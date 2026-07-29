#!/usr/bin/env bash
# Diagnóstico: ¿están los pines GPIO14/15 enrutados a un UART?
#   sudo bash diag_uart_pins.sh
#
# Lee GPFSEL1 del BCM2711 y traduce el modo de cada pin. Es la única forma
# de saber si el firmware asignó los pines, porque con dtoverlay=disable-bt
# el device-tree deja uart0_pins vacío a propósito.

[[ $EUID -ne 0 ]] && { echo "Ejecuta con sudo"; exit 1; }

python3 - <<'PY'
import mmap, os

# BCM2711: periféricos en 0xFE000000, GPIO en +0x200000
GPIO_BASE = 0xFE200000
f = os.open('/dev/mem', os.O_RDONLY | os.O_SYNC)
m = mmap.mmap(f, 4096, prot=mmap.PROT_READ, offset=GPIO_BASE)

gpfsel1 = int.from_bytes(m[4:8], 'little')   # GPFSEL1 = GPIO 10..19
MODES = {0:'ENTRADA', 1:'SALIDA', 4:'ALT0', 5:'ALT1', 6:'ALT2', 7:'ALT3', 3:'ALT4', 2:'ALT5'}

print(f"GPFSEL1 = 0x{gpfsel1:08x}\n")
modes = {}
for pin, fisico in ((14, 8), (15, 10)):
    mode = (gpfsel1 >> ((pin % 10) * 3)) & 0b111
    modes[pin] = mode
    rol = ''
    if   mode == 4: rol = '  → UART0 / PL011 ('     + ('TXD' if pin == 14 else 'RXD') + ')'
    elif mode == 2: rol = '  → UART1 / mini-UART (' + ('TXD' if pin == 14 else 'RXD') + ')'
    print(f"  GPIO{pin}  (pin físico {fisico:>2})  {MODES.get(mode, '?'+str(mode)):<8}{rol}")

print()
print("=" * 68)
if modes[14] == 4 and modes[15] == 4:
    print("PINES OK → PL011 conectado a GPIO14/15.")
    print("El enlace físico de la Pi está bien: el problema está en el robot")
    print("(apagado, sin batería, dormido) o en el cableado TX/RX/GND.")
elif modes[14] == 2 and modes[15] == 2:
    print("Los pines siguen en el MINI-UART, pero disable-bt lo dejó 'disabled'.")
    print("Configuración incoherente → hay que revertir disable-bt.")
else:
    print("PINES NO ENRUTADOS A NINGÚN UART.")
    print("Es la causa de los cero bytes. Hay que revertir disable-bt y")
    print("volver al mini-UART, que sí funcionaba.")
print("=" * 68)

m.close(); os.close(f)
PY
