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
> | 1 | Enlace UART Pi ↔ RVR | ✅ **verificado en 20.04 (2026-07-29) y en 24.04 (2026-07-30)** |
> | 2 | Ritmo de telemetría | ✅ **medido 2026-07-29** |
> | 3 | Flasheo de Ubuntu Server 24.04 | ✅ **verificado 2026-07-30** |
> | 4 | Higiene del SO (headless, governor, journal) | ✅ **verificado 2026-07-30** |
> | 5 | ROS 2 Jazzy y workspace colcon | ✅ **verificado 2026-07-30** (5.4 en espera del port) |
> | 6 | Driver del RVR en `rclpy` | ⏳ **no escrito — EN CURSO** |
> | 7 | URDF y árbol TF | ✅ **verificado 2026-07-30** · `odom → laser` resuelve. Medidas del chasis 📝 sin medir |
> | 8 | YDLIDAR X2 | ✅ **verificado 2026-07-30** — hardware Y driver ROS 2, `/scan` a 10.1 Hz |
> | 8bis | LEDs y sensores del RVR | ✅ **verificado 2026-07-30** — 11 grupos de LED a la vista, 10/11 sensores |
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
Salida real en **Ubuntu Server 24.04.4** (2026-07-30, kernel `6.8.0-1047-raspi`):
```
puerto abierto: /dev/rvr @ 115200  (CTS=n/a)
[1] bytes espontaneos en 1s: 0
[2] enviado wake #1: 8d 3a 01 01 13 0d 01 a2 d8
    <- RECIBIDO 19 bytes: 8d 00 39 21 01 13 0d 01 00 83 d8 8d 28 01 13 11 ff b3 d8
[3] enviado get_version: 8d 3a 01 01 11 00 09 a9 d8
    <- RECIBIDO 16 bytes: 8d 39 21 01 11 00 09 00 00 09 00 01 01 ce b1 d8
RESULTADO: el RVR CONTESTA (55 bytes). El enlace UART funciona.
```

El número exacto de bytes varía entre ejecuciones (46 en 20.04, 55 aquí) porque el RVR
intercala notificaciones asíncronas propias — lo que importa es que **haya** respuesta con
checksum válido, no la cifra.

> **Cómo leer la respuesta de `get_version`.** El payload `09 00 01 01` es la versión del
> firmware: **9.1.462**. Coincide con el firmware documentado del robot, así que esta salida
> confirma dos cosas a la vez: que el enlace funciona y que se está hablando con el robot
> esperado.

**Nota sobre `bytes espontaneos en 1s: 0`:** es lo normal con el robot en reposo. Cero bytes
espontáneos **no** indica problema; cero bytes **tras el wake** sí — y en ese caso el primer
sospechoso es el robot dormido, no el cable (ver 1.5).

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

> 🔴 **VERIFICADO EL 2026-07-30, Y LA RESPUESTA ES NO: esta vía de mejora NO EXISTE.**
>
> Se pidió `frequency: 10.0` al driver y `/scan` salió a **10.1–11.75 Hz** según la ventana de
> medición. Sin driver, decodificando el protocolo a mano con `x2_parse.py`, se midieron
> **11.48 Hz**. **El X2 de canal único ignora el parámetro** y gira libre.
>
> La resolución angular real, medida con el driver, es **1.42°** (255 puntos por vuelta),
> coherente con los 1.39° de `x2_parse.py`. **La tabla de arriba se queda como referencia
> teórica de la relación giro↔resolución, pero los 7 Hz / 0.84° no son alcanzables** por
> software con este sensor.

### 8.4 Si el lidar no gira

El X2 alimenta su motor por la línea **DTR** del adaptador USB (de ahí el
`support_motor_dtr: true` de los launch). No todos los adaptadores la exponen.

**El adaptador es el primer sospechoso, no el lidar.**

### 8.5 ✅ Driver ROS 2 — **instalado y verificado 2026-07-30**

**No hay paquete apt.** Comprobado: `ros-jazzy-ydlidar-ros2-driver`, `ros-jazzy-ydlidar` y
`ros-jazzy-ydlidar-sdk` no existen, y `apt-cache search ydlidar` da 0 resultados. Hay que
compilar desde fuentes, en dos pasos.

#### a) `YDLidar-SDK` — la librería C++

```bash
mkdir -p ~/src_externos && cd ~/src_externos
git clone --depth 1 https://github.com/YDLIDAR/YDLidar-SDK
cd YDLidar-SDK && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j3                      # en un Pi 4 tarda unos minutos
sudo make install && sudo ldconfig
```

Instala **132 ficheros, todo bajo `/usr/local/`**, y no pisa nada del sistema de paquetes.
Comprobado antes de ejecutarlo con `make install DESTDIR=/tmp/prueba`, que es buena costumbre
con cualquier `make install` de fuentes:

```bash
make install DESTDIR=/tmp/prueba   # simula, sin tocar el sistema
find /tmp/prueba -type f | wc -l   # ¿cuántos ficheros?
```

> 📝 **Ruido a limpiar en la imagen dorada.** Instala **17 binarios de prueba** en
> `/usr/local/bin` (`gs_test`, `tof_test`, `tri_test`, `tea_test`…) que no se usan. No hacen
> daño, pero sobran en 16 robots.

> SWIG no está instalado, así que no genera los bindings de Python (`pyydlidar`). **No hacen
> falta:** el driver de ROS 2 usa la librería C++.

#### b) `ydlidar_ros2_driver` — el nodo ROS 2

```bash
cd ~/src_externos
git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver
cp -a ydlidar_ros2_driver ~/atriz_ws/src/
rm -rf ~/atriz_ws/src/ydlidar_ros2_driver/.git   # es código de terceros
cd ~/atriz_ws && colcon build --packages-select ydlidar_ros2_driver
```

**La rama `humble` compila en Jazzy sin cambios** (47.9 s). Los avisos son de parámetros sin
usar en el código de YDLIDAR, no errores. Versiones verificadas: driver **1.0.1**, SDK
**1.2.20**. Y **trae `params/X2.yaml` de fábrica**: el X2 está soportado.

Se copia **fuera** de `Atriz_rvr`: es código de terceros y no debe mezclarse con el del
proyecto.

#### c) La regla udev de `/dev/ydlidar`

```bash
sudo cp ~/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/udev/99-ydlidar.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=tty
ls -l /dev/ydlidar          # -> ttyUSB0
```

Va por **`ID_PATH`** (el puerto USB físico), no por número de serie: el CP2102 reporta
`ID_SERIAL_SHORT=0001`, genérico, así que con 16 adaptadores una regla por serie casaría con
todos. Detalle en [`FLOTA.md`](../03_operacion/FLOTA.md), restricción 1.

**Consecuencia práctica: el lidar debe ir siempre en el mismo puerto USB de cada Pi.**

#### d) 🔴 El QoS de `/scan` — la trampa que más caro sale

**El driver publica `/scan` como BEST_EFFORT.** Un suscriptor que pida **RELIABLE** —que es el
**valor por defecto en `rclpy`**— **no recibe absolutamente nada.** DDS no los empareja.

El driver lo avisa, y es uno de los mensajes buenos de ROS 2:

```
New subscription discovered on topic '/scan', requesting incompatible QoS.
No messages will be sent to it. Last incompatible policy: RELIABILITY_QOS_POLICY
```

Un suscriptor correcto:

```python
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)
node.create_subscription(LaserScan, 'scan', cb, qos)
```

> 🔴 **Riesgo directo para la Fase 4:** si `slam_toolbox` se suscribe con RELIABLE, **no
> recibirá ni un barrido y no dará ningún error** — solo un mapa vacío. **Comprobarlo antes de
> mapear.** La primera prueba de esta sesión cayó justo en esto y concluyó que `/scan` no
> llegaba.

#### e) Verificación

```bash
ros2 launch atriz_rvr_bringup robot.launch.py
ros2 topic hz /scan                     # ~10 Hz
ros2 run tf2_ros tf2_echo odom laser    # debe resolver
```

**Resultado real (2026-07-30):**

| | |
|---|---|
| `/scan` | **10.1 Hz** · `frame_id: laser` |
| Puntos por barrido | **255**, de los cuales **226 válidos (89 %)** |
| Distancias | 0.326 – 3.134 m *(rango configurado 0.1 – 8.0)* |
| Arco | −180° a 180° · resolución angular **1.42°** |
| `tf2_echo odom laser` | `Translation: [-0.018, -0.002, 0.141]` |

> **Avisos benignos, para no perseguirlos:**
> `[error] Fail to get baseplate device information!` aparece **siempre** — el X2 de canal
> único no responde a esa consulta, y el scan funciona igual. Y
> `Single Fixed Size: 270 / Sample Rate: 3.00K` es informativo y correcto.

---

## Capítulos 3, 4 y 5 — la instalación

> | Cap. | Estado |
> |---|---|
> | **3** — Flasheo, `cmdline.txt`, `config.txt` | ✅ **RECORRIDO Y VERIFICADO 2026-07-30** |
> | **4** — Higiene del SO | ✅ **RECORRIDO Y VERIFICADO 2026-07-30** |
> | **5** — ROS 2 Jazzy y workspace | ✅ **VERIFICADO 2026-07-30.** 201 paquetes, ros2 doctor OK |
>
> Los tres se redactaron **antes** de ejecutarlos, a partir de lo aprendido en Ubuntu 20.04 y
> de la documentación oficial. Los capítulos 3 y 4 ya se recorrieron sobre la máquina real y
> **se corrigieron sobre la marcha**: el 3.4 estaba equivocado en su suposición principal, y
> el 4 escondía un paso que no hacía nada. Ambas cosas están explicadas donde ocurrieron.
>
> **El capítulo 5 sigue sin ejecutarse.** Al recorrerlo: **verifica cada paso y corrige este
> documento en el mismo momento**, cambia su marca a ✅ con la fecha, y si algo no funciona
> como está escrito, **corrígelo aquí antes de seguir** — no en un mensaje de chat.
>
> Los puntos con más probabilidad de diferir están marcados **⚠️ COMPROBAR**. Los ya
> resueltos conservan la explicación de qué se encontró, porque el *por qué* es lo que evita
> que el siguiente robot repita el problema.

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

### 3.3 ✅ Antes del primer arranque, editar `cmdline.txt` — **verificado 2026-07-30**

**Este paso es crítico y fácil de olvidar.** Con la tarjeta aún en el PC, monta la partición
FAT (`system-boot` o `boot/firmware`) y edita **`cmdline.txt`**:

**Quitar `console=serial0,115200`.** La imagen de Ubuntu lo trae por defecto y **reserva el
UART para la consola del sistema**, dejándolo inutilizable para el RVR. Debe quedar
`console=tty1`.

Resultado real en esta instalación (2026-07-30) — se hizo desde Windows, con el Bloc de notas:
```
multipath=off dwc_otg.lpm_enable=0 console=tty1 root=LABEL=writable rootfstype=ext4 rootwait fixrtc cfg80211.ieee80211_regdom=CO
```
`cmdline.txt` es **una sola línea**: no metas saltos de línea al editarlo. Y no toques el resto
de parámetros.

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

### 4.2 ✅ Ejecutar — **verificado 2026-07-30**

```bash
sudo apt install -y iw      # NO viene en Server 24.04, y el paso 4/9 lo necesita
sudo bash ~/atriz_migracion/scripts/fase_1_higiene_so.sh
sudo reboot
```

**El script termina en rojo y con código 1 si algún paso no se pudo aplicar.** Lee la sección
«PASOS NO APLICADOS» del final: haber llegado hasta el final no significa que esté todo hecho.

⚠️ **Este reinicio te deja sin SSH un par de minutos, y el robot no tiene pantalla.** El paso
9/9 valida `netplan generate` antes de dejarte reiniciar, porque el paso 5 deshabilita
`cloud-init` y en esta imagen el WiFi vive en un netplan que generó `cloud-init`. El fichero
persiste y `systemd-networkd` lo sigue leyendo, pero ten un cable de `eth0` a mano.

⚠️ **A partir de aquí las actualizaciones de seguridad son MANUALES.** El paso 7/9 deshabilita
`unattended-upgrades`, que es lo que se quiere en un robot de laboratorio (no queremos que se
actualice solo a mitad de un experimento), pero hay que saberlo:
`sudo apt update && sudo apt upgrade`.

> ℹ️ **`snapd` queda deshabilitado pero sigue instalado.** El script lo avisa e imprime el
> comando para purgarlo del todo. No lo hace por su cuenta porque `apt purge snapd` es
> irreversible sin reinstalar.

### 4.3 ✅ Verificación del capítulo 4 — **verificado 2026-07-30**

Compara con la línea base de
[`00_auditoria/evidencia_24_04/`](../00_auditoria/evidencia_24_04/) — **este mismo sistema
antes de optimizar**.

🔴 **NO compares con `00_auditoria/evidencia/`**: esa es la línea base del sistema **viejo**
(20.04 + Noetic, 29.5 s de userspace y 273 tareas). Son dos sistemas distintos y mezclar sus
números es exactamente la deriva que este repositorio existe para evitar.

```bash
systemd-analyze                     # antes: 1 min 39 s de userspace -> objetivo < 15 s
ps -e | wc -l                       # antes: 187 tareas -> objetivo < 120
cat /proc/pressure/io               # antes: 'full total' 74.6 s en 34 min
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # performance
iw dev wlan0 get power_save         # Power save: off
journalctl --disk-usage             # decenas de MB, no cientos
systemctl get-default               # multi-user.target
systemctl --failed                  # vacío
uname -r                            # ¿cambió el kernel en este reinicio?
```

