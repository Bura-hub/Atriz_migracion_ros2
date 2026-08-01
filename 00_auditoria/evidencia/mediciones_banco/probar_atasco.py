#!/usr/bin/env python3
"""¿Detecta el driver un atasco de verdad? Necesita que BLOQUEES el robot.

    python3 probar_atasco.py      # NO hace falta encender el barrido

⚠️ EL ROBOT INTENTA AVANZAR MUY DESPACIO (0.08 m/s) durante 6 s. Tú lo bloqueas.

═══════════════════════════════════════════════════════════════════════════════
CÓMO BLOQUEARLO SIN PILLARTE LOS DEDOS
═══════════════════════════════════════════════════════════════════════════════
🔴 **NO metas los dedos entre la oruga y el chasis.** Usa una de estas:

   · Ponlo contra una pared o algo pesado y **presiona el chasis hacia abajo**
     con la palma abierta. En moqueta agarra; en suelo liso puede patinar.
   · O calza un **libro o un zapato** contra UNA sola oruga: así se comprueba
     además que identifica CUÁL está trabada.

📝 Si las orugas PATINAN, el detector NO saltará — y es correcto: los encoders
   siguen girando. Eso está documentado como su límite. Si patina, prueba en
   moqueta o bloqueando una oruga con un objeto.

═══════════════════════════════════════════════════════════════════════════════
QUÉ SE ESTÁ COMPROBANDO
═══════════════════════════════════════════════════════════════════════════════
El hueco de la detección de atasco estuvo abierto desde el principio y **se llegó
a dar por imposible**: el firmware no emite notificaciones de atasco, el SDK no
tiene `get_motor_stall_state`, y la corriente de los motores devuelve `bad_cid`.

La salida no fue leer nada nuevo, sino usar lo que ya se publicaba: **se le ordena
moverse y los encoders no avanzan**. Los falsos positivos ya están verificados
(en reposo y moviéndose libre no salta). Falta el positivo verdadero, que es esto.
"""
import argparse
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from atriz_rvr_msgs.msg import MotorStatus
from atriz_rvr_msgs.srv import MoveTimed


def _driver_corriendo() -> bool:
    """🔴 Sin esto, dos procesos se pelean por `/dev/rvr` en silencio."""
    try:
        s = subprocess.run(['ps', '-eo', 'comm'], capture_output=True, text=True, timeout=5)
        return 'rvr_driver_node' in s.stdout.split()
    except Exception:                                       # noqa: BLE001
        return True          # ante la duda, se asume que sí


def main() -> int:
    # 🔴 `argparse` LO PRIMERO. Sin él, `python3 probar_atasco.py --help` —lo que
    #    teclea cualquiera para leer los avisos— **movía el robot**. Encontrado
    #    en auditoría el 2026-08-01.
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--vel', type=float, default=0.08, help='m/s comandados')
    ap.add_argument('--seg', type=float, default=6.0, help='duración del empuje')
    ap.parse_args()

    if not _driver_corriendo():
        print('🔴 el driver no está corriendo. Esta prueba lo necesita:')
        print('   sudo systemctl start atriz-robot')
        return 1

    rclpy.init()
    n = Node('probar_atasco')
    ms = []
    n.create_subscription(MotorStatus, 'motor_status', lambda m: ms.append(m),
                          QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
    cli = n.create_client(MoveTimed, 'move_timed')
    ex = SingleThreadedExecutor()
    ex.add_node(n)
    if not cli.wait_for_service(timeout_sec=15.0):
        print('🔴 no responde move_timed. ¿corre el driver?')
        rclpy.shutdown()
        return 1

    print('═' * 74)
    print('DETECCIÓN DE ATASCO — prueba del positivo verdadero')
    print('═' * 74)
    print('\n  🔴 BLOQUEA EL ROBOT AHORA. Presiona el chasis contra el suelo, o')
    print('     calza un libro contra UNA oruga. NO metas los dedos.')
    for s in (5, 4, 3, 2, 1):
        print(f'     empieza en {s}…', flush=True)
        time.sleep(1)

    print('\n  ⚠️ ordenando avance a 0.08 m/s durante 6 s (por move_timed)…\n')
    req = MoveTimed.Request()
    req.linear, req.angular, req.duration = 0.08, 0.0, 6.0
    fut = cli.call_async(req)

    t0 = time.monotonic()
    visto = None
    # 🔴 ACUMULADOR, no «último estado visto». El firmware emite «atasco
    #    resuelto» en cuanto termina el empuje, así que `visto` volvía a
    #    (False, False) y la herramienta imprimía «NO detectó atasco»
    #    **habiéndolo detectado**. Es justo el falso negativo que esta prueba
    #    existe para descartar. Encontrado en auditoría el 2026-08-01.
    hubo = [False, False]
    while time.monotonic() - t0 < 9.0:
        ex.spin_once(timeout_sec=0.05)
        if ms:
            m = ms[-1]
            estado = (m.atascado_izquierdo, m.atascado_derecho)
            hubo[0] = hubo[0] or estado[0]
            hubo[1] = hubo[1] or estado[1]
            if estado != visto:
                visto = estado
                print(f'     t={time.monotonic()-t0:4.1f}s  izq={m.atascado_izquierdo}'
                      f'  der={m.atascado_derecho}'
                      f'  antigüedad={m.antiguedad_atasco_s:+.1f}s')
        if fut.done() and time.monotonic() - t0 > 7.0:
            break

    print('\n' + '═' * 74)
    if hubo[0] or hubo[1]:
        cual = ('izquierda' if hubo[0] and not hubo[1] else
                'derecha' if hubo[1] and not hubo[0] else 'LAS DOS')
        print(f'  ✅ ATASCO DETECTADO — oruga: {cual}')
        print('     El hueco que se dio por imposible queda CERRADO.')
    else:
        print('  🔴 NO detectó atasco. Dos explicaciones posibles, y hay que')
        print('     distinguirlas antes de tocar el código:')
        print('       · las orugas PATINABAN (los encoders giraban) → es el')
        print('         límite conocido del método, no un fallo. Reprueba en')
        print('         moqueta o calzando una oruga.')
        print('       · el robot se movió de verdad → no estaba bloqueado.')
        print('     ⚠️ Mira si el robot avanzó: eso lo desempata.')
        print('     📝 Y si NO intentó moverse siquiera, mira el log:')
        print('        journalctl -u atriz-robot -n 40 | grep -i collision')
    print('═' * 74)
    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
