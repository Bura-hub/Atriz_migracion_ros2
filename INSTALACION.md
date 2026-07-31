# Ruta de instalación — de apagar el sistema actual a un robot funcionando

> **Este es el documento a seguir en orden.** Los capítulos del manual están numerados
> **por tema**, no por orden de ejecución, así que seguirlos del 0 al 12 no funciona: el
> capítulo 1 (UART) presupone un sistema ya instalado, que es el capítulo 3.
>
> Aquí está el orden real, con el documento y el script de cada paso.

**Si eres un agente:** lee primero [`CLAUDE.md`](CLAUDE.md) y [`TRASPASO.md`](TRASPASO.md),
y luego recorre esta ruta. Los pasos marcados 👤 los ejecuta la persona, no tú.

---

## Resumen de la ruta

Marcas: ✅ recorrido y verificado · ⏳ pendiente · 👤 lo ejecuta la persona

```
  ETAPA A — Cerrar el sistema actual                              ✅ 2026-07-29/30
     A1  Preparar la Pi                     scripts/fase_0_3_respaldo.sh    ✅
     A2  Apagar                          👤                                 ✅
     A3  Imagen dd de la microSD          👤 RECUPERACION.md §1              ✅
     A4  Verificar la imagen              👤 RECUPERACION.md §1              ✅

  ETAPA B — Instalar el sistema nuevo                             ✅ 2026-07-30
     B1  Flashear Ubuntu Server 24.04     👤 manual, cap. 3.1-3.2            ✅
     B2  Editar cmdline.txt ANTES de arrancar 👤 manual, cap. 3.3  ⚠️ CRÍTICO ✅
     B3  Configuración de arranque + UART    manual, cap. 3.4 y 1.2          ✅
     B4  Primer arranque y verificación      manual, cap. 3.5-3.6            ✅
     B5  Cerrar actualizaciones + credenciales de git  cap. 3.5.1            ✅

  ETAPA C — Poner el sistema a punto                              ✅ 2026-07-30
     C1  Higiene del SO                       scripts/fase_1_higiene_so.sh   ✅
     C2  Verificar contra la línea base       manual, cap. 4.3               ✅

  ETAPA D — GO / NO-GO                                    🟢 GO — 2026-07-30
     D1  Clonar el código                     manual, cap. 5.1               ✅
     D2  Validar el SDK en Python 3.12        scripts/fase_1_validar_sdk_py312.py
         └── 🟢 GO: 16.67 Hz, firmware 9.1.462, los 103 ficheros compilan     ✅

  ETAPA E — ROS 2 y el robot
     E1  Instalar ROS 2 Jazzy                 manual, cap. 5.2-5.5            ✅
         └── 201 paquetes · ros2 doctor: 5/5 · pub/sub 9.997 Hz, σ 0.35 ms
     E2  Recuperar el estado actual           ver "Cómo volver a donde estábamos"  ✅
     E3  Verificar UART y telemetría          manual, cap. 1.3 y 2            ✅
     E4  Verificar el LIDAR                   manual, cap. 8.2                ✅

  ETAPA F — El robot completo sobre ROS 2                         ✅ 2026-07-31
     F1  Clonar y compilar el workspace       Atriz_rvr rama `ros2`           ✅
         └── driver rclpy + msgs + URDF + bringup. Ya escrito: solo se compila
     F2  Driver del LIDAR desde fuentes       manual, cap. 8.5a-b             ✅
         └── no hay paquete apt: YDLidar-SDK + ydlidar_ros2_driver (humble)
     F3  Instalar slam_toolbox                manual, cap. 9                  ✅
     F4  Arrancar y verificar                 manual, cap. 9.13               ✅
         └── el mapa CRECE al moverse: 2367 -> 3299 celdas (8.25 m²)

     F5  Deriva de SLAM caracterizada         14_deriva_slam_caracterizada.txt ✅
         └── mediana 1.0 cm (1.6 m) y 2.7 cm (2.4 m). Cabe en una celda del mapa
     F6  Los tres marcos de /odom              manual, cap. 10                 ✅
         └── yaw +0.00° · dirección vs yaw +0.03° · twist con 2 % de error

     F7  Nav2 NAVEGA                          manual, cap. 11                 ✅
         └── dos objetivos autónomos, 9-10 cm de error · ~89 % de un núcleo

     F8  collision_monitor: la capa de seguridad  manual, cap. 12            ✅
         └── para a 8-9 cm de una pared · sin LIDAR no conduce · no queda atrapado

     F9  Navegando a 0.40 m/s                  manual, cap. 11.10             ✅
         └── meseta 0.407 m/s · dos objetivos SUCCEEDED con 8 cm de error

     F10 Lo que queda                                                          ⏳ SIGUIENTE
         1. Obstáculos que haya que RODEAR (solo probado contra pared)  ← AQUÍ
         2. save_map falla intermitente        manual, cap. 11.11
         3. Fase 4c: map_server + AMCL        plan, Fase 4c
         4. La inclinación de ~8° (tres vías, causa sin determinar, NO urgente)
         5. Los 16 servicios y 4 topics del driver sin portar
         6. Plataforma web                    plan, Fase 5
         7. Clonar a los 16 robots            FLOTA.md
```

