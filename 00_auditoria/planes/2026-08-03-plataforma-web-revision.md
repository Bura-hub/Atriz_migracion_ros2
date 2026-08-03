# Fase 5 — Revisión del plan, tras someterlo a cuatro lentes opuestas

> **Qué es esto.** Una revisión del plan
> [`2026-08-03-plataforma-web.md`](2026-08-03-plataforma-web.md), no un plan nuevo. Producida el
> 2026-08-03 por la tarde **desde el PC de desarrollo**, con 13 agentes: cuatro auditores (uno por
> repositorio), cuatro arquitectos con lentes **deliberadamente opuestas**, un escéptico por
> arquitecto con mandato de **refutar, no de mejorar**, y una síntesis.
>
> ⚠️ **Todo lo de aquí es lectura de ficheros. Ninguna afirmación está contrastada contra
> hardware.** No había robot conectado. Lo que exija medir va en la sección 5.

---

## 0. El veredicto

**La app que está en los repositorios: descartada por unanimidad, y no por poco — no existe.** Los
tres repositorios suman **cero líneas de cliente de rosbridge**. `atriz-lab` tiene 0 coincidencias
de `fetch|WebSocket|roslib` en todo `frontend/src`; `Atriz_web_server` tiene **una** llamada HTTP en
todo su frontend, el login.

**La arquitectura del plan —agente de sesión en cada Pi— SÍ es la mejor.** Los cuatro arquitectos
dijeron **los cuatro** «el plan sirve con cambios», **ninguno propuso otra arquitectura**, y
**ningún escéptico refutó a su arquitecto**.

| Lente | Propuesta | Nota |
|---|---|---|
| abogado del plan | Puerta y ejecutor: el agente partido en dos, con la ruta de datos ciega | **7,5** |
| minimalista | Un proceso más por robot, y ninguno más en el servidor | 7 |
| experiencia docente | El taller: un terminal por robot, un muro para el profesor | 7 |
| seguridad de flota | Canal de parada independiente y JWT corto renovable | 6 |

Lo más informativo es el minimalista, cuyo encargo era restar: *«el agente de sesión en cada Pi es
la decisión correcta y la habría propuesto igual»*.

**La razón, y es la misma en las cuatro:** el navegador es **estructuralmente** incapaz de
distinguir «error del alumno» de «robot roto». `robot.launch.py` fija `params_glob: '[]'` y
`services_glob` no incluye `/get_rgbc_sensor_values`; `atriz.py:325-328` usa los dos. Un componente
dentro del grafo ROS puede leerlos; el navegador no, y no podrá sin ensanchar la lista blanca que
la Fase A cerró con **efecto físico** (evidencia 53: `raw_motors` al 30 % → **0,00 cm**).

---

## 1. Lo que sobrevive a las cuatro lentes — no se rediscute

Lo que aguanta a *abogado*, *minimalista*, *seguridad* y *docente* a la vez, **y a sus cuatro
escépticos**, es lo más sólido que hay aquí.

| | Coincidencia |
|---|---|
| **4 / 4** | El **agente de sesión en cada Pi**, sin alternativa propuesta |
| **4 / 4** | **rosbridge atado a `127.0.0.1`** — hoy el nodo lleva `'port': 9090` y **ningún** `address`. Es la línea que convierte la Fase B de intención en mecanismo |
| **4 / 4** | El código del alumno corre **en el robot**, con `rclpy` nativo sobre `atriz.py`, **sin tocar una línea** de la biblioteca |
| **4 / 4** | **PTY, no tubería**, y **un solo programa por robot** (`atriz.py:289` crea `Node('atriz_alumno')` con nombre fijo → la exclusividad sale de ahí, sin calendario) |
| **4 / 4** | **cgroup v2** con los números del plan: `pids.max=64`, `memory.max=512M`, `cpu.max` 80 %, `nice +5` |
| **4 / 4** | **No ensanchar las listas blancas**, y `probar_lista_blanca.py` como prueba de regresión |
| **4 / 4** | 🔴 **TLS AHORA, no en la Fase B** — única ruptura unánime con el plan. HTTPS + `ws://` = contenido mixto = no conecta nada. Y los cuatro rechazan el autofirmado por robot: enseña al alumno a aceptar 16 excepciones |
| **4 / 4** | **JWT asimétrico (EdDSA)**, clave privada solo en el servidor: ninguna Pi guarda un secreto |
| **4 / 4** | **FastAPI fuera de la ruta de datos, y SQLite basta.** Nadie propone PostgreSQL, Redis, Celery, TimescaleDB ni Docker Compose |
| **4 / 4** | **F0 —el aislamiento de clientes del AP— antes de una línea de código** |
| **4 / 4** | El **coste en CPU y batería del agente** es el riesgo mayor, y **nadie lo ha medido**. Método prescrito: `/proc/<pid>/stat` dos veces con 20 s, **nunca** `ps -o %cpu`; batería en **voltios** |
| **4 / 4** | De los dos repos web se reutiliza **casi nada, y lo mismo**: `globals.css` + `tailwind.config.ts` de `atriz-lab`; `dependencies.py` + `core/security.py` del viejo **como referencia**. **Cero** del camino de ejecución de cualquiera de los dos |

