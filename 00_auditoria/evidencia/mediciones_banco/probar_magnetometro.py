#!/usr/bin/env python3
"""¿Se puede sacar un rumbo ABSOLUTO del RVR? La última vía que queda.

    sudo systemctl stop atriz-robot
    python3 probar_magnetometro.py --seguro     # solo consultas, NO mueve
    python3 probar_magnetometro.py --calibrar   # ⚠️ PUEDE GIRAR EL ROBOT
    sudo systemctl start atriz-robot

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ IMPORTA
═══════════════════════════════════════════════════════════════════════════════
El yaw del RVR **se pone a cero al ENCENDER el robot**, no con `reset_yaw()` —que
no hace nada—. Su origen es arbitrario: medido el 2026-08-01 quedó en **+61.0°**.

Con 16 robots sobre un mapa compartido eso es un problema real: cada uno cree
mirar en una dirección distinta y **no hay forma de relacionarlos** sin que un
humano coloque cada robot o sin una pose inicial dada desde fuera.

═══════════════════════════════════════════════════════════════════════════════
LO QUE YA SE SABE (2026-08-01, evidencia 41)
═══════════════════════════════════════════════════════════════════════════════
🔴 `get_magnetometer_reading()` devuelve **`bad_cid`** — comando desconocido. Es
   el CID **0x52** al procesador ST. Y NO es un problema de destinatario:
   `get_temperature` y `get_bot_to_bot_infrared_readings` van al mismo target 2 y
   sí responden.

✅ Pero el RVR **sí tiene magnetómetro**: lleva una IMU de 9 ejes. Y el firmware
   lo usa por dentro — existe `control_system_type_magnetometer_drive = 7`.

🔴 Y actualizar el firmware NO es una opción: la última versión publicada por
   Sphero (Fall 2022) es **9.1.462 / 9.2.482**, que es **exactamente la que ya
   tiene este robot**. No hay nada más nuevo.

→ Queda **una vía**, y resulta que es **la que Sphero diseñó**:
  `magnetometer_calibrate_to_north()`, CID **0x25**, otro comando distinto.

═══════════════════════════════════════════════════════════════════════════════
LO QUE DICE SPHERO, Y CAMBIA EL PLANTEAMIENTO
═══════════════════════════════════════════════════════════════════════════════
Del foro oficial (`community.sphero.com/t/…/2682`, vía archive.org), respuesta de
**Sphero_JimK**, ingeniero de Sphero:

  «The `yaw_north_direction` value is **the offset from yaw=0 to magnetic
   north**.»

  «The intended usage of the offset is mostly for the Sphero EDU app to
   synchronize RVR's yaw orientation with the phone. In the case of the EDU app,
   **it never actually requests a magnetometer reading directly. Instead, it
   simulates the magnetometer heading using the reported north offset and the
   IMU heading.** You can do the same in your own programs.»

  «[get_magnetometer_reading] should probably have gotten a disclaimer stating
   that **the raw readings are not as useful as you might think**.»

  «Magnetometer readings tend to be **noisy at floor level due to the prevalence
   of ferrous metals in some floor structures**, and the full rotation allows us
   to do some extra filtering.»

🔴 **CONSECUENCIA: no hace falta leer el magnetómetro NUNCA.** El patrón previsto
   es *calibrar una vez → guardar el desfase al norte → calcular el rumbo
   absoluto como `yaw_IMU + desfase`*. Que `get_magnetometer_reading` no exista
   en este firmware **deja de ser un problema**.

📝 Y explica por qué falla: en el hilo, con firmware **8.3.432 / 8.6.448**, la
   lectura cruda SÍ respondía. Con el nuestro, **9.1.462 / 9.2.482**, da
   `bad_cid`. La lectura cruda se quitó o se movió en una versión posterior —
   justo la que el propio fabricante desaconseja usar.

═══════════════════════════════════════════════════════════════════════════════
⚠️ POR QUÉ ESTO NO ESTÁ EN EL MODO POR DEFECTO
═══════════════════════════════════════════════════════════════════════════════
🔴 **Calibrar un magnetómetro exige GIRAR.** El ejemplo oficial de Sphero no lo
   advierte, pero es lo que hace toda calibración de brújula: el robot **puede
   dar vueltas solo**. Por eso `--calibrar` es explícito y este script pide
   espacio antes.

🔴 Y hay un motivo para dudar de que funcione: el resultado llega por
   **NOTIFICACIÓN**, y en este firmware las notificaciones de motor se registran
   sin error y **no emiten ni un mensaje** (evidencia 35). Puede pasar lo mismo.
   Por eso hay timeout — el ejemplo oficial se queda en un bucle infinito, y su
   propio comentario reconoce que «en un proyecto real debería haber uno».
"""
import argparse
import asyncio
import sys

from sphero_sdk import SpheroRvrAsync, SerialAsyncDal

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# 🔴 Con el loop PARADO: su constructor hace run_until_complete().
rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))

resultado = {}


async def al_calibrar(respuesta):
    print(f'\n  ✅ NOTIFICACIÓN RECIBIDA: {respuesta}')
    resultado.update(respuesta or {})
    resultado['recibida'] = True


