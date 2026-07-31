#!/usr/bin/env bash
#
# Fase 7 — Arranque automático del robot con systemd
#
#     sudo bash fase_7_systemd.sh              # instala y habilita
#     sudo bash fase_7_systemd.sh --id 1       # y además crea la identidad ROS
#     sudo bash fase_7_systemd.sh --simular    # enseña qué haría, sin tocar nada
#     sudo bash fase_7_systemd.sh --quitar     # desinstala
#
# ✅ VERIFICADO DE EXTREMO A EXTREMO el 2026-07-31, con un reinicio de verdad:
#    el servicio volvió SOLO (PID 711, o sea del arranque), /scan a 0.00 Hz,
#    /odom a 16.49 Hz y el robot bloqueado sin barrido (0.0 cm contra 9.9 del
#    control). Evidencia 33.
#
# 📝 Lo que NO se ha ejercitado: la espera de puertos del envoltorio —las tres
#    veces salió `tras 0s`, udev llega antes— y `Restart=always`. Son redes de
#    seguridad sin estrenar, no comprobaciones aprobadas.
#
# ═══════════════════════════════════════════════════════════════════════════════
# QUÉ INSTALA
# ═══════════════════════════════════════════════════════════════════════════════
#   /usr/local/bin/atriz-robot.sh        el envoltorio que fija el entorno
#   /usr/local/bin/atriz-escaneo         encender/apagar el barrido del LIDAR
#   /etc/systemd/system/atriz-robot.service
#
# ═══════════════════════════════════════════════════════════════════════════════
# POR QUÉ ES NECESARIO, Y POR QUÉ NO BASTA CON UN ExecStart
# ═══════════════════════════════════════════════════════════════════════════════
#   En un laboratorio REMOTO nadie puede entrar a arrancar un proceso. Si un
#   robot se reinicia —corte de luz, kernel actualizado, watchdog— tiene que
#   volver solo, o queda inservible hasta que alguien vaya al edificio.
#
#   Pero systemd no ejecuta un shell de login: no lee ~/.bashrc ni
#   /etc/profile.d. Un ExecStart directo arrancaría SIN ROS_DOMAIN_ID, o sea con
#   los 16 robots en el dominio 0 viéndose entre sí — el fallo que la decisión D1
#   de ARQUITECTURA.md existe para evitar, y que no da ningún error.
#   De eso se encarga atriz-robot.sh.
#
# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 EL ROBOT ARRANCA CON EL BARRIDO DEL LIDAR APAGADO
# ═══════════════════════════════════════════════════════════════════════════════
#   Medido el 2026-07-31: el X2 gira SIEMPRE, a 2.7 Hz en reposo y 11.8 Hz
#   escaneando. Hoy se queda en 2.7 porque no hay nada corriendo. En cuanto los
#   16 robots levanten robot.launch.py solos, sería 11.8 Hz permanentes, 24/7,
#   se usen o no — peor que ahora, y como efecto secundario de esta tarea.
#
#   ⚠️ CONSECUENCIA QUE HAY QUE CONOCER: un robot recién arrancado NO CONDUCE
#      hasta que se enciende el barrido. No está roto. Es el collision_monitor
#      haciendo su trabajo: sin /scan bloquea el movimiento.
#
#          atriz-escaneo on        # y ya conduce
#
#      Cuando exista la plataforma web (Fase 5), esa llamada la hará ella al
#      empezar una sesión.
#
set -uo pipefail

MODO=instalar
ID_FORZADO=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --simular) MODO=simular ;;
        --quitar)  MODO=quitar ;;
        --id)      ID_FORZADO="${2:-}"; shift ;;
        *) echo "uso: $0 [--simular|--quitar] [--id NN]" >&2; exit 2 ;;
    esac
    shift
done

[[ $EUID -ne 0 ]] && { echo "Ejecuta con sudo: sudo bash $0 ${1:-}" >&2; exit 1; }

