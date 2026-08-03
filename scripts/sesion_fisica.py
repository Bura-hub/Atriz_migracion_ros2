#!/usr/bin/env python3
"""Guion de la SESIÓN FÍSICA — mide con el robot delante, sin `input()`.

    python3 sesion_fisica.py avanzar
    python3 sesion_fisica.py girar 90
    python3 sesion_fisica.py faros
    python3 sesion_fisica.py frontal
    python3 sesion_fisica.py ctrl_c

⚠️ MUEVE EL ROBOT en `avanzar`, `girar` y `ctrl_c`.

📝 **Por qué existe y no se usa la guía tal cual:** los pasos de la guía usan
   `input()` para dar tiempo a colocar el robot, y eso **no funciona** cuando el
   comando se lanza sin terminal interactiva (recibe EOF y aborta). Aquí se
   sustituye por una cuenta atrás, que sirve igual y funciona en los dos casos.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
from atriz import Robot                                      # noqa: E402


def cuenta_atras(segundos, que):
    print(f'\n>>> {que}')
    for queda in range(segundos, 0, -1):
        print(f'    arranco en {queda}...', flush=True)
        time.sleep(1)
    print('    ¡YA!\n', flush=True)


def avanzar(robot):
    """0.20 m/s durante 3 s. Espero 55-65 cm."""
    cuenta_atras(8, 'MARCA la posicion del robot. Necesita 1 m despejado.')
    robot.avanzar(0.20, 3)
    print('Hecho. MIDE con cinta lo que avanzo.')
    print('  esperado: 55-65 cm  ·  si mide ~6 cm es el watchdog cortando')


def girar(robot, grados):
    """Gira y devuelve lo que dice /odom. Compara con transportador."""
    cuenta_atras(8, f'MARCA el rumbo. Voy a pedir {grados} grados. '
                    f'Necesita 40 cm libres alrededor.')
    logrado = robot.girar(grados)
    print(f'Hecho. /odom dice {logrado:.2f} grados de los {grados} pedidos.')
    print('  MIDE con transportador y comparalo con ese numero.')


def faros(robot):
    """Enciende los faros en tres colores. Solo hay que MIRAR el robot."""
    print('\n>>> MIRA EL ROBOT. No se mueve; solo se encienden los faros.\n')
    for nombre, rgb in (('ROJO', (255, 0, 0)), ('VERDE', (0, 255, 0)),
                        ('AZUL', (0, 0, 255))):
        robot.luces(*rgb)
        print(f'    ahora deberia estar {nombre}', flush=True)
        time.sleep(3)
    robot.luces(0, 0, 0)
    print('    y ahora APAGADOS\n¿Viste los tres colores?')


def frontal(robot):
    """Lo que ve el LIDAR delante. Cierra si el angulo 0 apunta adelante."""
    print('\n>>> Pon algo plano JUSTO DELANTE del robot, a una distancia que '
          'puedas medir.')
    for queda in range(10, 0, -1):
        print(f'    leo en {queda}...', flush=True)
        time.sleep(1)
    d = robot.distancia_frontal()
    print(f'\n    el robot dice: {d:.3f} m')
    print('    MIDE tu la misma distancia con cinta, desde el centro del LIDAR.')
    print('    Si difieren mas de un par de cm, el angulo 0 no apunta adelante.')


def ctrl_c(robot):
    """Avanza 8 s; hay que pulsar Ctrl-C a mitad y medir lo que recorre despues.

    🔴 Repetir CINCO veces, pulsando a distintas alturas: el fallo que busca es
       INTERMITENTE, y una pasada verde no concluye nada.
    """
    cuenta_atras(8, 'MARCA la posicion. Necesita ~1.5 m despejado. '
                    'Pulsa Ctrl-C a mitad y mide lo que recorre DESPUES.')
    robot.avanzar(0.15, 8)
    print('Llegue al final sin Ctrl-C: repite y pulsalo antes.')


PASOS = {'avanzar': avanzar, 'girar': girar, 'faros': faros,
         'frontal': frontal, 'ctrl_c': ctrl_c}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in PASOS:
        sys.exit(f'uso: {sys.argv[0]} [{" | ".join(PASOS)}] [grados]')
    paso = sys.argv[1]
    with Robot() as robot:
        if paso == 'girar':
            PASOS[paso](robot, float(sys.argv[2]) if len(sys.argv) > 2 else 90)
        else:
            PASOS[paso](robot)
