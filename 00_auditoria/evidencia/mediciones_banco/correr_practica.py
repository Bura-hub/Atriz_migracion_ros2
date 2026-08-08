#!/usr/bin/env python3
"""Corre una práctica de alumno y mide SI EL ROBOT SE MOVIÓ.

    python3 correr_practica.py 01_avanzar.py [--esperado-cm 60] [--entrada "\\n\\n"]

🔴 MUEVE EL ROBOT (lo que mueva la práctica).

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════
Las diez prácticas nunca se habían ejecutado **con el robot moviéndose**. Al
correr la primera, el guion imprimió:

    Avanzando...
    Listo.

y salió con código 0. **Eso no dice nada.** Este proyecto tiene documentado el
caso exacto en el que un programa recorre su camino feliz sobre un robot que no
se mueve: la lista blanca de rosbridge dejando `raw_motors` al 30 % en **0,00 cm**
(evidencia 53), y `undercarriage_white` devolviendo `success=True` sin encender
nada. **Comprueba el efecto, no el código de salida.**

Así que aquí se lee `/odom` antes y después, y se informa del desplazamiento y
del giro. La práctica se ejecuta tal cual, sin tocarla: lo que se mide es lo que
el alumno va a ejecutar.

⚠️ **La odometría es el instrumento, y está validada contra cinta** n=5 en este
   robot (1,5 · 4,2 · 2,2 cm de error de posición, y 3,3 cm de deriva acumulada
   en un ciclo completo). No es circular como `pos_mapa()`: no la produce el
   mismo componente que decide si la práctica terminó bien.

📌 **Y no sustituye al ojo de quien mira el robot.** Un desplazamiento correcto
   con el robot arrastrándose de lado también da un número bonito.
"""
import argparse
import math
import os
import subprocess
import sys
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from nav_msgs.msg import Odometry

DIR_PRACTICAS = os.path.expanduser(
    '~/atriz_ws/src/Atriz_rvr/scripts/estudiantes')
QT = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)


def yaw_de(q):
    return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y),
                                   1 - 2 * (q.y ** 2 + q.z ** 2)))


p = argparse.ArgumentParser()
p.add_argument('practica')
p.add_argument('--esperado-cm', type=float, default=None,
               help='desplazamiento esperado; solo informa, no juzga')
p.add_argument('--entrada', default=None,
               help='texto que se manda a stdin (para las que piden input())')
p.add_argument('--plazo', type=float, default=180.0)
# 🔴 MI PROPIO FALSO POSITIVO, 2026-08-08. La práctica 5 lee el sensor de color
#    en bucle y NO MUEVE EL ROBOT — es lo correcto para lo que enseña. El arnés
#    imprimió «🔴 EL ROBOT NO SE MOVIÓ» sobre un guion que funcionaba
#    perfectamente. Un instrumento que grita sobre lo normal se acaba ignorando,
#    que es lo que este proyecto lleva escrito nueve veces del verificador.
p.add_argument('--no-mueve', action='store_true',
               help='esta práctica NO debe mover el robot; se invierte la comprobación')
p.add_argument('--en-bucle', action='store_true',
               help='no termina sola (lee sensores hasta Ctrl-C): agotar el plazo es lo ESPERADO')
a = p.parse_args()

ruta = a.practica if os.path.isabs(a.practica) else os.path.join(
    DIR_PRACTICAS, a.practica)
if not os.path.isfile(ruta):
    print(f'🔴 no existe: {ruta}')
    raise SystemExit(2)

rclpy.init()
n = Node('correr_practica')
pose = {}
n.create_subscription(Odometry, '/odom', lambda m: pose.update(
    x=m.pose.pose.position.x, y=m.pose.pose.position.y,
    yaw=yaw_de(m.pose.pose.orientation), t=time.monotonic()), QT)
ex = SingleThreadedExecutor()
ex.add_node(n)


