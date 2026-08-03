#!/usr/bin/env python3
"""SIMULACIÓN del sobregiro de girar() — tabla comparativa 10 Hz vs 20 Hz.

🔴 ESTO NO ES UNA MEDICIÓN. Se llamaba `medir_sobregiro.py` y se titulaba
   «MEDICIÓN DE SOBREGIRO», y ni una sola de sus cifras sale de un robot: son
   la integración de un modelo. En este proyecto la palabra «medido» está
   reservada a lo que se ha tomado con cinta, transportador o instrumento, y
   confundir las dos cosas es exactamente la deriva que aquí se persigue.
   Renombrado a `simular_sobregiro.py` por eso.

Usa generador_rampa_real() de simular_girar.py — la MISMA función que usa
la tabla de consola de `python3 simular_girar.py` — así que las dos
herramientas comparten una única fuente de física y no pueden dar cifras
distintas sin que sea un cambio real en simular_girar.py.

⚠️ Lo que el modelo NO tiene: inercia. Integra la velocidad comandada al
   instante. La deceleración angular del RVR NO LA HA MEDIDO NADIE, así que
   estas cifras son el sobregiro del LAZO, no el del robot.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))

from simular_girar import generador_rampa_real, simular_girar

print("═" * 70)
print("SIMULACIÓN DE SOBREGIRO — rampa real de velocidad_giro(), SIN robot")
print("🔴 Ninguna cifra de aquí abajo está medida: son un modelo integrado.")
print("═" * 70)

# Caso 1: A 10 Hz con rampa realista
print("\n[10 Hz]")
for grados_pedidos in [90, 180, 360, 720]:
    resultado, iters, razon = simular_girar(grados_pedidos, generador_rampa_real(), freq_hz=10.0)
    sobregiro = resultado - grados_pedidos
    print(f"  {grados_pedidos:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

# Caso 2: A 20 Hz
print("\n[20 Hz]")
for grados_pedidos in [90, 180, 360, 720]:
    resultado, iters, razon = simular_girar(grados_pedidos, generador_rampa_real(), freq_hz=20.0)
    sobregiro = resultado - grados_pedidos
    print(f"  {grados_pedidos:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

print("\n" + "═" * 70)
print("COMPARACIÓN: 10 Hz vs 20 Hz")
print("═" * 70)
print("\nGrados  | 10 Hz (s)   | 20 Hz (s)   | Sobregiro 10Hz | Sobregiro 20Hz | Mejora")
print("--------|-------------|-------------|-----------------|-----------------|--------")

for grados_pedidos in [90, 180, 360, 720]:
    r10, iters10, _ = simular_girar(grados_pedidos, generador_rampa_real(), freq_hz=10.0)
    sg10 = r10 - grados_pedidos

    r20, iters20, _ = simular_girar(grados_pedidos, generador_rampa_real(), freq_hz=20.0)
    sg20 = r20 - grados_pedidos

    tiempo_10 = iters10 * (1.0 / 10.0)
    tiempo_20 = iters20 * (1.0 / 20.0)
    mejora = sg10 - sg20

    print(f"  {grados_pedidos:3d}° |   {tiempo_10:6.3f}   |   {tiempo_20:6.3f}   |  "
          f"{sg10:+6.3f}°       |  {sg20:+6.3f}°       | {mejora:+.3f}°")

print("\n" + "═" * 70)
print("QUÉ COMPRA SUBIR A 20 Hz, SIN ADORNOS")
print("═" * 70)
print("""
  90°  -> NADA. 10 Hz y 20 Hz dan el MISMO resultado (90.5273).
          🔴 Y 90° es el ángulo de las prácticas 2, 3, 4 y 10: el único que
             el curso usa de verdad.
  180°, 360°, 720° -> 0.573° menos de sobregiro, que es exactamente un paso
          de la rampa lenta (0.20 rad/s x 0.05 s).

  🔴 PERO NO LEAS ESTAS CUATRO FILAS COMO UNA TENDENCIA. Barrido de 1 a 720°:
     la ventaja solo toma DOS valores, 0 o 0.573 — nunca otra cosa — y empata
     en la mitad de los ángulos de todos los rangos por igual:

         1-90°    52 % de empates      181-360°  50 %
        91-180°   48 % de empates      361-720°  51 %

     Es ALIASING de retícula: un paso de 10 Hz vale exactamente dos de 20, así
     que lo que se decide es la paridad del último tramo, no una tendencia con
     el ángulo. Sobre 720°, 0.573 es el 0.08 %. Estas cuatro filas son cuatro
     muestras de una moneda, no una curva.

  📝 Una versión anterior de esta tabla reportaba +0.573° de ventaja TAMBIÉN a
     90°. Era un ARTEFACTO: `simular_girar()` seguía integrando 0.20 rad/s
     después de la orden de parada, y ese paso de más vale 0.20 x dt — o sea
     el doble a 10 Hz que a 20. Modelado el `parar()`, la ventaja a 90°
     desaparece. El test `test_a_90_grados_subir_a_20hz_NO_compra_nada` lo
     sujeta para que no vuelva.

  ⚠️ Y el techo real: /odom llega a 16.5 Hz. Por encima de eso quien fija el
     paso ya no es el bucle sino la odometría, así que subir la frecuencia de
     publicación más allá no compra resolución. Nada de esto está medido
     sobre el robot.
""")
print("═" * 70)
