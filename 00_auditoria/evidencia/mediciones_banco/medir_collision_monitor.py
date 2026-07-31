#!/usr/bin/env python3
"""Mide la capa de seguridad: ¿está en el lazo, y a qué distancia para de verdad?

    # 1. Sin mover el robot apenas — comprueba la topología y el paso de comandos
    python3 medir_collision_monitor.py --cadena

    # 2. La prueba de verdad: conducir contra un obstáculo y ver dónde para
    python3 medir_collision_monitor.py --parada 0.25
    python3 medir_collision_monitor.py --parada 0.40

    # 3. ¿Puede salir? Un robot atrapado en un laboratorio remoto es un robot muerto
    python3 medir_collision_monitor.py --escape

⚠️ MUEVE EL ROBOT. Hace falta un obstáculo plano delante y ~1.5 m de carrera.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ PUBLICA EN /cmd_vel_raw Y NO EN /cmd_vel
═══════════════════════════════════════════════════════════════════════════════
Porque publicar en `/cmd_vel` **salta el collision_monitor**, que es justo lo que
esta herramienta tiene que medir. La cadena es:

    esta herramienta ─► /cmd_vel_raw ─► collision_monitor ─► /cmd_vel ─► driver

Si mides la parada publicando en `/cmd_vel`, mides el watchdog del driver, no la
capa de seguridad — y sale un número plausible y equivocado.

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE MIDE LA DISTANCIA AL OBSTÁCULO
═══════════════════════════════════════════════════════════════════════════════
Con el propio `/scan`, tomando la MEDIANA de los puntos dentro de ±5° de la
dirección de avance. La mediana y no el mínimo: un solo rayo espurio movería el
número entero, y el X2 da ~1.42°/punto, así que ±5° son ~7 rayos.

📝 El valor es la distancia desde el LIDAR, que va montado en el centro del robot
   (`laser_x: 0.0`). El hueco real hasta el obstáculo es ese valor menos la media
   longitud del chasis, **0.091 m** ✅ medido. Se imprimen los dos.

🔴 Hasta el 2026-07-31 esta constante valía 0.109, tomada de un URDF que tenía el
   largo y el ancho CRUZADOS (modelaba 21.8 x 18.5 cuando el robot mide 18 x 22).
   Todos los huecos medidos ese día salieron **2 cm cortos** y están corregidos en
   `17_collision_monitor.txt`.
"""
import argparse
import math
import statistics
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan

#: Media longitud del chasis. ✅ MEDIDO 2026-07-31: 18.2 cm de frente a atrás,
#: con orugas. El LIDAR está en el centro. Antes ponía 0.109, de un URDF que tenía
#: largo y ancho CRUZADOS, y por eso los huecos salían 2 cm cortos.
MEDIA_LONGITUD_M = 0.091
#: Semiancho del cono que se mira hacia delante.
CONO_RAD = math.radians(5.0)
#: Se considera parado por debajo de esto.
QUIETO_MS = 0.02

QOS_SENSOR = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST, depth=5)


