#!/usr/bin/env bash
# medir_partof.sh — ¿`PartOf=` devuelve la unidad atada, o solo lo parecía?
#
# POR QUÉ EXISTE
# ─────────────
# El 2026-08-06 (noche), al añadir el timestamp a M10, salió algo que contradice
# lo que este proyecto tiene escrito desde el mismo día:
#
#   documentado:  «`PartOf=` deja la unidad viva y MUDA, que es peor que morir»
#   medido:       tras MATAR el proceso base, la atada quedó `active`
#                 CON TIMESTAMP NUEVO (23:44:13 -> 23:44:23)
#
# Timestamp nuevo = proceso nuevo. O sea que NO sobrevivió muda: se reinició
# limpia. Con `is-active` a secas los dos casos se escriben igual, y por eso la
# tabla anterior no podía distinguirlos.
#
# 🔴 SI ESTO SE SOSTIENE, EL DISEÑO SE SIMPLIFICA A LA MITAD: `PartOf=` haría el
#    mismo trabajo que `BindsTo=` + `Upholds=` con DOS UNIDADES MENOS, y se
#    llevaría por delante la fricción más fea —que `systemctl stop atriz-slam`
#    no funcione mientras el deseo esté puesto—.
#
# QUÉ CORRIGE DE LA MEDICIÓN ANTERIOR
# ───────────────────────────────────
# 🔴 Aquella hacía un `systemctl start` de la atada ENTRE el caso 1 y el caso 2,
#    para dejarla arriba. Eso pone un timestamp nuevo por sí solo, así que el
#    del caso 1 NO discrimina nada. Aquí se mide SOLO el caso que decide —matar
#    el proceso, que es lo que pasó de verdad— y sin ningún `start` intermedio.
# 🔴 Y era n=1 por rama. Aquí son TRES vueltas.
#
# Además se registra el PID, que es el testigo más directo: un PID distinto es
# un proceso distinto, sin depender de cómo systemd rellene el timestamp.
#
# ⚠️ NO toca el robot, NO toca el RVR, NO mueve nada. Tres unidades de JUGUETE
#    que se borran al terminar. Dura ~2 min.
#
# Uso:   sudo bash ~/atriz_migracion/scripts/medir_partof.sh

set -euo pipefail

SALIDA="${1:-$HOME/medicion_partof_$(date +%Y%m%d_%H%M%S).txt}"
exec > >(tee "$SALIDA") 2>&1

VUELTAS=3

echo "═══════════════════════════════════════════════════════════════════"
echo " medir_partof.sh   ·   $(date -Is)   ·   $(hostname)"
echo " systemd: $(systemctl --version | head -1)"
echo "═══════════════════════════════════════════════════════════════════"

limpiar() {
  systemctl stop juguete-deseo.service    2>/dev/null || true
  systemctl stop juguete-atada.service    2>/dev/null || true
  systemctl stop juguete-base.service     2>/dev/null || true
  systemctl reset-failed juguete-deseo.service juguete-atada.service \
                         juguete-base.service 2>/dev/null || true
  rm -f /etc/systemd/system/juguete-{base,atada,deseo}.service
  systemctl daemon-reload
}
# Pase lo que pase, no se dejan unidades sueltas.
trap limpiar EXIT

escribir_base() {
  cat > /etc/systemd/system/juguete-base.service <<'UNIDAD'
[Unit]
Description=juguete base (imita atriz-robot)
[Service]
ExecStart=/bin/sleep infinity
Restart=always
RestartSec=1
UNIDAD
}

# $1 = bindsto-upholds | partof-requires | partof-solo
escribir_atada() {
  {
    echo "[Unit]"
    echo "Description=juguete atada"
    case "$1" in
      bindsto-upholds) echo "BindsTo=juguete-base.service" ;;
      partof-requires) echo "PartOf=juguete-base.service"; echo "Requires=juguete-base.service" ;;
      partof-solo)     echo "PartOf=juguete-base.service" ;;
    esac
    echo "After=juguete-base.service"
    echo "[Service]"
    echo "ExecStart=/bin/sleep infinity"
    echo "Restart=on-failure"
  } > /etc/systemd/system/juguete-atada.service

  if [[ "$1" == "bindsto-upholds" ]]; then
    cat > /etc/systemd/system/juguete-deseo.service <<'UNIDAD'
