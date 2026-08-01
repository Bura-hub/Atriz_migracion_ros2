> 🔴 **El piso del LIDAR es BLANCO, y eso tiene una consecuencia medida.** Los 4.6 cm de piso
> adicional sobre la tapa del RVR reflejan la luz de los LEDs del robot sobre el **sensor de luz
> ambiente**, que mira hacia arriba: encenderlos todos sube la lectura **13.3×**.
> → Por eso **`/ambient_light` no sirve en este montaje** y no se usa. Manual, cap. 18.4b.

# Qué medir en el robot — y qué cambia cada cota

> Creado el **2026-07-31**, después de descubrir que el URDF tenía el **largo y el ancho
> cruzados**: modelaba un robot de 21.8 × 18.5 cm cuando el real mide **18.2 × 21.7**. Venía de
> la ficha publicada del RVR y estaba declarado «NO MEDIDO» desde el principio.
>
> ✅ **Medido entero el mismo día. No queda ninguna cota medible sin medir** — solo `imu_z`,
> que exige abrir el robot y hoy no afecta a nada. El repaso destapó **tres cosas**, y la
> tercera cierra un problema abierto:
>
> 1. la ficha del RVR daba **11.4 cm de alto** y son **7.0** — 4.4 de más;
> 2. por eso `laser_z` estaba **2 cm alto**: el robot ve más abajo de lo documentado;
> 3. 🔴 y el LIDAR está **nivelado en los cuatro puntos**, así que la «inclinación de ~8°» del
>    robot **no existe**: es un desvío de la IMU (manual, cap. 13).
>
> Este documento lista **todas** las cotas que el modelo usa, cuáles están medidas y cuáles no,
> y **qué se rompe si cada una está mal**.

**Herramienta:** una regla o cinta métrica, y el robot **apagado y sobre suelo plano**.

---

## Antes de nada: ¿qué es `wheel_separation`?

Es la **distancia entre los centros de las dos orugas**, medida de lado a lado.

En un robot diferencial normal de ROS es **el parámetro más crítico del modelo**: es lo que
convierte velocidades de rueda en giro,

```
velocidad angular = (v_derecha − v_izquierda) / wheel_separation
```

Si te equivocas un 10 %, el robot gira un 10 % de más o de menos y la odometría se va.

**🔴 Aquí no hace nada de eso.** El RVR resuelve su propia cinemática: el driver le manda
velocidad lineal y angular ya hechas (`drive_rc_si_units`) y la pose viene del **locator
interno** del robot. En este proyecto `wheel_separation` **solo sirve para dibujar las orugas
en su sitio en RViz**.

✅ **RESUELTO el 2026-07-31.** Estaba inconsistente y la cinta lo explicó: las orugas son de
**3.5 cm** de ancho (no 2.5) y van de **borde interno a borde interno a 14.8 cm**.

```
entre centros  =  14.8 + 3.5           =  18.3 cm   -> wheel_separation 0.183
de borde a borde =  14.8 + 2 × 3.5     =  21.8 cm   ≈  21.7 medidos de lado a lado  ✅
```

**Las orugas ocupan todo el ancho del robot.** Los 4.5 cm que faltaban eran los dos anchos de
oruga mal puestos.

---

## GRUPO A — Las que cambian los resultados de las pruebas

Estas tres son las que hay que medir **antes de repetir nada**.

### A1 · ✅ `laser_z` — del SUELO al centro del disco giratorio: **15.5 cm**

| | |
|---|---|
| Valor **medido** | **0.155 m** ✅ 2026-07-31 |
| Valor anterior | 0.1745 m — derivado, y **2 cm de más** |

La cadena completa, medida:

```
suelo → tapa del RVR                 7.0 cm   ✅   (la ficha decía 11.4: 4.4 de más)
tapa  → base del LIDAR (piso extra)  4.6 cm   ✅
base del LIDAR → centro del disco    3.9 cm
────────────────────────────────────────────
suelo → CENTRO DEL DISCO            15.5 cm   ✅
suelo → extremo superior            16.5 cm   ✅
```

Comprobación cruzada: `7.0 + 4.6 + 5.0` (alto del LIDAR) `= 16.6 ≈ 16.5`. ✅ Cierra.

🔴 **El robot ve 2 cm más abajo de lo documentado.** El límite «por debajo de X cm el LIDAR no
ve nada» pasa de **17.45 a 15.5 cm**.

📝 Un error en `laser_z` es una **traslación pura en Z**: no inclina nada, así que **no afecta
a SLAM 2D ni a Nav2**, que trabajan en el plano. Afecta a la visualización y a ese límite.

### A2 · ✅ El LIDAR está NIVELADO — y eso resuelve la inclinación de ~8°

Medido el 2026-07-31: el disco está a la **misma altura en los cuatro puntos** (delante,
detrás, izquierda, derecha). 8° habrían dado ~1.1 cm de diferencia sobre los 7.6 cm del disco:
se habrían visto.

🔴 **Conclusión: el robot está físicamente horizontal, y los ~8° son un desvío de la IMU.**

Y las «tres vías independientes» que confirmaban la inclinación **no eran independientes**:

| «vía» | de dónde sale de verdad |
|---|---|
| árbol TF | de `odom.pose.pose.orientation`, que el driver copia del… |
| cuaternión del RVR | …que calcula la **IMU** |
| acelerómetro | el **mismo chip** |

