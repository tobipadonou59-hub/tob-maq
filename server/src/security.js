/* Sécurité : mots de passe (scrypt), jetons, limitation de débit, validation. */
import crypto from "node:crypto";

export class HttpError extends Error {
  constructor(status, message, code) { super(message); this.status = status; this.code = code || "HTTP_" + status; }
}
export const fail = (status, message, code) => { throw new HttpError(status, message, code); };

const SCRYPT = { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
const scrypt = (pw, salt) => new Promise((ok, ko) => crypto.scrypt(pw, salt, 64, SCRYPT, (e, k) => e ? ko(e) : ok(k)));

export async function hashPassword(pw) {
  const salt = crypto.randomBytes(16);
  const key = await scrypt(pw.normalize("NFKC"), salt);
  return `scrypt$${SCRYPT.N}$${SCRYPT.r}$${SCRYPT.p}$${salt.toString("base64")}$${key.toString("base64")}`;
}
export async function verifyPassword(pw, stored) {
  const parts = String(stored || "").split("$");
  if (parts.length !== 6 || parts[0] !== "scrypt") { await scrypt("leurre", crypto.randomBytes(16)); return false; }
  const key = await scrypt(pw.normalize("NFKC"), Buffer.from(parts[4], "base64"));
  const ref = Buffer.from(parts[5], "base64");
  return ref.length === key.length && crypto.timingSafeEqual(ref, key);
}
/* Jeton aléatoire envoyé au client ; seule son empreinte SHA-256 est stockée. */
export const newToken = () => crypto.randomBytes(32).toString("base64url");
export const sha256 = s => crypto.createHash("sha256").update(s).digest("hex");
export const uid = () => crypto.randomUUID();

/* Limitation de débit en mémoire (suffisant pour une seule instance). */
const hits = new Map();
export function rateLimit(key, max, windowMs) {
  const t = Date.now(), arr = (hits.get(key) || []).filter(x => t - x < windowMs);
  arr.push(t); hits.set(key, arr);
  if (arr.length > max) fail(429, "Trop de tentatives. Patiente quelques minutes puis réessaie.", "RATE_LIMIT");
}
setInterval(() => { const t = Date.now(); for (const [k, v] of hits) if (!v.some(x => t - x < 3600000)) hits.delete(k); }, 600000).unref();

/* Validation des entrées */
export const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/;
export function text(v, { min = 0, max = 1000, name = "Ce champ" } = {}) {
  if (typeof v !== "string") fail(400, `${name} est manquant ou invalide.`);
  const s = v.trim();
  if (s.length < min) fail(400, `${name} est trop court.`);
  if (s.length > max) fail(400, `${name} est trop long (${max} caractères maximum).`);
  return s;
}
export function email(v) {
  const s = text(v, { min: 5, max: 160, name: "L'adresse e-mail" }).toLowerCase();
  if (!EMAIL_RE.test(s)) fail(400, "Adresse e-mail invalide.");
  return s;
}
export function password(v) {
  if (typeof v !== "string" || v.length < 10 || v.length > 128 || !/\p{L}/u.test(v) || !/\d/.test(v))
    fail(400, "Le mot de passe doit contenir 10 à 128 caractères, avec au moins une lettre et un chiffre.");
  return v;
}
export function oneOf(v, list, name = "Valeur") { if (!list.includes(v)) fail(400, `${name} invalide.`); return v; }

/* Vérifie la signature binaire d'un fichier envoyé (ne pas se fier au type annoncé). */
export function sniff(buf) {
  if (buf.length >= 8 && buf.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return "image/png";
  if (buf.length >= 3 && buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff) return "image/jpeg";
  if (buf.length >= 12 && buf.subarray(4, 8).toString("latin1") === "ftyp") return "video/mp4";
  if (buf.length >= 5 && buf.subarray(0, 5).toString("latin1") === "%PDF-") return "application/pdf";
  if (buf.length >= 4 && buf[0] === 0x50 && buf[1] === 0x4b && buf[2] === 0x03 && buf[3] === 0x04) return "application/zip";
  return null;
}
export function parseCookies(h) {
  const out = {};
  for (const part of String(h || "").split(";")) { const i = part.indexOf("="); if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim()); }
  return out;
}
