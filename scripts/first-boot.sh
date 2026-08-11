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

# ── Modos ────────────────────────────────────────────────────────────────────
#   (sin argumentos)  primer arranque completo: identidad + red, y se deshabilita
#   --solo-red        REGENERA SOLO /etc/netplan/60-atriz.yaml y para.
#
# 🔴 `--solo-red` existe porque cambiar una IP no debería costar un reinicio.
#    Con 16 robots, «edita red.txt y reinicia» es la diferencia entre un minuto
#    y una tarde. No toca hostname, ni machine-id, ni las claves SSH, ni la
#    marca de first-boot: solo escribe el netplan y lo valida.
#
# ⚠️ Y NO APLICA la configuración: la deja escrita y validada. Aplicarla es
#    `netplan try`, que revierte solo si te quedas sin conexión. Separar
#    «escribir» de «aplicar» es lo que hace que una IP mal puesta no te deje
#    fuera del robot.
SOLO_RED=no
case "${1:-}" in
    --solo-red) SOLO_RED=si ;;
    '')         ;;
    -h|--help)  sed -n '2,16p' "$0"; exit 0 ;;
    *)          echo "uso: $0 [--solo-red]" >&2; exit 2 ;;
esac
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
if [[ $SOLO_RED == no ]]; then
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
fi   # fin de las secciones 2-5, que --solo-red se salta

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
        # 🔴 OBSOLETO desde el 2026-08-04, y se avisa a gritos en vez de callar.
        #    El administrador de red asigna las direcciones UNA A UNA, así que una
        #    derivada casi seguro NO es la que te han dado. Y rvr-01 lo demuestra:
        #    tiene 10.14.7.7 mientras este esquema daría 10.14.7.101 — el robot de
        #    referencia no seguía su propio esquema, y eso se hereda a la imagen
        #    dorada. Se conserva el cálculo para no romper un red.txt ya escrito,
        #    pero la plantilla ya no lo ofrece.
        echo "  ! LAB_IP DERIVADA del número de robot: $LAB_IP"
        echo "    ⚠️ El esquema derivado está OBSOLETO: las direcciones del"
        echo "       laboratorio las asigna el administrador de red, una a una."
        echo "       Pon la que te hayan dado en LAB_IP de /boot/firmware/red.txt."
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
            # 🔴 CAMBIADO EL 2026-08-04 · AQUÍ YA NO VAN LAS DIRECCIONES.
            #    Netplan asigna las direcciones A LA INTERFAZ, no al punto de
            #    acceso: no sabe dar una IP distinta por SSID. Por eso el robot
            #    llevaba SIEMPRE las dos estáticas y `rvr-NN.local` resolvía a
            #    cuatro direcciones, de las que dos son un agujero negro desde
            #    cualquier red. El navegador probaba en orden y se colgaba ~21 s
            #    en cada una: el muro no encontraba NINGÚN robot.
            #    Las direcciones pasan a los `.network` con `[Match] SSID=` de
            #    más abajo. Netplan se queda con lo que sí sabe hacer: la
            #    ASOCIACIÓN wifi (`netplan-wpa-wlan0.service`).
            #    Diseño: 00_auditoria/planes/2026-08-04-direccionamiento-flota.md
            if [[ -n "$DNS" ]]; then
                echo "      nameservers:"
                echo "        addresses: [${DNS}]"
            fi
        } > "$YAML"
        # 🔴 600: lleva la PSK del WiFi en claro. El propio netplan avisa si no.
        chmod 600 "$YAML"

        # ── Una dirección por red, emparejada por SSID ───────────────────────
        # `systemd-networkd` SÍ sabe hacerlo: `[Match] SSID=` existe desde
        # systemd v244 —«shell-style globs matching the SSID of the currently
        # connected wireless LAN»— y aquí corre la 255.
        #
        # 🔴 EL ORDEN ES LO QUE LO HACE FUNCIONAR: estos ficheros van en /etc y
        #    ordenan 05/06, así que se evalúan ANTES que el
        #    `10-netplan-wlan0.network` que netplan deja en /run. Si el SSID no
        #    casa con ninguno, cae al de netplan y el robot se comporta como
        #    antes: sigue alcanzable. El «si no sé, no toco» lo implementa el
        #    EMPAREJADOR, no un script que pelee con networkd.
        #
        # 🔴 Y se usa "$LAB_IP" **ya derivada** de LAB_BASE+LAB_OCTETO más
        #    arriba, no la clave del fichero: con la plantilla tal cual
        #    `LAB_IP=` viene VACÍA y esto no escribiría nada en 15 de los 16
        #    robots. Es el error exacto que hundió el intento anterior.
        escribir_red_ssid() {
            local nombre="$1" ssid="$2" ip="$3" pref="$4" gw="$5" fich
            fich="/etc/systemd/network/$nombre"
            # Se niega antes que dejar un robot sin ruta: sin puerta no hay NTP,
            # y esta Pi no tiene RTC.
            if [[ -z "$ssid" || -z "$ip" ]]; then
                rm -f "$fich"; return 0
            fi
            if [[ -z "$gw" ]]; then
                echo "  ! $nombre: sin puerta de enlace en red.txt — NO se escribe"
                echo "    (sin ruta por defecto no hay NTP, y esta Pi no tiene RTC)"
                rm -f "$fich"; return 0
            fi
            {
                echo "# Generado por atriz-first-boot el $(date -u '+%Y-%m-%dT%H:%M:%SZ')."
                echo "# NO EDITAR A MANO: se regenera desde /boot/firmware/red.txt."
                echo "# Una dirección por red. Ver 2026-08-04-direccionamiento-flota.md"
                echo "[Match]"
                echo "Name=wlan0"
                echo "SSID=$ssid"
                echo ""
                echo "[Network]"
                echo "Address=$ip/${pref:-24}"
                echo "Gateway=$gw"
                [[ -n "$DNS" ]] && echo "DNS=${DNS//,/ }"
                echo "IPv6AcceptRA=no"
            } > "$fich"
            chmod 644 "$fich"
            echo "  ✓ $nombre → $ip/${pref:-24} vía $gw  (SSID «$ssid»)"
        }
        mkdir -p /etc/systemd/network
        escribir_red_ssid 05-atriz-lab.network  "$LAB_SSID"  "$LAB_IP"  "${LAB_PREFIJO:-24}"  "$LAB_GATEWAY"
        escribir_red_ssid 06-atriz-casa.network "$CASA_SSID" "$CASA_IP" "${CASA_PREFIJO:-24}" "$CASA_GATEWAY"

        # 🔴 NUNCA una ruta FIJA en /tmp. `fs.protected_regular=2` (Ubuntu 24.04)
        #    impide a **root** escribir en un fichero de /tmp que no le pertenece.
        #    Con un `/tmp/netplan.err` dejado por otro usuario, la redirección
        #    falla, bash NO llega a ejecutar el comando, y el script acaba
        #    imprimiendo el contenido RANCIO como si fuera el error de ahora.
        #    Pasó el 2026-08-01: se leyó un fallo de systemd que nunca ocurrió y
        #    se borró un netplan que estaba bien.
        ERR=$(mktemp) || ERR=/dev/null
        if netplan generate 2>"$ERR"; then
            echo "  ✓ $YAML generado (LAB $LAB_IP${CASA_IP:+ · CASA $CASA_IP})"
            echo "    ruta por defecto: ${RUTA:-dhcp}"
        else
            echo "  ! netplan RECHAZÓ la configuración generada:"
            sed 's/^/      /' "$ERR"
            echo "    se retira para no dejar el robot sin red"
            rm -f "$YAML"
            netplan generate 2>/dev/null || true
        fi
        [[ "$ERR" != /dev/null ]] && rm -f "$ERR"

    fi
