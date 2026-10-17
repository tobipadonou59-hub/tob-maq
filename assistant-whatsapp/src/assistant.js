/* Cœur de l'assistant : enregistre les messages, regroupe ceux qui arrivent à la suite,
   demande une analyse à Claude, applique les règles puis envoie ou met en attente de validation. */
import { config } from "./config.js";
import { one, all, run, getRules, getMode, isPaused, contactState, setContactState } from "./db.js";
import { analyser } from "./claude.js";
import { decider } from "./decision.js";
import { sendText } from "./whatsapp.js";

const EN_ATTENTE = ["a_valider", "suggestion"];
const timers = new Map(), files = new Map();

/* Messages reçus par le webhook. Meta peut renvoyer plusieurs fois le même : l'identifiant unique évite les doublons. */
export async function recevoir(messages) {
  const contacts = new Set();
  for (const m of messages) {
    const r = run("INSERT OR IGNORE INTO messages (id, contact, nom, sens, type, texte, at) VALUES (?, ?, ?, 'entrant', ?, ?, ?)", m.id, m.contact, m.nom, m.type, m.texte, m.at);
    if (r.changes) contacts.add(m.contact);
  }
  for (const c of contacts) {
    // Plus de 10 messages en 2 minutes : sans doute un robot ou une boucle. Pause automatique d'une heure.
    const n = one("SELECT COUNT(*) AS n FROM messages WHERE contact = ? AND sens = 'entrant' AND at > ?", c, Date.now() - 120000).n;
    if (n > 10) setContactState(c, "bloque_jusqua", Date.now() + 3600000);
  }
  await Promise.all([...contacts].map(planifier));
}

/* Messages que vous avez envoyés vous-même depuis l'application WhatsApp Business (coexistence). */
export function recevoirEchos(echos) {
  const heures = getRules().pause_apres_reponse_manuelle_heures ?? 2;
  for (const e of echos) {
    if (one("SELECT 1 AS x FROM messages WHERE id = ?", e.id)) continue; // déjà connu (dont nos propres envois)
    run("INSERT INTO messages (id, contact, sens, type, texte, at, traite) VALUES (?, ?, 'echo', ?, ?, ?, 1)", e.id, e.contact, e.type, e.texte, e.at);
    setContactState(e.contact, "humain_jusqua", Date.now() + heures * 3600000);
    run(`UPDATE brouillons SET statut = 'rejete', raison = 'Vous avez répondu vous-même.', maj = ? WHERE contact = ? AND statut IN ('a_valider', 'suggestion')`, Date.now(), e.contact);
  }
}

/* Attend un court instant après le dernier message d'un contact pour répondre une seule fois à l'ensemble. */
export function planifier(contact) {
  clearTimeout(timers.get(contact));
  if (config.debounceMs <= 0) return enFile(contact);
  timers.set(contact, setTimeout(() => { timers.delete(contact); enFile(contact); }, config.debounceMs));
}

/* Un seul traitement à la fois par contact. */
function enFile(contact) {
  const p = (files.get(contact) || Promise.resolve()).then(() => traiter(contact)).catch(e => console.error("Traitement", e));
  files.set(contact, p);
  return p;
}

