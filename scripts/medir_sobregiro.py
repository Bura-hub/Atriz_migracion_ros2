#!/usr/bin/env python3
"""Medición del sobregiro en girar() - usando el simulador con rampa real.

Llama a simular_girar() con un generador que integra velocidad_giro() REAL.
Esto asegura que el modelo es correcto y reproducible.
"""

import sys
from pathlib import Path
import math

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))

from atriz import velocidad_giro
from simular_girar import simular_girar


def make_yaw_con_rampa_real(freq_hz):
    """Generador que integra velocidad_giro() REAL.

    Mantiene estado y respeta dt para integrar correctamente.
    """
    acumulado = 0.0

    def gen(iteracion, restante_grados, dt):
        nonlocal acumulado
        if iteracion == 0:
            return 0.0
        # Calcular velocidad según la rampa REAL
        objetivo_rad = math.radians(restante_grados)
        v_cmd = velocidad_giro(objetivo_rad)
        # Integrar: delta = velocidad * dt
        delta = v_cmd * dt
        acumulado += delta
        return acumulado

    return gen


print("═" * 70)
print("MEDICIÓN DE SOBREGIRO — Modelo con rampa REAL")
print("═" * 70)

# Caso 1: A 10 Hz con rampa realista
print("\n[MODELO REALISTA — 10 Hz]")
for grados_pedidos in [90, 180, 360, 720]:
    generador = make_yaw_con_rampa_real(10.0)
    resultado, iters, razon = simular_girar(grados_pedidos, generador, freq_hz=10.0)
    sobregiro = resultado - grados_pedidos
    print(f"  {grados_pedidos:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

# Caso 2: A 20 Hz
print("\n[MODELO REALISTA — 20 Hz]")
for grados_pedidos in [90, 180, 360, 720]:
    generador = make_yaw_con_rampa_real(20.0)
    resultado, iters, razon = simular_girar(grados_pedidos, generador, freq_hz=20.0)
    sobregiro = resultado - grados_pedidos
    print(f"  {grados_pedidos:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

print("\n" + "═" * 70)
print("COMPARACIÓN: 10 Hz vs 20 Hz")
print("═" * 70)
print("\nGrados  | 10 Hz (s)   | 20 Hz (s)   | Sobregiro mejora")
print("--------|-------------|-------------|------------------")

for grados_pedidos in [90, 180, 360, 720]:
    gen10 = make_yaw_con_rampa_real(10.0)
    r10, iters10, _ = simular_girar(grados_pedidos, gen10, freq_hz=10.0)
    sg10 = r10 - grados_pedidos

    gen20 = make_yaw_con_rampa_real(20.0)
    r20, iters20, _ = simular_girar(grados_pedidos, gen20, freq_hz=20.0)
    sg20 = r20 - grados_pedidos

    tiempo_10 = iters10 * (1.0 / 10.0)
    tiempo_20 = iters20 * (1.0 / 20.0)
    mejora = sg10 - sg20

    print(f"  {grados_pedidos:3d}° |   {tiempo_10:6.3f}   |   {tiempo_20:6.3f}   |  {mejora:+6.3f}°")

print("\n" + "═" * 70)
print("\nNOTA IMPORTANTE: Este modelo usa velocidad_giro() REAL del código.")
print("A 20 Hz: /odom llega cada ~60 ms; el bucle pide cada 50 ms.")
print("El cuello de botella ES /odom (16.5 Hz), no el bucle.")
print("Por eso el beneficio de 20 Hz es limitado: el paso máximo lo fija /odom.")
print("═" * 70)
