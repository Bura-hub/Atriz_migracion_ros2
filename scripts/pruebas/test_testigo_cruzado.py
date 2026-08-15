"""EL CRUCE: un testigo emitido por la WEB, verificado por el PYTHON del robot.

🔴 POR QUE ESTA PRUEBA VALE MAS QUE LAS OTRAS DIEZ.

`test_atriz_testigo.py` firma con `cryptography` y verifica con `cryptography`:
comprueba que este fichero es coherente CONSIGO MISMO. Y del otro lado,
`testigo_robot.test.ts` firma con `node:crypto` y verifica con `node:crypto`.

**Las dos pasarian con el contrato roto.** Si Next pusiera `exp` en
milisegundos, o cambiara el orden de las claves de la cabecera —lo firmado es el
TEXTO, no el objeto—, cada lado seguiria contento y el fallo aparecería en la Pi,
la primera vez que un alumno pulsara Ejecutar en el aula.

Lo unico que cruza de verdad es un testigo REAL emitido por uno y verificado por
el otro. Eso es lo que hay aqui.

⚠️ EL FICHERO DE EJEMPLO VIVE EN EL OTRO REPOSITORIO
   (`atriz-lab/herramientas/testigo_ejemplo.json`), porque lo emite quien firma.
   Si no esta —en el robot no lo esta— la prueba se SALTA diciendolo. Saltarse
   una prueba por no encontrar su material es honesto; darla por buena no.
"""

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

cryptography = pytest.importorskip('cryptography')
from cryptography.hazmat.primitives.serialization import load_pem_public_key  # noqa: E402

import atriz_testigo  # noqa: E402
from atriz_testigo import CIERRE_OTRO_ROBOT, CIERRE_TESTIGO_MALO, verificar  # noqa: E402


#: Se busca al lado del repositorio, que es como estan los dos en el PC. Con la
#: variable ATRIZ_TESTIGO_EJEMPLO se puede apuntar a otro sitio.
def _ruta_ejemplo() -> Path:
    import os
    puesto = os.environ.get('ATRIZ_TESTIGO_EJEMPLO')
    if puesto:
        return Path(puesto)
    raiz = Path(__file__).resolve().parents[2]          # .../atriz_migracion
    return raiz.parent / 'atriz-lab' / 'herramientas' / 'testigo_ejemplo.json'


@pytest.fixture(scope='module')
def ejemplo():
    ruta = _ruta_ejemplo()
    if not ruta.is_file():
        pytest.skip(
            f'no esta el testigo de ejemplo en {ruta}. Lo emite la web con '
            '`node herramientas/emitir_testigo_ejemplo.mjs`; en el robot no existe.',
        )
    return json.loads(ruta.read_text(encoding='utf8'))


@pytest.fixture(scope='module')
def publica(ejemplo):
    return load_pem_public_key(ejemplo['clave_publica_pem'].encode('ascii'))


@pytest.fixture(autouse=True)
def reloj_congelado(monkeypatch, ejemplo):
    """El reloj se para en el instante en que se emitio el ejemplo.

    🔴 Sin esto la prueba se pondria roja SOLA a los diez minutos de emitir el
       fichero, una tarde cualquiera y sin que nadie hubiera roto nada — y una
       prueba que se rompe sola se acaba ignorando, que es peor que no tenerla.
    """
    monkeypatch.setattr(atriz_testigo, 'reloj_fiable', lambda: True)
    monkeypatch.setattr(time, 'time', lambda: float(ejemplo['emitido_s'] + 5))


def test_el_testigo_de_la_web_ABRE_su_robot(ejemplo, publica):
    """El cruce entero, en una linea: lo que firma Node lo verifica Python."""
    v = verificar(ejemplo['testigo'], ejemplo['robot'], publica)
    assert v.ok, v.motivo
    assert v.sujeto == ejemplo['sujeto']


def test_el_mismo_testigo_NO_abre_otro_robot(ejemplo, publica):
    """El control. Sin el, «abre» no distingue verificar de aceptar cualquier cosa."""
    otro = 1 if ejemplo['robot'] != 1 else 2
    v = verificar(ejemplo['testigo'], otro, publica)
    assert not v.ok
    assert v.codigo == CIERRE_OTRO_ROBOT


def test_una_firma_de_otra_pareja_NO_abre(ejemplo):
    """Y el control de la clave: la publica del fichero es la que manda."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    ajena = Ed25519PrivateKey.generate().public_key()
    v = verificar(ejemplo['testigo'], ejemplo['robot'], ajena)
    assert not v.ok
    assert v.codigo == CIERRE_TESTIGO_MALO


def test_tocar_UN_caracter_del_cuerpo_lo_invalida(ejemplo, publica):
    """🔴 El fallo clasico de esta clase de codigo es leer el JWT sin verificarlo.

    Aqui se cambia el robot dentro del cuerpo, que es lo que haria quien quisiera
    abrir otro robot con su propio testigo. La firma deja de cuadrar.
    """
    cab, cue, firma = ejemplo['testigo'].split('.')
    tocado = cue[:-1] + ('A' if cue[-1] != 'A' else 'B')
    v = verificar(f'{cab}.{tocado}.{firma}', ejemplo['robot'], publica)
    assert not v.ok
    assert v.codigo == CIERRE_TESTIGO_MALO


def test_los_campos_son_los_cuatro_acordados(ejemplo):
    """El contrato, mirado desde este lado.

    Si la web añade o quita un campo, esto lo dice aqui —en el repositorio del
    robot— en vez de en el aula.
    """
    import base64
    cue = ejemplo['testigo'].split('.')[1]
    cuerpo = json.loads(base64.urlsafe_b64decode(cue + '=' * (-len(cue) % 4)))
    assert sorted(cuerpo) == ['exp', 'iat', 'rob', 'sub']
    # 🔴 Y en SEGUNDOS: diez cifras. En milisegundos serian trece, y el testigo
    #    caducaria dentro de 50 000 años sin que nada se quejara.
    assert len(str(cuerpo['iat'])) == 10
    assert cuerpo['exp'] > cuerpo['iat']
