#!/usr/bin/env python3
"""Segunda tanda: lo que la documentación rescatada dejó pendiente de probar.

    sudo systemctl stop atriz-robot
    python3 probar_sdk_tanda2.py              # FASE A — no mueve el robot
    python3 probar_sdk_tanda2.py --calibrar   # ⚠️ + FASE B: GIRA 360°
    sudo systemctl start atriz-robot

═══════════════════════════════════════════════════════════════════════════════
DE DÓNDE SALE ESTA TANDA
═══════════════════════════════════════════════════════════════════════════════
La documentación oficial del protocolo (`00_auditoria/referencia_sdk/`, rescatada
de archive.org porque `sdk.sphero.com` ya no existe) destapó **dos errores** de la
primera tanda y dejó tres cosas por comprobar. Evidencia 43.

  🔴 ERROR 1 — `get_temperature(id0=0, id1=1)`: los IDs 0 y 1 **no existen**. El
     enum dice `left_motor=4`, `right_motor=5`, `nordic_die=8`. Se consultaron
     sensores inexistentes, el firmware contestó igual, y el resultado se dio por
     bueno **porque parecía razonable**. Aquí se piden los buenos.

  🔴 ERROR 2 — `get_current_detected_color_reading` se clasificó como «mudo». La
     doc: «this does not return anything. Instead, a **color_detection_notify
     async** will be sent after measurement». Es asíncrono POR DISEÑO. Aquí se
     prueba como toca: registrando la notificación.

═══════════════════════════════════════════════════════════════════════════════
FASE A — no toca el movimiento
═══════════════════════════════════════════════════════════════════════════════
1. Temperaturas con los IDs correctos (4, 5, 8).
2. Color por su vía asíncrona.
   ⚠️ Enciende el **LED blanco bajo el chasis**; se apaga al terminar.
3. Batería en detalle, para el diseño de la alerta de flota.

═══════════════════════════════════════════════════════════════════════════════
FASE B (`--calibrar`) — 🔴 EL ROBOT GIRA 360° SOBRE SÍ MISMO, TRES VECES
═══════════════════════════════════════════════════════════════════════════════
`magnetometer_calibrate_to_north` → `yaw_north_direction`, que según un ingeniero
de Sphero es **el desfase entre el yaw=0 (arbitrario, del encendido) y el norte
magnético**. Es la referencia absoluta que le falta a la flota.

🔴 **Se repite TRES veces a propósito.** Sphero avisa de que a ras de suelo las
   lecturas son ruidosas por el hierro de las estructuras, y hay dos motores con
   imanes a centímetros del sensor. **Un valor que no se repite no sirve como
   referencia.** Si las tres medidas no caen dentro de unos pocos grados, se
   descarta.
"""
import argparse
import asyncio
import statistics
import sys

from sphero_sdk import SpheroRvrAsync, SerialAsyncDal

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))   # con el loop PARADO

colores = []
calibraciones = []


async def al_color(r):
    colores.append(r)
    print(f'     ✅ notificación de color: {r}')


async def al_calibrar(r):
    calibraciones.append(r)
    print(f'     ✅ notificación de calibración: {r}')


async def fase_a():
    print('\n' + '─' * 74)
    print('FASE A — consultas, no mueve el robot')
    print('─' * 74)

    # ── 1. Temperaturas con los IDs que existen ──────────────────────────
    print('\n  1) get_temperature con los IDs CORRECTOS')
    print('     (4 = motor izq · 5 = motor der · 8 = die del Nordic)')
    for a, b, etq in ((4, 5, 'motores'), (8, 8, 'die del Nordic')):
        try:
            r = await rvr.get_temperature(id0=a, id1=b, timeout=8)
            print(f'     ✅ {etq:16s} {r}')
        except Exception as e:                              # noqa: BLE001
            print(f'     🔴 {etq:16s} {type(e).__name__}: {e}')
    print('\n     · y el sondeo que YA usa el driver, para contrastar:')
    try:
        r = await rvr.get_motor_thermal_protection_status(timeout=8)
        print(f'       {r}')
        print('       ⚠️ Si estos números y los de arriba NO cuadran, la medida')
        print('          de la primera tanda (IDs 0 y 1) era basura plausible.')
    except Exception as e:                                  # noqa: BLE001
        print(f'       🔴 {e}')

    # ── 2. El color, por su vía asíncrona ────────────────────────────────
    print('\n  2) color por NOTIFICACIÓN (que es como funciona de verdad)')
    print('     ⚠️ Se enciende el LED blanco bajo el chasis.')
    try:
        await rvr.enable_color_detection(is_enabled=True)
        await rvr.on_color_detection_notify(handler=al_color)
        await asyncio.sleep(1.0)
        await rvr.get_current_detected_color_reading()
        for _ in range(40):                    # 4 s de margen
            if colores:
                break
            await asyncio.sleep(0.1)
        if not colores:
            print('     🔴 sin notificación en 4 s → entonces sí está mudo')
        else:
            c = colores[-1]
            conf = c.get('confidence')
            cid = c.get('color_classification_id')
            print(f'     📝 confianza {conf}/255 · clasificación {cid}')
            if cid == 0xFF:
                print('        0xFF = «no se pudo identificar el color», que es')
                print('        un resultado LEGÍTIMO, no un fallo (doc oficial).')
    except Exception as e:                                  # noqa: BLE001
        print(f'     🔴 {type(e).__name__}: {e}')
    finally:
        try:
            await rvr.enable_color_detection(is_enabled=False)
            print('     · LED del sensor de color APAGADO')
        except Exception:                                   # noqa: BLE001
            print('     ⚠️ no se pudo apagar el LED del sensor de color')

    # ── 3. Batería, para diseñar la alerta de la flota ───────────────────
    print('\n  3) batería en detalle (para la alerta de los 16)')
    for etq, corr in (('voltios', rvr.get_battery_voltage_in_volts(reading_type=0, timeout=8)),
                      ('estado', rvr.get_battery_voltage_state(timeout=8)),
                      ('umbrales', rvr.get_battery_voltage_state_thresholds(timeout=8)),
                      ('porcentaje', rvr.get_battery_percentage(timeout=8))):
        try:
            print(f'     ✅ {etq:12s} {await corr}')
        except Exception as e:                              # noqa: BLE001
            print(f'     🔴 {etq:12s} {e}')


