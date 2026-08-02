#!/usr/bin/env python3
"""Prueba de aceptacion de un robot: de arranque en frio a navegacion autonoma.

    python3 prueba_aceptacion.py            # las diez fases
    python3 prueba_aceptacion.py --desde F4 # retomar sin repetir

⚠️ EL ROBOT SE MUEVE en F4, F5, F6 y F7, y enciende LEDs en F3. Es GUIADA: se
   para y te dice que hacer antes de cada fase fisica.

⛔ Ctrl-C en cualquier momento PARA EL ROBOT (parada de emergencia).

📎 Criterio, umbrales y por que de cada fase: 03_operacion/PRUEBA_ACEPTACION.md
"""
import argparse
import math
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from aceptacion_nucleo import (                                  # noqa: E402
    PASA, REVISAR, FALLO, PENDIENTE, PENDIENTES_CONOCIDOS, Resultado,
    juzgar_banda, juzgar_categorico, no_verificado,
    hay_via_libre, formatear_informe,
)

import rclpy                                                     # noqa: E402
from rclpy.node import Node                                      # noqa: E402
from rclpy.executors import SingleThreadedExecutor               # noqa: E402
from rclpy.qos import (QoSProfile, ReliabilityPolicy,            # noqa: E402
                       DurabilityPolicy)
from rclpy.signals import SignalHandlerOptions                   # noqa: E402
from std_msgs.msg import Empty                                   # noqa: E402
from std_srvs.srv import Empty as EmptySrv                       # noqa: E402

#: Umbral de aborto. 7.0 V es el «baja» que devuelve el FIRMWARE, verificado en
#: el journal el 2026-08-01. Por debajo, los motores dan menos y mediriamos una
#: regresion que no existe.
BATERIA_MINIMA_V = 7.0
#: Tope para «el servicio subio EN EL ARRANQUE». Medido: 23 s tras el boot
#: (evidencia 47). Con 120 s hay holgura de sobra, y si alguien lo levanto a mano
#: la diferencia serian minutos u horas, no segundos.
ARRANQUE_MAXIMO_S = 120.0

BE = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
FIABLE = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


def driver_corriendo() -> bool:
    """🔴 `ps -o comm` TRUNCA A 15 CARACTERES y `rvr_driver_node` mide 15 justos."""
    try:
        s = subprocess.run(['ps', '-eo', 'comm'], capture_output=True,
                           text=True, timeout=5)
        return any(c.startswith('rvr_driver_nod') for c in s.stdout.split())
    except Exception:                                            # noqa: BLE001
        return True                          # ante la duda, se asume que si


def matar_por_comm(prefijo: str) -> int:
    """Mata por nombre de proceso. 🔴 NUNCA `pkill -f`: su patron casa con la
    linea de comando entera, asi que alcanza a procesos que solo MENCIONAN el
    nombre — incluida esta misma prueba."""
    n = 0
    try:
        s = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True,
                           text=True, timeout=5)
        for linea in s.stdout.splitlines()[1:]:
            partes = linea.split(None, 1)
            if len(partes) == 2 and partes[1].strip().startswith(prefijo[:15]):
                os.kill(int(partes[0]), signal.SIGINT)
                n += 1
    except Exception:                                            # noqa: BLE001
        pass
    return n


