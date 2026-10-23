/* Examen final et certificat de mérite.
   - L'examen s'ouvre quand toutes les leçons disponibles de la formation sont terminées (vérifié par le serveur).
   - 10 questions tirées au hasard ; la correction se fait uniquement ici, jamais dans le navigateur.
   - 10/10 : certificat PDF au nom de l'apprenant, avec numéro vérifiable publiquement. */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import PDFDocument from "pdfkit";
import { config } from "./config.js";
import { db, one, all, run, now } from "./db.js";
import { fail, rateLimit, text } from "./security.js";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const ASSETS = path.join(HERE, "..", "assets", "certificat");
const BANK = JSON.parse(fs.readFileSync(path.join(HERE, "..", "contenus", "examens.json"), "utf8"));
export const EXAM_SIZE = 10, MAX_ATTEMPTS_PER_DAY = 5;

db.exec(`
CREATE TABLE IF NOT EXISTS exam_attempts (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, formation_id TEXT NOT NULL,
  items TEXT NOT NULL, created_at TEXT NOT NULL, submitted_at TEXT, score INTEGER);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON exam_attempts(user_id, formation_id, created_at);
CREATE TABLE IF NOT EXISTS certificates (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, formation_id TEXT NOT NULL,
  full_name TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, issued_at TEXT NOT NULL,
  UNIQUE (user_id, formation_id));
`);

const shuffle = arr => { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = crypto.randomInt(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const certId = () => { const A = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; let s = ""; for (let i = 0; i < 10; i++) s += A[crypto.randomInt(A.length)]; return `TM-${s.slice(0, 5)}-${s.slice(5)}`; };
const fmtDate = iso => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });

function status(userId, fid) {
  const f = BANK[fid];
  if (!f) fail(404, "Aucun examen pour cette formation.", "NOT_FOUND");
  const done = new Set(all("SELECT lesson_id FROM lessons WHERE user_id = ?", userId).map(r => r.lesson_id));
  const missing = f.lessons.filter(l => !done.has(l));
  const since = new Date(Date.now() - 864e5).toISOString();
  const used = one("SELECT COUNT(*) AS n FROM exam_attempts WHERE user_id = ? AND formation_id = ? AND created_at > ?", userId, fid, since).n;
  const cert = one("SELECT id, full_name, issued_at FROM certificates WHERE user_id = ? AND formation_id = ?", userId, fid);
  return { formation: fid, title: f.title, lessons: f.lessons.length, missing, eligible: missing.length === 0, attemptsLeft: Math.max(0, MAX_ATTEMPTS_PER_DAY - used),
    questions: EXAM_SIZE, certificate: cert ? { id: cert.id, fullName: cert.full_name, issuedAt: cert.issued_at } : null };
}

export async function certificatePdf(c) {
  const f = BANK[c.formation_id] || { title: c.formation_id };
  const doc = new PDFDocument({ size: "A4", layout: "landscape", margin: 0, info: { Title: `Certificat TOB-MAQ · ${f.title}`, Author: "TOB-MAQ", Subject: `Certificat n° ${c.id}` } });
  const chunks = []; doc.on("data", d => chunks.push(d));
  const done = new Promise(r => doc.on("end", () => r(Buffer.concat(chunks))));
  doc.registerFont("nom", path.join(ASSETS, "GreatVibes.woff"));
  doc.registerFont("texte", path.join(ASSETS, "DMSans-Regular.woff"));
  doc.registerFont("gras", path.join(ASSETS, "DMSans-Bold.woff"));
  doc.image(path.join(ASSETS, "fond.jpg"), 0, 0, { width: 842, height: 595 });
  // Nom de l'apprenant en lettres dorées (réduit si très long)
  let size = 46; doc.font("nom");
  while (size > 24 && doc.fontSize(size).widthOfString(c.full_name) > 520) size -= 2;
  doc.fillColor("#B07D22").fontSize(size).text(c.full_name, 121, 202 + (46 - size) * .5, { width: 600, align: "center", lineBreak: false });
  doc.moveTo(266, 262).lineTo(576, 262).lineWidth(.8).strokeColor("#3A3D48").stroke();
  // Texte officiel
  doc.font("texte").fontSize(10.4).fillColor("#3A3D48").text(
    `En reconnaissance de l'excellence de son parcours, ce certificat atteste que le ou la titulaire a suivi avec assiduité ` +
    `l'intégralité de la formation « ${f.title} » dispensée par TOB-MAQ, et a réussi avec brio l'examen final de certification ` +
    `en obtenant la note parfaite de ${c.score}/${c.total}. Il confirme la maîtrise des compétences enseignées, ainsi que la rigueur, ` +
    "la persévérance et la créativité dont il ou elle a fait preuve. Toute notre équipe lui adresse ses plus sincères félicitations " +
    "et lui souhaite une brillante carrière dans les métiers créatifs et du numérique.",
    136, 276, { width: 570, align: "center", lineGap: 3.2 });
  // Date de délivrance
  doc.font("gras").fontSize(11.5).fillColor("#0E1222").text(fmtDate(c.issued_at), 170, 462, { width: 150, align: "center" });
  // Numéro et vérification
  const verify = `${config.publicUrl.replace(/^https?:\/\//, "")}/#/certificat/${c.id}`;
  doc.font("gras").fontSize(7.5).fillColor("#6B6F7B").text(`N° ${c.id}`, 80, 62, { width: 260, characterSpacing: .8 });
  doc.font("texte").fontSize(6.6).fillColor("#8A8E99").text(`Vérification : ${verify}`, 80, 73, { width: 300 });
  doc.end();
  return done;
}

