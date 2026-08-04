#!/usr/bin/env bash
#
# verificar_robot.sh — ¿está este robot como debe estar?
#
#     bash verificar_robot.sh              # todo lo que no necesita root ni robot
#     bash verificar_robot.sh --hardware   # además habla con el RVR y el LIDAR
#     bash verificar_robot.sh --breve      # solo el resumen y los fallos
#
#     Código de salida:  0 = todo bien   ·   1 = hay fallos   ·   2 = hay avisos
#
# POR QUÉ EXISTE
#
#   El 2026-07-30 se verificó rvr-01 a mano, con unos 25 comandos sueltos, y
#   aparecieron CINCO fallos que no se manifestaban como error:
#
#     · un script abortaba antes de crear /dev/rvr
#     · un servicio systemd en verde que no hacía nada (faltaba el binario)
#     · snapd "disabled" y corriendo, porque su socket lo reactivaba
#     · una herramienta reportando 741 Hz en un sensor de 10 Hz
#     · un verificador dando falso positivo por mayúsculas
#
#   Repetir esa revisión a ojo en 16 robots garantiza que algo se cuele. Este
#   script convierte ese conocimiento en aserciones ejecutables: no informa de
#   lo que hay, sino de si coincide con lo que DEBE haber.
#
#   Regla de oro del fichero: **comprobar el efecto, no la intención.**
#   `systemctl is-enabled` miente (snapd). `systemctl is-active` de un servicio
#   oneshot no dice si hizo su trabajo. Se comprueba el estado resultante.
#
# QUÉ NO HACE
#
#   No arregla nada. Si algo falla, dice qué comando lo arregla y para.
#
# ESTADO
#   ✅ Probado contra rvr-01 el 2026-07-30 (Ubuntu Server 24.04.4, kernel 1060).
#   ⏳ Las comprobaciones de ROS 2, del driver y de rosbridge se añaden cuando
#      esas piezas existan. Los bloques están marcados como PENDIENTE.
#
set -uo pipefail

HARDWARE=0; BREVE=0
for a in "$@"; do
    case "$a" in
        --hardware) HARDWARE=1 ;;
        --breve)    BREVE=1 ;;
        -h|--help)  sed -n '2,40p' "$0" | sed 's/^#//'; exit 0 ;;
        *) echo "opción desconocida: $a" >&2; exit 64 ;;
    esac
done

VERDE=$'\033[92m'; ROJO=$'\033[91m'; AMAR=$'\033[93m'; AZUL=$'\033[94m'; GRIS=$'\033[90m'; FIN=$'\033[0m'
FALLOS=(); AVISOS=(); N_OK=0

sec()  { [[ $BREVE -eq 1 ]] || printf '\n%s▶ %s%s\n' "$AZUL" "$1" "$FIN"; }
_ok()  { N_OK=$((N_OK+1)); [[ $BREVE -eq 1 ]] || printf '  %s✓%s %s\n' "$VERDE" "$FIN" "$1"; }
_mal() { FALLOS+=("$1${2:+  →  $2}"); printf '  %s✗%s %s\n' "$ROJO" "$FIN" "$1"; }
_avi() { AVISOS+=("$1${2:+  →  $2}"); [[ $BREVE -eq 1 ]] || printf '  %s!%s %s\n' "$AMAR" "$FIN" "$1"; }
_nota(){ [[ $BREVE -eq 1 ]] || printf '  %s· %s%s\n' "$GRIS" "$1" "$FIN"; }

# comprobar <descripción> <valor obtenido> <valor esperado> [arreglo]
comprobar() {
    if [[ "$2" == "$3" ]]; then _ok "$1: $2"
    else _mal "$1: es '$2', se esperaba '$3'" "${4:-}"; fi
}
# comprobar_contiene <descripción> <valor> <subcadena esperada> [arreglo]
comprobar_contiene() {
    if [[ "$2" == *"$3"* ]]; then _ok "$1: $2"
    else _mal "$1: es '$2', debía contener '$3'" "${4:-}"; fi
}

printf '%s' "$AZUL"
cat <<'EOF'
======================================================================
  verificar_robot.sh — ¿está este robot como debe estar?
======================================================================
EOF
printf '%s' "$FIN"
_nota "host $(hostname) · $(date -Is) · kernel $(uname -r)"
[[ $HARDWARE -eq 0 ]] && _nota "sin --hardware: no se hablará con el RVR ni con el LIDAR"

# ─────────────────────────────────────────────────────────────────────────────
sec "1 · Sistema base"

comprobar "arquitectura" "$(uname -m)" "aarch64"
comprobar_contiene "distribución" "$(lsb_release -ds 2>/dev/null || echo '?')" "24.04"
PY="$(python3 --version 2>&1 | awk '{print $2}')"
case "$PY" in
    3.12.*) _ok "python3: $PY" ;;
    *) _mal "python3: $PY, se esperaba 3.12.x" "3.12 es el Python de 24.04; otra versión significa que el SO no es el previsto" ;;
esac
case "$(hostname)" in
    rvr-[0-9][0-9]) _ok "hostname: $(hostname)" ;;
    *) _mal "hostname: '$(hostname)', se esperaba rvr-NN" \
            "edita /boot/firmware/robot_id.txt y borra /var/lib/atriz-first-boot.done" ;;
esac

# ─────────────────────────────────────────────────────────────────────────────
sec "2 · Arranque y UART (lo que decide si el robot habla)"

# cmdline.txt NO debe reservar el puerto serie para la consola del kernel
if grep -q 'console=serial' /boot/firmware/cmdline.txt 2>/dev/null; then
    _mal "cmdline.txt reserva el serie para la consola" \
         "quita 'console=serial0,115200' de /boot/firmware/cmdline.txt y reinicia"
else
    _ok "cmdline.txt no reserva el puerto serie ($(grep -o 'console=[^ ]*' /boot/firmware/cmdline.txt | tr '\n' ' '))"
fi

# El device-tree del arranque ACTUAL es la única prueba de que disable-bt surtió
# efecto. Un grep a config.txt solo dice qué se pidió, no qué se aplicó — y con
# las secciones de placa ([cm4], [pi4]...) puede pedirse y no aplicarse.
UART0="$(tr -d '\0' < /proc/device-tree/aliases/uart0 2>/dev/null || true)"
if [[ "$UART0" == *7e201000* ]]; then
    _ok "uart0 -> $UART0 (PL011, reloj estable)"
else
    _mal "uart0 -> ${UART0:-desconocido}, se esperaba /soc/serial@7e201000 (PL011)" \
         "falta 'dtoverlay=disable-bt' bajo [all] en config.txt; usa fase_0_1_fix_uart.sh y reinicia"
fi
MINI="$(tr -d '\0' < /proc/device-tree/soc/serial@7e215040/status 2>/dev/null || echo '?')"
[[ "$MINI" == disabled ]] && _ok "mini-UART: disabled (normal y deseable tras disable-bt)" \
                          || _avi "mini-UART: '$MINI' (se esperaba disabled)"

# /dev/rvr: el nombre estable. El código nunca debe usar ttyAMA0 directamente.
if [[ -L /dev/rvr ]]; then
    DEST="$(readlink /dev/rvr)"
    comprobar "/dev/rvr apunta a" "$DEST" "ttyAMA0" "revisa /etc/udev/rules.d/99-rvr.rules"
    if [[ -r /dev/rvr && -w /dev/rvr ]]; then
        _ok "/dev/rvr legible y escribible por $USER"
    else
        _mal "/dev/rvr sin permisos para $USER" \
             "sudo usermod -aG dialout $USER  (y cerrar y abrir sesión)"
    fi
else
    _mal "/dev/rvr NO existe" "sudo bash \$(dirname \$0)/fase_0_1_fix_uart.sh"
fi
[[ -f /etc/udev/rules.d/99-rvr.rules ]] && _ok "regla udev 99-rvr.rules presente" \
    || _mal "falta /etc/udev/rules.d/99-rvr.rules" "sudo bash \$(dirname \$0)/fase_0_1_fix_uart.sh"

# Nada debe ocupar el UART. Un getty en ttyAMA0 se come los bytes del robot.
for u in serial-getty@ttyAMA0.service serial-getty@ttyS0.service; do
    E="$(systemctl is-enabled "$u" 2>&1 | head -1)"
    case "$E" in
        disabled|masked|not-found) _ok "$u: $E" ;;
        *) _mal "$u está '$E' y ocupa el UART" "sudo systemctl disable --now $u" ;;
    esac
done

# Bluetooth: en 24.04 la unidad no existe, y eso es correcto (no hay adaptador).
BT="$(systemctl is-active bluetooth 2>&1 | head -1)"
case "$BT" in
    inactive|unknown|failed) _ok "bluetooth: $BT" ;;
    *) [[ "$BT" == "active" ]] && _mal "bluetooth activo: compite por el PL011" \
            "sudo systemctl disable --now bluetooth" || _ok "bluetooth: $BT (unidad ausente en 24.04)" ;;
esac

# ─────────────────────────────────────────────────────────────────────────────
sec "3 · LIDAR YDLIDAR X2"

if lsusb 2>/dev/null | grep -qi '10c4:ea60'; then
    _ok "adaptador CP210x detectado en USB"
else
    _avi "no se ve el CP2102 (10c4:ea60) en lsusb" "¿está enchufado el LIDAR?"
fi
lsmod 2>/dev/null | grep -q '^cp210x' && _ok "módulo cp210x cargado" \
    || _avi "módulo cp210x no cargado" "viene en linux-modules-*-raspi; se carga al conectar"
if [[ -c /dev/ttyUSB0 ]]; then
    _ok "/dev/ttyUSB0 presente"
    IDP="$(udevadm info -q property -n /dev/ttyUSB0 2>/dev/null | sed -n 's/^ID_PATH=//p')"
    _nota "ID_PATH=$IDP  (el serial es genérico '0001'; para la regla udev de la flota usar ID_PATH)"
else
    _avi "/dev/ttyUSB0 no existe" "¿está enchufado el LIDAR?"
fi

# ─────────────────────────────────────────────────────────────────────────────
sec "4 · Higiene del SO (efecto real, no 'is-enabled')"

comprobar "default target" "$(systemctl get-default)" "multi-user.target" \
          "sudo systemctl set-default multi-user.target"
comprobar "governor de CPU" "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)" \
          "performance" "sudo systemctl enable --now cpu-performance.service"

# El power-save del WiFi: comprobar el ESTADO, no que el servicio esté activo.
# OJO con las mayúsculas: iw imprime "Power save: off". Buscarlo en minúsculas
# fue un falso positivo real el 2026-07-30.
IFACE="$(ls /sys/class/net 2>/dev/null | grep -m1 '^wl' || echo wlan0)"
if command -v iw >/dev/null; then
    PS="$(iw dev "$IFACE" get power_save 2>&1 | grep -oi 'power.save:.*' || echo '(sin salida)')"
    if [[ "${PS,,}" == *off* ]]; then _ok "$IFACE power-save: $PS"
    else _mal "$IFACE power-save: $PS (introduce latencias de 100-300 ms)" \
              "sudo systemctl enable --now wifi-no-powersave.service"; fi
else
    _mal "'iw' no está instalado: no se puede comprobar ni apagar el power-save" "sudo apt install -y iw"
fi

