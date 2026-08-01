# Bitácora

Una entrada por sesión de trabajo. Formato: qué se hizo, qué se verificó, qué quedó pendiente.

---

## 2026-08-01 (noche) — El LIDAR inundaba el journal, y la primera solución era peor

`atriz-escaneo off` es el **estado normal en reposo** de los 16 robots. Con él, el nodo del
YDLIDAR emitía `Failed to get scan` **25 veces por segundo**: 47 291 de 47 551 líneas del
journal del servicio (**el 99 %**), 2.17 millones de mensajes al día por robot. Ahoga cualquier
error de verdad —y los peores fallos de este proyecto están documentados como silenciosos— y
son escrituras 24/7 sobre una **microSD**, que es lo que las mata.

### 🔴 Lo interesante no es el bug, es cómo se estuvo a punto de arreglar mal

La propuesta era **no levantar el nodo del LIDAR** hasta que hiciera falta. El usuario
desconfió —*«¿voy a perder esa automatización al encender el robot?»*— y pidió que se le
convenciera siendo imparcial. Al ir a argumentarlo hubo que leer el fuente, y la causa real
estaba ahí:

```cpp
while (ret && rclcpp::ok()) {
  if (laser.doProcessSimple(scan)) { ...publica... }
  else { RCLCPP_ERROR(node->get_logger(), "Failed to get scan"); }   // 20 Hz
}
```

`/stop_scan` y `/start_scan` son servicios **del propio nodo** y llaman a `turnOff()`/`turnOn()`,
pero **nadie guarda ese estado**. No era una consecuencia de apagar el barrido: **al driver le
falta una variable.**

Las tres opciones que se habían planteado atacaban el síntoma, y la recomendada además cambiaba
el arranque del robot para nada. **La desconfianza del usuario fue lo que forzó a mirar.**

### El arreglo: nueve líneas, y no cambia nada del arranque

Una bandera `std::atomic<bool> escaneando` que los dos servicios actualizan, y una salida
temprana en el bucle. ✅ Verificado en rvr-01:

| | antes | después |
|---|---|---|
| barrido apagado | 502 errores / 20 s | **0** |
| `atriz-escaneo on` | — | `/scan` a **12.00 Hz**, 250 puntos |
| `atriz-escaneo off` | — | 0 mensajes, **0 ruido** |

El nodo **sigue levantándose con el robot**, como antes.

### Y la otra mitad: que sobreviva a un reflasheo

`provision.sh` clona el ydlidar de GitHub y **le borra el `.git`**. Un cambio a mano se perdería
y este robot divergiría de uno recién aprovisionado — y la regla dice que **gana el script**.
Por eso el parche se versiona en `Atriz_rvr/atriz_rvr_bringup/patches/`, `provision.sh` lo
aplica tras clonar (idempotente), `patch` se añade a los paquetes de apt, y el verificador
comprueba **el fuente y el efecto**.

📝 Si el upstream lo arregla algún día, el parche fallará al aplicarse y `provision.sh` lo dirá.

### 📄 Y un tercer caso de deriva documental

El **plan** decía «Nav2 ⏳ pendiente» con Nav2 navegando desde el 31 de julio (9–10 cm de error,
4 de 4 rodeando obstáculos, AMCL a 0.1 cm). Van dos en un día, con el índice del manual. Los
documentos de **estado** se quedan atrás mientras las evidencias están al día. Regla escrita en
el propio plan: al cerrar algo, se actualiza **en el mismo commit** que la evidencia.

---

## 2026-08-01 (tarde) — La red de la flota, verificada de extremo a extremo

Cerró **la última incógnita grande antes de la Fase 5**: cómo hablan la web y 16 robots, y cómo
se pasa del PC de casa al laboratorio sin reconfigurar dieciséis tarjetas.

### ✅ La suposición que sostenía el diseño: verificada

Todo dependía de que una IP **estática** y el **DHCP** convivieran en la misma interfaz. Si no,
había que rehacerlo. Conviven:

```
wlan0  UP  10.14.7.7/21  192.168.1.200/24  192.168.1.58/24
            ^laboratorio  ^casa             ^DHCP
default via 192.168.1.1 dev wlan0 proto dhcp     ← la ruta la pone el DHCP, como se diseñó
```

**Este robot se lleva al laboratorio sin tocar un solo comando.**

### ✅ La web habla con el robot, probado desde un navegador de verdad

`ws://rvr-01.local:9090` desde el PC del usuario, con
[`03_operacion/probar_conexion_web.html`](03_operacion/probar_conexion_web.html) — sin
librerías y sin CDN, para que funcione sin internet. Funcionaron **las dos direcciones**:
telemetría llegando y `set_led_rgb` **encendiendo los faros de verdad**, confirmado con la
vista. Importaba: en este proyecto `success=true` ya devolvió `true` sobre un LED que no
alumbra.

```
navegador → WebSocket → rosbridge → servicio ROS 2 → driver → SDK → serie → RVR → LED
```

Y resolvió **por nombre**, sin escribir ninguna IP: eso es lo que permite que el mismo código
web funcione en las dos redes.

### ✅ Riesgo nº4 de `FLOTA.md`: cerrado, y con la estimación corregida

| Estado | por robot | ×16 |
|---|---|---|
| navegando | **80.7 kB/s** | **10.3 Mbit/s** |
| en reposo | **13.6 kB/s** | **1.7 Mbit/s** |

Se había estimado que el JSON de rosbridge multiplicaría por **3–5×**. El real es **~2×**, y esa
diferencia separa «hay que comprar red» de «cabe». Medido **dos veces con dos clientes
distintos en dos máquinas distintas**, que coincidieron al 3 % en reposo — en un proyecto donde
ya han mentido cuatro instrumentos, eso convierte la cifra en un hecho replicado.

🔴 **La palanca: `/scan` es el 83 % del tráfico.** La diferencia entre 1.7 y 10.3 Mbit/s es
`/scan` y nada más.

### 🔴 Tres fallos encontrados, dos de ellos míos

1. **`chmod 600` sobre `/boot/firmware` no hace nada, y devuelve 0.** Es FAT: no guarda
   permisos de Unix, los fija el montaje. **La PSK del WiFi queda legible por cualquier usuario
   de los 16 robots.** Y la instrucción `sudo chmod 600 red.txt` la di yo, en los pasos
   detallados: no solo era inútil, daba falsa confianza. Se cierra en `/etc/fstab` con
   `fmask=0177,dmask=0077` — **pendiente del usuario**.
2. **Un fichero rancio en `/tmp` inventó un fallo de netplan que nunca ocurrió.**
   `fs.protected_regular=2` impide a root escribir en un `/tmp/…` ajeno; si la redirección
   falla, **bash no ejecuta el comando**, y el `else` imprimió el contenido de seis horas antes
   como si fuera el error del momento. Arreglado con `mktemp` en `first-boot.sh` y en
   `provision.sh`, que tenía el mismo patrón.
3. **El índice del manual llevaba desviado del contenido.** Decía que los capítulos 9, 10, 11 y
   12 estaban «no escritos» cuando llevaban semanas escritos y verificados, y numeraba hasta 12
   mientras el manual llegaba al 18. Además había un «Capítulo 6» huérfano **entre el 16 y el
   17**. Es la deriva documentación↔realidad que la auditoría original señaló como el problema
   de fondo, reproducida dentro del documento que venía a arreglarla.

### Cambios

| Fichero | Qué |
|---|---|
| `scripts/first-boot.sh` | **`--solo-red`**: regenera el netplan sin reiniciar ni tocar la identidad · `mktemp` |
| `scripts/provision.sh` | `mktemp` para el `.deb` de ROS |
| `scripts/verificar_robot.sh` | **sección 12**: mDNS, netplan, `red.txt`, direcciones reales de `wlan0`, rosbridge en las dos familias, y una regresión que busca rutas fijas de `/tmp`. **102 correctas, 0 fallos** |
| `scripts/red.txt.ejemplo` | avisa de que `chmod` no sirve sobre la FAT |
| `03_operacion/probar_conexion_web.html` | **nuevo** — la prueba desde el navegador |
| `mediciones_banco/probar_mdns.py` | **nuevo** — mDNS crudo, sin dependencias · `--flota 16` |
| `mediciones_banco/probar_rosbridge.py` | **nuevo** — cliente WebSocket propio que mide bytes/s |
| `02_manual/…` | **capítulo 19** (red de la flota) · índice reescrito · capítulo 6 recolocado |
| `03_operacion/FLOTA.md`, `ARQUITECTURA.md`, `CLAUDE.md` | alineados |

### Pendiente

- 🔴 `/etc/fstab` para cerrar la PSK legible (sudo del usuario)
- mDNS **por enlace**: `wlan0: no` mientras `Global: yes`
- Aislamiento de clientes del AP del aula — sin comprobar
- ⏳ **Namespace `/rvr_NN` o sin namespace**, que hay que fijar **antes** de la Fase 5


## 2026-08-01 — `ARQUITECTURA.md` contra el robot real: una errata era un fallo de seguridad

Al responder a *«¿cómo esperamos cambiar la comunicación para que ya no sea por SSH?»* salió que
el **contrato de topics para la web** ya no describía este robot.

### 🔴 La grave: el contrato decía que la web publica en `cmd_vel`

**Publicar ahí salta el `collision_monitor`.** `/cmd_vel` es la **salida** del monitor y tiene un
solo publicador; la cadena es `web → cmd_vel_raw → collision_monitor → cmd_vel → driver`.
Publicar en `/cmd_vel` **funciona** —el robot obedece— y por eso es peligroso: la Fase 5 lo habría
implementado tal cual y el robot habría conducido sin capa de seguridad.

### El resto de erratas

- `battery` → el topic real es **`battery_state`**.
- Faltaban `motor_status`, `encoders`, `color`, y —lo importante— los servicios **`/start_scan`**
  y `/stop_scan`. `/start_scan` es **obligatorio**: sin él el robot no obedece y parece averiado.
- No decía que `odom`, `imu`, `scan` y `color` son **BEST_EFFORT**. Un suscriptor con el perfil
  por defecto **no recibe nada**, sin error.
- La fila del **SSH** decía «solo ciclo de vida: arrancar/parar el stack». **Ya no hace falta**:
  `atriz-robot.service` levanta el robot al encender y se recupera solo. El SSH sale de la
  operación normal y queda para mantenimiento.

### ⏳ Y dos decisiones que NO se han tomado

Se marcan como pendientes en vez de resolverlas por cuenta propia — son de diseño y afectan al
cliente web, así que cambiarlas después obliga a tocar los 16 robots **y** el cliente:

1. **Namespace `/rvr_NN` o sin namespace.** El diseño decía `/rvr_NN`; el driver corre hoy sin él.
2. **El nombre canónico de la parada de emergencia** — el driver escucha los tres a propósito.

---

## 2026-08-01 — La imagen dorada, auditada contra el estado real

Petición del usuario: *«revisa qué tan completa está la imagen dorada para pasarse a otro
sphero»*. **Veredicto: funcionalmente casi completa, pero no se debe clonar todavía.**

### 🔴 Y lo primero es una corrección: la imagen SÍ llevaría el arranque automático

Este proyecto documentó —lo escribí yo— que «si se construye la imagen antes de añadir systemd a
`provision.sh`, los 16 robots saldrán **sin** arranque automático». **Es falso.** Un `dd` copia el
disco entero: `/usr/local/bin` y `/etc/systemd/system` viajan con él.

El problema real es otro y es peor de razonar: **la imagen y `provision.sh` divergirían**, y la
regla del proyecto dice que **gana el script**. Un robot reprovisionado desde cero saldría
distinto de uno clonado.

📝 Y hay una segunda divergencia más silenciosa: **`provision.sh` no clona `~/atriz_migracion`**,
así que un robot provisionado se queda sin `verificar_robot.sh` ni `fase_7_systemd.sh`.

### 🔴 Los tres bloqueantes

1. **`~/.git-credentials` con el PAT viaja en la imagen.** `fase_6` avisa pero no lo borra —
   deliberado, puede ser un token compartido. Repartir uno personal en 16 microSD es una decisión
   👤, y se suma a que la imagen ya lleva la PSK del WiFi.
2. **rosbridge no está instalado**, y la web habla por ahí. Clonar antes de la Fase 5 = clonar dos
   veces, ~300 MB por robot sobre la única AP.
3. **La divergencia con `provision.sh`.**

### 🔴 Y dos bombas de relojería en `fase_6`, arregladas hoy

**No borraba `/var/lib/atriz-first-boot.done`.** El servicio de personalización lleva
`ConditionPathExists=!` sobre esa marca: si el robot de referencia ejecuta first-boot **una sola
vez**, la marca viaja en la imagen y **los 16 clones se saltan la personalización entera** —
mismo hostname, mismo `ROS_DOMAIN_ID`, los 16 viéndose en DDS. Y **sin dar ningún error**.

📝 Hoy la marca no existe, así que la imagen de hoy estaría bien. Es una bomba de una sola línea.

**No borraba `/etc/profile.d/atriz-robot.sh`.** El clon arrancaría con el `ROS_DOMAIN_ID=1` del
robot de referencia hasta que first-boot lo pisara; si first-boot fallara, se quedaría ahí para
siempre. → Ahora se borran los dos: la identidad **solo** puede venir de first-boot, y si falta,
el envoltorio del servicio **se niega a arrancar**.

✅ Y `fase_6` avisa ahora de los tres bloqueantes **antes** del `dd`, cuando aún se pueden
arreglar.

Evidencia 38.

---

## 2026-08-01 — El piso blanco del LIDAR, y dos huecos encontrados de rebote

### ✅ Por qué el sensor de luz ve los LEDs del robot — la explicación es física

La aportó el usuario y cierra el hallazgo: el sensor de luz ambiente **mira hacia arriba**, y
encima del Sphero está el **piso que sostiene el LIDAR** —los 4.6 cm ya documentados en
`MEDIDAS_ROBOT.md`— que es **blanco**. Ese piso le devuelve la luz de los propios LEDs del robot.

📝 **No se podía deducir de los datos.** Los datos decían «ve los LEDs»; el *porqué* es una
observación del montaje. Mismo patrón que la inclinación del robot y el LED de los bajos: **hay
cosas que solo se saben mirando el hardware.**

🔴 **Decisión: `/ambient_light` no se usa.** Un valor alto significa «el robot tiene LEDs
encendidos», no «hay luz». Se probó solo para saber si responde, y responde. Se deja publicado
porque es gratis, pero ningún consumidor debe apoyarse en él. No se arregla con software y nada
del laboratorio lo necesita.

### 🔴 Y al meter los topics nuevos en el verificador salieron dos huecos de operación

**(a) `TRANSIENT_LOCAL` no garantiza que un suscriptor tardío reciba el último valor.** El driver
lo daba por hecho para `/motor_status` y `/battery_state` — lo escribí yo. Medido: un suscriptor
nuevo se quedaba **sin recibir nada en 10 s, 2 de cada 3 veces**, incluso en su propio proceso.
Con el sondeo cada 30 s, eso dejaba a la web **medio minuto a ciegas** sobre un fallo de motor.
→ Arreglado republicando a **1 Hz**: gratis, no toca el puerto serie, y no depende de esa
semántica. 3 de 3 pasadas estables después.

**(b) 🔴🔴 Si un nodo muere, systemd no se entera.** Lo destapó un `SyntaxError` mío: el driver
estuvo **cuatro minutos muerto** con el servicio en **`active (running)`**. El PID principal es el
`ros2 launch`, que sobrevive a la muerte de un nodo, así que `Restart=always` —estrenado ayer y
funcionando— **no cubre este caso**.

⚠️ Es el peor modo de fallo para un laboratorio remoto: un robot inservible que **desde fuera
parece sano**. Exactamente el mismo patrón que el RVR dormido con el nodo vivo.

→ Arreglado con **`on_exit=Shutdown()`** en el nodo del driver. Verificado matando solo ese nodo:
`NRestarts` 12→13 y el robot entero de vuelta en **25 s**. Solo en el driver: sin él no hay robot,
mientras que sin LIDAR se puede teleoperar.

⏳ **Sin decidir:** si el `collision_monitor` debe llevarlo también. Un robot sin capa de seguridad
que parece sano es peligroso.

### El verificador

Sección nueva para `/encoders`, `/ambient_light` y `/motor_status` — comprueba que **publiquen**,
no que existan. **94 comprobaciones, 0 fallos.** `/ambient_light` se comprueba por ritmo y **no
por valor**, a propósito: su número depende de qué LEDs estén encendidos.

Evidencia 37 · manual cap. 18.4.

---

## 2026-08-01 — Los dos sensores ópticos: funcionan, y son DOS

Petición del usuario: *«el sistema tiene problemas con los sensores de color y de luz ambiental,
puedes probarlos con detalle»*. **Los dos funcionan.** Los «problemas» eran el LED apagado por
defecto, dos montajes de prueba mal hechos, y **dos afirmaciones mías que resultaron falsas**.

### ✅ El sensor de color acierta los cinco

| superficie | `clear` | R/G | B/G | `/color` |
|---|---|---|---|---|
| suelo | 1275 | 0.546 | 0.413 | (255, 220, 209) |
| blanco | **2288** | 0.482 | 0.498 | (244, 235, 255) |
| rojo | 565 | **2.743** | 0.355 | **(255, 31, 43)** |
| azul | 396 | 0.447 | **0.856** | **(88, 120, 201)** |
| negro | **181** | 0.480 | 0.460 | (28, 27, 29) |

12.6× entre blanco y negro, los ratios se mueven en la dirección correcta, y `/color` acierta a
ojo los cinco. 🔴 La **confianza es 0** en todos, y no es el sensor: es el **clasificador**, que
necesita una **paleta** (`load_color_palette` existe en el SDK y no se usa).

### ✅ Y el de luz ambiente es OTRO sensor, en otro sitio

Lo dijo el usuario, y la medida lo confirmó: encender los 10 grupos de LED sube la luz de **1.76 a
23.55** (13.3×), mientras el RGBC da valores **idénticos** con los LEDs en rojo, verde o azul.
→ ⚠️ **`/ambient_light` no mide la luz de la sala**: la dominan los LEDs del propio robot.

### 🔴 Dos afirmaciones retiradas, las dos documentadas ese mismo día

**«`/ambient_light` da 0.0 sin `color_detection`»** — falso. Las lecturas de 0.0 se tomaron **con
el robot sin levantar de verdad**, y el usuario lo confirmó *después*. → **Si tu medida depende de
que alguien haga algo físico, pregunta si lo hizo antes de concluir.**

**«cada reinicio del driver degrada el stream»** — falso. Era el **apagado limpio apagando los
LEDs**, como propuso el usuario. Su hipótesis descartó la mía.

### 🔴 Y dos montajes que daban resultados imposibles

- Deslizar el papel sin comprobar que tapa la ventana: el «blanco» dio **exactamente** los mismos
  números que la referencia. **Idéntico no es parecido: es la señal de que no cambiaste nada.**
- **Pegar el objeto contra la ventana tapa también el LED**: el blanco daba `clear=261` y el negro
  795, al revés de lo físicamente posible.

→ El protocolo que sí funciona lo propuso el usuario: **una superficie por vez, colocada y
confirmada antes de medir**. Con él salieron los cinco a la primera.

Evidencia 37 · manual cap. 18.4.

---

## 2026-08-01 — LEDs, luz ambiente y encoders: tres bugs que solo salen mirando el robot

El usuario pidió *«prueba todos los leds para ver si hay comunicación todavía»*. Los 12 grupos
devolvieron `success=True`. **Y dos no se encendieron.**

### 🔴 `led_group` es una máscara de bits, y `set_all_leds` quiere un brillo POR BIT

Los 10 grupos normales tienen **3 bits** (R, G, B), `all_lights` tiene **30** y
`undercarriage_white` **1**. El driver mandaba **siempre tres**: para los 10 acierta, y a los
otros dos el RVR les dice que sí y no hace nada.

📝 **Lo encontró el ojo del usuario, no el código:** *«no vi los bajos ni tampoco todos»*. Sin
eso, los doce ✅ del script habrían pasado por buenos. Arreglado contando bits; los tres
servicios de LED comparten ahora la misma regla, y el usuario confirmó ver `all_lights`.

### ✅ `/encoders` y `/ambient_light`, con dos bugs de camino

Las claves del stream son **`LeftTicks`/`RightTicks`**, no `Left`/`Right` — **la tabla de
documentación del propio SDK dice otra cosa que el payload**. Con las claves malas el handler
lanzaba `KeyError` y el topic quedaba registrado con **cero mensajes**: el síntoma exacto de un
RVR dormido. Y los ticks vienen **sin signo en 32 bits**: un retroceso llega como `4294965940`,
que son **−1356**.

Medido después: `/odom` 16.58 · `/imu` 16.57 · `/encoders` 16.57 · `/ambient_light` 13.06 Hz.
**Añadir dos sensores al stream no le cuesta ritmo a `/odom`.**

### 🔴 `/ambient_light` da 0.0 si el sensor de color está apagado

**0.0 constante** con `color_detection=false` — incluso con el robot **levantado** (247 muestras)
y por las dos vías, stream y consulta directa. Con `color_detection:=true`: **2.497**. Comparten
óptica. Es la misma trampa que dejó `/color` en `[0,0,0]` durante meses: el topic existe, el
ritmo es correcto, y el dato es un cero. El driver ahora lo avisa por el log.

✅ **Y eso contesta lo del LED de los bajos:** lo enciende `enable_color_detection`, **no** el
grupo `undercarriage_white` del SDK.

### 🔴 Una conclusión retirada, y grave: «un comando de LED mata la telemetría»

Durante un buen rato esta sesión creyó haber encontrado un fallo serio: tras cualquier comando de
LED, `/odom`, `/encoders` y la luz caían a **0.0 Hz**. Se llegó a **aislar** quitando los dos
sensores nuevos, seguía pasando, y se concluyó *«es preexistente»* — lo cual habría significado
que la web no puede encender un faro sin cegar al robot.

**Era falso. El fallo estaba en el instrumento.** El script mezclaba
`rclpy.spin_until_future_complete(nodo, f)` con un `SingleThreadedExecutor` que ya tenía ese
nodo: el nodo deja de ser atendido y **mis** suscripciones se callan. Con el ejecutor bien usado:
16.9 → 16.6 → 16.6 → 16.5 Hz. **El robot no había dejado de publicar ni un mensaje.**

Van **cuatro** veces que el instrumento miente en este proyecto. Ante una medida rara, sospecha
del medidor.

📝 Contribuyó un bug propio: `_avisar_una_vez` se apoyaba en `_recibidos`, que `_quiza_publicar`
**vacía en cada ciclo de `/odom`** — así que un aviso «una sola vez» salía **13 veces por
segundo** desde el hilo de asyncio.

### 🔴 Seis veces el mismo error de `colcon`, y por fin un arreglo

«Summary: 0 packages finished» no compila nada y no parece un error; lo siguiente es reiniciar el
nodo y leer un log del código viejo. Pasó **seis veces en esta sesión**, ya documentado. Y creó
un **workspace parásito** en `src/Atriz_rvr/build`, borrado.

→ Un aviso que se ignora seis veces no es un aviso: es una tarea pendiente. Ahora hay
**`scripts/compilar.sh`**, que se sitúa solo en la raíz, comprueba que compiló algo y detecta el
parásito. Probado a propósito desde el directorio malo: funciona, y encontró el parásito a la
primera.

### ⏳ Abierto

`/color` sigue publicando `(0,0,0)` **con la luz encendida** (166 mensajes). No se investigó y no
se da por bueno — hay que mirar `confidence` y contrastar el servicio contra el topic. Evidencia
36, sección 6.

---

## 2026-07-31 — «¿Está todo el Sphero en ROS?» — No: 27 de 94

Pregunta del usuario al cerrar el día. Se comprobó en vez de darla por buena, y la respuesta
cambia lo que va primero en la próxima sesión.

### Los números

`SpheroRvrAsync` expone **94 métodos públicos**. El driver usa **27**.

### Frente al driver de ROS 1 estamos casi completos… pero no del todo

Tenía 20 servicios; hay **18**, más **cuatro piezas que ROS 1 no tenía** (`set_leds`,
`trigger_led_event`, `set_pos_and_yaw`, y `battery_state` pasó de servicio a **topic**).

🔴 **Pero quedan cuatro huecos sin equivalente**, y el inventario que el propio driver llevaba
en un comentario **no los mencionaba** — decía «16 servicios pendientes», de los que 14 se
portaron esa misma tarde, y se quedó ahí:

- **`reset_odom`** — el locator se resetea al arrancar y **no hay forma de repetirlo en
  caliente**. La web lo va a pedir entre estudiantes. ⚠️ Y al implementarlo hay que decidir y
  **medir** si se re-fija también `yaw₀`: `reset_locator_x_and_y()` **realinea el marco**, no
  solo pone la posición a cero.
- **`ambient_light`** — el SDK lo expone, el sensor está verificado, y no llega a ROS.
- **Recibir IR** — se puede **enviar** pero no recibir, y el tipo de mensaje **ya está definido**
  en `atriz_rvr_msgs` sin que nadie lo publique.
- **Topic `encoders`** — hay servicio, falta el flujo continuo. Son la única fuente que no
  depende del marco de referencia.

Cuatro más están diferidos **a propósito**, cada uno con su razón medida
(`configure_streaming`/`start_streaming`, `enable_color`, `cmd_degrees`, `ir_messages`).

### 🔴 Y lo que más valor tendría no estaba ni en la lista

De los 67 métodos que no llegan a ROS, los que cambian la operación de un laboratorio remoto:

**`motor_stall_notify` y `motor_fault_notify`.** Hoy **un robot con una oruga trabada se ve
exactamente igual que uno que navega mal**. Con 16 robots en otro edificio, esa diferencia es la
que decide si alguien tiene que ir hasta allí.

También: `on_will_sleep_notify` (el RVR **avisa** antes de dormirse — el proyecto lo resolvió con
un keepalive y un detector de silencio), protección térmica de motores, magnetómetro, temperatura
y tensión de batería en voltios (que es lo que haría viable medir el consumo del lidar, pendiente
desde la evidencia 30).

### Lo que sí se puede afirmar

✅ «Todo lo que el laboratorio usaba en ROS 1 está en ROS 2», menos esos cuatro huecos y con
cuatro piezas nuevas. 🔴 **No** «está todo lo que el Sphero puede hacer».

Plan y costes en `00_auditoria/evidencia_24_04/34_que_falta_del_sphero.txt`. Los cuatro huecos son
trabajo de **rclpy**, no de averiguar si el hardware responde: los sensores están verificados
desde el 2026-07-30.

📝 Batería al cerrar la sesión: **26 %** (45 % tras la prueba de Nav2, 34 % al cerrar la parada
de emergencia). El servicio se dejó parado.

---

## 2026-07-31 — Revisión de alineación: la documentación contra el sistema real

Petición: *«revisa que todo lo realizado ahora esté alineado»*. No bastaba con releer — se
contrastó cada afirmación contra el sistema en marcha y contra los ficheros de configuración.

### Afirmaciones vigentes que habían dejado de ser ciertas

`TRASPASO` seguía listando «sin arranque automático — ninguna unidad systemd ⏳ pendiente»
(resuelto hacía una hora). Los conteos del verificador estaban en **84/76** en cuatro ficheros.
`CLAUDE.md` decía «tres fallos propios» cuando iban seis. `INSTALACION` decía «etapas A a F22».
Y `scripts/README` marcaba `fase_7_systemd.sh` como *«probado en seco, nunca se ha arrancado»*
después de haberlo arrancado con un reinicio real.

