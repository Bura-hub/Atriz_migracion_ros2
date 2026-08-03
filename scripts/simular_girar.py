#!/usr/bin/env python3
"""Simulador del lazo de girar() — herramienta de banco para verificación.

Simula el comportamiento de girar() sin tocar el robot, usando funciones puras
importadas de atriz.py. Permite medir sobregiro y verificar el comportamiento
ante odometría congelada o con jitter.
"""

import math
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
    objetivo = math.radians(grados_pedidos)
    if abs(objetivo) < math.radians(0.5):
        return 0.0, 0, 'objetivo_minimo'

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

    # 🔴 AQUI `girar()` LLAMA A `parar()`: la velocidad comandada pasa a CERO.
    #    Este simulador NO tiene modelo de inercia (integra la velocidad
    #    comandada al instante, sin deceleracion), asi que con velocidad cero el
    #    rumbo ya no cambia: la re-medida de despues del `sleep(0.5)` devuelve
    #    lo mismo que la ultima del lazo, y el acumulado se queda como esta.
    #    Por eso NO se vuelve a llamar al generador.
    #
    #    Antes si se le llamaba, con `restante_grados=0.0`. Y como
    #    `velocidad_giro(0)` vale 0.20 rad/s —nunca cero—, el generador seguia
    #    integrando 0.20 rad/s DESPUES de la orden de parada: 0.20 * dt de
    #    sobregiro inventado, proporcional a dt. Medido antes de este arreglo:
    #      a 10 Hz: +1.1459 grados     a 20 Hz: +0.5730 grados
    #    O sea que el simulador fabricaba una ventaja de 20 Hz de exactamente
    #    0.5730 grados que no venia del lazo, sino de su propio ultimo paso.
    #    A 90 grados esa era TODA la ventaja que reportaba.
    #
    # ⚠️ Lo que este simulador NO modela, y conviene tenerlo escrito: cuanto
    #    sigue rodando el robot de VERDAD tras la orden de parada. La
    #    deceleracion angular del RVR NO LA HA MEDIDO NADIE. Asi que estas
    #    cifras son el sobregiro del LAZO, no el del robot.
    tiempo_transcurrido += 0.5

    return math.degrees(acumulado), iteracion, 'convergencia'


def generador_rampa_real():
    """Fábrica de generador de yaw que integra `velocidad_giro()` REAL — la
    misma rampa que usa `Robot.girar()` en `atriz.py` — en vez de una
    velocidad inventada.

    🔴 Reproduce solo dos piezas del lazo real, verificadas con test:
    la MAGNITUD (integra `velocidad_giro()`, no una velocidad inventada) y
    el SIGNO (`sentido * velocidad_giro(...)`, igual que `girar()` real,
    porque `velocidad_giro()` usa `abs()` por dentro y nunca es negativa).
    Cualquier otra propiedad del lazo real que no tenga un test explícito
    NO está garantizada por este generador — no lo trates como el lazo
    completo.

    Es la ÚNICA función de este módulo que produce cifras de sobregiro. Tanto
    la tabla que imprime este script (`__main__`) como `simular_sobregiro.py`
    la importan de aquí: no hay una segunda copia de la física en ningún otro
    sitio, así que las dos herramientas no pueden divergir en silencio.

    Cada llamada recibe el `dt` que le pasa `simular_girar()` (no lo calcula
    por su cuenta), así que además sirve de canario: si `simular_girar()`
    tuviera el `dt` hardcodeado en vez de derivarlo de `freq_hz`, las
    trayectorias a 10 Hz y a 20 Hz saldrían IDÉNTICAS con este generador.
    Eso lo comprueban `test_generador_recibe_dt_correcto_segun_freq_hz` (que
    va directo al `dt`) y `test_a_partir_de_180_grados_20hz_si_reduce_el_sobregiro`
    (que lo pilla por la física, con desigualdad estricta).

    ⚠️ Ojo con el encuadre: que a 20 Hz salga MENOS sobregiro en algunos
    ángulos NO es una propiedad general. Barriendo 1..720° la diferencia solo
    vale 0 o 0.573°, con ~50 % de empates en todos los rangos — es aliasing de
    retícula, no una tendencia. Aquí se usa solo como canario del `dt`.

    Se instancia una vez por llamada a `simular_girar()` (lleva estado propio
    en `acumulado` y en `sentido`), nunca se reutiliza entre corridas.
    """
    acumulado = 0.0
    sentido = 1.0  # se fija en la primera llamada, igual que en girar()

    def generador(iteracion, restante_grados, dt):
        nonlocal acumulado, sentido
        if iteracion == 0:
            # En la llamada 0, simular_girar() pasa grados_pedidos tal cual
            # (el objetivo completo, no lo que queda), así que su signo es
            # el signo del giro pedido.
            sentido = 1.0 if restante_grados >= 0.0 else -1.0
            return 0.0
        v_cmd = velocidad_giro(math.radians(restante_grados))
        acumulado += sentido * v_cmd * dt
        return acumulado

    return generador


