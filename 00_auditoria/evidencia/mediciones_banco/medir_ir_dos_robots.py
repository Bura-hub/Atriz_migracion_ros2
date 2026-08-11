#!/usr/bin/env python3
"""El sistema de infrarrojos, medido con DOS robots. Y la pregunta que decide el diseño.

    En el robot que MIDE:   python3 medir_ir_dos_robots.py
    En el robot que EMITE:  python3 medir_ir_dos_robots.py --emitir

QUÉ RESPONDE, Y POR QUÉ IMPORTA
───────────────────────────────────────────────────────────────────────────────
El SDK ofrece cuatro sensores receptores de IR y dice que cada byte del `uint32`
que devuelve `get_bot_to_bot_infrared_readings` corresponde a uno.

🔴 PERO ESA MÁSCARA ESTÁ DOCUMENTADA «on BOLT» (referencia_sdk/sensor.md:47), y
   el robot de este laboratorio es un **Sphero RVR**: otro producto, otro chasis,
   otra disposición física. Que valga igual es una SUPOSICIÓN HEREDADA.

   Y este proyecto ya ha pagado por fiarse de la documentación del propio SDK:
   documenta los encoders como `Left`/`Right` y el payload real trae
   `LeftTicks`/`RightTicks`. La documentación del fabricante no es evidencia.

Así que esta herramienta no pregunta «¿funciona el IR?» —eso ya está medido— sino:

    ¿Los cuatro sensores del RVR DISCRIMINAN DIRECCIÓN?

CRITERIO, FIJADO ANTES DE MEDIR
───────────────────────────────────────────────────────────────────────────────
    ✅ DISCRIMINA      en cada posición hay bytes != 255 y CAMBIAN según el lado
    🟡 DETECTA, no discrimina   responde igual esté donde esté el emisor
    🔴 NO SIRVE        sigue en 0xFFFFFFFF con otro robot emitiendo a 50 cm

Se fija antes para no mirar los números y decidir después qué contaban como
éxito. Si sale 🟡, el diseño colapsa los cuatro campos a uno («hay alguien») y
`quien_hay_cerca()` se retira de la biblioteca del alumno.

Diseño: docs/superpowers/specs/2026-08-11-sistema-ir-robot-a-robot-design.md

⚠️ NO HACE FALTA PARAR EL DRIVER. Se lee `/estado_ir`, no el puerto serie.
   Abrirlo por nuestra cuenta con el driver vivo NO da error —pyserial no pone
   TIOCEXCL— y los dos se pisarían en silencio.
"""
import argparse
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions

from atriz_rvr_msgs.msg import EstadoIR
from atriz_rvr_msgs.srv import SetIRMode

VACIO = 255                     # ese sensor no ve nada (sensor.md:54)
NADA = 0xFFFFFFFF               # los cuatro vacíos


