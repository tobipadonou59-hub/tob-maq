/* Envoi d'e-mails. Avec BREVO_API_KEY : envoi réel via l'API Brevo.
   Sans clé : le message est écrit dans le journal du serveur (développement uniquement). */
import { config } from "./config.js";

export async function sendMail({ to, subject, text }) {
  if (!config.brevoKey) {
    console.log(`\n[e-mail non envoyé : BREVO_API_KEY absent]\nÀ : ${to}\nObjet : ${subject}\n${text}\n`);
    return { sent: false };
  }
  const res = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": config.brevoKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ sender: { email: config.mailFrom, name: "TOB-MAQ" }, to: [{ email: to }], subject, textContent: text })
  });
  if (!res.ok) { console.error("Échec d'envoi d'e-mail", res.status, await res.text().catch(() => "")); return { sent: false }; }
  return { sent: true };
}
