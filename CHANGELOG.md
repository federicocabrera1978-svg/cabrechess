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
