/* Fournisseurs d'IA. La clé reste dans les variables d'environnement du serveur.
   Images : OpenAI (API Images) si OPENAI_API_KEY est défini.
   Vidéos : aucun fournisseur branché par défaut ; ajoutez un adaptateur ici
   (Runway, Luma, Veo, Replicate…) en suivant le modèle createVideoJob / getVideoJob. */
import { config } from "./config.js";
import { HttpError } from "./security.js";

export const imageProvider = config.openaiKey ? "openai" : null;
export const videoProvider = null;

const SIZES = { square: "1024x1024", portrait: "1024x1536", landscape: "1536x1024" };
export const IMAGE_SIZES = [["square", "Carré (1:1)"], ["portrait", "Portrait (2:3)"], ["landscape", "Paysage (3:2)"]];
export const IMAGE_STYLES = ["Photographie réaliste", "Cinématique", "Illustration flat", "3D", "Aquarelle", "Affiche graphique"];

/* Renvoie l'image générée sous forme de Buffer PNG. */
export async function generateImage({ prompt, size }) {
  if (!imageProvider) throw new HttpError(503, "Aucun service de génération d'images n'est configuré sur le serveur.", "AI_NOT_CONFIGURED");
  const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 110000);
  try {
    const res = await fetch("https://api.openai.com/v1/images/generations", {
      method: "POST", signal: ctrl.signal,
      headers: { Authorization: `Bearer ${config.openaiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: config.openaiImageModel, prompt, size: SIZES[size] || SIZES.square, n: 1 })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = String(data?.error?.message || ""), code = String(data?.error?.code || "");
      if (code.includes("moderation") || /safety|moderation|content policy/i.test(msg))
        throw new HttpError(422, "La description a été refusée par le filtre de sécurité du service d'IA. Reformule-la.", "AI_REFUSED");
      if (res.status === 429) throw new HttpError(503, "Le service d'IA est saturé. Réessaie dans quelques minutes.", "AI_BUSY");
      console.error("Erreur du fournisseur d'images", res.status, msg);
      throw new HttpError(502, "Le service d'IA a renvoyé une erreur. Réessaie plus tard.", "AI_ERROR");
    }
    const b64 = data?.data?.[0]?.b64_json;
    if (b64) return Buffer.from(b64, "base64");
    const url = data?.data?.[0]?.url;
    if (url) { const r = await fetch(url); if (r.ok) return Buffer.from(await r.arrayBuffer()); }
    throw new HttpError(502, "Le service d'IA n'a renvoyé aucune image.", "AI_EMPTY");
  } catch (e) {
    if (e instanceof HttpError) throw e;
    if (e.name === "AbortError") throw new HttpError(504, "Le service d'IA a mis trop de temps à répondre.", "AI_TIMEOUT");
    throw new HttpError(502, "Impossible de joindre le service d'IA.", "AI_UNREACHABLE");
  } finally { clearTimeout(timer); }
}

/* Construit la consigne envoyée au fournisseur à partir du formulaire. */
export function buildImagePrompt({ prompt, style, usage }) {
  return `${prompt}\nStyle : ${style}. Usage : ${usage}. Image de démonstration pédagogique, sans texte illisible, sans logo de marque existante.`;
}
export function buildDemoPrompt({ topic, details }) {
  return `Illustration pédagogique claire expliquant « ${topic} » pour des apprenants en graphisme et montage vidéo. Style schéma moderne, fond neutre, annotations visuelles simples. ${details || ""}`.trim();
}
