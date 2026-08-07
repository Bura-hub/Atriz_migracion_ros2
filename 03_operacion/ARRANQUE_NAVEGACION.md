# Cómo arranca la navegación en los 16 robots

> **La contradicción que cierra.** `atriz-robot.service` levanta **solo** `robot.launch.py`.
> `nav2.launch.py`, `slam.launch.py` y `localizacion.launch.py` se lanzan **a mano, por SSH, en
> dos terminales**. Así que la Decisión 2 —«el SSH ya no hace falta ni para el ciclo de vida»— es
> cierta **solo para teleoperación**: para navegar, hoy alguien tiene que entrar por SSH.
> `ARQUITECTURA.md` lo tiene anotado como decisión pendiente desde el 2026-08-02.
>
> Diseñado y acordado el **2026-08-03**.

---

## Lo que se decidió con el usuario, y por qué

| Pregunta | Respuesta | Qué implica |
|---|---|---|
| ¿Quién necesita navegación y cuándo? | **No se sabe**: depende de cómo salga la web, que está por hacer | No hay información para optimizar. Lo correcto es **elegir barato**, no elegir bien |
| ¿Cómo pasan el día los robots? | **Encendidos solo durante la clase** (2-3 h), luego apagados o cargando | Pero «solo en clase» incluye **sesiones de desarrollo largas**, que es donde más se nota |
| ¿Vuelve la navegación tras un reinicio? | **No.** Explícito | Un robot que se reinicie de madrugada vuelve a su estado base |

### 🔴 El dato que decide, y que no se dio por supuesto

> **«La Pi se alimenta del puerto USB del RVR»** — `MANUAL_ATRIZ_ROS2.md:63`

**La carga de CPU sale de la batería del robot.** Y la autonomía medida es **~2 h por carga**
contra una clase de **2-3 h**: la batería ya es la restricción que aprieta, y no cubre una clase
entera. Nav2 es **la pieza más pesada del sistema, ~58 % de un núcleo**.

⚠️ **Con una salvedad honesta:** lo medido es **0.74 %/min conduciendo**, sin separar motores de
Pi. **Cuánto cuesta en batería un 58 % de núcleo extra NO lo sabe nadie.** La dirección está
clara; la magnitud, no. El proyecto ya decidió una vez no gastar horas de robot en una medida
parecida (el consumo del lidar), y esta no se persigue tampoco.

📝 **Y la sesión del 2026-08-03 es el argumento de más peso**, porque no es una estimación: la
batería cayó **7.60 → 7.28 V** en una sesión donde el robot condujo unos pocos metros. Casi todo
el gasto fue **estar encendido**, no moverse. En una sesión de desarrollo el robot pasa la mayor
parte del tiempo quieto mientras se edita código — y ahí un Nav2 arrancado solo serían horas de
58 % de núcleo sin usarse ni una vez.

---

## 🔴 AMPLIACIÓN DEL 2026-08-06 (tarde) — decisión del usuario

> *«Ambas deberían poderse habilitar desde la web según la necesidad del usuario. **Apruebo que
> estén disponibles.**»*

**Lo que NO cambia:** ni Nav2 ni SLAM arrancan solos al encender el robot. La decisión de arriba
—instaladas y no habilitadas— sigue entera, y por la misma razón: la Pi se alimenta de la batería
del RVR y Nav2 son ~58 % de un núcleo.

**Lo que SÍ cambia:** deja de ser *«se arrancan por SSH»* y pasa a ser ***«se arrancan bajo demanda,
y la web es quien las pide»***. El estado por defecto sigue siendo apagado; lo que se añade es el
mando.

⚠️ **Y eso reabre un punto que un panel anterior usó para rechazar el mecanismo**: rosbridge **no
autentica a nadie** (`websocket_handler.py:233-234` devuelve `True` sin condiciones, y las 15
capacidades instaladas de `rosbridge_library` no incluyen ninguna de autenticación). Exponer
`start`/`stop` por ahí es exponerlo a cualquiera en la red del aula.
→ **No se esquiva: se resuelve.** Análisis en curso con cuatro agentes (seguridad, mecanismo
systemd, integración ROS y un escéptico). El diseño resultante irá en un plan aparte.

📌 **Y una cosa que este documento ya no puede seguir dando por hecha:** el argumento que mantiene
Nav2 sin habilitar es su coste, **~58 % de un núcleo**. **SLAM cuesta 4,8 %, doce veces menos.** La
conclusión para SLAM puede seguir siendo la buena, pero **no por esta razón**, y ninguna otra está
escrita.

---

## 🔧 Dónde se configura el mapa — UN sitio, `/etc/default/atriz`

```
ATRIZ_MAPA=/home/sphero/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/maps/aula.yaml
ATRIZ_DIR_MAPAS=/home/sphero/mapas
```

Lo leen las **tres** unidades por `EnvironmentFile=-/etc/default/atriz`:
`atriz-robot` (y con ella `supervisor_navegacion`, que corre dentro), `atriz-nav` y `atriz-slam`.

