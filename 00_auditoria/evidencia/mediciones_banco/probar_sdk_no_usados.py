#!/usr/bin/env python3
"""De los 99 métodos del SDK, el driver usa 37. ¿Cuáles de los otros SIRVEN?

    sudo systemctl stop atriz-robot          # el driver tiene ocupado /dev/rvr
    python3 probar_sdk_no_usados.py
    sudo systemctl start atriz-robot         # devolver el robot a su estado

⚠️ DESPIERTA EL ROBOT y consulta al RVR. **No lo mueve.**

🔴 Pero **despertarlo SÍ enciende sus LEDs** —lo dice el propio CLAUDE.md— y
   gasta batería. La cabecera afirmaba «no enciende LEDs», y era falso: hay un
   `wake()` en la línea de arranque. Corregido en auditoría el 2026-08-01.
   Salvo ese `wake()`, todas las llamadas son de lectura.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════
«El driver usa 37 de 99 métodos» no dice nada por sí solo: la mayoría de los 62
restantes son modos de conducción alternativos que no hacen falta. La pregunta
útil es **cuáles de los que faltan responden y dan un dato aprovechable**.

🔴 Y NO SE PUEDE DEDUCIR LEYENDO EL SDK. Este proyecto tiene medido que
   `core_time` está en el enum y **el firmware no lo transmite**, y que las
   notificaciones de motor se registran sin error y **no emiten ni un mensaje**.
   Que un método exista en la librería no significa que el RVR lo conteste.

Por eso esto llama a cada uno de verdad y enseña lo que devuelve.

═══════════════════════════════════════════════════════════════════════════════
LOS TRES QUE PODRÍAN CAMBIAR ALGO
═══════════════════════════════════════════════════════════════════════════════
1. **`get_current_sense_amplifier_current`** — corriente de cada motor, en A.
   El proyecto tiene un hueco abierto: **la detección de atasco**. Las
   notificaciones no llegan y el SDK no tiene `get_motor_stall_state`, así que
   `antiguedad_atasco_s` vale −1.0 («no se sabe») para siempre. Pero un atasco
   tiene firma eléctrica: **motor comandado + corriente alta + encoders
   quietos**. Los encoders ya se publican. Si esta consulta responde, el
   detector que falta se puede construir.

2. **`get_magnetometer_reading`** — rumbo absoluto. El yaw del RVR se pone a
   cero **al encender**, así que su origen es arbitrario (hoy: +61.0°). Con 16
   robots sobre un mapa compartido hace falta una referencia común.
   ⚠️ Con reservas: un magnetómetro a centímetros de dos motores, dentro de un
   edificio, suele ser ruido. **Medir antes de ilusionarse.**

3. **`get_battery_voltage_state`** — estado con umbrales del propio firmware, en
   vez del porcentaje que ya se sondea. El plan pide «alerta de batería baja»
   para la flota.
"""
import argparse
import asyncio
import subprocess
import sys
import time

from sphero_sdk import SpheroRvrAsync, SerialAsyncDal
from sphero_sdk.common.enums.power_enums import (AmplifierIdsEnum,
                                                 BatteryVoltageReadingTypesEnum,
                                                 BatteryVoltageStatesEnum)

# ═══════════════════════════════════════════════════════════════════════════
# 🔴 EL PUERTO SERIE NO SE ABRE AL IMPORTAR — corregido el 2026-08-01
#    Antes, `loop` y `rvr` se creaban a nivel de módulo, así que
#    `python3 esta_herramienta.py --help` **abría /dev/rvr y hablaba con el
#    robot** antes de imprimir la ayuda. Un `--flag` mal escrito, igual.
#    Ahora se construyen en `_conectar()`, DESPUÉS de `parse_args()`.
#
#    ⚠️ Se sigue construyendo con el LOOP PARADO: el constructor de
#       `SpheroRvrAsync` hace `run_until_complete()`, y hacerlo desde una
#       corrutina falla con «This event loop is already running».
# ═══════════════════════════════════════════════════════════════════════════
loop = None
rvr = None


def _driver_corriendo() -> bool:
    """🔴 pyserial NO pone TIOCEXCL: el `open()` tiene ÉXITO con el driver vivo,
    y los dos se reparten los bytes del mismo TTY en silencio."""
    try:
        s = subprocess.run(['ps', '-eo', 'comm'], capture_output=True,
                           text=True, timeout=5)
        # 🔴 `comm` trunca a 15 caracteres y `rvr_driver_node` mide exactamente
        #    15: vale hoy por un carácter. Se comprueba el prefijo truncado.
        return any(c.startswith('rvr_driver_nod') for c in s.stdout.split())
    except Exception:                                       # noqa: BLE001
        return True


def _conectar() -> bool:
    global loop, rvr
    if _driver_corriendo():
        print('🔴 El driver está corriendo y tiene ocupado /dev/rvr.')
        print('   Párala primero:  sudo systemctl stop atriz-robot')
        print('   Y al terminar:   sudo systemctl start atriz-robot')
        return False
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))
    return True

