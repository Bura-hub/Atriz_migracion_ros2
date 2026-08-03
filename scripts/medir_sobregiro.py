#!/usr/bin/env python3
"""Medición del sobregiro en girar() - tabla comparativa 10 Hz vs 20 Hz.

Usa generador_rampa_real() de simular_girar.py — la MISMA función que usa
la tabla de consola de `python3 simular_girar.py` — así que las dos
herramientas comparten una única fuente de física y no pueden dar cifras
distintas sin que sea un cambio real en simular_girar.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))

from simular_girar import generador_rampa_real, simular_girar

print("═" * 70)
print("MEDICIÓN DE SOBREGIRO — rampa REAL (misma física que simular_girar.py)")
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
print("\nNOTA IMPORTANTE: Este modelo usa velocidad_giro() REAL del código.")
print("A 20 Hz: /odom llega cada ~60 ms; el bucle pide cada 50 ms.")
print("El cuello de botella ES /odom (16.5 Hz), no el bucle.")
print("Por eso el beneficio de 20 Hz es limitado: el paso máximo lo fija /odom.")
print("═" * 70)
