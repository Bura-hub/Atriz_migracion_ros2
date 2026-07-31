#!/usr/bin/env python3
"""Repite la prueba de SLAM N veces y da la DISTRIBUCIÓN de la deriva.

    ros2 launch atriz_rvr_bringup robot.launch.py     # dejar corriendo
    python3 caracterizar_deriva_slam.py

⚠️  MUEVE EL ROBOT durante ~20 min. Necesita un pasillo despejado; ver abajo.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════

Al cerrar la Fase 4 quedaron **dos medidas de deriva que se contradicen**, tomadas
el mismo día con el mismo binario:

    corrida 1 (2.62 m de recorrido)  ->  87.8 cm y 10.9° de error al volver
    corrida 2 (1.78 m de recorrido)  ->   0.9 cm y  3.1°

Dos órdenes de magnitud. Y diferían en **dos cosas a la vez**: la distancia
recorrida y que en la primera el robot rozó obstáculos. Con dos variables
cambiando no se puede atribuir la causa a ninguna — es la regla nº4 del proyecto
(mide antes de atribuir), y con dos puntos sueltos era imposible cumplirla.

Esta herramienta convierte esos dos puntos en una **distribución**:

  · Repite la misma prueba N veces en el MISMO sitio.
  · Alterna DOS distancias, para ver si la deriva escala con el recorrido.
  · **Reinicia `slam_toolbox` de cero en cada repetición**, para que ninguna
    herede el mapa de la anterior. Sin esto las últimas corridas parten con
    ventaja y la comparación no vale.
  · Deja el robot volviendo siempre al mismo punto de partida.

Lo que NO controla, y hay que controlar a mano: que **nadie cruce la zona**. El
LIDAR ve piernas a 17.5 cm perfectamente, y una persona pasando mete un obstáculo
móvil que el emparejado no puede reconciliar. Es una de las sospechas de por qué
la corrida 1 salió tan mal.

═══════════════════════════════════════════════════════════════════════════════
ESPACIO NECESARIO
═══════════════════════════════════════════════════════════════════════════════

Pasillo despejado. Lo que hace falta es **espacio POR DELANTE**:

    |<──────────────── 3 m ────────────────>|
    ┌───────────────────────────────────────┐
    │              ┌─────┐                  │ 0.8 m
    │              │ RVR │ →                │ de ancho
    │              └──┬──┘                  │
    └───────────────────────────────────────┘
                  EL CENTRO

🔴 CORREGIDO 2026-07-31: aquí ponía «el robot en el CENTRO, porque avanza y
retrocede la misma distancia». Es impreciso. El patrón real es **giro 360° →
avanza N tramos → retrocede los mismos N y vuelve al punto de partida**: NO pasa
por detrás del inicio. Lo que hace falta es:

  · POR DELANTE:  N × PASO_M + 0.091 (medio robot) + margen
                  con la corrida larga: 1.20 + 0.091 = **1.29 m mínimo**
  · ALREDEDOR:    0.142 m (radio circunscrito) para el giro de 360°
  · POR DETRÁS:   solo para que el retorno no se pase de largo

Centrarlo es una recomendación segura, no un requisito. Un robot pegado al fondo
del pasillo y mirando hacia el otro extremo cumple igual.

🔴 **El robot NO esquiva obstáculos.** Solo tiene el watchdog de `cmd_vel`, que
para los motores si dejan de llegar órdenes, no si hay algo delante. Nada a menos
de 60 cm. Y el LIDAR barre en horizontal a 15.5 cm: pasa por encima de zócalos y
por debajo de mesas, así que «despejado a ras de suelo» no basta.
═══════════════════════════════════════════════════════════════════════════════

🔴 ARRÁNCALO CON LA CAPA DE SEGURIDAD DESACTIVADA:

    ros2 launch atriz_rvr_bringup robot.launch.py collision_monitor:=false

Esta herramienta es ANTERIOR al `collision_monitor` y publica en `/cmd_vel`
directamente, así que con el monitor activo **saltaría la seguridad en silencio**
— justo el fallo contra el que avisa `collision_monitor.yaml`. Desactivarlo lo
hace explícito.

Y además conviene para la medida: con el monitor en el lazo, `approach` frenaría
al acercarse a los extremos del pasillo y metería una variable de más en un
experimento que compara derivas.

⚠️ Con el monitor desactivado el robot **no esquiva nada**: solo queda el watchdog
   de `cmd_vel`. De ahí la insistencia en el espacio despejado.
"""
from __future__ import annotations

import argparse
import math
import re
import statistics
import os
import subprocess
import sys
import time

