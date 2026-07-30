# Bitácora

Una entrada por sesión de trabajo. Formato: qué se hizo, qué se verificó, qué quedó pendiente.

---

## 2026-07-30 — Instalación de 24.04: etapas A, B y C recorridas y verificadas

**El sistema nuevo está instalado y a punto.** Ubuntu Server 24.04.4 LTS · aarch64 ·
Python 3.12.3 · `rvr-01`. Los capítulos **1, 3, 4 y 8** del manual dejan de estar
NO VERIFICADO. Falta el go/no-go del SDK (Etapa D), que es el siguiente paso.

### Los dos scripts fallaban justo donde tocaba usarlos

Ambos con la misma raíz: **fallo silencioso**.

**`fase_0_1_fix_uart.sh` abortaba en el paso 1/4.** Tenía
`USERCFG=/boot/firmware/usercfg.txt` fijo. En 24.04 ese fichero no existe, así que el `grep`
fallaba, caía al `else`, y el `cp -a` sobre un fichero inexistente mataba el script por
`set -euo pipefail` — **antes de escribir la regla udev**. Síntoma: `/dev/rvr` no aparecía.

**`fase_1_higiene_so.sh` no apagaba el power-save del WiFi.** El `ExecStart` era
`iw ... || true`, y **`iw` no viene instalado en Ubuntu Server 24.04**. El
`wifi-no-powersave.service` quedaba en verde sin hacer nada, para siempre. Ahora instala `iw`
(esperando el lock de dpkg, que en un robot recién grabado lo tiene `unattended-upgrades`),
quita el `|| true`, **comprueba el efecto real**, y acumula los pasos no aplicados para
imprimirlos al final y salir con código 1. Antes terminaba en verde pasara lo que pasara.

### Por qué no existe `usercfg.txt` — la respuesta, con evidencia

No falta: **Ubuntu abandonó el esquema en 24.04.** En 20.04, `config.txt` decía «DO NOT
modify» y terminaba en `include syscfg.txt` + `include usercfg.txt`, gestionados por
**`pibootctl`**. En 24.04 `pibootctl` **no se instala**, `config.txt` es la plantilla upstream
de Raspberry Pi OS (`vc4-kms-v3d`, `camera_auto_detect`, `[pi02]`, `[cm4]`) y **no tiene
ninguna línea `include`**. Búsqueda en todo el sistema: cero resultados.

**Crear `usercfg.txt` a mano sería un fichero fantasma** que el firmware nunca lee.

Y **la cabecera `[all]` es obligatoria**: la imagen termina en `[cm4]`, así que lo añadido al
final sin `[all]` quedaría restringido a esa placa y **no se aplicaría en un Pi 4** — existiría
en el fichero sin hacer nada. El script ahora respeta las secciones al comprobar si una clave
está activa; un `grep` normal habría dado por bueno un `disable-bt` colgando bajo `[cm4]`.

Dato colateral útil: `enable_uart=1` estaba en **ambas** versiones. Lo único que faltó siempre
fue `disable-bt`.

### `unattended-upgrades` viene activo y actualizó el kernel solo

Durante la propia sesión instaló 8 lotes de paquetes en 4 minutos, incluido
`linux-image-6.8.0-1060-raspi` sobre un sistema corriendo el `1047`, dejando
`/var/run/reboot-required`.

Obligó a reordenar el plan: **cerrar las actualizaciones y reiniciar antes de tocar el
device-tree**, o un mismo reinicio aplica dos cambios y un fallo posterior no es atribuible
(regla nº4). Nuevo apartado 3.5.1 del manual. El capítulo 4 lo deshabilita.

También aprovechó que `dtoverlay=disable-bt` **ya estaba en efecto** (editado desde Windows
antes del primer arranque) para ahorrarse un reinicio: la regla udev y los `systemctl` surten
efecto al instante, así que el script ahora solo pide reiniciar cuando de verdad hace falta.

### Verificado sobre el robot real

| Prueba | Resultado |
|---|---|
| `uart0` | `/soc/serial@7e201000` (PL011) · mini-UART `disabled` |
| `/dev/rvr` | → `ttyAMA0` |
| `raw_uart.py` | **el RVR CONTESTA (55 bytes)** · firmware `09 00 01 01` = **9.1.462** |
| `x2_parse.py` | **1144/1144 checksums = 100 %**, 2970 muestras/s, **11.48 Hz**, 1.39° |
| Higiene | `multi-user.target`, governor `performance`, `Power save: off`, `cloud-init` fuera, timers de `apt` fuera, `noatime`, `systemctl --failed` vacío |

El número de bytes de `raw_uart.py` varía entre ejecuciones (46 en 20.04, 55 aquí) porque el
RVR intercala notificaciones asíncronas. Lo que importa es que haya respuesta con checksum
válido, no la cifra.

### `x2_parse.py` mentía, y ya no

Imprimía **480 Hz** de frecuencia de giro en 20.04 y **741 Hz** en 24.04, para un sensor cuya
especificación son 6–12 Hz. Calculaba la mediana de los intervalos de llegada de paquetes, que
salen del buffer USB **a ráfagas** de ~1.3 ms. Ahora divide vueltas entre duración: **11.48
Hz**, coincidiendo con las 138 vueltas contadas a mano el 2026-07-29.

Queda la lección general: **un timestamp tomado al leer de un buffer no mide cuándo ocurrió el
evento.** `CLAUDE.md` pasa de «dos herramientas mienten» a una.

### Un falso positivo propio, y por qué se deja escrito

