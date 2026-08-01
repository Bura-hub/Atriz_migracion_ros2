#!/usr/bin/env python3
"""El sensor óptico del RVR por sus TRES rutas a la vez. ¿Cuál funciona?

    python3 probar_sensor_optico.py                 # una lectura
    python3 probar_sensor_optico.py --guiado        # con superficies, paso a paso
    python3 probar_sensor_optico.py --seg 10        # ventana más larga

No mueve el robot. ⚠️ Si `color_detection` está encendido, hay un LED blanco bajo
el chasis.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ MIRA TRES RUTAS Y NO UNA
═══════════════════════════════════════════════════════════════════════════════
El RVR expone lo óptico por caminos distintos, y **este proyecto ha probado cada
uno por separado, en días distintos, y ha sacado conclusiones que no encajan**:

  1. topic `/color`          <- stream `color_detection` · da rgb + confianza
  2. topic `/ambient_light`  <- stream `ambient_light`   · da un escalar
  3. servicio `get_rgbc_sensor_values` <- consulta directa · da R,G,B,Clear crudos

  El 2026-07-31 la ruta 3 midió **clear 4 apagado contra 741 encendido**: el
  sensor ve. El 2026-08-01 la ruta 1 daba **(0,0,0) con la luz encendida** y la
  ruta 2 daba **0.0** salvo con `color_detection:=true`.

  🔴 Que una ruta funcione NO DICE NADA de las otras. Por eso se leen a la vez,
     sobre la misma superficie y en el mismo instante: es la única forma de saber
     si el problema es el sensor, el stream o la interpretación.

═══════════════════════════════════════════════════════════════════════════════
LO QUE HAY QUE MIRAR, Y NO ES EL RGB
═══════════════════════════════════════════════════════════════════════════════
🔴 `/color` trae **`confidence`**, y hasta ahora nadie lo había mirado. Un
   `(0,0,0)` con confianza 0 significa **«no reconozco este color»**, que es un
   resultado legítimo del detector — no un sensor roto. Un `(0,0,0)` con
   confianza alta sí sería un fallo. Son cosas opuestas y el RGB solo no las
   distingue.

📝 Y `clear` de la ruta 3 es el canal SIN filtro: mide cuánta luz vuelve, sin
   importar el color. Es el mejor indicador de «¿está encendido el LED y llega
   luz de vuelta?», independiente de que el detector reconozca un color o no.
"""
import argparse
import statistics
import sys
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Illuminance

from atriz_rvr_msgs.msg import Color
from atriz_rvr_msgs.srv import GetRGBCSensorValues

QOS = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                 history=HistoryPolicy.KEEP_LAST, depth=50)


class Optico(Node):
    def __init__(self):
        super().__init__('probar_sensor_optico')
        self.color: list = []
        self.luz: list = []
        self.create_subscription(Color, 'color', self._c, QOS)
        self.create_subscription(Illuminance, 'ambient_light', self._l, QOS)
        self.cli = self.create_client(GetRGBCSensorValues, 'get_rgbc_sensor_values')
        # 🔴 UN SOLO EJECUTOR, y todo el giro es suyo. Mezclar
        #    `rclpy.spin_*(nodo, …)` con esto deja de atender las suscripciones y
        #    hace creer que el robot se ha quedado mudo (manual, cap. 18.5).
        self.ex = SingleThreadedExecutor()
        self.ex.add_node(self)

    def _c(self, m):
        self.color.append((tuple(m.rgb_color), m.confidence))

    def _l(self, m):
        self.luz.append(m.illuminance)

    def girar(self, seg):
        t0 = time.monotonic()
        while time.monotonic() - t0 < seg:
            self.ex.spin_once(timeout_sec=0.05)

    def rgbc(self):
        if not self.cli.service_is_ready():
            return None
        f = self.cli.call_async(GetRGBCSensorValues.Request())
        self.ex.spin_until_future_complete(f, timeout_sec=15.0)
        return f.result()

    def leer(self, etiqueta: str, seg: float):
        self.color.clear(); self.luz.clear()
        self.girar(seg)
        r = self.rgbc()

        print(f'\n  ── {etiqueta} ──')
        # 1. /color
        if not self.color:
            print('     /color          🔴 sin mensajes (¿driver parado?)')
        else:
            rgbs = [c[0] for c in self.color]
            conf = [c[1] for c in self.color]
            distintos = len(set(rgbs))
            print(f'     /color          rgb={max(set(rgbs), key=rgbs.count)}  '
                  f'confianza={statistics.mean(conf):.2f}  '
                  f'({len(rgbs)} msgs, {distintos} valores distintos)')
            if all(x == (0, 0, 0) for x in rgbs) and statistics.mean(conf) == 0:
                print('                     📝 (0,0,0) con confianza 0 = «no reconozco '
                      'color», NO es un sensor roto')
        # 2. /ambient_light
        if not self.luz:
            print('     /ambient_light  🔴 sin mensajes')
        else:
            print(f'     /ambient_light  media={statistics.mean(self.luz):7.2f}  '
                  f'max={max(self.luz):7.2f}  ({len(self.luz)} msgs)')
        # 3. servicio RGBC
        if r is None:
            print('     get_rgbc        🔴 el servicio no respondió')
        elif not getattr(r, 'success', True):
            print(f'     get_rgbc        🔴 success=False  {getattr(r, "message", "")}')
        else:
            print(f'     get_rgbc        R={r.red_channel_value:5d} '
                  f'G={r.green_channel_value:5d} B={r.blue_channel_value:5d} '
                  f'CLEAR={r.clear_channel_value:5d}   <- clear dice si LLEGA LUZ')
        return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seg', type=float, default=6.0)
    ap.add_argument('--guiado', action='store_true',
                    help='pide superficies distintas, una por una')
    a = ap.parse_args()

    rclpy.init()
    n = Optico()
    print('═' * 74)
    print('SENSOR ÓPTICO DEL RVR — las tres rutas a la vez')
    print('═' * 74)
    if not n.cli.wait_for_service(timeout_sec=15.0):
        print('🔴 no responde get_rgbc_sensor_values. ¿está corriendo el driver?')
        rclpy.shutdown()
        return 1

    if not a.guiado:
        n.leer('tal como está ahora', a.seg)
    else:
        pasos = [
            'DEJA EL ROBOT COMO ESTÁ (referencia)',
            'PON UN PAPEL BLANCO debajo del robot',
            'PON ALGO ROJO debajo',
            'PON ALGO AZUL debajo',
            'LEVANTA EL ROBOT unos 20 cm y mantenlo',
        ]
        for i, p in enumerate(pasos, 1):
            print(f'\n{"═" * 74}')
            print(f'  PASO {i}/{len(pasos)}: {p}')
            print(f'{"═" * 74}')
            for s in (5, 4, 3, 2, 1):
                print(f'    midiendo en {s}...', flush=True)
                time.sleep(1)
            n.leer(p, a.seg)

    print('\n' + '═' * 74)
    print('  CÓMO LEERLO')
    print('    clear alto  -> llega luz de vuelta: el LED está encendido y el sensor ve')
    print('    clear ~0    -> o el LED está apagado, o el sensor no responde')
    print('    rgb (0,0,0) con confianza 0 -> el detector no reconoce ese color.')
    print('                   Es un resultado válido, no un fallo.')
    print('    luz 0.0 con clear alto -> el problema está en el STREAM de luz,')
    print('                   no en el sensor.')
    print('═' * 74)
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
