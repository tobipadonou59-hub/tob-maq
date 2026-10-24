/* Connexion et inscription avec Google, Apple ou Facebook (OAuth 2.0 / OpenID Connect, code d'autorisation).
   - Les clés restent dans les variables d'environnement ; un fournisseur sans clés n'est pas proposé.
   - Le « state » est aléatoire, à usage unique et valable 10 minutes ; Google utilise aussi PKCE.
   - Un compte existant n'est relié automatiquement que si le fournisseur garantit l'adresse e-mail.
   - Une première inscription passe par une étape de finalisation (âge, conditions, accord parental). */
import crypto from "node:crypto";
import express from "express";
import { config } from "./config.js";
import { db, one, run, now } from "./db.js";
import { fail, newToken, sha256, rateLimit, email as cleanEmail } from "./security.js";

db.exec(`
CREATE TABLE IF NOT EXISTS oauth_accounts (
  provider TEXT NOT NULL, subject TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at TEXT NOT NULL,
  PRIMARY KEY (provider, subject));
CREATE TABLE IF NOT EXISTS oauth_states (state TEXT PRIMARY KEY, provider TEXT NOT NULL, verifier TEXT, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS oauth_pending (
  token_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, subject TEXT NOT NULL, email TEXT, email_verified INTEGER NOT NULL DEFAULT 0,
  name TEXT, expires_at INTEGER NOT NULL);
`);

const T = config.oauthTestBase;
const URLS = {
  google: { auth: "https://accounts.google.com/o/oauth2/v2/auth", token: "https://oauth2.googleapis.com/token", me: "https://openidconnect.googleapis.com/v1/userinfo" },
  facebook: { auth: "https://www.facebook.com/v19.0/dialog/oauth", token: "https://graph.facebook.com/v19.0/oauth/access_token", me: "https://graph.facebook.com/v19.0/me" },
  apple: { auth: "https://appleid.apple.com/auth/authorize", token: "https://appleid.apple.com/auth/token" }
};
const url = (p, k) => T ? `${T}/${p}/${k}` : URLS[p][k];
export const enabledProviders = () => [
  config.googleClientId && config.googleClientSecret && "google",
  config.appleClientId && config.appleTeamId && config.appleKeyId && config.applePrivateKey && "apple",
  config.facebookAppId && config.facebookAppSecret && "facebook"
].filter(Boolean);
const callbackUrl = p => `${config.publicUrl}/api/auth/oauth/${p}/callback`;
const b64url = buf => Buffer.from(buf).toString("base64url");
const decodeJwt = jwt => JSON.parse(Buffer.from(String(jwt).split(".")[1] || "", "base64url").toString("utf8") || "{}");

function appleClientSecret() {
  const iat = Math.floor(Date.now() / 1000);
  const head = b64url(JSON.stringify({ alg: "ES256", kid: config.appleKeyId }));
  const body = b64url(JSON.stringify({ iss: config.appleTeamId, iat, exp: iat + 300, aud: "https://appleid.apple.com", sub: config.appleClientId }));
  const sig = crypto.sign("sha256", Buffer.from(`${head}.${body}`), { key: config.applePrivateKey, dsaEncoding: "ieee-p1363" });
  return `${head}.${body}.${b64url(sig)}`;
}

