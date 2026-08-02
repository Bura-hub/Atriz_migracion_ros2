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

**🔴 NO USES `percentage` PARA DECIDIR SI HAY QUE CARGAR: usa `voltage`.** Medido el
2026-08-01: el porcentaje decía **100 %** con la batería a **8.29 V**, a 1.29 V del umbral de
«baja» del propio firmware (7.0 V; crítica 6.5 V, histéresis 0.2). El porcentaje es una
estimación gruesa. Desde esa fecha `/battery_state` publica `voltage` (antes era `NaN`) y el
driver registra los umbrales en el log al arrancar.

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

**🔴🔴 RETRACTADO EL 2026-08-01: `ros2 topic hz` SÍ FUNCIONA sobre topics BEST_EFFORT.**
Medido en este robot con `ros2cli 0.32.10`:

```
ros2 topic hz /odom       → average rate: 16.525     (Reliability: BEST_EFFORT)
ros2 topic hz /imu        → average rate: 13.338 · 16.297 · 16.505   (tres tomas)
ros2 topic hz /encoders   → average rate: 16.669
```

**Por qué funciona**, leído en el código y no supuesto: `ros2topic/verb/hz.py:268` se suscribe con
**`qos_profile_sensor_data` fijo** — BEST_EFFORT · VOLATILE · depth 5. Un suscriptor BEST_EFFORT
empareja con publicadores **BEST_EFFORT y RELIABLE** por igual (lo pedido ≤ lo ofrecido), así que
`hz` sirve para **todos** los topics. Es exactamente lo contrario de lo que decía la creencia.
📝 Una versión anterior de esta nota decía que `hz` «consulta el QoS del publicador y lo adapta».
**Eso también era inventado**: no consulta nada, lleva el perfil clavado. La conclusión era
correcta por una razón equivocada, y corregir solo la conclusión habría dejado el error en pie.

⚠️ **Dos trampas al usarlo:**
- **Canalizar su salida la esconde.** `ros2 topic hz /imu | tail` no imprime nada antes del
  timeout, porque Python pasa a buffer de bloque. Sale vacío y se lee como «no mide» — que es
  justo de donde salió la creencia falsa. Usa `stdbuf -oL`, o míralo en la terminal.
- **`/imu` no tiene un ritmo estable:** 13.338, 16.297 y 16.505 Hz en tres tomas, más **15.27 Hz**
  con suscriptor propio. La dispersión es del **±11 %** y **no está explicada**. No cites un
  número suelto de `/imu` como si fuera su frecuencia.

🔴 **Y esa creencia falsa ha costado caro:** guió el rediseño del verificador, y el 2026-08-01
llevó a «corregir» el plan y el RUNBOOK sustituyendo un comando que funciona. Se detectó al
medirlo antes de propagar la corrección a un cuarto fichero.

📝 **La lección: una trampa documentada también caduca.** Este proyecto exige medir antes de
afirmar; eso vale igual para lo que ya está escrito, sobre todo si depende de la versión de una
herramienta que se actualiza sola.

⚠️ **`medir_ritmo_ros2.py` sigue valiendo más** para caracterizar: da jitter, huecos y percentiles,
y `topic hz` solo la media. Pero para «¿publica esto?» `topic hz` sirve.

**Texto original, conservado:** 🔴 `ros2 topic hz /odom` DA 0 Hz SIEMPRE, con el robot perfecto. `/odom` se publica
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

**📚 LA DOCUMENTACIÓN OFICIAL DEL PROTOCOLO ESTÁ EN EL REPO**, en
[`00_auditoria/referencia_sdk/`](00_auditoria/referencia_sdk/) — con el análisis en la
evidencia 43. El sitio
`sdk.sphero.com` **ya no existe**; hay copia de 2021 en archive.org. Documenta el **protocolo
del robot**, no el SDK de Python, así que describe comandos que la librería **no expone** —
`get_motor_temperature` y `force_battery_refresh` están en el protocolo y **faltan en nuestro
SDK**. Si algo no cuadra entre el SDK y el robot, mira ahí antes de teorizar.

