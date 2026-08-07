#!/usr/bin/env python3
"""Convierte TRES medidas de cinta en una posición, y dice quién miente.

    python3 comparar_con_cinta.py  AB  AP  BP  [--detras] \\
            --odom X Y  --amcl X Y

    AB   distancia entre las dos marcas del suelo      (p. ej. 1.00)
    AP   de la marca A (inicio) al centro final        (la diagonal de siempre)
    BP   de la marca B (lateral) al centro final       ← la que faltaba
    --detras   si el robot acabó DETRÁS de la línea A-B

Todo en METROS. El banco `probar_navegacion.py` imprime al terminar el comando
ya montado con `--odom` y `--amcl`: solo hay que añadirle las tres distancias.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ HACEN FALTA DOS DISTANCIAS Y NO UNA
═══════════════════════════════════════════════════════════════════════════════
🔴 **Una sola distancia NO determina una posición en un plano.** Medir solo la
   diagonal A→P deja al robot en cualquier punto de una circunferencia.

Y eso no es teórico: el 2026-08-07, con solo la diagonal, la odometría y AMCL
**coincidían** en la distancia (65,2 y 71,4 cm contra 66,0 de cinta) mientras
**discrepaban 45 cm en posición y 38° en rumbo**:

    odometría   acabó en (+0,542, −0,362)   →  36 cm desviado a un lado
    AMCL        acabó en (+0,712, +0,058)   →  casi sin desviarse

La cinta no podía distinguirlos. **La segunda distancia sí.**

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE MARCA, ANTES DE ARRANCAR
═══════════════════════════════════════════════════════════════════════════════
  A   cinta adhesiva bajo el CENTRO del robot
  B   otra marca a ~1 m de A, a la IZQUIERDA del robot (perpendicular a como
      mira). ⚠️ El ángulo NO tiene que ser exacto: lo que hay que medir bien es
      la distancia A→B, y se pasa como primer argumento.

📌 Se elige la izquierda por convenio, para que el signo de `y` coincida con el
   de ROS (regla de la mano derecha: +y a la izquierda del robot).
"""
import argparse
import math
import sys

p = argparse.ArgumentParser(add_help=True)
p.add_argument('AB', type=float)
p.add_argument('AP', type=float)
p.add_argument('BP', type=float)
p.add_argument('--detras', action='store_true',
               help='el robot acabó DETRÁS de la línea A-B')
p.add_argument('--odom', nargs=2, type=float, metavar=('X', 'Y'))
p.add_argument('--amcl', nargs=2, type=float, metavar=('X', 'Y'))
a = p.parse_args()

AB, AP, BP = a.AB, a.AP, a.BP

# ── Trilateración ────────────────────────────────────────────────────────────
# A en el origen; B a distancia AB sobre el eje +y (a la izquierda del robot).
# El robot mira hacia +x. Dos circunferencias, dos incógnitas:
#     x² + y²        = AP²
#     x² + (y − AB)² = BP²
# Restando desaparece x² y `y` sale directo.
y = (AP**2 - BP**2 + AB**2) / (2 * AB)
bajo = AP**2 - y**2
if bajo < 0:
    print('🔴 LAS TRES MEDIDAS NO FORMAN UN TRIÁNGULO.')
    print(f'   AP={AP:.3f}  BP={BP:.3f}  AB={AB:.3f}')
    print('   Alguna está mal tomada: revisa que A→B sea la que dices y que las')
    print('   tres se hayan medido al MISMO punto del robot (el centro).')
    sys.exit(1)
x = math.sqrt(bajo)
# 🔴 La trilateración desde DOS puntos tiene dos soluciones, espejo respecto a
#    la línea A-B. Aquí eso es «por delante» o «por detrás», y la cinta no lo
#    distingue: lo tiene que decir quien miró.
if a.detras:
    x = -x

dist = math.hypot(x, y)
rumbo = math.degrees(math.atan2(y, x))

print('=' * 72)
print(' POSICIÓN FINAL SEGÚN LA CINTA')
print('=' * 72)
print(f'   avance   x = {x:+.3f} m      (hacia donde miraba al empezar)')
print(f'   desvío   y = {y:+.3f} m      (+ izquierda, − derecha)')
print(f'   distancia    {dist * 100:.1f} cm       rumbo {rumbo:+.1f}°')

if a.odom or a.amcl:
    print()
    print('=' * 72)
    print(' QUIÉN SE ACERCA MÁS A LA CINTA')
    print('=' * 72)
    print(f'   {"fuente":10s} {"x":>8s} {"y":>8s} {"dist":>8s} {"rumbo":>8s}   error de POSICIÓN')
    print(f'   {"cinta":10s} {x:+8.3f} {y:+8.3f} {dist*100:7.1f}cm {rumbo:+7.1f}°   —')
    for nom, v in (('odometría', a.odom), ('AMCL', a.amcl)):
        if not v:
            continue
        e = math.hypot(v[0] - x, v[1] - y)
        print(f'   {nom:10s} {v[0]:+8.3f} {v[1]:+8.3f} '
              f'{math.hypot(*v)*100:7.1f}cm {math.degrees(math.atan2(v[1], v[0])):+7.1f}°'
              f'   {e*100:6.1f} cm')
    print()
    print('   🔴 La columna que decide es la ÚLTIMA: el error de POSICIÓN.')
    print('      Acertar la distancia y fallar el rumbo es acabar en otro sitio,')
    print('      y con una sola medida de cinta eso no se ve.')
print('=' * 72)
