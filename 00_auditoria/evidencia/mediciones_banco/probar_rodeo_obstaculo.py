#!/usr/bin/env python3
"""¿Cuánto hueco necesita Nav2 para rodear un obstáculo en este robot?

    python3 probar_rodeo_obstaculo.py <etiqueta> [--meta 1.4] [--plazo 90]

🔴 MUEVE EL ROBOT hasta `--meta` metros hacia delante.

═══════════════════════════════════════════════════════════════════════════════
DE DÓNDE SALE ESTA PREGUNTA
═══════════════════════════════════════════════════════════════════════════════
La prueba de aceptación del 2026-08-08 dejó **un solo FALLO** en 74
comprobaciones: el objetivo CON obstáculo dio `ABORTED`. Se miró el journal
—porque ese mismo día se descubrió que `ABORTED` puede ser mentira— y no lo era:

    planner_server: [compute_path_to_pose] Aborting handle   × 8
    behavior_server: spin -> backup (failed) -> spin
    bt_navigator: Goal failed

**Falla el PLANIFICADOR: no había plan que ejecutar.** Y quedó sin saber si es un
defecto del robot o **un montaje demasiado justo** — el cuarto son 3,8 × 4,2 m.

📌 **Y los números con los que se iba a diseñar la repetición eran DERIVADOS, no
   medidos.** De la configuración salen dos cosas con respaldo distinto:

     robot_radius     0.145  ✅ MEDIDO con cinta (18 x 22 cm -> circunscrito 0.142)
     inflation_radius 0.25   ⚠️ razonado, no medido

   y de ahí se dedujo «hueco mínimo 29 cm, cómodo 50». **Eso es un modelo de cómo
   se comporta la capa de inflación, no una medida de este robot.** Puede fallar
   por `cost_scaling_factor` o porque NavFn se rinda antes.

✅ **Así que en vez de usar esos números como criterio, este banco los MIDE**:
   se estrecha el hueco tanda a tanda y se busca dónde deja de planificar.

═══════════════════════════════════════════════════════════════════════════════
EL PROTOCOLO, Y POR QUÉ EN ESE ORDEN
═══════════════════════════════════════════════════════════════════════════════
  1. CONTROL, sin obstáculo, al mismo objetivo
  2. hueco ancho   (~60 cm)
  3. hueco medio   (~45 cm)
  4. hueco estrecho(~30 cm)

🔴 **El control va PRIMERO y no es una formalidad.** Sin él, «no planificó» sería
   indistinguible de «el objetivo no era alcanzable», y todo lo demás no
   concluiría nada. Es la misma lección que el 2x2 del sensor de color: la
   casilla que parece sobrar es la que sostiene el resultado.

📌 **Y de ancho a estrecho, no al revés.** Si el ancho ya falla, los estrechos no
   añaden información y se para: el problema no es la geometría.
"""
import argparse
import math
import subprocess
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener
from std_srvs.srv import SetBool
from atriz_rvr_msgs.msg import EstadoNavegacion
from atriz_rvr_msgs.srv import SetPosAndYaw

p = argparse.ArgumentParser()
p.add_argument('etiqueta')
p.add_argument('--meta', type=float, default=1.4)
p.add_argument('--plazo', type=float, default=90.0)
p.add_argument('--ocio-min', type=float, default=15.0,
               help='%% de CPU ociosa mínimo antes de mandar el objetivo')
a = p.parse_args()

QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)
FIN = {4: '✅ CON ÉXITO', 5: '🔴 CANCELADO', 6: '🔴 ABORTADO'}


def yaw_de(q):
    return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y),
                                   1 - 2 * (q.y ** 2 + q.z ** 2)))


rclpy.init()
n = Node('probar_rodeo')
odom, est = {}, {}
n.create_subscription(Odometry, '/odom', lambda m: odom.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y), QT)
n.create_subscription(EstadoNavegacion, '/estado_navegacion',
                      lambda m: est.update(nav=m.nav), QT)
pub_ip = n.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
cli_odom = n.create_client(SetPosAndYaw, '/set_pos_and_yaw')
cli_nav = n.create_client(SetBool, '/pedir_nav')
cli_meta = ActionClient(n, NavigateToPose, 'navigate_to_pose')
buf = Buffer(); TransformListener(buf, n)


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.02)


def llamar(cli, req, seg=20.0):
    f = cli.call_async(req)
    rclpy.spin_until_future_complete(n, f, timeout_sec=seg)
    return f.result()


print('=' * 76)
print(f' RODEO DE OBSTÁCULO · {a.etiqueta} · objetivo +{a.meta:.2f} m')
print('=' * 76)