**Resultado de esta ejecución, comprobado inmediatamente (sin reiniciar):**

| Medida | Antes | Después |
|---|---|---|
| Default target | `graphical.target` | ✅ `multi-user.target` |
| Governor | `ondemand` | ✅ `performance` |
| Journal | sin tope | ✅ `SystemMaxUse=32M`, recortado |
| WiFi power-save | (`iw` no instalado) | ✅ `Power save: off` |
| `cloud-init` | habilitado | ✅ `/etc/cloud/cloud-init.disabled` |
| Timers de `apt` | habilitados | ✅ `apt-daily`, `apt-daily-upgrade`, `motd-news`, `fstrim`: disabled |
| Servicios inútiles | activos | ✅ `snapd`, `ModemManager`, `avahi`, `multipathd`, `open-iscsi`, `iscsid`, `lvm2-monitor`, `unattended-upgrades`: disabled |
| `noatime` | no | ✅ en la raíz |
| netplan | 600 | ✅ 600, y `netplan generate` correcto |
| `systemctl --failed` | — | ✅ vacío |
| `/dev/rvr` | `→ ttyAMA0` | ✅ intacto: el script no toca el UART |

**Medido DESPUÉS del reinicio, con los contadores a cero** (2026-07-30, kernel
`6.8.0-1060-raspi`):

| Métrica | 24.04 recién instalado | Tras la higiene | Objetivo |
|---|---|---|---|
| Arranque, userspace | 1 min 39 s | **8.7 s** | < 15 s ✅ |
| `multi-user.target` alcanzado | 31.8 s | **8.6 s** | — |
| Servicio más lento | `cloud-final` 1 min 7 s | `snapd.seeded` 3.5 s | — |
| Journal | 17.7 MB | 14.1 MB, con tope de 32M | decenas de MB ✅ |
| Governor | `ondemand` | `performance` | ✅ |
| WiFi power-save | (`iw` no instalado) | `Power save: off` | ✅ |
| Default target | `graphical.target` | `multi-user.target` | ✅ |
| `systemctl --failed` | — | vacío | ✅ |
| Temperatura | 63.7 °C | 58.4 °C, `throttled=0x0` | < 70 °C ✅ |
| **Presión de I/O en reposo** | 2.19 s/min | **~0.00 s/min** (3 ms en 45 s) | casi cero ✅ |

**El arranque baja de 1 min 39 s a 8.7 s: 11 veces más rápido.** La causa era `cloud-init`,
tal como decía la auditoría.

#### ⚠️ Dos correcciones de metodología que salieron al medir

**1. La presión de I/O hay que medirla como RITMO, no como acumulado.** El `total` de
`/proc/pressure/io` cuenta desde el arranque, así que justo tras instalar está dominado por
`cloud-init` y `apt` y no dice nada del estado en reposo. Se mide con dos lecturas:

```bash
grep full /proc/pressure/io; sleep 60; grep full /proc/pressure/io
```
En reposo dio **3 ms en 45 segundos**. Antes, el ritmo equivalente era 2.19 s/min. La mejora es
real y grande, pero comparar los dos `total` a pelo la habría escondido.

**2. El objetivo «< 120 tareas» estaba mal planteado y se retira.** `ps -e` cuenta los hilos de
kernel, que son el suelo del sistema y no se pueden bajar:

```
ps -e total             : 168
hilos de kernel (PPID 2): 129     <- intocable
procesos de usuario     :  39     <- de los cuales ~16 son la sesión SSH y el agente
servicios en ejecución  :  15
```

Las 273 tareas de 20.04 incluían ~120 procesos de GNOME, así que allí el número sí medía algo.
En un Server headless, no. **Las métricas que sí sirven** y sustituyen a la vieja:

```bash
ps -e -o ppid= | awk '$1!=2' | wc -l                                   # procesos de usuario -> < 30
systemctl list-units --type=service --state=running --no-legend | wc -l  # servicios -> < 20
```

#### 🐛 `snapd` no se apagaba, y `systemctl` decía que sí

Tras el reinicio, `systemctl is-enabled snapd` respondía `disabled` **y el demonio estaba
corriendo**, siendo `snapd.seeded.service` el servicio más lento del arranque (3.5 s).

La causa: `snapd.service` tiene `TriggeredBy=snapd.socket`, y el script solo deshabilitaba el
servicio. **Activación por socket: apagar el servicio no sirve de nada si el socket sigue
en pie.** Hay que apagar también `snapd.socket`, `snapd.seeded.service`,
`snapd.apparmor.service` y `snapd.autoimport.service`. Corregido en el script, que además
comprueba con `is-active` en vez de fiarse de `is-enabled`.

> ℹ️ **`cloud-init` sigue diciendo `enabled` y es correcto.** Se desactiva con el fichero
> `/etc/cloud/cloud-init.disabled`, no con `systemctl`. Lo que hay que comprobar es que está
> **`inactive`**, no que esté `disabled`. Si buscas `is-enabled` te llevarás un susto y
> perseguirás un problema que no existe.

> 🐛 **El paso 4/9 tenía un bug que lo hacía inútil, y su verificador otro.** Está contado en
> el `CHANGELOG.md` del 2026-07-30. En resumen: el `ExecStart` era `iw ... || true` y `iw` no
> estaba instalado, así que el servicio quedaba en verde sin hacer nada. Al arreglarlo, el
> nuevo verificador dio un **falso positivo** por buscar `power save:` en minúsculas cuando
> `iw` imprime `Power save:`. Las dos cosas están corregidas. Se cuentan porque son el tipo de
> fallo que este proyecto persigue: **el que no se ve.**

---

## Capítulo 5 — ROS 2 Jazzy y workspace

### 5.1 🟢 El go/no-go — **GO, verificado 2026-07-30**

**Este es el paso que decide si la migración es viable.** No instales nada de ROS 2 hasta
haberlo hecho.

#### Las tres dependencias, y de dónde sale cada una

Esto importa más de lo que parece: **las tres son obligatorias**, aunque solo dos tengan que
ver con hablar con el robot.

| Módulo | Cómo se instala | Para qué |
|---|---|---|
| `pyserial` | `apt install python3-serial` *(ya viene en la imagen)* | el enlace serie |
| `aiohttp` | `apt install python3-aiohttp` | **`sphero_sdk/__init__.py` lo importa sin condiciones** |
| `pyserial-asyncio` | `pip3 install --break-system-packages pyserial-asyncio` | el backend asyncio del SDK |

```bash
sudo apt install -y python3-pip python3-aiohttp
sudo pip3 install --break-system-packages pyserial-asyncio
```

> 🔴 **`pyserial-asyncio` NO existe como paquete apt.** Comprobado el 2026-07-30:
> `apt-cache policy python3-pyserial-asyncio` no devuelve nada. Es la única dependencia que
> obliga a usar `pip`, y 24.04 aplica **PEP 668**, de ahí `--break-system-packages`.
>
> 🔴 **Instálalo con `sudo`, a nivel de SISTEMA.** Con `pip --user` acaba en `~/.local`, donde
> un servicio systemd puede no verlo según su `User=`, y en la imagen dorada quedaría
> enterrado en el home de un usuario en lugar de en el sistema. Pasó el 2026-07-30 y hubo que
> corregirlo.

> ⚠️ **`aiohttp` parece opcional y no lo es.** Solo se usa en un fichero
> (`common/firmware/cms_fw_check_base.py`) y solo para consultar la versión del firmware
> contra un **servicio web de Sphero** — nada que ver con el UART. Pero `__init__.py` importa
> todo el SDK de golpe, así que sin `aiohttp` el SDK **no se puede ni importar**.
>
> En 20.04 estaba instalado por casualidad, así que nadie había notado la dependencia. La
> primera ejecución de este paso en 24.04 dio un **NO-GO falso** por eso: el script sugería
> replantear la arquitectura del proyecto por un paquete que se instala en diez segundos.

#### El código del robot

```bash
mkdir -p ~/atriz_ws/src && cd ~/atriz_ws/src
git clone -b ros2 https://github.com/Bura-hub/Atriz_rvr.git
#            ↑ `ros2`, NO `migracion-ros2`: esa es la rama VIEJA con código de
#              ROS 1 (catkin), que no compila con colcon.

# Regla nº1 del proyecto: fetch ANTES de mirar el código
git -C ~/atriz_ws/src/Atriz_rvr fetch origin
git -C ~/atriz_ws/src/Atriz_rvr status -sb        # esperado: rama `ros2`
```

#### Ejecutarlo

```bash
# Con el RVR ENCENDIDO:
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

- **GO** → sigue con 5.2
- **NO-GO** → **PARA.** El script imprime las cuatro alternativas ordenadas por coste. Es una
  decisión de arquitectura, no un problema a improvisar.

#### Resultado real: 🟢 **GO**

```
▶ 1/6 · Entorno         Python 3.12.3 · Linux-6.8.0-1060-raspi-aarch64
▶ 2/6 · Dependencias    serial 3.5 · serial_asyncio 0.6 · aiohttp 3.9.1
▶ 3/6 · Localizar SDK   ~/atriz_ws/src/Atriz_rvr/atriz_rvr_driver/scripts
▶ 4/6 · Importar        sphero_sdk 1.0.0 — SpheroRvrAsync, SerialAsyncDal, … disponibles
▶ 5/6 · Compilar        los 103 ficheros compilan sin errores de sintaxis
▶ 6/6 · Hablar con el RVR
        SpheroRvrAsync construido en 0.0 s
        batería: 100 %
        firmware (Nordic): 9.1.462
        streaming: 99 muestras a 16.67 Hz

  GO — el SDK funciona en esta versión de Python.
```

**El dato que cierra el riesgo principal del proyecto:** la telemetría rinde **16.67 Hz en
Python 3.12 sobre 24.04**, frente a los **16.59 Hz** medidos en Python 3.8 sobre 20.04. Es el
mismo rendimiento. El análisis estático predecía un parche de ~4 líneas; resultaron ser
**cero**.

**Y el tiempo de construcción de `SpheroRvrAsync` es 0.0 s**, que según el atajo de
`CLAUDE.md` significa que el robot responde. (~10 s serían dos timeouts de 5 s = no responde.)

> **Lo que este GO NO significa.** El driver ROS sigue siendo **ROS 1 (catkin)** y no
> compilará con `colcon` hasta el port de la Fase 2. Lo que queda validado es la pieza
> insustituible: el SDK, que es lo único que sabe hablar con el RVR.

Evidencia cruda con todo el contexto en
[`00_auditoria/evidencia_24_04/04_gonogo_sdk_py312_2026-07-30.txt`](../00_auditoria/evidencia_24_04/04_gonogo_sdk_py312_2026-07-30.txt).

### 5.2.0 🔴 ANTES de instalar ROS 2: falta `noble-updates` en la imagen

**La imagen de Ubuntu Server 24.04 para Raspberry Pi viene sin el repositorio
`noble-updates`.** Verificado el 2026-07-30 en `rvr-01`: `/etc/apt/sources.list.d/ubuntu.sources`
(fechado en la creación de la imagen, no modificado por nadie) solo lista:

```
Suites: noble
Suites: noble-security
```

**Por qué rompe la instalación de ROS 2.** Las bibliotecas de runtime *sí* se actualizan desde
`noble-security` (a versiones con sufijo `.1`), pero sus paquetes `-dev`, que exigen una
versión exacta de la runtime, viven en `noble-updates`. Sin ese repositorio, `apt` solo puede
ofrecer el `-dev` de la versión original y la dependencia es insatisfacible:

```
The following packages have unmet dependencies:
 dpkg-dev    : Depends: bzip2 but it is not installable
 liblz4-dev  : Depends: liblz4-1 (= 1.9.4-1build1) but 1.9.4-1build1.1 is to be installed
 libzstd-dev : Depends: libzstd1 (= 1.5.5+dfsg2-2build1) but 1.5.5+dfsg2-2build1.1 is to be installed
 zlib1g-dev  : Depends: zlib1g (= 1:1.3.dfsg-3.1ubuntu2) but 1:1.3.dfsg-3.1ubuntu2.1 is to be installed
E: Unable to correct problems, you have held broken packages.
```

`ros-dev-tools` arrastra esos `-dev`, y **sin ellos no hay `colcon build`**: no es un problema
cosmético, impide compilar el workspace.

**El arreglo** — añadir `noble-updates` a la *primera* sección, sin tocar `noble-security`:

```bash
# ⚠️ El respaldo va FUERA de sources.list.d/. Si se deja dentro, apt imprime
#    «Ignoring file … invalid filename extension» en CADA ejecución. Es
#    inofensivo pero es ruido permanente, y en 16 robots molesta de verdad.
sudo install -d /root/respaldos-apt
sudo cp /etc/apt/sources.list.d/ubuntu.sources \
        /root/respaldos-apt/ubuntu.sources.bak-$(date +%Y%m%d)
sudo sed -i '0,/^Suites: noble$/s//Suites: noble noble-updates/' \
        /etc/apt/sources.list.d/ubuntu.sources
