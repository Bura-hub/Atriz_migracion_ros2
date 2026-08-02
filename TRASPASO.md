# Traspaso — dónde estamos y cómo seguir

> **Léelo si retomas el proyecto** después de un tiempo, en otra máquina, o si la
> Raspberry Pi ya se reflasheó. Está escrito para que no haga falta reconstruir el
> contexto desde cero.
>
> Última actualización: **2026-08-01** (tras explorar el SDK entero y cerrar la 2ª auditoría).

---

## En una frase

✅ **Y la RED DE LA FLOTA está resuelta y verificada de extremo a extremo (2026-08-01).** Un
navegador del PC abre `ws://rvr-01.local:9090`, recibe telemetría y **enciende los faros** —
resolviendo **por nombre**, sin ninguna IP. `wlan0` lleva **tres direcciones a la vez**
(laboratorio + casa + DHCP), así que el robot se muda sin tocar un comando. Ancho de banda
medido dos veces con dos clientes distintos: **80.7 kB/s navegando → 10.3 Mbit/s los 16**, y
`/scan` es el **83 %**. Manual, **cap. 19**.

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

✅ **Y la deriva de la localización está resuelta.** Con 24 corridas apareció que **~1 de cada
5 se iba a 6–56 cm**; la causa era que **el robot no volvía a su sitio** (~8 cm de deriva por
corrida). Referenciando la posición antes de cada corrida: **0 fallos de 12**, peor caso
**4.4 cm**, y la deriva **no crece con la distancia** (1.55 cm a 1.6 m, 0.90 cm a 2.3 m). Muy
por debajo de la tolerancia de 10 cm de Nav2. Manual, **cap. 9.12c**.

✅ **Y los TRES bugs de marcos de referencia de `/odom` están arreglados y verificados.** Los
sensores del RVR siempre estuvieron bien —`Velocity` es exacto, el locator acierta con 1 mm en
1 m—; lo que fallaba era cómo el driver los combinaba. Ahora el yaw arranca en **+0.00°**, la
dirección de avance coincide con él (**+0.03°**), y `odom.twist.linear` da la velocidad en el
marco del robot con un **2 % de error** mire donde mire (`15_velocidad_odom.txt`).

✅ **Y Nav2 NAVEGA.** Dos objetivos autónomos completados con **9–10 cm de error final**, que
es la tolerancia configurada. Coste: ~89 % de **un** núcleo con todo el stack, `loadavg` 2.53
sobre 4, sin throttling. Manual, **cap. 11**.

✅ **Y la capa de seguridad está puesta y medida.** El `collision_monitor` para el robot a
**8 cm de una pared a 0.25 m/s y a 9 cm a 0.40 m/s**, sin dejarlo atrapado, y sin LIDAR
**bloquea la conducción por completo** (0.0 cm de movimiento, comprobado matando el nodo).
De paso destapó un agujero: el `behavior_server` de Nav2 publicaba en `/cmd_vel`
**saltándose la seguridad**. Manual, **cap. 12**.

✅ **Y ya navega a 0.40 m/s**, el máximo del robot: meseta medida en **0.407 m/s**, dos
objetivos `SUCCEEDED` con **8 cm** de error cada uno — *mejor* que los 9–10 cm de las corridas
a 0.25. La capa de seguridad solo se activó cuatro veces y ninguna fue una parada.

✅ **Y rodea obstáculos.** Cuatro navegaciones seguidas esquivando una caja de 16 cm puesta en
medio del camino: **todas `SUCCEEDED`, todas por la derecha, 8–9 cm de error** — el mismo que
sin obstáculo. Manual, **cap. 11.13**.

🔴 **Y el paso estrecho dio el límite: con `radius: 0.18` NO cruza 40 cm.** El robot entró en
la boca, con el camino despejado delante y sin tocar nada, y se bloqueó — el borde estaba a
17 cm y su círculo mide 18. Salió marcha atrás sin problema. No es un fallo: es el compromiso
`parar lejos de las paredes` ↔ `cruzar huecos estrechos`, ahora medido.

🔴 **Y por el camino salió que el URDF tenía largo y ancho CRUZADOS.** El robot mide **18.2 ×
21.7 cm** (medido con orugas), no 21.8 × 18.5. Los huecos publicados salían 2 cm cortos
—corregidos— y **`robot_radius: 0.11` estaba mal**: el circunscrito real es 0.142. Corregido a
0.145.

✅ **El robot se midió entero el mismo día**
([`03_operacion/MEDIDAS_ROBOT.md`](03_operacion/MEDIDAS_ROBOT.md)), y salieron dos cosas más:

- 🔴 **El plano de barrido está 2 cm más bajo de lo documentado**: **15.5 cm**, no 17.45. La
  ficha del RVR daba 11.4 cm de alto y son **7.0**. El robot **ve mejor** de lo que decíamos.
- 🔴 **La inclinación de ~8° NO EXISTE** (ver abajo). Un problema abierto desde el principio,
  cerrado con una regla.

✅ **Y las paradas contra pared se repitieron con las cotas buenas**: **9.9 cm** a 0.25 m/s y
**10.6 / 10.7 cm** a 0.40 — a 1–2 mm del recálculo, y con 1 mm de dispersión entre las dos
corridas a 0.40. Ya no hay ningún número recalculado sin verificar.

