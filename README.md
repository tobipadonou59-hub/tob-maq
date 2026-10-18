# TOB-MAQ

> **Imagine. Crée. Maîtrise.**
> L'académie numérique du graphisme, du maquettisme et du montage vidéo au Bénin (15–40 ans).

Ce dépôt contient la plateforme complète :
- **le site** : `index.html`, en HTML, CSS et JavaScript, sans framework ;
- **le serveur** : `server/`, en Node.js avec SQLite. Il sert le site et son API à la même adresse et gère les comptes, la progression, le portfolio, la modération, les quotas d'IA et l'administration.

Ouvert sans serveur, le site reste utilisable (jeux, cours, ressources) : les fonctions qui exigent un compte l'indiquent clairement, sans rien simuler.

```
tob-maq/
├── index.html                        ← le site complet (design, 21 pages, jeux, studio IA, données de démo)
├── ressources/                       ← 5 PDF réels, licence CC BY 4.0
├── apercus/                          ← vignettes PNG des PDF (première page)
├── outils/generer_ressources.py      ← régénère les PDF et leurs aperçus
├── outils/construire_publication.py  ← construit la version en ligne et le QR code
├── publication/                      ← version publiée et QR code (générés)
├── server/                           ← serveur Node.js (API, base SQLite, tests)
│   ├── src/index.js                  ← routes de l'API et service du site
│   ├── src/db.js · security.js · ai.js · mail.js
│   ├── test/api.test.js              ← 10 tests d'intégration
│   └── .env.example                  ← modèle de configuration
└── Dockerfile                        ← image de production (site + API)
```

---

## 1. Lancer TOB-MAQ avec son serveur (recommandé)

Prérequis : **Node.js 22.13 ou plus récent**.

```bash
cd tob-maq/server
npm install
cp .env.example .env          # puis renseignez au minimum PUBLIC_URL et ADMIN_EMAILS
npm start
```
Ouvrez **http://localhost:8080**. Le serveur sert le site et branche automatiquement l'API (`/api`).

- **Devenir administrateur** : mettez votre adresse e-mail dans `ADMIN_EMAILS` avant de vous inscrire, ou, après l'inscription, lancez `npm run create-admin -- vous@exemple.bj`.
- **E-mails** (accord parental, mot de passe oublié) : sans `BREVO_API_KEY`, ils s'affichent dans le terminal du serveur, ce qui est pratique pour tester.
- **IA** : sans `OPENAI_API_KEY`, le studio affiche « service non configuré ». Avec une clé, la génération d'images fonctionne, avec un quota par jour et un budget mensuel en FCFA réglables dans l'administration. Aucun fournisseur vidéo n'est branché pour l'instant (voir `server/src/ai.js` pour en ajouter un).
- **Tests** : `npm test` (10 tests : comptes, CSRF, progression, accord parental, IA, portfolio et modération, mot de passe oublié, limitation des tentatives).

### Mettre en ligne (Railway, Render, Fly.io, VPS…)
Le `Dockerfile` à la racine produit une image unique (site + API). Chez l'hébergeur :
1. Déployez le dépôt avec ce Dockerfile.
2. Montez un **volume persistant sur `/data`**. Il contient la base de données et les fichiers envoyés ; sans lui, tout est perdu à chaque redéploiement.
3. Définissez les variables d'environnement de `server/.env.example`, dont `PUBLIC_URL` (votre adresse en `https://…`), `TRUST_PROXY=1` et `ADMIN_EMAILS`.
4. Ajoutez votre nom de domaine. L'hébergeur fournit le certificat HTTPS.

Sur un VPS sans Docker : `npm ci --omit=dev` dans `server/`, puis lancez `npm start` avec un gestionnaire de processus (systemd, pm2) derrière Nginx ou Caddy en HTTPS.

**Sauvegardes** : copiez régulièrement le dossier `/data` (ou `server/storage`).

