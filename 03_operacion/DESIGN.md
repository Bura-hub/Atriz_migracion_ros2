# Design System: Atriz — instrumento del laboratorio de robótica

> **Para pegar en Google Stitch.** Escrito en el formato que su agente interpreta:
> descripción visual + valores exactos.
>
> 🔴 **Léase antes la sección 8.** Este documento **anula cinco reglas por defecto** de la guía
> de estilo de la que nace, y cada anulación tiene detrás una medición de este laboratorio. Si
> Stitch devuelve una pantalla que las incumple, la pantalla está mal aunque sea bonita.

---

## 0 · Qué es esto, en una frase

La interfaz de un laboratorio universitario con **16 robots Sphero RVR**. Los alumnos están
**en la misma sala que el robot**, midiendo con cinta métrica y transportador. El profesor mira
los 16 desde el otro lado del aula, a veces proyectado.

**No es un panel de administración ni un producto de consumo: es un instrumento.** La referencia
mental es un multímetro de laboratorio o una consola de control de vuelo, no un *dashboard* de
SaaS.

**Diales:** Densidad **8** (Cockpit Dense) · Varianza **2** (Predictable Symmetric) ·
Movimiento **2** (Static Restrained).

⚠️ La varianza y el movimiento van deliberadamente **bajos**, al contrario del valor por defecto
(8 y 6). Un instrumento que sorprende es un instrumento que distrae, y quien lo usa lo mira
veinte veces por sesión. *«Consistency over surprise: the same visual vocabulary screen to
screen is a virtue.»*

---

## 1 · Atmósfera visual

Un taller de precisión bien iluminado. Superficies claras y cálidas, tinta casi negra, líneas
finas que compartimentan de verdad. Nada flota: todo está apoyado en una rejilla.

La sensación buscada es **legibilidad bajo presión** — alguien mirando esto con un robot en
movimiento delante y quince minutos de práctica. No hay nada que descubrir ni ningún momento de
deleite: hay cifras que leer rápido y una decisión que tomar.

**Luz, no oscuridad.** La escena manda: aula con luz encendida, portátiles, y un proyector que
lava los negros. Un fondo claro con tinta oscura se lee a tres metros proyectado; uno oscuro no.
El modo oscuro existe para persianas bajadas y **se pide a mano**, no se hereda del sistema.

---

## 2 · Paleta y funciones

**Sustrato**

- **Lino** `#FAFAF9` — fondo de página. Blanco cálido, nunca blanco puro
- **Papel** `#FFFFFF` — relleno de paneles y celdas
- **Tinta** `#1C1917` — texto principal. Nunca `#000000`
- **Grafito** `#57534E` — etiquetas, unidades, metadatos. Contraste 7,63:1 sobre papel
- **Trazo** `#D6D3D1` — la línea de 1 px que compartimenta. Es estructura, no decoración

**El vocabulario de estados** — cinco, y esto anula la regla de «máximo un acento»

- **Neutro** `#78716C` — *no se sabe*. Ni bueno ni malo
- **Vivo** `#15803D` — solo desde un dato reciente y concreto
- **Mirar** `#B45309` — algo que revisar
- **Ir** `#BE185D` — hecho confirmado, hay que levantarse
- **Frenando** `#1D4ED8` — la capa de seguridad está limitando el movimiento

🔴 **No es una paleta de acento: es un idioma.** Un instrumento tiene que distinguir «no lo sé»
de «va bien» de «míralo» de «ve ahora», y eso son cuatro cosas distintas que no caben en un
color.

✅ **Contrastes calculados, no supuestos** — los **14 pares** (7 tintas × 2 fondos) pasan
**WCAG AA**, 0 fallos. El peor es **Neutro sobre Lino, 4,59:1**, y va justo por encima del
umbral de 4,5: **el gris «no se sabe» no puede aclararse más**. El mejor, Tinta sobre Papel,
17,49:1.

⚠️ **Y el color nunca es el único código.** Cada estado lleva además su palabra y, en el muro,
**grosor de franja** (0 · 4 px · 8 px). Un proyector desatura y una de cada doce personas no
distingue rojo de ámbar.

---

## 3 · Tipografía

- **Texto:** pila del sistema (`ui-sans-serif, system-ui, Segoe UI, Roboto`)
- **Cifras:** monoespaciada del sistema (`ui-monospace, Cascadia Mono, Consolas`)
- **`font-variant-numeric: tabular-nums` global**

🔴 **Tipografía del sistema, y no es pereza: es una restricción medida.** El experimento que hoy
bloquea el producto es si el punto de acceso del aula deja pasar el tráfico entre clientes. Una
interfaz que necesita descargar dos fuentes de Google **se queda sin letra, en silencio, justo
donde va a usarse**. Esto anula la prohibición de «fuentes del sistema»: aquí la red no es un
supuesto.

**Jerarquía en tres niveles, y es lo que hace que esto se lea como un instrumento:**

1. **La cifra** — monoespaciada, 1,25–1,875 rem, `tracking-tight`. Manda
2. **La unidad** — 0,62 em, peso normal, en Grafito, pegada a la cifra
3. **La antigüedad y la referencia** — 0,6875 rem, línea propia, debajo

