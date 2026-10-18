/* Parcours complet : webhook signé -> Claude (imité) -> règles -> envoi WhatsApp (imité). */
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "assistant-wa-"));
Object.assign(process.env, {
  STORAGE_DIR: dir, DELAI_REGROUPEMENT_MS: "0", WHATSAPP_APP_SECRET: "secret-app", WHATSAPP_VERIFY_TOKEN: "verif",
  WHATSAPP_TOKEN: "jeton-wa", WHATSAPP_PHONE_NUMBER_ID: "123", ADMIN_TOKEN: "a".repeat(32), RACCOURCI_TOKEN: "r".repeat(32), TZ: "UTC"
});
const { createApp } = await import("../src/index.js");
const { setClaudeClient } = await import("../src/claude.js");
const { setSetting, getRules } = await import("../src/db.js");

let analyse, appelsClaude = 0;
setClaudeClient({ beta: { messages: { create: async params => {
  appelsClaude++;
  assert.ok(!JSON.stringify(params).includes("22990000001"), "le numéro du contact ne doit pas être envoyé à Claude");
  return { stop_reason: "end_turn", content: [{ type: "thinking", thinking: "" }, { type: "text", text: JSON.stringify(analyse) }] };
} } } });

const envois = [], vraiFetch = globalThis.fetch;
globalThis.fetch = async (url, opts) => {
  if (String(url).startsWith("https://graph.facebook.com/")) { envois.push(JSON.parse(opts.body)); return new Response(JSON.stringify({ messages: [{ id: "wamid.envoi" + envois.length }] })); }
  return vraiFetch(url, opts);
};

let server, base;
before(async () => { server = createApp().listen(0); await new Promise(r => server.once("listening", r)); base = `http://127.0.0.1:${server.address().port}`; });
after(() => { server.close(); globalThis.fetch = vraiFetch; });

const corps = (id, texte, from = "22990000001") => JSON.stringify({ entry: [{ changes: [{ field: "messages", value: {
  metadata: { display_phone_number: "22900000000" }, contacts: [{ wa_id: from, profile: { name: "Awa" } }],
  messages: [{ id, from, timestamp: String(Math.floor(Date.now() / 1000)), type: "text", text: { body: texte } }] } }] }] });
const signer = b => "sha256=" + crypto.createHmac("sha256", "secret-app").update(b).digest("hex");
const webhook = (b, sig = signer(b)) => fetch(base + "/webhook", { method: "POST", headers: { "Content-Type": "application/json", "X-Hub-Signature-256": sig }, body: b });
const admin = (chemin, opts = {}) => fetch(base + "/api/admin" + chemin, { ...opts, headers: { "Content-Type": "application/json", Authorization: "Bearer " + "a".repeat(32) } }).then(r => r.json());
const attendre = () => new Promise(r => setTimeout(r, 100));
const simple = { categorie: "salutation", langue: "fr", ton_du_message: "amical", sensible: false, raison: "Salutation.", contexte_suffisant: true, besoin_info_proprietaire: false, confiance: 0.95, reponse: "Salut Awa, ça va ?", resume: "Dit bonjour." };

test("vérification du webhook par Meta", async () => {
  assert.equal(await (await fetch(base + "/webhook?hub.mode=subscribe&hub.verify_token=verif&hub.challenge=42")).text(), "42");
  assert.equal((await fetch(base + "/webhook?hub.mode=subscribe&hub.verify_token=faux&hub.challenge=42")).status, 403);
});

test("signature invalide refusée", async () => {
  assert.equal((await webhook(corps("m0", "Salut"), "sha256=00")).status, 401);
});

test("mode suggestion par défaut : rien n'est envoyé", async () => {
  analyse = simple;
  assert.equal((await webhook(corps("m1", "Salut"))).status, 200);
  await attendre();
  const e = await admin("/etat");
  assert.equal(e.mode, "suggestion");
  assert.equal(e.enAttente[0].statut, "suggestion");
  assert.equal(envois.length, 0);
});

test("validation manuelle : envoi une seule fois", async () => {
  const id = (await admin("/etat")).enAttente[0].id;
  assert.deepEqual(await admin(`/brouillons/${id}/envoyer`, { method: "POST", body: JSON.stringify({ texte: "Salut Awa !" }) }), { ok: true });
  assert.equal(envois.at(-1).text.body, "Salut Awa !");
  assert.equal(envois.at(-1).to, "22990000001");
  const encore = await admin(`/brouillons/${id}/envoyer`, { method: "POST", body: "{}" });
  assert.match(encore.erreur, /déjà/);
  assert.equal(envois.length, 1);
});

test("mode automatique : message simple envoyé, doublon Meta ignoré, sujet sensible retenu", async () => {
  await admin("/mode", { method: "POST", body: JSON.stringify({ mode: "automatique" }) });
  setSetting("regles", { ...getRules(), heures_automatiques: null });
  analyse = { ...simple, reponse: "Coucou, ça roule ?" };
  const avant = appelsClaude;
  await webhook(corps("m2", "Coucou")); await webhook(corps("m2", "Coucou")); // Meta renvoie parfois le même message
  await attendre();
  assert.equal(appelsClaude, avant + 1);
  assert.equal(envois.length, 2);
  assert.equal(envois.at(-1).text.body, "Coucou, ça roule ?");

  analyse = { ...simple, categorie: "finance", sensible: true, reponse: "Je te redis." };
  await webhook(corps("m3", "Tu peux m'envoyer de l'argent ?"));
  await attendre();
  assert.equal(envois.length, 2);
  assert.equal((await admin("/etat")).enAttente[0].statut, "a_valider");
});

test("arrêt d'urgence : plus aucun envoi automatique", async () => {
  await admin("/pause", { method: "POST", body: JSON.stringify({ pause: true }) });
  analyse = { ...simple, reponse: "Bonne soirée !" };
  await webhook(corps("m4", "Bonsoir", "22990000002"));
  await attendre();
  assert.equal(envois.length, 2);
  await admin("/pause", { method: "POST", body: JSON.stringify({ pause: false }) });
});

test("tableau de bord et raccourci protégés", async () => {
  assert.equal((await fetch(base + "/api/admin/etat")).status, 401);
  assert.equal((await fetch(base + "/api/suggerer", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })).status, 401);
  analyse = { ...simple, categorie: "prix_ou_service", sensible: true, besoin_info_proprietaire: true, reponse: "Je regarde et je te dis." };
  const r = await (await fetch(base + "/api/suggerer", { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + "r".repeat(32) }, body: JSON.stringify({ texte: "C'est combien ?" }) })).json();
  assert.equal(r.reponse, "Je regarde et je te dis.");
  assert.match(r.avertissement, /vérifier/);
});
