# Cómo se asegura rosbridge en los 16 robots

> ✅ **ESTADO (2026-08-15): la Fase B está DESPLEGADA en rvr-01** — rosbridge exige testigo
> Ed25519 desde la red y exime a `127.0.0.1` (§ «REDISEÑADA EL 2026-08-15», evidencia 124). El
> párrafo siguiente describe el problema TAL COMO ERA cuando se diseñó esto, y sigue siendo
> cierto para un rosbridge sin envolver — o sea, para los otros 15 hasta que les llegue.

> **El problema.** `robot.launch.py` levanta `rosbridge_websocket` en el **9090, sin autenticación
> ni TLS, escuchando en todas las interfaces**, y expone **doce** de los 19 servicios del driver más los **dos** del supervisor de navegación — incluido
> `raw_motors`, que se salta el `collision_monitor` y el watchdog y **no tiene corte automático**.
> Cualquiera en la red del aula puede abrir un WebSocket y mover un robot. Está verificado de
> extremo a extremo: un navegador de otra subred abrió `ws://rvr-01.local:9090` y **encendió los
> faros del robot** (evidencia 39).
>
> Era el primero de los cuatro pendientes que bloquean la Fase 5, y **había que decidirlo antes de
> escribir el cliente porque cambia su arquitectura**. Diseñado y acordado el **2026-08-02**.

---

## Lo que se descubrió al explorarlo, y que cambia el planteamiento

**🔴 rosbridge 2.7.0 en Jazzy NO TIENE AUTENTICACIÓN. No es que esté sin configurar: no existe.**

- `rosauth` no es dependencia (`/opt/ros/jazzy/share/rosbridge_server/package.xml`) ni está instalado
- No hay parámetro `authenticate` ni equivalente en `SERVER_PARAMETERS` / `PROTOCOL_PARAMETERS`
  (`rosbridge_websocket.py:60-103`)
- La capacidad `Authentication` **no está** en el protocolo (`rosbridge_protocol.py:32-45`)
- Y `check_origin()` **devuelve `True` incondicionalmente**
  (`rosbridge_server/websocket_handler.py:233-234`): cualquier página que cargue el navegador de
  cualquiera puede abrir el WebSocket contra el robot

→ **Esto elimina «token en el propio WebSocket»**, que era una de las tres opciones que el proyecto
tenía escritas. No se puede hacer con rosbridge tal cual.

**Lo que sí soporta**, y es sobre lo que se construye este diseño:

| Parámetro | Para qué | Referencia |
|---|---|---|
| `address` | atarlo a `127.0.0.1` | `rosbridge_websocket.py:63`, usado en `:237` |
| `certfile` / `keyfile` | TLS (ambos o ninguno) | `:66-67`, `:234-239` |
| `topics_sub_glob`, `topics_pub_glob` | lista blanca de lectura y escritura | `:96-97` |
| `services_glob`, `actions_glob` | lista blanca de servicios y acciones | `:98-99` |
| `params_glob` | qué parámetros deja tocar `rosapi` | leído por `rosapi/glob_helper.py:48` |

**🔴 Y un hallazgo de propina: no hay cortafuegos, aunque lo parezca.** `systemctl is-active ufw`
dice **`active`**, pero `/etc/ufw/ufw.conf` tiene `ENABLED=no` y `/usr/lib/ufw/ufw-init:36-38` sale
con 0 sin cargar una sola regla. Es un `oneshot` con `RemainAfterExit`.
📝 **Octava vez en este proyecto que algo informa de éxito sin haber hecho nada.** No se apoya
ninguna parte de este diseño en el cortafuegos.

---

## Requisitos, decididos con el usuario

**Dónde se usa:** solo desde dentro del aula, red cerrada. No hay acceso desde internet.

**Qué hay que impedir**, los cuatro:

1. Que un alumno mueva **el robot de otro** → exige **identidad por usuario**, no una clave compartida
2. Que alguien sin permiso mueva **cualquier** robot
3. Que se llame a **`raw_motors` y similares** → se cierra con lista blanca, sin autenticación
4. Que se pueda **espiar la telemetría** → exige cifrado

---

## La arquitectura

Dos fases independientes. **La A no toca el cliente y se aplica ya; la B llega con la Fase 5.**

### Fase A — Lista blanca ✅ APLICADA 2026-08-02

Cuatro parámetros en `robot.launch.py`. Cero código nuevo, cero cambios en el cliente.

