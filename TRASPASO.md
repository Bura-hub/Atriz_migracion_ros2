# Traspaso — dónde estamos y cómo seguir

> **Léelo si retomas el proyecto** después de un tiempo, en otra máquina, o si la
> Raspberry Pi ya se reflasheó. Está escrito para que no haga falta reconstruir el
> contexto desde cero.
>
> Última actualización: **2026-07-31**.

---

## En una frase

**🟢 La migración funciona: el robot corre sobre ROS 2 Jazzy y SLAM ya mapea.** Ubuntu Server
24.04.4 + Jazzy instalados, driver portado a `rclpy` (`/odom` a 16.67 Hz), URDF y árbol TF
enteros, LIDAR publicando `/scan`, y `slam_toolbox` activo publicando `/map`.

✅ **Y el enlace ya aguanta solo.** El RVR se dormía a los **300.6 s** y el nodo no se
enteraba; desde el 2026-07-31 el driver le habla cada 30 s, publica `/battery_state`, y avisa
y reanuda si aun así deja de llegar telemetría. Verificado: 12 min sin un hueco, contra 2
huecos sin el arreglo (manual, cap. 9.8).

✅ **Y la Fase 4 está CERRADA.** `slam_toolbox` mapea de verdad: moviendo el robot 1.78 m el
mapa pasó de **2367 a 3299 celdas** (5.92 → 8.25 m²). Hicieron falta tres arreglos y corregir
dos herramientas propias, y **ninguno de los fallos daba un error** (manual, cap. 9.11).

✅ **Y la deriva de la localización está caracterizada**: 6 corridas dan una mediana de
**1.0 cm** (recorridos de 1.6 m) y **2.7 cm** (2.4 m), con un peor caso de 3.2 cm. El error
cabe en una celda del mapa, así que **la pose ya no bloquea Nav2**.

✅ **Y los TRES bugs de marcos de referencia de `/odom` están arreglados y verificados.** Los
sensores del RVR siempre estuvieron bien —`Velocity` es exacto, el locator acierta con 1 mm en
1 m—; lo que fallaba era cómo el driver los combinaba. Ahora el yaw arranca en **+0.00°**, la
dirección de avance coincide con él (**+0.03°**), y `odom.twist.linear` da la velocidad en el
marco del robot con un **2 % de error** mire donde mire (`15_velocidad_odom.txt`).

🟡 **Nav2 está instalado, medido y configurado — pero SIN PROBAR contra el robot.** Manual,
**cap. 11**. Lo siguiente es exactamente eso: arrancarlo y mandarle un objetivo.

---

## Qué está verificado (con mediciones, no suposiciones)

| Componente | 20.04 + Noetic | **24.04** | Evidencia |
|---|---|---|---|
| Raspberry Pi 4B 8 GB | ✅ 57 °C, cero throttling | ✅ 63.7 °C, `throttled=0x0` | `evidencia*/` |
| Enlace UART Pi ↔ RVR | ✅ PL011 vía `/dev/rvr` | ✅ **el RVR contesta**, firmware 9.1.462 | `raw_uart_2026-07-30.txt` |
| YDLIDAR X2 | ✅ 100 % checksums, 11.4 Hz | ✅ **100 %, 11.48 Hz** | `lidar_x2_2026-07-30.txt` |
| Higiene del SO | receta documentada | ✅ **aplicada** | `02_higiene_aplicada_*.txt` |
| Telemetría del RVR a 16.59 Hz | ✅ 12 min, 0 huecos, 0 pérdidas | ✅ **12 min, 0 huecos** con el driver ROS 2 y keepalive | `12_keepalive_rvr.txt` |
| SDK de Sphero | ✅ GO en Python 3.8 | 🟢 **GO en 3.12**, 16.67 Hz | `04_gonogo_sdk_py312_*.txt` |
| Enlace estable sin tocar nada | — | ✅ el RVR se dormía a los **300.6 s**; arreglado | `12_keepalive_rvr.txt` |

Firmware del RVR: **9.1.462** (Nordic), confirmado también en 24.04 leyendo el payload de
`get_version` (`09 00 01 01`).

