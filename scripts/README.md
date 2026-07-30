# Scripts

Cada script corresponde a un paso del [plan](../01_plan/PLAN_MIGRACION_ROS2.md).
Todos son **idempotentes** (se pueden repetir sin daño) y **respaldan** lo que
modifican con sufijo de fecha.

| Script | Fase / Etapa | Requiere root | Estado |
|---|---|---|---|
| `fase_0_1_fix_uart.sh` | 0.1 · B3 | sí | ✅ **ejecutado y verificado** en 20.04 (2026-07-29) y en **24.04 (2026-07-30)** |
| `diag_uart_pins.sh` | 0.1 | sí | diagnóstico opcional, **nunca ha hecho falta** |
| `fase_0_3_respaldo.sh` | 0.3 · A1 | no (sudo opcional) | ✅ **ejecutado** (2026-07-29). 📝 Sus dos correcciones del 2026-07-30 **sin reejecutar** |
| `fase_1_higiene_so.sh` | 1 · C1 | sí | ✅ **ejecutado y verificado** en 24.04 (2026-07-30) |
| `fase_1_validar_sdk_py312.py` | 1 · D2 | no | ⏳ **pendiente** — es el go/no-go de la migración |
| `fase_6_preparar_imagen_dorada.sh` | 6 · F6 | sí | ⏳ **pendiente**, y 📝 **NO VERIFICADO** |
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

⏳ **Pendiente.** Es **el punto de decisión de toda la migración**: comprueba si el SDK de
Sphero funciona en Python 3.12. No instales ROS 2 antes de haberlo pasado.

```bash
pip install --break-system-packages pyserial-asyncio   # 24.04 aplica PEP 668
python3 fase_1_validar_sdk_py312.py [--puerto /dev/rvr]   # con el RVR ENCENDIDO
```

Si sale **NO-GO**, el propio script imprime las cuatro alternativas ordenadas por coste. Es
una decisión de arquitectura, no algo a improvisar.
