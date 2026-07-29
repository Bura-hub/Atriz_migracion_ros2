#!/usr/bin/env bash
#
# atriz-first-boot — personaliza un clon de la imagen dorada en su primer arranque
#
# Lo instala fase_6_preparar_imagen_dorada.sh en /usr/local/sbin/ y lo lanza
# atriz-first-boot.service una única vez.
#
# 📝 NO VERIFICADO. Escrito antes de disponer de un segundo robot.
#
# LEE:     /boot/firmware/robot_id.txt   ->  ROBOT_ID=NN
# ESCRIBE: hostname, /etc/hosts, ROS_DOMAIN_ID, claves SSH de host, machine-id
# DEJA:    /var/log/atriz-first-boot.log
#
# Si robot_id.txt falta o es inválido, NO adivina: deja el sistema tal cual,
# registra el problema y se vuelve a ejecutar en el siguiente arranque. Es
# preferible a que dos robots acaben con la misma identidad en silencio.
#
set -uo pipefail

LOG=/var/log/atriz-first-boot.log
ID_FILE=/boot/firmware/robot_id.txt
exec > >(tee -a "$LOG") 2>&1

echo "════ atriz-first-boot ════ $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# ── 1. Leer la identidad ─────────────────────────────────────────────────────
if [[ ! -f "$ID_FILE" ]]; then
    echo "ERROR: no existe $ID_FILE."
    echo "       Monta la partición FAT desde un PC y crea el fichero con:"
    echo "           ROBOT_ID=07"
    echo "       Se reintentará en el próximo arranque. Sin cambios."
    exit 1
fi

ROBOT_ID="$(grep -oP '^\s*ROBOT_ID\s*=\s*\K[0-9]+' "$ID_FILE" | head -1 || true)"
if [[ -z "${ROBOT_ID}" ]]; then
    echo "ERROR: $ID_FILE no contiene una línea ROBOT_ID=<número> válida."
    echo "       Contenido actual:"; sed 's/^/         /' "$ID_FILE"
    echo "       Se reintentará en el próximo arranque. Sin cambios."
    exit 1
fi

ID_NUM=$((10#$ROBOT_ID))          # 10# fuerza base 10: "08" no es octal
if (( ID_NUM < 1 || ID_NUM > 99 )); then
    echo "ERROR: ROBOT_ID=$ROBOT_ID fuera de rango (1-99). Sin cambios."
    exit 1
fi
ID2=$(printf '%02d' "$ID_NUM")
HOST="rvr-$ID2"
NS="rvr_$ID2"

echo "identidad: ROBOT_ID=$ID2  hostname=$HOST  namespace=/$NS  ROS_DOMAIN_ID=$ID_NUM"

# ── 2. Hostname ──────────────────────────────────────────────────────────────
echo "$HOST" > /etc/hostname
hostnamectl set-hostname "$HOST" 2>/dev/null || true
# /etc/hosts: sustituir la línea 127.0.1.1 o añadirla
if grep -q '^127\.0\.1\.1' /etc/hosts; then
    sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t$HOST/" /etc/hosts
else
    printf '127.0.1.1\t%s\n' "$HOST" >> /etc/hosts
fi
echo "  ✓ hostname -> $HOST"

# ── 3. machine-id (si sigue vacío) ───────────────────────────────────────────
if [[ ! -s /etc/machine-id ]]; then
    systemd-machine-id-setup 2>/dev/null && echo "  ✓ machine-id regenerado" \
        || echo "  ! no se pudo regenerar el machine-id"
fi

# ── 4. Claves SSH de host ────────────────────────────────────────────────────
if ! ls /etc/ssh/ssh_host_*_key >/dev/null 2>&1; then
    ssh-keygen -A >/dev/null 2>&1 && echo "  ✓ claves SSH de host generadas" \
        || echo "  ! fallo al generar claves SSH"
    systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true
fi

# ── 5. Entorno ROS 2 del usuario ─────────────────────────────────────────────
# Fichero aparte en vez de editar .bashrc: idempotente y fácil de inspeccionar
cat > /etc/profile.d/atriz-robot.sh <<EOF
# Identidad del robot — generado por atriz-first-boot, NO editar a mano.
# Para cambiar el número: edita /boot/firmware/robot_id.txt y borra
# /var/lib/atriz-first-boot.done, luego reinicia.
export ATRIZ_ROBOT_ID=$ID2
export ATRIZ_NAMESPACE=$NS
export ROS_DOMAIN_ID=$ID_NUM
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
EOF
chmod 644 /etc/profile.d/atriz-robot.sh
echo "  ✓ /etc/profile.d/atriz-robot.sh  (ROS_DOMAIN_ID=$ID_NUM)"

# ── 6. Deshabilitarse ────────────────────────────────────────────────────────
mkdir -p /var/lib
date -u '+%Y-%m-%dT%H:%M:%SZ' > /var/lib/atriz-first-boot.done
echo "ROBOT_ID=$ID2" >> /var/lib/atriz-first-boot.done
systemctl disable atriz-first-boot.service 2>/dev/null || true
echo "  ✓ servicio deshabilitado (marca en /var/lib/atriz-first-boot.done)"

cat <<EOF

Robot $ID2 personalizado. Reinicia para que el hostname se aplique en todas partes:
    sudo reboot

Verificar después:
    hostname                 # $HOST
    echo \$ROS_DOMAIN_ID      # $ID_NUM
    ls -l /dev/rvr /dev/ttyUSB0
EOF
echo "════ fin ════"
