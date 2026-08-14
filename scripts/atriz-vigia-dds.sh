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
set -u

# `-u` obligatorio: bajo systemd, stdout va con búfer de bloque y el mensaje
# «MUDO: SIGINT al PID…» se perdería justo cuando systemd mate a este proceso
# tras el reinicio que él mismo dispara. El journal es la única caja negra.
exec python3 -u /usr/local/bin/vigia_dds.py