🔴 **Y una contradicción directa entre dos ficheros:** `fase_1_higiene_so.sh` se declaraba
**NO VERIFICADO en 24.04** mientras su propio `README` decía **✅ ejecutado y verificado**. Se
comprobó en el sistema —governor `performance`, `multi-user.target`, `iw` con power_save `off`,
netplan en 600, arranque de userspace en 16.6 s contra 1 min 39 s— y la razón la tenía el README.

### Dos comprobaciones que parecen fallar y no fallan

Al verificar lo anterior salieron dos trampas nuevas, las dos capaces de hacer creer que la
higiene del SO no funcionó:

- **`systemctl is-enabled cloud-init` dice `enabled`** — se desactiva con el **fichero**
  `/etc/cloud/cloud-init.disabled`, no con systemctl. Las tres unidades están `inactive`.
- **`ps -e | wc -l` da 166 contra el objetivo «< 120»** — pero **86 de esas tareas son de
  `atriz-robot.service`**: el SO solo tiene **80**. Y el objetivo estaba mal planteado de todos
  modos: `ps -e` cuenta ~123 hilos de kernel.

### 🔴 Y el verificador tenía DOS fallos más — van ocho

Los creó el trabajo del propio día, y los dos daban **FALLO sobre un robot recién arrancado y
sano**:

**7 · «el LIDAR no publica» sobre el estado NORMAL del robot.** Cierto que `/scan` daba 0: el
barrido **arranca parado a propósito**. El verificador declaraba roto el reposo. → Ahora, con
`--hardware`, lo **enciende, mide y lo deja como estaba**.

**8 · Contar un comentario como si fuera un ajuste. Otra vez.** Al quitar
`export ROS_DOMAIN_ID=1` del `.bashrc` se dejó un comentario explicando por qué ya no está, y el
`grep -q 'ROS_DOMAIN_ID'` casaba con él: **fallaba justo después de arreglar el problema**. Es el
mismo error que el fallo nº2, repetido a las pocas horas. → Anclado a
`^[[:space:]]*export[[:space:]]+ROS_DOMAIN_ID=`.

### El `.bashrc`, limpiado

`ROS_DOMAIN_ID` y `RMW_IMPLEMENTATION` vivían **en el `.bashrc` y en `/etc/profile.d`**. El
`.bashrc` se lee después y gana, así que un clon de la imagen dorada se habría quedado en el
dominio 1 fuera cual fuera su `robot_id` — la trampa que el propio bloque avisaba. Quitados del
`.bashrc`; los tres tipos de shell siguen dando 1, ahora desde **una sola fuente**.

### Valores contra la configuración real

`robot_radius` 0.145, `desired_linear_vel` 0.40, `radius` 0.18, `base_length` 0.182,
`base_width` 0.217, `laser_z` 0.155, `support_motor_dtr` true — **todos coinciden**. Solo falló
un comentario dentro de `collision_monitor.yaml`, que citaba un `robot_radius: 0.11` corregido a
0.145 ese mismo día.

### Estado final

**91 comprobaciones con `--hardware`** (89 sin él), **0 fallos**. El único aviso que queda es
real: los `.bak` de apt.

---

## 2026-07-31 — Barrido documental: llevar lo de hoy a los sitios donde se busca

Todo lo de esta sesión estaba en el manual, el CHANGELOG y las evidencias. **No estaba donde lo
buscaría alguien que solo quiere operar el robot.** Ocho ficheros corregidos.

### Lo más grave: el RUNBOOK decía cómo arrancar el robot, y ya no era así

Decía *«no hay arranque automático, hay que hacerlo a mano»* y su sección de parada de
emergencia seguía siendo de **ROS 1** (`rostopic`, `rosparam`), afirmando cosas ya arregladas.
Reescritas las dos, más una sección nueva —**«el robot no conduce pero todo lo demás va»**— que
es el síntoma que va a producir el nuevo diseño y que sin explicación parece una avería.

### `medir.py` estaba roto y aun así se recomendaba

Es de ROS 1: muere con `ModuleNotFoundError: rospy`. Seguía en `CLAUDE.md` y en el RUNBOOK como
herramienta de diagnóstico. **Una herramienta rota que se recomienda es peor que ninguna.**
Portada como `medir_ritmo_ros2.py`… y de paso volvió a morder lo mismo:

🔴 **Mi primera versión daba 15.03 Hz mientras su propio intervalo medio decía 60.4 ms** (=16.55).
La diferencia era el descubrimiento de DDS metido en el denominador. Con el ritmo calculado
desde los intervalos: **16.54 Hz**. Van **tres** formas distintas de medir mal una frecuencia en
este proyecto —`ros2 topic hz` (QoS), `spin_once` en bucle (pierde mensajes) y `mensajes/duración`
(descubrimiento)— y las tres dan números **bajos** sobre un robot sano.

### El repositorio del robot describía otro software

`README.md` y `CHANGELOG.md` de `Atriz_rvr` eran **enteros de ROS 1**: catkin, `/cmd_degrees` y
**5 servicios cuando hay 18**. Se conservan —documentan Noetic, que es la ruta de vuelta atrás—
pero ahora lo dicen en la primera línea, y encima llevan una referencia ROS 2 con lo que de
verdad corre. La lista de servicios se sacó **del código**, no de memoria.

### Y una afirmación sobre la web que hoy dejó de ser cierta

`28_pendiente_web.txt` decía que la parada de emergencia «no corta lo que venga de Nav2». Ya sí.
Y se le añadió lo que la Fase 5 **tendrá que** implementar:

🔴 **La web tendrá que llamar a `/start_scan` al empezar cada sesión.** Los robots arrancan solos
pero con el barrido parado, y sin `/scan` el `collision_monitor` bloquea el movimiento. Un robot
recién encendido **no obedece `cmd_vel`**, y desde la web se verá exactamente igual que uno
averiado. Es una línea de código, pero hay que saberla.

### El resto

`README.md` (el estado decía que el siguiente paso era caracterizar la deriva, hecho hace
horas), `INSTALACION.md` (la lista de pendientes repetía «systemd» **tres veces**),
`FLOTA.md`, `RECUPERACION.md` —con un **rescate de un comando** si el arranque automático da
problemas, y la nota de que el SSH no depende de él— y `CLAUDE.md`.

---

## 2026-07-31 — El robot se levanta solo al encender ✅

La prueba que justifica que exista `atriz-robot.service`: en un laboratorio remoto nadie puede
entrar a arrancar un proceso.

```
uptime                  1 min
Active: active (running) since 14:59:28
Main PID: 711 (ros2)                     <- del arranque, no de una mano
ExecStartPost=atriz-escaneo off          status=0/SUCCESS
systemd-analyze         5.5s kernel + 16.6s userspace
```

Y arrancó **en el estado correcto**, comprobado por efecto: `/scan` a **0.00 Hz**, `/odom` a
**16.49 Hz**, `/cmd_vel` con un solo publicador, `collision_monitor` en `active [3]`, y el
`ROS_DOMAIN_ID` viniendo de `/etc/profile.d` —no del `~/.bashrc`, que systemd no lee.

### La afirmación que sostiene el diseño, medida con control

Arrancar con el lidar parado solo es aceptable si el robot **no puede moverse** así:

| barrido | mismo comando por `/cmd_vel_raw` | desplazamiento |
|---|---|---|
| **apagado** | 0.10 m/s · 1.5 s | **0.0 cm** ✅ |
| **encendido** (control) | 0.10 m/s · 1.0 s | **9.9 cm** |

🔴 Sin el control, «0.0 cm» es indistinguible de un `cmd_vel` que nunca llegó.

📝 Corroboración accidental: una primera pasada del control falló por un bug de la herramienta
—esperaba `/odom` 2 s fijos y llegó a los 2.5— pero el robot **sí ejecutó** el comando, y se ve
en la pasada buena: la posición de partida era +0.092 m. Dos medidas del mismo efecto.

### 📝 Lo que NO se ha ejercitado, y no se va a presentar como si sí

- **La espera de puertos del envoltorio nunca ha llegado a esperar**: las tres veces `tras 0s`,
  también en frío. Red de seguridad **sin estrenar**.
- **`Restart=always` tampoco.** Y no arregla el fallo típico de este robot: el RVR dormido deja
  el proceso vivo.
- **n=1.** Un reinicio. Sin corte de corriente ni arranque con el hardware desconectado.

### El coste: cinco fallos, ninguno visible leyendo el código

Dos los cazaron `systemd-analyze verify` y `env -i` antes de instalar. Los otros tres solo
aparecieron al arrancarlo de verdad, y el peor fue **arreglar un fallo en un fichero y no
buscarlo en su hermano**: el `ExecStartPost` murió con `status=1/FAILURE` dejando el servicio
`active (running)` y el barrido **encendido** — el estado exacto que existía para evitar.

Batería al terminar: 34 %. Evidencia 33 · manual cap. 17.

---

## 2026-07-31 — systemd arrancado de verdad: cinco fallos que solo salen al ejecutar

El servicio quedó instalado, habilitado y **arrancado**, y comprobado por efecto:

```
Active: active (running)
ExecStartPost=/usr/local/bin/atriz-escaneo off   status=0/SUCCESS  (10 s)
/scan    0.00 Hz   · barrido parado, que es lo que se pedía
/odom   16.54 Hz   · el robot vive, a la frecuencia de referencia
/cmd_vel Publisher count: 1   · la capa de seguridad intacta
```

### Los cinco fallos, y el patrón que los une

**1 y 2 · antes de instalar** (`systemd-analyze verify` y `env -i`): `StartLimitIntervalSec` en
`[Service]` se ignora, y los `setup.bash` de ROS no son compatibles con `set -u`.

**3 · en el primer arranque real.** El mismo `set -u` **en el script hermano**, que se arregló
en `atriz-robot.sh` y no se buscó en `atriz-escaneo.sh`. El `ExecStartPost` murió con
`status=1/FAILURE`, el servicio quedó `active (running)` gracias al `-` de la unidad, y **el
barrido se quedó encendido** — exactamente el estado que ese `ExecStartPost` existía para evitar.

**4 y 5 · al arreglar el 3.** `ros2 topic echo /scan` se suscribe RELIABLE mientras `/scan` es
BEST_EFFORT (decía «apagado» con el LIDAR a 8 Hz); y ni con `--qos-reliability best_effort`,
porque con `--no-daemon` tiene que **descubrir el tipo** del topic y falla **2 de cada 3 veces**.
Reescrito como suscriptor propio: el tipo se dice, no se descubre. 3 de 3 en los dos estados.

🔴 **El patrón, que es lo que hay que llevarse:** arreglar un fallo en un fichero y **no buscarlo
en sus hermanos**. Costó el único paso que este diseño tenía que garantizar.

### Y un aviso engañoso, también corregido

Al reinstalar sobre un robot ya arrancado, el paso 2/5 señalaba al driver **del propio servicio**
como si fuera un lanzamiento a mano. Ahora se distingue por el cgroup. Un aviso que asusta sin
motivo se acaba ignorando igual que un fallo falso.

### ⏳ Falta

**El `sudo reboot`** — lo único que demuestra que un robot remoto se recupera solo, que es el
motivo por el que existe todo esto. Y añadirlo a `provision.sh` cuando se cierre el robot de
referencia.

Manual, cap. 17.

---

## 2026-07-31 — La parada de emergencia, verificada con control. Y el verificador mentía tres veces

### ✅ El agujero de la parada de emergencia, tapado y demostrado

Stack completo (driver + LIDAR + SLAM + Nav2), los cinco nodos de Nav2 en `active [3]` y
`/cmd_vel` con **un solo publicador**. Mismo protocolo en las dos condiciones:

| | objetivo tras la parada | movimiento al liberar |
|---|---|---|
| **con** `cancelar_nav2` | **CANCELED** | **0.0 cm** ✅ |
| **sin** él (control) | sigue **ACTIVO** | **34.7 cm** 🔴 arrancó solo |

🔴 **El control es la mitad que importa.** La primera pasada sola solo demuestra que el robot se
quedó quieto, no que lo consiga el arreglo. Con el control quedan cuatro medidas de acuerdo en
dos parejas opuestas — y el estado del objetivo lo da el propio action server, no una inferencia.

📝 n=1 por condición, y se acepta: el fenómeno **no es intermitente**, es determinista y trazado
en código. La regla de «replica antes de atribuir» se escribió para el fallo de SLAM, que sí lo
era (~21 %).

### 🔴 Y el verificador tenía TRES fallos más — van seis

Los tres daban veredictos **falsos sobre un robot sano**, que es lo peor que puede hacer un
verificador: uno con falsos positivos se acaba ignorando.

**4 · «el RVR está dormido» con el robot apagado.** La comprobación se guardaba con
`ros2 topic list | grep -qx '/odom'`, y **el daemon de ROS conserva topics de nodos muertos**. →
Mirar el **proceso**, no la lista.

**5 · `ros2 topic hz` no puede medir `/odom`. Nunca pudo.** `/odom` se publica **BEST_EFFORT** y
`ros2 topic hz` se suscribe RELIABLE **sin opción de cambiarlo** en Jazzy: DDS no empareja y da
0 Hz siempre. La misma trampa de QoS que costó la parada de emergencia, esta vez dentro del
verificador. Pasaba desapercibida porque el bloque solo corría si `/odom` aparecía en la lista, y
con el driver parado no aparecía: **una comprobación muerta que contaba como aprobada**.

**6 · Y mi primer arreglo también medía mal: 11.3 Hz sobre un robot a 16.5.** La comprobación
*pasaba* (el umbral es >10), así que habría llevado a «arreglar» un driver sano, a tocar
`streaming_interval_ms` o a documentar una degradación inexistente. Se salvó por comparar contra
el valor de referencia medido — que es exactamente para lo que existe esa tabla.

La causa: **`rclpy.spin_once(nodo, …)` en bucle pierde mensajes**, porque cada llamada engancha y
desengancha el nodo del ejecutor global. Con un `SingleThreadedExecutor` persistente el mismo
robot da **16.53 Hz**, intervalo 60.0 ms de mediana, σ 2.2 ms — o sea la referencia del proyecto,
intacta.

→ La regla, con dos ejemplos nuevos: comprobar el efecto y no la intención, y además
**comprobar el instrumento antes que la medida**.

### Estado del verificador

**86 comprobaciones con `--hardware`** (80 sin él), 0 fallos, 3 avisos — los tres reales: los
`.bak` de apt y las dos cosas de systemd, sin instalar a propósito.

Evidencia: `31_parada_cancela_nav2.txt` y `32_verificador_dos_fallos_mas.txt` · manual cap. 15.4.

---

## 2026-07-31 — La parada de emergencia: la cuarta causa, y estaba mal enunciada

En la lista de pendientes ponía *«la parada no cancela las acciones de Nav2, solo para los
motores»*. **Ese enunciado era falso.** El driver pone una bandera y `_cb_cmd_vel` descarta todo
lo que llega, así que con Nav2 mandando a 10 Hz el robot **sí se queda quieto**.

🔴 **El agujero estaba al LIBERAR.** `/release_emergency_stop` solo baja la bandera. El objetivo
de Nav2 seguía vivo, el `controller_server` nunca dejó de publicar, y no aborta enseguida porque
el progress checker está relajado a 0.25 m en 15 s a propósito. → **En el instante en que la
bandera baja, el robot arrancaba solo**, sin que nadie mandara nada. Que es lo contrario de lo
que debe hacer una parada de emergencia.

📝 Y encaja con el historial: esta función ya había fallado **tres** veces, siempre en silencio y
siempre devolviendo `200 OK` (nombre del topic, namespace, QoS). Esta es la cuarta, y también es
muda.

### El arreglo

Nodo nuevo `cancelar_nav2`, arrancado por `nav2.launch.py`. Llama a `_action/cancel_goal` con un
`CancelGoal.Request` **vacío**, que en `action_msgs` significa **CANCEL_ALL** — así no hay que
seguir la pista de handles que lanzó otro proceso (la web, RViz2, un script).

Va **aparte y no dentro del driver** porque el driver tiene que funcionar sin Nav2. QoS
**VOLATILE** en el suscriptor, no `TRANSIENT_LOCAL`: en un suscriptor no añade garantías, solo
exige que el publicador también lo sea — fue la tercera causa del fallo silencioso.

### Verificado sin mover el robot

El nodo recibe por `/rvr/emergency_stop` —el nombre absoluto que usa la web y que fallaba en
ROS 1— y sin Nav2 degrada bien. Eso cubre las causas 2 y 3. Compilado y comprobado el **efecto**:
el ejecutable instalado existe y el launch instalado lo contiene, sin workspace parásito.

### ⏳ Falta la prueba que importa

**NO VERIFICADO con Nav2 navegando.** Herramienta escrita y lista:
`mediciones_banco/medir_parada_nav2.py`. Necesita ~2.5 m despejados y mide **desplazamiento**,
no velocidad — un robot que arranca y frena da velocidad media ~0 y se ha movido 20 cm, que es
el error que ya se cometió midiendo el watchdog.

Manual, cap. 15.4 · evidencia `00_auditoria/evidencia_24_04/31_parada_cancela_nav2.txt`.

---

## 2026-07-31 — Arranque automático con systemd (escrito, sin arrancar todavía)

En un laboratorio remoto nadie puede entrar a arrancar un proceso: si un robot se reinicia
tiene que volver solo. Escritos `atriz-robot.service`, el envoltorio `atriz-robot.sh`, el
ayudante `atriz-escaneo` y el instalador `fase_7_systemd.sh`.

📝 **NO VERIFICADO de extremo a extremo:** el servicio nunca se ha arrancado bajo systemd.
Instalarlo requiere `sudo`. Lo que sí se ejecutó está abajo.

### Por qué hace falta un envoltorio y no un `ExecStart`

systemd no ejecuta un shell de login: no lee `~/.bashrc` ni `/etc/profile.d`. Un `ExecStart`
directo arrancaría **sin `ROS_DOMAIN_ID`**, o sea con los 16 robots en el dominio 0 viéndose
entre sí — la decisión D1 de `ARQUITECTURA.md` rota, sin ningún error. El envoltorio carga el
entorno, **se niega a arrancar si falta `ROS_DOMAIN_ID`**, espera a udev y hace `exec`.

### El robot arrancará con el barrido del LIDAR apagado

Consecuencia directa de lo medido hoy (11.8 vs 2.7 Hz): sin esto el arranque automático dejaría
el X2 a 11.8 Hz permanentes en los 16 robots. La unidad llama a `atriz-escaneo off` en su
`ExecStartPost`.

⚠️ Y hay que saberlo: **un robot recién arrancado no conduce**. No está roto — sin `/scan` el
`collision_monitor` bloquea el movimiento. Se activa con `atriz-escaneo on`.

### 🔴 Dos fallos que solo aparecieron al ejecutar

Los dos habrían fallado en el primer reinicio, con mensajes que no mencionan ni ROS ni systemd:

- **`StartLimitIntervalSec` en `[Service]` se ignora** — va en `[Unit]`. Lo dijo
  `systemd-analyze verify`. Efecto: bucle de reinicio **sin tope**.
- **Los `setup.bash` de ROS no son compatibles con `set -u`**:
  `AMENT_TRACE_SETUP_FILES: unbound variable`. Con `set -euo pipefail` mata el envoltorio antes
  de arrancar nada. Salió de ejecutarlo con `env -i`; leyéndolo no se ve.

Y un tercero, del propio instalador: creaba el fichero de identidad **durante la fase de
comprobación**, antes de decidir si instalaba, y en simulación el `> /dev/null` se tragaba su
propio aviso. Los dos corregidos.

### Ejecutado y comprobado

- `bash -n` en los tres scripts.
- `systemd-analyze verify` sobre la unidad: limpio tras mover las dos directivas.
- El envoltorio, con `env -i`: **se niega** sin `ROS_DOMAIN_ID` (código 1), y con él recorre
  todo —entorno, RMW, espera de `/dev/rvr` y `/dev/ydlidar`— hasta el `exec`.
- `fase_7_systemd.sh --simular --id 1`: recorre los cinco pasos.

### ⏳ Abierto

**`provision.sh` no instala esto todavía**, así que la imagen dorada saldría sin arranque
automático. Está sin hacer a propósito: mientras se desarrolla en el robot de referencia, un
servicio levantado pelearía por `/dev/rvr` con las pruebas a mano. Es una decisión del usuario.

Manual, cap. 17.

---

## 2026-07-31 — El lidar gira siempre: qué se puede hacer y qué no

Pregunta del usuario, al oír el robot: *«el lidar siempre está girando nada más encender el
sistema. Solo va más rápido cuando se usa. ¿No se ahorraría si girara solo cuando hace falta?»*

### La observación era correcta, y tiene un mecanismo

**DTR no enciende el motor del X2: elige su velocidad.** Medido alternando cada 12 s sin cerrar
el puerto entre tramos —cerrarlo reinicia las líneas de control y falsea la medida—:

| línea | giro (5 tramos) | checksums |
|---|---|---|
| `DTR=1` | 11.86 · 11.77 · 11.85 · 11.85 · 11.76 Hz | 99.8 % |
| `DTR=0` | 2.66 · 2.74 · 2.73 · 2.63 · 2.74 Hz | 99.8–100 % |

**4.3×**, diez tramos, ninguno fuera de sitio. ✅ Y **confirmado por oído**: el usuario escuchó
los dos minutos y reportó «cambio claro cada ~12 s». Dos vías de verdad independientes —una
mecánica, otra el contenido de las tramas— que es lo que este proyecto aprendió a exigir tras
el «confirmado por tres vías» que era una sola.

Además aparecieron `/stop_scan` y `/start_scan`, dos servicios del driver que no estaban
documentados aquí. Verificados en ROS (11.81 → 0.00 → 13.44 Hz) **y por oído**, que es lo que
demuestra que frenan el motor y no solo callan el topic.

### Y el usuario tenía razón en la objeción

*«Entonces simplemente son los estados de cuando el robot se enciende y cuando está escaneando,
o sea que no aporta nada.»* Exacto. **`/stop_scan` no baja de 2.7 Hz**: llega al mismo reposo al
que llega solo el lidar cuando no hay driver. Hoy, con el robot apagándose entre sesiones, no
hay nada que ahorrar — el salto grande ya ocurre solo. Y pararlo del todo no está en la mano del
software: el láser y la electrónica siguen alimentados mientras haya 5 V, y la Pi 4 no puede
cortar VBUS.

### 🔴 Dónde sí importa: el arranque automático, que es lo siguiente

En cuanto los 16 robots levanten `robot.launch.py` solos al encender, el lidar pasará a
**11.8 Hz permanentes, 24/7, en los 16**. Sería *peor* que ahora, y habría llegado como efecto
secundario de una tarea que no habla de lidares. → Las unidades systemd arrancarán con el
escaneo **parado**. La seguridad encaja sola: sin `/scan` el `collision_monitor` no deja
conducir, y eso ya estaba verificado.

### 🔴 Una medida retirada, y la regla que deja

Para saber si `/stop_scan` bajaba DTR se abrió un segundo descriptor sobre el tty y se hizo
`TIOCMGET`: daba `DTR=1` en los dos estados → «no toca el motor». **Falso.** Al validar el
lector poniendo `DTR=0` a propósito seguía diciendo `1`: no solo mentía, **además perturbaba el
estado que medía**, porque `open()` sobre un tty vuelve a levantar la línea.

→ **Antes de creerte un instrumento, pon el sistema en un estado que conozcas y comprueba que
el instrumento lo ve.** Dos minutos, y evitó documentar lo contrario de lo que pasa. El eslabón
se cerró con el oído del usuario, que no toca el puerto serie.

### ⏳ Sin medir, a propósito

**Cuánta corriente se ahorra entre 11.8 y 2.7 Hz: NO MEDIDO.** Serían horas de robot con
`/battery_state` para un número que solo matiza el systemd. Decisión del usuario: documentar y
seguir. No se estima de la ficha — la del RVR ya mintió en las tres dimensiones del robot.

📝 Y un coste que no es eléctrico y puede pesar más: el X2 gira **desde que se enciende la Pi
hasta que se apaga**, siempre. Desgaste de rodamiento continuo en 16 unidades; es el argumento
más fuerte para un interruptor físico en los 5 V.

Evidencia: `00_auditoria/evidencia_24_04/30_lidar_giro_dtr.txt` · manual, cap. 8.4a.

---

## 2026-07-31 — Una suposición aceptada a propósito: `provision.sh` sin probar entero

Cierre del día. `provision.sh` gana hoy la instalación de Nav2 y el verificador sube a 84
comprobaciones, pero **el script nunca se ha ejecutado de principio a fin sobre un Ubuntu
24.04 limpio** — haría falta reflashear rvr-01, que es el único robot montado.

**Decisión del usuario: no se reflashea.** Se asume que funciona hasta tener una tarjeta de
repuesto. Es razonable, y por eso mismo va escrita: la regla 2 del proyecto dice que nada se
documenta sin ejecutarse, así que una excepción consciente se registra en lugar de disolverse.

### Lo que sí se pudo verificar sin reflashear

`bash provision.sh --simular` recorre las nueve secciones y sale con **código 0**. Eso descarta
errores de sintaxis y de lógica en todo el camino. Y el bloque añadido hoy —la comprobación de
los binarios de Nav2— **no se simula**: se ejecuta de verdad, y pasan los cuatro
(`collision_monitor`, `map_server`, `amcl`, `controller_server`). La idempotencia también
responde: reconoce lo ya instalado en vez de repetirlo.

De paso salió un defecto cosmético: las secciones decían «2/7 … 6/7» y luego «7/8, 8/8».
Corregido a `0/8 … 8/8`.

### Lo que sigue sin verificar, que es lo que importa

La simulación convierte en no-operación **justo los pasos que instalan y compilan**: el
`full-upgrade`, el arreglo del UART, la higiene del SO, el `apt install`, compilar YDLidar-SDK
y el `colcon build`. De una pasada limpia no se ha probado **nada** de eso.

🔴 **Consecuencia operativa:** la regla «la imagen dorada es el atajo, `provision.sh` es la
verdad» **supone que el script funciona**, y esa suposición es la que está sin comprobar. El
riesgo no es que falle: es que falle en el robot 7 de 16, con seis ya desplegados.

