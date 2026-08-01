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

**🔴 Y EL TRUCO DEL CORCHETE NO BASTA.** Mordió otras dos veces el 2026-07-31, así:

```bash
# Esto se mata a sí mismo, AUNQUE lleve corchete:
for p in $(pgrep -f "nav2\.launch\.p[y]"); do kill -INT $p; done
python3 - <<'EOF'
p = 'atriz_rvr_bringup/launch/nav2.launch.py'   # ← el texto buscado, aquí abajo
EOF
```

El corchete protege de que el patrón **se encuentre a sí mismo**. No protege de que la cadena
buscada aparezca **en otra parte de la misma orden** — un heredoc, una ruta, un `nohup ... &`
más abajo. `pgrep -f` mira la línea de comando **entera** del `bash -c`.

→ **La regla operativa:** no metas en la misma orden un `pgrep -f X` y cualquier otra mención
  de `X`. Mejor todavía, mata sin `-f`:

```bash
# por nombre de proceso exacto (comm, 15 caracteres), nunca por línea de comando
ps -eo pid,ppid,comm | awk '$3=="rvr_driver_node"{print $2}'   # el PID del launch padre
```

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

**`save_map` puede dar 255 sin que falte nada.** El fallo histórico era
`Package 'nav2_map_server' not found` y se arregló instalando `navigation2`. Pero hay un
segundo 255, **intermitente** (medido: falla ~1 de cada 3), con otro mensaje: `Failed to spin
map subscription`. Es una carrera entre el `map_update_interval: 5.0` de slam_toolbox y el
`save_map_timeout: 2.0` del map_saver. → Antes de tocar la instalación, **lee el mensaje en el
log de slam_toolbox**. Y guarda los mapas así, que es lo verificado:
```bash
ros2 run nav2_map_server map_saver_cli -f <ruta> --ros-args -p save_map_timeout:=10.0
```

**🔴 La ficha del Sphero RVR MIENTE sobre este robot, y el URDF la copiaba.** Hasta el
2026-07-31 el modelo decía `0.218 × 0.185 × 0.114` y las tres estaban mal: el robot mide
**18.2 × 21.7 × 7.0 cm** (medido con cinta, con orugas). Largo y ancho estaban **cruzados**, y
el alto tenía **4.4 cm de más** — que es lo que hacía que `laser_z` estuviera 2 cm alto.
→ **Antes de dimensionar nada con el tamaño del robot, mira
[`03_operacion/MEDIDAS_ROBOT.md`](03_operacion/MEDIDAS_ROBOT.md)**: dice qué está medido y qué
viene de una ficha. **Ya está todo medido** salvo `imu_z`, que exige abrir el robot.

**🔴 «Confirmado por tres vías independientes» puede ser una sola vía contada tres veces.** El
proyecto dio por buena una inclinación de ~8° del robot durante días porque la confirmaban el
árbol TF, el Roll de la IMU y el acelerómetro. **Las tres salen de la IMU**: el TF copia
`odom.pose.pose.orientation`, que el driver copia del cuaternión del RVR, que calcula la IMU, y
el acelerómetro es el mismo chip. → **Antes de decir "confirmado por N vías", traza de dónde
sale el dato de cada una.**

**🔴 Y la inclinación costó DOS conclusiones retiradas más.** Merece leerse entero el cap. 13,
porque las dos son errores de método fáciles de repetir:
- «El LIDAR está nivelado en 4 puntos, luego el robot está horizontal» — **la regla mide desde
  el SUELO**, así que no distingue «nivelado respecto al chasis» de «horizontal respecto a la
  gravedad».
- «El pitch cambia de signo al girar 180°, luego la inclinación es física» — **el cambio de
  signo solo dice que el error está en el marco del MUNDO**, y eso lo producen dos causas: un
  suelo inclinado **o** una referencia de gravedad torcida.

✅ **Lo que sí lo zanja: el acelerómetro CRUDO no gira con el robot** (`accel.x` −1.091 →
−1.158 tras girar 177.8°) mientras el pitch fusionado sí cambia de signo. Error fijo en el
marco del robot + suelo plano medido con nivel = **el sensor está descalibrado**. Y `|g|` sale
**3.8 % corto**, que lo confirma.

**⚠️ La inclinación del RVR vive en el PITCH (~6.9°), no en el roll (~1°), y los dos SE
REPARTEN SEGÚN EL RUMBO.** Cualquier comprobación que mire solo el roll da un falso negativo —
abortó un experimento de 45 min por eso. Mira siempre `hypot(roll, pitch)`.

✅ **Desde el 2026-07-31 el driver NO la publica**: `publicar_inclinacion` es `false` por
defecto y `/odom` sale con `roll +0.00° pitch +0.00°`. Con `true` se recupera. Si ves 6.9° en
`/odom`, alguien lo ha puesto a `true`.

**🔴 UNA EXCEPCIÓN EN UN MANEJADOR DE TELEMETRÍA MATA `/odom` E `/imu` EN SILENCIO.** Pasó el
2026-07-31 al añadir un parámetro al driver: se usó `self._publicar_inclinacion` sin asignarla
(el nombre de la variable vecina era `_timeout_silencio`, no `_silence_timeout`). Resultado:
`AttributeError` en `_h_quaternion`, **ni una línea en el log**, `/odom` e `/imu` a cero con los
topics existiendo, y `/scan` funcionando.

Y **el detector de silencio NO salta**, por diseño: mide el tiempo desde la última **muestra
del RVR**, no desde la última publicación. Las muestras llegaban — se ve el
`origen del yaw fijado en +10.2°` en el log, que sale de la primera.

→ **Atajo:** si `/scan` va y `/odom` no, **y no hay ningún error ni aviso de silencio**,
sospecha de una excepción dentro de un manejador. El síntoma «el topic existe y no publica» es
idéntico al de un RVR dormido, pero **el RVR dormido sí dispara el detector de silencio**: esa
es la diferencia que los separa.

**📝 `/battery_state.percentage` es una fracción 0–1, no un porcentaje.** Es lo que manda
`sensor_msgs/BatteryState` y el driver lo respeta: `0.34` son **34 %**. Leerlo como 0–100 hace
que un robot al 34 % parezca estar al 0 % — provocó una falsa alarma de batería agotada.