| Parámetro | Contenido |
|---|---|
| `topics_sub_glob` | lo que la web **lee**: `/odom`, `/scan`, `/imu`, `/battery_state`, `/motor_status`, `/encoders`, `/color`, `/map`, `/tf`, `/tf_static`, `/collision_monitor_state`, `/amcl_pose` |
| `topics_pub_glob` | lo que la web **manda**: **solo** `/cmd_vel_raw`, `/emergency_stop`, `/initialpose` |
| `services_glob` | **DOCE**: `/start_scan`, `/stop_scan`, `/release_emergency_stop`, **`/set_pos_and_yaw`**, los cuatro de LED (`/set_led_rgb`, `/set_multiple_leds`, `/set_leds`, `/trigger_led_event`), la sesión de color (`/enable_color`, `/get_rgbc_sensor_values`) y los botones de navegación (**`/pedir_slam`**, **`/pedir_nav`**, del `supervisor_navegacion` — NO del driver) |
| | 🔴 **`set_pos_and_yaw` se añadió el 2026-08-02; la primera versión de este diseño lo dejaba FUERA.** Es el **único** modo de poner la odometría a cero entre alumnos: `reset_odom` no existe, y lo que hay es `set_pos_and_yaw(0,0,0)`, que llama a `reset_locator_x_and_y()` y pone `_yaw_offset = None`. Sin él la web no puede resetear entre sesiones. Solo acepta (0,0,0), así que exponerlo es seguro. Lo destapó **cruzar este documento con la evidencia 34** — ningún fichero lo decía por sí solo |
| `actions_glob` | `/navigate_to_pose` |
| `params_glob` | `"[]"` — **nada**. La web no cambia parámetros |

**Sintaxis, que no es obvia** (`rosbridge_websocket.py:115-126`): son **cadenas** que contienen una
lista estilo Python con patrones **`fnmatch`**, no regex.

- `""` (el defecto, y lo que hay hoy) → **sin filtro, todo permitido**
- `"[]"` → **filtra y no casa nada: todo denegado**
- `"['/odom', '/scan']"` → lista blanca

📝 `services_glob`, si no es `None`, **se le añade `/rosapi/*` automáticamente**
(`rosbridge_websocket.py:141-142`).

**Qué cierra:** `raw_motors`, `move_timed`, `move_to_pose`, `move_to_pos_and_yaw`,
`set_ir_evading`, `set_ir_mode`, `set_drive_parameters`
— y, lo más importante, **publicar directamente en `/cmd_vel`**, que hoy salta el
`collision_monitor` entero.

> ### 🔴 ESTE APARTADO SE CONTRADECÍA A SÍ MISMO — corregido el 2026-08-16
>
> Decía «**DOCE**» servicios y listaba **`send_infrared_message`** y
> **`set_pos_and_yaw`** entre lo que la lista *cierra*. Las tres cosas eran falsas
> contra el launch de hoy: son **TRECE**, y los dos servicios están **DENTRO** —
> `set_pos_and_yaw` aparecía además como permitido tres líneas más arriba, en su
> propia fila de la tabla, o sea que el documento se desmentía en la misma página.
>
> Lo destapó una auditoría del código el 2026-08-16, al ir a contestar si se puede
> conducir con el barrido apagado.
>
> **La lista literal, copiada de `atriz_rvr_bringup/launch/robot.launch.py:383-405`:**
>
> ```
> /start_scan · /stop_scan · /release_emergency_stop · /set_pos_and_yaw ·
> /set_led_rgb · /set_multiple_leds · /set_leds · /trigger_led_event ·
> /enable_color · /get_rgbc_sensor_values · /pedir_slam · /pedir_nav ·
> /send_infrared_message
> ```
>
> 📌 **La fuente autoritativa es el launch, no este fichero.** Un número escrito a
> mano —«DOCE»— envejece en cuanto alguien añade una entrada, y nadie vuelve a
> contarlo. Es la misma forma que este proyecto persigue en el código: una
> afirmación sin ejecutor detrás.
>
> ⚠️ Y hay un hueco que conviene saber: `comprobar_contrato.mjs` compara
> `topics_sub_glob`, `topics_pub_glob` y `services_glob` contra el launch, pero
> **NO `actions_glob`**, porque ese va inline sin constante que extraer
> (`atriz-lab/frontend/src/lib/rosbridge/contrato.ts:101-105`). Es el único de los
> cuatro sin verificación automatizada.