✅ **Y la inclinación del RVR está resuelta**: no es el robot, es el **acelerómetro**, que da
`|g|` un 3.8 % corto y un error **fijo en el marco del robot**. Son **6.9° y viven en el PITCH**
(el roll es de 1°), no «~8° de roll» como decía la documentación. Costó **dos conclusiones mías
retiradas**; están explicadas en el **cap. 13** porque las dos son errores de método fáciles de
repetir.

⚠️ **El experimento de la deriva con y sin ese roll NO responde la pregunta**: el efecto buscado
era de ~1 cm y apareció el fallo de 12–56 cm que lo entierra.

✅ ~~Lo siguiente es el fallo bimodal a 2.3 m~~ — **cerrado el 2026-07-31** con
`referenciar_posicion.py`: 0 fallos de 12 y peor caso 4.4 cm.

🔴 **LO SIGUIENTE DE VERDAD, HOY: migrar el robot 2** →
[`03_operacion/FLOTA.md`, «Robot 2: instalación LIMPIA»](03_operacion/FLOTA.md). Levanta la
única suposición peligrosa que queda (`provision.sh` nunca se ha ejecutado entero), da el
segundo robot para el IR, y valida la imagen dorada antes de replicarla catorce veces.

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

## El SDK del RVR, explorado (2026-08-01) — 16 consultas de 62 métodos

De los 62 métodos que el driver no usaba se **probaron las 16 consultas** que podían aportar algo. Los otros 46 son **notificaciones** —cuyo estado es **NO VERIFICADO**, no «no emiten»: la de atasco **sí** llega— y modos de conducción alternativos que no hacen falta. Resumen para no repetirlo:

| | |
|---|---|
| ✅ **Batería con voltaje y umbrales del firmware** | implementado y verificado. `voltage` 8.28 V · umbrales **7.0 / 6.5 V** leídos del propio firmware. 🔴 **La web debe mirar `voltage`, no `percentage`**: el porcentaje decía 100 % a 1.29 V del umbral de «baja» |
| 🔴 **El atasco SÍ se detecta**, y dice **qué oruga** | 3 de 3 con el robot bloqueado. La conclusión anterior («las notificaciones no llegan») era **falsa**, y la causa es **el tiempo**: el ensayo original duró **3 s** y la detección tardó **~5 s** (⚠️ n=1, de un par de marcas del journal con resolución de 1 s: **5 ±2 s**, y a otra velocidad que el ensayo fallido). Y el RVR **enciende LEDs amarillos y rojos** por su cuenta |
| 🔴 **No hay rumbo absoluto** — limitación del hardware | `get_magnetometer_reading` da `bad_cid` y `magnetometer_calibrate_to_north` **no hace nada**. El firmware ya está en la última versión. **La pose inicial tendrá que venir del mapa o del operador** |
| 🔴 **No hay corriente de motores** | `bad_cid`. Ya no importa: el atasco se detecta por notificación |
| ⚠️ **Térmica y fallo: NO VERIFICADAS** | la prueba llegó a 40 °C y no podía disparar nada. No se persigue: el sondeo cada 30 s ya da el dato |
| 📚 **Documentación del protocolo rescatada** | `sdk.sphero.com` ya no existe. Copia en `00_auditoria/referencia_sdk/` |

⏳ **Lo único que queda necesita un segundo robot:** todo el **IR robot-a-robot**. Y el arreglo
de seguridad de `set_ir_evading` está verificado **por código**, nunca con un emisor delante.

📝 **Dos datos que la Fase 5 necesita saber:** un motor bloqueado sube **+11.1 °C en 90 s** de bloqueo (ritmo NO constante, 5→10 °C/min, n=1)
(sirve de corroboración de atasco), y **la temperatura publicada puede tener 30 s de retraso** —
una temperatura plana **no** significa «estable», puede ser el mismo dato repetido.

---

## Qué está roto y confirmado

