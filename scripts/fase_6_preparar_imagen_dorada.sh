#!/usr/bin/env bash
#
# Fase 6 — Preparar el robot de referencia para convertirlo en IMAGEN DORADA
#
#     sudo bash fase_6_preparar_imagen_dorada.sh
#     sudo poweroff        # y hacer el dd desde un PC
#
# 📝 NO VERIFICADO. Escrito antes de disponer de un segundo robot para probarlo.
#    Al clonar el primero, verificar cada paso y corregir FLOTA.md.
#
# QUÉ HACE Y POR QUÉ
#
#   Clonar una tarjeta tal cual produce 16 robots con la MISMA identidad, y eso
#   rompe cosas de formas confusas:
#
#     machine-id igual      -> el servidor DHCP puede dar la MISMA IP a dos robots
#     claves SSH de host    -> "REMOTE HOST IDENTIFICATION HAS CHANGED" al saltar
#                              de robot a robot, y ningún aviso real si hay un
#                              intruso
#     hostname igual        -> imposible saber a qué robot estás conectado
#     ROS_DOMAIN_ID igual   -> los robots se ven entre sí en DDS. Es exactamente
#                              lo que la Decisión 1 de ARQUITECTURA.md evita
#
#   Este script BORRA todo lo que debe ser único e instala first-boot.service,
#   que lo regenera en el primer arranque leyendo /boot/firmware/robot_id.txt
#
# ⚠️  DESPUÉS DE EJECUTARLO, ESTE ROBOT YA NO TIENE IDENTIDAD.
#     Al arrancar leerá robot_id.txt como cualquier clon. Es lo correcto: el
#     robot de referencia pasa a ser el robot 01.
#
set -uo pipefail

[[ $EUID -ne 0 ]] && { echo "Ejecuta con sudo: sudo bash $0" >&2; exit 1; }

say()  { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
avis() { printf '  \033[1;33m!\033[0m %s\n' "$1"; }

REAL_USER="${SUDO_USER:-sphero}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat <<'EOF'
════════════════════════════════════════════════════════════════════════════
  Esto prepara ESTE robot para ser clonado. Borra su identidad única.
  Solo debe ejecutarse cuando el robot funciona del todo y está verificado.
════════════════════════════════════════════════════════════════════════════
EOF
read -rp "  ¿Continuar? Escribe 'si' para confirmar: " C
[[ "$C" != "si" ]] && { echo "  Cancelado."; exit 0; }

# ─────────────────────────────────────────────────────────────────────────────
say "0/6 · Puerta: ¿este robot está de verdad como dice el repositorio?"

# 🔴 ESTO BLOQUEA, no avisa. Y es la diferencia entre este script y el de antes.
#
#    Hasta el 2026-08-03 esta fase avisaba mucho y no impedía nada. Ese día se
#    midió que fase_7_systemd.sh llevaba tres días sin ejecutarse: atriz-nav
#    estaba en git, estaba en el instalador, y NO estaba en el sistema. Una
#    imagen hecha en ese momento habría salido sin navegación — en los 16
#    robots, y sin que nadie lo notara hasta necesitarla.
#    Evidencia: 00_auditoria/evidencia/63_alineacion_ANTES.txt
#
#    Un robot divergido no se clona: se arregla y se vuelve a intentar. Una
#    divergencia aquí se multiplica por 16 y se descubre semanas después.
#
# 📝 Se ejecuta como el usuario real, no como root: el verificador comprueba
#    cosas del $HOME del usuario, y con root miraría /root.
VERIF="$SCRIPTS_DIR/verificar_robot.sh"
if [[ ! -f "$VERIF" ]]; then
    echo "  ✗ no encuentro $VERIF. Sin él no se puede saber si este robot" >&2
    echo "    coincide con el repositorio, y no se prepara la imagen." >&2
    exit 1
fi
# ⚠️ Los TRES códigos de salida del verificador significan cosas distintas, y
#    tratarlos igual rompería la puerta de una de dos maneras:
#      0  todo bien
#      1  hay FALLOS        -> se bloquea. No es negociable.
#      2  solo AVISOS       -> se pregunta. Si bloqueara, la puerta sería
#                             inusable —siempre hay algún aviso— y acabaría
#                             desactivada, que es como muere un control.
#    Pero tampoco se pasan de largo: un aviso multiplicado por 16 deja de ser
#    un aviso (los permisos de red.txt, por ejemplo, exponen la PSK del WiFi).
sudo -u "$REAL_USER" bash "$VERIF" --breve
SALIDA_VERIF=$?
case $SALIDA_VERIF in
    0)  ok "el verificador pasa sin avisos: el robot coincide con el repositorio" ;;
    2)  avis "el verificador pasa PERO con avisos (ver arriba)."
        avis "Un aviso en el robot de referencia se copia a los 16. Míralos ahora,"
        avis "no cuando estén repartidos."
        read -rp "  ¿Seguir de todas formas? Escribe 'si': " CA
        [[ "$CA" != "si" ]] && { echo "  Cancelado. Arregla los avisos y vuelve."; exit 0; } ;;
    *)  echo >&2
        echo "  ✗ EL VERIFICADOR FALLA (salida $SALIDA_VERIF). NO se prepara la imagen." >&2
        echo "    Arregla lo de arriba y vuelve a ejecutar este script." >&2
        echo "    Si algún fallo es del RVR apagado, enciéndelo: la imagen se hace" >&2
        echo "    de un robot que funciona, no de uno que casi funciona." >&2
        exit 1 ;;
