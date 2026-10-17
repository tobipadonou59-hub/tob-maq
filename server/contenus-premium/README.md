# Contenus Premium

**Méthode recommandée : l'import depuis le site.** Connecte-toi en administrateur →
Administration → Abonnements → **Leçons Premium**, puis choisis les fichiers `.json`.
Les leçons sont enregistrées dans le dossier de données du serveur (`STORAGE_DIR/premium`,
donc `/data/premium` sur Render) et **ne passent jamais par GitHub**. Il faut un disque
persistant sur Render, sinon elles disparaissent au redémarrage (comme les comptes).

Le serveur sert ces leçons **uniquement** aux abonnés (et aux administrateurs) ; le site les
affiche dans le catalogue, avec un cadenas pour les non-abonnés.

- Le nom du fichier est l'identifiant : lettres minuscules, chiffres et tirets, par ex. `logo-brief.json`.
- Pour qu'une leçon apparaisse dans une formation, utilise l'identifiant d'une leçon déjà listée
  dans `FORMATIONS` (index.html), par ex. `logo-brief`, `logo-construction`, `ae-titres`.
- Champs : `title`, `software`, `level` (Débutant, Intermédiaire ou Avancé), `minutes`, `objective`,
  `intro` (HTML simple : p, strong, em, ul, ol, li, br), `beginner`, `advanced`, `steps`, `params`,
  `illustration`, `caption`, `before`, `after`, `example`, `exercise`, `quiz`, `recap`.
  Le serveur vérifie chaque fichier et explique l'erreur s'il est incomplet.

Le dossier `lecons/` du dépôt ne sert qu'aux tests automatiques : n'y mets pas de vrai contenu
tant que le dépôt GitHub est public.
