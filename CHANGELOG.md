# Bitácora

Una entrada por sesión de trabajo. Formato: qué se hizo, qué se verificó, qué quedó pendiente.

---

## 2026-07-29 (tarde) — Fase 0.1 completada y auditoría corregida

**Fase 0.1 — completada y verificada sobre el robot real.**

### Lo más importante: el clon local estaba desactualizado

`~/atriz_git/src/Atriz_rvr` estaba **5 commits por detrás de GitHub** y **nunca se le
había hecho `git fetch`**. La auditoría de la mañana se hizo sobre código de octubre
de 2025, ignorando trabajo de marzo de 2026. **Tres hallazgos resultaron erróneos** —
ver «Correcciones tras verificar en banco» en el informe.

Lección para el resto del proyecto: `git fetch` **antes** de auditar nada.

### Estructura de ramas

- `main` local puesto al día con `origin/main` (`659364c`), fast-forward limpio.
- Rama nueva **`migracion-ros2`** creada **desde `origin/main`**, no desde el local obsoleto.
- Los 3 scripts de estudiantes sin commitear quedaron en `stash@{0}`.
- `migracion-ros2` **subida a GitHub** (`24c7749`).

### UART reparado y verificado

- `dtoverlay=disable-bt` + `enable_uart=1` en `/boot/firmware/usercfg.txt`
- `/etc/udev/rules.d/99-rvr.rules` → `/dev/rvr` → `ttyAMA0` (PL011)
- `bluetooth.service` deshabilitado (no había adaptador registrado)
- Verificado con paquetes crudos: el RVR responde con checksum válido

Falsa alarma que costó tiempo: `uart0_pins` queda con `brcm,pins` vacío tras
`disable-bt`. Decompilando el overlay se ve que **es intencional** — el firmware
asigna los pines, no el kernel. Los cero bytes iniciales eran simplemente que
**el robot estaba dormido**.

### Odometría: de 3.85 Hz a 16.59 Hz con una línea

| `interval` | Frecuencia | σ |
|---|---|---|
| 250 ms (original) | 3.85 Hz | 1.7 ms |
| 100 ms | 9.94 Hz | 2.4 ms |
| **60 ms (elegido)** | **16.59 Hz** | **2.8 ms** |
| 50 ms | no arranca | — |

El firmware cuantiza a múltiplos de 20 ms. Medido también a nivel del SDK sin ROS:
resultado **idéntico**, lo que demuestra que **el anti-patrón del event loop NO era
el cuello de botella**, como afirmaba la auditoría.

Cierra el riesgo «115200 baud no aguanta 20 Hz»: 125 paquetes/s a 60 ms, holgado.

### Commits en `migracion-ros2`

```
24c7749  Sensores: bajar el intervalo de streaming de 250 ms a 60 ms
67c8776  UART: usar /dev/rvr en lugar de /dev/ttyS0
```

### Pendiente

1. ~~Subir `migracion-ros2`~~ ✅ hecho (`24c7749` en GitHub).
2. **Fase 0.3 (bloqueante)** — imagen `dd` de la microSD antes de reflashear.
3. ~~Prueba de estabilidad larga~~ ✅ **SUPERADA**: 12 min, 11 962 mensajes a 16.59 Hz,
   **0 huecos**, **0 discontinuidades de secuencia**, **0 mensajes perdidos**, RSS plano
   en 53 MB, temperatura 55.5–57.9 °C. Evidencia en
   `00_auditoria/evidencia/mediciones_banco/estabilidad_12min_2026-07-29.txt`.
4. **Sin medir:** el impacto de las 48 llamadas a `asyncio.run()` en la latencia de
   `cmd_vel`. No afirmar nada sobre ello sin datos.
5. **Sin verificar:** que la parada de emergencia de la web esté rota.

---

## 2026-07-29 (mañana) — Auditoría inicial y creación del repositorio

**Fase 00 — completada.** Repositorio publicado en
<https://github.com/Bura-hub/Atriz_migracion_ros2> (privado), commit `f714a74`.

