# Runbook de operación

> ## ✅ Estado: **ROS 2 Jazzy**, verificado sobre rvr-01
>
> 🔴 Esta cabecera decía «válido para el sistema ROS Noetic actual · se reescribirá para ROS 2
> Jazzy» hasta el 2026-08-01, cuando **todo el cuerpo del documento ya era ROS 2**. Hacía
> desconfiar del documento entero justo cuando más falta hace: es el que se abre con el robot
> caído.

---

## Arrancar el robot

✅ **El robot arranca SOLO al encender.** Desde el 2026-07-31 hay `atriz-robot.service`, y está
probado con un reinicio de verdad (manual, cap. 17). No tienes que hacer nada.

```bash
systemctl status atriz-robot        # active (running)
```

### 🔴 Y arranca CON EL BARRIDO DEL LIDAR APAGADO, así que NO CONDUCE

**No está roto.** Es a propósito: si no, el X2 giraría a 11.8 Hz de forma permanente en los 16
robots, se usen o no. Sin `/scan` el `collision_monitor` bloquea el movimiento — medido: 0.0 cm
con el barrido apagado contra 9.9 cm con él encendido, mismo comando.

```bash
atriz-escaneo on        # el X2 sube a 11.8 Hz y el robot ya conduce
atriz-escaneo estado
atriz-escaneo off       # al terminar la sesión
```

⚠️ **Si el robot «no responde a `cmd_vel`», esto es lo PRIMERO que hay que mirar.**
📝 Los **servicios de movimiento** del driver sí funcionan con el barrido apagado: hablan al RVR
por el puerto serie y se saltan el monitor.

### Pararlo y arrancarlo a mano

```bash
sudo systemctl stop atriz-robot       # no lo deshabilita: volverá al encender
sudo systemctl start atriz-robot
sudo systemctl restart atriz-robot
journalctl -u atriz-robot -f          # Ctrl-C para salir
```

### Si necesitas lanzarlo a mano (para depurar con argumentos)

🔴 **Para el servicio primero**, o los dos se pelearán por `/dev/rvr`:

```bash
sudo systemctl stop atriz-robot
source /opt/ros/jazzy/setup.bash && source ~/atriz_ws/install/setup.bash

# Terminal 1 — el robot: driver del RVR + URDF + LIDAR
ros2 launch atriz_rvr_bringup robot.launch.py

# Terminal 2 — SLAM (opcional; el robot funciona sin él)
ros2 launch atriz_rvr_bringup slam.launch.py
```

🔴 **Los dos launch se arrancan JUNTOS y en ese orden.** Reiniciar el driver por debajo de un
`slam_toolbox` ya en marcha lo deja con un hueco en su buffer TF y **deja de procesar**, sin
dar ningún error: el mapa se queda idéntico celda a celda. Si tienes que reiniciar el driver,
reinicia también SLAM.

Argumentos útiles:

```bash
ros2 launch atriz_rvr_bringup robot.launch.py lidar:=false          # solo el RVR
ros2 launch atriz_rvr_bringup robot.launch.py keepalive_period:=0.0 # reproduce el sueño a propósito
ros2 launch atriz_rvr_bringup slam.launch.py autostart:=false       # deja slam_toolbox sin activar
ros2 launch atriz_rvr_bringup robot.launch.py color_detection:=true # enciende el LED del sensor de color
ros2 launch atriz_rvr_bringup robot.launch.py publicar_inclinacion:=true  # /odom con el pitch de 6.9°
```

📝 `color_detection` y `publicar_inclinacion` van a **false** por defecto, y por buenas razones:
el primero deja un LED blanco encendido bajo el chasis, y el segundo publica una inclinación que
es un artefacto del acelerómetro descalibrado, no del robot (manual, cap. 13 y 16).

### Antes de arrancar, dos comprobaciones de 5 segundos

```bash
ls -l /dev/rvr          # debe existir y apuntar a ttyAMA0
ls -l /dev/ydlidar      # el LIDAR, si lo vas a usar -> ttyUSB0
```

