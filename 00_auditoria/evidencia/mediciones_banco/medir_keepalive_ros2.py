#!/usr/bin/env python3
"""¿Sigue vivo el enlace con el RVR después de estar un rato sin tocar nada?

    # A) SIN keepalive: mide cuánto tarda el RVR en dormirse, y prueba que el
    #    detector de silencio lo pilla y lo recupera.
    ros2 launch atriz_rvr_bringup robot.launch.py lidar:=false keepalive_period:=0.0
    python3 medir_keepalive_ros2.py --minutos 10

    # B) CON keepalive: prueba que ya no se duerme.
    ros2 launch atriz_rvr_bringup robot.launch.py lidar:=false
    python3 medir_keepalive_ros2.py --minutos 10

⚠️  DESPIERTA EL ROBOT y lo deja encendido todo el rato. NO lo mueve.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════

El 2026-07-30 este robot se quedó mudo a mitad de sesión sin que nada pareciera
roto: `/odom`, `/imu` y `/color` dejaron de publicar **a la vez** mientras el
proceso seguía vivo al 12.3 % de CPU, con sus topics registrados y **ni un solo
error en el log**. El RVR se había dormido por inactividad.

Se arregló con un keepalive y un detector de silencio en el driver. **Esta
herramienta es la que comprueba que el arreglo funciona**, y no de la manera
fácil: no mira si el nodo existe ni si el topic está registrado —las dos cosas
eran ciertas mientras el robot estaba mudo— sino si **siguen llegando datos**.

🔴 NO MIRA `ros2 topic list`, MIRA EL RITMO. Es toda la diferencia.

Y de paso mide lo que quedó sin medir: **cuánto tarda el RVR en dormirse**. Con
`keepalive_period:=0.0` el driver no lo previene, así que el primer hueco largo
ES el timeout de inactividad. Hasta ahora solo estaba acotado entre ~2 y ~7.5
min por los timestamps de aquel fallo.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import sys
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy)
from sensor_msgs.msg import BatteryState

#: Un hueco más largo que esto se considera «el enlace se cayó», no jitter.
#: A 60 ms de intervalo llegan ~16.7 muestras/s: 2 s son ~33 muestras perdidas.
HUECO_CAIDA_S = 2.0


class VigilanteEnlace(Node):
    def __init__(self) -> None:
        super().__init__('medir_keepalive')

        # 🔴 /odom es BEST_EFFORT. Con el perfil por defecto de rclpy (RELIABLE)
        # DDS no emparejaría y esta herramienta no recibiría NADA — y concluiría
        # que el robot está mudo cuando no lo está. Es la trampa de QoS del
        # proyecto, y aquí daría un falso positivo perfecto.
        self.create_subscription(
            Odometry, '/odom', self._cb_odom,
            QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT))

        # battery_state va RELIABLE + TRANSIENT_LOCAL (lo publica el keepalive).
        self.create_subscription(
            BatteryState, '/battery_state', self._cb_bateria,
            QoSProfile(depth=1,
                       reliability=QoSReliabilityPolicy.RELIABLE,
                       durability=QoSDurabilityPolicy.TRANSIENT_LOCAL))

        self.t0 = time.monotonic()
        self.n_odom = 0
        self.t_ultimo_odom: float | None = None
        self.huecos: list[tuple[float, float]] = []   # (instante, duración)
        self.n_bateria = 0
        self.bateria_pct: float | None = None
        self.t_ultima_bateria: float | None = None

    def _cb_odom(self, _msg) -> None:
        ahora = time.monotonic()
        if self.t_ultimo_odom is not None:
            hueco = ahora - self.t_ultimo_odom
            if hueco > HUECO_CAIDA_S:
                self.huecos.append((self.t_ultimo_odom - self.t0, hueco))
                print(f"  🔴 t={self.t_ultimo_odom - self.t0:6.1f} s  "
                      f"HUECO de {hueco:.1f} s en /odom  "
                      f"(se recuperó a t={ahora - self.t0:.1f} s)", flush=True)
        self.t_ultimo_odom = ahora
        self.n_odom += 1

    def _cb_bateria(self, msg: BatteryState) -> None:
        ahora = time.monotonic()
        self.n_bateria += 1
        self.bateria_pct = msg.percentage * 100.0
        self.t_ultima_bateria = ahora
        print(f"  🔋 t={ahora - self.t0:6.1f} s  batería {self.bateria_pct:.0f} %"
              f"  (lectura nº {self.n_bateria} — cada una es un keepalive)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--minutos', type=float, default=10.0,
                    help='Cuánto vigilar. El fallo original se vio entre los 2 y '
                         'los 7.5 min, así que menos de 10 no prueba gran cosa.')
    args = ap.parse_args()

    rclpy.init()
    n = VigilanteEnlace()

    duracion = args.minutos * 60.0
    print("═" * 74)
    print("VIGILAR EL ENLACE CON EL RVR — ¿se duerme?")
    print("═" * 74)
    print(f"Vigilando {args.minutos:.0f} min SIN TOCAR NADA. El robot no se mueve.")
    print("Se avisa de cada hueco de /odom y de cada lectura de batería.")
    print("Ctrl-C para cortar antes.\n")

    ultimo_informe = 0.0
    try:
        while True:
            t = time.monotonic() - n.t0
            if t >= duracion:
                break
            rclpy.spin_once(n, timeout_sec=0.2)

            # Informe de vida cada minuto: si esto deja de aparecer con un ritmo
            # sano, el enlace se ha caído mientras mirabas.
            if t - ultimo_informe >= 60.0:
                ultimo_informe = t
                silencio = (time.monotonic() - n.t_ultimo_odom
                            if n.t_ultimo_odom else float('inf'))
                estado = "✅ vivo" if silencio < HUECO_CAIDA_S else f"🔴 MUDO desde hace {silencio:.0f} s"
                print(f"  · t={t/60:4.1f} min  {n.n_odom:6d} muestras de /odom  ·  {estado}",
                      flush=True)
    except KeyboardInterrupt:
        print("\n⚠️  cortado por el usuario")

    transcurrido = time.monotonic() - n.t0

    # ── veredicto ─────────────────────────────────────────────────────────────
    print("\n" + "═" * 74)
    print("VEREDICTO")
    print("═" * 74)
    print(f"  vigilado          {transcurrido/60:.1f} min")
    print(f"  muestras de /odom {n.n_odom}"
          f"  ({n.n_odom/transcurrido:.2f} Hz de media, se esperan ~16.7)")
    print(f"  lecturas batería  {n.n_bateria}"
          + (f"  (última: {n.bateria_pct:.0f} %)" if n.bateria_pct is not None else ""))

    salida = 0
    if n.n_odom == 0:
        print("\n  🔴 NO LLEGÓ NI UNA MUESTRA de /odom.")
        print("     ¿está robot.launch.py corriendo? ¿está el RVR encendido?")
        print("     ros2 topic hz /odom     # debe dar ~16.7 Hz")
        salida = 1
    elif not n.huecos:
        print(f"\n  ✅ NINGÚN HUECO en {transcurrido/60:.1f} min: el enlace aguantó.")
        if n.n_bateria == 0:
            print("     ⚠️  pero NO llegó ninguna lectura de batería: el keepalive")
            print("        no está funcionando, o se lanzó con keepalive_period:=0.")
            print("        Si fue con keepalive desactivado, este resultado significa")
            print("        que el RVR no se durmió en este rato — no que esté arreglado.")
            salida = 1
    else:
        print(f"\n  🔴 {len(n.huecos)} hueco(s) en /odom:")
        for cuando, cuanto in n.huecos:
            print(f"     · a los {cuando/60:.1f} min, duró {cuanto:.1f} s")
        primero = n.huecos[0][0]
        print(f"\n  📏 EL PRIMER HUECO empezó a los {primero:.0f} s ({primero/60:.1f} min).")
        print("     Si se lanzó con keepalive_period:=0.0, ESE es el timeout de")
        print("     inactividad del RVR — el dato que faltaba por medir.")
        print("\n     Y que el hueco TERMINE prueba que el detector de silencio")
        print("     hizo su trabajo. Compruébalo en el log del driver:")
        print("       'el RVR lleva N s sin enviar telemetría'  ->  detectado")
        print("       'streaming reanudado'                     ->  recuperado")
        salida = 1

    print("\n  El log del driver es la otra mitad de la prueba: esta herramienta")
    print("  ve el efecto (llegan datos o no), el log dice si el nodo se enteró.")

    n.destroy_node()
    rclpy.shutdown()
    return salida


if __name__ == '__main__':
    sys.exit(main())