sudo apt update
```

> 🐛 **Aprendido a base de meter la pata el 2026-07-30:** el respaldo se dejó
> dentro de `sources.list.d/` y desde entonces cada `apt install` terminaba con
> ese aviso. Se mueve con:
> ```bash
> sudo mv /etc/apt/sources.list.d/ubuntu.sources.bak-* /root/respaldos-apt/
> ```

El `0,/patrón/s//…/` de `sed` sustituye **solo la primera aparición**, que es la del repositorio
principal. Comprobado sobre una copia antes de aplicarlo: una única línea de diferencia.

> **Compruébalo así:** tras el `apt update` deben aparecer **tres** repositorios de Ubuntu
> (`noble`, `noble-updates`, `noble-security`), no dos. Y espera que el siguiente `apt upgrade`
> ofrezca paquetes: eran los *bug fixes* que no son de seguridad, que hasta ahora no llegaban.

⚠️ **Esto afecta a los 16 robots.** Va en `provision.sh` y por tanto queda dentro de la imagen
dorada, así que solo hay que arreglarlo una vez — pero si algún día partes de una imagen limpia
de Ubuntu, te lo encontrarás otra vez.

---

### 5.2 Instalar ROS 2 Jazzy — **método actualizado 2026-07-30**

El ⚠️ COMPROBAR de este apartado estaba justificado: **el método de las claves GPG cambió**.
Hay dos vías y no son equivalentes.

#### ✅ Método recomendado: el paquete `ros2-apt-source`

Es el método oficial actual, y **para una flota es el único sensato**: es un `.deb` mantenido
por Open Robotics que instala el keyring y el fichero de sources, y **mantiene la clave
actualizada por sí solo**. Con el método manual de abajo, el día que la clave caduque
—**y ya pasó una vez, rompiendo `apt` en todas las instalaciones de ROS del mundo**— se rompen
los 16 robots a la vez y hay que entrar en cada uno a mano.

```bash
# 'universe' hace falta. En Ubuntu Server 24.04 ya viene habilitado; compruébalo:
grep -m1 Components /etc/apt/sources.list.d/ubuntu.sources    # debe incluir 'universe'

# Última versión del paquete de sources (1.2.0 el 2026-07-30):
V=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
    | grep -F '"tag_name"' | awk -F'"' '{print $4}')
CODENAME=$(. /etc/os-release && echo $VERSION_CODENAME)      # noble
curl -L -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${V}/ros2-apt-source_${V}.${CODENAME}_all.deb"

sudo apt install -y /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools
```

> **Audítalo antes de instalarlo como root.** Es buena costumbre con cualquier `.deb` de
> fuera de los repos, y con este cuesta diez segundos:
> ```bash
> dpkg-deb -c /tmp/ros2-apt-source.deb                       # qué ficheros coloca
> dpkg-deb --ctrl-tarfile /tmp/ros2-apt-source.deb | tar -t   # ¿scripts como root?
> ```
> Comprobado el 2026-07-30 en la versión 1.2.0: **no tiene ningún script de mantenedor**
> (solo `control` y `md5sums`), así que no ejecuta nada como root — únicamente coloca
> `/usr/share/keyrings/ros2-archive-keyring.gpg`, `/usr/share/ros-apt-source/ros2.sources` y
> un symlink en `/etc/apt/sources.list.d/`.
>
> La clave que trae, verificada con `gpg --show-keys`:
> ```
> pub   rsa4096 2019-05-30 [SC] [expires: 2030-06-01]
>       C1CF 6E31 E6BA DE88 68B1  72B4 F42E D6FB AB17 C654
> uid   Open Robotics <info@osrfoundation.org>
> ```
> **Caduca en junio de 2030**, después del fin de soporte de Jazzy (mayo 2029), así que no
> caducará a mitad de la vida del proyecto.

#### Método manual (solo si el paquete no estuviera disponible)

Funciona, pero **la clave hay que renovarla a mano cuando caduque**, en los 16 robots:

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

> `apt-key add`, que usaba el manual original, **está obsoleto** y ya no debe usarse en
> ninguna de las dos vías.

> **`ros-base`, NO `desktop`.** En el sistema anterior estaban instalados `desktop-full`,
> `desktop` **y** `ros-base` a la vez: **236 paquetes**, con Gazebo y RViz en un robot que
> no tiene pantalla. RViz2 se ejecuta desde un portátil, conectándose por DDS o rosbridge.

### 5.3 Entorno

🔴 **`ROS_DOMAIN_ID` distinto por robot no es un detalle, es la Decisión 1 de la arquitectura.**
Si dos robots comparten dominio, se ven entre sí en DDS y el descubrimiento multicast entre
~160 participantes sobre WiFi satura la red. Ver `ARQUITECTURA.md`, Decisión 1.

**En la flota lo fija `atriz-first-boot`**, leyendo `/boot/firmware/robot_id.txt` y escribiendo
`/etc/profile.d/atriz-robot.sh`. Ese es el mecanismo bueno: un fichero por robot, generado, no
editado a mano. Ver `FLOTA.md`.

**Pero ese servicio no está instalado en el robot de referencia** hasta que se ejecute
`fase_6_preparar_imagen_dorada.sh`. Mientras tanto, a mano en `~/.bashrc`:

```bash
cat >> ~/.bashrc <<'EOF'

# ── ROS 2 Jazzy ──────────────────────────────────────────────────────────────
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=1                       # ← el número de ESTE robot (1..16)
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
[ -f ~/atriz_ws/install/setup.bash ] && source ~/atriz_ws/install/setup.bash
EOF
exec bash          # o cierra y abre la sesión SSH
```

> ⚠️ **Si algún día existen los dos** (`~/.bashrc` y `/etc/profile.d/atriz-robot.sh`), el
> `.bashrc` gana porque se lee después — y te quedarás con un `ROS_DOMAIN_ID` fijo a 1 en un
> robot que debería ser otro. Al preparar la imagen dorada, **quita estas líneas del
> `.bashrc`** y deja solo el `source` del setup, o tendrás dos robots en el mismo dominio sin
> que nada avise. `verificar_robot.sh` compara `ROS_DOMAIN_ID` con el número del hostname
> precisamente para cazar eso.

**`RMW_IMPLEMENTATION=rmw_fastrtps_cpp`** se fija de forma explícita aunque sea el valor por
defecto de Jazzy: así el comportamiento no cambia si un día lo cambian, y queda documentado qué
middleware se está usando cuando haya que depurar la red.

### 5.4 Compilar el workspace

✅ **Con la rama `ros2` el workspace COMPILA** — es lo que hace `INSTALACION.md`, Etapa F1.

🔴 **Lo que sigue describe la rama VIEJA `migracion-ros2`**, y se conserva porque explica por
qué hubo que portar el driver. Si clonaste `ros2`, sáltatelo: `colcon build` funciona.

Con `migracion-ros2` el código es **ROS 1 (catkin)**: los tres `package.xml` declaran `catkin`
y `Atriz_rvr_node.py` tiene **99 referencias a `rospy`**, que no existe en ROS 2. `colcon
build` fallará, y es lo esperado.

Medido el 2026-07-30 sobre `migracion-ros2` (`24c7749`):

| | |
|---|---|
| `Atriz_rvr_node.py` | **1704 líneas** |
| referencias a `rospy.*` | **99** |
| llamadas a `asyncio.run()` | **48**, cada una crea y destruye un event loop |
| paquetes | 3, los tres **catkin** (no `ament`) |
| interfaces | 6 `.msg` + 20 `.srv`, todas registradas correctamente |

**Lo que sí está validado en este punto es el SDK**, que es Python puro, no necesita compilarse,
y es la pieza insustituible. El driver es código propio y por tanto reescribible.

El port es la **Fase 2 del plan** y el capítulo 6 de este manual. Cuando exista, aquí irá:

```bash
cd ~/atriz_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

> `rosdep` ya viene inicializado por `provision.sh`. Si lo haces a mano, **`rosdep update` se
> ejecuta como tu usuario, NO con `sudo`**: con `sudo` deja ficheros de root en `~/.ros` y
> después falla en silencio.

### 5.4.1 ⚠️ «Existe `setup.bash`» NO significa «ROS 2 está instalado»

En un Pi 4, instalar 509 paquetes tarda del orden de **15-20 minutos**, y `apt` los procesa en
dos fases: primero desempaqueta y luego configura. Entre una y otra, el sistema está en un
estado engañoso:

```
$ ls /opt/ros/jazzy/setup.bash        # existe ✓
$ source /opt/ros/jazzy/setup.bash; echo $ROS_DISTRO
jazzy                                  # responde ✓

$ dpkg-query -W -f='${Package} ${Status}\n' ros-jazzy-ros-base
ros-jazzy-ros-base install ok unpacked      # ← NO configurado
$ dpkg -l 'ros-jazzy-*' | grep -c '^ii'
0                                            # ← CERO paquetes terminados
```

**El fichero existe, la variable responde, y no hay ni un paquete configurado.** Pasó el
2026-07-30: se dio por terminada la instalación mirando `setup.bash` y `dpkg` decía otra cosa.

**Cómo saber de verdad si terminó:**
```bash
pgrep -af 'apt install|^dpkg'                    # vacío = apt ha soltado el sistema
dpkg -l 'ros-jazzy-*' | grep -c '^ii'            # debe ser un número grande, no 0
dpkg -l | grep -vE '^(ii|rc)' | grep -E '^[a-z]{2} '   # vacío = nada a medias
```

Los dos primeros caracteres de `dpkg -l` son el estado: **`ii` = instalado y configurado**.
`iU` o `it` significan «a medio hacer», y `apt` puede necesitar
`sudo dpkg --configure -a` si algo se interrumpió.

> **La lección, que es la de siempre en este proyecto:** un artefacto presente no prueba que el
> proceso haya terminado. Igual que un nodo que arranca no prueba que el enlace UART funcione
> (cap. 1.5), o que un servicio en verde no prueba que haya hecho su trabajo (cap. 4.3).
> **Comprueba el efecto, no el indicio.**

### 5.5 ✅ Verificación del capítulo 5 — **verificado 2026-07-30**

> 🐛 **La versión anterior de este apartado no se podía ejecutar.** Pedía
> `ros2 run demo_nodes_cpp talker`, y **`demo_nodes_cpp` NO viene en `ros-base`**: es el paquete
> aparte `ros-jazzy-demo-nodes-cpp`. Resultado real: `Package 'demo_nodes_cpp' not found`.
>
> Se sustituye por una prueba equivalente con `ros2 topic pub`/`echo`/`hz`, que vienen en
> `ros2cli` y por tanto **ya están instaladas**. Mejor para la flota: verifica lo mismo (ida y
> vuelta completa sobre DDS) sin añadir un paquete a 16 robots.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# 1. Salud general
ros2 doctor                          # -> All 5 checks passed
echo $ROS_DOMAIN_ID                  # -> el número de este robot

# 2. Que la instalación esté COMPLETA (ver 5.4.1: setup.bash no basta)
dpkg -l 'ros-jazzy-*' | grep -c '^ii'                 # -> 201, no 0
dpkg -l | grep -vE '^(ii|rc)' | grep -cE '^[a-z]{2} '  # -> 0, nada a medias

# 3. Ida y vuelta sobre DDS. En una terminal:
ros2 topic pub -r 10 /prueba_atriz std_msgs/String '{data: "hola"}'
#    y en otra:
ros2 topic echo /prueba_atriz --once
ros2 topic hz /prueba_atriz
ros2 topic info /prueba_atriz
```

**Resultado real en `rvr-01`:**

| Comprobación | Resultado |
|---|---|
| `ros2 doctor` | **All 5 checks passed** |
| Paquetes `ros-jazzy` configurados | **201**, y 0 a medio instalar |
| `ros2 topic echo --once` | `data: hola desde rvr-01` |
| `ros2 topic hz` | **9.997 Hz** · min 0.099 s · max 0.101 s · **σ 0.35 ms** |
| `ros2 topic info` | `std_msgs/msg/String`, 1 publicador |

**σ de 0.35 ms sobre un objetivo de 10 Hz**: DDS funciona con precisión en este Pi 4. Es un
dato útil de referencia — cuando la odometría real vaya a 16.5 Hz, ya sabemos que el jitter no
lo introduce el middleware.

> ℹ️ **`ros2 doctor` avisará de versiones más nuevas** (`local: 0.36.21 < latest: 0.36.22`).
> Es cosmético: el repositorio de ROS publica versiones continuamente y el índice local se
> queda atrás entre `apt update`s. No es un fallo.

> ⚠️ **Al matar procesos de ROS, usa el PID, nunca `pkill -f`.** El patrón coincide con la
> línea de comando del propio shell que lo ejecuta, y **mata tu terminal** — pasó dos veces con
> el driver de ROS 1. Y ojo con los falsos positivos: un `pgrep -f 'listener'` en este robot
> encuentra **`sshd`**, cuya línea de comando contiene literalmente `[listener]`.

---

## Capítulo 7 — URDF y árbol TF

> ✅ **VERIFICADO el 2026-07-30 sobre el robot real.** `tf2_echo odom laser`
> resuelve la cadena completa, que antes respondía «Could not find a connection».
>
> Las **medidas del chasis** vienen de la especificación del RVR y **no se han
> medido** en esta unidad; lo que sí está medido está marcado ✅.

### 7.1 El problema: el árbol TF estaba partido en dos

Antes de la Fase 3 **no existía ningún `.urdf` ni `.xacro`** en el proyecto. Los transforms se
publicaban a mano, y no encajaban:

```
   odom ──────────► rvr_base_link          ← lo publicaba el driver
   base_link ─────► laser                  ← un static_transform_publisher del launch
```

**Dos árboles inconexos.** Nada unía `rvr_base_link` con `base_link`, así que no había forma de
saber dónde está el LIDAR respecto a la odometría. Y sin eso, SLAM y Nav2 son **imposibles**:
el plan lo llama «el bloqueante raíz».

Lo peor es cómo falla: `ros2 run tf2_ros tf2_echo odom laser` dice *«Could not find a
connection»* y nada más. Ningún nodo se cae, ningún topic deja de publicar. **Silencioso.**

### 7.2 La cadena canónica

Según REP-105, y es lo que esperan `slam_toolbox` y Nav2 sin configuración extra:

```
   map ──► odom ──► base_footprint ──► base_link ──► laser
                                                └──► imu_link
                                                └──► wheel_left / wheel_right
```

**Quién publica qué, y esto es lo que más se confunde:**

| Transform | Lo publica | Por qué |
|---|---|---|
| `map → odom` | `slam_toolbox` (Fase 4) | Es la corrección del mapa. Todavía no existe |
| **`odom → base_link`** | **el driver** (`atriz_rvr_driver`) | Es el único que sabe dónde está el robot |
| `base_footprint → base_link` | `robot_state_publisher` | Geometría fija, sale del URDF |
| `base_link → laser`, `imu_link`, ruedas | `robot_state_publisher` | Idem |

El driver publica `odom → base_link` con su parámetro `base_frame`, cuyo valor por defecto es
`base_link`. **Si lo cambias, cambia también el URDF**, o el árbol se vuelve a partir.

### 7.3 Las medidas, y cuáles son de fiar

Todo lo geométrico está en propiedades `xacro` al principio del fichero, para cambiarlo en un
solo sitio:

| Propiedad | Valor | Procedencia |
|---|---|---|
| `laser_x`, `laser_y` | `0.0`, `0.0` | ✅ **medido**: el X2 está centrado (2026-07-30) |
| `laser_gap` | `0.040` | ✅ **medido**: hueco entre la tapa del RVR y la base del LIDAR |
| `base_length/width/height` | `0.218` / `0.185` / `0.114` | 📝 ficha del RVR, **sin medir en esta unidad** |
| `x2_height` | `0.041` | 📝 ficha del YDLIDAR X2 |
| `wheel_radius/width/separation` | `0.032` / `0.025` / `0.150` | 📝 **sin medir**. Solo geométricos |

**La altura del plano de barrido se DERIVA:**

```
    base_height    0.114     alto del RVR        (ficha, sin medir)
  + laser_gap      0.040     hueco               ✅ medido
  + x2_height/2    0.0205    al centro del disco (ficha)
  ─────────────────────────
    laser_z        0.1745    = 17.45 cm sobre el suelo
```

🔴 **El valor que arrastraba el proyecto era `0.10`, y se queda 7.4 cm corto.** Venía del
`static_transform_publisher` de `lidar_only.launch`, y la propia `GUIA_COMPLETA_LIDAR.md` del
repositorio lo admitía: «se **asume** que el LIDAR está en el centro del RVR y 0,1 m por
encima. Ajusta estos valores a tu montaje real». Nadie lo ajustó.

**Por qué 7 cm no es un detalle.** Un error en `laser_z` inclina el mapa entero; un error en
`laser_x` desplaza cada barrido respecto a la odometría, y SLAM lo interpreta como movimiento
que no ocurrió. El mapa sale torcido **sin un solo mensaje de error**.

👤 **Si el mapa sale mal, el primer sospechoso es `base_height`**, que es el único término de la
suma que no está medido. Mide con una regla, con el robot en el suelo, del **suelo al centro del
disco giratorio**, y pon ese número directo en `laser_z` ignorando la suma.

### 7.4 Las ruedas son `fixed`, y es deliberado

Un joint `continuous` obligaría a publicar `/joint_states` con el ángulo de cada rueda. **El RVR
no expone la posición angular de las ruedas** — solo conteos de encoder acumulados. Declararlas
móviles dejaría a `robot_state_publisher` esperando datos que nunca llegan, y el árbol se
rompería con un aviso poco claro.

Como el RVR entrega la odometría ya integrada por su locator interno, las ruedas son
**decorativas**. `fixed` es lo honesto, y por eso este paquete **no arranca
`joint_state_publisher`**.

### 7.5 Ejecutar

```bash
# xacro NO viene en ros-base. Comprobado el 2026-07-30.
sudo apt install -y ros-jazzy-xacro

cd ~/atriz_ws && colcon build --packages-select atriz_rvr_description
source install/setup.bash

# En una terminal, el driver (publica odom -> base_link):
ros2 run atriz_rvr_driver rvr_driver_node
# En otra, la descripción (publica el resto):
ros2 launch atriz_rvr_description description.launch.py
```

`robot_state_publisher` y `tf2_tools` **sí** vienen en `ros-base`; `xacro` no.

### 7.6 Verificación — que el árbol esté ENTERO

Es la única prueba que importa, y la que fallaba antes:

```bash
# La cadena completa debe resolver. Si dice «Could not find a connection»,
# el árbol sigue roto.
ros2 run tf2_ros tf2_echo odom laser

# El árbol en PDF, para verlo de un vistazo
ros2 run tf2_tools view_frames

# Y que no haya dos publicadores del mismo transform, que produce saltos
ros2 topic echo /tf_static --once
```

**Resultado real (2026-07-30):**

```
$ ros2 run tf2_ros tf2_echo odom laser
- Translation: [-0.018, -0.002, 0.141]
- Rotation: in RPY (degree) [1.603, -7.013, -5.000]

$ ros2 run tf2_tools view_frames
base_link   parent: odom        rate 16.699 Hz     <- el driver
laser       parent: base_link   rate 10000 Hz     <- robot_state_publisher
imu_link    parent: base_link   rate 10000 Hz
wheel_*     parent: base_link   rate 10000 Hz
```

Tres señales de que es correcto y no casualidad: la **z = 0.141** coincide con los 0.1425 del
URDF (la diferencia es la inclinación del robot), los transforms fijos van a **10000 Hz** —
la marca de `/tf_static`, que no se republica sino que se retiene—, y `base_link` va a
**16.699 Hz**, el ritmo de la telemetría del driver.

> El `Invalid frame ID "odom"` de la primera línea es normal: `tf2_echo` arranca antes de que
> llegue el primer transform. Un segundo después resuelve.

> 📝 **Dato colateral sin medir:** el RPY sale **[1.6°, −7.0°, −5.0°]**. Un pitch de −7° significa
> que el chasis está inclinado o el suelo tiene pendiente. **El LIDAR lo está viendo**, así que
> conviene tenerlo presente cuando salga el primer mapa. No se ha determinado si es del suelo o
> del montaje.

> 🐛 **El launch falló la primera vez**, y con un error de los útiles:
> ```
> Unable to parse the value of parameter robot_description as yaml. If the parameter
> is meant to be a string, try wrapping it in ParameterValue(value, value_type=str)
> ```
> El fichero **ya llevaba un comentario explicando justamente eso** — se documentó la solución
> y no se implementó. `robot_description` es XML, y `launch` intenta interpretarlo como YAML si
> no se le dice el tipo.

---

## Capítulo 8bis — LEDs y sensores del RVR

> ✅ **Verificado el 2026-07-30.** Los 11 grupos de LED confirmados **a la vista**, y 10 de los
> 11 sensores por streaming más los 7 puntuales verificados con datos reales.
> Herramienta: `00_auditoria/evidencia/mediciones_banco/verificar_leds_sensores.py`

### 8bis.1 Los 11 grupos de LED

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/verificar_leds_sensores.py --solo-leds
```

Enciende cada grupo en azul, uno a uno, con 1.2 s de pausa para mirarlo:

| Grupo | Dónde está |
|---|---|
| `status_indication_left` / `_right` | indicadores |
| `headlight_left` / `_right` | faros delanteros |
| `battery_door_front` / `_rear` | puerta de la batería |
| `power_button_front` / `_rear` | botón de encendido |
| `brakelight_left` / `_right` | luces de freno |
| `undercarriage_white` | bajos — **blanco de un solo canal, no acepta RGB** |

Y los cinco métodos de conjunto: `set_all_leds_rgb`, `set_all_leds_color`,
`set_multiple_leds_with_rgb`, `set_multiple_leds_with_enums`, `turn_leds_off`.

> ⚠️ **Los LEDs no se pueden verificar por software.** El SDK no ofrece forma de leer el estado
> de un LED, así que un script solo puede comprobar que el comando **se acepta**. Que se
> enciendan **lo tiene que ver una persona**. Si uno no se enciende, el script dirá ✓ y será un
> fallo real.

### 8bis.2 🔴 El LED del sensor de color no se apaga con `turn_leds_off()`

**No es un grupo de `RvrLedGroups`.** Se controla con `enable_color_detection()`, y si no se
desactiva **se queda encendido indefinidamente**, gastando batería después de que el programa
termine.

```python
await rvr.enable_color_detection(is_enabled=True)    # necesario para leer color
...
await rvr.enable_color_detection(is_enabled=False)   # ← IMPRESCINDIBLE al terminar
```

Lo detectó el usuario **mirando el robot**, no el script. Cada `(True)` necesita su `(False)`,
también en el camino de error.

> Y al revés: **el sensor de color no transmite sin su LED.** Sin
> `enable_color_detection(True)` devuelve ceros y *parece* roto.

### 8bis.3 Los sensores, con datos reales

4 s a `interval=60 ms`, robot quieto:

| Stream | Muestras | Dato |
|---|---|---|
| `color_detection` | 52 | `R=193 G=167 B=149` |
| `ambient_light` | 52 | `Light=12.487` |
| `quaternion` | 65 | `W=0.998 X=0.007 Y=-0.062` |
| `imu` | 65 | `Pitch=1.089 Roll=-7.040 Yaw=-3.051` |
| `accelerometer` | 65 | `X=-0.123 Y=-0.016 Z=0.959` |
| `gyroscope` | 65 | `X=0.057 Y=-0.263 Z=0.000` |
| `locator` · `velocity` · `speed` | 65 | ceros, robot quieto |
| `encoders` | 65 | `LeftTicks=15359 RightTicks=17258` |
| `core_time` | **0** | 🔴 **no lo transmite el firmware** |

**Dos señales de que los datos son buenos y no ruido:** el acelerómetro marca **Z = 0.959 g**
—la gravedad, con el robot horizontal— y el **`Roll = −7.040°` coincide con el pitch de −7°**
medido de forma independiente en el árbol TF (cap. 7.6). **Dos sensores distintos dicen lo
mismo: el robot está inclinado unos 7°.** Sin determinar si es del suelo o del montaje.

**Puntuales, los siete funcionan:** batería (100 %), estado de tensión, RGBC
(`red=271 green=488 blue=193 clear=857`), luz ambiente (9.99), encoders, y las dos versiones de
firmware.

### 8bis.4 🔴 `core_time` no existe en el firmware 9.1.462

Está declarado en el enum del SDK y **el RVR no lo entrega**. Verificado aislándolo: **0
muestras solo y 0 acompañado**, mientras `quaternion` daba 30 en la misma configuración — así
que **no es un conflicto de slots**, es el firmware.

No lo usa nada del driver, así que no bloquea. Se documenta para que nadie pierda tiempo.

### 8bis.5 ⚠️ `get_main_application_version()` exige `target`

El RVR tiene **dos procesadores**, y hay que decir cuál:

```bash
target=1  Nordic  ->  9.1.462
target=2  ST      ->  9.2.482
```

Sin el argumento: `TypeError`. De aquí sale la versión del **ST (9.2.482)**, que el proyecto no
tenía documentada — solo conocía la Nordic.

### 8bis.6 Qué de esto expone el driver de ROS 2

**Solo `/color`.** Los 16 servicios que faltan por portar (LEDs, IR, encoders, system info,
motores crudos…) tienen **el hardware detrás ya verificado**, así que portarlos es trabajo de
`rclpy`, no de averiguar si el sensor funciona. Están listados al final de
`rvr_driver_node.py`.

---

## Capítulo 9 — SLAM con slam_toolbox (Fase 4)

✅ **CERRADA** el 2026-07-31. `slam_toolbox` arranca, se activa, completa el árbol TF,
publica `/map` **y el mapa crece al moverse**: de 657 a **3110 celdas** (1.64 → 7.78 m²)
recorriendo 2.6 m. Ver 9.11.

⚠️ Con una reserva medida: **la localización deriva más de lo aceptable para Nav2** (87.8 cm
tras 2.6 m). El mapa sirve; la pose todavía no. Ver 9.12.

Para cerrarla hubo que arreglar **tres cosas** y corregir **dos herramientas propias**.
Ninguna de las cinco daba un error: **todas fallaban en silencio.** Están en 9.11.

### 9.1 Qué añade SLAM, y qué tenía que estar ya en su sitio

```
map ──(slam_toolbox)──► odom ──(driver)──► base_footprint ──► base_link ──► laser
└── ESTO es lo nuevo                       └───────── ya lo daba la Fase 3 (cap. 7)
```

`slam_toolbox` no publica el robot: publica **una sola cosa**, la corrección
`map → odom`. Todo lo demás lo tiene que encontrar ya hecho. Si falta un eslabón, no da
un error claro: se queda repitiendo un aviso y produciendo un mapa vacío.

```bash
# terminal 1 — el robot (cap. 7 y 8.5)
ros2 launch atriz_rvr_bringup robot.launch.py
# terminal 2 — SLAM
ros2 launch atriz_rvr_bringup slam.launch.py
```

### 9.2 🔴 `slam_toolbox` es un nodo de CICLO DE VIDA en Jazzy

En Jazzy `slam_toolbox` arranca en estado `unconfigured`. Eso significa: **el proceso
vive, `ros2 node list` lo muestra, y no hace absolutamente nada.** No se suscribe a
`/scan`, no publica `/map`, y su log se queda en `Node using stack size` sin un solo
error ni aviso.

Así se veía el fallo:

```
$ ros2 topic info /scan --verbose
Subscription count: 0          # <- slam_toolbox no está escuchando
$ ros2 lifecycle get /slam_toolbox
unconfigured [1]
```

El arreglo **no** es `Node` con más parámetros: es `LifecycleNode` más los dos eventos de
transición `configure` → `activate`. `launch/slam.launch.py` lo hace siguiendo el patrón
del `online_async_launch.py` oficial de slam_toolbox, con un argumento `autostart`
(por defecto `true`).

Encadenar las transiciones con un `sleep` **no** vale: se hace con
`OnStateTransition`, esperando a que `configuring` termine en `inactive`, o el arranque
falla una vez de cada diez.

Verificación (2026-07-30):

```
$ ros2 lifecycle get /slam_toolbox
active [3]
```

### 9.3 ✅ El QoS de `/scan` empareja — riesgo cerrado

El capítulo 8.5 dejó abierto un riesgo real: el driver del LIDAR publica `/scan` como
**BEST_EFFORT**, y si `slam_toolbox` pidiera RELIABLE, **DDS no los emparejaría y no
recibiría ni un barrido, sin dar ningún error**.

Comprobado con el nodo ya en `active`:

```
$ ros2 topic info /scan --verbose
Subscription count: 1
  Node name: slam_toolbox
  Reliability: BEST_EFFORT          # <- empareja
