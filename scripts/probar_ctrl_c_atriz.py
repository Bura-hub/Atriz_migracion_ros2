#!/usr/bin/env python3
"""¿Para el robot un Ctrl-C a mitad de un avance? — se mide el DESPLAZAMIENTO.

    python3 probar_ctrl_c_atriz.py

⚠️ MUEVE EL ROBOT. Necesita ~1.5 m despejado por delante (0.15 m/s × 10 s).
   ⚠️ El LIDAR barre a 15.5 cm del suelo: una caja baja no lo ve.

🔴 Por que se repite: `rclpy.init()` sin `SignalHandlerOptions.NO` invalida su
   propio contexto en el SIGINT, y el fallo es INTERMITENTE — segun donde caiga
   el Ctrl-C, a veces la parada si sale. Por eso la verificacion del 2026-08-01
   de otra herramienta paso con el fallo dentro. Una pasada no concluye.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
from atriz import Robot                                      # noqa: E402

print(__doc__)
print('Avanzando 10 s a 0.15 m/s. Pulsa Ctrl-C a los ~3 s y mide con cinta\n'
      'CUANTO RECORRE EL ROBOT DESPUES de que pulses.\n')
with Robot() as robot:
    input('Marca la posicion inicial y pulsa Enter...')
    robot.avanzar(0.15, 10)
    print('Llego al final sin Ctrl-C: repite y pulsalo antes.')
