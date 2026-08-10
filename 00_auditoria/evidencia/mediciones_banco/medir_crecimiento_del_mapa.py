#!/usr/bin/env python3
"""¿Crece el mapa de slam_toolbox conforme el robot conduce, o se queda quieto?

    python3 medir_crecimiento_del_mapa.py <etiqueta> [--minutos 4]

🔴 CONDUCE EL ROBOT SOLO por el cuarto. Requiere a alguien mirando y el suelo
   despejado. Manda por `/cmd_vel_raw`, o sea CON el collision_monitor en el lazo.

═══════════════════════════════════════════════════════════════════════════════
LA PREGUNTA, Y POR QUÉ ES UNA Y NO DOS
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-09 el mapa de slam_toolbox salió **casi vacío** —49 celdas ocupadas
para un cuarto entero, 91,8 % desconocido— y **no cambió** tras 360° de giro y
160 cm de vaivén. Se anotó como «mapa congelado», un defecto.

⚠️ **Pero al releer la configuración esa conclusión se tambalea:**

      minimum_travel_distance: 0.3   -> un nodo del grafo cada 30 cm
      min_pass_through: 2            -> una celda necesita DOS rayos que la crucen

   160 cm de recorrido son ~4 nodos, y el grafo tenía **exactamente 4**. Con
   cuatro barridos desde casi el mismo sitio, la mayoría de celdas reciben **un
   solo rayo** y se descartan. **Un mapa 91,8 % vacío es lo ESPERABLE de ese
   recorrido, no necesariamente un fallo.**

   Y hay un precedente que apunta a lo mismo: **`cuarto3` existe y es un mapa de
   verdad**, hecho conduciendo por el cuarto. Si slam_toolbox estuviera roto, no
   existiría.

🔎 **Las dos hipótesis se separan con UNA medida: la curva de relleno contra
   distancia conducida.**

     A) el mapa CRECE con los metros  -> era submuestreo. No hay defecto, y el
        aula se mapea conduciendo, que es lo que se iba a hacer igualmente.
     B) los NODOS crecen y la rejilla NO -> sí hay defecto, y con el nodo y la
        celda delante se sabe dónde mirar.

📌 Por eso se muestrean **las dos cosas a la vez**: nodos del grafo y contenido de
   la rejilla. Mirar sólo el mapa no distingue «no llegan barridos» de «llegan y
   no se pintan» — que es justo el error que hizo falta corregir.

═══════════════════════════════════════════════════════════════════════════════
CÓMO CONDUCE
═══════════════════════════════════════════════════════════════════════════════
Patrón conservador y repetitivo: **girar un poco, avanzar un poco**, con guardia
por LIDAR. No busca cubrir el cuarto de forma óptima: busca **acumular nodos**,
que es lo que decide la pregunta.

🔴 La guardia corta el avance a **35 cm** de cualquier cosa. La franja de
   inmovilización del `collision_monitor` empieza en 15, así que nunca se acerca:
   un robot atascado a mitad de medida la echaría a perder (evidencia 94).
"""
import argparse
import csv
import hashlib
import math
import os
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy)
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from visualization_msgs.msg import MarkerArray

p = argparse.ArgumentParser()
p.add_argument('etiqueta')
p.add_argument('--minutos', type=float, default=4.0)
p.add_argument('--guardia', type=float, default=0.35,
               help='m: no avanza si hay algo más cerca por delante')
a = p.parse_args()

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'crecimiento_mapa.csv')
QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)
LAT = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                 durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
n = Node('crecimiento_mapa')
odom, esc, mapa, grafo = {}, {}, {}, {}


def cb_odom(m):
    q = m.pose.pose.orientation
    y = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))
    if odom:
        odom['rec'] = odom.get('rec', 0.0) + math.hypot(
            m.pose.pose.position.x - odom['x'], m.pose.pose.position.y - odom['y'])
    odom.update(x=m.pose.pose.position.x, y=m.pose.pose.position.y, yaw=y)


