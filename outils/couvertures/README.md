# Couvertures des formations

`scenes.html` dessine une illustration par formation et par domaine (SVG 800×320, couleurs TOB-MAQ).
Les scènes `domaine-<id>` vont dans `apercus/domaines/<id>.webp` (cartes « Nos domaines de formation »).
Pour les régénérer : ouvrir la page dans Chromium (Playwright), appeler `draw(id)` pour chaque
clé de `scenes`, faire une capture de `#s`, puis convertir en WebP dans `apercus/formations/<id>.webp`.
Une nouvelle formation sans image garde automatiquement l'ancienne couverture dessinée.
