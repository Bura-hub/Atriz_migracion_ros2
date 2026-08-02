#!/usr/bin/env python3
"""¿La parada de emergencia deja el robot quieto DESPUÉS de liberarla?

    # con robot.launch.py y nav2.launch.py ya corriendo:
    python3 medir_parada_nav2.py --distancia 2.0

⚠️ MUEVE EL ROBOT. Necesita ~2.5 m despejados por delante.

═══════════════════════════════════════════════════════════════════════════════
QUÉ MIDE, Y POR QUÉ ESTA PRUEBA Y NO OTRA
═══════════════════════════════════════════════════════════════════════════════
La parada de emergencia **ya paraba el robot**: el driver pone una bandera y
descarta todo `cmd_vel`. Eso no hace falta volver a medirlo.

🔴 Lo que se mide aquí es el instante de LIBERARLA. Sin `cancelar_nav2`, el
objetivo de Nav2 sigue vivo, el `controller_server` nunca dejó de publicar, y en
cuanto la bandera baja **el robot arranca solo**, sin que nadie mande nada.

    1. objetivo a `--distancia` metros
    2. a mitad de camino -> /rvr/emergency_stop
    3. ¿el objetivo pasa a CANCELED?          <- lo que hace cancelar_nav2
    4. /release_emergency_stop
    5. 🔴 LA MEDIDA: ¿se mueve el robot en los siguientes 10 s?

═══════════════════════════════════════════════════════════════════════════════
SE MIDE DESPLAZAMIENTO, NO VELOCIDAD
═══════════════════════════════════════════════════════════════════════════════
Un robot que arranca y frena puede dar velocidad media ~0 y haberse movido 20 cm.
Es el error que ya se cometió midiendo el watchdog, y por eso aquí se integra la
posición de `/odom` y se compara con la de antes de liberar.

📝 `/odom` vale para esto aunque su marco tenga sus problemas conocidos: la
   pregunta es «¿cambió la posición?», no «¿en qué dirección exacta?».
"""
import argparse
import math
import sys
import time

import rclpy
from rclpy.signals import SignalHandlerOptions
import tf2_ros
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Empty
from std_srvs.srv import Empty as EmptySrv

QOS_SENSOR = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST, depth=5)
#: Por debajo de esto se considera que el robot no se ha movido: es el ruido
#: propio del locator (acierta con 1 mm en 1 m) más un margen generoso.
QUIETO_M = 0.02


