# Instrucciones para Claude — proyecto Atriz

Este fichero se carga automáticamente al iniciar Claude Code en este directorio.
**Léelo entero antes de actuar.**

---

## Qué es este proyecto

Laboratorio de robótica remoto: **16 robots Sphero RVR**, cada uno con una Raspberry Pi 4
y un YDLIDAR X2, gobernados desde una plataforma web. Migración de **ROS Noetic
(EOL) → ROS 2 Jazzy**.

Tres repositorios:

| Repo | Qué es |
|---|---|
| **este** (`Atriz_migracion_ros2`) | Auditoría, plan, manual, scripts, documentación de operación |
| `Bura-hub/Atriz_rvr` | Código del robot. Rama de trabajo: **`migracion-ros2`** |
| `Bura-hub/Atriz_web_server` | Plataforma web. **Se aborda al final**, no antes |

---

## Lo PRIMERO que debes hacer

1. Lee **[`TRASPASO.md`](TRASPASO.md)** — es el estado actual: qué está verificado, qué está
   roto, cuál es el siguiente paso exacto.
2. Lee **[`CHANGELOG.md`](CHANGELOG.md)** — la bitácora, para saber qué pasó y por qué.
3. Si vas a instalar el sistema desde cero: **[`INSTALACION.md`](INSTALACION.md)**.
   ⚠️ **No sigas el manual del capítulo 0 al 12** — sus capítulos están numerados por tema,
   no por orden de ejecución. `INSTALACION.md` da el recorrido real y remite a cada capítulo
   cuando toca.

**No empieces a tocar el sistema sin haber leído esos tres.** El contexto de este proyecto
tiene bastantes trampas documentadas que cuestan horas si se ignoran.

---

## Reglas del proyecto — no negociables

### 1. `git fetch` ANTES de auditar o leer código

```bash
git -C ~/atriz_ws/src/Atriz_rvr fetch origin && git -C ~/atriz_ws/src/Atriz_rvr status -sb
```

El 2026-07-29 se hizo una auditoría completa sobre un clon **5 commits por detrás** al que
**nunca se le había hecho `fetch`**. Tres hallazgos resultaron falsos y hubo que rehacer
trabajo. Es el error más caro de la historia del proyecto.

### 2. Nada se documenta sin haberse ejecutado y verificado

Si un paso no se ha probado, se marca explícitamente **NO VERIFICADO**. Nunca se presenta
una deducción como un hecho. La deriva entre documentación y código es uno de los problemas
que encontró la auditoría original — no se repite.

### 3. Nada se ejecuta sin documentarse

El recíproco de la anterior, y también se ha incumplido una vez. Si creas una rama, rescatas
un stash, o descubres algo, **va al repositorio antes de seguir**. Un mensaje de chat no es
documentación: desaparece.

### 4. Mide antes de atribuir

La auditoría culpó al bucle de asyncio del driver de que la odometría fuera a 4 Hz. Al medir
el SDK **sin ROS de por medio** salió idéntico: la causa era un solo parámetro. El arreglo
fue **una línea** en lugar de una reescritura planificada.

Antes de afirmar que X causa Y, aísla X.

### 5. Sin secretos en el repositorio

Ni contraseñas, ni claves, ni la PSK del WiFi. La credencial del usuario `sphero` **ya está
expuesta** en `Atriz_web_server` público y debe rotarse. `MANUAL_SPHERO_original.docx` la
contiene: por eso este repositorio es **privado**.

### 6. Commitea al cerrar cada fase, y actualiza el `CHANGELOG.md`

Aunque sea una línea. Es lo que permite retomar el hilo semanas después.

---

## Trampas de diagnóstico — te ahorrarán horas

**Un robot dormido parece un cable roto.** Un RVR dormido no devuelve ni un byte, síntoma
idéntico a un cable mal puesto. **Pide al usuario que apague y encienda el robot antes de
tocar configuración.** Se perdió un buen rato persiguiendo un problema de device-tree
inexistente.