Marcado en `CLAUDE.md`, `TRASPASO.md`, `INSTALACION.md` y —donde más falta hace— al principio
de `03_operacion/FLOTA.md`, que es la guía que construye la imagen. Detalle en
`00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.

**Se levanta** cuando haya una microSD de repuesto, o cuando rvr-01 deje de ser el único robot.

---

## 2026-07-31 — Barrido de deriva documental, y qué le falta al repositorio web

Cierre de la sesión: revisar que la documentación **no siga afirmando lo que hoy ha dejado de
ser cierto**, y dejar por escrito lo que afecta al tercer repositorio.

### Ocho afirmaciones obsoletas, corregidas

Lo de hoy cambió valores que estaban repetidos por varios ficheros:

| | decía | dice |
|---|---|---|
| plano del LIDAR | 17.45 / 17.5 cm | **15.5 cm** ✅ medido |
| media longitud del chasis | 0.109 m | **0.091 m** |
| el verificador | 50 comprobaciones / 48 aserciones | **84** |

Corregidas en `README.md`, `scripts/README.md`, `RUNBOOK.md`, `INSTALACION.md`, `TRASPASO.md`,
`CLAUDE.md`, `mediciones_banco/README.md` y el manual (dos sitios).

📝 **El `CHANGELOG` no se reescribe**: es el registro de lo que se creía cada día. Donde una
entrada antigua da un valor que luego cambió, se **anota** al lado en vez de falsearla. Y las
derivaciones que resultaron erróneas —como la suma que daba 17.45— **se conservan con su nota**,
porque explican la causa raíz: dos de sus tres sumandos venían de la ficha del fabricante.

### 📌 El tercer repositorio: `Atriz_web_server`

**No está clonado en este robot ni se ha tocado**, y es deliberado: la web es la **Fase 5** por
decisión del usuario, y es un repositorio **público con una credencial expuesta** — meterse ahí
antes de su turno es asumir un riesgo sin necesidad.

Lo que le afecta queda en `28_pendiente_web.txt` (nuevo):

- ✅ **La parada de emergencia ya funciona sin tocar la web.** El driver escucha
  `/rvr/emergency_stop` con `RELIABLE + VOLATILE`, que es el QoS que usa rosbridge por defecto.
  ⚠️ **Pero no corta lo que venga de Nav2**: para una parada de verdad hay que **cancelar la
  acción** `navigate_to_pose`, no solo parar los motores. Sin implementar.
- **18 servicios y 5 topics** disponibles. 🔴 Dos avisos: los de movimiento **se saltan la capa
  de seguridad** (hablan al RVR por el puerto serie), y para teleoperar hay que publicar en
  **`/cmd_vel_raw`**, no en `/cmd_vel`.
- 📝 `/color` publica `[0,0,0]` salvo `color_detection:=true`.
- 🔴 **La credencial sigue expuesta**, y rotarla no basta: hay que quitarla del **historial** de
  git. Acción del usuario, pendiente desde el 2026-07-29.

**Ficheros:** `28_pendiente_web.txt` (nuevo), `README.md`, `scripts/README.md`,
`03_operacion/RUNBOOK.md`, `00_auditoria/evidencia/mediciones_banco/README.md`,
`INSTALACION.md`, `TRASPASO.md`, `CLAUDE.md`, `02_manual/MANUAL_ATRIZ_ROS2.md`.

---

## 2026-07-31 — 🔴 `provision.sh` nunca instalaba Nav2. Verificador de 50 a 84

Evidencia: `00_auditoria/evidencia_24_04/27_provision_verificador.txt`.

Regla del proyecto: **la imagen dorada es el atajo, `provision.sh` es la verdad**. Todo lo hecho
desde la Fase 4b estaba **solo en este robot**.

### 🔴 `provision.sh` no instalaba `navigation2`

El paso 7/8 instalaba `xacro` y `slam_toolbox` y nada más. **Un robot aprovisionado con el
script tenía driver, LIDAR y SLAM — y no podía navegar, ni tenía capa de seguridad, ni
localización.**

De `navigation2` sale mucho más que navegar: `collision_monitor` (cap. 12), `map_server` + `amcl`
(cap. 14) y `map_saver_cli`, la única forma fiable de guardar mapas (cap. 11.11).

✅ Añadido, con la decisión documentada en el propio script —**`navigation2`, no
`nav2-bringup`**, que son 312 paquetes de TurtleBot simulado replicados por 16— y **comprobando
el efecto**: que los binarios existan, no que `apt` dijera que sí.

### `verificar_robot.sh`: de 50 a 84 comprobaciones

Los binarios de Nav2 y 0 paquetes de simulador · los 9 ficheros de config y launch · los
**valores medidos** (`robot_radius` 0.145 en los dos costmaps, URDF 0.182 × 0.217, `laser_z`
0.155) · los valores **por defecto que son decisiones** (`publicar_inclinacion` y
`color_detection` en `false`, `/rvr/emergency_stop`, QoS VOLATILE) · y con `--hardware`, **los
18 servicios**.

🔴 **Preguntando a un CLIENTE, no a `ros2 service list`**, que miente por omisión: dejó fuera
`set_drive_parameters` (17 de 18). Un verificador que usara la lista daría un fallo falso.

### 🔴 Y el verificador tenía TRES fallos propios

Aplicarle su propia regla —«comprobar el efecto»— los sacó:

1. **Comprobaba el driver de ROS 1.** Hacía grep sobre `Atriz_rvr_node.py`, que sigue en el
   repo como herencia: **la comprobación pasaba mirando un fichero que no se ejecuta.** Deriva
   silenciosa, justo lo que el script existe para evitar.
2. **Contaba un comentario.** `grep -c 'robot_radius: 0.145'` daba **3** —los dos ajustes más
   una mención en la cabecera— y fallaba con la configuración **correcta**.
3. **Daba el LIDAR por roto con el robot funcionando.** La prueba abre `/dev/ttyUSB0` en crudo,
   y con el `ydlidar_ros2_driver` vivo el puerto está ocupado. Ahora, si el driver corre, se
   comprueba por **`/scan`** — y es mejor prueba, porque cubre el driver ROS y el QoS. Medido:
   **89 barridos en 8 s, ~11 Hz**.

> 📝 **Un verificador con falsos positivos se acaba ignorando, y eso es peor que no tenerlo.**

### Resultado

```
sin --hardware   76 correctas · 1 aviso · 0 fallos
con --hardware   84 correctas · 1 aviso · 0 fallos
```

⏳ **`provision.sh` NO se ha ejecutado de principio a fin desde estos cambios.** Es idempotente y
el paso 7 se probó a mano, pero una pasada completa sobre un 24.04 limpio sigue **sin
verificar** — y es lo que decide si la imagen dorada sale bien.

**Ficheros:** `scripts/provision.sh`, `scripts/verificar_robot.sh`,
`27_provision_verificador.txt` (nuevo), `TRASPASO.md`, `INSTALACION.md` (F22 ✅ → F23),
`CLAUDE.md`.

---

## 2026-07-31 — ✅ Los servicios del driver, de 1 a 18. Y `/color` nunca funcionó

Evidencia: `00_auditoria/evidencia_24_04/26_servicios_driver.txt`, manual **cap. 16** (nuevo).
Herramienta nueva: `mediciones_banco/medir_sensor_color.py`.

### Los 18, portados en orden de riesgo

Primero lo que no mueve nada, para poder probarlo en banco sin espacio:

```
lecturas    get_encoders · get_system_info · get_control_state · get_rgbc_sensor_values
luces       set_led_rgb · set_multiple_leds · set_leds · trigger_led_event
IR          send_infrared_message · set_ir_mode · set_ir_evading (⚠️ este sí mueve)
config      set_drive_parameters · set_pos_and_yaw
movimiento  move_timed · raw_motors · move_to_pose · move_to_pos_and_yaw
```

Verificados **contra el robot**, no solo por que respondan:

```
move_timed  2 s a 0.15 m/s   ->  30.3 cm medidos contra 30   (101 %)
raw_motors  reversa 25 %     ->  30.7 cm, para al mandar modo 0
move_to_pos_and_yaw 0.20 m   ->  19.5 cm                     ( 97 %)
```

✅ **Y la parada de emergencia los bloquea**: `success=False` y **0.0 cm** de desplazamiento.

### 🔴🔴 `/color` llevaba publicando `[0,0,0]` desde siempre

Lo destapó una pregunta del usuario. **El sensor no da nada sin su luz** — medido:

| | Claro |
|---|---|
| sin luz | **4** |
| con luz | **741** |

**185×.** Y el driver **nunca la encendía**: el topic existía, publicaba a 16 Hz, y el dato era
oscuridad. Estaba en la lista de «verificado» desde la Fase 2.

🔴 **Y no se puede encender bajo demanda:** con el streaming de `color_detection` ya
configurado, `enable_color_detection` **no hace nada** — 481 mensajes de `/color`, todos ceros,
durante la llamada. La primera versión del servicio hacía justo eso y devolvía oscuridad con
`success=True`.

✅ **Arreglado** con el parámetro `color_detection` (por defecto `false`), que lo enciende
**antes** del streaming. Con `false`, el driver **avisa por el log**. Verificado: `/color` pasa
a dar `[164, 140, 119]` y el servicio 735 en el canal claro.

### 🔴 Y un fallo mío, que vio el usuario

El driver encendía el sensor y **no lo apagaba al morir**: el LED blanco se quedaba encendido
gastando batería. Es exactamente lo que avisa `CLAUDE.md` —«cada `(True)` necesita su `(False)`,
también en el camino de error»— cometido dos horas después de leerlo, y **lo detectó el ojo del
usuario, no el código**. Arreglado en `_apagar_rvr()`: apaga sensor y LEDs. Verificado,
`clear=733` → **`clear=0`** tras SIGINT.

### Lo que no se portó tal cual, y por qué

- **`set_pos_and_yaw` solo acepta (0,0,0)** y rechaza el resto **en vez de fingir**: el SDK no
  puede fijar una pose arbitraria, y `reset_yaw()` no hace nada.
- **`trigger_led_event`**: el RVR no tiene «eventos de LED». Se traducen a colores fijos.
- **`uptime_ms`**: el SDK no lo expone. Se dice en el `message` en vez de dejar un cero mudo.
- **`ConfigureStreaming` / `StartStreaming`: no portados a propósito** — pueden romper la
  telemetría del propio driver.

### ⚠️ Los servicios de movimiento se saltan la capa de seguridad

No publican en ningún topic: hablan al RVR por el puerto serie, así que ni el
`collision_monitor` ni el watchdog los ven. Solo los para la **parada de emergencia**. Y
`raw_motors` no tiene corte automático.

### 📝 `ros2 service list` no es autoritativo

Omitió `set_drive_parameters` (17 de 18) mientras `ros2 service type` sí lo encontraba y un
cliente con `wait_for_service` decía **disponible**. Es descubrimiento de DDS.
→ **Para saber si un servicio existe, usa un cliente.** En `CLAUDE.md`.

**Ficheros:** `rvr_driver_node.py`, `robot.launch.py`, `26_servicios_driver.txt` (nuevo),
`medir_sensor_color.py` (nuevo), manual cap. 16, `TRASPASO.md`, `INSTALACION.md` (F21 ✅ → F22),
`CLAUDE.md`.

---

## 2026-07-31 — 🔴 La parada de emergencia fallaba por TRES causas. Arreglada

Evidencia: `00_auditoria/evidencia_24_04/25_parada_emergencia.txt`, manual **cap. 15** (nuevo).

### Las tres, y las tres en silencio con `200 OK`

| | Causa | Cuándo |
|---|---|---|
| 1ª | **nombre de topic**: la web publica en `/rvr/emergency_stop`, el driver escuchaba `is_emergency_stop` | ROS 1, auditoría |
| 2ª | **namespace**: al portar se arregló el nombre y se coló el `/rvr/` | ROS 2, hoy |
| 3ª | **QoS incompatible** | ROS 2, hoy |

**La segunda.** El driver se suscribía a nombres **relativos**, que con el namespace vacío
resuelven a `/emergency_stop` y `/is_emergency_stop`:

```
$ ros2 topic info /rvr/emergency_stop
  Unknown topic '/rvr/emergency_stop'      ← el que usa la web
```

📝 Y el `TRASPASO.md` decía «el topic ya existe en el driver ROS 2». Existe **un** topic; no el
que la web usa. Corregido.

**La tercera, y solo aparece probándolo.** Con el nombre ya correcto:

```
New publisher discovered on topic '/rvr/emergency_stop', offering incompatible QoS.
No messages will be received from it. Last incompatible policy: DURABILITY
```

El driver se suscribía `RELIABLE + TRANSIENT_LOCAL`, justificado con «así un suscriptor que
llegue tarde recibe el último estado». **Ese razonamiento es del publicador.**

> 🔴 **En el suscriptor, `TRANSIENT_LOCAL` solo RESTRINGE:** exige que el publicador también lo
> sea, y ninguno lo es por defecto — ni `ros2 topic pub`, ni **rosbridge**, que es por donde
> hablará la web. `VOLATILE` empareja con todo y es estrictamente más compatible.

### ✅ El arreglo, verificado

El driver escucha **también `/rvr/emergency_stop`** (absoluto) y el QoS pasa a
`RELIABLE + VOLATILE`. Disparando los tres nombres uno a uno:

```
/rvr/emergency_stop  ✅   /emergency_stop  ✅   /is_emergency_stop  ✅
avisos de "incompatible QoS": 0 · paradas: 3 · liberaciones: 3
```

⚠️ **Tres suscripciones para una función es feo, y a propósito**: el modo de fallo de este botón
es «no llega el mensaje» y ha fallado dos veces por eso. La Fase 5 unifica a uno, **no antes**
de que el nuevo esté probado de extremo a extremo.

📝 **La lección de método:** las causas 2 y 3 **solo aparecen publicando de verdad**. Leer el
código da el nombre pero no el namespace resuelto ni el QoS; `ros2 topic list` da el namespace
pero no el QoS. En `CLAUDE.md`.

### 🔴 Y lo que sigue sin estar

**La parada no corta lo que venga de Nav2.** Pone el flag del driver, que ignora `cmd_vel` —
pero Nav2 seguiría mandando objetivos y su controlador publicando. Habría que **cancelar la
acción** además de parar los motores. **Sin comprobar.**

### 📝 De paso: workspace parásito borrado

Buscando el fichero instalado apareció `src/Atriz_rvr/{build,install,log}` — el parásito que
documenta `CLAUDE.md`, de los dos `colcon build` desde el directorio equivocado. Estaba inerte
(tenía `COLCON_IGNORE`) pero confunde. Borrado, 1.1 MB.

Y queda aclarado cómo funciona `--symlink-install` aquí: el módulo instalado **apunta al fichero
fuente**, así que editarlo cambia el comportamiento sin reinstalar. Pero `colcon build` sigue
haciendo falta para los launch y los YAML de bringup, que **sí** se copian.

**Ficheros:** `rvr_driver_node.py`, `25_parada_emergencia.txt` (nuevo), manual cap. 15,
`TRASPASO.md`, `INSTALACION.md` (F20 ✅ → F21), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Fase 4c: `map_server` + AMCL, y Nav2 navegando sobre el mapa

Evidencia: `00_auditoria/evidencia_24_04/24_fase4c_amcl.txt`, manual **cap. 14** (nuevo).
Nuevos: `config/localizacion_amcl.yaml` y `launch/localizacion.launch.py`.

### ✅ El ciclo completo, de principio a fin

```
a) MAPEAR con slam_toolbox         celdas 486 → 2774
b) GUARDAR con map_saver_cli       mapa_amcl.pgm, 5989 bytes
c) PARAR SLAM                      `map` deja de existir  ✅ punto de partida limpio
d) LOCALIZAR                       map_server y amcl active [3]
                                   map → odom: (−0.004, 0.011), yaw +0.65°
e) ¿SIGUE LA POSE?  60 cm          ODOM 61.8 · AMCL 61.9 · dif 0.1 cm  ✅
f) NAVEGAR con Nav2 sobre el mapa  SUCCEEDED, error 8 cm
                                   ODOM 73.4 · AMCL 72.3 · dif 1.1 cm  ✅
```

### 🔴 AMCL cuesta CASI EL DOBLE que SLAM — al revés de lo que suponía

| | CPU | RAM |
|---|---|---|
| `slam_toolbox` | **4.8 %** | 49.1 MB |
| `amcl` + `map_server` | **8.8 %** | 85.9 MB |

En el YAML había escrito «se espera menos, pero **se mide, no se supone**». Menos mal.

**El argumento para AMCL no es la CPU: es el marco compartido.** 16 robots sobre un mismo `map`
es lo que permite que la web diga «ve a la mesa 3» y que todos entiendan lo mismo. Con 16 SLAM
hay 16 mapas del mismo sitio, cada uno con su origen.

⚠️ **Nota de método que afecta a números ya publicados:** `ps -o %cpu` da el **promedio desde
que arrancó el proceso**, no el instantáneo. Las cifras de arriba se midieron muestreando
`/proc` dos veces con 20 s. Las anteriores del proyecto usaron `ps`; `slam_toolbox` vuelve a
salir 4.8 % con el método bueno, así que el orden de magnitud aguanta. En `CLAUDE.md`.

### ✅ Dos salvaguardas en el launch, probadas

🔴🔴 **AMCL y `slam_toolbox` publican los dos `map → odom`.** Juntos parten el árbol TF **sin dar
ningún error** — es el fallo que costó la Fase 4. El launch **se niega a arrancar** si
`slam_toolbox` está vivo, y también si el mapa no existe (y entonces dice cómo hacerlo).

📝 La comprobación usa `ps -eo comm`, **no `pgrep -f`**: el patrón de `-f` casa con la propia
línea de comando y eso ya ha matado la terminal dos veces en este proyecto.

### ⚠️ Lo que NO está resuelto

🔴 **La σyaw crece:** 6.7° tras avanzar 60 cm, **18.0°** tras navegar 80. Es mucho. La sospecha
es que el mapa es pequeño y poco distintivo, pero **no está comprobado**.

🔴 **La pose inicial.** AMCL cree que el robot está en (0,0,0). Si no lo está, empieza
equivocado y puede no recuperarse. ⏳ **Para la flota tendrá que venir por robot.**

⚠️ Y estas pruebas comprobaron la **consistencia** de la pose con la odometría (0.1 y 1.1 cm),
**no su corrección absoluta** — para eso haría falta una referencia externa medida con cinta.

**Ficheros:** `config/localizacion_amcl.yaml` (nuevo), `launch/localizacion.launch.py` (nuevo),
`24_fase4c_amcl.txt` (nuevo), manual cap. 14, `mapas/mapa_amcl.*` (nuevo), `TRASPASO.md`,
`INSTALACION.md` (F19 ✅ → F20), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Decidido: no se persigue el roll, y el driver deja de publicarlo

Decisión del usuario, y una consecuencia que **no** se deriva de ella.

### La decisión

**No se persigue el efecto del roll en la deriva.** Cerrarlo costaría **~62 corridas y
5.2 horas de robot** para un efecto de ~1 cm sobre una tolerancia de objetivo de Nav2 de
**10 cm**.

### 🔴 Pero eso no deja el roll publicado — son dos preguntas distintas

| | |
|---|---|
| ¿**afecta** la inclinación a la deriva? | sin responder, y se acepta así |
| ¿**existe** la inclinación? | **respondida: no** (cap. 13.3) |

Suelo plano medido con nivel (≤0.40°), error del acelerómetro **fijo en el marco del robot**, y
`\|g\|` un **3.8 % corto**. **Publicar 6.9° que no existen en `odom → base_footprint` es
publicar un dato que sabemos incorrecto**, se pueda medir su efecto o no. REP-105 espera ahí la
pose del robot.

✅ **Aplicado:** `publicar_inclinacion` pasa a **`false` por defecto**, en el driver y en
`robot.launch.py`. Verificado sobre el sistema instalado:

```
ros2 param get /rvr_driver publicar_inclinacion  ->  False
/odom  ->  roll +0.00°  pitch +0.00°   (296 muestras)
```

⚠️ Con `publicar_inclinacion:=true` se recupera lo anterior. Haría falta si un robot trabajara
en una superficie inclinada de verdad — pero entonces hay que **calibrar antes el
acelerómetro**, que no acierta ni el módulo.

📝 **Consecuencia para el futuro:** si algún día se mete `robot_localization` para fusionar la
IMU, hay que saber que ese sensor da una gravedad con **3.8 % de error de módulo y ~6.9° de
dirección**. Fusionarlo tal cual metería ese error en la pose.

**Ficheros:** `rvr_driver_node.py`, `robot.launch.py`, manual cap. 13.5 y 9.12d,
`23_referenciar_posicion.txt`, `TRASPASO.md`, `INSTALACION.md` (F18 ✅ → F19), `CLAUDE.md`
(nueva fila en «Decisiones ya tomadas»). Y `deriva_roll_resultados.jsonl` pasa a
`deriva_roll_tanda3.jsonl`, para que la siguiente tanda no lo pise.

---

## 2026-07-31 — ✅ Referenciar la posición: los fallos de SLAM desaparecen

Herramienta nueva: `mediciones_banco/referenciar_posicion.py`, que
`caracterizar_deriva_slam.py` llama **antes de cada corrida**. Evidencia:
`23_referenciar_posicion.txt`, manual **cap. 9.12c–9.12d**.

### ✅ El robot se queda donde debe — y esto no depende de ninguna estadística

| | adelante | derecha |
|---|---|---|
| **sin** referenciar | rango **0.47 m** | rango **0.81 m** (monótono) |
| **con** referenciar | rango **0.06 m** | rango **0.03 m** |

**8× menos dispersión hacia delante, 27× lateral**, y la deriva monótona desaparece.

### ✅ Y con ella, los fallos

| | fallos > 5 cm | peor caso |
|---|---|---|
| tandas 1+2, **sin** referenciar | **5 de 24** | **56.1 cm** |
| tanda 3, **con** referenciar | **0 de 12** | **4.4 cm** |

Las doce: `0.5 0.5 0.7 0.7 0.9 0.9 1.1 2.1 2.2 3.7 3.7 4.4`. **La distribución deja de ser
bimodal.**

⚠️ **Honestidad estadística:** Fisher exacto de 0/12 contra 5/24 da **p = 0.113** — sugerente,
**no concluyente al 5 %**. Con una tasa base del 21 %, sacar 0 de 12 por azar tiene un 6 % de
probabilidad. Lo indiscutible es la tabla de posiciones.

### ✅ Y la deriva NO crece con la distancia

```
CORTA (158 cm, n=6)   mediana 1.55 cm
LARGA (233 cm, n=6)   mediana 0.90 cm    ← recorre un 47 % más y sale MEJOR
```

Desmonta definitivamente la narrativa del fichero 14 («0.63 % del recorrido en las cortas,
1.14 % en las largas»). ✅ **Para Nav2: 1–4 cm en recorridos de 1.6–2.3 m**, muy por debajo de
la tolerancia de objetivo de 10 cm. **La localización deja de ser un bloqueante.**

### Cómo funciona, y dos decisiones que importan

Ajusta una recta a la pared frontal en el marco del robot —`x = m·y + c` da el rumbo `atan(m)`
y la distancia perpendicular `c·cos(θ)`— y entonces conduce a la distancia objetivo y se alinea.

🔴 **El orden es distancia y DESPUÉS rumbo**, y salió probando: al revés, conducir vuelve a
torcer el rumbo recién corregido (medido, **+0.41° → +2.53°**). Girar sobre el eje no cambia la
distancia perpendicular, porque el centro del robot no se mueve.

🔴 **No usa `/odom` ni el mapa, a propósito:** referenciar con odometría sería circular — es
justo lo que se está midiendo.

Precisión: **±0.2 cm y ±0.2°** en dos pasadas seguidas. La tolerancia se dejó en 3 cm porque la
frenada del RVR se come 1–2 cm y pedir menos impediría converger.

### ⚠️ La pregunta del roll: ahora se intuye, y sigue sin resolverse

```
CON roll  n=6  media 2.23 cm      SIN roll  n=6  media 1.33 cm      diferencia +0.90 cm
```

📝 **Las dos distancias apuntan en el mismo sentido**, cosa que antes no pasaba: CORTA +1.30 cm,
LARGA +1.40. El roll **siempre** sale peor, y la magnitud coincide con la predicha —`cos(6.9°)`
comprime los alcances un 0.7 %.

⚠️ **Pero p = 0.142** (permutación exacta sobre 924 particiones). Con n=6 por rama, no.

⏳ Con d = 0.64 harían falta **~31 corridas por rama → ~62 en total, unas 5.2 horas de robot**.
El efecto es de ~1 cm sobre una tolerancia de objetivo de 10 cm: **es una decisión, no un
pendiente automático.**

### Menor

⏳ `comparar_deriva_roll.py` captura la salida de `caracterizar_deriva_slam.py` y solo extrae
las líneas de CORTA/LARGA: **los residuos de cada referenciado se pierden**. Deberían ir al
`.jsonl` para poder cruzarlos con la deriva.

Batería, tercera medida: 69 % → 59 % en la tanda 3 — gasta más que las anteriores porque el
referenciado añade movimiento (bloques de 3.5 min en vez de 2.7). Estimación conjunta de las
tres tandas: **~0.5–0.9 %/min** conduciendo.

**Ficheros:** `mediciones_banco/referenciar_posicion.py` (nuevo),
`caracterizar_deriva_slam.py`, `23_referenciar_posicion.txt` (nuevo), manual cap. 9.12c–9.12d,
`deriva_roll_tanda1.jsonl` / `tanda2.jsonl` / `resultados.jsonl`, `TRASPASO.md`,
`INSTALACION.md` (F17 ✅ → F18), `CLAUDE.md`.

---

## 2026-07-31 — 🔴 La réplica desmonta mi conclusión: no es la distancia, es que el robot se va

Se repitió el experimento de deriva **con el mismo protocolo, una hora después**, añadiendo una
sola cosa: **registrar dónde está el robot** antes de cada bloque. Evidencia:
`22_replica_deriva.txt`, manual **cap. 9.12b**.

### 🔴 El fallo cambió de distancia

| | TANDA 1 | TANDA 2 (réplica) |
|---|---|---|
| CORTA (158 cm) | 1.0, 1.0, 1.2, 2.1, 2.2, 2.9 → **0 de 6** | 0.8, 0.8, 1.6, 2.7, **6.6**, **14.3** → **2 de 6** |
| LARGA (233 cm) | 0.9, 1.1, 1.2, **12**, **16**, **56** → **3 de 6** | 1.0, 1.9, 2.5, 2.7, 3.0, 3.3 → **0 de 6** |

En la tanda 1 fallaban las largas y las cortas iban perfectas. En la 2, al revés. **La distancia
no es la variable**, y la conclusión que escribí hace una hora —«SLAM es fiable hasta 1.6 m y
deja de serlo a 2.3 m»— **queda retirada**.

📝 Era coherente con sus datos y estaba equivocada. Es exactamente para lo que sirve replicar.

### Las 24 corridas juntas — lo que sí se sostiene

```
CORTA (n=12)   normales (10): mediana 1.40 cm, rango 0.8–2.9  ·  fallos (2): 6.6, 14.3  → 17 %
LARGA (n=12)   normales  (9): mediana 1.90 cm, rango 0.9–3.3  ·  fallos (3): 12, 16, 56 → 25 %
GLOBAL: 5 fallos de 24  →  ~21 %
```

✅ **Cuando funciona va bien, y casi igual a las dos distancias** (1.40 vs 1.90 cm) — lo que
además desmonta la narrativa del fichero 14 de que la deriva crecía proporcionalmente al
recorrido. Sus **medianas eran correctas**; lo que no vio con n=3 es **la cola**.

🔴 **Y una de cada cinco corridas falla**, de forma bimodal: o ≤3.3 cm o ≥6.6 cm.

### 🔴 La causa más probable: el robot se va del sitio y nadie lo corrige

| bloque | adelante | der | CORTA | recorrido |
|---|---|---|---|---|
| A1 | 2.06 m | **0.97** | **6.6** 🔴 | 159 |
| B1 | 2.11 | 0.42 | 1.6 | 158 |
| A2 | 2.01 | 0.30 | 0.8 | 156 |
| B2 | **1.64** | 0.26 | **14.3** 🔴 | **137** |
| A3 | 1.73 | 0.19 | 0.8 | 156 |
| B3 | 1.73 | **0.16** | 2.7 | 153 |

🔴 **`der` cae de forma monótona: 0.97 → 0.16 m.** El robot deriva a la derecha corrida tras
corrida y acaba **a 5 cm de rozar** (media anchura 11 cm). Y en la tanda 1: **94 cm de deriva
hacia delante en 12 corridas**, ~8 cm cada una.

> **La consecuencia de método, que es la importante:** `caracterizar_deriva_slam.py` y
> `comparar_deriva_roll.py` asumen que el robot vuelve al punto de partida y que las N corridas
> son repeticiones del **mismo** experimento. **No lo son.** Eso no es una repetición: es un
> barrido por posiciones distintas, sin control ni registro.

⏳ **El arreglo, no implementado:** re-referenciar la posición antes de cada corrida con `/scan`.
Hasta entonces ninguna de las dos herramientas da una distribución válida.

### La pregunta del roll, aplazada por tercera vez

La única comparación sin fallos dentro fue LARGA: **2.70 contra 2.50 cm**, diferencia de 0.20 cm
con σ 1.19 — **compatible con cero**. Pero con n=3 por rama y un efecto de ~1 cm eso **no
permite decir que el roll no afecte**: solo que no se ve. Y no se verá hasta controlar la
posición.

**24 corridas y hora y media de robot sin responder la pregunta** — porque el banco de pruebas
no controla la variable que más se mueve.

### Detalles menores

- El registro del entorno **falló en silencio** la primera vez (devolvía `None`): usé `repr()`
  en vez de `shlex.quote()` para pasar el código al shell, y `repr()` escapa los saltos de línea.
  Se pilló **probándolo antes** de lanzar.
- Consumo de batería, segunda medida: 81 % → 73 % en la tanda 2, más lento que la 1 (92 → 85).
  Estimación conjunta **~0.5–0.8 %/min** conduciendo, 2–3 h por carga. Sigue siendo gruesa.

**Ficheros:** `22_replica_deriva.txt` (nuevo), `21_deriva_roll_y_fallo_largo.txt` (retractación
de su sección 3), manual cap. 9.12a (retractado), 9.12b (nuevo) y 13.6,
`mediciones_banco/comparar_deriva_roll.py` (registro del entorno),
`deriva_roll_tanda1.jsonl` + `deriva_roll_resultados.jsonl`, `TRASPASO.md`,
`INSTALACION.md` (F16 ✅ → F17), `CLAUDE.md`.

---

## 2026-07-31 — 🔴 SLAM falla el 50 % a 2.3 m, y la inclinación es del acelerómetro

Evidencia: `00_auditoria/evidencia_24_04/21_deriva_roll_y_fallo_largo.txt`, manual **cap. 13**
(reescrito) y **9.12a** (nuevo). Herramienta nueva: `mediciones_banco/comparar_deriva_roll.py`.

### 🔴 El hallazgo: a 2.3 m, la mitad de las corridas fallan

Se iba a medir si el roll de la IMU empeora la deriva. **No respondió esa pregunta** — apareció
algo mayor. 12 corridas, `slam_toolbox` reiniciado de cero en cada una:

```
CORTA (158 cm, n=6)   0.9  1.0  1.0  1.2  2.1  2.2  2.9
  -> mediana 1.65 cm · peor 2.9 cm · corridas > 5 cm: 0 de 6        ✅