# cloud-init se desactiva con un FICHERO, no con systemctl: 'is-enabled' seguirá
# diciendo 'enabled' y es correcto. Lo que importa es que esté inactivo.
if [[ -f /etc/cloud/cloud-init.disabled ]]; then
    _ok "cloud-init desactivado (/etc/cloud/cloud-init.disabled presente)"
    _nota "'systemctl is-enabled cloud-init' dirá 'enabled' y NO es un problema"
elif [[ -d /etc/cloud ]]; then
    _mal "cloud-init sigue activo (se llevaba 1 min 7 s del arranque)" "sudo touch /etc/cloud/cloud-init.disabled"
else
    _ok "cloud-init no está instalado"
fi

# snapd: aquí is-enabled MIENTE. snapd.socket reactiva el servicio.
SNAP_A="$(systemctl is-active snapd.service 2>&1 | head -1)"
SNAP_S="$(systemctl is-active snapd.socket 2>&1 | head -1)"
if [[ "$SNAP_A" == active || "$SNAP_S" == active ]]; then
    _mal "snapd sigue vivo (service=$SNAP_A socket=$SNAP_S)" \
         "sudo systemctl disable --now snapd.socket snapd.seeded.service snapd"
else
    _ok "snapd inactivo (service=$SNAP_A socket=$SNAP_S)"
fi

for t in apt-daily.timer apt-daily-upgrade.timer unattended-upgrades; do
    E="$(systemctl is-enabled "$t" 2>&1 | head -1)"
    case "$E" in
        disabled|masked|not-found) _ok "$t: $E" ;;
        *) _avi "$t está '$E': el robot puede actualizarse solo a mitad de un experimento" \
                "sudo systemctl disable --now $t" ;;
    esac
done

# Ficheros con extension no reconocida en sources.list.d/ hacen que apt imprima
# un aviso en CADA ejecucion. Suele ser un respaldo mal colocado.
RUIDO="$(ls /etc/apt/sources.list.d/ 2>/dev/null | grep -vE '\.(list|sources)$' | tr '\n' ' ')"
[[ -z "$RUIDO" ]] && _ok "sources.list.d/ limpio (sin ficheros que apt ignore)" \
    || _avi "apt avisara en cada ejecucion por: $RUIDO" \
            "muevelos fuera: sudo mkdir -p /root/respaldos-apt && sudo mv /etc/apt/sources.list.d/*.bak-* /root/respaldos-apt/"

comprobar_contiene "noatime en /" "$(findmnt -no OPTIONS / 2>/dev/null)" "noatime" \
                   "añade ',noatime' a la línea de / en /etc/fstab"

# La imagen de 24.04 para Raspberry Pi viene SIN noble-updates, y eso impide
# instalar cualquier paquete -dev (por tanto, colcon build). Ver manual 5.2.0.
if grep -qhE '^Suites:.*noble-updates' /etc/apt/sources.list.d/*.sources 2>/dev/null; then
    _ok "repositorio noble-updates habilitado"
else
    _mal "falta el repositorio 'noble-updates': no se podrán instalar paquetes -dev" \
         "sudo sed -i '0,/^Suites: noble\$/s//Suites: noble noble-updates/' /etc/apt/sources.list.d/ubuntu.sources && sudo apt update"
fi

JOUR="$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[MG]' | head -1 || echo '?')"
case "$JOUR" in
    *G) _mal "journal ocupa $JOUR: castiga la microSD" "SystemMaxUse=32M en /etc/systemd/journald.conf" ;;
    *M) _ok "journal: $JOUR" ;;
    *)  _avi "no se pudo leer el tamaño del journal" ;;
esac

FALL="$(systemctl --failed --no-legend --no-pager 2>/dev/null | wc -l)"
comprobar "servicios en fallo" "$FALL" "0" "systemctl --failed  para ver cuáles"

# ─────────────────────────────────────────────────────────────────────────────
sec "5 · Salud del hardware"

TEMP=$(( $(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0) / 1000 ))
if   (( TEMP == 0 ));  then _avi "no se pudo leer la temperatura"
elif (( TEMP < 70 ));  then _ok "temperatura: ${TEMP} °C"
elif (( TEMP < 80 ));  then _avi "temperatura: ${TEMP} °C (alta; vigilar bajo carga)"
else _mal "temperatura: ${TEMP} °C" "riesgo de throttling: revisa ventilación"; fi

if command -v vcgencmd >/dev/null; then
    TH="$(vcgencmd get_throttled 2>/dev/null)"
    comprobar "throttling / under-voltage" "$TH" "throttled=0x0" \
              "0x0 = nunca ha habido; cualquier otro valor apunta a la alimentación"
fi
_nota "espacio en /: $(df -h / | awk 'NR==2{print $4" libres ("$5" usado)"}')"
_nota "swap: $(free -h | awk '/^Swap:/{print $2}') (0B es lo correcto: desgasta la SD)"

# El objetivo "< 120 tareas" del plan original estaba MAL PLANTEADO: 'ps -e'
# cuenta ~123 hilos de kernel, que son el suelo del sistema. Se mide lo que sí
# se puede bajar.
KERN=$(ps -e -o ppid= | awk '$1==2' | wc -l)
USUARIO=$(( $(ps -e --no-headers | wc -l) - KERN ))
SERV=$(systemctl list-units --type=service --state=running --no-legend --no-pager 2>/dev/null | wc -l)
_nota "procesos de usuario: $USUARIO (hilos de kernel: $KERN, que no se pueden bajar)"
if (( SERV <= 20 )); then _ok "servicios en ejecución: $SERV"
else _avi "servicios en ejecución: $SERV (se esperaban ≤ 20)" "systemctl list-units --state=running"; fi

# ─────────────────────────────────────────────────────────────────────────────
sec "6 · Dependencias de Python del SDK"

# Las TRES son obligatorias. aiohttp no se usa para hablar con el robot, pero
# sphero_sdk/__init__.py lo importa sin condiciones: sin él, el SDK no importa.
for par in "serial:python3-serial (apt)" \
           "serial_asyncio:pyserial-asyncio (pip --break-system-packages; NO existe en apt)" \
           "aiohttp:python3-aiohttp (apt)"; do
    MOD="${par%%:*}"; COMO="${par#*:}"
    V="$(python3 -c "import $MOD,sys; sys.stdout.write(getattr($MOD,'__version__','?'))" 2>/dev/null)"
    [[ -n "$V" ]] && _ok "$MOD $V" || _mal "falta el módulo $MOD" "instálalo: $COMO"
done

# ─────────────────────────────────────────────────────────────────────────────
sec "7 · Código del robot"

# La identidad de git es GLOBAL, no por repositorio. Sin ella 'git commit' falla
# en cualquier repo — y el 2026-07-30 el 'git push' de una rama SI funciono sin
# ella, subiendola sin el commit, asi que el fallo pasa desapercibido.
if git config --global user.email >/dev/null 2>&1; then
    _ok "identidad de git: $(git config --global user.email)"
else
    _avi "sin identidad de git global: 'git commit' fallará" \
         "git config --global user.name '…' && git config --global user.email '…'"
fi

WS="$HOME/atriz_ws/src/Atriz_rvr"
if [[ -d "$WS/.git" ]]; then
    RAMA="$(git -C "$WS" rev-parse --abbrev-ref HEAD)"
    _ok "Atriz_rvr en $WS (rama $RAMA, $(git -C "$WS" rev-parse --short HEAD))"
    SUCIO="$(git -C "$WS" status --porcelain | grep -v '^??' || true)"
    [[ -z "$SUCIO" ]] && _ok "sin cambios sin commitear" \
        || _avi "hay cambios sin commitear en Atriz_rvr" "git -C $WS status"
    # Los dos arreglos que hacen que el robot funcione. Si faltan, el driver
    # abrirá un puerto que existe pero no lleva el UART, y a 3.85 Hz.
    DAL="$WS/atriz_rvr_driver/scripts/sphero_sdk/asyncio/client/dal/serial_async_dal.py"
    grep -q "port_id='/dev/rvr'" "$DAL" 2>/dev/null \
        && _ok "SDK usa /dev/rvr por defecto (commit 67c8776)" \
        || _mal "el SDK NO usa /dev/rvr por defecto" "¿clonaste sin -b ros2? un clone a secas da main, que no lleva 67c8776"
    # 🔴 CORREGIDO 2026-07-31: esto comprobaba `Atriz_rvr_node.py`, que es el
    # driver de ROS 1. Sigue en el repo como herencia, así que la comprobación
    # PASABA mirando un fichero que no se ejecuta — deriva silenciosa, justo lo
    # que este script existe para evitar. El driver de ROS 2 es otro y usa un
    # parámetro, no una constante.
    DRV="$WS/atriz_rvr_driver/scripts/atriz_rvr_driver/rvr_driver_node.py"
    if [[ -f "$DRV" ]]; then
        _ok "driver de ROS 2 presente (rvr_driver_node.py)"
        grep -q "streaming_interval_ms" "$DRV" \
            && _ok "streaming parametrizado (60 ms → 16.67 Hz)" \
            || _mal "el driver no expone streaming_interval_ms" "¿rama equivocada?"
    else
        _mal "falta el driver de ROS 2" "git -C $WS checkout ros2"
    fi
else
    _avi "no existe $WS" "git clone -b ros2 https://github.com/Bura-hub/Atriz_rvr.git ~/atriz_ws/src/"
fi

# ─────────────────────────────────────────────────────────────────────────────
sec "8 · ROS 2"

if [[ -d /opt/ros/jazzy ]]; then
    # OJO: que exista /opt/ros/jazzy y que 'source setup.bash' funcione NO prueba
    # que la instalacion haya terminado. apt desempaqueta primero y configura
    # despues; entre las dos fases setup.bash ya existe y dpkg dice 'unpacked'.
    # Verificado el 2026-07-30: setup.bash presente, ROS_DISTRO=jazzy, y CERO
    # paquetes en estado 'ii'. Se comprueba el estado de dpkg, no el fichero.
    # OJO: 'grep -c' imprime 0 Y ADEMAS sale con codigo 1 cuando no hay
    # coincidencias, asi que un '|| echo 0' concatena un segundo cero y la
    # variable queda como "0\n0", rompiendo la aritmetica. Es el mismo patron
    # que rompio la comprobacion de 'systemctl is-enabled' este mismo dia.
    # Solucion: no poner el '|| echo 0' (grep -c ya imprime 0) y quedarse con
    # la primera linea por seguridad.
    N_II="$(dpkg -l 'ros-jazzy-*' 2>/dev/null | grep -c '^ii' | head -1)"
    N_II=${N_II:-0}
    if (( N_II > 50 )); then
        _ok "ROS 2 Jazzy: $N_II paquetes instalados y configurados"
    elif (( N_II > 0 )); then
        _mal "solo $N_II paquetes ros-jazzy configurados: la instalación está a medias" \
             "espera a que apt termine, o: sudo dpkg --configure -a"
    else
        _mal "/opt/ros/jazzy existe pero NINGÚN paquete está configurado" \
             "apt desempaquetó y no ha configurado. Espera a que termine, o: sudo dpkg --configure -a"
    fi

    # ¿Queda algo a medio instalar en TODO el sistema?
    A_MEDIAS="$(dpkg -l 2>/dev/null | grep -vE '^(ii|rc|un)' | grep -cE '^[a-z]{2} ' | head -1)"
    A_MEDIAS=${A_MEDIAS:-0}
    (( A_MEDIAS == 0 )) && _ok "ningún paquete a medio instalar" \
        || _avi "$A_MEDIAS paquete(s) en estado intermedio" \
                "dpkg -l | grep -vE '^(ii|rc)' — puede hacer falta: sudo dpkg --configure -a"

    # ros-base, no desktop: son ~236 paquetes con Gazebo y RViz en un robot sin
    # pantalla, y fue una de las causas de lentitud del sistema anterior.
    dpkg -l ros-jazzy-desktop 2>/dev/null | grep -q '^ii' \
        && _mal "ros-jazzy-desktop instalado: Gazebo y RViz en un robot sin pantalla" \
                "debe ser ros-jazzy-ros-base. RViz2 va en un portátil" \
        || _ok "sin ros-jazzy-desktop (correcto: ros-base)"

    for p in ros-jazzy-ros-base ros-jazzy-rclpy ros-dev-tools; do
        EST="$(dpkg-query -W -f='${Status}' "$p" 2>/dev/null || echo 'ausente')"
        case "$EST" in
            *"ok installed") _ok "$p instalado y configurado" ;;
            *unpacked)       _mal "$p desempaquetado pero SIN configurar" "sudo dpkg --configure -a" ;;
            *)               _avi "$p: $EST" ;;
        esac
    done
    command -v colcon >/dev/null && _ok "colcon disponible" \
        || _mal "falta colcon: no se podrá compilar el workspace" "apt install ros-dev-tools"

    # ROS_DOMAIN_ID: uno por robot. Es la Decisión 1 de ARQUITECTURA.md, no un
    # detalle: dos robots en el mismo dominio se ven entre si en DDS.
    if [[ -n "${ROS_DOMAIN_ID:-}" ]]; then
        ESPERADO="$(hostname | grep -oE '[0-9]+$' | sed 's/^0*//')"
        comprobar "ROS_DOMAIN_ID" "$ROS_DOMAIN_ID" "$ESPERADO" \
                  "un dominio por robot; ARQUITECTURA.md D1. Lo fija /etc/profile.d/atriz-robot.sh"
    else
        _avi "ROS_DOMAIN_ID no definido en este shell" \
             "en la flota lo pone /etc/profile.d/atriz-robot.sh; en el robot de referencia, ~/.bashrc"
    fi


    # ── Arbol TF ──────────────────────────────────────────────────────────
    # 🔴 LA comprobacion es `odom -> base_footprint`, NO `odom -> laser`.
    #
    # Hasta el 2026-07-30 este script comprobaba `odom -> laser`, y PASABA
    # mientras el arbol estaba partido en dos: el driver publicaba
    # odom->base_link y el URDF base_footprint->base_link, asi que base_link
    # tenia DOS PADRES. `odom -> laser` resolvia por el camino equivocado
    # (odom -> base_link -> laser) y base_footprint colgaba de otro arbol.
    # slam_toolbox repetia "Failed to compute odom pose" y esta verificacion
    # decia que todo estaba bien.
    #
    # La regla que queda: COMPRUEBA EL TRANSFORM QUE PIDE EL CONSUMIDOR, con
    # sus frames exactos. slam_toolbox pide `base_frame: base_footprint`, asi
    # que eso es lo que hay que comprobar. Un tf2_echo que resuelve prueba que
    # hay UN camino, no que el arbol este bien.
    if command -v ros2 >/dev/null && [[ -n "${ROS_DISTRO:-}" ]]; then
        if timeout 8 ros2 run tf2_ros tf2_echo odom base_footprint >/dev/null 2>&1; then
            _ok "arbol TF: odom -> base_footprint resuelve (es lo que pide slam_toolbox)"
        else
            _nota "arbol TF: odom -> base_footprint no resuelve ahora mismo."
            _nota "  Solo es un fallo si robot.launch.py esta corriendo."
            _nota "  Si el driver publica odom->base_link, base_link tiene dos padres"
            _nota "  y el arbol esta partido: manual cap. 9.4."
        fi
        # La cadena completa, como comprobacion secundaria.
        timeout 8 ros2 run tf2_ros tf2_echo odom laser >/dev/null 2>&1 \
            && _ok "arbol TF: odom -> laser resuelve (la cadena hasta el sensor)"

        # 🔴 EL RITMO de /odom, no que el topic exista.
        #
        # El 2026-07-30 el RVR se durmio solo y el driver siguio vivo al 12.3 %
        # de CPU con /odom registrado (Publisher count: 1) publicando CERO, sin
        # un solo error. Comprobar que el nodo o el topic existen NO detecta
        # esto; hay que medir el ritmo. Ver manual, cap. 9.8.
        # 🔴 SE MIRA EL PROCESO, NO `ros2 topic list`. El daemon de ROS conserva
        #    topics de nodos ya muertos, así que con el driver PARADO `/odom`
        #    seguía apareciendo y esta comprobación gritaba «el RVR está
        #    dormido» sobre un robot que simplemente estaba apagado. Falso
        #    positivo, 2026-07-31.
        if ps -eo comm | grep -qx 'rvr_driver_node'; then
            # 📝 NO se usa `ros2 topic hz`, y el MOTIVO cambió el 2026-08-01:
            #    se creía que no podía medir `/odom` por QoS, y **eso era falso**
            #    (evidencia 45: da 16.525 Hz sobre un topic BEST_EFFORT). La
            #    razón buena es otra: un suscriptor propio da **jitter y huecos**,
            #    elige el QoS explícitamente, y no depende de la versión de
            #    `ros2cli`, que se actualiza sola.
            #    RELIABLE sin opción de cambiarlo en Jazzy. DDS no empareja, no
            #    llega nada, y da 0 Hz SIEMPRE — con el robot funcionando
            #    perfectamente. Es la misma trampa de QoS que ya costó la parada
            #    de emergencia (manual, cap. 15.1), aquí dentro del verificador.
            HZ_ODOM="$(timeout 15 python3 -c '
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry
rclpy.init()
n = Node("verificar_hz_odom"); c = [0]
n.create_subscription(Odometry, "odom", lambda m: c.__setitem__(0, c[0] + 1),
                      QoSProfile(depth=50, reliability=ReliabilityPolicy.BEST_EFFORT))