**🔴 EL ROBOT NO VUELVE AL PUNTO DE PARTIDA, y eso invalidaba todas las medidas de deriva.**
Medido el 2026-07-31: **94 cm de deriva en 12 corridas** (~8 cm cada una) hacia delante en una
tanda, y lateralmente hasta quedar **a 5 cm de rozar** en la otra (`der` 0.97 → 0.16 m). Así que
«N repeticiones» era un barrido por posiciones distintas, y con él **el 21 % de las corridas
fallaba** con errores de hasta 56 cm.

✅ **ARREGLADO** con `mediciones_banco/referenciar_posicion.py`, que `caracterizar_deriva_slam.py`
llama antes de cada corrida: ajusta una recta a la pared frontal, conduce a la distancia
objetivo y **luego** se alinea. Resultado: dispersión de posición de ±47 cm a **±3 cm**, y
**0 fallos de 12** con un peor caso de **4.4 cm** (era 56.1).

→ **El orden es distancia y DESPUÉS rumbo.** Al revés, conducir vuelve a torcer el rumbo recién
corregido (+0.41° → +2.53°). Girar sobre el eje no cambia la distancia perpendicular.
→ **No referencies con `/odom` ni con el mapa**: sería circular, es lo que estás midiendo.

**🔴 Y una conclusión de una sola tanda puede ser coherente y falsa.** El 2026-07-31 se concluyó
—con datos limpios— que «SLAM falla el 50 % a 2.3 m y es fiable a 1.6 m». Una réplica del mismo
protocolo, **una hora después**, dio lo contrario: fallaron las cortas y las largas salieron
perfectas. **El fallo cambió de distancia.** → Con un fenómeno intermitente (~21 % aquí),
**replica antes de atribuir**. Manual, cap. 9.12b.

**🔴 `rclpy.spin_once(nodo, …)` EN BUCLE PIERDE MENSAJES: 11.3 Hz sobre un robot que va a
16.5.** Cada llamada engancha el nodo al ejecutor global y lo desengancha al salir; en ese hueco
se pierde lo que llegue. Medido las dos formas el 2026-07-31 sobre el mismo robot en el mismo
minuto. Y la comprobación **pasaba** (el umbral es >10 Hz), así que habría llevado a «arreglar»
un driver sano.
→ Para **contar mensajes**, ejecutor persistente:
```python
ex = SingleThreadedExecutor(); ex.add_node(n)
while ...: ex.spin_once(timeout_sec=0.1)      # 16.5 Hz — el valor real
```
→ Para *conducir* o esperar, `rclpy.spin_once` vale: ahí no se cuenta nada.

**🔴 `ros2 topic hz /odom` DA 0 Hz SIEMPRE, con el robot perfecto.** `/odom` se publica
**BEST_EFFORT** y `ros2 topic hz` se suscribe RELIABLE **sin opción de cambiarlo** en Jazzy. DDS
no empareja y no llega nada. Es la misma trampa de QoS que costó la parada de emergencia, y
estuvo **dentro del verificador** sin que nadie lo notara — porque el bloque solo corría si
`/odom` salía en `ros2 topic list`, y con el driver parado no salía. Una comprobación muerta que
contaba como aprobada.
→ Mide con un suscriptor BEST_EFFORT propio.

**🔴 `ros2 topic echo --no-daemon` FALLA 2 DE CADA 3 VECES con `Could not determine the type
for the passed topic`** — con el topic publicando perfectamente. Tiene que descubrir el tipo por
sí mismo y es una carrera. Y ademas se suscribe RELIABLE, así que en `/scan` o `/odom` no
recibiría nada aunque acertara el tipo.
→ Para comprobar si un topic PUBLICA, escribe un suscriptor: el tipo **se dice**, no se
  descubre, y el QoS se elige. Un comprobador que acierta un tercio de las veces es peor que no
  tenerlo.

**🔴 LOS `setup.bash` DE ROS NO SON COMPATIBLES CON `set -u`** — `AMENT_TRACE_SETUP_FILES:
unbound variable`. Con `set -euo pipefail` matan el script antes de hacer nada, y el mensaje no
menciona ROS. Envuelve los `source` en `set +u` / `set -u`.
→ ⚠️ **Y búscalo en TODOS los scripts, no solo en el que falló.** Se arregló en
  `atriz-robot.sh` y no en `atriz-escaneo.sh`; en el primer arranque real bajo systemd el
  `ExecStartPost` murió con `status=1/FAILURE`, el servicio quedó `active (running)` y el
  barrido del LIDAR se quedó **encendido** — el estado que ese `ExecStartPost` existía para
  evitar.

**🔴 `ros2 topic list` INCLUYE TOPICS DE NODOS MUERTOS.** El daemon los conserva. El verificador
veía `/odom` en la lista con el robot **apagado**, medía 0 y declaraba «el RVR está dormido».
→ Para saber si algo corre, mira el **proceso**: `ps -eo comm | grep -qx rvr_driver_node`.

**🔴 `ps -o %cpu` NO da la CPU instantánea: da el PROMEDIO desde que arrancó el proceso.** Un
nodo recién lanzado sale inflado, y uno que lleva horas sale diluido. Las cifras de CPU
anteriores de este fichero se tomaron con `ps`; `slam_toolbox` vuelve a salir 4.8 % con el
método bueno, así que el orden de magnitud aguanta. → Para comparar procesos, **muestrea
`/proc/<pid>/stat` dos veces** (`utime+stime`) con 20 s de diferencia.

**🔴 AMCL cuesta MÁS que SLAM en este robot**, al revés de lo que se suponía: 8.8 % contra
4.8 %. → **El argumento para AMCL no es la CPU, es el marco compartido**: 16 robots sobre un
mismo `map` es lo que permite que la web diga «ve a la mesa 3». Manual, cap. 14.1.

**📝 `/amcl_pose` no llega con el robot quieto, y no es un fallo.** AMCL solo actualiza tras
moverse `update_min_d` (0.15 m). Mueve el robot antes de dar por roto nada.

