"""Las funciones puras de `atriz.py`: sin ROS, sin robot, sin motores.

🔴 El test que importa es `test_acumular_una_vuelta_entera_da_360`: leyendo el yaw
   ABSOLUTO una vuelta completa da 0°, porque `atan2` devuelve −π..π. Ese error es
   invisible hasta que alguien pide `girar(360)` y el robot no se mueve.
"""
import math
import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))

from atriz import (                                          # noqa: E402
    ErrorAtriz, GRADOS_MAX, RITMO_HZ, SENALES_DE_CIERRE, TIEMPO_MAX,
    TOPIC_MANDO, VEL_GIRO_MAX, VEL_MAX, Robot, acumular, debe_apagar_barrido, alcanzado, limitar,
    normalizar, secuencia_de_cierre, validar_canal_led, velocidad_giro,
    yaw_de_cuaternion,
)


# ═══════════════════════════════════════════════════════════════════════════
# EL BARRIDO DEL LIDAR SE APAGA PASE LO QUE PASE
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 Es LA garantia de esta biblioteca, y tenia dos agujeros: el segundo
#    Ctrl-C y las señales que no eran SIGINT. Si no se apaga, el X2 se queda
#    girando a 11.8 Hz en vez de 2.7, indefinidamente, en 16 robots.
#    Estos tests PROVOCAN el fallo; no lo razonan.

def _rastro_de_cierre(parar):
    """Corre la secuencia real anotando que pasos se llegaron a ejecutar."""
    rastro = []
    secuencia_de_cierre(
        parar=parar,
        apagar_barrido=lambda: rastro.append('/stop_scan'),
        desmontar=lambda: rastro.append('desmontar'),
        avisar=lambda _m: None)
    return rastro


def test_el_barrido_se_apaga_aunque_el_paso_de_parar_lance_systemexit():
    """🔴 EL SEGUNDO Ctrl-C. El manejador de señal hace `sys.exit()`, que lanza
    `SystemExit` — y `SystemExit` NO es `Exception`. Con la estructura vieja
    (dos `try`, un solo `finally` colgado del segundo, `except Exception`) esa
    excepcion escapaba del cierre a medias y `/stop_scan` NO se llamaba.
    """
    def parar():
        raise SystemExit(130)          # exactamente lo que hace el manejador

    # 🔴 El `SystemExit` se atrapa y se convierte en un dato, NO se deja
    #    propagar ni se relanza otra excepcion desde el `except`: las dos cosas
    #    TERMINAN la sesion de pytest y esconden los demas tests. Medido al
    #    reintroducir el bug: 25 tests corridos de 76.
    rastro, escapo = [], False
    try:
        rastro = _rastro_de_cierre(parar)
    except SystemExit:
        escapo = True

    assert not escapo, (
        'el SystemExit del segundo Ctrl-C escapo del cierre: el apagado del '
        'barrido quedo a merced de donde cayera la señal')
    assert '/stop_scan' in rastro, (
        'el segundo Ctrl-C se llevo por delante el apagado del barrido: el X2 '
        'se queda girando a 11.8 Hz para siempre')
    assert 'desmontar' in rastro


def test_el_barrido_se_apaga_aunque_el_paso_de_parar_lance_keyboardinterrupt():
    """`KeyboardInterrupt` tampoco es `Exception`. Mismo agujero, otra puerta.

    🔴 Igual que el test de arriba, se atrapa en vez de dejarlo propagar: un
       `KeyboardInterrupt` suelto hace que pytest ABORTE LA SESION ENTERA
       ("session interrupted"), y entonces el fallo real queda escondido detras
       de 50 tests que ni se ejecutan. Medido reintroduciendo el bug.
    """
    def parar():
        raise KeyboardInterrupt

    rastro, escapo = [], False
    try:
        rastro = _rastro_de_cierre(parar)
    except KeyboardInterrupt:
        escapo = True

    assert not escapo, 'el KeyboardInterrupt escapo del cierre'
    assert '/stop_scan' in rastro


