# Prueba de aceptación de un robot — de arranque en frío a navegación autónoma

> **Para qué existe.** Todo en este proyecto se ha verificado **por partes**: los LEDs un día, el
> `collision_monitor` otro, Nav2 otro, siempre sobre un robot ya encendido y toqueteado a mano.
> Que cada pieza funcione por separado **no dice que arranquen juntas**. Esta prueba hace una sola
> pasada continua, desde un reinicio de verdad hasta un objetivo autónomo rodeando un obstáculo, y
> responde a una única pregunta: **¿se puede empezar la plataforma web sobre este robot?**
>
> Diseñada y acordada el **2026-08-01**, antes de abrir la Fase 5.

---

## Lo que esta prueba cierra, y lo que no

**Los tres huecos que la motivaron:**

| | |
|---|---|
| 🔴 **Nunca hubo una pasada de arranque en frío a navegación de un tirón** | Cada fase se probó en un momento distinto. Nadie ha comprobado que un robot recién reiniciado llegue solo hasta navegar |
| 🔴 **El ángulo nunca se ha medido** | `move_to_pos_and_yaw` está verificado en **distancia** (0.20 m comandados → 19.5 cm medidos, evidencia 26), pero **su componente de yaw no**, y `move_to_pose` figura como «✅» sin un número detrás |
| 🔴 **`verificar_robot.sh` no mueve el robot** | Ni con `--hardware`. Sus 105 comprobaciones son estáticas y de telemetría; toda la parte dinámica quedaba fuera |

**Lo que NO cierra, y hay que saberlo antes de empezar:** las decisiones abiertas (rosbridge sin
autenticación, el hueco de los precipicios, el `fmask` de la PSK, la rotación de la credencial).
Ninguna se arregla ejecutando nada. La prueba **las lista y se niega a dar vía libre** mientras
sigan abiertas — ver «El veredicto».

---

## Arquitectura

Un solo proceso, `scripts/prueba_aceptacion.py`, con **un nodo ROS propio y persistente** para
todas las fases.

📝 **Por qué un solo nodo y no reutilizar las herramientas de banco encadenadas:** esas
herramientas son **instrumentos de exploración, no jueces** — imprimen números, no dicen
«aprobado», y sacar un veredicto parseando su salida es frágil. Además cada una arranca y para su
propio nodo: doce arranques del SDK, con el RVR despertándose cada vez.

Se lanza por SSH después del reinicio. `--desde F4` retoma sin repetir lo ya pasado.

---

## Las diez fases

| | Fase | ¿Mueve? | Qué comprueba |
|---|---|---|---|
| **F0** | Arranque en frío | no | El robot arrancó **solo**: el servicio activo a 23 s del boot y `NRestarts=0` (ver abajo — **no** el `uptime`, que caduca), los 6 nodos del servicio, el journal limpio, y delega las 105 comprobaciones estáticas en `verificar_robot.sh`. Al final ejercita `Restart=always`, hoy **sin ejercitar** |
| **F1** | Telemetría | no | Los topics con su QoS y su ritmo, medidos con **ejecutor persistente**. Voltaje, estado y umbrales de batería. Que la temperatura no medida sea `NaN` y no `0.0`. Deriva de yaw en reposo |
| **F2** | LIDAR | no | `start_scan` → `/scan` a **10–12 Hz** con rangos sanos → `stop_scan` → se para. Y que el parche del journal aguanta: nada de inundación con el barrido parado |
| **F3** | Luces | no | 🔴 **Puerta: miras el robot.** Los cuatro servicios de LED. Lo confirmas tú con los ojos: no hay forma de leerlo desde el software |
| **F4** | Movimiento básico | **sí** | 🔴 **Puerta: pasillo despejado.** `move_timed` adelante y atrás. Y **parada de emergencia a mitad de un avance**, midiendo cuánto recorre después de recibirla |
| **F5** | **Ángulos** | **sí** | El hueco. Giros en el sitio de 90°, 180° y 360°, por `move_to_pos_and_yaw` y por `move_timed`, midiendo el **Δyaw** logrado contra `/odom` (nunca el yaw absoluto — ver abajo). También el convenio de signo |
| **F6** | Seguridad | **sí** | 🔴 **Puerta: pared enfrente.** `collision_monitor` frenando y el watchdog cortando al dejar de publicar `cmd_vel` |
| **F7** | Autónomo | **sí** | Lanza SLAM + Nav2, espera al lifecycle activo, manda el objetivo de 1.50 m. Luego 🔴 **puerta: obstáculo a 0.75 m dejando 60 cm libres MEDIDOS CON CINTA** y repite. Vigila que no reaparezca el `Failed to make progress` |
| **F8** | Web | no | rosbridge de verdad: conectar, suscribirse y llamar a un servicio |
| **F9** | Veredicto | no | Los cuatro niveles y la lista de pendientes que bloquean |

