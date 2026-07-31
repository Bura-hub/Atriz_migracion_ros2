#!/usr/bin/env python3
"""¿Funciona el sensor de color del RVR SIN encender su luz?

    # PARA el driver antes: este script abre /dev/rvr directamente.
    python3 medir_sensor_color.py

⚠️ Enciende el LED del sensor unos segundos. No mueve el robot.

═══════════════════════════════════════════════════════════════════════════════
LA PREGUNTA
═══════════════════════════════════════════════════════════════════════════════
El RVR trae un sensor RGBC (rojo/verde/azul/claro) mirando al suelo, con un LED
blanco al lado para iluminarlo. La creencia del proyecto es que **sin encender
ese LED el sensor no da nada**, y eso importa por dos razones:

  · el LED gasta batería, y si no se apaga se queda encendido indefinidamente
    (`enable_color_detection(True)` necesita su `(False)`; CLAUDE.md)
  · un robot con una luz blanca encendida bajo el chasis es ruido visual en un
    laboratorio con 16

Si el sensor diera valores útiles con luz ambiente, se podría dejar apagado.

═══════════════════════════════════════════════════════════════════════════════
QUÉ MIDE, Y POR QUÉ ASÍ
═══════════════════════════════════════════════════════════════════════════════
Tres tandas de lecturas, en este orden:

    1. SIN encender nada           <- ¿da algo el sensor?
    2. CON el LED encendido        <- ¿cambia?
    3. otra vez SIN, tras apagar   <- ¿vuelve a lo de antes?

La tercera no sobra: distingue «el sensor necesita la luz» de «el sensor necesita
que le hayan llamado a `enable_color_detection` alguna vez». Son cosas distintas
y el síntoma inicial es el mismo.

🔴 Y ESPERA ENTRE ENCENDER Y LEER. La primera versión del servicio del driver
   leía inmediatamente después de `enable_color_detection(True)` y daba
   (3, 3, 0, 4) — valores casi nulos con la luz supuestamente encendida. Si el
   LED o la integración del sensor tardan, leer al instante mide el estado
   anterior. Aquí se prueban varias esperas para saber cuánta hace falta.
"""
import argparse
import asyncio
import os
import statistics
import sys

RUTA_SDK = '/home/sphero/atriz_ws/src/Atriz_rvr/atriz_rvr_driver/scripts'
sys.path.insert(0, RUTA_SDK)

from sphero_sdk import SerialAsyncDal, SpheroRvrAsync  # noqa: E402


async def leer(rvr, n: int, pausa: float) -> list[dict]:
    out = []
    for _ in range(n):
        d = await rvr.get_rgbc_sensor_values()
        if isinstance(d, dict):
            out.append(d)
        await asyncio.sleep(pausa)
    return out


def resumen(etiqueta: str, muestras: list[dict]) -> tuple:
    if not muestras:
        print(f'  {etiqueta:34s} 🔴 sin lecturas')
        return (0, 0, 0, 0)
    med = tuple(
        statistics.median(m.get(k, 0) for m in muestras)
        for k in ('red_channel_value', 'green_channel_value',
                  'blue_channel_value', 'clear_channel_value'))
    print(f'  {etiqueta:34s} R {med[0]:5.0f}  G {med[1]:5.0f}  '
          f'B {med[2]:5.0f}  C {med[3]:5.0f}   (n={len(muestras)})')
    return med


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lecturas', type=int, default=5)
    a = ap.parse_args()

    if not os.path.exists('/dev/rvr'):
        print('🔴 no existe /dev/rvr')
        return 1

    # 🔴 Construido con el loop PARADO: `SpheroRvrAsync.__init__` llama a
    # `run_until_complete`, así que hacerlo desde una corrutina en marcha da
    # `RuntimeError: This event loop is already running` (CLAUDE.md). Por eso
    # este `main` se llama con `asyncio.run` y el objeto se crea DENTRO... no:
    # se crea fuera, antes. Ver `if __name__`.
    rvr = RVR[0]
    await rvr.wake()
    await asyncio.sleep(2.0)

    print('═' * 74)
    print('SENSOR DE COLOR — ¿hace falta encender su luz?')
    print('═' * 74)
    print(f'{a.lecturas} lecturas por tanda. Los cuatro canales son crudos, 0..65535.\n')

    print('── 1. SIN tocar enable_color_detection ──')
    apagado = resumen('sin luz, sin haber encendido nunca',
                      await leer(rvr, a.lecturas, 0.2))

    print('\n── 2. CON el LED encendido, probando varias esperas ──')
    await rvr.enable_color_detection(is_enabled=True)
    conluz = {}
    for espera in (0.0, 0.3, 1.0, 2.0):
        await asyncio.sleep(espera if espera else 0)
        conluz[espera] = resumen(f'con luz, {espera:.1f} s tras encender',
                                 await leer(rvr, a.lecturas, 0.2))

    print('\n── 3. otra vez SIN luz, tras apagarla ──')
    await rvr.enable_color_detection(is_enabled=False)
    await asyncio.sleep(1.0)
    despues = resumen('sin luz, ya apagada', await leer(rvr, a.lecturas, 0.2))

    print('\n' + '═' * 74)
    print('QUÉ CONCLUIR')
    print('═' * 74)
    mejor = max(conluz.values(), key=lambda m: m[3])
    print(f'  claro (C) sin luz: {apagado[3]:.0f}  ·  con luz: {mejor[3]:.0f}')
    if apagado[3] < 5 and mejor[3] > 20:
        print('  🔴 EL SENSOR NO SIRVE SIN SU LUZ. Hay que encenderla para leer,')
        print('     y apagarla después — cada (True) necesita su (False).')
    elif apagado[3] > 20:
        print('  ✅ DA VALORES SIN LUZ. Habría que comprobar si distinguen colores')
        print('     de verdad, y con qué luz ambiente: esto solo dice que no es 0.')
    else:
        print('  ⚠️ NO CONCLUYENTE: los dos valores son bajos. Prueba sobre una')
        print('     superficie clara y con más luz en la sala.')
    lento = [e for e, m in conluz.items() if m[3] < mejor[3] * 0.5]
    if lento:
        print(f'\n  ⏱️  HAY QUE ESPERAR tras encender: con {sorted(lento)} s la lectura')
        print('     sale muy por debajo del máximo. Leer al instante mide el estado')
        print('     ANTERIOR — que es justo el bug de la primera versión del servicio.')
    else:
        print('\n  ⏱️  No hace falta esperar: todas las esperas dan lo mismo.')

    await rvr.enable_color_detection(is_enabled=False)
    await rvr.close()
    return 0


if __name__ == '__main__':
    # El objeto se construye con el loop PARADO, a propósito (ver arriba).
    RVR = [SpheroRvrAsync(dal=SerialAsyncDal(asyncio.get_event_loop(),
                                             port_id='/dev/rvr'))]
    sys.exit(asyncio.get_event_loop().run_until_complete(main()))
