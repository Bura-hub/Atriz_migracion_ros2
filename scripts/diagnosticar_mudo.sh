#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# diagnosticar_mudo.sh — «el robot sale sin señal de vida en la web»
# ═══════════════════════════════════════════════════════════════════════════════
# Contesta UNA pregunta y la contesta en el orden correcto: ¿el robot no publica,
# o publica y lo que falla es el camino hasta la web?
#
# Solo lectura. NO necesita sudo. NO mueve el robot. NO reinicia nada.
#
# POR QUÉ EXISTE
#
#   El 2026-08-12, en el laboratorio, rvr-01 salió en la web con «Voltaje —» y
#   «sin señal de vida». El robot estaba encendido, el servicio en verde, el
#   driver vivo al 21 % de CPU y con la batería leída (8,37 V). Lo que no cruzaba
#   era DDS: los publicadores existían y NO llegaba un mensaje a nadie, tampoco a
#   un `echo` en la propia Pi. Diagnosticarlo costó una docena de comandos, y este
#   guion es esos comandos en el orden que separa las hipótesis. Evidencia 102.
#
# 🔴 EL PRIMER INSTRUMENTO QUE MINTIÓ FUE EL DEMONIO DEL CLI. `ros2 topic list`
#    daba una lista INCOMPLETA —sin `/battery_state` ni `/odom`— sobre un robot
#    cuyos publicadores existían. Por eso este guion REINICIA el demonio antes de
#    preguntar nada. Y `ros2 node list` puede salir VACÍO con todo publicando
#    perfectamente: no se usa como síntoma de nada.
#
# ⚠️ VERIFICADO el 2026-08-12 sobre rvr-01 SANO (la rama «publica»). La rama
#    «mudo» reproduce a mano lo que se midió aquel día, pero el guion entero NO se
#    ha ejecutado sobre un robot en ese estado: para eso hace falta que vuelva a
#    pasar.
# ═══════════════════════════════════════════════════════════════════════════════
set -uo pipefail        # 🔴 sin `-e`: aquí un comando que falla ES un resultado

VERDE=$'\e[32m'; ROJO=$'\e[31m'; AMAR=$'\e[33m'; GRIS=$'\e[90m'; FIN=$'\e[0m'
ok()   { echo "  ${VERDE}✓${FIN} $*"; }
mal()  { echo "  ${ROJO}🔴${FIN} $*"; }
avis() { echo "  ${AMAR}⚠️${FIN}  $*"; }
dato() { echo "  ${GRIS}·${FIN} $*"; }
titulo() { echo; echo "── $* ──"; }

echo "diagnosticar_mudo.sh · $(hostname) · $(date '+%F %T %Z')"

# ── 1. ¿Están los procesos? ───────────────────────────────────────────────────
# 🔴 `systemctl is-active` NO sirve solo: el PID principal es `ros2 launch`, que
#    SOBREVIVE a la muerte de un nodo suyo. Un servicio en verde con el driver
#    muerto es un modo de fallo documentado de este proyecto.
titulo "1 · procesos"
dato "servicio: $(systemctl is-active atriz-robot 2>/dev/null) · NRestarts=$(systemctl show atriz-robot -p NRestarts --value 2>/dev/null)"
for p in rvr_driver_node ydlidar_ros2_dr collision_monit; do
    if ps -eo comm | grep -qx "$p"; then ok "$p vivo"; else mal "$p NO está"; fi
done
# rosbridge y rosapi se llaman `python3`: hay que mirar la línea de comando.
for n in rosbridge_websocket rosapi_node; do
    if pgrep -f "lib/ros.*/$n" >/dev/null 2>&1 || pgrep -f "$n --ros-args" >/dev/null 2>&1
    then ok "$n vivo"; else avis "$n no encontrado (¿nombre distinto?)"; fi
done

# ── 2. ¿PUBLICA? Esta es la pregunta que parte el diagnóstico en dos ──────────
titulo "2 · ¿llegan datos? (el demonio del CLI se reinicia antes: miente)"
set +u
source /opt/ros/jazzy/setup.bash 2>/dev/null
[[ -f /home/sphero/atriz_ws/install/setup.bash ]] && source /home/sphero/atriz_ws/install/setup.bash 2>/dev/null
[[ -f /etc/profile.d/atriz-robot.sh ]] && source /etc/profile.d/atriz-robot.sh 2>/dev/null
set -u
dato "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-<SIN DEFINIR>}  RMW=${RMW_IMPLEMENTATION:-<por defecto>}"
[[ -z "${ROS_DOMAIN_ID:-}" ]] && mal "sin ROS_DOMAIN_ID: este robot hablaría en el dominio 0"

ros2 daemon stop >/dev/null 2>&1; sleep 2; ros2 daemon start >/dev/null 2>&1; sleep 5

MUDO=0
for t in /odom /imu /estado_robot; do
    R=$(timeout 10 ros2 topic hz "$t" 2>&1 | grep -m1 -oE 'average rate: [0-9.]+')
    if [[ -n "$R" ]]; then ok "$t · $R"; else mal "$t · SIN DATOS en 10 s"; MUDO=$(( MUDO + 1 )); fi
done
# `/battery_state` es TRANSIENT_LOCAL: si alguna vez se publicó, un suscriptor que
# llega tarde recibe el último valor AL INSTANTE. Que no llegue nada es concluyente.
V=$(timeout 10 ros2 topic echo /battery_state --once 2>/dev/null | grep -m1 -oE 'voltage: [0-9.]+')
if [[ -n "$V" ]]; then ok "/battery_state · $V"; else mal "/battery_state · SIN MENSAJE (y es TRANSIENT_LOCAL)"; MUDO=$(( MUDO + 1 )); fi

