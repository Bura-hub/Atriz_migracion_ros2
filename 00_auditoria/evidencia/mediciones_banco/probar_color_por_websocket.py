#!/usr/bin/env python3
"""Los DOS modos del sensor de color, por el camino de la WEB: rosbridge.

    python3 probar_color_por_websocket.py [host]

NO mueve el robot. Enciende y apaga el LED blanco del sensor.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE, Y NO ES UNA FORMALIDAD
═══════════════════════════════════════════════════════════════════════════════
La evidencia 86 midió los dos modos **por ROS**, con un cliente rclpy en el
propio robot. La web no habla ROS: habla **rosbridge por WebSocket**, y en este
proyecto ese camino tiene trampas propias, todas medidas:

  · `/start_scan` parecía tardar 4,6-6,5 s medido con `ros2 service call`, y por
    WebSocket son **1,4-2,1 s**. El instrumento era el que tardaba.
  · rosbridge comparte UNA suscripción ROS por topic entre todos los clientes,
    así que **el primero que se suscribe impone el QoS a los demás** — y uno que
    pida un QoS incompatible deja MUDOS a todos.
  · La lista blanca deniega **en silencio**: un servicio fuera de ella no da
    error, simplemente no contesta.

📌 Así que «funciona por ROS» no implica «funciona por la web». Esto lo cierra.

Reutiliza el cliente WebSocket propio de `probar_rosbridge.py` (sin librerías ni
CDN, a propósito: el robot no tiene que instalar nada para poder probarse).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probar_rosbridge import handshake, recibir, enviar        # noqa: E402
import socket                                                  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
PUERTO = 9090
N = 8


def llamar(sock, servicio, tipo, args, plazo=8.0):
    """Un `call_service` de rosbridge, midiendo lo que tarda de verdad."""
    ident = f'{servicio}-{time.time_ns()}'
    t0 = time.monotonic()
    enviar(sock, json.dumps({'op': 'call_service', 'service': servicio,
                             'type': tipo, 'args': args, 'id': ident}))
    while time.monotonic() - t0 < plazo:
        # 🔴 `recibir()` LANZA TimeoutError, no devuelve vacío. Con el plazo del
        #    socket largo, la primera espera se comía el plazo entero; con él
        #    corto y capturado, esto es un sondeo. Es la misma familia que el
        #    `spin_once` en bucle: el instrumento imponiendo su propio ritmo.
        try:
            r = recibir(sock)
        except (TimeoutError, socket.timeout):
            continue
        except Exception:                                      # noqa: BLE001
            break
        if r is None:
            break
        # 🔴 `recibir()` DEVUELVE UNA TUPLA `(datos, opcode)`, no una cadena. La
        #    primera versión de este fichero hacía `json.loads(r)` directamente:
        #    reventaba con CADA mensaje y su propio `except ... continue` los
        #    tiraba en silencio. Resultado: «/enable_color no contestó en 8 s»
        #    sobre un servicio que contestaba perfectamente, y a punto estuve de
        #    culpar a la lista blanca de rosbridge.
        #    📌 Lo destapó comparar contra `probar_rosbridge.py`, que ya estaba
        #       verificado. **Valida el instrumento antes de acusar a lo medido.**
        datos, op = r
        if op == 0x8:                       # el servidor cerró
            break
        if op != 0x1:                       # no es texto
            continue
        try:
            d = json.loads(datos)
        except Exception:                                      # noqa: BLE001
            continue
        if d.get('id') == ident and d.get('op') == 'service_response':
            return d, (time.monotonic() - t0) * 1000
    # 🔴 Silencio NO es error. La lista blanca de rosbridge deniega callando: un
    #    servicio fuera de ella se comporta EXACTAMENTE igual que uno que no
    #    existe. Se dice, en vez de devolver None y que parezca un timeout.
    return None, (time.monotonic() - t0) * 1000


def leer(sock, veces=N):
    lecturas, tiempos = [], []
    for _ in range(veces):
        d, ms = llamar(sock, '/get_rgbc_sensor_values',
                       'atriz_rvr_msgs/srv/GetRGBCSensorValues', {})
        tiempos.append(ms)
        if d is None:
            continue
        v = d.get('values', {})
        # 🔴 `result` es de ROSBRIDGE (¿pudo llamar?); `success` es del DRIVER
        #    (¿contestó el sensor?). Son dos capas distintas y hay que mirar las
        #    dos: el 2026-08-08 no mirar `success` estuvo a punto de costar un
        #    resultado correcto (evidencia 86, apartado 4c).
        lecturas.append({
            'rosbridge_ok': bool(d.get('result')),
            'driver_ok': bool(v.get('success')),
            'r': v.get('red_channel_value'), 'g': v.get('green_channel_value'),
            'b': v.get('blue_channel_value'), 'claro': v.get('clear_channel_value'),
            'mensaje': v.get('message', ''),
        })
        time.sleep(0.1)
    return lecturas, tiempos


def resumen(titulo, lecturas, tiempos):
    if not lecturas:
        print(f'  {titulo:22s}  🔴 CERO respuestas — ¿lista blanca? ¿rosbridge?')
        return
    malas = [x for x in lecturas if not x['rosbridge_ok'] or not x['driver_ok']]
    med = lambda k: sorted(x[k] for x in lecturas)[len(lecturas) // 2]   # noqa: E731
    r, g, b, c = med('r'), med('g'), med('b'), med('claro')
    print(f'  {titulo:22s}  R {r:5d}  G {g:5d}  B {b:5d}  claro {c:5d}'
          f'   · R/G {r/g if g else float("nan"):5.2f}  B/G {b/g if g else float("nan"):5.2f}')
    print(f'  {"":22s}  {len(lecturas)}/{N} respuestas · latencia mediana '
          f'{sorted(tiempos)[len(tiempos)//2]:.0f} ms · máx {max(tiempos):.0f} ms'
          + (f'  🔴 {len(malas)} con success/result falso' if malas else ''))
    if lecturas[-1]['mensaje']:
        print(f'  {"":22s}  driver dice: «{lecturas[-1]["mensaje"][:60]}…»')


print('=' * 78)
print(f' LOS DOS MODOS DEL SENSOR, POR ROSBRIDGE  ·  ws://{HOST}:{PUERTO}')
print('=' * 78)

sock = socket.create_connection((HOST, PUERTO), timeout=10)
sock.settimeout(0.4)          # sondeo, no espera bloqueante
handshake(sock, HOST)
print('  ✅ WebSocket abierto\n')

for encender, nombre in ((True, 'MODO REFLEJO (luz ON)'), (False, 'MODO EMISIÓN (luz OFF)')):
    d, ms = llamar(sock, '/enable_color', 'std_srvs/srv/SetBool', {'data': encender})
    if d is None:
        print(f'  🔴 /enable_color no contestó en {ms:.0f} ms — ¿está en la lista blanca?')
        break
    print(f'  /enable_color({str(encender).lower():5s})  result={d.get("result")}  '
          f'success={d.get("values", {}).get("success")}  ·  {ms:.0f} ms')
    time.sleep(1.5)                       # que el sensor se asiente
    resumen(nombre, *leer(sock))
    print()

print('-' * 78)
print('  📌 `result` es de ROSBRIDGE (¿pudo llamar?) y `success` del DRIVER')
print('     (¿contestó el sensor?). Son dos capas y hay que mirar las dos.')
print('  📌 La lista blanca deniega EN SILENCIO: cero respuestas y un servicio')
print('     inexistente se ven exactamente igual desde aquí.')
print('=' * 78)
sock.close()
