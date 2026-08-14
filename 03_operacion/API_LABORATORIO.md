# La API del laboratorio y el material docente

> **Para qué existe.** Las prácticas del curso —diez scripts y cinco documentos, 16 h de clase—
> están escritas en **ROS 1** y **no arrancan**. No es que estén desactualizadas: `import rospy`
> lanza `ModuleNotFoundError` en la primera línea. Y las quince publicaciones que hacen van a
> **`/cmd_vel`**, que en este sistema es la **salida** del `collision_monitor`: si arrancaran,
> saltarían la capa de seguridad entera.
>
> Hay que reescribirlas con o sin plataforma web. Este documento decide **sobre qué** se
> reescriben: una biblioteca del laboratorio, `atriz.py`, en vez de `rclpy` a pelo.
>
> Diseñado y acordado el **2026-08-02**.

---

## Estado, al cierre de la Tarea 13 (2026-08-03)

**Implementado.** `atriz.py`, los diez guiones y los cinco documentos están escritos y
commiteados en `Atriz_rvr` (rama `ros2`, sin `push`), y hay **89 tests** en
`~/atriz_migracion/scripts/pruebas/`.

**✅ VERIFICADO por ejecución:** las funciones puras (89 tests); que `Robot()` conecta, enciende
el barrido y lo deja apagado al cerrar (10 corridas, código 0); que un arranque fallido no deja
el LIDAR encendido; que la parada de emergencia llega al driver y se libera solo con un acto
explícito; que `color()` avisa en vez de devolver ceros y que `luces()` rechaza tipos que no son
enteros; que ningún guion importa `rospy` ni publica en `/cmd_vel`; y que las credenciales
salieron del **contenido** de los cinco documentos.

**🔴 NO VERIFICADO — nada se ha medido con el robot moviéndose:** los ~60 cm de `avanzar()`, los
ángulos de `girar()` con transportador, las cinco corridas de Ctrl-C, que los faros enciendan,
que `distancia_frontal()` apunte de verdad hacia delante (el ángulo 0 de `/scan` nunca se
contrastó con cinta), el seguidor de línea con edge-following sobre una línea real (ver más
abajo, corregido durante la implementación), la rama del `join` expirado en `cerrar()`, y
ninguna de las diez prácticas ejecutada de principio a fin. El siguiente paso exacto —la sesión
física— está en `TRASPASO.md`.

**Y esto no lo arregla ningún trabajo de documentación:** las credenciales encontradas en
`Atriz_rvr` (PSK del WiFi del laboratorio y contraseña de `sphero`) siguen en el **historial** de
las ramas remotas: tras el push, la **punta** de `origin/ros2` ya está limpia (**0**) y la de
`main` no; el **historial de las dos las conserva**, y ningún tag. Rotarlas es
acción del usuario y es lo único que cierra la exposición.
⚠️ El 2026-08-03 se borraron `migracion-ros2` y `wip/scripts-estudiantes`, que también las
servían por su punta. **Borrar ramas no cierra la exposición**; solo reduce por dónde se sirve.

---

## Lo que se comprobó antes de diseñar nada

Ejecutado sobre `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/`, no deducido:

| | Medido |
|---|---|
| Scripts que arrancan | **0 de 10.** `python3 01_avanzar.py` → `ModuleNotFoundError: No module named 'rospy'` |
| Scripts con `import rospy` | **10 de 10.** Con `rclpy`: **0** |
| Publicaciones a `/cmd_vel` | **15**, en 8 ficheros |
| `/enable_color`, que usan dos scripts | **NO EXISTÍA** el 2026-08-02. ✅ **Existe desde el 2026-08-06** (`std_srvs/SetBool`), y hace justo lo que aquellos dos scripts esperaban: encender el LED del sensor en caliente |
| Documentos | 5 `.md`, 1923 líneas |

Y una cosa más, que no estaba en el encargo y cambia una prioridad:

### 🔴 Las credenciales del laboratorio están en un repositorio PÚBLICO

