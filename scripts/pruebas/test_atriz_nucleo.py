"""Las funciones puras de `atriz.py`: sin ROS, sin robot, sin motores.

🔴 El test que importa es `test_acumular_una_vuelta_entera_da_360`: leyendo el yaw
   ABSOLUTO una vuelta completa da 0°, porque `atan2` devuelve −π..π. Ese error es
   invisible hasta que alguien pide `girar(360)` y el robot no se mueve.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))

from atriz import (                                          # noqa: E402
    GRADOS_MAX, RITMO_HZ, TIEMPO_MAX, TOPIC_MANDO, VEL_GIRO_MAX, VEL_MAX,
    acumular, alcanzado, limitar, normalizar, velocidad_giro, yaw_de_cuaternion,
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
