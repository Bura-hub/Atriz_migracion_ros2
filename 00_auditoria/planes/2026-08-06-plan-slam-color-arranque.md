# Plan único — color en caliente, SLAM que no queda mudo, y que la web se entere sola
**Fecha: 2026-08-06 · Cubre A9 (color en caliente), A10 (arrancar SLAM desde la web) y la recuperación tras apagar el RVR**

> ## ⚠️ SUPERADO EN LA PARTE DEL COLOR — el mismo día, por la tarde
>
> **A9 está hecho y verificado.** El servicio `/enable_color` (`std_srvs/SetBool`) existe, funciona
> en caliente y está en la lista blanca; `EstadoRobot` tiene `color_activo`; y la luz se apaga sola
> por inactividad y por tope duro. Evidencias **76** y **77**.
>
> 🔴 **Y la fila de abajo que dice «este proyecto YA INTENTÓ el servicio `enable_color` y lo
> declaró imposible» citaba una afirmación FALSA.** No estaba medida: el servicio de julio hacía
> `enable(True) → leer → enable(False)` dentro de la misma llamada, así que los 481 mensajes eran
> casi todos posteriores al apagado. La medida no distinguía las dos hipótesis.
>
> Se deja el plan entero sin tocar porque **su parte de SLAM y de recuperación sigue vigente**, y
> porque razonó bien sobre premisas malas — que es justo lo que conviene poder releer.
>
> 📌 Lo que sí acertó de lleno, y hay que reconocerlo: la fila de `stop()`/`clear()` y la de
> `_recuperar_streaming` describían el mecanismo correcto. La conclusión falsa no venía del
> análisis, venía de fiarse de un comentario del código.

Este plan sale de cuatro análisis y sus cuatro refutaciones. **Donde el escéptico tumbó algo, gana el escéptico** y lo digo abajo. Donde dos análisis se contradicen, lo dejo escrito como contradicción abierta y no elijo.

He comprobado a mano en los tres repositorios lo que aparece en el apartado 1. Lo que no pude comprobar desde Windows va en el apartado 2 con su comando.

---

## 1 · Lo que está VERIFICADO

### 1.1 · El sensor de color

| Hecho | Evidencia |
|---|---|
| `stop()` **NO** borra los manejadores de usuario (solo vacía `__enabled_sensors`); `clear()` **sí** los borra. Por eso un `stop()`/`start()` no exige re-registrar nada, y re-registrar duplicaría cada muestra | `sphero_sdk/common/sensors/sensor_streaming_control.py:136-145` (stop) y `:147-161` (clear) |
| `start()` sale en seco si ya hay sensores activos, y `stop()` sale en seco si no hay ninguno. El par solo es idempotente si el estado del SDK coincide con el del robot | `sensor_streaming_control.py:110-112` y `:140-142` |
| Los cinco métodos de `SensorControlAsync` **encolan con `ensure_future`**: `await sc.stop()` vuelve antes de que salga un byte | `sphero_sdk/asyncio/controls/sensor_control_async.py:35, 48, 57, 66, 73` |
| El driver **ya hace `stop()`→`start()` en caliente** y funciona con el RVR vivo: es `_recuperar_streaming`, el remedio del RVR dormido | `rvr_driver_node.py:1168-1214` |
| 🔴 **Este proyecto YA INTENTÓ el servicio `enable_color` y lo declaró imposible.** El driver de ROS 1 lo tenía (`rospy.Service('enable_color', std_srvs.srv.SetBool, …)`) y las notas del driver de ROS 2 lo listan como **«🔴 MEDIDO: NO PUEDE FUNCIONAR como servicio»** | ROS 1: `atriz_rvr_driver/scripts/Atriz_rvr_node.py:331` y `:1641`. ROS 2: `rvr_driver_node.py:2779-2782` |
| Y el `.srv` de `ConfigureStreaming` y `StartStreaming` **sigue vivo y compilándose**, con su razón de estar diferido escrita | `atriz_rvr_msgs/srv/ConfigureStreaming.srv`, `StartStreaming.srv`; razón en `rvr_driver_node.py:2775-2778` |
| **NO existe `add_on_set_parameters_callback` en el driver.** `declare_parameter('color_detection', False)` está en `:242` y `self._color_detection` se copia una sola vez en `:257`. Un `set_parameters()` movería el almacén de rclpy y **dejaría el atributo intacto** | `rvr_driver_node.py:242`, `:257`; grep de `add_on_set_parameters_callback` sobre el fichero completo: **cero coincidencias** |
| `_srv_rgbc` decide su `message` leyendo **el atributo**, no el parámetro | `rvr_driver_node.py:2231-2233` |
| Ya existe banco para esto: `medir_sensor_color.py` hace tres tandas, consulta el RGBC con el driver parado, prueba varias esperas de asentamiento, y **documenta el (3, 3, 0, 4)** de la primera versión del servicio | `00_auditoria/evidencia/mediciones_banco/medir_sensor_color.py:36-40` |
| ⚠️ Por tanto **es falso que «nadie miró el RGBC durante aquella prueba»**. Sí se miró, y dio oscuridad. Lo que faltó fue la espera de asentamiento | `rvr_driver_node.py:2213-2214` + el fichero anterior |

**Refutación que se mantiene y que corrige el análisis:** el hallazgo «hay que mover el PARÁMETRO ROS, no el atributo» es **falso como está escrito**. Hay que mover **los dos**, o `/get_rgbc_sensor_values` seguirá diciendo «el sensor está APAGADO» sobre un sensor encendido — el mismo fallo silencioso que se venía a evitar, mudado de sitio.

### 1.2 · systemd, SLAM y la navegación

