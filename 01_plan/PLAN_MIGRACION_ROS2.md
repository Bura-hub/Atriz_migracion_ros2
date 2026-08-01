# Plan: Migración del sistema Atriz RVR a ROS 2 Jazzy y escalado a 16 robots

## Contexto

Hoy existe **una** Raspberry Pi 4B (8 GB) con Ubuntu 20.04 + ROS Noetic que controla un Sphero RVR por UART, con un YDLIDAR X2 añadido recientemente. El objetivo final es un **laboratorio remoto** con 16 robots idénticos, gobernados desde la plataforma web `Atriz_web_server`.

La auditoría del sistema encontró tres problemas de naturaleza distinta:

1. **Lentitud percibida — es 100% configuración, no hardware.** El hardware está sano: 59.9 °C estable, cero throttling, cero under-voltage, 4.2 GB de RAM libre. Lo que duele es un escritorio GNOME completo *y duplicado* (dos Xorg + dos gnome-shell, ~120 procesos GUI), el governor `ondemand` dejando la CPU a 600 MHz el **59.6 %** del tiempo, y 784 MB de journal sin límite generando **47 s de bloqueo total por I/O en 42 min** de sistema ocioso.

2. **Un fallo funcional latente en el enlace UART.** No existe `dtoverlay=disable-bt` en ninguna parte — el manual nunca toca `config.txt`. El PL011 (`ttyAMA0`, el UART bueno) está reservado a un Bluetooth **sin adaptador registrado** (`hciconfig -a` vacío, `bluetoothd` lleva 2 meses y 21 días corriendo para nada), y el RVR habla por el mini-UART `ttyS0`, cuyo baudrate deriva del reloj VPU. Es la causa clásica de tramas corruptas y desconexiones intermitentes.

3. **Un techo arquitectónico para la flota.** ROS Noetic está EOL (mayo 2025), Ubuntu 20.04 fuera de soporte estándar (abril 2025). Un solo `roscore` es punto único de fallo para 16 robots. La plataforma web controla los robots por `subprocess.run(["ssh", ...])` en un bucle serie con contraseñas en texto plano commiteadas en GitHub público, sin telemetría en streaming.

**Decisión tomada:** migrar a **Ubuntu 24.04 LTS + ROS 2 Jazzy** (soporte hasta mayo 2029) **reinstalando sobre esta misma microSD**. La web pasará a hablar por **rosbridge + roslibjs**. Hardware reutilizado: Pi 4 + microSD. Sin cámara en los robots.

**Estrategia de reversión (decisión del usuario):** no se compra tarjeta nueva. Si la migración no funciona, se reflashea la SD y se rehace el sistema siguiendo el manual antiguo. Por eso este documento y los entregables de la Fase 7 son **parte crítica del plan, no un extra**: son lo que hace que esa reversión sea de horas y no de días. Antes de tocar nada se hace una **imagen completa de la SD actual** (Fase 0.3) — cuesta 20 minutos y convierte "rehacer el manual entero" en "restaurar una imagen".

**Por qué ROS 2 no supone perder alcance** (verificado sobre el propio código):
- El SDK del RVR (103 ficheros, 1.3 MB) tiene **cero** imports de ROS, **cero** `@asyncio.coroutine`, **cero** kwargs `loop=`, **cero** `yield from`. Solo 4 `asyncio.get_event_loop()`, y 3 están en el backend `observer` que no se usa. Portarlo a Python 3.12 es un parche de ~4 líneas.
- Todo lo que hoy *falta* (driver YDLIDAR, SLAM, navegación, rosbridge, multi-robot) está mejor soportado en ROS 2.
- Lo único que se "pierde" —la capa C++ `ros_control`— ya es código muerto: no se ejecuta, y `hw_controller.launch` apunta a `rvr-ros.py`, que ni siquiera tiene bit de ejecución.

---

## Fase 00 — Repositorio de seguimiento (PRIMER PASO, antes que nada)

Todo lo producido en esta auditoría vive hoy únicamente en la SD que se va a borrar, y en un chat que no sobrevive al reinicio. Antes de tocar una sola línea del sistema, se materializa en una carpeta con git y se sube a GitHub. A partir de ahí el proyecto se puede seguir desde cualquier máquina, sobreviva o no esta Pi.

**Ubicación local:** `/home/sphero/atriz_migracion/` → **`github.com/Bura-hub/Atriz_migracion_ros2`** (repo nuevo, independiente de `Atriz_rvr` y de `Atriz_web_server`, porque documenta la transición entre ambos y debe seguir siendo legible aunque esos dos cambien de rama o de estructura).

```
atriz_migracion/
├── README.md                    Índice, estado actual del proyecto, cómo usar este repo
├── CHANGELOG.md                 Bitácora fechada: qué se hizo en cada sesión y qué quedó pendiente
├── 00_auditoria/
│   ├── INFORME_AUDITORIA.md     La auditoría completa con todas las mediciones
│   └── evidencia/               Salidas CRUDAS de los comandos, para poder comparar después:
│                                systemd-analyze blame, time_in_state, pressure/io, iwconfig,
│                                lsblk, dpkg -l, pip3 list, config.txt, cmdline.txt, syscfg.txt,
│                                usercfg.txt, systemctl list-unit-files --state=enabled
├── 01_plan/
│   └── PLAN_MIGRACION_ROS2.md   Este plan
├── 02_manual/
│   ├── MANUAL_SPHERO_original.docx        Copia intacta del manual (5.6 MB) — es el plan B
│   ├── MANUAL_SPHERO_transcripcion.md     Su texto completo en Markdown, buscable y diffeable
│   └── MANUAL_ATRIZ_ROS2.md               El manual nuevo (se escribe en las fases 1–5)
├── 03_operacion/                RUNBOOK.md · RECUPERACION.md · ARQUITECTURA.md · FLOTA.md
└── 04_respaldo/
    ├── configs/                 netplan, udev, .bashrc, fstab actuales
    └── sin_commitear/           Los 6 ficheros modificados/nuevos de Atriz_rvr que se perderían
```

**Por qué la transcripción del manual además del `.docx`:** el binario de Word no se puede diffear ni buscar desde un servidor, y es el único registro de cómo se montó el sistema actual. La transcripción en Markdown lo hace utilizable; el `.docx` original se conserva intacto porque es el procedimiento de reversión.