---

## 2. Los cinco huecos del plan, por gravedad

1. 🔴 **No hay profesor.** «Profesor» aparece **dos veces en 403 líneas**, y solo para decir que
   asigna. No hay vista de flota ni presupuesto de red para ella. La cuenta que faltaba:
   **16 × 81 kB/s = 10,3 Mbit/s hacia un solo portátil** — el presupuesto entero del WiFi del aula
   para una pantalla que muestra nueve estados. **La Decisión 2 se razonó contra el servidor, nunca
   contra un navegador.** → El muro del profesor se alimenta de un **digest a ~1 Hz**, no de
   telemetría.
2. **No hay política de desconexión.** El plan diagnostica *«cerrar la pestaña NO cancela la meta:
   el programa sigue corriendo y el robot moviéndose, y ya no lo ve nadie»* **como argumento contra
   la postura B**… y no lo resuelve para la suya. Tiene `atriz_adjuntar` —que implica sesiones que
   sobreviven a la pestaña— y ningún plazo ni acción asociados.
3. 🔴 **El driver no publica su bandera de parada de emergencia.** Verificado: `rvr_driver_node.py`
   tiene 7 `create_publisher` (`:385-434`) y **ninguno es de la parada**; `:1856` la pone y no emite
   nada, `:2423` la baja igual de callado. **Consecuencias:** ninguna UI puede pintar «parada
   activa» con un dato del robot; el ACK de parada por «`/odom` quieto» es **indistinguible de un
   robot cargando** (evidencia 52); y no hay señal que separe «cargando» de «mudo». **Es una línea
   de driver que resuelve un problema de arquitectura, y no está en el plan.**
4. **No dice quién sirve el NTP.** El plan exige reloj sincronizado y hace que el agente **se niegue
   a arrancar** sin él. Sin chrony en el aula, eso son **16 robots muertos** el día que falle la
   hora — y en un aula sin internet, ese día llega.
5. 🔴 **No escribe que el alumno tiene MÁS autoridad que la web.** Con `rclpy` nativo alcanza
   `raw_motors`, `move_timed`, `move_to_pose`, `move_to_pos_and_yaw` y `set_ir_mode('following')` —
   los seis caminos que se saltan `collision_monitor` y watchdog, y el último **ni siquiera
   comprueba la parada**. → **«`raw_motors` ya no es alcanzable, 0,00 cm verificado» deja de ser
   cierto mientras haya una sesión en marcha.** Es el precio de la postura A y hay que escribirlo
   con la seriedad del hueco de los precipicios.

**Y dos más, menores pero con fecha:**

6. **Atar rosbridge a loopback dispara un aviso del propio verificador** (`verificar_robot.sh`
   comprueba `[::]:9090`). Sería la **novena** vez que el verificador se queja del estado bueno.
   Se actualiza **en el mismo commit**.
7. **El certificado por nombre mDNS mata el override por IP** de `ARQUITECTURA.md`, salvo que el
   SAN lleve `iPAddress` — y la del DHCP no cabe en un certificado.

---

