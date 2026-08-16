# Qué se rompe cuando el RVR se apaga con todo encendido, y cómo recuperarlo

**Fecha:** 2026-08-06 · **Robot:** rvr-01 · **Estado:** diagnóstico MEDIDO, remedios
PROPUESTOS y sin implementar.

---

## El caso que lo destapó

Mapeando un cuarto con `slam.launch.py` a mano, el usuario **puso el RVR a cargar**.
El robot no se movió de sitio y la Raspberry Pi siguió viva. Al volver a mirar:

```
/odom           95 mensajes en 6 s     ✅ 16,5 Hz
/estado_robot    7 mensajes en 6 s     ✅ rvr_responde: true, muestra de hace 0,021 s
/tf            265 mensajes en 16 s    ✅
/scan            0                     🔴
/map             0 en 16 s             🔴  (y el latch llega en ~40 ms cuando hay mapa)
```

O sea: **el robot parecía sano por todos los indicadores habituales** —driver
publicando, RVR respondiendo, TF circulando— y las dos cosas que hacían falta
para trabajar estaban muertas.

Es exactamente la familia de fallo que este proyecto persigue: *algo que parece
sano y está mudo*.

---

## Qué pasó, en orden

1. **El RVR se apagó y encendió** al conectarlo a cargar.
2. **El driver murió y systemd lo reinició.** No se observó directamente, pero la
   prueba es indirecta y sólida: el barrido del LIDAR estaba **apagado**, que es
   el estado que `atriz-robot.service` fuerza con su `ExecStartPost` **en cada
   arranque**. Nadie llamó a `/stop_scan`.
3. **`slam_toolbox` sobrevivió al reinicio del driver** —es un proceso aparte,
   lanzado a mano— y se quedó **vivo y mudo**.

Ese tercer punto es una trampa ya documentada en `CLAUDE.md`, y volvió a morder:

> *No reinicies el driver por debajo de un `slam_toolbox` ya arrancado. Se queda
> con un hueco en su búfer TF y con el `odom` anterior, y **deja de procesar**: el
> mapa sale idéntico celda a celda tras mover el robot 80 cm. Invalidó una prueba
> entera de la Fase 4.*

La diferencia con aquella vez es que **entonces alguien reinició el driver a
propósito**. Esta vez lo reinició *el hecho de cargar el robot*, que es una acción
cotidiana que nadie considera peligrosa.

---

## Los cuatro daños, por separado

| Daño | Se ve como | ¿Se recupera solo? |
|---|---|---|
| **1 · `slam_toolbox` vivo y mudo** | el mapa no crece aunque el robot se mueva | ❌ No |
| **2 · El barrido vuelve a OFF** | «el robot no obedece» — sin `/scan` el `collision_monitor` bloquea el movimiento (0,0 cm medidos contra 9,9 de control) | ❌ No, hay que pedir `/start_scan` |
| **3 · El origen de la odometría se reinicia** | posiciones y rumbos que no cuadran con lo de antes; el yaw del RVR vuelve a cero al ENCENDER | ❌ No, y no debería: es correcto que empiece de cero |
| **4 · El descriptor del LIDAR puede quedar muerto** | `/start_scan` responde `false` con «Timeout exceeded», el journal se llena de `Failed to get scan` a 20 Hz | ❌ No — evidencia 69 |

⚠️ **El daño 4 NO ocurrió esta vez**: `/start_scan` contestó `result: true` y `/scan`
volvió a **11,7 Hz**. Es importante decirlo, porque los daños 1 y 4 se parecen
desde fuera —«no hay `/scan`»— y tienen remedios distintos. Lo que los separa es
la respuesta de `/start_scan`.

---

## Cómo distinguirlos en 10 segundos

```bash
# ¿Es el descriptor muerto (daño 4)?
ls -l /proc/$(pgrep -f "[y]dlidar_ros2_dr")/fd | grep tty     # «(deleted)» -> sí
```

