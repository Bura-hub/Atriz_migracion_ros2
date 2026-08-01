# Arquitectura

> ## ✅ Estado: **IMPLEMENTADO Y VERIFICADO** salvo la plataforma web (Fase 5)
>
> El robot corre ROS 2 Jazzy, arranca solo con systemd, navega con Nav2 y habla por rosbridge.
> Verificado el 2026-08-01 desde un navegador: `ws://rvr-01.local:9090`, telemetría entrando y
> servicios respondiendo. Lo único que falta es **el cliente web**.
>
> 🔴 **Esta cabecera decía «DISEÑO, NO IMPLEMENTADO. Nada de lo que describe está en marcha
> todavía; el sistema actual sigue siendo ROS Noetic con control por SSH» hasta el
> 2026-08-01.** Era la primera frase del fichero y llevaba semanas siendo falsa. Peor: el
> documento mezclaba secciones actualizadas con secciones de diseño previo, así que **el lector
> no podía saber qué párrafo describía la realidad y cuál una intención**. Se ha revisado
> entero contra el código.
>
> Las decisiones marcadas ✅ están respaldadas por mediciones reales; las marcadas 🔵 son
> razonadas pero **sin verificar**.

---

## El problema que resuelve

Un laboratorio remoto con **16 robots** y varios usuarios simultáneos. Cada usuario
teleopera o programa un robot desde el navegador, ve su telemetría en vivo, y puede lanzar
experimentos.

Lo que hay hoy no llega:

| Hoy | Por qué no escala |
|---|---|
| Un solo `roscore` | Punto único de fallo para los 16 |
| Control por `subprocess.run(["ssh", ...])` en bucle secuencial | Hasta **64 s** por comando con 16 robots (`timeout=4.0` × 16), con FastAPI bloqueado |
| Cada lectura de telemetría abre un proceso SSH nuevo | Sin streaming; imposible ver datos en vivo |
| Contraseña en texto plano en un repositorio público | Comprometida |
| ~~Sin watchdog~~ | 📝 **Era falso incluso sobre ROS 1**: el watchdog ya existía (`cmd_vel_timeout` 0.3 s). Se auditó un commit anterior al que lo añadió |

---

## Decisión 1 ✅ — Un `ROS_DOMAIN_ID` por robot

**Es la decisión estructural más importante del diseño.**

```
Robot 01: ROS_DOMAIN_ID=1,  ws://rvr-01.local:9090  ─┐
Robot 02: ROS_DOMAIN_ID=2,  ws://rvr-02.local:9090  ─┤  16 WebSockets
   ...                                               ├─►  Servidor web
Robot 16: ROS_DOMAIN_ID=16, ws://rvr-16.local:9090  ─┘   (FastAPI + Vue)

   SIN NAMESPACE: los topics son /odom, /scan, /cmd_vel_raw.
   Al robot lo identifica la CONEXIÓN, no el nombre del topic.
```

**Alternativa descartada: un solo dominio DDS con namespaces.** El descubrimiento
multicast de DDS hace que cada participante hable con todos los demás. Con ~10 nodos por
robot × 16 robots ≈ 160 participantes sobre WiFi, el tráfico de descubrimiento satura la
red antes de transportar un solo dato útil.

**Evidencia que lo respalda:** esta Pi, con **un** robot, ya registra **797 reintentos de
Tx en 42 minutos** con señal de −62 dBm. El WiFi no tiene margen para una tormenta de
descubrimiento.

**Consecuencia:** cada robot es una isla DDS completa; no se ven entre ellos. La
coordinación entre robots ocurre en la **capa de aplicación del servidor**, que además es
mucho más fácil de depurar que multicast DDS.

**Vía de escape** 🔵 — si más adelante hace falta comunicación robot-a-robot real en DDS
(experimentos *swarm* donde la latencia por el servidor no valga), se añade
`zenoh-bridge-ros2dds` o un FastDDS Discovery Server. **No obliga a rehacer nada**: se
añade encima.