| Problema | Gravedad | Estado |
|---|---|---|
| ~~El RVR se duerme solo y el driver no se entera~~ | seguridad operativa | ✅ **resuelto 2026-07-31**: timeout medido en **300.6 s**, keepalive cada 30 s + detector de silencio. 2 huecos → 0 |
| ~~La velocidad de `/odom` sale en el marco equivocado~~ | bloqueaba Nav2 | ✅ **resuelto 2026-07-31**: rotación −90° + proyección sobre el rumbo. **2 % de error** con el robot a 84° |
| ~~La posición y la orientación de `/odom` tienen manos contrarias~~ | bloqueaba Nav2 | ✅ **resuelto**: sobraba el `−Y`. Ahora giran igual (+89.87° vs +90.00°) |
| ~~El eje X del locator está 90° girado~~ | bloqueaba Nav2 | ✅ **resuelto**: `R(−90°)·(x,y) = (y,−x)` en `_h_locator` |
| 📝 `reset_yaw()` **no hace nada** — el yaw se pone a cero al **encender** el RVR | menor | ✅ **corregido**: el driver mide `yaw₀` al conectar y lo resta. Cinco arranques dieron cinco offsets distintos |
| ~~`inverted` del LIDAR sin verificar~~ | corrompe mapas | ✅ **verificado 2026-07-31**: `true` es CORRECTO. El equivocado era el yaw de `/odom` |
| ~~El robot está inclinado ~8°~~ | calidad de Nav2 | ✅ **resuelto 2026-07-31**: NO está inclinado. Las «tres vías» eran **una sola contada tres veces** (todas salen de la IMU). El acelerómetro crudo **no gira con el robot** y `\|g\|` sale 3.8 % corto → está **descalibrado**. El driver publica la orientación plana (`publicar_inclinacion: false`). Manual, cap. 13 |
| ~~La parada de emergencia de la web no hace nada~~ | seguridad | ✅ **resuelta 2026-07-31**. Había **tres** causas, no una: nombre, **namespace** (`/rvr/`) y **QoS** (`TRANSIENT_LOCAL` en el suscriptor no empareja con nadie). Verificada por los tres nombres, 0 avisos de QoS. Manual, cap. 15 |
| **Credencial del usuario `sphero` expuesta** en `Atriz_web_server` público, sin rotar | seguridad | 🔴 abierto — **acción del usuario**. Y no basta con rotarla: hay que quitarla del **historial** de git, no solo del último commit |
| ~~Sin arranque automático~~ | operación | ✅ **resuelto 2026-07-31**: `atriz-robot.service`, probado con un reinicio real. Falta que `provision.sh` lo instale |
| ~~La integración con el SDK NO está completa~~ | funcionalidad | ✅ **explorado el 2026-08-01**: el driver usa **37 de 99** métodos, y de los 62 restantes se probaron **las 16 consultas útiles** (evidencias 41–44); los otros 46 son notificaciones y modos de conducción alternativos. De lo que faltaba, **solo uno era aprovechable y ya está puesto** (voltaje de batería). 🔴 **El atasco SÍ se detecta** — la conclusión contraria era falsa. 🔴 **No hay rumbo absoluto**, cerrado con evidencia. ⏳ Queda el **IR**, que necesita un segundo robot |
| ~~No hay watchdog de `cmd_vel`~~ | seguridad | ✅ **resuelto**: para en 527 ms / 7.9 cm |
| ~~No hay URDF → árbol TF partido~~ | bloqueante | ✅ **resuelto**: `atriz_rvr_description` |
| ~~Driver ROS del LIDAR no instalado~~ | bloqueante | ✅ **resuelto**: `/scan` a 10.1 Hz |
| ~~Sin SLAM~~ | bloqueante | ✅ **Fase 4 CERRADA 2026-07-31**: el mapa crece al moverse (2367 → 3299 celdas) |
| ~~`imu.angular_velocity` en deg/s~~ | calidad de SLAM | ✅ **resuelto**: rad/s (REP-103) |

---

## 🔴 Prueba de aceptación en curso (2026-08-02) — F0 a F5 corriendo

Antes de abrir la Fase 5 se está construyendo una **prueba de aceptación de extremo a extremo**:
`scripts/prueba_aceptacion.py`, diez fases, de arranque en frío a navegación autónoma. Diseño en
[`03_operacion/PRUEBA_ACEPTACION.md`](03_operacion/PRUEBA_ACEPTACION.md).

**Última corrida: 12 PASA · 0 REVISAR · 0 FALLO.**

| Fase | Estado |
|---|---|
| F0 arranque en frío | ✅ 11 OK · **`Restart=always` ejercitado por primera vez** (PID 725→12608) |
| F1 telemetría | ✅ `/odom` 16.58 Hz · `/imu` 16.56 · 7.75 V · deriva de yaw **0.002°/30 s** |
| F2 LIDAR | ✅ arranca apagado · 11.81 Hz · 213/260 finitos · el parche del journal aguanta |
| F3 luces | ⏳ los servicios responden; **falta la confirmación visual de una persona** |
| F4 movimiento | ✅ 29.9 / 30.4 cm · **parada de emergencia en 1.5 cm** y rechaza `move_timed` |
| F5 **ángulos** | ✅ **90°→86.6° · 180°→179.6° · 360°→358.4°** · signo REP-103 · ⚠️ n=1. Evidencia 48 |
| F6 seguridad · F7 autónomo · F8 web · F9 | ⏳ pendientes |

⚠️ **La vía libre está BLOQUEADA**, y es lo acordado: los cuatro pendientes conocidos —empezando
por **rosbridge sin autenticación**— impiden decir «se puede empezar la web» aunque el robot esté
impecable.

🔴 **Cómo lanzarla:** el modo guiado **exige un terminal de verdad**. Ni el prefijo `!` de Claude
Code ni las herramientas de un agente dan TTY, y desde el 2026-08-02 la prueba **aborta con
código 2** en vez de mover el robot sin confirmación.

```bash
ssh sphero@rvr-01.local
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash && source ~/atriz_ws/install/setup.bash
python3 -u scripts/prueba_aceptacion.py            # entera, o --desde F4
```

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

### ✅ Hecho: Nav2 navega

| | Desde | Hasta | Resultado | Error |
|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.00, −0.03) | **SUCCEEDED** | **10 cm** |
| vuelta | (0.90, 0.00) | (0.00, 0.00) | **SUCCEEDED** | **9 cm** |

