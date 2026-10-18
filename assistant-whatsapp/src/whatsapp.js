/* WhatsApp Business Platform (Cloud API officielle de Meta) : réception par webhook et envoi de texte. */
import crypto from "node:crypto";
import { config } from "./config.js";

/* Meta signe chaque appel du webhook avec la clé secrète de l'app (en-tête X-Hub-Signature-256). */
export function verifySignature(rawBody, header) {
  if (!config.waAppSecret || typeof header !== "string" || !header.startsWith("sha256=")) return false;
  const attendu = crypto.createHmac("sha256", config.waAppSecret).update(rawBody).digest("hex");
  const recu = header.slice(7);
  return recu.length === attendu.length && crypto.timingSafeEqual(Buffer.from(recu), Buffer.from(attendu));
}

const texteDe = m =>
  m.type === "text" ? m.text?.body || "" :
  m.type === "button" ? m.button?.text || "" :
  m.type === "interactive" ? m.interactive?.button_reply?.title || m.interactive?.list_reply?.title || "" :
  m.type === "reaction" ? `[réaction ${m.reaction?.emoji || ""}]` :
  m.type === "image" || m.type === "video" || m.type === "document" ? `[${m.type}] ${m[m.type]?.caption || ""}`.trim() :
  `[${m.type}]`;

/* Extrait du corps du webhook :
   - messages : messages reçus des contacts ;
   - echos    : messages envoyés par vous depuis l'application WhatsApp Business (mode « coexistence »).
   Les accusés de lecture et de remise (statuses) sont ignorés : ils ne doivent jamais déclencher de réponse. */
export function parseWebhook(body) {
  const messages = [], echos = [];
  for (const entry of body?.entry || []) for (const change of entry.changes || []) {
    const v = change.value || {};
    if (change.field === "messages") {
      const noms = Object.fromEntries((v.contacts || []).map(c => [c.wa_id, c.profile?.name || ""]));
      for (const m of v.messages || []) {
        if (!m?.id || !m.from || m.from === v.metadata?.display_phone_number) continue;
        messages.push({ id: m.id, contact: m.from, nom: noms[m.from] || "", type: m.type, texte: texteDe(m), at: Number(m.timestamp) * 1000 || Date.now() });
      }
    } else if (change.field === "smb_message_echoes") {
      for (const m of v.message_echoes || []) {
        if (m?.id && m.to) echos.push({ id: m.id, contact: m.to, type: m.type, texte: texteDe(m), at: Number(m.timestamp) * 1000 || Date.now() });
      }
    }
  }
  return { messages, echos };
}

/* Envoie un message texte. Renvoie l'identifiant WhatsApp du message envoyé. */
export async function sendText(to, body, replyTo) {
  if (!config.waToken || !config.waPhoneId) throw new Error("WhatsApp n'est pas configuré sur le serveur.");
  const res = await fetch(`https://graph.facebook.com/${config.graphVersion}/${config.waPhoneId}/messages`, {
    method: "POST",
    headers: { Authorization: `Bearer ${config.waToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      messaging_product: "whatsapp", recipient_type: "individual", to, type: "text",
      text: { body, preview_url: false }, ...(replyTo ? { context: { message_id: replyTo } } : {})
    }),
    signal: AbortSignal.timeout(20000)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code = data?.error?.code;
    // 131047 : plus de 24 h depuis le dernier message du contact, réponse libre interdite par WhatsApp.
    if (code === 131047) throw new Error("Plus de 24 h depuis le dernier message de ce contact : WhatsApp n'autorise plus de réponse libre. Répondez depuis votre téléphone.");
    throw new Error(`WhatsApp a refusé l'envoi (${res.status}${code ? `, code ${code}` : ""}) : ${data?.error?.message || "erreur inconnue"}`);
  }
  return data?.messages?.[0]?.id || null;
}