### Dos decisiones que conviene tener a la vista

**F5 no tiene base histórica.** El ángulo nunca se midió, así que esa fase **no puede suspender
contra un número que no existe**: la primera pasada **establece la referencia** y solo avisa si
sale de una banda de cordura amplia. Llamarlo aprobado o suspenso sería fingir un criterio que no
hay.

**F0 comprueba que el servicio subió SOLO, en el arranque y a la primera** — no el reloj.

Una primera versión de este diseño exigía `uptime < 30 min`. Funciona, pero **caduca**: si
preparar la prueba lleva media hora, falla sin que nada esté roto. Lo que de verdad se quiere
probar se lee sin reloj, y se midió el 2026-08-01 (evidencia 47):

| Señal | Medido | Qué demuestra |
|---|---|---|
| `ActiveEnterTimestamp − boot` | **23 s** | subió **en el arranque**. Si lo hubiera levantado alguien a mano, serían minutos u horas |
| `NRestarts` | **0** | a la primera, sin que `Restart=always` tuviera que rescatarlo |
| `Result` | `success` | |

Sin esto, la prueba «pasaría» sobre un sistema que lleva días encendido y arreglado a mano — el
sesgo que existe para eliminar. El `uptime` se sigue **informando**, porque es útil leerlo, pero
ya no decide nada.

⚠️ **`NRestarts` se queda a 1 en cuanto F0 ejercita `Restart=always`**, que mata el driver a
propósito. En una segunda pasada sobre el mismo arranque ya no será 0, así que F0 lo trata como
**REVISAR y no FALLO**, diciendo las dos lecturas posibles: o es una repetición de esta misma
prueba, o el driver se cayó de verdad. Lo desempata el journal.

### El journal solo se mira en F0, y hay que decir exactamente qué se mira

Concretamente: `journalctl -u atriz-robot -p err --boot`. Dos precisiones que evitan falsos
suspensos, y las dos son trampas reales de este sistema:

- 🔴 **La comprobación del journal NO puede repetirse al final.** El driver registra la parada de
  emergencia con **nivel ERROR** (`[ERROR] PARADA DE EMERGENCIA`), y F4 y F6 la provocan a
  propósito. Buscar errores después de mover el robot encontraría **los que la propia prueba
  causó** y los llamaría regresión. Por eso va en F0, antes de que nada se mueva.
- ⚠️ **Los 5 avisos de `verificar_robot.sh` no son FALLO.** F0 los traduce uno a uno, y ninguno a
  FALLO:

  | Aviso | Se traduce a |
  |---|---|
  | ~~`red.txt` en 755, la PSK legible~~ | ✅ **RESUELTO.** Ese aviso ya no sale: `verificar_robot.sh` dice `✓ /etc/fstab cierra la PSK (fmask=0177,dmask=0077)`. Comprobado el 2026-08-11 en **los dos** robots — en rvr-01 el `fstab` lo lleva y `/boot/firmware` es `drwx------`; en rvr-02 lo pone `provision.sh` (paso 8bis de la higiene) |
  | mDNS por enlace: `wlan0` no lo tiene | **PENDIENTE** (drop-in de systemd-networkd, manual 19.5) |
  | los `.bak-*` de apt | cosmético, se informa y ya |
  | no se pudo leer `60-atriz.yaml` (necesita root) | no concluyente: se **reintenta con `sudo -n`**, y si no hay privilegio se marca **NO VERIFICADO**, que no es lo mismo que «bien» |
  | yaw de `/odom` en reposo lejos de 0 | **se informa y no se juzga** — ver abajo, la premisa de ese aviso es falsa |

