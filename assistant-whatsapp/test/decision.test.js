import { test } from "node:test";
import assert from "node:assert/strict";
import { decider } from "../src/decision.js";

const regles = {
  categories_automatiques: ["salutation", "question_simple"], confiance_minimale: 0.8, max_reponses_auto_par_contact_par_heure: 3,
  mots_toujours_valides: ["prix", "urgent"], contacts: { "229111": { automatique: false } }, contacts_jamais_automatique: []
};
const analyse = { categorie: "salutation", sensible: false, contexte_suffisant: true, besoin_info_proprietaire: false, confiance: 0.95, reponse: "Salut, ça va ?", raison: "" };
const base = { mode: "automatique", pause: false, regles, analyse, contact: "229999", nouveaux: ["Bonjour"], types: ["text"],
  etat: { humain_jusqua: 0, bloque_jusqua: 0 }, envoisDerniereHeure: 0, dernieresReponses: [] };
const d = over => decider({ ...base, ...over });

test("message simple en mode automatique : envoi", () => assert.equal(d({}).statut, "a_envoyer"));
test("mode suggestion et mode validation : jamais d'envoi", () => {
  assert.equal(d({ mode: "suggestion" }).statut, "suggestion");
  assert.equal(d({ mode: "validation" }).statut, "a_valider");
});
test("arrêt d'urgence : jamais d'envoi", () => assert.equal(d({ pause: true }).statut, "suggestion"));
test("spam : ignoré", () => assert.equal(d({ analyse: { ...analyse, categorie: "ne_pas_repondre", reponse: "" } }).statut, "ignore"));
test("chaque garde-fou envoie en validation", () => {
  const cas = [
    { analyse: { ...analyse, sensible: true } },
    { analyse: { ...analyse, categorie: "finance" } },
    { analyse: { ...analyse, contexte_suffisant: false } },
    { analyse: { ...analyse, besoin_info_proprietaire: true } },
    { analyse: { ...analyse, confiance: 0.5 } },
    { nouveaux: ["C'est quoi ton PRIX ?"] },
    { nouveaux: ["c'est urgént"] },
    { types: ["image"] },
    { contact: "229111" },
    { etat: { humain_jusqua: Date.now() + 60000, bloque_jusqua: 0 } },
    { etat: { humain_jusqua: 0, bloque_jusqua: Date.now() + 60000 } },
    { envoisDerniereHeure: 3 },
    { dernieresReponses: ["salut, ça va ?"] },
    { analyse: null },
    { analyse: { refus: true } }
  ];
  for (const c of cas) assert.equal(d(c).statut, "a_valider", JSON.stringify(c));
});
test("heures automatiques, y compris sur la nuit", () => {
  const midi = new Date("2026-10-17T12:00:00Z"), nuit = new Date("2026-10-17T23:30:00Z");
  const r = h => ({ ...regles, heures_automatiques: h });
  assert.equal(d({ regles: r({ debut: "07:00", fin: "22:00" }), maintenant: midi }).statut, "a_envoyer");
  assert.equal(d({ regles: r({ debut: "07:00", fin: "22:00" }), maintenant: nuit }).statut, "a_valider");
  assert.equal(d({ regles: r({ debut: "22:00", fin: "06:00" }), maintenant: nuit }).statut, "a_envoyer");
});
