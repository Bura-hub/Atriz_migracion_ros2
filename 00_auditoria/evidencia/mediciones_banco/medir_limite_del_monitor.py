#!/usr/bin/env python3
"""¿A qué distancia inmoviliza el `collision_monitor`, y depende de la dirección?

    python3 medir_limite_del_monitor.py <etiqueta>

🔴 MUEVE EL ROBOT: tres órdenes cortas por cada radio probado. Requiere a alguien
   mirando — parte del barrido se hace con el círculo MÁS PEQUEÑO que el actual,
   o sea con MENOS margen de frenado del habitual.

═══════════════════════════════════════════════════════════════════════════════
QUÉ CONTESTA, Y POR QUÉ HACE FALTA
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-09 (evidencia 93) se midió que con la pared **detrás** a 16,8 cm el
robot no gira, no avanza y **ni siquiera puede alejarse**. Pero el manual (cap.
12.5) afirmaba lo contrario con tres casos verificados, uno de ellos «pegado a la
pared, 2,9 cm -> retrocedió 196 cm».

⏳ **Las dos cosas no pueden ser ciertas a la vez, y hay dos variables sin
   controlar entre unas medidas y otras:**
     (a) la DIRECCIÓN del obstáculo respecto al movimiento mandado
     (b) si aquellas distancias se midieron desde el BORDE del robot o desde el
         LIDAR — para un obstáculo delante o detrás son **9 cm** de diferencia,
         y cambian el veredicto

Este banco separa las dos: el usuario coloca el obstáculo en cada lado, y para
cada radio se prueban **las tres órdenes por separado**.

═══════════════════════════════════════════════════════════════════════════════
EL ATAJO, Y POR QUÉ ES LEGÍTIMO
═══════════════════════════════════════════════════════════════════════════════
El monitor actúa cuando hay puntos DENTRO de su círculo, o sea cuando
`distancia < radius`. Con el robot quieto, **barrer el radio equivale a barrer la
distancia**, y se hace por software en segundos en vez de recolocando el robot
centímetro a centímetro.

    distancia efectiva de disparo ≈ radius

📌 La distancia se mide **desde el LIDAR**, que es lo que ve el monitor. Se
   informa también la distancia desde el borde del robot (−9 cm de frente o
   detrás, −10,8 de costado) porque es lo que ve una persona con una cinta, y
   confundir las dos es justo lo que dejó el manual en contradicción.

🔴 SE RESTAURA `Aproximacion.radius` A 0.18 AL TERMINAR, pase lo que pase.
"""
import argparse
import math
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from nav2_msgs.msg import CollisionMonitorState

p = argparse.ArgumentParser()
p.add_argument('etiqueta', help='DETRAS, DELANTE, IZQUIERDA o DERECHA')
p.add_argument('--radios', default='0.20,0.18,0.16,0.14,0.12,0.10')
p.add_argument('--minimo-seguro', type=float, default=0.09,
               help='m: si el LIDAR ve algo más cerca, se aborta la orden')
a = p.parse_args()

RADIO_NORMAL = 0.18
QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)
ACC = {0: '-', 1: 'PARADA', 2: 'FRENADO', 3: 'APROX', 4: 'LIMITE'}

rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
n = Node('limite_monitor')
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
    mejor, ang_mejor = 9.9, 0.0
    for i, r in enumerate(m.ranges):
        if not (m.range_min < r < m.range_max) or math.isinf(r) or math.isnan(r):
            continue
        if r < mejor:
            mejor, ang_mejor = r, m.angle_min + i * m.angle_increment
    esc.update(d=mejor, ang=math.degrees(ang_mejor))


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


def poner_radio(r):
    subprocess.run(['ros2', 'param', 'set', '/collision_monitor',
                    'Aproximacion.radius', str(r)],
                   capture_output=True, timeout=30)
    bombear(2.5)


