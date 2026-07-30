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
| **Fase actual** | **Etapas A, B, C y D completadas** (2026-07-30). 🟢 **GO: la migración es viable** — el SDK de Sphero funciona en Python 3.12 y entrega telemetría a **16.67 Hz**, el mismo rendimiento que en Python 3.8 |
| **Siguiente paso** | **Etapa E1 — instalar `ros-jazzy-ros-base`** (manual, cap. 5.2), y después portar el driver a `rclpy` (plan, Fase 2) |
| **Sistema hoy** | Raspberry Pi 4B 8 GB · **Ubuntu Server 24.04.4 LTS** · Python 3.12.3 · `rvr-01` · arranque en **8.7 s** · Sphero RVR por `/dev/rvr` (PL011) · YDLIDAR X2 en `/dev/ttyUSB0` · **ROS todavía no instalado** |
| **Sistema objetivo** | Ubuntu Server 24.04 LTS · ROS 2 Jazzy (soporte hasta mayo 2029) · rosbridge · SLAM + Nav2 · 16 robots |
| **Vuelta atrás** | ✅ Disponible. La imagen `dd` del sistema Noetic está hecha **y verificada**. Ver [RECUPERACION.md](03_operacion/RECUPERACION.md) |

Ver [CHANGELOG.md](CHANGELOG.md) para la bitácora detallada, e
[INSTALACION.md](INSTALACION.md) para el estado exacto de cada etapa.

### Qué está verificado sobre la máquina real

| | 20.04 + Noetic | **24.04** |
|---|---|---|
| Enlace UART Pi ↔ RVR (`/dev/rvr` → PL011) | ✅ 2026-07-29 | ✅ **2026-07-30** |
| Telemetría del RVR a 16.59 Hz, 12 min sin huecos | ✅ 2026-07-29 | ⏳ tras portar el driver |
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

**39 comprobaciones** y código de salida ≠ 0 si algo falla. Es lo que hace que 16 robots sean
manejables: no se pueden revisar a ojo. En `rvr-01`, el 2026-07-30: **39 correctas, 0 fallos**.

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
├── verificar_robot.sh        ✅ 39 aserciones: ¿está este robot bien? ← ÚSALO SIEMPRE
├── provision.sh              🟡 de un 24.04 limpio a robot terminado (probado en seco)
├── preparar_tarjeta.sh       🟡 en el PC: prepara la tarjeta de cada robot (en seco)
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
- ⚠️ **`MANUAL_SPHERO_original.docx` sí la contiene** (es una copia intacta, y es
  el procedimiento de reversión). Por eso **este repositorio es privado** —
  confirmado el 2026-07-30: `git ls-remote` sin credenciales es rechazado.
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
