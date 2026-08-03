"""Las funciones puras de `atriz.py`: sin ROS, sin robot, sin motores.

🔴 El test que importa es `test_acumular_una_vuelta_entera_da_360`: leyendo el yaw
   ABSOLUTO una vuelta completa da 0°, porque `atan2` devuelve −π..π. Ese error es
   invisible hasta que alguien pide `girar(360)` y el robot no se mueve.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))

from atriz import (                                          # noqa: E402
    ErrorAtriz, GRADOS_MAX, RITMO_HZ, TIEMPO_MAX, TOPIC_MANDO, VEL_GIRO_MAX,
    VEL_MAX, acumular, alcanzado, limitar, normalizar, validar_canal_led,
    velocidad_giro, yaw_de_cuaternion,
)


# ── Las constantes, con su fuente ────────────────────────────────────────────
def test_el_topic_de_mando_no_es_cmd_vel():
    """🔴 `/cmd_vel` es la SALIDA del collision_monitor: publicar ahí salta la
    capa de seguridad y FUNCIONA, que es lo que lo hace peligroso."""
    assert TOPIC_MANDO == '/cmd_vel_raw'


def test_los_topes_son_los_medidos():
    assert VEL_MAX == 0.40          # meseta real medida (2026-07-31)
    assert VEL_GIRO_MAX == 2.0
    assert TIEMPO_MAX == 10.0
    assert GRADOS_MAX == 720.0


def test_el_ritmo_bate_al_watchdog():
    """El driver corta a los 0.3 s sin cmd_vel; hay que publicar más rápido."""
    assert 1.0 / RITMO_HZ < 0.3


# ── limitar ──────────────────────────────────────────────────────────────────
def test_limitar_no_toca_ni_avisa_dentro_del_limite():
    valor, aviso = limitar(0.20, VEL_MAX, 'velocidad', 'm/s')
    assert valor == 0.20
    assert aviso is None


def test_limitar_recorta_y_avisa_en_voz_alta():
    valor, aviso = limitar(1.5, VEL_MAX, 'velocidad', 'm/s')
    assert valor == 0.40
    assert aviso is not None and '1.5' in aviso and '0.4' in aviso


def test_limitar_respeta_el_signo():
    valor, aviso = limitar(-1.5, VEL_MAX, 'velocidad', 'm/s')
    assert valor == -0.40
    assert aviso is not None


# ── normalizar ───────────────────────────────────────────────────────────────
def test_normalizar_deja_quieto_lo_que_ya_esta_en_rango():
    assert math.isclose(normalizar(math.radians(45.0)), math.radians(45.0))


def test_normalizar_359_es_menos_uno():
    assert math.isclose(normalizar(math.radians(359.0)), math.radians(-1.0),
                        abs_tol=1e-9)


def test_normalizar_devuelve_pi_y_no_menos_pi():
    """El intervalo es (−π, π]: el extremo cerrado es el positivo."""
    assert math.isclose(normalizar(-math.pi), math.pi, abs_tol=1e-9)


# ── acumular ─────────────────────────────────────────────────────────────────
def test_acumular_una_vuelta_entera_da_360():
    """🔴 EL TEST QUE JUSTIFICA LA FUNCIÓN. 36 pasos de 10°: leyendo el yaw
    absoluto el total sería 0, y `girar(360)` terminaría sin moverse."""
    acumulado, anterior = 0.0, 0.0
    for paso in range(1, 37):
        actual = normalizar(math.radians(10.0 * paso))
        acumulado = acumular(anterior, actual, acumulado)
        anterior = actual
    assert math.isclose(math.degrees(acumulado), 360.0, abs_tol=1e-6)


def test_acumular_cuenta_negativo_al_girar_al_reves():
    acumulado, anterior = 0.0, 0.0
    for paso in range(1, 10):
        actual = normalizar(math.radians(-10.0 * paso))
        acumulado = acumular(anterior, actual, acumulado)
        anterior = actual
    assert math.isclose(math.degrees(acumulado), -90.0, abs_tol=1e-6)


# ── yaw_de_cuaternion ────────────────────────────────────────────────────────
def test_yaw_de_cuaternion_identidad_es_cero():
    assert yaw_de_cuaternion(0.0, 0.0, 0.0, 1.0) == 0.0


def test_yaw_de_cuaternion_noventa_grados():
    mitad = math.radians(45.0)
    yaw = yaw_de_cuaternion(0.0, 0.0, math.sin(mitad), math.cos(mitad))
    assert math.isclose(math.degrees(yaw), 90.0, abs_tol=1e-9)


# ── alcanzado ────────────────────────────────────────────────────────────────
def test_alcanzado_hacia_la_izquierda():
    assert alcanzado(math.radians(91.0), math.radians(90.0))
    assert not alcanzado(math.radians(89.0), math.radians(90.0))


def test_alcanzado_hacia_la_derecha_no_confunde_el_signo():
    """girar(−90) termina en −π/2. Comparar valores absolutos daría por buena
    una vuelta en el sentido contrario."""
    assert alcanzado(math.radians(-91.0), math.radians(-90.0))
    assert not alcanzado(math.radians(-89.0), math.radians(-90.0))
    assert not alcanzado(math.radians(+91.0), math.radians(-90.0))


# ── velocidad_giro ───────────────────────────────────────────────────────────
def test_velocidad_giro_frena_al_acercarse():
    lejos = velocidad_giro(math.radians(90.0))
    medio = velocidad_giro(math.radians(20.0))
    cerca = velocidad_giro(math.radians(3.0))
    assert lejos > medio > cerca > 0.0


def test_velocidad_giro_nunca_pasa_del_tope():
    for grados in (0.5, 5.0, 45.0, 180.0, 720.0):
        assert 0.0 < velocidad_giro(math.radians(grados)) <= VEL_GIRO_MAX


def test_velocidad_giro_no_depende_del_signo():
    assert velocidad_giro(math.radians(45.0)) == velocidad_giro(math.radians(-45.0))


# ── simular_girar ────────────────────────────────────────────────────────────
def test_simulador_converge_en_caso_normal():
    """El simulador converge a los valores pedidos en caso ideal."""
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import simular_girar  # noqa: E402, F401

    def yaw_ideal(iteracion, restante_grados, dt):
        if iteracion == 0:
            return 0.0
        return iteracion * dt * 0.5

    resultado, iters, razon = simular_girar(90, yaw_ideal, freq_hz=20.0)
    assert razon == 'convergencia'
    assert abs(resultado - 90.0) < 2.0  # margen para la simulación


def test_simulador_detecta_odom_congelado():
    """El simulador detecta cuando /odom no se actualiza."""
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import simular_girar  # noqa: E402

    def yaw_congelado(iteracion, restante_grados, dt):
        if iteracion >= 50:
            return math.radians(45.8)
        return iteracion * dt * 0.5

    resultado, iters, razon = simular_girar(90, yaw_congelado, freq_hz=20.0)
    assert razon == 'odom_congelado'
    assert abs(resultado - 45.8) < 1.0


def test_simulador_tolera_duplicados_ocasionales():
    """El simulador permite que muestras ocasionales se repitan (normal)."""
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import simular_girar  # noqa: E402

    def yaw_con_duplicados(iteracion, restante_grados, dt):
        if iteracion % 3 == 0:
            return (iteracion - 1) * dt * 0.5
        return iteracion * dt * 0.5

    resultado, iters, razon = simular_girar(90, yaw_con_duplicados, freq_hz=20.0)
    assert razon == 'convergencia'  # debe convergir a pesar de los duplicados
    assert abs(resultado - 90.0) < 2.5


def test_frecuencia_20hz_reduce_el_sobregiro():
    """A 20 Hz el sobregiro en grados es MENOR que a 10 Hz, con la rampa REAL
    de velocidad_giro() (generador_rampa_real, la misma que usan
    simular_girar.py y medir_sobregiro.py).

    🔴 Desigualdad ESTRICTA a propósito, no `<=`. Con el bug original
    (`dt = 1.0/20.0` hardcodeado dentro de simular_girar(), ignorando
    freq_hz) las dos llamadas reciben el MISMO dt por dentro, así que
    generan la MISMA trayectoria y r20 == r10 — una igualdad que `<=`
    dejaría pasar en silencio. Con `<` estricto, ese caso FALLA.
    Ver la Ronda de arreglo 4 del informe: reintroducido el bug, este test
    falla; restaurado, pasa.
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    for grados in [90, 180, 360, 720]:
        r10, _, _ = simular_girar(grados, generador_rampa_real(), freq_hz=10.0)
        r20, _, _ = simular_girar(grados, generador_rampa_real(), freq_hz=20.0)
        assert r20 < r10, (
            f"{grados}°: 10 Hz={r10:.3f}, 20 Hz={r20:.3f}. "
            f"A 20 Hz el sobregiro tiene que ser ESTRICTAMENTE menor. "
            f"Si salen iguales, sospecha de un dt hardcodeado en simular_girar()."
        )