⚠️ Las dos líneas base son distintas y **no se mezclan**: `00_auditoria/evidencia/` es el
sistema viejo, `00_auditoria/evidencia_24_04/` el nuevo.

## Qué está roto y confirmado

| Problema | Gravedad | Estado |
|---|---|---|
| ~~El RVR se duerme solo y el driver no se entera~~ | seguridad operativa | ✅ **resuelto 2026-07-31**: timeout medido en **300.6 s**, keepalive cada 30 s + detector de silencio. 2 huecos → 0 |
| ~~La velocidad de `/odom` sale en el marco equivocado~~ | bloqueaba Nav2 | ✅ **resuelto 2026-07-31**: rotación −90° + proyección sobre el rumbo. **2 % de error** con el robot a 84° |
| ~~La posición y la orientación de `/odom` tienen manos contrarias~~ | bloqueaba Nav2 | ✅ **resuelto**: sobraba el `−Y`. Ahora giran igual (+89.87° vs +90.00°) |
| ~~El eje X del locator está 90° girado~~ | bloqueaba Nav2 | ✅ **resuelto**: `R(−90°)·(x,y) = (y,−x)` en `_h_locator` |
| 📝 `reset_yaw()` **no hace nada** — el yaw se pone a cero al **encender** el RVR | menor | ✅ **corregido**: el driver mide `yaw₀` al conectar y lo resta. Cinco arranques dieron cinco offsets distintos |
| ~~`inverted` del LIDAR sin verificar~~ | corrompe mapas | ✅ **verificado 2026-07-31**: `true` es CORRECTO. El equivocado era el yaw de `/odom` |
| 🔴 **El robot está inclinado ~8°** (árbol TF, Roll de la IMU y acelerómetro: **tres** vías) | calidad de Nav2 | 🔴 abierto, causa sin determinar. **No urgente**: con ella la deriva de SLAM es de 2.7 cm |
| 🔴 **La parada de emergencia de la web no hace nada.** Publica en `/rvr/emergency_stop`, que no existe. Falla **en silencio** con `200 OK` | seguridad | ⏳ el topic ya existe en el driver ROS 2; falta el lado web (fase final) |
| **Credencial del usuario `sphero` expuesta** en `Atriz_web_server` público, sin rotar | seguridad | 🔴 abierto — acción del usuario |
| **Sin arranque automático** — ninguna unidad systemd | operación | ⏳ pendiente |
| 16 de 20 servicios y 4 topics sin portar | funcionalidad | ⏳ diferido por el usuario |
| ~~No hay watchdog de `cmd_vel`~~ | seguridad | ✅ **resuelto**: para en 527 ms / 7.9 cm |
| ~~No hay URDF → árbol TF partido~~ | bloqueante | ✅ **resuelto**: `atriz_rvr_description` |
| ~~Driver ROS del LIDAR no instalado~~ | bloqueante | ✅ **resuelto**: `/scan` a 10.1 Hz |
| ~~Sin SLAM~~ | bloqueante | ✅ **Fase 4 CERRADA 2026-07-31**: el mapa crece al moverse (2367 → 3299 celdas) |
| ~~`imu.angular_velocity` en deg/s~~ | calidad de SLAM | ✅ **resuelto**: rad/s (REP-103) |

---

## El siguiente paso, exacto

### ✅ Hecho el 2026-07-31: el keepalive del driver

**El RVR se dormía a los 300.6 s = 5.01 min** y el nodo no se enteraba. Medido y arreglado
(manual cap. 9.8a–9.8c). Se durmió **dos veces** en 12 min sin keepalive, y las dos aguantó
300.6 s **exactos**: es un temporizador del firmware.

- **`_keepalive`** cada 30 s con `get_battery_percentage()` — y publica **`/battery_state`**,
  que no existía ni en ROS 1.
- **`_vigilar_silencio`** a 1 Hz: si pasan 3 s sin muestras, avisa e intenta reanudar.
  Verificado: detectó a los 3.4 s y reanudó en 4 ms, las dos veces, 0 fallos.

Contraste: **2 huecos sin keepalive, 0 con él**, en 12 min cada prueba.

