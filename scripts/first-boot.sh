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

# ── 5-bis. Red: genera /etc/netplan/60-atriz.yaml desde red.txt ──────────────
#
# 🔴 POR QUÉ AQUÍ Y NO EN /etc/netplan A MANO
#    Una IP estática equivocada deja el robot SIN dirección en esa LAN, y sin SSH
#    para arreglarlo. `red.txt` vive en la partición FAT, que se edita desde
#    cualquier PC metiendo la microSD — sin arrancar la Pi. Es la misma idea que
#    `robot_id.txt`, que ya funciona así.
#
# 🔴 LAS DOS DIRECCIONES ESTÁTICAS SE PONEN SIEMPRE, en las dos redes. Es lo que
#    permite mudarse de casa al laboratorio sin tocar nada: en cada sitio funciona
#    la que corresponde y la otra queda como un alias inofensivo.
#
#    ⚠️ Pero la RUTA POR DEFECTO no puede duplicarse: una ruta hacia un gateway
#       que no existe en la red actual **rompe el tráfico de salida**, porque el
#       sistema la da por válida igualmente (la dirección la hace «on-link»). Por
#       eso `RUTA_POR_DEFECTO` elige UNA, y por defecto la deja en manos del DHCP.
RED_FILE=/boot/firmware/red.txt

if [[ ! -f "$RED_FILE" ]]; then
    echo "  ! no existe $RED_FILE: la red se queda como esté (normalmente DHCP)"
    echo "    Para configurarla: copia scripts/red.txt.ejemplo a $RED_FILE,"
    echo "    rellénalo, borra /var/lib/atriz-first-boot.done y reinicia."
else
    # Lectura tolerante: ignora comentarios y espacios. No se usa `source` a
    # propósito — este fichero lo edita una persona desde Windows y un carácter
    # raro no debe poder ejecutar nada.
    leer_red() {
        sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$RED_FILE" \
            | head -1 | tr -d '\r' | sed 's/[[:space:]]*$//'
    }
    LAB_SSID=$(leer_red LAB_SSID);       LAB_PASS=$(leer_red LAB_PASS)
    LAB_IP=$(leer_red LAB_IP);           LAB_BASE=$(leer_red LAB_BASE)
    LAB_OCTETO=$(leer_red LAB_OCTETO);   LAB_PREFIJO=$(leer_red LAB_PREFIJO)
    LAB_GATEWAY=$(leer_red LAB_GATEWAY)
    CASA_SSID=$(leer_red CASA_SSID);     CASA_PASS=$(leer_red CASA_PASS)
    CASA_IP=$(leer_red CASA_IP);         CASA_PREFIJO=$(leer_red CASA_PREFIJO)
    CASA_GATEWAY=$(leer_red CASA_GATEWAY)
    DHCP=$(leer_red DHCP);               RUTA=$(leer_red RUTA_POR_DEFECTO)
    DNS=$(leer_red DNS)

    # La IP del laboratorio: explícita si la hay, derivada si no.
    if [[ -z "$LAB_IP" && -n "$LAB_BASE" && -n "$LAB_OCTETO" ]]; then
        LAB_IP="$LAB_BASE.$(( LAB_OCTETO + ID_NUM ))"
        echo "  · LAB_IP derivada del número de robot: $LAB_IP"
    fi

    if [[ -z "$LAB_SSID" || -z "$LAB_IP" ]]; then
        echo "  ! $RED_FILE incompleto (falta LAB_SSID o la IP): red sin tocar"
    else
        YAML=/etc/netplan/60-atriz.yaml
        {
            echo "# Generado por atriz-first-boot el $(date -u '+%Y-%m-%dT%H:%M:%SZ')."
            echo "# NO EDITAR A MANO: se regenera desde /boot/firmware/red.txt."
            echo "network:"
            echo "  version: 2"
            echo "  renderer: networkd"
            echo "  wifis:"
            echo "    wlan0:"
            echo "      optional: true"
            [[ "${DHCP,,}" == "si" || "${DHCP,,}" == "sí" ]] \
                && echo "      dhcp4: true" || echo "      dhcp4: false"
            echo "      dhcp4-overrides:"
            echo "        use-routes: true"
            echo "      access-points:"
            printf '        "%s":\n          password: "%s"\n' "$LAB_SSID" "$LAB_PASS"
            [[ -n "$CASA_SSID" ]] && \
                printf '        "%s":\n          password: "%s"\n' "$CASA_SSID" "$CASA_PASS"
            echo "      addresses:"
            echo "        - $LAB_IP/${LAB_PREFIJO:-24}"
            [[ -n "$CASA_IP" ]] && echo "        - $CASA_IP/${CASA_PREFIJO:-24}"
            # 🔴 `routes:`, NUNCA `gateway4:` — obsoleto en netplan y en 24.04 ya
            #    avisa. La configuración vieja del laboratorio lo usaba.
            case "${RUTA,,}" in
                lab)  [[ -n "$LAB_GATEWAY" ]] && {
                          echo "      routes:"
                          echo "        - to: default"
                          echo "          via: $LAB_GATEWAY"; } ;;
                casa) [[ -n "$CASA_GATEWAY" ]] && {
                          echo "      routes:"
                          echo "        - to: default"
                          echo "          via: $CASA_GATEWAY"; } ;;
            esac
            if [[ -n "$DNS" ]]; then
                echo "      nameservers:"
                echo "        addresses: [${DNS}]"
            fi
        } > "$YAML"
        # 🔴 600: lleva la PSK del WiFi en claro. El propio netplan avisa si no.
        chmod 600 "$YAML"

        if netplan generate 2>/tmp/netplan.err; then
            echo "  ✓ $YAML generado (LAB $LAB_IP${CASA_IP:+ · CASA $CASA_IP})"
            echo "    ruta por defecto: ${RUTA:-dhcp}"
        else
            echo "  ! netplan RECHAZÓ la configuración generada:"
            sed 's/^/      /' /tmp/netplan.err
            echo "    se retira para no dejar el robot sin red"
            rm -f "$YAML"
            netplan generate 2>/dev/null || true
        fi
    fi
fi

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