---

## Decisión 2 🔵 — La web habla por rosbridge, no por SSH

| Capa | De qué se encarga | De qué NO |
|---|---|---|
| **roslibjs** (navegador) | Suscripción a `odom`, `scan`, `battery_state`, `map`; publicación de **`cmd_vel_raw`** | Autenticación, persistencia |
| **FastAPI** | JWT, reserva de robots por usuario, catálogo, experimentos, logging | Estar en la ruta de los datos en vivo |
| **SSH** | ~~Ciclo de vida del stack ROS~~ → **ya no hace falta**: `atriz-robot.service` levanta el robot al encender y se recupera solo (manual, cap. 17). Queda solo para **mantenimiento** | Cualquier cosa de la operación normal |

**Por qué:** la telemetría en vivo no puede pasar por un proceso SSH nuevo en cada lectura.
Con rosbridge, el navegador mantiene **un** WebSocket por robot y recibe los datos
empujados. FastAPI deja de ser cuello de botella porque deja de estar en medio.

### Cómo localiza la web a cada robot

**Por nombre, no por IP:** `ws://rvr-NN.local:9090`, con la IP como override configurable. Eso es
lo que hace que **el mismo código funcione en el PC de casa y en el laboratorio** sin tocar nada.

Cada robot tiene además una **IP estática por red**, generada por `first-boot` desde
`/boot/firmware/red.txt` — así el robot es alcanzable aunque mDNS falle, y sin depender de que
nadie configure el router. Manual, cap. 19.

⚠️ **Comprobar en el aula si el AP tiene aislamiento de clientes.** Rompería mDNS *y* la
comunicación PC↔robot si el PC va por WiFi.

### Contrato de topics por robot

> ## ✅ DECISIÓN CERRADA (2026-08-01): **SIN NAMESPACE**
>
> Los topics son `/odom`, `/scan`, `/cmd_vel_raw` — **no** `/rvr_01/odom`. Tres razones, en orden
> de peso:
>
> **1. El aislamiento ya está resuelto por otra vía.** Cada robot corre en su propio
> `ROS_DOMAIN_ID` (Decisión 1). Eso es aislamiento DDS **total**: los robots no se ven entre sí ni
> queriendo. Un namespace resolvería un problema que ya no existe.
>
> **2. La web tampoco lo necesita.** Habla por rosbridge, **un WebSocket por robot**:
> `ws://rvr-07.local:9090`. Esa conexión ya solo alcanza al robot 7. Poner `/rvr_07/odom` dentro
> de un canal que únicamente llega al robot 7 es escribir el número dos veces.
>
> **3. 🔴 Y la razón de peso: la parada de emergencia ya falló una vez POR UN NAMESPACE.** Al
> portar de ROS 1 se corrigió el nombre del topic y se coló un `/rvr/`; falló en silencio, con
> `200 OK`. Añadir namespaces reintroduce esa clase de fallo **en 16 robots a la vez**, y es un
> fallo de seguridad, no de comodidad. Van cuatro fallos de la parada, y este documento no va a
> regalar el quinto.
>
> ⚠️ **Y un namespace no hace lo que suele creerse: NO renombra los `frame_id` de TF.** Si algún
> día se metiera a los 16 robots en un mismo dominio, seguirían colisionando dieciséis
> `odom → base_footprint`. Da protección **parcial**, que es peor que ninguna porque parece
> completa.
>
> ### El camino de escape queda abierto, y ahora funciona
>
> `robot.launch.py`, `slam`, `nav2` y `localizacion` **ya aceptan un argumento `namespace`** con
> `''` por defecto. Se deja: si algún día se quiere ver varios robots en un mismo RViz, es cambiar
> una bandera.
>
> 🔴 **Pero ese camino estaba roto hasta hoy.** El driver tenía `odom_frame`, `base_frame` e
> `imu_frame` como parámetros y **dos `frame_id` escritos a fuego** (`/ambient_light` y
> `/motor_status`). Con el namespace activo se habrían quedado sin prefijo, partiendo el árbol TF
> — el mismo fallo que costó la Fase 3. Ahora es el parámetro **`body_frame`** (`base_link` por
> defecto). ✅ Verificado tras el cambio: los dos topics siguen publicando con `base_link`.