Y desde la web, sin entrar por SSH:

- `/start_scan` contesta **`result: true`** y `/scan` vuelve → era solo el estado
  de reposo tras el reinicio (daño 2).
- `/start_scan` **no contesta o contesta `false`** → descriptor muerto (daño 4):
  `sudo systemctl restart atriz-robot`.
- `/scan` va, `/tf` va, y **`/map` sigue a cero** → `slam_toolbox` mudo (daño 1):
  hay que relanzarlo.

---

## Remedios propuestos

### R1 · SLAM como unidad systemd atada al driver — **el que resuelve el daño 1**

Hoy SLAM se lanza a mano por SSH, así que systemd no sabe que existe y no puede
protegerlo. La pieza que falta es un `atriz-slam.service` hermano de
`atriz-nav.service`, que ya resolvió este problema para Nav2.

🔴 **Y aquí hay un matiz de systemd que decide si el remedio funciona, y que este
proyecto NO ha verificado:**

- **`BindsTo=`** propaga el **paro**: si el driver se detiene, la unidad atada se
  detiene. Es lo que `atriz-nav.service` usa hoy.
- **`PartOf=`** propaga el **paro y el REINICIO**: cuando la unidad nombrada se
  reinicia, la acción se propaga.

Si eso es exacto, `BindsTo=` **solo** haría que SLAM se pare cuando el driver se
reinicie — no que vuelva. Eso ya sería una mejora enorme sobre lo de hoy (un SLAM
parado es honesto; uno mudo no lo es), pero **no es recuperación automática**.

⚠️ **NO VERIFICADO en este robot.** Es lo que dice la documentación de systemd,
y este proyecto tiene la regla de no presentar una deducción como un hecho. Se
comprueba así, y son dos minutos:

```bash
# Con atriz-nav corriendo (o el atriz-slam nuevo):
systemctl restart atriz-robot
sleep 20
systemctl is-active atriz-nav      # ¿inactive (paró) o active (volvió)?
```

→ Si sale `inactive`, hace falta **`PartOf=` además de `BindsTo=`** para que
vuelva. Y entonces hay que decidir si *se quiere* que vuelva: para SLAM
probablemente sí; para Nav2 probablemente no —un robot que reanuda la navegación
solo tras un corte es justo lo que `cancelar_nav2` vino a evitar.

📝 **Y esto afecta a `atriz-nav.service` tal y como está hoy**, no solo al SLAM
futuro: con `BindsTo` a secas, un reinicio del driver deja la navegación parada
sin avisar a nadie. Puede ser lo correcto, pero hoy es un efecto secundario, no
una decisión.

### R2 · Que la web detecte el reinicio del driver — **no necesita tocar la Pi**

`/estado_robot` trae un `latido` que **arranca de cero con el driver**. Así que un
`latido` que **retrocede** es una prueba directa de que el driver se reinició, sin
preguntarle nada a nadie.

Es el mismo mecanismo que ya usa la liberación de la parada de emergencia para
saber si un mensaje es posterior a una llamada.

Con eso, la interfaz puede decir en el acto:

> *El driver se ha reiniciado. El barrido está apagado y el origen de la
> odometría ha vuelto a cero. Si estabas mapeando, SLAM ya no está procesando.*

Que es la frase que hoy no dice nadie, y la que habría ahorrado este rato.

**Coste: cero en el robot.** Es trabajo de la web y se puede hacer ya.

### R3 · Que el driver avise de que acaba de arrancar

Complementario a R2 y más barato de consumir: un campo o un log que diga
«arranque número N» o el instante de arranque. Hoy se deduce del `latido`, que
funciona pero es indirecto.

⚠️ Tocar `EstadoRobot.msg` obliga a recompilar el paquete de mensajes **borrando
`build/` e `install/`** —`colcon build` a secas dice «finished» y deja el `.msg`
viejo instalado, con el suscriptor dando `AttributeError`—. No es gratis: R2 da
el 90 % del valor sin tocar el robot.

