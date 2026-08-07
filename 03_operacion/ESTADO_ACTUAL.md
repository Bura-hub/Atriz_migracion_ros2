# Estado actual

Fichero corto, para situarse en un minuto. **Es el canal de contexto entre el Claude del PC y el de
la Pi**, y el único que sobrevive cuando Claude Code se desinstale del robot.

`CLAUDE.md` son 107 KB (~26.800 tokens) y `TRASPASO.md` otros 72 KB: eso es para el detalle. Esto es
para saber por dónde vas.

> **Regla:** si algo importa y solo vive en un hilo de Claude, en `memory/` o en un transcripto,
> **no existe**. Se pierde al desinstalar. Lo que importe, aquí o en el repositorio.

---

**Última actualización:** 2026-08-06

---

## 📣 PARA EL CLAUDE DEL PC — el botón de color ya se puede construir

**El robot expone desde hoy el ciclo completo de la sesión de medición de color.** Los dos
servicios están en la lista blanca de rosbridge y **verificados a través de ella**:

| servicio | tipo | qué hace |
|---|---|---|
| `/enable_color` | `std_srvs/SetBool` | `data:true` enciende el LED del sensor y `/color` pasa a dar valores reales; `data:false` lo apaga |
| `/get_rgbc_sensor_values` | `atriz_rvr_msgs/srv/GetRGBCSensorValues` | lectura puntual en crudo (R, G, B, claro) |

Medido por el driver y por rosbridge: `/color` no-cero **0 → 53 → 0**, canal claro **1 → 1320 → 0**,
RGB reales `(255, 224, 208)`. Evidencia 76.

✅ **Y `color_activo` YA ESTÁ**, decidido y medido (2026-08-06 tarde). `EstadoRobot` pasa a **8
campos**; el nuevo va el último:

```
bool color_activo        # ¿hay luz en el sensor?
```

🔴 **Lo que te toca, y sin esto el cliente lanza antes de mandar nada:** añadir los dos servicios a
`contrato.ts` con sus tipos **y el campo nuevo a `EstadoRobot`**. `comprobar_contrato.mjs` seguirá
en rojo hasta entonces (la política es «gana el robot»). **Va todo en un solo commit del robot**
para que solo tengas que alinear una vez.

**Los tipos exactos:**

| | |
|---|---|
| `/enable_color` | `std_srvs/srv/SetBool` — petición `bool data`; respuesta `bool success`, `string message` |
| `/get_rgbc_sensor_values` | `atriz_rvr_msgs/srv/GetRGBCSensorValues` — petición **vacía**; respuesta `uint16 red_channel_value`, `uint16 green_channel_value`, `uint16 blue_channel_value`, `uint16 clear_channel_value`, `bool success`, `string message` |

🔴 **`enable_color` devuelve `success`, y NO hay que creérselo** — clasifícalo como los otros
cuatro de `confirmaEfecto()`. **El testigo es `color_activo`, no `/color`.** Esperar a que `/color`
deje de ser `[0,0,0]` funciona para encender, pero **falla para apagar y sobre negro**: el topic
publica ceros con la luz apagada *y* una superficie negra de verdad da valores muy bajos. `/color`
dice qué se ve; `color_activo` dice si hay luz para verlo.

🔴 **Y el estado hay que LEERLO, no recordarlo: la luz se apaga sola.** El driver la apaga por
inactividad (120 s sin nadie usándola) y por tope duro (900 s desde el enable), los dos como
parámetros del launch. Un flag local pintaría el botón encendido sobre un sensor a oscuras.

📝 **La actividad cuenta las dos vías** —suscriptores de `/color` **o** llamadas a
`get_rgbc_sensor_values`— porque `atriz.py` lee por servicio y si no se le cortaba la práctica al
alumno. Medido: con actividad sigue encendida a los 160 s; sin actividad se apaga a los 126 s.
Evidencia 77.

⚠️ **El botón de PARAR tiene que ser tan visible como el de arrancar.** El LED blanco gasta batería
mientras siga encendido, y son 16 robots. **Sin cifra**: cuánto gasta este LED en concreto no está
medido, y con el apagado automático puesto la exposición deja de ser indefinida.

📝 **Y por qué esto no estaba hecho antes:** el proyecto afirmaba en cinco documentos que era
imposible encender el sensor en caliente. **Era falso y nunca estuvo medido** — la prueba de julio
encendía y apagaba en la misma llamada. Detalle completo en el `CHANGELOG` del 2026-08-06 (tarde) y
en la evidencia 76. Si tenías algo diseñado sobre «hay que reiniciar el driver», **tíralo**: además
de caro, reiniciar **baja la parada de emergencia** (`rvr_driver_node.py:266`).

