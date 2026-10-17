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
