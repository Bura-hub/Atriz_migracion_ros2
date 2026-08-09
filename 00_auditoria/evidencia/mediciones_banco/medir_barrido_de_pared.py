#!/usr/bin/env python3
"""¿A qué distancia de una pared vuelve a moverse el robot, y depende del lado?

    python3 medir_barrido_de_pared.py <DETRAS|DELANTE|IZQUIERDA|DERECHA> <hueco_cm>

    <hueco_cm> = lo que mide la CINTA entre el borde del robot y la pared.
                 0 = tocando.

🔴 MUEVE EL ROBOT: tres órdenes cortas. Requiere a alguien mirando.
✅ Manda por `/cmd_vel_raw`, o sea CON el collision_monitor en el lazo: es
   exactamente lo que hará un alumno o la web.

═══════════════════════════════════════════════════════════════════════════════
QUÉ CONTESTA
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-09 (evidencia 93) se midió que con la pared DETRÁS a 16,8 cm el robot
no gira, no avanza y **ni siquiera puede alejarse**. Pero el manual afirmaba lo
contrario con tres casos, y la evidencia 19 anotó «PUDO SALIR» con el obstáculo
**al lado**. Las dos cosas no pueden ser ciertas a la vez.

🔎 **Este banco recorre la curva entera en vez de discutir puntos sueltos:** el
   usuario coloca el robot tocando la pared y lo va separando de 2 en 2 cm, en las
   CUATRO direcciones, y en cada estación se prueban las tres órdenes.

📌 **Lo mueve SIEMPRE el usuario, también de frente y de atrás donde el robot
   podría separarse solo.** Es más lento, y es a propósito: hoy tres
   comparaciones se han arruinado por una variable sin controlar, y cambiar de
   método entre direcciones sería una más.

═══════════════════════════════════════════════════════════════════════════════
LO QUE HAY QUE SABER PARA LEER LAS PRIMERAS ESTACIONES
═══════════════════════════════════════════════════════════════════════════════
⚠️ **Por debajo de 10 cm DESDE EL EJE DEL LIDAR el obstáculo es INVISIBLE**
   (`range_min: 0.1`). Tocando por detrás son 9,0 cm, así que el sensor NO ve la
   pared — pero sí ve rayos oblicuos recortados en 10,02 cm, y el 2026-08-09 se
   comprobó que **con uno basta para que el monitor congele al robot**.

   Por eso se registran las dos cosas y no se mezclan:
     · `hueco_cm`  -> LA CINTA DEL USUARIO. Es el dato bueno cerca de la pared.
     · `lidar_cm`  -> lo que ve el sensor, que es lo que ve el monitor.

   Del eje del LIDAR al borde: **9,0 cm detrás** (validado con dos instrumentos)
   y **10,8 a cada costado**. ⏳ El delantero está en conflicto —cinta 9,0 contra
   URDF 10,0— así que en DELANTE la conversión se marca como incierta.

Los resultados se acumulan en `barrido_pared.csv`, al lado de este fichero.
"""
import argparse
import csv
import math
import os
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from nav2_msgs.msg import CollisionMonitorState

DIRECCIONES = ('DETRAS', 'DELANTE', 'IZQUIERDA', 'DERECHA')
# Del eje del LIDAR al borde del robot, por sentido. Medido con cinta 2026-08-09.
BORDE = {'DETRAS': 0.090, 'DELANTE': 0.090, 'IZQUIERDA': 0.108, 'DERECHA': 0.108}
CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'barrido_pared.csv')

p = argparse.ArgumentParser()
p.add_argument('direccion', choices=DIRECCIONES)
p.add_argument('hueco_cm', type=float, help='cinta: borde del robot -> pared. 0 = tocando')
p.add_argument('--minimo-seguro', type=float, default=0.105,
               help='m: si el LIDAR ve algo más cerca, se aborta la orden')
a = p.parse_args()

QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)
ACC = {0: '-', 1: 'PARADA', 2: 'FRENADO', 3: 'APROX', 4: 'LIMITE'}

rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
n = Node('barrido_pared')
odom, esc, est = {}, {}, []


def cb_odom(m):
    q = m.pose.pose.orientation
    y = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))
    if odom:
        d = y - odom['yaw']
        odom['acum'] = odom.get('acum', 0.0) + abs(math.atan2(math.sin(d),
                                                              math.cos(d)))
    odom.update(x=m.pose.pose.position.x, y=m.pose.pose.position.y, yaw=y)


def cb_scan(m):
    """Distancia mínima global y en el sector donde está la pared."""
    sector = {'DELANTE': (-25, 25), 'DETRAS': (155, 205),
              'IZQUIERDA': (65, 115), 'DERECHA': (-115, -65)}[a.direccion]
    mejor, mejor_sec = 9.9, 9.9
    for i, r in enumerate(m.ranges):
        if not (m.range_min < r < m.range_max) or math.isinf(r) or math.isnan(r):
            continue
        mejor = min(mejor, r)
        ang = math.degrees(m.angle_min + i * m.angle_increment) % 360
        lo, hi = sector[0] % 360, sector[1] % 360
        dentro = (lo <= ang <= hi) if lo <= hi else (ang >= lo or ang <= hi)
        if dentro:
            mejor_sec = min(mejor_sec, r)
    esc.update(min=mejor, sector=(mejor_sec if mejor_sec < 9.9 else None),
               recortado=abs(mejor - 0.1002) < 0.0008)


