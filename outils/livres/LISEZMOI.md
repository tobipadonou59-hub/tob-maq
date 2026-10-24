# Livres des formations

Un livre PDF de 10 à 15 pages (format A5) par formation, plus les images des pages pour le lecteur « à feuilleter » de l'application (`#/livres`, `#/livre/<id>`).

- `livre.html` : modèle de mise en page (couverture, sommaire, fiche, chapitres, quiz, glossaire, projet, dos).
- `contenu/*.json` : textes rédigés pour chaque formation (accroche, glossaire, mémo, projet, et chapitres des leçons qui n'ont pas encore de contenu complet dans l'application). Les leçons complètes sont reprises directement de `index.html`, le quiz de `server/contenus/examens.json`.
- `generer.cjs` : `node outils/livres/generer.cjs [id ...]` produit `ressources/livres/<id>.pdf`, `apercus/livres/<id>/NN.webp` et `apercus/livres/index.json`.

Si un livre dépasse 15 pages, le générateur le compacte automatiquement ; s'il en fait moins de 10, il ajoute des pages « Mes notes ».