Y lo más importante: **¿está el RVR encendido, con la batería puesta?** Un RVR dormido
produce exactamente el mismo síntoma que un cable mal conectado.

> **Para el sistema viejo (Noetic), tras restaurar la imagen `dd`:** `roscore` en una terminal
> 📝 Eso era ROS 1. Hoy el robot **arranca solo** con `atriz-robot.service`, y para lanzarlo a
> mano hay que **parar el servicio primero** (`sudo systemctl stop atriz-robot`) o los dos se
> pelean por `/dev/rvr`.
> Los nombres del `MANUAL SPHERO.docx` (`sphero_rvr_hw`, `sphero_rvr`) **no existen**.

---

## Verificar que funciona

```bash
ros2 topic list                      # /odom /imu /cmd_vel /color /scan /battery_state /tf ...
ros2 node list                       # /rvr_driver /robot_state_publisher /ydlidar_ros2_driver_node
```

**Y ahora las comprobaciones que de verdad importan.** Cada una existe porque lo que había
antes **pasaba con el sistema roto**:

```bash
ros2 topic hz /odom          # ~16.5 Hz ✅ funciona: topic hz adapta el QoS
#    🔴 Mira el RITMO, no que el topic exista: `ros2 topic list` conserva topics
#       de nodos MUERTOS, y el RVR se dormía con el topic registrado.
#    📝 Para caracterizar (jitter, huecos) usa `medir_ritmo_ros2.py`.
                             #          dejando el nodo vivo y publicando CERO, sin un error
ros2 run tf2_ros tf2_echo odom base_footprint
                             # 🔴 ESTA, no `odom laser`: la segunda resolvía por el camino
                             #    equivocado con el árbol TF partido en dos
ros2 topic echo /battery_state --once
                             # llega cada 30 s. Es el latido del keepalive: si no llega,
                             # el robot se dormirá a los 5 min
ros2 topic hz /scan          # 10.1–11.9 Hz, con el barrido ENCENDIDO
ros2 lifecycle get /slam_toolbox     # active [3] — si dice `unconfigured`, está vivo y NO mapea
```

Valores de referencia medidos sobre **ROS 2 Jazzy**:

| Métrica | Esperado | Medido |
|---|---|---|
| `/odom` | **16.7 Hz**, σ 0.47 ms | 2026-07-30 |
| `/scan` | ~10 Hz, 260 puntos | 2026-07-31 |
| `/map` | 0.200 Hz exactos | 2026-07-31 |
| `/battery_state` | cada **30.0 s** exactos | 2026-07-31 |
| CPU del driver | ~23 % de un núcleo | 2026-07-31 |
| CPU de `slam_toolbox` | **4.4 %** | 2026-07-31 |
| Todo a la vez | ~30 % de un núcleo, ~200 MB, 64 °C | 2026-07-31 |

Si te desvías mucho de esos números, algo cambió. Son la línea base.

O de una vez, con las 50 aserciones:

```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```

---

## Parar

```bash
sudo systemctl stop atriz-robot     # lo normal desde el 2026-07-31

# Si lo lanzaste a mano: Ctrl+C en cada launch.
# Si quedan procesos colgados, por PID:
kill -INT $(pgrep -f "[r]os2 launch atriz_rvr_bringup")
sleep 3
pgrep -af "[r]vr_driver_node|[y]dlidar_ros2_driver_node|async_slam_toolbox_node"
```

> ⚠️ **No uses `pkill -f`, y ojo también con `pgrep -f`.** El patrón coincide con la propia
> línea de comando del shell que lo ejecuta y **mata tu terminal**. Pasó tres veces.
>
> 🔴 **Y el truco del corchete (`[r]vr_driver`) no basta.** Protege de que `pgrep` case su
> propio patrón, **no** de que case una *ruta* que lo contenga: un script que buscaba
> `slam_toolbox` se mató a sí mismo al pasarle
> `/opt/ros/jazzy/share/slam_toolbox/config/…` como argumento. Filtra por algo que no pueda
> estar en tu propia línea de comandos (`lib/slam_toolbox/async_slam_toolbox_node`) y excluye
> `$$` y `$PPID`.