def cb_scan(m):
    fr = []
    for i, r in enumerate(m.ranges):
        if not (m.range_min < r < m.range_max) or math.isinf(r) or math.isnan(r):
            continue
        ang = m.angle_min + i * m.angle_increment
        x, y = r * math.cos(ang), r * math.sin(ang)
        if x > 0.02 and abs(y) < 0.16:
            fr.append(x)
    esc['delante'] = min(fr) if fr else None
    # sitio a cada lado, para decidir HACIA DÓNDE girar en vez de a ciegas
    iz = [r for i, r in enumerate(m.ranges)
          if (m.range_min < r < m.range_max) and not math.isinf(r) and not math.isnan(r)
          and 40 <= math.degrees(m.angle_min + i * m.angle_increment) <= 140]
    de = [r for i, r in enumerate(m.ranges)
          if (m.range_min < r < m.range_max) and not math.isinf(r) and not math.isnan(r)
          and -140 <= math.degrees(m.angle_min + i * m.angle_increment) <= -40]
    esc['izq'] = max(iz) if iz else 0.0
    esc['der'] = max(de) if de else 0.0


def cb_map(m):
    d = m.data
    mapa.update(w=m.info.width, h=m.info.height, res=m.info.resolution,
                ocupado=sum(1 for v in d if v >= 65),
                libre=sum(1 for v in d if 0 <= v < 25),
                desc=d.count(-1), total=len(d),
                hash=hashlib.md5(bytes((v + 1) & 0xFF for v in d)).hexdigest()[:8])


n.create_subscription(Odometry, '/odom', cb_odom, QT)
n.create_subscription(LaserScan, '/scan', cb_scan, QT)
n.create_subscription(OccupancyGrid, '/map', cb_map, LAT)
n.create_subscription(MarkerArray, '/slam_toolbox/graph_visualization',
                      lambda m: grafo.update(n=len(m.markers)), 10)
pub = n.create_publisher(Twist, '/cmd_vel_raw', 10)


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.01)


def parar():
    tw = Twist()
    for _ in range(25):
        pub.publish(tw); time.sleep(0.02)
    bombear(0.5)


# 🔴 EXPLORACIÓN REACTIVA, y la primera versión NO lo era: giraba 40 grados a
#    ciegas y volvía a encararse a la misma pared. Con el frente a 29-36 cm y la
#    guardia en 35, `avanzar` devolvía False SIEMPRE y el robot se quedó dando
#    tumbos contra la pared sin acumular un solo nodo.
#    Lo vio el usuario: «está atrapado frente a la pared, deberías darle una
#    exploración un poco más adaptativa».
# ✅ Ahora no se elige un ángulo: se GIRA HASTA QUE EL FRENTE SE ABRE. Es
#    reactivo, no necesita control de ángulo —que además tiene sobregiro— y sale
#    solo de rincones.
def girar_hasta_hueco(objetivo, tope_s=12.0):
    """Gira hacia el lado con más sitio hasta que el frente supere `objetivo`."""
    izq = esc.get('izq', 0.0) or 0.0
    der = esc.get('der', 0.0) or 0.0
    w = 0.6 if izq >= der else -0.6
    tw = Twist(); tw.angular.z = w
    t0 = time.time()
    while time.time() - t0 < tope_s:
        d = esc.get('delante')
        if d is not None and d > objetivo:
            break
        pub.publish(tw)
        rclpy.spin_once(n, timeout_sec=0.0); time.sleep(0.05)
    parar()
    return esc.get('delante')


def avanzar_hasta(guardia, metros, tope_s=12.0):
    """Avanza hasta acercarse a `guardia` o recorrer `metros`."""
    x0, y0 = odom['x'], odom['y']
    tw = Twist(); tw.linear.x = 0.15
    t0 = time.time()
    while time.time() - t0 < tope_s:
        d = esc.get('delante')
        if d is not None and d < guardia:
            break
        if math.hypot(odom['x'] - x0, odom['y'] - y0) >= metros:
            break
        pub.publish(tw)
        rclpy.spin_once(n, timeout_sec=0.0); time.sleep(0.05)
    parar()
    return math.hypot(odom['x'] - x0, odom['y'] - y0)


