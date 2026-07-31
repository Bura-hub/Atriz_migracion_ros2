#!/usr/bin/env bash
#
# Fase 1 / Capítulo 4 — Higiene del sistema operativo
#
#     sudo bash fase_1_higiene_so.sh
#     sudo reboot
#
# ✅ EJECUTADO Y VERIFICADO en Ubuntu 24.04 el 2026-07-30. Comprobado en vivo el
#    2026-07-31: governor `performance`, `multi-user.target`, `iw` instalado con
#    power_save `off`, netplan en 600, y el arranque de userspace en **16.6 s**
#    contra 1 min 39 s de la línea base.
#
# ⚠️ DOS COMPROBACIONES QUE PARECEN FALLAR Y NO FALLAN:
#    · `systemctl is-enabled cloud-init` dice **enabled** igualmente. cloud-init
#      se desactiva con el FICHERO `/etc/cloud/cloud-init.disabled`, no con
#      systemctl. Lo que importa es que las tres unidades estén `inactive`.
#    · `ps -e | wc -l` da ~166 con el robot corriendo, contra el objetivo «<120».
#      **86 de esas tareas son de `atriz-robot.service`**: el SO solo tiene 80.
#      `verificar_robot.sh` lo mide bien; el objetivo del plan estaba mal
#      planteado y contaba además ~123 hilos de kernel.
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

# Pasos que NO se pudieron aplicar. Se imprimen al final y cambian el codigo de
# salida. Sin esto el script terminaba en verde aunque un paso no hubiera hecho
# nada — y eso ya paso con el power-save del WiFi (ver paso 4).
NO_APLICADO=()

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

# `iw` NO viene en Ubuntu Server 24.04. Verificado el 2026-07-30: `command -v iw`
# no devuelve nada en una imagen recién instalada.
#
# La versión anterior de este paso hacía `iw ... || true` dentro del ExecStart, así
# que sin el binario el servicio arrancaba "correctamente" y no hacía NADA, para
# siempre. Es el fallo silencioso contra el que avisa CLAUDE.md: un servicio en
# verde que no cumple su función es peor que un servicio en rojo.
IW="$(command -v iw || true)"
if [[ -z "$IW" ]]; then
    avis "iw no está instalado (normal en Server 24.04) — instalando…"
    # En una imagen recién grabada, unattended-upgrades está trabajando y tiene
    # cogido el lock de dpkg. Sin esta espera, el apt-get de abajo falla con
    # "Could not get lock" en casi cualquier robot nuevo de la flota.
    for i in $(seq 1 30); do
        fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || break
        [[ $i -eq 1 ]] && avis "esperando a que apt/unattended-upgrades suelte el lock de dpkg…"
        sleep 5
    done
    if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then
        avis "el lock de dpkg sigue ocupado tras 150 s. ¿Quién lo tiene?"
        fuser -v /var/lib/dpkg/lock-frontend 2>&1 | sed 's/^/       /'
    fi
    apt-get install -y iw >/dev/null 2>&1 || avis "apt-get falló (¿sin red? ¿lock ocupado?)"
    IW="$(command -v iw || true)"
fi

if [[ -z "$IW" ]]; then
    NO_APLICADO+=("WiFi power-save: falta el binario 'iw'. Instálalo y reejecuta:")
    NO_APLICADO+=("    sudo apt install -y iw && sudo bash $0")
    printf '  \033[1;31m✗\033[0m %s\n' "sin 'iw' no se puede tocar el power-save — PASO NO APLICADO"
else
    ok "iw disponible en $IW"
    IFACE="$(ls /sys/class/net | grep -m1 '^wl' || echo wlan0)"
    ok "interfaz inalámbrica detectada: $IFACE"

    cat > /etc/systemd/system/wifi-no-powersave.service <<EOF