fi

# ── 6. Deshabilitarse ────────────────────────────────────────────────────────
if [[ $SOLO_RED == si ]]; then
    echo "  (--solo-red: no se toca la marca de first-boot)"
    echo
    echo "  SIGUIENTE PASO, y hazlo tu a mano. CUAL de los dos depende de si la"
    echo "  direccion por la que estas conectado SOBREVIVE al cambio:"
    echo
    if grep -qiE '^[[:space:]]*DHCP[[:space:]]*=[[:space:]]*no' "$RED_FILE" 2>/dev/null; then
        echo "      sudo reboot        <-- ESTE, porque red.txt lleva DHCP=no"
        echo
        echo "  Con DHCP=no, aplicar QUITA la direccion del DHCP por la que estas"
        echo "  conectado: la sesion SSH se corta, no hay quien confirme el"
        echo "  'netplan try', y a los 90 s revierte. Siempre. Reinicia y vuelve"
        echo "  a entrar por nombre: ssh sphero@\$(hostname).local"
    else
        echo "      sudo netplan try --timeout 90"
        echo "  Aplica la red y la REVIERTE sola si pierdes la conexion."
        echo "  Sirve porque red.txt NO lleva DHCP=no: la direccion actual"
        echo "  sobrevive y puedes confirmar. (Verificado en rvr-01 el"
        echo "  2026-08-01: wlan0 con TRES direcciones IPv4 a la vez.)"
    fi
    echo
    echo "  Si tras el cambio el robot no responde: red.txt vive en la FAT."
    echo "  Metes la tarjeta en cualquier PC, lo corriges y arrancas otra vez."
    exit 0
fi

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
