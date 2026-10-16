/* Tests de l'abonnement Premium avec un faux serveur FedaPay (aucun paiement réel). */
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";

const storage = fs.mkdtempSync(path.join(os.tmpdir(), "tobmaq-billing-"));
const fake = { status: "pending", amount: null, created: 0 };
const fedapay = http.createServer((req, res) => {
  let body = "";
  req.on("data", c => body += c);
  req.on("end", () => {
    assert.equal(req.headers.authorization, "Bearer sk_sandbox_test");
    res.setHeader("Content-Type", "application/json");
    if (req.method === "POST" && req.url === "/transactions") { fake.created++; fake.amount = JSON.parse(body).amount; fake.callback = JSON.parse(body).callback_url; return res.end(JSON.stringify({ "v1/transaction": { id: 101, amount: fake.amount } })); }
    if (req.method === "POST" && req.url === "/transactions/101/token") return res.end(JSON.stringify({ token: "tok", url: "https://checkout.fedapay.test/tok" }));
    if (req.method === "GET" && req.url === "/transactions/101") return res.end(JSON.stringify({ "v1/transaction": { id: 101, status: fake.status, amount: fake.amount } }));
    res.statusCode = 404; res.end("{}");
  });
});
await new Promise(ok => fedapay.listen(0, ok));
Object.assign(process.env, { STORAGE_DIR: storage, ADMIN_EMAILS: "admin@tob-maq.test", PUBLIC_URL: "http://localhost",
  FEDAPAY_SECRET_KEY: "sk_sandbox_test", FEDAPAY_API_URL: `http://127.0.0.1:${fedapay.address().port}` });

const { createApp } = await import("../src/index.js");
const lessonFile = path.join(path.dirname(new URL(import.meta.url).pathname), "..", "contenus-premium", "lecons", "test-premium.json");
let server, base;
function client() {
  let cookie = "";
  return async (method, url, body) => {
    const headers = { Accept: "application/json" };
    if (cookie) headers.Cookie = cookie;
    if (body) headers["Content-Type"] = "application/json";
    const res = await fetch(base + url, { method, headers, body: body ? JSON.stringify(body) : undefined, redirect: "manual" });
    const set = res.headers.get("set-cookie"); if (set) cookie = set.split(";")[0];
    const ct = res.headers.get("content-type") || "";
    return { status: res.status, data: ct.includes("json") ? await res.json() : await res.text(), location: res.headers.get("location") };
  };
}
const reg = (c, name, email) => c("POST", "/api/auth/register", { displayName: name, email, password: "motdepasse12", interests: ["video"], level: "Débutant", ageGroup: "adulte", acceptTerms: true });

before(() => new Promise(ok => {
  fs.writeFileSync(lessonFile, JSON.stringify({ title: "Leçon premium de test", minutes: 10, software: "Test", level: "Avancé", objective: "Tester." }));
  server = createApp().listen(0, () => { base = `http://127.0.0.1:${server.address().port}`; ok(); });
}));
after(() => { server.close(); fedapay.close(); fs.rmSync(lessonFile, { force: true }); fs.rmSync(storage, { recursive: true, force: true }); });

test("vente fermée tant que l'administration n'a pas fixé de prix", async () => {
  const c = client(); await reg(c, "Ama", "ama@exemple.bj");
  assert.equal((await c("GET", "/api/billing/plans")).data.enabled, false);
  assert.equal((await c("POST", "/api/billing/checkout", { plan: "mois" })).data.code, "BILLING_CLOSED");
  const a = client(); await reg(a, "Admin", "admin@tob-maq.test");
  assert.equal((await a("PATCH", "/api/admin/billing", { enabled: true })).status, 400, "prix obligatoire avant ouverture");
  assert.equal((await a("PATCH", "/api/admin/billing", { enabled: true, priceMonthly: 2500, priceYearly: "" })).status, 200);
  const plans = (await c("GET", "/api/billing/plans")).data;
  assert.equal(plans.enabled, true);
  assert.deepEqual(plans.plans.map(p => [p.id, p.price]), [["mois", 2500]]);
  assert.equal((await c("PATCH", "/api/admin/billing", { enabled: true, priceMonthly: 1 })).status, 403, "un membre ne peut pas changer les prix");
});

