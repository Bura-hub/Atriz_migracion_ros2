#!/usr/bin/env python3
"""¿EXIGE ESTE ROBOT UN TESTIGO PARA ABRIR rosbridge? — Fase B (A7).

    python3 scripts/sistema/comprobar_testigo_rosbridge.py

Lo llama `verificar_robot.sh`. Corre en el robot, sin `sudo` y sin mover nada.

═══════════════════════════════════════════════════════════════════════════════
🔴🔴 POR QUÉ NO SE PUEDE COMPROBAR DESDE 127.0.0.1, QUE ES LO NATURAL
═══════════════════════════════════════════════════════════════════════════════
Porque el parche **exime a localhost a propósito** (ver `rosbridge_nucleo.py`:
quien corre dentro de la Pi ya alcanza `raw_motors` con `rclpy`, así que exigirle
testigo no cerraría nada y en cambio dejaría muertas las herramientas de banco).

Consecuencia: un verificador que conectara a `ws://127.0.0.1:9090` **vería
"aceptado" siempre**, exija el robot testigo o no. Sería exactamente la clase de
comprobación que este proyecto persigue —una que no puede fallar—, y van doce en
este guion.

Así que se conecta a la **dirección de red del propio robot**, que no está
exenta. Y se hacen las DOS, que es lo que lo convierte en una medida:

    desde la IP de red, SIN testigo   ->  tiene que RECHAZAR (4401)
    desde 127.0.0.1,    SIN testigo   ->  tiene que ACEPTAR  (la exención vive)

Sin la segunda, «rechaza» pasaría igual con un rosbridge caído. Sin la primera,
«acepta» pasaría igual con un robot abierto de par en par.
"""

from __future__ import annotations

import base64
import os
import re
import socket
import struct
import subprocess
import sys

PUERTO = int(os.environ.get('ATRIZ_PUERTO_ROSBRIDGE', '9090'))
#: Los mismos de `atriz_testigo.py`. Aquí solo se reconocen, no se deciden.
CIERRE_SIN_TESTIGO = 4401