LARGA (233 cm, n=6)   0.9  1.1  1.2  |  12.0  16.0  56.1
  -> mediana 6.60 cm · peor 56.1 cm · corridas > 5 cm: 3 de 6  🔴 el 50 %
```

🔴 **Es BIMODAL: o ~1 cm o ≥12 cm, sin nada en medio.** No es deriva gradual — es el emparejado
de barridos **enganchando o perdiéndose**. Los errores angulares acompañan: 0.9–2.4° en las
buenas, **5.2–28.1°** en las malas.

**Corrige la caracterización anterior**, que con n=3 por distancia **tuvo suerte**:

| | fichero 14 (n=3) | ahora (n=6) |
|---|---|---|
| CORTA mediana | 1.0 cm | 1.65 cm |
| LARGA mediana | 2.7 cm | **6.60 cm** |
| **peor caso** | 3.2 cm | **56.1 cm** 🔴 |

**Y resucita la anomalía de la Fase 4** — aquella corrida de 2.62 m con 87.8 cm y 10.9° se
atribuyó a que el robot rozó obstáculos, y el fichero 14 la dio por explicada. **Es el mismo
fallo bimodal: no era una anomalía, es la mitad de las veces.**

⚠️ **Consecuencia para Nav2:** SLAM es fiable hasta ~1.6 m de recorrido y deja de serlo a
~2.3 m. Las navegaciones que salieron bien (8–10 cm de error) eran de **0.9–1.5 m**: por debajo
del umbral. **Objetivos más largos entran en la zona donde SLAM se pierde la mitad de las
veces.** Con 16 robots y estudiantes, no es desplegable así.

⏳ Causa sin determinar. Los tres fallos fueron corridas largas **contiguas** (2ª, 3ª y 4ª),
repartidas entre las dos ramas del experimento, y decrecientes (56.1 → 16.0 → 12.0). La firma
temporal apunta a algo del entorno que cambió y volvió, pero **no hay evidencia** y no se le
atribuye causa.

### ✅ La inclinación: es el acelerómetro, no el robot — tras dos retractaciones

**La cifra correcta:** `roll +1.10°`, `pitch +6.74°`, **total ~6.9°**. La documentación decía
«~8° de **roll**»: son ~6.9° y están casi todos en el **pitch**. ⚠️ Y **se reparten según el
rumbo** — lo único estable es el módulo.

🔴 **Dos conclusiones retiradas, y ninguno de los dos argumentos valía:**

1. «No existe, el LIDAR está nivelado en 4 puntos» — **la regla mide desde el SUELO**, así que
   no distingue «nivelado respecto al chasis» de «horizontal respecto a la gravedad».
2. «Es física, el pitch cambia de signo al girar 180°» — **el cambio de signo solo dice que el
   error está en el marco del MUNDO**, y eso lo producen dos causas: suelo inclinado **o**
   referencia de gravedad torcida. Presenté como resuelto un caso con dos explicaciones.

✅ **Lo que sí lo zanja**, y es el acelerómetro **crudo** porque no pasa por ninguna fusión:

| | ANTES | DESPUÉS del giro de 177.8° | |
|---|---|---|---|
| pitch | +6.72° | **−6.99°** | cambia de signo |
| `accel.x` | −1.091 | **−1.158** | **NO cambia** |

Error **fijo en el marco del robot** + suelo plano medido con nivel (≤0.40°) = **el sensor está
descalibrado**. Lo confirma el módulo: `|g| = 9.435` contra 9.807, **3.8 % corto**. Y no es la
referencia de arranque: se apagó, se dejó plano en el suelo y se encendió allí — igual.

⏳ **Sin explicar:** por qué el cuaternión fusionado gira con el rumbo mientras el sesgo del
acelerómetro no. Una traza de 90 s descarta que sea un transitorio. Se deja como pregunta
abierta, **sin inventarle mecanismo**.

### El experimento del roll queda sin responder

| | | mediana | σ |
|---|---|---|---|
| CORTA | CON roll / SIN roll | 2.10 / 1.20 cm | 0.95 / 0.64 |
| LARGA | CON roll / SIN roll | 1.10 / 12.00 cm | 8.66 / 29.08 |

El efecto buscado era de ~1 cm y la dispersión de las largas es de 30. **No se puede concluir
nada**, y repetirlo no serviría hasta arreglar el fallo bimodal.

📝 **El diseño alternado sí cumplió su función**: deja ver que los fallos **no** se reparten por
condición (1 CON roll, 2 SIN roll). Con 6 y 6 en bloque habrían caído todos en una rama y
habrían parecido su causa.

### 🔴 Un falso positivo del guardián — que aun así fue lo correcto

El primer lanzamiento abortó a los 2 min: el guardián comprobaba solo el **roll**, que valía
+0.11° porque la inclinación estaba entera en el pitch. Arreglado a `hypot(roll, pitch)`.
**Mejor un falso positivo a los 2 min que 45 min de datos con el interruptor sin efecto.**

### ✅ Consumo de batería — un dato que el proyecto no tenía

**92 % → 85 %** en 6 bloques; mediana **2 puntos** por bloque de 2.7 min → **~0.74 %/min**, del
orden de **2 horas de conducción** por carga. ⚠️ Estimación gruesa: `/battery_state` va en pasos
de 1 %, los bloques son cortos y el ritmo cayó (1.12 → 0.74 → 0.37 %/min).

**Ficheros:** `21_deriva_roll_y_fallo_largo.txt` (nuevo), `14_deriva_slam_caracterizada.txt`
(aviso de superado), manual cap. 13 (reescrito) y 9.12a (nuevo),
`mediciones_banco/comparar_deriva_roll.py` (nuevo), `caracterizar_deriva_slam.py`,
`medir_slam_ros2.py`, `TRASPASO.md`, `INSTALACION.md` (F15 ✅ → F16), `CLAUDE.md`.

---

## 2026-07-31 — ⏳ Interruptor del roll de la IMU: puesto y verificado, medida pendiente

Para poder **medir** si el roll falso de ~8° contribuye a la deriva de SLAM, en vez de
suponerlo. Evidencia: `20_interruptor_inclinacion.txt`, manual **cap. 13.4–13.5**.

### ✅ El interruptor

```bash
ros2 launch atriz_rvr_bringup robot.launch.py publicar_inclinacion:=false
```

Nuevo parámetro del driver, **por defecto `true`** (el comportamiento de siempre). Con `false`,
`_h_quaternion` pone `roll = pitch = 0` antes de componer la orientación que va a `/odom` y a
TF. **Verificado**: `roll +0.00° pitch +0.00°` sobre **414 muestras**.

Es un interruptor de **medición**, no de operación: el valor por defecto no se cambia hasta
tener el número.

### El diseño de la prueba, y por qué no se puede recortar

- 🔴 **La línea base anterior no vale.** Las 6 corridas del fichero 14 se hicieron con
  `laser_z = 0.1745`, y el desplazamiento lateral que induce el roll **escala con esa altura**:
  `0.1745 × sin(8°) = 2.4 cm` entonces, **2.2 cm ahora**. Hay que rehacer las dos mitades.
- 🔴 **Las condiciones se ALTERNAN**, no 6 con roll y luego 6 sin él. Si la batería corta a
  mitad, los datos siguen **balanceados**; y el nivel de carga y el calentamiento dejan de
  poder colarse como variable — que es el tipo de confusión que ya costó una retractación.
- ⚠️ **No se puede bajar a 2 corridas por condición.** El efecto buscado es de ~**1 cm** y la
  dispersión ya medida es **σ = 0.6–1.0 cm**: saldría dentro del ruido. Hacen falta ≥3
  repeticiones de cada distancia por condición — **12 corridas**.

⏳ **Pendiente de ejecutar.** Son ~40 min de robot moviéndose y la batería estaba al **34 %**.
Se decidió **cargar primero**: el consumo del RVR por minuto **no está medido**, y arriesgar un
corte a mitad daría un «no concluyente» habiendo gastado la carga.

### 🔴 Trampa nueva: una excepción en un manejador mata `/odom` en silencio

Montando el interruptor se escribió la asignación contra `self._silence_timeout` cuando la
variable real del driver se llama **`self._timeout_silencio`**. La línea no se insertó y
`self._publicar_inclinacion` quedó **usada sin existir**:

| | |
|---|---|
| `AttributeError` en `_h_quaternion` | **ni una línea en el log** |
| `/odom` y `/imu` | **cero mensajes**, con los topics existiendo |
| `/scan` | funcionando |
| el detector de silencio | **no saltó** |

Y no salta **por diseño**: mide el tiempo desde la última **muestra del RVR**, no desde la
última publicación. Las muestras llegaban — se ve el `origen del yaw fijado en +10.2°` en el
log, que sale de la primera. Lo que fallaba era el manejador que las convierte.

> **Atajo de diagnóstico:** si `/scan` va y `/odom` no, **y no hay error ni aviso de silencio**,
> sospecha de una excepción dentro de un manejador. El síntoma «el topic existe y no publica»
> es idéntico al de un RVR dormido, pero **el RVR dormido sí dispara el detector de silencio**.

📝 Es la **tercera** vez que el proyecto se topa con un fallo que no da error. Las anteriores:
el árbol TF partido y `slam_toolbox` en `unconfigured`. En `CLAUDE.md`.

### 📝 `/battery_state.percentage` es una fracción 0–1

Es lo que manda `sensor_msgs/BatteryState` («Charge percentage on 0 to 1 range») y el driver lo
respeta: `0.34` son **34 %**. Leerlo como 0–100 hace que un robot al 34 % parezca estar al
**0 %** — provocó una falsa alarma de batería agotada en esta misma sesión. En `CLAUDE.md`.

⏳ Y deja al descubierto un dato que el proyecto **no tiene** y que hará falta con 16 robots:
**cuánto consume el RVR por minuto conduciendo**.

**Ficheros:** `atriz_rvr_driver/scripts/atriz_rvr_driver/rvr_driver_node.py`,
`atriz_rvr_bringup/launch/robot.launch.py`, `20_interruptor_inclinacion.txt` (nuevo),
manual cap. 13.4–13.5, `mediciones_banco/caracterizar_deriva_slam.py` (17.5 → 15.5 cm),
`TRASPASO.md`, `INSTALACION.md` (F14 ✅ → F15), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Paradas contra pared re-medidas: el recálculo era correcto

Los huecos publicados estaban **recalculados, no vueltos a medir** — la corrección de las cotas
del robot había cambiado la constante sin repetir el experimento. Repetido con el robot ya bien
modelado (media longitud 0.091, `laser_z` 0.155, `wheel_radius` 0.035) y `radius: 0.18`:

| velocidad | n | **medido** | recalculado | dif |
|---|---|---|---|---|
| 0.25 m/s | 1 | **9.9 cm** | 9.8 | +0.1 |
| 0.40 m/s | 2 | **10.6 / 10.7 cm** | 10.8 | −0.2 |

**Las diferencias son de 1–2 mm**, por debajo de la resolución útil de la medida. Y **repite**:
las dos corridas a 0.40 dan 10.6 y 10.7, 1 mm de dispersión.

### El modelo, afinado

```
asíntota = radius − media longitud = 0.18 − 0.091 = 8.9 cm
a 0.25 m/s  →  9.9 cm    margen +1.0 cm
a 0.40 m/s  → 10.65 cm   margen +1.8 cm
```

📝 **El margen crece con la velocidad**, lo que confirma con más resolución lo que ya se había
visto: `approach` empieza a frenar antes cuanto más rápido va, así que la holgura **no se
degrada al acelerar — mejora**.

📝 Y cambiar `laser_z` (0.1745 → 0.155) y `wheel_radius` (0.032 → 0.035) **no alteró el
comportamiento**, como se preveía: son traslaciones en Z y el monitor trabaja en el plano. Los
números lo confirman en vez de suponerlo.

Comprobado al arrancar, con el URDF nuevo: `base_footprint → laser` = `[0.000, 0.000, 0.155]`,
exactamente lo medido con la regla.

**Ficheros:** `17_collision_monitor.txt` (bloque «RE-MEDIDO»), manual cap. 12.4,
`03_operacion/MEDIDAS_ROBOT.md`, `TRASPASO.md`, `INSTALACION.md` (F13 ✅ → F14), `CLAUDE.md`.

---

## 2026-07-31 — ✅ El robot medido entero, y la «inclinación de ~8°» resulta no existir

El usuario midió todas las cotas de
[`03_operacion/MEDIDAS_ROBOT.md`](03_operacion/MEDIDAS_ROBOT.md) con el robot apagado sobre
suelo plano. Evidencia: `19_paso_estrecho.txt` (ampliación), manual **cap. 13** (nuevo) y 12.8.

### La ficha del RVR mentía en las tres cotas

| | medido | URDF (ficha) |
|---|---|---|
| frente-atrás | **18.2 cm** | 21.8 |
| lado a lado | **21.7 cm** | 18.5 |
| suelo → tapa | **7.0 cm** | 11.4 |
| ancho de oruga | **3.5 cm** | 2.5 |
| `wheel_separation` (entre centros) | **18.3 cm** | 15.0 |

✅ **Y cierra solo:** `14.8` (borde interno a borde interno) `+ 2 × 3.5 = 21.8 ≈ 21.7` de ancho
total. **Las orugas ocupan todo el ancho del robot** — ahí estaban los 4.5 cm que no cuadraban
en la entrada anterior.

### 🔴 El plano de barrido está 2 cm más abajo de lo documentado

`laser_z` era una **suma derivada** con la altura del RVR sacada de la ficha. Medido en cadena:

```
suelo → tapa del RVR                 7.0 cm
tapa  → base del LIDAR (piso extra)  4.6 cm
base del LIDAR → centro del disco    3.9 cm
────────────────────────────────────────────
suelo → CENTRO DEL DISCO            15.5 cm   ← laser_z
suelo → extremo superior            16.5 cm
```

Comprobación cruzada: `7.0 + 4.6 + 5.0` (alto del LIDAR) `= 16.6 ≈ 16.5`. ✅

**El límite «por debajo de X cm el robot no ve nada» pasa de 17.45 a 15.5 cm**: el robot ve
**mejor** de lo que decíamos. Un error en `laser_z` es una traslación pura en Z, así que **no
afecta a SLAM 2D ni a Nav2** — solo a la visualización y a ese límite.

### 🔴 Y la «inclinación de ~8°» no existe

Un problema abierto desde el principio, cerrado **con una regla**.

El usuario midió del suelo al disco del LIDAR **en cuatro puntos** —delante, detrás, izquierda,
derecha— y salen **iguales**. El disco mide ~7.6 cm: 8° habrían dado **~1.1 cm** de diferencia.
Se habrían visto. **El robot está físicamente horizontal.**

Y las «**tres vías independientes**» que lo confirmaban **no eran independientes**:

| «vía» | de dónde sale de verdad |
|---|---|
| árbol TF | de `odom.pose.pose.orientation`… |
| cuaternión del RVR | …que el driver copia del cuaternión, **que calcula la IMU** |
| acelerómetro | el **mismo chip** |

**Una sola fuente contada tres veces.** El árbol TF no confirmaba nada: **repetía**. El driver
llevaba un comentario explícito —«esa inclinación es real, no un error de referencia»— apoyado
en esa falsa independencia. Corregido.

> Es la regla nº4 del proyecto fallando por el lado contrario: no se atribuyó sin medir, se
> **midió tres veces lo mismo** creyendo que eran tres cosas. Anotado en `CLAUDE.md`: **antes
> de decir «confirmado por N vías», traza de dónde sale el dato de cada una.**

⏳ **Consecuencia, SIN APLICAR:** el driver publica un roll falso de ~8° en `/odom` y en TF. Un
roll en `odom → base_footprint` inclina el plano del láser y comprime los alcances por
`cos(8°) = 0.990` — un **1 %**, ~1 cm por metro. La deriva de SLAM medida es de **1–3 cm** en
1.6–2.4 m: **el orden de magnitud coincide**, así que podría ser parte de ella.

La corrección es una línea (`roll = pitch = 0.0`) y **no se aplica sin medirla**, porque
hacerlo a ciegas sería repetir el error que la creó. Hace falta repetir
`caracterizar_deriva_slam.py` con y sin, y comparar.

### Ajuste fino

Media longitud 0.090 → **0.091**: los huecos publicados bajan 1 mm (9.9 → **9.8 cm** a 0.25
m/s, 10.9 → **10.8** a 0.40). El radio circunscrito sigue en **0.142**, así que
`robot_radius: 0.145` no cambia.

### ✅ Y el modelo cierra: `wheel_radius` **3.5 cm**, LIDAR centrado

La última cota, medida también: **3.5 cm** del suelo al centro del eje (la ficha decía 3.2). Y
el usuario confirmó el **centrado** del LIDAR con las cotas nuevas.

**El modelo cuadra ahora por dos caminos independientes:**

```
wheel_radius 0.035  →  oruga de 0.070 de diámetro
base_height         =  0.070   (medido del suelo a la tapa)
→ la caja del chasis va DEL SUELO A 7 cm, justo como se ve el RVR:
  las orugas ocupan todo el alto del lateral.

0.148 + 2 × 0.035 = 0.218 ≈ 0.217 de ancho total medido.
```

Verificado sobre el URDF compilado: `base_footprint → base_link` = 0.035, láser a **0.155 m**
sobre el suelo (= lo medido, exacto), caja del chasis de 0.000 a 0.070.

✅ **No queda ninguna cota medible sin medir.** Solo `imu_z` (0.05, suposición), que exige abrir
el robot y hoy no afecta a nada: la IMU no se fusiona con la odometría.

**Ficheros:** `atriz_rvr_description/urdf/rvr.urdf.xacro`,
`atriz_rvr_driver/scripts/atriz_rvr_driver/rvr_driver_node.py` (comentarios del cuaternión),
`03_operacion/MEDIDAS_ROBOT.md`, manual **cap. 13** (nuevo) y 12.3–12.10,
`19_paso_estrecho.txt`, `mediciones_banco/medir_collision_monitor.py`, `TRASPASO.md`,
`INSTALACION.md` (F12 ✅ → F13), `CLAUDE.md`.

---

## 2026-07-31 — 🔴 El paso de 40 cm no se cruza, y el URDF tenía las cotas cruzadas

Evidencia: `00_auditoria/evidencia_24_04/19_paso_estrecho.txt`, manual **cap. 12.10**.

### El límite, medido

Con `radius: 0.18` el robot **entró en la boca de un paso de 40 cm y se quedó bloqueado**:

```
ang −84°…−99°   objeto derecho, a 22 cm del centro
ang +72°…+87°   objeto izquierdo, a 17 cm del centro
al frente, a menos de 60 cm: NADA
```

No tocaba nada y tenía el camino despejado delante. Lo paró el monitor porque su círculo mide
18 cm y el borde estaba a 17: **le sobraba 1 cm**. ✅ Salió marcha atrás (58 cm) — `approach`
en vez de `stop`, otra vez.

📝 **Nav2 no llegó a intentarlo**: con el paso abierto por los lados (65 y 63 cm) el
planificador se fue por la ruta ancha, que es lo correcto. La prueba que responde es conducir
recto por `/cmd_vel_raw`, sin planificador que pueda escaquearse.

**No es un fallo: es el compromiso, ahora cuantificado.**

| `radius` | para a | pasillo mínimo |
|---|---|---|
| 0.14 | 5 cm | 28 cm |
| **0.18** | **9 cm** | **36 cm** ← el actual |
| 0.20 | 11 cm | 40 cm |

Para 16 robots en un laboratorio **remoto donde nadie puede levantarlos**, parar a 9–11 cm de
las paredes vale más que cruzar huecos de 40 cm. Es una **decisión de laboratorio**.

### 🔴 Y por el camino: el URDF tenía largo y ancho cruzados

El usuario midió el robot con una cinta, de punta a punta y con orugas:

| | medido | URDF (ficha, «NO MEDIDO») |
|---|---|---|
| frente-atrás | **18 cm** | 21.8 cm |
| lado-lado | **22 cm** | 18.5 cm |

**Dos consecuencias, de distinto peso:**

1. Los huecos publicados hoy salían **2 cm cortos** (media longitud 0.109 en vez de 0.09):
   8.0 → **9.9 cm** a 0.25 m/s, 9.0 → **10.9 cm** a 0.40. El modelo
   `hueco ≈ radius − media longitud + 1 cm` **no se cae**, solo cambia la constante, y las
   conclusiones del fichero 17 siguen valiendo. Están **recalculados, no vueltos a medir**.
2. 🔴 **`robot_radius: 0.11` estaba mal, y eso sí es un error real.** Lo escribí llamándolo
   «radio circunscrito» y es aritmética mal hecha: el circunscrito es **0.142** con las cotas
   medidas y **0.143 incluso con las del URDF**. Con cualquiera de los dos se queda corto — el
   planificador puede trazar rutas donde una **esquina** roza, **sin dar ningún error**. Lo
   tapaba el `collision_monitor` con sus 0.18, que es probablemente por qué `approach` saltaba
   al rodear obstáculos. **Corregido a 0.145** en los dos costmaps.

URDF corregido a 18 × 22. Solo cambia la caja de colisión y la inercia: las ruedas usan
`wheel_separation`, independiente, así que **ningún frame TF se mueve**.

### Nuevo: `03_operacion/MEDIDAS_ROBOT.md`

Lista **todas** las cotas del modelo, cuáles están medidas y cuáles vienen de una ficha, y qué
se rompe si cada una está mal. Lo urgente: **`laser_z`** —la altura a la que el robot ve, hoy
**derivada** de dos fichas de fabricante— y **si el LIDAR está nivelado**, que es la mejor
pista sobre la inclinación de ~8° que sigue abierta.

Explica también qué es `wheel_separation` y por qué aquí **no hace nada**: el RVR resuelve su
propia cinemática, así que solo dibuja las orugas en RViz. Pero está **inconsistente** —
0.150 + 0.025 dan 17.5 cm de oruga a oruga contra 22 cm de robot.

### Dos errores propios

- **Un `radius: 0.15` de contraste que no vale.** Lo lancé para dar la curva completa del
  compromiso y **midió otro hueco** (33.9 cm a −61.5° de rumbo, porque el robot se había
  reorientado). Cruzó *un* hueco, no *el* hueco. Descartado; el valor volvió a 0.18.
- **El X2 no ve un objeto fino en un solo barrido.** Los dos objetos daban 2 y 3 puntos; con un
  `/scan` suelto desaparecen y el detector de huecos deja de ver el paso. Los escaneos que
  funcionaron acumulaban 6–8 s. En `CLAUDE.md`.

**Ficheros:** `atriz_rvr_description/urdf/rvr.urdf.xacro`, `config/nav2_atriz.yaml`,
`config/collision_monitor.yaml`, `mediciones_banco/medir_collision_monitor.py`,
manual cap. 12.3–12.5 y 12.10, `19_paso_estrecho.txt` (nuevo), `17_collision_monitor.txt`
(aviso de corrección), `03_operacion/MEDIDAS_ROBOT.md` (nuevo), `TRASPASO.md`,
`INSTALACION.md` (F11 ✅ → F12), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Rodea obstáculos, y la seguridad hacía abortar a Nav2

Cierra la última laguna: hasta ahora todo se había probado **contra una pared frontal**, así
que estaba demostrado que el robot **para**, no que **rodee**. Evidencia:
`00_auditoria/evidencia_24_04/18_rodear_obstaculo.txt`, manual **cap. 11.13**.

### El obstáculo, caracterizado antes de mover nada

Con `/scan`, y el salto en las distancias es lo que lo **aísla de las paredes** — un umbral
tonto tipo «menos de 1.6 m» las etiqueta a ellas también:

| ángulo | dist | |
|---|---|---|
| −3° | 2.54 m | abierto |
| **0°…+9°** | **0.75–0.77 m** | ← obstáculo |
| +12° | 2.07 m | abierto |

A **0.75 m**, ~**16 cm de ancho**. El robot mide 18.5 cm: **bloquea la línea recta**. Holgura a
su altura: 63 cm por la derecha, 44 por la izquierda.

Los requisitos que se le pidieron al usuario salían todos de un número medido: **más de 25 cm
de alto** porque el plano del LIDAR está a 17.45 cm *(⚠️ ese valor se corrigió después a
**15.5 cm** — era derivado; ver la entrada del robot medido)*; **50 cm libres a un lado** porque el
`collision_monitor` trata al robot como un disco de 36 cm.

### ✅ Lo rodea, y de forma repetible

Objetivo a 1.50 m, **el mismo que la corrida limpia**, para que el obstáculo fuera la única
variable:

```
x=+0.00 y=+0.00 → x=+0.62 y=-0.29 → x=+0.79 y=-0.30 → x=+1.28 y=-0.03
                                     ↑ justo a la altura del obstáculo
