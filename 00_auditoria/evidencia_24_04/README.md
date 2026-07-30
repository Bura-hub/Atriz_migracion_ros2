# Evidencia — Ubuntu Server 24.04 (el sistema NUEVO)

Salidas **crudas** de la instalación de 2026-07-30. Sirven para dos cosas:

1. **Reproducir la instalación desde cero** sabiendo qué salió de verdad en cada paso, no
   solo qué se esperaba. Si un robot nuevo de la flota da otro resultado, aquí está contra
   qué comparar.
2. **Comparar antes/después** de cada cambio, en vez de afirmar mejoras de memoria.

> ⚠️ **No confundir con [`../evidencia/`](../evidencia/)**, que es la línea base del sistema
> **viejo** (Ubuntu 20.04 + ROS Noetic). Son dos sistemas distintos y mezclar sus números es
> lo que produce deriva entre documentación y realidad. Cuando el manual pide «comparar con
> la línea base», la línea base de 24.04 es **esta** carpeta.

## Ficheros

Los ficheros van **numerados en orden cronológico**, que es el mismo orden de las etapas de
`INSTALACION.md`. Así se lee la instalación entera de arriba abajo.

| Fichero | Qué contiene | Etapa |
|---|---|---|
| `01_estado_tras_instalar_…` | SO, boot, UART, LIDAR, rendimiento, red, actualizaciones automáticas. **La línea base** | B, antes de la higiene |
| `02_higiene_aplicada_pre_reboot_…` | Las 11 medidas del cap. 4 aplicadas, antes de reiniciar | C |
| `03_etapa_C_verificada_post_reboot_…` | Las métricas con los contadores a cero: arranque **1min39s → 8.7 s** | C, tras reiniciar |
| `04_gonogo_sdk_py312_…` | 🟢 **GO** del SDK en Python 3.12, con el contexto del NO-GO falso | D |
| `05_verificar_robot_…` | Salida completa de `verificar_robot.sh --hardware` | cualquiera |
| `06_ros2_jazzy_instalado_…` | ROS 2 Jazzy: 201 paquetes, `ros2 doctor` 5/5, pub/sub a 9.997 Hz σ 0.35 ms | E1 |
| `07_fase2_driver_ros2_…` | El driver en `rclpy`: `/odom` a 16.671 Hz, watchdog en 527 ms, y **el hallazgo del sensor `Velocity`** | Fase 2 |
| `08_fase3_urdf_…` | El árbol TF. ⚠️ Su comprobación (`odom → laser`) resultó ser **insuficiente**: ver el fichero 11 | Fase 3 |
| `09_fase3_lidar_ros2_…` | El driver ROS del X2: `/scan` a 10.1 Hz, y **el QoS BEST_EFFORT** | Fase 3.2 |
| `10_leds_sensores_…` | 37 comprobaciones: los LEDs uno a uno y los 17 sensores, sin ROS | 8bis |
| `11_slam_fase4.txt` | SLAM: ciclo de vida, `base_link` con dos padres, y **🔴 el RVR se duerme solo** | Fase 4 |
| `12_keepalive_rvr.txt` | El timeout del RVR **medido en 300.6 s**, y el arreglo verificado: 2 huecos → **0** | Fase 4 |
| `13_fase4_cerrada.txt` | **Fase 4 cerrada**: el mapa crece al moverse. Tres arreglos y dos herramientas propias corregidas | Fase 4 |
| `14_deriva_slam_caracterizada.txt` | La deriva, con 6 corridas: mediana **1.0 / 2.7 cm**. Los 87.8 cm eran una anomalía | Fase 4 |
| `mapas/` | `mapa_fase4_banco` (robot casi quieto) y `mapa_fase4_cerrada` (8.25 m² mapeados) — formato nativo de slam_toolbox | Fase 4 |
| `lidar_x2_2026-07-30.txt` | Salida de `x2_parse.py` | B |
| `raw_uart_2026-07-30.txt` | Salida de `raw_uart.py`: «el RVR CONTESTA» | B |