**Cuando termines de trabajar, para los nodos.** Con el driver activo el RVR permanece
despierto y consume batería — y ahora además el keepalive lo mantiene despierto a propósito.

⚠️ **`stop` NO deshabilita el servicio**: volverá solo en el próximo arranque, que es lo que
queremos. Para que deje de hacerlo —solo si algo va mal— hace falta
`sudo systemctl disable --now atriz-robot`.

📝 Y si solo quieres bajar el consumo sin apagar el robot, **`atriz-escaneo off`** deja el X2 en
2.7 Hz en vez de 11.8. No lo apaga: el láser y la electrónica siguen alimentados mientras haya
5 V en el USB, y la Pi 4 no puede cortarlos (manual, cap. 8.4a).

---

## Cuando algo falla

### 🔴 El robot está «vivo» pero no publica nada — EMPIEZA POR AQUÍ

Es el fallo más traicionero del sistema, porque **todo parece correcto**: el proceso vive, el
nodo aparece en `ros2 node list`, los topics están registrados (`Publisher count: 1`) y **no
hay ni un error en el log**.

```bash
ros2 topic hz /odom          # ¿~16.5 Hz, o nada?
```

**Si no llega nada, el RVR se durmió.** Medido: se duerme a los **300.6 s = 5.01 min** exactos
sin que nadie le hable. `/odom`, `/imu` y `/color` se callan **a la vez**.

⚠️ **Y la pista fácil engaña:** `ros2 topic hz /tf` puede seguir dando 50 Hz, así que parece
que «TF va bien». Esos 50 Hz son de `slam_toolbox` **a solas** — con el driver aportando
serían ~67 Hz.

**Arreglo inmediato: reinicia el driver.** `/odom` vuelve a 16.669 Hz.

**Por qué no debería pasar ya:** el driver lleva desde el 2026-07-31 un keepalive que le habla
al RVR cada 30 s y un detector de silencio que avisa y reanuda a los 3 s. Si vuelve a pasar,
mira el log del driver:

```
[WARN] el RVR lleva 3.4 s sin enviar telemetría … Intentando reanudar (intento nº 1)…
[INFO] streaming reanudado.
```

- Si **aparecen esos mensajes**, el detector funciona y algo está tirando el enlace repetidamente.
- Si **no aparece ninguno** y `/odom` está mudo, el keepalive no está corriendo: comprueba que
  no arrancaste con `keepalive_period:=0.0`.
- 📝 Un `systemd` con `Restart=always` **no** arregla esto: el proceso no muere.

### 🔴 SLAM no produce mapa, o el mapa no crece

Por orden, y **los tres primeros ya han sido la causa real** en este proyecto:

**1. ¿Está `slam_toolbox` activado?** Es un **nodo de ciclo de vida**: arranca en
`unconfigured`, vivo y sin hacer absolutamente nada — no se suscribe a `/scan`, no publica
`/map`, y su log se queda en «Node using stack size» sin un solo error.

```bash
ros2 lifecycle get /slam_toolbox      # debe decir: active [3]
ros2 topic info /scan --verbose       # `Subscription count: 0` es el síntoma
```

**2. ¿Has movido el robot lo suficiente?** 🔴 **Girar sobre el eje NO hace crecer el mapa,
nunca.** El X2 barre los 360°, así que girar en el sitio vuelve a ver lo mismo desde el mismo
punto. Y no bastan 40 cm de avance: `slam_toolbox` cuenta la distancia desde el **último nodo
del grafo**, no desde donde empezaste. Hicieron falta **~0.85 m**.

```bash
ros2 topic echo /slam_toolbox/graph_visualization   # si el nº de marcadores no sube,
                                                    # no está añadiendo nodos
```

**3. ¿Son todos los barridos del mismo tamaño?**

```bash
grep fixed_resolution ~/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/config/ydlidar_x2.yaml
# debe decir: true
```

