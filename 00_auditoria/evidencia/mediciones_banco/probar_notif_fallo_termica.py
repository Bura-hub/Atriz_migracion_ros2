#!/usr/bin/env python3
"""¿Llegan las notificaciones de FALLO y TÉRMICA? Repetición por el camino bueno.

    python3 probar_notif_fallo_termica.py          # 10 ciclos, ~100 s de bloqueo
    python3 probar_notif_fallo_termica.py --ciclos 6

⚠️ EL ROBOT EMPUJA CONTRA TU BLOQUEO Y LOS MOTORES SE CALIENTAN A PROPÓSITO.
   Ctrl-C lo para en cualquier momento.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ HAY QUE REPETIRLAS
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-01 se midió que las tres notificaciones de motor «se registran sin
error y no emiten ni un mensaje», y de ahí salieron varias conclusiones.

🔴 **La del ATASCO resultó ser FALSA** (evidencia 44): sí llega, 3 de 3, y acierta
   la oruga. El error estaba en el método — aquella prueba forzó los motores con
   `raw_motors` (PWM crudo), que **se salta el sistema de control del RVR**, y la
   detección vive dentro de ese sistema.

⚠️ **Las otras dos se probaron IGUAL DE MAL.** Su resultado negativo es
   sospechoso por la misma razón, y no se puede dar por bueno sin repetirlo por
   el camino que el robot usa de verdad: `drive_rc_si_units`, que es lo que hay
   debajo de `move_timed` y de `cmd_vel`.

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE PROVOCAN
═══════════════════════════════════════════════════════════════════════════════
· **Térmica** — un motor bloqueado consume corriente sin girar, y eso calienta el
  bobinado. Es exactamente el escenario para el que existe la protección térmica.
  Estados: 0 = ok · 1 = warn · 2 = critical.
· **Fallo** — es un fallo ELÉCTRICO. No se puede provocar a voluntad sin romper
  algo, y no se va a intentar. Lo que se comprueba es si **aparece sola** bajo
  carga extrema, que es cuando tendría sentido.

🔴 SEGURIDAD: se aborta si la temperatura pasa de 65 °C. La protección térmica
   del propio RVR limita la potencia antes, que es lo que se está midiendo.
"""
import argparse
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from atriz_rvr_msgs.msg import MotorStatus
from atriz_rvr_msgs.srv import MoveTimed

TOPE_C = 65.0
ESTADOS = {0: 'ok', 1: 'WARN', 2: 'CRITICAL'}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ciclos', type=int, default=10)
    ap.add_argument('--seg', type=float, default=10.0, help='segundos por ciclo')
    ap.add_argument('--vel', type=float, default=0.20, help='m/s comandados')
    a = ap.parse_args()

    rclpy.init()
    n = Node('probar_notif')
    ms = []
    n.create_subscription(MotorStatus, 'motor_status', lambda m: ms.append(m),
                          QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
    cli = n.create_client(MoveTimed, 'move_timed')
    ex = SingleThreadedExecutor()
    ex.add_node(n)
    if not cli.wait_for_service(timeout_sec=15.0):
        print('🔴 no responde move_timed. ¿corre el driver?')
        return 1

    def leer(seg=1.5):
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            ex.spin_once(timeout_sec=0.1)
        return ms[-1] if ms else None

    print('═' * 74)
    print('NOTIFICACIONES DE FALLO Y TÉRMICA — repetición por el camino bueno')
    print('═' * 74)
    m = leer(3.0)
    if m is None:
        print('🔴 sin /motor_status')
        return 1
    print(f'\n  partida: izq {m.temperatura_izquierdo:.1f} °C · '
          f'der {m.temperatura_derecho:.1f} °C · '
          f'térmico {ESTADOS.get(m.estado_termico_izquierdo,"?")}/'
          f'{ESTADOS.get(m.estado_termico_derecho,"?")} · fallo {m.fallo}')
    print(f'\n  🔴 BLOQUEA EL ROBOT y NO LO SUELTES durante ~{a.ciclos*(a.seg+3):.0f} s.')
    print('     Presiona el chasis contra el suelo. NO metas los dedos.')
    print('     Ctrl-C para abortar.')
    for s in (5, 4, 3, 2, 1):
        print(f'     empieza en {s}…', flush=True)
        time.sleep(1)

    base_t = max(m.temperatura_izquierdo, m.temperatura_derecho)
    print(f'\n  {"ciclo":>5}  {"izq °C":>7} {"der °C":>7}  {"térmico":>12}  fallo')
    for i in range(1, a.ciclos + 1):
        req = MoveTimed.Request()
        req.linear, req.angular, req.duration = float(a.vel), 0.0, float(a.seg)
        fut = cli.call_async(req)
        t0 = time.monotonic()
        while time.monotonic() - t0 < a.seg + 1.0:
            ex.spin_once(timeout_sec=0.05)
        m = leer(1.5)
        if m is None:
            continue
        term = f'{ESTADOS.get(m.estado_termico_izquierdo,"?")}/{ESTADOS.get(m.estado_termico_derecho,"?")}'
        print(f'  {i:>5}  {m.temperatura_izquierdo:>7.1f} {m.temperatura_derecho:>7.1f}'
              f'  {term:>12}  {m.fallo}')
        if m.estado_termico_izquierdo or m.estado_termico_derecho:
            print('\n  ✅ NOTIFICACIÓN TÉRMICA: el estado cambió de ok.')
            break
        if m.fallo:
            print('\n  ✅ NOTIFICACIÓN DE FALLO recibida.')
            break
        pico = max(m.temperatura_izquierdo, m.temperatura_derecho)
        if pico > TOPE_C:
            print(f'\n  ⚠️ ABORTADO: {pico:.1f} °C supera el tope de seguridad.')
            break

    print('\n' + '═' * 74)
    m = leer(2.0)
    if m:
        subida = max(m.temperatura_izquierdo, m.temperatura_derecho) - base_t
        print(f'  subida de temperatura: {subida:+.1f} °C en {a.ciclos} ciclos')
        if not (m.estado_termico_izquierdo or m.estado_termico_derecho or m.fallo):
            print('  🔴 NI térmica NI fallo en toda la tanda.')
            print('     ⚠️ Y eso NO prueba que no lleguen: puede que no se haya')
            print('        calentado lo suficiente. Mira la subida de arriba —')
            print('        si es de pocos grados, el ensayo no llegó a exigirle.')
    print('  📝 El sondeo cada 30 s cubre las dos de todos modos.')
    print('═' * 74)
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\n  abortado por el usuario')