✅ El riesgo del QoS de `/scan` era **infundado**: tres suscriptores, todos BEST_EFFORT, y los
costmaps ven obstáculos de verdad (905 y 1983 celdas ocupadas).

🔴 **El primer objetivo abortó**, y no era la configuración: `Lookup would require extrapolation
into the future` en `odom → map`. Se comprobó antes de tocar nada — tolerancias puestas,
`use_sim_time` coherente, y `map → odom` a 50.0 Hz con **cero** huecos > 200 ms. Era el buffer
TF del controlador, aún sin llenar con los nodos recién arrancados. ⚠️ **Da unos segundos entre
activar Nav2 y el primer objetivo.**

### ✅ Hecho: la capa de seguridad

| Prueba | Resultado |
|---|---|
| parada contra pared a 0.25 m/s | **9.9 cm** de hueco |
| parada contra pared a 0.40 m/s | **10.6 / 10.7 cm** — más margen, no menos |
| escape pegado a la pared (1.1 cm) | retrocedió **196 cm** ✅ |
| LIDAR muerto, comandando 0.10 m/s | **0.0 cm** ✅ bloqueado |
| Nav2 con la seguridad en medio | **SUCCEEDED**, 9 cm de error |

🔴 **Dos hallazgos que no daban ningún error:**

1. **El `behavior_server` de Nav2 publicaba en `/cmd_vel`** — cinco publicadores, uno por
   conducta de recuperación (`spin`, `backup`…), saltándose el monitor. Y son justo las que se
   ejecutan cuando el robot está atascado, o sea pegado a algo. Salió de **contar
   publicadores**: salían seis donde debía haber uno. Arreglado.
2. **`approach` no es una parada de seguridad, es un frenado suave.** Con `radius: 0.11` el
   robot paró a **1.1 cm** de la pared: la asíntota del controlador es el contacto. La holgura
   se consigue **inflando el círculo** — `hueco ≈ radius − 0.091`.

🔴 **El límite que ninguna configuración arregla:** el plano del LIDAR está a **15.5 cm** del
suelo. Todo lo más bajo es **invisible** y el robot lo embestirá. Tiene que ir en las
instrucciones a los estudiantes.

### ✅ Hecho: navegando a 0.40 m/s

| | Desde | Hasta | Resultado | Error | v (p90) |
|---|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.50, 0.00) | **SUCCEEDED** | **8 cm** | 0.412 m/s |
| vuelta | (1.42, −0.01) | (0.00, 0.00) | **SUCCEEDED** | **8 cm** | 0.409 m/s |

Lo que había que comprobar no era que llegara, sino que **de verdad fuera a 0.40**: meseta de
**0.407 m/s** alcanzada en 0.9 s. Y subir la velocidad **no empeoró la precisión** — 8 cm
contra los 9–10 de antes.

Se subió con las tres condiciones medidas: dos navegaciones limpias a 0.25, el
`collision_monitor` verificado, y **a 0.40 la seguridad deja más hueco que a 0.25** (10.6 cm
contra 8.0). Ese último dato es el que quitaba el miedo.

🔴 **Y salió un fallo nuevo: `save_map` da 255 de forma intermitente.** No es el de la Fase 4
(`Package 'nav2_map_server' not found`): aquí el `map_saver` arranca y **se queda sin mapa**.
Es una carrera entre `map_update_interval: 5.0` y el `save_map_timeout: 2.0` del saver. Arreglo
propuesto en el manual 11.11, **sin verificar**.

### ✅ Hecho: rodea obstáculos

Objetivo a 1.50 m —el mismo que la corrida limpia, para que el obstáculo fuera la única
variable— con una caja de 16 cm a 0.75 m bloqueando la recta:

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

Rodea siempre por el lado con más hueco (63 cm por la derecha contra 44 por la izquierda), con
el mismo desvío. **Es repetible.**

🔴 **El hallazgo: la capa de seguridad hizo abortar a Nav2.** `Failed to make progress` → el
`SimpleProgressChecker` exige 0.5 m en 10 s (5 cm/s) y el `collision_monitor` había frenado al
40 %. **Con una capa de seguridad delante, ir despacio ya no es prueba de estar atascado.**
Relajado a 0.25 m en 15 s; tras el cambio, **cero abortos en cuatro navegaciones**.

✅ **Y `save_map` queda arreglado y verificado**: el servicio con su timeout de 2 s falla ~1 de
cada 3 (0, **255**, 0); `map_saver_cli` con `save_map_timeout:=10.0` funciona. Confirma que era
una carrera contra el `map_update_interval: 5.0`.

### ✅ Hecho: el paso de 40 cm, y las cotas corregidas

Con `radius: 0.18` **no cruza**. Y el compromiso queda cuantificado:

| `radius` | para a | pasillo mínimo |
|---|---|---|
| 0.14 | 5 cm | 28 cm |
| **0.18** | **9 cm** | **36 cm** ← el actual |
| 0.20 | 11 cm | 40 cm |

Para 16 robots en un laboratorio remoto **donde nadie puede levantarlos**, parar a 9–11 cm de
las paredes vale más que cruzar huecos de 40 cm — pero es una **decisión de laboratorio**.