**🔴🔴 SI UN NODO MUERE, systemd NO SE ENTERA: EL SERVICIO SIGUE EN VERDE.** El PID principal de
`atriz-robot.service` es el `ros2 launch`, que **sobrevive** a la muerte de uno de sus nodos, así
que `Restart=always` no cubre este caso. Medido el 2026-08-01: un `SyntaxError` dejó el driver
**muerto cuatro minutos** con `systemctl is-active` diciendo **active**.
→ Es el peor modo de fallo para un laboratorio remoto: un robot inservible que **desde fuera
  parece sano**, igual que el RVR dormido con el nodo vivo o el topic registrado y mudo.
→ ✅ Arreglado con **`on_exit=Shutdown()`** en el nodo del driver (`robot.launch.py`). Verificado
  matando solo ese nodo: `NRestarts` 12→13 y el robot entero de vuelta en **25 s**.
→ ✅ **El `collision_monitor` también lo lleva** (decisión del usuario, 2026-08-01), y por una
  razón más fuerte: un robot **sin capa de seguridad que parece sano** es peligroso. Verificado:
  `NRestarts` 14→15, todo de vuelta en 25 s.
→ ⚠️ **El LIDAR NO lo lleva, y no es contradicción:** sin `/scan` el propio `collision_monitor`
  bloquea el movimiento, así que el robot queda **seguro**. Si muere el monitor, queda conduciendo
  **sin filtro**. Son situaciones opuestas.

**🔴 `TRANSIENT_LOCAL` EN EL PUBLICADOR NO GARANTIZA QUE UN SUSCRIPTOR TARDÍO RECIBA EL ÚLTIMO
VALOR.** El driver lo daba por hecho para `/motor_status` y `/battery_state`. Medido: un
suscriptor nuevo se quedaba **sin recibir nada en 10 s, 2 de cada 3 intentos**, con el topic
publicando bien y en su propio proceso.
→ Con el sondeo cada 30 s, eso dejaba a la web **medio minuto a ciegas** sobre un fallo de motor.
→ **Arreglo: republicar el estado a 1 Hz.** Es gratis —no toca el puerto serie— y no depende de
  la semántica de TRANSIENT_LOCAL. El sondeo sigue a 30 s, que es lo que cuesta.

**🔴🔴 EN UN SUSCRIPTOR, `TRANSIENT_LOCAL` NO AÑADE GARANTÍAS: SOLO RESTRINGE CON QUIÉN
EMPAREJA.** Exige que el publicador también lo sea, y **ninguno lo es por defecto** — ni
`ros2 topic pub`, ni rosbridge. La parada de emergencia del driver estaba suscrita
`RELIABLE + TRANSIENT_LOCAL` «para que un suscriptor que llegue tarde reciba el último estado»,
que es un razonamiento **del publicador**. Resultado: `incompatible QoS […] No messages will be
received`. → En un suscriptor usa **VOLATILE**, que empareja con todo; la fiabilidad la da
`RELIABLE`. Manual, cap. 15.1.

**🔴 Y LA CUARTA VEZ FALLÓ AL SOLTARLA, NO AL PULSARLA.** El enunciado «la parada no cancela
Nav2, solo para los motores» era **falso**: la bandera del driver descarta todo `cmd_vel`, así
que el robot sí se queda quieto. Lo que no hacía nadie era **cancelar el objetivo**, y
`/release_emergency_stop` solo baja la bandera → **al liberarla el robot arrancaba solo**,
porque el `controller_server` nunca dejó de publicar y el progress checker está relajado a
0.25 m en 15 s. → Arreglado con el nodo `cancelar_nav2` (en `nav2.launch.py`, no en el driver:
el driver tiene que funcionar sin Nav2). ✅ **Verificado con control**: con el nodo, objetivo
`CANCELED` y **0.0 cm** al liberar; sin él, objetivo **ACTIVO** y **34.7 cm** — arrancó solo.
Manual, cap. 15.4.

**🔴 La parada de emergencia ha fallado TRES veces, siempre en silencio y con `200 OK`.**
(1) nombre de topic distinto, en ROS 1. (2) **namespace**: al portar se arregló el nombre y se
coló el `/rvr/`. (3) **QoS**. → Las causas 2 y 3 **solo aparecen publicando de verdad**: leer el
código da el nombre pero no el namespace resuelto ni el QoS. **Publica y mira el log del
driver.**

**El X2 no ve un objeto fino en un solo barrido.** A 0.68 m tira un rayo cada 1.7 cm, así que
un objeto de 5 cm da 2-3 puntos y en un barrido suelto puede desaparecer. → Para geometría
fina, **acumula 6-8 s de barridos y toma la mediana por sector angular**. Un `/scan` suelto no
basta, y hace dudar de `min_points: 2` con obstáculos así.

**Una capa de seguridad hace abortar a Nav2 por «no progresar».** El `SimpleProgressChecker`
de fábrica exige 0.5 m en 10 s; el `collision_monitor` frena al 40 % y `approach` baja más la
velocidad junto a un obstáculo, así que salta `Failed to make progress` con el robot
funcionando bien. → **Ir despacio ya no es prueba de estar atascado**: relajado a 0.25 m en
15 s (manual, cap. 11.13).

**⚠️ DOS COMPROBACIONES DE LA HIGIENE DEL SO QUE PARECEN FALLAR Y NO FALLAN.** Las dos hacen
pensar que `fase_1_higiene_so.sh` no funcionó, con el sistema perfecto:
- **`systemctl is-enabled cloud-init` dice `enabled`.** cloud-init se desactiva con el **fichero**
  `/etc/cloud/cloud-init.disabled`, no con systemctl. Lo que cuenta es que `cloud-init`,
  `cloud-config` y `cloud-final` estén **`inactive`**.
- **`ps -e | wc -l` da ~166 contra el objetivo «< 120».** **86 de esas tareas son de
  `atriz-robot.service`** — el SO solo tiene **80**. Y el objetivo original estaba mal planteado
  de todos modos: `ps -e` cuenta ~123 **hilos de kernel**, que son el suelo del sistema.
  `verificar_robot.sh` ya lo mide bien (procesos de usuario, excluyendo `ppid==2`).

