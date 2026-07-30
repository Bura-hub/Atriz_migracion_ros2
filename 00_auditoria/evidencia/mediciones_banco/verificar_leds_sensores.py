#!/usr/bin/env python3
"""Verifica LEDs y sensores del Sphero RVR, contra el SDK y sin ROS de por medio.

    python3 verificar_leds_sensores.py              # todo
    python3 verificar_leds_sensores.py --solo-leds
    python3 verificar_leds_sensores.py --solo-sensores
    python3 verificar_leds_sensores.py --rapido     # sin las pausas para mirar

⚠️ **ENCIENDE LOS LEDS DEL ROBOT.** No lo mueve: no manda ni un comando de motor.

⚠️ **Y enciende el LED emisor del sensor de color**, que NO se apaga con
   `turn_leds_off()`: hay que llamar a `enable_color_detection(False)`. Este script
   lo hace al terminar, incluso si falla por el camino. Si alguna vez se te queda
   encendido, es porque el proceso murió sin llegar al cierre.

POR QUÉ SIN ROS

  De los 20 servicios del driver de ROS 1, solo 4 están portados a ROS 2. Si algo
  de los LEDs o los sensores no funcionara, hay que saber si es culpa del hardware,
  del SDK, o del port — y la única forma es aislar el SDK. Regla nº4 del proyecto.

  Si esto pasa y luego falla por ROS, el problema está en el port. Si falla aquí,
  el problema está debajo.

QUÉ COMPRUEBA

  LEDs      los 11 grupos que define RvrLedGroups, uno por uno, más los tres
            métodos de conjunto (all_leds_rgb, multiple_leds, turn_leds_off)
  Sensores  los 11 streams (color, luz ambiente, IMU, quaternion, acelerómetro,
            giroscopio, locator, velocidad, speed, core_time, encoders)
            y los 5 puntuales (batería, RGBC, luz ambiente, encoders, versión)

CÓMO LEER EL RESULTADO

  Los LEDs **no se pueden verificar por software**: el SDK no ofrece forma de leer
  el estado de un LED. Lo que este script comprueba es que el comando **se acepta
  sin error**; que el LED se encienda de verdad **lo tienes que ver tú**. Por eso
  hace una pausa en cada uno y dice qué deberías estar viendo.

  Los sensores SÍ se verifican de verdad: se comprueba que llegan datos y que los
  valores son plausibles.
"""
import argparse
import asyncio
import sys
import time

sys.path.insert(0, '/home/sphero/atriz_ws/src/Atriz_rvr/atriz_rvr_driver/scripts')

from sphero_sdk import (  # noqa: E402
    Colors, RvrLedGroups, RvrStreamingServices, SerialAsyncDal, SpheroRvrAsync,
)

V, R, A, Z, G, F = ('\033[92m', '\033[91m', '\033[93m', '\033[94m',
                    '\033[90m', '\033[0m')
ok_n, mal_n, avi_n = [0], [0], [0]
FALLOS = []


def sec(t):  print(f'\n{Z}▶ {t}{F}')
def ok(t):   ok_n[0] += 1; print(f'  {V}✓{F} {t}')
def mal(t):  mal_n[0] += 1; FALLOS.append(t); print(f'  {R}✗{F} {t}')
def avi(t):  avi_n[0] += 1; print(f'  {A}!{F} {t}')
def mira(t): print(f'  {Z}👁  {t}{F}')
def nota(t): print(f'  {G}· {t}{F}')


