#!/usr/bin/env python3
"""Proxy autenticador de la Fase B. Va DELANTE de rosbridge, en cada robot.

════════════════════════════════════════════════════════════════════════════
🔴🔴 NADA DE ESTE FICHERO ESTÁ EJECUTADO NI MEDIDO
════════════════════════════════════════════════════════════════════════════
Escrito desde el PC el 2026-08-10, sin robot donde instalarlo. En este proyecto
eso NO es un cierre: es código con un plan al lado. El protocolo de verificación
—con su control negativo en cada punto— está en
`00_auditoria/planes/2026-08-10-fase-b-proxy.md`, apartado 7.

**Las tres comprobaciones que importan son las NEGATIVAS**: sin testigo, con
testigo de otro robot, y con la firma manipulada. Un proxy que deja pasar todo
supera igual de bien las positivas.

════════════════════════════════════════════════════════════════════════════
QUÉ HACE
════════════════════════════════════════════════════════════════════════════
    navegador ──9443── proxy ──127.0.0.1:9090── rosbridge

rosbridge 2.7.0 **no tiene autenticación**: `rosauth` no es dependencia, no
existe el parámetro `authenticate`, y `check_origin()` devuelve `True`
incondicionalmente. Así que la identidad no se le puede añadir: se le pone
delante, y se le quita la red (`address: 127.0.0.1`).

════════════════════════════════════════════════════════════════════════════
POR QUÉ TORNADO Y NO otra cosa
════════════════════════════════════════════════════════════════════════════
Porque **ya está en el robot**: `rosbridge_server` depende de él. Este proyecto
tiene cinco dependencias en la web y lo considera un valor; el robot merece lo
mismo. La única biblioteca nueva es `cryptography`, para verificar Ed25519.

⚠️ **Y esa sí hay que comprobarla en la Pi**: `python3 -c "import cryptography"`.
   Si no estuviera, es un `apt install python3-cryptography` en `provision.sh`,
   no un cambio de diseño.

════════════════════════════════════════════════════════════════════════════
🔴 EL TESTIGO VIAJA EN EL SUBPROTOCOLO, Y NO ES UN CAPRICHO
════════════════════════════════════════════════════════════════════════════
El navegador **no puede poner cabeceras en un WebSocket** —no hay API—, así que
`Authorization: Bearer …` está descartado. De ahí viene el «token en el
WebSocket es imposible» del CLAUDE.md, que dicho así es **demasiado fuerte**:
lo imposible es la cabecera, y que *rosbridge* consuma un testigo. Quedan dos
vías, y se elige la que no se filtra:

    subprotocolo   new WebSocket(url, ['atriz.v1', 'atriz.token.' + jwt])
    consulta       wss://…/?t=<jwt>     <- acaba en registros e historial

⚠️ **La trampa del subprotocolo, y es de las de este proyecto:** si el servidor
   **no devuelve** uno de los ofrecidos, el navegador cierra él mismo con 1006 y
   **sin motivo** — la firma de «no llego», otra vez. Por eso
   `select_subprotocol` devuelve `atriz.v1` SIEMPRE, incluso cuando se va a
   rechazar: primero se abre, y luego se cierra CON MOTIVO.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.websocket import websocket_connect

# ── Constantes, y de dónde sale cada una ────────────────────────────────────

from atriz_testigo import (                    # noqa: E402
    CIERRE_OTRO_ROBOT, CIERRE_RELOJ, CIERRE_SIN_TESTIGO, CIERRE_TESTIGO_MALO,
    PREFIJO_TESTIGO, SUBPROTOCOLO, reloj_fiable, verificar,
)


class Puente(tornado.websocket.WebSocketHandler):
    """Un cliente autenticado, y su conexión gemela contra rosbridge."""

    def initialize(self, robot: int, clave_publica, destino: str):
        self.robot = robot
        self.clave_publica = clave_publica
        self.destino = destino
        self.arriba = None          # la conexión hacia rosbridge
        self.cola: list = []        # lo que llegue antes de que el puente esté

    def check_origin(self, origin: str) -> bool:
        """El origen NO autentica, y por eso no se usa como si lo hiciera.

        🔴 Es exactamente lo que hace rosbridge (`return True`) y lo que hace
        que no proteja nada. Un `Origin` lo pone el navegador y lo falsifica
        cualquier cliente que no lo sea. **Quien autentica es el testigo.**
        Filtrar por origen aquí daría una sensación de cierre sin cerrar nada.
        """
        return True

    def select_subprotocol(self, subprotocols):
        """Guarda el testigo y **devuelve siempre** el subprotocolo.

        🔴 Devolver `None` hace que el navegador cierre con 1006 y sin motivo:
        la firma de «no llego», que en este proyecto ya costó doce segundos de
        cuelgue sin error ni cierre. Se abre siempre y se cierra con motivo.
        """
        self.testigo = ''
        for s in subprotocols or []:
            if s.startswith(PREFIJO_TESTIGO):
                self.testigo = s[len(PREFIJO_TESTIGO):]
        return SUBPROTOCOLO

    async def open(self):
        if not self.testigo:
            return self.close(CIERRE_SIN_TESTIGO, 'no traes testigo: inicia sesión en la web')

        v = verificar(self.testigo, self.robot, self.clave_publica)
        if not v.ok:
            print(f'[proxy] RECHAZADO {v.codigo} · {v.motivo}', flush=True)
            return self.close(v.codigo, v.motivo)

        print(f'[proxy] admitido «{v.sujeto}» en el robot {self.robot}', flush=True)
        try:
            self.arriba = await websocket_connect(
                self.destino, on_message_callback=self._de_rosbridge,
            )
        except Exception as e:                                 # noqa: BLE001
            # rosbridge caído es un problema DEL ROBOT, y se dice así: si se
            # devolviera «no autorizado», se mandaría a mirar la sesión.
            return self.close(1011, f'no puedo hablar con rosbridge: {e}')

        for m in self.cola:
            self.arriba.write_message(m)
        self.cola.clear()

    def on_message(self, mensaje):
        # 🔴 Puede llegar ANTES de que el puente esté hecho: `open()` es una
        #    corrutina y tornado sigue entregando mientras espera. Sin la cola
        #    se perderían las primeras órdenes —y la primera suele ser el
        #    `subscribe`, así que el síntoma sería «este topic no llega».
        if self.arriba is None:
            self.cola.append(mensaje)
        else:
            self.arriba.write_message(mensaje)

    def _de_rosbridge(self, mensaje):
        if mensaje is None:
            return self.close(1011, 'rosbridge cerró la conexión')
        try:
            self.write_message(mensaje, binary=isinstance(mensaje, bytes))
        except tornado.websocket.WebSocketClosedError:
            pass

    def on_close(self):
        if self.arriba is not None:
            self.arriba.close()


def main() -> int:
    p = argparse.ArgumentParser(description='Proxy autenticador delante de rosbridge')
    p.add_argument('--robot', type=int, required=True, help='número de ESTE robot, 1..16')
    p.add_argument('--puerto', type=int, default=9443)
    p.add_argument('--destino', default='ws://127.0.0.1:9090')
    p.add_argument('--clave-publica', default='/etc/atriz/testigo.pub',
                   help='clave Ed25519 pública en PEM. NUNCA la privada')
    p.add_argument('--cert', default='', help='certificado TLS. Sin él habla ws:// en claro')
    p.add_argument('--clave-tls', default='')
    a = p.parse_args()

    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    ruta = Path(a.clave_publica)
    if not ruta.exists():
        print(f'🔴 no existe {ruta}. Sin clave pública no se puede verificar nada.')
        return 1
    clave = load_pem_public_key(ruta.read_bytes())

    app = tornado.web.Application([
        (r'/', Puente, dict(robot=a.robot, clave_publica=clave, destino=a.destino)),
    ])

    ssl_ctx = None
    if a.cert and a.clave_tls:
        import ssl
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(a.cert, a.clave_tls)
    else:
        # ⚠️ SIN TLS EL TESTIGO VIAJA EN CLARO. Quien esté en la WiFi del aula
        #    puede copiarlo y usarlo hasta que caduque. La Fase B sin TLS cierra
        #    los requisitos 1 y 2 contra el error honesto y contra el curioso,
        #    NO contra alguien escuchando el aire. Se avisa al arrancar en vez
        #    de dejarlo en un documento.
        print('⚠️  sin TLS: el testigo viaja EN CLARO. Requisito 4 SIN cubrir.', flush=True)

    app.listen(a.puerto, ssl_options=ssl_ctx)
    esquema = 'wss' if ssl_ctx else 'ws'
    print(f'[proxy] robot {a.robot} · {esquema}://0.0.0.0:{a.puerto} -> {a.destino}', flush=True)
    if not reloj_fiable():
        print('⚠️  el reloj aún no está sincronizado: se rechazará hasta que lo esté.', flush=True)
    tornado.ioloop.IOLoop.current().start()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