> **Las etapas A a F9 están recorridas y verificadas sobre la máquina real.** Los capítulos
> 1, 3, 4, 5, 7, 8, 8bis, 9, 10, **11 (Nav2)** y **12 (seguridad)** del manual dejaron de ser
> NO VERIFICADO: el robot navega solo y para antes de chocar. La evidencia cruda de cada paso está
> en [`00_auditoria/evidencia_24_04/`](00_auditoria/evidencia_24_04/) — es lo que permite
> comparar cuando un robot nuevo de la flota no dé lo mismo.
>
> **🟢 El go/no-go salió GO**, ROS 2 Jazzy está instalado y el robot funciona entero: driver en
> `rclpy`, URDF, LIDAR, SLAM, y la odometría con sus tres marcos corregidos. **Nav2 ya está
> instalado y NAVEGANDO** con los valores medidos del robot, y con la **capa de seguridad
> puesta y medida** (manual, cap. 12), navegando ya a **0.40 m/s**. El siguiente paso es probar
> con obstáculos que haya que **rodear**.
>
> ### Un solo comando para saber si el robot está bien
>
> ```bash
> bash scripts/verificar_robot.sh --hardware
> ```
>
> **50 comprobaciones**, y sale con código ≠ 0 si algo falla. Pásalo al final de cada etapa en
> lugar de recordar qué había que mirar. En `rvr-01`, el 2026-07-31: 50 correctas, 0 fallos.
>
> ### Y si estás instalando el robot 2, 3… 16
>
> **No sigas esta ruta a mano.** Hay tres scripts para eso, y el procedimiento completo está en
> [`03_operacion/FLOTA.md`](03_operacion/FLOTA.md):
>
> | Script | Dónde | Qué hace |
> |---|---|---|
> | `preparar_tarjeta.sh --id NN` | en el **PC** | `cmdline.txt`, `config.txt` y `robot_id.txt` de una tarjeta recién grabada |
> | `provision.sh` | en el robot | Todas las etapas B–E de una vez. Idempotente |
> | `verificar_robot.sh` | en el robot | Decide si quedó bien |
>
> Esta ruta a mano es **para el primer robot** y para entender *por qué* hace cada cosa. A
> partir del segundo, la imagen dorada ahorra ~300 MB de descarga y 15-20 min **por robot**.

---

## ETAPA A — Cerrar el sistema actual

### A1 · Preparar la Pi

```bash
bash ~/atriz_migracion/scripts/fase_0_3_respaldo.sh
```

