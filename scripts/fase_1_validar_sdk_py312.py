#!/usr/bin/env python3
"""
Fase 1 — GO / NO-GO de toda la migración a ROS 2.

    python3 fase_1_validar_sdk_py312.py [--puerto /dev/rvr]

EJECUTAR ESTO ANTES DE PORTAR UNA SOLA LÍNEA DEL DRIVER.

QUÉ DECIDE
==========
El SDK de Sphero (`sphero_sdk`, 103 ficheros) es la pieza insustituible del
proyecto: es lo único que sabe hablar con el RVR. Si no funciona en Python 3.12
—el que trae Ubuntu 24.04— la migración a ROS 2 Jazzy no es viable tal como está
planteada, y hay que replantear (contenedor con Python 3.8, o portar el SDK).

El análisis estático hecho el 2026-07-29 fue muy favorable:

    imports de rospy/rclpy en el SDK ......  0 de 103 ficheros
    @asyncio.coroutine (roto en 3.11) .....  0
    kwarg loop= (roto en 3.10) ............  0
    'yield from' en corrutinas ............  0
    asyncio.get_event_loop() ..............  4, y 3 en el backend 'observer'
                                              que el proyecto no usa

Es decir: sobre el papel, un parche de ~4 líneas. **Pero análisis estático no es
ejecución.** Este script lo comprueba de verdad.

CÓMO INTERPRETARLO
==================
    GO          → seguir con el port a rclpy según el plan
    GO PARCIAL  → funciona con los parches indicados; aplicarlos y seguir
    NO-GO       → parar y replantear. Ver "Si sale NO-GO" al final de la salida.

REQUISITOS
==========
  - Python 3.12 (o el que traiga el sistema; el script avisa de la versión)
  - pyserial y pyserial-asyncio instalados
  - El RVR conectado y **ENCENDIDO** (un RVR dormido no contesta nada, y el
    síntoma es idéntico a un cable mal puesto)
  - Ruta al SDK accesible por sys.path
"""
import argparse
import asyncio
import importlib
import os
import platform
import sys
import time

# ── Rutas donde buscar el SDK, en orden ──────────────────────────────────────
CANDIDATOS_SDK = [
    os.path.expanduser('~/atriz_ws/src/Atriz_rvr/atriz_rvr_driver/scripts'),           # ROS 2
    os.path.expanduser('~/atriz_git/src/Atriz_rvr/atriz_rvr_driver/scripts'),          # ROS 1
    os.path.expanduser('~/atriz_git/devel/lib/python3/dist-packages'),
]

