#!/usr/bin/env python3
"""Mide el watchdog de `cmd_vel` del driver ROS 2 con timestamps reales.

    python3 medir_watchdog_ros2.py [--velocidad 0.15] [--duracion 2.0]

⚠️ **EL ROBOT SE MUEVE.** Ponlo en el SUELO con espacio libre. A 0.15 m/s
   recorre 15 cm por segundo; sobre una mesa se cae.

QUÉ MIDE, Y POR QUÉ IMPORTA

  El watchdog es la única defensa del robot si se cae la red: sin él, el RVR
  sigue ejecutando el último `cmd_vel` indefinidamente. En un laboratorio remoto
  con 16 robots y 797 reintentos de WiFi medidos en 42 minutos, eso no es
  hipotético.

  El watchdog existía en el nodo de ROS 1 desde el commit `d8f182d`, pero
  **nunca se había probado**. Este script es esa prueba.

CÓMO LO MIDE — Y POR QUÉ **NO** POR VELOCIDAD

  🔴 **El stream `Velocity` del RVR NO refleja la velocidad real.** Medido el
  2026-07-30: con el robot avanzando a **0.147 m/s** comprobados por
  desplazamiento, el sensor reportaba **0.001 m/s**.

  La primera versión de este script usaba esa velocidad y concluyó «el robot
  NUNCA se movió» mientras el robot cruzaba la habitación. Lo corrigió el
  usuario, mirándolo. Mide el DESPLAZAMIENTO, no la velocidad.

    1. Publica `cmd_vel` a 10 Hz durante `--duracion` segundos.
    2. Deja de publicar y anota el instante exacto (`t_ultimo_cmd`).
    3. Sigue la POSICIÓN en `/odom` hasta que deja de avanzar.
    4. Informa de `t_parada - t_ultimo_cmd`.

  «Parado» se define como avanzar menos de `UMBRAL_QUIETO_M` entre dos muestras
  consecutivas de `/odom`, que llegan a ~16.7 Hz. A 0.15 m/s el robot recorre
  9 mm entre muestras, así que 1.5 mm distingue bien movimiento de ruido.

EL CRITERIO DE ÉXITO, Y POR QUÉ NO ES EL TIMEOUT

  ⚠️ La primera versión de este script exigía **< 350 ms** («timeout de 0.3 s +
  periodo de comprobación de 0.05 s») y daba AVISO a los 498 ms medidos. Ese
  umbral estaba mal calculado: entre que el watchdog manda `drive_stop` y el
  robot está quieto pasan cosas físicas que no dependen del software.

  El tiempo total se descompone así, medido el 2026-07-30:

      ~300 ms   el timeout de cmd_vel_timeout. ESTO es lo que mide el watchdog,
                y sale exacto (se ve en el log del driver).
      ~200 ms   latencia del comando por UART + inercia del robot + resolución
                de /odom (una muestra cada 60 ms) + el umbral de detección.
      ─────
       498 ms   hasta quieto, con ~7.5 cm recorridos tras perder la red.

  Así que el umbral se pone en **timeout + 300 ms de margen físico**, y lo que
  se juzga de verdad es la **distancia recorrida tras el corte**: es la magnitud
  que importa en un laboratorio con obstáculos, y escala con la velocidad.
"""
import argparse
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

#: Avance entre dos muestras consecutivas de /odom (~60 ms) por debajo del cual
#: se considera que el robot está quieto. A 0.15 m/s recorrería ~9 mm.
UMBRAL_QUIETO_M = 0.0015


