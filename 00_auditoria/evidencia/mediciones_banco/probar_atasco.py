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
from std_msgs.msg import Empty
from atriz_rvr_msgs.msg import MotorStatus
from atriz_rvr_msgs.srv import MoveTimed


def _driver_corriendo() -> bool:
    """🔴 Sin esto, dos procesos se pelean por `/dev/rvr` en silencio."""
    try:
        s = subprocess.run(['ps', '-eo', 'comm'], capture_output=True, text=True, timeout=5)
        # 🔴 `comm` TRUNCA A 15 CARACTERES, y `rvr_driver_node` mide exactamente
        #    15. Vale hoy por un carácter: renombrarlo a `rvr_driver_nodo` (16)
        #    lo dejaría en `rvr_driver_nod` y el guardia diría «no corre» para
        #    siempre, en silencio. Se comprueba el prefijo truncado.
        return any(c.startswith('rvr_driver_nod') for c in s.stdout.split())
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
    a = ap.parse_args()          # 🔴 el resultado SE DESCARTABA: `--vel 0.02` se
                                 #    aceptaba sin protestar y el robot salía a
                                 #    0.08 igual. Encontrado en auditoría 2026-08-01.

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
    par = n.create_publisher(Empty, 'emergency_stop', 10)
    ex = SingleThreadedExecutor()
    ex.add_node(n)
    if not cli.wait_for_service(timeout_sec=15.0):
        print('🔴 no responde move_timed. ¿corre el driver?')
        _cerrar(n, par)
        return 1

    # 🔴🔴 Ctrl-C AQUÍ ERA PELIGROSO Y NO SE HABÍA VISTO. `move_timed` es un
    #    servicio: el empuje corre **en el driver**, no aquí. Matar el cliente no
    #    para nada — el robot seguía empujando los 6 s **con las manos del usuario
    #    sujetándolo**, que es exactamente la postura que esta prueba exige. Y el
    #    reflejo ante un robot que hace algo raro es Ctrl-C.
    #    Ahora Ctrl-C publica la parada de emergencia por el camino canónico.
    #    Encontrado en auditoría el 2026-08-01.
    try:
        return _prueba(a, n, ex, cli, par, ms)
    except KeyboardInterrupt:
        print('\n\n  ⛔ Ctrl-C — PARANDO EL ROBOT…')
        _cerrar(n, par)
        print('  ✅ parada enviada. Suelta el robot.')
        return 130


def _prueba(a, n, ex, cli, par, ms) -> int:
    print('═' * 74)
    print('DETECCIÓN DE ATASCO — prueba del positivo verdadero')
    print('═' * 74)
    print(f'\n  ⛔ Ctrl-C en cualquier momento PARA EL ROBOT (parada de emergencia).')
    print('\n  🔴 BLOQUEA EL ROBOT AHORA. Presiona el chasis contra el suelo, o')
    print('     calza un libro contra UNA oruga. NO metas los dedos.')
    for s in (5, 4, 3, 2, 1):
        print(f'     empieza en {s}…', flush=True)
        time.sleep(1)

    print(f'\n  ⚠️ ordenando avance a {a.vel} m/s durante {a.seg} s (por move_timed)…\n')
    req = MoveTimed.Request()
    req.linear, req.angular, req.duration = a.vel, 0.0, a.seg
    fut = cli.call_async(req)

    t0 = time.monotonic()
    visto = None
    # 🔴 ACUMULADOR, no «último estado visto». El firmware emite «atasco
    #    resuelto» en cuanto termina el empuje, así que `visto` volvía a
    #    (False, False) y la herramienta imprimía «NO detectó atasco»
    #    **habiéndolo detectado**. Es justo el falso negativo que esta prueba
    #    existe para descartar. Encontrado en auditoría el 2026-08-01.
    hubo = [False, False]
    # 🔴 Y se vacía la cola JUSTO ANTES del empuje. El suscriptor lleva vivo
    #    desde antes de la cuenta atrás, así que un `atascado=True` de un intento
    #    ANTERIOR seguía en `ms` y el acumulador —que solo suma— lo daba por
    #    bueno: «✅ ATASCO DETECTADO» sin haber empujado. Un falso positivo en la
    #    herramienta que existe para descartar un falso negativo es peor que no
    #    tenerla. Encontrado en auditoría el 2026-08-01.
    ms.clear()
    while time.monotonic() - t0 < a.seg + 3.0:
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
        if fut.done() and time.monotonic() - t0 > a.seg + 1.0:
            break

    return _informe(hubo, n, par)


def _informe(hubo, n, par) -> int:
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
    _cerrar(n, par)
    return 0


def _cerrar(n, par) -> None:
    """🔴 Para el robot ANTES de soltar el nodo. Ver el comentario de main()."""
    try:
        par.publish(Empty())
        time.sleep(0.3)          # que salga por el cable antes de destruir el nodo
    except Exception:                                       # noqa: BLE001
        pass
    try:
        n.destroy_node()
        rclpy.shutdown()
    except Exception:                                       # noqa: BLE001
        pass


if __name__ == '__main__':
    raise SystemExit(main())