t_ini = time.strftime('%Y-%m-%dT%H:%M:%S%z')

if not cli_odom.wait_for_service(timeout_sec=15):
    print('  🔴 /set_pos_and_yaw no responde'); raise SystemExit(1)
req = SetPosAndYaw.Request(); req.yaw = 0.0
llamar(cli_odom, req)
bombear(2)
print(f'  odometría a cero: ({odom.get("x", 0):+.4f}, {odom.get("y", 0):+.4f})')

# 🔴 EL BARRIDO, ANTES DE PEDIR NADA. Sin `/scan` la navegación queda CIEGA y
#    este banco moría con «la navegación no llegó a funcionar» — que es cierto y
#    no dice por qué. Pasó el 2026-08-09: se apagó el barrido al medir la puerta
#    con el LIDAR y la tanda siguiente no arrancó. El estado del supervisor SÍ lo
#    decía («encendido pero SIN barrido»); el banco no lo miraba.
subprocess.run(['/usr/local/bin/atriz-escaneo', 'on'], capture_output=True, timeout=30)
time.sleep(2.0)

if not cli_nav.wait_for_service(timeout_sec=15):
    print('  🔴 /pedir_nav no responde'); raise SystemExit(1)
rq = SetBool.Request(); rq.data = True
llamar(cli_nav, rq)
t0 = time.monotonic()
while time.monotonic() - t0 < 150:
    bombear(0.5)
    if est.get('nav') in (2, 5):
        break
if est.get('nav') != 2:
    # 🔴 Y se dice CUÁL es el estado, no solo que no es el bueno. «No llegó a
    #    funcionar» manda a mirar Nav2; «CIEGO» manda a encender el barrido.
    NOM = {0: 'APAGADO', 1: 'ARRANCANDO', 2: 'FUNCIONANDO', 3: 'CIEGO',
           4: 'MUDO', 5: 'FALLO', 6: 'DESCONOCIDO'}
    print(f'  🔴 la navegación está en {NOM.get(est.get("nav"), est.get("nav"))}, '
          f'no en FUNCIONANDO')
    raise SystemExit(1)

import os


def ocio_cpu(muestra=1.0):
    """% de CPU OCIOSA, leído de /proc/stat. NO `load average`.

    🔴 `os.getloadavg()` NO mide saturación de CPU en esta máquina. Medido el
       2026-08-09 con `vmstat` y `top` mientras el load average marcaba 8,85:

           r = 8-18 ejecutables · b = 0 bloqueados · wa = 0,0 %
           CPU 60-75 % usada · 25-39 % OCIOSA · 10 500 cambios de contexto/s

       O sea: la carga la inflan MUCHOS HILOS despertándose a menudo —la firma
       de ROS 2 con doce nodos y sus temporizadores— no CPU agotada ni espera de
       disco. Un umbral de «load < 4» aquí es INALCANZABLE con Nav2 arrancado, y
       este banco se pasaba 90 s esperándolo para seguir igual.

    📌 Y esto retira una explicación anterior: el 2026-08-07 los abortos de Nav2
       se atribuyeron a «la Pi saturada, load 8,39». La causa real era
       `default_server_timeout: 20` (evidencia 88), y ahora se ve que la Pi
       tampoco estaba saturada. El instrumento estaba mal leído.
    """
    def leer():
        with open('/proc/stat') as f:
            v = [int(x) for x in f.readline().split()[1:]]
        return sum(v), v[3]          # total, idle
    t0, i0 = leer()
    time.sleep(muestra)
    t1, i1 = leer()
    return 100.0 * (i1 - i0) / max(t1 - t0, 1)


t0 = time.monotonic()
while ocio_cpu(0.5) < a.ocio_min and time.monotonic() - t0 < 60:
    bombear(2)
ocio = ocio_cpu(1.0)
print(f'  CPU ociosa al mandar el objetivo: {ocio:.0f} %'
      f'   (load average {os.getloadavg()[0]:.1f}, que aquí NO mide saturación)')

# 🔴🔴 AQUÍ NO SE PUBLICA `/initialpose`, Y ES DELIBERADO.
#    La primera versión lo publicaba en (0,0) copiando el banco de navegación
#    —donde el robot SÍ arranca sobre el origen del mapa, la marca A—. Aquí no:
#    el robot está donde lo dejó la tanda anterior. Decirle a AMCL «estás en el
#    origen» es MENTIRLE, y se notó:
#
#      objetivo    1,40 m por delante
#      avance real 2,085 m   (y el control, 2,068 — casi idéntico)
#
#    Esa coincidencia lo delata: el robot recorría hasta un PUNTO FIJO del mapa,
#    no 1,4 m desde donde estaba. AMCL aceptaba la pose falsa un instante, el
#    casado de barridos la corregía ~0,7 m atrás, y el robot se comía la
#    diferencia.
#
# 📌 AMCL ya está localizado —lleva rato corriendo y siguiendo al robot—, así que
#    forzarle una pose no aporta nada y estropea la geometría del experimento.
#    `set_initial_pose: true` de su configuración ya cubre el arranque.
bombear(2)