```

| | Resultado | | Error | Junto al obstáculo |
|---|---|---|---|---|
| ida 1 | **SUCCEEDED** | 5 s | 8 cm | derecha, y=−0.26 |
| vuelta 1 | **SUCCEEDED** | 13 s | 8 cm | derecha, y=−0.32 |
| ida 2 | **SUCCEEDED** | 5 s | 9 cm | derecha, y=−0.26 |
| vuelta 2 | **SUCCEEDED** | 12 s | 8 cm | derecha, y=−0.30 |

Siempre por el lado con más hueco y con el mismo desvío. **8–9 cm de error: el mismo que sin
obstáculo** — rodear no degradó la precisión.

### 🔴 El hallazgo: la capa de seguridad hacía abortar a Nav2

```
[controller_server] [ERROR] Failed to make progress
[controller_server] [WARN]  [follow_path] [ActionServer] Aborting handle.
```

El objetivo acabó en `SUCCEEDED` porque el árbol replanificó, pero el aborto es real y en un
paso más estrecho podría no recuperarse.

El `SimpleProgressChecker` de fábrica exige **0.5 m en 10 s = 5 cm/s**, y el
`collision_monitor` había frenado al 40 % (0.16 m/s) y `approach` bajó más la velocidad junto
al obstáculo.

> **Con una capa de seguridad delante, ir despacio ya no es prueba de estar atascado** — que es
> lo único que ese comprobador debería detectar. Un robot de verdad atascado se mueve 0 m y lo
> sigue disparando igual.

Relajado a **0.25 m en 15 s** (1.7 cm/s). Tras el cambio, en cuatro navegaciones:
`Failed to make progress` **0**, `Aborting handle` **0**, recuperaciones **0**,
`Control loop missed` **0** — y la seguridad **sí trabajó**: 2 `approach` + 5 `slowdown`,
8.1 s de frenado.

### ✅ `save_map`: hipótesis confirmada y arreglo verificado

La entrada anterior dejaba el arreglo propuesto **sin verificar**. Probado:

| | Resultado |
|---|---|
| servicio de `slam_toolbox`, timeout de 2 s | `0`, **`255`**, `0` — falla ~1 de cada 3 |
| `map_saver_cli` con `save_map_timeout:=10.0` | **`Map saved successfully`** |

Confirma la causa deducida —una carrera contra el `map_update_interval: 5.0`— y **el
procedimiento bueno pasa a ser `map_saver_cli`, no el servicio**. En `CLAUDE.md`.

**Ficheros:** `atriz_rvr_bringup/config/nav2_atriz.yaml`, manual cap. 11.11 y 11.13–11.14,
`18_rodear_obstaculo.txt` (nuevo), `mapas/mapa_rodeo.pgm`, `TRASPASO.md`,
`INSTALACION.md` (F10 ✅ → F11), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Navegando a 0.40 m/s, el máximo del robot

`desired_linear_vel` sube de 0.25 a **0.40**. Evidencia:
`00_auditoria/evidencia_24_04/16_nav2_preparacion.txt` (sección final), manual **cap. 11.10**.

Se sube con las tres condiciones cumplidas y **medidas**, no por optimismo:

1. el robot navegó dos veces sin incidentes a 0.25 (cap. 11.7);
2. el `collision_monitor` está puesto y verificado (cap. 12);
3. y **a 0.40 la capa de seguridad deja *más* hueco que a 0.25** — 9.0 cm contra 8.0 —, porque
   `approach` empieza a frenar antes cuanto más rápido va. Ese es el dato que quitaba el miedo.

### Lo que había que comprobar no era que llegara, sino que fuera a 0.40

Perfil en `/odom` durante la ida de 1.50 m:

| t | v |
|---|---|
| 0.31 s | 0.057 m/s |
| 0.61 s | 0.357 m/s |
| **0.91 s** | **0.407 m/s** ← meseta |
| 2.00 s | 0.407 m/s |

Máxima 0.431 · percentil 90 **0.412 m/s**. Coherente con la rampa de ~0.5 s ya medida y con
`max_linear_accel: 0.8`.

| | Desde | Hasta | Resultado | Error | v (p90) |
|---|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.50, 0.00) | **SUCCEEDED** | **8 cm** | 0.412 m/s |
| vuelta | (1.42, −0.01) | (0.00, 0.00) | **SUCCEEDED** | **8 cm** | 0.409 m/s |

📝 **8 cm las dos veces, contra 9–10 cm a 0.25 m/s: subir la velocidad no empeoró la
precisión.** La vuelta tardó 16 s para 1.42 m, giro de 180° incluido.

### La capa de seguridad no estorbó

Cuatro frenados en toda la sesión —2125, 1582, 130 y 65 ms—, **ninguno una parada**, cero
conductas de recuperación y cero fallos de plan. ⚠️ No se ha aislado **qué** los disparó: se
registra el hecho, no una causa inventada.

### 🔴 Y salió un fallo nuevo: `save_map` da 255 de forma intermitente

```
[map_saver] Saving map from 'map' topic to '…' file
[map_saver] [ERROR] Failed to spin map subscription
```

**No es el fallo de la Fase 4.** Aquel era `Package 'nav2_map_server' not found` y se arregló
instalando `navigation2`. Aquí el paquete está, el `map_saver` arranca, se configura y **se
queda sin mapa**: perseguir la instalación sería perder el tiempo.

Causa, deducida de dos números del propio sistema: `map_update_interval: 5.0` en slam_toolbox
contra el `save_map_timeout: 2.0` por defecto del saver. **Es una carrera** — explica que
funcionara dos veces y fallara la tercera.

⏳ **Arreglo propuesto, NO VERIFICADO:** reintentar; o `map_saver_cli` con
`save_map_timeout:=10.0`; o bajar `map_update_interval`, que cuesta CPU. Hace falta resuelto
para la Fase 4c. Anotado en `CLAUDE.md` como trampa de diagnóstico.

**Ficheros:** `atriz_rvr_bringup/config/nav2_atriz.yaml`, manual cap. 11.10–11.12 y 12.9,
`16_nav2_preparacion.txt`, `TRASPASO.md`, `INSTALACION.md` (F9 ✅ → F10), `CLAUDE.md`.

---

## 2026-07-31 — ✅ La capa de seguridad: el robot para antes de chocar

`collision_monitor` configurado, medido contra una pared y verificado. Evidencia:
`00_auditoria/evidencia_24_04/17_collision_monitor.txt`, manual **cap. 12**.

### La decisión de arquitectura: no va con Nav2

El ejemplo oficial lo pone con la navegación. Aquí no, y la razón sale del propio proyecto:
**los estudiantes teleoperan sin Nav2** —la web hablará por rosbridge (plan, Fase 5)—, así que
con el monitor colgando de `nav2.launch.py` el caso peligroso de verdad, una persona
conduciendo el robot contra una pared **desde otro edificio**, no estaría protegido.

Vive en `robot.launch.py`, con su propio `lifecycle_manager`. Y la regla que lo hace funcionar:

```
    Nav2 (velocity_smoother) ─┐
    web / rosbridge          ─┼─► /cmd_vel_raw ─► collision_monitor ─► /cmd_vel ─► driver
    teleop / scripts         ─┘
```

**`/cmd_vel` tiene un solo publicador.** Publicar ahí funciona —el driver obedece— pero salta
la seguridad sin dar ningún aviso.

### 🔴 Un agujero real, encontrado contando publicadores

```
$ ros2 topic info /cmd_vel --verbose
Publisher count: 6      ← behavior_server ×5  +  collision_monitor
```

El `behavior_server` abre **un publicador por conducta** (`spin`, `backup`,
`drive_on_heading`, `wait`, `assisted_teleop`). Los cinco publicaban directamente al robot. Y
es el peor sitio posible: las conductas de recuperación se ejecutan justo cuando el robot está
**atascado**, o sea pegado a algo — `backup` habría retrocedido a ciegas.

Arreglado con un remapeo. **No lo delataba ningún error**: solo salió de mirar el número.

### 🔴 `approach` no es una parada de seguridad, y lo puse mal

Primera configuración, `radius: 0.11` (el `robot_radius` de los costmaps). El robot paró a
**1.1 cm de la pared**. El monitor actuó —el log muestra `slowdown` y `approach`—; lo que
estaba mal era mi modelo:

> `approach` escala la velocidad para que el choque caiga justo en `time_before_collision`.
> Según baja la distancia baja la velocidad, así que el robot se acerca **asintóticamente al
> contacto**. Es un frenado suave, no una parada.

Con media longitud de chasis 0.109 m, la asíntota era 0.1 cm. **Funcionó exactamente como está
escrito.** La holgura se consigue **inflando el círculo**: `hueco ≈ radius − 0.109 + ~1 cm`.

### ✅ Medido con `radius: 0.18`

| velocidad | recorrido | **hueco real** | predicción |
|---|---|---|---|
| 0.25 m/s | 191 cm | **8.0 cm** | 8 cm |
| 0.40 m/s | 191 cm | **9.0 cm** | — |

A 0.40 m/s —el máximo del robot— para **más lejos**, no más cerca: el controlador empieza a
frenar antes cuanto mayor es la velocidad.

### ✅ No queda atrapado, y sin LIDAR no conduce

Los dos polígonos son `approach` y `slowdown`, **nunca `stop`**, y la razón es operativa: un
`stop` fijo para *cualquier* movimiento mientras haya algo dentro, así que un robot pegado a
una pared se congela. En un laboratorio **remoto no hay nadie que lo levante**.

| Prueba | Resultado |
|---|---|
| escape desde 1.1 cm pegado a la pared | retrocedió **196 cm** ✅ |
| `kill -9` al LIDAR + comandar 0.10 m/s 2.5 s | **0.0 cm** ✅ bloqueado |
| Nav2 con la seguridad en medio | **SUCCEEDED**, 9 cm de error, 39 cm a la pared |

⚠️ Salir de un rincón es **lento**: la caja de precaución sigue viendo la pared y frena al
40 %. Conviene saberlo antes de pensar que el robot no responde.

### 🔴 El límite que ninguna configuración arregla

El plano de barrido del X2 está a **17.45 cm del suelo**. Todo lo más bajo —un zócalo, una
regleta, un pie de mesa que se ensancha abajo— es **invisible** y el robot lo embestirá sin
frenar. No es un fallo de configuración: es lo que un LIDAR 2D puede ver. **Tiene que ir en
las instrucciones a los estudiantes.**

📝 Lo que sí está cubierto: el `range_min: 0.1` del X2, montado en el centro, deja su punto
ciego **dentro del chasis**. No hay zona muerta alrededor del robot.

### Y un error propio, dos veces

Me maté el shell dos veces con `pgrep -f "…[y]"`: el truco del corchete protege de que el
patrón se encuentre a sí mismo, **no** de que la cadena buscada aparezca en otra parte de la
misma orden (un heredoc con la ruta, un `nohup` más abajo). Documentado en `CLAUDE.md` junto a
la trampa de `pkill -f` que ya estaba, con la alternativa: matar por `comm` con `ps`, sin `-f`.

**Ficheros:** `atriz_rvr_bringup/config/collision_monitor.yaml` (nuevo),
`launch/robot.launch.py`, `launch/nav2.launch.py`,
`mediciones_banco/medir_collision_monitor.py` (nuevo), manual cap. 12,
`17_collision_monitor.txt` (nuevo), `TRASPASO.md`, `INSTALACION.md` (F8 ✅ → F9),
`CLAUDE.md`.

---

## 2026-07-31 — ✅ Nav2 NAVEGA: primera navegación autónoma

**El robot llega solo a un punto del mapa.** Dos objetivos completados, ida y vuelta:

| | Desde | Hasta | Resultado | Error final |
|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.00, −0.03) | **SUCCEEDED** | **10 cm** |
| vuelta | (0.90, 0.00) | (0.00, 0.00) | **SUCCEEDED** | **9 cm** |

El error coincide con la `xy_goal_tolerance: 0.10` configurada — el controlador para al entrar
en tolerancia, así que **no es casualidad**.

### El riesgo del QoS de `/scan` era infundado

Se avisaba en el cap. 11.6 de que un desemparejamiento BEST_EFFORT/RELIABLE dejaría el costmap
**vacío sin dar error**. Comprobado: `/scan` acabó con **tres** suscriptores —`slam_toolbox`,
`local_costmap` y `global_costmap`— todos BEST_EFFORT. Nav2 usa el perfil de datos de sensor,
que empareja con el driver.

Y no basta con que estén suscritos: se verificó que los costmaps **ven obstáculos de verdad**
— 905 celdas ocupadas en el local (60×60), 1983 en el global (148×139).

### 🔴 El primer objetivo abortó, y no era la configuración

```
[controller_server] [ERROR] [RPPPathHandler]: Exception in transformPose:
  Lookup would require extrapolation into the future … from frame [odom] to frame [map]
```

Antes de tocar nada se midió, en vez de suponer (regla nº4):

| Sospecha | Medido |
|---|---|
| ¿faltan tolerancias? | RPP **0.2**, costmaps **0.3** — puestas |
| ¿`use_sim_time` incoherente? | **False** en los cinco nodos, en SLAM y en el driver |
| ¿`map → odom` con huecos? | **50.0 Hz**, mediana 20.0 ms, **máximo 25 ms**, cero huecos > 200 ms |

**Era transitorio**: el buffer TF del controlador aún no se había llenado con los nodos recién
arrancados. El segundo objetivo, idéntico, funcionó.

⚠️ **Consecuencia práctica: dar unos segundos entre activar Nav2 y mandar el primer objetivo.**
Un `ABORTED` inmediato tras arrancar **no** significa que la configuración esté mal. Queda en
el manual (11.8) porque es exactamente el tipo de falso positivo que hace perder una tarde.

### El Pi 4 aguanta el stack entero

~**89 %** de un núcleo y ~477 MB entre los nueve procesos (driver 19.7 %, `bt_navigator`
14.4 %, `controller_server` 13.1 %…). `loadavg` **2.53** sobre 4 núcleos, **58.9 °C**,
`throttled=0x0`, RAM 1.5 GB de 7.6.

**Nav2 solo son ~58 % de un núcleo**: es la pieza más pesada con diferencia, como se preveía —
pero **queda margen para `rosbridge`** en la Fase 5.

### Lo que esto NO prueba

Las dos navegaciones fueron **en línea recta por un pasillo despejado**. Se ha probado que el
robot **llega**; no que **rodee** un obstáculo. Eso queda pendiente, junto con el
`collision_monitor` —la capa de seguridad, necesaria antes de dejar esto con estudiantes— y
subir `desired_linear_vel` de 0.25 a 0.40 (el robot llega a 0.40, ya medido).

Mapa guardado: `mapas/mapa_nav2_navegado.pgm` (20726 bytes).

**Ficheros:** `00_auditoria/evidencia_24_04/16_nav2_preparacion.txt` (sección final),
manual cap. 11.7–11.10, `TRASPASO.md`, `INSTALACION.md` (F7 ✅ → F8 = `collision_monitor`),
`CLAUDE.md` (valores de referencia).

---

## 2026-07-31 (parte 7) — Nav2 instalado, y otra retractación mía

### Nav2: `navigation2`, NO `nav2-bringup`

Comprobado **antes** de instalar nada:

| | Paquetes | Qué arrastra |
|---|---|---|
| `ros-jazzy-navigation2` | **309** | lo que se usa: amcl, bt-navigator, controller, costmap-2d, planners, `map-server`… |
| `ros-jazzy-nav2-bringup` | **621** | lo anterior **+ Gazebo**: `nav2-minimal-tb3-sim`, `tb4-sim`, `ros-gz-sim`, y `pocketsphinx-en-us` |

`nav2-bringup` son ficheros de ejemplo para TurtleBot **en simulador**. Los launch de Atriz los
escribimos nosotros, igual que con `slam_toolbox`, y esos 312 paquetes acabarían replicados en
los **16 robots** vía imagen dorada.

**Instalado y verificado:** 30 paquetes `nav2`, los diez que importan presentes, **cero** de
simulador, y el disco sube solo 900 MB (5.4 → 6.3 GB).

### ✅ `save_map` arreglado — el diagnóstico de la Fase 4 era correcto

Con `nav2-map-server` instalado, `/slam_toolbox/save_map` devuelve **`result=0`** y genera el
`.pgm` + `.yaml` que Nav2 carga. Antes fallaba con `result=255` y el error real solo aparecía
en el log de slam_toolbox: `Package 'nav2_map_server' not found`.

### La configuración de Nav2, con los valores medidos

`atriz_rvr_bringup/config/nav2_atriz.yaml` + `launch/nav2.launch.py`. **Todos** los valores del
robot sustituidos por los medidos:

| | Atriz | Ejemplo de Nav2 (TurtleBot) |
|---|---|---|
| `robot_radius` | **0.11 m** | 0.22 m — **el doble** |
| `max_vel` lineal | 0.40 m/s | 0.26 m/s |
| `max_vel` angular | 2.0 rad/s | 1.0 rad/s |
| alcance del LIDAR | **8.0 m** | 20.0 m |

El `robot_radius` es el que más duele: con 0.22 el robot se negaría a pasar por huecos por los
que cabe de sobra. Y un `raytrace_max_range` de 20 m haría que Nav2 despejara como «libre»
espacio que el sensor **nunca midió**.

Decisiones, con su porqué: **RPP** y no MPPI/DWB (mucho más barato en un Pi 4 que ya lleva el
driver al 23 %), **NavFn** y no Smac (el robot gira sobre su eje), costmap local de **3 × 3 m**,
`lookahead_dist: 0.4` escalado al robot, y **`desired_linear_vel: 0.25`** aunque llegue a 0.40 —
es la primera vez que navega solo.

**NO se configuran `map_server`/`amcl`**: Nav2 se apoya en `slam_toolbox`, ya verificado. Meter
AMCL ahora pondría **dos nodos publicando `map → odom`**, y eso parte el árbol TF sin dar error
— el fallo que costó la Fase 4. Ni el **`collision_monitor`**: hace falta antes de dejar esto
con estudiantes, pero configurar sus umbrales sin haber visto navegar al robot sería adivinar.

⏳ **Nada de esto se ha probado contra el robot todavía.**

### 🔴 Y una retractación: el robot SÍ alcanza la velocidad comandada

Al medir la velocidad **angular** para configurar Nav2 salió que sigue al comando al
**99–102 %** hasta 2.0 rad/s. Eso no cuadraba con la lineal, que según nuestra propia
documentación solo llegaba al 63 % a 0.40 m/s. Así que medí el **perfil en el tiempo** en vez
de la media:

```
comandado 0.20 m/s  ->  meseta 0.199  (100 %)   alcanzada en ~0.5 s
comandado 0.40 m/s  ->  meseta 0.401  (100 %)   alcanzada en ~0.5 s
```

**No hay tope.** La causa del error era la **ventana de medida**: iba hasta la última muestra
del locator, y `conducir()` duerme 1.2 s **después** de `drive_stop()`, así que la media
incluía el robot frenando y parado.

📝 Es **el mismo fallo** que ya había arreglado en la prueba de marcos y que dejé sin arreglar
en el barrido de velocidades. Arreglado ahora en `medir_velocidad_rvr.py`.

Lo que sí existe es una **rampa de aceleración de ~0.5 s**. Importa para Nav2 —el robot no
cambia de velocidad instantáneamente— pero es otra cosa, y se configura con `acc_lim`, no con
`max_vel`.

---

## 2026-07-31 (parte 6) — Los TRES bugs de marcos, arreglados y verificados

Implementa el arreglo que la parte 5 dejó definido. Evidencia: `15_velocidad_odom.txt`.
Código: `Atriz_rvr` rama `ros2`.

**Los sensores del RVR siempre estuvieron bien.** Lo que fallaba era cómo el driver combinaba
sus marcos. Las tres piezas se implementaron y **se verificaron una a una**, como se acordó —
no las tres de golpe.

| Pieza | Qué se hizo | Antes | Después |
|---|---|---|---|
| **1. Orientación** | restar el yaw del arranque | −74.6° / +64.9° en reposo | **+0.00°** |
| **2. Posición** | quitar el `−Y` y rotar −90° | dirección vs yaw: −89.7° | **+0.03°** |
| **3. Velocidad** | rotación + proyección sobre el rumbo | `(-0.000, -0.200)` avanzando recto | **`(+0.101, +0.001)`** vs 0.099 real |

Y la prueba B de la pieza 2: al girar 90°, el yaw cambió **+89.87°** y el desplazamiento
**+90.00°** — mismo sentido. Antes iban en sentidos opuestos.

📝 **Cinco arranques dieron cinco offsets de yaw distintos** (+51.1°, +52.7°, +56.5°, −74.6°,
+64.9°). Confirma que no había constante posible: solo se puede medir en cada arranque.

### 🔴 Una trampa nueva que costó dar por fallida una corrección correcta

**`colcon build` lanzado desde `src/Atriz_rvr` en vez de la raíz del workspace** crea ahí
dentro un **workspace parásito** (`build/`, `install/`, `log/`), compila contra él, dice
«Finished», y el cambio **nunca llega al sistema que se está ejecutando**. El mensaje de éxito
es idéntico al bueno.

Pasó **dos veces**. La primera hizo que la pieza 2 diera 🔴 con el código correcto; la segunda
casi cuela porque el `grep` de verificación usaba **ruta relativa** y acabó mirando el install
parásito.

→ Documentado en `CLAUDE.md` con cómo detectarlo. Y `log/` añadido al `.gitignore` de
`Atriz_rvr`: `build/` e `install/` ya estaban, `log/` no.

### Y un recordatorio sobre medir la referencia

Una primera corrida de la pieza 3 dio un 15 % de error aparente. **No era el driver**: la
ventana de medida eran 0.7 s justo después de un giro de 90°. Con 3 s de ventana el error baja
al 2 %. **La referencia también hay que medirla bien.**

---

## 2026-07-31 (parte 5) — El modelo de marcos del RVR, completo

Cierra la investigación de la parte 4. Evidencia: `15_velocidad_odom.txt`.
**No se implementa el arreglo**, a propósito: ver el final.

### Cinco medidas, y cada una descartó una hipótesis

| | yaw en reposo | desplazamiento | qué descartó |
|---|---|---|---|
| sesión previa ×2 | −74.6° | −90.2°, −90.0° | hay desfase, no se sabe de qué depende |
| tras apagar/encender | +64.9° | −90.0° | **no es constante** (−15° → −155°) |
| tras girar 90° + apagar/encender | **+0.5°** | −90.0° | **el yaw se pone a cero AL ENCENDER** |
| tras girar 90° a mano, sin apagar | −89.9° | −89.7° | el locator **se realinea al arrancar el driver** |
| girando con `cmd_vel`, sin reiniciar | +89.4° (Δ) | **−88.8°** (Δ) | 🔴 **manos contrarias** |

### El modelo que sale, y explica las cinco

1. **El marco del locator es FIJO** y se **realinea en cada `reset_locator_x_and_y()`** — es
   decir, al arrancar el driver. Su eje X queda **90° girado** respecto al «adelante» del
   robot: por eso avanzar recto da siempre −90°.
2. **El yaw se pone a cero al ENCENDER el RVR**, no con `reset_yaw()`, que no hace nada. Los
   valores raros de antes eran de un robot manipulado *después* de encenderse.
3. 🔴 **La posición y la orientación de `/odom` tienen manos contrarias.** El `−Y` que el
   driver aplica al locator **sobra**.

**El yaw es el bueno** — contrastado contra el LIDAR, un sensor físico con convención ROS
conocida. Y el `−Y` vino de una **inferencia inválida**: se dedujo midiendo que «al curvar a la
izquierda `dy` salía negativo», dando por hecho que el eje X del locator apuntaba adelante,
cuando está 90° girado. Es el mismo patrón que ya falló otras veces hoy: **deducir en vez de
medir**.

### El arreglo, definido pero NO implementado

| | Qué hacer |
|---|---|
| **Posición** | quitar el `−Y` del locator y **rotar −90°** |
| **Velocidad** | la misma rotación, y proyectar sobre el rumbo |
| **Orientación** | restar el yaw del arranque (`yaw − yaw₀`) |

No se implementa hoy **a propósito**: toca posición, velocidad y orientación a la vez, y esta
sesión ya acumuló tres errores por ir rápido (el choque, elegir 180° dos veces para una prueba
de signo, y este `−Y` deducido en vez de medido). Se verifica cada pieza por separado.

**Verificación cuando se haga:** una corrida recta debe dar la dirección del desplazamiento
**igual** al yaw publicado, y girar el robot debe mover ambas en el **mismo** sentido.

### 👤 El robot no quedó en su posición inicial

La última prueba lo dejó ~26 cm adelantado y ~19 cm de lado respecto a la marca. Recolocarlo
antes de retomar, y comprobar la orientación con un empujón de 10 cm.

---

## 2026-07-31 (parte 4) — 🔴 RETRACTACIÓN: el stream `Velocity` NO era basura

Manual, cap. 2 y 10. Evidencia: `00_auditoria/evidencia_24_04/15_velocidad_odom.txt`.
Herramienta nueva: `mediciones_banco/medir_velocidad_rvr.py`.

### Lo que este proyecto daba por firme, y era falso

Desde el 2026-07-30, en `CLAUDE.md`, el manual, `TRASPASO.md`, el CHANGELOG y en comentarios
del propio driver:

> «El stream `Velocity` del RVR no refleja la velocidad real. Con el robot avanzando a
> 0.147 m/s comprobados por desplazamiento, el sensor reportaba 0.001 m/s.»

Se usó para declarar la velocidad de `/odom` un **bloqueante de Nav2**.

### Lo medido

```
dirección del desplazamiento del locator:  +90.2°
dirección del vector Velocity:             +90.1°     ← 0.1° de diferencia
módulo real 0.199 m/s  ·  Velocity 0.200              ← 0 % de error
```

**`Velocity` es EXACTO.** La observación original era cierta, pero la conclusión no: el stream
viene en el marco del **MUNDO**, y se leyó solo su componente X con el robot encarado a ~90° de
ese eje. Ahí X vale ~0 aunque el robot cruce la habitación.

### 🔴 Bug A — el driver mete una velocidad del mundo en un campo del robot

`odom.twist` va expresado en `child_frame_id`, o sea en el marco del **robot**. Medido a través
de ROS con el robot avanzando recto a 0.199 m/s:

```
odom.twist.linear publicado:  (-0.000, -0.200)
debería ser:                  (+0.199, +0.000)
```

Solo coincide cuando el robot mira al eje X del odom — que es justo el caso en el que se probó.

### 🔴 Bug B (nuevo) — y tras apagar el robot resultó ser DOS problemas

Medido con el RVR apagado y encendido de por medio:

| | yaw en reposo | desplazamiento | desfase |
|---|---|---|---|
| sesión previa, medida 1 | −74.6° | −90.2° | −14.2° |
| sesión previa, medida 2 | −74.6° | −90.0° | −15.5° |
| **tras apagar y encender** | **+64.9°** | **−90.0°** | **−154.9°** |

🔴 **El desfase NO es constante**: pasó de ~−15° a −154.9° solo con apagar y encender.
**Una corrección constante no sirve.** Y la tabla separa dos problemas independientes que
hasta ahora se veían como uno:

1. **El yaw del cuaternión tiene un origen arbitrario en cada encendido.** `reset_yaw()` no
   lo corrige.
2. **El marco del locator está girado ~90° respecto al robot.** El robot avanza recto y su
   odometría dice que se mueve a −90.0°, en las **tres** medidas.

En los tres casos: `desfase = −90° − yaw_reposo`. Los «~15°» eran la suma casual de ambos.

⚠️ **Variable no controlada:** al apagar, el robot también se **recolocó** en el centro, así
que la orientación física pudo cambiar. Que el desplazamiento siguiera dando −90° **apunta** a
que el marco del locator es relativo al robot, pero **no lo demuestra**.

### La medida original que lo destapó

```
yaw en reposo justo tras arrancar el driver:  -74.6°   ← reset_yaw() NO lo pone a cero
desplazamiento -90.2°  ·  yaw publicado -76.0°  ->  desfase -14.2°
desplazamiento -90.0°  ·  yaw publicado -74.5°  ->  desfase -15.5°   (driver reiniciado)
```

**~15° entre la orientación y la posición del mismo mensaje.** ⚠️ **SIN DETERMINAR** si
sobrevive a un apagado del RVR: las dos medidas son de la misma sesión de encendido. 👤 Hace
falta apagar y encender el robot y repetir.

### No se arregla ninguno todavía, a propósito

El arreglo de A es proyectar sobre el rumbo, así que **depende de B**. Aplicarlo ahora daría un
3 % de error en la proyección y dejaría los 15° intactos. Los dos se documentan en el código y
se arreglan juntos.

### Lo demás que salió

| | |
|---|---|
| **Locator validado con cinta métrica** | 101.1 medidos contra **101.0 reales** — 1 mm en 1 m |
| **Encoders calibrados** | **7792 ticks/m**, contra la cinta y no contra otro sensor |
| `Speed` (escalar) | existe, y es el módulo de `Velocity`. Comprobación cruzada barata |
| ~~El robot no alcanza la velocidad comandada~~ | ⚠️ **RETRACTADO 2026-07-31** (parte 7): era la ventana de medida, que incluía el período tras la frenada. La meseta real es del **100 %** a 0.20 y a 0.40 m/s. Lo que sí hay es una **rampa de ~0.5 s** |

### Dos errores de método míos

- **Choqué el robot.** Ejecuté `--calibrar` (avanza 1 m y para) y después el barrido **sin
  recolocarlo**. La herramienta hace `reset_locator_x_and_y()`, así que su cero decía 0 mientras
  el robot estaba un metro adelantado. 🔴 **Poner a cero la odometría no es devolver el robot al
  inicio**: el cero de software se mueve con el robot. Sin daños. Arreglado en la herramienta —
  cada modo vuelve al punto de partida y el barrido va y vuelve en cada velocidad.
- **Elegí 180° para una prueba de signo. Dos veces.** 180° es exactamente el ángulo donde el
  signo de un giro es ambiguo, y ya me había pasado al determinar el yaw. La prueba buena no
  gira nada: compara la dirección de `Velocity` con la del desplazamiento del locator, que ya
  están en el mismo marco.

---

## 2026-07-31 (parte 3) — La deriva de SLAM, caracterizada: es pequeña

Cierra la única incógnita que dejó la Fase 4. Manual, cap. 9.12. Evidencia:
`00_auditoria/evidencia_24_04/14_deriva_slam_caracterizada.txt`.

**Herramienta nueva:** `mediciones_banco/caracterizar_deriva_slam.py`.

### El problema: dos medidas que se contradecían

```
corrida 1 (2.62 m de recorrido)  ->  87.8 cm y 10.9°
corrida 2 (1.78 m de recorrido)  ->   0.9 cm y  3.1°
```

Dos órdenes de magnitud, y diferían en **dos cosas a la vez**: la distancia recorrida y que en
la primera el robot rozó obstáculos. Con dos variables cambiando no se puede atribuir la causa
a ninguna.

### Cómo se controlaron las variables

- Mismo pasillo despejado de 3 m × 0.8 m, robot en el **centro**, punto de partida marcado.
- **Orientación comprobada ANTES de empezar** con un empujón de 10 cm. La vez anterior se
  movió primero y se perdió una corrida entera contra los obstáculos.
- Nadie cruzó la zona en los ~20 min — el LIDAR ve piernas a 17.5 cm perfectamente.
- **Dos distancias alternadas**, para separar «distancia» de «obstáculos».
- **`slam_toolbox` reiniciado de cero en cada corrida.** Sin esto las últimas parten con el
  mapa que construyeron las anteriores y la comparación no vale.

### Resultado: 6 corridas

| Recorrido | n | Deriva mediana | Peor caso | σ |
|---|---|---|---|---|
| ~159 cm | 3 | **1.0 cm** y 1.3° | 2.7 cm | 1.0 cm |
| ~237 cm | 3 | **2.7 cm** y 2.3° | 3.2 cm | 0.6 cm |

**El error cabe dentro de una celda del mapa** (5 cm) y es un orden de magnitud menor que el
radio del robot (~11 cm). Crece con la distancia de forma coherente (0.63 % del recorrido en
las cortas, 1.14 % en las largas): es el comportamiento normal de una odometría corregida por
emparejado de barridos, no el patrón de un fallo.

Y el mapa es **repetible**: las tres corridas largas dieron +2347, +2321 y +2334 celdas.

### 🔴 Los 87.8 cm de la Fase 4 eran una anomalía

La corrida larga de aquí recorre 237 cm —comparable a los 262 cm de aquella— y sale **30 veces
mejor**. ⚠️ **No se reprodujo la anomalía a propósito**, así que «rozar obstáculos» sigue
siendo la explicación más probable, **no una causa demostrada**. Lo que sí queda demostrado es
que no es el comportamiento normal del sistema.

### ✅ Consecuencia: un bloqueante menos para Nav2

La localización ya no bloquea. Quedan dos: la **velocidad de `/odom`** (que pasa a ser el
siguiente paso) y la **inclinación de ~8°** — cuya gravedad queda acotada por estos números:
con la inclinación presente, la deriva es de 2.7 cm, así que no está arruinando el emparejado.

### La lección de método

Con dos puntos que se contradicen no se puede concluir nada, y la tentación es quedarse con el
que conviene. Seis corridas con las variables controladas costaron 20 minutos y convirtieron
«no sabemos si sirve para Nav2» en un número con desviación típica.

---

## 2026-07-31 (parte 2) — Fase 4 CERRADA: SLAM mapea de verdad

```
celdas conocidas   657 -> 3110      área  1.64 -> 7.78 m²   (casi 5x)
nodos del grafo      4 -> 8         recorrido 262.5 cm
✅ EL MAPA CRECE AL MOVERSE
```

Manual cap. 9. Evidencia: `00_auditoria/evidencia_24_04/13_fase4_cerrada.txt` y
`mapas/mapa_fase4_cerrada.*`.

Para llegar aquí hubo que arreglar **tres cosas** y corregir **dos herramientas propias**.
Ninguna de las cinco daba un error: todas fallaban en silencio.

### 🔴 1. `/scan` y `/odom` se contradecían en el sentido de giro

Girando el robot y correlacionando el barrido de antes con el de después:

```
giro real (odom):          -47.0°
desplazamiento del scan:   -47.0°   <- MISMO signo; la física exige OPUESTOS
```

⚠️ **Y eso solo no dice cuál de los dos está mal.** La primera versión de
`verificar_inverted_lidar.py` concluyó «`/scan` está espejado» y **era concluir de más**:
los datos encajaban igual con «el yaw de `/odom` está invertido». Herramienta corregida
para reportar la contradicción y enumerar las dos causas.

**Lo desempató una observación física**, que ningún software del robot puede hacer: se
mandó un giro positivo y **se miró el robot** — giró a la izquierda. Como el SDK documenta
`yaw_angular_velocity` con la regla de la mano derecha y el driver pasa `angular.z` sin
tocarlo, el giro real fue +47°, el barrido (−47°) era correcto, y el equivocado era el yaw
de `/odom`.

✅ **`inverted: true` del YDLIDAR era correcto. El LIDAR nunca fue el problema.**

### 🔴 2. El RVR no usa una sola convención de ejes

Se aplicó la conversión FRD→FLU a los cuatro sensores **por analogía**, y eso rompió dos.
Hubo que medir cada uno por separado:

| Sensor | Estaba | Acción |
|---|---|---|
| cuaternión | yaw invertido | `(x, -y, -z, w)` |
| locator | `y` invertida | `-y` |
| giroscopio | **ya estaba bien** | solo deg/s → rad/s |
| acelerómetro | **ya estaba bien**, y en **g** | solo **g → m/s²** |

En reposo el acelerómetro daba módulo **0.973**: el RVR reporta en **g**, y el driver de
ROS 1 tampoco lo convertía. Ahora `(-1.314, -0.004, +9.281)`, módulo 9.374 m/s².

📝 De propina, el acelerómetro da la inclinación del robot por una **tercera vía
independiente**: `asin(1.314/9.374) = 8.1°`, coherente con los ~7° del árbol TF y del Roll.

Efecto sobre la coherencia de SLAM, misma prueba antes y después:

```
deriva tras un giro de 360° y volver al sitio
  antes:   6.6 cm y 30.0°
  después: 0.2 cm y  1.8°
