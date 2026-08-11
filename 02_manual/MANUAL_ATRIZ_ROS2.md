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
> 🔴 **Este índice estuvo desviado del contenido hasta el 2026-08-01.** Decía que los
> capítulos 9, 10, 11 y 12 estaban «no escritos» cuando llevaban semanas escritos y
> verificados, y numeraba hasta 12 mientras el manual llegaba al 18. Es justo la deriva
> documentación↔realidad que la auditoría original señaló como el problema de fondo del
> proyecto, reproducida **dentro del documento que venía a arreglarla**.
> → **Si añades un capítulo, actualiza esta tabla en el mismo commit.**
>
> | Cap. | Contenido | Estado |
> |---|---|---|
> | 0 | Convenciones y hardware | ✅ verificado |
> | 1 | Enlace UART Pi ↔ RVR | ✅ verificado en 20.04 (2026-07-29) y 24.04 (2026-07-30) |
> | 2 | Ritmo de telemetría | ✅ **16.59 Hz** (2026-07-29) · **16.53 Hz** re-medido (2026-07-31) |
> | 3 | Flasheo de Ubuntu Server 24.04 | ✅ verificado 2026-07-30 |
> | 4 | Higiene del SO | ✅ verificado 2026-07-30 |
> | 5 | ROS 2 Jazzy y workspace colcon | ✅ verificado 2026-07-30 |
> | 6 | El driver del RVR en `rclpy` | 📝 **sin capítulo propio, y a propósito** — ver abajo |
> | 7 | URDF y árbol TF | ✅ verificado · medidas del chasis **medidas con cinta** el 2026-07-31 |
> | 8 | YDLIDAR X2 | ✅ verificado · `/scan` 10.1–11.9 Hz · **8.4a: gira siempre** · **8.4b: inundaba el journal, arreglado** |
> | 8bis | LEDs y sensores del RVR | ✅ verificado 2026-07-30 |
> | 9 | SLAM con `slam_toolbox` (Fase 4) | ✅ **verificado** · deriva caracterizada, 9.12b: replicar antes de atribuir |
> | 10 | Los marcos de referencia de `/odom` | ✅ **verificado** · los tres bugs de marcos, arreglados |
> | 11 | Nav2 (Fase 4b) | ✅ **el mecanismo, verificado** · ⚠️ el «error final 9–10 cm» es la tolerancia repetida, ver 11.7 |
> | 12 | El `collision_monitor` | ✅ **verificado** · parada en 9.9 cm |
> | 13 | La inclinación del RVR: es el acelerómetro | ✅ **verificado** · y dos conclusiones retiradas |
> | 14 | `map_server` + AMCL (Fase 4c) | ✅ **verificado** · 0.1 cm siguiendo la pose |
> | 15 | La parada de emergencia: tres fallos silenciosos | ✅ **verificado con control** (15.4) |
> | 16 | Los servicios del driver y el sensor de color | ✅ **verificado** |
> | 17 | Arranque automático con systemd | ✅ **verificado con un reinicio real** |
> | 18 | Telemetría que faltaba: motores, encoders, luz | ✅ **verificado** · 18.4: los dos sensores ópticos |
> | 19 | **Red de la flota y cómo la web encuentra a los robots** | ✅ **verificado de extremo a extremo 2026-08-01** |
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

Hecho en el commit `67c8776`, hoy en el histórico de `ros2` (se hizo en `migracion-ros2`,
rama borrada el 2026-08-03; el commit sigue alcanzable).

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

📝 **Ese bloque es de la época ROS 1 y ya no se puede ejecutar**: `medir.py` usa `rospy` y muere
con `ModuleNotFoundError`. Se conserva porque documenta cómo se obtuvo aquella medida. El
equivalente hoy es `mediciones_banco/medir_ritmo_ros2.py`, con el robot corriendo bajo
`atriz-robot.service`.

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

`atriz_rvr_driver/scripts/Atriz_rvr_node.py:1313` → `interval=60`. Commit `24c7749`, hoy en el
histórico de `ros2` (se hizo en `migracion-ros2`, rama borrada el 2026-08-03). En el port a
`rclpy` pasa a ser el valor por defecto del parámetro `streaming_interval_ms`.

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

### 8.4a ✅ El X2 gira SIEMPRE, a dos velocidades — **medido 2026-07-31**

Pregunta del usuario: *el lidar siempre está girando nada más encender el sistema, y solo va
más rápido cuando se usa. ¿Está bien? ¿No se ahorraría si girara solo cuando hace falta?*

La observación es correcta y tiene un mecanismo. **DTR no enciende el motor: elige su
velocidad.** Medido alternando cada 12 s sin cerrar el puerto entre tramos — cerrarlo
reinicia las líneas de control y falsea la medida:

| línea | giro (5 tramos cada una) | checksums |
|---|---|---|
| `DTR=1` | 11.86 · 11.77 · 11.85 · 11.85 · 11.76 Hz | 99.8 % |
| `DTR=0` | 2.66 · 2.74 · 2.73 · 2.63 · 2.74 Hz | 99.8–100 % |

**4.3×**, diez tramos, ninguno fuera de sitio. A 2.7 Hz el lidar **sigue midiendo bien**: solo
gira más despacio, con menos resolución angular.

Los dos estados que se oyen son exactamente estos:

```
sin nada corriendo   ->  puerto cerrado  ->  DTR cae  ->   2.7 Hz    (el «lento»)
driver arrancado     ->                      DTR sube ->  11.8 Hz    (el «rápido»)
```

✅ **Confirmado por oído**, que es una vía independiente del protocolo: el usuario escuchó los
dos minutos y reportó «cambio claro cada ~12 s». En este proyecto ya costó caro un «confirmado
por tres vías» que era una sola vía contada tres veces (cap. 13), así que aquí importa que una
medida sea mecánica y la otra sea el contenido de las tramas.

#### `/stop_scan` y `/start_scan` existen, y frenan el motor de verdad

El `ydlidar_ros2_driver_node` publica dos servicios `std_srvs/srv/Empty` que este proyecto no
tenía documentados:

```
/stop_scan   ->  CYdLidar::turnOff()  ->  stop()  ->  stopMotor()  ->  clearDTR()
/start_scan  ->  CYdLidar::turnOn()             ->  startMotor()  ->  setDTR()
```

```
/scan escaneando      : 11.81 Hz
/scan tras stop_scan  :  0.00 Hz
/scan tras start_scan : 13.44 Hz     <- se recupera solo, sin reiniciar nada
```

✅ Y se confirmó **también por oído** que además frena el motor, no solo calla el topic:
alternando `/stop_scan` ↔ `/start_scan` cada 12 s el usuario oyó «el mismo cambio que antes».
Sin esa segunda pasada solo sabríamos que el topic se calla, que es mucho más débil.

📝 `support_motor_dtr: true` se verificó con `ros2 param get` sobre el **nodo vivo**, no
leyendo el YAML: es la diferencia entre comprobar el efecto y comprobar la intención.

📝 Curiosidad del SDK: `ydlidar_help.h:548 isSupportMotorCtrl()` calcula un `ret` mirando el
modelo (X4, S2, S4, S4B) y luego hace **`return true;`** ignorándolo. Es un bug, pero aquí
juega a favor: sin él el X2 no entraría por la rama del motor.

#### ⚠️ Lo que esto NO resuelve, que es la mitad de la respuesta

**`/stop_scan` no baja de 2.7 Hz.** Llega exactamente al mismo reposo al que llega solo el
lidar cuando no hay driver. No es un apagado. Así que hoy, con el robot apagándose entre
sesiones, **no hay nada que ahorrar**: el salto grande ya ocurre solo.

Y **pararlo del todo no está en la mano del software**: DTR frena el motor, pero el láser, el
receptor y el MCU siguen alimentados mientras haya 5 V en el USB, y la Pi 4 no puede cortar
VBUS. Haría falta un interruptor físico en la línea de 5 V, en 16 robots.

#### 🔴 Dónde sí cambia la respuesta: el arranque automático con systemd

Hoy el lidar se queda a 2.7 Hz porque no hay nada corriendo. **En cuanto los 16 robots arranquen
`robot.launch.py` solos al encender, pasará a 11.8 Hz permanentes, 24/7, en los 16**, se use el
robot o no. Sería *peor* que la situación actual, y habría llegado como efecto secundario de una
tarea que no habla de lidares.

→ **Diseño a aplicar al escribir las unidades systemd:** el robot arranca con todo levantado y
listo para responder, pero con el escaneo **parado**, y se activa al empezar una sesión.

✅ **Y medido con control**, porque es la afirmación que sostiene todo el diseño: arrancar con el
lidar parado solo es aceptable si el robot no puede moverse en ese estado.

| barrido | mismo comando por `/cmd_vel_raw` | desplazamiento |
|---|---|---|
| **apagado** | 0.10 m/s · 1.5 s | **0.0 cm** ✅ bloqueado |
| **encendido** (control) | 0.10 m/s · 1.0 s | **9.9 cm** |

🔴 Sin el control, «0.0 cm» no demuestra nada: es indistinguible de un `cmd_vel` que nunca llegó.

#### ⏳ Lo que queda sin medir

**Cuánta corriente se ahorra entre 11.8 y 2.7 Hz: NO MEDIDO.** No se estima de la ficha a
propósito — la del RVR ya mintió en las tres dimensiones del robot y la del X2 con el
`frequency` configurable. Se mide con `/battery_state`, el robot quieto, un par de horas por
estado. La premisa del usuario sí es buena: **la Pi se alimenta del puerto USB del RVR**, así
que ese consumo sale de la batería del robot.

📝 Y hay un coste que no es eléctrico y puede pesar más: el X2 gira **desde que se enciende la
Pi hasta que se apaga**, siempre. Eso es desgaste de rodamiento continuo en 16 unidades — el
argumento más fuerte para un interruptor físico.

Evidencia cruda: `00_auditoria/evidencia_24_04/30_lidar_giro_dtr.txt`.

### 8.4b 🔴 El nodo del YDLIDAR inundaba el journal con el barrido apagado

> ✅ **ARREGLADO el 2026-08-01** con un parche de nueve líneas. Evidencia 40.

Consecuencia no prevista de la decisión de 8.4a. Con `atriz-escaneo off` —que es el **estado
normal en reposo** de los 16 robots— el nodo emitía:

```
[ydlidar_ros2_driver_node-3] [ERROR] ... : Failed to get scan
```

**502 errores en 20 s = 25 por segundo.** El **99 %** del journal del servicio (47 291 de 47 551
líneas), **2.17 millones de mensajes al día por robot**, 34 millones entre los 16.

🔴 **Lo grave no es el ruido:**

1. **Ahoga cualquier error de verdad.** Los peores fallos de este proyecto están documentados como
   silenciosos, y el journal es donde se buscan.
2. **Desgasta la microSD.** Las tarjetas mueren por escrituras, y es el único almacenamiento que
   tiene el robot.
3. Sondea el puerto serie 20 veces por segundo para nada.

⚠️ **Y no lo ve nadie:** el servicio está `active`, el verificador pasa, y el robot funciona.

#### La causa, y por qué la primera solución era peor que el problema

La primera propuesta fue **no levantar el nodo del LIDAR** hasta que hiciera falta. El usuario
desconfió — *«¿voy a perder esa automatización al encender el robot?»*— y al ir a argumentarlo
hubo que leer el fuente. La causa real estaba ahí:

```cpp
while (ret && rclcpp::ok()) {
  if (laser.doProcessSimple(scan)) { ...publica... }
  else { RCLCPP_ERROR(node->get_logger(), "Failed to get scan"); }   // 20 Hz
}
```

`/stop_scan` y `/start_scan` son servicios **del propio nodo** y llaman a `turnOff()`/`turnOn()`,
pero **nadie guarda ese estado**. No era una consecuencia de apagar el barrido: **al driver le
falta una variable.**

📝 **La lección de método:** las tres soluciones que se habían planteado atacaban el síntoma, y la
recomendada cambiaba el arranque del robot para nada. **Antes de rediseñar el arranque de un
sistema, mira por qué falla el componente.** La desconfianza del usuario fue lo que forzó a mirar.

#### El arreglo, y cómo sobrevive a un reflasheo

Una bandera `std::atomic<bool> escaneando` que los dos servicios actualizan, y una salida temprana
en el bucle. Con el barrido parado no se toca el hardware ni se escribe en el log, pero **se sigue
atendiendo a ROS** — los servicios tienen que responder para poder volver a encenderlo.

| | antes | después |
|---|---|---|
| barrido apagado | 502 errores / 20 s | **0** |
| `atriz-escaneo on` | — | `/scan` a **12.00 Hz**, 250 puntos |
| `atriz-escaneo off` | — | 0 mensajes, **0 ruido** |

✅ **El nodo sigue levantándose con el robot**, igual que antes.

🔴 **Y va como parche versionado, no como edición a mano.** `provision.sh` clona el ydlidar de
GitHub y **le borra el `.git`**: un cambio manual se perdería al reflashear y este robot
divergiría de uno recién aprovisionado — y la regla del proyecto dice que **gana el script**. El
parche vive en `Atriz_rvr/atriz_rvr_bringup/patches/`, `provision.sh` lo aplica tras clonar (y es
idempotente), y el verificador comprueba **el fuente y el efecto**.

📝 Si el upstream lo arregla algún día, el parche fallará al aplicarse y `provision.sh` lo dirá.
Es lo que queremos: enterarnos, no seguir en silencio.

---

---

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
- **Activar SSH**, marcando 🔴 **«usar contraseña para autenticar»** — **NO** «permitir sólo
  autenticación por clave pública»
- Zona horaria y teclado

> Dejar que el Imager configure el WiFi ahorra tener que escribir netplan a mano.

> 🔴 **Contraseña, no clave pública.** El Pi va headless: si marcas sólo clave pública y esa
> clave no es la del PC desde el que entras, no hay teclado ni pantalla con los que arreglarlo y
> toca sacar la tarjeta. Toda la flota va por contraseña — **verificado en rvr-01 el 2026-08-11**:
> `PasswordAuthentication` sin tocar (o sea `yes`) y `~/.ssh/authorized_keys` de **0 bytes**.

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

> 🔴 **`cfg80211.ieee80211_regdom=CO` está puesto y NO surte efecto.** Medido en rvr-01 el
> 2026-08-03:
>
> ```
> /sys/module/cfg80211/parameters/ieee80211_regdom   ->  CO          # el parámetro SÍ llegó
> iw reg get                                         ->  global country US: DFS-FCC
>                                                        phy#0  country 99: DFS-UNSET
> ```
>
> El firmware del `brcmfmac` es *self-managed*: fija su propio dominio y **pisa** el parámetro del
> kernel. El dominio regulatorio real de este robot es **US**, no CO. Leer el `cmdline.txt` y dar
> por hecho que está aplicado es el mismo error que este proyecto lleva toda la migración
> encontrando — el parámetro se aplica, el efecto no.
>
> **Hoy no rompe nada**, porque los canales de 2.4 GHz que usa el laboratorio están permitidos en
> los dos dominios. Se anota para que nadie lo dé por resuelto si algún día hace falta un canal
> que dependa del país. `verificar_robot.sh` sección 12 lo comprueba comparando el `iw reg get`
> con lo que pide el `cmdline.txt`, y avisa si no coinciden.
>
> ⚠️ **De dónde salió: no se sabe.** `grep -rn regdom scripts/` no encuentra nada, así que **no
> lo pone ningún script del repositorio**; se escribió a mano en algún momento de la instalación
> y no quedó registrado. Eso significa que una tarjeta grabada siguiendo este manual **no lo
> tendría**, y las 16 saldrían distintas según quién las prepare. Por eso `preparar_tarjeta.sh`
> lo fija ahora de forma idempotente: no porque el parámetro sirva —no sirve—, sino para que las
> 16 tarjetas sean iguales y el `cmdline.txt` de un robot no dependa de quién lo grabó.

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
ps -e | wc -l                       # antes: 187 tareas
# ⚠️ el objetivo '< 120' estaba MAL PLANTEADO: ps -e cuenta ~123 hilos de
#    kernel, y con atriz-robot.service corriendo suma 86 tareas más.
#    Medido el 2026-07-31: 166 totales = 80 del SO + 86 del robot.
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
| Servicios inútiles | activos | ✅ `snapd`, `ModemManager`, `multipathd`, `open-iscsi`, `iscsid`, `lvm2-monitor`, `unattended-upgrades`: disabled. 🔴 **`avahi` YA NO** — ver abajo |

> 🔴 **`avahi-daemon` SE QUEDA desde el 2026-08-01.** Esta tabla lo listaba entre los servicios
> deshabilitados, con el criterio de «inútil en un robot headless». Era un error: **es lo que
> hace que un robot responda a `rvr-NN.local`**, y sin él la web tendría que saberse 16 IP.
> Además contradecía al propio manual, que en el cap. 7 decía «usa `ping rvr-01.local`».
> `fase_1_higiene_so.sh` ahora lo **habilita** y activa `MulticastDNS=yes`. Cap. 19.5.
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
#            ↑ `ros2` es la rama por defecto desde el 2026-08-04: el `-b` ya no
#              hace falta. Se deja explícito porque `main` sigue existiendo y es
#              ROS 1 (catkin), no compila con colcon y va 75 commits detrás.

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

## Capítulo 6 — El driver del RVR en `rclpy`

