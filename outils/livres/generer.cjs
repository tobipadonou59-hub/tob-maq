/* Génère les livres de formation TOB-MAQ (PDF A5 de 10 à 15 pages + images des pages pour le lecteur).
   Usage : node outils/livres/generer.cjs [id-formation ...]
   Sorties : ressources/livres/<id>.pdf, apercus/livres/<id>/NN.webp, apercus/livres/index.json
   Nécessite : Playwright (Chromium) et Pillow (python3) pour la conversion WebP. */
const fs = require("fs"), path = require("path"), { execFileSync } = require("child_process");
let chromium; try { ({ chromium } = require("playwright")); } catch { ({ chromium } = require("/opt/node-tools/node_modules/playwright")); }

const ROOT = path.resolve(__dirname, "../.."), HERE = __dirname;
const OUT_PDF = path.join(ROOT, "ressources/livres"), OUT_IMG = path.join(ROOT, "apercus/livres");
const CONTENU = Object.assign({}, ...fs.readdirSync(path.join(HERE, "contenu")).filter(f => f.endsWith(".json")).map(f => JSON.parse(fs.readFileSync(path.join(HERE, "contenu", f), "utf8"))));
const EXAMS = JSON.parse(fs.readFileSync(path.join(ROOT, "server/contenus/examens.json"), "utf8"));
const strip = h => String(h || "").replace(/<(?!\/?(strong|em|code)\b)[^>]+>/g, " ").replace(/\s+/g, " ").trim();

function pickQuiz(fid, data) {
  let qs = EXAMS[fid]?.questions || [];
  if (!qs.length) qs = data.FORMATIONS.find(f => f.id === fid).modules.flatMap(m => m.lessons).flatMap(l => data.LESSONS[l]?.quiz || []);
  // Sélection régulière et stable (pas de hasard : le livre reste identique d'une génération à l'autre)
  const n = Math.min(8, qs.length), step = qs.length / n;
  return Array.from({ length: n }, (_, i) => qs[Math.floor(i * step)]);
}

function bookFor(f, data) {
  const c = CONTENU[f.id];
  if (!c) throw new Error(`Contenu manquant pour ${f.id}`);
  const chapters = f.modules.flatMap(m => m.lessons.map(id => {
    const L = data.LESSONS[id] || {}, x = c.chapitres?.[id];
    if (L.steps) return { title: L.title, module: m.title, minutes: L.minutes, objective: L.objective, intro: strip(L.intro), notions: L.steps.map(s => [s.t, strip(s.d)]), beginner: L.beginner, tip: L.advanced, example: L.example, recap: L.recap, exercise: L.exercise };
    if (!x) throw new Error(`Chapitre manquant : ${f.id} / ${id}`);
    return { title: L.title || x.titre, module: m.title, minutes: L.minutes, objective: x.objectif, intro: x.intro, notions: x.notions, tip: x.astuce, example: x.exemple, exercise: x.exercice, code: x.code };
  }));
  return { f, domain: data.DOMAINS.find(d => d.id === f.domain)?.name || f.domain, software: f.software.map(s => data.SOFTWARE.find(x => x.id === s)?.name || s),
    chapters, quiz: pickQuiz(f.id, data), glossary: c.glossaire, memo: c.memo, project: c.projet, accroche: c.accroche };
}

// Versions de plus en plus compactes si le livre dépasse 15 pages
const SHRINK = [b => b, b => ({ ...b, chapters: b.chapters.map(c => ({ ...c, beginner: null })) }), b => ({ ...b, quiz: b.quiz.slice(0, 6), chapters: b.chapters.map(c => ({ ...c, beginner: null, recap: (c.recap || []).slice(0, 3) })) }),
  b => ({ ...b, quiz: b.quiz.slice(0, 5), chapters: b.chapters.map(c => ({ ...c, beginner: null, recap: null, tip: null })) })];

(async () => {
  const only = process.argv.slice(2);
  const browser = await chromium.launch();
  // Données des formations : lues directement dans l'application
  const app = await browser.newPage();
  await app.goto("file://" + path.join(ROOT, "index.html")); await app.waitForTimeout(800);
  const data = await app.evaluate(() => ({ FORMATIONS, LESSONS, DOMAINS: DOMAINS.map(d => ({ id: d.id, name: d.name })), SOFTWARE: SOFTWARE.map(s => ({ id: s.id, name: s.name })) }));
  await app.close();
  const page = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2 });
  await page.goto("file://" + path.join(HERE, "livre.html")); await page.evaluate(() => document.fonts.ready);
  fs.mkdirSync(OUT_PDF, { recursive: true }); fs.mkdirSync(OUT_IMG, { recursive: true });
  const idxFile = path.join(OUT_IMG, "index.json"), index = fs.existsSync(idxFile) ? JSON.parse(fs.readFileSync(idxFile, "utf8")) : {};
  for (const f of data.FORMATIONS) {
    if (only.length && !only.includes(f.id)) continue;
    const base = bookFor(f, data);
    let n = 0;
    for (const s of SHRINK) { n = await page.evaluate(b => build(b), s(base)); if (n <= 15) break; }
    await page.evaluate(() => Promise.all([...document.images].map(i => i.decode().catch(() => {}))));
    await page.evaluate(() => document.fonts.ready);
    await page.pdf({ path: path.join(OUT_PDF, f.id + ".pdf"), width: "148mm", height: "210mm", printBackground: true, preferCSSPageSize: true });
    const dir = path.join(OUT_IMG, f.id); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const els = await page.$$(".page");
    for (let i = 0; i < els.length; i++) await els[i].screenshot({ path: path.join(dir, String(i + 1).padStart(2, "0") + ".png") });
    execFileSync("python3", ["-c", `import sys,glob,os
from PIL import Image
for p in sorted(glob.glob(sys.argv[1]+'/*.png')):
    im=Image.open(p).convert('RGB'); im=im.resize((840, round(840*im.height/im.width)), Image.LANCZOS)
    im.save(p[:-4]+'.webp','WEBP',quality=80,method=6); os.remove(p)`, dir]);
    index[f.id] = { pages: els.length, title: f.title };
    console.log(`${f.id} : ${els.length} pages`);
  }
  fs.writeFileSync(idxFile, JSON.stringify(index, null, 0));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
