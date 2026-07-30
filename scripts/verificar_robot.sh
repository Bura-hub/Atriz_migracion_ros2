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

comprobar_contiene "noatime en /" "$(findmnt -no OPTIONS / 2>/dev/null)" "noatime" \
                   "añade ',noatime' a la línea de / en /etc/fstab"

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
    _avi "no existe $WS" "git clone -b migracion-ros2 https://github.com/Bura-hub/Atriz_rvr.git ~/atriz_ws/src/"
fi

# ─────────────────────────────────────────────────────────────────────────────
sec "8 · ROS 2 — PENDIENTE"

if [[ -d /opt/ros/jazzy ]]; then
    _ok "ROS 2 Jazzy instalado en /opt/ros/jazzy"
    if [[ -n "${ROS_DOMAIN_ID:-}" ]]; then
        ESPERADO="$(hostname | grep -oE '[0-9]+$' | sed 's/^0*//')"
        comprobar "ROS_DOMAIN_ID" "$ROS_DOMAIN_ID" "$ESPERADO" \
                  "un dominio por robot; ver ARQUITECTURA.md D1. Lo fija /etc/profile.d/atriz-robot.sh"
    else
        _avi "ROS_DOMAIN_ID no está definido en este shell" "source /etc/profile.d/atriz-robot.sh"
    fi
    dpkg -l ros-jazzy-desktop 2>/dev/null | grep -q '^ii' \
        && _avi "ros-jazzy-desktop instalado: son ~236 paquetes con Gazebo y RViz en un robot sin pantalla" \
                "debe ser ros-jazzy-ros-base" \
        || _ok "sin ros-jazzy-desktop (correcto: ros-base)"
else
    _nota "ROS 2 aún no instalado — es la Etapa E. Nada que comprobar todavía."
fi
_nota "PENDIENTE de añadir aquí: /dev/ydlidar, unidades systemd del stack,"
_nota "rosbridge en :9090, árbol TF conectado, y frecuencias de /odom y /scan."

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
