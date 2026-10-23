/* TOB-MAQ : service worker de l'application installable.
   - Pages : réseau d'abord, copie locale si pas de connexion (leçons et jeux restent ouverts hors ligne).
   - Icônes et aperçus : copie locale d'abord, mise à jour en arrière-plan.
   - L'API, les vidéos et les PDF ne sont jamais mis en cache ici. */
const VERSION = "tobmaq-v2";
const SHELL = ["/", "/manifest.webmanifest", "/icones/favicon.svg", "/icones/icone-192.png", "/icones/icone-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (/^\/(api|videos|ressources)\//.test(url.pathname)) return;

  if (req.mode === "navigate") {
    e.respondWith(fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put("/", copy)); }
      return res;
    }).catch(() => caches.match("/")));
    return;
  }

  if (/^\/(icones|apercus)\//.test(url.pathname) || url.pathname === "/manifest.webmanifest") {
    e.respondWith(caches.open(VERSION).then(async c => {
      const hit = await c.match(req);
      const fresh = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => hit);
      return hit || fresh;
    }));
  }
});
