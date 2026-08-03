# Fase 5 — La plataforma web del laboratorio

> **Para quien lo ejecute:** este plan se escribió el 2026-08-03 en el robot de referencia y está
> pensado para ejecutarse **desde el PC de desarrollo**, con los dos repositorios clonados. Casi
> todo se puede hacer sin el robot delante; lo que no, va marcado.
>
> 🔴 **Empieza por la F0. Son dos mediciones, no código, y una de ellas puede tirar el diseño de
> transporte entero.** Si el AP del aula aísla clientes, no se ajusta el cliente: se replantea.
>
> 👤 **Y antes de tocar `Atriz_web_server`: rotar la credencial de `sphero`.** Sigue pública.

**Diseño y debate:** tres arquitectos con posturas contrarias; el veredicto y sus razones están en
la sección 2. Todo lo que se afirma aquí sobre el repositorio de la web se midió por la API de
GitHub el 2026-08-03, sin clonarlo.

## Contexto

La Fase 5 es lo único grande que queda. El transporte ya está verificado de extremo a extremo
—navegador → rosbridge → driver → RVR, con los faros encendiéndose y confirmado a la vista— y la
lista blanca de rosbridge está aplicada y comprobada con **efecto físico** (`raw_motors` al 30 % por
WebSocket → **0,00 cm** de desplazamiento).

**Lo que decidiste hoy:**

| | |
|---|---|
| **Alcance** | Todo: cliente + backend + **el proxy con JWT en cada robot** (Fase B) |
| **El código del alumno** | **La web sustituye al SSH**: se escribe en el navegador y corre en el robot |
| **Repositorio** | Rama nueva en `Atriz_web_server`, sin tocar el historial |
| **Sesiones y reservas** | Sin decidir |
| **Quién lo ejecuta** | **Tú, desde el Claude de tu PC**, con el plan commiteado |

**Resultado buscado:** una web que muestre datos reales, que sustituya al SSH para el alumno, y que
cierre el pendiente de seguridad que hoy bloquea la Fase 5.

---

## 1. Lo que se encontró hoy inspeccionando el repositorio de la web

No estaba clonado; se inspeccionó por la API de GitHub sin descargar los 63,7 MB.

> # 🔴 LÉASE ESTO ANTES QUE NADA: **HAY QUE FIJAR LA RAMA**
>
> Esta sección se escribió dos veces el 2026-08-03 con resultados contradictorios, y la tercera
> medición explica por qué: **`Atriz_web_server` tiene tres ramas que son códigos distintos**, y
> `compare` entre ellas devuelve 404 — no comparten ancestro.
>
> | | `master` | `pruebas` | `develop` |
> |---|---|---|---|
> | fecha | 2026-02-09 | **2026-02-16** ← la más nueva | 2026-02-10 |
> | por defecto en `git clone` | **sí** | no | no |
> | `PythonCode.vue` | **2,9 KB**, `<textarea>` + Prism | **11,0 KB**, Monaco de verdad | — |
> | `ExecuteCommand.vue` | 404 | existe | existe |
> | `raspberry_config.py` | 404 | existe | existe |
> | `/robots/execute/` | no | sí | sí |
> | «Pasos simulados» | no | sí | no |
>
> **Ninguna de las dos auditorías se equivocó al medir. Las dos midieron ramas distintas y ninguna
> lo dijo, empezando por la primera — que es de quien escribió este plan.** La corrección de la
> tarde midió `master` (lo que da un `git clone`); la mañana midió `pruebas`.
>
> **Autoridad: `pruebas`.** Es la más reciente por 7 días y es la que cita **toda** la documentación
> del proyecto: `INFORME_AUDITORIA.md:5` y `:308`, `TRASPASO.md:1103` y `CHANGELOG.md:4560`, todos
> con el commit `924d659`. Para clonarla: `git clone -b pruebas …`.
>
> ⚠️ **Lo que sigue en esta sección mezcla las dos.** Cada afirmación necesita su rama al lado. Al
> revisarlo, ese es el primer trabajo — y hasta que esté hecho, **el inventario y la estimación no
> son fiables**.
>
> ✅ **Lo que NO depende de la rama, y por tanto se sostiene entero:** que la autenticación está
> escrita y sin conectar, que la telemetría es falsa, las dos credenciales nuevas
> (`SECRET_KEY` de los JWT está en `core/security.py` en **las tres** ramas), y el veredicto: **se
> rehace**. Ese aguanta, y sale reforzado.
>
> 📝 Y la lección para el plan, que vale más que el inventario: **un repositorio sin rama fijada no
> es una referencia.** Este proyecto ya tiene documentada la trampa de auditar un clon
> desincronizado —tres hallazgos falsos— y esta es la misma con otro disfraz.

