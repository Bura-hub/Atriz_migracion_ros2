#!/usr/bin/env bash
#
# provision.sh — de un Ubuntu Server 24.04 recién instalado a un robot Atriz
#
#     sudo bash provision.sh                 # todo
#     sudo bash provision.sh --sin-ros       # solo SO, UART y dependencias
#     sudo bash provision.sh --simular       # dice qué haría, sin tocar nada
#
# POR QUÉ ESTE SCRIPT ES LA PIEZA CENTRAL DE LA FLOTA
#
#   Para 16 robots, la vía rápida es la IMAGEN DORADA: clonar una tarjeta ya
#   terminada evita que cada robot descargue ~1.5 GB (full-upgrade + kernel +
#   ROS 2 + dependencias). Con 15 robots eso son ~22 GB sobre la única AP del
#   laboratorio, que FLOTA.md ya señala como el riesgo principal sin medir.
#
#   Pero una imagen dorada que nadie sabe reconstruir es una CAJA NEGRA, y es
#   exactamente el problema del MANUAL SPHERO.docx original: describía un sistema
#   que nadie podía rehacer. Si la imagen se corrompe, si sale 24.04.5, o si hay
#   que cambiar un parámetro, no quieres estar arqueando a mano otra vez.
#
#   Así que la relación correcta es:
#
#       provision.sh  ──ejecutar una vez──►  robot terminado
#                                                  │
#                                    fase_6_preparar_imagen_dorada.sh
#                                                  │
#                                                  ▼
#                                          IMAGEN DORADA  ──►  robots 2..16
#
#   La imagen es el ATAJO. El script es la VERDAD. Si divergen, gana el script:
#   se reconstruye la imagen.
#
# NO DUPLICA NADA
#
#   Llama a fase_0_1_fix_uart.sh y fase_1_higiene_so.sh, que ya existen, están
#   probados y respaldan lo que modifican. Un script que reimplementa a otros
#   dos acaba divergiendo de ellos; este los orquesta.
#
# IDEMPOTENTE
#
#   Se puede volver a ejecutar sin daño, y se DEBE: es también la forma de
#   actualizar un robot ya en marcha (git pull && sudo bash provision.sh).
#
# ESTADO
#   📝 NO VERIFICADO como conjunto. Escrito el 2026-07-30 encadenando los pasos
#      que SÍ se ejecutaron uno a uno en rvr-01 ese día. Al aprovisionar el
#      primer robot con él de principio a fin, corregirlo aquí y anotarlo.
#
set -uo pipefail

SIN_ROS=0; SIMULAR=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sin-ros) SIN_ROS=1; shift ;;
        --simular) SIMULAR=1; shift ;;
        -h|--help) sed -n '2,45p' "$0" | sed 's/^#\{0,1\}//'; exit 0 ;;
        *) echo "opción desconocida: $1" >&2; exit 64 ;;
    esac
done

[[ $EUID -ne 0 && $SIMULAR -eq 0 ]] && { echo "Ejecuta con sudo: sudo bash $0" >&2; exit 1; }

VERDE=$'\033[92m'; ROJO=$'\033[91m'; AMAR=$'\033[93m'; AZUL=$'\033[94m'; GRIS=$'\033[90m'; FIN=$'\033[0m'
say()  { printf '\n%s▶ %s%s\n' "$AZUL" "$1" "$FIN"; }
ok()   { printf '  %s✓%s %s\n' "$VERDE" "$FIN" "$1"; }
mal()  { printf '  %s✗%s %s\n' "$ROJO" "$FIN" "$1" >&2; }
avi()  { printf '  %s!%s %s\n' "$AMAR" "$FIN" "$1"; }
salta(){ printf '  %s– %s%s\n' "$GRIS" "$1" "$FIN"; }

FALLOS=()
REPO="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
SCRIPTS="$REPO/scripts"
USUARIO="${SUDO_USER:-sphero}"
HOME_USUARIO="$(getent passwd "$USUARIO" | cut -d: -f6)"

correr() {
    if [[ $SIMULAR -eq 1 ]]; then printf '  %s[simular]%s %s\n' "$GRIS" "$FIN" "$*"; return 0; fi
    "$@"
}

printf '%s' "$AZUL"
cat <<'EOF'
======================================================================
  provision.sh — de Ubuntu Server 24.04 a robot Atriz
======================================================================
EOF
printf '%s' "$FIN"
echo "  repo: $REPO"
echo "  usuario: $USUARIO ($HOME_USUARIO)"
[[ $SIMULAR -eq 1 ]] && avi "MODO SIMULACIÓN: no se toca nada"
[[ $SIN_ROS -eq 1 ]] && avi "--sin-ros: se salta la instalación de ROS 2"

# ─────────────────────────────────────────────────────────────────────────────
say "0/9 · Comprobar que el punto de partida es el esperado"

# Aprovisionar sobre un SO que no es el previsto produce fallos incomprensibles
# tres pasos más adelante. Se comprueba antes de tocar nada.
V="$(lsb_release -rs 2>/dev/null || echo '?')"
[[ "$V" == 24.04 ]] && ok "Ubuntu $V" \
    || { mal "Ubuntu $V, se esperaba 24.04. Aborto: este script está escrito para 24.04."; exit 1; }
A="$(uname -m)"
[[ "$A" == aarch64 ]] && ok "arquitectura $A" || { mal "arquitectura $A, se esperaba aarch64. Aborto."; exit 1; }
ok "Python $(python3 --version | awk '{print $2}')"

