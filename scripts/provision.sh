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
espera_lock || true
export DEBIAN_FRONTEND=noninteractive
correr apt-get update -qq && ok "apt-get update" || { mal "apt-get update falló"; FALLOS+=("apt update"); }
correr apt-get full-upgrade -y -qq && ok "full-upgrade" || { mal "full-upgrade falló"; FALLOS+=("full-upgrade"); }

if [[ -f /var/run/reboot-required ]]; then
    avi "hay un reinicio pendiente: $(tr '\n' ' ' < /var/run/reboot-required.pkgs 2>/dev/null)"
    avi "no es un problema — el paso 7/7 te dirá cuándo reiniciar"
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
    if correr sudo -u "$USUARIO" git clone -q -b migracion-ros2 \
            https://github.com/Bura-hub/Atriz_rvr.git "$WS/Atriz_rvr"; then
        ok "Atriz_rvr clonado en $WS (rama migracion-ros2)"
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
    avi "📝 PENDIENTE DE ESCRIBIR — la Etapa E no se ha ejecutado todavía en"
    avi "   ningún robot, así que aquí NO hay comandos. Ponerlos sin haberlos"
    avi "   probado es exactamente lo que este proyecto no hace."
    avi ""
    avi "   Sigue el capítulo 5.2-5.5 del manual a mano, y cuando funcione,"
    avi "   trae los comandos exactos aquí y quita este aviso."
    avi ""
    avi "   Recuerda: ros-jazzy-ros-base, NO desktop (son 236 paquetes con"
    avi "   Gazebo y RViz en un robot sin pantalla)."
fi

# ─────────────────────────────────────────────────────────────────────────────
say "7/7 · Resumen"

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

  El verificador es el que decide si este robot está listo: 36+ comprobaciones,
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
