#!/usr/bin/env bash
#
# Fase 1 / Capítulo 4 — Higiene del sistema operativo
#
#     sudo bash fase_1_higiene_so.sh
#     sudo reboot
#
# 📝 NO VERIFICADO en Ubuntu 24.04. Escrito a partir de lo medido en 20.04.
#    Al ejecutarlo por primera vez, comprobar cada paso y corregir el capítulo 4
#    del manual en el mismo momento.
#
# Cada medida responde a algo MEDIDO en la auditoría, no a preferencias:
#
#   governor            la CPU pasaba 59.6 % del tiempo a 600 MHz con 'ondemand',
#                       teniendo 60 °C y cero throttling
#   journal             784 MB sin límite; journald.conf estaba vacío. Causaba
#                       47 s de bloqueo global por I/O en 42 min de sistema ocioso
#   WiFi power-save     latencias aleatorias de 100-300 ms
#   cloud-init          ~20 de los 27 s de userspace del arranque
#   timers de apt       1 min 27 s + 1 min 14 s martilleando la microSD
#   noatime             una escritura menos por cada lectura. Longevidad de la SD
#
# Es idempotente y respalda cada fichero que modifica con sufijo de fecha.
#
set -uo pipefail        # sin -e: queremos continuar aunque un paso opcional falle

[[ $EUID -ne 0 ]] && { echo "Ejecuta con sudo: sudo bash $0" >&2; exit 1; }