### 🔴 El yaw NO se pone a cero al reiniciar la Pi, y eso condiciona F5

Una primera versión de este diseño daba por hecho que `/odom` arrancaría en 0 tras el reinicio.
**Es falso, y estaba documentado en el propio driver desde el 2026-07-31**
(`rvr_driver_node.py:316`): `reset_yaw()` **no pone el yaw a cero**. El yaw solo se pone a cero
**al encender el RVR**, y `sudo reboot` reinicia **la Pi**, no el RVR — que tiene su propia
batería y su propio botón. El RVR arrastra su origen desde el último encendido: con uno limpio da
+0.5°, pero si se ha movido, cualquier cosa (+64.9° medido entonces; −75.9° medido hoy).

**Las dos consecuencias:**

1. **F5 mide Δyaw, nunca yaw absoluto.** Un giro de 90° se juzga por *cuánto cambió* la
   orientación, no por a dónde apunta. Es lo correcto de todos modos, pero ahora se sabe **por
   qué** y no se puede «arreglar» a la ligera.
2. **El aviso de yaw de `verificar_robot.sh` tiene una premisa falsa.** Dice «se esperaba ~0», y
   eso solo vale tras un encendido limpio del RVR. F0 lo informa sin traducirlo a nada.
   ⏳ Queda anotado como defecto a corregir en ese script, fuera del alcance de esta prueba.

📝 Si alguna vez quieres el origen limpio, hay que **apagar y encender el RVR**, no la Pi.

---

## Umbrales

**Todos salen de mediciones registradas en este repositorio. Ninguno es inventado.**

| Medida | Base medida | Fuente | Banda de aceptación |
|---|---|---|---|
| `/odom`, `/imu`, `/encoders` | 16.5 Hz | Fase 4 | ≥ 13 Hz |
| `/scan` | **10.1 · 11.84 · 12.00 Hz** | medido ×3 con el driver ROS 2 | 9.5–13 Hz |
| | ⚠️ *Una versión anterior citaba «9.997 Hz · σ 0.35 ms, manual cap. 12». Esa cifra es de `/prueba_atriz`, un topic **sintético** publicado a 10 Hz para probar DDS — no del LIDAR. El `/scan` real varía porque el motor del X2 **gira libre**.* | | |
| `move_timed` 2 s @ 0.15 m/s | **30.3 cm** (101 %) | evidencia 26 | 24–37 cm |
| `move_to_pos_and_yaw` 0.20 m | **19.5 cm** (97 %) | evidencia 26 | 16–24 cm |
| `collision_monitor` | **9.9 cm** @ 0.25 · 10.6 @ 0.40 | CHANGELOG:1824 | ≤ 15 cm |
| watchdog de `cmd_vel` | **527 ms · ~7.9 cm** | CHANGELOG:3303 | ≤ 12 cm |
| 🔴 Nav2, «error final» | **8 cm**; 9–10 en otra tanda | coherencia interna | ≤ 15 cm |

🔴🔴 **Y ESA FILA NO MIDE PRECISIÓN. Hay que leerla sabiéndolo.** El número sale de
`pos_mapa()`, que es la pose de **AMCL**: el robot juzgándose a sí mismo. Y el controlador
para cuando **cree** estar en tolerancia, así que tiende a la tolerancia por construcción —
de ahí que «8-10 cm» coincidiera con `xy_goal_tolerance: 0.10`. Eso no era una confirmación:
era circularidad.

Medido con cinta y trilateración el 2026-08-07 (evidencias 83 y 84), sobre un mapa rancio:

```
  lo que habría reportado esta fila    6,8 cm   → PASA ✅
  donde estaba el robot de verdad     41,3 cm   🔴
```

Y con el mapa bueno, dos tandas dieron **6,1 y 11,8 cm** reales — **con Nav2 diciendo
`SUCCEEDED` las tres veces**.

📌 **No se cambia la banda ni se convierte en FALLO**, y es deliberado: sería fingir que el
número mide algo que no mide. La prueba **avisa por pantalla** y remite al instrumento que sí
lo mide — `mediciones_banco/comparar_con_cinta.py`, con **dos** distancias de cinta.