| Hecho | Evidencia |
|---|---|
| `atriz-nav.service` usa **`BindsTo=atriz-robot.service` + `After=`**, `Restart=on-failure`, `ExecStartPre=/usr/local/bin/atriz-escaneo on` **sin `-`**, y `ExecStopPost=-/usr/local/bin/atriz-escaneo off` | `atriz_migracion/scripts/atriz-nav.service:28-29, 54, 64, 84` |
| Consecuencia: si la propagación ocurre, un reinicio del driver **para la navegación y no la devuelve** (`on-failure` no dispara ante un paro que systemd ordenó) y **apaga el barrido** de camino | mismas líneas |
| **`PartOf=` NO está en ninguna unidad del proyecto.** Cualquier experimento que lo pruebe está probando una directiva que no está en el fichero | grep sobre `atriz_migracion/scripts/*.service` |
| **No existe `atriz-slam.service`.** SLAM solo se lanza a mano por SSH | `fase_7_systemd.sh` instala robot y nav, nada más |
| `slam.launch.py` **ya declara `autostart`** (`default_value='true'`), `LifecycleNode`, `use_lifecycle_manager: False` y los dos `EmitEvent` condicionados a `autostart` | `Atriz_rvr/atriz_rvr_bringup/launch/slam.launch.py:86-92, 97, 108, 113-136` |
| 🔴 `localizacion.launch.py` decide si SLAM corre mirando **el PROCESO** (`ps -eo comm` contra `async_slam_tool`) y aborta con `RuntimeError`. Un slam_toolbox residente-inactivo **bloquearía `atriz-nav` siempre** | `localizacion.launch.py:67, 70-78, 82-97` |
| 🔴 **Y `slam.launch.py` NO tiene guardia en la dirección contraria**: nada impide dos slam_toolbox publicando `map → odom` a la vez | grep de `_slam_vivo` / `RuntimeError` sobre `slam.launch.py`: **cero coincidencias** |
| El driver **NO muere cuando el RVR se apaga**: `_recuperar_streaming` envuelve todo en `try/except` y libera el guardia en un `finally`; reintenta indefinidamente. Medido el 2026-08-02: 123 reintentos, 8 «streaming reanudado» en 30 s, con el proceso vivo | `rvr_driver_node.py:1194-1210`; `00_auditoria/evidencia_24_04/52_reanudar_que_no_reanuda.txt` |
| 🔴 **Y eso desmiente la explicación «la Pi se reinició entera».** Si apagar el RVR reiniciara la Pi, la evidencia 52 no existiría | mismas fuentes |
| 🔴 **`_recuperar_streaming` reinicia `_t_ultima_muestra` DESPUÉS del `start()`, sin que haya llegado un dato.** Es exactamente el fallo que la evidencia 52 denunció, dentro del código escrito para detectarlo | `rvr_driver_node.py:1188-1190` |
| **No hay ningún fichero de evidencia del 2026-08-06.** La numeración llega a `75_navegador_por_nombre.txt` (2026-08-04). Los números del incidente viven **solo** en el plan y copiados en un docstring de la web | `ls 00_auditoria/evidencia/` y `evidencia_24_04/` |

### 1.3 · La web

| Hecho | Evidencia |
|---|---|
| `reinicio.ts` **no lo importa nadie** y es el único fichero de `lib/robot/` **sin `.test.ts`** (`mapa`, `no_obedece` y `origen_odometria` sí lo tienen) | grep de `robot/reinicio`, `trasLatido`, `SIN_REINICIOS` en todo `frontend/src`: solo su propia declaración |
| 🔴 **`latidoPrevio` está cableado hasta el muro y NO SE COMPARA NUNCA.** Se calcula en `BaldosaConectada.tsx:58-72` y `useResumenRobot.ts:72-86`, viaja por `lecturas.ts:129, 163, 173`, se declara en `resumen.ts:72` con seis líneas explicando que es lo único que prueba que hay alguien detrás… y **`resumirBaldosa()` no lo lee**: decide con `paradaEmergencia`, `rvrResponde` y las dos antigüedades | leído entero `resumen.ts:195-245` |
| El robot **no ofrece nada para arrancar SLAM**: `SERVICIOS` son ocho y ninguno toca systemd ni ciclo de vida | `robot.launch.py:344-347` |
| La web tiene su **propia lista blanca** y **lanza antes de mandar nada** si el servicio no está: `contrato.ts:18-21` + `permitidoLlamar()`. Y `herramientas/comprobar_contrato.mjs` cruza los dos ficheros — «si divergen, gana el robot» | `contrato.ts:1-6, 18-21`; `protocolo.ts:96-98` |
| Por tanto **añadir un servicio son TRES ficheros y un comprobador**, no una línea en el launch | mismas fuentes |
| `params_glob: '[]'` — la web **no puede leer ningún parámetro ROS**, y `/rvr_driver/get_parameters` no está en `SERVICIOS`. Una pestaña recién abierta **no tiene forma de saber** si el color está encendido | `robot.launch.py:363` (bloque de `puente`) |
| `rvr_responde` se calcula a 1 Hz **sin consultar `_recuperando`**, con umbral `_timeout_silencio` (3 s) | `rvr_driver_node.py:1945-1946` frente a `:1124-1125` |
| 🔴 **Un reinicio del driver baja la parada de emergencia**: `self._parada_emergencia = False` en el constructor. Un robot que un humano había dejado detenido vuelve a aceptar `cmd_vel_raw` sin que nadie lo decida | `rvr_driver_node.py:266` |

