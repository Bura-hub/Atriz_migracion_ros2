#!/usr/bin/env bash
# medir_arranque_nav.sh — B2 y B3: la navegación bajo systemd, por primera vez.
#
# ═══════════════════════════════════════════════════════════════════════════════
# POR QUÉ EXISTE
# ═══════════════════════════════════════════════════════════════════════════════
# `atriz-nav.service` se escribió el 2026-08-03 y **NUNCA SE HA EJECUTADO BAJO
# SYSTEMD**. Se está diseñando encima de él —y extendiéndolo a SLAM— un mecanismo
# que no se ha visto correr ni una sola vez con carga real.
#
#   B2 · ¿arranca de verdad? ¿y CUÁNTO TARDA hasta aceptar objetivos?
#        Ese número no lo tiene nadie. `TimeoutStartSec=120` es un tope que
#        alguien escribió, no una medida. De él dependen tres cosas:
#          · el plazo del estado «arrancando» que la web tiene que pintar
#          · si el apagado por inactividad compensa
#          · si `TimeoutStartSec` está bien puesto o es humo
#
#   B3 · sin mapa, ¿corta el `StartLimitBurst` o el botón se queda muerto?
#        `Restart=on-failure` + `StartLimitBurst=3`/300 s: **un solo
#        `systemctl start` produce tres intentos** y puede dejar la unidad
#        latcheada. Recuperarla pide `reset-failed`, o sea privilegio — que
#        nadie tiene desde el navegador. Desde la web, «no arrancó» y «bloqueado
#        hasta que alguien entre por SSH» son INDISTINGUIBLES.
#
# ═══════════════════════════════════════════════════════════════════════════════
# ⚠️ ACCIONES FÍSICAS — LÉELO ANTES DE LANZARLO
# ═══════════════════════════════════════════════════════════════════════════════
#   · ENCIENDE EL BARRIDO del LIDAR: el X2 sube de 2,7 a 11,8 Hz mientras dure.
#   · Nav2 son ~58 % de un núcleo, y la Pi se alimenta de la BATERÍA DEL RVR.
#   · NO MUEVE EL ROBOT: no se envía ningún objetivo en ningún momento.
#   · Al terminar deja el sistema como estaba: nav parada, barrido apagado,
#     `reset-failed` hecho y el drop-in borrado. Incluso si falla a mitad.
#
# Uso:   sudo bash ~/atriz_migracion/scripts/medir_arranque_nav.sh
#        sudo bash ~/atriz_migracion/scripts/medir_arranque_nav.sh /ruta/mapa.yaml

set -uo pipefail          # 🔴 SIN -e a propósito: aquí un fallo ES un resultado.

MAPA="${1:-/home/sphero/mapas/cuarto.yaml}"
SALIDA="$HOME/medicion_arranque_nav_$(date +%Y%m%d_%H%M%S).txt"
DROPIN_DIR=/etc/systemd/system/atriz-nav.service.d
DROPIN="$DROPIN_DIR/99-medicion.conf"

exec > >(tee "$SALIDA") 2>&1

echo "═══════════════════════════════════════════════════════════════════"
echo " medir_arranque_nav.sh   ·   $(date -Is)   ·   $(hostname)"
echo " mapa: $MAPA"
echo "═══════════════════════════════════════════════════════════════════"

# ── Limpieza, pase lo que pase ───────────────────────────────────────────────
limpiar() {
  echo
  echo "── dejando el sistema como estaba ─────────────────────────────────"
  systemctl stop atriz-nav.service 2>/dev/null || true
  systemctl reset-failed atriz-nav.service 2>/dev/null || true
  rm -f "$DROPIN"; rmdir "$DROPIN_DIR" 2>/dev/null || true
  systemctl daemon-reload
  # El barrido: la unidad lo apaga en su ExecStopPost, pero no se da por hecho.
  su - sphero -c '/usr/local/bin/atriz-escaneo off' >/dev/null 2>&1 || true
  echo "  atriz-nav:  $(systemctl is-active atriz-nav 2>/dev/null) / $(systemctl is-failed atriz-nav 2>/dev/null)"
  echo "  atriz-robot:$(systemctl is-active atriz-robot 2>/dev/null)"
  echo "  drop-in borrado, reset-failed hecho."
}
trap limpiar EXIT

poner_mapa() {   # $1 = ruta que verá la unidad
  mkdir -p "$DROPIN_DIR"
  printf '[Service]\nEnvironment=ATRIZ_MAPA=%s\n' "$1" > "$DROPIN"
  systemctl daemon-reload
}