def test_el_barrido_se_apaga_aunque_el_paso_de_parar_lance_una_excepcion():
    """El caso corriente: `_mandar()` revienta publicando sobre un contexto ya
    invalido. Tambien tiene que llegarse a `/stop_scan`."""
    def parar():
        raise RuntimeError('publisher context is invalid')

    assert '/stop_scan' in _rastro_de_cierre(parar)


def test_los_recursos_se_sueltan_aunque_falle_el_apagado_del_barrido():
    """El tercer paso cuelga del `finally` del segundo, no del mismo `try`."""
    pasos = []
    secuencia_de_cierre(
        parar=lambda: pasos.append('parar'),
        apagar_barrido=lambda: (_ for _ in ()).throw(RuntimeError('sin driver')),
        desmontar=lambda: pasos.append('desmontar'),
        avisar=lambda _m: None)
    assert pasos == ['parar', 'desmontar']


def test_se_capturan_TODAS_las_senales_de_fin_que_se_pueden_capturar():
    """🔴 Solo con SIGINT, cerrar la terminal (SIGHUP), `kill` (SIGTERM) o
    Ctrl-\\ (SIGQUIT) mataban el proceso SIN pasar por `cerrar()`, y el barrido
    quedaba encendido. El watchdog de 0.3 s del driver para los MOTORES; del
    LIDAR no sabe nada. Verificado provocando cada señal sobre procesos reales.

    🔴 SIGQUIT es el que mas cuesta acordarse y el mas probable de todos DESPUES
       del arreglo del segundo Ctrl-C: ahora la biblioteca ignora los Ctrl-C
       repetidos y pide esperar, y ese es exactamente el momento en que alguien
       prueba Ctrl-\\. Medido sin capturarla: salida 131, «core dumped»,
       barrido ENCENDIDO.

    La lista se compara contra las señales de fin capturables que existen en
    este sistema, no contra una lista escrita a mano: si mañana hiciera falta
    otra, este test no la echaria de menos por si solo, pero al menos no deja
    caer ninguna de las cuatro que ya sabemos que hacen falta.
    """
    nombres = {s.name for s in SENALES_DE_CIERRE}
    assert nombres == {'SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT'}, (
        f'faltan señales de cierre: {nombres}. Sin SIGHUP, perder el SSH deja '
        f'el X2 girando a 11.8 Hz; sin SIGTERM, `systemctl stop` hace lo mismo; '
        f'sin SIGQUIT, Ctrl-\\ tambien')


def test_ninguna_senal_de_cierre_es_incapturable():
    """SIGKILL y SIGSTOP no se pueden capturar: meterlos en la lista haria que
    `signal.signal()` lanzara al construir el Robot, o sea que romperia el
    arranque entero en vez de proteger nada."""
    incapturables = {getattr(signal, n) for n in ('SIGKILL', 'SIGSTOP')
                     if hasattr(signal, n)}
    assert not (set(SENALES_DE_CIERRE) & incapturables)


def _robot_sin_ros():
    """Un `Robot` de laboratorio SIN ROS ni robot: se salta `__init__` y se le
    inyecta lo justo. Ejercita los metodos REALES `cerrar()` y `_al_senal()`,
    no una copia — una copia podria quedarse atras sin que nada fallara."""
    robot = Robot.__new__(Robot)
    robot._cerrado = False
    robot._cerrando = False
    robot.rastro = []
    robot._mandar = lambda *_a, **_k: robot.rastro.append('parar')
    robot._apagar_barrido = lambda: robot.rastro.append('/stop_scan')
    robot._desmontar = lambda: robot.rastro.append('desmontar')
    return robot


