# Gestión de la flota — 16 robots

> 🔴🔴 **ANTES DE CONSTRUIR LA IMAGEN DORADA, LEE ESTO.**
>
> Esta guía supone que `provision.sh` funciona. **Eso no está comprobado**: el script nunca se
> ha ejecutado de principio a fin sobre un Ubuntu 24.04 limpio, porque exigiría reflashear
> rvr-01 —el único robot montado— y el usuario decidió no hacerlo el 2026-07-31.
>
> Lo verificado es sintaxis, una pasada con `--simular` y la comprobación de los binarios de
> Nav2. **De una pasada limpia no se ha probado nada de lo que instala o compila.**
>
> El riesgo no es que falle: es que falle **en el robot 7 de 16**, con seis ya desplegados.
> Detalle en `00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.
>
> 🔴 **Y hay TRES bloqueantes más, auditados el 2026-08-01** (evidencia 38):
> 1. **`~/.git-credentials` con el PAT viaja en la imagen.** `fase_6` avisa pero no lo borra.
>    Repartir un token personal en 16 microSD es una decisión, no un detalle. 👤
> 2. **rosbridge no está instalado**, y la web habla por ahí. Clonar antes de la Fase 5 significa
>    clonar dos veces.
> 3. ~~La imagen y `provision.sh` divergen~~ ✅ **RESUELTO 2026-08-01**: `provision.sh` instala el
>    arranque automático en su paso **8/9**. Ya no divergen.
>
> ⚠️ **CORRECCIÓN:** esta guía llegó a decir que «si se construye la imagen antes, los 16 saldrán
> sin arranque automático». **Es falso** — sí lo tendrían. El problema es la divergencia, no la
> ausencia.



> **Estado: DISEÑO. No implementado.** Se ejecuta en la Fase 6, después de tener **un**
> robot completamente funcional sobre ROS 2.
>
> Lo que sí es firme son las **restricciones descubiertas durante la Fase 0.1**, medidas
> sobre hardware real. Son el motivo de varias decisiones de este documento, y conviene
> leerlas antes de comprar nada.

---

## Restricciones descubiertas midiendo (no suposiciones)

### 1. 🔴 Los adaptadores USB del LIDAR no tienen serial único

Confirmado dos veces, en 20.04 y en 24.04, sobre la misma unidad:

```
$ udevadm info -q property -n /dev/ttyUSB0 | grep -E 'ID_SERIAL_SHORT|ID_PATH='
ID_SERIAL_SHORT=0001                                        ← genérico, inservible
ID_PATH=platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0   ← el puerto físico, SÍ sirve
```

**Consecuencia:** si los 16 adaptadores reportan `0001`, **no se puede crear una regla udev
por número de serie**. Y sin regla, `/dev/ttyUSB0` no es determinista: con dos dispositivos
USB serie, el orden de enumeración depende del arranque.

**Tres salidas, en orden de preferencia:**

| Opción | Coste | Inconveniente |
|---|---|---|
| **a) Regla udev por ruta física del puerto** | 0 € | El lidar debe ir **siempre en el mismo puerto USB** de cada Pi. Documentar con foto |
| **b) Adaptadores FTDI con serial único** | ~5 €/robot | Hay que comprobar que expone **DTR** (el X2 alimenta el motor por ahí) |
| **c) Reprogramar el serial del CP2102** | 0 € | Requiere la herramienta de Silicon Labs y un paso manual por robot |

**Recomendación:** (a) para empezar, porque es gratis y funciona. Pasar a (b) si el
mantenimiento se vuelve molesto.

Para (a), la clave es **`ID_PATH`**, que sí identifica el puerto de forma única y estable.
Regla propuesta para `/etc/udev/rules.d/99-ydlidar.rules`:

```
# /dev/ydlidar -> el adaptador USB-serie conectado al puerto físico de SIEMPRE.
# No se puede usar el serial: los CP2102 genéricos reportan todos "0001".
# Obtén el ID_PATH de TU robot con:
#     udevadm info -q property -n /dev/ttyUSB0 | grep ID_PATH=
SUBSYSTEM=="tty", ENV{ID_VENDOR_ID}=="10c4", ENV{ID_MODEL_ID}=="ea60", \
  ENV{ID_PATH}=="platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0", \
  SYMLINK+="ydlidar", MODE="0660", GROUP="dialout"