**`unattended-upgrades` viene ACTIVO y actualiza el kernel solo.** Durante la instalación del
2026-07-30 metió 8 lotes de paquetes en 4 minutos, incluido `linux-image-6.8.0-1060-raspi`
sobre un sistema corriendo el 1047. **Cierra las actualizaciones y reinicia antes de tocar el
device-tree**, o un mismo reinicio aplicará dos cambios y no podrás atribuir un fallo
posterior. `fase_1_higiene_so.sh` lo deshabilita.

**`/etc/netplan/*.yaml` puede venir con permisos `644`** — contiene la PSK del WiFi en texto
plano. En 20.04 estaba así; en la imagen de **Server 24.04 ya viene `600`**. Compruébalo, no
lo asumas en ninguna de las dos direcciones. `fase_1_higiene_so.sh` lo corrige si hace falta.

**✅ LOS DOS SENSORES ÓPTICOS FUNCIONAN, Y SON DOS SENSORES DISTINTOS.** Caracterizados el
2026-08-01 (evidencia 37, manual cap. 18.4):
- **Color:** con `color_detection:=true`, `clear` recorre **12.6×** entre blanco y negro, el rojo
  dispara R/G de 0.48 a **2.74**, el azul sube B/G a **0.86**, y `/color` acierta los cinco
  (suelo, blanco, rojo, azul, negro). Normaliza por **G**: es el canal más sensible.
- **Luz ambiente:** es **otro sensor, en otro sitio**, y **NO depende de `color_detection`**.
  ⚠️ **Ve los LEDs del propio robot** —encenderlos todos la sube de 1.76 a **23.55**, 13.3×—
  mientras el RGBC da valores **idénticos** con los LEDs en rojo, verde o azul.
  ✅ **El porqué es físico y lo aportó el usuario:** el sensor mira **hacia arriba**, y el **piso
  blanco que sostiene el LIDAR** (4.6 cm, `MEDIDAS_ROBOT.md`) le devuelve la luz de esos LEDs.
  🔴 **DECISIÓN: `/ambient_light` NO SE USA.** En este montaje un valor alto significa «el robot
  tiene LEDs encendidos», no «hay luz». Se deja publicado porque es gratis, pero **ningún
  consumidor debe apoyarse en él**. No se arregla con software y no hace falta para nada.
- 🔴 La **`confianza` de `/color` es siempre 0**: es el **clasificador**, que necesita una
  **paleta**. `load_color_palette` y `set_active_color_palette` existen en el SDK y no se usan.

**🔴 Y ESTO COSTÓ DOS AFIRMACIONES FALSAS Y DOS MONTAJES QUE MENTÍAN:**
- «da 0.0 sin `color_detection`» — las lecturas de 0.0 se tomaron **con el robot sin levantar**,
  y lo confirmó el usuario **después**. → **Si tu medida depende de que alguien haga algo físico,
  pregunta si lo hizo antes de concluir.**
- «los reinicios degradan el stream» — era el **apagado limpio apagando los LEDs**. Lo propuso el
  usuario y la medida le dio la razón.
- **pegar el objeto contra la ventana tapa también el LED**: el blanco daba menos que el negro.
- deslizar papel sin comprobar que tapa la ventana: dio números **idénticos** a la referencia.
  **Idéntico no es parecido — es la señal de que no cambiaste nada.**

**🔴 `undercarriage_white` NO ENCIENDE EL LED DE LOS BAJOS, y devuelve `success=True`.** Lo
enciende **`enable_color_detection`**. Medido con el sensor de luz como testigo.

**🔴 `set_all_leds` ESPERA UN VALOR DE BRILLO POR BIT DEL GRUPO, no siempre tres.** `led_group` es
una máscara: los 10 grupos normales tienen **3 bits**, `all_lights` **30** y `undercarriage_white`
**1**. Mandar tres a los dos últimos **no da error**: el RVR lo acepta y no hace nada. Lo
encontró el ojo del usuario, no el código. Arreglado contando bits.

**🔴 Las claves del stream de encoders son `LeftTicks`/`RightTicks`, NO `Left`/`Right`** — la
tabla de documentación del propio SDK dice otra cosa que el payload. Con las claves malas el
handler lanza `KeyError` y el topic queda **registrado con cero mensajes**: el síntoma exacto de
un RVR dormido. Y **los ticks vienen sin signo en 32 bits**: un retroceso llega como `4294965940`,
que son **−1356**.

**🔴🔴 EL SENSOR DE COLOR NO DA NADA SIN SU LUZ, y `/color` publicó `[0,0,0]` durante meses.**
Medido el 2026-07-31: canal claro **4 con la luz apagada contra 741 encendida** — 185×. Y el
driver **nunca la encendía**: el topic existía, publicaba a 16 Hz, y el dato era oscuridad.
→ Se enciende con `robot.launch.py color_detection:=true`, **por defecto false** porque deja un
LED blanco bajo el chasis. Con false el driver lo **avisa por el log**.

**🔴 Y NO SE PUEDE ENCENDER BAJO DEMANDA:** con el streaming de `color_detection` ya
configurado, `enable_color_detection` **no hace nada** — 481 mensajes de `/color`, todos ceros,
durante la llamada. Hay que encenderlo **ANTES** de `add_sensor_data_handler`. Manual, cap. 16.2.

**📝 `ros2 service list` NO es autoritativo.** Omitió `set_drive_parameters` (17 de 18) mientras
`ros2 service type` sí lo encontraba y un cliente con `wait_for_service` decía disponible. Es
descubrimiento de DDS. → **Para saber si un servicio existe, usa un cliente.**

**⚠️ Los servicios de movimiento del driver SE SALTAN el `collision_monitor` y el watchdog.**
No publican en ningún topic: hablan al RVR por el puerto serie. Lo único que los para es la
**parada de emergencia** (verificado). Y `raw_motors` no tiene corte automático: sigue hasta que
se le manda modo 0.

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