[Unit]
Description=Desactivar power-save del WiFi (introduce latencias de 100-300 ms)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
# Sin '|| true': si esto falla, el servicio debe quedar en rojo y verse en
# 'systemctl --failed'. Un power-save que sigue activo degrada la teleoperacion.
ExecStart=$IW dev $IFACE set power_save off

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    if systemctl enable --now wifi-no-powersave.service 2>/dev/null; then
        ok "wifi-no-powersave.service activo"
    else
        NO_APLICADO+=("wifi-no-powersave.service no arrancó: systemctl status wifi-no-powersave")
        printf '  \033[1;31m✗\033[0m %s\n' "el servicio NO arrancó — míralo antes de seguir"
    fi
    # Comprobar el efecto REAL, no que el servicio esté 'activo'.
    # OJO con las mayúsculas: iw 6.7 imprime "Power save: off", no "power save".
    # Con un grep sensible a mayúsculas esto daba un falso positivo (2026-07-30).
    PS="$("$IW" dev "$IFACE" get power_save 2>&1 | grep -oi 'power.save:.*' || echo '(sin salida de iw)')"
    if [[ "${PS,,}" == *off* ]]; then
        ok "verificado: $PS"
    else
        NO_APLICADO+=("power-save sigue en '$PS' pese a que el servicio está activo")
        printf '  \033[1;31m✗\033[0m %s\n' "power-save NO quedó apagado: $PS"
    fi
fi

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

# OJO con snapd: deshabilitar snapd.service NO SIRVE DE NADA por sí solo, porque
# snapd.socket lo reactiva (TriggeredBy=snapd.socket). Verificado el 2026-07-30:
# tras un reinicio, `systemctl is-enabled snapd` decía "disabled" y el demonio
# estaba corriendo. Hay que apagar el SOCKET y las unidades acompañantes.
# snapd.seeded.service era, con 3.5 s, el servicio más lento del arranque.
for u in snapd.socket snapd.seeded.service snapd.apparmor.service \
         snapd.autoimport.service snapd.recovery-chooser-trigger.service snapd \
         lxd-agent bluetooth ModemManager cups cups-browsed \
         whoopsie kerneloops switcheroo-control avahi-daemon \
         multipathd open-iscsi iscsid lvm2-monitor unattended-upgrades; do
    systemctl disable --now "$u" 2>/dev/null && ok "$u deshabilitado" || true
done

# Comprobar el efecto REAL, no que 'is-enabled' diga disabled.
if systemctl is-active snapd.service >/dev/null 2>&1; then
    NO_APLICADO+=("snapd SIGUE ACTIVO. Mira quién lo dispara:")
    NO_APLICADO+=("    systemctl show snapd.service -p TriggeredBy")
    printf '  \033[1;31m✗\033[0m %s\n' "snapd sigue activo pese a deshabilitarlo"
else
    ok "verificado: snapd.service no está activo"
fi

# snapd instalado ocupa loop devices y varios segundos de arranque
if dpkg -l snapd 2>/dev/null | grep -q '^ii'; then
    avis "snapd sigue INSTALADO (deshabilitado, pero en disco). Para eliminarlo del todo:"
    avis "    sudo apt purge -y snapd && sudo rm -rf /var/cache/snapd /snap ~/snap"
    avis "No lo hace este script: 'apt purge' es irreversible sin reinstalar."
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
say "9/9 · Comprobar la red antes de reiniciar (esta máquina es headless)"
# `systemctl is-enabled` de una unidad ausente imprime "not-found" Y sale con
# codigo != 0, asi que un `|| echo no` concatenaba las dos cosas y salia
# "not-found\nno" en la misma variable. Se toma solo la primera linea.
NM=$(systemctl is-enabled NetworkManager 2>/dev/null | head -1); NM=${NM:-no}
ND=$(systemctl is-enabled systemd-networkd 2>/dev/null | head -1); ND=${ND:-no}
echo "  NetworkManager: $NM    systemd-networkd: $ND"
if [[ "$NM" == "enabled" && "$ND" == "enabled" ]]; then
    avis "AMBOS activos. En el sistema anterior esto causaba 6 ciclos de"
    avis "'wpa_supplicant couldn't grab this interface' en cada arranque."
    avis "Ubuntu Server usa netplan+systemd-networkd: considera deshabilitar NetworkManager:"
    avis "    sudo systemctl disable --now NetworkManager NetworkManager-wait-online"