```

> 📝 **NO VERIFICADO.** La regla está deducida del `ID_PATH` medido, pero **no se ha
> escrito ni probado** todavía. Se hace en la Fase 3, junto con el driver ROS del X2.
> Al probarla, comprobar además que el `ID_PATH` es idéntico en dos robots distintos con
> el lidar en el mismo puerto físico — si no lo fuera, la regla no es clonable y habría que
> generarla en el primer arranque (`first-boot.sh`) en lugar de meterla en la imagen dorada.

> **Verificar primero:** puede que los 16 adaptadores **no** sean todos `0001`. Enchufa dos
> y compara `udevadm info -q property -n /dev/ttyUSB0 | grep ID_SERIAL_SHORT` antes de
> decidir. (Usa `udevadm`, no `dmesg`: en 24.04 `dmesg` requiere `sudo`.)

### 2. El techo de la telemetría es el firmware del RVR, no la red ni el UART

Medido con las 8 corrientes de sensores activas:

| `interval` | `/odom` |
|---|---|
| 250 ms | 3.85 Hz |
| 100 ms | 9.94 Hz |
| **60 ms** | **16.59 Hz** ← usar este |
| 50 ms | **no arranca** |

El firmware cuantiza a múltiplos de 20 ms y **no baja de 60 ms**. 125 paquetes/s caben de
sobra en 115200 baud (~11.5 KB/s), así que el UART no es el límite.

**Para la flota:** 16.5 Hz por robot es el máximo. Presupuestar la red y el servidor con ese
número, no con aspiraciones.

### 3. Consumo por robot, medido

| Recurso | Un robot, solo el driver |
|---|---|
| CPU | **29.5 %** de un núcleo (Pi 4) |
| RAM | 53 MB, plana durante 12 min |
| Temperatura | 55–58 °C |

Queda **holgura** para el driver del LIDAR, SLAM, Nav2 y rosbridge, pero **hay que medirlo
otra vez cuando estén** — 29.5 % es solo el punto de partida.

### 4. 🔴 El riesgo de red sigue sin medir, y es el principal

Esta Pi, con **un** robot y sin rosbridge, ya registra:

```
Signal level = -62 dBm      Tx excessive retries = 797  (en 42 min)
```

**No sabemos cuánto ancho de banda consume un robot con rosbridge activo.** Es el número
que decide si 16 robots caben en un punto de acceso o hacen falta varios.

> **Medirlo con UN robot en la Fase 5 y extrapolar, antes de comprar hardware de red.**
> Es la decisión de compra más cara que queda por tomar.

---

## Asignación por robot

| Robot | Hostname | `ROS_DOMAIN_ID` | Namespace | IP (reserva DHCP) | MAC |
|---|---|---|---|---|---|
| 01 | `rvr-01` | 1 | `/rvr_01` | `192.168.1.58` ⚠️ **sin reserva DHCP todavía** | `d8:3a:dd:d6:c1:ee` (wlan0) · `d8:3a:dd:d6:c1:ea` (eth0) |
| 02 | `rvr-02` | 2 | `/rvr_02` | | |
| … | … | … | … | | |
| 16 | `rvr-16` | 16 | `/rvr_16` | | |

**Rellenar esta tabla a medida que se despliega cada robot.** Es el inventario, y sin él no
se puede diagnosticar nada a distancia.

👤 **Pendiente en `rvr-01`:** crear su **reserva DHCP** en el router para la MAC
`d8:3a:dd:d6:c1:ee`. Hoy tiene `192.168.1.58` por DHCP dinámico, así que puede cambiar y
dejarte sin saber dónde está el robot. Es el momento de hacerlo, antes de que haya 16.

**Por qué un dominio DDS por robot** y no namespaces en un dominio común: ver
[ARQUITECTURA.md](ARQUITECTURA.md), Decisión 1. Resumen: ~160 participantes DDS sobre WiFi
saturan la red solo con el descubrimiento.

**Red:** reservas DHCP por MAC en el router, **no** IPs estáticas configuradas en 16
dispositivos. Un cambio de subred se hace en un sitio en vez de en dieciséis.

---

## Cómo NO repetir el proceso 16 veces

**El trabajo se hace UNA vez.** Perfeccionas un robot, conviertes su tarjeta en imagen, y
cada robot nuevo cuesta **~3 minutos atendidos**.

### Las cuatro herramientas

Escritas el 2026-07-30, después de instalar `rvr-01` a mano y descubrir que el proceso tiene
más trampas de las que caben en una lista de pasos.

| Script | Dónde corre | Qué hace |
|---|---|---|
| **`provision.sh`** | en el robot | De un 24.04 recién instalado a robot terminado. Idempotente. **Es la fuente de verdad**: la imagen dorada se construye ejecutándolo |
| **`preparar_tarjeta.sh`** | en el **PC** (Linux/WSL) | Sobre una tarjeta recién grabada: `cmdline.txt`, `config.txt` con `[all]`, `robot_id.txt`. Elimina el editar ficheros a mano |
| **`verificar_robot.sh`** | en el robot | 36+ aserciones. Sale con código ≠ 0 si algo falla. **Es quien decide si un robot está listo** |
| **`fase_6_preparar_imagen_dorada.sh`** | en el robot de referencia | Le quita la identidad para poder clonarlo |

### Por qué imagen dorada y no aprovisionar 15 robots por red

Es una decisión de **ancho de banda**, no de comodidad. Y esta vez con cifras medidas, no
estimadas.

**Medido el 2026-07-30 aprovisionando `rvr-01`:**

| Paso | Descarga | En disco |
|---|---|---|
| `ros-jazzy-ros-base` + `ros-dev-tools` | **157 MB** (509 paquetes) | 703 MB |
| `apt full-upgrade` inicial + kernel nuevo | ~120 MB | — |
| `iw`, `python3-pip`, `python3-aiohttp`, `pyserial-asyncio` | ~2.5 MB | ~11 MB |
| Las 46 actualizaciones pendientes de `noble-updates` | pendiente de medir | — |

**Del orden de 300 MB de descarga por robot**, y eso *antes* de compilar el workspace o de
instalar el driver del LIDAR y Nav2, que vendrán después.

> ⚠️ Una versión anterior de este documento decía «~1.5 GB por robot». Era una **estimación
> presentada como dato**, y estaba inflada unas cinco veces. Corregido el 2026-07-30 con las
> cifras reales de `apt`. La conclusión no cambia, pero el número sí: **mide antes de
> afirmar.**

Con 15 robots eso es del orden de **4-5 GB sobre la única AP del laboratorio**, que es justo el
[riesgo nº4 de esta página](#4--el-riesgo-de-red-sigue-sin-medir-y-es-el-principal) — el que
sigue sin medir y el más probable. Con imagen dorada son **0 GB de red**: se escriben por SD
desde el PC.

Y hay un segundo argumento, más fuerte que el ancho de banda: **el tiempo**. En el Pi 4, esos
509 paquetes tardan del orden de 15-20 minutos en desempaquetarse e instalarse. Por 15 robots
son varias horas de espera; grabar una imagen son ~8 minutos desatendidos por tarjeta, y se
pueden grabar varias en paralelo con varios lectores USB.

**Pero una imagen que nadie sabe reconstruir es una caja negra**, y ese es exactamente el
problema del `MANUAL SPHERO.docx` original: describía un sistema que nadie podía rehacer. De
ahí la relación entre las dos piezas:

```
   provision.sh ──(una vez, en el robot de referencia)──►  robot terminado
                                                                  │
                                            fase_6_preparar_imagen_dorada.sh
                                                                  │
                                                                  ▼
                                                          IMAGEN DORADA
                                                                  │
                                          preparar_tarjeta.sh --id NN
                                                                  │
                                                                  ▼
                                                      robots 02 … 16
