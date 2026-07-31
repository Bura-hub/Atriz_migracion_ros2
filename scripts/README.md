# Scripts

Cada script corresponde a un paso del [plan](../01_plan/PLAN_MIGRACION_ROS2.md).
Todos son **idempotentes** (se pueden repetir sin daño) y **respaldan** lo que
modifican con sufijo de fecha.

## Los tres que usarás para la flota

Si vienes a montar un robot nuevo, son estos. El resto son las piezas que ellos orquestan.

| Script | Dónde corre | Para qué |
|---|---|---|
| **`preparar_tarjeta.sh --id NN`** | en el **PC**, tarjeta recién grabada | Deja `cmdline.txt`, `config.txt` y `robot_id.txt` correctos antes del primer arranque |
| **`provision.sh`** | en el robot | De un 24.04 limpio a robot terminado. Idempotente: sirve también para actualizar |
| **`verificar_robot.sh --hardware`** | en el robot | 36+ aserciones. **Decide si el robot está listo.** Código ≠ 0 si algo falla |

El procedimiento completo de alta de un robot está en
[`03_operacion/FLOTA.md`](../03_operacion/FLOTA.md).

---

## Todos los scripts

| Script | Fase / Etapa | Requiere root | Estado |
|---|---|---|---|
| `verificar_robot.sh` | cualquiera | no | ✅ **probado en rvr-01** (2026-07-31): **86 con `--hardware`** (80 sin él), 0 fallos y 3 avisos (2026-07-31). 📝 Ese mismo día se le encontraron **tres fallos propios más** (van seis): ver evidencia 32 |
| `provision.sh` | B–**F** | sí | 🟡 **probado en seco** (`--simular`); no ejecutado de principio a fin. 📝 Desde el 2026-07-31 deja el robot **completo** (8 pasos, incluida la Etapa F) y clona la rama **`ros2`** — antes clonaba `migracion-ros2`, que es código de ROS 1 y no compila |
| `preparar_tarjeta.sh` | B (en el PC) | sí | 🟡 **probado en seco** sobre copias de la partición FAT; no en una microSD real |
| `fase_0_1_fix_uart.sh` | 0.1 · B3 | sí | ✅ **ejecutado y verificado** en 20.04 (2026-07-29) y en **24.04 (2026-07-30)** |
| `diag_uart_pins.sh` | 0.1 | sí | diagnóstico opcional, **nunca ha hecho falta** |
| `fase_0_3_respaldo.sh` | 0.3 · A1 | no (sudo opcional) | ✅ **ejecutado** (2026-07-29). 📝 Sus dos correcciones del 2026-07-30 **sin reejecutar** |
| `fase_1_higiene_so.sh` | 1 · C1 | sí | ✅ **ejecutado y verificado** en 24.04 (2026-07-30) |
| `fase_1_validar_sdk_py312.py` | 1 · D2 | no | ✅ **ejecutado 2026-07-30 → 🟢 GO** (16.67 Hz en Python 3.12) |
| `fase_7_systemd.sh` | 7 | sí | 🟡 **probado en seco** (`--simular` recorre los 5 pasos). El servicio **nunca se ha arrancado**: 📝 NO VERIFICADO |
| `atriz-robot.sh` + `atriz-robot.service` | 7 | sí (instalarlos) | 🟡 el envoltorio **sí se ejecutó** (guardas y espera de puertos, 2026-07-31); la unidad pasa `systemd-analyze verify` |
| `atriz-escaneo.sh` | 7 | no | 🟡 las dos llamadas que hace están **verificadas** en ROS y por oído; el script instalado, no |
| `fase_6_preparar_imagen_dorada.sh` | 6 · F6 | sí | ⏳ **pendiente**, y 📝 **NO VERIFICADO** |

> ⚠️ **`verificar_robot.sh` comprueba el EFECTO, no la intención**, y las dos aserciones que se
> le añadieron el 2026-07-30/31 explican por qué:
>
> - Mide el **ritmo** de `/odom`, no que el topic exista — el RVR se dormía a los 300.6 s
>   dejando el nodo vivo y publicando cero, sin un error.
> - Comprueba `odom → base_footprint`, no `odom → laser` — la segunda **pasaba** con el árbol
>   TF partido en dos, resolviendo por el camino equivocado.
>
> Si añades comprobaciones, mantén esa regla.
| `first-boot.sh` + `first-boot.service` | 6 · F6 | sí (en el robot clonado) | ⏳ **pendiente**, y 📝 **NO VERIFICADO** |