Comprueba que no queda nada sin commitear, **sin subir**, o en un **stash** — los stashes no
viajan a un remoto y desaparecen con la tarjeta. Respalda en `~/respaldo_pre_migracion`:
claves SSH, netplan (con la PSK del WiFi), `.bashrc`, ficheros sin trackear, un inventario de
paquetes, y el historial de Claude Code.

**Si el script marca ✗, resuélvelo antes de continuar.**

👤 **Copia `~/respaldo_pre_migracion` a un USB o a tu PC.** No va a git: contiene claves
privadas y la PSK del WiFi.

### A2 👤 · Apagar

```bash
sudo poweroff
```

### A3 👤 · Imagen de la microSD — **BLOQUEANTE**

Con la Pi **apagada** y la tarjeta en un PC. Copia byte a byte de toda la tarjeta a un
fichero: es el botón de deshacer de todo el proyecto.

**Procedimiento completo, con Windows y Linux paso a paso, en
[`03_operacion/RECUPERACION.md`](03_operacion/RECUPERACION.md) §1.**

🔴 **Si el PC es Windows:** al insertar la microSD, Windows ofrecerá **formatearla** porque no
entiende ext4. **CANCELAR SIEMPRE** — aceptar destruye el sistema que se intenta respaldar.
La herramienta es **Win32DiskImager**, botón **Read**; Rufus y balenaEtcher no sirven porque
solo escriben, no leen.

En Linux:

```bash
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL      # identifica el dispositivo
sudo dd if=/dev/mmcblk0 of=atriz_noetic_fallback.img bs=4M status=progress conv=fsync
sha256sum atriz_noetic_fallback.img > atriz_noetic_fallback.img.sha256
gzip -6 atriz_noetic_fallback.img
```

⚠️ **Un `of=` equivocado destruye el disco de destino.** Verifica dos veces.

**Guárdala en dos sitios distintos.** Una copia única en el mismo PC desde el que reflasheas
no es un respaldo.

### A4 👤 · Verificar la imagen

**Una imagen sin verificar no es un respaldo.** Procedimiento en `RECUPERACION.md` §1:
montarla con `losetup -Pf` y comprobar que se ven las dos particiones y que
`home/sphero/atriz_git/src/Atriz_rvr` existe dentro.

> **Qué estás respaldando:** no el sistema lento de esta mañana, sino uno donde el RVR va a
> 16.59 Hz sin perder un mensaje en 12 minutos y el LIDAR entrega el 100 % de sus tramas
> correctas. Si la migración se atasca, restaurar esto te devuelve a un punto bueno conocido.

---

## ETAPA B — Instalar el sistema nuevo

### B1 👤 · Flashear Ubuntu Server 24.04 LTS arm64

**Manual, capítulo 3.1–3.2.** Con Raspberry Pi Imager. **Server, no Desktop** — el escritorio
fue la causa nº1 de la lentitud del sistema anterior.

En «Editar ajustes»: usuario `sphero` con **contraseña nueva** (la anterior está comprometida),
hostname `rvr-01`, WiFi (preferir 5 GHz), y **activar SSH**.

### B2 👤 · Editar `cmdline.txt` ANTES del primer arranque — ⚠️ CRÍTICO

**Manual, capítulo 3.3.**

Con la tarjeta aún en el PC, monta la partición FAT y **quita `console=serial0,115200`** de
`cmdline.txt`. La imagen de Ubuntu lo trae por defecto y **reserva el UART para la consola**,
dejándolo inutilizable para el RVR.

Es el único acierto importante del manual original y hay que repetirlo en cada instalación.

### B3 ✅ · Configuración de arranque y UART — **verificado 2026-07-30**

**Manual, capítulo 3.4** (qué ficheros existen en 24.04) **y capítulo 1.2** (el razonamiento
completo del UART).

**Se parte en dos, y la primera mitad se puede hacer desde Windows** con la tarjeta en el PC:

**(a) La configuración de arranque** — en la partición FAT, con el Bloc de notas. En
**24.04 el fichero es `/boot/firmware/config.txt`**: `usercfg.txt` **no existe** y crearlo no
sirve de nada (Ubuntu abandonó el esquema de `pibootctl`; el porqué está en el cap. 3.4).
Añade al final, **con la cabecera `[all]`**:

```
[all]
dtoverlay=disable-bt
```

`enable_uart=1` **ya viene** en la imagen de 24.04. Y `[all]` es obligatorio: la imagen
termina en `[cm4]`, así que sin esa cabecera la línea quedaría dentro de `[cm4]` y **no se
aplicaría en un Pi 4** — existiría en el fichero sin hacer nada.

**(b) La regla udev y los `systemctl`** — necesitan el sistema arrancado, así que van por SSH:

```bash
sudo bash ~/atriz_migracion/scripts/fase_0_1_fix_uart.sh
```

El script detecta el fichero correcto, **respeta las secciones de placa** al comprobar si la
clave ya está activa, crea `/dev/rvr`, y apaga Bluetooth y `serial-getty`. Si `disable-bt` ya
estaba en efecto (porque hiciste (a) desde Windows y ya has arrancado), **te dirá que no hace
falta reiniciar** — y es cierto: udev y systemctl surten efecto al instante.

### B4 ✅ · Primer arranque y verificación — **verificado 2026-07-30**

**Manual, capítulo 3.5–3.6.**

```bash
lsb_release -a && uname -m && python3 --version   # 24.04.4 · aarch64 · 3.12.3
grep -o "console=[^ ]*" /boot/firmware/cmdline.txt      # solo console=tty1
ls -l /dev/rvr                                          # -> ttyAMA0
cat /proc/device-tree/aliases/uart0                     # /soc/serial@7e201000 (PL011)
sudo dmesg | grep -i ttyAMA                             # "is a PL011 rev2"
```

⚠️ **`dmesg` necesita `sudo` en 24.04** (`kernel.dmesg_restrict=1`). Sin él responde
`Operation not permitted`, y leído con prisa parece que el UART no existe. El
`cat /proc/device-tree/aliases/uart0` de la línea anterior da la misma información **sin
`sudo`** y es el atajo preferible.

**Y la prueba que de verdad importa**, con el RVR **encendido**:
```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/raw_uart.py
# esperado: "el RVR CONTESTA"
```
Si da 0 bytes: **apaga y enciende el robot antes de tocar configuración.** Un RVR dormido da
el síntoma idéntico a un cable mal puesto.

### B5 ✅ · Cerrar actualizaciones y credenciales de git — **verificado 2026-07-30**

Dos cosas que no estaban en la ruta y que hacen falta en toda instalación nueva.