`scripts/estudiantes/00_LEEME_PRIMERO.md` y `GUIA_PASO_A_PASO.md` llevan **en texto plano** la
PSK del WiFi del laboratorio y la contraseña de un usuario. Están **empujadas al remoto**, no solo
en el disco:

```
$ git show origin/ros2:scripts/estudiantes/00_LEEME_PRIMERO.md | grep -n "Contraseña"
14:Contraseña: <PSK del WiFi>
26:6. Contraseña: <contraseña de usuario>
...
$ git branch -r --contains b1ca095
  origin/main   origin/migracion-ros2   origin/ros2   origin/wip/scripts-estudiantes

$ curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/Bura-hub/Atriz_rvr
200          ← sin autenticar: el repositorio es PÚBLICO
```

📝 **Es un segundo caso, no el que ya se conocía.** El expuesto que este proyecto tenía anotado es
la credencial de `sphero` en `Atriz_web_server`. Este es **otro fichero, otro repositorio, otras
dos credenciales**, y una de ellas es la **PSK del WiFi** — la misma que el `fmask` de
`/boot/firmware` deja legible en el robot y que la imagen dorada replicaría por 16.

→ **Y la consecuencia para el orden de trabajo:** reescribir el material **saca las credenciales
del contenido actual, no del historial**. Lo que de verdad lo cierra es **rotarlas** (acción del
usuario). Purgar el historial es higiene, y es incompleta por naturaleza: GitHub conserva commits
sin referenciar accesibles por su SHA, y cualquier *fork* se los queda para siempre. Rotar primero,
reescribir después; al revés da sensación de resuelto sin estarlo.

---

## Requisitos, decididos con el usuario

| | |
|---|---|
| **Qué se enseña** | **Robótica.** ROS es el medio, no la asignatura |
| **Dónde corre el código del alumno** | **En el robot**, contra una API del laboratorio — no contra `rclpy` ni contra el SDK |
| **Qué escribe el alumno** | Su programa, usando la API. **No** escribe nodos ROS |
| **Alcance** | Los 10 scripts y los 5 documentos. Se reescriben, no se parchean |

---

## La decisión: una biblioteca, y por qué no `rclpy` directo

Un script de alumno escrito contra `rclpy` tiene que acertar, **cada vez y sin ayuda**, en siete
cosas que este proyecto ha aprendido pagándolas. La alternativa es que las acierte una vez, en un
fichero, y que el alumno escriba robótica.

```python
from atriz import Robot

robot = Robot()                      # conecta, enciende el barrido y comprueba que hay /scan
robot.avanzar(0.20, 3)               # m/s durante segundos
robot.girar(90)                      # grados; positivo = a la izquierda
robot.parar()
r, g, b, claro = robot.color()       # servicio /get_rgbc_sensor_values, 13-20 ms
robot.luces(255, 0, 0)               # RGB de todos los faros
d = robot.distancia_frontal()        # metros, del /scan
v = robot.bateria()                  # voltios
robot.parada_emergencia()            # acto explícito; NO se libera sola
robot.cerrar()                       # para el robot y apaga el barrido
```

📝 **`color()` sale de un servicio, no del topic `/color`, y por una razón medida.** El mensaje
`atriz_rvr_msgs/msg/Color` solo lleva `rgb_color` y `confidence` — **no trae el canal `clear`**,
que es el que discrimina de verdad (**12.6×** entre blanco y negro, contra un RGB que apenas se
mueve). `clear` solo lo da `/get_rgbc_sensor_values`, y **cuesta 13.3–20.5 ms** (n=5, medido el
2026-08-02 sobre el robot vivo): cabe de sobra en un lazo de control a 10 Hz, que es lo que hace el
seguidor de línea.

Y con `with`, que es lo que se enseña, para que cerrar no dependa de acordarse:

```python
with Robot() as robot:
    robot.avanzar(0.20, 3)
    robot.girar(90)
```

**Un solo fichero `atriz.py`, junto a los scripts, sin instalar.** Nada de paquete, `setup.py` ni
`colcon build`: el material tiene que funcionar en 16 robots salidos de la imagen dorada, y cada
paso de instalación es una cosa más que se rompe en clase. `python3 mi_script.py` y ya.