🔴 **Existe porque la ruta vivía en dos sitios independientes y se desincronizaron de verdad** el
2026-08-07: el launch resolvía al directorio **instalado** y el script al **fuente**. El síntoma
fue `hay_mapa: false` sobre un robot que sí podía navegar — y el caso inverso es peor: la web
habilita el botón, la unidad falla al arrancar y **gasta su presupuesto de reintentos hasta quedar
latcheada**, que solo se recupera con `reset-failed`. Evidencia 80.

📝 **No está en el manifiesto**, y es a propósito: el manifiesto es para ficheros idénticos en los
16 comprobados con `cmp`, y este lo edita el operador. `fase_7` **no lo sobrescribe si ya existe**
y `--quitar` **no lo borra** — puede llevar la ruta de un mapa que costó una sesión entera.
Se verifica **por efecto**: que las unidades lo declaren y que el mapa sea legible.

⚠️ Tras editarlo: `sudo systemctl restart atriz-robot` (y las unidades que estén activas).

## El diseño

### `atriz-nav.service` — instalada, NO habilitada

```bash
systemctl start atriz-nav      # arranca navegacion
systemctl stop atriz-nav       # la para
systemctl restart atriz-nav    # sin tocar el driver ni soltar /dev/rvr
```

**No sobrevive a un reinicio.** Se instala sin `enable`, así que `WantedBy` no llega a crear el
enlace. Es la decisión del usuario y encaja con la línea del proyecto: nada de estado silencioso.

📝 **Por qué una unidad aparte y no un argumento de `robot.launch.py`.** Fusionarlos acoplaría los
ciclos de vida: reiniciar Nav2 obligaría a reiniciar el driver. El proyecto ya decidió lo
contrario, y por la razón buena — *«SLAM va en un launch aparte… el robot tiene que arrancar sin
SLAM, y SLAM reiniciarse sin soltar `/dev/rvr`»*. En una sesión de desarrollo se reinicia la
navegación muchas veces; el driver, casi nunca.

### Levanta AMCL, no SLAM

`localizacion.launch.py` + `nav2.launch.py`.

**No SLAM**, y no por la CPU — AMCL cuesta **8.8 %** contra los **4.8 %** de SLAM, o sea que es
*más* caro. El argumento es **el marco compartido**: 16 robots sobre un mismo `map` es lo que
permite que la web diga «ve a la mesa 3». Está decidido desde el manual, cap. 14.1.

⚠️ Los dos publican `map → odom`: **son excluyentes** y `localizacion.launch.py` lo comprueba al
arrancar. SLAM se queda como está —**a mano, para hacer mapas**—, que es tarea de administrador,
no de operación.

### 🔴 El barrido: dos conflictos reales que hay que cerrar

Comprobado sobre el código, no supuesto:

```
ningun launch de navegacion enciende el barrido
  slam.launch.py y nav2.launch.py NECESITAN /scan   (localizacion.launch.py no lo toca)
  robot.launch.py solo NOMBRA start_scan/stop_scan en la lista blanca de rosbridge (linea 338),
     no los llama
quien lo APAGA es la unidad:  atriz-robot.service:49  ->  ExecStartPost=-atriz-escaneo off
atriz.py enciende el barrido al conectar y lo APAGA al cerrar
```

📝 Ese reparto importa para el diseño: **el barrido no lo gobierna ningún launch, lo gobierna
quien arranca el sistema**. Por eso la unidad nueva es el sitio correcto para encenderlo, y no
`nav2.launch.py`.

**Conflicto 1 — la navegación arrancaría ciega.** Sin `/scan` el `collision_monitor` bloquea el
movimiento (medido: **0.0 cm** contra 9.9 del control) y el robot **parece averiado**.
→ La unidad enciende el barrido al arrancar y lo apaga al parar.

**Conflicto 2 — un script de alumno dejaría a Nav2 ciego en silencio.** Con navegación en marcha,
`cerrar()` de `atriz.py` llama a `/stop_scan` y Nav2 se queda sin datos sin que nada avise.

→ **Arreglo en `atriz.py`: dejar las cosas como las encontró.** Si al conectar **ya llega
`/scan`**, es que otro lo tiene encendido → **no lo apaga al cerrar**. Solo apaga lo que él
encendió.

Es pequeño, es un principio general, y es lo que evita que dos consumidores del mismo recurso se
pisen sin enterarse. **Los dos conflictos son la firma de fallo de este proyecto: algo que parece
sano y no está haciendo nada.**

