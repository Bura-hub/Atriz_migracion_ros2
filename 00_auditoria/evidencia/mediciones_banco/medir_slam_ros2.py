#!/usr/bin/env python3
"""Mide si slam_toolbox está MAPEANDO de verdad, moviendo el robot.

    python3 medir_slam_ros2.py            # giro + avance + retroceso
    python3 medir_slam_ros2.py --solo-giro  # solo gira: no necesita espacio libre

⚠️  MUEVE EL ROBOT. Necesita ~1 m libre delante y detrás (menos con --solo-giro).
    Requiere `robot.launch.py` y `slam.launch.py` ya en marcha.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE ESTA HERRAMIENTA
═══════════════════════════════════════════════════════════════════════════════

El 2026-07-30 se arrancó SLAM con el robot QUIETO y el mapa salió **92.9 %
desconocido**: 6706 celdas sin explorar, 458 libres, 57 ocupadas. Con el LIDAR
girando a 10 Hz y viendo paredes a 2 m, eso parece un fallo. **No lo es.**

Con `min_pass_through: 2`, una celda necesita **dos rayos** que la atraviesen para
marcarse como libre. Un robot quieto barre siempre desde el mismo punto, y los
rayos divergen: solo las celdas CERCA del robot reciben dos o más rayos. Las
lejanas reciben uno y se quedan en «desconocido» para siempre.

    robot quieto:            robot que se mueve:
    rayos divergentes        cada celda vista desde varios sitios
    ·  ·   ·    ·            ····························
     · ·  ·  ·               ····························
      ·· · ·                 ····························
       ·│·                   ↑ el mapa se rellena

Y además `minimum_travel_distance: 0.3` / `minimum_travel_heading: 0.5` significan
que **slam_toolbox no añade un barrido nuevo al grafo hasta que el robot se ha
movido** 30 cm o girado 28.6°. Quieto, el grafo tiene un solo nodo.

→ **Un mapa casi vacío con el robot parado NO es un fallo de SLAM.** Es la trampa
  de diagnóstico obvia de la Fase 4, y sin esta herramienta se pierde una tarde
  ajustando parámetros del solver que están bien.

MIDE EL EFECTO, NO LA INTENCIÓN (regla del proyecto): no comprueba «he publicado
cmd_vel», comprueba **cuántas celdas conocidas tiene el mapa antes y después**.

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import collections
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from tf2_ros import Buffer, TransformListener

# El watchdog del driver corta a los 500 ms sin cmd_vel (medido: 527 ms). A 20 Hz
# hay margen de sobra sin inundar DDS.
HZ_CMD = 20.0

# Velocidades deliberadamente bajas: es una prueba de banco, no de rendimiento, y
# el objetivo es que slam_toolbox tenga barridos limpios que emparejar.
VEL_GIRO = 0.5      # rad/s  -> 360° en ~12.6 s
VEL_AVANCE = 0.15   # m/s    -> medido bueno para el emparejado


class MedidorSlam(Node):
    def __init__(self) -> None:
        super().__init__('medir_slam')

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # 🔴 /map es RELIABLE + TRANSIENT_LOCAL (latched). Con el perfil por
        # defecto de rclpy (VOLATILE) habría que esperar hasta 5 s al siguiente
        # `map_update_interval`; con TRANSIENT_LOCAL llega el último al instante.
        # Es el mismo problema de emparejado de QoS que con /scan, al revés.
        self.create_subscription(
            OccupancyGrid, '/map', self._cb_mapa,
            QoSProfile(depth=1,
                       reliability=QoSReliabilityPolicy.RELIABLE,
                       durability=QoSDurabilityPolicy.TRANSIENT_LOCAL))

        self.mapa: OccupancyGrid | None = None
        self.buf = Buffer()
        self.escucha = TransformListener(self.buf, self)

    def _cb_mapa(self, m: OccupancyGrid) -> None:
        self.mapa = m

    # ── medición ──────────────────────────────────────────────────────────────
    def resumen_mapa(self) -> dict | None:
        if self.mapa is None:
            return None
        m = self.mapa
        c = collections.Counter(m.data)
        total = len(m.data)
        desconocido = c[-1]
        libre = c[0]
        ocupado = sum(v for k, v in c.items() if k > 0)
        return {
            'ancho': m.info.width,
            'alto': m.info.height,
            'res': m.info.resolution,
            'total': total,
            'libre': libre,
            'ocupado': ocupado,
            'desconocido': desconocido,
            'conocido': total - desconocido,
            'area_m2': (total - desconocido) * m.info.resolution ** 2,
        }

    def pose(self, padre: str, hijo: str) -> tuple[float, float, float] | None:
        """(x, y, yaw) de `hijo` en `padre`, o None si TF no lo tiene."""
        try:
            t = self.buf.lookup_transform(padre, hijo, rclpy.time.Time())
        except Exception:
            return None
        q = t.transform.rotation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y ** 2 + q.z ** 2))
        return (t.transform.translation.x, t.transform.translation.y, yaw)

    # ── movimiento ────────────────────────────────────────────────────────────
    def mover(self, lineal: float, angular: float, segundos: float,
              etiqueta: str) -> float:
        """Mueve y devuelve el RECORRIDO REAL en `odom`, en metros.

        Devolver el recorrido es lo que separa los dos fallos que se confunden:

          · recorrido ≈ 0  y el mapa no crece  ->  el ROBOT no se movió
          · recorrido > 0  y el mapa no crece  ->  SLAM no está procesando

        Sin este dato, un mapa que no crece tiene dos causas indistinguibles y se
        acaba depurando la equivocada. Se acumula el desplazamiento paso a paso
        (no inicio-contra-fin) para que un giro o un ida-y-vuelta cuenten: el neto
        de avanzar 40 cm y retroceder 40 cm es cero, y el robot sí se movió 80 cm.

        🔴 Se mide POSICIÓN, no velocidad. El stream `Velocity` del RVR es basura
           (0.001 m/s reportados a 0.147 m/s reales) y ya hizo concluir a una
           herramienta de este proyecto que «el robot NUNCA se movió» mientras
           cruzaba la habitación. El locator (posición) sí es fiable.
        """
        print(f"  ▸ {etiqueta}  ({segundos:.1f} s)", flush=True)
        tw = Twist()
        tw.linear.x = lineal
        tw.angular.z = angular
        fin = time.time() + segundos
        periodo = 1.0 / HZ_CMD
        recorrido = 0.0
        previa = self.pose('odom', 'base_footprint')
        while time.time() < fin:
            self.pub.publish(tw)
            rclpy.spin_once(self, timeout_sec=periodo)
            actual = self.pose('odom', 'base_footprint')
            if previa and actual:
                recorrido += math.hypot(actual[0] - previa[0], actual[1] - previa[1])
            if actual:
                previa = actual
        print(f"    recorrido real en odom: {recorrido*100:.1f} cm")
        return recorrido

    def parar(self) -> None:
        """Frena publicando ceros y luego CALLA.

        Se publican ceros ~0.3 s y se deja de publicar. El watchdog del driver
        saltará una vez unos 500 ms después: **eso es lo correcto y esperado**,
        no un fallo. Publicar «por cortesía» un Twist vacío cada cierto tiempo
        para «evitar» el watchdog es lo que hizo una prueba anterior, y solo
        consiguió disparar el watchdog dos veces en vez de una.
        """
        tw = Twist()
        fin = time.time() + 0.3
        while time.time() < fin:
            self.pub.publish(tw)
            rclpy.spin_once(self, timeout_sec=1.0 / HZ_CMD)

    def esperar_mapa(self, segundos: float) -> None:
        """Espera a que llegue un /map nuevo. `map_update_interval` es 5 s."""
        fin = time.time() + segundos
        while time.time() < fin:
            rclpy.spin_once(self, timeout_sec=0.2)


def imprimir(titulo: str, r: dict | None) -> None:
    print(f"\n── {titulo} ──")
    if r is None:
        print("  🔴 no ha llegado ningún /map")
        return
    print(f"  rejilla      {r['ancho']} x {r['alto']} celdas a {r['res']*100:.0f} cm"
          f"  = {r['ancho']*r['res']:.2f} x {r['alto']*r['res']:.2f} m")
    print(f"  conocido     {r['conocido']:6d} celdas  ({100*r['conocido']/r['total']:5.1f} %)"
          f"  = {r['area_m2']:.2f} m² mapeados")
    print(f"    libre      {r['libre']:6d}")
    print(f"    ocupado    {r['ocupado']:6d}   <- obstáculos")
    print(f"  desconocido  {r['desconocido']:6d} celdas  ({100*r['desconocido']/r['total']:5.1f} %)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--solo-giro', action='store_true',
                    help='No avanza. Para cuando no hay espacio libre delante.')
    ap.add_argument('--avance-m', type=float, default=0.40,
                    help='Metros a avanzar y retroceder (por defecto 0.40).')
    args = ap.parse_args()

    rclpy.init()
    n = MedidorSlam()

    print("═" * 74)
    print("MEDIR SLAM — ¿está mapeando de verdad?")
    print("═" * 74)
    print("⚠️  El robot va a MOVERSE. Ctrl-C para abortar (frena solo).")

    # Antes de mover nada: ¿está el árbol TF completo? Sin map->base_footprint,
    # slam_toolbox no está localizando y medir el mapa no significa nada.
    print("\n── árbol TF (sin esto, el resto no significa nada) ──")
    n.esperar_mapa(3.0)
    ok_tf = True
    for padre, hijo in (('odom', 'base_footprint'), ('map', 'base_footprint'),
                        ('base_link', 'laser')):
        p = n.pose(padre, hijo)
        if p is None:
            print(f"  🔴 {padre} -> {hijo}: NO RESUELVE")
            ok_tf = False
        else:
            print(f"  ✅ {padre} -> {hijo}: x={p[0]:+.3f} y={p[1]:+.3f} yaw={math.degrees(p[2]):+.1f}°")
    if not ok_tf:
        print("\n🔴 El árbol TF está incompleto. Arregla eso antes de medir el mapa.")
        n.destroy_node()
        rclpy.shutdown()
        return 2

    antes = n.resumen_mapa()
    pose_antes = n.pose('map', 'base_footprint')
    imprimir("MAPA ANTES de mover", antes)

    recorrido_total = 0.0
    try:
        # 1) Giro completo. Añade barridos al grafo por `minimum_travel_heading`
        #    (0.5 rad = 28.6°), y hace que las celdas cercanas reciban rayos
        #    desde muchos ángulos.
        recorrido_total += n.mover(0.0, VEL_GIRO, 2 * math.pi / VEL_GIRO,
                                   "giro de 360° sobre el eje")
        n.parar()
        n.esperar_mapa(6.0)          # > map_update_interval (5 s)
        tras_giro = n.resumen_mapa()
        imprimir("MAPA tras el giro", tras_giro)

        # 2) Avance y retroceso. Es lo que de verdad rellena el mapa: cambia el
        #    punto de vista, así que celdas que antes recibían un solo rayo pasan
        #    a recibir varios y superan `min_pass_through`.
        tras_avance = tras_giro
        if not args.solo_giro:
            t = args.avance_m / VEL_AVANCE
            recorrido_total += n.mover(VEL_AVANCE, 0.0, t,
                                       f"avance de {args.avance_m:.2f} m")
            n.parar()
            n.esperar_mapa(6.0)
            recorrido_total += n.mover(-VEL_AVANCE, 0.0, t,
                                       f"retroceso de {args.avance_m:.2f} m")
            n.parar()
            n.esperar_mapa(6.0)
            tras_avance = n.resumen_mapa()
            imprimir("MAPA tras avanzar y retroceder", tras_avance)
    except KeyboardInterrupt:
        print("\n⚠️  abortado por el usuario — frenando")
        n.parar()
        n.destroy_node()
        rclpy.shutdown()
        return 130

    # ── veredicto ─────────────────────────────────────────────────────────────
    print("\n" + "═" * 74)
    print("VEREDICTO")
    print("═" * 74)

    salida = 0
    if antes is None or tras_avance is None:
        print("🔴 FALLO: no llegó /map. ¿está `slam.launch.py` en marcha y en `active`?")
        print("   ros2 lifecycle get /slam_toolbox   # debe decir: active [3]")
        salida = 1
    else:
        crecimiento = tras_avance['conocido'] - antes['conocido']
        print(f"  recorrido real:   {recorrido_total*100:.1f} cm  (medido en odom)")
        print(f"  celdas conocidas: {antes['conocido']} -> {tras_avance['conocido']}"
              f"  ({crecimiento:+d})")
        print(f"  área mapeada:     {antes['area_m2']:.2f} -> {tras_avance['area_m2']:.2f} m²")

        # El robot se movió si recorrió más de 5 cm: por debajo es ruido del
        # locator y no se puede exigir que el mapa cambie.
        se_movio = recorrido_total > 0.05

        if crecimiento > 0:
            print("\n  ✅ EL MAPA CRECE AL MOVERSE: slam_toolbox está mapeando.")
        elif not se_movio:
            print(f"\n  🔴 EL ROBOT NO SE MOVIÓ ({recorrido_total*100:.1f} cm). No es culpa de")
            print("     SLAM: el mapa no puede crecer sin puntos de vista nuevos.")
            print("     1. ¿está el RVR despierto? Un RVR dormido publica CERO y el")
            print("        nodo sigue vivo con todos los topics: reinicia el driver.")
            print("            ros2 topic hz /odom      # debe dar ~16.7 Hz")
            print("     2. ¿llega cmd_vel al driver?  ros2 topic hz /cmd_vel")
            print("     3. ¿lo frena el watchdog?  busca 'watchdog' en el log del driver")
            salida = 1
        else:
            print(f"\n  🔴 EL ROBOT SÍ SE MOVIÓ ({recorrido_total*100:.1f} cm) Y EL MAPA NO CRECIÓ.")
            print("     El problema está en slam_toolbox, no en el robot.")
            print("     1. ros2 lifecycle get /slam_toolbox      # debe: active [3]")
            print("     2. ros2 topic hz /scan                   # ¿llegan barridos?")
            print("     3. ros2 topic info /scan --verbose       # QoS: BEST_EFFORT en AMBOS")
            print("     4. ⚠️  si reiniciaste el driver DESPUÉS de arrancar slam_toolbox,")
            print("        reinicia slam_toolbox también: se queda con un hueco en su")
            print("        buffer TF y con el `odom` viejo, y deja de procesar. Mezclar")
            print("        un slam viejo con un driver nuevo NO es una prueba válida.")
            salida = 1

    pose_despues = n.pose('map', 'base_footprint')
    if pose_antes and pose_despues:
        d = math.hypot(pose_despues[0] - pose_antes[0], pose_despues[1] - pose_antes[1])
        giro = math.degrees(abs(pose_despues[2] - pose_antes[2]))
        print(f"\n  pose en `map`: se desplazó {d*100:.1f} cm y giró {giro:.1f}°")
        print("  (tras un giro de 360° y volver al sitio, lo ideal es ~0 en ambos;")
        print("   lo que sobra es deriva acumulada de odometría + emparejado)")

    print("\n  Guardar este mapa (formato nativo, NO necesita nav2):")
    print("    ros2 service call /slam_toolbox/serialize_map \\")
    print("      slam_toolbox/srv/SerializePoseGraph \"{filename: /ruta/sin/extension}\"")

    n.destroy_node()
    rclpy.shutdown()
    return salida


if __name__ == '__main__':
    sys.exit(main())