### Las ocho cosas que la biblioteca acierta por el alumno

Ninguna es hipotética. Cada una es un fallo que este proyecto ya pagó:

| | Qué hace `atriz.py` | El fallo que evita |
|---|---|---|
| 1 | Publica en **`/cmd_vel_raw`**, nunca en `/cmd_vel` | `/cmd_vel` es la **salida** del `collision_monitor`. Publicar ahí **funciona**, y por eso es el agujero más silencioso: el robot obedece y no hay capa de seguridad. Los 10 scripts actuales lo hacen |
| 2 | Llama a **`/start_scan`** al construirse | Un robot recién arrancado **no obedece `cmd_vel`**: el barrido arranca apagado a propósito, y sin `/scan` el `collision_monitor` bloquea (medido **0.0 cm** contra 9.9 del control). Desde fuera es **idéntico a un robot averiado** |
| 3 | Republica el comando a **10 Hz** mientras dura el movimiento | El watchdog del driver corta a los **0.3 s** sin `cmd_vel`. Un `sleep(3)` entre dos publicaciones deja al robot parado casi todo el tiempo |
| 4 | **Ctrl-C para el robot**, con `SignalHandlerOptions.NO` | `rclpy.init()` instala su manejador de SIGINT e **invalida su propio contexto**: el `except KeyboardInterrupt` que intenta publicar la parada muere con `publisher's context is invalid`. Medido: **0 líneas** de parada contra 5 con la opción puesta. Y **es intermitente**, que es lo que lo hizo pasar desapercibido |
| 5 | Se suscribe con **BEST_EFFORT** a `/scan`, `/odom`, `/imu`, `/color` y `/encoders` | Un suscriptor RELIABLE **no recibe nada, sin error**: DDS no empareja. Es la misma trampa de QoS que costó la parada de emergencia. 📝 `/ambient_light` queda **fuera de la API**: la decisión del 2026-08-01 es que en este montaje no significa lo que parece |
| 6 | Limita a **≤ 0.40 m/s** y a un tiempo máximo por llamada | 0.40 m/s es la meseta medida del robot; por encima el número es ficción. El tiempo máximo evita el script que se va a comer una pared mientras el alumno mira otra cosa |
| 7 | `cerrar()` **para el robot y apaga el barrido**, también en el camino de error | Si no, el X2 se queda girando a **11.8 Hz** en vez de 2.7 — 24/7, por 16 robots |
| 8 | 🆕 `cerrar()` **apaga además los modos IR, y ANTES de parar los motores** | `following` y `evading` son modos del **firmware**: el robot conduce sin que nadie le mande `cmd_vel`, así que ni el watchdog ni el `collision_monitor` los ven. Parar primero lo frenaría un instante y **volvería a arrancar en la siguiente detección** — el mismo fallo que ya mordió a la parada de emergencia. Sin esto, un Ctrl-C deja **un robot conduciendo por el aula** |

📌 Eran siete hasta el 2026-08-11. La octava salió de probar el IR con dos robots por primera vez.

---

## 🆕 Infrarrojos robot-a-robot (2026-08-11)

Este documento tenía **cero menciones al IR** hasta esta fecha, y la biblioteca tampoco lo exponía.
No era un olvido con causa: **hasta el 2026-08-10 solo había un robot**, y el IR robot-a-robot no
se puede ni probar con uno.

Al probarlo con dos aparecieron dos cosas que cambian lo que se puede prometer al alumno:

- ✅ **`broadcasting`, `following` y `evading` funcionan** — comportamiento físico confirmado.
- 🔴 **El IR de ROS 1 nunca recibió un solo mensaje**, y su `evading` llamaba a un método que no
  existe en el SDK. No se perdió al migrar: nunca funcionó.

### Lo que expone la biblioteca

