#!/usr/bin/env bash
#
# Fase 0.3 — Preparar la microSD para el respaldo
#
#   Ejecutar EN LA RASPBERRY PI, antes de apagarla:
#       bash fase_0_3_respaldo.sh
#
# Este script NO hace la imagen (eso se hace desde un PC con la SD fuera).
# Lo que hace es dejar la tarjeta lista y recoger lo que no está en git:
#   1. Comprueba que no queda trabajo sin subir en ningún repo
#   2. Copia claves SSH y la config de red a un directorio aparte
#   3. Sincroniza a disco y deja instrucciones del dd
#
set -euo pipefail

DEST="$HOME/respaldo_pre_migracion"
STAMP="$(date +%Y%m%d-%H%M%S)"

say() { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; }

mkdir -p "$DEST"

# ─────────────────────────────────────────────────────────────────────────────
say "1/4 · ¿Queda trabajo sin subir a GitHub?"

PROBLEMAS=0
for repo in "$HOME/atriz_git/src/Atriz_rvr" "$HOME/atriz_migracion"; do
    [[ -d "$repo/.git" ]] || continue
    nombre=$(basename "$repo")
    sucio=$(git -C "$repo" status --porcelain | grep -v '^??' || true)
    rama=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
    sinsubir=$(git -C "$repo" log --oneline "@{upstream}..HEAD" 2>/dev/null | wc -l || echo '?')
    stashes=$(git -C "$repo" stash list | wc -l)

    echo "  ── $nombre (rama $rama)"
    [[ -n "$sucio" ]]      && { bad "cambios sin commitear:"; echo "$sucio" | sed 's/^/       /'; PROBLEMAS=1; } || ok "sin cambios pendientes"
    [[ "$sinsubir" == "0" ]] && ok "todo subido al remoto" || { bad "$sinsubir commit(s) SIN SUBIR"; PROBLEMAS=1; }
    [[ "$stashes" == "0" ]]  && ok "sin stashes" || { bad "$stashes stash(es) — NO viajan al remoto"; PROBLEMAS=1; }

    # los untracked se respaldan aunque no sean un problema
    git -C "$repo" status --porcelain | awk '$1=="??"{print $2}' | while read -r f; do
        [[ -f "$repo/$f" ]] && install -D "$repo/$f" "$DEST/untracked/$nombre/$f" && echo "       respaldado (sin trackear): $f"
    done
done

# ─────────────────────────────────────────────────────────────────────────────
say "2/4 · Copiar lo que NO está en ningún repositorio"

if [[ -d "$HOME/.ssh" ]]; then
    cp -a "$HOME/.ssh" "$DEST/ssh"; chmod -R go-rwx "$DEST/ssh"
    ok "claves SSH → $DEST/ssh   (¡contienen material privado, no subir a git!)"
fi
if sudo -n true 2>/dev/null; then
    sudo cp /etc/netplan/*.yaml "$DEST/" 2>/dev/null && ok "netplan copiado (contiene la PSK del WiFi)"
else
    bad "netplan necesita sudo — cópialo a mano: sudo cp /etc/netplan/*.yaml $DEST/"
fi
cp "$HOME/.bashrc" "$DEST/bashrc" 2>/dev/null && ok ".bashrc copiado"
{ echo "# Estado del sistema justo antes del respaldo — $STAMP"; echo
  echo "## /dev/rvr"; ls -l /dev/rvr 2>&1
  echo; echo "## ROS"; rosversion -d 2>&1
  echo; echo "## paquetes pip3"; pip3 list 2>/dev/null
  echo; echo "## paquetes ros-noetic"; dpkg -l | awk '/ros-noetic/{print $2, $3}'
} > "$DEST/estado_sistema_${STAMP}.txt"
ok "inventario del sistema → estado_sistema_${STAMP}.txt"

# ─────────────────────────────────────────────────────────────────────────────
say "3/4 · Volcar cachés a disco"
sync; ok "sync completado"

# ─────────────────────────────────────────────────────────────────────────────
say "4/4 · Resumen"

if [[ $PROBLEMAS -eq 0 ]]; then
    ok "Todo el trabajo está en GitHub. Puedes apagar y hacer la imagen."
else
    bad "HAY TRABAJO EN RIESGO (ver arriba). Resuélvelo antes de apagar:"
    echo "       git add -A && git commit && git push          # cambios pendientes"
    echo "       git stash pop  o  git stash branch <nombre>   # stashes"
fi

cat <<EOF

────────────────────────────────────────────────────────────────────────────
  Copia $DEST a un USB o a tu PC. NO va a git (contiene claves y la PSK).

  Luego:  sudo poweroff
  Saca la microSD y, desde un PC:

    Linux/WSL:
      lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL      # identifica el dispositivo
      sudo dd if=/dev/mmcblk0 of=atriz_noetic_fallback.img bs=4M status=progress conv=fsync
      sha256sum atriz_noetic_fallback.img > atriz_noetic_fallback.img.sha256
      gzip -6 atriz_noetic_fallback.img              # 29 GB -> ~4-6 GB

    Windows:
      Win32DiskImager -> boton "Read"

  ⚠️  Un 'of=' equivocado destruye el disco de destino. Verifica dos veces.

  VERIFICA la imagen antes de reflashear (una imagen sin verificar no es un
  respaldo). El procedimiento completo está en 03_operacion/RECUPERACION.md
────────────────────────────────────────────────────────────────────────────
EOF
