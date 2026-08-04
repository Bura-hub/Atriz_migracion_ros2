# Las dudas abiertas — todas juntas, para la revisión

> Escrito el 2026-08-04, al terminar el diseño de la estructura de la aplicación.
> **Cada una lleva mi recomendación y qué he hecho mientras tanto**, para que ninguna te bloquee:
> ninguna ha frenado el trabajo. Las que piden robot o aula están al final.

---

## A · Las que cambian el diseño — decide tú

### A1 · 🔴 La F0 bloquea el producto, y no la puedo medir yo

**Qué es:** si el punto de acceso del aula **aísla clientes entre sí**, el navegador del alumno no
puede hablar con el robot directamente y **el transporte entero se replantea** — habría que meter un
relé por el servidor, que es otra arquitectura.

**Por qué importa:** bloquea el **agente de sesión**, que bloquea el **terminal**, que **es el
producto** (decisión 17: ninguna de las diez prácticas teleopera).

**Lo que necesito:** un portátil y un robot en el aula, en el AP real, y un `ws://rvr-01.local:9090`
desde el navegador. Diez minutos. **En casa no se puede medir**: la red de casa no aísla.

**Mi recomendación:** medirlo **antes** que ninguna otra cosa del terminal. Es el único experimento
del proyecto que puede tirar un diseño entero, y cuesta diez minutos.
**Mientras tanto** he construido todo lo que **no** depende de ella, que es la aplicación menos el
terminal.

---

### A2 · Las tres señales que le faltan al driver — ¿las meto?

Para que la interfaz sea honesta, el robot tiene que publicar tres cosas que hoy no publica:

| Señal | Sin ella, la interfaz… | Coste |
|---|---|---|
| **`/latido`** 1 Hz, contador monótono | **no puede saber si un robot está vivo** en el muro del profesor sin pagar `/odom` (1,7 Mbit/s por 16) | 0,5 kB/s los 16 |
| **La bandera de parada** | dice «parada enviada» y **nunca «parada activa»** | ~0 |
| **Un «estoy cargando»** | pinta de ámbar un robot que solo está en el cargador, **el estado cotidiano** | ~0 |

✅ **HECHO el 2026-08-04: las tres van en un solo topic, `/estado_robot` a 1 Hz**
(`atriz_rvr_msgs/EstadoRobot`), en la rama **`feat/estado-robot`** de `Atriz_rvr`. `ros2` intacta en
`65ad124`, y el diff toca **4 líneas existentes** —la lista blanca, el reflujo de un `import` y un
rótulo—, todo lo demás es añadido. **NO VERIFICADO: no hay robot.**

🔴 **Y al escribirlo apareció un fallo de mi encargo, que conviene que sepas porque es de los
buenos:** yo dije que `reanudaciones_fallidas` se apoyara en `_t_ultima_muestra`. **Habría estado
mal**: ese campo lo reinician también `_conectar_rvr` y `_recuperar_streaming`, así que significa
«hace poco que pasó algo», no «hace poco que llegó un dato» — y con el RVR apagado una reanudación
habría parecido un éxito, que es **exactamente el fallo del 2026-08-02 reproducido dentro del campo
escrito para detectarlo**. Resuelto con un espejo que solo tocan los manejadores.

⚠️ **Lo que hay que mirar al fusionarlo NO es el topic nuevo:** es que `/odom` e `/imu` sigan
publicando. El riesgo de este parche es llevarse por delante la telemetría, no fallar en lo suyo.

**Mi recomendación era: sí, pero en una RAMA APARTE**, no en `ros2`. Razón:
tocar el driver sin robot delante es exactamente donde este proyecto se ha hecho daño. *«Una
excepción en un manejador de telemetría mata `/odom` e `/imu` en silencio»* costó una sesión entera,
y el fallo **no deja ni una línea en el log**.
→ Así mañana lo revisas y lo fusionas **tú**, con el robot delante, y nada de lo que ejecutes cambia
  hasta que lo decidas. Si no te convence, se borra la rama y no ha pasado nada.

---

### A3 · Las 1134 líneas de maqueta de `atriz-lab` — ¿se tiran?

`Dashboard.tsx`, `RobotStatusCard.tsx`, `SystemMetricsCard.tsx`, `ActiveExperimentsCard.tsx`,
`DashboardLayout.tsx`, `ToastNotifications.tsx`. **Ninguna habla con nada**: cero `fetch`, cero
`WebSocket`. Pintan un estado de robot **inventado**.

**Mi recomendación: borrarlas.** Una interfaz bonita que enseña un estado falso es **el modo de
fallo característico de este proyecto** — el nodo en verde con el robot mudo, `systemctl active`
sobre un driver muerto, `success=true` sin encender el LED. Una maqueta que dice «Robot 3: OK» sin
haber hablado con el robot 3 es lo mismo, en la pantalla que mira el profesor.

⚠️ **Pero no las he tocado**: puede que el diseño visual sea tuyo y quieras conservarlo como
referencia. **No he construido encima de ellas** tampoco — la aplicación nueva no las importa.
Decides tú: borrar, o quedártelas como referencia visual en una carpeta `maquetas/` que no compile.