def orden(lin, ang, seg):
    """Manda una orden corta y devuelve (cm recorridos, grados girados, acciones).

    🔴 Con guardia por LIDAR: si algo entra por debajo de `--minimo-seguro` se
       corta. Parte de este barrido corre con el círculo MÁS PEQUEÑO que el de
       producción, así que la red de seguridad habitual está recortada.
    """
    bombear(1.5)
    est.clear()
    x0, y0 = odom['x'], odom['y']
    odom['acum'] = 0.0
    tw = Twist(); tw.linear.x = lin; tw.angular.z = ang
    t0 = time.time(); cortado = False
    while time.time() - t0 < seg:
        if esc.get('d', 9) < a.minimo_seguro:
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
            sorted({e for e in est if e != '-'}), cortado)


print('=' * 78)
print(f' LÍMITE DEL collision_monitor · obstáculo {a.etiqueta}')
print(' 🔴 MUEVE EL ROBOT. Parte del barrido va con MENOS margen del habitual.')
print('=' * 78)

bombear(4)
if 'd' not in esc or 'yaw' not in odom:
    print('  🔴 falta /scan o /odom'); raise SystemExit(1)

d0, ang0 = esc['d'], esc['ang']
# 🔴 EL BORDE DEL ROBOT, Y ESTO ESTUVO INVERTIDO: el RVR es MÁS ANCHO QUE LARGO.
#    Medido por el usuario con las orugas: frente-atrás 18 cm (media 0.09) y
#    lado-lado 21,6 cm (media 0.108) -> esquina 0.1406. Los 21,8 x 18,5 que
#    rondan por el proyecto son las mismas magnitudes pero CRUZADAS de eje, y
#    del URDF, que venía de la ficha publicada y los tenía CRUZADOS — el fichero
#    19 ya lo avisaba.
#    ✅ Validado el 2026-08-09 con dos instrumentos: cinta 9 cm del eje al borde
#       trasero, y el LIDAR 12,20 cm con el robot 3 cm separado (12,00 esperados).
borde = 0.09 if (abs(ang0) < 45 or abs(ang0) > 135) else 0.108
print(f'  obstáculo más cercano: {d0*100:.1f} cm DESDE EL LIDAR, a {ang0:+.0f}°')
print(f'    -> desde el borde del robot serían {(d0-borde)*100:.1f} cm')
print(f'    -> con radius {RADIO_NORMAL}: {"DENTRO del círculo" if d0 < RADIO_NORMAL else "fuera"}')

# «alejarse» depende de dónde esté el obstáculo. En diferencial no hay lateral.
if abs(ang0) > 135:
    aleja, acerca = +1.0, -1.0          # obstáculo detrás -> alejarse es avanzar
elif abs(ang0) < 45:
    aleja, acerca = -1.0, +1.0          # obstáculo delante -> alejarse es retroceder
else:
    aleja, acerca = None, None          # obstáculo al costado: ninguna lo aleja
print(f'    -> «alejarse» aquí es {"AVANZAR" if aleja == 1 else ("RETROCEDER" if aleja == -1 else "NINGUNA (obstáculo al costado)")}')
print()
print(f'  {"radius":>7} | {"GIRAR":>16} | {"ALEJARSE":>16} | {"ACERCARSE":>16}')
print('  ' + '-' * 74)

try:
    for r in [float(x) for x in a.radios.split(',')]:
        poner_radio(r)
        cel = []
        g_cm, g_deg, g_acc, _ = orden(0.0, 0.6, 2.0)
        cel.append(f'{g_deg:5.1f}° {",".join(g_acc) or "-":>8}')
        for signo in (aleja, acerca):
            if signo is None:
                cel.append(f'{"n/a":>16}')
                continue
            c, _, acc, cortado = orden(0.10 * signo, 0.0, 1.5)
            cel.append(f'{c:5.1f}cm {",".join(acc) or "-":>8}' + ('!' if cortado else ''))
        print(f'  {r:7.2f} | {cel[0]:>16} | {cel[1]:>16} | {cel[2]:>16}'
              f'   (LIDAR {esc.get("d", 0)*100:.1f} cm)')
finally:
    poner_radio(RADIO_NORMAL)
    ver = subprocess.run(['ros2', 'param', 'get', '/collision_monitor',
                          'Aproximacion.radius'], capture_output=True, text=True,
                         timeout=30).stdout.strip()
    print(f'\n  radius restaurado -> {ver}')
print('=' * 78)
