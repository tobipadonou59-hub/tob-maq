/* Téléchargement de l'application :
   - /telecharger            → page « Télécharger l'application » (lien court à partager, QR code)
   - /telecharger/android    → fichier APK Android, s'il a été publié par l'administrateur
   L'APK est gardé dans STORAGE_DIR/appli (jamais dans le dépôt GitHub). */
import fs from "node:fs";
import path from "node:path";
import multer from "multer";
import { config } from "./config.js";
import { fail } from "./security.js";

const DIR = path.join(config.storageDir, "appli"), APK = path.join(DIR, "tob-maq.apk");
fs.mkdirSync(DIR, { recursive: true });
const MAX_MB = 150;

const apkInfo = () => { try { const s = fs.statSync(APK); return { apk: true, sizeMb: Math.round(s.size / 1048576 * 10) / 10, updatedAt: s.mtime.toISOString() }; } catch { return { apk: false }; } };

export function registerAppDownloads(app, api, { needAdmin }) {
  app.get("/telecharger", (req, res) => res.redirect(302, "/#/application"));
  app.get("/telecharger/android", (req, res) => {
    if (!apkInfo().apk) return res.redirect(302, "/#/application");
    res.set({ "Content-Type": "application/vnd.android.package-archive", "Content-Disposition": 'attachment; filename="TOB-MAQ.apk"', "Cache-Control": "no-cache" });
    res.sendFile(APK);
  });
  api.get("/app/info", (req, res) => res.json(apkInfo()));

  const upload = multer({ storage: multer.diskStorage({ destination: DIR, filename: (req, file, cb) => cb(null, "envoi-" + Date.now() + ".tmp") }), limits: { fileSize: MAX_MB * 1048576, files: 1, fields: 5 } });
  api.post("/admin/app/apk", needAdmin, upload.single("file"), (req, res) => {
    if (!req.file) fail(400, "Ajoute le fichier .apk.");
    const fd = fs.openSync(req.file.path, "r"), head = Buffer.alloc(4); fs.readSync(fd, head, 0, 4, 0); fs.closeSync(fd);
    // Un APK est une archive ZIP : il commence par « PK\x03\x04 ».
    if (!(head[0] === 0x50 && head[1] === 0x4b && head[2] === 3 && head[3] === 4) || !/\.apk$/i.test(req.file.originalname || "")) { fs.rmSync(req.file.path, { force: true }); fail(400, "Ce fichier n'est pas un APK Android valide."); }
    fs.renameSync(req.file.path, APK);
    res.status(201).json(apkInfo());
  });
  api.delete("/admin/app/apk", needAdmin, (req, res) => { fs.rmSync(APK, { force: true }); res.json(apkInfo()); });
}