for s in fase_0_1_fix_uart.sh fase_1_higiene_so.sh; do
    [[ -f "$SCRIPTS/$s" ]] || { mal "no encuentro $SCRIPTS/$s. ¿Está el repo completo?"; exit 1; }
done
ok "los scripts de fase están presentes"

if ! ping -c1 -W3 archive.ubuntu.com >/dev/null 2>&1 && ! ping -c1 -W3 ports.ubuntu.com >/dev/null 2>&1; then
    avi "no hay salida a Internet: los pasos de apt y pip fallarán"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "1/9 · Terminar las actualizaciones pendientes"

# La imagen trae unattended-upgrades ACTIVO y, en cuanto hay red, instala por su
# cuenta — incluido un kernel nuevo. Si no se cierra esto ANTES de tocar el
# device-tree, un mismo reinicio aplica dos cambios y un fallo posterior no se
# puede atribuir. Verificado el 2026-07-30: metió 8 lotes en 4 minutos.
espera_lock() {
    for i in $(seq 1 60); do
        fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || return 0
        [[ $i -eq 1 ]] && avi "esperando a que unattended-upgrades suelte el lock de dpkg…"
        sleep 5
    done
    avi "el lock de dpkg sigue ocupado tras 5 min. ¿Quién lo tiene?"
    fuser -v /var/lib/dpkg/lock-frontend 2>&1 | sed 's/^/       /'
    return 1
}
# La imagen de Ubuntu Server 24.04 para Raspberry Pi viene SIN 'noble-updates':
# solo trae 'noble' y 'noble-security'. Verificado el 2026-07-30 en rvr-01.
#
# Eso rompe la instalacion de ROS 2 mas adelante, y de forma nada obvia: las
# bibliotecas de runtime SI se actualizan desde noble-security (a versiones con
# sufijo .1), pero sus paquetes -dev, que exigen una version exacta de la
# runtime, viven en noble-updates. Sin ese repo, 'apt install ros-dev-tools'
# falla con 'held broken packages' en zlib1g-dev, libzstd-dev, liblz4-dev y
# dpkg-dev. Y sin los -dev no hay colcon build.
SRC=/etc/apt/sources.list.d/ubuntu.sources
if [[ -f "$SRC" ]]; then
    if grep -qE '^Suites:.*noble-updates' "$SRC"; then
        salta "noble-updates ya está habilitado"
    else
        # El respaldo va FUERA de sources.list.d/: apt avisa en CADA ejecucion
        # de los ficheros con extension que no reconoce, y en 16 robots eso es
        # ruido permanente. Verificado el 2026-07-30:
        #   N: Ignoring file 'ubuntu.sources.bak-...' ... invalid filename extension
        correr install -d /root/respaldos-apt
        correr cp -a "$SRC" "/root/respaldos-apt/$(basename "$SRC").bak-$(date +%Y%m%d-%H%M%S)"
        # 0,/patron/s//…/ sustituye SOLO la primera aparicion: la del repo
        # principal. No debe tocar la linea de noble-security.
        correr sed -i '0,/^Suites: noble$/s//Suites: noble noble-updates/' "$SRC"
        if [[ $SIMULAR -eq 0 ]]; then
            grep -qE '^Suites: noble noble-updates$' "$SRC" \
                && ok "noble-updates añadido (sin tocar noble-security)" \
                || { mal "no se pudo añadir noble-updates a $SRC — añádelo a mano"
                     FALLOS+=("noble-updates"); }
        fi
    fi
fi

espera_lock || true
export DEBIAN_FRONTEND=noninteractive
correr apt-get update -qq && ok "apt-get update" || { mal "apt-get update falló"; FALLOS+=("apt update"); }
correr apt-get full-upgrade -y -qq && ok "full-upgrade" || { mal "full-upgrade falló"; FALLOS+=("full-upgrade"); }

if [[ -f /var/run/reboot-required ]]; then
    avi "hay un reinicio pendiente: $(tr '\n' ' ' < /var/run/reboot-required.pkgs 2>/dev/null)"
    avi "no es un problema — el paso 9/9 te dirá cuándo reiniciar"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "2/9 · Paquetes del sistema"

# iw               apagar el power-save del WiFi. NO viene en Server 24.04.
# python3-aiohttp  sphero_sdk/__init__.py lo importa SIN CONDICIONES (a través de
#                  rvr_fw_check_async -> cms_fw_check_base.py:2). Sin él el SDK no
#                  importa, aunque solo se USE para consultar el firmware por web.
# python3-serial   pyserial, el enlace serie.
# python3-pip      necesario solo para pyserial-asyncio, que no está en apt.
# python3-cryptography  verifica el testigo Ed25519 (atriz_rosbridge y el agente
#                       del Taller). Hoy viene de la imagen base de Ubuntu, pero
#                       marcado `automatic`: sin esta línea, funcionaba por
#                       herencia y no por cadena. Evidencia 125, 3d.
PAQUETES=(iw python3-serial python3-aiohttp python3-pip python3-cryptography git patch)   # `patch`: aplica el parche del ydlidar
FALTANTES=()
for p in "${PAQUETES[@]}"; do
    dpkg -l "$p" 2>/dev/null | grep -q '^ii' && salta "$p ya instalado" || FALTANTES+=("$p")