esac

# 🔴 AÑADIDO el 2026-08-14, antes de la PRIMERA ejecución real: el driver se
#    comprueba AQUÍ, en la puerta, y no solo en el paso 4. El orden viejo
#    borraba la identidad (pasos 1-3: profile.d, machine-id, claves de host)
#    y SOLO ENTONCES descubría el driver corriendo y abortaba — dejando un
#    robot a MEDIO preparar, con el error en pantalla y la identidad ya
#    borrada. La puerta se cruza entera o no se cruza.
if systemctl is-active --quiet atriz-robot 2>/dev/null; then
    echo >&2
    echo "  ✗ atriz-robot está ACTIVO. La imagen se hace de un robot PARADO y" >&2
    echo "    parado LIMPIO (el apagado ordenado apaga LEDs y luz del sensor):" >&2
    echo "        sudo systemctl stop atriz-robot" >&2
    echo "        systemctl is-failed atriz-robot   # debe decir 'inactive', no 'failed'" >&2
    echo "    y vuelve a lanzar este script." >&2
    exit 1
fi
ok "atriz-robot está parada: se puede preparar la imagen"

# 🔴🔴 LA CLAVE PÚBLICA DEL TESTIGO — PUERTA DESDE EL 2026-08-15 (A7, Fase B)
#
#    Desde que rosbridge exige testigo, `/etc/atriz/testigo.pub` **deja de ser
#    cosa solo del Taller**: sin ella, `atriz_rosbridge.py` falla cerrado y el
#    robot se queda **invisible para la web**. Un clon sin clave arranca, parece
#    sano, y no hay forma de hablarle desde la interfaz.
#
#    Va en la imagen porque los 16 comparten el MISMO servidor web, así que es
#    la misma clave para todos. Y se comprueba AQUÍ, en la puerta, por lo mismo
#    que el driver: descubrirlo después de borrar la identidad deja un robot a
#    medio preparar.
if [[ ! -s /etc/atriz/testigo.pub ]]; then
    echo >&2
    echo "  ✗ falta /etc/atriz/testigo.pub (o está vacía)." >&2
    echo "    Sin ella los 16 clones quedarán INVISIBLES PARA LA WEB: rosbridge" >&2
    echo "    exige testigo desde la Fase B y sin la clave no puede verificarlo." >&2
    echo "    Se emite en el PC, dentro de atriz-lab:" >&2
    echo "        node herramientas/publicar_clave.mjs" >&2
    echo "    y se instala aquí con:  sudo tee /etc/atriz/testigo.pub" >&2
    exit 1
fi
ok "clave pública del testigo presente: los clones podrán hablar con la web"

# ─────────────────────────────────────────────────────────────────────────────
say "1/6 · Instalar el servicio de personalización de primer arranque"