async def main(calibrar: bool, espera: float) -> int:
    print('═' * 78)
    print('MAGNETÓMETRO DEL RVR — ¿hay rumbo absoluto?')
    print('═' * 78)
    await rvr.wake()
    await asyncio.sleep(2)

    # ── 1. La lectura directa, que ya sabemos que falla. Se repite para dejar
    #       constancia en la misma corrida que el resto.
    print('\n  1) get_magnetometer_reading()  (CID 0x52)')
    try:
        r = await rvr.get_magnetometer_reading(timeout=8)
        print(f'     ✅ {r}   ← ¡INESPERADO! revisa la evidencia 41')
    except Exception as e:                                  # noqa: BLE001
        print(f'     🔴 {type(e).__name__}: {e}   (esperado: bad_cid)')

    # ── 2. ¿Existe el sistema de control por magnetómetro? Es una CONSULTA:
    #       no mueve nada, y dice si el firmware lo conoce.
    print('\n  2) get_default_control_system_for_type(magnetometer_drive = 7)')
    try:
        r = await rvr.get_default_control_system_for_type(
            control_system_type=7, timeout=8)
        print(f'     ✅ {r}   ← el firmware SÍ conoce el sistema por magnetómetro')
    except Exception as e:                                  # noqa: BLE001
        print(f'     🔴 {type(e).__name__}: {e}')

    if not calibrar:
        print('\n  3) magnetometer_calibrate_to_north()  — SALTADO')
        print('     ⚠️ Puede GIRAR el robot. Añade --calibrar y despeja el espacio.')
        await rvr.close()
        print('═' * 78)
        return 0

    # ── 3. La calibración. Es lo único que puede dar el rumbo absoluto.
    print('\n  3) magnetometer_calibrate_to_north()  (CID 0x25)')
    print('     🔴 EL ROBOT VA A GIRAR 360° EN SENTIDO ANTIHORARIO.')
    print('        Confirmado en el foro oficial de Sphero. Necesita espacio.')
    try:
        await rvr.on_magnetometer_calibration_complete_notify(handler=al_calibrar)
        print('     · manejador de la notificación registrado')
    except Exception as e:                                  # noqa: BLE001
        print(f'     🔴 no se pudo registrar la notificación: {e}')

    try:
        await rvr.magnetometer_calibrate_to_north(timeout=8)
        print('     · comando aceptado, esperando el resultado…')
    except Exception as e:                                  # noqa: BLE001
        print(f'     🔴 {type(e).__name__}: {e}')
        await rvr.close()
        print('═' * 78)
        return 1

    # 🔴 CON TIMEOUT. El ejemplo oficial de Sphero espera en un bucle infinito.
    t = 0.0
    while not resultado.get('recibida') and t < espera:
        await asyncio.sleep(0.2)
        t += 0.2
        if int(t * 5) % 25 == 0:
            print(f'     · esperando… {t:.0f}/{espera:.0f} s')

    print()
    if resultado.get('recibida'):
        yaw = resultado.get('yaw_north_direction')
        exito = resultado.get('is_successful')
        print(f'  ✅ CALIBRACIÓN COMPLETA · is_successful={exito} · '
              f'yaw_north_direction = {yaw}')
        print('     🔴 ESE NÚMERO ES LA REFERENCIA ABSOLUTA que le falta al proyecto:')
        print('        el desfase entre el yaw=0 (arbitrario, del encendido) y el')
        print('        NORTE MAGNÉTICO. Con él, rumbo_absoluto = yaw_IMU + desfase,')
        print('        que es exactamente lo que hace la app de Sphero.')
        print()
        print('     ⚠️ ANTES DE FIARSE, REPETIRLO 3 VECES girando el robot en medio.')
        print('        Sphero avisa de que a ras de suelo hay hierro en las')
        print('        estructuras y las lecturas son ruidosas. Si los tres valores')
        print('        no concuerdan dentro de unos pocos grados, NO SIRVE.')
    else:
        print(f'  🔴 SIN NOTIFICACIÓN en {espera:.0f} s.')
        print('     Es el mismo patrón que las notificaciones de motor (evidencia 35):')
        print('     se aceptan sin error y no emiten nada. Si además el robot NO giró,')
        print('     el comando probablemente tampoco está implementado.')
        print('     → El rumbo absoluto NO se puede obtener del RVR.')

    await rvr.drive_stop()
    await rvr.close()
    print('═' * 78)
    return 0 if resultado.get('recibida') else 2


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--calibrar', action='store_true',
                    help='⚠️ ejecuta la calibración: PUEDE GIRAR EL ROBOT')
    ap.add_argument('--seguro', action='store_true',
                    help='solo consultas (es el comportamiento por defecto)')
    ap.add_argument('--espera', type=float, default=45.0)
    a = ap.parse_args()
    try:
        sys.exit(loop.run_until_complete(main(a.calibrar, a.espera)))
    except KeyboardInterrupt:
        loop.run_until_complete(rvr.drive_stop())
        loop.run_until_complete(rvr.close())
        sys.exit(1)