class Verificador:
    def __init__(self, pausa: float):
        self.pausa = pausa
        self.rvr = None
        self.recibido = {}

    def construir(self, loop):
        """Construye el objeto del SDK con el event loop TODAVÍA PARADO.

        🔴 NO SE PUEDE HACER DESDE DENTRO DE UNA CORRUTINA.

        `SpheroRvrAsync.__init__` (sphero_rvr_async.py:35) hace
        `asyncio.get_event_loop().run_until_complete(self._check_rvr_fw())`.
        Llamarlo desde una corrutina que ya corre en ese loop falla con
            RuntimeError: This event loop is already running

        Es el único `get_event_loop()` de la ruta usada, el que la auditoría del
        2026-07-29 señaló como el riesgo del port a Python 3.12. Y muerde de
        verdad: pasó al escribir el driver de ROS 2, se documentó allí, y **se
        volvió a repetir al escribir este fichero**. Por eso está ahora en
        CLAUDE.md.

        El tiempo que tarda es diagnóstico: 0 s = el robot responde,
        ~10 s = dos timeouts de 5 s = no responde. Un RVR dormido da el mismo
        síntoma que un cable mal puesto.
        """
        sec('Conexión')
        t0 = time.monotonic()
        self.rvr = SpheroRvrAsync(
            dal=SerialAsyncDal(loop, port_id='/dev/rvr', baud=115200)
        )
        dt = time.monotonic() - t0
        if dt > 5.0:
            mal(f'la comprobación de firmware tardó {dt:.1f} s: son timeouts, '
                'el RVR NO responde. APAGA Y ENCIENDE EL ROBOT.')
            return False
        ok(f'RVR presente (firmware comprobado en {dt:.2f} s)')
        return True

    async def despertar(self):
        await self.rvr.wake()
        await asyncio.sleep(1.5)
        ok('despierto')
        return True

    # ── LEDs ─────────────────────────────────────────────────────────────────
    async def leds(self):
        sec('LEDs — los 11 grupos, uno por uno')
        avi('el SDK NO permite LEER el estado de un LED: aquí solo se comprueba '
            'que el comando se acepta. Que se encienda LO VES TÚ.')

        grupos = [g for g in RvrLedGroups if g.name != 'all_lights']
        for g in grupos:
            try:
                if g.name == 'undercarriage_white':
                    # El de los bajos es BLANCO de un solo canal: no acepta RGB.
                    # Se le manda un solo valor de brillo.
                    await self.rvr.set_all_leds(
                        led_group=g.value, led_brightness_values=[255])
                    mira(f'{g.name}: debería estar BLANCO')
                else:
                    await self.rvr.led_control.set_led_rgb(
                        led=g, red=0, green=0, blue=255)
                    mira(f'{g.name}: debería estar AZUL')
                ok(f'set_led_rgb({g.name}) aceptado')
                await asyncio.sleep(self.pausa)
                await self.rvr.led_control.turn_leds_off()
            except Exception as e:
                mal(f'set_led_rgb({g.name}) FALLÓ: {type(e).__name__}: {e}')

        sec('LEDs — métodos de conjunto')
        pruebas = [
            ('set_all_leds_rgb(255,0,0)  TODO ROJO',
             lambda: self.rvr.led_control.set_all_leds_rgb(red=255, green=0, blue=0)),
            ('set_all_leds_rgb(0,255,0)  TODO VERDE',
             lambda: self.rvr.led_control.set_all_leds_rgb(red=0, green=255, blue=0)),
            ('set_all_leds_color(Colors.blue)  TODO AZUL',
             lambda: self.rvr.led_control.set_all_leds_color(color=Colors.blue)),
            ('set_multiple_leds_with_rgb  faros ROJO+VERDE',
             lambda: self.rvr.led_control.set_multiple_leds_with_rgb(
                 leds=[RvrLedGroups.headlight_left, RvrLedGroups.headlight_right],
                 colors=[255, 0, 0, 0, 255, 0])),
            ('set_multiple_leds_with_enums  frenos AMARILLO',
             lambda: self.rvr.led_control.set_multiple_leds_with_enums(
                 leds=[RvrLedGroups.brakelight_left, RvrLedGroups.brakelight_right],
                 colors=[Colors.yellow, Colors.yellow])),
        ]
        for desc, fn in pruebas:
            try:
                await fn()
                mira(desc)
                ok(f'{desc.split()[0]} aceptado')
                await asyncio.sleep(self.pausa)
            except Exception as e:
                mal(f'{desc.split()[0]} FALLÓ: {type(e).__name__}: {e}')
        try:
            await self.rvr.led_control.turn_leds_off()
            mira('turn_leds_off: TODO APAGADO')
            ok('turn_leds_off aceptado')
        except Exception as e:
            mal(f'turn_leds_off FALLÓ: {e}')

    # ── Sensores por streaming ───────────────────────────────────────────────
    async def streams(self):
        sec('Sensores por streaming — los 11')
        streams = ['color_detection', 'ambient_light', 'quaternion', 'imu',
                   'accelerometer', 'gyroscope', 'locator', 'velocity',
                   'speed', 'core_time', 'encoders']

        # El sensor de color necesita que se ENCIENDA su LED emisor. Sin esto
        # devuelve ceros y parece roto.
        try:
            await self.rvr.enable_color_detection(is_enabled=True)
            ok('enable_color_detection(True) — el sensor de color necesita su LED')
        except Exception as e:
            avi(f'enable_color_detection falló: {e}')

        sc = self.rvr.sensor_control
        for s in streams:
            svc = getattr(RvrStreamingServices, s, None)
            if svc is None:
                mal(f'{s}: no existe en RvrStreamingServices')
                continue
            try:
                await sc.add_sensor_data_handler(svc, self._hacer_handler(s))
            except Exception as e:
                mal(f'{s}: add_sensor_data_handler falló: {e}')

        await sc.start(interval=60)
        nota('recogiendo 4 s de datos…')
        await asyncio.sleep(4.0)
        await sc.stop()

        for s in streams:
            d = self.recibido.get(s)
            if d is None:
                if s == 'core_time':
                    # Verificado el 2026-07-30 aislándolo: no llega ni una muestra
                    # ni solo ni acompañado, mientras quaternion sí llega en la
                    # misma configuración. El firmware 9.1.462 del RVR no lo
                    # transmite, aunque el SDK lo declare en el enum.
                    avi('core_time: NO lo transmite el firmware 9.1.462. '
                        'Está en el enum del SDK pero el RVR no lo entrega. '
                        'Verificado aislándolo. No lo usa nada del driver.')
                else:
                    mal(f'{s}: NO llegó ni una muestra')
            else:
                ok(f'{s}: {d["n"]} muestras · {self._resumen(s, d["ultimo"])}')

    def _hacer_handler(self, nombre):
        async def h(datos):
            e = self.recibido.setdefault(nombre, {'n': 0, 'ultimo': None})
            e['n'] += 1
            e['ultimo'] = datos
        return h

    #: El SDK entrega un dict cuya clave es el NOMBRE del sensor, con mayúsculas
    #: propias que no coinciden con el nombre del stream. Coger `values()[0]` a
    #: ciegas muestra el sensor equivocado — pasó el 2026-07-30 y hacía que cuatro
    #: sensores distintos apareciesen con el mismo cuaternión.
    CLAVE = {
        'color_detection': 'ColorDetection', 'ambient_light': 'AmbientLight',
        'quaternion': 'Quaternion', 'imu': 'IMU', 'accelerometer': 'Accelerometer',
        'gyroscope': 'Gyroscope', 'locator': 'Locator', 'velocity': 'Velocity',
        'speed': 'Speed', 'core_time': 'CoreTime', 'encoders': 'Encoders',
    }

    @classmethod
    def _resumen(cls, nombre, d):
        if not isinstance(d, dict):
            return str(d)[:70]
        k = cls.CLAVE.get(nombre)
        v = d.get(k)
        if v is None:
            # La clave esperada no está: se dice cuáles SÍ vinieron, en vez de
            # inventarse un valor.
            return f'(claves recibidas: {list(d)})'
        if isinstance(v, dict):
            return ' '.join(f'{kk}={vv:.3f}' if isinstance(vv, float) else f'{kk}={vv}'
                            for kk, vv in list(v.items())[:4])
        return str(v)[:70]

    # ── Sensores puntuales ───────────────────────────────────────────────────
    async def puntuales(self):
        sec('Sensores puntuales (petición/respuesta)')
        pruebas = [
            ('batería (%)',       self.rvr.get_battery_percentage),
            ('estado de tensión', self.rvr.get_battery_voltage_state),
            ('RGBC del sensor de color', self.rvr.get_rgbc_sensor_values),
            ('luz ambiente',      self.rvr.get_ambient_light_sensor_value),
            ('encoders',          self.rvr.get_encoder_counts),
            # get_main_application_version EXIGE el argumento 'target': el RVR
            # tiene dos procesadores (Nordic = 1, ST = 2) y hay que decir cuál.
            # Sin él: TypeError. Pasó el 2026-07-30.
            ('firmware Nordic (target=1)',
             lambda: self.rvr.get_main_application_version(target=1)),
            ('firmware ST (target=2)',
             lambda: self.rvr.get_main_application_version(target=2)),
        ]
        for desc, fn in pruebas:
            try:
                r = await asyncio.wait_for(fn(), timeout=6.0)
                ok(f'{desc}: {r}')
            except asyncio.TimeoutError:
                mal(f'{desc}: TIMEOUT de 6 s — el RVR no contestó')
            except Exception as e:
                mal(f'{desc} FALLÓ: {type(e).__name__}: {e}')

    async def cerrar(self):
        """Deja el robot como estaba: TODO apagado.

        🔴 `turn_leds_off()` NO apaga el LED emisor del sensor de color. Ese no es
        un grupo de `RvrLedGroups`: se controla con `enable_color_detection`, y si
        no lo desactivas **se queda encendido indefinidamente**, gastando batería
        después de que el script termine.

        Pasó el 2026-07-30: lo detectó el usuario mirando el robot, no el script.
        Cada `enable_color_detection(True)` necesita su `(False)`.
        """
        for desc, coro in (
            ('LED del sensor de color', lambda: self.rvr.enable_color_detection(is_enabled=False)),
            ('LEDs',                    lambda: self.rvr.led_control.turn_leds_off()),
            ('streaming',               lambda: self.rvr.sensor_control.clear()),
            ('puerto',                  lambda: self.rvr.close()),
        ):
            try:
                await asyncio.wait_for(coro(), timeout=4.0)
            except Exception as e:
                avi(f'no se pudo apagar {desc}: {type(e).__name__}. '
                    f'Comprueba el robot a la vista.')
        nota('apagado: LEDs, LED del sensor de color, streaming y puerto')


