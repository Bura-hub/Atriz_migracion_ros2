#!/usr/bin/env python3
"""La prueba de navegación entera en UN SOLO proceso.

    python3 -u prueba_navegacion_completa.py [distancia_m]

🔴 MUEVE EL ROBOT.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ UN SOLO PROCESO — Y ES UN RESULTADO, NO UNA COMODIDAD
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-07, dos objetivos seguidos **ABORTARON** con:

    bt_navigator: Timed out while waiting for action server to acknowledge
                  goal request (follow_path)

No era falta de tiempo de asentamiento —se probó con 8 s— sino **la Pi
saturada**:

    load average 8,39 sobre 4 núcleos
    rvr_driver 22 %  ·  los 5 nodos de Nav2 a 13-15 % cada uno
    y el propio Claude Code al 21,6 %

🔴 **El instrumento estaba perturbando el experimento.** Cada `ros2 service call`
   levanta un intérprete de Python entero; la secuencia anterior encadenaba
   cinco procesos —resetear odometría, pedir navegación, esperar el estado,
   medir, comparar— mientras Nav2 peleaba por la CPU.

Aquí todo va en un proceso: un nodo, sus clientes, y nada más. Y se espera a que
la carga baje antes de mandar el objetivo, en vez de suponer que da igual.
"""
import math
import os
import subprocess
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from std_srvs.srv import SetBool
from tf2_ros import Buffer, TransformListener
from atriz_rvr_msgs.msg import EstadoNavegacion
from atriz_rvr_msgs.srv import SetPosAndYaw

META = float(sys.argv[1]) if len(sys.argv) > 1 else 0.80
CARGA_MAX = 4.0            # sobre 4 núcleos; por encima, Nav2 pierde mensajes
QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)
NOM = {0: 'APAGADO', 1: 'ARRANCANDO', 2: 'FUNCIONANDO', 3: 'CIEGO',
       4: 'MUDO', 5: 'FALLO', 6: 'DESCONOCIDO'}
FIN = {4: '✅ CON ÉXITO', 5: '🔴 CANCELADO', 6: '🔴 ABORTADO'}


def yaw_de(q):
    return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y),
                                   1 - 2 * (q.y ** 2 + q.z ** 2)))


def carga():
    return os.getloadavg()[0]


rclpy.init()
n = Node('prueba_navegacion')
odom, amcl, est = {}, {}, {}
n.create_subscription(Odometry, '/odom', lambda m: odom.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y), QT)
n.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', lambda m: amcl.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y), 10)
n.create_subscription(EstadoNavegacion, '/estado_navegacion',
                      lambda m: est.update(nav=m.nav, det=m.nav_detalle), QT)
pub_ip = n.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
buf = Buffer(); TransformListener(buf, n)
cli_odom = n.create_client(SetPosAndYaw, '/set_pos_and_yaw')
cli_nav = n.create_client(SetBool, '/pedir_nav')
cli_meta = ActionClient(n, NavigateToPose, 'navigate_to_pose')


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.02)


def llamar(cli, req, seg=20.0):
    f = cli.call_async(req)
    rclpy.spin_until_future_complete(n, f, timeout_sec=seg)
    return f.result()


def correccion():
    try:
        t = buf.lookup_transform('map', 'odom', rclpy.time.Time())
        tr = t.transform.translation
        return math.hypot(tr.x, tr.y), yaw_de(t.transform.rotation)
    except Exception:                                            # noqa: BLE001
        return None, None


print('=' * 74)
print(f' prueba de navegación · objetivo ({META:.2f}, 0.00) · carga inicial {carga():.2f}')
print('=' * 74)
print('  📏 El robot tiene que estar sobre la marca A, y B a ~1 m a su izquierda.')
print()

# ── 1 · odometría a cero ─────────────────────────────────────────────────────
if not cli_odom.wait_for_service(timeout_sec=15):
    print('  🔴 /set_pos_and_yaw no responde'); raise SystemExit(1)
req = SetPosAndYaw.Request(); req.yaw = 0.0
r = llamar(cli_odom, req)
bombear(2)
print(f'  odometría a cero: success={r.success if r else "?"} · '
      f'odom=({odom.get("x", 0):+.4f}, {odom.get("y", 0):+.4f})')

# ── 2 · pedir la navegación ──────────────────────────────────────────────────
if not cli_nav.wait_for_service(timeout_sec=15):
    print('  🔴 /pedir_nav no responde'); raise SystemExit(1)
rq = SetBool.Request(); rq.data = True
r = llamar(cli_nav, rq)
print(f'  /pedir_nav: {r.success if r else "?"} · {r.message[:60] if r else ""}')
if r is None or not r.success:
    raise SystemExit(1)

t0 = time.monotonic()
while time.monotonic() - t0 < 150:
    bombear(0.5)
    if est.get('nav') in (2, 5):
        break
