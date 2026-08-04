#!/usr/bin/env python3
"""Observa los DOS testigos de una parada de emergencia. Corre EN LA PI.

    python3 observar_parada_emergencia.py            # 90 s de ventana
    python3 observar_parada_emergencia.py --seg 150

═══════════════════════════════════════════════════════════════════════════════
QUÉ ES ESTO Y QUÉ NO
═══════════════════════════════════════════════════════════════════════════════
🔴 **NO publica la parada.** Solo mira. Quien la publica es el PC, con el código
   de producción de `atriz-lab`, porque **esa es la mitad que ha fallado**.

   De los cinco fallos históricos de este botón, el manual dice que el
   **namespace y el QoS solo aparecen publicando de verdad**. El navegador no
   publica con `rclpy`: manda `advertise` + `publish` por WebSocket y es
   **rosbridge** quien resuelve el nombre y el QoS dentro del robot. Un script
   local con `rclpy` ejerce la mitad que menos dudas tiene.

   → Reparto: el **PC publica**, la **Pi observa**, el **usuario mide con cinta**.

═══════════════════════════════════════════════════════════════════════════════
DOS TESTIGOS, Y NO TRES — RETIRADO EL DE LA DISTANCIA EL 2026-08-04
═══════════════════════════════════════════════════════════════════════════════
Este botón ha fallado CINCO veces, y CUATRO devolviendo éxito. Un solo testigo
no basta. Los que da este script son:

  1. el log del driver    tiene que aparecer «PARADA DE EMERGENCIA»
  2. `/estado_robot`      `parada_emergencia` pasa a true   <- el campo NUEVO

Los dos son de PRESENCIA, no de tiempo, y por eso un muestreo a 1 Hz les basta.

🔴 HABÍA UN TERCERO —cuánto recorría el robot tras la parada— Y MENTÍA. Medido
   el 2026-08-04 sobre el MISMO evento de las 09:30:29 que midió el PC:

       PC (sabe cuándo publicó) ....... 2.9 cm
       este script .................... 0.4 cm     🔴

   La causa es de construcción, no un ajuste: el cronómetro arrancaba al ver la
   bandera en `/estado_robot`, **que se publica a 1 Hz**. O sea hasta un segundo
   TARDE, con el robot ya frenado. A 0,20 m/s eso son 20 cm de ventana ciega
   para medir una frenada de 2-3.

   → **Un testigo a 1 Hz no puede cronometrar un evento de 100 ms.** Se retira
     en vez de reajustarlo: quien publica la parada SABE cuándo lo hizo y mide
     esa distancia sin ventana ciega, así que el dato ya existe y mejor. Este
     script no aporta nada ahí y sí estorbaba, dando un número creíble y falso.

⚠️ Y el que de verdad cierra la prueba tampoco lo da este script: **la cinta**.
   `/odom` es odometría comparándose consigo misma.

═══════════════════════════════════════════════════════════════════════════════
DOS TRAMPAS QUE ESTE PROYECTO YA PAGÓ
═══════════════════════════════════════════════════════════════════════════════
🔴 `journalctl --since "-25 s"`, NUNCA `$(date -u +%T)`: `date -u` da hora UTC y
   journalctl la interpreta como local, así que en este robot (UTC−5) la ventana
   cae CINCO HORAS EN EL FUTURO y cuenta 0 aunque la parada haya llegado.

🔴 `rclpy.init(signal_handler_options=SignalHandlerOptions.NO)`: sin esto, un
   Ctrl-C invalida el contexto antes de que se pueda publicar o cerrar limpio.

🔴 Y NO se usa `spin_once()` en bucle para contar: pierde mensajes —11,3 Hz
   medidos sobre un robot a 16,5, y hoy mismo 14,3 sobre 16,5—. Va un
   `SingleThreadedExecutor` persistente.
"""
import argparse
import subprocess
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from rclpy.utilities import remove_ros_args
from rclpy.signals import SignalHandlerOptions

from atriz_rvr_msgs.msg import EstadoRobot