say()  { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
avis() { printf '  \033[1;33m!\033[0m %s\n' "$1"; }
mal()  { printf '  \033[1;31m✗\033[0m %s\n' "$1"; }

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_USER="${SUDO_USER:-sphero}"

hacer() {
    if [[ $MODO == simular ]]; then
        printf '  \033[0;36m[simular]\033[0m %s\n' "$*"
    else
        "$@"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
if [[ $MODO == quitar ]]; then
    say "Desinstalando el arranque automático"
    systemctl disable --now atriz-robot.service 2>/dev/null || true
    rm -f /etc/systemd/system/atriz-robot.service
    rm -f /usr/local/bin/atriz-robot.sh /usr/local/bin/atriz-escaneo
    systemctl daemon-reload
    ok "quitado. El robot ya no arranca solo."
    avis "los procesos que estuvieran corriendo NO se han tocado"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
say "1/5 · Comprobar que hay algo que arrancar"

FALLOS=0
comprobar() {
    if eval "$2" >/dev/null 2>&1; then ok "$1"; else mal "$1"; (( FALLOS++ )); fi
}
comprobar "el workspace está compilado" \
          "[[ -f /home/$REAL_USER/atriz_ws/install/setup.bash ]]"
comprobar "existe robot.launch.py instalado" \
          "ls /home/$REAL_USER/atriz_ws/install/atriz_rvr_bringup/share/atriz_rvr_bringup/launch/robot.launch.py"
comprobar "ROS 2 Jazzy está instalado" "[[ -f /opt/ros/jazzy/setup.bash ]]"
comprobar "existe el envoltorio en el repo" "[[ -f $SCRIPTS_DIR/atriz-robot.sh ]]"
comprobar "existe la unidad en el repo"     "[[ -f $SCRIPTS_DIR/atriz-robot.service ]]"
comprobar "existe atriz-escaneo en el repo" "[[ -f $SCRIPTS_DIR/atriz-escaneo.sh ]]"

# ── La identidad ROS, que es lo único que systemd no puede heredar ───────────
# 🔴 En el ROBOT DE REFERENCIA esto NO existe: ROS_DOMAIN_ID sale del ~/.bashrc,
# y systemd no ejecuta un shell de login. Sin este fichero el servicio arrancaría
# en el dominio 0 —los 16 robots viéndose entre sí— o, con el envoltorio actual,
# se negaría a arrancar. Las dos cosas al primer reinicio, no ahora.
#
# 📝 Aquí solo se COMPRUEBA si se sabe qué número tiene el robot. Crear el fichero
#    es un cambio en el sistema y va en el paso 3, después de decidir que se
#    instala: no se toca nada durante una fase de comprobación que puede abortar.
CREAR_IDENTIDAD=no
ID_NUM=""
if [[ -f /etc/profile.d/atriz-robot.sh ]]; then
    ok "/etc/profile.d/atriz-robot.sh (de donde sale ROS_DOMAIN_ID)"
else
    ID_NUM="$ID_FORZADO"
    if [[ -z "$ID_NUM" && -f /boot/firmware/robot_id.txt ]]; then
        ID_NUM=$(tr -dc '0-9' < /boot/firmware/robot_id.txt | head -c2)
        [[ -n "$ID_NUM" ]] && avis "id tomado de /boot/firmware/robot_id.txt: $ID_NUM"
    fi
    if [[ -z "$ID_NUM" ]]; then
        mal "falta /etc/profile.d/atriz-robot.sh y no sé qué número tiene este robot"
        avis "en un clon lo crea first-boot.sh leyendo /boot/firmware/robot_id.txt"
        avis "en el robot de referencia, dímelo tú:  sudo bash $0 --id 1"
        (( FALLOS++ ))
    elif ! [[ "$ID_NUM" =~ ^[0-9]+$ ]] || (( 10#$ID_NUM < 1 || 10#$ID_NUM > 99 )); then
        mal "id '$ID_NUM' no válido (1-99)"
        (( FALLOS++ ))
    else
        ID_NUM=$((10#$ID_NUM))
        CREAR_IDENTIDAD=si
        avis "falta /etc/profile.d/atriz-robot.sh — se creará con ROS_DOMAIN_ID=$ID_NUM"
    fi
fi

# ⚠️ El ~/.bashrc se lee DESPUÉS de /etc/profile.d y GANA. Si los dos exportan
# números distintos, tus shells y el servicio acaban en dominios DDS distintos y
# no se ven — sin un solo error por ningún lado.
if grep -q '^export ROS_DOMAIN_ID=' "/home/$REAL_USER/.bashrc" 2>/dev/null; then
    BASHRC_ID=$(grep -m1 '^export ROS_DOMAIN_ID=' "/home/$REAL_USER/.bashrc" \
                | sed 's/[^0-9]*\([0-9]*\).*/\1/')
    EFECTIVO="$ID_NUM"
    [[ -z "$EFECTIVO" && -f /etc/profile.d/atriz-robot.sh ]] && \
        EFECTIVO=$(sed -n 's/^export ROS_DOMAIN_ID=\([0-9]*\).*/\1/p' \
                   /etc/profile.d/atriz-robot.sh | head -1)
    if [[ -n "$EFECTIVO" && "$BASHRC_ID" != "$EFECTIVO" ]]; then
        mal "~/.bashrc exporta ROS_DOMAIN_ID=$BASHRC_ID y el servicio usaría $EFECTIVO"
        mal "el .bashrc se lee DESPUÉS y gana: tus shells y el servicio estarían"
        mal "en dominios DDS distintos y no se verían. Arréglalo antes de seguir."
        (( FALLOS++ ))
    else
        avis "~/.bashrc también exporta ROS_DOMAIN_ID=$BASHRC_ID (coincide)"
        avis "bórralo de ahí ANTES de crear la imagen dorada: se lee después de"
        avis "/etc/profile.d y dejaría los 16 clones en el dominio $BASHRC_ID"
    fi
fi

if (( FALLOS )); then
    mal "$FALLOS comprobaciones fallaron. No se instala nada."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
say "2/5 · ¿Hay ya un robot.launch.py corriendo a mano?"

# 🔴 Kill por `comm` con ps, NUNCA con pkill -f: el patrón coincidiría con la
# línea de comandos de este mismo script y mataría el shell. Pasó dos veces
# (CLAUDE.md).
# Y se descarta el driver DEL PROPIO SERVICIO: al reinstalar sobre un robot ya
# arrancado, este aviso salía señalando al hijo de systemd como si fuera un
# lanzamiento a mano. Un aviso que asusta sin motivo se acaba ignorando igual que
# un fallo falso. Se distingue por el cgroup, que es de dónde cuelga de verdad.
VIVOS=""
for P in $(ps -eo pid,comm | awk '$2=="rvr_driver_node"{print $1}'); do
    if grep -q 'atriz-robot\.service' "/proc/$P/cgroup" 2>/dev/null; then
        continue
    fi
    VIVOS="$VIVOS $P"
done
VIVOS="${VIVOS# }"
if [[ -n "$VIVOS" ]]; then
    avis "hay un driver lanzado A MANO (PID $VIVOS)"
    avis "systemd NO lo tocará, pero los dos se pelearán por /dev/rvr"
    avis "páralo antes de arrancar el servicio, o reinicia la Pi"
elif systemctl is-active --quiet atriz-robot 2>/dev/null; then
    ok "solo corre el driver del propio servicio (se reiniciará al aplicar esto)"
else
    ok "nada corriendo, el puerto está libre"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "3/5 · Instalar los ficheros"

if [[ $CREAR_IDENTIDAD == si ]]; then
    if [[ $MODO == simular ]]; then
        printf '  \033[0;36m[simular]\033[0m crear /etc/profile.d/atriz-robot.sh con ROS_DOMAIN_ID=%s\n' "$ID_NUM"
    else
        # `cat` directo y no `hacer`: con `hacer` el `> fichero` se tragaría
        # también el mensaje de simulación, y el paso parecería no existir.
        cat > /etc/profile.d/atriz-robot.sh <<EOF
# Identidad del robot — creado por fase_7_systemd.sh el $(date -I).
# En los clones lo REGENERA atriz-first-boot a partir de robot_id.txt.
export ATRIZ_ROBOT_ID=$(printf '%02d' "$ID_NUM")
export ATRIZ_NAMESPACE=rvr_$(printf '%02d' "$ID_NUM")
export ROS_DOMAIN_ID=$ID_NUM
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
EOF
        chmod 644 /etc/profile.d/atriz-robot.sh
        ok "/etc/profile.d/atriz-robot.sh  (ROS_DOMAIN_ID=$ID_NUM)"
    fi
fi

hacer install -m 755 "$SCRIPTS_DIR/atriz-robot.sh"   /usr/local/bin/atriz-robot.sh
ok "/usr/local/bin/atriz-robot.sh"
hacer install -m 755 "$SCRIPTS_DIR/atriz-escaneo.sh" /usr/local/bin/atriz-escaneo
ok "/usr/local/bin/atriz-escaneo"
hacer install -m 644 "$SCRIPTS_DIR/atriz-robot.service" /etc/systemd/system/atriz-robot.service
ok "/etc/systemd/system/atriz-robot.service"

# ─────────────────────────────────────────────────────────────────────────────
say "4/5 · Habilitar"

hacer systemctl daemon-reload
hacer systemctl enable atriz-robot.service
ok "atriz-robot.service habilitado (arrancará en el próximo reinicio)"

# ─────────────────────────────────────────────────────────────────────────────
say "5/5 · Comprobar el efecto, no la intención"

if [[ $MODO == simular ]]; then
    avis "en modo simulación no hay nada que comprobar"
else
    # `systemd-analyze verify` lee la unidad como lo hará systemd y se queja de
    # directivas mal escritas — que si no, fallan en silencio en el reinicio.
    if systemd-analyze verify /etc/systemd/system/atriz-robot.service 2>&1 | grep -q .; then
        avis "systemd-analyze verify tiene algo que decir:"
        systemd-analyze verify /etc/systemd/system/atriz-robot.service 2>&1 | sed 's/^/     /'
    else
        ok "systemd-analyze verify: sin quejas"
    fi
    if systemctl is-enabled atriz-robot.service >/dev/null 2>&1; then
        ok "is-enabled: $(systemctl is-enabled atriz-robot.service)"
    else
        mal "is-enabled dice que NO está habilitado"
    fi
fi

cat <<'EOF'

════════════════════════════════════════════════════════════════════════════
  Instalado. Ahora falta PROBARLO, que es lo único que lo verifica.

    sudo systemctl start atriz-robot        # sin reiniciar
    systemctl status atriz-robot
    journalctl -u atriz-robot -f            # Ctrl-C para salir

  ⚠️ EL ROBOT NO CONDUCIRÁ TODAVÍA, y no está roto: arranca con el barrido del
     LIDAR apagado a propósito, y sin /scan el collision_monitor bloquea el
     movimiento. Para usarlo:

    atriz-escaneo on          # el X2 sube de 2.7 a 11.8 Hz y el robot conduce
    atriz-escaneo estado
    atriz-escaneo off         # al terminar la sesión

  Y la prueba de verdad, la que dice si un robot remoto se recupera solo:

    sudo reboot
    systemctl status atriz-robot            # debe estar active (running)
════════════════════════════════════════════════════════════════════════════
EOF