**Refutaciones que se mantienen:**
- **`medir_ritmo_ros2.py --topic /odom` no existe.** El script solo declara `--seg` (`:77`). El comando aborta con «unrecognized arguments» y no mide nada.
- **«barrido en OFF ⇒ se reinició el servicio» no es exclusivo.** `/stop_scan` está en la lista blanca (cualquier pestaña lo apaga) y `atriz.py` lo apaga al cerrar por seis caminos. Con 16 alumnos, barrido apagado es el estado normal al final de un ejercicio.
- **`/map` no sirve como indicador de que SLAM está encendido.** Va a 0,200 Hz (`slam_toolbox_atriz.yaml:63`, `map_update_interval: 5.0`), llega latcheado a un suscriptor nuevo aunque el publicador esté desactivado (la trampa del latch que la propia web tiene escrita y prohibida en `teleoperacion.ts:390` y `resumen.ts:68`), **y `map_server` de AMCL publica el mismo topic** (`localizacion.launch.py:110-112`). Un umbral de 1 s pintaría «SLAM apagado» el 96 % del tiempo con SLAM sano.

---

## 2 · Lo que NO está verificado, y el comando exacto para medirlo

Todo esto exige el robot. Nada de lo de abajo debe darse por cierto hasta que salga en pantalla.
**Sitio de la evidencia:** `atriz_migracion/00_auditoria/evidencia/76_…`, `77_…` etc., en el mismo commit que la conclusión.

### M1 · ¿El `enable_color_detection` con el stream montado enciende el LED o no? (separa las dos explicaciones)

Es la pregunta que decide todo el alcance de A9, y **no hay que escribir una línea de servicio antes**. Las dos explicaciones encajan con la medida de 2026-07-31 (481 mensajes a cero):
**(a)** el comando se ignora por completo · **(b)** el módulo y el LED sí se encienden, pero el servicio de streaming quedó ligado a una fuente muerta.

```bash
sudo systemctl stop atriz-robot
cd ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco
python3 medir_sensor_color.py           # ya hace las tres tandas y prueba varias esperas
```
Y **extender ese mismo script** (no escribir uno nuevo: ya hay dos bancos que miden esto, `medir_sensor_color.py` y `probar_sensor_optico.py`) con una tanda 4:

1. `add_sensor_data_handler(ColorDetection)` + `sensor_control.start(60)` **sin** enable → contar muestras 3 s (deben ser ceros).
2. `enable_color_detection(True)`, **esperar 1 s**, `get_rgbc_sensor_values()` y contar muestras otra vez.
3. 👤 **Y mirar el robot**: ¿se enciende el LED blanco bajo el chasis? El ojo de quien tiene el robot delante es el instrumento que manda.
4. `sensor_control.stop(); await asyncio.sleep(0.1); enable_color_detection(True); await asyncio.sleep(0.1); start(60)` → ¿dejan de ser cero las muestras?
5. Marcar el instante de la última muestra antes del stop y de la primera después del start → **ese es el hueco**, que nadie ha medido nunca.

| Resultado | Qué significa |
|---|---|
| LED **sí** + `clear` sube + muestras a cero | explicación **(b)** — el LED ya se puede encender hoy sin tocar el stream, y A9 es más pequeño de lo que parece |
| LED **no** + `clear` no sube | explicación **(a)** — hace falta el `stop`/`start` |
| paso 4 devuelve muestras no nulas | **la conmutación en caliente funciona** |

### M2 · El orden real en el cable (contradicción abierta, ver §3)

Dentro del mismo script de M1:
```python
import logging; logging.getLogger('sphero_sdk').setLevel(logging.DEBUG)
```
y leer el orden de las líneas `Writing serial data: [...]` entre `sensor_control.stop()` y `enable_color_detection()`.

### M3 · ¿Cuánto dura el hueco de telemetría, y qué le hace al muro?

⚠️ **`medir_ritmo_ros2.py` NO tiene `--topic`.** El comando correcto:
```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_ritmo_ros2.py --seg 40
```
y a mitad de la ventana, desde otra terminal, disparar la conmutación. **El dato es el HUECO MÁXIMO, no la media.** Si pasa de 3,0 s, `rvr_responde` se pone en `false` (`rvr_driver_node.py:1945`) y el muro del profesor pinta ese robot caído mientras un alumno enciende el color.

### M4 · ¿Qué hace `slam.launch.py autostart:=false`? (🔴 **contradicción abierta, ver §3**)

La medida que existe (`evidencia_24_04/11_slam_fase4.txt:13`) dice literalmente **«Con un `Node` normal en el launch:»** — es decir, se midió **antes** de que existieran `LifecycleNode`, `autostart` y `use_lifecycle_manager`. **`autostart:=false` no se ha ejecutado nunca.**

```bash
sudo systemctl stop atriz-nav 2>/dev/null
ros2 launch atriz_rvr_bringup slam.launch.py autostart:=false
# en otra terminal:
ros2 lifecycle get  /slam_toolbox                 # ¿unconfigured [1] o active [3]?
ros2 lifecycle list /slam_toolbox                 # ¿qué transiciones admite?
ros2 topic info /scan --verbose | grep -i subscription
ros2 service list | grep slam_toolbox
```
Y el coste permanente, que decide si esto es viable en 16 robots. **No uses `ps -o %cpu`** (da el promedio desde el arranque):
```bash
P=$(ps -eo pid,comm | awk '$2=="async_slam_tool"{print $1}')
grep VmRSS /proc/$P/status
A=$(awk '{print $14+$15}' /proc/$P/stat); sleep 20; B=$(awk '{print $14+$15}' /proc/$P/stat)
echo "fraccion de nucleo: $(echo "($B-$A)/2000" | bc -l)"
```

### M5 · ¿Se recupera slam_toolbox sin matarlo?