```

### 🔴 3. `fixed_resolution: false` hacía que slam_toolbox descartara los barridos

El X2 entrega barridos de longitud **variable** (254 unas veces, 255 otras) y
`slam_toolbox` registra el sensor con el tamaño del primero, **descartando el resto**. Una
sola línea en su log, ningún error:

```
LaserRangeScan contains 254 range readings, expected 255
```

Ese parámetro se puso a `false` en la Fase 3.2 **para callar un aviso cosmético**. Cambiar
un parámetro para silenciar un aviso cambió un síntoma visible por uno invisible. Con
`true`: 142 barridos, **todos de 260 puntos**.

📝 El mismo problema reventaba `verificar_inverted_lidar.py` con `IndexError`. Corregido
remuestreando a una rejilla angular fija. Mismo origen, dos víctimas.

### 🔴 4. Mi propia herramienta daba un falso negativo

Con todo lo anterior arreglado, `medir_slam_ros2.py` **seguía** diciendo «el mapa no
creció». No era SLAM: era la prueba. Avanzaba 40 cm y retrocedía otros 40, y solo miraba
el mapa al final — con el robot otra vez donde empezó.

`slam_toolbox` cuenta la distancia **desde el último nodo del grafo**, no desde donde
empezó la prueba: con el umbral en 0.3 hicieron falta **~0.85 m**. Y girar en el sitio no
basta — cuatro vueltas y media seguidas no cambiaron ni una celda.

Lo demostró mirar el **grafo**, no el mapa, y compararlo contra la **configuración de
fábrica** (que se comportó igual, descartando de un golpe que fueran mis parámetros).

La herramienta ahora avanza en **tramos**, mide **después de cada uno**, y el veredicto usa
el mapa **más grande visto**, no el último.

### Coste en el Pi 4

| Proceso | CPU | RSS |
|---|---|---|
| `rvr_driver_node` | 33.6 % | 86.3 MB |
| `async_slam_toolbox_node` | 5.0 % | 50.3 MB |
| `ydlidar_ros2_driver_node` | 2.6 % | 30.8 MB |
| `robot_state_publisher` | 0.5 % | 32.4 MB |

64.2 °C. El driver sube de 15.9 % a 33.6 %: lleva ahora el keepalive, el detector de
silencio y las conversiones de ejes.

### ⚠️ Lo que queda abierto

### Segunda corrida, en espacio despejado — y contradice a la primera

La primera se hizo en un hueco demasiado justo y el robot llegó a **rozar obstáculos**. Se
repitió con 2 m × 0.8 m libres y el robot centrado:

```
recorrido 178.5 cm    celdas 2367 -> 3299 (+932)    área 5.92 -> 8.25 m²
✅ EL MAPA CRECE AL MOVERSE
deriva al volver al punto de partida:  0.9 cm y 3.1°
```

🟡 **La deriva NO está caracterizada: las dos medidas se contradicen.** Mismo binario, el
mismo día:

| Corrida | Recorrido | Deriva | Espacio |
|---|---|---|---|
| 1ª (`--pasos 3`) | 262.5 cm | **87.8 cm y 10.9°** | justo, rozó obstáculos |
| 2ª (`--pasos 2`) | 178.5 cm | **0.9 cm y 3.1°** | 2 m × 0.8 m despejados |

**Ninguna se presenta como «la buena».** En ambas el mapa crece y es utilizable, pero con dos
órdenes de magnitud de diferencia no se puede decir aún si la pose sirve para Nav2. **Hay que
repetir la prueba varias veces en espacio despejado antes de atribuir nada** — regla nº 4 del
proyecto, y aquí era fácil saltársela.

Tres sospechas **sin aislar**: rozar obstáculos en la primera, la inclinación de ~8° que hace
al LIDAR barrer un plano inclinado, y la velocidad de `/odom`, que sigue siendo basura.

📝 Y una lección de operación que costó una corrida entera: **hay que decir cuánto espacio
hace falta ANTES de mover el robot.** `medir_slam_ros2.py` necesita, con el robot en el
centro, 1 m por delante, 1 m por detrás y 40 cm a cada lado — y nada a menos de 60 cm, porque
el robot **no esquiva obstáculos**, solo tiene watchdog. Documentado ya en el manual 9.13 y en
`CLAUDE.md`.

🔴 La inclinación de ~8°, ahora confirmada por **tres** vías independientes. Causa sin
determinar.

---

## 2026-07-31 — El RVR se dormía a los 300.6 s: medido y arreglado

Cierra el fallo grave que abrió la Fase 4. Manual: **cap. 9.8a–9.8d**. Evidencia:
`00_auditoria/evidencia_24_04/12_keepalive_rvr.txt`.

### ✅ El timeout, medido: 300.6 s = 5.01 min

Arrancando el driver con el keepalive desactivado a propósito (`keepalive_period:=0.0`) y
vigilando el **ritmo** de `/odom` 12 minutos, el robot se durmió **dos veces**:

| | Aguantó | Detectado tras | Reanudado en |
|---|---|---|---|
| Sueño 1 (a los 3.9 min) | **300.6 s** | 3.4 s | 0.004 s |
| Sueño 2 (a los 9.0 min) | **300.6 s** | 3.4 s | 0.004 s |

**300.6 s idénticos a la décima de segundo no es una heurística: es un temporizador del
firmware.** Coincide con los 5 min documentados del RVR y cae dentro del intervalo 2–7.5 min
que los timestamps del fallo original solo permitían acotar. **Deja de estar NO VERIFICADO.**

### El arreglo: dos piezas, y hacen falta las dos

En `rvr_driver_node.py`, bloque nuevo «SALUD DEL ENLACE»:

- **`_keepalive`** — timer cada **30 s** que llama a `get_battery_percentage()`. Se eligió una
  **lectura** y no `wake()` a secas porque no cambia ningún estado del robot: no puede
  interferir con una maniobra en curso ni con la parada de emergencia. Y de paso publica
  **`/battery_state`** (`sensor_msgs/BatteryState`, RELIABLE + TRANSIENT_LOCAL), que no existía
  ni en el driver de ROS 1, con avisos al cruzar el 25 % y el 10 %.
- **`_vigilar_silencio`** — timer a 1 Hz que mira **cuánto hace que llegó la última muestra**,
  no si el nodo existe ni si el topic está registrado: las dos cosas eran ciertas mientras el
  robot estaba mudo. A los 3 s avisa e intenta reanudar (`wake` + `stop` + `start`).

El keepalive cubre la causa conocida; el vigilante cubre el resto (un cable flojo, un
`sensor_control` caído, un firmware atascado) y **convierte un fallo silencioso en uno
ruidoso**.

30 s frente a un timeout de 300 s son **10× de margen**. Se podría subir a 120 s sin riesgo,
pero un comando cada 30 s son ~2 bytes/s sobre un enlace que ya lleva 16.7 Hz.

Parámetros nuevos: `keepalive_period` y `silence_timeout`, expuestos también como argumentos
de `robot.launch.py`. A 0 se desactivan — que es como se reproduce el fallo para medirlo.

### ✅ Verificado: las dos pruebas, una al lado de la otra

Mismo robot, misma duración, mismo binario. Solo cambia `keepalive_period`:

| | A (`keepalive=0`) | B (`keepalive=30 s`) |
|---|---|---|
| duración | 12.0 min | 12.0 min |
| muestras de `/odom` | 11795 | 11909 |
| ritmo medio | 16.38 Hz | **16.54 Hz** |
| **huecos en `/odom`** | **2** (3.9 y 9.0 min) | **0** |
| avisos de silencio | 2 | 0 |
| reanudaciones | 2, **0 fallos** | 0 |
| lecturas de batería | 0 | **24**, cada 30.0 s exactos |

Se durmió **dos veces sin keepalive y ninguna con él**. En la prueba B el detector no tuvo
nada que detectar, que es el objetivo. El ritmo medio sube de 16.38 a 16.54 Hz: la diferencia
es exactamente el tiempo que estuvo mudo en la A.

### Herramienta nueva

`00_auditoria/evidencia/mediciones_banco/medir_keepalive_ros2.py` — vigila el **ritmo** de
`/odom`, no la existencia del topic. Se suscribe con **BEST_EFFORT** a propósito: con el
perfil por defecto de `rclpy` (RELIABLE) DDS no emparejaría y la herramienta no recibiría
nada, concluyendo que el robot está mudo cuando no lo está. Sería un falso positivo perfecto.

### Detalle de implementación que conviene no deshacer

El `finally` que libera `_recuperando` pase lo que pase. Sin él, una excepción durante la
recuperación dejaría la vigilancia muerta para siempre: **el fallo silencioso otra vez, esta
vez dentro del código escrito para evitarlo.**

Y `cerrar()` apaga la vigilancia **antes** de parar nada, para que una parada normal no
dispare un WARN alarmante en cada apagado.

---

## 2026-07-30 (parte 9) — Fase 4: SLAM arranca y mapea, pero aparece un fallo grave del driver

🟡 **Fase 4 PARCIAL.** `slam_toolbox` arranca, se activa, completa el árbol TF y publica
`/map`. **Lo que falta es la prueba que importa: que el mapa crezca al moverse.** Y en el
camino salió un fallo del driver que afecta a todo el laboratorio.

Manual: **capítulo 9 nuevo**. Evidencia cruda: `00_auditoria/evidencia_24_04/11_slam_fase4.txt`
y `mapas/`. Rama `ros2` de `Atriz_rvr`.

### 🔴🔴 El RVR se duerme solo y el nodo sigue pareciendo sano

El hallazgo grave, y no es de SLAM. A mitad de sesión, sin tocar nada, `/odom`, `/imu` y
`/color` dejaron de publicar **a la vez**:

```
ros2 topic hz /tf     -> average rate: 50.193      # 50 Hz = SOLO slam_toolbox
ros2 topic hz /odom   -> (nada)
ros2 topic info /odom -> Publisher count: 1  ·  Node name: rvr_driver
ps -p 56100           -> Sl  12.3 %  86.4 MB  ·  17 hilos     # el proceso VIVE
```

Ni un error en el log. Y la pista fácil engañaba: `/tf` a 50 Hz decía «TF va bien», pero 50 Hz
es exactamente el `transform_publish_period` de `slam_toolbox` **a solas** — con el driver
serían ~67 Hz.

**Causa, confirmada en el código:** `rvr_driver_node.py:367` llama a `wake()` **una sola vez al
arrancar**, y no vuelve a hablar con el RVR salvo cuando llega un `cmd_vel`. El SDK vendorizado
**no tiene** `set_inactivity_timeout`. Reiniciar el driver lo revive: `/odom` vuelve a
16.669 Hz.

⚠️ **NO VERIFICADO el tiempo exacto**: acotado entre ~2 y ~7.5 min por los timestamps
(arranque 00:03:43, último dato 00:05:35, muerto a las 00:11). Encaja con los 5 min
documentados del RVR, pero **no se ha medido** y no se escribe como hecho.

**Por qué es serio para el laboratorio:** un robot que espere 5 minutos a que el estudiante
empiece su práctica **estará mudo al empezar**, y la web no verá ningún error — el nodo está
vivo y los topics existen. Un `systemd` con `Restart=always` **no** lo arregla: el proceso no
muere.

**Arreglo pendiente**, en el driver: keepalive cada 60 s con `get_battery_percentage()` (es una
lectura, y de paso da la batería, que hoy no se publica) + un detector de silencio que avise en
vez de publicar nada con cara de sano.

### 🔴 `base_link` tenía DOS padres — bloqueante de la Fase 4, error de diseño propio

`slam_toolbox` repetía `Failed to compute odom pose`:

```
/tf         odom            -> base_link       (driver)
/tf_static  base_footprint  -> base_link       (URDF)
-> "Tf has two or more unconnected trees."
```

En TF un frame solo puede tener **un** padre. Arreglado: el driver publica
`odom → base_footprint`, que es además lo correcto por REP-105 y lo que pide el `base_frame` de
`slam_toolbox`. La IMU pasa a su propio `imu_frame` (`imu_link`).

**Y la lección de método, que vale más que el arreglo:** la verificación de la Fase 3 era
`tf2_echo odom laser` y **pasaba**, resolviendo por el camino equivocado
(`odom → base_link → laser`) mientras `base_footprint` colgaba de otro árbol. **Hay que
comprobar el transform que pide el consumidor, con sus frames exactos.** Un `tf2_echo` que
resuelve prueba que hay *un* camino, no que el árbol esté bien.

Tras el arreglo: un solo árbol, y `Failed to compute odom pose` **0 veces**.

### 🔴 `slam_toolbox` es un nodo de ciclo de vida en Jazzy

Arrancaba en `unconfigured`: proceso vivo, en `ros2 node list`, **sin hacer nada** —
`Subscription count: 0` en `/scan`, sin publicar `/map`, sin un solo error.

`slam.launch.py` reescrito con `LifecycleNode` + eventos `configure`→`activate` encadenados con
`OnStateTransition` (no con un `sleep`), siguiendo el patrón del `online_async_launch.py`
oficial. Argumento `autostart`, por defecto `true`. Resultado: `active [3]` automáticamente.

### ✅ El riesgo del QoS de `/scan` era infundado

`slam_toolbox` se suscribe con **BEST_EFFORT**, igual que publica el driver del LIDAR:
emparejan. Queda documentado porque comprobarlo cuesta un comando y perseguir un mapa vacío
cuesta una tarde. Al revés sí muerde: **`/map` es RELIABLE + TRANSIENT_LOCAL**.

### `save_map` no funciona sin Nav2; `serialize_map` sí

`save_map` devuelve `result=255`, y el error real está en el log de slam_toolbox, no en la
respuesta: `Package 'nav2_map_server' not found`. Este sistema tiene `ros-jazzy-ros-base` y
Nav2 llega en la Fase 5.

`serialize_map` (nativo, sin Nav2) → `result=0`, `.data` 11 KB + `.posegraph` **3.4 MB** con el
robot casi quieto. ⚠️ Vigilar ese tamaño antes de guardar mapas en los 16 robots.

### Un robot quieto da un mapa 92.9 % desconocido, y no es un fallo

`min_pass_through: 2` exige **dos rayos** por celda y los rayos de un LIDAR quieto divergen:
solo las celdas cercanas reciben dos (1.29 m² libres). Y `minimum_travel_distance: 0.3` deja el
grafo en **un solo nodo**. No hay que ajustar el solver, hay que mover el robot.

**Herramienta nueva:** `00_auditoria/evidencia/mediciones_banco/medir_slam_ros2.py` — mueve el
robot (giro 360° + avance/retroceso) y mide **cuántas celdas conocidas gana el mapa**. Mide el
**recorrido real en `odom`** para separar los dos fallos que se confunden: «el robot no se
movió» y «SLAM no procesó». Mide posición, nunca velocidad (el stream `Velocity` del RVR es
basura).

### ⏳ La prueba de mapeo con movimiento NO es válida: hay que repetirla

Se reinició **solo el driver** (había muerto), dejando el `slam_toolbox` viejo en marcha. Ese
`slam_toolbox` dejó de procesar: mapa **idéntico celda a celda** (515 conocidas antes y
después) tras un giro de 360° y 80 cm de recorrido.

→ **Reiniciar el driver por debajo de un `slam_toolbox` ya arrancado invalida la prueba**: se
queda con un hueco en su buffer TF y con el `odom` anterior. Arrancar los dos juntos,
`robot.launch.py` primero.

### Coste en el Pi 4 con todo a la vez

| Proceso | CPU | RSS |
|---|---|---|
| `rvr_driver_node` | 15.9 % | 86.3 MB |
| `async_slam_toolbox_node` | **4.5 %** | 49.3 MB |
| `ydlidar_ros2_driver_node` | 2.6 % | 31.3 MB |
| `robot_state_publisher` | 0.5 % | 32.6 MB |

`loadavg` 0.62 sobre 4 núcleos · 62.3 °C · `throttled=0x0`.

**SLAM sale barato (4.5 %).** El presupuesto de CPU lo consume el driver del RVR, así que
subir `throttle_scans` para «aliviar el Pi» sería optimizar lo que no cuesta.

### Pendiente al cerrar la sesión

| Qué | Por qué importa |
|---|---|
| **Keepalive del driver** | sin él, un robot idle 5 min llega mudo a la práctica |
| Repetir `medir_slam_ros2.py` con los dos launch desde cero | es la única prueba que cierra la Fase 4 |
| 🔴 Verificar `inverted` del LIDAR | si está al revés **el mapa sale espejado**, sin dar error |
| 🔴 Inclinación de ~7° del robot | `slam_toolbox` la absorbe en `map → odom`; para Nav2 hay que resolverla |
| Velocidad de `/odom` | sigue siendo basura; no bloquea SLAM, sí Nav2 |
| Los 16 servicios y 4 topics sin portar | diferido por el usuario a «cuando acabemos todo» |

---

## 2026-07-30 (parte 7) — Fase 3 COMPLETA: `/scan` funciona y el robot arranca con un comando

Paquete **nuevo** `atriz_rvr_bringup`, rama `ros2` commit `b117791`.

```bash
ros2 launch atriz_rvr_bringup robot.launch.py
```

Tres nodos que se reparten el árbol TF, verificado contra el hardware:

```
tf2_echo odom laser -> Translation: [-0.018, -0.002, 0.141]

/tf         odom -> base_link                              (driver, 16.989 Hz)
/tf_static  base_footprint -> base_link
            base_link -> {laser, imu_link, wheel_left, wheel_right}
/scan       10.1 Hz · frame_id: laser · 255 puntos, 226 válidos (89 %)
            0.326 – 3.134 m · arco −180° a 180° · resolución 1.42°
