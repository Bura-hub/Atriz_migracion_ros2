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
| `Bura-hub/Atriz_rvr` | Código del robot. Rama de trabajo: **`ros2`**, y desde el 2026-08-04 es también **la rama por defecto**: un `git clone` a secas ya da la buena (verificado clonando). ⚠️ `main` sigue existiendo, es ROS 1 (catkin) y está **75 commits por detrás**: no lo uses |
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
contiene.

🔴 **Aquí ponía «por eso este repositorio es privado». Ya NO lo es.** 👤 El 2026-08-11 el usuario
puso `Atriz_migracion_ros2` y `Atriz_rvr` en público a propósito, para no repartir un PAT en 16
microSD (medido ese día: los dos clonan sin credencial; `atriz-lab` sigue privado). El `.docx`
sigue versionado en `02_manual/`. **No des por privado nada de este repositorio.**

✅ **Pero la credencial del `.docx` está MUERTA: se rotó el 2026-08-04**, junto con la PSK. Lo que
queda versionado es una contraseña que ya no vale. Sacarla es higiene, no urgencia. 📌 Antes de
marcar algo como riesgo abierto, mira si el repositorio ya registra que se cerró.

🔴 **Y el 2026-08-02 apareció un SEGUNDO caso, en `Atriz_rvr` (público, rama `ros2`), otro
fichero y otras dos credenciales:** la PSK del WiFi del laboratorio y la contraseña del usuario
`sphero`, en texto plano en `scripts/estudiantes/00_LEEME_PRIMERO.md` y
`GUIA_PASO_A_PASO.md`. Las once líneas se **sacaron del contenido actual** al reescribir esos
documentos (tarea 12, commit `d543cdd`), pero **siguen en el historial** de `main` y `ros2` —
medido el 2026-08-02 sobre las cuatro ramas remotas que entonces existían, 11 coincidencias en
cada una, ningún tag afectado, 2 commits tocan el valor. El 2026-08-03 se **borraron**
`migracion-ros2` y `wip/scripts-estudiantes`, así que hoy quedan **dos** ramas y solo la punta
de `main` sigue sirviéndolas; **eso no cierra nada**: el historial de `main` y `ros2` las
conserva igual. Reescribir el
contenido no cierra la exposición: **rotar la PSK y la contraseña es lo único que lo hace**, y
es acción del usuario. Purgar el historial después es higiene y es incompleta — no llega a los
forks que ya existan. Al revés (purgar sin rotar) no sirve de nada.

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

**🔴🔴 UN PROGRAMA TIENE MÁS CAMINOS DE SALIDA DE LOS QUE SE TE OCURREN, Y CADA UNO PUEDE
DEJAR EL LIDAR ENCENDIDO.** `atriz.py` prometía apagar el barrido «pase lo que pase» y fallaba en
**cuatro** caminos. Ninguno lo vio ninguna de las trece revisiones por separado: solo aparecen al
hacer **la tabla de TODOS los caminos de salida contra la promesa**.

| Camino | Por qué fallaba |
|---|---|
| **Segundo Ctrl-C** | dos `try` y **un solo `finally`**, y `except Exception` **no ve `SystemExit`** |
| **Cerrar la terminal / perder el SSH** | solo se manejaba `SIGINT`, ni `SIGHUP` ni `SIGTERM` |
| **Ctrl-\ (`SIGQUIT`)** | tampoco, y **sí se puede capturar** |
| **Ventana de dos sentencias** | poner la bandera de «ya cerrado» **antes** que la de «cerrando» |

```
antes + SIGQUIT/SIGTERM/SIGHUP -> /stop_scan NO se llamo    despues -> LLAMADO
```
⚠️ Tabla de **mecanismo**: lo medido es la llamada al servicio, **no** el tambor parando.
🔴 **El código de salida es idéntico en los cuatro casos, antes y después.** Solo el efecto los
distingue: es la regla «comprueba el efecto, no el código de salida» apareciendo dentro de su
propia verificación.
→ **`atexit` NO es una garantía entera:** no corre con `os._exit()`, `SIGKILL`, `SIGABRT` ni caída
  dura. Sirve para la salida normal sin `with` y la excepción sin capturar; lo demás hay que
  capturarlo por señal, y lo que no se pueda **se escribe**, no se calla.
→ 📝 **Y arreglar un camino puede abrir otro:** al hacer que la biblioteca pidiera «espera, ya
  estoy cerrando» en el segundo Ctrl-C, se empujaba al alumno justo hacia probar Ctrl-\.
→ El arreglo vive en `atriz.py`, constante `SENALES_DE_CIERRE` y el método `cerrar()`; los tests
  que lo protegen, en `scripts/pruebas/test_atriz_nucleo.py`. Medido el **2026-08-03**,
  **evidencia 56**.

**🔴 UNA FUNCIÓN QUE «RECORTA A UN VALOR SEGURO» PUEDE MAPEAR LO PEOR AL MÁXIMO.** `limitar(nan)`
devolvía **0.40 m/s** —el tope— porque `abs(nan) <= tope` es `False` y caía en la rama de recorte.
Con el tope de tiempo, `avanzar(nan, nan)` habría conducido **4 metros**.
→ Comprueba `math.isfinite` **antes** de comparar. `aceptacion_nucleo.delta_angulo()` ya lo hacía
  bien: la disciplina estaba en el repo y no se aplicó al escribir la biblioteca nueva.
  Medido el **2026-08-03**; el arreglo está en `limitar()` de `atriz.py`.

**🔴 `comprobar_contrato.mjs` NO VE UN CAMBIO DE CAMPOS EN UN `.msg`: solo mira que el fichero
EXISTA.** Descubierto el 2026-08-09 por el PC, al añadir `mapa_nombre` y `mapa_edad_s` a
`EstadoNavegacion` y **no ponerse en rojo**. En su fuente:

```
herramientas/comprobar_contrato.mjs:228
  if (!existsSync(rutaMsg)) faltantes.push({ topic, tipo, rutaMsg })
```

→ 🔴 **Y la dirección del fallo es la mala:** yo había escrito «estará en rojo hasta que alineen».
  Si se hubieran fiado, **los dos campos no habrían llegado nunca a la pantalla, con todo en
  verde**. Un comprobador que calla sobre lo que cambió es peor que no tenerlo: **sustituye a
  mirar**.
→ **La regla mientras eso siga así: al tocar un `.msg`, DECÍRSELO explícitamente al PC** en
  `ESTADO_ACTUAL.md`. No hay automatismo que lo cace.
→ 📌 Misma familia que `ros2 topic list` incluyendo topics de nodos muertos y que
  `systemctl is-active` sobre un launch cuyo nodo murió: **una comprobación que mira la existencia
  y no el contenido.**

**🔴 UNA RAMA «POR DESCARTE» RECOGE EL RUIDO, Y LO AFIRMA CON TODA CONFIANZA.** Misma familia que
la de arriba, encontrada el **2026-08-09** validando la web contra rvr-01. El clasificador de color
en modo emisión decidía así: `R/G > 1` → rojo · `B/G > 1` → azul · **si no, verde**. Con el robot
sobre suelo mate el sensor devolvió `R=0 G=1 B=0` —una cuenta de ruido— y los dos cocientes
valieron 0, o sea «ninguno pasa de 1», o sea **verde**. La pantalla afirmó *«la luz que sale de la
superficie es verde»* sobre un suelo a oscuras.
→ **Una rama por descarte necesita su propia condición de señal.** «Ninguno de los otros» no es
  una observación: es la ausencia de observación, y sin un mínimo que la sostenga cualquier ruido
  cae ahí.
→ 🔴 **Y había un test escrito contra este mismo fallo**, que comprobaba `verde === 0`. Aquí verde
  vale **1**: se coló por el borde de la guarda. Es la regla de este fichero —*«un test que barre
  tres puntos representativos puede dejar sin cubrir justo el tramo donde vive el bug»*— cometida
  **en el fichero que la citaba**. El arreglo barre el tramo entero (1..40), no tres puntos.
→ El umbral se **deriva**, no se inventa: las cuentas son enteras, el error de `R/G` es ±1/G, y con
  G=1 eso es ±100 % —no distingue 0,9 de 1,1, que es la frontera del color—. Resolverlo mejor del
  10 % da G ≥ 10. `atriz-lab`, `lib/robot/color.ts`.

**🔴 LA LUZ DEL SENSOR DE COLOR NO SE APAGÓ SOLA: 14 min 38 s ENCENDIDA SIN NADIE LEYENDO.** Medido
el **2026-08-09** cerrando la pestaña tras la última lectura (19:47:23) y mirando **el LED en el
robot**, no solo `color_activo`. El apagado por inactividad son **120 s** y pasaron **878**. Se
apagó porque se apagó a mano.
→ ⚠️ **El tope duro de 900 s quedó SIN MEDIR**, y por un error de método: se apagó a menos de dos
  segundos de cuando habría vencido, así que no se distingue «saltó» de «lo apagué yo». Repetirlo
  exige no tocar nada 20 min.
→ 📌 **Hipótesis, no medida:** el driver cuenta como actividad que alguien esté suscrito a
  `/color` (`pub_color.get_subscription_count() > 0`), y **rosbridge puede conservar la suscripción
  cuando la pestaña se cierra de golpe**. Se cierra con `ros2 topic info /color` en el robot, con
  la web cerrada.
→ 🔴 **Por qué importa con 16 robots:** es un LED blanco bajo el chasis que sale de la batería del
  RVR, que es de donde también se alimenta la Pi. Si no se apaga solo, se queda encendido toda la
  clase. `atriz-lab` **dejó de prometer** que se apaga sola y ahora dice «apágala tú».

**📌 `rosapi/get_param` REVIENTA, y `ATRIZ_MAPA` no está documentado para el PC.** Los dos del
2026-08-09, de rebote:
- `rosapi/get_param` sobre `/supervisor_navegacion/mapa` devuelve `result=true` con
  `successful=false` y `cannot access local variable 'node_name'` — un error **interno**, no una
  respuesta. ⚠️ Fíjate en la forma: es la distinción `result`/`success` del 2026-08-08 apareciendo
  sola en el primer sitio donde se usó `rosapi`. **Si `rosapi` no sirve para leer parámetros, la
  web no puede preguntar por la configuración del robot** y todo tiene que venir por topic o por
  servicio propio, como ya hace `/estado_navegacion`.
- El supervisor usa `os.environ.get('ATRIZ_MAPA') or ~/atriz_ws/.../maps/aula.yaml`, y en rvr-01
  **ese directorio está vacío** mientras `hay_mapa` dice `true`: la variable está puesta y el mapa
  vive en otro sitio. **Quien lea el código deduce la ruta equivocada** — pasó, y se mandó al
  usuario un comando que no podía funcionar. Se cierra con
  `systemctl show atriz-robot -p Environment | grep MAPA`.


**🔴 CON EL RVR APAGADO, EL DRIVER DICE «streaming reanudado» PARA SIEMPRE.** Medido el
2026-08-02 apagando el robot para cargarlo con la Pi encendida —un estado **cotidiano** en el
laboratorio y que nadie había probado—: **`/odom` a 0 mensajes en 15 s** mientras el log escribía
**8 «streaming reanudado» en 30 s**, y 123 intentos de reconexión, uno cada 4 s, sin espera
creciente. Lo imprime porque `wake`+`stop`+`start` no lanzan excepción, **no porque vuelva un
dato**.
→ **Un robot muerto parece sano en el log.** Misma familia que el RVR dormido con el nodo vivo y
  que el nodo muerto con systemd en verde.
→ Y son ~46 000 líneas al día por robot sobre una **microSD**. ⏳ Pendiente: no decir «reanudado»
  hasta que llegue una muestra de verdad, y espera creciente con tope. Evidencia 52.

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

**🔴 LA DERIVA DE YAW ES ~1000× MAYOR JUSTO TRAS ENCENDER EL RVR.** Medido el 2026-08-02 por
casualidad, al dar REVISAR la prueba de aceptación con el robot recién encendido tras cargar:

```
21:01:36   deriva 0.97  °/30 s    motor 23.2 °C   RVR recién encendido
21:08:18   deriva 0.001 °/30 s    motor 24.1 °C   ~7 min después     ← 970×
```

→ **Consecuencia para la web:** si un alumno empieza nada más encender el robot, la odometría
  deriva ~1°/30 s los primeros minutos — decenas de grados sobre una práctica de 15 min. Y
  `set_pos_and_yaw(0,0,0)` **no lo arregla**: pone el origen a cero, no corrige la deriva.
→ ⚠️ **La causa es una hipótesis, no una medida:** el sesgo de una IMU MEMS depende de la
  temperatura y el motor subió 0.9 °C entre las dos tomas. Cerrarlo exigiría una curva desde el
  encendido. No se persigue: desaparece solo.
→ 📝 Otro estado que **nadie había probado** porque las pruebas siempre se hacían con el robot
  llevando rato en marcha — como «RVR apagado con la Pi viva», encontrado el mismo día.
  Evidencia 54.

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
→ Para **contar mensajes**, ejecutor persistente **y `timeout_sec=0.0`**:
```python
ex = SingleThreadedExecutor(); ex.add_node(n)
while ...: ex.spin_once(timeout_sec=0.0)      # 16.40 Hz — coincide con topic hz
```

🔴 **CORREGIDO EL 2026-08-04: este remedio estaba INCOMPLETO y su cifra era falsa.** Decía
`timeout_sec=0.1` con el comentario «16.5 Hz — el valor real». Remedido sobre el mismo robot,
en el mismo minuto y contra `ros2 topic hz` como referencia:

```
ros2 topic hz /odom          16.51 Hz   <- referencia (y /imu 16.39-16.57)
spin_once(timeout_sec=0.0)   16.40 Hz   ✅ coincide
spin_once(timeout_sec=0.1)   15.02 Hz   🔴 el remedio DOCUMENTADO, subestimando
     (y en otras tomas del día, 13.6-14.3 Hz)
```

**La causa no es el ejecutor: es que `spin_once` procesa UN callback por llamada.** Con
`timeout_sec=0.1` el bucle gira ~10 veces por segundo, así que el conteo queda capado por el
BUCLE y no por el robot. Poner un ejecutor persistente sin quitar el `0.1` arregla la mitad.
→ ⚠️ Y esto costó una falsa alarma el 2026-08-04: se anotó «`/odom` a 14,3 Hz contra los 16,5
  habituales, sin explicar» sobre un robot **sano**, dos veces y desde las dos máquinas.
→ ⚠️ Una tercera variante —girar el ejecutor en un hilo aparte— dio 13.70 Hz, pero **esa medida
  no se cree**: el proceso volcó el core al cerrar y está contaminada. Queda **sin medir**.
→ 📝 La lección de segundo orden, que es la que vale: **una trampa documentada puede traer un
  remedio que tampoco funciona.** Este llevaba desde el 2026-07-31 con una cifra inventada al
  lado, y se usó sin comprobarlo porque venía con el sello de «ya medido».

→ Para *conducir* o esperar, `rclpy.spin_once` vale: ahí no se cuenta nada.

**🔴 `npm run build` CON `npm run dev` CORRIENDO ROMPE EL SERVIDOR, Y EL SÍNTOMA PARECE UN FALLO DE
TU CÓDIGO.** Los dos escriben en `.next/`: la compilación de producción pisa el caché del de
desarrollo y a partir de ahí las rutas devuelven **HTTP 500**. Pasó el 2026-08-04 justo después de
tocar el muro de flota, y durante un rato pareció que el cambio estaba mal:

```
tsc limpio · eslint limpio · 290 pruebas en verde · «Compiled successfully»
GET /flota  ->  500
```