class Aceptacion:
    def __init__(self, guiada=True):
        self.res: list[Resultado] = []
        self.guiada = guiada
        # 🔴🔴 `SignalHandlerOptions.NO` NO ES OPCIONAL, Y ES LO QUE HACE QUE LA
        #    PARADA DE EMERGENCIA FUNCIONE. `rclpy.init()` a secas instala su
        #    propio manejador de SIGINT que **invalida el contexto** antes de que
        #    el `except KeyboardInterrupt` llegue a publicar:
        #        RCLError: Failed to publish: publisher's context is invalid
        #    Medido el 2026-08-02 con el driver escuchando: por defecto **0
        #    lineas** de «PARADA DE EMERGENCIA» en el journal; con NO, **5**.
        #    ⚠️ Y es INTERMITENTE segun donde caiga el Ctrl-C, que es como paso la
        #       verificacion del 2026-08-01. Un fallo de seguridad que funciona a
        #       veces es peor que uno que no funciona nunca.
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        self.nodo = Node('prueba_aceptacion')
        self.ex = SingleThreadedExecutor()
        self.ex.add_node(self.nodo)
        self.parada_pub = self.nodo.create_publisher(Empty, 'emergency_stop', FIABLE)
        self.liberar = self.nodo.create_client(EmptySrv, 'release_emergency_stop')

    # ── registro ──────────────────────────────────────────────────────────
    def add(self, r: Resultado) -> Resultado:
        icono = {PASA: '  ok ', REVISAR: ' REV ', FALLO: 'FALLO', PENDIENTE: 'PEND '}
        print(f'    [{icono[r.veredicto]}] {r.concepto}')
        if r.detalle:
            print(f'            {r.detalle}')
        self.res.append(r)
        return r

    # ── puertas ───────────────────────────────────────────────────────────
    def puerta(self, texto: str) -> None:
        """Se para hasta que el usuario confirme. NO se salta nunca en las fases
        que mueven el robot: arrancar un motor con algo delante que nadie
        esperaba es como se rompen robots y dedos."""
        print('\n' + '─' * 74)
        print(f'  🔴 {texto}')
        print('─' * 74)
        if not self.guiada:
            print('     (--sin-puertas: se continua)')
            time.sleep(2)
            return
        print('     Pulsa Enter cuando este listo (o Ctrl-C para abortar)…')
        sys.stdin.readline()

    # ── seguridad ─────────────────────────────────────────────────────────
    def parada_emergencia(self) -> None:
        """Publica la parada por el camino canonico y espera a que salga.

        🔴 `move_timed` y los demas servicios de movimiento corren EN EL DRIVER.
           Matar este proceso no para el robot: lo unico que lo corta es esto.
        """
        for _ in range(5):
            self.parada_pub.publish(Empty())
            self.ex.spin_once(timeout_sec=0.05)
        time.sleep(0.3)

    def liberar_parada(self) -> bool:
        if not self.liberar.wait_for_service(timeout_sec=5.0):
            return False
        fut = self.liberar.call_async(EmptySrv.Request())
        fin = time.monotonic() + 5.0
        while not fut.done() and time.monotonic() < fin:
            self.ex.spin_once(timeout_sec=0.05)
        return fut.done()

    # ── utilidades ────────────────────────────────────────────────────────
    def llamar(self, cliente, req, timeout=10.0):
        """🔴 TODA llamada lleva tope. Una sola sin el cuelga la prueba entera en
        silencio — paso con get_battery_percentage() el 2026-07-30."""
        if not cliente.wait_for_service(timeout_sec=timeout):
            return None
        fut = cliente.call_async(req)
        fin = time.monotonic() + timeout
        while not fut.done() and time.monotonic() < fin:
            self.ex.spin_once(timeout_sec=0.05)
        return fut.result() if fut.done() else None

    def esperar(self, topic, tipo, qos, segundos=5.0) -> list:
        """Recoge mensajes con el ejecutor PERSISTENTE.

        🔴 `rclpy.spin_once(nodo, ...)` en bucle PIERDE MENSAJES: engancha el nodo
           al ejecutor global y lo desengancha al salir, y en ese hueco se pierde
           lo que llegue. Dio 11.3 Hz sobre un robot que iba a 16.5.
        """
        buf = []
        sub = self.nodo.create_subscription(tipo, topic, lambda m: buf.append(m), qos)
        fin = time.monotonic() + segundos
        while time.monotonic() < fin:
            self.ex.spin_once(timeout_sec=0.05)
        self.nodo.destroy_subscription(sub)
        return buf

    def ritmo(self, topic, tipo, qos, segundos=5.0):
        """Hz reales: (n-1) intervalos entre el primer y el ultimo sello.

        🔴 `mensajes / duracion` SUBESTIMA: mete el descubrimiento de DDS en el
           denominador. Se mide entre el primer y el ultimo mensaje recibidos.
        """
        buf = self.esperar(topic, tipo, qos, segundos)
        if len(buf) < 3:
            return None
        t = [m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 for m in buf]
        span = t[-1] - t[0]
        return (len(t) - 1) / span if span > 0 else None

    def pos_yaw(self):
        """(x, y, yaw en radianes) de /odom. None si no llega nada."""
        from nav_msgs.msg import Odometry
        b = self.esperar('odom', Odometry, BE, 2.0)
        if not b:
            return None
        p, q = b[-1].pose.pose.position, b[-1].pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                         1 - 2 * (q.y ** 2 + q.z ** 2))
        return p.x, p.y, yaw

    def cerrar(self):
        self.parada_emergencia()
        self.liberar_parada()
        try:
            self.nodo.destroy_node()
            rclpy.shutdown()
        except Exception:                                        # noqa: BLE001
            pass


def delta_angulo(a, b) -> float:
    """b - a normalizado a (-pi, pi].

    🔴 Sin esto NO SE PUEDE MEDIR UN GIRO DE 360°: atan2 devuelve -pi..pi, asi que
       una vuelta entera se lee como ~0. F5 acumula estos deltas.
    """
    d = b - a
    while d > math.pi:
        d -= 2 * math.pi
    while d <= -math.pi:
        d += 2 * math.pi
    return d