**Reglas:**
- **Sin secretos.** Nada de credenciales, claves SSH ni `.env`. La contraseña ya está expuesta en `Atriz_web_server` público; no se replica el error. `.gitignore` con `*.key`, `.env`, `id_*`.
- El `CHANGELOG.md` se actualiza al final de **cada** sesión de trabajo, aunque sea una línea. Es lo que permite retomar el hilo semanas después.
- Cada fase completada se commitea antes de empezar la siguiente.

**Verificación:** `git log` en el remoto muestra el commit inicial; clonar el repo en otra máquina y comprobar que el `README.md` basta para entender en qué punto está el proyecto sin más contexto.

---

## Arquitectura objetivo

### Aislamiento DDS: un `ROS_DOMAIN_ID` por robot

Es la decisión estructural más importante del plan. **No** poner los 16 robots en el mismo dominio DDS con namespaces: el descubrimiento multicast de DDS entre ~160 participantes sobre WiFi genera una tormenta de tráfico que satura la red (y esta Pi ya registra **797 reintentos Tx en 42 min** con un solo robot).

```
Robot 01: ROS_DOMAIN_ID=1,  ws://rvr-01.local:9090  ─┐
Robot 02: ROS_DOMAIN_ID=2,  ws://rvr-02.local:9090  ─┤  16 WebSockets
   ...                                               ├─► Servidor web
Robot 16: ROS_DOMAIN_ID=16, ws://rvr-16.local:9090  ─┘   (FastAPI + Vue)

   SIN NAMESPACE: los topics son /odom, /scan, /cmd_vel_raw.
   El robot lo identifica la CONEXIÓN, no el nombre del topic.
```

> ✅ **SIN NAMESPACE — decisión cerrada el 2026-08-01.** Este diagrama decía
> `namespace /rvr_01`. Con un `ROS_DOMAIN_ID` por robot el aislamiento ya es total, y la web
> abre **un WebSocket por robot**: poner `/rvr_07/odom` dentro de un canal que solo alcanza al
> robot 7 es escribir el número dos veces. 🔴 Y pesa más otra cosa: **la parada de emergencia ya
> falló una vez por un namespace** — se coló un `/rvr/` al portar de ROS 1 y falló en silencio
> con `200 OK`. `ARQUITECTURA.md` y manual cap. 19.
>
> ⚠️ **Y resuelven la localización por `rvr-NN.local` (mDNS)**, no por IP: es lo que hace que el
> mismo código funcione en casa y en el laboratorio. Verificado desde el PC del usuario.

Cada robot es una isla DDS completa. La coordinación (experimentos tipo `box_pushing`) ocurre en la capa de aplicación del servidor, que es además mucho más depurable. **Escape hatch documentado:** si más adelante hace falta comunicación robot-a-robot real en DDS, se añade `zenoh-bridge-ros2dds` o un FastDDS Discovery Server, sin rehacer nada de lo anterior.

### Stack por robot

```
Ubuntu Server 24.04 LTS arm64 (headless, multi-user.target)
└── ROS 2 Jazzy (ros-base, NO desktop)
    ├── atriz_rvr_driver      (rclpy) → /odom /imu /battery_state /color /encoders
    │                                    /ambient_light /motor_status ; ← /cmd_vel
    ├── collision_monitor     /cmd_vel_raw (web) → /cmd_vel (driver)  ← LA SEGURIDAD VA AQUÍ
    ├── rosbridge_websocket   :9090, dentro del launch para heredar ROS_DOMAIN_ID
    ├── atriz_rvr_description (URDF/xacro) + robot_state_publisher
    ├── ydlidar_ros2_driver   → /scan
    ├── slam_toolbox          (async) → /map
    ├── nav2                  → navegación autónoma
    └── rosbridge_server      :9090 (WebSocket) ← único punto de contacto con la web
```

---

## Fase 0 — Validar sobre el sistema actual antes de reinstalar (~2 h)

> ✅ **§0.1 COMPLETADA el 2026-07-29.** UART sobre PL011 vía `/dev/rvr`, verificado con
> paquetes crudos de checksum válido. De paso se midió y corrigió la frecuencia de
> odometría (3.85 → 16.59 Hz). Commits `67c8776` y `24c7749` en la rama
> `migracion-ros2` de `Atriz_rvr`. **Pendientes: §0.3 (imagen de respaldo, bloqueante)
> y la prueba de estabilidad larga.**

Como la SD se va a reflashear, aquí **no se persigue dejar bonito el sistema viejo**: se persigue *validar en un entorno que ya funciona* la única configuración cuyo fallo sería ambiguo después de reinstalar. Si el RVR falla tras la migración, hay que poder descartar que la causa sea el cableado o el UART.

El resto de la higiene del SO (§0.2) **no se aplica aquí** — se documenta como receta y se aplica una sola vez en la Fase 1, ya sobre 24.04.

### 0.1 Reparar y validar el UART — lo único obligatorio de esta fase

En `/boot/firmware/usercfg.txt` (hoy **vacío**):
```
dtoverlay=disable-bt
enable_uart=1
```
`disable-bt` devuelve el **PL011 a GPIO14/15**, cuyo reloj es estable — esto elimina de raíz el problema del baudrate derivante, mejor que fijar `core_freq`.

Luego: deshabilitar `bluetooth.service` y `serial-getty@ttyAMA0`, y crear un symlink estable en `/etc/udev/rules.d/99-rvr.rules`:
```
SUBSYSTEM=="tty", KERNEL=="ttyAMA0", SYMLINK+="rvr", MODE="0660", GROUP="dialout"
```
Todo el código pasará a usar `/dev/rvr`, nunca `/dev/ttyS0` ni `/dev/ttyAMA0`. Hoy `/dev/ttyS0` está hardcodeado en 4 sitios: `sphero_sdk/asyncio/client/dal/serial_async_dal.py:15`, `sphero_sdk/observer/client/dal/serial_observer_dal.py:17`, `src/sphero_rvr_hw_interface.cpp:29`, `src/base_controller.cpp:40`.