```

**El riesgo era infundado.** Queda documentado porque comprobarlo cuesta un comando y
perseguir un mapa vacío cuesta una tarde.

### 9.4 🔴 El fallo de diseño que costó la Fase 4: `base_link` con DOS padres

Con todo arrancado, `slam_toolbox` repetía:

```
[WARN] [slam_toolbox]: Failed to compute odom pose
```

La causa era **un error de diseño propio**, no de slam_toolbox:

```
/tf         frame_id: odom            child_frame_id: base_link       <- el driver
/tf_static  frame_id: base_footprint  child_frame_id: base_link       <- el URDF
```

**En TF un frame solo puede tener UN padre.** Con dos, el árbol no se une, se parte en
dos, y `tf2_echo` lo dice con claridad:

```
Could not find a connection between 'odom' and 'base_footprint' …
Tf has two or more unconnected trees.
```

**Arreglo:** el driver publica `odom → base_footprint`, no `odom → base_link`. Es además
lo correcto por REP-105 (el frame proyectado al suelo es el que se localiza) y lo que
`slam_toolbox` pide en su `base_frame`.

- `rvr_driver_node.py`: parámetro `base_frame` con valor por defecto `base_footprint`.
- `robot.launch.py`: `'base_frame': 'base_footprint'`.
- La IMU pasa a tener su propio `imu_frame` (`imu_link`): sus datos **no** están en
  `base_frame`, y decir lo contrario era otra imprecisión.

#### ⚠️ Por qué la verificación de la Fase 3 no lo detectó — lección de método

El capítulo 7 dio la Fase 3 por buena con esto:

```bash
ros2 run tf2_ros tf2_echo odom laser     # ✅ resolvía
```

**Y resolvía de verdad**, por el camino equivocado: `odom → base_link → laser`. El
transform existía, así que la comprobación pasaba, mientras `base_footprint` quedaba
colgando en un árbol aparte que nadie miraba.

> **Comprueba el transform QUE PIDE EL CONSUMIDOR, no uno que se le parezca.** Un
> `tf2_echo` que resuelve prueba que hay *un* camino, no que el árbol esté bien. La
> prueba correcta es la que usa los frames exactos que aparecen en el YAML de
> `slam_toolbox`:
>
> ```bash
> ros2 run tf2_ros tf2_echo odom base_footprint    # ← ESTA
> ```

Tras el arreglo (2026-07-30), un solo árbol:

```
/tf         odom            -> base_footprint         (driver, 16.7 Hz)
/tf_static  base_footprint  -> base_link
            base_link       -> imu_link, laser, wheel_left, wheel_right
```

y `Failed to compute odom pose`: **0 apariciones**.

### 9.5 Guardar el mapa: `save_map` NO funciona, `serialize_map` SÍ

```
$ ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: mapa}}"
response: SaveMap_Response(result=255)
```

`255` es «fallo indefinido». La causa está en el log de `slam_toolbox`, no en la
respuesta del servicio:

```
Package 'nav2_map_server' not found
```

`save_map` de slam_toolbox **delega en el map_saver de Nav2**, y este sistema tiene
`ros-jazzy-ros-base` sin Nav2 (decisión del proyecto: Nav2 llega en la Fase 5).

Hay dos salidas, y para la Fase 4 sirve la segunda:

| Servicio | Formato | Necesita Nav2 | Sirve para |
|---|---|---|---|
| `save_map` | `.pgm` + `.yaml` | **sí** | dárselo a Nav2 / verlo como imagen |
| `serialize_map` | `.posegraph` + `.data` | **no** | que slam_toolbox lo recargue en modo `localization` |

```bash
ros2 service call /slam_toolbox/serialize_map \
  slam_toolbox/srv/SerializePoseGraph "{filename: /ruta/sin/extension}"
# response: SerializePoseGraph_Response(result=0)   <- 0 = OK
```

Verificado el 2026-07-30 (`00_auditoria/evidencia_24_04/mapas/`):

```
mapa_fase4_banco.data          11 KB
mapa_fase4_banco.posegraph    3.4 MB
```

⚠️ El `.posegraph` es el grafo completo, y **3.4 MB con el robot casi quieto**. Crecerá
con el recorrido: hay que vigilarlo antes de guardar mapas en los 16 robots.

### 9.6 🔴 Un robot QUIETO produce un mapa casi vacío — y no es un fallo

Con todo funcionando y el robot parado:

```
rejilla      83 x 87 celdas a 5 cm  = 4.15 x 4.35 m
libre           458 (  6.3 %)
ocupado          57 (  0.8 %)
desconocido    6706 ( 92.9 %)
```

Con el LIDAR girando a 10 Hz y viendo paredes a 2 m, un 92.9 % desconocido parece un
fallo grave. **No lo es**, y son dos parámetros del propio YAML de Atriz los que lo
explican:

- **`min_pass_through: 2`** — una celda necesita **dos rayos** que la atraviesen para
  marcarse. Un robot quieto barre siempre desde el mismo punto y los rayos divergen: solo
  las celdas **cerca** del robot reciben dos o más. Las lejanas reciben uno y se quedan
  en «desconocido» para siempre. De ahí que el área libre (1.29 m²) sea un disco pequeño
  alrededor del robot.
- **`minimum_travel_distance: 0.3` / `minimum_travel_heading: 0.5`** — slam_toolbox no
  añade un barrido nuevo al grafo hasta que el robot se ha movido 30 cm o girado 28.6°.
  Quieto, el grafo tiene **un solo nodo**.

> Sin saber esto se pierde una tarde ajustando el solver, que está bien. La herramienta
> `00_auditoria/evidencia/mediciones_banco/medir_slam_ros2.py` existe para no repetirlo:
> mueve el robot y mide **cuántas celdas conocidas gana el mapa**, distinguiendo
> «el robot no se movió» de «SLAM no procesó».

### 9.7 El intento fallido del 2026-07-30 — por qué no valía

✅ **Ya resuelto**: el mapa crece, verificado el 2026-07-31 (9.11). Se conserva este
apartado porque la regla que dejó sigue valiendo.

El intento del 2026-07-30 no era válido, y la razón importa:

1. El driver murió a mitad de sesión (ver 9.8) y hubo que reiniciarlo.
2. Se reinició **solo el driver**, dejando el `slam_toolbox` viejo en marcha.
3. Ese `slam_toolbox` dejó de procesar: el mapa salió **idéntico celda a celda** (515
   conocidas antes y después) tras un giro de 360° y 80 cm de recorrido.

> **Reiniciar el driver por debajo de un `slam_toolbox` ya arrancado invalida la prueba.**
> Se queda con un hueco en su buffer TF y con el `odom` anterior. Arranca los dos juntos
> y en ese orden, siempre.

La secuencia correcta, que es la que cerró la fase:

```bash
# 1. los dos, desde cero, en este orden
ros2 launch atriz_rvr_bringup robot.launch.py
ros2 launch atriz_rvr_bringup slam.launch.py
# 2. la prueba
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_slam_ros2.py
```

Del capítulo 8.5 quedaba abierto lo que puede arruinar un mapa **sin dar ningún error**:

- ✅ **`inverted` del LIDAR: VERIFICADO el 2026-07-31, y era correcto** (`true`). No hizo
  falta colocar ningún objeto: se comprueba por software girando el robot y correlacionando
  el barrido de antes con el de después (`verificar_inverted_lidar.py`). Detalle en 9.11.
- 🔴 **El robot está inclinado ~7°**, medido por dos vías independientes (el árbol TF y
  el `Roll` de la IMU). El LIDAR barre un plano inclinado. Causa sin determinar.
  Consecuencia observada: `slam_toolbox` absorbe esa inclinación dentro de `map → odom`,
  que deja de ser una corrección plana. Para mapear en 2D funciona; **para Nav2 hay que
  resolverlo**, porque la odometría del driver mete roll y pitch en
  `odom → base_footprint` cuando por REP-105 debería ser plana (x, y, yaw).

### 9.8 EL RVR SE DUERME A LOS 5 MIN — ✅ medido y arreglado

El hallazgo más importante de la Fase 4, y no es de SLAM. Encontrado el 2026-07-30,
**medido y corregido el 2026-07-31** (9.8a–9.8c). Se cuenta entero, incluido el síntoma,
porque es el patrón de fallo que este proyecto persigue en todas partes.

A mitad de sesión, con todo arrancado y sin tocar nada:

```
$ ros2 topic hz /tf
average rate: 50.193              # <- 50 Hz = SOLO slam_toolbox (transform_publish_period 0.02)
$ ros2 topic hz /odom
(nada)
$ ros2 topic hz /imu
(nada)
$ ros2 topic hz /color
(nada)
$ ps -p 56100 -o stat=,%cpu=
Sl  12.3                          # <- el proceso VIVE, 17 hilos, 86 MB
$ ros2 topic info /odom --verbose
Publisher count: 1
  Node name: rvr_driver           # <- registrado, publicando cero