### ✅ Hecho el 2026-07-31: Fase 4 CERRADA

`slam_toolbox` mapea. Verificado moviendo el robot: **2367 → 3299 celdas**, 5.92 → 8.25 m².
Manual cap. 9, evidencia `13_fase4_cerrada.txt`.

Hicieron falta tres arreglos y corregir dos herramientas propias, y **ninguno daba un error**:

- **El yaw de `/odom` tenía el signo invertido** — el RVR reporta el cuaternión y el locator
  en FRD y el driver los copiaba crudos. `/scan` y `/odom` decían que giraba en sentidos
  contrarios. ✅ `inverted: true` del LIDAR **era correcto**; el LIDAR nunca fue el problema.
- **El acelerómetro venía en `g`**, no en m/s². Ni el driver de ROS 1 lo convertía.
- **`fixed_resolution: false`** hacía que `slam_toolbox` descartara barridos (254/255 puntos).
- **Mi herramienta medía algo imposible**: giraba en el sitio y esperaba que el mapa creciera.

### ✅ Hecho el 2026-07-31: la deriva, caracterizada

**Es pequeña y estable.** 6 corridas con las variables controladas (mismo pasillo de 3 m,
`slam_toolbox` reiniciado de cero en cada una, sin nadie cruzando):

| Recorrido | n | Deriva mediana | Peor caso | σ |
|---|---|---|---|---|
| ~159 cm | 3 | **1.0 cm** y 1.3° | 2.7 cm | 1.0 cm |
| ~237 cm | 3 | **2.7 cm** y 2.3° | 3.2 cm | 0.6 cm |

El error **cabe dentro de una celda del mapa** (5 cm). ✅ **La localización ya no es un
bloqueante para Nav2.** Los 87.8 cm de la Fase 4 fueron una anomalía, 30 veces peor que lo
normal a distancia comparable — muy probablemente por rozar obstáculos, aunque **no se
reprodujo a propósito**, así que no es una causa demostrada.

### ✅ Hecho: los TRES bugs de marcos, arreglados y verificados

**Medido, implementado pieza a pieza y verificado cada una por separado**
(evidencia `15_velocidad_odom.txt`). Los sensores del RVR estaban bien; lo que fallaba era
cómo el driver combinaba sus marcos.

| Pieza | Qué se hizo | Verificación |
|---|---|---|
| **1. Orientación** | restar el yaw del arranque | yaw en reposo: **+0.00°** (antes −74.6° / +64.9°) |
| **2. Posición** | quitar el `−Y` y rotar −90° | dirección vs yaw: **+0.03°** (antes −89.7°), y giran en el **mismo** sentido |
| **3. Velocidad** | la misma rotación + proyectar sobre el rumbo | con el robot a 84°: **(+0.101, +0.001)** vs 0.099 real (antes daba `(-0.000, -0.200)`) |

📝 Cinco arranques dieron cinco offsets de yaw distintos (+51.1°, +52.7°, +56.5°, −74.6°,
+64.9°): confirma que no había constante posible y que solo se puede medir en cada arranque.

🔴 **Y una trampa nueva que costó dar por fallida una corrección correcta:** `colcon build`
lanzado desde `src/Atriz_rvr` en vez de la raíz del workspace crea ahí dentro un **workspace
parásito**, dice «Finished», y el cambio **nunca llega al sistema**. Pasó dos veces. Está en
`CLAUDE.md` con cómo detectarlo.

### ✅ Hecho: Nav2 instalado, medido y configurado

- **`ros-jazzy-navigation2`, NO `nav2-bringup`** — 309 paquetes contra 621. `bringup` arrastra
  Gazebo, dos TurtleBots de simulación y `pocketsphinx-en-us`. Verificado: cero paquetes de
  simulador instalados, disco +900 MB.
- ✅ **`save_map` arreglado**: con `nav2-map-server` devuelve `result=0` y genera el `.pgm` +
  `.yaml`. El diagnóstico del capítulo 9.5 era correcto.
- ✅ **Velocidades medidas**: lineal **0.401 m/s** (100 % de lo comandado, en ~0.5 s) y angular
  **99–102 %** hasta 2.0 rad/s. ⚠️ Esto **retracta** el «0.40 → 63 %» que este documento llegó
  a tener: era la ventana de medida.
