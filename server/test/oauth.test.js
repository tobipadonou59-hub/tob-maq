/* Connexion avec Google, Apple et Facebook : parcours complet avec un faux fournisseur local. */
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import crypto from "node:crypto";

// Faux fournisseur OAuth (jetons et profils)
let gProfile = { sub: "g-123", email: "Ama@Gmail.com", email_verified: true, given_name: "Ama" };
const jwt = p => ["e30", Buffer.from(JSON.stringify(p)).toString("base64url"), "sig"].join(".");
const provider = http.createServer((req, res) => {
  const send = o => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(o)); };
  if (req.url.startsWith("/google/token")) return send({ access_token: "g-tok" });
  if (req.url.startsWith("/google/me")) return send(gProfile);
  if (req.url.startsWith("/facebook/token")) return send({ access_token: "fb-tok" });
  if (req.url.startsWith("/facebook/me")) return send({ id: "fb-77", first_name: "Koffi" }); // sans e-mail
  if (req.url.startsWith("/apple/token")) return send({ id_token: jwt({ iss: "test", aud: "bj.tobmaq.web", sub: "ap-9", email: "sena@privaterelay.appleid.com", email_verified: "true", exp: Math.floor(Date.now() / 1000) + 600 }) });
  res.statusCode = 404; res.end();
});
await new Promise(ok => provider.listen(0, ok));

const storage = fs.mkdtempSync(path.join(os.tmpdir(), "tobmaq-oauth-"));
Object.assign(process.env, {
  STORAGE_DIR: storage, PUBLIC_URL: "http://localhost", ADMIN_EMAILS: "", OAUTH_TEST_BASE: `http://127.0.0.1:${provider.address().port}`,
  GOOGLE_CLIENT_ID: "g-id", GOOGLE_CLIENT_SECRET: "g-secret", FACEBOOK_APP_ID: "fb-id", FACEBOOK_APP_SECRET: "fb-secret",
  APPLE_CLIENT_ID: "bj.tobmaq.web", APPLE_TEAM_ID: "TEAM123", APPLE_KEY_ID: "KEY123",
  APPLE_PRIVATE_KEY: crypto.generateKeyPairSync("ec", { namedCurve: "P-256" }).privateKey.export({ type: "pkcs8", format: "pem" }).replace(/\n/g, "\\n")
});
const { createApp } = await import("../src/index.js");
let server, base;
before(() => new Promise(ok => { server = createApp().listen(0, () => { base = `http://127.0.0.1:${server.address().port}`; ok(); }); }));
after(() => { server.close(); provider.close(); fs.rmSync(storage, { recursive: true, force: true }); });

function client() {
  let cookie = "";
  return async (method, url, { body, form, headers = {} } = {}) => {
    const h = { ...headers }; if (cookie) h.Cookie = cookie;
    if (body) h["Content-Type"] = "application/json";
    if (form) h["Content-Type"] = "application/x-www-form-urlencoded";
    const res = await fetch(base + url, { method, headers: h, body: body ? JSON.stringify(body) : form ? new URLSearchParams(form) : undefined, redirect: "manual" });
    const set = res.headers.get("set-cookie"); if (set) cookie = set.split(";")[0];
    const ct = res.headers.get("content-type") || "";
    return { status: res.status, location: res.headers.get("location"), data: ct.includes("json") ? await res.json() : await res.text() };
  };
}
const profile = { ageGroup: "adulte", acceptTerms: true, level: "Débutant", interests: ["video"] };
const start = async (c, p) => { const r = await c("GET", `/api/auth/oauth/${p}/start`); assert.equal(r.status, 303); return new URL(r.location); };

test("les trois fournisseurs configurés sont proposés", async () => {
  assert.deepEqual((await client()("GET", "/api/auth/providers")).data.sort(), ["apple", "facebook", "google"]);
});