def test_generador_recibe_dt_correcto_segun_freq_hz():
    """simular_girar() tiene que pasarle al generador dt = 1.0 / freq_hz.

    Éste es el test dirigido al bug real (Ronda de arreglo 3): un dt
    hardcodeado a 1.0/20.0 dentro de simular_girar(), ignorando el parámetro
    freq_hz, hace que para freq_hz=10.0 el generador reciba 0.05 en vez de
    0.1 — esta aserción lo atrapa directamente, sin pasar por la física de
    velocidad_giro().
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import simular_girar  # noqa: E402

    for freq_hz in (10.0, 20.0):
        dts_recibidos = []

        def yaw_gen(iteracion, restante_grados, dt, _dts=dts_recibidos):
            _dts.append(dt)
            return 0.0 if iteracion == 0 else iteracion * dt * 0.5

        simular_girar(90, yaw_gen, freq_hz=freq_hz)

        assert dts_recibidos, "el generador nunca fue llamado"
        esperado = 1.0 / freq_hz
        assert all(math.isclose(dt, esperado) for dt in dts_recibidos), (
            f"freq_hz={freq_hz}: el generador recibió dt={dts_recibidos[0]}, "
            f"se esperaba {esperado}. El dt está hardcodeado en simular_girar()."
        )


def test_generador_rampa_real_respeta_el_signo_en_giros_negativos():
    """generador_rampa_real() tiene que aplicar el SIGNO del objetivo, igual
    que Robot.girar() real: `sentido * velocidad_giro(...)`.

    velocidad_giro() usa abs() por dentro y nunca es negativa. Si el
    generador hace `acumulado += v_cmd * dt` sin multiplicar por el signo del
    objetivo, un giro negativo (`girar(-90)`, "a la derecha" según el
    docstring de girar()) hace que el acumulado se ALEJE del objetivo en vez
    de acercarse, y el lazo agota el tope de tiempo en vez de converger.

    Ronda de arreglo 5: encontrado ejecutando
    `simular_girar(-90, generador_rampa_real(), freq_hz=20.0)` -> ~589°,
    'timeout'.
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    resultado, iters, razon = simular_girar(-90, generador_rampa_real(), freq_hz=20.0)

    assert razon == 'convergencia', (
        f"giro de -90° con generador_rampa_real() terminó en '{razon}' "
        f"(resultado={resultado:.3f}°, iters={iters}), no en 'convergencia'. "
        f"Si el generador no aplica el signo, el acumulado se aleja del "
        f"objetivo y agota el tope de tiempo en vez de converger."
    )
    assert math.isclose(resultado, -90.0, abs_tol=2.0), (
        f"giro de -90° dio {resultado:.3f}°, se esperaba cerca de -90°."
    )


