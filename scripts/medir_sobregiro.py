#!/usr/bin/env python3
"""Medición del sobregiro en girar() - modelo realista de la dinámica.

Integra correctamente la velocidad angular según la rampa de velocidad_giro()
y la frecuencia de publicación.
"""

import sys
from pathlib import Path
import math

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))

from atriz import acumular, alcanzado, normalizar, velocidad_giro, yaw_de_cuaternion
from simular_girar import simular_girar


def yaw_dinamico_real(dt, velocidad_angular_cmd):
    """Generador que simula integración real de velocidad angular.

    Mantiene estado entre llamadas.
    """
    acumulado = 0.0

    def generador(iteracion, restante_grados):
        nonlocal acumulado
        # Integrar: y(t) = y0 + ∫v(τ) dτ
        # Aquí v es el comando de velocidad_giro()
        acumulado += velocidad_angular_cmd * dt
        # Normalizar para que atan2 no nos engañe
        return normalizar(acumulado)

    return generador


print("═" * 70)
print("MEDICIÓN DE SOBREGIRO — Modelo de integración realista")
print("═" * 70)

# Caso 1: A 10 Hz con rampa realista
print("\n[MODELO REALISTA — 10 Hz]")
dt_10hz = 1.0 / 10.0

for grados_pedidos in [90, 180, 360, 720]:
    # Crear generador que integra velocidad angular
    objetivo_rad = math.radians(grados_pedidos)
    acumulado = 0.0
    dt = dt_10hz
    iteracion = 0

    anterior = 0.0

    # Simular el lazo
    while not alcanzado(acumulado, objetivo_rad):
        # Calcular velocidad según rampa
        restante = abs(objetivo_rad - acumulado)
        v_cmd = velocidad_giro(restante)  # rad/s

        # Integrar: delta_yaw = velocidad * dt
        delta_yaw = v_cmd * dt
        acumulado = acumular(anterior, anterior + delta_yaw, acumulado)
        anterior = anterior + delta_yaw

        iteracion += 1
        if iteracion > 10000:
            break

    resultado_grados = math.degrees(acumulado)
    sobregiro = resultado_grados - grados_pedidos
    print(f"  {grados_pedidos:3d}° → {resultado_grados:7.3f}° (sobregiro {sobregiro:+.3f}°)")

# Caso 2: A 20 Hz
print("\n[MODELO REALISTA — 20 Hz]")
dt_20hz = 1.0 / 20.0

for grados_pedidos in [90, 180, 360, 720]:
    objetivo_rad = math.radians(grados_pedidos)
    acumulado = 0.0
    dt = dt_20hz
    iteracion = 0

    anterior = 0.0

    # Simular el lazo
    while not alcanzado(acumulado, objetivo_rad):
        # Calcular velocidad según rampa
        restante = abs(objetivo_rad - acumulado)
        v_cmd = velocidad_giro(restante)  # rad/s

        # Integrar: delta_yaw = velocidad * dt
        delta_yaw = v_cmd * dt
        acumulado = acumular(anterior, anterior + delta_yaw, acumulado)
        anterior = anterior + delta_yaw

        iteracion += 1
        if iteracion > 10000:
            break

    resultado_grados = math.degrees(acumulado)
    sobregiro = resultado_grados - grados_pedidos
    print(f"  {grados_pedidos:3d}° → {resultado_grados:7.3f}° (sobregiro {sobregiro:+.3f}°)")

print("\n" + "═" * 70)
print("COMPARACIÓN: 10 Hz vs 20 Hz")
print("═" * 70)
print("\nGrados  | 10 Hz (ms)  | 20 Hz (ms)  | Diferencia")
print("--------|-------------|-------------|----------")

for grados_pedidos in [90, 180, 360, 720]:
    objetivo_rad = math.radians(grados_pedidos)

    # 10 Hz
    acumulado_10 = 0.0
    dt = 1.0 / 10.0
    anterior = 0.0
    iteracion = 0
    while not alcanzado(acumulado_10, objetivo_rad) and iteracion < 10000:
        restante = abs(objetivo_rad - acumulado_10)
        v_cmd = velocidad_giro(restante)
        delta_yaw = v_cmd * dt
        acumulado_10 = acumular(anterior, anterior + delta_yaw, acumulado_10)
        anterior = anterior + delta_yaw
        iteracion += 1
    tiempo_10 = iteracion * dt

    # 20 Hz
    acumulado_20 = 0.0
    dt = 1.0 / 20.0
    anterior = 0.0
    iteracion = 0
    while not alcanzado(acumulado_20, objetivo_rad) and iteracion < 10000:
        restante = abs(objetivo_rad - acumulado_20)
        v_cmd = velocidad_giro(restante)
        delta_yaw = v_cmd * dt
        acumulado_20 = acumular(anterior, anterior + delta_yaw, acumulado_20)
        anterior = anterior + delta_yaw
        iteracion += 1
    tiempo_20 = iteracion * dt

    diff = tiempo_10 - tiempo_20
    print(f"  {grados_pedidos:3d}° |   {tiempo_10:6.3f}   |   {tiempo_20:6.3f}   |  {diff:+6.3f}")

print("\n" + "═" * 70)