📝 **Este capítulo no tiene cuerpo propio, y es una decisión, no un olvido.**

Hasta el 2026-08-01 decía *«no escrito todavía, se redacta al ejecutar las fases 1–6»*, y
además estaba **físicamente colocado entre el 16 y el 17**. Las dos cosas eran falsas: las
fases 1–6 estaban ejecutadas y el driver llevaba semanas funcionando.

El driver **sí está documentado**, pero repartido por tema, que es como está organizado este
manual. Un capítulo 6 que lo repitiera sería una segunda copia que se desviaría de la primera
— exactamente el problema que este proyecto arrastra. Dónde está cada cosa:

| Del driver quieres saber… | Capítulo |
|---|---|
| Cómo publica `/odom`, y los tres bugs de marcos de referencia | **10** |
| Los servicios (LEDs, movimiento, sensores) y el sensor de color | **16** |
| La parada de emergencia y sus tres fallos silenciosos | **15** |
| `/motor_status`, `/encoders`, `/ambient_light` | **18** |
| El keepalive y el detector de silencio (el RVR se duerme a los 5 min) | **2** y `CLAUDE.md` |
| Convenciones de ejes de cada sensor (FRD contra FLU) | **10.3** |
| Que arranque solo bajo systemd | **17** |

🔴 **Y la trampa que vale por todo el capítulo:** construir `SpheroRvrAsync` desde dentro de
una corrutina falla con `RuntimeError: This event loop is already running`, y el nodo arranca
**con todos los topics registrados y cero datos**. Constrúyelo con el loop parado, antes de
arrancar el hilo. Ha mordido dos veces.

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
| **`odom → base_footprint`** | **el driver** (`atriz_rvr_driver`) | Es el único que sabe dónde está el robot. 🔴 **`base_footprint`, no `base_link`** — ver abajo |
| `base_footprint → base_link` | `robot_state_publisher` | Geometría fija, sale del URDF |
| `base_link → laser`, `imu_link`, ruedas | `robot_state_publisher` | Idem |

🔴 **ESTE PÁRRAFO DECÍA JUSTO LO CONTRARIO HASTA EL 2026-08-01**, y enseñaba la configuración
que **partió el árbol TF y costó la Fase 3**: decía que el driver publica `odom → base_link` con
`base_frame` por defecto `base_link`.

✅ **Lo correcto:** el driver publica **`odom → base_footprint`**. El parámetro `base_frame`
vale **`base_footprint`** por defecto, y el código lleva el comentario
`# 🔴 base_footprint, NO base_link`.

**Por qué importa:** con `odom → base_link`, y el URDF publicando `base_footprint → base_link`,
**`base_link` tendría DOS padres**. En TF un frame solo puede tener uno: el árbol se parte en
dos mitades y `slam_toolbox` repite `Failed to compute odom pose` sin que nada más falle.

⚠️ **Y la trampa de método, que es lo que de verdad hay que llevarse:** la verificación de
entonces era `tf2_echo odom laser` y **pasaba**, resolviendo por el camino equivocado
(`odom → base_link → laser`) mientras `base_footprint` colgaba de otro árbol. **Comprueba el
transform que pide el consumidor, con sus frames exactos** — aquí `tf2_echo odom base_footprint`.
Un `tf2_echo` que resuelve prueba que hay *un* camino, no que el árbol esté bien.

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

> 🔴 **ESTA SUMA ESTABA MAL, y el error era `base_height`.** Medido con regla el 2026-07-31: el
> RVR mide **7.0 cm** de alto, no los 11.4 de la ficha, y el plano de barrido está a **15.5 cm**
> del suelo — 2 cm por debajo de lo que daba esta cuenta. `laser_z` es hoy un **valor directo
> medido**, no una suma. Cap. 12.8 y `03_operacion/MEDIDAS_ROBOT.md`.
>
> 📝 Se conserva la derivación porque explica **por qué** dos de sus tres sumandos venían de una
> ficha de fabricante, que es la causa raíz.

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
>
> 🔴 **MATIZADO EL 2026-08-08, y el matiz es una función:** eso vale para una superficie que
> **REFLEJA**. Para una que **EMITE luz propia** —una pantalla, una baldosa LED— la luz apagada es
> el modo **correcto**, y encendida da lo contrario de lo que hay: una pantalla roja a tope da
> `R/G = 0,53`, o sea **menos rojo que verde**, porque el reflejo especular del LED sobre el vidrio
> tapa el color. Apagada da `R/G = 6,17`.
>
> ⚠️ **Y en ese modo el topic `/color` no sirve: publica ceros** (medido: 0 de 39 mensajes). Sale
> del *streaming* del RVR, que se apaga con la detección; hay que usar el **servicio**
> `/get_rgbc_sensor_values`, que consulta. Los dos modos y el contrato para la web están en
> [`03_operacion/SENSOR_COLOR.md`](../03_operacion/SENSOR_COLOR.md). Evidencia 86.

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

> 🔴 **ESTA SECCIÓN ESTÁ SUPERADA. Lee antes el 9.12a.** Sus números salen de n=3 por distancia
> y **tuvieron suerte**: con n=6, la mitad de las corridas largas fallan catastróficamente.

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

### 9.12a 🔴 CORRECCIÓN: SLAM falla en ~1 de cada 5 corridas

> ⚠️ **Esta sección se escribió atribuyendo el fallo a la DISTANCIA. Eso quedó
> retirado una hora después por una réplica — lee el 9.12b.** Lo que sigue siendo
> cierto es que el fallo EXISTE y es bimodal; lo que no, que dependa del recorrido.

**Repetido el 2026-07-31 con n=6 por distancia** (12 corridas en total, mismo método).
Evidencia: `21_deriva_roll_y_fallo_largo.txt`, sección 3.

```
CORTA (158 cm, n=6)   0.9  1.0  1.0  1.2  2.1  2.2  2.9
  -> mediana 1.65 cm · peor 2.9 cm · corridas > 5 cm: 0 de 6        ✅

LARGA (233 cm, n=6)   0.9  1.1  1.2  |  12.0  16.0  56.1
  -> mediana 6.60 cm · peor 56.1 cm · corridas > 5 cm: 3 de 6  🔴 el 50 %
```

🔴 **Es BIMODAL: o ~1 cm o ≥ 12 cm, sin nada en medio.** Eso no es deriva gradual — es el
emparejado de barridos **enganchando o perdiéndose**. Los errores angulares acompañan: 0.9–2.4°
en las buenas, **5.2–28.1°** en las malas.

| | 9.12 (n=3) | **9.12a (n=6)** |
|---|---|---|
| CORTA mediana | 1.0 cm | 1.65 cm |
| LARGA mediana | 2.7 cm | **6.60 cm** |
| **peor caso** | 3.2 cm | **56.1 cm** 🔴 |

**Y esto resucita la anomalía de la Fase 4.** Aquella corrida de 2.62 m con 87.8 cm y 10.9° se
atribuyó a que el robot rozó obstáculos, y el 9.12 la dio por explicada. **Es el mismo fallo
bimodal: no era una anomalía, es la mitad de las veces.**

**Los fallos no siguen a ninguna condición controlada**: fueron las corridas largas 2ª, 3ª y 4ª
—contiguas— repartidas entre las dos ramas del experimento del cap. 13.6, y decrecieron
(56.1 → 16.0 → 12.0) antes de desaparecer.

⏳ **Causa sin determinar.** La firma temporal apunta a algo del entorno que cambió y volvió,
pero **no hay evidencia** y no se le atribuye causa. Lo primero sería repetir **solo corridas
largas**, muchas, registrando la **pose absoluta de partida** de cada una.

🔴 **RETIRADO:** aquí se concluyó que «SLAM es fiable hasta ~1.6 m y deja de serlo a ~2.3 m».
La réplica del 9.12b lo desmonta.

### 9.12b 🔴 La réplica: el fallo NO depende de la distancia

Mismo protocolo, mismo robot, **una hora después**. Evidencia: `22_replica_deriva.txt`.

| | TANDA 1 | TANDA 2 (réplica) |
|---|---|---|
| CORTA (158 cm) | 1.0, 1.0, 1.2, 2.1, 2.2, 2.9 → **0 de 6** | 0.8, 0.8, 1.6, 2.7, **6.6**, **14.3** → **2 de 6** |
| LARGA (233 cm) | 0.9, 1.1, 1.2, **12.0**, **16.0**, **56.1** → **3 de 6** | 1.0, 1.9, 2.5, 2.7, 3.0, 3.3 → **0 de 6** |

**El fallo cambió de distancia.** En la tanda 1 fallaban las largas y las cortas iban perfectas;
en la 2, al revés. 🔴 **La distancia no es la variable.**

**Las 24 corridas juntas:**

```
CORTA (n=12)   normales (10): mediana 1.40 cm, rango 0.8–2.9   ·  fallos (2): 6.6, 14.3   → 17 %
LARGA (n=12)   normales  (9): mediana 1.90 cm, rango 0.9–3.3   ·  fallos (3): 12, 16, 56  → 25 %
GLOBAL: 5 fallos de 24  →  ~21 %
```

✅ **Cuando funciona, funciona bien y casi igual a las dos distancias** (1.40 vs 1.90 cm). Eso
también desmonta la narrativa del 9.12 de que la deriva crecía proporcionalmente al recorrido.

🔴 **Y una de cada cinco corridas falla**, de forma bimodal: o ≤3.3 cm o ≥6.6 cm.

#### La causa más probable: el robot se va del sitio y nadie lo corrige

La tanda 2 registró el entorno antes de cada bloque:

| bloque | adelante | der | CORTA | recorrido |
|---|---|---|---|---|
| A1 | 2.06 m | **0.97** | **6.6** 🔴 | 159 |
| B1 | 2.11 | 0.42 | 1.6 | 158 |
| A2 | 2.01 | 0.30 | 0.8 | 156 |
| B2 | **1.64** | 0.26 | **14.3** 🔴 | **137** |
| A3 | 1.73 | 0.19 | 0.8 | 156 |
| B3 | 1.73 | **0.16** | 2.7 | 153 |

🔴 **`der` cae de forma monótona: 0.97 → 0.16 m.** El robot deriva a la derecha corrida tras
corrida y acaba **a 5 cm de rozar** (media anchura 11 cm). Y en la tanda 1, medido antes y
después: **94 cm de deriva hacia delante en 12 corridas**, ~8 cm por corrida.

> 🔴 **La consecuencia de método, que es la importante:** `caracterizar_deriva_slam.py` y
> `comparar_deriva_roll.py` asumen que el robot vuelve al punto de partida y que las N corridas
> son repeticiones del **mismo** experimento. **No lo son** — cada una empieza en un sitio
> distinto. Eso no es una repetición: es un barrido por posiciones, sin control ni registro.

⏳ **El arreglo, no implementado:** re-referenciar la posición **antes de cada corrida**,
conduciendo el robot hasta una distancia objetivo de la pared frontal con `/scan`. Hasta
entonces ninguna de las dos herramientas puede dar una distribución válida.

🔴 **La inclinación de ~8°**, confirmada por **tres vías independientes** (árbol TF, Roll de la
IMU y acelerómetro). Causa sin determinar.

📝 Los resultados de deriva **acotan su gravedad**: con la inclinación presente, la deriva es de
2.7 cm. Así que no está arruinando el emparejado. Sigue habiendo que resolverla para Nav2
—por REP-105 `odom → base_footprint` debería ser plana— pero **no es urgente**.

✅ **La velocidad de `/odom` está arreglada** (2026-07-31). El stream nunca fue el problema:
es exacto. Lo que fallaba era que el driver copiaba una velocidad del marco del **mundo** a un
campo que ROS define en el marco del **robot**. Ahora publica `(+0.101, +0.001)` con el robot
a 84° contra 0.099 m/s reales — 2 % de error. **Capítulo 10.**


### 9.12c ✅ Referenciar la posición: los fallos desaparecen

**Arreglado el 2026-07-31.** Herramienta nueva: `mediciones_banco/referenciar_posicion.py`,
llamada por `caracterizar_deriva_slam.py` **antes de cada corrida**. Evidencia:
`23_referenciar_posicion.txt`.

#### Cómo fija el origen

Ajusta una recta a los puntos de la pared frontal en el marco del robot:

```
x = m·y + c    →    error de rumbo θ = atan(m)
                    distancia perpendicular D = c·cos(θ)
```

Y entonces, **en este orden**: (1) conduce hasta la distancia objetivo, (2) gira −θ.

🔴 **El orden importa**, y salió probando. Al revés —rumbo y luego distancia— conducir vuelve a
torcer el rumbo recién corregido: medido, pasó de +0.41° a **+2.53°**. Girar sobre el eje **no**
cambia la distancia perpendicular, porque el centro del robot no se mueve, así que la rotación
va la última.

🔴 **No usa `/odom` ni el mapa, a propósito**: referenciar con odometría sería circular — es
justo lo que se está midiendo. El LIDAR contra una pared física es independiente.

Precisión, dos pasadas seguidas: **±0.2 cm y ±0.2°**.

#### ✅ El robot se queda donde debe — y esto no depende de ninguna estadística

| | adelante | derecha |
|---|---|---|
| **sin** referenciar (tanda 2) | 2.06 2.11 2.01 1.64 1.73 1.73 → rango **0.47 m** | 0.97 0.42 0.30 0.26 0.19 0.16 → rango **0.81 m** |
| **con** referenciar (tanda 3) | 3.50 3.52 3.51 3.48 3.46 3.47 → rango **0.06 m** ✅ | 0.92 0.94 0.94 0.95 0.93 0.93 → rango **0.03 m** ✅ |

**8× menos dispersión hacia delante y 27× lateral**, y la deriva monótona desaparece.

#### ✅ Y los fallos desaparecen

| | fallos > 5 cm | peor caso |
|---|---|---|
| tandas 1+2, **sin** referenciar | **5 de 24** | **56.1 cm** |
| tanda 3, **con** referenciar | **0 de 12** | **4.4 cm** |

Las doce corridas: `0.5 0.5 0.7 0.7 0.9 0.9 1.1 2.1 2.2 3.7 3.7 4.4`. **La distribución deja de
ser bimodal**: ya no hay dos grupos separados, hay una sola nube.

⚠️ **Honestidad estadística:** Fisher exacto de 0/12 contra 5/24 da **p = 0.113** — sugerente,
**no concluyente al 5 %**. Con una tasa base del 21 %, sacar 0 de 12 por azar tiene un 6 % de
probabilidad. Lo indiscutible es la tabla de posiciones; que los fallos desaparezcan a la vez
es coherente, pero confirmarlo pide otra tanda.

#### ✅ Y la deriva NO crece con la distancia

```
CORTA (158 cm, n=6)   0.5  0.9  0.9  2.2  3.7  3.7   mediana 1.55 cm
LARGA (233 cm, n=6)   0.5  0.7  0.7  1.1  2.1  4.4   mediana 0.90 cm
```

La larga recorre un **47 % más** y sale **igual o mejor**. Eso desmonta definitivamente la
narrativa del 9.12 («0.63 % del recorrido en las cortas, 1.14 % en las largas»): con la posición
controlada, esa proporcionalidad no aparece.

✅ **Para Nav2:** la localización da **1–4 cm** en recorridos de 1.6–2.3 m, muy por debajo de la
tolerancia de objetivo de 10 cm. **Ya no es un bloqueante** — siempre que el robot no acabe
donde no debe, que era el problema real.

### 9.12d ⚠️ La pregunta del roll: ahora se intuye, y sigue sin resolverse

```
CON roll  n=6  media 2.23 cm   [0.5, 0.5, 2.1, 2.2, 3.7, 4.4]
SIN roll  n=6  media 1.33 cm   [0.7, 0.7, 0.9, 0.9, 1.1, 3.7]
diferencia +0.90 cm
```

📝 **Y las dos distancias apuntan en el mismo sentido**, cosa que antes no pasaba: CORTA
+1.30 cm, LARGA +1.40 cm. El roll **siempre** sale peor, y la magnitud coincide con la predicha
— `cos(6.9°)` comprime los alcances un 0.7 %, ~0.7 cm por metro.

⚠️ **Pero no es significativo.** Test de permutación exacto sobre las 924 particiones posibles:
**p = 0.142**. Con n=6 por rama no se puede concluir.

⏳ **Lo que haría falta:** con d = 0.64 (efecto 0.90 cm, σ 1.40), **~31 corridas por rama** para
80 % de potencia al 5 % → **~62 corridas, unas 5.2 horas de robot**. Hoy hay 6 por rama.

> ✅ **DECIDIDO el 2026-07-31: no se persigue.** El efecto es de ~1 cm sobre una tolerancia de
> objetivo de Nav2 de 10 cm, y costaría 5 horas de robot. La decisión **no deja el roll
> publicado**: `publicar_inclinacion` pasa a `false` por defecto, porque la inclinación es falsa
> con independencia de que su efecto sea medible (cap. 13.5).

---

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
va a **15.5 cm** ✅ medido de altura barriendo en horizontal, así que pasa por encima de zócalos
y cajas bajas — «parece despejado» a ras de suelo no basta.

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

### 10.2b ⏳ ¿Se puede tener un rumbo ABSOLUTO? La vía que queda

