#!/usr/bin/env python3
"""LA LOGICA DEL TESTIGO. PURO: sin tornado, sin red, sin sockets.

════════════════════════════════════════════════════════════════════════════
POR QUE ESTA SEPARADO DEL PROXY
════════════════════════════════════════════════════════════════════════════
Porque es lo unico de la Fase B que se puede PROBAR sin robot, y separarlo es lo
que lo hace posible: `tornado` solo esta en la Pi —llega con rosbridge, que es
justo el argumento para usarlo— asi que un fichero que lo importe no se puede ni
cargar desde el PC.

Es el mismo patron que la web: la logica pura aparte del componente. Y aqui paga
igual, porque **las tres comprobaciones que importan son las NEGATIVAS** —sin
testigo, con testigo de otro robot, y con la firma manipulada— y todas viven
aqui.

🔴 Lo que sigue SIN medir es el proxy entero contra rosbridge de verdad. Ver
   `00_auditoria/planes/2026-08-10-fase-b-proxy.md`, apartado 7.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path


def _b64u(s: str) -> bytes:
    """Base64 de URL sin relleno, que es lo que usa JWT."""
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


#: Prefijo del subprotocolo que lleva el testigo.
PREFIJO_TESTIGO = 'atriz.token.'

#: El subprotocolo que el proxy SIEMPRE devuelve. Ver la nota de arriba: no
#: devolver ninguno hace que el navegador cierre con 1006 y sin motivo.
SUBPROTOCOLO = 'atriz.v1'

#: Códigos de cierre. Se usan del rango privado (4000-4999) salvo 1013, que es
#: «Try Again Later» del estándar y es exactamente lo que significa el reloj sin
#: sincronizar.
CIERRE_RELOJ = 1013
CIERRE_SIN_TESTIGO = 4401
CIERRE_TESTIGO_MALO = 4403
CIERRE_OTRO_ROBOT = 4404

#: Fichero que systemd-timesyncd crea al sincronizar. Es la comprobación EN VIVO
#: del reloj; `After=time-sync.target` en la unidad ordena el arranque pero no
#: garantiza que NTP haya contestado.
MARCA_RELOJ = Path('/run/systemd/timesync/synchronized')

#: 🔴 Margen de tolerancia del reloj, en segundos. NO es un número inventado:
#: con el reloj YA sincronizado, la deriva entre la Pi y el servidor es de
#: milisegundos. 60 s cubre eso con dos órdenes de margen sin abrir la puerta a
#: un testigo caducado de verdad, que dura una clase entera.
MARGEN_RELOJ_S = 60


class Veredicto:
    """El resultado de mirar un testigo. Nunca es un booleano suelto.

    🔴 Un booleano obligaría a inventar el motivo en el sitio equivocado, y este
    proyecto tiene medido lo que cuesta un rechazo sin explicación: el alumno va
    a buscar a un profesor en vez de esperar quince segundos.
    """

    def __init__(self, ok: bool, codigo: int = 0, motivo: str = '', sujeto: str = ''):
        self.ok = ok
        self.codigo = codigo
        self.motivo = motivo
        self.sujeto = sujeto


def reloj_fiable() -> bool:
    """¿Se puede validar un tiempo con el reloj de esta Pi?

    🔴🔴 LA PI NO TIENE RTC. Medido en este proyecto (evidencia 85): arranca con
    el reloj restaurado a la última marca guardada —hasta **19,5 h en el
    pasado**— y NTP lo salta hacia delante unos 18 s después.

    Validar un `exp` contra ese reloj **rechaza todos los testigos buenos**, en
    los primeros segundos tras encender y sin ninguna pista. Y un reloj
    adelantado haría lo contrario, que es peor.
    """
    return MARCA_RELOJ.exists()


def verificar(testigo: str, robot: int, clave_publica) -> Veredicto:
    """Comprueba firma, caducidad y a qué robot apunta.

    🔴 EL ORDEN IMPORTA Y NO ES CASUAL: **primero la firma**. Leer los campos de
    un JWT antes de verificarlo es el fallo clásico de esta clase de código —
    quien manipule el testigo decide lo que lees. Aquí no se mira ni un campo
    hasta que la firma cuadra.
    """
    from cryptography.exceptions import InvalidSignature

    partes = testigo.split('.')
    if len(partes) != 3:
        return Veredicto(False, CIERRE_TESTIGO_MALO, 'el testigo no tiene la forma de un JWT')

    cabecera_b64, cuerpo_b64, firma_b64 = partes
    try:
        firmado = f'{cabecera_b64}.{cuerpo_b64}'.encode('ascii')
        clave_publica.verify(_b64u(firma_b64), firmado)
    except InvalidSignature:
        return Veredicto(False, CIERRE_TESTIGO_MALO, 'la firma no es válida')
    except Exception as e:                                    # noqa: BLE001
        return Veredicto(False, CIERRE_TESTIGO_MALO, f'no se pudo verificar la firma: {e}')

    # Solo AHORA se mira el contenido.
    try:
        cuerpo = json.loads(_b64u(cuerpo_b64))
    except Exception:                                          # noqa: BLE001
        return Veredicto(False, CIERRE_TESTIGO_MALO, 'el cuerpo del testigo no es JSON')

    sujeto = str(cuerpo.get('sub', '?'))

    # ── El robot. Es el requisito 1 entero, y cabe en dos líneas ────────────
    # El robot no necesita saber nada de usuarios ni de reservas: le basta con
    # comparar un número con el suyo.
    pedido = cuerpo.get('rob')
    if pedido != robot:
        return Veredicto(
            False, CIERRE_OTRO_ROBOT,
            f'este testigo es para el robot {pedido}, y este es el {robot}', sujeto,
        )

    # ── La caducidad, solo si el reloj vale ─────────────────────────────────
    if not reloj_fiable():
        return Veredicto(
            False, CIERRE_RELOJ,
            'el robot aún no tiene la hora (no hay RTC y NTP no ha contestado). '
            'Espera unos segundos y vuelve a intentarlo', sujeto,
        )

    ahora = time.time()
    exp = cuerpo.get('exp')
    if not isinstance(exp, (int, float)):
        return Veredicto(False, CIERRE_TESTIGO_MALO, 'el testigo no dice cuándo caduca', sujeto)
    if ahora > exp + MARGEN_RELOJ_S:
        return Veredicto(False, CIERRE_TESTIGO_MALO, 'el testigo ha caducado', sujeto)

    iat = cuerpo.get('iat')
    if isinstance(iat, (int, float)) and iat > ahora + MARGEN_RELOJ_S:
        # Un testigo «del futuro» con el reloj YA sincronizado es una señal de
        # manipulación, no de deriva.
        return Veredicto(False, CIERRE_TESTIGO_MALO, 'el testigo dice haberse emitido en el futuro', sujeto)

    return Veredicto(True, sujeto=sujeto)