**Corregido:** URDF a 18 × 22 cm y `robot_radius` 0.11 → **0.145**. Ningún frame TF se mueve.

⚠️ **Retirado:** intenté medir el mismo paso con `radius: 0.15` para dar la curva completa, y
el buscador eligió **otro hueco** (33.9 cm, a −61.5° de rumbo). Cruzó *un* hueco, no *el*
hueco. No cuenta.

### ✅ Hecho: el robot medido entero

| Cota | Medido | Antes |
|---|---|---|
| frente-atrás | **18.2 cm** | 21.8 (ficha, cruzado) |
| lado a lado | **21.7 cm** | 18.5 (ficha, cruzado) |
| suelo → tapa | **7.0 cm** | 11.4 (ficha) |
| **suelo → centro del disco (`laser_z`)** | **15.5 cm** | 17.45 (derivado) |
| ancho de oruga | **3.5 cm** | 2.5 (ficha) |
| `wheel_separation` (entre centros) | **18.3 cm** | 15.0 (ficha) |
| `wheel_radius` (suelo → eje) | **3.5 cm** | 3.2 (ficha) |

✅ **Cierra por dos caminos independientes**: `14.8 + 2 × 3.5 = 21.8 ≈ 21.7` de ancho, y
`wheel_radius 3.5` da una oruga de 7 cm de diámetro = `base_height`, así que la caja del chasis
va del suelo a 7 cm — justo como se ve el RVR.

✅ **El modelo geométrico está completo.** Solo falta `imu_z`, que exige abrir el robot y hoy
no afecta a nada. El LIDAR está confirmado **centrado y nivelado**.

### ✅ Hecho: referenciar la posición, y con eso los fallos desaparecen

El problema no era de SLAM: era del banco de pruebas. Las herramientas repetían N corridas
dando por hecho que el robot volvía al punto de partida, y **no volvía**.

`referenciar_posicion.py` ajusta una recta a la pared frontal, conduce a la distancia objetivo y
**luego** se alinea (ese orden importa: al revés, conducir vuelve a torcer el rumbo).

| | sin referenciar | con referenciar |
|---|---|---|
| dispersión de posición, adelante | 0.47 m | **0.06 m** |
| dispersión lateral | 0.81 m | **0.03 m** |
| fallos > 5 cm | **5 de 24** | **0 de 12** |
| peor caso | **56.1 cm** | **4.4 cm** |

⚠️ **Fisher exacto de 0/12 contra 5/24 da p = 0.113**: sugerente, no concluyente al 5 %. Lo
indiscutible es la dispersión de posición; que los fallos se vayan a la vez es coherente pero
pide otra tanda para cerrarlo.

### ✅ Decidido: no se persigue el roll — y el driver deja de publicarlo

Con el ruido bajado, las dos distancias apuntaban en el mismo sentido (CORTA +1.30 cm, LARGA
+1.40) con la magnitud predicha, pero **p = 0.142** con n=6 por rama. Cerrarlo costaría **~62
corridas y 5.2 horas de robot** para un efecto de ~1 cm sobre una tolerancia de **10 cm**.
**Decisión del usuario el 2026-07-31: no se persigue.**

🔴 **Pero eso no deja el roll publicado.** `publicar_inclinacion` pasa a **`false` por
defecto**, y la razón **no depende** de la medida que no se va a hacer: la inclinación **es
falsa** (suelo plano con nivel, error del acelerómetro fijo en el marco del robot, `|g|` un
3.8 % corto). Publicar 6.9° que no existen en `odom → base_footprint` es publicar un dato
incorrecto. Verificado: `/odom` da `roll +0.00° pitch +0.00°`.

### ✅ Hecho: Fase 4c — `map_server` + AMCL

El ciclo completo funciona: **mapear → guardar → localizar → navegar** sobre el mapa, sin SLAM.

```
mapear con slam_toolbox      celdas 486 → 2774
guardar con map_saver_cli    mapa_amcl.pgm
parar SLAM                   `map` deja de existir  ✅
localizar                    map_server y amcl active [3]
seguir la pose               ODOM 61.8 cm · AMCL 61.9 · dif 0.1 cm
navegar con Nav2             SUCCEEDED, error 8 cm · dif ODOM/AMCL 1.1 cm
```

✅ **Y el launch se niega a arrancar** si `slam_toolbox` está vivo o si el mapa no existe — las
dos probadas. Los dos publican `map → odom` y juntos parten el árbol TF **sin dar error**.

🔴 **AMCL cuesta casi el doble que SLAM** (8.8 % contra 4.8 %), al revés de lo que suponía.
**El argumento para AMCL es el marco compartido, no el coste.**

⚠️ **Sin resolver:** la σyaw sube a **18°** navegando (mapa pequeño y poco distintivo, sin
comprobar), y **la pose inicial tendrá que venir por robot** para la flota. Manual, **cap. 14**.

### ✅ Hecho: la parada de emergencia, que fallaba por TRES causas