El yaw arbitrario no es un problema con un robot: se resta el origen al arrancar y se navega en
relativo. **Con 16 sobre un mapa compartido sí lo es**: cada uno cree mirar en una dirección
distinta, y hoy la única forma de relacionarlos es que alguien los coloque a mano.

🔴 **Lo que NO funciona, y por qué no insistas:**

| Idea | Por qué no |
|---|---|
| `get_magnetometer_reading()` | **`bad_cid`** en este firmware — comando desconocido |
| Actualizar el firmware | Ya tenemos el último: **9.1.462 / 9.2.482** (Fall 2022) |
| Buscar un «SDK modificado» | El SDK solo serializa el protocolo. **`bad_cid` lo responde el robot** |

📝 Y hay una ironía: en el foro oficial, con el firmware **anterior** (8.3.432/8.6.448), la
lectura cruda **sí respondía**. La versión más nueva tiene **menos** API cruda, no más.

✅ **Pero el RVR sí lleva magnetómetro** — es una IMU de 9 ejes — y **la lectura cruda no es la
que hay que usar**. Lo dice un ingeniero de Sphero en el foro oficial:

> «The `yaw_north_direction` value is **the offset from yaw=0 to magnetic north**.»
>
> «In the case of the EDU app, **it never actually requests a magnetometer reading directly.
> Instead, it simulates the magnetometer heading using the reported north offset and the IMU
> heading.** You can do the same in your own programs.»

**El patrón previsto por el fabricante:**

```
1. magnetometer_calibrate_to_north()      ← una sola vez, CID 0x25
2. llega la notificación con {'is_successful': True, 'yaw_north_direction': N}
3. desde ahí:   rumbo_absoluto = yaw_de_la_IMU + N
```

🔴 **La calibración GIRA EL ROBOT 360°** en sentido antihorario. El ejemplo oficial de Sphero no
lo advierte; `mediciones_banco/probar_magnetometro.py` sí, y por eso exige `--calibrar`.

🔴 **PROBADO EL 2026-08-01 — Y NO FUNCIONA. La vía queda cerrada.**

```
Calibración 1/3 — girando…
   🔴 sin notificación en 45 s
```

El comando **se aceptó sin error** (no dio `bad_cid`), no llegó notificación, **y el robot no
giró** — esto último lo confirmó el usuario mirándolo, y es lo que zanja la cuestión: sin ese
dato, «no llegó el aviso» era ambiguo. Es un **no-op**.

**Las dos vías están cerradas**, así que el RVR no puede dar un rumbo absoluto. La pose inicial
de cada robot tendrá que venir **del mapa** (AMCL con pose inicial por robot, que ya se
planeaba) o **del operador**. No bloquea nada —AMCL sigue la pose con 0.1 cm— pero se pierde
poder inicializar sin intervención humana. **Es una limitación del hardware, no una tarea
pendiente.**

📝 Lo que se sospechaba, y se cumplió:

1. El resultado llega por **notificación**. ⚠️ Y este argumento se apoyaba en que «las
   notificaciones de motor no llegan», **que resultó ser falso** (cap. 18): la de atasco sí
   llega. Así que la sospecha era más débil de lo que parecía — pero la conclusión no cambia,
   porque la calibración se probó y **no hizo nada**.
2. **Hay dos motores con imanes a centímetros del sensor.** El propio Sphero avisa de que a ras
   de suelo las lecturas son ruidosas por el hierro de las estructuras.

→ **Criterio para darlo por bueno:** tres calibraciones, girando el robot en medio, que
coincidan en unos pocos grados. **Un valor que no se repite no sirve como referencia.** Si
falla, la pose inicial tendrá que venir del mapa o del operador, y eso pasa a ser una limitación
del hardware, no una tarea pendiente.

Detalle completo en `00_auditoria/evidencia_24_04/42_magnetometro_y_firmware.txt`.

---

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
9–10 cm de «error final» ⚠️ que es la tolerancia repetida, no una medida — ver el aviso del 11.7. Lo que queda abierto está marcado ⏳ en el 11.7.

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
| `robot_radius` | **0.145 m** | 0.22 m — el TurtleBot es mayor |

> 🔴 **Esta tabla decía `0.11 m` y lo presentaba como «Atriz (medido)».** Era falso por partida
> doble: el fichero real tiene **0.145** (radio circunscrito medido 0.142), y el 0.11 salía de
> las cotas equivocadas de la ficha del RVR. Con `0.11` el `collision_monitor` llegó a parar a
> **1.1 cm de la pared** (cap. 12.4). El propio manual lo corrige en el cap. 12.10; esta tabla
> se quedó atrás.
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

🔴🔴 **CORREGIDO EL 2026-08-08: ESA COLUMNA NO ES UN ERROR MEDIDO. ES LA TOLERANCIA, REPETIDA.**

Aquí ponía: *«El error coincide con la `xy_goal_tolerance: 0.10` configurada — **no es
casualidad**: el controlador para al entrar en tolerancia»*. La frase **describe su propia
circularidad y se leyó como una confirmación**. El «error final» de la tabla sale de la pose que
el propio sistema se atribuye, y el controlador para cuando **cree** estar dentro de 10 cm: por
construcción va a dar ~10 cm, esté el robot donde esté.

**Lo que eso puede esconder, medido con cinta el 2026-08-07** (evidencias 83 y 84): con un mapa
rancio, un objetivo `SUCCEEDED` «dentro de tolerancia» tenía al robot a **41,3 cm** de verdad. Y
con el mapa bueno, dos tandas dieron **6,1 y 11,8 cm** reales — una dentro y otra fuera.

```
                          dice el robot   dice la cinta
  2026-07-31 (esta tabla)     9-10 cm      NO SE MIDIÓ
  2026-08-07 mapa rancio      «dentro»       41,3 cm
  2026-08-07 mapa fresco      «dentro»        6,1 cm
  2026-08-08 mapa fresco      «dentro»       11,8 cm
```

🔴 **Y con UNA sola distancia tampoco basta**, aunque sea de cinta: deja al robot en cualquier
punto de una circunferencia. El 2026-08-07 la odometría y AMCL coincidían en distancia (2 cm) y
estaban **a 45 cm la una de la otra**. Hace falta **trilateración desde dos marcas**
(`00_auditoria/evidencia/mediciones_banco/comparar_con_cinta.py`).

✅ **Lo que la tabla SÍ prueba, y no es poco:** que Nav2 acepta un objetivo, planifica, replanifica
y termina `SUCCEEDED` — el mecanismo entero. **Que llegue, no.**

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

### 11.10 ✅ `desired_linear_vel` a 0.40 — el máximo del robot

Subido el 2026-07-31 con las tres condiciones cumplidas y **medidas**: navegó dos veces sin
incidentes a 0.25, el `collision_monitor` está verificado (cap. 12), y **a 0.40 la seguridad
deja más hueco que a 0.25** — 9.0 cm contra 8.0 (cap. 12.4). Ese último dato es el que quita
el miedo a subirlo.

**Lo que había que comprobar no es que llegue, sino que de verdad vaya a 0.40.** Perfil en
`/odom` durante la ida de 1.50 m:

| t | v |
|---|---|
| 0.31 s | 0.057 m/s |
| 0.61 s | 0.357 m/s |
| **0.91 s** | **0.407 m/s** ← meseta |
| 1.52 s | 0.406 m/s |
| 2.00 s | 0.407 m/s |

Máxima 0.431 · percentil 90 **0.412 m/s**. Alcanza la meseta en ~0.9 s, coherente con la rampa
de ~0.5 s ya medida y con `max_linear_accel: 0.8`.

| | Desde | Hasta | Resultado | Error | v (p90) |
|---|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.50, 0.00) | **SUCCEEDED** | **8 cm** | 0.412 m/s |
| vuelta | (1.42, −0.01) | (0.00, 0.00) | **SUCCEEDED** | **8 cm** | 0.409 m/s |

📝 **8 cm las dos veces, contra 9–10 cm a 0.25 m/s: subir la velocidad no empeoró la
precisión.**

**¿Estorbó la capa de seguridad? No.** Cuatro frenados en toda la sesión —2125, 1582, 130 y
65 ms—, ninguno una parada, cero conductas de recuperación y cero fallos de plan. ⚠️ No se ha
aislado **qué** los disparó; se registra el hecho, no una causa inventada.

### 11.11 🔴 `save_map` falla de forma intermitente — y no es el fallo de la Fase 4

```
response: SaveMap_Response(result=255)
[map_saver] Saving map from 'map' topic to '…' file
[map_saver] [ERROR] Failed to spin map subscription
```

🔴 **Es un error distinto del histórico.** En la Fase 4 el 255 venía de `Package
'nav2_map_server' not found` y se arregló instalando `navigation2` (cap. 11.2). Aquí el paquete
está, el `map_saver` arranca, **se configura y se queda sin mapa**. Perseguir la instalación
sería perder el tiempo.

**Causa, deducida de dos números del propio sistema:**

| | |
|---|---|
| `map_update_interval` (`slam_toolbox_atriz.yaml`) | **5.0 s** |
| `save_map_timeout` (por defecto del `map_saver`) | **2.0 s** |

El saver espera 2 s a que llegue un `/map` y `slam_toolbox` lo publica cada 5. **Es una
carrera**: si la llamada cae en el hueco, falla. Explica que funcionara dos veces y fallara la
tercera.

✅ **CONFIRMADO Y ARREGLADO el 2026-07-31.** Se probó lo uno contra lo otro:

| | Resultado |
|---|---|
| servicio de `slam_toolbox`, timeout de 2 s | `result=0`, **`255`**, `0` — falla ~1 de cada 3 |
| `map_saver_cli` con `save_map_timeout:=10.0` | **`Map saved successfully`** |

**El procedimiento bueno para guardar mapas es este, no el servicio:**

```bash
ros2 run nav2_map_server map_saver_cli -f <ruta> --ros-args -p save_map_timeout:=10.0
```

### 11.13 ✅ Rodear un obstáculo — y el aborto que provocó la seguridad

Hasta aquí todo se había probado **contra una pared frontal**: estaba demostrado que el robot
**para**, no que **rodee**.

**El obstáculo, caracterizado con `/scan` antes de mandar ningún objetivo.** El salto en las
distancias es lo que lo aísla de las paredes —un umbral tonto tipo «menos de 1.6 m» etiqueta
también las paredes:

| ángulo | dist | x | y | |
|---|---|---|---|---|
| −3° | 2.54 | +2.54 | −0.13 | abierto |
| **0°…+9°** | **0.75–0.77** | **+0.75** | **0.00…+0.12** | ← obstáculo |
| +12° | 2.07 | +2.03 | +0.43 | abierto |

A **0.75 m**, ~**16 cm de ancho**, escorado 6 cm a la izquierda del eje. El robot mide 18.5 cm:
**bloquea la línea recta**. Holgura a su altura: ~63 cm por la derecha, ~44 por la izquierda.

**La trayectoria** — objetivo a 1.50 m, el mismo que la corrida limpia, para que el obstáculo
sea la única variable:

```
x=+0.00  y=+0.00
x=+0.31  y=-0.12
x=+0.62  y=-0.29
x=+0.79  y=-0.30   ← justo a la altura del obstáculo
x=+0.95  y=-0.21
x=+1.28  y=-0.03
```

Desvío máximo **30 cm por la derecha** —el lado con más hueco— y vuelta al eje. Error final
**8 cm: el mismo que sin obstáculo.**

#### 🔴 En la vuelta, la seguridad hizo abortar a Nav2

```
[controller_server] [ERROR] Failed to make progress
[controller_server] [WARN]  [follow_path] [ActionServer] Aborting handle.
```

El objetivo acabó en `SUCCEEDED` porque el árbol replanificó, pero el aborto es real y en un
paso más estrecho podría no recuperarse.

**Causa:** el `SimpleProgressChecker` de fábrica exige `0.5 m` en `10 s` = **5 cm/s de media**.
El `collision_monitor` había frenado al 40 % (0.16 m/s) y `approach` bajó más la velocidad al
pasar junto al obstáculo.

> **Con una capa de seguridad delante, ir despacio ya no es prueba de estar atascado** — que es
> lo único que ese comprobador debería detectar. Un robot de verdad atascado se mueve 0 m y lo
> sigue disparando igual.

**Arreglo:** `required_movement_radius: 0.25` en `movement_time_allowance: 15.0` → 1.7 cm/s.

#### ✅ Verificado: cuatro navegaciones seguidas tras el cambio

| | Resultado | | Error | Junto al obstáculo |
|---|---|---|---|---|
| ida 1 | **SUCCEEDED** | 5 s | 8 cm | derecha, y=−0.26 |
| vuelta 1 | **SUCCEEDED** | 13 s | 8 cm | derecha, y=−0.32 |
| ida 2 | **SUCCEEDED** | 5 s | 9 cm | derecha, y=−0.26 |
| vuelta 2 | **SUCCEEDED** | 12 s | 8 cm | derecha, y=−0.30 |

`Failed to make progress`: **0** · `Aborting handle`: **0** · conductas de recuperación: **0** ·
`Control loop missed`: **0**.

Y la seguridad **sí trabajó**: 2 `approach` + 5 `slowdown`, **8.1 s** de frenado en total. Las
cuatro rodean por la derecha con el mismo desvío (26–32 cm): es **repetible**, no casualidad.

### 11.14 ⏳ Lo que queda

- ✅ ~~`collision_monitor`~~ (cap. 12) · ~~`desired_linear_vel` a 0.40~~ (11.10) ·
  ~~`save_map`~~ (11.11) · ~~rodear un obstáculo~~ (11.13).
- ⏳ **Un paso estrecho de verdad**, cerca de los 36 cm mínimos del monitor. Aquí había 63 cm
  por la derecha: holgado.
- ⏳ **Un obstáculo que aparezca DURANTE la navegación.** Todo lo probado estaba puesto antes
  de arrancar.
- ⏳ **`min_points: 2`** contra obstáculos finos de verdad (patas de silla). Las dos navegaciones fueron en línea recta por un
  pasillo despejado: se ha probado que **llega**, no que **rodee**.
- **Fase 4c: `map_server` + AMCL** — mapear una vez y localizar en los 16 robots, en lugar de
  16 SLAM simultáneos. El `.pgm`/`.yaml` ya se genera.
- ✅ ~~La inclinación de ~8°, sin causa determinada~~ — **resuelta en el cap. 13**: son **6.9° y
  están en el PITCH** (el roll es ~1°), y no es el robot sino **su acelerómetro descalibrado**
  (`|g|` sale un 3.8 % corto). Desde el 2026-07-31 el driver publica la orientación **plana**.

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

### 12.2b 🔴🔴 Lo que NO ve: los precipicios

`collision_monitor` tiene **una sola fuente**, `/scan` (`collision_monitor.yaml:196-200`), y un
LIDAR **2D horizontal no detecta un vacío a ninguna altura**: el rayo no vuelve, y una lectura
fuera de `range_max` **no es un obstáculo** para `nav2_collision_monitor`.

⚠️ No confundirlo con la limitación del capítulo 12.2, que es la contraria: allí el plano pasa
**por encima** de zócalos y cajas bajas. Aquí el problema no es la altura del plano — **es que un
sensor 2D no tiene con qué ver un hueco.** Subir o bajar el LIDAR no lo arregla.

**Qué significa en la práctica:** un escalón, el borde de una mesa o el hueco de una escalera **no
frenan al robot**. Con estudiantes teleoperando en remoto y sin ver el robot, es un riesgo real.

📌 **Regla de laboratorio, y hoy es la única mitigación:** suelo continuo y cerrado. Nunca sobre
mesas o tarimas, ni cerca de escaleras sin barrera física.

✅ **Se puede tapar sin cámara**, y el hardware ya está caracterizado: el sensor de color mira al
suelo y su canal `clear` va de **181 (negro) a 2288 (blanco)**. Sobre un vacío no habría
superficie que devolviera la luz.
⚠️ **Nunca se ha medido sobre un vacío.** A 0.40 m/s el robot avanza **~6.4 cm cada 160 ms**: hay
que comprobar que `clear` se desploma lo bastante **y a tiempo**. Y exige `color_detection:=true`,
que enciende un LED blanco bajo el chasis (hoy en `false`).

---

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

Con `radius` 0.11 y media longitud de chasis **0.091** ✅ medida, la asíntota era 1.9 cm. Paró a
2.9 cm — exactamente como está escrito que funciona.

**La holgura se consigue inflando el círculo:**

```
hueco ≈ radius − 0.095 + ~1 cm

radius: 0.18  →  asíntota 8.5 cm   ·  MEDIDO 9.3-9.4 a 0.25 m/s · 10.9 a 0.40
radius: 0.15  →  asíntota 5.5 cm   ·  MEDIDO 6.3 a 0.25 m/s · 7.4 y 6.6 a 0.40   ← EL ACTUAL
```

🔄 **Desde el 2026-08-09 el valor es `0.15`** (evidencia 94). Los dos están medidos contra pared, y
el perfil del recorte es lineal en la distancia al círculo: `mando ≈ 0,0125 × (d_LIDAR − radius)`.

📝 La holgura **depende de la dirección**, porque el robot no es un círculo: de frente
`0.18 − 0.091 = 8.9 cm`, de costado `0.18 − 0.1085 = 7.2 cm`, y en esquina
`0.18 − 0.142 = 3.8 cm`, que es el caso peor.

### 12.4 ✅ Medido — y el hueco no empeora con la velocidad

