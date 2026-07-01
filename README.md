# CabreChess

Un juego de ajedrez funcional inspirado en Lichess, hecho con `pygame` y `python-chess`.

## Ejecutar desde el código fuente

```
pip install -r requirements.txt
python cabrechess.py
```

## Descargar el ejecutable (Windows)

Los `.exe` se publican en [Releases](../../releases), junto con un archivo `.sha256`
para verificar que el archivo descargado es exactamente el que se generó a partir del
código fuente publicado en este repositorio (no uno modificado):

```powershell
Get-FileHash CabreChess.exe -Algorithm SHA256
```

Compará el resultado con el contenido de `CabreChess.exe.sha256`.

### Por qué Windows/antivirus puede marcarlo como sospechoso

El ejecutable no está firmado con un certificado de firma de código (requiere una
identidad verificada y tiene costo). Los `.exe` generados con PyInstaller sin firmar
son comúnmente marcados como falso positivo por SmartScreen o algunos antivirus,
simplemente porque ese empaquetado también es usado por malware. El release se genera
automáticamente desde este código fuente público mediante GitHub Actions
(ver `.github/workflows/release.yml`), por lo que cualquiera puede auditar exactamente
qué se compiló.

Este proyecto solicitó firma de código gratuita para proyectos open source a través de
[SignPath.io / SignPath Foundation](https://signpath.io/). Ver [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md)
para el detalle de procedencia, roles y estado.

## Build local

```
pip install -r requirements.txt
pyinstaller --onefile --windowed --name CabreChess cabrechess.py
```

## Licencia

GPL-3.0-or-later. Ver [LICENSE](LICENSE).