**🔴 UN VALOR PLAUSIBLE NO ES UN VALOR VALIDADO.** El 2026-08-01 se llamó a
`get_temperature(id0=0, id1=1)` y salió 27.76/28.61 °C, que se dio por bueno porque **encajaba**
con la temperatura de motores ya conocida. Los IDs documentados son **4** (motor izq), **5** (motor
der) y **8** (die del Nordic). ✅ Comprobado después: con 4 y 5 salen 27.50/28.26 °C, que
**coinciden en 0.08 °C** con `get_motor_thermal_protection_status`, y con 8 sale 32.0 —o sea que
el firmware **sí respeta el ID**.
→ ⚠️ **Pero llamar «basura» a la medida con 0 y 1 fue pasarse por mi parte:** dieron 27.76/28.61,
  a dos décimas de lo bueno. Podrían ser alias no listados. **Usa 4, 5 y 8**, que están
  documentados y verificados; de 0 y 1 no se sabe.
→ 📝 **Y la lección de verdad, que costó dos vueltas: una corrección también es una afirmación,
  y necesita la misma evidencia que lo que corrige.** Van dos veces seguidas que arreglar un
  error genera otro.

**🔴 EL FIRMWARE DEL RVR YA ESTÁ EN LA ÚLTIMA VERSIÓN, y actualizar quitaría API, no la
añadiría.** La última publicada por Sphero (Fall 2022) es **9.1.462 / 9.2.482**, que es
**exactamente la que tiene este robot**. Y en el foro oficial se ve que con el firmware
**anterior** (8.3.432/8.6.448) `get_magnetometer_reading` **sí respondía**; con el nuestro da
`bad_cid`. → **No busques versiones nuevas ni «SDK modificados»:** el SDK solo serializa el
protocolo, y `bad_cid` **lo responde el robot**. Ningún fork añade un comando que el firmware
no implementa. Evidencia 42.

**🔴 «El comando falla» NO es «la capacidad no existe».** El 2026-08-01 se concluyó que el RVR
«no tiene magnetómetro» porque `get_magnetometer_reading` daba `bad_cid`. **Falso:** lleva una
IMU de 9 ejes, y un ingeniero de Sphero explica que la lectura cruda **no es la que hay que
usar** — el patrón previsto es `magnetometer_calibrate_to_north()` (CID **0x25**, otro comando)
→ `yaw_north_direction`, que es **el desfase entre el yaw=0 arbitrario y el norte magnético**, y
desde ahí el rumbo sale de la IMU. La app de Sphero nunca lee el magnetómetro.
→ 🔴 **PROBADO EL 2026-08-01, Y CERRADO: NO HAY RUMBO ABSOLUTO.**
  `magnetometer_calibrate_to_north()` **se acepta sin error** —no da `bad_cid`— y luego **ni
  gira el robot ni emite notificación**. Es un **no-op**. Lo zanjó el usuario mirando el robot:
  sin ese dato, «no llegó la notificación» era ambiguo.
→ **Consecuencia, y es una limitación del hardware, no una tarea:** la pose inicial de cada
  robot tiene que venir de fuera — del mapa (AMCL con pose inicial por robot, que ya se
  planeaba) o del operador. No bloquea nada: AMCL sigue la pose con 0.1 cm. **Deja de
  buscarlo.** Evidencia 42.

**🔴 `chmod` NO HACE NADA EN `/boot/firmware`, Y NO DA ERROR.** Es **vfat**, y FAT no
almacena permisos de Unix: los fija `fmask` en el **montaje**, para toda la partición. Con el
`defaults` de Ubuntu queda todo en **755**, así que `red.txt` —que lleva **la PSK del WiFi**—
lo lee cualquier usuario sin `sudo`. Medido el 2026-08-01: `sudo chmod 600` aceptado, `ls`
seguía diciendo `-rwxr-xr-x`.
→ Lo grave no es el permiso, es que **`chmod` se acepta en silencio**: el problema queda
  abierto **con aspecto de resuelto**. Misma clase de error que `usercfg.txt` en 24.04 — un
  fichero que existe y no hace nada.
→ Para cerrarlo: montar con `fmask=0177,dmask=0077` en `/etc/fstab`. Manual, cap. 19.3b.
  ⏳ **Decisión pendiente del usuario.**

