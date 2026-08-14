#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# atriz-escaneo — enciende o apaga el barrido del LIDAR
# ═══════════════════════════════════════════════════════════════════════════════
#   atriz-escaneo on       # el robot puede navegar y conducir
#   atriz-escaneo off      # reposo: el X2 baja de 11.8 a 2.7 Hz
#   atriz-escaneo estado   # ¿está publicando /scan?
#   atriz-escaneo off-si-sobra [unidad]  # apaga SOLO si ninguna unidad de
#                                # navegación lo necesita Y (con [unidad]) si
#                                # el barrido no estaba ya encendido cuando esa
#                                # unidad llegó. Lo usan atriz-slam y atriz-nav
#                                # al parar: con DOS consumidores, un `off`
#                                # incondicional deja ciego al otro EN SILENCIO.
#   atriz-escaneo on-recordando <unidad>  # `on` anotando si YA estaba
#                                # encendido — la otra mitad: al parar, esa
#                                # unidad devuelve el estado que encontró.
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
    # $1 (opcional): ventana en segundos. 5 por defecto; `on-recordando` usa 2
    # para no encarecer el arranque de nav cuando el barrido está apagado (el
    # caso común) — con él encendido, los 3 mensajes llegan en ~0,3 s igual.
    ATRIZ_VENTANA="${1:-5}" timeout 15 python3 -c '
import os, time
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
ventana = float(os.environ.get("ATRIZ_VENTANA", "5"))
while time.monotonic() - t0 < ventana and c[0] < 3:
    ex.spin_once(timeout_sec=0.1)
sys.exit(0 if c[0] >= 3 else 1)
' 2>/dev/null
}

# La marca de «ya estaba encendido cuando llegué» — la mitad B del conflicto 2
# (decisión del usuario, 2026-08-14). Vive en /run/atriz (lo crea atriz-robot
# con RuntimeDirectory+Preserve: sobrevive a reinicios de unidad, muere al
# reiniciar la Pi). Una por unidad: nav y slam no se pisan la suya.
marca_previa() { echo "/run/atriz/barrido-previo-${1:?falta la unidad}"; }

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
    on-recordando)
        # ── `on`, PERO ANOTANDO SI YA ESTABA ENCENDIDO ───────────────────────
        # Lo usan los ExecStartPre de atriz-nav y atriz-slam. Es la mitad que
        # le faltaba a `off-si-sobra`: ese cubre a las UNIDADES, y esto cubre
        # al consumidor HUMANO — el alumno con atriz.py o la teleop web que
        # tenía el barrido encendido ANTES de que alguien arrancara la
        # navegación. Al parar, `off-si-sobra` consume la marca y DEVUELVE EL
        # ESTADO ENCONTRADO (el mismo principio que atriz.py:177-189).
        #
        # ⚠️ Lo que NO cubre, dicho desde el diseño: el orden inverso — un
        #    alumno que enciende DESPUÉS de arrancado nav. Ese caso queda como
        #    estaba (aviso en la web al parar).
        UNIDAD="${2:?uso: atriz-escaneo on-recordando <unidad>}"
        M="$(marca_previa "$UNIDAD")"
        if hay_scan 2; then
            # touch puede fallar si /run/atriz no existe (atriz-robot nunca
            # arrancó este boot — imposible con Requires=, pero por si acaso):
            # el sesgo del fallo es «sin marca», o sea el comportamiento viejo.
            touch "$M" 2>/dev/null \
                && echo "escaneo: ya estaba ENCENDIDO — anotado; al parar $UNIDAD se dejará como está" \
                || echo "⚠️ no pude anotar la marca en $M: al parar se apagará (comportamiento viejo)"
        else
            # Marca rancia de una vida anterior (un crash entre medias): se
            # limpia para que el paro refleje EL ESTADO DE ESTE arranque.
            rm -f "$M"
        fi
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
    off-si-sobra)
        # ── APAGA SOLO SI NADIE MÁS LO NECESITA ──────────────────────────────
        # 🔴 POR QUÉ EXISTE. `atriz-nav.service` hacía `ExecStopPost=atriz-escaneo
        #    off` sin condición, y su comentario lo justificaba así: «se acepta
        #    porque parar la navegación es un acto explícito de operador, no algo
        #    que ocurra solo».
        #
        #    **Esa premisa murió el día que existe el botón en la web** (decisión
        #    del usuario, 2026-08-06). Parar la navegación pasa a ser un clic de
        #    un alumno cualquiera sobre un robot que puede estar compartido — y
        #    apagar /scan deja al robot SIN OBEDECER cmd_vel para todos los
        #    demás, sin ningún error: el collision_monitor bloquea el movimiento
        #    (medido: 0,0 cm contra 9,9). Desde el navegador es indistinguible de
        #    un robot averiado.
        #
        # ⚠️ EL SESGO DEL FALLO ES DELIBERADO: si la comprobación se equivoca,
        #    deja el barrido ENCENDIDO (desgaste del X2) en vez de apagado (robot
        #    ciego que parece averiado). El desgaste se ve en la factura; un robot
        #    que no obedece se lleva una clase por delante.
        #
        # 📝 Es el mismo principio que `atriz.py:177-189` ya implementa para el
        #    alumno: apagar solo lo que uno encendió.
        OTRAS=""
        for U in atriz-slam.service atriz-nav.service; do
            # 🔴 `|| true` OBLIGATORIO. `systemctl is-active` devuelve **3** para
            #    una unidad inactiva: eso NO es un error, es la respuesta. Con
            #    `set -e`, la asignación mata el guion antes de decidir nada — y
            #    con el `-` del ExecStopPost, systemd se lo traga en silencio.
            #    Medido el 2026-08-07: el barrido se quedaba ENCENDIDO tras
            #    parar SLAM y no aparecía una sola línea en el journal.
            #    Es la TERCERA vez que este patrón muerde a este proyecto, tras
            #    `(( t++ ))` en atriz-robot.sh y `[[ … ]] && kill` en un banco.
            EST="$(systemctl is-active "$U" 2>/dev/null || true)"
            if [[ "$EST" == "active" || "$EST" == "activating" ]]; then
                OTRAS="$OTRAS $U"
            fi
        done
        if [[ -n "$OTRAS" ]]; then
            echo "escaneo: se DEJA ENCENDIDO —lo necesita:$OTRAS"
            exit 0
        fi
        # ── Y LA MARCA DEL CONSUMIDOR HUMANO (2026-08-14, decisión B) ───────
        # Si `on-recordando` anotó que el barrido YA estaba encendido cuando
        # esta unidad llegó, se DEVUELVE EL ESTADO ENCONTRADO: encendido. La
        # marca se consume — el siguiente ciclo decide con su propia foto.
        if [[ -n "${2:-}" ]]; then
            M="$(marca_previa "$2")"
            if [[ -f "$M" ]]; then
                rm -f "$M"
                echo "escaneo: se DEJA ENCENDIDO — ya lo estaba antes de que $2 lo encendiera (se devuelve el estado encontrado)"
                exit 0
            fi
        fi
        llamar stop_scan
        echo "✅ escaneo APAGADO — ninguna unidad de navegación lo necesitaba"
        ;;
    estado)
        if hay_scan; then
            echo "escaneo: ENCENDIDO  (/scan publica)"
        else
            echo "escaneo: apagado o el driver no está corriendo"
        fi
        ;;
    *)
        sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
        exit 2
        ;;
esac