**🔴 LAS NOTIFICACIONES DE MOTOR NO LLEGAN, PERO LAS CONSULTAS SÍ.** `enable_motor_stall_notify`,
`enable_motor_fault_notify` y la térmica se registran sin error y **no emiten ni un mensaje**:
comprobado el 2026-08-01 forzando los motores a 220/255 con el robot sujeto, y esperando 100 s la
térmica —que debería llegar sola— sin recibir nada. Es el mismo caso que `core_time`.
→ **Sondea**: `get_motor_fault_state()` y `get_motor_thermal_protection_status()` **sí responden**
  (27.9 / 27.7 °C). El driver lo hace cada 30 s y publica **`/motor_status`**.
→ ⚠️ **El atasco se queda sin cubrir**: el SDK no tiene `get_motor_stall_state`. Por eso
  `antiguedad_atasco_s` vale **-1.0** — «no se sabe», que no es lo mismo que «no hay atasco».

**🔴 CAMBIAR UN `.msg` NO BASTA CON `colcon build`.** Se añadió un campo, el build dijo
«2 packages finished», y el `.msg` **instalado** seguía sin él: el suscriptor daba
`AttributeError`. → Borra `build/` e `install/` del paquete de mensajes y recompila (~4.5 min):
```bash
rm -rf build/atriz_rvr_msgs install/atriz_rvr_msgs
colcon build --packages-select atriz_rvr_msgs
grep -c campo_nuevo install/atriz_rvr_msgs/share/atriz_rvr_msgs/msg/X.msg   # el EFECTO
```

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

**🔴🔴 USA `scripts/compilar.sh`, NO `colcon build` A PELO.** El error de compilar desde el
directorio equivocado se cometió **seis veces el 2026-08-01**, en una sola sesión y estando ya
documentado aquí abajo. Un aviso que se ignora seis veces no es un aviso: es una tarea pendiente.
El script se sitúa solo en la raíz, comprueba que compiló **algo**, y detecta el workspace
parásito.
```bash
bash ~/atriz_migracion/scripts/compilar.sh atriz_rvr_driver
bash ~/atriz_migracion/scripts/compilar.sh --limpio atriz_rvr_msgs   # si tocaste un .msg
```

**🔴 NO MEZCLES `rclpy.spin_*(nodo, …)` CON UN EJECUTOR PROPIO.** Si hiciste
`ex.add_node(n)`, todo el giro tiene que ser de `ex` — incluido
`ex.spin_until_future_complete(futuro)`. Llamar a `rclpy.spin_until_future_complete(n, f)` mete
el nodo en el ejecutor **global** y deja de atender tus suscripciones.
→ El 2026-08-01 esto hizo creer durante una hora que **«un comando de LED mata la telemetría»**:
  `/odom`, `/encoders` y la luz caían a 0.0 Hz. Se llegó a aislar quitando código y a concluir
  que el fallo era *preexistente*. **El robot no había dejado de publicar ni un mensaje.** Con el
  ejecutor bien usado: 16.9 → 16.6 → 16.6 → 16.5 Hz.
→ Van **cuatro** veces que el instrumento miente en este proyecto: `ros2 topic hz`, `spin_once`
  en bucle, `mensajes/duración`, y esto. **Ante una medida rara, sospecha del medidor.**

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

**🔴 EL X2 GIRA SIEMPRE, Y AL PONER systemd PASARÁ A GIRAR SIEMPRE **RÁPIDO**.** DTR no
enciende el motor: elige su velocidad. Medido el 2026-07-31, diez tramos alternados y
confirmado por oído: `DTR=1` → **11.8 Hz**, `DTR=0` → **2.7 Hz** (4.3×, checksums 99.8 % en los
dos). Hoy el robot se queda en 2.7 porque no hay nada corriendo; **en cuanto los 16 arranquen
`robot.launch.py` solos, será 11.8 Hz permanentes, 24/7**, se use el robot o no.
→ El driver ya trae **`/stop_scan` y `/start_scan`** (`std_srvs/Empty`), verificados, y frenan
  el motor de verdad — no solo callan el topic. **Las unidades systemd tienen que arrancar con
  el escaneo parado.** La seguridad encaja sola: sin `/scan` el `collision_monitor` no deja
  conducir.
→ ⚠️ `/stop_scan` **no baja de 2.7 Hz**: es el mismo reposo, no un apagado. Pararlo del todo
  exige cortar los 5 V, y la Pi 4 no puede. Manual, cap. 8.4a.

**🔴 NO PUEDES LEER DTR ABRIENDO UN SEGUNDO DESCRIPTOR: EL PROPIO `open()` LA LEVANTA.** Se
intentó comprobar con `TIOCMGET` si `/stop_scan` bajaba DTR, y daba `DTR=1` en los dos estados
→ conclusión «no toca el motor», que era **falsa**. Al validar el lector poniendo `DTR=0` a
propósito seguía diciendo `1`: no solo mentía, **además perturbaba el estado que medía**.
→ **La regla, y es general: antes de creerte un instrumento, pon el sistema en un estado que
  conozcas y comprueba que el instrumento lo ve.** Costó dos minutos y evitó documentar lo
  contrario de lo que pasa.

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
medir_ritmo_ros2.py  # frecuencia y jitter de /odom, /imu y /scan
#                     ⚠️ `medir.py` es de ROS 1 y YA NO ARRANCA (rospy)
sdk_full.py 60   # ritmo del SDK con los 8 sensores
estabilidad.py   # 12 min: huecos, pérdidas, fugas de memoria

