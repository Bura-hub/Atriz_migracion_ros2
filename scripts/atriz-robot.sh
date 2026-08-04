#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# atriz-robot.sh — arranca robot.launch.py bajo systemd
# ═══════════════════════════════════════════════════════════════════════════════
# Lo ejecuta atriz-robot.service. Se instala en /usr/local/bin/ con
# fase_7_systemd.sh. No lo copies a mano.
#
# POR QUÉ EXISTE ESTE ENVOLTORIO Y NO UN ExecStart DIRECTO
#
#   systemd NO ejecuta un shell de login: no lee `~/.bashrc` ni `/etc/profile.d`.
#   Un `ExecStart=ros2 launch ...` falla con «ros2: command not found», y si se
#   pone la ruta absoluta arranca SIN ROS_DOMAIN_ID — o sea, todos los robots en
#   el dominio 0, viéndose entre sí. Que es justo lo que la decisión D1 de
#   `ARQUITECTURA.md` quiere evitar, y falla en silencio.
#
# ✅ VERIFICADO bajo systemd el 2026-07-31, con un reinicio de verdad: el robot
#    volvió solo (PID 711), ROS_DOMAIN_ID salió de /etc/profile.d y /odom a
#    16.49 Hz. Evidencia 33.
#
# 📝 Lo que NO se ha ejercitado: la espera de puertos de más abajo. Las tres
#    veces salió `tras 0s` —udev llega antes—, también en frío. Es una red de
#    seguridad SIN ESTRENAR, no una comprobación aprobada.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

WS=/home/sphero/atriz_ws
ESPERA_HW=${ATRIZ_ESPERA_HW:-60}      # segundos que se esperan los dos puertos

log() { echo "[atriz-robot] $*"; }

# ── 1. El entorno, en el mismo orden que un shell de login ────────────────────
# 🔴 `set -u` APAGADO mientras se cargan los setup de ROS. No son compatibles:
#     /opt/ros/jazzy/setup.bash: line 8: AMENT_TRACE_SETUP_FILES: unbound variable
#    Con `set -euo pipefail` eso mata el script ANTES de arrancar nada, y el
#    mensaje no menciona ROS ni el servicio. Se descubrió ejecutándolo con `env -i`
#    el 2026-07-31; leyéndolo no se ve.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

# ROS_DOMAIN_ID lo fija first-boot.sh al personalizar el clon de la imagen.
if [[ -f /etc/profile.d/atriz-robot.sh ]]; then
    # shellcheck disable=SC1091
    source /etc/profile.d/atriz-robot.sh
else
    log "⚠️ no existe /etc/profile.d/atriz-robot.sh"
    log "   este robot no ha pasado por first-boot.sh, o se instaló a mano"
fi

if [[ -z "${ROS_DOMAIN_ID:-}" ]]; then
    # 🔴 Parar es lo correcto. Arrancar en el dominio 0 pone a este robot a
    # hablar con todos los demás, y el síntoma —topics duplicados, TF que salta—
    # aparece lejos de la causa.
    log "🔴 ROS_DOMAIN_ID no está definido. NO se arranca."
    log "   arréglalo con /boot/firmware/robot_id.txt y first-boot.sh, o exporta"
    log "   ROS_DOMAIN_ID en /etc/profile.d/atriz-robot.sh"
    exit 1
fi

if [[ ! -f "$WS/install/setup.bash" ]]; then
    log "🔴 no existe $WS/install/setup.bash — el workspace no está compilado"
    exit 1
fi
# shellcheck disable=SC1091
source "$WS/install/setup.bash"
set -u          # a partir de aquí sí queremos que una variable sin definir chille

# ⚠️ El RMW también sale del entorno del usuario, y una discrepancia NO da error:
# dos nodos con implementaciones distintas simplemente no se ven. Hoy coinciden
# porque `rmw_fastrtps_cpp` es el de por defecto en Jazzy, así que esto es un
# seguro, no un arreglo.
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

log "ROS_DOMAIN_ID=$ROS_DOMAIN_ID  RMW=$RMW_IMPLEMENTATION  hostname=$(hostname)"

