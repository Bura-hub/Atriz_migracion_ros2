# Atriz — Migración a ROS 2 y escalado a 16 robots

Repositorio de **seguimiento** de la migración del laboratorio remoto Atriz
(Sphero RVR + Raspberry Pi) desde ROS Noetic a ROS 2 Jazzy.

No contiene código del robot — ese vive en
[`Atriz_rvr`](https://github.com/Bura-hub/Atriz_rvr) y
[`Atriz_web_server`](https://github.com/Bura-hub/Atriz_web_server).
Aquí está **la auditoría, el plan, el manual y la documentación de operación**:
lo que hace falta para retomar el trabajo desde cualquier máquina, y para
reconstruir el sistema si algo sale mal.

> **Por qué existe este repositorio.** La microSD de la Raspberry Pi se va a
> reflashear para instalar Ubuntu 24.04 + ROS 2. Todo lo documentado aquí vivía
> únicamente en esa tarjeta. Ahora sobrevive independientemente de ella.

---

## Estado del proyecto

| | |
|---|---|
| **Fase actual** | **Etapas A–E1 y Fases 2, 3, 4 y 4c completadas, más Nav2 y el arranque automático** (2026-07-31). El robot **navega** con Nav2 (⚠️ el «error 8–10 cm» es la tolerancia repetida, no una medida: con cinta y trilateración son **~10-12 cm**, y **41 cm** sobre un mapa rancio — evidencias 83-84), se **localiza** con AMCL sobre un mapa guardado, tiene capa de seguridad (`collision_monitor`), 18 servicios en el driver y **se levanta solo al encender** |
| **Siguiente paso** | **Migrar el robot 2** → [`03_operacion/FLOTA.md`, «Robot 2: instalación LIMPIA, paso a paso»](03_operacion/FLOTA.md). ✅ `provision.sh` YA se ha ejecutado entero (2026-08-11, rvr-02: 96 ✓ · 0 fallos) — cae la última suposición peligrosa. Queda el segundo robot para probar el IR y validar la imagen dorada antes de replicarla catorce veces. Después, **la plataforma web (Fase 5)**, que es lo único grande que falta |
| **Sistema hoy** | Raspberry Pi 4B 8 GB · **Ubuntu Server 24.04.4 LTS** · Python 3.12.3 · `rvr-01` · arranque en **22.1 s** (5.5 kernel + 16.6 userspace) · Sphero RVR por `/dev/rvr` (PL011) · YDLIDAR X2 en `/dev/ydlidar` · **ROS 2 Jazzy** (`ros-base` + `navigation2`) · driver, URDF, LIDAR, SLAM, Nav2, AMCL y `atriz-robot.service` funcionando |
| ⚠️ **Al arrancar NO conduce** | A propósito: el barrido del lidar arranca **apagado** y sin `/scan` el `collision_monitor` bloquea el movimiento. Se despierta con `atriz-escaneo on`. Ver [RUNBOOK](03_operacion/RUNBOOK.md) |
| **Sistema objetivo** | Ubuntu Server 24.04 LTS · ROS 2 Jazzy (soporte hasta mayo 2029) · rosbridge · SLAM + Nav2 · 16 robots |
| **Vuelta atrás** | ✅ Disponible. La imagen `dd` del sistema Noetic está hecha **y verificada**. Ver [RECUPERACION.md](03_operacion/RECUPERACION.md) |

Ver [CHANGELOG.md](CHANGELOG.md) para la bitácora detallada, e
[INSTALACION.md](INSTALACION.md) para el estado exacto de cada etapa.

### Qué está verificado sobre la máquina real

| | 20.04 + Noetic | **24.04** |
|---|---|---|
| Enlace UART Pi ↔ RVR (`/dev/rvr` → PL011) | ✅ 2026-07-29 | ✅ **2026-07-30** |
| Telemetría del RVR | ✅ 16.59 Hz, 12 min sin huecos | ✅ **16.671 Hz** sobre ROS 2, σ 0.47 ms |
| Driver en `rclpy` · `cmd_vel` · watchdog | — | ✅ **2026-07-30**, verificado en banco |
| Árbol TF conectado (`odom → base_footprint → laser`) | 🔴 partido en dos | ✅ **2026-07-31** — era el bloqueante raíz de SLAM |
| Driver ROS del LIDAR · `/scan` | 🔴 nunca instalado | ✅ **2026-07-30** — 10.1 Hz, 89 % de puntos válidos |
| **SLAM: el mapa crece al moverse** | 🔴 nunca hubo SLAM | ✅ **2026-07-31** — 2367 → 3299 celdas, 8.25 m² |
| **El enlace aguanta solo** (el RVR se dormía a los 300.6 s) | — | ✅ **2026-07-31** — 12 min sin un hueco |
| Ejes según REP-103 (`/odom`, `/imu`) | 🔴 sin verificar | ✅ **2026-07-31** — medido sensor a sensor |
| `/imu.linear_acceleration` en m/s² | 🔴 venía en `g`, y ROS 1 tampoco convertía | ✅ **2026-07-31** — 9.374 m/s² en reposo |
| YDLIDAR X2 (100 % checksums, ~2990 muestras/s, 11.48 Hz) | ✅ 2026-07-29 | ✅ **2026-07-30** |
| Higiene del SO | receta documentada | ✅ **2026-07-30** — arranque 1min39s → **8.7 s** |
| SDK de Sphero | ✅ GO en Python 3.8 | ✅ 🟢 **GO en Python 3.12** — 16.67 Hz |

Evidencia cruda: [`00_auditoria/evidencia/`](00_auditoria/evidencia/) para 20.04,
[`00_auditoria/evidencia_24_04/`](00_auditoria/evidencia_24_04/) para 24.04. **Son dos líneas
base distintas y no deben mezclarse.**

### Un solo comando para saber si un robot está bien

```bash
bash scripts/verificar_robot.sh --hardware
```

**105 comprobaciones** con `--hardware` (102 sin él) y código de salida ≠ 0 si algo falla. Es lo que hace que 16 robots sean
manejables: no se pueden revisar a ojo. En `rvr-01`, el 2026-08-01: **105 correctas con `--hardware`, 0 fallos**.

Su regla es **comprobar el efecto, no la intención**, y no es retórica: comprueba el *ritmo* de
`/odom` (no que el topic exista) porque el RVR se dormía dejando el nodo vivo y publicando cero,
y comprueba `odom → base_footprint` (no `odom → laser`) porque esa segunda **pasaba** con el
árbol TF partido en dos.

---

## Por dónde empezar

**Si eres un agente (Claude Code u otro)** → **[CLAUDE.md](CLAUDE.md)**. Se carga
automáticamente al abrir este directorio y contiene las reglas del proyecto, las trampas
conocidas y los valores de referencia medidos.

**Si retomas el proyecto tras un tiempo, o en otra máquina** → **[TRASPASO.md](TRASPASO.md)**.
Es el documento de contexto: qué está verificado, qué está roto, cuál es el siguiente paso
exacto, y las cinco lecciones que ahorran horas.

**Si vienes nuevo al proyecto** → lee el [informe de auditoría](00_auditoria/INFORME_AUDITORIA.md).
Explica qué hay montado, qué falla y por qué.

**Si vas a formatear e instalar el sistema** → **[INSTALACION.md](INSTALACION.md)**. Es el
recorrido paso a paso, en orden, desde apagar el sistema actual hasta el robot funcionando.

**Si quieres el porqué y la estrategia** → el [plan](01_plan/PLAN_MIGRACION_ROS2.md),
dividido en fases con criterios de verificación.

**Si algo se rompió y hay que volver atrás** → [RECUPERACION.md](03_operacion/RECUPERACION.md).

**Si quieres saber cómo se montó el sistema actual** →
[transcripción del manual original](02_manual/MANUAL_SPHERO_transcripcion.md),
con anotaciones de auditoría marcadas aparte del texto original.

---

## Estructura

```
CLAUDE.md                     ← contexto e instrucciones para agentes
INSTALACION.md                ← LA RUTA: de formatear a robot funcionando
TRASPASO.md                   ← EMPIEZA AQUÍ si retomas el proyecto
00_auditoria/
├── INFORME_AUDITORIA.md      Diagnóstico completo con mediciones
├── evidencia/                Salidas CRUDAS — línea base del sistema VIEJO (20.04 + Noetic)
└── evidencia_24_04/          Salidas CRUDAS — línea base del sistema NUEVO (24.04)
01_plan/
└── PLAN_MIGRACION_ROS2.md    Plan por fases, de la Fase 00 a los 16 robots
02_manual/
├── MANUAL_SPHERO_original.docx        El manual con el que se montó el sistema
├── MANUAL_SPHERO_transcripcion.md     Su texto en Markdown + anotaciones
├── MANUAL_SPHERO_extraccion_mecanica.txt   Extracción cruda (prueba de fidelidad)
└── MANUAL_ATRIZ_ROS2.md               El manual nuevo (se escribe en fases 1–5)
03_operacion/
├── RECUPERACION.md           Cómo volver al sistema Noetic
├── RUNBOOK.md                Operación y diagnóstico de fallos
├── ARQUITECTURA.md           Las 4 decisiones de diseño
├── ESTADO_ACTUAL.md          🔴 El canal de contexto entre el Claude del PC y el de la Pi
├── SENSOR_COLOR.md           🆕 El sensor RGBC y sus DOS modos (reflejo / emisión) + contrato web
├── ARRANQUE_NAVEGACION.md    SLAM y Nav2 desde la web: unidades, supervisor y el mapa
├── API_LABORATORIO.md        Diseño de `atriz.py`, la biblioteca que usan los alumnos
├── PRUEBA_ACEPTACION.md      Criterio y umbrales de la prueba de aceptación
├── MEDIDAS_ROBOT.md          Qué está medido con cinta y qué viene de una ficha
└── FLOTA.md                  Restricciones medidas y gestión de los 16 robots
04_respaldo/
├── configs/                  cmdline.txt, config.txt, udev, fstab, bashrc (del sistema viejo)
└── sin_commitear/            Los 6 ficheros de Atriz_rvr que se perderían al reflashear
scripts/
├── fase_0_1_fix_uart.sh      ✅ repara el UART — verificado en 20.04 y 24.04
├── diag_uart_pins.sh         diagnóstico de los pines GPIO14/15 (nunca ha hecho falta)
├── fase_0_3_respaldo.sh      ✅ prepara la SD para la imagen
├── fase_1_higiene_so.sh      ✅ higiene del SO — verificado en 24.04
├── fase_1_validar_sdk_py312.py   ✅ GO/NO-GO de la migración — 🟢 GO (2026-07-30)
├── verificar_robot.sh        ✅ 105 aserciones: ¿está este robot bien? ← ÚSALO SIEMPRE
├── provision.sh              ✅ de un 24.04 limpio a robot terminado (ejecutado entero en rvr-02)
├── preparar_tarjeta.sh       ✅ en el PC: prepara la tarjeta de cada robot
├── fase_6_preparar_imagen_dorada.sh   📝 NO VERIFICADO — imagen dorada de la flota
└── first-boot.sh / .service  📝 NO VERIFICADO — personaliza cada robot clonado
```

Cada carpeta de evidencia y la de scripts tienen su propio `README.md` con el detalle.

---

## Los cinco hallazgos que motivan todo

Resumidos del [informe completo](00_auditoria/INFORME_AUDITORIA.md):

1. **La lentitud es 100 % configuración, no hardware.** 59.9 °C, cero throttling,
   cero under-voltage, 4.2 GB de RAM libre. Lo que duele es un escritorio GNOME
   *duplicado*, el governor `ondemand` dejando la CPU a 600 MHz el **59.6 %** del
   tiempo, y 784 MB de journal generando **47 s de bloqueo por I/O en 42 min**.

2. ✅ **El UART del RVR estaba sobre el mini-UART** — *resuelto en la Fase 0.1*.
   Faltaba `dtoverlay=disable-bt`, así que el PL011 (el UART bueno) estaba
   reservado a un Bluetooth **sin adaptador** y el RVR hablaba por un puerto cuyo
   baudrate deriva con el reloj del VPU. Ahora corre sobre el PL011 vía `/dev/rvr`,
   verificado con paquetes crudos de checksum válido.

3. **El driver del YDLIDAR no está instalado en la Pi.** El sensor **sí funciona**
   (verificado: 100 % de checksums válidos, 2998 muestras/s, 11.4 Hz) y el código que
   lo consume existe (`obstacle_avoidance.py`), pero el paquete `ydlidar_ros_driver`
   nunca se instaló. Y el árbol TF sigue partido en dos (`rvr_base_link` vs
   `base_link`), lo que impide SLAM.

4. 🔴 **La parada de emergencia de la web no funciona — confirmado en banco.**
   Publica en `/rvr/emergency_stop`, un topic que no existe; el driver escucha
   `is_emergency_stop`. Falla **en silencio**: la API devuelve `200 OK` y el robot
   sigue igual. Es peor que no tener botón.

5. **La arquitectura no llega a 16 robots.** ROS Noetic EOL, un `roscore` único,
   control por SSH secuencial (hasta 64 s por comando con 16 robots) y sin
   telemetría en streaming.

---

## Seguridad

- **Ninguna credencial en texto plano** en los ficheros de este repositorio.
  La contraseña del manual aparece redactada como `«CONTRASEÑA»`.
- 🔴 **`MANUAL_SPHERO_original.docx` sí la contiene** (es una copia intacta, y es
  el procedimiento de reversión), y **está versionado**: `02_manual/`, desde el
  commit `f714a74`.
  - Aquí ponía: *«Por eso **este repositorio es privado** — confirmado el
    2026-07-30: `git ls-remote` sin credenciales es rechazado»*. **Esa premisa
    dejó de ser cierta el 2026-08-11**, cuando 👤 el usuario puso el repositorio
    en **público** a propósito, para no repartir un PAT en 16 microSD. Medido
    ese día: `git ls-remote` **sin credenciales funciona**.
  - O sea que **el fichero que justificaba la privacidad sigue aquí y la
    privacidad ya no**. 👤 Decisión pendiente del usuario: sacar el `.docx` del
    repositorio (y del historial), volver a privado, o asumirlo.
  - ✅ **Y lo que de verdad cierra esto: la contraseña se ROTÓ el 2026-08-04.** La que hay
    en el `.docx` **ya no vale**. Rotar es lo único que cierra una exposición —borrar
    ramas o archivar repositorios no cerró nada, y los dos casos están medidos—, así que
    lo que queda versionado es una credencial muerta. Sigue siendo higiene sacarla, no
    una urgencia.
- 🔴 **La credencial del usuario `sphero` está expuesta** en el repositorio público
  `Atriz_web_server` (`swarm_lab_api/app/core/raspberry_config.py`) y **debe considerarse
  comprometida**. Ver §5.1 del plan.
  - ⏳ **SIN CONFIRMAR:** si la contraseña que se puso al grabar la imagen de 24.04 es
    **nueva** o la misma de antes. `INSTALACION.md` §B1 pide que sea nueva, pero eso lo
    decidió quien manejó el Raspberry Pi Imager y no hay forma de comprobarlo desde el
    sistema. **Preguntarlo y anotarlo aquí.**
  - ⏳ **Pendiente en todo caso:** purgar el fichero del historial de `Atriz_web_server`
    (`git filter-repo`) y migrar a claves SSH. Rotar la contraseña de la Pi no arregla que la
    antigua siga en un repositorio público.
- ⚠️ **No metas el token de GitHub en el repositorio.** Va en `~/.git-credentials` con
  permisos `600`, y `.gitignore` lo excluye explícitamente junto a `*.token` y
  `authorized_keys`.
  - 📌 Desde el 2026-08-11 **el token solo hace falta para SUBIR**: `Atriz_migracion_ros2` y
    `Atriz_rvr` son públicos y se clonan sin credencial. O sea que solo debe existir
    `~/.git-credentials` en la máquina desde la que se publica, **no en los 16 robots** — que era
    justo el bloqueante nº 1 de la Fase 6.
- ⚠️ La credencial **ya está expuesta** en el repositorio público
  `Atriz_web_server` (`swarm_lab_api/app/core/raspberry_config.py`).
  **Debe considerarse comprometida y rotarse.** Ver §5.1 del plan.
- `/etc/netplan/*.yaml` se excluye deliberadamente porque contiene la PSK del WiFi.
  Ver [NETPLAN_OMITIDO.md](04_respaldo/configs/NETPLAN_OMITIDO.md).

---

## Convenciones

- **Nada se documenta sin haberse ejecutado y verificado.** Lo no probado se marca
  explícitamente como **NO VERIFICADO**. La deriva entre documentación y código es
  uno de los problemas que encontró esta auditoría; no se repite.
- Rutas y nombres de paquete se copian de la terminal, nunca de memoria.
- El `CHANGELOG.md` se actualiza al final de cada sesión, aunque sea una línea.
- Cada fase completada se commitea antes de empezar la siguiente.