[Unit]
Description=juguete deseo
Upholds=juguete-atada.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/true
ExecStop=/usr/bin/systemctl stop juguete-atada.service
UNIDAD
  else
    rm -f /etc/systemd/system/juguete-deseo.service
  fi
  systemctl daemon-reload
}

# El testigo: PID y timestamp juntos. El PID es el más directo — un PID distinto
# es un proceso distinto, sin depender de cómo systemd rellene el timestamp.
huella() {
  local est pid ts
  est="$(systemctl is-active juguete-atada 2>/dev/null || true)"
  pid="$(systemctl show juguete-atada -p MainPID --value 2>/dev/null || echo '?')"
  ts="$(systemctl show juguete-atada -p ExecMainStartTimestamp --value 2>/dev/null || true)"
  printf '%-9s PID=%-7s %s' "$est" "$pid" "${ts:-—}"
}

probar() {
  local modo="$1" v
  echo
  echo "┌── $modo ────────────────────────────────────────────────"
  for v in $(seq 1 "$VUELTAS"); do
    limpiar >/dev/null 2>&1 || true
    escribir_base
    escribir_atada "$modo"

    systemctl start juguete-base.service
    sleep 1
    if [[ "$modo" == "bindsto-upholds" ]]; then
      systemctl start juguete-deseo.service     # el deseo levanta la atada
    else
      systemctl start juguete-atada.service
    fi
    sleep 3

    local antes despues pid_antes pid_despues
    antes="$(huella)"
    pid_antes="$(systemctl show juguete-atada -p MainPID --value)"

    # ── EL ÚNICO SUCESO. Sin `start` intermedio que ensucie la medida. ────────
    # Es lo que pasó de verdad: el proceso base MURIÓ y `Restart=always` lo
    # repuso. NO es un `systemctl restart`, que es un job explícito y se
    # propaga por otro camino.
    local pid_base
    pid_base="$(systemctl show juguete-base -p MainPID --value)"
    # 🔴 `if` explícito, NO `[[ … ]] && kill`. Con `set -e`, un `&&` cuya
    #    condición sale falsa devuelve 1 y aborta el guion — es la misma trampa
    #    que el `(( t++ ))` de `atriz-robot.sh`, que desactivó la salvaguarda
    #    escrita para evitar justo el fallo que luego ocurrió.
    if [[ "$pid_base" != "0" ]]; then
      kill -9 "$pid_base"
    else
      echo "│    ⚠️ la base no tenía proceso: esta vuelta no mide nada"
    fi
    sleep 8

    despues="$(huella)"
    pid_despues="$(systemctl show juguete-atada -p MainPID --value)"

    printf '│  vuelta %s\n' "$v"
    printf '│    antes   %s\n' "$antes"
    printf '│    después %s\n' "$despues"

    # El veredicto por EFECTO, no por lo que parezca:
    if [[ "$(systemctl is-active juguete-atada 2>/dev/null)" != "active" ]]; then
      printf '│    → 🔴 NO VOLVIÓ\n'
    elif [[ "$pid_despues" != "$pid_antes" && "$pid_despues" != "0" ]]; then
      printf '│    → ✅ VOLVIÓ con proceso NUEVO (%s → %s)\n' "$pid_antes" "$pid_despues"
    else
      printf '│    → ⚠️ activa con el MISMO PID: sobrevivió, no se reinició\n'
    fi
  done
  echo "└──"
}

probar partof-requires
probar partof-solo
probar bindsto-upholds     # control: ya se sabe que este vuelve

echo
echo "── cómo se lee ────────────────────────────────────────────────────"
cat <<'LEER'
  El PID manda sobre el timestamp: un PID distinto es un proceso distinto.

    NO VOLVIÓ          -> la navegación se queda muerta. Es el caso que este
                          diseño existe para evitar.
    proceso NUEVO      -> volvió LIMPIO, con búfer TF nuevo. Es lo que se busca.
    MISMO PID          -> sobrevivió sin reiniciarse. 🔴 Es la trampa del
                          slam_toolbox vivo y MUDO: `active` sin estar
                          funcionando.

  Si `partof-requires` da «proceso NUEVO» las TRES vueltas, hace el mismo
  trabajo que `bindsto-upholds` con DOS UNIDADES MENOS, y sin la fricción de
  que `systemctl stop` no funcione.

  Si alguna vuelta da «MISMO PID», la creencia documentada era la buena y hay
  que quedarse con `BindsTo=` + `Upholds=`.
LEER
echo
echo "═══ fin · salida en $SALIDA ═══"