verificar_leds_sensores.py   # 37 comprobaciones de LEDs y los 17 sensores (sin ROS)
medir_watchdog_ros2.py       # ¿frena el watchdog? mide DESPLAZAMIENTO, no velocidad
medir_slam_ros2.py           # ⚠️ MUEVE EL ROBOT: ¿crece el mapa al moverse?
medir_keepalive_ros2.py      # ¿se duerme el RVR? vigila el RITMO de /odom, no el topic
caracterizar_deriva_slam.py  # ⚠️ MUEVE EL ROBOT 20 min: 6 corridas -> distribución de la deriva
medir_slam_ros2.py           # ⚠️ MUEVE EL ROBOT ~1.3 m: ¿crece el mapa? (girar NO vale)
verificar_inverted_lidar.py  # ⚠️ gira 50°: ¿se contradicen /scan y /odom?
medir_parada_nav2.py         # ⚠️ MUEVE EL ROBOT ~2 m: ¿arranca solo al LIBERAR la parada?
probar_sensor_optico.py      # color y luz por sus TRES rutas a la vez · --guiado
probar_leds_ros2.py          # ⚠️ ENCIENDE LEDS (no mueve): los 12 grupos, ¿hay comunicación?
probar_rosbridge.py          # cliente WebSocket propio: ¿llega la web? y CUÁNTOS BYTES cuesta
probar_mdns.py               # ¿responde un robot a su nombre .local? · --flota 16
```

⚠️ **`medir_slam_ros2.py` necesita espacio, y el robot NO esquiva obstáculos** (solo tiene
watchdog). Con el robot en el centro: **1 m por delante** (hacia donde mira), **1 m por
detrás**, **40 cm a cada lado**. El LIDAR va a **15.5 cm** ✅ medido barriendo en horizontal, así que pasa
por encima de zócalos y cajas bajas: «despejado a ras de suelo» no basta.

En `scripts/`:

```bash
fase_0_1_fix_uart.sh          # repara el UART (sudo + reinicio)
fase_1_higiene_so.sh          # headless, governor, journal, WiFi (sudo)
fase_0_3_respaldo.sh          # prepara la SD antes de reflashear
fase_1_validar_sdk_py312.py   # GO/NO-GO de la migración
fase_7_systemd.sh --id NN     # arranque automático (sudo) · --simular · --quitar
diag_uart_pins.sh             # último recurso: lee GPFSEL del chip
```

**✅ El robot arranca SOLO desde el 2026-07-31.** `atriz-robot.service`, probado con un reinicio
de verdad. Dos consecuencias que cambian el día a día:

- **Al arrancar NO conduce**, y no está roto: el barrido del lidar arranca **apagado** a
  propósito y sin `/scan` el `collision_monitor` bloquea el movimiento (medido: 0.0 cm contra
  9.9 del control). Se despierta con **`atriz-escaneo on`**.
- **Antes de lanzar `robot.launch.py` a mano, para el servicio**: `sudo systemctl stop
  atriz-robot`. Si no, los dos se pelean por `/dev/rvr`.

---

## Valores de referencia medidos — si te desvías, algo cambió

| Métrica | Esperado | Medido el |
|---|---|---|
| `/odom` | **16.59 Hz**, σ 2.5 ms | 2026-07-29, 12 min sin huecos |
| `/odom` y `/imu` (re-medidos) | **16.53 / 16.49 Hz**, intervalo 60.0 ms mediana, σ 2.2 / 2.6 ms | 2026-07-31, 30 s |
| `/scan` | ~10 Hz, 2998 muestras/s | 2026-07-29, 100 % checksums |
| CPU del driver | ~29.5 % de un núcleo | Pi 4 |
| RAM del driver | ~53 MB, plana | sin fugas en 12 min |
| Temperatura | 55–58 °C | con el driver activo |
| Puerto del RVR | `/dev/rvr` → `ttyAMA0` (PL011) | |
| Puerto del LIDAR | `/dev/ydlidar` → `ttyUSB0` (CP2102, serie `0001` genérico) | regla udev por `ID_PATH` |
| **Giro del X2 en reposo** (nada corriendo, DTR baja) | **2.7 Hz** — sigue midiendo bien | 2026-07-31, n=5 |
| **Giro del X2 escaneando** (DTR alta) | **11.8 Hz** — 4.3× el reposo | 2026-07-31, n=5 |
| `/scan` | **10.1 Hz**, 255 puntos, 226 válidos (89 %), resolución **1.42°** | 2026-07-30, con el driver ROS 2 |
| Firmware del RVR | 9.1.462 (Nordic) | |
| `/map` | **0.200 Hz** exactos (= `map_update_interval` 5 s) | 2026-07-30 |
| **Timeout de inactividad del RVR** | **300.6 s = 5.01 min** (dos medidas idénticas) | 2026-07-31 |
| `/battery_state` | cada **30.0 s** exactos — es el latido del keepalive | 2026-07-31 |
| `/motor_status` | cada **30 s** (mismo latido) · temperatura de motores **27.9 / 27.7 °C** en reposo | 2026-08-01 |
| `/encoders` | **16.57 Hz** · ticks con signo (7792 ticks/m) | 2026-08-01 |
| `/ambient_light` | **13.06 Hz** · ~1.8 con los LEDs apagados, **23.55 con todos encendidos** (13.3×) | 2026-08-01 |
| `/color` (con `color_detection:=true`) | `clear` **181** (negro) → **2288** (blanco), 12.6× · rojo R/G **2.74** · azul B/G **0.86** | 2026-08-01 |
| Enlace con keepalive | **12 min, 0 huecos** en `/odom`, 16.54 Hz | 2026-07-31 |
| **Nav2 navegando** | error final **9–10 cm** (= la tolerancia configurada) | 2026-07-31 |
| Stack COMPLETO (driver+LIDAR+SLAM+Nav2) | **~89 %** de un núcleo, ~477 MB, loadavg 2.53/4, 58.9 °C | 2026-07-31 |
| Nav2 solo | ~58 % de un núcleo — la pieza más pesada | 2026-07-31 |
| **Parada del `collision_monitor`** | **9.9 cm** a 0.25 m/s · **10.6-10.7 cm** a 0.40 (n=2) | 2026-07-31 |
| Nav2 a 0.40 m/s | meseta **0.407 m/s** en 0.9 s · error de objetivo **8 cm** | 2026-07-31 |
| Rodeando un obstáculo | desvío **26–32 cm**, error **8–9 cm**, 4 de 4 SUCCEEDED | 2026-07-31 |
| **Ancho de banda por rosbridge** (JSON) | **80.7 kB/s** navegando (`/scan` es el **83 %**) · **13.6 kB/s** en reposo · ×16 = **10.3 / 1.7 Mbit/s** | 2026-08-01, medido en el robot Y en el navegador |
| **Tamaño del robot** | **18.2 cm** frente-atrás × **21.7 cm** lado-lado, con orugas | 2026-07-31 |
| **Plano de barrido del LIDAR** | **15.5 cm** del suelo ✅ MEDIDO (antes 17.45, derivado) | 2026-07-31 |
| Alto del RVR (suelo → tapa) | **7.0 cm** — la ficha decía 11.4 | 2026-07-31 |
| Radio circunscrito | **0.142 m** → `robot_radius: 0.145` | derivado de lo anterior |
| Paso mínimo con `radius: 0.18` | **no cruza 40 cm** — necesita ~36 cm + margen | 2026-07-31 |
| ✅ **Deriva de SLAM (referenciando)** | mediana **1.55 cm** (1.6 m) y **0.90 cm** (2.3 m) · peor **4.4 cm** · **0 fallos de 12**. NO crece con la distancia | 2026-07-31, n=12 |
| 🔴 Deriva de SLAM **sin** referenciar | **~21 %** de las corridas se iban a 6–56 cm | 2026-07-31, n=24 |
| ✅ **Referenciado de posición** | dispersión **±3 cm** (era ±47 cm) y **±0.2°**. `referenciar_posicion.py` | 2026-07-31 |
| Inclinación que reporta el RVR | **6.9° y está en el PITCH** (roll ~1°), y se reparte con el rumbo | 2026-07-31 |
| `\|g\|` del acelerómetro | **9.435 m/s²** contra 9.807 — **3.8 % corto**, está descalibrado | 2026-07-31 |
| Consumo del RVR conduciendo | **~0.74 %/min** → ~2 h por carga (estimación gruesa) | 2026-07-31 |
| CPU de `slam_toolbox` | **4.8 %** de un núcleo, 49.1 MB (medido desde `/proc`) | 2026-07-31 |
| 🔴 CPU de `amcl` + `map_server` | **8.8 %**, 85.9 MB — **casi el doble que SLAM** | 2026-07-31 |
| AMCL siguiendo la pose | **0.1 cm** en 61.8 cm · **1.1 cm** en 73.4 navegando | 2026-07-31 |
| Todo a la vez (driver+LIDAR+RSP+SLAM) | **~24 %** de un núcleo, ~200 MB, loadavg 0.62, 62.3 °C, `throttled=0x0` | 2026-07-30 |

**SLAM sale barato.** El presupuesto de CPU de este robot lo consume el driver del RVR
(15.9 %), no `slam_toolbox` (4.5 %). Subir `throttle_scans` o `minimum_travel_distance` para
«aliviar el Pi 4» sería optimizar lo que no cuesta.

**Línea base de Ubuntu Server 24.04 recién instalado** (2026-07-30, *antes* de la higiene del
SO). Evidencia cruda en `00_auditoria/evidencia_24_04/`:

| Métrica | 20.04 (sistema viejo) | 24.04 recién instalado | Objetivo tras la higiene |
|---|---|---|---|
| Arranque, userspace | 29.5 s | **1 min 39 s** (`cloud-final` = 1 min 7 s) | < 15 s |
| Tareas | 273 | **187** | ⚠️ `< 120` estaba mal planteado: ver la trampa de abajo |
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
| La web habla por **rosbridge**, no por SSH | `ARQUITECTURA.md`, D2. ⚠️ Y desde el 2026-08-01 **el SSH ya no hace falta ni para el ciclo de vida**: `atriz-robot.service` levanta el robot solo |
| 🔴 **La web publica en `cmd_vel_raw`, NO en `cmd_vel`** | `/cmd_vel` es la SALIDA del `collision_monitor`. Publicar ahí funciona y **salta la seguridad**. `ARQUITECTURA.md` decía `cmd_vel` y se corrigió el 2026-08-01 |
| ⏳ **SIN DECIDIR: namespace `/rvr_NN` o sin namespace** | el diseño decía `/rvr_NN`, el driver corre sin él. Hay que fijarlo **antes** de la Fase 5: cambiarlo después toca los 16 robots y el cliente |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final** | decisión del usuario |
| `ros-jazzy-ros-base`, **NO** `desktop` | Server headless; RViz2 va en un portátil |
| **`ros-jazzy-navigation2`, NO `ros-jazzy-nav2-bringup`** | `bringup` depende de `nav2-minimal-tb3-sim`, `tb4-sim` y `ros-gz-sim`: **312 paquetes** de simulador y dos TurtleBots en un robot real, incluido `pocketsphinx-en-us`. Los launch los escribimos nosotros, como con `slam_toolbox` |
| **Imagen dorada** para los 16, no aprovisionar por red | ~300 MB y 15-20 min por robot, sobre la única AP. `FLOTA.md` |
| La imagen dorada se **construye ejecutando `provision.sh`**, no a mano | Una imagen irreproducible es una caja negra. `FLOTA.md` |
| **`provision.sh` instala `navigation2`** desde el 2026-07-31 | Antes no lo instalaba: un robot aprovisionado con el script no podía navegar, ni tenía capa de seguridad, ni localización |
| ✅ **El camino web ↔ robot está verificado de extremo a extremo** | Navegador del PC → `ws://rvr-01.local:9090` → topics **y** servicios. `03_operacion/probar_conexion_web.html`, sin librerías ni CDN. La web **no necesita SSH para nada operativo**. Evidencia 39 |
| ✅ **La web localiza a los robots por `rvr-NN.local` (mDNS)**, con la IP como override | Es lo que hace que el mismo código funcione en casa y en el laboratorio sin tocar nada. Verificado el 2026-08-01 desde el PC del usuario: avahi publica **A=192.168.1.58 y AAAA link-local**, y rosbridge escucha en **las dos familias**. Evidencia 39 |
| 🔴 **NO se reflashea rvr-01 para probar `provision.sh` entero** | Es el único robot montado. Decisión del usuario el 2026-07-31: se **asume** que funciona hasta tener una tarjeta de repuesto. **Es una suposición, no un hecho** — ver abajo |
| **🟢 GO: el SDK funciona en Python 3.12** (16.67 Hz) | manual, cap. 5.1 · verificado 2026-07-30 |
| El driver publica `odom → base_footprint`, **no** `odom → base_link` | manual, cap. 9.4 · REP-105 y un frame = un padre |
| `async_slam_toolbox_node`, no el `sync` | no bloquea por barrido, y cuesta 4.5 % · manual cap. 9 |
| SLAM va en un launch **aparte** de `robot.launch.py` | el robot tiene que arrancar sin SLAM, y SLAM reiniciarse sin soltar `/dev/rvr` |
| **`localizacion.launch.py` es EXCLUYENTE con `slam.launch.py`** y lo comprueba al arrancar | los dos publican `map → odom`; juntos parten el árbol TF sin dar error. Manual, cap. 14.2 |
| 🔴 **`/ambient_light` NO SE USA** | el sensor mira hacia arriba y el **piso blanco del LIDAR** le refleja los LEDs del propio robot (13.3×). Un valor alto significa «el robot tiene LEDs encendidos», no «hay luz». Se probó, responde, y no sirve en este montaje. Decisión del usuario, 2026-08-01 |
| **La salud de motores se SONDEA, no se escucha** | las notificaciones del SDK no llegan en este firmware (medido); las consultas directas sí. `/motor_status`, evidencia 35 |
| **El driver publica la orientación PLANA** (`publicar_inclinacion: false`) | la inclinación de 6.9° del RVR es un artefacto de su acelerómetro descalibrado, no del robot: suelo plano medido con nivel y error fijo en el marco del robot. Manual, cap. 13 |
| ✅ **`provision.sh` instala el arranque automático** (paso 8/9) desde el 2026-08-01 | Antes no, a propósito: un servicio levantado peleaba por `/dev/rvr` con las pruebas a mano. Se añadió al desaparecer esa razón y para cerrar la **divergencia** con la imagen dorada —que sí lo lleva, porque un `dd` copia todo— y la regla dice que gana el script. Evidencia 38 |
| **Las unidades systemd arrancarán con el lidar PARADO** (`/stop_scan`) | si no, el X2 gira a 11.8 Hz 24/7 en los 16 robots en vez de a 2.7. Manual, cap. 8.4a |
| **NO se mide ahora el consumo del lidar** entre 11.8 y 2.7 Hz | serían horas de robot con `/battery_state` para un número que solo decide un matiz del systemd. Se anota **NO MEDIDO**. Decisión del usuario, 2026-07-31 |
| **NO se persigue el efecto del roll en la deriva** | medido ~1 cm sin significación (p=0.142). Cerrarlo costaría ~62 corridas y 5 h de robot, para 1 cm sobre una tolerancia de objetivo de 10. Decisión del usuario, 2026-07-31 |

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

