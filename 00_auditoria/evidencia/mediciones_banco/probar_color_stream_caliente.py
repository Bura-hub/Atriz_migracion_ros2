#!/usr/bin/env python3
"""¿Encender el LED del color EN CALIENTE, CON EL STREAMING YA ARRANCADO, da lecturas?

    # 👤 hace falta parar el driver: este guion abre /dev/rvr directamente
    sudo systemctl stop atriz-robot
    python3 -u probar_color_stream_caliente.py
    sudo systemctl start atriz-robot

⚠️ ENCIENDE UN LED BLANCO bajo el chasis. No mueve el robot. Lo apaga siempre,
   tambien en el camino de error.

═══════════════════════════════════════════════════════════════════════════════
LA PREGUNTA, Y POR QUE NO LA CONTESTA NINGUN BANCO ANTERIOR
═══════════════════════════════════════════════════════════════════════════════
El usuario recuerda que en ROS 1 el ciclo era: llamar al servicio `enable_color`
(que hace `enable_color_detection(True)`) y DESPUES leer `/color`, y que salian
mediciones reales. El codigo de ROS 1 lo respalda: el handler de
`color_detection` se registra SIEMPRE (`Atriz_rvr_node.py:1246-1249`), el
streaming arranca en el arranque (`:1313`), y el LED se enciende DESPUES, en
caliente, desde el servicio (`:331-344`, registrado en `:1636`).

El proyecto de ROS 2 documenta lo contrario: «con el streaming de
`color_detection` ya configurado, `enable_color_detection` NO HACE NADA — 481
mensajes de /color, todos ceros».

Los dos bancos que ya existen NO discriminan:
  · `medir_sensor_color.py`      -> sin streaming, solo consulta directa
  · `probar_color_en_caliente.py`-> tambien sin streaming (y ademas construye
                                    el SpheroRvrAsync dentro de `asyncio.run`,
                                    que es justo la trampa que su cabecera avisa)

Aqui se reproduce la secuencia de ROS 1 TAL CUAL: streaming CORRIENDO, y el
enable llega despues.

═══════════════════════════════════════════════════════════════════════════════
LOS TESTIGOS (tres, y ninguno es el mismo dato)
═══════════════════════════════════════════════════════════════════════════════
  1) el STREAM `color_detection`        -> lo que publicaria /color
  2) `get_rgbc_sensor_values()`         -> consulta directa, OTRO camino
  3) `get_ambient_light_sensor_value()` -> OTRO sensor fisico, mide luz
  4) 👤 TU OJO: ¿se enciende el LED blanco bajo el chasis? Manda sobre los tres.

═══════════════════════════════════════════════════════════════════════════════
QUE DISCRIMINA CADA RESULTADO
═══════════════════════════════════════════════════════════════════════════════
  FASE 2 (enable en caliente) con muestras no-cero  -> el usuario tiene razon;
        la documentacion de ROS 2 esta mal y el boton es un servicio trivial.
  FASE 2 a cero pero `clear` de la consulta directa sube -> el LED SI se
        enciende en caliente, pero el stream quedo atado a una fuente muerta:
        hace falta reordenar (stop -> enable -> start), que es lo que mide la
        FASE 3.
  FASE 2 a cero Y `clear` sin subir -> el enable no llega mientras el stream
        corre. Solo queda reordenar o reiniciar.
"""
import asyncio
import sys

RUTA_SDK = '/home/sphero/atriz_ws/src/Atriz_rvr/atriz_rvr_driver/scripts'
sys.path.insert(0, RUTA_SDK)

from sphero_sdk import SerialAsyncDal, SpheroRvrAsync   # noqa: E402
from sphero_sdk import RvrStreamingServices             # noqa: E402

VENTANA = 6.0        # s de escucha por fase
INTERVALO_MS = 250   # el mismo que ROS 1 (`Atriz_rvr_node.py:1313`)

muestras_color: list[tuple] = []
muestras_luz: list[float] = []


async def h_color(d):
    c = d.get('ColorDetection', {})
    muestras_color.append((c.get('R'), c.get('G'), c.get('B'), c.get('Confidence')))


async def h_luz(d):
    muestras_luz.append(d.get('AmbientLight', {}).get('Light'))


async def consulta_directa(rvr):
    try:
        rgbc = await asyncio.wait_for(rvr.get_rgbc_sensor_values(), timeout=6)
    except Exception as e:                                    # noqa: BLE001
        rgbc = {'error': str(e)}
    try:
        luz = await asyncio.wait_for(rvr.get_ambient_light_sensor_value(), timeout=6)
    except Exception as e:                                    # noqa: BLE001
        luz = {'error': str(e)}
    return rgbc, luz


