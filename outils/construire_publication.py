"""
Construit la version hébergée de TOB-MAQ (publication sur claude.ai) à partir
de index.html, et génère le QR code d'accès.

Usage :
  python3 outils/construire_publication.py              # -> publication/tob-maq.html
  python3 outils/construire_publication.py --qr <URL>   # + publication/qr-tob-maq.png

L'hébergeur ajoute lui-même <!doctype>, <html>, <head> et <body> : on les
retire ici et on active CONFIG.HOSTED (téléchargements via claude.ai).
Nécessite pour --qr : pip install qrcode pillow
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "publication"


def construire():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for motif in [r"<!DOCTYPE html>\s*", r'<html lang="fr">\s*', r"<head>\s*", r"</head>\s*", r"<body>\s*",
                  r"</body>\s*", r"</html>\s*", r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*']:
        html, n = re.subn(motif, "", html, count=1)
        assert n == 1, f"motif introuvable : {motif}"
    html = html.replace("<title>TOB-MAQ</title>", '<title>TOB-MAQ</title>\n<meta name="claude:viewport-fit-sides" content="cover">', 1)
    html, n = re.subn(r"HOSTED: false", "HOSTED: true", html, count=1)
    assert n == 1
    OUT.mkdir(exist_ok=True)
    cible = OUT / "tob-maq.html"
    cible.write_text(html, encoding="utf-8")
    print("Page construite :", cible, f"({cible.stat().st_size // 1024} Ko)")


def qr(url):
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    from PIL import Image, ImageDraw, ImageFont

    q = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=14, border=3)
    q.add_data(url)
    q.make(fit=True)
    code = q.make_image(fill_color="#0B0E17", back_color="white").convert("RGB")
    w, h = code.width + 120, code.height + 320
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 160], fill="#0B0E17")
    for i, c in enumerate(["#5B3DF5", "#A83BD8", "#F2612D"]):
        d.rectangle([i * w // 3, 160, (i + 1) * w // 3, 168], fill=c)

    def police(taille, gras=False):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if gras else "") + ".ttf", taille)
        except OSError:
            return ImageFont.load_default()

    def centre(y, txt, f, couleur):
        d.text(((w - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=couleur)

    centre(38, "TOB-MAQ", police(50, True), "white")
    centre(104, "Imagine. Crée. Maîtrise.", police(24), "#FF9A6B")
    img.paste(code, (60, 190))
    centre(code.height + 212, "Scanne pour ouvrir TOB-MAQ", police(28, True), "#0B0E17")
    centre(code.height + 258, "Graphisme · Maquettisme · Montage vidéo", police(21), "#545B6E")
    cible = OUT / "qr-tob-maq.png"
    img.save(cible)
    print("QR code :", cible)


if __name__ == "__main__":
    construire()
    if "--qr" in sys.argv:
        qr(sys.argv[sys.argv.index("--qr") + 1])