# Ejecutor PERSISTENTE. Con rclpy.spin_once(n, ...) en bucle salen 11 Hz sobre un
# robot que va a 16.5: cada llamada engancha y desengancha el nodo del ejecutor
# global, y en ese hueco se pierden mensajes. Medido las dos formas el mismo dia.
ex = SingleThreadedExecutor(); ex.add_node(n)
t0 = time.monotonic()
while time.monotonic() - t0 < 8.0:
    ex.spin_once(timeout_sec=0.1)
print(f"{c[0] / (time.monotonic() - t0):.2f}")
' 2>/dev/null)"
            HZ_ODOM="${HZ_ODOM:-0}"
            # El firmware no baja de interval=60 ms => 16.5-16.7 Hz. Por debajo
            # de 10 Hz algo va mal; a 0 el RVR esta dormido o el enlace caido.
            if awk -v h="$HZ_ODOM" 'BEGIN{exit !(h > 10)}'; then
                _ok "/odom a ${HZ_ODOM} Hz (esperado ~16.7)"
            elif awk -v h="$HZ_ODOM" 'BEGIN{exit !(h > 0)}'; then
                _mal "/odom solo a ${HZ_ODOM} Hz (esperado ~16.7)" \
                     "revisa streaming_interval_ms=60 en robot.launch.py"
            else
                _mal "el driver CORRE pero /odom no publica NADA: el RVR esta dormido" \
                     "reinicia el driver. El proceso no muere, asi que systemd no lo arregla. Manual cap. 9.8"
            fi
        else
            _nota "rvr_driver_node no esta corriendo: no hay ritmo que medir."
        fi

        # 🔴 EL YAW DEBE ARRANCAR EN ~0. Es la comprobacion mas barata de que la
        # correccion de marcos sigue en su sitio (manual cap. 10).
        #
        # `reset_yaw()` del RVR NO pone a cero el yaw: el cuaternion arrastra su
        # origen desde que se ENCENDIO el robot. Cinco arranques dieron cinco
        # offsets distintos (+51.1, +52.7, +56.5, -74.6, +64.9). El driver mide
        # el offset al conectar y lo resta. Si esta comprobacion falla, esa
        # correccion se ha perdido — y con ella la coherencia entre la posicion
        # y la orientacion de /odom, que no da NINGUN error.
        #
        # ⚠️ Solo vale con el robot QUIETO y recien arrancado el driver.
        if timeout 6 ros2 topic list 2>/dev/null | grep -qx '/odom'; then
            YAW="$(timeout 10 ros2 topic echo /odom --once --field pose.pose.orientation 2>/dev/null \
                   | python3 -c 'import sys,math
d={}
for l in sys.stdin:
    if ":" in l:
        k,v=l.split(":",1)
        try: d[k.strip()]=float(v)
        except ValueError: pass
if all(k in d for k in "xyzw"):
    print(round(math.degrees(math.atan2(2*(d["w"]*d["z"]+d["x"]*d["y"]),
                                        1-2*(d["y"]**2+d["z"]**2))),1))' 2>/dev/null)"
            if [[ -n "$YAW" ]]; then
                if awk -v y="$YAW" 'BEGIN{exit !(y<5 && y>-5)}'; then
                    _ok "yaw de /odom en reposo: ${YAW}° (el offset se esta restando)"
                else
                    _avi "yaw de /odom en reposo: ${YAW}°, se esperaba ~0" \
                         "si el robot NO esta quieto es normal; si lo esta, se perdio la correccion de marcos (manual cap. 10)"
                fi
            fi
        fi

        # El keepalive publica /battery_state cada 30 s. Que ese topic tenga un
        # mensaje reciente es la prueba MAS BARATA de que el keepalive corre: sin
        # el, el RVR se duerme a los 300.6 s (medido) y el nodo no se entera.
        # Es TRANSIENT_LOCAL, asi que el ultimo valor llega al instante.
        if timeout 6 ros2 topic list 2>/dev/null | grep -qx '/battery_state'; then
            BAT="$(timeout 10 ros2 topic echo /battery_state --once 2>/dev/null \
                   | grep -m1 -oE 'percentage: [0-9.]+' | grep -oE '[0-9.]+')"
            if [[ -n "$BAT" ]]; then
                PCT="$(awk -v b="$BAT" 'BEGIN{printf "%.0f", b*100}')"
                _ok "keepalive vivo · bateria ${PCT} % (/battery_state)"
                awk -v b="$BAT" 'BEGIN{exit !(b < 0.25)}' \
                    && _avi "bateria por debajo del 25 %" "ponlo a cargar antes de una practica"
            else
                _avi "/battery_state existe pero no llega valor" \
                     "el keepalive puede estar desactivado (keepalive_period=0): manual 9.8b"
            fi
        fi
    fi

    # El driver del LIDAR y su SDK se compilan desde fuentes: no hay paquete apt.
    [[ -f /usr/local/lib/libydlidar_sdk.a ]] \
        && _ok "YDLidar-SDK instalado en /usr/local" \
        || _avi "falta YDLidar-SDK (no hay paquete apt: se compila)" "ver manual, cap. 8.5a"
    if [[ -d "$HOME/atriz_ws/install/ydlidar_ros2_driver" ]]; then
        _ok "ydlidar_ros2_driver compilado en el workspace"
    else
        _avi "falta ydlidar_ros2_driver: no habra /scan" "ver manual, cap. 8.5b"
    fi
    # /dev/ydlidar: nombre estable por regla udev. Sin el, /dev/ttyUSB0 no es
    # determinista con dos dispositivos USB-serie.
    if [[ -L /dev/ydlidar ]]; then
        _ok "/dev/ydlidar -> $(readlink /dev/ydlidar)"
    else
        _avi "/dev/ydlidar no existe (el driver lo espera)" \
             "sudo cp .../atriz_rvr_bringup/udev/99-ydlidar.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules"
    fi

    # xacro NO viene en ros-base y hace falta para el URDF.
    dpkg -l ros-jazzy-xacro 2>/dev/null | grep -q '^ii' \
        && _ok "ros-jazzy-xacro instalado (no viene en ros-base)" \
        || _avi "falta ros-jazzy-xacro: no se podra procesar el URDF" \
                "sudo apt install -y ros-jazzy-xacro"

    # Si existen los dos, .bashrc gana (se lee despues) y deja el dominio fijo a 1
    # en un robot que deberia ser otro. Fallo silencioso: dos robots, un dominio.
    # 🔴 Anclado a un `export` REAL, no a que la cadena aparezca. La primera
    #    versión hacía `grep -q 'ROS_DOMAIN_ID'` y **contaba el comentario que
    #    explica por qué ya no está** como si fuera el ajuste: fallaba justo
    #    después de arreglar el problema. Es el mismo error que ya se cometió
    #    contando un comentario como un ajuste de `robot_radius`.
    if [[ -f /etc/profile.d/atriz-robot.sh ]] \
       && grep -qE '^[[:space:]]*export[[:space:]]+ROS_DOMAIN_ID=' "$HOME/.bashrc" 2>/dev/null; then
        _mal "ROS_DOMAIN_ID está definido en ~/.bashrc Y en /etc/profile.d/atriz-robot.sh" \
             "el .bashrc gana y pisa la identidad del robot: quítalo del .bashrc"
    fi