- **`nav2_atriz.yaml` con los valores medidos**, no los del ejemplo — el `robot_radius` del
  TurtleBot es **el doble** del real, y con él el robot se negaría a pasar por huecos por los
  que cabe.

### 1. ⏳ Probar Nav2 — es lo siguiente

```bash
ros2 launch atriz_rvr_bringup robot.launch.py    # terminal 1
ros2 launch atriz_rvr_bringup slam.launch.py     # terminal 2
ros2 launch atriz_rvr_bringup nav2.launch.py     # terminal 3
```

🔴 **Antes de mandar ningún objetivo**, comprobar que los cinco nodos llegan a `active [3]` y
que `/scan` tiene **dos** suscriptores en BEST_EFFORT. Si el QoS no emparejara, el costmap se
quedaría vacío **sin dar error** y el robot navegaría creyendo que no hay nada delante.

⚠️ Necesita el pasillo despejado y alguien mirando: el robot se moverá solo hasta 0.25 m/s y
**no tiene evitación reactiva** — el `collision_monitor` aún no está configurado.

### 2. 🔴 La inclinación de ~8°, confirmada por TRES vías

Árbol TF, `Roll` de la IMU y el acelerómetro con unidades correctas. Causa sin determinar.

📝 La caracterización de la deriva **acota su gravedad**: con la inclinación presente, la
deriva es de 2.7 cm, así que no está arruinando el emparejado. Hay que resolverla para Nav2
—por REP-105 `odom → base_footprint` debería ser plana— pero **no es urgente**.

---

## Histórico de fases cerradas

**Fase 2 del plan — portar el driver a `rclpy`.** Era el trabajo grande.

✅ **La Fase 2 está ARRANCADA y el núcleo funciona** (2026-07-30, rama **`ros2`**, commit
`80e1cbf`). **Verificado contra el robot real** — no lo repitas:

| | |
|---|---|
| `atriz_rvr_msgs` | ✅ portado a `ament_cmake` + `rosidl`, 6 msg + 20 srv |
| `atriz_rvr_driver` | ✅ portado a `ament_python`, el nodo corre |
| `/odom` | ✅ **16.671 Hz**, σ 0.47 ms (ROS 1 daba 16.59) |
| `imu.angular_velocity` | ✅ rad/s (antes deg/s, violaba REP-103) |
| árbol TF | ✅ `odom → base_footprint` (antes `rvr_base_link`, partido; y `base_link` fue mal hasta la Fase 4, ver abajo) |
| `cmd_vel` | ✅ 34 cm a 0.15 m/s en 2 s |
| watchdog | ✅ quieto en 527 ms, ~7.9 cm. **Primera vez que se prueba** |
| Fase 2.1 limpieza | ✅ 79 ficheros y 700 KB menos |

**Lo que queda del nodo:** 16 de los 20 servicios y 4 topics, listados al final de
`rvr_driver_node.py`.

✅ **Fase 3 COMPLETA, incluido el LIDAR** (commit `b117791`). Un comando arranca el robot
entero: `ros2 launch atriz_rvr_bringup robot.launch.py` → `/odom` 16.99 Hz, `/scan` 10.1 Hz,
árbol TF resuelto.

✅ **El riesgo del QoS de `/scan` era infundado**, comprobado en la Fase 4: `slam_toolbox` se
suscribe con **BEST_EFFORT**, igual que publica el driver del LIDAR. Emparejan. Sigue siendo
cierto que **`rclpy` pide RELIABLE por defecto**, así que cualquier suscriptor propio a `/scan`
tiene que pedir BEST_EFFORT explícitamente o no recibirá nada, sin error.

✅ **Fase 4 PARCIAL** (manual cap. 9, evidencia `11_slam_fase4.txt`). `slam_toolbox` arranca,
se activa y publica `/map` a 0.200 Hz; el árbol TF llega hasta `map`. Coste: **4.5 % de CPU**,
y ~24 % con todo a la vez. Dos hallazgos que hubo que arreglar:

- **Es un nodo de ciclo de vida**: arrancaba en `unconfigured`, vivo y sin hacer nada.
  `slam.launch.py` ahora usa `LifecycleNode` + `configure`/`activate`.
- **`base_link` tenía dos padres** (`odom → base_link` del driver y `base_footprint →
  base_link` del URDF) → el árbol se partía y `slam_toolbox` repetía `Failed to compute odom
  pose`. El driver publica ahora **`odom → base_footprint`** (REP-105).

⚠️ **Y la Fase 3 lo había dado por bueno**: su comprobación `tf2_echo odom laser` **pasaba**,
resolviendo por el camino equivocado. **Comprueba el transform que pide el consumidor, con sus
frames exactos** — aquí `tf2_echo odom base_footprint`.

📝 **`save_map` no funciona sin Nav2** (`result=255`, `Package 'nav2_map_server' not found`).
Para guardar un mapa hoy: `serialize_map`, que es nativo (`result=0`).

✅ **Fase 3.1 cerrada** (commit `719c769`): el paquete `atriz_rvr_description` une el árbol TF, que
estaba partido en dos y era el bloqueante raíz de SLAM. **Verificado sobre el robot:**
`tf2_echo odom laser` resuelve con `Translation: [-0.018, -0.002, 0.141]`, y antes respondía
«Could not find a connection».

Medida del LIDAR: **17.45 cm** sobre el suelo (centrado, 4 cm de hueco medidos). El proyecto
arrastraba `0.10`, que se quedaba **7.4 cm corto** y habría inclinado el mapa.

⚠️ **RETRACTADO el 2026-07-31 — se conserva porque explica cómo se llegó al error.**

Esto decía: «un bloqueante nuevo antes de SLAM: la velocidad de `/odom` es basura. El stream
`Velocity` del RVR reporta 0.001 m/s con el robot a 0.147 m/s reales».

**La observación era cierta; la conclusión, falsa.** `Velocity` es **exacto** (0 % de error en
módulo, 0.1° en dirección) y viene en el marco del **mundo**. Se leyó solo su componente X con
el robot encarado a ~90° de ese eje, donde X vale ~0 aunque el robot cruce la habitación.
El fallo está en el **driver**, no en el sensor. Ver `15_velocidad_odom.txt`.

🔴 **Hasta que esto se haga, el driver del robot NO se ha ejecutado nunca en este sistema — y
no puede.** No es «pendiente de probar», es **imposible**: `Atriz_rvr_node.py` es ROS 1.
Medido el 2026-07-30 sobre `migracion-ros2` (`24c7749`):

| | |
|---|---|
| `Atriz_rvr_node.py` | **1704 líneas** |
| referencias a `rospy.*` | **99** (y `rospy` no existe en ROS 2) |
| llamadas a `asyncio.run()` | **48**, cada una crea y destruye un event loop entero |
| paquetes | 3, los tres **catkin** — no `ament` |
| interfaces | 6 `.msg` + 20 `.srv`, todas registradas correctamente |

`colcon build` fallará, y **debe** fallar. Lo que sí está validado es el **SDK** (Etapa D, 🟢
GO): es la pieza insustituible, la única que sabe hablar con el RVR. El driver es código propio
y por tanto reescribible.

**Lo que el port tiene que incluir** (plan, Fase 2, apartados 2.1 a 2.4):

1. **Limpieza previa.** Borrar lastre en vez de portarlo: los `.cpp` y `src/rvr++/`
   (`hardware_interface` que nunca se ejecutó), el paquete `atriz_rvr_serial`, y
   `scripts/rvr-ros.py` — confirmado el 2026-07-30 que **no tiene bit de ejecución**.
2. **Los 3 paquetes catkin → `ament`**, y `atriz_rvr_msgs` a `rosidl`.
3. **El arreglo estructural.** Hoy el event loop de asyncio solo avanza en ráfagas dentro de un
   `while not rospy.is_shutdown()`. Pasa a vivir en su propio hilo, y los comandos entran con
   `asyncio.run_coroutine_threadsafe` en lugar de crear un loop por cada `cmd_vel`.