install -m 755 "$SCRIPTS_DIR/first-boot.sh"       /usr/local/sbin/atriz-first-boot.sh
install -m 644 "$SCRIPTS_DIR/first-boot.service"  /etc/systemd/system/atriz-first-boot.service
systemctl daemon-reload
systemctl enable atriz-first-boot.service
ok "atriz-first-boot.service habilitado"

# Plantilla del fichero de identidad, en la partición FAT (editable desde cualquier PC)
if [[ ! -f /boot/firmware/robot_id.txt ]]; then
    # ⚠️ NINGÚN DÍGITO EN LOS COMENTARIOS, y no es cosmético.
    #    El comentario decía «Rango válido: 01 a 16», y el parser que usaban
    #    provision.sh y fase_7 (`tr -dc '0-9' | head -c2`) leía los dos primeros
    #    dígitos del FICHERO ENTERO: devolvía 01 con cualquier ROBOT_ID.
    #    El parser ya está anclado en los cuatro sitios, pero la plantilla se
    #    deja limpia igualmente: una plantilla que arma un fallo si alguien
    #    copia el parser viejo es una trampa esperando a que alguien caiga.
    #    Medido el 2026-08-03: 00_auditoria/evidencia/64_parser_robot_id.txt
    cat > /boot/firmware/robot_id.txt <<'EOF'
# Identidad de este robot. Editable desde Windows, macOS o Linux sin arrancar la Pi.
# Cambia el número de la última línea y nada más.
# Cada robot del laboratorio tiene el suyo, de uno a dieciséis.
ROBOT_ID=01
EOF
    ok "/boot/firmware/robot_id.txt creado (ROBOT_ID=01)"
else
    avis "robot_id.txt ya existía: $(grep -E '^ROBOT_ID' /boot/firmware/robot_id.txt)"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "1-bis/6 · Borrar la IDENTIDAD ROS y la marca de first-boot"

# 🔴 SIN ESTO, LA PERSONALIZACIÓN NO SE EJECUTA EN LOS CLONES.
#
#   `atriz-first-boot.service` lleva `ConditionPathExists=!/var/lib/atriz-first-boot.done`
#   — o sea que NO corre si esa marca existe. Si el robot de referencia llega a
#   ejecutar first-boot alguna vez, la marca se queda en la imagen y **los 16
#   clones se saltan la personalización entera**: mismo hostname, mismo
#   ROS_DOMAIN_ID, los 16 viéndose en DDS. Y sin dar ningún error.
rm -f /var/lib/atriz-first-boot.done && ok "marca de first-boot borrada"

# Y el fichero de identidad, por lo mismo: si sobrevive, el clon arranca con el
# ROS_DOMAIN_ID del robot de referencia hasta que first-boot lo pise. Si
# first-boot fallara —robot_id.txt mal escrito— el clon se quedaría ahí para
# siempre, en silencio. Que lo cree first-boot y nadie más.
rm -f /etc/profile.d/atriz-robot.sh && ok "/etc/profile.d/atriz-robot.sh borrado"
avis "el clon NO tendrá ROS_DOMAIN_ID hasta que first-boot lea robot_id.txt"
avis "y el envoltorio del servicio SE NIEGA A ARRANCAR sin él — es lo correcto"

say "2/6 · Borrar el machine-id (systemd lo regenera al arrancar)"
# Un machine-id duplicado hace que el DHCP pueda asignar la misma IP a dos robots
: > /etc/machine-id
rm -f /var/lib/dbus/machine-id
ln -sf /etc/machine-id /var/lib/dbus/machine-id
ok "machine-id vaciado"

# ─────────────────────────────────────────────────────────────────────────────
say "3/6 · Borrar las claves SSH de host (se regeneran al arrancar)"
rm -f /etc/ssh/ssh_host_*
ok "claves de host eliminadas"
avis "en el primer arranque de cada clon, tu PC avisará de una huella nueva: es lo esperado"

