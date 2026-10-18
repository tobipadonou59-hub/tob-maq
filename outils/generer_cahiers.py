"""
Génère les cahiers d'exercices PDF de TOB-MAQ (exercices + corrigés) et leurs aperçus.

Usage : python3 outils/generer_cahiers.py
Nécessite : reportlab ; pdftoppm (poppler-utils) pour les aperçus.
Le script affiche à la fin les entrées à recopier dans RESOURCES (index.html).
"""
import subprocess
import sys
from pathlib import Path
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generer_ressources import (OUT, PREV, W, H, INK, NIGHT, VIOLET, ORANGE, MUTED, LINE, PAPER,  # noqa: E402
                                entete, pied)

MARGE = 42
LARGEUR = W - 2 * MARGE
BAS = 58
OK = HexColor("#16794A")
CODE_BG = HexColor("#0F1320")
CODE_INK = HexColor("#E6E8F0")


class Cahier:
    def __init__(self, fichier, titre, sous_titre):
        self.c = canvas.Canvas(str(OUT / fichier), pagesize=(W, H))
        self.c.setTitle(titre)
        self.c.setAuthor("TOB-MAQ")
        self.titre, self.page = titre, 1
        entete(self.c, titre, sous_titre)
        self.y = H - 124

    def nouvelle_page(self):
        pied(self.c, self.page)
        self.c.showPage()
        self.page += 1
        self.c.setFillColor(NIGHT)
        self.c.rect(0, H - 34, W, 34, stroke=0, fill=1)
        self.c.setFillColor(white)
        self.c.setFont("Sans-Bold", 9)
        self.c.drawString(MARGE, H - 22, "TOB-MAQ · " + self.titre)
        self.y = H - 62

    def place(self, h):
        if self.y - h < BAS:
            self.nouvelle_page()

    def texte(self, txt, police="Sans", taille=10, couleur=INK, retrait=0, interligne=1.42, apres=6):
        lignes = simpleSplit(txt, police, taille, LARGEUR - retrait)
        for ligne in lignes:
            self.place(taille * interligne)
            self.c.setFont(police, taille)
            self.c.setFillColor(couleur)
            self.c.drawString(MARGE + retrait, self.y - taille, ligne)
            self.y -= taille * interligne
        self.y -= apres

    def titre_section(self, txt, couleur=VIOLET):
        self.place(46)
        self.y -= 8
        self.c.setFillColor(couleur)
        self.c.rect(MARGE, self.y - 22, 4, 22, stroke=0, fill=1)
        self.c.setFont("Sans-Bold", 15)
        self.c.setFillColor(INK)
        self.c.drawString(MARGE + 12, self.y - 17, txt)
        self.y -= 34

    def exercice(self, n, ex):
        self.place(70)
        self.c.setFillColor(PAPER)
        self.c.roundRect(MARGE, self.y - 30, LARGEUR, 30, 6, stroke=0, fill=1)
        self.c.setFillColor(ORANGE)
        self.c.setFont("Sans-Bold", 11)
        self.c.drawString(MARGE + 10, self.y - 19, f"Exercice {n}")
        self.c.setFillColor(INK)
        self.c.drawString(MARGE + 84, self.y - 19, ex["titre"])
        self.c.setFillColor(MUTED)
        self.c.setFont("Sans", 8.5)
        self.c.drawRightString(W - MARGE - 10, self.y - 19, f'{ex["niveau"]} · {ex["duree"]}')
        self.y -= 40
        self.texte(ex["consigne"])
        for i, etape in enumerate(ex.get("etapes", []), 1):
            self.texte(f"{i}. {etape}", retrait=10, apres=2)
        if ex.get("code"):
            self.code(ex["code"])
        if ex.get("criteres"):
            self.y -= 2
            self.texte("Critères de réussite :", police="Sans-Bold", taille=9.5, apres=3)
            for crit in ex["criteres"]:
                self.place(14)
                self.c.setStrokeColor(MUTED)
                self.c.rect(MARGE + 10, self.y - 9.5, 8, 8, stroke=1, fill=0)
                self.texte(crit, taille=9.5, retrait=24, apres=1)
        self.y -= 12

    def code(self, src):
        lignes = src.strip("\n").split("\n")
        h = len(lignes) * 11.5 + 14
        if h > self.y - BAS:
            self.nouvelle_page()
        self.c.setFillColor(CODE_BG)
        self.c.roundRect(MARGE + 6, self.y - h, LARGEUR - 12, h, 6, stroke=0, fill=1)
        self.c.setFillColor(CODE_INK)
        self.c.setFont("Mono", 8.5)
        yy = self.y - 16
        for ligne in lignes:
            self.c.drawString(MARGE + 16, yy, ligne.replace("\t", "    "))
            yy -= 11.5
        self.y -= h + 8

    def corrige(self, n, titre, cor):
        self.place(40)
        self.texte(f"Exercice {n} · {titre}", police="Sans-Bold", taille=11, couleur=OK, apres=4)
        for para in cor["texte"]:
            self.texte(para, taille=9.5)
        if cor.get("code"):
            self.code(cor["code"])
        self.y -= 6

    def fin(self):
        pied(self.c, self.page)
        self.c.save()
        return self.page


def produire(c):
    cahier = Cahier(c["fichier"], c["titre"], c["sous_titre"])
    cahier.texte(c["intro"], taille=10.5, apres=4)
    cahier.texte("Conseil : fais les exercices dans l'ordre, sans regarder les corrigés, puis compare. "
                 "Coche les critères de réussite : ils sont aussi la grille utilisée pour évaluer un projet.",
                 taille=9, couleur=MUTED, apres=10)
    cahier.titre_section("Exercices")
    for i, ex in enumerate(c["exercices"], 1):
        cahier.exercice(i, ex)
    cahier.nouvelle_page()
    cahier.titre_section("Corrigés et éléments de réponse", OK)
    for i, ex in enumerate(c["exercices"], 1):
        cahier.corrige(i, ex["titre"], ex["corrige"])
    return cahier.fin()


