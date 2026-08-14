#!/usr/bin/env python3
"""El botón de Nav2 de extremo a extremo, por PRIMERA vez (cierra el ⏳ de la
evidencia 80): /pedir_nav true → FUNCIONANDO → /pedir_nav false → estado final.

Un solo proceso a propósito (la lección de la 81-84: encadenar `ros2 service
call` levanta un intérprete por llamada). No manda ningún objetivo: el robot
NO se mueve. Mide también el barrido tras el paro (dato del conflicto 2).
"""
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from atriz_rvr_msgs.msg import EstadoNavegacion
from sensor_msgs.msg import LaserScan
from std_srvs.srv import SetBool

NOMBRES = {0: 'APAGADO', 1: 'ARRANCANDO', 2: 'FUNCIONANDO', 3: 'CIEGO',
           4: 'MUDO', 5: 'FALLO', 6: 'DESCONOCIDO'}
qos_be = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)


class Prueba(Node):
    def __init__(self):
        super().__init__('prueba_boton_nav')
        self.estado = None
        self.t_scan = None
        self.n_scan = 0
        self.create_subscription(EstadoNavegacion, 'estado_navegacion',
                                 self._cb, qos_be)
        self.create_subscription(LaserScan, 'scan', self._cb_scan, qos_be)
        self.cli = self.create_client(SetBool, 'pedir_nav')

    def _cb(self, m):
        self.estado = m

    def _cb_scan(self, _m):
        self.t_scan = time.monotonic()
        self.n_scan += 1


def pedir(ex, nodo, valor):
    req = SetBool.Request()
    req.data = valor
    fut = nodo.cli.call_async(req)
    ex.spin_until_future_complete(fut, timeout_sec=10.0)
    r = fut.result()
    print(f'  /pedir_nav {{data: {valor}}} -> success={r.success}')
    print(f'    message: {r.message}')
    return r


def esperar_estado(ex, nodo, objetivo, plazo_s):
    t0 = time.monotonic()
    ultimo = None
    while time.monotonic() - t0 < plazo_s:
        ex.spin_once(timeout_sec=0.2)
        if nodo.estado is not None:
            e = nodo.estado.nav
            if e != ultimo:
                print(f'    t={time.monotonic()-t0:6.1f}s  nav={NOMBRES[e]}'
                      f'  ({nodo.estado.nav_detalle})')
                ultimo = e
            if e == objetivo:
                return time.monotonic() - t0
    return None


def main():
    rclpy.init()
    nodo = Prueba()
    ex = SingleThreadedExecutor()
    ex.add_node(nodo)
    if not nodo.cli.wait_for_service(timeout_sec=5.0):
        print('🔴 /pedir_nav no disponible')
        return 1

    print('── estado previo (5 s de escucha) ──')
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5.0:
        ex.spin_once(timeout_sec=0.2)
    if nodo.estado is None:
        print('🔴 /estado_navegacion no llega: sin supervisor no hay prueba')
        return 1
    print(f'  nav={NOMBRES[nodo.estado.nav]} · hay_mapa={nodo.estado.hay_mapa}'
          f' · mapa={nodo.estado.mapa_nombre}'
          f' · barrido={"ON" if nodo.n_scan else "OFF"} ({nodo.n_scan} scans/5s)')

    print('── ARRANQUE por el botón ──')
    t_pedido = time.monotonic()
    r = pedir(ex, nodo, True)
    if not r.success:
        print('🔴 rechazado — la prueba termina aquí')
        return 1
    t = esperar_estado(ex, nodo, 2, 90.0)   # FUNCIONANDO
    if t is None:
        print('🔴 no llegó a FUNCIONANDO en 90 s')
        return 1
    print(f'  ✅ FUNCIONANDO a los {time.monotonic()-t_pedido:.1f} s del pedido')

    print('── 10 s en régimen (¿se sostiene?) ──')
    n0 = nodo.n_scan
    t0 = time.monotonic()
    while time.monotonic() - t0 < 10.0:
        ex.spin_once(timeout_sec=0.2)
    print(f'  nav={NOMBRES[nodo.estado.nav]} · /scan {(nodo.n_scan-n0)/10.0:.1f} Hz')

    print('── PARO por el botón ──')
    r = pedir(ex, nodo, False)
    t = esperar_estado(ex, nodo, 0, 40.0)   # APAGADO
    print(f'  estado tras el paro: nav={NOMBRES[nodo.estado.nav]}'
          + (f' (a los {t:.1f} s)' if t is not None else ' (no llegó a APAGADO en 40 s)'))

    print('── el barrido tras el paro (10 s de escucha) ──')
    n0 = nodo.n_scan
    t0 = time.monotonic()
    while time.monotonic() - t0 < 10.0:
        ex.spin_once(timeout_sec=0.2)
    hz = (nodo.n_scan - n0) / 10.0
    print(f'  /scan tras parar: {hz:.1f} Hz -> barrido '
          + ('ENCENDIDO' if hz > 1 else 'APAGADO'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