> Los scripts de la Fase 6 (imagen dorada y personalización por robot) se escribieron antes de
> tener un robot terminado. **No se han ejecutado nunca.** No los uses hasta que este robot
> pase la verificación de extremo a extremo del plan.

---

## `fase_0_1_fix_uart.sh` — reparar el enlace UART

**Problema que resuelve.** En la Raspberry Pi 4, sin `dtoverlay=disable-bt`, los pines
GPIO14/15 cuelgan del **mini-UART**, que deriva su baudrate del reloj del núcleo VPU.
Cuando el VPU cambia de frecuencia, el baudrate real se desvía → tramas corruptas y
desconexiones intermitentes. El **PL011** (reloj estable, FIFO de 32 bytes) queda
reservado al Bluetooth, que en esta máquina no tiene ni adaptador registrado.

**Qué hace.**

1. **Detecta a qué fichero hay que escribir** y añade lo que falte de
   `dtoverlay=disable-bt` + `enable_uart=1`
2. Crea `/etc/udev/rules.d/99-rvr.rules` → symlink estable **`/dev/rvr`**
3. Deshabilita `bluetooth.service` (y `hciuart`, que en Ubuntu no existe)
4. Deshabilita `serial-getty@ttyAMA0` y `@ttyS0`, y avisa si `cmdline.txt` reserva
   el puerto para la consola

```bash
sudo bash fase_0_1_fix_uart.sh
# Solo reinicia si el script te lo pide: si disable-bt ya estaba en efecto,
# la regla udev y los systemctl surten efecto al instante.
```

**Verificación:**
```bash
ls -l /dev/rvr                       # -> ttyAMA0
cat /proc/device-tree/aliases/uart0  # -> /soc/serial@7e201000 (PL011)
sudo dmesg | grep -i ttyAMA          # -> "is a PL011 rev2"   (sudo: ver abajo)
systemctl is-active bluetooth        # -> inactive, o not-found en 24.04
```

> ⚠️ **`dmesg` necesita `sudo` en Ubuntu 24.04** (`kernel.dmesg_restrict=1`). Sin él da
> `Operation not permitted`, que parece un fallo de hardware y no lo es. El
> `cat /proc/device-tree/aliases/uart0` da lo mismo sin `sudo` y es preferible.

### Los tres ficheros de arranque, y por qué el script los detecta

| Sistema | Fichero efectivo | Detalle |
|---|---|---|
| Ubuntu 20.04 | `usercfg.txt` | `config.txt` lo cargaba con `include usercfg.txt`, y lo gestionaba `pibootctl` |
| **Ubuntu 24.04** | **`config.txt`**, bajo `[all]` | `usercfg.txt` **no existe** y `pibootctl` no se instala |

El script usa `usercfg.txt` **solo si existe Y `config.txt` lo incluye**. Esa segunda
condición es lo importante: un `usercfg.txt` sin `include` que lo cargue es un **fichero
fantasma** que el firmware nunca lee, y escribir ahí haría creer que la configuración está
aplicada cuando no lo está.

Al escribir en `config.txt`, el script **encabeza con `[all]`**, porque la imagen de 24.04
termina en `[cm4]` y sin esa cabecera la línea quedaría restringida a esa placa. Y al
comprobar si una clave ya está activa **respeta las secciones**: un `dtoverlay=disable-bt`
colgando bajo `[cm4]` existe en el fichero y no hace nada en un Pi 4, así que un `grep` normal
lo daría por bueno.

> 🐛 **Historia de este arreglo (2026-07-30).** La versión anterior tenía
> `USERCFG=/boot/firmware/usercfg.txt` fijo. En 24.04 ese fichero no existe, así que el `grep`
> fallaba, caía al `else`, y el `cp -a` sobre un fichero inexistente **abortaba el script**
> por `set -euo pipefail` — antes de escribir la regla udev. Síntoma: `/dev/rvr` no aparecía.

**Reversión** — el script imprime los comandos exactos al terminar. Si escribió en el fichero
de arranque, incluye la ruta de su respaldo (`config.txt.bak-<fecha>` en 24.04,
`usercfg.txt.bak-<fecha>` en 20.04); si no tocó nada, lo dice en lugar de ofrecerte restaurar
un respaldo que no existe.

