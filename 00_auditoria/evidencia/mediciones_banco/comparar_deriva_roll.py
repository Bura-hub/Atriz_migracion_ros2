#!/usr/bin/env python3
"""¿El roll falso de la IMU contribuye a la deriva de SLAM? Mídelo.

    # NO arranques el robot: este script lo lanza y lo para él mismo,
    # porque tiene que cambiar `publicar_inclinacion` entre bloques.
    python3 comparar_deriva_roll.py                # 3 bloques por condición
    python3 comparar_deriva_roll.py --bloques 2    # más corto

⚠️ MUEVE EL ROBOT durante ~45 min. Que no cruce nadie.

═══════════════════════════════════════════════════════════════════════════════
LA PREGUNTA
═══════════════════════════════════════════════════════════════════════════════
El driver publica el roll y el pitch que reporta la IMU del RVR: ~8°. El
2026-07-31 se midió con una regla que el robot está HORIZONTAL (manual, cap. 13),
así que ese roll es un desvío del sensor.

Un roll en `odom -> base_footprint` **inclina el plano del láser** y comprime los
alcances por `cos(8°) = 0.990` — un 1 %, ~1 cm por metro. La deriva de SLAM
medida es de 1-3 cm: **el orden de magnitud coincide**.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ ALTERNA LAS CONDICIONES
═══════════════════════════════════════════════════════════════════════════════
No hace 6 corridas con roll y luego 6 sin él, sino bloques cortos alternando:

    A(roll)  B(plano)  A  B  A  B

Dos razones, y las dos vienen de errores que este proyecto ya ha pagado:

  1. **Si la batería corta a mitad, los datos siguen BALANCEADOS.** Con 6 y 6,
     un corte deja una condición completa y la otra vacía: sin comparación.
  2. **El nivel de batería y el calentamiento dejan de poder colarse como
     variable.** Es exactamente la confusión que obligó a retractar la medida de
     velocidad lineal (fichero 16): dos cosas cambiando a la vez.

Cada bloque relanza el driver con `publicar_inclinacion` en true o false, porque
es un parámetro de arranque.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ NO SE PUEDE RECORTAR
═══════════════════════════════════════════════════════════════════════════════
    efecto buscado        ~1 cm
    dispersión ya medida  σ = 0.6-1.0 cm   (fichero 14)

Con 2 corridas por condición el resultado sale dentro del ruido: se gasta la
batería para acabar en «no concluyente». Hacen falta ≥3 repeticiones de cada
distancia por condición.

📝 Y la línea base del fichero 14 NO sirve: se tomó con `laser_z = 0.1745`, y el
   desplazamiento lateral que induce el roll escala con esa altura (2.4 cm
   entonces, 2.2 ahora). Por eso se rehacen las dos mitades.

═══════════════════════════════════════════════════════════════════════════════
Los resultados se guardan **según van saliendo** en un `.jsonl`, así que un corte
por batería no pierde lo ya medido.
"""
import argparse
import json
import re
import math
import shlex
import os
import signal
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))

#: Extrae una corrida de la salida de `caracterizar_deriva_slam.py`.
RE_LINEA = re.compile(
    r'^\s*(CORTA|LARGA)\s+\S+\s+([\d.]+)\s*cm\s*->\s*([\d.]+)\s*cm,\s*([\d.]+)\s*°',
    re.M)

#: Los `comm` (nombre de proceso, 15 caracteres) del stack del robot.
#: Se mata por `comm` y NO con `pgrep -f`: el patrón de `-f` casa con la propia
#: línea de comando de quien lo ejecuta. Ya mató la terminal dos veces.
COMMS = ('rvr_driver_node', 'ydlidar_ros2_dr', 'collision_monit',
         'robot_state_pub', 'lifecycle_manag')


def _pids() -> list[int]:
    r = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True, text=True)
    out = []
    for linea in r.stdout.splitlines()[1:]:
        partes = linea.split(None, 1)
        if len(partes) == 2 and partes[1].strip() in COMMS:
            out.append(int(partes[0]))
    return out


