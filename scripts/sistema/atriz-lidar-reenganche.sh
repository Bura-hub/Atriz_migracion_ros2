#!/bin/bash
# atriz-lidar-reenganche — reinicia atriz-robot cuando el LIDAR re-enumera y el
# nodo se quedó con el descriptor muerto.
#
# POR QUÉ EXISTE (evidencia 69 §6, decisión A del usuario 2026-08-14):
#   Apagar y encender el RVR con la Pi viva —cotidiano: ponerlo a cargar—
#   re-enumera el adaptador USB del X2. La regla udev rehace /dev/ydlidar,
#   pero el nodo abre el puerto UNA vez al arrancar y se queda agarrado a
#   `/dev/ttyUSB0 (deleted)`: /start_scan devuelve false, /scan a 0, y el
#   robot «no obedece» con systemctl en verde. Hasta hoy solo lo arreglaba un
#   humano por SSH.
#
# CÓMO LLEGA AQUÍ: 98-atriz-lidar-reenganche.rules (udev) dispara esta unidad
# oneshot CADA vez que el adaptador aparece — incluido el arranque normal, por
# eso los guardias de abajo importan tanto como el reinicio.
#
# LOS GUARDIAS, en orden — todos fallan ABIERTO (no tocar nada):
#   1. atriz-robot no está activa      → arranque normal o robot parado: nada.
#   2. el nodo del lidar no corre      → la unidad está arrancando: su propio
#                                        envoltorio espera a /dev/ydlidar.
#   3. el nodo no tiene fd de tty      → aún no abrió el puerto: nada.
#   4. el fd apunta a un tty VIVO      → sano: nada. (El discriminante es el
#                                        «(deleted)» — el diagnóstico
#                                        documentado en CLAUDE.md.)
#   5. anti-aleteo: reenganche hace <120 s → nada. Un cable malo re-enumerando
#      en bucle quemaría el StartLimitBurst de atriz-robot (5/300 s) y
#      convertiría un lidar flojo en un robot MUERTO.
set -euo pipefail

MARCA=/run/atriz-lidar-reenganche.ultima

log() { echo "[lidar-reenganche] $*"; }

if [[ "$(systemctl is-active atriz-robot 2>/dev/null || true)" != "active" ]]; then
    log "atriz-robot no está activa: nada que reenganchar"; exit 0
fi

PID="$(pgrep -x ydlidar_ros2_dr || true)"
if [[ -z "$PID" ]]; then
    log "el nodo del lidar no corre (¿unidad arrancando?): no toco nada"; exit 0
fi

# El fd del puerto serie del nodo, si ya lo abrió.
FD_TTY="$(ls -l "/proc/$PID/fd" 2>/dev/null | grep -F tty || true)"
if [[ -z "$FD_TTY" ]]; then
    log "el nodo aún no abrió ningún tty: no toco nada"; exit 0
fi
if ! grep -qF '(deleted)' <<< "$FD_TTY"; then
    log "el descriptor del lidar está VIVO: sano, no toco nada"; exit 0
fi

if [[ -f "$MARCA" ]]; then
    EDAD=$(( $(date +%s) - $(stat -c %Y "$MARCA") ))
    if (( EDAD < 120 )); then
        log "🔴 descriptor muerto PERO ya reenganché hace ${EDAD}s (<120):"
        log "   no reinicio otra vez — un USB aleteando no debe quemar el"
        log "   StartLimitBurst de atriz-robot. Si persiste: revisa el cable."
        exit 0
    fi
fi

touch "$MARCA"
log "🔴 el nodo del lidar tiene el descriptor MUERTO ((deleted)) y el"
log "   adaptador acaba de reaparecer: reiniciando atriz-robot (evidencia 115)."
systemctl restart atriz-robot --no-block