VERDE, ROJO, AMAR, AZUL, FIN = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[0m'
def ok(m):   print(f'  {VERDE}✓{FIN} {m}')
def mal(m):  print(f'  {ROJO}✗{FIN} {m}')
def avis(m): print(f'  {AMAR}!{FIN} {m}')
def sec(m):  print(f'\n{AZUL}▶ {m}{FIN}')

fallos, parches = [], []


def paso_1_entorno():
    sec('1/6 · Entorno')
    v = sys.version_info
    print(f'  Python {platform.python_version()}  ({sys.executable})')
    print(f'  {platform.platform()}')
    if v >= (3, 12):
        ok(f'Python {v.major}.{v.minor} — es el escenario que hay que validar')
    elif v >= (3, 10):
        avis(f'Python {v.major}.{v.minor}: los patrones rotos en 3.10/3.11 ya aplican, '
             'pero no es exactamente el objetivo')
    else:
        avis(f'Python {v.major}.{v.minor}: DEMASIADO ANTIGUO para que esta prueba '
             'signifique algo. En 3.8 el SDK ya funciona; lo que hay que probar es 3.12.')


def paso_2_dependencias():
    """Las tres son OBLIGATORIAS, aunque aiohttp no se use para hablar con el robot.

    Aquí había un error de bulto (corregido el 2026-07-30): aiohttp estaba marcado
    como «opcional, no afecta al backend serie» y solo se avisaba de su ausencia.
    Pero `sphero_sdk/__init__.py` importa TODO de golpe, y esa cadena llega a
    `common/firmware/cms_fw_check_base.py`, que hace `import aiohttp` a nivel de
    módulo. Sin el paquete, el paso 4 muere con ModuleNotFoundError y el script
    imprime un **NO-GO falso**, sugiriendo replantear la arquitectura por una
    dependencia que se instala en diez segundos.

    Que aiohttp solo se USE para consultar la versión del firmware contra un
    servicio web de Sphero es cierto e irrelevante: el import es incondicional.
    """
    sec('2/6 · Dependencias del SDK')
    for mod, paquete, nota in (
            ('serial',         'python3-serial (apt) o pyserial (pip)',        'el enlace serie'),
            ('serial_asyncio', 'pyserial-asyncio (pip; NO existe en apt)',     'el backend asyncio'),
            ('aiohttp',        'python3-aiohttp (apt)',                        'lo importa __init__.py sin condiciones')):
        try:
            m = importlib.import_module(mod)
            ok(f'{mod} {getattr(m, "__version__", "?")}  — {nota}')
        except ImportError as e:
            mal(f'{mod} AUSENTE ({nota}): {e}')
            avis(f'instálalo con: {paquete}')
            fallos.append(f'falta {mod}')


def paso_3_localizar_sdk(extra=None):
    sec('3/6 · Localizar el SDK')
    rutas = ([extra] if extra else []) + CANDIDATOS_SDK
    for r in rutas:
        if r and os.path.isdir(os.path.join(r, 'sphero_sdk')):
            sys.path.insert(0, r)
            ok(f'encontrado en {r}')
            return r
    mal('no se encuentra sphero_sdk en ninguna ruta candidata:')
    for r in rutas:
        print(f'       {r}')
    fallos.append('SDK no encontrado')
    return None


def paso_4_importar():
    sec('4/6 · Importar el SDK (aquí es donde revientan los patrones obsoletos)')
    try:
        import sphero_sdk
        ok(f'sphero_sdk desde {sphero_sdk.__file__}')
        try:
            from sphero_sdk.__version__ import __version__ as ver
            ok(f'version {ver}')
        except Exception:
            pass
    except SyntaxError as e:
        mal(f'SyntaxError — sintaxis no válida en esta versión de Python: {e}')
        fallos.append('SyntaxError al importar el SDK')
        return False
    except Exception as e:
        mal(f'{type(e).__name__}: {e}')
        fallos.append(f'fallo al importar: {type(e).__name__}')
        return False

    for nombre in ('SpheroRvrAsync', 'SerialAsyncDal', 'RvrStreamingServices',
                   'RvrLedGroups', 'RawMotorModesEnum'):
        try:
            mod = importlib.import_module('sphero_sdk')
            getattr(mod, nombre)
            ok(f'{nombre} disponible')
        except Exception as e:
            mal(f'{nombre}: {type(e).__name__}: {e}')
            fallos.append(f'símbolo ausente: {nombre}')
    return True


def paso_5_compilar_todo(raiz):
    """Compila TODOS los .py del SDK: detecta sintaxis inválida sin ejecutar nada."""
    sec('5/6 · Compilar los 103 ficheros del SDK')
    base = os.path.join(raiz, 'sphero_sdk')
    total = errores = 0
    for dirp, _, ficheros in os.walk(base):
        if '__pycache__' in dirp:
            continue
        for f in ficheros:
            if not f.endswith('.py'):
                continue
            total += 1
            ruta = os.path.join(dirp, f)
            # compile() en memoria: detecta SyntaxError sin escribir nada al disco
            # (py_compile no sirve: rechaza /dev/null como cfile)
            try:
                with open(ruta, 'r', encoding='utf-8') as fh:
                    compile(fh.read(), ruta, 'exec')
            except SyntaxError as e:
                errores += 1
                mal(f'{os.path.relpath(ruta, raiz)}:{e.lineno}: {e.msg}')
                parches.append(os.path.relpath(ruta, raiz))
            except Exception as e:
                errores += 1
                mal(f'{os.path.relpath(ruta, raiz)}: {type(e).__name__}: {e}')
                parches.append(os.path.relpath(ruta, raiz))
    if errores == 0:
        ok(f'los {total} ficheros compilan sin errores de sintaxis')
    else:
        mal(f'{errores} de {total} ficheros NO compilan')
        fallos.append(f'{errores} ficheros con sintaxis inválida')
    return errores == 0


def paso_6_hablar_con_el_robot(puerto):
    sec(f'6/6 · Hablar con el RVR de verdad ({puerto})')
    if not os.path.exists(puerto):
        mal(f'{puerto} no existe. ¿Regla udev aplicada? ¿dtoverlay=disable-bt?')
        fallos.append(f'{puerto} inexistente')
        return False

    from sphero_sdk import SpheroRvrAsync, SerialAsyncDal

    # OJO: SpheroRvrAsync.__init__ hace run_until_complete() para el check de
    # firmware, así que hay que construirlo FUERA de un loop en ejecución.
    # (Es 'sphero_rvr_async.py:35', el único get_event_loop() de la ruta usada.)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        mal(f'no se pudo crear el event loop: {e}')
        fallos.append('event loop')
        return False

    t0 = time.time()
    try:
        rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop, port_id=puerto))
        dt = time.time() - t0
        ok(f'SpheroRvrAsync construido en {dt:.1f} s')
        # El tiempo de construcción ES un diagnóstico. Medido el 2026-07-29:
        #   robot despierto  -> 0.0 s
        #   robot dormido    -> 10.6 s (dos timeouts de 5 s del check de firmware,
        #                       que rvr_fw_check_async.py traga en silencio)
        if dt > 8:
            avis(f'tardó {dt:.1f} s. Con el robot despierto esto tarda ~0 s. '
                 'Casi seguro son los DOS timeouts del check de firmware, que '
                 'rvr_fw_check_async.py captura en silencio: el robot NO responde. '
                 '¿Está encendido?')
    except Exception as e:
        mal(f'{type(e).__name__}: {e}')
        fallos.append(f'construcción: {type(e).__name__}')
        return False

    async def dialogo():
        await rvr.wake()
        await asyncio.sleep(2)
        bat = await asyncio.wait_for(rvr.get_battery_percentage(), timeout=10)
        ok(f'batería: {bat}')
        # target=1 -> procesador Nordic; target=2 -> ST. El SDK lo exige.
        ver = await asyncio.wait_for(rvr.get_main_application_version(target=1), timeout=10)
        ok(f'firmware (Nordic): {ver}')
        # Streaming al ritmo elegido en la Fase 0.1
        recibidos = []
        from sphero_sdk import RvrStreamingServices
        async def h(_d):
            recibidos.append(time.time())
        await rvr.sensor_control.clear()
        await rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.locator, handler=h)
        await rvr.sensor_control.start(interval=60)
        await asyncio.sleep(6)
        await rvr.sensor_control.clear()
        if len(recibidos) > 2:
            hz = (len(recibidos) - 1) / (recibidos[-1] - recibidos[0])
            ok(f'streaming: {len(recibidos)} muestras a {hz:.2f} Hz '
               f'(esperado ~16.5 Hz con interval=60)')
            if hz < 12:
                avis('por debajo de lo medido en Noetic (16.59 Hz) — investigar')
        else:
            mal(f'streaming: solo {len(recibidos)} muestras. El robot no envía datos.')
            fallos.append('streaming vacío')
        await rvr.close()

    try:
        loop.run_until_complete(asyncio.wait_for(dialogo(), timeout=45))
        return True
    except asyncio.TimeoutError:
        mal('TIMEOUT — el RVR no responde. ¿ESTÁ ENCENDIDO? ¿Batería puesta?')
        fallos.append('el RVR no responde')
        return False
    except Exception as e:
        mal(f'{type(e).__name__}: {e}')
        fallos.append(f'diálogo: {type(e).__name__}')
        return False
    finally:
        try:
            loop.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description='GO/NO-GO del SDK de Sphero en Python 3.12')
    ap.add_argument('--puerto', default='/dev/rvr')
    ap.add_argument('--ruta-sdk', default=None, help='directorio que contiene sphero_sdk/')
    ap.add_argument('--sin-robot', action='store_true',
                    help='omitir el paso 6 (solo comprueba imports y sintaxis)')
    a = ap.parse_args()

    print('=' * 70)
    print('  GO / NO-GO — SDK de Sphero sobre Python 3.12')
    print('=' * 70)

    paso_1_entorno()
    paso_2_dependencias()
    raiz = paso_3_localizar_sdk(a.ruta_sdk)
    if raiz:
        if paso_4_importar():
            paso_5_compilar_todo(raiz)
            if not a.sin_robot:
                paso_6_hablar_con_el_robot(a.puerto)
            else:
                sec('6/6 · Omitido (--sin-robot)')
                avis('sin hablar con el robot esto NO es un GO completo')

    print('\n' + '=' * 70)
    if not fallos:
        print(f'{VERDE}  GO — el SDK funciona en esta versión de Python.{FIN}')
        print('  Seguir con el port a rclpy según la Fase 2 del plan.')
    else:
        print(f'{ROJO}  NO-GO / GO PARCIAL — {len(fallos)} problema(s):{FIN}')
        for f in fallos:
            print(f'    · {f}')
        if parches:
            print('\n  Ficheros que no compilan (candidatos a parche):')
            for p in sorted(set(parches)):
                print(f'    · {p}')
        print("""
  SI SALE NO-GO — opciones, de menos a más invasiva:

  1. Parchear el SDK. Si son unos pocos ficheros con patrones asyncio
     obsoletos, es lo más barato. El análisis estático del 2026-07-29 predecía
     solo `sphero_rvr_async.py:35` (un `get_event_loop()`).

  2. Contenedor con Python 3.8. Docker con el SDK aislado, hablando con el
     nodo ROS 2 por un socket. Funciona, pero añade una pieza que mantener en
     16 robots.

  3. Quedarse en Noetic. La Fase 0.1 dejó el robot a 16.59 Hz y estable; es un
     punto de partida decente. Se pierden SLAM/Nav2 modernos y el soporte
     hasta 2029. Restaurar con la imagen de la Fase 0.3.

  4. Reimplementar el protocolo serie del RVR. Está documentado y ya lo
     validamos a mano en `raw_uart.py` (cabecera 0x8D, fin 0xD8, checksum por
     complemento). Es el camino largo, pero elimina la dependencia de un SDK
     que Sphero ya no mantiene.
""")
    print('=' * 70)
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