def parar_robot(espera: float = 20.0) -> None:
    for p in _pids():
        try:
            os.kill(p, signal.SIGINT)
        except ProcessLookupError:
            pass
    t0 = time.monotonic()
    while time.monotonic() - t0 < espera and _pids():
        time.sleep(0.5)
    for p in _pids():
        try:
            os.kill(p, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(2.0)


def arrancar_robot(con_roll: bool, espera: float = 45.0) -> bool:
    """Lanza el robot y espera a que /odom publique de verdad.

    🔴 `collision_monitor:=false` a propósito: `medir_slam_ros2.py` publica en
    `/cmd_vel` directamente, así que con el monitor activo saltaría la seguridad
    EN SILENCIO. Y además `approach` frenaría cerca de los extremos del pasillo,
    metiendo una variable de más en un experimento que compara derivas.
    """
    subprocess.Popen(
        ['bash', '-lc',
         'source /opt/ros/jazzy/setup.bash && '
         'source /home/sphero/atriz_ws/install/setup.bash && '
         'exec ros2 launch atriz_rvr_bringup robot.launch.py '
         f'collision_monitor:=false publicar_inclinacion:={"true" if con_roll else "false"}'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    # No basta con que el proceso exista: hay que ver /odom moverse. Una
    # excepción en un manejador deja los topics creados y mudos (manual, 13.5).
    t0 = time.monotonic()
    while time.monotonic() - t0 < espera:
        time.sleep(3.0)
        if _leer(['/odom'], 6.0).get('/odom'):
            return True
    return False


def _leer(topics: list[str], seg: float) -> dict:
    """Lee un mensaje de cada topic con `ros2 topic echo --once`."""
    out = {}
    for t in topics:
        r = subprocess.run(
            ['bash', '-lc',
             'source /opt/ros/jazzy/setup.bash && '
             'source /home/sphero/atriz_ws/install/setup.bash && '
             f'timeout {seg:.0f} ros2 topic echo {t} --once'],
            capture_output=True, text=True)
        out[t] = r.stdout if r.returncode == 0 and r.stdout.strip() else None
    return out


def bateria() -> float | None:
    """Porcentaje 0-100. `/battery_state.percentage` es una FRACCIÓN 0-1."""
    s = _leer(['/battery_state'], 45.0).get('/battery_state')
    if not s:
        return None
    for l in s.splitlines():
        if l.startswith('percentage:'):
            try:
                return float(l.split(':', 1)[1]) * 100.0
            except ValueError:
                return None
    return None


def inclinacion_publicada() -> tuple[float, float, float] | None:
    """(roll, pitch, total) en grados de `/odom`.

    🔴 Devuelve el TOTAL, no solo el roll. La primera versión comprobaba el roll
    a secas y abortó el experimento con un falso positivo: la inclinación de este
    robot vive sobre todo en el PITCH (~6.8°) y el roll estaba en +0.11°.

    Y no es fijo: roll y pitch **se reparten según el rumbo** —medido el
    2026-07-31, giran con el yaw— así que cualquiera de los dos puede pasar por
    cero. Lo único estable es el módulo.
    """
    s = _leer(['/odom'], 20.0).get('/odom')
    if not s:
        return None
    q = {}
    dentro = False
    for l in s.splitlines():
        if l.strip() == 'orientation:':
            dentro = True
            continue
        if dentro:
            for k in ('x', 'y', 'z', 'w'):
                if l.strip().startswith(f'{k}:'):
                    q[k] = float(l.split(':', 1)[1])
            if len(q) == 4:
                break
    if len(q) != 4:
        return None
    roll = math.degrees(math.atan2(2 * (q['w'] * q['x'] + q['y'] * q['z']),
                                   1 - 2 * (q['x'] ** 2 + q['y'] ** 2)))
    sp = 2 * (q['w'] * q['y'] - q['z'] * q['x'])
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, sp))))
    return roll, pitch, math.hypot(roll, pitch)


#: Snippet aislado para leer el entorno. Va en un proceso APARTE a propósito:
#: hacer rclpy.init/shutdown repetidamente dentro de este script, que además
#: lanza y mata el robot doce veces, es pedir problemas.
_SNIPPET_ENTORNO = """
import math, statistics, time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
q = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
               history=HistoryPolicy.KEEP_LAST, depth=5)
rclpy.init(); n = Node('entorno'); acc = {}
def cb(m):
    for i, r in enumerate(m.ranges):
        if not (m.range_min < r < m.range_max) or not math.isfinite(r):
            continue
        a = math.degrees(math.atan2(math.sin(m.angle_min + i*m.angle_increment),
                                    math.cos(m.angle_min + i*m.angle_increment)))
        acc.setdefault(round(a/3)*3, []).append(r)
n.create_subscription(LaserScan, 'scan', cb, q)
t = time.time()
while time.time() - t < 6: rclpy.spin_once(n, timeout_sec=0.1)
pts = {a: statistics.median(v) for a, v in acc.items()}
def sect(c):
    v = [d for a, d in pts.items() if abs(((a-c+180) % 360) - 180) <= 8]
    return statistics.median(v) if v else -1.0
print('ENTORNO %.3f %.3f %.3f %.3f' % (sect(0), sect(180), sect(90), sect(-90)))
n.destroy_node(); rclpy.shutdown()
"""