**🔴 `chmod` SOBRE `/boot/firmware` NO HACE NADA, Y DEVUELVE 0.** Es una partición **FAT**, y
FAT no guarda permisos de Unix: los fija el *montaje* (`fmask=0022` con `defaults`), así que
todo queda en **755** hagas lo que hagas. → **La PSK del WiFi de `red.txt` es legible por
cualquier usuario del robot, sin `sudo`**, y la imagen dorada lo replicaría por 16. Se cierra
en `/etc/fstab`: `defaults,fmask=0177,dmask=0077`. El firmware de la Pi lee la FAT en crudo
antes de arrancar Linux, así que no le afecta. Manual, cap. 19.3b.
→ 📝 **Y la forma general, que ya va por la quinta vez en este proyecto: un comando que
  devuelve 0 no prueba que hiciera algo.** Como `set_all_leds` con una máscara mal formada,
  `undercarriage_white` con su `success=true`, `colcon build` diciendo «finished» sin compilar,
  y `netplan generate` que ni llegó a ejecutarse. **Comprueba el efecto, no el código de
  salida.**

**🔴 NUNCA ESCRIBAS EN UNA RUTA FIJA DE `/tmp` DESDE UN SCRIPT CON `sudo`.**
Ubuntu 24.04 trae `fs.protected_regular=2`, que impide a **root** escribir en un fichero de
un directorio pegajoso (`/tmp`) que **no le pertenece**. Y el modo de fallo es venenoso:

```bash
if netplan generate 2>/tmp/netplan.err; then     # ← si la redirección falla...
```
**Si la redirección falla, bash NO ejecuta el comando** y devuelve error. El script se va al
`else` y hace `cat` del fichero — que sigue teniendo el **contenido rancio de otra ejecución**,
de otro usuario, de horas antes. Resultado: un fallo inventado, atribuido a la causa
equivocada, y en este caso el borrado de un netplan que estaba perfectamente bien.

Pasó el 2026-08-01: el script informó de `Interactive authentication required` de systemd,
que era el error de **una ejecución sin sudo de las 14:43**. `netplan generate` nunca llegó a
correr. → Usa `mktemp`. Arreglado en `first-boot.sh` y en `provision.sh` (el `.deb` de ROS,
que habría mordido igual en la instalación de los 16).

→ **Y la regla general:** un error que menciona permisos o autenticación en un script que ya
corre como root **casi nunca es lo que dice**. Mira si lo que falló fue la *redirección*, y
comprueba la **fecha** del fichero que estás leyendo.

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
  **paleta**… 🔴 **y esa explicación era FALSA, comprobada el 2026-08-01**:
  `get_active_color_palette` devuelve **5 colores cargados y activos** —(212,40,47),
  (243,218,67), (21,157,128), (0,140,160), (97,53,139)—. **Hay paleta.** La confianza es 0
  porque las superficies probadas (suelo, blanco, rojo, azul, negro) **no se parecen a esos
  cinco colores**, no porque falte configurar nada. Evidencia 41.

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

**✅ ~~LA DETECCIÓN DE ATASCO PODRÍA REABRIRSE~~ — NO HACE FALTA: ya funciona** por la
notificación del firmware (3 de 3, y dice qué oruga). Esto nació de creer que era imposible.
📝 La temperatura sigue valiendo como **corroboración**: un motor bloqueado sube **+11.1 °C en 90 s** de bloqueo (ritmo NO constante, 5→10 °C/min, n=1).
Texto original: La doc oficial
dice que la temperatura del motor está **«calculated from motor current»** — o sea que es un
**proxy de la corriente**, que es lo que no se puede leer. Y el driver **ya publica** las dos
temperaturas en `/motor_status` cada 30 s. → Lo que falta no es leer nada nuevo, es
**interpretarlo**: temperatura subiendo + movimiento comandado + encoders quietos = atasco
probable. ⚠️ Es un proxy **lento** (decenas de segundos por la masa térmica): no sirve para
parar el robot, sí para decidir si hay que ir a rescatarlo. Sin implementar. Evidencia 43.

**🔴🔴 EN ESTE FIRMWARE, QUE UN COMANDO NO DÉ ERROR NO SIGNIFICA QUE HAGA ALGO.** Van
**dos** comandos comprobados que se aceptan en silencio y no hacen nada:
`magnetometer_calibrate_to_north` (ni gira ni avisa) y `core_time` (en el enum, el RVR no lo
transmite).
→ ⚠️ **Antes esta lista decía CINCO** e incluía `enable_motor_stall_notify` —que **sí funciona**,
  retractado— y las notificaciones de fallo y térmica, que quedaron **NO VERIFICADAS**: el ensayo
  no llegó a la temperatura de disparo, así que no están desmentidas. **«Sin verificar» no es
  «no funciona»**, y meterlas en la misma lista fue lo que alimentó la conclusión falsa.
