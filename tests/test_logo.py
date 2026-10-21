"""El logo y el ícono existen y se cargan."""
from pathlib import Path


import cabrechess

LOGO = Path(__file__).resolve().parent.parent / "cabrechess" / "assets" / "logo"


def test_archivos_del_logo():
    for name in ("cabrechess.png", "cabrechess_64.png", "cabrechess.ico", "banner.png"):
        assert (LOGO / name).is_file(), name


def test_icono_de_ventana_se_carga(game):
    icon = cabrechess.load_window_icon()
    assert icon is not None
    assert icon.get_size() == (64, 64)


def test_ico_tiene_tamano_chico():
    # El .ico debe traer al menos 16 y 256 px para la barra de tareas y el explorador.
    data = (LOGO / "cabrechess.ico").read_bytes()
    count = int.from_bytes(data[4:6], "little")
    sizes = {data[6 + 16 * i] or 256 for i in range(count)}
    assert {16, 32, 48, 256} <= sizes
