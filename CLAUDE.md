# Instrucciones para Claude — proyecto Atriz

Este fichero se carga automáticamente al iniciar Claude Code en este directorio.
**Léelo entero antes de actuar.**

---

## Qué es este proyecto

Laboratorio de robótica remoto: **16 robots Sphero RVR**, cada uno con una Raspberry Pi 4
y un YDLIDAR X2, gobernados desde una plataforma web. Migración de **ROS Noetic
(EOL) → ROS 2 Jazzy**.

Tres repositorios:

| Repo | Qué es |
|---|---|
| **este** (`Atriz_migracion_ros2`) | Auditoría, plan, manual, scripts, documentación de operación |
| `Bura-hub/Atriz_rvr` | Código del robot. Rama de trabajo: **`ros2`**. ⚠️ `migracion-ros2` es la rama VIEJA con código de ROS 1: no compila con colcon |
| `Bura-hub/Atriz_web_server` | Plataforma web. **Se aborda al final**, no antes |

---

## Lo PRIMERO que debes hacer

1. Lee **[`TRASPASO.md`](TRASPASO.md)** — es el estado actual: qué está verificado, qué está
   roto, cuál es el siguiente paso exacto.
2. Lee **[`CHANGELOG.md`](CHANGELOG.md)** — la bitácora, para saber qué pasó y por qué.
3. Si vas a instalar el sistema desde cero: **[`INSTALACION.md`](INSTALACION.md)**.
   ⚠️ **No sigas el manual del capítulo 0 al 12** — sus capítulos están numerados por tema,
   no por orden de ejecución. `INSTALACION.md` da el recorrido real y remite a cada capítulo
   cuando toca.

**No empieces a tocar el sistema sin haber leído esos tres.** El contexto de este proyecto
tiene bastantes trampas documentadas que cuestan horas si se ignoran.

---

## Reglas del proyecto — no negociables

### 1. `git fetch` ANTES de auditar o leer código

```bash
git -C ~/atriz_ws/src/Atriz_rvr fetch origin && git -C ~/atriz_ws/src/Atriz_rvr status -sb
```

El 2026-07-29 se hizo una auditoría completa sobre un clon **5 commits por detrás** al que
**nunca se le había hecho `fetch`**. Tres hallazgos resultaron falsos y hubo que rehacer
trabajo. Es el error más caro de la historia del proyecto.

### 2. Nada se documenta sin haberse ejecutado y verificado

Si un paso no se ha probado, se marca explícitamente **NO VERIFICADO**. Nunca se presenta
una deducción como un hecho. La deriva entre documentación y código es uno de los problemas
que encontró la auditoría original — no se repite.

### 3. Nada se ejecuta sin documentarse

El recíproco de la anterior, y también se ha incumplido una vez. Si creas una rama, rescatas
un stash, o descubres algo, **va al repositorio antes de seguir**. Un mensaje de chat no es
documentación: desaparece.

### 4. Mide antes de atribuir

La auditoría culpó al bucle de asyncio del driver de que la odometría fuera a 4 Hz. Al medir
el SDK **sin ROS de por medio** salió idéntico: la causa era un solo parámetro. El arreglo
fue **una línea** en lugar de una reescritura planificada.

Antes de afirmar que X causa Y, aísla X.

### 5. Sin secretos en el repositorio

Ni contraseñas, ni claves, ni la PSK del WiFi. La credencial del usuario `sphero` **ya está
expuesta** en `Atriz_web_server` público y debe rotarse. `MANUAL_SPHERO_original.docx` la
contiene: por eso este repositorio es **privado**.

### 6. Commitea al cerrar cada fase, y actualiza el `CHANGELOG.md`

Aunque sea una línea. Es lo que permite retomar el hilo semanas después.

---

## Trampas de diagnóstico — te ahorrarán horas

**Un robot dormido parece un cable roto.** Un RVR dormido no devuelve ni un byte, síntoma
idéntico a un cable mal puesto. **Pide al usuario que apague y encienda el robot antes de
tocar configuración.** Se perdió un buen rato persiguiendo un problema de device-tree
inexistente.

**🔴🔴 EL RVR SE DUERME SOLO Y EL NODO SIGUE «SANO».** Y es peor que lo anterior, porque
aquí no hay nada que parezca roto. Medido el 2026-07-30: a mitad de sesión, sin tocar nada,
`/odom`, `/imu` y `/color` dejaron de publicar **a la vez**, mientras el proceso seguía vivo
al 12.3 % de CPU con 17 hilos, sus topics registrados (`Publisher count: 1`) y **ni un
mensaje de error**.