Falló tres veces y siempre en silencio, con `200 OK` en la web: **nombre** de topic (ROS 1),
**namespace** `/rvr/` (al portar), y **QoS** — el driver se suscribía `TRANSIENT_LOCAL`, que en
un suscriptor **solo restringe** y no empareja con ningún publicador por defecto.

Verificada disparando los tres nombres: **3 paradas, 3 liberaciones, 0 avisos de QoS**.
Manual, **cap. 15**.

✅ ~~Pero no corta lo que venga de Nav2~~ — **FALSO, y ya estaba arreglado cuando se escribió
esto.** El nodo `cancelar_nav2` manda `CANCEL_ALL` a `NavigateToPose`. Verificado con control:
objetivo `CANCELED` y **0.0 cm** al liberar la parada; sin él, objetivo **ACTIVO** y el robot
**arrancó solo 34.7 cm** (manual, cap. 15.4).

🔴 Es la **tercera** vez que esta misma frase sobrevive en un fichero distinto tras corregirla.
Es el caso que `CLAUDE.md` usa como ejemplo canónico de deriva documental — **una función de
seguridad descrita como rota cuando funciona**.

### ✅ Hecho: los servicios del driver, de 1 a 18

Todos **probados contra el robot**, y en orden de riesgo: primero lo que no mueve nada.

```
move_timed  2 s a 0.15 m/s   ->  30.3 cm medidos contra 30   (101 %)
raw_motors  reversa 25 %     ->  30.7 cm, para al mandar modo 0
move_to_pos_and_yaw 0.20 m   ->  19.5 cm                     ( 97 %)
con la parada de emergencia  ->  success=False, 0.0 cm       ✅
```

🔴 **Y destapó que `/color` publicaba `[0,0,0]` desde siempre.** El sensor no da nada sin su
luz —canal claro **4 apagada contra 741 encendida**, 185×— y el driver **nunca la encendía**.
El topic estaba en la lista de «verificado». Arreglado con el parámetro `color_detection`
(por defecto `false`, porque enciende un LED bajo el chasis).

🔴 Y **no se puede encender bajo demanda**: con el streaming ya configurado,
`enable_color_detection` no hace nada. Hay que encenderlo **antes**.

⚠️ **Los servicios de movimiento se saltan el `collision_monitor` y el watchdog** — hablan al
RVR por el puerto serie, no por un topic. Solo los para la parada de emergencia. Manual,
**cap. 16**.

### ✅ Hecho: `provision.sh` y `verificar_robot.sh` al día

🔴 **`provision.sh` nunca instalaba `navigation2`.** Un robot aprovisionado con el script tenía
driver, LIDAR y SLAM — y **no podía navegar, ni tenía capa de seguridad, ni localización**.
Añadido, comprobando además que los binarios existan y que no entre el simulador.

**`verificar_robot.sh` pasa de 50 a 84 comprobaciones** (con `--hardware`, y esa misma tarde a **91**): los binarios de
Nav2, los 9 ficheros de config y launch, los **valores medidos** (`robot_radius` 0.145, URDF
0.182 × 0.217, `laser_z` 0.155), los valores **por defecto que son decisiones**
(`publicar_inclinacion` y `color_detection` en `false`, la parada en VOLATILE), y los **18
servicios preguntando a un cliente** — no a `ros2 service list`, que miente por omisión.

🔴 **Y el verificador tenía tres fallos propios** —esa misma tarde salieron **tres más**, van seis (evidencia 32)—, encontrados al ejecutarlo: comprobaba el
driver de **ROS 1**, contaba un **comentario** como si fuera un ajuste, y daba el LIDAR por roto
cuando el driver tenía el puerto ocupado. Los tres corregidos.

```
sin --hardware   76 correctas · 1 aviso · 0 fallos
con --hardware   105 correctas · 0 fallos   (2026-08-01)
```

### ✅ Dos decisiones CERRADAS el 2026-08-01 (eran los últimos bloqueos de la Fase 5)

Las dos las destapó alinear `ARQUITECTURA.md` con el robot real, y las dos afectan al cliente
web: cambiarlas después obligaría a tocar los 16 robots **y** el cliente a la vez.

**1. ✅ SIN NAMESPACE.** Los topics son `/odom`, no `/rvr_01/odom`.

- El **`ROS_DOMAIN_ID` por robot** ya da aislamiento DDS **total** — los robots no se ven entre sí
  ni queriendo. El namespace resolvería un problema que no existe.
- La web habla por **un WebSocket por robot** (`ws://rvr-07.local:9090`). Poner `/rvr_07/odom`
  dentro de un canal que solo alcanza al robot 7 es escribir el número dos veces.
- 🔴 **Y la parada de emergencia ya falló una vez POR UN NAMESPACE**: al portar de ROS 1 se coló
  un `/rvr/` y falló en silencio con `200 OK`. Van cuatro fallos de la parada; no se le regala el
  quinto multiplicado por 16.

⚠️ Un namespace **no renombra los `frame_id` de TF**, así que ni siquiera resuelve el caso para el
que suele invocarse. El argumento `namespace` de los launch se deja como camino de escape — y al
cerrar esto se descubrió que **ese camino estaba roto**: dos `frame_id` a fuego en el driver, ya
convertidos en el parámetro `body_frame`.

