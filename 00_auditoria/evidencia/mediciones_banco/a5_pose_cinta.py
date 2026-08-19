#!/usr/bin/env python3
"""A5 · ¿es correcta la pose que fija /initialpose? — cinta contra AMCL.

Dos subcomandos, y las medidas SIEMPRE son dos distancias PERPENDICULARES a dos
paredes distintas (nunca una diagonal: con una sola distancia dos hipotesis
separadas 45 cm difieren 2 cm y no se distinguen — evidencia 84).

  fijar    --izq CM --atras CM [--yaw GRADOS]
      publica /initialpose con la pose que dice la cinta. Sello 0, que en tf2
      significa «usa la transformada mas reciente»: con now() AMCL la descarta
      por extrapolacion al futuro (evidencia 88).

  comparar --izq CM --atras CM
      lee /amcl_pose y la contrasta con lo que dice la cinta.

Referencia: paredes del mapa arena.yaml, nombradas como las veia el robot en la
esquina de arranque al mapear.
"""
import argparse, math, sys, time

# 🔴 NO se usan los extremos de celdas ocupadas del mapa (-0.61 / +0.70): un extremo
#    es un valor ATIPICO por construccion, y daban 7 y 15 cm de sesgo. La referencia
#    se ancla al ORIGEN, que es el unico punto cuya coordenada esta verificada (el
#    anclaje de SLAM en (0,0,0) el 2026-08-19), con las distancias que el LIDAR leyo
#    ALLI al empezar a mapear: 0.55 a la izquierda y 0.54 atras.
X_PARED_ATRAS = -0.54
Y_PARED_IZQ = +0.55

def cinta_a_mapa(izq_cm, atras_cm):
    """Distancias a las dos paredes -> coordenadas del mapa."""
    return X_PARED_ATRAS + atras_cm / 100.0, Y_PARED_IZQ - izq_cm / 100.0

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from geometry_msgs.msg import PoseWithCovarianceStamped

def fijar(a):
    x, y = cinta_a_mapa(a.izq, a.atras)
    th = math.radians(a.yaw)
    rclpy.init()
    n = Node('a5_fijar')
    pub = n.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
    ex = SingleThreadedExecutor(); ex.add_node(n)
    m = PoseWithCovarianceStamped()
    m.header.frame_id = 'map'          # sello 0 a proposito (evidencia 88)
    m.pose.pose.position.x = x
    m.pose.pose.position.y = y
    m.pose.pose.orientation.z = math.sin(th / 2)
    m.pose.pose.orientation.w = math.cos(th / 2)
    cov = [0.0] * 36
    cov[0] = cov[7] = 0.25             # 50 cm de sigma: generosa, que AMCL corrija
    cov[35] = 0.07                     # ~15 grados
    m.pose.covariance = cov
    print(f"cinta: izq {a.izq} cm · atras {a.atras} cm  ->  map ({x:+.3f},{y:+.3f}) yaw {a.yaw:+.1f}°")
    t0 = time.time()
    while time.time() - t0 < 2.0:      # varias veces: es un topic, no un servicio
        pub.publish(m)
        ex.spin_once(timeout_sec=0.0); time.sleep(0.2)
    print("publicado en /initialpose")
    n.destroy_node(); rclpy.shutdown()

def leer_amcl(segundos=20.0):
    rclpy.init()
    n = Node('a5_leer')
    d = {}
    qos = QoSProfile(depth=5, reliability=QoSReliabilityPolicy.RELIABLE)
    n.create_subscription(PoseWithCovarianceStamped, '/amcl_pose',
                          lambda m: d.__setitem__('p', m), qos)
    ex = SingleThreadedExecutor(); ex.add_node(n)
    t0 = time.time()
    while time.time() - t0 < segundos and 'p' not in d:
        ex.spin_once(timeout_sec=0.0); time.sleep(0.005)
    n.destroy_node(); rclpy.shutdown()
    return d.get('p')

def comparar(a):
    xc, yc = cinta_a_mapa(a.izq, a.atras)
    p = leer_amcl()
    if p is None:
        print("SIN /amcl_pose. AMCL solo publica tras moverse ~15 cm: conduce un poco.")
        sys.exit(1)
    q = p.pose.pose.orientation
    yaw = math.degrees(math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z)))
    xa, ya = p.pose.pose.position.x, p.pose.pose.position.y
    dx, dy = xa - xc, ya - yc
    d = math.hypot(dx, dy)
    print(f"cinta dice:  map ({xc:+.3f},{yc:+.3f})")
    print(f"AMCL dice:   map ({xa:+.3f},{ya:+.3f}) yaw {yaw:+.1f}°")
    print(f"DIFERENCIA:  {d*100:.1f} cm   (dx {dx*100:+.1f} · dy {dy*100:+.1f})")
    print(f"sigma de AMCL: x {math.sqrt(p.pose.covariance[0])*100:.1f} cm · y {math.sqrt(p.pose.covariance[7])*100:.1f} cm")

ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest='cmd', required=True)
for nombre in ('fijar', 'comparar'):
    s = sub.add_parser(nombre)
    s.add_argument('--izq', type=float, required=True, help='cm del punto a la pared IZQUIERDA (la del mapeo)')
    s.add_argument('--atras', type=float, required=True, help='cm del punto a la pared de DETRAS (la del mapeo)')
    if nombre == 'fijar':
        s.add_argument('--yaw', type=float, default=0.0, help='grados; 0 = mirando como al mapear')
a = ap.parse_args()
(fijar if a.cmd == 'fijar' else comparar)(a)