```

**La imagen es el atajo. El script es la verdad.** Si divergen, gana el script: se
reconstruye la imagen. Y como `provision.sh` es idempotente, sirve además para **actualizar**
un robot ya en marcha (`git pull && sudo bash provision.sh`), que es lo que evita la deriva
de configuración — lo que mata las flotas.

### Lo que se hace una sola vez

```bash
# En el robot de referencia, cuando pasa verificar_robot.sh --hardware SIN FALLOS
# y ha superado la verificación de extremo a extremo del plan:
sudo bash ~/atriz_migracion/scripts/fase_6_preparar_imagen_dorada.sh
sudo poweroff       # NO volver a arrancar esta tarjeta antes del dd

# Desde un PC, con la tarjeta fuera:
sudo dd if=/dev/mmcblk0 of=atriz_jazzy_v1.img bs=4M status=progress conv=fsync
sha256sum atriz_jazzy_v1.img > atriz_jazzy_v1.img.sha256
sudo pishrink.sh -Z atriz_jazzy_v1.img     # reduce al tamaño usado: 29 GB -> ~4-6 GB

# Y etiqueta el código, para saber qué corre cada robot:
git tag -a v1.0-jazzy -m "Primera imagen dorada validada" && git push origin v1.0-jazzy
```

🔴 **La imagen dorada contiene la PSK del WiFi** (en `/etc/netplan/50-cloud-init.yaml`) y la
contraseña del usuario `sphero`. Es lo deseable —así los 16 robots entran solos en la red—
pero significa que **la imagen es material sensible**: no sale del laboratorio, no va a git,
y no se comparte por servicios en la nube.

### Lo que se hace por robot

| Paso | Tiempo | ¿Atendido? |
|---|---|---|
| 1. Grabar la imagen en la microSD | ~8 min | no |
| 2. `sudo bash preparar_tarjeta.sh --id NN` (en el PC) | ~15 s | **sí** |
| 3. Anotar la MAC y crear la reserva DHCP en el router | ~1 min | **sí** |
| 4. Arrancar — `atriz-first-boot` hace el resto | ~2 min | no |
| 5. `bash verificar_robot.sh --hardware` | ~1 min | **sí** |
| 6. Rellenar la fila de la tabla de asignación | ~15 s | **sí** |

**Total atendido: unos 3 minutos por robot.** Los 16 caben en una tarde, y con **varios
lectores de tarjetas USB** se graban tres o cuatro en paralelo mientras se verifican las
anteriores.

El paso 2 sustituye a lo que antes era «editar `robot_id.txt` con el Bloc de notas». Sigue
siendo posible hacerlo a mano —la partición es FAT y se abre desde cualquier PC— pero el
script comprueba además que `cmdline.txt` y `config.txt` están bien, y esos dos **fallan en
silencio**: un `[all]` olvidado no da ningún error, el robot simplemente no habla con el RVR.

Si en lugar de la imagen dorada partes de una **instalación limpia** de Ubuntu Server, el
paso 4 pasa a ser `sudo bash provision.sh` y sube a ~25 minutos, casi todos desatendidos.

📝 **`provision.sh` deja el robot COMPLETO desde el 2026-07-31**: sus 8 pasos incluyen ya la
Etapa F (xacro, `slam_toolbox`, `YDLidar-SDK` compilado desde fuentes, `ydlidar_ros2_driver`,
la regla udev de `/dev/ydlidar` y `colcon build`). Antes se quedaba en «ROS 2 instalado y el
código clonado», que no arranca.

🔴 **Y clonaba la rama equivocada** (`migracion-ros2`, la vieja con código de ROS 1, que no
compila con colcon). Corregido a **`ros2`**. Si reconstruyes la imagen dorada desde un
`provision.sh` anterior a esa fecha, el robot no funcionará.

### Por qué hace falta el paso de «preparar»

Clonar una tarjeta tal cual produce 16 robots con la **misma identidad**, y eso rompe cosas
de formas confusas:

| Duplicado | Qué provoca |
|---|---|
| `machine-id` | El DHCP puede dar la **misma IP a dos robots** |
| Claves SSH de host | `REMOTE HOST IDENTIFICATION HAS CHANGED` al saltar de robot a robot — y ningún aviso real si algún día hay un intruso |
| `hostname` | Imposible saber a qué robot estás conectado |
| `ROS_DOMAIN_ID` | **Los robots se ven entre sí en DDS.** Es exactamente lo que la Decisión 1 evita |

`fase_6_preparar_imagen_dorada.sh` borra todo eso e instala
**`atriz-first-boot.service`**, que lo regenera en el primer arranque leyendo
`robot_id.txt`.

Detalles del servicio que importan:

- Corre **antes de `network-pre.target`**: el hostname queda fijado antes de que el DHCP
  pida IP, así el router registra el nombre correcto desde el principio.
- Si `robot_id.txt` falta o es inválido, **no adivina**: registra el problema en
  `/var/log/atriz-first-boot.log`, deja el sistema intacto y **se reintenta en el siguiente
  arranque**. Es preferible a que dos robots acaben con la misma identidad en silencio.
- Escribe la identidad en `/etc/profile.d/atriz-robot.sh` (no en `.bashrc`), así es
  idempotente y fácil de inspeccionar.
- Se deshabilita solo, dejando la marca `/var/lib/atriz-first-boot.done`.

**Para cambiar el número de un robot ya desplegado:** edita `robot_id.txt`, borra
`/var/lib/atriz-first-boot.done` y reinicia.

> 📝 **NO VERIFICADO.** Estos scripts se escribieron **antes** de disponer de un segundo
> robot. Al clonar el primero, comprueba cada paso y corrige este documento. La lógica de
> parseo de `robot_id.txt` sí se probó de forma aislada, incluido el caso trampa de `08`
> (que sin `10#` bash interpretaría como octal).

