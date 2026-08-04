#!/usr/bin/env python3
"""El CONTROL por SSH del movimiento que ya se hizo desde el navegador.

    python3 control_ssh_mismo_movimiento.py

⚠️ MUEVE EL ROBOT ~30 cm y LO DEJA CON LA PARADA PUESTA. Necesita 1 m libre.

═══════════════════════════════════════════════════════════════════════════════
QUÉ CIERRA, Y POR QUÉ REPLICA EN VEZ DE SIMPLIFICAR
═══════════════════════════════════════════════════════════════════════════════
La especificación del cliente de rosbridge pedía: *«un robot real se teleopera
desde el navegador y el desplazamiento medido con cinta coincide con el del
mismo movimiento por SSH»*. La primera mitad está hecha (evidencia 71: 4 de 4,
cinta 30 cm en dos corridas). **Esta es la segunda.**

🔴 La única diferencia entre las dos tiene que ser el TRANSPORTE:

    navegador ->  advertise + publish por WebSocket  ->  rosbridge  ->  DDS
    esto      ->  rclpy publica directamente         ->               DDS

Por eso se replica la secuencia ENTERA —barrido, 0,20 m/s, 1,5 s, republicación
a 10 Hz, y parada de emergencia al final— en vez de hacer «algo parecido». Si se
simplificara, una diferencia en el resultado no se podría atribuir al transporte,
que es lo único que este experimento existe para aislar.

═══════════════════════════════════════════════════════════════════════════════
LAS TRAMPAS DE ESTE PROYECTO QUE ESTE GUION RESPETA
═══════════════════════════════════════════════════════════════════════════════
🔴 `SignalHandlerOptions.NO`. `rclpy.init()` instala SU manejador de SIGINT e
   invalida su propio contexto, así que un Ctrl-C deja la parada SIN PUBLICAR
   —medido: 0 líneas contra 5—. Es obligatorio en cualquier herramienta que
   pare el robot.
🔴 `/odom` es BEST_EFFORT. Un suscriptor RELIABLE no empareja y no llega NADA,
   sin error y sin aviso.
🔴 `/emergency_stop` con **RELIABLE + VOLATILE**. En un suscriptor,
   TRANSIENT_LOCAL solo restringe con quién empareja; el driver escucha
   VOLATILE, así que el publicador tiene que serlo.
🔴 Se publica en **`/cmd_vel_raw`**, NUNCA en `/cmd_vel`: `/cmd_vel` es la
   SALIDA del `collision_monitor` y publicar ahí salta la capa de seguridad.
🔴 Hay que **republicar a 10 Hz**: el watchdog del driver corta a los 0,3 s.
🔴 El barrido tiene que estar encendido y **hay que esperar un `/scan` REAL**,
   no el código de retorno de `/start_scan`: sin `/scan` el `collision_monitor`
   bloquea el movimiento. Y `/start_scan` ha devuelto `result:false` con el
   puerto del LIDAR muerto mientras el nodo parecía sano.
🔴 **NO libera la parada.** Soltarla es un acto humano deliberado: el cuarto
   fallo histórico de este botón fue justo al soltarlo, con el robot arrancando
   solo 34,7 cm.

📝 Para CONDUCIR y esperar, `spin_once` vale: aquí no se cuenta ninguna
   frecuencia. El déficit de conteo de `spin_once` (15,02 contra 16,51) es un
   problema de MEDIR ritmos, no de mover el robot.
"""
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Empty
from std_srvs.srv import Empty as EmptySrv

V_AVANCE = 0.20          # m/s   · idéntico al del navegador
SEG_AVANCE = 1.5         # s     · idéntico
HZ = 10.0                # republicación contra el watchdog de 0,3 s
SEG_TRAS_PARAR = 3.0
PLAZO_SCAN = 8.0

BEST = QoSProfile(depth=10)
BEST.reliability = QoSReliabilityPolicy.BEST_EFFORT

# RELIABLE + VOLATILE: el driver escucha así. Ver la cabecera.
ESTOP = QoSProfile(depth=10)
ESTOP.reliability = QoSReliabilityPolicy.RELIABLE
ESTOP.durability = QoSDurabilityPolicy.VOLATILE


