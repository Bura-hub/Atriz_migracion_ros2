# Traspaso — dónde estamos y cómo seguir

> **Léelo si retomas el proyecto** después de un tiempo, en otra máquina, o si la
> Raspberry Pi ya se reflasheó. Está escrito para que no haga falta reconstruir el
> contexto desde cero.
>
> Última actualización: **2026-07-30**.

---

## En una frase

**El sistema nuevo está instalado y a punto**: Ubuntu Server 24.04.4 con el RVR y el LIDAR
verificados. Lo que falta es el **go/no-go del SDK en Python 3.12**, y con él la decisión de
si la migración sigue adelante tal como está planteada.

---

## Qué está verificado (con mediciones, no suposiciones)

| Componente | 20.04 + Noetic | **24.04** | Evidencia |
|---|---|---|---|
| Raspberry Pi 4B 8 GB | ✅ 57 °C, cero throttling | ✅ 63.7 °C, `throttled=0x0` | `evidencia*/` |
| Enlace UART Pi ↔ RVR | ✅ PL011 vía `/dev/rvr` | ✅ **el RVR contesta**, firmware 9.1.462 | `raw_uart_2026-07-30.txt` |
| YDLIDAR X2 | ✅ 100 % checksums, 11.4 Hz | ✅ **100 %, 11.48 Hz** | `lidar_x2_2026-07-30.txt` |
| Higiene del SO | receta documentada | ✅ **aplicada** | `02_higiene_aplicada_*.txt` |
| Telemetría del RVR a 16.59 Hz | ✅ 12 min, 0 huecos, 0 pérdidas | ⏳ requiere portar el driver | `estabilidad_12min_2026-07-29.txt` |
| SDK de Sphero | ✅ GO en Python 3.8 | ⏳ **3.12 SIN PROBAR — es el siguiente paso** | `scripts/fase_1_validar_sdk_py312.py` |

Firmware del RVR: **9.1.462** (Nordic), confirmado también en 24.04 leyendo el payload de
`get_version` (`09 00 01 01`).

⚠️ Las dos líneas base son distintas y **no se mezclan**: `00_auditoria/evidencia/` es el
sistema viejo, `00_auditoria/evidencia_24_04/` el nuevo.

## Qué está roto y confirmado

| Problema | Gravedad |
|---|---|
| 🔴 **La parada de emergencia de la web no hace nada.** Publica en `/rvr/emergency_stop`, que no existe. Falla **en silencio** con `200 OK` | seguridad |
| 🔴 **No hay watchdog de `cmd_vel`.** Si cae la red, el robot sigue con el último comando | seguridad |
| 🔴 **No hay URDF** → árbol TF partido → SLAM imposible | bloqueante |
| 🔴 **Driver ROS del LIDAR no instalado** (el sensor sí funciona) | bloqueante |
| 🔴 **Sin SLAM ni navegación**: no hay `gmapping`, `slam_toolbox`, `move_base`, `amcl`, `robot_localization` | bloqueante |
| **Sin arranque automático** — ninguna unidad systemd | operación |
| **`imu.angular_velocity` en deg/s** (viola REP-103) | calidad de SLAM |
| **Credencial del usuario `sphero` expuesta** en `Atriz_web_server` público, sin rotar | seguridad |

---

## El siguiente paso, exacto

**Etapa D — el GO/NO-GO del SDK en Python 3.12.** Es el punto de decisión de toda la
migración. **No instales ROS 2 antes de pasarlo.**

