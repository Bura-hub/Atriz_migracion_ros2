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

# 🔴 TERCERA VEZ QUE ESTE SCRIPT AFIRMA UN EFECTO QUE NO OCURRE, y las tres han
#    sido en `--simular`. Las dos anteriores: «se reiniciará al aplicar esto»
#    (falso, no hay ningún restart) e «Instalado.» sin instalar. Esta, la peor
#    por número: los `ok` que seguían a cada `hacer` se imprimían SIEMPRE, así
#    que un ensayo en seco sacaba SIETE ✓ —incluido «atriz-robot.service
#    habilitado»— sin haber tocado nada. Y el paso 5, que es el que comprobaría,
#    se salta en simulación: los ✓ falsos eran la única salida.
#    Encontrado el 2026-08-04 leyendo la salida de `--simular` del usuario.
#
#    `hecho` dice la verdad en los dos modos: ✓ cuando se hizo, y un «(sin
#    hacer)» explícito cuando no. La lección ya estaba escrita en el comentario
#    del arreglo anterior — no bastó con arreglar el caso que falló entonces.
hecho() {
    if [[ $MODO == simular ]]; then
        printf '  \033[0;36m·\033[0m %s \033[0;36m(sin hacer: es un ensayo)\033[0m\n' "$1"
    else
        ok "$1"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
if [[ $MODO == quitar ]]; then
    say "Desinstalando el arranque automático"
    systemctl disable --now atriz-slam.service 2>/dev/null || true
    systemctl disable --now atriz-nav.service 2>/dev/null || true
    systemctl disable --now atriz-robot.service 2>/dev/null || true
    rm -f /etc/systemd/system/atriz-robot.service /etc/systemd/system/atriz-nav.service \
          /etc/systemd/system/atriz-slam.service
    rm -f /usr/local/bin/atriz-robot.sh /usr/local/bin/atriz-escaneo
    rm -f /usr/local/bin/atriz-nav.sh /usr/local/bin/atriz-slam.sh \
          /usr/local/bin/atriz-exclusion
    rm -f /usr/local/bin/atriz-vigia-dds /usr/local/bin/vigia_dds.py
    rm -f /usr/local/bin/atriz-lidar-reenganche \
          /etc/systemd/system/atriz-lidar-reenganche.service \
          /etc/udev/rules.d/98-atriz-lidar-reenganche.rules
    udevadm control --reload-rules 2>/dev/null || true
    rm -f /etc/polkit-1/rules.d/49-atriz-unidades.rules
    # /etc/default/atriz NO se borra: lo edita el operador y puede llevar la
    # ruta de un mapa que costó una sesión de mapeo. Se avisa y se deja.
    [[ -f /etc/default/atriz ]] && \
        echo "  · /etc/default/atriz se DEJA (lo edita el operador). Bórralo a mano si quieres."
    # El entorno de ROS de los shells. Se quita también, o quedaría un fichero
    # huérfano que `verificar_robot.sh` sección 13 no sabría de dónde viene.
    # ⚠️ NO se toca /etc/profile.d/atriz-robot.sh: ese lleva la IDENTIDAD del
    #    robot y lo genera atriz-first-boot, no este script.
    rm -f /etc/profile.d/atriz-ros.sh
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
# Los de la navegación y el entorno: si faltan, `install` fallaría a mitad de la
# instalación y dejaría el robot a medias. Mejor negarse antes de tocar nada.
comprobar "existe atriz-nav.sh en el repo"     "[[ -f $SCRIPTS_DIR/atriz-nav.sh ]]"
comprobar "existe atriz-nav.service en el repo" "[[ -f $SCRIPTS_DIR/atriz-nav.service ]]"
comprobar "existe atriz-slam.sh en el repo"    "[[ -f $SCRIPTS_DIR/atriz-slam.sh ]]"
comprobar "existe atriz-slam.service en el repo" "[[ -f $SCRIPTS_DIR/atriz-slam.service ]]"
comprobar "existe atriz-exclusion.sh en el repo" "[[ -f $SCRIPTS_DIR/atriz-exclusion.sh ]]"
comprobar "existe atriz-vigia-dds.sh en el repo" "[[ -f $SCRIPTS_DIR/atriz-vigia-dds.sh ]]"
comprobar "existe vigia_dds.py en el repo"       "[[ -f $SCRIPTS_DIR/sistema/vigia_dds.py ]]"
comprobar "existe atriz-lidar-reenganche.sh en el repo" "[[ -f $SCRIPTS_DIR/sistema/atriz-lidar-reenganche.sh ]]"
comprobar "existe atriz-lidar-reenganche.service en el repo" "[[ -f $SCRIPTS_DIR/sistema/atriz-lidar-reenganche.service ]]"
comprobar "existe 98-atriz-lidar-reenganche.rules en el repo" "[[ -f $SCRIPTS_DIR/sistema/98-atriz-lidar-reenganche.rules ]]"
comprobar "existe la regla de polkit en el repo" \
          "[[ -f $SCRIPTS_DIR/sistema/49-atriz-unidades.rules ]]"
comprobar "existe la plantilla de ajustes en el repo" \
          "[[ -f $SCRIPTS_DIR/sistema/atriz-defaults ]]"
comprobar "existe sistema/atriz-ros.sh en el repo" "[[ -f $SCRIPTS_DIR/sistema/atriz-ros.sh ]]"

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
        # 🔴 ANCLADO al principio de línea y a la sintaxis exacta, igual que en
        #    first-boot.sh:56. La versión anterior era:
        #        tr -dc '0-9' < robot_id.txt | head -c2
        #    que coge los DOS PRIMEROS DÍGITOS DEL FICHERO, comentarios
        #    incluidos. Medido el 2026-08-03 contra la plantilla que escribe
        #    fase_6 —cuyo comentario dice «Rango válido: 01 a 16»—: con
        #    ROBOT_ID=07 devolvía 01. Los 16 robots habrían salido con
        #    ROS_DOMAIN_ID=1, viéndose todos entre sí, que es exactamente lo que
        #    la Decisión 1 de ARQUITECTURA.md existe para evitar.
        #    Y sin dar ningún error: solo robots que se ven de más.
        #    Evidencia: 00_auditoria/evidencia/64_parser_robot_id.txt
        ID_NUM=$(grep -oP '^\s*ROBOT_ID\s*=\s*\K[0-9]+' /boot/firmware/robot_id.txt | head -1)
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
RECORDAR_REINICIO=no
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
    # 🔴 Este mensaje decía «se reiniciará al aplicar esto», y era FALSO: este
    #    script no tiene un solo `systemctl restart`. `install` sustituye el
    #    inodo del fichero y `daemon-reload` recarga las UNIDADES, pero ninguna
    #    de las dos cosas toca un proceso vivo — el driver sigue ejecutando el
    #    código viejo hasta que alguien lo reinicie.
    #    Lo detectó el usuario al leer la salida de --simular el 2026-08-03.
    #    Un mensaje que anuncia un efecto que no ocurre es peor que no decir
    #    nada: se lee «ya está aplicado» y se cierra la sesión creyéndolo.
    ok "solo corre el driver del propio servicio (systemd lo lanzó, no tú)"
    RECORDAR_REINICIO=si
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

# ── El entorno de ROS de los shells ──────────────────────────────────────────
# 🔴 Sin esto, un robot montado desde cero solo con los repositorios tendría
#    shells interactivos SIN `ros2`: en rvr-01 esas líneas vivían en el
#    ~/.bashrc y NINGÚN script las escribía (medido el 2026-08-03).
#    Va en /etc/profile.d y NO en el .bashrc a propósito: se lee ANTES, así que
#    desaparece la trampa del «.bashrc gana» que este script avisa más arriba.
#    No lleva identidad dentro — el ROS_DOMAIN_ID sigue saliendo de
#    atriz-robot.sh, que por orden alfabético se lee justo antes.
hacer install -m 644 "$SCRIPTS_DIR/sistema/atriz-ros.sh" /etc/profile.d/atriz-ros.sh
hecho "/etc/profile.d/atriz-ros.sh (entorno de ROS, sin identidad)"

# ── Y el puente para los shells que NO son de login ──────────────────────────
# /etc/profile.d lo leen los shells de LOGIN. Un `tmux`, un `su` o un `bash`
# suelto son interactivos y NO de login: no pasan por ahí y se quedarían sin
# `ros2`. Una línea en el ~/.bashrc lo resuelve.
#
# 📝 Categoría B (scripts/sistema/README.md): el ~/.bashrc pertenece a la
#    distribución, así que NO se versiona una copia — se versiona el generador,
#    que es esto, y el efecto lo comprueba verificar_robot.sh.
#    Se AÑADE, nunca se reescribe el fichero: dentro hay ajustes del usuario.
BRC="/home/$REAL_USER/.bashrc"
if [[ ! -f "$BRC" ]]; then
    avis "no hay $BRC: los shells no-login de $REAL_USER no tendrán ros2"
elif grep -qF '/etc/profile.d/atriz-ros.sh' "$BRC"; then
    ok "~/.bashrc ya llama a /etc/profile.d/atriz-ros.sh"
elif [[ $MODO == simular ]]; then
    printf '  \033[0;36m[simular]\033[0m %s\n' "añadir el puente a $BRC"
else
    cat >> "$BRC" <<'EOF'

# ── ROS 2, para los shells interactivos que NO son de login ───────────────────
# Lo añade fase_7_systemd.sh. El entorno vive en /etc/profile.d/atriz-ros.sh,
# que solo leen los shells de LOGIN; esto cubre tmux, su y un bash suelto.
# Con guarda, para que un robot al que aún no se le ha pasado fase_7 no dé un
# error en cada shell.
[ -f /etc/profile.d/atriz-ros.sh ] && . /etc/profile.d/atriz-ros.sh
EOF
    chown "$REAL_USER:$REAL_USER" "$BRC" 2>/dev/null || true
    ok "~/.bashrc: añadido el puente a /etc/profile.d/atriz-ros.sh"
fi

hacer install -m 755 "$SCRIPTS_DIR/atriz-robot.sh"   /usr/local/bin/atriz-robot.sh
hecho "/usr/local/bin/atriz-robot.sh"
hacer install -m 755 "$SCRIPTS_DIR/atriz-escaneo.sh" /usr/local/bin/atriz-escaneo
hecho "/usr/local/bin/atriz-escaneo"
hacer install -m 644 "$SCRIPTS_DIR/atriz-robot.service" /etc/systemd/system/atriz-robot.service
hecho "/etc/systemd/system/atriz-robot.service"

# ── La navegación, que se instala pero NO se habilita ────────────────────────
hacer install -m 755 "$SCRIPTS_DIR/atriz-nav.sh"      /usr/local/bin/atriz-nav.sh
hecho "/usr/local/bin/atriz-nav.sh"
hacer install -m 644 "$SCRIPTS_DIR/atriz-nav.service" /etc/systemd/system/atriz-nav.service
hecho "/etc/systemd/system/atriz-nav.service"

# ── SLAM y las piezas que comparten las dos unidades (2026-08-07) ────────────
# 🔴 `atriz-exclusion` va ANTES que las unidades en el orden mental, aunque el
#    orden de instalación no importe: sin él, los dos `ExecStartPre` fallarían y
#    NINGUNA de las dos arrancaría. Es dependencia dura, no adorno.
hacer install -m 755 "$SCRIPTS_DIR/atriz-exclusion.sh" /usr/local/bin/atriz-exclusion
hecho "/usr/local/bin/atriz-exclusion"
hacer install -m 755 "$SCRIPTS_DIR/atriz-slam.sh"      /usr/local/bin/atriz-slam.sh
hecho "/usr/local/bin/atriz-slam.sh"
hacer install -m 644 "$SCRIPTS_DIR/atriz-slam.service" /etc/systemd/system/atriz-slam.service
hecho "/etc/systemd/system/atriz-slam.service"

# El vigía de DDS: contra el robot que nace MUDO en un arranque en frío
# (evidencia 109 — intermitente, causa sin conocer, remedio medido 2 de 2).
# Lo llama atriz-robot.service como ExecStartPost=-; reinicia UNA vez por
# arranque (SIGINT al proceso principal + Restart=always) y falla abierto.
hacer install -m 755 "$SCRIPTS_DIR/atriz-vigia-dds.sh"    /usr/local/bin/atriz-vigia-dds
hecho "/usr/local/bin/atriz-vigia-dds"
hacer install -m 755 "$SCRIPTS_DIR/sistema/vigia_dds.py"  /usr/local/bin/vigia_dds.py
hecho "/usr/local/bin/vigia_dds.py"

# El reenganche del LIDAR tras re-enumerar el USB (evidencia 69 §6, decisión A
# del 2026-08-14): udev dispara una oneshot que reinicia atriz-robot SOLO si el
# nodo quedó con el descriptor muerto. Casi siempre es un no-op con guardias.
hacer install -m 755 "$SCRIPTS_DIR/sistema/atriz-lidar-reenganche.sh" /usr/local/bin/atriz-lidar-reenganche
hecho "/usr/local/bin/atriz-lidar-reenganche"
hacer install -m 644 "$SCRIPTS_DIR/sistema/atriz-lidar-reenganche.service" /etc/systemd/system/atriz-lidar-reenganche.service
hecho "/etc/systemd/system/atriz-lidar-reenganche.service"
hacer install -m 644 "$SCRIPTS_DIR/sistema/98-atriz-lidar-reenganche.rules" /etc/udev/rules.d/98-atriz-lidar-reenganche.rules
# ⚠️ Sin el reload, la regla existe y no actúa — la familia de siempre. NO se
#    hace `udevadm trigger`: re-dispararía eventos add y con ellos el
#    reenganche (inofensivo por los guardias, pero ruido gratis en el journal).
hacer udevadm control --reload-rules
hecho "/etc/udev/rules.d/98-atriz-lidar-reenganche.rules (+ reload de udev)"

# La regla de polkit: sin ella, `supervisor_navegacion` recibe «Interactive
# authentication required» al llamar a systemctl (verificado el 2026-08-07) y
# los botones de la web no hacen nada.
# ── Los ajustes compartidos, y NO se sobrescriben ────────────────────────────
# 🔴 `/etc/default/atriz` está pensado para que el OPERADOR lo edite: la ruta del
#    mapa de SU aula, o de su cuarto si está probando. Reinstalar no puede
#    borrarle eso. Por la misma razón NO está en el manifiesto —que es para
#    ficheros idénticos en los 16, comprobados con `cmp`— y se verifica POR
#    EFECTO: que las unidades lo declaren y que defina el mapa.
if [[ -f /etc/default/atriz ]]; then
    hecho "/etc/default/atriz ya existe: NO se toca (lo edita el operador)"
else
    hacer install -m 644 "$SCRIPTS_DIR/sistema/atriz-defaults" /etc/default/atriz
    hecho "/etc/default/atriz (plantilla; edítalo si tu mapa está en otro sitio)"
fi

hacer install -d -m 755 /etc/polkit-1/rules.d
hacer install -m 644 "$SCRIPTS_DIR/sistema/49-atriz-unidades.rules" \
                     /etc/polkit-1/rules.d/49-atriz-unidades.rules
hecho "/etc/polkit-1/rules.d/49-atriz-unidades.rules"

# ─────────────────────────────────────────────────────────────────────────────
say "4/5 · Habilitar"

hacer systemctl daemon-reload
hacer systemctl enable atriz-robot.service
hecho "atriz-robot.service habilitado (arrancará en el próximo reinicio)"

# 🔴 atriz-nav NO se habilita, y NO es un olvido. La navegación cuesta ~58 % de
#    un núcleo, y la Pi se alimenta del USB del RVR, así que eso sale de la
#    batería del robot — cuya autonomía (~2 h) ya no cubre una clase (2-3 h).
#    Y aún no se sabe si la web la necesitará siempre o a demanda.
#    Se arranca a mano:  systemctl start atriz-nav
#    El día que haga falta que arranque sola, es un `systemctl enable`.
#    Razonado en 03_operacion/ARRANQUE_NAVEGACION.md.
avis "atriz-nav.service instalado pero NO habilitado (a propósito)"
avis "atriz-slam.service instalado pero NO habilitado (a propósito)"
avis "  los dos se piden desde la web:  /pedir_slam  ·  /pedir_nav"
avis "  o a mano:  systemctl start atriz-slam | atriz-nav"
avis "  arráncalo cuando lo necesites:  sudo systemctl start atriz-nav"

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

# 🔴 EL AVISO QUE FALTABA. install + daemon-reload NO tocan un proceso vivo:
#    el driver que está corriendo sigue con el código de antes. Sin esta línea
#    la sesión se cierra creyendo que el cambio ya está aplicado, y el fallo
#    aparece días después, en el próximo reinicio, sin nada que lo relacione.
if [[ $RECORDAR_REINICIO == si && $MODO != simular ]]; then
    printf '\n  \033[1;33m!\033[0m %s\n' "atriz-robot SIGUE CORRIENDO CON EL CÓDIGO VIEJO."
    printf '  \033[1;33m!\033[0m %s\n'   "Los ficheros están instalados, pero el proceso vivo no los ha leído."
    printf '  \033[1;33m!\033[0m %s\n'   "Para aplicarlo de verdad:  sudo systemctl restart atriz-robot"
    printf '  \033[1;33m!\033[0m %s\n'   "⚠️ Eso DESPIERTA el robot: enciende sus LEDs y tarda unos 30 s."
fi

# ⚠️ En --simular NO se ha instalado nada, y el rótulo decía «Instalado.» de
#    todas formas. Es el mismo tipo de mentira que el «se reiniciará» de arriba,
#    solo que más barata de creer: se lee el rótulo, no los `[simular]`.
if [[ $MODO == simular ]]; then
    cat <<'EOF'

════════════════════════════════════════════════════════════════════════════
  ENSAYO. No se ha instalado nada: eso es todo lo que HARÍA.
  Para aplicarlo de verdad, el mismo comando sin --simular.
════════════════════════════════════════════════════════════════════════════
EOF
    exit 0
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