```bash
ros2 lifecycle set /slam_toolbox deactivate
ros2 lifecycle set /slam_toolbox cleanup
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```
🔴 **El testigo no puede ser «el mapa crece»**: un `cleanup` que borre el grafo y un `configure` que empiece de cero pasan ese test perfectamente, y encima tras un reinicio del driver el marco `odom` volvió a cero, así que el mapa **crecería mal**. El criterio es la **coherencia geométrica contra algo externo** (una pared conocida, o `referenciar_posicion.py`), después de **desplazar** el robot ~1 m — girar sobre el eje no hace crecer el mapa nunca.

### M6 · ¿Qué pasó de verdad el 2026-08-06?

Todavía se puede saber si no ha habido reinicio desde entonces:
```bash
systemctl show atriz-robot -p NRestarts -p ExecMainStartTimestamp --value
uptime -s
journalctl --list-boots | tail -3
journalctl -u atriz-robot --since "2026-08-06" | grep -nE "Started|Stopped|Main process exited|rvr_driver arrancando"
journalctl -u atriz-robot --since "-6h" | grep -c 'streaming reanudado'
```
⚠️ `--since "-6h"`, **nunca** `$(date -u +%T)`: en este robot (UTC−5) esa ventana cae cinco horas en el futuro y cuenta 0.

### M7 · ¿Un reinicio del driver tira de verdad el WebSocket?

Leído en el launch (`robot.launch.py:192` `on_exit=Shutdown()`, `:351-354` el nodo `puente` en el mismo `LaunchDescription`), **no medido por su efecto**.
```bash
systemctl show atriz-robot -p NRestarts --value
ps -eo pid,comm | awk '$2=="rvr_driver_node"{print $1}' | xargs -r kill -TERM
```
🔴 **NO uses `pkill -f rvr_driver_node`: mata tu propia terminal.** Ha pasado dos veces.
Desde el navegador tiene que verse `onclose` y la reconexión; `NRestarts` sube en 1.

### M8 · ¿Salta `/odom` si el RVR se apaga y enciende con el driver VIVO?

Es el modo de fallo que **ningún indicador de hoy ve**: `_yaw_offset` se fija una sola vez (`rvr_driver_node.py:1541-1547`) y solo se anula en `set_pos_and_yaw` (`:2503`); `reset_locator_x_and_y()` solo se llama al conectar (`:860`). El latido no retrocede.
```bash
ros2 topic echo /odom --once            # anotar pose y orientación, robot QUIETO
# apagar el RVR, esperar 30 s
ros2 topic echo /estado_robot --once    # reanudaciones_fallidas debe haber subido
# encender el RVR, esperar a que /odom vuelva — SIN MOVER EL ROBOT
ros2 topic echo /odom --once
ros2 topic echo /estado_robot --once    # latido grande y continuo = el driver NO se reinició
```
⚠️ **Que el apagado del RVR ponga a cero el LOCATOR es DEDUCCIÓN.** Lo medido es que el **yaw** se pone a cero al encender. Hay que medir las dos cosas.

### M9 · ¿Recibe un cliente nuevo de rosbridge el valor latcheado de `/estado_robot`?

Decide si el `latidoPrevio` del muro protege de algo. Desde el navegador, con el robot sano: abrir una segunda pestaña y **cronometrar** el primer `/estado_robot`. `<100 ms` = el latch llega; `~1 s` (el siguiente tic) = no llega. **Tres tomas**: la entrega TRANSIENT_LOCAL ya se midió intermitente (2 de 3 fallos).

### M10 · La propagación de systemd, y en los DOS caminos

El plan del 2026-08-06 propone probar con `systemctl restart`. **Ese es el camino equivocado**: en el incidente nadie escribió `restart`, fue `Restart=always` reviviendo un proceso muerto, que es un camino distinto (`RestartMode=`, systemd 254+, documenta esa esquina). Con unidades de juguete, **sin tocar el robot**:

```bash
sudo tee /etc/systemd/system/p-base.service >/dev/null <<'EOF'
[Unit]
Description=base
[Service]
ExecStart=/bin/sleep infinity
Restart=always
RestartSec=1
EOF
for D in Requires BindsTo PartOf; do sudo tee /etc/systemd/system/p-$D.service >/dev/null <<EOF
[Unit]
Description=$D
$D=p-base.service
After=p-base.service
[Service]
ExecStart=/bin/sleep infinity
EOF
done
sudo systemctl daemon-reload

# CASO 1 · reinicio explícito
sudo systemctl start p-base p-BindsTo
systemctl show p-BindsTo -p ExecMainStartTimestamp --value
sudo systemctl restart p-base; sleep 3
systemctl is-active p-BindsTo; systemctl show p-BindsTo -p ExecMainStartTimestamp --value

# CASO 2 · el que de verdad pasó: auto-reinicio tras una muerte
sudo systemctl start p-base p-BindsTo
systemctl show p-BindsTo -p ExecMainStartTimestamp --value
sudo kill -9 $(systemctl show p-base -p MainPID --value); sleep 5
systemctl is-active p-BindsTo; systemctl show p-BindsTo -p ExecMainStartTimestamp --value
systemctl show p-base -p NRestarts --value

# limpieza
sudo systemctl stop p-base p-Requires p-BindsTo p-PartOf
sudo rm /etc/systemd/system/p-*.service && sudo systemctl daemon-reload
```
**Lectura:** `active` + timestamp cambiado = volvió · `active` + timestamp igual = ni se enteró · `inactive` = se paró y no volvió.
⚠️ `is-active` **no basta**: da `active` en dos de los tres casos.

---

## 3 · Contradicciones abiertas — no elijo

