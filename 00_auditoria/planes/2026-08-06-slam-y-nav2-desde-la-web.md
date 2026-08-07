# SLAM y Nav2 bajo demanda desde la web — diseño

**Fecha:** 2026-08-06 (noche) · **Decisión del usuario:** *«Ambas deberían poderse habilitar desde
la web según la necesidad del usuario. Apruebo que estén disponibles.»*

**Método:** cuatro agentes en paralelo con lentes distintas —seguridad, mecanismo systemd,
integración ROS y un escéptico— y **las dos contradicciones entre ellos zanjadas midiendo**, no
eligiendo. Lo que sigue distingue en todo momento **medido** de **razonado**.

**Lo que NO cambia:** ninguna arranca sola al encender. El estado por defecto sigue siendo apagado
(decisión del 2026-08-03, `03_operacion/ARRANQUE_NAVEGACION.md`). Se añade **el mando**, no el
arranque automático.

---

## 0 · Las tres cosas que este análisis corrigió, y una es mía

### 0.1 · 🔴 «Root arranca un proceso» es INEXACTO — y bloqueó la decisión un día

El panel del 2026-08-06 (mañana) rechazó el mecanismo con esto:

> *«Convierte "cualquiera en la red llama a un servicio" en "cualquiera en la red hace que **root**
> arranque un proceso".»*

**Medido sobre la unidad ya resuelta por systemd, no sobre el fichero:**

```
$ systemctl show atriz-nav -p User -p Group -p AmbientCapabilities
User=sphero · Group=sphero · AmbientCapabilities=(vacío)

$ grep -nE "Exec(StartPre|Start|StopPost)=" /etc/systemd/system/atriz-nav.service
54:ExecStartPre=/usr/local/bin/atriz-escaneo on
56:ExecStart=/usr/local/bin/atriz-nav.sh
64:ExecStopPost=-/usr/local/bin/atriz-escaneo off
```

**Ninguno lleva `+`, `!` ni `!!`.** Sin esos prefijos, `User=` se aplica a los tres. Lo que ocurre
es que systemd —que sí es root— arranca una unidad cuyos **tres procesos corren como `sphero` sin
capacidades**. No hay escalada de privilegio en ningún punto.

Y el complemento, también medido: `sphero` **no puede escribir** lo que se ejecuta —
`/etc/systemd/system/`, `/usr/local/bin/` y los tres ficheros son `root:root`. Más: **`sphero` ya
está en el grupo `sudo`**, así que una regla polkit no le da nada nuevo; **le quita la contraseña**.

📌 **Dos de los cuatro agentes repitieron la frase de «root» sin comprobarla.** Es una creencia
heredada que sobrevivió a tres documentos, exactamente como la del sensor de color.

### 0.2 · 🔴 `/release_emergency_stop` NO está en `g_srv` — y esto lo escribí yo

```
rvr_driver_node.py:647-649   create_service(EmptySrv, 'release_emergency_stop', …,
                                            callback_group=g_cmd)
rvr_driver_node.py:658       g_srv = MutuallyExclusiveCallbackGroup()   ← se define DESPUÉS
```

La frase *«un callback largo bloquea `/release_emergency_stop`»* —que está en
`2026-08-06-arrancar-desde-la-web.md`, en `ESTADO_ACTUAL.md` y que repetí de viva voz— **es falsa**.
El límite es real: bloquea **los otros 18 servicios**. Pero la parada de emergencia vive en `g_cmd`,
con `cmd_vel`.

⚠️ Sigue siendo razón suficiente para no meter esto en el driver, **pero por el motivo correcto**.

### 0.3 · 🔴 LA CUARTA TRAMPA, y no estaba en ninguna lista: **el reloj**

La encontró el escéptico. **Verificada en el arranque actual:**

```
$ timedatectl              → RTC time: n/a
$ ls /dev/rtc*             → No such file or directory
$ ls /sys/class/rtc/       → (0 entradas)
```

**Esta Pi no tiene reloj de tiempo real.** Y esto es lo que pasó en el arranque de ahora mismo —el
posterior al corte de alimentación del RVR del 2026-08-06:

```
Jun 05 10:37:49  kernel: Booting Linux…                          ← reloj falso, DOS MESES atrás
Aug 06 21:42:41  timesyncd: System clock … restored from recorded timestamp
Aug 06 21:42:46  [atriz-robot] arrancando robot.launch.py
Aug 06 23:10:33  timesyncd: Initial clock synchronization        ← salto de +1 h 27 m 47 s
Aug 06 23:10:34  [launch]: All log files can be found below…
```

**El salto cayó DENTRO del arranque de `robot.launch.py`**, entre dos líneas separadas por ~1,5 s
reales. Y no hay nada que lo espere:

```
$ systemctl is-enabled systemd-time-wait-sync   → disabled
$ systemctl show atriz-robot -p After           → network-online.target   (sin time-sync.target)
```

**Por qué esto tumba el diseño si no se arregla:** ROS 2 sella con el reloj del sistema. Un salto
adelante de 5 272 s **caduca el búfer TF entero de golpe** — que es el estado exacto del fallo ya
medido: `slam_toolbox` vivo y mudo, mapa idéntico celda a celda tras mover el robot 80 cm. Esta vez
el driver se salvó por ~1 s de margen.

Y en el aula es peor: el servidor NTP es `ntp.ubuntu.com`, **hace falta internet**, y
`05-atriz-lab.network` no ha casado nunca con nada. Sin NTP, **16 robots con 16 relojes distintos
separados por horas**.

⚠️ **NO VERIFICADO**: que el salto rompa TF *de verdad*. Es deducción del modelo de tiempo de
ROS 2, no una medida. Se cierra provocándolo (ver §5).

---

## 1 · El diseño, en el que los cuatro convergen

### 1.1 · Un nodo supervisor aparte, NO el driver

**`atriz_supervisor`**, en el mismo paquete, con su propio ejecutor, lanzado por
`robot.launch.py` bajo `atriz-robot.service`.

Tres razones, en orden de peso:

1. **Aísla el privilegio.** La regla polkit se acota a **un ejecutable** y a cuatro unidades.
   Quitarle ese permiso mañana es parar una unidad, no reescribir el driver.
2. **No comparte `g_srv`** con los 18 servicios que hablan al RVR por el puerto serie. Un RVR
   dormido no puede dejar el botón de SLAM esperando 5 s por algo ajeno.
3. 🔴 **El estado de SLAM no puede vivir en el ciclo de vida del driver.** Si el driver se
   reinicia, `slam_toolbox` sobrevive —vivo y mudo— y una señal alojada en el driver se pondría a
   cero justo en el caso que existe para detectar.

📝 **Precedente en el propio repositorio:** `cancelar_nav2.py` es exactamente esta figura —nodo
aparte, mismo paquete, entry point propio— y su cabecera lleva escrito el argumento: *«el driver
tiene que funcionar sin Nav2»*.

**Si el supervisor muere:** SLAM y Nav2 **siguen corriendo** — son unidades de systemd, no hijos
suyos. Se pierden el botón y la señal, y la web lo ve porque **su latido deja de avanzar**.

### 1.2 · Servicio para PEDIR, topic para SABER

| | Elegido | Por qué |
|---|---|---|
| **Pedir** | 2 × `std_srvs/SetBool`: `/pedir_slam`, `/pedir_nav` | Tipo que la web **ya** usa (`enable_color`). Cero tipos nuevos |
| **Saber** | topic `/estado_navegacion` a 1 Hz | El estado tiene que sobrevivir a cerrar la pestaña |

**Por qué NO una acción**, aunque parezca lo natural para algo largo:

- 🔴 **`SendActionGoal` no implementa `finish()`** (`capability.py:87` es un `pass`). Cerrar la
  pestaña no cancela la meta, pero el cliente **pierde feedback y resultado para siempre**:
  rosbridge no reexpone goals entre conexiones. El caso real es *«arranco SLAM, cierro el
  portátil, vuelvo a los 20 minutos»*. Con acción vuelve a un estado que no puede consultar.
- 🔴 **`comprobar_contrato.mjs` NO compara acciones** — solo `LEER`, `ESCRIBIR` y `SERVICIOS`. Todo
  lo que entre por acciones entra **sin red de seguridad**.

**Por qué NO un topic solo:** rosbridge **deniega `publish` en silencio**. Se pasaría de «el botón
dice que falló y el robot lo hizo» a «el botón no dice nada nunca».