Y la pista fácil engaña: `ros2 topic hz /tf` daba **50 Hz**, así que «TF va bien». Pero 50 Hz
es exactamente el `transform_publish_period` de `slam_toolbox` a solas — con el driver
aportando serían ~67 Hz.

**Causa:** el `wake()` del arranque se llamaba **una sola vez** y el nodo no volvía a hablarle
al RVR salvo cuando llegaba un `cmd_vel`. El SDK vendorizado **no tiene**
`set_inactivity_timeout`.

✅ **El timeout son 300.6 s = 5.01 min**, medido el 2026-07-31 arrancando con
`keepalive_period:=0.0`: se durmió **dos veces** y las dos aguantó **300.6 s exactos**. Es un
temporizador del firmware, no una heurística. Coincide con los 5 min documentados del RVR.

✅ **ARREGLADO** en el driver (bloque «SALUD DEL ENLACE»), con dos piezas que hacen falta las
dos:
- **`_keepalive`** — cada **30 s** llama a `get_battery_percentage()` (una lectura, inocua) y
  publica **`/battery_state`**, que no existía ni en ROS 1. 10× de margen sobre los 5 min.
- **`_vigilar_silencio`** — a 1 Hz mira **cuánto hace que llegó la última muestra**. A los 3 s
  avisa e intenta reanudar (`wake` + `stop` + `start`). Verificado: detectó a los 3.4 s y
  reanudó en 4 ms, las dos veces, sin un solo fallo.

Los dos se desactivan con `keepalive_period:=0.0` / `silence_timeout:=0.0`, que es como se
reproduce el fallo a propósito.

→ **La regla de diagnóstico sigue valiendo:** si un robot no publica `/odom`, mira el
  **ritmo**, no si el nodo o el topic existen — las dos cosas eran ciertas mientras estaba
  mudo. Y un `systemd` con `Restart=always` no habría arreglado nada: el proceso no muere.

**Que el nodo arranque NO prueba que el enlace funcione.** `rvr_fw_check_async.py` captura
`except (asyncio.TimeoutError, Exception)` y continúa en silencio: el nodo registra sus
topics, parece sano, y no circula ni un dato.
→ **Atajo:** el tiempo de construcción de `SpheroRvrAsync` es diagnóstico. **0 s** = el robot
responde. **~10 s** = dos timeouts de 5 s = no responde.

**No uses `pkill -f Atriz_rvr_node`.** El patrón coincide con la propia línea de comando del
shell que lo ejecuta y **mata tu terminal**. Pasó dos veces. Usa `pgrep -f "[A]triz..."` con
el corchete, o el PID directamente.

**`uart0_pins` vacío tras `disable-bt` es NORMAL.** El overlay lo vacía a propósito: en
Raspberry Pi es el *firmware* quien asigna los pines. No es un fallo, y perseguirlo cuesta
tiempo.
→ **Atajo para saber si el overlay está en efecto, sin `sudo`:**
`cat /proc/device-tree/aliases/uart0` debe dar `/soc/serial@7e201000` (PL011). Si da
`7e215040`, sigues en el mini-UART.

**`dmesg` necesita `sudo` en Ubuntu 24.04.** `kernel.dmesg_restrict=1`. Sin `sudo` responde
`read kernel buffer failed: Operation not permitted`, que leído con prisa parece que el UART
no existe. Es un permiso, no un fallo de hardware.

**En 24.04 NO existe `usercfg.txt`, y crearlo no sirve de nada.** Ubuntu abandonó el esquema
de tres ficheros: `pibootctl` ya no se instala y `config.txt` no tiene ninguna línea
`include`. Se escribe en `/boot/firmware/config.txt`, y **obligatoriamente bajo `[all]`** —
la imagen termina en `[cm4]`, así que lo añadido al final sin esa cabecera no se aplica en un
Pi 4. Existe en el fichero y no hace nada. Detalle en el manual, cap. 3.4.

**`iw` no viene instalado en Ubuntu Server 24.04.** Importa porque es lo que apaga el
power-save del WiFi. `fase_1_higiene_so.sh` lo instala; si escribes un `ExecStart` con
`iw ... || true`, el servicio queda en verde sin hacer nada, para siempre.

**`unattended-upgrades` viene ACTIVO y actualiza el kernel solo.** Durante la instalación del
2026-07-30 metió 8 lotes de paquetes en 4 minutos, incluido `linux-image-6.8.0-1060-raspi`
sobre un sistema corriendo el 1047. **Cierra las actualizaciones y reinicia antes de tocar el
device-tree**, o un mismo reinicio aplicará dos cambios y no podrás atribuir un fallo
posterior. `fase_1_higiene_so.sh` lo deshabilita.

