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
const planLabel = id => PLANS[id]?.label || (id === "essai" ? "Essai gratuit" : id);
/* Leçons Premium : importées par l'administration dans le dossier de stockage (hors du dépôt
   GitHub, qui peut être public), avec en secours celles livrées avec le code. */
const PREMIUM_DIR = path.join(SERVER_DIR, "contenus-premium", "lecons");
const premiumUploadDir = () => path.join(config.storageDir, "premium");
const ID_RE = /^[a-z0-9-]{1,60}$/;
const LEVELS = ["Débutant", "Intermédiaire", "Avancé"];

/* L'introduction est du HTML : seules quelques balises de mise en forme sans attributs sont gardées. */
const cleanHtml = h => String(h).replace(/<(\/?)([a-z0-9]+)[^>]*>/gi, (m, slash, tag) => ["p", "strong", "em", "b", "i", "ul", "ol", "li", "br"].includes(tag.toLowerCase()) ? `<${slash}${tag.toLowerCase()}>` : "");

/* Vérifie et normalise une leçon importée ; renvoie la leçon propre ou lève une erreur 400 explicite. */
export function validateLesson(l) {
  const bad = m => fail(400, `Leçon invalide : ${m}`);
  if (!l || typeof l !== "object" || Array.isArray(l)) bad("le fichier doit contenir un objet JSON.");
  const str = (k, max, need = true) => { const v = l[k]; if (v === undefined || v === null || v === "") { if (need) bad(`le champ « ${k} » est obligatoire.`); return undefined; } if (typeof v !== "string" || v.length > max) bad(`le champ « ${k} » doit être un texte de ${max} caractères maximum.`); return v.trim(); };
  const list = (k, max, fn, need = true) => { const v = l[k]; if (v === undefined && !need) return undefined; if (!Array.isArray(v) || (need && !v.length) || v.length > max) bad(`le champ « ${k} » doit être une liste (1 à ${max} éléments).`); return v.map((x, i) => fn(x, i)); };
  const txt = (v, max, where) => { if (typeof v !== "string" || !v.trim() || v.length > max) bad(`${where} : texte manquant ou trop long.`); return v.trim(); };
  const minutes = Number(l.minutes);
  if (!Number.isInteger(minutes) || minutes < 1 || minutes > 600) bad("« minutes » doit être un nombre entier entre 1 et 600.");
  if (!LEVELS.includes(l.level)) bad(`« level » doit valoir ${LEVELS.join(", ")}.`);
  const out = { title: str("title", 120), software: str("software", 60), level: l.level, minutes, objective: str("objective", 400),
    intro: cleanHtml(str("intro", 6000)), beginner: str("beginner", 800, false), advanced: str("advanced", 800, false),
    steps: list("steps", 20, (x, i) => ({ t: txt(x?.t, 120, `étape ${i + 1}`), d: txt(x?.d, 1200, `étape ${i + 1}`),
      ...(x?.keys !== undefined ? { keys: (Array.isArray(x.keys) && x.keys.length <= 8 ? x.keys : bad(`étape ${i + 1} : 8 raccourcis maximum.`)).map(k => txt(k, 30, `raccourci de l'étape ${i + 1}`)) } : {}) })),
    params: l.params === undefined ? undefined : list("params", 20, (x, i) => { if (!Array.isArray(x) || x.length !== 2) bad(`paramètre ${i + 1} : il faut [nom, valeur].`); return [txt(x[0], 80, `paramètre ${i + 1}`), txt(x[1], 300, `paramètre ${i + 1}`)]; }, false),
    illustration: str("illustration", 30, false), caption: str("caption", 200, false),
    before: str("before", 600, false), after: str("after", 600, false),
    example: str("example", 2000), exercise: str("exercise", 2000),
    quiz: list("quiz", 10, (x, i) => { const choices = Array.isArray(x?.choices) && x.choices.length >= 2 && x.choices.length <= 5 ? x.choices.map(c => txt(c, 200, `quiz ${i + 1}`)) : bad(`quiz ${i + 1} : 2 à 5 réponses.`);
      if (!Number.isInteger(x.answer) || x.answer < 0 || x.answer >= choices.length) bad(`quiz ${i + 1} : « answer » doit être le numéro (à partir de 0) de la bonne réponse.`);
      return { q: txt(x.q, 300, `quiz ${i + 1}`), choices, answer: x.answer, explain: txt(x.explain, 500, `quiz ${i + 1}`) }; }),
    recap: list("recap", 12, (x, i) => txt(x, 300, `récapitulatif ${i + 1}`)) };
  if (out.illustration && !/^[a-z]+$/.test(out.illustration)) bad("« illustration » invalide.");
  return Object.fromEntries(Object.entries(out).filter(([, v]) => v !== undefined));
}

