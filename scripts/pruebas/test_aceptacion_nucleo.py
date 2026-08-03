import math
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from aceptacion_nucleo import (
    PASA, REVISAR, FALLO, PENDIENTE,
    Resultado, juzgar_banda, juzgar_categorico, no_verificado, delta_angulo,
)


# ── delta_angulo (D1: logica pura, la funcion que se colgaba con `inf`) ────

def test_delta_angulo_cero():
    assert delta_angulo(0.0, 0.0) == 0.0


def test_delta_angulo_media_vuelta_positiva():
    # a=0, b=pi: el limite superior del rango (-pi, pi] queda DENTRO.
    assert math.isclose(delta_angulo(0.0, math.pi), math.pi)


def test_delta_angulo_media_vuelta_negativa():
    # a=0, b=-pi es el MISMO angulo que +pi (equivalentes modulo 2*pi): la
    # normalizacion a (-pi, pi] los manda a los dos al mismo valor +pi.
    assert math.isclose(delta_angulo(0.0, -math.pi), math.pi)


def test_delta_angulo_nan_lanza_valueerror():
    with pytest.raises(ValueError):
        delta_angulo(float('nan'), 0.0)
    with pytest.raises(ValueError):
        delta_angulo(0.0, float('nan'))


def test_delta_angulo_inf_lanza_valueerror():
    # 🔴 Sin este rechazo, el `while d > math.pi: d -= 2*math.pi` de abajo NO
    #    TERMINA NUNCA con inf (inf - 2*pi sigue siendo inf) — verificado en su
    #    dia con `timeout 3`, salida 124. Es la razon de ser de esta funcion.
    with pytest.raises(ValueError):
        delta_angulo(float('inf'), 0.0)
    with pytest.raises(ValueError):
        delta_angulo(0.0, float('inf'))


def test_delta_angulo_menos_inf_lanza_valueerror():
    with pytest.raises(ValueError):
        delta_angulo(float('-inf'), 0.0)
    with pytest.raises(ValueError):
        delta_angulo(0.0, float('-inf'))


def test_delta_angulo_acumulado_una_vuelta_completa():
    # Simula lo que hace F5: acumular deltas de un yaw que atan2 solo entrega
    # en (-pi, pi], a lo largo de una vuelta ENTERA (360°) en pasos de 45°.
    # Sin la normalizacion de delta_angulo, la vuelta se leeria como ~0.
    def wrap(x):
        return math.atan2(math.sin(x), math.cos(x))

    pasos = [wrap(i * (2 * math.pi / 8)) for i in range(9)]     # 0..360° en 8 pasos
    acumulado = 0.0
    prev = pasos[0]
    for q in pasos[1:]:
        acumulado += delta_angulo(prev, q)
        prev = q
    assert math.isclose(math.degrees(acumulado), 360.0, abs_tol=1e-6)


def test_dentro_de_banda_pasa():
    r = juzgar_banda('move_timed 2 s', 30.3, 24.0, 37.0, 'evidencia 26: 30.3 cm', 'F4', 'cm')
    assert r.veredicto == PASA
    assert r.medido == 30.3


def test_fuera_de_banda_es_revisar_no_fallo():
    # 🔴 La regla que define esta prueba: con n=1 detras, un numero raro NO es
    #    un suspenso. Si esto se convierte en FALLO, el diseño esta roto.
    r = juzgar_banda('move_timed 2 s', 12.0, 24.0, 37.0, 'evidencia 26: 30.3 cm', 'F4', 'cm')
    assert r.veredicto == REVISAR


def test_los_extremos_de_la_banda_entran():
    assert juzgar_banda('x', 24.0, 24.0, 37.0, 'b', 'F4').veredicto == PASA
    assert juzgar_banda('x', 37.0, 24.0, 37.0, 'b', 'F4').veredicto == PASA


def test_valor_ausente_es_no_verificado_no_pasa():
    # Un None no puede colarse como aprobado: es justo el fallo que esta prueba
    # existe para evitar (un hueco leido como «bien»).
    r = juzgar_banda('ritmo de /odom', None, 13.0, 99.0, 'Fase 4: 16.5 Hz', 'F1', 'Hz')
    assert r.veredicto == PENDIENTE
    assert 'NO VERIFICADO' in r.detalle


