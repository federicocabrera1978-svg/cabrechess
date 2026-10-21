# SPDX-License-Identifier: GPL-3.0-or-later
"""Sprites de piezas: set cburnett (PNG) con respaldo dibujado en código, e ícono."""
import math
import sys
from pathlib import Path

import chess
import pygame

# ─── PIEZAS DIBUJADAS EN CÓDIGO (RESPALDO) ──────────────────────────────────────
# Usadas solo si faltan los PNG de assets/pieces/cburnett/. Se arman a 4x y se
# reducen con smoothscale (anti-aliasing). Estilo marfil / grafito.
PIECE_SUPERSAMPLE = 4
PIECE_STYLE = {
    # color de pieza: (relleno claro, relleno oscuro, contorno, brillo)
    chess.WHITE: ((255, 255, 252), (206, 204, 196), (34, 32, 30), (255, 255, 255, 150)),
    chess.BLACK: ((92, 88, 84), (22, 21, 20), (8, 8, 8), (255, 255, 255, 70)),
}
_piece_cache = {}


def _ellipse(ex, ey, rx, ry, start=0.0, end=2 * math.pi, n=64):
    return [(ex + rx * math.cos(start + (end - start) * i / n),
             ey + ry * math.sin(start + (end - start) * i / n))
            for i in range(n + 1)]


def _mirror(cx, pts):
    return pts + [(2 * cx - x, y) for (x, y) in pts][::-1]


def _profile(s, pts):
    """Perfil simétrico: pts = [(yf, half_f), ...] de arriba hacia abajo."""
    cx = s / 2
    left = [(cx - hf * s, yf * s) for (yf, hf) in pts]
    return _mirror(cx, left)


def _base(s, w=0.275):
    cx = s / 2
    return (_ellipse(cx, 0.745 * s, w * s, 0.03 * s, math.pi, 2 * math.pi)
            + _ellipse(cx, 0.815 * s, w * s, 0.035 * s, 0, math.pi))


def _band(s, yc, half, ry=0.040):
    return _ellipse(s / 2, yc * s, half * s, ry * s)


def _pawn_parts(s):
    """Partes del peón (base, cuerpo, collar, cabeza)."""
    cx = s / 2
    top_y, bot_y = 0.44 * s, 0.76 * s
    left, right = [], []
    for i in range(33):
        t = i / 32
        half = (0.078 + 0.165 * t ** 1.9) * s
        y = top_y + (bot_y - top_y) * t
        left.append((cx - half, y))
        right.append((cx + half, y))
    body = left + _ellipse(cx, bot_y, 0.243 * s, 0.035 * s, 0, math.pi)[::-1] + right[::-1]
    return [_base(s), body, _band(s, 0.445, 0.160),
            _ellipse(cx, 0.300 * s, 0.128 * s, 0.128 * s)]


def _king_parts(s):
    cx = s / 2
    body = _profile(s, [
        (0.42, 0.095), (0.46, 0.088), (0.52, 0.132), (0.58, 0.112),
        (0.66, 0.135), (0.71, 0.185), (0.748, 0.235),
    ])
    head = _profile(s, [
        (0.235, 0.045), (0.255, 0.095), (0.295, 0.125), (0.345, 0.122),
        (0.40, 0.100), (0.43, 0.078),
    ])
    cross_v = [
        (cx - 0.027 * s, 0.050 * s), (cx + 0.027 * s, 0.050 * s),
        (cx + 0.027 * s, 0.250 * s), (cx - 0.027 * s, 0.250 * s),
    ]
    cross_h = [
        (cx - 0.082 * s, 0.100 * s), (cx + 0.082 * s, 0.100 * s),
        (cx + 0.082 * s, 0.152 * s), (cx - 0.082 * s, 0.152 * s),
    ]
    return [_base(s, 0.285), body, _band(s, 0.425, 0.150), head, cross_v, cross_h]


def _queen_parts(s):
    cx = s / 2
    body = _profile(s, [
        (0.40, 0.100), (0.45, 0.090), (0.52, 0.130), (0.60, 0.110),
        (0.67, 0.140), (0.71, 0.190), (0.748, 0.240),
    ])
    head = _profile(s, [
        (0.305, 0.085), (0.325, 0.140), (0.355, 0.150), (0.39, 0.130),
    ])
    crownband = _profile(s, [(0.275, 0.150), (0.305, 0.150)])
    parts = [_base(s, 0.285), body, _band(s, 0.405, 0.150), head, crownband]
    offs = (-0.118, -0.059, 0.0, 0.059, 0.118)
    for ox in offs:
        tipx = cx + ox * s
        parts.append([
            (tipx - 0.030 * s, 0.278 * s),
            (tipx + 0.030 * s, 0.278 * s),
            (tipx, 0.205 * s),
        ])
    for ox in offs:
        parts.append(_ellipse(cx + ox * s, 0.198 * s, 0.030 * s, 0.030 * s))
    return parts


