# La plataforma Atriz — encargo de diseño para Google Stitch

> **Cómo se usa este documento.**
>
> - Las secciones **§1 a §4** son *el sistema*. Se pegan **una sola vez** al empezar una sesión
>   con Stitch, y valen para todas las pantallas.
> - La sección **§5** tiene **una tarjeta por pantalla**, y cada tarjeta termina con un
>   **prompt listo para pegar**. Se pega el de la pantalla que toque.
> - La sección **§8** —lo que la plataforma NO puede hacer— se pega **siempre**, al final de
>   cada prompt. No es opcional: cada línea viene de un fallo medido en el laboratorio.
> - Las secciones **§6 y §7** no se pegan: son la memoria de por qué las cosas son así.
>   Existen para que nadie reabra una discusión ya cerrada.
>
> 🔴 Este fichero **sustituye a `DESIGN.md`** y a la versión anterior de sí mismo. Aquél
> describía un mundo sobrio de papel gris que se descartó, y ésta describía ocho pantallas
> cuando el análisis dio **diez**. Aquí no queda nada de aquello salvo lo que sobrevivió a
> propósito, y lo que sobrevivió está marcado como tal.

---

## §0 · Qué cambió, en cinco líneas

1. **El mundo visual es ÓRBITA + BLOQUES**, y es lo único nuevo del registro: pozo oscuro
   azulado con dos orbes de luz fijos, y **dos clases de superficie** —vidrio y bloque de color
   a plena saturación— cuya diferencia **es el idioma de la aplicación**, no decoración.
2. **Son diez pantallas, no ocho.** Aparecen «Por qué no obedece» y «Cuaderno de medidas», y
   «Diagnóstico» deja de ser *la pantalla fea a propósito* para ser seis superficies reales.
3. **El terminal sigue siendo el producto y sigue sin existir**, pero deja de ser un decorado
   vacío: pasa a ser la **lista de requisitos medidos** que su agente de sesión tendrá que
   cumplir (PTY, stdin, señales, PID).
4. **La cruceta de nueve celdas se reduce a cinco**, la barra de nivel de batería desaparece, y
   el porcentaje de batería se retira de todas partes menos de una nota explicativa.
5. **Todo campo lleva ahora su fuente, su formato y qué se pinta cuando no hay dato.** Eso es
   §5, y es la mitad del documento.

---

## §1 · Qué es esto

Un **laboratorio universitario de robótica** con **16 robots Sphero RVR**, cada uno con una
Raspberry Pi 4 y un LIDAR YDLIDAR X2. La plataforma los gobierna desde el navegador por
WebSocket, a través de rosbridge.

**No es un panel de administración remoto. Es un taller presencial**: el robot está en la misma
sala que quien lo mira, y el alumno lo está midiendo con cinta métrica y transportador. Eso
cambia el diseño entero — **la pantalla no sustituye al robot, lo acompaña**. Cuando la pantalla
no sabe algo, la respuesta correcta muchas veces es *«mira el robot»*, y eso se escribe.

**Tres personas, tres necesidades, y el diseño sirve a las tres sin mezclarlas:**

| Quién | Dónde está | Qué necesita en un segundo | Su pantalla |
|---|---|---|---|
| **El alumno** | sentado, con su robot delante, midiendo | escribir código, verlo correr, parar el robot | Taller · Conducir · Cuaderno |
| **El profesor** | al fondo del aula, a veces proyectando | **a cuál de los 16 hay que ir** | Muro de flota |
| **Quien monta** | por SSH, depurando la flota | ritmos, antigüedades, qué llega y qué no | Diagnóstico · No obedece |

**Densidad media-alta.** Hay mucho dato, pero **cada pantalla tiene una sola cosa que se lee
primero**, y en §5 está dicha para cada una.

---

## §2 · El mundo visual — ÓRBITA + BLOQUES

### 2.1 · El registro

**Producto digital contemporáneo, oscuro y con luz.** Pozo profundo casi negro-azulado, dos
orbes de luz ambiente que tiñen la pantalla entera, superficies de vidrio con desenfoque,
tipografía grande de peso medio y una entrada escalonada al cargar.

**Por qué oscuro, cuando el aula tiene las luces encendidas:** porque la pantalla que manda es
la del alumno, a 50 cm, durante dos horas seguidas; y porque el laboratorio quiere parecer un
producto, no una hoja de cálculo. **El muro del profesor —y solo él— tiene un modo de
proyección** de alto contraste, porque un proyector lava los negros. **Es un botón, no una
preferencia del sistema operativo**: la decisión la toma quien proyecta, no su portátil.

### 2.2 · 🔴 Las dos superficies — esto ES el idioma, no es estilo

La aplicación tiene **dos clases de superficie y nada entre medias**:

| Superficie | Cómo se dibuja | Qué significa |
|---|---|---|
| **VIDRIO** | relleno `rgba(255,255,255,0.045)`, borde de 1 px `rgba(255,255,255,0.09)`, `backdrop-filter: blur(20px)`, radio **20 px** | superficie normal: **sin novedad**, o **no se llega** al robot |
| **BLOQUE** | color **a plena saturación**, sin blur, sin borde, radio 20 px, texto sobre el color | **este robot pide algo** |

**Por qué importa tanto:** con trece baldosas de vidrio y tres bloques de color, el ojo del
profesor va solo, **desde tres metros y antes de leer una palabra**. Si todas fueran de color,
la pantalla gritaría entera y no diría nada; si todas fueran de vidrio, la que importa se
perdería entre las quince que no.

⚠️ **Y el color nunca va solo.** Cada bloque lleva **su palabra** —«en línea», «sin telemetría»,
«mirar», «hay que ir»— y, en el muro, **un tercer código redundante**: el paso de la trama del
galón. Una de cada doce personas no distingue el lima del coral, y este muro se proyecta.

### 2.3 · Color

**Sustrato**

- **Pozo** `#07080D` — el fondo de la aplicación. **Nunca negro puro.**
- **Pozo elevado** `#0C0E16` — cabeceras fijas y barras ancladas
- **Vidrio** `rgba(255,255,255,0.045)` · **Vidrio activo** `rgba(255,255,255,0.075)`
- **Filo** `rgba(255,255,255,0.09)` — el borde de 1 px
- **Texto** `#EDEFF5` · **Texto tenue** `#8B90A3`

**Luz ambiente** — dos orbes desenfocados a 90 px, **fijos al viewport**, nunca dentro de un
contenedor que se desplace:

- arriba a la izquierda, 620 px, `rgba(91,140,255,0.34)`
- a la derecha, 560 px, `rgba(34,211,238,0.20)`

**Los bloques** — los tres colores de campo, a plena saturación:

- **Cobalto** `#2B4BF2` — en línea, no hay nada que hacer
- **Lima** `#B6E01E` — **mirar**
- **Coral** `#FF5C39` — **hay que ir**

**🔴 El vocabulario de estados para TEXTO e insignias — cuatro colores con significado fijo**

- **Neutro** `#8B90A3` — *no se sabe*. Ni bueno ni malo, y es un veredicto legítimo
- **Vivo** `#4ADE80` — solo desde un dato **reciente y concreto**
- **Mirar** `#FBBF24` — algo que revisar
- **Ir** `#FB6A5A` — hecho confirmado, hay que levantarse

⚠️ **Existe un quinto, `--estado-frenando` `#5B8CFF`, declarado y SIN USAR a propósito.** Saldría
de `/collision_monitor_state`, cuyo `action_type` solo se ha observado en un valor. El hueco se
declara; no se rellena con una suposición. **No lo uses.**

**Acento** — **Eléctrico** `#5B8CFF` y **Cian** `#22D3EE`: botones primarios, pestaña activa,
foco, degradado del titular de pantalla.

**Modo proyección** (solo el muro de flota, y por botón): fondo `#F6F5F3`, texto `#0F1020`,
tarjetas blancas con sombra, los tres bloques en sus versiones oscuras (`#15803D`, `#B45309`,
`#BE123C`). Su criterio de aceptación **es una persona a tres metros del muro**, no una prueba
automática, y así se dice en la propia pantalla.

### 2.4 · Tipografía

- **Titulares y cuerpo:** `Geist` — pesos 400/500/600/650. **Empaquetada en el bundle, cero
  peticiones externas** (el punto de acceso del aula puede bloquear la red, y por eso se
  empaqueta, no por eso se renuncia a ella)
- **Cifras medidas:** `Geist Mono`, con `font-variant-numeric: tabular-nums` **global** — casi
  todo número de esta interfaz es una medida, y unas cifras que bailan de ancho al actualizarse
  se leen peor

**Escala**

| Uso | Tamaño | Peso | Tracking |
|---|---|---|---|
| Titular de pantalla | `clamp(2,5rem, 6vw, 4,875rem)` | 650 | −0,045em |
| Identificador de robot en el muro | `clamp(1,5rem, 3,2vw, 2,4rem)` | 600 | −0,04em |
| Cifra medida grande | 38–42 px | 600 | −0,03em |
| Título de tarjeta | 19 px | 600 | −0,02em |
| Cuerpo | 15–16 px, interlineado 1,55 | 400 | 0 |
| Etiqueta / antigüedad | 11,5 px | 400 | 0 |
| Microetiqueta sobre una cifra | 10 px, versalitas | 500 | 0,16em |

**🔴 La regla de las cifras, y es la identidad de esta plataforma:** una medida se compone de
**tres niveles** y nunca de uno.

```
        8,28 V          <- la cifra manda: 38 px, mono. La UNIDAD va al 36 % de
        ────                su tamaño, peso normal, en texto tenue. Nunca iguales.
        hace 12,4 s · por encima del umbral
        └─ segunda línea, 11,5 px, tenue: CUÁNDO llegó y CONTRA QUÉ se compara
```

**La monoespaciada es solo para medidas** y para lo que hay que copiar literalmente (URLs,
comandos, nombres de topic). Nombres, títulos y botones van en la de texto: `rvr-07` es un
**nombre**, no una medida, y va en Geist. Una mono usada como disfraz de «técnico» abarata la
pantalla.

### 2.5 · Forma y profundidad

**Tarjeta de vidrio.** Radio **20 px**. Relleno vidrio, borde de 1 px `Filo`,
`backdrop-filter: blur(20px)`. Un **filo superior encendido**: una línea de 1 px con degradado
horizontal que va de transparente al color del estado y vuelve a transparente. **Es lo único que
colorea una tarjeta de vidrio.**

**Bloque de color.** Radio 20 px, relleno saturado, **sin blur y sin borde** — un bloque no es
vidrio teñido, es otra cosa. Lleva **galón**: una franja de 10 px pegada al canto izquierdo,
`repeating-linear-gradient` a 45° en el color del texto al 55 % de opacidad, con **paso 14 px si
es MIRAR y 6 px si es IR**. Así «más denso = más urgente» se aprende de un vistazo, porque los
dos aparecen en el mismo muro, y **sobrevive a un proyector que desatura**.

**Número fantasma.** En una baldosa de bloque, el número del robot repetido en grande, recortado
por el canto inferior derecho, opacidad 0,13, `aria-hidden`. Refuerza a dónde ir sin añadir texto.

**Sombra.** `0 18px 40px -22px rgba(0,0,0,0.7)` más un realce interior de 1 px arriba. Con
desplazamiento y desenfoque — un halo sin desplazamiento es decoración. **Y nunca se declara la
elevación dos veces**: o borde marcado o sombra marcada, no las dos gritando.

**Botón.** Píldora, `padding 12px 22px`. Primario: relleno eléctrico, texto casi negro
(`#07080D`). Al pulsar `scale(0.97)` en 140 ms. Los botones con flecha llevan la flecha **dentro
de un círculo propio** pegado al borde derecho, y ese círculo se desplaza 4 px en diagonal al
pasar por encima.

**El bloque que importa ocupa el doble de ancho.** Cuando una pantalla tiene una pieza que manda
—la parada de emergencia, el veredicto de «no obedece», el voltaje del muro— esa pieza **no
comparte fila**: ocupa el ancho entero o el doble de la celda vecina. La jerarquía se dice con
espacio, no solo con tamaño de letra.

### 2.6 · Movimiento — cuatro reglas y ninguna más

1. **Entrada escalonada.** Al montar una pantalla, sus tarjetas suben 18 px y aparecen, **60 ms
   entre una y la siguiente**, curva `cubic-bezier(0.23, 1, 0.32, 1)`, **720 ms**. Ocurre **una
   vez al montar**, en CSS, y **nunca** al recibir datos ni al reordenar una rejilla.
2. **Pulsación.** `scale(0.97)`, 140 ms.
3. **Cambio de estado.** Solo color, 200 ms. Es **anti-parpadeo**: con 16 baldosas, un hipo de
   WiFi que cruce un umbral y vuelva daría un estroboscopio.
4. **Al pasar por encima.** El vidrio sube de 0,045 a 0,075 y la superficie se eleva 2 px,
   500 ms con `cubic-bezier(0.32, 0.72, 0, 1)`.

⚠️ **Nunca `ease-in` en interfaz**: empieza lento justo en el instante que se mira, así que
300 ms con `ease-in` **se sienten** más lentos que con `out`.

🔴 **Nada se repite solo. Nada late. Nada gira.** Ver §8.

`prefers-reduced-motion`: se anulan los desplazamientos y **se conservan las transiciones de
color** — reducir movimiento no puede devolver el parpadeo.

### 2.7 · Componentes

**Medida** — microetiqueta arriba, cifra + unidad, antigüedad debajo. Es el átomo de la
plataforma y aparece en las diez pantallas. Emite `<data value="8.28">` cuando hay dato, y **no
emite `<data>` cuando no lo hay**: un hueco no es un valor.

**Insignia de estado** — píldora con un punto de 5 px, borde y fondo al 12 % del color, texto a
plena luminosidad, **y su palabra siempre**. **El punto no parpadea.**

**Botón de parada de emergencia** — el elemento más inequívoco de cualquier pantalla donde
aparezca: **ancho completo, alto 64 px**, coral a plena saturación, versalitas de 20 px, borde de
4 px más claro, **sin sombra**. **No comparte fila con nada**, y va anclado (`sticky top-0`) para
que ningún desplazamiento lo saque de la vista.

**Tira de testigos** — dos o tres casillas separadas por filetes de 1 px, **jamás fundidas en un
solo verde**. Es el componente que impide la mentira favorita de este proyecto: confundir «el
mensaje salió» con «el robot lo hizo».

**Desplegable de contexto** — un `▸` que gira 200 ms. Guarda el **porqué** de una medida
(umbrales, procedencia, historia), **nunca su estado actual ni el motivo de una alarma**.

**Ficha de causa** — se abre **en sitio**, dentro de la propia celda, empujando la rejilla hacia
abajo. **No es un modal y no navega.** El clic **amplía**, no revela: lo corto ya estaba visible.

**Campo de texto** — fondo `rgba(255,255,255,0.04)`, borde `Filo`, radio 12 px, etiqueta encima
(nunca flotante), y el error **debajo**, en coral, diciendo qué pasó y cómo arreglarlo.

**Comando copiable** — `<samp>` a ancho completo, seleccionable, mono, con botón de copiar y
**una línea que dice qué desempata**, no qué hace.

---

## §3 · El idioma de la honestidad — gobierna todo lo demás

**La regla central: la pantalla nunca puede afirmar lo que no sabe.**

El peor modo de fallo de este laboratorio, documentado una y otra vez, son **interfaces que
parecen sanas sobre sistemas rotos**: `systemctl` diciendo *active* con el driver muerto cuatro
minutos; un servicio devolviendo `success=true` sin encender el LED; el log escribiendo
«streaming reanudado» con el robot **apagado**; el topic registrado y mudo. Todas comparten la
forma: **un código de salida 0 no prueba que algo pasara.**

### 3.1 · Seis estados vacíos, no uno

Un hueco tiene que decir **cuál** de estos seis es:

1. **Primer uso** — «esta pestaña se abrió hace 3 s y aún no ha llegado nada»
2. **Sin resultados** — la lista está vacía y eso es correcto
3. **Filtrado** — hay datos, no los estás viendo
4. **Sin permiso** — aquí, «rosbridge deniega en silencio»
5. **Fallo** — se intentó y salió mal, con su motivo literal
6. **🔴 NO CONSTRUIDO** — la funcionalidad **no existe todavía**. No es «cargando», no es
   «próximamente», no es un hueco silencioso: es **una casilla que dice qué falta y qué la
   bloquea**. Es el estado del terminal, que es el producto.

### 3.2 · «No se sabe» tiene que verse distinto de un cero

- Un hueco se pinta como **raya `—` en mono con `title="no se sabe"`**, o con la frase entera.
- **Nunca** `0`, `0,00 V`, `0 ms`, `0 Hz`, `--`, ni una casilla vacía.
- **`−1,0` significa «nunca se ha sabido nada»** y se escribe así. Un cero ahí sería afirmar una
  comprobación que no se hizo.
- **`NaN` es un dato que llegó vacío a propósito** y es distinto de que no llegara nada: el
  driver publica NaN cuando la lectura falla. Se dice: «llegó el mensaje y venía sin valor».

### 3.3 · Ningún número sin su antigüedad, y ninguna antigüedad sin su cadencia

`/battery_state` llega **cada 30,0 s exactos**: 28 s de antigüedad es normal y 90 s es que el
keepalive no corre. El sondeo térmico va cada 30 s y `/motor_status` se republica a 1 Hz **desde
memoria**: una temperatura plana puede ser **el mismo dato repetido**, y por encima de 35 s se
dice.

**🔴 Y un umbral de silencio en milisegundos NO es transferible entre topics de ritmos
distintos.** Los 3000 ms calibrados contra `/odom` (16,5 Hz) son **50 mensajes perdidos**; los
mismos 3000 ms sobre `/motor_status` (1 Hz) son **tres**, y pintarían las 16 baldosas «sin señal
de vida» al primer hipo de WiFi. **El umbral se expresa en MENSAJES PERDIDOS y se traduce a
milisegundos con el período de SU topic.**

### 3.4 · La batería se decide por VOLTAJE

`percentage` marcó **100 % con la batería a 8,29 V**, a 1,29 V del umbral de «baja» del propio
firmware (7,0 V; crítica 6,5 V). Además es **una fracción 0-1**, no un porcentaje. **No se pinta
en ninguna pantalla**, ni pequeño, ni «marcado como que no decide nada»: un número declarado
inútil sigue ocupando el sitio del que decide.

### 3.5 · Dos hechos nunca se funden en un verde

«Salió por el WebSocket» es un hecho **del navegador**. «El robot dice que su bandera está
puesta» es un hecho **del robot**. «No se sabe» es un tercero. **Van en casillas separadas por un
filete**, siempre, en todas las pantallas donde aparezcan.

### 3.6 · Lo que sí se puede afirmar, y por qué

**«parada ACTIVA» SÍ se puede decir**, y es la excepción que confirma la regla: estuvo prohibida
hasta que el robot empezó a publicar su bandera y el flanco `false → true` se presenció **con el
robot en marcha, desde los dos lados a la vez**. Pasó de suposición a dato. **Solo se usa con
`/estado_robot` en la mano**; si no llega, la respuesta es «no se sabe», **nunca** «no está
puesta».

---

## §4 · El mapa — diez pantallas y tres recorridos que no se cruzan

| # | Pantalla | Ruta | Prioridad |
|---|---|---|---|
| 1 | Portada | `/` | imprescindible |
| 2 | Muro de flota | `/flota` | imprescindible |
| 3 | Marco del robot (armazón) | `/robot/[id]/*` | imprescindible |
| 4 | Taller del alumno | `/robot/[id]` | imprescindible · **NO CONSTRUIDO** |
| 5 | Por qué no obedece | `/robot/[id]/no-obedece` | imprescindible · ruta nueva |
| 6 | Conducir | `/robot/[id]/conducir` | imprescindible |
| 7 | Telemetría | `/robot/[id]/telemetria` | imprescindible |
| 8 | LIDAR | `/robot/[id]/lidar` | importante |
| 9 | Diagnóstico | `/robot/[id]/diagnostico` | imprescindible |
| 10 | Cuaderno de medidas | `/cuaderno` | importante |

**El profesor** entra directamente en `/flota` —puede ponerla como página de inicio, porque la
portada no guarda ningún estado que haya que atravesar— y normalmente no sale de ahí. Cuando una
baldosa pide algo, **la ficha de causa se abre EN SITIO, sin navegar**. Si decide mirar más, el
identificador de la baldosa lleva a **`/robot/NN/no-obedece`**, no a Conducir: su pregunta es
«por qué», no «cómo lo muevo».

**El alumno** entra por la portada la primera vez, elige su robot, y a partir de ahí llega
directo a `/robot/NN` (el Taller), que es la ruta índice. El marco le da la franja de seguridad
con la parada y el voltaje **en las seis pestañas**, así que no cambia de pantalla para saber si
el robot está vivo. Al medir con la cinta sale a `/cuaderno`, que es de nivel superior a
propósito: no abre socket, sobrevive a cambiar de robot y **funciona hoy**. El alumno no pasa
nunca por `/flota`: tiene un robot delante y lo está tocando.

**Quien monta** vive en `/robot/NN/diagnostico`, al que llega por URL directa o desde la ficha de
la baldosa. Es el único que recorre las seis pestañas, y es quien paga el LIDAR.

**Tres reglas de navegación que no son organización sino coste y seguridad:**

1. **El socket es del marco.** Se abre y se cierra en `app/robot/[id]/layout.tsx` + `MarcoRobot`,
   así que cambiar de pestaña **no multiplica el caudal ni reconecta**.
2. **El LIDAR tiene ruta propia justamente para que su suscripción muera al salir.** Metido
   dentro de Telemetría pagaría el 83 % del tráfico mientras alguien mira la batería.
3. **Nada navega solo.** El muro no salta a un robot porque se ponga en coral, y la portada no
   redirige.

---

## §5 · Las diez pantallas

> Cada tarjeta tiene el mismo esqueleto: **Trabajo · Quién la usa · Primera lectura ·
> Composición · Campos · Estados · Copia literal · Prohibido aquí · Prompt para Stitch.**
>
> **La «copia literal» se pega tal cual.** No se reescribe, no se resume, no se redondea ninguna
> cifra. Las cifras de este documento están medidas en el robot y una versión «más limpia» de
> ellas es una mentira.

---

### 5.1 · Portada — `/`

**Trabajo.** Llevar al muro o a un robot en un clic, y **declarar de forma permanente** que no
hay control de acceso y qué no existe todavía.

**Quién la usa.** Todos la primera vez. El profesor puede saltársela poniendo `/flota` como
página de inicio, y eso es un caso previsto, no un descuido.

**Primera lectura.** El titular y los **dos destinos**, lado a lado y del mismo peso. Justo
debajo, sin plegar y sin tener que desplazar, **la casilla permanente de lo que no funciona**.
No es una pantalla de bienvenida: es una declaración con dos puertas.

**Composición.**

1. **Titular de pantalla** en degradado blanco → `#A8B0C8`, y una frase de 52ch debajo diciendo
   qué es esto.
2. **Dos tarjetas de vidrio grandes, lado a lado.** «Los 16 de un vistazo» (lleva a `/flota`) y
   «Un robot», con una rejilla de dieciséis píldoras numeradas `01`–`16`. Si hay un último robot
   usado, se marca — y la etiqueta dice **«es una preferencia guardada, no una identidad»**.
3. **Tarjeta ámbar permanente «Lo que todavía no funciona».** Dos filas: el terminal no existe,
   y Nav2 / el mapa del aula no están arrancados.
4. **Tarjeta neutra permanente «No hay control de acceso».** Es la única pantalla donde esto se
   declara entero, y por eso no puede depender de que alguien pase por aquí: se repite en el
   Taller y en Diagnóstico.
5. **Enlace a `/cuaderno`**, en una línea, al pie. No abre socket y funciona hoy.

🔴 **Cero telemetría y cero sockets.** Esta pantalla **no abre dieciséis conexiones para
pintarse**, y por eso no puede llevar ningún contador de robots en línea.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| Los dieciséis identificadores | `ROBOTS` de `lib/interfaz/identidad.ts`. **No es telemetría** | píldoras `01`–`16`, Geist, no mono | siempre hay: son 1..16 fijos |
| Último robot usado | `localStorage` de **este** navegador | píldora marcada + la frase «preferencia guardada, no identidad» | ninguna píldora marcada. No se elige uno por defecto |
| Lo que no funciona | constante escrita a mano en el repositorio | dos filas de texto, ámbar, permanentes | no aplica: es texto, no un dato |
| Control de acceso | hecho del sistema: rosbridge 2.7.0 no trae autenticación | párrafo neutro permanente | no aplica |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| Primer uso | las dos tarjetas, ninguna píldora marcada, las dos casillas permanentes | «Elige los dieciséis o un robot. Aquí no hay nada que cargar: esta pantalla no habla con ningún robot» |
| Con un robot recordado | la píldora de ese robot marcada, con su nota | «La última vez entraste en rvr-07. Es una preferencia guardada en este navegador, no una identidad: la plataforma no puede saber quién eres» |

**Copia literal.**

```
Laboratorio Atriz

Dieciséis Sphero RVR en el aula, gobernados desde el navegador. Esta portada no habla
con ningún robot: solo lleva a donde se habla con ellos.

Los 16 de un vistazo — el muro dice a cuál hay que levantarse.
Un robot — su taller, su mando y su telemetría.

Es una preferencia guardada en este navegador, no una identidad. La plataforma no puede
saber quién eres.

🔴 No hay control de acceso. rosbridge 2.7.0 no trae autenticación: `rosauth` no es
dependencia, no existe el parámetro `authenticate`, y `check_origin()` devuelve `True`
sin mirar nada. Cualquiera que esté en la red del aula y sepa la dirección puede mover
cualquier robot publicando en `/cmd_vel_raw`, y ya se midió un navegador de otra subred
abriendo `ws://rvr-01.local:9090`. Se cerrará con un proxy que valide el testigo en cada
robot, con rosbridge atado a 127.0.0.1: no está construido.

Aquí no hay ninguna pantalla de inicio de sesión, y no es un olvido: fingir un control de
acceso que no protege nada sería peor que no tenerlo.

Lo que todavía no funciona
· El terminal del alumno no existe. Se puede ver la forma que tendrá, y nada más.
· La navegación (Nav2) y el mapa del aula no están arrancados: `atriz-nav.service` está
  instalada y NO habilitada, y no existe el mapa.
```

**Prohibido aquí.** Cualquier telemetría; abrir sockets; un contador «N de 16 en línea» (eso solo
lo diría `/estado_robot.latido` avanzando, que está **NO VERIFICADO**, y además un contador
esconde **cuál** de los dieciséis); una pantalla de inicio de sesión; decir «tu robot».

**🎨 Prompt para Stitch — Portada**

```
Pantalla de portada de un laboratorio universitario de robótica, en español, oscura.

Fondo: pozo #07080D con dos orbes de luz desenfocados a 90 px y FIJOS — uno arriba a la
izquierda de 620 px en rgba(91,140,255,0.34), otro a la derecha de 560 px en
rgba(34,211,238,0.20).

Contenido, centrado, ancho máximo 6xl:
1. Titular «Laboratorio Atriz» en Geist 650, clamp(2,5rem,6vw,4,875rem), tracking −0,045em,
   con degradado de blanco a #A8B0C8. Debajo, un párrafo de 52 caracteres de ancho en
   #8B90A3, 16 px.
2. Dos tarjetas de vidrio grandes en fila (rgba(255,255,255,0.045), borde 1 px
   rgba(255,255,255,0.09), blur 20 px, radio 20 px, sombra 0 18px 40px -22px rgba(0,0,0,.7)):
   «Los 16 de un vistazo» y «Un robot». La segunda contiene una rejilla de 16 píldoras
   numeradas 01–16, una de ellas marcada en azul eléctrico #5B8CFF con una nota debajo.
   Cada tarjeta lleva una flecha DENTRO de un círculo propio pegado al borde derecho.