El log lo delata, pero hay que ir a buscarlo: `ENOENT: .next/server/vendor-chunks/next.js` y
`Could not find the module … in the React Client Manifest`. Ninguno menciona tu fichero.
→ **Arreglo:** parar el servidor, `rm -rf .next`, y volver a arrancar. Verificado: 0 errores y las
  seis rutas a 200.
→ **Y la regla:** no compiles producción y desarrollo a la vez sobre el mismo directorio. Si hay que
  hacer las dos, `next build --distDir` aparte, o secuencialmente.
→ 📝 Van **seis** veces que el instrumento miente en este proyecto —`ros2 topic hz`, `spin_once` en
  bucle, `mensajes/duración`, mezclar ejecutores, `ros2 service call` para medir latencia, y ahora
  esto—. La forma es siempre la misma: **el fallo estaba en el medidor y se atribuyó a lo medido.**

**🔴 UN UMBRAL DE SILENCIO EN MILISEGUNDOS NO ES TRANSFERIBLE ENTRE TOPICS DE RITMOS DISTINTOS.**
Los 3000 ms de `salud.ts` están calibrados contra `/odom`, que va a **16,5 Hz**: son **50 mensajes
perdidos** antes de dar la alarma. El mismo número sobre `/motor_status`, que va a **1 Hz**, son
**tres**. Reutilizarlo habría pintado **las 16 baldosas del muro del profesor «sin señal de vida» al
primer hipo de WiFi** — justo el falso positivo que ese código existe para evitar.
→ Lo pilló quien implementaba, contra un encargo mío que decía «usa `evaluarSalud()`». **El umbral
  se expresa en MENSAJES PERDIDOS y se traduce a milisegundos con el período de SU topic**, no se
  copia. En `atriz-lab` son dos constantes distintas (`UMBRAL_SILENCIO_MS` 3000 y
  `UMBRAL_LATIDO_MURO_MS` 5000) **con una prueba que impide unificarlas**.
→ 📝 Misma familia que «`ps -o %cpu` da el promedio, no lo instantáneo» y que los 11,3 Hz de
  `spin_once`: **una cifra correcta en su contexto se vuelve falsa al mudarla de sitio.** Medido el
  2026-08-04.

**🔴🔴 EN ROSBRIDGE, EL PRIMER CLIENTE QUE SE SUSCRIBE A UN TOPIC IMPONE EL QoS A TODOS LOS
DEMÁS.** rosbridge crea **una sola suscripción ROS por topic** y la comparte. Medido el 2026-08-04
contra rvr-01, con control:

```
CASO 1 · sano primero, luego uno pidiendo RELIABLE
  A sano antes de B  16.25 Hz   ·  A después de B  16.67 Hz  (sigue bien)
  B pidiendo RELIABLE            16.50 Hz   <- su QoS se IGNORA, hereda el de A
CASO 2 · el que pide RELIABLE llega PRIMERO
  C pidiendo RELIABLE  0.00 Hz  ·  D sano, llegando después  0.00 Hz  <- NACE MUDO
CASO 3 · control, dos sanos      16.60 y 16.60 Hz
```

🔴 **Con 16 robots y varias pestañas por robot, UNA pestaña que pida un QoS incompatible deja MUDAS
a todas las demás de ese robot.** Y el síntoma es «este robot no manda datos», que se busca en el
robot y no en el navegador. Sin aviso: rosbridge **no manda `status`** (confirmado en el cable —
cero mensajes que no fueran `publish` o `service_response` en 30 s).

→ **Regla: NO mandes campo `qos` en `subscribe`.** Sin él, rosbridge usa `qos_profile_sensor_data`
(BEST_EFFORT), que empareja con publicadores BEST_EFFORT y RELIABLE por igual.
→ ✅ **Y sí toma efecto cuando se manda**, al contrario de lo que el plan daba por no verificado:
pedir `reliability: reliable` sobre `/odom` (que es BEST_EFFORT) da **0.00 Hz** entre dos controles
a 16,5. `extract_qos_profile` existe en el 2.7.0 instalado; los valores van en **minúsculas con
guión bajo**, y en mayúsculas lanzan `InvalidArgumentException`.
→ ✅ **`throttle_rate` sí funciona:** `/imu` de 16,30 a **1,83 Hz** pidiendo 2. Es la palanca barata
para `/scan`, que es el 83 % del tráfico. Evidencia 68.
→ 🔴 **PERO NO ES UN CONTROL POR CLIENTE, y esa frase sola induce a creer que sí.** Misma causa que
  el QoS —una suscripción ROS compartida— y peor forma: `subscribe.py:225` hace
  `self.throttle_rate = min(f("throttle_rate"))` (y `:226` lo mismo con `queue_length`). **Gana el
  cliente MÁS RÁPIDO, para todos.** Un profesor que pida 1 Hz recibirá a 16,5 en cuanto **un alumno**
  esté suscrito sin límite en ese robot.
  → Sirve para **bajar tu propio coste cuando eres el único**; **no** para protegerte de los demás.
    Con 16 robots, una vista de flota **no** puede apoyarse en él: tiene que **suscribirse solo a
    topics baratos** (`/battery_state` + `/motor_status` = 0,48 kB/s por robot, **7,7 los 16**).
  → 📝 Y es la tercera vez que aparece la misma forma en rosbridge: **lo que un cliente pide, otro
    cliente se lo cambia**, sin aviso y sin error. Antes de usar cualquier parámetro de `subscribe`,
    mira si el fuente lo combina entre clientes.

**🔴🔴 ~~`rvr-NN.local` RESUELVE A CUATRO DIRECCIONES~~ — ✅ ARREGLADO EL MISMO DÍA, y el
navegador ya lo confirma.** Se conserva entero porque la forma del fallo vuelve.

✅ **Cerrado la tarde del 2026-08-04** con **una dirección por red** (evidencia 74): `[Match]
SSID=` de systemd-networkd elige el fichero por la red en la que esté, y en avahi `use-ipv6=no`
**más `publish-aaaa-on-ipv4=no`** — 🔴 **sin lo segundo no basta**, porque `use-ipv6=no` apaga el
*transporte* IPv6 y el registro `AAAA` **se seguía anunciando por el transporte IPv4**. Venía
comentado, o sea corriendo con su valor por defecto (`yes`).

✅ **Y el criterio que la evidencia 74 dejaba abierto está medido:** `ws://rvr-01.local:9090`
**ABRE en el navegador** — 4339 ms con la caché fría, 2331 ms caliente —, y el muro pinta
`rvr-01 · 7,67 V · en línea` **por nombre, sin override**. La resolución mDNS es casi todo el
coste y solo la primera vez: **2716 · 2710 · 2729 ms** con la caché vaciada contra **2 ms** con
ella caliente.

⚠️ **Lo que sigue sin probarse es el AULA**, y ahí está el riesgo real: `05-atriz-lab.network`
**nunca ha casado con nada**. Si el SSID difiere en un carácter, el robot cae al netplan
genérico y se queda **sin dirección estática** con 16 alumnos delante. Tampoco está probado que
sobreviva a un arranque en frío, que es justo lo que hará el robot 7.

---

**El fallo original, conservado porque la forma vuelve:**

Medido el 2026-08-04 por la mañana en el navegador, con el robot **encendido y sano**:

```
ws://rvr-01.local:9090     🔴 12 s sin abrir, sin error y sin cierre
ws://10.14.7.7:9090        🔴 12 s igual  <- LA MISMA FIRMA
ws://192.168.1.58:9090     ✅ abre
ws://192.168.1.200:9090    ✅ abre
```

El resolutor del sistema devuelve, **en este orden**: `fe80::da3a:ddff:fed6:c1ee` (IPv6
link-local **sin zona**, que el navegador no puede usar), `10.14.7.7` (la estática del
laboratorio), `192.168.1.58` y `192.168.1.200`. El navegador prueba en ese orden y **las dos
primeras no fallan: se cuelgan** — un SYN sin respuesta tarda ~21 s en rendirse, así que nunca
llega a las buenas.

→ 🔴 **Era la consecuencia directa de la decisión «estática + DHCP conviven en `wlan0`»**, que se
  verificó y se dio por buena porque el robot se muda de casa al aula sin tocar un comando. Era
  cierto **para el robot**; para un cliente significaba que **desde cualquier red al menos una de
  sus direcciones es un agujero negro**. 📝 **Y esa es la lección que sobrevive al arreglo: una
  decisión puede ser correcta desde un lado del cable y romper el otro.** La verificación se hizo
  entera desde el robot.
→ 🔴 **Y JavaScript no puede arreglarlo:** no hay API para enumerar lo que resolvió un nombre ni
  para elegir dirección. El cliente no puede competir entre ellas como hace el sistema operativo.
  Por eso la solución tuvo que ser del robot, no de la web.
→ ✅ En `atriz-lab` quedan **dos** piezas, y **ninguna sobra** aunque la causa esté cerrada: un
  **plazo de conexión de 10 s** —sin él un socket colgado **nunca llama a `onclose`**, así que la
  reconexión con espera creciente no llegaba ni a arrancar y el muro dejaba 16 conexiones
  colgadas; y un **robot apagado da exactamente la misma firma**— y una **dirección por robot**
  escrita a mano, que es el camino de escape para el día que el SSID del aula no case.
→ ⚠️ **Cuidado con el diagnóstico fácil, que aquí engañó DOS veces:**
  · `ping rvr-01.local` **funcionaba** (elige la `fe80` con su zona `%10`, 1 ms) y
    `Resolve-DnsName` listaba las cuatro sin quejarse. Las dos decían que el nombre estaba bien.
  · Y al arreglarlo, `getent ahosts rvr-01.local` **desde la Pi** devolvió una sola dirección
    mientras el PC seguía recibiendo dos. **`getent` no ve lo que la Pi anuncia al cable.**
  → **El testigo válido es el CLIENTE**, y en este caso concreto el navegador: `ping`,
    `Resolve-DnsName` y `getent` pueden dar verde los tres con el navegador colgado.
→ 📝 **La forma general: un fallo que se CUELGA es peor que uno que falla.** Sin `onerror` ni
  `onclose` no hay nada que reintentar, nada que registrar y nada que enseñar — el mismo perfil
  que el RVR dormido con el nodo vivo, el nodo muerto con systemd en verde, y el descriptor del
  LIDAR apuntando a un `/dev/ttyUSB0 (deleted)`.

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

**✅ CERRADO EL 2026-08-08: la PSK ya NO es legible.** `fmask=0177,dmask=0077` en `/etc/fstab`,
aplicado y **verificado por efecto**:

```
antes    -rwxr-xr-x  root:root  /boot/firmware/red.txt      ← lo leía cualquiera
después  drwx------  root:root  /boot/firmware              ← ni se puede entrar
         fmask=0177 · dmask=0077
```

→ 🔴 **Y `mount -o remount /boot/firmware` A SECAS NO LO APLICA: devuelve 0 y deja las máscaras
  viejas.** Medido: tras el remount, `findmnt` seguía dando `fmask=0022`. **Hizo falta REINICIAR.**
  Es la MISMA forma que el `chmod` de abajo, sobre el mismo fichero, con otra orden — dos maneras
  distintas de que el problema quede **abierto con aspecto de resuelto**.
→ 🔴🔴 **Y rompió el verificador: DÉCIMO falso positivo, el mismo día que el noveno.** Al cerrar el
  directorio, `[[ -f /boot/firmware/red.txt ]]` da falso y el guion decía **«no hay red.txt: la red
  se queda en DHCP»** sobre un fichero que está ahí. Peor que el caso de polkit: **mandaba a
  recrear el fichero que lleva la PSK**, y rehacerlo mal deja al robot sin red.
  ✅ Arreglado con un guardia `BOOT_LEGIBLE` que **distingue «no puedo verlo» de «no está»** — y en
  este caso el «no puedo verlo» **es la prueba de que está bien**, así que se reporta como ✅.
→ 🔴 **Y NADIE EN EL REPOSITORIO LO APLICABA.** `fase_1_higiene_so.sh` tocaba el `fstab` para el
  `noatime` de la raíz y nunca la línea de `/boot/firmware`: la imagen dorada sí lo llevaba (un
  `dd` copia el fstab) pero **`provision.sh` desde cero dejaba la PSK expuesta** — justo la
  divergencia que la regla «gana el script» existe para impedir. ✅ Añadido como paso 8bis/9,
  idempotente y con `findmnt --verify` antes de que un reinicio estrene el fstab.
→ 📌 **Le pasará a los 16 en cuanto la imagen dorada lleve el `fmask`**, que es justo lo que se
  quiere. Por eso se arregló en el verificador y no con un caso especial.

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

**🔴🔴 `set -e` + `(( t++ ))` MATA EL SCRIPT EN SILENCIO, Y ASÍ ESTUVO ROTA LA ESPERA DE
HARDWARE DE `atriz-robot.sh`.** Un post-incremento aritmético **devuelve el valor ANTERIOR**, y
`(( 0 ))` es falso → estado de salida **1** → con `set -e` el script muere ahí mismo, sin una
línea. Descubierto el 2026-08-04:

```bash
set -euo pipefail
esperar() { local t=0; while [[ ! -e $1 ]]; do sleep 1; (( t++ )); done; }   # 🔴 muere en la 1ª vuelta
esperar() { local t=0; while [[ ! -e $1 ]]; do sleep 1; t=$(( t + 1 )); done; }   # ✅ una asignación devuelve 0
```

→ **Las tres consecuencias, medidas:** la espera de 60 s para que udev cree los enlaces **nunca
  ocurrió** (moría en ~1 s, el `sleep`); el mensaje `🔴 /dev/ydlidar no apareció` era
  **inalcanzable**; y systemd solo veía `status=1/FAILURE` **sin una palabra de explicación**.
→ 🔴 **Y lo que lo hace peor: la salvaguarda estaba escrita contra el fallo que acabó causando.**
  Su comentario decía *«sin esto el launch arranca, no encuentra el puerto y el nodo queda vivo y
  mudo — el fallo más caro de diagnosticar de este proyecto»*. Costó cuatro intentos de cable
  porque el único error visible venía del `ExecStartPost` y apuntaba al launch.
→ **Búscalo con este patrón**, que es lo que lo encontró en un solo comando:
```bash
grep -rlE 'set -e' scripts/*.sh | xargs grep -nE '\(\(\s*[A-Za-z_]\w*(\+\+|--)\s*\)\)'
```
→ 📝 Misma familia que la de abajo: **una opción de bash que protege puede desactivar una
  protección**. Evidencia 69, apartado 10.

**🔴 LOS `setup.bash` DE ROS NO SON COMPATIBLES CON `set -u`** — `AMENT_TRACE_SETUP_FILES:
unbound variable`. Con `set -euo pipefail` matan el script antes de hacer nada, y el mensaje no
menciona ROS. Envuelve los `source` en `set +u` / `set -u`.
→ ⚠️ **Y búscalo en TODOS los scripts, no solo en el que falló.** Se arregló en
  `atriz-robot.sh` y no en `atriz-escaneo.sh`; en el primer arranque real bajo systemd el
  `ExecStartPost` murió con `status=1/FAILURE`, el servicio quedó `active (running)` y el
  barrido del LIDAR se quedó **encendido** — el estado que ese `ExecStartPost` existía para
  evitar.

**🔴🔴 LA PI NO TIENE RTC: LOS SERVICIOS QUE ARRANCAN CON ELLA QUEDAN SELLADOS ~20 HORAS EN EL
PASADO, Y `journalctl --since "-Nh"` NO LOS VE.** Medido el 2026-08-08:

```
arranque de la Pi          2026-08-08 12:07:53
driver, según systemd      2026-08-07 16:40:39   <- 19,5 h ANTES de arrancar
NTP sincronizó             2026-08-08 12:08:11   <- 18 s después del arranque

systemd-timesyncd: «System clock time unset or jumped backwards, restored from
                    recorded timestamp: Fri 2026-08-07 16:40:38»
```

