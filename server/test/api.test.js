/* Tests d'intégration de l'API (node --test). Base temporaire, aucune clé d'IA. */
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const storage = fs.mkdtempSync(path.join(os.tmpdir(), "tobmaq-test-"));
process.env.STORAGE_DIR = storage;
process.env.ADMIN_EMAILS = "admin@tob-maq.test";
process.env.PUBLIC_URL = "http://localhost";
delete process.env.OPENAI_API_KEY;
delete process.env.BREVO_API_KEY;

const { createApp } = await import("../src/index.js");
const { one } = await import("../src/db.js");
const { sha256 } = await import("../src/security.js");
let server, base;

/* Petit client qui garde le cookie de session, comme un navigateur. */
function client() {
  let cookie = "";
  return async (method, url, body, { form, origin } = {}) => {
    const headers = { Accept: "application/json" };
    if (cookie) headers.Cookie = cookie;
    if (origin) headers.Origin = origin;
    if (body && !form) headers["Content-Type"] = "application/json";
    const res = await fetch(base + url, { method, headers, body: form || (body ? JSON.stringify(body) : undefined), redirect: "manual" });
    const set = res.headers.get("set-cookie");
    if (set) cookie = set.split(";")[0];
    const ct = res.headers.get("content-type") || "";
    return { status: res.status, data: ct.includes("json") ? await res.json() : await res.text(), headers: res.headers };
  };
}
const adult = { displayName: "Kofi", email: "kofi@exemple.bj", password: "motdepasse12", interests: ["video"], level: "Débutant", ageGroup: "adulte", acceptTerms: true };
const PNG = Buffer.from("89504e470d0a1a0a0000000d4948445200000001000000010806000000" + "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082", "hex");

before(() => new Promise(ok => { server = createApp().listen(0, () => { base = `http://127.0.0.1:${server.address().port}`; ok(); }); }));
after(() => { server.close(); fs.rmSync(storage, { recursive: true, force: true }); });