**(a) Termina las actualizaciones ANTES de seguir.** Manual, cap. 3.5.1. La imagen trae
`unattended-upgrades` **activo**, y en cuanto el robot tiene red instala por su cuenta —
incluido un kernel nuevo. Si te lo dejas para después, un mismo reinicio aplicará dos cambios
y un fallo posterior no será atribuible.

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y iw                  # no viene, y el cap. 4 lo necesita
cat /var/run/reboot-required.pkgs 2>/dev/null    # ¿qué paquete pide reinicio?
```

**(b) Credenciales de git.** El repositorio es privado y un sistema recién instalado **no
tiene credenciales**: `git fetch` falla con `could not read Username` y todo lo que commitees
se queda solo en la tarjeta. 👤 Lo hace la persona, porque el token es un secreto:

```bash
git config --global credential.helper 'store --file ~/.git-credentials'
cd ~/atriz_migracion && git fetch origin    # Username: Bura-hub · Password: el PAT
chmod 600 ~/.git-credentials
git config --global user.name  "Tu Nombre"
git config --global user.email "tu@correo"  # sin esto, git no deja commitear
```

⚠️ **No pegues los tres comandos de golpe.** Si `git fetch` pide usuario, se comerá la línea
siguiente como respuesta. Uno a uno.

`fase_0_3_respaldo.sh` respalda `~/.git-credentials` desde el 2026-07-30, para no repetir esto
en el siguiente reflasheo — su pérdida es lo que obligó a rehacerlo aquí.

---

## ETAPA C — Poner el sistema a punto

### C1 ✅ · Higiene del sistema operativo — **verificado 2026-07-30**

**Manual, capítulo 4** (el por qué de cada medida, con la evidencia medida).

```bash
sudo bash ~/atriz_migracion/scripts/fase_1_higiene_so.sh
sudo reboot
```

El script **termina en rojo y con código 1 si algún paso no se pudo aplicar** — no lo des por
hecho solo porque haya terminado. Lee la sección «PASOS NO APLICADOS» del final.

⚠️ **Este reinicio te deja sin SSH un par de minutos, y esta máquina no tiene pantalla.** El
paso 9/9 comprueba `netplan generate` antes de dejarte reiniciar, porque el paso 5 deshabilita
`cloud-init` y el WiFi vive en un netplan que generó `cloud-init`. Ten el cable de `eth0` a
mano por si acaso.

**A partir de aquí las actualizaciones de seguridad son manuales** (`unattended-upgrades`
queda deshabilitado). Es lo que se quiere en un robot de laboratorio, pero hay que saberlo.

### C2 ✅ · Verificar contra la línea base — **verificado 2026-07-30**

**Manual, capítulo 4.3.** Compara con
[`00_auditoria/evidencia_24_04/`](00_auditoria/evidencia_24_04/) — **este mismo sistema antes
de optimizar**:

| Métrica | Antes (24.04 recién instalado) | Objetivo |
|---|---|---|
| `systemd-analyze` (userspace) | **1 min 39 s** (`cloud-final` = 1 min 7 s) | **< 15 s** |
| `ps -e \| wc -l` | **187 tareas** | **< 120** |
| governor | `ondemand` | `performance` |
| `journalctl --disk-usage` | 17.7 MB | decenas de MB (con tope de 32M) |
| `cat /proc/pressure/io` | `full total` 74.6 s / 34 min | mucho menor |
| `iw dev wlan0 get power_save` | (`iw` no instalado) | **`Power save: off`** |
| `systemctl get-default` | `graphical.target` | `multi-user.target` |
| `systemctl --failed` | — | vacío |

🔴 **No compares con `00_auditoria/evidencia/`.** Esa es la línea base del sistema **viejo**
(20.04 + Noetic, 29.5 s y 273 tareas). Son dos sistemas distintos, y mezclar sus números es
exactamente la deriva documentación-realidad que este repositorio existe para evitar.

**Y confirma que el UART sobrevivió al cambio de kernel**, que es lo que este reinicio
introduce además de la higiene:

```bash
uname -r                                     # ¿cambió el kernel?
ls -l /dev/rvr                               # -> ttyAMA0
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/raw_uart.py
```

---

## ETAPA D — GO / NO-GO · el punto de decisión

**Manual, capítulo 5.1.** **No instales ROS 2 antes de esto.**

```bash
sudo apt install -y python3-pip python3-venv
pip install --break-system-packages pyserial pyserial-asyncio

mkdir -p ~/atriz_ws/src && cd ~/atriz_ws/src
git clone -b ros2 https://github.com/Bura-hub/Atriz_rvr.git
#            ↑ `ros2`, NO `migracion-ros2`: esa es la rama vieja de ROS 1

# Con el RVR ENCENDIDO:
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

- **GO** → etapa E
- **NO-GO** → **PARA.** El script imprime las cuatro alternativas ordenadas por coste. Es una
  decisión de arquitectura, no algo a improvisar.

> El análisis estático fue muy favorable (0 patrones roubles en Python 3.12, un único
> `get_event_loop()` en la ruta usada), pero **análisis estático no es ejecución**.