async def fase_b(vueltas: int, espera: float):
    print('\n' + '─' * 74)
    print('FASE B — 🔴 EL ROBOT VA A GIRAR 360° SOBRE SÍ MISMO')
    print('─' * 74)
    try:
        await rvr.on_magnetometer_calibration_complete_notify(handler=al_calibrar)
    except Exception as e:                                  # noqa: BLE001
        print(f'  🔴 no se pudo registrar la notificación: {e}')

    for i in range(1, vueltas + 1):
        antes = len(calibraciones)
        print(f'\n  Calibración {i}/{vueltas} — girando…')
        try:
            await rvr.magnetometer_calibrate_to_north(timeout=10)
        except Exception as e:                              # noqa: BLE001
            print(f'     🔴 {type(e).__name__}: {e}')
            if 'bad_cid' in str(e):
                print('        → el comando NO EXISTE en este firmware.')
                print('        → No hay rumbo absoluto. Cierra la vía.')
            return
        t = 0.0
        while len(calibraciones) == antes and t < espera:
            await asyncio.sleep(0.2); t += 0.2
        if len(calibraciones) == antes:
            print(f'     🔴 sin notificación en {espera:.0f} s')
            print('        Mismo patrón que las notificaciones de motor: se')
            print('        aceptan y no emiten nada. Si además NO giró, el')
            print('        comando tampoco está implementado.')
            return
        if i < vueltas:
            print('     ⚠️ GIRA EL ROBOT A MANO unos 90° y pulsa Enter…')
            await loop.run_in_executor(None, input)

    vals = [c.get('yaw_north_direction') for c in calibraciones
            if c.get('yaw_north_direction') is not None]
    print('\n  ── ¿es repetible? ──')
    print(f'     valores: {vals}')
    if len(vals) >= 2:
        disp = max(vals) - min(vals)
        print(f'     dispersión: {disp}°  (mediana {statistics.median(vals)})')
        if disp <= 10:
            print('     ✅ REPETIBLE. Sirve como referencia absoluta de rumbo.')
        else:
            print('     🔴 NO REPETIBLE. Es ruido de los motores y del suelo:')
            print('        no sirve como referencia. La pose inicial tendrá que')
            print('        venir del mapa o del operador.')


async def main(calibrar: bool, vueltas: int, espera: float) -> int:
    print('═' * 74)
    print('SDK — SEGUNDA TANDA (lo que destapó la documentación rescatada)')
    print('═' * 74)
    await rvr.wake()
    await asyncio.sleep(2)
    await fase_a()
    if calibrar:
        await fase_b(vueltas, espera)
    else:
        print('\n  FASE B saltada. ⚠️ Gira el robot 360°: usa --calibrar y')
        print('  despeja un círculo de ~40 cm alrededor.')
    await rvr.drive_stop()
    await rvr.close()
    print('\n' + '═' * 74)
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--calibrar', action='store_true', help='⚠️ GIRA EL ROBOT 360°')
    ap.add_argument('--vueltas', type=int, default=3)
    ap.add_argument('--espera', type=float, default=45.0)
    a = ap.parse_args()
    try:
        sys.exit(loop.run_until_complete(main(a.calibrar, a.vueltas, a.espera)))
    except KeyboardInterrupt:
        loop.run_until_complete(rvr.drive_stop())
        loop.run_until_complete(rvr.close())
        sys.exit(1)