**Verificación (esta es la prueba que de verdad importa):** `ls -l /dev/rvr` apunta a `ttyAMA0`; el driver conecta apuntando a `/dev/rvr`; `rostopic echo /odom` fluye **sin gaps durante 10 min seguidos** y la teleoperación no se corta. Si esto pasa, el cableado TX/RX/GND y el enlace serie quedan descartados como sospechosos para siempre — y esa certeza vale más que el resto de la Fase 0.

Anotar también, para poder comparar después de migrar:
```bash
systemd-analyze; free -h; cat /proc/pressure/io
ps aux --sort=-%mem | head -10
awk '{s+=$2} END {print s}' /sys/devices/system/cpu/cpu0/cpufreq/stats/time_in_state
```

### 0.2 Receta de higiene del SO — se documenta ahora, se aplica en la Fase 1

| Acción | Evidencia que lo motiva |
|---|---|
| `systemctl set-default multi-user.target`; deshabilitar `gdm` | dos Xorg + dos gnome-shell (208 + 395 MB), 273 tareas |
| Governor a `performance` (unidad systemd) | 59.6 % del tiempo a 600 MHz, con 60 °C y cero throttling |
| `journald.conf`: `SystemMaxUse=32M` + `Storage=volatile` | 784 MB de journal, `io.full total = 46.97 s` en 42 min |
| WiFi power-save OFF (`iw dev wlan0 set power_save off` persistente) | `Power Management: on`, 797 reintentos Tx, latencias de 100–300 ms |
| Purgar: `ubuntu-desktop`, `xrdp`, `cups*`, `ModemManager`, `whoopsie`, `switcheroo-control`, `openvpn`, `iscsi*`, `multipath*`, `snapd`+`lxd`, `tracker-*`, `evolution-*` | ~25 servicios inútiles; LXD en un robot; 6 loop devices |
| Deshabilitar `cloud-init` (`/etc/cloud/cloud-init.disabled`) | ~20 de los 27 s de userspace del boot |
| Desactivar timers `apt-daily` / `apt-daily-upgrade` | 1min27s + 1min14s martilleando la SD |
| Resolver el conflicto NetworkManager ↔ systemd-networkd (quedarse con **uno**) | 6 ciclos de `wpa_supplicant couldn't grab this interface` en el journal |
| `noatime` en `/etc/fstab` | longevidad de la microSD |
| Enganchar **Ubuntu Pro** (gratis ≤5 máquinas: `esm-infra` + `esm-apps` + servicio **`ros`**) | focal EOL, Noetic EOL, máquina sin ESM |

Nota: instalando **Ubuntu Server** (Fase 1) la mayoría de estas purgas dejan de hacer falta — no habrá GNOME, ni xrdp, ni `desktop-full`. La tabla se conserva porque documenta **por qué** el sistema actual iba lento, y porque `cloud-init`, `snapd`, los timers de `apt` y el conflicto de red **sí vienen** en la imagen Server.

**Objetivo medible tras la Fase 1:** boot < 15 s de userspace (hoy 29.5 s), < 120 tareas (hoy 273), `io.full total` cercano a cero, CPU sin bajar de 1.5 GHz bajo carga.

### 0.3 🔴 Congelar el fallback — PASO BLOQUEANTE

Como se reinstala **sobre esta misma SD**, este paso es lo único que separa un error de perder el sistema entero. **No continuar a la Fase 1 sin haberlo completado y verificado.**

Con la Pi apagada y la SD en un PC (Linux/WSL):
```bash
sudo dd if=/dev/mmcblk0 of=atriz_noetic_fallback.img bs=4M status=progress conv=fsync
sha256sum atriz_noetic_fallback.img > atriz_noetic_fallback.img.sha256
```
En Windows sirve Win32DiskImager ("Read") o `dd` desde WSL. La imagen ocupa 29 GB en bruto; comprimirla (`gzip`, queda ~4–6 GB) y **guardarla en dos sitios distintos**.

Además, antes de reflashear, copiar fuera de la SD:
- `~/atriz_git/` completo (el repo tiene **6 cambios sin commitear**: `.fw`, `01_avanzar.py`, `02_girar.py`, `11_sensor_avanzado.py`, `carro.py`, `prueba.py` — commitear o al menos respaldar).
- `~/.ssh/`, la configuración WiFi de netplan, `/etc/udev/rules.d/50-serial.rules`.
- `~/Documents/MANUAL SPHERO.docx`.

**Verificación:** montar la imagen (`losetup -P`) y comprobar que se ven ambas particiones y que `home/sphero/atriz_git/src/Atriz_rvr` existe dentro. Una imagen que no se ha verificado no es un backup.

---

## Fase 1 — Reinstalación: ROS 2 Jazzy sobre la misma SD

> Requiere la Fase 0.3 verificada. Este paso **borra** el sistema Noetic actual.

1. Ubuntu **Server** 24.04.x LTS arm64 (no Desktop) con Raspberry Pi Imager; usuario `sphero`, SSH y WiFi preconfigurados en los ajustes del Imager.
2. **Antes del primer arranque completo**, editar `/boot/firmware/cmdline.txt`: quitar `console=serial0,115200` (la imagen de Ubuntu 24.04 lo trae por defecto y roba el UART — es exactamente lo que el manual acierta en corregir). Dejar `console=tty1`.
3. Aplicar **toda la Fase 0**. ✅ **Resuelto el 2026-07-30:** en 24.04 la configuración de arranque vive en un único `/boot/firmware/config.txt`, `usercfg.txt` y `syscfg.txt` **no existen** (Ubuntu abandonó el esquema de `pibootctl`), y las líneas nuevas necesitan cabecera `[all]`. Detalle en el manual, cap. 3.4.
4. Instalar `ros-jazzy-ros-base` + `ros-dev-tools`. **No** `desktop` (hoy hay `desktop-full` + `desktop` + `ros-base` instalados a la vez: 236 paquetes).
5. Longevidad de SD — imprescindible con 16 robots: `log2ram` o `/var/log` en tmpfs, journal volátil, sin swap.
6. `~/.bashrc`: `source /opt/ros/jazzy/setup.bash`, `export ROS_DOMAIN_ID=<n>`, `export RMW_IMPLEMENTATION=rmw_fastrtps_cpp`.

**Verificación:** `ros2 doctor`; `ros2 run demo_nodes_cpp talker` + `listener` en dos terminales; `ros2 topic hz /chatter` estable.