| | qué hace | ¿mueve el robot? |
|---|---|---|
| `emitir_ir(codigo)` | manda un código 0-7 por los cuatro emisores | no |
| `escuchar_ir(caducidad=2.0)` | el último código recibido, o `None` | no |
| `quien_hay_cerca()` | lo que ven los cuatro sensores | no |
| `emitir_como_baliza(lejos, cerca)` | emite para que otro te siga o te evite | no |
| `seguir_a_otro(lejos, cerca)` | va hacia el que emita | 🔴 **sí, solo** |
| `huir_de_otro(lejos, cerca)` | se aleja del que emita | 🔴 **sí, solo** |
| `parar_ir()` | apaga los tres modos | — |

### Tres decisiones que conviene entender

**1 · `escuchar_ir()` tiene caducidad, y no es una comodidad.** El registro del firmware **se borra
al segundo**. Un código de hace diez segundos no dice que haya alguien ahí ahora, solo que lo hubo.
Devolver el último valor sin más sería mentir con un dato real.

**2 · `quien_hay_cerca()` dice SI hay alguien, y solo a medias POR DÓNDE — y está MEDIDO.**
Se probó el 2026-08-11 con los dos robots, girando el que lee (evidencia 100):

```
[1] solo          →  el otro está a tu IZQUIERDA
[1,3] / [1,2,3]   →  está DETRÁS
[2,3]             →  está DELANTE o A LA DERECHA    ← no los separa
```

**Tres estados, no cuatro.** Y `sensor_0` **no lleva datos nunca**, en ninguno de los dos robots.
🔴 La máscara del SDK, que asignaría cada byte a una esquina, está documentada **para el BOLT** y
**no describe al RVR**: no encaja en ninguna de las dos lecturas posibles del orden de bytes.

Por eso los campos siguen llamándose `sensor_N`. No porque falte medirlo, sino porque **la
medición dice que no se pueden nombrar**.

**3 · Los dos que conducen avisan por pantalla y se apagan al cerrar.** Ver la garantía nº 8: es la
única forma de que un Ctrl-C no deje un robot rodando por el aula.

---

## `girar()` en lazo cerrado, y por qué no una constante calibrada

⚠️ **Ojo con la atribución:** los **86.6 / 86.2 / 87.7°** que este documento citaba como «lo que
da el giro por tiempo» se midieron con **`move_timed`** —un servicio del driver— **a 1.0 rad/s**
(evidencia 48), y la práctica usa `girar_por_tiempo()` **a 0.8 rad/s** por `/cmd_vel_raw`: otro
mecanismo, otra velocidad. **El déficit de ESE camino no está medido.** Con esa reserva: el giro
por tiempo no cierra, y con `move_timed` a 90° comandados salió **86.6 / 86.2 / 87.7°** (n=3, medido
el 2026-08-02 con baterías del 55 % al 100 %, así que **el déficit no depende de la carga**). La
salida barata es multiplicar por 1.04 y seguir.

**No se hace así.** `girar()` mide el rumbo real en `/odom` y para cuando llega:

```
Δyaw acumulado, normalizado a (−π, π] en cada paso, hasta alcanzar el objetivo
```

La normalización no es un detalle: `atan2` devuelve −π..π, así que un giro de 360° leído como yaw
absoluto vuelve al punto de partida y **se lee como 0°**. Acumular el incremento normalizado es lo
que hace que 360° sean 360°. Es exactamente lo que ya hace la fase F5 de la prueba de aceptación,
y se reutiliza.

📝 **Y es la razón pedagógica de todo el documento:** un lazo cerrado le gana a una constante
calibrada, y eso es una idea de robótica de verdad. Un alumno que ve `girar(90)` acertar sobre un
robot con déficit de fábrica ha visto para qué sirve realimentar.

⚠️ **Lo que el lazo NO arregla:** la deriva de yaw es **~1000× mayor** en los primeros minutos tras
encender el RVR (0.97 °/30 s recién encendido contra 0.001 siete minutos después). En una práctica
de 15 min empezada sobre un robot recién encendido son decenas de grados de error acumulado en la
odometría. El lazo cerrado de un giro suelto no lo nota —un giro dura segundos—, pero un script que
encadene diez movimientos sí. Va escrito en la guía, no escondido.

