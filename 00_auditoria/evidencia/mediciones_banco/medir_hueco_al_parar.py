#!/usr/bin/env python3
"""¿A cuántos cm de la pared para el robot, y cómo cambia con `Aproximacion.radius`?

    python3 medir_hueco_al_parar.py [--radios 0.18,0.15] [--vel 0.25] [--repes 2]

🔴 EL ROBOT AVANZA CONTRA UNA PARED a velocidad de trabajo. Exige a alguien
   mirando y ~1,2 m de carrerilla despejada por delante.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ HACE FALTA
═══════════════════════════════════════════════════════════════════════════════
El barrido de pared del 2026-08-09 (24 estaciones, cuatro direcciones) dejó el
umbral del `collision_monitor` medido y con él la BANDA DE TRAMPA: entre el radio
circunscrito del robot (14,42 cm desde `base_footprint`) y `Aproximacion.radius`
(18 cm), el robot está **congelado pudiendo girar sin rozar nada**. Son 3,6 cm.

🔎 **Y el hallazgo que decide el ajuste: la banda de trampa y el margen de
   seguridad contra el error del LIDAR SON EL MISMO NÚMERO**, `radius − 14,42`.
   No se puede encoger uno sin encoger el otro.

        radius   banda de trampa   margen ante error   hueco al parar (MODELO)
         0.18         3,6 cm            3,6 cm               8,5 cm
         0.15         0,6 cm            0,6 cm               5,5 cm
         0.145        0,1 cm            0,1 cm               5,0 cm   <- por debajo
                                                                        del ruido
                                                                        medido (±0,3)

🔴 **La última columna es un MODELO** (`radius − media longitud`), no una medida.
   La única cifra real es «para a 20,8 cm sin chocar» de la aceptación, y los
   9,9 cm a 0,25 m/s del fichero 17 — las dos con `radius: 0.18`.
   **Este banco mide esa columna**, que es lo único que falta para elegir el radio
   con datos en vez de con una fórmula.

═══════════════════════════════════════════════════════════════════════════════
CÓMO
═══════════════════════════════════════════════════════════════════════════════
Por cada radio y repetición: el robot avanza a `--vel` con el monitor EN EL LAZO
(`/cmd_vel_raw`) hasta que deja de moverse, y se mide la distancia final a la
pared. El `approach` no es una parada: **escala la velocidad para que el choque
caiga en `time_before_collision`, así que el robot se acerca ASINTÓTICAMENTE**.
Por eso se espera a que la velocidad real caiga, no a un evento de parada.

  · `lidar_cm`  distancia del EJE DEL LIDAR a la pared
  · `hueco_cm`  lo que vería una persona: `lidar_cm − 10,0`, porque el borde
                delantero está a 10,0 cm del eje (medido con el robot tocando la
                pared: perfil perpendicular plano en ±24°, n=3478)

🔴 ENTRE REPETICIONES HAY QUE RETROCEDER PUENTEANDO EL MONITOR, y no es un atajo:
   al pararse, la pared queda DENTRO del círculo y el robot queda inmovilizado
   —no puede ni alejarse— como se midió en la evidencia 93. El retroceso va por
   `/cmd_vel` y **se comprueba que la distancia CRECE**: si no crece, se aborta.

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

BORDE_DELANTERO = 0.100          # eje del LIDAR -> borde delantero, medido
RADIO_NORMAL = 0.18

p = argparse.ArgumentParser()
p.add_argument('--radios', default='0.18,0.15')
p.add_argument('--vel', type=float, default=0.25)
p.add_argument('--repes', type=int, default=2)
p.add_argument('--carrerilla', type=float, default=0.60,
               help='m: distancia mínima a la pared para empezar')
p.add_argument('--abortar-en', type=float, default=0.105,
               help='m: si el LIDAR ve la pared más cerca, se corta (el monitor '
                    'habría fallado)')
a = p.parse_args()

QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)

rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
n = Node('hueco_al_parar')
odom, esc = {}, {}


def cb_odom(m):
    odom.update(x=m.pose.pose.position.x, y=m.pose.pose.position.y,
                v=m.twist.twist.linear.x)


def cb_scan(m):
    mejor = 9.9
    for i, r in enumerate(m.ranges):
        if not (m.range_min < r < m.range_max) or math.isinf(r) or math.isnan(r):
            continue
        ang = math.degrees(m.angle_min + i * m.angle_increment)
        if abs(ang) <= 20:
            # perpendicular a una pared frontal
            mejor = min(mejor, r * math.cos(math.radians(abs(ang))))
    esc['d'] = mejor if mejor < 9.9 else None


n.create_subscription(Odometry, '/odom', cb_odom, QT)
n.create_subscription(LaserScan, '/scan', cb_scan, QT)
pub_seg = n.create_publisher(Twist, '/cmd_vel_raw', 10)     # CON monitor
pub_cru = n.create_publisher(Twist, '/cmd_vel', 10)         # SIN monitor


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.01)


def parar(pub):
    tw = Twist()
    for _ in range(30):
        pub.publish(tw); time.sleep(0.02)
    bombear(1.5)


def poner_radio(r):
    subprocess.run(['ros2', 'param', 'set', '/collision_monitor',
                    'Aproximacion.radius', str(r)], capture_output=True, timeout=30)
    bombear(2.5)


def retroceder_puenteando(objetivo):
    """Aleja el robot de la pared saltándose el monitor, que si no lo dejaría
    atrapado. Comprueba que la distancia CRECE: si no, aborta."""
    d0 = esc.get('d')
    tw = Twist(); tw.linear.x = -0.12
    t0 = time.time()
    while time.time() - t0 < 15:
        if esc.get('d') and esc['d'] >= objetivo:
            break
        pub_cru.publish(tw); rclpy.spin_once(n, timeout_sec=0.0); time.sleep(0.05)
        if time.time() - t0 > 3 and esc.get('d') and d0 and esc['d'] < d0 + 0.02:
            parar(pub_cru)
            return False, esc.get('d')
    parar(pub_cru)
    return True, esc.get('d')


print('=' * 78)
print(f' HUECO AL PARAR · {a.vel:.2f} m/s · radios {a.radios} · {a.repes} repeticiones')
print(' 🔴 EL ROBOT AVANZA CONTRA LA PARED. Alguien tiene que estar mirando.')
print('=' * 78)

bombear(4)
if esc.get('d') is None or 'x' not in odom:
    print('  🔴 falta /scan frontal o /odom'); raise SystemExit(1)
print(f'  pared al empezar: {esc["d"]*100:.1f} cm del eje '
      f'({esc["d"]*100 - BORDE_DELANTERO*100:.1f} cm del morro)')

resultados = []
try:
    for r in [float(x) for x in a.radios.split(',')]:
        poner_radio(r)
        print(f'\n  ── Aproximacion.radius = {r:.3f} ──')
        for rep in range(1, a.repes + 1):
            if esc['d'] < a.carrerilla:
                ok, d = retroceder_puenteando(a.carrerilla)
                print(f'     (retrocediendo para tomar carrerilla -> {d*100:.1f} cm'
                      + ('' if ok else '  🔴 NO se alejó: abortando') + ')')
                if not ok:
                    raise SystemExit(1)
            bombear(1.5)
            tw = Twist(); tw.linear.x = a.vel
            t0 = time.time(); quieto_desde = None; abortado = False
            while time.time() - t0 < 25:
                pub_seg.publish(tw)
                rclpy.spin_once(n, timeout_sec=0.0); time.sleep(0.05)
                if esc.get('d') and esc['d'] < a.abortar_en:
                    abortado = True; break
                if abs(odom.get('v', 0.0)) < 0.01:
                    quieto_desde = quieto_desde or time.time()
                    if time.time() - quieto_desde > 2.0 and time.time() - t0 > 3:
                        break
                else:
                    quieto_desde = None
            parar(pub_seg)
            d = esc.get('d')
            hueco = d - BORDE_DELANTERO
            resultados.append((r, rep, d * 100, hueco * 100))
            print(f'     {rep}. paró a {d*100:5.1f} cm del eje  ->  '
                  f'HUECO AL MORRO {hueco*100:5.1f} cm   ({time.time()-t0:.1f} s)'
                  + ('   🔴 ABORTADO POR LA GUARDIA: el monitor no frenó a tiempo'
                     if abortado else ''))
finally:
    poner_radio(RADIO_NORMAL)
    ver = subprocess.run(['ros2', 'param', 'get', '/collision_monitor',
                          'Aproximacion.radius'], capture_output=True, text=True,
                         timeout=30).stdout.strip()
    print(f'\n  radius restaurado -> {ver}')

if resultados:
    print('\n  ── RESUMEN ──')
    print(f'  {"radius":>7} {"hueco medido":>26}   {"modelo (r−9,5)":>16}')
    for r in sorted({x[0] for x in resultados}):
        hs = [h for rr, _, _, h in resultados if rr == r]
        print(f'  {r:7.3f} {"  ".join(f"{h:.1f}" for h in hs):>26}   '
              f'{(r-0.095)*100:13.1f} cm')
print('=' * 78)