| Topic / servicio | Tipo | Dirección | Nota |
|---|---|---|---|
| `odom` | `nav_msgs/Odometry` | robot → web | 16.5 Hz · 🔴 **BEST_EFFORT** |
| `imu` | `sensor_msgs/Imu` | robot → web | 16.5 Hz · 🔴 **BEST_EFFORT** |
| `scan` | `sensor_msgs/LaserScan` | robot → web | 10 Hz · 🔴 **BEST_EFFORT** · 0 si el barrido está parado |
| `battery_state` | `sensor_msgs/BatteryState` | robot → web | **RELIABLE + TRANSIENT_LOCAL** · cada 30 s · `percentage` es **0–1**, no % · 🔴 **usa `voltage`, no `percentage`** — ver abajo |
| `motor_status` | `atriz_rvr_msgs/MotorStatus` | robot → web | **RELIABLE + TRANSIENT_LOCAL** · se **sondea cada 30 s** y se republica a 1 Hz |
| `encoders` | `atriz_rvr_msgs/Encoder` | robot → web | 16.5 Hz · 🔴 **BEST_EFFORT** · ticks con signo |
| `color` | `atriz_rvr_msgs/Color` | robot → web | 🔴 **BEST_EFFORT** · `[0,0,0]` salvo `color_detection:=true` |
| `ambient_light` | `sensor_msgs/Illuminance` | robot → web | 🔴 **BEST_EFFORT** · ⚠️ **NO SE USA**: ve los LEDs del propio robot |
| `collision_monitor_state` | `nav2_msgs/CollisionMonitorState` | robot → web | dice **si la seguridad está frenando**. Útil para la web |
| `map` | `nav_msgs/OccupancyGrid` | robot → web | RELIABLE + TRANSIENT_LOCAL |
| **`cmd_vel_raw`** | `geometry_msgs/Twist` | web → robot | 🔴 **AQUÍ, no en `cmd_vel`** — ver abajo |
| **`emergency_stop`** | `std_msgs/Empty` | web → robot | ✅ **el oficial**. RELIABLE + **VOLATILE** |
| **`/start_scan`** | `std_srvs/Empty` | web → robot | 🔴 **OBLIGATORIO al empezar sesión** |
| `/stop_scan` | `std_srvs/Empty` | web → robot | al terminar la sesión |
| `/release_emergency_stop` | `std_srvs/Empty` | web → robot | liberar la parada, acto **explícito** |

### Los otros servicios del driver — la web puede llamarlos, y algunos son peligrosos

La tabla de arriba solo lista los tres que la web necesita en su ciclo normal. **El driver
expone 18**, y **todos son alcanzables por rosbridge**, así que conviene saber qué hay:

| Grupo | Servicios | Riesgo |
|---|---|---|
| LEDs | `set_led_rgb`, `set_leds`, `set_all_leds`, `turn_leds_off` | ninguno |
| Sensores | `get_rgbc_sensor_values`, `enable_color_detection`, … | ninguno |
| Configuración | `set_drive_parameters`, `reset_locator`, `reset_yaw` | bajo |
| 🔴 **Movimiento** | `move_timed`, `raw_motors`, `move_to_pose`, `move_to_pos_and_yaw` | **alto** |
| 🔴 **Infrarrojos** | `set_ir_mode`, `set_ir_evading` | **alto** |

🔴 **Los servicios de movimiento SE SALTAN el `collision_monitor` y el watchdog.** No publican
en ningún topic: hablan al RVR **por el puerto serie**. Lo único que los para es la parada de
emergencia. Y `raw_motors` **no tiene corte automático**: sigue hasta que se le manda modo 0.