---

## 🔴 El seguidor de línea: el diseño original NO podía funcionar, y se corrigió al implementarlo

**Este documento especificaba, en su primera versión, un PID de umbral único sobre el canal
`claro`.** Es un error de diseño, no una simplificación aceptable, y se descubrió en la tarea 11
—al implementarlo—, no aquí. Se deja escrito para que quien retome este documento no repita el
error, y porque esconder una corrección de diseño es exactamente lo que este proyecto se ha
prohibido hacer.

**Por qué no puede funcionar.** El sensor de color mira hacia abajo y entrega un solo escalar,
`claro`. Si el robot deriva a la **izquierda** del centro de la línea, el sensor deja de ver
negro y ve suelo claro. Si deriva a la **derecha**, pasa exactamente lo mismo: deja de ver negro
y ve suelo claro. La lectura es **idéntica** en los dos casos, así que
`error = (claro − umbral) / umbral` tiene el mismo signo esté el robot desviado al lado que sea
— y un PID solo puede sacar **una** salida de giro para un signo de error dado. La corrección es
la correcta la mitad de las veces y empuja al robot **más lejos** de la línea la otra mitad.

No era un hallazgo nuevo: ya estaba escrito en el propio repositorio, en
`SEGUIDOR_LINEA_EXPLICACION.md` de la versión ROS 1 que este material reemplaza (sección 3):
*«con un solo sensor no es fiable estimar el desalineamiento lateral clásico»*. Esa versión
antigua ya implementaba **edge-following** por esta misma razón, y el diseño de este documento
no lo cruzó contra ella antes de especificar un PID de umbral único.

**La corrección, decidida por el usuario: edge-following.** El seguidor ya no intenta centrarse
sobre la línea; sigue siempre el **mismo borde**:

- El **PID no se toca** (es contenido docente) y decide la **magnitud** del giro, a partir de
  cuánto se aleja `claro` del centro entre `UMBRAL_NEGRO` y `UMBRAL_CLARO`.
- El **signo** lo decide `lado_borde` — un estado que se arrastra entre vueltas del bucle, no una
  lectura instantánea — y se invierte si el robot lleva más de `tiempo_perdido_max` segundos sin
  reencontrar el borde.

**Y costó una segunda corrección.** La primera versión del edge-following medía el signo con las
fronteras de histéresis de `clasificar()` (en `umbral ± margen`) y la magnitud con el centro real
— dos referencias distintas. Entre ambas fronteras (`claro` 701–949 con los umbrales medidos)
discrepaban: el estado seguía siendo `'negro'` (signo hacia un lado) mientras la magnitud ya
crecía hacia el otro, produciendo **realimentación positiva** — el controlador alejaba al robot
del borde en vez de traerlo, justo lo contrario de lo que el edge-following existe para hacer.
Cinco tests que solo probaban los extremos y el punto de equilibrio (181, 700, 1275) no lo
atraparon: la banda intermedia no la miraba nadie. El arreglo fue hacer que el signo y la
magnitud midan desde el mismo centro. Detalle completo, con las tablas de antes/después, en
`.superpowers/sdd/2026-08-02-api-laboratorio/tarea-11-report.md`, «Ronda de arreglo 1» y «Ronda
de arreglo 2».

**Lo que se simplificó respecto a la versión ROS 1, a propósito, y sin verificar.** La versión
antigua recuperaba el borde perdido en **dos fases discretas**: retroceder con giro contrario y
luego escanear en el sitio. El material nuevo **no** reproduce esa máquina de estados — solo
invierte `lado_borde` tras `tiempo_perdido_max` segundos sostenido en `'claro'`, sin fase de
retroceso ni de escaneo. Es una simplificación deliberada, no una réplica, y **NO VERIFICADA
sobre el robot**: si al moverlo se pierde el borde de forma persistente, es el primer sitio donde
mirar.