4. 🔴 **Watchdog de `cmd_vel` — seguridad, y hoy no existe.** Si cae la red, el robot sigue
   ejecutando el último comando indefinidamente. Debe parar los motores si no llega `cmd_vel`
   en 500 ms.
5. 🔴 **`imu.angular_velocity` a rad/s.** Hoy va en deg/s y viola REP-103, lo que degrada la
   calidad de SLAM. Y `gyroscope_handler` publica **dos veces**, en unidades distintas.
6. Parametrizar `serial_port` (por defecto `/dev/rvr`), `baud`, los frames y
   `streaming_interval_ms` con `declare_parameter`. Nada hardcodeado.

**Lo que NO hay que volver a tocar:** el `interval=60` ya está aplicado (16.59 Hz medidos), y
el puerto ya es `/dev/rvr`. Ambos verificados hoy en el SDK.

**Después del port viene la Fase 3, el URDF**, que el plan llama **el bloqueante raíz**: el
árbol TF está partido en dos (`odom → rvr_base_link` por un lado, el LIDAR colgando de
`base_link` por otro) y sin un árbol conectado SLAM es imposible por bien que funcione el
driver.

⚠️ **Y antes de crear la imagen dorada:** quitar `ROS_DOMAIN_ID` de `~/.bashrc`. Está puesto
ahí a mano porque `atriz-first-boot` no está instalado todavía, pero el `.bashrc` se lee
**después** de `/etc/profile.d/`, así que clonar tal cual dejaría **los 16 robots en el dominio
1** sin que nada avise. `verificar_robot.sh` ya comprueba esa colisión.

### Ya hecho, no lo repitas

| Etapa | Estado |
|---|---|
| **A** — imagen `dd` del sistema Noetic | ✅ hecha **y verificada**. La reversión existe |
| **B** — instalar 24.04, `cmdline.txt`, `config.txt`, UART, `/dev/rvr` | ✅ verificado 2026-07-30 |
| **B5** — actualizaciones cerradas y credenciales de git | ✅ 2026-07-30 |
| **C** — higiene del SO (arranque 1min39s → **8.7 s**) | ✅ verificado 2026-07-30 |
| **D** — **GO/NO-GO del SDK en Python 3.12** | ✅ 🟢 **GO** — 16.67 Hz, firmware 9.1.462 |
| **E3/E4** — verificación de UART y LIDAR | ✅ hechas ya, sobre 24.04 |

Y para no repetir la verificación a mano: **`bash scripts/verificar_robot.sh --hardware`**
hace 48 comprobaciones y sale con código ≠ 0 si algo falla. En `rvr-01`, el 2026-07-30: **48
correctas, 0 fallos**.

✅ **El `stash@{0}` ya está rescatado.** Contenía tres scripts de estudiantes que solo
existían en un stash local — y los stashes **no viajan a un remoto**, así que se habrían
perdido al reflashear. Están preservados sin modificar en la rama
**`wip/scripts-estudiantes`** (commit `62e0313`). El stash original se conserva intacto
(se usó `stash apply`, no `pop`).

⚠️ **Decisión pendiente sobre `01_avanzar.py`.** No está modificado: está **reemplazado**.
El tutorial «ULTRA SIMPLE: solo avanza el robot» ya no existe en esa rama; en su lugar hay
una clase `SeguidorBordeRojo` que sigue el borde de una línea roja con `/color` y el servicio
`/enable_color`. Parece un experimento escrito encima del fichero equivocado — es el
**primer** script que ejecutan los estudiantes y ya no hace lo que su nombre promete.
Además `origin/main` ya trae `scripts/estudiantes/seguidor_linea_pid_demo.py`, que aborda el
mismo problema.

Hay que decidir: **(a)** mover el seguidor a su propio fichero y restaurar el tutorial, o
**(b)** descartarlo por estar superado por `seguidor_linea_pid_demo.py`. Por eso la rama es
WIP y **no debe mezclarse con `main`** hasta resolverlo.

⚠️ **Antes de apagar la Pi en cualquier momento, comprueba que no queda nada sin subir.** Es
lo que hace `fase_0_3_respaldo.sh`, pero conviene saber por qué: un commit local o un stash
**no existen** para nadie más, y desaparecen con la tarjeta.