---

## Imagen dorada — detalle

### Crearla

Desde el robot de referencia ya validado (Fase 0.3 → Fase 5 completas):

```bash
# En la Pi, antes de apagar:
bash ~/atriz_migracion/scripts/fase_0_3_respaldo.sh
sudo poweroff

# Con la SD en un PC:
sudo dd if=/dev/mmcblk0 of=atriz_jazzy_v1.img bs=4M status=progress conv=fsync
sha256sum atriz_jazzy_v1.img > atriz_jazzy_v1.img.sha256
pishrink.sh atriz_jazzy_v1.img          # reduce la imagen al tamaño usado
```

**Antes de clonar**, quitar de la imagen todo lo que debe ser único por robot:
- claves SSH de host (`/etc/ssh/ssh_host_*`) → se regeneran en el primer arranque
- `machine-id` (`/etc/machine-id` vacío → systemd lo regenera)
- hostname
- `~/.bash_history`, logs

### Personalizar en el primer arranque

Un fichero de texto en la partición `/boot/firmware` —**editable desde cualquier PC, sin
arrancar la Pi**— y un servicio que lo lee:

```
# /boot/firmware/robot_id.txt
ROBOT_ID=03
```

`first-boot.service` (a escribir en la Fase 6) lee ese fichero y fija hostname,
`ROS_DOMAIN_ID`, namespace y claves; luego se deshabilita solo.

