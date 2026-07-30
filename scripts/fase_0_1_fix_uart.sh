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
CONFIG=/boot/firmware/config.txt
UDEV=/etc/udev/rules.d/99-rvr.rules

say() { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
warn(){ printf '  \033[1;33m!\033[0m %s\n' "$1"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; }

# ─────────────────────────────────────────────────────────────────────────────
# ¿A qué fichero hay que escribir?
#
#   Ubuntu 20.04 traía config.txt NO editable, que hacía `include usercfg.txt`.
#   Ubuntu 24.04 trae UN SOLO config.txt editable, y NO existe usercfg.txt.
#
#   Escribir en un usercfg.txt que config.txt no incluya crea un fichero
#   FANTASMA: el firmware no lo lee, el script dice "hecho" y nada cambia.
#   Por eso no basta con que el fichero exista — tiene que estar incluido.
#
#   (La versión anterior de este script asumía usercfg.txt y ABORTABA en
#   24.04: el `cp -a` sobre un fichero inexistente mata el script por
#   `set -euo pipefail`, antes de escribir la regla udev. Verificado el
#   2026-07-30 en Ubuntu Server 24.04.4.)
if [[ -f /boot/firmware/usercfg.txt ]] \
   && grep -qE '^[[:space:]]*include[[:space:]]+usercfg\.txt' "$CONFIG" 2>/dev/null; then
    BOOTCFG=/boot/firmware/usercfg.txt
    ok "config.txt incluye usercfg.txt — se escribirá ahí (patrón de 20.04)"
else
    BOOTCFG="$CONFIG"
    [[ -f /boot/firmware/usercfg.txt ]] \
        && warn "existe usercfg.txt pero config.txt NO lo incluye: sería un fichero fantasma"
fi
[[ -f "$BOOTCFG" ]] || { bad "no existe $BOOTCFG — ¿está montada /boot/firmware?"; exit 1; }

# ¿Está una clave activa PARA ESTA PLACA?
#
#   config.txt se divide en secciones de placa: [pi4], [cm4], [pi02]... Una
#   línea solo se aplica si está antes de cualquier sección, o dentro de [all]
#   o de la sección de esta placa. Un `dtoverlay=disable-bt` colgando bajo
#   [cm4] existe en el fichero y NO hace nada en un Pi 4 — un grep normal lo
#   daría por bueno. De ahí este awk.
SECCION_PLACA=pi4      # los 16 robots del laboratorio son Raspberry Pi 4 Model B
clave_efectiva() {
    awk -v pat="$2" -v placa="$3" '
        /^[[:space:]]*\[/ { s = $0; sub(/^[[:space:]]*\[/, "", s); sub(/\].*$/, "", s); next }
        $0 ~ pat && (s == "" || s == "all" || s == placa) { hallado = 1 }
        END { exit(hallado ? 0 : 1) }
    ' "$1"
}

# ─────────────────────────────────────────────────────────────────────────────
say "1/4 · Liberar el PL011 del Bluetooth (${BOOTCFG})"

FALTAN=()
clave_efectiva "$BOOTCFG" '^[[:space:]]*dtoverlay=disable-bt' "$SECCION_PLACA" \
    && ok "dtoverlay=disable-bt ya está activo para [$SECCION_PLACA]" \
    || FALTAN+=("dtoverlay=disable-bt")
clave_efectiva "$BOOTCFG" '^[[:space:]]*enable_uart=1' "$SECCION_PLACA" \
    && ok "enable_uart=1 ya está activo (24.04 lo trae por defecto)" \
    || FALTAN+=("enable_uart=1")

if [[ ${#FALTAN[@]} -eq 0 ]]; then
    warn "nada que añadir — no se toca el fichero"
else
    cp -a "$BOOTCFG" "${BOOTCFG}.bak-${STAMP}"
    ok "respaldo: ${BOOTCFG}.bak-${STAMP}"
    # La cabecera [all] es OBLIGATORIA: sin ella, lo añadido al final de
    # config.txt queda dentro de la ÚLTIMA sección de placa del fichero (en la
    # imagen de 24.04 es [cm4]) y no se aplicaría en un Pi 4.
    {
        echo
        echo "# ── Sphero RVR — añadido en la Fase 0.1 de la migración a ROS 2 ──────────────"
        echo "# Libera el PL011 (ttyAMA0) del Bluetooth y lo asigna a GPIO14/15, donde está"
        echo "# cableado el RVR. Sin esto el RVR queda en el mini-UART, cuyo baudrate deriva"
        echo "# con el reloj del VPU y produce fallos intermitentes."
        echo "[all]"
        printf '%s\n' "${FALTAN[@]}"
    } >> "$BOOTCFG"
    ok "añadido bajo [all]: ${FALTAN[*]}"
fi

# Estado REAL del arranque actual, que es lo único que prueba que funciona.
# De aquí sale REINICIO_NECESARIO: si el PL011 ya está en GPIO14/15, el overlay
# está en efecto y el resto del script (udev, systemctl) surte efecto al instante.
# Decir "hay que reiniciar" cuando no hace falta gasta 40 s del usuario y le
# enseña a ignorar los avisos del script.
UART0="$(tr -d '\0' < /proc/device-tree/aliases/uart0 2>/dev/null || true)"
if [[ "$UART0" == *7e201000* ]]; then
    ok "device-tree del arranque ACTUAL: uart0 -> $UART0 (PL011) — el overlay ya está en efecto"
    REINICIO_NECESARIO=0
else
    warn "device-tree del arranque actual: uart0 -> ${UART0:-desconocido}"
    warn "hasta reiniciar, GPIO14/15 siguen en el mini-UART"
    REINICIO_NECESARIO=1
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
printf '\n────────────────────────────────────────────────────────────────────────────\n'
if [[ $REINICIO_NECESARIO -eq 1 ]]; then
    cat <<'EOF'
  HAY QUE REINICIAR.  El cambio de device-tree solo se aplica en el arranque.

      sudo reboot

  Y DESPUÉS del reinicio, verifica:
EOF
else
    cat <<'EOF'
  NO hace falta reiniciar: el overlay ya estaba en efecto en este arranque, y
  la regla udev y los systemctl surten efecto al instante.

  Verifica AHORA:
EOF
fi

cat <<EOF

      ls -l /dev/rvr               # debe existir y apuntar a ttyAMA0
      cat /proc/device-tree/aliases/uart0    # -> /soc/serial@7e201000 (PL011)
      sudo dmesg | grep -i ttyAMA  # "is a PL011 rev2"   (en 24.04 dmesg NECESITA sudo)
      systemctl is-active bluetooth          # "inactive" o "not-found" (24.04 no la trae)

  Y con el RVR ENCENDIDO, la prueba que de verdad importa:

      python3 $(dirname "$(dirname "$(readlink -f "$0")")")/00_auditoria/evidencia/mediciones_banco/raw_uart.py
      # esperado: "el RVR CONTESTA". Si da 0 bytes, APAGA Y ENCIENDE EL ROBOT:
      # un RVR dormido da el sintoma identico a un cable mal puesto.

  PARA REVERTIR:
EOF
if [[ ${#FALTAN[@]} -gt 0 ]]; then
    echo "      sudo cp ${BOOTCFG}.bak-${STAMP} ${BOOTCFG}"
else
    echo "      (no se modificó ${BOOTCFG}, así que no hay respaldo que restaurar)"
fi
cat <<EOF
      sudo rm ${UDEV}
      sudo systemctl enable --now bluetooth.service 2>/dev/null || true
      sudo reboot
────────────────────────────────────────────────────────────────────────────
EOF
