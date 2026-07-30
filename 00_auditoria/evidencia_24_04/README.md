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

| Fichero | Qué contiene | Momento |
|---|---|---|
| `01_estado_tras_instalar_2026-07-30.txt` | Estado completo: SO, boot, UART, LIDAR, rendimiento, red, actualizaciones automáticas | Tras el primer arranque, **antes** de la higiene del SO (cap. 4) |
| `lidar_x2_2026-07-30.txt` | Salida de `x2_parse.py` | Idem |

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