**C1 · El orden en el cable del `stop()` + `enable`.** El análisis del color afirma (marcado `verificado: true`) que la secuencia obvia manda **el ENABLE primero y el CLEAR después**, «reproduciendo el orden que no funciona». El escéptico confirma el mecanismo (`ensure_future` encola; `enable_color_detection` escribe en el acto) pero señala que la conclusión **apunta al revés**: el cable vería `ENABLE → CLEAR → CONFIGURE → START`, que es enable **antes** de la reconfiguración, o sea el orden **documentado como bueno**. Las dos lecturas del mismo código son coherentes. **Lo zanja M2, mirando los bytes.** Hasta entonces no se escribe el servicio.

**C2 · Qué hace `autostart:=false`.** El análisis de arranque lo marca `verificado: true` citando `evidencia_24_04/11_slam_fase4.txt`. Ese fichero dice en su línea 13 **«Con un `Node` normal en el launch:»** — no es la misma configuración. Y la semántica de `use_lifecycle_manager: False` no está respaldada por ningún código de estos tres repositorios (el fuente de slam_toolbox viene de apt). **P1 entero de ese análisis descansa sobre esto. Lo zanja M4.**

**C3 · Qué significaban los 265 msg/16 s de `/tf` del 2026-08-06.** El análisis de systemd concluye que slam_toolbox estaba **muerto entero** (16,56 Hz = el ritmo del driver a solas; con SLAM serían ~67). La aritmética es correcta y confirmé sus dos piezas (`transform_publish_period: 0.02` en `slam_toolbox_atriz.yaml:60`; el driver emite un TF por `/odom`). Pero: **(i)** no consta con qué instrumento se contó y este proyecto lleva seis casos de «el instrumento miente»; **(ii)** la premisa de que slam_toolbox siga publicando TF sin barridos está marcada `verificado: false` por el propio análisis; **(iii)** hay una **tercera** explicación que no enumera y que es una trampa ya catalogada: slam_toolbox en `unconfigured` — proceso vivo, cero TF, cero `/map`, `Subscription count: 0`, ni un error (`slam.launch.py:18-27`). **Encajan tres. El dato es que encajan tres.**

**C4 · El latch de `/map`.** El plan del 2026-08-06 dice «~40 ms cuando hay mapa»; CLAUDE.md dice que un suscriptor VOLATILE **no** recibe el último mapa y espera hasta 5 s. Ninguna de las dos frases dice con qué QoS se midió. **Y hay una segunda contradicción sobre el mismo topic:** el plan mide «/map 0 mensajes en 16 s» con SLAM vivo, mientras CLAUDE.md describe el mismo fallo como «el mapa sale **idéntico celda a celda**» — es decir, publicando.

**C5 · El QoS con que rosbridge se suscribe.** `transporte.ts:259-260` afirma que «rosbridge infiere el QoS mirando los publicadores al suscribirse»; CLAUDE.md afirma que sin campo `qos` usa `qos_profile_sensor_data` (BEST_EFFORT + VOLATILE). De cuál sea cierta depende si el `latidoPrevio` del muro protege de algo real. El fuente de rosbridge no está en estos repos. **Lo zanja M9, que mide el efecto y no la semántica.**

**C6 · El marco de la web, ¿se desmonta al cambiar de robot?** El análisis de detección lo marca `verificado: true` y **P2 entero descansa en ello**. El código dice lo contrario de lo que haría falta: `MarcoRobot.tsx:236` renderiza `<ProveedorRobot robot={…}>` **sin `key`**, y `layout.tsx` es el mismo componente para los 16 ids — React reconcilia, no desmonta. Lo que sí tiene frontera es el `Transporte` (`useMemo(..., [url, fabrica])`). **Consecuencia si se ignora:** el `latidoPrevio` del robot 1 se compara con el `latido` del robot 2 y la web anuncia un reinicio que no ocurrió, en el robot equivocado. **El arreglo es de una línea: atar el estado a la identidad del `transporte`, o `key={url}` en el proveedor.** No hace falta medir nada: se lee.

---

## 4 · Las decisiones que tienes que tomar

### D1 · ¿Se toca el driver para el color en caliente (A9)?

| Opción | Coste | Qué pasa |
|---|---|---|
| **(a) Medir M1+M2 y decidir después** | 15 min de robot, sin mover nada, `sudo systemctl stop atriz-robot` | Si sale (b), puede que el LED ya se encienda hoy y A9 sea trivial |
| (b) Escribir `/set_color_detection` ya | ~90 líneas en el driver + 3 ficheros en la web + recompilar | Se diseña sobre una medida que **solo miró el topic**, con el propio driver diciendo `🔴 MEDIDO: NO PUEDE FUNCIONAR` (`:2779`) |
| (c) No hacerlo, y quitar el LED de la ecuación | 0 | `color_detection:=true` en el launch sigue siendo la única vía; el material docente sigue mandando al profesor por SSH |

**RECOMENDACIÓN: (a).** El motivo no es prudencia genérica: **este proyecto ya escribió ese servicio en ROS 1 y lo retiró documentando que no funciona.** Volver a escribirlo sin medir sería la tercera vez que se rediseña algo que el repositorio ya intentó — la misma forma exacta del error del seguidor de línea. Y M1 cuesta 15 minutos.

Y si M1 dice que se puede: **el servicio no puede prometer el efecto en 5 s**. `g_srv` es `MutuallyExclusiveCallbackGroup` (`:640`), `_pedir` tiene 5,0 s de plazo (`:773`), la web llama con `ms = 5000` (`transporte.ts:552`) y el `default_call_service_timeout` de rosbridge son 5,0 s. Un servicio que hace 0,2 s de sleeps + hasta 2 s esperando muestras + hasta 5 s de RGBC **se pasa del plazo y la web daría timeout sobre una conmutación que sí ocurrió**. Hay que diseñarlo para caber, y **mientras corre ningún otro servicio de ese robot responde** (`set_leds`, `get_encoders`, `set_pos_and_yaw`… todos en `g_srv`).

