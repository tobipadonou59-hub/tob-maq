/* ==========================================================================
   Assistant WhatsApp — webhook officiel WhatsApp Business Platform + Claude.
   Routes : /webhook (Meta), /api/admin/* (tableau de bord), /api/suggerer (raccourci iPhone).
   ========================================================================== */
import express from "express";
import crypto from "node:crypto";
import path from "node:path";
import { config, configProblems, ROOT } from "./config.js";
import { all, getRules, setSetting, getMode, isPaused, purge } from "./db.js";
import { verifySignature, parseWebhook } from "./whatsapp.js";
import { recevoir, recevoirEchos, envoyer, rejeter, suggerer, reprendre } from "./assistant.js";

const MODES = ["suggestion", "validation", "automatique"];

const egal = (a, b) => {
  const x = crypto.createHash("sha256").update(String(a)).digest(), y = crypto.createHash("sha256").update(String(b)).digest();
  return crypto.timingSafeEqual(x, y);
};

/* Limite simple en mémoire : n essais par fenêtre, par clé (adresse IP). */
function limiteur(n, fenetreMs) {
  const hits = new Map();
  return key => {
    const now = Date.now(), h = (hits.get(key) || []).filter(t => t > now - fenetreMs);
    h.push(now); hits.set(key, h);
    return h.length > n;
  };
}

function jeton(req) {
  const h = req.headers.authorization || "";
  return h.startsWith("Bearer ") ? h.slice(7).trim() : "";
}