---

### A4 · El taller ocurre antes que la Fase B — ¿qué se hace con eso?

**El hecho:** rosbridge 2.7.0 **no tiene autenticación**. No es que esté mal configurada: no existe.
Con la Fase A cerrada, `raw_motors` ya no es alcanzable — pero **cualquiera en el aula puede
teleoperar cualquier robot** por `cmd_vel_raw`.

**Mi recomendación: aceptarlo explícitamente para el taller presencial, y escribirlo.** En un aula
con el profesor delante y los robots a la vista, el atacante tendría que estar en la sala haciéndolo
delante de todos. **El riesgo real no es el alumno malicioso: es el error honesto** — dos pestañas
del mismo robot, o alguien que teclea el número que no es.
→ Eso último **sí** se puede mitigar sin autenticación, y es lo que he hecho: la aplicación abre
  **una conexión por robot**, atada a la ruta, y se cierra al salir.

🔴 **Lo que NO recomiendo es poner un login que no proteja nada.** Sería el estado engañoso otra
vez: la pantalla diría que hay control de acceso y no lo habría.

---

### A5 · ¿Un robot por alumno, o compartido?

El diseño asume **un robot por alumno, fijo durante la clase**, asignado por el profesor. Si hay más
alumnos que robots cambian dos cosas:

- El terminal deja de ser «uno por robot» y necesita **una cola** (`atriz.py` crea
  `Node('atriz_alumno')` con **nombre fijo**: dos a la vez son dos nodos homónimos).
- La suscripción compartida de rosbridge empieza a doler: **el primero que se suscribe impone el QoS
  a todos**, y una pestaña puede dejar mudas a las demás.

**Mi recomendación:** si son ≤ 16, uno por alumno y no hay problema. **Dime cuántos alumnos** y si
son más lo diseño con cola. **Mientras tanto** he construido para el caso de uno por robot, que es lo
que decía el plan.

---

### A6 · El terminal: ¿Monaco, o algo más barato?

Monaco (el editor de VS Code) son **~5 MB** y una dependencia nueva. Sobre el WiFi del aula, con 16
navegadores cargándolo a la vez, el primer arranque puede ser lento.

**Mi recomendación: empezar con un `<textarea>` con números de línea y tabulación,** y subir a
Monaco solo si molesta. Las prácticas son de **~30 líneas**; autocompletado y *linting* no aportan
nada ahí, y el ancho de banda del aula ya está contado. **No es una decisión urgente**: el terminal
está bloqueado por A1 de todos modos.

---

## B · Las que necesitan el robot — y son tuyas

### B1 · 🔴 La T9 no está cerrada: falta la cinta

Anoche el cliente web movió el robot **59,7 cm según su propia odometría**. Eso es odometría
comparándose consigo misma. **El criterio de aceptación es la CINTA**, y contra un control por SSH
con el mismo comando.
→ Sin ese número, lo que está probado es que **la cadena funciona**, no que el movimiento sea el
  pedido. Es una distinción que este proyecto ya pagó.

### B2 · 🔴 La parada de emergencia, publicada con el robot EN MARCHA

**Ha fallado cuatro veces, siempre en silencio y con `200 OK`.** Nombre de topic, namespace, QoS, y
la cuarta al **soltarla**. Las causas 2 y 3 **solo aparecen publicando de verdad**: leer el código da
el nombre pero no el namespace resuelto ni el QoS.
→ Publicar `/emergency_stop` con el robot moviéndose y **mirar el log del driver**.
→ ⚠️ Usa `journalctl --since "-25 s"`. Con `$(date -u +%T)` la ventana cae **cinco horas en el
  futuro** (UTC−5) y cuenta 0 aunque la parada haya llegado.

### B3 · El mapa del aula

Sigue sin existir, y sin él no hay AMCL ni Nav2, así que `atriz-nav.service` está **instalado y sin
verificar**. No bloquea la web —la teleoperación va la última— pero sí bloquea cualquier «ve a la
mesa 3».

### B4 · `fmask=0177` para `red.txt`

Pendiente desde el 2026-08-01. La PSK del WiFi es legible por cualquier usuario del robot **sin
`sudo`**, y `chmod` sobre `/boot/firmware` **se acepta y no hace nada**. Se cierra en `/etc/fstab`.
La imagen dorada lo replicaría por 16.

---

## C · Lo que NO es duda, para que no lo busques

- **Qué repositorio usar** — cerrado: `atriz-lab`, sobre `main`. Las tres webs anteriores tenían
  **cero líneas de cliente de rosbridge**, así que no había nada que aprovechar.
- **`throttle_rate` para el muro del profesor** — cerrado y **descartado**: `min()` en
  `subscribe.py:225`, gana el cliente más rápido para todos. El muro se suscribe solo a topics
  baratos.
- **Mandar `qos` en `subscribe`** — cerrado y **prohibido en el código**: el primero que se suscribe
  impone el QoS a todos, y una pestaña puede dejar mudas a las demás.
- **Si la web puede confirmar un efecto físico** — cerrado: **no puede**, y el tipo del cliente hace
  hoy **estructuralmente imposible** prometerlo.