def guardas(a: Aceptacion) -> str | None:
    """Devuelve el motivo de aborto, o None si se puede seguir."""
    if not driver_corriendo():
        return ('el driver no esta corriendo. Esta prueba lo necesita:\n'
                '     sudo systemctl start atriz-robot')

    # 🔴 35 s, NO 8. `/battery_state` se publica **cada 30 s exactos** (es el
    #    latido del keepalive), asi que una ventana de 8 s casi nunca ve un
    #    mensaje y la guarda abortaria por «no llega» con la bateria perfecta.
    #    Medido el 2026-08-02: **1 mensaje en 40 s, el primero a los 15.3 s**.
    from sensor_msgs.msg import BatteryState
    print('    esperando a /battery_state (se publica cada 30 s)…')
    b = a.esperar('battery_state', BatteryState, FIABLE, 35.0)
    if not b:
        return ('no llega /battery_state en 35 s. Sin saber la bateria no se mueve\n'
                '     nada. ¿Esta el driver publicando? journalctl -u atriz-robot -n 40')
    v = b[-1].voltage
    if v == v and v < BATERIA_MINIMA_V:     # v==v descarta NaN
        return (f'bateria a {v:.2f} V, por debajo de {BATERIA_MINIMA_V} V (umbral '
                f'«baja» del firmware).\n     Con la bateria caida los motores dan '
                f'menos y mediriamos una regresion que no existe. Cargalo.')
    print(f'    bateria {v:.2f} V · {b[-1].percentage * 100:.0f} %')
    return None


FASES = []          # se llena con @fase en las tareas 4-11


def fase(clave, titulo, mueve=False):
    def deco(fn):
        FASES.append((clave, titulo, mueve, fn))
        return fn
    return deco


def ejecutar(a: Aceptacion, desde: str) -> int:
    claves = [f[0] for f in FASES]
    if desde not in claves:
        print(f'🔴 fase «{desde}» desconocida. Hay: {", ".join(claves)}')
        return 1
    for clave, titulo, mueve, fn in FASES[claves.index(desde):]:
        print(f'\n{"═" * 74}\n  {clave} · {titulo}' +
              ('   ⚠️ MUEVE EL ROBOT' if mueve else '') + f'\n{"═" * 74}')
        try:
            fn(a)
        except KeyboardInterrupt:
            raise
        except Exception as e:                                   # noqa: BLE001
            a.parada_emergencia()
            a.add(juzgar_categorico(f'{clave} completa', False, clave,
                                    f'la fase reventó: {type(e).__name__}: {e}'))
            print(f'\n  🔴 {clave} reventó. El robot esta parado.')
            print('     ¿Sigues con las demas fases? [s/N] ', end='', flush=True)
            if sys.stdin.readline().strip().lower() != 's':
                break
    ruta = escribir_informe(a)
    print(formatear_informe(a.res, cabecera()))
    print(f'\n  📄 informe: {ruta}')
    return 0 if hay_via_libre(a.res) else 2


def cabecera() -> str:
    return (f'PRUEBA DE ACEPTACION · {os.uname().nodename} · '
            f'{time.strftime("%Y-%m-%d %H:%M:%S")}')


def escribir_informe(a: Aceptacion, abortada=False) -> str:
    """Se escribe SIEMPRE, pase o falle. Un informe que solo aparece cuando todo
    va bien no sirve para depurar nada."""
    res = list(a.res) + PENDIENTES_CONOCIDOS
    d = pathlib.Path.home() / 'atriz_migracion' / '00_auditoria' / 'evidencia_24_04'
    d.mkdir(parents=True, exist_ok=True)
    ruta = d / f'47_aceptacion_{time.strftime("%Y%m%d_%H%M%S")}.txt'
    cab = cabecera() + ('  ⚠️ ABORTADA POR Ctrl-C' if abortada else '')
    ruta.write_text(formatear_informe(res, cab), encoding='utf-8')
    a.res = res
    return str(ruta)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--desde', default='F0', help='retomar desde una fase (F0…F9)')
    ap.add_argument('--sin-puertas', action='store_true',
                    help='no esperar confirmacion (solo para las fases sin movimiento)')
    args = ap.parse_args()          # 🔴 argparse LO PRIMERO: `--help` no debe mover nada

    a = Aceptacion(guiada=not args.sin_puertas)
    try:
        motivo = guardas(a)
        if motivo:
            print(f'\n🔴 {motivo}')
            a.cerrar()
            return 1
        return ejecutar(a, args.desde)
    except KeyboardInterrupt:
        print('\n\n  ⛔ Ctrl-C — PARANDO EL ROBOT…')
        # 🔴 Y SE BLOQUEA LA SEÑAL: la recuperacion tarda varios segundos, y quien
        #    ve que el robot no para al primer Ctrl-C pulsa un segundo. Ese
        #    segundo abortaba la recuperacion a medias.
        previo = signal.signal(signal.SIGINT, signal.SIG_IGN)
        print('     (Ctrl-C ignorado hasta que termine — deja que acabe)')
        try:
            a.parada_emergencia()
            print('     ✅ parada enviada. Suelta el robot.')
            a.liberar_parada()
            escribir_informe(a, abortada=True)
        finally:
            signal.signal(signal.SIGINT, previo)
        a.cerrar()
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
