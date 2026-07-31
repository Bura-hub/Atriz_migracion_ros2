#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# atriz-escaneo — enciende o apaga el barrido del LIDAR
# ═══════════════════════════════════════════════════════════════════════════════
#   atriz-escaneo on       # el robot puede navegar y conducir
#   atriz-escaneo off      # reposo: el X2 baja de 11.8 a 2.7 Hz
#   atriz-escaneo estado   # ¿está publicando /scan?
#
# Se instala en /usr/local/bin/atriz-escaneo con fase_7_systemd.sh.
#
# ═══════════════════════════════════════════════════════════════════════════════
# QUÉ HACE DE VERDAD, Y QUÉ NO
# ═══════════════════════════════════════════════════════════════════════════════
# Llama a `/stop_scan` y `/start_scan`, dos servicios `std_srvs/srv/Empty` del
# `ydlidar_ros2_driver_node`. Medido el 2026-07-31:
#
#     /scan escaneando      : 11.81 Hz     motor a 11.8 Hz
#     /scan tras stop_scan  :  0.00 Hz     motor a  2.7 Hz
#     /scan tras start_scan : 13.44 Hz     se recupera solo
#
# ⚠️ `off` NO APAGA EL LIDAR. Baja el motor al mismo reposo al que llega solo
#    cuando no hay driver; el láser y la electrónica siguen alimentados. Pararlo
#    del todo exige cortar los 5 V del USB, y la Pi 4 no puede.
#
# 🔴 CON EL ESCANEO EN `off` EL ROBOT NO CONDUCE, y es a propósito: sin `/scan`
#    el `collision_monitor` bloquea el movimiento (verificado, manual cap. 12).
#    Si el robot «no responde a cmd_vel», esto es lo primero que hay que mirar.
#    Los servicios de movimiento del driver SÍ funcionan — hablan al RVR por el
#    puerto serie y se saltan el monitor (CLAUDE.md).
#
# 📝 NO VERIFICADO como script instalado. Lo que sí está verificado son las dos
#    llamadas a servicio que hace, en ROS y por oído (manual, cap. 8.4a).
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

ESPERA=${ATRIZ_ESPERA_SRV:-30}

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
[[ -f /etc/profile.d/atriz-robot.sh ]] && source /etc/profile.d/atriz-robot.sh
[[ -f /home/sphero/atriz_ws/install/setup.bash ]] \
    && source /home/sphero/atriz_ws/install/setup.bash

llamar() {
    local srv=$1
    # `ros2 service call` ya espera a que el servicio aparezca, así que el
    # timeout es contra un nodo que no llega a existir, no contra la llamada.
    #
    # 📝 Y se usa una llamada, no `ros2 service list`: esa lista NO es
    #    autoritativa —omitió 1 de 18 servicios del driver (CLAUDE.md)—, pero un
    #    cliente sí lo es.
    if timeout "$ESPERA" ros2 service call "/$srv" std_srvs/srv/Empty > /dev/null; then
        return 0
    fi
    echo "🔴 /$srv no respondió en ${ESPERA}s. ¿está corriendo robot.launch.py?" >&2
    echo "   systemctl status atriz-robot" >&2
    return 1
}

# ¿Llega /scan? Se mide el RITMO, no si el topic existe: un topic registrado y
# mudo es el síntoma estrella de este proyecto.
hay_scan() {
    timeout 8 ros2 topic echo /scan --once --no-daemon > /dev/null 2>&1
}

case "${1:-}" in
    on)
        llamar start_scan
        sleep 2
        if hay_scan; then
            echo "✅ escaneo ENCENDIDO — /scan publica, el robot puede conducir"
        else
            echo "⚠️ start_scan respondió pero /scan no publica. Mira el journal:"
            echo "   journalctl -u atriz-robot -n 50"
            exit 1
        fi
        ;;
    off)
        llamar stop_scan
        echo "✅ escaneo APAGADO — el X2 baja a ~2.7 Hz"
        echo "   ⚠️ el robot NO conducirá hasta un 'atriz-escaneo on'"
        ;;
    estado)
        if hay_scan; then
            echo "escaneo: ENCENDIDO  (/scan publica)"
        else
            echo "escaneo: apagado o el driver no está corriendo"
        fi
        ;;
    *)
        sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
        exit 2
        ;;
esac
