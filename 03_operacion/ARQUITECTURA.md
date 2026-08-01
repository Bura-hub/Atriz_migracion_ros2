# Arquitectura

> **Estado: DISEÑO, NO IMPLEMENTADO.** Este documento fija las decisiones antes de
> escribir código, para no descubrirlas a medias. Nada de lo que describe está en marcha
> todavía; el sistema actual sigue siendo ROS Noetic con control por SSH.
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
| Sin watchdog | Si cae la red, el robot sigue conduciendo |

---

## Decisión 1 ✅ — Un `ROS_DOMAIN_ID` por robot

**Es la decisión estructural más importante del diseño.**

```
Robot 01: ROS_DOMAIN_ID=1, namespace /rvr_01, rosbridge :9090  ─┐
Robot 02: ROS_DOMAIN_ID=2, namespace /rvr_02, rosbridge :9090  ─┤  16 WebSockets
   ...                                                          ├─►  Servidor web
Robot 16: ROS_DOMAIN_ID=16, namespace /rvr_16, rosbridge :9090 ─┘   (FastAPI + Vue)
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
| `battery_state` | `sensor_msgs/BatteryState` | robot → web | cada 30 s · `percentage` es **0–1**, no % |
| `motor_status` | `atriz_rvr_msgs/MotorStatus` | robot → web | 1 Hz · temperatura y fallo de motores |
| `encoders` | `atriz_rvr_msgs/Encoder` | robot → web | 16.5 Hz · ticks con signo |
| `color` | `atriz_rvr_msgs/Color` | robot → web | `[0,0,0]` salvo `color_detection:=true` |
| `map` | `nav_msgs/OccupancyGrid` | robot → web | RELIABLE + TRANSIENT_LOCAL |
| **`cmd_vel_raw`** | `geometry_msgs/Twist` | web → robot | 🔴 **AQUÍ, no en `cmd_vel`** — ver abajo |
| **`emergency_stop`** | `std_msgs/Empty` | web → robot | ✅ **el oficial**. RELIABLE + **VOLATILE** |
| **`/start_scan`** | `std_srvs/Empty` | web → robot | 🔴 **OBLIGATORIO al empezar sesión** |
| `/stop_scan` | `std_srvs/Empty` | web → robot | al terminar la sesión |
| `/release_emergency_stop` | `std_srvs/Empty` | web → robot | liberar la parada, acto **explícito** |

🔴 **`cmd_vel_raw`, NO `cmd_vel`.** Este documento decía `cmd_vel`, y eso **salta la capa de
seguridad**: `/cmd_vel` es la **salida** del `collision_monitor` y tiene un solo publicador. La
cadena es `web → cmd_vel_raw → collision_monitor → cmd_vel → driver`. Publicar en `/cmd_vel`
funciona —el robot obedece— y por eso es peligroso. Manual, cap. 12.

🔴 **`/start_scan` es obligatorio.** Los robots arrancan solos pero con el **barrido del lidar
parado**, y sin `/scan` el `collision_monitor` **bloquea el movimiento**. Un robot recién
encendido **no obedece `cmd_vel`** y desde la web se verá igual que uno averiado. Manual,
cap. 17.2.

🔴 **Los cuatro topics de telemetría son BEST_EFFORT.** Un suscriptor con el perfil por defecto
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

## Decisión 3 🔵 — Seguridad: dos defensas independientes

La parada por software **nunca** debe ser la única defensa. Hoy lo es — y probablemente ni
funciona.

**a) Unificar el topic de emergencia.** La web publica en `/rvr/emergency_stop`; el driver
escucha `is_emergency_stop`. **Nombres distintos**, así que el botón de emergencia del
panel probablemente no hace nada. *(Pendiente de verificar en banco. Es seguridad y merece
comprobación explícita, no deducción.)*

Unificar en `/<ns>/emergency_stop` (`std_msgs/Empty`) con QoS **reliable** + **transient
local**, para que un suscriptor que conecte tarde reciba el último mensaje.

**b) Watchdog de `cmd_vel` en el driver.** Si no llega `cmd_vel` en **500 ms**, parar
motores. Hoy no existe: si el WebSocket se cae —y con 797 reintentos de Tx en 42 minutos,
se caerá— el robot **sigue conduciendo con el último comando**.

El watchdog es la defensa que de verdad importa, porque **no depende de que la red funcione
para actuar**. Es justo al contrario: actúa *porque* la red falló.

**c) Estado de conexión visible en la UI.** Si el usuario no sabe que perdió el enlace,
seguirá dando órdenes al vacío.

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
    ├── atriz_rvr_driver      (rclpy) → odom, imu, battery, color, encoders ; ← cmd_vel
    ├── atriz_rvr_description (URDF/xacro) + robot_state_publisher
    ├── ydlidar_ros2_driver   → scan
    ├── slam_toolbox          (async) → map
    ├── nav2                  → navegación autónoma
    └── rosbridge_server      :9090 ← único punto de contacto con la web
```

### Árbol TF objetivo

```
map → odom → base_footprint → base_link → { laser, imu_link, wheel_* }
```

El driver publica **solo** `odom → base_link`. `robot_state_publisher` publica el resto
desde el URDF.

**Hoy el árbol está partido en dos:** el driver publica `odom → rvr_base_link`
(`Atriz_rvr_node.py:99`) y el LIDAR cuelga de `base_link` vía un
`static_transform_publisher`. Sin puente entre ambos, cualquier SLAM o navegación es
imposible. Y **no existe ningún URDF** en el repositorio.

---

## Presupuestos medidos

Lo que está cuantificado, para no diseñar sobre suposiciones:

| Recurso | Medido | Fuente |
|---|---|---|
| Odometría | **16.59 Hz**, σ 2.8 ms | Fase 0.1, `interval=60` |
| Techo del RVR | **60 ms mínimo**, cuantizado a 20 ms | barrido de intervalos |
| UART | 125 paquetes/s de 8 sensores en 115200 baud (~11.5 KB/s) | `sdk_full.py` |
| LIDAR X2 | 10 Hz, canal único, sin intensidad, ~8 m útiles | hoja de datos |
| CPU del driver | ~29 % de un núcleo a 16.5 Hz | prueba de estabilidad |
| RAM del driver | 53 MB, plana | prueba de estabilidad |
| Temperatura | 57 °C con el driver activo | prueba de estabilidad |

**Sin medir todavía:**

- **Ancho de banda por robot con rosbridge activo.** Es el **riesgo principal de los 16**:
  con 16 clientes de telemetría continua en un solo punto de acceso, la red es el cuello de
  botella más probable del laboratorio entero. Hay que medirlo con un robot y extrapolar
  **antes** de comprar hardware de red.
- Si Nav2 cabe en el Pi 4 junto al resto del stack.
- Latencia de `cmd_vel` de extremo a extremo (navegador → motores).
