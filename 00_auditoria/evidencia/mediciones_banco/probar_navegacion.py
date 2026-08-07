#!/usr/bin/env python3
"""¿Navega Nav2 de verdad, y está AMCL localizado? — repetible.

    ros2 run … no: se ejecuta suelto, con el entorno de ROS cargado:
        python3 -u probar_navegacion.py            # objetivo por defecto: 0,80 m
        python3 -u probar_navegacion.py 0.60       # otra distancia

🔴 MUEVE EL ROBOT. Requiere:
   · el robot colocado DONDE ESTABA AL MAPEAR (posición Y rumbo)
   · espacio despejado por delante: la distancia del objetivo + medio metro
   · una persona mirando, con la mano cerca
   · CINTA MÉTRICA — es el único testigo que no se puede enredar

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE, Y QUÉ MIDE QUE NO SE MEDÍA
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-07 (evidencia 81) Nav2 navegó por primera vez y **declaró el objetivo
cumplido sobre una pose que se había ido 98°**:

    cinta         70   cm      odometría   70,1 cm     ← coinciden en 1 mm
    AMCL          78,4 cm      objetivo    80   cm
    map -> odom   yaw +98,46°  🔴

Si aquella prueba se hubiera leído por `/amcl_pose` se habría escrito «navega con
2,5 cm de error». Falso por partida doble: el error real fue 10 cm y la dirección
estaba 98° equivocada.

**Por eso este banco registra `map -> odom` DURANTE el recorrido, no solo al
final.** Un marco que rota mientras el robot avanza es la firma de una AMCL que
no está localizada, y con una sola lectura final no se distingue de un ajuste
inicial legítimo.
"""
import math
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener

META_X = float(sys.argv[1]) if len(sys.argv) > 1 else 0.80

QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)


def yaw_de(q):
    return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y),
                                   1 - 2 * (q.y ** 2 + q.z ** 2)))


rclpy.init()
n = Node('probar_navegacion')
odom, amcl = {}, {}
n.create_subscription(Odometry, '/odom', lambda m: odom.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y,
    yaw=yaw_de(m.pose.pose.orientation)), QT)
n.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', lambda m: amcl.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y,
    yaw=yaw_de(m.pose.pose.orientation)), 10)
pub_ip = n.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
buf = Buffer(); TransformListener(buf, n)


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.02)


def correccion():
    """`map -> odom`: lo que AMCL está corrigiendo. 0 = confía en la odometría."""
    try:
        t = buf.lookup_transform('map', 'odom', rclpy.time.Time())
        tr = t.transform.translation
        return math.hypot(tr.x, tr.y), yaw_de(t.transform.rotation)
    except Exception:                                            # noqa: BLE001
        return None, None


print('=' * 74)
print(f' probar_navegacion.py · objetivo ({META_X:.2f}, 0.00) en el marco `map`')
print('=' * 74)
print('  📏 ANTES DE SEGUIR, marca el suelo con cinta adhesiva:')
print('       A = bajo el CENTRO del robot')
print('       B = a ~1 m de A, a la IZQUIERDA del robot (perpendicular a como mira)')
print('     Mide A→B con la cinta y apúntala. El ángulo NO tiene que ser exacto;')
print('     la distancia sí.')
print('  🔴 Con UNA sola distancia no se puede saber dónde acabó: deja al robot en')
print('     cualquier punto de una circunferencia. Con dos, sale la posición.')
print()
bombear(3)
if not odom:
    print('  🔴 no llega /odom. ¿Está el driver corriendo?'); raise SystemExit(1)

print(f'  odom inicial   x={odom.get("x", 0):+.3f} y={odom.get("y", 0):+.3f} '
      f'yaw={odom.get("yaw", 0):+.1f}°')