def entorno() -> dict | None:
    """Dónde está el robot: distancias a lo que tiene en las cuatro direcciones.

    🔴 Existe porque la primera tanda dejó tres fallos catastróficos SIN pista de
    dónde estaba el robot en cada uno. El robot vuelve APROXIMADAMENTE al punto de
    partida, así que su posición real deriva entre corridas — y esa deriva es una
    de las sospechas del fallo bimodal (manual, cap. 9.12a).
    """
    r = subprocess.run(
        ['bash', '-lc',
         'source /opt/ros/jazzy/setup.bash && '
         'source /home/sphero/atriz_ws/install/setup.bash && '
         # 🔴 shlex.quote, NO repr(): repr() escapa los saltos de línea a `\n`
         # literales y Python no puede parsear eso. Devolvía None en silencio.
         'timeout 30 python3 -c ' + shlex.quote(_SNIPPET_ENTORNO)],
        capture_output=True, text=True)
    for l in r.stdout.splitlines():
        if l.startswith('ENTORNO '):
            v = [float(x) for x in l.split()[1:]]
            return {'adelante': v[0], 'atras': v[1], 'izq': v[2], 'der': v[3]}
    return None


def un_bloque(con_roll: bool, etq: str) -> list[dict]:
    """Un bloque = 1 corrida corta + 1 larga, con el driver ya arrancado."""
    r = subprocess.run(
        [sys.executable, 'caracterizar_deriva_slam.py', '--repeticiones', '1'],
        capture_output=True, text=True, cwd=AQUI, timeout=900)
    corridas = []
    # La línea es:  "  CORTA 1/1      82.3 cm ->    1.2 cm,   2.1°  (mapa +412)"
    # 📝 La etiqueta lleva un ESPACIO ("CORTA 1/1"), así que un `split()[1]`
    #    cogería "1/1" y no el recorrido. Por eso va con regex y no troceando.
    for m in RE_LINEA.finditer(r.stdout):
        corridas.append({'bloque': etq, 'con_roll': con_roll,
                         'tipo': m.group(1),
                         'recorrido_cm': float(m.group(2)),
                         'deriva_cm': float(m.group(3)),
                         'deriva_deg': float(m.group(4))})
    if not corridas:
        print('    🔴 no salió ninguna corrida. Últimas líneas:')
        print('\n'.join('      ' + x for x in r.stdout.splitlines()[-12:]))
    return corridas


