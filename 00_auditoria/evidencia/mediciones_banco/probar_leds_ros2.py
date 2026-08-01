#!/usr/bin/env python3
"""Recorre los 12 grupos de LED del RVR por ROS 2. ¿Sigue habiendo comunicación?

    python3 probar_leds_ros2.py              # uno a uno, 1.5 s cada uno
    python3 probar_leds_ros2.py --pausa 3    # más lento, para mirarlos bien
    python3 probar_leds_ros2.py --sin-bajos  # se salta el LED de los bajos

⚠️ ENCIENDE LEDS. No mueve el robot. Los apaga todos al terminar, también si
   falla o si lo cortas con Ctrl-C.

═══════════════════════════════════════════════════════════════════════════════
QUÉ COMPRUEBA DE VERDAD
═══════════════════════════════════════════════════════════════════════════════
Que el camino **completo** sigue vivo:

    servicio ROS 2 -> driver -> `_pedir` -> SDK -> puerto serie -> RVR -> LED

Un `success=True` recorre todo eso, así que es una prueba de comunicación mucho
más barata que mover el robot. Y los LEDs son de los pocos actuadores que se
pueden ejercitar **sin riesgo y sin espacio**.

🔴 PERO `success=True` NO PRUEBA QUE EL LED SE ENCIENDA. Prueba que el RVR
   aceptó el comando. La única forma de saber si alumbra es MIRARLO — por eso
   este script pausa entre uno y otro y te dice cuál debería estar encendido.
   El proyecto ya se comió un `/color` que publicaba a 16 Hz con el sensor a
   oscuras: «el comando funcionó» y «el hardware hizo algo» son cosas distintas.

═══════════════════════════════════════════════════════════════════════════════
LOS 12 GRUPOS, EN EL ORDEN DE LA TABLA `LEDS` DEL DRIVER
═══════════════════════════════════════════════════════════════════════════════
El `led_id` de `set_led_rgb` es el ÍNDICE en esa tabla, no un valor del SDK.

🔴 `undercarriage_white` NO ENCIENDE NADA, y el servicio devuelve `success=True`.
   Medido el 2026-08-01 con el sensor de luz como testigo: la luz no cambia al
   activarlo. **El LED blanco de los bajos se enciende con
   `enable_color_detection`** —o sea, arrancando con `color_detection:=true`—
   y no por este grupo. Se deja en la lista a propósito: es una comprobación de
   que la comunicación llega, y su fallo está documentado.
   ⚠️ Y NO SE VE DESDE ARRIBA: está bajo el chasis. Hay que levantar el robot.
📝 `all_lights` (índice 11) los enciende TODOS a la vez: sirve de resumen final.
"""
import argparse
import sys
import time

import rclpy
from rclpy.node import Node

from atriz_rvr_msgs.srv import SetLEDRGB, SetLeds

#: El mismo orden que `RvrDriverNode.LEDS`. Si cambia allí, cambia aquí.
GRUPOS = [
    'headlight_left', 'headlight_right',
    'brakelight_left', 'brakelight_right',
    'status_indication_left', 'status_indication_right',
    'battery_door_front', 'battery_door_rear',
    'power_button_front', 'power_button_rear',
    'undercarriage_white', 'all_lights',
]

#: Un color distinto por grupo, para que dos encendidos seguidos no se
#: confundan. El blanco se reserva a los bajos, que es blanco de fábrica.
COLORES = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (255, 128, 0), (128, 0, 255),
    (0, 255, 128), (255, 0, 128), (255, 255, 255), (0, 128, 255),
]


class Probador(Node):
    def __init__(self):
        super().__init__('probar_leds')
        self.cli_uno = self.create_client(SetLEDRGB, 'set_led_rgb')
        self.cli_todos = self.create_client(SetLeds, 'set_leds')

    def esperar(self, seg=15.0) -> bool:
        # 📝 Se espera con un CLIENTE, no con `ros2 service list`: esa lista no
        #    es autoritativa — omitió 1 de los 18 servicios del driver.
        return (self.cli_uno.wait_for_service(timeout_sec=seg)
                and self.cli_todos.wait_for_service(timeout_sec=5.0))

    def encender(self, idx: int, rgb) -> tuple[bool, str]:
        req = SetLEDRGB.Request()
        req.led_id = idx
        req.red, req.green, req.blue = rgb
        fut = self.cli_uno.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=15.0)
        r = fut.result()
        if r is None:
            return False, 'sin respuesta en 15 s'
        return r.success, r.message

    def apagar_todo(self) -> bool:
        req = SetLeds.Request()
        req.rgb_color = [0, 0, 0]
        fut = self.cli_todos.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=15.0)
        return fut.result() is not None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pausa', type=float, default=1.5,
                    help='segundos que se deja encendido cada grupo')
    ap.add_argument('--sin-bajos', action='store_true',
                    help='se salta undercarriage_white (el LED de los bajos)')
    a = ap.parse_args()

    rclpy.init()
    n = Probador()
    print('═' * 74)
    print('LEDS DEL RVR POR ROS 2 — ¿sigue habiendo comunicación?')
    print('═' * 74)

    if not n.esperar():
        print('🔴 no responden set_led_rgb / set_leds.')
        print('   ¿está corriendo el driver?  systemctl status atriz-robot')
        rclpy.shutdown()
        return 1

    print(f'  ⚠️ se van a encender LEDs, {a.pausa:.1f} s cada uno. MÍRALOS.')
    print(f'  {"":4s} {"grupo":26s} {"color":16s} resultado\n')

    ok_n, fallos = 0, []
    try:
        for i, grupo in enumerate(GRUPOS):
            if a.sin_bajos and grupo == 'undercarriage_white':
                print(f'  {i:2d}   {grupo:26s} {"—":16s} saltado (--sin-bajos)')
                continue
            rgb = COLORES[i]
            ok, msg = n.encender(i, rgb)
            marca = '✅' if ok else '🔴'
            print(f'  {i:2d}   {grupo:26s} {str(rgb):16s} {marca} {msg}')
            if ok:
                ok_n += 1
            else:
                fallos.append(grupo)
            time.sleep(a.pausa)
            # Se apaga ESTE antes del siguiente, o al final quedarían todos
            # encendidos y no se sabría cuál responde a qué.
            if grupo != 'all_lights':
                n.encender(i, (0, 0, 0))
    finally:
        # 🔴 En el `finally`: un Ctrl-C a mitad no debe dejar el robot iluminado.
        #    El LED de los bajos, además, gasta batería indefinidamente.
        n.apagar_todo()
        time.sleep(0.5)

    print('\n' + '═' * 74)
    esperados = len(GRUPOS) - (1 if a.sin_bajos else 0)
    print(f'  {ok_n} de {esperados} grupos aceptaron el comando')
    if fallos:
        print(f'  🔴 fallaron: {", ".join(fallos)}')
        print('     Mira el log del driver: journalctl -u atriz-robot -n 50')
    else:
        print('  ✅ el camino ROS -> driver -> SDK -> serie -> RVR está vivo entero.')
        print('  ⚠️ Y esto dice que el RVR ACEPTÓ los 12 comandos, no que los 12')
        print('     LEDs alumbren. Eso solo lo dice haberlos mirado.')
    print('  (todos apagados)')
    print('═' * 74)
    rclpy.shutdown()
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