ip = PoseWithCovarianceStamped()
ip.header.frame_id = 'map'
ip.header.stamp = n.get_clock().now().to_msg()
ip.pose.pose.orientation.w = 1.0
ip.pose.covariance[0] = ip.pose.covariance[7] = 0.25
ip.pose.covariance[35] = 0.07
pub_ip.publish(ip)
bombear(5)
d, a = correccion()
print(f'  tras /initialpose(0,0,0):  amcl=({amcl.get("x", 0):+.3f}, '
      f'{amcl.get("y", 0):+.3f}) yaw={amcl.get("yaw", 0):+.1f}°')
print(f'                             map->odom  {d:.3f} m  {a:+.2f}°'
      if d is not None else '                             (sin transformada)')

cli = ActionClient(n, NavigateToPose, 'navigate_to_pose')
if not cli.wait_for_server(timeout_sec=20):
    print('  🔴 /navigate_to_pose no responde. ¿Está la navegación arrancada?')
    raise SystemExit(1)

g = NavigateToPose.Goal()
g.pose.header.frame_id = 'map'
g.pose.header.stamp = n.get_clock().now().to_msg()
g.pose.pose.position.x = META_X
g.pose.pose.orientation.w = 1.0

print(f'\n  🔴 OBJETIVO ENVIADO. EL ROBOT SE MUEVE.\n')
t0 = time.monotonic()
fg = cli.send_goal_async(g)
rclpy.spin_until_future_complete(n, fg, timeout_sec=20)
gh = fg.result()
if gh is None or not gh.accepted:
    print('  🔴 objetivo RECHAZADO'); raise SystemExit(1)

fr = gh.get_result_async()
traza = []
ult = 0.0
while not fr.done() and time.monotonic() - t0 < 90:
    rclpy.spin_once(n, timeout_sec=0.0)
    time.sleep(0.05)
    if time.monotonic() - ult >= 3.0:
        ult = time.monotonic()
        d, a = correccion()
        traza.append((ult - t0, d, a))
        print(f'    {ult - t0:5.1f}s  odom=({odom.get("x", 0):+.3f},{odom.get("y", 0):+.3f})'
              f'  amcl=({amcl.get("x", 0):+.3f},{amcl.get("y", 0):+.3f})'
              f'  map->odom {a:+7.2f}°' if a is not None else '')
bombear(2)

rec_odom = math.hypot(odom.get('x', 0), odom.get('y', 0))
rec_amcl = math.hypot(amcl.get('x', 0), amcl.get('y', 0))
d, a = correccion()
giros = [abs(x[2]) for x in traza if x[2] is not None]

print('\n' + '=' * 74)
print(f'  duración                    {time.monotonic() - t0:.1f} s')
print(f'  recorrido según ODOMETRÍA   {rec_odom * 100:.1f} cm')
print(f'  recorrido según AMCL        {rec_amcl * 100:.1f} cm   (objetivo {META_X * 100:.0f})')
print(f'  corrección map->odom final  {d:.3f} m   {a:+.2f}°' if d is not None else '')
if giros:
    print(f'  |yaw| de map->odom durante  min {min(giros):.2f}°  max {max(giros):.2f}°')
print()
print('  📏 AHORA MIDE, con el robot donde paró:')
print('       AP = de la marca A al centro del robot   (la diagonal de siempre)')
print('       BP = de la marca B al centro del robot   ← la que decide')
print()
print('  Y pega esto, poniendo tus tres distancias EN METROS:')
print()
print(f'    python3 comparar_con_cinta.py  <AB> <AP> <BP> \\')
print(f'        --odom {odom.get("x", 0):.3f} {odom.get("y", 0):.3f} '
      f'--amcl {amcl.get("x", 0):.3f} {amcl.get("y", 0):.3f}')
print()
print('  (añade --detras si el robot acabó DETRÁS de la línea A-B)')
print()
print('  🔴 Lo que decide NO es quién acierta la distancia, sino quién acierta la')
print('     POSICIÓN. El 2026-08-07 la odometría y AMCL coincidían en distancia y')
print('     estaban a 45 cm y 38° la una de la otra. Una sola medida no lo ve.')
print('=' * 74)
n.destroy_node()
rclpy.shutdown()