3. Debajo, a lo ancho, una tarjeta ámbar (borde y fondo al 12 % de #FBBF24) titulada
   «Lo que todavía no funciona», con dos filas de texto.
4. Debajo, otra tarjeta de vidrio en tono neutro titulada «No hay control de acceso», con
   tres párrafos de texto denso.
5. Al pie, un enlace de texto a «Cuaderno de medidas».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla, sin reescribirlos.

Movimiento: entrada escalonada de las tarjetas, 60 ms entre una y la siguiente, subiendo
18 px, 720 ms, cubic-bezier(0.23,1,0.32,1). SOLO al montar. Nada más se mueve.

NO dibujes: ningún dato de telemetría, ningún contador de robots en línea, ningún indicador
de conexión, ninguna pantalla de inicio de sesión, ningún avatar ni nombre de usuario.

Aplica además la sección §8 entera (lo que esta plataforma NO puede hacer).
```

---

### 5.2 · Muro de flota — `/flota`

**Trabajo.** Decir **a cuál de los dieciséis hay que levantarse**, leído desde tres metros y
antes de leer una palabra. **No conduce nada: cuenta.**

**Quién la usa.** El profesor, de reojo y sin dejar de hablar. Quien monta, en los dos primeros
minutos de clase.

**Primera lectura.** Lo primero que se lee, **a tres metros y sin leer una palabra**, es
**cuántas baldosas son bloque de color y cuáles**: el campo de color contra el vidrio. Trece de
vidrio y tres de color mandan el ojo solo, y ese conteo **ya es la respuesta** a «¿tengo que
levantarme?». Segundo, dentro de un bloque, el identificador y el número fantasma recortado por
el canto. Tercero, el voltaje en mono a 2,4 rem. Cuarto, y ya de cerca, las etiquetas cortas de
motivo.

**El galón** —la trama diagonal del canto izquierdo— se lee a la vez que el color y sobrevive a
un proyector que desatura. Y el caso de **las dieciséis baldosas apagadas y en una línea se lee
como LA RED**, no como dieciséis averías: es **un dibujo distinto, no un color distinto**.

**Composición.** De arriba abajo, ancho máximo 7xl, sobre el pozo con los dos orbes **fijos**.

**1 · CABECERA.** Izquierda: titular «Flota Atriz» en degradado y, debajo, la frase de qué es
esto en 52ch. Derecha, en una fila que envuelve:

- dos **pastillas de vidrio** con el presupuesto —«POR ROBOT 0,48 kB/s» y «LOS 16 7,68 kB/s»,
  mono 21 px— y **pegada a ellas, sin plegar, la advertencia de que la cifra no está completa**,
  porque el muro también escucha `/estado_robot` y su caudal no está medido;
- botón **«Modo proyección»**, que conmuta `data-tema` en la raíz y lo guarda en este navegador.
  **Nunca `prefers-color-scheme`**;
- conmutador de orden con dos posiciones etiquetadas: **«Orden: por número»** (por defecto) y
  **«Orden: por voltaje»**.

**2 · «DÓNDE BUSCAR A LOS ROBOTS»**, plegado y **cerrado**, justo encima de la rejilla. Es
configuración de red **de este navegador**, no estado del robot: por eso se pliega, y por eso
plegarlo **no contradice** la regla de que los motivos no se pliegan nunca. El resumen visible
dice «todos por nombre» o «N con dirección puesta». Abierto: dieciséis filas `rvr-NN` con un
campo de IP (validación IPv4 estricta) y una segunda columna, **«sitio en el aula»**, texto
libre, **rotulada como escrita a mano** y nunca mezclada con la telemetría.

**3 · REJILLA 4×4** (`grid-cols-2 sm:grid-cols-3 lg:grid-cols-4`, hueco 12 px). Entrada
escalonada de 60 ms por baldosa, **en CSS y solo al montar**; reordenar por voltaje **no la
vuelve a disparar** y **no anima el reacomodo**: el muro no baraja sus fichas.

- **3a · BALDOSA DE VIDRIO** (no se llega al robot): **una sola línea de contenido**.
  Identificador tenue arriba a la izquierda, píldora de borde a la derecha («abriendo …» o «no
  llego»), y abajo una raya `—` en mono con `title="no se sabe"` más «último dato: nunca».
  **Sin galón, sin voltaje, sin motivos, sin sombra.**
- **3b · BALDOSA DE BLOQUE** (color a plena saturación: este robot pide algo). Galón de 10 px al
  canto izquierdo, paso 14 px si MIRAR y 6 px si IR; **NINGUNA no lleva galón**. Número fantasma
  recortado abajo a la derecha. Fila superior: identificador enorme + píldora con la palabra («en
  línea», «sin telemetría», «mirar», «hay que ir»). Bloque inferior: **voltaje mono 2,4 rem** con
  la unidad al 36 % y, en segunda línea de 11,5 px, su antigüedad. Debajo, la lista de etiquetas
  de motivo, **TODAS**, en línea y envolviendo, **sin desplegable**. Debajo, cuando toque, la
  cursiva de vigencia y la nota de temperatura repetida.
- **3c · La baldosa deja de ser un enlace entero.** El **identificador es el enlace** y lleva a
  «Por qué no obedece» de ese robot; el resto de la superficie es un botón **«por qué»** que abre
  la **ficha de causa en sitio**, dentro de la propia celda, empujando la rejilla hacia abajo,
  **sin navegar y sin tapar el muro con un modal**. (Anidar un botón dentro de un `<a>` no es
  válido, y esta separación es además la que pide el encargo.)
- **3d · FICHA DE CAUSA.** Los motivos **largos completos**, en el mismo orden que las etiquetas;
  las tres causas de SIN_DATOS **listadas sin elegir**, con la nota de por qué no se puede
  elegir; los **tres relojes** de `/motor_status` en una lista de definición —atasco, fallo,
  térmico— con «no se sabe» donde vale −1,0; el latido del nodo con **las dos lecturas** que
  hacen falta para creerlo; y el **sello de verificación** de cada campo que lo necesita.

**4 · LEYENDA DEL IDIOMA**, en una línea: *bloque de color = pide algo · vidrio = sin novedad o
no se llega · galón denso = hay que ir.*

**5 · «CÓMO LEER ESTE MURO»**, tarjeta de vidrio con las cuatro reglas: rojo solo por un hecho,
«sin señal de vida» no es avería, la batería en voltios, y el umbral de 5 s que es **de este
muro** y no se intercambia con el de la ficha de un robot.

**6 · PIE**, sin adornos: qué **no** puede saber este muro.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Identificador del robot** | no es telemetría: `ROBOTS` de `lib/interfaz/identidad.ts`. Es el número pintado en el robot, no la dirección | `rvr-NN`, semibold, `clamp(1,5rem, 3,2vw, 2,4rem)`, **NO monoespaciado** (es un nombre). En vidrio, mismo texto en color tenue y un paso más pequeño | siempre hay: son 1..16 fijos. Si el segmento no nombra a ninguno, la ruta responde **404** y no se adivina un robot por defecto |
| **Voltaje de batería** | `/battery_state.voltage`, cada **30,0 s exactos** | «8,28 V» mono, 2,4 rem, coma decimal, unidad al 36 %. Atenuado al 60 % si no hay latido | **«no se sabe»** a 1,25 rem y opacidad 0,7 —nunca 0,00 V ni casilla vacía— y además la etiqueta «batería: no se sabe» entre los motivos: el driver publica NaN cuando la lectura falla |
| **Nivel de batería** | derivado: `nivelBateria(voltios)` contra **7,0** y **6,5 V**, umbrales del firmware | palabra junto al número: «baja» o «CRÍTICA». **OK no escribe nada**: el silencio ya es la ausencia de novedad | DESCONOCIDO se escribe «no se sabe» y **NO se pinta como OK** — `nivelBateria(NaN)` devolvía OK y era un bug corregido |
| **Antigüedad del voltaje** | `msDesdeUltimo('/battery_state')` | «hace 12,4 s», 11,5 px, tenue, debajo del número. Por encima de 45 s (30 de cadencia + margen), «hace más de 45 s» | «aún no ha llegado ninguno». **Ningún número de esta pantalla se pinta sin su antigüedad** |
| **Latido del muro** | `msDesdeUltimo('/motor_status')` contra **`UMBRAL_LATIDO_MURO_MS = 5000`** = cinco mensajes perdidos a 1 Hz | no se pinta como número en la baldosa: decide **estado y vigencia**. En la ficha sí | `null` = no ha llegado ninguno = SIN_DATOS. 🔴 **Jamás los 3000 ms de `/odom`**: sobre 1 Hz serían tres mensajes |
| **Estado del enlace** | derivado: WebSocket conectado + latido fresco → SIN_CONEXION / EN_LINEA / SIN_DATOS | píldora de borde arriba a la derecha: «abriendo», «no llego», «en línea», «sin telemetría» | no aplica: los tres estados cubren el espacio entero. «abriendo» solo existe mientras no se agote `PLAZO_CONEXION_MS` (10 s) |
| **Atención** | derivado: `resumirBaldosa().atencion` → NINGUNA / MIRAR / IR | **tres códigos redundantes a la vez**: color del bloque (cobalto / lima / coral), palabra en la píldora, y paso del galón (sin galón / 14 px / 6 px) | **IR jamás sale de un hueco**: exige un hecho positivo Y vigente. Sin latido lo máximo es MIRAR, que es justo la acción que deshace la duda |
| **Motivos** | derivado: `.etiquetas` (cortas, en la baldosa) y `.motivos` (largos, en la ficha), construidos juntos y en el mismo orden | lista en línea de 11,5 px con viñeta `·`, **todas visibles**, envolviendo. Peor caso real: 6 motivos, el más largo de 155 caracteres | lista vacía = no hay nada que decir. **Nunca se rellena con «todo bien»** |
| **Atasco** | `/motor_status.atascado_izquierdo \| atascado_derecho`, filtrados por `antiguedad_atasco_s` | etiqueta «atasco»; en la ficha, la frase entera y **qué oruga**. Único motivo confirmado por notificación del firmware (3 de 3) | `−1,0` ⇒ `null` ⇒ **no se dice nada**. Las banderas valen `false` por ser su valor inicial, no porque nadie haya comprobado nada |
| **Parada de emergencia** | `/estado_robot.parada_emergencia`, 1,000 Hz | etiqueta «parada puesta» y atención **MIRAR**, no IR: es un estado normal del aula. ✅ **Único campo de este topic VERIFICADO** contra hardware | `null` ⇒ «no se sabe», **nunca** «no está puesta». El silencio no es un no |
| **¿Contesta el RVR?** | `/estado_robot.rvr_responde` | etiqueta «el RVR no contesta» y atención MIRAR: cargando con la Pi viva es lo más cotidiano | `null` ⇒ nada. ⏳ En la ficha, el sello: **este campo nunca se ha visto en `false`** |
| **Odometría muerta** | `/estado_robot.antiguedad_muestra_s` y `.antiguedad_odom_s` contra `UMBRAL_ODOM_MUERTA_S = 3 s` | etiqueta «odometría muerta» y atención **IR**: es el único hueco que un robot sano no delata por ningún otro camino | cualquiera de los dos relojes en −1,0 ⇒ no se afirma nada. ⏳ Sello: el discriminador solo se ha visto **sano** |
| **Latido del nodo** | `/estado_robot.latido`, contador monótono, comparado con la **lectura anterior** | solo en la ficha: «avanza» / «no avanza entre dos lecturas», con los dos valores. El topic va TRANSIENT_LOCAL: puede venir **latcheado de un nodo ya muerto** | con una sola lectura, «aún no se sabe»: un número suelto no prueba nada, lo que prueba es que **se mueva** |
| **Reanudaciones fallidas** | `/estado_robot.reanudaciones_fallidas` | solo en la ficha: `0` · `1-2` «pudo ser una siesta» · `>2` «el RVR no está ahí». ⚠️ **Lectura razonada, NO umbral calibrado** | no llega el topic ⇒ no se pinta la fila. **No se sustituye por 0** |
| **Los tres relojes de motores** | `.antiguedad_atasco_s`, `.antiguedad_fallo_s`, `.antiguedad_termico_s` | en la ficha, lista de definición con «hace 12,4 s» cada uno. Separados porque las tres fuentes son distintas | `−1,0` = «nunca se ha sabido nada», **jamás 0 s**: un cero aquí sería afirmar una comprobación que no se hizo |
| **Temperatura repetida** | derivado: `antiguedad_termico_s > 35 s` | línea de 11,5 px: «La temperatura publicada es el mismo dato repetido: el sondeo va cada 30 s». **NO sube la atención** | frescura desconocida ⇒ no se pinta la línea ni se pinta una temperatura |
| **Fallo eléctrico** | `/motor_status.fallo`, filtrado por `antiguedad_fallo_s` | solo en la ficha, con su antigüedad. **Aquí sí**, `false` significa «se comprobó y no hay»: se sondea cada 30 s | `−1,0` ⇒ «no se sabe». Y **se dice, no se calla** |
| **Dónde buscar a este robot** | no es telemetría: `localStorage` de **este** navegador | fila del cuadro plegado, mono 12 px, con «por nombre» o el motivo del rechazo al lado | vacío = «por nombre». No escanea, no descubre y **no comprueba que la dirección responda** |
| **Sitio en el aula** | no es telemetría: texto escrito por una persona | segunda columna del cuadro plegado y, en la ficha, una línea rotulada **«escrito a mano · nadie lo comprueba»**, en tipo de texto y **nunca en mono** | vacío = «nadie lo ha escrito». No se infiere de nada |
| **Presupuesto de red** | `caudalDeFlota(TOPICS_MURO, 1)` y `(…, 16)` sobre `CAUDAL_KBS`, medido en el robot | dos pastillas mono: **0,48 kB/s** por robot · **7,68 kB/s** los dieciséis, con la lista de topics en `code` | 🔴 la baldosa también escucha `/estado_robot` y ese topic **no tiene caudal medido**, así que junto a las pastillas va escrito que **la cifra se queda corta y no se sabe en cuánto** |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso · el muro se acaba de abrir** | Dieciséis baldosas de vidrio en una línea, píldora «abriendo» con los segundos transcurridos, refrescados cada 500 ms. Sin galón, sin color, sin números. **Nada parpadea: lo único que cambia es una cifra** | «abriendo · 4,0 s sin respuesta todavía». Un WebSocket que no abre **no da error** —ni `onerror`, ni `onclose`, ni excepción—, así que hasta que se agotan los 10 s el navegador todavía no sabe nada. Decir «no llego» antes sería afirmar un fallo que no consta |
| **No llego · una baldosa** | Vidrio apagado, una sola línea: identificador tenue, píldora «no llego», raya `—` y «último dato: nunca». El resto del muro sigue en color | El contraste **es** el mensaje: una baldosa apagada entre quince vivas salta a la vista sin necesidad de rojo. La ficha añade: «no hay WebSocket abierto con el robot, así que no se sabe nada de él. Eso NO es una avería» |
| **No llego · las dieciséis a la vez** | Dieciséis baldosas apagadas e idénticas, y **una banda sobria** bajo la cabecera —no roja, no de alarma— que cuenta 16 de 16 y explica el patrón | «Ninguna de las dieciséis conexiones ha abierto. Cuando fallan las dieciséis a la vez, lo que suele estar mal es esta red o este navegador, no dieciséis robots. Desde aquí no se puede comprobar.» **Nunca dice que la red esté caída: no lo sabe** |
| **Sin telemetría · el enlace va y no llega `/motor_status`** | Bloque **lima**, galón de paso 14 px, píldora «sin telemetría», etiquetas «sin señal de vida · la Pi calla», y **todo lo numérico atenuado al 60 %** con la cursiva de vigencia debajo | «Lo de arriba es lo último que se supo, de antigüedad desconocida.» En la ficha, **las tres causas sin elegir** y por qué no se elige: distinguir la tercera exigiría mantener `/scan`, que es el 83 % del tráfico |
| **En línea, nada que hacer** | Bloque **cobalto SIN galón**, píldora «en línea», voltaje con su antigüedad, sin lista de motivos | Nada más. «Este robot está vivo» ya es algo que decir cuando quince no lo están, **pero no se adorna con una palabra de aprobación**: el muro no dice «OK», dice qué sabe y cuándo lo supo |
| **Mirar** | Bloque **lima**, galón a 14 px, píldora «mirar», y las etiquetas de todos los motivos | El motivo **ES** la acción, así que va visible y nunca plegado. Ninguno de estos manda a cruzar el aula: la parada puesta y el RVR sin contestar son estados normales, y gastar el aviso fuerte en ellos **quemaría el que sí importa** |
| **Hay que ir** | Bloque **coral**, galón a 6 px —el doble de denso, legible aunque el proyector se coma el color—, píldora «hay que ir» y la etiqueta del hecho | Solo tres cosas lo producen, **y las tres son hechos positivos y vigentes**: atasco confirmado, voltaje por debajo de 6,5 V, u odometría muerta |
| **No construido** | Dos casillas **nombradas**, no dos huecos: (a) el identificador enlaza a «Por qué no obedece», que hoy no existe → lleva a `/diagnostico` y lo dice al pasar el ratón; (b) el modo proyección está marcado PENDIENTE | «Por qué no obedece — todavía no está construida. Este enlace lleva mientras tanto al diagnóstico de ese robot.» · «Modo proyección — lo aprueba una persona a tres metros del muro, no una prueba automática» |

**Copia literal.**

```
Flota Atriz

Dieciséis Sphero RVR en el aula. Los que están en color piden algo; los de vidrio, no.
Este muro cuenta a cuál hay que levantarse: no conduce nada.

abriendo · 4,0 s sin respuesta todavía

no llego · último dato: nunca

Ninguna de las dieciséis conexiones ha abierto. Cuando fallan las dieciséis a la vez, lo
que suele estar mal es esta red o este navegador, no dieciséis robots. Desde aquí no se
puede comprobar.

«Sin señal de vida» no es una avería. Un robot cargando —RVR apagado con la Raspberry Pi
encendida— es el estado más común del laboratorio, y se ve igual que uno dormido.

Lo de arriba es lo último que se supo, de antigüedad desconocida.

El latido de este muro dice que la Raspberry Pi está publicando, no que el robot esté
bien: /motor_status se republica cada segundo desde el último valor conocido y llega
igual con el RVR mudo. Del robot hablan «el RVR no contesta» y «odometría muerta».

batería: no se sabe — /battery_state no ha traído un voltaje válido, y el driver publica
NaN cuando la lectura falla. Esta baldosa NO está diciendo que esté bien.

La batería se lee en voltios contra 7,0 y 6,5 V, que son los umbrales del propio
firmware. El porcentaje marcó 100 % con la batería a 8,29 V.

Orden por voltaje · los que no se saben van al final y aparte: un voltaje que falta no es
alto ni bajo. Sin histórico ni tendencia — aquí no se guarda nada, y una gráfica sería
telemetría inventada.

Modo proyección — lo aprueba una persona a tres metros del muro, no una prueba automática.

Dónde buscar a los robots · todos por nombre. Por defecto cada baldosa busca
rvr-NN.local; escribe una IP y esa baldosa irá directa. Se guarda en este navegador, no
en el robot, y nadie comprueba que la dirección responda.

Este muro paga /battery_state + /motor_status: 0,48 kB/s por robot, 7,68 los dieciséis.
También escucha /estado_robot, y su caudal NO está medido: la cifra de arriba se queda
corta y no se sabe en cuánto.

bloque de color = pide algo · vidrio = sin novedad o no se llega · galón denso = hay que ir
```

**Prohibido aquí.**

- Un **porcentaje de batería**, ni como dato principal, ni como criterio de color, ni como barra
  de nivel.
- **Rojo, «hay que ir» o cualquier alarma nacida de un hueco.** Con dieciséis robots cargando
  —el estado cotidiano—, adivinar saca la flota entera en rojo, y **un muro siempre rojo se
  ignora**.
- **Plegar los motivos**, las causas de SIN_DATOS o los relojes tras un desplegable. El motivo ES
  la acción.
- Suscribirse a `/scan`, `/odom`, `/imu` o a cualquier topic **sin caudal medido**; apoyarse en
  `throttle_rate` como si protegiera; mandar campo `qos` en un `subscribe`.
- Un cero, `--`, `0,00 V`, `0 s` o una casilla vacía donde no hay dato.
- **Histórico, tendencia, sparkline, media o cualquier serie temporal**: no hay persistencia en
  ningún sitio.
- Un botón de parada de emergencia **en el muro** (ver §7).

**🎨 Prompt para Stitch — Muro de flota**

```
Muro de flota de un laboratorio de robótica con 16 robots, en español, oscuro, pensado para
leerse a TRES METROS y a veces proyectado.

Fondo: pozo #07080D con dos orbes de luz desenfocados a 90 px y FIJOS (620 px arriba a la
izquierda en rgba(91,140,255,0.34); 560 px a la derecha en rgba(34,211,238,0.20)).

Cabecera: a la izquierda, titular «Flota Atriz» con degradado blanco→#A8B0C8 y una frase
descriptiva de 52 caracteres de ancho. A la derecha, en una fila que envuelve: dos pastillas
de vidrio con «POR ROBOT 0,48 kB/s» y «LOS 16 7,68 kB/s» en mono 21 px, con una nota de dos
líneas pegada debajo; un botón «Modo proyección»; y un conmutador de dos posiciones
etiquetadas «Orden: por número» / «Orden: por voltaje».

Debajo, un panel plegado y CERRADO titulado «Dónde buscar a los robots · todos por nombre».

Debajo, rejilla 4×4 (16 celdas, hueco 12 px) con DOS TIPOS DE BALDOSA claramente distintos:

· BALDOSA DE VIDRIO (dibuja 12 así): rgba(255,255,255,0.045), borde 1 px
  rgba(255,255,255,0.09), blur 20 px, radio 20 px, SIN sombra. Una sola línea de contenido:
  identificador «rvr-04» tenue arriba a la izquierda, píldora de borde «no llego» a la
  derecha, y abajo una raya «—» en mono con «último dato: nunca». Sin galón, sin voltaje,
  sin motivos.

· BALDOSA DE BLOQUE (dibuja 4 así, no más): color a PLENA SATURACIÓN, sin blur y sin borde,
  radio 20 px. Dos en cobalto #2B4BF2 con la píldora «en línea» y SIN galón; una en lima
  #B6E01E con píldora «mirar» y galón de trama diagonal a 45° de paso 14 px pegado al canto
  izquierdo; una en coral #FF5C39 con píldora «hay que ir» y el mismo galón a paso 6 px.
  Dentro de cada bloque: identificador «rvr-07» en Geist 600 a clamp(1,5rem,3,2vw,2,4rem)
  (NO monoespaciado), un número fantasma gigante recortado por el canto inferior derecho al
  13 % de opacidad, el voltaje «8,28 V» en Geist Mono 2,4 rem con la unidad al 36 % del
  tamaño, debajo «hace 12,4 s» a 11,5 px, y debajo una lista en línea de etiquetas cortas de
  motivo con viñeta «·», TODAS visibles y envolviendo, sin ningún desplegable.

Una de las baldosas de bloque tiene abierta su FICHA DE CAUSA: se abre EN SITIO dentro de la
propia celda, empujando la rejilla hacia abajo — NO es un modal. Contiene los motivos largos
completos, una lista de tres causas posibles sin elegir entre ellas, y una lista de
definición con tres relojes donde dos dicen «no se sabe».

Al pie: una línea de leyenda, una tarjeta de vidrio «Cómo leer este muro» con cuatro reglas,
y un pie con lo que este muro NO puede saber.

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

Movimiento: entrada escalonada de 60 ms por baldosa al montar, y nada más. Ningún punto que
parpadee, ningún pulso, ninguna barra de progreso.

NO dibujes: porcentaje de batería, barra de nivel de batería, gráficas, sparklines, un
contador «N de 16 en línea», ni un botón de parada de emergencia.