**`/etc/netplan/*.yaml` puede venir con permisos `644`** — contiene la PSK del WiFi en texto
plano. En 20.04 estaba así; en la imagen de **Server 24.04 ya viene `600`**. Compruébalo, no
lo asumas en ninguna de las dos direcciones. `fase_1_higiene_so.sh` lo corrige si hace falta.

**El LED del sensor de color NO se apaga con `turn_leds_off()`.** No es un grupo de
`RvrLedGroups`: se controla con `enable_color_detection`, y si no lo desactivas **se queda
encendido indefinidamente** gastando batería. Cada `enable_color_detection(True)` necesita su
`(False)`, también en el camino de error.

**Construir `SpheroRvrAsync` desde dentro de una corrutina FALLA.** `sphero_rvr_async.py:35`
hace `asyncio.get_event_loop().run_until_complete(...)` en el constructor, así que hacerlo
desde una corrutina que ya corre en ese loop da
`RuntimeError: This event loop is already running` — y el nodo arranca con todos los topics
registrados y **cero datos**. Constrúyelo con el loop **parado**, antes de arrancar el hilo.
Es el único `get_event_loop()` de la ruta usada, el que la auditoría señaló como el riesgo del
port. Ha mordido **dos veces**: al escribir el driver y al escribir una herramienta de banco.

**`core_time` no existe en el firmware 9.1.462.** Está en el enum del SDK y el RVR **no lo
transmite** — 0 muestras aislado y acompañado, mientras `quaternion` sí llega. No lo usa nada.

**`get_main_application_version()` exige `target`.** El RVR tiene dos procesadores:
`target=1` es Nordic (**9.1.462**) y `target=2` es ST (**9.2.482**). Sin el argumento: `TypeError`.

**🔴 El QoS de `/scan` es BEST_EFFORT, y `rclpy` pide RELIABLE por defecto.** Si no coinciden,
**DDS no empareja publicador y suscriptor y no llega NADA** — sin error, sin aviso en el
suscriptor. El driver del LIDAR sí lo dice, y hay que leerlo:
`New subscription discovered on topic '/scan', requesting incompatible QoS. No messages will be
sent to it.`
→ Suscríbete con `QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)`.
→ ✅ **Con `slam_toolbox` NO hay problema**, comprobado el 2026-07-30: se suscribe también con
  BEST_EFFORT (`ros2 topic info /scan --verbose`). El riesgo estaba documentado y era
  infundado.
→ Al revés también muerde: **`/map` es RELIABLE + TRANSIENT_LOCAL** (latched). Un suscriptor
  con el perfil por defecto de `rclpy` (VOLATILE) no recibe el último mapa y espera hasta 5 s
  al siguiente `map_update_interval`.

**🔴 `slam_toolbox` es un NODO DE CICLO DE VIDA en Jazzy.** Arranca en `unconfigured`: el
proceso vive, `ros2 node list` lo muestra, y **no hace nada** — no se suscribe a `/scan`, no
publica `/map`, y su log se queda en `Node using stack size` sin un solo error.
→ Se ve con `ros2 lifecycle get /slam_toolbox` (debe decir `active [3]`) y con
  `ros2 topic info /scan --verbose` (`Subscription count: 0` es el síntoma).
→ En el launch: `LifecycleNode` + eventos `configure`→`activate` encadenados con
  `OnStateTransition`, **no con un `sleep`**. `slam.launch.py` ya lo hace, con `autostart`.

**🔴 En TF un frame solo puede tener UN padre.** El driver publicaba `odom → base_link` y el
URDF `base_footprint → base_link`: el árbol se partió en dos y `slam_toolbox` repetía
`Failed to compute odom pose`. Arreglado publicando `odom → base_footprint` (que es además lo
correcto por REP-105 y lo que pide el `base_frame` de slam_toolbox).
→ **Y la lección de método, que es lo que importa:** la verificación de la Fase 3 era
  `tf2_echo odom laser` y **pasaba**, resolviendo por el camino equivocado
  (`odom → base_link → laser`) mientras `base_footprint` colgaba de otro árbol.
  **Comprueba el transform QUE PIDE EL CONSUMIDOR, con sus frames exactos** — aquí
  `tf2_echo odom base_footprint`. Un `tf2_echo` que resuelve prueba que hay *un* camino, no
  que el árbol esté bien.