# ═══════════════════════════════════════════════════════════════════════════════
echo
echo "── 0 · antes de tocar nada ────────────────────────────────────────"
echo "  atriz-robot:        $(systemctl is-active atriz-robot)"
echo "  atriz-nav:          $(systemctl is-active atriz-nav) / $(systemctl is-failed atriz-nav)"
echo "  slam_toolbox vivo:  $(ps -eo comm | grep -cx async_slam_tool)"
echo "  barrido:            $(su - sphero -c '/usr/local/bin/atriz-escaneo estado' 2>/dev/null | tail -1)"
echo "  mapa legible:       $([[ -r "$MAPA" ]] && echo 'sí' || echo '🔴 NO')"

if [[ "$(systemctl is-active atriz-robot)" != "active" ]]; then
  echo "  🔴 el driver no está activo. Sin él esto no mide nada. Abortando."
  exit 1
fi
if [[ ! -r "$MAPA" ]]; then
  echo "  🔴 sin mapa legible no se puede medir B2. Pásalo como argumento."
  exit 1
fi
# 🔴 Y que la IMAGEN que referencia exista. Un .yaml presente con su .pgm
#    ausente hace fallar a `map_server` por un motivo distinto del que se está
#    midiendo, y B2 saldría «no arrancó» culpando a la unidad. `image:` suele
#    ser relativo AL DIRECTORIO DEL YAML, no al directorio de trabajo.
IMG="$(grep -oP '^image:\s*\K\S+' "$MAPA" 2>/dev/null)"
[[ "$IMG" = /* ]] || IMG="$(dirname "$MAPA")/$IMG"
if [[ ! -r "$IMG" ]]; then
  echo "  🔴 el mapa referencia una imagen que no se puede leer: $IMG"
  echo "     Abortando: mediría el fallo equivocado."
  exit 1
fi
echo "  imagen del mapa:    $IMG ($(stat -c%s "$IMG" 2>/dev/null) bytes)"
if [[ "$(ps -eo comm | grep -cx async_slam_tool)" != "0" ]]; then
  echo "  🔴 hay un slam_toolbox corriendo: AMCL y SLAM son excluyentes."
  echo "     Párale primero. Abortando."
  exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
# B2 · ¿arranca, y cuánto tarda hasta ACEPTAR OBJETIVOS?
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo "── B2 · arranque real, cronometrado ───────────────────────────────"
echo "  ⚠️ ENCIENDE EL BARRIDO (11,8 Hz) y ~58 % de un núcleo. NO mueve el robot."
poner_mapa "$MAPA"

T0=$(date +%s.%N)
systemctl start atriz-nav.service &          # --no-block equivalente: no esperar
PID_START=$!

# 🔴 EL TESTIGO NO ES `is-active`, y esa es la razón de ser de esta medición:
#    la unidad puede estar `active` con Nav2 todavía sin poder aceptar nada.
#    Se espera al EFECTO: que el servidor de acción de /navigate_to_pose esté
#    listo. Se usa un CLIENTE, no `ros2 action list` — el descubrimiento DDS no
#    es autoritativo (omitió 1 de 18 servicios el 2026-08-01).
cat > /tmp/cronometro_nav.py <<'PYFIN'
import time, rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose

CICLO = ['controller_server', 'planner_server', 'behavior_server',
         'bt_navigator', 'smoother_server', 'map_server', 'amcl']

rclpy.init()
n = Node('cronometro_nav')
cli = ActionClient(n, NavigateToPose, 'navigate_to_pose')
t0 = time.monotonic()
hitos = {}
listo = None
while time.monotonic() - t0 < 170:
    rclpy.spin_once(n, timeout_sec=0.0)
    t = time.monotonic() - t0
    vistos = [x for x, _ in n.get_node_names_and_namespaces()]
    for c in CICLO:
        if c not in hitos and c in vistos:
            hitos[c] = t
            print('    %6.1fs  aparece el nodo %s' % (t, c))
    if listo is None and cli.server_is_ready():
        listo = t
        print('    %6.1fs  /navigate_to_pose ACEPTA OBJETIVOS' % t)
        break
    time.sleep(0.2)
print()
if listo is None:
    print('    NO llego a aceptar objetivos en %.0f s.' % (time.monotonic() - t0))
    print('    Nodos que si aparecieron: %s' % (', '.join(hitos) or 'ninguno'))
else:
    cabe = 'cabe' if listo < 120 else 'NO CABE'
    print('    LISTO EN %.1f s desde el systemctl start' % listo)
    print('    (TimeoutStartSec=120 en la unidad: %s)' % cabe)
n.destroy_node(); rclpy.shutdown()
PYFIN
chmod 644 /tmp/cronometro_nav.py

# 🔴 El Python va en un FICHERO, no incrustado en el `-c` de `su`. Anidar
#    comillas dentro de comillas ya rompio este guion una vez: las comillas
#    escapadas de una f-string se las comia el shell antes de que Python las
#    viera. Un fichero no tiene ese problema y ademas se puede probar suelto.
su - sphero -c "source /opt/ros/jazzy/setup.bash; \
                source /home/sphero/atriz_ws/install/setup.bash; \
                timeout 180 python3 -u /tmp/cronometro_nav.py"
wait "$PID_START" 2>/dev/null
T1=$(date +%s.%N)
echo
echo "  systemctl start devolvió en $(echo "$T1 - $T0" | bc) s (eso NO es el arranque)"
echo "  estado de la unidad:  $(systemctl is-active atriz-nav) / $(systemctl show atriz-nav -p Result --value)"
echo "  barrido tras arrancar: $(su - sphero -c '/usr/local/bin/atriz-escaneo estado' 2>/dev/null | tail -1)"

echo
echo "  ── al parar: ¿qué pasa con el barrido? (conflicto 2 de ARRANQUE_NAVEGACION) ──"
systemctl stop atriz-nav.service
sleep 3
echo "  barrido tras parar:    $(su - sphero -c '/usr/local/bin/atriz-escaneo estado' 2>/dev/null | tail -1)"
echo "  🔴 si dice APAGADO, parar la navegación deja ciego a cualquier otro"
echo "     consumidor de /scan — y con el botón en la web eso lo hace un alumno."

# ═══════════════════════════════════════════════════════════════════════════════
# B3 · sin mapa: ¿corta el StartLimitBurst, o el botón se queda muerto?
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo "── B3 · sin mapa: el botón de tres pulsaciones ────────────────────"
systemctl reset-failed atriz-nav.service 2>/dev/null || true
poner_mapa "/ruta/que/no/existe/mapa.yaml"

echo "  primer 'systemctl start' (uno solo):"
systemctl start atriz-nav.service 2>&1 | sed 's/^/    /'
echo "    código de salida: $?"
echo "  observando 45 s los reintentos…"
sleep 45
echo "    estado:      $(systemctl is-active atriz-nav) / $(systemctl show atriz-nav -p Result --value)"
echo "    NRestarts:   $(systemctl show atriz-nav -p NRestarts --value)"
echo
echo "  segundo 'systemctl start' — ¿lo deja, o dice 'repeated too quickly'?"
systemctl start atriz-nav.service 2>&1 | sed 's/^/    /'
echo "    código de salida: $?"
echo "    estado:      $(systemctl is-active atriz-nav) / $(systemctl show atriz-nav -p Result --value)"
echo
echo "  lo que dijo el journal:"
journalctl -u atriz-nav --since "-2 min" --no-pager 2>/dev/null \
  | grep -Ei "no hay mapa|repeated too quickly|Failed|start request|Scheduled restart" \
  | tail -8 | sed 's/^/    /'

echo
echo "── cómo se lee ────────────────────────────────────────────────────"
cat <<'LEER'
  B2 · el número que importa NO es lo que tarda `systemctl start` en devolver
       —eso es encolar un job— sino los segundos hasta «ACEPTA OBJETIVOS».
       Ese es el plazo real del estado «arrancando» que la web debe pintar.

       Si supera 120 s, `TimeoutStartSec=120` está mal puesto y la unidad se
       mataría a sí misma a mitad de arrancar.

  B3 · tres desenlaces, y son distintos:

       Result=exit-code + NRestarts=3 + el segundo start dice
       «Start request repeated too quickly»
          -> 🔴 CONFIRMADO: un solo clic quema el presupuesto y el botón queda
             muerto hasta que alguien entre por SSH. El servicio ROS TIENE que
             negarse ANTES de llamar a systemctl si no hay mapa.

       Result=exit-code + NRestarts=0
          -> `Restart=on-failure` no reintentó. El latch no existe y B3 se cae.

       el segundo start arranca normal
          -> el StartLimit no llegó a agotarse en esta ventana. Repetir con
             más pulsaciones antes de concluir.

  ⚠️ Y en los tres casos, mira el barrido tras parar la navegación (arriba).
     Es una decisión pendiente, no un dato de color.
LEER
echo
echo "═══ fin · salida en $SALIDA ═══"
