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
        || _mal "el SDK NO usa /dev/rvr por defecto" "¿estás en la rama migracion-ros2? falta el commit 67c8776"
    grep -q 'sensor_control.start(interval=60)' "$WS/atriz_rvr_driver/scripts/Atriz_rvr_node.py" 2>/dev/null \
        && _ok "streaming a interval=60 ms → 16.59 Hz (commit 24c7749)" \
        || _avi "el driver no tiene interval=60" "con 250 ms la odometría va a 3.85 Hz; falta 24c7749"
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
        if timeout 6 ros2 topic list 2>/dev/null | grep -qx '/odom'; then
            HZ_ODOM="$(timeout 12 ros2 topic hz /odom --window 10 2>/dev/null \
                       | grep -m1 -oE 'average rate: [0-9.]+' | grep -oE '[0-9.]+')"
            HZ_ODOM="${HZ_ODOM:-0}"
            # El firmware no baja de interval=60 ms => 16.5-16.7 Hz. Por debajo
            # de 10 Hz algo va mal; a 0 el RVR esta dormido o el enlace caido.
            if awk -v h="$HZ_ODOM" 'BEGIN{exit !(h > 10)}'; then
                _ok "/odom a ${HZ_ODOM} Hz (esperado ~16.7)"
            elif awk -v h="$HZ_ODOM" 'BEGIN{exit !(h > 0)}'; then
                _mal "/odom solo a ${HZ_ODOM} Hz (esperado ~16.7)" \
                     "revisa streaming_interval_ms=60 en robot.launch.py"
            else
                _mal "/odom EXISTE pero no publica NADA: el RVR esta dormido" \
                     "reinicia el driver. El proceso no muere, asi que systemd no lo arregla. Manual cap. 9.8"
            fi
        else
            _nota "/odom no esta publicado: robot.launch.py no esta corriendo."
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
    if [[ -f /etc/profile.d/atriz-robot.sh ]] \
       && grep -q 'ROS_DOMAIN_ID' "$HOME/.bashrc" 2>/dev/null; then
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
    sec "9 · Hablar con el hardware de verdad"
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

    if [[ -c /dev/ttyUSB0 && -f "$MED/x2_parse.py" ]]; then
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