**Que el nodo arranque NO prueba que el enlace funcione.** `rvr_fw_check_async.py` captura
`except (asyncio.TimeoutError, Exception)` y continúa en silencio: el nodo registra sus
topics, parece sano, y no circula ni un dato.
→ **Atajo:** el tiempo de construcción de `SpheroRvrAsync` es diagnóstico. **0 s** = el robot
responde. **~10 s** = dos timeouts de 5 s = no responde.

**No uses `pkill -f Atriz_rvr_node`.** El patrón coincide con la propia línea de comando del
shell que lo ejecuta y **mata tu terminal**. Pasó dos veces. Usa `pgrep -f "[A]triz..."` con
el corchete, o el PID directamente.

**`uart0_pins` vacío tras `disable-bt` es NORMAL.** El overlay lo vacía a propósito: en
Raspberry Pi es el *firmware* quien asigna los pines. No es un fallo, y perseguirlo cuesta
tiempo.
→ **Atajo para saber si el overlay está en efecto, sin `sudo`:**
`cat /proc/device-tree/aliases/uart0` debe dar `/soc/serial@7e201000` (PL011). Si da
`7e215040`, sigues en el mini-UART.

**`dmesg` necesita `sudo` en Ubuntu 24.04.** `kernel.dmesg_restrict=1`. Sin `sudo` responde
`read kernel buffer failed: Operation not permitted`, que leído con prisa parece que el UART
no existe. Es un permiso, no un fallo de hardware.

**En 24.04 NO existe `usercfg.txt`, y crearlo no sirve de nada.** Ubuntu abandonó el esquema
de tres ficheros: `pibootctl` ya no se instala y `config.txt` no tiene ninguna línea
`include`. Se escribe en `/boot/firmware/config.txt`, y **obligatoriamente bajo `[all]`** —
la imagen termina en `[cm4]`, así que lo añadido al final sin esa cabecera no se aplica en un
Pi 4. Existe en el fichero y no hace nada. Detalle en el manual, cap. 3.4.

**`iw` no viene instalado en Ubuntu Server 24.04.** Importa porque es lo que apaga el
power-save del WiFi. `fase_1_higiene_so.sh` lo instala; si escribes un `ExecStart` con
`iw ... || true`, el servicio queda en verde sin hacer nada, para siempre.

**`unattended-upgrades` viene ACTIVO y actualiza el kernel solo.** Durante la instalación del
2026-07-30 metió 8 lotes de paquetes en 4 minutos, incluido `linux-image-6.8.0-1060-raspi`
sobre un sistema corriendo el 1047. **Cierra las actualizaciones y reinicia antes de tocar el
device-tree**, o un mismo reinicio aplicará dos cambios y no podrás atribuir un fallo
posterior. `fase_1_higiene_so.sh` lo deshabilita.

**`/etc/netplan/*.yaml` puede venir con permisos `644`** — contiene la PSK del WiFi en texto
plano. En 20.04 estaba así; en la imagen de **Server 24.04 ya viene `600`**. Compruébalo, no
lo asumas en ninguna de las dos direcciones. `fase_1_higiene_so.sh` lo corrige si hace falta.

**Una herramienta miente** (antes eran dos). `scripts/lydar/test_lidar.py` (en `Atriz_rvr`)
reporta «Tipo de LIDAR: Desconocido» con datos perfectamente válidos — mira «bytes recibidos»
y «tasa de datos», no el tipo.
✅ `x2_parse.py` **ya está corregido** (2026-07-30): imprimía frecuencias de giro absurdas
(480 Hz, luego 741 Hz) porque promediaba intervalos de llegada de paquetes que salen a
ráfagas del buffer USB. Ahora cuenta vueltas y da 11.48 Hz. La lección que queda:
**un timestamp tomado al leer de un buffer no mide cuándo ocurrió el evento.**

---

