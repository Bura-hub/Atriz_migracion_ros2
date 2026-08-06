#!/usr/bin/env bash
# medir_recuperacion.sh — M6 y M10 del plan del 2026-08-06.
#
# Responde a DOS preguntas que hoy están abiertas y que deciden el diseño:
#
#   M6 · ¿QUÉ PASÓ DE VERDAD el 2026-08-06 al poner el RVR a cargar?
#        Se concluyó «el driver se reinició» por una prueba INDIRECTA (el barrido
#        estaba apagado). Encajan VARIAS explicaciones y el journal las separa.
#
#        🔴🔴 CORREGIDO EL 2026-08-06, Y EL ERROR ERA GRAVE. La primera versión
#        de este guion decía «CADUCA: si se reinicia la Pi, esto se pierde» y
#        usaba dos instrumentos que miran el sitio equivocado:
#
#          · `systemctl show NRestarts` es del ARRANQUE ACTUAL. Con la Pi
#            reiniciada después del suceso vale 0 — y la guía de lectura decía
#            «NRestarts = 0 -> el driver NO se ha reiniciado». Un FALSO NEGATIVO
#            con la firma de siempre: una comprobación que no puede fallar porque
#            mira donde no ocurrió.
#          · `journalctl --since "-6 hours"` MEZCLA arranques sin distinguirlos.
#
#        Y la premisa era falsa: en este robot `/var/log/journal` existe, así que
#        el journal es PERSISTENTE y conserva 5 arranques. `fase_1_higiene_so.sh`
#        lo limita a 32 M pero no lo hace volátil. El dato no se perdía.
#
#        → Ahora se acota POR ARRANQUE (`--list-boots` + `-b <id>`), que es la
#          única forma de responderlo. Lo encontró el usuario revisando el guion.
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
# M6 · ¿Qué pasó de verdad? — acotado POR ARRANQUE (el journal es persistente)
# ─────────────────────────────────────────────────────────────────────────────
echo
echo "── M6 · el journal de atriz-robot, ACOTADO POR ARRANQUE ────────────"
echo
echo "· ¿es el journal persistente? (si no lo fuera, solo habría el arranque actual)"
if [[ -d /var/log/journal ]]; then
  echo "  ✅ /var/log/journal existe -> PERSISTENTE. Hay historial de arranques anteriores."
else
  echo "  🔴 /var/log/journal NO existe -> journal VOLÁTIL: solo el arranque actual."
fi
journalctl --disk-usage 2>/dev/null || true

echo
echo "· los arranques que conserva la Pi:"
# 🔴 ESTO ES LO QUE HACE QUE M6 SE PUEDA RESPONDER. Cada arranque es un mundo
#    aparte: NRestarts se pone a cero, el journal empieza de nuevo, y mezclarlos
#    con `--since` produce una respuesta que no significa nada.
journalctl --list-boots --no-pager 2>/dev/null || echo "  (no disponible)"

echo
echo "· NRestarts del arranque ACTUAL:"
# ⚠️ Y SOLO DEL ACTUAL. Un 0 aquí NO dice que el driver no se haya reiniciado
#    nunca: dice que no lo ha hecho DESDE EL ÚLTIMO ARRANQUE DE LA PI. Si el
#    suceso fue antes, este número no lo puede ver.
systemctl show atriz-robot -p NRestarts -p ActiveEnterTimestamp || true
echo "  la Pi arrancó (este arranque): $(uptime -s 2>/dev/null || echo '?')"

# ── Y ahora, arranque por arranque ──────────────────────────────────────────
echo
echo "· qué pasó en CADA uno de los arranques conservados:"
# Se recorren los ids de `--list-boots` (columna 1: 0, -1, -2, …) y se pregunta
# a cada uno por separado. Es la unica forma de no mezclar.
IDS="$(journalctl --list-boots --no-pager 2>/dev/null | awk '{print $1}' || true)"
if [[ -z "$IDS" ]]; then
  echo "  (no se pudieron listar los arranques)"