La Pi arranca con el reloj **restaurado a la última marca guardada**, levanta los servicios, y
**después** NTP lo salta hacia delante. Todo lo que arranque en esos 18 s queda con marcas del
pasado.
→ 🔴 **Y mordió el mismo día:** se comprobó A11 —el `collision_monitor` descartando el LIDAR— con
  `--since "-6h"`, que **excluye justo el arranque**, que es cuando ocurre el fenómeno. El
  resultado (0 ocurrencias) salió correcto **por casualidad**.
→ **La regla: para cualquier cosa del arranque, `journalctl -b`. Nunca una ventana relativa.** Es
  la trampa de `date -u +%T` en versión nueva: una ventana relativa sobre un reloj que salta.
→ ⚠️ **`ExecMainStartTimestamp` no sirve para saber cuánto lleva vivo un servicio.** `NRestarts` y
  el PID sí. → 📌 **Le pasa a los 16 robots en CADA arranque**: ninguna Pi 4 tiene RTC. Evidencia 85.

**🔴🔴 `avanzar(0.20, 3)` NO SIGNIFICA 60 cm: EL POLÍGONO DE SEGURIDAD LO PUEDE PARTIR POR LA
MITAD, EN SILENCIO.** Medido el 2026-08-08 sobre la práctica 1 del curso: **26,4 cm** una vez y
**59,5 cm** la siguiente, sin tocar nada. El journal lo dice y el usuario lo vio:

```
12:58:21  Robot to slowdown for 40.000000 percents due to Precaucion polygon
12:58:23  Robot to continue normal operation
```

→ **Y el polígono es más ANCHO de lo que se suponía:**
  `[[0.36, 0.20], [0.36, -0.20], [-0.24, -0.20], [-0.24, 0.20]]` — 60 cm de largo × **40 de
  ancho**. Con el robot midiendo 21,7 de ancho, **cualquier cosa a menos de ~9 cm de un costado**
  lo frena al 40 %, aunque se esté alejando de ella.
→ **No es un fallo: es la capa de seguridad funcionando.** Pero **el alumno pide 60 cm, obtiene 26
  y no recibe ningún mensaje**, y cualquier práctica que dependa de la distancia —la 3 dibuja un
  cuadrado— sale deformada cerca de una pared o de una pata de silla.
→ ⚠️ Es la evidencia 49 con otra cara: allí un retroceso de 30 cm hizo 14 porque el polígono no
  sabe hacia dónde vas. **Aquí es el ancho.** Evidencia 85.

**🔴🔴 UN GUARDIÁN QUE CUENTA ITERACIONES EN VEZ DE SEGUNDOS DISPARA SOBRE UN SISTEMA SANO.**
`girar()` de `atriz.py` abortaba el giro a los **5,5° de 90 pedidos** —**saliendo con código 0**—
avisando «Odometría perdida o desconectada» con `/odom` a **16,54 Hz, σ 2,5 ms, peor hueco 81 ms**.

```python
MAX_SIN_CAMBIO = 5   # ~0.25 s a 20 Hz     <- cuenta VUELTAS, y SUPONE el ritmo
```

→ Tres defectos y uno solo basta: **mide en la unidad equivocada** (supone que el bucle va a
  20 Hz, y el propio fichero admitía «nada de esto está medido sobre el robot»), **el margen era
  3× y no 10**, y **al disparar mentía sobre la causa** — manda a buscar una avería inexistente,
  misma familia que `Failed to get scan` con el barrido apagado a propósito.
→ 🔴 **El modo de fallo es el peor: no falla, MIENTE BAJITO.** Termina, imprime su resultado y
  devuelve 0 con el robot a 5°. Un `if` sobre el código de salida no lo ve. Reproducido **1 de 4**.
→ 🔴 **Y EL PEOR HUECO NO ES EL DE RÉGIMEN PERMANENTE.** Medido el mismo día, sin buscarlo, al
  reiniciar el driver: **régimen permanente 78-81 ms (σ 2,0-2,5), recién reiniciado 325,7 ms
  (σ 16-19)**. O sea que el umbral viejo de 250 ms estaba **por debajo de un hueco que ocurre de
  verdad**: un `girar()` en los primeros segundos tras arrancar el driver abortaba por
  construcción. **Una medida tomada en un solo régimen no caracteriza el fenómeno.**
→ ✅ **Arreglado**: tiempo de reloj desde la última muestra nueva, **2,0 s** = 6× el peor hueco
  REAL (y 25× el permanente), criterio extraído a `odom_rancia()` —**el fallo era justo que no se podía comprobar en
  ningún sitio**— y **7 tests que discriminan** (con el umbral viejo fallan DOS). 4/4 en el robot,
  ⚠️ que **no basta** para un fallo intermitente: lo que sostiene el arreglo es estructural.
→ ⏳ **Y el disparador NO se conoce.** Sesión entera de aislamiento el 2026-08-08: **siete**
  hipótesis descartadas midiendo —huecos reales, sellos repetidos, arranque del LIDAR, `/scan`
  compitiendo en el ejecutor, la ventana de arranque, el robot moviéndose, y un proceso
  competidor a 500 Hz— y **no reproducido en ~32 tandas ni en 5 minutos seguidos**: la racha
  nunca pasó de **1** (~100 ms) contra un umbral de 250. **Un fallo que sale 1 de 4 y luego no
  sale en 32 no está entendido**, y no se presenta como cerrado. Lo que sostiene el arreglo es
  estructural y el margen (2,0 s son 20× el peor caso reproducible). Evidencia 85, apartado 1c.
→ **La regla general: un umbral en unidades del observador, no del fenómeno, es un falso positivo
  esperando.** Y ya está escrita en este fichero para otro caso — «un umbral de silencio en
  milisegundos no es transferible entre topics de ritmos distintos». Evidencia 85.

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

**🔴🔴 Y `ABORTED` DE NAV2 TAMPOCO ES DE FIAR: EL ROBOT PUEDE HABER LLEGADO.** Medido el
2026-08-08 (evidencia 88). `bt_navigator` tenía `default_server_timeout: 20` —**veinte
milisegundos** para que el controlador acusara recibo— y se rendía mientras `controller_server`
conducía:

```
  22:18:57  Received a goal, begin computing control effort   <- el controlador SI lo recibio
  22:18:57  Timed out ... Aborting handle · Goal failed
  22:19:07  Reached the goal!                                 <- DIEZ SEGUNDOS DESPUES
```

El robot recorrió **67 cm y llegó**, con la acción marcada como fallida. ✅ Subido a **1000 ms**.
→ 🔴 **Reinterpreta tres tandas dadas por fallidas: el robot había navegado bien las tres.** Se
  habían atribuido a saturación de la Pi —real y medida— pero **la causa próxima era el plazo**.
→ 🔴 **Las DOS direcciones del desenlace fallan**, así que `navigate_to_pose` **no informa de lo
  que pasó**: `SUCCEEDED` puede estar equivocado en 41 cm y `ABORTED` puede ser un robot que
  llegó. Una pantalla que diga «no se pudo llegar» sobre un robot en el destino es tan mala como
  la contraria.
→ ✅ **Lo que sí se puede mostrar es el desplazamiento por `/odom`**, que acierta a 0,3-4,2 cm.
  `atriz-lab` lo pinta en el desenlace desde el 2026-08-09.
→ 📝 **Y la forma general: 20 ms era un plazo puesto sin medir contra qué.** El ruido de
  planificación de esta máquina llega a **326 ms** al reiniciar el driver — dieciséis veces el
  plazo. Misma familia que el `MAX_SIN_CAMBIO = 5` de `girar()`, que contaba vueltas suponiendo el
  ritmo.

**🔴🔴 UN MAPA QUE NO ES DEL SITIO HACE QUE NAV2 DIGA «LLEGUÉ» ESTANDO A MEDIO METRO, Y NO HAY
NINGÚN OTRO SÍNTOMA.** Medido el 2026-08-07 con el mismo robot, el mismo recorrido de 80 cm y los
mismos parámetros de AMCL — **lo único distinto era el mapa**:

```
                          mapa rancio    tanda 1    tanda 2
  error de AMCL              45,0 cm      8,9 cm    15,2 cm
  corrección map -> odom      0,424 m     0,028 m    0,021 m
  distancia real al objetivo  41,3 cm      6,1 cm    11,8 cm
  ¿dentro de los 10 cm?        🔴 NO       ✅ SÍ      🔴 NO
  lo que dijo Nav2            ✅ ÉXITO    ✅ ÉXITO   ✅ ÉXITO   <- 🔴 LAS TRES
```

→ **El objetivo termina `SUCCEEDED`, `/estado_navegacion` dice `FUNCIONANDO`, y no hay una línea
  de error en ningún log.** Nada dentro del sistema lo detecta: lo destapó **una cinta métrica**.
  Misma familia que el RVR dormido con el nodo vivo y el nodo muerto con systemd en verde, pero
  peor: aquí el componente **contesta que le fue bien**.
→ 📌 **Mapear es parte de MONTAR EL AULA, no una tarea de una sola vez.** Si se mueven las mesas,
  se remapea. Y la **imagen dorada sale SIN mapa a propósito** (`fase_6` borra `~/mapas` y vacía
  `ATRIZ_MAPA`): clonarlo repartiría a los 16 un mapa que en 15 ni siquiera es del mismo sitio.
→ ⚠️ **Y fueron DOS fallos distintos con el mismo síntoma aparente**, que es lo que costó tres
  tandas: el marco `map -> odom` rotando **98°** era la recuperación de «robot secuestrado»
  (`recovery_alpha_slow/fast`, evidencia 82); el error de **45 cm en posición** con el marco ya
  quieto era el mapa (evidencia 84). **Arreglar el primero dejó el segundo en pie**, y durante un
  rato pareció que no había mejorado nada.
→ 🔴 **AMCL sigue siendo peor que la odometría** incluso con el mapa bueno: **8,9 y 15,2 cm contra
  4,2 y 2,2** — un factor de 4. Lo que cambió es la magnitud, de absurda a molesta.
→ 🔴🔴 **Y OJO CON LA CIFRA BUENA: «paró a 6,1 cm, dentro de la tolerancia» ERA n=1 Y LA RÉPLICA
  LO DESMINTIÓ** (11,8 cm, fuera). **La cifra honesta es ~10-12 cm**, y sobre todo: **Nav2 dijo
  `SUCCEEDED` en las tres, a 6,1, a 11,8 y a 41,3 cm.** Nada que prometa precisión puede apoyarse
  en el desenlace del objetivo. n=2. Evidencias 81-84.

**🔴🔴 EL `ABORTED` DE NAV2 TAMPOCO ES DE FIAR: `default_server_timeout` SON 20 ms Y ABORTA
OBJETIVOS QUE SE COMPLETAN.** Medido el 2026-08-08 (evidencia 88), leyendo el journal, que es lo
que no se había hecho las tres veces anteriores:

```
22:18:57  Received a goal, begin computing control effort   <- el controlador SÍ lo recibió
22:18:57  Timed out while waiting for action server to acknowledge … follow_path
22:18:57  [navigate_to_pose] Aborting handle · Goal failed
22:19:07  Reached the goal!                                 <- DIEZ SEGUNDOS DESPUÉS
```

→ **`bt_navigator` se rinde esperando el ACUSE mientras `controller_server` conduce.** El robot
  recorrió 67 cm y llegó, con la acción marcada como fallida.
→ 🔴 **Reinterpreta las tres tandas del 07 y 08 dadas por fallidas: el robot había navegado bien
  las tres.** Se atribuyeron a saturación de la Pi —que era real y medida— pero la causa próxima
  era el plazo.
→ **20 ms está MUY por debajo del ruido de planificación de esta máquina**: un proceso se queda sin
  CPU hasta **326 ms** al reiniciar el driver y ~105 ms en régimen permanente. Misma forma que el
  guardia de `girar()` rindiéndose a los 250 ms. ✅ **Subido a 1000 ms** y verificado por efecto.
→ 🔴 **Y para la web: las DOS direcciones fallan.** `SUCCEEDED` puede estar equivocado en 41 cm y
  `ABORTED` puede significar que llegó. **El desenlace de la acción no informa de lo que pasó.**

**🔴 `/initialpose` CON SELLO `now()` SE RECHAZA: «extrapolation into the future».** El sello iba
**69 ms** por delante de lo último que tenía TF, y AMCL la descartaba. Pasó en **las 10 tandas de
navegación de la historia del proyecto** sin que nadie mirara: el banco creía fijar la pose y no la
fijaba nunca.
→ 📌 **El daño fue menor y conviene decir por qué**, para no exagerarlo: AMCL arranca en (0,0) por
  su `set_initial_pose: true`, y el journal confirma `Begin navigating from current location
  (-0,02 · 0,00)`. La pose de partida era correcta **por otra vía**. Las evidencias 83 y 84 se
  sostienen.
→ ✅ **Arreglo: sello `0`**, que en tf2 significa «usa la transformada más reciente». Evidencia 88.

**📌 `/estado_navegacion` DICE QUÉ MAPA ES Y DE CUÁNDO — `hay_mapa` a solas no basta.** Añadidos
`mapa_nombre` y `mapa_edad_s` el 2026-08-08 (13 campos), porque un mapa que no es del sitio hace que
Nav2 declare éxito **a 41,3 cm sin ningún otro síntoma** y **la única defensa es que una persona
mire la fecha** — y quien tiene delante a la persona es la web, que solo recibía un booleano.
→ ⚠️ **Es el `mtime` del fichero, NO «cuándo se mapeó ese espacio».** Copiar un mapa viejo lo
  rejuvenece. Por eso va el **nombre** al lado: el robot da los dos datos y la persona decide.
→ Verificado en el topic: `mapa_nombre='cuarto3.yaml'`, `mapa_edad_s=104976` (1,22 días) contra un
  fichero de hace ~29 h.

**🔴🔴 EL MAPA DE slam_toolbox ENGORDA LOS OBJETOS ~5 cm POR LADO, Y ESO CIERRA HUECOS QUE SÍ
CABEN.** Medido el 2026-08-09 (evidencia 91) con los tres instrumentos sobre la misma fila, hueco
físico de 45 cm:

```
LIDAR crudo (retornos)   ... (82,-21)   [HUECO 44,8 cm]   (82,+24) ...
cinta del usuario                          45 cm
MAPA DE SLAM en x=85     ocupado en -20, -15  y en +20  ->  hueco 35 cm
```

→ 🔴 El mapa marca ocupado a **-15 cm cuando el objeto real empieza en -21,3**. Inflando 14,5 cm (el
  radio inscrito) desde cada borde del mapa, la ventana transitable queda en **una celda a coste 96**,
  y en la fila exacta de los objetos **en ninguna**. NavFn no puede cruzar y **traza un RODEO**: 168-233 %
  de largo, 68-115 cm de desvío lateral, en un cuarto con 55 y 67 cm a los lados.
→ ✅ **Regla con número, no intuición:** `hueco mínimo ≈ 2 × (14,5 inscrito + 5 engorde + 5 celda) ≈ 49 cm`
  para que sea TRANSITABLE, y **entre 45 y 60 cm** para que además sea barato y Nav2 no prefiera rodear.
  La única tanda con plan recto fue la de 60 cm (14 cm de desvío).
→ 🔴🔴 **ALCANCE, Y NO ES UN MATIZ: eso vale CON SLAM.** Lo destapó el usuario preguntando «pero en
  la prueba inicial con AMCL sí pasó por 45 cm». Es cierto, y se repitió: con AMCL sobre `cuarto3`
  —hecho sin la puerta— el plan sale **RECTO** (109 %, 13 cm) en cuatro consultas. En la misma fila:

```
línea de la puerta (x=85 cm), lateral -40..+40, misma escena, mismos 45 cm
  con AMCL    99  99  99 100  99  99  99 | 84  84 | 99  99  99 100 ...  canal ABIERTO
  con SLAM   100  99  99 100 100 100  99   99  99   99  99  99 100 ...  canal CERRADO
```

  Con AMCL la puerta la marca **sólo la capa de obstáculos del LIDAR**, que es fina y exacta; con
  SLAM entra en la **capa estática** ya engordada. **La regla de los 49 cm sigue siendo la buena
  para la F7 de la aceptación, que lanza SLAM** — que es donde apareció el FALLO.
→ ⏳ **La casilla que falta, y es la del aula: AMCL sobre un mapa que SÍ contiene los objetos.** Los
  mapas del aula se hacen con slam_toolbox y se guardan, así que lo que estuviera puesto al mapear
  entra ya engordado en el fichero. **Predicción NO VERIFICADA: se comportará como SLAM.**
→ ✅ **Y explica el único `FALLO` de la prueba de aceptación del 2026-08-08:** montaje demasiado justo.
  Cadena completa: hueco 45 → mapa 35 → inflación lo cierra → rodeo → `collision ahead` →
  `failure_tolerance: 0.3` → `Controller patience exceeded` → `ABORTED`.
→ ⏳ **De dónde salen esos 5 cm: NO VERIFICADO.** Candidatos sin medir: celdas de 5 cm, el modelo de
  ocupación de slam_toolbox, error residual de pose.

**🔴🔴 UN OBSTÁCULO DENTRO DE `Aproximacion.radius` INMOVILIZA AL ROBOT POR COMPLETO — NI SIQUIERA
PUEDE ALEJARSE.** (Eran 18 cm hasta el 2026-08-09; desde entonces **15**, ver más abajo.) Medido el 2026-08-09 (evidencia 93) con la pared **detrás** a 16,8 cm y 188 cm libres
delante, mandando por `/cmd_vel_raw`:

```
AVANZAR alejándose de la pared  ->  0.0 cm    monitor: APROXIMACION
GIRAR en el sitio               ->  0.0°      monitor: APROXIMACION
RETROCEDER hacia la pared       ->  0.0 cm    monitor: APROXIMACION
```

→ 🔴 `approach` escala el mando ENTERO —lineal y angular— por el tiempo hasta colisión, y con un
  punto **ya dentro** del círculo (`Aproximacion.radius`) ese factor es 0, **sin mirar si el
  movimiento acerca o aleja**. Sólo sale a mano.
→ ✅ **Y girando NO rozaría nada**: con el monitor puenteado dio **359,6° y 358,8° de 360**, 12,6 s
  (igual que en campo abierto), y el usuario mirando: «no ha tocado la pared en ningún momento».
  El radio circunscrito del robot es **14,06 cm** —18 × 21,6 cm medidos con cinta el 2026-08-09, LIDAR
  centrado y validado contra el propio LIDAR con 2 mm de error— contra un círculo de 18: **el monitor es más gordo que
  el robot.**
→ 🔴🔴 **`Aproximacion.radius` ES INERTE EN CALIENTE, y esto retracta una conclusión del mismo día.**
  `ros2 param set` lo guarda y `get` lo devuelve, pero el `collision_monitor` **no reconstruye el
  polígono**. Demostrado con 0,30 —que debería frenar mucho antes— dando el perfil IDÉNTICO a 0,18
  y a 0,15: `mando ≈ 0,0125 × (distancia_LIDAR − 18 cm)` en los tres. **Cambiar el radio exige
  editar el YAML y reiniciar**, o sea es un cambio de imagen dorada para los 16, no un botón.
  ⚠️ Y la prueba que «aislaba la causa» tenía además el control roto: la pared estaba a 18,3 cm y no
  a 16,8, o sea **ya fuera del círculo**. Dos fallos independientes en la misma medida.
→ ✅ **Hueco al parar MEDIDO con el radio real (0.18), a 0,25 m/s: 9,3 · 9,4 · 9,3 · 9,4 cm**
  (n=4, 1 mm de dispersión). Cuadra con la asíntota `18 − 9,5 = 8,5` más ~1 cm de arrastre, y con
  los 9,9 cm del fichero 17. El escalón de 0,25 a 0,100 a ~36 cm es el polígono `Precaucion`.
→ 🔴 **Contradice a la evidencia 19**, que anotó «PUDO SALIR: retrocedió 58 cm» — allí el obstáculo
  estaba **al lado**, hoy **detrás**. ⏳ Por qué una geometría deja salir y la otra no: NO VERIFICADO.
→ ⏳ **NO se ha tocado la configuración**: `radius` fija a la vez el hueco al parar (`≈ radius −
  media longitud`) y el pasillo mínimo (`≈ 2 × radius`), y el 0.18 está respaldado por «para a
  20,8 cm sin chocar» de la aceptación. Bajarlo exige repetir esa medida. 👤 Decisión del usuario.
→ 💡 Idea anotada y sin implementar: el problema no es el radio, es que `approach` **no distingue
  acercarse de alejarse**. Mitigación barata: que `atriz.py` lea `/collision_monitor_state` y avise
  («no me muevo: hay algo a 17 cm») en vez de dejar al alumno mirando un robot mudo 40 s.

**🔴 EL PUNTO CIEGO DEL LIDAR SOBRESALE DEL CHASIS POR DELANTE Y POR DETRÁS — 1 cm QUE NINGÚN
POLÍGONO CUBRE.** El manual y `collision_monitor.yaml` afirmaban lo contrario («cae dentro del
chasis, no hay zona muerta»), el manual **con los números correctos y la conclusión mala**:
`range_min 0.100 > media longitud 0.091`. Medido el 2026-08-09 con el robot **tocando** la pared:
**10 277 rayos traseros descartados** y sólo uno oblicuo superviviente, recortado en 10,02 cm — que
basta para que el `collision_monitor` siga congelando al robot.
→ ✅ Geometría medida con cinta desde el **eje del LIDAR**: 9,0 detrás · 10,8 a cada costado →
  circunscrito **0,1406**. Validada contra el propio LIDAR con **2 mm** (12,20 leídos vs 12,00
  predichos separando el robot 3 cm, n=8268 rayos, perfil plano en ±20°).
→ 🔴 **Y ojo con las medias dimensiones: el RVR es MÁS ANCHO QUE LARGO.** Media longitud **0,090**,
  media anchura **0,108**. Los `0.109` que aparecen por el proyecto son del URDF **cruzado de eje**;
  el fichero 19 ya lo avisaba en 2026-07-31 y aun así se volvieron a usar el 2026-08-09.
→ ⏳ Borde DELANTERO en conflicto: cinta 9,0 vs URDF 10,0. **NO VERIFICADO.**

**✅ `Aproximacion.radius` BAJADO DE 0.18 A 0.15 EL 2026-08-09, CON TODO MEDIDO (evidencia 94).**
La clave es una simetría: **`banda de inmovilización` = `margen ante el error del LIDAR` =
`radius − 0.1442`** — son el mismo número, así que no se puede encoger uno sin el otro.

```
radius   banda de trampa   hueco al parar 0.40 m/s   aceptación F6
 0.18         3.6 cm            10.9 cm               pasa
 0.15         0.6 cm             7.4 / 6.6 cm         pasa      <- el actual
 0.145        0.1 cm             (sin medir)          — margen < ruido del LIDAR
```

→ ✅ Verificado a la MISMA distancia con los dos valores: pared a 15,8 cm de `base_footprint`,
  con 0.18 **congelado**, con 0.15 **gira 34,9° y se aleja 5,7 cm**.
→ 🔴 **No se baja más:** con 0.145 el margen (0,1 cm) queda por debajo del ruido de LIDAR **medido**
  (±0,3 cm): autorizaría a girar cuando el robot no cabe.
→ ⚠️ **No arregla el centímetro CIEGO** de `range_min`, que no depende de este parámetro, ni los
  0,6 cm de banda que quedan.
→ 🔴 **NO SE PUEDE PROBAR EN CALIENTE**: hay que editar el YAML y reiniciar `atriz-robot` (👤 `sudo`).
  `verificar_robot.sh` da **FALLO** si encuentra 0.18 en un robot: significa que no le llegó el
  fichero nuevo.

**🔴 UNA MÉTRICA QUE DA EL MISMO NÚMERO PARA EL ÉXITO Y PARA EL FRACASO NO ES UNA MÉTRICA.**
El 2026-08-09 se midió el error de un giro de 360° como `wrap(yaw_final − yaw_inicial)` contra un
pedido de `((360+180) % 360) − 180 = 0`. **Una vuelta completa da 0; estar quieto también.** Se
imprimió «error −0,1°» tres veces con el robot PARADO contra una pared, y se llegó a escribir una
evidencia entera concluyendo lo contrario de la verdad. Lo paró el usuario mirando el robot: «es que
ni siquiera giró».
→ ✅ Para giros, **INTEGRA el acumulado** (`Σ|Δyaw|`), no restes rumbos. Y `girar()` **devuelve los
  grados que giró de verdad**: úsalo.
→ 📌 Los «40,5 s» que parecían un giro lento eran el plazo de `girar()` agotándose:
  `|objetivo|/0.20 + 5.0` = **36,4 s** para 360°.

**🔴🔴 NAV2 PUEDE ARRANCAR MAL SIN DECIRLO, Y SU «PLAN PERFECTO» ES EL SÍNTOMA.** El 2026-08-09
(evidencia 97) se lanzó `nav2.launch.py` **4 s después** de `localizacion.launch.py`, con el barrido
apagado, así que AMCL aún no publicaba `map -> odom`:

```
[global_costmap] Failed to activate global_costmap because transform from base_footprint to map ... timed out
[lifecycle_manager_navigation] Failed to bring up all requested nodes. Aborting bringup
```

→ 🔎 **Y las consultas de plan salieron «perfectas»: 139 cm para 140, 3,5 cm de lateral, las cuatro
  idénticas.** Es la firma de un costmap **VACÍO** — NavFn sin obstáculos devuelve la recta. Se
  estuvo a punto de escribirlo como resultado.
→ 🔴 **`navigate_to_pose` y `compute_path_to_pose` EXISTEN Y RESPONDEN aunque el arranque haya
  abortado.** Que el servidor de acción conteste no prueba nada.
→ ✅ **Antes de creerte cualquier medida de planificación:**

```bash
ros2 lifecycle get /planner_server                 # active [3]
ros2 lifecycle get /global_costmap/global_costmap  # active [3]
```

→ ⚠️ **Y el orden importa:** `nav2.launch.py` necesita `map -> odom` **ya publicándose** —o sea AMCL
  localizado, o sea **el barrido encendido**—. Lanzarlo pegado al de localización no basta.
→ 📌 La señal estaba a la vista: el suscriptor al costmap recibía **0 mensajes**. Se leyó como «fallo
  de mi suscriptor» y se reintentó dos veces antes de mirar el log.

**🔴🔴 UN PASO DE UNA SOLA CELDA PARPADEA, Y NAV2 PLANIFICA A VECES SÍ Y A VECES NO.** Medido el
2026-08-09 (evidencia 97) con el robot **quieto**, el costmap poblado y todo en `active`: ocho
consultas idénticas dieron **3 planes y 5 `SIN CAMINO`**. Muestreando el costmap 49 veces en 75 s:

```
x= 90 y= +0   84..99   >=99 en 19/49   <- LA ÚNICA celda abierta de esa fila
x= 95 y= +5   96..99   >=99 en 24/49
resto de la banda -15..+15 cm: 99/100 en las 49 muestras
```

→ 🔴 **El paso tiene UNA celda de ancho (5 cm) y esa celda cruza el umbral de 99 sola**, por el ruido
  del LIDAR (±0,3 cm medido). NavFn es determinista: lo que cambia es el costmap.
→ ✅ **PREDICHO Y CONFIRMADO el mismo día**, que es lo que le da valor: se escribió «a 60 cm habrá
  3 celdas y 8 de 8 consultas» **antes** de tocar nada, el usuario ensanchó a 61,1 cm y salió
  exactamente eso — mediana de **3 celdas** en la fila de pinza, **0 cierres en 50 muestras**, y
  **8 de 8** planes idénticos.

```
              47,4 cm                61,1 cm
fila x=90     1 celda · cerrada 19/49    2-3 celdas · cerrada 0/50
consultas     3 de 8                     8 de 8
```

→ ✅ **Y da la regla general para dimensionar un paso: no cuentes centímetros, cuenta CELDAS
  TRANSITABLES en la fila más estrecha, y ten al menos 2-3.** Con `resolution: 0.05` eso son ~10-15 cm
  de holgura sobre el mínimo geométrico. Explica los 60 cm del guion, que eran empíricos.
→ ✅ **LA CURVA, medida con tres anchos el 2026-08-09 (evidencia 97):**

```
hueco     celdas en la pinza      consultas    travesía real
38,6 cm   0 · cerrada 37/37        0 de 6      no intentada (no hay paso)
38,9 cm   —                        0 de 8      —
41,1 cm   —                        0 de 8      —
47,1 cm   1 · cerrada 19/49        3 de 8      3 de 3, DEGRADADA (5x desvío, 2,7x tiempo)
61,1 cm   2-3 · cerrada 0/50       8 de 8      1 de 1, limpia en 7,8 s
```

  ✅ **TRES REGÍMENES, y es lo operativo: `< ~45 cm` no pasa · `~47-55` pasa y cuesta · `> 55`
  estable.** Para el aula: **60 cm**, que es lo que ya exige el guion de aceptación.
  🔴 **Y AQUÍ CAYÓ UNA FÓRMULA MÍA, que es lo que hay que recordar:** se escribió que la primera
  celda aparecía en `2 × (14,5 + 5) = 39 cm`, y con 38,6 cerrado el ajuste parecía perfecto — llegué
  a escribir que era «casi incómodo de lo bueno». **Casualidad.** A 38,9 y a 41,1 sigue cerrado: el
  umbral está **entre 41,1 y 47,1**. **Un punto que casa no valida un modelo.**
  ⏳ Sin distinguir: si es que **la rejilla no se alinea con el hueco** —las celdas son fijas en el
  marco del mapa, así que el umbral dependería de DÓNDE está la puerta y no sólo de su ancho— o si
  el radio efectivo es mayor de 0,145. **NO VERIFICADO.**
→ 🔴🔴 **PERO LA TASA DE CONSULTA NO PREDICE FALLO: PREDICE COSTE**, y esto corrigió una conclusión
  precipitada del mismo día. Con el robot **pasando de verdad** por ese hueco de 47 cm: **3 de 3 con
  éxito**, porque Nav2 **replanifica continuamente** —16, 15 y hasta **35 planes** en un solo
  trayecto— y le basta con que el hueco esté abierto en ALGÚN instante. Lo que se degrada es el
  coste: **hasta 5× más desvío lateral y 2,7× más tiempo** que con 61 cm (29,6 cm y 52,3 s contra
  5,9 cm y 7,8 s).
→ 🔴🔴 **Y EL FALLO DE MÉTODO QUE LO DESTAPÓ, que es el que hay que no repetir: se midieron ocho
  consultas y CERO travesías.** Lo vio el usuario: «¿por qué lo mandas a que pase? No lo hemos
  visto». `compute_path_to_pose` devuelve una **promesa**: que exista ruta no dice que el
  controlador la ejecute, ni que el `collision_monitor` la permita, ni que el robot quepa — y las
  tres pueden fallar por separado. **La consulta mide si el paso EXISTE; sólo la travesía mide lo
  que cuesta cruzarlo.**