### R4 · Lo que NO se propone, y por qué

- **Restaurar el barrido a su estado anterior tras un reinicio.** Tentador y
  equivocado: el barrido arranca apagado *a propósito* —si no, el X2 gira a
  11,8 Hz permanentes en los 16 robots— y un reinicio inesperado no es momento
  de encender un motor por iniciativa propia. Mejor **decirlo** (R2) que
  adivinarlo.
- **Que SLAM se relance solo siempre.** Sin mapa que conservar, relanzar SLAM
  empieza un mapa nuevo desde el origen nuevo. Si alguien llevaba veinte minutos
  mapeando, lo pierde igual. Lo que hace falta es **enterarse**, no reintentar.

---

## Qué hacer ahora mismo, mientras nada de esto esté implementado

Si el RVR se apaga y enciende con la Pi viva:

```bash
# 1 · El barrido vuelve a estar apagado. Encenderlo (o desde la web).
atriz-escaneo on

# 2 · Si estabas mapeando: SLAM está mudo. Ctrl-C y relanzar.
ros2 launch atriz_rvr_bringup slam.launch.py
ros2 lifecycle get /slam_toolbox      # tiene que decir  active [3]

# 3 · Si /start_scan no responde, es el descriptor muerto:
sudo systemctl restart atriz-robot
```

⚠️ Y **espera unos minutos antes de mapear**: la deriva del rumbo es ~1000× mayor
justo tras encender el RVR —0,97 °/30 s recién encendido contra 0,001 siete
minutos después—, así que un mapa hecho en caliente sale con distorsión evitable.

---

## 🔴 M6 ES IRRECUPERABLE. Y la causa no es la que el guion suponía

Actualizado el **2026-08-06, noche**. Lo encontró el usuario revisando el guion, en dos vueltas.

**Primera vuelta — el guion preguntaba mal.** `medir_recuperacion.sh` usaba
`systemctl show NRestarts` y `journalctl --since "-6 hours"`. Los dos miran el sitio
equivocado: `NRestarts` es **del arranque actual** —y la Pi había reiniciado *después*
del suceso, así que valía 0— y `--since` **mezcla arranques**. La guía de lectura decía
literalmente *«NRestarts = 0 → el driver NO se ha reiniciado»*: un **falso negativo**, una
comprobación que no puede fallar porque mira donde no ocurrió. Arreglado acotando por
arranque (`--list-boots` + `-b <id>`).

**Segunda vuelta — y el dato ya no existía.** Con el arreglo puesto, los arranques `-1` a
`-4` aparecen en `--list-boots` y están **vacíos**: 0 líneas de cualquier unidad. Sus
cabeceras sobreviven; su contenido lo borró la rotación.

```
journal en disco   34,3 M        SystemMaxUse = 32 M
arranques -1 a -4  0 líneas
registro más antiguo que queda:  4 de agosto, 21:25
```

### La ironía es del proyecto, no del guion

`fase_1_higiene_so.sh` fija `SystemMaxUse=32M` para proteger la microSD, y lo justifica con
una medida: *784 MB de journal sin límite causaban 47 s de bloqueo por I/O en 42 min de
sistema ocioso*. **Es una buena decisión.** Y es la que destruyó la evidencia forense del
único incidente que se ha querido investigar.

Con un agravante medido el mismo día, dentro del propio journal:

```
[collision_monitor] Latest source and current collision monitor node timestamps
differ on 4514.739089 seconds. Ignoring the source.
```

**El ruido de un componente se está comiendo el historial de todos los demás.**

### Lo que queda escrito, y con su etiqueta

La explicación original —*el driver se reinició*— **sigue siendo un razonamiento indirecto**,
apoyado en que el barrido estaba apagado y eso es lo que el `ExecStartPost` fuerza en cada
arranque. **No se puede confirmar ni desmentir.** Se etiqueta así y no se cita como hecho.