→ **Comprueba siempre el EFECTO**: un dato que llega, o el robot moviéndose. Y cuando el efecto
  es **físico, pregunta a la persona que lo está mirando** — es el único instrumento que no se
  puede enredar. El 2026-08-01 «el robot no giró» fue lo que zanjó lo del magnetómetro.

**🔴🔴 RETRACTADO: LAS NOTIFICACIONES DE ATASCO **SÍ** LLEGAN.** Lo de abajo era falso, y
costó tres investigaciones. Medido el 2026-08-01 con el robot bloqueado a mano: **3 de 3
detecciones, acertando la oruga las tres veces**.

```
18:08:07  🔴 MOTOR IZQUIERDO ATASCADO. El firmware ve corriente y no ve giro.
18:08:09  motor izquierdo: atasco resuelto
```

🔴 **La causa real es el TIEMPO, no el camino.** La evidencia 35 hizo **dos** ensayos, y el
primero ya usaba `move_timed` —`drive_rc_si_units`, el camino bueno— durante **3 s**. La
detección tardó **~5 s**. No dio tiempo.

⚠️ **Ese «~5 s» es débil y conviene saberlo:** sale de **un solo par de marcas del journal** (18:08:02 → 18:08:07), que tiene resolución de 1 s en cada extremo — o sea **5 ±2 s**. El atasco se detectó 3 de 3, pero **solo se cronometró una vez**. Y no basta para cerrar la explicación: el ensayo fallido iba a **0.15 m/s** y el bueno a **0.08 m/s**, así que cambiaron dos cosas a la vez. Lo razonable es que a más velocidad se detecte *antes* (el error entre comandado y medido es mayor), lo que **refuerza** la conclusión — pero eso es un argumento, no una medida.
📝 **El experimento que lo cerraría**, ahora que `probar_atasco.py` respeta sus argumentos de verdad: `--vel 0.15 --seg 3` reproduce las condiciones exactas del ensayo fallido. Si detecta, la explicación del tiempo es incompleta. Requiere bloquear el robot a mano. ⚠️ Y hay un confusor sin aislar: aquel ensayo iba a
0.15 m/s y el que detecta a 0.08.
📝 **La lección: antes de concluir que algo NO ocurre, pregunta cuánto tendrías que haber
esperado.** Un negativo sin esa cuenta no es un negativo.

⚠️ La primera explicación de esta retractación decía «se probó con `raw_motors`, que se salta el
sistema de control». **Eso solo cubre el segundo ensayo**, y hubo que corregirlo — corregir un
error generó otro, por tercera vez en el día.

⚠️ Y encadenó errores: sobre esa base falsa se buscó la corriente de los motores (`bad_cid`), se
declaró el atasco **imposible**, y se llegó a implementar un detector por encoders —**todo
innecesario**, y retirado—. Evidencia 44.

✅ **Bonus, y lo vio el usuario mirando el robot:** durante el atasco **el RVR enciende LEDs
amarillos y rojos** por su cuenta. El driver no los toca. Es diagnóstico sin abrir un terminal.

⚠️ **`enable_motor_fault_notify` y la térmica: repetidas por el camino bueno y quedan NO
VERIFICADAS.** 10 ciclos de bloqueo real subieron los motores de 28.7 a **40.0 °C** y no saltó
ninguna. Pero **eso no prueba nada**: la protección térmica no actúa a 40 °C, y el tope de
seguridad de la prueba estaba en 65 — **el ensayo nunca pudo dispararla**.
📝 A qué temperatura salta **no se sabe**: no está en el SDK ni en la documentación de Sphero
que se rescató. La versión anterior de este párrafo decía «70-80 °C» y «~5 min más», y **las dos
cifras eran inventadas**: la primera no tiene fuente, y la segunda extrapolaba linealmente un
ritmo que en la propia medición **no es lineal** (5.0 → 8.4 → 10.2 °C/min entre tramos). 📝 **No se persigue**: el sondeo cada 30 s ya da la
temperatura **y** el estado térmico, así que saber si además llega la *notificación* aporta muy
poco, y el coste es estrés real sobre la única unidad montada. El fallo eléctrico no se puede
provocar sin romper algo.

