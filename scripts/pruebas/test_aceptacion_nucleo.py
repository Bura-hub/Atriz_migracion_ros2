import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aceptacion_nucleo import (
    PASA, REVISAR, FALLO, PENDIENTE,
    Resultado, juzgar_banda, juzgar_categorico, no_verificado,
)


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