class Control(Node):
    def __init__(self) -> None:
        super().__init__('control_ssh_mismo_movimiento')
        self.pose = None
        self.t_ultimo_scan = None
        self.create_subscription(Odometry, '/odom', self._odom, BEST)
        self.create_subscription(LaserScan, '/scan', self._scan, BEST)
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel_raw', 10)
        self.pub_estop = self.create_publisher(Empty, '/emergency_stop', ESTOP)
        self.cli_start = self.create_client(EmptySrv, '/start_scan')

    def _odom(self, m: Odometry) -> None:
        p = m.pose.pose.position
        self.pose = (p.x, p.y)

    def _scan(self, _m: LaserScan) -> None:
        self.t_ultimo_scan = time.monotonic()


def atender(nodo: Node, seg: float) -> None:
    """Atiende callbacks durante `seg` segundos.

    📝 NO se llama `girar`: en este proyecto `girar()` es una primitiva de
    MOVIMIENTO de `atriz.py` que hace rotar el robot, y un lector rapido podria
    creer que esto lo mueve. Aqui no se mueve nada: solo se atiende el ejecutor.
    """
    fin = time.monotonic() + seg
    while time.monotonic() < fin:
        rclpy.spin_once(nodo, timeout_sec=0.02)


def modulo(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def exigir_pose(nodo: Control, cuando: str):
    """Un `None` aquí daría NaN, y un NaN comparado con un umbral da FALSO."""
    if nodo.pose is None:
        raise SystemExit(f'🔴 no hay pose de /odom {cuando}: el robot no publica')
    return nodo.pose


def main() -> int:
    # 🔴 NO, no None. Ver la cabecera.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    nodo = Control()
    try:
        print('esperando /odom…')
        t0 = time.monotonic()
        while nodo.pose is None and time.monotonic() - t0 < 10:
            rclpy.spin_once(nodo, timeout_sec=0.1)
        exigir_pose(nodo, 'al arrancar')

        # ── el barrido, esperando un /scan REAL ──────────────────────────────
        if not nodo.cli_start.wait_for_service(timeout_sec=5.0):
            raise SystemExit('🔴 /start_scan no está: ¿corre robot.launch.py?')
        fut = nodo.cli_start.call_async(EmptySrv.Request())
        rclpy.spin_until_future_complete(nodo, fut, timeout_sec=10.0)
        t0 = time.monotonic()
        while nodo.t_ultimo_scan is None and time.monotonic() - t0 < PLAZO_SCAN:
            rclpy.spin_once(nodo, timeout_sec=0.1)
        if nodo.t_ultimo_scan is None:
            raise SystemExit(
                f'🔴 /start_scan respondió pero no llegó ningún /scan en {PLAZO_SCAN:.0f} s.\n'
                '   Mira si el descriptor del LIDAR está muerto:\n'
                '     ls -l /proc/$(pgrep -f "[y]dlidar_ros2_dr")/fd | grep tty')
        print(f'barrido listo en {time.monotonic() - t0:.2f} s')

        # ── el avance, republicando a 10 Hz ─────────────────────────────────
        pose_ini = exigir_pose(nodo, 'al empezar a mover')
        print(f'🔴 MOVIENDO a {V_AVANCE} m/s durante {SEG_AVANCE} s')
        tw = Twist()
        tw.linear.x = V_AVANCE
        fin = time.monotonic() + SEG_AVANCE
        while time.monotonic() < fin:
            nodo.pub_cmd.publish(tw)
            atender(nodo, 1.0 / HZ)

        pose_parar = exigir_pose(nodo, 'en el instante de la parada')
        print(f'recorrido antes de la parada: {modulo(pose_ini, pose_parar) * 100:.1f} cm')

        # ── la parada, igual que el navegador ───────────────────────────────
        nodo.pub_estop.publish(Empty())
        print('parada ENVIADA por /emergency_stop')
        atender(nodo, SEG_TRAS_PARAR)

        pose_fin = exigir_pose(nodo, 'al terminar de frenar')
        print(f'══ RECORRIDO TRAS LA PARADA: {modulo(pose_parar, pose_fin) * 100:.1f} cm ══')
        print(f'total desde el inicio: {modulo(pose_ini, pose_fin) * 100:.1f} cm')
        print()
        print('👤 MIDE AHORA CON CINTA el recorrido TOTAL, que es lo que se compara')
        print('   con las corridas del navegador (30 cm en las dos).')
        print()
        print('⚠️ EL ROBOT QUEDA CON LA PARADA PUESTA. Liberarla es presencial:')
        print('   ros2 service call /release_emergency_stop std_srvs/srv/Empty')
        return 0
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