### D2 · ¿SLAM residente-inactivo en los 16 robots, o unidad que arranca el proceso?

| Opción | Coste | Riesgo |
|---|---|---|
| **(a) Nada residente. `atriz-slam.service` que se instala y NO se habilita, y A10 espera** | ~1 h de unidad + 3 sitios en `fase_7_systemd.sh` (`--quitar`, comprobaciones, instalación) | La web sigue sin poder arrancar SLAM. Honesto |
| (b) Residente con `autostart:=false`, encendido por ciclo de vida | ~40 líneas + **arreglar `_slam_vivo()` antes o a la vez** | 🔴 **Rompe `atriz-nav.service` de forma determinista** (`localizacion.launch.py:70-78` mira el proceso). Y descansa en C2, que no está medido |
| (c) `sudo` acotado + `systemctl start` desde un nodo ROS | menos líneas | 🔴 Convierte «cualquiera en la red llama a un servicio» en «cualquiera en la red hace que **root** arranque un proceso», sobre un rosbridge que **no tiene autenticación** (`check_origin()` devuelve `True` incondicionalmente) |

**RECOMENDACIÓN: (a) hoy, y (b) solo si M4 sale bien Y se arregla `_slam_vivo()` Y se mide el coste residente.** Tres razones concretas:
1. **La suposición central de (b) está sin medir** (C2): `autostart:=false` no se ha ejecutado nunca.
2. **Copiar `atriz-nav.service` arrastra su `ExecStartPre=atriz-escaneo on`**, y con la unidad habilitada eso son **11,8 Hz de X2 permanentes 24/7 en 16 robots** en vez de 2,7 — exactamente la decisión que el proyecto tomó al revés. Y si se le quita, se cae en el otro modo de fallo: **SLAM `active` sin `/scan` = suscrito, sin recibir un barrido, sin publicar y sin un solo error.** `atriz-nav.service:46-54` lleva esa salvaguarda escrita, **sin `-`**, precisamente por esto; ninguna de las propuestas la replica.
3. La razón «mapear es un acto de operador, igual que Nav2» **no traslada**: `atriz-nav` no está habilitada porque Nav2 cuesta ~58 % de núcleo y sale de la batería del RVR; **SLAM cuesta 4,8 %**, doce veces menos. La conclusión puede seguir siendo la buena, pero por sus otras razones.

**Y en cualquiera de las dos: `Conflicts=` NO.** Hoy arrancar la navegación con SLAM vivo lanza un `RuntimeError` de ocho líneas con el comando para pararlo (`localizacion.launch.py:82-97`). Con `Conflicts=`, systemd **para slam_toolbox sin decir una palabra**: quien lleve veinte minutos mapeando pierde el mapa y nadie se entera. Cambiar un fallo ruidoso por uno silencioso es la dirección contraria a la de este proyecto. Lo que sí falta es el guardia que **no existe**: `slam.launch.py` no comprueba si ya hay un slam_toolbox corriendo, y con una unidad **más** el SSH habrá dos caminos y dos slam_toolbox publicando `map → odom` sin ningún error.

### D3 · ¿Qué dice la web cuando el driver se reinicia, y dónde?

| Opción | Coste | Qué gana |
|---|---|---|
| **(a) Cinta en `MarcoRobot`, atada a la identidad del `Transporte`, con las CUATRO pérdidas y acuse por reinicio** | ~60 líneas de React + pruebas de la parte pura | Se ve en las seis pestañas. `ultimoAviso` solo se pinta en `PanelConducir.tsx:463` y `PanelDiagnostico.tsx:203` — un aviso levantado mientras alguien mira LIDAR o Navegar es **invisible** |
| (b) Solo una causa nueva en `no_obedece.ts` | ~25 líneas | Obliga a ir a la pantalla de diagnóstico a enterarse, que es el mismo error que ya se cometió con `ultimoAviso` |
| (c) Nada | 0 | `reinicio.ts` sigue escrito y sin usar |

**RECOMENDACIÓN: (a) + (b)**, pero con **cuatro** correcciones no negociables:

1. 🔴 **Son CUATRO pérdidas, no tres, y la primera es de seguridad: la parada de emergencia baja sola** (`rvr_driver_node.py:266`). Y `transporte.ts:331-332` deja escrito, a propósito, que la web **no la re-publica al reconectar**. O sea que tras un reinicio **nadie la vuelve a poner**. El texto debe empezar por ahí.
2. **Atar el estado al `Transporte`, no al marco** (C6). Si no, el reinicio se anuncia en el robot equivocado.
3. **Nada de «hace ~N s» calculado del latido.** Aunque el temporizador fuera exactamente 1 Hz, el latido cuenta desde que el **nodo** empieza a girar, y entre el reinicio y eso hay `RestartSec=15` + hasta 60 s de espera de udev + ~10 s de launch + hasta 30 s de `ExecStartPost` (`atriz-robot.service:55-59, 75-76`; el `TimeoutStartSec=180` existe porque la suma se pasaba de 90). El error es **monótono y siempre hacia abajo**: siempre hacia «esto acaba de pasar». Si se pone un número, va con «~» y con esas decenas de segundos declaradas.
4. **El botón `/start_scan` tiene que distinguir su respuesta.** En el caso gemelo —el descriptor muerto del LIDAR tras re-enumerarse el USB al apagar el RVR, **que es el mismo gesto físico**— `/start_scan` contesta `false` y el remedio es `sudo systemctl restart atriz-robot`, que la web **no puede hacer**. Si devuelve `false`, la cinta debe decir «esto ya no lo arregla la web» y dar el comando.