## Herramientas de diagnóstico — úsalas antes de teorizar

En `00_auditoria/evidencia/mediciones_banco/`:

```bash
raw_uart.py      # ¿contesta el RVR a nivel de bytes?  <- EL MÁS ÚTIL
x2_parse.py      # ¿funciona el LIDAR? (sin driver ROS)
medir.py         # frecuencia y jitter de /odom e /imu
sdk_full.py 60   # ritmo del SDK con los 8 sensores
estabilidad.py   # 12 min: huecos, pérdidas, fugas de memoria
```

En `scripts/`:

```bash
fase_0_1_fix_uart.sh          # repara el UART (sudo + reinicio)
fase_1_higiene_so.sh          # headless, governor, journal, WiFi (sudo)
fase_0_3_respaldo.sh          # prepara la SD antes de reflashear
fase_1_validar_sdk_py312.py   # GO/NO-GO de la migración
diag_uart_pins.sh             # último recurso: lee GPFSEL del chip
```

---

## Valores de referencia medidos — si te desvías, algo cambió

| Métrica | Esperado | Medido el |
|---|---|---|
| `/odom` | **16.59 Hz**, σ 2.5 ms | 2026-07-29, 12 min sin huecos |
| `/scan` | ~10 Hz, 2998 muestras/s | 2026-07-29, 100 % checksums |
| CPU del driver | ~29.5 % de un núcleo | Pi 4 |
| RAM del driver | ~53 MB, plana | sin fugas en 12 min |
| Temperatura | 55–58 °C | con el driver activo |
| Puerto del RVR | `/dev/rvr` → `ttyAMA0` (PL011) | |
| Puerto del LIDAR | `/dev/ttyUSB0` (CP2102, `ID_SERIAL_SHORT=0001`) | |
| Firmware del RVR | 9.1.462 (Nordic) | |

**Línea base de Ubuntu Server 24.04 recién instalado** (2026-07-30, *antes* de la higiene del
SO). Evidencia cruda en `00_auditoria/evidencia_24_04/`:

| Métrica | 20.04 (sistema viejo) | 24.04 recién instalado | Objetivo tras la higiene |
|---|---|---|---|
| Arranque, userspace | 29.5 s | **1 min 39 s** (`cloud-final` = 1 min 7 s) | < 15 s |
| Tareas | 273 | **187** | < 120 |
| `io.full total` | 47 s / 42 min | **74.6 s / 34 min** | mucho menor |
| Journal | 784 MB | 17.7 MB | decenas de MB |
| Governor | `ondemand` | `ondemand` | `performance` |
| Default target | `graphical.target` | `graphical.target` (sí, en Server) | `multi-user.target` |
| Temperatura | 59.9 °C | 63.7 °C, `throttled=0x0` | — |
| `iw` | instalado | **no instalado** | instalado |

⚠️ **No compares 24.04 contra la línea base de 20.04.** Son dos sistemas distintos:
`00_auditoria/evidencia/` es el viejo, `00_auditoria/evidencia_24_04/` el nuevo. Mezclarlos es
lo que produce deriva entre documentación y realidad.

**Límites del hardware, no negociables:**
- El firmware del RVR **no baja de `interval=60` ms** (16.5 Hz) y cuantiza a múltiplos de 20 ms.
- El X2 entrega ~3000 muestras/s repartidas según la velocidad de giro: más lento = más
  resolución angular.

---

## Decisiones ya tomadas — no las vuelvas a plantear

