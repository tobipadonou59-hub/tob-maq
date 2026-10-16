/* Donne le rôle administrateur à un compte existant.
   Usage : npm run create-admin -- adresse@exemple.bj */
import { one, run } from "./db.js";

const email = String(process.argv[2] || "").trim().toLowerCase();
if (!email) { console.error("Usage : npm run create-admin -- adresse@exemple.bj"); process.exit(1); }
const u = one("SELECT id FROM users WHERE email = ?", email);
if (!u) { console.error(`Aucun compte avec l'adresse ${email}. Inscris-toi d'abord sur le site.`); process.exit(1); }
run("UPDATE users SET role = 'admin' WHERE id = ?", u.id);
run("DELETE FROM sessions WHERE user_id = ?", u.id);
console.log(`${email} est maintenant administrateur. Reconnecte-toi pour appliquer le changement.`);