# --------------------------------------------------------------------------
# Contenus
# --------------------------------------------------------------------------
CAHIERS = [
{
 "id": "res-cahier-web", "fichier": "tobmaq-cahier-web-html-css.pdf", "categorie": "web", "logiciels": ["vscode"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Créer son site en HTML et CSS", "sous_titre": "Création web · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : HTML, CSS et responsive",
 "desc": "5 exercices progressifs, de la première page à une grille de produits responsive, avec les corrigés en code complet.",
 "intro": "Ce cahier accompagne la formation « Créer son premier site web : HTML et CSS ». Tu n'as besoin que de VS Code (gratuit) et d'un navigateur. "
          "À la fin, tu auras construit la page complète d'une boutique, lisible sur téléphone comme sur ordinateur.",
 "exercices": [
  {"titre": "Trouver les erreurs", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Ce code contient 5 erreurs de structure ou d'accessibilité. Repère-les et réécris le code corrigé.",
   "code": '<html>\n<head>\n  <title>Salon Belle</title>\n</head>\n<body>\n  <h1>Salon Belle</h1>\n  <h1>Nos coiffures</h1>\n  <img src="tresses.jpg">\n  <p>Tresses, nattes et tissages.\n  <a href="tel:0100000000">cliquez ici</a>\n</body>\n</html>',
   "criteres": ["Les 5 erreurs sont trouvées et expliquées.", "Le code corrigé s'ouvre sans erreur sur validator.w3.org."],
   "corrige": {"texte": ["1) Il manque <!DOCTYPE html> et lang=\"fr\" sur <html>. 2) Le <head> doit contenir <meta charset=\"UTF-8\"> et la balise viewport. "
                          "3) Deux h1 : le second doit être un h2. 4) L'image n'a pas d'attribut alt. 5) Le paragraphe n'est pas fermé, et « cliquez ici » n'explique pas où mène le lien."],
               "code": '<!DOCTYPE html>\n<html lang="fr">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Salon Belle</title>\n</head>\n<body>\n  <h1>Salon Belle</h1>\n  <h2>Nos coiffures</h2>\n  <img src="tresses.jpg" alt="Tresses africaines longues réalisées au salon">\n  <p>Tresses, nattes et tissages.</p>\n  <a href="tel:+2290100000000">Appeler le salon</a>\n</body>\n</html>'}},
  {"titre": "La page d'un commerce", "niveau": "Débutant", "duree": "45 min",
   "consigne": "Crée index.html pour un commerce de ton quartier.",
   "etapes": ["Un header avec le nom (h1) et un menu nav de 3 liens vers les sections.", "Un main avec 3 sections : Services, Horaires, Contact (chacune avec un h2).",
              "Au moins 2 images avec un alt utile.", "Un lien WhatsApp au format https://wa.me/229XXXXXXXXXX.", "Un footer avec l'année."],
   "criteres": ["Un seul h1, des h2 pour les sections.", "Les liens du menu font défiler jusqu'aux sections (href=\"#id\").", "Zéro erreur sur validator.w3.org."],
   "corrige": {"texte": ["Structure attendue : header (h1 + nav), main (3 sections avec un id chacune), footer. Les liens du menu utilisent href=\"#services\", "
                          "href=\"#horaires\", href=\"#contact\", et chaque section porte l'id correspondant. Le lien WhatsApp contient le numéro au format "
                          "international sans + ni espaces. Chaque image a un alt qui décrit ce qu'elle montre, pas « image » ou « photo »."]}},
  {"titre": "Une palette en variables CSS", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Crée style.css avec 3 couleurs déclarées en variables dans :root, et utilise-les pour le fond de l'en-tête, les titres et un bouton.",
   "criteres": ["Les couleurs sont écrites une seule fois, dans :root.", "Le bouton a un état :hover.", "Le contraste texte/fond atteint au moins 4,5:1."],
   "corrige": {"texte": ["Changer une couleur dans :root met à jour tout le site : c'est le principe d'une charte graphique."],
               "code": ":root {\n  --principale: #5b3df5;\n  --accent: #e8742c;\n  --texte: #1d1d1d;\n}\nheader { background: var(--principale); color: white; padding: 24px; }\nh2 { color: var(--principale); }\n.bouton {\n  background: var(--accent); color: white;\n  padding: 12px 20px; border-radius: 8px; text-decoration: none;\n}\n.bouton:hover { filter: brightness(0.9); }"}},
  {"titre": "Le modèle de boîte", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Une carte a width: 300px; padding: 20px; border: 2px solid; margin: 16px. Quelle largeur occupe-t-elle à l'écran, sans puis avec box-sizing: border-box ? Quelle place totale prend-elle avec ses marges ?",
   "criteres": ["Les deux calculs sont justifiés."],
   "corrige": {"texte": ["Sans border-box : 300 + 2 × 20 + 2 × 2 = 344 px de boîte visible, et 344 + 2 × 16 = 376 px avec les marges.",
                          "Avec border-box : la boîte visible fait exactement 300 px (le padding et la bordure sont inclus), et 332 px avec les marges."]}},
  {"titre": "Grille de produits responsive", "niveau": "Intermédiaire", "duree": "45 min",
   "consigne": "Ajoute une section de 6 cartes produit (image, nom, prix en FCFA, bouton). Elles doivent s'afficher sur 3 colonnes sur ordinateur et 1 colonne sur téléphone, sans défilement horizontal.",
   "criteres": ["Testé à 360, 768 et 1280 px dans le mode appareil (Ctrl+Maj+M).", "Les images ne dépassent jamais de leur carte.", "Le titre est réduit sous 600 px."],
   "corrige": {"texte": ["Avec flex: 1 1 260px, aucune media query n'est nécessaire pour les colonnes : les cartes se répartissent selon la place disponible."],
               "code": "img { max-width: 100%; height: auto; }\n.produits { display: flex; flex-wrap: wrap; gap: 16px; }\n.carte {\n  flex: 1 1 260px;\n  border: 1px solid #ddd; border-radius: 12px; padding: 16px;\n}\n@media (max-width: 600px) {\n  h1 { font-size: 1.6rem; }\n}"}}]},
{
 "id": "res-cahier-wordpress", "fichier": "tobmaq-cahier-wordpress.pdf", "categorie": "web", "logiciels": ["wordpress"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Sites vitrines avec WordPress", "sous_titre": "Création web · 4 exercices de mise en situation et leurs corrigés",
 "titre_court": "Cahier d'exercices : site vitrine WordPress",
 "desc": "4 mises en situation avec un client : budget, cahier des charges, construction du site et checklist de livraison, avec les corrigés.",
 "intro": "Ce cahier te met dans la peau d'un créateur de sites qui travaille pour de vrais clients. Les exercices suivent l'ordre d'un projet : "
          "comprendre le besoin, préparer le lancement, construire le site, puis le livrer.",
 "exercices": [
  {"titre": "Le cahier des charges", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Une pharmacie de Parakou veut un site. Rédige les 8 questions à lui poser avant de commencer, puis un cahier des charges d'une page (objectif, public, pages, contenus à fournir par le client, délai).",
   "criteres": ["Les questions portent sur le besoin, pas sur la technique.", "La liste des contenus à fournir par le client est précise."],
   "corrige": {"texte": ["Questions utiles : Que doit faire un visiteur après avoir vu le site (appeler, venir, commander) ? Qui sont vos clients ? Quelles informations "
                          "vous demande-t-on le plus souvent (horaires, garde, produits) ? Avez-vous un logo et des photos ? Qui mettra le site à jour ? "
                          "Quels sites aimez-vous ? Quel est votre budget annuel ? Pour quand en avez-vous besoin ?",
                          "Pages probables : Accueil, Services (conseils, tests, livraison), Pharmacie de garde, Contact avec carte. Contenus du client : logo, "
                          "photos de la façade et de l'équipe, horaires, numéros, textes de présentation validés."]}},
  {"titre": "Le budget annuel", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Le nom de domaine coûte 12 000 FCFA par an, l'hébergement 3 500 FCFA par mois, et ta maintenance 10 000 FCFA par mois. Calcule le budget annuel du client, puis le total de la première année avec la création du site facturée 150 000 FCFA.",
   "criteres": ["Chaque ligne du calcul est détaillée."],
   "corrige": {"texte": ["Domaine 12 000 + hébergement 3 500 × 12 = 42 000 + maintenance 10 000 × 12 = 120 000. Budget annuel : 174 000 FCFA.",
                          "Première année : 174 000 + 150 000 = 324 000 FCFA. Présente toujours séparément la création (une fois) et les frais récurrents (chaque année)."]}},
  {"titre": "Construire le site vitrine", "niveau": "Débutant", "duree": "3 h",
   "consigne": "Construis le site de la pharmacie (en local avec un outil comme LocalWP, ou sur un hébergement de test).",
   "etapes": ["Thème léger, palette de 3 couleurs maximum.", "4 pages, page d'accueil statique, menu testé sur téléphone.",
              "Bouton WhatsApp (wa.me) sur l'accueil, Contact et le pied de page.", "Images réduites à environ 1600 px, avec texte alternatif."],
   "criteres": ["Le site s'affiche correctement à 360 px de large.", "Toutes les images ont un texte alternatif.", "Le lien WhatsApp ouvre bien la conversation."],
   "corrige": {"texte": ["Accueil attendu : une photo de la pharmacie avec la phrase « Votre pharmacie à Parakou, ouverte 7 j/7 », un bouton « Écrire sur WhatsApp », "
                          "3 blocs de services en colonnes, les horaires, puis un appel à l'action final. Erreurs fréquentes : trop de couleurs, images de plusieurs Mo, "
                          "menu non testé sur téléphone, page d'accueil laissée sur « Derniers articles »."]}},
  {"titre": "La checklist de livraison", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Rédige la checklist de 10 points à vérifier avant de livrer un site WordPress à un client.",
   "criteres": ["Sécurité, sauvegardes, accès du client et formation sont couverts."],
   "corrige": {"texte": ["1) HTTPS actif partout. 2) Identifiant administrateur personnel, mot de passe fort. 3) Thèmes et extensions inutiles supprimés. "
                          "4) Mises à jour automatiques activées. 5) Sauvegarde automatique testée (une restauration a été essayée). 6) Formulaire et liens WhatsApp testés. "
                          "7) Site vérifié sur téléphone. 8) Compte Éditeur créé pour le client. 9) Tutoriel vidéo remis. 10) Domaine et hébergement au nom du client, "
                          "dates de renouvellement notées."]}}]},
{
 "id": "res-cahier-javascript", "fichier": "tobmaq-cahier-javascript.pdf", "categorie": "developpement", "logiciels": ["vscode"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Programmer avec JavaScript", "sous_titre": "Développement · 5 exercices et leurs corrigés en code",
 "titre_court": "Cahier d'exercices : JavaScript",
 "desc": "5 exercices, des variables jusqu'à un calculateur interactif, avec les corrigés en code commenté.",
 "intro": "Ce cahier accompagne la formation « Programmer avec JavaScript ». Teste chaque programme dans la console du navigateur (F12) ou dans un fichier "
          "script.js relié à une page. Un programme n'est réussi que s'il fonctionne aussi avec des valeurs inhabituelles.",
 "exercices": [
  {"titre": "Prédire le résultat", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Sans exécuter le code, écris ce qu'affiche chaque ligne. Vérifie ensuite dans la console.",
   "code": 'console.log(2 + 3 * 4);\nconsole.log((2 + 3) * 4);\nconsole.log("10" + 5);\nconsole.log(Number("10") + 5);\nconsole.log(17 % 5);\nconsole.log(5 === "5");',
   "criteres": ["Au moins 5 bonnes réponses sur 6.", "Chaque erreur est comprise après vérification."],
   "corrige": {"texte": ["14 (la multiplication passe avant l'addition) · 20 · \"105\" (texte collé) · 15 · 2 (reste de 17 ÷ 5) · false (types différents avec ===)."]}},
  {"titre": "Le ticket de caisse", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Déclare le prix unitaire (3 500 FCFA), la quantité (4) et la livraison (1 000 FCFA). Affiche le sous-total, la TVA à 18 % et le total TTC, chacun sur une ligne.",
   "criteres": ["const pour les valeurs fixes.", "Les montants sont affichés avec toLocaleString(\"fr-FR\")."],
   "corrige": {"texte": ["Sous-total 14 000 + livraison 1 000 = 15 000 ; TVA 2 700 ; total TTC 17 700 FCFA."],
               "code": 'const prix = 3500, quantite = 4, livraison = 1000, TVA = 0.18;\nconst sousTotal = prix * quantite + livraison;\nconst tva = sousTotal * TVA;\nconst total = sousTotal + tva;\nconst f = n => n.toLocaleString("fr-FR") + " FCFA";\nconsole.log("Sous-total :", f(sousTotal));\nconsole.log("TVA 18 % :", f(tva));\nconsole.log("Total TTC :", f(total));'}},
  {"titre": "Les mentions", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Écris la fonction mention(note) : « Très bien » à partir de 16, « Bien » à partir de 14, « Assez bien » à partir de 12, « Passable » à partir de 10, sinon « Ajourné ». Teste-la avec une boucle sur [9.5, 10, 12, 13.99, 14, 16, 20].",
   "criteres": ["Les cas limites 10, 12, 14 et 16 donnent la bonne mention.", "La fonction utilise return."],
   "corrige": {"texte": ["En testant du plus grand au plus petit, chaque condition n'a besoin que d'une seule comparaison."],
               "code": 'function mention(note) {\n  if (note >= 16) return "Très bien";\n  if (note >= 14) return "Bien";\n  if (note >= 12) return "Assez bien";\n  if (note >= 10) return "Passable";\n  return "Ajourné";\n}\nfor (const n of [9.5, 10, 12, 13.99, 14, 16, 20]) {\n  console.log(n, "→", mention(n));\n}'}},
  {"titre": "Les statistiques de ventes", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Avec le tableau ventes = [12000, 8500, 23000, 4000, 15500], calcule et affiche le total, la moyenne, la meilleure vente et le nombre de ventes supérieures à 10 000 FCFA, en utilisant une seule boucle.",
   "criteres": ["Une seule boucle for…of.", "Résultats : 63 000 ; 12 600 ; 23 000 ; 3."],
   "corrige": {"texte": ["On initialise les compteurs avant la boucle, on les met à jour à chaque vente, puis on calcule la moyenne après la boucle."],
               "code": 'const ventes = [12000, 8500, 23000, 4000, 15500];\nlet total = 0, meilleure = 0, grosses = 0;\nfor (const v of ventes) {\n  total += v;\n  if (v > meilleure) meilleure = v;\n  if (v > 10000) grosses++;\n}\nconsole.log(total, total / ventes.length, meilleure, grosses);'}},
  {"titre": "Le compteur de clics", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Crée une page avec un bouton « J'aime », un bouton « Remettre à zéro » et un paragraphe qui affiche le nombre de clics. Le texte doit être au singulier ou au pluriel (« 1 j'aime », « 2 j'aime »… et « Aucun j'aime » à 0).",
   "criteres": ["querySelector, addEventListener et textContent sont utilisés.", "Le cas 0 affiche « Aucun j'aime »."],
   "corrige": {"texte": ["Une seule fonction afficher() met à jour le texte : les deux boutons l'appellent, le code n'est pas répété."],
               "code": '<button id="jaime">J\'aime</button> <button id="zero">Remettre à zéro</button>\n<p id="compteur"></p>\n\nlet clics = 0;\nconst sortie = document.querySelector("#compteur");\nfunction afficher() {\n  sortie.textContent = clics === 0 ? "Aucun j\'aime" : `${clics} j\'aime`;\n}\ndocument.querySelector("#jaime").addEventListener("click", () => { clics++; afficher(); });\ndocument.querySelector("#zero").addEventListener("click", () => { clics = 0; afficher(); });\nafficher();'}}]},
{
 "id": "res-cahier-python", "fichier": "tobmaq-cahier-python.pdf", "categorie": "developpement", "logiciels": ["python"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Python pour débuter", "sous_titre": "Développement · 5 exercices et leurs corrigés en code",
 "titre_court": "Cahier d'exercices : Python",
 "desc": "5 exercices concrets (convertisseur FCFA, tontine, stock, devinette) avec les corrigés en code Python commenté.",
 "intro": "Ce cahier accompagne la formation « Python pour débuter ». Chaque exercice est un petit outil utile au quotidien. Exécute tes programmes avec "
          "python fichier.py et teste-les avec des saisies inhabituelles : zéro, nombre négatif, texte à la place d'un nombre.",
 "exercices": [
  {"titre": "Convertisseur FCFA ↔ euros", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Demande un montant en FCFA et affiche l'équivalent en euros, arrondi à 2 décimales (1 € = 655,957 FCFA, parité fixe).",
   "criteres": ["La saisie est convertie avec float().", "10 000 FCFA donne 15,24 €."],
   "corrige": {"texte": ["round(valeur, 2) arrondit à 2 décimales ; :.2f dans une f-string force l'affichage de 2 décimales."],
               "code": 'TAUX = 655.957\nmontant = float(input("Montant en FCFA : "))\neuros = montant / TAUX\nprint(f"{montant:.0f} FCFA = {euros:.2f} €")'}},
  {"titre": "La tontine", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Une tontine réunit N membres qui cotisent chacun C FCFA par semaine ; chaque semaine, un membre reçoit toute la cagnotte. Demande N et C, puis affiche la cagnotte hebdomadaire et le nombre de semaines du cycle complet.",
   "criteres": ["Les saisies sont converties avec int().", "Avec 12 membres à 5 000 FCFA : 60 000 FCFA, cycle de 12 semaines."],
   "corrige": {"texte": ["Cagnotte = N × C, et le cycle dure N semaines puisque chaque membre reçoit une fois."],
               "code": 'membres = int(input("Nombre de membres : "))\ncotisation = int(input("Cotisation par semaine (FCFA) : "))\nprint(f"Cagnotte hebdomadaire : {membres * cotisation} FCFA")\nprint(f"Cycle complet : {membres} semaines")'}},
  {"titre": "La table de multiplication", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Demande un nombre et affiche sa table de multiplication de 1 à 10 avec une boucle for.",
   "criteres": ["Une boucle for avec range(1, 11)."],
   "corrige": {"texte": ["range(1, 11) va de 1 à 10 : la borne de fin n'est jamais incluse."],
               "code": 'n = int(input("Nombre : "))\nfor i in range(1, 11):\n    print(f"{n} x {i} = {n * i}")'}},
  {"titre": "Le stock et les erreurs de saisie", "niveau": "Intermédiaire", "duree": "35 min",
   "consigne": "Reprends le gestionnaire de stock de la leçon et ajoute un menu en boucle (1 voir, 2 vendre, 3 quitter). Si l'utilisateur tape un texte à la place d'une quantité, le programme affiche un message au lieu de s'arrêter.",
   "criteres": ["while True et break pour le menu.", "try / except ValueError autour de int().", "Un article inconnu affiche un message clair."],
   "corrige": {"texte": ["try / except permet d'attraper l'erreur ValueError et de continuer le programme."],
               "code": 'stock = {"pagne": 12, "sac": 5}\nwhile True:\n    choix = input("1 voir, 2 vendre, 3 quitter : ")\n    if choix == "1":\n        for article, q in stock.items():\n            print(f"- {article} : {q}")\n    elif choix == "2":\n        article = input("Article : ")\n        if article not in stock:\n            print("Article inconnu.")\n            continue\n        try:\n            q = int(input("Quantité : "))\n        except ValueError:\n            print("Tape un nombre entier.")\n            continue\n        if 0 < q <= stock[article]:\n            stock[article] -= q\n            print("Vente enregistrée.")\n        else:\n            print("Quantité impossible.")\n    elif choix == "3":\n        break'}},
  {"titre": "Le nombre mystère", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "L'ordinateur choisit un nombre entre 1 et 100 (module random). Le joueur propose des nombres ; le programme répond « plus grand » ou « plus petit » et compte les essais jusqu'à la victoire.",
   "criteres": ["random.randint(1, 100) est utilisé.", "Le nombre d'essais s'affiche à la fin."],
   "corrige": {"texte": ["Stratégie gagnante à expliquer au joueur : proposer toujours le milieu de l'intervalle restant (50, puis 25 ou 75…) trouve le nombre en 7 essais maximum."],
               "code": 'import random\nmystere = random.randint(1, 100)\nessais = 0\nwhile True:\n    proposition = int(input("Ton nombre : "))\n    essais += 1\n    if proposition < mystere:\n        print("Plus grand !")\n    elif proposition > mystere:\n        print("Plus petit !")\n    else:\n        print(f"Bravo, trouvé en {essais} essais !")\n        break'}}]},
{
 "id": "res-cahier-game-design", "fichier": "tobmaq-cahier-game-design.pdf", "categorie": "jeux-video", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Game design", "sous_titre": "Jeux vidéo · 4 exercices de conception et leurs éléments de réponse",
 "titre_court": "Cahier d'exercices : game design",
 "desc": "4 exercices pour concevoir un jeu sur papier : analyse, boucle de jeu, document de conception et niveaux, avec les éléments de réponse.",
 "intro": "Ce cahier accompagne la formation « Game design : concevoir un jeu ». Pas besoin d'ordinateur : un crayon, du papier quadrillé et des amis "
          "pour tester suffisent. Les grands jeux commencent tous sur une feuille.",
 "exercices": [
  {"titre": "Analyser un jeu connu", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Choisis un jeu que tu connais bien (sur téléphone ou console). Décris en 5 lignes : sa boucle de jeu, son objectif, sa condition de défaite, ses commandes et la façon dont la difficulté augmente.",
   "criteres": ["La boucle est décrite comme un cycle d'actions.", "Les retours (sons, animations, points) sont mentionnés."],
   "corrige": {"texte": ["Exemple avec un jeu de course sans fin : boucle « courir → éviter un obstacle → ramasser des pièces → la vitesse augmente ». Objectif : aller le plus loin "
                          "possible. Défaite : toucher un obstacle. Commandes : glisser vers la gauche, la droite, le haut et le bas. Difficulté : la vitesse augmente avec le temps, "
                          "les obstacles se rapprochent. Retours : son des pièces, compteur, effet visuel à chaque bonus."]}},
  {"titre": "La boucle de jeu", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Invente un jeu inspiré de ta ville. Écris l'idée en une phrase (« un jeu où… doit… pour… mais… »), puis dessine sa boucle de jeu en 4 étapes sous forme de cercle.",
   "criteres": ["La phrase contient un joueur, une action, un objectif et un obstacle.", "Chaque étape de la boucle mène à la suivante."],
   "corrige": {"texte": ["Exemple : « Un jeu où une vendeuse du marché doit servir ses clients avant qu'ils ne partent, mais les commandes arrivent de plus en plus vite. » "
                          "Boucle : un client arrive (défi) → la joueuse prépare la commande (action) → son de caisse et pièces (retour) → argent pour améliorer l'étal (récompense)."]}},
  {"titre": "Le document de conception", "niveau": "Débutant", "duree": "40 min",
   "consigne": "Rédige le document d'une page de ton jeu : titre, phrase d'idée, public, plateforme, boucle, commandes, victoire et défaite, 3 éléments de progression, style visuel.",
   "criteres": ["Tout tient sur une page.", "Les commandes sont limitées à 1 ou 2 gestes sur téléphone."],
   "corrige": {"texte": ["Grille d'évaluation : l'idée se comprend en une lecture (2 pts) ; la boucle est claire et répétable (3 pts) ; les commandes sont simples (2 pts) ; "
                          "la progression est variée (nouveaux obstacles, vitesse, récompenses) (2 pts) ; le style visuel est illustré par des références (1 pt)."]}},
  {"titre": "Trois niveaux sur papier", "niveau": "Intermédiaire", "duree": "45 min",
   "consigne": "Dessine sur papier quadrillé les 3 premiers niveaux de ton jeu en appliquant la méthode « présenter, pratiquer, combiner, tester », puis trace la courbe de difficulté.",
   "criteres": ["Une seule nouveauté par niveau.", "Un point de reprise après chaque passage difficile.", "La courbe alterne pics et pauses."],
   "corrige": {"texte": ["Niveau 1 : la mécanique de base, sans danger, puis avec un obstacle très visible. Niveau 2 : une nouveauté (par exemple un obstacle mobile), "
                          "présentée seule avant d'être combinée avec l'obstacle du niveau 1. Niveau 3 : test de maîtrise qui combine tout, avec une pause et une récompense "
                          "au milieu. La courbe ressemble à des marches d'escalier avec de petits paliers de repos."]}}]},
{
 "id": "res-cahier-godot", "fichier": "tobmaq-cahier-godot.pdf", "categorie": "jeux-video", "logiciels": ["godot"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Créer un jeu 2D avec Godot", "sous_titre": "Jeux vidéo · 4 exercices et leurs corrigés en GDScript",
 "titre_court": "Cahier d'exercices : Godot et GDScript",
 "desc": "4 exercices en GDScript (vies, course, minuteur, ennemi) pour finir un premier jeu jouable, avec les corrigés.",
 "intro": "Ce cahier accompagne la formation « Créer un jeu 2D avec Godot » (Godot 4). Chaque exercice ajoute une fonctionnalité à ton jeu. "
          "Dans les codes, l'indentation se fait avec la touche Tab, comme dans l'éditeur de Godot.",
 "exercices": [
  {"titre": "Les vies du joueur", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Dans un script, crée une variable vies := 3 et une fonction perdre_une_vie() qui retire une vie, affiche le nombre restant et affiche « Partie terminée » à 0. Appelle-la 3 fois dans _ready().",
   "criteres": ["Le message final s'affiche exactement une fois.", "Les vies ne descendent jamais sous 0."],
   "corrige": {"texte": ["max(vies - 1, 0) empêche d'avoir des vies négatives même si la fonction est appelée trop souvent."],
               "code": 'extends Node2D\n\nvar vies := 3\n\nfunc _ready():\n\tfor i in 3:\n\t\tperdre_une_vie()\n\nfunc perdre_une_vie():\n\tvies = max(vies - 1, 0)\n\tprint("Vies : ", vies)\n\tif vies == 0:\n\t\tprint("Partie terminée")'}},
  {"titre": "Courir avec Maj", "niveau": "Intermédiaire", "duree": "20 min",
   "consigne": "Ajoute une action « courir » dans Projet > Paramètres du projet > Contrôles, associée à la touche Maj. Quand elle est enfoncée, le joueur va deux fois plus vite.",
   "criteres": ["L'action est créée dans les Contrôles (InputMap), pas testée par code de touche.", "La vitesse normale est réglable avec @export."],
   "corrige": {"texte": ["Input.is_action_pressed() renvoie true tant que la touche est enfoncée."],
               "code": 'extends CharacterBody2D\n\n@export var vitesse := 200.0\n\nfunc _physics_process(_delta):\n\tvar direction := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")\n\tvar v := vitesse * 2 if Input.is_action_pressed("courir") else vitesse\n\tvelocity = direction * v\n\tmove_and_slide()'}},
  {"titre": "Le minuteur de 60 secondes", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Ajoute un nœud Timer (Wait Time 60, One Shot, Autostart) et un Label. Le Label affiche le temps restant en secondes ; à la fin, il affiche « Temps écoulé ! » et le joueur ne peut plus bouger.",
   "criteres": ["Le temps restant est lu avec time_left.", "Le signal timeout est connecté."],
   "corrige": {"texte": ["time_left donne le temps restant ; ceili() l'arrondit à la seconde supérieure, en nombre entier. set_physics_process(false) arrête la fonction de déplacement du joueur."],
               "code": 'extends Node2D\n\n@onready var minuteur: Timer = $Timer\n@onready var affichage: Label = $Label\n@onready var joueur = $Joueur\n\nfunc _process(_delta):\n\tif not minuteur.is_stopped():\n\t\taffichage.text = str(ceili(minuteur.time_left)) + " s"\n\nfunc _on_timer_timeout():\n\taffichage.text = "Temps écoulé !"\n\tjoueur.set_physics_process(false)'}},
  {"titre": "Un ennemi qui patrouille", "niveau": "Intermédiaire", "duree": "35 min",
   "consigne": "Crée un ennemi (Area2D) qui fait des allers-retours horizontaux sur 200 pixels. S'il touche le joueur, celui-ci perd une vie.",
   "criteres": ["Le mouvement utilise delta pour être régulier sur tous les ordinateurs.", "Le contact passe par le signal body_entered."],
   "corrige": {"texte": ["On mémorise la position de départ, on avance dans une direction, et on inverse la direction quand l'écart dépasse 200 pixels. "
                          "La fonction perdre_une_vie() doit exister dans le script du joueur."],
               "code": 'extends Area2D\n\n@export var vitesse := 120.0\nvar depart: float\nvar sens := 1\n\nfunc _ready():\n\tdepart = position.x\n\nfunc _process(delta):\n\tposition.x += sens * vitesse * delta\n\tif abs(position.x - depart) > 200:\n\t\tsens = -sens\n\nfunc _on_body_entered(body):\n\tif body.has_method("perdre_une_vie"):\n\t\tbody.perdre_une_vie()'}}]},
{
 "id": "res-cahier-graphisme", "fichier": "tobmaq-cahier-graphisme.pdf", "categorie": "graphisme", "logiciels": ["photoshop", "illustrator", "canva"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Graphisme", "sous_titre": "Graphisme · 5 exercices pratiques et leurs éléments de réponse",
 "titre_court": "Cahier d'exercices : graphisme",
 "desc": "5 exercices sur les couleurs, la typographie, l'affiche, le logo et les formats, avec les éléments de réponse et les grilles d'évaluation.",
 "intro": "Ce cahier accompagne les formations de graphisme. Les exercices se font avec le logiciel de ton choix (Photoshop, Illustrator, Canva, GIMP, Inkscape). "
          "Les corrigés donnent les éléments attendus et une grille d'évaluation : en création, il n'existe pas une seule bonne réponse.",
 "exercices": [
  {"titre": "Trois palettes", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Pour une marque de jus de bissap, crée trois palettes de 4 couleurs : complémentaire, analogue, triadique. Indique pour chacune la couleur dominante, celle des textes et le code HEX de chaque couleur.",
   "criteres": ["Les relations sur le cercle chromatique sont respectées.", "Le texte atteint un contraste de 4,5:1 sur son fond."],
   "corrige": {"texte": ["Le bissap évoque un rouge pourpre (environ #8E1B3A). Complémentaire : un vert profond en accent. Analogue : pourpre, rose framboise, violet. "
                          "Triadique : pourpre, vert-jaune et bleu, avec le pourpre dominant à 60 %. Les textes sont en blanc cassé sur fond foncé, ou en brun très foncé sur fond clair."]}},
  {"titre": "Hiérarchie typographique", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Mets en page ces informations sur un flyer A5 avec 3 niveaux de hiérarchie et 2 polices maximum : « Soirée Afrobeat · Samedi 12 avril · 21 h · Espace culturel de Cotonou · Entrée 3 000 FCFA · Réservations : 01 00 00 00 00 ».",
   "criteres": ["Le nom de la soirée se lit en premier, même de loin.", "Date, heure et lieu forment le niveau 2.", "2 polices maximum."],
   "corrige": {"texte": ["Niveau 1 : « Soirée Afrobeat », très grand et gras. Niveau 2 : « Samedi 12 avril · 21 h » puis le lieu, en taille moyenne avec la couleur d'accent. "
                          "Niveau 3 : prix et réservations en petit, en bas. Un seul alignement principal et des espaces réguliers entre les groupes d'informations."]}},
  {"titre": "Affiche d'événement", "niveau": "Intermédiaire", "duree": "1 h 30",
   "consigne": "Crée l'affiche A3 de la soirée de l'exercice 2, prête pour l'imprimeur.",
   "criteres": ["Format A3 avec 3 mm de fond perdu (303 × 426 mm).", "Textes à plus de 5 mm du bord de coupe.", "Images à 300 ppp à la taille d'impression.", "Export PDF en CMJN."],
   "corrige": {"texte": ["Grille d'évaluation sur 10 : lisibilité à 3 mètres (3 pts), hiérarchie claire (2 pts), cohérence des couleurs (2 pts), préparation technique : fond perdu, "
                          "zone de sécurité, résolution, CMJN (3 pts). Erreur la plus fréquente : texte important trop près du bord, coupé à l'impression."]}},
  {"titre": "Un logo en trois pistes", "niveau": "Avancé", "duree": "2 h",
   "consigne": "Pour un atelier de couture « Fil d'Or », rédige un brief d'une page, dessine 20 croquis, puis présente 3 pistes vectorielles différentes avec une phrase d'explication chacune.",
   "criteres": ["Les 3 pistes sont vraiment différentes (typographique, symbole + nom, emblème).", "Chaque piste est lisible à 1 cm et en noir seul."],
   "corrige": {"texte": ["Pistes possibles : 1) le nom en lettres fines et élégantes, avec un fil doré qui relie le F et le O ; 2) une aiguille stylisée dont le chas forme un O ; "
                          "3) un emblème rond avec le nom autour d'un motif de pagne. Chaque piste est testée en 16 px, en noir, et sur fond foncé."]}},
  {"titre": "Les bons formats", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Indique le format de fichier et les dimensions adaptés à : a) une publication carrée Instagram, b) une story WhatsApp, c) un logo pour un imprimeur, d) une miniature YouTube, e) une photo sur un site web.",
   "criteres": ["5 bonnes réponses sur 5."],
   "corrige": {"texte": ["a) JPG ou PNG, 1080 × 1080 px. b) JPG ou PNG, 1080 × 1920 px. c) PDF vectoriel, SVG ou AI. d) JPG, 1280 × 720 px. "
                          "e) WebP ou JPG compressé, environ 1600 px de large au maximum."]}}]},
{
 "id": "res-cahier-maquettisme", "fichier": "tobmaq-cahier-maquettisme.pdf", "categorie": "maquettisme", "logiciels": ["indesign", "affinity"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Maquettisme", "sous_titre": "Maquettisme · 4 exercices de mise en page et leurs corrigés",
 "titre_court": "Cahier d'exercices : maquettisme et mise en page",
 "desc": "4 exercices de mise en page (grille, coquilles typographiques, chemin de fer, calculs d'impression) avec les corrigés.",
 "intro": "Ce cahier accompagne les formations de maquettisme. Les exercices se font avec InDesign, Affinity Publisher ou Scribus (gratuit). "
          "Un bon maquettiste est rigoureux : vérifie chaque mesure, chaque espace et chaque marge.",
 "exercices": [
  {"titre": "La grille d'un magazine", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Crée un document A4 avec des marges de 15 mm (20 mm à l'intérieur), une grille de 12 colonnes et une gouttière de 4 mm. Compose une page d'article sur 3 colonnes avec un titre sur toute la largeur et une photo sur 8 colonnes.",
   "criteres": ["Les marges intérieures sont plus grandes que les extérieures.", "Tous les blocs s'alignent sur la grille."],
   "corrige": {"texte": ["Largeur utile : 210 − 20 − 15 = 175 mm. Avec 11 gouttières de 4 mm, chaque colonne mesure (175 − 44) ÷ 12 ≈ 10,9 mm. "
                          "Un bloc de 4 colonnes mesure 4 × 10,9 + 3 × 4 ≈ 55,7 mm : c'est la largeur d'une colonne de texte dans la mise en page à 3 colonnes."]}},
  {"titre": "Chasse aux coquilles", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Corrige ce texte selon les règles typographiques françaises : « Rendez-vous le 1ère fois a 18H30 , au 2ème étage. Prix : 25.000 FCFA ! Il a dit \"bienvenue\"... »",
   "criteres": ["Au moins 7 corrections sur 8."],
   "corrige": {"texte": ["« Rendez-vous la 1re fois à 18 h 30, au 2e étage. Prix : 25 000 FCFA ! Il a dit « bienvenue »… » "
                          "Corrections : la 1re (et non le 1ère), à avec accent, 18 h 30, pas d'espace avant la virgule, 2e, espace pour les milliers, "
                          "guillemets français avec espaces insécables, points de suspension en un seul caractère."]}},
  {"titre": "Le chemin de fer", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Prépare le chemin de fer (plan de toutes les pages) d'un magazine scolaire de 16 pages : couverture, sommaire, édito, 4 rubriques, jeux, publicité, 4e de couverture.",
   "criteres": ["Le nombre de pages est un multiple de 4.", "Les doubles pages sont pensées ensemble.", "La publicité est placée sur une page de droite."],
   "corrige": {"texte": ["Exemple : p.1 couverture ; p.2 publicité (2e de couverture) ; p.3 sommaire ; p.4-5 édito et actualités ; p.6-7 et 8-9 deux rubriques en double page ; "
                          "p.10-11 grand reportage ; p.12-13 culture ; p.14 jeux ; p.15 publicité (page de droite, plus visible) ; p.16 4e de couverture. "
                          "Un livret agrafé se compose de feuilles pliées en 4 pages : 16 pages = 4 feuilles."]}},
  {"titre": "Calculs d'impression", "niveau": "Intermédiaire", "duree": "15 min",
   "consigne": "a) Taille du document pour un A5 (148 × 210 mm) avec 3 mm de fond perdu ? b) Combien de pixels pour une photo pleine page A5 à 300 ppp ? c) Une photo de 1200 px de large imprimée sur 15 cm : quelle résolution réelle ? Est-ce suffisant ?",
   "criteres": ["Chaque calcul est détaillé."],
   "corrige": {"texte": ["a) 154 × 216 mm. b) 148 ÷ 25,4 × 300 ≈ 1748 px et 210 ÷ 25,4 × 300 ≈ 2480 px. "
                          "c) 15 cm = 5,9 pouces ; 1200 ÷ 5,9 ≈ 203 ppp : insuffisant pour une impression de qualité (viser 300 ppp), il faut une image plus grande ou la réduire à 10 cm."]}}]},
{
 "id": "res-cahier-montage", "fichier": "tobmaq-cahier-montage-video.pdf", "categorie": "video", "logiciels": ["premiere", "resolve", "capcut"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Montage vidéo", "sous_titre": "Montage vidéo · 5 exercices pratiques et leurs corrigés",
 "titre_court": "Cahier d'exercices : montage vidéo",
 "desc": "5 exercices de montage (timecode, ordre des plans, Reel, publicité, export) avec les corrigés et les grilles d'évaluation.",
 "intro": "Ce cahier accompagne les formations de montage vidéo. Les exercices pratiques se font avec Premiere Pro, DaVinci Resolve (gratuit) ou CapCut (gratuit). "
          "Filme tes propres images au téléphone : c'est le meilleur entraînement.",
 "exercices": [
  {"titre": "Calculs de timecode", "niveau": "Débutant", "duree": "15 min",
   "consigne": "À 25 images par seconde : a) Combien d'images dans 4 s et 10 images ? b) Durée d'un plan de 00:00:12:20 à 00:00:15:05 ? c) Une publicité de 30 s doit contenir 12 plans de même durée : combien d'images par plan ?",
   "criteres": ["Les calculs sont détaillés."],
   "corrige": {"texte": ["a) 4 × 25 + 10 = 110 images. b) 15:05 − 12:20 : 15 × 25 + 5 = 380 et 12 × 25 + 20 = 320, soit 60 images = 2 s et 10 images (00:00:02:10). "
                          "c) 30 × 25 = 750 images ÷ 12 = 62,5 : impossible en images entières ; on alterne des plans de 62 et 63 images, ou on choisit 10 plans de 75 images."]}},
  {"titre": "Remettre les plans dans l'ordre", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Classe ces plans d'un reportage sur un atelier de poterie : A) gros plan des mains dans l'argile ; B) plan large du village ; C) interview de la potière ; D) plan moyen de l'atelier ; E) les poteries finies au soleil.",
   "criteres": ["L'ordre va du général au particulier, puis conclut."],
   "corrige": {"texte": ["B → D → A → C → E. On situe le lieu (plan large), on entre dans l'atelier (plan moyen), on montre le geste (gros plan), on écoute la personne, "
                          "puis on conclut sur le résultat. D'autres ordres sont défendables si l'intention est expliquée (par exemple commencer par le gros plan pour intriguer)."]}},
  {"titre": "Un Reel de 20 secondes", "niveau": "Débutant", "duree": "1 h",
   "consigne": "Monte un Reel vertical de 20 secondes qui présente un produit local, avec des sous-titres.",
   "criteres": ["1080 × 1920, MP4 (H.264).", "Accroche dans les 2 premières secondes.", "Sous-titres relus, hors de la zone des boutons.", "Plans de 1 à 3 secondes."],
   "corrige": {"texte": ["Grille sur 10 : accroche (2 pts), rythme et coupes sur l'action (2 pts), sous-titres lisibles et placés dans la zone sûre (2 pts), son équilibré (2 pts), "
                          "réglages d'export corrects (2 pts). Vérifie toujours le résultat final sur un téléphone, en plein écran, sans le son."]}},
  {"titre": "Le script d'une publicité", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Écris le script en 5 temps d'une publicité de 30 secondes pour un service de livraison à moto à Cotonou : accroche, problème, solution, preuve, appel à l'action, avec la durée de chaque partie.",
   "criteres": ["Les 5 temps sont présents et minutés.", "L'appel à l'action dit exactement quoi faire."],
   "corrige": {"texte": ["0-2 s : un colis qui file dans la circulation en accéléré. 2-7 s : « Ton client attend et tu ne peux pas quitter ta boutique ? ». "
                          "7-18 s : prise en charge, trajet, livraison au client souriant. 18-25 s : « Livré en moins d'une heure, plus de 500 livraisons ce mois-ci ». "
                          "25-30 s : logo, « Commande ta livraison sur WhatsApp au 01 00 00 00 00 », affiché au moins 3 secondes."]}},
  {"titre": "Les bons réglages d'export", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Indique la résolution et le format d'export pour : a) une vidéo YouTube Full HD, b) un TikTok, c) un statut WhatsApp, d) une vidéo à projeter lors d'un mariage, e) un fichier à envoyer à l'étalonneur.",
   "criteres": ["5 bonnes réponses sur 5."],
   "corrige": {"texte": ["a) 1920 × 1080, MP4 H.264. b) 1080 × 1920, MP4 H.264. c) 1080 × 1920 (ou 720 × 1280 pour un fichier plus léger), MP4 H.264, courte durée. "
                          "d) 1920 × 1080, MP4 H.264 à débit élevé, testé sur le matériel de projection. e) Un format intermédiaire de haute qualité (ProRes ou DNxHR), "
                          "sans compression destructrice."]}}]},
]


