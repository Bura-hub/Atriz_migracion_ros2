#!/usr/bin/env bash
#
# Fase 0.1 — Reparar el enlace UART del Sphero RVR
#
#   Ejecutar con:  sudo bash fase_0_1_fix_uart.sh
#   Requiere reinicio al terminar.
#
# QUÉ HACE Y POR QUÉ
#
#   Hoy el RVR habla por /dev/ttyS0, el "mini-UART" de la Raspberry Pi 4.
#   Ese puerto deriva su baudrate del reloj del núcleo VPU, que es variable:
#   cuando el VPU cambia de frecuencia, el baudrate real se desvía y aparecen
#   tramas corruptas y desconexiones intermitentes.
#
#   El UART bueno (PL011, /dev/ttyAMA0 — FIFO de 32 bytes y reloj estable) está
#   reservado al Bluetooth. Y en esta máquina el Bluetooth no tiene ni adaptador
#   registrado: `hciconfig -a` no devuelve nada, pero bluetoothd lleva meses
#   corriendo. Se paga el coste sin obtener el beneficio.
#
#   `dtoverlay=disable-bt` libera el PL011 y lo asigna a los pines GPIO14/15,
#   que son donde está cableado el RVR. Elimina el problema de raíz, y es mejor
#   que fijar core_freq porque el PL011 no depende del reloj del VPU.
#
#   Además crea /dev/rvr como nombre estable, para que el código no dependa de
#   si el puerto se llama ttyS0 o ttyAMA0.
#
# REVERSIÓN
#
#   Los ficheros modificados se respaldan con sufijo .bak-<fecha>.
#   Ver la sección "PARA REVERTIR" al final de la salida del script.
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: este script necesita root. Ejecuta:  sudo bash $0" >&2
    exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
USERCFG=/boot/firmware/usercfg.txt
UDEV=/etc/udev/rules.d/99-rvr.rules

say() { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
warn(){ printf '  \033[1;33m!\033[0m %s\n' "$1"; }

# ─────────────────────────────────────────────────────────────────────────────
say "1/4 · Liberar el PL011 del Bluetooth (${USERCFG})"

if grep -q '^[[:space:]]*dtoverlay=disable-bt' "$USERCFG" 2>/dev/null; then
    warn "disable-bt ya estaba presente — no se toca el fichero"
else
    cp -a "$USERCFG" "${USERCFG}.bak-${STAMP}"
    ok "respaldo: ${USERCFG}.bak-${STAMP}"
    cat >> "$USERCFG" <<'EOF'

# ── Sphero RVR — añadido en la Fase 0.1 de la migración a ROS 2 ──────────────
# Libera el PL011 (ttyAMA0) del Bluetooth y lo asigna a GPIO14/15, donde está
# cableado el RVR. Sin esto el RVR queda en el mini-UART, cuyo baudrate deriva
# con el reloj del VPU y produce fallos intermitentes.
dtoverlay=disable-bt
enable_uart=1
EOF
    ok "dtoverlay=disable-bt añadido"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "2/4 · Crear el nombre estable /dev/rvr (${UDEV})"

cat > "$UDEV" <<'EOF'
# /dev/rvr → el UART de los pines GPIO14/15, donde está cableado el Sphero RVR.
# Con dtoverlay=disable-bt ese puerto es el PL011, que el kernel llama ttyAMA0.
# El código debe usar /dev/rvr y nunca el nombre del kernel directamente.
SUBSYSTEM=="tty", KERNEL=="ttyAMA0", SYMLINK+="rvr", MODE="0660", GROUP="dialout"
EOF
ok "regla udev escrita"
udevadm control --reload-rules && udevadm trigger --subsystem-match=tty
ok "reglas de udev recargadas"

# ─────────────────────────────────────────────────────────────────────────────
say "3/4 · Detener el Bluetooth (no hay adaptador y bloquea el UART)"

if hciconfig -a 2>/dev/null | grep -q .; then
    warn "hciconfig SÍ detecta un adaptador Bluetooth."
    warn "Se deshabilita igualmente porque el UART tiene prioridad para el RVR."
else
    ok "confirmado: no hay ningún adaptador Bluetooth registrado"
fi

systemctl disable --now bluetooth.service 2>/dev/null && ok "bluetooth.service deshabilitado" \
    || warn "bluetooth.service ya estaba deshabilitado"
systemctl disable --now hciuart.service 2>/dev/null && ok "hciuart deshabilitado" \
    || true   # en Ubuntu esta unidad no existe; es normal

# ─────────────────────────────────────────────────────────────────────────────
say "4/4 · Asegurar que ninguna consola de login ocupa el UART"

for u in serial-getty@ttyAMA0.service serial-getty@ttyS0.service; do
    systemctl disable --now "$u" 2>/dev/null && ok "$u deshabilitado" \
        || ok "$u ya estaba deshabilitado"
done

if grep -q 'console=serial' /boot/firmware/cmdline.txt; then
    warn "cmdline.txt contiene console=serial — HAY QUE QUITARLO A MANO"
else
    ok "cmdline.txt no reserva el puerto serie para la consola"
fi

# ─────────────────────────────────────────────────────────────────────────────
cat <<EOF

────────────────────────────────────────────────────────────────────────────
  HAY QUE REINICIAR.  El cambio de device-tree solo se aplica en el arranque.

      sudo reboot

  DESPUÉS del reinicio, verifica:

      ls -l /dev/rvr          # debe existir y apuntar a ttyAMA0
      dmesg | grep -i ttyAMA  # debe decir "is a PL011 rev2"
      systemctl is-active bluetooth   # debe decir "inactive"

  PARA REVERTIR:
      sudo cp ${USERCFG}.bak-${STAMP} ${USERCFG}
      sudo rm ${UDEV}
      sudo systemctl enable --now bluetooth.service
      sudo reboot
────────────────────────────────────────────────────────────────────────────
EOF