**🔴🔴 GIRAR SOBRE EL EJE NO HACE CRECER EL MAPA. NUNCA.** El X2 barre los 360° completos,
así que un robot que gira en el sitio vuelve a ver **exactamente lo mismo desde exactamente
el mismo punto**: cero información nueva. Verificado el 2026-07-31: cuatro vueltas y media
seguidas, 0 celdas de cambio.
→ Una herramienta de este proyecto medía justo eso y daba un **falso negativo**, que llevó a
  bisecar el YAML de `slam_toolbox` parámetro a parámetro y a culpar a una configuración que
  estaba bien. **Para saber si SLAM mapea, DESPLAZA el robot.**
→ Y no bastan 40 cm: `slam_toolbox` cuenta la distancia desde el **último nodo del grafo**,
  no desde donde empezó la prueba. Hicieron falta **~0.85 m**. Mira el grafo, no solo el mapa:
  `ros2 topic echo /slam_toolbox/graph_visualization`.

**🔴 El RVR NO usa una sola convención de ejes, y aplicarla «por analogía» rompe cosas.**
Medido sensor a sensor el 2026-07-31:

| Sensor | Convención | Qué hay que hacerle |
|---|---|---|
| cuaternión | **FRD** | `(x, -y, -z, w)` |
| locator | **FRD** | invertir la `Y` |
| giroscopio | **ya FLU** | solo deg/s → rad/s |
| acelerómetro | **ya FLU**, y en **g** | solo × 9.80665 |

Convertir los cuatro dejaba la gravedad apuntando al techo (`z = -0.967`) y un giroscopio que
contradecía a la orientación de su propio mensaje `/imu`. **Comprueba cada sensor por
separado**: cuesta un giro y una lectura en reposo.

**Ningún software del robot puede decidir si el equivocado es `/scan` o `/odom`.** Si los dos
se contradicen en el sentido de giro, las dos explicaciones encajan con los datos. Lo desempata
**mirar el robot**: manda `angular.z` positivo y observa. El SDK documenta positivo =
antihorario, y **cumple** (verificado). `inverted: true` del YDLIDAR **era correcto**.

**`fixed_resolution: false` hace que `slam_toolbox` descarte barridos.** El X2 alterna 254/255
puntos; slam_toolbox registra el sensor con el tamaño del **primero** y tira el resto, con una
sola línea en su log y ningún error: `LaserRangeScan contains 254 range readings, expected 255`.
Se había puesto a `false` para callar un aviso **cosmético** — cambiar un parámetro para
silenciar un aviso cambió un síntoma visible por uno invisible. Con `true`: 142 barridos, todos
de 260 puntos.

**`pgrep -f` también muerde por la RUTA, no solo por el patrón.** El truco del `[s]lam_toolbox`
evita que `pgrep` case su propio patrón, pero **no** que case una ruta que lo contenga: pasarle
`/opt/ros/jazzy/share/slam_toolbox/config/…` hizo que un script se matara a sí mismo. Filtra por
algo que no pueda estar en tu propia línea de comandos (`lib/slam_toolbox/async_slam_toolbox_node`)
y excluye `$$` y `$PPID`.

**Un robot QUIETO produce un mapa 92.9 % desconocido, y no es un fallo.** Con
`min_pass_through: 2` una celda necesita **dos rayos** para marcarse, y los rayos de un LIDAR
quieto divergen: solo las celdas cercanas reciben dos. Además `minimum_travel_distance: 0.3`
hace que el grafo tenga **un solo nodo** si el robot no se mueve. No ajustes el solver: mueve
el robot, con `mediciones_banco/medir_slam_ros2.py`.

**`/slam_toolbox/save_map` falla con `result=255` porque no está Nav2.** El error real no está
en la respuesta del servicio, está en el log de slam_toolbox: `Package 'nav2_map_server' not
found`. Este sistema tiene `ros-jazzy-ros-base` y Nav2 llega en la Fase 5.
→ Usa **`serialize_map`** (`.posegraph` + `.data`), que es nativo y no necesita Nav2:
  `result=0`. El `.pgm`+`.yaml` de `save_map` solo hace falta para dárselo a Nav2.

**No reinicies el driver por debajo de un `slam_toolbox` ya arrancado.** Se queda con un hueco
en su buffer TF y con el `odom` anterior, y **deja de procesar**: el mapa sale idéntico celda
a celda tras mover el robot 80 cm. Invalidó una prueba entera de la Fase 4. Arranca los dos
juntos, `robot.launch.py` primero.

