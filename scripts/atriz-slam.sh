#!/usr/bin/env bash
# atriz-slam.sh — lo que ejecuta atriz-slam.service. NO se llama a mano.
#
# Mismo patrón que `atriz-nav.sh`, y por las mismas razones: systemd NO lee
# `~/.bashrc`, así que hay que hacer `source` explícito de los dos `setup.bash` y
# del `profile.d` que define `ROS_DOMAIN_ID`. Sin él, los 16 robots caerían al
# dominio 0 **en silencio** y se verían entre ellos.
#
# ⚠️ NO exige mapa —SLAM lo crea— pero SÍ exige que el directorio donde va a
#    guardarse exista y sea escribible: un SLAM de veinte minutos que no puede
#    guardar es la misma familia de fallo que Nav2 sin mapa.

set -euo pipefail

log() { echo "[atriz-slam] $*"; }

# 🔴 `set +u` alrededor de los `source`. Los `setup.bash` de ROS leen variables
#    sin definir, y con `set -u` el guion muere ahí — trampa ya documentada que
#    mordió a `atriz-escaneo.sh`.
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/atriz_ws/install/setup.bash"
set -u

if [[ -r /etc/profile.d/atriz-robot.sh ]]; then
    set +u; source /etc/profile.d/atriz-robot.sh; set -u
fi
log "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-<sin definir>}"

# ── Dónde se guardará el mapa ────────────────────────────────────────────────
# No se necesita para arrancar, pero si no se puede escribir hay que decirlo
# AHORA y no cuando el alumno lleve veinte minutos mapeando.
DIR_MAPAS="${ATRIZ_DIR_MAPAS:-$HOME/mapas}"
if [[ ! -d "$DIR_MAPAS" ]]; then
    log "el directorio de mapas no existe, creándolo: $DIR_MAPAS"
    mkdir -p "$DIR_MAPAS" || { log "🔴 no se pudo crear $DIR_MAPAS"; exit 1; }
fi
if [[ ! -w "$DIR_MAPAS" ]]; then
    log "🔴 $DIR_MAPAS no es escribible por $(id -un)."
    log "   SLAM arrancaría y no podrías guardar nada. No se arranca."
    exit 1
fi
log "los mapas se guardarán en: $DIR_MAPAS"
log "   guarda con:  ros2 run nav2_map_server map_saver_cli -f $DIR_MAPAS/<nombre>"

# 🔴 `exec`: el PID principal de la unidad tiene que ser el launch, o el SIGINT
#    de `systemctl stop` no llega a `slam_toolbox` y el `.posegraph` se queda a
#    medias. Es la razón que `atriz-nav.sh:59-72` ya documenta.
#
# 📝 Aquí NO hace falta el `trap` de `atriz-nav.sh`: allí hay DOS launch (AMCL y
#    Nav2) y uno queda en segundo plano. Aquí solo hay uno.
log "arrancando slam.launch.py"
exec ros2 launch atriz_rvr_bringup slam.launch.py