**El nombre es deliberado: `pedir`, no `arrancar`.** El `success=true` significa **petición
aceptada**, jamás «arrancado». Quien pinta el botón es el topic.

**Cómo cabe en los 5 s** (plazo de `_pedir`, de rosbridge y del cliente web, los tres a 5,0 s):

1. Rechazos deterministas y baratos, con `message` accionable: sin mapa · unidad en `failed`
   («hace falta `reset-failed` desde el robot») · el otro ya corriendo.
2. `systemctl start|stop --no-block` — encola y vuelve.
3. `success=true` + *«petición ACEPTADA, no arrancado: mira `/estado_navegacion`»*.

📊 **Medido:** `systemctl show atriz-nav -p ActiveState` tarda **0,05-0,06 s de reloj, 0,01 s de
CPU**. Dos órdenes de magnitud por debajo del plazo.

### 1.3 · Los testigos: qué prueba que FUNCIONA, no que está `active`

**`systemctl is-active` queda descartado como fuente de verdad.** Solo se usa para distinguir
«arrancando» de «arrancado».

| | Testigo | Por qué ese, y no el obvio |
|---|---|---|
| **SLAM vive** | `ps -eo comm` = `async_slam_tool` | ✅ **VERIFICADO** por un agente copiando `/bin/sleep` con ese nombre. `ros2 node list` no vale: conserva nodos muertos |
| **SLAM procesa** | crecimiento del grafo (`/slam_toolbox/graph_visualization`) | 🔴 **`/map` NO vale**: 0,2 Hz, **latcheado**, y `map_server` de AMCL publica **el mismo topic**. Un umbral de 1 s pintaría «apagado» el 96 % del tiempo con SLAM sano |
| | ⚠️ y solo exigible si el robot se **desplazó** ≥ 0,30 m | `minimum_travel_distance: 0.3`. **Girar no cuenta** (medido: 4,5 vueltas → 0 celdas). Sin esta condición, un robot quieto y sano se pintaría «mudo» |
| **Nav2 acepta** | `ActionClient.server_is_ready()` **en proceso** + ciclo de vida de `bt_navigator` | El action server existe desde `on_configure`: **`configured` ≠ `active`**. Y `ros2 action list` no es autoritativo — el descubrimiento DDS ya omitió 1 de 18 servicios |
| **Los dos: ¿ciego?** | llega `/scan` | Sin `/scan` el `collision_monitor` bloquea: **0,0 cm contra 9,9** con el mismo comando. Nav2 diría `active` todo el rato y **el robot parece averiado** |

🔴 **`map → odom` NO vale como testigo de SLAM**: sale de un hilo a ~50 Hz que **republica el último
valor congelado**. Miente exactamente en el caso «vivo y mudo».

### 1.4 · Seis estados, nunca un booleano

`apagado` · `arrancando` · `funcionando` · **`ciego`** · **`mudo`** · `fallo`

Los dos del medio son los que `is-active` esconde, y son los que este proyecto ya ha pagado.

- **`arrancando` tiene tope**, y sale de `TimeoutStartSec`, no de un número inventado. Pasado el
  tope se va a `fallo` con motivo: **nunca un `arrancando` eterno**, que es como se disfraza un
  fallo de arranque.
- **La web pinta el estado que llega, nunca el que pidió.** Misma lección que `color_activo`.
- ⏳ **Nadie ha medido cuánto tarda Nav2 en estar listo.** Hasta que se mida, la web muestra
  **segundos transcurridos, no porcentaje**: un porcentaje inventado es una mentira con aspecto de
  dato.

### 1.5 · Que la unidad atada VUELVA — el patrón `Upholds=`

El problema conocido: `BindsTo=` propaga la **parada**, no el **reinicio**. Si el driver se
reinicia —y lo hace solo, de forma rutinaria—, la navegación se apaga y **no vuelve**.

```
atriz-slam-deseada.service   el DESEO — oneshot, RemainAfterExit, NO habilitada
        │ Upholds=            "mientras yo esté activa, mantén esa unidad arriba"
        ▼
atriz-slam.service           la EJECUCIÓN
        │ BindsTo= + After=   "si el driver se va, yo me voy" — morir visible, no mudo
        ▼
atriz-robot.service          el driver — la única habilitada
```