**🔴 `colcon build` desde el directorio equivocado dice «Finished» y NO instala nada.**
Si lo lanzas desde `~/atriz_ws/src/Atriz_rvr` en vez de la raíz `~/atriz_ws`, colcon crea
**ahí dentro** un workspace parásito (`build/`, `install/`, `log/`), compila contra él, y el
cambio **nunca llega al sistema que estás ejecutando**. El mensaje de éxito es idéntico.
Pasó **dos veces** el 2026-07-31 y costó dar por fallida una corrección que estaba bien.
→ **Comprueba el efecto, no el mensaje:** `grep` el cambio en el fichero **instalado**, con
  **ruta absoluta** — si usas ruta relativa acabas mirando el install parásito:
```bash
cd ~/atriz_ws && colcon build --packages-select atriz_rvr_driver
grep -c 'lo_que_cambiaste' \
  /home/sphero/atriz_ws/install/atriz_rvr_driver/lib/python3.12/site-packages/atriz_rvr_driver/rvr_driver_node.py
ls -d ~/atriz_ws/src/*/build 2>/dev/null && echo "🔴 hay workspace parásito: bórralo"
```

**Un `nohup ... &` desde una herramienta Bash muere con el shell.** Si necesitas dejar un
launch corriendo entre llamadas, usa `setsid nohup … < /dev/null &` y `disown`. Sin eso el
proceso desaparece y el diagnóstico siguiente miente.

**El `frequency` del X2 no hace nada.** Se pide 10 Hz y gira a 10.1–11.75. Medido sin driver:
11.48 Hz. Es de canal único y el motor va libre. **La mejora de resolución angular bajando el
giro a 7 Hz, que propone el manual 8.3, no es alcanzable por software.**

**🔴 `Velocity` viene en el MARCO DEL MUNDO, no en el del robot — y el driver lo copia mal.**

Durante un tiempo este fichero decía que el stream era «basura» porque reportaba 0.001 m/s con
el robot a 0.147 m/s reales. **Esa conclusión era falsa y se retractó el 2026-07-31.** Medido
con el robot avanzando recto:

```
dirección del desplazamiento del locator:  +90.2°
dirección del vector Velocity:             +90.1°     ← 0.1° de diferencia
módulo real 0.199 m/s  ·  Velocity 0.200   ← 0 % de error
```

El stream es **exacto**. Lo que falla es leer solo `Velocity.X` con el robot encarado a ~90°
del eje X del locator: ahí X vale ~0 mientras el robot cruza la habitación.

→ **Bug real en el driver:** copia `Velocity.X` a `odom.twist.twist.linear.x`, que ROS define
  en el marco del **robot** (`child_frame_id`). Medido: publica `(-0.000, -0.200)` donde debería
  poner `(+0.199, 0.000)`. Arreglo: proyectar sobre el rumbo —
  `vx = vx_w·cos(yaw) + vy_w·sin(yaw)`.

**🔴🔴 EL MODELO DE MARCOS DEL RVR — medido con cinco pruebas el 2026-07-31.** Es lo que hay
que tener en la cabeza antes de tocar `/odom`:

1. **El marco del LOCATOR es FIJO** (no gira con el robot) y **se realinea en cada
   `reset_locator_x_and_y()`**, o sea al arrancar el driver. Su eje X queda **90° girado**
   respecto al «adelante» del robot: por eso **avanzar recto SIEMPRE da −90°**.
2. **El yaw se pone a cero al ENCENDER el RVR, no con `reset_yaw()`** — que no hace nada.
   Arrastra su origen desde el encendido, así que es arbitrario respecto al locator. Con un
   encendido limpio y sin tocar el robot: **+0.5°**. Tras manipularlo: −74.6°, +64.9°.
3. **La posición y la orientación de `/odom` tienen MANOS CONTRARIAS.** Girando el robot, el
   yaw cambió **+89.4°** y el desplazamiento **−88.8°**. **El `−Y` que el driver aplica al
   locator sobra.**

**El yaw es el bueno**: está contrastado contra el LIDAR, un sensor físico con convención ROS
conocida (`verificar_inverted_lidar.py`: +48.5° contra −49.0°, opuestos). El `−Y` vino de una
**inferencia inválida** — se dedujo midiendo que «al curvar a la izquierda `dy` salía negativo»,
dando por hecho que el eje X del locator apuntaba adelante, y está 90° girado.

**ARREGLO, tres piezas, y NO se implementan de golpe:**

| | Qué hacer |
|---|---|
| Posición | quitar el `−Y` del locator y **rotar −90°** |
| Velocidad | la misma rotación, y proyectar sobre el rumbo |
| Orientación | restar el yaw del arranque (`yaw − yaw₀`) |

