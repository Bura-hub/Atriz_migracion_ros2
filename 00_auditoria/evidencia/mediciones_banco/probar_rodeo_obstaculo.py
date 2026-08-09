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
✅ RESPUESTA, 2026-08-09 (evidencias 90 y 91) — Y LEE ESTO ANTES DE USARLO
═══════════════════════════════════════════════════════════════════════════════
**Era el montaje.** El MAPA engorda los objetos ~5 cm por lado: un hueco de 45 cm
entra en él como 35, la inflación del radio inscrito (14,5 cm) lo cierra, y NavFn
**traza un rodeo** de 168-233 % de largo que en un cuarto con 55 y 67 cm a los
lados no cabe. El rodeo roza la inflación, el controlador ve colisión, y
`failure_tolerance: 0.3` mata el objetivo en tres décimas.

    hueco mínimo ~ 2 x (14,5 inscrito + 5 engorde + 5 celda) ~ 49 cm

🔴 **Y LA LECCIÓN QUE VALE MÁS QUE EL RESULTADO: esto NO hacía falta medirlo
   moviendo el robot.** Ocho tandas, un choque y 66 puntos de batería no
   distinguieron «Nav2 traza recto y el robot no sigue» de «Nav2 traza un rodeo».
   Lo contestó `consultar_plan.py` en dos minutos, con el robot quieto.

✅ **Usa `consultar_plan.py` PRIMERO.** Este banco es para confirmar con el robot
   lo que la consulta ya haya señalado, no para descubrirlo.

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
from nav_msgs.msg import Odometry, OccupancyGrid, Path
from sensor_msgs.msg import LaserScan
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
# 🔴 LA VARIANTE CON SLAM NO PUEDE PASAR POR EL SUPERVISOR, y no es un rodeo:
#    es que `/pedir_nav` arranca `localizacion.launch.py` (AMCL), y el supervisor
#    RECHAZA hacerlo con SLAM vivo —«SLAM y AMCL son excluyentes»— porque los dos
#    publican `map -> odom`. Comprobado el 2026-08-09: la llamada devolvió ese
#    mensaje exacto y `slam` se quedó en APAGADO.
#    Con `--slam` el banco NO pide nada al supervisor y comprueba la navegación
#    por su EFECTO: que el servidor de acción `navigate_to_pose` responda. Da
#    igual quién la haya levantado.
p.add_argument('--slam', action='store_true',
               help='SLAM en vez de AMCL: no llama a /pedir_nav; espera al '
                    'servidor de acción, que es el efecto que importa')
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
    x=m.pose.pose.position.x, y=m.pose.pose.position.y,
    yaw=math.radians(yaw_de(m.pose.pose.orientation))), QT)
n.create_subscription(EstadoNavegacion, '/estado_navegacion',
                      lambda m: est.update(nav=m.nav, slam=m.slam), QT)
pub_ip = n.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
cli_odom = n.create_client(SetPosAndYaw, '/set_pos_and_yaw')
cli_nav = n.create_client(SetBool, '/pedir_nav')
cli_meta = ActionClient(n, NavigateToPose, 'navigate_to_pose')
# El costmap se guarda DURANTE toda la tanda para poder mirarlo en el instante
# del fallo, no antes (ver el décimo fallo del banco, más abajo).
cmap = []
n.create_subscription(
    OccupancyGrid, '/global_costmap/costmap', lambda m: cmap.append(m) or
    (cmap.pop(0) if len(cmap) > 2 else None),
    QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
               durability=QoSDurabilityPolicy.TRANSIENT_LOCAL))
# 🔴 EL PLAN, QUE ES LO QUE FALTABA. Las cuatro tandas del 2026-08-09 mostraron
#    al robot yéndose 56-77 cm de lado con el objetivo recto delante, y el banco
#    no podía distinguir dos cosas MUY distintas:
#      a) Nav2 traza recto por el hueco y el robot no lo sigue  -> problema de control
#      b) Nav2 traza un RODEO alrededor de la puerta            -> problema de coste
#    `/plan` lo dice sin ambigüedad. Se guarda el PRIMERO, que es el que decide.
planes = []
n.create_subscription(Path, '/plan', lambda m: planes.append(m), 10)
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