**Separa el deseo de la ejecución.** `BindsTo=` se queda: aquí **queremos** que SLAM muera con el
driver, porque sobrevivir es el fallo. El deseo lo vuelve a levantar **limpio**, sobre un búfer TF
nuevo.

Ninguna de las unidades nuevas se habilita → **un reinicio de la Pi no devuelve nada**, y la
decisión del 2026-08-03 queda intacta.

⚠️ **Punto de fricción que hay que documentar en voz alta:** con el deseo puesto,
`systemctl stop atriz-slam` **no funciona** — el deseo la revive en un segundo y el operador
concluirá que el sistema está roto. Por eso el punto de entrada único es `atriz-modo slam on|off`,
que comprueba el efecto igual que hace `atriz-escaneo`.

### 1.6 · Exclusión mutua sin `Conflicts=`

| | `Conflicts=` | `ExecStartPre` que se niega |
|---|---|---|
| Quien lleva 20 min mapeando | **pierde el mapa, sin una palabra** | no pierde nada |
| Qué ve el operador | nada | ocho líneas y el comando para arreglarlo |
| Quién decide | systemd, en silencio | la persona |

🔴 **Y el guardia que HOY NO EXISTE:** `localizacion.launch.py:70-93` comprueba si hay SLAM vivo
antes de arrancar AMCL — **pero `slam.launch.py` no comprueba nada**. La exclusión funciona **en un
solo sentido**. Con la web ofreciendo los dos botones, «Nav2 y luego SLAM» arranca tan contento:
**dos publicadores de `map → odom`, árbol TF partido, sin un solo error.**

→ Hace falta el guardia simétrico en `slam.launch.py`, más `atriz-exclusion` como `ExecStartPre`
de las dos unidades (falla en 0,1 s, antes de subir el X2 a 11,8 Hz).

### 1.7 · El barrido: `off-si-sobra`

`atriz-nav.service:64` hace hoy `ExecStopPost=-atriz-escaneo off`, y su comentario lo justifica:
*«se acepta porque parar la navegación es un acto explícito de operador»*.

🔴 **Esa premisa muere el día que existe el botón.** Parar la navegación pasa a ser un clic de
cualquier alumno sobre un robot compartido, y apagar `/scan` **deja al robot sin obedecer
`cmd_vel` para todos los demás**, sin error.

→ `atriz-escaneo off-si-sobra`: apaga solo si **ninguna** de las dos unidades sigue activa. El
sesgo del fallo es deliberado: si se equivoca, deja el barrido **encendido** (desgaste) en vez de
apagado (robot ciego que parece averiado). Es el mismo principio ya implementado en `atriz.py`.

### 1.8 · El permiso

```javascript
/* /etc/polkit-1/rules.d/49-atriz-unidades.rules — NO VERIFICADA */
polkit.addRule(function(action, subject) {
    if (action.id != "org.freedesktop.systemd1.manage-units") return polkit.Result.NOT_HANDLED;
    if (subject.user != "sphero")                             return polkit.Result.NOT_HANDLED;
    var u = action.lookup("unit"), v = action.lookup("verb");
    var UNIDADES = ["atriz-slam-deseada.service", "atriz-nav-deseada.service",
                    "atriz-slam.service",         "atriz-nav.service"];
    if (UNIDADES.indexOf(u) >= 0 && (v == "start" || v == "stop")) return polkit.Result.YES;
    return polkit.Result.NOT_HANDLED;
});
```

Tres propiedades, y la segunda es la que más vale:

1. **No es «root arranca un proceso»** (§0.1): es «systemd arranca una de estas cuatro, y todas
   corren como `sphero`».
2. 🔴 **`enable`/`disable` quedan FUERA a propósito.** La web puede encender y apagar; **no puede
   hacer que sobreviva a un reinicio**. La decisión del 2026-08-03 queda protegida por el sistema
   de permisos, no por un acuerdo entre personas.
3. `subject.user` en vez de `isInGroup`: un nodo ROS bajo una unidad de sistema **no tiene sesión
   de logind**, así que depender de `active`/`inactive` rompería.