def _rook_parts(s):
    cx = s / 2
    body = _profile(s, [
        (0.47, 0.165), (0.51, 0.150), (0.60, 0.150), (0.66, 0.170),
        (0.71, 0.205), (0.748, 0.250),
    ])
    left, right = cx - 0.205 * s, cx + 0.205 * s
    merlon_top, gap_bot, block_bot = 0.345 * s, 0.395 * s, 0.475 * s
    n_merlons = 4
    seg = (right - left) / (2 * n_merlons - 1)
    battlement = [(left, block_bot), (left, gap_bot)]
    cur = left
    for k in range(2 * n_merlons - 1):
        top = merlon_top if k % 2 == 0 else gap_bot
        battlement.append((cur, top))
        battlement.append((cur + seg, top))
        cur += seg
    battlement.append((right, block_bot))
    return [_base(s, 0.285), body, _band(s, 0.505, 0.175), battlement]


def _bishop_parts(s):
    cx = s / 2
    body = _profile(s, [
        (0.46, 0.085), (0.52, 0.112), (0.60, 0.118), (0.66, 0.150),
        (0.71, 0.180), (0.748, 0.215),
    ])
    mitre = _profile(s, [
        (0.175, 0.012), (0.21, 0.058), (0.27, 0.100), (0.33, 0.125),
        (0.40, 0.112), (0.455, 0.078),
    ])
    ball = _ellipse(cx, 0.165 * s, 0.032 * s, 0.032 * s)
    slit = [
        (cx - 0.055 * s, 0.285 * s), (cx - 0.030 * s, 0.265 * s),
        (cx + 0.060 * s, 0.360 * s), (cx + 0.035 * s, 0.380 * s),
    ]
    return [_base(s, 0.270), body, _band(s, 0.455, 0.135), mitre, ball,
            ("outline", slit)]


def _knight_parts(s):
    neck = _profile(s, [
        (0.58, 0.150), (0.64, 0.170), (0.71, 0.205), (0.748, 0.250),
    ])
    # Silueta del caballo mirando a la izquierda
    pts = [
        (0.315, 0.705), (0.30, 0.615), (0.285, 0.535), (0.255, 0.49),
        (0.215, 0.465), (0.175, 0.455), (0.135, 0.455), (0.115, 0.425),
        (0.115, 0.395), (0.145, 0.375), (0.135, 0.345), (0.175, 0.345),
        (0.215, 0.335), (0.245, 0.305), (0.265, 0.27), (0.30, 0.235),
        (0.345, 0.195), (0.375, 0.155), (0.405, 0.205), (0.435, 0.225),
        (0.465, 0.175), (0.505, 0.205), (0.545, 0.27), (0.58, 0.355),
        (0.61, 0.455), (0.63, 0.56), (0.64, 0.665), (0.59, 0.705),
    ]
    horse = [(x * s, y * s) for (x, y) in pts]
    eye = _ellipse(0.315 * s, 0.295 * s, 0.019 * s, 0.019 * s)
    nostril = _ellipse(0.155 * s, 0.405 * s, 0.013 * s, 0.013 * s)
    return [_base(s, 0.285), neck, horse, ("outline", eye), ("outline", nostril)]


_PIECE_PARTS = {
    chess.PAWN: _pawn_parts,
    chess.KING: _king_parts,
    chess.QUEEN: _queen_parts,
    chess.ROOK: _rook_parts,
    chess.BISHOP: _bishop_parts,
    chess.KNIGHT: _knight_parts,
}

_PIECE_SHINE = {
    chess.PAWN: [(0.425, 0.225, 0.075, 0.05)],
    chess.KING: [(0.40, 0.26, 0.07, 0.05)],
    chess.QUEEN: [(0.40, 0.33, 0.07, 0.05)],
    chess.ROOK: [(0.37, 0.40, 0.07, 0.05)],
    chess.BISHOP: [(0.40, 0.27, 0.06, 0.05)],
    chess.KNIGHT: [(0.33, 0.33, 0.06, 0.05)],
}