⚠️ **Consecuencia para la flota:** esta prueba **no puede aceptar ni rechazar la precisión**
de un robot. Lo que sí verifica es el mecanismo: que Nav2 acepte, planifique y termine. La
precisión de cada aula se comprueba **una vez, con cinta**, al montarla.
| Nav2, meseta de velocidad | **0.407 m/s** · p90 0.412 | TRASPASO:293 | ≥ 0.35 m/s |
| Obstáculo, desvío lateral | **30 cm**, y vuelve al eje | manual 11.13 | 15–50 cm |
| Yaw en reposo (**deriva**, no valor) | **0.01° / 60 s** | medido 2026-08-01 | ≤ 0.5° |
| Umbrales de batería | baja 7.00 V · crítica 6.50 V | firmware | exactos |
| **Ángulos (F5)** — siempre **Δyaw** | **no hay** | — | banda de cordura; la primera pasada fija la base |

⚠️ **Casi todas son n=1 a n=4.** Por eso las bandas son anchas: un umbral que salta siempre no
vale nada, y uno que no salta nunca tampoco. Y por eso **salir de banda no es un suspenso**.

---

## El veredicto, en cuatro niveles

| | Significa | ¿Bloquea la Fase 5? |
|---|---|---|
| **FALLO** | Categórico: falta un nodo, un servicio no responde, el robot no se mueve, **la parada de emergencia no para**, Nav2 aborta, hay errores en el journal desde el arranque. Aquí no hay banda que valga: o funciona o no | **sí** |
| **REVISAR** | Funciona, pero el número se fue de banda. El informe dice cuánto y contra qué. Con n=1 detrás, llamar «suspenso» a un 20 % de desviación sería fingir una precisión que no tenemos | no por sí solo |
| **PASA** | Dentro de banda | no |
| **PENDIENTE** | Decisiones abiertas que ninguna ejecución cierra | **sí** |

**`✅ VÍA LIBRE PARA LA FASE 5` solo con cero FALLO y cero PENDIENTE.**

### Los PENDIENTE de hoy (2026-08-01)

1. 🔴 **rosbridge sin autenticación** en el 9090, exponiendo `raw_motors`, que se salta el
   `collision_monitor` y no tiene corte automático. Hay que decidirlo **antes** de escribir el
   cliente, porque cambia su arquitectura.
2. 🔴 **El hueco de los precipicios.** `collision_monitor` solo mira `/scan`, y un LIDAR 2D no ve
   un vacío a ninguna altura. Mitigado hoy solo por la regla de laboratorio (suelo continuo).
3. ⚠️ **La PSK del WiFi es legible** por cualquier usuario: falta `fmask=0177,dmask=0077` en
   `/etc/fstab`. `chmod` no sirve, es FAT.
4. ⚠️ **La credencial `sphero` sin rotar** y sin purgar del histórico de git.

📝 Esta lista se mantiene **en el propio script**, no aquí, para que no se queden desincronizados.
Este documento explica el criterio; el script lleva la cuenta.

---

## Cuando algo va mal

- **`Ctrl-C` en cualquier fase** → parada de emergencia por el camino canónico
  (`/emergency_stop`), **señal enmascarada durante la recuperación** y liberación al final.
  📝 Esto es la lección del 2026-08-01: `move_timed` corre **en el driver**, así que matar el
  cliente no para nada, y un segundo Ctrl-C durante la recuperación la abortaba a medias.
- **Una fase que revienta** → parada de emergencia, se marca FALLO, y **te pregunta si sigues** en
  vez de decidir sola.
- **Guarda de batería:** aborta por debajo de **7.0 V**, el umbral «baja» del firmware. Con la
  batería caída los motores dan menos y mediríamos una regresión que no existe.
- **Guarda de `/dev/rvr`:** si hay otro proceso hablando con el RVR, no arranca.
- **Timeout en toda llamada a servicio.** Una sola llamada sin tope cuelga la prueba entera en
  silencio — ya pasó con `get_battery_percentage()`.