export const isPremium = u => Boolean(u && (u.role === "admin" || (u.premium_until && u.premium_until > now())));
/* Accès payant obligatoire : actif seulement si l'administrateur l'a choisi ET que la vente est réellement ouverte. */
export const paywallOn = () => { const s = getBillingSettings(); return Boolean(s.paywall && s.enabled && config.fedapayKey && (s.priceMonthly || s.priceYearly)); };
export const hasAccess = u => !paywallOn() || isPremium(u);
export function needAccess(req, res, next) {
  if (hasAccess(req.user)) return next();
  fail(402, "Cette partie est réservée aux abonnés. Lance ton essai gratuit ou abonne-toi pour continuer.", "SUBSCRIPTION_REQUIRED");
}

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
    return { enabled: Boolean(s.enabled && config.fedapayKey && plans.length), configured: Boolean(config.fedapayKey), currency: "FCFA", plans, mode: config.fedapayEnv,
      trial: { enabled: Boolean(s.trialEnabled), days: s.trialDays }, paywall: paywallOn() };
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

  /* Essai gratuit : une seule fois par compte, sans moyen de paiement ; l'accès s'arrête seul à la fin. */
  api.post("/billing/trial", needUser, needConsent, (req, res) => {
    const s = getBillingSettings();
    if (!s.trialEnabled) fail(403, "L'essai gratuit n'est pas proposé pour le moment.", "TRIAL_CLOSED");
    const u = one("SELECT * FROM users WHERE id = ?", req.user.id);
    if (u.trial_used_at) fail(409, "Tu as déjà profité de ton essai gratuit. Tu peux continuer avec un abonnement Premium.", "TRIAL_USED");
    if (u.premium_until && u.premium_until > now()) fail(409, "Tu es déjà membre Premium.", "ALREADY_PREMIUM");
    const end = new Date(); end.setUTCDate(end.getUTCDate() + s.trialDays);
    // Mise à jour conditionnelle : deux clics simultanés ne donnent qu'un seul essai.
    const r = run("UPDATE users SET premium_until = ?, trial_used_at = ? WHERE id = ? AND trial_used_at IS NULL", end.toISOString(), now(), u.id);
    if (!r.changes) fail(409, "Tu as déjà profité de ton essai gratuit.", "TRIAL_USED");
    run("INSERT INTO payments(id, user_id, provider, plan, amount, status, created_at, approved_at) VALUES (?,?,?,?,?,?,?,?)", uid(), u.id, "essai", "essai", 0, "approved", now(), now());
    res.json({ premiumUntil: end.toISOString(), days: s.trialDays });
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
    const u = one("SELECT premium_until, role, trial_used_at FROM users WHERE id = ?", req.user.id);
    const paid = one("SELECT 1 AS x FROM payments WHERE user_id = ? AND status = 'approved' AND provider != 'essai'", req.user.id);
    const premium = isPremium({ ...req.user, ...u });
    res.json({ premiumUntil: u.premium_until, premium, trialUsed: Boolean(u.trial_used_at), onTrial: Boolean(premium && u.trial_used_at && !paid && u.role !== "admin"),
      payments: all("SELECT plan, amount, status, created_at FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", req.user.id)
        .map(p => ({ plan: planLabel(p.plan), amount: p.amount, status: p.status, createdAt: p.created_at })) });
  });

  /* ---------- Contenus premium (fichiers JSON dans server/contenus-premium/lecons) ---------- */
  const dirs = () => [premiumUploadDir(), PREMIUM_DIR];
  const readLesson = id => { for (const d of dirs()) { try { return JSON.parse(fs.readFileSync(path.join(d, id + ".json"), "utf8")); } catch { /* fichier suivant */ } } return null; };
  const lessonIds = () => [...new Set(dirs().flatMap(d => { try { return fs.readdirSync(d).filter(f => f.endsWith(".json")).map(f => f.slice(0, -5)); } catch { return []; } }))].filter(id => ID_RE.test(id)).sort();
  api.get("/premium/catalog", (req, res) => {
    res.json(lessonIds().map(id => { const l = readLesson(id); return l && { id, title: l.title, minutes: l.minutes, software: l.software, level: l.level }; }).filter(Boolean));
  });
  api.get("/premium/lessons/:id", needUser, (req, res) => {
    if (!ID_RE.test(req.params.id)) fail(404, "Leçon introuvable.");
    if (!isPremium(req.user)) fail(403, "Cette leçon est réservée aux membres Premium.", "PREMIUM_REQUIRED");
    const l = readLesson(req.params.id);
    if (!l) fail(404, "Leçon introuvable.");
    res.set("Cache-Control", "private, no-store").json(l);
  });

  /* ---------- Administration ---------- */
  api.get("/admin/premium", needAdmin, (req, res) => {
    res.json(lessonIds().map(id => { const l = readLesson(id); return l && { id, title: l.title, minutes: l.minutes, level: l.level,
      imported: fs.existsSync(path.join(premiumUploadDir(), id + ".json")) }; }).filter(Boolean));
  });
  api.put("/admin/premium/:id", needAdmin, (req, res) => {
    if (!ID_RE.test(req.params.id)) fail(400, "Identifiant invalide : lettres minuscules, chiffres et tirets uniquement.");
    const lesson = validateLesson(req.body);
    fs.mkdirSync(premiumUploadDir(), { recursive: true });
    const file = path.join(premiumUploadDir(), req.params.id + ".json");
    fs.writeFileSync(file + ".tmp", JSON.stringify(lesson)); fs.renameSync(file + ".tmp", file);
    res.json({ id: req.params.id, title: lesson.title });
  });
  api.delete("/admin/premium/:id", needAdmin, (req, res) => {
    if (!ID_RE.test(req.params.id)) fail(404, "Leçon introuvable.");
    const file = path.join(premiumUploadDir(), req.params.id + ".json");
    if (!fs.existsSync(file)) fail(404, "Seules les leçons importées depuis l'administration peuvent être retirées ici.");
    fs.rmSync(file); res.json({ ok: true });
  });

  api.get("/admin/billing", needAdmin, (req, res) => {
    const s = getBillingSettings();
    res.json({ ...s, paywallActive: paywallOn(), configured: Boolean(config.fedapayKey), mode: config.fedapayEnv,
      webhookUrl: `${config.publicUrl}/api/billing/webhook`,
      revenue: one("SELECT COALESCE(SUM(amount), 0) AS t FROM payments WHERE status = 'approved'").t,
      subscribers: one("SELECT COUNT(*) AS n FROM users WHERE premium_until > ?", now()).n,
      trials: one("SELECT COUNT(*) AS n FROM users WHERE trial_used_at IS NOT NULL").n,
      convertedTrials: one("SELECT COUNT(DISTINCT u.id) AS n FROM users u JOIN payments p ON p.user_id = u.id WHERE u.trial_used_at IS NOT NULL AND p.status = 'approved' AND p.provider != 'essai'").n });
  });
  api.patch("/admin/billing", needAdmin, (req, res) => {
    const price = v => { if (v === null || v === "" || v === undefined) return null; const n = Number(v); if (!Number.isInteger(n) || n < 100 || n > 5000000) fail(400, "Prix invalide : un nombre entier entre 100 et 5 000 000 FCFA."); return n; };
    const cur = getBillingSettings(); // un réglage absent de la requête garde sa valeur actuelle
    const days = req.body?.trialDays === undefined ? cur.trialDays : Number(req.body.trialDays);
    if (!Number.isInteger(days) || days < 1 || days > 90) fail(400, "La durée de l'essai doit être comprise entre 1 et 90 jours.");
    const s = { enabled: req.body?.enabled === true, priceMonthly: price(req.body?.priceMonthly), priceYearly: price(req.body?.priceYearly),
      trialEnabled: req.body?.trialEnabled === undefined ? cur.trialEnabled : req.body.trialEnabled === true, trialDays: days,
      paywall: req.body?.paywall === undefined ? Boolean(cur.paywall) : req.body.paywall === true };
    if (s.enabled && !s.priceMonthly && !s.priceYearly) fail(400, "Fixe au moins un prix avant d'ouvrir la vente.");
    if (s.paywall && !s.enabled) fail(400, "Ouvre la vente avant de rendre l'accès payant.");
    if (s.paywall && !config.fedapayKey) fail(400, "Configure FedaPay (FEDAPAY_SECRET_KEY) avant de rendre l'accès payant.");
    setBillingSettings(s);
    res.json(s);
  });
  api.get("/admin/payments", needAdmin, (req, res) => res.json(all("SELECT p.*, u.display_name, u.email FROM payments p JOIN users u ON u.id = p.user_id ORDER BY p.created_at DESC LIMIT 300")
    .map(p => ({ user: `${p.display_name} (${p.email})`, plan: planLabel(p.plan), amount: p.amount, status: p.status, createdAt: p.created_at }))));
}