#: (etiqueta, corrutina, para qué serviría). El orden es de utilidad esperada.
def pruebas():
    return [
        ('get_current_sense_amplifier_current(izq)',
         lambda: rvr.get_current_sense_amplifier_current(
             amplifier_id=AmplifierIdsEnum.left_motor, timeout=8),
         '🔴 podría cerrar el hueco de la DETECCIÓN DE ATASCO'),
        ('get_current_sense_amplifier_current(der)',
         lambda: rvr.get_current_sense_amplifier_current(
             amplifier_id=AmplifierIdsEnum.right_motor, timeout=8),
         'idem, el otro motor'),
        ('get_magnetometer_reading',
         lambda: rvr.get_magnetometer_reading(timeout=8),
         '🔴 rumbo ABSOLUTO — el yaw del RVR es arbitrario'),
        ('get_battery_voltage_state',
         lambda: rvr.get_battery_voltage_state(timeout=8),
         '🔴 alerta de batería con umbrales del firmware'),
        ('get_battery_voltage_state_thresholds',
         lambda: rvr.get_battery_voltage_state_thresholds(timeout=8),
         'los umbrales que usa el firmware'),
        ('get_battery_voltage_in_volts(filtrado)',
         lambda: rvr.get_battery_voltage_in_volts(
             reading_type=BatteryVoltageReadingTypesEnum.calibrated_and_filtered,
             timeout=8),
         'voltios en vez de porcentaje'),
        ('get_ambient_light_sensor_value',
         lambda: rvr.get_ambient_light_sensor_value(timeout=8),
         '📝 consulta directa; el STREAM ya se descartó (refleja los LEDs)'),
        ('get_current_detected_color_reading',
         lambda: rvr.get_current_detected_color_reading(timeout=8),
         'color sin el stream'),
        ('get_active_color_palette',
         lambda: rvr.get_active_color_palette(timeout=8),
         '📝 la paleta es por lo que /color da confianza 0'),
        ('get_temperature',
         lambda: rvr.get_temperature(id0=0, id1=1, timeout=8),
         'temperatura por sensor (la de motores ya se sondea)'),
        ('get_stop_controller_state',
         lambda: rvr.get_stop_controller_state(timeout=8),
         '¿cómo frena? contraste con drive_rc_si_units'),
        ('get_drive_target_slew_parameters',
         lambda: rvr.get_drive_target_slew_parameters(timeout=8),
         'la rampa de aceleración de ~0.5 s medida'),
        ('get_bot_to_bot_infrared_readings',
         lambda: rvr.get_bot_to_bot_infrared_readings(timeout=8),
         '⚠️ IR: sin un segundo robot dará vacío, pero dice si RESPONDE'),
        ('get_core_up_time_in_milliseconds',
         lambda: rvr.get_core_up_time_in_milliseconds(timeout=8),
         '📝 `core_time` NO se transmite; esto es la CONSULTA, otra cosa'),
        ('get_bluetooth_advertising_name',
         lambda: rvr.get_bluetooth_advertising_name(timeout=8),
         'identificar el robot sin abrirlo'),
        ('get_stats_id',
         lambda: rvr.get_stats_id(timeout=8),
         'sin uso previsto'),
    ]


async def main(repeticiones: int) -> int:
    print('═' * 78)
    print('MÉTODOS DEL SDK QUE EL DRIVER NO USA — ¿cuáles responden?')
    print('═' * 78)
    await rvr.wake()
    await asyncio.sleep(2)
    v = await rvr.get_battery_percentage(timeout=10)
    print(f'  robot despierto · batería {v.get("percentage", "?")} %\n')

    responden, mudos, fallos = [], [], []
    for etiqueta, llamada, para_que in pruebas():
        vals = []
        err = None
        for _ in range(repeticiones):
            try:
                t0 = time.monotonic()
                r = await llamada()
                dt = (time.monotonic() - t0) * 1000
                vals.append((r, dt))
            except Exception as e:                       # noqa: BLE001
                err = f'{type(e).__name__}: {e}'
                break
            await asyncio.sleep(0.15)

        print(f'  ── {etiqueta}')
        print(f'     {para_que}')
        if err:
            print(f'     🔴 {err}')
            fallos.append(etiqueta)
        elif not vals or vals[0][0] is None:
            # El caso que este proyecto ya conoce: se acepta y no contesta.
            print('     🔴 SIN RESPUESTA (el firmware no lo contesta)')
            mudos.append(etiqueta)
        else:
            for r, dt in vals:
                print(f'     ✅ {r}   ({dt:.0f} ms)')
            responden.append((etiqueta, vals[0][0]))
        print()

    print('═' * 78)
    print(f'  ✅ responden: {len(responden)}   🔴 mudos: {len(mudos)}   '
          f'💥 error: {len(fallos)}')
    if mudos:
        print('\n  Mudos (existen en el SDK y el firmware no los contesta):')
        for m in mudos:
            print(f'    · {m}')
    if fallos:
        print('\n  Con error:')
        for f in fallos:
            print(f'    · {f}')
    print('\n  ⚠️ Que responda NO significa que el dato sirva. Un magnetómetro')
    print('     junto a dos motores puede contestar y dar ruido. El siguiente')
    print('     paso de los que respondan es CARACTERIZARLOS.')
    print('═' * 78)

    await rvr.close()
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repite', type=int, default=2,
                    help='lecturas por método (2 para ver si el valor varía)')
    a = ap.parse_args()
    if not _conectar():
        sys.exit(1)
    try:
        sys.exit(loop.run_until_complete(main(a.repite)))
    except KeyboardInterrupt:
        loop.run_until_complete(rvr.close())
        sys.exit(1)
