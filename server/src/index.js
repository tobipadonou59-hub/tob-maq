/* ==========================================================================
   Serveur TOB-MAQ — sert le site (index.html, ressources) et l'API /api.
   Même origine pour le site et l'API : cookies de session HttpOnly, sans CORS.
   ========================================================================== */
import express from "express";
import multer from "multer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config, SITE_DIR } from "./config.js";
import { one, all, run, now, getAiSettings, setAiSettings } from "./db.js";
import { HttpError, fail, hashPassword, verifyPassword, newToken, sha256, uid, rateLimit, text, email, password, oneOf, sniff, parseCookies } from "./security.js";
import { sendMail } from "./mail.js";
import { registerBilling, isPremium } from "./billing.js";
import { imageProvider, videoProvider, generateImage, buildImagePrompt, buildDemoPrompt, IMAGE_SIZES, IMAGE_STYLES } from "./ai.js";

const LEVELS = ["Débutant", "Intermédiaire", "Avancé"];
const INTERESTS = ["graphisme", "maquettisme", "video", "reseaux", "cinema", "ia"];
const DISCIPLINES = ["Affiches", "Logos", "Identités visuelles", "Maquettes éditoriales", "Vidéos cinématiques", "Clips montés", "Publicités", "Animations graphiques"];
const GAME_LEVELS = ["facile", "moyen", "difficile"];
const ID_RE = /^[a-z0-9-]{1,60}$/;
const COOKIE = "tobmaq_sid";

const publicUser = u => ({
  displayName: u.display_name, email: u.email, level: u.level || "", interests: JSON.parse(u.interests || "[]"), role: u.role,
  ageGroup: u.age_group, pendingParentalConsent: u.age_group === "mineur" && !u.parent_consent_at,
  premium: isPremium(u), premiumUntil: u.premium_until || null, trialUsed: Boolean(u.trial_used_at)
});
const authorName = u => u.age_group === "mineur" ? "Apprenant TOB-MAQ" : u.display_name; // jamais de nom affiché pour un mineur
const ip = req => req.ip || req.socket.remoteAddress || "?";

