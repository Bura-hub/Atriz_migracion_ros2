#!/bin/bash
# atriz-vigia-dds — ¿cruza DDS? Y si no, UN reinicio y solo uno (evidencia 109).
#
# Lo instala fase_7_systemd.sh en /usr/local/bin junto a vigia_dds.py.
# Lo llama atriz-robot.service como ExecStartPost=- (el guion importa: si esto
# falla, NO tumba la unidad). Corre como sphero, sin privilegios: el reinicio
# es un SIGINT al proceso principal, que es del mismo usuario.
set -euo pipefail

# 🔴 Los setup.bash de ROS no soportan `set -u` (trampa de CLAUDE.md).
set +u
source /opt/ros/jazzy/setup.bash
[[ -f /home/sphero/atriz_ws/install/setup.bash ]] && \
    source /home/sphero/atriz_ws/install/setup.bash

# La IDENTIDAD (ROS_DOMAIN_ID, RMW): la MISMA fuente que atriz-robot.sh.
# 🔴 Sin esta línea el vigía escucha en el dominio 0 con el robot en el 1 y
#    declara MUDO un robot SANO — pasó el 2026-08-14 en el primer arranque
#    armado (evidencia 113): dos falsos positivos y un reinicio de más. La
#    marca de una-sola-vez contuvo el bucle, que es para lo que existe.
#    La trampa estaba documentada en la cabecera de atriz-robot.sh y aun así
#    se repitió: systemd no lee /etc/profile.d.
[[ -f /etc/profile.d/atriz-robot.sh ]] && source /etc/profile.d/atriz-robot.sh
set -u

# Si el vigía no conoce su dominio, no puede fiarse de su propio oído: un
# silencio en el dominio equivocado no es un robot mudo. NO actúa (abierto).
if [[ -z "${ROS_DOMAIN_ID:-}" ]]; then
    echo "[vigia-dds] 🔴 ROS_DOMAIN_ID no definido: mi silencio no sería" \
         "prueba de nada — no actúo (fallo abierto)"
    exit 0
fi

# `-u` obligatorio: bajo systemd, stdout va con búfer de bloque y el mensaje
# «MUDO: SIGINT al PID…» se perdería justo cuando systemd mate a este proceso
# tras el reinicio que él mismo dispara. El journal es la única caja negra.
exec python3 -u /usr/local/bin/vigia_dds.py
