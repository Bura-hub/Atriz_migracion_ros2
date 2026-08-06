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

## Lo que este documento NO sabe

- **Si el driver murió de verdad o solo se reconfiguró.** La prueba es indirecta
  (el barrido en OFF). Para confirmarlo hace falta
  `journalctl -u atriz-robot --since "-30 min"` en el robot, y no se ha mirado.
- **Si `PartOf=` se comporta como dice la documentación en este systemd 255.**
  Ver R1: el proyecto ya se llevó una sorpresa con `StartLimitBurst`, que systemd
  acepta en la sección equivocada **sin decir nada**.
- **Qué pasa si el RVR se apaga y NO se vuelve a encender.** Ahí la Pi acaba
  perdiendo alimentación, que es otro caso y no se ha caracterizado.