- **SLAM y Nav2** se lanzan como subprocesos y se matan **por `comm`, nunca con `pkill -f`**.
- El informe se escribe **pase o falle**, en
  `00_auditoria/evidencia_24_04/47_aceptacion_<fecha>.txt`.

---

## Cómo se ejecuta

```bash
# 1. Reinicia el robot de verdad. F0 lo comprueba con el uptime.
sudo reboot

# 2. Espera a que vuelva y entra:
ssh sphero@rvr-01.local

# 3. Lánzala. Es guiada: se para y te dice qué hacer antes de cada fase física.
python3 ~/atriz_migracion/scripts/prueba_aceptacion.py

#    Retomar desde una fase concreta, sin repetir lo ya pasado:
python3 ~/atriz_migracion/scripts/prueba_aceptacion.py --desde F4
```

⚠️ **Necesitas el pasillo de siempre**: objetivos de 1.50 m y ~63 cm de holgura lateral para el
sorteo. Los umbrales están calibrados contra ese escenario, así que en otro sitio los números
**no son comparables** y REVISAR dejaría de significar nada.

⚠️ **Acciones físicas.** El robot se mueve en F4, F5, F6 y F7, y enciende LEDs en F3. Ten el
pasillo despejado y no te pongas delante.

---

## Cómo leer el informe

El informe se escribe **siempre**, pase o falle, en
`00_auditoria/evidencia_24_04/47_aceptacion_<fecha>.txt`, y la propia terminal imprime el mismo
texto al final. La cabecera dice de qué robot y cuándo:

```
==============================================================================
PRUEBA DE ACEPTACION · rvr-01 · 2026-08-02 14:10:16
==============================================================================
```

Después va una sección por fase (`── F8 ──…`), con una línea por comprobación y su icono:

```
── F8 ──────────────────────────────────────────────────────────────────────
  [OK   ] rosbridge completa el handshake WebSocket
          HTTP/1.1 101 Switching Protocols
Server: TornadoServer/6.4
  [OK   ] la web recibe /odom por rosbridge
          suscripcion real, no solo el puerto abierto
```

Los cuatro iconos son los cuatro niveles de siempre — `OK` (PASA), `REV` (REVISAR), `FALLO` y
`PEND` (PENDIENTE) — y significan exactamente lo que dice la tabla de «El veredicto» de más
arriba. La línea sin sangría es el concepto comprobado; la línea sangrada, si la hay, es el
detalle: el número medido y su banda, el mensaje de error, o por qué algo quedó sin verificar.

Al final va el recuento y el veredicto, en ese orden:

```
==============================================================================
  2 PASA · 0 REVISAR · 0 FALLO · 4 PENDIENTE
==============================================================================

  🔴 NO HAY VIA LIBRE PARA LA FASE 5

     Lo que lo impide:
       · [PENDIENTE] rosbridge sin autenticacion en el 9090
       · [PENDIENTE] el hueco de los precipicios
       · [PENDIENTE] la PSK del WiFi es legible por cualquier usuario   ← ✅ YA NO
       · [PENDIENTE] la credencial sphero sin rotar                     ← ✅ YA NO
==============================================================================
```

(Salida real de `python3 -u scripts/prueba_aceptacion.py --desde F8 --sin-puertas`, 2026-08-02 —
por eso solo aparecen F8 y F9: no repite lo ya pasado.)

**Lo único que importa para decidir si se puede empezar la Fase 5 es esa línea `VIA LIBRE` /
`NO HAY VIA LIBRE`.** Sale de `hay_via_libre()`: cero `FALLO` y cero `PENDIENTE`, sin excepción.
Un `REVISAR` **no** aparece en «lo que lo impide» — puede haber decenas y seguir habiendo vía
libre, porque es un número fuera de banda con n=1 a n=4 detrás, no un «no funciona». Si hay algún
`REVISAR`, el informe los lista aparte, al final, bajo «Y N número(s) fuera de banda»: para
mirarlos, no para bloquear por ellos.

📝 Los cuatro `PENDIENTE` de F9 (`PENDIENTES_CONOCIDOS` en `aceptacion_nucleo.py`) **aparecen
siempre**, en cualquier corrida, aunque el robot esté impecable — son decisiones abiertas que
ninguna ejecución cierra, no algo que esta prueba pueda medir. Que bloqueen la vía libre es el
comportamiento acordado el 2026-08-01, no un fallo de la prueba ni del robot.


