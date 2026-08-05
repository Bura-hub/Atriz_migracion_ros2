# La plataforma Atriz, repensada — descripción para Google Stitch

> **Cómo usarlo.** Las secciones 1-6 son el sistema: se pegan **una sola vez** al empezar, y
> Stitch las aplica a todo. La sección 7 tiene **una tarjeta por pantalla**: se pega la que toque
> cada vez que se genere una pantalla nueva. La 8 se pega **siempre**, al final del prompt.
>
> 🔴 Sustituye a `DESIGN.md`, que describía la versión anterior —sobria, de papel, gris— que se
> descartó. Aquí no queda nada de aquella.

---

## 1 · Qué es esto

Un **laboratorio universitario de robótica** con **16 robots Sphero RVR**, cada uno con una
Raspberry Pi y un LIDAR. La plataforma los gobierna desde el navegador por WebSocket.

**Tres personas, tres necesidades distintas, y el diseño tiene que servir a las tres:**

| Quién | Dónde está | Qué necesita en un segundo |
|---|---|---|
| **El alumno** | sentado, con su robot delante, midiendo con cinta | escribir código, verlo correr, parar el robot |
| **El profesor** | al fondo del aula, a veces proyectando | **a cuál de los 16 hay que ir** |
| **Quien monta** | por SSH, depurando | ritmos, antigüedades, qué llega y qué no |

**No es un panel de administración remoto.** Es un taller presencial: el robot está en la misma
sala que quien lo mira. Eso cambia el diseño — la pantalla no sustituye al robot, lo acompaña.

---

## 2 · El registro visual

**Producto digital contemporáneo, oscuro y con luz.** Fondo profundo casi negro-azulado,
tarjetas de vidrio con desenfoque, dos orbes de luz ambiente que tiñen la pantalla, tipografía
grande de peso medio y una entrada escalonada al cargar.

**Por qué oscuro, cuando el aula tiene las luces encendidas:** porque la pantalla que manda es la
del alumno, a 50 cm, durante dos horas seguidas; y porque el laboratorio quiere parecer un
producto, no una hoja de cálculo. **El muro del profesor —y solo él— tiene un modo claro de alto
contraste** para cuando se proyecta, porque un proyector lava los negros. Es un botón, no una
preferencia del sistema operativo.

**Densidad media-alta.** Hay mucho dato, pero cada pantalla tiene **una** cosa que se lee primero.

---

## 3 · Color

Paleta **comprometida**: el fondo y la luz ambiente ocupan la pantalla entera; el acento
eléctrico marca lo interactivo; y hay un vocabulario de cuatro estados que **no se toca**.

**Sustrato**

- **Pozo** `#07080D` — el fondo de la aplicación
- **Pozo elevado** `#0C0E16` — cabeceras fijas y barras
- **Vidrio** `rgba(255,255,255,0.045)` — el relleno de toda tarjeta
- **Vidrio activo** `rgba(255,255,255,0.07)` — al pasar por encima
- **Filo** `rgba(255,255,255,0.09)` — el borde de 1 px de las tarjetas
- **Texto** `#EDEFF5` · **Texto tenue** `#8B90A3`

**Luz ambiente** — dos orbes desenfocados a 90 px, **fijos**, nunca dentro de un contenedor que
se desplace:

- arriba a la izquierda, 620 px, `rgba(91,140,255,0.34)`
- a la derecha, 560 px, `rgba(34,211,238,0.20)`

**Acento**

- **Eléctrico** `#5B8CFF` y **Cian** `#22D3EE` — botones primarios, pestaña activa, foco,
  degradado del titular

**🔴 El vocabulario de estados — cuatro colores con significado fijo**

- **Neutro** `#8B90A3` — *no se sabe*. Ni bueno ni malo
- **Vivo** `#4ADE80` — solo desde un dato reciente y concreto
- **Mirar** `#FBBF24` — algo que revisar
- **Ir** `#FB6A5A` — hecho confirmado, hay que levantarse

⚠️ **El color nunca es el único código.** Cada estado lleva **su palabra** al lado, siempre. Una
de cada doce personas no distingue el ámbar del coral, y el muro se proyecta.

**Modo claro del muro** (solo esa pantalla): fondo `#F6F5F3`, texto `#0F1020`, tarjetas blancas
con sombra, los mismos cuatro estados en sus versiones oscuras (`#15803D`, `#B45309`, `#BE123C`).

---

## 4 · Tipografía