```bash
sudo apt install -y python3-pip python3-venv
pip install --break-system-packages pyserial-asyncio     # pyserial 3.5 ya está en el sistema
                                                          # (24.04 aplica PEP 668)
mkdir -p ~/atriz_ws/src && cd ~/atriz_ws/src
git clone -b migracion-ros2 https://github.com/Bura-hub/Atriz_rvr.git

# Regla nº1 del proyecto: fetch ANTES de auditar o leer código
git -C ~/atriz_ws/src/Atriz_rvr fetch origin
git -C ~/atriz_ws/src/Atriz_rvr status -sb    # esperado: migracion-ros2 = 24c7749

# Con el RVR ENCENDIDO:
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

- **GO** → seguir con la Etapa E (instalar `ros-jazzy-ros-base`), manual cap. 5.2.
- **NO-GO** → **PARAR.** El script imprime las cuatro alternativas ordenadas por coste. Es una
  decisión de arquitectura, no algo a improvisar. Documentar la salida cruda y consultar.

### Ya hecho, no lo repitas

| Etapa | Estado |
|---|---|
| **A** — imagen `dd` del sistema Noetic | ✅ hecha **y verificada**. La reversión existe |
| **B** — instalar 24.04, `cmdline.txt`, `config.txt`, UART, `/dev/rvr` | ✅ verificado 2026-07-30 |
| **B5** — actualizaciones cerradas y credenciales de git | ✅ 2026-07-30 |
| **C** — higiene del SO | ✅ 2026-07-30 |
| **E3/E4** — verificación de UART y LIDAR | ✅ hechas ya, sobre 24.04 |

✅ **El `stash@{0}` ya está rescatado.** Contenía tres scripts de estudiantes que solo
existían en un stash local — y los stashes **no viajan a un remoto**, así que se habrían
perdido al reflashear. Están preservados sin modificar en la rama
**`wip/scripts-estudiantes`** (commit `62e0313`). El stash original se conserva intacto
(se usó `stash apply`, no `pop`).

⚠️ **Decisión pendiente sobre `01_avanzar.py`.** No está modificado: está **reemplazado**.
El tutorial «ULTRA SIMPLE: solo avanza el robot» ya no existe en esa rama; en su lugar hay
una clase `SeguidorBordeRojo` que sigue el borde de una línea roja con `/color` y el servicio
`/enable_color`. Parece un experimento escrito encima del fichero equivocado — es el
**primer** script que ejecutan los estudiantes y ya no hace lo que su nombre promete.
Además `origin/main` ya trae `scripts/estudiantes/seguidor_linea_pid_demo.py`, que aborda el
mismo problema.

Hay que decidir: **(a)** mover el seguidor a su propio fichero y restaurar el tutorial, o
**(b)** descartarlo por estar superado por `seguidor_linea_pid_demo.py`. Por eso la rama es
WIP y **no debe mezclarse con `main`** hasta resolverlo.

⚠️ **Antes de apagar la Pi en cualquier momento, comprueba que no queda nada sin subir.** Es
lo que hace `fase_0_3_respaldo.sh`, pero conviene saber por qué: un commit local o un stash
**no existen** para nadie más, y desaparecen con la tarjeta.

```bash
for r in ~/atriz_ws/src/Atriz_rvr ~/atriz_migracion; do
  echo "── $r"; git -C $r status -sb | head -1; git -C $r stash list