### 🔴 Y LO QUE LA LISTA BLANCA **NO** CIERRA: EL TALLER

La lista blanca gobierna **rosbridge (9090)**. El Taller es **otro puerto y otro
proceso**: `atriz-agente` en el **9443** ejecuta Python del alumno con `pty.fork()`
como usuario `sphero`, y desde ahí `import rclpy` alcanza `raw_motors`,
`move_timed` y `set_ir_mode` — **saltándose el `collision_monitor`**, que es justo
lo que esta lista cierra para el navegador.

No es un descubrimiento: lo dice el propio agente en
`Atriz_rvr/scripts/agente/README.md:80-84` — «**No es una frontera de seguridad**»
— y lo repite la web en `PanelTerminal.tsx:33-37`.

📌 **Consecuencia práctica, y es la que importa en el aula:** la respuesta a «¿se
puede mover el robot con el LIDAR apagado?» es **sí, pero no por la pantalla de
conducir**. Desde el 2026-08-16 esa pantalla lo dice en vez de callarlo: quien
tenga un LIDAR roto encuentra la salida, con su advertencia de que ahí no hay capa
de seguridad.

**Y se levanta `rosapi_node`**, que hoy no corre. Sin él, `ros.getTopics()`, `getServices()` y
`getTopicType()` de roslibjs **se cuelgan sin error**, que es una trampa documentada. Se levanta
con `params_glob: "[]"` para que no deje tocar parámetros.

### 🔴 La trampa que obliga a verificar de forma explícita

**rosbridge deniega EN SILENCIO.** Registra un `warn` en su log y hace `return`; **no manda
respuesta de error al cliente** (`capabilities/call_service.py:109-113`, `publish.py:96-99`,
`subscribe.py:296-299`).

→ Una lista blanca mal puesta **se manifiesta como «la web no responde»**, no como un fallo. Es
exactamente la clase de error que este proyecto lleva pagando toda la migración.

**Por eso la fase A no está terminada hasta que exista la verificación**, y la verificación tiene
que comprobar las dos direcciones:

- 🔴 que `raw_motors` y un `publish` a `/cmd_vel` **sean rechazados** (si pasan, la lista no sirve)
- ✅ que `/odom`, `cmd_vel_raw` y `/start_scan` **sigan funcionando** (si no, hemos roto la web)

Va en tres sitios: una herramienta nueva de banco, una comprobación en `verificar_robot.sh`, y la
fase **F8** de la prueba de aceptación.

### 🔴 REDISEÑADA EL 2026-08-15: la Fase B NO es un proxy (evidencia 124)

Lo de abajo se conserva porque explica el problema, pero **el proxy no se
construye**. Al leer el fuente de rosbridge en la Pi apareció que la clase del
manejador se importa **por nombre**:

```
rosbridge_websocket.py:54   from rosbridge_server import ... RosbridgeWebSocket
rosbridge_websocket.py:221  handlers = [(r"/", RosbridgeWebSocket), ...]
```

así que basta con parchear sus métodos y ejecutar el nodo original con `runpy`.
`atriz_rvr_bringup/scripts/atriz_rosbridge.py`, ~250 líneas con sus comentarios.

| | proxy (lo planeado) | parche en el sitio (lo hecho) |
|---|---|---|
| ruta de datos | 🔴 **un salto de Python a 80,7 kB/s por robot** | **cero** |
| puerto / unidad | uno nuevo de cada | ninguno |
| `address: 127.0.0.1` | imprescindible | innecesario |
| TLS | había que implementarlo | `certfile`/`keyfile`, ya soportados |

🔴 Y el proxy **contradecía en silencio la Decisión 2 de `ARQUITECTURA.md`**:
este documento afirmaba que «los datos siguen yendo robot → navegador directos»,
y con un relevo eso dejaba de ser cierto dentro de la Pi.

✅ **Verificado contra rvr-01, 8/8** (puerto 9091, sin tocar el 9090 de
producción): 4401 sin testigo · 4401 sin subprotocolo · 4403 firma mala · 4404
robot ajeno · y los tres controles positivos, incluido `/odom` fluyendo.
El requisito 1 queda demostrado: el robot sabe **quién** entra.