### Qué se hizo

- Auditoría completa del sistema: hardware, SO, arranque, rendimiento, térmica,
  almacenamiento, red, UART, software y logs.
- Auditoría del repositorio `Atriz_rvr` (3 paquetes catkin, ~1650 líneas de driver).
- Auditoría de la plataforma web `Atriz_web_server` (rama `pruebas`).
- Transcripción del `MANUAL SPHERO.docx` a Markdown, con anotaciones de auditoría.
- Análisis de compatibilidad del SDK de Sphero con Python 3.12.
- Creación de este repositorio con auditoría, plan, manual y respaldos.

### Qué se verificó

| Medición | Valor |
|---|---|
| Temperatura en reposo-medio | 59.9 °C estable (5 muestras) |
| Throttling / under-voltage | 0 eventos en `dmesg` |
| CPU a 600 MHz | **59.6 %** del tiempo (`time_in_state`) |
| Bloqueo global por I/O | **46.97 s** en 42 min de uptime ocioso |
| Journal | 785 MB, `journald.conf` vacío |
| Arranque | 6.1 s kernel + 29.5 s userspace |
| Tareas en ejecución | 273, con ROS parado |
| Sesiones gráficas | 2 simultáneas (gdm + sphero) |
| WiFi | -62 dBm, 797 reintentos Tx, power-save **on** |
| `dtoverlay=disable-bt` | **ausente** en todos los ficheros de boot |
| `usercfg.txt` | **vacío** |
| Adaptador Bluetooth | **ninguno** (`hciconfig -a` sin salida), `bluetoothd` activo 2m21d |
| `/dev/serial0` | **no existe** |
| Driver YDLIDAR en el sistema | **no existe** (`find` → 0 resultados) |
| SDK Sphero: imports de ROS | **0** de 103 ficheros |
| SDK Sphero: patrones rotos en Py3.12 | **0** `@asyncio.coroutine`, **0** `loop=`, **0** `yield from` |
| SDK Sphero: `get_event_loop()` | 4, de los cuales 3 en el backend `observer` no usado |

Salidas crudas en [`00_auditoria/evidencia/`](00_auditoria/evidencia/).

### Decisiones tomadas

- **Migrar a Ubuntu Server 24.04 + ROS 2 Jazzy** (soporte hasta mayo 2029).
- **Reinstalar sobre la misma microSD**, no comprar tarjeta nueva.
  Reversión mediante imagen `dd` + el manual original.
- **La web hablará por rosbridge + roslibjs**, no por SSH.
- **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total, coordinación en el servidor.
- Alcance objetivo para un robot: teleoperación + telemetría + LIDAR + SLAM + Nav2.
- **Sin cámara** en los robots (confirmado): no se instala `web_video_server`.

### Pendiente para la próxima sesión

1. **Fase 0.1** — aplicar `dtoverlay=disable-bt` + regla udev `/dev/rvr`, deshabilitar
   `bluetooth.service`. Validar 10 min de `/odom` sin cortes. Requiere `sudo` y reinicio.
2. **Fase 0.3 (bloqueante)** — imagen `dd` de la microSD antes de reflashear.
3. Commitear o descartar los 6 cambios sueltos de `Atriz_rvr`
   (respaldados en `04_respaldo/sin_commitear/`).

### Riesgos abiertos

- **Go/no-go de toda la migración:** que el SDK de Sphero funcione en Python 3.12.
  El análisis estático es muy favorable, pero **no está verificado en ejecución**.
  Se prueba al inicio de la Fase 1, antes de portar una sola línea del driver.
- **Sin verificar:** que la parada de emergencia de la web esté realmente rota.
  Los nombres de topic no coinciden (`/rvr/emergency_stop` vs `is_emergency_stop`),
  pero no se ha probado en banco. Es seguridad — verificar como prioridad.
- La credencial del usuario `sphero` está expuesta en GitHub público y **no se ha rotado**.