- **Titulares y cuerpo:** `Geist` — pesos 400/500/600/650
- **Cifras medidas:** `Geist Mono`, con `font-variant-numeric: tabular-nums`

**Escala**

| Uso | Tamaño | Peso | Tracking |
|---|---|---|---|
| Titular de pantalla | `clamp(38px, 6vw, 72px)` | 650 | −0,045em |
| Identificador de robot en el muro | `clamp(28px, 4vw, 44px)` | 600 | −0,04em |
| Cifra medida | 38–42px | 600 | −0,03em |
| Título de tarjeta | 19px | 600 | −0,02em |
| Cuerpo | 15–16px, interlineado 1,55 | 400 | 0 |
| Etiqueta / antigüedad | 11,5px | 400 | 0 |
| Microetiqueta sobre una cifra | 10px, versalitas | 500 | 0,16em |

**🔴 La regla de las cifras, y es la identidad de esta plataforma:** una medida se compone de
**tres niveles** y nunca de uno.

```
        7,41 V          <- la cifra manda: 38 px. La UNIDAD va al 36 % de su
        ────                tamaño, peso normal, en texto tenue. Nunca iguales.
        hace 1,2 s · por encima del umbral
        └─ segunda línea, 11,5 px, tenue: cuándo llegó y contra qué se compara
```

**La monoespaciada es solo para medidas.** Nombres, títulos y botones van en la de texto. Una
mono usada como disfraz de «técnico» abarata la pantalla.

---

## 5 · Forma, profundidad y movimiento

**Tarjeta.** Radio **18 px**. Relleno vidrio, borde de 1 px `Filo`, `backdrop-filter: blur(20px)`.
Un **filo superior encendido**: una línea de 1 px con degradado horizontal que va de transparente
al color del estado y vuelve a transparente. Es lo único que colorea la tarjeta.

**Sombra.** `0 18px 40px -22px rgba(0,0,0,0.7)` más un realce interior de 1 px arriba. Con
desplazamiento y desenfoque — un halo sin desplazamiento es decoración.

**Botón.** Píldora, `padding 12px 22px`. Primario: relleno eléctrico, texto casi negro. Al pulsar
`scale(0.97)` en **140 ms**. Los botones con flecha llevan la flecha **dentro de un círculo
propio** pegado al borde derecho, y ese círculo se desplaza 4 px en diagonal al pasar por encima.

**Movimiento — cuatro reglas y ninguna más**

1. **Entrada escalonada.** Al cargar una pantalla, sus tarjetas suben 18 px y aparecen, **60 ms
   entre una y la siguiente**, curva `cubic-bezier(0.23, 1, 0.32, 1)`, 700 ms. Ocurre **una vez
   al montar**, nunca al recibir datos.
2. **Pulsación.** `scale(0.97)`, 140 ms.
3. **Cambio de estado.** Solo color, 200 ms. Es **anti-parpadeo**: con 16 tarjetas, un hipo de
   WiFi que cruce un umbral y vuelva daría un estroboscopio.
4. **Al pasar por encima.** El vidrio sube de 0,045 a 0,07 y la tarjeta se eleva 2 px, 500 ms con
   `cubic-bezier(0.32, 0.72, 0, 1)`.

🔴 **Nada se repite solo. Nada late. Nada gira.** Ver la sección 8.

`prefers-reduced-motion`: se anulan los desplazamientos y **se conservan las transiciones de
color** — reducir movimiento no puede devolver el parpadeo.

---

## 6 · Componentes

**Medida** — microetiqueta arriba, cifra + unidad, antigüedad debajo. Es el átomo de la
plataforma y aparece en cinco pantallas.

**Distintivo de estado** — píldora con un punto de 5 px, borde y fondo al 12 % del color, texto
a plena luminosidad. **El punto no parpadea.**

**Barra de nivel** — 4 px de alto, radio completo, relleno con degradado del color del estado.
Solo cuando hay una magnitud real que enseñar (batería). **Nunca** para simular progreso.

**Botón de parada de emergencia** — es el elemento más inequívoco de cualquier pantalla donde
aparezca: ancho completo, alto 64 px, relleno coral a plena saturación, versalitas de 20 px,
borde de 2 px más claro. **No comparte fila con nada.**

**Desplegable de contexto** — un `▸` que gira 200 ms. Guarda el *porqué* de una medida, nunca su
estado actual.

**Campo de texto** — fondo `rgba(255,255,255,0.04)`, borde `Filo`, radio 12 px, etiqueta encima
(nunca flotante), y el error **debajo**, en coral, diciendo qué pasó y cómo arreglarlo.

