# Bitácora

Una entrada por sesión de trabajo. Formato: qué se hizo, qué se verificó, qué quedó pendiente.

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