**Verificación:** una corrida recta debe dar la dirección del desplazamiento **igual** al yaw
publicado, y girar el robot debe mover ambas en el **mismo** sentido. Hoy fallan las dos.
Detalle completo en `00_auditoria/evidencia_24_04/15_velocidad_odom.txt`.

**`Speed` (escalar) existe y es el módulo de `Velocity`.** Sirve como comprobación cruzada
barata, pero no aporta nada nuevo.

**Los encoders funcionan y están calibrados: 7792 ticks/m**, contra cinta métrica. Son la única
fuente que **no depende del marco de referencia**.

**El locator acierta con 1 mm en 1 m** (101.1 medidos contra 101.0 de cinta). Es la referencia
válida para todo lo demás.

✅ **VELOCIDADES MÁXIMAS REALES, medidas con el perfil en el tiempo** (2026-07-31):

| | Comandado | Meseta real | Se alcanza en |
|---|---|---|---|
| lineal | 0.20 m/s | **0.199** (100 %) | ~0.5 s |
| lineal | 0.40 m/s | **0.401** (100 %) | ~0.5 s |
| angular | 0.5 → 2.0 rad/s | **99–102 %** en las cuatro | inmediato |

⚠️ **RETRACTADO:** este fichero afirmó que «el robot no alcanza la velocidad comandada:
0.10→87 %, 0.40→63 %». **Es falso.** La ventana de medida incluía el período posterior a la
frenada, y hundía la media. Lo que sí existe es una **rampa de aceleración de ~0.5 s**: importa
para Nav2, pero no es un tope.

**`drive_rc_si_units` frena mucho mejor que `drive_with_heading`.** Deriva tras `drive_stop`:
**1.1 cm** contra **11.3 cm**. Por eso el driver usa el primero.

**Una herramienta miente** (antes eran dos). `scripts/lydar/test_lidar.py` (en `Atriz_rvr`)
reporta «Tipo de LIDAR: Desconocido» con datos perfectamente válidos — mira «bytes recibidos»
y «tasa de datos», no el tipo.
✅ `x2_parse.py` **ya está corregido** (2026-07-30): imprimía frecuencias de giro absurdas
(480 Hz, luego 741 Hz) porque promediaba intervalos de llegada de paquetes que salen a
ráfagas del buffer USB. Ahora cuenta vueltas y da 11.48 Hz. La lección que queda:
**un timestamp tomado al leer de un buffer no mide cuándo ocurrió el evento.**

---

## Herramientas de diagnóstico — úsalas antes de teorizar

En `00_auditoria/evidencia/mediciones_banco/`:

```bash
raw_uart.py      # ¿contesta el RVR a nivel de bytes?  <- EL MÁS ÚTIL
x2_parse.py      # ¿funciona el LIDAR? (sin driver ROS)
medir.py         # frecuencia y jitter de /odom e /imu
sdk_full.py 60   # ritmo del SDK con los 8 sensores
estabilidad.py   # 12 min: huecos, pérdidas, fugas de memoria

verificar_leds_sensores.py   # 37 comprobaciones de LEDs y los 17 sensores (sin ROS)
medir_watchdog_ros2.py       # ¿frena el watchdog? mide DESPLAZAMIENTO, no velocidad
medir_slam_ros2.py           # ⚠️ MUEVE EL ROBOT: ¿crece el mapa al moverse?
medir_keepalive_ros2.py      # ¿se duerme el RVR? vigila el RITMO de /odom, no el topic
caracterizar_deriva_slam.py  # ⚠️ MUEVE EL ROBOT 20 min: 6 corridas -> distribución de la deriva
medir_slam_ros2.py           # ⚠️ MUEVE EL ROBOT ~1.3 m: ¿crece el mapa? (girar NO vale)
verificar_inverted_lidar.py  # ⚠️ gira 50°: ¿se contradicen /scan y /odom?
```

⚠️ **`medir_slam_ros2.py` necesita espacio, y el robot NO esquiva obstáculos** (solo tiene
watchdog). Con el robot en el centro: **1 m por delante** (hacia donde mira), **1 m por
detrás**, **40 cm a cada lado**. El LIDAR va a 17.5 cm barriendo en horizontal, así que pasa
por encima de zócalos y cajas bajas: «despejado a ras de suelo» no basta.

En `scripts/`:

```bash
fase_0_1_fix_uart.sh          # repara el UART (sudo + reinicio)
fase_1_higiene_so.sh          # headless, governor, journal, WiFi (sudo)
fase_0_3_respaldo.sh          # prepara la SD antes de reflashear
fase_1_validar_sdk_py312.py   # GO/NO-GO de la migración
diag_uart_pins.sh             # último recurso: lee GPFSEL del chip
```

