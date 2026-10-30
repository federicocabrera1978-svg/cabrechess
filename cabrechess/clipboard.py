"""Copiar texto al portapapeles del sistema (FEN / PGN).

Prueba primero con ``pygame.scrap`` (SDL2) y, si no está disponible, con
tkinter. Nunca lanza excepciones: devuelve True si pudo copiar.
"""
import logging

log = logging.getLogger(__name__)


def _copy_pygame(text):
    import pygame
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return False
    scrap = pygame.scrap
    if not scrap.get_init():
        scrap.init()
    put_text = getattr(scrap, "put_text", None)
    if put_text is None:     # pygame viejo: API con tipos MIME
        scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
    else:
        put_text(text)
    return True


def _copy_tk(text):
    import tkinter
    root = tkinter.Tk()
    root.withdraw()
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()        # sin esto el texto se pierde al cerrar la ventana
    finally:
        root.destroy()
    return True


def copy_text(text, backends=None):
    """Copia ``text`` al portapapeles. Devuelve True si algún método funcionó."""
    for backend in backends or (_copy_pygame, _copy_tk):
        try:
            if backend(text):
                return True
        except Exception as e:  # noqa: BLE001 - el portapapeles depende del sistema
            log.debug("portapapeles: %s falló: %s", getattr(backend, "__name__", backend), e)
    return False