## 3. Las discrepancias reales, y el hecho que decide cada una

Ninguna se resuelve promediando posturas. Cada una tiene un hecho que la zanja.

| Discrepancia | Posturas | Qué la decide |
|---|---|---|
| **¿Un proceso o dos?** | monolito (minimalista, docente) · puerta+ejecutor (abogado) · agente+parada (seguridad) | **Que el driver publique su bandera de parada** quita el argumento más fuerte a favor de partir. Lo que queda en pie es disponibilidad: **matar el agente con el robot avanzando y medir con cinta — y repetirlo con el agente COLGADO (`SIGSTOP`), no muerto**, que es el modo de fallo característico de este proyecto |
| **¿El agente lleva copia de los globs?** | sí (plan, docente, seguridad) · no (abogado, minimalista) | 16 copias de una política verificada en un solo sitio = deriva garantizada; pero es lo único que convierte el silencio de rosbridge en una frase. **Decisión, no medida** |
| **¿El reloj se arregla o se aborta?** | abortar (plan) · chrony en el aula (minimalista, seguridad) | 👤 **¿Hay un servidor del aula siempre encendido?** Si lo hay, son dos líneas de `provision.sh`. Si no, el plan crea una dependencia dura nueva |
| **¿Quién posee el barrido del LIDAR?** | la sesión (docente) · cada `Robot()` (hoy) | El docente lo llama «la mayor fuga de minutos de clase»; su escéptico demuestra que **son timeouts, no costes** (`atriz.py:549-566` sondea cada 0,01 s y retorna en ms con el driver vivo). **Pero lo que sí se paga entero es `atriz.py:500` (1,0 s) más el tiempo físico hasta el primer `/scan` real — el X2 subiendo de 2,7 a 11,8 Hz, y eso NO está medido.** Un cronómetro y diez repeticiones lo cierran |
| **¿El alumno corre como `sphero` o como usuario propio?** | propio (abogado, seguridad) | Como `sphero`, el alumno hace `print(open('/boot/firmware/red.txt').read())` y **la PSK del WiFi sale por el terminal de la web**. Lo que falta medir: **si DDS empareja entre dos usuarios distintos** — si hay que forzar UDP por perfil XML, cambia el transporte del robot entero y hay que re-medir los 16,5 Hz |
| 🔴 **¿Presencial o remoto?** | — | 👤 **La única que no es técnica, y condiciona el orden entero de F4.** Las diez prácticas piden cinta, transportador o superficies bajo el robot; `04` y `99` **entre pausa y pausa**. Pero `Atriz_summary.txt`, el acta fundacional, define un cliente **remoto**. Si es taller presencial sin SSH, la teleoperación va **la última** (ninguna de las 10 prácticas teleopera) y el terminal es el producto |

---

## 4. Errores de hecho del plan original, verificados

- **`plan:309` cita `atriz.py:292`** para `Node('atriz_alumno')`; la línea real es la **289**.
- **`plan:193` dice que `04_giro_preciso.py` tiene tres `input()`. Son cuatro** (`:75, :103, :106,
  :109`), más una quinta en `99_test_ctrl_c.py`. No cambia la conclusión: la refuerza.
- 🔴 **El Ctrl-C: el plan pide de más y tres arquitectos pidieron de menos.** El plan lo da por
  `NO VERIFICADO`; tres arquitectos «corrigieron» diciendo «5 de 5 con el robot en movimiento».
  **Las dos cosas son falsas.** `60_atriz_ctrl_c.txt:42-45`, literal: *«una de las cinco corridas […]
  tuvo el Ctrl-C en el `input()`, antes de que el robot arrancara. […] No cuenta como prueba de
  parada en movimiento, y por eso se dice»*. **Son 4 de 5.** A F1 le falta la quinta corrida en
  movimiento **y** los centímetros.
- **`plan:341` (F4) lista «editor con Monaco»** sin calibrar su coste. Ver sección 7: depende de la
  rama y del repositorio que se elija.

---

## 5. F0 ampliada — lo que va antes de escribir código