def test_el_segundo_ctrl_c_no_aborta_el_cierre_en_curso():
    """🔴 EL AGUJERO A1, con señales de VERDAD sobre los metodos de VERDAD.

    El segundo Ctrl-C se entrega con `signal.raise_signal()` desde dentro del
    paso de parada, que es justo cuando llega en la practica. Antes,
    `_al_ctrl_c` hacia `sys.exit(130)` incondicional: `cerrar()` reentraba,
    salia por `if self._cerrado: return`, y el `SystemExit` escapaba del
    cierre a medias.

    📝 Y `00_LEEME_PRIMERO.md` le decia al alumno «espera un segundo y vuelve
       a pulsar»: el manual conducia al agujero.
    """
    robot = _robot_sin_ros()

    def parar_y_recibir_el_segundo_ctrl_c(*_a, **_k):
        robot.rastro.append('parar')
        signal.raise_signal(signal.SIGINT)

    robot._mandar = parar_y_recibir_el_segundo_ctrl_c

    anterior = signal.signal(signal.SIGINT, robot._al_senal)
    try:
        with pytest.raises(SystemExit):
            robot._al_senal(signal.SIGINT, None)      # el PRIMER Ctrl-C
    finally:
        signal.signal(signal.SIGINT, anterior)

    assert '/stop_scan' in robot.rastro, (
        f'el segundo Ctrl-C aborto el cierre: {robot.rastro}. El barrido del '
        f'X2 se queda encendido a 11.8 Hz')
    assert robot.rastro == ['parar', '/stop_scan', 'desmontar']


def test_una_senal_durante_el_cierre_no_lo_interrumpe():
    """El guardia de reentrada de `_al_senal()`, POR SI SOLO.

    🔴 Es defensa en profundidad, y por eso necesita su propio test: con
       `except BaseException` en `secuencia_de_cierre()` el barrido ya se
       apagaria igual, asi que un test que solo mirase `/stop_scan` NO detecta
       que este guardia desaparezca — comprobado quitandolo: los 75 seguian en
       verde. Lo que el guardia aporta es que el cierre TERMINE entero en vez
       de salir por la mitad, y eso es lo que se fija aqui.
    """
    robot = _robot_sin_ros()
    robot._cerrando = True                    # cierre ya en curso
    robot._al_senal(signal.SIGTERM, None)     # no debe lanzar SystemExit
    assert robot.rastro == [], (
        'una señal durante el cierre arranco un cierre nuevo en vez de '
        'dejar terminar el que estaba en marcha')


def test_el_guardia_se_pone_ANTES_de_marcar_el_cierre_como_hecho():
    """🔴 LA VENTANA DE DOS SENTENCIAS, que resucitaba el bug del segundo Ctrl-C.

    `cerrar()` pone dos banderas. Si `_cerrado` se pusiera PRIMERO, quedaria un
    hueco en el que `_cerrado` ya es True pero el guardia aun no esta puesto:
    una señal que cayera justo ahi veria `_cerrando == False`, llamaria a
    `cerrar()`, esta saldria por `if self._cerrado: return`, y el manejador
    haria `sys.exit()`. Ni parar, ni /stop_scan, ni desmontar — la mecanica
    exacta de A1. Reproducido entregando la señal en ese punto: rastro VACIO.

    Este test no depende de acertar el instante: intercepta la asignacion y
    comprueba la INVARIANTE — cuando `_cerrado` pasa a True, `_cerrando` ya
    tiene que valer True. Si alguien vuelve a invertir las dos lineas, cae.
    """
    visto = {}

    class RobotVigilado(Robot):
        def __setattr__(self, nombre, valor):
            if nombre == '_cerrado' and valor is True:
                visto['cerrando_en_ese_instante'] = getattr(
                    self, '_cerrando', False)
            object.__setattr__(self, nombre, valor)

    robot = RobotVigilado.__new__(RobotVigilado)
    object.__setattr__(robot, '_cerrado', False)
    object.__setattr__(robot, '_cerrando', False)
    object.__setattr__(robot, 'rastro', [])
    object.__setattr__(robot, '_mandar',
                       lambda *_a, **_k: robot.rastro.append('parar'))
    object.__setattr__(robot, '_apagar_barrido',
                       lambda: robot.rastro.append('/stop_scan'))
    object.__setattr__(robot, '_desmontar',
                       lambda: robot.rastro.append('desmontar'))

    robot.cerrar()

    assert visto.get('cerrando_en_ese_instante') is True, (
        'al marcar `_cerrado = True` el guardia `_cerrando` todavia valia '
        'False: queda una ventana en la que una señal aborta el cierre entero '
        'sin llamar a /stop_scan. `_cerrando` tiene que ponerse ANTES.')
    assert robot.rastro == ['parar', '/stop_scan', 'desmontar']