## Lo que hay que leer de aquí

**El esquema de ficheros de arranque cambió.** `usercfg.txt` y `syscfg.txt` **no existen** en
24.04, `pibootctl` no se instala, y `config.txt` no tiene ninguna línea `include`. La
búsqueda en todo el sistema está en el fichero de estado. Explicado en el manual, cap. 3.4.

**El arranque es mucho más lento que en 20.04, y no es un problema de la máquina.**

| | 20.04 (`../evidencia/`) | 24.04 recién instalado |
|---|---|---|
| userspace | 29.5 s | **1 min 39 s** |
| culpable nº1 | escritorio GNOME duplicado | **`cloud-final.service` = 1 min 7 s** |
| tareas | 273 | **187** |
| journal | 784 MB | 17.7 MB |
| governor | `ondemand` | `ondemand` |
| `io.full total` | 47 s / 42 min | **74.6 s / 34 min** |

Menos procesos y menos journal, pero arranque peor y **más presión de I/O** — porque
`cloud-init` y `unattended-upgrades` están trabajando. El capítulo 4 los desactiva.

**`unattended-upgrades` viene activo y actualiza el kernel solo.** Ver el apartado
«Actualizaciones automaticas» del fichero de estado: kernel en ejecución `6.8.0-1047-raspi`,
kernel instalado `6.8.0-1060-raspi`, con `reboot-required` puesto. Es el motivo del apartado
3.5.1 del manual: **cerrar las actualizaciones antes de tocar el device-tree**, para no
mezclar dos cambios en un mismo reinicio.

**`iw` no viene instalado.** Aparece como `NO` en la sección de red. Importa porque el script
de higiene lo necesita para apagar el power-save del WiFi.

**El CP2102 del LIDAR no tiene serial único** (`ID_SERIAL_SHORT=0001`), pero su `ID_PATH`
**sí** identifica el puerto físico. Relevante para la regla udev de los 16 robots: ver
`03_operacion/FLOTA.md`.

## Y los hallazgos que más caros habrían salido

**🔴 El stream `Velocity` del RVR no sirve** (fichero 07). Con el robot avanzando a
**0.147 m/s** comprobados por desplazamiento, el sensor reportaba **0.001 m/s**. El driver
publica `odom.twist.twist.linear` desde ahí, así que **la velocidad de `/odom` es basura** — y de
ahí comen SLAM y `robot_localization`. La **posición** sí es buena.

**🔴 La posición del LIDAR estaba 7.4 cm corta** (fichero 08). El proyecto arrastraba `0.10 m`
desde un `static_transform_publisher` que la propia documentación admitía como suposición. El
valor real es **0.1745 m**. Un error así inclina el mapa entero sin dar ningún error.

**🔴 El RVR se duerme solo y el nodo no se entera** (ficheros 11 y 12). `/odom`, `/imu` y
`/color` dejan de publicar **a la vez** mientras el proceso sigue vivo al 12.3 % de CPU con sus
topics registrados y **sin un solo error**. Un robot que espere 5 minutos a que el estudiante
empiece su práctica **estará mudo al empezar**, y la web no verá nada raro. `systemd` con
`Restart=always` no lo arregla: el proceso no muere.
→ ✅ **Medido en 300.6 s exactos** (dos veces) **y arreglado** con keepalive + detector de
silencio: 2 huecos en 12 min pasan a **0**. Fichero 12.

**🔴 `base_link` tenía dos padres** (fichero 11) y partía el árbol TF en dos, con SLAM sin
mapear. Lo grave no es el error: es que **la verificación de la Fase 3 lo dio por bueno**.
Comprobaba `tf2_echo odom laser`, que resolvía por el camino equivocado. La regla que queda:
**comprueba el transform que pide el consumidor, con sus frames exactos.**

Todos se encontraron **midiendo**, no leyendo código.