⏳ **Y NADA ESTÁ DESPLEGADO**: `robot.launch.py` sigue lanzando el rosbridge
normal a propósito. Falta el cliente (F2), el doble (F3), las herramientas y el
verificador (F4) y TLS (F5). Detalle y lo que salió mal: **evidencia 124**.

---

### Fase B — Proxy autenticador en cada robot (con la Fase 5)

```
navegador ──wss://rvr-NN.local:9443──►  proxy (en la Pi)  ──ws://127.0.0.1:9090──► rosbridge
                  con JWT                valida y filtra
```

- `rosbridge` pasa a **`address: 127.0.0.1`**: deja de ser alcanzable desde la red
- El proxy valida el **JWT que emite FastAPI** y termina el TLS
- 🔑 **Y de aquí sale el requisito 1:** el proxy comprueba que el token dice **este robot**. Un
  alumno con token para el robot 3 no puede abrir el 7. El robot **no necesita saber nada de
  usuarios ni de reservas**: solo verificar una firma y comparar un número

**Por qué el proxy va en el robot y no en el centro.** Un proxy central daría lo mismo en identidad,
pero **los 10.3 Mbit/s medidos de los 16 robots atravesarían FastAPI** — que es exactamente lo que
la Decisión 2 evitó a propósito («De qué NO: estar en la ruta de los datos en vivo»,
`ARQUITECTURA.md:78`). Con el proxy en cada Pi, **los datos siguen yendo robot → navegador
directos** y la Decisión 2 se mantiene intacta.

⏳ **TLS: decidido posponer el cómo.** La fase A no lo necesita. La elección entre CA propia del
laboratorio y certificado autofirmado por robot se toma en la fase B, con los datos delante —
sabiendo ya que lo autofirmado obliga al alumno a aceptar una excepción **en cada uno de los 16
robots**, y que eso educa a dar a «aceptar siempre».

---

## Qué cubre cada fase, sin adornos

| Requisito | Fase A | Fase B | estado real |
|---|---|---|---|
| 3 · cerrar `raw_motors` y compañía | ✅ | ✅ | ✅ desde 2026-08-02 |
| 2 · que nadie sin permiso mueva un robot | ❌ | ✅ | ✅ **en rvr-01 desde el 2026-08-15** |
| 1 · que un alumno no mueva el robot de otro | ❌ | ✅ | ✅ **en rvr-01**: el testigo lleva el número y el robot lo compara (cierre `4404`) |
| 4 · que no se pueda espiar la telemetría | ❌ | ✅ (TLS) | ⏳ **abierto**: `certfile`/`keyfile` están soportados, falta decidir certificados |

~~⚠️ **La fase A sola NO levanta el pendiente que bloquea la Fase 5.**~~ Cerraba el agujero más
grave y reducía la superficie, pero **cualquiera en el aula seguía pudiendo teleoperar cualquier
robot**.

✅ **RESUELTO EN rvr-01 EL 2026-08-15** (evidencia 124): rosbridge exige un testigo firmado, y el
robot **sabe quién entra**. Medido en las dos direcciones y desde los dos lados.

⏳ **Lo que sigue abierto**, y conviene no darlo por cerrado:
- **los otros 15 robots**: llega con la imagen dorada, no está desplegado;
- **el requisito 4 (TLS)**: el testigo y toda la telemetría **viajan en claro**;
- 🔴 **quien corre DENTRO de la Pi sigue teniendo más autoridad que la web** —el Taller ejecuta
  código del alumno como `sphero`, que alcanza `raw_motors` con `rclpy`—. La exención de
  `127.0.0.1` no lo empeora, pero tampoco lo arregla, y no lo arregla nada de la Fase B.

---

## Ficheros

| Fichero | Qué cambia |
|---|---|
| `Atriz_rvr/atriz_rvr_bringup/launch/robot.launch.py` | los cinco `*_glob` en el nodo de rosbridge; levantar `rosapi_node` |
| `atriz_migracion/00_auditoria/evidencia/mediciones_banco/probar_lista_blanca.py` | **nuevo** — cliente WebSocket que comprueba que lo prohibido se rechaza y lo permitido funciona |
| `atriz_migracion/scripts/verificar_robot.sh` | comprobación nueva: la lista blanca está puesta y **deniega de verdad** |
| `atriz_migracion/scripts/prueba_aceptacion.py` | F8 comprueba lo mismo contra el robot |
| `atriz_migracion/03_operacion/ARQUITECTURA.md` | la decisión, y retirar «token en el WebSocket» como opción |
| `CLAUDE.md`, `TRASPASO.md`, `CHANGELOG.md` | el estado del pendiente |