def test_categorico_falso_es_fallo():
    r = juzgar_categorico('la parada de emergencia para', False, 'F4')
    assert r.veredicto == FALLO


def test_categorico_cierto_pasa():
    assert juzgar_categorico('nodo rvr_driver presente', True, 'F0').veredicto == PASA


def test_no_verificado_lleva_el_motivo():
    r = no_verificado('netplan 60-atriz.yaml', 'F0', 'necesita root')
    assert r.veredicto == PENDIENTE
    assert 'necesita root' in r.detalle


def test_el_detalle_dice_contra_que_se_comparo():
    r = juzgar_banda('collision_monitor', 22.0, 0.0, 15.0, 'CHANGELOG:1824: 9.9 cm', 'F6', 'cm')
    assert '22.0' in r.detalle and 'CHANGELOG:1824' in r.detalle


from aceptacion_nucleo import (
    PENDIENTES_CONOCIDOS, hay_via_libre, resumen, formatear_informe,
)


def test_sin_fallos_ni_pendientes_hay_via_libre():
    assert hay_via_libre([juzgar_categorico('x', True, 'F0')]) is True


def test_un_fallo_bloquea():
    assert hay_via_libre([juzgar_categorico('x', False, 'F0')]) is False


def test_revisar_solo_no_bloquea():
    r = juzgar_banda('x', 99.0, 0.0, 1.0, 'b', 'F4')
    assert r.veredicto == REVISAR
    assert hay_via_libre([r]) is True


def test_un_pendiente_bloquea():
    assert hay_via_libre([no_verificado('x', 'F0', 'sin root')]) is False


def test_los_pendientes_conocidos_bloquean_una_pasada_perfecta():
    # 🔴 Consecuencia elegida a proposito: aunque el robot este impecable, la
    #    pasada NO da via libre mientras quede un pendiente abierto.
    #    📝 El comentario original decia «porque rosbridge sigue sin
    #       autenticacion», y eso se quedo desactualizado el mismo dia: la Fase A
    #       cerro `raw_motors`. Lo que bloquea ahora es la falta de IDENTIDAD POR
    #       USUARIO (Fase B). El test no cambia; la razon si.
    todo_bien = [juzgar_categorico('x', True, 'F0')]
    assert hay_via_libre(todo_bien) is True
    assert hay_via_libre(todo_bien + PENDIENTES_CONOCIDOS) is False


def test_rosbridge_sin_autenticacion_esta_entre_los_pendientes():
    assert any('rosbridge' in p.concepto.lower() for p in PENDIENTES_CONOCIDOS)


def test_resumen_cuenta_cada_veredicto():
    c = resumen([juzgar_categorico('a', True, 'F0'),
                 juzgar_categorico('b', False, 'F0'),
                 no_verificado('c', 'F0', 'm')])
    assert c[PASA] == 1 and c[FALLO] == 1 and c[PENDIENTE] == 1 and c[REVISAR] == 0


def test_el_informe_niega_la_via_libre_cuando_hay_fallo():
    txt = formatear_informe([juzgar_categorico('la parada para', False, 'F4')], 'cabecera')
    assert 'VIA LIBRE' not in txt.replace('NO HAY VIA LIBRE', '')
    assert 'la parada para' in txt


def test_el_informe_da_via_libre_cuando_todo_pasa():
    # 🔴 Las dos mitades hacen falta: 'VIA LIBRE PARA LA FASE 5' es subcadena de
    #    'NO HAY VIA LIBRE PARA LA FASE 5', asi que la comprobacion ingenua pasa
    #    con el informe diciendo lo CONTRARIO. Encontrado en revision.
    txt = formatear_informe([juzgar_categorico('x', True, 'F0')], 'cabecera')
    assert 'NO HAY VIA LIBRE' not in txt and 'VIA LIBRE PARA LA FASE 5' in txt