🔴 **La unidad NUNCA al mismo peso que el número.** Un multímetro no pinta «8,23» y «V» iguales:
el número es el dato y la unidad su contexto. Al mismo tamaño compiten y el ojo tiene que
separarlos en cada lectura. Es también lo único que permite leer una columna de medidas de un
vistazo.

**La ausencia se pinta como una raya `—`**, más pequeña y apagada. Se distingue de un cero al
instante, pero no compite con lo que sí llegó.

---

## 4 · Componentes

**Panel** — borde de 1 px, **radio 0**, cabecera con título y subtítulo separada del cuerpo por
una línea. Sin sombra: la jerarquía la dan la línea y el tamaño. *(Anula el radio de 2,5 rem: un
instrumento no redondea.)*

**Rejilla de 1 px** — la compartimentación se ve. `display: grid; gap: 1px` con el fondo del
contenedor asomando por el hueco, así **cada línea entre celdas es una y no dos bordes pegados**.

**Dato** — microetiqueta arriba, cifra + unidad, antigüedad debajo. Apretado dentro, generoso
entre datos.

**Botón** — plano, borde de 1 px, radio 0. `scale(0.97)` al pulsar en **140 ms**. Sin resplandor.

**Botón de parada de emergencia** — el elemento más inequívoco de cualquier pantalla donde
aparezca: ancho completo, borde de 4 px, versalitas, color **Ir**. Su marco lo distingue; **no
lleva sombra**, porque no necesita parecer que sobresale.

**Insignia de estado** — rectangular, borde de 1 px, con un **cuadrado** de color delante.
🔴 **El cuadrado NO parpadea, ni parpadeará.**

**Desplegable «Por qué»** — el contexto de fondo plegado, el triángulo gira 200 ms al abrir.

**Estados vacíos — y aquí hay uno que ninguna guía contempla:**

- *no se sabe* — el dato no ha llegado. Una raya
- *sin señal* — el robot no contesta. Ámbar, **nunca rojo**, con las tres causas listadas y
  **sin elegir** entre ellas
- *no llego* — no hay socket. Apagado, una línea
- **🔴 *no construido*** — la funcionalidad **no existe todavía**. No es «cargando» ni
  «próximamente»: es una casilla que dice qué falta y qué lo bloquea, con la cadena entera

---

## 5 · Las pantallas, una a una

### Portada

Punto de entrada, sin adornos. Nombre del laboratorio, acceso al muro, y una rejilla con los 16
robots numerados `01`–`16`.

🔴 **Y un bloque en ámbar titulado «Lo que todavía no funciona».** No es un pegote temporal: es
parte del diseño permanente. La portada dice lo que la aplicación **no** sabe hacer, porque la
anterior decía «Sistema operacional» sin haber hablado con ningún robot.

### Muro de flota — la del profesor

Rejilla **4×4 como una sola losa** de 1 px. **Dos distancias de lectura en la misma baldosa:**

- **Lejos (3 m, proyectado):** el identificador enorme —`clamp(1.75rem, 4.5vw, 3rem)`, el único
  de toda la aplicación—, la franja de atención y el voltaje en monoespaciada
- **Cerca:** el estado, las etiquetas de los motivos y «lo último que se supo». Pequeños,
  presentes y **nunca escondidos**

🔴 **Una baldosa inalcanzable se dibuja distinta de una en apuros:** apagada, en una línea, sin
franja. Así, cuando **uno** de los dieciséis se cae salta a la vista; y cuando se caen los
dieciséis, se lee como lo que es —un problema de red— y no como dieciséis robots averiados.

### Espacio de trabajo de un robot

Cabecera fija con identificador, estado del enlace y batería. Pestañas: **Terminal · Telemetría ·
Conducir · LIDAR · Diagnóstico**.

### Terminal — el producto, y está bloqueado

Editor a la izquierda, salida a la derecha, barra inferior con Ejecutar, Parar y la parada de
emergencia. **Una línea de entrada visible y deshabilitada**, porque sin ella dos de las diez
prácticas están muertas.

🔴 **Cero contenido fabricado.** El editor y la salida son contenedores vacíos con su estado
nombrado. Un editor de mentira con salida inventada sería una maqueta en la pestaña principal.

### Telemetría

Cuatro paneles: batería, motores, odometría, encoders. Cada valor con **su** antigüedad, porque
llegan por caminos distintos y refrescan a ritmos distintos.

### Conducir

Cruceta de nueve celdas y el botón de parada, grande y siempre visible sin desplazar.
🔴 **Sin botón de liberar la parada**: soltarla es presencial.

### LIDAR

Lienzo cuadrado, anillos de distancia cada 0,5 m, el robot dibujado a escala real con su proa.
**Con un aviso de coste en pantalla**: esta vista consume el 83 % del tráfico de un robot.

### Diagnóstico

Tabla densa de ritmos y antigüedades, estilo consola. **Es la pantalla fea a propósito**, y por
eso fue la primera que se construyó.

---

## 6 · Disposición