✅ **Y de esa prueba salieron dos datos que sí valen:**
- **Un motor bloqueado sube **+11.1 °C en 90 s** de bloqueo (ritmo NO constante, 5→10 °C/min, n=1).** La temperatura sirve de **corroboración** de
  atasco: si `/motor_status` marca atasco *y* la temperatura sube, no hay duda.
- 🔴 **La temperatura publicada puede tener 30 s de retraso** — solo cambia cuando corre el
  sondeo. **La web no debe leer una temperatura plana como «estable»**: puede ser el mismo dato
  repetido. Para eso está `antiguedad_termico_s`.

---

**Lo que decía antes, conservado para que no vuelva por la puerta de atrás:**

**🔴 ~~LAS NOTIFICACIONES DE MOTOR NO LLEGAN~~, PERO LAS CONSULTAS SÍ.** `enable_motor_stall_notify`,
`enable_motor_fault_notify` y la térmica se registran sin error y **no emiten ni un mensaje**:
comprobado el 2026-08-01 forzando los motores a 220/255 con el robot sujeto, y esperando 100 s la
térmica —que debería llegar sola— sin recibir nada. Es el mismo caso que `core_time`.
→ **Sondea**: `get_motor_fault_state()` y `get_motor_thermal_protection_status()` **sí responden**
  (27.9 / 27.7 °C). El driver lo hace cada 30 s y publica **`/motor_status`**.
→ ✅ **RETRACTADO: el atasco SÍ se cubre**, por la notificación del firmware. Lo que sigue
  siendo cierto es que **no hay consulta** (`get_motor_stall_state` no existe) y que la
  **corriente** tampoco se puede leer. Lo falso era la conclusión. Texto original: No es solo que
  falte `get_motor_stall_state`: la mejor alternativa era deducirlo de la **corriente** de los
  motores (corriente alta + encoders quietos), y `get_current_sense_amplifier_current` devuelve
  **`bad_cid`** — el firmware **no implementa** esa consulta. Tampoco hay magnetómetro. Es una
  carencia del firmware, no del driver: **deja de buscarlo**. Evidencia 41.
  ✅ **Ya no hace falta ninguna vía alternativa:** la notificación del firmware funciona. Se
  llegó a implementar un detector por encoders y **se retiró** — resolvía un problema que no
  existía. Evidencia 44.
→ Por eso
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

**🔴🔴 CON EL BARRIDO APAGADO, EL NODO DEL LIDAR ESCUPE 25 ERRORES POR SEGUNDO.**
`Failed to get scan`, y el barrido apagado es el **estado normal en reposo** de los 16 robots.
Medido el 2026-08-01: **502 errores en 20 s**, **el 99 % del journal del servicio**
(47 291 de 47 551 líneas), 2.17 millones de mensajes al día por robot.
→ Lo grave no es el ruido: **ahoga cualquier error de verdad**, y este proyecto tiene sus
  peores fallos documentados como silenciosos — el journal es donde se buscan. Además son
  escrituras 24/7 sobre una **microSD**, que es lo que las mata.
→ **Y nadie lo ve:** servicio `active`, verificador con 105 correctas, robot funcionando.
→ **La lección:** la decisión «arrancar con el lidar parado» se validó mirando **el motor**,
  no **el nodo ROS que lo lee**. **Al cambiar el estado por defecto de un componente,
  comprueba qué hacen todos los que dependían de él.**
→ ✅ **ARREGLADO el 2026-08-01, y no como se había planteado.** La primera propuesta era **no
  levantar el nodo** hasta que hiciera falta; el usuario desconfió, y con razón. Al mirar el
  fuente apareció la causa real: `/stop_scan` y `/start_scan` son servicios **del propio nodo**
  y llaman a `turnOff()`/`turnOn()`, pero **nadie guarda ese estado**, así que el bucle sigue
  sondeando el puerto serie a 20 Hz y fallando siempre.
→ **Arreglo: nueve líneas** — una bandera `std::atomic<bool> escaneando` y una salida temprana
  en el bucle. **No cambia nada del arranque:** el nodo sigue levantándose con el robot y
  `atriz-escaneo on/off` funciona igual. ✅ Verificado: **0 errores en 20 s** (eran 502),
  `on` → `/scan` a **12.00 Hz / 250 puntos**, `off` → 0 mensajes y 0 ruido.
