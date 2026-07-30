#!/usr/bin/env python3
"""¿Se contradicen `/scan` y `/odom`? Lo decide girando el robot, sin colocar nada.

    ros2 launch atriz_rvr_bringup robot.launch.py
    python3 verificar_inverted_lidar.py

⚠️  GIRA EL ROBOT ~50° sobre su eje. No avanza: no necesita espacio libre.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ IMPORTA, Y POR QUÉ NO SE VE MIRANDO EL MAPA
═══════════════════════════════════════════════════════════════════════════════

SLAM cruza dos fuentes: de dónde vienen los barridos (`/scan`) y cuánto se ha
movido el robot (`/odom`). Si las dos no usan **la misma mano** para medir
ángulos, tiran en sentidos contrarios.

🔴 El resultado es un mapa ESPEJADO o emborronado. Y lo peor: sale **coherente
   consigo mismo**. Las paredes son rectas, las esquinas cuadran, el cierre de
   bucle funciona. Parece perfecto y tiene el laboratorio al revés.
   **Mirar el mapa NO detecta esto.**

Dos sitios donde el signo puede estar mal, y esta herramienta no los distingue:

  · `inverted` del driver del YDLIDAR — invierte el signo de los ángulos. El
    `X2.yaml` oficial trae `false`, el launch de ROS 1 de Atriz tenía `true`, y
    ese launch **nunca llegó a ejecutarse**: nadie sabe cuál es el correcto.
  · El **yaw de `/odom`** — si el RVR reporta en FRD (x adelante, y a la
    DERECHA, z abajo) y el driver lo copia crudo a ROS, que espera FLU (y a la
    izquierda, z arriba), el signo del giro sale invertido.

Lo que esta herramienta **sí** decide, y es lo importante, es si los dos
**coinciden entre sí**. Cuál de los dos arreglar lo decide una observación
física: mirar hacia dónde gira el robot. El veredicto lo explica.

Es la regla del proyecto —medir antes de atribuir— aplicada a un signo.

CÓMO FUNCIONA

  Si el robot gira en sentido antihorario (yaw +θ), el mundo, VISTO DESDE EL
  ROBOT, gira en sentido horario: un objeto que estaba a +30° pasa a estar a
  +30° − θ.

      correcto  ->  el patrón de /scan se desplaza −θ
      espejado  ->  el patrón de /scan se desplaza +θ   (signo al revés)

  El desplazamiento se mide por CORRELACIÓN: se busca el giro k que mejor hace
  coincidir el barrido de después con el de antes. No depende de reconocer un
  objeto concreto ni de que haya nada en particular delante — usa toda la
  geometría de la habitación a la vez.

  El giro real se toma de `odom`, que es la fuente independiente. 🔴 De la
  POSICIÓN/ORIENTACIÓN del locator, que es buena; nunca del stream `Velocity`,
  que es basura (0.001 m/s reportados a 0.147 m/s reales).
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener

HZ_CMD = 20.0          # el watchdog del driver corta a los 500 ms
VEL_GIRO = 0.5         # rad/s
GIRO_OBJETIVO = math.radians(50.0)


class VerificadorInverted(Node):
    def __init__(self) -> None:
        super().__init__('verificar_inverted')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        # 🔴 BEST_EFFORT: el driver del LIDAR publica así y rclpy pide RELIABLE
        # por defecto. Sin esto DDS no empareja y no llega NI UN barrido, sin
        # error, y esta herramienta diría «no hay /scan» con el LIDAR girando.
        self.create_subscription(
            LaserScan, '/scan', self._cb_scan,
            QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT))
        self.scan: LaserScan | None = None
        self.buf = Buffer()
        self.escucha = TransformListener(self.buf, self)

    def _cb_scan(self, m: LaserScan) -> None:
        self.scan = m

    def yaw(self) -> float | None:
        try:
            t = self.buf.lookup_transform('odom', 'base_footprint', rclpy.time.Time())
        except Exception:
            return None
        q = t.transform.rotation
        return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                          1.0 - 2.0 * (q.y ** 2 + q.z ** 2))

    def esperar(self, s: float) -> None:
        fin = time.time() + s
        while time.time() < fin:
            rclpy.spin_once(self, timeout_sec=0.1)

    def girar(self, radianes: float) -> float:
        """Gira y devuelve el giro REAL medido en odom (rad, con signo)."""
        y0 = self.yaw()
        tw = Twist()
        tw.angular.z = math.copysign(VEL_GIRO, radianes)
        fin = time.time() + abs(radianes) / VEL_GIRO
        while time.time() < fin:
            self.pub.publish(tw)
            rclpy.spin_once(self, timeout_sec=1.0 / HZ_CMD)
        # Frena y calla. El watchdog saltará una vez ~500 ms después: es lo
        # correcto y esperado, no un fallo.
        tw = Twist()
        for _ in range(6):
            self.pub.publish(tw)
            rclpy.spin_once(self, timeout_sec=1.0 / HZ_CMD)
        self.esperar(1.5)                      # que se asiente antes de medir
        y1 = self.yaw()
        if y0 is None or y1 is None:
            return float('nan')
        return math.atan2(math.sin(y1 - y0), math.cos(y1 - y0))


#: Celdas de la rejilla angular común. 360 = 1° por celda, más fina que la
#: resolución real del X2 (1.42°) y suficiente para decidir un signo.
CELDAS = 360


def a_rejilla(scan: LaserScan) -> list[float]:
    """Remuestrea un barrido a una rejilla fija de `CELDAS` celdas de 360°/N.

    🔴 Hace falta porque **el X2 entrega barridos de longitud VARIABLE**: dos
    lecturas seguidas pueden traer 255 y 254 puntos, con `angle_increment`
    ligeramente distinto. Correlacionar los dos vectores crudos por índice
    compara ángulos que no se corresponden — y con longitudes distintas, además,
    revienta con IndexError. Pasó la primera vez que se ejecutó esto.

    Cada celda guarda la media de las lecturas VÁLIDAS que caen en ella. Las
    celdas sin lecturas quedan a 0.0 y la correlación las ignora: el X2 devuelve
    ~11 % de nulos, y compararlos contra un cero inventado falsearía el ajuste.
    """
    suma = [0.0] * CELDAS
    cuenta = [0] * CELDAS
    for i, r in enumerate(scan.ranges):
        if not math.isfinite(r) or r <= scan.range_min or r > scan.range_max:
            continue
        ang = scan.angle_min + i * scan.angle_increment
        j = int((ang % (2 * math.pi)) / (2 * math.pi) * CELDAS) % CELDAS
        suma[j] += r
        cuenta[j] += 1
    return [suma[j] / cuenta[j] if cuenta[j] else 0.0 for j in range(CELDAS)]


def correlacionar(r1: list[float], r2: list[float]) -> tuple[int, float]:
    """Devuelve (desplazamiento en celdas, calidad 0-1) que lleva r1 -> r2.

    Busca el giro circular k que minimiza la diferencia media, comparando solo
    las celdas válidas en AMBOS barridos.
    """
    n = CELDAS
    mejor_k, mejor_coste = 0, float('inf')
    costes = []
    for k in range(n):
        suma, cuenta = 0.0, 0
        for i in range(n):
            a, b = r1[i], r2[(i + k) % n]
            if a > 0.0 and b > 0.0:
                suma += abs(a - b)
                cuenta += 1
        if cuenta < n // 6:        # muy pocos puntos: ese k no es fiable
            costes.append(float('inf'))
            continue
        coste = suma / cuenta
        costes.append(coste)
        if coste < mejor_coste:
            mejor_coste, mejor_k = coste, k
    # Calidad: cuánto destaca el mejor ajuste sobre el promedio. Si la
    # habitación fuera perfectamente circular no habría un mínimo claro, y hay
    # que saberlo en vez de dar un veredicto sin fundamento.
    finitos = [c for c in costes if math.isfinite(c)]
    if not finitos or mejor_coste == 0:
        return mejor_k, 0.0
    medio = sum(finitos) / len(finitos)
    calidad = max(0.0, min(1.0, 1.0 - mejor_coste / medio)) if medio > 0 else 0.0
    return mejor_k, calidad


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--grados', type=float, default=50.0,
                    help='Cuánto girar. Bastante para no confundirse con el '
                         'ruido, poco para que la escena siga siendo la misma.')
    args = ap.parse_args()

    rclpy.init()
    n = VerificadorInverted()

    print("═" * 74)
    print("¿ESTÁ /scan ESPEJADO? — cruzando LIDAR contra odometría")
    print("═" * 74)
    print("⚠️  El robot va a GIRAR sobre su eje. No avanza.\n")

    n.esperar(3.0)
    if n.scan is None:
        print("🔴 no llega /scan.")
        print("   ¿está robot.launch.py corriendo con lidar:=true?")
        print("   ros2 topic hz /scan          # ~10 Hz")
        print("   ojo: /scan es BEST_EFFORT; un suscriptor RELIABLE no recibe nada.")
        n.destroy_node(); rclpy.shutdown(); return 1
    if n.yaw() is None:
        print("🔴 no resuelve odom -> base_footprint. Sin la referencia")
        print("   independiente, esta prueba no significa nada.")
        n.destroy_node(); rclpy.shutdown(); return 2

    inc = n.scan.angle_increment
    print(f"  /scan: {len(n.scan.ranges)} puntos · resolución "
          f"{math.degrees(inc):.2f}° · arco "
          f"{math.degrees(n.scan.angle_min):.0f}° a {math.degrees(n.scan.angle_max):.0f}°")

    antes = a_rejilla(n.scan)
    print(f"\n  ▸ girando {args.grados:.0f}° en sentido ANTIHORARIO (yaw +)…")
    giro = n.girar(math.radians(args.grados))
    despues = a_rejilla(n.scan)

    if math.isnan(giro) or abs(giro) < math.radians(10):
        print(f"\n🔴 el robot apenas giró ({math.degrees(giro):.1f}°). Sin giro no")
        print("   hay nada que comparar. ¿está despierto? ros2 topic hz /odom")
        n.destroy_node(); rclpy.shutdown(); return 1

    k, calidad = correlacionar(antes, despues)
    # El desplazamiento circular k puede leerse como +k o como k-N (mismo giro,
    # camino corto o largo). Se toma el camino corto, que es el físico.
    if k > CELDAS // 2:
        k -= CELDAS
    desplazamiento = k * (2 * math.pi / CELDAS)

    print(f"\n  giro real (odom):        {math.degrees(giro):+7.1f}°")
    print(f"  desplazamiento del scan: {math.degrees(desplazamiento):+7.1f}°"
          f"   ({k:+d} celdas)")
    print(f"  calidad del ajuste:      {calidad:.2f}  (0 = sin mínimo claro)")

    print("\n" + "═" * 74)
    print("VEREDICTO")
    print("═" * 74)

    if calidad < 0.15:
        print("  ⚠️  NO CONCLUYENTE: la correlación no encontró un ajuste claro.")
        print("     Pasa cuando la geometría alrededor es demasiado uniforme")
        print("     (una sala vacía y simétrica) o el LIDAR ve muy poco.")
        print("     Mueve el robot a un sitio con más estructura y repite.")
        n.destroy_node(); rclpy.shutdown(); return 2

    # correcto: el mundo se desplaza al revés que el robot -> signos opuestos
    coherente = (desplazamiento * giro) < 0
    error = abs(abs(desplazamiento) - abs(giro))

    if coherente:
        print("  ✅ /scan y /odom SON COHERENTES entre sí.")
        print(f"     La odometría midió {math.degrees(giro):+.1f}° y el patrón del")
        print(f"     barrido se desplazó {math.degrees(desplazamiento):+.1f}°: signos")
        print("     opuestos, que es lo que la física exige. SLAM puede fiarse")
        print("     de los dos a la vez.")
        salida = 0
    else:
        # ⚠️ AQUÍ NO SE PUEDE CONCLUIR MÁS, y la primera versión de esta
        # herramienta lo hizo: dijo «/scan está espejado» cuando los datos NO
        # permiten separar las dos causas. Se corrigió el 2026-07-31.
        print("  🔴 /scan y /odom SE CONTRADICEN. Uno de los dos miente.")
        print(f"     La odometría midió {math.degrees(giro):+.1f}° y el patrón se")
        print(f"     desplazó {math.degrees(desplazamiento):+.1f}° — el MISMO signo,")
        print("     cuando la física exige signos opuestos.")
        print(f"\n     Según el barrido, el robot giró {math.degrees(-desplazamiento):+.1f}°.")
        print(f"     Según la odometría, giró    {math.degrees(giro):+.1f}°.")
        print("\n  ESTO ROMPE SLAM PASE LO QUE PASE. El emparejado de barridos y la")
        print("  odometría tiran en sentidos contrarios: el mapa sale espejado, o")
        print("  smeared, o las dos cosas — y coherente consigo mismo, así que")
        print("  MIRAR EL MAPA NO LO DETECTA.")
        print("\n  ⚠️  PERO ESTA PRUEBA NO DICE CUÁL DE LOS DOS ESTÁ MAL. Las dos")
        print("      explicaciones encajan igual con estos datos:")
        print("\n      A) El LIDAR está bien y el YAW DE /odom tiene el signo")
        print("         invertido (el RVR reportaría en FRD —y a la derecha, z")
        print("         abajo— y el driver lo copia crudo, sin pasarlo a FLU).")
        print("         Arreglo: convertir FRD->FLU en _h_quaternion, _h_locator,")
        print("         _h_gyroscope y _h_accel (y = -y, z = -z).")
        print("\n      B) La odometría está bien y /scan ESTÁ ESPEJADO.")
        print("         Arreglo: invertir `inverted` en")
        print("         atriz_rvr_bringup/config/ydlidar_x2.yaml")
        print("\n  LAS SEPARA UNA SOLA OBSERVACIÓN FÍSICA, que ningún software de")
        print("  este robot puede hacer por ti: MIRAR HACIA DÓNDE GIRA.")
        print("\n      El SDK documenta `yaw_angular_velocity` con la regla de la")
        print("      mano derecha (positivo = antihorario visto desde arriba), y")
        print("      el driver pasa `angular.z` sin tocarlo. Así que:")
        print("\n        ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \\")
        print("          '{angular: {z: 0.5}}'      # y MIRA el robot")
        print("\n        gira ANTIHORARIO (izquierda) -> el SDK cumple -> caso A")
        print("        gira HORARIO    (derecha)    -> el SDK miente  -> caso B")
        salida = 1

    if error > math.radians(15):
        print(f"\n  ⚠️  Las magnitudes no cuadran del todo: {math.degrees(error):.0f}° de")
        print("     diferencia. El signo (que es lo que decide `inverted`) sigue")
        print("     siendo fiable, pero esa diferencia apunta a deriva de la")
        print("     odometría o a que la escena cambió entre los dos barridos.")

    n.destroy_node()
    rclpy.shutdown()
    return salida


if __name__ == '__main__':
    sys.exit(main())