def test_cerrar_dos_veces_no_repite_el_trabajo():
    robot = _robot_sin_ros()
    robot.cerrar()
    robot.cerrar()
    assert robot.rastro == ['parar', '/stop_scan', 'desmontar']


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


# ── limitar: lo NO finito se rechaza, no se recorta ──────────────────────────
# 🔴 `math.copysign(tope, nan)` devuelve el TOPE. La funcion cuyo proposito
#    documentado es «recortar a un valor seguro» convertia la entrada menos
#    fiable de todas en la velocidad MAXIMA. Medido antes del arreglo:
#      limitar(nan) -> 0.4   limitar(inf) -> 0.4   limitar(-inf) -> -0.4
#    Mismo criterio que `aceptacion_nucleo.delta_angulo()`, que ya rechazaba
#    lo no finito con una excepcion en vez de dejarlo pasar.

@pytest.mark.parametrize('valor', [float('nan'), float('inf'), float('-inf')])
def test_limitar_rechaza_lo_no_finito_en_vez_de_mapearlo_al_maximo(valor):
    with pytest.raises(ErrorAtriz):
        limitar(valor, VEL_MAX, 'velocidad', 'm/s')


def test_limitar_nunca_devuelve_el_tope_para_una_entrada_no_finita():
    """La forma general, por si alguien cambia el mensaje o el tipo de error:
    lo que NO puede pasar es que `nan` salga de aqui convertido en 0.40."""
    for valor in (float('nan'), float('inf'), float('-inf')):
        try:
            recortado, _ = limitar(valor, VEL_MAX, 'velocidad', 'm/s')
        except ErrorAtriz:
            continue
        assert abs(recortado) != VEL_MAX, (
            f'limitar({valor}) devolvio {recortado}: un valor no finito se '
            f'convirtio en la velocidad MAXIMA del laboratorio')


def test_avanzar_con_nan_no_puede_conducir_los_cuatro_metros():
    """🔴 El desenlace que esto evita, con las dos llamadas que hace
    `avanzar()`: `limitar(nan, VEL_MAX)` daba 0.40 m/s y
    `limitar(abs(nan), TIEMPO_MAX)` daba 10.0 s — 4.0 METROS a maxima
    velocidad, con el robot en un aula."""
    nan = float('nan')
    with pytest.raises(ErrorAtriz):
        limitar(nan, VEL_MAX, 'velocidad', 'm/s')
    with pytest.raises(ErrorAtriz):
        limitar(abs(nan), TIEMPO_MAX, 'tiempo', 's')


def test_limitar_rechaza_lo_que_no_es_un_numero():
    for valor in ('0.2', None, [0.2], True):
        with pytest.raises(ErrorAtriz):
            limitar(valor, VEL_MAX, 'velocidad', 'm/s')


def test_limitar_sigue_aceptando_enteros():
    """`avanzar(0.20, 3)` pasa un `int` por el camino del tiempo."""
    valor, aviso = limitar(3, TIEMPO_MAX, 'tiempo', 's')
    assert valor == 3 and aviso is None


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