if not cli_meta.wait_for_server(timeout_sec=20):
    print('  🔴 /navigate_to_pose no responde'); raise SystemExit(1)
# 🔴 EL OBJETIVO ES RELATIVO A DONDE ESTÁ EL ROBOT, no absoluto en el mapa.
#    La primera versión mandaba `map (meta, 0)` a secas, y el CONTROL lo cazó:
#    con el robot en x = -0,67 del mapa, un objetivo en x = 1,4 son **2,07 m de
#    recorrido real** en vez de 1,4. Para el control daba igual —llegó— pero para
#    las tandas del obstáculo lo invalidaría todo: la geometría que se diseña
#    (obstáculo a 70 cm, meta a 140) no sería la que ocurre.
#    📌 La prueba de aceptación ya lo hacía bien: «objetivo +1.50 m sobre el rumbo
#       actual». Aquí se copia ese criterio.
# 🔴🔴 EL OBJETIVO VA EN EL MARCO `odom`, NO EN `map`. Y esto es un resultado,
#    no una comodidad.
#
#    La versión anterior leía la pose en `map` y ponía el objetivo a +1,4 m de
#    ahí. Pero la pose en `map` la da AMCL, y AMCL se equivoca: dos tandas
#    seguidas con el robot FÍSICAMENTE EN EL MISMO SITIO dieron
#
#        yaw  +1°   y luego   yaw -26°
#
#    🔎 Y que el robot no se movió lo dice el LIDAR, que es independiente: la
#       puerta —que nadie tocó— apareció con el hueco centrado en y=+28 y luego
#       en y=+32. Con un giro real de 26°, a 0,9 m de distancia, ese centro
#       habría saltado a ~+67 cm. **Quien giró fue la estimación, no el robot.**
#
#    Consecuencia: pedir «1,4 m hacia delante» calculado sobre una pose torcida
#    26° manda el objetivo a otro sitio, y el recorrido real salía 56 cm largo.
#
# ✅ `odom` no tiene ese problema: la odometría de este robot está medida contra
#    cinta cuatro veces —1,5 · 4,2 · 2,2 · 0,3 cm— y en 1,4 m no deriva nada
#    apreciable. Con la odometría recién puesta a cero, «+1,4 m hacia delante» es
#    literalmente `odom (1.4, 0)`.
#
# ⚠️ Nav2 lo transforma a `map` para planificar, así que AMCL sigue en el camino
#    del CONTROL — pero ya no define DÓNDE está el objetivo, que es lo que
#    contaminaba la geometría.
print(f'  objetivo: odom ({a.meta:+.2f}, 0.00)  =  +{a.meta:.2f} m hacia delante, '
      f'medido por odometría')
try:
    tr = buf.lookup_transform('map', 'base_footprint', rclpy.time.Time())
    print(f'  (AMCL cree estar en ({tr.transform.translation.x:+.3f}, '
          f'{tr.transform.translation.y:+.3f}) yaw {yaw_de(tr.transform.rotation):+.0f}° '
          f'— se anota, NO se usa)')
except Exception:                                                # noqa: BLE001
    pass

g = NavigateToPose.Goal()
g.pose.header.frame_id = 'odom'
g.pose.pose.position.x = a.meta
g.pose.pose.position.y = 0.0
g.pose.pose.orientation.w = 1.0

print('\n  🔴 OBJETIVO ENVIADO. EL ROBOT SE MUEVE.\n', flush=True)
t0 = time.monotonic()
fg = cli_meta.send_goal_async(g)
rclpy.spin_until_future_complete(n, fg, timeout_sec=25)
gh = fg.result()
if gh is None or not gh.accepted:
    print('  🔴 objetivo RECHAZADO'); raise SystemExit(1)

def correccion():
    """`map -> odom`: cuánto está corrigiendo AMCL. 0 = se fía de la odometría."""
    try:
        t = buf.lookup_transform('map', 'odom', rclpy.time.Time())
        tr = t.transform.translation
        return math.hypot(tr.x, tr.y), yaw_de(t.transform.rotation)
    except Exception:                                            # noqa: BLE001
        return None, None