---

## ETAPA E — ROS 2 y volver a donde estábamos

### E1 · Instalar ROS 2 Jazzy

**Manual, capítulo 5.2–5.5.** `ros-jazzy-ros-base`, **no** `desktop`.

⚠️ **COMPROBAR:** el método de las claves GPG cambia entre versiones. `apt-key add`, que
usaba el manual original, está obsoleto.

### E2 · Cómo volver a donde estábamos

El estado alcanzado el 2026-07-29 se reproduce con **cuatro cosas**, y todas están ya en los
repositorios:

| Qué | Dónde |
|---|---|
| `dtoverlay=disable-bt` + regla udev `/dev/rvr` | `scripts/fase_0_1_fix_uart.sh` |
| Código con `/dev/rvr` e `interval=60` | rama **`ros2`** de `Atriz_rvr` |
| Higiene del SO | `scripts/fase_1_higiene_so.sh` |
| Cómo verificar que funciona | manual, caps. 1.3, 2 y 8.2 |

> 📝 En esta etapa solo interesa el **SDK**, que es Python puro y no depende de ROS. La rama
> `ros2` ya trae el driver portado y compila; la rama vieja `migracion-ros2` es ROS 1 (catkin)
> y **no** compila con colcon — no la uses.

### E3 · Verificar UART y telemetría

**Manual, capítulos 1.3 y 2.**

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/raw_uart.py
# esperado: "el RVR CONTESTA (46 bytes)"

python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/sdk_full.py 60
# esperado: ~16.5 Hz en los 6 sensores de odometría
```

### E4 · Verificar el LIDAR

**Manual, capítulo 8.2.**

```bash
ls -l /dev/ttyUSB0
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/x2_parse.py
# esperado: 100 % de checksums válidos, ~2998 muestras/s
```

**Al llegar aquí has recuperado el estado del 2026-07-29, pero sobre ROS 2.**

---

## ETAPA F — El robot completo sobre ROS 2

✅ **Recorrida y verificada el 2026-07-31.** Al final de esta etapa el robot arranca con dos
comandos y `slam_toolbox` construye un mapa.

Todo el código vive en `Bura-hub/Atriz_rvr`, rama **`ros2`**. No hay que escribir nada: se
clona, se compila y se verifica.

### F1 ✅ · Clonar y compilar el workspace

```bash
mkdir -p ~/atriz_ws/src && cd ~/atriz_ws/src
git clone -b ros2 https://github.com/Bura-hub/Atriz_rvr.git
git -C ~/atriz_ws/src/Atriz_rvr fetch origin && git -C ~/atriz_ws/src/Atriz_rvr status -sb
#   ↑ regla nº1 del proyecto: `fetch` ANTES de leer o auditar código

# xacro NO viene en ros-base y hace falta para el URDF
sudo apt install -y ros-jazzy-xacro                                    # 👤 sudo

cd ~/atriz_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

⚠️ Si `ros2 run` dice «No executable found» con `colcon build` diciendo «Finished», falta
`setup.cfg` en el paquete Python. Manual, cap. 6.

### F2 ✅ · Driver del LIDAR — se compila desde fuentes

**No hay paquete apt**: `ros-jazzy-ydlidar-ros2-driver` y sus variantes **no existen**
(comprobado, `apt-cache search ydlidar` da 0 resultados). Manual, cap. 8.5a.

```bash
# 1. El SDK (instala en /usr/local)
cd ~ && git clone https://github.com/YDLIDAR/YDLidar-SDK.git
mkdir -p YDLidar-SDK/build && cd YDLidar-SDK/build
cmake .. && make -j2
sudo make install                                                      # 👤 sudo

# 2. El driver ROS 2 — rama `humble`, compila en Jazzy sin cambios
cd ~/atriz_ws/src
git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git
rm -rf ydlidar_ros2_driver/.git      # es código de terceros: no se mezcla con Atriz_rvr

# 3. La regla udev para /dev/ydlidar (por ID_PATH: el CP2102 no tiene serie única)
sudo cp ~/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/udev/99-ydlidar.rules \
        /etc/udev/rules.d/                                             # 👤 sudo
sudo udevadm control --reload-rules && sudo udevadm trigger            # 👤 sudo
ls -l /dev/ydlidar                   # -> ttyUSB0

cd ~/atriz_ws && colcon build --symlink-install
```