async function traiter(contact) {
  const nouveaux = all("SELECT * FROM messages WHERE contact = ? AND sens = 'entrant' AND traite = 0 ORDER BY at", contact);
  if (!nouveaux.length) return;
  for (const m of nouveaux) run("UPDATE messages SET traite = 1 WHERE id = ?", m.id);

  // Les brouillons encore en attente pour ce contact sont remplacés par une réponse unique à l'ensemble.
  const anciens = all("SELECT * FROM brouillons WHERE contact = ? AND statut IN ('a_valider', 'suggestion')", contact);
  const idsAnciens = anciens.flatMap(b => JSON.parse(b.messages));
  const lot = [...all(`SELECT * FROM messages WHERE id IN (${idsAnciens.map(() => "?").join(",") || "''"}) ORDER BY at`, ...idsAnciens), ...nouveaux];
  for (const b of anciens) run("UPDATE brouillons SET statut = 'remplace', maj = ? WHERE id = ?", Date.now(), b.id);

  const ids = lot.map(m => m.id);
  const historique = all(`SELECT * FROM (SELECT * FROM messages WHERE contact = ? AND id NOT IN (${ids.map(() => "?").join(",")}) ORDER BY at DESC LIMIT 12) ORDER BY at`, contact, ...ids);
  const regles = getRules(), fiche = regles.contacts?.[contact] || {};
  const nom = fiche.nom || lot.at(-1).nom || "";
  const profil = { nom, relation: fiche.relation, style: fiche.style };

  let analyse = null, erreur = null;
  try { analyse = await analyser({ regles, profil, historique, nouveaux: lot.map(m => m.texte) }); }
  catch (e) { erreur = e.message; console.error("Claude", e.message); }

  const d = erreur ? { statut: "a_valider", raison: "Claude est indisponible : à traiter vous-même." } : decider({
    mode: getMode(), pause: isPaused(), regles, analyse, contact,
    nouveaux: lot.map(m => m.texte), types: lot.map(m => m.type), etat: contactState(contact),
    envoisDerniereHeure: one("SELECT COUNT(*) AS n FROM brouillons WHERE contact = ? AND auto = 1 AND statut = 'envoye' AND maj > ?", contact, Date.now() - 3600000).n,
    dernieresReponses: all("SELECT texte FROM messages WHERE contact = ? AND sens = 'sortant' ORDER BY at DESC LIMIT 5", contact).map(r => r.texte),
    timeZone: config.timeZone
  });
  const now = Date.now();
  const { lastInsertRowid: id } = run(
    "INSERT INTO brouillons (contact, nom, messages, dernier_message_id, analyse, reponse, statut, raison, erreur, cree, maj) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    contact, nom, JSON.stringify(ids), lot.at(-1).id, analyse ? JSON.stringify(analyse) : null, analyse?.reponse || "", d.statut, d.raison, erreur, now, now);

  if (d.statut === "a_envoyer") await envoyer(Number(id), { auto: true }).catch(() => {});
  else if (d.statut === "a_valider") notifier();
}

/* Envoi d'un brouillon. Le passage au statut « envoi » est atomique : un même brouillon ne part jamais deux fois. */
export async function envoyer(id, { texte, auto = false } = {}) {
  if (auto && isPaused()) { run("UPDATE brouillons SET statut = 'suggestion', raison = 'Arrêt d''urgence activé.', maj = ? WHERE id = ?", Date.now(), id); return null; }
  const permis = auto ? ["a_envoyer"] : [...EN_ATTENTE, "erreur"];
  const r = run(`UPDATE brouillons SET statut = 'envoi', auto = ?, reponse = COALESCE(?, reponse), maj = ? WHERE id = ? AND statut IN (${permis.map(() => "?").join(",")})`,
    auto ? 1 : 0, texte ?? null, Date.now(), id, ...permis);
  if (!r.changes) throw new Error("Ce brouillon a déjà été traité.");
  const b = one("SELECT * FROM brouillons WHERE id = ?", id);
  if (!b.reponse.trim()) { run("UPDATE brouillons SET statut = 'erreur', erreur = 'Réponse vide.' WHERE id = ?", id); throw new Error("Réponse vide."); }
  try {
    const waId = await sendText(b.contact, b.reponse, b.dernier_message_id);
    run("UPDATE brouillons SET statut = 'envoye', envoye_id = ?, erreur = NULL, maj = ? WHERE id = ?", waId, Date.now(), id);
    run("INSERT OR IGNORE INTO messages (id, contact, sens, type, texte, at, traite) VALUES (?, ?, 'sortant', 'text', ?, ?, 1)", waId || `envoi-${id}`, b.contact, b.reponse, Date.now());
    return waId;
  } catch (e) {
    run("UPDATE brouillons SET statut = 'erreur', erreur = ?, maj = ? WHERE id = ?", e.message, Date.now(), id);
    throw e;
  }
}

export function rejeter(id) {
  const r = run("UPDATE brouillons SET statut = 'rejete', maj = ? WHERE id = ? AND statut IN ('a_valider', 'suggestion', 'erreur')", Date.now(), id);
  if (!r.changes) throw new Error("Ce brouillon a déjà été traité.");
}

/* Notification sans contenu (aucun texte de message ne quitte le serveur vers ntfy). */
function notifier() {
  if (!config.ntfyTopic) return;
  fetch(`https://ntfy.sh/${encodeURIComponent(config.ntfyTopic)}`, { method: "POST", body: "Une réponse attend votre validation.", headers: { Title: "Assistant WhatsApp" }, signal: AbortSignal.timeout(5000) })
    .catch(e => console.error("ntfy", e.message));
}

/* Suggestion ponctuelle pour le raccourci iPhone : rien n'est enregistré sur le serveur. */
export async function suggerer({ texte, contact, style }) {
  const a = await analyser({ regles: getRules(), profil: { nom: contact || "" }, historique: [], nouveaux: [texte], style });
  if (a.refus) return { reponse: "", avertissement: "Claude n'a pas voulu proposer de réponse à ce message." };
  return {
    reponse: a.reponse, categorie: a.categorie, sensible: a.sensible, resume: a.resume,
    avertissement: a.sensible || a.besoin_info_proprietaire ? `À vérifier avant d'envoyer : ${a.raison}` : ""
  };
}

/* Au redémarrage, reprend les messages reçus mais pas encore traités. */
export function reprendre() {
  for (const { contact } of all("SELECT DISTINCT contact FROM messages WHERE sens = 'entrant' AND traite = 0")) planifier(contact);
}