> 🔴 **CORREGIDO EL 2026-08-03 POR LA TARDE, LEYENDO LOS FICHEROS DE `master`.** Cuatro afirmaciones
> de la versión de la mañana son falsas **en esa rama** —incluida la única que declaraba un activo
> técnico rescatable— y **ciertas en `pruebas`**. Cada punto va marcado abajo. Evidencia 66.
>
> Y aparecieron **dos credenciales nuevas** en ese repositorio, que sigue **público**
> (`private=False`, `forks=0`): la de PostgreSQL en un `.env` **commiteado** y duplicada en
> `core/config.py`, y la `SECRET_KEY` de firma de los JWT, un literal de plantilla en
> `core/security.py`. 👤 **Rotar antes de tocar el repositorio.**
>
> 📝 **La causa es una trampa que este proyecto ya tiene documentada dos veces:** un `grep` de una
> cadena suelta encuentra el ajuste **y lo que solo habla del ajuste**. Aquí cruzó una dependencia
> declarada-y-nunca-importada con una `font-family` de CSS.

### 🔴 La autenticación está escrita y no se conectó a nada

`app/dependencies.py` tiene un `get_current_user` correcto: `OAuth2PasswordBearer`, `jwt.decode` con
`SECRET_KEY` y `ALGORITHM`, su `credentials_exception`. Alguien lo escribió bien.

**Y no lo usa ningún endpoint.** Referencias a `get_current_user` o `dependencies`:

```
robots.py  0      files.py        0
scripts.py 0      experiments.py  0
```

En `main.py` los **seis** `include_router(...)` van **sin `dependencies=`**. Hay una `LoginPage.vue`,
se emite un JWT, existe la función que lo valida, **y nadie la llama**.

✅ **VERIFICADO EN LAS TRES RAMAS, así que esto NO depende de la rama** — es el hallazgo más sólido
de toda la sección. Medido: seis routers sin `dependencies=` en `pruebas` y en `develop` (los del
plan), cinco en `master`, y `get_current_user` importado y nunca llamado en las tres.

✅ **Y `POST /api/robots/execute/` TAMBIÉN EXISTE, en `pruebas` y en `develop`:**

```python
@router.post("/robots/execute/")     # robots.py en `pruebas` (4337 B) y `develop` (3543 B)
async def execute_command_on_robot(robot_ip: str = Form(...), command: str = Form(...)):
```

Un `command` arbitrario por formulario, sin autenticación: **el plan tenía razón**. La retractación
de la tarde midió `master` —donde `robots.py` son 667 B con dos rutas CRUD— y no lo dijo.

🆕 **Y hay dos endpoints más que ni el plan ni la corrección mencionaron**, en `pruebas` y `develop`:
`POST /robots/stop/` y `POST /robots/emergency-stop/`, los dos con `robot_ip` por formulario y sin
autenticación. **Una parada de emergencia sin autenticar es también una parada que cualquiera puede
NO dejar funcionar**; entra en el inventario de la Fase B.

**Y en `master` el agujero equivalente está en otro sitio y merece leerse igual, porque es el diseño
que alguien retomaría:**

```python
@router.post("/scripts/upload/")                          # app/api/scripts.py
async def upload_new_script(file: UploadFile = File(...),  robot_ip: str = Form(...)):
```

Sin autenticación, recibe **un programa Python entero** y lo ejecuta en el robot. Y `ros_bridge.py`
añade **tres defectos que este plan no vio**:

| | |
|---|---|
| **Inyección de argumentos** | `robot_ip` llega del formulario sin validar y va a `["scp", …, f"{robot_ip}:/tmp/…"]` y `["ssh", robot_ip, …]`. No es inyección de shell (usa listas), es peor de lo que parece igual: un valor que empiece por `-o` lo interpretan scp/ssh como **opción**, y `-oProxyCommand=…` ejecuta código **en el servidor** |
| **Ruta fija `/tmp/user_script.py`** | en las **dos** máquinas: dos alumnos a la vez se pisan el fichero. Y es la trampa `fs.protected_regular=2` que ya costó un netplan borrado |
| **`rosrun`** | ROS 1. No existe en este sistema |

📝 Y el detalle que lo resume: el comentario que encabeza los cinco routers en `main.py` dice
literalmente **«# Rutas que pueden ser públicas»**, y `scripts.router` está debajo.

**Enunciado original, que resulta ser CIERTO en `pruebas` y `develop`:** → **`POST
/api/robots/execute/`** acepta un `command` arbitrario y lo ejecuta por SSH en el robot indicado,
**sin autenticación efectiva**.

📝 Corrige el plan que se traía: «portar el login JWT» daba por hecho un sistema funcionando. Lo que
hay son **piezas sueltas sin conectar**, que es un estado más engañoso: parece completo y no protege.

⚠️ `app/ros_bridge.py` **no tiene nada que ver con rosbridge**: 1 KB de `subprocess` y
`send_code_to_ros(script_path, robot_ip, user)`. El nombre engaña.

### La Fase C no parte de cero, y el intento previo era la postura C

✅ **RAMA FIJADA. EL TEXTO ORIGINAL DE ESTA SUBSECCIÓN VALE: en `pruebas` SÍ HAY MONACO.** Medido
el 2026-08-03 por la tarde: `PythonCode.vue` son **10913 bytes** e **importa el editor de verdad**.
Los «11 KB con Monaco» del plan eran correctos, y `ExecuteCommand.vue` (**5598 B**) también existe.
→ **La Fase C NO parte de cero.**

⚠️ **En `master` —lo que da un `git clone` sin argumentos— es otro código:** 2895 bytes, un
`<textarea>` con Prism.js, `ExecuteCommand.vue` da 404, y la única aparición de «Monaco» en el
fichero es una línea de CSS —

```css
font-family: "Fira Code", "Consolas", "Monaco", "Ubuntu Mono", monospace !important;
```

— la **tipografía de macOS**, con `monaco-editor ^0.51.0` declarado en `package.json` y sin importar.
La frase «Pasos simulados» tampoco está **en `master`** (0 coincidencias de
`simulad|simulat|desarrollo.tex`), y sí en `pruebas`.

🔴 **Retractación de la retractación, y la lección es de método, no de dato:** la corrección de la
tarde midió `master` sin decirlo, y de ahí salió un «RETRACTADO ENTERO» que era falso. **Corregir un
error generó otro** — van tres veces en este proyecto. La causa es la misma las tres: **una
corrección es una afirmación, y necesita fijar sus condiciones igual que lo que corrige.** Aquí la
condición era la rama, y el dato que lo habría evitado (`default_branch=master`) estaba impreso en la
propia salida de la verificación.

📝 **Lo que sí sobrevive de la corrección, porque no depende de la rama:** que el flujo de subida no
sube nada. En `master`, `uploadScript()` abre un selector, lee el `.py` con `FileReader` y lo vuelca
en el textarea, **sin una sola llamada HTTP**. En `pruebas` está por recomprobar. ⏳ NO VERIFICADO.

**Texto original, que resulta ser el bueno para `pruebas`:** *«Ya existe `PythonCode.vue` (11 KB) con
Monaco de verdad (`monaco-editor ^0.51.0`) […] los nombres que el CHANGELOG citaba eran reales:
`ExecuteCommand.vue`, `BatterySensorData.vue`, `RobotDashboard.vue` (39,6 KB), `VideoStream.vue`.»*