Aplica además la sección §8 entera.
```

---

### 5.3 · Marco del robot — armazón persistente de `/robot/[id]/*`

**Trabajo.** Ser el **dueño del único WebSocket** de este robot y tener **la parada de emergencia
y el estado real delante en TODAS las pestañas**, sin depender de cuál esté activa.

**Quién la usa.** Los tres roles. **Es la única superficie que ninguno puede evitar.**

**Primera lectura.** Hay dos «primeros» y no compiten, porque uno no se lee. Lo primero que se
**encuentra** es la **banda roja de la parada**: ancho completo, sin nada que comparta su fila, y
anclada (`sticky top-0`) para que **ningún desplazamiento de ninguna pestaña la saque de la
pantalla**. Se localiza por **forma y color**, no por texto. Lo primero que se **lee** es la línea
de **identidad y destino**: `rvr-07` en grande con `ws://rvr-07.local:9090` en mono justo debajo,
porque cuando algo no responde la primera pregunta es **si estás hablando con el robot que
crees**.

**El orden vertical es: identidad (renglón fino) → parada (banda alta) → hechos del robot (tira
de datos) → pestañas.** Los datos van **después** de la parada a propósito: ningún número, por
interesante que sea, puede empujar el botón fuera de la vista.

**Composición.**

**Dónde vive.** `app/robot/[id]/layout.tsx` es de **servidor** y solo espera `params`, interpreta
el identificador y responde 404 si el segmento no nombra un robot. Todo lo demás es `MarcoRobot`,
cliente. Navegar entre pestañas **no desmonta el layout** → el WebSocket no se corta; cambiar de
robot **sí** lo desmonta → se cierra el socket viejo antes de abrir el nuevo.

**🔴 Cambio estructural obligatorio: el marco pasa a ser dueño también de LA teleoperación.** Si
el marco monta su propia instancia para la parada, `paradaEmergencia()` cortaría **su** bucle y
**no el `setInterval` de 10 Hz de Conducir**: el navegador seguiría publicando `cmd_vel_raw`
contra un robot con la bandera puesta, y al liberarla presencialmente **el robot arranca** — la
forma exacta del cuarto fallo histórico (34,7 cm contra 0,0). → **El marco crea la única
`Teleoperacion` y la reparte por contexto**; Conducir y Taller la consumen, y sus botones de
parada locales **desaparecen**.

**1 · Renglón de identidad y destino** (alto ~44 px). Izquierda: `rvr-07` a 24-30 px semibold y
debajo, en **mono 12 px atenuada**, `ws://rvr-07.local:9090` — **dos renglones, no dos cosas en la
misma línea base**: identidad y destino son preguntas distintas. Derecha: insignia de enlace, el
literal «socket abierto» / «socket cerrado», y el enlace **«ver los 16»**. Con el identificador
siendo una IP, el nombre grande **es** la IP y bajo él la misma URL: se ve que estás en el
override y no en mDNS.

**2 · Banda de seguridad**, ancho completo, **borde de 4 px** del color reservado, **sin sombra**.
Dentro, y en este orden:

- a) el botón **PARADA DE EMERGENCIA**, alto ~64 px, mayúsculas, **100 % del ancho**;
- b) **la tira de tres testigos**, separados por filetes de 1 px y **jamás fundidos en un solo
  verde**: `salió por el WebSocket` (hecho del navegador) · `el robot dice que su bandera está
  puesta` (`/estado_robot.parada_emergencia`) · `no se sabe`. Cada casilla con su tono y su
  antigüedad. **Una casilla apagada es un hueco declarado, no un «no»**;
- c) cuando la parada salió y la bandera no lo confirma, **el cronómetro**, en mono, corriendo a
  500 ms;
- d) el párrafo fijo de **cómo se libera presencialmente**, siempre visible, 12 px.

🔴 El estado del resultado (salió / no salió, hora, cronómetro) **vive en el marco**, no en el
componente del botón: si vive en el botón se pierde al cambiar de pestaña, **que es justo cuando
hace falta**.

**3 · Tira de hechos baratos**, tres o cuatro celdas: **voltaje + antigüedad**, **último `/scan` +
su advertencia**, **`/estado_robot`: latido y antigüedad de `/odom` según el robot**. **Sin
porcentaje de batería.**

**4 · Barra de pestañas**, montada sobre el borde inferior de la banda, con la **lengüeta activa
del color del suelo** y un filete de 2 px. Orden: **Taller · Conducir · No obedece · Telemetría ·
LIDAR · Diagnóstico**. Una pestaña no construida **sigue navegando** a una página que explica qué
falta —nunca un enlace muerto ni desactivado sin motivo— y lleva la marca **«no construido»** en
la propia lengüeta. Hoy pone «(bloqueado)», que sugiere un permiso; **lo que pasa es que no
existe**.

**5 · `<main>`**, `max-w-6xl`, con la pestaña activa. Único elemento que se desplaza bajo la banda
anclada.

**Lo que el marco paga, en números medidos:** `/odom` **13,05 kB/s** —lo único calibrado contra
los 3 s de silencio—, `/battery_state` **0,03**. `/estado_robot` **no tiene caudal medido**, así
que no se presupuesta a ojo: **se dice que falta medirlo**. Varias suscripciones al mismo topic
se deduplican: son **una** suscripción ROS, no dos.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Robot** | segmento `[id]` → `interpretarIdRobot()` / `etiquetaRobot()` | «rvr-07» a 24-30 px semibold. Con override por IP, la IP literal en el mismo hueco | no puede faltar: si el segmento no nombra robot, **404** en vez de adivinar |
| **Destino** | `urlDeRobot(...)` | «ws://rvr-07.local:9090» mono 12 px atenuada, **en su propio renglón** | no puede faltar: se construye del segmento |
| **Socket** | `conectado`, muestreado cada 500 ms | texto literal «socket abierto» / «socket cerrado», 12 px | arranca en «socket cerrado» y puede ir **hasta 500 ms por detrás al ABRIR**. Se dice, no se disimula |
| **Enlace** | `evaluarSalud()` sobre conectado + `msDesdeUltimo('/odom')` | insignia: NEUTRO «no llego al robot» · BIEN «en línea» · ATENCIÓN «el enlace va y el robot no manda telemetría» | SIN_DATOS es **ámbar, nunca rojo**, y arrastra **las tres causas sin elegir** |
| **Plazo de conexión** | `PLAZO_CONEXION_MS` (10 000) contra un reloj propio | «3,5 s de los 10» en mono, avanzando cada 500 ms. **Números, no una barra que gire** | solo se pinta mientras el socket no esté abierto. Es una cuenta **del navegador**, con granularidad de 500 ms, y se dice así |
| **Aviso del transporte** | `ultimoAviso` | componente de aviso nivel ERROR con **el mensaje literal**, sin reescribirlo | no se pinta nada. **Su ausencia NO significa que el enlace vaya**: rosbridge no manda «status» |
| **Bandera de parada del robot** | `/estado_robot.parada_emergencia` | casilla de la tira, tono GRAVE con «parada ACTIVA» cuando es `true` | `null` ⇒ «no se sabe» en NEUTRO, **JAMÁS «no está puesta»**. Y `false` se pinta como `false`, que es un dato distinto de no saberlo |
| **Antigüedad de `/estado_robot`** | `msDesdeUltimo('/estado_robot')` | «hace 0,8 s» al lado de la casilla | «no se sabe» mientras no llegue el primero. 🔴 **No se le pone umbral**: su ritmo no está medido y los 3 s son de `/odom` |
| **Latido del nodo** | `/estado_robot.latido` | «el contador subió de 4412 a 4415» en mono, con el intervalo entre las dos lecturas | con **una** lectura: «una sola lectura: no prueba nada» — el topic va TRANSIENT_LOCAL y puede venir latcheado de un nodo muerto |
| **Antigüedad de `/odom` según el robot** | `/estado_robot.antiguedad_odom_s` | «el robot dice: hace 0,06 s». Va **junto** a la insignia de enlace, no dentro | `-1.0` y cualquier no finito ⇒ «no se sabe». **Distinto de 0,0 s** |
| **RVR responde** | `/estado_robot.rvr_responde` | casilla sí/no con su antigüedad. Separa «la Pi está viva» de «el RVR contesta» | sin el topic, «no se sabe». Y aunque llegue `true`, va con la antigüedad de `/odom`: el caso medido es latido avanzando + `rvr_responde` true + `/odom` a 0 Hz |
| **Resultado del envío de la parada** | hecho local: si `paradaEmergencia()` lanzó o no | PARADA_ENVIADA / PARADA_NO_ENVIADA en negrita + hora. El fallo, **con el mensaje de la excepción tal cual** | antes de pulsar **no hay resultado y no se pinta ninguna casilla**: no hay un «listo» que pueda confundirse con un «enviada» |
| **Tiempo desde el envío sin confirmación** | reloj propio (500 ms) desde el envío, contra la bandera | «enviada hace 4,5 s y la bandera sigue en false» en mono, corriendo. Pasa a ATENCIÓN a los 5 s | **los 5 s van escritos EN PANTALLA como ELECCIÓN, no como medida**: lo verificado es que el flanco ocurre, no cuánto tarda. Nadie lo ha cronometrado |
| **Voltaje** | `/battery_state.voltage` → `nivelBateria()` | «8,28 V» grande, el número manda y la unidad acompaña, con el veredicto pegado | `NaN` a propósito cuando la lectura falla ⇒ DESCONOCIDO, tono NEUTRO, «no se sabe». **Nunca OK por la puerta de atrás** |
| **Antigüedad del voltaje** | `msDesdeUltimo('/battery_state')` | «hace 12 s» pegado al voltaje, **siempre** — llega cada 30,0 s exactos | «no se sabe» + la nota de que puede tardar medio minuto **con el robot perfecto** |
| **Último `/scan`** | `msDesdeUltimo('/scan')`. 🔴 **El marco NO se suscribe**: es el 83 % del tráfico | «hace 4 s» + la advertencia de que la cuenta **solo avanza mientras alguna pestaña esté suscrita** | «no se sabe» mientras nadie haya mirado el LIDAR. Y al cerrar esa pestaña la cuenta queda **congelada y envejece para siempre**: se dice, en vez de dejar que se lea como «hace mucho que no barre» |
| **Motivo de bloqueo de la capa de seguridad** | `/collision_monitor_state` → `interpretarSeguridad()` | solo cuando bloquea por falta de barrido: una línea ámbar «enciende el barrido antes de mover el robot» | **sin mensaje NO es «todo bien»**: el monitor publica al CAMBIAR y solo cuando le llega `cmd_vel_raw`. DESCONOCIDO no pinta nada verde |
| **Estado de construcción de cada pestaña** | constante local: existencia real de la ruta | **«no construido»** en versalitas 11 px **dentro de la propia lengüeta** | no aplica. Y una pestaña así **sigue navegando**: su página explica qué falta y en qué orden |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso · abriendo el socket** | Insignia NEUTRO «no llego al robot» desde el primer instante, «socket cerrado», y debajo la cuenta «2,5 s de los 10» avanzando cada 500 ms. **La parada se ve entera y habilitada.** Los tres testigos, apagados | «Abriendo el WebSocket con ws://rvr-07.local:9090 · 2,5 s de los 10 del plazo. Un socket que no abre no da error nunca, ni onerror ni onclose: por eso esto es una cuenta y no algo que gire» |
| **No llego · el plazo venció** | La cuenta se sustituye por el aviso literal del transporte y por el texto de reintento. La cuenta vuelve a arrancar en cada intento | «no llego al robot — no se abrió el WebSocket en 10 s. Puede estar apagado, fuera de esta red, o con el servicio parado. Se reintenta solo, con espera creciente de 1 s a 30 s» |
| **Sin datos · el enlace va y el robot calla** | Insignia **ATENCIÓN (ámbar, nunca roja)**. Debajo, las tres causas **en lista, sin elegir**. Si llega `/estado_robot`, su latido y su antigüedad de `/odom` al lado | «el enlace va y el robot no manda telemetría — hace 8,4 s del último /odom. Esto no es una avería. La primera causa —el robot cargando— es el estado cotidiano del laboratorio» |
| **Parada enviada · el robot confirma** | Testigos 1 y 2 encendidos, **cada uno con su hora y su antigüedad, separados por un filete**: dos hechos, dos casillas, **ningún verde único**. Cronómetro apagado. La banda pasa a GRAVE y se queda así | «parada enviada · 12:04:31 · parada ACTIVA — el robot dice que su bandera está puesta, hace 0,4 s. No aceptará ninguna orden de movimiento hasta que se libere presencialmente» |
| **Parada enviada · la bandera sigue en false** | Testigo 1 encendido; testigo 2 en ATENCIÓN diciendo `false` con su antigüedad. **Cronómetro corriendo en mono**, que cruza a ámbar a los 5 s. **Ningún parpadeo: un número que sube** | «parada enviada hace 6,2 s y el robot sigue diciendo que su bandera no está puesta. Puede ser que aún no haya llegado, o que no la haya aplicado — mira el robot» |
| **Parada enviada · no llega `/estado_robot`** | Testigo 1 encendido. Testigo 2 **vacío y NEUTRO** con «no se sabe». **Cronómetro apagado: sin testigo no hay nada que cronometrar** | «parada enviada · 12:04:31. Esto es lo que sabe el navegador: que el mensaje salió por el WebSocket. No está llegando /estado_robot — mira el robot. El silencio no es un no» |
| **LA PARADA NO SE HA ENVIADO** | Banda entera en GRAVE con borde continuo, la frase **en mayúsculas con la hora**, y debajo el mensaje literal de la excepción. **Persiste al cambiar de pestaña** | «LA PARADA NO SE HA ENVIADO · 12:04:31 — sin conexión con el robot. Ve hasta el robot: la parada física y el interruptor del RVR no dependen de esta red» |
| **Pestaña no construida** | La lengüeta lleva «no construido» en versalitas, **con el mismo peso que las demás y sin desactivar**: se puede entrar | «Taller · no construido — no es "cargando" ni "próximamente": no existe. Lo que ves es la forma que tendrá» |

**Copia literal.**

```
rvr-07
ws://rvr-07.local:9090
socket abierto

PARADA DE EMERGENCIA

Abriendo el WebSocket · 2,5 s de los 10 del plazo. Un socket que no abre no da error
nunca: por eso esto es una cuenta y no algo que gire sin fin.

no llego al robot — no se abrió el WebSocket a ws://rvr-07.local:9090 en 10 s. Puede
estar apagado, fuera de esta red, o con el servicio parado. Se reintenta solo, con espera
creciente de 1 s a 30 s.

el enlace va y el robot no manda telemetría — hace 8,4 s del último /odom. Esto no es una
avería, y desde el navegador no se puede saber cuál de las tres causas es.

parada enviada · 12:04:31 — el mensaje salió por el WebSocket. Que saliera no prueba que
el robot la haya aplicado.

parada ACTIVA — el robot lo dice él: su bandera está puesta, hace 0,4 s. No aceptará
ninguna orden de movimiento hasta que se libere presencialmente.

parada enviada hace 6,2 s y el robot sigue diciendo que su bandera no está puesta. Puede
ser que aún no haya llegado, o que no la haya aplicado — mira el robot.

Los 5 s a partir de los cuales esto se marca son una elección de esta pantalla, no una
medida: lo verificado es que el flanco ocurre, no cuánto tarda.

LA PARADA NO SE HA ENVIADO · 12:04:31 — sin conexión con el robot. Ve hasta el robot: la
parada física no depende de esta red.

Para quitarla hay que ir hasta el robot: se libera con /release_emergency_stop en el
propio laboratorio, y esta interfaz no ofrece ese botón a propósito. Al liberarla con un
objetivo de Nav2 vivo el robot arrancó solo —34,7 cm medidos contra 0,0 con el arreglo—
porque el controlador nunca había dejado de publicar.

Último /scan: no se sabe. Esta cuenta solo avanza mientras alguna pestaña esté suscrita, y
esa suscripción cuesta el 83 % del tráfico del robot: la paga la pestaña del LIDAR
mientras la miras, y nadie más.
```

**Prohibido aquí.**

- **Un botón de liberar la parada**, ni con confirmación. Es un acto presencial.
- **Un solo verde** —o una sola insignia— que funda «salió por el WebSocket» con «el robot dice
  que su bandera está puesta». **Cuatro de los cinco fallos históricos devolvían éxito con cero
  efecto.**
- Pintar el silencio de `/estado_robot` como «la parada no está puesta», ni el de
  `/collision_monitor_state` como «seguridad OK».
- Que el marco monte **su propia** `Teleoperacion` mientras Conducir monta otra.
- Nada que gire, parpadee o lata sin final; ni spinner ni barra indeterminada mientras abre el
  socket.
- Reutilizar los 3 s de silencio de `/odom` para `/estado_robot` o `/battery_state`.
- Suscribir `/scan` desde el marco.
- Un porcentaje de batería, o cualquier cifra de latencia.

**🎨 Prompt para Stitch — Marco del robot**

```
Armazón persistente de la pantalla de un robot, en español, oscuro. Es la cabecera que
comparten seis pestañas.

Fondo: pozo #07080D con los dos orbes fijos. La cabecera va sobre un pozo elevado #0C0E16 y
está ANCLADA arriba.

De arriba abajo:

1. Renglón fino de identidad, alto 44 px. Izquierda: «rvr-07» en Geist 600 a 28 px, y JUSTO
   DEBAJO, en su propio renglón, «ws://rvr-07.local:9090» en Geist Mono 12 px en #8B90A3.
   Derecha: una insignia con punto de 5 px que dice «en línea», el texto «socket abierto» a
   12 px, y un enlace «ver los 16».

2. BANDA DE SEGURIDAD a ancho completo, con borde de 4 px en coral #FF5C39 y SIN sombra.
   Dentro, en este orden:
   a) un botón «PARADA DE EMERGENCIA» que ocupa el 100 % del ancho, alto 64 px, relleno coral
      a plena saturación, versalitas de 20 px, texto casi negro. No comparte fila con nada.
   b) una tira de TRES casillas separadas por filetes de 1 px, nunca fundidas: «salió por el
      WebSocket» (con hora 12:04:31), «el robot dice que su bandera está puesta» (con «hace
      0,4 s»), y «no se sabe» apagada. Cada una con su propio tono.
   c) un cronómetro en mono: «enviada hace 6,2 s y la bandera sigue en false».
   d) un párrafo fijo de 12 px explicando que la parada se libera presencialmente.

3. Tira de tres celdas de datos: voltaje «8,28 V» con «hace 12 s»; «último /scan: no se
   sabe» con su advertencia; y «el robot dice: hace 0,06 s» con el latido del nodo.

4. Barra de SEIS pestañas montada sobre el borde inferior de la banda: Taller · Conducir ·
   No obedece · Telemetría · LIDAR · Diagnóstico. La activa lleva el color del suelo y un
   filete de 2 px. «Taller» lleva además la marca «no construido» en versalitas de 11 px
   DENTRO de la propia lengüeta, sin estar desactivada.

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: ningún botón de liberar la parada, ninguna insignia verde única que resuma la
parada, ningún porcentaje de batería, ningún spinner ni barra indeterminada, ningún punto
que parpadee, y ninguna barra que se deslice entre pestañas.

Aplica además la sección §8 entera.
```

---

### 5.4 · Taller del alumno (el terminal) — `/robot/[id]` · 🔴 NO CONSTRUIDO

**Trabajo.** Escribir un guion, ejecutarlo **EN** el robot, verlo imprimir en vivo, contestarle
por teclado y pararlo. **Hoy NO CONSTRUIDO**: se dibuja el chasis y la cadena de bloqueo, y **ni
una línea de código o de salida inventada**.

**Quién la usa.** El alumno del taller presencial de 90 minutos. **Es el 90 % de su tiempo y el
0 % de lo que funciona.**

**Primera lectura.** La palabra **NO CONSTRUIDO**, dos veces y antes que nada: en la propia
pestaña y en la cabecera del panel. Debajo, una sola frase: *«Aquí todavía no se puede escribir ni
ejecutar código: esto es la forma que tendrá, sin nada detrás.»* Va primero porque **el criterio
de revisión de esta pantalla es una sola pregunta —¿alguien podría creer que esto ya
funciona?—** y porque es la pestaña por defecto de `/robot/[id]`.

Lo segundo, inmediatamente debajo y sin desplazar, es **la parada de emergencia**: es lo único de
esta pantalla que habla con el robot hoy. El alumno lanza sus guiones por SSH mientras el terminal
no exista, **y el robot se mueve de verdad mientras esta pantalla está abierta**.

**Composición.**

1. **CABECERA DEL PANEL.** `Terminal · rvr-07` a la izquierda; a la derecha, insignia NEUTRO con
   el texto **`no construido`**. Bajo el título, la frase. **Sin adornos, sin icono, sin
   «próximamente».**
2. **LA PARADA**, ancho completo y sin compartir fila. Encima del botón, cuando la bandera llega
   en `true`, la franja «parada ACTIVA» —**se ve sin haber pulsado nada**. Debajo, una línea
   propia de esta pantalla: **para el robot venga la orden de donde venga**, incluido un guion
   lanzado por SSH. Y: no hay botón de liberar.
3. **EL CHASIS**, dos columnas 60/40 que en móvil se apilan:
   - **Editor · tu código**: caja vacía con borde, alto mínimo fijo, microetiqueta arriba y un
     párrafo dentro explicando que no hay editor **y que tampoco hay uno de mentira**. Sin
     resaltado de sintaxis falso, sin números de línea, **sin cursor**.
   - **Salida del programa**: caja vacía igual. **Sin cursor parpadeante, sin prompt `$`, sin una
     sola línea de texto simulado.**
   - **Línea de entrada** a lo ancho: `<input>` **visible y `disabled`**, etiqueta encima,
     placeholder «el programa te pedirá que midas algo y pulses Enter», y el motivo debajo con
     **fichero y línea** de los cinco `input()` reales.
   - **Barra inferior**: `Ejecutar` y `Parar el programa`, los dos desactivados, y `PID —` con la
     nota de que el PID **es dato de la práctica 99, no decoración**. Al final: «Los tres
     necesitan el agente de sesión.»
4. **QUÉ FALTA, EN ORDEN** — la cadena de bloqueo como **lista numerada de tres eslabones**, cada
   uno con su estado en una insignia y su porqué en dos líneas:
   - **F0 · medir el punto de acceso del aula** → *sin medir* · si el AP aísla a sus clientes
     entre sí, el navegador no puede hablar con el robot y el transporte entero se replantea.
     Diez minutos en el aula, **y es el único experimento que puede tirar un diseño completo**.
   - **Agente de sesión en el robot** (`wss://rvr-NN.local:9443`) → *no escrito* · tu código corre
     **EN** el robot con `rclpy` nativo sobre `atriz.py`, no por rosbridge.
   - **Este terminal** → *chasis dibujado, sin conectar*.

   **Nada de barra de progreso ni de porcentaje: son tres casillas, no un avance medido.**
5. **LO QUE EL AGENTE TIENE QUE DAR** — tres requisitos escritos, **cada uno con la medida que lo
   obliga**. No es documentación interna: es lo que separa «no está hecho» de «no está hecho de
   cualquier manera».
   - **PTY, no tubería** · `05_sensor_color.py` imprime una fila cada 0,5 s, `11_sensor_avanzado.py`
     una cada diez tramos y el seguidor gira a 10 Hz. Contra una tubería, `print()` escribe a
     bloques: **pantalla congelada con el robot en marcha**.
   - **stdin bidireccional** · cuatro `input()` en `04_giro_preciso.py` (líneas 75, 103, 106, 109)
     y un quinto en `99_test_ctrl_c.py` (línea 64). **Sin él, dos prácticas de diez están
     muertas.**
   - **Señales y PID a la vista** · SIGINT repetido, SIGQUIT, SIGTERM y SIGHUP son el **objeto de
     estudio** de la 99, y su ejercicio 5 pide `kill -9 <pid>` desde otra terminal.
6. **HAZ LA CUENTA DEL ESPACIO — ANTES.** En cuanto se construye `Robot()`, la biblioteca
   **enciende el barrido del LIDAR** y a partir de ahí el robot ya obedece: la cuenta va **antes**
   de ejecutar. Tabla literal por práctica: 01 → 1,5 m delante y ~1 m detrás · 02 → 40 cm
   alrededor · 03 → cuadrado libre de ~1,5 m de lado · 04 → 40 cm + transportador · 05 → el robot
   no se mueve · 10 → 3 m en la dirección en que mire · 11 → 1 m + cinta negra cruzando, 40 cm
   detrás · seguidor → pista con ≥6 m · 90 → 1 m + 40 cm alrededor · 99 → 1,5 m. **Dos avisos al
   pie**: despejado **a 15,5 cm del suelo**, no a ras de suelo; y **hacia atrás no hay capa de
   seguridad**. Para un fichero del alumno, la fila **no lleva número**: lleva «no se puede saber,
   la cuenta sale de tu código».
7. **LOS FICHEROS Y SU ENUNCIADO**, dos columnas. Izquierda: la lista de `scripts/estudiantes/` en
   el orden del curso, con una nota fija: **esta lista es la del repositorio, no la del robot**.
   Derecha: el docstring del fichero elegido **tal cual**, en mono, **sin reescribir ni redondear
   cifras**; encima, en ámbar y siempre visible, la frase de que **ninguno se ha ejecutado nunca
   contra el robot moviéndose y tu medida gana**. Debajo, los EJERCICIOS literales. Y
   `atriz.py` con insignia **solo lectura**.
8. **FIN DE SESIÓN — NADA SE APAGA POR CERRAR LA PESTAÑA.** Tres filas: tu programa sigue vivo · el
   barrido sigue encendido (con botón **Parar barrido** → `/stop_scan`, y su nota de que responde
   vacío y el tambor no para del todo) · la parada, si la pusiste, sigue enganchada.
9. **AVISO DE AUTORIDAD**, tarjeta ámbar al final, **sin desplegable**: cuando esto funcione, **el
   guion del alumno tendrá más autoridad sobre el robot que esta web**.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Parada — bandera del robot** | `/estado_robot.parada_emergencia`, 1 Hz | palabra, **nunca solo color**: «parada ACTIVA» · «la bandera no está puesta» · «no se sabe», con la hora de llegada al lado | «no se sabe», gris, **distinto de un cero**. NUNCA «no está puesta». Y se añade «mira el robot» |
| **Señal de vida del nodo (latido)** | `/estado_robot.latido` | «el latido avanzó hace 1,1 s». **El número crudo no se enseña**: no significa nada para el alumno | «no se sabe si el nodo está vivo». Un driver anterior al 2026-08-04 no publica este topic, **y eso no es una avería** |
| **¿Responde la bola del RVR?** | `/estado_robot.rvr_responde` | «el RVR responde» / «no responde» + antigüedad. En el segundo caso, **las tres causas listadas sin elegir** | «no se sabe». **Nunca «robot averiado»**: el RVR apagado cargando con la Pi viva es lo cotidiano |
| **Antigüedad de la última muestra del RVR** | `/estado_robot.antiguedad_muestra_s` | segundos con un decimal, mono tabular | el `-1.0` se pinta «no se sabe», **jamás 0,0 s** |
| **Batería, en VOLTIOS** | `/battery_state.voltage`, cada 30,0 s | cifra grande en mono, «V» pequeña, y segunda línea «hace N s · umbrales del firmware 7,0 y 6,5 V» | `NaN` → «no se sabe». **No se cae en «OK» por la puerta de atrás** |
| **Atasco mientras tu guion mueve el robot** | `/motor_status`, sondeo 30 s + notificación del firmware | «oruga izquierda atascada» / «sin atasco notificado» + antigüedad propia. **Es lo que explica que el robot se pare solo contra una pata de mesa** | `antiguedad_atasco_s = -1.0` → «no se sabe si hay atasco», **que no es «no hay atasco»** |
| **¿Queda el barrido encendido?** | `/scan`, solo mientras alguien esté suscrito | «llegó un barrido hace N s» si hay suscripción; si no, «nadie está mirando /scan desde esta pantalla» | «desde el navegador no se sabe», y al lado cómo se comprueba de verdad: `atriz-escaneo estado` **en el robot** |
| **Enlace y a qué máquina va** | el propio WebSocket. **Hecho del navegador, NO un topic**, y se dice así | insignia + la URL en mono, **siempre visible**: distingue «me equivoqué de robot» de «este robot no responde» | un socket que no abre **no da ni error ni cierre**: a los 10 s se declara «no llego» |
| **Fichero de práctica y su enunciado** | 🔴 **el repositorio de este proyecto, NO el robot** — y la pantalla lo dice en una línea fija | nombre + docstring **literal** en mono, con sus avisos y sus EJERCICIOS tal cual, **sin redondear ninguna cifra** | sin agente **no se puede listar lo que hay EN el robot**; se dice «esta lista es la del repositorio» y **no se finge un inventario** |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **NO CONSTRUIDO** — el estado **permanente** de esta pantalla hoy, no un vacío temporal | pestaña «Terminal — no construido», insignia en la cabecera, editor y salida **vacíos con su nombre y su motivo**, entrada y botones dibujados y desactivados, y la cadena de bloqueo en tres pasos. **Ni una línea de código ni de salida, ni gris ni «de muestra»** | «Aquí todavía no se puede escribir ni ejecutar código. Esto es la forma que tendrá, sin nada detrás. Lo que falta está abajo, en orden» |
| **No llego al robot** | insignia gris, la URL a la vista, todos los campos del robot en «no se sabe»; **la parada sigue pulsable** y, si el publicar lanza, «LA PARADA NO SE HA ENVIADO» | «No llego a ws://rvr-07.local:9090. Puede ser el nombre, la red o el robot: desde aquí no se distingue» |
| **El enlace va y el robot no manda telemetría** | insignia ámbar, campos en «no se sabe», y **las tres causas listadas juntas sin resaltar ninguna** | «El enlace va y el robot no manda telemetría. No es una avería, y desde aquí no se sabe cuál de las tres es» |
| **Enlace abierto y `/estado_robot` llegando** | latido, bandera, `rvr_responde` y antigüedad con su hora; batería con la suya; atasco con la suya | Cada cifra con su antigüedad y nada más. **La pantalla no dice que el robot esté listo para tu guion**: dice qué llegó y cuándo |
| **`/estado_robot` no llega y el resto sí** | los cuatro campos de ese topic en «no se sabe», **claramente distintos de un cero**; voltaje y motores normales | «Este robot no publica /estado_robot. No es una avería: es un driver anterior al 2026-08-04. De la parada, desde aquí, no se sabe nada — mira el robot» |
| **Parada ACTIVA** | franja sobre el botón, **visible al entrar aunque la parada la pusiera otra pestaña o la sesión anterior** | «parada ACTIVA — el robot no aceptará ninguna orden de movimiento, tampoco de tu guion, hasta que se libere presencialmente» |
| **Parada enviada y la bandera sigue en false** | el aviso con su hora, y debajo **la discrepancia dicha en voz alta** | «El mensaje salió, pero el robot sigue diciendo que su bandera no está puesta — mira el robot» |
| **Fin de sesión: nadie mira `/scan`** | el campo del barrido en «no se sabe», el botón «Parar barrido» al lado y su nota bajo el botón | «Desde aquí no se sabe si el barrido sigue encendido: nadie está suscrito a /scan, que es el 83 % del tráfico de un robot» |

**Copia literal.**

```
Terminal · rvr-07 — no construido. Aquí todavía no se puede escribir ni ejecutar código:
esto es la forma que tendrá, sin nada detrás.

Editor · tu código. Aquí irán tus treinta líneas. No hay editor, y tampoco hay un editor
de mentira: una caja donde se puede escribir y que no ejecuta nada es peor que una caja
vacía.

Salida del programa. Aquí saldrá lo que imprima tu programa mientras corre. No hay nada
que enseñar porque no hay ningún programa ejecutándose: esta caja está vacía a propósito,
no con un ejemplo.

Entrada del programa · desactivada. Sin esta línea, dos prácticas de diez están muertas:
04_giro_preciso.py te para cuatro veces a pedirte que midas con el transportador (líneas
75, 103, 106 y 109) y 99_test_ctrl_c.py una quinta (línea 64). Está dibujada porque es un
requisito, no un adorno.

Tiene que ser una terminal de verdad (PTY), no una tubería. 05_sensor_color.py imprime una
fila cada 0,5 s, 11_sensor_avanzado.py una cada diez tramos y el seguidor de línea gira a
10 Hz: contra una tubería, print() escribe a bloques y verías una pantalla congelada con
el robot en marcha.

El PID tiene que verse, y las señales llegar enteras. Ctrl-C repetido, Ctrl-\, kill y
cerrar la terminal son el objeto de estudio de la práctica 99, y su ejercicio 5 te pide
kill -9 <pid> desde otra terminal. Un botón «Parar» que solo mande SIGINT deja esa
práctica sin hacer.

Haz la cuenta del espacio ANTES de ejecutar. En cuanto se construye Robot(), la biblioteca
enciende el barrido del LIDAR y el robot ya obedece: la cuenta va antes, no después. Y
despejado a 15,5 cm del suelo, que es la altura a la que barre el LIDAR — «despejado a ras
de suelo» no basta. Hacia atrás no hay capa de seguridad: su polígono mira hacia delante.

Para un fichero tuyo no se puede saber: la cuenta sale de tu código. Suma los avanzar()
que encadenes (metros = velocidad × segundos), cuenta que girar() necesita sitio a los
lados, y si mandas velocidades negativas cuenta también el espacio de detrás.

Esta lista es la del repositorio, no la del robot: nadie le ha preguntado a rvr-07 qué
ficheros tiene. Cuando exista el agente de sesión se leerá del robot, y esta frase
desaparecerá.

Ninguno de estos guiones se ha ejecutado nunca contra el robot moviéndose. Lo que dicen
las guías es aritmética de velocidad × tiempo leída del código, no un robot que alguien
haya visto hacerlo. Si tu medida no coincide, tu medida gana: anótala y díselo al profesor.

atriz.py se lee, no se toca. Se abrirá en solo lectura: sus protecciones son fallos que
este laboratorio ya pagó, y romperla se la rompe también al siguiente que use el robot.

Cerrar esta pestaña no apaga nada. Tu programa sigue vivo en el robot, el barrido del
LIDAR sigue encendido y la parada, si la pusiste, sigue enganchada.

Parar barrido llama a /stop_scan, que sí está en la lista blanca. Este servicio responde
vacío: no llega ni un bit que diga qué pasó en el robot. Y el tambor no se detiene del
todo — baja de 11,8 Hz a 2,7. Para comprobarlo de verdad: atriz-escaneo estado, en el
robot.

Cuando esto funcione, tu programa podrá más que esta web. Corre con rclpy nativo dentro
del grafo del robot, así que alcanza raw_motors, move_timed, move_to_pose y los modos de
infrarrojos: los caminos que se saltan la capa de seguridad y que el navegador tiene
cerrados con una lista blanca. Mientras haya una sesión en marcha, esa lista no cubre tu
código. La parada sí, porque el driver descarta el mando venga de donde venga.
```

**Prohibido aquí.**

- **Ni una línea de código en el editor ni una línea de salida en la consola**: ni gris, ni «de
  muestra», ni un cursor parpadeando que sugiera un proceso vivo detrás.
- «Próximamente», «en construcción», «beta», una cuenta atrás, **o una barra de progreso de la
  cadena de bloqueo**: nadie está midiendo ese progreso, y F0 depende de entrar en un aula.
- **Un editor escribible que no ejecuta nada**, o un botón Ejecutar habilitado que no haga nada.
- Listar ficheros «del robot» sin haberlos leído del robot, o enseñar un `ls` simulado.
- **Reescribir, resumir o redondear las cifras de los enunciados.**
- Decir «la parada no está puesta» cuando `/estado_robot` no llega.
- **Ningún cursor de terminal animado** — es la misma mentira con otro disfraz.
- Un botón de liberar la parada, y cualquier cifra de latencia.

**🎨 Prompt para Stitch — Taller (NO CONSTRUIDO)**

```
Pantalla de un terminal de programación para alumnos que TODAVÍA NO EXISTE, en español,
oscura. El objetivo es que NADIE pueda creer que ya funciona.

Fondo: pozo #07080D con los dos orbes fijos. Arriba, la cabecera del marco del robot con la
banda de parada de emergencia (ver el prompt del Marco).

Contenido:
1. Cabecera del panel: «Terminal · rvr-07» a la izquierda, y a la derecha una insignia
   neutra (#8B90A3) con el texto «no construido». Debajo, una frase de una línea.
2. Dos columnas 60/40 con dos cajas de vidrio VACÍAS, cada una con su microetiqueta en
   versalitas de 10 px y un párrafo explicativo dentro, centrado y en #8B90A3:
   «Editor · tu código» y «Salida del programa». SIN números de línea, SIN resaltado de
   sintaxis, SIN prompt «$», SIN cursor, SIN una sola línea de texto simulado.
3. A lo ancho, un campo de texto VISIBLE Y DESACTIVADO con etiqueta encima, placeholder y un
   motivo escrito debajo en 11,5 px.
4. Barra inferior con dos botones desactivados («Ejecutar», «Parar el programa»), el texto
   «PID —», y una nota al final.
5. Una lista NUMERADA de tres eslabones («Qué falta, en orden»), cada uno con una insignia de
   estado y dos líneas de porqué. NADA de barra de progreso ni de porcentaje.
6. Tres tarjetas de vidrio con requisitos técnicos, cada una con la medida que la obliga.
7. Una tabla densa de espacio necesario por práctica, con dos avisos al pie.
8. Dos columnas: lista de ficheros a la izquierda, y a la derecha un bloque de texto
   monoespaciado con un enunciado literal, precedido de un aviso ámbar.
9. Tres filas de «fin de sesión» y, al final, una tarjeta ámbar de «aviso de autoridad».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: código de ejemplo, salida de consola de ejemplo, cursores parpadeantes, barras
de progreso, la palabra «próximamente», ni un editor que parezca escribible.

Aplica además la sección §8 entera.
```

---

### 5.5 · Por qué no obedece — `/robot/[id]/no-obedece` · ruta nueva

**Trabajo.** Separar **los comportamientos normales** de **una avería de verdad**, listar las
causas **SIN elegir** cuando no se pueden separar, y dar **el comando exacto de desempate** para
las que el navegador no puede cerrar.

**Quién la usa.** Los tres: es la interrupción número uno del profesor, la primera hora del
alumno, y el trabajo entero de quien monta.

**Primera lectura.** **UNA SOLA FRASE**, a 28-32 px, en la tarjeta de arriba: **qué está
bloqueando el movimiento AHORA** — y **solo si un dato del robot lo afirma**. Debajo, a 11,5 px y
tenue, **de qué campo sale y su antigüedad** («/estado_robot.parada_emergencia · hace 0,9 s»),
para que la frase **no aparezca nunca sin su procedencia**.

Solo **dos causas** pueden llegar aquí hoy, y las dos tienen topic detrás: la **parada** y el
**bloqueo por falta de barrido** (`polygon_name === "invalid source"`). Si ningún dato afirma
nada, esa misma línea dice **«No se sabe por qué. Estas son las causas que quedan»** — un
veredicto **tan legítimo como los otros**, en neutro, **nunca en verde ni en rojo**. Y si hay
**dos causas confirmadas a la vez**, se nombran **las dos unidas por «y»**: la pantalla no elige.

**Composición.** Hereda del marco el identificador, la URL y la insignia de enlace: **no los
repite**.

**1 · EL VEREDICTO** — tarjeta a todo el ancho, **la única con filo superior encendido**.
- línea 1, 28-32 px: la frase.
- línea 2, 11,5 px tenue: campo de origen + antigüedad.
- línea 3, **el recuento honesto en cuatro cifras**: «1 confirmada · 2 descartadas · 3 no se sabe
  · 3 que el navegador no puede ver». **Nunca un «todo bien».**

**2 · TRES SUJETOS, TRES SITIOS** — tres columnas iguales, **en fila**, con separador de 1 px.
**Nunca apiladas dentro de un mismo bloque: la separación ES el contenido**, porque este proyecto
los confunde siempre.

| Sujeto | Quién lo sabe | Dónde se arregla |
|---|---|---|
| **ENLACE** | el navegador, siempre | en tu red y en esta pestaña |
| **NODO de la Pi** | el latido **avanzando** | por SSH en la Raspberry Pi |
| **RVR** | `rvr_responde` + `antiguedad_odom_s` | en la bola: encenderla, cargarla, el cable |

Cada columna: microetiqueta en versalitas · dato principal en mono · antigüedad debajo · **una
sola línea de «dónde se arregla»**. La columna cuyo sujeto explica el veredicto lleva el filo
encendido; las otras dos, no.

**3 · EL LATIDO, COMPARADO** — banda a lo ancho bajo la columna NODO. Tres celdas en mono:
«lectura anterior» → «lectura actual» → «Δ», y bajo ellas «medidas con 1,0 s de diferencia».
**Tres estados y ni uno más**: AVANZA · NO AVANZA · SOLO HAY UNA LECTURA. **Jamás un booleano
«vivo».** Nota fija con el porqué (TRANSIENT_LOCAL).

**4 · EL TERCER ESTADO MUDO** — tarjeta propia con **las dos medidas ENFRENTADAS**, las dos a
38 px en mono con su antigüedad: `antiguedad_muestra_s` | `antiguedad_odom_s`. Entre ellas, **el
discriminante en cuatro filas**, con la que aplica marcada:

```
las dos ~0                  ->  el RVR habla y /odom se completa
muestra ~0 · odom CRECE     ->  llegan 4 de los 5 componentes de /odom
las dos crecen              ->  el RVR calló
−1,0 en cualquiera          ->  «no se sabe», que no es cero
```

Y **una quinta fila**, que es la que separa el robot del enlace: junto a `antiguedad_odom_s` (lo
que dice el robot) va `msDesdeUltimo('/odom')` (lo que ve esta pestaña). **Si el robot dice
0,06 s y el navegador 4,2 s, lo que se ha perdido es el camino, no la odometría.**

**5 · `reanudaciones_fallidas`** — el número a 38 px y, debajo, una escala de tres tramos con el
actual marcado: `0` · `1-2` · `más de 2`. Microetiqueta encima, literal: **«LECTURA RAZONADA, SIN
CALIBRAR»**.

**6 · LAS CAUSAS, UNA POR UNA** — ordenadas **por lo que la pantalla PUEDE DECIR de cada una**, no
por probabilidad. Cada fila: nombre · insignia · campo de origen con su antigüedad · qué hacer.
**Cuatro insignias y ninguna más:**

- **CONFIRMADA** — un dato lo afirma
- **DESCARTADA** — un dato lo niega, con antigüedad
- **NO SE SABE** — el campo no llegó, o vale −1. **Neutro, nunca verde**
- **EL NAVEGADOR NO LA VE** — lleva su comando al lado

Las nueve filas, en este orden: parada de emergencia · barrido apagado · atasco de motor · batería
por voltaje · odometría muerta · polígono estático frenando · descriptor USB muerto del LIDAR · el
nodo caído o la Pi callada · otra pestaña con un QoS incompatible. **Las cuatro últimas nunca
pueden pasar de NO SE SABE o EL NAVEGADOR NO LA VE, y eso se ve en la propia fila.**

**7 · LO QUE NO ES AVERÍA Y LO PARECE** — cuatro comportamientos medidos, **SIN insignia de estado
porque no son estados**: el polígono estático, el barrido apagado por defecto, el vigilante de
0,3 s del driver, y la pestaña en segundo plano.

**8 · COMANDOS DE DESEMPATE** — la única tarjeta con fondo distinto. Cada comando en `<samp>`,
ancho completo, seleccionable, con botón de copiar y **una línea que dice qué desempata** (no qué
hace).

**9 · LO QUE ESTA PANTALLA NO PUEDE CERRAR** — lista final, sin adornos, **permanente**.

Rejilla: una columna hasta `lg`; de `lg` en adelante, los bloques 4-5 en una columna y el 6 en la
otra, con `items-start`.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Enlace** | `Transporte.conectado` + la URL. **No es un topic** | «abierto» / «no llego al robot», con la URL en mono debajo | no aplica: siempre hay respuesta. **«no llego» no es una avería** |
| **Latido, lectura actual** | `/estado_robot.latido` | entero en mono, sin unidad | «aún no ha llegado ningún /estado_robot». **Se distingue de un 0**, que sería un contador real |
| **Latido, lectura anterior y Δ** | dos lecturas guardadas por la pantalla, con marca de tiempo del navegador | anterior → actual → Δ, tres celdas en mono; debajo «medidas con 1,0 s de diferencia» | «solo hay una lectura todavía»: **no se afirma que avance ni que no avance**. Nunca un booleano «vivo» |
| **Antigüedad de `/estado_robot`** | `msDesdeUltimo('/estado_robot')` | «hace 0,9 s» | «no se sabe». Puede ser un **driver anterior al 2026-08-04**. **No es un veredicto sobre el robot** |
| **Parada de emergencia** | `/estado_robot.parada_emergencia` | «parada ACTIVA» o «la parada no está puesta», con su antigüedad | «no se sabe». **JAMÁS «no está puesta»**: este botón ha fallado cinco veces devolviendo éxito |
| **El RVR contesta** | `/estado_robot.rvr_responde` | «contesta» / «no contesta», con antigüedad | «no se sabe». Y «no contesta» **tampoco es avería**: cargando con la Pi viva es lo cotidiano |
| **`antiguedad_muestra_s`** | `/estado_robot.antiguedad_muestra_s` | segundos con 1 decimal, mono, 38 px | `−1,0` ⇒ «no se sabe», **nunca 0,0** |
| **`antiguedad_odom_s`** | `/estado_robot.antiguedad_odom_s` | segundos con 1 decimal, mono, 38 px, **enfrentado al anterior** | `−1,0` ⇒ «no se sabe». **Es el campo que cubre el tercer estado**: ni el vigilante de silencio ni `rvr_responde` lo ven |
| **Antigüedad del último `/odom` vista aquí** | `msDesdeUltimo('/odom')` | «hace 61 ms», **al lado** del campo del robot para poder contrastarlos | «no se sabe». **Contrastado con el campo del robot es lo único que atribuye la pérdida al camino** |
| **`reanudaciones_fallidas`** | `/estado_robot.reanudaciones_fallidas` | entero a 38 px con la escala debajo y el tramo actual marcado; microetiqueta «LECTURA RAZONADA, SIN CALIBRAR» | «no se sabe». Y con dato se dice **«no se está recuperando»**, nunca «el RVR está apagado» |
| **Acción de la capa de seguridad** | `/collision_monitor_state.action_type` → `interpretarSeguridad()` | sin restricción · bloquea · ralentiza · **no reconocido (con su número entre paréntesis)** | «no se sabe»: el monitor publica **AL CAMBIAR** y solo procesa cuando le llega `/cmd_vel_raw`. **Con el robot quieto no llega nada (0 mensajes en 12 s), y ese silencio NO es «todo bien»** |
| **Motivo o polígono** | `/collision_monitor_state.polygon_name` | el literal **entre comillas y en mono**; «invalid source» se traduce debajo a «no le llega el barrido del LIDAR» | «no se sabe». **A veces trae un motivo y no un polígono**, y no se le inventa significado a ninguno |
| **Antigüedad del último `/collision_monitor_state`** | `msDesdeUltimo(...)` | «hace 12 s», pegado al campo anterior | «no ha llegado ninguno». **Sin él, un «bloquea» de hace media hora se leería como de ahora** |
| **Atasco de motor** | `/motor_status.atascado_*` + `antiguedad_atasco_s` | «motor izquierdo atascado», **nombrando la oruga**, con su antigüedad | `−1,0` ⇒ «no se sabe», **que NO es «no hay atasco»**. Se propaga como `null`, no se colapsa a `false` |
| **Batería, por voltaje** | `/battery_state.voltage` + `nivelBateria()` | «8,29 V» a 38 px, y debajo **el umbral contra el que se compara**: 7,0 baja · 6,5 crítica | «no se sabe»: el driver publica NaN cuando la lectura falla. **Nunca 0,00 V**, y **nunca el porcentaje** |
| **Temperatura de los motores** | `/motor_status.temperatura_*` + `antiguedad_termico_s` | °C con su antigüedad; por encima de 35 s se marca **«el mismo dato repetido»** | «no se sabe». **Solo corrobora** un atasco: es un proxy lento y **no decide nada por sí solo** |
| **Coste de esta pantalla** | `caudalDeFlota(TOPICS, 1)` | kB/s en mono, con la lista de topics debajo | 🔴 **la función LANZA hoy**: ni `/estado_robot` ni `/collision_monitor_state` están en la tabla de caudales. El segundo **sí está medido** (0,012 kB/s) y se puede añadir; el primero **no**. Hasta que se mida, **se suma lo medido y se nombra lo que falta**, en vez de imprimir un total redondo |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso** | las tres columnas con «no se sabe» en cada dato; el veredicto en neutro; ninguna causa marcada; **ninguna barra, ningún esqueleto, ningún punto que se mueva** | «Esperando el primer mensaje del robot. Todavía no se sabe nada, y eso no es un veredicto» |
| **No llego al robot** | la columna ENLACE en neutro; NODO y RVR **atenuadas, con hueco declarado y no con ceros**; las nueve causas en «no se sabe» | «No hay WebSocket abierto con este robot, así que de la Raspberry Pi y del RVR no se sabe nada. Un socket que no abre no da ningún error: por eso el aviso tarda hasta 10 s» |
| **El enlace va y `/estado_robot` no llega** | ENLACE «abierto»; NODO y RVR en «no se sabe»; nota fija bajo el veredicto; parada, latido y tercer estado marcados **EL NAVEGADOR NO LA VE** | «Ese topic existe en el robot desde el 2026-08-04: si el driver es anterior, esta pantalla se queda sin la mitad de lo que sabe decir. **No es un veredicto sobre el robot**» |
| **Solo hay una lectura del latido** | las tres celdas con la actual rellena, «anterior» vacía y Δ sin valor; la columna NODO en neutro | «Solo hay una lectura del contador. Una sola no dice nada: el topic va TRANSIENT_LOCAL y puede venir latcheado de un nodo ya muerto. La siguiente llega en un segundo» |
| **Todo llega y ninguna causa se confirma** | veredicto neutro con el recuento de cuatro cifras; **la lista de causas entera visible**; la tarjeta de comandos destacada | «No se sabe por qué. Ninguna de las causas que esta pantalla puede ver está confirmada, y quedan tres que el navegador no ve. Los comandos de abajo las desempatan» |
| **Una causa confirmada** | el veredicto con su frase y el filo encendido; su fila la primera de la lista; **la columna del sujeto responsable, encendida** | «La parada de emergencia está puesta. El robot no acepta órdenes de movimiento hasta que alguien la libere con el robot delante» |
| **Dos o más causas a la vez** | las dos frases unidas por «y», las dos filas arriba, **ninguna destacada sobre la otra** | «Hay dos causas confirmadas a la vez. Esta pantalla no elige entre ellas: las dos hay que resolverlas» |
| **No construido** | dos filas permanentes al final, en neutro, con la etiqueta «no construido» y qué las bloquea | «Que el LIDAR se recupere solo del descriptor muerto está sin hacer en el robot… Y no hay autenticación: cualquiera en el aula puede conducir cualquier robot» |

**Copia literal.**

```
Por qué no obedece

Tres sujetos distintos, y cada uno se arregla en un sitio: el enlace en tu red, el nodo en
la Raspberry Pi, el RVR en la bola. Confundirlos es el error favorito de este laboratorio.

No se sabe por qué. Estas son las causas que quedan, sin elegir entre ellas.

El contador anterior contra el actual. Si no se mueve, el nodo no está corriendo, por
mucho que el topic exista y por mucho que acabe de llegar un mensaje: /estado_robot va
TRANSIENT_LOCAL y puede venir latcheado de un nodo que ya está muerto. Lo único que prueba
que hay alguien detrás es que el número avance.

La muestra del RVR llega y /odom no se completa: faltan componentes de los cinco con los
que el driver lo arma. Ni el vigilante de silencio ni rvr_responde lo ven, así que sin
este par de números el muro del profesor pinta este robot en verde con la odometría muerta.

El robot dice que su /odom es fresco y a esta pestaña no le llega. Entonces lo que pierde
mensajes es el camino —rosbridge, el WiFi del aula, el bucle de eventos del navegador—, no
la odometría del robot.

Tres reanudaciones seguidas sin que volviera ni un dato: el robot no se está recuperando.
Los tramos 0 · 1-2 · más de 2 son una lectura razonada de una medida, no un umbral
calibrado: nadie ha cronometrado cuánto tarda una siesta real en recuperarse. Con este
número no se puede afirmar que el RVR esté apagado.

parada ACTIVA — el robot no acepta órdenes de movimiento hasta que alguien la libere con
el robot delante. Es la única causa de esta lista que la pantalla puede afirmar, porque el
robot publica su bandera y el flanco se presenció desde los dos lados con el robot en
marcha.

No llega /estado_robot, así que no se sabe si la parada está puesta. Esta pantalla no va a
decir que no lo está: el silencio no es un no.

La capa de seguridad bloquea el movimiento porque no le llega el barrido del LIDAR. El
robot está bien: sin /scan no puede saber si hay algo delante y no deja conducir. Se
enciende en «Conducir», y aquí se lee de polygon_name por 0,012 kB/s, sin pagar el 83 %
del tráfico que cuesta suscribirse a /scan.

Retroceder junto a una pared tarda más de lo esperado. El polígono de precaución es
estático y se extiende 0,36 m hacia delante: mientras la pared siga dentro, frena al 40 %
aunque el robot se esté alejando. Medido con cinta: 2 s a 0,15 m/s recorrieron 14 cm en
vez de 30. No es que no obedezca.

Si alguien apagó y encendió el RVR con la Raspberry Pi viva, el LIDAR puede haberse
quedado agarrado a un descriptor que el kernel ya destruyó. Desde el navegador esto no se
ve: el nodo vive, sus servicios contestan y /odom va a 16,5 Hz mientras /scan está a cero.

Estos comandos desempatan lo que el navegador no puede. Se ejecutan en la Raspberry Pi de
este robot, por SSH.

  ls -l /proc/$(pgrep -f "[y]dlidar_ros2_dr")/fd | grep tty
  ↳ si pone «(deleted)», el LIDAR tiene el descriptor muerto

  sudo systemctl restart atriz-robot
  ↳ lo arregla. Verificado por efecto: /scan volvió a 11,90 Hz

  ps -eo comm | grep -qx rvr_driver_node
  ↳ si el driver corre. «ros2 topic list» no sirve: conserva topics de nodos muertos

  journalctl --since "-25 s"
  ↳ el log del último cuarto de minuto. Nunca con date -u: en este robot la ventana caería
    cinco horas en el futuro y contaría cero

Con varias pestañas abiertas sobre este robot, un topic a 0 Hz también es compatible con
que otra pestaña pidiera un QoS incompatible: en rosbridge el primer cliente que se
suscribe a un topic impone su QoS a todos los demás. Es una hipótesis, y esta pantalla no
la va a dar por hecha — no existe ningún dato que la confirme, porque rosbridge no manda
status por el socket.
```

**Prohibido aquí.**

- **Nunca «el robot está roto» ni un rojo por falta de datos.** De las nueve causas, **cinco son
  estados NORMALES** del laboratorio.
- Nunca «no está puesta» sobre la parada sin `/estado_robot` en la mano. **Esa asimetría es
  deliberada.**
- **Nunca elegir entre causas que no se pueden separar.**
- Nunca leer el silencio de `/collision_monitor_state` como «la seguridad no está limitando nada».
- **Nunca un booleano «nodo vivo» a partir de un solo mensaje.**
- Nunca traducir `reanudaciones_fallidas > 2` a «el RVR está apagado».
- **Nunca suscribirse a `/scan` desde esta pantalla.**
- Nada parpadea, nada late, nada gira, ningún contador sube solo, ninguna barra indeterminada:
  **aquí esperar un dato es el estado normal**.

**🎨 Prompt para Stitch — Por qué no obedece**

```
Pantalla de diagnóstico «Por qué no obedece» de un robot, en español, oscura y densa.

Fondo: pozo #07080D con los dos orbes fijos. Arriba, la cabecera del marco del robot con su
banda de parada.

De arriba abajo, una columna hasta lg y dos columnas después:

1. VEREDICTO: tarjeta de vidrio a todo el ancho, la ÚNICA con un filo superior encendido de
   1 px en degradado. Línea 1 a 30 px: una sola frase. Línea 2 a 11,5 px tenue: el campo de
   origen y su antigüedad, en mono. Línea 3: un recuento de cuatro cifras.
2. TRES COLUMNAS IGUALES separadas por filetes de 1 px, tituladas ENLACE, NODO DE LA PI y
   RVR en versalitas de 10 px. Cada una: dato principal en mono, antigüedad debajo, y una
   línea de «dónde se arregla». Solo una lleva el filo encendido.
3. Banda a lo ancho con tres celdas en mono: «lectura anterior» → «lectura actual» → «Δ», y
   debajo «medidas con 1,0 s de diferencia».
4. Tarjeta con DOS NÚMEROS ENFRENTADOS a 38 px en mono, y entre ellos una tabla de cuatro
   filas con una marcada.
5. Tarjeta con un número a 38 px y una escala de tres tramos debajo, con la microetiqueta
   «LECTURA RAZONADA, SIN CALIBRAR».
6. Lista de NUEVE causas, una por fila: nombre, insignia, campo de origen con antigüedad y
   qué hacer. Solo cuatro tipos de insignia: CONFIRMADA, DESCARTADA, NO SE SABE (neutra) y
   EL NAVEGADOR NO LA VE. Ninguna verde.
7. Cuatro viñetas de «lo que no es avería y lo parece», SIN insignia.
8. Tarjeta con fondo distinto: cuatro comandos en <samp> monoespaciado, a ancho completo,
   seleccionables, con botón de copiar y una línea de «qué desempata» bajo cada uno.
9. Lista final «Lo que esta pantalla no puede cerrar».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: ningún indicador verde de «todo bien», ningún rojo nacido de falta de datos,
ningún medidor circular, ninguna barra de progreso, ningún punto que parpadee.

Aplica además la sección §8 entera.
```

---

### 5.6 · Conducir — `/robot/[id]/conducir`

**Trabajo.** Mover el robot **con el dedo puesto**, pararlo antes de que llegue al borde de la
mesa, y **explicar los comportamientos medidos que parecen fallos y no lo son**.

**Quién la usa.** El alumno cuando teleopera; quien monta, para comprobar que `/odom` se mueve.

**Primera lectura.** El **botón de parada a ancho completo** y, pegado debajo sin separación, un
**renglón de tres insignias**: **enlace · barrido · capa de seguridad**. Los dos están fijos al
desplazar; nada más comparte esa franja.

Quien abre esta pantalla tiene el robot a un metro y trae **dos preguntas**: «cómo lo paro» y «por
qué no se mueve». La primera se contesta con **el único control que no puede fallar en silencio**.
La segunda, con **tres insignias que no pueden decir «bien» por ausencia de dato**: la causa más
frecuente de «el robot no obedece» está medida y es **el barrido del LIDAR apagado**, que además
es el estado de reposo normal de los 16 robots.

La posición, el rumbo y las velocidades van **después**, en la columna derecha: se leen cuando el
robot ya se ha movido, **de pie y con la cinta métrica en la mano**.

**Composición.**

**1 · Barra de parada** — pegajosa, ancho completo, fuera de la rejilla. Encima del botón, y solo
cuando la bandera es `true`, la franja «parada ACTIVA»; **se ve sin haber pulsado nada**. Debajo,
el resultado del último pulsado con su hora y **las tres redacciones** según lo que diga el robot.
**Una sola instancia de teleoperación por pantalla**, o serían dos bucles de 10 Hz publicando
twists distintos contra el mismo robot.

**2 · Renglón de estado del mando** — misma franja pegajosa, **altura fija** para que no salte la
página cuando una insignia cambia. **Ninguna de las tres puede quedarse en verde por falta de
dato.**

**3 · Comprobación presencial** — ancho completo, solo hasta que se confirma. Cinco puntos y un
botón «Lo he mirado — activar el mando». Mientras no se confirme, **las cinco celdas del mando
están desactivadas con el motivo escrito al lado**, no mudas. Al confirmar, se pliega a una línea
con la hora. **Esa línea nunca dice «espacio comprobado»: dice «confirmaste a las 10:32:07 que lo
habías mirado»**, porque marcar una casilla no comprueba nada.

**4 · Avisos** — apilados, aparecen una vez y **ninguno se autocierra**.

**5 · Rejilla de dos columnas a partir de `lg`**, con `items-start`. A la izquierda **lo que se
toca**; a la derecha **lo que se lee**.

- *Izquierda*: **Enlace** · **Barrido del LIDAR** (dos botones y el estado de arranque con su
  hora; el botón dice «Esperando un /scan real…» mientras corre, **no «cargando»**) · **Mando**
  (rejilla 3×3 con **cinco celdas**: adelante, izquierda, parar, derecha, atrás; **las cuatro
  esquinas NO EXISTEN**: hueco vacío, sin borde y sin botón desactivado, porque un botón apagado
  promete una función que no está; celdas de **64 px** de alto mínimo, `select-none touch-none`,
  `setPointerCapture` en `pointerdown`, y `pointerup` + `pointercancel` + `lostpointercapture` los
  tres atados a parar; **las cuatro direcciones se mantienen pulsadas, la del centro es un clic**
  y se dibuja distinta) · **Poner la odometría a cero** (un botón, la hora del último reset, y
  **sin campos para escribir coordenadas**).
- *Derecha*: **La capa de seguridad** (siempre visible, **incluido el estado desconocido**; el
  texto sale entero de la función que lo traduce y **no se reescribe aquí**) · **Lo mandado y lo
  que dice el robot** (dos bloques enfrentados bajo **dos rótulos distintos**) · **Lo que va a
  pasar y no es un fallo** (cinco viñetas, **todas con su medida**) · **Lo que esta pantalla no
  puede hacer** (tarjeta ámbar **permanente**, no un aviso temporal).

**6 · Pie.** El coste: esta pantalla mantiene `/odom`, `/estado_robot`, `/battery_state`,
`/motor_status` y `/collision_monitor_state`; **`/scan` solo durante el arranque del barrido y se
da de baja al confirmarlo**.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Enlace** | WebSocket + llegadas de `/odom` | insignia de tres estados con «WebSocket abierto\|cerrado» en mono al lado | pasados 3 s sin `/odom` cae a ámbar y **lista las tres causas sin elegir**. **Nunca verde por ausencia, y nunca rojo** |
| **Parada — bandera del robot** | `/estado_robot.parada_emergencia` | franja «parada ACTIVA» sobre el botón, **solo cuando el campo llega y vale true** | **no se pinta nada afirmativo**. El texto dice «no está llegando /estado_robot, así que desde aquí no se sabe si la parada se aplicó — mira el robot» |
| **Capa de seguridad** | `/collision_monitor_state` → `interpretarSeguridad()` | insignia + frase entera + **«qué hacer» en negrita**. Polígonos reales: «Aproximacion» y «Precaucion»; también puede traer «invalid source». 🔴 **Con `action_type = 3` (APROXIMACION) el texto tiene que decir que el robot NO PUEDE SALIR SOLO** — ver el bloque de abajo | efecto **DESCONOCIDO, visible y con su frase completa**: solo publica cuando el robot procesa un `cmd_vel_raw`. **La tarjeta no se oculta ni se pinta verde** |

### 🔴 `APROXIMACION` no es «va despacio»: es que el robot NO SE MUEVE, y no puede salir

Medido el 2026-08-09 con 24 estaciones en las cuatro direcciones (evidencias 93, 94 y 95). Con un
obstáculo dentro del círculo del `collision_monitor`:

```
pared DETRÁS a 16,8 cm, 188 cm libres delante, mandando por /cmd_vel_raw
  AVANZAR alejándose  ->  0,0 cm     GIRAR  ->  0,0°     RETROCEDER  ->  0,0 cm
```

`approach` escala el mando **entero** —lineal y angular— por el tiempo hasta colisión, y con un
punto ya dentro ese factor es **0**, **sin mirar si el movimiento acerca o aleja**.

⚠️ **Y el alumno no recibe nada.** `girar(360)` tarda 40 s —su plazo interno— y devuelve −0,1° sin
un solo mensaje: se lee como un robot colgado o como una web que no manda.

✅ **Requisito, y es la razón de que esto esté en la especificación:** cuando llegue
`action_type = 3` la tarjeta debe decir, con todas las letras, que **no se puede desbloquear desde
la web**:

> **El robot está bloqueado por la capa de seguridad.** Tiene un obstáculo a menos de 15 cm.
> **No puede salir solo, ni siquiera alejándose** — hay que retirar el obstáculo o mover el robot
> a mano.

🔴 **No ofrezcas un botón de «liberar» ni sugieras mandar marcha atrás**: está medido que no
funciona. Lo único que lo saca es una mano.

📌 **El umbral son 15 cm desde `base_footprint`** (`Aproximacion.radius: 0.15` desde el 2026-08-09;
antes 0.18). Si el texto cita una distancia, ésa es.

⚠️ **Y hay ~1 cm CIEGO** por delante y por detrás que ningún parámetro cubre: el `range_min` del
LIDAR son 10 cm y el borde del robot está a 9. **Un obstáculo pegado al robot puede no verse.** No
prometas en pantalla que la capa de seguridad ve todo lo que hay alrededor.

| **Velocidad lineal medida** | `/odom.twist.twist.linear.x` | mono, 3 decimales, «m/s» al 62 % debajo; antigüedad abajo; referencia «meseta real 0,199 m/s pidiendo 0,20» | raya `—` atenuada, **sin elemento `<data>`**. **Nunca 0,000** |
| **Velocidad angular medida** | `/odom.twist.twist.angular.z` | mono, 3 decimales, «rad/s»; antigüedad debajo | raya `—`, sin `<data>` |
| **Velocidad mandada** | **LOCAL**: el Twist que se republica a 10 Hz. **No viene del robot y el rótulo lo dice** | bajo el rótulo «Mandado (esta pestaña, 10 Hz)», **separado** del bloque «Medido» | con el bucle parado dice **«nada: el bucle está parado»**, no «0,000 m/s». **Mandar cero y no mandar nada son cosas distintas** |
| **Posición X / Y desde el reset** | `/odom.pose.pose.position` | mono, metros con 3 decimales, antigüedad debajo | raya `—`, sin `<data>` |
| **Rumbo (yaw)** | `/odom.pose.pose.orientation` | mono, grados con 1 decimal. **Es la orientación PLANA**: el driver publica `publicar_inclinacion=false` a propósito | raya `—` si el cuaternión no trae los cuatro componentes finitos |
| **Distancia en línea recta desde el reset** | derivado de la posición | mono, metros con 3 decimales, con la nota «**en línea recta desde el punto de reset; no es el recorrido**» | raya `—` si falta cualquiera de las dos coordenadas. **No se calcula con una sola** |
| **Antigüedad del último `/odom`** | reloj del navegador | «hace 0,2 s», 11 px, bajo cada valor | «no se sabe» mientras no haya llegado ninguno. **Nunca «hace 0 s»** |
| **Ritmo de `/odom` observado** | llegadas al navegador | «16,4 Hz observados en el navegador», con «16,53 Hz medidos en el robot» al lado | con menos de dos llegadas, «no se sabe», **nunca 0 Hz**. Un ritmo bajo dice que **algo entre el robot y esta pestaña pierde mensajes**, no que el robot publique despacio |
| **Barrido confirmado** | `/scan` — **una sola muestra**, durante el arranque; la suscripción se cierra al confirmarla | **hecho con hora fija**: «confirmado por un /scan real · 10:31:44». **No es un ritmo ni un indicador vivo** | «sin pedir» antes de pulsar; «/start_scan respondió pero no llegó ningún /scan real en 8 s» al vencer el tope; «se perdió la conexión mientras se esperaba». **Nunca se da por arrancado con la respuesta del servicio** |
| **Latido del nodo** | `/estado_robot.latido`, **dos lecturas** | «avanzó entre dos lecturas separadas 1,0 s» / «no avanzó en 1,0 s» | «no se sabe» si el topic no llega **o si solo hay una lectura** |
| **Antigüedad de `/odom` según el robot** | `/estado_robot.antiguedad_odom_s` | segundos con 1 decimal, junto al latido | `-1,0` es «no se sabe» y **se escribe así, nunca como 0** |
| **Batería** | `/battery_state.voltage` → `nivelBateria()` | mono, «8,28 V», insignia OK / BAJA / CRÍTICA (7,0 y 6,5 V). **El porcentaje NO aparece** | `NaN` cuando la lectura falla ⇒ DESCONOCIDO en ámbar, **nunca OK** |
| **Motor atascado** | `/motor_status` | insignia + qué oruga + antigüedad. **Solo se afirma con antigüedad válida** | `−1,0` ⇒ «no se sabe», **nunca «no hay atasco»** |
| **Último reset de odometría** | respuesta de `/set_pos_and_yaw` | «orden enviada · 10:33:02» + el texto de confirmación del servicio | si no se ha pedido: «la posición y el rumbo de abajo se cuentan desde que arrancó el driver, no desde un reset tuyo». Si `success=false`: «el robot respondió que la llamada falló» |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso** | Barra de parada activa. Renglón: barrido «sin confirmar», seguridad «no ha dicho nada». **Comprobación presencial abierta a ancho completo.** Mando **desactivado con el motivo al lado**. Columna derecha con los rótulos puestos y **rayas** en los valores | «Antes de la primera orden, míralo tú.» Y en el mando: «Confirma la comprobación de arriba para activar las celdas» |
| **No llego al robot** | Insignia neutra, WebSocket cerrado. Las cinco celdas y los botones del barrido desactivados. **El botón de parada sigue pulsable** y, si se pulsa, dice en rojo que NO se envió | «El navegador no consigue abrir el WebSocket. El cliente reintenta solo, con espera creciente de 1 s a 30 s.» El plazo son 10 s: **un socket que no abre no da error nunca** |
| **Enlace abierto y telemetría muda** | Insignia ámbar. Los valores de la derecha, en rayas. **El mando sigue activo: el robot puede estar sano** | «Hace más de 3 s que no llega /odom. Las causas posibles, sin elegir…» Y en el mando: «Puedes seguir mandando, pero desde aquí no se verá si el robot se mueve — míralo» |
| **Barrido sin confirmar** | Insignia de barrido en ámbar. El botón «Arrancar barrido» destacado. **Las celdas del mando siguen activas** | «El barrido arranca apagado a propósito… Sin /scan la capa de seguridad bloquea el movimiento — medido: 0,0 cm contra 9,9 del control. Si mandas ahora, es probable que el robot no se mueva, **y no está roto**» |
| **Con el dedo puesto** | La celda pulsada en color primario, **sin ninguna animación de repetición**. El bloque «Mandado» con lo que sale ahora. El bloque «Medido» **muestreado cada 500 ms, no a 16,5 Hz** | «Mandando 0,200 m/s · 0,000 rad/s, diez veces por segundo, en /cmd_vel_raw.» **Nada dice que el robot se esté moviendo**: eso lo dice el bloque «Medido» |
| **La capa de seguridad no ha dicho nada** | Tarjeta visible, tono neutro, **con el texto entero. No se oculta ni se colapsa** | «No se sabe: la capa de seguridad solo informa cuando el robot recibe órdenes de movimiento. **Esto NO significa que todo esté bien**» |
| **La capa de seguridad bloquea o frena** | Tarjeta ámbar con el polígono o el motivo nombrado y la acción en negrita. La insignia cambia **con una transición de 200 ms solo de color** | Bloqueo: «no le llega el barrido del LIDAR… enciende el barrido antes de mover el robot». Frenando: «va más despacio porque hay algo cerca ("Precaucion") — **si vas marcha atrás alejándote, también frena: el polígono no sabe hacia dónde vas**» |
| **Parada ACTIVA** | Franja sobre el botón, **visible aunque nadie haya pulsado en esta pestaña**. El mando **queda activo** —nadie miente diciendo que lo desactiva el robot— con la franja explicando por qué no va a pasar nada | «parada ACTIVA — el robot no aceptará ninguna orden hasta que se libere presencialmente. Al liberarla con un objetivo de Nav2 vivo el robot arrancó solo —34,7 cm medidos—» |

**Copia literal.**

```
Conducir
Se conduce con el dedo puesto: mientras mantienes pulsado, esta pestaña manda velocidad a
/cmd_vel_raw diez veces por segundo. Al soltar, se manda parar. El robot pararía igual si
dejaras de mandar sin más —el vigilante del driver corta a los 0,3 s—, pero eso es que el
robot se pare por inanición, no que tú lo pares.

Antes de la primera orden, míralo tú
Esto no lo comprueba el robot ni esta pantalla: lo compruebas tú, que estás en la sala.
· Espacio delante, detrás y a los lados. Las medidas de banco de este proyecto se hacen
  con 1 m por delante, 1 m por detrás y 40 cm a cada lado.
· 🔴 El borde de una mesa, un escalón o una escalera NO frenan al robot. La capa de
  seguridad tiene una sola fuente, /scan, y un rayo que no vuelve no es un obstáculo para
  ella: no es un ajuste que falte, es la dimensionalidad del sensor. Regla del laboratorio:
  suelo continuo y cerrado.
· El plano de barrido está a 15,5 cm del suelo. Un zócalo, un cable, una caja baja o un pie
  quedan por debajo y el robot no los ve. «Despejado a ras de suelo» no basta.
· Cuenta con unos 10 cm de más después de soltar: la parada de la capa de seguridad son
  9,9 cm a 0,25 m/s y 10,6 cm a 0,40.
· Que alguien mire el robot mientras otro conduce.
[ Lo he mirado — activar el mando ]

Confirmaste a las 10:32:07 que lo habías mirado. No se comprobó nada: es tu palabra, no una
medida.

Mantén pulsado para conducir. Al soltar, se manda parar.
Se publica en /cmd_vel_raw, que es la ENTRADA de la capa de seguridad. Publicar en /cmd_vel
también movería el robot y se saltaría la seguridad entera sin ningún aviso; por eso
/cmd_vel no está en la lista blanca del robot y esta pantalla no lo puede alcanzar ni por
equivocación.

0,10 y 0,20 m/s, las dos medidas: pidiendo 0,20 la meseta real es 0,199 m/s y se alcanza en
~0,5 s de rampa. El tope del robot son 0,40 m/s y aquí no se ofrece.
Giro fijo a 0,8 rad/s. Entre 0,5 y 2,0 rad/s el robot cumple el 99–102 % de lo que se le
pide.
No hay diagonales, y no es una simplificación: avanzar y girar a la vez son combinaciones
de v y w que nadie ha caracterizado en este robot, así que no se ofrecen.

Parar manda un twist cero y corta el bucle. Soltar cualquier otra celda hace exactamente lo
mismo; ésta existe para poder mandarlo sin tener nada pulsado.
orden de parar enviada · 10:34:11 — el mensaje salió por el WebSocket. Cuánto recorre el
robot después de eso no lo sabe el navegador: mídelo con la cinta.

Barrido del LIDAR
Sin /scan el robot no se puede conducir: la capa de seguridad bloquea el movimiento, y está
medido — 0,0 cm contra 9,9 del control. El barrido arranca apagado con el robot a
propósito: si no, el X2 giraría a 11,8 Hz las 24 horas en los 16 robots en vez de a 2,7.
Que el robot no se mueva antes de pulsar aquí no es una avería.
Al pulsar se llama a /start_scan y se espera un /scan de verdad, con un tope de 8 s. La
respuesta de /start_scan viene VACÍA: no llega ni un bit que diga qué pasó en el robot, así
que no cuenta como arranque. Por WebSocket la llamada tarda 1,4–2,1 s medidos, 6 de 6.

barrido confirmado por un /scan real · 10:31:44
Ha llegado un barrido de verdad, no sólo una respuesta del servicio: es lo único que prueba
que el LIDAR está entregando datos. Esta pestaña deja de escuchar /scan en ese momento,
porque es el 83 % del tráfico de un robot: así que «confirmado a las 10:31:44» no dice que
siga llegando ahora. Para ver el barrido en vivo, la pestaña LIDAR.

La capa de seguridad no ha dicho nada.
Sólo informa cuando el robot recibe órdenes de movimiento, así que con el robot quieto no
llega ningún mensaje: 0 en 12 s en reposo, y uno en 5 s conduciendo. Esto NO significa que
todo esté bien.

Si te vas a otra pestaña, el robot para.
Al ocultarse esta pestaña se manda un twist cero explícito. Pararía igual sin eso —el
navegador baja el temporizador a ~1 Hz y el vigilante del driver corta a los 0,3 s—, pero
eso sería pararlo por inanición en vez de mandarlo parar. Es el lado seguro, y sorprende:
por eso está escrito antes de que pase.

Poner la odometría a cero
/set_pos_and_yaw con (0, 0, 0). Es el único reset que existe: el driver rechaza cualquier
otro valor porque el SDK no puede fijar una pose arbitraria, y por eso aquí no hay campos
donde escribir coordenadas.
El robot responde que la llamada al SDK no lanzó. Eso no dice que el efecto ocurriera:
quien lo dice es que la posición de aquí abajo vuelva a 0,000.
🔴 Y no arregla la deriva del rumbo: pone el origen a cero, no la deriva.

Mandado (esta pestaña, 10 Hz): 0,200 m/s · 0,000 rad/s
Medido (/odom): 0,181 m/s · 0,002 rad/s · hace 0,2 s
Que no coincidan no es desobediencia: hay ~0,5 s de rampa, la capa de seguridad puede estar
frenando al 40 %, y el driver proyecta la velocidad sobre el rumbo antes de publicarla. La
diferencia no se convierte en un porcentaje: sería una cifra que nadie ha medido.

Lo que va a pasar y no es un fallo
· Retroceder junto a una pared tarda más de lo esperado. El polígono de precaución es
  estático y se extiende 0,36 m hacia delante: mientras la pared esté dentro, la seguridad
  frena al 40 % aunque el robot se esté alejando. Medido: un retroceso de 2 s a 0,15 m/s
  recorrió 14 cm en vez de 30. No es que no obedezca.
· Frenar deja recorrido: 9,9 cm a 0,25 m/s y 10,6–10,7 cm a 0,40.
· El robot se planta en la boca de un paso estrecho. El círculo de aproximación mide 0,18 m
  de radio, así que necesita ~36 cm más margen. Medido el 2026-07-31: entró en un paso de
  40 cm con el camino despejado delante y se quedó bloqueado. Marcha atrás sí pudo salir.
· El rumbo se va casi un grado cada 30 s los primeros minutos tras encender el RVR. Medido:
  0,97 °/30 s recién encendido y 0,001 °/30 s siete minutos después — 970 veces menos.
  Sobre una práctica de 15 min son decenas de grados. Se va sola dejando el robot un rato
  en marcha, y poner la odometría a cero no la corrige.
· Sin barrido del LIDAR el robot no se mueve: 0,0 cm contra 9,9 del control.

Lo que esta pantalla no puede hacer
· No hay ningún control de acceso. rosbridge 2.7.0 no trae autenticación —el parámetro no
  existe—, así que cualquiera que esté en la red del aula y sepa la dirección puede conducir
  este robot desde su portátil. Se cierra con un proxy que valide el testigo en cada robot:
  no está construido.
· No se puede decir cuánto tarda una orden en llegar a los motores. El recorrido navegador →
  rosbridge → driver → motores no se ha medido en este proyecto, y una cifra inventada aquí
  sería peor que ninguna.
· No se puede decir que el robot se haya movido. Que el mensaje salga por el WebSocket es lo
  único que ve el navegador; que el robot se moviera lo dice /odom, y /odom puede estar mudo
  con el topic existiendo.
```

**Prohibido aquí.**

- **Publicar en `/cmd_vel`.** Es la **SALIDA** del `collision_monitor`: funciona, mueve el robot y
  **salta la capa de seguridad entera sin un solo aviso**.
- Mandar el campo `qos` o `throttle_rate` en un `subscribe`.
- **Afirmar que el robot se movió, se paró o cambió de estado** porque un `publish` no lanzó o un
  servicio devolvió `success=true`.
- **Diagonales, joystick analógico, o teclado con repetición automática.**
- Un porcentaje de cumplimiento entre lo mandado y lo medido, o una gráfica de tendencia.
- Cualquier cifra del tiempo que tarda una orden en llegar a los motores.
- **Pulsos, latidos o brillos infinitos**: ni en el botón de parada, ni en la celda pulsada, ni en
  las insignias.
- Leer el silencio de `/collision_monitor_state` como «todo bien», ocultar la tarjeta cuando el
  efecto es DESCONOCIDO, o reescribir sus frases en el componente.

**🎨 Prompt para Stitch — Conducir**

```
Pantalla de teleoperación de un robot, en español, oscura.

Fondo: pozo #07080D con los dos orbes fijos.

De arriba abajo:
1. Franja PEGAJOSA con el botón «PARADA DE EMERGENCIA» a ancho completo, 64 px de alto,
   coral #FF5C39 a plena saturación, versalitas, sin compartir fila; y pegado debajo, SIN
   separación, un renglón de altura fija con TRES insignias: «enlace», «barrido», «capa de
   seguridad». Ninguna de las tres en verde: enlace en verde «en línea», barrido en ámbar
   «sin confirmar», seguridad en neutro «no ha dicho nada».
2. Tarjeta de vidrio a ancho completo «Antes de la primera orden, míralo tú», con cinco
   viñetas de texto y un botón «Lo he mirado — activar el mando».
3. Rejilla de dos columnas con items-start.
   IZQUIERDA: tarjeta de enlace; tarjeta «Barrido del LIDAR» con dos botones; tarjeta
   «Mando» con una rejilla 3×3 donde SOLO existen CINCO celdas (arriba-centro, izquierda,
   centro, derecha, abajo-centro) — las cuatro ESQUINAS son huecos completamente vacíos, sin
   borde y sin botón desactivado. Celdas de 64 px de alto mínimo; la del centro («parar») se
   dibuja distinta de las otras cuatro. Al lado, un selector de velocidad con dos opciones,
   0,10 y 0,20 m/s. Debajo, tarjeta «Poner la odometría a cero» con un solo botón y NINGÚN
   campo de coordenadas.
   DERECHA: tarjeta «La capa de seguridad» en tono neutro con texto completo; tarjeta con dos
   bloques enfrentados bajo los rótulos «Mandado (esta pestaña, 10 Hz)» y «Medido (/odom)»,
   con cifras en Geist Mono de 3 decimales y su antigüedad; tarjeta «Lo que va a pasar y no
   es un fallo» con cinco viñetas; y tarjeta ámbar permanente «Lo que esta pantalla no puede
   hacer».
4. Pie con el coste en kB/s.

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: celdas en diagonal, joystick, gráficas de velocidad, porcentajes de
cumplimiento, ningún botón de liberar la parada, ningún indicador que parpadee.

Aplica además la sección §8 entera.
```

---

### 5.7 · Telemetría — `/robot/[id]/telemetria`

**Trabajo.** Enseñar lo que el robot mide, **cada número con SU antigüedad y su procedencia**,
porque **llegan por caminos distintos y refrescan a ritmos distintos**.

**Quién la usa.** El alumno para contrastar con la cinta; quien monta para decidir si algo está
rancio.

**Primera lectura.** El **VOLTAJE** de la batería, a ancho completo, con su antigüedad pegada
debajo. Por tres razones y ninguna es estética:

1. es **el único número de esta pantalla que decide una acción fuera de ella** —ir a cargar ese
   robot—; todo lo demás es para contrastar;
2. es **el más LENTO** de la pantalla (cada 30,0 s exactos), así que es donde **la antigüedad más
   cambia el significado del número**: 28 s es normal, 90 s es que el keepalive no está corriendo;
3. es el número **que el firmware ya falló al resumir** —100 % con la batería a 8,29 V—, así que
   enseñarlo en voltios **es lo que corrige ese fallo**.

Lo segundo, ya dentro de la rejilla, es la **POSICIÓN con los ENCODERS pegados al lado**: es el
par que el alumno contrasta con la cinta, y los encoders van ahí porque son **la única fuente que
no depende del marco de referencia** (7792 ticks/m contra cinta), o sea **el juez de la otra**.

El estado del enlace **no se repite aquí**: ya está en la cabecera del marco.

**Composición.**

**0 · CINTA DE PROCEDENCIA**, una sola línea en mono bajo las pestañas, **sin caja**: enumera los
topics que **esta pantalla paga** y su coste medido —«suscrita a /odom · /encoders ·
/motor_status · /battery_state · /estado_robot — 14,92 kB/s medidos (los cuatro primeros;
/estado_robot no tiene caudal medido y **no se suma**)». No es adorno: **es la razón de que
`/scan` y `/imu` no estén aquí**, y hace visible que esta pantalla **cuesta dinero de WiFi**.

**1 · BANDA «Batería»**, ancho completo, una sola tarjeta. Línea de procedencia en mono:
`/battery_state · cada 30,0 s · el keepalive del driver`. Dentro, el voltaje en cifra grande
(mono, unidad al 62 % por partición), debajo el veredicto en texto y la antigüedad. Insignia de
nivel arriba a la derecha **solo si el nivel no es DESCONOCIDO**. Los umbrales bajan al
desplegable de contexto: **son constantes, no estado**. **El porcentaje del firmware NO aparece.**

**2 · BANDA «Flujo continuo del RVR»**, con la frase «llega a 16,5 Hz y **se lee muestreado cada
500 ms**: un número que parpadea dieciséis veces por segundo no se puede leer». Debajo, dos
tarjetas en dos columnas:

- **2a · Odometría** — `/odom · 16,53 Hz · stream del RVR, cinco componentes`. Rejilla interna de
  dos columnas: Posición X, Posición Y, Rumbo (yaw), **Inclinación (roll/pitch)**, Velocidad
  lineal, Velocidad angular. Al pie, la **línea de frescura doble** (aquí / en el robot) y el
  contexto con la deriva de yaw de los primeros minutos.
- **2b · Encoders** — `/encoders · 16,57 Hz`. Dos datos, ticks con **los metros derivados como
  nota bajo cada uno**. **Pegada a 2a a propósito: es la fuente que arbitra la de al lado.**
- **2c · IMU** a ancho completo, en estado **NO CONSTRUIDO**, con su bloqueo escrito y su coste
  medido (9,48 kB/s).

**3 · BANDA «Sondeo del driver, republicado desde memoria»**. Una tarjeta, **Motores** —
`/motor_status · 1 Hz · lo que se sondea va cada 30 s`. Cuatro datos en rejilla (dos temperaturas
con la antigüedad térmica **pegada a cada una**, dos estados térmicos **en crudo**), y debajo,
separada por una línea de 1 px, **la fila de hechos**: Atasco y Fallo eléctrico como insignias con
su propia antigüedad. Va **después** de la banda 2 aunque sea más lenta **porque su contenido es
diagnóstico, no medida de práctica**.

**4 · BANDA «Solo si alguien lo pidió al arrancar»**. Una tarjeta, **Color**, en **NO
CONSTRUIDO**, con los tres bloqueos escritos.

**5 · BANDA «Salidas»**, al final y **visualmente separada por un espacio doble**: los LEDs **no
son telemetría, son órdenes**. Selector con los doce grupos y cinco botones de color. El resultado
sale en un aviso con la hora, y **nunca dice más que «orden enviada»**. El `led_id 10` está en la
lista **con su nota medida pegada, no escondido**.

Rejilla de dos columnas a partir de `lg`. **Ningún acordeón por encima del nivel del desplegable
de contexto**: esconder POR QUÉ algo está en ámbar deja el ámbar sin acción posible.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Voltaje de la batería** | `/battery_state.voltage` | Mono, 3xl, dos decimales con coma y la unidad al 62 %: «8,23 V». Emite `<data value="8.23">` | Una raya `—` pequeña y apagada, con `title="no se sabe"`, y **SIN elemento `<data>`**. **Nunca 0,00 V** |
| **Veredicto de la batería** | derivado del voltaje, umbrales 7,0 / 6,5 V del firmware | Texto bajo el número: «por encima del umbral» · «toca cargar» · «el RVR se va a apagar». Insignia a juego arriba a la derecha | **La insignia NO se pinta.** Repetir «no se sabe» arriba a la derecha con los valores ya en rayas **convierte el hueco en el contenido de la pantalla** |
| **Antigüedad de la batería** | `msDesdeUltimo('/battery_state')` | Línea subordinada: «hace 12,4 s». **Envejece sola** | No se pinta. **Si el valor es un hueco, la antigüedad DE ESE VALOR tampoco existe** |
| **Posición X / Y** | `/odom.pose.pose.position` | Mono, tres decimales: «1,204 m». **Muestreado a 500 ms** | Raya, sin `<data>` |
| **Rumbo (yaw)** | `/odom.pose.pose.orientation` | Mono, un decimal, con signo: «+87,7°». Referencia debajo: «girar 90° dio 86,6 / 86,2 / 87,7° en n=3» | Raya. Devuelve nulo si alguno de los cuatro componentes no es finito |
| **Inclinación (roll y pitch)** | los otros dos ángulos del mismo cuaternión | Un solo dato con el par: «+0,00° / +0,00°», y la nota de por qué salen a cero. **Es un CENTINELA**: un valor distinto de cero delata que alguien arrancó el driver con `publicar_inclinacion:=true` | Raya. **No se asume 0,00° por defecto**: eso sería afirmar que el robot está plano sin haber recibido nada |
| **Velocidad lineal** | `/odom.twist.twist.linear.x` | Mono, tres decimales: «0,199 m/s». Referencia: «meseta real 0,199 m/s pidiendo 0,20» | Raya |
| **Velocidad angular** | `/odom.twist.twist.angular.z` | Mono, tres decimales: «0,802 rad/s» | Raya |
| **Última `/odom` · aquí y en el robot** | `msDesdeUltimo('/odom')` y `/estado_robot.antiguedad_odom_s` | Dos cifras en una línea: «aquí hace 61 ms · en el robot hace 0,1 s», con **la etiqueta NO VERIFICADO en la segunda**. Si crece la de aquí y la del robot no, **el que pierde mensajes es el camino**; si crece la del robot, **`/odom` no se está completando** | Cada mitad por separado. Si `/estado_robot` no llega —driver anterior al 2026-08-04— **se dice eso, no se calla** |
| **Ticks de la rueda izquierda / derecha** | `/encoders.left_wheel_count` y `.right_wheel_count` (`atriz_rvr_msgs/msg/Encoder`, **SINGULAR**) | Mono, entero con signo: «−1356 ticks», y como nota debajo los metros derivados: «−0,174 m recorridos» (7792 ticks/m) | Raya, **y sin la nota de metros: no se divide un hueco** |
| **Temperatura oruga izquierda / derecha** | `/motor_status.temperatura_*` | Mono, un decimal: «27,5 °C». **Antigüedad pegada** desde `antiguedad_termico_s`. Referencias: 27,5 y 28,3 °C en reposo | Raya y sin antigüedad |
| **Estado térmico izquierdo y derecho, EN CRUDO** | `/motor_status.estado_termico_*` (uint8) | Dos datos con **el entero pelado**: «0» y «0». **Sin traducir a palabras, sin color.** Una sola nota debajo del par explica que 0 es normal y que el resto no está caracterizado | Raya. **Un 0 pintado por defecto diría «normal» sin que nadie lo haya dicho** |
| **Atasco** | banderas filtradas por `antiguedad_atasco_s` | Insignia con la antigüedad al lado: «oruga trabada» / «sin atasco». Si es true, qué oruga y que **el propio RVR enciende LEDs amarillos y rojos** durante el atasco | Insignia NEUTRO con «no se sabe» **y SIN antigüedad al lado** —porque las dos dirían lo mismo—. Debajo, el contexto que explica el −1,0 |
| **Fallo eléctrico** | bandera filtrada por `antiguedad_fallo_s` | Insignia con antigüedad: «hay fallo» / «sin fallo». **Aquí el false SÍ significa «se comprobó y no hay»**: se sondea cada 30 s | Insignia NEUTRO con «no se sabe», sin antigüedad |
| **Aceleración lineal y \|g\| (IMU)** | `/imu.linear_acceleration` — **AUTORIZADO en el robot y NO MODELADO en la web** | Cuando se construya: tres ejes en mono con tres decimales, y el módulo con su aviso: «\|g\| = 9,435 m/s² contra 9,807 — **3,8 % corto, el sensor está descalibrado**» | Hoy: **NO CONSTRUIDO**, con el bloqueo exacto y su coste medido, 9,48 kB/s. **No se dibuja una tarjeta vacía ni un esqueleto** |
| **Giroscopio (IMU)** | `/imu.angular_velocity` | Cuando se construya: tres ejes en rad/s. **SIN cifra de frecuencia de referencia al lado**: sus tres tomas dieron 13,34 · 16,30 · 16,51 Hz (±11 % sin explicar) | NO CONSTRUIDO, en la misma tarjeta |
| **Color RGB y confianza** | `/color.rgb_color` y `.confidence` — AUTORIZADO y NO MODELADO | Cuando se construya: los tres enteros 0-255, una muestra de color **como clase, nunca `style` en línea** (el modo oscuro forzado de Edge reescribe los `style` y rompe la hidratación), la confianza tal cual, y los cocientes R/G y B/G con sus referencias. **El canal «claro» NO se puede enseñar: no viaja en el mensaje** | NO CONSTRUIDO, con los tres bloqueos escritos. Y cuando llegue: **unos ceros NO se interpretan como «sensor apagado»** |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso** | La cinta de procedencia y las cinco bandas ya montadas, con sus títulos y procedencias. `/odom`, `/encoders` y `/motor_status` se rellenan en menos de un segundo; **la banda de batería puede tardar hasta medio minuto y lo dice** | «Todavía no ha llegado ningún /battery_state. Llega cada 30,0 s, así que puede tardar medio minuto en aparecer **con el robot perfecto**» |
| **No llego al robot** | Todos los valores en rayas y **NINGUNA tarjeta pinta insignia de estado**. Los botones de LED desactivados | «Sin enlace no se puede llamar a ningún servicio.» Y en la cinta: «cero mensajes desde que se abrió esta pestaña» |
| **El enlace va y el robot no manda telemetría** | **Ámbar, nunca rojo.** Valores en rayas y una nota al pie con **las tres causas listadas sin elegir** | «El WebSocket está abierto y hace más de 3 s que no llega /odom. Esto no es una avería, y el navegador no puede saber cuál de las causas es» |
| **Llega el mensaje y el número es NaN** | **Distinto de un cero y distinto de no haber llegado nada**: raya en el valor, y un párrafo explicando que el dato SÍ llegó y venía vacío a propósito | «Ha llegado un /battery_state sin voltaje válido. El driver publica NaN a propósito cuando la lectura falla —el RVR apagado con la Pi viva, que es como se carga— porque 0,00 V sería un dato y esto es un hueco» |
| **El dato existe y está rancio** | El número **se sigue pintando** —es un dato real— pero su antigüedad pasa de 35 s y aparece una advertencia. **El número NO cambia de color: no es un fallo, es una fecha** | «La temperatura tiene 47 s. El sondeo va cada 30 s y /motor_status se republica a 1 Hz desde memoria, así que por encima de 35 s lo que ves es el mismo dato repetido» |
| **El campo llega y significa «nunca se ha sabido nada»** | Insignia NEUTRO con «no se sabe» **y sin antigüedad al lado** (si no, la pantalla dice la misma frase dos veces: «Atasco [no se sabe] no se sabe») | «La antigüedad del atasco vale −1,0, que significa "nunca se ha sabido nada de eso". Las banderas valen false porque es su valor inicial, no porque nadie haya comprobado nada» |
| **No construido · IMU y Color** | Tarjeta con su título y su procedencia, cuerpo con **una casilla que nombra el bloqueo en pasos numerados**. **Ni esqueleto, ni «próximamente», ni un hueco silencioso.** El coste medido va escrito **para que se vea que la decisión tiene precio** | «No construido. El robot autoriza este topic; esta web todavía no modela su .msg, y añadirlo exige **leer su definición, no adivinarla**» |
| **Orden a un LED enviada** | Un aviso de nivel **ATENCIÓN (no éxito verde)** con la hora exacta. **No cambia nada más**: no hay ningún punto que se encienda para representar el LED, **porque nadie sabe si se encendió** | «orden enviada: rojo · 18:42:07 — el robot respondió que la llamada al SDK no lanzó. Eso no dice que el efecto físico ocurriera» |

**Copia literal.**

```
Se decide por voltios. El porcentaje del firmware dijo 100 % con la batería a 8,29 V, a
1,29 V del umbral de «baja», así que aquí no aparece.

Umbrales del propio firmware: baja por debajo de 7,00 V, crítica por debajo de 6,50 V, con
0,2 V de histéresis.

Ha llegado un /battery_state sin voltaje válido. El driver publica NaN a propósito cuando
la lectura falla —el RVR apagado con la Raspberry Pi viva, que es como se carga— porque
0,00 V sería un dato y esto es un hueco.

Las covarianzas de /odom y de /imu no se pintan. El driver no las rellena, así que llegan a
0.0 — y en ROS un 0.0 en la covarianza significa «certeza perfecta». Enseñarlas sería
enseñar una confianza que nadie ha calculado.

Roll y pitch salen +0,00° porque el driver publica la orientación plana: publicar_inclinacion
está en false por defecto. Si aquí ves 6,9°, alguien lo arrancó con ese parámetro en true, y
esos grados son el acelerómetro descalibrado del RVR, no el suelo.

La única fuente que no depende del marco de referencia: 7792 ticks/m, contrastados contra
cinta métrica. Los ticks llegan con signo porque el driver ya convierte los 32 bits sin
signo del RVR, donde un retroceso se veía como 4294965940 en vez de −1356.

La deriva del rumbo es unas mil veces mayor los primeros minutos tras encender el RVR:
0,97 °/30 s recién encendido contra 0,001 °/30 s siete minutos después. Poner la odometría a
cero no lo corrige: pone el origen a cero, no la deriva. Se va sola dejando el robot un rato
en marcha.

La temperatura tiene 47 s. El sondeo va cada 30 s y /motor_status se republica a 1 Hz desde
memoria, así que por encima de 35 s lo que ves es el mismo dato repetido, no una temperatura
que se mantenga.

0 es normal. Los demás valores los define el RVR y este proyecto no los ha caracterizado: se
enseñan sin traducir.

La antigüedad del atasco vale −1,0, que significa «nunca se ha sabido nada de eso»: no ha
llegado ninguna notificación desde que arrancó el driver. Las banderas de abajo valen false
porque es su valor inicial, no porque nadie haya comprobado nada.

No construido. El robot autoriza /imu y esta web todavía no modela sensor_msgs/msg/Imu:
hasta que su definición se lea y se añada, aquí no se puede pintar nada. Cuando exista irá
detrás de un botón y no de fondo, porque cuesta 9,48 kB/s medidos. Y llevará dos avisos
pegados a la cifra: |g| sale 9,435 m/s² contra los 9,807 de la gravedad —un 3,8 % corto, el
sensor está descalibrado— y su ritmo no es estable: 13,34 · 16,30 · 16,51 Hz en tres tomas,
un ±11 % que nadie ha explicado, así que aquí no va ninguna frecuencia de referencia.

No construido. El robot autoriza /color y esta web todavía no modela
atriz_rvr_msgs/msg/Color. Y cuando se construya seguirá faltando lo principal: estos valores
solo son luz de verdad si alguien arrancó el driver con color_detection:=true, y esta web no
puede saberlo —rosbridge va con params_glob '[]' y no lee parámetros—. Tampoco se deduce de
que lleguen ceros: /color publicó [0, 0, 0] durante meses, a 16 Hz, con el topic pareciendo
sano.

La confianza es siempre 0, y no por falta de paleta: el RVR tiene cinco colores cargados y
activos. Es que las superficies del laboratorio no se parecen a ninguno de los cinco.

Encender un LED sirve para una cosa: encontrar este robot entre los dieciséis, mirando la
sala. La orden va a un grupo concreto de la tabla de doce del driver. El led_id 10
(undercarriage_white) está en la lista con su nota: se midió que responde igual que los
demás y el LED de los bajos no se encendió —lo enciende enable_color_detection, que es otro
comando—; después el driver corrigió cuántos valores de brillo manda a ese grupo, y nadie lo
ha vuelto a medir.
```

**Prohibido aquí.**

- **Pintar `/battery_state.percentage`**, ni siquiera pequeño y explicado. **Se RETIRA**: un
  número declarado inútil ocupa el sitio del que decide. Su explicación se queda, **en una línea
  de contexto, sin cifra**.
- **Una barra, un aro o un medidor de nivel de batería.** Exigiría un máximo, y **este proyecto no
  tiene medido el voltaje de «lleno»**: la barra inventaría la escala entera.
- **Traducir `estado_termico_*` a palabras, iconos o color.**
- **Pintar las covarianzas** de `/odom` o `/imu`.
- Decir «el sensor de color está apagado» o cualquier estado de configuración **deducido de que un
  valor llegue a cero**.
- Decir «LED encendido», «color cambiado», «efecto confirmado» u «orden confirmada».
- **Mostrar `/ambient_light`.** No está en la lista blanca, y en este montaje un valor alto
  significa «el robot tiene LEDs encendidos», no «hay luz».
- Gráficas de tendencia, sparklines, **contadores que suben de un valor a otro**, o cualquier
  animación al llegar un dato.

**🎨 Prompt para Stitch — Telemetría**

```
Pantalla de telemetría de un robot, en español, oscura y densa.

Fondo: pozo #07080D con los dos orbes fijos. Arriba, la cabecera del marco con su banda de
parada.

De arriba abajo:
0. Una sola línea en Geist Mono, sin caja, listando los topics suscritos y su coste en kB/s.
1. Banda «Batería» a ancho completo: una línea de procedencia en mono, el voltaje «8,23 V»
   en Geist Mono 3xl con la unidad al 62 % del tamaño, el veredicto en texto debajo, la
   antigüedad «hace 12,4 s» a 11,5 px, y una insignia de nivel arriba a la derecha. NINGÚN
   porcentaje, NINGUNA barra de nivel.
2. Etiqueta de sección «Flujo continuo del RVR» con una frase explicativa. Debajo, dos
   tarjetas de vidrio en dos columnas: «Odometría» (rejilla interna de dos columnas con seis
   medidas en mono, cada una con microetiqueta en versalitas de 10 px arriba, cifra a 38 px
   y antigüedad a 11,5 px debajo) y «Encoders» (dos medidas con una nota de metros bajo cada
   una). Debajo, a ancho completo, una tarjeta «IMU» en estado NO CONSTRUIDO con una casilla
   de pasos numerados.
3. Etiqueta de sección «Sondeo del driver, republicado desde memoria», y una tarjeta
   «Motores» con cuatro medidas en rejilla —dos temperaturas y DOS ENTEROS PELADOS sin
   traducir— y, separada por una línea de 1 px, una fila con dos insignias y sus antigüedades.
4. Etiqueta «Solo si alguien lo pidió al arrancar» y una tarjeta «Color» en NO CONSTRUIDO.
5. Separada por un espacio doble, la banda «Salidas»: una tarjeta «LEDs · encontrar este
   robot en la sala» con un selector de doce grupos y cinco botones de color, y un aviso
   ámbar con la hora que dice sólo «orden enviada».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: porcentaje de batería, barra o aro de nivel, gráficas, sparklines, ningún LED
dibujado que se encienda, ninguna traducción de los estados térmicos a palabras o color.

Aplica además la sección §8 entera.
```

---

### 5.8 · LIDAR — `/robot/[id]/lidar`

**Trabajo.** Dibujar el barrido para ver **lo que ve el robot**, **pagando su coste a la vista** y
**soltándolo al salir**.

**Quién la usa.** El alumno, en ratos cortos; quien monta, para reconocer un barrido congelado.

**Primera lectura.** **NO es el dibujo**: es **el sello de antigüedad del último barrido,
estampado DENTRO del propio lienzo**, arriba a la izquierda, en mono y del mismo tamaño que un
dato («hace 84 ms»). Va ahí y no debajo porque **un barrido congelado es píxel a píxel idéntico a
uno vivo** — es el modo de fallo medido: el descriptor USB del LIDAR muerto con el nodo vivo,
`systemctl` en `active`, sus servicios contestando y `/odom` a 16,58 Hz. **Un dibujo que no se
actualiza no se distingue de una habitación quieta**, así que el número que dice CUÁNDO tiene que
estar tocando la imagen.

Justo después se lee la segunda línea del sello: **«217 de 260 puntos»**, que es lo que impide
leer un barrido pobre como una habitación vacía. **Y solo entonces el dibujo.**

**Composición.** Una sola columna: **el lienzo es cuadrado y manda**. Partir en dos columnas lo
encogería, y aquí **la resolución ES la información** (el X2 tira un rayo cada 1,7 cm a 0,68 m).

**1 · BANDA DE COSTE**, fija arriba, **siempre visible**. Es lo primero de la página **porque esta
ruta existe por el coste, no por organización**: los ~67 kB/s de `/scan` (83 % de los 80,7
medidos), los ~8,6 Mbit/s que serían 16 pestañas, y **las DOS suscripciones extra sin caudal
medido declaradas como tales** — un aviso de coste que deja una fuera suena a que ya lo contó
todo. Cierra con las dos frases que la persona controla: **la suscripción muere al salir**, y **el
barrido NO se apaga al salir**.

**2 · BARRA DE MANDO DEL BARRIDO**, dos botones y nada más. El de encender **espera un `/scan`
real** (tope de 8 s), no la respuesta del servicio. A su derecha, en mono, **los dos números
medidos por esta pantalla y separados a propósito**: «`/start_scan` respondió a los 1,9 s» y
«primer barrido a los 2,4 s» — **el segundo es el efecto y es el que vale**. Debajo, la referencia
del robot para el primero (1,4-2,1 s, n=6) y **la ausencia declarada de referencia para el
segundo**.

**3 · EL LIENZO**, cuadrado, 560 px o el ancho disponible, centrado, borde de 1 px. **Dentro del
propio lienzo**, esquina superior izquierda, **el SELLO** en mono: antigüedad, «N de M puntos», y
el ritmo observado **con su referencia al lado**. Contenido: **tres anillos y no dieciséis** —0,5
· 1,0 · 2,0 m—; el radio del lienzo es **2,5 m de los 8,0** que declara el sensor, y eso se dice
al pie **junto con cuántos puntos caen fuera**. En el centro, **NO el robot a escala**: una cruz
de 9 px y una flecha corta hacia arriba marcando «adelante». Los puntos, **cuadrados de 3 px, sin
degradado y sin estela**: cada barrido reemplaza al anterior, **no se acumulan ni se interpolan**.

**4 · PIE DEL LIENZO**, tres renglones cortos: «lo más cercano: 0,23 m» **con su matiz pegado**;
el plano de barrido a 15,5 cm; y el origen del dibujo con **el porqué de no dibujar el chasis**.

**5 · FICHA DEL BARRIDO**, tabla densa en mono, cuatro filas, **leída de CADA mensaje y con esa
frase de cabecera**: tamaño de `ranges`, resolución angular, sector y alcance. Debajo, una línea
con **los tamaños medidos —250 · 253 · 254 · 255 · 260 · 270—** para que ver 250 hoy y 270 mañana
**no parezca una avería**.

**6 · CAPA DE SEGURIDAD**, una tarjeta **que solo aparece cuando ha llegado un mensaje**. Con
«invalid source» **es la única pantalla donde se ve desde fuera** lo que ya se sabía.

**7 · SEÑALES DE VIDA DEL NODO**, franja discreta al pie: latido (con su variación entre dos
lecturas), `antiguedad_muestra_s` y `antiguedad_odom_s` **por separado**. **No emite veredicto**:
está para que quien monta pueda leer «el nodo respira y `/odom` llega, lo que no llega es
`/scan`» **sin que la pantalla elija la causa**.

**8 · LO QUE ESTA PANTALLA NO PUEDE DECIR**, caja al final, **siempre presente**.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Antigüedad del último barrido** | `/scan` (marca de llegada al navegador) | mono, **dentro del lienzo**: «hace 84 ms»; por encima de 1 s, «hace 4,2 s» | «no se sabe — no ha llegado ningún barrido desde que se abrió esta pestaña», **y el lienzo no se dibuja** |
| **Barridos recibidos en esta pestaña** | contador de llegadas | entero mono: «312 barridos» | **aquí «0 barridos» SÍ es un dato y se pinta como tal**: el contador existe desde que se montó la vista, así que no es un hueco |
| **Ritmo observado en el navegador** | llegadas de `/scan` | «11,8 Hz observado en el navegador» y al lado «11,9 Hz medido en el robot · 2026-08-04». **El rótulo «observado» no se omite nunca** | con menos de dos barridos: «no se sabe: con uno solo no hay intervalo que medir» |
| **Puntos utilizables** | `/scan.ranges` filtrados | «217 de 260 · 83 %», en el sello | «no se sabe» |
| **Puntos que caen fuera del lienzo** | derivado: r > radio dibujado | «34 puntos más allá de 2,5 m no se dibujan» | «no se sabe» |
| **Tamaño de `ranges`** | `/scan.ranges.length` | entero mono, sin unidad, **leído de CADA mensaje** | «no se sabe» |
| **Resolución angular** | `/scan.angle_increment` | «1,39° por rayo» | «no se sabe» |
| **Sector barrido** | `/scan.angle_min` y `.angle_max` | «de −180,0° a +180,0°» | «no se sabe» |
| **Alcance declarado por el sensor** | `/scan.range_min` y `.range_max` | «0,10 – 8,00 m» | «no se sabe» |
| **Lo más cercano de este barrido** | derivado de `/scan` | «0,23 m» en negrita, **con su matiz en la misma línea** | si no hay ni un punto utilizable: «ningún punto utilizable en este barrido» — **nunca «0 m»** |
| **Tiempo hasta el primer barrido tras pedir el encendido** | medición de esta pantalla (del clic al primer `/scan`) | «primer barrido a los 2 380 ms», con la etiqueta **«medido aquí, en el navegador · sin referencia del robot»** | si el barrido ya estaba encendido al abrir: «no se sabe: no se ha encendido desde esta pantalla» |
| **Respuesta de `/start_scan`** | el servicio | «/start_scan respondió a los 1,9 s» · referencia 1,4-2,1 s (n=6). **Responde vacío: la palabra «encendido» no aparece** | si rechaza, **el mensaje del error tal cual, sin reinterpretarlo** |
| **Efecto de la capa de seguridad** | `/collision_monitor_state` | insignia + frase; con «invalid source», la frase de que bloquea por falta de barrido y qué hacer | «no se sabe: el monitor solo habla cuando el robot recibe órdenes de movimiento. **Su silencio no es un "todo bien"**» |
| **Polígono o motivo** | `.polygon_name` | mono, **literal y sin traducir** («Precaucion», «invalid source») | «no se sabe» |
| **Latido del nodo** | `/estado_robot.latido` | entero mono + «avanzó +17 desde la lectura anterior, hace 1,0 s»; **nunca una sola lectura suelta** | con una sola lectura: «no se sabe todavía: hace falta una segunda». **Ojo: el topic va TRANSIENT_LOCAL y puede llegar latcheado** |
| **Antigüedad de la última muestra del RVR y de `/odom`** | `/estado_robot` | **las dos por separado**, «hace 0,1 s» cada una; **nunca fundidas en un solo número** | −1,0 o no finito: «no se sabe», **que no es «hace cero segundos»** |
| **Coste de esta pantalla** | constante medida (83 % de 80,7 kB/s) + las dos sin medir | «≈67 kB/s de /scan, medido el 2026-08-01 · /collision_monitor_state y /estado_robot: caudal sin medir» | no aplica: es una constante medida **y va siempre con su fecha**; lo no medido **se nombra, no se estima en 0** |
| **Altura del plano de barrido** | medida del proyecto (2026-07-31) | «15,5 cm del suelo» | no aplica: constante medida, con su fecha |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso** | **Marco del lienzo dibujado y vacío, sin anillos y sin cruz**: el recuadro está, el contenido no. **Nada gira, nada palpita, ningún esqueleto de carga** | «No ha llegado ningún barrido desde que se abrió esta pestaña (hace 3 s). Puede que el barrido esté apagado, que es el estado de reposo normal de los 16 robots» |
| **Barrido apagado — el reposo normal** | Lienzo vacío, el botón «Encender el barrido» destacado, y la tarjeta de la capa de seguridad si ha llegado «invalid source» | «El barrido está apagado **y eso no es una avería**: arranca apagado a propósito en los 16 robots… Sin /scan la capa de seguridad no deja conducir: 0,0 cm medidos contra 9,9 del control» |
| **Llegando — el estado de trabajo** | El dibujo actualizándose **sin efectos**: cada barrido reemplaza al anterior. Sello con antigüedad, recuento y ritmo observado | **Ninguna frase de estado**: el sello con su antigüedad ya lo dice. Al pie, lo permanente: «Este lienzo llega a 2,5 m de los 8,0 que declara el sensor. 34 puntos caen más lejos y no se dibujan» |
| **Congelado — llegó y dejó de llegar (más de 4,2 s)** | **El dibujo NO se borra y NO se congela en silencio**: el lienzo entero baja a ~35 % y **una banda estampada encima** da la antigüedad. El sello pasa a ámbar. **Nunca rojo: no hay ninguna avería probada** | «El último barrido es de hace 12,4 s. La imagen que ves es de entonces.» ⚠️ **Los 4,2 s no se copian de los 3000 ms de `/odom`: son los mismos 50 mensajes perdidos, traducidos con el período de `/scan` (11,9 Hz). El umbral se expresa en barridos perdidos, no en milisegundos** |
| **Se pidió el encendido y no llegó barrido (8 s)** | El botón vuelve a su sitio, aviso ERROR bajo la barra, lienzo vacío. **Los dos tiempos medidos siguen a la vista: se ve que el servicio respondió y el efecto no llegó** | «/start_scan respondió a los 1,9 s y no llegó ningún barrido real en 8 s. El robot no tiene por qué estar averiado… Con el puerto USB muerto este servicio responde igual» |
| **No llego al robot** | El lienzo queda con su última imagen **atenuada y sellada**. La cabecera ya marca el enlace; **aquí no se repite el veredicto, solo la consecuencia** | «Se perdió la conexión con el robot. La imagen es de hace 12,4 s y no se está actualizando» |
| **Barrido sin un solo punto utilizable** | El lienzo con sus anillos y su cruz, **y ni un punto**. El recuento: «0 de 260» | «Llegó el barrido y ninguna de sus 260 lecturas es utilizable… Un rayo que no vuelve es un rayo que no encontró nada en 8 m, así que esto puede ser una sala grande y despejada. **No es un 0 m: es que no hay medida**» |
| **No construido — el mapa** | Casilla al pie, con borde discontinuo, **texto y nada más. Sin previsualización, sin imagen de ejemplo, sin «próximamente»** | «El mapa (/map) no está construido. Está autorizado por el robot, pero esta web no ha leído su definición de mensaje, y además exige AMCL o SLAM corriendo… Tres cosas, en ese orden» |

**Copia literal.**

```
Lo que el robot ve — barrido del LIDAR en el marco del robot · arriba es «adelante»

Esta pantalla cuesta ancho de banda, y es la única. /scan es el 83 % del tráfico de un
robot: ~67 kB/s de los 80,7 medidos el 2026-08-01. Dieciséis pestañas de LIDAR abiertas a la
vez son ~8,6 Mbit/s solo de barrido, sobre la única AP del aula. Hay además dos
suscripciones más —/collision_monitor_state y /estado_robot— cuyo caudal NADIE ha medido: no
valen cero, es que no se sabe.

Las tres suscripciones se cierran solas al salir de esta pestaña. El barrido NO: sale de
aquí encendido y el X2 se queda girando a 11,8 Hz hasta que alguien lo apague. Ese botón es
tuyo, y está aquí al lado.

Esta pantalla no sabe cuántas más están abiertas contra este robot: rosbridge no lo dice, y
no hay forma de preguntárselo. El coste que ves es el tuyo.

No se puede pedir menos ritmo. El cliente de esta web no acepta el campo throttle_rate a
propósito, y aunque lo aceptara no serviría: rosbridge comparte una sola suscripción por
topic y se queda con el mínimo entre todos los clientes, así que gana el más rápido y su
ritmo se le impone a todos. Sirve para bajar tu coste cuando eres el único; no para
protegerte de los demás.

Encender el barrido · esperando un barrido de verdad…
Espera a que llegue un /scan real, no a que el servicio responda: con el puerto USB del
LIDAR muerto, /start_scan responde igual y no llega ni un barrido.

Apagar el barrido. No lo para del todo: el X2 baja de 11,8 a 2,7 Hz, que es su reposo.
Pararlo entero exigiría cortarle los 5 V, y la Raspberry Pi no puede. Y el servicio responde
vacío: que no llegue ni un bit no confirma nada — lo que se ve es que /scan deja de llegar.

El sello de arriba a la izquierda va dentro del dibujo a propósito: un barrido congelado se
ve exactamente igual que uno vivo, y ese fallo está medido (el nodo vivo, el servicio
contestando, /odom a 16,58 Hz y ni un barrido).

Los puntos que faltan no son obstáculos ausentes: entre el 83 y el 89 % de las lecturas son
válidas y el resto llegan como Infinity o NaN. Depende de la habitación, no del sensor.
Pintar un hueco como 0 dibujaría un obstáculo pegado al robot que no existe.

Un objeto fino de 5 cm da 2-3 puntos a 0,68 m, así que en un barrido suelto puede
desaparecer. Esto sirve para orientarse, no para decidir por dónde se pasa.

El plano de barrido va a 15,5 cm del suelo: zócalos, cables y cajas bajas no aparecen aquí —
y tampoco los ve la capa de seguridad. «Despejado a ras de suelo» no basta.

Este lienzo llega a 2,5 m; el sensor declara 8,0. Lo que cae más lejos no se dibuja, y
arriba dice cuántos puntos son. Los anillos son tres —0,5, 1 y 2 m— porque dieciséis no se
leen.

El origen del dibujo es el centro del robot. El LIDAR está 0,5 cm por detrás (medido con
cinta), y eso ya está aplicado a cada punto: a esta escala es menos de un píxel. El chasis
no se dibuja a escala porque su largo tiene un conflicto abierto —18,2 cm contra 19,0, las
dos medidas con cinta— y dibujarlo sería elegir una.
```

**Prohibido aquí.**

- **Dejar el último dibujo en pantalla sin su antigüedad encima**, o **borrarlo en silencio** al
  perder el enlace. Las dos son la misma mentira por lados opuestos.
- **Pintar un hueco (Infinity o NaN) como 0**, o escribir «0,00 m» en «lo más cercano».
- **Fijar `ranges.length`, `angle_increment`, el sector o el alcance como constantes.**
- Mandar el campo `qos` o `throttle_rate` en el `subscribe`.
- Decir que el barrido está encendido porque `/start_scan` respondió, o que el paso está libre
  porque la distancia mínima es grande.
- **Llamar a `/stop_scan` automáticamente al salir de la pestaña**: el LIDAR es del robot y puede
  estarlo usando otra persona o un guion de un alumno. **Lo que sí es obligatorio es que la
  suscripción muera al desmontar.**
- **Dibujar el robot a escala**, anillos cada 0,5 m hasta los 8 m, **estelas, interpolación o
  animación de llegada**: a ~11,9 Hz eso es un estroboscopio.
- **Inventar un contador de pestañas abiertas** contra este robot.

**🎨 Prompt para Stitch — LIDAR**

```
Pantalla de visualización del barrido de un LIDAR, en español, oscura. Una sola columna.

Fondo: pozo #07080D con los dos orbes fijos. Arriba, la cabecera del marco con su banda de
parada.

De arriba abajo:
1. Banda fija de coste, nivel NOTA, con tres párrafos densos sobre el ancho de banda.
2. Barra de mando con dos botones: «Encender el barrido» y «Apagar el barrido». A su derecha,
   en Geist Mono pequeño, DOS tiempos separados: «/start_scan respondió a los 1,9 s» y
   «primer barrido a los 2,4 s», cada uno con su nota debajo.
3. UN LIENZO CUADRADO de 560 px, centrado, con borde de 1 px. Dentro: fondo del pozo, TRES
   anillos concéntricos finos etiquetados 0,5 m / 1 m / 2 m en el eje vertical; en el centro
   una cruz de 9 px con una flecha corta hacia arriba; y unos 217 puntos en cian #22D3EE
   dibujados como cuadrados de 3 px, sin degradado y sin estela, formando el contorno de una
   habitación. En la esquina SUPERIOR IZQUIERDA, DENTRO del lienzo, un sello en Geist Mono
   con tres líneas: «hace 84 ms», «217 de 260 puntos» y «11,8 Hz observado en el navegador ·
   11,9 Hz medido en el robot».
4. Tres renglones cortos al pie del lienzo.
5. Tabla densa en mono de cuatro filas con la ficha del barrido, y debajo una línea con los
   seis tamaños medidos.
6. Tarjeta de la capa de seguridad con el polígono en mono y sin traducir.
7. Franja discreta con tres datos del nodo, POR SEPARADO.
8. Caja final «Lo que esta pantalla no puede decir».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: el robot a escala en el centro, anillos cada 0,5 m hasta 8 m, estelas de barridos
anteriores, degradados en los puntos, ningún radar que barra en círculo, ninguna animación.

Aplica además la sección §8 entera.
```

---

### 5.9 · Diagnóstico — `/robot/[id]/diagnostico`

**Trabajo.** Decir **qué llega, hace cuánto y qué no llega**; y **declarar por escrito lo que esta
interfaz NO puede saber**. 🔴 **Deja de ser «la pantalla fea a propósito» y pasa a ser seis
superficies reales** — ver §6, tensión 1.

**Quién la usa.** Quien monta y depura la flota. El profesor no la abre y el alumno tampoco.

**Primera lectura.** La **LÍNEA DEL ENLACE**, entera y a tamaño de titular: **la URL exacta del
socket**, una sola palabra de veredicto y —cuando el socket todavía no ha abierto— **la cuenta del
intento en curso avanzando contra los 10 s**. Va primero por dos razones medidas:

1. **todos los números de abajo son basura si el socket no es el que crees**: `rvr-01.local`
   resolvía a cuatro direcciones y dos se colgaban sin dar error, así que **la URL escrita es el
   primer dato que hay que confirmar con el ojo**;
2. **un WebSocket que no abre NO da ni `onerror` ni `onclose`** (medido: 12 s de silencio absoluto
   contra un robot sano), así que si la página no pinta el intento como una cuenta que avanza,
   **el fallo más caro de esta pantalla es invisible**.

Lo segundo que busca el ojo es **la columna «último hace», no la de Hz**: el veredicto se decide
por antigüedad y **los Hz son para mirar**.

**Composición.** Una columna, densa, mono para todo número medido, rejilla de 1 px, **sin sombras
ni degradados**. Seis superficies, y el orden es el de un diagnóstico real: **primero por dónde
hablo, luego qué llega, luego qué pasó, luego qué puedo mandar, luego qué estoy autorizado a pedir
y cuánto cuesta, y al final qué no sé.**

**1 · ENLACE.** URL completa en mono **sin recortar**; insignia del veredicto; «WebSocket
abierto/cerrado» con la nota de que **se muestrea cada 500 ms y puede ir 0,5 s por detrás AL
ABRIR** (no al cerrar: ahí sí hay evento). Si el socket está conectando, **una barra de progreso
DETERMINADA de 0 a 10 s con su cifra** («4,2 s de 10 s»), **que termina y no se repite**. Debajo:
cierres vistos y **el RANGO** de la espera del próximo intento. Cierra el párrafo de que
**JavaScript no puede enumerar ni elegir las direcciones que resolvió el nombre — no hay API**.

**2 · LLEGADAS POR TOPIC.** Tabla de cinco columnas: `topic · mensajes · último hace · observado
aquí · medido en el robot`. **Cada celda de ritmo lleva la microetiqueta PEGADA** («observado en
el navegador» / «medido en el robot, 2026-07-31»), **nunca en una nota al pie**. Debajo, dos
frases fijas: la conclusión honesta de una diferencia, y **que el veredicto no sale de esta
tabla**.

**3 · CRONOLOGÍA.** Lista de **longitud fija (40 líneas)**, la más nueva arriba, **SIN
auto-desplazamiento y sin crecer sin tope**; cuando se cae una línea por el fondo, **un contador
dice cuántas se han descartado**. Entran: abrió · cerró · reintento · **TODOS** los avisos —no
solo el último— · cada llamada a servicio con su número y su motivo real · cada publicación
rechazada · cada pulsación de parada · **cada flanco `false→true` de la bandera, en su propia
línea**. Al pie, la nota del reloj: **las marcas son del navegador y `Date.now()` no es monótono**.

**4 · SERVICIOS.** Los ocho, en tabla, cada uno con su confirmación (`NINGUNA` /
`SOLO_QUE_NO_LANZO`) y **el texto íntegro, sin recortar ni esconder tras un desplegable**. Fila
propia para `undercarriage_white` (`led_id 10`). Cierra la nota de que **el tipo no tiene un
tercer valor a propósito**.

**5 · CONTRATO Y LO QUE CUESTA.** Los cuatro tamaños leídos al pintar (**13 · 3 · 8 · 1**), la
fecha y **la RAMA** de la última comparación **como constante escrita a mano y marcada como tal**,
la excepción de las ACCIONES, y el párrafo de **la denegación silenciosa**. Debajo, el caudal:
kB/s por topic, total ×1 y ×16, **y aparte —sin sumar— los topics sin caudal medido**.

**6 · LO QUE NO SE PUEDE DECIR, CORREGIDA.** Las cinco entradas **con su marca: tres VIGENTES y
dos LEVANTADAS**, y **las levantadas se dejan escritas con lo que las levantó al lado**. Termina
con **la tabla de `/estado_robot` campo a campo: seis filas, cinco con «NO VERIFICADO» y una sola
con «MEDIDO»**.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **URL del socket** | `urlDeRobot()` sobre el destino, con el override si lo hay | mono, **entera y sin recortar**. Al lado, «por nombre» o «IP escrita a mano» | no ocurre: si el segmento no nombra un robot **la ruta ya devolvió 404** |
| **Estado del socket** | `conectado`, muestreado cada 500 ms | «abierto» / «cerrado», mono, **con la nota de que se muestrea** | no hay hueco posible, **pero se declara el retraso**: hasta 0,5 s por detrás **al ABRIR** |
| **Intento de conexión en curso** | reloj local contra `PLAZO_CONEXION_MS` (10 s) | **progreso DETERMINADO con su cifra**: «4,2 s de 10 s». **Termina y no se reinicia solo** | con el socket abierto o cerrado del todo, **desaparece el bloque entero**: «no hay ningún intento en curso» |
| **Cierres vistos y espera del próximo intento** | cuenta local + la fórmula de espera creciente | «3 cierres vistos por esta pestaña · próximo intento entre 0,8 y 1,2 s (1 s doblando hasta 30 s, ±20 %)» | «la espera real la sortea el transporte y no la publica»: **aquí va el RANGO, nunca un valor** |
| **Veredicto del enlace** | `evaluarSalud()` sobre `msDesdeUltimo('/odom')`, umbral 3 s | insignia de un tono: neutro (no llego) · verde (en línea) · ámbar (sin datos). **Nunca rojo** | SIN_DATOS **lista sus tres causas SIN elegir**; nunca «averiado» |
| **Mensajes contados, por topic** | contador acumulado | entero, tabular, alineado a la derecha | **0 aquí SÍ es un dato** («esta pestaña ha contado cero desde que se abrió») y **se acompaña de la fecha de montaje** para que no se lea como «el robot manda cero» |
| **Último hace, por topic** | `msDesdeUltimo(topic)` | «612 ms» y a partir del segundo «4,3 s» | `null` → raya `—` con el título «no ha llegado ninguno», **pintado distinto de «0 ms»**. **Es la distinción que manda en esta tabla** |
| **Ritmo observado en el navegador** | llegadas | «16,40 Hz» en mono **con la microetiqueta «observado en el navegador» pegada debajo de la cifra** | con menos de dos llegadas, o con intervalo no positivo (**`Date.now()` no es monótono**), «no se sabe» — **NUNCA 0 Hz** |
| **Ritmo medido en el robot** | tabla de referencias (`/odom` 16,53 · `/encoders` 16,57 · `/motor_status` 1 · `/battery_state` 1/30) | «16,53 Hz» atenuado, **con su fecha de medida al lado** | `undefined` → **«nadie lo ha medido»**. **No se estima ni se rellena con el observado.** `/imu` no está a propósito: su ritmo dispersa un ±11 % |
| **Línea de cronología** | eventos locales de esta pestaña | hora local `hh:mm:ss` · etiqueta del tipo · **texto íntegro** en una línea que puede envolver | primer uso: «no ha pasado nada desde que se abrió esta pestaña, a las 22:03:11». **No se pinta ninguna línea de ejemplo** |
| **Avisos del cliente** | todos, acumulados | línea con nivel y **el mensaje completo del transporte** | ninguno todavía → no se pinta el bloque. 🔴 **Hoy el último aviso pisa a los anteriores; aquí se guardan todos, porque el que importa suele ser el primero** |
| **Llamada a servicio** | la promesa: resuelta, rechazada con el motivo **REAL** de rosbridge, o por el plazo local | «nº 3 de esta pestaña · /start_scan · el servicio falló: …» | **el id que viaja NO se puede enseñar**: la capa lo numera por dentro y no lo devuelve. **Se pinta el nº de llamada de esta pestaña y se dice que no es el id del cable** |
| **Motivo de un servicio sin respuesta** | plazo local = 5 s + 2 s de margen | el texto literal: «sin respuesta en 7 s. Puede estar denegado por la lista blanca (**rosbridge deniega en silencio**) o el robot puede estar caído» | **las dos causas se dan JUNTAS y sin elegir**: desde el navegador son indistinguibles, y el margen de 2 s existe **para que el motivo real gane la carrera cuando lo haya** |
| **Publicación rechazada** | la excepción de `publicar()` sin enlace | «sin conexión con el robot: «/emergency_stop» NO se ha enviado», en rojo y con su hora | si no ha habido ninguna, **la fila no existe**. **No se pinta «0 rechazos»** |
| **Pulsación de parada / bandera** | el publish (local) y `/estado_robot.parada_emergencia` (del robot), **en DOS líneas distintas** | «22:14:07 se publicó en /emergency_stop — el mensaje salió por el WebSocket» y «22:14:08 llegó parada_emergencia = true» | si el topic no llega, la segunda línea dice «no se sabe si la bandera se puso», **nunca «no está puesta»**. **Y NO se resta una hora de la otra** |
| **Confirmación de cada servicio** | el contrato | tabla de 8 filas: nombre · `NINGUNA` o `SOLO_QUE_NO_LANZO` · el texto íntegro | no aplica: es un hecho del contrato. **Ninguna fila puede decir «confirma»: el tipo no tiene ese valor** |
| **Contrato vigente** | los cuatro tamaños, leídos al pintar | «13 de lectura · 3 de escritura · 8 servicios · 1 acción», con las listas desplegadas debajo | no aplica: se lee del fichero, **no del robot**. **Y por eso NO prueba que el robot autorice lo mismo** |
| **Última comparación con el robot** | **constante escrita a mano** (el navegador no puede ejecutarla), con fecha, rama y veredicto | «2026-08-04 · rama ros2 · 13/3/8 coinciden, TIPOS 4 de 4, ACCIONES fuera de la comparación» | si no se ha tocado en más de una semana, **la fecha se pinta ámbar** con «esto es lo último que alguien comprobó, no lo que hay hoy». Y el código 2 del comprobador **se escribe «no se comparó nada», jamás como aprobado** |
| **Lo que cuesta esta pestaña** | tabla de caudales medidos | kB/s por topic, total de este robot y total ×16, en mono | los topics **sin caudal medido van APARTE**, marcados «nadie lo ha medido», y **NO entran en la suma** |
| **`/estado_robot`, campo a campo** | los seis campos validados | seis filas: valor · «llega/no llega» (lo puede ver esta pestaña) · **marca MEDIDO o NO VERIFICADO** (lo dice el robot) | si el mensaje no llega o le falta un esencial, las seis filas dicen «no se sabe» — **un driver anterior al 2026-08-04, que no es «todo bien»**. Las antigüedades a −1,0 se pintan «nunca se ha sabido nada», **nunca 0 s** |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso** | La URL y la cuenta del intento avanzando. La tabla con sus cinco filas presentes, «mensajes 0» y «último hace —». Cronología vacía con su hora de apertura | «Esta pestaña se abrió a las 22:03:11 y todavía no ha llegado nada. **Cero mensajes contados aquí no significa que el robot mande cero**: significa que aún no ha llegado ninguno» |
| **No llego · el socket no abre** | Cuenta de 0 a 10 s; al vencer, el aviso del transporte en la cronología y el número de cierres vistos | «No se abrió el WebSocket en 10 s. **Un socket colgado no da error**: puede que el nombre resuelva a una dirección inalcanzable desde esta red. **JavaScript no puede saber a cuáles resolvió**» |
| **Sin datos · el socket va y `/odom` calla** | Insignia **ÁMBAR, nunca roja**. Las tres causas listadas sin elegir. La tabla enseña «último hace» creciendo | «El WebSocket está abierto y hace más de 3 s que no llega /odom. Esto no es una avería y el navegador no puede saber cuál de las tres causas es» |
| **En línea · llega todo** | Insignia verde, las cinco filas con su antigüedad por debajo del segundo y **los dos ritmos lado a lado** | «Llega /odom desde hace menos de 3 s. Ese umbral es el mismo que usa el detector de silencio del driver, **para que cliente y robot coincidan en cuándo algo va mal**» |
| **Un topic mudo con el enlace bien** | `/odom` fresco y otra fila con «último hace» creciendo o en `—`, **sin que cambie el veredicto del enlace** | «El enlace va y este topic no llega. Puede estar denegado por la lista blanca o puede que nadie lo publique: **rosbridge deniega en silencio, así que desde aquí las dos cosas se ven exactamente igual**» |
| **`/estado_robot` no llega** | Las seis filas en raya, **con la marca de cada campo intacta al lado** | «Este robot no publica /estado_robot: es un driver anterior al 2026-08-04. No se sabe si la parada está puesta, **y eso no es "no está puesta"**» |
| **Parada · enviada, y luego vista** | **Dos líneas separadas** en la cronología, con sus horas, y la fila de la bandera cambiando a `true` | «22:14:07 el mensaje salió por el WebSocket. 22:14:08 la bandera llegó en true.» Y si la segunda no llega: «el mensaje salió; no se sabe si la bandera se puso» |
| **No construido · lo que esta pantalla nunca va a tener** | **Dos casillas nombradas**, con el nombre de lo que las bloquea, **sin sitio reservado para un futuro número** | «Cuánto tarda una orden en llegar a los motores: no se puede medir desde aquí, y no se estima. Por qué rosbridge denegó algo: no existe. **Ninguna de las dos está pendiente de escribirse; están cerradas**» |

**Copia literal.**

```
Diagnóstico — qué llega, hace cuánto, y qué no puede saber esta pantalla.

ws://rvr-01.local:9090. El nombre lo resuelve el sistema, y JavaScript no puede enumerar las
direcciones que devolvió ni elegir una: no hay API. Si el nombre resuelve a una dirección
inalcanzable, el socket no da error — se cuelga, y esa es la misma firma que un robot
apagado.

Intento en curso: 4,2 s de los 10 s del plazo. Al vencer, el cliente cierra el socket a mano
para que exista un cierre; sin ese cierre la reconexión con espera creciente no llegaría ni
a arrancar.

Cierres que ha visto esta pestaña: 3. La espera del siguiente intento la sortea el
transporte —1 s doblando hasta 30 s, con ±20 % de ruido— y no la publica: aquí va el rango,
no el valor.

16,40 Hz observado en el navegador · 16,53 Hz medido en el robot el 2026-07-31. Si el
observado sale por debajo, lo que dice es que algo del camino pierde mensajes, no que el
robot publique despacio. Con menos de dos llegadas pone «no se sabe», nunca 0 Hz.

El estado del enlace no sale de esta tabla. Se decide por la antigüedad de la última
llegada, con el mismo umbral de 3 s que usa el detector de silencio del driver. Una
comprobación de «más de 10 Hz» de este proyecto pasó midiendo 11,3 Hz sobre un robot que iba
a 16,5.

Las horas son del reloj del navegador, y Date.now() no es monótono: un ajuste de hora puede
dejar dos líneas en orden imposible. Por eso aquí no se resta nada, ni siquiera cuando
restar parecería útil.

22:14:07 se publicó en /emergency_stop — el mensaje salió por el WebSocket. · 22:14:08 llegó
parada_emergencia = true. Se dejan separadas a propósito: /estado_robot va a 1 Hz, así que
el hueco entre las dos es sobre todo el periodo del topic, y restarlas daría una cifra que
parece latencia y no lo es.

Ninguno de los ocho servicios confirma un efecto físico, y el tipo no tiene un tercer valor
a propósito. Cuatro responden vacío: no llega ni un bit. Los otros cuatro dicen que la
corrutina del SDK no lanzó. undercarriage_white responde así y deja el LED apagado — medido
con el sensor de luz como testigo.

13 topics de lectura, 3 de escritura, 8 servicios y 1 acción, leídos de contrato.ts al
pintar esta página. La última comparación contra robot.launch.py se pasó el 2026-08-04 sobre
la rama ros2: el navegador no puede ejecutar npm run contrato, así que esa fecha la escribe
una persona y envejece sola.

ACCIONES (/navigate_to_pose) no se compara con el robot: allí ese glob va escrito dentro de
la llamada del launch, sin una constante que extraer. El visto bueno de arriba es de tres
listas, no de cuatro.

rosbridge deniega sin decirlo: registra un aviso en el log del robot y no manda nada por el
socket. Un topic denegado por la lista blanca y un robot caído se ven igual desde aquí —
silencio. Esta pantalla no elige entre los dos.

Pedir menos mensajes no protege de nadie: rosbridge mantiene una suscripción por topic y se
queda con el throttle_rate más bajo de todos los clientes, así que gana el más rápido. Baja
tu propio coste cuando eres el único; no te defiende de la pestaña que alguien acaba de
abrir sobre este mismo robot.

Dos de estas cinco entradas ya no son ciertas, y se corrigen aquí en vez de borrarlas. La
bandera de parada la publica el robot desde el 2026-08-04 y su flanco se presenció con el
robot en marcha. El significado de cada valor del collision_monitor se leyó de su .msg real
el mismo día — lo que sigue sin medirse es su caudal, y por eso no entra en ninguna suma.
```

**Prohibido aquí.**

- **Ningún pulso, latido ni parpadeo infinito** — tampoco en «reintentando» ni en el punto de la
  insignia. **Lo único que se mueve es la cuenta del plazo de conexión**, que es progreso
  determinado, tiene final y no se repite sola.
- **Ninguna cifra de latencia**, y eso incluye **restar la hora de la pulsación de la hora del
  flanco de parada**.
- **Ningún 0 Hz, ningún «0 ms» y ninguna casilla vacía** donde no hay medida.
- **La cronología no se auto-desplaza, no late y no crece sin tope.** Cuando cae una línea, **se
  dice cuántas se han descartado**: un truncado silencioso es un dato perdido que parece que nunca
  existió.
- **No se muestra solo el último aviso.**
- No se dice «denegado» ni «el robot está caído» cuando un topic calla.
- **No se suman caudales sin medir.**
- Esta pantalla **no se suscribe a `/scan`** ni manda campo `qos` en ningún `subscribe`.

**🎨 Prompt para Stitch — Diagnóstico**

```
Pantalla de diagnóstico técnico de un robot, en español, oscura, MUY densa. Una sola
columna, rejilla de 1 px, monoespaciada para todo número medido, SIN sombras y SIN degradados.

Fondo: pozo #07080D con los dos orbes fijos, pero mucho más contenido que en las demás
pantallas.

Seis superficies, de arriba abajo:
1. ENLACE: la URL «ws://rvr-01.local:9090» a tamaño de titular en Geist Mono, sin recortar,
   con una insignia de veredicto al lado y el texto «WebSocket abierto». Debajo, una BARRA DE
   PROGRESO DETERMINADA de 0 a 10 s con la cifra «4,2 s de 10 s» — determinada, con final, no
   indeterminada. Debajo, dos párrafos densos.
2. LLEGADAS POR TOPIC: tabla de cinco columnas (topic · mensajes · último hace · observado
   aquí · medido en el robot) con cinco filas. En la columna «observado aquí», la cifra
   «16,40 Hz» con la microetiqueta «observado en el navegador» PEGADA debajo en versalitas de
   10 px. Una fila con «último hace» en raya «—». Debajo, dos frases fijas.
3. CRONOLOGÍA: lista de longitud fija de unas 12 líneas visibles, la más nueva arriba, cada
   una con hora hh:mm:ss en mono, una etiqueta de tipo y el texto íntegro. Al pie, un contador
   de líneas descartadas y una nota sobre el reloj.
4. SERVICIOS: tabla de ocho filas con nombre, un valor de confirmación y el texto íntegro sin
   recortar.
5. CONTRATO Y COSTE: cuatro cifras, una fecha con rama, tres párrafos, y una tabla de caudal
   por topic con dos filas APARTE marcadas «nadie lo ha medido».
6. LO QUE NO SE PUEDE DECIR: cinco entradas marcadas VIGENTE o LEVANTADA, y una tabla final de
   seis filas donde cinco dicen «NO VERIFICADO» y una dice «MEDIDO».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: barras indeterminadas, spinners, puntos que parpadeen, ninguna cifra de latencia,
ningún 0 Hz, ningún gráfico.

Aplica además la sección §8 entera.
```

---

### 5.10 · Cuaderno de medidas — `/cuaderno`

**Trabajo.** Guardar **el número que la persona midió con la cinta o el transportador** junto al
que **imprimió el programa**, y poner **tres o cinco corridas de lo mismo una al lado de otra**
para ver **la DISPERSIÓN**.

**Quién la usa.** El alumno del taller presencial. **Es el único sitio donde cae hoy lo que la
guía llama «tu medida gana».**

**Primera lectura.** **El hueco.** Al empezar no hay ni una fila, y eso se ve: una tabla con sus
cabeceras y **nada debajo**, con una frase que dice que está vacía **a propósito**. Lo segundo es
el botón de añadir una medida. **Ni una fila de ejemplo**, porque una fila de ejemplo en el único
sitio donde el dato lo escribe una persona es exactamente la mentira que esta plataforma existe
para no cometer.

**Composición.**

1. **Cabecera** con el titular y una línea: qué es esto y **dónde se guarda**.
2. **Aviso permanente de almacenamiento**, en neutro: *guardado en ESTE navegador*. No hay cuenta,
   no hay servidor, **y cerrar el navegador puede perderlo**.
3. **Botón «Anotar una medida»** y, debajo, **la tabla**. Por fila: robot · guion · las constantes
   con las que corrió · instante · **lo que imprimió el programa** · **lo que midió la persona** ·
   unidad · instrumento (cinta / transportador) · nota libre · **cómo terminó** (fin normal,
   Ctrl-C, señal, código de salida).
4. **Vista de corridas**: las del mismo guion **en columnas contiguas**, para que la dispersión se
   vea de un vistazo. **Sin ninguna estadística agregada.**
5. **Recordatorio de recolocar el robot entre corridas**, permanente.
6. **Pie**: esta pantalla **no abre ningún WebSocket** y **no vive bajo `/robot/[id]`**, así que
   sobrevive a cambiar de robot **y funciona hoy**, sin el agente de sesión.

🔴 **Todo lo tecleado se marca como ESCRITO POR UNA PERSONA** y **no comparte nunca superficie ni
tipografía con la telemetría**: es el único número de la plataforma que **no viene del robot**. Va
en la tipografía de texto, sobre una superficie con un tratamiento propio, **nunca en la mono de
las medidas del robot**.

**Campos.**

| Campo | Fuente | Formato | Si no hay dato |
|---|---|---|---|
| **Robot** | elegido por la persona | `rvr-NN`, Geist | «sin robot anotado». **No se rellena con el último visitado** |
| **Guion** | elegido de la lista del repositorio | nombre de fichero en mono | «sin guion anotado» |
| **Constantes con las que corrió** | tecleado | texto libre corto, **marcado como escrito a mano** | «no anotadas». **No se deducen del nombre del fichero** |
| **Instante** | reloj del navegador al guardar | fecha y hora local | siempre hay. **Y se dice que es el reloj del navegador**, no el del robot |
| **Lo que imprimió el programa** | **tecleado por la persona**, copiado de su terminal | mono, **marcado como transcrito a mano** | «no anotado». 🔴 **La plataforma no lo lee del robot: no hay agente de sesión** |
| **Lo que midió la persona** | tecleado | cifra en la tipografía de texto, **nunca en la mono de la telemetría** | «no medido». **Un hueco aquí es la mitad del valor de la fila y se ve** |
| **Unidad** | elegida | cm · m · grados | «sin unidad»: **una cifra sin unidad no se guarda como número** |
| **Instrumento** | elegido | «cinta» / «transportador» / otro, texto | «no anotado» |
| **Cómo terminó** | tecleado | fin normal · Ctrl-C · señal · código de salida | «no anotado» |
| **Nota libre** | tecleado | texto | vacío, y se ve vacío |

**Estados.**

| Estado | Qué se ve | Qué dice |
|---|---|---|
| **Primer uso · vacío** | La tabla con sus cabeceras y **nada debajo**. El botón de anotar destacado. **Ni una fila de ejemplo** | «Todavía no has anotado ninguna medida. Esta tabla está vacía a propósito: aquí solo entra lo que mides tú» |
| **Una sola corrida** | Una fila. **Ninguna estadística**, ninguna media, ningún «±» | «Una sola corrida no dice nada de la dispersión. La lección de la práctica 04 es justamente esa: en lazo cerrado la media es la misma y la dispersión es 4,5 veces menor» |
| **Tres o cinco corridas del mismo guion** | Las corridas **en columnas contiguas**, con cómo terminó cada una. **La dispersión se ve, no se resume** | «Aquí no se calcula ninguna media ni ninguna desviación: con n=2 o n=3 una cifra agregada da una falsa sensación de precisión. Míralas una al lado de otra» |
| **Sin recolocar entre corridas** | El recordatorio permanente, siempre visible | «Recoloca el robot entre corridas. Sin recolocar, "N repeticiones" es un barrido por posiciones distintas: se midieron **94 cm de deriva acumulada en 12 corridas**» |

**Copia literal.**

```
Cuaderno de medidas

Aquí va el número que mediste tú con la cinta o el transportador, al lado del que imprimió
tu programa. Es el único sitio de esta plataforma donde el dato lo escribe una persona, y
por eso se dibuja distinto: no comparte tipografía con la telemetría del robot.

Todavía no has anotado ninguna medida. Esta tabla está vacía a propósito: aquí solo entra lo
que mides tú.

Escrito por una persona · nadie lo comprueba.

Se guarda en ESTE navegador. No hay cuenta y no hay servidor: si cierras el navegador o
borras sus datos, esto se pierde. Cópialo a papel o a tu cuaderno antes de acabar la sesión.

Aquí no se calcula ninguna media ni ninguna desviación. Con dos o tres corridas, una cifra
agregada da una falsa sensación de precisión: la lección de la práctica 04 es la DISPERSIÓN
—misma media, 4,5 veces menos dispersión en lazo cerrado— y esa se ve poniendo las corridas
una al lado de otra, no resumiéndolas.

Recoloca el robot entre corridas. Sin recolocar, «N repeticiones» es un barrido por
posiciones distintas: se midieron 94 cm de deriva acumulada en 12 corridas, unos 8 cm cada
una, y con eso el 21 % de las corridas fallaba con errores de hasta 56 cm.

Ninguno de los guiones del curso se ha ejecutado nunca contra el robot moviéndose. Si tu
medida no coincide con lo que dice la guía, tu medida gana: anótala aquí y díselo al
profesor.

Esta pantalla no habla con ningún robot y no abre ningún WebSocket. Funciona hoy, con o sin
terminal, y sobrevive a que cambies de robot.
```

**Prohibido aquí.**

- **Ni una fila de ejemplo.** Si no hay medida, **se ve el hueco**.
- **Cero estadística agregada** calculada por la plataforma sobre n=2 o n=3: ni media, ni
  desviación, ni «±», ni barra de error.
- **Ninguna gráfica de tendencia** de las medidas anotadas.
- **Mezclar la tipografía de lo tecleado con la de la telemetría.**
- Abrir un WebSocket, o vivir bajo `/robot/[id]`.
- Prometer que lo guardado está a salvo, o sincronizarlo con nada.

**🎨 Prompt para Stitch — Cuaderno de medidas**

```
Pantalla de un cuaderno de laboratorio para anotar medidas hechas a mano, en español,
oscura. NO habla con ningún robot.

Fondo: pozo #07080D con los dos orbes fijos. Sin cabecera de robot: esta pantalla es de nivel
superior, con una barra simple que lleva al muro y a un robot.

De arriba abajo:
1. Titular «Cuaderno de medidas» en degradado, y un párrafo de 52 caracteres de ancho.
2. Un aviso permanente en tono neutro sobre dónde se guarda.
3. Un botón primario «Anotar una medida».
4. Una TABLA VACÍA: cabeceras visibles (robot, guion, constantes, instante, lo que imprimió
   el programa, lo que mediste tú, unidad, instrumento, cómo terminó, nota) y NADA debajo,
   con una frase centrada en el hueco que dice que está vacía a propósito. NI UNA FILA DE
   EJEMPLO.
5. Debajo, una vista de «corridas del mismo guion» dibujada como tres columnas contiguas,
   también vacías, con una nota de por qué no hay ninguna estadística.
6. Un recordatorio permanente en ámbar sobre recolocar el robot entre corridas.
7. Pie con la frase de que esta pantalla no abre ningún WebSocket.

Tipografía: lo que escribe una persona va en Geist (la de texto) sobre una superficie con un
tratamiento propio, NUNCA en Geist Mono, que en esta plataforma está reservada a las medidas
que vienen del robot. Cada campo tecleado lleva la marca «escrito por una persona».

Textos: usa EXACTAMENTE los del bloque «Copia literal» de esta pantalla.

NO dibujes: filas de ejemplo, medias, desviaciones, barras de error, gráficas de tendencia,
ningún indicador de conexión, ningún dato de telemetría.

Aplica además la sección §8 entera.
```

---

## §6 · Tensiones resueltas — no las reabras

Cada una es un choque real entre dos criterios legítimos. **Está resuelta, y aquí queda la
resolución con su motivo** para que no vuelva a discutirse.

**1 · 🔴 LA DESPROPORCIÓN, y es la contradicción principal.** El terminal es el 90 % de los
90 minutos del alumno; la versión anterior de este documento le dedicaba la sección 7.4 entera a
**lo que no existe** y despachaba el diagnóstico en cuatro líneas («la pantalla fea a propósito»).
Y una pestaña que no existe no puede ser la puerta de entrada.
→ **RESOLUCIÓN:** el Taller **conserva la ruta índice** —su ausencia tiene que doler y su cadena
de bloqueo tiene que estar donde se tropiece con ella— pero **la desproporción se arregla SUBIENDO
el diagnóstico a seis superficies reales, no bajando el terminal**. Y el Taller **deja de ser «una
pantalla de terminal» para ser la lista de requisitos medidos** que el agente tendrá que cumplir:
así **el hueco es un encargo, no un decorado**.

**2 · 🔴 ¿PORTADA O EL MURO COMO ARRANQUE?** Para el profesor la portada es «un clic de más cada
mañana»; para seguridad y datos es **imprescindible**, porque es el único sitio donde se declara
que **no hay autenticación**.
→ **RESOLUCIÓN:** se queda, **pero deja de ser un menú y no es un peaje** —no guarda estado, no
abre sockets, y quien quiera **arranca en `/flota`**—. Y como el aviso de «cualquiera puede mover
cualquier robot» **no puede depender de que alguien pase por la portada**, se repite donde
importa: **en el Taller** (el guion del alumno tiene MÁS autoridad que la web) **y en
Diagnóstico**.

**3 · 🔴 ¿EL PORQUÉ, DETRÁS DE UN CLIC?** El profesor pide la ficha de causa «a un clic»; las
reglas del proyecto **prohíben por escrito esconder el motivo** («esconder el porqué deja el color
sin acción posible»).
→ **RESOLUCIÓN:** no son incompatibles **si el clic AMPLÍA en vez de REVELAR**. Las etiquetas
cortas **están siempre visibles** en la baldosa, en una línea y sin desplegable; la ficha larga se
abre **en la misma pantalla sin navegar**. **Ningún motivo vive SOLO detrás del clic**, y el `▸`
queda **para el contexto de una medida, nunca para su estado**.

**4 · 🔴 `/collision_monitor_state`: PROHIBIDO POR DOS CRITERIOS, MEDIDO POR EL TERCERO.** Se
prohibía porque su caudal no estaba medido; luego se midió: **0,012 kB/s**, y publica **solo
cuando procesa un `cmd_vel_raw`**.
→ **RESOLUCIÓN:** entra en la tabla de caudales y **se usa en Conducir, en «Por qué no obedece» y
en LIDAR**, donde es prácticamente gratis y **cierra la causa más barata de «no obedece»**
(«invalid source» = me falta `/scan`). **Pero NO entra en el muro, y no por coste: no publica
periódicamente, así que su silencio no significa nada y a tres metros se leería como "todo
bien"**. Del enum **solo se conoce un valor**: el resto **se pinta en crudo**.

**5 · ⚠️ EL MURO SE APOYA EN UN MENSAJE NO VERIFICADO, Y EL INVENTARIO DE HUECOS ESTABA RANCIO.**
El `.msg` de `/estado_robot` dice que se escribió sin robot delante; a la vez, **`parada_emergencia`
SÍ está verificada** (flanco presenciado desde los dos lados) mientras la lista de «lo que no se
puede decir» seguía afirmando que «el driver no publica su bandera de parada» — **falso desde el
2026-08-04**, y es literalmente el caso del manual 15.3: **una función de seguridad descrita como
rota estando sana**.
→ **RESOLUCIÓN:** la lista **se corrige en el MISMO commit que este documento**, y **toda pantalla
que lea `/estado_robot` marca CAMPO A CAMPO qué está medido y qué no**. Mientras el resto no se
mida, **el muro sigue usando `/motor_status` a 1 Hz como latido**, porque la alternativa —`/odom`
por dieciséis— son **1,7 Mbit/s**.

**6 · 🔴 EL CORAL NO PUEDE SER A LA VEZ «IR» Y «PARAR».** El muro asigna coral al estado IR; la
parada exige que su color esté **reservado**, porque si dieciséis baldosas salen en coral por
batería baja, **el aula aprende a leer ese color como «batería»**.
→ **RESOLUCIÓN:** **los dos nunca aparecen en la misma pantalla**, porque **el muro no lleva botón
de parada** (§7) y la parada vive en el marco del robot. Además **la parada no se distingue por
color sino por FORMA y SITIO** —ancho completo, 64 px, versalitas, no comparte fila— y **el muro
codifica la urgencia con un canal redundante al color**: el paso del galón.

**7 · ⚠️ QUÉ SOBREVIVE DEL REGISTRO ANTERIOR, Y QUÉ NO.** Al elegir «Órbita + Bloques» se puso en
duda media sección visual. Resolución pieza a pieza, **para que nadie la reabra**:

| Pieza | Veredicto |
|---|---|
| Los **dos orbes** desenfocados a 90 px, fijos | ✅ **Se conservan** en todas las pantallas. Son el fondo, **nunca dentro de algo que se desplace** |
| `backdrop-filter: blur(20px)` **en tarjeta de vidrio** | ✅ **Se conserva** |
| El mismo blur **en una baldosa de BLOQUE** | 🔴 **Se retira.** Un bloque es color a plena saturación, **no vidrio teñido**: el blur le bajaría el contraste justo en la pantalla con criterio «a tres metros» |
| **Entrada escalonada de 60 ms** | ✅ **Se conserva**, en CSS y **solo al montar**. 🔴 **Y NO se dispara al reordenar la rejilla por voltaje**: el muro **no baraja sus fichas** |
| **Titular con degradado** | ✅ **Se conserva**, y **solo** en el titular de pantalla |
| **La barra eléctrica que se DESLIZA entre pestañas** | 🔴 **Descartada.** La lengüeta activa se resuelve con el color del suelo y un filete de 2 px, **sin deslizamiento**: es movimiento que no dice nada y compite con la banda de parada que tiene justo encima |

---

## §7 · Descartado, con su motivo — para que nadie lo reabra

**1 · La cruceta de nueve celdas, reducida a cinco.**
Un robot diferencial solo tiene `linear.x` y `angular.z`: **las cuatro diagonales tendrían que
inventarse una combinación de v y w que nadie ha medido en este robot**. Lo verificado son 0,10 /
0,20 m/s y 0,8 rad/s. **Un mando con más grados de libertad que medidas es superficie de riesgo
gratis.**

**2 · La barra de nivel de batería de 4 px con degradado, y el porcentaje «marcado como que no
decide nada».**
Una barra sin escala **reintroduce exactamente la lectura porcentual que el proyecto prohíbe**
—invita a leer «va por la mitad»— y **no existe ninguna escala 0-100 honesta** entre los 8,29 V
que el firmware llama «100 %» y los 6,5 de crítica. Y **un número que se declara inútil sigue
ocupando el sitio del voltaje**: si no decide, no se pinta.

**3 · Las tres pastillas de caudal en la cabecera del muro, la píldora «N de 16 en línea», y
cualquier topic caro en la vista de flota.**
**El cliente NO mide su propio caudal**: los 80,7 / 13,6 kB/s son medidas **del robot**, así que en
la cabecera serían **un número sin fuente ni antigüedad**. Y **el profesor no hace nada con
«7,7 kB/s»**: el caudal es la restricción que gobierna el diseño, no una decisión de clase — se
muda a Diagnóstico, **con su fecha**. «En línea» solo lo diría `/estado_robot.latido` avanzando,
que está **NO VERIFICADO**, y además **un contador esconde CUÁL de los dieciséis**.
⚠️ Lo que sí queda en la cabecera del muro son **dos** pastillas con el presupuesto **medido** de
lo que ese muro paga, **con la advertencia pegada de que la cifra se queda corta**.

**4 · El botón de parada de emergencia en el muro, y el botón de liberar la parada en cualquier
pantalla.**
**Liberar es un acto presencial ya decidido**: con un objetivo de Nav2 vivo, liberarla hizo que el
robot **arrancara solo** —34,7 cm contra 0,0 con el arreglo—. Y **una parada pulsada por error
sobre un 4×4 mirado a tres metros CREA el trabajo que el muro existe para evitar**: alguien tendrá
que ir a liberarla. **El profesor está en la misma sala.**

**5 · La entrada escalonada aplicada a las dieciséis baldosas como espectáculo, el blur por
baldosa de bloque, y el titular gigante como protagonista del muro.**
El escalonado son **~960 ms hasta ver la última baldosa**: en la pantalla cuyo único trabajo es
decir **quién NO responde**, animar la aparición del estado **retrasa la única información que
da**. Se conserva **porque ocurre una vez y no vuelve**, pero **no se le añade nada**: ni
reacomodo animado, ni escalonado al reordenar. Y **el titular no puede gastar la franja superior
de la proyección en decir «Flota»**, que es lo que el profesor ya sabe: se queda, contenido.

**6 · Cualquier insinuación de identidad**: pantalla de inicio de sesión, «tu robot», «sesión de
rvr-07», contador de conectados, atribución de quién conduce.
**rosbridge 2.7.0 no trae autenticación**, así que la plataforma **no puede saber quién eres ni
cuántos están conectados al mismo robot**. Fingirlo sería peor que no tenerlo, **y además
ocultaría un riesgo real**: dos bucles de 10 Hz publicando `cmd_vel_raw` a la vez producen un
movimiento **que no es el de ninguno de los dos**, y **ninguna pantalla puede detectarlo**. La
portada lo **DECLARA** en vez de simularlo.

**7 · Toda superficie de mapa y navegación**: `/map`, `/amcl_pose`, `/initialpose`,
`/navigate_to_pose`, «ve a la mesa 3», la pose inicial por robot.
Están en la lista blanca y **NO EXISTEN hoy**: `atriz-nav.service` está instalada y **sin
habilitar** (Nav2 cuesta ~58 % de un núcleo y **sale de la batería del RVR**, que ya no cubre una
clase de 2-3 h) y **no hay mapa del aula**. Además el cliente **no tiene soporte de acciones**, y
`/amcl_pose` **no llegaría con el robot quieto**. **Una pantalla que los pintara estaría vacía para
siempre.**

**8 · Cuatro pantallas propuestas que no ganan ruta y se pliegan donde ya viven:** «rumbo y
distancia frontal en vivo» (→ Telemetría y LIDAR), «muro en modo depuración» (→ Diagnóstico),
«sitio en el aula» (→ campo escrito a mano en «Dónde buscar»), y «registro de intentos de parada»
+ «cronología del enlace», **que son el mismo artefacto** (→ una sola cronología en Diagnóstico).
Ninguna llegó a una «imprescindible» ni a dos «importantes», **y las cuatro cabían enteras dentro
de una pantalla que sí entró**. Partirlas habría multiplicado los sitios donde la misma
información se dibuja distinta — **que es exactamente cómo se coló el namespace en el segundo
fallo de la parada de emergencia: por tener dos caminos para lo mismo**.

**9 · Los efectos decorativos de la propuesta original que no sobrevivieron**: la barra eléctrica
deslizante entre pestañas (§6, tensión 7), el vidrio sobre los bloques del muro, y cualquier
*scanline*, dithering o ruido analógico. **Decoración que compite con señal real.**

---

## §8 · 🔴 Lo que esta plataforma NO puede hacer

> **Esta sección se pega en TODOS los prompts, siempre, entera.** Es lo que separa este producto
> de un panel genérico bonito, y **cada línea viene de un fallo real medido en el laboratorio**.

### Prohibiciones de movimiento

- ❌ **Ningún pulso, latido, brillo o giro infinito**, y **en especial no en los indicadores de
  estado**. Un punto que late siempre es indistinguible de un robot que vive siempre — y esta
  pantalla vigila dieciséis que pueden estar mudos.
- ❌ **Nada se anima al llegar un dato.** La telemetría llega a 16,5 veces por segundo: animarla
  sería un **estroboscopio sobre las cifras que alguien está leyendo**.
- ❌ **Ni contadores que suben** de un valor a otro: enseñarían voltajes que el robot nunca
  reportó.
- ❌ **Ni esqueletos de carga, ni barras de progreso indeterminadas, ni spinners.** Simulan un
  progreso que nadie está midiendo. **La única barra permitida en toda la plataforma es la cuenta
  determinada del plazo de conexión**, que va de 0 a 10 s, **tiene final y no se repite**.
- ❌ **Ni cursores de terminal parpadeando** sobre una consola que no existe: es la misma mentira
  con otro disfraz.
- ❌ **Ni reordenaciones animadas ni entradas escalonadas al recibir datos.** El escalonado corre
  **una vez, al montar**.

### Prohibiciones de contenido

- ❌ **Ningún dato de ejemplo, de relleno ni «orgánico».** Si no hay valor, se dice **«no se
  sabe»**, y **tiene que verse distinto de un cero**.
- ❌ **Ningún número sin su antigüedad.** El sondeo térmico va cada 30 s: **una temperatura plana
  puede ser el mismo dato repetido**.
- ❌ **Nunca «LED encendido», «color cambiado», «orden confirmada» ni «efecto confirmado».**
  **Ningún servicio del robot confirma un efecto físico**: uno de ellos devuelve éxito **sin
  encender nada**.
- ❌ **Nunca «robot averiado» por falta de datos.** Un robot cargando es el estado más común del
  laboratorio. Eso es **ámbar**, con **sus causas listadas y sin elegir entre ellas**.
- ❌ **Nunca «la parada no está puesta»** sin el mensaje del robot en la mano. **El silencio no es
  un no**, y esa asimetría es deliberada.
- ❌ **El porcentaje de batería no se pinta en ninguna parte.** Marcó **100 % con la batería a
  8,29 V**, a 1,29 V del umbral de «baja», y además es una **fracción 0-1**. **Manda el voltaje.**
- ❌ **Ninguna cifra de latencia**, ni «tiempo hasta los motores», ni restar dos horas para
  insinuarla. **No está medido.**
- ❌ **Ningún umbral copiado entre topics de ritmos distintos.** Se expresa **en mensajes
  perdidos** y se traduce con el período **de su topic**.
- ❌ **Ningún caudal estimado a ojo sumado a un total.** Lo no medido **se nombra aparte**.

### Prohibiciones de forma

- ❌ Gráficas de tendencia, medidores circulares, *sparklines* y series temporales **haciendo de
  contenido**. **No hay persistencia en ningún sitio.**
- ❌ **Barras de nivel** salvo que exista una escala real y medida. La de batería **no existe**.
- ❌ Texto con degradado **fuera del titular de pantalla**.
- ❌ **Emojis haciendo de iconos**: los iconos se dibujan, con un grosor de trazo único.
- ❌ **Negro puro `#000000`.**
- ❌ **Una pantalla de inicio de sesión**, un avatar, un nombre de usuario o un contador de
  conectados: **no hay control de acceso, y fingirlo sería peor**.
- ❌ **Esconder tras un desplegable** el motivo de un estado, las causas de «no se sabe», o los
  relojes de una ficha. **El motivo ES la acción.**

### Prohibiciones de protocolo (afectan al dibujo, aunque parezcan técnicas)

- ❌ **Publicar en `/cmd_vel`.** Es la **salida** de la capa de seguridad: mover el robot por ahí
  **funciona y salta la seguridad entera sin un solo aviso**.
- ❌ **Mandar el campo `qos` en un `subscribe`.** El **primer** cliente que se suscribe a un topic
  **impone su QoS a todos los demás**: una pestaña pidiendo RELIABLE sobre `/odom` deja a **0,00 Hz
  a todas las demás de ese robot**, sin error y sin aviso.
- ❌ **Apoyarse en `throttle_rate` como si protegiera.** rosbridge se queda con **el mínimo entre
  todos los clientes**: **gana el más rápido, para todos**.
- ❌ **Suscribirse a `/scan` fuera de la pestaña LIDAR** (y de la confirmación puntual del arranque
  en Conducir). Es el **83 %** del tráfico de un robot.
- ❌ **Suscribirse a cualquier topic sin caudal medido** desde el muro.

---

## §9 · Índice de prompts

Se pega **§1–§4 una vez**, después **uno** de estos, y **siempre §8 al final**.

| Pantalla | Dónde está su prompt |
|---|---|
| Portada | §5.1, al final |
| Muro de flota | §5.2, al final |
| Marco del robot | §5.3, al final |
| Taller (NO CONSTRUIDO) | §5.4, al final |
| Por qué no obedece | §5.5, al final |
| Conducir | §5.6, al final |
| Telemetría | §5.7, al final |
| LIDAR | §5.8, al final |
| Diagnóstico | §5.9, al final |
| Cuaderno de medidas | §5.10, al final |

**Coletilla obligatoria de todos los prompts**, si por lo que sea se pega uno suelto:

```
Todo el texto en ESPAÑOL. Ningún dato inventado: donde no haya valor, escribe «no se sabe»
y que se vea distinto de un cero. Ningún número sin su antigüedad. La batería en VOLTIOS,
nunca en porcentaje. Nada parpadea, nada late, nada gira, ninguna barra indeterminada,
ningún esqueleto de carga. Ninguna pantalla de inicio de sesión. Nunca «robot averiado» ni
«LED encendido».
```

---

## §10 · Cómo se revisa lo que salga de Stitch

Cuatro preguntas, en este orden. **Si alguna falla, la pantalla vuelve.**

1. **¿Hay algún número que la pantalla no pueda sostener?** Busca porcentajes de batería, cifras
   de latencia, ritmos sin su etiqueta de procedencia, y ceros donde debería haber «no se sabe».
2. **¿Se mueve algo para siempre?** Un punto, un pulso, un spinner, una barra indeterminada, un
   cursor. **Cualquier movimiento perpetuo es un fallo**, no un detalle.
3. **¿Algún hueco se lee como un cero, o algún silencio como un «todo bien»?** Especialmente:
   `/collision_monitor_state` callado, `/estado_robot` ausente, y `−1,0`.
4. **¿Se lee a tres metros?** Solo para el muro, **y lo aprueba una persona de pie a tres metros
   del muro proyectado, no una prueba automática.**

⚠️ **Y una advertencia que este proyecto ha pagado seis veces:** una batería de comprobaciones **de
ausencia** (no aparece esta frase, no hay un cero, no hay un pulso) **la cumple una página
vacía**. Toda revisión necesita **al menos una comprobación de presencia**: que los datos
lleguen y se pinten.






