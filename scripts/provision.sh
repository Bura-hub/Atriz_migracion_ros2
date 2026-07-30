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
say "0/7 · Comprobar que el punto de partida es el esperado"

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
say "1/7 · Terminar las actualizaciones pendientes"

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
    avi "no es un problema — el paso 8/8 te dirá cuándo reiniciar"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "2/7 · Paquetes del sistema"

# iw               apagar el power-save del WiFi. NO viene en Server 24.04.
# python3-aiohttp  sphero_sdk/__init__.py lo importa SIN CONDICIONES (a través de
#                  rvr_fw_check_async -> cms_fw_check_base.py:2). Sin él el SDK no
#                  importa, aunque solo se USE para consultar el firmware por web.
# python3-serial   pyserial, el enlace serie.
# python3-pip      necesario solo para pyserial-asyncio, que no está en apt.
PAQUETES=(iw python3-serial python3-aiohttp python3-pip git)
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
say "3/7 · UART del RVR  (delega en fase_0_1_fix_uart.sh)"

if [[ $SIMULAR -eq 1 ]]; then
    printf '  %s[simular]%s bash %s\n' "$GRIS" "$FIN" "$SCRIPTS/fase_0_1_fix_uart.sh"
elif bash "$SCRIPTS/fase_0_1_fix_uart.sh"; then
    ok "fase_0_1_fix_uart.sh completado"
else
    mal "fase_0_1_fix_uart.sh falló"; FALLOS+=("UART")
fi

# ─────────────────────────────────────────────────────────────────────────────
say "4/7 · Higiene del SO  (delega en fase_1_higiene_so.sh)"

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
say "5/7 · Código del robot en ~/atriz_ws"

WS="$HOME_USUARIO/atriz_ws/src"
if [[ -d "$WS/Atriz_rvr/.git" ]]; then
    salta "Atriz_rvr ya está en $WS"
    # Regla nº1 del proyecto: fetch ANTES de mirar el código. El 2026-07-29 se
    # auditó un clon 5 commits por detrás y tres hallazgos salieron falsos.
    correr sudo -u "$USUARIO" git -C "$WS/Atriz_rvr" fetch origin \
        && ok "fetch hecho" || avi "no se pudo hacer fetch (¿sin red? ¿sin credenciales?)"
    R="$(sudo -u "$USUARIO" git -C "$WS/Atriz_rvr" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    ok "rama actual: $R"
else
    correr install -d -o "$USUARIO" -g "$USUARIO" "$WS"
    if correr sudo -u "$USUARIO" git clone -q -b ros2 \
            https://github.com/Bura-hub/Atriz_rvr.git "$WS/Atriz_rvr"; then
        ok "Atriz_rvr clonado en $WS (rama ros2)"
    else
        mal "fallo al clonar Atriz_rvr"; FALLOS+=("clonar Atriz_rvr")
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
say "6/7 · ROS 2 Jazzy"

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

    DEB=/tmp/ros2-apt-source.deb
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
say "7/8 · El robot completo: xacro, LIDAR, SLAM y compilar"

# Esta es la Etapa F de INSTALACION.md. Sin ella el robot tiene ROS 2 y el codigo
# clonado, pero no arranca: falta xacro para el URDF, el driver del LIDAR (que NO
# tiene paquete apt) y slam_toolbox.

if [[ $SIN_ROS -eq 1 ]]; then
    salta "saltado por --sin-ros"
elif [[ ! -d /opt/ros/jazzy ]]; then
    salta "sin ROS 2 instalado, no hay nada que compilar"
else
    # xacro NO viene en ros-base y hace falta para el URDF. slam_toolbox tampoco.
    espera_lock || true
    correr apt-get install -y -qq ros-jazzy-xacro ros-jazzy-slam-toolbox \
        && ok "ros-jazzy-xacro + ros-jazzy-slam-toolbox instalados" \
        || { mal "fallo instalando xacro/slam_toolbox"; FALLOS+=("xacro/slam_toolbox"); }

    # 🔴 El driver del YDLIDAR NO tiene paquete apt. Comprobado el 2026-07-30:
    # `apt-cache search ydlidar` da 0 resultados. Se compila desde fuentes.
    if [[ -f /usr/local/lib/libydlidar_sdk.a ]]; then
        salta "YDLidar-SDK ya está en /usr/local"
    else
        SDKDIR="$HOME_USUARIO/YDLidar-SDK"
        [[ -d "$SDKDIR/.git" ]] || correr sudo -u "$USUARIO" git clone -q \
            https://github.com/YDLIDAR/YDLidar-SDK.git "$SDKDIR"
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
    if [[ -d "$WS/ydlidar_ros2_driver" ]]; then
        salta "ydlidar_ros2_driver ya está en $WS"
    elif correr sudo -u "$USUARIO" git clone -q -b humble \
            https://github.com/YDLIDAR/ydlidar_ros2_driver.git "$WS/ydlidar_ros2_driver"; then
        correr rm -rf "$WS/ydlidar_ros2_driver/.git"
        ok "ydlidar_ros2_driver clonado (rama humble, sin .git)"
    else
        mal "fallo al clonar ydlidar_ros2_driver"; FALLOS+=("ydlidar_ros2_driver")
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
    else
        avi "no se encontró $UDEV_SRC — /dev/ydlidar no existirá"
    fi

    # Y compilar. Que `colcon build` no falle es la prueba de que lo anterior
    # esta en su sitio.
    if correr sudo -u "$USUARIO" bash -c \
        "source /opt/ros/jazzy/setup.bash && cd '$HOME_USUARIO/atriz_ws' && colcon build --symlink-install >/dev/null 2>&1"; then
        ok "workspace compilado (colcon build)"
    else
        mal "colcon build falló"; FALLOS+=("colcon build")
        avi "míralo a mano: cd ~/atriz_ws && colcon build --symlink-install"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
say "8/8 · Resumen"

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

  El verificador es el que decide si este robot está listo: 50 comprobaciones,
  y sale con código != 0 si algo falla. No des el robot por bueno sin él.

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