```

### No hay paquete apt del driver: se compila desde fuentes

Comprobado antes de compilar nada: `ros-jazzy-ydlidar-ros2-driver`, `ros-jazzy-ydlidar` y
`ros-jazzy-ydlidar-sdk` **no existen**, y `apt-cache search ydlidar` da 0 resultados.

**`YDLidar-SDK`** con cmake → 132 ficheros bajo `/usr/local`. Comprobado **en seco** con
`make install DESTDIR=/tmp/prueba` antes de ejecutarlo: **no pisa nada** del sistema de
paquetes. 📝 Instala 17 binarios de prueba en `/usr/local/bin` que sobran en la imagen dorada.

**`ydlidar_ros2_driver` rama `humble` compila en Jazzy sin cambios** (47.9 s). Driver 1.0.1,
SDK 1.2.20. Y **trae `params/X2.yaml` de fábrica**. Va en `~/atriz_ws/src/` **sin `.git`**: es
código de terceros y no se mezcla con `Atriz_rvr`.

### 🔴 El hallazgo más importante: el QoS de `/scan`

**El driver publica `/scan` como BEST_EFFORT, y `rclpy` pide RELIABLE por defecto.** Si no
coinciden, **DDS no empareja publicador y suscriptor y no llega nada** — sin error en el
suscriptor.

```
New subscription discovered on topic '/scan', requesting incompatible QoS.
No messages will be sent to it. Last incompatible policy: RELIABILITY_QOS_POLICY
```

**El primer test de esta sesión cayó justo ahí** y concluyó que `/scan` no llegaba. Con
BEST_EFFORT llegan 81 barridos en 8 s.

🔴 **Riesgo directo para la Fase 4:** si `slam_toolbox` se suscribe con RELIABLE, **no recibirá
un solo barrido y no dará ningún error** — solo un mapa vacío. **Comprobarlo antes de mapear.**

### ⚠️ `frequency` no funciona en el X2 — y eso cierra una vía de mejora

Se pidió `frequency: 10.0` y `/scan` salió a **10.1–11.75 Hz**. Sin driver, con `x2_parse.py`,
se midieron **11.48 Hz**. **El X2 de canal único ignora el parámetro:** el motor va libre.

**Consecuencia:** el apartado 8.3 del manual proponía bajar a 7 Hz para ganar resolución angular
(0.84° en vez de 1.37°). **Esa vía no existe por software.** La resolución real medida con el
driver es **1.42°**, coherente con los 1.39° de `x2_parse.py`. Corregido en el manual.

### Lo que queda sin verificar, y por qué importa

**`inverted`.** El `X2.yaml` oficial trae `false`; el launch de ROS 1 de Atriz tenía `true`.
Pero **ese launch nunca se ejecutó**, porque el driver del LIDAR no estaba instalado (hallazgo
nº3 de la auditoría). Así que `true` es una suposición heredada, no un valor validado.

**Si está mal, el mapa sale espejado** — y es de los fallos más desconcertantes de SLAM: parece
que funciona, y las paredes están en el lado contrario. Documentado cómo comprobarlo en
`config/ydlidar_x2.yaml`: un objeto plano a 1 m justo delante, y el mínimo de `ranges` debe caer
en el índice del ángulo 0.

**La regla udev entre robots.** Va por `ID_PATH` (el puerto USB físico) porque el CP2102
reporta serie `0001`, genérico. Comprobada en seco y en caliente en `rvr-01`, pero **si en otro
robot el lidar va en otro puerto físico, el `ID_PATH` será distinto y la regla no casará.**

### Avisos benignos, documentados para que nadie los persiga

`[error] Fail to get baseplate device information!` aparece **siempre**: el X2 de canal único no
responde a esa consulta, y el scan funciona igual. Y `Single Fixed Size: 270 / Sample Rate:
3.00K` es informativo y correcto.

### Documentado

- **Manual, cap. 8.5** — escrito completo: los dos pasos de compilación, la comprobación en
  seco del `make install`, la regla udev, **el QoS**, y la verificación con la salida real.
- **Manual, cap. 8.3** — corregido: la mejora de resolución bajando el giro **no es
  alcanzable**.
- **`CLAUDE.md`** — dos trampas nuevas: el QoS de `/scan` y el `frequency` inútil.
- **`verificar_robot.sh`** — comprueba el SDK, el driver compilado y `/dev/ydlidar`.

### Pendiente

1. **Fase 4: `slam_toolbox`.** Y lo PRIMERO es comprobar con qué QoS se suscribe a `/scan`.
2. 👤 **Comprobar `inverted`** con un objeto a 1 m delante del robot, antes de mapear.
3. **La velocidad de `/odom` sigue siendo basura** (parte 5). Afecta a `robot_localization` y a
   los controladores de Nav2, no a `slam_toolbox`, que usa el TF.
4. Los 16 servicios del driver sin portar.
5. 📝 El pitch de −7° del robot, sin determinar si es del suelo o del montaje.

---

## 2026-07-30 (parte 6) — Fase 3: el URDF, y el árbol TF deja de estar partido

Paquete **nuevo** `atriz_rvr_description`, rama `ros2` commit `89be510`. Antes de esto el
proyecto **no tenía ningún `.urdf` ni `.xacro`**.

### El bloqueante raíz, y por qué era invisible

```
   odom      ──► rvr_base_link      ← lo publicaba el driver
   base_link ──► laser              ← un static_transform_publisher del launch
```

**Nada unía `rvr_base_link` con `base_link`.** Dos árboles inconexos: no había forma de saber
dónde está el LIDAR respecto a la odometría, y sin eso SLAM y Nav2 son imposibles.

Lo peor es cómo falla: `tf2_echo odom laser` responde *«Could not find a connection»* y nada
más. **Ningún nodo se cae, ningún topic deja de publicar.** Otro fallo silencioso.

Ahora la cadena es una sola, canónica según REP-105:

```
   map ──► odom ──► base_footprint ──► base_link ──► { laser, imu_link, wheels }
```

Con el reparto explícito de quién publica qué — que es lo que más se confunde:

| Transform | Lo publica |
|---|---|
| `map → odom` | `slam_toolbox` (Fase 4, aún no existe) |
| **`odom → base_link`** | **el driver**, porque es el único que sabe dónde está el robot |
| `base_footprint → base_link`, `→ laser`, `→ imu_link`, ruedas | `robot_state_publisher`, desde el URDF |

### 🔴 El valor del LIDAR estaba 7.4 cm corto

```
  base_height    0.114     alto del RVR         📝 ficha, SIN MEDIR en esta unidad
+ laser_gap      0.040     hueco tapa→LIDAR     ✅ MEDIDO por el usuario
+ x2_height/2    0.0205    al centro del disco  📝 ficha del X2
─────────────────────────
  laser_z        0.1745  = 17.45 cm sobre el suelo
```

El proyecto arrastraba **`0.10`**. Venía del `static_transform_publisher` de
`lidar_only.launch`, y la propia `GUIA_COMPLETA_LIDAR.md` lo admitía: «se **asume** que el LIDAR
está en el centro del RVR y 0,1 m por encima. **Ajusta estos valores a tu montaje real**».
Nadie lo ajustó en toda la vida del proyecto.

**Por qué 7 cm no es cosmético:** un error en `laser_z` inclina el mapa entero; uno en `laser_x`
desplaza cada barrido respecto a la odometría, y SLAM lo lee como movimiento que no ocurrió. El
mapa sale torcido **sin un solo mensaje de error**.

El término dudoso es `base_height`, el único sin medir. Queda documentado que si el mapa sale
inclinado, ese es el primer sospechoso, y se resuelve con **una** medida del suelo al centro del
disco.

### Las ruedas son `fixed`, y es deliberado

Un joint `continuous` obligaría a publicar `/joint_states` con el ángulo de cada rueda, y el RVR
**no expone la posición angular** — solo conteos de encoder acumulados. Declararlas móviles
dejaría a `robot_state_publisher` esperando datos que nunca llegan, y el árbol se rompería con
un aviso poco claro. Como el RVR entrega la odometría ya integrada, son decorativas. Por eso el
launch tampoco arranca `joint_state_publisher`.

### Dos hallazgos menores pero reales

**`xacro` NO viene en `ros-jazzy-ros-base`.** Hay que instalarlo aparte
(`sudo apt install ros-jazzy-xacro`). `robot_state_publisher` y `tf2_tools` **sí** vienen.

**Un fallo latente evitado:** `install(DIRECTORY … rviz)` con el directorio vacío habría roto el
build **en un clon recién hecho**, porque git no versiona directorios vacíos. Se añadirá cuando
haya una configuración de RViz2 de verdad (Fase 4).

### Documentado

- **Manual, capítulo 7** — escrito. No existía. Con la tabla de quién publica cada transform,
  la procedencia de cada medida, y los comandos de verificación.
- **`verificar_robot.sh`** — comprobación nueva del árbol TF (`tf2_echo odom laser`) y de que
  `ros-jazzy-xacro` esté instalado.

### ✅ CERRADA — `odom → laser` resuelve

```
$ ros2 run tf2_ros tf2_echo odom laser
- Translation: [-0.018, -0.002, 0.141]
- Rotation: in RPY (degree) [1.603, -7.013, -5.000]

base_link   parent: odom        rate 16.699 Hz    <- el driver
laser       parent: base_link   rate 10000 Hz    <- robot_state_publisher
imu_link, wheel_*                rate 10000 Hz
```

La **z = 0.141** coincide con los 0.1425 del URDF, los 10000 Hz son la marca de `/tf_static`, y
`base_link` va al ritmo de la telemetría. **El bloqueante raíz de SLAM está resuelto.**

📝 **Dato colateral sin medir:** el RPY sale **[1.6°, −7.0°, −5.0°]**. Un pitch de −7° significa
chasis inclinado o suelo con pendiente. **El LIDAR lo está viendo.** No se ha determinado la
causa, y conviene recordarlo cuando salga el primer mapa.

### 🐛 Dos fallos propios más

**El launch falló con un error de los útiles**, y el fichero **ya llevaba un comentario
explicando la solución** que no se había implementado:

```
Unable to parse the value of parameter robot_description as yaml. If the parameter
is meant to be a string, try wrapping it in ParameterValue(value, value_type=str)
```

`robot_description` es XML y `launch` lo interpreta como YAML si no se le dice el tipo.

**Y un respaldo mal colocado hizo que `apt` avisara en cada ejecución.** Al añadir
`noble-updates` se dejó `ubuntu.sources.bak-…` **dentro** de `sources.list.d/`, y desde entonces
todo `apt install` terminaba con `N: Ignoring file … invalid filename extension`. Inofensivo,
pero en 16 robots es ruido permanente. Corregido en `provision.sh` (los respaldos van a
`/root/respaldos-apt/`), en el manual, y **`verificar_robot.sh` ahora lo detecta**.

### Pendiente
2. **La velocidad de `/odom` sigue siendo basura** (parte 5). Bloquea SLAM de calidad, no la
   estructura del árbol.
3. Los 16 servicios del driver sin portar.
4. Fase 4: `slam_toolbox`.

---

## 2026-07-30 (parte 5) — El driver corre sobre ROS 2, y el watchdog se prueba por primera vez

Rama **`ros2`** de `Atriz_rvr`, commit `80e1cbf`. **Verificado contra el robot real.**

```
/odom              16.671 Hz · sigma 0.47 ms      (ROS 1 daba 16.59 Hz)
angular_velocity   rad/s                          (antes deg/s, violaba REP-103)
árbol TF           odom -> base_link              (antes rvr_base_link, partido)
cmd_vel            34.0 cm a 0.15 m/s en 2 s      (esperado ~30 cm)
watchdog           quieto en 527 ms, ~7.9 cm      PRIMERA VEZ QUE SE PRUEBA
```

### Fase 2.1 — limpieza: 79 ficheros y 700 KB menos

Cada borrado verificado antes de hacerlo, no por lo que decía el plan:

| Borrado | Comprobación |
|---|---|
| `atriz_rvr_driver/src/` (38 ficheros) | El CMakeLists **sí** lo construía, pero **ningún launch lo invocaba** |
| `atriz_rvr_serial/` | Solo lo dependía el driver, y solo para ese C++ |
| `rvr-ros.py` (722 líneas) | Sin bit de ejecución, y su launch invocaba `rvr-ros-sim.py`, que **no existe** |
| `sphero_rvr_hw/` | Sin `package.xml`, huérfana |
| 3 `.launch` | Cadena entera colgando del C++ borrado |

### Fase 2.2 — `atriz_rvr_driver` a `ament_python`

Se van `roscpp`, `message_generation/runtime`, `transmission_interface`, `cv_bridge` (sin
cámara) y `joint_limit_interface` — que además estaba **mal escrito** (el real es
`joint_limits_interface`) y por eso `rosdep` fallaba.

**El SDK no se mueve** de `scripts/`: sus 196 ficheros usan imports absolutos y es la única
pieza validada en Python 3.12. Con `package_dir={'': 'scripts'}` sigue importándose igual.

### Fase 2.3/2.4 — el nodo: 1704 líneas → ~490 con el núcleo

Lo que se arregló, y lo que **ya estaba bien**. Ver la corrección del plan más abajo.

- **`imu.angular_velocity` a rad/s, convertido una sola vez.** El original lo asignaba en
  deg/s, publicaba, y solo después convertía — incrementando el contador de componentes **dos
  veces por muestra**, así que `/odom` podía salir con la velocidad angular en grados.
- **`run_coroutine_threadsafe`** en vez de las 48 `asyncio.run()`. Sin afirmar que fuera el
  cuello de botella: **no se ha medido**.
- **`odom → base_link`**, el bloqueante raíz de SLAM.
- Todo parametrizado, watchdog a 20 Hz (antes ~6 Hz), y la parada de emergencia con QoS
  *reliable + transient local* escuchando **los dos** nombres de topic.

### 🔴 Dos puntos del plan eran FALSOS — la misma causa de siempre

Verificado antes de escribir código: el plan decía que **no había watchdog de `cmd_vel`** y que
el **event loop avanzaba en ráfagas** dentro del bucle de ROS. **Las dos cosas ya estaban
resueltas** en `migracion-ros2`.

Se añadieron en `4ae8467` y `d8f182d`/`659364c`, que están **entre los 5 últimos commits de
`origin/main`** — exactamente el rango que le faltaba al clon desactualizado sobre el que se
hizo la auditoría. **Es la misma causa que los tres hallazgos ya retirados**, y van cinco.

Corregido en el plan, apartados 2.3 y 2.4, con la explicación completa.

### 🔴 HALLAZGO NUEVO: el stream `Velocity` del RVR no sirve

Medido aislando el SDK, sin ROS de por medio:

| Método | Recorrido real (locator) | `Velocity` reportada | Deriva tras `drive_stop` |
|---|---|---|---|
| `drive_rc_si_units(0.15)` | **29.4 cm** = 0.147 m/s | **0.001 m/s** | **1.1 cm** |
| `drive_with_heading(64)` | 45.6 cm | 0.028 m/s | **11.3 cm** |

> ⚠️ **RETRACTADO el 2026-07-31.** Lo que sigue se conserva como registro de lo que se midió
> aquel día, pero **la conclusión era falsa**: el stream `Velocity` es **exacto** (0 % de error
> en módulo, 0.1° en dirección). Viene en el marco del **mundo**, y aquí se leyó solo su
> componente X con el robot encarado a ~90° de ese eje. El fallo está en el **driver**, que la
> copia a un campo que ROS define en el marco del **robot**.
> Detalle en `00_auditoria/evidencia_24_04/15_velocidad_odom.txt`.

**Consecuencia grave:** el driver publica `odom.twist.twist.linear` desde ese sensor, así que
**la velocidad de `/odom` es basura**. Afecta a SLAM y a `robot_localization`. La **posición**
sí es buena (29.4 cm contra 30.0 esperados).

Dato colateral: `drive_rc_si_units` frena diez veces mejor que `drive_with_heading`.

**Pendiente decidir** de dónde sacar la velocidad: derivarla del locator, integrarla de los
encoders, o dejarla a cero y que la estime `robot_localization`. **Ninguna probada. No tocar
`/odom` hasta medirlo.**

### El watchdog, probado por primera vez en la historia del proyecto

Existía desde `d8f182d` y nunca se había verificado. Herramienta nueva:
`mediciones_banco/medir_watchdog_ros2.py`.

```
tiempo hasta quedar quieto      527 ms
  timeout del driver           ~300 ms   <- exactamente cmd_vel_timeout
  frenada + latencia + detección ~227 ms <- físico, no software