```

Los tres streams del RVR muertos, el nodo vivo al 12.3 % de CPU con todos sus topics
registrados, y **ni un mensaje de error en el log**. Es el patrón de fallo silencioso
contra el que avisa `CLAUDE.md`, esta vez en su forma más difícil de ver: `/tf` seguía a
50 Hz, así que un vistazo rápido decía «TF va bien».

**Causa:** `rvr_driver_node.py` llama a `wake()` **una sola vez, al arrancar** (línea
367), y no vuelve a hablar con el RVR salvo cuando llega un `cmd_vel`. El RVR se duerme
por inactividad y deja de transmitir. Reiniciar el driver lo revive:

```
$ ros2 topic hz /odom
average rate: 16.669              # <- vuelve exactamente al ritmo esperado
```

**Consecuencias para el laboratorio, que son serias:**

- Un robot que espere 5 minutos a que un estudiante empiece su práctica **estará mudo
  cuando empiece**, y la web no verá ningún error: el nodo está vivo y los topics
  existen.
- Cualquier medición larga (estabilidad, mapeo, docencia) se corta sin avisar.
- Un `systemd` con `Restart=always` **no** lo arregla: el proceso no muere.

### 9.8a ✅ El timeout medido: 300.6 s = 5.01 min

Medido el **2026-07-31** arrancando el driver con el keepalive desactivado a propósito y
vigilando el **ritmo** de `/odom` durante 12 minutos:

```bash
ros2 launch atriz_rvr_bringup robot.launch.py lidar:=false keepalive_period:=0.0
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_keepalive_ros2.py --minutos 12
```

El robot se durmió **dos veces**, y las dos aguantó **exactamente lo mismo**:

| | Aguantó | Detectado tras | Reanudado en |
|---|---|---|---|
| Sueño 1 (a los 3.9 min) | **300.6 s** | 3.4 s | 0.004 s |
| Sueño 2 (a los 9.0 min) | **300.6 s** | 3.4 s | 0.004 s |

**300.6 s idénticos a la décima de segundo no es una heurística difusa: es un
temporizador del firmware.** Coincide con los 5 min documentados del RVR, y cae dentro
del intervalo 2–7.5 min que los timestamps del fallo original solo permitían acotar.

📝 El SDK vendorizado **no tiene** `set_inactivity_timeout` para cambiarlo: solo `wake()`,
`sleep()` y las de batería. Hay que hablarle, no configurarlo.

### 9.8b ✅ El arreglo: keepalive + detector de silencio

Están en `rvr_driver_node.py`, bloque «SALUD DEL ENLACE». **Hacen falta los dos**, y
cubren cosas distintas:

| | Qué hace | Cubre |
|---|---|---|
| **`_keepalive`** | cada **30 s** llama a `get_battery_percentage()` | la causa conocida: que se duerma |
| **`_vigilar_silencio`** | a 1 Hz mira cuánto hace que llegó la última muestra; a los 3 s avisa y reanuda | **todo lo demás**: cable flojo, `sensor_control` caído, firmware atascado |

Tres decisiones de diseño que conviene no deshacer:

- **Se usa una LECTURA (`get_battery_percentage`), no `wake()` a secas.** Una lectura no
  cambia ningún estado del robot, así que no puede interferir con una maniobra en curso ni
  con la parada de emergencia. Y devuelve un dato que hacía falta: **`/battery_state`**,
  que no se publicaba ni en el driver de ROS 1.
- **El vigilante mide el SILENCIO, no el estado del proceso ni la existencia del topic.**
  Es toda la diferencia: durante el fallo el proceso estaba vivo y el topic registrado.
- **30 s con un timeout de 300 s son 10× de margen.** Se podría subir a 120 s sin riesgo,
  pero no hay motivo: un comando cada 30 s son ~2 bytes/s sobre un enlace de 115200
  baudios que ya lleva 16.7 Hz de telemetría.

Los dos se desactivan con `keepalive_period:=0.0` y `silence_timeout:=0.0`, que es como se
reproduce el fallo a propósito para medirlo.

### 9.8c ✅ Verificado: las dos pruebas, una al lado de la otra

Mismo robot, misma duración, mismo binario. Lo único que cambia es `keepalive_period`:

| | A (`keepalive=0`) | B (`keepalive=30 s`) |
|---|---|---|
| duración | 12.0 min | 12.0 min |
| muestras de `/odom` | 11795 | 11909 |
| ritmo medio | 16.38 Hz | **16.54 Hz** |
| **huecos en `/odom`** | **2** (a los 3.9 y 9.0 min) | **0** |
| duración de los huecos | 3.5 s y 3.7 s | — |
| avisos de silencio | 2 | 0 |
| reanudaciones | 2, **0 fallos** | 0 |
| lecturas de batería | 0 | **24**, cada 30.0 s exactos |

**Se durmió dos veces sin keepalive y ninguna con él.** En la prueba B el detector no tuvo
nada que detectar, que es justo el objetivo: el keepalive impidió que llegara a haber un
problema. Y el ritmo medio sube de 16.38 a 16.54 Hz — la diferencia es exactamente el
tiempo que estuvo mudo en la prueba A.

Lo que el driver dice cuando el detector sí actúa (prueba A):

```
[WARN] el RVR lleva 3.4 s sin enviar telemetría (se esperan ~16.7 muestras/s).
       Lo más probable es que se haya dormido. Intentando reanudar (intento nº 1)…
[INFO] streaming reanudado. Si esto se repite cada pocos minutos, el keepalive
       no está llegando: revisa keepalive_period y el enlace.
```

Antes de esto, el mismo suceso dejaba el robot mudo **indefinidamente y sin una línea en
el log**.

### 9.8d La regla de diagnóstico, que sigue valiendo

**Si un robot no publica `/odom`, mira el RITMO, no si el nodo o el topic existen** — las
dos cosas eran ciertas mientras estaba mudo. `verificar_robot.sh --hardware` comprueba el
ritmo desde el 2026-07-30, precisamente por esto.

Evidencia cruda: `00_auditoria/evidencia_24_04/12_keepalive_rvr.txt`.

### 9.9 Coste en el Pi 4 con todo a la vez

Medido el 2026-07-30 con driver + LIDAR + `robot_state_publisher` + SLAM activos:

| Proceso | CPU | RSS |
|---|---|---|
| `rvr_driver_node` | 15.9 % | 86.3 MB |
| `async_slam_toolbox_node` | **4.5 %** | 49.3 MB |
| `ydlidar_ros2_driver_node` | 2.6 % | 31.3 MB |
| `robot_state_publisher` | 0.5 % | 32.6 MB |
| **total** | **~24 %** de un núcleo | ~200 MB |

`loadavg` 0.62 sobre 4 núcleos · 62.3 °C · `throttled=0x0`.

**SLAM sale barato: 4.5 %.** El presupuesto de CPU de este robot lo consume el driver del
RVR, no slam_toolbox, así que subir `throttle_scans` o `minimum_travel_distance` para
«aliviar el Pi» sería optimizar lo que no cuesta.

Un aviso benigno que aparece de vez en cuando y **no** hay que perseguir:

```
Message Filter dropping message: frame 'laser' … 'discarding message because the queue is full'
```

Es el filtro de mensajes de TF descartando un barrido mientras espera su transform. Cuatro
veces en ~20 min de sesión.

### 9.11 ✅ Cómo se cerró la fase: tres arreglos y dos herramientas corregidas

Con todo lo anterior en su sitio, el mapa **seguía sin crecer**. Estas cinco causas se
fueron encontrando en cadena, y ninguna daba un error.

#### 1. 🔴 `/scan` y `/odom` se contradecían en el sentido de giro

Girando el robot y correlacionando el barrido de antes con el de después
(`verificar_inverted_lidar.py`): la física exige que el patrón se desplace **al revés** que
el robot, y salían **el mismo signo**.

```
giro real (odom):          -47.0°
desplazamiento del scan:   -47.0°     <- deberían tener signos opuestos
```

⚠️ **Eso solo no dice cuál de los dos está mal**, y mi herramienta concluyó de más diciendo
«`/scan` está espejado». Los datos encajaban igual con «el yaw de `/odom` está invertido».

**Lo desempató una observación física**, y este es el punto del capítulo que más vale la
pena recordar: se mandó un giro positivo y **se miró el robot**. Giró a la izquierda. Como
el SDK documenta `yaw_angular_velocity` con la regla de la mano derecha y el driver pasa
`angular.z` sin tocarlo, el giro real fue +47°, el barrido (−47°) era el correcto, y **el
equivocado era el yaw de `/odom`**.

> Cuando dos sensores se contradicen, el software puede decirte **que** se contradicen,
> pero no **cuál miente**. Para eso hay que mirar el robot.

✅ **`inverted: true` del YDLIDAR era correcto.** El LIDAR nunca fue el problema.

#### 2. 🔴 El RVR no usa una sola convención de ejes

Apliqué la conversión FRD→FLU a los cuatro sensores **por analogía** y rompí dos. Medidos
uno a uno:

| Sensor | Estaba | Qué necesita |
|---|---|---|
| cuaternión | yaw invertido | `(x, -y, -z, w)` |
| locator | `y` invertida | `-y` |
| giroscopio | **ya en FLU** | solo deg/s → rad/s |
| acelerómetro | **ya en FLU**, y en **g** | solo **g → m/s²** |

En reposo el acelerómetro daba módulo **0.973**: el RVR reporta en **g**, y el driver de
ROS 1 tampoco lo convertía — `/imu` llevaba desde siempre valores 9.8 veces pequeños. Ahora
`(-1.314, -0.004, +9.281)`, módulo 9.374 m/s².

📝 De propina, el acelerómetro mide la inclinación del robot por una **tercera vía
independiente**: `asin(1.314/9.374) = 8.1°`.

El efecto sobre SLAM, misma prueba antes y después:

| | Deriva tras girar 360° y volver |
|---|---|
| antes | 6.6 cm y **30.0°** |
| después | 0.2 cm y **1.8°** |

#### 3. 🔴 `fixed_resolution: false` hacía que se descartaran los barridos

El X2 entrega barridos de longitud **variable** (254 unas veces, 255 otras). `slam_toolbox`
registra el sensor con el tamaño del **primero** y **descarta todos los demás**, con una
sola línea en su log y ningún error:

```
LaserRangeScan contains 254 range readings, expected 255
```

Ese parámetro se había puesto a `false` en la Fase 3.2 **para callar un aviso cosmético**
del driver. **Cambiar un parámetro para silenciar un aviso cambió un síntoma visible por
uno invisible.** Con `true`: 142 barridos, **todos de 260 puntos**.

📝 El mismo problema reventaba `verificar_inverted_lidar.py` con `IndexError`: asumía
barridos del mismo tamaño. Corregido remuestreando a una rejilla angular fija de 360
celdas. **Mismo origen, dos víctimas.**

#### 4. 🔴 Y aun así el mapa no crecía: la herramienta daba un falso negativo

`medir_slam_ros2.py` avanzaba 40 cm, retrocedía otros 40, y **solo miraba el mapa al
final** — con el robot otra vez donde empezó, el momento en que menos ha cambiado nada.

`slam_toolbox` cuenta la distancia **desde el último nodo del grafo**, no desde donde
empezó la prueba. Con `minimum_travel_distance: 0.3` hicieron falta **~0.85 m**. Y girar en
el sitio no basta: **cuatro vueltas y media seguidas no cambiaron ni una celda.**

Lo que lo demostró fue mirar el **grafo**, no el mapa:

```
(mi config, minimum_travel_distance 0.3)
inicio                 grafo=4  mapa= 708 celdas
tras paso 1 (+0.45 m)  grafo=4  mapa= 708
tras paso 2 (+0.45 m)  grafo=5  mapa=1542   <- CRECE
tras paso 3 (-0.45 m)  grafo=5  mapa=1542
tras paso 4 (-0.45 m)  grafo=6  mapa=2279   <- CRECE
```

> **El truco de diagnóstico:** `ros2 topic echo /slam_toolbox/graph_visualization` — si el
> número de marcadores no sube, `slam_toolbox` no está añadiendo nodos, y entonces el mapa
> no puede crecer por mucho que el robot se mueva. Es más directo que mirar el mapa.

Y antes de eso, **comparar contra la configuración de fábrica** descartó de un golpe que
fueran mis parámetros: se comportó exactamente igual.

#### El resultado

```
── árbol TF ──   ✅ odom → base_footprint   ✅ map → base_footprint   ✅ base_link → laser

ANTES de mover      79 x 89 celdas     657 conocidas ( 9.3 %)  1.64 m²
tras el giro 360°   79 x 89            657            ( 9.3 %)  1.64 m²
tras avance 1/3     79 x 89            657            ( 9.3 %)  1.64 m²
tras avance 2/3     84 x 95           1669            (20.9 %)  4.17 m²
tras avance 3/3     86 x 95           2023            (24.8 %)  5.06 m²
al volver          121 x 98           3110            (26.2 %)  7.78 m²

recorrido real: 262.5 cm · nodos del grafo: 4 → 8
✅ EL MAPA CRECE AL MOVERSE
```

Coste con todo en marcha: driver 33.6 %, SLAM 5.0 %, LIDAR 2.6 %, RSP 0.5 %; 64.2 °C.

### 9.12 ⚠️ Lo que queda abierto tras cerrar la fase

✅ **La deriva está CARACTERIZADA, y es pequeña** (2026-07-31, 6 corridas con las variables
controladas). Evidencia: `14_deriva_slam_caracterizada.txt`.

| Recorrido | n | Deriva mediana | Peor caso | σ |
|---|---|---|---|---|
| ~159 cm | 3 | **1.0 cm** y 1.3° | 2.7 cm | 1.0 cm |
| ~237 cm | 3 | **2.7 cm** y 2.3° | 3.2 cm | 0.6 cm |

**El error de posición cabe dentro de una celda del mapa** (5 cm) y es un orden de magnitud
menor que el radio del robot (~11 cm). Crece con la distancia de forma coherente —0.63 % del
recorrido en las cortas, 1.14 % en las largas—, que es el comportamiento normal de una
odometría corregida por emparejado de barridos, no el patrón de un fallo.

Y el mapa es **repetible**: las tres corridas largas dieron +2347, +2321 y +2334 celdas — un
rango de 26 celdas sobre 2334.

🔴 **Los 87.8 cm de la primera corrida de la Fase 4 fueron una anomalía.** La corrida larga de
aquí recorre 237 cm, comparable a los 262 cm de aquella, y sale **30 veces mejor**. La
diferencia conocida es que aquella se hizo en un hueco demasiado justo y el robot rozó
obstáculos.

⚠️ **No se reprodujo la anomalía a propósito**, así que «rozar obstáculos» sigue siendo la
explicación más probable, **no una causa demostrada**. Lo que sí queda demostrado es que no es
el comportamiento normal del sistema.

✅ **Consecuencia: la localización ya NO es un bloqueante para Nav2.** De los tres que había,
queda uno menos.

🔴 **La inclinación de ~8°**, confirmada por **tres vías independientes** (árbol TF, Roll de la
IMU y acelerómetro). Causa sin determinar.

📝 Los resultados de deriva **acotan su gravedad**: con la inclinación presente, la deriva es de
2.7 cm. Así que no está arruinando el emparejado. Sigue habiendo que resolverla para Nav2
—por REP-105 `odom → base_footprint` debería ser plana— pero **no es urgente**.

✅ **La velocidad de `/odom` está arreglada** (2026-07-31). El stream nunca fue el problema:
es exacto. Lo que fallaba era que el driver copiaba una velocidad del marco del **mundo** a un
campo que ROS define en el marco del **robot**. Ahora publica `(+0.101, +0.001)` con el robot
a 84° contra 0.099 m/s reales — 2 % de error. **Capítulo 10.**

### 9.13 Verificación del capítulo

```bash
ros2 lifecycle get /slam_toolbox                 # active [3]
ros2 run tf2_ros tf2_echo odom base_footprint    # ← LA prueba: es lo que pide SLAM
ros2 run tf2_ros tf2_echo map base_footprint     # lo que añade SLAM
ros2 topic hz /map                               # 0.200 Hz (map_update_interval 5 s)
ros2 topic hz /odom                              # 16.7 Hz  ← si es 0, ver 9.8
ros2 topic info /scan --verbose | grep -i reliab  # BEST_EFFORT en publicador y suscriptor
ros2 topic echo /battery_state --once            # llega cada 30 s: es el keepalive (9.8b)
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_slam_ros2.py
# 12 min sin tocar nada, para probar que el enlace aguanta:
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_keepalive_ros2.py
```

⚠️ **Y el espacio importa.** `medir_slam_ros2.py` necesita, con el robot en el centro:

```
              ↑ 1 m por delante (hacia donde mira)
      ┌───────────────────────┐
 40cm │      ┌─────┐          │ 40cm     el robot NO se desplaza
 ←────┤      │ RVR │ →        ├────→     lateralmente: a los lados
      │      └──┬──┘          │          solo hace falta el hueco
      └───────────────────────┘          del giro (radio 14 cm)
              ↓ 1 m por detrás
