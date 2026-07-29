# Manual Atriz — ROS 2 Jazzy

> **NO ESCRITO TODAVÍA.** Sustituto del `MANUAL SPHERO.docx`. Se redacta de forma
> incremental durante las **fases 1–5** del plan, documentando únicamente pasos ya
> ejecutados y verificados.

Cubrirá la instalación completa desde una microSD en blanco hasta un robot navegando:

1. Flasheo de Ubuntu Server 24.04 LTS arm64 y ajustes del Raspberry Pi Imager
2. `cmdline.txt` — retirar `console=serial0,115200`
3. `config.txt` — `dtoverlay=disable-bt` y `enable_uart=1`
4. Reglas udev: `/dev/rvr` y `/dev/ydlidar`
5. Higiene del SO: headless, governor, journal, WiFi power-save, longevidad de SD
6. ROS 2 Jazzy (`ros-base`) y workspace colcon
7. Driver del RVR en `rclpy`
8. URDF y `robot_state_publisher`
9. YDLIDAR X2: `YDLidar-SDK` + `ydlidar_ros2_driver`
10. SLAM (`slam_toolbox`) y navegación (Nav2)
11. `rosbridge_server` y conexión con la plataforma web
12. Arranque automático con systemd

Hasta que exista, el procedimiento válido es el
[manual original anotado](MANUAL_SPHERO_transcripcion.md), que documenta el sistema
Noetic actual e incluye las correcciones detectadas en la auditoría.
