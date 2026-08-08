#!/usr/bin/env python3
"""¿Puede el RGBC medir una superficie que EMITE luz (pantalla, baldosa LED)?

    python3 medir_superficie_emisora.py <etiqueta>

NO mueve el robot. Enciende y apaga el LED blanco del sensor.

La pregunta: con el LED del sensor ENCENDIDO se mide el reflejo del propio LED
—y sobre vidrio eso es especular y blanco, o sea que tapa el color de la
pantalla—. Con el LED APAGADO, lo único que puede llegar al fotodiodo es lo que
la superficie EMITE.

Se toman las dos, en la misma posición y seguidas, porque una sola no distingue
«no funciona» de «lo tapa mi linterna».
"""
import statistics
import sys
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from atriz_rvr_msgs.srv import GetRGBCSensorValues

ETIQUETA = sys.argv[1] if len(sys.argv) > 1 else 'sin etiqueta'
N = 12

rclpy.init()
n = Node('medir_pantalla')
cli_led = n.create_client(SetBool, '/enable_color')
cli_rgbc = n.create_client(GetRGBCSensorValues, '/get_rgbc_sensor_values')
for c, nom in ((cli_led, '/enable_color'), (cli_rgbc, '/get_rgbc_sensor_values')):
    if not c.wait_for_service(timeout_sec=15):
        print(f'  🔴 {nom} no responde')
        raise SystemExit(1)


def llamar(cli, req, seg=15.0):
    f = cli.call_async(req)
    rclpy.spin_until_future_complete(n, f, timeout_sec=seg)
    return f.result()


def led(encendido):
    r = llamar(cli_led, SetBool.Request(data=encendido))
    time.sleep(1.5)                      # que el sensor se asiente
    return r is not None and r.success


def tanda():
    m = []
    for _ in range(N):
        r = llamar(cli_rgbc, GetRGBCSensorValues.Request())
        if r is not None and r.success:
            m.append((r.red_channel_value, r.green_channel_value,
                      r.blue_channel_value, r.clear_channel_value))
        time.sleep(0.12)
    return m


def resumen(titulo, m):
    if not m:
        print(f'  {titulo:22s}  🔴 sin lecturas')
        return None
    med = [statistics.median(x[i] for x in m) for i in range(4)]
    disp = [max(x[i] for x in m) - min(x[i] for x in m) for i in range(4)]
    r, g, b, c = med
    print(f'  {titulo:22s}  R {r:6.0f}  G {g:6.0f}  B {b:6.0f}  claro {c:6.0f}'
          f'   · dispersión claro {disp[3]:.0f}')
    if g > 0:
        print(f'  {"":22s}  R/G {r/g:5.2f}   B/G {b/g:5.2f}')
    return med


print('=' * 76)
print(f' RGBC sobre una superficie que EMITE luz  ·  {ETIQUETA}')
print('=' * 76)

print('  ⚠️ enciendo el LED blanco del sensor…')
led(True)
con = resumen('LED del sensor ON', tanda())

print('  ⚠️ apago el LED del sensor…')
led(False)
sin = resumen('LED del sensor OFF', tanda())

print('-' * 76)
if con and sin:
    print(f'  el LED del sensor aporta  {con[3] - sin[3]:+.0f} de claro'
          f'   ({con[3] / max(sin[3], 1):.0f}× )')
    if sin[3] <= 5:
        print('  🔴 con el LED apagado no llega NADA: o la pantalla no está debajo,')
        print('     o está apagada, o el sensor no la ve.')
    else:
        print(f'  ✅ con el LED apagado el sensor SÍ ve algo: claro {sin[3]:.0f}')
        print('     (el suelo de ruido medido en este robot es 1-4)')
print('=' * 76)

n.destroy_node()
rclpy.shutdown()