if __name__ == '__main__':
    print("═" * 70)
    print("SIMULADOR DE girar() — sobregiro con la rampa REAL de velocidad_giro()")
    print("═" * 70)

    # Prueba 1: Sobregiro a 10 Hz
    print("\n[10 Hz]")
    for grados in [90, 180, 360, 720]:
        resultado, iters, razon = simular_girar(grados, generador_rampa_real(), freq_hz=10.0)
        sobregiro = resultado - grados
        print(f"  {grados:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

    # Prueba 2: Sobregiro a 20 Hz
    print("\n[20 Hz]")
    for grados in [90, 180, 360, 720]:
        resultado, iters, razon = simular_girar(grados, generador_rampa_real(), freq_hz=20.0)
        sobregiro = resultado - grados
        print(f"  {grados:3d}° → {resultado:7.3f}° (sobregiro {sobregiro:+.3f}°)")

    # Las dos pruebas siguientes usan una velocidad CONSTANTE simplificada
    # (0.5 rad/s), a propósito: no miden sobregiro, solo comprueban que
    # simular_girar() detecta /odom congelado y tolera duplicados
    # ocasionales. Para el sobregiro en grados, la rampa real de arriba es la
    # que vale.
    def yaw_congelado_en_45(iteracion, restante_grados, dt):
        """/odom se congela a los 45.8°."""
        if iteracion >= 50:
            return math.radians(45.8)
        return iteracion * dt * 0.5

    def yaw_con_duplicados_ocasionales(iteracion, restante_grados, dt):
        """/odom se repite ocasionalmente (normal a 10 vs 16.5 Hz)."""
        if iteracion % 3 == 0:  # cada 3 iteraciones, se repite la anterior
            return (iteracion - 1) * dt * 0.5
        return iteracion * dt * 0.5

    # Prueba 3: /odom congelado
    print("\n[/odom congelado] (velocidad constante simplificada, no la rampa)")
    resultado, iters, razon = simular_girar(90, yaw_congelado_en_45, freq_hz=20.0)
    print(f"  90° con /odom congelado → {resultado:.3f}° ({razon})")

    # Prueba 4: Duplicados ocasionales
    print("\n[Duplicados ocasionales] (velocidad constante simplificada, no la rampa)")
    resultado, iters, razon = simular_girar(90, yaw_con_duplicados_ocasionales, freq_hz=20.0)
    print(f"  90° con duplicados → {resultado:.3f}° ({razon})")

    print("\n" + "═" * 70)
    print("LO QUE ESTAS CIFRAS NO DICEN")
    print("═" * 70)
    print("""
  ⚠️ Ninguna está MEDIDA: son un modelo integrado, sin robot.
  ⚠️ El modelo NO tiene inercia — integra la velocidad comandada al instante.
     Cuánto sigue rodando el RVR tras la orden de parada NO LO HA MEDIDO NADIE.
     Esto es el sobregiro del LAZO, no el del robot.
  ⚠️ El cuello de botella real es /odom, que llega a 16.5 Hz. Con el bucle a
     20 Hz, quien fija el paso ya NO es el bucle sino la odometría, así que
     este modelo (que supone una lectura fresca por iteración) es OPTIMISTA
     para 20 Hz.
  🔴 A 90° —el ángulo de las prácticas 2, 3, 4 y 10— 10 Hz y 20 Hz dan el
     MISMO resultado: subir la frecuencia ahí no compra nada. Y la ventaja
     NO crece con el ángulo: barriendo 1..720° solo sale 0 o 0.573°, con
     ~50 % de empates en todos los rangos. Es aliasing de retícula.
""")
    print("Tabla comparativa 10 Hz vs 20 Hz con tiempos y mejora:")
    print("  python3 simular_sobregiro.py")
    print("═" * 70)