### ¿Hay algo rescatable?

**Sirve:** ~~Monaco (integrado de verdad)~~ **← falso, ver arriba**. Queda: `app/dependencies.py`
entero (el `get_current_user` está bien escrito y solo hay que cablearlo), `core/security.py` salvo
su clave, el interceptor de axios que inyecta el `Bearer`, y el diseño visual como referencia.

🆕 **Y hay un TERCER repositorio que este plan no conocía: `Bura-hub/atriz-lab`** (Next.js 15 +
React 19 + TypeScript + Tailwind 3.4, FastAPI + Celery, 5 commits del 2025-10-17). No tiene
autenticación (`jwt`/`oauth` → 0 ficheros), su telemetría son constantes literales y **su frontend
no hace ni una llamada de red**. Lo que sí aporta y no está en el viejo: **`globals.css`, 582 líneas
de tokens claro/oscuro mapeados en `tailwind.config.ts`** con `rgb(var(--x) / <alpha-value>)`.

🔴 **El hecho que unifica a los tres: NINGUNO ha hablado jamás con rosbridge.** Ni una línea de
cliente. El único camino web↔robot verificado del proyecto es `03_operacion/probar_conexion_web.html`,
escrito a mano. → **La elección de repositorio pesa menos de lo que parecía**, porque el trabajo
central no está hecho en ninguno.

**Muere:** el transporte (SSH bloqueante, hasta 64 s con 16 robots), la autenticación (escrita y sin
conectar), la telemetría (**`Math.random()`** con retardos para parecer real), el flujo de subida
(**simulado**), `ExecuteCommand.vue` + `/robots/execute/` (✅ **los dos existen en `pruebas`**, más
`/robots/stop/` y `/robots/emergency-stop/`, también sin autenticar), `VideoStream.vue` (no hay
cámaras), y los artefactos commiteados.

⚠️ **Las cifras de tamaño que siguen son de `master` y hay que remedirlas en `pruebas`:** árbol de
6977 entradas, de las que `swarm_lab_env/` son 5578, `build/` 1175 y `devel/` 93 — el **98,1 %**.
`node_modules/` **no está commiteado ahí**: 0 entradas. Y los «63,7 MB» son el `size` de la API de
GitHub, o sea el repositorio **comprimido**; descomprimido son ~138 MB — las dos cifras son
correctas midiendo cosas distintas. ⏳ **NO VERIFICADO en `pruebas`.**

🔴 **Las tres piezas centrales —transporte, autenticación y telemetría— están las tres ausentes o
fingidas.** Lo que queda es «usar Vue 3 + Tailwind + Monaco», que es una decisión, no código.
**Se rehace**, y ahora apoyado en medidas.

✅ **`app/core/raspberry_config.py` EXISTE en `pruebas` y en `develop`** (413 B), y da **404 en
`master`**. El enunciado original era correcto para la rama que manda; la retractación de la tarde
medía `master` y decía «no ha existido nunca», que era una afirmación sobre el repositorio entero.

🔐 **Y las credenciales, ya con la rama al lado, que es lo que faltaba:**

| | `master` | `pruebas` | `develop` |
|---|---|---|---|
| `.env` commiteado (PostgreSQL) | **sí** | 404 | 404 |
| `core/config.py` con la misma credencial | **sí** | por remedir | por remedir |
| **`core/security.py` con la `SECRET_KEY`** | **sí** | **sí** | **sí** |

→ **La que importa es la `SECRET_KEY`, y no depende de la rama: está en las tres.** Con ella
cualquiera **forja un token válido**, así que cablear `get_current_user` no serviría de nada hasta
cambiarla. La de PostgreSQL apunta a `localhost`, es de desarrollo y es **solo de `master`**:
limpieza, no puerta abierta. 👤 **Rotar antes de tocar el repositorio.** Evidencias 66 y 67.
📝 Dato para tu decisión sobre el historial, sin cambiarla: el repositorio tiene **0 forks**, así que
purgar sería más efectivo de lo que el proyecto asumía.

---