class Medidor(Node):
    def __init__(self):
        super().__init__('medir_collision_monitor')
        self.pub = self.create_publisher(Twist, 'cmd_vel_raw', 10)
        self.create_subscription(LaserScan, 'scan', self._scan, QOS_SENSOR)
        self.create_subscription(Odometry, 'odom', self._odom, QOS_SENSOR)
        # Lo que el monitor deja pasar de verdad al robot.
        self.create_subscription(Twist, 'cmd_vel', self._salida, 10)
        self.dist = None        # distancia al obstáculo, m
        self.pos = None         # (x, y) de /odom
        self.v = None           # velocidad lineal en el marco del robot
        self.salidas = []       # lo que llegó a /cmd_vel

    def _scan(self, m: LaserScan) -> None:
        buenos = []
        for i, r in enumerate(m.ranges):
            ang = m.angle_min + i * m.angle_increment
            # normaliza a (-pi, pi] para que ±5° funcione aunque angle_min sea -pi
            ang = math.atan2(math.sin(ang), math.cos(ang))
            if abs(ang) <= CONO_RAD and m.range_min < r < m.range_max and math.isfinite(r):
                buenos.append(r)
        if buenos:
            self.dist = statistics.median(buenos)

    def _odom(self, m: Odometry) -> None:
        self.pos = (m.pose.pose.position.x, m.pose.pose.position.y)
        self.v = m.twist.twist.linear.x

    def _salida(self, m: Twist) -> None:
        self.salidas.append((time.monotonic(), m.linear.x, m.angular.z))

    # ── utilidades ────────────────────────────────────────────────────────────
    def girar(self, seg: float) -> None:
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            rclpy.spin_once(self, timeout_sec=0.02)

    def conducir(self, vx: float, wz: float = 0.0) -> None:
        t = Twist()
        t.linear.x = float(vx)
        t.angular.z = float(wz)
        self.pub.publish(t)

    def parar(self) -> None:
        """Cero repetido: un solo mensaje se puede perder."""
        for _ in range(10):
            self.conducir(0.0)
            self.girar(0.05)

    def esperar_datos(self, seg: float = 15.0) -> bool:
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.dist is not None and self.pos is not None:
                return True
        return False


def modo_cadena(n: Medidor) -> int:
    """Comprueba la topología y que los comandos ATRAVIESAN el monitor.

    Mueve el robot ~1 cm: es la única forma de demostrar que pasan de verdad.
    """
    print('── 1. ¿llegan los sensores? ──')
    if not n.esperar_datos():
        print('  🔴 sin /scan o sin /odom. ¿Arrancaste robot.launch.py?')
        return 1
    print(f'  /scan  obstáculo más cercano al frente: {n.dist:.3f} m')
    print(f'  /odom  pose ({n.pos[0]:+.3f}, {n.pos[1]:+.3f})')

    print('\n── 2. ¿pasa un comando por el monitor? ──')
    print('  ⚠️ el robot avanzará ~1 cm')
    n.salidas.clear()
    d0 = n.pos
    t0 = time.monotonic()
    while time.monotonic() - t0 < 0.5:
        n.conducir(0.02)
        n.girar(0.05)
    n.parar()
    n.girar(0.5)
    recorrido = math.dist(n.pos, d0)
    llegaron = [s for s in n.salidas if abs(s[1]) > 1e-6]
    print(f'  comandos que llegaron a /cmd_vel: {len(llegaron)} con v≠0')
    print(f'  desplazamiento medido en /odom:   {recorrido*100:.1f} cm')
    if not llegaron:
        print('  🔴 EL MONITOR NO DEJA PASAR NADA. ¿está en `active [3]`?')
        return 1
    print('  ✅ el monitor está en el lazo y deja pasar')
    return 0