**🔴 LO QUE HACÍA RODEAR A NAV2 ERA UN MAPA DE CUATRO NODOS, NO «SLAM CONTRA AMCL».** Cerrada la
casilla que faltaba (evidencia 97), con el mismo escenario y el mismo hueco:

```
localización   mapa                                   plan
AMCL           cuarto3, SIN objetos, 4,3 m de error   RECTO 109 % · 13 cm
SLAM           mapa VIVO de 160 cm (4 nodos)          RODEA 168-233 % · 68-115 cm
AMCL           mapa nuevo, CON objetos, 781 cm        RECTO 102 % · 8,3 cm
```

→ 🔴 **Consecuencia operativa: la fase F7 de la aceptación ARRANCA SLAM Y NAVEGA INMEDIATAMENTE**, o
  sea sobre un mapa de segundos — casi vacío por construcción. Es una explicación más profunda del
  `FALLO` original que «el hueco era estrecho». ⏳ Si F7 debe mapear antes de navegar: **sin decidir**.

**🔴 UN SISTEMA QUE ACUMULA NO SE JUZGA CON UNA FOTO: HACE FALTA LA CURVA.** El 2026-08-09 se
concluyó que «el mapa de slam_toolbox está congelado» a partir de **160 cm de vaivén y un giro de
360°** — y era **falso**: con `minimum_travel_distance: 0.3` eso son 4 nodos, y un giro de 360° con
un LIDAR de 360° **no aporta información nueva**. Conduciendo de verdad el mapa crece monótonamente:

```
recorrido    nodos   ocupadas   libres   desconocido
     0 cm        4         54      549       89,3 %
   276 cm       10        406     2822       45,9 %
  1346 cm       30        606     3029       41,4 %
```

→ ✅ **Regla operativa con número: un mapa utilizable necesita VARIOS METROS de recorrido.** Con ~3 m
  el desconocido baja del 90 al 46 %. `min_pass_through: 2` descarta las celdas cruzadas por un solo
  rayo, así que pocos nodos = mapa vacío, y es lo correcto.
→ 🔴 **Y el precedente estaba delante todo el rato: `cuarto3` existe y es un mapa de verdad.** Si
  slam_toolbox estuviera roto, no existiría. Evidencia 96.
→ ⚠️ **El coste no fue la conclusión, fue el canal:** el falso defecto llegó a `ESTADO_ACTUAL.md`,
  que es lo que lee el PC, presentado como el bloqueo principal de la Fase 6.

**⚠️ Lo que se afirmó y queda RETIRADO (se conserva porque la forma del fallo vuelve):** Medido el 2026-08-09:
**49 celdas ocupadas** para un cuarto entero (una pared de 15 m a 5 cm serían ~300), contenido
**idéntico celda por celda** tras 360° de giro y 160 cm de vaivén, republicando cada 5 s con sello
fresco y con 4 nodos en el grafo. El LIDAR estaba sano (227/270 rayos, 11,7 Hz, 360°).
→ 🔴 **Comprueba el mapa por su CONTENIDO, no porque `/map` se publique.** Cuenta celdas ocupadas y
  compáralas con la geometría del sitio; un `slam: FUNCIONANDO` no dice nada de esto.
→ ⏳ Causa **NO VERIFICADA**, y es prioritaria: es la ruta con la que se hacen los mapas del aula.
→ 🔴 Y obliga a **matizar la evidencia 91**: su «el mapa engorda los objetos ~5 cm por lado» se
  dedujo de tres celdas sobre un mapa así. El efecto en el costmap sigue medido; el mecanismo no.

**✅ `compute_path_to_pose` PLANIFICA SIN MOVER EL ROBOT — ÚSALO ANTES DE GASTAR BATERÍA.** Es la
acción que `bt_navigator` usa por dentro; llamada suelta devuelve la ruta sin encadenarla al
controlador. **Cuatro tandas de robot en marcha no distinguieron «Nav2 traza recto y el robot no
sigue» de «Nav2 traza un rodeo»; una consulta de dos minutos sí.** Herramienta:
`00_auditoria/evidencia/mediciones_banco/consultar_plan.py`.

**🔴 `99` EN EL COSTMAP PUBLICADO NO ES «CASI LETAL»: ES EL RADIO INSCRITO**, y para NavFn es tan
infranqueable como `100`. El umbral que hay que mirar es **99**, no 100. Costó una lectura entera
mal interpretada el 2026-08-09.

**🔴 MOVER EL ROBOT A MANO ES UN TELETRANSPORTE PARA SLAM**, igual que poner la odometría a cero con
`/set_pos_and_yaw`. slam_toolbox sigue registrando barridos desde un origen que se movió bajo sus
pies y **el mapa queda embadurnado** (medido: 40 % letal, el robot y el objetivo en bolsas separadas
por un muro inexistente, planificador fallando 8 veces).
→ ✅ Después de recolocar el robot a mano, **reinicia SLAM**. AMCL sí lo encaja; SLAM no.

**🔴 EL SUPERVISOR RECHAZA SLAM CON AMCL VIVA, Y AL REVÉS** —«SLAM y AMCL son excluyentes»—: los dos
publican `map -> odom`. Para la variante con SLAM hay que lanzar `nav2.launch.py` **a mano**, como
hace `prueba_aceptacion.py`. `atriz-nav.sh` lanza `localizacion.launch.py` y `nav2.launch.py` por
separado, así que la variante es sustituir el primero por `slam.launch.py`.

**⏳ `failure_tolerance: 0.3` en `controller_server`: el controlador aborta tras 0,3 s sin poder
generar mando.** Mismo patrón que el `default_server_timeout: 20` de la evidencia 88. **NO SE HA
TOCADO**: no está medido que subirlo arregle nada y con el mapa estrecho el rodeo seguiría ahí.

**🔴🔴 METER OBJETOS EN UNA HABITACIÓN YA MAPEADA DESPLAZA A AMCL MÁS DE UN METRO.** Medido el
2026-08-09 (evidencia 90) con una puerta de dos cajas en un pasillo, sobre el mapa `cuarto3` hecho
dos días antes con el pasillo despejado:

```
                 planificador   desvío lateral   corrección map->odom
   hueco 60 cm     0 abortos         14 cm        —
   hueco 45 cm     0 abortos         15 cm        0,27 -> 1,02 m
   hueco 30 cm     0 abortos        116 cm        0,60 -> 1,21 m
   hueco 30 cm 2ª  0 abortos        156 cm        0,00 -> **1,68 m**
```

→ 🔴 **Para el aula es directo: si un alumno deja una silla donde no estaba, la navegación se va al
  traste** — y con `SUCCEEDED` de por medio. Precisa la regla del mapa fresco con un mecanismo:
  **no hace falta que el mapa sea viejo, basta con AÑADIR objetos.**
→ 🔴🔴 **PERO LA ATRIBUCIÓN DE CAUSA DE ESA TANDA ESTÁ RETIRADA (evidencia 91, mismo día).** Se
  escribió que el robot se desviaba porque AMCL casaba contra un mapa sin los objetos. Se repitió
  **con SLAM** —que mapea la puerta en vivo, así que ese mecanismo no puede darse— y el robot
  **falló igual, con `map -> odom` en 0,035 m**. Las medidas de arriba son buenas; la explicación no.
  Los desvíos laterales **eran el plan**, no AMCL perdiendo al robot: Nav2 rodeaba.
→ ✅ Lo que SÍ sigue en pie de esa tanda: la deriva de AMCL hasta 1,68 m es real, y para el aula
  vale igual — **si un alumno deja una silla donde no estaba, la localización se degrada más de un
  metro** y con `SUCCEEDED` de por medio.
→ 🔴 **Y una predicción mía que falló:** con 45 cm de hueco el margen es 11,9 cm por lado contra un
  `robot_radius` de 14,5, así que «debería fallar». **Pasó sin despeinarse** — pero con la
  localización rota, o sea que la tanda no probaba el hueco. Con la localización sana **falla**.

**🔴 `load average` NO MIDE SATURACIÓN DE CPU EN ESTA MÁQUINA, Y SE USÓ COMO SI LA MIDIERA.** Con
`load average` marcando **8,85**, medido con `vmstat` y `top`:

```
r = 8-18 ejecutables · b = 0 bloqueados · wa = 0,0 %
CPU 60-75 % usada · **25-39 % OCIOSA** · 10 500 cambios de contexto/s
```

→ Lo que infla la carga son **muchos hilos despertándose a menudo** —la firma de ROS 2 con doce
  nodos y sus temporizadores—, no CPU agotada ni espera de disco.
→ 🔴 **Y retira una explicación del 2026-08-07:** los abortos de Nav2 se atribuyeron a «la Pi
  saturada, load 8,39». La causa real era `default_server_timeout: 20` (evidencia 88), **y la Pi
  tampoco estaba saturada**. El instrumento estaba mal leído las dos veces.
→ ✅ **Para saber si hay CPU, lee `/proc/stat`** y calcula el % ocioso. Un umbral tipo «load < 4»
  es **inalcanzable** aquí con Nav2 arrancado: un banco que lo esperaba se pasaba 90 s para seguir
  igual.

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

**🔴🔴 UNA LLAMADA DE LA WEB A `/rosapi/get_param` MATA EL NODO `rosapi` ~30 s DESPUÉS, Y
`systemctl` SIGUE EN VERDE.** Medido el 2026-08-08 (evidencia 87), con control:

```
llamada BIEN formada a un nodo QUE EXISTE   ->  rosapi VIVO a los 80 s   ✅
llamada a un nodo QUE NO EXISTE             ->  MUERTO entre 20 y 40 s   🔴
sin tocarlo durante 60 s                    ->  VIVO                     ✅

rosapi/params.py:174, en un temporizador de limpieza suyo:
  (now - cached_client.last_used_time)
  TypeError: Can't subtract times with different clock types
```

→ 🔴 **No es un caso raro: es el caso NORMAL de la web.** `amcl`, `slam_toolbox` y los nodos de
  Nav2 **solo existen con la navegación arrancada**. Una pantalla que lea un parámetro de Nav2 con
  la navegación parada **mata rosapi para todos los clientes de ese robot**. Verificado con
  `/amcl:alpha1`.
→ ⚠️ **El modo de fallo, otra vez el peor:** `systemctl` dice `active`, rosbridge sigue
  contestando, el driver publica, y lo único que desaparece es `/rosapi/*` — que es lo que
  **roslibjs usa AL CONECTAR**. Los clientes conectados parecen sanos; los nuevos no arrancan.
→ ✅ **Arreglado con `respawn=True, respawn_delay=2.0`** en el nodo `rosapi` de `robot.launch.py`.
  **`respawn` y NO `on_exit=Shutdown()`**, al revés que el driver: perder rosapi no deja al robot
  inservible, y reiniciar el launch entero le costaría la sesión a un alumno. Verificado por
  efecto: PID 53455→53711 matándolo, y 53711→54485 con la llamada venenosa.
→ ⚠️ **No arregla la causa**, que es de rosapi en Jazzy. Hace que el fallo dure ~2 s en vez de para
  siempre. **La web no debería preguntar por parámetros de nodos que puede que no corran.**

**📌 Y `get_param` SÍ FUNCIONA — el nombre lleva DOS PUNTOS, no barra.** Es lo que costó el
diagnóstico falso de arriba:

```
'keepalive_period'                  ->  «cannot access local variable 'node_name'»
'/supervisor_navegacion/mapa'       ->  lo mismo
'/rvr_driver:keepalive_period'      ->  value '30.0'  successful=True   ✅
```

→ **El nodo se llama `/rvr_driver`, no `/rvr_driver_node`.** La lista buena la da
  `/rosapi/get_param_names`, que funciona sin problemas y ya devuelve la forma correcta.
→ 🔴 **Y el log del robot lo decía desde la primera llamada:** `[WARN] [rosapi]: Malformed
  parameter name: ...; expecting <node_name>:<param_name>`. **El PC no ve el journal**, y ahí está
  el límite real de trabajar en dos máquinas: quien ve el síntoma no ve el log.

**🔴 rosbridge NO SUELTA LA SUSCRIPCIÓN CUANDO EL CLIENTE SE CAE, Y ESO IMPIDE QUE SE APAGUE EL LED
DEL SENSOR.** Confirma la hipótesis que dejó escrita el PC tras medir **14 min 38 s** con la luz
encendida sin nadie leyendo (apagado por inactividad: 120 s). Medido el 2026-08-08 cerrando el
socket **de golpe, sin `unsubscribe`**:

```
justo tras cerrar   Subscription count: 1
a los 32 s          1        ros2 topic info /color --verbose
                             Node name: rosbridge_websocket   <- sin cliente conectado
```

→ El driver cuenta `pub_color.get_subscription_count() > 0` como actividad, así que **el apagado
  por inactividad no vence nunca**.
→ 📌 Encaja con lo ya conocido: rosbridge mantiene **UNA suscripción ROS por topic** compartida
  entre clientes — lo mismo que hace que el primero imponga el QoS. Que no la suelte al perder un
  cliente es la misma arquitectura vista desde otro lado.
→ ⏳ **Propuesto y NO hecho** (cambia el comportamiento del alumno): contar como actividad **solo
  las llamadas a servicio**, que no pueden quedarse colgadas — y el contrato ya dice que la web lea
  por servicio en los dos modos. ✅ Lo que protege hoy es el **tope duro de 900 s**, que no depende
  de la actividad: la exposición está acotada a 15 min, no es indefinida.


**🔴 `comprobar_contrato.mjs` NO VE LOS CAMPOS DE UN `.msg`, Y SE CONTABA CON QUE SÍ.** El
2026-08-08 el robot añadió `mapa_nombre` y `mapa_edad_s` a `EstadoNavegacion` y escribió: *«le toca
al PC añadirlos a `contrato.ts`; `comprobar_contrato.mjs` estará en rojo hasta entonces, que es lo
correcto»*. **No lo estuvo:** ejecutado antes de tocar nada, dio los cuatro ✅.
→ Compara **nombres** de topics, servicios y acciones, y de los **tipos** solo que el `.msg`
  **exista**. Los campos de dentro le son invisibles.
→ 🔴 **Fiarse de ese rojo habría dejado los dos campos sin llegar a la pantalla, con todo verde** —
  y esos dos campos existen para avisar del fallo de los 41,3 cm.
→ 📝 Misma familia que «`ros2 topic list` incluye topics de nodos muertos» y que los ocho fallos
  propios del verificador: **una comprobación que se cree que cubre algo y no lo cubre**. Lo que la
  hace peligrosa no es lo que no mira, es que alguien planifique contando con que sí.
→ ⏳ Cerrarlo sería leer los campos del `.msg` y cruzarlos con la interfaz de TypeScript. **No
  hecho.** Mientras tanto: al añadir un campo a un `.msg`, **avísalo por el CHANGELOG**, que es lo
  único que cruza hoy las dos máquinas.

**🔴 UN UMBRAL SOBRE UN DATO QUE NO MIDE LO QUE FALLA DA VERDE EN EL CASO PEOR.** Al poner la edad
del mapa en la web se propuso avisar a los **7 días**, por coherencia con `verificar_robot.sh`.
La decisión de **no** ponerlo en la web se mantiene, y el robot la aceptó — pero **no por el motivo
que escribí primero**:
→ 🔴🔴 **CORREGIDO EL 2026-08-09, Y EL ERROR ES MÍO.** Aquí ponía *«ese umbral no existe en ese
  script ni en ningún otro»*. **Existe**: `verificar_robot.sh:1459`, `if [[ "$DIAS_MAPA" -le 7 ]]`,
  puesto el día antes. Lo di por inexistente porque mi `grep` buscaba `7 días`, `604800`,
  `-mtime +7`… y el código dice **`-le 7` sobre una variable**: ninguno de mis patrones podía
  casarlo.
  📝 **Es la versión con `grep` del error que este fichero persigue:** un negativo sacado de una
  búsqueda que no podía encontrar lo que buscaba. Igual que «antes de concluir que algo NO ocurre,
  pregunta cuánto tendrías que haber esperado» — aquí es **pregunta si tu patrón podía casar**.
  Y duele más porque el negativo se usó para desacreditar a quien tenía razón.
