# Arrancar y parar SLAM, Nav2 y el LED del sensor de color desde la web

**Fecha:** 2026-08-06 · **Estado:** diagnóstico MEDIDO, soluciones PROPUESTAS y sin implementar.
**Para:** el Claude del PC, que lleva `atriz-lab`.

---

## Lo que pide el usuario

> *«Poder arrancar y detener SLAM, Nav2 y el LED del sensor de color desde la web.»*

Y el contexto en el que lo pide: *«el robot y la Pi después de volverlo a iniciar debería poder
iniciarse sin problemas y todo debería ser iniciable desde la plataforma web»*.

## Por qué surge ahora: la Pi se reinicia sola cuando el RVR se apaga

Medido el 2026-08-06. Mapeando un cuarto, el usuario puso el RVR a cargar. Al volver, `/scan` y
`/map` estaban a cero mientras `/odom`, `/tf` y `/estado_robot` seguían sanos.

Se creyó que el driver se había reiniciado. **No fue eso.** El listado de arranques lo zanja:

```
arranque -1  termina  2026-08-06 15:09:03
arranque  0  empieza  2026-08-06 16:17:06     ← más de una HORA de hueco
```

**Se reinició la Pi entera**, porque se alimenta del USB del RVR. Eso explica de golpe los cuatro
síntomas: el barrido apagado (lo fuerza el `ExecStartPost` en cada arranque), `NRestarts=0`,
`slam_toolbox` muerto (se lo llevó la sesión SSH) y el mapa perdido.

📝 **Y el contenido del journal de ese arranque ya no existe** —rotado por `SystemMaxUse=32M`—
pero **las cabeceras de arranque sobrevivieron y bastaban**. Lo irrecuperable era el detalle, no
el desenlace.

---

## Estado medido: qué vuelve solo y qué puede lanzar la web

```
atriz-robot   enabled · active      ✅ vuelve solo   (verificado: volvió tras el reinicio)
atriz-nav     disabled · inactive   🔴 NO vuelve
SLAM          no existe unidad      🔴 se lanza a mano por SSH
```

Y lo que la web puede pedir hoy, que es la lista blanca entera de servicios:

```
/start_scan · /stop_scan · /release_emergency_stop · /set_pos_and_yaw
/set_led_rgb · /set_multiple_leds · /set_leds · /trigger_led_event
```

🔴 **Ocho servicios y ninguno arranca nada.** Encienden el barrido, liberan la parada, ponen LEDs.
**Nav2 y SLAM no son servicios ROS: son unidades de systemd y ficheros de launch**, y rosbridge
solo sabe hablar ROS. La web no tiene a quién pedírselo — no es que falte un botón.

---

## Los tres, uno a uno. Los obstáculos NO son el mismo

### 1 · SLAM — el más fácil, y no tiene unidad

No existe `atriz-slam.service`. Se lanza a mano (`slam.launch.py`), y por eso **muere con la
sesión SSH** — que es parte de lo que pasó el 2026-08-06.

⚠️ Y arrastra una trampa ya documentada: **`slam_toolbox` sobrevive a un reinicio del driver y se
queda vivo y MUDO** — con un hueco en su búfer TF, deja de procesar, y el mapa sale idéntico celda
a celda tras mover el robot 80 cm. Invalidó una prueba entera de la Fase 4.

### 2 · Nav2 — la unidad existe, y está deshabilitada A PROPÓSITO

Tres razones medidas, todas siguen en pie:

| | |
|---|---|
| **Coste** | Nav2 son **~58 % de un núcleo**, y la Pi sale de la batería del RVR. Con ~2 h de autonomía contra clases de 2-3 h, tenerla siempre encendida **acorta la sesión del alumno** |
| **Exige un mapa** | `atriz-nav.sh:47` falla alto si no hay `aula.yaml`. Habilitarla hoy la dejaría fallando en bucle |
| **`BindsTo=`** | medido hoy con unidades de juguete: si el proceso base MUERE, la unidad atada queda `inactive` **y no vuelve** |

🔴 **Y el resultado de esa medición es más incómodo de lo que parece:**

```
dependencia   tras `systemctl restart`   tras MATAR el proceso
BindsTo=      active                     inactive   🔴 no vuelve
PartOf=       active                     active
```

Parece que `PartOf=` es la respuesta. **No lo es:** «active» no es «funcionando». Es exactamente
la trampa de `slam_toolbox` — sobrevive y queda mudo. La elección real es entre **morir
visiblemente** y **sobrevivir mudo**, y este proyecto tiene medido que lo segundo es peor.
→ Lo que hace falta no es cambiar la directiva: es que la unidad atada **vuelva a arrancar**.

### 3 · 🔴 El LED del sensor de color — NO se puede encender en caliente

Y esto es lo que hay que saber antes de diseñar ningún botón.

`rvr_driver_node.py:1218`, medido el 2026-07-31:

> **«Con el streaming de `color_detection` ya configurado, `enable_color_detection` NO HACE
> NADA.»** Se comprobó llamándolo desde un servicio y mirando `/color` a la vez: **481 mensajes,
> todos `[0, 0, 0]`**, durante toda la llamada.

El sensor **tiene que activarse ANTES de `add_sensor_data_handler`**, o sea antes de que arranque
el streaming. Hoy es un parámetro de arranque: `color_detection:=false` por defecto, y se pone a
`true` al lanzar `robot.launch.py`.

**Un botón «encender el LED del color» que llame a `enable_color_detection` devolvería éxito y no
haría nada.** Es exactamente el patrón que este proyecto persigue, y ya está medido dos veces en
este mismo sensor (`undercarriage_white` devuelve `success=True` sin encender nada).

---

## Las soluciones, en orden de coste

### A · Envolver SLAM y Nav2 en servicios ROS que el driver exponga  ← recomendada

Cuatro servicios nuevos (`/arrancar_slam`, `/parar_slam`, `/arrancar_nav`, `/parar_nav`) que el
driver registre junto a los 18 que ya tiene, y cuatro entradas más en la lista blanca.

Por dentro, `systemctl start|stop` de dos unidades: `atriz-slam.service` (nueva) y
`atriz-nav.service` (ya existe).

**Lo que hay que respetar, y no es negociable:**

- 🔴 **Los servicios del driver comparten `MutuallyExclusiveCallbackGroup`**: un callback largo
  **bloquea `/release_emergency_stop`**. Arrancar Nav2 tarda segundos, así que **no puede
  esperarse dentro del callback** — tiene que lanzarse y volver, y el estado consultarse aparte.
- 🔴 **`systemctl start` desde el driver exige permisos.** El servicio corre como `sphero`. Hace
  falta una regla de `polkit` acotada a esas dos unidades, **no** un sudo sin contraseña general.
- 🔴 **El éxito es que arranque, no que la llamada vuelva.** El servicio no puede devolver
  `success=true` porque `systemctl` devolvió 0: hay que comprobar el efecto —`/map` publicando
  para SLAM, `/navigate_to_pose` disponible para Nav2— o devolver «lanzado, mira el estado».
- 🔴 **Nav2 sin mapa falla en bucle.** El servicio debe negarse y decirlo, no intentarlo.

**Lo que la web necesita para pintarlo:** un topic de estado. `/estado_robot` ya existe y se
publica a 1 Hz — añadirle dos campos (`slam_activo`, `nav_activo`) es más barato que un topic
nuevo, y llega por un camino que la web ya lee.

### B · El LED del color — dos caminos, y ninguno es un botón

**B1 · Reiniciar el driver con el parámetro puesto.** Es lo único que funciona hoy. Un servicio
`/color_detection` que reescriba el parámetro y **reinicie `atriz-robot`**. Honesto pero brutal:
tira la telemetría unos 25 s y con ella cualquier sesión en curso.

**B2 · Arreglarlo en el driver: reordenar el arranque del streaming.** Que
`enable_color_detection` se pueda aplicar deteniendo y rearmando el streaming —`stop()`,
`enable_color_detection(True)`, `add_sensor_data_handler`, `start()`—, que es la secuencia que el
propio driver ya ejecuta en `_recuperar_streaming()`. **Más trabajo, y es la solución de verdad.**

⚠️ **NO VERIFICADO**: que rearmar el streaming baste para que el sensor se active. Lo medido es
que llamarlo con el streaming ya configurado no hace nada; que funcione tras un `stop()` es una
hipótesis razonable **y hay que medirla antes de prometer el botón.**

### C · El agente de sesión (Fase B) — la solución general, y está bloqueada

Es lo que resuelve esto y el terminal del alumno a la vez. Depende de la **F0**: el aislamiento de
clientes del AP del aula, que necesita estar en el laboratorio. Mientras siga sin medir, no se
puede construir sobre él.

---

## Y lo que hay que arreglar aunque no se haga nada de lo anterior

🔴 **Que el robot vuelva entero tras un apagón del RVR.** Hoy vuelve `atriz-robot` y nada más.
Con 16 robots y alumnos poniendo a cargar, esto va a pasar constantemente. Y no basta con
`enable`: la unidad de Nav2 exige mapa, y la de SLAM no existe.

📌 **Decisión que corresponde al usuario, no a la web:** si Nav2 y SLAM deben arrancar **solos** al
encender (y pagar la batería), o **solo cuando la web lo pida** (y entonces hace falta A).

## Lo que le toca al PC

1. **Los botones no existen todavía en ninguna capa.** Antes de dibujar nada, saber que el del
   color **no puede funcionar como los otros dos**.
2. **Si se implementa A**, la web necesita: cuatro servicios en `contrato.ts` + sus tipos, y dos
   campos nuevos en `EstadoRobot` para pintar el estado sin sondear.
3. **El estado de arranque no es booleano.** «Arrancando» dura segundos y hay que pintarlo: si la
   interfaz solo tiene encendido/apagado, el alumno pulsará dos veces.