export function createApp() {
  const app = express();
  app.disable("x-powered-by");
  if (config.trustProxy) app.set("trust proxy", 1);

  /* En-têtes de sécurité */
  app.use((req, res, next) => {
    res.set({
      "X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin", "X-Frame-Options": "DENY",
      "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
      "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    });
    if (req.secure) res.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
    next();
  });

  /* Session : cookie HttpOnly -> utilisateur */
  app.use((req, res, next) => {
    req.user = null;
    const t = parseCookies(req.headers.cookie)[COOKIE];
    if (t) {
      const s = one("SELECT s.expires_at AS session_expires, u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?", sha256(t));
      if (s && s.session_expires > Date.now()) {
        // Une adresse listée dans ADMIN_EMAILS devient administrateur, même si le compte existait déjà.
        if (s.role !== "admin" && config.adminEmails.includes(s.email)) { run("UPDATE users SET role = 'admin' WHERE id = ?", s.id); s.role = "admin"; }
        req.user = s;
      }
      else if (s) run("DELETE FROM sessions WHERE token_hash = ?", sha256(t));
    }
    next();
  });

  const api = express.Router();
  api.use(express.json({ limit: "64kb" }));
  /* Protection CSRF : les requêtes qui modifient des données doivent venir du site lui-même. */
  const siteOrigin = new URL(config.publicUrl).origin;
  api.use((req, res, next) => {
    if (["GET", "HEAD", "OPTIONS"].includes(req.method)) return next();
    const origin = req.get("origin"), self = `${req.protocol}://${req.get("host")}`;
    if (origin && origin !== self && origin !== siteOrigin) return next(new HttpError(403, "Origine de la requête refusée.", "BAD_ORIGIN"));
    const site = req.get("sec-fetch-site");
    if (!origin && site && !["same-origin", "none"].includes(site)) return next(new HttpError(403, "Origine de la requête refusée.", "BAD_ORIGIN"));
    next();
  });

  const needUser = (req, res, next) => req.user ? next() : next(new HttpError(401, "Connecte-toi pour continuer.", "AUTH_REQUIRED"));
  const needAdmin = (req, res, next) => req.user?.role === "admin" ? next() : next(new HttpError(req.user ? 403 : 401, "Accès réservé aux administrateurs.", "ADMIN_REQUIRED"));
  const needConsent = (req, res, next) => publicUser(req.user).pendingParentalConsent
    ? next(new HttpError(403, "Cette fonction sera disponible quand ton parent ou tuteur aura confirmé son accord.", "CONSENT_PENDING")) : next();
  const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: config.maxUploadMb * 1048576, files: 1, fields: 20 } });

  function openSession(req, res, userId) {
    const t = newToken();
    run("INSERT INTO sessions(token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)", sha256(t), userId, Date.now() + config.sessionDays * 864e5, now());
    res.append("Set-Cookie", `${COOKIE}=${t}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${config.sessionDays * 86400}${req.secure ? "; Secure" : ""}`);
  }
  function newMailToken(userId, kind, hours) {
    const t = newToken();
    run("INSERT INTO tokens(token_hash, user_id, kind, expires_at) VALUES (?, ?, ?, ?)", sha256(t), userId, kind, Date.now() + hours * 3600e3);
    return t;
  }
  function useMailToken(t, kind) {
    const row = typeof t === "string" && t.length < 100 ? one("SELECT * FROM tokens WHERE token_hash = ? AND kind = ?", sha256(t), kind) : null;
    if (!row || row.used_at || row.expires_at < Date.now()) return null;
    return row;
  }

  /* ---------------- Authentification ---------------- */
  api.post("/auth/register", async (req, res) => {
    rateLimit("register:" + ip(req), 10, 15 * 60000);
    const b = req.body || {};
    const displayName = text(b.displayName, { min: 2, max: 30, name: "Le prénom ou pseudonyme" });
    if (!/^[\p{L}\p{N} ._'-]+$/u.test(displayName)) fail(400, "Le pseudonyme contient des caractères non autorisés.");
    const mail = email(b.email), pw = password(b.password);
    const ageGroup = oneOf(b.ageGroup, ["adulte", "mineur", "moins15"], "Tranche d'âge");
    if (ageGroup === "moins15") fail(400, "TOB-MAQ s'adresse aux personnes de 15 ans et plus.", "TOO_YOUNG");
    if (b.acceptTerms !== true) fail(400, "Tu dois accepter les conditions d'utilisation.");
    const level = oneOf(b.level, LEVELS, "Niveau");
    const interests = Array.isArray(b.interests) ? b.interests.filter(i => INTERESTS.includes(i)) : [];
    if (!interests.length) fail(400, "Choisis au moins un domaine d'intérêt.");
    let parent = null;
    if (ageGroup === "mineur") { parent = email(b.parentEmail); if (parent === mail) fail(400, "L'e-mail du parent doit être différent du tien."); }
    if (one("SELECT 1 FROM users WHERE email = ?", mail)) fail(409, "Un compte existe déjà avec cette adresse e-mail.", "EMAIL_TAKEN");
    const id = uid(), role = config.adminEmails.includes(mail) ? "admin" : "membre";
    run("INSERT INTO users(id, email, display_name, password_hash, role, level, interests, age_group, parent_email, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
      id, mail, displayName, await hashPassword(pw), role, level, JSON.stringify(interests), ageGroup, parent, now());
    if (parent) {
      const t = newMailToken(id, "consent", 24 * 14);
      await sendMail({ to: parent, subject: "TOB-MAQ : accord parental demandé",
        text: `Bonjour,\n\n${displayName} (15-17 ans) souhaite créer un compte sur TOB-MAQ, une plateforme de formation au graphisme et au montage vidéo.\n\nPour donner votre accord, ouvrez ce lien (valable 14 jours) :\n${config.publicUrl}/api/auth/parent-consent?token=${t}\n\nSi vous ne connaissez pas cette demande, ignorez ce message : le compte restera limité.\n\nL'équipe TOB-MAQ` });
    }
    openSession(req, res, id);
    res.status(201).json({ user: publicUser(one("SELECT * FROM users WHERE id = ?", id)) });
  });

  api.post("/auth/login", async (req, res) => {
    const b = req.body || {};
    const mail = typeof b.email === "string" ? b.email.trim().toLowerCase() : "";
    rateLimit("login:" + ip(req), 20, 15 * 60000);
    rateLimit("login:" + mail, 8, 15 * 60000);
    const u = one("SELECT * FROM users WHERE email = ?", mail);
    const ok = await verifyPassword(typeof b.password === "string" ? b.password : "", u?.password_hash);
    if (!u || !ok) fail(401, "Adresse e-mail ou mot de passe incorrect.", "BAD_CREDENTIALS");
    if (u.role !== "admin" && config.adminEmails.includes(u.email)) { run("UPDATE users SET role = 'admin' WHERE id = ?", u.id); u.role = "admin"; }
    openSession(req, res, u.id);
    res.json({ user: publicUser(u) });
  });

  api.post("/auth/logout", (req, res) => {
    const t = parseCookies(req.headers.cookie)[COOKIE];
    if (t) run("DELETE FROM sessions WHERE token_hash = ?", sha256(t));
    res.append("Set-Cookie", `${COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`);
    res.status(204).end();
  });

  api.get("/auth/me", (req, res) => req.user ? res.json({ user: publicUser(req.user) }) : res.status(401).json({ message: "Non connecté.", code: "AUTH_REQUIRED" }));

  api.post("/auth/forgot-password", async (req, res) => {
    rateLimit("forgot:" + ip(req), 5, 15 * 60000);
    const mail = typeof req.body?.email === "string" ? req.body.email.trim().toLowerCase() : "";
    const u = one("SELECT * FROM users WHERE email = ?", mail);
    if (u) {
      const t = newMailToken(u.id, "reset", 1);
      await sendMail({ to: u.email, subject: "TOB-MAQ : réinitialiser ton mot de passe",
        text: `Bonjour ${u.display_name},\n\nPour choisir un nouveau mot de passe, ouvre ce lien (valable 1 heure) :\n${config.publicUrl}/#/reinitialiser?token=${t}\n\nSi tu n'as rien demandé, ignore ce message.\n\nL'équipe TOB-MAQ` });
    }
    res.status(204).end(); // même réponse que le compte existe ou non
  });

  api.post("/auth/reset-password", async (req, res) => {
    rateLimit("reset:" + ip(req), 10, 15 * 60000);
    const row = useMailToken(req.body?.token, "reset");
    if (!row) fail(400, "Ce lien n'est plus valide. Fais une nouvelle demande de réinitialisation.", "BAD_TOKEN");
    const pw = password(req.body?.password);
    run("UPDATE users SET password_hash = ? WHERE id = ?", await hashPassword(pw), row.user_id);
    run("UPDATE tokens SET used_at = ? WHERE token_hash = ?", now(), row.token_hash);
    run("DELETE FROM sessions WHERE user_id = ?", row.user_id);
    res.status(204).end();
  });

  const page = (title, body) => `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title} · TOB-MAQ</title>
    <style>body{font-family:system-ui,sans-serif;background:#0B0E17;color:#ECEEF5;display:grid;place-items:center;min-height:100vh;margin:0;padding:16px}main{max-width:480px;background:#141927;border:1px solid #2A3148;border-radius:18px;padding:32px}h1{margin-top:0}button{background:#8F76FF;color:#0B0E17;border:0;border-radius:999px;padding:12px 22px;font-weight:700;font-size:1rem;cursor:pointer}a{color:#B8AAFF}</style></head><body><main>${body}</main></body></html>`;
  api.get("/auth/parent-consent", (req, res) => {
    const row = useMailToken(req.query.token, "consent");
    if (!row) return res.status(400).send(page("Lien invalide", "<h1>Lien invalide ou expiré</h1><p>Demande à ton enfant de se reconnecter : un nouveau lien pourra être envoyé.</p>"));
    const u = one("SELECT display_name FROM users WHERE id = ?", row.user_id);
    const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    res.send(page("Accord parental", `<h1>Accord parental</h1><p><strong>${esc(u.display_name)}</strong> souhaite utiliser TOB-MAQ pour apprendre le graphisme et le montage vidéo.</p>
      <p>En confirmant, vous autorisez son compte. Son portfolio ne sera jamais public et son nom ne sera jamais affiché.</p>
      <form method="post" action="/api/auth/parent-consent"><input type="hidden" name="token" value="${esc(req.query.token)}"><button type="submit">Je donne mon accord</button></form>`));
  });
  api.post("/auth/parent-consent", express.urlencoded({ extended: false, limit: "4kb" }), (req, res) => {
    const row = useMailToken(req.body?.token, "consent");
    if (!row) return res.status(400).send(page("Lien invalide", "<h1>Lien invalide ou expiré</h1>"));
    run("UPDATE users SET parent_consent_at = ? WHERE id = ?", now(), row.user_id);
    run("UPDATE tokens SET used_at = ? WHERE token_hash = ?", now(), row.token_hash);
    res.send(page("Merci", `<h1>Merci !</h1><p>Le compte est maintenant actif. Vous pouvez fermer cette page.</p><p><a href="/">Découvrir TOB-MAQ</a></p>`));
  });

  /* ---------------- Compte et progression ---------------- */
  api.patch("/me", needUser, (req, res) => {
    const b = req.body || {};
    const name = text(b.displayName, { min: 2, max: 30, name: "Le pseudonyme" });
    if (!/^[\p{L}\p{N} ._'-]+$/u.test(name)) fail(400, "Le pseudonyme contient des caractères non autorisés.");
    const level = b.level ? oneOf(b.level, LEVELS, "Niveau") : null;
    const interests = Array.isArray(b.interests) ? b.interests.filter(i => INTERESTS.includes(i)) : [];
    run("UPDATE users SET display_name = ?, level = ?, interests = ? WHERE id = ?", name, level, JSON.stringify(interests), req.user.id);
    res.json({ user: publicUser(one("SELECT * FROM users WHERE id = ?", req.user.id)) });
  });

  function progressOf(userId) {
    const games = {};
    for (const g of all("SELECT * FROM games WHERE user_id = ?", userId)) {
      const e = games[g.game_id] ||= { best: {}, plays: 0, lastAt: null };
      e.best[g.level] = g.best; e.plays += g.plays; if (!e.lastAt || g.last_at > e.lastAt) e.lastAt = g.last_at;
    }
    return {
      lessonsDone: Object.fromEntries(all("SELECT lesson_id, done_at FROM lessons WHERE user_id = ?", userId).map(r => [r.lesson_id, r.done_at])),
      games, favorites: all("SELECT resource_id FROM favorites WHERE user_id = ?", userId).map(r => r.resource_id),
      downloads: all("SELECT resource_id, at FROM downloads WHERE user_id = ? ORDER BY at DESC LIMIT 40", userId).map(r => ({ id: r.resource_id, at: r.at }))
    };
  }
  const saveGame = (userId, gameId, level, points, plays = 1, at = now()) =>
    run(`INSERT INTO games(user_id, game_id, level, best, plays, last_at) VALUES (?,?,?,?,?,?)
         ON CONFLICT(user_id, game_id, level) DO UPDATE SET best = MAX(best, excluded.best), plays = plays + excluded.plays, last_at = excluded.last_at`,
      userId, gameId, level, points, plays, at);

  api.get("/me/progress", needUser, (req, res) => res.json(progressOf(req.user.id)));
  /* Importe la progression faite sur l'appareil avant la connexion (fusion, jamais d'écrasement à la baisse). */
  api.post("/me/progress/import", needUser, (req, res) => {
    const b = req.body || {};
    for (const [id, at] of Object.entries(b.lessonsDone || {}).slice(0, 500))
      if (ID_RE.test(id)) run("INSERT OR IGNORE INTO lessons(user_id, lesson_id, done_at) VALUES (?,?,?)", req.user.id, id, typeof at === "string" ? at.slice(0, 30) : now());
    for (const [id, g] of Object.entries(b.games || {}).slice(0, 100)) {
      if (!ID_RE.test(id) || !g || typeof g.best !== "object") continue;
      // Le nombre de parties jouées sur l'appareil est compté une seule fois (sur le premier niveau importé).
      let plays = Math.max(0, Math.min(10000, Math.round(Number(g.plays) || 0)));
      for (const [lvl, pts] of Object.entries(g.best)) if (GAME_LEVELS.includes(lvl) && Number.isFinite(pts)) { saveGame(req.user.id, id, lvl, Math.max(0, Math.min(100000, Math.round(pts))), plays, now()); plays = 0; }
    }
    for (const id of (Array.isArray(b.favorites) ? b.favorites : []).slice(0, 200)) if (ID_RE.test(id)) run("INSERT OR IGNORE INTO favorites VALUES (?, ?)", req.user.id, id);
    res.json(progressOf(req.user.id));
  });
  api.post("/me/lessons", needUser, (req, res) => {
    const id = text(req.body?.lessonId, { min: 1, max: 60, name: "La leçon" });
    if (!ID_RE.test(id)) fail(400, "Leçon invalide.");
    if (req.body.done === false) run("DELETE FROM lessons WHERE user_id = ? AND lesson_id = ?", req.user.id, id);
    else run("INSERT OR IGNORE INTO lessons(user_id, lesson_id, done_at) VALUES (?,?,?)", req.user.id, id, now());
    res.status(204).end();
  });
  api.post("/me/games", needUser, (req, res) => {
    const b = req.body || {};
    if (!ID_RE.test(String(b.gameId))) fail(400, "Jeu invalide.");
    const level = oneOf(b.level, GAME_LEVELS, "Niveau");
    const pts = Number(b.points);
    if (!Number.isFinite(pts) || pts < 0 || pts > 100000) fail(400, "Score invalide.");
    saveGame(req.user.id, b.gameId, level, Math.round(pts));
    res.status(204).end();
  });
  api.post("/me/downloads", needUser, (req, res) => {
    if (!ID_RE.test(String(req.body?.resourceId))) fail(400, "Ressource invalide.");
    run("INSERT INTO downloads VALUES (?,?,?,?)", uid(), req.user.id, req.body.resourceId, now());
    res.status(204).end();
  });
  api.post("/me/favorites", needUser, (req, res) => {
    if (!ID_RE.test(String(req.body?.resourceId))) fail(400, "Ressource invalide.");
    if (req.body.favorite === false) run("DELETE FROM favorites WHERE user_id = ? AND resource_id = ?", req.user.id, req.body.resourceId);
    else run("INSERT OR IGNORE INTO favorites VALUES (?, ?)", req.user.id, req.body.resourceId);
    res.status(204).end();
  });
  api.get("/me/projects", needUser, (req, res) => res.json(all("SELECT id, title, discipline, visibility, status, created_at FROM projects WHERE user_id = ? ORDER BY created_at DESC", req.user.id)
    .map(p => ({ id: p.id, title: p.title, discipline: p.discipline, visibility: { public: "Public", membres: "Membres", prive: "Privé" }[p.visibility] + " · " + { pending: "en modération", published: "publié", rejected: "refusé" }[p.status], createdAt: p.created_at }))));
  api.get("/me/creations", needUser, (req, res) => res.json(all("SELECT id, type, prompt, created_at FROM creations WHERE user_id = ? AND saved = 1 ORDER BY created_at DESC LIMIT 60", req.user.id)
    .map(c => ({ id: c.id, type: c.type, prompt: c.prompt, url: `/api/files/${c.id}`, createdAt: c.created_at }))));
  api.post("/me/creations", needUser, (req, res) => {
    const r = run("UPDATE creations SET saved = 1 WHERE id = ? AND user_id = ?", String(req.body?.id || ""), req.user.id);
    if (!r.changes) fail(404, "Création introuvable.");
    res.status(204).end();
  });
  api.get("/files/:id", needUser, (req, res) => {
    const c = one("SELECT * FROM creations WHERE id = ?", req.params.id);
    if (!c || (c.user_id !== req.user.id && req.user.role !== "admin")) fail(404, "Fichier introuvable.");
    res.set("Cache-Control", "private, max-age=86400").type(c.mime).sendFile(path.join(config.storageDir, "ai", c.file));
  });

  /* ---------------- Studio IA ---------------- */
  const today = () => new Date().toISOString().slice(0, 10);
  const used = (userId, kind) => one("SELECT COUNT(*) AS n FROM ai_usage WHERE user_id = ? AND kind = ? AND substr(at, 1, 10) = ?", userId, kind, today()).n;
  const monthCost = () => one("SELECT COALESCE(SUM(cost_fcfa), 0) AS c FROM ai_usage WHERE substr(at, 1, 7) = ?", today().slice(0, 7)).c;

  api.get("/ai/config", (req, res) => {
    const s = getAiSettings();
    res.json({
      provider: imageProvider,
      image: { enabled: Boolean(imageProvider && s.imageEnabled), styles: IMAGE_STYLES, sizes: IMAGE_SIZES },
      video: { enabled: Boolean(videoProvider && s.videoEnabled), ratios: ["16:9", "9:16", "1:1"], durations: [], imageToVideo: false },
      quota: req.user ? { images: { used: used(req.user.id, "image"), limit: s.dailyImageQuota }, videos: { used: used(req.user.id, "video"), limit: s.dailyVideoQuota } } : null
    });
  });
  async function imageJob(req, prompt, label) {
    const s = getAiSettings();
    if (!imageProvider) fail(503, "Aucun service de génération d'images n'est configuré sur le serveur.", "AI_NOT_CONFIGURED");
    if (!s.imageEnabled) fail(503, "La génération d'images est temporairement désactivée par l'administration.", "AI_DISABLED");
    rateLimit("ai:" + req.user.id, 3, 60000);
    if (used(req.user.id, "image") >= s.dailyImageQuota) fail(429, `Quota atteint : ${s.dailyImageQuota} image(s) par jour. Reviens demain.`, "QUOTA");
    if (monthCost() + config.imageCostFcfa > s.monthlyBudget) fail(429, "Le budget mensuel de génération de la plateforme est atteint. Réessaie le mois prochain.", "BUDGET");
    const png = await generateImage({ prompt, size: req.body.size });
    const id = uid();
    fs.writeFileSync(path.join(config.storageDir, "ai", id + ".png"), png);
    run("INSERT INTO creations(id, user_id, type, prompt, file, mime, created_at) VALUES (?,?,?,?,?,?,?)", id, req.user.id, label, text(req.body.prompt ?? req.body.topic, { max: 1000 }), id + ".png", "image/png", now());
    run("INSERT INTO ai_usage VALUES (?,?,?,?,?)", uid(), req.user.id, "image", config.imageCostFcfa, now());
    return { id, url: `/api/files/${id}`, quota: { used: used(req.user.id, "image"), limit: s.dailyImageQuota } };
  }
  api.post("/ai/images", needUser, needConsent, async (req, res) => {
    const b = req.body || {};
    const prompt = text(b.prompt, { min: 10, max: 1000, name: "La description" });
    const style = oneOf(b.style, IMAGE_STYLES, "Style");
    oneOf(b.size, IMAGE_SIZES.map(s => s[0]), "Format");
    const usage = text(b.usage, { max: 60, name: "L'usage" });
    const r = await imageJob(req, buildImagePrompt({ prompt, style, usage }), "image");
    res.json({ images: [{ id: r.id, url: r.url }], quota: r.quota });
  });
  api.post("/ai/demos", needUser, needConsent, async (req, res) => {
    const topic = text(req.body?.topic, { min: 3, max: 120, name: "La technique" });
    const details = req.body?.details ? text(req.body.details, { max: 200 }) : "";
    req.body.size = "landscape";
    const r = await imageJob(req, buildDemoPrompt({ topic, details }), "démonstration");
    res.json({ id: r.id, url: r.url, quota: r.quota });
  });
  api.post("/ai/videos", needUser, needConsent, upload.single("image"), () => {
    fail(503, "Aucun service de génération vidéo n'est configuré sur le serveur pour le moment.", "AI_NOT_CONFIGURED");
  });
  api.get("/ai/jobs/:id", needUser, () => fail(404, "Tâche introuvable."));
  api.delete("/ai/jobs/:id", needUser, () => fail(404, "Tâche introuvable."));

  /* ---------------- Portfolio, signalements, contact ---------------- */
  api.get("/portfolio", (req, res) => {
    const vis = req.user ? ["public", "membres"] : ["public"];
    const rows = all(`SELECT p.*, u.display_name, u.age_group FROM projects p JOIN users u ON u.id = p.user_id WHERE p.status = 'published' AND p.visibility IN (${vis.map(() => "?").join(",")}) ORDER BY p.created_at DESC LIMIT 60`, ...vis);
    res.json(rows.map(p => ({ id: p.id, title: p.title, discipline: p.discipline, description: p.description, tools: JSON.parse(p.tools), author: authorName(p),
      fileUrl: `/api/projects/${p.id}/file`, mime: p.mime, createdAt: p.created_at })));
  });
  api.get("/projects/:id/file", (req, res) => {
    const p = one("SELECT * FROM projects WHERE id = ?", req.params.id);
    const owner = req.user && (req.user.id === p?.user_id || req.user.role === "admin");
    const visible = p && p.status === "published" && (p.visibility === "public" || (p.visibility === "membres" && req.user));
    if (!p || !(owner || visible)) fail(404, "Fichier introuvable.");
    res.set("Cache-Control", "private, max-age=3600").type(p.mime).sendFile(path.join(config.storageDir, "projects", p.file));
  });
  api.post("/portfolio", needUser, needConsent, upload.single("file"), (req, res) => {
    const b = req.body || {};
    const title = text(b.title, { min: 3, max: 80, name: "Le titre" });
    const discipline = oneOf(b.discipline, DISCIPLINES, "Discipline");
    const description = text(b.description, { min: 20, max: 1200, name: "La description" });
    let visibility = oneOf(b.visibility, ["public", "membres", "prive"], "Visibilité");
    if (req.user.age_group === "mineur" && visibility === "public") visibility = "membres";
    let tools = [];
    try { tools = JSON.parse(b.tools || "[]").filter(t => typeof t === "string" && ID_RE.test(t)).slice(0, 12); } catch { /* outils ignorés */ }
    if (!req.file) fail(400, "Ajoute une image ou une vidéo.");
    const mime = sniff(req.file.buffer);
    if (!["image/png", "image/jpeg", "video/mp4"].includes(mime)) fail(400, "Format refusé : envoie une image JPG ou PNG, ou une vidéo MP4.");
    const id = uid(), file = id + { "image/png": ".png", "image/jpeg": ".jpg", "video/mp4": ".mp4" }[mime];
    fs.writeFileSync(path.join(config.storageDir, "projects", file), req.file.buffer);
    run("INSERT INTO projects(id, user_id, title, discipline, description, tools, visibility, file, mime, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
      id, req.user.id, title, discipline, description, JSON.stringify(tools), visibility, file, mime, now());
    res.status(201).json({ id, status: "pending" });
  });
  api.post("/reports", (req, res) => {
    rateLimit("report:" + ip(req), 10, 60 * 60000);
    const projectId = text(req.body?.projectId, { min: 1, max: 60, name: "Le projet" });
    const reason = oneOf(req.body?.reason, ["Contenu inapproprié", "Non-respect des droits d'auteur", "Données personnelles visibles", "Autre"], "Motif");
    run("INSERT INTO reports(id, project_id, reporter_id, reason, created_at) VALUES (?,?,?,?,?)", uid(), projectId, req.user?.id || null, reason, now());
    res.status(201).json({ ok: true });
  });
  api.post("/contact", async (req, res) => {
    rateLimit("contact:" + ip(req), 5, 60 * 60000);
    const name = text(req.body?.name, { min: 2, max: 40, name: "Le nom" }), mail = email(req.body?.email), message = text(req.body?.message, { min: 10, max: 2000, name: "Le message" });
    run("INSERT INTO messages VALUES (?,?,?,?,?)", uid(), name, mail, message, now());
    if (config.contactEmail) await sendMail({ to: config.contactEmail, subject: `Contact TOB-MAQ : ${name}`, text: `De : ${name} <${mail}>\n\n${message}` });
    res.status(201).json({ ok: true });
  });

  /* ---------------- Administration ---------------- */
  api.get("/admin/stats", needAdmin, (req, res) => res.json({
    users: one("SELECT COUNT(*) AS n FROM users").n, lessonsCompleted: one("SELECT COUNT(*) AS n FROM lessons").n,
    downloads: one("SELECT COUNT(*) AS n FROM downloads").n,
    aiGenerations: one("SELECT COUNT(*) AS n FROM ai_usage WHERE substr(at, 1, 7) = ?", today().slice(0, 7)).n,
    pendingProjects: one("SELECT COUNT(*) AS n FROM projects WHERE status = 'pending'").n, monthCostFcfa: monthCost()
  }));
  api.get("/admin/formations", needAdmin, (req, res) => res.json(all("SELECT lesson_id AS lessonId, COUNT(*) AS count FROM lessons GROUP BY lesson_id ORDER BY count DESC")));
  api.post("/admin/resources", needAdmin, upload.single("file"), (req, res) => {
    const title = text(req.body?.title, { min: 3, max: 120, name: "Le titre" }), licence = text(req.body?.licence, { min: 2, max: 120, name: "La licence" });
    if (!req.file) fail(400, "Ajoute un fichier.");
    const mime = sniff(req.file.buffer);
    if (!mime) fail(400, "Format refusé : PDF, ZIP, PNG, JPG ou MP4 uniquement.");
    const id = uid(), file = id + path.extname(req.file.originalname || "").toLowerCase().replace(/[^.a-z0-9]/g, "").slice(0, 6);
    fs.writeFileSync(path.join(config.storageDir, "uploads", file), req.file.buffer);
    run("INSERT INTO uploaded_resources(id, title, licence, file, original_name, mime, created_at) VALUES (?,?,?,?,?,?,?)", id, title, licence, file, String(req.file.originalname).slice(0, 200), mime, now());
    res.status(201).json({ id, published: false });
  });
  api.get("/admin/ai-config", needAdmin, (req, res) => res.json({ ...getAiSettings(), provider: imageProvider ? `Images : ${imageProvider}` : "aucun (OPENAI_API_KEY absent)", monthCostFcfa: monthCost() }));
  api.patch("/admin/ai-config", needAdmin, (req, res) => {
    const b = req.body || {}, int = (v, max) => { const n = Number(v); if (!Number.isInteger(n) || n < 0 || n > max) fail(400, "Valeur de quota invalide."); return n; };
    setAiSettings({ dailyImageQuota: int(b.dailyImageQuota, 500), dailyVideoQuota: int(b.dailyVideoQuota, 50), monthlyBudget: int(b.monthlyBudget, 100000000), imageEnabled: b.imageEnabled === true, videoEnabled: b.videoEnabled === true });
    res.json(getAiSettings());
  });
  api.get("/admin/reports", needAdmin, (req, res) => res.json(all(`SELECT r.*, COALESCE(p.title, r.project_id) AS project_title FROM reports r LEFT JOIN projects p ON p.id = r.project_id ORDER BY r.created_at DESC LIMIT 200`)
    .map(r => ({ id: r.id, projectId: r.project_id, projectTitle: r.project_title, reason: r.reason, status: r.status, createdAt: r.created_at }))));
  api.get("/admin/projects", needAdmin, (req, res) => {
    const status = oneOf(req.query.status || "pending", ["pending", "published", "rejected"], "Statut");
    res.json(all("SELECT p.*, u.display_name FROM projects p JOIN users u ON u.id = p.user_id WHERE p.status = ? ORDER BY p.created_at DESC LIMIT 200", status)
      .map(p => ({ id: p.id, title: p.title, discipline: p.discipline, author: p.display_name, visibility: p.visibility, fileUrl: `/api/projects/${p.id}/file`, mime: p.mime, createdAt: p.created_at })));
  });
  api.patch("/admin/projects/:id", needAdmin, (req, res) => {
    const status = oneOf(req.body?.status, ["published", "rejected"], "Statut");
    const r = run("UPDATE projects SET status = ? WHERE id = ?", status, req.params.id);
    if (!r.changes) fail(404, "Projet introuvable.");
    if (status === "rejected") run("UPDATE reports SET status = 'traité' WHERE project_id = ?", req.params.id);
    res.json({ id: req.params.id, status });
  });
  api.get("/admin/users", needAdmin, (req, res) => res.json(all("SELECT display_name, email, role, age_group, parent_consent_at, created_at FROM users ORDER BY created_at DESC LIMIT 500")
    .map(u => ({ displayName: u.display_name, email: u.email, role: u.role, ageGroup: u.age_group === "mineur" ? (u.parent_consent_at ? "15-17 (accord donné)" : "15-17 (accord en attente)") : "18+", createdAt: u.created_at }))));
  api.post("/admin/announcements", needAdmin, (req, res) => {
    run("INSERT INTO announcements VALUES (?,?,?,?)", uid(), text(req.body?.title, { min: 3, max: 100, name: "Le titre" }), text(req.body?.body, { min: 5, max: 1000, name: "Le texte" }), now());
    res.status(201).json({ ok: true });
  });
  api.get("/announcements", (req, res) => res.json(all("SELECT title, body, created_at AS createdAt FROM announcements ORDER BY created_at DESC LIMIT 5")));
  registerBilling(api, { needUser, needAdmin, needConsent });
  api.get("/health", (req, res) => res.json({ ok: true, ai: { images: Boolean(imageProvider), videos: Boolean(videoProvider) } }));

  api.use((req, res) => res.status(404).json({ message: "Route inconnue.", code: "NOT_FOUND" }));
  app.use("/api", api);

  /* ---------------- Site ---------------- */
  const indexPath = path.join(SITE_DIR, "index.html");
  const renderIndex = () => {
    const html = fs.readFileSync(indexPath, "utf8");
    const out = html.replace('API_BASE_URL: "",', 'API_BASE_URL: "/api",').replace('CONTACT_EMAIL: "",', `CONTACT_EMAIL: ${JSON.stringify(config.contactEmail)},`);
    if (out === html) throw new Error("index.html : impossible d'injecter l'adresse de l'API (CONFIG modifié ?).");
    return out;
  };
  renderIndex(); // vérification au démarrage
  app.get(["/", "/index.html"], (req, res) => res.set("Cache-Control", "no-cache").type("html").send(renderIndex()));
  app.use("/ressources", express.static(path.join(SITE_DIR, "ressources"), { maxAge: "7d", fallthrough: false }));
  app.use("/apercus", express.static(path.join(SITE_DIR, "apercus"), { maxAge: "7d", fallthrough: false }));
  app.use((req, res) => res.status(404).type("text").send("Page introuvable."));

  /* Erreurs : message clair pour l'utilisateur, détails seulement dans le journal. */
  app.use((err, req, res, next) => { // eslint-disable-line no-unused-vars
    if (err instanceof multer.MulterError) return res.status(err.code === "LIMIT_FILE_SIZE" ? 413 : 400).json({ message: err.code === "LIMIT_FILE_SIZE" ? `Fichier trop volumineux (${config.maxUploadMb} Mo maximum).` : "Envoi de fichier invalide.", code: err.code });
    if (err.type === "entity.parse.failed" || err.type === "entity.too.large") return res.status(400).json({ message: "Requête invalide.", code: "BAD_BODY" });
    if (err.status === 404 && !(err instanceof HttpError)) return res.status(404).type("text").send("Fichier introuvable.");
    if (err instanceof HttpError) return res.status(err.status).json({ message: err.message, code: err.code });
    console.error(new Date().toISOString(), req.method, req.originalUrl, err);
    res.status(500).json({ message: "Erreur interne du serveur. Réessaie plus tard.", code: "SERVER_ERROR" });
  });
  return app;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  createApp().listen(config.port, () => {
    console.log(`TOB-MAQ en ligne sur ${config.publicUrl} (port ${config.port})`);
    console.log(`IA images : ${imageProvider || "non configurée"} · e-mails : ${config.brevoKey ? "Brevo" : "affichés dans ce journal"} · admins : ${config.adminEmails.join(", ") || "aucun"}`);
  });
}