# ── validar_canal_led ────────────────────────────────────────────────────────
def test_validar_canal_led_acepta_el_rango_valido():
    validar_canal_led(0, 'rojo')
    validar_canal_led(255, 'rojo')
    validar_canal_led(128, 'rojo')


def test_validar_canal_led_rechaza_fuera_de_rango():
    with pytest.raises(ErrorAtriz):
        validar_canal_led(256, 'rojo')
    with pytest.raises(ErrorAtriz):
        validar_canal_led(-1, 'rojo')


def test_validar_canal_led_rechaza_bool_aunque_sea_subclase_de_int():
    """🔴 `bool` es subclase de `int` en Python: sin este chequeo,
    `luces(True, True, True)` pasaria como RGB (1,1,1) -- practicamente
    apagado -- sin avisar. Ronda de arreglo 1 de la Tarea 5."""
    with pytest.raises(ErrorAtriz):
        validar_canal_led(True, 'rojo')
    with pytest.raises(ErrorAtriz):
        validar_canal_led(False, 'rojo')


def test_validar_canal_led_rechaza_float_aunque_trunque_a_un_valor_valido():
    """`int(-0.5) == 0` es un entero valido: si el rango se comprobara
    DESPUES de convertir a int, esto pasaria en silencio. Hay que validar el
    valor tal como llega, no su truncamiento."""
    with pytest.raises(ErrorAtriz):
        validar_canal_led(-0.5, 'rojo')
    with pytest.raises(ErrorAtriz):
        validar_canal_led(128.0, 'rojo')


