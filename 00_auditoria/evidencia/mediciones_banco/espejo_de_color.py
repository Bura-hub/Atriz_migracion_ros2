r"""El robot se enciende del color que ve debajo. Espejo de color, en vivo.

    python3 espejo_de_color.py --calibrar 20 --seg 120
    python3 espejo_de_color.py --desde-csv ciclo.csv --base base.csv

NO mueve el robot. Lee el RGBC (que mira HACIA ABAJO) y pinta TODOS los LEDs del
RVR con ese color, escalado entre el mínimo y el máximo de cada canal.

⚠️ ACCIÓN FÍSICA: enciende todos los LEDs del robot y los deja encendidos
   mientras corre. Sale de la batería del RVR, que es también la de la Pi.

🔴 EL LED BLANCO DEL SENSOR VA APAGADO. Sobre una superficie que EMITE, encenderlo
   no pierde precisión: ENGAÑA. Medido el 2026-08-08 sobre una pantalla roja a
   tope: `R/G` 5,12 con la luz del sensor apagada (rojo) contra 0,66 encendida —
   o sea el sensor lee MENOS rojo que verde sobre una superficie roja, porque el
   reflejo especular de su propio LED aporta el 88 % de lo que mide. Evidencia 86.

🔴 POR QUÉ HAY QUE ESCALAR, Y POR QUÉ ES PELIGROSO
   Lo que devuelve el RGBC sobre un piso luminoso son cuentas pequeñas y con poco
   recorrido (medido el 2026-08-12 sobre el suelo del laboratorio: R 15-39,
   G 33-76, B 13-45). Mandarlas tal cual a unos LEDs de 0-255 daría un color
   apagado y casi siempre el mismo. Estirar cada canal entre su mínimo y su máximo
   lo arregla — Y AMPLIFICA EL RUIDO EN LA MISMA PROPORCIÓN. Si el recorrido de un
   canal es de unas pocas cuentas, lo que se está estirando es la dispersión del
   sensor y los LEDs van a parpadear sin que debajo cambie nada. El guion lo AVISA
   con `--min-recorrido` y suaviza con una mediana móvil, que no arregla la causa
   pero deja de estroboscopiar a un aula entera.

📌 LA LÍNEA BASE NO ES CERO. Con el LED del sensor apagado, el suelo del
   laboratorio da `claro ≈ 99` de luz ambiente reflejada, que se SUMA a lo que
   emita la baldosa. Con `--base` se resta y los colores dejan de salir lavados
   hacia el color de la lámpara de la sala.

CIERRE: los LEDs se apagan SIEMPRE — Ctrl-C, Ctrl-\, SIGTERM y al perder el SSH.
   Es el fallo de los cuatro caminos de salida de la evidencia 56, y aquí deja al
   robot encendido gastando batería toda la clase.
"""
import argparse
import csv
import signal
import statistics
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from rclpy.signals import SignalHandlerOptions
from std_srvs.srv import SetBool
from atriz_rvr_msgs.srv import GetRGBCSensorValues, SetLeds

SENALES_DE_CIERRE = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)
CANALES = ('rojo', 'verde', 'azul')

p = argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--seg', type=float, default=120.0, help='cuánto tiempo hacer de espejo (s)')
p.add_argument('--hz', type=float, default=5.0,
               help='veces por segundo que se repinta el color (por defecto 5)')
p.add_argument('--calibrar', type=float, default=0.0,
               help='segundos de observación previa para aprender mín/máx de cada canal')
p.add_argument('--desde-csv', default=None,
               help='sacar mín/máx de un CSV de registrar_piso_luminoso.py')
p.add_argument('--base', default=None,
               help='CSV de línea base (baldosa APAGADA) que se resta antes de escalar')
p.add_argument('--suavizado', type=int, default=5,
               help='muestras de la mediana móvil (1 = sin suavizar)')
p.add_argument('--min-recorrido', type=int, default=8,
               help='recorrido mínimo por canal para no avisar de que se amplifica ruido')
