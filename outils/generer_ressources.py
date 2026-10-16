"""
Génère les ressources téléchargeables de TOB-MAQ (PDF) et leurs aperçus.

Usage : python3 outils/generer_ressources.py
Nécessite : reportlab ; pdftoppm (poppler-utils) pour les aperçus.

Toutes ces ressources sont créées par TOB-MAQ et publiées sous licence
CC BY 4.0 : réutilisation libre, y compris commerciale, avec mention « TOB-MAQ ».
Les raccourcis indiqués sont ceux par défaut sous Windows ; ils peuvent
varier selon la version du logiciel et la configuration.
"""
import subprocess
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ressources"
PREV = ROOT / "apercus"
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", FONT_DIR + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", FONT_DIR + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", FONT_DIR + "DejaVuSansMono.ttf"))

INK = HexColor("#12141C")
NIGHT = HexColor("#0B0E17")
VIOLET = HexColor("#6A4BFF")
ORANGE = HexColor("#E8501A")
MUTED = HexColor("#5B6172")
LINE = HexColor("#E3E5EC")
PAPER = HexColor("#F5F6F8")
CMYK = [HexColor("#00B4E6"), HexColor("#E6007E"), HexColor("#FFD400"), INK]
W, H = A4
LICENCE = "TOB-MAQ · Imagine. Crée. Maîtrise. · Licence CC BY 4.0 : réutilisation libre avec mention « TOB-MAQ »."