**2. ✅ EL OFICIAL ES `/emergency_stop`**, con QoS **RELIABLE + VOLATILE** (`TRANSIENT_LOCAL` fue
la tercera causa de fallo, y rosbridge no lo es).

El driver **sigue escuchando los tres** y eso no se toca: con un botón de emergencia el modo de
fallo que importa es «el mensaje no llega». Escuchar de más no cuesta nada.

### 📌 El tercer repositorio: `Atriz_web_server`

**No está clonado en este robot ni se ha tocado**, a propósito: la web es la Fase 5 y es un
repositorio **público con una credencial expuesta**.

Lo que le afecta de todo lo hecho está recogido en
`00_auditoria/evidencia_24_04/28_pendiente_web.txt`, para que quien abra la Fase 5 no tenga que
reconstruirlo. En resumen:

- ✅ **La parada de emergencia ya funciona sin tocar la web**: el driver escucha
  `/rvr/emergency_stop` con el QoS que usa rosbridge, y desde el 2026-07-31 **también cancela
  los objetivos de Nav2** — antes, al *liberarla*, el robot arrancaba solo (34.7 cm medidos).
- 🔴 **NUEVO Y OBLIGATORIO: la web tendrá que llamar a `/start_scan` al empezar una sesión.**
  Los robots arrancan solos pero con el barrido del lidar **parado**, y sin `/scan` el
  `collision_monitor` bloquea el movimiento. Un robot recién encendido **no obedece `cmd_vel`**,
  y desde la web se verá igual que uno averiado.
- 📝 La web ya **no tiene que arrancar nada por SSH**: `atriz-robot.service` lo hace, y se
  recupera solo de un reinicio (probado).
- La web puede usar ya **18 servicios y 5 topics**. 🔴 Con dos avisos: los servicios de
  movimiento **se saltan la capa de seguridad**, y hay que publicar en **`/cmd_vel_raw`**, no en
  `/cmd_vel`.
- 📝 `/color` publica `[0,0,0]` salvo que se arranque con `color_detection:=true`.
- 🔴 La **credencial sigue expuesta**, y quitarla exige limpiar el **historial** de git.

### 🔴 Suposición aceptada: `provision.sh` no se ha probado entero

**Decisión del usuario el 2026-07-31: no se reflashea rvr-01.** Es el único robot montado y
probar el script de principio a fin exigiría un 24.04 limpio. Se **asume** que funciona hasta
tener una tarjeta de repuesto.

✅ **Verificado:** sintaxis, una pasada con `--simular` (código 0 recorriendo las nueve
secciones), la comprobación de los cuatro binarios de Nav2 —que **no** se simula— y la
idempotencia.

🔴 **Sin verificar, y es lo que importa:** la simulación convierte en no-operación **justo lo
que instala y compila** — el `full-upgrade`, el arreglo del UART, la higiene del SO, el
`apt install`, compilar YDLidar-SDK y el `colcon build`. De una pasada limpia **no se ha probado
nada**.

