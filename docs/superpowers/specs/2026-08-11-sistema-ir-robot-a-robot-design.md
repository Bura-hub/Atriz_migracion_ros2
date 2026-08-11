# Rediseño del sistema de infrarrojos robot-a-robot

**Fecha:** 2026-08-11 · **Robots:** rvr-01 y rvr-02 · **Evidencia base:** `00_auditoria/evidencia/99_el_ir_robot_a_robot_y_un_agujero_de_la_parada.txt`

---

## Por qué existe este documento

El IR del proyecto se portó de ROS 1 sin comprobarlo, y al probarlo con dos robots por primera vez
—el 2026-08-11, porque hasta ese día solo había uno— resultó que **la mitad nunca había
funcionado** y que el tipo de mensaje **describe algo que el robot no envía**.

👤 Decisión del usuario: rediseñarlo entero en vez de parchear la clave que falla.

### Lo que está MEDIDO, y es la base de todo lo demás

| hecho | cómo se sabe |
|---|---|
| El firmware **sí** entrega la notificación IR | `PRIMER mensaje IR recibido. Payload CRUDO: {'infrared_code': 3}` en rvr-01, con rvr-02 emitiendo el código 3 |
| El payload trae **UNA sola clave**: `infrared_code` | el mismo volcado, y `sensor.py:211-218` declara un único `output` |
| `broadcasting` · `following` · `evading` funcionan | 👤 comportamiento físico confirmado por el usuario con los dos robots |
| `get_bot_to_bot_infrared_readings` **responde** | evidencia 41: `{'sensor_data': 4294967295}` = `0xFFFFFFFF` = los cuatro sensores vacíos, correcto con un solo robot |
| Existe `get_active_control_system_id()` → **8** mientras el robot conduce por IR | `drive.py:684`, `drive_enums.py:79` |
| La lectura direccional **caduca en 1 s** | `referencia_sdk/sensor.md:54` |
| 4 emisores (frontal/izq/der/trasero), 4 receptores en las esquinas | `sensor.md:213-224`, `:45-47` |
| `far_code` = 3 m o más · `near_code` = menos de 1 m | `sensor.md:69-74` |
| Las intensidades encendidas deben compartir nivel | `sensor.md:213` |

### Lo que está ROTO

1. **`InfraredMessage.msg` tiene cuatro campos que el firmware nunca envía.** `front/left/right/rear_strength` son parámetros del **envío**; la recepción no los trae.
2. **El extractor del handler no busca la clave real.** Busca `Code`/`code`/`InfraredCode`; la real es `infrared_code`, así que `/infrared_messages` publica `code=0` siempre. Introducido el mismo 2026-08-11.
3. **ROS 2 perdió la validación de rangos que ROS 1 sí tenía** en `set_ir_evading` y en los códigos de modo. El SDK tampoco valida: el único sitio de todo el SDK con el límite `0-64` es un helper que el driver no usa.
4. **Nada en ROS sabe que el robot conduce por IR.** `following`/`evading` son modos del firmware: no pasan por `cmd_vel`, el `collision_monitor` no los ve y `/estado_robot` no los menciona.
5. **La detección direccional no la usa nadie**, pese a responder.
6. **Cero API para el alumno.** Ni en `atriz.py`, ni en las once prácticas, ni en `API_LABORATORIO.md`.
7. **Cero pruebas válidas para ROS 2.** Las de `testing_scripts/` son de ROS 1 y usan nombres que ya no existen.
8. **Todo el IR está fuera de la lista blanca de rosbridge.**

### Dos afirmaciones falsas que este rediseño retira

- *«ROS 1 publicaba los dos topics con los mismos datos»* (driver `:3159`, CHANGELOG). **Falso:** `/ir_messages` se anunciaba y **nunca se publicaba**, y `/infrared_messages` salía de un handler que hacía `datos['InfraredMessage']['Code']` contra `{'infrared_code': N}` — `KeyError` en la primera línea. **El IR de ROS 1 nunca recibió nada.**
- *«`get_bot_to_bot_infrared_readings` devuelve basura»*. **Falso:** `0xFFFFFFFF` es el valor correcto de «cuatro sensores vacíos».

---

## Arquitectura

**Evento y estado separados**, que es como este proyecto ya resolvió el mismo problema con
`/estado_robot`: *un topic mudo no distingue el silencio del fallo*.

```
   ┌───────────── driver (rvr_driver_node) ─────────────┐
   │                                                     │
   │  notificación 0x2C ──► _h_ir_mensaje ──► /infrared_messages   (evento)
   │                                                     │
   │  sondeo 1 Hz ─┬─ get_bot_to_bot_infrared_readings   │
   │               ├─ get_active_control_system_id       ├─► /estado_ir  (estado)
   │               └─ modo y códigos actuales            │
   │                                                     │
   │  servicios: set_ir_mode · set_ir_evading · send_infrared_message
   └─────────────────────────────────────────────────────┘
            ▲                                   ▲
            │                                   │
      atriz.py (alumno)                   rosbridge (web)
```

