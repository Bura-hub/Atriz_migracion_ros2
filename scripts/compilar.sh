#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# compilar.sh — compila el workspace SIN poder equivocarse de directorio
# ═══════════════════════════════════════════════════════════════════════════════
#   bash compilar.sh                          # todo
#   bash compilar.sh atriz_rvr_driver         # solo un paquete
#   bash compilar.sh --limpio atriz_rvr_msgs  # borra build/ e install/ antes
#
# ═══════════════════════════════════════════════════════════════════════════════
# POR QUÉ EXISTE ESTE SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 `colcon build` desde el directorio equivocado dice **«0 packages finished»**
#    y NO compila nada. El mensaje no parece un error, así que lo siguiente que
#    haces es reiniciar el nodo y leer un log del código VIEJO creyendo que es
#    del nuevo.
#
#    Pasó **seis veces el 2026-08-01**, en una sola sesión, después de estar ya
#    documentado en CLAUDE.md. Un aviso que se ignora seis veces no es un aviso:
#    es una tarea pendiente. Por eso ahora es un script.
#
# 🔴 Y CAMBIAR UN `.msg` NO BASTA CON `colcon build`: el fichero instalado se
#    queda con la versión anterior y el suscriptor da `AttributeError` sobre un
#    campo que existe en el fuente. Hace falta borrar `build/` e `install/` del
#    paquete — eso es `--limpio`.
#
# Lo que hace de más que un `colcon build` pelado:
#   · se sitúa SIEMPRE en la raíz del workspace
#   · comprueba que compiló ALGO, y falla si no
#   · avisa si hay un workspace parásito dentro de src/
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

WS=/home/sphero/atriz_ws

LIMPIO=no
if [[ "${1:-}" == "--limpio" ]]; then LIMPIO=si; shift; fi
PAQUETES=("$@")

cd "$WS"     # ← el motivo de todo esto

if [[ $LIMPIO == si ]]; then
    if [[ ${#PAQUETES[@]} -eq 0 ]]; then
        echo "🔴 --limpio necesita al menos un paquete (borrar todo es demasiado)" >&2
        exit 2
    fi
    for p in "${PAQUETES[@]}"; do
        rm -rf "build/$p" "install/$p"
        echo "  borrado build/$p e install/$p"
    done
fi

if [[ ${#PAQUETES[@]} -gt 0 ]]; then
    SALIDA="$(colcon build --packages-select "${PAQUETES[@]}" 2>&1)"
else
    SALIDA="$(colcon build 2>&1)"
fi
echo "$SALIDA" | tail -3

# ── Comprobar el EFECTO, no el mensaje ───────────────────────────────────────
if grep -qE '^Summary: 0 packages finished' <<<"$SALIDA"; then
    echo
    echo "🔴 COMPILÓ 0 PAQUETES. Eso NO es éxito." >&2
    echo "   Suele ser un nombre de paquete mal escrito. Los que hay:" >&2
    ls -1 "$WS/src"/*/ -d 2>/dev/null | xargs -n1 basename | sed 's/^/     /' >&2
    ls -1 "$WS/src"/*/*/package.xml 2>/dev/null | xargs -n1 dirname \
        | xargs -n1 basename | sed 's/^/     /' >&2
    exit 1
fi
if grep -qE 'Failed|Aborted' <<<"$SALIDA"; then
    echo "🔴 la compilación falló; mira el log completo con: colcon build" >&2
    exit 1
fi

# 🔴 Un `build/` dentro de src/ es un workspace parásito: colcon compila ahí y
#    el cambio nunca llega al sistema que se está ejecutando.
if ls -d "$WS"/src/*/build >/dev/null 2>&1; then
    echo "🔴 HAY UN WORKSPACE PARÁSITO en src/. Bórralo:" >&2
    ls -d "$WS"/src/*/build >&2
    exit 1
fi

echo "  ✅ compilado. Para desplegarlo en el robot:"
echo "     kill -INT \$(systemctl show atriz-robot -p MainPID --value)   # vuelve solo en ~30 s"
