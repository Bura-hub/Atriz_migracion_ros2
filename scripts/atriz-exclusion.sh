#!/usr/bin/env bash
# atriz-exclusion — se niega si ya hay alguien publicando `map → odom`.
#
#     atriz-exclusion slam    # ¿puede arrancar SLAM?
#     atriz-exclusion nav     # ¿puede arrancar la navegación?
#
# Va como `ExecStartPre` de `atriz-slam.service` y `atriz-nav.service`, SIN el
# guion delante: si no se puede garantizar la exclusión, la unidad NO arranca.
#
# ═══════════════════════════════════════════════════════════════════════════════
# POR QUÉ EXISTE, SI YA HAY UN GUARDIA EN LOS LAUNCH
# ═══════════════════════════════════════════════════════════════════════════════
# `localizacion.launch.py` y `slam.launch.py` ya se niegan (el segundo desde el
# 2026-08-07). Pero lo hacen TARDE y CARO: el `ExecStartPre=atriz-escaneo on` ya
# ha subido el X2 a 11,8 Hz y el launch ya lleva segundos levantando nodos.
#
# Aquí falla en ~0,1 s, antes de tocar el LIDAR, y el mensaje queda en el journal
# DE LA UNIDAD — que es donde mira `supervisor_navegacion` para poner el
# `*_detalle` que la web enseña al alumno.
#
# 📌 Y NO se usa `Conflicts=` de systemd, que sería lo obvio: pararía al otro
#    **sin decir una palabra**, y quien llevara veinte minutos mapeando perdería
#    el mapa sin enterarse. Cambiar un fallo ruidoso por uno silencioso va en la
#    dirección contraria a la de este proyecto.
#
# ⚠️ LO QUE ESTO NO PUEDE HACER, y está dicho para que nadie lo suponga:
#    · **No cierra la carrera.** Mira `ps` en un instante; dos peticiones
#      simultáneas pueden ver las dos el sistema limpio. Eso pide un cerrojo en
#      el supervisor, no aquí.
#    · **`ps` ve el proceso, no si funciona.** Un `slam_toolbox` en
#      `unconfigured` bloquearía la navegación sin estar haciendo nada. Es el
#      sesgo seguro: prefiere negarse de más a partir el árbol TF.

set -uo pipefail

#: `comm` de los procesos, TRUNCADO A 15 CARACTERES por el kernel, que es lo que
#: devuelve `ps`. `async_slam_toolbox_node` sale como `async_slam_tool`.
#: Verificado el 2026-08-06 copiando `/bin/sleep` con ese nombre.
COMM_SLAM=async_slam_tool
COMM_AMCL=amcl

log() { echo "[atriz-exclusion] $*"; }

# 🔴 Por `comm` con `ps`, NUNCA con `pgrep -f`: el patrón de `-f` casa con la
#    propia línea de comando de quien lo ejecuta, y en este proyecto eso ya ha
#    matado la terminal dos veces.
vivo() { ps -eo comm | grep -qx "$1"; }

case "${1:-}" in
  slam)
    if vivo "$COMM_AMCL"; then
      log "🔴 AMCL ESTÁ CORRIENDO. SLAM no arranca."
      log ""
      log "   AMCL y slam_toolbox publican los dos 'map -> odom'. Juntos parten"
      log "   el árbol TF SIN DAR NINGÚN ERROR y la pose salta entre las dos"
      log "   estimaciones. Es el fallo que costó la Fase 4."
      log ""
      log "   Para la navegación primero:   systemctl stop atriz-nav"
      log "   (o desde la web: /pedir_nav con data:false)"
      exit 1
    fi
    if vivo "$COMM_SLAM"; then
      log "🔴 YA HAY UN slam_toolbox CORRIENDO. No se arranca un segundo."
      log "   Si el que corre es el que quieres, ya está mapeando."
      exit 1
    fi
    ;;
  nav)
    if vivo "$COMM_SLAM"; then
      log "🔴 slam_toolbox ESTÁ CORRIENDO. La navegación no arranca."
      log ""
      log "   Son excluyentes: mapear y navegar sobre un mapa guardado no se"
      log "   hacen a la vez."
      log ""
      log "   Para SLAM primero:   systemctl stop atriz-slam"
      log "   (o desde la web: /pedir_slam con data:false)"
      log "   ⚠️ Si llevas rato mapeando, GUARDA EL MAPA antes de pararlo."
      exit 1
    fi
    # 🆕 2026-08-11 · Y EL INFRARROJO, que hasta hoy no vigilaba nadie.
    #
    # 🔴 `set_ir_mode('following')` y `set_ir_evading` hacen conducir al robot
    #    por FIRMWARE: no pasan por `/cmd_vel`. Así que si se arranca Nav2 con
    #    uno de esos activo, quedan DOS CONTROLADORES mandando sobre el mismo
    #    robot — Nav2 publicando velocidades y el firmware conduciendo por su
    #    cuenta— y nada los arbitra. El SDK tampoco: se buscó el 2026-08-11 y no
    #    hay ni una línea sobre precedencia.
    #
    # 📝 Se mira `/estado_ir`, que el driver publica a 1 Hz. Si no llega (driver
    #    parado, o `ir_sondeo_hz:=0`), NO se bloquea: no se puede afirmar que
    #    haya IR activo, y negar el arranque por no poder mirar sería peor que
    #    el problema. Se avisa y se sigue — la regla del proyecto es no fingir
    #    que se ha comprobado algo.
    EST_IR="$(timeout 4 ros2 topic echo /estado_ir --once 2>/dev/null || true)"
    if [[ -z "$EST_IR" ]]; then
      log "⚠️ no se pudo leer /estado_ir: NO se comprueba el infrarrojo."
      log "   (driver parado, o arrancado con ir_sondeo_hz:=0)"
    elif grep -q 'conduciendo_por_ir: true' <<<"$EST_IR"; then
      log "🔴 EL ROBOT ESTÁ CONDUCIENDO POR INFRARROJOS. La navegación no arranca."
      log ""
      log '   following y evading son modos del FIRMWARE: el robot se mueve'
      log '   SIN pasar por /cmd_vel, asi que ni el watchdog ni el'
      log '   collision_monitor los ven. Arrancar Nav2 encima dejaria DOS'
      log '   controladores mandando sobre el mismo robot, sin nadie que arbitre.'
      log ""
      log '   Apagalo primero:'
      log "     ros2 service call /set_ir_mode atriz_rvr_msgs/srv/SetIRMode \"{mode: 'off', far_code: 0, near_code: 0}\""
      log '   Desde una practica:  robot.parar_ir()'
      exit 1
    fi
    ;;
  *)
    log "uso: atriz-exclusion slam|nav"
    exit 2
    ;;
esac

log "vía libre para $1"
exit 0