STAMP="$(date +%Y%m%d-%H%M%S)"
say()  { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
avis() { printf '  \033[1;33m!\033[0m %s\n' "$1"; }
salta(){ printf '  \033[0;90m–\033[0m %s\n' "$1"; }

respalda() { [[ -f "$1" ]] && cp -a "$1" "$1.bak-$STAMP" && ok "respaldo: $1.bak-$STAMP"; }

# ─────────────────────────────────────────────────────────────────────────────
say "1/9 · Arranque sin entorno gráfico"
if [[ "$(systemctl get-default)" == "multi-user.target" ]]; then
    salta "ya es multi-user.target"
else
    systemctl set-default multi-user.target && ok "target por defecto -> multi-user"
fi
for u in gdm gdm3 lightdm; do
    systemctl disable --now "$u" 2>/dev/null && ok "$u deshabilitado" || true
done

# ─────────────────────────────────────────────────────────────────────────────
say "2/9 · Governor de CPU a 'performance'"
# Unidad propia: 'ondemand.service' lo revierte en cada arranque
cat > /etc/systemd/system/cpu-performance.service <<'EOF'
[Unit]
Description=Fijar el governor de CPU a performance (lazo de control ROS)
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $g; done'

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now cpu-performance.service 2>/dev/null && ok "cpu-performance.service activo"
systemctl disable --now ondemand 2>/dev/null && ok "ondemand.service deshabilitado" || true
avis "governor actual: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"

# ─────────────────────────────────────────────────────────────────────────────
say "3/9 · Limitar el journal (era el mayor generador de escrituras en la SD)"
respalda /etc/systemd/journald.conf
if grep -q '^SystemMaxUse=' /etc/systemd/journald.conf 2>/dev/null; then
    salta "SystemMaxUse ya configurado"
else
    cat >> /etc/systemd/journald.conf <<'EOF'

# Higiene de microSD — añadido por fase_1_higiene_so.sh
# El sistema anterior acumuló 784 MB de journal sin límite, y era la causa
# principal de los 47 s de bloqueo por I/O medidos en 42 min de reposo.
SystemMaxUse=32M
RuntimeMaxUse=16M
EOF
    ok "SystemMaxUse=32M"
fi
journalctl --vacuum-size=32M >/dev/null 2>&1 && ok "journal recortado a 32M"
systemctl restart systemd-journald 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
say "4/9 · Desactivar el ahorro de energía del WiFi"
cat > /etc/systemd/system/wifi-no-powersave.service <<'EOF'
[Unit]
Description=Desactivar power-save del WiFi (introduce latencias de 100-300 ms)
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'iw dev wlan0 set power_save off || true'

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now wifi-no-powersave.service 2>/dev/null && ok "wifi-no-powersave.service activo"
avis "power_save: $(iw dev wlan0 get power_save 2>/dev/null || echo '(iw no disponible)')"

# ─────────────────────────────────────────────────────────────────────────────
say "5/9 · Deshabilitar cloud-init (~20 s del arranque, sin función aquí)"
if [[ -d /etc/cloud ]]; then
    touch /etc/cloud/cloud-init.disabled && ok "/etc/cloud/cloud-init.disabled creado"
else
    salta "cloud-init no está instalado"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "6/9 · Silenciar los timers de apt (martilleaban la microSD)"
for t in apt-daily.timer apt-daily-upgrade.timer motd-news.timer fstrim.timer; do
    systemctl disable --now "$t" 2>/dev/null && ok "$t deshabilitado" || salta "$t no existe"
done
avis "las actualizaciones de seguridad pasan a ser MANUALES: sudo apt update && sudo apt upgrade"

# ─────────────────────────────────────────────────────────────────────────────
say "7/9 · Purgar servicios sin función en un robot"
for u in snapd lxd-agent bluetooth ModemManager cups cups-browsed \
         whoopsie kerneloops switcheroo-control avahi-daemon \
         multipathd open-iscsi iscsid lvm2-monitor unattended-upgrades; do
    systemctl disable --now "$u" 2>/dev/null && ok "$u deshabilitado" || true
done
# snapd instalado ocupa 6 loop devices y ~11 s de arranque
if dpkg -l snapd 2>/dev/null | grep -q '^ii'; then
    avis "snapd sigue INSTALADO. Para eliminarlo del todo:"
    avis "    sudo apt purge -y snapd && sudo rm -rf /var/cache/snapd /snap ~/snap"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "8/9 · noatime en / (longevidad de la microSD)"
respalda /etc/fstab
if grep -q 'noatime' /etc/fstab; then
    salta "noatime ya presente"
else
    # solo la línea de la raíz, y solo si tiene 'defaults'
    if sed -i -E 's|^(LABEL=writable[[:space:]]+/[[:space:]]+ext4[[:space:]]+)defaults|\1defaults,noatime|' /etc/fstab \
       && grep -q noatime /etc/fstab; then
        ok "noatime añadido a la raíz"
    else
        avis "no se pudo editar automáticamente. Añade ',noatime' a mano en la línea de / :"
        grep -E '\s/\s' /etc/fstab | sed 's/^/       /'
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
say "9/9 · Comprobar que no hay dos stacks de red compitiendo"
NM=$(systemctl is-enabled NetworkManager 2>/dev/null || echo no)
ND=$(systemctl is-enabled systemd-networkd 2>/dev/null || echo no)
echo "  NetworkManager: $NM    systemd-networkd: $ND"
if [[ "$NM" == "enabled" && "$ND" == "enabled" ]]; then
    avis "AMBOS activos. En el sistema anterior esto causaba 6 ciclos de"
    avis "'wpa_supplicant couldn't grab this interface' en cada arranque."
    avis "Ubuntu Server usa netplan+systemd-networkd: considera deshabilitar NetworkManager:"
    avis "    sudo systemctl disable --now NetworkManager NetworkManager-wait-online"
else
    ok "solo un stack de red activo"
fi

# ─────────────────────────────────────────────────────────────────────────────
cat <<EOF

────────────────────────────────────────────────────────────────────────────
  REINICIA para aplicarlo todo:   sudo reboot

  Después, verifica contra la línea base de 00_auditoria/evidencia/
  (el sistema ANTES de optimizar):

    systemd-analyze              # antes 29.5 s userspace -> objetivo < 15 s
    ps -e | wc -l                # antes 273 tareas       -> objetivo < 120
    cat /proc/pressure/io        # 'full total' mucho menor
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # performance
    iw dev wlan0 get power_save  # off
    journalctl --disk-usage      # decenas de MB, no cientos
    systemctl get-default        # multi-user.target
    systemctl --failed           # vacío

  Los respaldos de esta ejecución llevan el sufijo .bak-$STAMP

  ⚠️  Este script NO estaba verificado en 24.04 al escribirse. Si algo no se
     comportó como se describe, corrige el capítulo 4 del manual AHORA.
────────────────────────────────────────────────────────────────────────────
EOF
