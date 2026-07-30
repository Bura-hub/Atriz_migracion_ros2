# Manual Atriz — Sphero RVR sobre Raspberry Pi

> ⚠️ **Los capítulos están numerados POR TEMA, no por orden de ejecución.** No los sigas del
> 0 al 12: el capítulo 1 (UART) presupone un sistema ya instalado, que es el capítulo 3.
>
> **Para instalar desde cero, sigue [`INSTALACION.md`](../INSTALACION.md)**, que da el orden
> real y remite a los capítulos que toquen. Este manual es la **referencia temática**; ese
> otro es el **recorrido**.
>
> ---
>
> **Sustituto de `MANUAL SPHERO.docx`.** Se escribe de forma incremental: cada capítulo
> aparece aquí **solo después de haberse ejecutado y verificado** en la máquina real.
>
> | Cap. | Contenido | Estado |
> |---|---|---|
> | 0 | Convenciones y hardware | ✅ verificado |
> | 1 | Enlace UART Pi ↔ RVR | ✅ **verificado 2026-07-29** |
> | 2 | Ritmo de telemetría | ✅ **medido 2026-07-29** |
> | 3 | Flasheo de Ubuntu Server 24.04 | ✅ **verificado 2026-07-30** |
> | 4 | Higiene del SO (headless, governor, journal) | 📝 **escrito · NO VERIFICADO** |
> | 5 | ROS 2 Jazzy y workspace colcon | 📝 **escrito · NO VERIFICADO** |
> | 6 | Driver del RVR en `rclpy` | ⏳ no escrito |
> | 7 | URDF y árbol TF | ⏳ no escrito |
> | 8 | YDLIDAR X2 | 🟡 **hardware verificado en 20.04 y 24.04**; driver ROS pendiente |
> | 9 | SLAM y Nav2 | ⏳ no escrito |
> | 10 | rosbridge y plataforma web | ⏳ no escrito |
> | 11 | Arranque automático con systemd | ⏳ no escrito |
> | 12 | Clonado a los 16 robots | ⏳ no escrito |
>
> Los capítulos 1 y 2 se validaron sobre **Ubuntu 20.04 + ROS Noetic**. La configuración de
> arranque **no** es idéntica en 24.04: `usercfg.txt` y `syscfg.txt` **no existen** y todo va
> en un único `config.txt`, bajo una cabecera `[all]`. Resuelto y explicado en el
> **capítulo 3.4** (2026-07-30).

---

## Capítulo 0 — Convenciones y hardware

### Hardware verificado

| | |
|---|---|
| Placa | Raspberry Pi 4 Model B Rev 1.5, 8 GB |
| Almacenamiento | microSD 32 GB (medida a 83.9 MB/s secuencial) |
| Robot | Sphero RVR por UART, 115200 8N1 |
| LIDAR | YDLIDAR X2 por USB (adaptador serie) |
| Alimentación | La Pi se alimenta del puerto USB del RVR |

### Cableado UART — TX y RX van CRUZADOS

Es el error de montaje más común y el más difícil de diagnosticar. El manual original
solo lo mostraba en fotos; aquí queda escrito:

| Raspberry Pi | | Sphero RVR |
|---|---|---|
| GPIO14 / TXD — **pin físico 8** | → | **RX** |
| GPIO15 / RXD — **pin físico 10** | → | **TX** |
| GND — pin 6, 9, 14, 20, 25, 30, 34 o 39 | → | **GND** |

GND común es **obligatorio**. Sin él la comunicación falla de forma errática, no limpia,
lo que hace el diagnóstico mucho más difícil.

### Convenciones

- Cada procedimiento termina con su **verificación** y la salida esperada.
- Lo no verificado se marca **NO VERIFICADO**; nunca se presenta como hecho.
- Rutas y nombres de paquete se copian de la terminal, no de memoria.

---

## Capítulo 1 — Enlace UART Pi ↔ RVR

### 1.1 El problema que hay que evitar

La Raspberry Pi 4 tiene dos UARTs, y **la asignación por defecto es la mala para este uso**:

| UART | Hardware | FIFO | Reloj | Asignación por defecto |
|---|---|---|---|---|
| `ttyAMA0` | **PL011** | 32 bytes | estable | **reservado al Bluetooth** |
| `ttyS0` | mini-UART 16550 | 8 bytes | **derivado del VPU** | pines GPIO14/15 |

El mini-UART deriva su baudrate del reloj del núcleo VPU, **que es variable**. Cuando el
VPU cambia de frecuencia el baudrate real se desvía, y aparecen bytes corruptos,
checksums inválidos y desconexiones intermitentes.

`dtoverlay=disable-bt` mueve el **PL011 a GPIO14/15**. Su reloj no depende del VPU, así
que elimina el problema de raíz — mejor que fijar `core_freq`, que es el otro camino.