## 2. El debate: cómo llega y se ejecuta el código del alumno

Tres arquitectos con posturas contrarias. **Gana A**, y las razones están verificadas en código.

### B pierde, pero **corrigió el enunciado** y su crítica se queda

Se le planteó como «un servicio ROS», y su defensa fue que debía ser **una acción**, con razón:

| Hecho verificado por B | |
|---|---|
| `send_action_goal.py:171-207` | Una acción **sí tiene acuse en las dos direcciones**: `_success` manda `action_result{result:true}` y `_failure` manda `action_result{result:false, values:str(exc)}`. Un `publish` no tiene nada de esto |
| `actions.py:193-195` | Si el servidor de acción no corre, el cliente recibe literalmente `"No action server available"` — sabe distinguir «el robot está pero el ejecutor no» |
| El feedback **no pasa por `topics_sub_glob`** | Una acción no amplía la superficie de topics ni un milímetro |

**Pero pierde por cuatro cosas, tres verificadas en código:**

| | |
|---|---|
| `rvr_driver_node.py:530` + `:551` | `g_srv = MutuallyExclusiveCallbackGroup()` asignado a **los 18 servicios** en un bucle: un callback largo **bloquea `/release_emergency_stop`** |
| `call_service.py:61` · `:149` | timeout de 5 s y `# TODO: fragmentation` — si fuera servicio, muerto |
| 🔴 **`SendActionGoal` no implementa `finish()`** | **Cerrar la pestaña NO cancela la meta**: el programa sigue corriendo y el robot moviéndose, y ya no lo ve nadie |
| 🔴 **`04_giro_preciso.py` tiene tres `input()`** | Una acción es petición→respuesta con feedback **de ida**. Sin stdin bidireccional, dos prácticas de diez están muertas. **Lo concede B misma**: *«si el curso necesita `input()`, gana A»* |

Y lo que lo cierra: **`robot.color()` llama a `/get_rgbc_sensor_values`, que no está en la lista
blanca.** Cualquier diseño que ejecute la lógica del alumno desde el navegador tiene que ensancharla.

### 🔴 El hallazgo de B que importa **gane quien gane**

`send_action_goals_in_new_thread` vale `False` por defecto en la clase (`send_action_goal.py:65`,
con el comentario *«actions block and must be processed sequentially»*) y `True` en el nodo
(`rosbridge_websocket.py:102`). Hay **una sola cola de entrada por conexión**
(`websocket_handler.py:85-124`).

**Si en la práctica fuera `False`, una meta larga bloquearía la entrada de esa conexión — incluido el
`publish` de `/emergency_stop`.** Y esto **ya afecta hoy** a `/navigate_to_pose`, que está en la
lista blanca desde el 2026-08-02.

→ **Hay que medirlo, con la meta en curso y cinta métrica, aunque la web no se llegue a construir.**

### La crítica de B contra A, que hay que respetar en el diseño

1. **Convierte al guardián en intérprete.** Una fuga o una excepción no capturada en el agente
   tumba la autenticación **y** la ruta de 10,3 Mbit/s. Mitigación: el código del alumno va en un
   **subproceso** con su propio cgroup, y el agente solo engendra, lee el PTY y reenvía.
2. **Prioridad.** El agente está en la ruta de datos y **no puede correr con `nice 5`**; el hijo sí
   debe. Son procesos distintos con políticas distintas, y el diseño tiene que respetarlo.
3. **Se pierden las herramientas.** Con una acción, el profesor depura con `ros2 action list` y
   `ros2 action send_goal`. Con un protocolo propio, cuando falle a las 10:15 de un martes **no
   habrá ninguna orden que mirar**. Mitigación: el agente expone su estado por un topic de solo
   lectura, para que `ros2 topic echo` siga sirviendo.

### C pierde, pero por menos, y su crítica hay que conservarla

