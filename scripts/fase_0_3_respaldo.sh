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
say "1/5 · ¿Queda trabajo sin subir a GitHub?"

PROBLEMAS=0
# 🔴 EL `|| continue` SILENCIOSO FUE UN FALLO REAL, encontrado el 2026-08-01.
#    Este bucle miraba `~/atriz_git/src/Atriz_rvr`, que es la ruta del sistema
#    VIEJO (20.04). En 24.04 el repo del robot vive en `~/atriz_ws/src/Atriz_rvr`,
#    así que la ruta no existía, el `continue` la saltaba **sin decir nada**, y el
#    script terminaba con «✓ Todo el trabajo está en GitHub» **habiendo mirado un
#    solo repositorio de los dos**.
#
#    Es el peor fallo posible en ESTE script: existe para que no se pierda trabajo
#    al reflashear, y daba el visto bueno sin comprobar el repositorio del código
#    del robot. Este proyecto YA perdió tiempo una vez por un stash.
#
# → Ahora se buscan las dos ubicaciones posibles, y **la ausencia se avisa**.
REPOS=()
for cand in "$HOME/atriz_ws/src/Atriz_rvr" "$HOME/atriz_git/src/Atriz_rvr" \
            "$HOME/atriz_migracion"; do
    [[ -d "$cand/.git" ]] && REPOS+=("$cand")