✅ **Re-medido con las cotas buenas** el 2026-07-31, después de corregir el URDF:

| velocidad | n | **hueco real medido** | recalculado | dif |
|---|---|---|---|---|
| 0.25 m/s | 1 | **9.9 cm** | 9.8 | +0.1 |
| 0.40 m/s | 2 | **10.6 / 10.7 cm** | 10.8 | −0.2 |

Las diferencias son de **1–2 mm**, por debajo de la resolución útil de la medida: el recálculo
era correcto. Y **repite**: las dos corridas a 0.40 dan 10.6 y 10.7.

**El modelo, afinado:**

```
asíntota = radius − media longitud = 0.18 − 0.091 = 8.9 cm
a 0.25 m/s  →  9.9 cm    margen +1.0 cm
a 0.40 m/s  → 10.65 cm   margen +1.8 cm
```

📝 **El margen crece con la velocidad.** Confirma lo ya visto: `approach` empieza a frenar
antes cuanto más rápido va, así que la holgura **no se degrada al acelerar — mejora**.

📝 Cambiar `laser_z` (0.1745 → 0.155) y `wheel_radius` (0.032 → 0.035) **no alteró el
comportamiento**, como se preveía: son traslaciones en Z y el monitor trabaja en el plano. Los
números lo confirman.

📝 A 0.40 m/s (el máximo del robot) para **más lejos**, no más cerca: el controlador empieza a
frenar antes cuanto mayor es la velocidad.

### 12.5 🔴 SÍ queda atrapado — el 2026-08-09 lo desmintió

> 🔴🔴 **AVISO: EL TÍTULO Y LA TABLA DE ESTA SECCIÓN ESTÁN EN DISPUTA.**
> El 2026-08-09 (evidencia 93) se midió lo contrario, con el usuario mirando el robot:
>
> ```
> pared DETRÁS a 16,8 cm, 188 cm libres delante, mandos por /cmd_vel_raw
>   AVANZAR alejándose de la pared  ->  0.0 cm    monitor: APROXIMACION
>   GIRAR en el sitio               ->  0.0 °
>   RETROCEDER hacia la pared       ->  0.0 cm
> ```
>
> **Inmovilización total: ni siquiera puede alejarse.** Y girando **no rozaría nada**: con el
> monitor puenteado dio **359,6° y 358,8° de 360** en 12,6 s —los mismos que en campo abierto— sin
> tocar la pared. El radio circunscrito del robot es **14,06 cm** —18 × 21,6 cm medidos con cinta, LIDAR centrado— contra un círculo de 18.
>
> ✅ **Y el 2026-08-09 por la noche se barrieron las CUATRO direcciones, 24 estaciones colocadas a
> mano de 2 en 2 cm (evidencia 94): el umbral es EL MISMO en las cuatro.** Desde `base_footprint`,
> la intersección de las cuatro horquillas es **(17,9 · 19,6) cm**, que contiene los 18,0 del
> círculo. **24 de 24 estaciones todo-o-nada.**
>
> ```
> DETRAS     bloqueado hasta 17,8  ·  libre desde 19,6
> DELANTE            "     16,1  ·      "      19,8
> IZQUIERDA          "     17,9  ·      "      19,7
> DERECHA            "     17,9  ·      "      19,7
> ```
>
> 🔴 **Así que NO hay dependencia de la dirección, y la tabla de abajo no se reproduce.** Su caso
> «dentro de un paso de 40 cm → retrocedió 58 cm» tenía el obstáculo **al lado a 17 cm**; aquí, a la
> izquierda y a 17,9, el robot **está bloqueado**. Lo que explica la discrepancia es probablemente
> **desde dónde se midieron aquellas distancias** —borde o LIDAR, y el LIDAR va 5 mm por detrás del
> centro—, pero eso ya no se puede reconstruir. **Los números de abajo se conservan como registro,
> no como comportamiento esperable.**
>
> 🔎 **El experimento que lo discrimina:** repetir las tres órdenes con la pared **delante** y con
> la pared **al lado**, a la misma distancia medida desde el LIDAR. Hasta entonces, lo que hay que
> dar por bueno en operación es lo peor: **con algo a menos de 20 cm el robot puede quedar muerto.**

**Lo que decía esta sección, conservado porque sus medidas siguen siendo datos:**



Un polígono `stop` fijo para **cualquier** movimiento mientras haya algo dentro. Un robot
pegado a una pared se congela: ni retrocede ni gira. En un laboratorio **remoto** no hay nadie
que lo levante — ese robot queda inservible hasta que alguien vaya al edificio.

Por eso los dos polígonos son **`approach` y `slowdown`, nunca `stop`**. Verificado dos veces:

| Situación | Resultado |
|---|---|
| pegado a la pared, 2.9 cm | retrocedió **196 cm** ✅ |
| a 10.65 cm | retrocedió 8.6 cm + giró en el sitio ✅ |
| dentro de un paso de 40 cm (12.10) | retrocedió **58 cm** ✅ |

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

El plano de barrido del X2 está a **15.5 cm del suelo** ✅ medido el 2026-07-31 con una regla,
del suelo al centro del disco giratorio.

🔴 **Corregido:** hasta esa fecha aquí ponía **17.45 cm**, que era una suma **derivada** con la
altura del RVR sacada de su ficha (11.4 cm cuando son **7.0**). El robot **ve 2 cm más abajo**
de lo que estaba documentado.

> **Todo lo que esté por debajo de 15.5 cm es invisible para el `collision_monitor`, y el
> robot lo embestirá sin frenar.** Un zócalo bajo, una regleta, un pie de mesa que se ensancha
> abajo, un cable grueso.

No es un fallo de configuración: es lo que un LIDAR 2D puede ver. **Tiene que ir en las
instrucciones a los estudiantes.**

🔴 **Y hay una SEGUNDA zona ciega que este manual negaba con sus propios números.** Decía:

> *«el X2 tiene `range_min: 0.1` y va montado en el centro (`laser_x: 0.0`), así que su punto ciego
> de 10 cm cae dentro del chasis (media longitud 0.091 m, media anchura 0.1085). No hay zona muerta
> alrededor del robot.»*

**Con esos mismos números no sale la conclusión**: `0.100 > 0.091`, así que el punto ciego
**sobresale** por delante y por detrás. Medido el 2026-08-09 (evidencia 93) con el robot **tocando**
la pared: se descartaron **10 277 rayos traseros** por debajo de `range_min` y sólo sobrevivió uno
oblicuo, recortado en 10,02 cm.

```
delante/detrás   0.100 − 0.090 ≈ 1 cm CIEGO, fuera del chasis
costados         0.100 − 0.108 = dentro del chasis, ahí sí está cubierto
```

⚠️ **Ningún polígono puede cubrir ese centímetro**: no es cuestión de ajustar `radius`, es que el
sensor no entrega el dato. Y `laser_x` no es 0.0 sino **−0.005** (URDF, medido el 2026-08-02).

✅ **Geometría medida con cinta desde el eje del LIDAR el 2026-08-09:** 9,0 cm detrás · 10,8 a cada
costado, validado contra el propio LIDAR con **2 mm** de error (12,20 leídos contra 12,00 predichos,
n=8268 rayos). ⏳ **El borde delantero queda en conflicto:** la cinta da 9,0 y el URDF 10,0
(`base_length 0.190` con `laser_x −0.005`). **NO VERIFICADO** — se cierra repitiendo la misma medida
con el robot mirando a la pared.

📝 Y el desglose completo de la altura, medido: `suelo → tapa del RVR 7.0` + `tapa → base del
LIDAR 4.6` + `base → centro del disco 3.9` = **15.5 cm**. Cierra contra la otra medida: los
16.5 cm hasta el extremo superior son `7.0 + 4.6 + 5.0` (alto del LIDAR).

### 12.9 Verificar tras arrancar

```bash
ros2 lifecycle get /collision_monitor   # active [3] ← si no, NO FILTRA NADA
ros2 topic info /cmd_vel --verbose      # Publisher count: 1, y es collision_monitor
```

✅ **Ya hecho lo importante:** las cotas están medidas con cinta
([`MEDIDAS_ROBOT.md`](../03_operacion/MEDIDAS_ROBOT.md), solo falta `imu_z`, que exige abrir el
robot) y **las paradas contra pared se re-midieron** con las cotas buenas: **9.9 cm** a 0.25 m/s
y **10.6 / 10.7 cm** a 0.40 (12.4). Ya no son recálculos.

⏳ **Lo que sigue abierto:** el barrido de `radius` contra un mismo paso, y ajustar
`min_points: 2` contra obstáculos finos de verdad (patas de silla).

✅ `desired_linear_vel` ya está en **0.40** (cap. 11.10), y navegando a esa velocidad la
seguridad solo se activó cuatro veces, ninguna como parada.

---

### 12.10 🔴 No cruza un paso de 40 cm — y las cotas del robot estaban mal

**El resultado:** con `radius: 0.18` el robot **entró en la boca de un paso de 40 cm y se
quedó bloqueado**. Medido con `/scan` acumulado en esa posición:

```
ang −84°…−99°   d=0.23   ← objeto derecho, a 22 cm del centro
ang +72°…+87°   d=0.18   ← objeto izquierdo, a 17 cm del centro
al frente, a menos de 60 cm: NADA
```

No tocaba nada (media anchura 11 cm contra 17 y 22 de holgura) y tenía el camino **despejado
delante**. Lo paró el monitor porque su círculo mide 18 cm y el borde estaba a 17: **le sobraba
1 cm**. ✅ Y **pudo salir marcha atrás** (58 cm) — `approach` en vez de `stop`, otra vez.

📝 **Nav2 no llegó a intentarlo**: con el paso abierto por los lados (65 y 63 cm), el
planificador se fue por la ruta ancha. Es lo correcto. La prueba que responde de verdad es
conducir recto por `/cmd_vel_raw`, sin planificador que pueda escaquearse.

**No es un fallo: es el compromiso, ahora medido.** El `radius` fija dos cosas en sentidos
opuestos:

| `radius` | para a | pasillo mínimo |
|---|---|---|
| 0.14 | 5 cm | 28 cm |
| 0.16 | 7 cm | 32 cm |
| **0.18** | **9 cm** | **36 cm** ← el actual |
| 0.20 | 11 cm | 40 cm |

Para 16 robots en un laboratorio **remoto donde nadie puede levantarlos**, parar a 9–11 cm de
las paredes vale más que cruzar huecos de 40 cm. Pero es una **decisión de laboratorio**, no
una verdad técnica.

#### 🔴 Y por el camino salió que el URDF tenía las cotas cruzadas

| | medido (usuario) | URDF (ficha) |
|---|---|---|
| frente-atrás | **18.2 cm** | 21.8 cm |
| lado-lado | **21.7 cm** | 18.5 cm |

Modelaba un robot **más largo que ancho** siendo al revés. Dos consecuencias:

1. **Los huecos publicados salían 2 cm cortos** (se calculaban con media longitud 0.109 en vez
   de 0.091). Corregidos en 12.4. El modelo `hueco ≈ radius − media longitud + 1 cm` **no se
   cae**, solo cambia la constante.
2. 🔴 **`robot_radius: 0.11` estaba mal**, y esto sí es un error real. Lo llamé «radio
   circunscrito» y es aritmética mal hecha: el circunscrito es `√(0.09² + 0.11²) = 0.142` con
   las cotas medidas, y **0.143 incluso con las del URDF**. Con cualquiera de los dos, 0.11 se
   queda corto — el planificador puede trazar rutas donde una **esquina** roza, **sin dar
   ningún error**. Lo tapaba el `collision_monitor` con sus 0.18, que es probablemente por qué
   `approach` saltaba al rodear (11.13). **Corregido a 0.145.**

📝 El URDF solo cambia la caja de colisión y la inercia: las ruedas usan `wheel_separation`,
independiente, así que **ningún frame TF se mueve** y la odometría no se toca.

✅ **Medido todo el mismo día**, incluidos `laser_z` y la nivelación del LIDAR:
[`03_operacion/MEDIDAS_ROBOT.md`](../03_operacion/MEDIDAS_ROBOT.md). **No queda ninguna cota
medible sin medir**, y el modelo cierra por dos caminos: la caja del chasis va de 0.000 a
0.070 m (= `base_height`) y el láser a 0.155 m (= lo medido). Dos hallazgos salieron de ahí: el
plano de barrido está **2 cm más bajo** (12.8) y **la inclinación de ~8° no existe** (cap. 13).

#### 📝 Un fallo de medición que vale la pena conocer

Los dos objetos daban **solo 2 y 3 puntos** de LIDAR cada uno: a 0.68 m el X2 tira un rayo cada
1.7 cm. Con **un solo barrido** pueden desaparecer y el detector de huecos deja de ver el paso.
Los escaneos que funcionaron **acumulaban 6–8 s** y tomaban la mediana por sector.

→ Para geometría fina, **acumula barridos**. Y es un aviso sobre `min_points: 2`: con objetos
así de finos está justo en el límite.


## Capítulo 13 — La inclinación del RVR: es el acelerómetro, no el robot

✅ **Resuelto el 2026-07-31**, tras **dos conclusiones mías retiradas** por el camino. Evidencia:
`00_auditoria/evidencia_24_04/21_deriva_roll_y_fallo_largo.txt`.

### 13.1 La cifra correcta, y dónde vive

```
roll  +1.10°      pitch  +6.74°      TOTAL  6.83–6.96°
                   ^^^^^
```

🔴 **La documentación decía «~8° de ROLL». Son ~6.9° y están casi todos en el PITCH.**

⚠️ **Y no son fijos: roll y pitch se reparten según el rumbo.** Medido — tras dos giros el roll
pasó de +1.10° a +0.15° mientras el pitch subía a +6.87°. **Lo único estable es el módulo.**
Cualquier comprobación que mire solo el roll da un falso negativo (13.5).

### 13.2 🔴 Dos conclusiones retiradas — y por qué ninguna valía

**Retirada 1: «la inclinación no existe, el LIDAR está nivelado en los cuatro puntos».**
La regla mide alturas **desde el suelo**. Un robot plano sobre un suelo inclinado da las cuatro
medidas iguales. Esa medida no podía distinguir «nivelado respecto al chasis» de «horizontal
respecto a la gravedad».

**Retirada 2: «es física: el pitch cambia de signo al girar 180°, luego el suelo tiene 12 % de
pendiente».** El cambio de signo solo prueba que el error está en el **marco del mundo**, y eso
lo producen **dos** causas: un suelo inclinado **o** una referencia de gravedad torcida.
Presenté como resuelto un caso con dos explicaciones — justo lo que la regla nº4 prohíbe.

### 13.3 ✅ Lo que sí lo zanja

**a) El suelo está plano.** Medido con nivel en cuatro puntos: 0.22°, 0.29°, 0.30°, 0.40°.

**b) El acelerómetro crudo NO gira con el robot.** Es el discriminador limpio porque no pasa
por ninguna fusión:

| | ANTES | DESPUÉS del giro de 177.8° | |
|---|---|---|---|
| pitch | +6.72° | **−6.99°** | cambia de signo |
| `accel.x` | −1.091 | **−1.158** | **NO cambia** |
| `accel.y` | −0.199 | **−0.197** | **NO cambia** |

Un error **fijo en el marco del robot** + suelo plano = **el sensor está descalibrado**, no el
robot inclinado.

**c) El módulo lo confirma:** `|g| = 9.435` contra 9.807 — **3.8 % corto**. Un acelerómetro que
no acierta el módulo tampoco acierta la dirección.

**d) No es la referencia de arranque.** Se apagó el RVR, se dejó plano en el suelo y se encendió
allí: la inclinación siguió igual (6.83° contra 6.83°).

### 13.4 ⏳ Lo que queda sin explicar

**Por qué el cuaternión fusionado gira con el rumbo mientras el sesgo del acelerómetro no.** Una
traza de 90 s tras el giro descarta que sea un transitorio: el pitch se queda clavado en
−6.9/−7.0. Es una rareza de la fusión del RVR y se deja como pregunta abierta, **sin inventarle
mecanismo**.

**Consecuencia práctica:** el driver publica en `/odom` y en TF una inclinación espuria que
**además cambia con el rumbo**. Una inclinación dependiente de la dirección es peor que una
constante: degrada el emparejado de forma direccional.

### 13.5 El interruptor, y el falso positivo que provocó

✅ **Por defecto `false` desde el 2026-07-31**: el driver publica la orientación **plana**.
Verificado sobre el sistema instalado: `/odom` da `roll +0.00° pitch +0.00°`.

```bash
# recuperar el comportamiento anterior, si alguna vez hace falta:
ros2 launch atriz_rvr_bringup robot.launch.py publicar_inclinacion:=true
```

🔴 **La razón NO es el efecto en la deriva**, que se midió y salió de ~1 cm sin significación
(9.12d), y **se decidió no perseguirlo**: ~62 corridas y 5 h de robot para un efecto de 1 cm
sobre una tolerancia de objetivo de 10.

**La razón es que la inclinación no existe** (13.3): suelo plano medido con nivel, error del
acelerómetro fijo en el marco del robot, y `|g|` un 3.8 % corto. **Publicar 6.9° de inclinación
falsa en `odom → base_footprint` es publicar un dato que sabemos incorrecto**, se pueda medir
su efecto o no. REP-105 espera ahí la pose del robot.

