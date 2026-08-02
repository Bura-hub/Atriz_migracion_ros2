#!/usr/bin/env python3
"""¿Llegan las notificaciones de FALLO y TÉRMICA? Repetición por el camino bueno.

    python3 probar_notif_fallo_termica.py          # 10 ciclos, ~100 s de bloqueo
    python3 probar_notif_fallo_termica.py --ciclos 6

⚠️ EL ROBOT EMPUJA CONTRA TU BLOQUEO Y LOS MOTORES SE CALIENTAN A PROPÓSITO.

🔴 **Ctrl-C publica la PARADA DE EMERGENCIA**, que es lo único que corta un
   `move_timed` en marcha. Hasta el 2026-08-01 esta cabecera decía «Ctrl-C lo
   para en cualquier momento» y **era falso**: el movimiento lo ejecuta el
   servidor en su propio bucle, así que el robot seguía empujando hasta 10 s más
   con el usuario sujetándolo. Encontrado en auditoría.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ HAY QUE REPETIRLAS
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-01 se midió que las tres notificaciones de motor «se registran sin
error y no emiten ni un mensaje», y de ahí salieron varias conclusiones.

🔴 **La del ATASCO resultó ser FALSA** (evidencia 44): sí llega, 3 de 3, y acierta
   la oruga. El error estaba en el método — aquella prueba forzó los motores con
   `raw_motors` (PWM crudo), que **se salta el sistema de control del RVR**, y la
   detección vive dentro de ese sistema.

⚠️ **Las otras dos siguen sin verificarse, pero NO por el mismo motivo.** La
   térmica se probó con **100 s de escucha pasiva**, sin forzar nada — no tiene
   el defecto que se le atribuyó. Lo que falta es llegar a la temperatura de
   disparo, que es lo que esta herramienta intenta.

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE PROVOCAN
═══════════════════════════════════════════════════════════════════════════════
· **Térmica** — un motor bloqueado consume corriente sin girar, y eso calienta el
  bobinado. Es exactamente el escenario para el que existe la protección térmica.
  Estados: 0 = ok · 1 = warn · 2 = critical.
· **Fallo** — es un fallo ELÉCTRICO. No se puede provocar a voluntad sin romper
  algo, y no se va a intentar. Lo que se comprueba es si **aparece sola** bajo
  carga extrema, que es cuando tendría sentido.

🔴 SEGURIDAD: se aborta a los **55 °C**, no a 65.

   ⚠️ Y el margen es a propósito: la temperatura de `/motor_status` **se sondea
      cada 30 s**, así que el valor que lee esta prueba puede tener medio minuto
      de retraso. Con el tope en 65 el corte real llegaba muy por encima de 65.
      La herramienta ahora **mira `antiguedad_termico_s`** y avisa si el dato
      está viejo.

   🔴 CUÁNTO es ese sobrepaso: NO se sabe con precisión, y el número que se venía
      usando (~3 °C, de «~6.5 °C/min») **está subestimado**. En la única tirada
      que existe el ritmo **no es constante y va subiendo**: 5.0 → 8.4 → 10.2
      °C/min entre tramos consecutivos. Con el último ritmo medido el sobrepaso
      son **~5 °C**, no 3, y **la extrapolación empeora cuanto más caliente**,
      que es justo el régimen en el que importa.
      Por eso 55: 55 + 5 = 60, aún lejos de cualquier daño. **El margen se
      sostiene por holgura, no por la cifra.** No lo subas apoyándote en 6.5.
"""
import argparse
import time
import rclpy
from rclpy.signals import SignalHandlerOptions
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from atriz_rvr_msgs.msg import MotorStatus
from atriz_rvr_msgs.srv import MoveTimed

#: 🔴 55 y no 65: el dato llega con hasta 30 s de retraso (sondeo del driver) y
#: el ritmo medido va de 5 a 10 °C/min **y subiendo**, así que el sobrepaso llega
#: a ~5 °C. Ver la cabecera: NO uses «6.5 °C/min» para recalcular este tope.
TOPE_C = 55.0
#: Si el dato de temperatura es más viejo que esto, no sirve para cortar.
EDAD_MAX_S = 45.0
ESTADOS = {0: 'ok', 1: 'WARN', 2: 'CRITICAL'}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ciclos', type=int, default=10)
    ap.add_argument('--seg', type=float, default=10.0, help='segundos por ciclo')
    ap.add_argument('--vel', type=float, default=0.20, help='m/s comandados')
    a = ap.parse_args()

    # 🔴🔴 `SignalHandlerOptions.NO` NO ES OPCIONAL AQUI, Y COSTO ENCONTRARLO.