```bash
for r in ~/atriz_ws/src/Atriz_rvr ~/atriz_migracion; do
  echo "── $r"; git -C $r status -sb | head -1; git -C $r stash list
done
```

🔴 **Y comprueba que PUEDES subir.** En un sistema recién instalado no hay credenciales y el
repositorio es privado: `git fetch` falla con `could not read Username`, así que los commits se
quedan solo en la tarjeta. Pasó el 2026-07-30 — ver `CLAUDE.md`, «Antes de subir nada».

```bash
git -C ~/atriz_migracion fetch origin && echo "OK: hay credenciales"
```

### Reinstalar con ayuda de un agente

Tras grabar Ubuntu Server 24.04 y clonar este repositorio, basta con arrancar Claude Code
en `~/atriz_migracion` y decirle:

> Lee CLAUDE.md y sigue INSTALACION.md para poner el sistema a punto.

`CLAUDE.md` se carga solo y le da las reglas, las trampas conocidas y los valores de
referencia de **ambos** sistemas.

**Estado de los capítulos del manual tras la sesión del 2026-07-30:**

| Cap. | Contenido | Estado |
|---|---|---|
| 1 | Enlace UART | ✅ verificado en 20.04 **y en 24.04** |
| 3 | Flasheo de 24.04, `cmdline.txt`, `config.txt` | ✅ **verificado** — dejó de ser NO VERIFICADO |
| 4 | Higiene del SO | ✅ **verificado** — dejó de ser NO VERIFICADO |
| 5 | ROS 2 Jazzy y workspace | ✅ **verificado 2026-07-30** — 201 paquetes, `ros2 doctor` 5/5 |
| 8 | YDLIDAR X2 | ✅ hardware verificado en ambos; driver ROS pendiente |

Los capítulos 3 y 4 se recorrieron y **se corrigieron sobre la marcha**, que es lo que pedía
la nota. El 5 sigue sin ejecutarse: al recorrerlo, corregirlo en el momento y cambiar su marca
a ✅ con la fecha. **En el repositorio, no en un mensaje de chat.**

---

## Estado de los repositorios

| Repo | Rama | Commit | Contenido |
|---|---|---|---|
| `Atriz_migracion_ros2` | `main` | — | Este repositorio: auditoría, plan, manual, scripts |
| `Atriz_rvr` | `main` | `6f48ae1` | Original + **el arreglo del UART** (cherry-pick de `67c8776`) |
| `Atriz_rvr` | **`ros2`** ← rama de trabajo actual | `1b1239a` | `atriz_rvr_msgs` portado a ament+rosidl |
| `Atriz_rvr` | `migracion-ros2` | `24c7749` | UART → `/dev/rvr` · `interval` 250→60 ms |
| `Atriz_rvr` | `wip/scripts-estudiantes` | `62e0313` | Stash rescatado. **No mezclar** — ver decisión pendiente arriba |
| `Atriz_web_server` | `pruebas` | `924d659` | Sin tocar — se aborda al final |

La rama `migracion-ros2` se creó **desde `origin/main`**, no desde el clon local. Importante:
ver la lección de abajo.

### ⚠️ Por qué el arreglo del UART también está en `main`

La imagen de respaldo de la Fase 0.3 se crea sobre un sistema que **ya tiene
`dtoverlay=disable-bt` aplicado**, así que en él `/dev/ttyS0` **ya no lleva el UART**.

Si se restaurara esa imagen y se trabajara desde `main` con el código original, el robot
parecería roto sin motivo aparente: el driver abriría un puerto que existe pero no está
conectado a nada. Por eso el commit del UART se llevó también a `main` (cherry-pick
`6f48ae1`).

**Regla general:** cualquier arreglo que dependa de la configuración del sistema operativo
—no solo de ROS— debe estar en `main`, porque `main` es lo que se ejecuta si algo se revierte.

### Ficheros sueltos sin versionar

`carro.py` (**0 bytes**, nada que salvar) y `prueba.py` (92 líneas) siguen sin trackear.