else
    _nota "ROS 2 aún no instalado — es la Etapa E1 (manual, cap. 5.2)."
fi

# El QoS de slam_toolbox ya se comprobó (2026-07-30): se suscribe BEST_EFFORT,
# igual que publica el LIDAR. Emparejan, el riesgo era infundado.
if command -v ros2 >/dev/null && [[ -n "${ROS_DISTRO:-}" ]]; then
    # slam_toolbox es un nodo de CICLO DE VIDA en Jazzy: arranca en
    # `unconfigured`, vivo y sin hacer nada. Que exista no prueba nada.
    if timeout 6 ros2 node list 2>/dev/null | grep -q 'slam_toolbox'; then
        ESTADO="$(timeout 8 ros2 lifecycle get /slam_toolbox 2>/dev/null | head -1)"
        case "$ESTADO" in
            active*) _ok "slam_toolbox en '$ESTADO'" ;;
            "")      _avi "slam_toolbox existe pero no responde a lifecycle get" "" ;;
            *)       _mal "slam_toolbox en '$ESTADO': vivo pero NO mapea" \
                          "arranca con slam.launch.py (autostart), o: ros2 lifecycle set /slam_toolbox configure && ... activate" ;;
        esac
    fi

    # ── La capa de seguridad (manual, cap. 12) ───────────────────────────────
    # También es nodo de ciclo de vida, y aquí un `unconfigured` es PEOR que en
    # slam_toolbox: el robot parecería protegido y no lo estaría.
    if timeout 6 ros2 node list 2>/dev/null | grep -q 'collision_monitor'; then
        ESTADO="$(timeout 8 ros2 lifecycle get /collision_monitor 2>/dev/null | head -1)"
        case "$ESTADO" in
            active*) _ok "collision_monitor en '$ESTADO'" ;;
            "")      _avi "collision_monitor existe pero no responde a lifecycle get" "" ;;
            *)       _mal "collision_monitor en '$ESTADO': vivo pero NO FILTRA NADA" \
                          "arranca el robot con robot.launch.py (autostart)" ;;
        esac

        # 🔴 LA comprobación de la capa de seguridad: contar publicadores.
        # Si el behavior_server de Nav2 no está remapeado salen SEIS, y sus cinco
        # conductas de recuperación conducen el robot saltándose el monitor.
        # Nada da error: hay que mirar el número (manual, cap. 12.2).
        N_PUB="$(timeout 8 ros2 topic info /cmd_vel --verbose 2>/dev/null \
                 | awk '/Publisher count:/{print $3; exit}')"
        if [[ -z "$N_PUB" ]]; then
            _avi "no se pudo contar los publicadores de /cmd_vel" ""
        elif [[ "$N_PUB" == "1" ]]; then
            _ok "/cmd_vel tiene UN publicador (es el collision_monitor)"
        else
            _mal "/cmd_vel tiene $N_PUB publicadores: algo conduce SALTÁNDOSE la seguridad" \
                 "mira quién con: ros2 topic info /cmd_vel --verbose. Si es behavior_server, falta su remapeo a cmd_vel_raw"
        fi
    fi
fi

_nota "PENDIENTE de añadir aquí cuando exista: unidades systemd del stack,"
_nota "rosbridge en :9090, y el keepalive del driver (manual cap. 9.8)."

# ─────────────────────────────────────────────────────────────────────────────
if [[ $HARDWARE -eq 1 ]]; then
    # 📝 «9-H», no «9»: había DOS secciones numeradas 9 (esta y la de Nav2, más
    #    abajo). Se le pone sufijo en vez de renumerar de la 9 a la 12, porque
    #    esos números están citados en el manual y en el RUNBOOK.
    sec "9-H · Hablar con el hardware de verdad (solo con --hardware)"
    # _nota, no _avi: es información, no un problema del robot. Con _avi el
    # script salía SIEMPRE con código 2 al usar --hardware, y eso convierte el
    # código de salida en inútil para automatizar "¿pasó este robot?".
    _nota "esto DESPIERTA el robot: enciende sus LEDs y gasta batería"
    AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    MED="$AQUI/00_auditoria/evidencia/mediciones_banco"

    if [[ -e /dev/rvr && -f "$MED/raw_uart.py" ]]; then
        if python3 "$MED/raw_uart.py" 2>&1 | grep -q 'RVR CONTESTA'; then
            _ok "el RVR contesta por /dev/rvr"
        else
            _mal "el RVR NO contesta" \
                 "APAGA Y ENCIENDE EL ROBOT y repite: un RVR dormido da el mismo síntoma que un cable roto"
        fi
    else
        _avi "no se puede probar el RVR (falta /dev/rvr o raw_uart.py)"
    fi

    # 🔴 SI EL DRIVER ESTÁ CORRIENDO, EL PUERTO ESTÁ OCUPADO. `x2_parse.py` abre
    #    /dev/ttyUSB0 en crudo, así que con `ydlidar_ros2_driver` vivo devolvía
    #    «no entrega datos válidos» — un FALLO FALSO que aparecía justo cuando el
    #    robot estaba funcionando bien. Es lo peor que puede hacer un verificador:
    #    quien lo vea dos veces deja de creérselo.
    #
    #    Con el driver vivo se comprueba EL EFECTO, que es `/scan` circulando —y
    #    es una prueba mejor, porque cubre además el driver ROS y el QoS.
    if ps -eo comm 2>/dev/null | grep -q '^ydlidar_ros2_dr$'; then
        N_SCAN="$(timeout 25 python3 - <<'PYEOF' 2>/dev/null || echo 0
import time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
# BEST_EFFORT: el driver del X2 publica así y el perfil por defecto de rclpy es
# RELIABLE, que NO empareja y no recibiría nada (CLAUDE.md).
q = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
               history=HistoryPolicy.KEEP_LAST, depth=5)
rclpy.init(); n = Node('verif_scan'); c = []
n.create_subscription(LaserScan, 'scan', lambda m: c.append(1), q)
t = time.time()
while time.time() - t < 8:
    rclpy.spin_once(n, timeout_sec=0.1)
print(len(c)); n.destroy_node(); rclpy.shutdown()
PYEOF
)"
        if [[ "${N_SCAN:-0}" -ge 40 ]]; then
            _ok "LIDAR X2 vía /scan: $N_SCAN barridos en 8 s (~$((N_SCAN/8)) Hz)"
        elif [[ -x /usr/local/bin/atriz-escaneo ]]; then
            # 🔴 CERO BARRIDOS NO ES UN FALLO DESDE EL 2026-07-31. El robot arranca
            #    con el barrido PARADO a propósito (manual, cap. 17), así que este
            #    es su estado NORMAL en reposo. Dar «✗ el LIDAR no publica» sobre
            #    un robot recién arrancado y sano es exactamente el falso positivo
            #    que este fichero lleva seis veces cometiendo.
            #
            #    Con --hardware sí se puede comprobar de verdad: se enciende, se
            #    mide, y SE DEJA COMO ESTABA. Comprobar el efecto, no la intención.
            _nota "/scan a 0: el barrido está parado (es lo normal en reposo). Encendiéndolo para medir…"
            atriz-escaneo on >/dev/null 2>&1
            sleep 2
            N_SCAN2="$(timeout 25 python3 - <<'PYEOF' 2>/dev/null || echo 0
import time, rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
q = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
               history=HistoryPolicy.KEEP_LAST, depth=10)
rclpy.init(); n = Node('verif_scan2'); c = []
n.create_subscription(LaserScan, 'scan', lambda m: c.append(1), q)
ex = SingleThreadedExecutor(); ex.add_node(n)
t = time.time()
while time.time() - t < 8:
    ex.spin_once(timeout_sec=0.1)
print(len(c)); n.destroy_node(); rclpy.shutdown()
PYEOF
)"
            # Se restaura el estado de partida: quien pasa el verificador no
            # espera que le deje el lidar girando a tope.
            atriz-escaneo off >/dev/null 2>&1
            if [[ "${N_SCAN2:-0}" -ge 40 ]]; then
                _ok "LIDAR X2: $N_SCAN2 barridos en 8 s tras 'atriz-escaneo on' (y devuelto a off)"
            else
                _mal "ni con el barrido encendido llega /scan ($N_SCAN2 barridos en 8 s)" \
                     "esperados ~80. Mira el log: journalctl -u atriz-robot -n 50"
            fi
        else
            _mal "el driver del LIDAR corre pero /scan da $N_SCAN barridos en 8 s" \
                 "esperados ~80. Mira el log del ydlidar_ros2_driver"
        fi
    elif [[ -c /dev/ttyUSB0 && -f "$MED/x2_parse.py" ]]; then
        SAL="$(python3 "$MED/x2_parse.py" 2>&1)"
        if grep -q 'X2 FUNCIONA' <<<"$SAL"; then
            _ok "LIDAR X2: $(grep -oE '[0-9.]+% validos' <<<"$SAL" | head -1) checksums, $(grep -oE 'frecuencia de giro *: [0-9.]+ Hz' <<<"$SAL" | grep -oE '[0-9.]+ Hz')"
        else
            _mal "el LIDAR X2 no entrega datos válidos" "revisa el adaptador USB: el X2 alimenta su motor por DTR"
        fi
    else
        _avi "no se puede probar el LIDAR (falta /dev/ttyUSB0 o x2_parse.py)"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
sec "9 · Nav2, seguridad, localización y servicios"

# Todo lo de la Fase 4b en adelante. Existe porque la imagen dorada replica lo
# que HAY en este robot: si algo de esto falta aquí, faltará en los 16.