> El `MANUAL SPHERO.docx` **nunca toca `config.txt`**, así que todo el sistema anterior
> funcionó sobre el mini-UART. Es la laguna más grave del manual original.

### 1.2 Procedimiento

Automatizado en [`scripts/fase_0_1_fix_uart.sh`](../scripts/fase_0_1_fix_uart.sh).
Manualmente:

**a) Liberar el PL011 del Bluetooth.** En el fichero de configuración de arranque:

| Sistema | Fichero | Nota |
|---|---|---|
| Ubuntu 20.04 | `/boot/firmware/usercfg.txt` | `config.txt` lo carga con `include usercfg.txt` |
| **Ubuntu 24.04** | **`/boot/firmware/config.txt`**, bajo `[all]` | `usercfg.txt` **no existe** — ver cap. 3.4 |

```
[all]
dtoverlay=disable-bt
enable_uart=1
```
En 24.04 `enable_uart=1` ya viene puesto, y la cabecera `[all]` es **obligatoria** (si no, lo
añadido queda dentro de `[cm4]` y no se aplica en un Pi 4). El detalle está en el cap. 3.4.

**b) Liberar la consola serie.** En `/boot/firmware/cmdline.txt`, **quitar**
`console=serial0,115200` y dejar `console=tty1`. La imagen de Ubuntu lo trae por defecto,
así que hay que repetirlo en cada instalación nueva.
```bash
sudo systemctl disable --now serial-getty@ttyAMA0.service serial-getty@ttyS0.service
```

**c) Nombre estable del puerto.** En `/etc/udev/rules.d/99-rvr.rules`:
```
SUBSYSTEM=="tty", KERNEL=="ttyAMA0", SYMLINK+="rvr", MODE="0660", GROUP="dialout"
```
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=tty
sudo usermod -a -G dialout $USER          # requiere cerrar y abrir sesión
```

> **`/dev/serial0` NO existe en Ubuntu.** A diferencia de Raspberry Pi OS, Ubuntu no
> instala las reglas udev que crean ese symlink; hay que crear el propio. Y el código debe
> usar **`/dev/rvr`**, nunca el nombre del kernel: así, el día que cambie el UART, solo se
> edita la regla udev.

**d) Apagar el Bluetooth.** No hay adaptador y solo estorba:
```bash
sudo systemctl disable --now bluetooth.service
```

**e) Reiniciar.** El device-tree solo cambia en el arranque.
```bash
sudo reboot
```

### 1.3 Verificación

```bash
$ ls -l /dev/rvr
lrwxrwxrwx 1 root root 7 ... /dev/rvr -> ttyAMA0

$ sudo dmesg | grep -i ttyAMA
[    1.562830] fe201000.serial: ttyAMA0 at MMIO 0xfe201000 (irq = 14) is a PL011 rev2

$ systemctl is-active bluetooth
inactive
```

> ⚠️ **En 24.04, `dmesg` NECESITA `sudo`.** Ubuntu activa `kernel.dmesg_restrict=1`, así que
> sin `sudo` responde `dmesg: read kernel buffer failed: Operation not permitted`. Es un
> permiso, **no un fallo de hardware** — pero leído con prisa parece que el UART no existe.

**Atajo mejor que `dmesg`, y sin `sudo`:** preguntar al device-tree del arranque actual qué
UART está en `uart0` (los pines GPIO14/15):

```bash
$ cat /proc/device-tree/aliases/uart0        # con disable-bt aplicado
/soc/serial@7e201000                          # <- PL011. El bueno.

