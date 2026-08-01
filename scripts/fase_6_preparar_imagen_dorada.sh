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
say "1/6 · Instalar el servicio de personalización de primer arranque"

install -m 755 "$SCRIPTS_DIR/first-boot.sh"       /usr/local/sbin/atriz-first-boot.sh
install -m 644 "$SCRIPTS_DIR/first-boot.service"  /etc/systemd/system/atriz-first-boot.service
systemctl daemon-reload
systemctl enable atriz-first-boot.service
ok "atriz-first-boot.service habilitado"

# Plantilla del fichero de identidad, en la partición FAT (editable desde cualquier PC)
if [[ ! -f /boot/firmware/robot_id.txt ]]; then
    cat > /boot/firmware/robot_id.txt <<'EOF'
# Identidad de este robot. Editable desde Windows, macOS o Linux sin arrancar la Pi.
# Cambia el número y nada más. Rango válido: 01 a 16.
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
: > /var/log/wtmp  2>/dev/null || true
: > /var/log/btmp  2>/dev/null || true
: > /var/log/lastlog 2>/dev/null || true
apt-get clean
rm -f  "$REAL_HOME/.bash_history" /root/.bash_history
rm -rf "$REAL_HOME/.cache/pip" "$REAL_HOME/.ros/log"
ok "logs, cachés e historial limpiados"

# ─────────────────────────────────────────────────────────────────────────────
say "5/6 · Comprobar que no queda nada personal ni secreto"
PROB=0
for f in "$REAL_HOME/.ssh/id_rsa" "$REAL_HOME/.ssh/id_ed25519" "$REAL_HOME/.git-credentials"; do
    [[ -f "$f" ]] && { avis "PRESENTE: $f  <- se clonará en los 16 robots"; PROB=1; }
done
if [[ $PROB -eq 1 ]]; then
    avis "Decide: si la clave/token es compartida a propósito, adelante."
    avis "Si es TU credencial personal, bórrala antes del dd:"
    avis "    rm -f $REAL_HOME/.git-credentials $REAL_HOME/.ssh/id_*"
else
    ok "sin claves privadas ni tokens en el home"
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