---

## 7 · Las ocho pantallas

### 7.1 · Portada

**Trabajo:** decidir a dónde ir, y saber qué no funciona todavía.

Titular a `clamp(38px,6vw,72px)` con degradado de blanco a gris azulado. Debajo, dos tarjetas
grandes lado a lado: **«Los 16 de un vistazo»** (lleva al muro) y **«Un robot»** (con una
rejilla de 16 píldoras numeradas `01`–`16`).

🔴 **Y una tercera tarjeta, en ámbar, titulada «Lo que todavía no funciona».** No es un aviso
temporal: es permanente y va en la portada. Dice que el terminal no existe y que no hay
autenticación.

### 7.2 · Muro de flota — la pantalla del profesor

**Trabajo:** decir **a cuál de los 16 hay que ir**, desde tres metros.

Cabecera con el titular, una píldora **«N de 16 en línea»** y tres pastillas de vidrio con el
caudal de red. A la derecha, el conmutador **claro/oscuro** — aquí sí, porque se proyecta.

Debajo, rejilla **4×4**. Cada tarjeta:

- **identificador enorme** arriba a la izquierda (es lo que se lee de lejos)
- distintivo de estado arriba a la derecha
- **voltaje a 38 px** en mono
- barra de nivel de la batería
- una línea de 11,5 px: la antigüedad y el motivo, **nunca escondida tras un desplegable**
- el filo superior encendido con el color del estado

🔴 **Una tarjeta a la que no se llega se dibuja distinta de una en apuros:** vidrio al 50 %, sin
filo encendido, sin barra, en una línea. Así, cuando **uno** de los dieciséis se cae salta a la
vista; y cuando se caen los dieciséis se lee como lo que es —un problema de red— y no como
dieciséis robots averiados.

Al pie, un panel plegable **«Dónde buscar a los robots»** con 16 campos para escribir una IP.

### 7.3 · Espacio de un robot — el armazón

Cabecera fija sobre `Pozo elevado`: identificador a 32 px, la URL del socket en mono tenue, el
distintivo del enlace, y un enlace **«ver los 16»**.

Debajo, pestañas: **Terminal · Telemetría · Conducir · LIDAR · Diagnóstico**. La activa lleva una
barra eléctrica de 2 px debajo que **se desliza** de una a otra en 250 ms.

### 7.4 · Terminal — el producto, y está bloqueado

Editor a la izquierda (60 %), salida a la derecha. Barra inferior con **Ejecutar**, **Parar** y la
parada de emergencia. Una **línea de entrada visible y desactivada**, con el motivo al lado.

🔴 **Cero contenido inventado.** El editor y la salida son contenedores vacíos con su estado
nombrado: **«no construido»**, con la cadena de bloqueo dibujada como una lista de tres pasos.
Sin código de mentira, sin salida de mentira.

### 7.5 · Telemetría

Rejilla de dos columnas con cuatro tarjetas —**Batería, Motores, Odometría, Encoders**— y una
quinta a lo ancho para los **LEDs**.

Cada valor con **su propia antigüedad**: llegan por caminos distintos y refrescan a ritmos
distintos. La batería se decide **en voltios**, y el porcentaje aparece debajo marcado como que
no decide nada.

### 7.6 · Conducir

La **parada de emergencia arriba del todo**, fija al desplazar, ancho completo. Debajo, dos
columnas: a la izquierda el enlace, el control del barrido y una **cruceta de nueve celdas** con
las velocidades; a la derecha, una tarjeta **«Lo que va a pasar y no es un fallo»** con cuatro
comportamientos medidos del robot.

🔴 **No hay botón para liberar la parada.** Soltarla es un acto presencial.

### 7.7 · LIDAR

Un lienzo **cuadrado y grande** (560 px o el ancho disponible) centrado, con anillos de distancia
cada 0,5 m, el robot dibujado a escala con su proa, y los puntos del barrido en cian. Debajo:
**«lo más cercano: 0,30 m»**.

Arriba, un aviso de coste: esta pantalla consume el **83 %** del tráfico de un robot.

### 7.8 · Diagnóstico

Tabla densa de ritmos y antigüedades, en mono, con filas alternas al 2 % de blanco. **Es la
pantalla fea a propósito** y no se le pone maquillaje.

---

## 8 · 🔴 Lo que esta plataforma NO puede hacer

**Esta sección se pega en TODOS los prompts.** Es lo que separa este producto de un panel
genérico bonito, y cada línea viene de un fallo real medido en el laboratorio.