✅ **Y el CONFLICTO 3, cerrado el 2026-08-07: la exclusión SLAM/AMCL era de un solo sentido.**
`localizacion.launch.py:70-93` se negaba si había SLAM vivo; **`slam.launch.py` no comprobaba
nada**, así que «Nav2 y luego SLAM» arrancaba tan contento y dejaba dos publicadores de
`map → odom` **sin un solo error**. Ya tiene su guardia simétrico (`Atriz_rvr@fac74bf`), que
comprueba `async_slam_tool` **y** `amcl`, verificado en las tres direcciones.
⚠️ Lo que NO cierra: la **carrera** entre dos clientes simultáneos. `ps` mira un instante. Eso
pide un cerrojo en el supervisor, no en un launch.

### Si el driver se cae, la navegación cae con él — y ahora TAMBIÉN VUELVE

Hoy la unidad usa `BindsTo=atriz-robot.service`. Sin eso quedaría un Nav2 publicando sobre una
odometría muerta — otra vez algo que parece vivo y no lo está, que es lo que `on_exit=Shutdown()`
vino a resolver en `robot.launch.py`.

🔴 **Pero `BindsTo=` propaga la PARADA, no el REINICIO.** Y el driver se reinicia solo, de forma
rutinaria. Medido el 2026-08-06 con unidades de juguete: **tras matar el proceso base, la unidad
atada queda `inactive` y NO VUELVE.** A mitad de clase, un nodo muere, el driver se repone, y la
navegación desaparece sin que nadie la haya parado.

✅ **La sustitución, MEDIDA 9 de 9 el 2026-08-07** (evidencia 78):

```
PartOf= + Requires= + After=        ← y NADA de BindsTo=
```

`PartOf=` propaga el paro **y el reinicio**: tras matar el proceso base, la atada volvió **con PID
nuevo** las seis veces (`partof-requires` y `partof-solo`). Proceso nuevo = búfer TF nuevo, que es
justo lo que hace falta — porque `slam_toolbox` **sobreviviendo** es el fallo, no el remedio.

⚠️ **Y NO se ponen las dos.** La rama «ambas» (`BindsTo=` + `PartOf=`) dio `inactive` tras matar el
proceso: **`BindsTo` gana y la unidad no vuelve.**

📝 `Requires=` no cambia la recuperación —`partof-solo` da lo mismo— pero impide arrancar sobre un
driver muerto, que daría un Nav2 `active` sin `/scan` y sin TF.

⏳ **Pendiente de aplicarlo a `atriz-nav.service`**, que sigue con `BindsTo=`. Va junto con la
sesión B2/B3, para no cambiar la unidad y estrenarla a ciegas en el mismo movimiento.

---

## Lo que este diseño NO decide, a propósito

**Si la navegación debe arrancar sola cuando exista la web.** No hay información para decidirlo:
la web está por hacer. Este diseño convierte esa decisión futura en **`systemctl enable
atriz-nav`, un segundo**, en lugar de en un rediseño.

Y deja de pie una medida que hará falta para tomarla y que **nadie ha tomado**:

⏳ **Cuánto tarda Nav2 en estar listo** (desde `systemctl start` hasta el lifecycle activo y
`/navigate_to_pose` aceptando objetivos). Si son 5 s, arrancar a demanda es gratis. Si son 40, no.
**NO MEDIDO.**

---

## Verificación

Se comprueba **el efecto, no el código de salida** — la regla que este proyecto lleva seis veces
documentada.

1. **Arranca y navega de verdad.** `systemctl start atriz-nav`, y después un objetivo por
   `/navigate_to_pose` que el robot cumpla. Que la unidad diga `active` no prueba nada.
2. 🔴 **El barrido se enciende solo.** Con el robot recién arrancado (barrido apagado por diseño),
   `systemctl start atriz-nav` tiene que dejar `/scan` publicando **sin que nadie lo toque**.
3. 🔴 **Y un script de alumno NO deja ciega la navegación.** Con `atriz-nav` corriendo, ejecutar
   un guion del curso de principio a fin y comprobar que `/scan` **sigue publicando** al terminar.
   Es el conflicto 2, y hay que provocarlo, no razonarlo.
4. **`restart` no toca el driver.** `systemctl restart atriz-nav` y comprobar que `/odom` no se
   interrumpe y que `NRestarts` de `atriz-robot` no sube.
5. **`BindsTo` funciona:** parar `atriz-robot` tiene que parar `atriz-nav`.
6. 🔴 **Tras un reinicio de verdad, la navegación NO vuelve** y el driver sí.
7. **Medir el tiempo de arranque** y anotarlo, que es el dato que falta para la decisión futura.

📝 **Todo lo de arriba se puede comprobar con CUALQUIER mapa válido**, apuntándolo con
`ATRIZ_MAPA`: verifica el **mecanismo**, no el contenido. Solo el `aula.yaml` de verdad tiene que
esperar al laboratorio.

---

## Lo que queda fuera

- **No decide el arranque automático.** Es el punto entero de este diseño.
- **No toca SLAM**, que sigue lanzándose a mano para mapear.
- **No mide el coste en batería de la CPU.** Se anota **NO MEDIDO** y se acepta la incertidumbre.
- **No construye ningún disparador para la web**, que no existe. Cuando exista, la unidad ya está.