## 📣 PARA EL PC — la decisión de Nav2/SLAM NO está pendiente

Tu informe la lista como *«una decisión tuya, y bloquea A10 y A13»*. **Ya estaba tomada, y dos
veces.** Fui yo quien la reabrió por no cruzar con lo que había en el repositorio.

**1 · Con el usuario, el 2026-08-03** — [`ARRANQUE_NAVEGACION.md`](ARRANQUE_NAVEGACION.md):

| | |
|---|---|
| **Nav2** | unidad instalada y **NO habilitada**. *«No sobrevive a un reinicio… es la decisión del usuario y encaja con la línea del proyecto: nada de estado silencioso»* |
| **SLAM** | **a mano**, para hacer mapas: *«tarea de administrador, no de operación»* |

El dato que la decidió: **la Pi se alimenta del USB del RVR**, autonomía medida **~2 h** contra
clases de **2-3 h**, y Nav2 son **~58 % de un núcleo**. Salvedad que el propio documento escribe:
**cuánto cuesta en batería ese 58 % no lo sabe nadie** — la dirección está clara, la magnitud no.

**2 · El panel de cuatro agentes, el 2026-08-06** — `planes/2026-08-06-plan-slam-color-arranque.md`,
D2: `atriz-slam.service` instalada y **no habilitada**, y **A10 espera**. Honesto: la web sigue sin
poder arrancar SLAM, y se dice.

### 🔴 Y hay algo que te afecta directamente si ibas a construir sobre mi plan

En `planes/2026-08-06-arrancar-desde-la-web.md` escribí una **«solución A recomendada»**: servicios
del driver que hagan `systemctl start` con una regla de polkit. **Está RECHAZADA** — el panel la
había tumbado esa misma mañana (D2, opción c), por seguridad. Verificado en el código, no citado:

```
rosbridge_server/websocket_handler.py:233   def check_origin(self, origin) -> bool:
                                     :234       return True        ← sin condiciones
systemctl show atriz-robot -p User          →   User=sphero        ← el driver no es root
```

rosbridge **no autentica a nadie**, así que polkit convertiría *«cualquiera en la red del aula
llama a un servicio»* en ***«cualquiera en la red del aula hace que root arranque un proceso»***.

📌 **Lo que del apartado A sí se queda**, porque vale para cualquier mecanismo que se acabe
eligiendo: el callback no puede bloquear los otros 18 servicios del driver (comparten
`MutuallyExclusiveCallbackGroup`), el éxito se mide por efecto y no por el retorno de `systemctl`,
y Nav2 sin mapa debe **negarse y decirlo** en vez de intentarlo.
⚠️ **Corregido:** aquí ponía «bloquea `/release_emergency_stop`». Es falso — la parada está en
`g_cmd` (`rvr_driver_node.py:647-649`), no en `g_srv`.

### ✅ ACTUALIZACIÓN de esa misma noche — el usuario decidió, y el argumento de «root» era falso

**Decisión del usuario:** *«Ambas deberían poderse habilitar desde la web según la necesidad del
usuario. Apruebo que estén disponibles.»* → **se añade el mando, NO el arranque automático**.
Ninguna arranca sola al encender; eso no cambia.

🔴 **Y el argumento que las bloqueaba resultó inexacto.** Medido sobre la unidad **resuelta**, no
sobre el fichero:

```
systemctl show atriz-nav -p User -p AmbientCapabilities  →  User=sphero · (vacío)
ExecStartPre / ExecStart / ExecStopPost   →  ninguno lleva '+', '!' ni '!!'
```

Sin esos prefijos, `User=` se aplica a los tres. **No es «root arranca un proceso»**: systemd
arranca una unidad cuyos procesos corren como `sphero` sin capacidades. Y `sphero` no puede
escribir la unidad ni los scripts (`root:root`), y **ya está en el grupo `sudo`** — una regla
polkit no le da nada nuevo, le quita la contraseña.

📌 **Diseño completo en [`planes/2026-08-06-slam-y-nav2-desde-la-web.md`]**, de un panel de cuatro
agentes con las contradicciones zanjadas midiendo. Lo que te toca a ti está en su §6. Resumen:
dos servicios `std_srvs/SetBool` (`/pedir_slam`, `/pedir_nav`), un topic `/estado_navegacion` con
**seis** estados, y **el `success` no confirma nada** — igual que con `enable_color`.