→ 🔴 **El parche vive en `Atriz_rvr/atriz_rvr_bringup/patches/` y lo aplica `provision.sh`**,
  no se edita a mano: el script clona el ydlidar de GitHub y le borra el `.git`, así que un
  cambio manual se perdería al reflashear y los robots divergirían.
→ 📝 **La lección de método:** la primera solución era peor que el problema y venía de no haber
  leído el fuente. **Antes de rediseñar el arranque de un sistema, mira por qué falla el
  componente.**

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
probar_magnetometro.py       # ¿hay rumbo absoluto? · --calibrar ⚠️ GIRA EL ROBOT 360°
probar_atasco.py             # ⚠️ MUEVE EL ROBOT y TÚ LO BLOQUEAS: ¿detecta un atasco?
probar_notif_fallo_termica.py # ⚠️ CALIENTA LOS MOTORES a propósito · quedó NO VERIFICADA
probar_sdk_tanda2.py         # temperaturas con los IDs buenos, color async, batería
#                              --calibrar ⚠️ GIRA EL ROBOT 360° tres veces
probar_sdk_no_usados.py      # los métodos del SDK que el driver NO usa: ¿cuáles responden?
#                              ⚠️ necesita el driver parado (sudo systemctl stop atriz-robot)
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
auditar_documentacion.py      # ¿dice la documentación lo que de verdad pasa? · sin ROS ni sudo
first-boot.sh --solo-red      # regenera /etc/netplan/60-atriz.yaml desde red.txt (sudo)
#                               NO aplica: eso es `netplan try`, que revierte solo
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
| `/motor_status` | cada **30 s** · temperatura en reposo **27.5 / 28.3 °C** · ✅ **el atasco SÍ se detecta** y dice **qué oruga** · bloqueado **+11.1 °C en 90 s** (5→10 °C/min, n=1) | 2026-08-01 |
| `/encoders` | **16.57 Hz** · ticks con signo (7792 ticks/m) | 2026-08-01 |
| `/ambient_light` | **13.06 Hz** · ~1.8 con los LEDs apagados, **23.55 con todos encendidos** (13.3×) | 2026-08-01 |
| **Batería** | ✅ **`/battery_state` publica `voltage`** desde el 2026-08-01: **8.28 V** al «100 %» · umbrales del firmware **7.0 / 6.5 V**, histéresis 0.2 | 2026-08-01, evidencia 43 |
| **Nombre Bluetooth del RVR** | `RV-1E6D` — identifica **la bola**, no la Pi. Para el inventario | 2026-08-01 |
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
| ✅ **SIN NAMESPACE** (cerrado 2026-08-01) | Los topics son `/odom`, no `/rvr_01/odom`. El `ROS_DOMAIN_ID` por robot ya da aislamiento total, y la web habla por **un WebSocket por robot**, así que el namespace no añade nada. 🔴 Y la parada de emergencia **ya falló una vez por un namespace**: no se le regala el quinto fallo. El argumento `namespace` de los launch se deja como camino de escape. `ARQUITECTURA.md` |
| ✅ **El nombre oficial de la parada es `/emergency_stop`** (cerrado 2026-08-01) | Es donde publica la web, con **RELIABLE + VOLATILE**. El driver sigue escuchando los tres nombres a propósito: con un botón de emergencia el modo de fallo que importa es «el mensaje no llega» |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final** | decisión del usuario |
| `ros-jazzy-ros-base`, **NO** `desktop` | Server headless; RViz2 va en un portátil |
| **`ros-jazzy-navigation2`, NO `ros-jazzy-nav2-bringup`** | `bringup` depende de `nav2-minimal-tb3-sim`, `tb4-sim` y `ros-gz-sim`: **312 paquetes** de simulador y dos TurtleBots en un robot real, incluido `pocketsphinx-en-us`. Los launch los escribimos nosotros, como con `slam_toolbox` |
| ✅ **Estática + DHCP conviven en `wlan0`** — verificado con 3 direcciones a la vez | Era la suposición «A VERIFICAR» que sostenía el diseño de la flota. El robot se muda de casa al laboratorio **sin tocar un comando**. Evidencia 39, manual cap. 19 |
| 📜 **El driver de ROS 1 de Atriz DERIVA de `git.uibk.ac.at/informatik/stair/ros-sphero-rvr`** (Innsbruck) | Descubierto el 2026-08-01: **seis nombres de servicio idénticos**, el topic `/is_emergency_stop` —el nombre raro que costó el primer fallo de la parada— y el `cmd_vel_timeout = 0.3` que su README documenta explícitamente. Explica de dónde salen nombres que aquí parecían arbitrarios. Evidencia 46 |
| ✅ **Y corrobora la prueba del magnetómetro** | Su driver hace **exactamente** la misma secuencia que probamos (`calibrate_to_north` + notificación → `yaw_north_direction`), sin ningún paso previo que nos hubiéramos saltado. Su docstring confirma que **el robot debería girar**. En nuestro firmware no gira: la conclusión «no hay rumbo absoluto» se sostiene con contraste externo |
| **NO se adopta nada de `CollaborativeRoboticsLab/sphero_rvr_ros`** (revisado 2026-08-01) | Su rama `ros2` usa **`ros2_control` en C++**, que es la arquitectura canónica — pero migrar sería reescribir el driver y **perder todo lo caracterizado**. Y está menos avanzada en lo que aquí importa: **sin keepalive** (el RVR se duerme a los 300.6 s), sin parada de emergencia, sin capa de seguridad, y con la navegación aún en `move_base` de ROS 1. ✅ **Sí se toma una idea**: separar el **canal de salud de flota** (~1 Hz) del canal de operación. Evidencia 46 |
| **Imagen dorada** para los 16, no aprovisionar por red | ~300 MB y 15-20 min por robot, sobre la única AP. `FLOTA.md` |
| La imagen dorada se **construye ejecutando `provision.sh`**, no a mano | Una imagen irreproducible es una caja negra. `FLOTA.md` |
| **`provision.sh` instala `navigation2`** desde el 2026-07-31 | Antes no lo instalaba: un robot aprovisionado con el script no podía navegar, ni tenía capa de seguridad, ni localización |
| ✅ **Estática y DHCP CONVIVEN en `wlan0`** (verificado 2026-08-01) | 3 direcciones IPv4 a la vez (`10.14.7.7`, `192.168.1.200`, DHCP) y la ruta por defecto la pone el DHCP. Era **la suposición que sostenía todo el diseño de red**. Un robot se muda de red **sin tocar un comando**. Manual, cap. 19 |
| 🔴 **PENDIENTE Y BLOQUEANTE: rosbridge está ABIERTO** | Puerto 9090 **sin autenticación ni TLS**, en todas las interfaces, y expone los 18 servicios — incluido `raw_motors`, que se salta el `collision_monitor` y **no tiene corte automático**. Cualquiera en la red del aula puede mover un robot. Hay que decidirlo **antes** de escribir el cliente: cambia su arquitectura. `ARQUITECTURA.md` |
| ✅ **El camino web ↔ robot está verificado de extremo a extremo** | Navegador del PC → `ws://rvr-01.local:9090` → topics **y** servicios. `03_operacion/probar_conexion_web.html`, sin librerías ni CDN. La web **no necesita SSH para nada operativo**. Evidencia 39 |
| ✅ **La web localiza a los robots por `rvr-NN.local` (mDNS)**, con la IP como override | Es lo que hace que el mismo código funcione en casa y en el laboratorio sin tocar nada. Verificado el 2026-08-01 desde el PC del usuario: avahi publica **A=192.168.1.58 y AAAA link-local**, y rosbridge escucha en **las dos familias**. Evidencia 39 |
| 🔴 **NO se reflashea rvr-01 para probar `provision.sh` entero** | Es el único robot montado. Decisión del usuario el 2026-07-31: se **asume** que funciona hasta tener una tarjeta de repuesto. **Es una suposición, no un hecho** — ver abajo |
| **🟢 GO: el SDK funciona en Python 3.12** (16.67 Hz) | manual, cap. 5.1 · verificado 2026-07-30 |
| El driver publica `odom → base_footprint`, **no** `odom → base_link` | manual, cap. 9.4 · REP-105 y un frame = un padre |
| `async_slam_toolbox_node`, no el `sync` | no bloquea por barrido, y cuesta 4.5 % · manual cap. 9 |
| SLAM va en un launch **aparte** de `robot.launch.py` | el robot tiene que arrancar sin SLAM, y SLAM reiniciarse sin soltar `/dev/rvr` |
| **`localizacion.launch.py` es EXCLUYENTE con `slam.launch.py`** y lo comprueba al arrancar | los dos publican `map → odom`; juntos parten el árbol TF sin dar error. Manual, cap. 14.2 |
| 🔴 **`/ambient_light` NO SE USA** | el sensor mira hacia arriba y el **piso blanco del LIDAR** le refleja los LEDs del propio robot (13.3×). Un valor alto significa «el robot tiene LEDs encendidos», no «hay luz». Se probó, responde, y no sirve en este montaje. Decisión del usuario, 2026-08-01 |
| **La salud de motores se SONDEA *y* se escucha** (corregido 2026-08-01) | El **atasco SÍ llega por notificación** —3 de 3, acertando la oruga— y era falso que no. El **fallo** y la **térmica** se sondean cada 30 s porque sus notificaciones siguen **NO VERIFICADAS**, que no es lo mismo que «no llegan». Evidencias 35 y 44 |
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