test("le site est servi avec l'adresse de l'API injectée et des en-têtes de sécurité", async () => {
  const r = await client()("GET", "/");
  assert.equal(r.status, 200);
  assert.match(r.data, /API_BASE_URL: "\/api"/);
  assert.match(r.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  assert.equal((await client()("GET", "/ressources/tobmaq-checklist-impression.pdf")).status, 200);
  assert.equal((await client()("GET", "/server/src/config.js")).status, 404, "le code du serveur n'est jamais exposé");
});

test("application installable : manifeste, service worker et icônes", async () => {
  const m = await client()("GET", "/manifest.webmanifest");
  assert.equal(m.status, 200);
  assert.match(m.headers.get("content-type"), /application\/manifest\+json/);
  const manifest = typeof m.data === "string" ? JSON.parse(m.data) : m.data;
  for (const i of [...manifest.icons, ...manifest.screenshots]) assert.equal((await client()("GET", i.src)).status, 200, i.src);
  const sw = await client()("GET", "/sw.js");
  assert.equal(sw.status, 200);
  assert.equal(sw.headers.get("service-worker-allowed"), "/");
});

test("inscription, session, déconnexion et connexion", async () => {
  const c = client();
  assert.equal((await c("GET", "/api/auth/me")).status, 401);
  const r = await c("POST", "/api/auth/register", adult);
  assert.equal(r.status, 201);
  assert.equal(r.data.user.displayName, "Kofi");
  assert.equal(r.data.user.role, "membre");
  assert.equal((await c("GET", "/api/auth/me")).data.user.email, "kofi@exemple.bj");
  const stored = one("SELECT password_hash FROM users WHERE email = ?", "kofi@exemple.bj").password_hash;
  assert.match(stored, /^scrypt\$/); assert.ok(!stored.includes("motdepasse12"), "mot de passe jamais stocké en clair");
  assert.equal((await c("POST", "/api/auth/register", adult)).status, 409);
  assert.equal((await c("POST", "/api/auth/logout")).status, 204);
  assert.equal((await c("GET", "/api/auth/me")).status, 401);
  assert.equal((await c("POST", "/api/auth/login", { email: "kofi@exemple.bj", password: "mauvais123" })).status, 401);
  assert.equal((await c("POST", "/api/auth/login", { email: "KOFI@exemple.bj", password: "motdepasse12" })).status, 200);
});

test("validation des entrées et refus des moins de 15 ans", async () => {
  const c = client();
  assert.equal((await c("POST", "/api/auth/register", { ...adult, email: "a@b.bj", password: "court" })).status, 400);
  assert.equal((await c("POST", "/api/auth/register", { ...adult, email: "b@b.bj", ageGroup: "moins15" })).status, 400);
  assert.equal((await c("POST", "/api/auth/register", { ...adult, email: "c@b.bj", displayName: "<script>" })).status, 400);
  assert.equal((await c("POST", "/api/auth/register", { ...adult, email: "d@b.bj", acceptTerms: false })).status, 400);
});

test("protection CSRF : une autre origine ne peut pas agir", async () => {
  const r = await client()("POST", "/api/auth/login", { email: "kofi@exemple.bj", password: "motdepasse12" }, { origin: "https://site-pirate.example" });
  assert.equal(r.status, 403);
});

test("progression : leçons, jeux (meilleur score conservé), favoris, import", async () => {
  const c = client();
  await c("POST", "/api/auth/login", { email: "kofi@exemple.bj", password: "motdepasse12" });
  assert.equal((await c("POST", "/api/me/lessons", { lessonId: "dr-etalonnage", done: true })).status, 204);
  await c("POST", "/api/me/games", { gameId: "rythme", level: "moyen", points: 900 });
  await c("POST", "/api/me/games", { gameId: "rythme", level: "moyen", points: 300 });
  await c("POST", "/api/me/favorites", { resourceId: "res-grille", favorite: true });
  const imp = await c("POST", "/api/me/progress/import", { lessonsDone: { "id-grille": "2026-10-01T00:00:00.000Z" }, games: { contraste: { best: { facile: 400 }, plays: 3 } }, favorites: ["res-brief"] });
  assert.deepEqual(Object.keys(imp.data.lessonsDone).sort(), ["dr-etalonnage", "id-grille"]);
  assert.equal(imp.data.games.rythme.best.moyen, 900);
  assert.equal(imp.data.games.rythme.plays, 2);
  assert.equal(imp.data.games.contraste.best.facile, 400);
  assert.equal(imp.data.games.contraste.plays, 3);
  assert.deepEqual(imp.data.favorites.sort(), ["res-brief", "res-grille"]);
  assert.equal((await c("POST", "/api/me/games", { gameId: "rythme", level: "expert", points: 1 })).status, 400);
});

test("mineur : accord parental requis avant l'IA et le portfolio", async () => {
  const c = client();
  const r = await c("POST", "/api/auth/register", { ...adult, displayName: "Afi", email: "afi@exemple.bj", ageGroup: "mineur", parentEmail: "parent@exemple.bj" });
  assert.equal(r.status, 201);
  assert.equal(r.data.user.pendingParentalConsent, true);
  assert.equal((await c("POST", "/api/ai/images", { prompt: "Une affiche de concert", style: "Cinématique", size: "square", usage: "Affiche" })).data.code, "CONSENT_PENDING");
  // Le parent reçoit un lien : on simule l'ouverture du lien avec un jeton créé comme le ferait l'e-mail.
  const uid = one("SELECT id FROM users WHERE email = 'afi@exemple.bj'").id;
  const { newToken } = await import("../src/security.js");
  const { run } = await import("../src/db.js");
  const t = newToken();
  run("INSERT INTO tokens(token_hash, user_id, kind, expires_at) VALUES (?,?,?,?)", sha256(t), uid, "consent", Date.now() + 3600e3);
  const pageConsent = await client()("GET", "/api/auth/parent-consent?token=" + t);
  assert.match(pageConsent.data, /Je donne mon accord/);
  const form = new URLSearchParams({ token: t });
  const ok = await fetch(base + "/api/auth/parent-consent", { method: "POST", body: form });
  assert.equal(ok.status, 200);
  assert.equal((await c("GET", "/api/auth/me")).data.user.pendingParentalConsent, false);
});

test("IA : sans clé, message clair et aucune génération simulée", async () => {
  const c = client();
  await c("POST", "/api/auth/login", { email: "kofi@exemple.bj", password: "motdepasse12" });
  const cfg = await c("GET", "/api/ai/config");
  assert.equal(cfg.data.image.enabled, false);
  assert.equal(cfg.data.quota.images.limit, 5);
  const r = await c("POST", "/api/ai/images", { prompt: "Une affiche de concert", style: "Cinématique", size: "square", usage: "Affiche" });
  assert.equal(r.status, 503); assert.equal(r.data.code, "AI_NOT_CONFIGURED");
  assert.equal((await c("POST", "/api/ai/videos", { prompt: "x" })).status, 503);
  assert.equal(one("SELECT COUNT(*) AS n FROM ai_usage").n, 0);
});

test("portfolio : envoi, modération par l'admin, publication et confidentialité des mineurs", async () => {
  const kofi = client(), afi = client(), admin = client(), visiteur = client();
  await kofi("POST", "/api/auth/login", { email: "kofi@exemple.bj", password: "motdepasse12" });
  await afi("POST", "/api/auth/login", { email: "afi@exemple.bj", password: "motdepasse12" });
  const send = (c, vis, buf = PNG) => { const f = new FormData(); f.append("title", "Mon affiche"); f.append("discipline", "Affiches"); f.append("description", "Une affiche de concert réalisée avec Illustrator."); f.append("tools", '["illustrator"]'); f.append("visibility", vis); f.append("file", new Blob([buf]), "a.png"); return c("POST", "/api/portfolio", null, { form: f }); };
  assert.equal((await send(kofi, "public", Buffer.from("pas une image"))).status, 400, "faux fichier refusé");
  const p1 = await send(kofi, "public"), p2 = await send(afi, "public");
  assert.equal(p1.status, 201); assert.equal(p2.status, 201);
  assert.equal(one("SELECT visibility FROM projects WHERE id = ?", p2.data.id).visibility, "membres", "un mineur ne publie jamais en public");
  assert.equal((await visiteur("GET", "/api/portfolio")).data.length, 0, "rien n'est visible avant modération");
  assert.equal((await kofi("GET", "/api/admin/projects")).status, 403);
  for (const path of ["/api/admin/stats", "/api/admin/users", "/api/admin/payments", "/api/admin/billing", "/api/admin/ai-config"]) {
    assert.equal((await kofi("GET", path)).status, 403, path + " refusé à un membre");
    assert.equal((await visiteur("GET", path)).status, 401, path + " refusé à un visiteur");
  }
  const ar = await admin("POST", "/api/auth/register", { ...adult, displayName: "Admin", email: "admin@tob-maq.test" });
  assert.equal(ar.data.user.role, "admin");
  const pending = await admin("GET", "/api/admin/projects?status=pending");
  assert.equal(pending.data.length, 2);
  for (const p of pending.data) assert.equal((await admin("PATCH", `/api/admin/projects/${p.id}`, { status: "published" })).status, 200);
  assert.equal((await visiteur("GET", "/api/portfolio")).data.length, 1, "un visiteur ne voit que les projets publics");
  const membres = await kofi("GET", "/api/portfolio");
  assert.equal(membres.data.length, 2);
  assert.ok(membres.data.some(p => p.author === "Apprenant TOB-MAQ"), "le nom d'un mineur n'est jamais affiché");
  assert.equal((await visiteur("GET", `/api/projects/${p2.data.id}/file`)).status, 404);
  assert.equal((await kofi("GET", `/api/projects/${p2.data.id}/file`)).status, 200);
  const stats = await admin("GET", "/api/admin/stats");
  assert.equal(stats.data.users, 3);
  assert.equal(stats.data.series.months.length, 6);
  assert.equal(stats.data.learners + stats.data.admins, 3);
  assert.equal(typeof stats.data.revenueTotal, "number");
  const q = await admin("PATCH", "/api/admin/ai-config", { dailyImageQuota: 10, dailyVideoQuota: 0, monthlyBudget: 20000, imageEnabled: true, videoEnabled: false });
  assert.equal(q.data.dailyImageQuota, 10);
  assert.equal((await admin("POST", "/api/reports", { projectId: p1.data.id, reason: "Autre" })).status, 201);
  assert.equal((await admin("GET", "/api/admin/reports")).data[0].projectTitle, "Mon affiche");
});

test("mot de passe oublié : même réponse, puis réinitialisation par jeton", async () => {
  const c = client();
  assert.equal((await c("POST", "/api/auth/forgot-password", { email: "inconnu@exemple.bj" })).status, 204);
  assert.equal((await c("POST", "/api/auth/forgot-password", { email: "kofi@exemple.bj" })).status, 204);
  const { newToken } = await import("../src/security.js");
  const { run } = await import("../src/db.js");
  const uid = one("SELECT id FROM users WHERE email = 'kofi@exemple.bj'").id, t = newToken();
  run("INSERT INTO tokens(token_hash, user_id, kind, expires_at) VALUES (?,?,?,?)", sha256(t), uid, "reset", Date.now() + 3600e3);
  assert.equal((await c("POST", "/api/auth/reset-password", { token: t, password: "nouveaumdp34" })).status, 204);
  assert.equal((await c("POST", "/api/auth/reset-password", { token: t, password: "nouveaumdp34" })).status, 400, "jeton à usage unique");
  assert.equal((await c("POST", "/api/auth/login", { email: "kofi@exemple.bj", password: "nouveaumdp34" })).status, 200);
});

test("limitation des tentatives de connexion", async () => {
  const c = client();
  let last;
  for (let i = 0; i < 9; i++) last = await c("POST", "/api/auth/login", { email: "cible@exemple.bj", password: "essai12345" });
  assert.equal(last.status, 429);
});

test("une adresse ajoutée à ADMIN_EMAILS après l'inscription devient administrateur à la connexion", async () => {
  const { config } = await import("../src/config.js");
  const c = client();
  await c("POST", "/api/auth/register", { ...adult, displayName: "Tardif", email: "tardif@exemple.bj" });
  assert.equal((await c("GET", "/api/auth/me")).data.user.role, "membre");
  config.adminEmails.push("tardif@exemple.bj");
  assert.equal((await c("GET", "/api/auth/me")).data.user.role, "admin");
  assert.equal((await c("GET", "/api/admin/stats")).status, 200);
});

test("validation Google : le code est extrait même si la balise complète est collée", async () => {
  const { googleVerificationTag } = await import("../src/index.js");
  const attendu = '<meta name="google-site-verification" content="AbC-12_xY">';
  assert.equal(googleVerificationTag("AbC-12_xY"), attendu);
  assert.equal(googleVerificationTag(' "AbC-12_xY" '), attendu);
  assert.equal(googleVerificationTag('<meta name="google-site-verification" content="AbC-12_xY" />'), attendu);
  assert.equal(googleVerificationTag("content='AbC-12_xY'"), attendu);
  assert.equal(googleVerificationTag(""), "");
});

test("appli Android : empreintes de certificat filtrées et assetlinks absent sans configuration", async () => {
  const { androidFingerprints } = await import("../src/index.js");
  const fp = Array.from({ length: 32 }, (_, i) => (i * 7 % 256).toString(16).padStart(2, "0")).join(":");
  assert.deepEqual(androidFingerprints(` ${fp}, n'importe quoi `), [fp.toUpperCase()]);
  assert.deepEqual(androidFingerprints(""), []);
  assert.equal((await client()("GET", "/.well-known/assetlinks.json")).status, 404);
});