→ 🔴 **Y aunque existiera, no serviría: la edad no mide lo que falla.** El fallo medido no es «el
  mapa es viejo», es «el mapa **no es de este sitio**» —41,3 cm con `SUCCEEDED` y sin una línea de
  error—, y uno de ayer del cuarto equivocado es igual de peligroso que uno de hace un mes. Peor:
  `mapa_edad_s` es el **`mtime`**, así que **copiar un mapa viejo lo rejuvenece** y el semáforo
  daría **verde justo en el caso peor**.
→ **Antes de poner un umbral, pregunta si la magnitud que mides es la que falla.** Cuando no lo es,
  lo honesto es enseñar el dato y **preguntar**, no graduar. La pantalla lo hace así, y una prueba
  impide añadir el umbral sin justificarlo.

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

**🔴🔴 Y LA QUINTA: `rclpy.init()` INVALIDA SU PROPIO CONTEXTO ANTES DE QUE PUEDAS PUBLICAR.**
Instala **su** manejador de SIGINT, así que un `except KeyboardInterrupt` que intenta publicar la
parada muere con `RCLError: Failed to publish: publisher's context is invalid`. Medido el
2026-08-02 con el driver escuchando, dos veces cada variante:

```
rclpy.init()                                          → 0 líneas «PARADA DE EMERGENCIA»
rclpy.init(signal_handler_options=SignalHandlerOptions.NO)  → 5 líneas
```

→ **Con `SignalHandlerOptions.NO` el SIGINT lo maneja Python**, el `except` corre con el contexto
  vivo, y la parada sale. Es obligatorio en cualquier herramienta que pare el robot con Ctrl-C.
→ ⚠️ **Y ES INTERMITENTE:** según dónde caiga el Ctrl-C a veces sí publicaba. Por eso la
  verificación del 2026-08-01 de `probar_atasco.py` **pasó** — la parada llegó al driver aquella
  vez. Afectaba a tres herramientas ya commiteadas; arregladas.
→ 📝 **La lección, y es la que importa: para un mecanismo de seguridad, «lo probé y funcionó» no
  basta.** Hay que preguntarse en qué condiciones NO funcionaría. Una sola pasada verde sobre un
  fallo intermitente es indistinguible de que no haya fallo.
→ ⚠️ **Trampa al verificarlo:** `journalctl --since "$(date -u +%T)"` cuenta **0 aunque la parada
  haya llegado** — `date -u` da hora UTC y `journalctl` la interpreta como local, así que en este
  robot (UTC−5) la ventana cae cinco horas en el futuro. Usa `--since "-25 s"`.

**🔴 La parada de emergencia ha fallado TRES veces, siempre en silencio y con `200 OK`.**
(1) nombre de topic distinto, en ROS 1. (2) **namespace**: al portar se arregló el nombre y se
coló el `/rvr/`. (3) **QoS**. → Las causas 2 y 3 **solo aparecen publicando de verdad**: leer el
código da el nombre pero no el namespace resuelto ni el QoS. **Publica y mira el log del
driver.**

**El X2 no ve un objeto fino en un solo barrido.** A 0.68 m tira un rayo cada 1.7 cm, así que
un objeto de 5 cm da 2-3 puntos y en un barrido suelto puede desaparecer. → Para geometría
fina, **acumula 6-8 s de barridos y toma la mediana por sector angular**. Un `/scan` suelto no
basta, y hace dudar de `min_points: 2` con obstáculos así.

**🔴 EL POLÍGONO DE FRENADO NO SABE HACIA DÓNDE VAS: frena igual al alejarte.** Medido con
cinta el 2026-08-02: un retroceso comandado de 2 s a 0.15 m/s (30 cm esperados) hizo **14 cm**.
`Precaucion` es un polígono **estático** que se extiende 0.36 m **hacia delante** con
`slowdown_ratio: 0.4`; con la pared a ~19 cm del centro sigue dentro, así que frena al 40 %
**aunque el robot se esté alejando** — `0.15 × 0.4 × 2 s = 12 cm`, y se midieron 14.
→ No es un fallo, es cómo funciona un polígono estático. Pero **la web tiene que saberlo**: un
  retroceso puede tardar más del doble de lo esperado si hay algo delante. No es que no obedezca.
→ Y explica por qué al robot «le cuesta» salir de un rincón. Evidencia 49.

**✅ `laser_x` MEDIDO: el LIDAR estaba 0.5 cm POR DETRÁS del centro, no en él.** Cerrado el
2026-08-02 con cinta: chasis **19.0 cm** de frente a atrás → centro geométrico en 9.5; centro del
tambor a **9.0 cm del borde trasero** → **`laser_x = −0.005 m`**. El modelo decía `0`, anotado el
2026-07-30 como «centrado» **sin cinta detrás** — igual que `laser_z`, que al medirse resultó estar
2 cm mal. Y `laser_y = 0` deja de ser suposición.
→ Lo destapó una discrepancia de ~2 cm entre lo que leía `/scan` tras una parada del
  `collision_monitor` (18.9 cm) y lo que el usuario medía en el suelo (7–8 cm): con `laser_x = 0`
  el residuo era 2.3 cm —fuera del ruido—; con −0.005 baja a 1.4, que **ya no se distingue del
  error de la propia cinta** (sus dos esquinas difieren 1.0 cm). Evidencia 51.
→ ⏳ **Queda abierto el LARGO**: la ficha dice 18.2 cm y el usuario mide 19.0. Difieren 0.8 cm y
  **las dos están anotadas como medidas con cinta**. El URDF usa ya 0.190. `MEDIDAS_ROBOT.md`.

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

**🔴🔴 PARA UNA SUPERFICIE QUE EMITE LUZ, EL LED DEL SENSOR HAY QUE APAGARLO — Y ENCENDIDO DA
LO CONTRARIO DE LO QUE HAY.** Todo lo demás de este fichero da por hecho que el RGBC necesita su
luz (185× medido), y **eso vale para una superficie que REFLEJA. Para una que EMITE se invierte.**
Medido el 2026-08-08 sobre una pantalla de móvil a brillo máximo, sin mover el robot:

```
                   LED del sensor OFF          LED del sensor ON
                  R/G     B/G    claro       R/G     B/G    claro
   ROJO          5.12    0.15      150      0.66    0.49     1238
   VERDE         0.17    0.20      387      0.37    0.40     1467
   AZUL          0.11    4.57      190      0.46    0.73     1230
```

→ ✅ **Apagado los tres se separan por un factor 25-30**, y la regla sale sola: `R/G > 1` rojo,
  `B/G > 1` azul, las dos bajas verde.
→ 🔴 **Encendido, los seis cocientes viven entre 0.37 y 0.73**, y el rojo da **`R/G = 0.66`, o sea
  MENOS rojo que verde sobre una pantalla roja a tope.** No pierde precisión: **engaña**. Sobre
  vidrio el reflejo es especular y blanco, y aporta el 88 % de lo que se mide.
→ 📌 **Control interno que salió gratis y vale más que el resultado:** el LED aportó **+1088,
  +1080 y +1040** de `claro` en los tres colores — 4 % de dispersión. Tiene que ser así, porque es
  su reflejo sobre el mismo vidrio y **no depende de lo que muestre la pantalla**. Eso prueba que
  el servicio hizo efecto **sin mirar su `success`**.
→ 🔴 **Y EN ESE MODO EL TOPIC `/color` NO SIRVE: publica CEROS.** Medido: luz encendida 40 de 40
  mensajes no-cero, luz apagada **0 de 39**. `/color` sale del **streaming** del RVR y el streaming
  se apaga con la detección; `/get_rgbc_sensor_values` **consulta**, así que sigue dando datos. Y el
  topic no trae `claro` de todas formas. **Contrato completo: `03_operacion/SENSOR_COLOR.md`.**
→ ⚠️ **Sin medir, y no se transfiere a una baldosa LED real:** dónde satura el canal (aquí el
  máximo fue 387 contra los 2288 del blanco reflectante) y el parpadeo PWM (aquí 2-4 cuentas de
  dispersión; una baldosa más lenta podría batir contra la integración). Evidencia 86.

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
→ Se enciende **en caliente** con el servicio `enable_color` (`std_srvs/SetBool`), o al arrancar
con `color_detection:=true`. **Por defecto false** porque deja un LED blanco bajo el chasis. Con
false el driver lo **avisa por el log**.

**✅ SÍ SE PUEDE ENCENDER BAJO DEMANDA — y aquí decía lo contrario hasta el 2026-08-06.** Con el
streaming corriendo a 250 ms: `/color` no-cero **0/24 → 24/24 → 0/24** y canal claro **1 → 1321 →
1**, reversible, con el LED visto encenderse. Evidencia 76.

**🔴 Y LA LECCIÓN VALE MÁS QUE EL DATO.** Lo que había aquí —«`enable_color_detection` no hace
nada, 481 mensajes todos ceros»— **no estaba medido**: el servicio bajo prueba hacía
`enable(True) → leer → enable(False)` en la misma llamada, y esos 481 mensajes (~38 s a 12,7 Hz)
son casi todos POSTERIORES al apagado. Una medida que da lo mismo si la hipótesis es cierta o
falsa **no es una medida**. Bloqueó una función seis días, y no la destapó ninguna revisión de
código: la destapó el usuario al recordar el ciclo funcionando en ROS 1 (cuyo servicio
`enable_color` hacía exactamente esto: `Atriz_rvr_node.py:331` y `:1636`).
→ **Antes de escribir «medido», di qué se habría visto si fuera falso.**

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

**🔴🔴 SI APAGAS Y ENCIENDES EL RVR CON LA PI VIVA, EL LIDAR QUEDA MUERTO Y TODO PARECE SANO.**
El X2 se alimenta del robot, así que apagarlo re-enumera su adaptador USB. La regla udev rehace
`/dev/ydlidar` correctamente, pero **el nodo abre el puerto una sola vez al arrancar y no lo
reabre nunca**: se queda agarrado al descriptor viejo, que el kernel ya destruyó. Medido el
2026-08-04:

```
nodo del lidar, fd 29  ->  /dev/ttyUSB0 (deleted)     <- descriptor MUERTO
proceso arrancado      ->  Aug  3 15:31:56
/dev/ttyUSB1 creado    ->  Aug  4 00:29:34            (nueve horas después)
```

→ **El síntoma no se parece a la causa:** `/start_scan` devuelve `result:false` con «Timeout
  exceeded while waiting for service response» (que es de **rosbridge**, no del robot), el
  journal se llena de `Failed to get scan` a 20 Hz, y `/scan` se queda a 0 — mientras
  `systemctl` dice `active`, el nodo vive, sus servicios contestan y `/odom` va a 16,58 Hz.
→ ⚠️ **Y bloquea el movimiento entero**: sin `/scan` el `collision_monitor` no deja conducir. Un
  robot así «no obedece» sin ninguna señal de avería.
→ **Atajo de diagnóstico**, que es lo único que lo ve de un vistazo:
```bash
ls -l /proc/$(pgrep -f "[y]dlidar_ros2_dr")/fd | grep tty    # si dice (deleted), es esto
```
→ **Arreglo hoy:** `sudo systemctl restart atriz-robot`. Verificado por efecto: fd vivo,
  0 errores, `/start_scan` `result:true`, **`/scan` a 11,90 Hz**.
→ ⏳ **Que se recupere solo está SIN HACER**, y con 16 robots va a volver: o udev reinicia la
  unidad al reaparecer el dispositivo, o el nodo reabre el puerto tras N fallos. Un
  `Restart=always` **no sirve**: el proceso no muere. Evidencia 69.
→ 📝 **`/start_scan` NO es lento**, aunque lo pareciera: medido por WebSocket con la conexión ya
  abierta —el camino de la web— son **1,4-2,1 s**, `result:true` 6 de 6, muy dentro de los 5 s de
  rosbridge. La medida de 4,6-6,5 s que se llegó a escribir salía de `ros2 service call`, que
  arranca un nodo entero en cada llamada. **Van cinco veces que el instrumento miente aquí.**

**🔴 Y EL HERMANO DEL ANTERIOR: SI EL LIDAR NO ESTÁ EN SU PUERTO USB, EL LAUNCH MUERE MUDO.** La
regla udev casa por **`ID_PATH`, el conector FÍSICO**, así que moverlo de sitio hace desaparecer
`/dev/ydlidar`. Y entonces `robot.launch.py` **muere en ~1 s sin imprimir una palabra**: el único
error visible es el del `ExecStartPost` —`🔴 /stop_scan no respondió en 30s. ¿está corriendo
robot.launch.py?`— que manda a mirar el launch, donde no está el problema. systemd reintenta 3
veces y se rinde con `Start request repeated too quickly`, que **exige `reset-failed`** antes de
poder arrancar otra vez. Medido el 2026-08-04: costó cuatro intentos de cable.
→ 📝 **El error que lo provocó merece decirse porque es natural:** se movió el cable buscando que
  volviera a ser **`/dev/ttyUSB0`**. Ese número **NO IMPORTA** —lo asigna el kernel por orden de
  aparición y cambia solo—, y la regla udev existe precisamente para hacerlo irrelevante: el nodo
  abre `/dev/ydlidar`. **Lo que importa es el conector, no el número.**
→ ✅ `verificar_robot.sh` ya lo dice en una línea: «el LIDAR está en el PUERTO USB 1.4, y la regla
  udev espera el 1.2 → MUEVE EL CABLE». Y comprueba también el descriptor muerto de arriba.
→ 👤 **DECIDIDO el 2026-08-04: el puerto fijo se mantiene en los 16.** Se ofreció quitar el
  `ID_PATH` (hay **un solo** dispositivo USB-serie en el robot: el RVR va por `ttyAMA0`, así que
  `10c4:ea60` bastaría y funcionaría en cualquier puerto) y se descartó por coherencia con la
  imagen dorada. **Consecuencia: la foto del conector en `FLOTA.md` es obligatoria y no existe.**
  Evidencia 69, apartados 7 y 8.

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