**Por qué en `/boot/firmware`:** es la partición FAT, legible desde Windows, macOS y Linux.
Grabas 16 tarjetas, editas un número en cada una, y listo. Sin sesiones SSH manuales.

---

## Versionado: los robots siguen etiquetas, no ramas

**Regla:** los robots se despliegan desde **tags**, nunca desde `main` ni desde ramas de
trabajo.

```bash
# Al validar una versión:
git tag -a v1.0-jazzy -m "Primer despliegue ROS 2 Jazzy validado"
git push origin v1.0-jazzy

# En cada robot:
git fetch --tags && git checkout v1.0-jazzy

# Para saber qué corre un robot:
git describe --tags
```

**Por qué.** Una rama se mueve bajo tus pies; un tag es inmutable. Cuando el robot 7 se
comporte distinto al 3, `git describe` responde en un segundo.

**Aprendido por las malas el 2026-07-29:** el clon de `Atriz_rvr` en esta Pi estaba **5
commits por detrás** de GitHub y **nunca se le había hecho `git fetch`**. Se auditó código
de nueve meses de antigüedad y tres hallazgos resultaron falsos. Con 16 máquinas y sin
disciplina de versiones, ese problema se multiplica por dieciséis y se vuelve imposible de
razonar.

---

## Longevidad de las microSD

Con 16 tarjetas, la mortalidad pasa de anécdota a tarea de mantenimiento. En la auditoría
original se midieron **47 segundos de bloqueo global por I/O en 42 minutos** con el sistema
ocioso, y **784 MB de journal** sin límite.

Obligatorio en la imagen dorada:

| Medida | Por qué |
|---|---|
| `journald.conf`: `Storage=volatile` o `SystemMaxUse=32M` | Era el mayor generador de escrituras |
| `log2ram` o `/var/log` en tmpfs | Idem |
| `noatime` en `/etc/fstab` | Evita una escritura por cada lectura |
| Sin swap | Evita bloqueos y desgaste |
| Timers `apt-daily` desactivados | 1 min 27 s + 1 min 14 s martilleando la tarjeta |
| Sin `tracker-miner-fs` (no habrá, con Server) | Indexaba la tarjeta continuamente |
| `chmod 600 /etc/netplan/*.yaml` | En 20.04 estaba en **`-rw-r--r--`**: la **PSK del WiFi era legible por cualquier usuario** del sistema. Con 16 robots y estudiantes con acceso, importa |