a = p.parse_args(remove_ros_args(args=sys.argv)[1:])

if a.hz <= 0:
    print('  🔴 --hz tiene que ser mayor que 0'); raise SystemExit(2)


def leer_csv(ruta):
    """Devuelve la lista de (r, g, b) de un CSV de registrar_piso_luminoso.py."""
    with open(ruta, newline='') as fh:
        return [(int(f['rojo']), int(f['verde']), int(f['azul']))
                for f in csv.DictReader(fh)]


# 🔴 SignalHandlerOptions.NO es obligatorio: con el manejador de rclpy un Ctrl-C
#    invalida el contexto ANTES de que podamos apagar los LEDs, y la llamada muere
#    con «publisher's context is invalid». Medido el 2026-08-02.
rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
n = Node('espejo_de_color')
cli_led_sensor = n.create_client(SetBool, '/enable_color')
cli_rgbc = n.create_client(GetRGBCSensorValues, '/get_rgbc_sensor_values')
cli_leds = n.create_client(SetLeds, '/set_leds')
for c, nom in ((cli_led_sensor, '/enable_color'), (cli_rgbc, '/get_rgbc_sensor_values'),
               (cli_leds, '/set_leds')):
    if not c.wait_for_service(timeout_sec=15):
        print(f'  🔴 {nom} no responde. ¿está corriendo atriz-robot?')
        raise SystemExit(1)

_cerrando = False


def llamar(cli, req, seg=5.0):
    f = cli.call_async(req)
    rclpy.spin_until_future_complete(n, f, timeout_sec=seg)
    return f.result()


def pintar(r, g, b):
    """🔴 `SetLeds.srv` NO tiene campos de respuesta: no hay `success` que mirar.
    El instrumento aquí es el OJO de quien tiene el robot delante."""
    llamar(cli_leds, SetLeds.Request(rgb_color=[int(r), int(g), int(b)]))


def apagar():
    """Se llama desde CUALQUIER camino de salida. Idempotente."""
    global _cerrando
    if _cerrando:
        return
    _cerrando = True
    try:
        if rclpy.ok():
            pintar(0, 0, 0)
            llamar(cli_led_sensor, SetBool.Request(data=False))
            print('  ✓ LEDs del robot APAGADOS · LED del sensor APAGADO')
    except Exception as e:                # noqa: BLE001 — cerrar nunca debe estorbar
        print(f'  ⚠️ no se pudo confirmar el apagado: {e}')
        print('     🔴 MIRA EL ROBOT. Si sigue encendido: ros2 service call /set_leds '
              'atriz_rvr_msgs/srv/SetLeds "{rgb_color: [0,0,0]}"')


def _por_senal(sig, _):
    print(f'\n  ⚠️ señal {signal.Signals(sig).name}: cerrando')
    apagar()
    raise SystemExit(130)


for s in SENALES_DE_CIERRE:
    signal.signal(s, _por_senal)


def leer():
    """Una lectura (r, g, b) o None si el sensor NO contestó.

    🔴 Sin mirar `success`, «no hay nada que ver» y «el sensor no respondió» son
       el mismo (0,0,0)."""
    r = llamar(cli_rgbc, GetRGBCSensorValues.Request())
    if r is None or not r.success:
        return None
    return (r.red_channel_value, r.green_channel_value, r.blue_channel_value)


print('=' * 76)
print(' ESPEJO DE COLOR · el robot se enciende del color que ve debajo')
print('=' * 76)

# 🔴 Inicializadas ANTES del try: si algo aborta durante la calibración, el
#    resumen de abajo daría NameError y taparía el error de verdad.
n_pint = 0
ultimo = None