done
```

🔴 **Y comprueba que PUEDES subir.** En un sistema recién instalado no hay credenciales y el
repositorio es privado: `git fetch` falla con `could not read Username`, así que los commits se
quedan solo en la tarjeta. Pasó el 2026-07-30 — ver `CLAUDE.md`, «Antes de subir nada».

```bash
git -C ~/atriz_migracion fetch origin && echo "OK: hay credenciales"
```

### Reinstalar con ayuda de un agente

Tras grabar Ubuntu Server 24.04 y clonar este repositorio, basta con arrancar Claude Code
en `~/atriz_migracion` y decirle:

> Lee CLAUDE.md y sigue INSTALACION.md para poner el sistema a punto.

`CLAUDE.md` se carga solo y le da las reglas, las trampas conocidas y los valores de
referencia de **ambos** sistemas.

**Estado de los capítulos del manual tras la sesión del 2026-07-30:**

| Cap. | Contenido | Estado |
|---|---|---|
| 1 | Enlace UART | ✅ verificado en 20.04 **y en 24.04** |
| 3 | Flasheo de 24.04, `cmdline.txt`, `config.txt` | ✅ **verificado** — dejó de ser NO VERIFICADO |
| 4 | Higiene del SO | ✅ **verificado** — dejó de ser NO VERIFICADO |
| 5 | ROS 2 Jazzy y workspace | 📝 **sigue NO VERIFICADO** — es lo próximo |
| 8 | YDLIDAR X2 | ✅ hardware verificado en ambos; driver ROS pendiente |

Los capítulos 3 y 4 se recorrieron y **se corrigieron sobre la marcha**, que es lo que pedía
la nota. El 5 sigue sin ejecutarse: al recorrerlo, corregirlo en el momento y cambiar su marca
a ✅ con la fecha. **En el repositorio, no en un mensaje de chat.**

---

## Estado de los repositorios

| Repo | Rama | Commit | Contenido |
|---|---|---|---|
| `Atriz_migracion_ros2` | `main` | — | Este repositorio: auditoría, plan, manual, scripts |
| `Atriz_rvr` | `main` | `6f48ae1` | Original + **el arreglo del UART** (cherry-pick de `67c8776`) |
| `Atriz_rvr` | **`migracion-ros2`** | `24c7749` | UART → `/dev/rvr` · `interval` 250→60 ms |
| `Atriz_rvr` | `wip/scripts-estudiantes` | `62e0313` | Stash rescatado. **No mezclar** — ver decisión pendiente arriba |
| `Atriz_web_server` | `pruebas` | `924d659` | Sin tocar — se aborda al final |

La rama `migracion-ros2` se creó **desde `origin/main`**, no desde el clon local. Importante:
ver la lección de abajo.

### ⚠️ Por qué el arreglo del UART también está en `main`

La imagen de respaldo de la Fase 0.3 se crea sobre un sistema que **ya tiene
`dtoverlay=disable-bt` aplicado**, así que en él `/dev/ttyS0` **ya no lleva el UART**.

Si se restaurara esa imagen y se trabajara desde `main` con el código original, el robot
parecería roto sin motivo aparente: el driver abriría un puerto que existe pero no está
conectado a nada. Por eso el commit del UART se llevó también a `main` (cherry-pick
`6f48ae1`).

**Regla general:** cualquier arreglo que dependa de la configuración del sistema operativo
—no solo de ROS— debe estar en `main`, porque `main` es lo que se ejecuta si algo se revierte.

### Ficheros sueltos sin versionar

`carro.py` (**0 bytes**, nada que salvar) y `prueba.py` (92 líneas) siguen sin trackear.

`prueba.py` es un tercer intento de seguidor de línea y **está roto**: define
`def _init_(self)` con **un solo guion bajo** en lugar de `__init__`, así que el constructor
nunca se ejecuta y la clase no hace nada. Además se suscribe a `/color_sensor_left` y
`/color_sensor_right`, que **no existen** — el driver publica únicamente `/color`.

Están respaldados como ficheros en `04_respaldo/sin_commitear/archivos/`. **Decisión
pendiente:** versionarlos o descartarlos. Recomendación: borrar `carro.py` y no recuperar
`prueba.py`, ya que `seguidor_linea_pid_demo.py` (en `origin/main`) resuelve lo mismo y
funciona.

---

## Cinco lecciones que ahorran horas

**1. `git fetch` antes de auditar cualquier cosa.** Se hizo una auditoría completa sobre un
clon **5 commits por detrás** al que **nunca se le había hecho `fetch`**. Tres hallazgos
resultaron falsos. Es el error más caro de la sesión.

**2. Un robot dormido parece un cable roto.** Cero bytes de respuesta, idéntico síntoma.
**Apaga y enciende el robot antes de tocar configuración.** Se perdió un buen rato
persiguiendo un problema de device-tree que no existía.

**3. Que el nodo arranque no prueba que el enlace funcione.** `rvr_fw_check_async.py` hace
`except (asyncio.TimeoutError, Exception)` y continúa en silencio. Pero el **tiempo de
construcción** sí es diagnóstico: **0 s** = el robot responde, **~10 s** = dos timeouts = no
responde.

**4. No uses `pkill -f Atriz_rvr_node`.** El patrón coincide con la propia línea de comando
del shell que lo ejecuta y **mata tu terminal**. Pasó dos veces. Usa `pgrep -f "[A]triz..."`
con el corchete, o el PID.

**5. Mide antes de atribuir.** La auditoría culpó al bucle de asyncio de la odometría a
4 Hz. Midiendo el SDK **sin ROS** salió idéntico: la causa era un solo parámetro. El arreglo
fue **una línea** en vez de una reescritura.

---

## Herramientas de diagnóstico disponibles

Todas en `00_auditoria/evidencia/mediciones_banco/`, con su README:

```bash
raw_uart.py      # ¿contesta el RVR a nivel de bytes?     <- el más útil
x2_parse.py      # ¿funciona el LIDAR? (sin driver ROS)
medir.py         # frecuencia y jitter de /odom e /imu
sdk_full.py 60   # ritmo del SDK con los 8 sensores
estabilidad.py   # 12 min: huecos, pérdidas, fugas de memoria
test_rvr.py      # diálogo básico con el SDK
```
Y en `scripts/`: `fase_0_1_fix_uart.sh`, `diag_uart_pins.sh`,
`fase_0_3_respaldo.sh`, `fase_1_validar_sdk_py312.py`.

---

## Decisiones ya tomadas — no volver a discutirlas

| Decisión | Dónde está razonada |
|---|---|
| Ubuntu Server 24.04 + ROS 2 Jazzy (soporte a mayo 2029) | plan, Contexto |
| Reinstalar **sobre la misma microSD**; reversión por imagen `dd` | plan, Fase 0.3 |
| **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total | `ARQUITECTURA.md`, D1 |
| La web habla por **rosbridge**, no por SSH | `ARQUITECTURA.md`, D2 |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final**, cuando el robot esté funcional | decisión del usuario |

---

## Lo que sigue sin medir

- **Ancho de banda por robot con rosbridge activo.** Es el **riesgo principal del escalado**
  y la decisión de compra de red más cara. Medir con un robot en la Fase 5 y extrapolar.
- Si Nav2 cabe en el Pi 4 junto al resto (referencia: el driver solo ya usa 29.5 % de un núcleo).
- Latencia de `cmd_vel` de extremo a extremo, y el impacto de las **48** llamadas a
  `asyncio.run()` en callbacks.
- Si el driver del X2 puede fijar la velocidad de giro (afectaría a la resolución del mapa).
- Si los 16 adaptadores USB comparten el mismo `SerialNumber "0001"`.
