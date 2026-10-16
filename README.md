# TOB-MAQ

> **Imagine. Crée. Maîtrise.**
> L'académie numérique du graphisme, du maquettisme et du montage vidéo au Bénin (15–40 ans).

Ce dépôt contient la **première version front-end** de la plateforme : un site complet dans `index.html`, en HTML, CSS et JavaScript, sans framework ni dépendance à installer. Les fonctions qui exigent un serveur (comptes, stockage, IA, paiements) sont **prêtes côté navigateur** mais **ne sont pas simulées** : elles affichent clairement qu'un backend est nécessaire.

```
tob-maq/
├── index.html                        ← le site complet (design, 21 pages, jeux, studio IA, données de démo)
├── ressources/                       ← 5 PDF réels, licence CC BY 4.0
├── apercus/                          ← vignettes PNG des PDF (première page)
├── outils/generer_ressources.py      ← régénère les PDF et leurs aperçus
├── outils/construire_publication.py  ← construit la version en ligne et le QR code
└── publication/                      ← version publiée et QR code (générés)
```

---

## 1. Lancer le site

```bash
cd tob-maq
python3 -m http.server 8000
```
Ouvrez **http://localhost:8000**. Vous pouvez aussi double-cliquer sur `index.html`, mais certains navigateurs bloquent alors les téléchargements.

**Mise en ligne** : déposez le dossier tel quel sur Netlify, Vercel, Cloudflare Pages, GitHub Pages ou chez un hébergeur classique. Activez la compression gzip ou brotli : le fichier passe d’environ 300 Ko à environ 90 Ko.

---

## 2. Ce qui fonctionne, ce qui attend un serveur

| Fonction | État |
|---|---|
| 21 pages, navigation, menu mobile, recherche globale | ✅ Fonctionnel |
| Thème clair / sombre / système, taille du texte, contraste renforcé, réduction des animations | ✅ Fonctionnel, mémorisé sur l'appareil |
| Catalogue, filtres (domaine, logiciel, niveau, prix), pages des 3 domaines, 12 logiciels détaillés par niveau | ✅ Fonctionnel |
| **8 leçons complètes** (objectif, explication adaptée au niveau, tutoriel, raccourcis, paramètres, illustration, avant/après, exemple, exercice, fichier, quiz, fiche) | ✅ Contenus de démonstration à faire valider |
| **13 jeux jouables**, 3 niveaux chacun, points, indices, corrections, défi du jour et défi de la semaine | ✅ Fonctionnel ; progression enregistrée sur l'appareil, ou dans le compte une fois le serveur branché |
| 5 démonstrations interactives (étalonnage, calques, profondeur de champ, typographie, timeline) | ✅ Fonctionnel, sans IA |
| Bibliothèque : 5 vrais PDF téléchargeables, aperçus, licences, favoris, historique | ✅ Fonctionnel |
| Inscription (avec accord parental de 15 à 17 ans), connexion, mot de passe oublié | ⚠️ Serveur requis |
| Studio IA : images, vidéos (suivi des tâches), démonstrations par IA, quotas | ⚠️ Serveur et service d'IA requis. Sans eux, la page montre la requête qui serait envoyée |
| Publication et signalement dans le portfolio, projets enregistrés, contact | ⚠️ Serveur requis |
| Administration (statistiques, ressources, IA et quotas, modération, utilisateurs, annonces) | ⚠️ Serveur requis, accès réservé au rôle `admin` |
| Paiements (offres premium, crédits IA) en FCFA | ⛔ Désactivés (`PAYMENTS_ENABLED: false`) |

---

## 3. Personnaliser les contenus

Tout se trouve dans `index.html`, section **« 2. DONNÉES »** du script :

| Constante | Contenu |
|---|---|
| `DOMAINS` | Les 3 domaines et leurs modules (liés aux leçons ou formations) |
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