⚠️ Si algún día un robot trabaja en una superficie inclinada de verdad, habría que poner `true`
**y calibrar antes el acelerómetro** — el que hay no acierta ni el módulo.

🔴 El experimento de 13.6 **abortó a los 2 minutos** con un falso positivo: su guardián
comprobaba solo el **roll**, que en ese momento valía +0.11° porque la inclinación estaba
entera en el pitch. Arreglado para mirar `hypot(roll, pitch)`.

✅ Que abortara es lo correcto: mejor un falso positivo a los 2 min que 45 min de datos con el
interruptor sin efecto.

### 13.6 ⚠️ El experimento NO responde la pregunta

12 corridas, 3 bloques de cada condición **alternando**, `slam_toolbox` reiniciado de cero en
cada una:

| | | mediana | σ | valores |
|---|---|---|---|---|
| CORTA (158 cm) | CON roll | 2.10 cm | 0.95 | 2.1, 1.0, 2.9 |
| | SIN roll | 1.20 cm | 0.64 | 2.2, 1.0, 1.2 |
| LARGA (233 cm) | CON roll | 1.10 cm | 8.66 | 1.1, **16.0**, 0.9 |
| | SIN roll | 12.00 cm | 29.08 | **56.1**, **12.0**, 1.2 |

⚠️ **No se puede concluir nada sobre el roll.** El efecto buscado era de ~1 cm y apareció un
fallo de 6–56 cm que lo entierra.

**Repetido una hora después** (cap. 9.12b), la única comparación sin fallos dentro fue LARGA:
**2.70 contra 2.50 cm**, una diferencia de 0.20 cm con σ 1.19 — **compatible con cero**. Pero
con n=3 por rama y un efecto buscado de ~1 cm, eso **no permite decir que el roll no afecte**:
solo que **no se ve**.

🔴 Y no se verá hasta arreglar lo del 9.12b: mientras el robot derive de su sitio entre
corridas, las repeticiones no son repeticiones.

📝 **El diseño alternado sí cumplió su función:** deja ver que los fallos **no** se reparten por
condición (1 CON roll, 2 SIN roll). Con 6 y 6 en bloque, los tres habrían caído en una sola
condición y habrían parecido su causa.

### 13.7 ✅ Consumo de batería — un dato que el proyecto no tenía

Medido de paso: **92 % → 85 %** en los 6 bloques, mediana **2 puntos** por bloque de 2.7 min de
movimiento → **~0.74 %/min**, o del orden de **2 horas de conducción** por carga.

⚠️ Primera estimación, no una medida fina: `/battery_state` llega en pasos de 1 %, los bloques
son cortos, y el ritmo cayó a lo largo del experimento (1.12 → 0.74 → 0.37 %/min), que es lo
típico de una curva de descarga no lineal.

---

## Capítulo 14 — `map_server` + AMCL: localizar sobre un mapa (Fase 4c)

✅ **VERIFICADO el 2026-07-31**: el ciclo completo funciona — mapear, guardar, localizar y
**navegar** sobre el mapa, sin SLAM. Evidencia: `00_auditoria/evidencia_24_04/24_fase4c_amcl.txt`.

### 14.1 Por qué esta fase — y por qué NO es por CPU

Con SLAM, cada uno de los 16 robots construye **su propio mapa**: 16 mapas del mismo
laboratorio, cada uno con su origen, y **ninguna coordenada común**. Con AMCL se mapea una vez,
el `.pgm` se reparte con la imagen dorada, y los 16 se localizan sobre él.

🔴 **El argumento no es la CPU, y eso salió midiendo.** En el YAML había escrito «se espera
menos, pero se mide, no se supone». Menos mal:

| | CPU | RAM |
|---|---|---|
| `slam_toolbox` | **4.8 %** | 49.1 MB |
| `amcl` + `map_server` | **8.8 %** | 85.9 MB |

**AMCL cuesta casi el doble.** El argumento es el **marco compartido**: es lo que permite que la
web diga «ve a la mesa 3» y que los 16 robots entiendan lo mismo.

⚠️ **Nota de método, y afecta a números ya publicados:** `ps -o %cpu` da el **promedio desde que
arrancó el proceso**, no el instantáneo, así que infla lo recién lanzado. Las cifras de arriba
se midieron muestreando `/proc` dos veces con 20 s de diferencia. Las cifras de CPU anteriores
del proyecto se tomaron con `ps`; la de `slam_toolbox` vuelve a salir 4.8 % con el método bueno,
así que el orden de magnitud aguanta — pero conviene saberlo.

### 14.2 ✅ Las dos salvaguardas del launch

🔴🔴 **AMCL y `slam_toolbox` publican los dos `map → odom`.** Juntos parten el árbol TF **sin dar
ningún error**: TF se queda con el último mensaje y la pose salta entre las dos estimaciones. Es
el fallo que costó la Fase 4 (cap. 9.4). Por eso el launch **se niega a arrancar**:

```
🔴 slam_toolbox ESTÁ CORRIENDO. localizacion.launch.py no arranca.
🔴 el mapa no existe: /no/existe.yaml
   Hazlo primero con slam.launch.py y guárdalo con el método verificado: […]
```

Las dos probadas. 📝 La comprobación usa `ps -eo comm`, **no `pgrep -f`** — el patrón de `-f`
casa con la propia línea de comando y en este proyecto eso ya ha matado la terminal dos veces.

### 14.3 ✅ El ciclo completo

```
a) MAPEAR con slam_toolbox            celdas 486 → 2774
b) GUARDAR con map_saver_cli          mapa_amcl.pgm, 5989 bytes
c) PARAR SLAM                         `map` deja de existir  ✅ punto de partida limpio
d) LOCALIZAR                          map_server y amcl active [3]
                                      map → odom: (−0.004, 0.011), yaw +0.65°
e) ¿SIGUE LA POSE?  avance de 60 cm   ODOM 61.8 cm · AMCL 61.9 cm · dif 0.1 cm  ✅
f) NAVEGAR con Nav2 sobre el mapa     SUCCEEDED, error 8 cm
                                      ODOM 73.4 cm · AMCL 72.3 cm · dif 1.1 cm  ✅
```

📝 **`/amcl_pose` no llega con el robot quieto, y no es un fallo:** AMCL solo actualiza tras
moverse `update_min_d` (0.15 m). Perseguirlo como si fuera un error cuesta tiempo.

### 14.4 ⚠️ Lo que NO está resuelto

🔴 **La incertidumbre de rumbo crece:** σyaw **6.7°** tras avanzar 60 cm, **18.0°** tras navegar
80 cm. Es mucho. La sospecha es que el mapa es pequeño y con pocos rasgos distintivos —una sala
casi rectangular da poca información angular— pero **no está comprobado**.

🔴 **La pose inicial.** `set_initial_pose: true` con (0,0,0) hace que AMCL crea que el robot está
en el origen del mapa. Si no lo está, empieza equivocado y **puede no recuperarse**: en una sala
con simetrías, casi seguro. ⏳ **Para la flota, la pose inicial tiene que venir por robot** — del
`robot_id.txt` o de un argumento del launch. Sin resolver.

⚠️ **Y estas pruebas no comprobaron la corrección ABSOLUTA de la pose**, solo su **consistencia**
con la odometría (0.1 y 1.1 cm). De hecho AMCL arrancó creyéndose en el origen con el robot
desplazado ~60 cm de él. Que la navegación saliera bien sugiere que convergió, pero para
afirmarlo haría falta una referencia externa — una marca en el suelo medida con cinta.

---

## Capítulo 15 — La parada de emergencia: tres fallos silenciosos

✅ **Arreglada y verificada el 2026-07-31.** Evidencia:
`00_auditoria/evidencia_24_04/25_parada_emergencia.txt`.

### 15.1 Este botón ha fallado tres veces, por tres causas distintas

Y las tres daban **`200 OK` en la web y cero efecto en el robot**.

| | Causa | Cuándo |
|---|---|---|
| 1ª | **nombre de topic**: la web publicaba en `/rvr/emergency_stop`, el driver escuchaba `is_emergency_stop` | ROS 1, auditoría 2026-07-29 |
| 2ª | **namespace**: al portar se arregló el nombre y se coló el prefijo `/rvr/` | ROS 2, 2026-07-31 |
| 3ª | **QoS incompatible** | ROS 2, 2026-07-31 |

**La segunda.** El driver se suscribía a `emergency_stop` e `is_emergency_stop`, nombres
**relativos** que con el namespace vacío —el valor por defecto— resuelven a `/emergency_stop` y
`/is_emergency_stop`:

```
$ ros2 topic list | grep -i emergency
  /emergency_stop
  /is_emergency_stop
$ ros2 topic info /rvr/emergency_stop
  Unknown topic '/rvr/emergency_stop'      ← el que usa la web
```

📝 Y el `TRASPASO.md` decía «el topic ya existe en el driver ROS 2». Existe **un** topic; no el
que la web usa.

**La tercera, y solo aparece PROBÁNDOLO.** Con el nombre ya correcto:

```
New publisher discovered on topic '/rvr/emergency_stop', offering incompatible QoS.
No messages will be received from it. Last incompatible policy: DURABILITY
```

El driver se suscribía con `RELIABLE + TRANSIENT_LOCAL`, justificado con «así un suscriptor que
llegue tarde recibe el último estado». **Ese razonamiento es del publicador.**

> 🔴 **En el suscriptor, `TRANSIENT_LOCAL` solo RESTRINGE**: exige que el publicador también lo
> sea. Y ninguno lo es por defecto — ni `ros2 topic pub`, ni **rosbridge**, que es por donde
> hablará la web. `VOLATILE` en el suscriptor empareja con **todo**: es estrictamente más
> compatible.

### 15.2 ✅ El arreglo y su verificación

1. El driver escucha **también `/rvr/emergency_stop`**, en absoluto.
2. El QoS pasa de `RELIABLE + TRANSIENT_LOCAL` a **`RELIABLE + VOLATILE`**.

Disparando los tres nombres uno a uno:

```
/rvr/emergency_stop    -> PARADA DE EMERGENCIA ✅
/emergency_stop        -> PARADA DE EMERGENCIA ✅
/is_emergency_stop     -> PARADA DE EMERGENCIA ✅

avisos de "incompatible QoS": 0 · paradas: 3 · liberaciones: 3
```

⚠️ **Tres suscripciones para una función es feo, y está hecho a propósito**: en un botón de
emergencia el modo de fallo es «no llega el mensaje», y ha fallado dos veces exactamente por
eso. La Fase 5 unifica a uno — **no antes** de que el nuevo esté probado de extremo a extremo.

📝 **La lección de método:** las causas 2 y 3 **solo aparecen publicando de verdad**. Leer el
código daba el nombre pero no el namespace resuelto, y no decía nada del QoS. `ros2 topic list`
daba el namespace pero no el QoS. Hizo falta **publicar y mirar el log del driver**.

### 15.3 Lo que faltaba, y ya no falta

> 🔴 **Esta sección afirmó hasta el 2026-08-01 que «la parada no corta lo que venga de Nav2» y
> que estaba «sin comprobar». Las dos cosas eran falsas**, y llevaban serlo desde el 31 de julio.
> Es la peor clase de deriva documental que puede tener este proyecto: **una función de seguridad
> descrita como rota cuando funciona**. Quien lo leyera creería que el robot no se para.

✅ **La parada SÍ corta lo que venga de Nav2, y está verificado con control** (15.4): el nodo
`cancelar_nav2` manda un `CANCEL_ALL` al `NavigateToPose`. Con él, el objetivo queda `CANCELED` y
el robot recorre **0.0 cm** al liberar la parada; sin él, el objetivo sigue **ACTIVO** y el robot
**arrancó solo 34.7 cm**.

📝 Va en `nav2.launch.py` y **no** en el driver, a propósito: el driver tiene que funcionar aunque
Nav2 no esté.

✅ **Y el nombre del topic ya está decidido** (2026-08-01): el oficial para la web es
**`/emergency_stop`**, con QoS **RELIABLE + VOLATILE**.

⚠️ **Los tres nombres se quedan, y eso no es indecisión.** Con un botón de emergencia el modo de
fallo que importa es **«el mensaje no llega»**. Escuchar de más no cuesta nada; escuchar de menos
ya ha fallado **cuatro veces**. `ARQUITECTURA.md`.

### 15.4 🔴 La cuarta causa: liberar la parada devolvía el robot a navegar

En la lista de pendientes ponía *«la parada de emergencia no cancela las acciones de Nav2, solo
para los motores»*. **Ese enunciado era falso**, y al mirar el código apareció algo peor.

**Lo que sí funciona:** `_cb_parada_emergencia` pone una bandera, y `_cb_cmd_vel` empieza con
`if self._parada_emergencia: return`. Con Nav2 publicando a 10 Hz el robot **se queda quieto
igualmente**.

**El agujero está al liberar.** `/release_emergency_stop` solo baja la bandera:

```python
def _srv_liberar_parada(self, _req, resp):
    self._parada_emergencia = False
```

Y mientras tanto el objetivo de Nav2 **sigue vivo**, el `controller_server` nunca dejó de
publicar, y no aborta enseguida porque el `SimpleProgressChecker` está relajado a 0.25 m en 15 s
a propósito (cap. 11.13). → **En el instante en que la bandera baja, el robot arranca solo.** Que
es lo contrario de lo que debe hacer una parada de emergencia: soltarla tiene que dejar el robot
quieto, no devolverlo a lo que estaba haciendo.

**El arreglo:** un nodo aparte, `cancelar_nav2`, que arranca `nav2.launch.py`. Escucha los tres
nombres de la parada y llama a `_action/cancel_goal` con un `CancelGoal.Request` **vacío** — que
en `action_msgs` no significa «no cancelar nada», sino **CANCEL_ALL**. Así no hay que seguir la
pista de handles que lanzó otro proceso (la web, RViz2, un script).

Va **aparte y no dentro del driver** porque el driver tiene que funcionar sin Nav2: es la misma
razón por la que SLAM y la navegación viven en launches separados.

✅ **Verificado sin mover el robot:** el nodo recibe por `/rvr/emergency_stop` —el nombre
absoluto que usa la web y que fallaba en ROS 1— y sin Nav2 degrada bien, avisando en vez de
bloquear la parada. Eso cubre las causas 2 y 3 de este mismo capítulo.

✅ **Y VERIFICADO CON NAV2 NAVEGANDO, con control**, que es lo que lo hace concluyente:

| | objetivo tras la parada | movimiento al liberar |
|---|---|---|
| **con** `cancelar_nav2` | **CANCELED** | **0.0 cm** ✅ |
| **sin** él (control) | sigue **ACTIVO** | **34.7 cm** 🔴 arrancó solo |