⚠️ **No construyas la imagen dorada sin levantar esto.** El riesgo no es que falle: es que falle
**en el robot 7 de 16**, con seis ya desplegados.
Detalle: `00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.

### 1. ✅ Las unidades systemd — FUNCIONANDO, probadas con un reinicio

✅ Instalado, habilitado y **arrancado** el 2026-07-31, comprobado por efecto: `ExecStartPost`
`status=0/SUCCESS`, `/scan` a **0.00 Hz** (barrido parado), `/odom` a **16.54 Hz** y `/cmd_vel`
con un solo publicador.

✅ **Y probado con un reinicio de verdad:** volvió solo (PID 711), `/scan` a 0.00 Hz, `/odom` a
16.49, y el robot **bloqueado sin barrido** — 0.0 cm contra 9.9 del control.

📝 Sin ejercitar: la espera de puertos del envoltorio (siempre `tras 0s`) y `Restart=always`.
Son redes de seguridad sin estrenar. Evidencia 33.

✅ **`provision.sh` YA lo instala** (paso 8/9), desde el 2026-08-01. Era un requisito para la
imagen dorada: construirla antes habría dado 16 robots sin arranque automático. Manual, cap. 17.

🔴 **Y tiene que arrancar con el lidar PARADO.** Medido el 2026-07-31: el X2 gira siempre, a
2.7 Hz en reposo y 11.8 Hz escaneando. Hoy se queda en 2.7 porque no hay nada corriendo; en
cuanto los 16 robots levanten `robot.launch.py` solos, pasará a **11.8 Hz permanentes, 24/7, en
los 16**. Sería peor que ahora, y llegaría como efecto secundario de una tarea que no habla de
lidares.

El driver ya trae `/stop_scan` y `/start_scan` (verificados, y frenan el motor de verdad), así
que basta con arrancar parado y activar al empezar la sesión. La seguridad encaja sola: sin
`/scan` el `collision_monitor` no deja conducir. Manual, cap. 8.4a.

Todo lo de hoy —`collision_monitor`, localización con AMCL, URDF corregido,
`publicar_inclinacion`, `color_detection`, `robot_radius`, los 18 servicios— **tiene que estar
en el script de aprovisionamiento y en el verificador**, o la imagen dorada no lo tendrá. Es la
regla del propio proyecto: *la imagen dorada es el atajo, `provision.sh` es la verdad*.

✅ **Ya hecho:** las unidades **systemd** de arranque automático están instaladas, probadas con
un reinicio real, y `provision.sh` las instala (paso 8/9). Quedan sin
portar `ConfigureStreaming` y `StartStreaming` —a propósito: pueden romper la telemetría del
propio driver.

📌 **Aplazado hasta tener el circuito definitivo:** mapear el laboratorio real y la pose inicial
por robot.

### ✅ Hecho: las paradas re-medidas

| velocidad | n | **medido** | recalculado | dif |
|---|---|---|---|---|
| 0.25 m/s | 1 | **9.9 cm** | 9.8 | +0.1 |
| 0.40 m/s | 2 | **10.6 / 10.7 cm** | 10.8 | −0.2 |

El modelo afinado: asíntota `0.18 − 0.091 = 8.9 cm`, y el margen sobre ella **crece con la
velocidad** (+1.0 cm a 0.25, +1.8 a 0.40). La holgura **no se degrada al acelerar: mejora**.

📝 Cambiar `laser_z` y `wheel_radius` **no alteró el comportamiento**, como se preveía: son
traslaciones en Z y el monitor trabaja en el plano.

### ✅ ~~Cargar el robot y medir la deriva con y sin el roll~~ — CERRADO, no se persigue

El interruptor ya está: `robot.launch.py publicar_inclinacion:=false`. Lo que falta es
ejecutar **12 corridas** de `caracterizar_deriva_slam.py`, 6 por condición.

**El diseño, y por qué no se puede recortar:**

- 🔴 **La línea base anterior no vale.** Se hizo con `laser_z = 0.1745`, y el desplazamiento
  lateral que induce el roll escala con esa altura: 2.4 cm entonces, **2.2 cm ahora**.
- 🔴 **Las condiciones se ALTERNAN**, no 6 y 6. Así un corte por batería deja datos
  **balanceados**, y el nivel de carga deja de poder colarse como variable.
- ⚠️ **No se puede bajar a 2 por condición.** El efecto buscado es de ~**1 cm** y la dispersión
  ya medida es **σ = 0.6–1.0 cm**: saldría dentro del ruido.

⏳ Y falta un dato que el proyecto no tiene y hará falta con 16 robots: **cuánto consume el RVR
por minuto conduciendo**. Es lo que impide saber si un 34 % aguanta 40 min.

Después: el **barrido de `radius`** contra un mismo paso estrecho.

### 2. ✅ RESUELTO: la inclinación de ~8° no existe

El usuario midió del suelo al disco del LIDAR **en cuatro puntos** y salen **iguales**. 8°
habrían dado ~1.1 cm de diferencia sobre los 7.6 cm del disco: se habrían visto. **El robot
está físicamente horizontal.**

Y las «tres vías independientes» **no eran independientes**: el árbol TF sale de
`odom.pose.pose.orientation`, que el driver copia del cuaternión del RVR, que calcula la IMU —
y el acelerómetro es el mismo chip. **Una sola fuente contada tres veces.** El TF no
confirmaba: repetía.

✅ **YA APLICADO** (2026-07-31): `publicar_inclinacion` es `false` por defecto y `/odom` sale
con `roll +0.00° pitch +0.00°`. ⚠️ Y no eran «~8° de roll»: son **6.9° y están en el PITCH**.
Texto original: el driver publica un roll falso de ~8° en `/odom` y en TF. Eso
inclina el plano del láser y comprime los alcances un **1 %** (~1 cm por metro) — y la deriva
de SLAM medida es de **1–3 cm**. El orden de magnitud coincide: **podría ser parte de ella**.
La corrección es una línea y **no se aplica sin medirla**. Manual, **cap. 13**.

<details><summary>Lo que decía antes de resolverse</summary>

### 🔴 La inclinación de ~8°, confirmada por TRES vías

Árbol TF, `Roll` de la IMU y el acelerómetro con unidades correctas. Causa sin determinar.

📝 La caracterización de la deriva **acota su gravedad**: con la inclinación presente, la
deriva es de 2.7 cm, así que no está arruinando el emparejado. Hay que resolverla para Nav2
—por REP-105 `odom → base_footprint` debería ser plana— pero **no es urgente**.

</details>

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

> ⚠️ **Ese 17.45 también resultó estar mal**, y por lo mismo: era una **suma derivada** con el
> alto del RVR sacado de su ficha (11.4 cm cuando son **7.0**). Medido con regla el 2026-07-31,
> el plano de barrido está a **15.5 cm**. Manual, cap. 12.8.

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
4. ✅ ~~Watchdog de `cmd_vel` — hoy no existe~~ — **existía ya en ROS 1** y sigue en el port:
   `cmd_vel_timeout` = **0.3 s**, medido en **527 ms / 7.9 cm**. Este párrafo cita el plan de la
   Fase 2, que estaba equivocado. Texto original: si cae la red, el robot sigue
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
medir_ritmo_ros2.py  # frecuencia y jitter de /odom, /imu y /scan
#                     ⚠️ medir.py es de ROS 1 y YA NO ARRANCA
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