BEST = QoSProfile(depth=10)
BEST.reliability = QoSReliabilityPolicy.BEST_EFFORT


class Observador(Node):
    def __init__(self) -> None:
        super().__init__('observar_parada')
        self.parada_desde: float | None = None
        self.parada_hasta: float | None = None
        self.ultimo_estado: EstadoRobot | None = None
        self.vio_true = False
        self.create_subscription(EstadoRobot, '/estado_robot', self._estado, BEST)


    def _estado(self, m: EstadoRobot) -> None:
        self.ultimo_estado = m
        if m.parada_emergencia and not self.vio_true:
            self.vio_true = True
            self.parada_desde = time.monotonic()
            print(f'\n  🔴 parada_emergencia -> True   (latido={m.latido})')
        elif self.vio_true and not m.parada_emergencia and self.parada_hasta is None:
            self.parada_hasta = time.monotonic()
            print(f'  ✅ parada_emergencia -> False  (liberada, latido={m.latido})')



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seg', type=float, default=90.0, help='ventana de observación')
    args = ap.parse_args(remove_ros_args(args=None)[1:])

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    n = Observador()
    ex = SingleThreadedExecutor()
    ex.add_node(n)

    print('═' * 70)
    print('OBSERVANDO. Este script NO publica la parada: lánzala desde el PC.')
    print(f'Ventana: {args.seg:.0f} s. Ctrl-C para cortar antes.')
    print('═' * 70)
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < args.seg:
            ex.spin_once(timeout_sec=0.1)
            if n.parada_hasta is not None and time.monotonic() - n.parada_hasta > 5:
                break
    except KeyboardInterrupt:
        print('\n  (cortado a mano)')

    print('\n' + '═' * 70)
    print('RESULTADO — los dos testigos')
    print('═' * 70)

    # ── 1 · el log del driver ────────────────────────────────────────────────
    # 🔴 `--since "-90 s"`, no `date -u`: ver la cabecera.
    try:
        sal = subprocess.run(
            ['journalctl', '-u', 'atriz-robot', '--since', f'-{int(args.seg) + 15} s',
             '--no-pager'],
            capture_output=True, text=True, timeout=30).stdout
        golpes = [l for l in sal.splitlines() if 'PARADA DE EMERGENCIA' in l]
        liber = [l for l in sal.splitlines() if 'parada de emergencia liberada' in l]
        if golpes:
            print(f'  1· log del driver ✅ «PARADA DE EMERGENCIA» × {len(golpes)}')
            print(f'                    {golpes[0].strip()[:100]}')
        else:
            print('  1· log del driver 🔴 NO aparece «PARADA DE EMERGENCIA»')
        if liber:
            print(f'                    ✅ «parada de emergencia liberada» × {len(liber)}')
    except Exception as e:                                        # noqa: BLE001
        print(f'  1· log del driver ⚠️ no se pudo leer el journal: {e}')

    # ── 2 · el campo nuevo ───────────────────────────────────────────────────
    if n.vio_true:
        dur = (n.parada_hasta - n.parada_desde) if n.parada_hasta else None
        print('  2· /estado_robot  ✅ parada_emergencia pasó a True'
              + (f' y volvió a False tras {dur:.1f} s' if dur else
                 ' (NO se vio volver a False: ¿se liberó?)'))
    else:
        e = n.ultimo_estado
        print('  2· /estado_robot  🔴 parada_emergencia NUNCA pasó a True'
              + ('' if e else '  (y no llegó ningún /estado_robot: ¿está el driver nuevo?)'))

    print('═' * 70)
    ok = n.vio_true and bool(golpes if 'golpes' in dir() else False)
    print('  Los DOS tienen que coincidir. Uno solo no prueba nada:')
    print('    log sin parada real  -> la recibió y no la aplicó')
    print('    parada sin log       -> paró por otra cosa (el watchdog corta a 0,3 s)')
    print('═' * 70)

    n.destroy_node()
    rclpy.shutdown()
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