#    `rclpy.init()` instala SU PROPIO manejador de SIGINT, que **invalida el
#    contexto** antes de que el `except KeyboardInterrupt` llegue a publicar. La
#    parada de emergencia moria con:
#        RCLError: Failed to publish: publisher's context is invalid
#    Medido el 2026-08-02, con el driver escuchando: por defecto **0 lineas** de
#    «PARADA DE EMERGENCIA» en el journal; con NO, **5**.
#    ⚠️ Y es INTERMITENTE: segun donde caiga el Ctrl-C a veces si publicaba, que
#       es como paso la verificacion del 2026-08-01. Un fallo de seguridad que
#       funciona a veces es peor que uno que no funciona nunca.
#    → Con NO, el SIGINT lo maneja Python: el `except KeyboardInterrupt` corre con
#      el contexto VIVO y la parada sale de verdad.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
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
        edad = m.antiguedad_termico_s
        if edad < 0 or edad > EDAD_MAX_S:
            print(f'\n  ⚠️ ABORTADO: el dato de temperatura tiene {edad:.0f} s '
                  f'(máx {EDAD_MAX_S:.0f}). Sin dato fresco no hay corte fiable.')
            break
        if pico > TOPE_C:
            print(f'\n  ⚠️ ABORTADO: {pico:.1f} °C supera el tope de {TOPE_C:.0f} °C '
                  f'(dato de hace {edad:.0f} s).')
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
        # 🔴 El `move_timed` corre en el SERVIDOR y no se entera de este Ctrl-C.
        #    Lo único que lo corta es la parada de emergencia.
        print('\n  🔴 Ctrl-C — publicando PARADA DE EMERGENCIA para cortar el empuje…')
        # 🔴🔴 Y SE BLOQUEA LA SEÑAL mientras dura esto. Este bloque tarda hasta
        #    ~11 s (cinco publicaciones + dos esperas de 5 s), y un usuario que ve
        #    que el robot no para al primer Ctrl-C pulsa un segundo — es el
        #    reflejo. Ese segundo Ctrl-C caía DENTRO de la recuperación y la
        #    abortaba: si llegaba antes del bucle de publicación **el robot no
        #    llegaba a pararse**, y si llegaba después quedaba parado sin liberar,
        #    obedeciendo a nadie hasta que alguien lo supiera desbloquear.
        #    El manejador de Ctrl-C tenía el mismo fallo que venía a arreglar.
        #    Encontrado en auditoría el 2026-08-01.
        import signal as _sig
        _previo = _sig.signal(_sig.SIGINT, _sig.SIG_IGN)
        print('     (Ctrl-C ignorado hasta que termine — deja que acabe)')
        try:
            import rclpy as _r
            from rclpy.node import Node as _N
            from rclpy.qos import (QoSProfile as _Q, ReliabilityPolicy as _R,
                                   DurabilityPolicy as _D)
            from std_msgs.msg import Empty as _E
            from std_srvs.srv import Empty as _ES
            if not _r.ok():
                _r.init()
            n2 = _N('abortar_atasco')
            q = _Q(depth=10, reliability=_R.RELIABLE, durability=_D.VOLATILE)
            pub = n2.create_publisher(_E, 'emergency_stop', q)
            for _ in range(5):
                pub.publish(_E())
                _r.spin_once(n2, timeout_sec=0.1)
            print('     ✅ parada publicada. Liberándola…')
            cli = n2.create_client(_ES, 'release_emergency_stop')
            if cli.wait_for_service(timeout_sec=5.0):
                f = cli.call_async(_ES.Request())
                _r.spin_until_future_complete(n2, f, timeout_sec=5.0)
                print('     ✅ liberada. El robot vuelve a obedecer.')
            else:
                print('     ⚠️ no respondió /release_emergency_stop.')
                print('        Libérala tú: ros2 service call /release_emergency_stop '
                      'std_srvs/srv/Empty')
            n2.destroy_node()
            _r.shutdown()
        except Exception as e:                              # noqa: BLE001
            print(f'     🔴 no se pudo publicar la parada: {e}')
            print('        HAZLO A MANO: ros2 topic pub --once /emergency_stop '
                  'std_msgs/msg/Empty "{}"')
        finally:
            _sig.signal(_sig.SIGINT, _previo)               # se devuelve la señal
        raise SystemExit(130)