# ── seguidor_linea_pid_demo: el signo del giro depende del LADO ────────────
# 🔴 Tarea 11, Ronda de arreglo 1. Un solo sensor mirando hacia abajo no
# puede saber si el robot se desvio a la izquierda o a la derecha de la
# linea: `claro` sale igual de alto en los dos casos. Por eso el diseno
# separa el PID (decide CUANTO corregir) de `lado_borde` (decide HACIA
# DONDE). Este test es la prueba de que esa separacion es real: con el
# MISMO `claro`, el UNICO cambio es el lado, y el giro tiene que salir con
# signo contrario. Si no se pudiera escribir este test, el diseno seguiria
# teniendo el problema original (ver tarea-11-report.md).
sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
from seguidor_linea_pid_demo import (                        # noqa: E402
    PID as PIDSeguidor, clasificar, decidir_giro, magnitud_correccion,
    signo_correccion,
)


def test_signo_del_giro_depende_del_lado_no_de_la_lectura():
    """Mismo `claro`, lado del borde contrario -> giros de signo contrario.

    `claro=1275` es el suelo real medido (evidencia 37): bien lejos de
    cualquier umbral, para que la magnitud no sea cero.
    """
    claro = 1275
    pid_derecha = PIDSeguidor()
    pid_izquierda = PIDSeguidor()

    giro_derecha = decidir_giro(claro, +1, pid_derecha)
    giro_izquierda = decidir_giro(claro, -1, pid_izquierda)

    assert giro_derecha != 0.0
    assert giro_izquierda == -giro_derecha