#: Las dos distancias de ida, en tramos de `PASO_M`. Con 3 m de pasillo y el
#: robot en el centro, la larga usa 1.20 + 0.11 = 1.31 m a cada lado: quedan
#: ~19 cm de margen, que es lo que hace falta porque el robot vuelve
#: APROXIMADAMENTE al punto de partida, no exactamente.
PASO_M = 0.40
PASOS_CORTO = 2      # 0.80 m de ida
PASOS_LARGO = 3      # 1.20 m de ida

#: 🔴 Distancia perpendicular a la pared frontal a la que se devuelve el robot
#: ANTES DE CADA CORRIDA. Sin esto las N corridas NO son repeticiones: medido el
#: 2026-07-31, el robot derivaba ~8 cm por corrida y 94 cm en doce (manual, 9.12b).
#: Con 2.05 m quedan 0.76 m de margen sobre los 1.29 que necesita la corrida larga.
DISTANCIA_ORIGEN_M = 2.05

RE_DERIVA = re.compile(r'se desplazó ([\d.]+) cm y giró ([\d.]+)°')
RE_CELDAS = re.compile(r'celdas conocidas: (\d+) -> (\d+)')
RE_RECORRIDO = re.compile(r'recorrido real:\s+([\d.]+) cm')


def slam_vivo() -> bool:
    r = subprocess.run(['ros2', 'lifecycle', 'get', '/slam_toolbox'],
                       capture_output=True, text=True, timeout=15)
    return r.stdout.strip().startswith('active')