# 🔴🔴 CON SLAM VIVO NO SE PUEDE PONER LA ODOMETRÍA A CERO. Séptimo fallo de este
#    banco, cazado el 2026-08-09 mirando el mapa que salió.
#
#    `/set_pos_and_yaw` mueve el ORIGEN del marco `odom`. AMCL lo encaja —vuelve a
#    casar contra un mapa fijo y recalcula `map -> odom`—, pero slam_toolbox NO:
#    para él el robot se TELETRANSPORTA (aquí 29 cm y 15°) y sigue registrando
#    barridos desde un origen que se movió bajo sus pies.
#
#    El efecto, medido sobre el `/global_costmap/costmap` de esa tanda: el mapa
#    quedó EMBADURNADO —5 558 celdas desconocidas y casi todo lo demás LETAL—, con
#    el robot y el objetivo en dos bolsas libres separadas por un muro que no
#    existe. El planificador falló 8 veces, y no por la puerta.
#
#    El journal lo fecha: «11:03:35 odometría puesta a cero» con SLAM mapeando
#    desde las 10:58.
#
# ✅ En modo SLAM el objetivo se calcula RELATIVO a la odometría actual, sin
#    tocarla. Es la misma geometría —+meta metros sobre el rumbo de ahora— sin la
#    discontinuidad.
if a.slam:
    bombear(3)
    if 'x' not in odom:
        print('  🔴 sin /odom'); raise SystemExit(1)
    ORI = (odom['x'], odom['y'], odom.get('yaw', 0.0))
    print(f'  odometría NO se toca (SLAM viva): origen tomado en '
          f'({ORI[0]:+.4f}, {ORI[1]:+.4f}) yaw {math.degrees(ORI[2]):+.1f}°')
else:
    if not cli_odom.wait_for_service(timeout_sec=15):
        print('  🔴 /set_pos_and_yaw no responde'); raise SystemExit(1)
    req = SetPosAndYaw.Request(); req.yaw = 0.0
    llamar(cli_odom, req)
    bombear(2)
    ORI = (0.0, 0.0, 0.0)
if not a.slam:
    print(f'  odometría a cero: ({odom.get("x", 0):+.4f}, {odom.get("y", 0):+.4f})')

# 🔴 EL BARRIDO, ANTES DE PEDIR NADA. Sin `/scan` la navegación queda CIEGA y
#    este banco moría con «la navegación no llegó a funcionar» — que es cierto y
#    no dice por qué. Pasó el 2026-08-09: se apagó el barrido al medir la puerta
#    con el LIDAR y la tanda siguiente no arrancó. El estado del supervisor SÍ lo
#    decía («encendido pero SIN barrido»); el banco no lo miraba.
# 🔴 PERO SE MIRA EL EFECTO ANTES DE PEDIRLO, y no es cosmético: el 2026-08-09
#    `atriz-escaneo on` se colgó 30 s —y tumbó la tanda con una excepción— con el
#    barrido YA ENCENDIDO y llegando. Pedir a ciegas algo que ya está hecho añade
#    un modo de fallo que no existía.
scan = []
n.create_subscription(LaserScan, '/scan', lambda m: scan.append(m), QT)
bombear(3)
if scan:
    print(f'  barrido ya encendido: {len(scan)} barridos en 3 s, no se toca')