🔴 **NO VERIFICADO, en conjunto: el seguidor de línea nunca se ha probado sobre una línea real.**
Las nueve funciones puras nuevas tienen tests (52 → 61 en `scripts/pruebas/`, tres rondas), pero
eso comprueba la aritmética del signo y la magnitud, no que el robot siga una línea de verdad.

---

## Lo que la API NO puede hacer, y hay que decirlo

Dos límites reales. Escribirlos aquí es más barato que descubrirlos en clase.

**⚠️ `robot.color()` devuelve oscuridad hasta que enciendas la luz del sensor, y no es un fallo de
la API.** El sensor necesita su propia luz. Desde el 2026-08-06 **se enciende en caliente** con el
servicio `enable_color` (`std_srvs/SetBool`) — medido: canal claro **1 → 1321**, y vuelta a 1 al
apagar (evidencia 76). Antes de esa fecha aquí ponía que era imposible; era falso.

⚠️ **Enciéndelo y apágalo:** deja un LED blanco bajo el chasis gastando batería.

El servicio systemd sigue arrancando con la luz apagada, que es lo que quieres por defecto en un
laboratorio de 16 robots:

```
$ ros2 param get /rvr_driver color_detection
Boolean value is: False
```

→ **La API lo consulta al construirse y avisa en voz alta** en vez de devolver `[0,0,0]` como si
fuera negro — que es justo lo que `/color` publicó durante meses sin que nadie lo notara. La
práctica de color exige arrancar el robot con `color_detection:=true`, y eso va en su enunciado.

**⚠️ La API no puede saber si la parada de emergencia está activa.** El driver **no publica ningún
estado de parada**: de los 29 topics vivos, los tres que llevan `emergency_stop` en el nombre son
**suscripciones suyas** —los tres nombres que escucha—, no un estado que alguien pueda leer. Lo
único observable es el síntoma —se manda `cmd_vel` y el robot no se mueve—, y ese síntoma es **indistinguible** de un
barrido apagado o de un `collision_monitor` frenando. Así que:

- Con **Ctrl-C**, `atriz.py` publica **velocidad cero** repetida y deja de publicar. 🔴 **No** dispara
  la parada de emergencia, y esto es una corrección al primer borrador de este diseño: la parada
  **se queda enganchada** hasta que alguien llame a `/release_emergency_stop`, así que un Ctrl-C
  que la disparara dejaría **el siguiente script del alumno sin funcionar y sin explicación** —
  justo la clase de trampa silenciosa que este proyecto lleva toda la migración pagando. El camino
  correcto para que un script termine es el normal: cero, y el watchdog de 0.3 s por debajo
- La parada de emergencia sí está, como **acto explícito**: `robot.parada_emergencia()`, que
  publica en `/emergency_stop` con **RELIABLE + VOLATILE** (el QoS que costó el tercer fallo)
- **Nunca** se llama a `/release_emergency_stop` sola, ni al arrancar ni al cerrar: liberar es del
  operador. Ese fue el cuarto fallo — al **soltarla**, no al pulsarla, el robot arrancaba solo
- Y **no promete** «respeta la parada», porque no puede comprobarlo

## 🔴🔴 `avanzar(v, s)` promete SEGUNDOS, no metros — y el alumno entiende metros

Medido el 2026-08-08 ejecutando la práctica 1 dos veces seguidas, sin tocar nada (evidencia 85):

```
  26,4 cm   ← con algo cerca
  59,5 cm   ← despejado          (los dos con avanzar(0.20, 3))
```

La causa está en la capa de seguridad, y **no es un fallo**: el polígono `Precaucion` frena al
40 % y mide **60 cm de largo × 40 de ANCHO**, centrado en el robot. Con un robot de 21,7 cm de
ancho, **cualquier cosa a menos de ~9 cm de un costado** lo frena, aunque se esté alejando de
ella. El journal lo registra; el alumno no ve nada.

📌 **Consecuencia de diseño, y por eso vive aquí y no solo en un enunciado:** ninguna práctica
puede apoyarse en que `avanzar(v, s)` recorra `v × s` metros. La 1 pide medir con cinta y la 3
dibuja un cuadrado — **un cuadrado pegado a una pared sale con un lado más corto**, y la primera
sospecha del alumno serán los giros, que están bien.