done
if [[ ${#REPOS[@]} -lt 2 ]]; then
    printf '  %s! solo se encontró %d repositorio(s) git: %s%s\n' \
           "${AMAR:-}" "${#REPOS[@]}" "${REPOS[*]:-ninguno}" "${FIN:-}"
    printf '    Se esperaban DOS (el código del robot y la documentación).\n'
    printf '    🔴 NO REFLASHEES hasta saber por qué falta uno.\n'
    PROBLEMAS=$((PROBLEMAS+1))
fi
for repo in "${REPOS[@]}"; do
    nombre=$(basename "$repo")
    sucio=$(git -C "$repo" status --porcelain | grep -v '^??' || true)
    rama=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
    sinsubir=$(git -C "$repo" log --oneline "@{upstream}..HEAD" 2>/dev/null | wc -l || echo '?')
    stashes=$(git -C "$repo" stash list | wc -l)

    echo "  ── $nombre (rama $rama)"
    [[ -n "$sucio" ]]      && { bad "cambios sin commitear:"; echo "$sucio" | sed 's/^/       /'; PROBLEMAS=1; } || ok "sin cambios pendientes"
    [[ "$sinsubir" == "0" ]] && ok "todo subido al remoto" || { bad "$sinsubir commit(s) SIN SUBIR"; PROBLEMAS=1; }
    # Los stashes no viajan al remoto. Pero comprobamos si su contenido ya está
    # preservado en algún commit alcanzable: si lo está, el stash es redundante y
    # no hay nada en riesgo. Evita falsas alarmas.
    if [[ "$stashes" == "0" ]]; then
        ok "sin stashes"
    else
        redundantes=0; enriesgo=0
        for i in $(seq 0 $((stashes-1))); do
            todo_ok=1
            while read -r f; do
                [[ -z "$f" ]] && continue
                h=$(git -C "$repo" show "stash@{$i}:$f" 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null)
                [[ -z "$h" ]] && { todo_ok=0; break; }
                # ¿existe ese blob exacto en alguna rama/tag?
                if ! git -C "$repo" cat-file -e "$h" 2>/dev/null; then todo_ok=0; break; fi
                if [[ -z "$(git -C "$repo" branch -a --contains \
                        "$(git -C "$repo" log --all --format=%H --find-object="$h" -1 2>/dev/null)" \
                        2>/dev/null)" ]]; then todo_ok=0; break; fi
            done < <(git -C "$repo" stash show --name-only "stash@{$i}" 2>/dev/null)
            if [[ $todo_ok -eq 1 ]]; then redundantes=$((redundantes+1)); else enriesgo=$((enriesgo+1)); fi
        done
        [[ $redundantes -gt 0 ]] && ok "$redundantes stash(es) redundante(s): su contenido ya está en un commit"
        if [[ $enriesgo -gt 0 ]]; then
            bad "$enriesgo stash(es) EN RIESGO — no viajan al remoto y se perderán"
            git -C "$repo" stash list | sed 's/^/       /'
            PROBLEMAS=1
        fi
    fi

    # los untracked se respaldan aunque no sean un problema
    git -C "$repo" status --porcelain | awk '$1=="??"{print $2}' | while read -r f; do
        [[ -f "$repo/$f" ]] && install -D "$repo/$f" "$DEST/untracked/$nombre/$f" && echo "       respaldado (sin trackear): $f"
    done
done

# ─────────────────────────────────────────────────────────────────────────────
say "2/5 · Copiar lo que NO está en ningún repositorio"

if [[ -d "$HOME/.ssh" ]]; then
    cp -a "$HOME/.ssh" "$DEST/ssh"; chmod -R go-rwx "$DEST/ssh"
    ok "claves SSH → $DEST/ssh   (¡contienen material privado, no subir a git!)"
fi

# Credenciales de git. Sin esto, tras reflashear NO SE PUEDE HACER PUSH y hay que
# generar un token nuevo. Pasó exactamente eso el 2026-07-30: el respaldo llevaba
# ~/.ssh (que además estaba vacío) pero no ~/.git-credentials, así que el sistema
# nuevo se quedó sin forma de subir a un repositorio privado.
for f in "$HOME/.git-credentials" "$HOME/.gitconfig"; do
    [[ -f "$f" ]] || continue
    cp -a "$f" "$DEST/$(basename "$f")" && chmod 600 "$DEST/$(basename "$f")"
    ok "$(basename "$f") → $DEST   (¡contiene un token, no subir a git!)"
done
[[ -f "$HOME/.git-credentials" ]] || avis "no hay ~/.git-credentials: comprueba cómo autenticas con GitHub antes de apagar"
if cp /etc/netplan/*.yaml "$DEST/" 2>/dev/null; then
    ok "netplan copiado (contiene la PSK del WiFi)"
elif sudo -n cp /etc/netplan/*.yaml "$DEST/" 2>/dev/null; then
    ok "netplan copiado con sudo (contiene la PSK del WiFi)"
else
    avis "netplan necesita contraseña. Ejecuta ahora:"
    avis "    sudo cp /etc/netplan/*.yaml $DEST/ && sudo chown \$USER $DEST/*.yaml"
    avis "(no cuenta como trabajo en riesgo: es reconstruible, ver NETPLAN_OMITIDO.md)"
fi
cp "$HOME/.bashrc" "$DEST/bashrc" 2>/dev/null && ok ".bashrc copiado"

# Inventario del sistema. Se escribe SIN la fecha en la cabecera para poder
# compararlo con el anterior: si no ha cambiado nada, no se crea otro fichero.
# (Ejecutar el script 6 veces dejó 6 ficheros byte a byte idénticos salvo la
#  fecha, que es ruido disfrazado de historial.)
TMP_INV="$(mktemp)"
{ echo "## sistema"; lsb_release -ds 2>/dev/null; uname -srm; python3 --version 2>&1
  echo; echo "## /dev/rvr"; ls -l /dev/rvr 2>&1
  echo; echo "## /dev/ttyUSB*"; ls -l /dev/ttyUSB* 2>&1
  echo; echo "## ROS"
  if command -v rosversion >/dev/null; then rosversion -d 2>&1        # ROS 1
  elif [[ -n "${ROS_DISTRO:-}" ]]; then echo "$ROS_DISTRO"            # ROS 2
  else echo "(sin ROS)"; fi
  echo; echo "## paquetes pip3"; pip3 list 2>/dev/null
  echo; echo "## paquetes ROS de apt"; dpkg -l | awk '/ros-(noetic|jazzy)/{print $2, $3}'
} > "$TMP_INV"

ULTIMO="$(ls -1t "$DEST"/estado_sistema_*.txt 2>/dev/null | head -1 || true)"
if [[ -n "$ULTIMO" ]] && diff -q <(tail -n +2 "$ULTIMO") "$TMP_INV" >/dev/null 2>&1; then
    salta_inv="$(basename "$ULTIMO")"
    ok "el inventario no ha cambiado desde $salta_inv — no se duplica"
    rm -f "$TMP_INV"
else
    { echo "# Estado del sistema justo antes del respaldo — $STAMP"; cat "$TMP_INV"; } \
        > "$DEST/estado_sistema_${STAMP}.txt"
    rm -f "$TMP_INV"
    ok "inventario del sistema → estado_sistema_${STAMP}.txt"
fi

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