| Decisión | Razonada en |
|---|---|
| Ubuntu Server 24.04 + ROS 2 Jazzy (soporte a mayo 2029) | plan, Contexto |
| Reinstalar sobre la misma microSD; reversión por imagen `dd` | plan, Fase 0.3 |
| **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total | `ARQUITECTURA.md`, D1 |
| La web habla por **rosbridge**, no por SSH | `ARQUITECTURA.md`, D2 |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final** | decisión del usuario |
| `ros-jazzy-ros-base`, **NO** `desktop` | Server headless; RViz2 va en un portátil |
| **Imagen dorada** para los 16, no aprovisionar por red | ~300 MB y 15-20 min por robot, sobre la única AP. `FLOTA.md` |
| La imagen dorada se **construye ejecutando `provision.sh`**, no a mano | Una imagen irreproducible es una caja negra. `FLOTA.md` |
| **🟢 GO: el SDK funciona en Python 3.12** (16.67 Hz) | manual, cap. 5.1 · verificado 2026-07-30 |

---

## Estilo de trabajo que espera el usuario

- **Español.** Toda la documentación y la comunicación.
- **Evidencia antes de afirmaciones.** Si dices que algo funciona, muestra la salida del
  comando que lo demuestra.
- **Corrige tus propios errores en voz alta.** En este proyecto se han retirado tres
  hallazgos de auditoría por estar equivocados, y eso es preferible a dejarlos.
- **Los pasos que requieren `sudo`, apagar la Pi o un PC externo los ejecuta el usuario**,
  no tú. Prepáraselos como script o comando exacto.
- **Avisa de las acciones físicas.** Despertar el robot enciende sus LEDs y gasta batería;
  cuando termines una prueba, para el nodo.

---

## Cómo saber en qué punto estás

### Primero: pasa el verificador. Un comando en vez de veinticinco.

```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```

**48 aserciones**, código de salida ≠ 0 si algo falla, y cada fallo viene con el comando que lo
arregla. Existe porque el 2026-07-30 se verificó este robot a mano con ~25 comandos y
aparecieron **cinco fallos silenciosos**. No repitas eso: pásalo al empezar y al cerrar.

Su regla es **comprobar el efecto, no la intención**. Si añades comprobaciones, mantenla.

### Los tres scripts de la flota

| Script | Dónde corre | Para qué |
|---|---|---|
| `preparar_tarjeta.sh --id NN` | en el **PC** | Tarjeta recién grabada: `cmdline.txt`, `config.txt`, `robot_id.txt` |
| `provision.sh` | en el robot | De un 24.04 limpio a robot terminado. Idempotente: sirve para actualizar |
| `verificar_robot.sh` | en el robot | Decide si el robot está listo |

**La imagen dorada es el atajo; `provision.sh` es la verdad.** Si divergen, gana el script y se
reconstruye la imagen. Procedimiento completo en `03_operacion/FLOTA.md`.

### Y luego el contexto

```bash
cat TRASPASO.md | head -60          # estado y siguiente paso
git -C ~/atriz_migracion log --oneline -10
git -C ~/atriz_ws/src/Atriz_rvr branch -vv    # (o ~/atriz_git si aún es ROS 1)
ls -l /dev/rvr /dev/ttyUSB0         # ¿está el hardware?
lsb_release -ds; uname -r           # ¿20.04+Noetic o 24.04+Jazzy? ¿qué kernel?
cat /proc/device-tree/aliases/uart0 # ¿está el PL011 en GPIO14/15?
```

### Antes de subir nada: comprueba que PUEDES subir

En un sistema recién instalado no hay credenciales de git, y el repositorio es privado.
`git fetch` falla con `could not read Username` y los commits se quedan solo en la tarjeta —
exactamente el riesgo que este proyecto ya sufrió con un stash.

```bash
git -C ~/atriz_migracion fetch origin && echo "OK: hay credenciales"
```

Si falla, es la persona quien lo arregla (el token es un secreto, no se pone en el repo ni se
teclea en un comando que quede en el historial):

```bash
git config --global credential.helper 'store --file ~/.git-credentials'
cd ~/atriz_migracion && git fetch origin   # Username: Bura-hub · Password: el PAT
chmod 600 ~/.git-credentials
```

`fase_0_3_respaldo.sh` respalda `~/.git-credentials` desde el 2026-07-30, para no repetirlo.