def reiniciar_slam() -> bool:
    """Mata slam_toolbox y lo arranca de cero. Devuelve True si quedó `active`.

    🔴 El patrón de `pgrep` NO puede aparecer en la línea de comandos de este
    proceso. Un script anterior buscaba `slam_toolbox` a secas y se mató a sí
    mismo al recibir como argumento la ruta
    `/opt/ros/jazzy/share/slam_toolbox/config/...`. El truco del `[s]` protege de
    que pgrep case su propio patrón, NO de una ruta que lo contenga.
    """
    subprocess.run(
        ['bash', '-c',
         'for p in $(pgrep -f "lib/slam_toolbox/async_slam_toolbox_node|slam\\.launch\\.py" 2>/dev/null); do '
         '[ "$p" = "$$" ] || kill -INT $p 2>/dev/null; done'],
        capture_output=True, timeout=20)
    for _ in range(15):
        r = subprocess.run(['pgrep', '-f', 'lib/slam_toolbox/async_slam_toolbox_node'],
                           capture_output=True)
        if r.returncode != 0:
            break
        time.sleep(1)

    subprocess.Popen(
        ['bash', '-c',
         'source /opt/ros/jazzy/setup.bash && source ~/atriz_ws/install/setup.bash && '
         'exec ros2 launch atriz_rvr_bringup slam.launch.py'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    for _ in range(40):
        time.sleep(2)
        try:
            if slam_vivo():
                time.sleep(5)      # que llene su buffer TF antes de mover nada
                return True
        except Exception:
            pass
    return False


def referenciar() -> bool:
    """Devuelve el robot al origen ANTES de la corrida. Ver 9.12b del manual.

    🔴 Va ANTES de reiniciar slam_toolbox, no después: si se moviera el robot con
    SLAM ya arrancado, ese movimiento entraría en el mapa y en la medida.
    """
    r = subprocess.run(
        [sys.executable, 'referenciar_posicion.py',
         '--distancia', str(DISTANCIA_ORIGEN_M)],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
        timeout=300)
    for l in r.stdout.splitlines():
        if 'ANTES' in l or 'DESPUÉS' in l or '🔴' in l or '⚠️' in l:
            print('   ' + l.strip(), flush=True)
    return '🔴' not in r.stdout


def una_corrida(pasos: int, etiqueta: str) -> dict | None:
    """Lanza medir_slam_ros2.py y extrae los números de su salida."""
    print(f"\n{'─' * 74}\n▶ {etiqueta}  ({pasos} tramos de {PASO_M:.2f} m = "
          f"{pasos * PASO_M:.2f} m de ida)\n{'─' * 74}", flush=True)
    if not referenciar():
        print("  🔴 no se pudo referenciar la posición. Se salta esta repetición.")
        return None
    if not reiniciar_slam():
        print("  🔴 slam_toolbox no llegó a `active`. Se salta esta repetición.")
        return None

    r = subprocess.run(
        [sys.executable, 'medir_slam_ros2.py',
         '--pasos', str(pasos), '--paso-m', str(PASO_M)],
        capture_output=True, text=True, timeout=420)
    salida = r.stdout

    m_d = RE_DERIVA.search(salida)
    m_c = RE_CELDAS.search(salida)
    m_r = RE_RECORRIDO.search(salida)
    if not (m_d and m_c and m_r):
        print("  🔴 no se pudieron extraer los números. Salida cruda:")
        print('\n'.join('    ' + l for l in salida.splitlines()[-15:]))
        return None

    d = {
        'etiqueta': etiqueta,
        'pasos': pasos,
        'recorrido_cm': float(m_r.group(1)),
        'deriva_cm': float(m_d.group(1)),
        'deriva_deg': float(m_d.group(2)),
        'celdas_ini': int(m_c.group(1)),
        'celdas_fin': int(m_c.group(2)),
    }
    print(f"  recorrido {d['recorrido_cm']:6.1f} cm  ·  "
          f"deriva {d['deriva_cm']:6.1f} cm y {d['deriva_deg']:5.1f}°  ·  "
          f"mapa {d['celdas_ini']} -> {d['celdas_fin']}", flush=True)
    return d


def resumen(nombre: str, datos: list[dict]) -> None:
    if not datos:
        print(f"  {nombre}: sin datos")
        return
    cm = [d['deriva_cm'] for d in datos]
    dg = [d['deriva_deg'] for d in datos]
    rec = statistics.mean(d['recorrido_cm'] for d in datos)
    print(f"  {nombre}  (n={len(cm)}, recorrido medio {rec:.0f} cm)")
    print(f"    deriva en cm    min {min(cm):6.1f}  mediana {statistics.median(cm):6.1f}  max {max(cm):6.1f}")
    print(f"    deriva en grados min {min(dg):5.1f}  mediana {statistics.median(dg):5.1f}  max {max(dg):5.1f}")
    if len(cm) > 1:
        print(f"    desviación típica: {statistics.stdev(cm):.1f} cm")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repeticiones', type=int, default=3,
                    help='Repeticiones de CADA distancia (por defecto 3 -> 6 corridas).')
    args = ap.parse_args()

    print("═" * 74)
    print("CARACTERIZAR LA DERIVA DE SLAM")
    print("═" * 74)
    print(f"{args.repeticiones} repeticiones de cada distancia, alternando, con")
    print("slam_toolbox reiniciado de cero en cada una.")
    print("⚠️  El robot se mueve. Que no cruce nadie la zona.\n")

    cortos: list[dict] = []
    largos: list[dict] = []
    try:
        for i in range(1, args.repeticiones + 1):
            d = una_corrida(PASOS_CORTO, f"CORTA {i}/{args.repeticiones}")
            if d:
                cortos.append(d)
            d = una_corrida(PASOS_LARGO, f"LARGA {i}/{args.repeticiones}")
            if d:
                largos.append(d)
    except KeyboardInterrupt:
        print("\n⚠️  abortado por el usuario")

    print("\n" + "═" * 74)
    print("DISTRIBUCIÓN DE LA DERIVA")
    print("═" * 74)
    resumen("CORTA", cortos)
    print()
    resumen("LARGA", largos)

    print("\n── todas las corridas ──")
    for d in cortos + largos:
        print(f"  {d['etiqueta']:12s} {d['recorrido_cm']:6.1f} cm -> "
              f"{d['deriva_cm']:6.1f} cm, {d['deriva_deg']:5.1f}°  "
              f"(mapa +{d['celdas_fin'] - d['celdas_ini']})")

    print("\n── qué concluir ──")
    if len(cortos) > 1 and len(largos) > 1:
        mc, ml = statistics.median(d['deriva_cm'] for d in cortos), \
                 statistics.median(d['deriva_cm'] for d in largos)
        print(f"  mediana CORTA {mc:.1f} cm  ·  mediana LARGA {ml:.1f} cm")
        if ml > 3 * mc:
            print("  -> la deriva CRECE con la distancia. La corrida mala de la Fase 4")
            print("     se explica por el recorrido, no (solo) por los obstáculos.")
        elif max(d['deriva_cm'] for d in cortos + largos) > 20:
            print("  -> hay corridas malas SIN relación clara con la distancia:")
            print("     la deriva es ERRÁTICA. Sospecha de la inclinación de ~8° o de")
            print("     obstáculos móviles, y aísla una cosa cada vez.")
        else:
            print("  -> la deriva es PEQUEÑA y ESTABLE en las dos distancias.")
            print("     Los 87.8 cm de la Fase 4 fueron una anomalía, muy probablemente")
            print("     por rozar obstáculos. Repítelo antes de darlo por cerrado.")
    else:
        print("  Faltan corridas para concluir nada. Vuelve a lanzarlo.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