**Y decide de paso qué se hace con `latidoPrevio`**: hoy es un campo muerto **con un comentario que afirma una protección que no existe**, en la web que va a vigilar 16 robots. O se borra de los cuatro ficheros, o se le da trabajo. Lo que no puede quedarse es como está. ⚠️ Y **el comentario no se declara falso hasta M9** (C5).

### D4 · Cuando el RVR vuelve tras un ciclo de alimentación, ¿se re-referencia la odometría?

| Opción | Coste | Consecuencia |
|---|---|---|
| (a) Que `_recuperar_streaming` haga `reset_locator_x_and_y()` + `_yaw_offset = None` | ~10 líneas + sesión física | 🔴 Mete un **salto en `/odom` en marcha**. `odom` tiene que ser continuo (REP-105) y este driver publica `odom → base_footprint`: es justo lo que rompe a slam_toolbox y a AMCL. Además `_recuperar_streaming` corre en **toda** recuperación de silencio, no solo tras un ciclo de alimentación — pondría el origen a cero en eventos donde no se perdió nada. Y **no es implementable ahí**: esa función no sabe si volvió un dato; ese juicio lo hace después `_vigilar_silencio` (`:1146-1156`) |
| **(b) No tocar la ruta de odometría. Registrarlo en el log, y que la web lo detecte y ofrezca `/set_pos_and_yaw(0,0,0)`** | ~10 líneas de log + ~20 en la web | El humano decide cuándo mover el origen. `/set_pos_and_yaw` **ya está en la lista blanca** (`robot.launch.py:344-347`) y es lo único que reancla (`:2498-2503`) |
| (c) Nada | 0 | El sesgo de yaw persiste sin que ningún indicador lo diga |

**RECOMENDACIÓN: (b), y primero M8.** El propio driver se niega a aceptar poses arbitrarias en `set_pos_and_yaw` con el argumento de que «tocar la ruta de la odometría —la parte más verificada del driver— pide su propia sesión de pruebas». Tocarla desde un camino **que se ejecuta solo** es peor que eso.

**Ojo con el detector de la web para este caso:** si el offset viejo persiste, el error de rumbo **no es un pico, es un sesgo constante**. Un detector de discontinuidad vería un salto y después un robot perfectamente coherente y perfectamente mal orientado. El discriminante gratis: **las dos averías dan firmas distintas de `/odom`** — un reinicio del driver lo deja en el origen; un ciclo de alimentación del RVR con el driver vivo deja la posición reiniciada y **el yaw desplazado**. Y `reanudaciones_fallidas` **ya viaja en `/estado_robot`** (`:1954`, alimentado en `:1146-1156`) y no lo lee nadie: sube mientras el RVR está ausente y vuelve a 0 cuando llega un dato de verdad.

---

## 5 · Orden de trabajo

### HOY, sin tocar el robot (todo es lectura o web)

1. **Corregir el docstring de `reinicio.ts:13-14`.** Afirma como hecho «el driver murió, systemd lo reinició»; su propia fuente dice «no se observó directamente, la prueba es indirecta» y «lo que este documento NO sabe: si el driver murió de verdad o solo se reconfiguró». **Y no hay ningún fichero de evidencia del 2026-08-06** — los números viven solo en el plan y copiados ahí. Poner «NO VERIFICADO» al lado.
2. **Escribir `reinicio.test.ts`**, que es el único fichero de `lib/robot/` sin pruebas. La primera prueba: que `latido` llega **como número** por el cable. Es `uint64` en `EstadoRobot.msg`; si alguna capa lo entregara como cadena, `Number.isFinite` daría `false` y `trasLatido()` devolvería el estado sin tocar — **el detector quedaría apagado para siempre, sin un error y sin una línea**.
3. **D3**: cinta en el marco, atada al `Transporte`, con las cuatro pérdidas. Y decidir `latidoPrevio` (borrar o dar trabajo). 358 pruebas detrás de `resumirBaldosa`: no se toca sin pasarlas.
4. **`no_obedece.ts`**: causa `reinicio`, **antes** que la del barrido, porque la explica. Coste de caudal: **cero** — `PanelNoObedece` ya está suscrito a `/estado_robot` y a `/scan`.
5. **Preparar la tanda 4 de `medir_sensor_color.py`** (M1+M2), sin ejecutarla.
6. **Preparar el guion de M10** (unidades de juguete), que no toca el robot ni el RVR.

### Sesión de robot nº 1 — 45 min, sin mover el robot

`sudo systemctl stop atriz-robot` primero.
- **M6** (¿qué pasó el 2026-08-06?) — es lo primero y caduca al reiniciar la Pi.
- **M1 + M2** (color) → decide D1.
- **M8** (el RVR apagado/encendido con el driver vivo) → decide D4.
- **M3** (el hueco de la conmutación) si M1 sale a favor.
- **M9** (latch de `/estado_robot`) desde el navegador.
- **M10** (systemd, los dos caminos) — se puede hacer mientras corre lo anterior.

Escribir `76_color_en_caliente.txt`, `77_rvr_reencendido_odom.txt`, `78_propagacion_systemd.txt` **en el mismo commit** que cualquier conclusión.

### Sesión de robot nº 2 — con espacio, mueve el robot

- **M4** (`autostart:=false`) → decide D2. Y el coste residente por `/proc`.
- **M5** (recuperación por ciclo de vida) con criterio geométrico, no «el mapa crece».
- **Arreglar `_slam_vivo()`** y verificarlo **en las dos direcciones**: con SLAM residente-inactivo `atriz-nav` **arranca**; con SLAM `active` **aborta**.

### Solo después

