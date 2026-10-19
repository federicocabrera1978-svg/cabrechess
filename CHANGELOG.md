# Changelog

Todos los cambios importantes de CabreChess se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Unreleased]

### Agregado
- Elegir color contra la IA desde el menú: **Blancas**, **Negras** o **Azar**.
  Si jugás con negras, el tablero se gira solo y la IA hace la primera jugada.
- Íconos dibujados con primitivas de pygame (reiniciar, girar, deshacer,
  guardar, menú, análisis, reloj, tablas y mate): ya no dependen de la fuente
  del sistema.
- Set de piezas **cburnett** (Lichess / Colin M.L. Burnett, GPLv2+): 12 PNG
  en `assets/pieces/cburnett/` (convertidos desde los SVG oficiales). Créditos
  y licencia en `assets/pieces/cburnett/LICENSE`.
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