$ cat /proc/device-tree/soc/serial@7e215040/status
disabled                                      # <- el mini-UART, apartado
```
`7e201000` es el PL011 y `7e215040` el mini-UART. Si `uart0` apunta a `7e215040`, el overlay
**no** está en efecto. Verificado el 2026-07-30 en 24.04.

**Prueba definitiva — que el robot conteste.** Con el RVR **encendido**:
```bash
python3 00_auditoria/evidencia/mediciones_banco/raw_uart.py
```
Salida esperada:
```
→ 8d 3a 01 01 13 0d 01 a2 d8                          wake
← 8d 39 21 01 13 0d 01 00 83 d8                       ACK, error=0x00
→ 8d 3a 01 01 11 00 09 a9 d8                          get_version
← 8d 39 21 01 11 00 09 00 00 09 00 01 01 ce b1 d8     con payload
RESULTADO: el RVR CONTESTA (46 bytes). El enlace UART funciona.
```

### 1.4 Adaptar el código

El puerto pasa de `ttyS0` a `ttyAMA0`, y el driver tenía **`/dev/ttyS0` hardcodeado en 6
sitios**. Sin este cambio el robot deja de responder tras aplicar el overlay.

El que realmente importa es `serial_async_dal.py:15`, porque `Atriz_rvr_node.py` llama a
`SerialAsyncDal(loop)` **sin pasar puerto**, y usa el valor por defecto:

```python
# atriz_rvr_driver/scripts/sphero_sdk/asyncio/client/dal/serial_async_dal.py
def __init__(self, loop=None, port_id='/dev/rvr', baud=115200):
```

Los demás: `serial_observer_dal.py:17`, `scripts/rgbc_sensor_service.py:61`,
`scripts/examples/rgbc_direct_test.py:48`, y el arg `rvr_serial_port` de
`rvr_with_lidar.launch`. Quedan dos en C++ (`sphero_rvr_hw_interface.cpp:29`,
`base_controller.cpp:40`) que **no se ejecutan** y se eliminan en el port a ROS 2.

Hecho en el commit `67c8776` de la rama `migracion-ros2`.

> **No hace falta recompilar.** `devel/lib/python3/dist-packages/sphero_sdk` es un
> redirector al código fuente, no una copia — verificado con `inspect.getfile()`. Editar
> el fuente surte efecto de inmediato.

### 1.5 Tres trampas de diagnóstico

**1. El robot se duerme, y el síntoma es idéntico a un cable mal puesto.** Un RVR dormido
no contesta absolutamente nada. **Antes de tocar configuración, apaga y enciende el
robot.** Costó un buen rato en la primera puesta en marcha.

**2. El check de firmware da falsos positivos.** `rvr_fw_check_async.py` captura
`except (asyncio.TimeoutError, Exception)` y **continúa en silencio**. El arranque
*parece* correcto aunque el RVR no responda: se pierden 10 s en dos timeouts y no avisa de
nada. **Que el nodo arranque no prueba que el enlace funcione** — usa `raw_uart.py`, o
comprueba que `/odom` publica.

**3. `uart0_pins` vacío es normal, no un fallo.** Tras aplicar `disable-bt`, ese grupo
queda con `brcm,pins` de 0 bytes y el mini-UART pasa a `disabled`. Parece que ningún UART
quedara enrutado a los pines. Es **intencional**: decompilando el overlay
(`dtc -I dtb -O dts /boot/firmware/overlays/disable-bt.dtbo`) se ve que lo vacía a
propósito, porque en Raspberry Pi es el **firmware** quien asigna los pines al ver
`enable_uart=1`, y el kernel no debe tocarlos.

---

## Capítulo 2 — Ritmo de telemetría

### 2.1 El valor por defecto es demasiado lento

El driver traía `sensor_control.start(interval=250)`, que da **3.85 Hz de odometría** —
insuficiente para SLAM o navegación.

### 2.2 Barrido medido

Pi 4, 115200 baud, con **las 8 corrientes de sensores** que registra el driver
(`locator`, `quaternion`, `gyroscope`, `velocity`, `accelerometer`, `imu`,
`ambient_light`, `color_detection`):

| `interval` | Intervalo real | `/odom` | Jitter (σ) |
|---|---|---|---|
| 250 ms | 260.0 ms | 3.85 Hz | 1.7 ms |
| 200 ms | 199.9 ms | 5.00 Hz | 0.6 ms |
| 150 ms | 160.1 ms | 6.25 Hz | 0.8 ms |
| 100 ms | 100.1 ms | 9.94 Hz | 2.4 ms |
| **60 ms** | **60.1 ms** | **16.59 Hz** | **2.8 ms** |
| 50 ms | — | **el streaming no arranca** | — |

**Dos límites del firmware que conviene conocer:**

1. **Cuantiza a múltiplos de 20 ms.** Pedir 250 da 260 reales; pedir 150 da 160. Conviene
   pedir valores que ya sean múltiplos de 20.
2. **60 ms es el mínimo.** Por debajo el streaming no arranca, y **sin ningún mensaje de
   error**: te quedas sin telemetría y sin saber por qué.

### 2.3 Ancho de banda

A 60 ms con los 8 sensores: **125 paquetes/s**. A 115200 baud hay ~11.5 KB/s, de sobra.
**No hace falta recortar sensores** para llegar a 16.5 Hz.

Los dos sensores lentos (`ambient_light` y `color_detection`) se quedan en 13 Hz por
limitación propia; los seis relevantes para odometría van a 16.5 Hz.

### 2.4 Dónde NO está el cuello de botella

Merece documentarse porque la intuición engaña:

| Medición | Resultado |
|---|---|
| `interval=250`, SDK solo (sin ROS) | 3.85 Hz, σ 1.1 ms |
| `interval=250`, a través del nodo ROS | 3.85 Hz, σ 1.7 ms |
| `interval=60`, a través del nodo ROS | **16.59 Hz**, σ 2.8 ms |

El nodo ROS **no limita nada**, ni siquiera a 16.5 Hz — pese a que su bucle principal
tiene un patrón cuestionable (`run_until_complete()` dentro de un `while` con
`rospy.Rate(15)` y un `asyncio.sleep(0.1)` dentro). Conviene arreglarlo por limpieza,
pero **no era lo que frenaba la odometría**.

Reproducir:
```bash
python3 00_auditoria/evidencia/mediciones_banco/sdk_full.py 60   # SDK, sin ROS
rosrun atriz_rvr_driver Atriz_rvr_node.py &
python3 00_auditoria/evidencia/mediciones_banco/medir.py         # a traves de ROS
```

### 2.5 Estabilidad verificada

12 minutos continuos con `interval=60`:

| Métrica | Resultado |
|---|---|
| `/odom` | 11 962 msgs en 721 s = **16.59 Hz** |
| Intervalo | mediana 60.1 ms, máx 82.7 ms, σ **2.5 ms** |
| Huecos > 180 ms | **0** |
| Discontinuidades de `header.seq` | **0** |
| Mensajes perdidos | **0** de 11 965 |
| RSS del nodo | 53 MB → 53 MB (**sin fugas**) |
| CPU del nodo | 29.5 % de un núcleo |
| Temperatura | 55.5 – 57.9 °C |

Exactamente 997 mensajes por minuto en los 12 intervalos, sin una sola reconexión del
UART. Reproducir con
`00_auditoria/evidencia/mediciones_banco/estabilidad.py`.

**Nota de consumo:** un solo robot ocupa ~29 % de un núcleo del Pi 4 a 16.5 Hz. Con SLAM
y Nav2 encima habrá que medir de nuevo — es la referencia contra la que comparar.

### 2.6 Aplicado

`atriz_rvr_driver/scripts/Atriz_rvr_node.py:1313` → `interval=60`. Commit `24c7749` en
`migracion-ros2`. En el port a `rclpy` pasa a ser el valor por defecto del parámetro
`streaming_interval_ms`.

---

## Capítulo 8 — YDLIDAR X2 (parcial)

> 🟡 **El hardware está verificado en 20.04 (2026-07-29) y en 24.04 (2026-07-30); el driver
> ROS aún no se ha instalado.** Los apartados 8.4 en adelante se escriben en la Fase 3.

### 8.1 El sensor

**YDLIDAR X2 — LiDAR 2D de 360°.** Conectado por un adaptador **CP2102 USB-UART**
(Silicon Labs, `10c4:ea60`) → `/dev/ttyUSB0`, grupo `dialout`.

En Ubuntu Server 24.04 **funciona sin instalar nada**: el módulo `cp210x` viene en
`linux-modules-*-raspi` y se carga solo al conectar el adaptador. No hace falta
`linux-modules-extra`.

| Parámetro | Nominal | Medido en 20.04 | **Medido en 24.04** |
|---|---|---|---|
| Barrido | 360° | 360° | 360° |
| Muestras | 3000/s | 2998/s | **2970–2994/s** |
| Frecuencia de giro | 6–12 Hz | 11.4 Hz | **11.48 Hz** |
| Checksums válidos | — | 1147/1147 = 100 % | **1144/1144 = 100 %** |
| Canal | único | único | único |
| Baudrate | 115200 | 115200 | 115200 |
| Alcance | 0.12 – 8 m | 0.445 – 3.16 m | 0.298 – 3.54 m *(limitado por la sala)* |
| Puntos por vuelta | — | 263 → **1.37°** | **259 → 1.39°** |
| Caudal USB | — | ~7 KB/s | ~7 KB/s |

**El cambio de sistema operativo no afecta al sensor.** Evidencia cruda en
[`00_auditoria/evidencia_24_04/lidar_x2_2026-07-30.txt`](../00_auditoria/evidencia_24_04/lidar_x2_2026-07-30.txt).

### 8.2 Verificación sin instalar el driver ROS

Igual que con el RVR, se puede validar el sensor a nivel de protocolo. Es la prueba que
distingue «el lidar está roto» de «el driver está mal configurado»:

```bash
python3 00_auditoria/evidencia/mediciones_banco/x2_parse.py
```
Salida de referencia (24.04, 2026-07-30):
```
duracion            : 12.2 s
paquetes decodificados: 1144   (94/s)
checksum OK / KO    : 1144 / 0   (100.0% validos)
muestras totales    : 36234   (2970 muestras/s)
paquetes de inicio de vuelta: 140
frecuencia de giro  : 11.48 Hz   (140 vueltas en 12.2 s)
muestras por vuelta : 259   (resolucion angular 1.39 grados)
distancias validas  : 28282  (78% de las muestras)
  min 0.298 m | p50 1.619 m | max 3.539 m