El mecanismo de fallo ruidoso que se añadió al script de higiene **reportó
`power-save NO quedó apagado` cuando sí lo estaba**. La causa era el verificador: buscaba
`power save:` en minúsculas e `iw 6.7` imprime `Power save: off`. Corregido con `grep -oi`.

Se documenta porque es el resultado honesto: el mecanismo funcionó a la primera y lo primero
que encontró fue a sí mismo. Sigue siendo preferible a un verificador que da verde mintiendo,
que es exactamente lo que hacía el script antes.

Segundo defecto del mismo estilo: `systemctl is-enabled` de una unidad ausente imprime
`not-found` **y** sale con código ≠ 0, así que el `|| echo no` concatenaba ambas cosas en la
misma variable.

### No se podía hacer `git push`

El sistema nuevo no tenía credenciales: `git fetch` fallaba con `could not read Username`, sin
credential helper, sin `~/.git-credentials` y con `~/.ssh/authorized_keys` **vacío**. El
respaldo de la Fase 0.3 copiaba `~/.ssh` pero **no el token**.

Corregido en `fase_0_3_respaldo.sh` (respalda `~/.git-credentials` y `~/.gitconfig`), y
documentado en `CLAUDE.md` e `INSTALACION.md` §B5 como paso propio de toda instalación nueva.
El script también deja de crear un `estado_sistema_*.txt` nuevo cuando el contenido no ha
cambiado: seis ejecuciones dejaron seis ficheros idénticos salvo la fecha.

### Estado de los tres repositorios — nada se perdió al reflashear

Verificado con `git ls-remote` contra GitHub:

| Repo | Rama | Commit |
|---|---|---|
| `Atriz_rvr` | `main` | `6f48ae1` |
| `Atriz_rvr` | `migracion-ros2` | `24c7749` |
| `Atriz_rvr` | `wip/scripts-estudiantes` | `62e0313` |
| `Atriz_web_server` | `pruebas` | `924d659` |

Coinciden exactamente con lo documentado en `TRASPASO.md`. El stash rescatado sobrevivió.

### Nueva carpeta de evidencia

`00_auditoria/evidencia_24_04/`, con su `README.md`, separada de `00_auditoria/evidencia/`
(el sistema viejo). **Comparar 24.04 contra los números de 20.04 es la deriva que este
repositorio existe para evitar**, así que la separación es deliberada y está avisada en los
seis sitios donde el manual pide «comparar con la línea base».

Línea base de 24.04 recién instalado: userspace **1 min 39 s** (`cloud-final` = 1 min 7 s),
187 tareas, journal 17.7 MB, `io.full total` 74.6 s / 34 min, governor `ondemand`,
`graphical.target`, 63.7 °C sin throttling.

### Pendiente

1. **Etapa D — el GO/NO-GO del SDK en Python 3.12.** Es el siguiente paso y el punto de
   decisión de toda la migración. No instalar ROS 2 antes.
2. **Medir la Etapa C con contadores a cero:** arranque, tareas y presión de I/O tras el
   reinicio. Los números pre-reinicio incluyen todo el trabajo de `apt` y no sirven.
3. **Confirmar si la contraseña de `sphero` se rotó de verdad** al grabar la imagen. No se
   puede comprobar desde el sistema; hay que preguntarlo. En cualquier caso sigue pendiente
   purgarla del historial de `Atriz_web_server`.
4. **Anotar dónde está guardada la imagen `dd`** (dos copias). Hay una tabla vacía esperándolo
   en `RECUPERACION.md`. Una imagen que nadie encuentra no es un respaldo.
5. La regla udev de `/dev/ydlidar` por `ID_PATH` está **propuesta y NO VERIFICADA**. Falta
   comprobar que el `ID_PATH` coincide entre dos robots distintos; si no, no es clonable en la
   imagen dorada y habría que generarla en `first-boot.sh`.
6. Siguen abiertas las decisiones de `01_avanzar.py` / `wip/scripts-estudiantes` y de
   `carro.py` / `prueba.py`.

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

### LIDAR X2 verificado — por primera vez en el proyecto

Nunca se había comprobado. Detectado como CP2102 en `/dev/ttyUSB0` y validado
decodificando el protocolo X2 a mano, **sin instalar el driver ROS**:

| Métrica | Resultado |
|---|---|
| Checksums válidos | **1147 / 1147 = 100 %** |
| Muestras | **2998/s** (especificación: 3000/s) |
| Giro | 138 vueltas en 12.1 s = **11.4 Hz** |
| Puntos por vuelta | 263 → resolución angular **1.37°** |
| Distancias | 0.445 – 3.158 m, mediana 1.205 m |

**Con esto, todo el hardware del robot está verificado.** Lo que queda es software.

Corrección documentada: `x2_parse.py` imprime "480.72 Hz de giro", que es **falso** —
mide intervalos de llegada de paquetes, que llegan a ráfagas desde el buffer USB. El
valor real sale de contar vueltas.

Aviso para la flota: el CP2102 reporta `SerialNumber "0001"`, genérico. Con 16
adaptadores iguales no se podrá hacer regla udev por serial.

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
5. ~~Sin verificar: la parada de emergencia de la web~~ 🔴 **CONFIRMADA ROTA**. Probado
   de extremo a extremo: la web publica en `/rvr/emergency_stop`, que **no existe**;
   el flag no se mueve. Con el topic correcto (`is_emergency_stop`) sí funciona.
   Falla en silencio con `200 OK`. Evidencia en `estop_2026-07-29.txt`.

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
