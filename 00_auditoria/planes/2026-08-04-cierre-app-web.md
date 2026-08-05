# El cierre de la aplicación web — especificación

> Escrito el 2026-08-04, tras revisar los dos planes anteriores contra el estado real.
> Aprobado por el usuario antes de ejecutar.

## Qué queda cerrado que los planes anteriores todavía no reflejan

| Duda | Estado |
|---|---|
| **A2** las tres señales del driver | ✅ fusionadas en `ros2` y verificadas contra el hardware |
| **A3** las 1125 líneas de maqueta | ✅ borradas, con sus dos dependencias |
| **A5** cuántos alumnos | ✅ **CERRADA: 16 o menos**, un robot por alumno. **No hace falta cola** |
| **A7** `FRENANDO` | ✅ medido y traducido. Falta ver los valores 2-4 del enum, que exigen un obstáculo |
| **A8** la vista del LIDAR | ✅ construida |
| **B1** la cinta | ✅ n=2 · 30 cm contra 30,2 y 29,6 |
| **B2** la parada en marcha | ✅ 4 de 4 · frenada 1,8-2,9 cm · los dos testigos |

**Sigue abierto y no es de esta tanda:** A1 (la F0, necesita el aula), A4 (sin autenticación,
aceptado), A6 (el editor, depende de A1), B3 (el mapa), B4 (el `fmask`).

---

## 1 · Los 2,7 s del nombre — ✅ CERRADO, y no era lo que este apartado suponía

> ✅ **RESUELTO el 2026-08-04 por la tarde.** Se midió en el navegador, como manda este apartado,
> y **el navegador sí pagaba** — mucho más que los 2,7 s de aquí: **no abría nunca**. La causa no
> era la latencia sino que `rvr-NN.local` resolvía a **cuatro** direcciones y el navegador se
> colgaba en las dos primeras, que no fallan.
>
> Se arregló **en el robot**, no en la web (una dirección por red, evidencia 74), porque
> JavaScript no puede elegir dirección. Hoy `ws://rvr-01.local:9090` **abre**: 4339 ms en frío,
> 2331 caliente, y el muro entra por nombre. Evidencia 75.
>
> 📝 **Y el apartado acertó en lo que importaba:** exigir la medida antes de diseñar. Lo que se
> habría diseñado sobre la hipótesis de «2,7 s de latencia» —una espera más larga, un indicador de
> carga— **no habría arreglado nada**, porque el problema no era esperar poco.

**Texto original, conservado:**

**Lo observado:** `ws://rvr-01.local:9090` abre en **2743 ms**; `ws://192.168.1.58:9090` en
**20 ms**. `rvr-01.local` resuelve a cuatro direcciones y la primera es IPv6 *link-local*
(`fe80::…`), que hay que esperar a que caduque.

🔴 **Pero esa medida es de Node, no del navegador.** Chrome y Edge implementan *Happy
Eyeballs* —lanzan IPv4 e IPv6 en paralelo y se quedan con el primero que conteste—, así que
**el navegador puede no pagar nada**. Diseñar el arreglo sobre el cliente equivocado sería el
error que este proyecto lleva documentado cinco veces: **el instrumento miente**.

**Paso 1, y puede que el único:** medir el tiempo de apertura **en el navegador**, por nombre y
por IP, y con el muro abriendo 16 sockets a la vez —que es el caso que importa—.

- Si el navegador va bien → **no hay nada que arreglar**. Se anota la diferencia entre los dos
  clientes y se cierra.
- Si el navegador también paga → entonces, y solo entonces, se diseña. **No se pre-diseña.**

## 2 · Mirar con datos lo que nunca se ha mirado

Muro, `/conducir` y LIDAR, con el robot vivo y por CDP con espera en tiempo real. Toda esta
sesión demuestra que mirar encuentra lo que `curl` no: el «MIRAR» en las 16 baldosas, el «hace
hace 7,9 s», la celda vacía.

⚠️ **`/conducir` mueve el robot.** Se coordina con el usuario antes.

## 3 · Pruebas que rendericen, sin instalar nada

**El problema, medido:** «hace hace 7,9 s» pasó **321 pruebas**. Ninguna comprueba texto
pintado, y `vitest.config.ts` documenta que `jsdom` no se instala.

**Y no basta con mirar el HTML del servidor:** la antigüedad solo aparece **con datos**, que
llegan por WebSocket después de hidratar. El fallo vivía justo donde el servidor no llega.