⚠️ **`set_ir_evading` y `set_ir_mode('following')` hacen conducir al robot SOLO**, por firmware.
No los uses desde la web sin espacio despejado. Comprueban la parada de emergencia **desde el
2026-08-01** — antes no, y era un agujero real.

📝 **Y `ros2 service list` no es autoritativo:** omitió 1 de los 18. Para saber si un servicio
existe, usa un cliente.

🔴 **`cmd_vel_raw`, NO `cmd_vel`.** Este documento decía `cmd_vel`, y eso **salta la capa de
seguridad**: `/cmd_vel` es la **salida** del `collision_monitor` y tiene un solo publicador. La
cadena es `web → cmd_vel_raw → collision_monitor → cmd_vel → driver`. Publicar en `/cmd_vel`
funciona —el robot obedece— y por eso es peligroso. Manual, cap. 12.

🔴 **Para la batería, la web debe mirar `voltage`, no `percentage`.** Medido: el porcentaje
decía **100 %** con la batería a **8.29 V**, a 1.29 V del umbral de «baja». Es una estimación
gruesa. Los umbrales son del propio firmware y el driver los registra en el log al arrancar:

| | |
|---|---|
| batería **baja** | `voltage` < **7.0 V** |
| batería **crítica** | `voltage` < **6.5 V** — el RVR se apagará |
| histéresis | **0.2 V**, la aplica el firmware (no rebota solo) |

⚠️ `power_supply_health` **no puede expresar «baja»**, y no se fuerza: una batería con poca
carga está **sana**, no averiada. Solo «crítica» se mapea a `DEAD`.

🔴 **`/start_scan` es obligatorio.** Los robots arrancan solos pero con el **barrido del lidar
parado**, y sin `/scan` el `collision_monitor` **bloquea el movimiento**. Un robot recién
encendido **no obedece `cmd_vel`** y desde la web se verá igual que uno averiado. Manual,
cap. 17.2.

🔴 **SEIS topics de telemetría son BEST_EFFORT**, no cuatro: `odom`, `imu`, `scan`, `color`,
`ambient_light` y `encoders` — todos comparten el mismo `qos_tel` del driver. Un suscriptor con el perfil por defecto
pide RELIABLE, **DDS no empareja y no llega NADA** — sin error y sin aviso. Si la web «no recibe
odometría» y todo lo demás parece bien, **mira el QoS antes que el código**.

## ✅ DECISIÓN CERRADA (2026-08-01): el nombre oficial de la parada es **`/emergency_stop`**

Es a donde **debe publicar la web**. Sin namespace, es además el nombre resuelto real.

⚠️ **El driver sigue escuchando los tres** (`emergency_stop`, `is_emergency_stop` y
`/rvr/emergency_stop`) y eso **no se toca**. No es indecisión: con un botón de emergencia el modo
de fallo que importa es **«el mensaje no llega»**, y escuchar de más no cuesta nada mientras que
escuchar de menos ya ha fallado **cuatro veces** — por nombre, por namespace, por QoS, y por no
cancelar el objetivo de Nav2 al soltarla.

🔴 **Lo que sí es obligatorio para la web:** publicar `std_msgs/Empty` con QoS **RELIABLE +
VOLATILE**. `TRANSIENT_LOCAL` en el suscriptor fue la tercera causa de fallo: exige que el
publicador también lo sea, y **rosbridge no lo es**. Manual, cap. 15.1.

📝 `ambient_light` existe y **no se usa**: el piso blanco del LIDAR le refleja los LEDs del propio
robot, así que no mide la luz de la sala. Manual, cap. 18.4b.

---

## Decisión 3 ✅ — Seguridad: cuatro defensas, todas verificadas