def resumen(datos: list[dict]) -> None:
    print('\n' + '═' * 74)
    print('COMPARACIÓN')
    print('═' * 74)
    if not datos:
        print('  sin datos')
        return
    for tipo in ('CORTA', 'LARGA'):
        print(f'\n── {tipo} ──')
        for con in (True, False):
            v = [d['deriva_cm'] for d in datos
                 if d['tipo'] == tipo and d['con_roll'] is con]
            nom = 'CON roll (~8°)' if con else 'SIN roll (plano)'
            if not v:
                print(f'  {nom:18s} sin datos')
                continue
            s = f'σ {statistics.stdev(v):.2f}' if len(v) > 1 else 'σ —'
            print(f'  {nom:18s} n={len(v)}  mediana {statistics.median(v):5.2f} cm  '
                  f'{s}   [{", ".join(f"{x:.1f}" for x in v)}]')
        a = [d['deriva_cm'] for d in datos if d['tipo'] == tipo and d['con_roll']]
        b = [d['deriva_cm'] for d in datos if d['tipo'] == tipo and not d['con_roll']]
        if len(a) > 1 and len(b) > 1:
            dif = statistics.median(a) - statistics.median(b)
            sig = max(statistics.stdev(a), statistics.stdev(b))
            print(f'  -> diferencia {dif:+.2f} cm   (σ mayor {sig:.2f})')
            if abs(dif) < sig:
                print('     ⚠️ DENTRO DEL RUIDO: no se puede concluir nada.')
            else:
                print('     ✅ la diferencia supera la dispersión.'
                      f' El roll {"EMPEORA" if dif > 0 else "MEJORA"} la deriva.')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bloques', type=int, default=3,
                    help='Bloques de CADA condición (3 -> 12 corridas, ~45 min).')
    a = ap.parse_args()

    salida = os.path.join(AQUI, 'deriva_roll_resultados.jsonl')
    print('═' * 74)
    print('DERIVA DE SLAM: CON vs SIN el roll de la IMU')
    print('═' * 74)
    print(f'{a.bloques} bloques de cada condición, ALTERNANDO.')
    print(f'Resultados incrementales en {os.path.basename(salida)}')
    print('⚠️  El robot se mueve ~45 min. Que no cruce nadie.\n')

    datos: list[dict] = []
    try:
        for i in range(1, a.bloques + 1):
            for con_roll in (True, False):
                etq = f'{"A" if con_roll else "B"}{i}'
                nom = 'CON roll' if con_roll else 'SIN roll'
                print(f'\n{"━" * 74}\n▶ BLOQUE {etq} — {nom}\n{"━" * 74}', flush=True)
                parar_robot()
                if not arrancar_robot(con_roll):
                    print('  🔴 el robot no llegó a publicar /odom. Se aborta.')
                    return 1
                inc = inclinacion_publicada()
                bat0 = bateria()
                if inc is None:
                    print('  🔴 sin /odom para comprobar la inclinación. Se aborta.')
                    return 1
                print(f'  /odom: roll {inc[0]:+.2f}°  pitch {inc[1]:+.2f}°  '
                      f'TOTAL {inc[2]:.2f}°')
                # El umbral va sobre el TOTAL: roll y pitch se reparten con el
                # rumbo y cualquiera de los dos puede pasar por cero.
                if con_roll and inc[2] < 1.0:
                    print('  🔴 se pidió publicar la inclinación y sale ~0. Se aborta.')
                    return 1
                if not con_roll and inc[2] > 0.2:
                    print(f'  🔴 se pidió inclinación PLANA y sale {inc[2]:.2f}°. Se aborta.')
                    return 1
                print(f'  batería al empezar: {bat0:.0f} %' if bat0 else '  batería: sin dato')
                ent = entorno()
                if ent:
                    print(f'  entorno: adelante {ent["adelante"]:.2f} m · atrás '
                          f'{ent["atras"]:.2f} · izq {ent["izq"]:.2f} · der {ent["der"]:.2f}')
                    if ent['adelante'] < 1.40:
                        print(f'  ⚠️ solo {ent["adelante"]:.2f} m por delante y la corrida '
                              'larga necesita 1.29: el robot ha derivado')

                t0 = time.monotonic()
                nuevas = un_bloque(con_roll, etq)
                mins = (time.monotonic() - t0) / 60.0
                bat1 = bateria()
                for d in nuevas:
                    d['bateria_ini'] = bat0
                    d['bateria_fin'] = bat1
                    d['entorno'] = ent
                    print(f'    {d["tipo"]:6s} recorrido {d["recorrido_cm"]:6.1f} cm '
                          f'-> deriva {d["deriva_cm"]:5.2f} cm, {d["deriva_deg"]:4.1f}°')
                datos += nuevas
                with open(salida, 'a') as f:
                    for d in nuevas:
                        f.write(json.dumps(d) + '\n')
                if bat0 and bat1:
                    print(f'  batería {bat0:.0f} % -> {bat1:.0f} %  '
                          f'({(bat0 - bat1) / mins:.2f} %/min en {mins:.1f} min)')
    except KeyboardInterrupt:
        print('\n⚠️  abortado; lo medido está guardado')
    finally:
        parar_robot()
        print('\n  ✅ robot parado')

    resumen(datos)

    # El consumo, que es un dato que el proyecto no tenía.
    tasas = []
    for d in datos:
        if d.get('bateria_ini') and d.get('bateria_fin'):
            tasas.append(d['bateria_ini'] - d['bateria_fin'])
    if tasas:
        print(f'\n── consumo de batería ──')
        print(f'  caída por bloque: mediana {statistics.median(tasas):.1f} puntos '
              f'({len(tasas)} bloques)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