Con `false` el X2 alterna 254/255 puntos y `slam_toolbox` **descarta** todos los que no midan
como el primero, con una sola línea en su log:
`LaserRangeScan contains 254 range readings, expected 255`.

**4. ¿Coinciden `/scan` y `/odom` en el sentido de giro?**

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/verificar_inverted_lidar.py
```

Si se contradicen, el emparejado de barridos pelea contra la odometría y **el mapa sale
espejado o emborronado — y coherente consigo mismo, así que mirarlo no lo detecta.**

**5. ¿Reiniciaste el driver con SLAM ya arrancado?** Reinicia también SLAM.

### El robot chocó durante una prueba

Las herramientas de banco **mueven el robot y no hay evitación de obstáculos**: solo existe el
watchdog de `cmd_vel`, que para los motores si deja de recibir órdenes, no si hay algo delante.

Antes de lanzar `medir_slam_ros2.py`, con el robot en el centro:

```
            ↑ 1 m por delante (hacia donde mira)
    ┌───────────────────────┐
40cm│      ┌─────┐          │40cm     el robot NO se desplaza
←───┤      │ RVR │ →        ├───→     lateralmente: a los lados
    │      └──┬──┘          │         solo hace falta el hueco
    └───────────────────────┘         del giro (radio 14 cm)
            ↓ 1 m por detrás
```

Y **nada a menos de 60 cm**. El LIDAR va a **15.5 cm** de altura barriendo en horizontal
(✅ medido con regla el 2026-07-31; antes se decía 17.45, que era un valor DERIVADO de la
ficha del RVR y salía 2 cm alto — manual, cap. 12.8):
pasa por encima de zócalos, cables y cajas bajas, y por debajo de mesas. «Parece despejado a
ras de suelo» no basta.

Con `--solo-giro` el robot **no se desplaza** y basta un círculo de 50 cm — pero recuerda que
girando el mapa no crece, así que eso no vale como prueba de SLAM.

### 🔴 El robot no conduce, pero todo lo demás va — EMPIEZA POR AQUÍ

Desde que hay arranque automático, **la causa nº1 es que el barrido del LIDAR está apagado**, y
el robot no está roto: sin `/scan` el `collision_monitor` bloquea el movimiento a propósito.

```bash
atriz-escaneo estado      # ¿"apagado"?
atriz-escaneo on          # y ya conduce
```

Medido: **0.0 cm** con el barrido apagado contra **9.9 cm** con él encendido, mismo comando por
`/cmd_vel_raw`. Si tras encenderlo sigue sin moverse, pasa al apartado siguiente.

📝 Segunda causa, si el barrido está encendido: **la parada de emergencia activa**. El log del
driver lo dice, y los servicios de movimiento responden *«parada de emergencia ACTIVA»*.

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
lsmod | grep cp210x                         # el módulo debe estar cargado
sudo dmesg | grep -i cp210x                 # ⚠️ sudo: en 24.04 dmesg está restringido
udevadm info -q property -n /dev/ttyUSB0 | grep -E 'ID_SERIAL_SHORT|ID_PATH='
```

> En Ubuntu Server 24.04 el módulo `cp210x` viene en `linux-modules-*-raspi` y se carga solo
> al conectar el adaptador — no hace falta instalar nada. Verificado el 2026-07-30.

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

✅ **Funciona, y la de la web también** desde el 2026-07-31. Escucha los **tres** nombres, así
que da igual cuál uses:

```bash
# ✅ EL OFICIAL desde el 2026-08-01, y es donde debe publicar la web:
ros2 topic pub --once /emergency_stop std_msgs/msg/Empty "{}" \
  --qos-reliability reliable --qos-durability volatile
# 📝 El driver escucha además /is_emergency_stop y /rvr/emergency_stop (la web
#    heredada usaba este último). Los tres a propósito: con un botón de
#    emergencia el modo de fallo que importa es que el mensaje NO llegue.
ros2 topic pub --once /emergency_stop     std_msgs/msg/Empty "{}"
```