> 🔴 **Esta sección describía toda la capa de seguridad como inexistente hasta el 2026-08-01**,
> y recomendaba `TRANSIENT_LOCAL` para la parada — que es **la tercera causa de fallo** ya
> documentada. Quien programara la web leyéndola habría reintroducido el fallo. Reescrita
> contra el código.

La parada por software **nunca** es la única defensa, y aquí no lo es.

**a) ✅ Parada de emergencia.** Oficial: **`/emergency_stop`** (`std_msgs/Empty`), QoS
**RELIABLE + VOLATILE**. Ver la decisión cerrada más arriba. Ha fallado **cuatro** veces en la
historia del proyecto —nombre, namespace, QoS y no cancelar Nav2— y las cuatro están cerradas y
verificadas con control.

**b) ✅ Watchdog de `cmd_vel`, y ya existía.** `cmd_vel_timeout` = **0.3 s** (no los 500 ms que
decía este documento), comprobado a 20 Hz. Medido con `medir_watchdog_ros2.py`, que mide
**desplazamiento** y no velocidad: **para en 527 ms / 7.9 cm**.

Es la defensa que de verdad importa, porque **no depende de que la red funcione para actuar**:
actúa *porque* la red falló.

**c) ✅ `collision_monitor`**, que las otras dos no cubren. Cadena:
`web → cmd_vel_raw → collision_monitor → cmd_vel → driver`. Para a **9.9 cm** a 0.25 m/s y
**10.6 cm** a 0.40. Y **sin `/scan` bloquea el movimiento**, así que un robot recién arrancado
no conduce hasta que la web llame a `/start_scan`.

**d) ✅ `on_exit=Shutdown()`** en el driver y en el `collision_monitor`. Si uno muere, se cae el
launch entero y systemd lo reinicia — **25 s** y el robot vuelve completo. Sin esto, el PID
principal es el `ros2 launch`, que sobrevive: un robot inservible con el servicio en verde.

⚠️ **El LIDAR no lo lleva, y no es contradicción:** sin `/scan` el `collision_monitor` bloquea
el movimiento y el robot queda **seguro**. Si muriera el monitor, quedaría conduciendo **sin
filtro**. Son situaciones opuestas.

**e) Estado de conexión visible en la UI.** ⏳ **Pendiente, es de la Fase 5.** Si el usuario no
sabe que perdió el enlace, seguirá dando órdenes al vacío.

🔴 **Lo que estas defensas NO cubren:** los servicios de movimiento del driver
(`move_timed`, `raw_motors`, `move_to_pose`, `move_to_pos_and_yaw`, `set_ir_evading`) hablan al
RVR **por el puerto serie**, así que ni el watchdog ni el `collision_monitor` los ven. Solo los
para la parada de emergencia — y `set_ir_evading` **no la comprobaba hasta el 2026-08-01**.

---

## Decisión 4 🔵 — Los robots siguen etiquetas, no ramas

Con 16 robots la pregunta que importa no es «¿cuántas ramas tiene el repositorio?» sino
**«¿qué commit exacto corre cada robot?»**.

Una rama se mueve bajo tus pies; un tag es inmutable. Los robots se despliegan desde
**tags** (`v0.1-noetic`, `v1.0-jazzy`), nunca desde `main` ni desde ramas de trabajo.
Cuando uno falle, `git describe` dice exactamente qué tiene, y es reproducible.

**Aprendido por las malas:** el clon local de `Atriz_rvr` en esta Pi estaba **5 commits por
detrás** de GitHub y **nunca se le había hecho `git fetch`**. Una auditoría completa se
escribió sobre código de nueve meses de antigüedad y tres hallazgos resultaron falsos.
Multiplicar eso por 16 máquinas es el modo de fallo a evitar.

---

## Stack por robot

