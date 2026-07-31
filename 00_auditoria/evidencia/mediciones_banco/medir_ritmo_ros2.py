#!/usr/bin/env python3
"""Ritmo y jitter de /odom, /imu y /scan. El sustituto ROS 2 de `medir.py`.

    python3 medir_ritmo_ros2.py            # 30 s
    python3 medir_ritmo_ros2.py --seg 120  # más largo, para ver huecos

No mueve el robot. Necesita el driver corriendo (systemd ya lo arranca solo).

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE ESTE FICHERO
═══════════════════════════════════════════════════════════════════════════════
`medir.py` es de ROS 1 y muere con `ModuleNotFoundError: No module named 'rospy'`.
Seguía recomendado en `CLAUDE.md` y en el RUNBOOK como herramienta de
diagnóstico: una herramienta rota que se recomienda es peor que ninguna.

═══════════════════════════════════════════════════════════════════════════════
🔴 TRES TRAMPAS QUE HACEN QUE ESTA MEDIDA SEA DIFÍCIL DE HACER BIEN
═══════════════════════════════════════════════════════════════════════════════
Las tres se descubrieron el 2026-07-31, y las tres dan números BAJOS sobre un robot
perfectamente sano — que es la peor forma de fallar, porque llevan a «arreglar»
lo que no está roto.

**1. `ros2 topic hz` NO PUEDE MEDIR ESTOS TOPICS.** `/odom`, `/imu` y `/scan` se
   publican **BEST_EFFORT**, y `ros2 topic hz` se suscribe RELIABLE **sin opción
   de cambiarlo** en Jazzy. DDS no empareja y da **0 Hz siempre**.

**2. `rclpy.spin_once(nodo, …)` EN BUCLE PIERDE MENSAJES.** Cada llamada engancha
   el nodo al ejecutor global y lo desengancha al salir; en ese hueco se pierde
   lo que llegue. Dio **11.3 Hz** sobre un robot que iba a **16.5**, medido las
   dos formas en el mismo minuto.
   → Por eso aquí hay un `SingleThreadedExecutor` **persistente**.

**3. Y `mensajes / duración` TAMBIÉN SUBESTIMA.** La primera versión de este mismo
   fichero daba 15.03 Hz mientras su propio intervalo medio decía 60.4 ms, que
   son 16.55. La diferencia es el **descubrimiento de DDS**: los primeros ~1.5 s
   no llega nada, y entran en el denominador.
   → El ritmo se calcula desde los INTERVALOS, que no dependen de cuándo empezó
     a llegar el primer mensaje. Tres formas de medir lo mismo, tres resultados
     bajos: es un aviso de lo fácil que es equivocarse aquí.

Y de ahí la regla que dejó: **antes de creerte un instrumento, comprueba que ve
un estado que ya conoces.**
"""
import argparse
import statistics
import sys
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Imu, LaserScan

#: Lo esperado, de la tabla de referencia del proyecto. Si te desvías, algo cambió.
ESPERADO = {'odom': 16.6, 'imu': 16.6, 'scan': 10.1}

#: 🔴 BEST_EFFORT: es como publican los tres. Con el RELIABLE por defecto de
#: rclpy, DDS no empareja y no llega ni un mensaje. `depth` holgado para que una
#: ráfaga no se pierda por cola corta.
QOS = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                 history=HistoryPolicy.KEEP_LAST, depth=50)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seg', type=float, default=30.0)
    a = ap.parse_args()

    rclpy.init()
    n = Node('medir_ritmo')
    t: dict[str, list[float]] = {'odom': [], 'imu': [], 'scan': []}
    for nombre, tipo in (('odom', Odometry), ('imu', Imu), ('scan', LaserScan)):
        n.create_subscription(tipo, nombre,
                              lambda _m, k=nombre: t[k].append(time.monotonic()),
                              QOS)

    # 🔴 Persistente. Ver la cabecera: con rclpy.spin_once en bucle salen 11 Hz
    # sobre un robot que va a 16.5.
    ex = SingleThreadedExecutor()
    ex.add_node(n)

    print('═' * 74)
    print(f'RITMO DE LA TELEMETRÍA — {a.seg:.0f} s')
    print('═' * 74)
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.seg:
        ex.spin_once(timeout_sec=0.1)
    dur = time.monotonic() - t0

    print(f'{"topic":8s} {"Hz":>7s} {"esperado":>9s} {"medio ms":>9s} '
          f'{"mediana":>8s} {"σ ms":>6s} {"peor hueco":>11s}')
    print('─' * 74)
    problemas = 0
    for k, ts in t.items():
        esp = ESPERADO[k]
        if len(ts) < 3:
            # `scan` sin mensajes NO es un problema: desde el 2026-07-31 el robot
            # arranca con el barrido apagado a propósito. Contarlo como fallo
            # haría que esta herramienta gritara en el estado NORMAL del robot.
            marca = '📝' if k == 'scan' else '🔴'
            print(f'{k:8s} {"—":>7s} {esp:9.1f}   {marca} {len(ts)} mensajes')
            if k != 'scan':
                problemas += 1
            continue
        iv = [b - a_ for a_, b in zip(ts, ts[1:])]
        # 🔴 Desde los INTERVALOS, no `len(ts)/dur`: el descubrimiento de DDS mete
        # ~1.5 s sin mensajes al principio y hunde la media. Ver la cabecera.
        medio = statistics.mean(iv)
        hz = 1.0 / medio if medio > 0 else 0.0
        peor = max(iv)
        marca = '✅' if hz > esp * 0.9 else '🔴'
        print(f'{k:8s} {hz:7.2f} {esp:9.1f} {medio*1000:9.1f} '
              f'{statistics.median(iv)*1000:8.1f} {statistics.pstdev(iv)*1000:6.1f} '
              f'{peor*1000:9.1f} {marca}')
        if hz <= esp * 0.9:
            problemas += 1
        # Un hueco de más de 3× el intervalo nominal no es jitter: es una pausa.
        if peor > 3.0 / esp:
            print(f'         ⚠️ hueco de {peor*1000:.0f} ms — eso no es jitter, es una pausa')

    print('═' * 74)
    if not t['scan']:
        # No es un fallo: desde el 2026-07-31 el robot arranca con el barrido
        # apagado a propósito (manual, cap. 17).
        print('  📝 /scan sin mensajes: probablemente el barrido está APAGADO.')
        print('     Compruébalo con `atriz-escaneo estado`. No es un fallo.')
    if problemas:
        print('  🔴 Algo va por debajo de lo esperado. Antes de tocar el driver:')
        print('     ¿está el robot enchufado a algo que le robe CPU? `uptime`, `vcgencmd get_throttled`')
    else:
        print('  ✅ Todo en su sitio.')
    rclpy.shutdown()
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main())