async def fase(rvr, etiqueta):
    muestras_color.clear()
    muestras_luz.clear()
    await asyncio.sleep(VENTANA)
    col = list(muestras_color)
    lz = [x for x in muestras_luz if x is not None]
    rgbc, luz = await consulta_directa(rvr)
    no_cero = [c for c in col if any(v for v in c[:3] if v)]
    print(f'\n  [{etiqueta}]')
    print(f'    stream color   : {len(col)} muestras, {len(no_cero)} con algun canal != 0')
    if col:
        print(f'      primeras 3   : {col[:3]}')
    if no_cero:
        print(f'      no-cero ej.  : {no_cero[:3]}')
    print(f'    stream luz amb.: {len(lz)} muestras'
          + (f', min/max {min(lz)}/{max(lz)}' if lz else ''))
    print(f'    consulta RGBC  : {rgbc}')
    print(f'    consulta luz   : {luz}')
    return len(no_cero), rgbc.get('clear_channel_value')


async def main(rvr):
    print('=' * 78)
    print(' enable_color_detection EN CALIENTE, con el streaming YA arrancado')
    print('=' * 78)
    await rvr.wake()
    await asyncio.sleep(2)

    encendido = False
    try:
        # ── Igual que ROS 1: limpiar, parar, registrar handlers, arrancar ────
        await rvr.sensor_control.clear()
        await rvr.sensor_control.stop()
        await rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.color_detection, handler=h_color)
        await rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.ambient_light, handler=h_luz)
        await rvr.sensor_control.start(interval=INTERVALO_MS)
        print(f'\n  streaming ARRANCADO a {INTERVALO_MS} ms, con el LED apagado')

        nc0, c0 = await fase(rvr, '1 · streaming corriendo, LED nunca encendido')

        # ── FASE 2: exactamente lo que hacia el servicio de ROS 1 ────────────
        print('\n  >>> enable_color_detection(True) EN CALIENTE')
        print('      👤 MIRA EL ROBOT: ¿se enciende el LED blanco bajo el chasis?')
        await rvr.enable_color_detection(is_enabled=True)
        encendido = True
        await asyncio.sleep(.1)          # el mismo sleep de `Atriz_rvr_node.py:341`
        nc1, c1 = await fase(rvr, '2 · tras enable en caliente (sleep 0.1, como ROS 1)')
        nc1b, c1b = await fase(rvr, '2b · %.0f s mas tarde (por si tarda)' % VENTANA)

        # ── FASE 3: la alternativa B2, reordenar el streaming ────────────────
        print('\n  >>> sensor_control.stop() -> enable(True) -> start()')
        await rvr.sensor_control.stop()
        await asyncio.sleep(.2)
        await rvr.enable_color_detection(is_enabled=True)
        await asyncio.sleep(.2)
        await rvr.sensor_control.start(interval=INTERVALO_MS)
        nc2, c2 = await fase(rvr, '3 · tras reordenar stop -> enable -> start')

        # ── FASE 4: apagar y comprobar que baja ──────────────────────────────
        print('\n  >>> enable_color_detection(False)')
        await rvr.enable_color_detection(is_enabled=False)
        encendido = False
        await asyncio.sleep(.1)
        nc3, c3 = await fase(rvr, '4 · tras apagar el LED en caliente')

        print('\n' + '=' * 78)
        print(' VEREDICTO')
        print('=' * 78)
        print(f'  muestras no-cero del stream: {nc0} -> {nc1} / {nc1b} -> {nc2} -> {nc3}')
        print(f'  clear de la consulta directa: {c0} -> {c1} / {c1b} -> {c2} -> {c3}')
        if nc1 or nc1b:
            print('  ✅ EL ENABLE EN CALIENTE FUNCIONA: el usuario tiene razon y la')
            print('     documentacion de ROS 2 hay que corregirla.')
        elif c1 and c0 is not None and c1 > 5 * max(c0, 1):
            print('  ⚠️ El LED SI se enciende en caliente (sube `clear`), pero el STREAM')
            print('     sigue a cero: el servicio de streaming quedo atado a una fuente')
            print('     muerta. Hace falta reordenar.')
            if nc2:
                print('     Y reordenar SI lo arregla (fase 3 da muestras no-cero).')
        else:
            print('  🔴 El enable en caliente no hace nada medible: ni el stream ni la')
            print('     consulta directa cambian. La documentacion de ROS 2 se sostiene.')
            if nc2:
                print('     Reordenar (fase 3) SI funciona.')
        print('\n  👤 Y EL TESTIGO QUE MANDA: ¿viste el LED blanco encendido?')
    finally:
        # 🔴 Cada (True) necesita su (False), tambien aqui.
        try:
            await rvr.enable_color_detection(is_enabled=False)
            print('\n  LED del sensor de color APAGADO.')
        except Exception:                                     # noqa: BLE001
            print('\n  🔴 NO se pudo apagar el LED del sensor: MIRALO')
        for coro in (rvr.sensor_control.clear(), rvr.close()):
            try:
                await coro
            except Exception:                                 # noqa: BLE001
                pass
    return 0


if __name__ == '__main__':
    # 🔴 Con el loop PARADO: `SpheroRvrAsync.__init__` hace `run_until_complete`,
    #    asi que construirlo desde dentro de una corrutina en marcha revienta.
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _rvr = SpheroRvrAsync(dal=SerialAsyncDal(_loop, port_id='/dev/rvr'))
    sys.exit(_loop.run_until_complete(main(_rvr)))
