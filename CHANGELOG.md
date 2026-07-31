# Bitácora

Una entrada por sesión de trabajo. Formato: qué se hizo, qué se verificó, qué quedó pendiente.

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