async def principal(a, v):
    print('=' * 72)
    print('  LEDs y sensores del Sphero RVR — SIN ROS, contra el SDK')
    print('  ⚠️  ENCIENDE LOS LEDS. No mueve el robot.')
    print('=' * 72)
    await v.despertar()
    try:
        if not a.solo_sensores:
            await v.leds()
        if not a.solo_leds:
            await v.streams()
            await v.puntuales()
    finally:
        await v.cerrar()

    print('\n' + '=' * 72)
    print(f'  {V}{ok_n[0]} correctas{F}'
          + (f'  ·  {A}{avi_n[0]} avisos{F}' if avi_n[0] else '')
          + (f'  ·  {R}{mal_n[0]} FALLOS{F}' if mal_n[0] else ''))
    if FALLOS:
        print(f'\n{R}FALLOS{F}:')
        for f in FALLOS:
            print(f'  ✗ {f}')
    print('\n  Recuerda: los LEDs solo se comprueban a nivel de comando aceptado.')
    print('  Si alguno NO se encendió a la vista, es un fallo aunque salga ✓.')
    print('=' * 72)
    return 1 if FALLOS else 0


def main():
    p = argparse.ArgumentParser(description='Verifica LEDs y sensores del RVR')
    p.add_argument('--solo-leds', action='store_true')
    p.add_argument('--solo-sensores', action='store_true')
    p.add_argument('--rapido', action='store_true',
                   help='sin pausas: para comprobar que no hay errores, no para mirar')
    a = p.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    v = Verificador(0.0 if a.rapido else 1.2)
    # El objeto del SDK se construye AQUÍ, con el loop parado. Ver Verificador.construir.
    if not v.construir(loop):
        loop.close()
        return 1
    try:
        return loop.run_until_complete(principal(a, v))
    finally:
        loop.close()


if __name__ == '__main__':
    sys.exit(main())