export function createApp() {
  const app = express();
  app.disable("x-powered-by");
  if (config.trustProxy) app.set("trust proxy", 1);
  app.use((req, res, next) => {
    res.set({
      "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
      "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    });
    next();
  });

  app.get("/api/sante", (req, res) => res.json({ ok: true }));

  /* Vérification du webhook par Meta (une seule fois, lors de la configuration). */
  app.get("/webhook", (req, res) => {
    if (config.waVerifyToken && req.query["hub.mode"] === "subscribe" && egal(req.query["hub.verify_token"] || "", config.waVerifyToken))
      return res.type("text/plain").send(String(req.query["hub.challenge"] || ""));
    res.sendStatus(403);
  });

  /* Messages entrants. On répond tout de suite à Meta (sinon il renvoie le message), puis on traite. */
  app.post("/webhook", express.raw({ type: "*/*", limit: "1mb" }), (req, res) => {
    if (!verifySignature(req.body, req.headers["x-hub-signature-256"])) return res.sendStatus(401);
    let body;
    try { body = JSON.parse(req.body.toString("utf8")); } catch { return res.sendStatus(400); }
    res.sendStatus(200);
    const { messages, echos } = parseWebhook(body);
    try { if (echos.length) recevoirEchos(echos); } catch (e) { console.error("Échos", e); }
    if (messages.length) recevoir(messages).catch(e => console.error("Réception", e));
  });

  app.use("/api", express.json({ limit: "200kb" }));

  /* Raccourci iPhone : suggestion seule, rien n'est envoyé ni enregistré. */
  const tropSuggestions = limiteur(60, 3600000);
  app.post("/api/suggerer", async (req, res) => {
    const t = jeton(req);
    const ok = t && ((config.shortcutToken.length >= 24 && egal(t, config.shortcutToken)) || (config.adminToken.length >= 24 && egal(t, config.adminToken)));
    if (!ok) return res.status(401).json({ erreur: "Jeton invalide." });
    if (tropSuggestions(req.ip)) return res.status(429).json({ erreur: "Trop de demandes. Réessayez plus tard." });
    const texte = String(req.body?.texte || "").trim().slice(0, 4000);
    if (!texte) return res.status(400).json({ erreur: "Aucun message à analyser. Copiez d'abord le message dans WhatsApp." });
    try {
      res.json(await suggerer({ texte, contact: String(req.body?.contact || "").slice(0, 60), style: String(req.body?.style || "").slice(0, 40) }));
    } catch (e) {
      console.error("Suggestion", e.message);
      res.status(502).json({ erreur: "Claude n'a pas pu répondre. Réessayez dans un instant." });
    }
  });

  /* Tableau de bord : protégé par ADMIN_TOKEN, avec blocage après trop d'échecs. */
  const tropEchecs = limiteur(10, 900000);
  app.use("/api/admin", (req, res, next) => {
    if (config.adminToken.length < 24) return res.status(503).json({ erreur: "ADMIN_TOKEN n'est pas configuré sur le serveur." });
    const t = jeton(req);
    if (t && egal(t, config.adminToken)) return next();
    if (tropEchecs(req.ip)) return res.status(429).json({ erreur: "Trop d'essais. Patientez 15 minutes." });
    res.status(401).json({ erreur: "Mot de passe incorrect." });
  });

  const lire = b => ({ ...b, messages: undefined, analyse: b.analyse ? JSON.parse(b.analyse) : null,
    textes: all(`SELECT texte, type, at FROM messages WHERE id IN (${JSON.parse(b.messages).map(() => "?").join(",") || "''"}) ORDER BY at`, ...JSON.parse(b.messages)) });

  app.get("/api/admin/etat", (req, res) => res.json({
    mode: getMode(), pause: isPaused(), modele: config.model, problemes: configProblems(),
    enAttente: all("SELECT * FROM brouillons WHERE statut IN ('a_valider', 'suggestion', 'erreur') ORDER BY cree DESC LIMIT 50").map(lire),
    recents: all("SELECT * FROM brouillons WHERE statut IN ('envoye', 'rejete', 'ignore') ORDER BY maj DESC LIMIT 30").map(lire)
  }));

  app.post("/api/admin/mode", (req, res) => {
    if (!MODES.includes(req.body?.mode)) return res.status(400).json({ erreur: "Mode inconnu." });
    setSetting("mode", req.body.mode); res.json({ mode: req.body.mode });
  });
  app.post("/api/admin/pause", (req, res) => { setSetting("pause", Boolean(req.body?.pause)); res.json({ pause: isPaused() }); });

  app.post("/api/admin/brouillons/:id/envoyer", async (req, res) => {
    const texte = typeof req.body?.texte === "string" ? req.body.texte.trim().slice(0, 4000) : undefined;
    try { await envoyer(Number(req.params.id), { texte }); res.json({ ok: true }); }
    catch (e) { res.status(409).json({ erreur: e.message }); }
  });
  app.post("/api/admin/brouillons/:id/rejeter", (req, res) => {
    try { rejeter(Number(req.params.id)); res.json({ ok: true }); }
    catch (e) { res.status(409).json({ erreur: e.message }); }
  });

  app.get("/api/admin/regles", (req, res) => res.json(getRules()));
  app.put("/api/admin/regles", (req, res) => {
    const r = req.body;
    const ok = r && typeof r === "object" && !Array.isArray(r) && Array.isArray(r.categories_automatiques) && Array.isArray(r.mots_toujours_valides)
      && typeof r.infos_autorisees === "string" && r.contacts && typeof r.contacts === "object";
    if (!ok) return res.status(400).json({ erreur: "Règles invalides : gardez au moins infos_autorisees, categories_automatiques, mots_toujours_valides et contacts." });
    setSetting("regles", r); res.json({ ok: true });
  });

  app.use(express.static(path.join(ROOT, "public"), { index: "index.html" }));
  return app;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.join(ROOT, "src", "index.js")) {
  for (const p of configProblems()) console.warn("⚠", p);
  createApp().listen(config.port, () => console.log(`Assistant WhatsApp prêt sur le port ${config.port} — mode ${getMode()}${isPaused() ? " (en pause)" : ""}.`));
  reprendre();
  purge();
  setInterval(() => purge(), 86400000).unref();
}