> ⚠️ **Después de este script hay que cambiar el código.** El puerto pasa de `ttyS0` a
> `ttyAMA0`, y el driver tenía `/dev/ttyS0` hardcodeado en 6 sitios. Hecho en el commit
> `67c8776` de la rama `migracion-ros2` de `Atriz_rvr`. Sin ese cambio el robot deja
> de responder.

> ℹ️ **Falsa alarma documentada.** Tras aplicar el overlay, `uart0_pins` queda con
> `brcm,pins` **vacío** en el device-tree y el mini-UART pasa a `disabled`. Parece que
> ningún UART quedara enrutado a los pines. **Es intencional:** decompilando el overlay
> (`dtc -I dtb -O dts /boot/firmware/overlays/disable-bt.dtbo`) se ve que vacía ese
> grupo a propósito, porque en Raspberry Pi es el *firmware* quien asigna los pines al
> ver `enable_uart=1`. Verificado en la práctica: el RVR responde.

---

## `diag_uart_pins.sh` — ¿están los pines en modo UART?

Lee **GPFSEL1** del BCM2711 vía `/dev/mem` y traduce el modo de GPIO14 y GPIO15.
Es la única forma de saberlo con certeza, porque el device-tree no lo refleja
(ver la falsa alarma anterior).

```bash
sudo bash diag_uart_pins.sh
```

Interpretación: **ALT0** = UART0/PL011 · **ALT5** = UART1/mini-UART · cualquier otra
cosa significa que el pin no está conectado a ningún UART.

Úsalo solo si `raw_uart.py` no obtiene respuesta **y** ya has confirmado que el robot
está encendido. **No fue necesario ejecutarlo**: el problema era el robot dormido.

---

## `fase_0_3_respaldo.sh` — preparar la SD para la imagen (BLOQUEANTE)

Se ejecuta **en la Pi, antes de apagarla**. No hace la imagen: la prepara.

1. Comprueba en los dos repositorios si queda algo sin commitear, **sin subir** o
   en un **stash** (los stashes no viajan al remoto y se pierden al reflashear)
2. Respalda lo que no está en git: claves SSH, **credenciales de git**, netplan (con la
   PSK del WiFi), `.bashrc`, ficheros sin trackear, e inventario de paquetes instalados
3. `sync`
4. Imprime los comandos exactos del `dd` para el PC

```bash
bash fase_0_3_respaldo.sh
# copia ~/respaldo_pre_migracion a un USB (NO a git: contiene claves y un token)
sudo poweroff
```

Luego, con la SD en un PC, seguir [RECUPERACION.md](../03_operacion/RECUPERACION.md).

> 🐛 **Dos correcciones del 2026-07-30, 📝 sin reejecutar todavía.**
>
> **Respalda `~/.git-credentials` y `~/.gitconfig`.** No lo hacía, y eso costó caro: tras
> reflashear, el sistema nuevo se quedó sin forma de hacer `push` a un repositorio privado y
> hubo que generar un token nuevo. El respaldo llevaba `~/.ssh`, que además estaba **vacío**.
>
> **No duplica el inventario si no ha cambiado.** Ejecutarlo seis veces dejó seis
> `estado_sistema_*.txt` idénticos byte a byte salvo la fecha — ruido disfrazado de historial.
> Ahora compara con el último y solo escribe si hay diferencias.

---

## Scripts de la Fase 6 — imagen dorada

📝 **NO VERIFICADOS. Nunca se han ejecutado.** Se escribieron antes de tener un robot
terminado, y no deben usarse hasta que este robot pase la verificación de extremo a extremo
del [plan](../01_plan/PLAN_MIGRACION_ROS2.md).

| Script | Qué pretende hacer |
|---|---|
| `fase_7_systemd.sh` | Instalar el arranque automático: el robot se levanta solo al encender, con el barrido del LIDAR apagado |
| `atriz-escaneo.sh` | Encender/apagar el barrido del LIDAR (`atriz-escaneo on\|off\|estado`). Sin barrido el robot no conduce |
| `fase_6_preparar_imagen_dorada.sh` | Limpiar el robot de referencia (claves de host, logs, `machine-id`) para convertirlo en imagen clonable |
| `first-boot.sh` + `first-boot.service` | En cada robot clonado, leer `robot_id.txt` de `/boot/firmware` y fijar hostname, `ROS_DOMAIN_ID` y claves |