class MedidorWatchdog(Node):
    def __init__(self, velocidad: float, duracion: float,
                 timeout_esperado: float = 0.3) -> None:
        super().__init__('medidor_watchdog')
        self._velocidad = velocidad
        self._duracion = duracion
        self._timeout_esperado = timeout_esperado

        self.pub = self.create_publisher(Twist, 'cmd_vel', 10)
        # BEST_EFFORT para que coincida con el QoS del driver: si no coinciden,
        # DDS no empareja publicador y suscriptor y no llega NADA. Es un fallo
        # silencioso muy típico de ROS 2.
        self.create_subscription(
            Odometry, 'odom', self._cb_odom,
            QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT),
        )

        self._muestras: list[tuple[float, float, float]] = []   # (t, x, y)
        self._t_ultimo_cmd: float | None = None
        self._t_parada: float | None = None
        self._recorrido_total = 0.0
        self._pos_al_cortar: tuple[float, float] | None = None

    def _cb_odom(self, msg: Odometry) -> None:
        t = time.monotonic()
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        avance = 0.0
        if self._muestras:
            _, xa, ya = self._muestras[-1]
            avance = math.hypot(x - xa, y - ya)
            self._recorrido_total += avance
        self._muestras.append((t, x, y))

        # Solo se declara parado si ya había una muestra previa con la que
        # comparar, y si el corte de cmd_vel ya ocurrió.
        if (self._t_ultimo_cmd is not None
                and self._t_parada is None
                and len(self._muestras) > 1
                and avance < UMBRAL_QUIETO_M):
            self._t_parada = t
            self._pos_al_cortar = (x, y)

    def ejecutar(self) -> int:
        print(f'  esperando /odom…', flush=True)
        t0 = time.monotonic()
        while not self._muestras and time.monotonic() - t0 < 10.0:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not self._muestras:
            print('  ✗ no llega /odom. ¿Está corriendo el driver? '
                  '¿coincide ROS_DOMAIN_ID?', file=sys.stderr)
            return 1
        print(f'  /odom recibido ({len(self._muestras)} muestras)', flush=True)

        # ── 1. Publicar cmd_vel ──────────────────────────────────────────────
        msg = Twist()
        msg.linear.x = self._velocidad
        print(f'  publicando cmd_vel linear.x={self._velocidad} m/s '
              f'durante {self._duracion} s…', flush=True)
        t_inicio = time.monotonic()
        while time.monotonic() - t_inicio < self._duracion:
            self.pub.publish(msg)
            self._t_ultimo_cmd = time.monotonic()
            fin = time.monotonic() + 0.1
            while time.monotonic() < fin:
                rclpy.spin_once(self, timeout_sec=0.01)

        # ── 2. Dejar de publicar y cronometrar ───────────────────────────────
        print(f'  DEJANDO DE PUBLICAR. Esperando que el watchdog pare el robot…',
              flush=True)
        self._t_parada = None
        t_corte = self._t_ultimo_cmd
        limite = t_corte + 3.0
        while self._t_parada is None and time.monotonic() < limite:
            rclpy.spin_once(self, timeout_sec=0.01)

        # ── 3. Informe ───────────────────────────────────────────────────────
        print()
        print(f'  recorrido total medido en /odom      : {self._recorrido_total * 100:.1f} cm')
        esperado = self._velocidad * self._duracion
        print(f'  recorrido esperado ({self._velocidad} m/s x {self._duracion} s)  : '
              f'~{esperado * 100:.1f} cm')
        if self._recorrido_total < 0.02:
            print('  ✗ el robot NUNCA se movió (menos de 2 cm): cmd_vel no llegó al')
            print('    driver, o está en parada de emergencia. Prueba no válida.',
                  file=sys.stderr)
            return 1

        if self._t_parada is None:
            print(f'  ✗ FALLO: 3 s después del último cmd_vel el robot SIGUE MOVIÉNDOSE.')
            print(f'    El watchdog NO funciona. Es un fallo de SEGURIDAD.', file=sys.stderr)
            return 1

        dt = self._t_parada - t_corte
        dist = self._velocidad * dt
        # Timeout del driver + margen físico: frenada, latencia del UART y
        # resolución de /odom. Ver la explicación de la cabecera.
        umbral = self._timeout_esperado + 0.30
        print(f'  tiempo hasta quedar quieto          : {dt * 1000:.0f} ms')
        print(f'    de los cuales, timeout del driver : ~{self._timeout_esperado * 1000:.0f} ms')
        print(f'    frenada + latencia + detección    : ~{(dt - self._timeout_esperado) * 1000:.0f} ms')
        print(f'  distancia recorrida tras el corte   : ~{dist * 100:.1f} cm')
        print()
        if dt < umbral:
            print(f'  ✅ El watchdog funciona: quieto en {dt * 1000:.0f} ms '
                  f'(< {umbral * 1000:.0f} ms)')
            print(f'     Tras perder la red, el robot recorre ~{dist * 100:.1f} cm más.')
            if dist > 0.10:
                print(f'     ⚠️  Más de 10 cm. Si hay obstáculos cerca, considera bajar')
                print(f'        cmd_vel_timeout: a la mitad, la distancia se reduce casi a la mitad.')
            return 0
        if dt < 1.5:
            print(f'  ⚠️  Para, pero tarda {dt * 1000:.0f} ms (esperado < {umbral * 1000:.0f} ms).')
            print('     Mira si el watchdog disparó a tiempo en el log del driver: si el')
            print('     timeout salió bien, lo que sobra es frenada física, no software.')
            return 2
        print(f'  ✗ Tarda {dt * 1000:.0f} ms. Demasiado para un laboratorio remoto.',
              file=sys.stderr)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description='Mide el watchdog de cmd_vel')
    ap.add_argument('--velocidad', type=float, default=0.15, help='m/s (default 0.15)')
    ap.add_argument('--duracion', type=float, default=2.0, help='s (default 2.0)')
    ap.add_argument('--timeout-esperado', type=float, default=0.3,
                    help='cmd_vel_timeout del driver, en s (default 0.3)')
    a = ap.parse_args()

    print('=' * 70)
    print('  Watchdog de cmd_vel — EL ROBOT SE MUEVE. Debe estar en el SUELO.')
    print('=' * 70)

    rclpy.init()
    nodo = MedidorWatchdog(a.velocidad, a.duracion, a.timeout_esperado)
    try:
        return nodo.ejecutar()
    finally:
        # NO se publica un Twist() vacío de cortesía: sería un cmd_vel más, y
        # reactivaría el watchdog del driver haciéndolo disparar una segunda vez
        # 0.3 s después. Se vio en el log del 2026-07-30 y confundía la lectura.
        # El watchdog ya deja el robot parado: para eso existe.
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
