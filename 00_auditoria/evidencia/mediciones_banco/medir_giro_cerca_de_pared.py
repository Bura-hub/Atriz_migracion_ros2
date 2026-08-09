#!/usr/bin/env python3
"""¿Gira peor el robot con una pared cerca? — hipótesis del usuario, 2026-08-09.

    python3 medir_giro_cerca_de_pared.py <etiqueta> [--vueltas 2] [--grados 360]

🔴 GIRA EL ROBOT SOBRE SU EJE. No se desplaza, así que no puede chocar — pero
   avisa a quien esté delante.

═══════════════════════════════════════════════════════════════════════════════
LA HIPÓTESIS, Y POR QUÉ NO SE DESCARTA DE ENTRADA
═══════════════════════════════════════════════════════════════════════════════
El usuario, viendo un giro de 360° que acabó 12,6° desviado:

    «existe buena precisión del sistema, pero cuando encuentra un obstáculo
     cercano se atrofia; en comparación con la práctica de giro preciso, que en
     lazo cerrado hacía giros muy precisos»

📌 **Esa tanda concreta NO la prueba**, y la aritmética lo dice sin experimento:

       giro acumulado medido en /odom   357,5°
       inercia tras dejar de mandar     ~15°   (0,4 s a 0,5 rad/s + rampa)
       357,5 + 15 = 372,5 = 360 + 12,5   ->  coincide con los +12,6 medidos

   Fue una **parada en lazo abierto escrita a mano**, no `girar()`. `girar()` es
   lazo cerrado con el sobregiro medido y da 87,9 / 174,2 / **357,8°** en F5.

🔎 **PERO LA HIPÓTESIS TIENE UN MECANISMO REAL, y por eso se mide en vez de
   argumentarse:** `girar()` publica en `/cmd_vel_raw`, o sea **pasa por el
   `collision_monitor`**, que tiene un polígono de frenado

       [[0.36, 0.20], [0.36, -0.20], [-0.24, -0.20], [-0.24, 0.20]]
       action_type: slowdown · slowdown_ratio: 0.4 · min_points: 4

   36 cm por delante, 24 por detrás, ±20 a los lados. Si al girar entra pared en
   ese polígono, **la velocidad cae al 40 %** — y un perfil de deceleración
   distinto es exactamente lo que cambia el sobregiro. Ya está documentado que
   este monitor frenó al robot al 40 % y pareció un atasco.

✅ **Y el mediador es OBSERVABLE**: `/collision_monitor_state` dice si actuó y con
   qué polígono. Así la prueba no responde solo «¿pasa?» sino «¿por qué?».

═══════════════════════════════════════════════════════════════════════════════
EL DISEÑO
═══════════════════════════════════════════════════════════════════════════════
Dos condiciones, con el MISMO instrumento (`girar()`), n≥2 cada una:

    CERCA   algo dentro del polígono de frenado (≤36 delante / ≤24 detrás / ≤20 lados)
    LEJOS   nada dentro de él

Y se registra, por tanda:
    · error de rumbo tras el giro, medido en /odom
    · deslizamiento (debe ser ~0: si no, no fue un giro en el sitio)
    · si `/collision_monitor_state` cambió, y a qué
    · la distancia mínima dentro del polígono, con el LIDAR

🔴 La condición la MIDE el guion con el LIDAR, no la declara el operador: «cerca»
   tiene que ser un número, o las dos condiciones no se distinguen.

🔴🔴 Y SE MIDE DURANTE TODA LA VUELTA, NO SOLO ANTES. Primer fallo de este banco,
   cazado en su primera tanda el 2026-08-09: se etiquetó una tanda como «LEJOS»
   mirando una foto inicial que decía «0 puntos dentro del polígono», y el monitor
   **frenó en las dos vueltas**. El polígono es rectangular y GIRA CON EL ROBOT,
   así que un punto a 25 cm que empieza fuera entra a mitad de vuelta.
   Lo destapó el usuario: «no encontraste diferenciación porque no había
   variación». Ahora se registra el MÍNIMO durante el giro y qué fracción del
   tiempo estuvo el monitor actuando.
"""
import argparse
import math
import sys
import threading
import time

sys.path.insert(0, '/home/sphero/atriz_ws/src/Atriz_rvr/scripts/estudiantes')

import rclpy                                                     # noqa: E402
from rclpy.node import Node                                      # noqa: E402
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile,          # noqa: E402
                       QoSReliabilityPolicy)
from nav_msgs.msg import Odometry                                # noqa: E402
from sensor_msgs.msg import LaserScan                            # noqa: E402
from nav2_msgs.msg import CollisionMonitorState                  # noqa: E402
from rclpy.signals import SignalHandlerOptions                   # noqa: E402

import atriz                                                     # noqa: E402