test("parcours de paiement : contenu verrouillé, paiement en attente, puis approuvé une seule fois", async () => {
  const c = client(); await c("POST", "/api/auth/login", { email: "ama@exemple.bj", password: "motdepasse12" });
  const cat = await c("GET", "/api/premium/catalog");
  assert.ok(cat.data.some(l => l.id === "test-premium"), "le catalogue liste les titres sans le contenu");
  assert.equal(cat.data[0].objective, undefined);
  assert.equal((await c("GET", "/api/premium/lessons/test-premium")).data.code, "PREMIUM_REQUIRED");

  const co = await c("POST", "/api/billing/checkout", { plan: "mois" });
  assert.equal(co.status, 200); assert.equal(co.data.url, "https://checkout.fedapay.test/tok");
  assert.equal(fake.amount, 2500, "le montant vient du serveur, pas du navigateur");
  const ref = new URL(fake.callback).searchParams.get("ref");

  fake.status = "pending";
  const r1 = await c("GET", `/api/billing/retour?ref=${ref}&status=approved`);
  assert.match(r1.location, /paiement=attente/, "le paramètre status du navigateur est ignoré");
  assert.equal((await c("GET", "/api/auth/me")).data.user.premium, false);

  fake.status = "approved";
  const r2 = await c("GET", `/api/billing/retour?ref=${ref}`);
  assert.match(r2.location, /paiement=ok/);
  const me = (await c("GET", "/api/auth/me")).data.user;
  assert.equal(me.premium, true);
  const until = me.premiumUntil;
  // Double notification (retour + webhook) : l'abonnement n'est prolongé qu'une fois.
  assert.equal((await client()("POST", "/api/billing/webhook", { name: "transaction.approved", entity: { id: 101 } })).status, 200);
  await c("GET", `/api/billing/retour?ref=${ref}`);
  assert.equal((await c("GET", "/api/auth/me")).data.user.premiumUntil, until);
  const days = (new Date(until) - Date.now()) / 864e5;
  assert.ok(days > 29 && days <= 30.01, "30 jours d'accès");

  const lesson = await c("GET", "/api/premium/lessons/test-premium");
  assert.equal(lesson.status, 200); assert.equal(lesson.data.objective, "Tester.");
  const hist = await c("GET", "/api/me/billing");
  assert.equal(hist.data.payments[0].status, "approved");
});

test("un montant modifié chez le prestataire ne débloque rien", async () => {
  const c = client(); await reg(c, "Koffi", "koffi@exemple.bj");
  await c("POST", "/api/billing/checkout", { plan: "mois" });
  fake.status = "approved"; fake.amount = 100; // montant trafiqué
  const ref = new URL(fake.callback).searchParams.get("ref");
  assert.match((await c("GET", `/api/billing/retour?ref=${ref}`)).location, /paiement=echec/);
  assert.equal((await c("GET", "/api/auth/me")).data.user.premium, false);
});

test("l'administration voit les paiements et le chiffre d'affaires", async () => {
  const a = client(); await a("POST", "/api/auth/login", { email: "admin@tob-maq.test", password: "motdepasse12" });
  const b = await a("GET", "/api/admin/billing");
  assert.equal(b.data.revenue, 2500); assert.equal(b.data.subscribers, 1);
  assert.match(b.data.webhookUrl, /\/api\/billing\/webhook$/);
  assert.equal((await a("GET", "/api/admin/payments")).data.length, 2);
  assert.equal(b.data.trials, 0);
});

test("essai gratuit : 30 jours, une seule fois par compte, sans paiement", async () => {
  const c = client(); await reg(c, "Essai", "essai@exemple.bj");
  const plans = (await c("GET", "/api/billing/plans")).data;
  assert.deepEqual(plans.trial, { enabled: true, days: 30 });
  assert.equal((await c("GET", "/api/premium/lessons/test-premium")).data.code, "PREMIUM_REQUIRED");
  const t = await c("POST", "/api/billing/trial");
  assert.equal(t.status, 200);
  const days = (new Date(t.data.premiumUntil) - Date.now()) / 864e5;
  assert.ok(days > 29.9 && days <= 30.01);
  const me = (await c("GET", "/api/auth/me")).data.user;
  assert.equal(me.premium, true); assert.equal(me.trialUsed, true);
  assert.equal((await c("GET", "/api/premium/lessons/test-premium")).status, 200, "l'essai donne accès au contenu premium");
  assert.equal((await c("GET", "/api/me/billing")).data.onTrial, true);
  assert.equal((await c("POST", "/api/billing/trial")).data.code, "TRIAL_USED", "un seul essai par compte");
  const deux = await Promise.all([client(), client()].map(async (x, i) => { await x("POST", "/api/auth/login", { email: "essai@exemple.bj", password: "motdepasse12" }); return x("POST", "/api/billing/trial"); }));
  assert.ok(deux.every(r => r.status === 409));
});

test("l'administration peut désactiver l'essai ou changer sa durée", async () => {
  const a = client(); await a("POST", "/api/auth/login", { email: "admin@tob-maq.test", password: "motdepasse12" });
  assert.equal((await a("PATCH", "/api/admin/billing", { enabled: true, priceMonthly: 2500, trialEnabled: true, trialDays: 200 })).status, 400);
  assert.equal((await a("PATCH", "/api/admin/billing", { enabled: true, priceMonthly: 2500, trialEnabled: false, trialDays: 14 })).status, 200);
  const c = client(); await reg(c, "Tardif", "tardif@exemple.bj");
  assert.equal((await c("POST", "/api/billing/trial")).data.code, "TRIAL_CLOSED");
  await a("PATCH", "/api/admin/billing", { enabled: true, priceMonthly: 2500, trialEnabled: true, trialDays: 14 });
  const t = await c("POST", "/api/billing/trial");
  const days = (new Date(t.data.premiumUntil) - Date.now()) / 864e5;
  assert.ok(days > 13.9 && days <= 14.01);
  const b = (await a("GET", "/api/admin/billing")).data;
  assert.equal(b.trials, 2); assert.equal(b.revenue, 2500, "les essais ne comptent pas dans le chiffre d'affaires");
});
