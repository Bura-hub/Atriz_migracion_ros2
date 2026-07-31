# Qué medir en el robot — y qué cambia cada cota

> Creado el **2026-07-31**, después de descubrir que el URDF tenía el **largo y el ancho
> cruzados**: modelaba un robot de 21.8 × 18.5 cm cuando el real mide **18 × 22**. Venía de la
> ficha publicada del RVR y estaba declarado «NO MEDIDO» desde el principio.
>
> Este documento existe para que eso no vuelva a pasar por sorpresa: lista **todas** las cotas
> que el modelo usa, cuáles están medidas y cuáles no, y **qué se rompe si cada una está mal**.

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

⚠️ Pero está **inconsistente**, y eso es una señal de que algo del modelo no cuadra:

```
wheel_separation 0.150 + wheel_width 0.025  =  17.5 cm de oruga a oruga
robot medido                                =  22.0 cm de lado a lado
```

Sobran 4.5 cm sin explicar. O la separación está corta, o el cuerpo del RVR sobresale de las
orugas. **Merece una cinta encima.**

---

## GRUPO A — Las que cambian los resultados de las pruebas

Estas tres son las que hay que medir **antes de repetir nada**.

### A1 · `laser_z` — del SUELO al centro del disco giratorio del LIDAR

| | |
|---|---|
| Valor actual | **0.1745 m** — ⚠️ **DERIVADO, no medido** |
| De dónde sale | `base_height 0.114` (ficha, sin medir) + `laser_gap 0.040` (✅ medido) + `x2_height/2 0.0205` (ficha) |
| Cómo medirlo | Regla apoyada en el suelo, hasta la **mitad del disco que gira** (no la tapa, no la base) |

**Es la cota más importante del robot**, porque decide **a qué altura ve**. Todo el límite
«por debajo de X cm el robot no ve nada y lo embiste» sale de aquí. Si son 15 cm y no 17.45,
la lista de cosas invisibles cambia.

Dos de los tres sumandos vienen de fichas de fabricante. **Mídelo directo y nos ahorramos la
suma entera.**

### A2 · ¿Está el LIDAR NIVELADO? — cuatro medidas alrededor del disco

| | |
|---|---|
| Valor actual | se supone perfectamente horizontal (`rpy="0 0 0"` en el URDF) |
| Cómo medirlo | Del suelo al **borde inferior del disco** en cuatro puntos: delante, detrás, izquierda, derecha |

🔴 **Es la mejor pista que tenemos sobre la inclinación de ~8°**, que lleva abierta desde el
2026-07-31 confirmada por tres vías (árbol TF, Roll de la IMU y acelerómetro) y sin causa.

Si las cuatro medidas no coinciden, el LIDAR está torcido y sabremos **cuánto y hacia dónde**.
El disco del X2 mide unos 7.6 cm de diámetro, así que **8° serían ~1.1 cm de diferencia entre
un lado y el otro** — se ve con una regla normal.

Si las cuatro coinciden, la inclinación no es del LIDAR y hay que buscarla en el chasis.

### A3 · `base_height` — del suelo a la tapa del RVR

| | |
|---|---|
| Valor actual | **0.114 m** — 📝 ficha del RVR, sin medir |
| Cómo medirlo | Del suelo a la superficie plana de arriba, donde se apoya el LIDAR |

Sirve de **comprobación cruzada de A1**: `A3 + 4.0 cm + 2.05 cm` debería dar A1. Si no cuadra,
una de las dos está mal y conviene saber cuál.

---

## GRUPO B — Cambian el modelo, no los números ya medidos

Merecen la pena porque el modelo se usa para RViz y para la caja de colisión, pero **no
invalidan ninguna prueba** de las hechas.

### B1 · `wheel_radius` — del suelo al centro del eje de la oruga

Actual **0.032 m**, sin medir. Es lo que separa `base_footprint` (el suelo) de `base_link`.
Mide del suelo al **centro del eje** de la rueda motriz.

### B2 · `wheel_separation` — entre los centros de las dos orugas

Actual **0.150 m**, sin medir, y es la que no cuadra (ver arriba). Mide del **centro de una
oruga al centro de la otra**.

### B3 · `wheel_width` — ancho de una oruga

Actual **0.025 m**, sin medir. De borde a borde de la banda de goma.

### B4 · `imu_z` — altura de la IMU dentro del RVR

Actual **0.05 m**, y es una suposición. No se puede medir sin abrir el robot, y **hoy no
afecta a nada**: la IMU no se fusiona con la odometría. Se deja como está y se anota.

---

## GRUPO C — Ya medidas, no hace falta tocarlas

| Cota | Valor | Cuándo |
|---|---|---|
| `base_length` (frente-atrás) | **0.18 m** | 2026-07-31, con orugas |
| `base_width` (lado-lado) | **0.22 m** | 2026-07-31, con orugas |
| `laser_x`, `laser_y` | **0, 0** — centrado | 2026-07-30 |
| `laser_gap` (tapa → base del LIDAR) | **0.040 m** | 2026-07-30 |

📝 **Vale la pena reconfirmar el centrado del LIDAR** ahora que sabemos que el robot es 18 de
largo por 22 de ancho: mide del borde delantero al eje del disco (debería dar 9 cm) y del
borde izquierdo al eje (debería dar 11 cm). Es la misma regla que ya tienes en la mano para A2.

---

## Lo que NO hace falta medir

No lo midas, ya está resuelto y por vías mejores que una regla:

- **La odometría.** La da el locator interno del RVR. Verificada: 1 mm de error en 1 m.
- **Las velocidades máximas.** Medidas: 0.40 m/s y 2.0 rad/s, con meseta al 100 %.
- **La rampa de aceleración.** Medida: ~0.5 s.
- **La distancia de frenado.** Medida con el `collision_monitor` en el lazo.

---

## Qué se puede repetir con cada medida

| Si mides… | Se puede volver a hacer |
|---|---|
| **A1** (`laser_z`) | Recalcular qué queda por debajo del plano de barrido — el límite del cap. 12.8 |
| **A2** (nivelación) | Atacar la inclinación de ~8°, que sigue sin causa |
| **A1 + A3** | Cerrar la cadena de la altura del LIDAR sin depender de dos fichas |
| **B1 + B2 + B3** | Dejar el modelo coherente para RViz y resolver los 4.5 cm que faltan |

Y con **A1 y A2** hechas, lo que toca repetir de verdad es:

1. **Las paradas contra pared** a 0.25 y 0.40 m/s. Los huecos publicados hoy
   (9.9 y 10.9 cm) están **recalculados con la media longitud corregida, no vueltos a medir**.
2. **El barrido de `radius`** (0.14 / 0.16 / 0.18) contra un mismo paso estrecho, fijando el
   hueco para que el buscador no elija otro — daría la curva completa del compromiso entre
   «parar lejos de las paredes» y «cruzar huecos estrechos».
