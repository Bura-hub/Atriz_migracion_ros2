# Manual Atriz — Sphero RVR sobre Raspberry Pi

> **Sustituto de `MANUAL SPHERO.docx`.** Se escribe de forma incremental: cada capítulo
> aparece aquí **solo después de haberse ejecutado y verificado** en la máquina real.
>
> | Cap. | Contenido | Estado |
> |---|---|---|
> | 0 | Convenciones y hardware | ✅ verificado |
> | 1 | Enlace UART Pi ↔ RVR | ✅ **verificado 2026-07-29** |
> | 2 | Ritmo de telemetría | ✅ **medido 2026-07-29** |
> | 3 | Flasheo de Ubuntu Server 24.04 | ⏳ no escrito |
> | 4 | Higiene del SO (headless, governor, journal) | ⏳ no escrito |
> | 5 | ROS 2 Jazzy y workspace colcon | ⏳ no escrito |
> | 6 | Driver del RVR en `rclpy` | ⏳ no escrito |
> | 7 | URDF y árbol TF | ⏳ no escrito |
> | 8 | YDLIDAR X2 | ⏳ no escrito |
> | 9 | SLAM y Nav2 | ⏳ no escrito |
> | 10 | rosbridge y plataforma web | ⏳ no escrito |
> | 11 | Arranque automático con systemd | ⏳ no escrito |
> | 12 | Clonado a los 16 robots | ⏳ no escrito |
>
> Los capítulos 1 y 2 se validaron sobre **Ubuntu 20.04 + ROS Noetic**. La configuración
> de arranque es idéntica en 24.04; lo único que cambia es que `usercfg.txt` y
> `syscfg.txt` pueden no existir y todo va en un único `config.txt` — **verificar al
> llegar al capítulo 3**.

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

**a) Liberar el PL011 del Bluetooth.** En `/boot/firmware/usercfg.txt`:
```
dtoverlay=disable-bt
enable_uart=1
```

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

$ dmesg | grep -i ttyAMA
[    1.562830] fe201000.serial: ttyAMA0 at MMIO 0xfe201000 (irq = 14) is a PL011 rev2

$ systemctl is-active bluetooth
inactive
```

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

### 2.5 Aplicado

`atriz_rvr_driver/scripts/Atriz_rvr_node.py:1313` → `interval=60`. Commit `24c7749` en
`migracion-ros2`. En el port a `rclpy` pasa a ser el valor por defecto del parámetro
`streaming_interval_ms`.

---

## Capítulos 3–12

⏳ **No escritos todavía.** Se redactan al ejecutar las fases 1–6 del
[plan](../01_plan/PLAN_MIGRACION_ROS2.md), capítulo a capítulo, tras verificar cada paso.

Hasta entonces, para reconstruir el sistema **Noetic** el procedimiento válido es el
[manual original anotado](MANUAL_SPHERO_transcripcion.md), aplicándole las correcciones
marcadas en sus bloques `⚠️ AUDITORÍA` — en particular los nombres de paquete de los
comandos de ejecución, que ya no existen.