Ver [`FLOTA.md`](../03_operacion/FLOTA.md) para el procedimiento completo de alta de un robot.

---

## Scripts de medición

Los de diagnóstico del enlace y del ritmo de sensores están en
[`../00_auditoria/evidencia/mediciones_banco/`](../00_auditoria/evidencia/mediciones_banco/)
con su propio README: `raw_uart.py`, `sdk_rate.py`, `sdk_full.py`, `medir.py`,
`test_rvr.py`, `estabilidad.py`, `x2_parse.py`.

El más útil sigue siendo **`raw_uart.py`**: responde a «¿contesta el RVR a nivel de bytes?»,
que es la pregunta que separa un problema de hardware de un problema de software.

---

## `fase_1_higiene_so.sh` — higiene del SO (Etapa C)

✅ **Ejecutado y verificado en 24.04 el 2026-07-30.** Nueve pasos: `multi-user.target`,
governor `performance`, tope del journal, power-save del WiFi, `cloud-init` fuera, timers de
`apt` fuera, servicios inútiles fuera, `noatime`, y comprobación de red antes de reiniciar.
El **por qué** de cada medida está en el capítulo 4 del manual, con la evidencia que la motiva.

```bash
sudo bash fase_1_higiene_so.sh
sudo reboot
```

**Termina en rojo y con código de salida 1 si algún paso no se pudo aplicar.** Lee la sección
«PASOS NO APLICADOS» antes de dar la higiene por hecha.

> 🐛 **El bug que tenía (arreglado el 2026-07-30).** El paso del power-save del WiFi hacía
> `iw ... || true` dentro del `ExecStart`, y **`iw` no viene instalado en Ubuntu Server
> 24.04**. Resultado: un `wifi-no-powersave.service` en verde que no hacía nada, para siempre.
> Ahora instala `iw` (esperando el lock de dpkg, que en un robot recién grabado lo tiene
> `unattended-upgrades`), quita el `|| true`, y **comprueba el efecto real** en vez de
> conformarse con que el servicio esté «activo».

⚠️ **Este script te deja sin SSH durante el reinicio, y el robot no tiene pantalla.** El paso
9/9 valida `netplan generate` antes de dejarte reiniciar, porque el paso 5 deshabilita
`cloud-init` y el WiFi vive en un netplan que `cloud-init` generó. Ten un cable de red a mano.

---

## `fase_1_validar_sdk_py312.py` — el go/no-go (Etapa D)

✅ **Ejecutado el 2026-07-30 → 🟢 GO.** Era **el punto de decisión de toda la migración**:
comprueba si el SDK de Sphero funciona en Python 3.12.

**Resultado:** los 103 ficheros del SDK compilan, `SpheroRvrAsync` se construye en 0.0 s,
batería 100 %, firmware 9.1.462, y streaming a **16.67 Hz** — el mismo rendimiento que los
16.59 Hz medidos en Python 3.8 sobre 20.04.

```bash
sudo apt install -y python3-aiohttp
sudo pip3 install --break-system-packages pyserial-asyncio   # 24.04 aplica PEP 668
python3 fase_1_validar_sdk_py312.py [--puerto /dev/rvr]      # con el RVR ENCENDIDO
```

Las **tres** dependencias son obligatorias. `pyserial-asyncio` no existe en apt, y hay que
instalarlo **a nivel de sistema** (con `sudo`): con `pip --user` acaba en `~/.local`, donde un
servicio systemd puede no verlo.

> 🐛 **El primer intento dio un NO-GO FALSO** por `ModuleNotFoundError: aiohttp`. No era una
> incompatibilidad con Python 3.12: era un paquete que faltaba. `sphero_sdk/__init__.py`
> importa todo de golpe y esa cadena llega a `cms_fw_check_base.py:2`, que hace
> `import aiohttp` a nivel de módulo. El script lo marcaba como «opcional» en el paso 2/6 y
> moría por él en el 4/6, sugiriendo replantear la arquitectura del proyecto por un paquete de
> diez segundos. Corregido.

Si algún día sale **NO-GO**, el script imprime las cuatro alternativas ordenadas por coste. Es
una decisión de arquitectura, no algo a improvisar.
