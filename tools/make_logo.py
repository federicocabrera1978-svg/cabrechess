"""Genera el logo y los íconos de CabreChess en cabrechess/assets/logo/.

Uso (solo para desarrollo, necesita Pillow):

    pip install pillow
    python tools/make_logo.py

Arma el ícono a partir del caballo blanco del set cburnett
(cabrechess/assets/pieces/cburnett/wN.png, GPLv2+) sobre un cuadrado redondeado con
casillas en los tonos clásicos de Lichess. Escribe:

- cabrechess/assets/logo/cabrechess.png      ícono 512x512 (README, ventana)
- cabrechess/assets/logo/cabrechess_64.png   ícono 64x64 (ícono de la ventana de pygame)
- cabrechess/assets/logo/cabrechess.ico      multi-tamaño 16-256 (ejecutable de Windows)
- cabrechess/assets/logo/banner.png          logo + nombre para el README
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cabrechess" / "assets" / "logo"
KNIGHT = ROOT / "cabrechess" / "assets" / "pieces" / "cburnett" / "wN.png"
FONT = Path("/usr/share/fonts/truetype/sand-box/google/Montserrat/"
            "Montserrat-VariableFont_wght.ttf")

LIGHT = (240, 217, 181)   # casilla clara Lichess
DARK = (181, 136, 99)     # casilla oscura Lichess
DEEP = (92, 58, 33)       # borde
S = 1024                  # se dibuja grande y se reduce (anti-aliasing)


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    return m


def make_icon():
    radius = int(S * 0.22)
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Fondo: 2x2 casillas
    board = Image.new("RGBA", (S, S), LIGHT + (255,))
    d = ImageDraw.Draw(board)
    h = S // 2
    d.rectangle((h, 0, S, h), fill=DARK + (255,))
    d.rectangle((0, h, h, S), fill=DARK + (255,))
    # leve viñeta para dar profundidad
    vign = Image.new("L", (S, S), 0)
    ImageDraw.Draw(vign).ellipse((-S * 0.25, -S * 0.25, S * 1.25, S * 1.25), fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(S * 0.12))
    shade = Image.new("RGBA", (S, S), (40, 22, 10, 255))
    board = Image.composite(board, shade, vign.point(lambda v: 150 + v * 105 // 255))
    # Borde: cuadrado redondeado oscuro y, adentro, las casillas (sin que
    # asome el tablero por fuera del borde en los tamaños chicos)
    ImageDraw.Draw(base).rounded_rectangle((0, 0, S - 1, S - 1), radius, fill=DEEP + (255,))
    b = 30
    inner = _rounded_mask(S - 2 * b, radius - b)
    base.paste(board.crop((b, b, S - b, S - b)), (b, b), inner)

    # Caballo con sombra
    kn_size = int(S * 0.86)
    knight = Image.open(KNIGHT).convert("RGBA").resize((kn_size, kn_size), Image.LANCZOS)
    off = ((S - kn_size) // 2, (S - kn_size) // 2 - int(S * 0.015))
    alpha = knight.split()[3]
    shadow = Image.new("RGBA", knight.size, (20, 10, 0, 0))
    shadow.putalpha(alpha.point(lambda v: v * 150 // 255))
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.018))
    base.alpha_composite(shadow, (off[0] + int(S * 0.025), off[1] + int(S * 0.035)))
    base.alpha_composite(knight, off)
    return base


def make_banner(icon):
    h = 360
    ic = icon.resize((h - 40, h - 40), Image.LANCZOS)
    font = ImageFont.truetype(str(FONT), 170)
    try:
        font.set_variation_by_name("ExtraBold")
    except (OSError, AttributeError):  # fuente no variable / sin libraqm
        pass
    small = ImageFont.truetype(str(FONT), 46)
    try:
        small.set_variation_by_name("Medium")
    except (OSError, AttributeError):  # fuente no variable / sin libraqm
        pass
    title, sub = "CabreChess", "Ajedrez en Python, inspirado en Lichess"
    tw = int(font.getlength(title))
    sw = int(small.getlength(sub))
    w = 20 + ic.width + 50 + max(tw, sw) + 40
    banner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    banner.alpha_composite(ic, (20, 20))
    d = ImageDraw.Draw(banner)
    x = 20 + ic.width + 50
    d.text((x, 52), "Cabre", font=font, fill=DARK + (255,))
    d.text((x + int(font.getlength("Cabre")), 52), "Chess", font=font, fill=(110, 110, 110, 255))
    d.text((x + 6, 250), sub, font=small, fill=(128, 128, 128, 255))
    return banner


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.resize((512, 512), Image.LANCZOS).save(OUT / "cabrechess.png", optimize=True)
    icon.resize((64, 64), Image.LANCZOS).save(OUT / "cabrechess_64.png", optimize=True)
    icon.resize((256, 256), Image.LANCZOS).save(
        OUT / "cabrechess.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    make_banner(icon).save(OUT / "banner.png", optimize=True)
    print("Logo generado en", OUT)


if __name__ == "__main__":
    main()