### F3 ✅ · SLAM

```bash
sudo apt install -y ros-jazzy-slam-toolbox                             # 👤 sudo
```

📝 **`ros-jazzy-nav2-map-server` no se instala todavía** (llega en la Fase 5). Consecuencia:
`/slam_toolbox/save_map` falla con `result=255` y el error real solo aparece en el log de
slam_toolbox (`Package 'nav2_map_server' not found`). Para guardar mapas hoy se usa
**`serialize_map`**, que es nativo. Manual, cap. 9.5.

### F4 ✅ · Arrancar y verificar

⚠️ **Los dos launch se arrancan JUNTOS y en este orden.** Reiniciar el driver por debajo de un
`slam_toolbox` ya en marcha lo deja con un hueco en su buffer TF y **deja de procesar**, sin
dar ningún error. Invalidó una prueba entera. Manual, cap. 9.7.

```bash
source ~/atriz_ws/install/setup.bash
ros2 launch atriz_rvr_bringup robot.launch.py     # terminal 1
ros2 launch atriz_rvr_bringup slam.launch.py      # terminal 2
```

Verificación, y **cada línea comprueba algo que ya falló en silencio alguna vez**:

```bash
ros2 lifecycle get /slam_toolbox                 # active [3] ← si dice `unconfigured`, cap. 9.2
ros2 run tf2_ros tf2_echo odom base_footprint    # ← LA prueba. NO uses `odom laser`: cap. 9.4
ros2 run tf2_ros tf2_echo map base_footprint     # lo que añade SLAM
ros2 topic hz /odom                              # 16.7 Hz ← si es 0, el RVR se durmió: cap. 9.8
ros2 topic hz /scan                              # ~10 Hz
ros2 topic hz /map                               # 0.200 Hz
ros2 topic echo /battery_state --once            # llega cada 30 s: es el keepalive
```

