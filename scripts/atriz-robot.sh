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
# 📝 NO VERIFICADO bajo systemd — escrito el 2026-07-31. Lo que sí se ha probado
#    está anotado en cada sitio.
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
esperar() {
    local dev=$1 t=0
    while [[ ! -e "$dev" ]]; do
        (( t >= ESPERA_HW )) && { log "🔴 $dev no apareció en ${ESPERA_HW}s"; return 1; }
        sleep 1; (( t++ ))
    done
    log "✓ $dev  (tras ${t}s)"
}
esperar /dev/rvr
esperar /dev/ydlidar

# ── 3. Arrancar ───────────────────────────────────────────────────────────────
# `exec` para que el launch herede el PID: sin él systemd vigila a este script y
# los SIGINT no llegan a ros2 launch, así que el driver nunca ejecuta su apagado
# limpio (apagar LEDs y el LED del sensor de color).
log "arrancando robot.launch.py"
exec ros2 launch atriz_rvr_bringup robot.launch.py "$@"