**Exposición residual, dicha sin adornos:** cualquiera en la red del aula podrá encender y apagar
SLAM y Nav2 de cualquier robot. Ya puede **conducirlo** por `/cmd_vel_raw`, dispararle
`/emergency_stop` y apagarle el barrido con `/stop_scan`. **El delta es pequeño.** Lo que lo cierra
de verdad es la Fase B (rosbridge en `127.0.0.1` detrás de un proxy con JWT), no esto.

---

## 2 · 🔴 El riesgo que SÍ es nuevo, y no estaba en ningún plan

**Exponer SLAM arrastra un botón «guardar el mapa», y los tres servicios candidatos aceptan la
ruta que les dé el cliente.** Verificado leyendo los `.srv` instalados:

```
slam_toolbox/srv/SaveMap.srv            std_msgs/String name
slam_toolbox/srv/SerializePoseGraph.srv string filename
nav2_msgs/srv/SaveMap.srv               string map_url
    # Can be an absolute path to a file: file:///path/to/maps/floor1.yaml
```

Cualquiera de los tres, en una lista blanca sin autenticación, es **escritura de fichero en ruta
arbitraria como `sphero`** — y `sphero` posee `~/atriz_ws/install/`, de donde `atriz-nav.sh:31` hace
`source`, y `~/.profile`. El contenido solo es parcialmente controlable (PGM/YAML), así que
ejecutar código pide trabajo; **borrar el workspace no pide ninguno.**

**Hoy no hay ni un servicio en la lista blanca que toque el sistema de ficheros.**

📌 **DECISIÓN: ninguno de los tres entra en la lista blanca.** Guardar el mapa espera al agente de
sesión de la Fase B, donde hay identidad y se puede fijar el directorio. **Este es el punto que de
verdad protege el laboratorio**, y es más importante que todo el debate sobre polkit.

---

## 3 · Lo que BLOQUEA, en orden

| # | Qué | Estado | Por qué bloquea |
|---|---|---|---|
| **B1** | 🔴 **El reloj.** Sin RTC; salto de +1 h 27 m **dentro** del arranque; sin `time-sync.target` en ninguna unidad; `systemd-time-wait-sync` **disabled** | **MEDIDO** en este arranque | Un salto adelante caduca el búfer TF entero — el estado exacto del `slam_toolbox` vivo y mudo. Y en el aula no hay internet para NTP |
| **B2** | 🔴 **`atriz-nav.service` NUNCA se ha ejecutado bajo systemd**, desde el 2026-08-03. Y **hoy no hay mapa** (`maps/` solo tiene README) | Verificado | Se quiere extender a SLAM un mecanismo que no se ha visto correr ni una vez |
| **B3** | 🔴 **Botón de tres pulsaciones.** `Restart=on-failure` + `StartLimitBurst=3`/300 s: **un solo `start` sin mapa produce tres intentos en ~20 s** y deja la unidad latcheada. Revivirla pide `reset-failed` con privilegio | Config verificada; el latch NO VERIFICADO | Desde el navegador, «no arrancó» y «bloqueado hasta que alguien entre por SSH» son indistinguibles |
| **B4** | 🔴 **`slam.launch.py` no comprueba nada**: la exclusión es de un solo sentido, y hay TOCTOU si dos clientes piden a la vez | **Verificado leyendo los dos launch** | «Nav2 y luego SLAM» parte el árbol TF **sin un solo error** |
| **B5** | ⏳ **`Upholds=` no está verificado.** Solo que systemd 255.4 **acepta la sintaxis** | NO VERIFICADO | Es la pieza central de §1.5. Y este proyecto tiene medido que `systemd-analyze verify` calla ante un `StartLimitBurst` mal colocado: **aceptar no es hacer** |

---

## 4 · Lo que NO bloquea, y conviene decirlo

- 🟢 **Seguridad de permisos: no hay agujero.** `sphero` no puede escribir la unidad ni los
  scripts; los tres `Exec*` corren como `sphero`; y `sphero` ya puede lanzar `nav2.launch.py` a
  mano ahora mismo. **La unidad no eleva privilegios; solo cambia quién teclea.**
  ⚠️ Con una condición: **nada de comodines en sudoers** (`sphero ALL=NOPASSWD: /usr/bin/systemctl`
  es root instantáneo vía `systemctl link`). Por eso se recomienda polkit acotado.
  ⚠️ Y una guardia que hoy no existe: **si alguien cambia `User=sphero` por `User=root`**, todo el
  modelo se cae en ese instante y **ningún test lo vería**.
