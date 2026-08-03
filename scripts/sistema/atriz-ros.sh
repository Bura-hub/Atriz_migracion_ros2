# /etc/profile.d/atriz-ros.sh — el entorno de ROS 2 de los shells del robot
#
# POR QUÉ ESTÁ AQUÍ Y NO EN ~/.bashrc
#
#   Hasta el 2026-08-03 estas líneas vivían en el ~/.bashrc de rvr-01, y
#   NINGÚN script del repositorio las escribía. Consecuencia medida: un robot
#   montado desde cero siguiendo solo los repositorios tendría shells
#   interactivos SIN `ros2` en el PATH. Lo único versionado era el .bashrc de
#   Noetic (04_respaldo/configs/home_bashrc), que es el respaldo del sistema
#   viejo y debe seguir siéndolo.
#
#   Y de paso desaparece una trampa que el proyecto llevaba documentando en
#   cuatro sitios distintos (fase_7_systemd.sh y verificar_robot.sh, dos veces
#   cada uno): «el ~/.bashrc se lee DESPUÉS de /etc/profile.d y gana». Mientras
#   la identidad del robot estuviera en un fichero y el entorno en otro, había
#   que vigilar que no se pisaran. Con los dos en /etc/profile.d ya no hay nada
#   que vigilar.
#
# 🔴 AQUÍ NO VA NINGUNA IDENTIDAD.
#
#   Ni ROS_DOMAIN_ID, ni ATRIZ_ROBOT_ID, ni el namespace. Eso es distinto en
#   cada uno de los 16 robots y lo genera atriz-first-boot en
#   /etc/profile.d/atriz-robot.sh, leyendo /boot/firmware/robot_id.txt.
#   Si algún día alguien exporta ROS_DOMAIN_ID en este fichero, vuelve el fallo
#   de los 16 robots en el mismo dominio DDS — sin un solo error por ningún lado.
#
#   Este fichero es idéntico en los 16 robots. Ese es justo el criterio para que
#   esté versionado: scripts/sistema/README.md, categoría A.

# Los `setup.bash` de ROS son bash, no sh. /etc/profile.d lo lee cualquier shell
# de login, incluido dash, y ahí `source` no existe: sin esta guarda, un login
# con /bin/sh escupiría un error en cada arranque de sesión.
[ -n "$BASH_VERSION" ] || return 0

[ -f /opt/ros/jazzy/setup.bash ] && . /opt/ros/jazzy/setup.bash

# El workspace del robot, si está compilado. Sin el guarda, un robot recién
# aprovisionado —donde install/ aún no existe— daría un error en cada login.
[ -f "$HOME/atriz_ws/install/setup.bash" ] && . "$HOME/atriz_ws/install/setup.bash"