def entete(c, titre, sous_titre):
    c.setFillColor(NIGHT)
    c.rect(0, H - 96, W, 96, stroke=0, fill=1)
    for i, col in enumerate(CMYK[:3] + [ORANGE]):
        c.setFillColor(col)
        c.rect(W - 40 - (4 - i) * 14, H - 30, 10, 10, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Sans-Bold", 11)
    c.drawString(36, H - 30, "TOB-MAQ")
    c.setFont("Sans-Bold", 19)
    c.drawString(36, H - 60, titre)
    c.setFillColor(HexColor("#B9B2FF"))
    c.setFont("Sans", 10)
    c.drawString(36, H - 80, sous_titre)


def pied(c, page=None):
    c.setStrokeColor(LINE)
    c.line(36, 40, W - 36, 40)
    c.setFillColor(MUTED)
    c.setFont("Sans", 7.5)
    c.drawString(36, 28, LICENCE)
    if page:
        c.drawRightString(W - 36, 28, f"Page {page}")


def tableau_raccourcis(c, x, y, titre, lignes, largeur=250):
    c.setFillColor(VIOLET)
    c.setFont("Sans-Bold", 11.5)
    c.drawString(x, y, titre)
    y -= 8
    for action, touche in lignes:
        y -= 17
        c.setStrokeColor(LINE)
        c.line(x, y - 5, x + largeur, y - 5)
        c.setFillColor(INK)
        c.setFont("Sans", 8.8)
        c.drawString(x, y, action)
        c.setFont("Mono", 8.8)
        c.setFillColor(NIGHT)
        c.drawRightString(x + largeur, y, touche)
    return y - 26


def note_mac(c, y):
    c.setFillColor(PAPER)
    c.roundRect(36, y - 8, W - 72, 26, 5, stroke=0, fill=1)
    c.setFillColor(MUTED)
    c.setFont("Sans", 8.3)
    c.drawString(46, y + 1, "Raccourcis par défaut sous Windows. Sur Mac : Ctrl → Cmd, Alt → Option. "
                           "Ils peuvent varier selon la version du logiciel.")


def raccourcis_graphisme():
    c = canvas.Canvas(str(OUT / "tobmaq-raccourcis-photoshop-illustrator.pdf"), pagesize=A4)
    c.setTitle("Raccourcis essentiels : Photoshop et Illustrator")
    c.setAuthor("TOB-MAQ")
    entete(c, "Raccourcis essentiels", "Adobe Photoshop · Adobe Illustrator")
    note_mac(c, H - 125)
    y1 = tableau_raccourcis(c, 36, H - 160, "Photoshop · Outils", [
        ("Déplacement", "V"), ("Rectangle de sélection", "M"), ("Lasso", "L"),
        ("Sélection rapide / Baguette magique", "W"), ("Recadrage", "C"), ("Pinceau", "B"),
        ("Gomme", "E"), ("Texte", "T"), ("Plume", "P"), ("Taille du pinceau", "[  ]"),
        ("Couleurs par défaut (noir/blanc)", "D"), ("Inverser premier/arrière-plan", "X")])
    tableau_raccourcis(c, 36, y1, "Photoshop · Calques et édition", [
        ("Nouveau calque", "Ctrl+Maj+N"), ("Dupliquer le calque / la sélection", "Ctrl+J"),
        ("Transformation manuelle", "Ctrl+T"), ("Masque d'écrêtage", "Ctrl+Alt+G"),
        ("Grouper les calques", "Ctrl+G"), ("Fusionner avec le calque inférieur", "Ctrl+E"),
        ("Intervertir la sélection", "Ctrl+Maj+I"), ("Désélectionner", "Ctrl+D"),
        ("Annuler", "Ctrl+Z"), ("Taille écran", "Ctrl+0")])
    y2 = tableau_raccourcis(c, 309, H - 160, "Illustrator · Outils", [
        ("Sélection", "V"), ("Sélection directe", "A"), ("Plume", "P"), ("Texte", "T"),
        ("Rectangle", "M"), ("Ellipse", "L"), ("Pipette", "I"), ("Main (temporaire)", "Espace")])
    tableau_raccourcis(c, 309, y2, "Illustrator · Objets", [
        ("Grouper", "Ctrl+G"), ("Dissocier", "Ctrl+Maj+G"), ("Vectoriser le texte", "Ctrl+Maj+O"),
        ("Masque d'écrêtage", "Ctrl+7"), ("Tracé transparent composé", "Ctrl+8"),
        ("Afficher les règles", "Ctrl+R"), ("Afficher/masquer les repères", "Ctrl+;"),
        ("Verrouiller la sélection", "Ctrl+2")])
    pied(c)
    c.save()


def raccourcis_video():
    c = canvas.Canvas(str(OUT / "tobmaq-raccourcis-premiere-resolve.pdf"), pagesize=A4)
    c.setTitle("Raccourcis essentiels : Premiere Pro et DaVinci Resolve")
    c.setAuthor("TOB-MAQ")
    entete(c, "Raccourcis de montage", "Adobe Premiere Pro · DaVinci Resolve · CapCut (ordinateur)")
    note_mac(c, H - 125)
    y1 = tableau_raccourcis(c, 36, H - 160, "Premiere Pro", [
        ("Outil Sélection", "V"), ("Outil Cutter", "C"), ("Ajouter un point de montage", "Ctrl+K"),
        ("Raccourcir le début jusqu'à la tête de lecture", "Q"),
        ("Raccourcir la fin jusqu'à la tête de lecture", "W"),
        ("Lecture arrière / pause / avant", "J  K  L"), ("Point d'entrée / de sortie", "I  /  O"),
        ("Insérer / Recouvrir", ",  /  ."), ("Transition vidéo par défaut", "Ctrl+D"),
        ("Transition audio par défaut", "Ctrl+Maj+D"), ("Zoom avant / arrière (timeline)", "+  /  -"),
        ("Ajuster la séquence à la fenêtre", "\\"), ("Exporter le média", "Ctrl+M")])
    tableau_raccourcis(c, 36, y1, "CapCut (ordinateur)", [
        ("Lecture / pause", "Espace"), ("Diviser le clip", "Ctrl+B"), ("Annuler", "Ctrl+Z")])
    tableau_raccourcis(c, 309, H - 160, "DaVinci Resolve", [
        ("Mode sélection", "A"), ("Mode lame (Blade)", "B"), ("Couper à la tête de lecture", "Ctrl+B"),
        ("Lecture arrière / pause / avant", "J  K  L"), ("Point d'entrée / de sortie", "I  /  O"),
        ("Transition par défaut", "Ctrl+T"), ("Page Color : nœud en série", "Alt+S"),
        ("Page Color : activer/désactiver le nœud", "Ctrl+D")])
    pied(c)
    c.save()


def case(c, x, y):
    c.setStrokeColor(VIOLET)
    c.setLineWidth(1.2)
    c.roundRect(x, y - 2, 10, 10, 2, stroke=1, fill=0)
    c.setLineWidth(1)


def checklist_impression():
    c = canvas.Canvas(str(OUT / "tobmaq-checklist-impression.pdf"), pagesize=A4)
    c.setTitle("Checklist : préparer un fichier pour l'imprimeur")
    c.setAuthor("TOB-MAQ")
    entete(c, "Checklist prépresse", "Avant d'envoyer un fichier à l'imprimeur · affiches, flyers, brochures")
    sections = [
        ("Format et fonds perdus", [
            "Le format fini est celui demandé (ex. A5 = 148 × 210 mm, A4 = 210 × 297 mm).",
            "Les fonds perdus sont ajoutés tout autour (souvent 3 mm, à confirmer avec l'imprimeur).",
            "Les images et aplats de couleur qui touchent le bord vont jusqu'au fond perdu.",
            "Les textes et logos restent dans la zone de sécurité (souvent 3 à 5 mm du bord fini).",
            "Les traits de coupe sont présents si l'imprimeur les demande."]),
        ("Images et couleurs", [
            "Les images ont une résolution suffisante à 100 % (en général 300 ppp pour l'offset).",
            "Le mode colorimétrique et le profil sont ceux demandés par l'imprimeur (souvent CMJN).",
            "Les noirs de grands aplats suivent la consigne de l'imprimeur (noir enrichi ou non).",
            "Les petits textes noirs sont en noir 100 % seul, pour éviter les décalages."]),
        ("Textes et polices", [
            "Les polices sont incorporées dans le PDF ou vectorisées, avec une licence valide.",
            "L'orthographe, les numéros, dates, adresses et prix ont été relus par une autre personne.",
            "Aucun texte n'est trop petit pour être lisible une fois imprimé."]),
        ("Export final", [
            "Le PDF est exporté avec le préréglage demandé (ex. PDF/X-1a ou PDF/X-4).",
            "Les fonds perdus et repères sont inclus dans le PDF si nécessaire.",
            "Le fichier est nommé clairement : client_produit_format_version.pdf",
            "Un BAT (bon à tirer) a été validé par le client avant l'impression."])]
    y = H - 130
    for titre, items in sections:
        c.setFillColor(VIOLET)
        c.setFont("Sans-Bold", 12)
        c.drawString(36, y, titre)
        y -= 6
        for it in items:
            y -= 20
            case(c, 40, y)
            c.setFillColor(INK)
            c.setFont("Sans", 9.5)
            c.drawString(60, y, it)
        y -= 28
    c.setFillColor(ORANGE)
    c.setFont("Sans-Bold", 9)
    c.drawString(36, 60, "Règle d'or : les valeurs exactes (fonds perdus, profil, préréglage PDF) sont celles de votre imprimeur.")
    pied(c)
    c.save()


def brief_creatif():
    c = canvas.Canvas(str(OUT / "tobmaq-modele-brief-creatif.pdf"), pagesize=A4)
    c.setTitle("Modèle de brief créatif")
    c.setAuthor("TOB-MAQ")
    entete(c, "Brief créatif", "À remplir avec le client avant de commencer un projet graphique ou vidéo")
    champs = [
        ("Client et contact", 2), ("Projet (affiche, logo, vidéo, brochure…)", 2),
        ("Objectif : que doit-il se passer après avoir vu la création ?", 3),
        ("Public visé (âge, ville, habitudes)", 2), ("Message principal (une seule phrase)", 2),
        ("Contenus fournis (textes, logos, photos, rushes, musique)", 3),
        ("Contraintes : formats, dimensions, durée, couleurs, mentions obligatoires", 3),
        ("Références appréciées / à éviter", 2), ("Budget et délais (date du premier aperçu, date de livraison)", 2),
        ("Livrables finaux et formats de fichier", 2)]
    y = H - 125
    for label, lignes in champs:
        c.setFillColor(INK)
        c.setFont("Sans-Bold", 9.5)
        c.drawString(36, y, label)
        c.setStrokeColor(LINE)
        for i in range(lignes):
            y -= 17
            c.line(36, y, W - 36, y)
        y -= 20
    pied(c)
    c.save()


def grille_a4():
    c = canvas.Canvas(str(OUT / "tobmaq-grille-a4-12-colonnes.pdf"), pagesize=A4)
    c.setTitle("Fichier de départ : grille A4 12 colonnes")
    c.setAuthor("TOB-MAQ")
    marge_int, marge_ext, marge_haut, marge_bas = 15 * mm, 15 * mm, 15 * mm, 20 * mm
    gouttiere = 4 * mm
    zone_w = W - marge_int - marge_ext
    col_w = (zone_w - 11 * gouttiere) / 12
    c.setFillColor(HexColor("#FDECE5"))
    for i in range(12):
        x = marge_int + i * (col_w + gouttiere)
        c.rect(x, marge_bas, col_w, H - marge_haut - marge_bas, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#E6007E"))
    c.setLineWidth(0.6)
    c.rect(marge_int, marge_bas, zone_w, H - marge_haut - marge_bas, stroke=1, fill=0)
    # lignes de base tous les 12 pt
    c.setStrokeColor(HexColor("#BFE9F7"))
    c.setLineWidth(0.3)
    yy = H - marge_haut
    while yy > marge_bas:
        c.line(marge_int, yy, W - marge_ext, yy)
        yy -= 12
    c.setFillColor(MUTED)
    c.setFont("Mono", 6.5)
    c.drawString(marge_int, H - 9 * mm, "TOB-MAQ · Grille A4 (210 × 297 mm) · 12 colonnes · gouttière 4 mm · "
                                        "marges 15/15/15/20 mm · lignes de base 12 pt · fichier d'exercice")
    c.drawString(marge_int, 8 * mm, "Exercice : composez la une d'un magazine culturel en respectant cette grille. "
                                    "Imprimez-la ou placez-la en arrière-plan dans votre logiciel.")
    c.setFillColor(HexColor("#E6007E"))
    for i in range(12):
        c.drawCentredString(marge_int + i * (col_w + gouttiere) + col_w / 2, marge_bas - 10, str(i + 1))
    c.save()


def apercus():
    for pdf in sorted(OUT.glob("*.pdf")):
        base = PREV / pdf.stem
        subprocess.run(["pdftoppm", "-png", "-r", "40", "-f", "1", "-l", "1", "-singlefile", str(pdf), str(base)], check=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    PREV.mkdir(exist_ok=True)
    raccourcis_graphisme()
    raccourcis_video()
    checklist_impression()
    brief_creatif()
    grille_a4()
    apercus()
    for f in sorted(OUT.glob("*.pdf")):
        print(f"{f.name}  {f.stat().st_size // 1024} Ko")
    for f in sorted(PREV.glob("*.png")):
        print(f"{f.name}  {f.stat().st_size // 1024} Ko")