🔴 **El control es la mitad que importa.** Sin él, «el robot se quedó quieto» no demuestra que lo
consiga `cancelar_nav2`: demuestra que se quedó quieto. Con él quedan cuatro medidas de acuerdo,
en dos parejas opuestas — y el estado del objetivo lo da el propio action server, no una
inferencia.

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_parada_nav2.py
```

Mide **desplazamiento**, no velocidad: un robot que arranca y frena puede dar velocidad media ~0
y haberse movido 20 cm — el error que ya se cometió midiendo el watchdog. Y deja la parada
**activa** al terminar: liberarla tiene que ser un acto explícito.

Evidencia: `00_auditoria/evidencia_24_04/31_parada_cancela_nav2.txt`.

---

## Capítulo 16 — Los servicios del driver, y el sensor de color que nunca funcionó

✅ **De 1 servicio a 18, todos probados contra el robot** (2026-07-31). Evidencia:
`00_auditoria/evidencia_24_04/26_servicios_driver.txt`.

### 16.1 El orden de portado: primero lo que no mueve nada

No se siguió el orden del `.srv`, sino el del riesgo — así se prueba en banco sin espacio:

| | Servicios | Verificación |
|---|---|---|
| **lecturas** | `get_encoders`, `get_system_info`, `get_control_state`, `get_rgbc_sensor_values` | app **9.1.462**, bootloader **9.1.167**, MAC, SKU, Nordic y ST |
| **luces** | `set_led_rgb`, `set_multiple_leds`, `set_leds`, `trigger_led_event` | y sus caminos de error |
| **IR** | `send_infrared_message`, `set_ir_mode`, `set_ir_evading` | ⚠️ el último **sí puede mover el robot** |
| **config** | `set_drive_parameters`, `set_pos_and_yaw` | |
| **movimiento** | `move_timed`, `raw_motors`, `move_to_pose`, `move_to_pos_and_yaw` | ver abajo |

```
move_timed  2 s a 0.15 m/s   ->  30.3 cm medidos contra 30    (101 %)
raw_motors  reversa 25 %     ->  30.7 cm, para al mandar modo 0
move_to_pos_and_yaw 0.20 m   ->  19.5 cm medidos              ( 97 %)
```

✅ **Y la parada de emergencia los bloquea**: con ella activa, `raw_motors` devuelve
`success=False` y el robot se desplaza **0.0 cm**.

### 16.2 🔴🔴 `/color` llevaba publicando `[0,0,0]` desde siempre

Lo destapó una pregunta del usuario: *«hasta donde sabía, el sensor de color no funcionaba sin
encender su luz»*.

**a) ¿Funciona sin luz? No.** Medido con el SDK directo:

| | R | G | B | **Claro** |
|---|---|---|---|---|
| sin luz, sin haber encendido nunca | 1 | 0 | 1 | **4** |
| con luz (0.0 / 0.3 / 1.0 / 2.0 s) | 241 | 420 | 160 | **741** |
| sin luz, ya apagada | 0 | 0 | 1 | **3** |

**185 veces más** en el canal claro. Sin su luz el sensor da **ruido, no señal**. La tercera
tanda no sobra: descarta la otra explicación posible —«necesita que le hayan llamado alguna
vez»—. Y **no hay que esperar** tras encender: 0.0 s da lo mismo que 2.0.

**b) El driver nunca encendía la luz.** `/color` existía, publicaba a 16 Hz, y **siempre
`[0,0,0]`** — 294 mensajes seguidos. El topic estaba en la lista de «verificado» desde la
Fase 2. Un fallo silencioso más: el topic existe, el ritmo es correcto, y el dato es basura.

**c) ✅ Y SÍ se puede encender bajo demanda.** Corregido el **2026-08-06**. Aquí ponía, desde el
2026-07-31, que con el streaming ya configurado `enable_color_detection` **no hacía nada** — 481
mensajes de `/color` todos ceros. **Era falso, y la medida no lo probaba.**

El servicio que se probó hacía `enable(True) → leer → enable(False)` **dentro de la misma
llamada**, y 481 mensajes a 12,7 Hz son ~38 s: casi todos POSTERIORES al apagado. La medida no
distinguía «el enable no hace nada» de «funcionó 200 ms y la propia llamada lo apagó».

Remedido con el streaming corriendo a 250 ms, reproduciendo la secuencia de ROS 1
(`mediciones_banco/probar_color_stream_caliente.py`, evidencia 76):

| fase | `/color` no-cero | canal claro |
|---|---|---|
| LED nunca encendido | 0 / 24 | 1 |
| tras `enable(True)` **en caliente** | **24 / 24** | **1321** |
| 6 s más tarde | 23 / 23 | 1321 |
| tras `enable(False)` | 0 / 24 | 1 |

Dos rutas independientes se mueven a la vez y vuelven a la línea base; el LED blanco se vio
encenderse. **1321×.**

→ Por eso existe el servicio **`enable_color`** (`std_srvs/SetBool`, `rvr_driver_node.py`), que
es el que sostiene el botón «sesión de medición» de la web. Lleva un `sleep(0.1)` dentro, copiado
de ROS 1 (`Atriz_rvr_node.py:341`): sin él, quien lea justo al volver el servicio se lleva la
muestra anterior —oscuridad— con `success=True`, que es **exactamente** el fallo de la primera
versión.

🔴 **La lección:** una medida que da el mismo resultado tanto si la hipótesis es cierta como si es
falsa no es una medida. Esta bloqueó una función seis días desde la propia documentación, y no la
destapó ninguna revisión de código: la destapó el usuario al recordar el ciclo funcionando en
ROS 1 — donde el servicio `enable_color` hacía justo esto (`Atriz_rvr_node.py:331`, `:1636`).

**d) El arreglo:** parámetro **`color_detection`**, por defecto `false`, que enciende el sensor
**antes** de configurar el streaming. Con `false`, el driver **avisa por el log** en vez de
publicar ceros en silencio.

```
con color_detection:=true
  /color    294 mensajes, TODOS con valores reales  ->  [164, 140, 119]
  servicio  R 237 · G 415 · B 160 · Claro 735       (coincide con los 741 del banco)
```

**e) 🔴 Y un fallo mío, que vio el usuario.** El driver encendía el sensor al arrancar y **no lo
apagaba al morir**: el LED blanco se quedaba encendido gastando batería. Es exactamente lo que
avisa `CLAUDE.md` —«cada `(True)` necesita su `(False)`, también en el camino de error»—
cometido dos horas después de leerlo. Arreglado en `_apagar_rvr()`, que ahora apaga sensor **y**
LEDs. Verificado: con el driver vivo `clear=733`; tras matarlo con SIGINT, **`clear=0`**.

⚠️ Solo con cierre **limpio** (SIGINT). Con `kill -9` no corre nada.

### 16.3 Lo que no se pudo portar tal cual, y por qué

| | |
|---|---|
| `set_pos_and_yaw` | **Solo (0,0,0)**, y rechaza el resto en vez de fingir. El SDK no puede fijar una pose arbitraria: solo `reset_locator_x_and_y()`, y `reset_yaw()` **no hace nada** (cap. 10) |
| `trigger_led_event` | El RVR **no tiene** «eventos de LED» — en ROS 1 eran animaciones de la app. Aquí, colores fijos: azul arranque, rojo parada, verde conduciendo, magenta error |
| `uptime_ms` | El SDK no lo expone. Se queda a 0 y **se dice en el `message`**, en vez de dejar un cero mudo que parezca un dato |
| `ConfigureStreaming`, `StartStreaming` | **No portados a propósito**: el driver ya configura su streaming para `/odom`, `/imu` y `/color`. Un servicio que lo reconfigure puede romper la telemetría del propio nodo |

### 16.4 ⚠️ Los servicios de movimiento se saltan la capa de seguridad

Y no hay forma de evitarlo desde el driver:

- el **`collision_monitor`** filtra `/cmd_vel_raw → /cmd_vel`. Estos servicios **no publican en
  ningún topic**: hablan al RVR por el puerto serie.
- el **watchdog de `cmd_vel`** tampoco: vigila que sigan *llegando* mensajes, y aquí no hay.
- **`raw_motors` no tiene ningún corte automático**: sigue hasta que se le manda modo 0.

🔴 **«Se comprueba en todos» ERA FALSO hasta el 2026-08-01**, y era un agujero de seguridad
real: **`set_ir_evading` no comprobaba la parada de emergencia**. Con la parada ACTIVA
respondía `success=True` y el RVR se ponía a conducir solo. Encontrado por una auditoría con
agentes aislados.

Y al lado había un segundo agujero: `set_ir_mode('off')` solo llamaba a
`stop_..._broadcasting()`, así que **`following` —que también conduce— no se podía apagar**, y
**`evading` no tenía ninguna forma de apagarse desde ROS**.

✅ **Arreglado y verificado**: `set_ir_evading` comprueba la parada, `'off'` para los tres
modos, y la parada de emergencia manda además `stop_evading` y `stop_following` — porque
`drive_stop()` **no basta** contra un modo del firmware, que volvería a conducir en la siguiente
detección IR.

**Lo único que los detiene es la parada de emergencia**, que se comprueba en todos y está
verificada (16.1).

### 16.5 📝 `ros2 service list` no es autoritativo

`set_drive_parameters` no aparecía ni en `ros2 service list` ni en `ros2 node info` —los dos
daban 17 de 18— mientras que `ros2 service type` **sí** devolvía el tipo y un cliente con
`wait_for_service` decía **disponible**.

Es descubrimiento de DDS inconsistente en las herramientas de introspección, no un fallo del
nodo. → **Para saber si un servicio existe, usa un cliente.** La lista puede mentir, y miente
**por omisión**, que es la peor forma.

---

## Capítulo 17 — Arranque automático con systemd

> ✅ **ARRANCADO Y VERIFICADO bajo systemd el 2026-07-31**, y de arrancarlo salieron **cinco**
> fallos más (17.3). Comprobado por efecto, no por mensaje:
>
> ```
> Active: active (running)
> ExecStartPost=/usr/local/bin/atriz-escaneo off   status=0/SUCCESS  (10 s)
> /scan    0.00 Hz   <- barrido parado, que es lo que se pedía
> /odom   16.54 Hz   <- el robot vive, a la frecuencia de referencia
> /cmd_vel Publisher count: 1   <- la capa de seguridad intacta
> ```
>
> ✅ **Y PROBADO CON UN REINICIO DE VERDAD**, que es lo único que demuestra el motivo por el que
> existe: `uptime` 1 min, servicio `active (running)` desde el arranque, **PID 711** —los
> procesos lanzados a mano tienen PIDs de miles—, y `/scan` a 0.00 Hz con `/odom` a 16.49.
> Arranque: 5.5 s de kernel + **16.6 s** de userspace.

### 17.1 Por qué, y por qué no basta con un `ExecStart`

En un laboratorio **remoto** nadie puede entrar a arrancar un proceso. Si un robot se
reinicia —corte de luz, kernel actualizado, watchdog— tiene que volver solo, o queda
inservible hasta que alguien vaya al edificio.

Lo que hace que esto no sea una línea de configuración:

**systemd no ejecuta un shell de login.** No lee `~/.bashrc` ni `/etc/profile.d`. Un
`ExecStart=ros2 launch ...` falla con `command not found`; y si se pone la ruta absoluta,
arranca **sin `ROS_DOMAIN_ID`** — o sea con los 16 robots en el dominio 0, viéndose entre sí.
Es exactamente lo que la decisión D1 de `ARQUITECTURA.md` existe para evitar, y **no da ningún
error**: solo topics duplicados y TF que salta, lejos de la causa.

Por eso hay un envoltorio, `atriz-robot.sh`, que carga el entorno, **se niega a arrancar si
`ROS_DOMAIN_ID` no está definido**, espera a que udev cree `/dev/rvr` y `/dev/ydlidar`, y hace
`exec` para que el launch herede el PID.

### 17.2 🔴 El robot arranca con el barrido del LIDAR apagado

Sin esto, el arranque automático empeoraría el robot: hoy el X2 se queda a **2.7 Hz** porque no
hay nada corriendo, y en cuanto los 16 levanten `robot.launch.py` solos pasaría a **11.8 Hz
permanentes, 24/7**, se use el robot o no (cap. 8.4a). Sería un efecto secundario de una tarea
que no habla de lidares.

La unidad llama a `atriz-escaneo off` en su `ExecStartPost`.

⚠️ **Consecuencia que hay que conocer: un robot recién arrancado NO CONDUCE.** No está roto —
sin `/scan` el `collision_monitor` bloquea el movimiento, que es justo lo que queremos. Para
usarlo:

```bash
atriz-escaneo on        # el X2 sube a 11.8 Hz y el robot conduce
atriz-escaneo estado
atriz-escaneo off       # al terminar la sesión
```

Cuando exista la plataforma web (Fase 5), esa llamada la hará ella al empezar una sesión.

📝 Los **servicios de movimiento** del driver sí funcionan con el barrido apagado: hablan al RVR
por el puerto serie y se saltan el monitor (cap. 16). No es una contradicción, es la misma
advertencia de siempre.

### 17.3 Dos fallos reales que salieron de EJECUTAR, no de leer

Los dos habrían fallado en el primer reinicio, con mensajes que no mencionan ni ROS ni el
servicio:

**a) `StartLimitIntervalSec` en `[Service]` se ignora.** Va en `[Unit]`. `systemd-analyze
verify` lo dice —`Unknown key name … ignoring`— y solo si lo ejecutas. El efecto habría sido un
bucle de reinicio **sin tope**, machacando el journal y escondiendo la causa.

**b) Los `setup.bash` de ROS no son compatibles con `set -u`.**

```
/opt/ros/jazzy/setup.bash: line 8: AMENT_TRACE_SETUP_FILES: unbound variable
```

Con `set -euo pipefail` eso mata el envoltorio **antes de arrancar nada**. Se descubrió
ejecutándolo con `env -i`; leyéndolo no se ve. El arreglo es `set +u` alrededor de los `source`
y `set -u` después.

**c) Y el mismo `set -u` volvió a morder en el script hermano, en el primer arranque real.**
Se arregló en `atriz-robot.sh` y **no se aplicó a `atriz-escaneo.sh`**. La primera vez que
systemd levantó el robot de verdad:

```
Process: 6074 ExecStartPost=/usr/local/bin/atriz-escaneo off (code=exited, status=1/FAILURE)
/opt/ros/jazzy/setup.bash: line 8: AMENT_TRACE_SETUP_FILES: unbound variable
```

El servicio quedó `active (running)` —el `-` de la unidad hizo justo su trabajo— pero **el
barrido se quedó encendido**, que era el único motivo de llamarlo. Un fallo que no tumba nada y
deja el sistema en el estado que querías evitar.

**d) Y al arreglarlo aparecieron DOS fallos más en `hay_scan`**, los dos de la misma familia:

1. `ros2 topic echo /scan` se suscribe **RELIABLE** y `/scan` es **BEST_EFFORT**: no llega nada
   nunca. Decía «apagado» con el LIDAR a 8 Hz.
2. Y ni con `--qos-reliability best_effort`: con `--no-daemon`, `echo` tiene que **descubrir el
   tipo** del topic y falla **2 de cada 3 veces** con `Could not determine the type for the
   passed topic`, con el LIDAR girando perfectamente.

→ Reescrito como suscriptor propio: el tipo **se dice**, no se descubre, y el QoS se elige.
✅ 3 de 3 aciertos en los dos estados.

→ **La regla del proyecto otra vez:** comprobar el efecto, no la intención. Un fichero de
unidad que *parece* correcto y dos scripts que *parecen* correctos fallaban los tres. Y el
patrón que se repite: **arreglar un fallo en un fichero y no buscarlo en sus hermanos**.

### 17.4 Instalar

```bash
# primero en seco, que no toca nada
sudo bash ~/atriz_migracion/scripts/fase_7_systemd.sh --simular --id 1

# y de verdad
sudo bash ~/atriz_migracion/scripts/fase_7_systemd.sh --id 1
```

`--id` solo hace falta en el **robot de referencia**, donde `ROS_DOMAIN_ID` vive en el
`~/.bashrc` y systemd no lo ve. En un clon lo crea `first-boot.sh` leyendo
`/boot/firmware/robot_id.txt`, y el script lo detecta.

⚠️ El script avisa si `~/.bashrc` y `/etc/profile.d/atriz-robot.sh` exportan **números
distintos**: el `.bashrc` se lee después y gana, así que tus shells y el servicio acabarían en
dominios DDS distintos sin un solo error.

### 17.5 Verificar — y esto sí es lo que lo verifica

```bash
sudo systemctl start atriz-robot
systemctl status atriz-robot            # active (running)
journalctl -u atriz-robot -n 50

atriz-escaneo estado                    # debe decir apagado
atriz-escaneo on
ros2 topic hz /scan --window 20

