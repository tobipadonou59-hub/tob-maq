"""Génère les icônes du site (onglet du navigateur, écran d'accueil du téléphone).

Motif : le « T » de TOB-MAQ dans les coins de cadrage orange du logo,
souligné du trait en dégradé violet → orange, sur le fond nuit.
Usage : python3 outils/generer_icones.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "icones"
NUIT, ENCRE, ORANGE = "#0B0E17", "#ECEEF5", "#FF7A45"
DEGRADE = [(0x5B, 0x3D, 0xF5), (0xA8, 0x3B, 0xD8), (0xF2, 0x61, 0x2D)]

# Géométrie sur une grille de 64 unités (reprise à l'identique dans le SVG).
COINS = [(10, 10, 1, 1), (54, 10, -1, 1), (10, 54, 1, -1), (54, 54, -1, -1)]
BRAS, EPAIS = 12, 4
T_BARRE = (18, 17, 46, 25)
T_PIED = (28, 17, 36, 43)
TRAIT = (22, 46, 42, 51)


def degrade(x, x0, x1):
    t = max(0.0, min(1.0, (x - x0) / (x1 - x0)))
    i, f = (0, t / 0.55) if t <= 0.55 else (1, (t - 0.55) / 0.45)
    a, b = DEGRADE[i], DEGRADE[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def dessiner(taille, plein=False):
    s = 16  # suréchantillonnage pour des bords nets après réduction
    n = taille * s
    u = n / 64
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = lambda b: [round(v * u) for v in b]
    if plein:  # icône d'écran d'accueil : carré plein, le système arrondit lui-même
        d.rectangle([0, 0, n, n], fill=NUIT)
    else:
        d.rounded_rectangle([0, 0, n - 1, n - 1], radius=round(14 * u), fill=NUIT)
    for x, y, dx, dy in COINS:
        xs = sorted([x, x + dx * BRAS]); ys = sorted([y, y + dy * EPAIS])
        d.rectangle(r([xs[0], ys[0], xs[1], ys[1]]), fill=ORANGE)
        xs = sorted([x, x + dx * EPAIS]); ys = sorted([y, y + dy * BRAS])
        d.rectangle(r([xs[0], ys[0], xs[1], ys[1]]), fill=ORANGE)
    d.rectangle(r(T_BARRE), fill=ENCRE)
    d.rectangle(r(T_PIED), fill=ENCRE)
    x0, y0, x1, y1 = r(TRAIT)
    for x in range(x0, x1):
        d.line([(x, y0), (x, y1)], fill=degrade(x, x0, x1))
    return img.resize((taille, taille), Image.LANCZOS)


def svg():
    coins = []
    for x, y, dx, dy in COINS:
        coins.append(f"M{x} {y + dy * BRAS}V{y}H{x + dx * BRAS}V{y + dy * EPAIS}H{x + dx * EPAIS}V{y + dy * BRAS}Z")
    rect = lambda b, f: f'<rect x="{b[0]}" y="{b[1]}" width="{b[2]-b[0]}" height="{b[3]-b[1]}" fill="{f}"/>'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#5B3DF5"/>'
        '<stop offset=".55" stop-color="#A83BD8"/><stop offset="1" stop-color="#F2612D"/></linearGradient></defs>'
        f'<rect width="64" height="64" rx="14" fill="{NUIT}"/>'
        f'<path fill="{ORANGE}" d="{"".join(coins)}"/>'
        + rect(T_BARRE, ENCRE) + rect(T_PIED, ENCRE) + rect(TRAIT, "url(#g)") + "</svg>\n"
    )


if __name__ == "__main__":
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "favicon.svg").write_text(svg(), encoding="utf-8")
    dessiner(32).save(SORTIE / "favicon-32.png", optimize=True)
    dessiner(48).save(SORTIE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    dessiner(180, plein=True).convert("RGB").save(SORTIE / "apple-touch-icon.png", optimize=True)
    dessiner(512).save(SORTIE / "icone-512.png", optimize=True)
    print("Icônes écrites dans", SORTIE)
