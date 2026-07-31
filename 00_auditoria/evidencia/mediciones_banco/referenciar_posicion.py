#!/usr/bin/env python3
"""Devuelve el robot a un origen REPETIBLE: perpendicular a la pared, a X metros.

    python3 referenciar_posicion.py --distancia 2.05
    python3 referenciar_posicion.py --solo-medir      # no mueve nada

⚠️ MUEVE EL ROBOT. Arráncalo con `collision_monitor:=false` (publica en /cmd_vel).

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════
`caracterizar_deriva_slam.py` repite N corridas dando por hecho que el robot
"vuelve al punto de partida". **No vuelve.** Medido el 2026-07-31 sobre 24
corridas (manual, cap. 9.12b):

    tanda 1:  94 cm de deriva hacia delante en 12 corridas  (~8 cm cada una)
    tanda 2:  deriva lateral hasta quedar a 16 cm de un obstáculo,
              con 11 cm de media anchura: A 5 cm DE ROZAR

Así que "12 repeticiones" eran 12 posiciones distintas sin registrar, y ninguna
distribución que salga de ahí vale. Este script convierte cada corrida en una
repetición de verdad.

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE FIJA EL ORIGEN
═══════════════════════════════════════════════════════════════════════════════
Con la pared que el robot tiene delante, que es la referencia más estable que hay
en el pasillo. Ajustando una recta a los puntos del frente en el marco del robot:

    x = m·y + c        ->    error de rumbo θ = atan(m)
                             distancia perpendicular D = c·cos(θ)

  (sale de meter un punto de pared (D, Y) del mundo en el marco del robot girado
   θ: x = D/cos θ + y·tan θ)

Entonces, **y en este orden**:
  1. avanza o retrocede hasta que D sea la distancia objetivo
  2. gira −θ  ->  queda PERPENDICULAR a la pared

🔴 El orden importa. Al revés, conducir vuelve a torcer el rumbo recién corregido:
   medido, pasaba de +0.41° a +2.53°. Girar sobre el eje NO cambia la distancia
   perpendicular —el centro del robot no se mueve—, así que la rotación va la
   última sin estropear nada.

   Con el orden bueno converge a ±0.2 cm y ±0.2°, medido en dos pasadas seguidas.

Lo que NO corrige es la posición LATERAL: un diferencial no puede desplazarse de
lado. Pero la deriva lateral viene sobre todo de acumular error de rumbo corrida
tras corrida, así que fijar el rumbo la ataca en su origen. El script imprime las
distancias laterales para poder comprobarlo.

═══════════════════════════════════════════════════════════════════════════════
🔴 NO USA /odom NI EL MAPA A PROPÓSITO
═══════════════════════════════════════════════════════════════════════════════
Referenciar con odometría sería circular: es justo lo que se está midiendo. El
LIDAR contra una pared física es independiente de la deriva que se investiga.
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

QOS = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                 history=HistoryPolicy.KEEP_LAST, depth=5)

#: Semiancho del sector frontal para ajustar la pared. ±35° a 2 m son ~1.4 m de
#: pared: suficiente para que la recta sea estable sin recoger las esquinas.
SECTOR_DEG = 35.0
#: Se acumulan barridos porque uno solo del X2 es ruidoso (manual, cap. 12.10).
SEGUNDOS_SCAN = 5.0
#: Tolerancias del origen. 3 cm y 1°. Los 3 cm no son pereza: la frenada del RVR se come 1-2 cm, así que
#: pedir menos haría que el bucle no convergiera nunca. Aun así es ~3 veces mejor
#: que los ~8 cm/corrida que se median sin referenciar.
TOL_DIST_M = 0.03
TOL_ANG_DEG = 1.0


class Referenciador(Node):
    def __init__(self):
        super().__init__('referenciar_posicion')
        self.pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_subscription(LaserScan, 'scan', self._scan, QOS)
        self.create_subscription(Odometry, 'odom', self._odom, QOS)
        self._acum: dict[float, list[float]] = {}
        self.yaw = None
        self.pos = None

    def _scan(self, m: LaserScan) -> None:
        for i, r in enumerate(m.ranges):
            if not (m.range_min < r < m.range_max) or not math.isfinite(r):
                continue
            a = math.atan2(math.sin(m.angle_min + i * m.angle_increment),
                           math.cos(m.angle_min + i * m.angle_increment))
            self._acum.setdefault(round(math.degrees(a) * 2) / 2, []).append(r)

    def _odom(self, m: Odometry) -> None:
        o = m.pose.pose.orientation
        self.yaw = math.atan2(2 * (o.w * o.z + o.x * o.y),
                              1 - 2 * (o.y * o.y + o.z * o.z))
        self.pos = (m.pose.pose.position.x, m.pose.pose.position.y)

    def girar_ros(self, seg: float) -> None:
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            rclpy.spin_once(self, timeout_sec=0.02)

    def barrer(self, seg: float = SEGUNDOS_SCAN) -> dict[float, float]:
        self._acum.clear()
        self.girar_ros(seg)
        return {a: statistics.median(v) for a, v in self._acum.items() if len(v) >= 3}

    def parar(self) -> None:
        for _ in range(12):
            self.pub.publish(Twist())
            self.girar_ros(0.04)


def ajustar_pared(pts: dict[float, float]) -> tuple[float, float, int] | None:
    """(error de rumbo en rad, distancia perpendicular, nº de puntos).

    Ajusta `x = m·y + c` por mínimos cuadrados sobre el sector frontal.
    """
    xs, ys = [], []
    for a, d in pts.items():
        if abs(a) > SECTOR_DEG:
            continue
        ar = math.radians(a)
        xs.append(d * math.cos(ar))
        ys.append(d * math.sin(ar))
    if len(xs) < 12:
        return None
    # Mediana ± 0.5 m: quita retornos de otras cosas dentro del sector.
    med = statistics.median(xs)
    filt = [(x, y) for x, y in zip(xs, ys) if abs(x - med) < 0.5]
    if len(filt) < 12:
        return None
    xs = [p[0] for p in filt]
    ys = [p[1] for p in filt]
    n = len(xs)
    my, mx = sum(ys) / n, sum(xs) / n
    den = sum((y - my) ** 2 for y in ys)
    if den < 1e-9:
        return None
    m = sum((y - my) * (x - mx) for x, y in zip(xs, ys)) / den
    c = mx - m * my
    theta = math.atan(m)
    return theta, c * math.cos(theta), n


def lateral(pts: dict[float, float]) -> tuple[float | None, float | None]:
    def sect(centro):
        v = [d for a, d in pts.items()
             if abs(((a - centro + 180) % 360) - 180) <= 8]
        return statistics.median(v) if v else None
    return sect(90), sect(-90)


def referenciar(n: Referenciador, objetivo: float, mover: bool) -> int:
    pts = n.barrer()
    aj = ajustar_pared(pts)
    if aj is None:
        print('  🔴 no se puede ajustar la pared frontal: '
              f'{sum(1 for a in pts if abs(a) <= SECTOR_DEG)} puntos en ±{SECTOR_DEG:.0f}°')
        return 1
    th, d, npts = aj
    izq, der = lateral(pts)
    print(f'  ANTES   perpendicular {d:.3f} m · rumbo {math.degrees(th):+.2f}° '
          f'({npts} puntos de pared)')
    print(f'          lateral: izq {izq:.2f} m · der {der:.2f} m'
          if izq and der else '          lateral: sin dato')
    if not mover:
        return 0

    # 🔴 EL ORDEN IMPORTA: primero la DISTANCIA y después el RUMBO.
    #
    # Al revés —que es como estaba— conducir vuelve a torcer el rumbo que se
    # acababa de corregir: medido, pasó de +0.41° a +2.53°. Girar sobre el eje,
    # en cambio, NO cambia la distancia perpendicular a la pared, porque el
    # centro del robot no se mueve. Así que la rotación puede ir la última sin
    # estropear nada.

    # ── 1. distancia ─────────────────────────────────────────────────────────
    for _ in range(4):
        aj = ajustar_pared(n.barrer(3.0))
        if aj is None:
            break
        th, d, _ = aj
        err = d - objetivo          # >0: está lejos, hay que avanzar
        if abs(err) <= TOL_DIST_M:
            break
        p0 = n.pos
        # Despacio cuando queda poco: la frenada se come 1-2 cm y con errores
        # pequeños ese overshoot es del tamaño de lo que se quiere corregir.
        v = 0.12 if abs(err) > 0.10 else (0.07 if abs(err) > 0.04 else 0.05)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 25:
            if math.dist(n.pos, p0) >= abs(err) - 0.005:
                break
            tw = Twist()
            tw.linear.x = v if err > 0 else -v
            n.pub.publish(tw)
            rclpy.spin_once(n, timeout_sec=0.03)
        n.parar()

    # ── 2. rumbo, EL ÚLTIMO ──────────────────────────────────────────────────
    aj = ajustar_pared(n.barrer(3.0))
    if aj is not None and abs(math.degrees(aj[0])) > TOL_ANG_DEG:
        th = aj[0]
        meta = n.yaw - th           # −θ deja al robot perpendicular
        t0 = time.monotonic()
        while time.monotonic() - t0 < 15:
            e = math.atan2(math.sin(meta - n.yaw), math.cos(meta - n.yaw))
            if abs(e) < 0.008:
                break
            tw = Twist()
            tw.angular.z = max(-0.6, min(0.6, 2.0 * e if abs(e) > 0.15
                                         else 0.30 * (1 if e > 0 else -1)))
            n.pub.publish(tw)
            rclpy.spin_once(n, timeout_sec=0.03)
        n.parar()

    # ── 3. qué quedó ─────────────────────────────────────────────────────────
    aj = ajustar_pared(n.barrer())
    if aj is None:
        print('  🔴 no se pudo verificar')
        return 1
    th, d, _ = aj
    izq, der = lateral(n.barrer(2.0))
    ok = abs(d - objetivo) <= TOL_DIST_M * 1.5 and abs(math.degrees(th)) <= TOL_ANG_DEG * 1.5
    print(f'  DESPUÉS perpendicular {d:.3f} m (objetivo {objetivo:.2f}, '
          f'error {(d-objetivo)*100:+.1f} cm) · rumbo {math.degrees(th):+.2f}°')
    if izq and der:
        print(f'          lateral: izq {izq:.2f} m · der {der:.2f} m')
    print('  ✅ referenciado' if ok else '  ⚠️ fuera de tolerancia, pero se continúa')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--distancia', type=float, default=2.05,
                    help='Distancia perpendicular objetivo a la pared frontal (m).')
    ap.add_argument('--solo-medir', action='store_true',
                    help='Mide y no mueve el robot.')
    a = ap.parse_args()

    rclpy.init()
    n = Referenciador()
    try:
        t0 = time.monotonic()
        while time.monotonic() - t0 < 15 and (n.yaw is None or not n._acum):
            rclpy.spin_once(n, timeout_sec=0.2)
        if n.yaw is None:
            print('  🔴 sin /odom. ¿Arrancaste robot.launch.py?')
            return 1
        return referenciar(n, a.distancia, not a.solo_medir)
    except KeyboardInterrupt:
        return 130
    finally:
        try:
            n.parar()
        except Exception:
            pass
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
