/* ==========================================================================
   Abonnement Premium payé via FedaPay (MTN MoMo, Moov Money, cartes).
   Principe de sécurité : le statut d'un paiement est TOUJOURS revérifié
   auprès de l'API FedaPay avec la clé secrète du serveur. Ni le navigateur
   ni le contenu d'un webhook ne suffisent à débloquer l'accès.
   ========================================================================== */
import fs from "node:fs";
import path from "node:path";
import { config, SERVER_DIR } from "./config.js";
import { one, all, run, now, getBillingSettings, setBillingSettings } from "./db.js";
import { HttpError, fail, uid, oneOf, rateLimit } from "./security.js";

export const PLANS = { mois: { label: "1 mois", days: 30, key: "priceMonthly" }, an: { label: "1 an", days: 365, key: "priceYearly" } };
const PREMIUM_DIR = path.join(SERVER_DIR, "contenus-premium", "lecons");
const ID_RE = /^[a-z0-9-]{1,60}$/;

export const isPremium = u => Boolean(u && (u.role === "admin" || (u.premium_until && u.premium_until > now())));

/* ---------- Client FedaPay ---------- */
const apiBase = () => config.fedapayApiUrl || (config.fedapayEnv === "live" ? "https://api.fedapay.com/v1" : "https://sandbox-api.fedapay.com/v1");
const unwrap = (d, k) => d?.[`v1/${k}`] ?? d?.[k] ?? d;
async function fedapay(method, p, body) {
  if (!config.fedapayKey) throw new HttpError(503, "Le paiement n'est pas encore configuré sur le serveur.", "PAYMENT_NOT_CONFIGURED");
  const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 20000);
  try {
    const res = await fetch(apiBase() + p, {
      method, signal: ctrl.signal,
      headers: { Authorization: `Bearer ${config.fedapayKey}`, "Content-Type": "application/json", Accept: "application/json" },
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { console.error("Erreur FedaPay", method, p, res.status, JSON.stringify(data).slice(0, 500)); throw new HttpError(502, "Le service de paiement a refusé la demande. Réessaie plus tard.", "PAYMENT_PROVIDER_ERROR"); }
    return data;
  } catch (e) {
    if (e instanceof HttpError) throw e;
    throw new HttpError(502, "Impossible de joindre le service de paiement. Réessaie dans quelques minutes.", "PAYMENT_UNREACHABLE");
  } finally { clearTimeout(timer); }
}

/* Revérifie un paiement auprès de FedaPay et, s'il est approuvé, prolonge l'abonnement (une seule fois). */
export async function confirmPayment(payment) {
  if (!payment || !payment.provider_tx_id) return payment;
  if (payment.status === "approved") return payment;
  const tx = unwrap(await fedapay("GET", `/transactions/${encodeURIComponent(payment.provider_tx_id)}`), "transaction");
  const status = String(tx?.status || "").toLowerCase();
  const amountOk = Number(tx?.amount) === payment.amount;
  if (status === "approved" && amountOk) {
    // Mise à jour conditionnelle : si deux confirmations arrivent en même temps, une seule prolonge l'abonnement.
    const r = run("UPDATE payments SET status = 'approved', approved_at = ? WHERE id = ? AND status != 'approved'", now(), payment.id);
    if (r.changes) {
      const u = one("SELECT premium_until FROM users WHERE id = ?", payment.user_id);
      const start = u?.premium_until && u.premium_until > now() ? new Date(u.premium_until) : new Date();
      start.setUTCDate(start.getUTCDate() + PLANS[payment.plan].days);
      run("UPDATE users SET premium_until = ? WHERE id = ?", start.toISOString(), payment.user_id);
    }
  } else if (["declined", "canceled", "cancelled", "refunded", "expired"].includes(status)) {
    run("UPDATE payments SET status = ? WHERE id = ? AND status = 'pending'", status, payment.id);
  } else if (status === "approved" && !amountOk) {
    console.error("Paiement FedaPay approuvé avec un montant inattendu", payment.id, tx?.amount, payment.amount);
    run("UPDATE payments SET status = 'montant_incorrect' WHERE id = ?", payment.id);
  }
  return one("SELECT * FROM payments WHERE id = ?", payment.id);
}

export function registerBilling(api, { needUser, needAdmin, needConsent }) {
  const plansPublic = () => {
    const s = getBillingSettings();
    const plans = Object.entries(PLANS).filter(([, p]) => Number.isInteger(s[p.key]) && s[p.key] > 0).map(([id, p]) => ({ id, label: p.label, price: s[p.key], days: p.days }));
    return { enabled: Boolean(s.enabled && config.fedapayKey && plans.length), configured: Boolean(config.fedapayKey), currency: "FCFA", plans, mode: config.fedapayEnv };
  };

  api.get("/billing/plans", (req, res) => res.json(plansPublic()));

  /* Démarre un paiement : crée la transaction chez FedaPay et renvoie l'adresse de la page de paiement. */
  api.post("/billing/checkout", needUser, needConsent, async (req, res) => {
    rateLimit("checkout:" + req.user.id, 5, 10 * 60000);
    const plan = oneOf(req.body?.plan, Object.keys(PLANS), "Formule");
    const info = plansPublic();
    if (!info.enabled) fail(503, "L'abonnement Premium n'est pas encore ouvert à la vente.", "BILLING_CLOSED");
    const p = info.plans.find(x => x.id === plan);
    if (!p) fail(400, "Cette formule n'est pas disponible.");
    const id = uid();
    run("INSERT INTO payments(id, user_id, provider, plan, amount, created_at) VALUES (?,?,?,?,?,?)", id, req.user.id, "fedapay", plan, p.price, now());
    const tx = unwrap(await fedapay("POST", "/transactions", {
      description: `TOB-MAQ Premium · ${p.label}`, amount: p.price, currency: { iso: "XOF" },
      callback_url: `${config.publicUrl}/api/billing/retour?ref=${id}`,
      customer: { firstname: req.user.display_name.slice(0, 40), lastname: "TOB-MAQ", email: req.user.email }
    }), "transaction");
    if (!tx?.id) fail(502, "Le service de paiement n'a pas créé la transaction.", "PAYMENT_PROVIDER_ERROR");
    run("UPDATE payments SET provider_tx_id = ? WHERE id = ?", String(tx.id), id);
    const tok = await fedapay("POST", `/transactions/${encodeURIComponent(tx.id)}/token`);
    const url = tok?.url || unwrap(tok, "token")?.url;
    // HTTPS obligatoire (http seulement accepté avec le faux FedaPay des tests).
    if (!url || !(/^https:\/\//.test(url) || (config.fedapayApiUrl && /^http:\/\//.test(url)))) fail(502, "Le service de paiement n'a pas fourni de page de paiement.", "PAYMENT_PROVIDER_ERROR");
    res.json({ url });
  });

  /* Retour de la page de paiement FedaPay vers le site. */
  api.get("/billing/retour", async (req, res) => {
    const pay = typeof req.query.ref === "string" ? one("SELECT * FROM payments WHERE id = ?", req.query.ref) : null;
    let result = "erreur";
    try { const p = await confirmPayment(pay); result = p?.status === "approved" ? "ok" : p?.status === "pending" ? "attente" : "echec"; }
    catch (e) { console.error("Vérification du paiement au retour", e.message); }
    res.redirect(303, `/#/tableau-de-bord?paiement=${result}`);
  });

  /* Notification envoyée par FedaPay : on ne lit que l'identifiant, puis on revérifie auprès de FedaPay. */
  api.post("/billing/webhook", async (req, res) => {
    const txId = String(req.body?.entity?.id ?? req.body?.object_id ?? req.body?.id ?? "");
    const pay = txId ? one("SELECT * FROM payments WHERE provider_tx_id = ?", txId) : null;
    if (pay) { try { await confirmPayment(pay); } catch (e) { console.error("Webhook FedaPay", e.message); return res.status(502).json({ ok: false }); } }
    res.json({ ok: true });
  });

  api.get("/me/billing", needUser, async (req, res) => {
    // Revérifie les paiements restés en attente (si l'utilisateur a fermé la page avant le retour).
    for (const p of all("SELECT * FROM payments WHERE user_id = ? AND status = 'pending' AND provider_tx_id IS NOT NULL ORDER BY created_at DESC LIMIT 3", req.user.id)) {
      try { await confirmPayment(p); } catch { /* nouvel essai à la prochaine visite */ }
    }
    const u = one("SELECT premium_until, role FROM users WHERE id = ?", req.user.id);
    res.json({ premiumUntil: u.premium_until, premium: isPremium({ ...req.user, ...u }),
      payments: all("SELECT plan, amount, status, created_at FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", req.user.id)
        .map(p => ({ plan: PLANS[p.plan]?.label || p.plan, amount: p.amount, status: p.status, createdAt: p.created_at })) });
  });

  /* ---------- Contenus premium (fichiers JSON dans server/contenus-premium/lecons) ---------- */
  const readLesson = id => { try { return JSON.parse(fs.readFileSync(path.join(PREMIUM_DIR, id + ".json"), "utf8")); } catch { return null; } };
  api.get("/premium/catalog", (req, res) => {
    let files = [];
    try { files = fs.readdirSync(PREMIUM_DIR).filter(f => f.endsWith(".json")); } catch { /* dossier absent */ }
    res.json(files.map(f => f.slice(0, -5)).filter(id => ID_RE.test(id)).map(id => { const l = readLesson(id); return l && { id, title: l.title, minutes: l.minutes, software: l.software, level: l.level }; }).filter(Boolean));
  });
  api.get("/premium/lessons/:id", needUser, (req, res) => {
    if (!ID_RE.test(req.params.id)) fail(404, "Leçon introuvable.");
    if (!isPremium(req.user)) fail(403, "Cette leçon est réservée aux membres Premium.", "PREMIUM_REQUIRED");
    const l = readLesson(req.params.id);
    if (!l) fail(404, "Leçon introuvable.");
    res.set("Cache-Control", "private, no-store").json(l);
  });

  /* ---------- Administration ---------- */
  api.get("/admin/billing", needAdmin, (req, res) => {
    const s = getBillingSettings();
    res.json({ ...s, configured: Boolean(config.fedapayKey), mode: config.fedapayEnv,
      webhookUrl: `${config.publicUrl}/api/billing/webhook`,
      revenue: one("SELECT COALESCE(SUM(amount), 0) AS t FROM payments WHERE status = 'approved'").t,
      subscribers: one("SELECT COUNT(*) AS n FROM users WHERE premium_until > ?", now()).n });
  });
  api.patch("/admin/billing", needAdmin, (req, res) => {
    const price = v => { if (v === null || v === "" || v === undefined) return null; const n = Number(v); if (!Number.isInteger(n) || n < 100 || n > 5000000) fail(400, "Prix invalide : un nombre entier entre 100 et 5 000 000 FCFA."); return n; };
    const s = { enabled: req.body?.enabled === true, priceMonthly: price(req.body?.priceMonthly), priceYearly: price(req.body?.priceYearly) };
    if (s.enabled && !s.priceMonthly && !s.priceYearly) fail(400, "Fixe au moins un prix avant d'ouvrir la vente.");
    setBillingSettings(s);
    res.json(s);
  });
  api.get("/admin/payments", needAdmin, (req, res) => res.json(all("SELECT p.*, u.display_name, u.email FROM payments p JOIN users u ON u.id = p.user_id ORDER BY p.created_at DESC LIMIT 300")
    .map(p => ({ user: `${p.display_name} (${p.email})`, plan: PLANS[p.plan]?.label || p.plan, amount: p.amount, status: p.status, createdAt: p.created_at }))));
}