def modo_parada(n: Medidor, vel: float, limite_s: float = 25.0) -> int:
    """Conduce contra el obstáculo hasta que la seguridad corte. Mide dónde."""
    if not n.esperar_datos():
        print('  🔴 sin /scan o sin /odom.')
        return 1
    d_ini, p_ini = n.dist, n.pos
    print(f'  obstáculo al frente: {d_ini:.3f} m   (hueco real '
          f'{(d_ini - MEDIA_LONGITUD_M)*100:.0f} cm)')
    if d_ini < 0.8:
        print(f'  🔴 DEMASIADO CERCA para medir una parada a {vel:.2f} m/s.')
        print('     Hacen falta al menos 0.8 m; mejor 1.5.')
        return 1

    print(f'\n  ⚠️ AVANZANDO a {vel:.2f} m/s contra el obstáculo\n')
    t0 = time.monotonic()
    quieto_desde = None
    d_min = d_ini
    movido = False
    while time.monotonic() - t0 < limite_s:
        n.conducir(vel)
        n.girar(0.05)
        if n.dist is not None:
            d_min = min(d_min, n.dist)
        v = abs(n.v or 0.0)
        if v > 0.05:
            movido = True
        # parado de verdad = quieto 0.6 s seguidos DESPUÉS de haberse movido
        if movido and v < QUIETO_MS:
            quieto_desde = quieto_desde or time.monotonic()
            if time.monotonic() - quieto_desde > 0.6:
                break
        else:
            quieto_desde = None
    n.parar()
    n.girar(1.0)

    if not movido:
        print('  🔴 el robot NUNCA se movió. O ya estaba dentro del polígono, o el')
        print('     monitor bloquea todo. Aléjalo del obstáculo y repite.')
        return 1

    d_fin = n.dist
    recorrido = math.dist(n.pos, p_ini)
    print(f'  recorrido            {recorrido*100:5.0f} cm')
    print(f'  distancia final      {d_fin:.3f} m desde el LIDAR')
    print(f'  HUECO REAL AL PARAR  {(d_fin - MEDIA_LONGITUD_M)*100:5.1f} cm  ← el número')
    print(f'  acercamiento máximo  {(d_min - MEDIA_LONGITUD_M)*100:5.1f} cm')
    if d_fin - MEDIA_LONGITUD_M < 0.02:
        print('\n  🔴 PARÓ A MENOS DE 2 cm — o tocó. Sube `time_before_collision`.')
        return 1
    print('\n  ✅ paró antes de tocar')
    return 0


def modo_escape(n: Medidor) -> int:
    """¿Puede salir de donde está? Un `stop` fijo lo dejaría atrapado."""
    if not n.esperar_datos():
        print('  🔴 sin /scan o sin /odom.')
        return 1
    print(f'  obstáculo al frente: {n.dist:.3f} m   (hueco '
          f'{(n.dist - MEDIA_LONGITUD_M)*100:.0f} cm)')
    if n.dist - MEDIA_LONGITUD_M > 0.15:
        print('  ⚠️ está a más de 15 cm: la prueba no dice nada. Acércalo primero')
        print('     con --parada.')

    p0 = n.pos
    print('\n  ⚠️ RETROCEDIENDO 1.5 s')
    t0 = time.monotonic()
    while time.monotonic() - t0 < 1.5:
        n.conducir(-0.15)
        n.girar(0.05)
    n.parar()
    n.girar(0.8)
    atras = math.dist(n.pos, p0)
    print(f'  retrocedió {atras*100:.1f} cm')

    p1 = n.pos
    print('\n  ⚠️ GIRANDO en el sitio 1.5 s')
    t0 = time.monotonic()
    while time.monotonic() - t0 < 1.5:
        n.conducir(0.0, 1.0)
        n.girar(0.05)
    n.parar()
    n.girar(0.8)

    ok = atras > 0.03
    print(f'\n  {"✅ PUEDE SALIR" if ok else "🔴 ATRAPADO: no retrocede"}')
    if not ok:
        print('     Un polígono `stop` fijo bloquea TODO movimiento. En un')
        print('     laboratorio remoto eso deja el robot inservible: cámbialo por')
        print('     `approach`, que solo bloquea lo que lleva al choque.')
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--cadena', action='store_true',
                   help='topología y paso de comandos (mueve ~1 cm)')
    g.add_argument('--parada', type=float, metavar='V',
                   help='conduce a V m/s contra el obstáculo y mide dónde para')
    g.add_argument('--escape', action='store_true',
                   help='¿puede retroceder y girar estando pegado?')
    a = ap.parse_args()

    rclpy.init()
    n = Medidor()
    try:
        if a.cadena:
            return modo_cadena(n)
        if a.parada is not None:
            return modo_parada(n, a.parada)
        return modo_escape(n)
    except KeyboardInterrupt:
        print('\n  interrumpido')
        return 130
    finally:
        # Pase lo que pase, el robot se queda quieto.
        try:
            n.parar()
        except Exception:
            pass
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