def _make_piece_sprite_drawn(piece_type, color, size):
    """Pieza dibujada por codigo (respaldo si faltan las imagenes cburnett)."""
    s = size * PIECE_SUPERSAMPLE
    light, dark, outline, shine = PIECE_STYLE[color]
    stroke = max(2, round(s * 0.020))

    grad = pygame.Surface((s, s), pygame.SRCALPHA)
    for x in range(s):
        t = min(1.0, max(0.0, (x / s - 0.30) / 0.45))
        c = [round(light[i] + (dark[i] - light[i]) * t) for i in range(3)]
        pygame.draw.line(grad, (*c, 255), (x, 0), (x, s))

    big = pygame.Surface((s, s), pygame.SRCALPHA)
    for part in _PIECE_PARTS[piece_type](s):
        if isinstance(part, tuple) and part[0] == "outline":
            poly = part[1]
            pygame.draw.polygon(big, outline, poly)
            pygame.draw.lines(big, outline, True, poly, stroke)
            continue
        poly = part
        pygame.draw.polygon(big, outline, poly)
        pygame.draw.lines(big, outline, True, poly, stroke * 2)
        for p in poly[::4]:
            pygame.draw.circle(big, outline, p, stroke)
        mask = pygame.Surface((s, s), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
        pygame.draw.lines(mask, (0, 0, 0, 0), True, poly, stroke * 2)
        fill = grad.copy()
        fill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        big.blit(fill, (0, 0))

    hl = pygame.Surface((s, s), pygame.SRCALPHA)
    for (hx, hy, hrx, hry) in _PIECE_SHINE.get(piece_type, []):
        pygame.draw.ellipse(hl, shine, pygame.Rect(hx * s, hy * s, hrx * s, hry * s))
    big.blit(hl, (0, 0))

    return pygame.transform.smoothscale(big, (size, size))


# ─── PIEZAS CBURNETT (LICHESS) ────────────────────────────────────────────────
# Set de piezas "cburnett" de Colin M.L. Burnett, el mismo que usa Lichess.
# Licencia GPLv2+ (ver cabrechess/assets/pieces/cburnett/LICENSE).
# Las imagenes viven en cabrechess/assets/pieces/cburnett/*.png (SVG a 256px).
def assets_dir():
    """Carpeta assets/ del paquete: dentro del paquete instalado / del repo,
    o dentro del bundle PyInstaller (que la copia a cabrechess/assets)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "cabrechess" / "assets"
    return Path(__file__).resolve().parent / "assets"


ASSETS_DIR = assets_dir()
_ASSETS_DIR = ASSETS_DIR / "pieces" / "cburnett"
_LOGO_DIR = ASSETS_DIR / "logo"


def load_window_icon():
    """Superficie con el ícono de CabreChess, o None si no está el archivo."""
    for name in ("cabrechess_64.png", "cabrechess.png"):
        path = _LOGO_DIR / name
        if path.is_file():
            try:
                return pygame.image.load(str(path))
            except pygame.error:
                continue
    return None
_CBURNETT_FILE = {
    (chess.KING,   chess.WHITE): "wK.png",
    (chess.QUEEN,  chess.WHITE): "wQ.png",
    (chess.ROOK,   chess.WHITE): "wR.png",
    (chess.BISHOP, chess.WHITE): "wB.png",
    (chess.KNIGHT, chess.WHITE): "wN.png",
    (chess.PAWN,   chess.WHITE): "wP.png",
    (chess.KING,   chess.BLACK): "bK.png",
    (chess.QUEEN,  chess.BLACK): "bQ.png",
    (chess.ROOK,   chess.BLACK): "bR.png",
    (chess.BISHOP, chess.BLACK): "bB.png",
    (chess.KNIGHT, chess.BLACK): "bN.png",
    (chess.PAWN,   chess.BLACK): "bP.png",
}
_cburnett_raw = {}  # (piece_type, color) -> Surface RGBA a resolucion nativa


def _load_cburnett_raw(piece_type, color):
    key = (piece_type, color)
    if key in _cburnett_raw:
        return _cburnett_raw[key]
    path = _ASSETS_DIR / _CBURNETT_FILE[key]
    if not path.is_file():
        _cburnett_raw[key] = None
        return None
    img = pygame.image.load(str(path)).convert_alpha()
    _cburnett_raw[key] = img
    return img


def make_piece_sprite(piece_type, color, size):
    """Superficie RGBA de size x size con la pieza del color pedido (cacheada).

    Preferencia: PNG del set cburnett (Lichess). Si falta el archivo, se cae
    al dibujo procedural anterior para no romper el juego.
    """
    key = (piece_type, color, size)
    if key in _piece_cache:
        return _piece_cache[key]
    raw = _load_cburnett_raw(piece_type, color)
    if raw is not None:
        if raw.get_width() == size and raw.get_height() == size:
            sprite = raw
        else:
            sprite = pygame.transform.smoothscale(raw, (size, size))
    else:
        sprite = _make_piece_sprite_drawn(piece_type, color, size)
    _piece_cache[key] = sprite
    return sprite


def make_piece_shadow(piece_type, size, alpha=110):
    """Sombra suave de la pieza (silueta negra semitransparente)."""
    key = ("shadow", piece_type, size, alpha)
    if key in _piece_cache:
        return _piece_cache[key]
    shadow = make_piece_sprite(piece_type, chess.WHITE, size).copy()
    shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
    shadow.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    _piece_cache[key] = shadow
    return shadow


def make_pawn_sprite(color, size):
    """Compat: peón del color pedido."""
    return make_piece_sprite(chess.PAWN, color, size)


def make_pawn_shadow(size, alpha=110):
    """Compat: sombra del peón."""
    return make_piece_shadow(chess.PAWN, size, alpha)


PIECE_NAMES = {
    chess.PAWN: 'Peón', chess.KNIGHT: 'Caballo', chess.BISHOP: 'Alfil',
    chess.ROOK: 'Torre', chess.QUEEN: 'Reina', chess.KING: 'Rey',
}