else
  for B in $IDS; do
    echo
    echo "  ┌─ arranque $B ────────────────────────────────────────────────"
    echo "  │  desde: $(journalctl -b "$B" --no-pager -o short-iso -n 1 2>/dev/null | head -1 | awk '{print $1}')"
    echo "  │  hasta: $(journalctl -b "$B" --no-pager -o short-iso 2>/dev/null | tail -1 | awk '{print $1}')"

    echo "  │  · eventos de la UNIDAD (arrancó, paró, murió):"
    journalctl -b "$B" -u atriz-robot --no-pager -o short-iso 2>/dev/null \
      | grep -Ei "Started|Stopped|Stopping|Starting|Scheduled restart|Main process exited|Failed|Deactivated" \
      | sed 's/^/  │      /' | tail -15 || true

    echo "  │  · lo que dijo el driver del ENLACE con el RVR:"
    # 🔴 LA DISCRIMINANTE. Si aparecen «streaming reanudado» o «silencio», el
    #    driver SOBREVIVIÓ al apagón del RVR y se recuperó — que es lo que su
    #    código dice que hace. Si no aparecen y sí hay un «Started» nuevo, el
    #    proceso se fue.
    journalctl -b "$B" -u atriz-robot --no-pager -o short-iso 2>/dev/null \
      | grep -Ei "reanudad|silencio|dormid|keepalive" \
      | sed 's/^/  │      /' | tail -10 || true

    echo "  │  · el barrido:"
    journalctl -b "$B" -u atriz-robot --no-pager -o short-iso 2>/dev/null \
      | grep -Ei "escaneo|stop_scan|start_scan" | sed 's/^/  │      /' | tail -8 || true
    echo "  └──"
  done
fi

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
  M6 — busca el arranque cuya ventana CONTENGA la hora en que se cargó el RVR,
       y lee SOLO ese bloque. Los demás no dicen nada del suceso.

    🔴 NRestarts NO sirve para juzgar el pasado: es del arranque ACTUAL. Un 0
       solo dice «no se ha reiniciado desde que la Pi arrancó esta vez».

    Dentro del arranque del suceso, hay CUATRO desenlaces y son distintos:

    (a) un «Started» a la hora de la carga, y NADA de «reanudado»
        -> el proceso del driver se fue y systemd lo repuso.

    (b) «streaming reanudado» / «silencio» y NINGÚN «Started»
        -> el driver SOBREVIVIÓ y se recuperó solo, que es lo que su código
           dice que hace. Entonces el barrido apagado tiene OTRA causa, y hay
           que buscar quién llamó a stop_scan.

    (c) el arranque TERMINA a la hora de la carga y empieza otro
        -> 🔴 NO se reinició el driver: SE REINICIÓ LA PI ENTERA. Es el caso
           que explica de golpe el barrido apagado, la odometría a cero, el
           slam_toolbox muerto (se lo lleva la sesión SSH) y NRestarts = 0.
           La Pi se alimenta del USB del RVR: es una explicación física, no
           una conjetura.

    (d) nada de lo anterior en ningún arranque
        -> el suceso no dejó rastro en esta unidad. Mira `journalctl -b <id>`
           sin `-u` a esa hora.

    Y aparte, en cualquier caso:
    fd con «(deleted)» -> el descriptor del LIDAR murió: es OTRO fallo, con su
                          propio remedio (`systemctl restart atriz-robot`).

  M10, para cada dependencia, mirando la columna `atada`:
    active   -> la unidad atada SOBREVIVIÓ o volvió sola
    inactive -> se paró y NO volvió   🔴 es el caso que deja la navegación muerta
    failed   -> se paró y su Restart intentó volver sin conseguirlo

  🔴 Lo que decide el diseño es el CASO 2 (matar el proceso), no el caso 1:
     el incidente real fue `Restart=always`, no un `systemctl restart`.
LEER

echo
echo "═══ fin · salida guardada en $SALIDA ═══"