---

## 🔴 El hueco del obstáculo de F7 son 60 cm medidos, no «unos 60»

El **único FALLO** de la corrida del 2026-08-08 fue el objetivo con obstáculo. Se midió el
2026-08-09 (evidencias 90 y 91) y la causa es geométrica, no un defecto:

**El mapa engorda los objetos ~5 cm por lado.** Un hueco físico de 45 cm entra en el mapa como 35;
inflando el radio inscrito (14,5 cm) desde cada borde queda **una celda a coste 96**, y en la fila
exacta del obstáculo **ninguna**. NavFn entonces no aprieta: **traza un rodeo** de 168-233 % de
largo, que en un cuarto de 3,8 × 4,2 m no cabe. El rodeo roza la inflación, el controlador ve
colisión y `failure_tolerance: 0.3` mata el objetivo en tres décimas.

```
hueco mínimo ≈ 2 × (14,5 inscrito + 5 engorde del mapa + 5 celda) ≈ 49 cm
con 60 cm el plan sale RECTO — única tanda que lo hizo, 14 cm de desvío
con 45 y con 34 cm RODEA siempre
```

✅ **Y se comprueba antes de gastar la tanda, sin mover el robot:**

```bash
python3 00_auditoria/evidencia/mediciones_banco/consultar_plan.py --meta 1.4 --repetir 3
```

Le pregunta la ruta a Nav2 con `compute_path_to_pose`. Si dice **RODEA**, el montaje está mal y la
tanda va a fallar: ensancha el hueco antes de mover nada.

### El obstáculo va sobre el rumbo del robot **de ese momento**, no el de partida

Lo preguntó el usuario el 2026-08-09: *«el robot quedó torcido, ¿el obstáculo va delante de este
nuevo POV o del inicial con el que empezó F7?»*. **Del nuevo.** El objetivo con obstáculo se manda
con `absoluta=None`, o sea calculado sobre la pose leída **en ese instante**.

Y quedar torcido **es esperable, no un fallo**: `yaw_goal_tolerance: 0.25` rad = **14,3°** de
margen en el regreso. El guion ya tenía anotado un caso de «regreso a −10° con la partida en +1°».

🔎 **A 0,75 m, 11° desplazan «delante» 14 cm de lado.** Con el hueco de 60 cm se aguanta; con 45 el
robot ya no apunta al hueco y la tanda **mide otra cosa sin avisar**.

✅ Desde el 2026-08-09 el guion **imprime el rumbo tras el regreso y el desvío respecto a la
partida** justo antes de pedirte el montaje, y si pasa de 5° te dice cuántos centímetros de lado
son. Alinea el hueco con el **eje del robot**, mirándolo de frente.

### Alcance: esto vale con SLAM — que es justo lo que lanza F7

Con **AMCL sobre un mapa que NO contiene los objetos**, un hueco de 45 cm **sí pasa**: medido dos
veces (evidencia 90 y su repetición en la 91), plan recto al 109 % con 13 cm de desvío. La razón,
en la misma fila y la misma escena:

```
línea de la puerta (x=85 cm), lateral -40..+40, mismos 45 cm
  con AMCL    99  99  99 100  99  99  99 | 84  84 | 99  99  99 100 ...   canal ABIERTO
  con SLAM   100  99  99 100 100 100  99   99  99   99  99  99 100 ...   canal CERRADO
```

Con AMCL la puerta la marca **sólo la capa de obstáculos del LIDAR**, fina y exacta. Con SLAM entra
en la **capa estática** ya engordada. **F7 lanza SLAM, así que el umbral de F7 son los 60 cm.**

⏳ **Sin verificar, y es la casilla del aula:** AMCL sobre un mapa que **sí** contiene los objetos.
Los mapas del aula se hacen con slam_toolbox y se guardan, así que lo que estuviera puesto al
mapear entra ya engordado en el fichero. **Predicción: se comportará como SLAM.**

📌 Para la imagen dorada: **esto no depende del robot**, así que los 16 aplicarán el mismo umbral.