else:
    print('  sin /scan: pidiendo encendido...')
    try:
        subprocess.run(['/usr/local/bin/atriz-escaneo', 'on'],
                       capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        print('  ⚠️ atriz-escaneo no devolvió en 30 s; se comprueba /scan igualmente')
    scan.clear(); bombear(5)
    if not scan:
        print('  🔴 sigue sin llegar /scan: la navegación quedaría CIEGA')
        raise SystemExit(1)
    print(f'  barrido encendido: {len(scan)} barridos en 5 s')

if a.slam:
    # Sin supervisor: se comprueba el EFECTO —que el servidor de acción esté—,
    # no que un servicio haya devuelto `success=True`.
    if not cli_meta.wait_for_server(timeout_sec=60):
        print('  🔴 navigate_to_pose no responde: ¿está nav2.launch.py levantado?')
        raise SystemExit(1)
    bombear(2)
    print(f'  modo SLAM: servidor de acción listo · slam={est.get("slam")} '
          f'(2=FUNCIONANDO) · nav={est.get("nav")} (0=APAGADO, correcto aquí)')
elif not cli_nav.wait_for_service(timeout_sec=15):
    print('  🔴 /pedir_nav no responde'); raise SystemExit(1)
else:
    rq = SetBool.Request(); rq.data = True
    llamar(cli_nav, rq)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 150:
        bombear(0.5)
        if est.get('nav') in (2, 5):
            break
if not a.slam and est.get('nav') != 2:
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
# Objetivo = ORIGEN + `meta` metros sobre el rumbo que tenía el robot al empezar.
# Con la odometría a cero (modo AMCL) esto es literalmente (meta, 0); en modo SLAM
# la odometría NO se toca, así que hay que componerlo a mano.
g.pose.pose.position.x = ORI[0] + a.meta * math.cos(ORI[2])
g.pose.pose.position.y = ORI[1] + a.meta * math.sin(ORI[2])
g.pose.pose.orientation.z = math.sin(ORI[2] / 2.0)
g.pose.pose.orientation.w = math.cos(ORI[2] / 2.0)

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
    # 🔴 EL DESVÍO ES PERPENDICULAR AL RUMBO INICIAL, no `|y|` a secas: con la
    #    odometría sin poner a cero (modo SLAM) `y` incluye dónde estaba el robot.
    dx = odom.get('x', 0.0) - ORI[0]
    dy = odom.get('y', 0.0) - ORI[1]
    lat_max = max(lat_max, abs(-dx * math.sin(ORI[2]) + dy * math.cos(ORI[2])))
    if time.monotonic() - ult >= 5.0:
        ult = time.monotonic()
        print(f'    {ult-t0:5.1f}s  odom=({odom.get("x",0)-ORI[0]:+.3f},{odom.get("y",0)-ORI[1]:+.3f})'
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
# 🔴 NOVENO FALLO DEL BANCO, y salta a la vista por absurdo: con `--slam` la
#    odometría NO se pone a cero, así que `odom.x` a secas es la posición ABSOLUTA,
#    no lo avanzado. El 2026-08-09 imprimió «avance 233,5 cm» para una tanda de
#    5,7 s — imposible a 0,26 m/s de tope. El avance es la PROYECCIÓN del
#    desplazamiento sobre el rumbo inicial.
_dx = odom.get('x', 0.0) - ORI[0]
_dy = odom.get('y', 0.0) - ORI[1]
avance = _dx * math.cos(ORI[2]) + _dy * math.sin(ORI[2])
print(f'\n  DESENLACE: {FIN.get(estado, estado)}')
print(f'  avance {avance*100:.1f} cm de {a.meta*100:.0f}  ·  desvío lateral máx '
      f'{lat_max*100:.1f} cm  ·  {time.monotonic()-t0:.1f} s')

# 🔴 DÉCIMO FALLO DEL BANCO: medía el costmap ANTES de mandar el objetivo, y eso
#    no vale para explicar un aborto. El 2026-08-09 se midió «robot coste 0,
#    objetivo coste 0, corredor máximo 96 -> transitable» y dos minutos después
#    `planner_server` dijo «failed to plan» DESDE ESA MISMA POSE. El costmap se
#    mueve: la capa de obstáculos se remarca cada ciclo. Hay que mirarlo EN EL
#    INSTANTE DEL FALLO.
# 📌 99 = radio inscrito: para NavFn es tan intransitable como 100. El umbral que
#    importa NO es 100.
if cmap:
    G = cmap[-1]; I = G.info; res = I.resolution
    gx = ORI[0] + a.meta * math.cos(ORI[2])
    gy = ORI[1] + a.meta * math.sin(ORI[2])
    rx, ry = odom.get('x', 0.0), odom.get('y', 0.0)

    def _cel(x, y):
        i = int((x - I.origin.position.x) / res)
        j = int((y - I.origin.position.y) / res)
        if not (0 <= i < I.width and 0 <= j < I.height):
            return None
        return G.data[j * I.width + i]

    def _et(c):
        if c is None:
            return 'FUERA'
        if c == -1:
            return 'desconocido'
        return f'INTRANSITABLE({c})' if c >= 99 else f'{c}'

    d = G.data; tot = len(d); A = res * res
    print(f'  costmap al terminar: LIBRE {d.count(0) * A:.2f} m2 · '
          f'INTRANSITABLE {sum(1 for v in d if v >= 99) * A:.2f} m2 · '
          f'desconocido {d.count(-1) * A:.2f} m2')
    if planes:
        pl = planes[0]
        pts = [(q.pose.position.x, q.pose.position.y) for q in pl.poses]
        if pts:
            # desviación perpendicular al rumbo inicial, en el marco del plan
            lat = [abs(-(x - pts[0][0]) * math.sin(ORI[2])
                       + (y - pts[0][1]) * math.cos(ORI[2])) for x, y in pts]
            adv = [(x - pts[0][0]) * math.cos(ORI[2])
                   + (y - pts[0][1]) * math.sin(ORI[2]) for x, y in pts]
            largo = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            print(f'  🗺️ PRIMER PLAN ({len(planes)} planes en total, marco '
                  f'{pl.header.frame_id}): {len(pts)} puntos, largo {largo * 100:.0f} cm '
                  f'para {a.meta * 100:.0f} cm en línea recta')
            print(f'     desviación lateral MÁXIMA DEL PLAN: {max(lat) * 100:.1f} cm')
            print('     🔴 el plan RODEA la puerta, no pasa por el hueco'
                  if max(lat) > 0.30 else
                  '     ✅ el plan va por el hueco (desviación < 30 cm)')
            print('     perfil (avance cm -> lateral cm): '
                  + '  '.join(f'{adv[k] * 100:.0f}->{lat[k] * 100:.0f}'
                              for k in range(0, len(pts), max(1, len(pts) // 8))))
    else:
        print('  ⚠️ no llegó ningún /plan: el planificador no produjo NADA')
    print(f'  corredor robot({rx:+.2f},{ry:+.2f}) -> objetivo({gx:+.2f},{gy:+.2f}): '
          + ' '.join(_et(_cel(rx + (gx - rx) * k / 10, ry + (gy - ry) * k / 10))
                     for k in range(11)))
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
