#!/usr/bin/env bash
#
# preparar_tarjeta.sh — deja una microSD recién grabada lista para arrancar
#
#   ⚠️  ESTO NO SE EJECUTA EN EL ROBOT. Se ejecuta en el PC (Linux o WSL) con la
#       microSD puesta, DESPUÉS de grabarla y ANTES del primer arranque.
#
#       sudo bash preparar_tarjeta.sh --id 07
#       sudo bash preparar_tarjeta.sh --id 07 --particion /media/tu/system-boot
#       sudo bash preparar_tarjeta.sh --id 07 --simular    # no escribe nada
#
# QUÉ RESUELVE
#
#   Hay tres cosas que TIENEN que estar bien antes del primer arranque, porque
#   después ya es tarde o mucho más incómodo:
#
#     1. cmdline.txt sin `console=serial0,115200`. La imagen de Ubuntu lo trae y
#        reserva el UART para la consola del kernel, dejándolo inservible para el
#        RVR. Si arrancas sin quitarlo, el robot no habla.
#     2. config.txt con `dtoverlay=disable-bt` bajo `[all]`, que mueve el PL011
#        (el UART bueno) a los pines GPIO14/15 donde está cableado el RVR.
#     3. robot_id.txt con el número del robot, que es lo que lee
#        atriz-first-boot para fijar hostname y ROS_DOMAIN_ID.
#
#   Hasta ahora esto se hacía a mano con el Bloc de notas en Windows. Para un
#   robot es tolerable; para 15 es una fuente de errores garantizada, y de los
#   silenciosos: una cabecera [all] olvidada no da ningún error, simplemente el
#   robot no funciona y no se sabe por qué.
#
# LA TRAMPA DE LA CABECERA [all]
#
#   config.txt se divide en secciones de placa: [pi4], [cm4], [pi02]... Una línea
#   solo se aplica si está antes de cualquier sección, dentro de [all], o dentro
#   de la sección de ESTA placa. La imagen de Ubuntu 24.04 **termina en [cm4]**,
#   así que añadir `dtoverlay=disable-bt` al final sin `[all]` lo mete dentro de
#   [cm4] y NO se aplica en un Raspberry Pi 4. Existe en el fichero y no hace
#   nada. Este script pone la cabecera siempre.
#
# LO QUE NO HACE
#
#   La regla udev de /dev/rvr, los systemctl y la higiene del SO viven en la
#   partición ext4 y necesitan el sistema arrancado. Eso lo hace provision.sh
#   por SSH, o va ya dentro de la imagen dorada.
#
# ESTADO
#   🟡 PROBADO EN SECO, no en una tarjeta real. El 2026-07-30 se ejecutó contra
#      dos copias de la partición FAT de rvr-01, verificando el RESULTADO y no
#      solo su salida:
#
#        · sobre una copia ya preparada  -> no toca nada (idempotente)
#        · sobre un cmdline.txt/config.txt reconstruidos tal como los trae
#          Ubuntu 24.04 (con console=serial0 y terminando en [cm4]):
#             - console=serial0 eliminado
#             - cmdline.txt sigue siendo UNA línea, sin '\n' final
#             - [all] añadido DESPUÉS de [cm4], y el awk confirma que las claves
#               quedan activas para [pi4]
#             - caso de control: 'dtoverlay=dwc2,dr_mode=host', que solo está
#               bajo [cm4], se detecta correctamente como INACTIVO
#             - dos ejecuciones seguidas -> una sola ocurrencia de disable-bt
#
#      📝 Lo que NO se ha probado: una microSD física, con su automontaje y su
#         sistema de ficheros FAT real. Al preparar el primer clon, comprobar
#         cada paso y corregir FLOTA.md.
#
set -uo pipefail

ID=""; PART=""; SIMULAR=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --id)        ID="${2:-}"; shift 2 ;;
        --particion) PART="${2:-}"; shift 2 ;;
        --simular)   SIMULAR=1; shift ;;
        -h|--help)   sed -n '2,50p' "$0" | sed 's/^#\{0,1\}//'; exit 0 ;;
        *) echo "opción desconocida: $1" >&2; exit 64 ;;
    esac
done