async function getJson(res, what) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${what} : ${res.status} ${data.error_description || data.error?.message || data.error || ""}`);
  return data;
}

/* Échange du code contre l'identité vérifiée de la personne. */
async function identify(provider, code, verifier, extra) {
  if (provider === "google") {
    const tok = await getJson(await fetch(url("google", "token"), { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ code, client_id: config.googleClientId, client_secret: config.googleClientSecret, redirect_uri: callbackUrl("google"), grant_type: "authorization_code", code_verifier: verifier }) }), "Google (jeton)");
    const me = await getJson(await fetch(url("google", "me"), { headers: { Authorization: `Bearer ${tok.access_token}` } }), "Google (profil)");
    return { subject: String(me.sub), email: me.email, emailVerified: me.email_verified === true, name: me.given_name || me.name };
  }
  if (provider === "facebook") {
    const q = new URLSearchParams({ client_id: config.facebookAppId, client_secret: config.facebookAppSecret, redirect_uri: callbackUrl("facebook"), code });
    const tok = await getJson(await fetch(`${url("facebook", "token")}?${q}`), "Facebook (jeton)");
    const proof = crypto.createHmac("sha256", config.facebookAppSecret).update(tok.access_token).digest("hex");
    const me = await getJson(await fetch(`${url("facebook", "me")}?${new URLSearchParams({ fields: "id,first_name,name,email", access_token: tok.access_token, appsecret_proof: proof })}`), "Facebook (profil)");
    return { subject: String(me.id), email: me.email, emailVerified: Boolean(me.email), name: me.first_name || me.name };
  }
  if (provider === "apple") {
    const tok = await getJson(await fetch(url("apple", "token"), { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ code, client_id: config.appleClientId, client_secret: appleClientSecret(), redirect_uri: callbackUrl("apple"), grant_type: "authorization_code" }) }), "Apple (jeton)");
    // Jeton reçu directement d'Apple (connexion TLS authentifiée par notre secret) : on contrôle émetteur, audience et validité.
    const id = decodeJwt(tok.id_token);
    if ((!T && id.iss !== "https://appleid.apple.com") || id.aud !== config.appleClientId || !(id.exp * 1000 > Date.now())) throw new Error("Apple : jeton d'identité invalide");
    let name = ""; try { const u = JSON.parse(extra.user || "{}"); name = u.name?.firstName || ""; } catch { /* nom absent après la première connexion */ }
    return { subject: String(id.sub), email: id.email, emailVerified: id.email_verified === true || id.email_verified === "true", name };
  }
  throw new Error("Fournisseur inconnu");
}

export function registerOAuth(app, api, { openSession, createAccount, signupProfile, cleanName, publicUser }) {
  api.get("/auth/providers", (req, res) => res.json(enabledProviders()));

  app.get("/api/auth/oauth/:provider/start", (req, res) => {
    const p = req.params.provider;
    if (!enabledProviders().includes(p)) return res.redirect(303, "/#/connexion?erreur=fournisseur");
    rateLimit("oauth:" + (req.ip || ""), 30, 600000);
    run("DELETE FROM oauth_states WHERE expires_at < ?", Date.now());
    const state = newToken(), verifier = p === "google" ? newToken() : null;
    run("INSERT INTO oauth_states(state, provider, verifier, expires_at) VALUES (?,?,?,?)", state, p, verifier, Date.now() + 600000);
    const q = { google: { client_id: config.googleClientId, response_type: "code", scope: "openid email profile", prompt: "select_account",
                          code_challenge: verifier && b64url(crypto.createHash("sha256").update(verifier).digest()), code_challenge_method: "S256" },
                facebook: { client_id: config.facebookAppId, response_type: "code", scope: "email,public_profile" },
                apple: { client_id: config.appleClientId, response_type: "code", scope: "name email", response_mode: "form_post" } }[p];
    res.redirect(303, `${url(p, "auth")}?${new URLSearchParams({ ...q, redirect_uri: callbackUrl(p), state })}`);
  });

  // Apple renvoie un formulaire POST depuis son domaine : cette route est volontairement hors du contrôle d'origine de l'API.
  const callback = async (req, res) => {
    const p = req.params.provider, b = { ...req.query, ...(req.body || {}) };
    const back = code => res.redirect(303, `/#/connexion?erreur=${code}`);
    if (!enabledProviders().includes(p)) return back("fournisseur");
    if (b.error) return back("annule");
    const st = typeof b.state === "string" ? one("SELECT * FROM oauth_states WHERE state = ?", b.state) : null;
    if (st) run("DELETE FROM oauth_states WHERE state = ?", b.state);
    if (!st || st.provider !== p || st.expires_at < Date.now() || typeof b.code !== "string") return back("session");
    let who;
    try { who = await identify(p, b.code, st.verifier, b); }
    catch (e) { console.error(new Date().toISOString(), "OAuth", p, e.message); return back("fournisseur"); }
    const mail = who.email ? String(who.email).trim().toLowerCase() : null;
    // 1. Compte déjà relié à ce fournisseur
    const linked = one("SELECT user_id FROM oauth_accounts WHERE provider = ? AND subject = ?", p, who.subject);
    let userId = linked?.user_id;
    // 2. Compte existant avec la même adresse, garantie par le fournisseur
    if (!userId && mail && who.emailVerified) {
      const u = one("SELECT id FROM users WHERE email = ?", mail);
      if (u) { userId = u.id; run("INSERT OR IGNORE INTO oauth_accounts(provider, subject, user_id, created_at) VALUES (?,?,?,?)", p, who.subject, u.id, now()); }
    }
    if (userId) {
      const u = one("SELECT * FROM users WHERE id = ?", userId);
      if (u.role !== "admin" && config.adminEmails.includes(u.email)) run("UPDATE users SET role = 'admin' WHERE id = ?", u.id);
      openSession(req, res, userId);
      return res.redirect(303, "/#/tableau-de-bord");
    }
    // 3. Nouvelle personne : finalisation de l'inscription
    const t = newToken();
    run("DELETE FROM oauth_pending WHERE expires_at < ?", Date.now());
    run("INSERT INTO oauth_pending(token_hash, provider, subject, email, email_verified, name, expires_at) VALUES (?,?,?,?,?,?,?)",
      sha256(t), p, who.subject, mail, who.emailVerified ? 1 : 0, (who.name || "").slice(0, 30), Date.now() + 30 * 60000);
    res.redirect(303, `/#/finaliser-inscription?jeton=${t}`);
  };
  app.get("/api/auth/oauth/:provider/callback", callback);
  app.post("/api/auth/oauth/:provider/callback", express.urlencoded({ extended: false, limit: "8kb" }), callback);

  const pending = t => { const row = typeof t === "string" && t.length < 100 ? one("SELECT * FROM oauth_pending WHERE token_hash = ?", sha256(t)) : null; return row && row.expires_at > Date.now() ? row : null; };
  api.get("/auth/oauth/pending", (req, res) => {
    const row = pending(req.query.jeton);
    if (!row) fail(410, "Cette demande d'inscription a expiré. Recommence la connexion.", "EXPIRED");
    res.json({ provider: row.provider, email: row.email, emailLocked: Boolean(row.email && row.email_verified), name: row.name || "" });
  });
  api.post("/auth/oauth/complete", async (req, res) => {
    rateLimit("register:" + (req.ip || ""), 10, 15 * 60000);
    const b = req.body || {}, row = pending(b.jeton);
    if (!row) fail(410, "Cette demande d'inscription a expiré. Recommence la connexion.", "EXPIRED");
    const mail = row.email && row.email_verified ? row.email : cleanEmail(b.email);
    const displayName = cleanName(b.displayName || row.name);
    const profile = signupProfile(b, mail);
    // Mot de passe inutilisable : la personne se connecte avec son fournisseur (ou en choisit un via « mot de passe oublié »).
    const id = await createAccount({ displayName, mail, passwordHash: "oauth", ...profile });
    run("INSERT INTO oauth_accounts(provider, subject, user_id, created_at) VALUES (?,?,?,?)", row.provider, row.subject, id, now());
    run("DELETE FROM oauth_pending WHERE token_hash = ?", row.token_hash);
    openSession(req, res, id);
    res.status(201).json({ user: publicUser(one("SELECT * FROM users WHERE id = ?", id)) });
  });
}