```
Ubuntu Server 24.04 LTS arm64 (headless, multi-user.target)
└── ROS 2 Jazzy (ros-base, NO desktop)
    ├── atriz_rvr_driver      (rclpy) → odom, imu, battery_state, color, encoders,
    │                                    ambient_light, motor_status ; ← cmd_vel
    ├── collision_monitor     cmd_vel_raw (web) → cmd_vel (driver) ← LA SEGURIDAD VA AQUÍ
    ├── atriz_rvr_description (URDF/xacro) + robot_state_publisher
    ├── ydlidar_ros2_driver   → scan
    ├── slam_toolbox          (async) → map
    ├── nav2                  → navegación autónoma
    └── rosbridge_websocket   :9090 ← único punto de contacto con la web
                              ⚠️ dentro de robot.launch.py, NO en unidad systemd propia:
                                 así hereda el ROS_DOMAIN_ID
```

### Árbol TF objetivo

```
map → odom → base_footprint → base_link → { laser, imu_link, wheel_* }
```

✅ **Y es el árbol REAL desde el 2026-07-30**, no un objetivo.

El driver publica **`odom → base_footprint`** (parámetro `base_frame`, por defecto
`base_footprint`). `robot_state_publisher` publica el resto desde
`atriz_rvr_description/urdf/rvr.urdf.xacro`.

🔴 **Este párrafo decía `odom → base_link`, y esa es exactamente la configuración que partió el
árbol en la Fase 3**: el driver publicaba `odom → base_link` y el URDF
`base_footprint → base_link`, o sea **un frame con dos padres**. El árbol se cortó en dos y
`slam_toolbox` repetía `Failed to compute odom pose`.

⚠️ **Y la lección de método:** la verificación de entonces era `tf2_echo odom laser` y **pasaba**,
resolviendo por el camino equivocado. **Comprueba el transform que pide el consumidor**, aquí
`tf2_echo odom base_footprint`.

📝 También decía que **no existe ningún URDF**. Existe desde el 2026-07-30.

---

## Presupuestos medidos

Lo que está cuantificado, para no diseñar sobre suposiciones:

| Recurso | Medido | Fuente |
|---|---|---|
| Odometría | **16.59 Hz**, σ 2.8 ms | Fase 0.1, `interval=60` |
| Techo del RVR | **60 ms mínimo**, cuantizado a 20 ms | barrido de intervalos |
| UART | 125 paquetes/s de 8 sensores en 115200 baud (~11.5 KB/s) | `sdk_full.py` |
| LIDAR X2 | 10 Hz, canal único, sin intensidad, ~8 m útiles | hoja de datos |
| CPU del driver | **15.9 %** de un núcleo · **33.6 %** desde que lleva keepalive | 24.04, `/proc` |
| RAM del driver | 53 MB, plana | prueba de estabilidad |
| Temperatura | **62–64 °C** con el stack completo, `throttled=0x0` | 24.04 |
| **Ancho de banda por rosbridge** | **80.7 kB/s** navegando · 13.6 en reposo · ×16 = **10.3 Mbit/s** | evidencia 39 |
| Stack completo (driver+LIDAR+SLAM+Nav2) | **~89 %** de un núcleo, 477 MB | 2026-07-31 |

⚠️ **Las cifras de CPU y temperatura anteriores (29 %, 57 °C) eran del sistema VIEJO** — 20.04
con el nodo de ROS Noetic — y estaban presentadas como referencia actual. Mezclar las dos líneas
base es un error que este proyecto prohíbe explícitamente.

**Lo que era «sin medir» y ya está medido:**

- ✅ **Ancho de banda con rosbridge.** Era el riesgo nº4 del proyecto. **80.7 kB/s por robot
  navegando → 10.3 Mbit/s los 16.** Medido dos veces, con dos clientes distintos en dos
  máquinas distintas. Y `/scan` es el **83 %**: sin él los 16 caben en 1.7 Mbit/s.
- ✅ **Nav2 cabe en el Pi 4**: el stack completo son ~89 % de **un** núcleo de cuatro.

**Sigue sin medir:**

- **Latencia de `cmd_vel` de extremo a extremo** (navegador → motores). Hace falta la web.
