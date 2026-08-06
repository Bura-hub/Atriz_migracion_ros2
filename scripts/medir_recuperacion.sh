#!/usr/bin/env bash
# medir_recuperacion.sh — M6 y M10 del plan del 2026-08-06.
#
# Responde a DOS preguntas que hoy están abiertas y que deciden el diseño:
#
#   M6 · ¿QUÉ PASÓ DE VERDAD el 2026-08-06 al poner el RVR a cargar?
#        Se concluyó «el driver se reinició» por una prueba INDIRECTA (el barrido
#        estaba apagado). Encajan TRES explicaciones y el journal las separa.
#        🔴 CADUCA: si se reinicia la Pi, esto se pierde. Va primero.
#
#   M10 · ¿systemd propaga un REINICIO a una unidad atada, o solo el paro?
#        De esto depende si `atriz-nav.service` —que hoy usa `BindsTo=`— se queda
#        muerta tras un reinicio del driver. Y si `atriz-slam.service` puede
#        existir.
#
# ⚠️ NO toca el robot, NO toca el RVR, NO mueve nada. Se puede ejecutar con el
#    driver corriendo y con SLAM corriendo. Lo único que crea son dos unidades de
#    JUGUETE que se borran al terminar.
#
# Uso:   bash ~/atriz_migracion/scripts/medir_recuperacion.sh
#        (pide sudo para las unidades de juguete; el resto no lo necesita)

set -euo pipefail

SALIDA="${1:-$HOME/medicion_recuperacion_$(date +%Y%m%d_%H%M%S).txt}"
exec > >(tee "$SALIDA") 2>&1

echo "═══════════════════════════════════════════════════════════════════"
echo " medir_recuperacion.sh   ·   $(date -Is)   ·   $(hostname)"
echo " salida: $SALIDA"
echo "═══════════════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────────────────────
# M6 · ¿Qué pasó de verdad? — VA PRIMERO PORQUE CADUCA
# ─────────────────────────────────────────────────────────────────────────────
echo
echo "── M6 · el journal de atriz-robot ─────────────────────────────────"
echo
echo "· ¿cuántas veces ha reiniciado el servicio desde que arrancó la Pi?"
# NRestarts es el contador de systemd. Si vale 0, el driver NO se ha reiniciado
# nunca -y entonces la explicación «el driver se reinició» es FALSA.
systemctl show atriz-robot -p NRestarts -p ActiveEnterTimestamp -p ExecMainStartTimestamp || true

echo
echo "· ¿cuándo arrancó la Pi, y cuándo arrancó el servicio?"
uptime -s || true
systemctl show atriz-robot -p ActiveEnterTimestamp --value || true

echo
echo "· arranques y paradas registrados (los 40 últimos eventos):"
# Se buscan las líneas que systemd escribe al arrancar/parar, no las del driver:
# son las que prueban un reinicio de la UNIDAD.
journalctl -u atriz-robot --since "-6 hours" --no-pager -o short-iso \
  | grep -Ei "Started|Stopped|Stopping|Starting|Scheduled restart|Main process exited|Failed|Deactivated" \
  | tail -40 || echo "  (sin coincidencias)"

echo
echo "· ¿alguien pidió parar el barrido, o lo apagó el arranque?"
# El ExecStartPost de la unidad ejecuta `atriz-escaneo off` en CADA arranque. Si
# aparece junto a un «Started», el barrido se apagó por el arranque -no porque
# nadie lo pidiera.
journalctl -u atriz-robot --since "-6 hours" --no-pager -o short-iso \
  | grep -Ei "escaneo|stop_scan|start_scan" | tail -20 || echo "  (sin coincidencias)"

echo
echo "· ¿qué dijo el driver sobre el enlace con el RVR?"
# 🔴 LA DISCRIMINANTE. Si aparecen «streaming reanudado» / «silencio», el driver
#    SOBREVIVIÓ y se recuperó -o sea que NO se reinició, y el barrido apagado
#    tiene otra causa. Si no aparecen y sí hay «Started», se reinició.
journalctl -u atriz-robot --since "-6 hours" --no-pager -o short-iso \
  | grep -Ei "reanudad|silencio|dormid|keepalive|RVR" | tail -25 || echo "  (sin coincidencias)"

echo
echo "· el descriptor del LIDAR, ahora mismo:"
# Si dice «(deleted)», es el fallo del USB re-enumerado -otra causa distinta.
PID_LIDAR="$(pgrep -f '[y]dlidar_ros2_dr' || true)"
if [[ -n "$PID_LIDAR" ]]; then
  ls -l "/proc/$PID_LIDAR/fd" 2>/dev/null | grep tty || echo "  (sin descriptor tty abierto)"