# ── Nav2 y sus binarios ──────────────────────────────────────────────────────
# `navigation2` trae mucho más que navegar: la capa de seguridad
# (collision_monitor), la localización (map_server + amcl) y map_saver_cli, que
# es la única forma fiable de guardar mapas (manual, cap. 11.11).
for BIN in collision_monitor map_server amcl controller_server planner_server; do
    if compgen -G "/opt/ros/jazzy/lib/*/$BIN" >/dev/null; then
        _ok "nav2: $BIN"
    else
        _mal "nav2: FALTA $BIN" "sudo apt install -y ros-jazzy-navigation2  (NO nav2-bringup)"
    fi
done
# 🔴 Y que NO esté el simulador: nav2-bringup arrastra 312 paquetes de TurtleBot
# simulado, y en la imagen dorada se replicarían por 16.
SIM="$(dpkg -l 2>/dev/null | grep -cE 'nav2-minimal-tb|ros-gz-sim|pocketsphinx' || true)"
[[ "$SIM" -eq 0 ]] && _ok "sin paquetes de simulador (0)" \
    || _avi "hay $SIM paquetes de simulador instalados" "¿se instaló nav2-bringup por error?"

# ── Los ficheros que definen el comportamiento ───────────────────────────────
CFG="$WS/atriz_rvr_bringup/config"
LAU="$WS/atriz_rvr_bringup/launch"
for F in "$CFG/nav2_atriz.yaml" "$CFG/collision_monitor.yaml" \
         "$CFG/localizacion_amcl.yaml" "$CFG/slam_toolbox_atriz.yaml" \
         "$CFG/ydlidar_x2.yaml" "$LAU/robot.launch.py" "$LAU/slam.launch.py" \
         "$LAU/nav2.launch.py" "$LAU/localizacion.launch.py"; do
    [[ -f "$F" ]] && _ok "existe $(basename "$F")" \
        || _mal "FALTA $(basename "$F")" "git -C $WS pull"
done

# ── Los VALORES medidos, no solo que el fichero exista ───────────────────────
# La regla del fichero: comprobar el efecto. Un YAML presente con los valores del
# ejemplo de Nav2 es peor que no tenerlo, porque parece configurado.
if [[ -f "$CFG/nav2_atriz.yaml" ]]; then
    # 0.145 = radio circunscrito medido (√(0.091² + 0.1085²)). Estuvo en 0.11,
    # que no era ni el inscrito ni el circunscrito (manual, cap. 12.10).
    # 🔴 Anclado al principio de línea y sin '#': la primera versión hacía
    #    `grep -c 'robot_radius: 0.145'` y contaba 3 —los dos ajustes MÁS un
    #    comentario que menciona el valor—, así que fallaba con la configuración
    #    correcta. Un verificador con falsos positivos se acaba ignorando, que es
    #    peor que no tenerlo.
    N_RR="$(grep -cE '^[[:space:]]+robot_radius: 0\.145[[:space:]]*$' "$CFG/nav2_atriz.yaml")"
    [[ "$N_RR" -eq 2 ]] \
        && _ok "robot_radius 0.145 en los dos costmaps" \
        || _mal "robot_radius 0.145 aparece $N_RR veces, se esperaban 2" "manual, cap. 12.10"
    grep -q 'desired_linear_vel: 0.40' "$CFG/nav2_atriz.yaml" \
        && _ok "desired_linear_vel 0.40 (el máximo medido)" \
        || _avi "desired_linear_vel no es 0.40" "manual, cap. 11.10"
fi
if [[ -f "$CFG/collision_monitor.yaml" ]]; then
    grep -q 'radius: 0.18' "$CFG/collision_monitor.yaml" \
        && _ok "collision_monitor: radius 0.18 (para a ~10 cm)" \
        || _avi "el radius del collision_monitor no es 0.18" "manual, cap. 12.4"
fi
URDF="$WS/atriz_rvr_description/urdf/rvr.urdf.xacro"
if [[ -f "$URDF" ]]; then
    # 🔴 Estas tres estuvieron MAL hasta el 2026-07-31: largo y ancho CRUZADOS y
    # el alto de la ficha, que hacía que laser_z estuviera 2 cm arriba.
    # 🔴 0.190 desde el 2026-08-02, no 0.182. El usuario volvio a medir con cinta
    #    (19.0 cm de frente a atras con orugas) al cerrar `laser_x`, y el URDF se
    #    actualizo — pero ESTA comprobacion se quedo con el valor viejo y empezo a
    #    dar FALLO sobre un modelo CORRECTO. Lo cazo la prueba de aceptacion.
    #    📝 Van dos veces que este verificador falla justo despues de arreglar lo
    #       que comprueba. Si cambias una cota del URDF, cambia esta linea.
    #    ⚠️ El conflicto 18.2 vs 19.0 sigue ABIERTO: dos medidas con cinta que
    #       difieren 0.8 cm. Ver MEDIDAS_ROBOT.md.
    grep -q 'base_length" value="0.190' "$URDF" && grep -q 'base_width"  value="0.217' "$URDF" \
        && _ok "URDF: 0.190 × 0.217 m (medido 2026-08-02, no la ficha)" \
        || _mal "el URDF no tiene las cotas MEDIDAS" "manual, cap. 12.10 y MEDIDAS_ROBOT.md"
    grep -q 'laser_z"   value="0.155' "$URDF" \
        && _ok "URDF: laser_z 0.155 m (medido con regla)" \
        || _mal "laser_z no es 0.155" "estaba DERIVADO y salía 2 cm alto; cap. 12.8"
fi

# ── Los valores por defecto del driver, que son decisiones ───────────────────
DRV="$WS/atriz_rvr_driver/scripts/atriz_rvr_driver/rvr_driver_node.py"
if [[ -f "$DRV" ]]; then
    grep -q "declare_parameter('publicar_inclinacion', False)" "$DRV" \
        && _ok "publicar_inclinacion False: /odom sale plano" \
        || _avi "publicar_inclinacion no es False por defecto" "la inclinación del RVR es un artefacto del acelerómetro; cap. 13"
    grep -q "declare_parameter('color_detection', False)" "$DRV" \
        && _ok "color_detection False: no deja el LED encendido" \
        || _avi "color_detection no es False por defecto" "cap. 16.2"
    grep -q "'/rvr/emergency_stop'" "$DRV" \
        && _ok "parada de emergencia: escucha también /rvr/emergency_stop" \
        || _mal "el driver NO escucha /rvr/emergency_stop" "es el topic que usa la web; cap. 15"
    grep -q 'durability=QoSDurabilityPolicy.VOLATILE' "$DRV" \
        && _ok "parada de emergencia: QoS VOLATILE (empareja con todo)" \
        || _mal "la parada usa TRANSIENT_LOCAL: no emparejará con rosbridge" "cap. 15.1"
fi

# ── Con hardware: los servicios, preguntando a un CLIENTE ────────────────────
if [[ $HARDWARE -eq 1 ]] && command -v ros2 >/dev/null && [[ -n "${ROS_DISTRO:-}" ]]; then
    if timeout 6 ros2 node list 2>/dev/null | grep -q 'rvr_driver'; then
        # 🔴 CON UN CLIENTE, NO CON `ros2 service list`. La lista MIENTE POR
        # OMISIÓN: el 2026-07-31 se dejó fuera `set_drive_parameters` (17 de 18)
        # mientras un cliente lo encontraba sin problema (manual, cap. 16.5).
        FALTAN="$(timeout 60 python3 - <<'PYEOF' 2>/dev/null
import rclpy
from rclpy.node import Node
from atriz_rvr_msgs import srv as S
from std_srvs.srv import Empty
PARES = [
    (S.GetEncoders, 'get_encoders'), (S.GetSystemInfo, 'get_system_info'),
    (S.GetControlState, 'get_control_state'),
    (S.GetRGBCSensorValues, 'get_rgbc_sensor_values'),
    (S.SetLEDRGB, 'set_led_rgb'), (S.SetMultipleLEDs, 'set_multiple_leds'),
    (S.SetLeds, 'set_leds'), (S.TriggerLedEvent, 'trigger_led_event'),
    (S.SendInfraredMessage, 'send_infrared_message'), (S.SetIRMode, 'set_ir_mode'),
    (S.SetIREvading, 'set_ir_evading'),
    (S.SetDriveParameters, 'set_drive_parameters'),
    (S.SetPosAndYaw, 'set_pos_and_yaw'), (S.MoveTimed, 'move_timed'),
    (S.RawMotors, 'raw_motors'), (S.MoveToPose, 'move_to_pose'),
    (S.MoveToPosAndYaw, 'move_to_pos_and_yaw'),
    (Empty, 'release_emergency_stop'),
]
rclpy.init(); n = Node('verif_srv')
faltan = [nom for tipo, nom in PARES
          if not n.create_client(tipo, nom).wait_for_service(timeout_sec=2.0)]
print(','.join(faltan))
n.destroy_node(); rclpy.shutdown()
PYEOF
)"
        if [[ -z "$FALTAN" ]]; then
            _ok "los 18 servicios del driver responden"
        else
            _mal "servicios que NO responden: $FALTAN" "manual, cap. 16"
        fi
    fi
fi

sec "10 · Telemetría añadida el 2026-08-01"

# La regla del proyecto: lo de cada día acaba aquí, o la imagen dorada no lo
# tendrá. Se comprueba el EFECTO —que los topics PUBLIQUEN— no que existan: un
# topic registrado y mudo es el síntoma estrella de este proyecto.
if ps -eo comm 2>/dev/null | grep -qx 'rvr_driver_node'; then
    RES="$(timeout 30 python3 - <<'PYEOF' 2>/dev/null || echo "0 0 0"
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from atriz_rvr_msgs.msg import Encoder
from sensor_msgs.msg import Illuminance
q = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
               history=HistoryPolicy.KEEP_LAST, depth=50)
rclpy.init()
n = Node("verif_tel_nueva"); c = {"enc": 0, "luz": 0}
n.create_subscription(Encoder, "encoders", lambda m: c.__setitem__("enc", c["enc"] + 1), q)
n.create_subscription(Illuminance, "ambient_light", lambda m: c.__setitem__("luz", c["luz"] + 1), q)

ex = SingleThreadedExecutor(); ex.add_node(n)
t0 = time.monotonic()
while time.monotonic() - t0 < 8.0:
    ex.spin_once(timeout_sec=0.1)
print(c["enc"], c["luz"])
PYEOF
)"
    N_ENC=$(awk '{print $1}' <<<"$RES"); N_LUZ=$(awk '{print $2}' <<<"$RES")
    [[ "${N_ENC:-0}" -ge 80 ]] \
        && _ok "/encoders: $N_ENC msgs en 8 s (~$((N_ENC/8)) Hz)" \
        || _mal "/encoders solo $N_ENC msgs en 8 s (esperados ~130)" \
                "las claves del stream son LeftTicks/RightTicks, no Left/Right"
    [[ "${N_LUZ:-0}" -ge 60 ]] \
        && _ok "/ambient_light: $N_LUZ msgs en 8 s" \
        || _mal "/ambient_light solo $N_LUZ msgs en 8 s (esperados ~105)" \
                "manual, cap. 18.4b"
    # 🔴 `/motor_status` VA EN SU PROPIO PROCESO, y no es un capricho: llega cada
    #    30 s y lo que se recibe es el ÚNICO mensaje retenido (TRANSIENT_LOCAL).
    #    Compartiendo nodo con `/encoders` y `/ambient_light` —~30 Hz entre los
    #    dos— ese mensaje único se quedaba esperando turno en el ejecutor y la
    #    comprobación fallaba UNA DE CADA DOS VECES sobre un robot sano.
    #    Un verificador intermitente se acaba ignorando (ver evidencia 32).
    N_MOT="$(timeout 25 python3 - <<'PYEOF' 2>/dev/null || echo 0
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from atriz_rvr_msgs.msg import MotorStatus
rclpy.init()
n = Node("verif_motor_status"); c = [0]
n.create_subscription(MotorStatus, "motor_status", lambda m: c.__setitem__(0, c[0] + 1),
                      QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                                 durability=DurabilityPolicy.VOLATILE,
                                 history=HistoryPolicy.KEEP_LAST, depth=1))
