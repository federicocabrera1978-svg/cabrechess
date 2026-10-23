# Changelog

Todos los cambios importantes de CabreChess se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Unreleased]

## [1.1.0] - 2026-10-23

Primera versión publicada.

### Versión
- La versión sale de un solo lugar (`cabrechess/_version.py`): el menú, el
  paquete y el `.exe` muestran 1.1.0 (antes el menú decía "v1.0.0" a mano y el
  paquete 0.1.0).
- El release de GitHub publica como notas la sección de esta versión del
  CHANGELOG y falla si la etiqueta no coincide con la versión del código.

### Temas de tablero
- Cuatro **temas de tablero** con los colores de Lichess: Marrón (el de siempre),
  Azul, Verde y Gris. Las piezas siguen siendo las cburnett.
- Tecla **`T`** para pasar al siguiente tema; muestra el nombre en un aviso y se
  recuerda en `settings.json` (`"board_theme": "marron" | "azul" | "verde" | "gris"`).
- Las letras y números de las coordenadas usan los colores del tema elegido.
- Un valor desconocido en `settings.json` vuelve al tema Marrón.

### Abandonar y tablas
- Botones **Abandonar** (bandera, con confirmación) y **Ofrecer tablas** (½) en
  el panel, solo durante una partida vs IA o de 2 jugadores.
- Contra la IA, la oferta se acepta si la IA va perdiendo por 1 peón o más, o si
  la posición está pareja (±0,3) desde la jugada 30; si no, "La IA rechaza las
  tablas". En 2 jugadores, el rival acepta o rechaza en un diálogo.
- Una oferta por jugada: después de un rechazo hay que mover para volver a ofrecer.
- Nuevos carteles "Ganan las blancas/negras por abandono" y "Tablas por acuerdo";
  se guardan en la base de partidas y en el PGN con el resultado correcto.
- Los botones del panel tienen una sola definición para dibujar y para los clicks
  (antes estaban duplicados).

### Sonidos
- **Sonidos** al mover, capturar, enrocar, dar jaque y al terminar la partida
  (mate, ahogado, tiempo o tablas), más un aviso cuando a tu reloj le quedan
  10 segundos. Se sintetizan dentro del juego: no hay archivos de audio ni
  licencias de terceros.
- Tecla **`M`** para silenciar o reactivar el sonido; la preferencia se guarda
  en `settings.json` (`"sound": true/false`).
- Al abrir una partida guardada no suena nada mientras se reconstruye.
- Sin dispositivo de audio el juego sigue funcionando en silencio.

### Partidas guardadas, análisis y relojes
- **Relojes congelados** al terminar la partida, por cualquier motivo: un único
  `end_game()` guarda los tiempos finales, y la jugada que termina la partida ya
  no suma incremento.
- **Barra de revisión siempre visible** al cerrar el panel o elegir
  "Revisar / Analizar" (antes recién aparecía al retroceder una jugada).
- **Carteles de resultado** claros: "¡Jaque mate! Ganan las blancas", "Ganan las
  negras por tiempo", "Tablas por ahogado / triple repetición / regla de 50
  movimientos / material insuficiente"…
- **Base de partidas** (SQLite) con autoguardado de cada partida terminada y
  pantalla **Partidas guardadas** (abrir en análisis, exportar PGN, borrar).
- **Mejor jugada** en análisis/revisión (flecha + SAN + evaluación), calculada en
  segundo plano con el motor propio. Stockfish opcional vía `settings.json`.
- PGN: `[Result]` correcto en derrotas por tiempo, `[Termination]`,
  `[TimeControl]`, y `[SetUp]/[FEN]` si la partida no arrancó de la posición inicial.

### Análisis post-partida
- Con la partida terminada, **deshacer ya no deshace jugadas ni devuelve
  tiempo**: resultado y relojes quedan congelados. El botón ← y `Ctrl+Z` solo
  retroceden en la revisión (junto con `|< < > >|` y las flechas).
  Se elimina el comportamiento anterior "deshacer después del mate reabre la partida".
