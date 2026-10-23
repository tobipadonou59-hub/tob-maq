# Couvertures des formations

`scenes.html` dessine une illustration par formation (SVG 800×320, couleurs TOB-MAQ).
Pour les régénérer : ouvrir la page dans Chromium (Playwright), appeler `draw(id)` pour chaque
clé de `scenes`, faire une capture de `#s`, puis convertir en WebP dans `apercus/formations/<id>.webp`.
Une nouvelle formation sans image garde automatiquement l'ancienne couverture dessinée.