🔴 **Y lo que NO va a entrar en la lista blanca, decidido:** ningún servicio de **guardar mapa**.
`slam_toolbox/SaveMap`, `SerializePoseGraph` y `nav2_msgs/SaveMap` **aceptan la ruta que les dé el
cliente** (`nav2_msgs/SaveMap.srv`: *«Can be an absolute path to a file»*). En un rosbridge sin
autenticación eso es escritura de fichero en ruta arbitraria. Guardar el mapa espera a la Fase B.

⏳ **Nada de esto se escribe todavía: hay cinco bloqueantes**, y el primero lo encontró el
escéptico y no estaba en ninguna lista — **esta Pi no tiene RTC y el reloj saltó +1 h 27 m dentro
del arranque de `robot.launch.py`**. ROS sella TF con ese reloj.

## ✅ Cerrado y comprobado — no lo vuelvas a poner como pendiente

> 🔴 **Esta sección existe porque el 2026-08-05 se listaron como pendientes CUATRO cosas que ya
> estaban hechas.** No fue descuido: quien las listó citaba este mismo fichero, fechado el día
> anterior, mientras el código y las evidencias habían seguido. **Un fichero de estado que se
> queda atrás es peor que no tenerlo**, porque manda a repetir trabajo con el sello de «está
> escrito». Antes de dar algo por pendiente, cruza con la evidencia; y si cierras algo, ciérralo
> **aquí** el mismo día.

| | evidencia |
|---|---|
| ✅ **`atriz-robot.sh` REINSTALADO** con el arreglo del `set -e` + `(( t++ ))` | `/usr/local/bin/atriz-robot.sh:102` tiene `t=$(( t + 1 ))`, `diagnosticar_lidar` está dentro, y `cmp` da **instalado == repositorio**. Manifiesto: 0 divergencias |
| ✅ **La tarea 9, CERRADA: la cinta y el control por SSH** | Evidencia 71. `web·3` → 30 cm · `web·4` → 30 · **`SSH·control` → 31 contra 31,3 de odometría**. Tres corridas, **dos transportes**, y la odometría acierta siempre dentro de la resolución de la cinta |
| ✅ **La parada de emergencia, con el robot EN MARCHA y por rosbridge** | **4 de 4** corridas paran el robot. Frenadas de **2,9 · 2,3 · 1,8 cm**, contra los 9,9-10,7 del `collision_monitor` |
| ✅ **`parada_emergencia` VISTO en `true`**, y en los dos sentidos | Evidencia 71: `🔴 parada_emergencia: False -> True (latido=2181)`, con el **flanco presenciado** —no una bandera encontrada ya puesta— y su vuelta a `false` al liberar |
| ✅ **El sensor de color se enciende y se apaga EN CALIENTE**, y hay servicio para ello | Evidencia 76. `/enable_color` (`std_srvs/SetBool`): `/color` no-cero **0 → 53 → 0**, canal claro **1 → 1320 → 0**, reversible, con el LED **visto** encenderse. Refuta lo que cinco documentos daban por medido |
| ✅ **El direccionamiento: una dirección por red, y el navegador entra por nombre** | Evidencias 74 y 75. `ws://rvr-01.local:9090` **abre** (4339 ms en frío, 2331 caliente), con control por IP y **control negativo** (`10.14.7.7` colgándose, que es la firma del fallo original) |

⚠️ **Y lo que de `/estado_robot` sigue SIN verificar, que no es lo mismo:** de sus **seis** campos
(siete con `color_activo`, añadido el 2026-08-06), están comprobados `parada_emergencia`, `latido`
y **`color_activo`** —este último en los dos sentidos y contra el valor del sensor, no contra sí
mismo—. **`rvr_responde`, `reanudaciones_fallidas` y `antiguedad_odom_s` no se han visto nunca en
su estado de fallo**, y son justo los campos que solo aparecen cuando algo se rompe. De esos tres
está probado que **no estorban**, no que **sirvan**.

## Los repositorios, de un vistazo

