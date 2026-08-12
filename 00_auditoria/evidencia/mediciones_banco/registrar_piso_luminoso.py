#!/usr/bin/env python3
r"""Registra el RGBC sobre un piso luminoso que CICLA DE COLOR SOLO, a CSV.

    python3 registrar_piso_luminoso.py --seg 120 --etiqueta "baldosa central"

NO mueve el robot. El sensor mira HACIA ABAJO: el robot tiene que estar ENCIMA
de la baldosa encendida.

POR QUÉ ESTA HERRAMIENTA Y NO `medir_superficie_emisora.py`

  Aquella contesta «¿ve algo el sensor?» con dos tandas y medianas por pantalla.
  Ésta contesta «¿QUÉ ve, a lo largo del tiempo?» y **guarda las muestras crudas**,
  que es lo que hace falta para dibujar después. Sin fichero no hay gráfica.

🔴 EL LED DEL SENSOR VA APAGADO, Y NO ES UN AJUSTE: DECIDE EL SIGNO.
  Medido el 2026-08-08 sobre una pantalla roja a tope (evidencia 86): con el LED
  del sensor APAGADO `R/G = 5,12` (rojo); ENCENDIDO `R/G = 0,66`, o sea el sensor
  lee MENOS rojo que verde sobre una superficie roja. Sobre vidrio el reflejo del
  propio LED es especular y blanco, y aporta el 88 % de lo que se mide. Encendido
  no pierde precisión: **engaña**.

🔴 Y `/color` NO SIRVE AQUÍ: publica CEROS con el LED apagado (40 de 40 mensajes
  no-cero con luz, 0 de 39 sin ella). Sale del *streaming*, que se apaga con la
  detección. Se usa el SERVICIO `/get_rgbc_sensor_values`, que es una CONSULTA y
  sigue respondiendo. Y el topic no trae `claro` de todas formas.

⚠️ LO QUE ESTA HERRAMIENTA **NO** PUEDE MEDIR: el parpadeo PWM de la baldosa. Se
  muestrea por servicio, a unos pocos Hz, y un PWM va a cientos o miles. Lo que sí
  se ve es su efecto agregado — dispersión anómala entre muestras consecutivas
  sobre un color estable, que es BATIDO (aliasing), no el parpadeo. Se informa
  como tal y no como una frecuencia.

CIERRE: el LED blanco de los bajos se apaga SIEMPRE — también con Ctrl-C, Ctrl-\,
  SIGTERM y al perder el SSH. Es el fallo de los cuatro caminos de salida que este
  proyecto ya pagó una vez (evidencia 56), y aquí cuesta batería del RVR.
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
from atriz_rvr_msgs.srv import GetRGBCSensorValues

SENALES_DE_CIERRE = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)

p = argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--seg', type=float, default=120.0, help='duración del registro (s)')
p.add_argument('--salida', default=None, help='CSV de salida (por defecto: piso_luminoso_<hora>.csv)')
p.add_argument('--etiqueta', default='sin etiqueta', help='dónde está el robot')
p.add_argument('--sin-control', action='store_true',
               help='no hacer la tanda de control con el LED del sensor ENCENDIDO')
a = p.parse_args(remove_ros_args(args=sys.argv)[1:])

SALIDA = a.salida or f'piso_luminoso_{time.strftime("%Y%m%d_%H%M%S")}.csv'
N_CONTROL = 12

# 🔴 SignalHandlerOptions.NO es obligatorio: con el manejador de rclpy, un Ctrl-C
#    invalida el contexto ANTES de que podamos apagar el LED, y la llamada muere
#    con «publisher's context is invalid». Medido el 2026-08-02.
rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
n = Node('registrar_piso_luminoso')
cli_led = n.create_client(SetBool, '/enable_color')
cli_rgbc = n.create_client(GetRGBCSensorValues, '/get_rgbc_sensor_values')
for c, nom in ((cli_led, '/enable_color'), (cli_rgbc, '/get_rgbc_sensor_values')):
    if not c.wait_for_service(timeout_sec=15):
        print(f'  🔴 {nom} no responde. ¿está corriendo atriz-robot?')
        raise SystemExit(1)

_cerrando = False


def llamar(cli, req, seg=10.0):
    f = cli.call_async(req)
    rclpy.spin_until_future_complete(n, f, timeout_sec=seg)
    return f.result()


def led(encendido):
    r = llamar(cli_led, SetBool.Request(data=encendido))
    time.sleep(1.5)                      # que el sensor se asiente
    return r is not None and r.success


def apagar_led():
    """Se llama desde CUALQUIER camino de salida. Idempotente."""
    global _cerrando
    if _cerrando:
        return
    _cerrando = True
    try:
        if rclpy.ok():
            llamar(cli_led, SetBool.Request(data=False), seg=5.0)
            print('  ✓ LED del sensor APAGADO')
    except Exception as e:                # noqa: BLE001 — cerrar nunca debe estorbar
        print(f'  ⚠️ no se pudo confirmar el apagado del LED: {e}')


def _por_senal(sig, _):
    print(f'\n  ⚠️ señal {signal.Signals(sig).name}: cerrando')
    apagar_led()
    raise SystemExit(130)


for s in SENALES_DE_CIERRE:
    signal.signal(s, _por_senal)


def leer():
    """Una lectura. Devuelve la tupla o None si el sensor NO contestó.

    🔴 Distinguir las dos cosas es obligatorio: sin mirar `success`, «no hay nada
       que ver» y «el sensor no respondió» son el mismo (0,0,0,0).
    """
    r = llamar(cli_rgbc, GetRGBCSensorValues.Request(), seg=5.0)
    if r is None or not r.success:
        return None
    return (r.red_channel_value, r.green_channel_value,
            r.blue_channel_value, r.clear_channel_value)


print('=' * 76)
print(f' PISO LUMINOSO · {a.etiqueta}')
print('=' * 76)
print(f'  salida: {SALIDA}')

filas = []
fallos_control = 0
control = None

try:
    # ── Control: el LED del sensor ENCENDIDO ─────────────────────────────────
    # No es el dato bueno: es la PRUEBA DE QUE EL SENSOR RESPONDE. Sin él, «con el
    # LED apagado no llega nada» es indistinguible de «el sensor está muerto» y de
    # «la baldosa está apagada». Cuesta ~5 s.
    if not a.sin_control:
        print('  ⚠️ ACCIÓN FÍSICA: enciendo el LED BLANCO bajo el chasis (control, ~5 s)')
        led(True)
        m = []
        for _ in range(N_CONTROL):
            v = leer()
            if v is None:
                fallos_control += 1
            else:
                m.append(v)
            time.sleep(0.10)
        if m:
            control = [statistics.median(x[i] for x in m) for i in range(4)]
            print(f'  control (LED ON)   R {control[0]:5.0f} G {control[1]:5.0f} '
                  f'B {control[2]:5.0f} claro {control[3]:5.0f}   ← el sensor RESPONDE')
        else:
            print(f'  🔴 el control no dio ni una lectura ({fallos_control} fallos): '
                  f'el sensor no responde. No sigo.')
            raise SystemExit(1)

    # ── El registro de verdad: LED del sensor APAGADO ────────────────────────
    print('  ⚠️ apago el LED del sensor — a partir de aquí solo se mide LO QUE EMITE el piso')
    led(False)
    print(f'  registrando {a.seg:.0f} s… (Ctrl-C corta y guarda lo que haya)')

    t0 = time.monotonic()
    fallos = 0
    while time.monotonic() - t0 < a.seg:
        t = time.monotonic() - t0
        v = leer()
        if v is None:
            fallos += 1
            continue
        filas.append((t,) + v)
        if len(filas) % 50 == 0:
            print(f'    {t:6.1f} s · {len(filas)} muestras · '
                  f'último R {v[0]} G {v[1]} B {v[2]} claro {v[3]}')
finally:
    apagar_led()

# ── Guardar SIEMPRE lo que se haya recogido ─────────────────────────────────
if filas:
    with open(SALIDA, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['t_s', 'rojo', 'verde', 'azul', 'claro'])
        for f in filas:
            w.writerow([f'{f[0]:.4f}', f[1], f[2], f[3], f[4]])
    print(f'  ✓ {len(filas)} muestras en {SALIDA}')
else:
    print('  🔴 0 muestras: no se escribe fichero')

# ── Resumen honesto ─────────────────────────────────────────────────────────
print('-' * 76)
if filas:
    dur = filas[-1][0] - filas[0][0]
    ritmo = (len(filas) - 1) / dur if dur > 0 else 0.0
    print(f'  ritmo de muestreo   {ritmo:5.2f} Hz  ({len(filas)} muestras en {dur:.1f} s, '
          f'{fallos} sin respuesta)')
    for i, nom in ((1, 'rojo'), (2, 'verde'), (3, 'azul'), (4, 'claro')):
        col = [f[i] for f in filas]
        print(f'  {nom:6s}  min {min(col):5d}   máx {max(col):5d}   mediana {statistics.median(col):6.0f}')
    claro = [f[4] for f in filas]
    techo = max(claro)
    # SATURACIÓN: la referencia es el blanco REFLECTANTE medido en este robot (2288)
    # y el máximo que dio una pantalla de móvil a tope (387). Un techo repetido
    # muchas veces es sospecha de saturación, no prueba: podría ser el color más
    # brillante del ciclo, simplemente.
    veces = claro.count(techo)
    print(f'  techo de `claro`    {techo}   alcanzado {veces} de {len(claro)} veces')
    print(f'                      (blanco reflectante en este robot: 2288 · pantalla de móvil: 387)')
    if veces > len(claro) * 0.1:
        print('  ⚠️ el techo se repite mucho: SOSPECHA de saturación. No es prueba —')
        print('     podría ser el color más brillante del ciclo. Se distingue bajando')
        print('     el brillo del piso y viendo si el techo baja con él.')
    # 🔴 EL RITMO DE MUESTREO NO ES EL RITMO DE INFORMACIÓN. Si el sensor refresca
    #    más despacio de lo que se le pregunta, se lee el MISMO valor varias veces
    #    y el CSV parece tener más resolución temporal de la que tiene. Se mide
    #    contando cuántas muestras consecutivas son IDÉNTICAS en los cuatro canales.
    iguales = sum(1 for i in range(len(filas) - 1) if filas[i][1:] == filas[i + 1][1:])
    frac = iguales / max(len(filas) - 1, 1)
    ritmo_util = ritmo * (1 - frac)
    print(f'  muestras repetidas  {iguales} de {len(filas) - 1} ({frac * 100:.0f} %)'
          f'   → ritmo ÚTIL ≈ {ritmo_util:.1f} Hz')
    if frac > 0.3:
        print('  ⚠️ se está SOBREMUESTREANDO: el sensor refresca más despacio de lo que se')
        print('     le pregunta. El CSV tiene más filas que información. Para la gráfica,')
        print('     eso NO es ruido: son el mismo dato repetido.')

    # BATIDO: dispersión entre muestras CONSECUTIVAS. No es el PWM.
    saltos = [abs(claro[i + 1] - claro[i]) for i in range(len(claro) - 1)]
    if saltos:
        print(f'  salto entre muestras consecutivas: mediana {statistics.median(saltos):.0f}, '
              f'máx {max(saltos)}')
        print('  📝 esto NO mide el PWM de la baldosa (va a cientos o miles de Hz y aquí se')
        print(f'     muestrea a {ritmo:.1f} Hz). Un salto grande sobre un color estable es BATIDO.')

    # 🔴 LA LÍNEA BASE NO ES CERO, Y ESTO ES LO QUE MÁS PUEDE ESTROPEAR LA GRÁFICA.
    #    Medido el 2026-08-12 sobre el suelo normal del laboratorio, con el LED del
    #    sensor APAGADO: claro ≈ 99, no 1-4. Eso es LUZ AMBIENTE reflejada, y se
    #    SUMA a lo que emita la baldosa. Sin restarla, los colores salen lavados
    #    hacia el color de la iluminación de la sala.
    if max(claro) <= 5:
        print('  🔴 con el LED apagado no llegó NADA (claro ≤ 5, el ruido de este robot):')
        print('     o el piso está apagado, o el robot no está encima, o no lo ve.')
    else:
        print(f'  📌 LÍNEA BASE: mide OTRA tanda con la baldosa APAGADA, misma posición y')
        print(f'     misma luz de sala, y RÉSTALA. El suelo del laboratorio dio claro ≈ 99')
        print(f'     con el LED del sensor apagado: eso es ambiente, no emisión.')
else:
    print('  sin datos que resumir')
print('=' * 76)

n.destroy_node()
rclpy.shutdown()
