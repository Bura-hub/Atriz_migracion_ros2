"""La decisión del vigía de DDS (evidencia 109: el mudo intermitente).

Lo que protege: que el vigía reinicie UNA sola vez por arranque y falle
ABIERTO — un robot mudo es malo; un robot latcheado por su propio vigía es
peor (StartLimitBurst=5/300 s: un ping-pong mudo→cura→mudo lo quemaría).
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'sistema'))

from vigia_dds import decidir, SANO, REINICIAR, RENDIRSE


def test_con_mensaje_es_sano():
    assert decidir(mensaje_llego=True, marca_existe=False) == SANO


def test_con_mensaje_y_marca_sigue_sano_y_no_rearma():
    # Decisión explícita: tras una cura, la marca SE QUEDA. Si el mudo
    # reapareciera más tarde en el MISMO arranque (nunca observado), el vigía
    # no vuelve a reiniciar — el rearme habilitaría el ping-pong que quema el
    # StartLimitBurst de atriz-robot.
    assert decidir(mensaje_llego=True, marca_existe=True) == SANO


def test_mudo_sin_marca_reinicia():
    assert decidir(mensaje_llego=False, marca_existe=False) == REINICIAR


def test_mudo_con_marca_se_rinde_fallando_abierto():
    # Ya se reinició una vez este arranque y sigue mudo: se deja corriendo y
    # se escribe a gritos. Nunca un segundo reinicio automático.
    assert decidir(mensaje_llego=False, marca_existe=True) == RENDIRSE
