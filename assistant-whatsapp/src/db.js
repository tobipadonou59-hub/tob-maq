/* Base de données SQLite (module node:sqlite intégré à Node 22). */
import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { config } from "./config.js";

fs.mkdirSync(config.storageDir, { recursive: true });
export const db = new DatabaseSync(path.join(config.storageDir, "assistant.db"));
db.exec(`
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, contact TEXT NOT NULL, nom TEXT, sens TEXT NOT NULL, type TEXT NOT NULL,
  texte TEXT NOT NULL, at INTEGER NOT NULL, traite INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS messages_contact ON messages (contact, at);
CREATE TABLE IF NOT EXISTS brouillons (
  id INTEGER PRIMARY KEY AUTOINCREMENT, contact TEXT NOT NULL, nom TEXT, messages TEXT NOT NULL, dernier_message_id TEXT,
  analyse TEXT, reponse TEXT NOT NULL DEFAULT '', statut TEXT NOT NULL, raison TEXT NOT NULL DEFAULT '',
  auto INTEGER NOT NULL DEFAULT 0, erreur TEXT, envoye_id TEXT, cree INTEGER NOT NULL, maj INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS brouillons_statut ON brouillons (statut, cree);
CREATE TABLE IF NOT EXISTS contacts_etat (
  contact TEXT PRIMARY KEY, humain_jusqua INTEGER NOT NULL DEFAULT 0, bloque_jusqua INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS reglages (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
`);

export const one = (sql, ...a) => db.prepare(sql).get(...a);
export const all = (sql, ...a) => db.prepare(sql).all(...a);
export const run = (sql, ...a) => db.prepare(sql).run(...a);

export function getSetting(cle, defaut) {
  const r = one("SELECT valeur FROM reglages WHERE cle = ?", cle);
  return r ? JSON.parse(r.valeur) : defaut;
}
export function setSetting(cle, valeur) {
  run("INSERT INTO reglages (cle, valeur) VALUES (?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur", cle, JSON.stringify(valeur));
}

/* Règles : copie de regles.json au premier démarrage, ensuite modifiables depuis le tableau de bord. */
export function getRules() {
  let r = getSetting("regles", null);
  if (!r) { r = JSON.parse(fs.readFileSync(config.defaultRulesFile, "utf8")); setSetting("regles", r); }
  return r;
}

/* Mode (suggestion | validation | automatique) et arrêt d'urgence. Démarrage prudent : suggestion. */
export const getMode = () => getSetting("mode", "suggestion");
export const isPaused = () => getSetting("pause", false);

export function contactState(contact) {
  return one("SELECT * FROM contacts_etat WHERE contact = ?", contact) || { contact, humain_jusqua: 0, bloque_jusqua: 0 };
}
export function setContactState(contact, champ, valeur) {
  if (!["humain_jusqua", "bloque_jusqua"].includes(champ)) throw new Error("champ inconnu");
  run(`INSERT INTO contacts_etat (contact, ${champ}) VALUES (?, ?) ON CONFLICT(contact) DO UPDATE SET ${champ} = excluded.${champ}`, contact, valeur);
}

/* Efface les vieux messages et brouillons terminés (protection de la vie privée). */
export function purge(days = config.retentionDays) {
  const limite = Date.now() - days * 86400000;
  run("DELETE FROM messages WHERE at < ?", limite);
  run("DELETE FROM brouillons WHERE maj < ? AND statut NOT IN ('a_valider', 'suggestion')", limite);
}
