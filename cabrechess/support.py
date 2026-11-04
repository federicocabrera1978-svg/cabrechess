# SPDX-License-Identifier: GPL-3.0-or-later
"""Apoyar el proyecto en Ko-fi.

- ``open_kofi()`` abre la página de Ko-fi en el navegador del sistema. El
  módulo ``webbrowser`` se importa recién al hacer click (nunca al arrancar), así
  el juego sigue sin cargar nada que lance procesos mientras nadie lo pide.
- ``should_prompt()`` decide si después de una partida terminada se muestra el
  aviso discreto: como mucho una vez cada N partidas (``support_prompt_every``
  en settings.json; 0 lo apaga).
"""
import logging

log = logging.getLogger(__name__)

KOFI_URL = "https://ko-fi.com/federicocabrera"


def open_kofi(opener=None):
    """Abre KOFI_URL en el navegador. Nunca lanza excepciones: devuelve True si
    el sistema aceptó abrirla. ``opener`` permite inyectar uno en los tests."""
    try:
        if opener is None:
            import webbrowser  # diferido: solo cuando el usuario hace click
            opener = webbrowser.open
        return bool(opener(KOFI_URL))
    except Exception:  # noqa: BLE001 - sin navegador, entorno raro, etc.
        log.exception("No se pudo abrir %s", KOFI_URL)
        return False


def should_prompt(games_finished, every):
    """True si toca mostrar el aviso tras ``games_finished`` partidas
    terminadas (contando la actual). ``every`` <= 0 lo desactiva."""
    try:
        every = int(every)
        games_finished = int(games_finished)
    except (TypeError, ValueError):
        return False
    return every > 0 and games_finished > 0 and games_finished % every == 0