### Sans serveur
`python3 -m http.server 8000` à la racine, puis http://localhost:8000. Jeux, cours et ressources fonctionnent ; les comptes et l'IA indiquent qu'un serveur est nécessaire.

---

## 2. Ce qui fonctionne, ce qui attend un serveur

| Fonction | État |
|---|---|
| 21 pages, navigation, menu mobile, recherche globale | ✅ Fonctionnel |
| Thème clair / sombre / système, taille du texte, contraste renforcé, réduction des animations | ✅ Fonctionnel, mémorisé sur l'appareil |
| Catalogue, filtres (domaine, logiciel, niveau, prix), pages des 3 domaines, 12 logiciels détaillés par niveau | ✅ Fonctionnel |
| **8 leçons complètes** (objectif, explication adaptée au niveau, tutoriel, raccourcis, paramètres, illustration, avant/après, exemple, exercice, fichier, quiz, fiche) | ✅ Contenus de démonstration à faire valider |
| **63 jeux jouables** dans les 10 domaines, 3 niveaux chacun, points, indices, corrections, défi du jour et défi de la semaine | ✅ Fonctionnel ; progression enregistrée sur l'appareil, ou dans le compte une fois le serveur branché |
| 5 démonstrations interactives (étalonnage, calques, profondeur de champ, typographie, timeline) | ✅ Fonctionnel, sans IA |
| Bibliothèque : 5 vrais PDF téléchargeables, aperçus, licences, favoris, historique | ✅ Fonctionnel |
| Inscription (avec accord parental de 15 à 17 ans), connexion, mot de passe oublié, synchronisation de la progression entre appareils | ✅ Avec le serveur inclus |
| Portfolio : envoi, modération, publication, signalement, confidentialité des mineurs | ✅ Avec le serveur inclus |
| Administration (statistiques, ressources, IA et quotas, modération, utilisateurs, annonces) | ✅ Avec le serveur inclus, réservée au rôle `admin` |
| Studio IA : génération d'images et de démonstrations, quotas, budget en FCFA | ✅ Avec le serveur et une clé `OPENAI_API_KEY` (non testé avec une vraie clé) |
| Studio IA : génération de vidéos | ⚠️ Aucun fournisseur vidéo branché pour l'instant |
| Envoi réel des e-mails | ⚠️ Nécessite `BREVO_API_KEY` ; sinon affichés dans le journal du serveur |
| Paiements (offres premium, crédits IA) en FCFA | ⛔ Désactivés (`PAYMENTS_ENABLED: false`) |

---

## 3. Personnaliser les contenus

Tout se trouve dans `index.html`, section **« 2. DONNÉES »** du script :

| Constante | Contenu |
|---|---|
| `DOMAINS` | Les 10 domaines (graphisme, maquettisme, montage vidéo, création web, développement, jeux vidéo, dessin et illustration, informatique et réseaux, marketing digital, business et finance) et leurs modules (liés aux leçons ou formations) |
| `SOFTWARE` | Logiciels, systèmes, licence, fonctionnalités par niveau |
| `FORMATIONS` | Formations : domaine, logiciels, niveau, durée, `price: "gratuit" \| "premium"`, modules |
| `LESSONS` | Leçons complètes, ou annoncées (`soon: true`) |
| `RESOURCES` | Ressources : `file` (fichier réel) ou `null` (« Bientôt disponible »), licence, aperçu |
| `PORTFOLIO` | Projets d'exemple de l'équipe (à remplacer par les vrais projets venant du serveur) |
| `POOLS`, `GAMES` | Banques de questions et liste des jeux |

**Ajouter une leçon** : copiez une leçon existante dans `LESSONS` (par exemple `"dr-etalonnage"`), changez l'identifiant et le contenu, puis ajoutez l'identifiant dans les `modules` d'une formation. Champs utiles :
- `beginner` / `advanced` : conseils affichés selon le niveau choisi dans le profil.
- `steps[].keys` : raccourcis clavier affichés sous forme de touches.
- `params` : paramètres importants.
- `illustration` : `wheel`, `typo`, `mask`, `bleed`, `grid`, `timeline`, `safezone` ou `grade` (avant/après).
- `video` : adresse d'une vidéo, chargée seulement quand on appuie sur lecture.
- `resource` : identifiant d'une ressource à télécharger.
- `demo: true` : badge « Démo ». Retirez-le après validation par un formateur.

