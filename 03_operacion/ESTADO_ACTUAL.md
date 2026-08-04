# Estado actual

Fichero corto, para situarse en un minuto. **Es el canal de contexto entre el Claude del PC y el de
la Pi**, y el único que sobrevive cuando Claude Code se desinstale del robot.

`CLAUDE.md` son 107 KB (~26.800 tokens) y `TRASPASO.md` otros 72 KB: eso es para el detalle. Esto es
para saber por dónde vas.

> **Regla:** si algo importa y solo vive en un hilo de Claude, en `memory/` o en un transcripto,
> **no existe**. Se pierde al desinstalar. Lo que importe, aquí o en el repositorio.

---

**Última actualización:** 2026-08-04

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

🔴 **PERO NO SE HA EJECUTADO NUNCA CONTRA UN ROBOT, ni en un navegador.** El criterio de aceptación
de la especificación —*«un robot real se teleopera desde el navegador y el desplazamiento medido con
cinta coincide con el del mismo movimiento por SSH»*— **sigue sin cumplirse**. La revisión final lo
dijo así: los defectos que se arreglaron son **«trampas armadas esperando al primer consumidor»**.
→ **Lo que falta son las tareas 8 y 9 del plan, y necesitan el robot encendido y cinta métrica.**

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
