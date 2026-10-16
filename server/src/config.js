/* Configuration lue dans les variables d'environnement (ou un fichier .env).
   Les secrets (clés d'API) ne quittent jamais le serveur. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const SERVER_DIR = path.resolve(here, "..");
export const SITE_DIR = path.resolve(SERVER_DIR, "..");

// Chargement minimal d'un fichier .env (sans dépendance) ; les variables déjà définies gagnent.
const envFile = path.join(SERVER_DIR, ".env");
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}
const env = (k, d = "") => process.env[k] ?? d;
const num = (k, d) => Number.isFinite(Number(process.env[k])) && process.env[k] !== "" && process.env[k] !== undefined ? Number(process.env[k]) : d;

export const config = {
  port: num("PORT", 8080),
  // Adresse publique : PUBLIC_URL, sinon celle fournie automatiquement par Render ou Railway.
  publicUrl: (env("PUBLIC_URL") || env("RENDER_EXTERNAL_URL") || (env("RAILWAY_PUBLIC_DOMAIN") ? "https://" + env("RAILWAY_PUBLIC_DOMAIN") : "") || "http://localhost:8080").replace(/\/$/, ""),
  storageDir: path.resolve(SERVER_DIR, env("STORAGE_DIR", "storage")),
  trustProxy: env("TRUST_PROXY", "0") === "1",
  adminEmails: env("ADMIN_EMAILS").split(",").map(s => s.trim().toLowerCase()).filter(Boolean),
  contactEmail: env("CONTACT_EMAIL"),
  mailFrom: env("MAIL_FROM", "no-reply@tob-maq.local"),
  brevoKey: env("BREVO_API_KEY"),
  openaiKey: env("OPENAI_API_KEY"),
  openaiImageModel: env("OPENAI_IMAGE_MODEL", "gpt-image-1"),
  imageCostFcfa: num("AI_IMAGE_COST_FCFA", 40),
  maxUploadMb: num("MAX_UPLOAD_MB", 50),
  sessionDays: num("SESSION_DAYS", 30)
};