done
if [[ ${#FALTANTES[@]} -gt 0 ]]; then
    espera_lock || true
    correr apt-get install -y -qq "${FALTANTES[@]}" \
        && ok "instalados: ${FALTANTES[*]}" \
        || { mal "fallo instalando: ${FALTANTES[*]}"; FALLOS+=("apt install"); }
fi

# pyserial-asyncio NO existe como paquete apt (comprobado el 2026-07-30:
# `apt-cache policy python3-pyserial-asyncio` no devuelve nada). Se instala a
# nivel de SISTEMA, no del usuario: el driver correrá como servicio systemd y
# ~/.local del usuario puede no estar en su sys.path.
if python3 -c 'import serial_asyncio' 2>/dev/null; then
    salta "pyserial-asyncio ya instalado"
else
    correr pip3 install --break-system-packages -q pyserial-asyncio \
        && ok "pyserial-asyncio instalado (PEP 668 obliga a --break-system-packages)" \
        || { mal "fallo instalando pyserial-asyncio"; FALLOS+=("pyserial-asyncio"); }
fi

# ─────────────────────────────────────────────────────────────────────────────
say "3/9 · UART del RVR  (delega en fase_0_1_fix_uart.sh)"

if [[ $SIMULAR -eq 1 ]]; then
    printf '  %s[simular]%s bash %s\n' "$GRIS" "$FIN" "$SCRIPTS/fase_0_1_fix_uart.sh"
elif bash "$SCRIPTS/fase_0_1_fix_uart.sh"; then
    ok "fase_0_1_fix_uart.sh completado"
else
    mal "fase_0_1_fix_uart.sh falló"; FALLOS+=("UART")
fi

# 🔴 LOS GRUPOS DEL USUARIO — hueco encontrado en rvr-02 el 2026-08-11
#
#    NINGÚN guion del proyecto metía al usuario en `dialout` ni en `video`. En
#    rvr-01 los tiene, pero de su montaje MANUAL original, no de un script. Y la
#    imagen dorada clona /etc/group, así que los robots 3..16 los heredarían y
#    esto NUNCA se habría visto: es exactamente el peligro de «la imagen es el
#    atajo, el script es la verdad».
#
#    Por qué no saltó antes: `atriz-robot.service` lleva `SupplementaryGroups=
#    dialout`, así que EL SERVICIO habla con el RVR aunque el usuario no esté en
#    el grupo. Lo que se rompe es todo lo INTERACTIVO — el verificador y, sobre
#    todo, `scripts/estudiantes/atriz.py`, que es lo que ejecuta el alumno.
#
#    En rvr-02 recién aprovisionado eso dio TRES fallos del verificador que en
#    realidad eran uno:
#        ✗ /dev/rvr sin permisos para sphero        → falta dialout
#        ✗ el RVR NO contesta                       → consecuencia del anterior
#        ✗ throttling: «Can't open /dev/vcio»       → falta video (vcgencmd)
#
#    dialout: /dev/rvr (ttyAMA0) y /dev/ttyUSB0 del LIDAR. video: /dev/vcio, que
#    es como vcgencmd lee si ha habido bajadas de tensión.
#    ⚠️ No surte efecto hasta cerrar y abrir sesión; el guion acaba pidiendo un
#       reinicio, así que queda cubierto.
for _g in dialout video; do
    if id -nG "$USUARIO" | tr ' ' '\n' | grep -qx "$_g"; then
        salta "$USUARIO ya está en el grupo $_g"
    elif correr usermod -aG "$_g" "$USUARIO"; then
        ok "$USUARIO añadido al grupo $_g (efectivo tras reiniciar)"
    else
        mal "no se pudo añadir $USUARIO al grupo $_g"; FALLOS+=("grupo $_g")
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
say "4/9 · Higiene del SO  (delega en fase_1_higiene_so.sh)"

if [[ $SIMULAR -eq 1 ]]; then
    printf '  %s[simular]%s bash %s\n' "$GRIS" "$FIN" "$SCRIPTS/fase_1_higiene_so.sh"
elif bash "$SCRIPTS/fase_1_higiene_so.sh"; then
    ok "fase_1_higiene_so.sh completado"
else
    # Sale con 1 si algún paso no se aplicó. Es información, no un desastre:
    # el propio script lista qué quedó pendiente.
    mal "fase_1_higiene_so.sh reportó pasos NO APLICADOS (ver su salida arriba)"
    FALLOS+=("higiene del SO")
fi

# ─────────────────────────────────────────────────────────────────────────────
say "5/9 · Código del robot en ~/atriz_ws"

WS="$HOME_USUARIO/atriz_ws/src"

# 🔴 EL FALLO QUE PARÓ A rvr-02 DOS VECES (2026-08-10 y 2026-08-11)
#
#    Aquí ponía  `install -d -o "$USUARIO" -g "$USUARIO" "$WS"`  y parecía
#    correcto: nombra el usuario, crea el árbol entero. Pero `install -d` NO
#    aplica -o/-g a los padres que crea de paso. El manual de coreutils de la
#    propia máquina lo dice sin ambigüedad:
#
#      «Parent directories are created with mode u=rwx,go=rx (755), regardless
#       of the -m option» … «giving them the DEFAULT attributes»
#
#    O sea que `.../atriz_ws/src` dejaba `src` del usuario y **`atriz_ws` de
#    root**, porque este guion corre con sudo. Después, `colcon build` va como
#    el usuario (línea ~520) y no puede crear `build/`, `install/` ni `log/`
#    dentro de un directorio 755 ajeno:
#
#        sphero@rvr-02:~/atriz_ws$ colcon build
#            Permission denied: 'log'
#
#    y el fallo se propaga: `fase_7_systemd.sh` se niega porque el workspace no
#    está compilado, así que el robot se queda sin arranque automático. Un solo
#    directorio con el dueño equivocado tumba los dos últimos pasos de los nueve.
#
#    Medido en rvr-02: atriz_ws root:root 755 · atriz_ws/src sphero:sphero.
#
# ARREGLO 1 · Se nombran los DOS directorios, que sí reciben los atributos
#             pedidos. Nombrar el padre no es redundante: es la única forma.
# ARREGLO 2 · Y se repara lo ya creado, porque la primera víctima de este fallo
#             es un robot que ya existe y al que hay que volver a lanzarle el
#             guion. Sin esto, ser «idempotente» no serviría de nada aquí.
if [[ -d "$HOME_USUARIO/atriz_ws" ]]; then
    _duenyo="$(stat -c %U "$HOME_USUARIO/atriz_ws" 2>/dev/null)"
    if [[ "$_duenyo" != "$USUARIO" ]]; then
        avi "~/atriz_ws es de '$_duenyo', no de '$USUARIO': colcon build no podría escribir ahí"
        if correr chown -R "$USUARIO:$USUARIO" "$HOME_USUARIO/atriz_ws"; then
            ok "~/atriz_ws devuelto a $USUARIO (era el fallo de rvr-02, 2026-08-10)"
        else
            mal "no se pudo corregir el dueño de ~/atriz_ws"; FALLOS+=("dueño de ~/atriz_ws")
        fi
    fi
fi

if [[ -d "$WS/Atriz_rvr/.git" ]]; then
    salta "Atriz_rvr ya está en $WS"
    # Regla nº1 del proyecto: fetch ANTES de mirar el código. El 2026-07-29 se
    # auditó un clon 5 commits por detrás y tres hallazgos salieron falsos.
    correr sudo -u "$USUARIO" git -C "$WS/Atriz_rvr" fetch origin \
        && ok "fetch hecho" || avi "no se pudo hacer fetch (¿sin red? ¿sin credenciales?)"
    R="$(sudo -u "$USUARIO" git -C "$WS/Atriz_rvr" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    ok "rama actual: $R"
else
    # Los DOS, no solo el hijo. Ver el bloque de arriba: install -d da a los
    # padres los atributos por defecto (root:root con sudo), no los pedidos.
    correr install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USUARIO/atriz_ws" "$WS"
    if correr sudo -u "$USUARIO" git clone -q -b ros2 \
            https://github.com/Bura-hub/Atriz_rvr.git "$WS/Atriz_rvr"; then
        ok "Atriz_rvr clonado en $WS (rama ros2)"
    else
        mal "fallo al clonar Atriz_rvr"; FALLOS+=("clonar Atriz_rvr")
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
say "6/9 · ROS 2 Jazzy"

if [[ $SIN_ROS -eq 1 ]]; then
    salta "saltado por --sin-ros"
elif [[ -d /opt/ros/jazzy ]]; then
    salta "ROS 2 Jazzy ya está en /opt/ros/jazzy"
else
    # Se usa el paquete ros2-apt-source, no el curl del keyring a mano. Es el
    # metodo oficial actual, y para una flota es el unico sensato: mantiene la
    # clave GPG actualizada solo. Con la clave puesta a mano, el dia que caduque
    # —y ya paso una vez, rompiendo apt en todas las instalaciones de ROS— se
    # rompen los 16 robots a la vez.
    #
    # Auditado el 2026-07-30 (v1.2.0): sin scripts de mantenedor, solo coloca el
    # keyring, el .sources y un symlink. Clave de Open Robotics, huella
    # C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654, caduca 2030-06-01 (despues del
    # fin de soporte de Jazzy, mayo 2029).
    grep -qm1 universe /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null \
        && ok "el componente 'universe' está habilitado" \
        || correr add-apt-repository -y universe

    # Ruta única, no fija: con `fs.protected_regular=2` un fichero de /tmp
    # dejado por otro usuario impide a root sobrescribirlo. Ver first-boot.sh.
    DEB=$(mktemp --suffix=.deb)
    V="$(curl -s --max-time 30 https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
         | grep -F '"tag_name"' | awk -F'"' '{print $4}')"
    CN="$(. /etc/os-release && echo "$VERSION_CODENAME")"
    if [[ -z "$V" ]]; then
        mal "no se pudo consultar la última versión de ros-apt-source (¿sin red?)"
        avi "alternativa manual en el manual, cap. 5.2. NO uses apt-key add: está obsoleto."
        FALLOS+=("ROS 2: repo")
    else
        ok "ros-apt-source $V para $CN"
        if correr curl -fsSL --max-time 120 -o "$DEB" \
              "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${V}/ros2-apt-source_${V}.${CN}_all.deb"; then
            # Comprobar que no trae scripts que se ejecuten como root antes de instalarlo.
            if [[ $SIMULAR -eq 0 ]]; then
                SCR="$(dpkg-deb --ctrl-tarfile "$DEB" | tar -t 2>/dev/null | grep -E '/(pre|post)(inst|rm)$' || true)"
                [[ -z "$SCR" ]] && ok "el .deb no trae scripts de mantenedor" \
                                || avi "el .deb trae scripts: $SCR — revísalos antes de seguir"
            fi
            espera_lock || true
            correr apt-get install -y -qq "$DEB" && ok "repositorio de ROS 2 configurado" \
                || { mal "fallo instalando ros2-apt-source"; FALLOS+=("ROS 2: repo"); }
            correr apt-get update -qq && ok "apt-get update con el repo de ROS" \
                || { mal "apt-get update falló"; FALLOS+=("ROS 2: update"); }

            # ros-base, NO desktop: son 236 paquetes con Gazebo y RViz en un robot
            # sin pantalla. RViz2 se ejecuta desde un portatil.
            espera_lock || true
            correr apt-get install -y -qq ros-jazzy-ros-base ros-dev-tools \
                && ok "ros-jazzy-ros-base + ros-dev-tools instalados" \
                || { mal "fallo instalando ROS 2"; FALLOS+=("ROS 2: paquetes"); }
        else
            mal "fallo descargando ros2-apt-source"; FALLOS+=("ROS 2: descarga")
        fi
    fi

    # Identidad de git, GLOBAL. El 2026-07-30 se configuro con 'git config' sin
    # --global en atriz_migracion, y el primer commit en Atriz_rvr fallo con
    # "Author identity unknown". Peor: el 'git push' de la rama SI funciono
    # (subiendola sin el commit), asi que el fallo era facil de pasar por alto.
    if [[ $SIMULAR -eq 0 ]] && ! sudo -u "$USUARIO" git config --global user.email >/dev/null 2>&1; then
        avi "el usuario $USUARIO no tiene identidad de git configurada."
        avi "Sin ella, 'git commit' falla en CUALQUIER repositorio. Ejecuta:"
        avi "    git config --global user.name  \"Tu Nombre\""
        avi "    git config --global user.email \"tu@correo\""
    elif [[ $SIMULAR -eq 0 ]]; then
        ok "identidad de git: $(sudo -u "$USUARIO" git config --global user.email)"
    fi

    # rosdep, que hace falta para resolver dependencias del workspace.
    if [[ $SIMULAR -eq 0 ]] && command -v rosdep >/dev/null; then
        rosdep init >/dev/null 2>&1 || salta "rosdep ya estaba inicializado"
        sudo -u "$USUARIO" rosdep update >/dev/null 2>&1 \
            && ok "rosdep actualizado (como $USUARIO, no como root)" \
            || avi "rosdep update falló; ejecútalo a mano como $USUARIO"
    fi

    avi "📝 El entorno del usuario (ROS_DOMAIN_ID, source del setup.bash) lo fija"
    avi "   atriz-first-boot en /etc/profile.d/atriz-robot.sh, a partir de"
    avi "   /boot/firmware/robot_id.txt. Ver manual cap. 5.3 y FLOTA.md."
fi

# ─────────────────────────────────────────────────────────────────────────────
say "7/9 · El robot completo: xacro, LIDAR, SLAM, Nav2 y compilar"

# Esta es la Etapa F de INSTALACION.md. Sin ella el robot tiene ROS 2 y el codigo
# clonado, pero no arranca: falta xacro para el URDF, el driver del LIDAR (que NO
# tiene paquete apt), slam_toolbox y navigation2.

if [[ $SIN_ROS -eq 1 ]]; then
    salta "saltado por --sin-ros"
elif [[ ! -d /opt/ros/jazzy ]]; then
    salta "sin ROS 2 instalado, no hay nada que compilar"
else
    # xacro NO viene en ros-base y hace falta para el URDF. slam_toolbox tampoco.
    #
    # 🔴 Y `ros-jazzy-navigation2`, NO `ros-jazzy-nav2-bringup`. La diferencia son
    #    312 paquetes: `bringup` arrastra `nav2-minimal-tb3-sim`, `tb4-sim`,
    #    `ros-gz-sim` y hasta `pocketsphinx-en-us` — dos TurtleBots simulados y
    #    reconocimiento de voz, en un robot real sin microfono. Y todo eso
    #    acabaria replicado en los 16 por la imagen dorada. Manual, cap. 11.1.
    #
    #    De `navigation2` sale ademas todo lo que el robot usa fuera de navegar:
    #    `collision_monitor` (la capa de seguridad, cap. 12), `map_server` y
    #    `amcl` (la localizacion de la Fase 4c, cap. 14), y `map_saver_cli`, que
    #    es la unica forma fiable de guardar mapas (cap. 11.11).
    espera_lock || true
    # 🔴 Y `rosbridge-suite`: es POR DONDE HABLA LA WEB (ARQUITECTURA.md, D2).
    #    Sin él los robots no son utilizables desde la plataforma, y añadirlo
    #    después significa ~300 MB por robot sobre la única AP del laboratorio —
    #    justo lo que la imagen dorada existe para evitar.
    correr apt-get install -y -qq ros-jazzy-xacro ros-jazzy-slam-toolbox \
        ros-jazzy-navigation2 ros-jazzy-rosbridge-suite \
        && ok "xacro + slam-toolbox + navigation2 + rosbridge instalados" \
        || { mal "fallo instalando xacro/slam_toolbox/navigation2"
             FALLOS+=("xacro/slam_toolbox/navigation2"); }

    # Comprobar el EFECTO, no que apt dijera que si: sin estos cuatro binarios el
    # robot arranca y falla al primer objetivo.
    for BIN in collision_monitor map_server amcl controller_server \
               rosbridge_websocket; do
        if [[ -x "/opt/ros/jazzy/lib/nav2_${BIN%%_*}"*"/$BIN" ]] \
           || compgen -G "/opt/ros/jazzy/lib/*/$BIN" >/dev/null; then
            ok "nav2: $BIN presente"
        else
            mal "nav2: FALTA $BIN"; FALLOS+=("nav2/$BIN")
        fi
    done

    # 🔴 El driver del YDLIDAR NO tiene paquete apt. Comprobado el 2026-07-30:
    # `apt-cache search ydlidar` da 0 resultados. Se compila desde fuentes.
    if [[ -f /usr/local/lib/libydlidar_sdk.a ]]; then
        salta "YDLidar-SDK ya está en /usr/local"
    else
        # 🔴 COMMIT FIJO, no la punta de la rama.
        #    Sin esto, dos robots aprovisionados con un mes de diferencia traen
        #    versiones distintas del SDK, y el segundo no es una copia del
        #    primero por mucho que el script sea el mismo — que es justo lo que
        #    la imagen dorada viene a garantizar.
        #    Este es el commit que corre en rvr-01, medido el 2026-08-03 sobre
        #    el clon del que salió /usr/local/lib/libydlidar_sdk.a.
        SDK_COMMIT=01cdda4f2b36dff2a706d0535c64228d863c7411   # 2026-07-01
        SDKDIR="$HOME_USUARIO/YDLidar-SDK"
        [[ -d "$SDKDIR/.git" ]] || correr sudo -u "$USUARIO" git clone -q \
            https://github.com/YDLIDAR/YDLidar-SDK.git "$SDKDIR"
        if ! correr sudo -u "$USUARIO" git -C "$SDKDIR" checkout -q "$SDK_COMMIT"; then
            avi "no pude fijar el SDK en $SDK_COMMIT: se compila la punta de la rama"
            avi "este robot podría no ser idéntico a rvr-01"
        fi
        correr sudo -u "$USUARIO" mkdir -p "$SDKDIR/build"
        if correr sudo -u "$USUARIO" bash -c "cd '$SDKDIR/build' && cmake .. >/dev/null && make -j2 >/dev/null" \
           && correr bash -c "cd '$SDKDIR/build' && make install >/dev/null"; then
            ok "YDLidar-SDK compilado e instalado en /usr/local"
        else
            mal "fallo compilando YDLidar-SDK"; FALLOS+=("YDLidar-SDK")
        fi
    fi

    # El driver ROS 2: rama `humble`, compila en Jazzy sin cambios. Se le quita
    # el .git porque es codigo de terceros y no se mezcla con Atriz_rvr.
    # 🔴 COMMIT FIJO, igual que el SDK. `-b humble` es una RAMA: apunta a donde
    #    esté la punta el día que se ejecute. Y aquí muerde el doble, porque
    #    justo debajo se aplica un parche con `patch -p1`: si upstream mueve
    #    esas líneas, el parche falla — o peor, aplica con `fuzz` en el sitio
    #    equivocado. Medido en rvr-01 el 2026-08-03.
    DRV_COMMIT=4ef70d3f32a85704ade0be54b214f3763b1ab3e8   # rama humble, 2025-06-20
    if [[ -d "$WS/ydlidar_ros2_driver" ]]; then
        salta "ydlidar_ros2_driver ya está en $WS"
    elif correr sudo -u "$USUARIO" git clone -q -b humble \
            https://github.com/YDLIDAR/ydlidar_ros2_driver.git "$WS/ydlidar_ros2_driver"; then
        # El checkout va ANTES de borrar el .git, que es lo único que lo permite.
        correr sudo -u "$USUARIO" git -C "$WS/ydlidar_ros2_driver" checkout -q "$DRV_COMMIT" \
            || avi "no pude fijar el driver en $DRV_COMMIT: el parche de abajo podría no aplicar"
        correr rm -rf "$WS/ydlidar_ros2_driver/.git"
        ok "ydlidar_ros2_driver clonado (rama humble, commit ${DRV_COMMIT:0:7}, sin .git)"
    else
        mal "fallo al clonar ydlidar_ros2_driver"; FALLOS+=("ydlidar_ros2_driver")
    fi

    # 🔴 PARCHE OBLIGATORIO AL DRIVER DEL YDLIDAR.
    # Sin él, con el barrido apagado —que es el ESTADO NORMAL en reposo de los
    # 16 robots— el nodo emite `Failed to get scan` **25 veces por segundo**:
    # medido en rvr-01 el 2026-08-01, el 99 % del journal del servicio y 2.17
    # millones de mensajes al día por robot. Ahoga los errores de verdad y
    # desgasta la microSD, que es el único almacenamiento del robot.
    #
    # Va aquí y no a mano porque arriba se borra el `.git`: un cambio manual se
    # perdería al reflashear y este script no lo reproduciría. La regla del
    # proyecto es que ante una divergencia **gana el script**.
    PARCHE="$WS/Atriz_rvr/atriz_rvr_bringup/patches/ydlidar-no-inundar-journal.patch"
    YSRC="$WS/ydlidar_ros2_driver/src/ydlidar_ros2_driver_node.cpp"
    if [[ ! -f "$YSRC" ]]; then
        avi "no está el fuente del ydlidar: no se puede parchear"
    elif grep -q "PARCHE ATRIZ" "$YSRC" 2>/dev/null; then
        salta "el parche del ydlidar ya está aplicado"
    elif [[ ! -f "$PARCHE" ]]; then
        avi "falta $PARCHE — este robot inundará el journal"
    elif correr sudo -u "$USUARIO" patch -s -p1 -d "$WS/ydlidar_ros2_driver" -i "$PARCHE"; then
        ok "parche del ydlidar aplicado (no inunda el journal con el barrido apagado)"
    else
        # Si el upstream lo arregla algún día, el parche fallará aquí. Es lo que
        # queremos: enterarnos, no seguir en silencio.
        mal "el parche del ydlidar NO se aplicó"; FALLOS+=("parche ydlidar")
    fi

    # Regla udev por ID_PATH: el CP2102 del X2 reporta ID_SERIAL_SHORT=0001, que
    # es generico y NO distingue un adaptador de otro. Sin /dev/ydlidar el driver
    # no encuentra el LIDAR de forma determinista.
    UDEV_SRC="$WS/Atriz_rvr/atriz_rvr_bringup/udev/99-ydlidar.rules"
    if [[ -f "$UDEV_SRC" ]]; then
        correr install -m 644 "$UDEV_SRC" /etc/udev/rules.d/99-ydlidar.rules
        correr udevadm control --reload-rules
        correr udevadm trigger
        ok "regla udev de /dev/ydlidar instalada"

        # ── PUERTA: ¿casa la regla EN ESTE ROBOT? ────────────────────────────
        # 🔴 La regla lleva dentro el ID_PATH completo, y su prefijo
        #    —`platform-fd500000.pcie-pci-0000:01:00.0`— es DE LA PLACA. Con una
        #    Pi de otra revisión no casa EN ABSOLUTO, y el sufijo `usb-0:1.2` no
        #    casa si el lidar va en otro conector. En los dos casos el síntoma es
        #    el mismo y es venenoso: `robot.launch.py` muere en ~1 s y el único
        #    error visible apunta al launch. Medido el 2026-08-04, evidencia 69.
        #
        #    Con la decisión de PUERTO FIJO en los 16 (FLOTA.md), esto deja de
        #    ser una nota y tiene que ser una puerta: se comprueba aquí, en la
        #    máquina que se está aprovisionando, ANTES de darla por buena. Misma
        #    forma que la puerta de fase_6.
        #
        #    Se comprueba el EFECTO (¿existe el enlace?), no que el fichero se
        #    haya copiado: copiar una regla que no casa devuelve 0 igual.
        sleep 1                                   # udevadm trigger es asíncrono
        _idp_esperado=$(grep -ho 'ID_PATH}=="[^"]*"' /etc/udev/rules.d/99-ydlidar.rules 2>/dev/null \
                        | head -1 | sed 's/.*=="//;s/"//')
        _idp_real=''
        for _d in /dev/ttyUSB*; do
            [[ -e "$_d" ]] || continue
            [[ $(udevadm info -q property -n "$_d" 2>/dev/null | sed -n 's/^ID_VENDOR_ID=//p') == 10c4 ]] \
                && _idp_real=$(udevadm info -q property -n "$_d" 2>/dev/null | sed -n 's/^ID_PATH=//p')
        done
        if [[ -L /dev/ydlidar ]]; then
            ok "/dev/ydlidar existe: la regla CASA en este robot"
        elif [[ -z "$_idp_real" ]]; then
            avi "no se ve ningún CP2102 (10c4): enchufa el LIDAR y repite este paso"
        else
            mal "la regla udev NO CASA en este robot: /dev/ydlidar no existe"
            avi "   real:     $_idp_real"
            avi "   la regla: ${_idp_esperado:-<sin ID_PATH>}"
            if [[ "${_idp_real%%-usb-*}" != "${_idp_esperado%%-usb-*}" ]]; then
                avi "   el prefijo DE LA PLACA difiere: este Pi no es el de referencia."
                avi "   La regla NO es clonable: hay que generarla en first-boot.sh (FLOTA.md, restricción 1)."
            else
                avi "   la placa coincide y el CONECTOR no: mueve el LIDAR al puerto de FLOTA.md."
            fi
            FALLOS+=("regla udev del LIDAR: no casa en este robot")
        fi
        unset _idp_esperado _idp_real _d
    else
        avi "no se encontró $UDEV_SRC — /dev/ydlidar no existirá"
        FALLOS+=("regla udev del LIDAR: no se encontró el fichero")
    fi

    # Y compilar. Que `colcon build` no falle es la prueba de que lo anterior
    # esta en su sitio.
    # 🔴 Aquí ponía `>/dev/null 2>&1`, y el 2026-08-11 eso costó una tarde: en la
    #    primera ejecución completa del guion en la historia del proyecto, el
    #    ÚNICO paso que falló fue justo éste, y había tirado su propia evidencia.
    #    El registro de 9.075 líneas decía «✗ colcon build falló» y nada más: la
    #    causa hubo que sacarla mirando el dueño de un directorio a mano.
    #    Ahora se guarda. Silencioso en pantalla —son cientos de líneas por 16
    #    robots— pero recuperable, que no es lo mismo que inexistente.
    LOG_COLCON="$HOME_USUARIO/atriz_ws/colcon-build.log"
    if correr sudo -u "$USUARIO" bash -c \
        "source /opt/ros/jazzy/setup.bash && cd '$HOME_USUARIO/atriz_ws' && colcon build --symlink-install >'$LOG_COLCON' 2>&1"; then
        ok "workspace compilado (colcon build)"
    else
        mal "colcon build falló"; FALLOS+=("colcon build")
        avi "el porqué está en $LOG_COLCON"
        # Las últimas líneas a pantalla: si el robot está delante, ahorra el viaje.
        [[ -s "$LOG_COLCON" ]] && tail -15 "$LOG_COLCON" | sed 's/^/      /'
        avi "y a mano: cd ~/atriz_ws && colcon build --symlink-install"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
say "8/9 · Arranque automático  (delega en fase_7_systemd.sh)"

# 🔴 POR QUÉ ESTO ESTÁ AQUÍ, Y POR QUÉ NO ESTABA ANTES
#
#   Hasta el 2026-08-01 este paso NO existía, a propósito: mientras se probaba el
#   robot de referencia a mano, un servicio levantado peleaba por /dev/rvr con
#   cada prueba.
#
#   Se añade ahora porque esa razón ya no aplica y quedaba una DIVERGENCIA que
#   rompe la regla del proyecto: la imagen dorada SÍ lleva el arranque automático
#   —un `dd` copia /usr/local/bin y /etc/systemd— y este script no lo instalaba.
#   Un robot reprovisionado salía DISTINTO de uno clonado, y la regla dice que
#   «la imagen es el atajo, provision.sh es la verdad». Evidencia 38.
#
# 📝 `fase_7_systemd.sh` HABILITA el servicio pero NO lo arranca: entra en el
#    próximo reinicio. Así este script no deja un robot moviéndose por sorpresa.
#
# ⚠️ El robot arrancará con el barrido del LIDAR APAGADO y por tanto NO CONDUCIRÁ
#    hasta un `atriz-escaneo on`. No está roto: sin /scan el collision_monitor
#    bloquea el movimiento. Manual, cap. 17.2.

# La identidad: si ya existe /etc/profile.d/atriz-robot.sh, fase_7 la respeta.
# Si no, se le pasa el número desde robot_id.txt — que es de donde sale en un
# clon. Si tampoco está, fase_7 se niega y lo dice, que es lo correcto: un robot
# sin ROS_DOMAIN_ID propio acaba en el dominio 0 con los otros 15.
ARG_ID=()
if [[ ! -f /etc/profile.d/atriz-robot.sh && -f /boot/firmware/robot_id.txt ]]; then
    # 🔴 ANCLADO, igual que en first-boot.sh:56 y fase_7_systemd.sh. El parser
    #    de antes (`tr -dc '0-9' | head -c2`) leía los dos primeros dígitos del
    #    FICHERO, comentarios incluidos: con la plantilla de fase_6 devolvía 01
    #    para cualquier robot. Ver 00_auditoria/evidencia/64_parser_robot_id.txt
    ID_TXT="$(grep -oP '^\s*ROBOT_ID\s*=\s*\K[0-9]+' /boot/firmware/robot_id.txt | head -1)"
    [[ -n "$ID_TXT" ]] && ARG_ID=(--id "$((10#$ID_TXT))")
fi

if [[ $SIMULAR -eq 1 ]]; then
    printf '  %s[simular]%s bash %s %s\n' "$GRIS" "$FIN" \
           "$SCRIPTS/fase_7_systemd.sh" "${ARG_ID[*]}"
elif bash "$SCRIPTS/fase_7_systemd.sh" "${ARG_ID[@]}"; then
    ok "fase_7_systemd.sh completado: el robot arrancará solo"
else
    # No es fatal para el resto del aprovisionamiento: el robot funciona, solo
    # que hay que levantarlo a mano. Pero SÍ se cuenta como fallo, porque un
    # laboratorio remoto sin arranque automático no sirve.
    mal "fase_7_systemd.sh falló (¿falta /boot/firmware/robot_id.txt?)"
    FALLOS+=("arranque automático")
fi

# ─────────────────────────────────────────────────────────────────────────────
say "9/9 · Resumen"

if [[ $SIMULAR -eq 1 ]]; then
    avi "simulación terminada: no se ha modificado nada"
    exit 0
fi

if [[ ${#FALLOS[@]} -gt 0 ]]; then
    printf '\n%sPASOS CON PROBLEMAS%s: %s\n' "$ROJO" "$FIN" "${FALLOS[*]}"
    printf '  Míralos antes de seguir. Este script es idempotente: arregla la causa\n'
    printf '  y vuelve a ejecutarlo.\n'
fi

cat <<EOF

────────────────────────────────────────────────────────────────────────────
  SIGUIENTE PASO:  reinicia y pasa el verificador.

      sudo reboot

      bash $SCRIPTS/verificar_robot.sh --hardware

  El verificador es el que decide si este robot está listo, y sale con código
  != 0 si algo falla. No des el robot por bueno sin él.

  ✅ EL ROBOT ARRANCA SOLO (paso 8/9, desde el 2026-08-01)

  El servicio queda HABILITADO pero no arrancado: entra en el próximo reinicio.

  ⚠️ Y arrancará con el barrido del LIDAR APAGADO, así que NO CONDUCIRÁ hasta:

      atriz-escaneo on

     No está roto: sin /scan el collision_monitor bloquea el movimiento, que es
     lo que hace seguro arrancar así. Manual, cap. 17.2.

  ¿Y PARA LOS OTROS 15 ROBOTS?

  Cuando ESTE robot pase la verificación de extremo a extremo del plan, se
  convierte en imagen dorada y los demás se clonan de ella:

      sudo bash $SCRIPTS/fase_6_preparar_imagen_dorada.sh
      # apagar, sacar la tarjeta, y hacer el dd desde un PC

  Y por cada robot nuevo, desde el PC:

      sudo bash $SCRIPTS/preparar_tarjeta.sh --id NN

  El procedimiento completo está en 03_operacion/FLOTA.md.
────────────────────────────────────────────────────────────────────────────
EOF

[[ ${#FALLOS[@]} -eq 0 ]] || exit 1
exit 0