**Por qué DOS topics y no uno:** el estado va a 1 Hz y el dato del firmware **caduca en 1 s**; con
solo el estado se perderían mensajes. Y por qué no solo el evento: un evento no dice qué ven mis
sensores **ahora**, ni si estoy conduciendo por IR.

---

## Componentes

### 1 · `InfraredMessage.msg` — se rehace

```
std_msgs/Header header      # cuándo llegó: es lo que caduca
uint8 code                  # 0-7
```

🔴 **Cambio incompatible, y es el momento barato de hacerlo:** no lo consume nadie — la web no lo
tiene en la lista blanca y ninguna práctica lo usa.

### 2 · `EstadoIR.msg` — nuevo

```
std_msgs/Header header

uint8   sensor_0            # los cuatro receptores. 255 = vacío · 0-15 = código visto
uint8   sensor_1
uint8   sensor_2
uint8   sensor_3
bool    lecturas_validas    # false si el sondeo está apagado o falló
float32 antiguedad_lectura_s

uint8   ultimo_codigo
bool    hay_mensaje         # false si no ha llegado ninguno desde el arranque
float32 antiguedad_mensaje_s

string  modo                # broadcasting · following · evading · off
uint8   far_code
uint8   near_code

bool    conduciendo_por_ir  # get_active_control_system_id() == 8
```

🔴 **Los sensores se llaman `sensor_0..3` a propósito.** La máscara que asigna cada byte a una
esquina está documentada como *«on BOLT»* (`sensor.md:47`) y **nadie ha comprobado que el RVR la
use igual**. Ponerles nombre de esquina hoy sería inventarse la orientación del robot. **La prueba
de viabilidad los bautiza**, y si discriminan, se renombran con lo medido.

⚠️ **Las antigüedades no son adorno.** Un `255` significa «nadie» o «hace demasiado que no
consulto», y sin la antigüedad no se distinguen.

### 3 · Driver: el sondeo

Un temporizador a **`ir_sondeo_hz`** (parámetro, por defecto `1.0`, **`0.0` lo apaga**) que:

1. llama a `get_bot_to_bot_infrared_readings()` y desempaqueta los cuatro bytes,
2. llama a `get_active_control_system_id()`,
3. publica `/estado_ir`.

⚠️ **Coste a medir, no a suponer:** es un comando más por segundo en el mismo enlace serie que
lleva la telemetría a 16,7 Hz. **Antes de adoptarlo se mide el ritmo de `/odom` con el sondeo
encendido y apagado.** Este proyecto ya midió una vez que a 50 ms el streaming ni arranca.

### 4 · Driver: el handler del evento

`_h_ir_mensaje` lee **`infrared_code`**, que es la clave real, y publica `/infrared_messages` con
`header.stamp`. Se conserva el volcado del primer payload al log: es lo que destapó el problema.

### 5 · Servicios: la validación que falta

| servicio | qué se añade |
|---|---|
| `set_ir_mode` | `far_code`/`near_code` en **0-7**; `mode` en `{broadcasting, following, evading, off}` |
| `set_ir_evading` | los mismos rangos. **Es una regresión frente a ROS 1**, que sí validaba |
| `send_infrared_message` | ya valida 0-7 y 0-64; se añade que **las intensidades encendidas compartan nivel** (`sensor.md:213`) |
| `SetIRMode.srv` | documentar los valores de `mode`. Hoy no los dice, y es donde ROS 1 (`broadcast`) y ROS 2 (`broadcasting`) divergieron |

📌 `evading` pasa a ser también un valor de `set_ir_mode`, además de su servicio propio, para que
el modo se pida siempre por el mismo sitio. El servicio suelto se mantiene por compatibilidad.

🔴 **Las guardias de la parada de emergencia se mantienen** en `following` y `evading`, y **no** en
`broadcasting` (solo emite luz) ni en `off` (apagar no se niega nunca).

### 6 · `atriz.py`: la capa del alumno

```python
robot.emitir_ir(codigo)          # 0-7
robot.escuchar_ir()              # último código recibido, o None si no hay o caducó
robot.quien_hay_cerca()          # las cuatro lecturas + antigüedad
robot.seguir_a_otro()            # 🔴 conduce solo
robot.huir_de_otro()             # 🔴 conduce solo
robot.parar_ir()
```

🔴 **`seguir_a_otro()` y `huir_de_otro()` hacen conducir al robot sin `collision_monitor` ni
watchdog.** La biblioteca debe: avisarlo por pantalla como ya hace con otras cosas, respetar la
parada de emergencia, y **apagarlos en `secuencia_de_cierre`** — igual que hoy apaga el barrido del
LIDAR. Sin eso, un Ctrl-C deja un robot conduciendo por el aula.

### 7 · La web

Entran en la lista blanca de `robot.launch.py`: `send_infrared_message`, `/infrared_messages` y
`/estado_ir`.