VEREDICTO: el YDLIDAR X2 FUNCIONA. Protocolo valido, checksums correctos.
```

El protocolo X2 es sencillo: cabecera `0xAA 0x55`, tipo, número de muestras, ángulo inicial
y final, checksum (XOR de palabras de 16 bits), y las muestras a 2 bytes. La **distancia en
milímetros es el valor entre 4**.

> ⚠️ **Un número falso que sigue vivo.**
>
> `scripts/lydar/test_lidar.py` (en `Atriz_rvr`) reporta **«Tipo de LIDAR: Desconocido»**
> aunque los datos sean perfectamente válidos: su identificador no reconoce al X2. Fíjate en
> «bytes recibidos» y «tasa de datos» (~7000 B/s), no en el tipo.
>
> ✅ **Y uno ya corregido.** Hasta el 2026-07-30, `x2_parse.py` imprimía frecuencias de giro
> absurdas (480 Hz en 20.04, 741 Hz en 24.04) porque calculaba la **mediana de los intervalos
> de llegada de paquetes**, y esos paquetes salen del buffer USB **a ráfagas** de ~1.3 ms. Ya
> no: ahora divide vueltas entre duración, que es lo que hay que hacer, y da **11.48 Hz** —
> coincidiendo con las 138 vueltas contadas a mano en la sesión de 20.04. La lección general:
> **un timestamp tomado al leer de un buffer no mide cuándo ocurrió el evento.**

### 8.3 Resolución angular — un margen de mejora real

El X2 entrega **~3000 muestras/s pase lo que pase**. Eso significa que la resolución angular
es **inversamente proporcional** a la velocidad de giro:

| Giro | Puntos/vuelta | Resolución |
|---|---|---|
| **11.4 Hz** (actual) | 263 | 1.37° |
| 10.0 Hz | 300 | 1.20° |
| **7.0 Hz** | **428** | **0.84°** |

Para mapear un laboratorio fijo, donde el robot se mueve despacio, **la resolución angular
importa más que la frecuencia de refresco**. Merece la pena probar 7 Hz y comparar la nitidez
del mapa.

> **NO VERIFICADO:** si el driver consigue fijar la velocidad del motor en un X2 de canal
> único, o si viene fija por hardware. Los launch del repo piden `frequency: 10.0`.

### 8.4 Si el lidar no gira

El X2 alimenta su motor por la línea **DTR** del adaptador USB (de ahí el
`support_motor_dtr: true` de los launch). No todos los adaptadores la exponen.

**El adaptador es el primer sospechoso, no el lidar.**

### 8.5 Driver ROS

⏳ **Pendiente, Fase 3.** `YDLidar-SDK` + `ydlidar_ros2_driver` (rama `humble`, funciona en
Jazzy), con `params/X2.yaml`.

---

## Capítulos 3, 4 y 5 — la instalación

> 📝 **ESCRITO PERO NO VERIFICADO.** Estos tres capítulos se redactaron **antes** de
> ejecutarlos, a partir de lo aprendido en Ubuntu 20.04 y de la documentación oficial de
> Ubuntu y ROS 2. **Nadie los ha ejecutado todavía en 24.04.**
>
> Al recorrerlos por primera vez: **verifica cada paso y corrige este documento en el
> mismo momento**. Cuando un apartado quede confirmado, cambia su marca a ✅ y anota la
> fecha. Si algo no funciona como está escrito, **corrígelo aquí antes de seguir** — no en
> un mensaje de chat.
>
> Los puntos con más probabilidad de diferir están marcados **⚠️ COMPROBAR**.

---

## Capítulo 3 — Flashear Ubuntu Server 24.04 LTS

### 3.1 Qué imagen y por qué

**Ubuntu Server 24.04 LTS arm64.** No Desktop.

El manual original instalaba Server y luego añadía `ubuntu-desktop` + `xrdp` a mano para
tener escritorio remoto. Esa decisión resultó ser la causa nº1 de la lentitud del sistema:
dos sesiones gráficas simultáneas, ~120 procesos GUI, 273 tareas con ROS parado. **No se
repite.** El acceso es por SSH, y RViz2 se ejecuta desde un portátil.

ROS 2 Jazzy tiene soporte hasta **mayo de 2029** y su plataforma de referencia es 24.04.

### 3.2 Grabar la tarjeta

Con **Raspberry Pi Imager** en un PC:

| Campo | Valor |
|---|---|
| Dispositivo | Raspberry Pi 4 |
| Sistema operativo | Other general-purpose OS → Ubuntu → **Ubuntu Server 24.04.x LTS (64-bit)** |
| Almacenamiento | la microSD (mínimo 32 GB) |

En **«Editar ajustes»**:
- Usuario **`sphero`**, con una contraseña **nueva** — la del manual original está
  comprometida (aparece en un repositorio público)
- Hostname: **`rvr-01`** (y `rvr-NN` para el resto de la flota)
- WiFi: SSID y contraseña. **Preferir 5 GHz**
- **Activar SSH**
- Zona horaria y teclado

> Dejar que el Imager configure el WiFi ahorra tener que escribir netplan a mano.

### 3.3 ⚠️ COMPROBAR — antes del primer arranque, editar `cmdline.txt`

**Este paso es crítico y fácil de olvidar.** Con la tarjeta aún en el PC, monta la partición
FAT (`system-boot` o `boot/firmware`) y edita **`cmdline.txt`**:

**Quitar `console=serial0,115200`.** La imagen de Ubuntu lo trae por defecto y **reserva el
UART para la consola del sistema**, dejándolo inutilizable para el RVR. Debe quedar
`console=tty1`.

Es el único acierto importante del manual original, y hay que repetirlo en cada instalación.

### 3.4 ✅ Configuración de arranque en 24.04 — **verificado 2026-07-30**

**En 24.04 hay un único `/boot/firmware/config.txt`, editable, y `usercfg.txt` NO existe.**
Confirmado sobre Ubuntu Server 24.04.4: los únicos `.txt` de la partición de boot son
`cmdline.txt` y `config.txt`, y una búsqueda en todo el sistema (`find / -name 'usercfg*'`)
no devuelve nada.

**Por qué cambió.** No es que el fichero falte: Ubuntu **abandonó el esquema de tres
ficheros**. En 20.04 el `config.txt` empezaba con «Please DO NOT modify this file» y
terminaba con:

```
include syscfg.txt      ← lo gestionaba la utilidad pibootctl
include usercfg.txt     ← el hueco reservado al usuario
```

En 24.04 el paquete **`pibootctl` ya no se instala**, y el `config.txt` nuevo es la plantilla
*upstream de Raspberry Pi OS* (se reconoce por `dtoverlay=vc4-kms-v3d`,
`camera_auto_detect`, `display_auto_detect`, y las secciones `[pi02]` y `[cm4]`). **No
contiene ninguna línea `include`.**

> 🔴 **No crees `usercfg.txt` a mano.** Sin un `include` que lo cargue, el firmware nunca lo
> lee: sería un **fichero fantasma** que hace creer que la configuración está aplicada
> cuando no lo está. Escribe en `config.txt`.

**Comprueba qué existe antes de editar:**
```bash
ls -l /boot/firmware/*.txt
grep -n 'include' /boot/firmware/config.txt      # en 24.04: sin resultados
```

**Añade al final de `config.txt`, y OBLIGATORIAMENTE bajo una cabecera `[all]`:**
```
[all]
dtoverlay=disable-bt
```

> ⚠️ **La cabecera `[all]` no es decorativa.** `config.txt` se divide en secciones de placa
> (`[pi4]`, `[cm4]`, `[pi02]`…) y una línea solo se aplica si está antes de cualquier
> sección, dentro de `[all]`, o dentro de la sección de **esta** placa. La imagen de 24.04
> **termina en `[cm4]`**, así que lo que se añada al final sin `[all]` quedaría dentro de
> `[cm4]` y **no se aplicaría en un Pi 4**. Existiría en el fichero y no haría nada.

**`enable_uart=1` ya viene puesto** en el primer `[all]` de la imagen de 24.04 — no hay que
añadirlo. (También estaba en 20.04, en el `[all]` de defaults y en `syscfg.txt`. Lo único que
faltó siempre fue `disable-bt`.)

El razonamiento completo está en el **capítulo 1**. Resumen: sin `disable-bt`, el RVR queda
en el mini-UART, cuyo baudrate deriva con el reloj del VPU.

**Se puede hacer desde Windows**, con la tarjeta en el PC: `config.txt` está en la partición
FAT (`system-boot`), y basta el Bloc de notas. Lo que **no** se puede hacer desde Windows es
la regla udev ni los `systemctl` — eso vive en la partición ext4 y necesita el sistema
arrancado (paso 1.2c, o `scripts/fase_0_1_fix_uart.sh`).

> ℹ️ **La edición sobrevive a las actualizaciones.** `dpkg -S /boot/firmware/config.txt` no
> encuentra dueño: la partición de boot la genera `flash-kernel`, no un paquete. Verificado
> el 2026-07-30 — una actualización de kernel reescribió todos los `.dtb`, `.elf` e
> `initrd.img` (dejando `.bak` de cada uno) y **no tocó `config.txt`**.

### 3.5 Primer arranque

```bash
ssh sphero@<ip>
```

Para encontrar la IP: mírala en el router (y aprovecha para **crear la reserva DHCP por
MAC** — con 16 robots es la única forma sensata), o usa `ping rvr-01.local` si mDNS responde.

⚠️ El primer arranque de Ubuntu Server tarda: `cloud-init` hace su trabajo inicial. Espera
un par de minutos antes de dar por perdida la conexión. Medido el 2026-07-30: **1 min 39 s de
userspace**, de los cuales `cloud-final.service` se lleva **1 min 7 s**.

### 3.5.1 🔴 Termina las actualizaciones ANTES de tocar el UART — verificado 2026-07-30

```bash
sudo apt update && sudo apt full-upgrade -y
cat /var/run/reboot-required.pkgs 2>/dev/null    # ¿pide reinicio? ¿por qué paquete?
sudo reboot
```

**Por qué es su propio apartado.** La imagen de 24.04 trae `unattended-upgrades`
**habilitado y activo**, y en cuanto el robot tiene red empieza a instalar por su cuenta. En
esta instalación metió ocho lotes de paquetes en cuatro minutos, incluido un **kernel nuevo**:

```
corriendo:  6.8.0-1047-raspi
instalado:  linux-image-6.8.0-1060-raspi        ← lo puso unattended-upgrades
/var/run/reboot-required.pkgs: linux-image-6.8.0-1060-raspi, linux-base
```

Si reinicias después de cambiar el device-tree sin haber cerrado esto, ese reinicio aplica
**dos cambios a la vez**: el overlay del UART y un kernel distinto. Si luego el RVR no
responde, no hay forma de saber cuál fue la causa — y este proyecto ya perdió tiempo
atribuyendo un síntoma a la causa equivocada (regla nº4: *aísla X antes de decir que X causa
Y*). **Un cambio por reinicio.**

> El capítulo 4 deshabilita `unattended-upgrades`, precisamente para que un robot no se
> actualice solo a mitad de un experimento. A partir de ahí las actualizaciones son manuales.

### 3.6 ✅ Verificación del capítulo 3 — **verificado 2026-07-30**

```bash
lsb_release -a                      # Ubuntu 24.04.4 LTS (noble)
uname -m                            # aarch64
python3 --version                   # 3.12.3
grep -o "console=[^ ]*" /boot/firmware/cmdline.txt   # solo console=tty1
grep -nE "disable-bt|enable_uart" /boot/firmware/config.txt
cat /proc/device-tree/aliases/uart0 # /soc/serial@7e201000  (PL011)
hostname                            # rvr-01
```

Salida real de esta instalación:

| Comprobación | Resultado |
|---|---|
| `lsb_release` | Ubuntu **24.04.4 LTS** (noble) |
| `uname -m` | `aarch64` |
| `python3 --version` | **3.12.3** — resuelve el ⚠️ COMPROBAR del go/no-go |
| `cmdline.txt` | `console=tty1` únicamente |
| `config.txt` | `enable_uart=1` (por defecto) + `dtoverlay=disable-bt` bajo `[all]` |
| `uart0` | `/soc/serial@7e201000` → PL011 activo |
| `hostname` | `rvr-01` |

Evidencia cruda en
[`00_auditoria/evidencia_24_04/`](../00_auditoria/evidencia_24_04/).

---

## Capítulo 4 — Higiene del sistema operativo

> Automatizado en [`scripts/fase_1_higiene_so.sh`](../scripts/fase_1_higiene_so.sh).
> Este capítulo explica **por qué** hace cada cosa.

Cada medida responde a algo **medido** en la auditoría del sistema anterior, no a
preferencias. Instalando Server, varias de las purgas originales ya no aplican (no habrá
GNOME ni xrdp), pero `cloud-init`, `snapd`, los timers de `apt` y el conflicto de red
**sí vienen** en la imagen Server.

### 4.1 Las medidas y su justificación

| Medida | Evidencia que la motiva |
|---|---|
| Governor a **`performance`** | La CPU pasaba **59.6 %** del tiempo a 600 MHz con `ondemand`, teniendo 60 °C y cero throttling. Causa nº1 de la sensación de lentitud |
| `journald`: `Storage=volatile` o `SystemMaxUse=32M` | **784 MB** de journal sin límite; `journald.conf` estaba vacío |
| WiFi **power-save OFF** | `Power Management: on` provocaba latencias aleatorias de 100–300 ms |
| Deshabilitar **`cloud-init`** | ~20 de los 27 s de userspace del arranque |
| Purgar **`snapd`** (y LXD si aparece) | 6 loop devices y ~11 s de arranque, sin función en un robot |
| Desactivar timers **`apt-daily`** | 1 min 27 s + 1 min 14 s martilleando la microSD periódicamente |
| **`noatime`** en `/etc/fstab` | Evita una escritura por cada lectura. Longevidad de la tarjeta |
| **Sin swap** | Evita bloqueos y desgaste de flash |
| Un solo stack de red | Estaban activos NetworkManager **y** systemd-networkd, con 6 ciclos de `wpa_supplicant couldn't grab this interface` en el journal |
| `multi-user.target` | Que no arranque nada gráfico ni por accidente |

> **Longevidad de la microSD.** Con un robot es una molestia; **con 16 es mantenimiento
> semanal**. La medición que lo justifica: **47 segundos de bloqueo global por I/O en 42
> minutos** con el sistema ocioso, causados sobre todo por el journal.

### 4.2 Ejecutar

```bash
sudo bash ~/atriz_migracion/scripts/fase_1_higiene_so.sh
sudo reboot
```

### 4.3 Verificación del capítulo 4

Compara con la línea base de `00_auditoria/evidencia/` (el sistema **antes** de optimizar):

```bash
systemd-analyze                     # antes: 29.5 s de userspace -> objetivo < 15 s
ps -e | wc -l                       # antes: 273 tareas -> objetivo < 120
cat /proc/pressure/io               # 'full total' debe ser mucho menor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # performance
iw dev wlan0 get power_save         # off
journalctl --disk-usage             # decenas de MB, no cientos
systemctl get-default               # multi-user.target
systemctl --failed                  # vacío
```

---

## Capítulo 5 — ROS 2 Jazzy y workspace

### 5.1 ⚠️ COMPROBAR — el go/no-go, ANTES de instalar ROS

**Este es el paso que decide si la migración es viable.** No instales nada de ROS 2 hasta
haberlo hecho.

```bash
sudo apt install -y python3-pip python3-venv
pip install --break-system-packages pyserial pyserial-asyncio
# (24.04 aplica PEP 668: pip requiere --break-system-packages o un venv)

# El código del robot, para tener el SDK a mano:
mkdir -p ~/atriz_ws/src && cd ~/atriz_ws/src
git clone -b migracion-ros2 https://github.com/Bura-hub/Atriz_rvr.git

# Con el RVR ENCENDIDO:
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

- **GO** → sigue con 5.2
- **NO-GO** → **PARA.** El script imprime las cuatro alternativas ordenadas por coste. Es una
  decisión de arquitectura, no un problema a improvisar.

> Contexto: el análisis estático del SDK fue muy favorable (0 patrones roubles en Python
> 3.12, un único `get_event_loop()` en la ruta usada), pero **análisis estático no es
> ejecución**.

### 5.2 Instalar ROS 2 Jazzy

⚠️ **COMPROBAR contra la documentación oficial** — el método de las claves GPG cambia entre
versiones. `apt-key add`, que usaba el manual original, **está obsoleto**.

```bash
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe -y

sudo curl -sSL -o /usr/share/keyrings/ros-archive-keyring.gpg \
  https://raw.githubusercontent.com/ros/rosdistro/master/ros.key

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools
```

> **`ros-base`, NO `desktop`.** En el sistema anterior estaban instalados `desktop-full`,
> `desktop` **y** `ros-base` a la vez: **236 paquetes**, con Gazebo y RViz en un robot que
> no tiene pantalla. RViz2 se ejecuta desde un portátil, conectándose por DDS o rosbridge.

### 5.3 Entorno

En `~/.bashrc`:
```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=1                       # ← el número de ESTE robot (1..16)
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
[ -f ~/atriz_ws/install/setup.bash ] && source ~/atriz_ws/install/setup.bash
```

**`ROS_DOMAIN_ID` distinto por robot** es una decisión de arquitectura, no un detalle: aísla
completamente cada robot en DDS. Ver `ARQUITECTURA.md`, Decisión 1.

### 5.4 Compilar el workspace

```bash
cd ~/atriz_ws
rosdep init 2>/dev/null; rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

> ⚠️ **El código de `migracion-ros2` es todavía ROS 1 (catkin).** No compilará con colcon
> hasta el port del capítulo 6. En este punto solo interesa tener el **SDK** accesible, que
> es Python puro y no necesita compilación.

### 5.5 Verificación del capítulo 5

```bash
ros2 doctor
echo $ROS_DOMAIN_ID
# En dos terminales:
ros2 run demo_nodes_cpp talker
ros2 run demo_nodes_cpp listener
ros2 topic hz /chatter              # estable
```

---

## Capítulos 6, 7 y 9–12

⏳ **No escritos todavía.** Se redactan al ejecutar las fases 1–6 del
[plan](../01_plan/PLAN_MIGRACION_ROS2.md), capítulo a capítulo, tras verificar cada paso.

Hasta entonces, para reconstruir el sistema **Noetic** el procedimiento válido es el
[manual original anotado](MANUAL_SPHERO_transcripcion.md), aplicándole las correcciones
marcadas en sus bloques `⚠️ AUDITORÍA` — en particular los nombres de paquete de los
comandos de ejecución, que ya no existen.