# ─────────────────────────────────────────────────────────────────────────────
say "4/6 · Limpiar logs, cachés e historial"
journalctl --rotate >/dev/null 2>&1 || true
journalctl --vacuum-time=1s >/dev/null 2>&1 || true
rm -rf /var/log/*.gz /var/log/*.[0-9] /var/log/journal/* 2>/dev/null
# 🔴 Los ficheros de rsyslog EN CURSO no los cubre el glob de arriba, que solo
#    caza los ROTADOS. En rvr-01 el 2026-08-15 `/var/log/syslog` tenía 16 MB
#    vivos: sin esto, la imagen dorada repartiría el log del robot que la
#    construyó a los otros 15. Desde esa fecha fase_1 para rsyslog, así que en
#    una imagen nueva estarán vacíos — pero una construida sobre un robot
#    anterior no, y el coste de vaciarlos es cero.
: > /var/log/syslog   2>/dev/null || true
: > /var/log/kern.log 2>/dev/null || true
: > /var/log/auth.log 2>/dev/null || true
: > /var/log/wtmp  2>/dev/null || true
: > /var/log/btmp  2>/dev/null || true
: > /var/log/lastlog 2>/dev/null || true
apt-get clean
rm -f  "$REAL_HOME/.bash_history" /root/.bash_history
rm -rf "$REAL_HOME/.cache/pip"

# 🔴 ~/.ros/log NO SE BORRA CON EL DRIVER CORRIENDO.
#
#    El 2026-08-03 se hizo `rm -rf ~/.ros/log/*` con atriz-robot activo. Al
#    pararlo después, el sistema de launch de ROS 2 REABRE su fichero de log
#    para cerrarlo, no lo encontró, y reventó:
#
#      FileNotFoundError: '.../.ros/log/2026-08-03-12-30-38-…-699/launch.log'
#      State 'stop-sigterm' timed out. Killing.  ->  SIGKILL a los 8 procesos
#
#    El apagado limpio nunca terminó y el servicio quedó en `failed`. Aquí eso
#    sería peor: pasa justo antes del `dd`, así que la imagen saldría de un
#    robot medio matado, y el fallo se repartiría a los 16.
#    Evidencia: 00_auditoria/evidencia/63_alineacion_DESPUES.txt
if systemctl is-active --quiet atriz-robot 2>/dev/null; then
    avis "atriz-robot está ACTIVO. No se toca ~/.ros/log con el driver vivo."
    avis "Párala primero y comprueba que paró LIMPIA (no basta con que pare):"
    avis "    sudo systemctl stop atriz-robot"
    avis "    systemctl is-failed atriz-robot     # debe decir 'inactive', no 'failed'"
    PROBLEMAS_LIMPIEZA=1
else
    # Y aunque esté parada: si quedó en `failed`, el apagado no fue limpio y hay
    # que saberlo antes de clonar, no después.
    if systemctl is-failed --quiet atriz-robot 2>/dev/null; then
        avis "atriz-robot está en 'failed': su último apagado NO fue limpio."
        avis "    sudo systemctl reset-failed atriz-robot"
    fi
    rm -rf "$REAL_HOME/.ros/log"
fi

# 📝 Medido en rvr-01 el 2026-08-03, antes de limpiar: ~/.ros/log 246 dirs y
#    43 MB, ~/atriz_ws/log 84 dirs y 13 MB. Se multiplicaba por 16 sin aportar
#    nada, y encima falsea el «este robot está recién hecho».
rm -rf "$REAL_HOME/atriz_ws/log" "$REAL_HOME/nav_logs"
rm -f  "$REAL_HOME/atriz_ws"/frames_*.gv "$REAL_HOME/atriz_ws"/frames_*.pdf

# 🔴 Los workspaces parásitos bajo src/: colcon compila ahí y el cambio nunca
#    llega al sistema. Clonarlos reparte el fallo a los 16.
#    A cualquier profundidad — el que había en rvr-01 estaba cuatro niveles
#    abajo y la guarda de compilar.sh, que solo miraba uno, no lo veía.
find "$REAL_HOME/atriz_ws/src" -type d \( -name build -o -name install -o -name log \) \
     -prune -exec rm -rf {} + 2>/dev/null

# 🔴🔴 LOS MAPAS DEL ROBOT DE REFERENCIA NO SE CLONAN, Y ESTO NO ES HIGIENE:
#    ES CORRECCIÓN. Un mapa que no es del sitio hace que **Nav2 mienta**.
#
#    Medido el 2026-08-07 (evidencias 83 y 84), mismo cuarto, mismo recorrido,
#    lo único distinto el mapa:
#
#              mapa rancio   tanda 1   tanda 2
#      AMCL       45,0 cm     8,9 cm   15,2 cm
#      al objetivo 41,3 cm    6,1 cm   11,8 cm    (tolerancia de Nav2: 10 cm)
#      Nav2 dijo   ÉXITO      ÉXITO    ÉXITO      <- 🔴 LAS TRES VECES
#
#    🔴 El síntoma es que **no hay síntoma**: Nav2 declara el objetivo cumplido,
#       `/estado_navegacion` dice FUNCIONANDO y el robot está medio metro de
#       donde cree. Clonar el mapa de esta Pi repartiría eso por 16, y en 15 de
#       ellos ni siquiera sería el mismo cuarto.
#
#    Y se borra TAMBIÉN la línea `ATRIZ_MAPA` de /etc/default/atriz: dejarla
#    apuntando a un fichero que ya no existe hace que `atriz-nav.sh` falle alto
#    —que es lo correcto y lo que se quiere— pero con un mensaje que habla de un
#    mapa del robot 01. Se deja el fichero SIN esa línea, y entonces el aviso
#    que sale es el suyo: «no hay mapa, mapea el aula».
if [[ -d "$REAL_HOME/mapas" ]]; then
    N_MAPAS=$(find "$REAL_HOME/mapas" -maxdepth 1 -name '*.yaml' | wc -l)
    rm -rf "${REAL_HOME:?}/mapas"/*
    ok "mapas del robot de referencia borrados ($N_MAPAS) — cada aula mapea el suyo"
fi
if [[ -f /etc/default/atriz ]] && grep -q '^ATRIZ_MAPA=' /etc/default/atriz; then
    sed -i 's|^ATRIZ_MAPA=.*|# ATRIZ_MAPA=  <- 🔴 SIN VALOR A PROPÓSITO. Mapea TU aula y pon aquí su .yaml.\n#              Un mapa que no es de este sitio hace que Nav2 diga «llegué»\n#              estando a medio metro (evidencia 84). Ver maps/README.md.|' \
        /etc/default/atriz
    ok "ATRIZ_MAPA vaciado en /etc/default/atriz — se rellena por aula"
fi

# Los .bak-* de /etc: son el rollback de fase_1, así que se MUEVEN, no se
# borran. Y el de apt hace que apt avise en cada ejecución (verificar_robot.sh).
# ⚠️ NO se tocan /etc/.resolv.conf.systemd-resolved.bak ni /boot/firmware/*.dtb.bak:
#    esos son de Ubuntu y de flash-kernel, no de Atriz.
mkdir -p /root/respaldos-atriz
mv /etc/fstab.bak-* /etc/systemd/journald.conf.bak-* \
   /etc/apt/sources.list.d/*.bak-* /root/respaldos-atriz/ 2>/dev/null || true

if [[ "${PROBLEMAS_LIMPIEZA:-0}" -eq 1 ]]; then
    echo >&2
    echo "  ✗ NO se prepara la imagen con el driver corriendo." >&2
    echo "    Párala, comprueba que quedó 'inactive' y no 'failed', y repite." >&2
    exit 1
fi

ok "logs, cachés, historial y artefactos de compilación limpiados"

# ─────────────────────────────────────────────────────────────────────────────
# 🔐 CLAUDE CODE FUERA. Es herramienta de desarrollo del robot de referencia,
#    no del producto — decisión del usuario, 2026-08-03.
#
#    Y no es solo peso muerto. Medido en rvr-01:
#      ~/.claude/.credentials.json  ->  claudeAiOauth.accessToken
#                                       claudeAiOauth.refreshToken
#    Son las credenciales de la suscripción de Claude del usuario. El modo 600
#    no protege NADA frente a un `dd`: una imagen de disco lo copia todo. Sin
#    esto, los 16 clones saldrían con sus tokens dentro.
#
#    Peso: ~/.claude 126 MB (incluido el transcripto de la sesión de trabajo,
#    41,8 MB) + ~/.local/share/claude 260 MB = 386 MB por robot, sin función.
#
# ⚠️ Lo que se pierde y NO se recupera: los ficheros de memory/ y los
#    transcriptos de las sesiones. Lo que valga la pena tiene que estar
#    commiteado ANTES.
if [[ -e "$REAL_HOME/.local/bin/claude" || -d "$REAL_HOME/.claude" ]]; then
    avis "Claude Code está instalado. Es herramienta de desarrollo: se elimina."
    avis "  🔐 ~/.claude/.credentials.json lleva los tokens OAuth de tu suscripción"
    avis "  ⚠️ se perderán los hilos, memory/ y los transcriptos. ¿Está todo commiteado?"
    read -rp "  Escribe 'si' para eliminarlo, cualquier otra cosa para abortar: " CC
    if [[ "$CC" != "si" ]]; then
        echo "  Cancelado. Commitea lo que necesites y vuelve." >&2
        exit 1
    fi
    rm -f  "$REAL_HOME/.local/bin/claude" "$REAL_HOME/.claude.json"
    rm -rf "$REAL_HOME/.local/share/claude" "$REAL_HOME/.claude"
    # Se comprueba el EFECTO, no que el rm devolviera 0.
    RESTOS="$(find "$REAL_HOME" -maxdepth 4 \( -name '.credentials.json' -o -name 'claude' \) \
              -path '*claude*' 2>/dev/null | head -5)"
    if [[ -z "$RESTOS" ]]; then
        ok "Claude Code eliminado (binario, datos y credenciales)"
    else
        avis "quedan restos de Claude Code:"; echo "$RESTOS" | sed 's/^/      /'
    fi
else
    ok "Claude Code no está instalado (correcto para un robot de la flota)"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "5/6 · Comprobar que no queda nada personal ni secreto"

# 🔴 BÚSQUEDA RECURSIVA, no una lista de tres rutas fijas.
#    La versión anterior miraba solo $REAL_HOME/.ssh/id_* y
#    $REAL_HOME/.git-credentials. El 2026-08-03 se encontró una COPIA del token
#    de GitHub en $REAL_HOME/respaldo_pre_migracion/.git-credentials: pasaba el
#    control sin decir nada y habría viajado en los 16 clones.
#    Un respaldo hecho a mano no tiene por qué estar donde el script espera —
#    ese es justo el motivo por el que hay que buscarlo, no listarlo.
# ⚠️ Y por NOMBRE solo para los ficheros que son un secreto por definición. Un
#    '*.pem' se descarta o no según su CONTENIDO: un certificado público no es
#    un secreto, y avisar de él cada vez entrena a la gente a ignorar el aviso
#    —que es como se pierde un control de verdad—.
PROB=0
# 🔐 `.credentials.json` está en la lista porque el 2026-08-03 se comprobó que
#    la búsqueda anterior NO lo veía: es donde Claude Code guarda los tokens
#    OAuth de la suscripción (`claudeAiOauth.accessToken` / `refreshToken`).
#    El paso 4 ya debería haberlo borrado; esto es el cinturón por si alguien
#    reinstala Claude Code después de limpiar.
ENCONTRADOS="$(find "$REAL_HOME" -xdev \
        \( -name '.git-credentials' -o -name 'id_rsa' -o -name 'id_ed25519' \
           -o -name 'id_ecdsa' -o -name '.netrc' -o -name '.credentials.json' \
           -o -name 'credentials.json' -o -name '*.pem' -o -name '*.key' \) \
        -type f 2>/dev/null)"
if [[ -n "$ENCONTRADOS" ]]; then
    while IFS= read -r f; do
        case "$f" in
            *.pem|*.key)
                # Solo cuenta si de verdad lleva una clave privada dentro.
                grep -qs 'PRIVATE KEY' "$f" || continue ;;
        esac
        avis "PRESENTE: $f  <- se clonará en los 16 robots"
        PROB=1
    done <<<"$ENCONTRADOS"
fi
if [[ $PROB -eq 1 ]]; then
    avis "Decide: si la clave/token es compartida a propósito, adelante."
    avis "Si es TU credencial personal, bórrala antes del dd. Para un token,"
    avis "'shred -u' en vez de 'rm': con rm el contenido sigue en la microSD."
else
    ok "sin claves privadas ni tokens en el home (búsqueda recursiva)"
fi
avis "netplan (con la PSK del WiFi) SÍ se clona: es lo deseable si todos usan la misma red"

# ── Lo que la imagen NO tendrá, y conviene saberlo ANTES del dd ───────────────
if ! dpkg -l ros-jazzy-rosbridge-suite 2>/dev/null | grep -q '^ii'; then
    avis "🔴 rosbridge NO está instalado: los clones no podrán hablar con la web"
    avis "   (es la Fase 5; si clonas antes, habrá que instalarlo en los 16)"
fi
if [[ ! -d "$REAL_HOME/atriz_migracion" ]]; then
    avis "🔴 no está ~/atriz_migracion: los clones no tendrán verificar_robot.sh"
fi
# 🔴 Y el mapa, que es lo ÚLTIMO que hay que hacer y lo primero que se olvida.
avis "🔴 LOS CLONES SALEN SIN MAPA, a propósito. Antes de que naveguen, en CADA"
avis "   aula: mapear con atriz-slam, guardar en ~/mapas, y poner su .yaml en"
avis "   ATRIZ_MAPA de /etc/default/atriz. Un mapa de otro sitio NO da error:"
avis "   Nav2 dice «llegué» estando a medio metro (evidencia 84)."
# 🔴 La divergencia que rompe la regla del proyecto («provision.sh es la verdad»)
if [[ -f /etc/systemd/system/atriz-robot.service ]] \
   && ! grep -q 'fase_7_systemd' "$SCRIPTS_DIR/provision.sh" 2>/dev/null; then
    avis "🔴 ESTA IMAGEN TENDRÁ ARRANQUE AUTOMÁTICO Y provision.sh NO LO INSTALA."
    avis "   Un robot reprovisionado desde cero saldrá DISTINTO del clonado, y la"
    avis "   regla del proyecto dice que gana provision.sh. Añádelo antes del dd."
fi

# ─────────────────────────────────────────────────────────────────────────────
say "6/6 · Estado final"
echo "  hostname actual : $(hostname)"
echo "  machine-id      : $(wc -c < /etc/machine-id) bytes (0 = correcto)"
echo "  claves de host  : $(ls /etc/ssh/ssh_host_* 2>/dev/null | wc -l) (0 = correcto)"
echo "  first-boot      : $(systemctl is-enabled atriz-first-boot.service 2>/dev/null)"

cat <<EOF

────────────────────────────────────────────────────────────────────────────
  APAGA AHORA — no vuelvas a arrancar esta tarjeta antes del dd, o el
  first-boot se ejecutará y volverá a generar la identidad:

      sudo poweroff

  Desde un PC, con la tarjeta fuera:

      sudo dd if=/dev/mmcblk0 of=atriz_jazzy_v1.img bs=4M status=progress conv=fsync
      sha256sum atriz_jazzy_v1.img > atriz_jazzy_v1.img.sha256
      # opcional, recomendable — reduce la imagen al tamaño realmente usado:
      #   https://github.com/Drewsif/PiShrink
      sudo pishrink.sh -Z atriz_jazzy_v1.img

  PARA CADA ROBOT (~15 min, casi todo desatendido):

      1. Grabar la imagen en la microSD (Raspberry Pi Imager o dd)
      2. Montar la partición FAT y editar robot_id.txt -> el número del robot
      3. Anotar la MAC y crear la reserva DHCP en el router
      4. Arrancar. El first-boot fija hostname, ROS_DOMAIN_ID y claves,
         y se deshabilita solo
      5. Verificar (ver FLOTA.md, "Alta de un robot nuevo")
      6. Rellenar la tabla de asignación de FLOTA.md

  Y ETIQUETA EL CÓDIGO antes de clonar, para saber qué corre cada robot:

      git tag -a v1.0-jazzy -m "Primera imagen dorada validada"
      git push origin v1.0-jazzy
────────────────────────────────────────────────────────────────────────────
EOF