print('=' * 78)
print(f' CRECIMIENTO DEL MAPA · {a.etiqueta} · {a.minutos:.0f} min')
print(' 🔴 EL ROBOT CONDUCE SOLO. Suelo despejado y alguien mirando.')
print('=' * 78)

bombear(5)
for k, v in (('odom', 'x' in odom), ('scan', 'delante' in esc),
             ('map', 'total' in mapa), ('grafo', 'n' in grafo)):
    if not v:
        print(f'  🔴 no llega {k}'); raise SystemExit(1)
odom['rec'] = 0.0

print(f'  {"t(s)":>5} {"recorrido":>10} {"nodos":>6} {"ocupado":>8} {"libre":>7} '
      f'{"descon.":>8} {"hash":>9}')
filas = []


def muestra(t):
    m2 = mapa['res'] ** 2
    fila = (round(t, 1), round(odom.get('rec', 0.0) * 100, 1), grafo.get('n', 0),
            mapa['ocupado'], mapa['libre'],
            round(100.0 * mapa['desc'] / mapa['total'], 1), mapa['hash'])
    filas.append(fila)
    print(f'  {fila[0]:5.0f} {fila[1]:9.0f}cm {fila[2]:6d} {fila[3]:8d} '
          f'{fila[4]:7d} {fila[5]:7.1f}% {fila[6]:>9}')


t0 = time.time()
muestra(0.0)
try:
    while time.time() - t0 < a.minutos * 60:
        d = esc.get('delante')
        if d is None or d < a.guardia + 0.15:
            girar_hasta_hueco(a.guardia + 0.25)
            bombear(0.8)
        rec = avanzar_hasta(a.guardia, 0.60)
        bombear(1.5)
        muestra(time.time() - t0)
        if rec < 0.05:            # no consiguió avanzar: fuerza un giro largo
            girar_hasta_hueco(a.guardia + 0.35, tope_s=8.0)
            bombear(0.8)
finally:
    parar()
    nuevo = not os.path.exists(CSV)
    with open(CSV, 'a', newline='') as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(['etiqueta', 't_s', 'recorrido_cm', 'nodos', 'ocupado',
                        'libre', 'desconocido_pct', 'hash'])
        for fila in filas:
            w.writerow([a.etiqueta] + list(fila))

if len(filas) >= 2:
    p0, pf = filas[0], filas[-1]
    print()
    print(f'  recorrido total     {pf[1]:.0f} cm')
    print(f'  nodos     {p0[2]:4d} -> {pf[2]:4d}')
    print(f'  ocupadas  {p0[3]:4d} -> {pf[3]:4d}')
    print(f'  libres    {p0[4]:4d} -> {pf[4]:4d}')
    print(f'  descon.  {p0[5]:5.1f}% -> {pf[5]:5.1f}%')
    print(f'  hashes distintos: {len(set(f[6] for f in filas))} de {len(filas)}')
    crecio_grafo = pf[2] > p0[2]
    crecio_mapa = (pf[3] + pf[4]) > (p0[3] + p0[4]) * 1.2
    print()
    if crecio_mapa:
        print('  ✅ HIPÓTESIS A: el mapa CRECE con los metros. Era submuestreo, no un'
              ' defecto:\n     el aula se mapea conduciendo, que es lo que se iba a hacer.')
    elif crecio_grafo:
        print('  🔴 HIPÓTESIS B: los NODOS crecen y la rejilla NO. Hay un defecto real'
              ' en\n     la conversión grafo -> OccupancyGrid.')
    else:
        print('  ⚠️ NI el grafo ni el mapa crecieron: mira si el robot llegó a moverse'
              '\n     (recorrido de arriba) antes de concluir nada.')
print('=' * 78)