**105 aserciones** con `--hardware` ✅ medido 2026-08-01 (102 sin él), 0 fallos, código de salida ≠ 0 si algo falla, y cada
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

### Y la documentación tiene su propio verificador desde el 2026-08-01

```bash
python3 ~/atriz_migracion/scripts/auditar_documentacion.py
```

Existe porque **ese mismo día aparecieron CUATRO casos de deriva documental**, y ninguno era
descuido: eran documentos de **estado** que se quedaron atrás mientras las evidencias estaban al
día. El índice del manual daba por «no escritos» cuatro capítulos verificados; el plan decía
«Nav2 ⏳ pendiente» con Nav2 navegando desde hacía un día; y **el manual 15.3 afirmaba que la
parada de emergencia no cancela Nav2 y que estaba «sin comprobar»** — las dos cosas falsas desde
el 31 de julio. **Una función de seguridad descrita como rota cuando funciona.**

Comprueba: enlaces a ficheros inexistentes, capítulos citados que no existen, secciones fuera de
orden dentro de un capítulo, frases que ya son falsas, y el índice del manual contra sus
capítulos reales.

⚠️ **Lo que NO puede hacer: saber si una afirmación es VERDAD.** Para eso está la regla:
**al cerrar algo, actualiza el plan y `TRASPASO.md` en el MISMO commit que la evidencia — y busca
TODAS las menciones, no la primera.** Corregir la cabecera del capítulo 4 del plan y dejar la
subsección 4b diciendo lo contrario ya pasó, el mismo día.