---

## Valores de referencia medidos — si te desvías, algo cambió

| Métrica | Esperado | Medido el |
|---|---|---|
| `/odom` | **16.59 Hz**, σ 2.5 ms | 2026-07-29, 12 min sin huecos |
| `/scan` | ~10 Hz, 2998 muestras/s | 2026-07-29, 100 % checksums |
| CPU del driver | ~29.5 % de un núcleo | Pi 4 |
| RAM del driver | ~53 MB, plana | sin fugas en 12 min |
| Temperatura | 55–58 °C | con el driver activo |
| Puerto del RVR | `/dev/rvr` → `ttyAMA0` (PL011) | |
| Puerto del LIDAR | `/dev/ydlidar` → `ttyUSB0` (CP2102, serie `0001` genérico) | regla udev por `ID_PATH` |
| `/scan` | **10.1 Hz**, 255 puntos, 226 válidos (89 %), resolución **1.42°** | 2026-07-30, con el driver ROS 2 |
| Firmware del RVR | 9.1.462 (Nordic) | |
| `/map` | **0.200 Hz** exactos (= `map_update_interval` 5 s) | 2026-07-30 |
| **Timeout de inactividad del RVR** | **300.6 s = 5.01 min** (dos medidas idénticas) | 2026-07-31 |
| `/battery_state` | cada **30.0 s** exactos — es el latido del keepalive | 2026-07-31 |
| Enlace con keepalive | **12 min, 0 huecos** en `/odom`, 16.54 Hz | 2026-07-31 |
| **Deriva de SLAM** | mediana **1.0 cm** (1.6 m de recorrido) y **2.7 cm** (2.4 m); peor caso 3.2 cm, n=6 | 2026-07-31 |
| CPU de `slam_toolbox` | **4.5 %** de un núcleo, 49 MB | 2026-07-30, async |
| Todo a la vez (driver+LIDAR+RSP+SLAM) | **~24 %** de un núcleo, ~200 MB, loadavg 0.62, 62.3 °C, `throttled=0x0` | 2026-07-30 |

**SLAM sale barato.** El presupuesto de CPU de este robot lo consume el driver del RVR
(15.9 %), no `slam_toolbox` (4.5 %). Subir `throttle_scans` o `minimum_travel_distance` para
«aliviar el Pi 4» sería optimizar lo que no cuesta.

**Línea base de Ubuntu Server 24.04 recién instalado** (2026-07-30, *antes* de la higiene del
SO). Evidencia cruda en `00_auditoria/evidencia_24_04/`:

| Métrica | 20.04 (sistema viejo) | 24.04 recién instalado | Objetivo tras la higiene |
|---|---|---|---|
| Arranque, userspace | 29.5 s | **1 min 39 s** (`cloud-final` = 1 min 7 s) | < 15 s |
| Tareas | 273 | **187** | < 120 |
| `io.full total` | 47 s / 42 min | **74.6 s / 34 min** | mucho menor |
| Journal | 784 MB | 17.7 MB | decenas de MB |
| Governor | `ondemand` | `ondemand` | `performance` |
| Default target | `graphical.target` | `graphical.target` (sí, en Server) | `multi-user.target` |
| Temperatura | 59.9 °C | 63.7 °C, `throttled=0x0` | — |
| `iw` | instalado | **no instalado** | instalado |

⚠️ **No compares 24.04 contra la línea base de 20.04.** Son dos sistemas distintos:
`00_auditoria/evidencia/` es el viejo, `00_auditoria/evidencia_24_04/` el nuevo. Mezclarlos es
lo que produce deriva entre documentación y realidad.

**Límites del hardware, no negociables:**
- El firmware del RVR **no baja de `interval=60` ms** (16.5 Hz) y cuantiza a múltiplos de 20 ms.
- El X2 entrega ~3000 muestras/s repartidas según la velocidad de giro: más lento = más
  resolución angular.

---

## Decisiones ya tomadas — no las vuelvas a plantear