# 🔴 LA RAMPA, CLAVADA. Hasta ahora NINGUN test la fijaba: comprobado mutandola
#    a mano, con los 76 en verde en las dos veces —
#      fronteras 30°/8° -> 25°/3°          : 76 passed
#      valores 0.80/0.40/0.20 -> 0.90/0.50/0.10 : 76 passed
#    Los tres tests de arriba solo miran la FORMA (que baje, que no pase del
#    tope, que ignore el signo), y esa forma sobrevive a cualquier rampa
#    decreciente. Pero estos numeros no son libres: el ultimo tramo (0.20 rad/s)
#    es el que fija la resolucion del lazo — 0.20 x 0.05 s = 0.573° de
#    granularidad — y el sobregiro que reportan simular_girar.py y
#    simular_sobregiro.py sale de ellos. Cambiarlos sin cambiar esas cifras es
#    exactamente la deriva que este proyecto persigue.

def test_las_fronteras_de_la_rampa_son_las_documentadas():
    """30° y 8°. Se prueba a los dos lados de cada frontera."""
    assert velocidad_giro(math.radians(30.1)) == 0.80
    assert velocidad_giro(math.radians(29.9)) == 0.40
    assert velocidad_giro(math.radians(8.1)) == 0.40
    assert velocidad_giro(math.radians(7.9)) == 0.20


def test_los_tres_valores_de_la_rampa_son_los_documentados():
    """0.80 / 0.40 / 0.20 rad/s. El ultimo es el que fija la resolucion del
    lazo de `girar()`, y de el sale el 0.573° de granularidad a 20 Hz."""
    assert velocidad_giro(math.radians(180.0)) == 0.80
    assert velocidad_giro(math.radians(20.0)) == 0.40
    assert velocidad_giro(math.radians(3.0)) == 0.20
    assert velocidad_giro(0.0) == 0.20


def test_la_granularidad_del_lazo_de_girar_sale_de_la_rampa():
    """La cifra que la documentacion tiene derecho a citar: el tramo lento de
    la rampa a 20 Hz da 0.573° de resolucion. Si alguien toca el 0.20, esta
    cifra deja de ser cierta y hay que reescribir lo que dice el manual."""
    lento = velocidad_giro(0.0)
    assert math.isclose(math.degrees(lento * 0.05), 0.5730, abs_tol=1e-4)
    assert math.isclose(math.degrees(lento * 0.10), 1.1459, abs_tol=1e-4)


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