ex = SingleThreadedExecutor(); ex.add_node(n)
t0 = time.monotonic()
while time.monotonic() - t0 < 10.0 and c[0] == 0:
    ex.spin_once(timeout_sec=0.1)
print(c[0])
PYEOF
)"
    [[ "${N_MOT:-0}" -ge 1 ]] \
        && _ok "/motor_status: llega el último estado (TRANSIENT_LOCAL)" \
        || _mal "/motor_status no publica nada" \
                "es TRANSIENT_LOCAL: un suscriptor nuevo debe recibir el último. Manual cap. 18.1"
else
    _nota "rvr_driver_node no corre: no se comprueban /encoders, /ambient_light ni /motor_status."
fi

# 📝 `/ambient_light` NO se comprueba por su VALOR a propósito: en este montaje el
#    piso blanco del LIDAR le refleja los LEDs del robot, así que el número
#    depende de qué LEDs estén encendidos. Se decidió no usarlo (manual 18.4b).

sec "11 · Arranque automático y parada de emergencia con Nav2"

# Lo del 2026-07-31. Aquí casi todo son AVISOS y no fallos a propósito: el
# arranque automático se instala aparte (fase_7_systemd.sh) y la decisión del
# usuario es añadirlo a provision.sh cuando se cierre el robot de referencia.
# Un robot sin systemd NO está roto — todavía.

INST="$HOME/atriz_ws/install"

# ── El cancelador de Nav2: se comprueba lo INSTALADO, no el fuente ───────────
# 🔴 `colcon build` desde el directorio equivocado dice «Finished» y no instala
#    nada (CLAUDE.md). Mirar el fuente daría un falso OK.
if [[ -x "$INST/atriz_rvr_driver/lib/atriz_rvr_driver/cancelar_nav2" ]]; then
    _ok "cancelar_nav2 instalado (la parada corta los objetivos de Nav2)"
else
    _mal "cancelar_nav2 NO instalado" \
         "cd ~/atriz_ws && colcon build --packages-select atriz_rvr_driver · manual cap. 15.4"
fi
NAV2_INST="$INST/atriz_rvr_bringup/share/atriz_rvr_bringup/launch/nav2.launch.py"
if [[ -f "$NAV2_INST" ]] && grep -q "cancelar_nav2" "$NAV2_INST"; then
    _ok "nav2.launch.py instalado arranca cancelar_nav2"
else
    _mal "el nav2.launch.py INSTALADO no arranca cancelar_nav2" \
         "sin él, liberar la parada de emergencia devuelve el robot a navegar"
fi

# ── De dónde saca systemd el ROS_DOMAIN_ID ──────────────────────────────────
# systemd no ejecuta un shell de login: no lee ~/.bashrc. Si el dominio solo
# vive ahí, el servicio arrancaría sin él —los 16 robots en el dominio 0— o se
# negaría a arrancar. En el robot de referencia esto es lo normal, todavía.
if [[ -f /etc/profile.d/atriz-robot.sh ]]; then
    DOM_P="$(sed -n 's/^export ROS_DOMAIN_ID=\([0-9]*\).*/\1/p' /etc/profile.d/atriz-robot.sh | head -1)"
    _ok "/etc/profile.d/atriz-robot.sh (ROS_DOMAIN_ID=${DOM_P:-?})"
    DOM_B="$(sed -n 's/^export ROS_DOMAIN_ID=\([0-9]*\).*/\1/p' "$HOME/.bashrc" 2>/dev/null | head -1)"
    if [[ -n "$DOM_B" && -n "$DOM_P" && "$DOM_B" != "$DOM_P" ]]; then
        # 🔴 El .bashrc se lee DESPUÉS y gana: shells y servicio en dominios
        #    distintos, sin un solo error por ningún lado.
        _mal "~/.bashrc dice ROS_DOMAIN_ID=$DOM_B y profile.d dice $DOM_P" \
             "el .bashrc gana: tus shells y el servicio no se verían"
    elif [[ -n "$DOM_B" ]]; then
        _avi "~/.bashrc también exporta ROS_DOMAIN_ID=$DOM_B" \
             "bórralo antes de la imagen dorada: dejaría los 16 clones en ese dominio"
    fi
else
    _avi "sin /etc/profile.d/atriz-robot.sh" \
         "systemd no lee ~/.bashrc: hace falta antes de fase_7_systemd.sh"
fi

# ── El servicio ──────────────────────────────────────────────────────────────
if [[ -f /etc/systemd/system/atriz-robot.service ]]; then
    _ok "atriz-robot.service instalado"
    if systemctl is-enabled atriz-robot.service >/dev/null 2>&1; then
        _ok "atriz-robot.service habilitado ($(systemctl is-enabled atriz-robot.service))"
    else
        _mal "atriz-robot.service NO habilitado" "sudo systemctl enable atriz-robot"
    fi
    # Comprobar el efecto: una unidad puede estar instalada y tener directivas
    # que systemd IGNORA en silencio. Pasó con StartLimitIntervalSec en
    # [Service] (manual, cap. 17.3).
    QUEJAS="$(systemd-analyze verify /etc/systemd/system/atriz-robot.service 2>&1 \
              | grep -v 'is not executable' | grep -c . || true)"
    [[ "$QUEJAS" -eq 0 ]] && _ok "systemd-analyze verify: sin quejas" \
        || _mal "systemd-analyze verify se queja ($QUEJAS línea(s))" \
                "systemd-analyze verify /etc/systemd/system/atriz-robot.service"
    [[ -x /usr/local/bin/atriz-robot.sh ]] && _ok "/usr/local/bin/atriz-robot.sh" \
        || _mal "falta /usr/local/bin/atriz-robot.sh" "el ExecStart apunta a un fichero que no existe"
    [[ -x /usr/local/bin/atriz-escaneo ]] && _ok "/usr/local/bin/atriz-escaneo" \
        || _mal "falta /usr/local/bin/atriz-escaneo" "el ExecStartPost del servicio lo llama"
else
    _avi "sin arranque automático (atriz-robot.service)" \
         "sudo bash ~/atriz_migracion/scripts/fase_7_systemd.sh --id NN · manual cap. 17"
fi


# ── 12. Red de la flota: mDNS, netplan y rosbridge ───────────────────────────
# Nada de esto existía hasta el 2026-08-01, y es lo que permite que la web
# encuentre a 16 robots sin saberse ninguna IP. Manual, cap. 19.
sec "12. Red de la flota — cómo la web encuentra a este robot"

# --- mDNS -------------------------------------------------------------------
# 🔴 `fase_1_higiene_so.sh` DESHABILITABA avahi como parte de la higiene, mientras
#    el manual decía «usa ping rvr-NN.local». Se corrigió; esto vigila que no
#    vuelva a pasar.
if systemctl is-active --quiet avahi-daemon 2>/dev/null; then
    _ok "avahi-daemon activo (responde a rvr-NN.local)"
else
    _mal "avahi-daemon NO está activo: nadie encontrará a este robot por nombre" \
         "sudo systemctl enable --now avahi-daemon"
fi
# El efecto, no la intención: se ancla a principio de línea y a la sintaxis
# exacta, porque un grep suelto encuentra también el COMENTARIO que habla del
# ajuste — error ya cometido dos veces en este verificador.
if grep -qE '^[[:space:]]*MulticastDNS[[:space:]]*=[[:space:]]*yes' \
        /etc/systemd/resolved.conf /etc/systemd/resolved.conf.d/*.conf 2>/dev/null; then
    _ok "MulticastDNS=yes en systemd-resolved"
else
    _avi "systemd-resolved sin MulticastDNS=yes" \
         "este robot no resolverá el .local de OTROS robots"
fi
# ⚠️ Global: yes con wlan0: no es el estado real medido el 2026-08-01. Avahi
#    responde igual, así que es aviso y no fallo.
if command -v resolvectl >/dev/null 2>&1; then
    if resolvectl mdns 2>/dev/null | grep -qiE 'wlan0.*yes|yes.*wlan0'; then
        _ok "mDNS habilitado también en el enlace wlan0"
    else
        _avi "mDNS por enlace: wlan0 no lo tiene (Global sí)" \
             "pendiente: drop-in de systemd-networkd. Manual, cap. 19.5"
    fi
fi

# --- Dominio regulatorio del WiFi: el parámetro llega y NO surte efecto -------
# 🔴 cmdline.txt pide cfg80211.ieee80211_regdom=CO y el módulo lo recibe —
#    /sys/module/cfg80211/parameters/ieee80211_regdom dice CO— pero el firmware
#    del brcmfmac es *self-managed* y lo pisa. Medido en rvr-01 el 2026-08-03:
#      /sys/…/ieee80211_regdom  ->  CO
#      iw reg get               ->  global country US · phy#0 country 99
#    Se comprueba el EFECTO (iw), no el parámetro, porque el parámetro miente.
#    Aviso y no fallo: la banda que usa el laboratorio (2.4 GHz) está permitida
#    en los dos dominios, así que hoy no rompe nada. Queda escrito para que
#    nadie vuelva a leer el cmdline.txt y dé por hecho que está aplicado.
if command -v iw >/dev/null 2>&1 && grep -q 'ieee80211_regdom' /boot/firmware/cmdline.txt 2>/dev/null; then
    REG_PEDIDO="$(grep -o 'ieee80211_regdom=[A-Z][A-Z]' /boot/firmware/cmdline.txt | cut -d= -f2)"
    REG_REAL="$(iw reg get 2>/dev/null | sed -n 's/^country \([A-Z0-9]*\):.*/\1/p' | head -1)"
    if [[ "$REG_PEDIDO" == "$REG_REAL" ]]; then
        _ok "dominio regulatorio WiFi: pedido $REG_PEDIDO, efectivo $REG_REAL"
    else
        _avi "regdom: cmdline.txt pide $REG_PEDIDO y el efectivo es ${REG_REAL:-desconocido}" \
             "el firmware brcmfmac es self-managed y lo ignora — no es un fallo, pero el cmdline miente"
    fi
fi

