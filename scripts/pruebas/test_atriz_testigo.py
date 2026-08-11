"""La logica del testigo de la Fase B. Sin robot, sin red y sin tornado.

🔴 LAS QUE IMPORTAN SON LAS NEGATIVAS.

Un proxy que deja pasar TODO supera sin despeinarse las pruebas positivas: se
conecta, los datos llegan, el ancho de banda es el mismo. Lo que distingue un
proxy que autentica de uno decorativo es que RECHACE — sin testigo, con testigo
de otro robot, y con la firma manipulada.

Este proyecto tiene ocho falsos positivos documentados en su propio verificador,
todos de la misma familia: comprobaciones que solo miraban el camino bueno.
"""

import base64
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

cryptography = pytest.importorskip('cryptography')
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from atriz_testigo import (  # noqa: E402
    CIERRE_OTRO_ROBOT, CIERRE_RELOJ, CIERRE_TESTIGO_MALO, verificar,
)


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


@pytest.fixture(scope='module')
def par():
    priv = Ed25519PrivateKey.generate()
    return priv, priv.public_key()


def firmar(priv, **campos) -> str:
    """Emite un testigo como lo hara el servidor de Next."""
    cuerpo = {'sub': 'ana', 'rob': 7, 'iat': int(time.time()),
              'exp': int(time.time()) + 3600, **campos}
    cab = b64u(json.dumps({'alg': 'EdDSA', 'typ': 'JWT'}).encode())
    cue = b64u(json.dumps(cuerpo).encode())
    firma = priv.sign(f'{cab}.{cue}'.encode())
    return f'{cab}.{cue}.{b64u(firma)}'


@pytest.fixture(autouse=True)
def reloj_sincronizado(monkeypatch):
    """El reloj se da por bueno salvo en la prueba que lo mira.

    🔴 Sin esto TODAS pasarian por la rama del reloj y ninguna probaria la
    firma — un falso verde perfecto, y de los dificiles de ver.
    """
    import atriz_testigo
    monkeypatch.setattr(atriz_testigo, 'reloj_fiable', lambda: True)


# ═══════════════════════════════════════════════════════════════════════════
# El camino bueno. Va primero para que el resto signifique algo: si esto no
# pasara, los rechazos de abajo podrian ser «rechaza siempre».
# ═══════════════════════════════════════════════════════════════════════════
def test_un_testigo_bueno_pasa(par):
    priv, pub = par
    v = verificar(firmar(priv), 7, pub)
    assert v.ok, v.motivo
    assert v.sujeto == 'ana'


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 LOS TRES RECHAZOS
# ═══════════════════════════════════════════════════════════════════════════
def test_firma_manipulada_no_pasa(par):
    """El fallo clasico de esta clase de codigo: leer el JWT sin verificarlo."""
    priv, pub = par
    cab, cue, _ = firmar(priv).split('.')
    # Firma de otra clave: bien formada, y ajena.
    otra = Ed25519PrivateKey.generate()
    falsa = b64u(otra.sign(f'{cab}.{cue}'.encode()))
    v = verificar(f'{cab}.{cue}.{falsa}', 7, pub)
    assert not v.ok
    assert v.codigo == CIERRE_TESTIGO_MALO


def test_cuerpo_manipulado_no_pasa(par):
    """Cambiar el robot en el cuerpo invalida la firma, que es el punto."""
    priv, pub = par
    cab, _, firma = firmar(priv, rob=7).split('.')
    cue_falso = b64u(json.dumps({'sub': 'ana', 'rob': 3,
                                 'exp': int(time.time()) + 3600}).encode())
    v = verificar(f'{cab}.{cue_falso}.{firma}', 3, pub)
    assert not v.ok
    assert v.codigo == CIERRE_TESTIGO_MALO


def test_testigo_de_otro_robot_no_pasa(par):
    """El requisito 1 entero: un alumno con el robot 7 no abre el 3."""
    priv, pub = par
    v = verificar(firmar(priv, rob=7), 3, pub)
    assert not v.ok
    assert v.codigo == CIERRE_OTRO_ROBOT
    # Y el motivo dice los DOS numeros: sin eso, «no autorizado» manda a mirar
    # la sesion en vez de la pestana equivocada.
    assert '7' in v.motivo and '3' in v.motivo


def test_caducado_no_pasa(par):
    priv, pub = par
    v = verificar(firmar(priv, exp=int(time.time()) - 7200), 7, pub)
    assert not v.ok
    assert 'caducado' in v.motivo


def test_sin_exp_no_pasa(par):
    """Un testigo sin caducidad seria eterno. No se acepta 'por defecto'."""
    priv, pub = par
    cuerpo = {'sub': 'ana', 'rob': 7}
    cab = b64u(json.dumps({'alg': 'EdDSA'}).encode())
    cue = b64u(json.dumps(cuerpo).encode())
    firma = b64u(priv.sign(f'{cab}.{cue}'.encode()))
    v = verificar(f'{cab}.{cue}.{firma}', 7, pub)
    assert not v.ok


def test_basura_no_revienta(par):
    """Nada de lo que llegue por el cable puede tumbar el proxy."""
    _, pub = par
    for malo in ['', 'a', 'a.b', 'a.b.c.d', '...', 'no-es-un-jwt']:
        v = verificar(malo, 7, pub)
        assert not v.ok, malo


# ═══════════════════════════════════════════════════════════════════════════
# 🔴🔴 EL RELOJ — la trampa que un diseno generico se comeria
# ═══════════════════════════════════════════════════════════════════════════
def test_sin_reloj_sincronizado_NO_valida_tiempos(par, monkeypatch):
    """La Pi NO tiene RTC: arranca hasta 19,5 h en el pasado (evidencia 85).

    Validar un `exp` contra ese reloj rechazaria TODOS los testigos buenos, en
    los primeros segundos tras encender y sin ninguna pista. El proxy cierra con
    un motivo que se puede leer, en vez de decir «no autorizado».
    """
    import atriz_testigo
    monkeypatch.setattr(atriz_testigo, 'reloj_fiable', lambda: False)
    priv, pub = par
    v = verificar(firmar(priv), 7, pub)
    assert not v.ok
    assert v.codigo == CIERRE_RELOJ
    assert 'hora' in v.motivo          # explicable, no un codigo a secas


def test_sin_reloj_el_robot_equivocado_SE_RECHAZA_IGUAL(par, monkeypatch):
    """🔴 El orden importa: el robot se comprueba ANTES que el reloj.

    Si el reloj sin sincronizar cortocircuitara antes, un testigo del robot 7
    abriria el 3 durante los ~18 s posteriores a cada encendido — y los 16
    robots arrancan a la vez al empezar la clase.
    """
    import atriz_testigo
    monkeypatch.setattr(atriz_testigo, 'reloj_fiable', lambda: False)
    priv, pub = par
    v = verificar(firmar(priv, rob=7), 3, pub)
    assert not v.ok
    assert v.codigo == CIERRE_OTRO_ROBOT


def test_la_clave_publica_no_sirve_para_firmar(par):
    """Por eso es asimetrica: una microSD robada no emite testigos.

    Con HMAC compartido, sacar una tarjeta de las 16 permitiria firmar para las
    otras quince.
    """
    _, pub = par
    assert not hasattr(pub, 'sign')
