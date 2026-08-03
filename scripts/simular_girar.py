#!/usr/bin/env python3
"""Simulador del lazo de girar() — herramienta de banco para verificación.

Simula el comportamiento de girar() sin tocar el robot, usando funciones puras
importadas de atriz.py. Permite medir sobregiro y verificar el comportamiento
ante odometría congelada o con jitter.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))

from atriz import acumular, alcanzado, velocidad_giro


def simular_girar(grados_pedidos, yaw_generador, freq_hz=20.0):
    """Simula el lazo de girar() con odometría sintética.

    Args:
        grados_pedidos: ángulo a girar en grados
        yaw_generador: función que devuelve yaw en radianes dado (iteración, restante_grados, dt)
                       IMPORTANTE: dt es 1/freq_hz y DEBE usarse para integrar correctamente
        freq_hz: frecuencia de publicación del lazo simulado

    Returns:
        (grados_acumulados, num_iteraciones, razon_termino)
        razon_termino puede ser: 'convergencia', 'timeout', 'odom_congelado',
                                  'objetivo_minimo', 'max_iteraciones'
    """
    import math

    objetivo = math.radians(grados_pedidos)
    if abs(objetivo) < math.radians(0.5):
        return 0.0, 0, 'objetivo_minimo'

    sentido = 1.0 if objetivo >= 0.0 else -1.0
    dt = 1.0 / freq_hz
    anterior = yaw_generador(0, grados_pedidos, dt)
    acumulado = 0.0

    # Tope de tiempo (sin monotonic)
    limite = abs(objetivo) / 0.20 + 5.0
    tiempo_transcurrido = 0.0
    iteracion = 0
    ultimo_timestamp = None
    sin_cambio = 0
    MAX_SIN_CAMBIO = 5

    while not alcanzado(acumulado, objetivo):
        if tiempo_transcurrido > limite:
            return math.degrees(acumulado), iteracion, 'timeout'

        # Simular lectura de /odom — el generador RECIBE dt
        actual = yaw_generador(iteracion, math.degrees(objetivo - acumulado), dt)

        # Detectar si la muestra cambió (usar yaw redondeado como proxy de timestamp)
        timestamp_actual = (round(actual * 1000000),)
        if timestamp_actual == ultimo_timestamp:
            sin_cambio += 1
            if sin_cambio >= MAX_SIN_CAMBIO:
                return math.degrees(acumulado), iteracion, 'odom_congelado'
        else:
            sin_cambio = 0
            ultimo_timestamp = timestamp_actual

        acumulado = acumular(anterior, actual, acumulado)
        anterior = actual

        # Simular el sleep del lazo
        tiempo_transcurrido += dt
        iteracion += 1

        if iteracion > 10000:
            return math.degrees(acumulado), iteracion, 'max_iteraciones'

    # Simular el sleep final y re-medida
    tiempo_transcurrido += 0.5
    actual_final = yaw_generador(iteracion, 0.0, dt)
    acumulado = acumular(anterior, actual_final, acumulado)

    return math.degrees(acumulado), iteracion, 'convergencia'


if __name__ == '__main__':
    import math

    print("═" * 70)
    print("SIMULADOR DE girar() — Verificación de sobregiro")
    print("═" * 70)

    # Generadores de yaw para diferentes escenarios

    def yaw_ideal(iteracion, restante_grados, dt):
        """Robot que gira a velocidad ideal según la rampa.

        IMPORTANTE: dt es 1/freq_hz y DEBE usarlo para integrar correctamente.
        """
        if iteracion == 0:
            return 0.0
        # Integrar correctamente: yaw = iteracion * dt * velocidad_angular
        # Simplificado: velocidad promedio ~0.5 rad/s
        return iteracion * dt * 0.5

    def yaw_congelado_en_45(iteracion, restante_grados, dt):
        """/odom se congela a los 45.8°."""
        if iteracion >= 50:
            return math.radians(45.8)
        # Integra correctamente según dt
        return iteracion * dt * 0.5

    def yaw_con_duplicados_ocasionales(iteracion, restante_grados, dt):
        """/odom se repite ocasionalmente (normal a 10 vs 16.5 Hz)."""
        if iteracion % 3 == 0:  # cada 3 iteraciones, se repite la anterior
            return (iteracion - 1) * dt * 0.5
        # Integra correctamente según dt
        return iteracion * dt * 0.5

    # Prueba 1: Sobregiro a 10 Hz
    print("\n[10 Hz]")
    for grados in [90, 180, 360, 720]:
        resultado, iters, razon = simular_girar(grados, yaw_ideal, freq_hz=10.0)
        sobregiro = resultado - grados
        print(f"  {grados:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

    # Prueba 2: Sobregiro a 20 Hz
    print("\n[20 Hz]")
    for grados in [90, 180, 360, 720]:
        resultado, iters, razon = simular_girar(grados, yaw_ideal, freq_hz=20.0)
        sobregiro = resultado - grados
        print(f"  {grados:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

    # Prueba 3: /odom congelado
    print("\n[/odom congelado]")
    resultado, iters, razon = simular_girar(90, yaw_congelado_en_45, freq_hz=20.0)
    print(f"  90° con /odom congelado → {resultado:.3f}° ({razon})")

    # Prueba 4: Duplicados ocasionales
    print("\n[Duplicados ocasionales]")
    resultado, iters, razon = simular_girar(90, yaw_con_duplicados_ocasionales, freq_hz=20.0)
    sobregiro = resultado - 90
    print(f"  90° con duplicados → {resultado:.3f}° ({razon})")

    print("\n" + "═" * 70)