p = argparse.ArgumentParser()
p.add_argument('etiqueta', help='CERCA o LEJOS, o lo que describa el montaje')
p.add_argument('--vueltas', type=int, default=2)
p.add_argument('--grados', type=float, default=360.0)
# 🔴🔴 SALTARSE EL collision_monitor, A PROPOSITO Y CON EL USUARIO MIRANDO.
#    `atriz.py` publica en `/cmd_vel_raw`, que ENTRA al monitor; `/cmd_vel` es su
#    SALIDA, así que publicar ahí lo puentea. Normalmente eso es un error grave
#    —el propio atriz.py lo advierte— y aquí es EL EXPERIMENTO: con la pared a
#    16,8 cm el monitor anula avanzar, retroceder Y girar, y hay que saber si el
#    robot podría girar sin él o si de verdad tocaría la pared.
#
#    🔎 El número que importa girando NO es el borde trasero: es el RADIO
#       CIRCUNSCRITO (18x22 cm -> 14,2 cm), porque lo que barre son las esquinas.
#       Con la pared a 16,8 cm del LIDAR el margen es ~2,6 cm.
#
# 🔴 SOLO con una persona mirando el robot. Sin monitor no hay nada que lo pare.
p.add_argument('--sin-monitor', action='store_true',
               help='publica en /cmd_vel (salta el collision_monitor). PELIGROSO: '
                    'exige a alguien vigilando')
a = p.parse_args()

QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT,
                durability=QoSDurabilityPolicy.VOLATILE)

# El polígono de frenado del collision_monitor, en metros y en el marco del robot.
ADELANTE, ATRAS, LADO = 0.36, -0.24, 0.20

ACCION = {0: 'ninguna', 1: 'PARADA', 2: 'FRENADO', 3: 'APROXIMACION', 4: 'LIMITE'}


def dentro_del_poligono(x, y):
    return ATRAS <= x <= ADELANTE and abs(y) <= LADO


# ⚠️ `SignalHandlerOptions.NO` es obligatorio en cualquier herramienta de este
#    proyecto que pueda pararse con Ctrl-C: sin él, rclpy secuestra la señal y el
#    robot puede quedarse en marcha.
rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
n = Node('medir_giro_pared')
odom, escena, estados = {}, {}, []
vigilando = {}          # se llena solo mientras dura una vuelta


def cb_odom(m):
    q = m.pose.pose.orientation
    y = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))
    # 🔴🔴 TERCER FALLO DEL BANCO, Y EL PEOR: LA MÉTRICA NO DISTINGUÍA «GIRÓ 360»
    #    DE «NO SE MOVIÓ». Se medía `wrap(yaw_final - yaw_inicial)` contra un
    #    pedido de `((360+180) % 360) - 180 = 0`. Una vuelta completa da 0 y estar
    #    quieto también da 0: las dos salían con «error 0,0°».
    #    El 2026-08-09 imprimió «error -0,1°» tres veces seguidas con el robot
    #    PARADO contra una pared, y lo paró el usuario mirándolo: «es que el robot
    #    ni siquiera giró».
    # ✅ Hay que INTEGRAR el giro acumulado, no restar rumbos.
    if odom:
        d = y - odom['yaw']
        odom['acum'] = odom.get('acum', 0.0) + abs(math.atan2(math.sin(d),
                                                              math.cos(d)))
    odom.update(x=m.pose.pose.position.x, y=m.pose.pose.position.y, yaw=y)


def cb_scan(m):
    dentro, minimo, dmin = 0, 9.9, None
    for i, r in enumerate(m.ranges):
        if not (m.range_min < r < m.range_max) or math.isinf(r) or math.isnan(r):
            continue
        ang = m.angle_min + i * m.angle_increment
        x, y = r * math.cos(ang), r * math.sin(ang)
        if dentro_del_poligono(x, y):
            dentro += 1
            if r < minimo:
                minimo, dmin = r, (x, y)
    cerca = min((r for r in m.ranges
                 if m.range_min < r < m.range_max), default=None)
    escena.update(dentro=dentro, minimo=(minimo if dentro else None), punto=dmin,
                  cerca=cerca)
    if vigilando and cerca is not None:
        vigilando['min'] = min(vigilando.get('min', 9.9), cerca)
        vigilando['dentro_max'] = max(vigilando.get('dentro_max', 0), dentro)
        vigilando['muestras'] = vigilando.get('muestras', 0) + 1
        if dentro:
            vigilando['con_puntos'] = vigilando.get('con_puntos', 0) + 1


n.create_subscription(Odometry, '/odom', cb_odom, QT)
n.create_subscription(LaserScan, '/scan', cb_scan, QT)
n.create_subscription(CollisionMonitorState, '/collision_monitor_state',
                      lambda m: estados.append((time.time(), m.action_type,
                                                m.polygon_name)), 10)


