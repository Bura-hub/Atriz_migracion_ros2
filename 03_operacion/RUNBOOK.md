# Runbook de operación

> **Estado: válido para el sistema ROS Noetic actual** (verificado 2026-07-29).
> Se reescribirá para ROS 2 Jazzy en las fases 2–5. Los procedimientos de
> **diagnóstico** de la sección «Cuando algo falla» son en su mayoría independientes
> de la versión de ROS y seguirán sirviendo.

---

## Arrancar el robot

**Estado actual: no hay arranque automático.** No existe ninguna unidad systemd, así que
hay que hacerlo a mano. Se resuelve en la Fase 1 del plan (`atriz-rvr.service`).

```bash
# Terminal 1
roscore

# Terminal 2
source /opt/ros/noetic/setup.bash
source ~/atriz_git/devel/setup.bash
rosrun atriz_rvr_driver Atriz_rvr_node.py
```

O con el script del repo, que hace las dos cosas:
```bash
bash ~/atriz_git/src/Atriz_rvr/start_ros.sh
```

> ⚠️ Los nombres de paquete del `MANUAL SPHERO.docx` (`sphero_rvr_hw`, `sphero_rvr`) **ya
> no existen**. El paquete es `atriz_rvr_driver`.

### Antes de arrancar, dos comprobaciones de 5 segundos

```bash
ls -l /dev/rvr          # debe existir y apuntar a ttyAMA0
ls -l /dev/ttyUSB0      # el LIDAR, si lo vas a usar
```

Y lo más importante: **¿está el RVR encendido, con la batería puesta?** Un RVR dormido
produce exactamente el mismo síntoma que un cable mal conectado.

---

## Verificar que funciona

```bash
rostopic list                       # deben aparecer /odom /imu /cmd_vel /color ...
rosnode list                        # debe aparecer /driver_rvr
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir.py
```

Valores de referencia medidos el 2026-07-29 (con `interval=60`):

| Métrica | Esperado |
|---|---|
| `/odom` | **16.59 Hz**, σ ~2.5 ms |
| `/imu` | 16.59 Hz |
| RSS del nodo | ~53 MB, **plano** |
| CPU del nodo | ~29.5 % de un núcleo |
| Temperatura de la Pi | 55–58 °C |

Si te desvías mucho de esos números, algo cambió. Son la línea base.

---

## Parar

```bash
# Parada normal: Ctrl+C en el nodo, luego en roscore
# Si quedan procesos colgados:
kill -INT $(pgrep -f "[A]triz_rvr_node.py")
sleep 3
kill -9 $(pgrep -f "[A]triz_rvr_node.py") 2>/dev/null
kill $(pgrep -x rosmaster)
```

> ⚠️ **No uses `pkill -f Atriz_rvr_node`.** El patrón coincide con la propia línea de
> comando del shell que lo ejecuta, y **mata tu propia terminal**. Pasó dos veces durante
> la Fase 0.1. Usa `pgrep -f "[A]triz..."` (con el corchete) o el PID directamente.

**Cuando termines de trabajar, para el nodo.** Con el driver activo el RVR permanece
despierto y consume batería.

---

## Cuando algo falla

### El robot no responde

Diagnostica **de abajo hacia arriba**. El orden importa: cada paso descarta una capa.

**1. ¿Está el robot encendido?** Suena obvio; es la causa nº1. Un RVR dormido no
devuelve ni un byte, igual que un cable suelto. **Apaga y enciende el robot antes de tocar
nada.**

**2. ¿Existe el puerto?**
```bash
ls -l /dev/rvr        # debe ser un symlink a ttyAMA0
```
Si falta: la regla udev no se aplicó. `sudo udevadm control --reload-rules && sudo udevadm trigger`.

**3. ¿Contesta a nivel de bytes?** Es la prueba decisiva, y no depende de ROS ni del SDK:
```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/raw_uart.py
```
- **Recibe bytes** → el enlace físico está bien. El problema está más arriba (SDK, ROS, driver).
- **Cero bytes** → el robot está apagado/dormido, o el cableado está mal (TX/RX cruzados, GND suelto).