# --- La identidad y el perfil de red, en la partición FAT --------------------
# 🔴 Viven en la FAT a propósito: una IP estática mal puesta deja al robot sin
#    dirección en esa LAN, y la FAT se corrige metiendo la microSD en un PC.
if [[ -f /boot/firmware/robot_id.txt ]]; then
    RID="$(grep -oP '^\s*ROBOT_ID\s*=\s*\K[0-9]+' /boot/firmware/robot_id.txt 2>/dev/null | head -1 || true)"
    if [[ -n "$RID" ]]; then
        _ok "robot_id.txt → ROBOT_ID=$RID"
        # Que la identidad declarada y la real coincidan. Si no, este robot
        # responde a un nombre y cree ser otro.
        ESP="rvr-$(printf '%02d' "$((10#$RID))")"
        [[ "$(hostname)" == "$ESP" ]] && _ok "hostname coincide con robot_id ($ESP)" \
            || _mal "hostname '$(hostname)' no coincide con robot_id ($ESP)" \
                    "sudo bash first-boot.sh   (regenera identidad)"

        # 🔴 Y EL DOMINIO DDS, que es el que falla EN SILENCIO.
        #    El hostname equivocado se ve enseguida: no puedes entrar por ssh.
        #    Un ROS_DOMAIN_ID equivocado no da ni un error — solo robots que no
        #    se ven, o que se ven de más. Y el 2026-08-03 se midió que dos de
        #    los cuatro parsers de robot_id.txt leían los dos primeros dígitos
        #    del fichero (comentarios incluidos), así que con la plantilla de
        #    fase_6 los 16 robots habrían salido en el dominio 1.
        #    Los parsers están arreglados; esta aserción es la red que lo habría
        #    cazado, y la que lo cazará la próxima vez.
        DOM_P="$(sed -n 's/^export ROS_DOMAIN_ID=\([0-9]*\).*/\1/p' \
                 /etc/profile.d/atriz-robot.sh 2>/dev/null | head -1)"
        if [[ -z "$DOM_P" ]]; then
            _nota "no hay ROS_DOMAIN_ID en /etc/profile.d/atriz-robot.sh (aún sin identidad)"
        elif [[ "$((10#$DOM_P))" -eq "$((10#$RID))" ]]; then
            _ok "ROS_DOMAIN_ID=$DOM_P coincide con robot_id.txt"
        else
            _mal "ROS_DOMAIN_ID=$DOM_P y robot_id.txt dice $RID: este robot está en el dominio equivocado" \
                 "sudo rm /var/lib/atriz-first-boot.done && sudo bash first-boot.sh"
        fi
    else
        _mal "robot_id.txt existe pero no tiene ROBOT_ID=NN" \
             "echo ROBOT_ID=01 | sudo tee /boot/firmware/robot_id.txt"
    fi
else
    _avi "no hay /boot/firmware/robot_id.txt" \
         "sin él, first-boot no puede personalizar un clon de la imagen dorada"
fi

if [[ -f /boot/firmware/red.txt ]]; then
    _ok "existe /boot/firmware/red.txt (perfil de red)"
    # 🔴 red.txt LLEVA LA PSK DEL WIFI Y ESTÁ EN UNA FAT, QUE NO GUARDA
    #    PERMISOS DE UNIX. `chmod 600` sobre él **no hace nada** y devuelve 0,
    #    que es lo peor: parece que funcionó. Los permisos los fija el MONTAJE
    #    (`fmask`), y con `defaults` salen 755 = legible por cualquier usuario.
    #    Se comprueba el montaje, que es lo único que puede cambiarlo.
    PERM="$(stat -c '%a' /boot/firmware/red.txt 2>/dev/null || echo '?')"
    if [[ "$PERM" == "600" ]]; then
        _ok "red.txt con permisos 600"
    else
        _avi "red.txt en $PERM: la PSK del WiFi es legible por cualquier usuario" \
             "chmod NO sirve (es FAT). Añade fmask=0177,dmask=0077 en /etc/fstab"
    fi
else
    _avi "no hay /boot/firmware/red.txt: la red se queda en DHCP" \
         "cp scripts/red.txt.ejemplo, rellénalo, y first-boot.sh --solo-red"
fi

# --- El netplan generado ----------------------------------------------------
if [[ -f /etc/netplan/60-atriz.yaml ]]; then
    _ok "existe /etc/netplan/60-atriz.yaml"
    # 🔴 El corazón del diseño de la flota: estática Y DHCP a la vez. Si esto no
    #    está, el robot no se puede mudar de red sin reconfigurarlo.
    if sudo -n grep -q 'dhcp4: true' /etc/netplan/60-atriz.yaml 2>/dev/null \
       || grep -q 'dhcp4: true' /etc/netplan/60-atriz.yaml 2>/dev/null; then
        _ok "netplan: dhcp4 activo junto a las direcciones estáticas"
    else
        _avi "no se pudo leer 60-atriz.yaml (necesita root) o no tiene dhcp4" ""
    fi
else
    _avi "no hay /etc/netplan/60-atriz.yaml" \
         "sudo bash scripts/first-boot.sh --solo-red   (y luego netplan try)"
fi
# Todo netplan lleva la PSK en claro. En 20.04 venían 644.
MAL_PERM=0
for F in /etc/netplan/*.yaml; do
    [[ -e "$F" ]] || continue
    [[ "$(stat -c '%a' "$F")" == "600" ]] || MAL_PERM=$((MAL_PERM+1))
done
[[ $MAL_PERM -eq 0 ]] && _ok "todos los /etc/netplan/*.yaml con permisos 600" \
    || _mal "$MAL_PERM fichero(s) de netplan sin 600 (contienen la PSK)" \
            "sudo chmod 600 /etc/netplan/*.yaml"

# --- Las direcciones que realmente tiene la interfaz -------------------------
# El efecto, no la configuración: lo que cuenta es lo que `ip` dice AHORA.
N_IP="$(ip -4 -o addr show wlan0 2>/dev/null | wc -l || echo 0)"
if [[ "$N_IP" -ge 2 ]]; then
    _ok "wlan0 con $N_IP direcciones IPv4 (estática y DHCP conviven ✅)"
elif [[ "$N_IP" -eq 1 ]]; then
    _avi "wlan0 con 1 sola dirección IPv4: $(ip -4 -br addr show wlan0 | awk '{print $3}')" \
         "normal si aún no se aplicó el netplan de la flota"
else
    _mal "wlan0 sin dirección IPv4" "nadie puede llegar a este robot"
fi

# --- rosbridge: por donde habla la web --------------------------------------
if compgen -G "/opt/ros/jazzy/lib/rosbridge_server/rosbridge_websocket" >/dev/null 2>&1; then
    _ok "rosbridge_websocket instalado"
else
    _mal "FALTA rosbridge_websocket: la web no puede hablar con el robot" \
         "sudo apt install -y ros-jazzy-rosbridge-suite"
fi
# Escuchando de verdad, y en las DOS familias: mDNS puede resolver a IPv6
# link-local (pasó el 2026-08-01 desde Windows).
if ss -tln 2>/dev/null | grep -q ':9090'; then
    _ok "rosbridge escuchando en el puerto 9090"
    ss -tln 2>/dev/null | grep -q '\[::\]:9090' \
        && _ok "rosbridge también en IPv6 (mDNS puede resolver a link-local)" \
        || _avi "rosbridge solo en IPv4" "si mDNS resuelve a IPv6, la web no conectará"
else
    _avi "nada escuchando en el 9090" \
         "¿corre atriz-robot? el rosbridge va dentro de robot.launch.py"
fi

# --- El parche del YDLIDAR --------------------------------------------------
# 🔴 Sin él, el nodo emite 25 errores/s con el barrido apagado (el estado normal
#    en reposo): el 99 % del journal y 2.17 millones de mensajes al día por
#    robot. Se comprueba el FUENTE, porque el binario no lo dice.
# 📝 $WS apunta a .../src/Atriz_rvr; el ydlidar es HERMANO, no hijo.
YSRC="$(dirname "$WS")/ydlidar_ros2_driver/src/ydlidar_ros2_driver_node.cpp"
if [[ -f "$YSRC" ]]; then
    grep -q "PARCHE ATRIZ" "$YSRC" \
        && _ok "ydlidar parcheado (no inunda el journal con el barrido apagado)" \
        || _mal "ydlidar SIN parchear: emitirá 25 errores/s con el barrido apagado" \
                "bash scripts/provision.sh   (aplica el parche y recompila)"
fi
# Y el efecto de verdad: que el journal no se esté llenando AHORA.
RUIDO="$(journalctl -u atriz-robot --since '-2 min' --no-pager 2>/dev/null \
         | grep -c 'Failed to get scan' || true)"
[[ "${RUIDO:-0}" -lt 20 ]] && _ok "journal limpio ($RUIDO 'Failed to get scan' en 2 min)" \
    || _mal "el journal se está inundando: $RUIDO errores en 2 min" \
            "¿se recompiló el ydlidar tras parchearlo?"

# --- La lista blanca de rosbridge ---------------------------------------------
# 🔴 `SEGURIDAD_ROSBRIDGE.md` prometia esta comprobacion «en tres sitios: una
#    herramienta de banco, verificar_robot.sh, y F8». Estaban dos de tres: AQUI
#    faltaba, y lo encontro una auditoria con subagentes.
#    Lo que habia comprobado era que el 9090 ESCUCHA — que es exactamente la
#    trampa «el puerto esta abierto ≠ funciona» que este proyecto tiene
#    documentada media docena de veces.
LAUNCH_ROBOT="$WS/atriz_rvr_bringup/launch/robot.launch.py"
if [[ -f "$LAUNCH_ROBOT" ]]; then
    if grep -q "topics_pub_glob" "$LAUNCH_ROBOT" && grep -q "services_glob" "$LAUNCH_ROBOT"; then
        _ok "rosbridge: la lista blanca esta en el launch"
    else
        _mal "rosbridge SIN lista blanca: raw_motors alcanzable desde la red" \
             "ver 03_operacion/SEGURIDAD_ROSBRIDGE.md, Fase A"
    fi
    grep -q "params_glob" "$LAUNCH_ROBOT" \
        && _ok "rosbridge: params_glob puesto (la web no toca parametros)" \
        || _avi "rosbridge sin params_glob" "ver SEGURIDAD_ROSBRIDGE.md"
    grep -q "rosapi" "$LAUNCH_ROBOT" \
        && _ok "rosapi_node se levanta (getTopics no se colgara)" \
        || _avi "rosapi_node NO se levanta: ros.getTopics() de roslibjs se cuelga SIN error" \
                "ver ARQUITECTURA.md, trampas de rosbridge"
    # 📝 Y esto NO prueba que deniegue: eso solo se sabe llamando. Para el efecto
    #    real esta `mediciones_banco/probar_lista_blanca.py`, que ademas exige un
    #    CONTROL para no confundir «denegado» con «aqui no funciona nada».
    _nota "para comprobar que DENIEGA de verdad: python3 00_auditoria/evidencia/mediciones_banco/probar_lista_blanca.py"
fi

# --- Regresión: rutas fijas en /tmp -----------------------------------------
# 🔴 `fs.protected_regular=2` impide a ROOT escribir en un fichero de /tmp que no
#    le pertenece. Si la redirección falla, bash NO ejecuta el comando y el
#    script acaba leyendo contenido RANCIO como si fuera el error de ahora.
#    Costó un diagnóstico entero el 2026-08-01. Manual, cap. 19.8.
FIJAS="$(grep -lE '>[[:space:]]*/tmp/[a-zA-Z]|=/tmp/[a-zA-Z]' "$(dirname "${BASH_SOURCE[0]}")"/*.sh 2>/dev/null \
        | grep -v verificar_robot || true)"
[[ -z "$FIJAS" ]] && _ok "ningún script escribe en una ruta fija de /tmp" \
    || _avi "escriben en rutas fijas de /tmp: $(echo "$FIJAS" | xargs -n1 basename | tr '\n' ' ')" \
            "usa mktemp: con fs.protected_regular=2 root no puede sobrescribirlas"

# ─────────────────────────────────────────────────────────────────────────────
sec "13 · El robot contra el repositorio (¿ha vuelto a divergir?)"

# 🔴 POR QUÉ EXISTE ESTA SECCIÓN
#
#    El 2026-08-03 se midió que fase_7_systemd.sh llevaba tres días sin
#    ejecutarse: /usr/local/bin/atriz-robot.sh instalado era VIEJO, y
#    atriz-nav.{sh,service} NO ESTABAN INSTALADOS — mientras el CHANGELOG
#    afirmaba «instalada pero NO habilitada». Una imagen dorada hecha ese día
#    habría salido sin navegación, en los 16 robots.
#    Evidencia: 00_auditoria/evidencia/63_alineacion_ANTES.txt
#
#    No se compara el fuente con el fuente: se compara lo INSTALADO con el repo.
#    Un «existe el fichero en scripts/» habría dado verde con el sistema vacío.
#
# 📝 La lista NO se escribe aquí. Vive en scripts/sistema/MANIFIESTO.tsv, que es
#    lo mismo que leen los instaladores. Una lista a mano en este fichero se
#    quedaría rancia igual que se quedó rancio fase_7 — el mismo fallo con otro
#    disfraz. Añadir una línea al manifiesto cubre las dos cosas a la vez.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || true)"
MANIF="$REPO/scripts/sistema/MANIFIESTO.tsv"

if [[ -z "$REPO" || ! -f "$MANIF" ]]; then
    # En un clon el repositorio puede no estar (fase_6 ya avisa de ello). Sin
    # repositorio no hay divergencia que medir: es un aviso, NO un fallo. Si
    # fuera _mal, los 15 clones saldrían en rojo por no tener el repo clonado.
    _avi "no encuentro el repositorio: no puedo comprobar la deriva robot↔repo" \
         "git clone …/atriz_migracion en \$HOME · manual, cap. 17"
else
    while IFS=$'\t' read -r ORIG DEST MODO INST FLAGS; do
        [[ -z "${ORIG:-}" || "${ORIG:0:1}" == "#" ]] && continue
        SRC="$REPO/$ORIG"
        BASE="$(basename "$DEST")"
        if [[ ! -f "$SRC" ]]; then
            _mal "el manifiesto cita $ORIG y no existe en el repositorio" \
                 "corrige scripts/sistema/MANIFIESTO.tsv"
        elif [[ ! -e "$DEST" ]]; then
            # 🔴 ESTE es el caso que se escapó con atriz-nav: en git, en el
            #    instalador, y NO en el sistema.
            if [[ "${FLAGS:-}" == "opcional" ]]; then
                _nota "$BASE no instalado (solo lo pone $INST, al preparar la imagen)"
            else
                _mal "$DEST NO está instalado, y sí está en el repositorio" \
                     "sudo bash $REPO/scripts/$INST"
            fi
        elif cmp -s "$SRC" "$DEST"; then
            _ok "$BASE coincide con el repositorio"
        else
            _mal "$DEST DIVERGE de $ORIG ($(diff "$SRC" "$DEST" 2>/dev/null | grep -c '^[<>]') líneas)" \
                 "diff $ORIG $DEST  ·  luego reinstálalo:  sudo bash scripts/$INST"
        fi
    done < "$MANIF"

    # ── El puente del ~/.bashrc: categoría B, así que se comprueba el EFECTO ──
    # No hay copia versionada del .bashrc contra la que hacer `cmp` — pertenece
    # a la distribución. Lo que importa es si un shell interactivo NO de login
    # (tmux, su, un bash suelto) encuentra `ros2`, porque esos no leen
    # /etc/profile.d. Se comprueba lanzando uno de verdad, no leyendo el fichero:
    # un `grep` diría que la línea está aunque no funcionara.
    #
    # 🔴 `env -i`, Y NO ES OPCIONAL. La primera versión hacía `bash -ic …` a
    #    secas, y el shell hijo HEREDA el PATH del padre — que ya tiene ros2
    #    porque este verificador se lanza desde un shell con ROS cargado. La
    #    comprobación pasaba con el puente puesto Y sin él: era una prueba que
    #    no podía fallar. Se descubrió quitando el puente a propósito, no
    #    leyendo el código. Es el quinto caso de este tipo en el proyecto.
    if [[ -n "$(env -i HOME="$HOME" TERM=dumb /bin/bash -ic 'command -v ros2' 2>/dev/null | tail -1)" ]]; then
        _ok "un shell interactivo no-login encuentra ros2"
    else
        _mal "un shell interactivo (tmux, su) NO encuentra ros2" \
             "falta el puente en ~/.bashrc: sudo bash $REPO/scripts/fase_7_systemd.sh"
    fi

    # Y el repositorio contra sí mismo: un fichero corregido y sin commitear se
    # pierde al reflashear, y uno sin empujar se pierde con la microSD.
    # @{u}..HEAD es LOCAL: no toca la red, compara contra la última referencia
    # conocida. Un `git fetch` aquí colgaría el verificador sin WiFi.
    SUCIO="$(git -C "$REPO" status --porcelain 2>/dev/null | wc -l)"
    if [[ "$SUCIO" -eq 0 ]]; then
        _ok "atriz_migracion: sin cambios sin commitear"
    else
        _avi "atriz_migracion: $SUCIO fichero(s) sin commitear" "git -C $REPO status"
    fi
    SINSUBIR="$(git -C "$REPO" rev-list --count '@{u}..HEAD' 2>/dev/null || echo '?')"
    if [[ "$SINSUBIR" == "0" ]]; then
        _ok "atriz_migracion: nada sin empujar"
    elif [[ "$SINSUBIR" == "?" ]]; then
        _nota "atriz_migracion: sin rama remota configurada"
    else
        _avi "atriz_migracion: $SINSUBIR commit(s) sin empujar" "git -C $REPO push"
    fi
fi

# ── El canal con el PC: cómo entra quien trabaja en este robot ───────────────
# 🔴 Medido el 2026-08-03: authorized_keys estaba VACÍO (0 bytes) y los 12
#    accesos del auth.log eran por contraseña. Con eso, cualquier canal
#    automatizado (`ssh rvr-01 …` desde un script o desde el Claude del PC) NO
#    falla: se queda colgado esperando una contraseña que nadie va a escribir.
#    Es aviso y no fallo porque un robot de la flota puede no necesitarlo.
if [[ -s "$HOME/.ssh/authorized_keys" ]]; then
    _ok "SSH por clave publica: $(grep -c '^ssh-' "$HOME/.ssh/authorized_keys" 2>/dev/null || echo 0) clave(s) autorizada(s)"
else
    _avi "~/.ssh/authorized_keys vacío: el acceso es por contraseña" \
         "un canal automático se colgaría esperándola · ssh-copy-id desde el PC"
fi

# 🔴 mDNS puede publicar una dirección INALCANZABLE, y devolverla la primera.
#    Medido: rvr-01.local -> A=10.14.7.7,192.168.1.200,192.168.1.58, y la
#    10.14.7.7 es la del laboratorio, que desde casa no responde (ping al
#    gateway: 100 % de pérdida). Un cliente que resuelva por nombre puede
#    quedarse en el timeout TCP de la IP muerta. No es un fallo del robot —es
#    correcto tener las dos redes puestas a la vez— pero quien conecte tiene
#    que saberlo. Se comprueba el EFECTO: ¿hay ruta hacia el gateway de cada
#    dirección? No basta con que la IP esté configurada.
NUM_IPS="$(ip -4 -o addr show wlan0 2>/dev/null | wc -l)"
if [[ "$NUM_IPS" -gt 1 ]]; then
    MUERTAS=""
    while read -r CIDR; do
        IPX="${CIDR%%/*}"
        # La dirección es alcanzable desde fuera solo si su red tiene salida.
        # Se prueba contra el gateway de esa red: .1 del prefijo, que es la
        # convención del laboratorio y de casa.
        GW="$(ip route show dev wlan0 2>/dev/null | awk -v ip="$IPX" '$1 ~ /\// && $NF==ip {print $1}' | head -1)"
        [[ -z "$GW" ]] && continue
        BASE_GW="$(echo "${GW%%/*}" | awk -F. '{print $1"."$2"."$3".1"}')"
        if ! ping -c1 -W1 -I wlan0 "$BASE_GW" >/dev/null 2>&1; then
            MUERTAS="$MUERTAS $IPX"
        fi
    done < <(ip -4 -o addr show wlan0 2>/dev/null | awk '{print $4}')
    if [[ -n "$MUERTAS" ]]; then
        _avi "wlan0 tiene $NUM_IPS IPv4 y no todas son alcanzables:${MUERTAS}" \
             "mDNS las publica TODAS y puede devolver primero una muerta: fija HostName en el ~/.ssh/config del PC"
    else
        _ok "las $NUM_IPS direcciones IPv4 de wlan0 tienen pasarela que responde"
    fi
fi

# 🔴 Claude Code es herramienta de DESARROLLO del robot de referencia, no del
#    producto (decisión del usuario, 2026-08-03). Guarda en
#    ~/.claude/.credentials.json los tokens OAuth de la suscripción, y ocupa
#    ~386 MB. Un robot de la flota no debe tenerlo; el de referencia sí, y por
#    eso esto es un _nota y no un fallo: quién es quién lo dice fase_6.
if [[ -e "$HOME/.local/bin/claude" || -d "$HOME/.claude" ]]; then
    _nota "Claude Code presente ($(du -sh "$HOME/.claude" 2>/dev/null | cut -f1) en ~/.claude) — quítalo antes del dd: fase_6 lo hace"
    [[ -f "$HOME/.claude/.credentials.json" ]] && \
        _avi "🔐 ~/.claude/.credentials.json: tokens OAuth de tu suscripción" \
             "un dd los copiaría a los 16 robots. fase_6 los borra"
else
    _ok "sin Claude Code (correcto para un robot de la flota)"
fi

# ─────────────────────────────────────────────────────────────────────────────
printf '\n%s' "$AZUL"
echo "======================================================================"
printf '%s' "$FIN"
printf '  %s%d comprobaciones correctas%s' "$VERDE" "$N_OK" "$FIN"
[[ ${#AVISOS[@]} -gt 0 ]] && printf '  ·  %s%d aviso(s)%s' "$AMAR" "${#AVISOS[@]}" "$FIN"
[[ ${#FALLOS[@]} -gt 0 ]] && printf '  ·  %s%d FALLO(S)%s' "$ROJO" "${#FALLOS[@]}" "$FIN"
echo

if [[ ${#AVISOS[@]} -gt 0 ]]; then
    printf '\n%sAVISOS%s (no bloquean, pero míralos):\n' "$AMAR" "$FIN"
    printf '  ! %s\n' "${AVISOS[@]}"
fi
if [[ ${#FALLOS[@]} -gt 0 ]]; then
    printf '\n%sFALLOS%s — este robot NO está listo:\n' "$ROJO" "$FIN"
    printf '  ✗ %s\n' "${FALLOS[@]}"
    printf '\n  Contexto de cada comprobación: 02_manual/MANUAL_ATRIZ_ROS2.md\n'
    printf '  Diagnóstico de fallos:          03_operacion/RUNBOOK.md\n'
    echo "======================================================================"
    exit 1
fi
[[ $HARDWARE -eq 0 ]] && printf '  %sVuelve a pasarlo con --hardware para probar el RVR y el LIDAR.%s\n' "$GRIS" "$FIN"
echo "======================================================================"
[[ ${#AVISOS[@]} -gt 0 ]] && exit 2
exit 0