**Diseño:** una prueba de extremo a extremo guardada tras `ATRIZ_ROBOT=1` —el mismo mecanismo
que las dos que ya existen— que conduce el navegador por CDP contra el robot real y comprueba
el HTML **ya hidratado**:

- ninguna palabra duplicada consecutiva («hace hace», «en reposo … en reposo»)
- ningún `SIN_DATO` dentro de un `<data>` — reutiliza `marcasDefectuosas()` de `semantica.ts`
- ninguna frase de `FRASES_PROHIBIDAS`
- y que **haya** al menos un `<data value>` con datos llegando, que es la mitad que nunca se
  verificó

⚠️ Y una trampa del método, ya pagada: `--virtual-time-budget` **congela el reloj del navegador
y ahoga la red**. Hay que esperar en tiempo real por CDP. Costó tres capturas vacías.

## 4 · El acabado — ✅ HECHO, y con una parte deliberadamente NO hecha

> ✅ **Estados de foco.** En `.rejilla` las baldosas se tocan con 1 px de hueco, así que el
> `outline-offset: 2px` invadía a la vecina **y la vecina lo tapaba por dos de sus cuatro lados**:
> un foco partido justo en el muro, que es donde quien navega con teclado más necesita verlo.
> Resuelto con `position: relative; z-index: 1` **solo mientras tiene el foco**. Verificado en
> captura, enfocando una baldosa rodeada por los cuatro lados.
>
> ✅ **Transición al cambiar de estado.** `Insignia` no tenía ninguna: un cambio de tono era un
> salto. Con 16 baldosas, un hipo de WiFi que cruce el umbral y vuelva da un estroboscopio. 200 ms
> sobre color, fondo y borde — **nada de `transform` ni opacidad**.
>
> ✅ **Y un defecto que apareció al mirarlo, no al planearlo:** la franja de atención era
> `border-l-0 / -4 / -8`, así que **cambiar de estado desplazaba el contenido** 4 u 8 px y el
> identificador quedaba **desalineado entre baldosas según el estado de cada una** — en una losa
> 4×4 eso se lee como un borde dentado. Ahora es una barra absoluta de 8 px escalada por
> `transform`: sin recalcular maquetación, sin mover nada, y las dieciséis alinean igual.
> Verificado sobre el DOM que Tailwind genera las clases arbitrarias
> (`matrix(0…)` / `matrix(0.5…)` / `matrix(1…)`, colores `rgb(180,83,9)` y `rgb(190,24,93)`).
>
> 🔴 **Lo que NO se hizo, y es una decisión, no un olvido: «tarjetas que dejen de ser todas
> iguales».** `craft-floor` llama a eso «el contenedor perezoso», y **aquí no aplica**:
> `impeccable/operate.md:61` dice lo contrario para este modo —*«Consistency over surprise. The
> same visual vocabulary screen to screen is a virtue»*— y la tabla de precedencia de
> `atriz-lab/CLAUDE.md` ya resolvió ese choque a favor de la consistencia. Las tarjetas **ya se
> diferencian por su papel** —la de batería lleva su estado en la cabecera, la parada de
> emergencia tiene su propio marco, el terminal tiene el estado «no construido»— y fabricar
> variación decorativa encima sería adorno en un instrumento. Se anota para que nadie lo
> reabra creyendo que quedó a medias.

**Texto original, conservado:**

Tarjetas que dejen de ser todas iguales —`craft-floor` llama a eso «el contenedor perezoso»—,
estados de foco trabajados, y transición al **cambiar de estado**.

🔴 **NO se anima la llegada de un dato.** `/odom` va a **16,5 Hz**: la puerta de frecuencia de
Emil lo prohíbe sin matices —*«100+ times/day → No animation. Ever»*— y en pantalla sería un
estroboscopio sobre las cifras que alguien está leyendo. Solo se anima el cambio de estado, que
es raro.

---

## Verificación

```bash
cd atriz-lab/frontend
npx tsc --noEmit && npx eslint src && npm test && npm run contrato
npx next dev -p 3118            # ⚠️ nunca a la vez que `npm run build`
```

Y **mirando la pantalla**, que es la lección de esta sesión: se verificó con `curl` y `grep`
durante nueve fases sin una sola captura, y el resultado era plano y repetitivo sin que nada lo
delatara.

⚠️ **DarkReader invierte la página.** Si se ve oscura, comprobar la extensión antes de tocar el
CSS: el token dice `250 250 249` y el `body` renderizado decía `rgb(24,26,27)`.