else
    ok "solo un stack de red activo (en Server 24.04 NetworkManager no viene instalado)"
fi

# El paso 5 deshabilitó cloud-init, y en esta imagen el WiFi vive en un netplan que
# generó cloud-init. El fichero PERSISTE y systemd-networkd lo sigue leyendo, pero
# hay que confirmarlo ANTES de reiniciar: si el WiFi no vuelve, se pierde el SSH a
# una máquina sin pantalla y toca ir con un cable.
if [[ -d /etc/netplan ]]; then
    if netplan generate 2>/dev/null; then
        ok "netplan generate correcto — la configuración de red sobrevive al reinicio"
    else
        NO_APLICADO+=("netplan generate FALLA. NO REINICIES: perderías el acceso SSH.")
        printf '  \033[1;31m✗\033[0m %s\n' "netplan generate falla — NO REINICIES hasta arreglarlo"
    fi
    for f in /etc/netplan/*.yaml; do
        [[ -f "$f" ]] || continue
        # Contiene la PSK del WiFi en texto plano: no debe ser legible por todos.
        perm=$(stat -c '%a' "$f")
        if [[ "$perm" == "600" ]]; then
            ok "$f permisos $perm"
        else
            chmod 600 "$f" && ok "$f: permisos $perm -> 600 (contiene la PSK del WiFi)"
        fi
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
if [[ ${#NO_APLICADO[@]} -gt 0 ]]; then
    printf '\n\033[1;31m▶ %s\033[0m\n' "PASOS NO APLICADOS — no des la higiene por hecha:"
    printf '  \033[1;31m✗\033[0m %s\n' "${NO_APLICADO[@]}"
fi

cat <<EOF

────────────────────────────────────────────────────────────────────────────
  REINICIA para aplicarlo todo:   sudo reboot

  Después, verifica contra la línea base de 00_auditoria/evidencia_24_04/
  (este mismo sistema recién instalado, ANTES de optimizar).

  ⚠️  NO compares con 00_auditoria/evidencia/: esa es la del sistema VIEJO
      (20.04 + Noetic). Son dos sistemas distintos y mezclar sus números es
      lo que produce deriva entre la documentación y la realidad.

    systemd-analyze              # antes 1min39s userspace -> objetivo < 15 s

    # Procesos de USUARIO, no 'ps -e': ese cuenta ~129 hilos de kernel, que son
    # el suelo del sistema y no se pueden bajar. Objetivo: < 30 (sin contar tu
    # propia sesion SSH, que son ~16 procesos entre sshd, bash y el agente).
    ps -e -o ppid= | awk '\$1!=2' | wc -l
    systemctl list-units --type=service --state=running --no-legend | wc -l   # objetivo < 20

    # Presion de I/O: mide el RITMO EN REPOSO, no el acumulado. El 'total' de
    # justo tras arrancar esta dominado por cloud-init y apt, y diria que no ha
    # mejorado nada cuando la causa ya esta desactivada. Toma dos lecturas:
    #   grep full /proc/pressure/io; sleep 60; grep full /proc/pressure/io
    # antes: 2.19 s por minuto  ->  objetivo: casi cero en reposo
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # performance
    iw dev wlan0 get power_save  # off
    journalctl --disk-usage      # decenas de MB, no cientos
    systemctl get-default        # multi-user.target
    systemctl --failed           # vacío
    uname -r                     # ¿cambió el kernel en este reinicio?

  Los respaldos de esta ejecución llevan el sufijo .bak-$STAMP
────────────────────────────────────────────────────────────────────────────
EOF

# Codigo de salida distinto de 0 si algun paso no se aplico: asi un script que
# llame a este puede pararse, en vez de asumir que la higiene esta hecha.
[[ ${#NO_APLICADO[@]} -eq 0 ]] || exit 1