else
  echo "  🔴 el nodo del LIDAR NO está corriendo"
fi

# ─────────────────────────────────────────────────────────────────────────────
# M10 · systemd: ¿se propaga el REINICIO, o solo el paro?
# ─────────────────────────────────────────────────────────────────────────────
echo
echo "── M10 · propagación de systemd, con unidades de JUGUETE ───────────"
echo
echo "  Dos unidades que no hacen nada (sleep infinity). Se prueban los DOS"
echo "  caminos, porque no son el mismo:"
echo "    caso 1 · systemctl restart  -> un job EXPLÍCITO del operador"
echo "    caso 2 · matar el proceso   -> lo que pasó de verdad (Restart=always)"
echo

crear_unidades() {
  local dep="$1"   # BindsTo / PartOf / ambas
  sudo tee /etc/systemd/system/juguete-base.service >/dev/null <<'UNIDAD'
[Unit]
Description=juguete base (imita atriz-robot)
[Service]
ExecStart=/bin/sleep infinity
Restart=always
RestartSec=1
UNIDAD

  {
    echo "[Unit]"
    echo "Description=juguete atada (imita atriz-slam / atriz-nav)"
    case "$dep" in
      bindsto) echo "BindsTo=juguete-base.service" ;;
      partof)  echo "PartOf=juguete-base.service"; echo "Requires=juguete-base.service" ;;
      ambas)   echo "BindsTo=juguete-base.service"; echo "PartOf=juguete-base.service" ;;
    esac
    echo "After=juguete-base.service"
    echo "[Service]"
    echo "ExecStart=/bin/sleep infinity"
    echo "Restart=on-failure"
  } | sudo tee /etc/systemd/system/juguete-atada.service >/dev/null

  sudo systemctl daemon-reload
}

probar() {
  local dep="$1"
  echo "  ┌── dependencia: $dep"
  crear_unidades "$dep"
  sudo systemctl start juguete-base.service juguete-atada.service
  sleep 2
  echo "  │  estado inicial:  base=$(systemctl is-active juguete-base) atada=$(systemctl is-active juguete-atada)"

  # ── caso 1: restart explícito ──────────────────────────────────────────────
  sudo systemctl restart juguete-base.service
  sleep 4
  echo "  │  tras 'systemctl restart base':   atada=$(systemctl is-active juguete-atada)"

  # Volver a dejarlas arriba para el segundo caso.
  sudo systemctl start juguete-atada.service 2>/dev/null || true
  sleep 2

  # ── caso 2: MATAR el proceso, que es lo que pasó de verdad ─────────────────
  # 🔴 No es lo mismo que el restart: aquí systemd reacciona por `Restart=always`,
  #    no por un job que alguien pidió. El incidente del 2026-08-06 fue este.
  local pid
  pid="$(systemctl show juguete-base -p MainPID --value)"
  if [[ "$pid" != "0" ]]; then sudo kill -9 "$pid"; fi
  sleep 5
  echo "  │  tras MATAR el proceso de base:   atada=$(systemctl is-active juguete-atada)"
  echo "  └──"

  sudo systemctl stop juguete-atada.service juguete-base.service 2>/dev/null || true
}

for dep in bindsto partof ambas; do
  probar "$dep"
done

echo
echo "  limpiando las unidades de juguete…"
sudo systemctl stop juguete-atada.service juguete-base.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/juguete-base.service /etc/systemd/system/juguete-atada.service
sudo systemctl daemon-reload
echo "  hecho."

# ─────────────────────────────────────────────────────────────────────────────
echo
echo "── cómo se lee esto ───────────────────────────────────────────────"
cat <<'LEER'
  M6:
    NRestarts = 0            -> el driver NO se ha reiniciado. «El driver se
                                reinició» es FALSO, y el barrido apagado tiene
                                otra causa (busca quién llamó a stop_scan).
    NRestarts > 0 + «Started» -> se reinició. Mira la hora contra la de la carga.
    Hay «streaming reanudado» -> el driver SOBREVIVIÓ al apagón del RVR y se
                                recuperó: eso es lo que dice el código que hace.
    fd con «(deleted)»        -> el descriptor del LIDAR murió: es OTRO fallo.

  M10, para cada dependencia, mirando la columna `atada`:
    active   -> la unidad atada SOBREVIVIÓ o volvió sola
    inactive -> se paró y NO volvió   🔴 es el caso que deja la navegación muerta
    failed   -> se paró y su Restart intentó volver sin conseguirlo

  🔴 Lo que decide el diseño es el CASO 2 (matar el proceso), no el caso 1:
     el incidente real fue `Restart=always`, no un `systemctl restart`.
LEER

echo
echo "═══ fin · salida guardada en $SALIDA ═══"