### Necesita el aula
1. 🔴 **Aislamiento de clientes del AP.** Si está activado no se ajusta el cliente: **se replantea
   el transporte entero**. Es la única medida que puede tirarlo todo, y con certificados por nombre
   mDNS el golpe es mayor que hoy.
2. **Estabilidad del WiFi con 16 clientes**: cuántos cortes de más de N segundos en 2 h. Sin ese
   número, **cualquier plazo de deadman es inventado**.
3. 👤 **¿Los PCs del aula son gestionados o los traen los alumnos?** Decide si la CA del laboratorio
   es viable. No consta en ningún repositorio.

### Necesita el robot
4. 🔴 **CPU y batería de un agente esqueleto** (solo TLS + reenvío) sobre un robot navegando 15 min.
   `/proc/<pid>/stat` dos veces con 20 s; batería en **voltios**.
   📝 Corrección a una premisa que circuló: son **~28,5 msg/s y 81 kB/s**, no «~1000 msg/s». Lo que
   se mide es el coste del TLS y de la copia, no el del parseo.
5. **¿Empareja DDS entre dos usuarios distintos?** Driver como `sphero`, nodo trivial como `alumno`,
   mismo `ROS_DOMAIN_ID`; con `medir_ritmo_ros2.py` (ejecutor persistente) **y por efecto**:
   `avanzar(0.20, 3)` con cinta. Decide si el usuario separado es barato o caro.
6. **El reenvío de tramas contra el Tornado de rosbridge**: fragmentación, ping/pong, cierre,
   `permessage-deflate` y **tramas binarias** (`compression: cbor` no es texto). Criterio de efecto:
   `probar_conexion_web.html` y `probar_lista_blanca.py` dando **exactamente lo mismo** por el 9443.
7. **`send_action_goals_in_new_thread`** con una meta en curso y cinta métrica. Es riesgo **de hoy**.
8. **Los centímetros del Ctrl-C, y la quinta corrida en movimiento** (ver sección 4).
9. **Tiempo de `Robot()` de «Run» a movimiento**, n=10 con el barrido apagado y n=10 con él
   encendido. Decide si la sesión debe poseer el barrido.
10. **Congelar el cgroup del alumno 60 s y medir `/odom` desde un tercer proceso.** Un suscriptor
    congelado deja de vaciar su cola de memoria compartida: **si el mecanismo de seguridad
    estrangula al driver**, hay que cambiar `freeze` por `SIGSTOP` o por matar.
11. **El ahorro real de `compression: "cbor"`.** El plan lo marca **teórico** y aun así cita
    80,7 → 40,5 kB/s. No se presupuesta la red con ese número hasta medirlo.
12. **Cuánto tarda Nav2 en estar listo desde `systemctl start`.** Sin él, la UI no puede distinguir
    «arrancando» de «roto».

### 👤 Decisión del usuario — ningún código las hace
13. 🔴 **Rotar credenciales, y la lista creció:** `sphero`, la PSK del WiFi, **la de PostgreSQL** del
    `.env` commiteado en `Atriz_web_server` (público, y **solo en `master`**) y **la `SECRET_KEY` de
    los JWT** (`core/security.py`, en **las tres ramas**). Purgar el historial no cierra nada si no
    se rota antes.
14. 🔴 **`fmask=0177,dmask=0077` en `/etc/fstab`.** Deja de ser higiene **el día que se ejecuta
    código de alumno en el robot**.
15. **Restaurar `authorized_keys`** (0 bytes). Con rosbridge en loopback, SSH pasa a ser el único
    rescate y el único camino que devuelve las herramientas ROS al PC por túnel.
16. **TLS: ¿un certificado con 16 SAN o 16 certificados?** Uno = una clave privada replicada 16 veces
    (microSD robada = cifrado de los dieciséis) pero imagen dorada idéntica.
17. **¿Presencial o remoto?** (sección 3).
18. **Reclasificar el pendiente de los precipicios** como riesgo aceptado con mitigación escrita, o
    `hay_via_libre()` no puede abrirse nunca por construcción.
19. **¿Dónde vive el agente:** `Atriz_rvr` (público) o `atriz_migracion` (privado)?
20. **Retención y borrado de transcripciones**, si se adopta el muro docente. Es una necesidad que
    hoy no existe y que esa propuesta crea.