**Ajouter des questions de jeu** : ajoutez une ligne dans `POOLS` au format `[niveau 1-3, question, [choix], index_bonne_réponse, explication, indice]`.

**Ajouter un fichier téléchargeable** : déposez-le dans `ressources/`, ajoutez son aperçu dans `apercus/` si possible, puis renseignez `file`, `size` et `licence` dans `RESOURCES`. N'ajoutez jamais un fichier dont la licence n'est pas vérifiée (polices, photos, musiques, LUTs, effets sonores).

---

## 4. Services externes à brancher

| Besoin | Options conseillées | Remarques |
|---|---|---|
| **Backend / API** | Node.js (NestJS ou Express), Laravel, Django, ou **Supabase** (Edge Functions) | Toutes les routes du § 5 |
| **Base de données** | PostgreSQL (Supabase, Neon, Railway, OVH) | Utilisateurs, progression, projets, quotas, signalements |
| **Authentification** | Supabase Auth, Auth.js, Lucia, ou une solution maison avec Argon2id | Session par cookie `HttpOnly`, `Secure`, `SameSite=Lax` ; 2FA pour les administrateurs |
| **Stockage de fichiers** | Cloudflare R2, Amazon S3, Supabase Storage | Fichiers privés et **liens signés** temporaires pour les ressources réservées |
| **Génération d'images** | Un fournisseur d'API d'images (par exemple OpenAI Images, Stability AI, Google Imagen, Replicate) | Clé **uniquement** dans les variables d'environnement du serveur |
| **Génération de vidéos** | Un fournisseur d'API vidéo (par exemple Runway, Luma, Google Veo, Replicate) | Tâches asynchrones : le serveur renvoie `jobId`, le site interroge l'avancement |
| **Modération** | Filtre de contenu du fournisseur d'IA, plus une file de modération humaine pour le portfolio | Obligatoire, surtout pour les mineurs |
| **E-mails** | Brevo, Postmark, Resend, Mailjet | Confirmation d'inscription, accord parental, réinitialisation du mot de passe |
| **Paiements (plus tard)** | FedaPay ou KKiaPay (Mobile Money au Bénin), Stripe pour les cartes | Ne jamais activer sans prestataire configuré ; prix en FCFA |
| **Journalisation des erreurs** | Sentry, Better Stack, ou journaux du serveur | Sans données personnelles inutiles |
| **Vidéos de cours** | Bunny Stream, Cloudflare Stream, Mux | Lecture adaptative, adaptée aux connexions lentes |

Comparez les tarifs et conditions actuels de chaque fournisseur avant de choisir : ils évoluent souvent.

---

## 5. API attendue par le site

Dans `index.html`, renseignez `CONFIG.API_BASE_URL` (en HTTPS). Toutes les requêtes envoient le cookie de session (`credentials: "include"`). En cas d'erreur, renvoyez le code HTTP adapté et `{ "message": "Texte en français", "code": "..." }`.

