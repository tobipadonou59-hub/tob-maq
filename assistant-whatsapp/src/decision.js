/* Décide du sort d'un brouillon. Fonction pure, sans accès réseau ni base : facile à tester.
   L'avis de Claude ne suffit jamais à envoyer seul : chaque condition ci-dessous doit être remplie.

   Statuts possibles :
   - "suggestion" : la réponse est proposée, vous l'envoyez vous-même (mode 1) ;
   - "a_valider"  : la réponse attend votre accord dans le tableau de bord (mode 2, ou cas sensible) ;
   - "a_envoyer"  : la réponse part automatiquement (mode 3, cas simple et autorisé) ;
   - "ignore"     : aucune réponse (spam, chaîne, message d'un robot). */

const normaliser = t => String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

function dansLesHeures(heures, date, timeZone) {
  if (!heures?.debut || !heures?.fin) return true;
  const hm = new Intl.DateTimeFormat("fr-FR", { timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(date);
  return heures.debut <= heures.fin ? hm >= heures.debut && hm < heures.fin : hm >= heures.debut || hm < heures.fin;
}

export function decider({ mode, pause, regles, analyse, contact, nouveaux, types, etat, envoisDerniereHeure, dernieresReponses, maintenant = new Date(), timeZone = "UTC" }) {
  if (!analyse || analyse.refus) return { statut: "a_valider", raison: "Claude n'a pas pu proposer de réponse : à traiter vous-même." };
  if (analyse.categorie === "ne_pas_repondre") return { statut: "ignore", raison: analyse.raison || "Message auquel il vaut mieux ne pas répondre." };
  if (!analyse.reponse) return { statut: "a_valider", raison: analyse.raison || "Aucune réponse proposée." };
  if (pause) return { statut: "suggestion", raison: "Arrêt d'urgence activé : rien n'est envoyé automatiquement." };
  if (mode === "suggestion") return { statut: "suggestion", raison: "Mode suggestion." };
  if (mode !== "automatique") return { statut: "a_valider", raison: "Mode validation." };

  // Mode automatique : la première condition non remplie envoie le brouillon en validation.
  const fiche = regles.contacts?.[contact] || {};
  const texte = normaliser(nouveaux.join(" "));
  const mot = (regles.mots_toujours_valides || []).find(m => texte.includes(normaliser(m)));
  const reponse = normaliser(analyse.reponse);
  const now = maintenant.getTime();
  const verifs = [
    [types.some(t => t !== "text"), "Le message contient une image, un audio ou un fichier."],
    [(regles.contacts_jamais_automatique || []).includes(contact) || fiche.automatique === false, "Ce contact est réglé sur « jamais automatique »."],
    [etat.bloque_jusqua > now, "Ce contact envoie beaucoup de messages : réponses automatiques suspendues."],
    [etat.humain_jusqua > now, "Vous avez répondu vous-même récemment : l'assistant vous laisse la main."],
    [!(regles.categories_automatiques || []).includes(analyse.categorie), `Catégorie « ${analyse.categorie} » non autorisée en automatique.`],
    [analyse.sensible, `Sujet sensible : ${analyse.raison}`],
    [!analyse.contexte_suffisant, "Contexte insuffisant pour répondre seul."],
    [analyse.besoin_info_proprietaire, "Il faut une information que vous seul connaissez."],
    [analyse.confiance < (regles.confiance_minimale ?? 0.8), `Confiance trop faible (${Math.round(analyse.confiance * 100)} %).`],
    [Boolean(mot), `Mot à valider toujours présent : « ${mot} ».`],
    [!dansLesHeures(regles.heures_automatiques, maintenant, timeZone), "En dehors des heures de réponse automatique."],
    [envoisDerniereHeure >= (regles.max_reponses_auto_par_contact_par_heure ?? 3), "Limite de réponses automatiques atteinte pour ce contact (anti-boucle)."],
    [dernieresReponses.some(r => normaliser(r) === reponse), "Réponse identique à une réponse déjà envoyée (anti-répétition)."]
  ];
  const bloque = verifs.find(([ko]) => ko);
  return bloque ? { statut: "a_valider", raison: bloque[1] } : { statut: "a_envoyer", raison: "Message simple, toutes les conditions de l'envoi automatique sont remplies." };
}