# la prueba de verdad, la que dice si un robot remoto se recupera solo:
sudo reboot
systemctl status atriz-robot
```

Para quitarlo: `sudo bash ~/atriz_migracion/scripts/fase_7_systemd.sh --quitar`.

### 17.6 ⏳ Lo que queda abierto

📝 **Lo que NO se ha ejercitado, aunque el servicio funcione:**

- **La espera de puertos del envoltorio nunca ha llegado a esperar.** Las tres veces salió
  `tras 0s`, también en frío: udev crea los enlaces antes de que systemd llegue a esta unidad.
  Es una red de seguridad **sin estrenar**, no una comprobación aprobada.
- **`Restart=always` tampoco.** No se ha matado el proceso para ver si vuelve. Y ojo: no arregla
  el fallo típico de este robot —el RVR dormido deja el proceso **vivo**—, de eso se encarga el
  keepalive del driver.
- **n=1.** Un solo reinicio. Sin corte de corriente, ni arranque con el RVR apagado o el lidar
  desenchufado.

- ✅ **`provision.sh` YA lo instala** (paso 8/9, desde el 2026-08-01). Toma el número de robot de `/boot/firmware/robot_id.txt`, y **habilita sin arrancar**: entra en el próximo reinicio.
- ~~`provision.sh` no lo instala todavía.~~ Si no se añade, la imagen dorada saldrá **sin
  arranque automático** y habrá que hacerlo robot a robot — justo lo que la imagen evita.
  Está sin hacer a propósito: mientras se desarrolla en el robot de referencia, un servicio
  levantado pelearía por `/dev/rvr` con las pruebas a mano.
- ✅ ~~La parada de emergencia no cancela las acciones de Nav2~~ — **falso, y ya estaba
  arreglado cuando se escribió esto**. El nodo `cancelar_nav2` manda `CANCEL_ALL`; verificado
  con control: objetivo `CANCELED` y **0.0 cm** al liberar, contra **34.7 cm** sin él (cap.
  15.4). 🔴 Es **la misma frase** que el cap. 15.3 documenta como el caso ejemplar de deriva
  documental de este proyecto: sobrevivió en otro capítulo del mismo fichero. **Al corregir
  algo, busca TODAS sus menciones.**
- ✅ ~~`rosbridge` no tiene unidad todavía~~ — está instalado y corriendo desde el 2026-08-01,
  dentro de `robot.launch.py` y **no** en unidad systemd propia, para que herede el
  `ROS_DOMAIN_ID` (cap. 19.6).


---

## Capítulo 18 — La telemetría que faltaba: motores, encoders y luz

> ✅ **Verificado el 2026-08-01** sobre rvr-01. Cada afirmación de este capítulo lleva la medida
> que la sostiene, y las tres retractaciones están marcadas.

Este capítulo cierra tres huecos del inventario del cap. 16 y **encuentra un bug de LEDs que
llevaba ahí desde el principio**. El hilo conductor es el mismo de todo el proyecto: *el comando
funcionó* y *el hardware hizo algo* son afirmaciones distintas.

### 18.1 🔴 `/motor_status` — y por qué se SONDEA en vez de escuchar

**El problema que resuelve:** hasta hoy, **un robot con una oruga trabada se veía exactamente
igual que uno que navegaba mal**. `/odom` avanzaba poco, Nav2 abortaba por «no progresar», y nada
distinguía un fallo de hardware de uno de algoritmo. Con 16 robots en otro edificio, esa
diferencia decide si alguien tiene que ir hasta allí.

Se implementó primero con las **notificaciones** que ofrece el SDK
(`enable_motor_stall_notify` + `on_motor_stall_notify`, y las de fallo y térmica). **No llega ni
una**, y se descartó la culpa propia una por una:

| Se comprobó | Resultado |
|---|---|
| ¿está bien el registro? | ✅ `on_command` mete el handler en la tabla de despacho y vuelve. La task terminando enseguida es **normal** — una versión de este código avisaba de ello como si fuera el fallo, y era un **falso positivo** |
| ¿da error el `enable_*`? | ✅ no. Devuelven `None`, que en este SDK significa «comando sin respuesta pedida» |
| ¿se atascó de verdad? | ✅ dos veces: `move_timed` 0.15 m/s con el robot sujeto, y `raw_motors` a **220/255** apretado contra el suelo |
| ¿y la térmica, que llega sola? | ✅ 100 s de escucha: **4 mensajes, los 4 del keepalive**, todos con antigüedad −1 |

Ese último es el que lo zanja: si el problema fuera «no atascamos bastante», la térmica habría
llegado igual. → **Este firmware no emite estas notificaciones**, igual que `core_time`.

✅ **Las consultas directas SÍ responden**, así que el driver **sondea cada 30 s** junto al
keepalive:

```
get_motor_fault_state                -> {'is_fault': False}
get_motor_thermal_protection_status  -> 27.9 / 27.7 °C, estados 0/0
```

📝 Es además la **única vía** por la que este proyecto tiene temperatura de motores.

> 🔴🔴 **RETRACTADO EL 2026-08-01: EL ATASCO NO SE QUEDA FUERA.** La notificación del firmware
> **sí llega** — 3 de 3 detecciones con el robot bloqueado a mano, acertando la oruga las tres
> veces. La medida que decía lo contrario hizo **dos** ensayos, y el primero **ya usaba el camino
> bueno** (`move_timed`) — durante **3 s**, cuando la detección tardó **~5 s** (⚠️ n=1, **5 ±2 s** por la resolución del journal, y a distinta velocidad que el ensayo fallido — ver `CLAUDE.md`). 🔴 **La causa es
> el TIEMPO, no el camino**; decir «se probó con `raw_motors`» solo explicaba el segundo ensayo.
> ⚠️ Y queda un confusor sin aislar: 0.15 m/s entonces contra 0.08 ahora.
>
> 📝 **Antes de concluir que algo NO ocurre, pregunta cuánto tendrías que haber esperado.**
> Evidencia 44.

✅ **Lo que sigue siendo cierto:** el SDK **no tiene** `get_motor_stall_state` —el atasco solo
existe por **notificación**, no por consulta— y la **corriente de los motores tampoco se puede
leer** (`get_current_sense_amplifier_current` → `bad_cid`). Lo falso era la conclusión, no esos
dos datos.

📝 **Y `antiguedad_atasco_s = −1.0` sigue apareciendo**, pero significa lo que siempre debió
significar: «**nunca se ha sabido nada**» — o sea que no ha habido ningún atasco desde que
arrancó el driver. No es «no hay atasco».

🔴 **Y ese campo nació mal:** la primera versión tenía **una sola** antigüedad para las tres
cosas, y el sondeo del fallo la refrescaba. Daba `antiguedad_atasco_s = 0.0` —«recién
comprobado»— sobre algo que no se comprueba nunca. **Falsa tranquilidad, peor que no publicar el
campo.**

### 18.2 🔴 El bug de los LEDs: una máscara de bits, no siempre tres canales

`led_group` es una **máscara**, y `set_all_leds` espera **un valor de brillo por bit encendido**:

| grupo | bits | valores que espera |
|---|---|---|
| los 10 normales | 3 | `[r, g, b]` |
| `all_lights` | **30** | `[r, g, b]` × 10 |
| `undercarriage_white` | **1** | uno solo (es blanco, no RGB) |

El driver mandaba **siempre tres**. Para los 10 acierta; a los otros dos **el RVR les dice que sí
y no hace nada**. `success=True` con el LED apagado.

📝 **Lo encontró el ojo del usuario, no el código.** El script reportó 12/12 ✅ y él dijo *«no vi
los bajos ni tampoco todos»*. Sin esa frase, los doce habrían pasado por buenos. Arreglado
contando bits; los tres servicios de LED comparten ahora la regla.

⚠️ **`undercarriage_white` sigue sin encender**, y esta vez medido sin depender de la vista: con
el sensor de luz como testigo, la luz no cambia. **El LED blanco de los bajos lo enciende
`enable_color_detection`**, no ese grupo. Y no se ve desde arriba: está bajo el chasis.

### 18.3 `/encoders` y `/ambient_light` — dos bugs de camino

Los dos están en `RvrStreamingServices`, así que van por el mismo stream que el resto.

🔴 **Las claves son `LeftTicks`/`RightTicks`, no `Left`/`Right`.** La tabla de documentación del
**propio SDK** dice `| Encoders | Left, Right |` y el payload trae otra cosa. Con las claves malas
el handler lanza `KeyError`, el topic queda **registrado y con cero mensajes** — el síntoma exacto
de un RVR dormido. Se desempató imprimiendo el dict **crudo**.

🔴 **Los ticks vienen sin signo, en 32 bits.** Un retroceso llega como **4294965940**, que son
**−1356**. `Encoder.msg` es `int32`: sin convertir se publicaría un número absurdo **y creciente**,
que parecería un encoder sano.

✅ **Y no le cuesta ritmo a `/odom`:** 16.58 · `/imu` 16.57 · `/encoders` 16.57 ·
`/ambient_light` 13.06 Hz.

### 18.4 ✅ Los DOS sensores ópticos — caracterizados, y son dos

> 🔴 **Esta sección sustituye a una anterior que era FALSA.** Se documentó que `/ambient_light`
> da 0.0 sin `color_detection`, y **no es cierto**: son sensores distintos, en sitios distintos.
> Las dos retractaciones están en 18.4c.

**El sensor de color funciona.** Con `color_detection:=true`, colocando cada superficie de una en
una y con el usuario confirmando antes de cada medida:

| superficie | `clear` | R/G | B/G | `/color` |
|---|---|---|---|---|
| suelo | 1275 | 0.546 | 0.413 | (255, 220, 209) beige cálido |
| blanco | **2288** | 0.482 | 0.498 | (244, 235, 255) neutro |
| rojo | 565 | **2.743** | 0.355 | **(255, 31, 43)** |
| azul | 396 | 0.447 | **0.856** | **(88, 120, 201)** |
| negro | **181** | 0.480 | 0.460 | (28, 27, 29) |

`clear` recorre **12.6×** entre blanco y negro, el rojo dispara R/G de 0.48 a 2.74, el azul sube
B/G a 0.86, y `/color` **acierta los cinco**.

📝 Se normaliza por **G** porque en un RGBC el verde es el canal más sensible: comparar los tres
en crudo hace parecer que «todo es verde».

🔴 **La `confianza` es 0.00 en los cinco, y NO es el sensor.** Es el **clasificador** del RVR, que
compara contra una **paleta**.

> 🔴 **Aquí este manual se equivocaba.** Decía que la confianza es 0 porque falta cargar una
> paleta. **Hay paleta y está activa**: `get_active_color_palette` devuelve cinco colores
> —(212,40,47), (243,218,67), (21,157,128), (0,140,160), (97,53,139)—. La confianza es 0 porque
> las superficies probadas **no se parecen a ninguno de esos cinco**, que es un resultado
> legítimo del clasificador. Comprobado el 2026-08-01, evidencia 41.
>
> 📝 **Y la lección:** era una explicación plausible que nadie comprobó. Bastaba una consulta.

El SDK tiene `load_color_palette` y `set_active_color_palette`, y el
driver **no usa ninguna**. Si alguna vez hace falta que el robot *nombre* un color, eso es lo que
hay que portar; los datos crudos ya sirven sin ello.

#### 18.4b `/ambient_light` es OTRO sensor, y ve los LEDs del propio robot

La medida que los separa:

```
encender los 10 grupos de LED:  luz 1.76 -> 23.55   (13.3×)  · y vuelve a 1.30
los mismos LEDs vistos por el RGBC:  IDÉNTICO en rojo, verde y azul
```

✅ **Y el porqué es físico, y lo aportó el usuario:** el sensor de luz ambiente **mira hacia
arriba**, y encima del Sphero está el **piso que sostiene el LIDAR** —los 4.6 cm de
[`MEDIDAS_ROBOT.md`](../03_operacion/MEDIDAS_ROBOT.md)—, que es **blanco**. Ese piso hace de
reflector y devuelve la luz de los LEDs del propio robot sobre el sensor.

📝 Esto **no se podía deducir de los datos**. Los datos decían «ve los LEDs»; el *porqué* es una
observación del montaje. Es el mismo patrón que la inclinación del robot y el LED de los bajos:
**hay cosas que solo se saben mirando el hardware.**

🔴 **DECISIÓN: `/ambient_light` no se usa.** En este montaje no mide la luz de la sala — mide el
reflejo de los LEDs del robot en una superficie blanca a 4.6 cm. Un valor alto significa «el robot
tiene LEDs encendidos», no «hay luz». Se probó solo para saber si el sensor responde, y responde.

El topic se deja publicado (es gratis, va en el mismo stream) pero **ningún consumidor debe
apoyarse en él** mientras el piso del LIDAR siga ahí, que será siempre. Y **no se arregla con
software**: haría falta pintar de negro la cara inferior del piso, o mover el sensor. No merece la
pena — nada del laboratorio necesita luz ambiente. Y **no depende de `color_detection`**.

#### 18.4c 🔴 Dos afirmaciones retiradas, y dos montajes que mentían

**(a) «`/ambient_light` da 0.0 sin `color_detection`»** — falso. Las lecturas de 0.0 se tomaron
con el robot **sin levantar de verdad** (lo confirmó el usuario después) y con los LEDs apagados.
→ **El error de método: se dio por hecha una condición experimental que nadie comprobó.** Si tu
medida depende de que alguien haga algo físico, **pregunta si lo hizo**.

**(b) «cada reinicio del driver degrada el stream de luz»** — falso. La caída de 13.4 a 2.0 era el
**apagado limpio apagando los LEDs**. Lo propuso el usuario y la medida le dio la razón.

**Y dos montajes que daban resultados imposibles:**
- deslizar el papel sin comprobar que tapa la ventana → el «blanco» dio **exactamente** los mismos
  números que la referencia. Idéntico no es parecido.
- **pegar el objeto contra la ventana tapa también el LED** → el blanco dio `clear=261` y el negro
  795, al revés de lo físicamente posible.

→ **El protocolo que sí funciona:** una superficie por vez, el usuario la coloca y **confirma**
antes de medir, a la distancia natural del suelo, y localizando la ventana primero con papel
blanco mientras se lee `clear` en vivo (765 → 2269, 3.0×).

### 18.5 🔴 Una conclusión RETIRADA: «un comando de LED mata la telemetría»

Durante una hora esta sesión creyó haber encontrado un fallo grave: tras cualquier comando de
LED, `/odom`, `/encoders` y la luz caían a **0.0 Hz**. Se llegó a **aislar** quitando los dos
sensores nuevos —seguía pasando— y a concluir que era **preexistente**, lo cual habría
significado que la web no puede encender un faro sin cegar al robot.

**Era falso. El fallo estaba en el instrumento de medida:**

```python
ex = SingleThreadedExecutor(); ex.add_node(n)
...
rclpy.spin_until_future_complete(n, futuro)   # 🔴 el nodo YA está en `ex`
```

`rclpy.spin_until_future_complete` mete el nodo en el ejecutor **global**; deja de ser atendido
por `ex` y **las suscripciones del medidor** se callan. Con `ex.spin_until_future_complete()`:
16.9 → 16.6 → 16.6 → 16.5 Hz. **El robot no había dejado de publicar ni un mensaje.**

→ **Regla:** si hiciste `ex.add_node(n)`, todo el giro es de `ex`.
→ Van **cuatro** veces que el instrumento miente en este proyecto (`ros2 topic hz`, `spin_once`
  en bucle, `mensajes/duración`, y esto). **Ante una medida rara, sospecha del medidor.**

📝 Contribuyó un bug propio: `_avisar_una_vez` se apoyaba en `_recibidos`, que `_quiza_publicar`
**vacía en cada ciclo de `/odom`**, así que un aviso «una vez» salía **13 veces por segundo**
desde el hilo de asyncio.

### 18.6 🔴 Seis veces el mismo error de `colcon` — y el arreglo

«Summary: 0 packages finished» no compila nada, no parece un error, y lo siguiente es reiniciar
el nodo y leer un log del código **viejo**. Pasó **seis veces en esta sesión**, ya documentado en
`CLAUDE.md`, y creó un **workspace parásito** en `src/Atriz_rvr/build`.

→ Un aviso que se ignora seis veces no es un aviso: es una tarea pendiente. Ahora hay
**`scripts/compilar.sh`**:

```bash
bash ~/atriz_migracion/scripts/compilar.sh atriz_rvr_driver
bash ~/atriz_migracion/scripts/compilar.sh --limpio atriz_rvr_msgs   # si tocaste un .msg
```

⚠️ **Cambiar un `.msg` no basta con `colcon build`:** el fichero instalado se queda con la
versión anterior y el suscriptor da `AttributeError` sobre un campo que existe en el fuente. Eso
es `--limpio`, y tarda ~4.5 min.

### 18.7 ✅ Y de paso se estrenó `Restart=always`

Para desplegar cada versión se mató el proceso principal en vez de pedir un `sudo`:

```
kill -INT $(systemctl show atriz-robot -p MainPID --value)
  +5s  activating · +20s PID nuevo · +30s active · NRestarts 0 -> 1
```

Funciona, y se repitió una docena de veces sin fallo. Era una de las tres redes de seguridad sin
estrenar (cap. 17.6). **Sigue sin estrenar la espera de puertos del envoltorio.**

### 18.7b ✅ La batería: usa `voltage`, no `percentage`

> Implementado y verificado el 2026-08-01. Evidencia 43.

🔴 **El porcentaje no sirve para decidir si hay que cargar.** Medido: decía **100 %** con la
batería a **8.29 V**, que está a **1.29 V** del umbral de «baja» del propio firmware. Es una
estimación gruesa.

Desde el 2026-08-01 `/battery_state` publica el **voltaje real** (antes era `NaN`) y el driver
registra los umbrales **del firmware** en el log al arrancar:

```
[rvr_driver]: umbrales de batería (firmware): baja 7.00 V · crítica 6.50 V · histéresis 0.20 V
```

| | |
|---|---|
| batería **baja** | `voltage` < **7.0 V** |
| batería **crítica** | `voltage` < **6.5 V** — umbral que **devuelve el propio firmware** (`get_battery_voltage_state_thresholds`). ⚠️ Qué hace el RVR al cruzarlo **no está documentado y no se ha provocado**: no asumas que se apaga solo |
| histéresis | **0.2 V**, la aplica el firmware, así que el estado **no rebota** |

📝 **Sale gratis:** las dos lecturas van en la misma pasada del keepalive, que ya llamaba al RVR
cada 30 s. No cuestan un viaje extra al puerto serie.

⚠️ **«Batería baja» NO se marca como averiada.** `power_supply_health` no tiene un valor para
«poca carga», y forzar `DEAD` engañaría a cualquier consumidor: una batería descargada está
**sana**. Solo «crítica» —cuando el RVR va a apagarse— se mapea a `DEAD`.

🔴 **Con 16 robots esto es una pregunta diaria.** «¿Cuál se está quedando sin carga?» no la
responde el porcentaje.

---

### 18.8 ⏳ Lo que queda abierto

✅ **CERRADO en 18.4.** La duda era «`/color` publica `(0,0,0)` con la luz encendida», y la
respuesta resultó ser que **en aquella prueba la luz NO estaba encendida**: el argumento del
launch pisa el valor declarado en el nodo, así que cambiar `declare_parameter` no servía de nada.

Con el LED encendido de verdad, `/color` **acierta los cinco colores** (18.4). Y la
`confidence` sigue en 0 — pero 🔴 **NO porque falte una paleta**: la hay y está **activa**
(cinco colores, cap. 18.4, comprobado el 2026-08-01). Es que las superficies probadas **no se
parecen a ninguno de los cinco**, que es un resultado legítimo del clasificador, no un fallo.

Evidencia cruda: `00_auditoria/evidencia_24_04/35_salud_motores.txt` y `36_leds_luz_encoders.txt`.

Hasta entonces, para reconstruir el sistema **Noetic** el procedimiento válido es el
[manual original anotado](MANUAL_SPHERO_transcripcion.md), aplicándole las correcciones
marcadas en sus bloques `⚠️ AUDITORÍA` — en particular los nombres de paquete de los
comandos de ejecución, que ya no existen.

---

## Capítulo 19 — Red de la flota: cómo la web encuentra a 16 robots

> ✅ **VERIFICADO DE EXTREMO A EXTREMO el 2026-08-01.** Un navegador del PC del usuario abrió
> `ws://rvr-01.local:9090`, recibió telemetría y **encendió los faros del robot** — confirmado
> con la vista, no solo por el `success=true`. Evidencia 39.