---

## 6. Lo que este informe NO puede cerrar

- **Si el agente en Python cabe en la Pi.** Nadie lo ha medido y el modo de fallo es el peor del
  proyecto: **no se cae nada — se pone lento, el latido sigue saliendo y el robot parece sano.**
- **La latencia extremo a extremo navegador → motores: NO MEDIDA.** No se puede prometer ninguna
  cifra de respuesta de teleoperación.
- **Cómo se comporta rosbridge por dentro.** Su fuente **no está en ninguno de los tres
  repositorios**: la denegación en silencio, la cola por conexión y el Tornado son **de segunda
  mano**. Y este proyecto ya pagó caro creerse una afirmación sobre una herramienta sin medirla
  (`ros2 topic hz` guió un rediseño entero antes de retractarse).
- **Si `provision.sh` funciona.** Nunca se ha ejecutado entero sobre un 24.04 limpio, y cada pieza
  nueva —agente, parada, CA, NTP, usuario `alumno`— se apila sobre esa suposición no levantada.
- **Cuánto cuesta el barrido encendido toda la sesión.** Marcado NO MEDIDO **por decisión expresa**
  (2026-07-31) porque entonces no decidía nada. **Ahora decide.**
- 🔴 **La autonomía de «~2 h» es débil.** Sale de extrapolar `percentage` —que el propio proyecto
  prohíbe usar para decidir carga— sobre un ritmo que en la misma medición **no es constante**
  (1,12 → 0,74 → 0,37 %/min). De esa cifra cuelgan **dos decisiones**: el modelo de sesiones y no
  habilitar Nav2. La dirección es sólida; **el número no aguanta que se apoye nada más encima**.

---

## 7. La decisión de repositorio, reabierta

El plan decidió **«rama nueva en `Atriz_web_server`, sin tocar el historial»**. Esa decisión se tomó
sin saber tres cosas que ahora están medidas, y por eso se reabre.

| | `Atriz_web_server` | `atriz-lab` | repo nuevo |
|---|---|---|---|
| visibilidad | **público**, 65 186 KB | **público**, 1839 KB | a elegir |
| ramas | **tres SIN ancestro común** (`compare` → 404) | una | — |
| artefactos | **98,1 %** del árbol (`swarm_lab_env/` 5578 entradas, `build/` 1175, `devel/` 93) | limpio | — |
| ¿se puede clonar en Windows? | **NO** — rutas demasiado largas bajo `build/demiurge-tycho/…` | sí | sí |
| submódulo | `src/demiurge-tycho` es un **gitlink sin `.gitmodules`**: roto | — | — |
| credenciales en el historial | **sí**, y la `SECRET_KEY` en las tres ramas | no | no |
| backend | pydantic **v1**, Python 3.8 | pydantic v2, Python 3.12 | — |
| lo aprovechable | `dependencies.py` + `security.py` **como referencia**; Monaco integrado **en `pruebas`** | `globals.css` (582 líneas de tokens) + `tailwind.config.ts` | — |

**Lo que inclina la balanza, y no es el inventario:** *ninguno de los tres ha hablado jamás con
rosbridge*. El trabajo central —transporte, autenticación, telemetría— **es nuevo en los tres
casos**, así que la base aporta poco y el lastre pesa mucho.

**Y hay un bloqueo duro:** `Atriz_web_server` **no se puede clonar con checkout en el PC del
usuario**, que es donde se ejecuta la Fase 5.

→ **Recomendación: repositorio nuevo y privado.** Lo aprovechable de los otros dos son **ficheros
que se copian** (`globals.css`, `tailwind.config.ts`, `dependencies.py` como referencia), no una
base sobre la que construir. Un repositorio nuevo empieza **sin credenciales en el historial**,
sin 138 MB de artefactos, sin un submódulo roto y sin tres ramas que no se hablan.

⚠️ **Lo que NO resuelve un repositorio nuevo, y hay que decir en voz alta:** `Atriz_web_server`
sigue público con la `SECRET_KEY` dentro. Abandonarlo **no lo cierra** — hay que rotar igual.
