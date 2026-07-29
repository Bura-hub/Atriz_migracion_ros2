# Informe de auditoría — Sistema Atriz / Sphero RVR

**Fecha:** 29 de julio de 2026
**Revisado:** 29 de julio de 2026 — ver [Correcciones](#correcciones-tras-verificar-en-banco) al final. **Léelas antes que nada: tres hallazgos de este informe resultaron erróneos.**
**Alcance:** Raspberry Pi 4B con Ubuntu 20.04 + ROS Noetic, repositorio `Atriz_rvr`, plataforma web `Atriz_web_server` (rama `pruebas`), y el `MANUAL SPHERO.docx` con el que se montó el sistema.
**Motivo:** el sistema se percibe lento e ineficiente. Se quiere determinar si existe una base mejor antes de escalar a 16 robots en un laboratorio remoto.

Todas las mediciones citadas son reproducibles y sus salidas crudas están en [`evidencia/`](evidencia/).

---

## Resumen ejecutivo

**El hardware está sano. La lentitud es 100 % de configuración.**

| Indicador | Medición | Lectura |
|---|---|---|
| Temperatura | 59.9 °C estable | Sin throttling (umbral 80 °C) |
| Throttling / under-voltage | **0 eventos** en `dmesg` | Alimentación correcta |
| RAM libre | 4.2 GB de 7.6 GB | La memoria no es el problema |
| Presión de memoria | `some avg300 = 0.00` | Confirmado: no es RAM |
| Lectura de SD | 83.9 MB/s secuencial | Tarjeta razonable |

Lo que sí duele, en orden de impacto:

1. **Un escritorio GNOME completo y duplicado** en un robot headless.
2. **La CPU al 33 % de su velocidad** por el governor `ondemand`.
3. **784 MB de journal sin límite** presionando la microSD.
4. **WiFi con power-save activo** introduciendo latencias erráticas.

Y, con independencia del rendimiento, **dos problemas estructurales**:

- 🔴 El enlace UART del RVR está montado sobre el mini-UART sin `disable-bt`: fallo latente de fiabilidad.
- 🔴 La arquitectura (ROS 1 EOL + `roscore` único + control por SSH con contraseña) tiene un techo real antes de los 16 robots.

---

## 1. Inventario del sistema

| | |
|---|---|
| Placa | Raspberry Pi 4 Model B Rev 1.5, **8 GB** |
| CPU | 4× ARM Cortex-A72, 600–1800 MHz (`arm_boost=1`) |
| SO | Ubuntu **20.04.6** LTS focal — soporte estándar terminado **abril 2025** |
| Kernel | 5.4.0-1129-raspi (arm64) |
| Python | **3.8.10** — EOL upstream octubre 2024 |
| ROS | **Noetic** — EOL **mayo 2025**. 236 paquetes `ros-noetic-*` |
| Almacenamiento | microSD ADATA 32 GB (fab. 11/2024), 12 GB usados de 29 GB |
| Red | WiFi 5 GHz (canal 36, 80 MHz), `192.168.1.200`. Ethernet caído |
| Swap | **Ninguna** (correcto en un robot) |
| Ubuntu Pro | **No conectado** — `esm-infra`, `esm-apps` y el servicio **`ros`** disponibles gratis y sin usar |

> Nota: `ros-noetic-desktop-full`, `ros-noetic-desktop` **y** `ros-noetic-ros-base` están instalados simultáneamente. Para un RVR por UART bastaría `ros-base`.

---

## 2. Rendimiento — hallazgos con evidencia

### P1 · Escritorio GNOME completo, y duplicado

`systemctl get-default` → `graphical.target`.

Hay **dos sesiones gráficas simultáneas**:

| Sesión | Procesos | RSS |
|---|---|---|
| `gdm` | Xorg vt1 + gnome-shell | 69 + **208 MB** |
| `sphero` | Xorg vt2 + gnome-shell | 92 + **395 MB** |

Más ~120 procesos de soporte: `gsd-*`×25, `ibus-*`×6, `gvfs*`×10, `evolution-*`×4, `tracker-miner-fs` (indexando la microSD), `at-spi2`, `colord`, `pulseaudio`. Y residentes sin función: `update-manager` ocupando **174 MB** de Python parado, `update-notifier`, `xrdp` escuchando en **0.0.0.0:3389**.

**273 tareas totales** con ROS parado. `gnome-shell` llegó al **23.5 % de CPU** sin que nadie tocara la pantalla.

Coste en arranque: `gdm.service` 10.8 s + `plymouth-quit-wait` 13.3 s.

> El impacto grave no es la RAM (sobra), sino el **jitter del planificador** — que es precisamente lo que degrada un lazo de control ROS, aunque haya 76.9 % de CPU ociosa.

**Origen:** el manual instala `ubuntu-desktop` y `xrdp` deliberadamente, para poder usar Escritorio Remoto. Es la decisión más cara del documento.

### P2 · La CPU vive al 33 % de su velocidad

Governor `ondemand` en los 4 núcleos, fijado en cada arranque por `ondemand.service`.

Distribución real del tiempo (`time_in_state`, ventana de ~44 min):

| Frecuencia | % del tiempo |
|---|---|
| **600 MHz** | **59.6 %** |
| 700–1700 MHz | 23.7 % |
| 1800 MHz | 16.6 % |

Con 59.9 °C y cero throttling, hay margen térmico de sobra para no bajar nunca de frecuencia. `ondemand` en ARM reacciona tarde, así que **cada acción interactiva empieza a 600 MHz**.

> Es la causa nº1 de la sensación de sistema pastoso con la CPU técnicamente ociosa — y se corrige con una línea.

### P3 · 784 MB de journal machacando la microSD

```
/var/log            789 MB
/var/log/journal    785 MB   (99.5 %, en ~97 ficheros de 8.1 MB)
```

`/etc/systemd/journald.conf` está **completamente vacío**: sin `SystemMaxUse`, sin `Storage=volatile`, sin `RuntimeMaxUse`.

Consecuencia medida en `/proc/pressure`:

```
io      some avg300=0.43   full total = 46_970_402 µs  ← 47 s
cpu     some avg300=0.57   some total = 18_802_527 µs  ← 19 s
memory  some avg300=0.00   total = 0
```

**Casi 47 segundos, en 42 minutos de uptime con el sistema prácticamente ocioso, en los que _todos_ los procesos estuvieron parados esperando a la microSD.** La presión de I/O supera a la de CPU. El disco duele más que el procesador.

Agravantes: `apt-daily.service` (1 min 14 s) y `apt-daily-upgrade.service` (1 min 27 s) martilleando la tarjeta periódicamente, más `tracker-miner-fs` indexando.

> Además del rendimiento, es **desgaste de flash**. Con 16 robots, esto es la diferencia entre tarjetas que duran 3 meses y tarjetas que duran 3 años.

### P4 · WiFi con power-save activo y señal mediocre

```
Signal level = -62 dBm      Link Quality = 48/70
Tx excessive retries = 797   (en 42 min)
Power Management: on
```
Confirmado en el kernel: `brcmfmac: brcmf_cfg80211_set_power_mgmt: power save enabled`.

El ahorro de energía del WiFi introduce **latencias aleatorias de 100–300 ms**. Todo el acceso va por `wlan0` (ethernet caído).

> Si la velocidad del sistema se juzga a través de SSH o de un IDE remoto, **una parte importante de la "lentitud" es esto y no la Pi**.

### P5 · Arranque: cloud-init + snapd + LXD

```
Startup finished in 6.147s (kernel) + 29.470s (userspace) = 35.618s
```

Cadena crítica: `cloud-init-local` 3.69 s → `cloud-init` 2.34 s → `snapd.seeded` **5.11 s** → `cloud-config` 1.96 s, más `cloud-final` 2.07 s, `snapd.service` 6.89 s, `snap.lxd.activate` 4.22 s y `systemd-udev-settle` 2.76 s.

**~20 de los 27 s de userspace** los consumen cloud-init, snapd y LXD. Ninguno aporta nada a un robot. Hay **LXD instalado** y 6 loop devices montados (dos revisiones de cada snap).

### P6 · ~25 servicios habilitados sin función

De 78 unit files activos: `cups` + `cups-browsed` (impresión, escuchando en :631), `ModemManager`, `openvpn`, `iscsi` + `open-iscsi`, `multipath-tools` + `multipathd`, `lvm2-monitor`, `whoopsie`, `kerneloops`, `xrdp` + `xrdp-sesman`, `snap.lxd.activate` + `lxd-agent`×2, `avahi-daemon`, `switcheroo-control` (GPU híbrida inexistente en una Pi), `motd-news` (3.28 s descargando publicidad), `pollinate`, `anacron`, `atd`, `rsync`, `bluetooth` (sin adaptador).

Servicio fallido: `fwupd-refresh.service`.

### P7 · Dos stacks de red compitiendo

Habilitados **a la vez**: `NetworkManager`, `NetworkManager-wait-online`, `networkd-dispatcher`, `systemd-networkd`, `systemd-networkd-wait-online` y `wpa_supplicant`.

`nmcli device status` → `wlan0 wifi unavailable`: NetworkManager corre pero **no gestiona nada** (la WiFi la lleva netplan/systemd-networkd). En el journal, **6 ciclos** de:
```
wpa_supplicant: Failed to initialize control interface '/run/wpa_supplicant'
NetworkManager: sup-iface[wlan0]: wpa_supplicant couldn't grab this interface
```

### P8 · Menor — reloj sin RTC y parámetros muertos

`who -b` reporta `system boot 1970-01-01`; `last reboot` muestra sesiones de "20581 días". La Pi no tiene RTC y `fixrtc` no resuelve bien la hora inicial, lo que corrompe las marcas de tiempo de wtmp/journal antes de que NTP sincronice — y puede confundir a herramientas ROS que usan tiempo de pared.

`elevator=deadline` en `cmdline.txt` es **obsoleto e ignorado** en kernel 5.4 con blk-mq. `vm.swappiness=60` sin swap es un valor sin efecto. `vcgencmd` no está instalado (falta `libraspberrypi-bin`), lo que impide diagnosticar throttling y voltaje de forma nativa.

---

## 3. 🔴 El enlace UART — fallo funcional latente

Este es el hallazgo más importante del informe, e **independiente del rendimiento**.

### Qué pasa

El manual **nunca toca `/boot/firmware/config.txt`**. No existe `dtoverlay=disable-bt` en ningún fichero de arranque, y `usercfg.txt` —el lugar previsto para los cambios del usuario— está **completamente vacío**.

Sin `disable-bt`, el reparto de UARTs en la Pi 4 es:

| UART | Hardware | Asignación |
|---|---|---|
| `ttyAMA0` | **PL011** — FIFO de 32 B, reloj estable | reservado al **Bluetooth** |
| `ttyS0` | **mini-UART** 16550 — FIFO de 8 B | GPIO14/15 → **el RVR** |

El mini-UART **deriva su baudrate del reloj del núcleo VPU**, que es variable. Sin `core_freq` fijo, el baudrate real deriva cuando el VPU cambia de frecuencia → **bytes corruptos, checksums inválidos y desconexiones intermitentes**.

### Lo absurdo de la situación

```
bluetooth.service   active (running) since 2026-05-08; 2 months 21 days ago
hciconfig -a        (sin salida — ningún controlador hci registrado)
```

**`bluetoothd` lleva 2 meses y 21 días corriendo sin ningún adaptador adjunto**, y a la vez el device-tree mantiene el PL011 reservado para ese Bluetooth. Se paga el coste sin obtener el beneficio.

### `/dev/serial0` no existe en Ubuntu

```
ls /dev/serial*  →  No such file or directory
```
A diferencia de Raspberry Pi OS, Ubuntu **no instala las reglas udev** que crean ese symlink. Cualquier código que lo abra falla. El manual lo menciona como si existiera.

### El puerto está hardcodeado en 4 sitios

| Fichero | Línea |
|---|---|
| `sphero_sdk/asyncio/client/dal/serial_async_dal.py` | 15 |
| `sphero_sdk/observer/client/dal/serial_observer_dal.py` | 17 |
| `atriz_rvr_driver/src/sphero_rvr_hw_interface.cpp` | 29 |
| `atriz_rvr_driver/src/base_controller.cpp` | 40 |

Siempre `/dev/ttyS0` @ 115200, sin forma de cambiarlo por parámetro ROS ni por launch arg.

### Lo que sí está bien

- `enable_uart=1` presente.
- `cmdline.txt` usa `console=tty1`, sin `console=serial0` — el manual acierta aquí.
- `serial-getty@ttyS0` y `@ttyAMA0` ambos `disabled`.
- El usuario `sphero` está en `dialout`, `gpio`, `spi`, `i2c`, `video`, `render`, `netdev`.

### Corrección

```
# /boot/firmware/usercfg.txt
dtoverlay=disable-bt
enable_uart=1
```
```
# /etc/udev/rules.d/99-rvr.rules
SUBSYSTEM=="tty", KERNEL=="ttyAMA0", SYMLINK+="rvr", MODE="0660", GROUP="dialout"
```
Deshabilitar `bluetooth.service` y `serial-getty@ttyAMA0`. Todo el código pasa a `/dev/rvr`.

`disable-bt` devuelve el **PL011 a GPIO14/15**, cuyo reloj no depende del VPU: elimina el problema de raíz, mejor que fijar `core_freq`.

---

## 4. Auditoría del código — `Atriz_rvr`

Workspace catkin clásico en `~/atriz_git`, con un único repo git en `src/Atriz_rvr`. Tres paquetes: `atriz_rvr_driver` (híbrido C++/Python), `atriz_rvr_msgs` (6 msg + 19 srv), `atriz_rvr_serial` (fork de `wjwwood/serial`). Último commit: 15-oct-2025.

### 4.1 🔴 Roto ahora mismo

**El LIDAR no existe.** `find /home/sphero /opt/ros -iname "*ydlidar*"` → **0 resultados**. Ni `ydlidar_ros_driver` ni `YDLidar-SDK` están en el sistema, pese a que `LIDAR_INTEGRATION_SUMMARY.md` (líneas 17-25) afirma que sí y 3 launch files los invocan. `roslaunch atriz_rvr_driver lidar_only.launch` **falla**.

**El árbol TF está partido en dos.** El driver publica `odom → rvr_base_link` (`Atriz_rvr_node.py:96`); el LIDAR cuelga de `base_link` vía `static_transform_publisher`. **Sin puente entre ambos** → cualquier SLAM o navegación es imposible.

**No hay URDF ni xacro** en todo el repo, pese a que `sphero_rvr_hw_interface.cpp:337` implementa `loadURDF()` y el CMake depende de `urdf`. Tampoco hay ningún `.rviz`.

**Scripts sin bit de ejecución referenciados en launch files:** `rvr-ros.py`, `emergency_stop.py`, `cmd_vel_rviz.py` → `roslaunch` falla con "cannot launch node ... not executable".

**Ficheros inexistentes referenciados:** `test_new_functionalities.py`, `rvr-ros-sim.py`, `scripts/sphero_sim/`, `scripts/core/`, `pyrightconfig.json`.

**`SetPosAndYaw.srv`** existe en disco pero **no está en `add_service_files()`** → nunca se genera.

### 4.2 Rendimiento del driver

**Anti-patrón estructural** (`Atriz_rvr_node.py:1633-1642`):
```python
asyncio.ensure_future(rvr_robot())
while not rospy.is_shutdown():
    loop.run_until_complete(asyncio.gather(handle_ros()))
    r.sleep()   # 15 Hz
```
`handle_ros()` termina con `await asyncio.sleep(0.1)`, y el `r.sleep()` añade otros ~66 ms. El event loop de asyncio **solo avanza mientras `run_until_complete` está activo**, así que los callbacks del SDK (streaming serie de sensores) se procesan **en ráfagas de ~100 ms cada ~166 ms**.

Combinado con `sensor_control.start(interval=250)` (línea 1280), el resultado es **odometría real a ~4 Hz con jitter alto**. Es la causa estructural de la latencia en `/odom` e `/imu`.

**`asyncio.run()` dentro de callbacks ROS síncronos.** `cmd_vel_callback:248` hace `asyncio.run(write_rc_si(...))`, y hay ~10 llamadas más (líneas 305, 323, 1116, 1126, 1515, 1519, 1528, 1532…). `asyncio.run()` **crea y destruye un event loop nuevo en cada llamada**, coexistiendo con el loop global. Varias son `asyncio.run(asyncio.sleep(.1))`, que es un `time.sleep(0.1)` carísimo.

**Busy-wait sin timeout.** `wait_until_motion_complete()` (línea 1544) espera a 10 Hz sin límite: si el evento `on_xy_handler` no llega, bloquea el hilo del servicio indefinidamente.

**Frecuencias contradictorias:** `hardware_interfaces.yaml` declara `loop_hz: 300`; el código C++ usa `20.0`. `cmd_vel_rviz.py:88` usa `rospy.Rate(60)` con un comentario que dice "0.1 Hz".

### 4.3 Correctitud

**Unidades (viola REP-103).** `gyroscope_handler` (líneas 911-922) llama a `check_if_need_to_send_msg('gyroscope')` **dos veces**: primero con deg/s (línea 916) y luego con rad/s (línea 922). La primera llamada puede disparar la publicación de `/odom` con la velocidad angular **en grados por segundo**. Además `imu.angular_velocity` queda **siempre** en deg/s, porque nunca se reasigna tras la conversión.

**Timestamp cero.** `light_handler` usa `msg.header.stamp = rospy.Time()` en vez de `rospy.Time.now()`.

**Config errónea.** `controller.maybe.config.yaml`: el joint `sphero_rvr_wheel_rl_joint` está **duplicado** y falta `_rr_`.

**Dependencia inexistente.** `package.xml` declara `joint_limit_interface` (singular); el paquete real es `joint_limits_interface`. `rosdep` falla.

**Paquete fantasma.** `setup.py` declara `packages=['sphero_sdk', 'sphero_sim']` pero `scripts/sphero_sim/` no existe.

### 4.4 Higiene

- `build/` y `devel/` conservan artefactos del **nombre antiguo** del proyecto: `ros_sphero_rvr`, `sphero_rvr_hw`, `sphero_rvr_msgs`. Nunca se limpiaron tras el rename.
- Carpeta huérfana `sphero_rvr_hw/scripts/` con 4 scripts, **sin `package.xml` ni `CMakeLists.txt`** → catkin no la ve.
- Sin `requirements.txt`, `Pipfile` ni `pyproject.toml`.
- 6 cambios sin commitear, incluido `.fw` (un fichero de timestamp que no debería estar versionado) y `carro.py` (0 bytes).

### 4.5 ✅ El SDK de Sphero — la buena noticia

Análisis del SDK vendorizado (`atriz_rvr_driver/scripts/sphero_sdk/`, 103 ficheros, 1.3 MB):

| Comprobación | Resultado |
|---|---|
| Imports de `rospy` / `rclpy` | **0** — el SDK es 100 % agnóstico a ROS |
| `@asyncio.coroutine` (eliminado en Python 3.11) | **0** |
| kwarg `loop=` (eliminado en 3.10) | **0** |
| `yield from` en corrutinas | **0** |
| `asyncio.get_event_loop()` | **4** — y 3 están en el backend `observer`, que no se usa |

Dependencias externas: `pyserial`, `pyserial-asyncio`, `aiohttp`, `dbussy`/`ravel` (BLE, opcional). Todas vivas en Python 3.12.

> **Conclusión:** el único punto real en la ruta que se usa es `sphero_rvr_async.py:35`. Portar el SDK a Python 3.12 es un parche de ~4 líneas, no una reescritura. Esto elimina el principal riesgo percibido de migrar a ROS 2.

---

## 5. Auditoría de la plataforma web — `Atriz_web_server` (rama `pruebas`)

Vue 3 + FastAPI + SQLAlchemy. El repositorio es además un workspace catkin, con paquetes heredados de otro robot (`box_pushing`, `mapping`, `path_planning`, `robotnik_msgs`, `robotnik_sensors`).

### 5.1 🔴 Credenciales en texto plano en un repositorio público

`swarm_lab_api/app/core/raspberry_config.py`:
```python
RASPBERRY_PI_CONFIGS = [
    {"host": "10.20.50.29", "username": "sphero", "password": "<REDACTADO>"},
    {"host": "10.20.50.24", "username": "ubuntu", "password": "<REDACTADO>"},
]
```
Es la misma credencial del manual. **Debe considerarse comprometida y rotarse.**

Además están commiteados `swarm_lab_env/` (un venv completo, **5418 ficheros**), `node_modules/`, `build/` y `devel/`.

### 5.2 🔴 La parada de emergencia probablemente no funciona

| | Topic |
|---|---|
| La web publica en | `/rvr/emergency_stop` (`app/api/robots.py`) |
| El driver escucha | `is_emergency_stop` (`Atriz_rvr_node.py:1599`) |

**Nombres distintos.** A menos que exista un remap que no se ha encontrado, **el botón de parada de emergencia del panel no hace nada**.

> Debe verificarse en banco como prioridad absoluta. Es seguridad, no funcionalidad.

### 5.3 🔴 No hay watchdog

Ningún componente detiene el robot si se pierde la conexión. En un laboratorio remoto, sobre un WiFi que registra 797 reintentos en 42 minutos, esto significa que **un corte de red deja el robot conduciendo**.

### 5.4 La arquitectura de control no escala

```python
ssh_command = ["ssh", f"{user}@{robot_ip}", "source /opt/ros/noetic/...; {command}"]
subprocess.Popen(ssh_command); process.communicate()   # bloqueante
```

- Cada lectura de telemetría es **un proceso SSH nuevo**. No hay streaming.
- `execute_command_on_multiple_robots` recorre los robots en un **`for` secuencial** con `timeout=4.0` cada uno → con 16 robots, hasta **64 s** por comando, con el proceso FastAPI bloqueado.
- **No hay rosbridge ni websockets** en ninguno de los dos repositorios. (`websocket-client` y `aiohttp` están en pip, pero no los importa ningún fichero del proyecto — son dependencias arrastradas del SDK.)
- El vídeo espera **MJPEG vía `web_video_server`**, que no está instalado en el robot. *(Confirmado con el usuario: los robots no llevan cámara.)*
- Las IPs `10.20.50.x` están hardcodeadas; esta Pi está en `192.168.1.200`.

---

## 6. Deriva entre documentación y código

La documentación del repo describe un sistema que no existe, lo que hace perder horas:

| Documento | Afirma | Realidad |
|---|---|---|
| `LIDAR_INTEGRATION_SUMMARY.md` | Existen `src/ydlidar_ros_driver/` y `src/YDLidar-SDK/` | **No existen** |
| `README.md` | `scripts/core/Atriz_rvr_node.py`, `pyrightconfig.json` | No existen |
| `README.md` | Ruta `atriz_git/src/ros_sphero_rvr/` | Nombre antiguo |
| `test_functionalities.launch` | `test_new_functionalities.py` | No existe |
| `hw_controller.launch` | `rvr-ros-sim.py` | No existe |
| `MANUAL SPHERO.docx` | `rosrun sphero_rvr_hw ...` | Paquete renombrado a `atriz_rvr_driver` |

El manual además deja como pendientes sin desarrollar: automatización de arranque, IPs estáticas, YDLIDAR, tracking del lidar y app web — **exactamente lo que hoy está ausente o roto**.

---

## 7. Conclusiones

**Sobre la lentitud.** No es hardware. Con las correcciones de la §2 esta misma Pi va notablemente mejor: boot de 29 s a menos de 15 s de userspace, de 273 tareas a menos de 120, y la CPU dejando de vivir a 600 MHz.

**Sobre la fiabilidad.** El UART sobre mini-UART sin `disable-bt` es un fallo latente que produce síntomas intermitentes difíciles de atribuir. Debe corregirse con independencia de cualquier otra decisión.

**Sobre escalar a 16 robots.** Hay un techo arquitectónico real: ROS Noetic EOL, un `roscore` único como punto de fallo, control por SSH secuencial con contraseña, y sin telemetría en streaming. No es cuestión de optimizar; es cuestión de cambiar de base.

**Sobre migrar a ROS 2.** El análisis del SDK (§4.5) elimina el principal riesgo: la parte difícil es agnóstica a ROS y está limpia para Python 3.12. Y todo lo que hoy *falta* —driver YDLIDAR, SLAM, navegación, rosbridge, multi-robot— está mejor soportado en ROS 2 que en ROS 1. Lo único que se pierde, la capa C++ `ros_control`, **ya es código muerto que no se ejecuta**.

El plan de migración derivado de este informe está en [`../01_plan/PLAN_MIGRACION_ROS2.md`](../01_plan/PLAN_MIGRACION_ROS2.md).

---

## Correcciones tras verificar en banco

El informe original se escribió por **análisis estático** sobre un clon local que, se descubrió después, estaba **5 commits por detrás de GitHub** y en el que **nunca se había ejecutado `git fetch`**. Al contrastar contra `origin/main` (`659364c`) y, sobre todo, al **medir sobre el robot real**, tres hallazgos resultaron equivocados.

Se dejan aquí en lugar de borrarlos: saber qué falló el análisis estático es tan útil como el análisis mismo.

### ❌ C1 — «Odometría a ~4 Hz **con jitter alto**» por el anti-patrón del event loop

**Lo que decía §4.2:** que el bucle `while` + `run_until_complete()` + `asyncio.sleep(0.1)` procesaba los callbacks del SDK a ráfagas, causando latencia y jitter.

**Lo medido:** la frecuencia era correcta (3.85 Hz), pero **el jitter es de σ = 1.7 ms** sobre una mediana de 259.9 ms. Es extraordinariamente estable, no errático.

**Y la atribución era falsa.** Midiendo a nivel del SDK, **sin ROS de por medio**, el resultado es idéntico:

| Configuración | Frecuencia | Mediana | σ |
|---|---|---|---|
| `interval=250`, SDK solo (sin ROS) | 3.85 Hz | 260.0 ms | 1.1 ms |
| `interval=250`, a través del nodo ROS | 3.85 Hz | 259.9 ms | 1.7 ms |

El nodo no añadía prácticamente nada. Los 4 Hz venían **solo** de `sensor_control.start(interval=250)`.

**Consecuencia práctica — el arreglo era una línea, no una reescritura.** Barrido del intervalo con los 8 sensores del driver:

| `interval` | Real | Frecuencia | σ |
|---|---|---|---|
| 250 ms | 260.0 ms | 3.85 Hz | 1.7 ms |
| 200 ms | 199.9 ms | 5.00 Hz | 0.6 ms |
| 150 ms | 160.1 ms | 6.25 Hz | 0.8 ms |
| 100 ms | 100.1 ms | 9.94 Hz | 2.4 ms |
| **60 ms** | **60.1 ms** | **16.59 Hz** | **2.8 ms** |
| 50 ms | — | el streaming **no arranca** | — |

El firmware del RVR **cuantiza a múltiplos de 20 ms** (250 → 260 reales, 150 → 160). Por debajo de 60 ms no arranca.

Y la prueba definitiva: **el nodo ROS transmite los 16.59 Hz sin degradarlos** (σ 2.8 ms). Si el event loop fuera el cuello de botella, a 60 ms se habría notado. No se nota.

> **Riesgo del plan cerrado.** El plan listaba como riesgo «115200 baud no aguanta 20 Hz». Medido: 125 paquetes/s a 60 ms, holgado para ~11.5 KB/s. Los seis sensores de odometría van a 16.5 Hz; `ambient_light` y `color_detection`, más lentos, se quedan en 13 Hz.
>
> **La reestructuración del event loop deja de ser prioritaria.** Sigue siendo deseable en el port a `rclpy` por limpieza y por las 48 llamadas a `asyncio.run()` en callbacks, pero **el impacto de esas 48 llamadas en la latencia de `cmd_vel` NO se ha medido** y no debe afirmarse sin datos.

### ❌ C2 — «`SetPosAndYaw.srv` no está registrado en `add_service_files()`»

**Falso en `origin/main`.** Está registrado (línea 8 de `atriz_rvr_msgs/CMakeLists.txt`) y `_SetPosAndYaw.py` se genera correctamente. Era un artefacto del código obsoleto. **Hallazgo retirado.**

### ❌ C3 — «No hay integración con el LIDAR»

**Impreciso.** En `origin/main` existen `obstacle_avoidance.py` (300 líneas; se suscribe a `/scan`, publica `/cmd_vel`, escucha `/is_emergency_stop`) y `rvr_with_lidar_autonomous.launch`.

**Lo que sí sigue siendo cierto** —y es un hecho del sistema, no del repositorio— es que el paquete `ydlidar_ros_driver` **no está instalado en esta Pi**, así que ese launch no puede arrancar. Y el árbol TF sigue partido.

### ⚠️ C4 — Los números de línea de todo el informe

`Atriz_rvr_node.py` creció 160 líneas entre el clon local y `origin/main`. **Todas las referencias `fichero:línea` del informe apuntan al código antiguo.** Las verificadas contra `origin/main`:

| Hallazgo | Línea en `origin/main` |
|---|---|
| `child_frame_id='rvr_base_link'` | 99 |
| `check_if_need_to_send_msg('gyroscope')` duplicado | 935 y 940 |
| `sensor_control.start(interval=...)` | 1313 |
| `wait_until_motion_complete()` sin timeout | 1568 |
| Bucle principal | 1661–1672 |

### ✅ Lo que sí se confirmó contra `origin/main`

Bucle principal con `run_until_complete` dentro del `while`; `asyncio.run()` en callbacks (**y empeoró: de ~10 a 48 ocurrencias**); doble llamada deg/s + rad/s en `gyroscope_handler`; `wait_until_motion_complete()` sin timeout; TF partido entre `rvr_base_link` y `base_link`; `/dev/ttyS0` hardcodeado en los mismos sitios; y el driver del YDLIDAR ausente del sistema.

**Hallazgo nuevo, no presente en el informe original:** `rvr_fw_check_async.py` captura `except (asyncio.TimeoutError, Exception)` y **continúa en silencio**. El resultado es que el arranque *parece* correcto aunque el RVR no responda: se pierden 10 s en dos timeouts y no se advierte de nada. Es un falso positivo que puede costar horas de diagnóstico — de hecho costó un rato durante esta verificación.

### Sobre el UART — una falsa alarma que conviene documentar

Tras aplicar `dtoverlay=disable-bt` se observó que `uart0_pins` queda con `brcm,pins` **vacío** (0 bytes) en el device-tree, y que el mini-UART pasa a `disabled`. Se interpretó como que ningún UART quedaba enrutado a GPIO14/15.

**Era una falsa alarma.** Al decompilar el overlay (`dtc -I dtb -O dts disable-bt.dtbo`) se ve que **vacía `uart0_pins` a propósito**: en Raspberry Pi es el *firmware* quien asigna los pines al ver `enable_uart=1`, y el kernel no debe tocarlos. Verificado en la práctica: con el robot encendido, el RVR responde con paquetes de checksum válido sobre `/dev/rvr` → `ttyAMA0` (PL011).

**La causa real de los «cero bytes» era que el robot estaba dormido.** Encenderlo lo resolvió.

---

## Anexo — cómo reproducir estas mediciones

Las salidas crudas están en [`evidencia/`](evidencia/), capturadas el 2026-07-29:

| Fichero | Contenido |
|---|---|
| `01_hardware_so.txt` | os-release, uname, modelo, lscpu, free, swap, df, lsblk, id |
| `02_boot_servicios.txt` | systemd-analyze, blame, critical-chain, unit-files, failed |
| `03_rendimiento.txt` | pressure io/cpu/memory, governor, **time_in_state**, temperatura, ps |
| `04_uart_serial.txt` | dispositivos tty, cmdline/config/syscfg/usercfg, udev, bluetooth, dmesg |
| `05_red.txt` | ip, iw, wireless, power_save, nmcli, puertos a la escucha |
| `06_software.txt` | python, ROS, pip3, snap, apt upgradable, ubuntu pro |
| `07_logs.txt` | journal disk-usage, journald.conf, errores del boot, dmesg |

Para comparar **después** de la migración, basta volver a ejecutar el mismo bloque de comandos y diffear. Los indicadores clave a vigilar:

```bash
systemd-analyze                                       # userspace
ps -e | wc -l                                         # nº de tareas
cat /proc/pressure/io                                 # full total
cat /sys/devices/system/cpu/cpu0/cpufreq/stats/time_in_state   # % a 600 MHz
journalctl --disk-usage                               # tamaño del journal
iw dev wlan0 get power_save                           # debe decir 'off'
ls -l /dev/rvr                                        # debe apuntar a ttyAMA0
```
