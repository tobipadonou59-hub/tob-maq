/* Base de données SQLite (module node:sqlite intégré à Node 22). */
import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { config } from "./config.js";

fs.mkdirSync(config.storageDir, { recursive: true });
for (const d of ["uploads", "ai", "projects"]) fs.mkdirSync(path.join(config.storageDir, d), { recursive: true });

export const db = new DatabaseSync(path.join(config.storageDir, "tobmaq.db"));
db.exec(`
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'membre', level TEXT, interests TEXT NOT NULL DEFAULT '[]',
  age_group TEXT NOT NULL, parent_email TEXT, parent_consent_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tokens (
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, expires_at INTEGER NOT NULL, used_at TEXT);
CREATE TABLE IF NOT EXISTS lessons (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, lesson_id TEXT NOT NULL, done_at TEXT NOT NULL,
  PRIMARY KEY (user_id, lesson_id));
CREATE TABLE IF NOT EXISTS games (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, game_id TEXT NOT NULL, level TEXT NOT NULL,
  best INTEGER NOT NULL DEFAULT 0, plays INTEGER NOT NULL DEFAULT 0, last_at TEXT, PRIMARY KEY (user_id, game_id, level));
CREATE TABLE IF NOT EXISTS favorites (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, resource_id TEXT NOT NULL, PRIMARY KEY (user_id, resource_id));
CREATE TABLE IF NOT EXISTS downloads (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, resource_id TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS creations (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, type TEXT NOT NULL,
  prompt TEXT NOT NULL, file TEXT NOT NULL, mime TEXT NOT NULL, saved INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_usage (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, kind TEXT NOT NULL,
  cost_fcfa INTEGER NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT NOT NULL,
  discipline TEXT NOT NULL, description TEXT NOT NULL, tools TEXT NOT NULL DEFAULT '[]', visibility TEXT NOT NULL,
  file TEXT NOT NULL, mime TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, reporter_id TEXT, reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ouvert', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS announcements (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS uploaded_resources (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, licence TEXT NOT NULL, file TEXT NOT NULL, original_name TEXT NOT NULL,
  mime TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_usage_user ON ai_usage(user_id, kind, at);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
`);

export const one = (sql, ...p) => db.prepare(sql).get(...p);
export const all = (sql, ...p) => db.prepare(sql).all(...p);
export const run = (sql, ...p) => db.prepare(sql).run(...p);
export const now = () => new Date().toISOString();

const AI_DEFAULTS = { dailyImageQuota: 5, dailyVideoQuota: 1, monthlyBudget: 50000, imageEnabled: true, videoEnabled: false };
export function getAiSettings() {
  const r = one("SELECT value FROM settings WHERE key = 'ai'");
  return { ...AI_DEFAULTS, ...(r ? JSON.parse(r.value) : {}) };
}
export function setAiSettings(v) {
  run("INSERT INTO settings(key, value) VALUES('ai', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", JSON.stringify(v));
}