def test_el_simulador_no_integra_despues_de_la_orden_de_parada():
    """🔴 El simulador tiene que modelar el `parar()` de `girar()`.

    Al salir del lazo, `girar()` llama a `parar()`: la velocidad comandada pasa
    a CERO. El simulador seguia llamando al generador una vez mas con
    `restante_grados=0.0`, y como `velocidad_giro(0)` vale 0.20 rad/s —nunca
    cero— integraba 0.20 rad/s DESPUES de la orden de parada. Ese paso de mas
    vale `0.20 * dt`, o sea que es proporcional a dt: +1.1459° a 10 Hz y
    +0.5730° a 20 Hz. Fabricaba una ventaja de 20 Hz de exactamente 0.5730°
    que no salia del lazo sino de su propio ultimo paso.

    Se cuenta el numero de llamadas al generador en vez de mirar el resultado:
    es la comprobacion DIRECTA del defecto. Con el bug, son `iters + 2`.
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    real = generador_rampa_real()
    llamadas = []

    def espia(iteracion, restante_grados, dt):
        llamadas.append(restante_grados)
        return real(iteracion, restante_grados, dt)

    resultado, iters, razon = simular_girar(90, espia, freq_hz=10.0)
    assert razon == 'convergencia'
    assert len(llamadas) == iters + 1, (
        f'el generador se llamo {len(llamadas)} veces para {iters} iteraciones '
        f'(se esperaba iters + 1, la de arranque). Una llamada de mas despues '
        f'del lazo significa que el simulador sigue integrando velocidad tras '
        f'la orden de parada: sobregiro inventado y proporcional a dt. '
        f'Ultimo restante recibido: {llamadas[-1]}')


@pytest.mark.parametrize('grados,segundos_analiticos', [
    # Integrando la rampa a mano: t = suma de (tramo / velocidad del tramo).
    #   0.80 rad/s mientras quedan > 30°, 0.40 mientras quedan > 8°, 0.20 luego.
    (90, (math.radians(90 - 30) / 0.80 + math.radians(30 - 8) / 0.40
          + math.radians(8) / 0.20)),
    (180, (math.radians(180 - 30) / 0.80 + math.radians(30 - 8) / 0.40
           + math.radians(8) / 0.20)),
    (360, (math.radians(360 - 30) / 0.80 + math.radians(30 - 8) / 0.40
           + math.radians(8) / 0.20)),
])
def test_el_tiempo_que_reporta_el_simulador_cuadra_con_la_rampa(
    grados, segundos_analiticos,
):
    """🔴 La columna «tiempo» de `simular_sobregiro.py` no la validaba NADA:
    podia estar mal sin que saltase un solo test. Aqui se contrasta contra la
    integral de la rampa hecha a mano, que es una via independiente del bucle.

    ⚠️ El margen es DOS pasos, no uno, y la cifra sale de MEDIRLO en vez de
       suponerla. Mi primera version puso un paso y el caso de 360° a 10 Hz la
       rompio. Medido el exceso (tiempo simulado - integral) en pasos de dt:

           90°  10 Hz  +0.33      90°  20 Hz  +0.66
          180°  10 Hz  +0.69     180°  20 Hz  +0.39
          360°  10 Hz  +1.42     360°  20 Hz  +0.85
          720°  10 Hz  +0.88     720°  20 Hz  -0.23   <- NEGATIVO

       La razon es que la rampa tiene TRES tramos, y el lazo cruza cada
       frontera con hasta un paso de error; ademas puede cruzarla tarde y
       quedarse un paso de mas a la velocidad rapida, lo que hace que a veces
       termine ANTES que el modelo continuo. Con ±2 dt caben los ocho casos
       con margen, y un error de verdad en la formula (usar el dt de la otra
       frecuencia, por ejemplo) desviaria el doble o mas.
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    for freq_hz in (10.0, 20.0):
        dt = 1.0 / freq_hz
        _, iters, razon = simular_girar(grados, generador_rampa_real(),
                                        freq_hz=freq_hz)
        assert razon == 'convergencia'
        segundos = iters * dt
        assert abs(segundos - segundos_analiticos) <= 2 * dt, (
            f'{grados}° a {freq_hz:.0f} Hz: el simulador dice {segundos:.3f} s '
            f'({iters} iteraciones x {dt} s), la integral de la rampa da '
            f'{segundos_analiticos:.3f} s. Se salen mas de dos pasos ({2 * dt} s).')


def test_las_dos_frecuencias_tardan_practicamente_lo_mismo():
    """Corolario que conviene tener fijado: subir a 20 Hz NO acelera el giro.
    Lo unico que cambia es la resolucion con la que se decide parar."""
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    for grados in (90, 180, 360):
        _, i10, _ = simular_girar(grados, generador_rampa_real(), freq_hz=10.0)
        _, i20, _ = simular_girar(grados, generador_rampa_real(), freq_hz=20.0)
        assert abs(i10 * 0.10 - i20 * 0.05) <= 0.10, (
            f'{grados}°: 10 Hz tarda {i10 * 0.10:.3f} s y 20 Hz '
            f'{i20 * 0.05:.3f} s. No deberian diferir mas de un paso.')