def test_el_signo_cambia_una_sola_vez_al_barrer_toda_la_banda():
    """🔴 Tarea 11, Ronda de arreglo 2. Barre `claro` de 181 a 1275
    (evidencia 37) entero, no tres puntos sueltos -- los tres puntos que
    probe en la ronda 1 (181, 700, 1275) son justo los tres que el bug NO
    tocaba. El signo del giro tiene que cambiar UNA SOLA VEZ, y exactamente
    donde la magnitud pasa por cero (el centro). Si `signo_correccion()`
    usa una frontera distinta a `magnitud_correccion()`, aparece una banda
    donde el signo no ha cambiado pero la magnitud ya "quiere" el otro
    signo -- ahi el controlador empuja al robot MAS LEJOS del borde:
    realimentacion positiva, justo lo contrario de un lazo de control.
    """
    lado_borde = 1
    claros = list(range(181, 1276))
    giros = [decidir_giro(claro, lado_borde, PIDSeguidor()) for claro in claros]

    signos = [1 if g > 0 else (-1 if g < 0 else 0) for g in giros]
    no_nulos = [s for s in signos if s != 0]
    cambios = sum(1 for a, b in zip(no_nulos, no_nulos[1:]) if a != b)
    assert cambios == 1, (
        f"el signo del giro cambia {cambios} veces recorriendo claro=181..1275 "
        f"(lado_borde=1), se esperaba 1 -- cambio justo en el centro"
    )

    primero_positivo = next(i for i, s in enumerate(signos) if s > 0)
    assert all(s >= 0 for s in signos[primero_positivo:]), (
        "el giro vuelve a negativo despues de cruzar a positivo: no es monotono"
    )

    # 🔴 La comprobación que de verdad atrapa el bug: el paso entre dos
    # `claro` consecutivos (diferencia de 1) tiene que ser CHICO en todo
    # el barrido -- si el signo cambia en un sitio distinto al de la
    # magnitud, el salto en el cruce es GRANDE (en la ronda 1: de -1.245 a
    # +1.25, un salto de 2.5, porque ahí la magnitud NO estaba cerca de
    # cero). Con las dos funciones usando el mismo centro, el salto
    # máximo tiene que ser una fracción de la pendiente normal.
    saltos = [abs(b - a) for a, b in zip(giros, giros[1:])]
    salto_maximo = max(saltos)
    indice_salto_maximo = saltos.index(salto_maximo)
    assert salto_maximo < 0.05, (
        f"salto de {salto_maximo:.4f} entre claro={claros[indice_salto_maximo]} y "
        f"claro={claros[indice_salto_maximo + 1]} (giro {giros[indice_salto_maximo]:.4f} -> "
        f"{giros[indice_salto_maximo + 1]:.4f}). Un salto grande significa que el signo "
        f"cambió en un sitio donde la magnitud NO estaba cerca de cero: justo el bug de la "
        f"Ronda de arreglo 2."
    )


def test_signo_correccion_cambia_en_el_centro_no_en_las_fronteras_de_clasificar():
    """El signo tiene que cambiar en el CENTRO (700 = punto medio entre
    UMBRAL_NEGRO=400 y UMBRAL_CLARO=1000), no en las fronteras de
    `clasificar()` (450 y 950, con margen de histeresis) -- esas son para
    decidir cuando estamos PERDIDOS, no para fijar el signo de la
    correccion continua. 750 y 900 son la banda exacta que reprodujo el
    coordinador: antes del arreglo daban signo -1 (incorrecto)."""
    assert signo_correccion(699, 1) == -1
    assert signo_correccion(701, 1) == 1
    assert signo_correccion(750, 1) == 1
    assert signo_correccion(900, 1) == 1
    assert signo_correccion(949, 1) == 1


def test_clasificar_con_los_valores_de_la_evidencia_37():
    """negro=181 y suelo real=1275 (evidencia 37, 2026-08-01) tienen que
    clasificar sin ambiguedad con los umbrales por defecto del script."""
    assert clasificar(181) == 'negro'
    assert clasificar(1275) == 'claro'
    assert clasificar(700) == 'borde'  # el punto medio de UMBRAL_NEGRO/UMBRAL_CLARO


def test_magnitud_correccion_nunca_es_negativa():
    """El PID controla la magnitud, no el signo: pase lo que pase, tiene
    que ser >= 0."""
    pid = PIDSeguidor()
    for claro in (100, 181, 400, 700, 1000, 1275, 2288):
        assert magnitud_correccion(claro, pid) >= 0.0


def test_magnitud_correccion_crece_lejos_del_borde():
    """Cerca del punto medio (borde) la correccion es chica; lejos, mayor."""
    cerca = magnitud_correccion(750, PIDSeguidor())    # justo pasado el centro (700)
    lejos = magnitud_correccion(1275, PIDSeguidor())   # el suelo real
    assert lejos > cerca
