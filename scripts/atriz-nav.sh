#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# atriz-nav.sh — arranca la navegación (AMCL + Nav2) bajo systemd
# ═══════════════════════════════════════════════════════════════════════════════
# Lo ejecuta atriz-nav.service. Se instala en /usr/local/bin/ con
# fase_7_systemd.sh. No lo copies a mano.
#
# POR QUÉ UN ENVOLTORIO Y NO UN ExecStart DIRECTO
#
#   El mismo motivo que atriz-robot.sh: systemd NO ejecuta un shell de login,
#   así que no lee `~/.bashrc` ni `/etc/profile.d`. Un `ExecStart=ros2 launch …`
#   falla con «ros2: command not found», y si se pone la ruta absoluta arranca
#   SIN ROS_DOMAIN_ID — o sea, los 16 robots en el dominio 0, viéndose entre sí.
#   Es justo lo que la decisión D1 de ARQUITECTURA.md quiere evitar, y falla en
#   silencio.
#
# 📝 NO VERIFICADO bajo systemd — escrito el 2026-08-03. Lo verifica la tarea 4
#    del plan `00_auditoria/planes/2026-08-03-arranque-navegacion.md`, que exige
#    el mapa del aula y por tanto estar en el laboratorio.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

log() { echo "[atriz-nav] $*"; }

# ── Entorno de ROS ────────────────────────────────────────────────────────────
# 🔴 Los `setup.bash` de ROS NO son compatibles con `set -u`:
#    «AMENT_TRACE_SETUP_FILES: unbound variable» mata el script antes de hacer
#    nada, y el mensaje no menciona ROS. Es una trampa documentada del proyecto,
#    y ya mordió una vez en atriz-escaneo.sh.
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/atriz_ws/install/setup.bash"
set -u

# ── El ROS_DOMAIN_ID, que es lo que aísla a cada robot ────────────────────────
if [[ -r /etc/profile.d/atriz-robot.sh ]]; then
    set +u; source /etc/profile.d/atriz-robot.sh; set -u
fi
log "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-<sin definir>}"

# ── El mapa ───────────────────────────────────────────────────────────────────
# 🔴 FALLA ALTO SI NO ESTÁ, a propósito. `localizacion.launch.py` exige el
#    argumento `mapa` y NO tiene valor por defecto; sin mapa, AMCL no sabe dónde
#    está el robot. Arrancar igualmente daría un sistema que parece vivo y no
#    puede navegar — la firma de fallo que este proyecto lleva toda la migración
#    documentando.
MAPA="${ATRIZ_MAPA:-$HOME/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/maps/aula.yaml}"
if [[ ! -r "$MAPA" ]]; then
    log "🔴 no hay mapa legible en $MAPA"
    log "   AMCL lo necesita y localizacion.launch.py no tiene valor por"
    log "   defecto. Sin él la navegación arrancaría ciega."
    log "   → genera uno con slam.launch.py y guárdalo ahí, o apunta a otro"
    log "     con la variable de entorno ATRIZ_MAPA."
    exit 1
fi
log "mapa: $MAPA"

# ── Arrancar ──────────────────────────────────────────────────────────────────
# 📝 Son dos ficheros de launch distintos, así que no caben en un solo
#    `ros2 launch`. Se lanza AMCL en segundo plano y Nav2 con `exec`, para que
#    Nav2 herede el PID: sin eso systemd vigilaría a este script y los SIGINT no
#    llegarían al launch, así que Nav2 no ejecutaría su apagado limpio.
log "arrancando localizacion.launch.py (AMCL)"
ros2 launch atriz_rvr_bringup localizacion.launch.py mapa:="$MAPA" &
AMCL_PID=$!

# Si este script se va, se lleva AMCL por delante: un Nav2 vivo sobre una
# localización muerta publicaría en un marco que ya no sostiene nadie.
trap 'kill -INT "$AMCL_PID" 2>/dev/null || true' EXIT INT TERM

log "arrancando nav2.launch.py"
exec ros2 launch atriz_rvr_bringup nav2.launch.py
