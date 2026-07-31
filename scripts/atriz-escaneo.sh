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
# ✅ VERIFICADO el 2026-07-31 contra el servicio corriendo: `on`, `off` y
#    `estado` — este último 3 de 3 en cada estado, después de reescribirlo (ver
#    el comentario de `hay_scan`, que tenía DOS fallos).
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

ESPERA=${ATRIZ_ESPERA_SRV:-30}

# 🔴 `set -u` APAGADO mientras se cargan los setup de ROS. No son compatibles:
#     /opt/ros/jazzy/setup.bash: line 8: AMENT_TRACE_SETUP_FILES: unbound variable
#
#    Y esto NO es teoría: el 2026-07-31, la primera vez que systemd arrancó el
#    robot de verdad, el `ExecStartPost` murió justo aquí con `status=1/FAILURE`.
#    El servicio siguió en pie —el `-` de la unidad hizo su trabajo— pero el
#    barrido se quedó ENCENDIDO, que era el único motivo de llamarlo.
#
#    El mismo fallo estaba arreglado en `atriz-robot.sh` y no se aplicó aquí.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
[[ -f /etc/profile.d/atriz-robot.sh ]] && source /etc/profile.d/atriz-robot.sh
[[ -f /home/sphero/atriz_ws/install/setup.bash ]] \
    && source /home/sphero/atriz_ws/install/setup.bash
set -u

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

# ¿Llega /scan? Se mide que LLEGA UN MENSAJE, no que el topic exista: un topic
# registrado y mudo es el síntoma estrella de este proyecto.
#
# 🔴 AQUÍ NO SIRVE `ros2 topic echo`, POR DOS RAZONES DISTINTAS, y las dos se
#    descubrieron ejecutándolo el 2026-07-31:
#
#    1. `/scan` se publica BEST_EFFORT y `echo` se suscribe RELIABLE por
#       defecto. Sin `--qos-reliability best_effort` no llega nada nunca.
#    2. Y ni con eso: con `--no-daemon` tiene que DESCUBRIR el tipo del topic, y
#       falla de forma intermitente —2 de cada 3 intentos— con
#       `Could not determine the type for the passed topic`, con el LIDAR
#       girando perfectamente. Un comprobador que acierta un tercio de las veces
#       es peor que no tenerlo.
#
#    Un suscriptor propio no tiene ninguno de los dos problemas: el tipo se dice,
#    no se descubre, y el QoS se elige.
hay_scan() {
    timeout 15 python3 -c '
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
import sys
rclpy.init()
n = Node("atriz_escaneo_estado"); c = [0]
n.create_subscription(LaserScan, "scan", lambda m: c.__setitem__(0, c[0] + 1),
                      QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
ex = SingleThreadedExecutor(); ex.add_node(n)
t0 = time.monotonic()
while time.monotonic() - t0 < 5.0 and c[0] < 3:
    ex.spin_once(timeout_sec=0.1)
sys.exit(0 if c[0] >= 3 else 1)
' 2>/dev/null
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
