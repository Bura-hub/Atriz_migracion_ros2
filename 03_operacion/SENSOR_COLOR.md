# El sensor de color del RVR — cómo funciona y sus DOS modos

> Para quien construya la pantalla de la web, escriba una práctica o dude de una lectura.
> Todo lo que hay aquí está **medido en rvr-01**; lo que no, lo dice.

---

## 1 · No es un sensor de color: es un RGBC

Cuatro fotodiodos bajo el chasis, mirando al suelo. **Tres llevan filtro** —rojo, verde, azul— y
**el cuarto no lleva ninguno**. Ese cuarto es `claro` (*clear*).

```
  R  G  B    ← «de qué color es»       (con filtro)
  claro      ← «cuánta luz hay»        (sin filtro)
```

Como `claro` no filtra nada, mide **la luz total**. En el modo normal eso equivale a *cómo de
reflectante es la superficie*, y por eso es el canal que distingue negro de blanco mucho mejor que
cualquier canal de color:

```
  negro     181
  blanco   2288        12,6 veces más
```

### Tres cosas que hay que saber antes de usar un número

**1 · `claro` no tiene unidades.** Es una cuenta cruda del conversor, en una escala arbitraria que
depende del tiempo de integración y de la iluminación. **No son lux.** Por eso un umbral como
`400` vale **para un montaje**, no en general — y de hecho el suelo dio **1275** en una habitación
y **~950** en otra, con el mismo robot y el mismo día.

**2 · El color se juzga por PROPORCIONES, no por valores absolutos.** Si el sensor se acerca o se
aleja, los cuatro canales suben o bajan juntos, pero `R/G` y `B/G` se mantienen. **Los absolutos
dicen cuánta luz; las proporciones, de qué color.** Se normaliza por **verde**, que es el canal más
sensible.

**3 · Hay un LED blanco bajo el chasis, y es parte del instrumento.** Lo enciende
`enable_color(true)` — **no** `undercarriage_white`, que devuelve `success=true` y no hace nada.
Sobre una superficie reflectante marca la diferencia entre medir y no medir: `claro` **4 apagado
contra 741 encendido**, 185×. Es el fallo que tuvo `/color` publicando ceros durante meses.

---

## 2 · LOS DOS MODOS, y el segundo no es un estado degradado

Aquí está lo que este documento existe para decir.

| | **Modo REFLEJO** | **Modo EMISIÓN** |
|---|---|---|
| Para qué | suelo, cinta, papel, una línea | **una pantalla, una baldosa LED** |
| La luz del sensor | **encendida** | **apagada** |
| Qué se mide | el reflejo del LED del robot | lo que la superficie **emite** |
| Cómo se lee | topic `/color` **o** el servicio | 🔴 **sólo el servicio** |
| Sin la luz correcta | lecturas de oscuridad | **el color sale al revés** |

### Por qué en una superficie que emite hay que APAGAR la luz

El LED está a **milímetros** de la superficie. Sobre vidrio pasa lo peor de los dos mundos: el
reflejo es **especular** —rebota como un espejo, no se dispersa— y **es blanco**, así que devuelve
el color del LED y no el de la baldosa.

Medido el 2026-08-08 sobre una pantalla de móvil a brillo máximo, **sin mover el robot entre
colores** (evidencia 86):

```
              luz del sensor APAGADA          luz del sensor ENCENDIDA
             R/G     B/G    claro            R/G     B/G    claro
  ROJO      5.12    0.15      150           0.66    0.49     1238
  VERDE     0.17    0.20      387           0.37    0.40     1467
  AZUL      0.11    4.57      190           0.46    0.73     1230
```

✅ **Apagada, los tres se separan por un factor 25-30.** La regla sale sola:
`R/G > 1` → rojo · `B/G > 1` → azul · las dos bajas → verde.

🔴 **Encendida, los seis cocientes viven entre 0,37 y 0,73** — el reflejo lo aplana todo. Y el rojo
da **`R/G = 0,66`: menos rojo que verde sobre una pantalla roja a tope.** No pierde precisión,
**engaña**.

📌 Para comparar: una superficie roja **mate** da `R/G = 2,74` con la luz encendida. Sobre vidrio
emisor da 0,66. **El vidrio no solo no ayuda: invierte el resultado.**

### El control que valida el experimento

La luz aportó **+1088, +1080 y +1040** de `claro` en los tres colores — **4 % de dispersión**.
Tiene que ser así: es su reflejo sobre el mismo vidrio, en la misma posición, y **no depende de lo
que muestre la pantalla debajo**. Eso prueba que el servicio hizo efecto **sin mirar su `success`**.

---

## 3 · 🔴 En modo EMISIÓN hay que usar el SERVICIO, no el topic

Es la trampa de este modo y está **medida**:

```
  luz ENCENDIDA   topic /color -> 40 mensajes, 40 no-cero     servicio -> R214 G468 B212 claro 809
  luz APAGADA     topic /color -> 39 mensajes,  0 no-cero     servicio -> lecturas REALES
```