**94 aserciones** con `--hardware` ✅ medido 2026-08-01, 0 fallos, código de salida ≠ 0 si algo falla, y cada
fallo viene con el comando que lo arregla. Existe porque el 2026-07-30 se verificó este robot a
mano con ~25 comandos y aparecieron **cinco fallos silenciosos**. No repitas eso: pásalo al
empezar y al cerrar.

⚠️ **Y el verificador también se equivoca: lleva SEIS fallos propios**, todos del 2026-07-31 y
todos dando veredictos falsos sobre un robot sano.

Por la mañana: comprobaba el driver de **ROS 1** (que sigue en el repo, así que pasaba mirando un
fichero que no se ejecuta), contaba un **comentario** como si fuera un ajuste, y daba el LIDAR
por roto cuando el driver tenía el puerto ocupado.

Por la tarde, y peores: guardaba la comprobación de `/odom` con `ros2 topic list` —que **conserva
topics de nodos muertos**— y gritaba «el RVR está dormido» sobre un robot **apagado**; usaba
`ros2 topic hz`, que **no puede medir `/odom`** y nunca pudo (QoS), una comprobación muerta que
contaba como aprobada; y el arreglo de eso medía **11.3 Hz sobre un robot a 16.5**, y *pasaba*.

Y **dos más al revisar que todo estuviera alineado, van ocho**: declaraba roto el LIDAR sobre el
estado **normal** del robot (el barrido arranca parado a propósito), y volvió a **contar un
comentario como si fuera un ajuste** —esta vez el que explicaba que `ROS_DOMAIN_ID` ya no está en
el `.bashrc`—, o sea que **fallaba justo después de arreglar el problema**.

