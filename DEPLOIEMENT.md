# Mettre TOB-MAQ en ligne sur Railway

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