---

## Fase 2 — Portar el driver a `rclpy`

Workspace nuevo `~/atriz_ws` (colcon). El repo `Atriz_rvr` pasa a rama `ros2`.

### 2.1 Limpieza previa (borrar lastre, no portarlo)

Eliminar: `src/*.cpp` y `src/rvr++/` (hardware_interface C++ nunca ejecutado), el paquete `atriz_rvr_serial` (fork de `wjwwood/serial`, solo lo usaba el C++), `sphero_rvr_hw/scripts/` (carpeta huérfana sin `package.xml`), `scripts/rvr-ros.py` (driver legacy sin bit de ejecución), `.fw`, `carro.py`, `prueba.py`, y los residuos `build/ros_sphero_rvr/` del nombre antiguo del proyecto.

### 2.2 Paquetes nuevos

| Paquete | Tipo | Contenido |
|---|---|---|
| `atriz_rvr_msgs` | `rosidl` | Los **6 msg + 20 srv** actuales, portados. ✅ *Corregido el 2026-07-30: el hallazgo de que `SetPosAndYaw.srv` no estaba registrado en `add_service_files()` **ya no aplica** — se comprobó sobre `migracion-ros2` (`24c7749`) y los 20 `.srv` del disco están todos registrados, `SetPosAndYaw.srv` incluido.* |
| `atriz_rvr_driver` | `ament_python` | Nodo `rvr_driver_node`, SDK vendorizado |
| `atriz_rvr_description` | `ament_cmake` | URDF/xacro + `robot_state_publisher` |
| `atriz_rvr_bringup` | `ament_python` | Launch files, params YAML |

### 2.3 El arreglo estructural del driver

**Problema actual** (`Atriz_rvr_node.py:1633`):
```python
while not rospy.is_shutdown():
    loop.run_until_complete(asyncio.gather(handle_ros()))   # + await asyncio.sleep(0.1) dentro
    r.sleep()                                               # 15 Hz
```
> ⚠️ **CORREGIDO EL 2026-07-29 — este apartado baja de prioridad.** El plan original
> afirmaba que este bucle causaba la odometría a 4 Hz «con jitter». **Medido y
> desmentido:** el jitter era de σ 1.7 ms, y midiendo a nivel del SDK **sin ROS de
> por medio** el resultado era idéntico (3.85 Hz). Los 4 Hz venían solo de
> `sensor_control.start(interval=250)`.
>
> Se bajó a `interval=60` y el nodo pasó a entregar **16.59 Hz con σ 2.8 ms sin
> degradación alguna** (commit `24c7749` en `migracion-ros2`). Si este bucle fuera el
> cuello de botella, a 60 ms se habría notado.
>
> **Sigue mereciendo la pena rehacerlo** en el port a `rclpy` —por claridad, y porque
> hay **48** llamadas a `asyncio.run()` en callbacks—, pero **ya no es la vía crítica
> para el rendimiento**. Y el impacto de esas 48 llamadas en la latencia de `cmd_vel`
> **no se ha medido**: no debe afirmarse sin datos.

El event loop de asyncio solo avanza mientras `run_until_complete` está activo, así que los callbacks serie del SDK se procesan en ráfagas de ~100 ms cada ~166 ms. Además, las 48 llamadas a `asyncio.run()` dentro de callbacks ROS síncronos **crean y destruyen un event loop entero por cada `cmd_vel`**.

**Solución (por limpieza y latencia de comandos, no por throughput):**
```python
# El event loop de asyncio vive en su PROPIO hilo, corriendo siempre
self._loop = asyncio.new_event_loop()
threading.Thread(target=self._loop.run_forever, daemon=True).start()

# Callbacks del SDK → cola thread-safe → un timer de ROS drena y publica
# Comandos ROS → al loop de asyncio, SIN crear loops nuevos:
asyncio.run_coroutine_threadsafe(self._rvr.drive_with_velocity(...), self._loop)
```
Nodo con `MultiThreadedExecutor` y callback groups separados para comandos y telemetría.

### 2.4 Correcciones de comportamiento

- **Parametrizar** `serial_port` (default `/dev/rvr`), `baud`, `odom_frame`, `base_frame`, `streaming_interval_ms` vía `declare_parameter`. Nada hardcodeado.
- **REP-103:** `gyroscope_handler` (`Atriz_rvr_node.py:911-922`) llama a `check_if_need_to_send_msg('gyroscope')` **dos veces**, primero en deg/s y luego en rad/s — puede publicar `/odom` con velocidad angular en grados. Y `imu.angular_velocity` queda **siempre** en deg/s. Publicar todo en rad/s, una sola vez.
- `light_handler` usa `rospy.Time()` (cero) como timestamp → usar el reloj del nodo.
- `wait_until_motion_complete()` no tiene timeout → puede colgar el hilo de servicio indefinidamente. Añadir timeout y devolver fallo.
- ⚠️ **Watchdog de `cmd_vel` — CORREGIDO EL 2026-07-30: YA EXISTE.** Este plan decía «hoy no existe nada así». Es **falso** sobre `migracion-ros2`: `handle_ros()` (`Atriz_rvr_node.py:1127-1128`) para los motores si pasan más de `cmd_vel_timeout = 0.3 s` sin comando, y se comprueba cada ~0.17 s. Se añadió en `d8f182d` y se refinó en `659364c`, ambos **posteriores al commit auditado** — la misma causa que los otros hallazgos retirados.
  ✅ **HECHO Y VERIFICADO.** Se conservó en el port, el timeout es un parámetro
  (`cmd_vel_timeout`, 0.3 s por defecto, `rvr_driver_node.py:228`) y se comprobó en banco con
  `medir_watchdog_ros2.py` — que mide **desplazamiento**, no velocidad, porque un robot que
  «va lento» y uno que «ha parado» se distinguen por dónde acaban: **para en 527 ms / 7.9 cm**.