FastAPI ejecutando por SSH. Su argumento fuerte es real y **hay que escribirlo en la arquitectura**:
la Decisión 2 dice que FastAPI no puede estar *«en la ruta de los datos en vivo»* — 80,7 kB/s por
robot— **y no dice nada del ciclo de vida de un proceso**, que son unos kB una vez por ejecución. Son
tres órdenes de magnitud. Lo que la auditoría condenó fueron tres patrones (proceso nuevo por
lectura, bloqueante, secuencial), no el protocolo.

Pierde por cuatro cosas medidas:

- 🔴 **Su premisa no existe ahora mismo**: `~/.ssh/authorized_keys` está a **0 bytes** (ejecutaste el
  comando que te ofrecí para retirar la clave; el `.bak` la conserva).
- 🔴 **`Linger=no`** → `systemd-run --user` por SSH no interactivo no es fiable, y sin él sus límites
  se caen a `ulimit`+`timeout`: sin `MemoryMax`, sin `TasksMax`, y **sin matar por cgroup**.
- **Centraliza el camino de control**: FastAPI caído = nadie puede parar un robot que conduce.
- **Necesita una credencial de flota** en el servidor central, en un proyecto cuya herida abierta es
  exactamente esa.

### A gana: el proxy de la Fase B es el **agente de sesión** del robot

El componente de la Fase B ya hay que escribirlo, instalarlo y certificarlo en las 16 Pis. La
pregunta no es «¿añadimos un agente?» sino «¿ese trabajo lo hace ese componente o levantamos otro?».

**Lo decisivo, verificado hoy:**

- **`robot.color()` NO lee el topic `/color`: llama al servicio `/get_rgbc_sensor_values`**
  (`atriz.py:328`), que tiene **0 apariciones** en la lista blanca. Cualquier diseño que haga pasar
  el código del alumno por rosbridge **tiene que ensanchar la lista blanca que la Fase A acaba de
  cerrar**. El agente no toca ni un glob: el programa del alumno corre con `rclpy` nativo, dentro del
  grafo, y la lista blanca del navegador sigue igual de cerrada.
- **`04_giro_preciso.py` tiene tres `input()`** (`:75`, `:103`, `:106`): el alumno mide con
  transportador y pulsa Enter. **Sin stdin, dos prácticas de diez están muertas.** Eso exige PTY, y
  mata cualquier diseño de petición-respuesta.
- **`atriz.py` se reutiliza sin tocar una línea.** Sus ocho protecciones son ocho fallos ya pagados:
  `SignalHandlerOptions.NO` (0 líneas de parada sin él), el `join()` antes de `destroy_node()`
  (SIGABRT en 2 de cada 3), el orden `_cerrando`/`_cerrado`, `limitar()` con `isfinite`
  (`avanzar(nan,nan)` conducía 4 m). Reimplementarlas en JavaScript es apostar a redescubrirlas todas
  en 16 robots con alumnos delante.
- **El botón de parar viaja por el mismo socket que la salida**: si el alumno ve texto, la parada
  llegará. Con dos componentes puedes ver salida con el canal de control muerto.
- **Solo el agente puede convertir el silencio de rosbridge en una frase.** rosbridge deniega con un
  `warn` y un `return`, sin respuesta al cliente. El agente lleva su copia de los globs y comprueba
  **antes** de reenviar.

---

## 3. La arquitectura

```
navegador ──wss://rvr-NN.local:9443──►  AGENTE DE SESIÓN (en la Pi)
              JWT en el subprotocolo        │
                                            ├─ ops propias: atriz_exec, atriz_stdin,
                                            │  atriz_signal, atriz_adjuntar
                                            │     └─► PTY ─► python3 programa.py ─► atriz.py
                                            │                (cgroup con límites)
                                            └─ todo lo demás, textual ──► ws://127.0.0.1:9090
                                                                          rosbridge
```

**Un proceso, un puerto, una autenticación, un certificado por robot.** rosbridge pasa a
`address: 127.0.0.1` y deja de ser alcanzable desde la red.

**Ejecución:** el código llega como cadena, se escribe en `/run/atriz/<sid>/` (**tmpfs**: sin
desgaste de SD, sin restos tras reiniciar), se lanza con `os.setsid()` —así el PID lo conocemos por
haberlo engendrado, y **`pkill -f` no aparece en ninguna parte**— sobre **PTY y no tubería**, porque:

1. `print()` contra una tubería es *block-buffered*: la salida aparecería a bloques minutos tarde.
2. **`input()` funciona**, que es lo que exigen dos prácticas.
3. La semántica de Ctrl-C llega sola.

`PYTHONPATH` al directorio de estudiantes **en solo lectura**, para que `from atriz import Robot`
funcione sin tocar nada y el alumno no pueda romper la biblioteca para el siguiente.

**Límites por cgroup v2** (verificado: `cpu memory pids` disponibles, systemd 255, **sin swap**):
`pids.max=64`, `memory.max=512M`, `cpu.max` 80 % de un núcleo con `nice +5` —el driver corre un lazo
de 0,05 s contra un watchdog de 0,3 s y **gana siempre**—, tope de pared **visible con cuenta atrás**
(dos prácticas son `while True` legítimos), y límite de salida **con contador de descartadas, nunca
en silencio**.

**Parar, en cuatro peldaños sobre el grupo de procesos:** `SIGINT` (el camino de Ctrl-C que
`atriz.py` ya captura y que hace `parar` → `/stop_scan` → desmontar) → esperar 10 s → `SIGTERM` →
`cgroup.kill`. Y después **se comprueba el efecto**: el agente llama a `/stop_scan` y mira que
`/odom` no se mueva. Si tras un `SIGKILL` el barrido quedó encendido, el X2 gira a 11,8 Hz por 16
robots hasta que alguien lo note.

**Un solo programa por robot.** `atriz.py:292` crea `Node('atriz_alumno')` con **nombre fijo**: dos a
la vez son dos nodos homónimos en el mismo dominio. Y mientras un programa corre, un `publish` del
navegador a `/cmd_vel_raw` se rechaza **visiblemente**; `/emergency_stop` pasa siempre.

---

## 4. Las fases

**F0 · Dos mediciones que van antes de escribir una línea.**

1. 🔴 **El aislamiento de clientes del AP del aula.** Si está activado rompe mDNS *y* la comunicación
   navegador↔robot: no es un ajuste del cliente, es el diseño de transporte entero. **Sin comprobar.**
2. 🔴 **`send_action_goals_in_new_thread` en la práctica.** Con una meta de `/navigate_to_pose` en
   curso, publicar `/emergency_stop` por la misma conexión y comprobar **con cinta** que el robot
   para. **Es un riesgo que existe hoy**, no del diseño nuevo.

**F1 · Verificar la línea base que todo lo demás asume.** El Ctrl-C de `atriz.py` está marcado
**NO VERIFICADO**: nadie ha matado un guion a mitad de un avance ni ha medido lo que recorre después.
Primero con SSH, y solo después con PTY. Construir sobre una protección no medida es repetir el error
que se acaba de retirar.

**F2 · El agente de sesión**, con las ops propias y el reenvío textual. Y `Delegate=yes` para el
subárbol de cgroup (👤 lleva `sudo`).

**F3 · El JWT y la Fase B.** Firma **asimétrica** (EdDSA o RS256): cada robot guarda **solo la clave
pública**, así ninguna Pi tiene un secreto. Con `HS256` habría un secreto compartido en 16 cacharros
sueltos en un aula.
🔴 **Y una restricción medida hoy: la Pi no tiene RTC** (`/dev/rtc*` no existe, `RTC time: n/a`). Hoy
`NTPSynchronized=yes`, pero en un aula sin NTP alcanzable un robot recién arrancado **rechazaría
tokens válidos o aceptaría caducados, en silencio**. El agente **se niega a arrancar si el reloj no
está sincronizado y lo dice a gritos**.

**F4 · El cliente web**, rehecho: teleoperación, telemetría real, editor con Monaco, panel de flota.

**F5 · El backend**: usuarios, asignación de robots, emisión de JWT, y el código del alumno
**guardado en la base de datos, no en el robot** — el robot solo tiene una copia efímera en tmpfs.

---

## 5. Verificación

Se comprueba **el efecto**, no el código de salida.