| Decisión | Razonada en |
|---|---|
| Ubuntu Server 24.04 + ROS 2 Jazzy (soporte a mayo 2029) | plan, Contexto |
| Reinstalar sobre la misma microSD; reversión por imagen `dd` | plan, Fase 0.3 |
| **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total | `ARQUITECTURA.md`, D1 |
| La web habla por **rosbridge**, no por SSH | `ARQUITECTURA.md`, D2 |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final** | decisión del usuario |
| `ros-jazzy-ros-base`, **NO** `desktop` | Server headless; RViz2 va en un portátil |
| **`ros-jazzy-navigation2`, NO `ros-jazzy-nav2-bringup`** | `bringup` depende de `nav2-minimal-tb3-sim`, `tb4-sim` y `ros-gz-sim`: **312 paquetes** de simulador y dos TurtleBots en un robot real, incluido `pocketsphinx-en-us`. Los launch los escribimos nosotros, como con `slam_toolbox` |
| **Imagen dorada** para los 16, no aprovisionar por red | ~300 MB y 15-20 min por robot, sobre la única AP. `FLOTA.md` |
| La imagen dorada se **construye ejecutando `provision.sh`**, no a mano | Una imagen irreproducible es una caja negra. `FLOTA.md` |
| **🟢 GO: el SDK funciona en Python 3.12** (16.67 Hz) | manual, cap. 5.1 · verificado 2026-07-30 |
| El driver publica `odom → base_footprint`, **no** `odom → base_link` | manual, cap. 9.4 · REP-105 y un frame = un padre |
| `async_slam_toolbox_node`, no el `sync` | no bloquea por barrido, y cuesta 4.5 % · manual cap. 9 |
| SLAM va en un launch **aparte** de `robot.launch.py` | el robot tiene que arrancar sin SLAM, y SLAM reiniciarse sin soltar `/dev/rvr` |

---

## Estilo de trabajo que espera el usuario

- **Español.** Toda la documentación y la comunicación.
- **Evidencia antes de afirmaciones.** Si dices que algo funciona, muestra la salida del
  comando que lo demuestra.
- **Corrige tus propios errores en voz alta.** En este proyecto se han retirado tres
  hallazgos de auditoría por estar equivocados, y eso es preferible a dejarlos.
- **Los pasos que requieren `sudo`, apagar la Pi o un PC externo los ejecuta el usuario**,
  no tú. Prepáraselos como script o comando exacto.
- **Avisa de las acciones físicas.** Despertar el robot enciende sus LEDs y gasta batería;
  cuando termines una prueba, para el nodo.

---

## Cómo saber en qué punto estás

### Primero: pasa el verificador. Un comando en vez de veinticinco.

```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```

**48 aserciones**, código de salida ≠ 0 si algo falla, y cada fallo viene con el comando que lo
arregla. Existe porque el 2026-07-30 se verificó este robot a mano con ~25 comandos y
aparecieron **cinco fallos silenciosos**. No repitas eso: pásalo al empezar y al cerrar.

Su regla es **comprobar el efecto, no la intención**. Si añades comprobaciones, mantenla.

### Los tres scripts de la flota

| Script | Dónde corre | Para qué |
|---|---|---|
| `preparar_tarjeta.sh --id NN` | en el **PC** | Tarjeta recién grabada: `cmdline.txt`, `config.txt`, `robot_id.txt` |
| `provision.sh` | en el robot | De un 24.04 limpio a robot terminado. Idempotente: sirve para actualizar |
| `verificar_robot.sh` | en el robot | Decide si el robot está listo |

**La imagen dorada es el atajo; `provision.sh` es la verdad.** Si divergen, gana el script y se
reconstruye la imagen. Procedimiento completo en `03_operacion/FLOTA.md`.

### Y luego el contexto

```bash
cat TRASPASO.md | head -60          # estado y siguiente paso
git -C ~/atriz_migracion log --oneline -10
git -C ~/atriz_ws/src/Atriz_rvr branch -vv    # (o ~/atriz_git si aún es ROS 1)
ls -l /dev/rvr /dev/ttyUSB0         # ¿está el hardware?
lsb_release -ds; uname -r           # ¿20.04+Noetic o 24.04+Jazzy? ¿qué kernel?
cat /proc/device-tree/aliases/uart0 # ¿está el PL011 en GPIO14/15?
```

### Antes de subir nada: comprueba que PUEDES subir

En un sistema recién instalado no hay credenciales de git, y el repositorio es privado.
`git fetch` falla con `could not read Username` y los commits se quedan solo en la tarjeta —
exactamente el riesgo que este proyecto ya sufrió con un stash.

```bash
git -C ~/atriz_migracion fetch origin && echo "OK: hay credenciales"
```

Si falla, es la persona quien lo arregla (el token es un secreto, no se pone en el repo ni se
teclea en un comando que quede en el historial):

```bash
git config --global credential.helper 'store --file ~/.git-credentials'
cd ~/atriz_migracion && git fetch origin   # Username: Bura-hub · Password: el PAT
chmod 600 ~/.git-credentials
```

`fase_0_3_respaldo.sh` respalda `~/.git-credentials` desde el 2026-07-30, para no repetirlo.