- ✅ **Frecuencia de sensores — RESUELTO Y MEDIDO** (Fase 0.1, commit `24c7749`).
  `interval` de 250 → **60 ms**, con las **8** corrientes de sensores activas:

  | `interval` | `/odom` real | σ |
  |---|---|---|
  | 250 ms | 3.85 Hz | 1.7 ms |
  | 100 ms | 9.94 Hz | 2.4 ms |
  | **60 ms** | **16.59 Hz** | **2.8 ms** |
  | 50 ms | el streaming **no arranca** | — |

  El firmware **cuantiza a múltiplos de 20 ms** (250 → 260 reales, 150 → 160). 60 ms
  es el mínimo estable. **No hizo falta recortar sensores:** 125 paquetes/s caben de
  sobra en 115200 baud (~11.5 KB/s). En el port a `rclpy` esto pasa a ser el valor
  por defecto del parámetro `streaming_interval_ms`.
- **Manejo de errores del check de firmware:** `rvr_fw_check_async.py` captura
  `except (asyncio.TimeoutError, Exception)` y **continúa en silencio**, de modo que
  el arranque parece correcto aunque el RVR no responda. Debe registrar un `WARN`
  visible y exponer el estado del enlace en un topic de diagnóstico.

**Verificación:**
```bash
# 🔴 NO uses `ros2 topic hz /odom`: da 0 Hz SIEMPRE con el robot perfecto. `/odom` es
#    BEST_EFFORT y `ros2 topic hz` se suscribe RELIABLE sin opción de cambiarlo en Jazzy;
#    DDS no empareja y no llega nada. La misma trampa de QoS que costó la parada de
#    emergencia. Mide con un suscriptor propio:
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_ritmo_ros2.py
#    → /odom ≈ 16.5 Hz (techo del firmware con interval=60), /scan ≈ 10-12 Hz

# 🔴 Y publica en `cmd_vel_raw`, NO en `cmd_vel`: `/cmd_vel` es la SALIDA del
#    collision_monitor. Publicar ahí funciona —el robot obedece— y SALTA LA SEGURIDAD.
ros2 topic pub /cmd_vel_raw geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
# soltar el publisher → debe pararse. Watchdog: `cmd_vel_timeout` = 0.3 s (no 500 ms),
# peor caso medido ~0.35 s. ⚠️ Y el barrido del lidar tiene que estar ENCENDIDO
# (`atriz-escaneo on`) o el collision_monitor bloquea el movimiento y parecerá averiado.
```

---

## Fase 3 — URDF, LIDAR y árbol TF

### 3.1 URDF — repara el árbol TF roto

Hoy el árbol está **partido en dos**: el driver publica `odom → rvr_base_link` (`Atriz_rvr_node.py:96`) y el LIDAR cuelga de `base_link` vía un `static_transform_publisher` (`lidar_only.launch`). Sin puente. Cualquier SLAM o navegación es imposible. Además **no existe ningún `.urdf` ni `.xacro`** en el repo, pese a que `sphero_rvr_hw_interface.cpp:337` implementa `loadURDF()`.

Crear `atriz_rvr_description/urdf/rvr.urdf.xacro` con la cadena canónica:
```
base_footprint → base_link → { laser, imu_link, wheel_* }
```
El driver publica **solo** `odom → base_link` (renombrando `rvr_base_link`). `robot_state_publisher` publica el resto. **Medir físicamente** el offset del X2 respecto al centro del RVR — no usar el `0.0 0.0 0.10` inventado del launch actual.

### 3.2 YDLIDAR X2

```bash
git clone https://github.com/YDLIDAR/YDLidar-SDK && cmake/make/install
git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver   # la rama humble funciona en Jazzy
```
Usar `params/X2.yaml` del propio driver como base. Los parámetros actuales del launch de ROS 1 son un punto de partida válido (`isSingleChannel: true`, `baudrate: 115200`, `sample_rate: 3`, `frequency: 10.0`, `range: 0.1–12.0`, `inverted: true`).

**Nota realista sobre el X2:** canal único, sin intensidad, ~8 m útiles, 10 Hz. SLAM interior funcionará, pero la calidad del mapa será modesta. Ajustar expectativas de Nav2 en consecuencia.

Añadir regla udev `/dev/ydlidar` por serial del adaptador USB — **imprescindible con 16 robots**, donde `/dev/ttyUSB0` no es determinista.

**Verificación:** `ros2 run tf2_tools view_frames` produce **un solo árbol conectado** — y
compruébalo con `ros2 run tf2_ros tf2_echo odom base_footprint`, que es **el transform que pide
el consumidor**: un `tf2_echo` cualquiera prueba que hay *un* camino, no que el árbol esté bien
(costó la Fase 3). `/scan` a **10.1–11.9 Hz** (el motor del X2 va libre, no clava una
frecuencia), medido con un suscriptor BEST_EFFORT, no con `ros2 topic hz`; visualizar `/scan` + TF en RViz2 desde un portátil (no en la Pi).

---

## Fase 4 — SLAM ✅ COMPLETADA · Nav2 ✅ COMPLETADO · AMCL ✅ COMPLETADO (2026-07-31)

> 🔴 **Esta cabecera decía «Nav2 ⏳ pendiente» hasta el 2026-08-01**, cuando Nav2 llevaba desde
> el 31 de julio navegando con **9–10 cm** de error final, rodeando obstáculos **4 de 4**, y con
> AMCL siguiendo la pose a **0.1 cm**. Es el mismo fallo que el índice del manual: **los
> documentos de ESTADO se quedan atrás mientras las evidencias están al día.**
> → Al cerrar algo, actualiza el plan y `TRASPASO.md` **en el mismo commit** que la evidencia.

### 4a. SLAM — ✅ hecho y verificado

`slam_toolbox` en modo `async`, con la configuración ajustada a lo **medido** de este robot
(`atriz_rvr_bringup/config/slam_toolbox_atriz.yaml`): 8 m de alcance real del X2, 5 cm de
resolución y 30 cm entre barridos.

**Verificado:** el mapa crece al mover el robot — 2367 → 3299 celdas (5.92 → 8.25 m²) tras
1.78 m de recorrido. Coste: **4.4 % de CPU**, ~30 % con todo a la vez. Manual, cap. 9.

⚠️ **El plan subestimó esta fase.** Se preveía «arrancar slam_toolbox y ajustar parámetros», y
lo que costó fueron **cuatro fallos que no daban ningún error**, tres de ellos fuera de SLAM:

| Lo que falló | Dónde estaba |
|---|---|
| `base_link` con **dos padres** → árbol TF partido | el driver y el URDF |
| El **yaw de `/odom` invertido** → `/scan` y `/odom` en desacuerdo | el driver (ejes FRD→FLU) |
| El acelerómetro en **`g`**, no en m/s² | el driver |
| `fixed_resolution: false` → slam_toolbox **descartaba barridos** | el YAML del LIDAR |

Y dos herramientas de banco propias dieron **falsos negativos**, una de ellas midiendo algo
imposible (si el mapa crecía **girando en el sitio**). El detalle está en el manual, cap. 9.11,
y la evidencia cruda en `00_auditoria/evidencia_24_04/13_fase4_cerrada.txt`.

**La lección para las fases que quedan:** en este sistema los fallos **no producen errores**.
Cada verificación tiene que comprobar el **efecto medible** —el ritmo de un topic, el número de
celdas del mapa— y no que un proceso exista o un comando devuelva 0.

### 4b. Nav2 — ✅ COMPLETADO Y VERIFICADO (2026-07-31)

> 📝 Esto decía «⏳ pendiente» hasta el 2026-08-01, **un día después de corregir la cabecera del
> capítulo por lo mismo**. Corregir un título no arregla el cuerpo: al cerrar algo hay que buscar
> **todas** sus menciones, no la primera.

✅ **Medido:** error final **9–10 cm** (= la tolerancia configurada), meseta de **0.407 m/s** a
0.40 comandado, y **4 de 4 SUCCEEDED** rodeando un obstáculo con desvíos de 26–32 cm.

- Nav2 con `nav2_regulated_pure_pursuit_controller` (diferencial), costmaps a resolución modesta (5 cm) y ventanas pequeñas — es la carga más pesada del Pi 4.

🔴 **Instalar `ros-jazzy-navigation2`, NO `ros-jazzy-nav2-bringup`.** Comprobado el 2026-07-31:

| | Paquetes | Qué arrastra |
|---|---|---|
| `ros-jazzy-navigation2` | **309** | lo que se usa: amcl, bt-navigator, controller, costmap-2d, planners, `map-server`… |
| `ros-jazzy-nav2-bringup` | **621** | lo anterior **+ Gazebo**: `nav2-minimal-tb3-sim`, `tb4-sim`, `ros-gz-sim`, y hasta `pocketsphinx-en-us` |

`nav2-bringup` son ficheros de ejemplo para TurtleBot en simulador. **Los launch y la
configuración de Atriz los escribimos nosotros**, igual que con `slam_toolbox`. Y esos 312
paquetes de más acabarían replicados en los **16 robots** vía imagen dorada.

📝 De paso, `nav2-map-server` viene en `navigation2`, así que **`/slam_toolbox/save_map` dejará
de fallar** con `result=255` (manual, cap. 9.5).
- Guardar el mapa del laboratorio (`nav2_map_server`) y distribuirlo a los 16 robots: en un laboratorio fijo, **mapear una vez y localizar con AMCL** es mucho más barato que 16 SLAM simultáneos.
  - 📝 `nav2_map_server` **no está instalado todavía**, y por eso `/slam_toolbox/save_map`
    falla con `result=255`. Para guardar mapas hoy se usa `serialize_map`, que es nativo.

✅ **Los tres bloqueantes de odometría están resueltos** (2026-07-31, manual cap. 10 y 9.12):

1. ~~La deriva de la localización~~ → **caracterizada**: mediana de 1.0 / 2.7 cm, y el error
   cabe en una celda del mapa.
2. ~~La velocidad de `/odom`~~ → **arreglada**. El stream `Velocity` era **exacto**; fallaba
   que el driver lo copiaba del marco del mundo a un campo del marco del robot.
3. ~~El yaw desfasado de la posición~~ → **arreglado**: `reset_yaw()` no hace nada, así que el
   driver mide el offset en cada arranque y lo resta.

🔴 **Queda la inclinación de ~8°**, confirmada por tres vías independientes (árbol TF, `Roll`
de la IMU y acelerómetro). Causa sin determinar. **No es urgente**: con ella presente la deriva
de SLAM es de 2.7 cm, así que no está arruinando el emparejado. Por REP-105
`odom → base_footprint` debería ser plana (x, y, yaw) y el driver mete roll y pitch.

**Verificación de Nav2:** enviar un `NavigateToPose` desde la CLI y comprobar que llega evitando un obstáculo; medir carga (`top`) durante la navegación para confirmar margen en el Pi 4.

---

## Fase 5 — Plataforma web sobre rosbridge

### 5.1 Seguridad primero (bloqueante)

- `swarm_lab_api/app/core/raspberry_config.py` contiene **IPs, usuarios y la contraseña del usuario `sphero` en texto plano, commiteados en un repo público**. Es la misma credencial del manual. **Rotar la contraseña** en todos los equipos, migrar a claves SSH, mover secretos a `.env` (ya existe `.env.example`), y purgar el fichero del historial (`git filter-repo`) asumiendo que la credencial antigua ya está comprometida.
- Sacar del control de versiones `swarm_lab_env/` (venv completo, **5418 ficheros**), `node_modules/`, `build/`, `devel/`.

### 5.2 🔴 Arreglar la parada de emergencia

La web publica en `/rvr/emergency_stop` (`swarm_lab_api/app/api/robots.py`); el driver escucha `is_emergency_stop` (`Atriz_rvr_node.py:1599`). **Nombres distintos — el botón de emergencia probablemente no hace nada.**

✅ **RESUELTO Y VERIFICADO** (2026-07-31 / 2026-08-01). El driver escucha **los tres** nombres
a propósito —con un botón de emergencia el modo de fallo que importa es «el mensaje no llega»— y
el oficial para la web es **`/emergency_stop`** (`std_msgs/Empty`).

🔴 **QoS: RELIABLE + VOLATILE.** Este párrafo decía *transient local*, y eso **fue la tercera
causa de fallo** de la parada: `TRANSIENT_LOCAL` en el suscriptor exige que el publicador
también lo sea, **y rosbridge no lo es** → `incompatible QoS, no messages will be received`, en
silencio. En un suscriptor se usa VOLATILE, que empareja con todo.