def ip_de_red() -> str | None:
    """La IPv4 no-loopback de este robot.

    📝 Con un UDP que no manda nada: es la forma de preguntarle al sistema qué
       dirección usaría para salir, sin depender de `ip`, `hostname -I` ni de
       cuántas interfaces haya.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        d = s.getsockname()[0]
        s.close()
        return None if d.startswith('127.') else d
    except OSError:
        return None


def tocar(host: str, timeout: float = 6.0) -> tuple[str, int, str]:
    """Abre SIN testigo y dice qué pasó.

    @return (`'abierto'` | `'rechazado'` | `'sin_apreton'` | `'sin_red'`,
             código de cierre o 0, detalle)
    """
    try:
        s = socket.create_connection((host, PUERTO), timeout=timeout)
    except OSError as e:
        return ('sin_red', 0, str(e))

    try:
        clave = base64.b64encode(os.urandom(16)).decode()
        s.send(f'GET / HTTP/1.1\r\nHost: {host}:{PUERTO}\r\n'
               f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
               f'Sec-WebSocket-Key: {clave}\r\n'
               f'Sec-WebSocket-Version: 13\r\n\r\n'.encode())
        resp = s.recv(4096)
        if b'101' not in resp[:20]:
            return ('sin_apreton', 0, repr(resp[:80]))

        # 🔴 El rechazo llega DESPUÉS del apretón: un cierre con motivo no cabe
        #    antes. Por eso aquí se espera un marco, y no basta con el 101.
        s.settimeout(timeout)
        try:
            marco = s.recv(4096)
        except (socket.timeout, TimeoutError):
            return ('abierto', 0, 'el apretón pasó y nadie cerró')
        if not marco:
            return ('abierto', 0, 'el otro lado cerró el socket sin marco')

        # ¿Es un marco de cierre (0x8)? Los dos primeros bytes de su carga son
        # el código, big-endian.
        if (marco[0] & 0x0f) == 0x08 and len(marco) >= 4:
            n = marco[1] & 0x7f
            codigo = struct.unpack('>H', marco[2:4])[0]
            motivo = marco[4:2 + n].decode('utf-8', 'ignore')
            return ('rechazado', codigo, motivo)
        return ('abierto', 0, 'llegó un marco de datos: la sesión está viva')
    finally:
        try:
            s.close()
        except OSError:
            pass


#: 🔴🔴 ANCLADO AL PRINCIPIO DE LÍNEA, Y NO UN `in` SOBRE EL FICHERO ENTERO.
#:
#: La primera versión buscaba la cadena suelta y **contó un COMENTARIO como si
#: fuera un ajuste**: el propio `robot.launch.py` lleva, dentro del bloque que
#: explica cómo activar la Fase B, la línea de ejemplo comentada. Resultado
#: medido en rvr-01: dijo FALLO «rosbridge acepta sin testigo» sobre un robot
#: que no tenía por qué exigirlo.
#:
#: 📌 Es la TERCERA vez que este proyecto cuenta un comentario como un ajuste, y
#:    la regla ya estaba escrita en CLAUDE.md por las dos anteriores: **ancla al
#:    principio de línea y a la sintaxis exacta**.
_CABLE = re.compile(r"^\s*package='atriz_rvr_bringup',\s*executable='atriz_rosbridge\.py'")


def cableado() -> bool:
    """¿Está el launch apuntando al lanzador con testigo?

    ⚠️ Esto SÍ es mirar la intención y no el efecto, y se usa **solo para
       decidir la severidad**: sin cablear, «no exige testigo» es lo esperado y
       no un fallo. El efecto lo miden las dos conexiones de arriba.
    """
    for base in (os.path.expanduser('~/atriz_ws/src/Atriz_rvr'),
                 os.environ.get('ATRIZ_RVR', '')):
        if not base:
            continue
        ruta = os.path.join(base, 'atriz_rvr_bringup', 'launch', 'robot.launch.py')
        try:
            with open(ruta, encoding='utf8') as f:
                return any(_CABLE.match(l) for l in f)
        except OSError:
            continue
    return False


def salida_de_emergencia_puesta() -> bool:
    """¿Alguien dejó `ATRIZ_ROSBRIDGE_SIN_TESTIGO=1` en el servicio?

    Es la puerta trasera del lanzador, y existe para no tener que entrar por SSH
    a 16 robots si el parche se rompe. **Una salida de emergencia que nadie ve es
    una puerta trasera**, así que se busca en el entorno REAL del proceso.
    """
    try:
        pid = subprocess.run(['pgrep', '-f', 'atriz_rosbridge|rosbridge_websocket'],
                             capture_output=True, text=True, timeout=5).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return False
    for p in pid:
        try:
            with open(f'/proc/{p}/environ', 'rb') as f:
                if b'ATRIZ_ROSBRIDGE_SIN_TESTIGO=1' in f.read():
                    return True
        except OSError:
            continue
    return False


def main() -> int:
    ip = ip_de_red()
    if ip is None:
        print('AVISO no encuentro una IPv4 de red: sin ella no se puede comprobar '
              'el testigo (desde 127.0.0.1 la exención lo taparía)')
        return 0

    if salida_de_emergencia_puesta():
        print('FALLO ATRIZ_ROSBRIDGE_SIN_TESTIGO=1 en el entorno de rosbridge: '
              'este robot NO pide credencial a nadie · quítalo del servicio')
        return 1

    estado_red, codigo, motivo = tocar(ip)
    estado_local, _, _ = tocar('127.0.0.1')
    con_cable = cableado()

    if estado_red == 'sin_red':
        print(f'AVISO no pude conectar a ws://{ip}:{PUERTO} ({motivo}): '
              '¿está corriendo atriz-robot?')
        return 0

    if not con_cable:
        print(f'INFO este robot NO exige testigo todavía: robot.launch.py sigue '
              f'lanzando el rosbridge normal (Fase B sin cablear). Desde la red: '
              f'{estado_red}')
        return 0

    # Cableado: ahora las dos direcciones son exigibles.
    if estado_red != 'rechazado' or codigo != CIERRE_SIN_TESTIGO:
        print(f'FALLO rosbridge ACEPTA sin testigo desde la red ({ip}): '
              f'{estado_red} {codigo} {motivo} · cualquiera en el aula puede '
              'teleoperar este robot')
        return 1
    if estado_local != 'abierto':
        print(f'FALLO la exención de localhost no funciona ({estado_local}): '
              'las herramientas de banco del robot dejarán de servir')
        return 1

    print(f'OK rosbridge exige testigo desde la red ({ip} → {codigo}) y exime a '
          'localhost')
    return 0


if __name__ == '__main__':
    sys.exit(main())
