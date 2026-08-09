#!/usr/bin/env python3
"""¿Qué ruta traza Nav2 hasta un objetivo? — SIN MOVER EL ROBOT.

    python3 consultar_plan.py [--meta 1.4] [--repetir 3]

✅ NO MUEVE EL ROBOT. Usa la acción `compute_path_to_pose`, que es justo la que
   `bt_navigator` invoca por dentro, pero sin encadenarla al controlador. Cuesta
   cero batería y no puede chocar.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════
Las cuatro tandas de `probar_rodeo_obstaculo.py` del 2026-08-09 —dos con AMCL y
dos con SLAM— enseñaron siempre lo mismo: **con el objetivo recto delante y una
puerta de 30-34 cm centrada en el eje, el robot se va 56-77 cm DE LADO en los
primeros cinco segundos** y acaba abortando.

Eso admite dos lecturas incompatibles, y el banco no las distinguía:

  a) Nav2 traza recto por el hueco y el robot no sigue el plan
     -> el problema está en el CONTROL
  b) Nav2 traza un RODEO alrededor de la puerta
     -> el problema está en el COSTE: pasar por el hueco sale caro y NavFn
        prefiere dar la vuelta. En un cuarto de 3,8 x 4,2 m no hay sitio para
        dar la vuelta, así que se queda sin camino y aborta.

🔎 **La forma del plan lo dice sin ambigüedad**, y se puede preguntar sin mover
   nada. Eso es preferible a deducirlo del recorrido: el recorrido mezcla plan,
   control, deriva y choques.

📌 Y se pregunta VARIAS VECES: el costmap cambia entre ciclos —medido el
   2026-08-09: «corredor máximo 96, transitable» y dos minutos después
   `planner_server` falló desde esa misma pose—. Un plan suelto no es un dato.

⚠️ Requiere `nav2.launch.py` levantado (con AMCL o con SLAM, da igual: esto sólo
   mira el planificador).
"""
import argparse
import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from nav_msgs.msg import Odometry, OccupancyGrid
from nav2_msgs.action import ComputePathToPose
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener

p = argparse.ArgumentParser()
p.add_argument('--meta', type=float, default=1.4,
               help='metros hacia delante, sobre el rumbo actual')
p.add_argument('--repetir', type=int, default=3)
p.add_argument('--marco', default='odom', choices=['odom', 'map'],
               help='marco del objetivo. `odom` no depende de la localización')
a = p.parse_args()

QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)


def yaw_de(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))


rclpy.init()
n = Node('consultar_plan')
odom = {}
n.create_subscription(Odometry, '/odom', lambda m: odom.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y,
    yaw=yaw_de(m.pose.pose.orientation)), QT)
cmap = []
n.create_subscription(
    OccupancyGrid, '/global_costmap/costmap', lambda m: cmap.append(m),
    QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
               durability=QoSDurabilityPolicy.TRANSIENT_LOCAL))
buf = Buffer(); TransformListener(buf, n)
cli = ActionClient(n, ComputePathToPose, 'compute_path_to_pose')


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.02)


print('=' * 76)
print(f' CONSULTA DE PLAN · +{a.meta:.2f} m hacia delante · marco {a.marco}')
print(' ✅ EL ROBOT NO SE MUEVE')
print('=' * 76)

if not cli.wait_for_server(timeout_sec=30):
    print('  🔴 compute_path_to_pose no responde: ¿está nav2 levantado?')
    raise SystemExit(1)
bombear(3)
if 'x' not in odom:
    print('  🔴 sin /odom'); raise SystemExit(1)
ox, oy, oyaw = odom['x'], odom['y'], odom['yaw']
print(f'  robot en odom ({ox:+.3f}, {oy:+.3f}) yaw {math.degrees(oyaw):+.1f}°')