Para liberarla — y es un acto **explícito**, a propósito:

```bash
ros2 service call /release_emergency_stop std_srvs/srv/Empty
```

**Qué hace exactamente:** el driver pone una bandera, llama a `drive_stop()` y a partir de ahí
**descarta todo `cmd_vel`**. Con Nav2 mandando a 10 Hz el robot se queda quieto igualmente.

🔴 **Y desde el 2026-07-31 CANCELA los objetivos de Nav2.** Antes no lo hacía, y el fallo estaba
donde nadie miraba: `/release_emergency_stop` solo baja la bandera, así que al soltarla **el
robot arrancaba solo** — el objetivo seguía vivo y el controlador nunca dejó de publicar. Medido:
**34.7 cm** sin el arreglo, **0.0 cm** con él. Lo hace el nodo `cancelar_nav2`, que arranca
`nav2.launch.py`.

✅ **También para los servicios de movimiento** (`move_timed`, `raw_motors`, `move_to_pose`…):
comprueban la bandera y se niegan con *«parada de emergencia ACTIVA: llama primero a
/release_emergency_stop»*. Lo que esos servicios **se saltan** es el `collision_monitor` —hablan
al RVR por el puerto serie, no publican en ningún topic—, que es un asunto distinto.

**Historial, porque esta función ha fallado CUATRO veces y siempre en silencio:**
nombre del topic (ROS 1) → namespace → QoS → y no cancelar Nav2. Manual, cap. 15.

> ✅ **Y sí hay watchdog** desde la Fase 2: si dejan de llegar `cmd_vel`, el driver para los
> motores en ~0.35 s. Este apartado decía lo contrario, y era del sistema viejo.

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
vcgencmd get_throttled                                        # 0x0 = ni throttling ni under-voltage
sudo dmesg | grep -iE "throttl|under.?volt"                    # vacío = alimentación correcta
```

> ⚠️ **`dmesg` necesita `sudo` en 24.04** (`kernel.dmesg_restrict=1`). Sin él responde
> `Operation not permitted`, que **no** es un fallo de hardware. `vcgencmd get_throttled` da la
> respuesta sin `sudo` y es más directo: `throttled=0x0` significa que nunca ha habido ni
> throttling térmico ni caída de tensión desde el arranque.

> En la auditoría original **el hardware estaba sano**: 59.9 °C, cero throttling, cero
> under-voltage, 4.2 GB de RAM libre. La lentitud era 100 % configuración. Empieza siempre
> por ahí.

### La batería se agota

```bash
# `battery_state` es un TOPIC, no un servicio — y `rosservice` es de ROS 1.
ros2 topic echo /battery_state --once
```

La Pi se alimenta del USB del RVR, así que **una batería baja apaga las dos cosas**. Si el
robot se apaga solo a mitad de una sesión, mira la batería antes de buscar fallos de
software.

---

## Antes de auditar o depurar cualquier cosa

**`git fetch` primero.** Siempre.

```bash
cd ~/atriz_ws/src/Atriz_rvr        # ~/atriz_git era la ruta del sistema VIEJO
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

# Ritmo de telemetría  (medir.py era de ROS 1 y ya no arranca)
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_ritmo_ros2.py

# LIDAR sin driver ROS
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/x2_parse.py

# Salud del SDK
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py

# El servicio del robot
systemctl status atriz-robot
journalctl -u atriz-robot -f
atriz-escaneo on | off | estado

# Emergencia
# ✅ El oficial es /emergency_stop, con RELIABLE + VOLATILE.
#    /rvr/emergency_stop lo escucha el driver a propósito (la web heredada lo
#    usaba), pero es el nombre que causó el fallo nº2: no lo enseñes.
ros2 topic pub --once /emergency_stop std_msgs/msg/Empty "{}" \
  --qos-reliability reliable --qos-durability volatile
ros2 service call /release_emergency_stop std_srvs/srv/Empty

# Estabilidad prolongada (12 min)
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/estabilidad.py
```