✅ **Y cancela Nav2**, que era el cuarto fallo: el nodo `cancelar_nav2` manda `CANCEL_ALL`.
Verificado con control — objetivo `CANCELED` y **0.0 cm** al liberar la parada; sin él, objetivo
**ACTIVO** y el robot **arrancó solo 34.7 cm**.

✅ **Y el watchdog de `cmd_vel` YA EXISTÍA**, incluso en ROS 1: `cmd_vel_timeout` = **0.3 s**.
Este plan decía que no existía y estaba equivocado.

### 5.3 Sustituir SSH por rosbridge en la ruta crítica

Hoy cada lectura de telemetría es un `subprocess.Popen(["ssh", ...])` nuevo, y `execute_command_on_multiple_robots` recorre los robots en un `for` con `timeout=4.0` → con 16 robots, hasta **64 s** por comando con el proceso FastAPI bloqueado.

**Nuevo reparto de responsabilidades:**

| Capa | Responsabilidad |
|---|---|
| **roslibjs (navegador)** | Suscripción a `/odom`, `/scan`, `/battery_state`, `/map`, `/motor_status`; publicación en **`/cmd_vel_raw`**. Tiempo real, sin pasar por FastAPI |
| **FastAPI** | Autenticación JWT, reserva de robots por usuario, registro y resultados de experimentos, catálogo de robots, logging |
| **SSH** | ✅ **Solo mantenimiento.** Ya no hace falta ni para el ciclo de vida: `atriz-robot.service` levanta el robot solo desde el 2026-07-31, verificado con un reinicio real |

Cambios concretos:
- ✅ `ros-jazzy-rosbridge-suite` **ya instalado** y en `provision.sh`. ⚠️ **NO** lleva unidad
  systemd propia: va dentro de `robot.launch.py` para heredar el `ROS_DOMAIN_ID`, que es
  justo lo que systemd no sabe dar por sí solo. Puerto 9090, verificado desde un navegador.
- 🔴 **Los topics de telemetría son BEST_EFFORT** (`odom`, `imu`, `scan`, `color`,
  `ambient_light`, `encoders`). Un suscriptor con el perfil por defecto pide RELIABLE, **DDS no
  empareja y no llega NADA** — sin error y sin aviso. Es el primer sitio donde mirar si «la web
  no recibe odometría».
- 🔴 **La web DEBE llamar a `/start_scan` al empezar cada sesión.** Los robots arrancan con el
  barrido del lidar parado, y sin `/scan` el `collision_monitor` bloquea el movimiento: un robot
  recién encendido no obedece y desde la web se ve igual que uno averiado.
- Modelo `Robot` en BD: `host` (= `rvr-NN.local`, con IP como override), `rosbridge_port`,
  `domain_id`, `status`. 🔴 **Sin columna `namespace`** — decisión cerrada, ver arriba.
- Composable Vue `useRosConnection(robot)` con `roslib.js`; reconexión automática y **estado de conexión visible** — si el WebSocket cae, el usuario debe verlo y el robot debe pararse.
- `RobotDashboard.vue` / `BatterySensorData.vue`: sustituir polling por suscripciones.
- Retirar `VideoStream.vue` como stream del robot (no hay cámara); dejar la opción de cámaras fijas de sala si más adelante se añaden.
- Eliminar del workspace web los paquetes heredados de otro robot que no se usan: `box_pushing`, `mapping`, `path_planning`, `robotnik_msgs`, `robotnik_sensors`.

**Verificación:** desde el navegador, mover el robot y ver `/odom` y `/scan` actualizándose en vivo; cortar el WiFi de la Pi y comprobar que **(a)** la UI marca desconexión y **(b)** el robot se detiene solo en <500 ms.

---

## Fase 6 — Escalar a 16 robots

1. **Imagen dorada:** de la SD perfeccionada, `dd` + `pishrink`. Documentar el proceso de clonado.
2. **Personalización en primer arranque:** un `first-boot.service` que lee un `robot_id` de un fichero en la partición `/boot/firmware` (editable desde cualquier PC) y fija hostname (`rvr-01`), `ROS_DOMAIN_ID`, namespace y clave SSH. Un solo fichero de texto por robot; sin sesiones manuales.
3. **Red:** reservas DHCP por MAC en el router en vez de IPs estáticas en 16 dispositivos. Preferir **5 GHz** y repartir los robots entre canales/APs — 16 clientes con telemetría continua en una sola AP es el cuello de botella más probable del laboratorio. Medir ancho de banda por robot en la Fase 5 y extrapolar antes de comprar hardware de red.
4. **Gestión continua:** Ansible con inventario de 16 hosts para actualizaciones y despliegue de código. Evita la deriva de configuración, que es lo que mata las flotas.
5. **Salud de flota:** endpoint que agregue batería, uptime, temperatura, estado de `/scan` y `/odom` de los 16. Alerta de batería baja.
6. **Documentación:** reescribir el `MANUAL SPHERO.docx` como la versión ROS 2. El manual actual tiene lagunas que causaron los problemas de esta auditoría — no toca `config.txt`, deja "automatización de arranque", "IP estáticas", "Ylidar" y "app web" como pendientes sin desarrollar, e instala el escritorio gráfico completo.

---

## Fase 7 — Documentación (transversal, se escribe DURANTE, no al final)

Con la reversión basada en "reflashear y rehacer", la documentación **es** el plan de contingencia. Se escribe a medida que cada fase se completa y se verifica, no en un sprint final.

Entregables, todos dentro del repo `atriz_migracion` creado en la **Fase 00** y commiteados a medida que se completan:

| Fichero | Contenido | Se escribe en |
|---|---|---|
| `00_auditoria/INFORME_AUDITORIA.md` | La auditoría completa de este análisis: hardware, los 11 cuellos de botella priorizados con sus mediciones (`time_in_state`, `pressure/io`, `systemd-analyze blame`, `iwconfig`), los hallazgos del UART, los bugs del driver con fichero:línea, el análisis de compatibilidad Python 3.12 del SDK, y la auditoría de la plataforma web | **Fase 00 (ya)** |
| `02_manual/MANUAL_ATRIZ_ROS2.md` | **Sustituto del `MANUAL SPHERO.docx`.** Instalación completa desde SD en blanco hasta robot navegando: flasheo, `cmdline.txt`, `config.txt` con `disable-bt`, udev, ROS 2 Jazzy, workspace, LIDAR, rosbridge, systemd. Cada comando exacto y su verificación | Fases 1–5, incremental |
| `03_operacion/RUNBOOK.md` | Operación diaria: arrancar/parar el stack, dónde miran los logs, qué hacer si el RVR no responde, si el LIDAR no aparece, si el WebSocket cae, si la batería se agota | Fases 2–5 |
| `03_operacion/RECUPERACION.md` | Cómo restaurar `atriz_noetic_fallback.img`, dónde está guardada, cómo verificarla, y qué se pierde al revertir | Fase 0.3 |
| `03_operacion/ARQUITECTURA.md` | El diagrama de la decisión DDS (un dominio por robot), el contrato de topics/servicios **sin namespace**, con su QoS, y por qué la web habla por rosbridge y no por SSH | Fase 5 |
| `03_operacion/FLOTA.md` | Clonado de la imagen dorada, `robot_id.txt` y `red.txt` en la partición FAT, tabla de los 16 robots (**IP estática desde la FAT**, no reserva DHCP; `domain_id`), procedimiento de alta de un robot nuevo | Fase 6 |

**Reglas para que la documentación no se pudra** — la deuda documental encontrada en esta auditoría (ver sección siguiente) nació de no seguirlas:
- Ningún documento describe algo que no se haya ejecutado y verificado. Si un paso no se ha probado, se marca explícitamente como **NO VERIFICADO**.
- Las rutas y nombres de paquete se copian de la terminal, no se escriben de memoria.
- Cuando se renombra algo, se hace `grep -r` del nombre viejo en `docs/` antes de dar por cerrado el cambio.

Además, el `MANUAL SPHERO.docx` original **se conserva sin modificar** junto a la imagen de fallback: sigue siendo el procedimiento válido para reconstruir el sistema Noetic si se decide revertir.

---

## Deuda documental a corregir (barata y de alto valor)

La documentación del repo describe un sistema que no existe, lo que hace perder horas:
- `LIDAR_INTEGRATION_SUMMARY.md` afirma que existen `~/atriz_git/src/ydlidar_ros_driver/` y `~/atriz_git/src/YDLidar-SDK/` → **no existen** (`find` sobre todo el sistema devuelve 0 resultados). Los 3 launch del LIDAR fallan.
- `README.md` describe `scripts/core/Atriz_rvr_node.py` y `pyrightconfig.json` → no existen; y usa la ruta del nombre antiguo `src/ros_sphero_rvr/`.
- `test_functionalities.launch` referencia `test_new_functionalities.py`, y `hw_controller.launch` referencia `rvr-ros-sim.py` → ninguno existe.
- `package.xml` de `atriz_rvr_driver` declara `joint_limit_interface` (paquete inexistente; el correcto es `joint_limits_interface`) → `rosdep` falla.
- `setup.py` declara `packages=['sphero_sdk', 'sphero_sim']` pero `scripts/sphero_sim/` no existe.
- `controller.maybe.config.yaml`: el joint `_rl_` está duplicado y falta `_rr_`.
- `hardware_interfaces.yaml` dice `loop_hz: 300`; el código C++ usa 20.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El SDK del RVR falla en Python 3.12 por algo no detectado en el análisis estático | **Validar en la Fase 1, antes de portar nada**: script mínimo `pyserial-asyncio` + SDK que despierte el robot y lea batería. Es el go/no-go de todo el plan |
| ~~115200 baud no aguanta 20 Hz de telemetría~~ | ✅ **CERRADO 2026-07-29.** Medido: 16.59 Hz con los 8 sensores y 125 paquetes/s, holgado para ~11.5 KB/s. No hizo falta recortar streams. El techo lo pone el firmware del RVR (mínimo 60 ms, cuantizado a 20 ms), no el enlace serie |
| WiFi saturado con 16 robots | Aislamiento DDS por dominio (ya en el diseño) elimina el tráfico de descubrimiento; medir ancho de banda real por robot en Fase 5 |
| Nav2 no cabe en el Pi 4 junto al resto | Mapear una vez + AMCL en vez de SLAM continuo; costmaps pequeños; si no llega, Nav2 en el servidor vía rosbridge |
| Mortalidad de microSD con 16 unidades | `log2ram`, journal volátil, `noatime`, sin swap (Fase 1.5); presupuestar tarjetas de repuesto y tener la imagen dorada lista para reflashear |
| La migración se alarga o falla y no hay robot usable | Restaurar `atriz_noetic_fallback.img` sobre la SD (Fase 0.3): ~20 min y el sistema Noetic vuelve exactamente como estaba. Sin esa imagen, la reversión es rehacer el manual entero a mano — de ahí que 0.3 sea bloqueante |
| Se pierde conocimiento entre sesiones y hay que redescubrir todo | Los entregables de la Fase 7 se escriben **según se avanza**, no al final. Cada fase deja su documentación antes de pasar a la siguiente |

---

## Verificación end-to-end (criterio de éxito global)

Sobre un robot, con el sistema arrancado por systemd tras un reinicio limpio y **sin ninguna intervención manual**:

1. `bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware` pasa **sin fallos**
   (105 aserciones). Sustituye a la comprobación por `ros2 topic list`, que **conserva topics de
   nodos muertos** y llegó a dar por vivo un robot apagado.
2. `ros2 run tf2_ros tf2_echo odom base_footprint` resuelve — **el transform que pide el
   consumidor**, no uno cualquiera.
3. `medir_ritmo_ros2.py` da `/odom` ≈ 16.5 Hz y `/scan` 10.1–11.9 Hz. 🔴 **No con
   `ros2 topic hz`**, que sobre estos topics da 0 Hz siempre (QoS).
4. Desde el navegador: teleoperación fluida, telemetría en vivo, mapa construyéndose.
5. Enviar destino de navegación desde la web → el robot llega evitando un obstáculo.
6. **Prueba de fallo:** cortar el WiFi de la Pi → la UI marca desconexión y el robot se detiene en <500 ms.
7. **Prueba de emergencia:** pulsar E-Stop en la web → parada inmediata verificada físicamente.
8. Uptime de 8 h sin degradación: sin crecimiento de memoria, sin desconexiones del UART, temperatura < 70 °C.

Superado esto, la SD se clona y se convierte en la imagen dorada de los 16.