`prueba.py` es un tercer intento de seguidor de línea y **está roto**: define
`def _init_(self)` con **un solo guion bajo** en lugar de `__init__`, así que el constructor
nunca se ejecuta y la clase no hace nada. Además se suscribe a `/color_sensor_left` y
`/color_sensor_right`, que **no existen** — el driver publica únicamente `/color`.

Están respaldados como ficheros en `04_respaldo/sin_commitear/archivos/`. **Decisión
pendiente:** versionarlos o descartarlos. Recomendación: borrar `carro.py` y no recuperar
`prueba.py`, ya que `seguidor_linea_pid_demo.py` (en `origin/main`) resuelve lo mismo y
funciona.

---

## Cinco lecciones que ahorran horas

**1. `git fetch` antes de auditar cualquier cosa.** Se hizo una auditoría completa sobre un
clon **5 commits por detrás** al que **nunca se le había hecho `fetch`**. Tres hallazgos
resultaron falsos. Es el error más caro de la sesión.

**2. Un robot dormido parece un cable roto.** Cero bytes de respuesta, idéntico síntoma.
**Apaga y enciende el robot antes de tocar configuración.** Se perdió un buen rato
persiguiendo un problema de device-tree que no existía.

**3. Que el nodo arranque no prueba que el enlace funcione.** `rvr_fw_check_async.py` hace
`except (asyncio.TimeoutError, Exception)` y continúa en silencio. Pero el **tiempo de
construcción** sí es diagnóstico: **0 s** = el robot responde, **~10 s** = dos timeouts = no
responde.

**4. No uses `pkill -f Atriz_rvr_node`.** El patrón coincide con la propia línea de comando
del shell que lo ejecuta y **mata tu terminal**. Pasó dos veces. Usa `pgrep -f "[A]triz..."`
con el corchete, o el PID.

**5. Mide antes de atribuir.** La auditoría culpó al bucle de asyncio de la odometría a
4 Hz. Midiendo el SDK **sin ROS** salió idéntico: la causa era un solo parámetro. El arreglo
fue **una línea** en vez de una reescritura.

---

## Herramientas de diagnóstico disponibles

Todas en `00_auditoria/evidencia/mediciones_banco/`, con su README:

```bash
raw_uart.py      # ¿contesta el RVR a nivel de bytes?     <- el más útil
x2_parse.py      # ¿funciona el LIDAR? (sin driver ROS)
medir.py         # frecuencia y jitter de /odom e /imu
sdk_full.py 60   # ritmo del SDK con los 8 sensores
estabilidad.py   # 12 min: huecos, pérdidas, fugas de memoria
test_rvr.py      # diálogo básico con el SDK
```
Y en `scripts/`: `fase_0_1_fix_uart.sh`, `diag_uart_pins.sh`,
`fase_0_3_respaldo.sh`, `fase_1_validar_sdk_py312.py`.

---

## Decisiones ya tomadas — no volver a discutirlas

| Decisión | Dónde está razonada |
|---|---|
| Ubuntu Server 24.04 + ROS 2 Jazzy (soporte a mayo 2029) | plan, Contexto |
| Reinstalar **sobre la misma microSD**; reversión por imagen `dd` | plan, Fase 0.3 |
| **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total | `ARQUITECTURA.md`, D1 |
| La web habla por **rosbridge**, no por SSH | `ARQUITECTURA.md`, D2 |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final**, cuando el robot esté funcional | decisión del usuario |

---

## Lo que sigue sin medir

- **Ancho de banda por robot con rosbridge activo.** Es el **riesgo principal del escalado**
  y la decisión de compra de red más cara. Medir con un robot en la Fase 5 y extrapolar.
- Si Nav2 cabe en el Pi 4 junto al resto (referencia: el driver solo ya usa 29.5 % de un núcleo).
- Latencia de `cmd_vel` de extremo a extremo, y el impacto de las **48** llamadas a
  `asyncio.run()` en callbacks.
- Si el driver del X2 puede fijar la velocidad de giro (afectaría a la resolución del mapa).
- Si los 16 adaptadores USB comparten el mismo `SerialNumber "0001"`.
