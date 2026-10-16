# Mettre TOB-MAQ en ligne

## Option simple : Render en un clic (recommandé)
1. Ouvre https://render.com/deploy?repo=https://github.com/tobipadonou59-hub/tob-maq
2. Connecte-toi avec **GitHub** et autorise Render à lire le dépôt `tob-maq`.
3. Dans le champ **ADMIN_EMAILS**, écris ton adresse e-mail (tu deviendras administrateur en t'inscrivant avec elle).
4. Ajoute un moyen de paiement si Render le demande (l'offre « Starter » avec disque permanent est payante : vérifie le prix affiché), puis clique sur **Deploy Blueprint**.
5. Après quelques minutes, Render affiche l'adresse du site (`https://tob-maq-xxxx.onrender.com`). Tout le reste est déjà réglé par `render.yaml` : disque pour les comptes, sécurité HTTPS, adresse du site.

---

## Autre option : Railway

Le fichier `railway.json` indique à Railway comment construire le site (avec le `Dockerfile`) et comment vérifier qu'il fonctionne (`/api/health`).

## 1. Créer le service
1. Sur https://railway.app, connecte-toi avec ton compte GitHub.
2. **New Project → Deploy from GitHub repo → tob-maq**.

## 2. Ajouter le stockage des comptes (indispensable)
Dans le service : **clic droit (ou ⌘K) → Add Volume**, chemin de montage : `/data`.
Sans ce volume, tous les comptes sont effacés à chaque mise à jour.

## 3. Variables (onglet « Variables » → « Raw Editor », coller puis adapter)
```
PUBLIC_URL=https://REMPLACER.up.railway.app
TRUST_PROXY=1
STORAGE_DIR=/data
ADMIN_EMAILS=ton.email@exemple.com
MAIL_FROM=no-reply@tob-maq.bj
```
Facultatif, à ajouter plus tard :
```
BREVO_API_KEY=        # envoi réel des e-mails (accord parental, mot de passe oublié)
OPENAI_API_KEY=       # génération d'images dans le studio IA
CONTACT_EMAIL=        # adresse affichée et destinataire du formulaire de contact
```

## 4. Obtenir l'adresse du site
Onglet **Settings → Networking → Generate Domain**. Railway donne une adresse du type
`https://tob-maq-production.up.railway.app`. Remplace `PUBLIC_URL` par cette adresse exacte (sans `/` à la fin) : Railway redéploie tout seul.

## 5. Vérifier
- `https://TON-ADRESSE/api/health` doit afficher `{"ok":true,...}`.
- Inscris-toi avec l'adresse mise dans `ADMIN_EMAILS` : tu deviens administrateur (menu « Administration »).

## Sauvegarde
Railway permet de faire des sauvegardes du volume (onglet du volume → Backups). Active-les avant d'ouvrir le site au public.

---

## Encaisser les abonnements Premium (FedaPay)

1. **Ouvre un compte marchand** sur https://fedapay.com (pièce d'identité et informations de l'activité demandées).
2. Dans le tableau de bord FedaPay, en **mode Sandbox** (essais), va dans **Paramètres → Clés API** et copie la **clé secrète** (`sk_sandbox_…`).
3. Sur Render → service **tob-maq** → **Environment**, ajoute :
   - `FEDAPAY_SECRET_KEY` = la clé secrète copiée
   - `FEDAPAY_ENV` = `sandbox`
4. Sur le site, **Administration → Abonnements** : fixe le prix (1 mois et/ou 1 an), coche **Ouvrir la vente**, enregistre.
   Copie l'**adresse de notification** affichée et colle-la dans FedaPay → **Webhooks** (événement « transaction approuvée »).
5. Fais un essai complet avec les numéros de test de FedaPay : aucun argent réel n'est prélevé.
6. Quand tout fonctionne et que ton compte FedaPay est validé : remplace la clé par la clé **live** (`sk_live_…`) et `FEDAPAY_ENV` par `live`.

**Sécurité** : la clé secrète ne doit **jamais** être envoyée par message ni écrite dans le code. Elle reste uniquement dans les variables de Render.
Le serveur revérifie chaque paiement auprès de FedaPay avant de débloquer l'accès.

**Contenu premium** : chaque leçon premium est un fichier dans `server/contenus-premium/lecons/` (voir le README de ce dossier). Passe le dépôt GitHub en **privé** avant d'y ajouter du contenu payant.