test("Google : inscription finalisée, puis connexion directe ; state à usage unique", async () => {
  const c = client(), auth = await start(c, "google");
  assert.ok(auth.searchParams.get("code_challenge"), "PKCE");
  assert.equal(auth.searchParams.get("redirect_uri"), "http://localhost/api/auth/oauth/google/callback");
  const state = auth.searchParams.get("state");
  const cb = await c("GET", `/api/auth/oauth/google/callback?code=abc&state=${state}`);
  assert.match(cb.location, /^\/#\/finaliser-inscription\?jeton=/);
  assert.equal((await c("GET", `/api/auth/oauth/google/callback?code=abc&state=${state}`)).location, "/#/connexion?erreur=session", "state rejoué refusé");
  const jeton = cb.location.split("jeton=")[1];
  const pend = await c("GET", `/api/auth/oauth/pending?jeton=${jeton}`);
  assert.equal(pend.data.email, "ama@gmail.com"); assert.equal(pend.data.emailLocked, true); assert.equal(pend.data.name, "Ama");
  assert.equal((await c("POST", "/api/auth/oauth/complete", { body: { jeton, ...profile, ageGroup: "moins15" } })).status, 400, "moins de 15 ans refusé");
  const done = await c("POST", "/api/auth/oauth/complete", { body: { jeton, displayName: "Ama", ...profile, email: "pirate@exemple.bj" } });
  assert.equal(done.status, 201); assert.equal(done.data.user.email, "ama@gmail.com", "l'e-mail garanti par Google ne peut pas être remplacé");
  assert.equal((await c("GET", "/api/auth/me")).data.user.displayName, "Ama");
  // Deuxième fois : connexion directe
  const c2 = client(), s2 = (await start(c2, "google")).searchParams.get("state");
  const cb2 = await c2("GET", `/api/auth/oauth/google/callback?code=x&state=${s2}`);
  assert.equal(cb2.location, "/#/tableau-de-bord");
  assert.equal((await c2("GET", "/api/auth/me")).data.user.email, "ama@gmail.com");
  // Pas de connexion par mot de passe sur un compte créé avec Google
  assert.equal((await client()("POST", "/api/auth/login", { body: { email: "ama@gmail.com", password: "oauth" } })).status, 401);
});

test("Facebook sans e-mail : l'adresse est demandée et ne peut pas reprendre un compte existant", async () => {
  const owner = client();
  await owner("POST", "/api/auth/register", { body: { displayName: "Proprio", email: "deja@exemple.bj", password: "motdepasse12", ...profile } });
  const c = client(), state = (await start(c, "facebook")).searchParams.get("state");
  const jeton = (await c("GET", `/api/auth/oauth/facebook/callback?code=f&state=${state}`)).location.split("jeton=")[1];
  assert.equal((await c("GET", `/api/auth/oauth/pending?jeton=${jeton}`)).data.emailLocked, false);
  assert.equal((await c("POST", "/api/auth/oauth/complete", { body: { jeton, displayName: "Koffi", email: "deja@exemple.bj", ...profile } })).status, 409);
  assert.equal((await c("POST", "/api/auth/oauth/complete", { body: { jeton, displayName: "Koffi", email: "koffi@exemple.bj", ...profile } })).status, 201);
});

test("Apple : retour en formulaire POST depuis le domaine d'Apple accepté, prénom transmis", async () => {
  const c = client(), auth = await start(c, "apple");
  assert.equal(auth.searchParams.get("response_mode"), "form_post");
  const cb = await c("POST", "/api/auth/oauth/apple/callback", { form: { code: "a", state: auth.searchParams.get("state"), user: JSON.stringify({ name: { firstName: "Séna" } }) }, headers: { Origin: "https://appleid.apple.com" } });
  assert.match(cb.location, /finaliser-inscription/);
  const jeton = cb.location.split("jeton=")[1];
  assert.equal((await c("GET", `/api/auth/oauth/pending?jeton=${jeton}`)).data.name, "Séna");
  assert.equal((await c("POST", "/api/auth/oauth/complete", { body: { jeton, displayName: "Séna", ...profile } })).status, 201);
});

test("un compte existant est relié quand le fournisseur garantit la même adresse", async () => {
  await client()("POST", "/api/auth/register", { body: { displayName: "Mawu", email: "mawu@exemple.bj", password: "motdepasse12", ...profile } });
  gProfile = { sub: "g-456", email: "mawu@exemple.bj", email_verified: true, given_name: "Mawu" };
  const c = client(), state = (await start(c, "google")).searchParams.get("state");
  assert.equal((await c("GET", `/api/auth/oauth/google/callback?code=m&state=${state}`)).location, "/#/tableau-de-bord");
  assert.equal((await c("GET", "/api/auth/me")).data.user.email, "mawu@exemple.bj");
  // Adresse NON vérifiée : pas de rattachement automatique
  gProfile = { sub: "g-789", email: "mawu@exemple.bj", email_verified: false, given_name: "Intrus" };
  const c2 = client(), s2 = (await start(c2, "google")).searchParams.get("state");
  assert.match((await c2("GET", `/api/auth/oauth/google/callback?code=n&state=${s2}`)).location, /finaliser-inscription/);
});