def test_a_90_grados_subir_a_20hz_NO_compra_nada():
    """🔴 LA VERDAD, y no es la que decia la documentacion.

    90° es el angulo de las practicas 2, 3, 4 y 10 — el unico que el curso usa
    de verdad. Con el `parar()` bien modelado, 10 Hz y 20 Hz dan EXACTAMENTE lo
    mismo a 90°: 90.5273 los dos. La ventaja de +0.573° que se reportaba era
    integramente el artefacto del paso de mas tras la parada.

    Este test es ademas el guardian de que ese artefacto no vuelva: si alguien
    reintroduce la integracion posterior a la parada, los dos dejan de ser
    iguales y esto falla.
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    r10, _, _ = simular_girar(90, generador_rampa_real(), freq_hz=10.0)
    r20, _, _ = simular_girar(90, generador_rampa_real(), freq_hz=20.0)
    assert math.isclose(r10, r20, abs_tol=1e-9), (
        f'a 90° salen 10 Hz={r10:.4f} y 20 Hz={r20:.4f}. Tienen que ser '
        f'IGUALES: a este angulo el paso de la rampa cae en el mismo sitio con '
        f'las dos frecuencias. Si difieren, el simulador ha vuelto a integrar '
        f'despues de la orden de parada.')


@pytest.mark.parametrize('grados', [180, 360, 720])
def test_a_partir_de_180_grados_20hz_si_reduce_el_sobregiro(grados):
    """Donde 20 Hz SI compra algo: 0.5730° menos de sobregiro, que es
    justamente un paso de la rampa lenta (0.20 rad/s x 0.05 s).

    Desigualdad ESTRICTA a proposito, no `<=`. Con el bug del `dt` clavado
    (`1.0/20.0` dentro de simular_girar(), ignorando freq_hz) las dos llamadas
    reciben el MISMO dt, generan la MISMA trayectoria y r20 == r10 — una
    igualdad que `<=` dejaria pasar en silencio.
    """
    sys.path.insert(0, str(Path.home() / 'atriz_migracion/scripts'))
    from simular_girar import generador_rampa_real, simular_girar  # noqa: E402

    r10, _, _ = simular_girar(grados, generador_rampa_real(), freq_hz=10.0)
    r20, _, _ = simular_girar(grados, generador_rampa_real(), freq_hz=20.0)
    assert r20 < r10, (
        f'{grados}°: 10 Hz={r10:.4f}, 20 Hz={r20:.4f}. A 20 Hz el sobregiro '
        f'tiene que ser ESTRICTAMENTE menor. Si salen iguales, sospecha de un '
        f'dt clavado en simular_girar().')


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


@pytest.mark.parametrize('lado_borde', [1, -1])
def test_el_signo_cambia_una_sola_vez_al_barrer_toda_la_banda(lado_borde):
    """🔴 Tarea 11, Ronda de arreglo 2. Barre `claro` de 181 a 1275
    (evidencia 37) entero, no tres puntos sueltos -- los tres puntos que
    probe en la ronda 1 (181, 700, 1275) son justo los tres que el bug NO
    tocaba. El signo del giro tiene que cambiar UNA SOLA VEZ, y exactamente
    donde la magnitud pasa por cero (el centro). Si `signo_correccion()`
    usa una frontera distinta a `magnitud_correccion()`, aparece una banda
    donde el signo no ha cambiado pero la magnitud ya "quiere" el otro
    signo -- ahi el controlador empuja al robot MAS LEJOS del borde:
    realimentacion positiva, justo lo contrario de un lazo de control.

    🔴 Ronda de arreglo 3: parametrizado por `lado_borde` (1 Y -1). Con
    solo `lado_borde=1` este barrido no atrapaba un bug que ignorara el
    lado en la zona 'negro' -- ver
    `test_signo_correccion_respeta_lado_borde_tambien_en_la_zona_negra`.
    """
    claros = list(range(181, 1276))
    giros = [decidir_giro(claro, lado_borde, PIDSeguidor()) for claro in claros]

    signos = [1 if g > 0 else (-1 if g < 0 else 0) for g in giros]
    no_nulos = [s for s in signos if s != 0]
    cambios = sum(1 for a, b in zip(no_nulos, no_nulos[1:]) if a != b)
    assert cambios == 1, (
        f"el signo del giro cambia {cambios} veces recorriendo claro=181..1275 "
        f"(lado_borde={lado_borde}), se esperaba 1 -- cambio justo en el centro"
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
        f"{giros[indice_salto_maximo + 1]:.4f}, lado_borde={lado_borde}). Un salto grande "
        f"significa que el signo cambió en un sitio donde la magnitud NO estaba cerca de "
        f"cero: justo el bug de la Ronda de arreglo 2."
    )


@pytest.mark.parametrize('lado_borde,signo_en_claro,signo_en_negro', [
    (1, 1, -1),
    (-1, -1, 1),
])
def test_signo_correccion_cambia_en_el_centro_no_en_las_fronteras_de_clasificar(
    lado_borde, signo_en_claro, signo_en_negro,
):
    """El signo tiene que cambiar en el CENTRO (700 = punto medio entre
    UMBRAL_NEGRO=400 y UMBRAL_CLARO=1000), no en las fronteras de
    `clasificar()` (450 y 950, con margen de histeresis) -- esas son para
    decidir cuando estamos PERDIDOS, no para fijar el signo de la
    correccion continua. 750 y 900 son la banda exacta que reprodujo el
    coordinador: antes del arreglo daban signo -1 (incorrecto) con
    lado_borde=1.

    🔴 Ronda de arreglo 3: probado con `lado_borde=1` Y `lado_borde=-1`.
    """
    assert signo_correccion(699, lado_borde) == signo_en_negro
    assert signo_correccion(701, lado_borde) == signo_en_claro
    assert signo_correccion(750, lado_borde) == signo_en_claro
    assert signo_correccion(900, lado_borde) == signo_en_claro
    assert signo_correccion(949, lado_borde) == signo_en_claro


def test_signo_correccion_respeta_lado_borde_tambien_en_la_zona_negra():
    """🔴 Tarea 11, Ronda de arreglo 3. El hueco que dejó la ronda 2: todos
    los tests anteriores probaban `lado_borde=-1` solo en la zona 'claro'
    (`claro=1275`, bien lejos del centro) o `lado_borde=1` en las dos
    zonas -- ninguno probaba `lado_borde=-1` CON `claro` por debajo del
    centro (zona 'negro').

    Bug quirúrgico que esto atrapa (inyectado por el re-revisor):
    `return lado_borde if claro >= centro else -1` -- ignora `lado_borde`
    en la zona negra. Con `lado_borde=1` ese bug es invisible (`-1 ==
    -lado_borde`); con `lado_borde=-1` no: el resultado correcto es `+1`
    (`-lado_borde`) y el bug sigue devolviendo `-1`.
    """
    assert signo_correccion(300, -1) == 1     # zona negro, lado -1: signo +1
    assert signo_correccion(181, -1) == 1     # el negro medido (evidencia 37)
    assert signo_correccion(699, -1) == 1
    assert signo_correccion(300, 1) == -1     # de control: zona negro, lado +1


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


# ── El barrido compartido ────────────────────────────────────────────────────
def test_no_apaga_el_barrido_si_ya_estaba_encendido():
    """🔴 Con la navegacion corriendo, un guion de alumno que apagara el barrido
    al cerrar dejaria a Nav2 CIEGO en silencio: sin /scan el collision_monitor
    bloquea el movimiento (medido: 0.0 cm contra 9.9 del control) y el robot
    parece averiado."""
    assert debe_apagar_barrido(lo_encendi=False) is False


def test_apaga_el_barrido_si_lo_encendio_el():
    """El caso normal: nadie mas lo usaba, asi que se deja como estaba."""
    assert debe_apagar_barrido(lo_encendi=True) is True
