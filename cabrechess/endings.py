# SPDX-License-Identifier: GPL-3.0-or-later
"""Textos de fin de partida (en castellano) a partir del motivo y el resultado."""
import chess

# Código de terminación -> (ícono, texto). {g} = "Ganan las blancas/negras".
_TEXTS = {
    "checkmate":    ("mate",  "¡Jaque mate! {g}"),
    "timeout":      ("clock", "{g} por tiempo"),
    "timeout_draw": ("clock", "Tablas por tiempo"),
    "stalemate":    ("draw",  "Tablas por ahogado"),
    "insufficient": ("draw",  "Tablas por material insuficiente"),
    "threefold":    ("draw",  "Tablas por triple repetición"),
    "fifty":        ("draw",  "Tablas por la regla de 50 movimientos"),
    "fivefold":     ("draw",  "Tablas por quíntuple repetición"),
    "seventyfive":  ("draw",  "Tablas por la regla de 75 movimientos"),
}
_SUBTITLES = {
    "timeout_draw": "Se acabó el tiempo, pero al rival no le alcanza el material",
}
# Valores estándar del tag PGN [Termination]
PGN_TERMINATION = {"timeout": "time forfeit", "timeout_draw": "time forfeit"}


def winner_text(result):
    return {"1-0": "Ganan las blancas", "0-1": "Ganan las negras"}.get(result, "")


def end_title(termination, result):
    """Frase principal, p. ej. "¡Jaque mate! Ganan las blancas"."""
    _icon, text = _TEXTS.get(termination, ("draw", "Partida terminada"))
    return text.format(g=winner_text(result)).strip()


def end_message(termination, result):
    """Mensaje para el panel: "icono\\ntítulo\\nsubtítulo"."""
    icon, _ = _TEXTS.get(termination, ("draw", ""))
    sub = _SUBTITLES.get(termination, f"Resultado: {result}")
    return f"{icon}\n{end_title(termination, result)}\n{sub}"


def detect_end(board):
    """(terminación, resultado) si la posición termina la partida, o None.
    Triple repetición y 50 movimientos se reclaman solas (como Lichess)."""
    if board.is_checkmate():
        return "checkmate", ("1-0" if board.turn == chess.BLACK else "0-1")
    if board.is_stalemate():
        return "stalemate", "1/2-1/2"
    if board.is_insufficient_material():
        return "insufficient", "1/2-1/2"
    if board.is_repetition(3):
        return "threefold", "1/2-1/2"
    if board.can_claim_fifty_moves():
        return "fifty", "1/2-1/2"
    if board.is_seventyfive_moves():
        return "seventyfive", "1/2-1/2"
    if board.is_fivefold_repetition():
        return "fivefold", "1/2-1/2"
    return None


def flag_end(board, flagged_color):
    """(terminación, resultado) cuando a `flagged_color` se le cae la bandera.
    Si el rival no puede dar mate de ninguna forma, es tablas (FIDE 6.9)."""
    rival = not flagged_color
    if board.has_insufficient_material(rival):
        return "timeout_draw", "1/2-1/2"
    return "timeout", ("1-0" if rival == chess.WHITE else "0-1")