export function registerCertificates(api, { needUser, needConsent }) {
  api.get("/exams/:fid", needUser, (req, res) => res.json(status(req.user.id, req.params.fid)));

  api.post("/exams/:fid/start", needUser, needConsent, (req, res) => {
    const st = status(req.user.id, req.params.fid);
    if (!st.eligible) fail(403, "Termine d'abord toutes les leçons de la formation.", "NOT_ELIGIBLE");
    if (!st.attemptsLeft) fail(429, `Tu as utilisé tes ${MAX_ATTEMPTS_PER_DAY} essais du jour. Révise les leçons et réessaie demain.`, "ATTEMPTS");
    const pool = BANK[req.params.fid].questions;
    const picked = shuffle(pool.map((_, i) => i)).slice(0, EXAM_SIZE);
    const items = picked.map(qi => ({ qi, order: shuffle(pool[qi].choices.map((_, i) => i)) }));
    const id = crypto.randomUUID();
    run("INSERT INTO exam_attempts(id, user_id, formation_id, items, created_at) VALUES (?,?,?,?,?)", id, req.user.id, req.params.fid, JSON.stringify(items), now());
    res.status(201).json({ attempt: id, title: st.title, questions: items.map(({ qi, order }) => ({ q: pool[qi].q, choices: order.map(o => pool[qi].choices[o]) })) });
  });

  api.post("/exams/attempts/:id/submit", needUser, needConsent, (req, res) => {
    rateLimit("exam:" + req.user.id, 20, 3600000);
    const a = one("SELECT * FROM exam_attempts WHERE id = ? AND user_id = ?", req.params.id, req.user.id);
    if (!a) fail(404, "Examen introuvable.", "NOT_FOUND");
    if (a.submitted_at) fail(409, "Cet examen a déjà été corrigé. Lance un nouvel essai.", "ALREADY_SUBMITTED");
    if (Date.now() - new Date(a.created_at) > 2 * 3600000) fail(410, "Cet examen a expiré. Lance un nouvel essai.", "EXPIRED");
    const pool = BANK[a.formation_id].questions, items = JSON.parse(a.items);
    const answers = Array.isArray(req.body?.answers) ? req.body.answers : [];
    const results = items.map(({ qi, order }, i) => {
      const chosen = Number.isInteger(answers[i]) && answers[i] >= 0 && answers[i] < order.length ? order[answers[i]] : -1;
      return { ok: chosen === pool[qi].answer, explain: pool[qi].explain, answer: order.indexOf(pool[qi].answer) };
    });
    const score = results.filter(r => r.ok).length, passed = score === items.length;
    run("UPDATE exam_attempts SET submitted_at = ?, score = ? WHERE id = ?", now(), score, a.id);
    let certificate = null;
    if (passed) {
      const existing = one("SELECT id FROM certificates WHERE user_id = ? AND formation_id = ?", req.user.id, a.formation_id);
      if (existing) certificate = existing.id;
      else {
        const fullName = text(req.body?.fullName || req.user.display_name, { min: 2, max: 60, name: "Le nom" }).replace(/\s+/g, " ");
        if (!/^[\p{L}\p{M} .'-]+$/u.test(fullName)) fail(400, "Le nom ne peut contenir que des lettres, des espaces, des points, des apostrophes et des tirets.", "BAD_NAME");
        certificate = certId();
        run("INSERT INTO certificates(id, user_id, formation_id, full_name, score, total, issued_at) VALUES (?,?,?,?,?,?,?)", certificate, req.user.id, a.formation_id, fullName, score, items.length, now());
      }
    }
    res.json({ score, total: items.length, passed, certificate, results: results.map(r => ({ ok: r.ok, explain: r.ok ? r.explain : "" })) });
  });

  api.get("/me/certificates", needUser, (req, res) => res.json(all("SELECT id, formation_id, full_name, score, total, issued_at FROM certificates WHERE user_id = ? ORDER BY issued_at DESC", req.user.id)
    .map(c => ({ id: c.id, formation: c.formation_id, title: BANK[c.formation_id]?.title || c.formation_id, fullName: c.full_name, score: c.score, total: c.total, issuedAt: c.issued_at }))));

  // Vérification publique : uniquement le nom, la formation et la date.
  api.get("/certificates/:id", (req, res) => {
    rateLimit("verif:" + (req.ip || ""), 60, 600000);
    const c = one("SELECT * FROM certificates WHERE id = ?", String(req.params.id).toUpperCase());
    if (!c) fail(404, "Aucun certificat ne porte ce numéro.", "NOT_FOUND");
    res.json({ id: c.id, fullName: c.full_name, formation: BANK[c.formation_id]?.title || c.formation_id, score: c.score, total: c.total, issuedAt: c.issued_at });
  });

  api.get("/certificates/:id/pdf", needUser, async (req, res, next) => {
    try {
      const c = one("SELECT * FROM certificates WHERE id = ?", String(req.params.id).toUpperCase());
      if (!c || (c.user_id !== req.user.id && req.user.role !== "admin")) fail(404, "Certificat introuvable.", "NOT_FOUND");
      const pdf = await certificatePdf(c);
      res.set({ "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="certificat-tobmaq-${c.formation_id}.pdf"`, "Cache-Control": "private, no-store" }).send(pdf);
    } catch (e) { next(e); }
  });
}