### 19.1 El problema real, que no es técnico

Los 16 robots viven en el laboratorio (`Atriz-server`, red `10.14.0.0/21` que administra un
tercero), pero la plataforma web se desarrolla en un PC de casa (`VERCINGE_TORIX`,
`192.168.1.0/24`). Y un robot montado no se reconfigura: **se lleva**.

Si la web guardara direcciones IP, mudar el robot de una red a otra obligaría a editar la web,
el robot, o los dos. Multiplicado por 16, y con un administrador de red ajeno de por medio, eso
es una tarde perdida cada vez.

**El objetivo del diseño es que mudarse cueste cero comandos.**

### 19.2 Tres piezas, y cada una cubre el fallo de otra

| Pieza | Qué resuelve | Qué pasa si falla |
|---|---|---|
| **IP estática** por robot, en las dos redes | dirección conocida y estable en el laboratorio | queda el DHCP |
| **DHCP simultáneo** | funciona en una red que nadie configuró | queda la estática |
| **mDNS** (`rvr-NN.local`) | encontrar al robot **sin saber ninguna IP** | quedan las dos anteriores |

🔴 **Las tres a la vez, no una.** La combinación es lo que hace que el sistema aguante que se
caiga el DHCP, que el administrador cambie la subred, o que alguien teclee mal una IP.

⚠️ **Lo que sí verifica esta lista: que `dhcp4: true` y `addresses:` estáticas CONVIVEN en la
misma interfaz.** Es la suposición sobre la que se apoya todo lo demás.

### 19.3 El perfil de red vive en la partición FAT

`/boot/firmware/red.txt`, junto a `robot_id.txt`. Plantilla sin secretos en
[`scripts/red.txt.ejemplo`](../scripts/red.txt.ejemplo).

```
LAB_SSID=Atriz-server
LAB_PASS=…
LAB_IP=10.14.7.7          # OBLIGATORIA: la que asigne el administrador de red
LAB_PREFIJO=21
LAB_GATEWAY=10.14.0.1

CASA_SSID=VERCINGE_TORIX
CASA_PASS=…
CASA_IP=192.168.1.200
CASA_PREFIJO=24
CASA_GATEWAY=192.168.1.1

DHCP=no                   # 🔴 era `si` hasta el 2026-08-04: ver abajo
RUTA_POR_DEFECTO=dhcp
DNS=8.8.8.8,1.1.1.1
```

🔴 **POR QUÉ EN LA FAT Y NO EN `/etc/netplan`.** Una IP estática equivocada deja al robot **sin
dirección en esa LAN**, y entonces no puedes entrar por SSH a arreglarla. La FAT se lee desde
Windows, macOS o Linux **metiendo la microSD en un PC, sin arrancar la Pi**. Siempre hay una
salida. Es el mismo mecanismo que `robot_id.txt`, que ya funcionaba así.

🔴 **Y NO VA A GIT:** lleva la PSK del WiFi (regla 5 del proyecto). Se versiona la plantilla.

### 19.3b `chmod` no funciona en la partición FAT, y eso deja la PSK al aire

```
$ sudo chmod 600 /boot/firmware/red.txt
$ ls -l /boot/firmware/red.txt
-rwxr-xr-x 1 root root 253 Aug  1 15:14 /boot/firmware/red.txt      ← sigue en 755

$ findmnt -no OPTIONS /boot/firmware
rw,relatime,fmask=0022,dmask=0022,…                                 ← el motivo

$ head -2 /boot/firmware/red.txt          # SIN sudo
LAB_SSID=Atriz-server
LAB_PASS=…                                                          🔴 legible por todos
```

🔴 **FAT no almacena permisos de Unix.** Los fija la opción **`fmask` del montaje**, y vale
para **toda la partición**. El `defaults` que trae Ubuntu da `fmask=0022` → **755**.

🔴 **Y `chmod` se acepta sin error.** No falla, no avisa, y no hace nada. Eso es peor que
fallar: deja el problema abierto **con aspecto de resuelto**. Este manual llegó a recomendar
ese `chmod`; se corrigió el 2026-08-01 al comprobar el efecto en vez del comando.

**Cuánto importa:** el robot tiene un solo usuario (`sphero`), así que quien puede leer el
fichero ya tiene sesión en la máquina. Pero **la misma PSK también está en `/etc/netplan/*.yaml`
con `600`**, o sea que la FAT es el eslabón débil, y la imagen dorada replica esto **por 16**.

**Si quieres cerrarlo** — es un cambio del arranque, así que lo ejecuta la persona:

```bash
sudo cp /etc/fstab /etc/fstab.bak
sudo sed -i 's|\(/boot/firmware\s\+vfat\s\+\)defaults|\1defaults,fmask=0177,dmask=0077|' /etc/fstab
sudo mount -o remount /boot/firmware
ls -l /boot/firmware/red.txt          # debe salir -rw------- root root
```

⚠️ Es seguro para el arranque: el firmware del Pi lee la FAT **antes de Linux** e ignora los
permisos de Unix. Pero **verifícalo con un reinicio** antes de meterlo en la imagen dorada.

📝 **Alternativa si no quieres tocar `fstab`:** asumirlo y no poner ahí nada más sensible que
la PSK del WiFi del laboratorio. Es una decisión de despliegue, no técnica.

#### 19.3b · `chmod 600` sobre la FAT no hace nada, y eso es peor que no intentarlo

```
-rwxr-xr-x 1 root root 253 Aug  1 15:14 /boot/firmware/red.txt
/dev/mmcblk0p1 vfat rw,relatime,fmask=0022,dmask=0022,…
```

**FAT no almacena permisos de Unix.** Los fija el *montaje* (`fmask`), y con `defaults` salen
**755**. El `chmod 600` **devuelve 0 y no cambia nada** — la peor combinación posible, porque
parece que funcionó.

🔴 **Consecuencia real:** cualquier usuario del robot lee la PSK del WiFi **sin `sudo`**. Y la
imagen dorada replica eso por 16.

```bash
head -2 /boot/firmware/red.txt     # sin sudo, y sale LAB_PASS=…
```

**Para cerrarlo**, en `/etc/fstab`:

```
LABEL=system-boot  /boot/firmware  vfat  defaults,fmask=0177,dmask=0077  0  1
```

Ficheros a 600 y directorios a 700. El firmware de la Pi lee la FAT **en crudo, antes de
arrancar Linux**, así que no le afecta.

📝 **La versión general de la trampa:** un comando que devuelve 0 no prueba que hiciera algo.
Es la misma forma de fallo que `set_all_leds` aceptando una máscara mal formada, que
`undercarriage_white` devolviendo `success=true` sin encender nada, y que `colcon build`
diciendo «finished» sin compilar. **Comprueba el efecto, no el código de salida.**

⚠️ **`RUTA_POR_DEFECTO` es el campo que más fácil rompe internet.** Las dos direcciones
estáticas están puestas siempre, en las dos redes — eso es inofensivo. Pero **una ruta por
defecto hacia un gateway que no existe en la red actual sí rompe el tráfico de salida**, porque
el sistema la da por válida igualmente. Por eso se elige UNA, y por defecto la pone el DHCP.

### 19.4 Generar y aplicar: dos pasos, y separarlos es la seguridad

```bash
# 1. Genera /etc/netplan/60-atriz.yaml y lo VALIDA. No aplica nada.
sudo bash ~/atriz_migracion/scripts/first-boot.sh --solo-red

# 2. Míralo (sin sacar las contraseñas por pantalla)
sudo grep -v password /etc/netplan/60-atriz.yaml

# 3. Aplica. CUÁL de los dos depende de si tu dirección sobrevive al cambio:
sudo reboot                     # si red.txt lleva DHCP=no  (lo normal)
sudo netplan try --timeout 90   # solo si el DHCP sigue encendido
```

📝 **`--solo-red` existe porque cambiar una IP no debería costar un reinicio.** Regenera el
netplan y para: no toca hostname, ni `machine-id`, ni las claves SSH de host, ni la marca de
first-boot. Con 16 robots, «edita `red.txt` y reinicia» convierte *«corrige la IP del robot 9»*
en una tarde.

🔴 **Y no aplica a propósito.** `netplan try` pide ENTER para confirmar y **revierte solo a los
90 s** si te quedas sin conexión. Separar «escribir» de «aplicar» es lo que impide que una IP
mal puesta te deje fuera de un robot que está en otro edificio.

⚠️ **Corregido el 2026-08-11: con `DHCP=no`, `netplan try` NO sirve.** Aplicar quita la dirección
del DHCP por la que estás conectado, la sesión SSH se corta en ese instante, no hay quien pulse
ENTER, y a los 90 s revierte. **Siempre.** La condición es si **la dirección por la que estás
conectado sobrevive al cambio**:

- ✅ **Sobrevive con el DHCP encendido** — así funcionó en rvr-01 el 2026-08-01, y por eso quedó
  verificado: `wlan0` acabó con **tres direcciones IPv4 a la vez**.
- 🔴 **No sobrevive con `DHCP=no`**, que es lo que trae la plantilla desde el 2026-08-04. Ahí va
  `sudo reboot`, y se vuelve a entrar por nombre (`ssh sphero@rvr-NN.local`), que funciona con
  cualquier dirección.

`first-boot.sh --solo-red` mira el `red.txt` y te dice cuál de los dos toca.

### 19.5 mDNS: encontrar al robot sin saber su IP

`fase_1_higiene_so.sh` **deshabilitaba `avahi-daemon`** como parte de la higiene, mientras el
capítulo 7 decía «usa `ping rvr-01.local`». Se corrigió el 2026-08-01: ahora lo habilita y pone
`MulticastDNS=yes` en `systemd-resolved`.

✅ **Verificado desde el PC del usuario:**

```
PS C:\Users\burav> ping rvr-01.local
Reply from fe80::da3a:ddff:fed6:c1ee%10: time=3ms      (4 de 4, 0 % de pérdida)
```

⚠️ **Respondió con una IPv6 link-local, no con la IPv4, y eso disparó dos sospechas que
resultaron FALSAS.** Comprobarlas costó dos comandos; la alternativa era descubrirlo en la
Fase 5 con la web ya escrita:

- *«rosbridge escucha en `0.0.0.0`, o sea solo IPv4»* → **falso**: `ss` muestra `0.0.0.0:9090`
  **y** `[::]:9090`.
- *«avahi publica solo la AAAA»* → **falso**: publica `A=192.168.1.58` **y** la AAAA. Windows
  simplemente **prefiere IPv6** (RFC 6724).
  🔴 **Y desde el 2026-08-04 ya no es así, ni debe serlo:** avahi publica **una sola A** y ninguna
  AAAA (`use-ipv6=no` **más** `publish-aaaa-on-ipv4=no`). Publicar varias direcciones es lo que
  colgaba al navegador —se queda en la primera que no sirve, sin dar error— y dejaba el muro sin
  encontrar ningún robot. Evidencias 74 y 75.

📝 **La lección de método:** el `ping` pasó y parecía un éxito completo. **Una prueba que pasa
tampoco dice lo que crees hasta que miras qué pasó exactamente.**

Herramienta: `mediciones_banco/probar_mdns.py`, que consulta los dos registros por separado y
tiene `--flota 16` para saber qué robots están vivos. No usa `zeroconf` ni `avahi-utils` a
propósito: **un diagnóstico que exige instalar software no sirve el día que hay una avería.**

⚠️ **Pendiente:** `resolvectl mdns` da `Global: yes` pero `wlan0: no`. Avahi responde —que es
lo que importa para que te encuentren— pero el robot no resuelve el `.local` de otros.

⚠️ **Y comprueba el aislamiento de clientes del punto de acceso del aula.** Rompería mDNS *y*
la comunicación PC↔robot. Es una casilla del AP, y no está comprobada.

### 19.6 La web habla por rosbridge, y cuánto cuesta

`robot.launch.py` levanta `rosbridge_websocket` en el **puerto 9090** (argumento `rosbridge`,
por defecto `true`). Va en el launch y **no en una unidad systemd propia** para que herede el
`ROS_DOMAIN_ID`, que es justo lo que systemd no sabe dar por sí solo.

**Ancho de banda medido dos veces, con dos clientes distintos en dos máquinas distintas:**

| | binario | rosbridge (JSON) | factor |
|---|---|---|---|
| `/odom` | 724 B | 818–820 B | 1.13× |
| `/scan` | 2220 B | **5532–5661 B** | **2.5×** |

| Estado del robot | por robot | ×16 |
|---|---|---|
| navegando (con `/scan`) | **80.7 kB/s** | **10.3 Mbit/s** |
| en reposo (sin `/scan`) | **13.6 kB/s** | **1.7 Mbit/s** |

🔴 **Se había estimado que el JSON multiplicaría por 3–5. El real es ~2×**, y esa diferencia es
la que separa «hay que comprar red» de «cabe».

🔴 **`/scan` es el 83 % del tráfico.** La diferencia entre 1.7 y 10.3 Mbit/s **es `/scan` y nada
más**. Si la web no lo necesita crudo —o le basta 1 de cada 5 barridos— el problema de red
desaparece. Es la palanca más grande que tiene este sistema.

📝 **Y el caudal NO es una constante del robot.** Las dos medidas difieren un 7.6 %, explicado
entero: el X2 **gira libre** (11.45 → 11.86 Hz) y el JSON de un float ocupa **según sus
dígitos** (`0.5` son 3 caracteres, `1.8371830940246582` son 18). Un robot en una habitación
con paredes irregulares genera más bytes que uno mirando al vacío. **Para dimensionar la red se
usa el número alto.**

### 19.7 La prueba de que todo esto funciona

[`03_operacion/probar_conexion_web.html`](../03_operacion/probar_conexion_web.html) — se abre
con doble clic **en el PC**, no en el robot. Sin librerías y sin CDN: WebSocket del navegador
contra el protocolo JSON de rosbridge, escrito a mano, para que funcione **sin internet**, que
el laboratorio puede no tener.

Prueba **las dos direcciones**, que son caminos distintos:

```
15:08:35  ✅ WebSocket abierto
          /odom  16.53 Hz  817 B    /scan  11.86 Hz  5661 B    /battery_state 100 %
15:09:13  respuesta de /set_led_rgb: success=true  headlight_left = (0,255,0)
```

✅ **Y los faros se encendieron de verdad**, confirmado con la vista. Importa: en este proyecto
`success=true` ya devolvió `true` sobre un LED que **no alumbra** (`undercarriage_white`). El
camino completo queda probado hasta el hardware:

```
navegador → WebSocket → rosbridge → servicio ROS 2 → driver → SDK → serie → RVR → LED
```

⚠️ Ábrela como fichero local (`file://`). Servida por HTTPS, el navegador bloquea `ws://` por
contenido mixto.

🔴 **No mueve el robot, a propósito.** `cmd_vel_raw` se salta el `collision_monitor` si se usa
mal, y una página de diagnóstico no es el sitio para descubrirlo.

### 19.8 Una trampa que costó un diagnóstico entero

Al ejecutar `first-boot.sh --solo-red` por primera vez, informó de que netplan había rechazado
la configuración con un error de **systemd sobre autenticación interactiva**. Nada de eso era
cierto: **netplan ni siquiera llegó a ejecutarse**.

```
-rw-rw-r-- 1 sphero sphero 203 Aug  1 14:43 /tmp/netplan.err
fs.protected_regular = 2
```

🔴 **Ubuntu 24.04 impide a ROOT escribir en un fichero de `/tmp` que no le pertenece**
(`fs.protected_regular=2`). La redirección `2>/tmp/netplan.err` fue denegada — y **si la
redirección falla, bash no ejecuta el comando**. El `if` dio error, el `else` imprimió el
contenido de las 14:43 (una prueba sin `sudo` de horas antes) como si fuera el fallo actual, y
borró un netplan que estaba perfectamente bien.

→ **Usa `mktemp`, nunca una ruta fija en `/tmp`.** Arreglado en `first-boot.sh` y en
`provision.sh`, que tenía el mismo patrón con el `.deb` de ROS y habría mordido igual
instalando los 16 robots.

→ **Y la regla general:** un error que menciona permisos o autenticación en un script que ya
corre como root **casi nunca es lo que dice**. Mira si lo que falló fue la *redirección*, y
**comprueba la fecha del fichero que estás leyendo**.

📝 El daño no fue el fallo, fue la **atribución**: el mensaje apuntaba a systemd y a polkit, y
se estuvo a punto de diagnosticar un problema de D-Bus inexistente en un sistema sano.

### 19.9 Lo que sigue sin verificar

| Pendiente | Por qué importa |
|---|---|
| ✅ ~~`netplan try` en vivo~~ | **Verificado el 2026-08-01**: `wlan0` con **tres** direcciones IPv4 a la vez y la ruta por defecto del DHCP. Conviven |
| mDNS **por enlace** (`wlan0: no`) | el robot no resuelve el `.local` de otros robots |
| Aislamiento de clientes del AP del aula | rompería mDNS y la comunicación PC↔robot |
| El bloque de IP del laboratorio | el usuario lo tiene asignado, pendiente de tenerlo a mano |
| ✅ ~~Namespace~~ | **CERRADO 2026-08-01: sin namespace.** Cap. 19.9 y `ARQUITECTURA.md` |