| Méthode | Route | Corps → réponse |
|---|---|---|
| POST | `/auth/register` | `{ displayName, email, password, interests[], level, ageGroup, parentEmail?, acceptTerms }` → `{ user }` |
| POST | `/auth/login` | `{ email, password }` → `{ user }` |
| POST | `/auth/logout` | → 204 |
| GET | `/auth/me` | → `{ user }` ou 401 |
| POST | `/auth/forgot-password` | `{ email }` → 204 (réponse identique, que le compte existe ou non) |
| PATCH | `/me` | `{ displayName, interests, level }` → `{ user }` |
| POST | `/me/lessons` · `/me/games` · `/me/downloads` · `/me/favorites` | progression, scores, historique, favoris |
| GET | `/me/projects` · `/me/creations` | listes de l'utilisateur |
| POST | `/me/creations` | `{ id }` : enregistre une création IA |
| GET | `/ai/config` | `{ image: { styles, sizes: [[id, libellé]] }, video: { ratios, durations, imageToVideo }, quota: { images: {used, limit}, videos: {used, limit} } }` |
| POST | `/ai/images` | `{ prompt, style, size, usage, variantOf? }` → `{ images: [{ id, url }], quota }` |
| POST | `/ai/videos` | formulaire multipart (`prompt`, `mood`, `cameraMove`, `ratio`, `duration`, `image?`) → `{ jobId }` |
| GET / DELETE | `/ai/jobs/:id` | `{ status: "queued" \| "running" \| "done" \| "failed", url?, message? }` / annulation |
| POST | `/ai/demos` | `{ topic, details }` → `{ url }` |
| POST | `/portfolio` | formulaire multipart (`title`, `discipline`, `description`, `tools`, `visibility`, `file`) |
| POST | `/reports` · `/contact` | signalement, message de contact |
| GET / PATCH | `/admin/ai-config` | quotas journaliers, budget mensuel en FCFA, services activés |
| GET / POST | `/admin/stats`, `/admin/formations`, `/admin/resources`, `/admin/reports`, `/admin/users`, `/admin/announcements` | administration |

Objet `user` : `{ displayName, email, level, interests, role: "membre" | "admin", ageGroup: "adulte" | "mineur", pendingParentalConsent }`.

### Règles impératives côté serveur
- **Clés API, secrets et mots de passe** : uniquement dans les variables d'environnement ou un coffre de secrets, jamais dans `index.html`.
- **Mots de passe** hachés avec Argon2id ou bcrypt ; limitation des tentatives de connexion.
- **CORS** limité au domaine du site ; protection **CSRF** (cookie `SameSite` et vérification de l'en-tête `Origin`).
- **Quotas IA** vérifiés **avant** chaque appel au fournisseur, avec un budget mensuel plafonné ; journalisation de chaque génération (utilisateur, coût estimé).
- **Rôle `admin`** vérifié sur chaque route `/admin/*`, pas seulement dans l'interface.
- **Fichiers envoyés** : contrôle du type et de la taille, analyse antivirus, publication seulement après modération.
- **Mineurs (15–17 ans)** : compte limité tant que le parent n'a pas confirmé, portfolio jamais public, aucune donnée personnelle affichée.
- Conformité avec le cadre béninois de protection des données personnelles (Code du numérique, APDP), avec l'appui d'un juriste.

---

## 6. Version en ligne et QR code

- Site publié : **https://claude.ai/artifact/XW2MjnwGZy6ugVrumpkp6b** (privé : visible par son propriétaire et par les personnes avec qui il est partagé depuis le menu « Partager »).
- QR code : `publication/qr-tob-maq.png`.

Pour régénérer après une modification :

```bash
python3 outils/construire_publication.py --qr "<URL publique>"
```
Cette commande produit `publication/tob-maq.html`, la version adaptée à l'hébergement sur claude.ai (téléchargements via la fonction de téléchargement de claude.ai), ainsi que `publication/qr-tob-maq.png`.

---

## 7. Avant l'ouverture publique

- [ ] Faire relire et valider chaque leçon par un formateur, puis retirer `demo: true`.
- [ ] Remplacer les projets d'exemple du portfolio par de vrais projets, publiés avec l'accord de leurs auteurs.
- [ ] Brancher le backend, l'authentification, le stockage et le service d'IA, puis tester les quotas.
- [ ] Faire valider les conditions d'utilisation et la politique de confidentialité par un juriste.
- [ ] Renseigner `CONTACT_EMAIL`.
- [ ] Tester sur un téléphone Android d'entrée de gamme avec une connexion 3G.