| Repo | Rama | Estado |
|---|---|---|
| `Atriz_migracion_ros2` | `main` | este; privado |
| `Atriz_rvr` | **`ros2`** ← por defecto desde el 2026-08-04 | público. Solo quedan **dos** ramas: `ros2` y `main` (ROS 1, 75 commits detrás). `migracion-ros2` y `wip/scripts-estudiantes` **borradas** el 2026-08-03 |
| `atriz-lab` | `main` | **el** repositorio de la web; privado. `cliente-rosbridge` fusionada (PR #1) y borrada |
| `Atriz_web_server` | `pruebas` | el viejo. **ARCHIVADO** el 2026-08-04, después de rotar. Público y en solo lectura; los secretos siguen en su historial pero **ya no valen** |
| `ATRIZ` | `master` | el **paraguas público** (⭐1) y los dos PDF institucionales. Su submódulo apuntaba a ROS 1 hasta el 2026-08-04 |

Los nueve del ecosistema, con quién es dueño de cuál: [`REPOSITORIOS.md`](REPOSITORIOS.md).

## En qué estamos

Cerrado hoy: la **alineación del robot con los repositorios** — 0 fallos en `verificar_robot.sh`,
con `atriz-nav` instalado y el parser de `robot_id.txt` unificado.

🔴 **Descartado hoy: el canal Claude↔Claude entre el PC y el robot.** Se diseñó, se construyó y se
probó; el usuario lo dio por no válido y se retiró entero. La conclusión que sí vale la pena
conservar: **no existe ningún mecanismo para que dos instancias de Claude Code compartan contexto**
—ni federación de sesiones, ni memoria compartida, ni `--resume` entre máquinas—, así que cualquier
intento futuro por ese camino parte de una premisa falsa. Lo que sí funciona entre las dos máquinas
es **el repositorio**: 249 commits en 7 días, mediana de 8 minutos.

🔴 **Y el mismo día, ya desde el PC: la sección 1 de ese plan tiene CUATRO afirmaciones falsas.** No
hay Monaco integrado —es un `<textarea>` con Prism, y «Monaco» era la **tipografía** en una línea de
CSS—, `POST /api/robots/execute/` y `ExecuteCommand.vue` no existen, `raspberry_config.py` da 404, y
una cita entrecomillada «del código» no está en ningún fichero. **El veredicto («se rehace») aguanta
y sale reforzado; el inventario y la estimación, no.** Evidencia 66.

🔴 **Y la tercera medición explica por qué las dos primeras se contradijeron: `Atriz_web_server`
tiene TRES ramas que son códigos distintos, y ninguna auditoría dijo cuál miraba.** `master` (la que
da un `git clone`) es del 2026-02-09 y ahí `PythonCode.vue` son 2,9 KB de `<textarea>`; **`pruebas`
es del 2026-02-16 —siete días más nueva— y ahí son 11 KB con Monaco de verdad**. `compare` entre
ellas devuelve 404: no comparten ancestro.
→ **Manda `pruebas`**: es la más reciente y la que cita **toda** la documentación del proyecto
(`INFORME_AUDITORIA.md:5`, `TRASPASO.md:1103`, `CHANGELOG.md:4560`, commit `924d659`).
`git clone -b pruebas …`. **Las dos auditorías midieron bien; el defecto fue no fijar la rama, y es
del plan.** Evidencia 67.

📌 **Tercer repositorio en juego: `Bura-hub/atriz-lab`**, clonado en el PC el 2026-08-03. Next.js 15 +
React 19 + Tailwind y un backend FastAPI + Celery, de 2025-10-17. Sin autenticación, telemetría de
mentira y **cero llamadas de red en el frontend**. Aporta una cosa que el viejo no tiene: `globals.css`
con 582 líneas de tokens claro/oscuro. → **Ninguno de los tres ha hablado nunca con rosbridge.**

## Lo siguiente

**La Fase 5 está planificada y el plan está en el repositorio:**
[`00_auditoria/planes/2026-08-03-plataforma-web.md`](../00_auditoria/planes/2026-08-03-plataforma-web.md).
Se ejecuta **desde el PC de desarrollo**. Decidido: se rehace la web entera —el transporte, la
autenticación y la telemetría de la actual están las tres ausentes o fingidas—, la web sustituye al
SSH para el alumno, y el proxy de la Fase B pasa a ser el **agente de sesión** de cada robot.

📌 **Y hay una REVISIÓN del plan**, del mismo día por la tarde:
[`00_auditoria/planes/2026-08-03-plataforma-web-revision.md`](../00_auditoria/planes/2026-08-03-plataforma-web-revision.md).
Sometió la arquitectura a cuatro lentes opuestas con un escéptico cada una. **El agente de sesión
gana: 4 de 4 dijeron «sirve con cambios» y ninguna propuso otra cosa.** Pero le encontró **cinco
huecos** —no hay profesor, no hay política de desconexión, **el driver no publica su bandera de
parada**, nadie sirve el NTP, y **el alumno con `rclpy` nativo tiene más autoridad que la web**—,
**reabrió la decisión de repositorio** (recomendación: uno nuevo y privado) y amplió la F0 de 2
puntos a 20.

🔴 **No se empieza por código: se empieza por dos mediciones.**

1. **El aislamiento de clientes del AP del aula.** Si está activado rompe mDNS y la comunicación
   navegador↔robot. Necesita estar en el laboratorio. **Sin comprobar.**
2. **`send_action_goals_in_new_thread`**: si en la práctica fuera `False`, una meta larga bloquearía
   la cola de entrada de esa conexión **incluido el `publish` de `/emergency_stop`**. Y afecta **hoy**
   a `/navigate_to_pose`, que está en la lista blanca desde el 2026-08-02.

Después: **la imagen dorada y el robot 2** (Fase 6), donde se comprueban por primera vez
`provision.sh` entero y el parser de `robot_id.txt` con un ID distinto de 01.

✅ **DECIDIDO el 2026-08-03: la web es un TALLER PRESENCIAL sin SSH**, no un laboratorio remoto. El
alumno está en el aula con el robot delante. **El producto es el terminal; la teleoperación va la
última** — ninguna de las diez prácticas teleopera. Motivo: las prácticas miden con cinta y
transportador (dos piden pausas entre medidas), y «sin cámaras» impide que un alumno en casa vea si
el robot chocó. Lo remoto se reabre cuando exista una práctica diseñada para serlo; el acta
fundacional lo pedía, así que **se aplaza con su condición escrita, no se olvida**. Revisión del
plan, decisión 17.

✅ **CERRADO el 2026-08-04: el cliente de rosbridge está escrito, revisado y en un PR.**
`atriz-lab` (privado) es ya **el** repositorio de la web, y el trabajo está **fusionado en `main`**
(PR #1, merge `42e5895`); la rama `cliente-rosbridge` se borró tras comprobarlo. Cinco módulos en
`frontend/src/lib/rosbridge/` sin un solo import de React, **87 pruebas**, `tsc`/`eslint` limpios, y
un comprobador que compara la lista blanca de la web con `robot.launch.py` **del robot** y falla si
divergen. Plan y especificación en `00_auditoria/planes/`.

✅ **Y EL 2026-08-04 SE EJECUTÓ CONTRA EL ROBOT: la web movió un RVR real, 60 cm.** Con el código
de producción —`Transporte` y `Teleoperacion` tal cual están en `main`— sobre el mismo WebSocket que
usará el navegador. `arrancarBarrido()` esperó un `/scan` de verdad (1,48 s), el bucle republicó a
10 Hz contra el watchdog, `parar()` lo detuvo y el barrido se apagó solo. Evidencia 70.
Se pudo hacer desde Node **porque el núcleo no importa React ni nada del navegador**, que fue una
decisión del primer día.
→ ⏳ **La tarea 9 NO está cerrada:** falta la medida con **CINTA** y el control por SSH. 59,7 cm es
  odometría comparándose consigo misma. Y falta publicar la **parada de emergencia con el robot en
  marcha** mirando el log del driver — ha fallado **cuatro veces** en silencio.

✅ **Los siete hallazgos del cliente, cerrados el 2026-08-04.** 87 → **97 pruebas**. El más
instructivo: `confirmaEfecto()` prometía un efecto físico que este proyecto midió que **no ocurre**
—`success=true` significa «la corrutina del SDK no lanzó», y `undercarriage_white` lo devuelve **sin
encender el LED**—. El tipo pasa a `'NINGUNA' | 'SOLO_QUE_NO_LANZO'`, **sin ningún miembro que diga
«confirma»**: hoy es estructuralmente imposible que la interfaz prometa un efecto.

✅ **Y el 2026-08-04 se diseñó lo que faltaba: LA ESTRUCTURA DE LA APLICACIÓN.**
[`00_auditoria/planes/2026-08-04-estructura-app-web.md`](../00_auditoria/planes/2026-08-04-estructura-app-web.md).
La capa de datos existía y estaba probada; **la aplicación nunca se había diseñado**. Rutas,
ficheros, modelo de conexión, la vista del profesor, el terminal, los estados de la interfaz y el
orden de construcción.
→ 🔴 **La aplicación tiene DOS MITADES y el producto está en la bloqueada.** Todo lo que va por
  rosbridge es construible hoy; **el terminal** depende del agente de sesión, que depende de la
  **F0** — la medición del AP del aula, que necesita el aula.
→ 🔴 **Y una medida decide la vista del profesor: `throttle_rate` NO limita por cliente.**
  `subscribe.py:225` hace `min(f("throttle_rate"))`: **gana el más rápido, para todos**. El muro se
  suscribe solo a `/battery_state` y `/motor_status` — **7,7 kB/s los 16**. Con `/odom` serían
  1,7 Mbit/s y con `/scan` **10,3**.
→ ✅ **Las tres señales YA EXISTEN: `feat/estado-robot` fusionada en `ros2` el 2026-08-04**
  (`65ad124..2fdcf6c`) y **probada en rvr-01**. `/estado_robot` a **1,000 Hz exacto**, con `latido`,
  `parada_emergencia`, `rvr_responde`, `antiguedad_muestra_s`, `antiguedad_odom_s` y
  `reanudaciones_fallidas`. Compilada con el borrado obligatorio de `build/` e `install/`.
  **Y lo que había que comprobar no era el topic nuevo:** `/odom` **16,53 Hz** e `/imu` **16,68**
  siguen intactos tras 225 líneas nuevas en el driver, con 0 errores en 5 min.
  → ⏳ **NO VERIFICADO lo que importa:** está probado que **no estorba**, no que **sirva**. Ninguno
    de los campos se ha visto en su estado de fallo — `rvr_responde` nunca ha estado en `false`,
    `reanudaciones_fallidas` vale 0, y `parada_emergencia` nunca ha pasado a `true`. Los campos que
    justifican el mensaje son justo los que solo aparecen cuando algo se rompe.
  → 🔴 **Y esto pone el CI de `atriz-lab` en rojo hasta que la web se ponga al día:** `/estado_robot`
    entró en la lista blanca del robot, así que `comprobar_contrato.mjs` sale con **código 1**
    (`solo en el ROBOT: /estado_robot`). Se cierra añadiéndolo a `TOPICS_LECTURA` y su tipo
    `atriz_rvr_msgs/msg/EstadoRobot` a `TIPOS`. Es correcto que falle: **gana el robot**. 👤 PC.

✅ **Y LA APLICACIÓN ESTÁ CONSTRUIDA Y SE PUEDE ABRIR** (2026-08-04, madrugada). Cinco rutas, sus
componentes, y **250 pruebas** (eran 97 al empezar la noche):

```
npm --prefix atriz-lab/frontend run dev      ->  http://localhost:3000
/                       la portada: los 16 robots, el muro, y lo que NO funciona
/flota                  el muro del profesor, solo con topics baratos
/robot/[id]/diagnostico ritmos, antigüedades, estado del enlace   <- la que mide
/robot/[id]/telemetria  batería en VOLTIOS, motores con su antigüedad, LEDs
/robot/[id]/conducir    teleoperación y el botón de parada
/robot/[id]             el TERMINAL — bloqueado, y lo dice en pantalla
```

🔴 **La regla de «lo que la interfaz no puede decir» ya no es un párrafo: es una prueba.**
`lib/interfaz/lenguaje.ts` abre los ficheros de `componentes/` y `app/` y **falla** si aparece
«parada activa», «led encendido», «robot averiado», «color cambiado» o «latencia». Comprobado
rompiéndolo. Es el primer sitio donde una lección de `CLAUDE.md` corre sola.

✅ **Verificado por el EFECTO, no por que compile:** con `npm run dev`, Edge headless por CDP y un
**rosbridge falso escrito a mano**. En el cable: **0 subscribes con `qos`**, **0 publicaciones en
`/cmd_vel`**, twists a ~10 Hz en `/cmd_vel_raw` con el cero al soltar, y cambiar de robot cierra un
socket y abre otro. En pantalla: `SIN_DATOS` sale **ámbar** con las tres causas sin elegir, y
`antiguedad_atasco_s = -1` sale como **«no se sabe»**.

🔴 **Y la portada era una maqueta que decía «Sistema operacional».** `/` renderizaba 1134 líneas con
datos inventados y cero conexiones: la peor familia de fallos de este proyecto, en la primera
pantalla. Sustituida por una que dice lo que **no** funciona. Las maquetas no se han borrado —duda
A3—, pero ya no las importa nadie.

⏳ **Lo que falta y por qué:** el **terminal** (F0), la **vista del LIDAR** (`/scan` sin modelar), y
**`FRENANDO`** — que sale de `/collision_monitor_state`, cuyo `action_type` no está caracterizado y
cuyo caudal no está medido: en vez de inventarlo, **el hueco se declara en pantalla**.

📋 **Todas las dudas abiertas, juntas y con recomendación:**
[`00_auditoria/planes/2026-08-04-dudas-abiertas.md`](../00_auditoria/planes/2026-08-04-dudas-abiertas.md).

**Texto anterior, conservado:** 🔴 **PERO NO SE HA EJECUTADO NUNCA CONTRA UN ROBOT, ni en un navegador.** El criterio de aceptación
de la especificación —*«un robot real se teleopera desde el navegador y el desplazamiento medido con
cinta coincide con el del mismo movimiento por SSH»*— **sigue sin cumplirse**. La revisión final lo
dijo así: los defectos que se arreglaron son **«trampas armadas esperando al primer consumidor»**.
→ **Lo que falta son las tareas 8 y 9 del plan, y necesitan el robot encendido y cinta métrica.**

✅ **Y el bloqueo que tenían, resuelto el 2026-08-04: `/start_scan` no fallaba, el LIDAR estaba
muerto.** La evidencia 68 §6 dejó abierto un `result:false` y lo atribuyó al robot, con razón:
**el nodo del X2 tenía el descriptor `/dev/ttyUSB0 (deleted)`** desde que se apagó y encendió el
RVR nueve horas antes. Abre el puerto una vez al arrancar y no lo reabre; udev rehace
`/dev/ydlidar` y nadie se lo dice al proceso. Un `systemctl restart atriz-robot` lo arregla, y
medido después: `/scan` a **11,90 Hz** y `/start_scan` en **1,4-2,1 s** por WebSocket, 6 de 6.
🔴 **Que se recupere solo sigue SIN HACER** y con 16 robots va a volver: cualquier
re-enumeración del USB lo provoca. Evidencia 69, apartado 6, con las dos opciones y sin decidir.

🔴 **Y del mismo episodio salió un SEGUNDO fallo, ya cerrado: el puerto USB físico.** Al mover el
cable buscando que volviera a ser `/dev/ttyUSB0` —número que **no importa**, para eso está la
regla udev— el LIDAR quedó en otro conector, `/dev/ydlidar` desapareció y **el launch murió en
1 s sin imprimir nada**, con el único error visible apuntando al sitio equivocado. Cuatro
intentos de cable. ✅ `verificar_robot.sh` ahora lo dice en una línea. 👤 **DECIDIDO: puerto fijo
en los 16**, y eso hace la **foto del conector en `FLOTA.md` obligatoria — sigue sin existir.**

🔴🔴 **Y la causa raíz no era ninguna de las dos: `set -e` + `(( t++ ))` en `atriz-robot.sh`.**
Un post-incremento devuelve el valor **anterior**; con `t=0` eso es falso → estado 1 → `set -e`
mataba el script en la primera vuelta del bucle. Así que **la espera de 60 s para que udev cree
los enlaces nunca ocurrió** y el mensaje `🔴 /dev/ydlidar no apareció` era **inalcanzable**: la
salvaguarda estaba escrita contra el fallo que acabó causando. Arreglado y verificado por efecto
(espera de verdad y escribe). Y el diagnóstico del puerto se movió **al arranque**, porque un
mensaje que solo vive en el verificador no sirve cuando el modo de fallo es que nadie lo ejecuta.

👤 **PENDIENTE Y BLOQUEA: reinstalar el script corregido.** `/usr/local/bin/atriz-robot.sh`
diverge del repositorio hasta que se ejecute `sudo bash scripts/fase_7_systemd.sh --id 01`. Hasta
entonces el robot arranca con la versión rota — funciona, pero sin espera ni diagnóstico.

📝 **Y una advertencia sobre el plan, marcada en su cabecera en rojo: YA SE EJECUTÓ y sus bloques de
código reproducirían defectos ya corregidos.** La fuente de verdad es el repositorio. El plan
acumuló **veinte defectos propios** y ninguno se encontró releyéndolo: los veinte salieron de
ejecutar algo. El más instructivo — una revisión comparó `contrato.ts` carácter a carácter contra el
plan y dio **✅ perfecto** mientras el tipo del mensaje estaba mal, **porque el plan también lo
estaba**. Transcribir fielmente una fuente equivocada produce un verde impecable.

📌 **Inventario de repositorios, nuevo:**
[`03_operacion/REPOSITORIOS.md`](REPOSITORIOS.md). Son **nueve** entre dos dueños, y existe porque la
confusión entre ellos ya costó tiempo real. Hecho el 2026-08-04: `ros_sphero_rvr` (ROS 1)
**archivado**, y el paraguas público `ATRIZ` **corregido** — sus dos submódulos apuntaban al sistema
muerto, así que un `git clone --recursive` repartía ROS 1 y la web abandonada. ✅ Y archivado
`Atriz_web_server` **en cuanto se rote la `SECRET_KEY`**, no antes.

## Lo que bloquea, y de quién es

| | |
|---|---|
| ✅ ~~**Rotar la PSK del WiFi y la contraseña de `sphero`**~~ | **HECHO el 2026-08-04.** Era el bloqueo más antiguo del proyecto. Los secretos siguen en el historial de los repositorios públicos, pero **ya no valen**: rotar es lo único que cierra una exposición, y borrar ramas o archivar repositorios **no cerró nada** — los dos casos medidos |
| ✅ ~~**DOS credenciales NUEVAS de `Atriz_web_server`**~~ | **HECHO el 2026-08-04.** La `SECRET_KEY` de los JWT estaba en las **tres** ramas y la de PostgreSQL en un `.env` commiteado en `master`. Rotadas, y el repositorio **archivado después** — en ese orden, porque archivar deja el repo en solo lectura y **no cierra ninguna exposición**. [`REPOSITORIOS.md`](REPOSITORIOS.md) |
| **`red.txt` en 755** | 👤 tuyo. La PSK es legible por cualquier usuario; `chmod` no sirve, va `fmask=0177` en `/etc/fstab` |
| **El mapa del aula** | 👤 tuyo, en el laboratorio. Bloquea la tarea 4 del plan de navegación |
| **`~/.ssh/authorized_keys` vacío** | 👤 tuyo, desde el PC |
| **La FOTO del conector USB del LIDAR** | 👤 tuyo, y **obligatoria** desde que se decidió puerto fijo en los 16 (2026-08-04). Es lo único que le dirá a quien monte el robot 7 dónde va el cable. Con el cable en el conector equivocado, el launch **muere en 1 s sin imprimir nada**. Sigue sin existir |
| 🔴 **Que el LIDAR se recupere solo tras re-enumerar el USB** | Hoy se arregla con `systemctl restart atriz-robot`, y **cualquier apagado del RVR con la Pi viva lo provoca** — o sea, algo cotidiano. Con 16 robots volverá. Evidencia 69, apartado 6: dos opciones y sin decidir |
| ⏳ **El aula, entero: `05-atriz-lab.network` nunca ha casado con nada** | El fichero está bien escrito y **nada más**. Si el SSID real difiere en un carácter, el robot cae al netplan genérico **sin dirección estática**; si `10.14.0.1` no es la puerta buena, habrá dirección pero sin salida ni NTP — y esta Pi no tiene RTC |
| ⏳ **Que el direccionamiento sobreviva a un ARRANQUE EN FRÍO** | Todo se aplicó en caliente con `netplan try`. Nadie ha comprobado que los `.network` se apliquen desde cero ni que el emparejamiento por SSID ocurra en el arranque. **Es exactamente lo que hará el robot 7** |

## Marcado NO VERIFICADO

- **`provision.sh` no se ha recorrido entero en ningún robot.** El SDK de rvr-01 se compiló a mano
  (md5 idéntico al de `src_externos`, y `~/YDLidar-SDK` no existe).
- **El parser de `robot_id.txt`** no se puede probar con `ROBOT_ID=01`: los dos parsers coinciden por
  casualidad.
- **El encargo por SSH desde el PC** — probado solo dentro de la Pi.
- **`atriz-nav.service`** nunca se ha arrancado bajo systemd: exige un mapa.
- **Las diez prácticas** de `estudiantes/` no se han ejecutado con el robot moviéndose.

## Suelto, sin dueño claro

- **`/ambient_light` no publica** (manual, cap. 18.4b). Intermitente: publicaba a las 14:30 del
  2026-08-03 y no a las 15:41, con `/odom` a 16,7 Hz y `/encoders` a 16,3 Hz sanos.
