#!/usr/bin/env bash
#
# Fase 0.3 — Preparar la microSD para el respaldo
#
#   Ejecutar EN LA RASPBERRY PI, antes de apagarla:
#       bash fase_0_3_respaldo.sh
#
# Este script NO hace la imagen (eso se hace desde un PC con la SD fuera).
# Lo que hace es dejar la tarjeta lista y recoger lo que no está en git:
#   1. Comprueba que no queda trabajo sin commitear, sin SUBIR, o en un STASH
#      (los stashes no viajan a un remoto y desaparecen con la tarjeta)
#   2. Copia claves SSH, netplan e inventario de paquetes a un directorio aparte
#   3. Respalda el historial de Claude Code, por si se quiere reanudar la sesión
#   4. Sincroniza a disco y emite los comandos exactos del dd
#
set -euo pipefail

DEST="$HOME/respaldo_pre_migracion"
STAMP="$(date +%Y%m%d-%H%M%S)"

say() { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }
ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; }
avis(){ printf '  \033[1;33m!\033[0m %s\n' "$1"; }

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
say "3/5 · Respaldar el historial de Claude Code (para intentar reanudar sesión)"

CLDIR="$HOME/.claude/projects/-home-sphero"
if [[ -d "$CLDIR" ]]; then
    mkdir -p "$DEST/claude"
    cp -a "$HOME/.claude/projects" "$DEST/claude/" 2>/dev/null
    [[ -f "$HOME/.claude/history.jsonl" ]] && cp -a "$HOME/.claude/history.jsonl" "$DEST/claude/"
    [[ -d "$HOME/.claude/plans" ]]        && cp -a "$HOME/.claude/plans"        "$DEST/claude/"
    ok "historial de Claude -> $DEST/claude  ($(du -sh "$DEST/claude" | cut -f1))"
    cat > "$DEST/claude/COMO_REANUDAR.md" <<'MD'
# Intentar reanudar la sesión de Claude tras reinstalar

## Aviso: es una red de seguridad, NO el plan principal

La fuente de contexto del proyecto es **el repositorio**, no esta sesión. Reanudar
depende de rutas y de la versión del CLI, y puede simplemente no funcionar.

**El camino fiable es:** arrancar Claude Code en `~/atriz_migracion` y decirle que
siga el repositorio. `CLAUDE.md` se carga automáticamente y le da todo el contexto,
las reglas y las trampas conocidas.

## Si quieres intentarlo de todas formas

1. Instala Claude Code en el sistema nuevo.
2. Arráncalo una vez en `/home/sphero` para que cree `~/.claude/`.
3. Ciérralo y restaura el historial:

   ```bash
   cp -a claude/projects/*  ~/.claude/projects/
   cp -a claude/plans/*     ~/.claude/plans/     2>/dev/null
   cp    claude/history.jsonl ~/.claude/         2>/dev/null
   ```

4. `claude --resume` y elige la sesión del 2026-07-29.

**Condición imprescindible:** el usuario debe seguir siendo `sphero` y el home
`/home/sphero`. El nombre del directorio (`-home-sphero`) codifica esa ruta; si
cambia, el historial no se encontrará.

## Si no funciona

No pasa nada. Arranca Claude en `~/atriz_migracion` y di:

> Lee CLAUDE.md y TRASPASO.md y continúa desde donde se quedó el proyecto.
MD
    ok "instrucciones en $DEST/claude/COMO_REANUDAR.md"
else
    avis "no se encontró historial de Claude en $CLDIR"
fi

# ─────────────────────────────────────────────────────────────────────────────
say "4/5 · Volcar cachés a disco"
sync; ok "sync completado"

# ─────────────────────────────────────────────────────────────────────────────
say "5/5 · Resumen"

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