### Prohibiciones de movimiento

- ❌ **Ningún pulso, latido, brillo o giro infinito**, y en especial **no en los indicadores de
  estado**. Un punto que late siempre es indistinguible de un robot que vive siempre — y esta
  pantalla vigila dieciséis que pueden estar mudos.
- ❌ **Nada se anima al llegar un dato.** La telemetría llega a 16,5 veces por segundo: animarla
  sería un estroboscopio sobre las cifras que alguien está leyendo.
- ❌ **Ni contadores que suben** de un valor a otro: enseñarían voltajes que el robot nunca
  reportó.

### Prohibiciones de contenido

- ❌ **Ningún dato de ejemplo, relleno ni «orgánico».** Si no hay valor, se dice **«no se sabe»**
  y tiene que **verse distinto de un cero**.
- ❌ **Barras de progreso indeterminadas y esqueletos de carga.** Simulan un progreso que nadie
  está midiendo.
- ❌ **Ningún número sin su antigüedad.** El sondeo térmico va cada 30 s: una temperatura plana
  puede ser el mismo dato repetido.
- ❌ **Nunca «LED encendido» ni «color cambiado».** Ningún servicio del robot confirma un efecto
  físico: uno de ellos devuelve éxito **sin encender nada**.
- ❌ **Nunca «robot averiado» por falta de datos.** Un robot cargando es el estado más común del
  laboratorio. Eso es **ámbar**, con sus causas listadas y **sin elegir** entre ellas.
- ❌ **El porcentaje de batería nunca es el dato principal.** Marcó **100 % con la batería a
  8,29 V**, a 1,29 V del umbral de «baja». Manda el voltaje.
- ❌ **Ninguna cifra de latencia.** No está medida.

### Prohibiciones de forma

- ❌ Gráficas de tendencia, medidores circulares y *sparklines* que hagan de contenido
- ❌ Texto con degradado fuera del titular de pantalla
- ❌ Emojis haciendo de iconos: los iconos se dibujan, con un grosor de trazo único
- ❌ Negro puro `#000000`
- ❌ Una pantalla de inicio de sesión: **no hay control de acceso**, y fingirlo sería peor

---

## 9 · Prompts listos para Stitch

Pegar la sección **1-6** una vez, y después uno de estos:

> **Muro de flota.** Pantalla oscura con dos orbes de luz ambiente fijos. Cabecera con titular en
> degradado «Flota Atriz», píldora «1 de 16 en línea» y tres pastillas de vidrio con cifras de
> red. Debajo, rejilla 4×4 de tarjetas de vidrio con radio 18 px y filo superior encendido. Cada
> tarjeta: identificador grande, distintivo de estado en píldora, voltaje a 38 px en mono, barra
> de nivel de 4 px y una línea de antigüedad. Cinco tarjetas en estado «no llego»: vidrio al 50 %,
> sin filo, sin barra. Entrada escalonada de 60 ms. **Aplicar la sección 8 entera.**

> **Telemetría de un robot.** Cabecera fija con identificador, URL del socket en mono y pestañas
> con barra deslizante. Rejilla de dos columnas con cuatro tarjetas de vidrio: Batería, Motores,
> Odometría, Encoders; y una quinta a lo ancho para LEDs. Cada medida en tres niveles: cifra
> grande en mono, unidad al 36 %, antigüedad debajo. **Aplicar la sección 8 entera.**

> **Conducir.** Botón de parada de emergencia fijo arriba, ancho completo, 64 px de alto, coral a
> plena saturación, versalitas. Debajo dos columnas: controles a la izquierda con cruceta de
> nueve celdas, y a la derecha una tarjeta de texto con cuatro comportamientos del robot. **Sin
> botón de liberar la parada. Aplicar la sección 8 entera.**

> **Terminal bloqueado.** Editor de código a la izquierda y consola a la derecha, los dos
> **vacíos**, con un estado «no construido» centrado que explica qué falta y qué lo bloquea, en
> tres pasos. Línea de entrada visible y desactivada. **Nada de código ni de salida inventados.
> Aplicar la sección 8 entera.**

---

## 10 · Referencia visual

Las tres maquetas de este registro, para enseñárselas a Stitch como nivel de acabado:

- **D · Órbita** — la que describe este documento
- **F · Aurora** — la misma estructura con campo de degradado en vez de pozo oscuro
- **E · Bloques** — el registro claro y saturado, por si se prefiere; solo cambiaría la sección 3