- Panel de fin de partida: **Guardar PGN** y **Revisar / Analizar**.
- En la revisión se muestra la barra de evaluación de la posición mirada
  (en cualquier modo) y el nombre de la apertura (ECO).

### Agregado
- **Nombre de la apertura** (código ECO + nombre en castellano) arriba de la
  lista de jugadas, también al revisar la partida. Se busca por posición, así
  que reconoce transposiciones. El PGN exportado suma los headers `ECO` y
  `Opening`.
- **Panel de fin de partida** con resultado y opciones: Guardar PGN, Revisar
  partida, Nueva partida y Cerrar. `Esc` lo cierra y deja ver el tablero final;
  el botón "Resultado" lo vuelve a abrir.
- **Revisión de la partida terminada**: navegar jugada por jugada con `←` `→`
  `Inicio` `Fin` o la barra `|< < > >|`; se resalta la jugada en la lista.
- **Ventana redimensionable**, maximizable y **pantalla completa con F11**. El
  juego se escala manteniendo la proporción (con barras negras) y el mouse se
  mapea bien a cualquier tamaño. Tamaño mínimo 770x546.
- Guardar PGN sin tkinter: si no hay diálogo de archivo, se guarda en
  `~/Documents/CabreChess/CabreChess_AAAAMMDD_HHMMSS.pgn`.

### Corregido
- Builds de Windows sin UPX (fuente común de falsos positivos de antivirus) y
  nuevo build **onedir** (`CabreChess-win64.zip`, `CabreChess-onedir.spec`)
  que no se autoextrae a `%TEMP%`; CI y release publican ambos formatos.
- Test que garantiza que el paquete no lanza subprocesos ni usa red, registro
  o motores externos (el análisis es 100% en el proceso).
- Al terminar la partida aparecía un menú que no se podía cerrar.
- Windows: el proceso declara DPI awareness (no más ventana borrosa o
  limitada con escalado 125/150%); tamaño inicial según el escritorio;
  pantalla completa a la resolución del escritorio; también `Alt+Enter`.
- Se maneja `WINDOWSIZECHANGED` además de `VIDEORESIZE`.
- `Esc` con la partida terminada ya no vuelve al menú (borraba la partida):
  reabre el panel.
- Medio segundo de gracia antes de aceptar clicks en el panel de fin de
  partida, para que el click de la última jugada no toque "Nueva partida".
- Triple repetición y regla de 50 movimientos terminan la partida (como Lichess).
- Si se cae la bandera mientras piensa la IA, se cancela la búsqueda.

### Cambiado
- `cabrechess.py` se partió en el paquete `cabrechess/` (`constants`, `engine`,
  `clock`, `pgn`, `sprites`, `ui`, `__main__`) sin cambiar el comportamiento.
  Se ejecuta con `cabrechess` o `python -m cabrechess`.
- `assets/` se movió a `cabrechess/assets/` y se declara como package data:
  `pip install .` (no editable) ya trae las piezas y el logo.
- PyInstaller arranca desde `packaging_entry.py` y empaqueta `cabrechess/assets`.
- CI: chequeo de `pip install .` fuera del repo y build del `.exe` con el spec.
- Tests nuevos de `clock`, `pgn` y ubicación de assets.

### Pulido para portfolio
- README reescrito: funcionalidades, controles, requisitos, badges, capturas y
  sección en inglés. Capturas de desarrollo movidas a `docs/screenshots/dev/`.
- CI (`.github/workflows/ci.yml`): ruff + pytest en Ubuntu y Windows.
- `pyproject.toml` con el comando `cabrechess` y configuración de ruff;
  `requirements-dev.txt` separado (pyinstaller, pytest, ruff).
- Tests nuevos: el motor encuentra mates en 1, nunca devuelve jugadas ilegales,
  y el PGN exportado se vuelve a leer con `chess.pgn`.
- `.github/FUNDING.yml` como plantilla comentada.

### Corregido
- Elección de fuente: `SysFont` nunca falla, así que ahora se verifica con
  `match_font` que la fuente esté instalada.
- Acceso al resultado de la IA protegido con un lock entre el hilo de búsqueda
  y el loop principal (`cancel_ai_search`).