🔴 Y el auditor nació con **tres falsos positivos propios**: comparaba secciones entre capítulos
(el manual está ordenado por tema a propósito), cortaba el índice antes de la tabla, y contaba
como deriva una frase falsa **citada para dejar constancia de que lo era**. Arreglados antes de
darlo por bueno — la misma regla que el verificador del robot.

Su regla es **comprobar el efecto, no la intención**. Si añades comprobaciones, mantenla.

### Los tres scripts de la flota

| Script | Dónde corre | Para qué |
|---|---|---|
| 🔴 `preparar_tarjeta.sh --id NN` | en el **PC** | **OBLIGATORIO antes del primer arranque**, no es comodidad: `cmdline.txt` (si no, el UART queda para la consola y **el RVR no habla**), `config.txt` con `[all]`, y `robot_id.txt` — que **`provision.sh` NECESITA** en su paso 8/9. `provision.sh` **no toca `cmdline.txt`** |
| `provision.sh` | en el robot | De un 24.04 limpio a robot terminado. Idempotente: sirve para actualizar |
| `verificar_robot.sh` | en el robot | Decide si el robot está listo |
| `fase_7_systemd.sh --id NN` | en el robot | Arranque automático. ✅ Probado con un reinicio real. ✅ `provision.sh` **lo llama** desde el 2026-08-01 (paso 8/9) |
| `first-boot.sh --solo-red` | en el robot | Regenera el netplan desde `red.txt` **sin reiniciar**. Después: `sudo netplan try --timeout 90` |
| `first-boot.sh --solo-red` | en el robot | Regenera el netplan desde `red.txt` **sin reiniciar**. No aplica: eso es `netplan try` |
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