for intento in range(1, a.repetir + 1):
    g = ComputePathToPose.Goal()
    g.use_start = False
    g.goal = PoseStamped()
    g.goal.header.frame_id = a.marco
    if a.marco == 'odom':
        gx, gy, gyaw = ox + a.meta * math.cos(oyaw), oy + a.meta * math.sin(oyaw), oyaw
    else:
        tr = buf.lookup_transform('map', 'base_footprint', rclpy.time.Time()).transform
        myaw = yaw_de(tr.rotation)
        gx = tr.translation.x + a.meta * math.cos(myaw)
        gy = tr.translation.y + a.meta * math.sin(myaw)
        gyaw = myaw
    g.goal.pose.position.x = gx
    g.goal.pose.position.y = gy
    g.goal.pose.orientation.z = math.sin(gyaw / 2.0)
    g.goal.pose.orientation.w = math.cos(gyaw / 2.0)

    fg = cli.send_goal_async(g)
    rclpy.spin_until_future_complete(n, fg, timeout_sec=25)
    gh = fg.result()
    if gh is None or not gh.accepted:
        print(f'  {intento}. 🔴 consulta RECHAZADA'); continue
    fr = gh.get_result_async()
    rclpy.spin_until_future_complete(n, fr, timeout_sec=30)
    res = fr.result()
    # 🔴 SE MIRA EL EFECTO —si hay puntos— y no sólo el `status`: un plan vacío
    #    con status 4 seguiría siendo «no hay camino».
    pts = [(q.pose.position.x, q.pose.position.y)
           for q in res.result.path.poses] if res else []
    if not pts:
        print(f'  {intento}. 🔴 SIN CAMINO (status {res.status if res else "?"}) '
              f'-> el planificador se niega, y esto no depende del controlador')
        bombear(2)
        continue

    largo = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    lat = [abs(-(x - pts[0][0]) * math.sin(oyaw) + (y - pts[0][1]) * math.cos(oyaw))
           for x, y in pts]
    adv = [(x - pts[0][0]) * math.cos(oyaw) + (y - pts[0][1]) * math.sin(oyaw)
           for x, y in pts]
    rodeo = max(lat) > 0.30
    print(f'  {intento}. {len(pts)} puntos · largo {largo*100:.0f} cm para '
          f'{a.meta*100:.0f} en recto ({100*largo/a.meta:.0f} %) · '
          f'lateral MÁX {max(lat)*100:.1f} cm  '
          + ('🔴 RODEA' if rodeo else '✅ pasa por el hueco'))
    print('       avance->lateral (cm): '
          + '  '.join(f'{adv[k]*100:.0f}->{lat[k]*100:.0f}'
                      for k in range(0, len(pts), max(1, len(pts) // 8))))
    bombear(2)

# El coste que ve el planificador en el eje, que es lo que decide si rodea.
bombear(2)
if cmap:
    G = cmap[-1]; I = G.info; res = I.resolution
    try:
        tr = buf.lookup_transform('map', 'base_footprint', rclpy.time.Time()).transform
        rx, ry, ryaw = tr.translation.x, tr.translation.y, yaw_de(tr.rotation)

        def cel(x, y):
            i = int((x - I.origin.position.x) / res)
            j = int((y - I.origin.position.y) / res)
            if not (0 <= i < I.width and 0 <= j < I.height):
                return None
            return G.data[j * I.width + i]

        print('  ── coste EN EL EJE del robot, cada 10 cm (99+ = intransitable) ──')
        fila = []
        for k in range(0, int(a.meta * 100) + 10, 10):
            d = k / 100.0
            c = cel(rx + d * math.cos(ryaw), ry + d * math.sin(ryaw))
            fila.append(f'{k:3d}cm:{"?" if c is None else ("desc" if c == -1 else c)}')
        print('     ' + '  '.join(fila))
    except Exception as e:                                          # noqa: BLE001
        print(f'  ⚠️ sin TF map->base_footprint: {e}')

print('=' * 76)