- `except:` pelados reemplazados por excepciones concretas.
- Docstring de `SimpleEngine` que mencionaba Stockfish (no se usa).
- Imports y variables sin usar; PGN separado en `build_pgn()` (testeable).

### Agregado
- Elegir color contra la IA desde el menú: **Blancas**, **Negras** o **Azar**.
  Si jugás con negras, el tablero se gira solo y la IA hace la primera jugada.
- Íconos dibujados con primitivas de pygame (reiniciar, girar, deshacer,
  guardar, menú, análisis, reloj, tablas y mate): ya no dependen de la fuente
  del sistema.
- Set de piezas **cburnett** (Lichess / Colin M.L. Burnett, GPLv2+): 12 PNG
  en `assets/pieces/cburnett/` (convertidos desde los SVG oficiales). Créditos
  y licencia en `assets/pieces/cburnett/LICENSE`.
- **Logo e ícono de CabreChess** (caballo cburnett sobre casillas en los tonos
  de Lichess) en `assets/logo/`: ícono de la ventana, ícono del `.exe` (`.ico`
  de 16 a 256 px) y banner del README. Se regeneran con `tools/make_logo.py`.
- Metadatos de versión del `.exe` de Windows (`version_info.txt`): nombre,
  descripción, versión y licencia en Propiedades > Detalles.
- Primeros tests automáticos con `pytest` en `tests/` (reloj y deshacer),
  que corren sin pantalla.

### Cambiado
- Todas las piezas del tablero, arrastre, animación, fantasma de premove,
  franja de capturadas, menú de promoción, paneles de jugador e íconos del
  menú usan ahora el set cburnett (escalado con `smoothscale`). Si faltan
  los PNG, se cae al dibujo procedural anterior como respaldo.
- Peones, rey, dama, torre, alfil y caballo dibujados en código quedan como
  fallback (contorno, degradé marfil/grafito, brillo y sombra).
- El incremento del reloj se suma en todas las jugadas, también en la
  primera, y ya no tiene el tope de "tiempo inicial + 60 s".

### Corregido
- El workflow de release compilaba con `pyinstaller cabrechess.py` y dejaba
  afuera la carpeta `assets/`: el `.exe` publicado no traía las piezas
  cburnett. Ahora compila con `CabreChess.spec`.
- Los íconos 💾 (Guardar), ⬜/⬛ (Turno) y ⏱/⚖ (fin de partida) se veían como
  rectángulos vacíos.
- Las letras de columna a–h no se veían: se dibujaban con el mismo color que la
  casilla y debajo de las piezas. Ahora las coordenadas van encima de las piezas
  y con el color contrario a la casilla.
- Textos superpuestos en el menú: "Dificultad IA:" y "Tiempo:" quedaban tapados
  por los botones. Ahora las etiquetas tienen su propia columna y el dibujo y
  los clics usan el mismo layout.
- El "+0" de la barra de evaluación se pisaba con el panel del jugador.
- Los paneles de jugador siguen al tablero cuando se gira.
- El reloj ya no se congela mientras piensa la IA: la IA gasta su propio
  tiempo y puede perder por tiempo. Si se le cae la bandera, no mueve después.
- Si se reinicia o se deshace mientras la IA piensa, el resultado viejo de la
  búsqueda se descarta.
- Deshacer (`Ctrl+Z` o el botón ←) ahora restaura todo: relojes, piezas
  capturadas, evaluación y gráfico del modo Análisis, y borra premoves y
  partículas pendientes. Antes las capturas y los relojes quedaban como
  estaban.
- Deshacer también funciona mientras la IA piensa: cancela la búsqueda y
  vuelve a tu jugada. En vs IA siempre vuelve hasta que te toca a vos (también
  jugando con negras).
- Si a un jugador se le acaba el tiempo y el rival no tiene material para dar
  mate (por ejemplo, rey solo), la partida es **tablas** y no victoria
  (regla FIDE 6.9).
- Las partículas de jaque no aparecían si el rey estaba en a1.

[Unreleased]: https://github.com/federicocabrera1978-svg/cabrechess/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/federicocabrera1978-svg/cabrechess/releases/tag/v1.1.0