---

## Verificación

Nada se da por bueno sin ejecutarlo. En orden:

1. **Lo prohibido se rechaza.** Llamar a `raw_motors` por WebSocket y comprobar que **no hay
   respuesta** y que el log de rosbridge registra el `warn`. Igual publicando en `/cmd_vel`.
   🔴 **Y comprobar el efecto físico: el robot NO se mueve.** Que no llegue respuesta no prueba que
   la orden no pasara — este proyecto tiene documentado que un `success` no prueba nada, y lo
   recíproco tampoco.
2. **Lo permitido sigue funcionando.** Suscribirse a `/odom` y recibir datos; publicar en
   `cmd_vel_raw` y ver movimiento; llamar a `/start_scan` y ver `/scan`.
3. **`rosapi` responde.** `ros.getTopics()` desde un cliente, y que **no** deje leer parámetros.
4. **La página de diagnóstico sigue valiendo.** `03_operacion/probar_conexion_web.html` usa
   `/set_led_rgb`, que está en la lista: debe seguir encendiendo los faros.
5. **Y el caso que más fácil se olvida:** que un robot **recién arrancado** aplique la lista. Se
   comprueba tras un reinicio, no solo tras relanzar el launch a mano.


---

## ✅ Fase A aplicada y verificada — 2026-08-02

`robot.launch.py` pasó de `{'port': 9090, 'use_sim_time': False}` a llevar los cinco `*_glob`, y
se levantó `rosapi_node`, que no corría.

**El log del servidor confirma las denegaciones** — que es la única prueba posible, porque
rosbridge no responde a un `publish`:

```
WARN  No match found for service, cancelling service call for: /raw_motors
WARN  No match found for service, cancelling service call for: /move_timed
WARN  No match found for topic, cancelling advertisement of: /cmd_vel
WARN  No match found for topic, cancelling publish to: /cmd_vel
```

Y lo permitido sigue vivo: `/start_scan` y `/set_pos_and_yaw` **responden y aceptan**, `rosapi`
responde.

### 🔴 Dos fallos de la propia herramienta de verificación, encontrados AL USARLA

1. **Su control dependía de `/odom`, que no llega con el RVR apagado cargando** — un estado que
   con 16 robots será cotidiano. Abortaba correctamente («no concluye nada») pero eso la dejaba
   inservible justo cuando más cómodo es tocar la configuración.
   → Control cambiado a **`rosapi`**, que responde sin el RVR. `/odom` se conserva como control
   adicional, y su ausencia **degrada** la prueba en vez de abortarla.

2. 🔴 **Contaba un error como éxito.** Miraba solo si llegaba *una* respuesta, y dio ✅ sobre un
   `set_pos_and_yaw` que había respondido con `NonexistentFieldException`: los campos que le
   mandaba estaban mal (`{'x','y','yaw'}` planos, cuando el servicio quiere
   `{'position': {...}, 'yaw'}`).
   **La herramienta que existe para cazar falsos positivos tenía uno dentro.**
   → Ahora distingue un `service_response` con `result` bueno de un `status` con `level: error`.

📝 Los dos salieron **de ejecutarla, no de leerla**. Es el argumento de que la verificación forme
parte de la fase y no sea un paso opcional al final.

### ✅ La Fase A queda CERRADA — comprobado con el efecto físico

Se mandó `raw_motors` **al 30 % (speed 77, modo 1)** por WebSocket, igual que lo haría alguien en la
red del aula, con el RVR encendido y espacio despejado:

```
antes:   x=-0.0620  y=-0.0057
después: x=-0.0620  y=-0.0057
DESPLAZAMIENTO: 0.00 cm
```

Y el log registró las dos denegaciones. **Evidencia 53.**

📝 **Por qué esta prueba hacía falta:** todo lo demás se apoyaba en que rosbridge **no responde**, y
**que no llegue respuesta NO prueba que la orden no pasara** — el recíproco de la trampa que este
proyecto lleva seis veces documentada. `raw_motors` no publica en ningún topic: habla al RVR **por
el puerto serie**, así que la única prueba concluyente es el robot quieto. Y es el peor caso
posible: se salta el `collision_monitor` **y** el watchdog, y **no tiene corte automático**.