Y la prueba que de verdad cierra la fase — **mueve el robot**:

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_slam_ros2.py
```

⚠️ **Necesita espacio y el robot NO esquiva obstáculos** (solo tiene watchdog). Con el robot en
el centro: **1 m por delante** (hacia donde mira), **1 m por detrás**, **40 cm a cada lado**, y
nada a menos de 60 cm. El LIDAR va a 17.5 cm barriendo en horizontal, así que pasa por encima
de zócalos y cajas bajas: «despejado a ras de suelo» no basta.

🔴 **Girar sobre el eje NO hace crecer el mapa.** El X2 barre los 360°, así que girar en el
sitio vuelve a ver lo mismo desde el mismo punto. Para saber si SLAM mapea hay que
**desplazar** el robot, y no bastan 40 cm: `slam_toolbox` cuenta la distancia desde el **último
nodo del grafo**. Hicieron falta ~0.85 m.

Resultado esperado: **el mapa crece**. En `rvr-01`, 2367 → 3299 celdas (5.92 → 8.25 m²) tras
1.78 m de recorrido.

### F5 ⏳ · Lo que queda

1. **Caracterizar la deriva de la localización** — dos corridas dieron 87.8 cm y 0.9 cm de
   error al volver al punto de partida. Repetir varias veces en espacio despejado.
2. **La inclinación de ~8°** del robot, confirmada por tres vías independientes (árbol TF,
   `Roll` de la IMU y acelerómetro). Causa sin determinar. Para SLAM 2D funciona; para Nav2 hay
   que resolverla.
3. ✅ **Los tres bugs de marcos de `/odom` están arreglados y verificados** (2026-07-31,
   manual **cap. 10**). Los sensores del RVR siempre estuvieron bien; fallaba cómo el driver
   los combinaba. Ahora el yaw arranca en +0.00°, la dirección de avance coincide con él
   (+0.03°) y `odom.twist.linear` da la velocidad en el marco del robot con un 2 % de error.
4. ✅ **Nav2 NAVEGA** (manual **cap. 11**): dos objetivos autónomos con 9–10 cm de error.
   Instala `ros-jazzy-navigation2`, **no** `nav2-bringup`: son 312 paquetes de simulador de
   más, y acabarían en la imagen dorada de los 16 robots.
4. **Nav2** (plan, Fase 4b) y los **16 servicios y 4 topics** del driver sin portar.
5. **Plataforma web** (Fase 5) — al final. **Arreglar primero la parada de emergencia**, que
   está confirmada como no funcional.
6. **Los 16 robots** ([`FLOTA.md`](03_operacion/FLOTA.md)) — el trabajo se hace **una vez**:
   `scripts/fase_6_preparar_imagen_dorada.sh` convierte este robot en imagen dorada, y cada
   robot nuevo cuesta **~3 minutos atendidos** (grabar, cambiar un número en `robot_id.txt`,
   anotar la MAC). `atriz-first-boot.service` fija hostname, `ROS_DOMAIN_ID` y claves solo.

---

## Si algo va mal

| Situación | Dónde mirar |
|---|---|
| El robot no responde | [`RUNBOOK.md`](03_operacion/RUNBOOK.md) → «Cuando algo falla» |
| El LIDAR no aparece | `RUNBOOK.md` → «El LIDAR no aparece» |
| Hay que volver a Noetic | [`RECUPERACION.md`](03_operacion/RECUPERACION.md) §2 |
| No sé en qué punto estoy | [`TRASPASO.md`](TRASPASO.md) |
| ¿Por qué se decidió X? | [`ARQUITECTURA.md`](03_operacion/ARQUITECTURA.md) |

**Las tres trampas que más tiempo cuestan** (detalle en `CLAUDE.md`):

1. **Un robot dormido parece un cable roto.** Apaga y enciende el robot antes de tocar nada.
2. **Que el nodo arranque no prueba que el enlace funcione.** El check de firmware traga
   excepciones. Usa `raw_uart.py`.
3. **`uart0_pins` vacío tras `disable-bt` es normal**, no un fallo.

---

## Recordatorio final

**Los capítulos 3 y 4 ya están ✅ VERIFICADOS** (2026-07-30): se recorrieron sobre la máquina
real y se corrigieron sobre la marcha. El 3.4 estaba equivocado en su suposición principal
(daba por hecho que existiría `usercfg.txt`) y el capítulo 4 escondía un paso que no hacía
nada. Ambas correcciones están donde ocurrieron, no en un mensaje.

**El capítulo 5 también quedó ✅ VERIFICADO** (2026-07-30), y también hubo que corregirlo: su
apartado 5.5 pedía `ros2 run demo_nodes_cpp talker`, y `demo_nodes_cpp` **no viene en
`ros-base`**. Se sustituyó por una prueba equivalente con `ros2 topic pub`/`echo`/`hz`.

**Los capítulos que siguen NO ESCRITOS son el 6 y siguientes** (driver en `rclpy`, URDF, SLAM,
web, flota). Se redactan al ejecutar las fases 2 a 6 del plan, capítulo a capítulo, tras
verificar cada paso. Al hacerlo, **corrige el documento en el mismo momento** y marca ✅ con la
fecha. No en un mensaje de chat: en el repositorio.

Y la regla que hizo falta en esta instalación, por si sirve en la siguiente: **un cambio por
reinicio.** Si aplicas dos cosas y algo se rompe, no sabrás cuál fue.