def bombear(seg):
    """🔴 `timeout_sec=0.0` y ejecutor persistente. Con 0.1 el bucle gira ~10
    veces por segundo y el conteo queda capado por el BUCLE, no por el robot:
    15,0 Hz medidos sobre un robot a 16,5. Trampa documentada en CLAUDE.md."""
    t = time.monotonic()
    while time.monotonic() - t < seg:
        ex.spin_once(timeout_sec=0.0)
        time.sleep(0.002)


print('=' * 74)
print(f' {os.path.basename(ruta)}')
print('=' * 74)

bombear(3)
if not pose:
    print('  🔴 no llega /odom. ¿Está corriendo atriz-robot?')
    raise SystemExit(1)
antes = dict(pose)
print(f'  odom antes   ({antes["x"]:+.3f}, {antes["y"]:+.3f})  yaw {antes["yaw"]:+.1f}°')
print('  🔴 LA PRÁCTICA ARRANCA — EL ROBOT PUEDE MOVERSE\n')

t0 = time.monotonic()
proc = subprocess.Popen([sys.executable, '-u', ruta], cwd=os.path.dirname(ruta),
                        stdin=subprocess.PIPE if a.entrada is not None else None,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True)
if a.entrada is not None:
    try:
        proc.stdin.write(a.entrada.replace('\\n', '\n'))
        proc.stdin.flush()
    except Exception:                                            # noqa: BLE001
        pass

# Se gira el ejecutor MIENTRAS corre la práctica: si no, el búfer de /odom se
# queda rancio y la lectura de después sería la de antes con otra marca de
# tiempo. Es la misma trampa que dio 0,072 m donde había 0,643.
salida = []
while proc.poll() is None and time.monotonic() - t0 < a.plazo:
    ex.spin_once(timeout_sec=0.0)
    time.sleep(0.01)
AGOTO = proc.poll() is None
if AGOTO:
    proc.kill()
    print(f'  {"·" if a.en_bucle else "🔴"} la práctica llegó a {a.plazo:.0f} s y se paró'
          f'{" (esperado: no termina sola)" if a.en_bucle else ": matada"}')
salida.append(proc.stdout.read() or '')
codigo = proc.wait()
dur = time.monotonic() - t0

bombear(2)
d = dict(pose)
dx, dy = d['x'] - antes['x'], d['y'] - antes['y']
dist = math.hypot(dx, dy) * 100
dyaw = (d['yaw'] - antes['yaw'] + 180) % 360 - 180

print(''.join(salida).rstrip())
print()
print('-' * 74)
print(f'  odom después ({d["x"]:+.3f}, {d["y"]:+.3f})  yaw {d["yaw"]:+.1f}°')
print(f'  DESPLAZAMIENTO {dist:6.1f} cm   ·   GIRO NETO {dyaw:+7.1f}°'
      f'   ·   {dur:.1f} s   ·   salida {codigo}')
if a.esperado_cm is not None:
    print(f'  esperado ~{a.esperado_cm:.0f} cm  ->  diferencia {dist - a.esperado_cm:+.1f} cm')
# 🔴 El caso que este arnés existe para cazar — y su contrario, que también
#    importa: una práctica de sensores que mueva el robot es un fallo distinto y
#    igual de invisible.
QUIETO = dist < 1.0 and abs(dyaw) < 2.0
if a.no_mueve:
    if QUIETO:
        print('  ✅ el robot NO se movió, que es lo que esta práctica promete.')
    else:
        print('  🔴 ESTA PRÁCTICA NO DEBERÍA MOVER EL ROBOT, y lo movió.')
elif QUIETO:
    print('  🔴 EL ROBOT NO SE MOVIÓ. Código de salida 0 no es lo mismo que efecto.')
print('=' * 74)

n.destroy_node()
rclpy.shutdown()
# Una práctica en bucle la mata el plazo: su código de salida no significa nada.
raise SystemExit(0 if (a.en_bucle and AGOTO) else codigo)
