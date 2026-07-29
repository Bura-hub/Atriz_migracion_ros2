# Traspaso — dónde estamos y cómo seguir

> **Léelo si retomas el proyecto** después de un tiempo, en otra máquina, o si la
> Raspberry Pi ya se reflasheó. Está escrito para que no haga falta reconstruir el
> contexto desde cero.
>
> Última actualización: **2026-07-29**.

---

## En una frase

El hardware del robot está **verificado y funcionando** sobre ROS Noetic; el siguiente paso
es hacer una imagen de respaldo de la microSD y reinstalar con Ubuntu 24.04 + ROS 2 Jazzy.

---

## Qué está verificado (con mediciones, no suposiciones)

| Componente | Estado | Evidencia |
|---|---|---|
| Raspberry Pi 4B 8 GB | ✅ sano: 57 °C, cero throttling, cero under-voltage | `evidencia/03_rendimiento.txt` |
| Enlace UART Pi ↔ RVR | ✅ PL011 vía `/dev/rvr` | `raw_uart.py`, checksums válidos |
| Sphero RVR | ✅ 12 min a **16.59 Hz**, 0 huecos, 0 pérdidas | `estabilidad_12min_2026-07-29.txt` |
| YDLIDAR X2 | ✅ **100 %** checksums, 2998 muestras/s, 11.4 Hz | `lidar_x2_2026-07-29.txt` |
| SDK de Sphero | ✅ GO en Python 3.8 · ⏳ **3.12 sin probar** | `scripts/fase_1_validar_sdk_py312.py` |

Firmware del RVR: **9.1.462** (Nordic). Batería en la última prueba: 79 %.

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

**Fase 0.3 — imagen de respaldo. Bloqueante.** Requiere apagar la Pi y un PC.

```bash
bash ~/atriz_migracion/scripts/fase_0_3_respaldo.sh
# copiar ~/respaldo_pre_migracion a un USB (NO a git: contiene claves)
sudo poweroff
# con la SD en un PC, seguir 03_operacion/RECUPERACION.md
```

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

⚠️ **Antes de apagar, comprueba que no queda nada sin subir.** Es lo que hace el propio
script, pero conviene saber por qué: un commit local o un stash **no existen** para nadie
más, y desaparecen con la tarjeta.

```bash
for r in ~/atriz_git/src/Atriz_rvr ~/atriz_migracion; do
  echo "── $r"; git -C $r status -sb | head -1; git -C $r stash list
done
```

**Después:** Fase 1 (reinstalación), y su primer paso es el go/no-go:

```bash
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

Si sale **NO-GO**, el propio script imprime las cuatro alternativas ordenadas por coste.

---

## Estado de los repositorios

| Repo | Rama | Commit | Contenido |
|---|---|---|---|
| `Atriz_migracion_ros2` | `main` | — | Este repositorio: auditoría, plan, manual, scripts |
| `Atriz_rvr` | `main` | `659364c` | Código original, sin tocar |
| `Atriz_rvr` | **`migracion-ros2`** | `24c7749` | UART → `/dev/rvr` · `interval` 250→60 ms |
| `Atriz_rvr` | `wip/scripts-estudiantes` | `62e0313` | Stash rescatado. **No mezclar** — ver decisión pendiente arriba |
| `Atriz_web_server` | `pruebas` | `924d659` | Sin tocar — se aborda al final |

La rama `migracion-ros2` se creó **desde `origin/main`**, no desde el clon local. Importante:
ver la lección de abajo.

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