**Con la luz apagada el topic publica ceros.** No es un fallo: `/color` sale del **streaming** del
RVR, y el streaming se apaga junto con la detección. El servicio
`/get_rgbc_sensor_values` **consulta**, así que sigue dando datos.

⚠️ **Y el topic no trae `claro` de todas formas** — `Color.rgb_color` son tres enteros. Para el
canal que discrimina hay que ir al servicio en los dos modos.

📌 **Coste medido: 20,6–20,8 ms por llamada (n=200).** Cabe de sobra en un lazo a 10 Hz.

---

## 4 · Contrato para la web

**No hace falta ningún servicio nuevo.** Las dos piezas ya existen, están en la lista blanca de
rosbridge y están verificadas:

| Llamada | Tipo | Para qué |
|---|---|---|
| `/enable_color` | `std_srvs/SetBool` | `true` = modo reflejo · `false` = modo emisión |
| `/get_rgbc_sensor_values` | `atriz_rvr_msgs/GetRGBCSensorValues` | R, G, B, `claro` + `success` + `message` |

### Cómo presentar los dos modos

```
  ( ) Superficie normal   — suelo, cinta, papel        → enable_color(true)
  ( ) Superficie luminosa — pantalla, baldosa LED      → enable_color(false)
```

**Y en los dos casos se lee con `/get_rgbc_sensor_values`.** La única diferencia es el estado de la
luz. Eso hace la pantalla muy simple: un interruptor de modo y el mismo lazo de lectura.

### Lo que la pantalla NO debe hacer

🔴 **No presentes `color_activo = false` como «sensor apagado» o «no disponible».** En modo emisión
ese es el estado **correcto**, y el sensor está midiendo. El campo dice *si la luz está
encendida*, no *si el sensor sirve*.

🔴 **No trates `claro = 0` como un fallo.** Significa «no llega luz», que en modo emisión es un
resultado legítimo: la baldosa está apagada, o no hay nada debajo. **El discriminante es
`success`**, no el valor.

⚠️ **Y no pintes un color sin decir de qué modo viene.** Los mismos R/G/B significan cosas
distintas: en reflejo son el color de la superficie; en emisión, el color de la luz que sale.

### Lo que sí conviene mostrar

- Los **cuatro** canales crudos, y `R/G` y `B/G` calculados. Las proporciones son lo que decide.
- El `message` del servicio: el driver avisa ahí cuando la luz está apagada, **sin afirmar que las
  lecturas sean oscuridad** — porque no puede saberlo.
- ⏳ Y si se muestra una interpretación («rojo», «azul»), que sea a partir de las proporciones y
  con el modo escrito al lado.

### Apagado automático — no interfiere

El driver apaga la luz sola tras `color_apagado_inactividad_s` (120 s) y con un tope duro de
`color_apagado_max_s` (900 s). **En modo emisión la luz ya está apagada, así que no hay conflicto.**
Y llamar a `/get_rgbc_sensor_values` **cuenta como actividad**, así que el modo reflejo no se corta
mientras el alumno mide.

---

## 5 · Lo que NO está medido, y no se puede prometer

⚠️ **Todo lo del modo emisión se midió con una PANTALLA DE MÓVIL, no con una baldosa LED.** Dos
diferencias que pueden cambiar el resultado:

- **Saturación.** El máximo alcanzado fue `claro = 387`, muy lejos de los 2288 del blanco
  reflectante. Una baldosa real puede ser mucho más brillante. **No se sabe dónde satura el canal**
  ni si el firmware ajusta la ganancia. Si satura, los tres canales se van al tope y **el color se
  pierde otra vez**, esta vez por arriba.
- **Parpadeo PWM.** Aquí la dispersión de `claro` fue de **2-4 cuentas en 12 lecturas** — el tiempo
  de integración promedia el PWM del móvil. Una baldosa con PWM más lento podría batir contra esa
  integración. **No se transfiere.**

⚠️ **Esto no es colorimetría.** Los filtros RGBC no están calibrados. Distingue primarios por
proporciones; **no** da un color en coordenadas de verdad.

⏳ **Sin probar:** colores intermedios, blanco emitido, y la baldosa real.

📝 **Y `confianza` es siempre 0**, en los dos modos. No es un fallo ni falta configurar nada: el
clasificador tiene su paleta de cinco colores cargada, y las superficies que se prueban no se
parecen a ninguno. **Ignórala.**

---

## 6 · El otro sensor óptico, que NO sirve

📌 `/ambient_light` es **otro sensor, en otro sitio, mirando hacia ARRIBA**. El piso blanco que
sostiene el LIDAR le devuelve la luz de los propios LEDs del robot: encenderlos todos lo sube de
1,76 a **23,55**, 13,3×.

🔴 **Decisión tomada: no se usa.** En este montaje un valor alto significa «el robot tiene LEDs
encendidos», no «hay luz». Se deja publicado porque es gratis. **Ningún consumidor debe apoyarse en
él**, y menos la pantalla de medición de superficies luminosas — que es justo donde alguien
pensaría en usarlo.