Una sola fuente contada tres veces. Detalle en el manual, **cap. 13**.

### A3 · ✅ `base_height` — del suelo a la tapa del RVR: **7.0 cm**

La ficha decía 11.4 cm: **4.4 cm de más**. Es el error que arrastraba `laser_z`.

---

## GRUPO B — Cambian el modelo, no los números ya medidos

Merecen la pena porque el modelo se usa para RViz y para la caja de colisión, pero **no
invalidan ninguna prueba** de las hechas.

### B1 · ✅ `wheel_radius` — del suelo al centro del eje: **3.5 cm**

La ficha decía 3.2. Es lo que separa `base_footprint` (el suelo) de `base_link`.

✅ **Y cierra el modelo por un segundo camino:** `wheel_radius 0.035` da una oruga de **7.0 cm
de diámetro**, que es exactamente `base_height`. Con eso la caja del chasis va **del suelo a
7 cm** — justo como se ve el RVR, con las orugas ocupando todo el alto del lateral. Dos
medidas independientes que concuerdan.

### B2 · ✅ `wheel_separation` — entre centros: **18.3 cm**

`14.8` (borde interno a borde interno) `+ 3.5` (un ancho de oruga) `= 18.3 cm`.

### B3 · ✅ `wheel_width` — ancho de una oruga: **3.5 cm**

### B4 · `imu_z` — altura de la IMU dentro del RVR

Actual **0.05 m**, y es una suposición. No se puede medir sin abrir el robot, y **hoy no
afecta a nada**: la IMU no se fusiona con la odometría. Se deja como está y se anota.

---

## GRUPO C — Ya medidas, no hace falta tocarlas

| Cota | Valor | Cuándo |
|---|---|---|
| `base_length` (frente-atrás) | **0.182 m** | 2026-07-31, con orugas |
| `base_width` (lado-lado) | **0.217 m** | 2026-07-31, con orugas |
| `base_height` (suelo → tapa) | **0.070 m** | 2026-07-31 |
| `laser_z` (suelo → centro del disco) | **0.155 m** | 2026-07-31 |
| `laser_gap` (tapa → base del LIDAR) | **0.046 m** | 2026-07-31 |
| `x2_height` (alto del LIDAR) | **0.050 m** | 2026-07-31 |
| `wheel_separation` (entre centros) | **0.183 m** | 2026-07-31 |
| `wheel_width` | **0.035 m** | 2026-07-31 |
| `laser_x`, `laser_y` | **0, 0** — centrado | 2026-07-30 |
| `wheel_radius` (suelo → centro del eje) | **0.035 m** | 2026-07-31 |
| nivelación del LIDAR | **igual en los 4 puntos** | 2026-07-31 |
| centrado del LIDAR | **confirmado** con las cotas nuevas | 2026-07-31 |

**Derivados de lo anterior:**

```
media longitud      0.091 m     -> hueco al parar ≈ radius − 0.091
media anchura       0.1085 m
radio inscrito      0.091 m
radio circunscrito  0.142 m     -> robot_radius: 0.145   ✅ ya puesto
```

✅ **El modelo cierra por dos caminos independientes:**

```
caja del chasis  →  de 0.000 a 0.070 m sobre el suelo   (= base_height, exacto)
plano del láser  →  0.155 m sobre el suelo              (= laser_z medido, exacto)
orugas           →  0.148 + 2 × 0.035 = 0.218 ≈ 0.217 de ancho total
```

---

## Lo que NO hace falta medir

No lo midas, ya está resuelto y por vías mejores que una regla:

- **La odometría.** La da el locator interno del RVR. Verificada: 1 mm de error en 1 m.
- **Las velocidades máximas.** Medidas: 0.40 m/s y 2.0 rad/s, con meseta al 100 %.
- **La rampa de aceleración.** Medida: ~0.5 s.
- **La distancia de frenado.** Medida con el `collision_monitor` en el lazo.

---

## Qué se puede repetir con cada medida

### ✅ No falta nada medible

Solo `imu_z` (0.05, suposición), que exige abrir el robot y hoy no afecta a nada: la IMU no se
fusiona con la odometría. **El modelo geométrico del robot está completo y verificado.**

### ⏳ Lo que hay que REPETIR ahora que las cotas son buenas

1. ✅ ~~**Las paradas contra pared**~~ — **hechas** el 2026-07-31 con las cotas buenas:
   **9.9 cm** a 0.25 m/s y **10.6 / 10.7 cm** a 0.40 (dos corridas). A 1–2 mm del recálculo, así
   que el recálculo era correcto. Manual, cap. 12.4.
2. **El barrido de `radius`** (0.14 / 0.16 / 0.18) contra un mismo paso estrecho, fijando el
   hueco para que el buscador no elija otro — daría la curva completa del compromiso entre
   «parar lejos de las paredes» y «cruzar huecos estrechos».
3. 🔴 **La deriva de SLAM con y sin el roll de la IMU.** Si el robot está horizontal, el roll de
   ~8° que el driver publica en TF es falso, e inclina el plano del láser: comprime los alcances
   por `cos(8°) = 0.990`, un **1 %**, ~1 cm por metro. Cabe dentro de la deriva medida (1–3 cm),
   así que **podría ser parte de ella**. La corrección sería `roll = pitch = 0.0` en
   `_h_quaternion`, y **no se aplica sin medirla antes**.
