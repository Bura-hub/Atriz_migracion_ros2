# Cómo se asegura rosbridge en los 16 robots

> **El problema.** `robot.launch.py` levanta `rosbridge_websocket` en el **9090, sin autenticación
> ni TLS, escuchando en todas las interfaces**, y expone los 18 servicios del driver — incluido
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

### Fase A — Lista blanca (inmediata)

Cuatro parámetros en `robot.launch.py`. Cero código nuevo, cero cambios en el cliente.

| Parámetro | Contenido |
|---|---|
| `topics_sub_glob` | lo que la web **lee**: `/odom`, `/scan`, `/imu`, `/battery_state`, `/motor_status`, `/encoders`, `/color`, `/map`, `/tf`, `/tf_static`, `/collision_monitor_state`, `/amcl_pose` |
| `topics_pub_glob` | lo que la web **manda**: **solo** `/cmd_vel_raw`, `/emergency_stop`, `/initialpose` |
| `services_glob` | **solo** `/start_scan`, `/stop_scan`, `/release_emergency_stop`, y los cuatro de LED (`/set_led_rgb`, `/set_multiple_leds`, `/set_leds`, `/trigger_led_event`) para que la web identifique robots encendiéndolos |
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
`set_ir_evading`, `set_ir_mode`, `send_infrared_message`, `set_drive_parameters`, `set_pos_and_yaw`
— y, lo más importante, **publicar directamente en `/cmd_vel`**, que hoy salta el
`collision_monitor` entero.

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

| Requisito | Fase A | Fase B |
|---|---|---|
| 3 · cerrar `raw_motors` y compañía | ✅ | ✅ |
| 2 · que nadie sin permiso mueva un robot | ❌ | ✅ |
| 1 · que un alumno no mueva el robot de otro | ❌ | ✅ |
| 4 · que no se pueda espiar la telemetría | ❌ | ✅ (TLS) |

⚠️ **La fase A sola NO levanta el pendiente que bloquea la Fase 5.** Cierra el agujero más grave y
reduce la superficie sobre la que nacerá el cliente, pero **cualquiera en el aula seguirá pudiendo
teleoperar cualquier robot** hasta que esté la B. Conviene que eso esté dicho, y no que la lista
blanca dé una sensación de resuelto.

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