Rejilla CSS, contenedor de 1400 px centrado, colapso a una columna por debajo de 768 px, sin
desplazamiento horizontal nunca. Objetivos táctiles de 44 px. Titulares con `clamp()`.

Apretado **dentro** de un grupo, generoso **entre** grupos. Más aire encima de un título que
debajo.

---

## 7 · Movimiento — aquí es sobre todo restar

Todo el movimiento de la aplicación cabe en tres reglas, ninguna por encima de 300 ms:

1. **Pulsación** — `scale(0.97)`, 140 ms, `cubic-bezier(0.23, 1, 0.32, 1)`
2. **Aparición de un aviso** — opacidad + 3 px + `scale(0.98)`, 180 ms, **una vez y nunca más**
3. **Cambio de estado** — color, 200 ms. Es **anti-parpadeo**: sin él, un hipo de WiFi hace
   estroboscopio en un muro de 16

`prefers-reduced-motion` **conserva las transiciones de color** y anula las de posición. Reducir
no es eliminar: matar la transición de color le devolvería el parpadeo a quien pidió menos
movimiento.

---

## 8 · 🔴 LO QUE ESTÁ PROHIBIDO — y las cinco anulaciones

### Las cinco reglas por defecto que aquí se anulan, con su motivo

| La guía dice | Aquí | Por qué |
|---|---|---|
| *«Perpetual micro-interactions: every active component should have an infinite loop state (Pulse, Shimmer…)»* | 🔴 **PROHIBIDO SIN EXCEPCIÓN** | **Un pulso infinito en un indicador de estado es indistinguible de un latido real.** Esta pantalla vigila 16 robots que pueden estar mudos; algo que se mueve siempre parece algo vivo siempre |
| *«Skeletal shimmer loaders»* | 🔴 Prohibido | Simulan progreso que nadie está midiendo. La regla es **nunca inventar progreso** |
| *«Maximum 1 accent color»* | Rechazado | El color aquí es un **vocabulario de cinco estados**, no un acento de marca |
| *«Variance 8, staggered cascade reveals, asymmetric layouts»* | Bajado a 2, sin cascada | Un instrumento se mira veinte veces por sesión. La cascada se repetiría en cada reconexión, y son 16 sockets independientes |
| *«Fake round numbers banned → use organic data like 47.2 %»* | 🔴 **Ningún dato inventado, ni orgánico ni redondo** | En una *landing* es cosmética. Aquí sería **telemetría falsa que parece real** |

### Y lo que esta interfaz no puede decir nunca

- ❌ «LED encendido», «color cambiado» — **ningún servicio del robot confirma un efecto físico**
- ❌ «robot averiado» por falta de datos — un robot cargando es el estado cotidiano
- ❌ Un porcentaje de batería como dato principal — marcó **100 % a 8,29 V**
- ❌ Un número sin su antigüedad
- ❌ Una cifra de latencia — no está medida
- ❌ Cualquier dato de ejemplo o de relleno
- ❌ Gráficas de tendencia, medidores circulares, barras de progreso, *sparklines*
- ❌ Emojis como iconos · gradientes · sombras de relieve · negro puro · cursores propios
- ❌ Una pantalla de inicio de sesión — **no hay control de acceso**, y fingirlo sería peor

---

## 9 · Cómo se juzga el resultado

Una sola pregunta, y vale para cada pantalla:

> **¿Alguien podría creer que esto sabe algo que no sabe?**

Si la respuesta no es un no rotundo, la pantalla está mal aunque sea preciosa.

📝 Y la prueba de fuego del muro no es una captura: es **una persona a tres metros con el
proyector encendido** diciendo qué robot hay que ir a mirar.

---

## 10 · Esto no es una propuesta: es lo que ya corre

Los ocho colores, las tres duraciones y las dos curvas de este documento **están tomados de
`atriz-lab/frontend/src/app/globals.css`**, no inventados para el encargo:

| Aquí | En el código | Valor |
|---|---|---|
| Lino | `--background` | `250 250 249` |
| Papel | `--card` | `255 255 255` |
| Tinta | `--foreground` | `28 25 23` |
| Grafito | `--muted-foreground` | `87 83 78` |
| Trazo | `--border` | `214 211 209` |
| Neutro · Vivo · Mirar · Ir · Frenando | `--estado-*` | `120 113 108` · `21 128 61` · `180 83 9` · `190 24 93` · `29 78 216` |
| Pulsación · estado · entrada | `--t-pulsacion` · `--t-estado` · `--t-entrada` | `140ms` · `200ms` · `180ms` |
| Curva de salida · de movimiento | `--curva-salida` · `--curva-mov` | `cubic-bezier(0.23, 1, 0.32, 1)` · `cubic-bezier(0.77, 0, 0.175, 1)` |

**Por qué importa:** lo que devuelva Stitch se puede **contrastar contra la aplicación real**,
píxel a píxel, en vez de admirarse por separado. Si Stitch propone otro color o otra duración,
es una **discrepancia medible** y hay que decidirla — no una alternativa que convive.

⚠️ Y al revés: si alguien cambia `globals.css`, **esta tabla queda mentida**. Es la deriva
documental que este proyecto lleva persiguiendo desde el principio; la tabla existe para que se
note.