# Lot A : cahiers d'exercices Infographie, Dessin et Illustration.
CAHIERS_A = [
{
 "id": "res-cahier-infographie", "fichier": "tobmaq-cahier-infographie.pdf", "categorie": "graphisme", "logiciels": ["photoshop", "illustrator", "indesign"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Infographie professionnelle", "sous_titre": "Graphisme · 5 mises en situation et leurs corrigés",
 "titre_court": "Cahier d'exercices : commande et déclinaisons",
 "desc": "5 mises en situation, du brief client à la déclinaison d'une campagne sur six supports, avec les calculs et les corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation Infographiste. Il te met face à de vraies commandes : comprendre un client, chiffrer un travail, préparer des fichiers "
          "aux bons formats et décliner une campagne. Fais les calculs à la main avant de vérifier dans Photoshop, Illustrator ou InDesign.",
 "exercices": [
  {"titre": "Le brief du client", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Une boutique de pagnes du marché Dantokpa t'écrit sur WhatsApp : « Je veux une affiche pour mes soldes, c'est urgent. » Rédige les 8 questions à poser avant de commencer, puis le résumé du brief que tu lui renverras pour confirmation.",
   "criteres": ["Les questions couvrent le support, le format, le délai, le public, le message, les éléments fournis et le budget.", "Le résumé tient en quelques lignes et demande une confirmation écrite."],
   "corrige": {"texte": ["Questions attendues : 1) Sur quels supports l'affiche sera-t-elle utilisée (impression, Facebook, WhatsApp) ? 2) À quel format et en combien d'exemplaires ? "
                          "3) Pour quelle date exacte en as-tu besoin ? 4) Qui sont tes clients ? 5) Quel est le message principal (pourcentage de réduction, dates des soldes) ? "
                          "6) As-tu un logo, des photos de tes pagnes, tes couleurs ? 7) Quelles informations pratiques afficher (adresse dans le marché, numéro, horaires) ? 8) Quel est ton budget ?",
                          "Résumé type : « Affiche A3 pour les soldes du 1er au 15 du mois, -30 % sur le wax, public : femmes de 25 à 50 ans, logo et 5 photos fournis par toi, "
                          "livraison du fichier le jeudi. Merci de me confirmer par écrit pour que je lance le travail. »"]}},
  {"titre": "Le devis et l'acompte", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Tu factures l'affiche maître 25 000 FCFA et chaque déclinaison 7 500 FCFA. Le client veut l'affiche et 4 déclinaisons, avec 3 aller-retours inclus et 5 000 FCFA par correction supplémentaire. Tu demandes 40 % d'acompte. Calcule le total, l'acompte et le solde. Le client demande finalement 2 corrections en plus : quel est le nouveau solde ?",
   "criteres": ["Chaque ligne du calcul est détaillée.", "Le devis précise le nombre d'aller-retours inclus."],
   "corrige": {"texte": ["Déclinaisons : 4 × 7 500 = 30 000 FCFA. Total : 25 000 + 30 000 = 55 000 FCFA.",
                          "Acompte : 55 000 × 0,40 = 22 000 FCFA. Solde : 55 000 - 22 000 = 33 000 FCFA.",
                          "Corrections supplémentaires : 2 × 5 000 = 10 000 FCFA. Nouveau solde : 33 000 + 10 000 = 43 000 FCFA, soit un total payé de 65 000 FCFA."]}},
  {"titre": "Les formats et les résolutions", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Calcule les dimensions en pixels de ces documents : un flyer A5 (148 × 210 mm) avec 3 mm de fond perdu à 300 ppp ; un kakémono 85 × 200 cm à 100 ppp puis à 150 ppp ; une bâche de 400 × 100 cm à 100 ppp. Rappel : 1 pouce = 2,54 cm = 25,4 mm.",
   "criteres": ["Le fond perdu est ajouté des deux côtés.", "Les conversions en pouces sont justifiées.", "Les résultats sont arrondis au pixel."],
   "corrige": {"texte": ["Flyer : 148 + 2 × 3 = 154 mm et 210 + 2 × 3 = 216 mm. 154 ÷ 25,4 × 300 ≈ 1 819 px ; 216 ÷ 25,4 × 300 ≈ 2 551 px. Document : 1 819 × 2 551 px.",
                          "Kakémono à 100 ppp : 85 ÷ 2,54 × 100 ≈ 3 346 px et 200 ÷ 2,54 × 100 ≈ 7 874 px. À 150 ppp : environ 5 020 × 11 811 px.",
                          "Bâche à 100 ppp : 400 ÷ 2,54 × 100 ≈ 15 748 px et 100 ÷ 2,54 × 100 ≈ 3 937 px. Un fichier aussi grand est lourd : beaucoup d'infographistes travaillent "
                          "à l'échelle 1/10 (40 × 10 cm à 1 000 ppp), ce qui donne exactement le même nombre de pixels. Demande toujours à l'imprimeur l'échelle et la résolution qu'il accepte."]}},
  {"titre": "La photo est-elle assez grande ?", "niveau": "Intermédiaire", "duree": "15 min",
   "consigne": "Le client envoie une photo de 3 000 × 2 000 px. Peut-on l'utiliser en pleine largeur sur une affiche A4 (21 cm de large) à 300 ppp ? Et en pleine largeur sur un kakémono de 85 cm ? Calcule la résolution obtenue dans chaque cas et conclus.",
   "criteres": ["La résolution effective est calculée en divisant les pixels par les pouces.", "La conclusion propose une solution concrète."],
   "corrige": {"texte": ["A4 : 21 ÷ 2,54 ≈ 8,27 pouces. 3 000 ÷ 8,27 ≈ 363 ppp : c'est au-dessus de 300 ppp, la photo convient.",
                          "Kakémono : 85 ÷ 2,54 ≈ 33,46 pouces. 3 000 ÷ 33,46 ≈ 90 ppp : c'est un peu sous les 100 ppp conseillés. Solutions : demander l'original de la photo "
                          "en plus grande taille, ou ne pas l'utiliser en pleine largeur (par exemple sur les deux tiers), ou accepter un léger flou après un test d'impression. "
                          "Agrandir l'image dans Photoshop n'ajoute pas de vrais détails."]}},
  {"titre": "Décliner une campagne", "niveau": "Intermédiaire", "duree": "3 h",
   "consigne": "Crée l'affiche maître A3 d'un concert à Cotonou, puis décline-la en 5 supports : flyer A5, kakémono 85 × 200 cm, publication 1080 × 1080 px, story 1080 × 1920 px et bannière web 1200 × 628 px.",
   "etapes": ["Affiche maître : titre, artiste, date, lieu, prix en FCFA, logo de l'organisateur.", "Un fichier ou un plan de travail par support, au format exact.",
              "Imprimés en CMJN avec fond perdu 3 mm pour le flyer ; écrans en RVB.", "Exports nommés : concert_support_dimensions.extension."],
   "criteres": ["Formats et modes colorimétriques exacts.", "Aucune image ni aucun texte déformé.", "Le texte important de la story est dans la zone sûre.", "Les 6 supports semblent appartenir à la même campagne."],
   "corrige": {"texte": ["Grille d'évaluation sur 10 : formats et résolutions exacts (2 points) ; modes CMJN et RVB corrects (1 point) ; fond perdu et marges de sécurité respectés (1 point) ; "
                          "lisibilité adaptée à chaque distance (2 points) ; cohérence des couleurs, polices et logo (2 points) ; zones sûres de la story et du pied de kakémono respectées (1 point) ; "
                          "fichiers nommés et organisés (1 point).",
                          "Erreurs fréquentes : affiche simplement étirée en bannière, trop de texte sur le kakémono, date masquée en haut de la story, flyer exporté en RVB."]}}]},
{
 "id": "res-cahier-dessin", "fichier": "tobmaq-cahier-dessin.pdf", "categorie": "dessin", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Dessin : formes, perspective, ombres", "sous_titre": "Dessin · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : bases du dessin",
 "desc": "5 exercices progressifs, de l'échelle de valeurs à la nature morte complète, avec critères de réussite et grilles d'évaluation.",
 "intro": "Ce cahier accompagne la formation Dessinateur. Il te faut seulement du papier, des crayons HB, 2B, 4B et 6B, une gomme, une gomme mie de pain et une règle. "
          "Date chaque dessin et garde-les tous : comparer tes premières pages aux dernières est la meilleure preuve de tes progrès.",
 "exercices": [
  {"titre": "L'échelle de valeurs", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Trace une bande de 7 cases de 2 × 2 cm. Laisse la première blanche, remplis la septième le plus foncé possible, puis crée 5 gris réguliers entre les deux. Recommence une deuxième bande uniquement en hachures.",
   "criteres": ["Les écarts entre deux cases voisines semblent égaux.", "La dernière case est vraiment noire.", "Les hachures sont régulières et sans traits qui dépassent."],
   "corrige": {"texte": ["Crayons conseillés : case 2 au HB très léger, cases 3 et 4 au 2B, case 5 au 4B, cases 6 et 7 au 6B en plusieurs couches croisées.",
                          "Vérification : prends une photo en noir et blanc et plisse les yeux. Si deux cases se confondent, reprends la plus claire des deux. "
                          "En hachures, le gris se fonce en serrant les traits puis en ajoutant une deuxième, puis une troisième direction."]}},
  {"titre": "Les proportions du corps", "niveau": "Débutant", "duree": "15 min",
   "consigne": "On mesure souvent un adulte en hauteurs de tête : environ 7,5 têtes. Pour dessiner un adulte de 1,70 m, quelle est la hauteur d'une tête ? Si ton personnage mesure 15 cm sur la feuille, quelle hauteur dessines-tu pour la tête ? Où se situe à peu près le milieu du corps ?",
   "criteres": ["Les deux divisions sont posées.", "Le repère du milieu du corps est indiqué."],
   "corrige": {"texte": ["Réalité : 170 ÷ 7,5 ≈ 22,7 cm par tête. Sur la feuille : 15 ÷ 7,5 = 2 cm par tête.",
                          "Le milieu du corps d'un adulte se situe à peu près au niveau du bassin, vers le haut des cuisses. Ce sont des repères moyens : "
                          "un enfant a une tête plus grande par rapport au corps, et chaque personne est un peu différente. Observe toujours ton modèle."]}},
  {"titre": "Des boîtes en perspective", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Sur une feuille A4 posée à l'horizontale, trace une ligne d'horizon. Dessine 3 boîtes en perspective à 1 point de fuite (une sous l'horizon, une coupée par l'horizon, une au-dessus), puis 3 boîtes en perspective à 2 points de fuite placés aux bords de la feuille.",
   "criteres": ["Toutes les lignes de fuite d'une boîte rejoignent bien son point de fuite.", "Les verticales restent verticales.", "On voit le dessus des boîtes sous l'horizon et le dessous de celles au-dessus."],
   "corrige": {"texte": ["En perspective à 1 point, la face avant reste un vrai rectangle et seules les arêtes de profondeur fuient. La boîte coupée par l'horizon ne montre ni son dessus ni son dessous.",
                          "En perspective à 2 points, l'arête verticale la plus proche est la plus haute. Si les boîtes semblent déformées, éloigne les points de fuite : "
                          "des points trop rapprochés écrasent les volumes. Vérifie chaque ligne avec la règle après l'avoir tracée à main levée."]}},
  {"titre": "Trois solides éclairés", "niveau": "Débutant", "duree": "45 min",
   "consigne": "Dessine une sphère, un cube et un cylindre éclairés par une seule lumière venant d'en haut à gauche. Indique la lumière, l'ombre propre, la lumière réfléchie et l'ombre portée de chacun.",
   "criteres": ["Toutes les ombres vont dans la même direction.", "Les ombres portées sont plus foncées au point de contact.", "Au moins 5 valeurs différentes sont visibles."],
   "corrige": {"texte": ["Sphère : lumière et reflet en haut à gauche, dégradé progressif vers l'ombre propre en bas à droite, mince lumière réfléchie au bord inférieur, ombre portée vers la droite.",
                          "Cube : trois faces de trois valeurs nettes (le dessus le plus clair, la face gauche moyenne, la face droite foncée), sans dégradé brusque. "
                          "Cylindre : dégradé vertical sur le corps, dessus elliptique clair. Erreur fréquente : un contour noir épais tout autour, qui aplatit le volume."]}},
  {"titre": "La nature morte du marché", "niveau": "Intermédiaire", "duree": "1 h 30",
   "consigne": "Compose une nature morte avec 3 objets de la vie quotidienne (par exemple une calebasse, un bol émaillé et une mangue) posés sur un pagne plié, éclairés par une fenêtre. Construis-les en formes simples, puis ombre-les complètement.",
   "criteres": ["Construction visible et proportions justes.", "Les objets sont bien posés sur la table grâce aux ombres portées.", "Contraste fort entre les zones claires et sombres."],
   "corrige": {"texte": ["Grille d'évaluation sur 10 : composition équilibrée sur la feuille (1 point) ; construction en formes simples (2 points) ; proportions et ellipses justes (2 points) ; "
                          "lumière cohérente sur tous les objets (2 points) ; ombres portées qui ancrent les objets (1 point) ; richesse des valeurs et contraste (1 point) ; propreté du trait final (1 point).",
                          "Les plis du pagne se traitent comme des cylindres couchés : un côté éclairé, un côté dans l'ombre. Le bol émaillé, brillant, demande des passages brusques du clair au foncé."]}}]},
{
 "id": "res-cahier-illustration", "fichier": "tobmaq-cahier-illustration.pdf", "categorie": "dessin", "logiciels": ["krita"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Illustration numérique avec Krita", "sous_titre": "Illustration · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : Krita et personnage",
 "desc": "5 exercices, de la prise en main de Krita à la fiche personnage complète, avec critères de réussite et grilles d'évaluation.",
 "intro": "Ce cahier accompagne la formation Illustrateur. Tu as besoin de Krita (gratuit, sur krita.org) et idéalement d'une tablette graphique. "
          "Enregistre toujours ton travail en .kra pour garder les calques, et exporte en PNG pour montrer ou publier.",
 "exercices": [
  {"titre": "Préparer la bonne toile", "niveau": "Débutant", "duree": "10 min",
   "consigne": "Calcule les dimensions en pixels d'une illustration destinée à être imprimée en A4 (21 × 29,7 cm) à 300 ppp, puis en A5 (14,8 × 21 cm) à 300 ppp. Crée ensuite le document A4 dans Krita avec Fichier > Nouveau.",
   "criteres": ["Les conversions en pouces sont justifiées (1 pouce = 2,54 cm).", "Le document créé dans Krita a les bonnes dimensions."],
   "corrige": {"texte": ["A4 : 21 ÷ 2,54 × 300 ≈ 2 480 px et 29,7 ÷ 2,54 × 300 ≈ 3 508 px. Toile : 2 480 × 3 508 px.",
                          "A5 : 14,8 ÷ 2,54 × 300 ≈ 1 748 px et 21 ÷ 2,54 × 300 ≈ 2 480 px. Toile : 1 748 × 2 480 px. Pour une impression à fond perdu, demande en plus la marge à l'imprimeur."]}},
  {"titre": "Prise en main et raccourcis", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Dessine une mangue en utilisant uniquement le clavier pour changer d'outil et de taille de pinceau. Utilise au moins : B, E, [ et ], Ctrl pour prélever une couleur, Espace pour déplacer la toile, M pour le miroir et Ctrl+Z.",
   "etapes": ["Règle la courbe de pression de la tablette dans les paramètres de Krita.", "Dessine le contour, puis colore la mangue.", "Vérifie le dessin en miroir avec M et corrige les défauts."],
   "criteres": ["Les raccourcis demandés sont tous utilisés.", "Le trait varie en épaisseur grâce à la pression.", "Le dessin est exporté en PNG."],
   "corrige": {"texte": ["B active le pinceau à main levée ; E bascule entre pinceau et mode gomme ; [ et ] réduisent et agrandissent la taille ; Ctrl maintenu prélève une couleur ; "
                          "Espace + glisser déplace la toile ; M affiche la vue en miroir ; Ctrl+Z annule.",
                          "Si le trait ne varie pas en épaisseur, vérifie que le pilote de la tablette est installé et que la taille du pinceau dépend bien de la pression dans l'éditeur de pinceaux."]}},
  {"titre": "Croquis, encrage, couleurs", "niveau": "Débutant", "duree": "1 h",
   "consigne": "Illustre un zémidjan à l'arrêt en utilisant trois calques nommés Croquis, Encrage et Couleurs. Baisse l'opacité du croquis pour encrer, active le stabilisateur, puis place les couleurs sous l'encrage.",
   "criteres": ["Trois calques nommés, dans le bon ordre.", "Lignes d'encrage nettes, d'épaisseurs variées.", "Les couleurs ne débordent pas sur les traits."],
   "corrige": {"texte": ["Ordre des calques, de haut en bas : Encrage, Couleurs, Croquis (masqué à la fin). Opacité du croquis autour de 20 à 30 %.",
                          "Encrage : contour extérieur plus épais, détails (rayons des roues, plis du gilet) plus fins. Le stabilisateur se règle dans les options de l'outil pinceau, "
                          "rubrique lissage du pinceau. Les aplats se posent avec l'outil de remplissage ou au pinceau, sur le calque Couleurs."]}},
  {"titre": "Silhouettes et turnaround", "niveau": "Intermédiaire", "duree": "1 h 30",
   "consigne": "Pour un personnage de pêcheur de Ganvié, dessine 10 silhouettes noires différentes, choisis-en une, puis réalise son turnaround face, profil et dos avec des lignes de repère horizontales.",
   "criteres": ["Les 10 silhouettes sont vraiment différentes (formes, postures, accessoires).", "La silhouette choisie est reconnaissable sans détail intérieur.", "Les trois vues ont la même taille et les mêmes repères."],
   "corrige": {"texte": ["Les silhouettes réussies jouent sur un ou deux éléments forts : chapeau large, filet de pêche, pagaie, posture penchée sur la pirogue.",
                          "Lignes de repère attendues : sommet du crâne, yeux, menton, épaules, taille, genoux, plante des pieds. Chaque vue s'aligne sur ces lignes. "
                          "Erreur fréquente : un profil plus petit que la face, ou des bras plus longs de dos."]}},
  {"titre": "La fiche personnage", "niveau": "Intermédiaire", "duree": "3 h",
   "consigne": "Réalise la fiche personnage complète de ton pêcheur sur une toile de 3 508 × 2 480 px : nom, turnaround en couleur, 4 expressions, 2 accessoires détaillés, palette avec codes couleur et 3 lignes de présentation.",
   "criteres": ["Tous les éléments demandés sont présents.", "Palette limitée et cohérente.", "Une seule direction de lumière pour toutes les ombres.", "Mise en page claire et lisible."],
   "corrige": {"texte": ["Grille d'évaluation sur 10 : silhouette lisible et originale (2 points) ; turnaround cohérent (2 points) ; expressions variées et justes (1 point) ; "
                          "encrage net (1 point) ; palette limitée avec codes couleur (1 point) ; ombres cohérentes (1 point) ; mise en page et textes de la fiche (2 points).",
                          "La fiche doit permettre à un autre illustrateur de dessiner le même personnage sans te poser de question : c'est le vrai test de réussite."]}}]}
]

CAHIERS_B = [
{
 "id": "res-cahier-informatique", "fichier": "tobmaq-cahier-informatique.pdf", "categorie": "informatique", "logiciels": ["windows"], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Informatique : bases et maintenance", "sous_titre": "Informatique · 5 exercices de diagnostic et d'entretien et leurs corrigés",
 "titre_court": "Cahier d'exercices : matériel, diagnostic et maintenance",
 "desc": "5 exercices concrets, de la lecture d'une fiche technique à la réinstallation de Windows, avec budget en FCFA et corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Informatique : bases et maintenance ». Il te met dans la situation d'un technicien qui dépanne "
          "les ordinateurs d'un cybercafé, d'un secrétariat ou d'une PME. Un ordinateur sous Windows 10 ou 11 suffit pour tous les exercices.",
 "exercices": [
  {"titre": "Lire une fiche technique", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Un client de Cotonou te montre l'annonce ci-dessous pour un portable d'occasion à 180 000 FCFA. Pour chaque ligne, dis à quel "
               "composant elle correspond et si elle te paraît suffisante pour de la bureautique, Internet et un peu de visioconférence.",
   "code": "Processeur : Intel Core i5-8250U, 4 cœurs, 1,6 GHz\nMémoire : 4 Go DDR4\nStockage : HDD 1 To 5400 tr/min\n"
           "Écran : 15,6 pouces 1366 x 768\nSystème : Windows 10 Professionnel\nBatterie : tient 1 h 30",
   "criteres": ["Les 6 lignes sont associées au bon composant.", "Au moins deux faiblesses sont identifiées et justifiées.",
                "Une amélioration chiffrée est proposée."],
   "corrige": {"texte": ["Processeur : correct pour la bureautique (4 cœurs). Mémoire vive : 4 Go est insuffisant, il faut au moins 8 Go. "
                          "Stockage : un HDD à 5400 tr/min est le principal frein, un SSD rendra le PC bien plus réactif ; 1 To est en revanche "
                          "confortable. Écran : résolution modeste mais utilisable. Système : Windows 10 ne reçoit plus de correctifs de sécurité "
                          "gratuits depuis le 14 octobre 2025 ; vérifie dans Paramètres > Windows Update si le passage à Windows 11 est proposé "
                          "(ce processeur de 8e génération figure parmi les processeurs compatibles, mais il faut aussi TPM 2.0 et le démarrage sécurisé). "
                          "Batterie : usée, à prévoir dans le budget.",
                          "Conseil au client : négocier le prix en tenant compte d'un SSD, d'une barrette de RAM supplémentaire et d'une batterie."]}},
  {"titre": "Le diagnostic au Gestionnaire des tâches", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Pour chacun des trois postes ci-dessous, observés dans l'onglet Performances du Gestionnaire des tâches (Ctrl+Maj+Échap), "
               "indique le composant en cause et la solution.",
   "etapes": ["Poste A : Disque 0 (HDD) à 100 % pendant 10 minutes après le démarrage, processeur à 15 %, mémoire à 55 %.",
              "Poste B : mémoire à 94 % (3,7 Go sur 4 Go), 25 onglets ouverts dans le navigateur, disque à 60 %.",
              "Poste C : processeur à 100 % en permanence à cause d'un processus au nom inconnu, même quand aucun programme n'est ouvert."],
   "criteres": ["Le composant saturé est identifié pour chaque poste.", "La solution proposée traite la cause, pas le symptôme.",
                "Le poste C est traité comme un incident de sécurité possible."],
   "corrige": {"texte": ["Poste A : le disque dur est le goulot d'étranglement. Solution durable : remplacer le HDD par un SSD. En attendant, "
                          "réduire les applications de démarrage.",
                          "Poste B : la mémoire vive est saturée, Windows utilise alors le disque comme mémoire de secours, ce qui ralentit tout. "
                          "Solution immédiate : fermer des onglets. Solution durable : passer à 8 Go de RAM.",
                          "Poste C : un processus inconnu qui monopolise le processeur peut être un logiciel malveillant (par exemple un mineur de "
                          "cryptomonnaie). Clic droit sur le processus > Ouvrir l'emplacement du fichier, recherche de son nom, puis analyse complète "
                          "avec Microsoft Defender. Déconnecte le poste du réseau si le doute persiste."]}},
  {"titre": "Mise à niveau ou PC neuf ?", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Un cybercafé de Cotonou possède 5 postes lents (HDD et 4 Go de RAM). Un SSD de 256 Go coûte 20 000 FCFA, une barrette de 4 Go "
               "15 000 FCFA, la main-d'œuvre 5 000 FCFA par poste. Un PC neuf équivalent coûte 250 000 FCFA. Calcule le coût des deux options "
               "pour les 5 postes et l'économie réalisée.",
   "criteres": ["Le coût par poste et le total sont détaillés.", "L'économie est calculée et la décision est argumentée."],
   "corrige": {"texte": ["Mise à niveau : 20 000 + 15 000 + 5 000 = 40 000 FCFA par poste, soit 40 000 × 5 = 200 000 FCFA pour les 5 postes.",
                          "PC neufs : 250 000 × 5 = 1 250 000 FCFA. Économie : 1 250 000 - 200 000 = 1 050 000 FCFA.",
                          "Décision : la mise à niveau est rentable si les processeurs suffisent aux usages et si le système reçoit encore des "
                          "mises à jour de sécurité. Sinon, une partie de l'économie doit être réservée au remplacement progressif des postes."]}},
  {"titre": "Le plan de sauvegarde 3-2-1", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Le secrétariat d'une PME de Porto-Novo a un seul ordinateur qui contient les factures, les contrats et la comptabilité. "
               "Rédige son plan de sauvegarde selon la règle 3-2-1.",
   "etapes": ["Liste les dossiers à sauvegarder.", "Indique les 3 copies, les 2 supports et la copie hors site.",
              "Précise la fréquence, la personne responsable et le test de restauration."],
   "criteres": ["La règle 3-2-1 est respectée.", "Au moins une copie est hors ligne.", "Un test de restauration est prévu."],
   "corrige": {"texte": ["Copie 1 : les fichiers sur le PC (dossiers Documents, Bureau, Comptabilité). Copie 2 : un disque externe, avec l'outil "
                          "Historique des fichiers de Windows ou une copie manuelle, chaque vendredi à 17 h ; le disque est débranché ensuite et "
                          "rangé dans une armoire fermée. Copie 3, hors site : synchronisation sur un cloud (OneDrive ou Google Drive) ou un "
                          "second disque gardé au domicile du gérant et échangé chaque semaine.",
                          "Deux supports différents : le disque interne du PC et le disque externe (le cloud est un support supplémentaire). "
                          "Responsable : la secrétaire, avec un rappel dans son agenda. Test : le premier lundi du mois, restaurer un fichier "
                          "au hasard depuis le disque externe et vérifier qu'il s'ouvre."]}},
  {"titre": "Remettre les étapes dans l'ordre", "niveau": "Intermédiaire", "duree": "15 min",
   "consigne": "Voici, dans le désordre, les étapes de la réinstallation de Windows sur un PC de lycée. Remets-les dans le bon ordre et "
               "explique pourquoi l'étape de sauvegarde ne peut pas être déplacée.",
   "code": "a) Installer les pilotes manquants depuis le site du fabricant\nb) Démarrer sur la clé USB (touche F12, F9 ou Échap)\n"
           "c) Sauvegarder les fichiers et vérifier qu'ils s'ouvrent\nd) Lancer Windows Update jusqu'au bout\n"
           "e) Créer la clé avec l'outil officiel de Microsoft (8 Go minimum)\nf) Restaurer les fichiers de l'utilisateur\n"
           "g) Installation personnalisée, partitions du disque système supprimées\nh) Vérifier Microsoft Defender et le Gestionnaire de périphériques",
   "criteres": ["L'ordre est correct.", "Le rôle de la sauvegarde avant la suppression des partitions est expliqué."],
   "corrige": {"texte": ["Ordre : c, e, b, g, d, a, h, f. On peut aussi restaurer les fichiers (f) juste après les pilotes : l'essentiel est que "
                          "le système soit à jour et protégé avant d'y remettre les données.",
                          "La sauvegarde vient obligatoirement en premier : supprimer les partitions efface tout le contenu du disque. Une "
                          "sauvegarde non vérifiée ne compte pas : on ouvre quelques fichiers avant d'effacer quoi que ce soit."]}}]},
{
 "id": "res-cahier-reseau", "fichier": "tobmaq-cahier-reseau.pdf", "categorie": "informatique", "logiciels": ["packettracer"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Réseaux : adressage et câblage", "sous_titre": "Réseaux · 5 exercices, du calcul d'adresses au laboratoire Packet Tracer",
 "titre_court": "Cahier d'exercices : adresses IP, sous-réseaux et câblage",
 "desc": "5 exercices progressifs : binaire, calculs de sous-réseaux, découpage d'un réseau de lycée, sertissage RJ45 et laboratoire Packet Tracer, avec corrigés.",
 "intro": "Ce cahier accompagne la formation « Réseaux : concevoir et câbler un réseau local ». Les calculs se font au crayon : vérifie-les "
          "ensuite avec un calculateur IP en ligne. Le dernier exercice demande Cisco Packet Tracer, gratuit avec un compte Cisco Networking Academy.",
 "exercices": [
  {"titre": "Binaire et masques", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Convertis en binaire les nombres 192, 168 et 224. Donne ensuite la notation CIDR des masques 255.255.255.0, 255.255.255.192 "
               "et 255.255.255.224, puis le masque décimal de /25 et de /20.",
   "criteres": ["Les trois conversions sont justes (8 bits chacune).", "Les cinq masques sont justes."],
   "corrige": {"texte": ["Poids des bits d'un octet : 128, 64, 32, 16, 8, 4, 2, 1. 192 = 128 + 64 = 11000000. 168 = 128 + 32 + 8 = 10101000. "
                          "224 = 128 + 64 + 32 = 11100000.",
                          "255.255.255.0 = /24 (8 + 8 + 8). 255.255.255.192 = /26 (24 + 2 bits à 1). 255.255.255.224 = /27 (24 + 3). "
                          "/25 = 255.255.255.128. /20 = 255.255.240.0 (16 + 4 bits à 1 dans le troisième octet : 128 + 64 + 32 + 16 = 240)."]}},
  {"titre": "Calculer un sous-réseau", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Pour chaque adresse, donne l'adresse du réseau, la première et la dernière adresse utilisables, la diffusion et le nombre "
               "d'appareils possibles.",
   "code": "a) 192.168.1.130/26\nb) 192.168.20.14/27\nc) 10.10.5.200/25",
   "criteres": ["Les 15 valeurs sont justes.", "La méthode (nombre magique ou binaire) est écrite."],
   "corrige": {"texte": ["Méthode : nombre magique = 256 - octet du masque. Le sous-réseau commence au multiple de ce nombre juste inférieur "
                          "ou égal à l'octet de l'adresse."],
               "code": "a) /26, magique 256-192 = 64 ; 130 est entre 128 et 191\n"
                       "   Réseau 192.168.1.128  Utilisables .129 à .190\n"
                       "   Diffusion 192.168.1.191  2^6 - 2 = 62 appareils\n"
                       "b) /27, magique 256-224 = 32 ; 14 est entre 0 et 31\n"
                       "   Réseau 192.168.20.0  Utilisables .1 à .30\n"
                       "   Diffusion 192.168.20.31  2^5 - 2 = 30 appareils\n"
                       "c) /25, magique 256-128 = 128 ; 200 est entre 128 et 255\n"
                       "   Réseau 10.10.5.128  Utilisables .129 à .254\n"
                       "   Diffusion 10.10.5.255  2^7 - 2 = 126 appareils"}},
  {"titre": "Le plan d'adressage du lycée", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Un lycée de Parakou dispose du réseau 192.168.50.0/24. Il faut : une salle informatique de 100 postes, une salle des "
               "enseignants de 40 appareils, l'administration avec 20 appareils et un Wi-Fi invités de 25 appareils. Attribue à chaque "
               "zone le plus petit sous-réseau suffisant, sans chevauchement, et donne sa passerelle (première adresse utilisable).",
   "etapes": ["Trouve le préfixe nécessaire pour chaque zone (2^n - 2 doit être supérieur ou égal au besoin).",
              "Place les sous-réseaux du plus grand au plus petit.", "Présente le résultat sous forme de tableau."],
   "criteres": ["Chaque sous-réseau contient assez d'adresses.", "Aucun sous-réseau ne chevauche un autre.", "Les passerelles sont justes."],
   "corrige": {"texte": ["100 postes : /25 (126 adresses). 40 : /26 (62). 20 : /27 (30). 25 : /27 (30). On commence par le plus grand pour "
                          "que chaque sous-réseau démarre sur une limite correcte. Le /24 est entièrement utilisé : 128 + 64 + 32 + 32 = 256 adresses."],
               "code": "Zone            Sous-réseau          Passerelle     Diffusion\n"
                       "Salle info      192.168.50.0/25      192.168.50.1   192.168.50.127\n"
                       "Enseignants     192.168.50.128/26    192.168.50.129 192.168.50.191\n"
                       "Administration  192.168.50.192/27    192.168.50.193 192.168.50.223\n"
                       "Wi-Fi invités   192.168.50.224/27    192.168.50.225 192.168.50.255"}},
  {"titre": "Sertir et contrôler un câble", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Écris l'ordre des 8 fils de la norme T568B. Un stagiaire a serti un câble avec T568B à un bout et l'ordre ci-dessous à "
               "l'autre bout : identifie le problème et ses conséquences.",
   "code": "Broche : 1            2       3           4     5\n"
           "Fil    : blanc-orange orange  blanc-bleu  bleu  blanc-vert\n"
           "Broche : 6            7             8\n"
           "Fil    : vert         blanc-marron  marron",
   "criteres": ["L'ordre T568B est juste.", "L'erreur est localisée précisément (broches 3 et 5).", "La correction est décrite."],
   "corrige": {"texte": ["T568B : 1 blanc-orange, 2 orange, 3 blanc-vert, 4 bleu, 5 blanc-bleu, 6 vert, 7 blanc-marron, 8 marron.",
                          "Les fils blanc-vert et blanc-bleu sont inversés (broches 3 et 5). Les paires sont alors séparées : le fil blanc-vert "
                          "n'est plus torsadé avec le vert. Le testeur signale une erreur de câblage et, même si le lien s'établit parfois, il "
                          "sera instable ou limité en vitesse. Il faut couper le connecteur et sertir à nouveau dans l'ordre T568B, puis "
                          "repasser le câble au testeur."]}},
  {"titre": "Laboratoire Packet Tracer", "niveau": "Intermédiaire", "duree": "1 h",
   "consigne": "Construis dans Packet Tracer le réseau d'un cybercafé, puis résous la panne décrite à la fin.",
   "etapes": ["1 routeur (passerelle 192.168.1.1/24), 1 switch, 6 PC, 1 imprimante en 192.168.1.10 et 1 point d'accès.",
              "Câbles droits partout ; PC en adresses fixes de 192.168.1.101 à 192.168.1.106, masque 255.255.255.0.",
              "Wi-Fi en WPA2-PSK avec chiffrement AES et une phrase de passe d'au moins 12 caractères.",
              "Panne : le PC6 ne joint ni l'imprimante ni la passerelle. Sa configuration est 192.168.10.106, masque 255.255.255.0, passerelle 192.168.1.1."],
   "criteres": ["Tous les PC joignent la passerelle et l'imprimante par ping.", "Le plan d'adressage est fourni.", "La panne du PC6 est expliquée."],
   "corrige": {"texte": ["Tests attendus dans Desktop > Command Prompt de chaque PC : ping 192.168.1.1 puis ping 192.168.1.10.",
                          "Panne du PC6 : son adresse 192.168.10.106/24 appartient au réseau 192.168.10.0/24, et non à 192.168.1.0/24. "
                          "Pour lui, l'imprimante et la passerelle sont sur un autre réseau : il ne peut joindre l'imprimante "
                          "directement, et sa passerelle 192.168.1.1 est hors de son réseau, donc inutilisable. Correction : adresse "
                          "192.168.1.106. Si le ping échoue encore, vérifie le câble (lien vert aux deux bouts) et le port du switch."],
               "code": "C:\\> ipconfig\n  IPv4 Address......: 192.168.1.106\n  Subnet Mask.......: 255.255.255.0\n"
                       "  Default Gateway...: 192.168.1.1\nC:\\> ping 192.168.1.10\nReply from 192.168.1.10: bytes=32 ...   (4 réponses attendues)"}}]},
{
 "id": "res-cahier-admin", "fichier": "tobmaq-cahier-admin-systeme.pdf", "categorie": "informatique", "logiciels": ["linux"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Administrer un serveur Linux", "sous_titre": "Administration système · 5 exercices et leurs corrigés en commandes",
 "titre_court": "Cahier d'exercices : administration Linux et services",
 "desc": "5 exercices sur Ubuntu Server : droits en octal, utilisateurs et groupes, crontab, partage Samba et supervision, avec les commandes corrigées.",
 "intro": "Ce cahier accompagne la formation « Administrateur réseau et système ». Travaille dans une machine virtuelle Ubuntu Server LTS "
          "(VirtualBox est gratuit) : tu peux tout essayer sans risque et revenir en arrière avec un instantané.",
 "exercices": [
  {"titre": "Les droits en octal", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Convertis en octal : rwxr-x---, rw-r--r--, rw-------, rwxrwx---. Convertis ensuite en lettres : 755, 640, 700. "
               "Pour chaque cas, dis qui peut lire le fichier.",
   "criteres": ["Les 7 conversions sont justes.", "La règle r = 4, w = 2, x = 1 est appliquée par groupe de trois lettres."],
   "corrige": {"texte": ["rwxr-x--- = 750 · rw-r--r-- = 644 · rw------- = 600 · rwxrwx--- = 770.",
                          "755 = rwxr-xr-x (tout le monde lit et exécute, seul le propriétaire écrit) · 640 = rw-r----- (propriétaire et groupe "
                          "lisent, les autres rien) · 700 = rwx------ (seul le propriétaire a accès).",
                          "Sur un dossier, x signifie « pouvoir y entrer » : un dossier en 640 est inutilisable, on lui donne plutôt 750 ou 770."]}},
  {"titre": "Utilisateurs, groupes et dossiers", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Sur le serveur d'une PME de Porto-Novo, crée les groupes compta et direction, les utilisateurs awa (compta), koffi (compta) "
               "et mariam (direction), et deux dossiers /srv/compta et /srv/direction accessibles chacun à son seul groupe.",
   "criteres": ["Chaque dossier appartient au bon groupe, en 770.", "awa ne peut pas lire /srv/direction (testé avec su - awa).",
                "Aucun dossier en 777."],
   "corrige": {"texte": ["On crée d'abord les groupes, puis les utilisateurs, puis on les ajoute aux groupes avec usermod -aG (le -a évite de "
                          "les retirer de leurs autres groupes). Un utilisateur doit se reconnecter pour que son nouveau groupe soit pris en compte."],
               "code": "sudo groupadd compta\nsudo groupadd direction\n"
                       "sudo adduser awa\nsudo adduser koffi\nsudo adduser mariam\n"
                       "sudo usermod -aG compta awa\nsudo usermod -aG compta koffi\nsudo usermod -aG direction mariam\n"
                       "sudo mkdir -p /srv/compta /srv/direction\n"
                       "sudo chown root:compta /srv/compta\nsudo chown root:direction /srv/direction\n"
                       "sudo chmod 770 /srv/compta /srv/direction\nls -ld /srv/*\n"
                       "su - awa -c 'ls /srv/direction'   # doit afficher : Permission non accordée"}},
  {"titre": "Écrire une crontab", "niveau": "Intermédiaire", "duree": "20 min",
   "consigne": "Écris la ligne cron (5 champs puis la commande /usr/local/bin/sauvegarde.sh) pour chacun des horaires suivants.",
   "code": "a) Tous les jours à 23 h 45\nb) Du lundi au vendredi à 18 h\nc) Le 1er de chaque mois à 3 h\n"
           "d) Toutes les 15 minutes\ne) Chaque dimanche à 4 h 30",
   "criteres": ["Les 5 lignes sont justes.", "L'ordre des champs est respecté : minute, heure, jour du mois, mois, jour de la semaine."],
   "corrige": {"texte": ["Rappel : jour de la semaine 0 ou 7 = dimanche, 1 = lundi. Dans une crontab, le caractère % doit être écrit \\%. "
                          "Ajoute >> /var/log/sauvegarde.log 2>&1 pour garder une trace de chaque exécution."],
               "code": "45 23 * * *    /usr/local/bin/sauvegarde.sh   # a)\n"
                       "0 18 * * 1-5   /usr/local/bin/sauvegarde.sh   # b)\n"
                       "0 3 1 * *      /usr/local/bin/sauvegarde.sh   # c)\n"
                       "*/15 * * * *   /usr/local/bin/sauvegarde.sh   # d)\n"
                       "30 4 * * 0     /usr/local/bin/sauvegarde.sh   # e)"}},
  {"titre": "Un partage Samba pour Windows", "niveau": "Avancé", "duree": "45 min",
   "consigne": "Rends le dossier /srv/compta accessible depuis les postes Windows sous le nom compta, uniquement pour les membres du "
               "groupe compta, en lecture et écriture.",
   "etapes": ["Installe Samba.", "Ajoute la section de partage dans /etc/samba/smb.conf.", "Crée le mot de passe Samba de awa et koffi.",
              "Vérifie la configuration, redémarre le service et ouvre \\\\IP-du-serveur\\compta depuis l'Explorateur Windows."],
   "criteres": ["testparm ne signale aucune erreur.", "awa accède au partage, mariam est refusée.", "Le service smbd est actif au démarrage."],
   "corrige": {"texte": ["Les mots de passe Samba sont distincts des mots de passe Linux : sans smbpasswd -a, l'utilisateur ne peut pas se "
                          "connecter au partage. Si le pare-feu ufw est actif, autorise Samba avec sudo ufw allow samba."],
               "code": "sudo apt install samba\nsudo nano /etc/samba/smb.conf   # ajouter à la fin :\n"
                       "[compta]\n   path = /srv/compta\n   valid users = @compta\n   read only = no\n   browseable = yes\n\n"
                       "sudo smbpasswd -a awa\nsudo smbpasswd -a koffi\ntestparm\n"
                       "sudo systemctl restart smbd\nsystemctl is-enabled smbd   # doit afficher enabled"}},
  {"titre": "Supervision et documentation", "niveau": "Avancé", "duree": "30 min",
   "consigne": "Voici la sortie de df -h sur le serveur d'une ONG de Cotonou. Interprète-la, propose les actions et rédige les 6 rubriques "
               "minimales du dossier d'exploitation de ce serveur.",
   "code": "Sys. de fichiers Taille Utilisé Dispo Uti% Monté sur\n"
           "/dev/sda2          98G     91G  2,4G  98% /\n"
           "/dev/sdb1         916G    412G  458G  48% /srv",
   "criteres": ["La partition critique est identifiée.", "Les commandes de recherche sont justes.", "La documentation ne contient aucun mot de passe."],
   "corrige": {"texte": ["La partition racine / est pleine à 98 % : au-delà de 85 %, il faut agir, et à 100 % les services (journaux, bases, "
                          "mises à jour) tombent en panne. /srv est à 48 %, sans urgence.",
                          "Actions : trouver les dossiers les plus lourds, nettoyer les paquets inutiles et limiter la taille des journaux. "
                          "Ensuite, planifier un relevé quotidien de df -h.",
                          "Dossier d'exploitation : 1) schéma du réseau ; 2) plan d'adressage ; 3) serveurs et services (rôle, version, ports) ; "
                          "4) sauvegardes (quoi, où, quand) et procédure de restauration testée ; 5) tâches planifiées (crontab) ; "
                          "6) contacts (prestataires, fournisseur d'accès). Les mots de passe restent dans un gestionnaire de mots de passe."],
               "code": "sudo du -xh / --max-depth=1 | sort -h | tail   # dossiers lourds\n"
                       "sudo apt autoremove && sudo apt clean          # paquets inutiles\n"
                       "journalctl --disk-usage                        # place des journaux\n"
                       "sudo journalctl --vacuum-size=500M             # limiter à 500 Mo"}}]},
{
 "id": "res-cahier-cyber", "fichier": "tobmaq-cahier-cybersecurite.pdf", "categorie": "informatique", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Cybersécurité au quotidien et en entreprise", "sous_titre": "Cybersécurité · 5 mises en situation défensives et leurs corrigés",
 "titre_court": "Cahier d'exercices : se protéger et protéger une entreprise",
 "desc": "5 mises en situation : repérer l'hameçonnage, choisir ses mots de passe, sécuriser son téléphone, organiser une PME et réagir à un rançongiciel.",
 "intro": "Ce cahier accompagne la formation « Cybersécurité : se protéger et protéger une entreprise ». Tous les exercices sont défensifs : "
          "il s'agit de protéger, de détecter et de réagir. Les situations sont inspirées d'arnaques réellement rencontrées au Bénin.",
 "exercices": [
  {"titre": "Vrai message ou arnaque ?", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Pour chacun des messages suivants, dis s'il est suspect et cite les signes qui t'alertent. Indique la bonne réaction.",
   "etapes": ["SMS d'un numéro ordinaire : « Vous avez reçu 25 000 FCFA par erreur, merci de les renvoyer au 01 XX XX XX XX. »",
              "WhatsApp d'un ami : « Envoie-moi vite le code à 6 chiffres que tu viens de recevoir, je me suis trompé de numéro. »",
              "E-mail : « Votre compte bancaire sera suspendu dans 2 heures. Confirmez vos informations ici : banque-securite-verif.com »",
              "Message : « Recrutement urgent, 300 000 FCFA par mois sans diplôme, payez 5 000 FCFA de frais de dossier. »",
              "Notification de l'application officielle de ta banque, ouverte par toi-même, qui affiche ton relevé du mois."],
   "criteres": ["Les 4 arnaques sont repérées.", "Pour chacune, au moins deux signes sont cités.", "La bonne réaction est donnée."],
   "corrige": {"texte": ["1) Arnaque : vérifie ton solde par le menu officiel de l'opérateur, jamais d'après le SMS ; rien n'est arrivé, ne renvoie rien. "
                          "2) Arnaque très courante : ce code sert à installer ton WhatsApp sur le téléphone du fraudeur, dont le compte de "
                          "ton ami a probablement été piraté. Ne le donne jamais, préviens ton ami par un appel. "
                          "3) Hameçonnage : urgence, adresse qui n'est pas celle de la banque. Ne clique pas, contacte ta banque par son numéro officiel. "
                          "4) Arnaque à l'emploi : un vrai employeur ne fait pas payer de frais de dossier. "
                          "5) Légitime : c'est toi qui as ouvert l'application officielle."]}},
  {"titre": "Classer des mots de passe", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Classe ces mots de passe du plus faible au plus solide et explique ton classement. Propose ensuite une phrase de passe pour ton téléphone.",
   "code": "a) Koffi1998\nb) 123456\nc) mangue-taxi-moto-lagune-violet\nd) P@ssw0rd!\ne) Cotonou2026",
   "criteres": ["Le classement est justifié.", "La phrase de passe proposée compte au moins 4 mots sans lien entre eux."],
   "corrige": {"texte": ["Du plus faible au plus solide : b, d, a et e (à égalité), c. 123456 est le mot de passe le plus essayé au monde. "
                          "P@ssw0rd! remplace des lettres par des symboles de façon prévisible : les logiciels d'attaque connaissent ces "
                          "substitutions. Koffi1998 et Cotonou2026 combinent un prénom ou une ville et une année, faciles à deviner à partir "
                          "des réseaux sociaux. La phrase de passe c est longue (30 caractères) et sans lien logique : de loin la plus solide.",
                          "Rappel : même un excellent mot de passe ne doit servir que pour un seul compte. Utilise un gestionnaire pour les autres."]}},
  {"titre": "Le bilan de ton téléphone", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Fais le bilan de sécurité de ton téléphone en vérifiant chaque point, et corrige ce qui manque.",
   "etapes": ["Verrouillage par code d'au moins 6 chiffres ou empreinte, délai de verrouillage automatique.",
              "Système et applications à jour, applications installées uniquement depuis la boutique officielle.",
              "WhatsApp : validation en deux étapes activée avec un code PIN et une adresse e-mail de récupération.",
              "Messagerie e-mail : double authentification activée.", "Localisation et effacement à distance activés."],
   "criteres": ["Les 5 points sont vérifiés.", "Les réglages manquants sont activés.", "Un plan est noté en cas de perte du téléphone."],
   "corrige": {"texte": ["Chemins utiles : WhatsApp > Paramètres > Compte > Validation en deux étapes. Android : Paramètres > Sécurité > "
                          "Localiser mon appareil. iPhone : Réglages > ton nom > Localiser.",
                          "Plan en cas de perte : 1) localiser ou effacer le téléphone à distance ; 2) appeler l'opérateur pour bloquer la carte SIM "
                          "et le compte mobile money ; 3) changer le mot de passe de la messagerie depuis un autre appareil ; 4) réinstaller "
                          "WhatsApp sur une nouvelle SIM avec le même numéro."]}},
  {"titre": "Organiser la sécurité d'une PME", "niveau": "Intermédiaire", "duree": "45 min",
   "consigne": "Une PME de Porto-Novo compte 8 salariés, un serveur de fichiers, un routeur Wi-Fi et des comptes de messagerie. Tout le monde "
               "utilise le compte administrateur « Bureau ». Propose une organisation sécurisée.",
   "etapes": ["Rédige l'inventaire (appareils, comptes, données sensibles).", "Définis les comptes et leurs droits selon le moindre privilège.",
              "Décris la sauvegarde 3-2-1 avec une copie hors ligne.", "Propose le réglage du Wi-Fi (personnel et invités)."],
   "criteres": ["Un compte nominatif standard par salarié.", "Au moins une copie de sauvegarde hors ligne.", "Le Wi-Fi invités est isolé."],
   "corrige": {"texte": ["Comptes : un compte standard nominatif par salarié, un seul compte administrateur réservé à l'informaticien, désactivation "
                          "le jour du départ. Dossiers par service : chacun n'accède qu'aux dossiers de son équipe. Double authentification sur "
                          "toutes les messageries.",
                          "Sauvegarde : copie 1 sur le serveur, copie 2 chaque nuit sur un disque dédié, copie 3 chaque vendredi sur un disque "
                          "externe débranché et emporté hors des locaux (en alternance avec un second disque). Test de restauration mensuel.",
                          "Wi-Fi : réseau du personnel en WPA2-AES ou WPA3, réseau invités isolé avec son propre mot de passe, WPS désactivé, "
                          "mot de passe d'administration du routeur changé. Mises à jour automatiques partout."]}},
  {"titre": "Exercice sur table : le rançongiciel", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Lundi, 8 h. Dans une ONG de Cotonou, les fichiers du serveur portent une extension inconnue et une note réclame une rançon en "
               "cryptomonnaie. Rédige la fiche réflexe : qui fait quoi, dans quel ordre, pendant les premières heures.",
   "criteres": ["L'isolement vient en premier.", "La rançon n'est pas payée.", "La restauration part d'une sauvegarde saine et hors ligne.",
                "Le signalement aux autorités compétentes est prévu."],
   "corrige": {"texte": ["1) Isoler : débrancher le câble réseau et couper le Wi-Fi des appareils touchés, sans les éteindre si possible (des traces "
                          "utiles à l'analyse restent en mémoire). 2) Alerter le responsable désigné et le prestataire informatique. 3) Ne pas payer : "
                          "rien ne garantit la récupération des données, et cela finance les attaquants. 4) Photographier la note de rançon et noter "
                          "l'heure des constats. 5) Changer les mots de passe depuis un appareil sain, en commençant par les comptes administrateur "
                          "et la messagerie. 6) Vérifier que la sauvegarde hors ligne est intacte, réinstaller les systèmes touchés, restaurer.",
                          "7) Signaler : porter plainte auprès de la police et solliciter le bjCSIRT, le centre national de réponse aux incidents de "
                          "cybersécurité du Bénin, dont les coordonnées figurent sur son site officiel. 8) Après l'incident : comprendre l'origine "
                          "(e-mail piégé, mot de passe faible, système non mis à jour) et corriger la faiblesse."]}}]},
]

CAHIERS_C = [
{
 "id": "res-cahier-marketing", "fichier": "tobmaq-cahier-marketing.pdf", "categorie": "marketing", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Les fondamentaux du marketing", "sous_titre": "Marketing · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : fondamentaux du marketing",
 "desc": "5 exercices progressifs, de l'analyse des concurrents au plan de communication, avec calcul de prix et corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Les fondamentaux du marketing ». Tu n'as besoin que d'un carnet, d'un tableur et de quelques conversations avec "
          "de vrais clients. Tous les chiffres utilisés sont des exemples pour t'entraîner : remplace-les par ceux de ton activité dès que possible.",
 "exercices": [
  {"titre": "Analyser trois concurrents", "niveau": "Débutant", "duree": "45 min",
   "consigne": "Tu conseilles un nouveau restaurant de plats locaux à Abomey-Calavi, près du campus. Construis un tableau d'analyse de 3 concurrents (deux directs, un indirect).",
   "etapes": ["Colonnes : nom, type (direct ou indirect), produits, fourchette de prix, canaux de vente, points forts, points faibles, ce que disent les clients.",
              "Remplis le tableau à partir d'une visite, des pages Facebook ou Google Maps et d'au moins 3 conversations.",
              "Termine par 3 opportunités : des besoins mal servis par les concurrents."],
   "criteres": ["Au moins un concurrent indirect est identifié.", "Chaque point fort ou faible est observé, pas supposé.", "Les 3 opportunités découlent du tableau."],
   "corrige": {"texte": ["Exemple de tableau attendu. Concurrent A (direct) : maquis familial, plats du jour, environ 1 000 à 1 500 FCFA en exemple, vente sur place uniquement ; "
                          "points forts : portions copieuses, prix bas ; points faibles : attente longue à midi, pas de livraison, horaires irréguliers. "
                          "Concurrent B (direct) : restaurant avec page Facebook, prix plus élevés, livraison ; point faible : réponses lentes sur WhatsApp selon les avis. "
                          "Concurrent C (indirect) : vendeuses de rue et repas préparés à la maison ; point fort : prix très bas ; point faible : choix limité, hygiène variable selon les clients interrogés.",
                          "Opportunités possibles : un repas servi en moins de 10 minutes à midi pour les étudiants pressés ; la commande WhatsApp avec réponse rapide ; un menu du jour annoncé chaque matin. "
                          "Erreur fréquente : oublier le concurrent indirect, alors que c'est souvent le principal rival pour un public au budget serré."]}},
  {"titre": "Segmenter et créer un persona", "niveau": "Débutant", "duree": "40 min",
   "consigne": "Pour une boutique de pagnes et de tenues sur mesure à Cotonou, propose 3 segments de clientèle, choisis-en un et rédige le persona correspondant.",
   "etapes": ["Pour chaque segment : critères (âge, lieu, besoin, comportement d'achat), taille estimée (petite, moyenne, grande), facilité à l'atteindre.",
              "Justifie le choix du segment prioritaire en 3 phrases.",
              "Persona : prénom, âge, métier, ville, budget d'exemple, réseaux utilisés, besoins, freins, objections, phrase qu'il pourrait dire."],
   "criteres": ["Les 3 segments sont vraiment différents.", "Le choix est justifié par des critères, pas par un goût personnel.", "Le persona contient au moins un frein et une objection."],
   "corrige": {"texte": ["Segments possibles : 1) Femmes de 25 à 40 ans qui préparent une cérémonie (besoin : une tenue unique et prête à temps). "
                          "2) Membres de la diaspora qui commandent depuis l'étranger (besoin : confiance, envoi fiable). "
                          "3) Associations et familles qui commandent un même pagne en grande quantité (besoin : prix de groupe, délai).",
                          "Choix argumenté du segment 1 : il est nombreux, joignable par WhatsApp et Facebook, achète régulièrement (mariages, baptêmes, fêtes) et accepte de payer plus pour la fiabilité.",
                          "Persona attendu : « Carine, 29 ans, comptable à Cotonou. Budget d'exemple : 30 000 à 40 000 FCFA par tenue. Utilise WhatsApp et Instagram. Besoin : une tenue assortie au thème de la fête. "
                          "Freins : peur du retard, mauvaises expériences avec des couturières. Objection : C'est plus cher qu'au marché. » La réponse marketing à l'objection : délai garanti et essayage inclus."]}},
  {"titre": "Réécrire des propositions de valeur", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Ces trois phrases sont des propositions de valeur faibles. Explique ce qui ne va pas, puis réécris chacune avec le modèle : Pour [cible] qui [besoin], [marque] offre [bénéfice] grâce à [preuve].",
   "etapes": ["« Salon Belle, la qualité au meilleur prix. »", "« Nous sommes une ONG engagée pour un monde meilleur. »", "« JusPlus, des jus naturels pour tous. »"],
   "criteres": ["Chaque phrase réécrite nomme une cible précise.", "Le bénéfice est concret et vérifiable.", "Une personne extérieure comprend la phrase en 5 secondes."],
   "corrige": {"texte": ["Défauts communs : pas de cible, des mots vides (« qualité », « meilleur », « pour tous ») que tous les concurrents peuvent utiliser, aucune preuve.",
                          "Exemples de réponses : 1) « Pour les femmes actives de Calavi qui manquent de temps, Salon Belle réalise tes tresses sur rendez-vous WhatsApp, sans attente, avec un prix annoncé avant de commencer. » "
                          "2) « Pour les familles rurales du Zou, notre ONG installe des points d'eau potable gérés par un comité du village, avec un rapport public pour chaque donateur. » "
                          "3) « Pour les salariés de Cotonou qui veulent manger plus sain, JusPlus livre au bureau des jus pressés le matin même, sans sucre ajouté, payables par mobile money. »",
                          "Grille : cible précise (1 point), besoin réel (1 point), bénéfice concret (1 point), preuve ou élément différenciant (1 point), clarté (1 point). Vise 4 sur 5 au minimum."]}},
  {"titre": "Calculer un prix rentable", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Restaurant étudiant à Calavi (chiffres d'exemple). Par plat : ingrédients 650 FCFA, emballage 100 FCFA. Charges fixes mensuelles : 180 000 FCFA. Volume prévu : 1 200 plats par mois. "
                "Concurrents : 1 000 à 1 500 FCFA. Le gérant veut une marge minimale de 20 % sur le coût de revient.",
   "etapes": ["Calcule le coût variable par plat et la part de charges fixes par plat.", "Calcule le coût de revient et le prix plancher.",
              "Propose un prix de vente justifié par les trois repères.", "Calcule le bénéfice mensuel prévu et le nombre de plats à vendre pour couvrir les charges fixes (seuil de rentabilité)."],
   "criteres": ["Chaque calcul est posé ligne par ligne.", "Le prix proposé est au-dessus du plancher et cohérent avec la concurrence.", "Le seuil de rentabilité est correctement interprété."],
   "corrige": {"texte": ["Coût variable par plat : 650 + 100 = 750 FCFA. Part de charges fixes : 180 000 ÷ 1 200 = 150 FCFA. Coût de revient : 750 + 150 = 900 FCFA.",
                          "Prix plancher : 900 × 1,20 = 1 080 FCFA. Les concurrents sont entre 1 000 et 1 500 FCFA. Un prix de 1 200 FCFA est au-dessus du plancher, dans la fourchette basse du marché et cohérent avec une cible étudiante.",
                          "Bénéfice par plat : 1 200 − 900 = 300 FCFA. Bénéfice mensuel prévu : 300 × 1 200 = 360 000 FCFA (si les 1 200 plats sont vendus).",
                          "Seuil de rentabilité : chaque plat rapporte 1 200 − 750 = 450 FCFA pour couvrir les charges fixes. 180 000 ÷ 450 = 400 plats par mois. En dessous de 400 plats, le restaurant perd de l'argent ; au-dessus, il en gagne. "
                          "Attention : si le volume réel n'est que de 600 plats, la part de charges fixes passe à 300 FCFA et le coût de revient à 1 050 FCFA : la marge fond, d'où l'importance de prévoir un volume réaliste."]}},
  {"titre": "Le plan de communication d'un mois", "niveau": "Débutant", "duree": "45 min",
   "consigne": "Avec un budget d'exemple de 50 000 FCFA, construis le plan de communication du premier mois d'une boutique de jus naturels à Cotonou.",
   "etapes": ["Fixe un objectif chiffré et daté.", "Écris le message principal à partir de la proposition de valeur.",
              "Choisis 3 à 4 actions (canal, contenu, fréquence, coût).", "Répartis le budget et indique comment tu mesureras chaque action."],
   "criteres": ["L'objectif est mesurable.", "Le budget total est respecté.", "Chaque action a un indicateur."],
   "corrige": {"texte": ["Exemple de plan. Objectif : 150 bouteilles vendues en 4 semaines et 80 contacts WhatsApp enregistrés. Message : « Des jus pressés du jour, sans sucre ajouté, livrés au bureau à Cotonou. »",
                          "Actions : 1) Dégustation dans 2 entreprises de Ganhi : 15 000 FCFA (échantillons), mesure : contacts recueillis. 2) Statuts WhatsApp quotidiens (photo du jour, prix, comment commander) : 0 FCFA, mesure : messages reçus. "
                          "3) Publicité Facebook ciblée sur Cotonou, objectif messages : 25 000 FCFA, mesure : coût par conversation. 4) Carte de fidélité imprimée (la 10e bouteille offerte) : 10 000 FCFA, mesure : cartes revenues.",
                          "Total : 15 000 + 0 + 25 000 + 10 000 = 50 000 FCFA. Bilan en fin de mois : comparer les ventes et les contacts à l'objectif, garder l'action la moins chère par client obtenu."]}}]},
{
 "id": "res-cahier-marketing-digital", "fichier": "tobmaq-cahier-marketing-digital.pdf", "categorie": "marketing", "logiciels": ["metabusiness"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Responsable marketing digital", "sous_titre": "Marketing digital · 5 exercices et leurs corrigés",
 "titre_court": "Cahier d'exercices : marketing digital et publicité Meta",
 "desc": "5 exercices : objectifs SMART, calendrier éditorial, WhatsApp Business, calcul des indicateurs publicitaires et rapport mensuel, avec corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Responsable marketing digital ». Il te met dans la peau d'un responsable qui doit planifier, lancer et justifier ses actions avec des chiffres. "
          "Les résultats de campagne sont des exemples d'entraînement ; l'interface de Meta évolue souvent, concentre-toi sur la logique.",
 "exercices": [
  {"titre": "Des objectifs SMART", "niveau": "Intermédiaire", "duree": "20 min",
   "consigne": "Transforme ces objectifs vagues en objectifs SMART pour une boutique en ligne de cosmétiques naturels à Cotonou (qui reçoit aujourd'hui, en exemple, 30 commandes par mois).",
   "etapes": ["« Être plus visible sur Instagram. »", "« Vendre plus grâce à WhatsApp. »", "« Avoir une communauté engagée. »", "« Faire de la publicité. »"],
   "criteres": ["Chaque objectif est chiffré, daté et réaliste par rapport au point de départ.", "Chaque objectif est relié à un indicateur précis."],
   "corrige": {"texte": ["Exemples de réponses : 1) « Passer de 800 à 1 500 abonnés Instagram dans la zone Cotonou-Calavi d'ici le 30 juin, en publiant 4 fois par semaine. » "
                          "2) « Passer de 30 à 45 commandes par mois via WhatsApp d'ici fin mars. » 3) « Atteindre 50 commentaires ou réponses par semaine sur nos publications et statuts d'ici 3 mois. » "
                          "4) « Obtenir 100 conversations WhatsApp en 2 semaines avec une campagne Meta de 30 000 FCFA, soit au plus 300 FCFA par conversation. »",
                          "Point de vigilance : un objectif réaliste part des chiffres actuels. Passer de 30 à 300 commandes en un mois n'est pas crédible sans moyens supplémentaires."]}},
  {"titre": "Calendrier éditorial et WhatsApp Business", "niveau": "Intermédiaire", "duree": "1 h",
   "consigne": "Prépare deux semaines de publications pour la même boutique et la configuration de son WhatsApp Business.",
   "etapes": ["Dans Google Sheets : colonnes date, canal, format, type de contenu, thème, appel à l'action, responsable, statut.", "Au moins 8 publications sur 2 canaux, avec 4 types de contenus différents.",
              "Rédige le message d'accueil, le message d'absence et 5 réponses rapides avec leur raccourci.", "Propose 5 étiquettes pour classer les conversations."],
   "criteres": ["Pas plus de deux publications de vente directe sur quatre.", "Chaque publication a un appel à l'action.", "Les réponses rapides couvrent prix, livraison, paiement, délai et retours."],
   "corrige": {"texte": ["Exemple de semaine : lundi Instagram, carrousel conseil (« 3 erreurs avec le beurre de karité »), appel à l'action « Enregistre ce post » ; mercredi statut WhatsApp, coulisses de la fabrication ; "
                          "vendredi Instagram, avis cliente avec photo (avec son accord) ; samedi statut WhatsApp, offre du week-end, « Réponds OFFRE pour commander ».",
                          "Message d'accueil : « Bonjour et bienvenue chez Naturelle ! Consulte notre catalogue ou dis-nous ce que tu cherches, nous répondons de 8 h à 20 h. » "
                          "Réponses rapides : /prix (renvoi au catalogue), /livraison (zones, délais et tarifs), /paiement (mobile money ou à la livraison), /delai (préparation sous 24 h), /retour (conditions d'échange).",
                          "Étiquettes : Nouveau contact, Commande en cours, Payé, Livré, À relancer. Les listes de diffusion ne touchent que les personnes qui ont enregistré ton numéro."]}},
  {"titre": "Comparer deux campagnes Meta", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Deux campagnes d'exemple, même budget de 15 000 FCFA, objectif messages, produit vendu 8 000 FCFA avec une marge brute de 3 000 FCFA par vente. "
                "Campagne A : 25 000 impressions, 300 clics, 50 conversations, 10 ventes. Campagne B : 40 000 impressions, 320 clics, 30 conversations, 6 ventes.",
   "etapes": ["Calcule pour chacune : CTR, CPC, coût par conversation, coût par vente, chiffre d'affaires, ROAS.", "Calcule le bénéfice après publicité.", "Décide quelle campagne garder et propose une amélioration pour l'autre."],
   "criteres": ["Les formules sont écrites avant les résultats.", "La décision s'appuie sur le coût par vente et le bénéfice, pas sur les impressions."],
   "corrige": {"texte": ["Formules : CTR = clics ÷ impressions × 100 ; CPC = dépense ÷ clics ; coût par conversation = dépense ÷ conversations ; coût par vente = dépense ÷ ventes ; ROAS = chiffre d'affaires ÷ dépense.",
                          "Campagne A : CTR = 300 ÷ 25 000 × 100 = 1,2 %. CPC = 15 000 ÷ 300 = 50 FCFA. Coût par conversation = 15 000 ÷ 50 = 300 FCFA. Coût par vente = 15 000 ÷ 10 = 1 500 FCFA. "
                          "Chiffre d'affaires = 10 × 8 000 = 80 000 FCFA. ROAS = 80 000 ÷ 15 000 ≈ 5,3. Bénéfice = 10 × 3 000 − 15 000 = 15 000 FCFA.",
                          "Campagne B : CTR = 320 ÷ 40 000 × 100 = 0,8 %. CPC = 15 000 ÷ 320 ≈ 46,9 FCFA. Coût par conversation = 15 000 ÷ 30 = 500 FCFA. Coût par vente = 15 000 ÷ 6 = 2 500 FCFA. "
                          "Chiffre d'affaires = 6 × 8 000 = 48 000 FCFA. ROAS = 48 000 ÷ 15 000 = 3,2. Bénéfice = 6 × 3 000 − 15 000 = 3 000 FCFA.",
                          "Décision : garder A. B touche plus de monde et a un CPC légèrement plus bas, mais ses clics se transforment moins en conversations et en ventes. "
                          "Piste pour B : resserrer l'audience ou reprendre le visuel de A. Retiens aussi qu'un ROAS de 3,2 n'est pas forcément rentable : tout dépend de la marge."]}},
  {"titre": "Concevoir un test A/B", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Un collègue propose trois tests. Dis pour chacun s'il est valable et pourquoi, puis conçois un test correct pour une boutique de pagnes.",
   "etapes": ["Test 1 : version A photo de tissu plié, texte court ; version B vidéo de la tenue portée, texte long, autre audience.",
              "Test 2 : version A et version B identiques sauf le visuel, budget égal, 7 jours.",
              "Test 3 : version A diffusée 2 jours, version B diffusée la semaine suivante pendant les fêtes."],
   "criteres": ["Les trois verdicts sont justifiés.", "Le test proposé ne fait varier qu'un seul élément.", "La durée, le budget et l'indicateur de décision sont indiqués."],
   "corrige": {"texte": ["Test 1 : non valable, trois éléments changent (format, texte, audience) ; impossible de savoir ce qui explique l'écart. Test 2 : valable, une seule variable, budget égal, durée suffisante. "
                          "Test 3 : non valable, les périodes sont différentes (les fêtes modifient le comportement d'achat) et 2 jours sont trop courts.",
                          "Test proposé : même audience (femmes 25-45 ans, Cotonou et Calavi), même texte, même budget de 2 500 FCFA par jour chacune pendant 7 jours, en même temps. "
                          "Variable : visuel A (tissu plié) contre visuel B (tenue portée). Indicateur de décision : coût par conversation WhatsApp, puis confirmation par les ventes."]}},
  {"titre": "Le rapport mensuel", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Chiffres d'exemple du mois : portée Facebook 18 000 (mois précédent 12 000), messages WhatsApp 140 (110), commandes 38 (35), dépense publicitaire 40 000 FCFA, chiffre d'affaires lié 190 000 FCFA. "
                "Rédige un rapport d'une page pour la gérante : résultats, analyse, 3 recommandations.",
   "criteres": ["Les évolutions sont calculées en pourcentage.", "Le rapport distingue ce qui progresse de ce qui stagne.", "Les recommandations sont concrètes et mesurables."],
   "corrige": {"texte": ["Évolutions : portée +50 % ((18 000 − 12 000) ÷ 12 000), messages +27 % environ ((140 − 110) ÷ 110), commandes +9 % environ ((38 − 35) ÷ 35). "
                          "Taux de transformation des messages en commandes : 35 ÷ 110 ≈ 32 % le mois précédent, 38 ÷ 140 ≈ 27 % ce mois-ci. ROAS : 190 000 ÷ 40 000 = 4,75.",
                          "Analyse : la visibilité et les contacts progressent bien, mais une part plus faible des conversations aboutit à une commande. Le problème se situe probablement dans la conversation (délai de réponse, prix, livraison), pas dans la publicité.",
                          "Recommandations : 1) Répondre en moins de 15 minutes aux heures de pointe, mesuré par un relevé sur une semaine. 2) Relancer sous 48 h les contacts étiquetés « À relancer ». "
                          "3) Ajouter les frais de livraison dans le catalogue pour éviter les abandons. Objectif du mois suivant : revenir à au moins 32 % de transformation."]}}]},
{
 "id": "res-cahier-redaction", "fichier": "tobmaq-cahier-redaction-web.pdf", "categorie": "marketing", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Rédacteur web", "sous_titre": "Rédaction web · 5 exercices et leurs corrigés",
 "titre_court": "Cahier d'exercices : rédaction web et SEO",
 "desc": "5 exercices pour écrire clair et court puis rédiger pour Google : réécriture, titres, intention de recherche, title, méta-description et plan Hn.",
 "intro": "Ce cahier accompagne la formation « Rédacteur web ». Un traitement de texte comme Google Docs et un navigateur suffisent. "
          "Les longueurs indiquées pour la balise title et la méta-description sont des repères : Google peut couper ou réécrire selon l'écran.",
 "exercices": [
  {"titre": "Réécrire un texte trop long", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Réécris ce texte pour une page web en moins de 45 mots, avec la pyramide inversée, une phrase d'appel à l'action et des phrases courtes : "
                "« Depuis de nombreuses années, notre pâtisserie familiale, qui a été fondée par notre grand-mère avec beaucoup d'amour et de passion, met tout en œuvre afin de proposer à sa fidèle clientèle "
                "des gâteaux de qualité, et nous avons aujourd'hui l'immense plaisir de vous annoncer qu'il est désormais possible de passer commande de gâteaux d'anniversaire, qui seront livrés à Cotonou. »",
   "criteres": ["L'information principale est dans la première phrase.", "Moins de 45 mots.", "Un appel à l'action avec un moyen de contact."],
   "corrige": {"texte": ["Exemple de réponse : « Commande ton gâteau d'anniversaire, livré à Cotonou. Choisis parmi nos recettes familiales, indique la date et le nombre d'invités, nous livrons à l'heure. "
                          "Écris-nous sur WhatsApp au 01 00 00 00 00. Paiement par mobile money ou à la livraison. » (environ 40 mots)",
                          "Ce qui a changé : l'information utile (gâteaux d'anniversaire livrés à Cotonou) passe en premier ; l'histoire de la famille est réduite à « recettes familiales » ; "
                          "la phrase unique d'environ 60 mots devient 4 phrases courtes ; les formules creuses (« met tout en œuvre », « immense plaisir ») disparaissent ; un appel à l'action est ajouté."]}},
  {"titre": "Des titres qui informent", "niveau": "Débutant", "duree": "15 min",
   "consigne": "Réécris ces 5 titres vagues pour qu'ils annoncent un bénéfice ou une réponse précise.",
   "etapes": ["« Nos services » (agence de nettoyage à Cotonou)", "« Actualités » (ONG d'éducation à Porto-Novo)", "« Découvrez notre offre » (forfait internet pour PME)",
              "« À propos » (start-up de livraison à Calavi)", "« Conseils » (blog d'une pharmacie)"],
   "criteres": ["Chaque titre dit concrètement ce que le lecteur va trouver.", "Pas plus d'environ 10 mots par titre."],
   "corrige": {"texte": ["Exemples : 1) « Nettoyage de bureaux à Cotonou, le soir ou le week-end ». 2) « 120 enfants inscrits au soutien scolaire cette année » (avec le chiffre réel de l'ONG). "
                          "3) « Internet illimité pour ta PME, installé en 48 h ». 4) « Qui nous sommes : des livreurs de Calavi formés et assurés ». 5) « Paludisme : 5 gestes pour protéger ta famille ».",
                          "Grille : le titre est précis (2 points), annonce un bénéfice ou une réponse (2 points), reste court (1 point)."]}},
  {"titre": "Mots-clés et intention de recherche", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Classe ces 8 requêtes selon l'intention (s'informer, trouver un site précis, comparer, acheter), puis indique le type de page le plus adapté pour chacune.",
   "etapes": ["comment conserver le gari", "boutique Awa Dantokpa", "meilleur forfait internet Bénin", "commander gâteau anniversaire Cotonou",
              "prix moto neuve Cotonou", "recette sauce arachide", "pharmacie de garde Calavi", "formation marketing digital en ligne avis"],
   "criteres": ["Au moins 6 bonnes réponses sur 8.", "Le type de page est cohérent avec l'intention."],
   "corrige": {"texte": ["S'informer : « comment conserver le gari » et « recette sauce arachide » (article ou guide). Trouver un site ou un lieu précis : « boutique Awa Dantokpa » (page d'accueil ou fiche Google de la boutique), "
                          "« pharmacie de garde Calavi » (page d'informations pratiques à jour). Comparer : « meilleur forfait internet Bénin », « prix moto neuve Cotonou », « formation marketing digital en ligne avis » "
                          "(comparatif, page de tarifs, avis). Acheter : « commander gâteau anniversaire Cotonou » (page de commande avec prix et contact).",
                          "Certaines requêtes sont mixtes : « prix moto neuve Cotonou » peut aussi être proche de l'achat. Regarde les premiers résultats de Google pour trancher."]}},
  {"titre": "Balise title et méta-description", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Pour la page de commande d'une pâtisserie de Cotonou (mot-clé : « gâteau anniversaire Cotonou »), critique le title proposé, puis rédige un title et une méta-description. Compte les caractères.",
   "etapes": ["Title proposé : « Bienvenue sur le site officiel de notre magnifique pâtisserie familiale située à Cotonou au Bénin ».",
              "Repères indicatifs : title d'environ 50 à 60 caractères, méta-description d'environ 120 à 160 caractères."],
   "criteres": ["Le mot-clé principal apparaît au début du title.", "Les longueurs sont dans les repères.", "La méta-description se termine par une incitation."],
   "corrige": {"texte": ["Critique : le title proposé fait 97 caractères, il sera coupé ; il commence par « Bienvenue », qui n'apporte rien, et ne contient pas le mot-clé « gâteau anniversaire ».",
                          "Title possible (60 caractères) : « Gâteau d'anniversaire à Cotonou livré en 24 h | Délices Mado ».",
                          "Méta-description possible (128 caractères) : « Commande ton gâteau d'anniversaire à Cotonou : 20 parfums, livraison en 24 h, paiement mobile money. Devis gratuit sur WhatsApp. »",
                          "Les promesses (20 parfums, 24 h) doivent être vraies pour l'entreprise : une méta-description trompeuse fait fuir le visiteur dès qu'il arrive sur la page."]}},
  {"titre": "Corriger un plan de page", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Ce plan de page pour un salon de coiffure de Calavi contient 5 erreurs de structure ou de SEO. Repère-les, puis propose un plan corrigé.",
   "code": "H1 : Bienvenue\nH1 : Salon de coiffure tresses Calavi tresses pas cher tresses\nH3 : Nos prestations\nH2 : Nos tarifs\nImage : IMG_2045.jpg (pas de texte alternatif)\nLien : « cliquez ici » vers la page Réservation",
   "criteres": ["Les 5 erreurs sont trouvées et expliquées.", "Le plan corrigé a un seul H1 et des niveaux sans saut.", "Le lien et l'image sont corrigés."],
   "corrige": {"texte": ["Erreurs : 1) Deux H1. 2) Bourrage de mots-clés dans le second H1. 3) Saut de niveau : un H3 apparaît avant tout H2. 4) Image sans texte alternatif et nom de fichier non parlant. "
                          "5) Texte de lien « cliquez ici » qui n'indique pas la destination."],
               "code": "H1 : Salon de coiffure à Calavi : tresses, nattes et tissages\nH2 : Nos prestations\n  H3 : Tresses et nattes\n  H3 : Tissages et perruques\nH2 : Nos tarifs\nH2 : Questions fréquentes\nImage : tresses-longues-salon-calavi.jpg\n  alt : « Tresses longues réalisées au salon Belle Tête »\nLien : « Réserve ton rendez-vous en ligne » vers la page Réservation"}}]},
{
 "id": "res-cahier-projet", "fichier": "tobmaq-cahier-chef-de-projet.pdf", "categorie": "marketing", "logiciels": ["trello"], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Chef de projet digital", "sous_titre": "Gestion de projet · 5 exercices et leurs corrigés",
 "titre_court": "Cahier d'exercices : cadrer et piloter un projet digital",
 "desc": "5 exercices, du cadrage au suivi prévu / réel : questions client, priorisation MoSCoW, budget avec réserve, tableau Trello et recette, avec corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Chef de projet digital ». Il suit un projet fil rouge : le site de commande en ligne d'un restaurant de Cotonou. "
          "Les montants et les taux journaliers sont des exemples d'entraînement, à adapter au marché et à ton équipe.",
 "exercices": [
  {"titre": "Reformuler le besoin", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "La gérante du restaurant t'écrit : « Il nous faut une application comme les grandes marques, vite, et pas trop chère. » Rédige 10 questions de cadrage, puis une reformulation du besoin en 5 lignes à lui renvoyer pour validation.",
   "criteres": ["Les questions portent sur le problème, les utilisateurs, les objectifs, le budget et le délai.", "La reformulation ne présuppose pas la solution technique."],
   "corrige": {"texte": ["Questions utiles : Quel problème voulez-vous résoudre ? Comment les clients commandent-ils aujourd'hui ? Combien de commandes par jour, et combien en voulez-vous ? "
                          "Qui recevra et préparera les commandes en ligne ? Quels moyens de paiement ? Qui livre et dans quelle zone ? Quel budget pour la création et pour l'entretien chaque année ? "
                          "Pour quelle date et pourquoi cette date ? Qui décide et valide ? Qui mettra à jour le menu et les prix ?",
                          "Reformulation possible : « Vous souhaitez que vos clients de Cotonou puissent commander et payer en ligne sans appeler, pour réduire les erreurs de commande et augmenter les ventes à emporter. "
                          "Les commandes doivent arriver dans la cuisine et sur WhatsApp. Le menu doit être modifiable par votre équipe. Le lancement est visé avant la rentrée. "
                          "Une application mobile n'est peut-être pas nécessaire au départ : un site adapté au téléphone peut suffire. »"]}},
  {"titre": "Prioriser le périmètre avec MoSCoW", "niveau": "Intermédiaire", "duree": "20 min",
   "consigne": "Classe ces 10 fonctionnalités en Must, Should, Could, Won't pour une première version livrée en 8 semaines, et justifie deux choix difficiles.",
   "etapes": ["Menu avec photos et prix", "Panier et commande", "Paiement mobile money", "Paiement à la livraison", "Suivi de commande en temps réel sur carte",
              "Programme de fidélité à points", "Notification WhatsApp au restaurant", "Application mobile Android et iOS", "Espace d'administration du menu", "Avis clients"],
   "criteres": ["Les Must permettent à eux seuls de commander et d'être servi.", "Au moins une fonctionnalité est en Won't.", "Les justifications citent le délai, le budget ou la valeur pour le client."],
   "corrige": {"texte": ["Proposition : Must : menu avec photos et prix, panier et commande, paiement à la livraison, notification WhatsApp au restaurant, espace d'administration du menu. "
                          "Should : paiement mobile money. Could : avis clients, programme de fidélité. Won't (cette version) : suivi en temps réel sur carte, application mobile Android et iOS.",
                          "Justifications : le paiement mobile money est très attendu mais dépend de l'ouverture d'un compte marchand et de délais externes ; le paiement à la livraison permet de lancer sans attendre. "
                          "L'application mobile doublerait le travail et le budget ; un site adapté au téléphone répond au besoin de la première version. D'autres classements sont acceptables s'ils sont justifiés."]}},
  {"titre": "Budget avec réserve", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Calcule le budget du projet à partir de ces estimations d'exemple : design 3 jours à 25 000 FCFA, développement 15 jours à 30 000 FCFA, rédaction des contenus 4 jours à 20 000 FCFA, "
                "gestion de projet 6 jours à 25 000 FCFA, tests 3 jours à 20 000 FCFA, domaine et hébergement 54 000 FCFA pour un an. Ajoute une réserve de 15 % sur le total.",
   "criteres": ["Chaque ligne est calculée séparément.", "La réserve est calculée sur le total hors réserve.", "Les frais récurrents sont signalés à part."],
   "corrige": {"texte": ["Design : 3 × 25 000 = 75 000. Développement : 15 × 30 000 = 450 000. Rédaction : 4 × 20 000 = 80 000. Gestion de projet : 6 × 25 000 = 150 000. Tests : 3 × 20 000 = 60 000. "
                          "Domaine et hébergement : 54 000.",
                          "Total hors réserve : 75 000 + 450 000 + 80 000 + 150 000 + 60 000 + 54 000 = 869 000 FCFA. Réserve de 15 % : 869 000 × 0,15 = 130 350 FCFA. Budget total : 869 000 + 130 350 = 999 350 FCFA.",
                          "À présenter au client : la création (815 000 FCFA hors réserve) est payée une fois ; le domaine et l'hébergement (54 000 FCFA) reviennent chaque année. "
                          "La réserve n'est pas un bénéfice caché : elle sert aux imprévus et son usage est expliqué au client."]}},
  {"titre": "Tableau Trello et sprints", "niveau": "Intermédiaire", "duree": "1 h",
   "consigne": "Crée dans Trello le tableau du projet et organise la réalisation en 3 sprints de deux semaines.",
   "etapes": ["Colonnes : Carnet, À faire, En cours, À vérifier, Terminé.", "Au moins 15 cartes avec responsable, échéance, liste de contrôle et étiquette.",
              "Répartis les cartes dans 3 sprints avec un objectif par sprint.", "Ajoute un tableau de 4 risques : probabilité, impact, action."],
   "criteres": ["Chaque carte est assez petite pour être finie en 1 à 2 jours.", "Chaque sprint se termine par quelque chose de montrable au client.", "Chaque risque a une action concrète et un responsable."],
   "corrige": {"texte": ["Exemple de découpage. Sprint 1 (objectif : maquettes validées et menu en ligne) : maquette accueil, maquette page menu, charte couleurs, installation du site, saisie de 20 plats avec photos. "
                          "Sprint 2 (objectif : commande de bout en bout) : panier, formulaire de commande, notification WhatsApp, paiement à la livraison, espace d'administration. "
                          "Sprint 3 (objectif : prêt à lancer) : paiement mobile money, pages Contact et Livraison, tests sur téléphone, corrections, formation de l'équipe.",
                          "Risques : contenus (photos, prix) fournis en retard par le client, probabilité forte, action : liste des contenus avec date limite dès le cadrage. "
                          "Compte marchand mobile money non validé à temps, probabilité moyenne, action : lancer avec paiement à la livraison. Indisponibilité du développeur, action : code et accès documentés. "
                          "Connexion lente des clients, action : images compressées et pages légères."]}},
  {"titre": "Suivi prévu / réel et recette", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Fin de la semaine 4 sur 8 (chiffres d'exemple). Budget de réalisation : 800 000 FCFA. Le carnet compte 40 cartes. Prévu à mi-parcours : 20 cartes terminées et 400 000 FCFA dépensés. "
                "Réel : 14 cartes terminées et 480 000 FCFA dépensés. Analyse la situation, propose une décision, puis rédige 5 cas de test pour la commande en ligne.",
   "etapes": ["Calcule l'avancement réel et la consommation du budget en pourcentage.", "Estime la date de fin et le coût final si le rythme reste le même.",
              "Propose deux options au commanditaire et ta recommandation.", "Cas de test : étape, résultat attendu, résultat obtenu, conforme ou non."],
   "criteres": ["Les calculs sont justes et expliqués.", "Les options sont chiffrées.", "Les cas de test couvrent au moins un cas d'erreur."],
   "corrige": {"texte": ["Avancement : 14 ÷ 40 = 35 % (prévu 50 %). Budget consommé : 480 000 ÷ 800 000 = 60 % (prévu 50 %). Le projet est en retard et coûte plus cher que prévu : signal d'alerte.",
                          "Rythme : 14 cartes en 4 semaines = 3,5 cartes par semaine. Il reste 26 cartes : 26 ÷ 3,5 ≈ 7,4 semaines, soit une fin vers la semaine 11 ou 12 au lieu de 8. "
                          "Coût : 480 000 ÷ 14 ≈ 34 300 FCFA par carte ; 40 cartes × 34 300 ≈ 1 372 000 FCFA, soit environ 570 000 FCFA de dépassement si rien ne change.",
                          "Option 1 : réduire le périmètre en reportant les Could et une partie des Should (par exemple 8 cartes) pour tenir la date et limiter le dépassement. "
                          "Option 2 : garder tout le périmètre, décaler la mise en ligne d'environ 4 semaines et augmenter le budget. Recommandation : option 1, car le restaurant a besoin d'être en ligne avant la rentrée ; "
                          "à décider avec la gérante cette semaine, pas à la fin du projet.",
                          "Cas de test d'exemple : 1) Ajouter 2 plats au panier : le total est juste. 2) Valider une commande avec paiement à la livraison : confirmation affichée et message WhatsApp reçu par le restaurant. "
                          "3) Envoyer le formulaire sans numéro de téléphone : message d'erreur clair, commande bloquée. 4) Modifier un prix dans l'administration : nouveau prix visible sur le site. "
                          "5) Passer une commande sur un téléphone d'entrée de gamme en connexion lente : la page reste utilisable."]}}]},
]

CAHIERS_D = [
{
 "id": "res-cahier-ecommerce", "fichier": "tobmaq-cahier-ecommerce.pdf", "categorie": "business", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · E-commerce : vendre en ligne", "sous_titre": "E-commerce · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : e-commerce et vente en ligne",
 "desc": "5 exercices progressifs, de la fiche produit au service après-vente, avec calcul du prix, de la livraison, du panier moyen et du taux de conversion, et corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « E-commerce : vendre en ligne ». Il te suffit d'un téléphone, d'un tableur et d'un carnet. "
          "Tous les chiffres sont des exemples d'entraînement : remplace-les par tes vrais coûts, tes vrais tarifs de livraison et les frais réels de ton opérateur.",
 "exercices": [
  {"titre": "Réécrire trois fiches produits", "niveau": "Débutant", "duree": "35 min",
   "consigne": "Une vendeuse de Cotonou publie ces trois annonces sur son catalogue WhatsApp Business. Explique ce qui ne va pas, puis réécris chaque fiche complète.",
   "etapes": ["Annonce 1 : « Beau pagne dispo, prix en privé. » (une seule photo sombre)",
              "Annonce 2 : « Sac top qualité !!! Livraison partout. »",
              "Annonce 3 : « Huile de coco 100 % naturelle, 3 500. »",
              "Pour chaque fiche : titre, description (matière, dimensions ou contenance, usage, entretien), prix en FCFA, délai et zone de livraison, liste des photos à prendre."],
   "criteres": ["Chaque titre indique le type de produit et une caractéristique clé.", "Le prix est affiché en FCFA, sans « prix en privé ».",
                "Le délai et la zone de livraison sont précisés.", "Au moins 3 photos différentes sont prévues par produit."],
   "corrige": {"texte": ["Défauts communs : prix caché (annonce 1), mots vagues sans information vérifiable (« top qualité », « partout »), aucune dimension ni contenance, livraison non précisée, photo unique et sombre. "
                          "Le client doit poser plusieurs questions avant de savoir s'il veut acheter : beaucoup abandonnent.",
                          "Exemple de réponse 1 : « Pagne wax 6 yards, motif fleurs jaunes et bleues, 100 % coton. » Description : environ 6 yards, idéal pour une tenue de cérémonie, lavage à la main à l'eau froide. "
                          "Prix d'exemple : 7 500 FCFA. Livraison à Cotonou en 24 h, 1 000 FCFA. Photos : pagne plié, motif en gros plan, pagne déplié sur un fond blanc, tenue portée.",
                          "Exemple de réponse 2 : « Sac à main en pagne wax doublé, fermeture éclair, 30 x 25 cm. » Description : doublure intérieure, une poche zippée, anse renforcée. Prix d'exemple : 9 000 FCFA. "
                          "Livraison : Cotonou et Calavi en 24 à 48 h selon la zone, tarifs affichés ; autres villes sur demande avec acompte. Photos : face, intérieur, détail de la couture, sac porté à l'épaule.",
                          "Exemple de réponse 3 : « Huile de coco vierge, flacon de 250 ml. » Description : usage cheveux et peau, conserver à l'abri du soleil, se solidifie au frais (c'est normal). Prix d'exemple : 3 500 FCFA. "
                          "Livraison à Cotonou en 24 h. Photos : flacon de face, étiquette lisible, texture, flacon à côté d'un objet pour l'échelle.",
                          "Grille sur 10 : titre clair (2), description complète (2), prix affiché (2), livraison précisée (2), photos prévues (2). Vise au moins 8 sur 10."]}},
  {"titre": "Coût de revient et prix de vente", "niveau": "Débutant", "duree": "35 min",
   "consigne": "Tu vends des sacs en pagne fabriqués par une couturière (chiffres d'exemple). Par sac : tissu 2 000 FCFA, fermeture et doublure 800 FCFA, couture 1 500 FCFA, emballage 200 FCFA. "
                "Charges fixes mensuelles : internet 15 000 FCFA, publicité 50 000 FCFA, déplacements 25 000 FCFA. Volume prévu : 60 sacs par mois. Les concurrents vendent entre 8 000 et 12 000 FCFA. Tu vises un taux de marge de 50 % sur le coût de revient.",
   "etapes": ["Calcule le coût variable par sac et la part de charges fixes par sac.", "Calcule le coût de revient et le prix de vente correspondant au taux de marge visé.",
              "Vérifie que ce prix est cohérent avec la concurrence.", "Calcule le bénéfice mensuel prévu et le seuil de rentabilité en nombre de sacs."],
   "criteres": ["Chaque calcul est posé ligne par ligne avec ses unités.", "Le prix tient compte de toutes les charges.", "Le seuil de rentabilité est correctement interprété."],
   "corrige": {"texte": ["Coût variable par sac : 2 000 + 800 + 1 500 + 200 = 4 500 FCFA. Charges fixes mensuelles : 15 000 + 50 000 + 25 000 = 90 000 FCFA. Part de charges fixes par sac : 90 000 ÷ 60 = 1 500 FCFA.",
                          "Coût de revient : 4 500 + 1 500 = 6 000 FCFA. Prix avec 50 % de marge : 6 000 × 1,50 = 9 000 FCFA. Marge par sac : 9 000 − 6 000 = 3 000 FCFA. "
                          "Le prix de 9 000 FCFA se situe dans la fourchette des concurrents (8 000 à 12 000 FCFA), plutôt dans le bas : il est crédible et laisse de la place pour une version plus haut de gamme.",
                          "Bénéfice mensuel prévu : 3 000 × 60 = 180 000 FCFA, si les 60 sacs sont vendus.",
                          "Seuil de rentabilité : chaque sac rapporte 9 000 − 4 500 = 4 500 FCFA pour couvrir les charges fixes. 90 000 ÷ 4 500 = 20 sacs par mois. "
                          "En dessous de 20 sacs, l'activité perd de l'argent ; au-delà, chaque sac supplémentaire rapporte 4 500 FCFA de bénéfice. Contrôle : 60 sacs donnent (60 − 20) × 4 500 = 180 000 FCFA, on retrouve le bénéfice calculé.",
                          "Erreur fréquente : oublier la publicité ou les déplacements dans le calcul. Sans les charges fixes, le vendeur croirait gagner 4 500 FCFA par sac au lieu de 3 000 FCFA."]}},
  {"titre": "Livraison, frais de paiement et colis refusés", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Reprends le sac vendu 9 000 FCFA avec une marge de 3 000 FCFA. Tarifs d'exemple de ton livreur à zémidjan : zone A (Cotonou centre) 1 000 FCFA, zone B (Akpakpa, Godomey) 1 500 FCFA, zone C (Calavi, Porto-Novo) 2 500 FCFA. "
                "Pour l'exercice, on suppose des frais de paiement Mobile Money de 1 % à ta charge (vérifie les frais réels auprès de ton opérateur). Le mois dernier, sur 40 commandes payables à la livraison, 4 colis ont été refusés ; chaque refus t'a coûté 2 000 FCFA (aller et retour du livreur).",
   "etapes": ["Calcule la marge restante si tu offres la livraison dans chaque zone, avec paiement Mobile Money.", "Calcule le coût total des refus et leur coût moyen par commande livrée.",
              "Propose une politique de livraison et de paiement rentable.", "Rédige le message qui présente cette politique au client."],
   "criteres": ["Les frais de paiement sont calculés sur le prix de vente.", "La politique proposée garde une marge positive dans toutes les zones.", "Le message au client est clair et poli."],
   "corrige": {"texte": ["Frais de paiement : 9 000 × 1 % = 90 FCFA. Marge avec livraison offerte : zone A : 3 000 − 1 000 − 90 = 1 910 FCFA ; zone B : 3 000 − 1 500 − 90 = 1 410 FCFA ; zone C : 3 000 − 2 500 − 90 = 410 FCFA. "
                          "Offrir la livraison en zone C ne laisse presque rien : un seul imprévu suffit à rendre la vente déficitaire.",
                          "Refus : 4 × 2 000 = 8 000 FCFA perdus. Commandes réellement livrées : 40 − 4 = 36. Coût moyen par commande livrée : 8 000 ÷ 36 ≈ 222 FCFA. Taux de refus : 4 ÷ 40 × 100 = 10 %.",
                          "Exemple de politique : livraison payée par le client selon la zone (tarifs affichés) ; livraison offerte en zone A à partir de 15 000 FCFA d'achat ; paiement à la livraison accepté en zones A et B ; "
                          "en zone C et pour les nouveaux clients, acompte du montant de la livraison par Mobile Money avant l'envoi. Ainsi, un refus ne te coûte plus rien en zone C.",
                          "Exemple de message : « Bonjour ! Livraison en 24 h : 1 000 FCFA à Cotonou centre, 1 500 FCFA à Akpakpa et Godomey, 2 500 FCFA à Calavi et Porto-Novo. Offerte à Cotonou centre dès 15 000 FCFA d'achat. "
                          "Pour Calavi et Porto-Novo, nous demandons le paiement de la livraison par Mobile Money à la commande. Merci de ta confiance ! »",
                          "Grille : calculs justes (4 points), politique rentable dans toutes les zones (3 points), message clair (3 points)."]}},
  {"titre": "Panier moyen et taux de conversion", "niveau": "Intermédiaire", "duree": "35 min",
   "consigne": "Données d'exemple d'une boutique en ligne de pagnes. Mois 1 : 250 conversations WhatsApp, 35 commandes, chiffre d'affaires 420 000 FCFA. "
                "Au mois 2, la boutique ajoute une offre « pagne + foulard assorti », des réponses rapides sur les tailles et une relance des clients indécis. Mois 2 : 300 conversations, 48 commandes, chiffre d'affaires 624 000 FCFA.",
   "etapes": ["Calcule le taux de conversion et le panier moyen des deux mois.", "Calcule l'évolution du chiffre d'affaires en pourcentage.",
              "Explique quelle action a probablement agi sur quel indicateur.", "Fixe un objectif chiffré pour le mois 3 et calcule le chiffre d'affaires visé."],
   "criteres": ["Les formules sont écrites avant les résultats.", "Chaque action est reliée à l'indicateur qu'elle influence.", "L'objectif du mois 3 est réaliste par rapport au mois 2."],
   "corrige": {"texte": ["Formules : taux de conversion = commandes ÷ conversations × 100 ; panier moyen = chiffre d'affaires ÷ commandes.",
                          "Mois 1 : conversion = 35 ÷ 250 × 100 = 14 % ; panier moyen = 420 000 ÷ 35 = 12 000 FCFA. Mois 2 : conversion = 48 ÷ 300 × 100 = 16 % ; panier moyen = 624 000 ÷ 48 = 13 000 FCFA.",
                          "Évolution du chiffre d'affaires : (624 000 − 420 000) ÷ 420 000 × 100 ≈ 48,6 %. Trois leviers ont joué en même temps : plus de conversations (+50), meilleure conversion (+2 points) et panier moyen plus élevé (+1 000 FCFA).",
                          "Lien actions et indicateurs : l'offre pagne + foulard agit sur le panier moyen ; les réponses rapides sur les tailles et la relance des indécis agissent sur le taux de conversion. "
                          "La hausse des conversations peut venir de la publicité, du bouche-à-oreille ou de la saison : il faudrait le vérifier.",
                          "Exemple d'objectif pour le mois 3 : garder 300 conversations, atteindre 18 % de conversion et 13 000 FCFA de panier moyen. Commandes visées : 300 × 18 % = 54. "
                          "Chiffre d'affaires visé : 54 × 13 000 = 702 000 FCFA. Un objectif à 40 % de conversion ne serait pas réaliste sans changement majeur."]}},
  {"titre": "Avis clients, service après-vente et retours", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Rédige la politique de service après-vente de ta boutique en ligne, puis réponds par écrit aux trois situations suivantes.",
   "etapes": ["Politique en 5 à 7 lignes : délai pour signaler un problème, cas acceptés, cas refusés, qui paie le retour, échange, avoir ou remboursement.",
              "Situation 1 : une cliente reçoit un pagne d'une autre couleur que celle commandée.",
              "Situation 2 : un client publie en commentaire « Livraison en retard, je ne recommande pas ! ».",
              "Situation 3 : une cliente veut rendre une robe portée pour une cérémonie, sans défaut, 10 jours après la livraison.",
              "Rédige aussi le message envoyé après chaque livraison pour demander un avis."],
   "criteres": ["La politique est claire, courte et visible avant l'achat.", "Les réponses restent calmes, polies et proposent une solution.",
                "Les décisions respectent la politique annoncée.", "La demande d'avis est courte et demande l'accord pour une éventuelle photo."],
   "corrige": {"texte": ["Exemple de politique : « Tu as 48 h après réception pour signaler un problème avec photo. Nous échangeons ou remboursons en cas d'erreur de notre part ou de défaut. "
                          "En cas d'erreur de notre part, le retour est à notre charge. Un changement d'avis est accepté sous 48 h si l'article n'a pas été porté ni lavé, retour à ta charge, sous forme d'échange ou d'avoir. "
                          "Les articles sur mesure, portés ou lavés ne sont ni repris ni échangés, sauf défaut. »",
                          "Situation 1 (erreur du vendeur) : s'excuser, envoyer le bon pagne à tes frais et récupérer l'autre au même passage du livreur. Exemple : « Bonjour, toutes nos excuses pour cette erreur. "
                          "Notre livreur t'apporte le bon pagne demain et récupère l'autre, sans frais pour toi. »",
                          "Situation 2 (avis public négatif) : répondre publiquement, brièvement, sans se justifier longuement, puis continuer en privé. Exemple : « Bonjour, tu as raison, ta commande est arrivée avec un jour de retard "
                          "et nous en sommes désolés. Nous t'écrivons en privé pour trouver une solution. » Une petite compensation (livraison offerte sur la prochaine commande) peut être proposée.",
                          "Situation 3 : la demande sort de la politique (article porté, délai de 48 h dépassé). Refuser poliment en citant la règle : « Nous comprenons ta demande, mais comme indiqué dans nos conditions, "
                          "les articles portés ne peuvent pas être repris. Nous serons ravis de t'aider pour ta prochaine tenue. »",
                          "Demande d'avis : « Merci pour ta commande ! As-tu bien reçu ton article ? Ton avis en une phrase nous aide beaucoup. Si tu es d'accord, envoie-nous aussi une photo : nous la partagerons seulement avec ta permission. »",
                          "Grille sur 10 : politique complète (3), trois réponses polies et cohérentes (2 chacune, soit 6), demande d'avis (1)."]}}]},
{
 "id": "res-cahier-freelance", "fichier": "tobmaq-cahier-freelance.pdf", "categorie": "business", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Freelance : vivre de ses compétences", "sous_titre": "Freelance · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : freelance, tarifs et devis",
 "desc": "5 exercices progressifs : offre et portfolio, calcul du tarif journalier, devis avec acompte, facturation et relances, gestion d'un client difficile, avec corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Freelance : vivre de ses compétences ». Il te fait passer de l'idée d'offre jusqu'à la gestion d'un client difficile. "
          "Les montants sont des exemples d'entraînement. Pour ton statut, tes impôts et les mentions obligatoires de tes factures, renseigne-toi auprès des services officiels ou d'un comptable.",
 "exercices": [
  {"titre": "Offre, niche et portfolio", "niveau": "Débutant", "duree": "45 min",
   "consigne": "Construis l'offre de départ d'un freelance (toi ou un profil imaginaire) et le plan de son portfolio.",
   "etapes": ["Liste 3 compétences, 3 types de clients possibles et 3 problèmes que tu sais résoudre.",
              "Choisis une niche et rédige ton offre avec le modèle : « J'aide [client] à [résultat] grâce à [service] ».",
              "Prévois 3 projets de portfolio : contexte, travail réalisé, résultat, visuel, et précise s'il s'agit d'un projet réel ou d'entraînement.",
              "Rédige le titre de ton profil LinkedIn (une ligne)."],
   "criteres": ["L'offre nomme un client précis et un résultat concret.", "Les projets du portfolio correspondent à la niche choisie.",
                "Les projets d'entraînement sont présentés honnêtement.", "Le titre LinkedIn est compréhensible par un non-spécialiste."],
   "corrige": {"texte": ["Exemple de réponse. Compétences : graphisme, montage vidéo court, rédaction de publications. Clients possibles : restaurants, salons de coiffure, écoles privées. "
                          "Problèmes : visuels peu attirants, pages Facebook inactives, menus illisibles.",
                          "Offre : « J'aide les restaurants et maquis de Cotonou à attirer plus de clients grâce à des menus, affiches et vidéos courtes pour WhatsApp et Facebook. »",
                          "Portfolio : 1) Menu refait pour un maquis d'Akpakpa (projet d'entraînement, précisé), avant/après. 2) Série de 4 visuels pour le restaurant d'un proche (projet réel, avec son accord), "
                          "résultat : plus de messages après publication selon le gérant. 3) Vidéo de 20 secondes présentant un plat du jour (projet d'entraînement).",
                          "Titre LinkedIn : « Graphiste pour restaurants · Menus, affiches et vidéos qui donnent faim ».",
                          "Erreur fréquente : présenter un projet d'entraînement comme une commande réelle. Si un client le découvre, la confiance est perdue. Grille : offre précise (3), cohérence du portfolio (3), honnêteté (2), titre clair (2)."]}},
  {"titre": "Calculer son tarif journalier", "niveau": "Débutant", "duree": "35 min",
   "consigne": "Chiffres d'exemple d'un freelance à Cotonou. Besoins mensuels : charges personnelles 180 000 FCFA, internet 20 000 FCFA, logiciels 15 000 FCFA, épargne et imprévus 30 000 FCFA, "
                "provision pour impôts et cotisations 30 000 FCFA (montant à vérifier selon ton statut). Il a acheté un ordinateur de 600 000 FCFA qu'il veut renouveler dans 24 mois. "
                "Il compte 20 jours ouvrés par mois, dont 6 consacrés à la prospection, à l'administratif et à la formation.",
   "etapes": ["Calcule la part mensuelle de l'ordinateur et le besoin mensuel total.", "Calcule le nombre de jours facturables et le tarif journalier minimum.",
              "Arrondis le tarif journalier, puis calcule un tarif horaire sur une base de 7 h par jour.", "Estime le prix d'un logo qui demande 2,5 jours de travail."],
   "criteres": ["Le matériel est réparti sur sa durée d'utilisation.", "Les jours non facturables sont déduits.", "Les arrondis sont faits vers le haut et justifiés."],
   "corrige": {"texte": ["Part de l'ordinateur : 600 000 ÷ 24 = 25 000 FCFA par mois. Besoin mensuel total : 180 000 + 20 000 + 15 000 + 30 000 + 30 000 + 25 000 = 300 000 FCFA.",
                          "Jours facturables : 20 − 6 = 14. Tarif journalier minimum : 300 000 ÷ 14 ≈ 21 429 FCFA. Arrondi vers le haut : 22 000 FCFA par jour. "
                          "Contrôle : 14 × 22 000 = 308 000 FCFA, ce qui couvre bien les 300 000 FCFA de besoins.",
                          "Tarif horaire : 22 000 ÷ 7 ≈ 3 143 FCFA, arrondi à 3 150 FCFA de l'heure.",
                          "Logo de 2,5 jours : 2,5 × 22 000 = 55 000 FCFA. Ce prix est ensuite comparé au marché et à la valeur pour le client : s'il est très au-dessus des prix pratiqués, il faut travailler plus vite, "
                          "viser des clients plus solides ou mieux montrer la valeur du travail.",
                          "Erreur fréquente : diviser par 20 jours au lieu de 14. Le tarif serait de 15 000 FCFA par jour, et le freelance ne couvrirait que 14 × 15 000 = 210 000 FCFA, soit 90 000 FCFA de moins que ses besoins."]}},
  {"titre": "Rédiger un devis avec acompte", "niveau": "Intermédiaire", "duree": "45 min",
   "consigne": "Une clinique de Cotonou te demande un site vitrine. Avec ton tarif de 22 000 FCFA par jour, prépare un devis complet. Durées estimées : maquette 2 jours, intégration de 5 pages 4 jours, "
                "formulaire de contact et bouton WhatsApp 1 jour, mise en ligne 0,5 jour, formation du personnel 0,5 jour. L'hébergement et le nom de domaine ne sont pas inclus. Acompte : 40 %.",
   "etapes": ["Calcule le prix de chaque ligne et le total.", "Calcule l'acompte et le solde.",
              "Rédige les conditions : délai, nombre de retouches, ce qui n'est pas inclus, validité du devis, propriété des fichiers.",
              "Rédige le message d'envoi du devis au client."],
   "criteres": ["Chaque ligne a une durée, un prix unitaire et un total.", "Acompte et solde sont justes et leur échéance est indiquée.",
                "Ce qui n'est pas inclus est écrit clairement.", "Le nombre de retouches est précisé."],
   "corrige": {"texte": ["Lignes : maquette 2 × 22 000 = 44 000 FCFA ; intégration 4 × 22 000 = 88 000 FCFA ; formulaire et bouton WhatsApp 1 × 22 000 = 22 000 FCFA ; mise en ligne 0,5 × 22 000 = 11 000 FCFA ; "
                          "formation 0,5 × 22 000 = 11 000 FCFA. Total : 44 000 + 88 000 + 22 000 + 11 000 + 11 000 = 176 000 FCFA (8 jours au total).",
                          "Acompte : 176 000 × 40 % = 70 400 FCFA, à la signature. Solde : 176 000 − 70 400 = 105 600 FCFA, à la mise en ligne.",
                          "Conditions d'exemple : délai de 4 semaines à partir de la réception de l'acompte et des contenus (textes, photos, logo) ; 2 séries de retouches incluses sur la maquette et 1 sur le site ; "
                          "retouche supplémentaire facturée au tarif horaire ; hébergement, nom de domaine, rédaction des textes et photos professionnelles non inclus ; devis valable 30 jours ; "
                          "codes d'accès et fichiers remis après paiement complet.",
                          "Message : « Bonjour Docteur, comme convenu, voici le devis pour le site de la clinique (176 000 FCFA, 8 jours de travail). Le projet démarre dès réception de l'acompte de 70 400 FCFA "
                          "et des contenus. Je reste disponible pour en parler par téléphone. »",
                          "Point de vigilance : les mentions obligatoires d'un devis et d'une facture dépendent de ton statut ; vérifie-les auprès de l'administration fiscale ou d'un comptable."]}},
  {"titre": "Facturer et relancer les paiements", "niveau": "Intermédiaire", "duree": "35 min",
   "consigne": "Le 20 du mois, ton tableau de suivi contient 4 factures d'exemple. F-001 : 70 400 FCFA, payée. F-002 : 105 600 FCFA, échéance dépassée de 12 jours. "
                "F-003 : 55 000 FCFA, échéance dans 3 jours. F-004 : 90 000 FCFA, échéance dépassée de 3 jours.",
   "etapes": ["Prépare les colonnes du tableau de suivi des factures.", "Calcule le montant total en attente et le montant en retard.",
              "Indique quelle relance envoyer pour chaque facture non payée.", "Rédige les trois modèles de messages : rappel avant échéance, relance courtoise, relance ferme."],
   "criteres": ["Le tableau permet de voir d'un coup d'œil ce qui est en retard.", "Les montants sont justes.", "Le ton des relances monte progressivement en restant poli."],
   "corrige": {"texte": ["Colonnes : numéro, client, date d'émission, montant, date d'échéance, date de paiement, statut (payée, à venir, en retard), nombre de jours de retard, dernière relance, prochaine action.",
                          "Total en attente : 105 600 + 55 000 + 90 000 = 250 600 FCFA. En retard : 105 600 + 90 000 = 195 600 FCFA. F-003 n'est pas encore en retard.",
                          "Actions : F-002 (12 jours de retard) : relance ferme par écrit puis appel téléphonique. F-004 (3 jours) : relance courtoise. F-003 : rappel aimable la veille de l'échéance.",
                          "Rappel : « Bonjour, petit rappel : la facture F-003 de 55 000 FCFA arrive à échéance demain. Merci d'avance ! » "
                          "Relance courtoise : « Bonjour, sauf erreur de ma part, la facture F-004 de 90 000 FCFA, échue depuis 3 jours, n'est pas encore réglée. Peux-tu me confirmer la date de paiement ? »",
                          "Relance ferme : « Bonjour, la facture F-002 de 105 600 FCFA est échue depuis 12 jours malgré mes messages. Conformément au devis signé, les fichiers définitifs seront remis après paiement. "
                          "Merci de régler cette facture d'ici vendredi. Je t'appelle demain pour en parler. »",
                          "Grille : tableau complet (3), calculs justes (3), relances adaptées et progressives (4)."]}},
  {"titre": "Gérer un client difficile", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "Étude de cas. Un commerçant te contacte pour une affiche « urgente pour demain », refuse l'acompte « parce qu'il paie toujours à la fin », demande trois propositions gratuites « pour voir ton niveau », "
                "trouve tes prix trop élevés et, après une première version, demande d'ajouter un flyer et une vidéo « dans le même prix ».",
   "etapes": ["Repère tous les signaux d'alerte de ce cas.", "Pour chacun, propose une réponse professionnelle.",
              "Décide si tu acceptes la mission et à quelles conditions.", "Rédige le message qui répond à la demande du flyer et de la vidéo."],
   "criteres": ["Au moins 4 signaux d'alerte sont identifiés.", "Les réponses s'appuient sur le devis et les conditions, pas sur l'émotion.",
                "La décision finale est argumentée.", "Le message reste poli et propose une solution payante."],
   "corrige": {"texte": ["Signaux d'alerte : délai irréaliste sans brief clair ; refus de l'acompte ; demande de travail gratuit ; contestation des prix avant même de voir le travail ; ajout de prestations sans paiement.",
                          "Réponses : délai : proposer un délai réaliste ou un supplément pour urgence écrit dans le devis. Acompte : rappeler que c'est ta règle avec tous les nouveaux clients. "
                          "Travail gratuit : renvoyer vers ton portfolio. Prix : expliquer ce qui est inclus ou proposer une version plus simple, sans baisser ton tarif journalier.",
                          "Décision possible : accepter seulement avec un devis signé et un acompte de 50 %, sinon refuser poliment. Un client qui refuse toutes les règles dès le début coûte souvent plus qu'il ne rapporte.",
                          "Message : « Bonjour, merci pour ta confiance ! Le flyer et la vidéo ne font pas partie du devis de l'affiche. Je te propose un devis complémentaire : flyer 15 000 FCFA, vidéo de 20 secondes 25 000 FCFA, "
                          "livraison en 5 jours après acompte. Dis-moi si cela te convient. » (prix d'exemple)",
                          "Grille : signaux identifiés (3), réponses professionnelles (3), décision argumentée (2), message clair et poli (2)."]}}]},
{
 "id": "res-cahier-services", "fichier": "tobmaq-cahier-services-numeriques.pdf", "categorie": "business", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Services numériques : créer son activité", "sous_titre": "Services numériques · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : services numériques pour PME",
 "desc": "5 exercices progressifs : diagnostic des PME, 3 formules chiffrées, contrat de maintenance, trésorerie prévisionnelle et choix entre recruter ou sous-traiter, avec corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Services numériques : créer son activité ». Tu vas construire une offre pour les PME de ta ville, la chiffrer, puis apprendre à la gérer. "
          "Tous les montants sont des exemples. Pour l'enregistrement de ton activité, la fiscalité et l'embauche, renseigne-toi auprès des services officiels ou d'un professionnel.",
 "exercices": [
  {"titre": "Diagnostiquer la présence en ligne de 5 PME", "niveau": "Débutant", "duree": "1 h",
   "consigne": "Choisis 5 PME d'une même zone (par exemple restaurants, pharmacies ou écoles d'un quartier de Cotonou ou de Calavi) et évalue leur présence numérique avec une grille sur 10.",
   "etapes": ["Grille : fiche Google à jour (2), page Facebook active dans le mois (2), WhatsApp Business avec catalogue ou réponses rapides (2), site web ou page de présentation (2), visuels de qualité (2).",
              "Note chaque PME et écris 2 observations précises.", "Pour chaque PME, propose le service qui aurait le plus d'impact.",
              "Termine par les 3 besoins les plus fréquents."],
   "criteres": ["Chaque note est justifiée par une observation.", "Les services proposés répondent au manque observé.", "Les 3 besoins fréquents découlent du tableau."],
   "corrige": {"texte": ["Exemple : Pharmacie A : 4 sur 10. Fiche Google présente mais horaires faux (1 sur 2) ; pas de page Facebook (0) ; WhatsApp Business installé mais profil incomplet, sans catalogue ni réponses rapides (1 sur 2) ; pas de site (0) ; enseigne et photos nettes (2 sur 2). Total : 1 + 0 + 1 + 0 + 2 = 4. "
                          "Service prioritaire : mise à jour de la fiche Google et configuration de WhatsApp Business.",
                          "Restaurant B : 6 sur 10. Page Facebook active mais photos sombres ; pas de catalogue WhatsApp. Service prioritaire : visuels de plats et catalogue WhatsApp Business.",
                          "Les 3 besoins fréquents typiques : informations à jour (horaires, localisation), publications régulières de qualité, commande ou prise de contact facile par WhatsApp. "
                          "Ce sont de bonnes bases pour une formule d'entrée.",
                          "Erreur fréquente : noter « à l'impression » sans vérifier. Chaque point doit être justifié par ce que tu as vu (date de la dernière publication, horaires affichés, etc.)."]}},
  {"titre": "Chiffrer trois formules", "niveau": "Débutant", "duree": "45 min",
   "consigne": "Pour des restaurants, tu proposes 3 formules mensuelles. Ton coût horaire cible est de 3 000 FCFA (chiffre d'exemple). "
                "Essentiel : mise à jour de la fiche Google 1 h, 4 visuels 4 h, mise à jour du catalogue WhatsApp 2 h, outils 3 000 FCFA. "
                "Visibilité : 12 publications à 45 min chacune, réponses aux messages 4 h, rapport 1 h, outils 5 000 FCFA. "
                "Croissance : tout Visibilité + gestion d'une campagne publicitaire 4 h + rapport détaillé 2 h supplémentaires, outils 8 000 FCFA ; le budget publicitaire est payé à part par le client. "
                "Prix proposés : 40 000, 75 000 et 120 000 FCFA.",
   "etapes": ["Calcule le temps total et le coût de chaque formule.", "Calcule la marge de chaque formule et son taux de marge sur le coût.",
              "Vérifie que les formules sont bien progressives.", "Rédige la présentation des 3 formules côte à côte."],
   "criteres": ["Les heures et les coûts sont détaillés ligne par ligne.", "Chaque formule a une marge positive.", "La présentation indique ce qui est inclus et ce qui ne l'est pas."],
   "corrige": {"texte": ["Essentiel : 1 + 4 + 2 = 7 h ; 7 × 3 000 = 21 000 FCFA + 3 000 FCFA d'outils = 24 000 FCFA. Marge : 40 000 − 24 000 = 16 000 FCFA. Taux de marge : 16 000 ÷ 24 000 × 100 ≈ 66,7 %.",
                          "Visibilité : publications 12 × 45 min = 540 min = 9 h ; total 9 + 4 + 1 = 14 h ; 14 × 3 000 = 42 000 FCFA + 5 000 FCFA = 47 000 FCFA. Marge : 75 000 − 47 000 = 28 000 FCFA. Taux : 28 000 ÷ 47 000 × 100 ≈ 59,6 %.",
                          "Croissance : 14 + 4 + 2 = 20 h ; 20 × 3 000 = 60 000 FCFA + 8 000 FCFA = 68 000 FCFA. Marge : 120 000 − 68 000 = 52 000 FCFA. Taux : 52 000 ÷ 68 000 × 100 ≈ 76,5 %.",
                          "Progression : chaque formule ajoute un résultat visible (être trouvé, être actif, attirer de nouveaux clients) et la marge en FCFA augmente avec la formule. "
                          "La marge de la formule du milieu est confortable : c'est celle à mettre en avant.",
                          "Présentation : pour chaque formule, le résultat promis, la liste des tâches incluses, les exclusions (budget publicitaire, séance photo, impression), l'engagement minimum (3 mois), le prix et le paiement en début de mois."]}},
  {"titre": "Rédiger et chiffrer un contrat de maintenance", "niveau": "Intermédiaire", "duree": "45 min",
   "consigne": "Une école privée de Calavi possède 10 ordinateurs et 2 imprimantes. Tu proposes une visite mensuelle de 3 h et estimes en moyenne 2 h d'interventions supplémentaires par mois. "
                "Ton coût horaire de technicien est de 4 000 FCFA et chaque mois te coûte 2 000 FCFA de transport (chiffres d'exemple). Les pièces de rechange sont facturées à part.",
   "etapes": ["Calcule le coût mensuel du contrat.", "Propose un prix mensuel avec une marge et calcule cette marge.",
              "Calcule le prix annuel, puis le prix avec une remise de 10 % pour un engagement de 12 mois.",
              "Rédige les clauses principales du contrat."],
   "criteres": ["Le coût inclut le temps et le transport.", "La remise est calculée correctement.", "Le contrat précise périmètre, interventions incluses, délai de réponse, exclusions, durée et préavis."],
   "corrige": {"texte": ["Coût mensuel : (3 + 2) h × 4 000 = 20 000 FCFA + 2 000 FCFA de transport = 22 000 FCFA.",
                          "Prix mensuel proposé : 35 000 FCFA. Marge : 35 000 − 22 000 = 13 000 FCFA par mois, soit un taux de marge de 13 000 ÷ 22 000 × 100 ≈ 59 %.",
                          "Prix annuel sans remise : 35 000 × 12 = 420 000 FCFA. Remise de 10 % : 420 000 × 0,10 = 42 000 FCFA. Prix annuel avec engagement : 420 000 − 42 000 = 378 000 FCFA, soit 31 500 FCFA par mois. "
                          "Marge mensuelle restante : 31 500 − 22 000 = 9 500 FCFA : la remise reste rentable et sécurise un client pour un an.",
                          "Clauses d'exemple : périmètre (10 ordinateurs, 2 imprimantes, réseau de la salle) ; une visite mensuelle de 3 h (nettoyage, mises à jour, antivirus, sauvegardes, vérification des imprimantes) ; "
                          "jusqu'à 2 h d'interventions supplémentaires par mois incluses, au-delà facturées à l'heure ; délai de réponse sous 24 h ouvrées ; pièces et matériel neuf exclus ; "
                          "durée de 12 mois ; préavis de résiliation d'un mois ; paiement en début de mois.",
                          "Grille : coût juste (3), prix et remise justes (3), clauses complètes (4)."]}},
  {"titre": "Construire une trésorerie prévisionnelle", "niveau": "Intermédiaire", "duree": "45 min",
   "consigne": "Petite agence de services numériques (chiffres d'exemple). Solde au début du mois 1 : 150 000 FCFA. Charges fixes : 250 000 FCFA par mois. Rémunération des deux associés : 300 000 FCFA par mois. "
                "Encaissements prévus : mois 1 : 600 000 FCFA ; mois 2 : 800 000 FCFA (dont 100 000 FCFA de retard du mois 1) ; mois 3 : 750 000 FCFA. "
                "Dépenses ponctuelles : achat d'un ordinateur de 350 000 FCFA au mois 1 et sous-traitance de 50 000 FCFA aux mois 2 et 3.",
   "etapes": ["Construis le tableau : solde de début, encaissements, décaissements, solde de fin, pour les 3 mois.", "Repère le problème éventuel.",
              "Propose une solution et refais le calcul.", "Compare le solde final à une réserve cible de 2 mois de charges fixes."],
   "criteres": ["Le solde de fin d'un mois devient le solde de début du suivant.", "Tous les décaissements sont comptés.", "La solution proposée est réaliste et chiffrée."],
   "corrige": {"texte": ["Mois 1 : décaissements 250 000 + 300 000 + 350 000 = 900 000 FCFA. Solde de fin : 150 000 + 600 000 − 900 000 = −150 000 FCFA.",
                          "Mois 2 : décaissements 250 000 + 300 000 + 50 000 = 600 000 FCFA. Solde de fin : −150 000 + 800 000 − 600 000 = 50 000 FCFA. "
                          "Mois 3 : décaissements 600 000 FCFA. Solde de fin : 50 000 + 750 000 − 600 000 = 200 000 FCFA.",
                          "Problème : la trésorerie est négative au mois 1, l'agence ne peut pas payer toutes ses dépenses, même si elle est rentable sur 3 mois.",
                          "Solution : reporter l'achat de l'ordinateur au mois 3. Mois 1 : 150 000 + 600 000 − 550 000 = 200 000 FCFA. Mois 2 : 200 000 + 800 000 − 600 000 = 400 000 FCFA. "
                          "Mois 3 : 400 000 + 750 000 − 600 000 − 350 000 = 200 000 FCFA. Le solde reste positif chaque mois. Autres pistes : facturer les forfaits en début de mois, relancer plus tôt le client en retard.",
                          "Réserve cible : 2 × 250 000 = 500 000 FCFA. Avec 200 000 FCFA en fin de mois 3, il manque 300 000 FCFA : il faut mettre de côté une partie de chaque mois avant tout nouvel achat important."]}},
  {"titre": "Recruter, sous-traiter et garantir la qualité", "niveau": "Intermédiaire", "duree": "40 min",
   "consigne": "L'agence a, en moyenne, 30 h de maintenance de trop chaque mois. Option A : sous-traiter à un technicien indépendant à 4 000 FCFA de l'heure. "
                "Option B : recruter un technicien pour un coût total d'exemple de 200 000 FCFA par mois (salaire et obligations, à vérifier auprès des services officiels).",
   "etapes": ["Calcule le coût mensuel de chaque option pour 30 h.", "Calcule le nombre d'heures à partir duquel le recrutement devient moins cher.",
              "Choisis une option et argumente avec au moins 2 critères non financiers.", "Rédige une checklist qualité de 8 points pour une intervention de maintenance."],
   "criteres": ["Les deux coûts sont justes.", "Le seuil est calculé et interprété.", "La checklist est concrète et vérifiable."],
   "corrige": {"texte": ["Option A : 30 × 4 000 = 120 000 FCFA par mois. Option B : 200 000 FCFA par mois, quel que soit le volume. Pour 30 h, la sous-traitance coûte 80 000 FCFA de moins.",
                          "Seuil : 200 000 ÷ 4 000 = 50 h par mois. Au-delà de 50 h stables chaque mois, recruter devient moins cher que sous-traiter.",
                          "Décision : sous-traiter pour l'instant. Critères non financiers : souplesse si le volume baisse ; possibilité de tester la personne sur quelques missions ; moins d'obligations administratives. "
                          "En contrepartie : moindre disponibilité et nécessité de contrôler le travail, car l'agence reste responsable face au client. À réévaluer si le volume dépasse durablement 50 h.",
                          "Checklist d'exemple : 1) confirmer le rendez-vous la veille ; 2) noter le problème signalé ; 3) sauvegarder les données avant intervention ; 4) vérifier les mises à jour et l'antivirus ; "
                          "5) tester les imprimantes et le réseau ; 6) nettoyer le matériel ; 7) faire signer une fiche d'intervention ; 8) envoyer un compte rendu au client dans les 24 h.",
                          "Grille : calculs justes (4), décision argumentée (3), checklist complète (3)."]}}]},
]

CAHIERS_E = [
{
 "id": "res-cahier-paris", "fichier": "tobmaq-cahier-paris-sportifs.pdf", "categorie": "business", "logiciels": [], "niveau": "Débutant",
 "titre": "Cahier d'exercices · Paris sportifs : cotes, risques et arnaques (18+)", "sous_titre": "Éducation financière · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : cotes, risques et arnaques aux paris (18+)",
 "desc": "5 exercices pour adultes : probabilités implicites, marge du bookmaker, espérance, coupons combinés, martingale, budget et analyse d'arnaques aux pronostics, avec corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Paris sportifs : comprendre les cotes et les risques (18+) ». Il est réservé aux adultes (18 ans et plus) et purement éducatif : "
          "il ne donne aucun pronostic, aucune méthode pour gagner et ne t'invite jamais à parier. Tu n'as besoin que d'une calculatrice ou d'un tableur. "
          "Tous les chiffres sont des exemples pour t'entraîner. Si le jeu te pose un problème, parles-en à un proche ou à un professionnel de santé.",
 "exercices": [
  {"titre": "Des cotes aux probabilités", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Un match fictif est proposé avec les cotes suivantes : victoire de l'équipe A à 1,80, match nul à 3,50, victoire de l'équipe B à 4,50. Un second pari, à deux issues (plus ou moins de 2,5 buts), est coté 1,85 et 1,95.",
   "etapes": ["Calcule la probabilité implicite de chaque issue (1 ÷ cote), arrondie au centième de pourcent.",
              "Additionne les probabilités de chaque pari et déduis la marge du bookmaker.",
              "Pour le match, estime les probabilités « sans marge » en divisant chaque probabilité implicite par la somme."],
   "criteres": ["Les 5 probabilités implicites sont justes.", "Les deux marges sont calculées et interprétées.", "Les probabilités sans marge totalisent 100 %."],
   "corrige": {"texte": ["Match : 1 ÷ 1,80 = 55,56 % ; 1 ÷ 3,50 = 28,57 % ; 1 ÷ 4,50 = 22,22 %. Somme : 106,35 %. La marge du bookmaker est d'environ 6,35 points.",
                          "Plus ou moins de 2,5 buts : 1 ÷ 1,85 = 54,05 % ; 1 ÷ 1,95 = 51,28 %. Somme : 105,34 %, soit une marge d'environ 5,34 points.",
                          "Probabilités sans marge du match (approximation) : 55,56 ÷ 106,35 = 52,24 % ; 28,57 ÷ 106,35 = 26,87 % ; 22,22 ÷ 106,35 = 20,90 %. Total : 100 %. "
                          "Conclusion : le bookmaker affiche pour chaque issue une probabilité plus élevée que son estimation, et paie donc moins que ce que le risque justifierait. "
                          "Erreur fréquente : croire qu'une cote basse signifie « victoire sûre ». Une cote de 1,80 correspond à un peu plus d'une chance sur deux."]}},
  {"titre": "L'espérance mathématique d'un pari", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Calcule l'espérance de deux paris fictifs, puis leur résultat moyen sur une longue série. Formule : espérance = probabilité réelle × montant total reçu - mise.",
   "etapes": ["Pari 1 : mise de 2 000 FCFA à la cote 1,90 sur une issue dont la probabilité réelle est de 50 %.",
              "Pari 2 : mise de 2 000 FCFA à la cote 3,00 sur une issue dont la probabilité réelle est de 30 %.",
              "Pour chaque pari, calcule l'espérance en FCFA et en pourcentage de la mise, puis la perte moyenne attendue sur 50 paris identiques."],
   "criteres": ["Les espérances sont négatives et correctement calculées.", "Le passage au pourcentage est juste.", "La conclusion distingue court terme et long terme."],
   "corrige": {"texte": ["Pari 1 : 0,5 × (2 000 × 1,90) - 2 000 = 0,5 × 3 800 - 2 000 = -100 FCFA, soit -5 % de la mise. Sur 50 paris : 50 × (-100) = -5 000 FCFA en moyenne.",
                          "Pari 2 : 0,3 × (2 000 × 3,00) - 2 000 = 0,3 × 6 000 - 2 000 = -200 FCFA, soit -10 % de la mise. Sur 50 paris : -10 000 FCFA en moyenne.",
                          "Conclusion : sur quelques paris, le hasard peut donner un gain ou une perte importante. Mais plus le nombre de paris augmente, plus le résultat total se rapproche de l'espérance, "
                          "qui est négative. C'est pour cela que le pari ne peut pas être une source de revenus."]}},
  {"titre": "Le piège du coupon combiné", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Un groupe WhatsApp vante un « coupon combiné » de 5 matchs, chacun à la cote 1,50. Supposons (exemple) que la probabilité réelle de chaque issue soit de 62 % et que les matchs soient indépendants.",
   "etapes": ["Calcule la probabilité implicite d'une cote de 1,50 et compare-la à 62 %.",
              "Calcule la cote totale du combiné et la probabilité réelle que les 5 issues se réalisent.",
              "Calcule l'espérance d'une mise de 1 000 FCFA sur ce combiné, en FCFA et en pourcentage."],
   "criteres": ["La cote totale est obtenue par multiplication.", "La probabilité de tout gagner est obtenue par multiplication.", "L'espérance est comparée à celle d'un pari simple."],
   "corrige": {"texte": ["Probabilité implicite : 1 ÷ 1,50 = 66,67 %, alors que la probabilité réelle de l'exemple est de 62 % : chaque cote est déjà défavorable.",
                          "Cote totale : 1,50 × 1,50 × 1,50 × 1,50 × 1,50 = 7,59 (exactement 7,59375). Probabilité de tout gagner : 0,62 × 0,62 × 0,62 × 0,62 × 0,62 = 0,0916, soit environ 9,2 %. "
                          "Le parieur perd donc son coupon environ 9 fois sur 10.",
                          "Espérance : 0,0916 × 7 594 - 1 000 = environ 696 - 1 000 = -304 FCFA, soit environ -30 % de la mise. "
                          "Pour un seul de ces paris : 0,62 × 1 500 - 1 000 = -70 FCFA, soit -7 %. Le combiné multiplie les marges : c'est le produit le plus rentable pour l'opérateur, pas pour le parieur."]}},
  {"titre": "Budget de jeu et piège de la martingale", "niveau": "Débutant", "duree": "30 min",
   "consigne": "Koffi gagne en exemple 90 000 FCFA par mois. Ses dépenses essentielles (loyer, nourriture, transport, factures) s'élèvent à 70 000 FCFA, il épargne 10 000 FCFA et il lui reste 10 000 FCFA de loisirs. Un ami lui conseille la « martingale » : doubler la mise après chaque perte, en commençant à 500 FCFA, sur des paris à environ 50 %.",
   "etapes": ["Indique quelles sommes ne doivent jamais aller au jeu, et propose une limite mensuelle raisonnable dans les loisirs.",
              "Calcule le total misé si Koffi perd 6 paris de suite avec la martingale (500, 1 000, 2 000...), et ce qu'il espérait gagner.",
              "Calcule la probabilité de 6 pertes de suite à 50 %, puis explique pourquoi cette série finit presque sûrement par arriver si on répète la méthode."],
   "criteres": ["Les dépenses essentielles et l'épargne sont protégées.", "Le total de la martingale est juste.", "L'argument sur la répétition est compris."],
   "corrige": {"texte": ["Les 70 000 FCFA essentiels et les 10 000 FCFA d'épargne ne doivent jamais servir au jeu, ni aucun emprunt. Seule une petite partie des 10 000 FCFA de loisirs, par exemple 2 000 FCFA, "
                          "pourrait être fixée comme limite, à condition d'accepter de la perdre entièrement et de s'arrêter une fois atteinte.",
                          "Martingale : 500 + 1 000 + 2 000 + 4 000 + 8 000 + 16 000 = 31 500 FCFA perdus en 6 paris, pour un gain espéré de seulement 500 FCFA par série. "
                          "Le 7e pari demanderait 32 000 FCFA : bien plus que tout le budget de loisirs, et même que l'épargne.",
                          "Probabilité de 6 pertes de suite : 0,5 × 0,5 × 0,5 × 0,5 × 0,5 × 0,5 = 1/64, soit environ 1,6 %. Cela paraît faible, mais sur 100 séries, la probabilité de rencontrer au moins une fois "
                          "cette série noire est d'environ 79 % (1 - (63/64) puissance 100). Et comme les cotes contiennent une marge, l'espérance reste négative à chaque pari. "
                          "La martingale ne supprime pas le risque : elle remplace beaucoup de petits gains par une grosse perte presque certaine à terme."]}},
  {"titre": "Démonter une arnaque aux pronostics", "niveau": "Débutant", "duree": "25 min",
   "consigne": "Analyse ce message fictif reçu sur Telegram : « BIG ANNONCE ! Match arrangé ce soir, cote 32, info directe des dirigeants. Seulement 20 places VIP à 15 000 FCFA par Mobile Money au 01 XX XX XX XX. 100 % sûr, remboursé si perdu. Regardez les gains de nos membres (captures). Payez avant 18 h ! »",
   "etapes": ["Relève au moins 6 signaux d'alerte dans le message.",
              "Explique pourquoi la logique même de l'offre est absurde.",
              "Rédige la réponse que tu enverrais à un ami qui veut payer, et liste ce qu'il faut faire face à ce type de message."],
   "criteres": ["Au moins 6 signaux pertinents.", "L'incohérence économique de l'offre est expliquée.", "Les bons réflexes sont donnés : ne pas payer, conserver les preuves, signaler, demander de l'aide."],
   "corrige": {"texte": ["Signaux d'alerte : promesse de gain « 100 % sûr » ; prétendu match « arrangé » avec une source invérifiable ; cote très élevée présentée comme certaine ; urgence (« avant 18 h ») "
                          "et rareté (« 20 places ») pour empêcher de réfléchir ; paiement à un numéro Mobile Money personnel, sans facture ni société identifiable ; « remboursement » impossible à faire valoir ; "
                          "captures de gains faciles à truquer ou à sélectionner.",
                          "Incohérence : si quelqu'un connaissait réellement un résultat à l'avance, il n'aurait aucun intérêt à le vendre 15 000 FCFA à des inconnus, au risque d'attirer l'attention. "
                          "Le vrai produit vendu, c'est l'accès payant : le vendeur gagne sur les paiements, que le match soit gagné ou perdu. Certains vendent même des issues différentes à différents groupes "
                          "pour pouvoir montrer ensuite des « gagnants ». Rappel : participer à une vraie manipulation de match serait de toute façon illégal.",
                          "Réponse possible : « Ne paie pas. Aucun pronostic n'est sûr, et ce groupe gagne sur ton argent, pas sur le match. » Bons réflexes : ne rien payer, ne transmettre aucun code "
                          "ni pièce d'identité, conserver les captures et le numéro, signaler le compte à la plateforme et aux autorités compétentes, quitter le groupe. "
                          "Si l'envie de jouer devient difficile à contrôler, en parler à un proche ou consulter un professionnel de santé."]}}]},
{
 "id": "res-cahier-trading", "fichier": "tobmaq-cahier-trading.pdf", "categorie": "business", "logiciels": [], "niveau": "Intermédiaire",
 "titre": "Cahier d'exercices · Trading : risques, levier et arnaques (18+)", "sous_titre": "Éducation financière · 5 exercices progressifs et leurs corrigés",
 "titre_court": "Cahier d'exercices : risques du trading et arnaques (18+)",
 "desc": "5 exercices pour adultes : pourcentages de gain et de perte, effet de levier, frais et stop-loss, calcul d'une promesse de Ponzi et analyse d'un faux trader, avec corrigés détaillés.",
 "intro": "Ce cahier accompagne la formation « Trading : comprendre les marchés et éviter les arnaques (18+) ». Il est réservé aux adultes (18 ans et plus) et purement éducatif : "
          "il ne constitue pas un conseil en investissement, ne recommande aucun produit et ne t'invite jamais à placer de l'argent réel. Tu n'as besoin que d'une calculatrice ou d'un tableur. "
          "Tous les chiffres sont des exemples pour t'entraîner à mesurer le risque et à reconnaître les arnaques.",
 "exercices": [
  {"titre": "Pourcentages de gain et de perte", "niveau": "Débutant", "duree": "20 min",
   "consigne": "Un capital fictif de 200 000 FCFA subit plusieurs variations. Formule : variation en % = (valeur finale - valeur initiale) ÷ valeur initiale × 100.",
   "etapes": ["Le capital tombe à 150 000 FCFA. Calcule la perte en % et le gain nécessaire pour revenir à 200 000 FCFA.",
              "Complète le tableau : gain nécessaire pour revenir au départ après une perte de 10 %, 20 %, 50 % et 80 % (formule : 1 ÷ (1 - perte) - 1).",
              "Le capital de départ subit successivement +10 %, -10 %, +15 % puis -20 %. Calcule la valeur finale et la variation totale."],
   "criteres": ["Les calculs sont justes et détaillés.", "L'asymétrie des pertes est expliquée.", "Les variations successives sont multipliées, pas additionnées."],
   "corrige": {"texte": ["Perte : (150 000 - 200 000) ÷ 200 000 = -25 %. Pour revenir à 200 000 FCFA, il faut gagner 50 000 FCFA sur 150 000 FCFA, soit 50 000 ÷ 150 000 = +33,3 %.",
                          "Tableau : après -10 %, il faut +11,1 % ; après -20 %, +25 % ; après -50 %, +100 % ; après -80 %, +400 % (le capital doit être multiplié par 5).",
                          "Variations successives : 200 000 × 1,10 × 0,90 × 1,15 × 0,80 = 182 160 FCFA, soit -8,92 %. Additionner les pourcentages (+10 - 10 + 15 - 20 = -5 %) serait faux. "
                          "Leçon : les grosses pertes sont très difficiles à rattraper, d'où l'importance de limiter le risque plutôt que de chercher de gros gains."]}},
  {"titre": "Mesurer l'effet de levier", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Avec un capital fictif de 50 000 FCFA, compare l'effet d'une variation de prix de +3 % et de -3 % selon le levier : 1, 5, 20 et 50.",
   "etapes": ["Pour chaque levier, calcule l'exposition (capital × levier).",
              "Calcule le gain et la perte en FCFA et en % du capital pour +3 % et -3 %.",
              "Calcule la baisse de prix qui effacerait tout le capital (100 % ÷ levier) et commente le cas du levier 50."],
   "criteres": ["Les 4 expositions sont justes.", "Gains et pertes sont symétriques et correctement calculés.", "Le seuil de perte totale est compris."],
   "corrige": {"texte": ["Levier 1 : exposition 50 000 FCFA ; +3 % donne +1 500 FCFA (+3 %), -3 % donne -1 500 FCFA (-3 %). Capital effacé par une baisse de 100 %.",
                          "Levier 5 : exposition 250 000 FCFA ; +/- 7 500 FCFA, soit +/- 15 % du capital. Capital effacé par une baisse de 20 %.",
                          "Levier 20 : exposition 1 000 000 FCFA ; +/- 30 000 FCFA, soit +/- 60 % du capital. Capital effacé par une baisse de 5 %.",
                          "Levier 50 : exposition 2 500 000 FCFA ; +3 % donnerait +75 000 FCFA (+150 %), mais -3 % représenterait -75 000 FCFA, plus que le capital : "
                          "la position est fermée bien avant, dès une baisse de 2 %, et tout le capital est perdu (voire davantage selon les conditions de la plateforme). "
                          "Conclusion : le levier ne rend pas plus habile, il multiplie le résultat dans les deux sens, et une petite variation suffit à tout perdre."]}},
  {"titre": "Frais et stop-loss", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Exemple fictif : achat de 50 titres à 2 500 FCFA, avec des frais de 0,5 % sur chaque opération (achat et vente). Un stop-loss est placé à 2 250 FCFA.",
   "etapes": ["Calcule le montant investi, les frais d'achat, et la perte en % visée par le stop-loss.",
              "Si le stop-loss s'exécute à 2 250 FCFA, calcule la perte sur le prix, les frais de vente et la perte totale.",
              "Explique ce qui se passe si le prix chute brutalement de 2 400 à 2 100 FCFA, et conclus sur ce que garantit ou non un stop-loss."],
   "criteres": ["Les frais sont comptés à l'achat et à la vente.", "La perte totale est juste.", "La limite du stop-loss est expliquée."],
   "corrige": {"texte": ["Montant investi : 50 × 2 500 = 125 000 FCFA. Frais d'achat : 125 000 × 0,5 % = 625 FCFA. Perte visée : (2 250 - 2 500) ÷ 2 500 = -10 %.",
                          "Vente à 2 250 FCFA : 50 × 2 250 = 112 500 FCFA, soit une perte de 12 500 FCFA sur le prix. Frais de vente : 112 500 × 0,5 % = 562,50 FCFA. "
                          "Perte totale : 12 500 + 625 + 562,50 = 13 687,50 FCFA, soit environ 10,95 % des 125 000 FCFA.",
                          "En cas de chute brutale, l'ordre se déclenche mais s'exécute au premier prix disponible, ici 2 100 FCFA : perte sur le prix de 50 × 400 = 20 000 FCFA (-16 %), plus les frais. "
                          "Un stop-loss limite la perte visée et évite de rester bloqué par l'émotion, mais ne garantit pas le prix de sortie. Les frais, eux, s'ajoutent toujours."]}},
  {"titre": "La promesse impossible : calcul d'un Ponzi", "niveau": "Intermédiaire", "duree": "25 min",
   "consigne": "Une « société d'investissement » contactée sur Facebook promet 15 % par mois garantis et un bonus pour chaque personne parrainée. Chaque membre doit recruter 3 nouveaux membres pour toucher ses gains.",
   "etapes": ["Calcule ce que deviendraient 100 000 FCFA après 12 mois à 15 % par mois composés.",
              "Calcule le nombre de nouveaux membres nécessaires au niveau 10 puis au niveau 15 du système de parrainage (3 puissance n).",
              "Explique d'où viennent les « gains » versés et comment le système finit."],
   "criteres": ["Le calcul composé est juste.", "La croissance du recrutement est chiffrée.", "Le mécanisme du Ponzi est expliqué clairement."],
   "corrige": {"texte": ["100 000 × 1,15 puissance 12 = environ 535 025 FCFA, soit plus de 5 fois la mise en un an. Aucun placement honnête ne peut garantir un tel rendement : "
                          "un rendement élevé va toujours avec un risque élevé, et le mot « garanti » est ici le premier signal d'arnaque.",
                          "Recrutement : 3 puissance 10 = 59 049 nouveaux membres au niveau 10, et 3 puissance 15 = 14 348 907 au niveau 15, soit de l'ordre de la population d'un pays entier. "
                          "Le recrutement ne peut donc pas continuer longtemps.",
                          "Les « gains » des premiers membres sont payés avec l'argent des nouveaux arrivants : c'est une pyramide de Ponzi. Quand les inscriptions ralentissent, les retraits sont « bloqués », "
                          "des « frais de déblocage » sont réclamés, puis les organisateurs disparaissent. La grande majorité des participants, souvent des proches recrutés les uns par les autres, perdent leur argent."]}},
  {"titre": "Analyser un faux trader et vérifier un intermédiaire", "niveau": "Intermédiaire", "duree": "30 min",
   "consigne": "Analyse ce message fictif reçu sur Instagram : « Salut ! Moi c'est Coach Max, trader pro. Regarde mes résultats : +1 200 000 FCFA cette semaine (capture). Mes signaux VIP 25 000 FCFA/mois, 95 % de réussite. Ou envoie-moi 100 000 FCFA par Mobile Money et je trade pour toi, tu récupères 300 000 FCFA dans 2 semaines. Plateforme partenaire avec levier x500. Offre valable aujourd'hui seulement. »",
   "etapes": ["Relève au moins 7 signaux d'alerte.",
              "Calcule la baisse de prix qui effacerait tout le capital avec un levier de 500.",
              "Rédige la liste des vérifications à faire avant de confier de l'argent à un intermédiaire, et les gestes à adopter si l'on a déjà payé."],
   "criteres": ["Au moins 7 signaux pertinents.", "Le calcul du levier est juste.", "Les vérifications citent le régulateur compétent et les bons réflexes en cas d'arnaque."],
   "corrige": {"texte": ["Signaux : contact spontané par un inconnu ; captures de gains invérifiables ; taux de réussite irréaliste (« 95 % ») ; vente de « signaux » payants ; demande d'envoyer de l'argent sur un compte "
                          "personnel pour « trader à ta place » ; rendement promis et quasi garanti (triplement en 2 semaines) ; levier extrême ; urgence (« aujourd'hui seulement ») ; "
                          "plateforme « partenaire » sans identité vérifiable.",
                          "Levier 500 : la baisse qui efface le capital est 100 % ÷ 500 = 0,2 %. Une variation minuscule, qui peut arriver en quelques minutes, suffit à tout perdre.",
                          "Vérifications : identité et adresse de la société ; agrément par le régulateur compétent (dans l'UMOA, dont fait partie le Bénin, une autorité régionale régule le marché financier : "
                          "renseigne-toi auprès d'elle ou de sources officielles) ; aucun paiement vers un numéro personnel ; aucune promesse de rendement garanti ; possibilité de retirer son argent sans frais inventés. "
                          "Si l'on a déjà payé : arrêter tout nouveau versement (même pour des « frais de déblocage »), conserver captures, numéros et reçus, prévenir son opérateur Mobile Money ou sa banque, "
                          "signaler aux autorités compétentes, et en parler à un proche pour ne pas rester seul face à la pression."]}}]},
]

CAHIERS += CAHIERS_A + CAHIERS_B + CAHIERS_C + CAHIERS_D + CAHIERS_E

def taille(fichier):
    return f"{max(1, round((OUT / fichier).stat().st_size / 1024))} Ko"


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    PREV.mkdir(exist_ok=True)
    entrees = []
    for c in CAHIERS:
        pages = produire(c)
        pdf = OUT / c["fichier"]
        subprocess.run(["pdftoppm", "-png", "-r", "40", "-f", "1", "-l", "1", "-singlefile", str(pdf), str(PREV / pdf.stem)], check=True)
        logiciels = ", ".join(f'"{x}"' for x in c["logiciels"])
        entrees.append(
            f'  {{ id: "{c["id"]}", title: "{c["titre_court"]}", type: "Cahier d\'exercices", category: "{c["categorie"]}", software: [{logiciels}], level: "{c["niveau"]}",\n'
            f'    file: "ressources/{c["fichier"]}", preview: "apercus/{pdf.stem}.png", format: "PDF", size: "{taille(c["fichier"])}", pages: {pages},\n'
            f'    licence: "CC BY 4.0 · TOB-MAQ", access: "libre", desc: "{c["desc"]}" }}')
        print(f'{c["fichier"]} · {pages} pages · {taille(c["fichier"])}', file=sys.stderr)
    print(",\n".join(entrees))