VERDE=$'\033[92m'; ROJO=$'\033[91m'; AMAR=$'\033[93m'; AZUL=$'\033[94m'; FIN=$'\033[0m'
say() { printf '\n%s▶ %s%s\n' "$AZUL" "$1" "$FIN"; }
ok()  { printf '  %s✓%s %s\n' "$VERDE" "$FIN" "$1"; }
mal() { printf '  %s✗%s %s\n' "$ROJO" "$FIN" "$1" >&2; }
avi() { printf '  %s!%s %s\n' "$AMAR" "$FIN" "$1"; }
morir(){ mal "$1"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
say "0/4 · Comprobaciones previas"

[[ -n "$ID" ]] || morir "falta --id NN. Ejemplo: sudo bash $0 --id 07"
[[ "$ID" =~ ^[0-9]{1,2}$ ]] || morir "--id debe ser un número de 1 o 2 cifras, no '$ID'"
ID_NUM=$((10#$ID))          # 10# fuerza base 10: '08' no es octal
(( ID_NUM >= 1 && ID_NUM <= 16 )) || morir "--id debe estar entre 1 y 16 (recibido $ID_NUM)"
ID2=$(printf '%02d' "$ID_NUM")
ok "robot $ID2  ->  hostname rvr-$ID2, ROS_DOMAIN_ID $ID_NUM"

# Localizar la partición FAT de arranque. Se identifica por su contenido, no por
# su nombre: montar la partición equivocada y escribir en ella sería destructivo.
if [[ -z "$PART" ]]; then
    for c in /media/*/system-boot /media/*/*/system-boot /mnt/system-boot /Volumes/system-boot; do
        [[ -d "$c" ]] && { PART="$c"; break; }
    done
fi
[[ -n "$PART" ]] || morir "no encuentro la partición de arranque. Pásala con --particion /ruta
       En Linux suele automontarse en /media/\$USER/system-boot.
       Si no, míralo con:  lsblk -o NAME,LABEL,MOUNTPOINT"
[[ -d "$PART" ]] || morir "'$PART' no existe o no es un directorio"

# Verificación de identidad de la partición: estos dos ficheros SIEMPRE están en
# la partición de arranque de una imagen de Ubuntu para Raspberry Pi.
for f in cmdline.txt config.txt; do
    [[ -f "$PART/$f" ]] || morir "'$PART' no parece la partición de arranque: falta $f.
       NO se escribe nada. Comprueba la ruta antes de repetir."
done
ok "partición de arranque: $PART"

if [[ ! -w "$PART" ]]; then
    morir "sin permiso de escritura en $PART. Ejecuta con sudo."
fi
[[ $SIMULAR -eq 1 ]] && avi "MODO SIMULACIÓN: no se escribirá nada"

STAMP="$(date +%Y%m%d-%H%M%S)"
respalda() {
    [[ $SIMULAR -eq 1 ]] && return 0
    cp -a "$1" "$1.bak-$STAMP" && ok "respaldo: $(basename "$1").bak-$STAMP"
}

# ─────────────────────────────────────────────────────────────────────────────
say "1/4 · cmdline.txt — liberar el puerto serie"

CMD="$PART/cmdline.txt"
if grep -q 'console=serial' "$CMD"; then
    respalda "$CMD"
    if [[ $SIMULAR -eq 0 ]]; then
        # cmdline.txt es UNA SOLA LÍNEA. Un salto de línea aquí impide arrancar,
        # asi que se edita con tr y printf, sin añadir '\n' al final.
        NUEVO="$(tr -d '\n' < "$CMD" | sed -E 's/[[:space:]]*console=serial[^[:space:]]*//g; s/  +/ /g; s/^ //; s/ $//')"
        printf '%s' "$NUEVO" > "$CMD"
    fi
    ok "quitado console=serial* (reservaba el UART para la consola del kernel)"
else
    ok "cmdline.txt ya estaba bien: no reserva el puerto serie"
fi
grep -q 'console=tty1' "$CMD" || avi "no hay console=tty1: no verás mensajes en un monitor HDMI"
printf '  contenido: %s\n' "$(cat "$CMD")"
# Una sola línea: si hay más de una, el arranque falla de formas confusas.
LINEAS=$(wc -l < "$CMD")
(( LINEAS <= 1 )) || mal "cmdline.txt tiene $LINEAS saltos de línea. DEBE ser una sola línea."

# ─────────────────────────────────────────────────────────────────────────────
say "2/4 · config.txt — dar el PL011 al RVR"

CFG="$PART/config.txt"

# ¿Está la clave activa PARA UN PI 4? Respeta las secciones de placa. Un
# 'dtoverlay=disable-bt' bajo [cm4] existe y no hace nada en un Pi 4.
clave_activa() {
    awk -v pat="$2" '
        /^[[:space:]]*\[/ { s=$0; sub(/^[[:space:]]*\[/,"",s); sub(/\].*$/,"",s); next }
        $0 ~ pat && (s=="" || s=="all" || s=="pi4") { hallado=1 }
        END { exit(hallado?0:1) }
    ' "$1"
}

# Un usercfg.txt sin 'include' que lo cargue es un fichero fantasma: el firmware
# no lo lee. En 24.04 no existe y no hay que crearlo.
if [[ -f "$PART/usercfg.txt" ]]; then
    if grep -qE '^[[:space:]]*include[[:space:]]+usercfg\.txt' "$CFG"; then
        avi "config.txt incluye usercfg.txt (patrón de 20.04): escribiendo ahí"
        CFG="$PART/usercfg.txt"
    else
        avi "hay usercfg.txt pero config.txt NO lo incluye: es un fichero fantasma, se ignora"
    fi
fi

FALTAN=()
clave_activa "$CFG" '^[[:space:]]*dtoverlay=disable-bt' \
    && ok "dtoverlay=disable-bt ya está activo para [pi4]" || FALTAN+=("dtoverlay=disable-bt")
clave_activa "$CFG" '^[[:space:]]*enable_uart=1' \
    && ok "enable_uart=1 ya está activo (24.04 lo trae por defecto)" || FALTAN+=("enable_uart=1")

if [[ ${#FALTAN[@]} -eq 0 ]]; then
    ok "nada que añadir a $(basename "$CFG")"
else
    respalda "$CFG"
    if [[ $SIMULAR -eq 0 ]]; then
        {
            echo
            echo "# ── Sphero RVR — añadido por preparar_tarjeta.sh el $STAMP ──────────────────"
            echo "# La cabecera [all] es OBLIGATORIA: sin ella estas líneas quedarían dentro de"
            echo "# la última sección de placa del fichero ([cm4] en la imagen de Ubuntu 24.04)"
            echo "# y NO se aplicarían en un Raspberry Pi 4."
            echo "#"
            echo "# disable-bt libera el PL011 (ttyAMA0) del Bluetooth y lo asigna a GPIO14/15,"
            echo "# donde está cableado el RVR. Sin esto el RVR queda en el mini-UART, cuyo"
            echo "# baudrate deriva con el reloj del VPU y produce fallos intermitentes."
            echo "[all]"
            printf '%s\n' "${FALTAN[@]}"
        } >> "$CFG"
    fi
    ok "añadido bajo [all] en $(basename "$CFG"): ${FALTAN[*]}"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "3/4 · robot_id.txt — la identidad de este robot"

RID="$PART/robot_id.txt"
if [[ -f "$RID" ]]; then
    ANT="$(grep -oE '^[[:space:]]*ROBOT_ID[[:space:]]*=[[:space:]]*[0-9]+' "$RID" | grep -oE '[0-9]+$' || echo '?')"
    [[ "$ANT" != "$ID2" && "$ANT" != "?" ]] && avi "robot_id.txt decía ROBOT_ID=$ANT, se cambia a $ID2"
    respalda "$RID"
fi
if [[ $SIMULAR -eq 0 ]]; then
    cat > "$RID" <<EOF
# Identidad de este robot. Editable desde Windows, macOS o Linux sin arrancar la Pi.
# Lo lee atriz-first-boot.service en el primer arranque, y de aquí salen:
#     hostname        rvr-$ID2
#     ROS_DOMAIN_ID   $ID_NUM      (un dominio por robot: ARQUITECTURA.md, Decisión 1)
#     namespace       /rvr_$ID2
#
# Para reasignar este robot: cambia el número, borra
# /var/lib/atriz-first-boot.done desde el sistema arrancado, y reinicia.
ROBOT_ID=$ID2
EOF
fi
ok "ROBOT_ID=$ID2  ->  rvr-$ID2 · ROS_DOMAIN_ID=$ID_NUM · /rvr_$ID2"

# ─────────────────────────────────────────────────────────────────────────────
say "4/4 · Resumen y siguiente paso"

if [[ $SIMULAR -eq 1 ]]; then
    avi "no se ha escrito nada (--simular). Repite sin --simular para aplicarlo."
    exit 0
fi

sync
ok "sync completado: los datos están en la tarjeta, ya se puede extraer"

cat <<EOF

────────────────────────────────────────────────────────────────────────────
  Tarjeta del robot $ID2 lista para el primer arranque.

  AHORA:
    1. Expulsa la tarjeta con seguridad y ponla en el robot $ID2.
    2. Arranca. Espera 2-3 minutos: cloud-init hace su trabajo inicial.
    3. NO hace falta reserva DHCP: el robot toma la IP fija que le da red.txt
       (10.14.7.NN en el laboratorio) Y DHCP a la vez. Se llega por nombre:
       rvr-$ID2.local, que funciona en las dos redes sin tocar el router.
    4. Entra por SSH y comprueba que es quien debe ser:

         ssh sphero@rvr-$ID2.local        # o por la IP del router
         hostname                         # rvr-$ID2
         echo \$ROS_DOMAIN_ID              # $ID_NUM

    5. Y pásale el verificador:

         bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware

  SI LA TARJETA SE GRABÓ CON LA IMAGEN DORADA, con eso ya está: el resto
  (UART, higiene, ROS 2, workspace) viene dentro. Rellena la tabla de
  asignación de 03_operacion/FLOTA.md y pasa al siguiente robot.

  SI ES UNA INSTALACIÓN LIMPIA de Ubuntu Server, falta aprovisionarla:

         sudo bash ~/atriz_migracion/scripts/provision.sh

  Respaldos de esta ejecución: *.bak-$STAMP en la propia partición.
────────────────────────────────────────────────────────────────────────────
EOF