**4. ¿Funciona el SDK?**
```bash
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

> 🔴 **No uses «el nodo arrancó» como prueba de que el enlace funciona.**
> `rvr_fw_check_async.py` captura `except (asyncio.TimeoutError, Exception)` y continúa en
> silencio. El nodo registra sus topics, parece sano, y no hay ningún dato circulando.
>
> **Atajo de diagnóstico:** el tiempo de construcción de `SpheroRvrAsync` te lo dice.
> **0 s** = el robot contesta. **~10 s** = dos timeouts de 5 s = no contesta.

### El LIDAR no aparece

```bash
lsusb | grep -i "silicon\|cp210\|ftdi"      # debe salir el CP2102
ls -l /dev/ttyUSB0
dmesg | grep -i cp210x
```

Si el dispositivo está pero no hay datos:
```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/x2_parse.py
```
Esto decodifica el protocolo X2 directamente, sin el driver ROS. Referencia medida:
**100 % de checksums válidos, 2998 muestras/s, 11.4 Hz, 263 puntos/vuelta.**

Si el lidar **no gira**: el X2 alimenta su motor por la línea **DTR** del adaptador USB.
No todos los adaptadores la exponen. **El adaptador es el primer sospechoso, no el lidar.**

> ⚠️ `scripts/lydar/test_lidar.py` reporta «Tipo de LIDAR: Desconocido» aunque los datos
> sean perfectamente válidos. Su identificador de protocolo no reconoce al X2. **No es un
> fallo del lidar.** Fíjate en «bytes recibidos» y «tasa de datos» (~7000 B/s), no en el tipo.

### La parada de emergencia

🔴 **La de la plataforma web NO FUNCIONA** (confirmado 2026-07-29). Publica en
`/rvr/emergency_stop`, un topic que no existe. Falla en silencio con `200 OK`.

**La que sí funciona:**
```bash
rostopic pub -1 /is_emergency_stop std_msgs/Empty '{}'
rosparam get /emergency_stop           # debe devolver: true
```

Para liberarla:
```bash
rosservice call /release_emergency_stop
rosparam get /emergency_stop           # debe devolver: false
```

> **No hay watchdog.** Si se cae la red, el robot **sigue con el último comando**. Hasta
> que se implemente (Fase 2), la parada física —apagar el robot— es la única defensa
> fiable. Tenlo presente al teleoperar.

### El sistema va lento

Comprueba lo que causó la lentitud original:
```bash
systemctl get-default                                          # debe ser multi-user.target
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor       # ideal: performance
journalctl --disk-usage                                        # no debe crecer sin control
cat /proc/pressure/io                                          # 'full total' alto = SD saturada
iw dev wlan0 get power_save                                    # debe decir: off
```

Y descarta el hardware antes de culparlo:
```bash
cat /sys/class/thermal/thermal_zone0/temp                      # /1000 = °C; <80 está bien
dmesg | grep -iE "throttl|under.?volt"                         # vacío = alimentación correcta
```

> En la auditoría original **el hardware estaba sano**: 59.9 °C, cero throttling, cero
> under-voltage, 4.2 GB de RAM libre. La lentitud era 100 % configuración. Empieza siempre
> por ahí.

### La batería se agota

```bash
rosservice call /battery_state
```

La Pi se alimenta del USB del RVR, así que **una batería baja apaga las dos cosas**. Si el
robot se apaga solo a mitad de una sesión, mira la batería antes de buscar fallos de
software.

---

## Antes de auditar o depurar cualquier cosa

**`git fetch` primero.** Siempre.

```bash
cd ~/atriz_git/src/Atriz_rvr
git fetch origin
git status -sb
git log --oneline HEAD..origin/main    # ¿qué me falta?
```

El 2026-07-29 se hizo una auditoría completa sobre un clon que estaba **5 commits por
detrás** y al que **nunca se le había hecho `fetch`**. Tres hallazgos resultaron falsos y
hubo que rehacer trabajo. Es el error más caro de la sesión, y el más fácil de evitar.

---

## Comandos de referencia rápida

```bash
# Estado del enlace
ls -l /dev/rvr /dev/ttyUSB0
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/raw_uart.py

# Ritmo de telemetría
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir.py

# LIDAR sin driver ROS
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/x2_parse.py

# Salud del SDK
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py

# Emergencia (la que funciona)
rostopic pub -1 /is_emergency_stop std_msgs/Empty '{}'
rosservice call /release_emergency_stop

# Estabilidad prolongada (12 min)
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/estabilidad.py
```
