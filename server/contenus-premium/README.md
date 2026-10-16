# Contenus Premium

Chaque fichier `lecons/<identifiant>.json` est une leçon réservée aux membres Premium.
Le serveur la sert **uniquement** aux abonnés (et aux administrateurs) ; le site l'affiche
automatiquement dans le catalogue, avec un cadenas pour les non-abonnés.

- L'identifiant (nom du fichier) : lettres minuscules, chiffres et tirets, par ex. `logo-construction`.
- Pour qu'une leçon apparaisse dans une formation, utilise l'identifiant d'une leçon déjà listée
  dans `FORMATIONS` (index.html), par ex. `logo-brief`, `logo-construction`, `ae-titres`.
- Le format est le même que les leçons de `LESSONS` dans `index.html` : `title`, `software`, `level`,
  `minutes`, `objective`, `intro` (HTML), `beginner`, `advanced`, `steps`, `params`, `illustration`,
  `caption`, `example`, `exercise`, `quiz`, `recap`.

⚠️ Le dépôt GitHub doit être **privé**, sinon n'importe qui peut lire ces fichiers sur GitHub.