class Medidor(Node):
    def __init__(self):
        super().__init__('medir_parada_nav2')
        self.pos = None
        self.create_subscription(Odometry, 'odom', self._odom, QOS_SENSOR)
        # VOLATILE por defecto en rclpy, que es lo que empareja con el driver.
        self.pub_parada = self.create_publisher(Empty, '/rvr/emergency_stop', 10)
        self.cli_liberar = self.create_client(EmptySrv, 'release_emergency_stop')
        self.nav = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.estado = None
        self._handle = None
        # 🔴 El objetivo va en el marco `map`, así que la pose de partida hay que
        # sacarla de TF, NO de /odom. Con `map` y `odom` casi alineados al
        # arrancar la diferencia es pequeña y el error pasa desapercibido — que
        # es justo lo que lo hace peligroso cuando ya no lo estén.
        self._tf_buf = tf2_ros.Buffer()
        self._tf_lis = tf2_ros.TransformListener(self._tf_buf, self)

    def pose_en_mapa(self, seg=10.0):
        """(x, y) del robot en el marco `map`, o None."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            rclpy.spin_once(self, timeout_sec=0.1)
            try:
                tr = self._tf_buf.lookup_transform(
                    'map', 'base_footprint', rclpy.time.Time())
                return (tr.transform.translation.x, tr.transform.translation.y)
            except Exception:                       # noqa: BLE001
                continue
        return None

    def _odom(self, m: Odometry) -> None:
        self.pos = (m.pose.pose.position.x, m.pose.pose.position.y)

    def girar(self, seg: float) -> None:
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            rclpy.spin_once(self, timeout_sec=0.02)

    def esperar_odom(self, seg=15.0) -> bool:
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.pos is not None:
                return True
        return False

    def recorrido_desde(self, p0) -> float:
        return math.dist(self.pos, p0) if (self.pos and p0) else float('nan')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--distancia', type=float, default=2.0,
                    help='a qué distancia poner el objetivo, en metros')
    ap.add_argument('--espera-tras-liberar', type=float, default=10.0,
                    help='cuánto se vigila el robot después de liberar la parada')
    a = ap.parse_args()

    # 🔴🔴 `SignalHandlerOptions.NO` NO ES OPCIONAL AQUI, Y COSTO ENCONTRARLO.
#    `rclpy.init()` instala SU PROPIO manejador de SIGINT, que **invalida el
#    contexto** antes de que el `except KeyboardInterrupt` llegue a publicar. La
#    parada de emergencia moria con:
#        RCLError: Failed to publish: publisher's context is invalid
#    Medido el 2026-08-02, con el driver escuchando: por defecto **0 lineas** de
#    «PARADA DE EMERGENCIA» en el journal; con NO, **5**.
#    ⚠️ Y es INTERMITENTE: segun donde caiga el Ctrl-C a veces si publicaba, que
#       es como paso la verificacion del 2026-08-01. Un fallo de seguridad que
#       funciona a veces es peor que uno que no funciona nunca.
#    → Con NO, el SIGINT lo maneja Python: el `except KeyboardInterrupt` corre con
#      el contexto VIVO y la parada sale de verdad.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    n = Medidor()

    print('═' * 74)
    print('PARADA DE EMERGENCIA CON NAV2 — ¿arranca solo al liberarla?')
    print('═' * 74)

    if not n.esperar_odom():
        print('🔴 sin /odom. ¿arrancaste robot.launch.py?')
        return 1
    if not n.nav.wait_for_server(timeout_sec=15.0):
        print('🔴 sin navigate_to_pose. ¿arrancaste nav2.launch.py?')
        return 1
    if not n.cli_liberar.wait_for_service(timeout_sec=10.0):
        print('🔴 sin release_emergency_stop. ¿es el driver nuevo?')
        return 1

    # Dos orígenes distintos y a propósito:
    #   `map`  -> para COLOCAR el objetivo, que va en ese marco
    #   `odom` -> para MEDIR el desplazamiento, que es lo único que se juzga aquí
    p_mapa = n.pose_en_mapa()
    if p_mapa is None:
        print('🔴 no hay transform map -> base_footprint.')
        print('   arranca slam.launch.py o localizacion.launch.py.')
        return 1
    p_inicio = n.pos
    print(f'  origen en map:  ({p_mapa[0]:+.3f}, {p_mapa[1]:+.3f})')
    print(f'  origen en odom: ({p_inicio[0]:+.3f}, {p_inicio[1]:+.3f})')

    # ── 1. Mandar el objetivo ────────────────────────────────────────────────
    obj = NavigateToPose.Goal()
    obj.pose = PoseStamped()
    obj.pose.header.frame_id = 'map'
    obj.pose.header.stamp = n.get_clock().now().to_msg()
    obj.pose.pose.position.x = p_mapa[0] + a.distancia
    obj.pose.pose.position.y = p_mapa[1]
    obj.pose.pose.orientation.w = 1.0

    print(f'\n  ⚠️ EL ROBOT VA A AVANZAR ~{a.distancia:.1f} m\n')
    fut = n.nav.send_goal_async(obj)
    rclpy.spin_until_future_complete(n, fut, timeout_sec=15.0)
    handle = fut.result()
    if handle is None or not handle.accepted:
        print('🔴 Nav2 rechazó el objetivo. ¿hay mapa y pose inicial?')
        return 1
    res_fut = handle.get_result_async()
    print('  objetivo aceptado, navegando…')

    # ── 2. Parar a mitad de camino ───────────────────────────────────────────
    objetivo_mitad = a.distancia / 2.0
    t0 = time.monotonic()
    while time.monotonic() - t0 < 60.0:
        n.girar(0.05)
        if n.recorrido_desde(p_inicio) >= objetivo_mitad:
            break
    else:
        print('🔴 el robot no llegó a la mitad en 60 s. Prueba abortada.')
        handle.cancel_goal_async()
        return 1

    d_mitad = n.recorrido_desde(p_inicio)
    print(f'  recorrido {d_mitad*100:.0f} cm  ->  PARADA DE EMERGENCIA')
    n.pub_parada.publish(Empty())
    n.girar(3.0)

    p_parado = n.pos
    print(f'  se detuvo tras {n.recorrido_desde(p_inicio)*100:.0f} cm en total')

    # ── 3. ¿Se canceló el objetivo? ──────────────────────────────────────────
    rclpy.spin_until_future_complete(n, res_fut, timeout_sec=10.0)
    if res_fut.done():
        # 5 = CANCELED, 4 = SUCCEEDED, 6 = ABORTED
        estado = res_fut.result().status
        nombres = {2: 'EXECUTING', 4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}
        etiqueta = nombres.get(estado, str(estado))
        print(f'\n  estado del objetivo: {etiqueta}')
        if estado == 5:
            print('  ✅ CANCELED — cancelar_nav2 hizo su trabajo')
        else:
            print(f'  🔴 se esperaba CANCELED y salió {etiqueta}')
    else:
        print('\n  🔴 el objetivo SIGUE ACTIVO tras la parada.')
        print('     Es el fallo: nadie lo canceló, y al liberar reanudará.')

    # ── 4. Liberar, que es el momento de la verdad ───────────────────────────
    print(f'\n  liberando la parada y vigilando {a.espera_tras_liberar:.0f} s…')
    lf = n.cli_liberar.call_async(EmptySrv.Request())
    rclpy.spin_until_future_complete(n, lf, timeout_sec=10.0)

    p_liberado = n.pos
    peor = 0.0
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.espera_tras_liberar:
        n.girar(0.05)
        peor = max(peor, n.recorrido_desde(p_liberado))

    # ── 5. El veredicto ──────────────────────────────────────────────────────
    print('\n' + '═' * 74)
    print(f'  movimiento tras liberar: {peor*100:.1f} cm')
    if peor <= QUIETO_M:
        print('  ✅ EL ROBOT SE QUEDÓ QUIETO. La parada de emergencia es segura:')
        print('     soltarla no devuelve el robot a lo que estaba haciendo.')
        codigo = 0
    else:
        print('  🔴 EL ROBOT ARRANCÓ SOLO al liberar la parada.')
        print('     El objetivo de Nav2 seguía vivo y el controlador nunca dejó')
        print('     de publicar. Es el agujero que cancelar_nav2 debe tapar:')
        print('     comprueba que el nodo está en nav2.launch.py y corriendo.')
        codigo = 1
    print('═' * 74)

    # Dejar el robot parado pase lo que pase.
    n.pub_parada.publish(Empty())
    n.girar(1.0)
    print('  (parada de emergencia dejada ACTIVA por seguridad;')
    print('   libérala con: ros2 service call /release_emergency_stop std_srvs/srv/Empty)')

    rclpy.shutdown()
    return codigo


if __name__ == '__main__':
    sys.exit(main())