class Medidor(Node):
    def __init__(self):
        super().__init__('medir_ir_dos_robots')
        self.estado = None
        self.create_subscription(
            EstadoIR, '/estado_ir', self._recibir,
            QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.cli_modo = self.create_client(SetIRMode, '/set_ir_mode')

    def _recibir(self, m):
        self.estado = m

    def esperar_estado(self, timeout=8.0):
        """El último `/estado_ir`, esperando a que llegue uno."""
        limite = time.monotonic() + timeout
        self.estado = None
        while self.estado is None and time.monotonic() < limite:
            rclpy.spin_once(self, timeout_sec=0.1)
        return self.estado

    def modo(self, modo, lejos=0, cerca=1):
        if not self.cli_modo.wait_for_service(timeout_sec=5.0):
            raise SystemExit('🔴 /set_ir_mode no aparece. ¿Está el driver vivo?')
        p = SetIRMode.Request()
        p.mode, p.far_code, p.near_code = modo, lejos, cerca
        fut = self.cli_modo.call_async(p)
        limite = time.monotonic() + 6.0
        while not fut.done() and time.monotonic() < limite:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not fut.done():
            raise SystemExit(f'🔴 /set_ir_mode({modo}) no contestó')
        r = fut.result()
        if not r.success:
            raise SystemExit(f'🔴 /set_ir_mode({modo}): {r.message}')
        return r.message


def emitir(nodo, lejos, cerca):
    print(f'\n▶ EMITIENDO como baliza (lejos={lejos} cerca={cerca}).')
    print(nodo.modo('broadcasting', lejos, cerca))
    print('\n  Este robot ya NO se mueve: solo enciende sus cuatro emisores.')
    print('  Ve al otro robot y ejecuta la medición.')
    print('\n  Ctrl-C aquí para apagar los emisores.\n')
    try:
        while True:
            rclpy.spin_once(nodo, timeout_sec=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            print('\n' + nodo.modo('off'))
        except SystemExit as e:
            print(f'AVISO al apagar: {e}')


def _leer(nodo, etiqueta):
    """Una lectura, con su interpretación al lado."""
    e = nodo.esperar_estado()
    if e is None:
        print(f'  {etiqueta:<22} 🔴 /estado_ir no llega. ¿ir_sondeo_hz=0?')
        return None
    if not e.lecturas_validas:
        print(f'  {etiqueta:<22} 🔴 lecturas_validas=False — el sondeo está '
              'apagado o la consulta al RVR falló')
        return None
    b = (e.sensor_0, e.sensor_1, e.sensor_2, e.sensor_3)
    vistos = [i for i, v in enumerate(b) if v != VACIO]
    marca = '·' if e.crudo == NADA else '◄'
    print(f'  {etiqueta:<22} {marca} crudo=0x{e.crudo:08X}  bytes={b}  '
          f'antigüedad={e.antiguedad_lectura_s:.1f}s'
          + (f'  → sensores {vistos}' if vistos else '  → NADIE'))
    return b


def medir(nodo, posiciones):
    print('\n▶ MEDICIÓN. El otro robot tiene que estar emitiendo.\n')
    print('🔴 Los cuatro bytes salen del uint32 del MENOS significativo al más.')
    print('   Ese orden es una decisión del driver, NO un hecho del hardware.')
    print('   Por eso se imprime también el `crudo`: si el troceado está mal,')
    print('   la evidencia sigue entera y se puede reinterpretar sin repetir.\n')

    lecturas = {}
    for pos in posiciones:
        print(f'\n── Coloca el robot EMISOR: {pos}')
        try:
            input('   Y pulsa ENTER (Ctrl-C para terminar)... ')
        except (EOFError, KeyboardInterrupt):
            print('\n  interrumpido')
            break
        # Tres lecturas: el dato del firmware caduca en 1 s, así que una sola
        # podría pillar el registro justo vacío y decir «nadie» sin motivo.
        muestras = [_leer(nodo, f'lectura {i + 1}/3') for i in range(3)]
        lecturas[pos] = [m for m in muestras if m is not None]

    return lecturas


def veredicto(lecturas):
    print('\n' + '=' * 70)
    print('  VEREDICTO — contra el criterio fijado ANTES de medir')
    print('=' * 70)
    if not lecturas:
        print('  Sin datos.')
        return 1

    algo = {p: any(v != VACIO for m in ms for v in m)
            for p, ms in lecturas.items() if ms}
    if not any(algo.values()):
        print('  🔴 NO SIRVE — ningún sensor vio nada en ninguna posición.')
        print('     Los cuatro bytes siguieron a 255 con otro robot emitiendo.')
        print('     Consecuencia para el diseño: se retira `quien_hay_cerca()`')
        print('     y los cuatro campos de EstadoIR pierden su razón de ser.')
        return 2

    # ¿El PATRÓN cambia según dónde esté el emisor?
    patrones = {p: tuple(sorted({tuple(m) for m in ms})) for p, ms in lecturas.items() if ms}
    distintos = len(set(patrones.values()))
    print(f'  Posiciones medidas: {len(patrones)} · patrones distintos: {distintos}')
    for p, pat in patrones.items():
        print(f'    {p:<22} {pat}')

    if distintos <= 1:
        print('\n  🟡 DETECTA PERO NO DISCRIMINA — responde igual esté donde esté.')
        print('     Consecuencia: los cuatro campos se colapsan a uno')
        print('     («hay alguien») y `quien_hay_cerca()` no promete dirección.')
        return 3

    print('\n  ✅ DISCRIMINA — el patrón cambia con la posición del emisor.')
    print('     Consecuencia: los campos `sensor_N` de EstadoIR se PUEDEN')
    print('     renombrar con el lado real, usando la tabla de arriba.')
    print('     🔴 Anótala en la evidencia: es lo que bautiza los campos.')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--emitir', action='store_true',
                    help='este robot hace de baliza en vez de medir')
    ap.add_argument('--lejos', type=int, default=0, help='far_code (0-7)')
    ap.add_argument('--cerca', type=int, default=1, help='near_code (0-7)')
    args = ap.parse_args()

    # 🔴 SignalHandlerOptions.NO: rclpy instala su propio manejador de SIGINT y
    #    se come el Ctrl-C, dejando los emisores encendidos. Regla del proyecto.
    rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
    nodo = Medidor()
    try:
        if args.emitir:
            emitir(nodo, args.lejos, args.cerca)
            return 0
        posiciones = ['DELANTE, a ~50 cm', 'DETRÁS, a ~50 cm',
                      'a la IZQUIERDA, ~50 cm', 'a la DERECHA, ~50 cm',
                      'DELANTE, a ~2 m']
        return veredicto(medir(nodo, posiciones))
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