# ── 2. Esperar el hardware ────────────────────────────────────────────────────
# systemd puede lanzarnos antes de que udev haya creado los enlaces. Sin esto el
# launch arranca, no encuentra el puerto y el nodo queda vivo y mudo — que es el
# fallo más caro de diagnosticar de este proyecto.
#
# 🔴🔴 Y ESTA ESPERA ESTUVO ROTA, EN SILENCIO, HASTA EL 2026-08-04.
#    Decía `(( t++ ))`. Con `t=0` el POST-incremento evalúa a 0, que en
#    aritmética es FALSO, así que el comando devuelve estado 1 y `set -e`
#    —línea 24— mataba el script en la PRIMERA vuelta del bucle. Consecuencias,
#    las tres medidas:
#      · la espera de ESPERA_HW segundos nunca ocurrió: moría en ~1 s (el sleep)
#      · el `🔴 ... no apareció` de abajo era INALCANZABLE
#      · systemd solo veía «status=1/FAILURE» sin una línea de explicación
#    O sea: la salvaguarda contra «el nodo queda vivo y mudo» estaba desactivada
#    por una trampa de bash, y su síntoma era el mismo que venía a evitar.
#    Se usa una ASIGNACIÓN, que siempre devuelve 0. Hermana de la trampa ya
#    documentada de `set -u` contra los `setup.bash` de ROS.
esperar() {
    local dev=$1 t=0
    while [[ ! -e "$dev" ]]; do
        if (( t >= ESPERA_HW )); then
            log "🔴 $dev no apareció en ${ESPERA_HW}s"
            [[ "$dev" == /dev/ydlidar ]] && diagnosticar_lidar
            return 1
        fi
        sleep 1
        t=$(( t + 1 ))     # NO `(( t++ ))`: devuelve 1 cuando t vale 0
    done
    log "✓ $dev  (tras ${t}s)"
}

# 🔴 El mensaje va AQUÍ, no solo en verificar_robot.sh: el modo de fallo es que
#    el arranque muere y NADIE ejecuta el verificador después. La causa habitual
#    de que falte /dev/ydlidar no es que falte la regla, es que el lidar está en
#    otro conector USB — la regla casa por ID_PATH, el puerto FÍSICO.
#    Medido el 2026-08-04: costó cuatro intentos de cable porque el único error
#    visible («/stop_scan no respondió en 30s») apunta al launch. Evidencia 69.
diagnosticar_lidar() {
    local regla=/etc/udev/rules.d/99-ydlidar.rules esperado='' real='' d v pe pr
    [[ -r $regla ]] && esperado=$(grep -ho 'ID_PATH}=="[^"]*"' "$regla" | head -1 | sed 's/.*=="//;s/"//')
    for d in /dev/ttyUSB*; do
        [[ -e $d ]] || continue
        v=$(udevadm info -q property -n "$d" 2>/dev/null | sed -n 's/^ID_VENDOR_ID=//p')
        [[ $v == 10c4 ]] && real=$(udevadm info -q property -n "$d" 2>/dev/null | sed -n 's/^ID_PATH=//p')
    done
    if [[ -z $real ]]; then
        log "   ↳ no se ve ningún adaptador CP2102 (10c4): ¿está el lidar enchufado y alimentado?"
        return
    fi
    pr=$(printf '%s' "$real"     | sed -n 's/.*usb-0:\([0-9.]*\).*/\1/p')
    pe=$(printf '%s' "$esperado" | sed -n 's/.*usb-0:\([0-9.]*\).*/\1/p')
    if [[ -n $pe && $pr != "$pe" ]]; then
        log "   ↳ el LIDAR está en el PUERTO USB ${pr:-?} y la regla udev espera el ${pe:-?}"
        log "   ↳ MUEVE EL CABLE al conector ${pe:-esperado} (cuál es: FLOTA.md). El número ttyUSBn NO importa"
    else
        log "   ↳ el adaptador está en el puerto correcto (${pr:-?}) pero no hay enlace:"
        log "   ↳ ¿está instalada la regla? sudo udevadm control --reload-rules && sudo udevadm trigger"
    fi
}

esperar /dev/rvr
esperar /dev/ydlidar

# ── 3. Arrancar ───────────────────────────────────────────────────────────────
# `exec` para que el launch herede el PID: sin él systemd vigila a este script y
# los SIGINT no llegan a ros2 launch, así que el driver nunca ejecuta su apagado
# limpio (apagar LEDs y el LED del sensor de color).
log "arrancando robot.launch.py"
exec ros2 launch atriz_rvr_bringup robot.launch.py "$@"