try:
    print('  ⚠️ apago el LED blanco del sensor (obligatorio sobre una superficie que EMITE)')
    llamar(cli_led_sensor, SetBool.Request(data=False))
    time.sleep(1.5)

    # ── La base que se resta ─────────────────────────────────────────────────
    base = (0, 0, 0)
    if a.base:
        m = leer_csv(a.base)
        if not m:
            print(f'  🔴 {a.base} no tiene muestras'); raise SystemExit(1)
        base = tuple(int(statistics.median(x[i] for x in m)) for i in range(3))
        print(f'  base restada (de {a.base}): R {base[0]}  G {base[1]}  B {base[2]}')

    # ── Los mín/máx con los que se escala ───────────────────────────────────
    muestras = []
    if a.desde_csv:
        muestras = leer_csv(a.desde_csv)
        print(f'  mín/máx tomados de {a.desde_csv} ({len(muestras)} muestras)')
    elif a.calibrar > 0:
        print(f'  ⚠️ calibrando {a.calibrar:.0f} s — DEJA QUE EL PISO COMPLETE SU CICLO,')
        print('     porque lo que no se vea ahora quedará fuera de la escala')
        t0 = time.monotonic()
        while time.monotonic() - t0 < a.calibrar:
            v = leer()
            if v:
                muestras.append(v)
            time.sleep(0.02)
        print(f'  {len(muestras)} muestras de calibración')
    else:
        print('  🔴 hace falta --calibrar N o --desde-csv fichero.csv')
        print('     sin mín/máx no hay escala, y sin escala el color sale plano')
        raise SystemExit(2)

    if not muestras:
        print('  🔴 sin muestras para calibrar'); raise SystemExit(1)

    lo, hi, estrecho = [], [], []
    for i, nom in enumerate(CANALES):
        col = [max(x[i] - base[i], 0) for x in muestras]
        lo.append(min(col))
        hi.append(max(col))
        rec = hi[i] - lo[i]
        marca = ''
        if rec < a.min_recorrido:
            estrecho.append(nom)
            marca = '   ⚠️ RECORRIDO CORTO'
        print(f'  {nom:6s}  mín {lo[i]:4d}  máx {hi[i]:4d}  recorrido {rec:4d}{marca}')

    if estrecho:
        print(f'  🔴 {", ".join(estrecho)}: el recorrido no llega a {a.min_recorrido} cuentas.')
        print('     Estirar eso a 0-255 AMPLIFICA LA DISPERSIÓN DEL SENSOR, no una señal.')
        print('     Los LEDs parpadearán sin que debajo cambie nada. Sigo, pero avisado:')
        print('     si el piso estaba encendido y aun así el recorrido es corto, el sensor')
        print('     no está separando sus colores y la gráfica tampoco lo hará.')

    # ── El espejo ────────────────────────────────────────────────────────────
    print(f'  espejo {a.seg:.0f} s a {a.hz:.1f} Hz · suavizado {a.suavizado} · Ctrl-C para salir')
    periodo = 1.0 / a.hz
    hist = []
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.seg:
        ciclo = time.monotonic()
        v = leer()
        if v is not None:
            hist.append(v)
            if len(hist) > max(a.suavizado, 1):
                hist.pop(0)
            suave = [statistics.median(x[i] for x in hist) for i in range(3)]
            salida = []
            for i in range(3):
                bruto = max(suave[i] - base[i], 0)
                rec = hi[i] - lo[i]
                # 🔴 Recorrido 0 -> no se puede escalar. Se manda 0, no se divide.
                v255 = 0 if rec <= 0 else (bruto - lo[i]) * 255.0 / rec
                salida.append(int(min(max(v255, 0), 255)))
            pintar(*salida)
            n_pint += 1
            ultimo = salida
            if n_pint % max(int(a.hz), 1) == 0:
                print(f'    {time.monotonic() - t0:6.1f} s   sensor R {v[0]:3d} G {v[1]:3d} '
                      f'B {v[2]:3d}   →   LEDs {salida}')
        resto = periodo - (time.monotonic() - ciclo)
        if resto > 0:
            time.sleep(resto)
finally:
    apagar()

print('-' * 76)
print(f'  {n_pint} repintados · último color {ultimo}')
print('  📌 El instrumento aquí es TU OJO: SetLeds.srv no devuelve `success`.')
print('=' * 76)

n.destroy_node()
rclpy.shutdown()
