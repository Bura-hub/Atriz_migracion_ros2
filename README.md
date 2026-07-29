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
| **Fase actual** | **Fase 0.1 — completada** (2026-07-29). UART sobre PL011 verificado, odometría de 3.85 → **16.59 Hz** |
| **Siguiente paso** | Subir la rama `migracion-ros2` y hacer la **Fase 0.3** (imagen de respaldo) |
| **Bloqueante antes de reinstalar** | **Fase 0.3** — imagen `dd` completa de la microSD. Ver [RECUPERACION.md](03_operacion/RECUPERACION.md) |
| **Sistema hoy** | Raspberry Pi 4B 8 GB · Ubuntu 20.04.6 · ROS Noetic · Sphero RVR por UART · YDLIDAR X2 (driver **no instalado**) |
| **Sistema objetivo** | Ubuntu Server 24.04 LTS · ROS 2 Jazzy (soporte hasta mayo 2029) · rosbridge · SLAM + Nav2 · 16 robots |

Ver [CHANGELOG.md](CHANGELOG.md) para la bitácora detallada.

---

## Por dónde empezar

**Si vienes nuevo al proyecto** → lee el [informe de auditoría](00_auditoria/INFORME_AUDITORIA.md).
Explica qué hay montado, qué falla y por qué.

**Si vas a ejecutar la migración** → lee el [plan](01_plan/PLAN_MIGRACION_ROS2.md).
Está dividido en fases con criterios de verificación en cada una.

**Si algo se rompió y hay que volver atrás** → [RECUPERACION.md](03_operacion/RECUPERACION.md).

**Si quieres saber cómo se montó el sistema actual** →
[transcripción del manual original](02_manual/MANUAL_SPHERO_transcripcion.md),
con anotaciones de auditoría marcadas aparte del texto original.

---

## Estructura

```
00_auditoria/
├── INFORME_AUDITORIA.md      Diagnóstico completo con mediciones
└── evidencia/                Salidas CRUDAS de los comandos (línea base)
01_plan/
└── PLAN_MIGRACION_ROS2.md    Plan por fases, de la Fase 00 a los 16 robots
02_manual/
├── MANUAL_SPHERO_original.docx        El manual con el que se montó el sistema
├── MANUAL_SPHERO_transcripcion.md     Su texto en Markdown + anotaciones
├── MANUAL_SPHERO_extraccion_mecanica.txt   Extracción cruda (prueba de fidelidad)
└── MANUAL_ATRIZ_ROS2.md               El manual nuevo (se escribe en fases 1–5)
03_operacion/
├── RECUPERACION.md           Cómo volver al sistema Noetic
├── RUNBOOK.md                Operación diaria (fases 2–5)
├── ARQUITECTURA.md           Decisiones de diseño (fase 5)
└── FLOTA.md                  Clonado y gestión de los 16 robots (fase 6)
04_respaldo/
├── configs/                  cmdline.txt, config.txt, udev, fstab, bashrc
└── sin_commitear/            Los 6 ficheros de Atriz_rvr que se perderían al reflashear
```

---

## Los cuatro hallazgos que motivan todo

Resumidos del [informe completo](00_auditoria/INFORME_AUDITORIA.md):

1. **La lentitud es 100 % configuración, no hardware.** 59.9 °C, cero throttling,
   cero under-voltage, 4.2 GB de RAM libre. Lo que duele es un escritorio GNOME
   *duplicado*, el governor `ondemand` dejando la CPU a 600 MHz el **59.6 %** del
   tiempo, y 784 MB de journal generando **47 s de bloqueo por I/O en 42 min**.

2. **El UART del RVR está sobre el mini-UART.** Falta `dtoverlay=disable-bt`,
   así que el PL011 (el UART bueno) está reservado a un Bluetooth **sin adaptador**
   y el RVR habla por un puerto cuyo baudrate deriva con el reloj del VPU.
   Fallo latente de fiabilidad.

3. **El LIDAR no existe en el sistema.** El driver YDLIDAR nunca se instaló, pero
   3 launch files y toda la documentación lo dan por hecho. Y el árbol TF está
   partido en dos, lo que hace imposible cualquier SLAM.

4. **La arquitectura no llega a 16 robots.** ROS Noetic EOL, un `roscore` único,
   control por SSH secuencial (hasta 64 s por comando con 16 robots), sin
   telemetría en streaming, y la parada de emergencia publicando en un topic que
   el driver no escucha.

---

## Seguridad

- **Ninguna credencial en texto plano** en los ficheros de este repositorio.
  La contraseña del manual aparece redactada como `«CONTRASEÑA»`.
- ⚠️ **`MANUAL_SPHERO_original.docx` sí la contiene** (es una copia intacta, y es
  el procedimiento de reversión). Por eso **este repositorio debería ser privado**.
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