📌 Y hay una sospecha mejor que no se pudo comprobar: **la Pi reinició a las 16:17**, ocho
minutos antes de que se relanzara SLAM. Si el suceso fue ese, no se reinició el driver sino
**la Pi entera** —la Pi se alimenta del USB del RVR—, y eso explicaría de golpe el barrido
apagado, la odometría a cero, el `slam_toolbox` muerto y el `NRestarts = 0`. **Sin confirmar,
y ya no se puede.**

### Las dos decisiones que esto destapa, y son más importantes que M6

**A12 · El journal no aguanta un incidente ni dos días.** Con 16 robots y fallos
intermitentes que se diagnostican *a posteriori*, eso es un problema de diseño y no una
molestia.
~~⚠️ **Subir `SystemMaxUse` no garantiza retención**: solo pone un techo, y con un emisor
constante cualquier techo se consume en un tiempo proporcional — más grande solo compra
horas. Lo que garantiza N arranques es **`SystemMaxFiles`**, y lo que garantiza tiempo es
**`MaxRetentionSec`**. Las tres opciones no son alternativas.~~

🔴 **RETIRADO el 2026-08-15: está AL REVÉS.** `MaxRetentionSec` es una edad **máxima** —borra lo
más viejo— y `SystemMaxFiles` un número **máximo** de ficheros. Los dos solo pueden **RECORTAR**
la retención; ninguno la garantiza. Lo único que la produce es `SystemMaxUse ÷ ritmo`.
📝 Lo que **sí** era cierto y se conserva: «más grande solo compra horas». La retención es un
cociente, no una promesa: una inundación como la del ydlidar (2,17 M líneas/día) hundiría los 7
días a minutos. Por eso el verificador **la mide**, en vez de leer el parámetro.

✅ **A12 CERRADO el 2026-08-15, evidencia 122.** Y lo que se encontró al medir era mayor que lo
planteado aquí: el tope de 32M **no controlaba ni la mitad de las escrituras**, porque Ubuntu
reenvía a rsyslog y cada línea se grababa dos veces (`/var/log` en 106 MB). Ver el fichero de
evidencia.

**A11 · Callar al `collision_monitor` es lo que ataca la causa.** Y antes de silenciarlo hay
que saber si el aviso es benigno, porque dice **«Ignoring the source»** y la fuente que
ignora es el LIDAR: si es cierto de forma sostenida, **la capa de seguridad está inerte**.

Medido después del hallazgo, con el barrido encendido: **`/scan` a 11,7 Hz** y el sello del
barrido a **0,5 s** del reloj de un PC externo — o sea que **el reloj está bien ahora**. Y
`/collision_monitor_state` a 0 **no prueba nada**: ese topic anuncia cambios de acción, y sin
nada dentro del polígono no hay cambio que anunciar.

→ Hipótesis principal, **SIN CONFIRMAR**: la Pi **no tiene RTC**, así que arranca con el
reloj rancio, los nodos sellan mensajes, y al sincronizar NTP el reloj **salta**. 4514 s son
~75 min, del orden de un arranque sin red inmediata.

→ **El discriminante, y es un comando:**

```bash
journalctl -b 0 -u atriz-robot --no-pager -o short-iso | grep "Ignoring the source" | head -3
journalctl -b 0 -u atriz-robot --no-pager -o short-iso | grep "Ignoring the source" | tail -3
```

**Agrupados en los primeros minutos** → transitorio de arranque; lo que sobra es el ruido.
**Repartidos hasta ahora** → el monitor lleva ignorando el LIDAR todo el día, y entonces la
capa de seguridad estuvo inerte mientras se conducía el robot desde la web. **Eso va por
delante de M10.**

---

## Lo que este documento NO sabe

- **Si el driver murió de verdad o solo se reconfiguró.** La prueba es indirecta
  (el barrido en OFF). Para confirmarlo hace falta
  `journalctl -u atriz-robot --since "-30 min"` en el robot, y no se ha mirado.