```

Nada a menos de 60 cm: **el robot no esquiva obstáculos**, solo tiene watchdog. Y el LIDAR
va a 17.5 cm de altura barriendo en horizontal, así que pasa por encima de zócalos y cajas
bajas — «parece despejado» a ras de suelo no basta.

Evidencia cruda: `00_auditoria/evidencia_24_04/11_slam_fase4.txt`,
`13_fase4_cerrada.txt` y `mapas/`.

---

## Capítulo 10 — Los marcos de referencia de `/odom`

✅ **Verificado el 2026-07-31.** Es el capítulo que más tiempo ahorra a quien toque la
odometría, porque **el RVR no usa una sola convención de ejes** y ninguno de sus desajustes
produce un error: todos fallan en silencio.

Evidencia cruda: `00_auditoria/evidencia_24_04/15_velocidad_odom.txt`.

### 10.1 El modelo, en una tabla

Cada fila se midió por separado. No deduzcas ninguna de otra: **este proyecto lo intentó tres
veces y se equivocó las tres**.

| Dato del RVR | Marco en que viene | Qué hay que hacerle |
|---|---|---|
| **Locator** (posición) | propio, **90° girado** respecto al «adelante», y se realinea en cada `reset_locator_x_and_y()` | rotar **−90°**: `(x,y) → (y,−x)` |
| **Velocity** | el mismo del locator (mundo) | la misma rotación, y **proyectar sobre el rumbo** |
| **Cuaternión** | FRD, con el yaw a cero **al ENCENDER el RVR** | `(x,−y,−z,w)` y **restar el yaw del arranque** |
| **Giroscopio** | ya FLU | solo deg/s → rad/s |
| **Acelerómetro** | ya FLU, y en **`g`** | solo × 9.80665 |

### 10.2 🔴 Las cuatro trampas, y por qué ninguna da error

**1. `reset_yaw()` no hace nada.** El driver lo llama al arrancar y el cuaternión sigue dando
lo que arrastraba. El yaw solo se pone a cero **al encender el RVR**. Cinco arranques dieron
cinco offsets distintos:

```
+51.1°   +52.7°   +56.5°   −74.6°   +64.9°
```

**No había constante posible.** El driver mide el offset en cada arranque y lo resta:

```
[INFO] origen del yaw fijado en +51.1° (reset_yaw() del RVR no lo pone a cero; se resta aquí)
```

**2. El eje X del locator está 90° girado** respecto al «adelante» del robot. Avanzar en línea
recta daba **siempre −90°**, con giros y apagados de por medio. Y el marco es **fijo** —no gira
con el robot— pero **se realinea en cada `reset_locator_x_and_y()`**, o sea al arrancar el
driver.

**3. `Velocity` viene en el marco del MUNDO, y es EXACTO.** Medido con el robot recto:

```
dirección del desplazamiento del locator:  +90.2°
dirección del vector Velocity:             +90.1°     ← 0.1° de diferencia
módulo real 0.199 m/s  ·  Velocity 0.200              ← 0 % de error
```

⚠️ Durante un día este proyecto lo dio por «basura» porque reportaba 0.001 m/s con el robot a
0.147 real. **La observación era cierta; la conclusión, falsa:** se leía solo la componente X
con el robot encarado a ~90° de ese eje, donde X vale ~0 aunque el robot cruce la habitación.
`odom.twist` va en el marco del **robot** (`child_frame_id`), así que hay que **proyectar sobre
el rumbo**, no copiar.

**4. La posición y la orientación pueden tener MANOS CONTRARIAS**, y eso no se ve mirando
ninguna de las dos por separado. Se detecta girando el robot y comparando **cómo cambian las
dos**:

```
el yaw cambió             +89.4°
el desplazamiento cambió  −88.8°     ← signo contrario
```

### 10.3 Cómo verificarlo — tres comprobaciones

Son las que se usaron para validar cada pieza del arreglo, y **detectan una regresión en un
minuto**:

```bash
ros2 launch atriz_rvr_bringup robot.launch.py lidar:=false
```

**A · el yaw arranca en cero** (no hace falta mover el robot):

```bash
ros2 topic echo /odom --once --field pose.pose.orientation
# el yaw debe salir ~0.00°. Si sale ±50-75°, el offset no se está restando.
```

**B · la posición y la orientación son coherentes** — avanza en recto y compara la dirección
del desplazamiento con el yaw publicado. Deben **coincidir**. Y al girar el robot, deben
moverse en el **mismo** sentido.

**C · la velocidad va en el marco del robot** — avanzando recto, `odom.twist.linear` debe dar
`(+v, 0.000)` **mire donde mire el robot**, y negativo al retroceder.

Valores medidos tras el arreglo:

| | Antes | Después |
|---|---|---|
| yaw en reposo | −74.6° / +64.9° | **+0.00°** |
| dirección vs yaw | −89.7° | **+0.03°** |
| al girar 90° | +89.4° vs −88.8° (opuestos) | **+89.87° vs +90.00°** |
| `twist.linear` con el robot a 84° | `(-0.000, -0.200)` | **`(+0.101, +0.001)`** vs 0.099 real |

### 10.4 ⚠️ Dos formas de equivocarse midiendo esto

**No uses 180° para una prueba de signo.** Es exactamente el ángulo donde el signo de un giro
es ambiguo: +180 y −180 son el mismo giro. Este proyecto lo eligió **dos veces** y las dos
perdió la medida. Para comparar marcos, la prueba buena **no gira nada**: compara la dirección
de `Velocity` con la del desplazamiento del locator, que ya están en el mismo marco.

**Mide también la referencia.** Una corrida de verificación dio un 15 % de error aparente en la
velocidad. No era el driver: la ventana de medida eran 0.7 s justo después de un giro. Con 3 s
de ventana el error baja al 2 %.

### 10.5 🔴 `colcon build` desde el directorio equivocado

No es de marcos, pero costó **dar por fallida una corrección que estaba bien**, así que va
aquí:

Lanzado desde `~/atriz_ws/src/Atriz_rvr` en vez de la raíz `~/atriz_ws`, colcon crea **ahí
dentro** un workspace parásito (`build/`, `install/`, `log/`), compila contra él, dice
**«Finished»**, y el cambio **nunca llega al sistema que estás ejecutando**.

```bash
cd ~/atriz_ws && colcon build --packages-select atriz_rvr_driver
# comprobar el EFECTO, con RUTA ABSOLUTA — con ruta relativa acabas mirando el parásito:
grep -c 'lo_que_cambiaste' \
  /home/sphero/atriz_ws/install/atriz_rvr_driver/lib/python3.12/site-packages/atriz_rvr_driver/rvr_driver_node.py