**🔴 UN SOLO SENSOR MIRANDO HACIA ABAJO NO PUEDE SABER HACIA QUÉ LADO SE DESVIÓ EL ROBOT.** El
diseño original de `03_operacion/API_LABORATORIO.md` (2026-08-02) especificaba un seguidor de
línea con **PID de umbral único** sobre el canal `claro`. No puede funcionar: si el robot deriva
a la izquierda de la línea el sensor deja de ver negro y ve suelo claro, y si deriva a la
derecha pasa **exactamente lo mismo** — la lectura es idéntica en los dos casos, así que
`error = (claro − umbral) / umbral` tiene el mismo signo esté el robot desviado al lado que sea,
y el PID solo puede sacar una salida para ese signo: acierta la mitad de las veces y empuja al
robot lejos de la línea la otra mitad. Estaba, además, ya escrito en el propio repositorio
(`SEGUIDOR_LINEA_EXPLICACION.md` de la versión ROS 1, sección 3: *"con un solo sensor no es
fiable estimar el desalineamiento lateral clásico"*) y nadie lo cruzó contra el diseño nuevo
hasta implementarlo (tarea 11). **Rediseñado a edge-following** por decisión del usuario: el PID
(sin tocar) decide la **magnitud** del giro; un estado que se arrastra entre vueltas del bucle
(`lado_borde`, no una lectura instantánea) decide el **signo**, y se invierte tras
`tiempo_perdido_max` segundos sin reencontrar el borde. **NO VERIFICADO sobre una línea real**:
las funciones puras suman 9 tests nuevos entre las tres rondas (52 → 61 en
`scripts/pruebas/`), pero el robot nunca ha seguido una línea físicamente.

🔴 **Y HAY UNA SEGUNDA FUENTE, EN ESTE MISMO PROYECTO, QUE YA TENÍA LA RESPUESTA — TAMPOCO SE
MIRÓ.** El 2026-07-29 se rescató un `git stash` de la microSD a la rama `wip/scripts-estudiantes`
de `Atriz_rvr` (commit `62e0313`). Dentro, un `SeguidorBordeRojo` escrito por el usuario que
decidía el giro **exactamente** con el mecanismo al que se llegó cuatro días después:

```python
cmd.angular.z = 0.32 * self.sentido_giro     # el signo NO sale de la lectura actual
if self.tiempo_sin_rojo > 25:                # sino de un estado que se arrastra,
    self.sentido_giro *= -1                  # y se invierte tras N ciclos sin ver el borde
```

Es `lado_borde` + `tiempo_perdido_max` con otros nombres, en 2026-07-29. El 2026-08-02 se
diseñó un PID de umbral único que **no podía funcionar**, se implementó, y se rediseñó
re-derivando esto desde cero. **Van dos fuentes del propio repositorio que lo decían antes de
tiempo** —esta y `SEGUIDOR_LINEA_EXPLICACION.md` de la versión ROS 1— y ninguna se cruzó contra
el diseño nuevo.
→ **La regla: antes de diseñar algo que el proyecto ya intentó, busca los intentos anteriores —
  incluidas las ramas WIP y los stashes rescatados.** El código de aquel seguidor no vale (es
  `rospy` y publica en `/cmd_vel`, la salida del `collision_monitor`); **el mecanismo sí**, y es
  lo único que se conserva: la rama se borró el 2026-08-03.

**🔴🔴 Y EL SIGNO Y LA MAGNITUD DE UNA CORRECCIÓN TIENEN QUE MEDIR DESDE EL MISMO CENTRO, O HAY
REALIMENTACIÓN POSITIVA.** Al implementar el edge-following de arriba, `signo_correccion()`
decidía el signo con las fronteras de histéresis de `clasificar()` (en 450/950) mientras
`magnitud_correccion()` medía la distancia al centro real (700). Entre 701 y 949 discrepan: el
estado seguía siendo `'negro'` (signo hacia un lado) mientras la magnitud ya crecía hacia el
otro — el controlador empujaba al robot **más lejos** del borde en vez de traerlo, justo lo
contrario de lo que el edge-following existe para hacer. Y **cinco tests que solo probaban los
extremos y el punto de equilibrio (181, 700, 1275) no lo atraparon**: la banda intermedia no la
miraba nadie. El arreglo fue hacer que las dos funciones calculen el mismo `centro` y comparen
contra él directamente. La lección: un test que barre tres puntos «representativos» de un rango
continuo puede dejar sin cubrir justo el tramo donde vive el bug — barre el rango entero, no los
extremos.

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
probar_lista_blanca.py       # ¿la lista blanca de rosbridge DENIEGA de verdad? (sin mover el robot)
probar_sdk_no_usados.py      # los métodos del SDK que el driver NO usa: ¿cuáles responden?
#                              ⚠️ necesita el driver parado (sudo systemctl stop atriz-robot)

prueba_navegacion_completa.py # ⚠️ MUEVE EL ROBOT ~80 cm: la prueba de Nav2 ENTERA en UN proceso.
#                              Resetea odometría, pide nav, espera FUNCIONANDO, ESPERA A QUE LA
#                              CARGA BAJE de 4.0, manda el objetivo y lee su DESENLACE.
#                              🔴 Es un proceso solo a propósito: encadenar `ros2 service call`
#                                 satura la Pi (load 8.39/4) y bt_navigator ABORTA el objetivo.
#                                 El instrumento competía por el recurso que medía.
comparar_con_cinta.py        # sin robot: convierte AB/AP/BP en una POSICIÓN por trilateración
#                              🔴 con UNA sola distancia no se puede: la diagonal dejó pasar un
#                                 error de 45 cm porque separaba las hipótesis solo 2 cm
probar_color_por_websocket.py # NO mueve: los DOS modos del sensor POR ROSBRIDGE, que es el
#                              camino de la WEB. Mide latencia y separa `result` (rosbridge)
#                              de `success` (driver). 🔴 «Funciona por ROS» NO implica «funciona
#                              por la web»: es lo que costó la falsa medida de /start_scan
medir_superficie_emisora.py  # NO mueve: ¿lee el RGBC una pantalla o una baldosa LED?
#                              Mide con el LED del sensor ON y OFF, seguidas y sin mover.
#                              🔴 Las DOS tandas hacen falta: con solo la de ON, «no se
#                                 distinguen los colores» es indistinguible de «no sirve»
correr_practica.py           # ⚠️ MUEVE EL ROBOT: corre una práctica de alumno y mide SI SE MOVIÓ
#                              Lee /odom antes y después, informa desplazamiento y giro netos.
#                              🔴 Hizo falta desde la primera práctica: imprimió «Avanzando...
#                                 Listo.» y salió con 0, que no dice nada. Con él salieron los
#                                 26,4 cm de un avance de 60 y el girar() que abortaba a los 5,5°
#                                 devolviendo 0. Evidencia 85.
consultar_plan.py            # ✅ NO MUEVE EL ROBOT: le pregunta a Nav2 qué RUTA trazaría, con
#                              `compute_path_to_pose`. Dice si el plan va recto o RODEA, y saca el
#                              coste del costmap en el eje cada 10 cm.
#                              🔴 ÚSALO ANTES DE GASTAR BATERÍA: cuatro tandas de robot en marcha
#                                 no distinguieron «traza recto y el robot no sigue» de «traza un
#                                 rodeo»; una consulta de dos minutos sí. Evidencia 91.
probar_rodeo_obstaculo.py    # ⚠️ MUEVE EL ROBOT hasta --meta metros: ¿cuánto hueco necesita Nav2?
#                              --slam  usa SLAM en vez de AMCL: NO llama a /pedir_nav (el
#                                      supervisor lo rechazaría) y NO pone la odometría a cero
#                                      (con SLAM viva eso corrompe el mapa). Exige nav2.launch.py
#                                      lanzado a mano.
#                              🔴 Diez fallos propios cazados midiendo, ninguno dio error. Los seis
#                                 primeros en la evidencia 90, los cuatro últimos en la 91.
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
prueba_aceptacion.py          # ⚠️ LA PRUEBA DE ACEPTACIÓN: 10 fases, de arranque en frío a Nav2
#                               MUEVE EL ROBOT en F4-F7 · GUIADA: exige terminal de verdad
#                               --solo F4,F6   ejecuta solo esas fases (las demás quedan PENDIENTE)
#                               --desde F4     retoma sin repetir
#                               Criterio y umbrales: 03_operacion/PRUEBA_ACEPTACION.md
aceptacion_nucleo.py          # su lógica pura (bandas, veredictos, informe). 24 tests, sin ROS:
#                               python3 -m pytest scripts/pruebas/ -q  (89 en total, 65 son de atriz.py)
probar_ctrl_c_atriz.py        # ⚠️ MUEVE EL ROBOT ~1.5 m: ¿para un Ctrl-C a mitad de avanzar()?
#                               mide DESPLAZAMIENTO tras matarlo. El fallo es INTERMITENTE:
#                               una sola pasada verde no basta, repite varias veces
simular_girar.py              # simulador de girar() SIN robot: funciones puras de atriz.py,
#                               sobregiro con odometría sintética (congelada, con jitter) · sin ROS
simular_sobregiro.py          # tabla comparativa de sobregiro a 10 Hz vs 20 Hz, misma física
#                               que simular_girar.py (comparten generador_rampa_real()) · sin ROS
#                               🔴 se llamaba medir_sobregiro.py y NO mide nada: es un modelo
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
| `/scan` | 🔴🔴 **EL TAMAÑO NO ES UNA CONSTANTE Y ESTA FILA NO PUEDE LLEVAR UN NÚMERO.** Medido desde el robot el 2026-08-04, ciclando el barrido: **250 · 250 · 270 · 250**, y el journal del mismo día registró además 253, 254 y 255. Dentro de UNA sesión es constante —por eso 35 barridos seguidos dieron «260, y solo 260», y por eso antes ponía «255»— pero **las dos eran fotos de una sesión**. La causa es `fixed_resolution: true`: el driver lo fija con el PRIMER barrido de cada sesión, y ese depende de a qué velocidad gire el X2 en ese instante — y el motor va libre, porque `frequency: 10.0` es decorativo. → **Nada puede depender del número**: `ranges.length` y `angle_increment` vienen en cada mensaje. Un cliente que lo asuma se rompe **una de cada tres** sesiones. 📝 Y esta fila lleva **dos** correcciones que eran fotos: ponerle un tercer número la volvería a dejar rancia | 2026-08-04, medido desde el robot |
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
| 🎯 **El sensor de color, la MISMA superficie con y sin luz** | **pantalla roja**: `R/G` **5,0** con la luz APAGADA → «rojo» · **0,57** con ella ENCENDIDA → el sensor lee *más verde que rojo* y no se puede decir. **papel rojo mate**: `R/G` **2,95** con luz → «rojo» · **0·0·0·0** sin luz. Factor **9** sobre el mismo objeto, a lados opuestos de 1 — **el modo no es un ajuste, decide el signo** | 2026-08-09, por la web |
| **SLAM arrancado desde la web** | `apagado → arrancando → funcionando` en **~18 s**, con los segundos subiendo (4 · 9 · 14). Y `CIEGO` en 1-2 s al apagar el barrido | 2026-08-09 |
| **WebSocket por nombre, desde el NAVEGADOR** | **2736 ms** con la caché mDNS fría · **16-25 ms** caliente (plazo del cliente: 10 s). ⚠️ Desde **Node** el mismo nombre tarda **7,3 s**: no se transfiere entre clientes | 2026-08-09, n=3 |
| Enlace con keepalive | **12 min, 0 huecos** en `/odom`, 16.54 Hz | 2026-07-31 |
| ✅ **GIRO POR ANGULO, medido con el robot en el suelo** | **`girar()` (lazo cerrado, tras compensar la inercia)**: n=5 a 90° → rango **0.94°**, peor error **0.74°**, media **+0.20°**. n=9 a 90/180/360 → sesgo **+0.19°**. · **`girar_por_tiempo()` (lazo abierto, 0.8 rad/s por `/cmd_vel_raw`)**: n=4 a 90° → rango **4.20°**, peor **2.30°**, media **+0.23°**. 🔴 **Misma media, 4.5× menos dispersion en el cerrado**: la realimentacion no mejora el acierto, reduce la varianza. ⚠️ Antes de compensar, el cerrado sobregiraba **+4.01° CONSTANTES** (0.35 s de inercia tras mandar parar) | 2026-08-03, evidencias 58 y 61 |
| ✅ **GIRO POR ANGULO** | **n=3**: 90°→**86.6 / 86.2 / 87.7°** · 180°→**179.6 / 179.6 / 179.6°** · 360°→**358.4 / 357.9 / 358.8°**. Rango 1.5° / **0.0°** / 0.9°. Deslizamiento **0.0–0.3 cm** · signo REP-103. 📝 Con baterías del 55 al 100 %: **el déficit NO depende de la carga**, y el de 180° sale idéntico las tres veces | 2026-08-02, evidencias 48 y 55 |
| ✅ **Nav2: error de RUMBO al llegar** | **13.6 · 10.1 · 14.1°** — dato NUEVO. Nav2 los da por `SUCCEEDED` (su `yaw_goal_tolerance` lo permite), pero **un robot que llega mirando 14° a un lado importa para la web** | 2026-08-02, evidencia 55 |
| 🔴 **Nav2 navegando** | «error final **9–10 cm**» — 🔴 **NO ES UNA MEDIDA: es la `xy_goal_tolerance` repetida.** Sale de la pose que el robot se atribuye, y el controlador para cuando **cree** estar dentro, así que da ~10 cm esté donde esté. Con cinta y trilateración: **6,1 · 11,8 · y 41,3 cm** con un mapa rancio, y `SUCCEEDED` las tres veces | 2026-07-31, corregido 2026-08-08 |
| ⚠️ **Nav2, error REAL contra cinta** (trilateración, no la diagonal) | **n=3: 6,1 · 11,8 · 11,3 cm** — **DOS de tres FUERA** de la tolerancia de 10 · odometría **1,5 · 4,2 · 2,2 · 0,3 cm** (n=4, dos mapas, cargas de 5 a 9) · AMCL **45,0 · 8,9 · 15,2 · 8,2**. 🔴 La cifra honesta es **~10-12 cm**, no la tolerancia | 2026-08-07/08, evidencias 84 y 88 |
| ~~Nav2, error real (n=2)~~ | **6,1 y 11,8 cm** de un objetivo de 80, sobre un mapa **fresco** — una tanda dentro de la tolerancia de 10 y otra fuera · AMCL **8,9 y 15,2**, odometría **4,2 y 2,2** · corrección `map→odom` **0,028 y 0,021 m**. 🔴 Con el mapa **rancio**: **41,3 · 45,0 · 0,424**. 🔴 **Nav2 declaró ÉXITO en las TRES.** n=2 | 2026-08-07/08, evidencia 84 |
| ✅ **Deriva acumulada de la odometría** | **3,3 cm** tras un ciclo completo (ida 45 cm, giro de 125°, vuelta, ×2), medido con cinta a la marca de partida | 2026-08-07 |
| Stack COMPLETO (driver+LIDAR+SLAM+Nav2) | **~89 %** de un núcleo, ~477 MB, loadavg 2.53/4, 58.9 °C | 2026-07-31 |
| Nav2 solo | ~58 % de un núcleo — la pieza más pesada | 2026-07-31 |
| **Parada del `collision_monitor`** | **9.9 cm** a 0.25 m/s · **10.6-10.7 cm** a 0.40 (n=2) | 2026-07-31 |
| Nav2 a 0.40 m/s | meseta **0.407 m/s** en 0.9 s · error de objetivo **8 cm** | 2026-07-31 |
| Rodeando un obstáculo | desvío **26–32 cm**, error **8–9 cm**, 4 de 4 SUCCEEDED | 2026-07-31 |
| **Ancho de banda por rosbridge** (JSON) | **80.7 kB/s** navegando (`/scan` es el **83 %**) · **13.6 kB/s** en reposo · ×16 = **10.3 / 1.7 Mbit/s** | 2026-08-01, medido en el robot Y en el navegador |
| **Tamaño del robot** | ⚠️ **CONFLICTO ABIERTO**: **18.2** cm (2026-07-31) contra **19.0** (2026-08-02), las dos con cinta y con orugas. Ancho **21.7 cm**, sin discusión. El URDF usa **0.190**. `MEDIDAS_ROBOT.md` | 2026-08-02 |
| **`laser_x` / `laser_y`** | ✅ **−0.005 / 0 m MEDIDOS** — el LIDAR está 0.5 cm por detrás del centro, centrado en Y | 2026-08-02, evidencia 51 |
| **Plano de barrido del LIDAR** | **15.5 cm** del suelo ✅ MEDIDO (antes 17.45, derivado) | 2026-07-31 |
| Alto del RVR (suelo → tapa) | **7.0 cm** — la ficha decía 11.4 | 2026-07-31 |
| Radio circunscrito | **0.142 m** → `robot_radius: 0.145` | derivado de lo anterior |
| Paso mínimo con `radius: 0.15` | ~**30 cm** + margen (`2 × radius`) — con el 0.18 anterior eran 36 y no cruzaba 40 | 2026-08-09 |
| Hueco al parar, `radius: 0.15` | **6.3 cm** a 0.25 m/s · **7.4 / 6.6 cm** a 0.40 (máxima) | 2026-08-09 |
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
| 🔴 ~~**Estática + DHCP conviven en `wlan0`**~~ **RETIRADA el 2026-08-04** | Era la suposición «A VERIFICAR» que sostenía el diseño de la flota. El robot se muda de casa al laboratorio **sin tocar un comando**. Evidencia 39, manual cap. 19 🔴 **RETIRADA: se midió desde el ROBOT y nunca desde el CLIENTE.** Con tres direcciones, `rvr-NN.local` resuelve a cuatro y el navegador **se cuelga ~21 s** en las que no sirven — el muro no encontraba ningún robot. La sustituye **una dirección por red** emparejada por SSID: `00_auditoria/planes/2026-08-04-direccionamiento-flota.md`. ✅ **Aplicada en rvr-01 y verificada desde el CLIENTE el 2026-08-04**: `ws://rvr-01.local:9090` abre en el navegador y el muro entra por nombre (evidencias 74 y 75). ⏳ **El aula sigue sin probarse:** `05-atriz-lab.network` nunca ha casado con nada |
| 📜 **El driver de ROS 1 de Atriz DERIVA de `git.uibk.ac.at/informatik/stair/ros-sphero-rvr`** (Innsbruck) | Descubierto el 2026-08-01: **seis nombres de servicio idénticos**, el topic `/is_emergency_stop` —el nombre raro que costó el primer fallo de la parada— y el `cmd_vel_timeout = 0.3` que su README documenta explícitamente. Explica de dónde salen nombres que aquí parecían arbitrarios. Evidencia 46 |
| ✅ **Y corrobora la prueba del magnetómetro** | Su driver hace **exactamente** la misma secuencia que probamos (`calibrate_to_north` + notificación → `yaw_north_direction`), sin ningún paso previo que nos hubiéramos saltado. Su docstring confirma que **el robot debería girar**. En nuestro firmware no gira: la conclusión «no hay rumbo absoluto» se sostiene con contraste externo |
| **NO se adopta nada de `CollaborativeRoboticsLab/sphero_rvr_ros`** (revisado 2026-08-01) | Su rama `ros2` usa **`ros2_control` en C++**, que es la arquitectura canónica — pero migrar sería reescribir el driver y **perder todo lo caracterizado**. Y está menos avanzada en lo que aquí importa: **sin keepalive** (el RVR se duerme a los 300.6 s), sin parada de emergencia, sin capa de seguridad, y con la navegación aún en `move_base` de ROS 1. ✅ **Sí se toma una idea**: separar el **canal de salud de flota** (~1 Hz) del canal de operación. Evidencia 46 |
| **Imagen dorada** para los 16, no aprovisionar por red | ~300 MB y 15-20 min por robot, sobre la única AP. `FLOTA.md` |
| La imagen dorada se **construye ejecutando `provision.sh`**, no a mano | Una imagen irreproducible es una caja negra. `FLOTA.md` |
| **`provision.sh` instala `navigation2`** desde el 2026-07-31 | Antes no lo instalaba: un robot aprovisionado con el script no podía navegar, ni tenía capa de seguridad, ni localización |
| 🔴 ~~**Estática y DHCP CONVIVEN en `wlan0`**~~ **RETIRADA el 2026-08-04** | 3 direcciones IPv4 a la vez (`10.14.7.7`, `192.168.1.200`, DHCP) y la ruta por defecto la pone el DHCP. Era **la suposición que sostenía todo el diseño de red**. Un robot se muda de red **sin tocar un comando**. Manual, cap. 19 🔴 **RETIRADA: se midió desde el ROBOT y nunca desde el CLIENTE.** Con tres direcciones, `rvr-NN.local` resuelve a cuatro y el navegador **se cuelga ~21 s** en las que no sirven — el muro no encontraba ningún robot. La sustituye **una dirección por red** emparejada por SSID: `00_auditoria/planes/2026-08-04-direccionamiento-flota.md`. ✅ **Aplicada en rvr-01 y verificada desde el CLIENTE el 2026-08-04**: `ws://rvr-01.local:9090` abre en el navegador y el muro entra por nombre (evidencias 74 y 75). ⏳ **El aula sigue sin probarse:** `05-atriz-lab.network` nunca ha casado con nada |
| ✅ **Fase A de seguridad APLICADA (2026-08-02): `raw_motors` ya NO es alcanzable** | Lista blanca en `robot.launch.py` (`topics_sub_glob`, `topics_pub_glob`, `services_glob`, `actions_glob`, `params_glob`) + `rosapi_node`. Cierra `raw_motors`, `move_timed`, `move_to_pose`, los IR y **publicar en `/cmd_vel`**, que era el agujero más silencioso. ✅ Verificado con el **efecto físico**: `raw_motors` al 30 % por WebSocket → **0.00 cm** de desplazamiento (evidencia 53). `SEGURIDAD_ROSBRIDGE.md` |
| 🔴 **PERO SIGUE BLOQUEANDO LA FASE 5: no hay identidad por usuario** | La Fase A **no** levanta el pendiente. **rosbridge 2.7.0 en Jazzy NO TIENE AUTENTICACIÓN** —no existe: `rosauth` no es dependencia, no hay parámetro `authenticate`, y `check_origin()` devuelve `True` incondicionalmente—, así que **cualquiera en el aula sigue pudiendo teleoperar cualquier robot** por `cmd_vel_raw`. Se cierra en la **Fase B**: proxy que valida el JWT en cada robot, con rosbridge atado a `127.0.0.1`. ⚠️ «Token en el WebSocket» quedó **descartado por imposible** |
| ✅ **El camino web ↔ robot está verificado de extremo a extremo** | Navegador del PC → `ws://rvr-01.local:9090` → topics **y** servicios. `03_operacion/probar_conexion_web.html`, sin librerías ni CDN. La web **no necesita SSH para nada operativo**. Evidencia 39 |
| ✅ **La web localiza a los robots por `rvr-NN.local` (mDNS)**, con la IP como override | Es lo que hace que el mismo código funcione en casa y en el laboratorio sin tocar nada. ⚠️ **Y estuvo ROTO entre el 2026-08-01 y el 2026-08-04**, sin que nadie lo notara: aquella verificación vio que avahi publicaba **A y AAAA a la vez** y lo dio por bueno — con varias direcciones, el navegador se cuelga en la primera que no sirve y **el muro no encontraba ningún robot**. ✅ Cerrado con **una dirección por red** y `publish-aaaa-on-ipv4=no`; hoy `ws://rvr-01.local:9090` **abre** desde el navegador. Evidencias 39, 74 y 75 |
| 🔁 ~~**NO se reflashea rvr-01 para probar `provision.sh` entero**~~ — **SUPERADA EL 2026-08-10** | Decía «es el único robot montado» y sobre eso se **asumía** que `provision.sh` funciona. 🆕 **Ya hay un `rvr-02`, y el guion se está ejecutando de verdad sobre él** — o sea que la suposición más cara del proyecto está **levantándose**, sin tocar rvr-01. ⏳ No ha terminado: quedó parado en `colcon build` con `Permission denied: 'log'`, y `fase_7` se niega en cadena porque el workspace no compiló. **La causa NO está determinada**; lo que sí está descartado es que la cause el guion —compila con `sudo -u "$USUARIO"` (`:519`) y crea el directorio con `install -d -o "$USUARIO"` (`:244`)—. Diagnóstico y arreglo en `ESTADO_ACTUAL.md`. 📌 **Y la regla que vale más que el arreglo: lo que frene a rvr-02 va al GUION, no se arregla a mano** — o los catorce siguientes tropiezan igual |
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
| 🔴 **El material docente corre sobre `atriz.py`, NO sobre `rclpy`** | Un script de alumno contra `rclpy` a pelo tiene que acertar siete cosas que este proyecto pagó aprendiéndolas (topic correcto, encender el barrido, republicar contra el watchdog, `SignalHandlerOptions.NO`, BEST_EFFORT, límites de velocidad/tiempo, apagar el barrido al cerrar). `atriz.py` las acierta una vez y el alumno escribe robótica, no ROS. Diseño en `03_operacion/API_LABORATORIO.md`, 2026-08-02. Código escrito y revisado (tareas 1-13 + oleada de arreglos final, **89 tests**) — **⏳ NO VERIFICADO contra el robot moviéndose**: falta la sesión física (ver `TRASPASO.md`) |
| ✅ **La navegación va en `atriz-nav.service`, instalada y NO habilitada** (2026-08-03) | Hasta entonces **nadie arrancaba Nav2 ni AMCL**: había que entrar por SSH y lanzar dos launch a mano, así que la Decisión 2 era cierta solo para teleoperación. Unidad aparte y no un argumento de `robot.launch.py`, para no acoplar los ciclos de vida. **Sin `enable`**: Nav2 cuesta ~58 % de un núcleo y la Pi se alimenta del USB del RVR, así que sale de la batería — y la autonomía (~2 h) ya no cubre una clase (2-3 h). Levanta **AMCL**, no SLAM, por el marco compartido. `03_operacion/ARRANQUE_NAVEGACION.md`. ⏳ **NO VERIFICADO**: exige el mapa del aula, que no existe |
| ⏳ **El seguidor de línea se valida EN EL AULA, no en casa** (decisión del usuario, 2026-08-09) | Una línea en el suelo de una habitación no reproduce lo que la práctica valida: el recorrido, la iluminación y el contraste del laboratorio. Y el seguidor decide **por umbral del canal `claro`**, que es justo lo que cambia con el suelo — medido: **1275 en una habitación y ~950 en otra, el mismo robot el mismo día**. Un ✅ en casa mediría **el suelo, no el algoritmo** |
| **El seguidor de línea es edge-following, NO un PID de umbral único** | Un solo sensor mirando abajo no puede distinguir desviarse a la izquierda de desviarse a la derecha — el diseño original de `API_LABORATORIO.md` no podía funcionar. Rediseñado en la tarea 11 (ver trampas, arriba). NO VERIFICADO sobre una línea real |

---

## Estilo de trabajo que espera el usuario

- **Español.** Toda la documentación y la comunicación.
- **Evidencia antes de afirmaciones.** Si dices que algo funciona, muestra la salida del
  comando que lo demuestra.
- **Corrige tus propios errores en voz alta.** En este proyecto se han retirado tres
  hallazgos de auditoría por estar equivocados, y eso es preferible a dejarlos.
- **Los pasos que requieren `sudo`, apagar la Pi o un PC externo los ejecuta el usuario**,
  no tú. Prepáraselos como script o comando exacto.
- **Avisa de las acciones físicas.** Reiniciar el driver despierta el RVR y gasta batería;
  cuando termines una prueba, para el nodo.
  📝 **CORREGIDO el 2026-08-04: arrancar el driver NO enciende ningún LED.** Esta línea decía
  «despertar el robot enciende sus LEDs» y se repitió como aviso durante meses. **Lo desmintió el
  usuario mirando el robot** («que sepas que no se encendieron los leds»), y se comprobó después:
  **cero llamadas a LEDs en `_conectar_rvr`**. Lo único que enciende algo es
  `color_detection:=true`, que está en `false` por defecto. Avisar de un efecto que no ocurre
  gasta la credibilidad del aviso que sí importa — y **el ojo de quien tiene el robot delante es
  el instrumento que manda**, que es una regla que este fichero ya tenía escrita.

---

## Cómo saber en qué punto estás

### Primero: pasa el verificador. Un comando en vez de veinticinco.

```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```

**150 comprobaciones** sin `--hardware` ✅ medido 2026-08-07 (eran 105 con `--hardware` el
2026-08-01), 0 fallos, código de salida ≠ 0 si algo falla, y cada
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

🔴 **Y VAN NUEVE, el 2026-08-08:** declaró **FALLO** sobre la regla de polkit
`49-atriz-unidades.rules` **que estaba instalada y funcionando**. La causa es general y vale
para cualquier comprobación de fichero: `/etc/polkit-1/rules.d` es `drwxr-x--- root:polkitd`,
así que **`[[ -e fichero ]]` da falso exista o no el fichero** cuando el usuario no puede
atravesar el directorio. **«No puedo verlo» no es «no está»**, y confundirlos manda a
reinstalar lo que ya funciona.
→ Lo desmintió el **efecto**: `start` y `stop` devolvían 0 sobre las unidades atriz cuando el
  permiso por defecto de polkit para `manage-units` es `auth_admin`, mientras `reset-failed`
  seguía denegado. **Esa asimetría solo la puede producir una lista blanca por verbo.**
→ ✅ Arreglado en el manifiesto (dice «NO SE PUEDE COMPROBAR sin privilegio») y con una
  comprobación **por efecto** —`stop` sobre una unidad ya parada, que es no-op pero pasa por
  el mismo control— **más un control negativo**: `reset-failed` tiene que seguir denegado, o
  el permiso sería general y **cualquiera que entre por rosbridge lo hereda**.

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

> ✅ **COMPROBADO el 2026-08-11 con rvr-02: `provision.sh` se ha ejecutado ENTERO**, sobre un
> Ubuntu Server 24.04 limpio, y termina con **96 ✓ · 16 avisos · 0 fallos**. Dejó de ser
> «la suposición más peligrosa que le queda al proyecto». Evidencia 98.
>
> 🔴 Pero no a la primera: la primera pasada tiró los dos últimos pasos con **el mismo fallo del
> 2026-08-10**, o sea reproducible. Causa: `install -d -o usuario .../atriz_ws/src` deja el
> **padre** `atriz_ws` de root —coreutils da a los padres los atributos por defecto, no los
> pedidos— y `colcon build`, que corre como el usuario, muere con `Permission denied: 'log'`.
> Arreglado en el guion, no a mano.
>
> Texto anterior: *«nunca se ha ejecutado de principio a fin sobre un 24.04 limpio: exigiría
> reflashear rvr-01, el único robot montado, y el usuario decidió no hacerlo (2026-07-31)»*.
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

En un sistema recién instalado no hay credenciales de git, y los commits se quedan solo en la
tarjeta — exactamente el riesgo que este proyecto ya sufrió con un stash.

🔴 **El control que había aquí dejó de servir el 2026-08-11.** Era:

```bash
git -C ~/atriz_migracion fetch origin && echo "OK: hay credenciales"   # ← YA NO PRUEBA NADA
```

y se apoyaba en que el repositorio fuera privado. Desde que es **público**, `git fetch` funciona
**anónimo**: el control pasa siempre, tengas credenciales o no. Es otra comprobación que no puede
fallar, el patrón que este proyecto persigue en todas partes.

**Lo que sí lo prueba es un `push`, porque escribir siempre exige autenticación:**

```bash
git -C ~/atriz_migracion push --dry-run origin HEAD && echo "OK: SÍ puedo subir"
```

Si falla, es la persona quien lo arregla (el token es un secreto, no se pone en el repo ni se
teclea en un comando que quede en el historial):

```bash
git config --global credential.helper 'store --file ~/.git-credentials'
cd ~/atriz_migracion && git push --dry-run origin HEAD   # Username: Bura-hub · Password: el PAT
chmod 600 ~/.git-credentials
```

📌 Para **clonar** no hace falta nada: `Atriz_migracion_ros2` y `Atriz_rvr` son públicos. El PAT
solo hace falta para **subir**, y solo en el robot desde el que se suba.

`fase_0_3_respaldo.sh` respalda `~/.git-credentials` desde el 2026-07-30, para no repetirlo.