1. **F0 primero**: el AP del aula. Si aísla clientes, se para todo y se replantea el transporte.
2. **La línea base de Ctrl-C**, con cinta métrica, antes de construir sobre ella.
3. **`SIGINT` a través del PTY** recorre `cerrar()` igual que un Ctrl-C por SSH — medido por efecto:
   `/scan` a 0 Hz y el robot parado.
4. **La lista blanca sigue intacta**: `probar_lista_blanca.py` tiene que seguir dando lo mismo
   después del agente. Si el agente obliga a abrir un glob, es que el diseño se torció.
5. **Coste en batería** del agente más un proceso de alumno. **Nunca se ha medido**, y la Pi se
   alimenta del RVR con ~2 h de autonomía contra clases de 2-3 h.
6. **Un robot cargando no se pinta como roto**: el control de salud va por `/rosapi/topics`, no por
   telemetría.
7. **Nada se da por bueno por un `desenlace=0`.** La prueba de que el alumno puede mover el robot
   desde el navegador es `avanzar(0.20, 3)` **medido con cinta** contra los ~60 cm del mismo script
   por SSH. Este proyecto tiene seis casos de «informa de éxito sin haber hecho nada».

---

## 6. Lo que sigue sin decidir, y hay que decidir

| | |
|---|---|
| **Sesiones y reservas** | Recomendación de los tres arquitectos, coincidente: **el profesor asigna, robot fijo dentro de la clase, reasignable en caliente**. Motivo medido: autonomía ~2 h contra clases de 2-3 h — un calendario promete un robot que puede estar sin batería |
| **Cómo viaja el JWT** | El navegador **no permite cabeceras** en un WebSocket: query string o subprotocolo. Recomendado el subprotocolo (no queda en logs ni en el historial) |
| **El bloqueo de los precipicios** | 🔴 `hay_via_libre()` exige **cero pendientes**, y «el hueco de los precipicios» es inherente a un LIDAR 2D: **no se puede cerrar nunca**. Propuesta: reclasificarlo como riesgo aceptado con su mitigación escrita, o la puerta no puede abrirse por construcción |
| 👤 **Rotar la credencial `sphero`** | Sigue pública ahora mismo. Es lo primero, antes de tocar el repositorio |
| 👤 **`fmask` de `red.txt`** | La PSK del WiFi es legible por cualquier usuario |
| 👤 **La clave SSH** | `authorized_keys` está a 0 bytes; el `.bak` la conserva. Restaurarla es una línea, y hace falta si algún día se quiere el camino de mantenimiento |

---

## 7. Dos palancas encontradas hoy en el código de rosbridge

No están en la documentación del proyecto, y las dos atacan el mayor coste: **`/scan` es el 83 % del
tráfico** (67,1 de 80,7 kB/s por robot).

1. **`compression: "cbor"` / `"cbor-raw"`** existe, y `cbor2` está instalado. Manda binario en vez de
   JSON, que es donde está el multiplicador de 2,49× de `/scan`.
   **Estimación: 80,7 → 40,5 kB/s por robot; los 16, de 10,3 → 5,2 Mbit/s.**
   📝 **Teórico. Hay que medirlo antes de citarlo.**
2. **`throttle_rate`, `queue_length`, `fragment_size`** en `subscribe`.

---

## Ficheros

| | |
|---|---|
| `00_auditoria/planes/2026-08-03-plataforma-web.md` | **nuevo**: este plan, en el repositorio, tarea por tarea |
| `03_operacion/ARQUITECTURA.md` | añadir la distinción **datos en vivo** vs **ciclo de vida de proceso**, que hoy no está escrita y es la fuente de la confusión |
| `03_operacion/SEGURIDAD_ROSBRIDGE.md` | la Fase B pasa a ser el agente de sesión |
| `scripts/aceptacion_nucleo.py:93-118` | reclasificar el pendiente de los precipicios |
| `Atriz_web_server`, rama nueva | el cliente y el backend |
| El agente | va en `Atriz_rvr` (público) o en `atriz_migracion` — **decidir**, y sin secretos |