⚠️ **Lo que NO se hace, y conviene que conste la decisión:** la API *podría* leer
`/collision_monitor_state` y avisar. Se descarta por ahora — añadiría una suscripción y una
condición de carrera a la biblioteca para un caso que se resuelve **despejando la mesa**, y este
proyecto ya tiene documentado que una salvaguarda mal puesta cuesta más que el problema. Lo que sí
se hace es **decirlo en la cabecera de las prácticas 1 y 3**, que es donde el alumno lo va a leer.

📝 Es la evidencia 49 con otra cara: allí un retroceso comandado de 30 cm hizo 14 porque el
polígono **no sabe hacia dónde vas**. Aquí es el **ancho**.

---

## El alcance de la reescritura

**Los 10 scripts.** Se conserva la progresión, que es lo bueno del material actual; cambia el
sustrato. `05` y `11` cambian además de fondo, porque usan un servicio que no existe:

| | Hoy | Después |
|---|---|---|
| `01_avanzar` · `02_girar` · `03_cuadrado` | `rospy` → `/cmd_vel` | `robot.avanzar()` / `robot.girar()` |
| `04_giro_preciso` | giro por tiempo, con la constante | `robot.girar()` en lazo cerrado, y la práctica es **comparar** las dos |
| `05_sensor_color` · `11_sensor_avanzado` | `/enable_color`, **que no existe** | `robot.color()`, y el enunciado exige arrancar con `color_detection:=true` |
| `10_movimiento_completo` | clase con `rospy` | la misma clase, sobre la API |
| `90_template` | plantilla `rospy` | plantilla de la API — es lo que copia el alumno |
| `99_test_ctrl_c` | prueba que Ctrl-C para | **sigue existiendo y gana valor**: ahora comprueba la protección 4, que ha fallado de verdad |
| `seguidor_linea_pid_demo` | PID de umbral único sobre `rospy` + `/cmd_vel` | 🔴 **No** «PID sobre la API» tal cual: un umbral único no puede funcionar con un solo sensor (ver sección dedicada, arriba). Rediseñado a **edge-following** sobre la API — el PID (sin tocar) decide la magnitud, `lado_borde` decide el signo |

**Los 5 documentos.** `00_LEEME_PRIMERO.md`, `GUIA_PASO_A_PASO.md`, `README.md`, `REFERENCIAS.md`
y `SEGUIDOR_LINEA_EXPLICACION.md`. Fuera de ellos:

- **las credenciales en texto plano** — es material que ven los alumnos, y está en público
- **`roscore`** y arrancar el driver a mano: el robot arranca solo desde el 2026-07-31
- **`/enable_color`** y todo lo que se apoya en él
- **`/cmd_vel`** como topic al que escribir

Y entra lo que hoy no está y hace falta el primer día: **el barrido se enciende**, la parada de
emergencia es un acto explícito, y qué significa que el robot vaya despacio (el polígono de
precaución frena al 40 % **aunque el robot se aleje**: 30 cm comandados → 14 medidos).

---

## Verificación

La regla del proyecto: se comprueba **el efecto**, no el código de salida.

> ✅ **ACTUALIZACIÓN 2026-08-13: la sesión física se hizo, en tres tandas, y casi todos los 🔴
> de abajo están cerrados.** 2026-08-03 (evidencias 57-61: avanzar, girar con transportador
> n=9, faros), 2026-08-08 (evidencia 85: ocho de las diez prácticas corridas, cuatro fallos
> reales encontrados y arreglados) y 2026-08-13 (evidencia 108: los cinco ensayos en banda con
> el usuario midiendo — avanzar 58/59 cm, girar(90) ~90°, **Ctrl-C 5 de 5** con ~1 cm de
> arrastre, luces vistas, distancia_frontal a 1,1 cm de la cinta).
> ⏳ **Sigue abierto únicamente el seguidor de línea (práctica 63)**, que espera a que haya
> línea en el aula; el calibrador de umbral está en `mediciones_banco/calibrar_claro.py`.
> La lista de abajo se conserva como estaba: es la foto del cierre de la Tarea 13.