distancia tras el corte        ~7.9 cm
```

### Cuatro errores propios de esta sesión

1. **`_enviar()` tiraba los errores a la basura.** Encolaba la corrutina y se olvidaba del
   `Future`, así que una excepción de `drive_rc_si_units` moría en silencio. Corregido con
   `add_done_callback` y una etiqueta por comando.
2. **Falta `setup.cfg` → `ros2 run` dice «No executable found»** aunque `colcon build` diga
   *Finished*. El `console_script` acaba en `bin/`, que `ros2` no mira. Documentado en el
   propio fichero.
3. **Mi herramienta midió por velocidad y concluyó «el robot NUNCA se movió»** mientras el
   robot cruzaba la habitación. **Lo corrigió el usuario, mirándolo.** La herramienta ahora
   mide desplazamiento.
4. **Mi umbral de éxito del watchdog (350 ms) estaba mal calculado**: no contaba la frenada
   física ni que `/odom` llega cada 60 ms. Ahora es `timeout + 300 ms` y lo que se juzga es la
   **distancia recorrida**, que es lo que importa con obstáculos cerca.

Y un artefacto del test: publicaba un `Twist()` vacío «de cortesía» al terminar, que reactivaba
el watchdog y lo hacía disparar dos veces. Quitado.

### Pendiente

1. **Los 16 servicios que faltan** (LEDs, IR, encoders, system info, streaming, motores crudos,
   `move_to_pose`) y 4 topics. Listados al final de `rvr_driver_node.py`. **No se portan a
   ciegas.**
2. **Decidir la velocidad de `/odom`** — ver el hallazgo de arriba. Bloquea SLAM de calidad.
3. **Fase 3: el URDF**, que el plan llama el bloqueante raíz. El driver ya publica
   `odom → base_link`, así que la mitad del problema está resuelta.
4. Decidir `ir_messages` vs `infrared_messages` (dos topics para lo mismo) y el namespace.
5. ⚠️ **Antes de la imagen dorada:** quitar `ROS_DOMAIN_ID` de `~/.bashrc`.

---

## 2026-07-30 (parte 4) — Fase 2 arrancada: `atriz_rvr_msgs` corre sobre ROS 2

**El primer código del proyecto que compila sobre ROS 2 Jazzy.** Rama nueva **`ros2`** en
`Atriz_rvr`, desde `migracion-ros2` (`24c7749`), commit `1b1239a`.

```
colcon build          Finished <<< atriz_rvr_msgs [3min 46s]
ros2 interface list   6 mensajes + 20 servicios
ros2 interface show   std_msgs/Header resuelto correctamente
import desde Python   los 26 tipos importan e instancian
```

### El port fue menos trabajo de lo que parecía

| | ROS 1 (catkin) | ROS 2 (ament) |
|---|---|---|
| Build | `catkin_package()` + `add_message_files()` + `add_service_files()` + `generate_messages()` | **un solo** `rosidl_generate_interfaces()`, con msg y srv en la misma lista |
| Rutas | `Color.msg` | `msg/Color.msg` (con prefijo) |
| `package.xml` | `format=2`, `message_generation`/`message_runtime` | `format=3`, `rosidl_default_generators`/`rosidl_default_runtime` |
| Grupo | — | **`<member_of_group>rosidl_interface_packages</member_of_group>`**, obligatorio y fácil de olvidar |

**Los 6 mensajes no necesitaron ni un cambio.** Ya estaban en `snake_case` y sin tipos `time`
ni `duration`, que son las otras dos incompatibilidades típicas de ROS 1 → ROS 2.

**El único cambio de contenido en 26 ficheros:** tres `.srv` declaraban `Header header`, y en
ROS 2 `Header` a secas **no resuelve** — tiene que ser `std_msgs/Header`. Afectaba a
`MoveToPose`, `MoveToPosAndYaw` y `SetPosAndYaw`.

### `COLCON_IGNORE` en los otros dos paquetes

`atriz_rvr_driver` y `atriz_rvr_serial` siguen siendo catkin y romperían el build del
workspace entero. Llevan `COLCON_IGNORE` hasta que les toque el port. Es el mecanismo estándar
de colcon y deja `colcon list` mostrando solo lo que de verdad se puede construir.

### 🐛 La identidad de git es por repositorio, no global

El primer `git commit` en `Atriz_rvr` falló con *«Author identity unknown»*: el 2026-07-30 se
había configurado `user.name`/`user.email` **solo en `atriz_migracion`**, con `git config` sin
`--global`. Peor aún: el `git push` de la rama **sí funcionó** —subiéndola sin el commit—, así
que el fallo era fácil de pasar por alto.

Corregido con `git config --global`, para que el tercer repositorio (`Atriz_web_server`) no
repita el tropiezo. **Va a `provision.sh`** como parte del aprovisionamiento.

### El mapa del driver, medido antes de tocarlo

Para el port del nodo, que es lo siguiente:

| | |
|---|---|
| Publishers | 7: `odom`, `imu`, `color`, `encoders`, `ambient_light`, `infrared_messages`, `ir_messages` |
| Subscribers | 3: `cmd_vel`, `cmd_degrees`, `is_emergency_stop` |
| Servicios | 20 |
| Handlers async del SDK | 12 |
| Estructura | **funciones a nivel de módulo compartiendo estado global**, sin clase |

Esa última fila es el trabajo real: `rclpy` quiere un `Node`, así que el port no es sustituir
`rospy` por `rclpy` línea a línea, es **reestructurar**.

Dos cosas anotadas al hacer el mapa, para revisar durante el port:
- Hay **dos publishers para lo mismo**: `infrared_messages` e `ir_messages`. Decidir cuál se
  queda antes de portar los dos.
- `Publisher('odom')` y el resto van **sin namespace**. Con un `ROS_DOMAIN_ID` por robot el
  namespace `/rvr_NN` no es imprescindible para el aislamiento, pero `ARQUITECTURA.md` lo
  contempla y la web lo espera. Decidirlo en el port, no después.

### Pendiente

1. **Portar `Atriz_rvr_node.py` a `rclpy`** (Fase 2.3 y 2.4), con los dos puntos de seguridad:
   el **watchdog de `cmd_vel`** y `imu.angular_velocity` en **rad/s**.
2. **Limpieza previa** (Fase 2.1): borrar los `.cpp`, `src/rvr++/`, el paquete
   `atriz_rvr_serial` y `scripts/rvr-ros.py` en lugar de portarlos.
3. Decidir los dos puntos del mapa: `ir_messages` vs `infrared_messages`, y el namespace.

---

## 2026-07-30 (parte 3) — ROS 2 Jazzy instalado y verificado (Etapa E1)

```
ros2 doctor            All 5 checks passed
paquetes ros-jazzy     201 en estado 'ii', 0 a medio instalar
pub/sub sobre DDS      9.997 Hz · min 0.099 s · max 0.101 s · sigma 0.35 ms
entorno                ROS_DISTRO=jazzy · ROS_DOMAIN_ID=1 · rmw_fastrtps_cpp
disco                  4.0 GB usados de 29 GB
```

**σ de 0.35 ms sobre 10 Hz.** Dato de referencia útil: cuando la odometría real vaya a
16.5 Hz, ya sabemos que el jitter **no** lo introduce el middleware.

### 🔴 La imagen de 24.04 para Raspberry Pi viene sin `noble-updates`

El `apt install` falló con `held broken packages` en `zlib1g-dev`, `libzstd-dev`,
`liblz4-dev` y `dpkg-dev`. La pista estaba en el `apt update`: **dos** repositorios de Ubuntu
donde deberían haber tres.

`/etc/apt/sources.list.d/ubuntu.sources` solo lista `noble` y `noble-security`. El fichero
está fechado en la creación de la imagen y nadie lo había tocado: **es como se distribuye**.

El mecanismo no es obvio: las bibliotecas de runtime *sí* se actualizan desde
`noble-security` (a versiones con sufijo `.1`), pero sus `-dev`, que exigen una versión
**exacta** de la runtime, viven en `noble-updates`. Sin ese repositorio la dependencia es
insatisfacible. Y `ros-dev-tools` arrastra esos `-dev`, así que **sin ellos no hay
`colcon build`**: no es cosmético.

Tras el arreglo aparecieron además **46 paquetes actualizables** que llevaban sin llegar —
eran los bug fixes que no son de seguridad.

Atacado en los tres sitios: **manual 5.2.0** (nuevo, antes del 5.2, con el mensaje de error
literal para que sea encontrable), **`provision.sh`** (lo arregla antes del primer `apt
update`, así que queda dentro de la imagen dorada) y **`verificar_robot.sh`** (comprobación
nueva, probada: lo detecta y da el comando de arreglo).

### El método de las claves GPG había cambiado — el ⚠️ COMPROBAR estaba justificado

Se usa el paquete oficial **`ros2-apt-source` 1.2.0**, no el `curl` del keyring a mano,
porque **mantiene la clave actualizada por sí solo**. Con la clave puesta a mano, el día que
caduque —y ya pasó una vez, rompiendo `apt` en todas las instalaciones de ROS del mundo— se
rompen los 16 robots a la vez y hay que entrar en cada uno.

Auditado antes de instalarlo como root: **sin scripts de mantenedor** (solo `control` y
`md5sums`), solo coloca el keyring, el `.sources` y un symlink. Clave de Open Robotics,
huella `C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654`, **caduca 2030-06-01** — después del fin de
soporte de Jazzy (mayo 2029), así que no caducará a mitad del proyecto.

### 🐛 «Existe `setup.bash`» NO significa «ROS 2 está instalado»

Estuve a punto de dar la instalación por terminada mirando el fichero. `dpkg` decía otra cosa:

```
ls /opt/ros/jazzy/setup.bash            -> existe
source setup.bash; echo $ROS_DISTRO     -> jazzy
dpkg-query -W ros-jazzy-ros-base        -> install ok UNPACKED
dpkg -l 'ros-jazzy-*' | grep -c '^ii'   -> 0          <- CERO configurados
```

En un Pi 4, 509 paquetes tardan 15-20 min y `apt` los procesa en dos fases. Entre
desempaquetar y configurar, el sistema **parece** listo.

Es la misma lección que ya estaba dos veces en este repositorio: un nodo que arranca no
prueba que el UART funcione (cap. 1.5), y un servicio en verde no prueba que haya hecho su
trabajo (cap. 4.3). **Comprueba el efecto, no el indicio.** Documentado como cap. 5.4.1.

`verificar_robot.sh`, bloque 8 reescrito a partir de eso: cuenta paquetes en estado `ii` y
consulta `dpkg-query` por paquete distinguiendo `ok installed` de `unpacked`. **Probado en
vivo durante la propia instalación:** detectó «solo 35 paquetes configurados: la instalación
está a medias».

### 🐛 El capítulo 5.5 pedía algo imposible

`ros2 run demo_nodes_cpp talker` → **`Package 'demo_nodes_cpp' not found`**. No viene en
`ros-base`, es un paquete aparte. Sustituido por `ros2 topic pub`/`echo`/`hz`, que vienen en
`ros2cli` y verifican lo mismo **sin añadir un paquete a 16 robots**.

### Tres defectos propios más, todos del mismo patrón

1. **`grep -c` imprime `0` Y sale con código 1**, así que un `|| echo 0` concatenaba un
   segundo cero y la variable quedaba `"0\n0"`, rompiendo la aritmética. Es **el mismo patrón
   que rompió `systemctl is-enabled`** esta misma mañana. Tercera aparición del día.
2. Mi `pgrep -f 'listener'` encontró **`sshd`**, cuya línea de comando contiene literalmente
   `[listener]`. Falso positivo inofensivo porque matamos por PID, pero es exactamente la
   trampa del `pkill -f` ya documentada.
3. `bash -lc` no ejecuta `~/.bashrc` (el de Ubuntu tiene un `return` si no es interactivo),
   así que mi primera comprobación del entorno dio vacío y **parecía** que la configuración
   había fallado. Era la prueba, no la configuración.

### Un dato mío corregido

`FLOTA.md` decía **«~1.5 GB por robot»** como si fuera medido. Era una estimación **inflada
unas cinco veces**: el `apt` real dice **157 MB** de descarga para ROS 2 (509 paquetes,
703 MB en disco), del orden de **300 MB por robot** en total. La conclusión (imagen dorada) no
cambia, pero el número sí. Y se añade el argumento que de verdad pesa más: **el tiempo**,
15-20 min de instalación por robot contra ~8 min de grabar una tarjeta, en paralelo.

### El driver sigue sin poder ejecutarse, y eso es lo esperado

`Atriz_rvr_node.py` es **ROS 1**: 1704 líneas, **99 referencias a `rospy`**, 48
`asyncio.run()`, 3 paquetes **catkin**. No es «sin probar», es **imposible** hasta el port.
`colcon build` fallará y debe fallar. Lo validado es el **SDK**, que es la pieza
insustituible; el driver es código propio y por tanto reescribible.

**`verificar_robot.sh` pasa de 39 a 48 aserciones. En `rvr-01`: 48 correctas, 0 fallos,
código de salida 0.**

### Pendiente

1. **Fase 2 del plan — portar el driver a `rclpy`.** El trabajo grande, y merece su propia
   sesión: incluye el **watchdog de `cmd_vel`** (hoy si cae la red el robot sigue con el
   último comando), `imu.angular_velocity` a **rad/s** (hoy viola REP-103), sacar el event
   loop de asyncio a su propio hilo, y borrar el lastre de C++ que nunca se ejecutó.
2. **Fase 3 — URDF.** El plan lo llama **el bloqueante raíz**: el árbol TF está partido, y sin
   un árbol conectado SLAM es imposible por mucho que el driver funcione.
3. ⚠️ **Antes de la imagen dorada: quitar `ROS_DOMAIN_ID` de `~/.bashrc`.** Está puesto a mano
   ahí porque `atriz-first-boot` no está instalado todavía. El `.bashrc` se lee **después** de
   `/etc/profile.d/`, así que si se clona tal cual, **los 16 robots quedarían en el dominio 1**
   sin que nada avise. `verificar_robot.sh` ya comprueba esa colisión.
4. 👤 Reserva DHCP de `rvr-01`, dónde está guardada la imagen `dd`, y si la contraseña de
   `sphero` se rotó. Siguen abiertos de la parte 2.

---

## 2026-07-30 (parte 2) — 🟢 GO, y la infraestructura para los 15 robots restantes

### 🟢 GO — el SDK de Sphero funciona en Python 3.12

**Es la decisión que bloqueaba todo el proyecto, y sale a favor.**

| Comprobación | Resultado |
|---|---|
| Los 103 ficheros del SDK | compilan sin errores de sintaxis en 3.12 |
| `SpheroRvrAsync` construido en | **0.0 s** (el atajo: 0 s = responde, ~10 s = dos timeouts) |
| Batería | 100 % |
| Firmware Nordic | **9.1.462** — el documentado |
| Streaming con `interval=60` | **16.67 Hz** |

**16.67 Hz en Python 3.12 sobre 24.04, frente a 16.59 Hz en Python 3.8 sobre 20.04.** Mismo
rendimiento. El análisis estático del 2026-07-29 predijo un parche de ~4 líneas; resultaron ser
**cero**.

Lo que este GO **no** significa: el driver sigue siendo ROS 1 (catkin) y no compilará con
`colcon` hasta el port de la Fase 2. Lo validado es la pieza insustituible, el SDK.

### El primer intento dio un NO-GO FALSO, y el script tenía la culpa

`ModuleNotFoundError: No module named 'aiohttp'`. **No era una incompatibilidad con Python
3.12: era un paquete que faltaba.** `sphero_sdk/__init__.py` importa todo de golpe, y esa
cadena llega a `common/firmware/cms_fw_check_base.py:2`, que hace `import aiohttp` a nivel de
módulo. En 20.04 estaba instalado por casualidad (aparece en el `pip list` del respaldo), así
que la dependencia nunca se había notado.

El script marcaba `aiohttp` como «opcional, no afecta al backend serie» en el paso 2/6 **y
moría por él en el 4/6** — sugiriendo replantear la arquitectura del proyecto por un paquete
que se instala en diez segundos. Corregido: las tres dependencias son obligatorias y cada una
dice cómo instalarse.

Que `aiohttp` solo se **use** para consultar el firmware contra un servicio web de Sphero es
cierto e irrelevante: el import es incondicional.

### Las tres dependencias, y dónde va cada una

| Módulo | Cómo | Dónde queda |
|---|---|---|
| `pyserial` 3.5 | `apt` (`python3-serial`, ya venía) | `/usr/lib/python3/dist-packages` |
| `aiohttp` 3.9.1 | `apt` (`python3-aiohttp`) | `/usr/lib/python3/dist-packages` |
| `pyserial-asyncio` 0.6 | `pip3 --break-system-packages` | `/usr/local/lib/python3.12/dist-packages` |

`pyserial-asyncio` **no existe como paquete apt** (`apt-cache policy` vacío): es la única que
obliga a `pip`, y 24.04 aplica PEP 668.

**Error propio corregido:** se instaló primero con `pip --user`, dejándolo en
`/home/sphero/.local`. Funciona para la prueba, pero un servicio systemd puede no verlo según
su `User=` y en la imagen dorada quedaría enterrado en el home de un usuario. Reinstalado a
nivel de sistema y **eliminada la copia de usuario**, que enmascaraba la del sistema.

---

### Infraestructura para no repetir esto 15 veces

Tres scripts nuevos, escritos **después** de instalar `rvr-01` a mano — no antes, para no
automatizar suposiciones.

**`verificar_robot.sh`** — 39 aserciones, código de salida ≠ 0 si algo falla. Es la pieza más
valiosa: hoy se verificó este robot con ~25 comandos sueltos y aparecieron **cinco fallos
silenciosos**; repetir eso a ojo en 15 robots garantiza que algo se cuele.

Su regla es **comprobar el efecto, no la intención**, y cada decisión viene de un fallo real:
no mira `config.txt` para saber si `disable-bt` está aplicado sino el device-tree; no se fía de
`systemctl is-enabled snapd`, que hoy mintió; lee el power-save con `grep -oi` porque `iw`
imprime `Power save:` con mayúsculas; sabe que `is-enabled cloud-init` dice `enabled` aunque
esté desactivado y lo dice en voz alta; y no usa `ps -e | wc -l` como métrica.
**Probado en `rvr-01`: 39 correctas, 0 fallos.** (Ampliado a **48** al instalar ROS 2 — ver la entrada de la parte 3.)

**`provision.sh`** — de un 24.04 limpio a robot terminado, idempotente. No duplica nada:
orquesta `fase_0_1_fix_uart.sh` y `fase_1_higiene_so.sh`. Su bloque de ROS 2 está
**deliberadamente vacío**, porque la Etapa E no se había ejecutado al escribirlo y poner
comandos sin probar es lo que este proyecto no hace.

**`preparar_tarjeta.sh`** — corre en el **PC** sobre una tarjeta recién grabada: `cmdline.txt`,
`config.txt` con `[all]` y `robot_id.txt`. Elimina el editar ficheros con el Bloc de notas, que
para un robot es tolerable y para 15 es una fuente garantizada de errores silenciosos. Probado
en seco contra copias de la partición FAT, incluido un **caso de control**
(`dtoverlay=dwc2,dr_mode=host` bajo `[cm4]` se detecta como inactivo), que es lo que demuestra
que el `awk` distingue secciones de verdad.

### Por qué imagen dorada: es ancho de banda, no comodidad

Aprovisionar un robot descarga ~1.5 GB *(⚠️ estimación, corregida a ~300 MB medidos en la parte 3)*. Quince robots serían ~22 GB sobre la única AP del
laboratorio**, que es el riesgo nº4 de `FLOTA.md` — el que sigue sin medir y el más probable.
Con imagen dorada son **0 GB de red**.

Pero una imagen que nadie sabe reconstruir es una **caja negra**, y ese es exactamente el
problema del `MANUAL SPHERO.docx` original. De ahí la relación: `provision.sh` construye el
robot de referencia, la imagen se hace de él, y si divergen **gana el script**. Coste por robot
nuevo: **~3 minutos atendidos**.

### Un tercer defecto propio, encontrado al probar

`verificar_robot.sh --hardware` salía **siempre** con código 2, porque el aviso «esto despierta
el robot» —informativo— se estaba contando como problema. Eso deja el código de salida inútil
para automatizar «¿pasó este robot?». Corregido a mensaje informativo.

### Pendiente

1. **Etapa E1: instalar `ros-jazzy-ros-base`** (manual cap. 5.2, todavía NO VERIFICADO), y
   luego la Fase 2 del plan: portar el driver a `rclpy` con el **watchdog de `cmd_vel`** y las
   unidades en rad/s.
2. 👤 **Reserva DHCP para `rvr-01`** (MAC `d8:3a:dd:d6:c1:ee`). Hoy tiene IP dinámica
   `192.168.1.58` y puede cambiar. Mejor hacerlo con un robot que con dieciséis.
3. 👤 **Anotar dónde está guardada la imagen `dd`**, con sus dos copias. Hay una tabla
   esperándolo en `RECUPERACION.md`. Una imagen que nadie encuentra no es un respaldo.
4. 👤 **Confirmar si la contraseña de `sphero` se rotó** al grabar la imagen. No se puede
   comprobar desde el sistema. En cualquier caso sigue pendiente purgarla del historial de
   `Atriz_web_server`.
5. La regla udev de `/dev/ydlidar` por `ID_PATH` está **propuesta y NO VERIFICADA**: falta
   comprobar que el `ID_PATH` coincide entre dos robots. Si no coincidiera, no es clonable en
   la imagen dorada y habría que generarla en `first-boot.sh`.
6. Medir el arranque tras el próximo reinicio: `snapd.seeded` (3.5 s de los 8.7 s) ya está
   fuera, así que debería bajar. **No se anota ninguna cifra hasta medirla.**

---

## 2026-07-30 (parte 1) — Instalación de 24.04: etapas A, B y C recorridas y verificadas

**El sistema nuevo está instalado y a punto.** Ubuntu Server 24.04.4 LTS · aarch64 ·
Python 3.12.3 · `rvr-01`. Los capítulos **1, 3, 4 y 8** del manual dejan de estar
NO VERIFICADO. Falta el go/no-go del SDK (Etapa D), que es el siguiente paso.

### Los dos scripts fallaban justo donde tocaba usarlos

Ambos con la misma raíz: **fallo silencioso**.

**`fase_0_1_fix_uart.sh` abortaba en el paso 1/4.** Tenía
`USERCFG=/boot/firmware/usercfg.txt` fijo. En 24.04 ese fichero no existe, así que el `grep`
fallaba, caía al `else`, y el `cp -a` sobre un fichero inexistente mataba el script por
`set -euo pipefail` — **antes de escribir la regla udev**. Síntoma: `/dev/rvr` no aparecía.

**`fase_1_higiene_so.sh` no apagaba el power-save del WiFi.** El `ExecStart` era
`iw ... || true`, y **`iw` no viene instalado en Ubuntu Server 24.04**. El
`wifi-no-powersave.service` quedaba en verde sin hacer nada, para siempre. Ahora instala `iw`
(esperando el lock de dpkg, que en un robot recién grabado lo tiene `unattended-upgrades`),
quita el `|| true`, **comprueba el efecto real**, y acumula los pasos no aplicados para
imprimirlos al final y salir con código 1. Antes terminaba en verde pasara lo que pasara.

### Por qué no existe `usercfg.txt` — la respuesta, con evidencia

No falta: **Ubuntu abandonó el esquema en 24.04.** En 20.04, `config.txt` decía «DO NOT
modify» y terminaba en `include syscfg.txt` + `include usercfg.txt`, gestionados por
**`pibootctl`**. En 24.04 `pibootctl` **no se instala**, `config.txt` es la plantilla upstream
de Raspberry Pi OS (`vc4-kms-v3d`, `camera_auto_detect`, `[pi02]`, `[cm4]`) y **no tiene
ninguna línea `include`**. Búsqueda en todo el sistema: cero resultados.

**Crear `usercfg.txt` a mano sería un fichero fantasma** que el firmware nunca lee.

Y **la cabecera `[all]` es obligatoria**: la imagen termina en `[cm4]`, así que lo añadido al
final sin `[all]` quedaría restringido a esa placa y **no se aplicaría en un Pi 4** — existiría
en el fichero sin hacer nada. El script ahora respeta las secciones al comprobar si una clave
está activa; un `grep` normal habría dado por bueno un `disable-bt` colgando bajo `[cm4]`.

Dato colateral útil: `enable_uart=1` estaba en **ambas** versiones. Lo único que faltó siempre
fue `disable-bt`.

### `unattended-upgrades` viene activo y actualizó el kernel solo

Durante la propia sesión instaló 8 lotes de paquetes en 4 minutos, incluido
`linux-image-6.8.0-1060-raspi` sobre un sistema corriendo el `1047`, dejando
`/var/run/reboot-required`.

Obligó a reordenar el plan: **cerrar las actualizaciones y reiniciar antes de tocar el
device-tree**, o un mismo reinicio aplica dos cambios y un fallo posterior no es atribuible
(regla nº4). Nuevo apartado 3.5.1 del manual. El capítulo 4 lo deshabilita.

También aprovechó que `dtoverlay=disable-bt` **ya estaba en efecto** (editado desde Windows
antes del primer arranque) para ahorrarse un reinicio: la regla udev y los `systemctl` surten
efecto al instante, así que el script ahora solo pide reiniciar cuando de verdad hace falta.

### Verificado sobre el robot real

| Prueba | Resultado |
|---|---|
| `uart0` | `/soc/serial@7e201000` (PL011) · mini-UART `disabled` |
| `/dev/rvr` | → `ttyAMA0` |
| `raw_uart.py` | **el RVR CONTESTA (55 bytes)** · firmware `09 00 01 01` = **9.1.462** |
| `x2_parse.py` | **1144/1144 checksums = 100 %**, 2970 muestras/s, **11.48 Hz**, 1.39° |
| Higiene | `multi-user.target`, governor `performance`, `Power save: off`, `cloud-init` fuera, timers de `apt` fuera, `noatime`, `systemctl --failed` vacío |

El número de bytes de `raw_uart.py` varía entre ejecuciones (46 en 20.04, 55 aquí) porque el
RVR intercala notificaciones asíncronas. Lo que importa es que haya respuesta con checksum
válido, no la cifra.

### `x2_parse.py` mentía, y ya no

Imprimía **480 Hz** de frecuencia de giro en 20.04 y **741 Hz** en 24.04, para un sensor cuya
especificación son 6–12 Hz. Calculaba la mediana de los intervalos de llegada de paquetes, que
salen del buffer USB **a ráfagas** de ~1.3 ms. Ahora divide vueltas entre duración: **11.48
Hz**, coincidiendo con las 138 vueltas contadas a mano el 2026-07-29.

Queda la lección general: **un timestamp tomado al leer de un buffer no mide cuándo ocurrió el
evento.** `CLAUDE.md` pasa de «dos herramientas mienten» a una.

### Un falso positivo propio, y por qué se deja escrito

El mecanismo de fallo ruidoso que se añadió al script de higiene **reportó
`power-save NO quedó apagado` cuando sí lo estaba**. La causa era el verificador: buscaba
`power save:` en minúsculas e `iw 6.7` imprime `Power save: off`. Corregido con `grep -oi`.

Se documenta porque es el resultado honesto: el mecanismo funcionó a la primera y lo primero
que encontró fue a sí mismo. Sigue siendo preferible a un verificador que da verde mintiendo,
que es exactamente lo que hacía el script antes.

Segundo defecto del mismo estilo: `systemctl is-enabled` de una unidad ausente imprime
`not-found` **y** sale con código ≠ 0, así que el `|| echo no` concatenaba ambas cosas en la
misma variable.

### No se podía hacer `git push`

El sistema nuevo no tenía credenciales: `git fetch` fallaba con `could not read Username`, sin
credential helper, sin `~/.git-credentials` y con `~/.ssh/authorized_keys` **vacío**. El
respaldo de la Fase 0.3 copiaba `~/.ssh` pero **no el token**.

Corregido en `fase_0_3_respaldo.sh` (respalda `~/.git-credentials` y `~/.gitconfig`), y
documentado en `CLAUDE.md` e `INSTALACION.md` §B5 como paso propio de toda instalación nueva.
El script también deja de crear un `estado_sistema_*.txt` nuevo cuando el contenido no ha
cambiado: seis ejecuciones dejaron seis ficheros idénticos salvo la fecha.

### Estado de los tres repositorios — nada se perdió al reflashear

Verificado con `git ls-remote` contra GitHub:

| Repo | Rama | Commit |
|---|---|---|
| `Atriz_rvr` | `main` | `6f48ae1` |
| `Atriz_rvr` | `migracion-ros2` | `24c7749` |
| `Atriz_rvr` | `wip/scripts-estudiantes` | `62e0313` |
| `Atriz_web_server` | `pruebas` | `924d659` |

Coinciden exactamente con lo documentado en `TRASPASO.md`. El stash rescatado sobrevivió.

### Nueva carpeta de evidencia

`00_auditoria/evidencia_24_04/`, con su `README.md`, separada de `00_auditoria/evidencia/`
(el sistema viejo). **Comparar 24.04 contra los números de 20.04 es la deriva que este
repositorio existe para evitar**, así que la separación es deliberada y está avisada en los
seis sitios donde el manual pide «comparar con la línea base».

Línea base de 24.04 recién instalado: userspace **1 min 39 s** (`cloud-final` = 1 min 7 s),
187 tareas, journal 17.7 MB, `io.full total` 74.6 s / 34 min, governor `ondemand`,
`graphical.target`, 63.7 °C sin throttling.

### Pendiente

1. **Etapa D — el GO/NO-GO del SDK en Python 3.12.** Es el siguiente paso y el punto de
   decisión de toda la migración. No instalar ROS 2 antes.
2. **Medir la Etapa C con contadores a cero:** arranque, tareas y presión de I/O tras el
   reinicio. Los números pre-reinicio incluyen todo el trabajo de `apt` y no sirven.
3. **Confirmar si la contraseña de `sphero` se rotó de verdad** al grabar la imagen. No se
   puede comprobar desde el sistema; hay que preguntarlo. En cualquier caso sigue pendiente
   purgarla del historial de `Atriz_web_server`.
4. **Anotar dónde está guardada la imagen `dd`** (dos copias). Hay una tabla vacía esperándolo
   en `RECUPERACION.md`. Una imagen que nadie encuentra no es un respaldo.
5. La regla udev de `/dev/ydlidar` por `ID_PATH` está **propuesta y NO VERIFICADA**. Falta
   comprobar que el `ID_PATH` coincide entre dos robots distintos; si no, no es clonable en la
   imagen dorada y habría que generarla en `first-boot.sh`.
6. Siguen abiertas las decisiones de `01_avanzar.py` / `wip/scripts-estudiantes` y de
   `carro.py` / `prueba.py`.

---

## 2026-07-29 (tarde) — Fase 0.1 completada y auditoría corregida

**Fase 0.1 — completada y verificada sobre el robot real.**

### Lo más importante: el clon local estaba desactualizado

`~/atriz_git/src/Atriz_rvr` estaba **5 commits por detrás de GitHub** y **nunca se le
había hecho `git fetch`**. La auditoría de la mañana se hizo sobre código de octubre
de 2025, ignorando trabajo de marzo de 2026. **Tres hallazgos resultaron erróneos** —
ver «Correcciones tras verificar en banco» en el informe.

Lección para el resto del proyecto: `git fetch` **antes** de auditar nada.

### Estructura de ramas

- `main` local puesto al día con `origin/main` (`659364c`), fast-forward limpio.
- Rama nueva **`migracion-ros2`** creada **desde `origin/main`**, no desde el local obsoleto.
- Los 3 scripts de estudiantes sin commitear quedaron en `stash@{0}`.
- `migracion-ros2` **subida a GitHub** (`24c7749`).

### UART reparado y verificado

- `dtoverlay=disable-bt` + `enable_uart=1` en `/boot/firmware/usercfg.txt`
- `/etc/udev/rules.d/99-rvr.rules` → `/dev/rvr` → `ttyAMA0` (PL011)
- `bluetooth.service` deshabilitado (no había adaptador registrado)
- Verificado con paquetes crudos: el RVR responde con checksum válido

Falsa alarma que costó tiempo: `uart0_pins` queda con `brcm,pins` vacío tras
`disable-bt`. Decompilando el overlay se ve que **es intencional** — el firmware
asigna los pines, no el kernel. Los cero bytes iniciales eran simplemente que
**el robot estaba dormido**.

### Odometría: de 3.85 Hz a 16.59 Hz con una línea

| `interval` | Frecuencia | σ |
|---|---|---|
| 250 ms (original) | 3.85 Hz | 1.7 ms |
| 100 ms | 9.94 Hz | 2.4 ms |
| **60 ms (elegido)** | **16.59 Hz** | **2.8 ms** |
| 50 ms | no arranca | — |

El firmware cuantiza a múltiplos de 20 ms. Medido también a nivel del SDK sin ROS:
resultado **idéntico**, lo que demuestra que **el anti-patrón del event loop NO era
el cuello de botella**, como afirmaba la auditoría.

Cierra el riesgo «115200 baud no aguanta 20 Hz»: 125 paquetes/s a 60 ms, holgado.

### LIDAR X2 verificado — por primera vez en el proyecto

Nunca se había comprobado. Detectado como CP2102 en `/dev/ttyUSB0` y validado
decodificando el protocolo X2 a mano, **sin instalar el driver ROS**:

| Métrica | Resultado |
|---|---|
| Checksums válidos | **1147 / 1147 = 100 %** |
| Muestras | **2998/s** (especificación: 3000/s) |
| Giro | 138 vueltas en 12.1 s = **11.4 Hz** |
| Puntos por vuelta | 263 → resolución angular **1.37°** |
| Distancias | 0.445 – 3.158 m, mediana 1.205 m |

**Con esto, todo el hardware del robot está verificado.** Lo que queda es software.

Corrección documentada: `x2_parse.py` imprime "480.72 Hz de giro", que es **falso** —
mide intervalos de llegada de paquetes, que llegan a ráfagas desde el buffer USB. El
valor real sale de contar vueltas.

Aviso para la flota: el CP2102 reporta `SerialNumber "0001"`, genérico. Con 16
adaptadores iguales no se podrá hacer regla udev por serial.

### Commits en `migracion-ros2`

```
24c7749  Sensores: bajar el intervalo de streaming de 250 ms a 60 ms
67c8776  UART: usar /dev/rvr en lugar de /dev/ttyS0
```

### Pendiente

1. ~~Subir `migracion-ros2`~~ ✅ hecho (`24c7749` en GitHub).
2. **Fase 0.3 (bloqueante)** — imagen `dd` de la microSD antes de reflashear.
3. ~~Prueba de estabilidad larga~~ ✅ **SUPERADA**: 12 min, 11 962 mensajes a 16.59 Hz,
   **0 huecos**, **0 discontinuidades de secuencia**, **0 mensajes perdidos**, RSS plano
   en 53 MB, temperatura 55.5–57.9 °C. Evidencia en
   `00_auditoria/evidencia/mediciones_banco/estabilidad_12min_2026-07-29.txt`.
4. **Sin medir:** el impacto de las 48 llamadas a `asyncio.run()` en la latencia de
   `cmd_vel`. No afirmar nada sobre ello sin datos.
5. ~~Sin verificar: la parada de emergencia de la web~~ 🔴 **CONFIRMADA ROTA**. Probado
   de extremo a extremo: la web publica en `/rvr/emergency_stop`, que **no existe**;
   el flag no se mueve. Con el topic correcto (`is_emergency_stop`) sí funciona.
   Falla en silencio con `200 OK`. Evidencia en `estop_2026-07-29.txt`.

---

## 2026-07-29 (mañana) — Auditoría inicial y creación del repositorio

**Fase 00 — completada.** Repositorio publicado en
<https://github.com/Bura-hub/Atriz_migracion_ros2> (privado), commit `f714a74`.

### Qué se hizo

- Auditoría completa del sistema: hardware, SO, arranque, rendimiento, térmica,
  almacenamiento, red, UART, software y logs.
- Auditoría del repositorio `Atriz_rvr` (3 paquetes catkin, ~1650 líneas de driver).
- Auditoría de la plataforma web `Atriz_web_server` (rama `pruebas`).
- Transcripción del `MANUAL SPHERO.docx` a Markdown, con anotaciones de auditoría.
- Análisis de compatibilidad del SDK de Sphero con Python 3.12.
- Creación de este repositorio con auditoría, plan, manual y respaldos.

### Qué se verificó

| Medición | Valor |
|---|---|
| Temperatura en reposo-medio | 59.9 °C estable (5 muestras) |
| Throttling / under-voltage | 0 eventos en `dmesg` |
| CPU a 600 MHz | **59.6 %** del tiempo (`time_in_state`) |
| Bloqueo global por I/O | **46.97 s** en 42 min de uptime ocioso |
| Journal | 785 MB, `journald.conf` vacío |
| Arranque | 6.1 s kernel + 29.5 s userspace |
| Tareas en ejecución | 273, con ROS parado |
| Sesiones gráficas | 2 simultáneas (gdm + sphero) |
| WiFi | -62 dBm, 797 reintentos Tx, power-save **on** |
| `dtoverlay=disable-bt` | **ausente** en todos los ficheros de boot |
| `usercfg.txt` | **vacío** |
| Adaptador Bluetooth | **ninguno** (`hciconfig -a` sin salida), `bluetoothd` activo 2m21d |
| `/dev/serial0` | **no existe** |
| Driver YDLIDAR en el sistema | **no existe** (`find` → 0 resultados) |
| SDK Sphero: imports de ROS | **0** de 103 ficheros |
| SDK Sphero: patrones rotos en Py3.12 | **0** `@asyncio.coroutine`, **0** `loop=`, **0** `yield from` |
| SDK Sphero: `get_event_loop()` | 4, de los cuales 3 en el backend `observer` no usado |

Salidas crudas en [`00_auditoria/evidencia/`](00_auditoria/evidencia/).

### Decisiones tomadas

- **Migrar a Ubuntu Server 24.04 + ROS 2 Jazzy** (soporte hasta mayo 2029).
- **Reinstalar sobre la misma microSD**, no comprar tarjeta nueva.
  Reversión mediante imagen `dd` + el manual original.
- **La web hablará por rosbridge + roslibjs**, no por SSH.
- **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total, coordinación en el servidor.
- Alcance objetivo para un robot: teleoperación + telemetría + LIDAR + SLAM + Nav2.
- **Sin cámara** en los robots (confirmado): no se instala `web_video_server`.

### Pendiente para la próxima sesión

1. **Fase 0.1** — aplicar `dtoverlay=disable-bt` + regla udev `/dev/rvr`, deshabilitar
   `bluetooth.service`. Validar 10 min de `/odom` sin cortes. Requiere `sudo` y reinicio.
2. **Fase 0.3 (bloqueante)** — imagen `dd` de la microSD antes de reflashear.
3. Commitear o descartar los 6 cambios sueltos de `Atriz_rvr`
   (respaldados en `04_respaldo/sin_commitear/`).

### Riesgos abiertos

- **Go/no-go de toda la migración:** que el SDK de Sphero funcione en Python 3.12.
  El análisis estático es muy favorable, pero **no está verificado en ejecución**.
  Se prueba al inicio de la Fase 1, antes de portar una sola línea del driver.
- **Sin verificar:** que la parada de emergencia de la web esté realmente rota.
  Los nombres de topic no coinciden (`/rvr/emergency_stop` vs `is_emergency_stop`),
  pero no se ha probado en banco. Es seguridad — verificar como prioridad.
- La credencial del usuario `sphero` está expuesta en GitHub público y **no se ha rotado**.
