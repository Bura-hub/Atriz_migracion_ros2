# Gestión de la flota — 16 robots

> **Estado: DISEÑO. No implementado.** Se ejecuta en la Fase 6, después de tener **un**
> robot completamente funcional sobre ROS 2.
>
> Lo que sí es firme son las **restricciones descubiertas durante la Fase 0.1**, medidas
> sobre hardware real. Son el motivo de varias decisiones de este documento, y conviene
> leerlas antes de comprar nada.

---

## Restricciones descubiertas midiendo (no suposiciones)

### 1. 🔴 Los adaptadores USB del LIDAR no tienen serial único

```
$ dmesg | grep -i cp210
usb 1-1.2: Product: CP2102 USB to UART Bridge Controller
usb 1-1.2: SerialNumber: 0001          ← genérico
```

**Consecuencia:** si los 16 adaptadores reportan `0001`, **no se puede crear una regla udev
por número de serie**. Y sin regla, `/dev/ttyUSB0` no es determinista: con dos dispositivos
USB serie, el orden de enumeración depende del arranque.

**Tres salidas, en orden de preferencia:**

| Opción | Coste | Inconveniente |
|---|---|---|
| **a) Regla udev por ruta física del puerto** (`KERNELS=="1-1.2"`) | 0 € | El lidar debe ir **siempre en el mismo puerto USB** de cada Pi. Documentar con foto |
| **b) Adaptadores FTDI con serial único** | ~5 €/robot | Hay que comprobar que expone **DTR** (el X2 alimenta el motor por ahí) |
| **c) Reprogramar el serial del CP2102** | 0 € | Requiere la herramienta de Silicon Labs y un paso manual por robot |

**Recomendación:** (a) para empezar, porque es gratis y funciona. Pasar a (b) si el
mantenimiento se vuelve molesto.

> **Verificar primero:** puede que los 16 adaptadores **no** sean todos `0001`. Enchufa dos
> y compara `dmesg | grep SerialNumber` antes de decidir.

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
| 01 | `rvr-01` | 1 | `/rvr_01` | *por asignar* | *por rellenar* |
| 02 | `rvr-02` | 2 | `/rvr_02` | | |
| … | … | … | … | | |
| 16 | `rvr-16` | 16 | `/rvr_16` | | |

**Rellenar esta tabla a medida que se despliega cada robot.** Es el inventario, y sin él no
se puede diagnosticar nada a distancia.

**Por qué un dominio DDS por robot** y no namespaces en un dominio común: ver
[ARQUITECTURA.md](ARQUITECTURA.md), Decisión 1. Resumen: ~160 participantes DDS sobre WiFi
saturan la red solo con el descubrimiento.

**Red:** reservas DHCP por MAC en el router, **no** IPs estáticas configuradas en 16
dispositivos. Un cambio de subred se hace en un sitio en vez de en dieciséis.

---

## Cómo NO repetir el proceso 16 veces

**El trabajo se hace UNA vez.** Perfeccionas un robot, conviertes su tarjeta en imagen, y
cada robot nuevo cuesta **~15 minutos casi desatendidos**: grabar la tarjeta, cambiar un
número en un fichero de texto, y anotar la MAC.

### Lo que se hace una sola vez

```bash
# En el robot de referencia, cuando ya funciona del todo y está verificado:
sudo bash ~/atriz_migracion/scripts/fase_6_preparar_imagen_dorada.sh
sudo poweroff

# Desde un PC, con la tarjeta fuera:
sudo dd if=/dev/mmcblk0 of=atriz_jazzy_v1.img bs=4M status=progress conv=fsync
sha256sum atriz_jazzy_v1.img > atriz_jazzy_v1.img.sha256
sudo pishrink.sh -Z atriz_jazzy_v1.img     # reduce al tamaño usado: 29 GB -> ~4-6 GB
```

### Lo que se hace por robot

| Paso | Tiempo | ¿Atendido? |
|---|---|---|
| 1. Grabar la imagen en la microSD | ~8 min | no |
| 2. Editar `robot_id.txt` en la partición FAT | 15 s | **sí** |
| 3. Anotar la MAC y crear la reserva DHCP | ~1 min | **sí** |
| 4. Arrancar (el `first-boot` hace el resto) | ~2 min | no |
| 5. Verificar | ~2 min | **sí** |

**Total atendido: unos 3 minutos por robot.** Los 16 caben en una tarde, y si consigues
**varios lectores de tarjetas USB** puedes grabar tres o cuatro en paralelo mientras
verificas las anteriores.

El paso 2 es literalmente cambiar un número:
```
# /boot/firmware/robot_id.txt
ROBOT_ID=07
```
La partición es **FAT**, así que se edita desde Windows, macOS o Linux **sin arrancar la
Pi**. Grabas las 16 tarjetas seguidas y luego las editas una a una en el portátil.

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

1. Grabar la imagen dorada en la microSD
2. Editar `/boot/firmware/robot_id.txt` con el número
3. Añadir la reserva DHCP en el router (por MAC)
4. Montar el hardware: RVR por UART (**TX/RX cruzados**, GND común), LIDAR **en el mismo
   puerto USB que los demás** (ver restricción 1)
5. Arrancar y verificar:
   ```bash
   hostname                    # rvr-NN
   echo $ROS_DOMAIN_ID         # NN
   ls -l /dev/rvr /dev/ydlidar
   python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
   ros2 topic hz /rvr_NN/odom  # ~16.5 Hz
   ros2 topic hz /rvr_NN/scan  # ~10 Hz
   ```
6. **Rellenar la tabla de asignación** de este documento
7. Registrar el robot en la plataforma web

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
