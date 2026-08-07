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
# 🔴 SE MIDE DOS VECES. Una sola vuelta no distingue "asi es" de "asi salio esa
#    vez": si los dos numeros se parecen, el arranque es reproducible y la web
#    puede fiarse del plazo; si no, hay que averiguar de que depende antes de
#    pintar nada. Es la misma correccion que la evidencia 78 (n=1 -> n=3).
medir_b2() {
  echo
  echo "  ┌── vuelta $1 ─────────────────────────────────────────────────"
  poner_mapa "$MAPA"

  rm -f /tmp/cronometro_listo /tmp/cronometro_salida.txt
  # 🔴 EL OBSERVADOR VA PRIMERO. Se espera a su marca antes de tocar systemd: asi
  #    el instante cero es el `systemctl start` de verdad, y no el arranque de
  #    Python. Esto es lo que convierte "entre 18 y 26 s" en un numero exacto.
  su - sphero -c "source /opt/ros/jazzy/setup.bash; \
                  source /home/sphero/atriz_ws/install/setup.bash; \
                  timeout 210 python3 -u /tmp/cronometro_nav.py" \
      > /tmp/cronometro_salida.txt 2>&1 &
  PID_CRONO=$!
  for _ in $(seq 1 60); do [[ -f /tmp/cronometro_listo ]] && break; sleep 1; done
  if [[ ! -f /tmp/cronometro_listo ]]; then
    echo "  🔴 el observador no llegó a ponerse en pie. Esta vuelta no mide nada."
  fi

  T0=$(date +%s.%N)
  # --no-block: encola el job y vuelve. Es lo que hara el servicio ROS, asi que se
  # mide lo que se va a usar, no otra cosa.
  systemctl start --no-block atriz-nav.service
  T_NOBLOCK=$(date +%s.%N)
  echo "  systemctl start --no-block devolvió en $(echo "$T_NOBLOCK - $T0" | bc) s"

  wait "$PID_CRONO" 2>/dev/null
  grep -E "observador|EPOCH_NODO|NO llego" /tmp/cronometro_salida.txt | sed 's/^/  /'
  EP=$(grep -oP 'EPOCH_LISTO \K[0-9.]+' /tmp/cronometro_salida.txt | tail -1)
  if [[ -n "$EP" && "$EP" != "0" ]]; then
    echo "  🎯 ACEPTA OBJETIVOS a los $(echo "$EP - $T0" | bc) s del systemctl start"
  else
    echo "  🔴 NO llegó a aceptar objetivos"
  fi
  echo "  estado de la unidad:  $(systemctl is-active atriz-nav) / $(systemctl show atriz-nav -p Result --value)"
  echo "  barrido tras arrancar: $(su - sphero -c '/usr/local/bin/atriz-escaneo estado' 2>/dev/null | tail -1)"

  echo
  echo "  ── al parar: ¿qué pasa con el barrido? (conflicto 2 de ARRANQUE_NAVEGACION) ──"
  systemctl stop atriz-nav.service
  sleep 3
  echo "  barrido tras parar:    $(su - sphero -c '/usr/local/bin/atriz-escaneo estado' 2>/dev/null | tail -1)"
  echo "  🔴 si dice APAGADO, parar la navegación deja ciego a cualquier otro"
  echo "     consumidor de /scan — y con el botón en la web eso lo hace un alumno."
  echo "  └──"
  # Entre vueltas se deja el sistema en reposo, o la segunda arrancaria sobre
  # los restos de la primera y mediria otra cosa.
  systemctl stop atriz-nav.service 2>/dev/null || true
  systemctl reset-failed atriz-nav.service 2>/dev/null || true
  sleep 5
}

for V in 1 2; do medir_b2 "$V"; done

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
