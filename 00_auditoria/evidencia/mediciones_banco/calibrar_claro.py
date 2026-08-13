#!/usr/bin/env python3
"""Lee el canal `claro` con la luz del sensor ENCENDIDA (superficie que refleja).

    python3 calibrar_claro.py <etiqueta>

Enciende la luz, toma 15 muestras por servicio (~1 por s: el sensor refresca a
~21 Hz pero el dato útil va más lento), imprime mediana y rango, y APAGA la luz
— también si muere a mitad (finally).
"""
import statistics
import sys
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from atriz_rvr_msgs.srv import GetRGBCSensorValues

etiqueta = sys.argv[1] if len(sys.argv) > 1 else 'superficie'
rclpy.init()
n = Node('calibrar_claro')
luz = n.create_client(SetBool, '/enable_color')
rgbc = n.create_client(GetRGBCSensorValues, '/get_rgbc_sensor_values')
for cli, nombre in ((luz, '/enable_color'), (rgbc, '/get_rgbc_sensor_values')):
    if not cli.wait_for_service(timeout_sec=5.0):
        sys.exit(f'🔴 {nombre} no responde')


def llamar(cli, req):
    fut = cli.call_async(req)
    rclpy.spin_until_future_complete(n, fut, timeout_sec=5.0)
    return fut.result()


try:
    r = llamar(luz, SetBool.Request(data=True))
    print(f'luz encendida: success={getattr(r, "success", None)}')
    time.sleep(1.0)                      # que el sensor se asiente con la luz
    claros = []
    for _ in range(15):
        resp = llamar(rgbc, GetRGBCSensorValues.Request())
        if resp is not None and resp.success:
            claros.append(resp.clear_channel_value)
        time.sleep(0.3)
    if not claros:
        sys.exit('🔴 ninguna lectura válida')
    print(f'{etiqueta}: n={len(claros)} · claro mediana={statistics.median(claros):.0f} '
          f'· rango {min(claros)}–{max(claros)}')
finally:
    llamar(luz, SetBool.Request(data=False))
    print('luz apagada')
    n.destroy_node()
    rclpy.shutdown()
