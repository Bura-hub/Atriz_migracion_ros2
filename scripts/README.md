# Scripts

Cada script corresponde a un paso del [plan](../01_plan/PLAN_MIGRACION_ROS2.md).
Todos son **idempotentes** (se pueden repetir sin daño) y **respaldan** lo que
modifican con sufijo de fecha.

| Script | Fase | Requiere root | Estado |
|---|---|---|---|
| `fase_0_1_fix_uart.sh` | 0.1 | sí | ✅ **ejecutado y verificado** (2026-07-29) |
| `diag_uart_pins.sh` | 0.1 | sí | diagnóstico opcional, **no ejecutado** |
| `fase_0_3_respaldo.sh` | 0.3 | no (sudo opcional) | ⏳ **pendiente** |

---

## `fase_0_1_fix_uart.sh` — reparar el enlace UART

**Problema que resuelve.** En la Raspberry Pi 4, sin `dtoverlay=disable-bt`, los pines
GPIO14/15 cuelgan del **mini-UART**, que deriva su baudrate del reloj del núcleo VPU.
Cuando el VPU cambia de frecuencia, el baudrate real se desvía → tramas corruptas y
desconexiones intermitentes. El **PL011** (reloj estable, FIFO de 32 bytes) queda
reservado al Bluetooth, que en esta máquina no tiene ni adaptador registrado.

**Qué hace.**

1. Añade `dtoverlay=disable-bt` + `enable_uart=1` a `/boot/firmware/usercfg.txt`
2. Crea `/etc/udev/rules.d/99-rvr.rules` → symlink estable **`/dev/rvr`**
3. Deshabilita `bluetooth.service` (y `hciuart`, que en Ubuntu no existe)
4. Deshabilita `serial-getty@ttyAMA0` y `@ttyS0`, y avisa si `cmdline.txt` reserva
   el puerto para la consola

```bash
sudo bash fase_0_1_fix_uart.sh
sudo reboot                      # el device-tree solo cambia en el arranque
```

**Verificación tras reiniciar:**
```bash
ls -l /dev/rvr                   # -> ttyAMA0
dmesg | grep -i ttyAMA           # -> "is a PL011 rev2"
systemctl is-active bluetooth    # -> inactive
```

**Reversión** — el script imprime los comandos exactos al terminar, con la ruta del
respaldo `usercfg.txt.bak-<fecha>`.

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
2. Respalda lo que no está en git: claves SSH, netplan (con la PSK del WiFi),
   `.bashrc`, ficheros sin trackear, e inventario de paquetes instalados
3. `sync`
4. Imprime los comandos exactos del `dd` para el PC

```bash
bash fase_0_3_respaldo.sh
# copia ~/respaldo_pre_migracion a un USB (NO a git: contiene claves)
sudo poweroff
```

Luego, con la SD en un PC, seguir [RECUPERACION.md](../03_operacion/RECUPERACION.md).

---

## Scripts de medición

Los de diagnóstico del enlace y del ritmo de sensores están en
[`../00_auditoria/evidencia/mediciones_banco/`](../00_auditoria/evidencia/mediciones_banco/)
con su propio README: `raw_uart.py`, `sdk_rate.py`, `sdk_full.py`, `medir.py`,
`test_rvr.py`, `estabilidad.py`.