- `atriz-slam.service` (con `ExecStopPost=-/usr/local/bin/atriz-escaneo off`, que las propuestas olvidan), tres sitios de `fase_7_systemd.sh`, y `probar_lista_blanca.py` en las dos direcciones si se toca alguna lista.
- Cualquier cambio en `robot.launch.py` obliga a **reiniciar `atriz-robot` en los 16** y, por la regla de `FLOTA.md`, a **reconstruir la imagen dorada** — que descansa sobre un `provision.sh` que **nunca se ha ejecutado entero** sobre un 24.04 limpio.

---

## 6 · Lo que NO hay que hacer

**Tumbado por los escépticos, y se mantiene:**

1. **No escribir `/set_color_detection` antes de M1.** El propio driver lo declara imposible en `:2779-2782` y la versión de ROS 1 existía (`Atriz_rvr_node.py:1641`). Diseñar sobre una medida que solo miró el topic es el error que este proyecto documenta seis veces.
2. **No mover solo el parámetro ROS.** Sin `add_on_set_parameters_callback` (no existe), `set_parameters()` deja `self._color_detection` intacto y `_srv_rgbc` seguiría mintiendo. **Los dos, o ninguno.**
3. **No contar «una línea en el launch» para exponer un servicio.** Son `robot.launch.py` + `contrato.ts` (`SERVICIOS` **y** su clasificación de confirmación) + `comprobar_contrato.mjs`. Y `confirmaEfecto()` tiene fallback: **olvidarse no da error, clasifica solo, en silencio** (`contrato.ts:155-157`).
4. **No usar `medir_ritmo_ros2.py --topic`.** No existe (`:77`). Aborta y no mide nada.
5. **No suponer que `_recuperando` protege del muro.** `_vigilar_silencio` sí lo mira (`:1124-1125`); **`rvr_responde` no** (`:1945`). Un hueco de más de 3 s tira el robot del muro del profesor.
6. **No usar `/map` como indicador de que SLAM está encendido.** 0,200 Hz, latcheado, y `map_server` de AMCL publica el mismo topic. Un umbral de 1 s da «apagado» el 96 % del tiempo; el latch da «encendido» sobre un SLAM apagado.
7. **No poner `BindsTo=` y `PartOf=` a la vez.** Si `BindsTo` ⊇ `Requires` ya propaga el reinicio explícito, `PartOf` no añade nada: solo quita la propagación de arranque, que `BindsTo` vuelve a poner. Es una línea que nadie entenderá en seis meses y sugiere una garantía que no existe.
8. **No poner `Conflicts=` entre `atriz-slam` y `atriz-nav`.** Cambia un `RuntimeError` de ocho líneas con el comando de remedio por un mapa destruido en silencio.
9. **No copiar `atriz-nav.service` tal cual para SLAM.** Arrastra `ExecStartPre=atriz-escaneo on` (→ X2 a 11,8 Hz 24/7 en 16 robots) y **no** trae `ExecStopPost=…off`. Y quitar el `ExecStartPre` sin más deja SLAM `active` y mudo.
10. **No probar la propagación solo con `systemctl restart`.** Es un job explícito del operador; el incidente fue `Restart=always`. Hay que **matar** el proceso (M10, caso 2).
11. **No proponer `PartOf` como «lo que arreglaría el daño 1» sin decir que `atriz-nav.service` usa `BindsTo`.** Con `BindsTo` + `Restart=on-failure`, el resultado no es «SLAM mudo»: es **«la navegación no existe»**, y la web no puede arrancarla.
12. **No dar por buena la explicación «la Pi se reinició entera».** La evidencia 52 midió exactamente ese escenario con la Pi viva. Las dos explicaciones **no** están empatadas.
13. **No tocar `_recuperar_streaming` para re-referenciar la odometría** (D4, opción (a)). Salto en `/odom` en marcha, en un camino que se ejecuta solo, en la parte más verificada del driver.
14. **No pedir `/rosout` a la lista blanca** para detectar el reinicio: abriría el log entero de los 16 robots por un dato que el latido ya da.
15. **No usar `sudo`/polkit/`systemctl --user`/un nodo que hace fork** para arrancar SLAM. Sobre un rosbridge **sin autenticación** (`check_origin()` → `True`), (c) de D2 significa que cualquiera en el aula hace que root arranque un proceso. Y un supervisor que hace fork reimplementa systemd sin `Restart`, sin identidad en el journal, y con la obligación de matar al hijo en **todos** los caminos de salida — `atriz.py` falló en cuatro.
16. **No cronometrar el hueco con «reanudó en 4 ms».** Ese número es el tiempo de **encolar**, no el de recuperar el dato: es exactamente la confusión que denunció la evidencia 52, y sigue en el código (`:1188-1190`).
17. **No `pkill -f rvr_driver_node`.** Mata tu terminal. Y ni el truco del corchete protege si la cadena aparece en otra parte de la misma orden.

**Y dos cosas que ninguna de las cuatro propuestas cubre, y que conviene tener escritas antes de construir encima:**

- **Si rosbridge muere solo, nada se entera.** El nodo `puente` no lleva `on_exit`, `respawn` ni nada (`robot.launch.py:351-360`): el launch sigue vivo, systemd en verde, `/odom` a 16,5 Hz, el latido sin reiniciar — y el socket **no abre nunca**. Firma idéntica a «robot apagado» y a «WiFi caído». Es el único fallo de esta familia que deja al alumno sin ningún camino.
- **El estado terminal de systemd es invisible desde la web.** `StartLimitBurst=5` en 300 s: a la sexta vez el servicio queda `failed` y hace falta `systemctl reset-failed` **desde el robot**. Ese estado es permanente y su firma en el navegador es la de un robot apagado.