# ── 3. Según la respuesta, se mira una cosa u otra ───────────────────────────
if (( MUDO > 0 )); then
    titulo "3 · el robot está MUDO — se busca por qué"
    mal "no es problema de la web: aquí, en la propia Pi, tampoco llega nada"

    # (a) ¿el RVR se durmió o se apagó? -> el driver LO DICE
    if journalctl -u atriz-robot -b --no-pager 2>/dev/null | grep -qE 'silencio|reanudado'; then
        avis "el driver avisó de SILENCIO del RVR: mira si el robot está dormido o apagado"
        journalctl -u atriz-robot -b --no-pager 2>/dev/null | grep -E 'silencio|reanudado' | tail -3 | sed 's/^/      /'
    else
        dato "el vigilante de silencio del driver NUNCA saltó → las muestras del RVR llegaban"
        dato "  o sea: el driver recibía datos y lo que no cruzó fue DDS"
    fi

    # (b) el salto de reloj (evidencia 102)
    SALTO=$(journalctl -b --no-pager 2>/dev/null | grep -m1 'jumped backwards\|restored from recorded')
    SYNC=$(journalctl -b --no-pager 2>/dev/null | grep -m1 'Initial clock synchronization')
    if [[ -n "$SALTO" && -n "$SYNC" ]]; then
        mal "EL RELOJ SALTÓ DURANTE EL ARRANQUE (la Pi no tiene RTC):"
        echo "      ${SALTO#*rvr-*: }"; echo "      ${SYNC#*rvr-*: }"
        dato "arranque del servicio: $(systemctl show atriz-robot -p ExecMainStartTimestamp --value)"
        dato "si el servicio arrancó ANTES de la sincronización, nació a caballo del salto"
    fi

    # (c) la red que no estaba
    NET=$(systemctl show network-online.target -p ActiveEnterTimestamp --value)
    ASOC=$(journalctl -b --no-pager -o short-iso 2>/dev/null | grep -m1 'CTRL-EVENT-CONNECTED' | cut -d' ' -f1)
    dato "network-online.target: $NET"
    dato "WiFi asociado:         ${ASOC:-<no visto>}"
    [[ "$(systemctl is-enabled systemd-networkd-wait-online 2>/dev/null)" != enabled ]] && \
        avis "systemd-networkd-wait-online está deshabilitado: network-online.target NO espera a nada"

    echo
    echo "  ${AMAR}REMEDIO${FIN} (👤 lleva sudo):  sudo systemctl restart atriz-robot"
    echo "  Con el reloj ya sincronizado, el stack nace con la hora buena."
else
    titulo "3 · el robot PUBLICA — el problema está en el camino a la web"
    ok "los datos salen del robot: lo que falle está entre rosbridge y el navegador"

    # (a) el enlace WiFi, con números
    if command -v iw >/dev/null; then
        SIG=$(iw dev wlan0 link 2>/dev/null | grep -oE 'signal: -[0-9]+ dBm')
        PS=$(iw dev wlan0 get power_save 2>/dev/null | grep -oE '(on|off)$')
        dato "${SIG:-sin enlace} · power_save: ${PS:-?}"
        [[ "$PS" == on ]] && avis "power_save ENCENDIDO: causa latencias y cortes. fase_1_higiene_so.sh lo apaga"
    fi
    DROP=$(ip -s link show wlan0 2>/dev/null | awk '/RX:/{getline; print $4}')
    dato "paquetes RX descartados: ${DROP:-?}"
    DESC=$(journalctl -b --no-pager 2>/dev/null | grep -c 'CTRL-EVENT-DISCONNECTED')
    if (( DESC > 0 )); then mal "$DESC desconexiones de WiFi en este arranque"; else ok "0 desconexiones de WiFi desde el arranque"; fi

    # (b) los websockets: ¿los cierra la red o el navegador?
    CON=$(journalctl -u atriz-robot -b --no-pager 2>/dev/null | grep -c 'Client connected')
    DIS=$(journalctl -u atriz-robot -b --no-pager 2>/dev/null | grep -c 'Client disconnected')
    dato "rosbridge: $CON conexiones · $DIS cierres · $(ss -tn 2>/dev/null | grep -c ':9090') abiertas ahora"
    # 🔴 La firma que los separa: un corte de RED deja un HUECO entre el cierre y la
    #    reconexión. El navegador cierra y abre en el MISMO segundo.
    MISMO=$(journalctl -u atriz-robot -b --no-pager -o short-iso 2>/dev/null \
            | grep -E 'Client (connected|disconnected)' | cut -d' ' -f1 | uniq -d | wc -l)
    if (( MISMO > 0 )); then
        ok "$MISMO cierres con reconexión en el MISMO segundo → los cierra el NAVEGADOR, no la red"
    elif (( DIS > 0 )); then
        avis "los cierres dejan hueco: podría ser la red. Mira las desconexiones de WiFi de arriba"
    fi

    echo
    echo "  ${AMAR}SIGUIENTE${FIN}: si la web sigue sin ver este robot y aquí todo publica,"
    echo "  sospecha del QoS de rosbridge — el PRIMER cliente que se suscribe a un topic"
    echo "  IMPONE su QoS a todos los demás, y una pestaña que pida RELIABLE sobre un"
    echo "  topic BEST_EFFORT deja MUDAS a las demás. Regla: no mandes campo 'qos'."
fi
echo