# 🔴 SE REGISTRA `map -> odom` AL PRINCIPIO Y AL FINAL, y es lo que explica el
#    sobrepaso. El objetivo se manda en `odom`, pero Nav2 lo transforma a `map`
#    UNA VEZ y luego conduce hasta ese punto del mapa. Si AMCL corrige durante el
#    trayecto, el punto se mueve respecto al mundo real, y el robot recorre de
#    más o de menos exactamente esa cantidad.
corr_ini = correccion()
fr = gh.get_result_async()
# 🔴 EL DESVÍO LATERAL es lo que prueba que RODEÓ y no que fue recto o se quedó
#    girando. Sin él, «llegó» no distingue un rodeo de un camino libre.
lat_max, ult = 0.0, 0.0
while not fr.done() and time.monotonic() - t0 < a.plazo:
    rclpy.spin_once(n, timeout_sec=0.0)
    time.sleep(0.05)
    lat_max = max(lat_max, abs(odom.get('y', 0.0)))
    if time.monotonic() - ult >= 5.0:
        ult = time.monotonic()
        print(f'    {ult-t0:5.1f}s  odom=({odom.get("x",0):+.3f},{odom.get("y",0):+.3f})'
              f'  desvío máx {lat_max*100:.1f} cm  carga {os.getloadavg()[0]:.1f}', flush=True)
# 🔴 SI SE AGOTA EL PLAZO, SE CANCELA EL OBJETIVO. La primera versión salía sin
#    cancelar: el banco terminaba, imprimía «DESENLACE: None», y **Nav2 seguía
#    intentándolo con el robot suelto**. Pasó el 2026-08-09 en la tanda de 30 cm.
#    Un banco que deja el robot en marcha al terminar es peor que uno que falla.
if not fr.done():
    print('  ⚠️ plazo agotado: CANCELANDO el objetivo')
    fc = gh.cancel_goal_async()
    rclpy.spin_until_future_complete(n, fc, timeout_sec=10)
    bombear(3)

bombear(3)

estado = fr.result().status if (fr.done() and fr.result()) else None
avance = odom.get('x', 0.0)
print(f'\n  DESENLACE: {FIN.get(estado, estado)}')
print(f'  avance {avance*100:.1f} cm de {a.meta*100:.0f}  ·  desvío lateral máx '
      f'{lat_max*100:.1f} cm  ·  {time.monotonic()-t0:.1f} s')
# 🔴 Y SE COMPRUEBA QUE LA GEOMETRÍA FUE LA QUE SE PIDIÓ. Si el recorrido real se
#    aleja mucho del objetivo, el experimento midió otra cosa -- pasó el
#    2026-08-09 con `/initialpose` mintiéndole a AMCL: 2,08 m para un objetivo de
#    1,40. Sin este aviso, el número se habría escrito como si fuera bueno.
bombear(2)
corr_fin = correccion()
if corr_ini[0] is not None and corr_fin[0] is not None:
    print(f'  corrección map->odom:  {corr_ini[0]:.3f} m {corr_ini[1]:+.1f}°  ->  '
          f'{corr_fin[0]:.3f} m {corr_fin[1]:+.1f}°   (AMCL se movió '
          f'{abs(corr_fin[0]-corr_ini[0])*100:.0f} cm durante el trayecto)')

desv = abs(avance - a.meta)
if desv > 0.20:
    print(f'  🔴 EL RECORRIDO NO ES EL PEDIDO: {desv*100:.0f} cm de diferencia. '
          f'La geometría del montaje NO es la que se diseñó — no compares esta '
          f'tanda con otras sin mirar por qué.')

# 🔴 Y LO QUE DECIDE EL DIAGNÓSTICO: quién abortó. Un ABORTED del planificador
#    («no hay plan») y uno del acuse («no llegó la confirmación, y el robot
#    llegó igual») son fallos COMPLETAMENTE distintos, y el desenlace de la
#    acción no los separa. Evidencia 88.
try:
    log = subprocess.run(
        ['journalctl', '-u', 'atriz-nav', '--no-pager', '--since', t_ini],
        capture_output=True, text=True, timeout=30).stdout
    plan = log.count('compute_path_to_pose') and log.count('Aborting handle')
    acuse = log.count('acknowledge goal request')
    print(f'  journal: planner_server abortó {log.count("[compute_path_to_pose] [ActionServer] Aborting handle")} vez/veces'
          f'  ·  acuse agotado {acuse}  ·  recuperaciones: '
          f'spin={log.count("Running spin")} backup={log.count("Running backup")}')
except Exception as e:                                           # noqa: BLE001
    print(f'  ⚠️ no se pudo leer el journal: {e}')

print('=' * 76)
n.destroy_node()
rclpy.shutdown()
