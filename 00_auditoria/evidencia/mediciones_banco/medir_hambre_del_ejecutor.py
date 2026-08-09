#!/usr/bin/env python3
"""¿Deja `/scan` sin atender a `/odom` DENTRO del proceso del alumno?

    python3 medir_hambre_del_ejecutor.py [segundos_por_fase]

NO mueve el robot. Enciende y apaga el barrido del LIDAR.

═══════════════════════════════════════════════════════════════════════════════
LA PREGUNTA, Y POR QUÉ NO LA RESPONDE `medir_ritmo_ros2.py`
═══════════════════════════════════════════════════════════════════════════════
El 2026-08-08 `girar()` abortó a los 5,5° de 90 pedidos, con el guardia viejo que
se rendía tras **5 vueltas del bucle viendo el mismo sello** — o sea ~250 ms sin
muestra nueva. Reproducido 1 de 4, y el disparador **no se aisló**.

🔴 Lo que se descartó midiendo: que `/odom` tuviera huecos reales (78-81 ms de
   peor caso en régimen permanente, n=3), que los sellos vinieran a cero o
   repetidos (166 de 166 distintos), y el arranque del LIDAR (en el fallo ya
   estaba girando).

📌 **Pero todo eso se midió DESDE OTRO PROCESO.** Un topic puede estar
   perfectamente sano en el cable y llegar tarde a un proceso concreto. Y
   `atriz.py` tiene la forma exacta que produce eso:

     · un `SingleThreadedExecutor` en un HILO DEMONIO
     · con TRES suscripciones: `/odom` (16,5 Hz), `/battery_state` (0,03 Hz)
       y **`/scan` (12 Hz, ~250 rangos por mensaje)**
     · y el barrido lo ENCIENDE ELLA al conectar, así que `/scan` fluye durante
       todas las prácticas — incluidas las que no lo usan, como `girar()`

   Un ejecutor de un solo hilo atiende las devoluciones **en serie**. Si
   deserializar un `/scan` cuesta, los `/odom` esperan detrás.

Este banco mide el hueco **como lo ve el proceso del alumno**, con y sin `/scan`,
usando el MISMO objeto `Robot` que usan las prácticas.

⚠️ Toca `robot._odom` y `robot._nodo`, que son privados. Es deliberado: lo que se
   mide es precisamente el camino interno, y falsearlo con una copia sería medir
   otra cosa.
"""
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.expanduser(
    '~/atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
from atriz import Robot                                          # noqa: E402

SEG = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
# 🔴 MODO ARRANQUE. El fallo original ocurrió a los 5,5° de giro, o sea ~0,25 s
#    despues de empezar -- y `girar()` empieza justo despues de conectar. En
#    regimen permanente la racha NUNCA pasa de 1 (medido), asi que llegar a 5
#    exige un paron de ~300 ms: eso no es jitter, es una anomalia. Este modo mira
#    SOLO la ventana donde ocurrio, y con un proceso NUEVO cada vez, que es lo
#    que hace el alumno al lanzar una practica.
ARRANQUE = '--arranque' in sys.argv
# 🔴🔴 MODO GIRANDO, y es el que faltaba. Las dos tandas anteriores midieron el
#    proceso OBSERVANDO, y el fallo ocurrio con el robot MOVIENDOSE. `girar()`
#    publica `cmd_vel_raw` a 20 Hz, y el driver manda esas ordenes por **el mismo
#    puerto serie** que trae la telemetria: el RVR habla por un solo UART. Una
#    colision ahi retrasaria las muestras de /odom sin que el topic se vea mal
#    desde otro proceso -- que es exactamente la firma del fallo.
#    ⚠️ MUEVE EL ROBOT: gira sobre su eje.
GIRANDO = '--girando' in sys.argv


def barrido(encender):
    subprocess.run(['/usr/local/bin/atriz-escaneo', 'on' if encender else 'off'],
                   capture_output=True, timeout=30)
    time.sleep(2.0)


def observar(robot, seg, etiqueta):
    """Huecos entre sellos NUEVOS de /odom, vistos desde este proceso.

    🔴 Se sondea a 20 Hz A PROPÓSITO: es el ritmo del bucle de `girar()`. Medir a
       500 Hz daría la latencia real del ejecutor, pero no lo que el guardia ve,
       que es lo que hizo abortar el giro.
    """
    ultimo = None
    t_ultimo = time.monotonic()
    huecos, seguidas, peor_seguidas = [], 0, 0
    t0 = time.monotonic()
    n_scan_0 = getattr(robot, '_scan', None)
    scans = 0
    while time.monotonic() - t0 < seg:
        if GIRANDO:
            # Lo mismo que hace el bucle de `girar()`: una orden por vuelta.
            robot.mover(0.0, 0.5)
        time.sleep(0.05)                       # el mismo 20 Hz que girar()
        m = getattr(robot, '_odom', None)
        s = getattr(robot, '_scan', None)
        if s is not None and s is not n_scan_0:
            scans += 1
            n_scan_0 = s
        if m is None:
            continue
        sello = (m.header.stamp.sec, m.header.stamp.nanosec)
        if sello == ultimo:
            seguidas += 1
            peor_seguidas = max(peor_seguidas, seguidas)
        else:
            ahora = time.monotonic()
            if ultimo is not None:
                huecos.append((ahora - t_ultimo) * 1000)
            ultimo, t_ultimo, seguidas = sello, ahora, 0
    if not huecos:
        print(f'  {etiqueta:26s} 🔴 sin muestras de /odom')
        return None
    hs = sorted(huecos)
    p95 = hs[int(len(hs) * 0.95)]
    print(f'  {etiqueta:26s} n={len(hs):4d}  mediana {statistics.median(hs):5.1f} ms'
          f'  p95 {p95:6.1f}  PEOR {max(hs):6.1f} ms')
    print(f'  {"":26s} vueltas seguidas sin sello nuevo: PEOR {peor_seguidas}'
          f'   (el guardia viejo abortaba a las 5)'
          f'   · /scan vistos: {scans}')
    return {'peor': max(hs), 'peor_seguidas': peor_seguidas, 'p95': p95}


if ARRANQUE:
    # Sin cabecera ni fases: una linea por ejecucion, para encadenar muchas.
    t_con = time.monotonic()
    with Robot() as robot:
        listo = time.monotonic() - t_con
        r = observar(robot, SEG,
                     f'{"GIRANDO" if GIRANDO else "quieto"} (+{listo:.1f}s conect.)')
        if GIRANDO:
            robot.parar()
    raise SystemExit(0 if (r and r['peor_seguidas'] < 5) else 1)

print('=' * 78)
print(f' ¿ESTORBA /scan A /odom DENTRO DEL PROCESO DEL ALUMNO?  ·  {SEG:.0f} s por fase')
print('=' * 78)
print('  ⚠️ enciende y apaga el barrido del LIDAR. NO mueve el robot.\n')

with Robot() as robot:
    time.sleep(3.0)

    barrido(True)
    con = observar(robot, SEG, 'CON /scan (12 Hz)')
    print()
    barrido(False)
    sin = observar(robot, SEG, 'SIN /scan')

    print('-' * 78)
    if con and sin:
        print(f'  peor hueco     con {con["peor"]:6.1f} ms   ·   sin {sin["peor"]:6.1f} ms')
        print(f'  p95            con {con["p95"]:6.1f} ms   ·   sin {sin["p95"]:6.1f} ms')
        print(f'  peor racha     con {con["peor_seguidas"]:3d} vueltas ·   sin {sin["peor_seguidas"]:3d}')
        print()
        if con['peor_seguidas'] >= 5:
            print('  🔴 CON /scan se alcanzan 5 vueltas seguidas: es EXACTAMENTE el umbral')
            print('     del guardia viejo. El disparador queda identificado.')
        elif con['peor'] > 2 * max(sin['peor'], 1):
            print('  ⚠️ /scan empeora el peor caso claramente, pero no llegó a las 5')
            print('     vueltas en esta tanda. Es intermitente: repite.')
        else:
            print('  📌 En esta tanda /scan NO estorba de forma medible. NO cierra nada:')
            print('     el fallo original fue 1 de 4. Hace falta repetir.')
print('=' * 78)
