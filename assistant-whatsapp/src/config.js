/* Configuration lue dans les variables d'environnement (fichier .env en local). */
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const env = process.env;

export const config = {
  port: Number(env.PORT || 8080),
  storageDir: env.STORAGE_DIR || path.join(ROOT, "donnees"),
  defaultRulesFile: path.join(ROOT, "regles.json"),
  trustProxy: env.TRUST_PROXY === "1",

  anthropicKey: env.ANTHROPIC_API_KEY || "",
  model: env.CLAUDE_MODEL || "claude-opus-5-5",
  effort: ["low", "medium", "high"].includes(env.CLAUDE_EFFORT) ? env.CLAUDE_EFFORT : "medium",

  waToken: env.WHATSAPP_TOKEN || "",
  waPhoneId: env.WHATSAPP_PHONE_NUMBER_ID || "",
  waAppSecret: env.WHATSAPP_APP_SECRET || "",
  waVerifyToken: env.WHATSAPP_VERIFY_TOKEN || "",
  graphVersion: env.GRAPH_API_VERSION || "v23.0",

  adminToken: env.ADMIN_TOKEN || "",
  shortcutToken: env.RACCOURCI_TOKEN || "",

  timeZone: env.TZ || "Africa/Porto-Novo",
  debounceMs: Number(env.DELAI_REGROUPEMENT_MS ?? 20000),
  retentionDays: Number(env.RETENTION_JOURS || 30),
  ntfyTopic: env.NTFY_TOPIC || ""
};

/* Problèmes de configuration à afficher au démarrage et dans le tableau de bord. */
export function configProblems() {
  const p = [];
  if (!config.anthropicKey) p.push("ANTHROPIC_API_KEY manquante : aucune réponse ne peut être rédigée.");
  if (config.adminToken.length < 24) p.push("ADMIN_TOKEN absent ou trop court (24 caractères minimum) : tableau de bord désactivé.");
  if (!config.waToken || !config.waPhoneId) p.push("WHATSAPP_TOKEN ou WHATSAPP_PHONE_NUMBER_ID manquant : envoi WhatsApp impossible.");
  if (!config.waAppSecret) p.push("WHATSAPP_APP_SECRET manquant : les messages reçus seront refusés.");
  if (!config.waVerifyToken) p.push("WHATSAPP_VERIFY_TOKEN manquant : Meta ne pourra pas valider le webhook.");
  return p;
}