- **Si `PartOf=` se comporta como dice la documentación en este systemd 255.**
  Ver R1: el proyecto ya se llevó una sorpresa con `StartLimitBurst`, que systemd
  acepta en la sección equivocada **sin decir nada**.
- **Qué pasa si el RVR se apaga y NO se vuelve a encender.** Ahí la Pi acaba
  perdiendo alimentación, que es otro caso y no se ha caracterizado.

---

## 🔴 CORRECCIÓN del 2026-08-06, noche: M6 SÍ tiene respuesta, y no es la que se buscaba

La sección de arriba concluye «M6 es irrecuperable» porque el **contenido** del journal de los
arranques anteriores se rotó. El contenido sí; **las cabeceras de arranque no**, y con ellas basta:

```
arranque -1  termina  2026-08-06 15:09:03
arranque  0  empieza  2026-08-06 16:17:06     ← más de una HORA de hueco
```

Es el **caso (c)** de la guía de lectura del propio `medir_recuperacion.sh`: *«el arranque TERMINA
a la hora de la carga y empieza otro → NO se reinició el driver: SE REINICIÓ LA PI ENTERA»*.
✅ **El usuario confirmó que el RVR estuvo cargando en esa ventana.**

Explica los cuatro síntomas de golpe, y es física, no conjetura: **la Pi se alimenta del USB del
RVR**. Barrido apagado (lo fuerza el `ExecStartPost` en cada arranque), `NRestarts=0`,
`slam_toolbox` muerto (se lo llevó la sesión SSH) y el mapa perdido.

📝 **Lo irrecuperable era el detalle, no el desenlace.** Y la lección de método: se dio por perdida
una pregunta mirando el sitio donde el dato ya no estaba, teniendo la respuesta en el índice.

## 🔴 Y la causa que se le atribuyó al journal tampoco se sostiene

Esta misma sección dice: *«el ruido de un componente se está comiendo el historial de todos los
demás»*, señalando al `collision_monitor` y sus «4514 s». **Medido el mismo día, y no:**

```
19 mensajes en 2 h, TODOS en la ventana con el barrido APAGADO
ninguno durante los 36 minutos con el LIDAR barriendo
```

Y los **4514 s no eran un salto de reloj**: son **la edad del último barrido**. Con el LIDAR
parado desde las 16:55, un mensaje de las 18:10 lleva un sello de 75 minutos ≈ 4500 s. Cuadra al
segundo. El `collision_monitor` estaba **haciendo su trabajo**: decir que no se fía de un dato
caducado. Y en ese estado el robot no conduce de todos modos.

**Las tres explicaciones candidatas, medidas:**

| candidato | medida | veredicto |
|---|---|---|
| `collision_monitor` | 19 mensajes en 2 h | ❌ no llena nada |
| La inundación del LIDAR (`Failed to get scan`) | **0 apariciones en todo el journal** | ❌ el parche del 2026-08-01 la cerró |
| Este arranque entero | **1463 entradas** (31 % kernel, 23 % atriz-robot, 23 % init.scope) | ❌ ni de lejos 32 MB |

→ ⏳ **Qué llenó los 32 MB queda SIN SABER**, y así se escribe. Lo que sí está medido es el
**efecto**: 34,3 MB contra un tope de 32, cuatro arranques vaciados, y el registro más antiguo del
**4 de agosto a las 21:25** — o sea **dos días de retención**.

✅ **Lo que sí se sostiene de aquel análisis, y es lo importante:** dos días de retención son pocos
para un laboratorio donde los fallos son intermitentes y se diagnostican a posteriori.
📝 Y el matiz que lo corrige: **`SystemMaxUse` es un techo, no una retención.** Subirlo solo compra
horas. ~~Lo que garantiza arranques conservados es `SystemMaxFiles` o `MaxRetentionSec`.~~
🔴 **Esa segunda frase está RETIRADA (2026-08-15): los dos solo RECORTAN.** Ver la corrección en la
sección A12 de este mismo plan.