- 🟢 **El arreglo de `atriz.py` está implementado de verdad**, no solo escrito en un plan:
  `debe_apagar_barrido()` en `:177-189`, `_barrido_era_mio` en `:519-531`. Queda un riesgo
  residual: la propiedad se decide con **una ventana de 1,0 s** al conectar, y con
  `TimeoutStartSec=120` esa ventana no es teórica.

---

## 5 · Qué medir ANTES de escribir código

| # | Qué | Cómo | Toca el robot |
|---|---|---|---|
| **M-A** | ¿Rompe TF el salto de reloj? | Con SLAM activo: `sudo timedatectl set-ntp false` · `sudo date -s "+90 minutes"` · ¿sigue publicando el grafo? | Sí |
| **M-B** | ¿Cuánto tarda este robot en sincronizar desde el arranque? | `journalctl -b 0 \| grep -E "Initial clock synchronization\|restored from recorded"` | No |
| **M-C** | `Upholds=` y la columna ambigua de `BindsTo` | `sudo bash scripts/medir_recuperacion.sh` (M10) **ampliado con un cuarto caso** con `Upholds=`, y leyendo `ExecMainStartTimestamp` además de `is-active` | No — unidades de juguete |
| **M-D** | ¿Arranca `atriz-nav` de verdad, y en cuánto? | `sudo systemctl start atriz-nav` con un mapa cualquiera vía `ATRIZ_MAPA`; cronometrar hasta `server_is_ready()` | Sí |
| **M-E** | ¿Corta el `StartLimitBurst`? | Con el mapa ausente: `start`, `sleep 45`, `status`, `start` otra vez → ¿«repeated too quickly»? | Sí |
| **M-F** | La regla polkit | `systemctl start atriz-slam-deseada` como `sphero` **sin sudo**: ¿arranca? Y `systemctl start ssh`: ¿**sigue** pidiendo autenticación? | No |

🔴 **M-C es la ambigüedad que hay que cerrar primero.** La tabla `BindsTo`/`PartOf` en la que se
apoya todo el apartado 4 **no lleva timestamp**, y sin él la casilla «`active` tras `restart`» no
distingue *«volvió»* de *«ni se enteró»*. La guía de lectura que el propio proyecto escribió lo
dice, y la tabla registrada no la cumple.

---

## 6 · Lo que le toca a la web, cuando llegue

- `contrato.ts`: `SERVICIOS` += `/pedir_slam`, `/pedir_nav` (de 10 a **12** — ⚠️ hay un
  `toHaveLength(10)` que hay que subir). `TOPICS_LECTURA` += `/estado_navegacion` (de 13 a **14**).
- 🔴 **`confirmaEfecto()`: clasificar los dos a mano.** Olvidarlo **no da error** — clasifica solo y
  en silencio. El `success` **no** confirma el efecto; lo confirma `/estado_navegacion`, igual que
  `color_activo` confirma `enable_color`.
- **Seis estados, no un interruptor.** Botón deshabilitado mientras `arrancando`, con **segundos
  transcurridos** y sin barra de progreso.
- **Botón de PARAR tan visible como el de arrancar** — aquí pesa más que en el color: Nav2 son
  ~58 % de un núcleo saliendo de la batería del RVR.

**Rompe el contrato, y es correcto.** Precedente ya aceptado con `/estado_robot` y con
`enable_color`: **todo el lado robot en un solo commit**, y la web se alinea después.

---

## 7 · Un agujero que este diseño NO cierra

**Cualquier pestaña de la web puede llamar a `/stop_scan`** —está en la lista blanca— y dejar
ciega a la navegación de ese robot, en silencio.

Lo que este diseño aporta es **que deje de ser silencioso**: el estado `ciego` lo detecta en ~1,7 s
y la web lo pinta. Lo que **no** hace es impedirlo.

📌 Cerrarlo son dos opciones y **ninguna se decide aquí**: quitar `/stop_scan` de la lista blanca
mientras haya navegación (cambia el contrato de la web), o que el supervisor lo vuelva a encender
(mete un componente que pelea con el usuario).
