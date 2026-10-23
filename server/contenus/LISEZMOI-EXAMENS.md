# Banque des examens finaux

- `examens.json` : utilisé par le serveur. Pour chaque formation : titre, leçons à terminer et questions
  (questions des quiz des leçons + questions complémentaires de `examens-extra/<formation>.json`).
- Chaque examen tire 10 questions au hasard ; il faut 10/10 pour obtenir le certificat.
- Une formation dont aucune leçon n'est encore publiée n'a pas d'examen : ajoute-la ici quand ses leçons sortent
  (au moins 12 questions pour que les essais varient).