def bombear(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.02)


print('=' * 76)
print(f' GIRO CON PARED CERCA · {a.etiqueta} · {a.vueltas} x {a.grados:.0f}°')
print(' 🔴 EL ROBOT GIRA SOBRE SU EJE (no se desplaza)')
print('=' * 76)

bombear(4)
if 'dentro' not in escena:
    print('  🔴 sin /scan: enciende el barrido'); raise SystemExit(1)
if 'yaw' not in odom:
    print('  🔴 sin /odom'); raise SystemExit(1)

# 🔴 LA CONDICION SE MIDE, NO SE DECLARA.
print(f'  ESCENA · lo más cercano en todo el barrido: {escena["cerca"]*100:.1f} cm')
print(f'           puntos DENTRO del polígono de frenado: {escena["dentro"]}'
      f'   (frena con min_points=4)')
if escena['minimo'] is not None:
    print(f'           el más cercano dentro: {escena["minimo"]*100:.1f} cm '
          f'en ({escena["punto"][0]*100:+.0f},{escena["punto"][1]*100:+.0f}) cm')
    print('           -> condición CERCA (el monitor puede frenar)')
else:
    print('           -> condición LEJOS (nada dentro del polígono)')

if a.sin_monitor:
    atriz.TOPIC_MANDO = '/cmd_vel'          # se lee al crear el publicador
    print('  🔴🔴 SIN collision_monitor: se publica en /cmd_vel.')
    print('       NO HAY NADA QUE PARE AL ROBOT. Alguien tiene que estar mirando.')
rb = atriz.Robot()
try:
    for v in range(1, a.vueltas + 1):
        bombear(2)
        y0, x0, p0 = odom['yaw'], odom['x'], odom['y']
        estados.clear()
        vigilando.clear()
        vigilando['activo'] = True
        t0 = time.time()
        # 🔴 SEGUNDO FALLO DEL BANCO: `girar()` BLOQUEA EL HILO PRINCIPAL, así que
        #    mientras dura la vuelta este nodo no gira y NO LLEGA NI UN BARRIDO.
        #    La primera versión imprimía `vmin = None` — o sea, medía la vuelta
        #    justo cuando no estaba mirando. Se lanza el giro en un hilo y se
        #    bombea aquí.
        # `girar()` DEVUELVE los grados que realmente giró. Se captura: es una
        # tercera vista independiente, y en la primera versión se tiraba.
        devuelto = []
        odom['acum'] = 0.0
        hilo = threading.Thread(
            target=lambda: devuelto.append(rb.girar(a.grados)), daemon=True)
        hilo.start()
        while hilo.is_alive():
            rclpy.spin_once(n, timeout_sec=0.0)
            time.sleep(0.01)
        hilo.join(timeout=5)
        vmin = vigilando.get('min')
        vfrac = (100.0 * vigilando.get('con_puntos', 0)
                 / max(vigilando.get('muestras', 1), 1))
        vigilando.clear()
        bombear(3)
        # error = cuánto se pasó o se quedó corto respecto al giro pedido
        acum = math.degrees(odom.get('acum', 0.0))       # ← LA MEDIDA BUENA
        neto = math.degrees(math.atan2(math.sin(odom['yaw'] - y0),
                                       math.cos(odom['yaw'] - y0)))
        err = math.radians(acum - abs(a.grados))
        desliz = math.hypot(odom['x'] - x0, odom['y'] - p0)
        dev = devuelto[0] if devuelto else None
        acciones = sorted({ACCION.get(t, t) for _, t, _ in estados if t != 0})
        pol = sorted({q for _, t, q in estados if t != 0 and q})
        tardanza = time.time() - t0
        print(f'  {v}. GIRÓ {acum:7.1f}° de {abs(a.grados):.0f} pedidos '
              f'(error {math.degrees(err):+.1f}°)  ·  girar() devolvió '
              f'{"?" if dev is None else f"{dev:.1f}°"}  ·  rumbo neto '
              f'{neto:+.1f}°  ·  deslizamiento {desliz*100:.1f} cm  ·  '
              f'{tardanza:.1f} s'
              + ('   🔴 PLAZO AGOTADO (límite ~36,4 s para 360°)'
                 if tardanza > 35 else ''))
        print(f'     DURANTE la vuelta: lo más cercano '
              f'{"?" if vmin is None else f"{vmin*100:.1f}"} cm'
              f'   ·  polígono ocupado el {vfrac:.0f} % del tiempo'
              f'   ·  monitor: {", ".join(acciones) if acciones else "no actuó"}'
              + (f' [{", ".join(pol)}]' if pol else ''))
finally:
    try:
        rb.cerrar()
    except Exception:                                            # noqa: BLE001
        pass

print('=' * 76)