🔴 **`following` y `evading` se quedan FUERA, y es una decisión que hay que declarar.**
`SEGURIDAD_ROSBRIDGE.md` cierra el IR a propósito porque esos dos se saltan la capa de seguridad, y
rosbridge **no tiene identidad por usuario** (pendiente abierto). Abrirlos significaría que
cualquiera en el aula puede poner a conducir cualquier robot. Se reabre cuando exista esa identidad.

⚠️ Rosbridge **deniega en silencio**: al tocar las listas hay que pasar
`mediciones_banco/probar_lista_blanca.py`, que comprueba las dos direcciones.

---

## Flujo de datos

**Recibir un mensaje:** otro robot emite → firmware entrega `0x2C` → `_h_ir_mensaje` publica
`/infrared_messages` **y** actualiza `ultimo_codigo`/`antiguedad_mensaje_s` del estado.

**Saber quién hay cerca:** el temporizador sondea → cuatro bytes → `/estado_ir`. Con `255` en los
cuatro, no hay nadie emitiendo a la vista.

**Seguir a otro:** A hace `broadcasting(far, near)`; B hace `following(far, near)` con **los mismos
códigos**. El firmware de B conduce. `/estado_ir` de B pasa a `conduciendo_por_ir: true` — que es
la única forma que tiene ROS de enterarse.

---

## Errores y casos límite

| caso | qué hace el sistema |
|---|---|
| El firmware rechaza `enable_..._notify` | se registra la **respuesta**, no solo la ausencia de excepción: el SDK devuelve un dict de error en vez de lanzar |
| El sondeo falla | `lecturas_validas: false`. **No se publican ceros como si fueran lecturas** |
| Nunca ha llegado un mensaje | `hay_mensaje: false`. Distinto de «llegó el código 0» |
| El dato caducó | `antiguedad_lectura_s` lo dice; el consumidor decide. El driver **no** inventa un valor |
| Código fuera de 0-7 | el servicio lo rechaza **antes** de llamar al SDK, que no valida |
| Parada de emergencia activa | `following` y `evading` se niegan; `off` **nunca** se niega |
| Ctrl-C en una práctica | `secuencia_de_cierre` apaga los modos IR |

---

## Pruebas

### 1 · Prueba de viabilidad de la detección direccional — **VA PRIMERO**

👤 Decisión del usuario: medir antes de construir encima. Es lo único del diseño que se apoya en
algo **no verificado** — que los cuatro sensores del RVR discriminen dirección como los del BOLT.

⚠️ **Y NO depende de nada de este diseño**, que si no sería circular: la prueba bautiza los campos
de `EstadoIR`, así que no puede leerlos. Es un guion suelto que llama directamente a
`get_bot_to_bot_infrared_readings()` del SDK e imprime los cuatro bytes en crudo.

**Montaje:** un robot en `broadcasting`; el otro quieto, ejecutando el guion. Se lee con el emisor
**delante, detrás, a izquierda y a derecha**, a ~50 cm y a ~2 m.

📌 **Orden de implementación que esto impone:** el guion de viabilidad y su medición van **antes**
de congelar `EstadoIR.msg`. Todo lo demás —la clave `infrared_code`, las validaciones, la seguridad
de `atriz.py`— no depende de ese resultado y puede ir en paralelo.

**Criterio, fijado ANTES de medir:**
- ✅ **Discrimina** si en cada posición hay bytes distintos de 255 y **cambian según el lado**.
- 🟡 **Detecta pero no discrimina** si responde igual en todas las posiciones → los cuatro campos
  se colapsan a uno (`hay_alguien`) y se retira `quien_hay_cerca()` del diseño.
- 🔴 **No sirve** si sigue en `0xFFFFFFFF` con otro robot emitiendo a 50 cm.

**Y de paso bautiza los campos:** qué byte corresponde a qué lado del robot.

### 2 · Banco `medir_ir_dos_robots.py`

En `00_auditoria/evidencia/mediciones_banco/`. Ejercita emisión→recepción, los modos, y **el coste
del sondeo sobre el ritmo de `/odom`**.

### 3 · `verificar_robot.sh`

Hoy comprueba que los tres servicios respondan. Se añade que **`/estado_ir` publique** — no hace
falta un segundo robot para eso.

⚠️ **`/infrared_messages` NO se puede comprobar con un solo robot**, y eso se dice en vez de
fingir que se comprueba.

---

## Lo que este diseño NO hace

- **No inventa semántica sobre el hardware.** Nada de «tengo un robot a la izquierda» en el
  contrato de ROS mientras no esté medido que se puede saber.
- **No abre `following`/`evading` a la web.** Ver §7.
- **No persigue los CIDs no documentados** (`0x2A`, `0x2B`, `0x2D`), que por vecindad parecen
  primitivas IR ocultas. Es una inferencia sin respaldo y no se construye sobre ella.
- **No toca `ir_messages` (String).** Sigue descartado, y ahora con mejor motivo: en ROS 1 nunca
  publicó nada.