n.create_subscription(Odometry, '/odom', cb_odom, QT)
n.create_subscription(LaserScan, '/scan', cb_scan, QT)
n.create_subscription(CollisionMonitorState, '/collision_monitor_state',
                      lambda m: est.append(ACC.get(m.action_type, m.action_type)), 10)
pub = n.create_publisher(Twist, '/cmd_vel_raw', 10)


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.01)


def orden(lin, ang, seg):
    bombear(1.5)
    est.clear()
    x0, y0 = odom['x'], odom['y']
    odom['acum'] = 0.0
    tw = Twist(); tw.linear.x = lin; tw.angular.z = ang
    t0 = time.time(); cortado = False
    while time.time() - t0 < seg:
        if esc.get('min', 9) < a.minimo_seguro and not esc.get('recortado'):
            cortado = True
            break
        pub.publish(tw)
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.05)
    tw.linear.x = 0.0; tw.angular.z = 0.0
    for _ in range(25):
        pub.publish(tw); time.sleep(0.02)
    bombear(1.5)
    return (math.hypot(odom['x'] - x0, odom['y'] - y0) * 100,
            math.degrees(odom.get('acum', 0.0)),
            ','.join(sorted({e for e in est if e != '-'})) or 'no actuó',
            cortado)


print('=' * 78)
print(f' BARRIDO DE PARED · {a.direccion} · hueco de cinta {a.hueco_cm:.0f} cm')
print(' 🔴 EL ROBOT SE MUEVE. Con collision_monitor en el lazo (/cmd_vel_raw).')
print('=' * 78)

bombear(4)
if 'min' not in esc or 'yaw' not in odom:
    print('  🔴 falta /scan o /odom'); raise SystemExit(1)

esperado = a.hueco_cm / 100.0 + BORDE[a.direccion]
lid = esc.get('sector')
print(f'  cinta: {a.hueco_cm:.0f} cm de hueco  ->  esperado en el LIDAR '
      f'{esperado*100:.1f} cm (borde {BORDE[a.direccion]*100:.1f})'
      + ('   ⏳ el borde DELANTERO está en conflicto: cinta 9,0 vs URDF 10,0'
         if a.direccion == 'DELANTE' else ''))
if lid is None:
    print(f'  LIDAR en ese sector: NADA. El obstáculo está por debajo de '
          f'range_min (10 cm): INVISIBLE para el monitor por ese lado.')
else:
    print(f'  LIDAR en ese sector: {lid*100:.1f} cm'
          + ('   ⚠️ RECORTADO en range_min: es un suelo, no una medida'
             if abs(lid - 0.1002) < 0.0008 else
             f'   (diferencia con lo esperado {lid*100-esperado*100:+.1f} cm)'))
print(f'  lo más cercano en TODO el barrido: {esc["min"]*100:.1f} cm'
      + ('   ⚠️ recortado' if esc.get('recortado') else ''))
print()

# «alejarse» sólo existe si la pared está delante o detrás: en diferencial no hay
# movimiento lateral, así que en los costados las dos lineales van PARALELAS.
if a.direccion == 'DETRAS':
    pruebas = [('GIRAR', 0.0, 0.6, 2.5), ('ALEJARSE (avanza)', 0.10, 0.0, 1.5),
               ('ACERCARSE (retrocede)', -0.08, 0.0, 1.0)]
elif a.direccion == 'DELANTE':
    pruebas = [('GIRAR', 0.0, 0.6, 2.5), ('ALEJARSE (retrocede)', -0.10, 0.0, 1.5),
               ('ACERCARSE (avanza)', 0.08, 0.0, 1.0)]
else:
    pruebas = [('GIRAR', 0.0, 0.6, 2.5), ('PARALELO adelante', 0.10, 0.0, 1.5),
               ('PARALELO atrás', -0.10, 0.0, 1.5)]

filas = []
for etq, lin, ang, seg in pruebas:
    cm, deg, acc, cortado = orden(lin, ang, seg)
    movio = 'SÍ' if (cm > 1.0 or deg > 3.0) else '🔴 NO'
    print(f'  {etq:24s} -> {cm:5.1f} cm · {deg:6.1f}°  ·  {movio:6s} ·  '
          f'monitor: {acc}' + ('  [cortado por la guardia]' if cortado else ''))
    filas.append((etq, round(cm, 1), round(deg, 1), movio, acc))

nuevo = not os.path.exists(CSV)
with open(CSV, 'a', newline='') as f:
    w = csv.writer(f)
    if nuevo:
        w.writerow(['fecha', 'direccion', 'hueco_cinta_cm', 'lidar_sector_cm',
                    'lidar_recortado', 'orden', 'cm', 'grados', 'se_movio', 'monitor'])
    for etq, cm, deg, movio, acc in filas:
        w.writerow([time.strftime('%Y-%m-%dT%H:%M:%S'), a.direccion, a.hueco_cm,
                    ('' if lid is None else round(lid * 100, 1)),
                    int(bool(esc.get('recortado'))), etq, cm, deg, movio, acc])
print(f'\n  anotado en {os.path.basename(CSV)}')
print('=' * 78)
