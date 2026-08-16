# Arrancar y parar SLAM, Nav2 y el LED del sensor de color desde la web

**Fecha:** 2026-08-06 · **Para:** el Claude del PC, que lleva `atriz-lab`.

**Estado:**
- ✅ **El color: HECHO en el robot** y verificado por rosbridge (§3 y §B). Falta la web.
- ⏳ **SLAM y Nav2: diagnosticados, sin implementar.** Ahí el obstáculo es real.

⚠️ **Este documento se corrigió el mismo día.** La versión de la mañana afirmaba que el LED del
color **no se podía encender en caliente**; era falso y no estaba medido. Si trabajas sobre una
copia anterior, **tírala**.

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

**Se reinició la Pi entera**, porque se alimenta del USB del RVR ⚠️ (cierto; pero **apagar** el RVR
no basta para tirarla — medido el 2026-08-15, evidencia 123: hace falta **cortar** la
alimentación). Eso explica de golpe los cuatro
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
/enable_color · /get_rgbc_sensor_values          ← añadidos el 2026-08-06
```

🔴 **Diez servicios, y ninguno arranca SLAM ni Nav2.** Encienden el barrido, liberan la parada,
ponen LEDs y ahora hacen la sesión de color. **Nav2 y SLAM no son servicios ROS: son unidades de
systemd y ficheros de launch**, y rosbridge solo sabe hablar ROS. La web no tiene a quién
pedírselo — no es que falte un botón.

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

🔴 **AQUÍ SE CONCLUYÓ QUE `PartOf=` NO VALÍA, Y ERA FALSO.** Se escribió: *«"active" no es
"funcionando": sobrevive y queda mudo»*. **Refutado el 2026-08-07, evidencia 78.**

La tabla de arriba registró solo `is-active`, y `active` significa **dos cosas opuestas** que no se
distinguen sin el timestamp. Remedido con el PID como testigo, **9 de 9**:

```
partof-requires   PID 2007→2054 · 2213→2264 · 2423→2473    proceso NUEVO
partof-solo       PID 2658→2699 · 2856→2904 · 3063→3113    proceso NUEVO
```

`PartOf=` **no deja la unidad muda: la reinicia limpia.** Y el diseño se simplifica —
`PartOf=` + `Requires=` + `After=`, **y NO `BindsTo=`**, que gana y deja la unidad `inactive`.

📝 Y el proyecto tenía lo correcto escrito el mismo día en otro documento:
`2026-08-06-recuperacion-tras-apagar-el-rvr.md:100` — *«`PartOf=` propaga el paro y el REINICIO»*.
Se eligió el equivocado porque su tabla parecía medida.

### 3 · ✅ El LED del sensor de color — RESUELTO Y EN EL ROBOT (2026-08-06)

**Este apartado decía lo contrario, y estaba mal.** Se deja el error a la vista porque es la parte
útil.

Lo que decía: *«con el streaming ya configurado, `enable_color_detection` NO HACE NADA — 481
mensajes de `/color`, todos ceros»*. **Esa medida no probaba eso.** El servicio bajo prueba hacía
`enable(True) → leer → enable(False)` en la misma llamada, y 481 mensajes a 12,7 Hz son ~38 s:
casi todos posteriores al apagado. No distinguía las dos hipótesis.

Lo destapó el usuario, recordando el ciclo funcionando en ROS 1. Y el código de ROS 1 lo
respaldaba: servicio `enable_color` (`Atriz_rvr_node.py:331`, registrado en `:1636`) llamado **en
caliente**, con el streaming ya arrancado en `:1313`.

**Remedido** (`mediciones_banco/probar_color_stream_caliente.py`, evidencia 76):

| fase | `/color` no-cero | canal claro |
|---|---|---|
| LED apagado | 0 / 24 | 1 |
| `enable(True)` en caliente | **24 / 24** | **1321** |
| `enable(False)` | 0 / 24 | 1 |

**Y ya está implementado y verificado en el robot**, a través del driver y de rosbridge:

```
servicio  /enable_color   std_srvs/SetBool
/color no-cero :  0 -> 53 -> 0
clear directo  :  1 -> 1320 -> 0
```

🔴 **Lo que la web tiene que saber, y no es evidente:** `/color` **publica `[0,0,0]` cuando el
sensor está apagado — no calla.** (ROS 1 sí callaba: tenía una compuerta `if not color_enabled:
return`.) Así que **la web no puede deducir el estado de si llegan mensajes.** Ver §B.

---

## Las soluciones, en orden de coste

### A · Envolver SLAM y Nav2 en servicios ROS que el driver exponga  🔴 RECHAZADA

> ## 🔴 ESTA PROPUESTA YA HABÍA SIDO TUMBADA CUANDO LA ESCRIBÍ
>
> El panel de cuatro agentes de `2026-08-06-plan-slam-color-arranque.md` (D2, opción **c**) la
> descartó **la misma mañana**, y por seguridad, no por coste. La escribí sin leer ese plan.
>
> **El argumento, verificado en el código:**
>
> ```
> rosbridge_server/websocket_handler.py:233   def check_origin(self, origin) -> bool:
>                                     :234       return True     ← sin condiciones
> ```
>
> rosbridge **no autentica a nadie**, y el driver corre como `sphero`
> (`systemctl show atriz-robot -p User` → `User=sphero`). Así que un servicio ROS que haga
> `systemctl start` necesita polkit, y eso convierte *«cualquiera en la red del aula llama a un
> servicio»* en ***«cualquiera en la red del aula hace que root arranque un proceso»***.
>
> 📌 **Y el resto del apartado sigue siendo útil**, porque los cuatro requisitos que lista
> —callback que no bloquee `/release_emergency_stop`, éxito medido por efecto, Nav2 sin mapa que
> se niegue— valen para *cualquier* mecanismo que se elija. Lo que no vale es el mecanismo.
>
> **Lo que el panel recomienda en su lugar (D2, opción a):** `atriz-slam.service` instalada y
> **NO habilitada**, y **A10 espera**. Honesto: la web sigue sin poder arrancar SLAM, y se dice.

Cuatro servicios nuevos (`/arrancar_slam`, `/parar_slam`, `/arrancar_nav`, `/parar_nav`) que el
driver registre junto a los 19 que ya tiene, y cuatro entradas más en la lista blanca.

Por dentro, `systemctl start|stop` de dos unidades: `atriz-slam.service` (nueva) y
`atriz-nav.service` (ya existe).

**Lo que hay que respetar, y no es negociable:**

- 🔴 **Los servicios del driver comparten `MutuallyExclusiveCallbackGroup`**: un callback largo
  **bloquea los otros 18**. Arrancar Nav2 tarda segundos, así que **no puede esperarse dentro del
  callback** — tiene que lanzarse y volver, y el estado consultarse aparte.
  ⚠️ **CORREGIDO el 2026-08-06 (noche): aquí ponía «bloquea `/release_emergency_stop`», y es
  FALSO.** La parada vive en `g_cmd` (`rvr_driver_node.py:647-649`), no en `g_srv`, que se define
  después (`:658`). El límite es real; el sujeto no era ese.
- 🔴 **`systemctl start` desde el driver exige permisos.** El servicio corre como `sphero`. Hace
  falta una regla de `polkit` acotada a esas dos unidades, **no** un sudo sin contraseña general.
- 🔴 **El éxito es que arranque, no que la llamada vuelva.** El servicio no puede devolver
  `success=true` porque `systemctl` devolvió 0: hay que comprobar el efecto —`/map` publicando
  para SLAM, `/navigate_to_pose` disponible para Nav2— o devolver «lanzado, mira el estado».
- 🔴 **Nav2 sin mapa falla en bucle.** El servicio debe negarse y decirlo, no intentarlo.

**Lo que la web necesita para pintarlo:** un topic de estado. `/estado_robot` ya existe y se
publica a 1 Hz — añadirle dos campos (`slam_activo`, `nav_activo`) es más barato que un topic
nuevo, y llega por un camino que la web ya lee.

### B · ✅ El LED del color — HECHO en el robot. Lo que falta es la web

**El botón «sesión de medición» ya se puede construir.** Dos servicios, los dos en la lista blanca
de rosbridge (`robot.launch.py:354`):

| servicio | tipo | qué hace |
|---|---|---|
| `/enable_color` | `std_srvs/SetBool` | `data:true` enciende el LED y `/color` da valores reales; `data:false` lo apaga |
| `/get_rgbc_sensor_values` | `atriz_rvr_msgs/GetRGBCSensorValues` | lectura puntual en crudo (R, G, B, claro) |

**Van los dos o no sirve ninguno:** sin el LED no hay lectura, y el LED solo lo enciende
`enable_color`.

El botón de arrancar llama a `enable_color(true)`; el de parar, a `enable_color(false)`. Entre
medias, `/color` a 12,7 Hz o consultas puntuales, lo que prefiera la interfaz.

🔴 **Tres cosas que no se pueden saltar:**

1. **Un botón de PARAR tan visible como el de arrancar.** El LED gasta batería mientras siga
   encendido, y son 16 robots. El driver lo apaga al cerrar (`_apagar_rvr`), pero eso solo cubre
   el caso de que el driver muera.
2. ✅ **RESUELTO: `color_activo` en `/estado_robot`** (2026-08-06 tarde). `EstadoRobot` pasa a 8
   campos. **Y ya no es «más honesto» sino necesario**, porque la luz **se apaga sola**: un flag
   local pintaría el botón encendido sobre un sensor a oscuras.
   → 🔴 **El testigo del botón es `color_activo`, no `/color`.** Esperar a que `/color` deje de
   ser `[0,0,0]` sirve para encender, pero falla para apagar y sobre negro.
3. **No fiarse del `success`.** Este sensor ya devolvió `success=True` sobre oscuridad dos veces.
   El servicio lleva ahora un `sleep(0.1)` dentro para que eso no pueda volver a pasar, pero la
   web debe confirmar con el dato.

📝 **Descartadas, y conviene que conste por qué:**
- **B1 (reiniciar el driver con el parámetro puesto)** — 🔴 además de tirar 25 s de telemetría,
  **el reinicio BAJA LA PARADA DE EMERGENCIA**: `self._parada_emergencia = False` en el
  constructor (`rvr_driver_node.py:266`). Un robot que un humano detuvo a propósito volvería a
  aceptar `cmd_vel_raw`. Es un problema de seguridad, no de comodidad.
- **B2 (reordenar el streaming, `stop → enable → start`)** — medido, funciona igual de bien
  (fase 3 del banco), pero es innecesario: el camino barato basta y no abre hueco de telemetría.

### C · El agente de sesión (Fase B) — la solución general, y está bloqueada

Es lo que resuelve esto y el terminal del alumno a la vez. Depende de la **F0**: el aislamiento de
clientes del AP del aula, que necesita estar en el laboratorio. Mientras siga sin medir, no se
puede construir sobre él.

---

## Y lo que hay que arreglar aunque no se haga nada de lo anterior

🔴 **Que el robot vuelva entero tras un apagón del RVR.** Hoy vuelve `atriz-robot` y nada más.
Con 16 robots y alumnos poniendo a cargar, esto va a pasar constantemente. Y no basta con
`enable`: la unidad de Nav2 exige mapa, y la de SLAM no existe.

> ## ✅ ESTO YA ESTABA DECIDIDO, Y LO PUSE COMO PENDIENTE
>
> **Decidido con el usuario el 2026-08-03** y escrito en
> [`03_operacion/ARRANQUE_NAVEGACION.md`](../../03_operacion/ARRANQUE_NAVEGACION.md):
>
> | | |
> |---|---|
> | **Nav2** | unidad instalada y **NO habilitada**. *«No sobrevive a un reinicio… es la decisión del usuario y encaja con la línea del proyecto: nada de estado silencioso»* |
> | **SLAM** | **a mano**, para hacer mapas: *«tarea de administrador, no de operación»* |
>
> El dato que la decidió: **la Pi se alimenta del USB del RVR**, la autonomía medida es **~2 h**
> contra clases de **2-3 h**, y Nav2 son **~58 % de un núcleo**. Con la salvedad que el propio
> documento ya escribe: **cuánto cuesta en batería ese 58 % no lo sabe nadie** — la dirección está
> clara, la magnitud no.
>
> 🔴 **Que yo la listara como pendiente es el fallo que `ESTADO_ACTUAL.md` documenta en su primera
> sección:** el 2026-08-05 se listaron como pendientes cuatro cosas ya hechas, citando un fichero
> que se había quedado atrás. Aquí ha pasado otra vez, con un documento de decisión que llevaba
> tres días escrito. **Antes de dar algo por pendiente, cruzar con la evidencia.**
>
> ⚠️ **Lo que SÍ queda abierto, y es un matiz del panel de agentes (D2, razón 3):** el argumento de
> Nav2 **no traslada a SLAM**. Nav2 no se habilita porque cuesta 58 % de núcleo; **SLAM cuesta
> 4,8 %, doce veces menos**. La conclusión puede seguir siendo la buena, pero **por otras razones**,
> y esas no están escritas. Eso es lo que merece una decisión, no lo de abajo.

📌 ~~**Decisión que corresponde al usuario, no a la web:**~~ si Nav2 y SLAM deben arrancar **solos** al
encender (y pagar la batería), o **solo cuando la web lo pida** (y entonces hace falta A).

## Lo que le toca al PC

1. **El del color YA SE PUEDE HACER**, y es el más fácil de los tres: `/enable_color`
   (`std_srvs/SetBool`) y `/get_rgbc_sensor_values` están en la lista blanca y verificados por
   rosbridge. Los de SLAM y Nav2 siguen sin existir en ninguna capa.
   → Hay que añadir los dos a `contrato.ts` con sus tipos, o el cliente **lanzará antes de mandar
   nada** y `comprobar_contrato.mjs` seguirá en rojo.
2. **Si se implementa A**, la web necesita: cuatro servicios en `contrato.ts` + sus tipos, y dos
   campos nuevos en `EstadoRobot` para pintar el estado sin sondear.
3. **El estado de arranque no es booleano.** «Arrancando» dura segundos y hay que pintarlo: si la
   interfaz solo tiene encendido/apagado, el alumno pulsará dos veces.