ls -d ~/atriz_ws/src/*/build 2>/dev/null && echo "🔴 workspace parásito: bórralo"
```

---

## Capítulo 11 — Nav2 (Fase 4b)

✅ **VERIFICADO el 2026-07-31 — el robot navega solo.** Dos objetivos autónomos completados,
9–10 cm de error final. Lo que queda abierto está marcado ⏳ en el 11.7.

Evidencia: `00_auditoria/evidencia_24_04/16_nav2_preparacion.txt`.

### 11.1 🔴 Qué paquete instalar — y cuál NO

```bash
sudo apt install -y ros-jazzy-navigation2      # ✅ 309 paquetes
```

**No instales `ros-jazzy-nav2-bringup`**, aunque sea lo que dice la documentación oficial:

| | Paquetes | Qué arrastra |
|---|---|---|
| `ros-jazzy-navigation2` | **309** | lo que se usa: amcl, bt-navigator, controller, costmap-2d, planners, `map-server`… |
| `ros-jazzy-nav2-bringup` | **621** | lo anterior **+ Gazebo**: `nav2-minimal-tb3-sim`, `tb4-sim`, `ros-gz-sim`, y `pocketsphinx-en-us` |

`nav2-bringup` son ficheros de ejemplo para TurtleBot **en simulador**. Los launch de Atriz
los escribimos nosotros, igual que con `slam_toolbox`, y esos **312 paquetes de más acabarían
replicados en los 16 robots** vía imagen dorada. `pocketsphinx-en-us` es reconocimiento de voz,
en un robot sin micrófono.

Verificado tras instalar: 30 paquetes `nav2` en `ii`, **cero** de simulador, disco 5.4 → 6.3 GB.

### 11.2 ✅ `save_map` deja de fallar

El fallo del capítulo 9.5 (`result=255`) era **solo** la falta de `nav2_map_server`, que viene
en `navigation2`:

```
$ ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: mapa}}"
response: SaveMap_Response(result=0)
```

Genera el `.pgm` + `.yaml` que carga `nav2_map_server` — el formato que hará falta para la
Fase 4c: **mapear una vez y localizar con AMCL** en los 16 robots, en lugar de 16 SLAM
simultáneos.

### 11.3 ✅ Las velocidades máximas, medidas

**Angular**, cuatro velocidades comandadas:

| Comandada | Real | Ratio |
|---|---|---|
| 0.50 rad/s | 0.511 | 102 % |
| 1.00 | 1.014 | 101 % |
| 1.50 | 1.493 | 100 % |
| 2.00 | 1.985 | **99 %** |

**Lineal**, midiendo el perfil en el tiempo:

| Comandada | Meseta | Se alcanza en |
|---|---|---|
| 0.20 m/s | **0.199** (100 %) | ~0.5 s |
| 0.40 m/s | **0.401** (100 %) | ~0.5 s |

⚠️ **Esto retracta una afirmación que este manual llegó a tener**: «el robot no alcanza la
velocidad comandada, 0.40 → 63 %». Era la **ventana de medida**, que incluía el período
posterior a la frenada. Detalle en el capítulo 10.4 y en el fichero 16.

**Lo que sí existe es una rampa de aceleración de ~0.5 s.** Importa para Nav2 —el robot no
cambia de velocidad instantáneamente— pero se configura con `acc_lim`, no con `max_vel`. De
ahí sale `0.8 m/s²`.

### 11.4 🔴 No copies la configuración del ejemplo

`config/nav2_atriz.yaml` tiene **todos** los valores del robot sustituidos por los medidos:

| | Atriz (medido) | Ejemplo de Nav2 (TurtleBot) |
|---|---|---|
| `robot_radius` | **0.11 m** | 0.22 m — **el doble** |
| `max_vel` lineal | 0.40 m/s | 0.26 m/s |
| `max_vel` angular | 2.0 rad/s | 1.0 rad/s |
| alcance del LIDAR | **8.0 m** | 20.0 m |
| resolución del costmap | 0.05 m | 0.05 m ← la única que coincide |

**El `robot_radius` es el que más duele:** con 0.22 el robot se negaría a pasar por huecos por
los que cabe de sobra. Y un `raytrace_max_range` de 20 m haría que Nav2 despejara como «libre»
espacio que el sensor **nunca midió**.

Decisiones tomadas, con su porqué:

- **`desired_linear_vel: 0.25`** aunque el robot llegue a 0.40. Es la primera vez que navega
  solo y no tiene evitación reactiva más allá del costmap. Subirlo cuando haya rodado sin
  incidentes.
- **Regulated Pure Pursuit**, no MPPI ni DWB — es mucho más barato en CPU, y el Pi 4 ya lleva
  el driver (23 %), el LIDAR (2.4 %) y SLAM (4.4 %).
- **NavFn**, no Smac: el robot gira sobre su eje, así que no necesita respetar cinemática.
- **Costmap local de 3 × 3 m**: el robot ve 8 m, pero el controlador solo mira el entorno
  inmediato, y mantener más cuesta CPU sin aportar.
- **`lookahead_dist: 0.4`** — escalado al robot. Con 1.5 m (el del ejemplo) cortaría las curvas.

### 11.5 Arrancar — los tres launch, en orden

```bash
ros2 launch atriz_rvr_bringup robot.launch.py    # terminal 1
ros2 launch atriz_rvr_bringup slam.launch.py     # terminal 2 — publica map → odom
ros2 launch atriz_rvr_bringup nav2.launch.py     # terminal 3
```

**Nav2 no publica el robot ni el mapa: solo navega.** Necesita encontrar ya hechos el árbol TF
entero y `map → odom`.

🔴 **Los nodos de Nav2 son de ciclo de vida**, igual que `slam_toolbox`: arrancan en
`unconfigured`, vivos y sin hacer nada. Lo gestiona el `lifecycle_manager`, y **el orden
importa** — los costmaps deben estar activos antes que el controlador que los lee.

### 11.6 Verificar ANTES de mandar un objetivo

```bash
ros2 lifecycle get /controller_server    # active [3]
ros2 lifecycle get /planner_server       # active [3]
ros2 lifecycle get /bt_navigator         # active [3]
ros2 topic info /scan --verbose          # DOS suscriptores, ambos BEST_EFFORT
```

🔴 **Ese último es el que puede arruinarlo en silencio.** Si el QoS de `/scan` no emparejara,
el costmap se quedaría **vacío sin dar ningún error**: el robot navegaría creyendo que no hay
nada delante. Es la misma trampa del capítulo 9.3, y aquí las consecuencias son físicas.

Y la prueba:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 1.0, y: 0.0},
    orientation: {w: 1.0}}}}"
```

⚠️ **El robot se moverá solo hasta 0.25 m/s y no tiene evitación reactiva** más allá del
costmap: el `collision_monitor` todavía no está configurado. Espacio despejado y alguien
mirando.

### 11.7 ✅ Verificado: el robot navega

**Primera navegación autónoma del proyecto**, y repetible:

| | Desde | Hasta | Resultado | Error final |
|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.00, −0.03) | **SUCCEEDED** | **10 cm** |
| vuelta | (0.90, 0.00) | (0.00, 0.00) | **SUCCEEDED** | **9 cm** |

El error coincide con la `xy_goal_tolerance: 0.10` configurada — no es casualidad: el
controlador para al entrar en tolerancia.

📝 En la ida, la distancia restante subió una vez (0.39 → 0.52). Es una **replanificación**,
no un fallo.

✅ **Y el riesgo del QoS de `/scan` era infundado**: `/scan` acabó con **tres** suscriptores
—`slam_toolbox`, `local_costmap` y `global_costmap`— todos en BEST_EFFORT. Nav2 usa el perfil
de datos de sensor, que empareja con el driver. Comprobado además que los costmaps **ven
obstáculos de verdad**: 905 celdas ocupadas en el local, 1983 en el global.

### 11.8 🔴 El primer objetivo abortó — y no era la configuración

```
[controller_server] [ERROR] [RPPPathHandler]: Exception in transformPose:
  Lookup would require extrapolation into the future … from frame [odom] to frame [map]
[controller_server] Unable to transform robot pose into global plan's frame
[bt_navigator] Goal failed
```

Antes de tocar nada se comprobó, en vez de suponer:

| Sospecha | Medido |
|---|---|
| ¿faltan tolerancias? | RPP **0.2**, costmaps **0.3** — puestas |
| ¿`use_sim_time` incoherente? | **False** en los cinco nodos, en SLAM y en el driver |
| ¿`map → odom` con huecos? | **50.0 Hz**, mediana 20.0 ms, **máximo 25 ms**, cero huecos > 200 ms |

**Era transitorio**: el buffer TF del controlador aún no se había llenado, con los nodos recién
arrancados. El segundo objetivo, idéntico, funcionó.

⚠️ **Consecuencia práctica: da unos segundos entre activar Nav2 y mandar el primer objetivo.**
Un `ABORTED` inmediato tras arrancar **no** significa que la configuración esté mal.

### 11.9 Coste en el Pi 4, con todo corriendo

| Proceso | CPU | RSS |
|---|---|---|
| `rvr_driver_node` | 19.7 % | 89.5 MB |
| `bt_navigator` | 14.4 % | 71.3 MB |
| `controller_server` | 13.1 % | 53.7 MB |
| `behavior_server` | 11.7 % | 49.2 MB |
| `planner_server` | 11.4 % | 53.5 MB |
| `velocity_smoother` | 7.0 % | 35.7 MB |
| `async_slam_toolbox_node` | 6.9 % | 53.5 MB |
| `ydlidar_ros2_driver_node` | 3.5 % | 34.5 MB |
| `robot_state_publisher` | 1.1 % | 35.7 MB |
| **total** | **~89 %** de un núcleo | **~477 MB** |

`loadavg` 2.53 sobre 4 núcleos · **58.9 °C** · `throttled=0x0` · RAM 1.5 GB de 7.6.

**Nav2 solo son ~58 % de un núcleo**: es la pieza más pesada con diferencia, como se preveía.
Pero el Pi 4 aguanta sin throttling y **queda margen para `rosbridge`**.

### 11.10 ⏳ Lo que queda

- **`collision_monitor`.** Ahora que se ha visto navegar al robot, sus umbrales se pueden
  elegir con criterio. **Hace falta antes de dejar esto con estudiantes.**
- **Subir `desired_linear_vel` de 0.25 a 0.40.** El robot llega (medido) y ha navegado sin
  incidentes. Mejor con el `collision_monitor` ya puesto.
- **Probar con obstáculos de por medio.** Las dos navegaciones fueron en línea recta por un
  pasillo despejado: se ha probado que **llega**, no que **rodee**.
- **Fase 4c: `map_server` + AMCL** — mapear una vez y localizar en los 16 robots, en lugar de
  16 SLAM simultáneos. El `.pgm`/`.yaml` ya se genera.
- 🔴 La **inclinación de ~8°**, sin causa determinada.

---

## Capítulo 12 — El `collision_monitor` (la capa de seguridad)

✅ **VERIFICADO el 2026-07-31** contra una pared, a 0.25 y 0.40 m/s. Evidencia cruda:
`00_auditoria/evidencia_24_04/17_collision_monitor.txt`.

### 12.1 🔴 No va con Nav2, aunque el ejemplo oficial lo ponga ahí

Los estudiantes teleoperan el robot **sin Nav2**: la web hablará por rosbridge y publicará
velocidades directamente. Con el monitor colgando de `nav2.launch.py`, el caso peligroso de
verdad —una persona conduciendo el robot contra una pared **desde otro edificio**— no estaría
protegido en absoluto.

Vive en `robot.launch.py`, con **su propio `lifecycle_manager`**, porque tiene que funcionar
cuando `nav2.launch.py` ni siquiera está corriendo.

**La regla que lo hace funcionar: `/cmd_vel` tiene un solo publicador.**

```
    Nav2 (velocity_smoother) ─┐
    web / rosbridge          ─┼─► /cmd_vel_raw ─► collision_monitor ─► /cmd_vel ─► driver
    teleop / scripts         ─┘
```

⚠️ Publicar en `/cmd_vel` **funciona** —el driver obedece— pero **salta la seguridad sin dar
ningún aviso**. Por eso la verificación es contar publicadores, no mirar si hay error.

### 12.2 🔴 Un agujero real, encontrado contando publicadores

```
$ ros2 topic info /cmd_vel --verbose
Publisher count: 6
  behavior_server      ← ×5
  collision_monitor
```

El `behavior_server` abre **un publicador de `cmd_vel` por conducta**: `spin`, `backup`,
`drive_on_heading`, `wait`, `assisted_teleop`. Los cinco publicaban **directamente al robot**.

Y es el peor sitio posible para un agujero: las conductas de recuperación se ejecutan justo
cuando el robot está **atascado**, o sea pegado a algo. `backup` habría retrocedido a ciegas.

Arreglo: remapear `cmd_vel → cmd_vel_raw` también en el `behavior_server`. **No lo delataba
ningún error** — solo salió de mirar el número.

### 12.3 🔴 `approach` no es una parada de seguridad

Primera configuración, con `radius: 0.11` (el mismo `robot_radius` de los costmaps):

```
avanzando a 0.25 m/s contra la pared
HUECO REAL AL PARAR   1.1 cm     🔴 casi tocando
```

El monitor **sí actuó** (el log muestra `slowdown` y luego `approach`). Lo que estaba mal era
el modelo:

> `approach` escala la velocidad para que el choque caiga **justo** en
> `time_before_collision`. Según baja la distancia baja la velocidad, así que el robot se
> acerca **asintóticamente al contacto**. Es un frenado suave, no una parada.

Con `radius` 0.11 y media longitud de chasis **0.109** (URDF), la asíntota era 0.1 cm. Paró a
1.1 cm — exactamente como está escrito que funciona.

**La holgura se consigue inflando el círculo:**

```
hueco ≈ radius − 0.109 + ~1 cm
radius: 0.18  →  asíntota 7.1 cm  →  predicción 8 cm
```

### 12.4 ✅ Medido — y el hueco no empeora con la velocidad

| velocidad | recorrido | dist. LIDAR | **hueco real** | predicción |
|---|---|---|---|---|
| 0.25 m/s | 191 cm | 0.189 m | **8.0 cm** | 8 cm |
| 0.40 m/s | 191 cm | 0.199 m | **9.0 cm** | — |

📝 A 0.40 m/s (el máximo del robot) para **más lejos**, no más cerca: el controlador empieza a
frenar antes cuanto mayor es la velocidad.

### 12.5 ✅ No queda atrapado — lo que justifica todo el diseño

Un polígono `stop` fijo para **cualquier** movimiento mientras haya algo dentro. Un robot
pegado a una pared se congela: ni retrocede ni gira. En un laboratorio **remoto** no hay nadie
que lo levante — ese robot queda inservible hasta que alguien vaya al edificio.

Por eso los dos polígonos son **`approach` y `slowdown`, nunca `stop`**. Verificado dos veces:

| Situación | Resultado |
|---|---|
| pegado a la pared, 1.1 cm | retrocedió **196 cm** ✅ |
| a 9.0 cm | retrocedió 8.6 cm + giró en el sitio ✅ |

⚠️ **Salir de un rincón es lento.** Los 8.6 cm salen de que la caja `Precaucion` sigue viendo
la pared y frena al 40 %: `0.15 × 0.4 × 1.5 s = 9 cm`. Correcto, pero conviene saberlo antes
de pensar que el robot no responde.

### 12.6 ✅ Sin LIDAR el robot no conduce — comprobado

`source_timeout: 0.5`, no los 5.0 del ejemplo: cinco segundos a 0.25 m/s son **1.25 m
conduciendo a ciegas**.

```
kill -9 al ydlidar_ros2_driver_node
comandando 0.10 m/s durante 2.5 s   (deberían ser ~25 cm)
SE MOVIÓ 0.0 cm     ✅ BLOQUEADO
```

⚠️ **Consecuencia operativa:** si el LIDAR falla, el robot no se mueve y **no da un error
obvio en el lado que conduce**. Es lo correcto en un laboratorio remoto, pero hay que
decírselo a los estudiantes. La salida es `robot.launch.py collision_monitor:=false`.

### 12.7 ✅ Nav2 sigue llegando con la seguridad en medio

La pregunta que decide si esto es desplegable: un robot inflado a 0.18, ¿deja de alcanzar
objetivos?

```
pared a 0.97 m · objetivo 0.56 m adelante
resultado    SUCCEEDED ✅    error 9 cm    hueco a la pared 39 cm
conductas de recuperación 0 · fallos de planificación 0
activaciones del monitor  1  (slowdown 3.6 s)
```

📝 **Observado y sin explicar:** el `distance_remaining` osciló mucho (0.48 → 6.50 → 2.08 →
4.15 → 0.20 m) para un objetivo de 56 cm. El robot se desplazó **48 cm netos** y no hubo
recuperaciones ni fallos de plan, así que son longitudes del plan global recalculado, **no
distancia recorrida**. No se le atribuye causa hasta medirlo.

### 12.8 🔴 El límite que ninguna configuración arregla

El plano de barrido del X2 está a **17.45 cm del suelo** (URDF, `laser_z`).

> **Todo lo que esté por debajo de 17.45 cm es invisible para el `collision_monitor`, y el
> robot lo embestirá sin frenar.** Un zócalo bajo, una regleta, un pie de mesa que se ensancha
> abajo, un cable grueso.

No es un fallo de configuración: es lo que un LIDAR 2D puede ver. **Tiene que ir en las
instrucciones a los estudiantes.**

📝 Lo que sí está cubierto: el X2 tiene `range_min: 0.1` y va montado en el centro
(`laser_x: 0.0`), así que su punto ciego de 10 cm cae **dentro del chasis** (media longitud
0.109 m). No hay zona muerta alrededor del robot.

### 12.9 Verificar tras arrancar

```bash
ros2 lifecycle get /collision_monitor   # active [3] ← si no, NO FILTRA NADA
ros2 topic info /cmd_vel --verbose      # Publisher count: 1, y es collision_monitor
```

⏳ **Lo que queda:** subir `desired_linear_vel` a 0.40 (ya no hay excusa), probar con
obstáculos que haya que **rodear** —aquí solo se ha probado contra una pared frontal—, y
ajustar `min_points: 2` contra obstáculos finos de verdad.

---

## Capítulo 6

⏳ **No escrito todavía.** Se redacta al ejecutar las fases 1–6 del
[plan](../01_plan/PLAN_MIGRACION_ROS2.md), capítulo a capítulo, tras verificar cada paso.

Hasta entonces, para reconstruir el sistema **Noetic** el procedimiento válido es el
[manual original anotado](MANUAL_SPHERO_transcripcion.md), aplicándole las correcciones
marcadas en sus bloques `⚠️ AUDITORÍA` — en particular los nombres de paquete de los
comandos de ejecución, que ya no existen.
