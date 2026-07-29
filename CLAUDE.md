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

**Dos herramientas mienten.** `scripts/lydar/test_lidar.py` reporta «Tipo de LIDAR:
Desconocido» con datos perfectamente válidos. Y `x2_parse.py` imprime una frecuencia de giro
absurda (~480 Hz) porque mide intervalos de llegada de paquetes que salen a ráfagas del
buffer USB; el valor real se obtiene contando vueltas.

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
| Puerto del LIDAR | `/dev/ttyUSB0` (CP2102) | |
| Firmware del RVR | 9.1.462 (Nordic) | |

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

```bash
cat TRASPASO.md | head -60          # estado y siguiente paso
git -C ~/atriz_migracion log --oneline -10
git -C ~/atriz_ws/src/Atriz_rvr branch -vv    # (o ~/atriz_git si aún es ROS 1)
ls -l /dev/rvr /dev/ttyUSB0         # ¿está el hardware?
```