🔴 **Esa última es la segunda vez que se comete el mismo error.** En un fichero de configuración,
un `grep` de una cadena suelta encuentra tanto el ajuste como lo que *habla* del ajuste. **Ancla
al principio de línea y a la sintaxis exacta**: `^[[:space:]]*export[[:space:]]+VAR=`.

**Un verificador con falsos positivos se acaba ignorando, y eso es peor que no tenerlo.**
Evidencia 32.

Su regla es **comprobar el efecto, no la intención**. Si añades comprobaciones, mantenla.

### Los tres scripts de la flota

| Script | Dónde corre | Para qué |
|---|---|---|
| `preparar_tarjeta.sh --id NN` | en el **PC** | Tarjeta recién grabada: `cmdline.txt`, `config.txt`, `robot_id.txt` |
| `provision.sh` | en el robot | De un 24.04 limpio a robot terminado. Idempotente: sirve para actualizar |
| `verificar_robot.sh` | en el robot | Decide si el robot está listo |
| `fase_7_systemd.sh --id NN` | en el robot | Arranque automático. ✅ Probado con un reinicio real. `provision.sh` **todavía no lo llama** |
| `atriz-escaneo on\|off\|estado` | en el robot | Enciende/apaga el barrido del lidar. **Sin barrido el robot no conduce** |

**La imagen dorada es el atajo; `provision.sh` es la verdad.** Si divergen, gana el script y se
reconstruye la imagen. Procedimiento completo en `03_operacion/FLOTA.md`.

> 🔴 **Y esa regla supone que el script funciona — eso NO está comprobado.**
> `provision.sh` **nunca se ha ejecutado de principio a fin** sobre un 24.04 limpio: exigiría
> reflashear rvr-01, el único robot montado, y el usuario decidió no hacerlo (2026-07-31).
>
> Lo que sí está verificado: sintaxis, una pasada completa con `--simular` (código 0), la
> comprobación de los binarios de Nav2 —que **no** se simula— y la idempotencia. Lo que **no**:
> nada de lo que instala o compila, porque la simulación convierte justo eso en no-operación.
>
> **No construyas la imagen dorada sin levantar esta suposición.** El riesgo no es que falle:
> es que falle **en el robot 7 de 16**, con seis ya desplegados.
> Detalle en `00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.

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