print(f'  estado: {NOM.get(est.get("nav"), "?")}  (en {time.monotonic()-t0:.0f} s)')
if est.get('nav') != 2:
    print('  🔴 la navegación no llegó a funcionar'); raise SystemExit(1)

# ── 3 · ESPERAR A QUE LA CARGA BAJE ──────────────────────────────────────────
# 🔴 Esto no es paciencia: es la condición que faltaba. Con la carga por encima
#    de ~2 núcleos, bt_navigator no consigue que controller_server le acuse el
#    objetivo y la acción ABORTA sin que nadie mueva el robot.
print(f'  esperando a que la carga baje de {CARGA_MAX:.1f} (ahora {carga():.2f})…', flush=True)
t0 = time.monotonic()
while carga() > CARGA_MAX and time.monotonic() - t0 < 90:
    bombear(3)
print(f'  carga al mandar el objetivo: {carga():.2f}  (tras {time.monotonic()-t0:.0f} s)')

# ── 4 · pose inicial y objetivo ──────────────────────────────────────────────
ip = PoseWithCovarianceStamped()
ip.header.frame_id = 'map'
ip.header.stamp = n.get_clock().now().to_msg()
ip.pose.pose.orientation.w = 1.0
ip.pose.covariance[0] = ip.pose.covariance[7] = 0.25
ip.pose.covariance[35] = 0.07
pub_ip.publish(ip)
bombear(5)
d, a = correccion()
print(f'  tras /initialpose: amcl=({amcl.get("x", 0):+.3f}, {amcl.get("y", 0):+.3f})'
      f'  map->odom {d:.3f} m {a:+.2f}°' if d is not None else '  (sin transformada)')

if not cli_meta.wait_for_server(timeout_sec=20):
    print('  🔴 /navigate_to_pose no responde'); raise SystemExit(1)
g = NavigateToPose.Goal()
g.pose.header.frame_id = 'map'
g.pose.header.stamp = n.get_clock().now().to_msg()
g.pose.pose.position.x = META
g.pose.pose.orientation.w = 1.0

print('\n  🔴 OBJETIVO ENVIADO. EL ROBOT SE MUEVE.\n', flush=True)
t0 = time.monotonic()
fg = cli_meta.send_goal_async(g)
rclpy.spin_until_future_complete(n, fg, timeout_sec=25)
gh = fg.result()
if gh is None or not gh.accepted:
    print('  🔴 objetivo RECHAZADO'); raise SystemExit(1)

fr = gh.get_result_async()
ult, giros = 0.0, []
while not fr.done() and time.monotonic() - t0 < 90:
    rclpy.spin_once(n, timeout_sec=0.0)
    time.sleep(0.05)
    if time.monotonic() - ult >= 3.0:
        ult = time.monotonic()
        d, a = correccion()
        if a is not None:
            giros.append(abs(a))
        print(f'    {ult-t0:5.1f}s  odom=({odom.get("x",0):+.3f},{odom.get("y",0):+.3f})'
              f'  amcl=({amcl.get("x",0):+.3f},{amcl.get("y",0):+.3f})'
              f'  map->odom {d:.3f}m {a:+6.2f}°  carga {carga():.1f}', flush=True)
bombear(3)

estado = fr.result().status if (fr.done() and fr.result()) else None
print(f'\n  DESENLACE: {FIN.get(estado, estado)}')

bombear(2)
d, a = correccion()
print(f'  duración {time.monotonic()-t0:.1f} s · carga final {carga():.2f}')
print(f'  odometría {math.hypot(odom.get("x",0), odom.get("y",0))*100:.1f} cm'
      f'   ·  AMCL {math.hypot(amcl.get("x",0), amcl.get("y",0))*100:.1f} cm'
      f'   (objetivo {META*100:.0f})')
if d is not None:
    print(f'  corrección map->odom  {d:.3f} m  {a:+.2f}°'
          + (f'  ·  yaw máx durante {max(giros):.2f}°' if giros else ''))

print()
if estado != 4:
    print('  🔴 NO MIDAS: el objetivo no terminó con éxito.')
    print('     journalctl -u atriz-nav --since "-3 min" | grep -iE "abort|timed|fail"')
else:
    print('  📏 MIDE ahora, marcando las cuatro esquinas y cruzando diagonales:')
    print('       AP = de A al centro final    ·    BP = de B al centro final')
    print()
    print('    python3 comparar_con_cinta.py  <AB> <AP> <BP> \\')
    print(f'        --odom {odom.get("x",0):.3f} {odom.get("y",0):.3f} '
          f'--amcl {amcl.get("x",0):.3f} {amcl.get("y",0):.3f}')
print('=' * 74)
n.destroy_node()
rclpy.shutdown()