**Presupuestar tarjetas de repuesto** y tener la imagen dorada lista para reflashear. Con 16
robots, reflashear será rutina, no emergencia.

---

## Alta de un robot nuevo

**1. Grabar** la imagen dorada en la microSD (Raspberry Pi Imager o `dd`).

**2. Preparar la tarjeta**, con ella todavía en el PC:
```bash
sudo bash ~/atriz_migracion/scripts/preparar_tarjeta.sh --id NN
```
Fija `robot_id.txt` y comprueba `cmdline.txt` y `config.txt`. Lleva `--simular` si quieres ver
qué haría antes de que lo haga.

**3. Montar el hardware.** RVR por UART: **TX y RX van CRUZADOS** (GPIO14→RX, GPIO15→TX) y el
**GND común es obligatorio** — sin él la comunicación falla de forma errática, no limpia, que
es mucho peor para diagnosticar. El LIDAR, **en el mismo puerto USB físico que en los demás
robots** (ver restricción 1: los CP2102 no tienen serial único).

**4. Arrancar.** `atriz-first-boot` lee `robot_id.txt` y fija hostname, `ROS_DOMAIN_ID`,
`machine-id` y claves SSH de host. Espera ~2 minutos.

> Tu PC avisará de una **huella SSH nueva** al conectarte. Es lo esperado: cada robot genera
> sus claves en el primer arranque. Si **no** avisara, es señal de que las claves se clonaron
> y todos los robots comparten identidad — eso sí es un problema.

**5. Anotar la MAC y crear la reserva DHCP** en el router. Con 16 robots es la única forma
sensata de saber quién es quién.

**6. Verificar.** Un solo comando decide si el robot está listo:
```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```
36+ comprobaciones y **código de salida ≠ 0 si algo falla**. No des el robot por bueno sin
esto: los fallos de este proyecto son los que no se manifiestan como error. Si sale limpio,
comprueba además las frecuencias, que dependen de ROS 2:
```bash
ros2 topic hz /rvr_NN/odom     # ~16.5 Hz
ros2 topic hz /rvr_NN/scan     # ~10 Hz
```

**7. Rellenar la fila** de la tabla de asignación de este documento. Sin inventario no se
diagnostica nada a distancia.

**8. Registrar el robot** en la plataforma web.

### Lo que la imagen dorada NO resuelve

Conviene tenerlo claro para no confiarse:

| | |
|---|---|
| **Deriva posterior** | La imagen iguala los robots el día 1. A partir de ahí divergen en cuanto alguien toca uno. La respuesta es `git pull && sudo bash provision.sh` en los 16, o Ansible |
| **Actualizaciones de seguridad** | La higiene deshabilita `unattended-upgrades` a propósito (no queremos que un robot se actualice a mitad de un experimento). Eso significa que **actualizar los 16 es una tarea manual y periódica** |
| **La regla udev del LIDAR** | Va por `ID_PATH`, y **está sin verificar** que el `ID_PATH` sea idéntico entre robots. Si no lo fuera, no es clonable y hay que generarla en `first-boot.sh`. Ver restricción 1 |
| **El ancho de banda en operación** | La imagen ahorra el tráfico de *instalación*, no el de *telemetría*. El riesgo nº4 sigue intacto y sin medir |
| **Las tarjetas microSD** | Mueren. Con 16 unidades es mantenimiento periódico. Tener la imagen lista es precisamente lo que convierte eso en 10 minutos |

---

## Salud de la flota

Pendiente de la Fase 6: un endpoint que agregue de los 16 robots batería, uptime,
temperatura, y si `/odom` y `/scan` están vivos. Con alerta de batería baja.

Umbrales de referencia, de las mediciones de la Fase 0.1:

| Señal | Normal | Sospechoso |
|---|---|---|
| `/odom` | 16.5 Hz | < 12 Hz |
| `/scan` | ~10 Hz | < 8 Hz |
| Temperatura | 55–60 °C | > 75 °C |
| RSS del driver | ~53 MB, plano | crecimiento sostenido = fuga |
| CPU del driver | ~29 % | > 50 % sin causa |