**Estado de cada punto al cierre de la Tarea 13 (2026-08-03):**

1. 🔴 **NO VERIFICADO. Los 10 scripts se ejecutan contra el robot**, uno a uno, con el pasillo
   despejado. Un script que «no da error» pero no mueve el robot **no cuenta como verificado**.
   Ninguno de los diez se ha ejecutado todavía — es la sesión física, ver `TRASPASO.md`.
2. **Las siete protecciones, cada una con su comprobación de efecto.** Las tres que se pueden
   falsear a propósito:
   - **`/start_scan`**: ⚠️ **PARCIAL.** ✅ Verificado en banco que `Robot()` enciende el barrido y
     lo deja apagado al cerrar (10 corridas, código 0) y que un arranque fallido no deja el LIDAR
     encendido. 🔴 **NO VERIFICADO** el caso que de verdad importa: un script sobre un robot
     **recién reiniciado de verdad** (`sudo reboot`), que es el estado con el que se encuentra un
     alumno y hoy parece un robot averiado.
   - **Ctrl-C**: 🔴 **NO VERIFICADO.** No se ha matado ningún script a mitad de un avance ni
     medido el desplazamiento posterior con cinta. Y el fallo que esto protege es
     **intermitente**: una sola pasada verde no distinguirá «arreglado» de «esta vez tocó» — hacen
     falta varias corridas, no una.
   - **Watchdog**: 🔴 **NO VERIFICADO.** No se ha medido cuánto recorre de verdad
     `avanzar(0.20, 3)`.
3. 🔴 **NO VERIFICADO. `girar()` medido con transportador**, n≥3 a 90°, 180° y 360°, contra los
   mismos ángulos por tiempo. El código implementa el lazo cerrado descrito arriba, pero **nadie
   ha medido con transportador si de verdad le gana a la constante**. Si no lo hace, el argumento
   pedagógico de este documento es falso y hay que cambiarlo.
4. ✅ **VERIFICADO. Que un alumno no pueda saltarse la seguridad sin querer**:
   `grep -rn "cmd_vel" *.py | grep -v cmd_vel_raw` sobre los diez scripts y `atriz.py` da solo dos
   líneas, y las dos son comentarios que explican por qué NO se usa `/cmd_vel` — ningún guion lo
   publica, y `atriz.py` no ofrece ningún camino que lleve ahí.
5. ✅ **VERIFICADO el `grep`; 🔴 NO VERIFICADO (ni verificable por este trabajo) que la exposición
   esté cerrada.** Las credenciales salieron del contenido de los cinco documentos (tarea 12).
   Pero siguen en el **historial** de las cuatro ramas remotas de `Atriz_rvr` — medido: 11
   coincidencias cada una, ningún tag afectado. **Rotarlas sigue pendiente y es del usuario**; es
   lo único que cierra la exposición de verdad.

---

## Lo que este trabajo NO cierra

- **No rota las credenciales expuestas** ni purga el historial. Saca el texto del contenido actual;
  lo demás es acción del usuario, con `sudo` y sobre GitHub.
- **No toca la plataforma web.** La API corre en el robot para el alumno que trabaja en el robot.
  Que la web ofrezca esta misma API es la Fase C, y llega después.
- **No arregla la deriva de yaw del arranque en frío.** Se documenta; desaparece sola.
- **No decide el arranque automático de Nav2/SLAM**, que es el punto siguiente del orden acordado.
- 🔴 **No mueve el robot.** La Tarea 13 (cierre de este plan, 2026-08-03) implementó, revisó y
  documentó el diseño y su corrección (ver «El seguidor de línea», arriba), pero por instrucción
  explícita no ejecutó ningún guion contra el robot ni movió las orugas. Los cinco puntos de
  «Verificación» quedan, en su mayoría, sin ejecutar — ver el estado marcado punto a punto ahí
  arriba, y el siguiente paso exacto en `TRASPASO.md`.
