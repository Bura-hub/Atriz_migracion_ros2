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
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from atriz_rvr_msgs.msg import MotorStatus
from atriz_rvr_msgs.srv import MoveTimed


def main() -> int:
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
    while time.monotonic() - t0 < 9.0:
        ex.spin_once(timeout_sec=0.05)
        if ms:
            m = ms[-1]
            estado = (m.atascado_izquierdo, m.atascado_derecho)
            if estado != visto:
                visto = estado
                print(f'     t={time.monotonic()-t0:4.1f}s  izq={m.atascado_izquierdo}'
                      f'  der={m.atascado_derecho}'
                      f'  antigüedad={m.antiguedad_atasco_s:+.1f}s')
        if fut.done() and time.monotonic() - t0 > 7.0:
            break

    print('\n' + '═' * 74)
    if visto and (visto[0] or visto[1]):
        cual = ('izquierda' if visto[0] and not visto[1] else
                'derecha' if visto[1] and not visto[0] else 'LAS DOS')
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
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
