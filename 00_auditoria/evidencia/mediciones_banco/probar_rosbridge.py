#!/usr/bin/env python3
"""¿Habla rosbridge? Cliente WebSocket mínimo, sin dependencias.

    python3 probar_rosbridge.py                 # contra el propio robot
    python3 probar_rosbridge.py --host rvr-01.local
    python3 probar_rosbridge.py --seg 20        # ventana más larga

No mueve el robot: solo se SUSCRIBE. Es la prueba de que la web podrá hablar con
el robot — el mismo camino exacto que usará el navegador.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ UN CLIENTE A MANO Y NO UNA LIBRERÍA
═══════════════════════════════════════════════════════════════════════════════
El robot no tiene `websockets` ni `websocket-client`, y **no conviene instalar
dependencias en los 16 robots solo para diagnosticar**. El handshake de WebSocket
son veinte líneas y el marcado de tramas de texto otras veinte, así que sale más
barato escribirlo que arrastrar un paquete a la imagen dorada.

═══════════════════════════════════════════════════════════════════════════════
LO QUE MIDE, Y ES EL NÚMERO QUE FALTABA
═══════════════════════════════════════════════════════════════════════════════
🔴 **rosbridge envía JSON, no binario.** La telemetría de un robot son
**42.2 kB/s** medidos en binario (evidencia 39), pero un `LaserScan` con 260
flotantes ocupa mucho más escrito como texto. Ese multiplicador es lo que decide
si 16 robots caben en un punto de acceso, y hasta ahora **nadie lo había medido**
porque rosbridge no estaba instalado.

Este script cuenta los bytes que salen de verdad por el WebSocket.
"""
import argparse
import base64
import json
import os
import socket
import struct
import sys
import time


def handshake(sock, host):
    clave = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((
        f"GET / HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {clave}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        b = sock.recv(1)
        if not b:
            raise ConnectionError('el servidor cerró durante el handshake')
        resp += b
    if b'101' not in resp.split(b'\r\n')[0]:
        raise ConnectionError(f'no aceptó el upgrade: {resp.splitlines()[0]!r}')


def enviar(sock, texto: str) -> None:
    """Trama de texto, FIN=1, opcode=1. El cliente SIEMPRE enmascara (RFC 6455)."""
    d = texto.encode()
    n = len(d)
    cab = bytearray([0x81])
    if n < 126:
        cab.append(0x80 | n)
    elif n < 65536:
        cab.append(0x80 | 126); cab += struct.pack('>H', n)
    else:
        cab.append(0x80 | 127); cab += struct.pack('>Q', n)
    m = os.urandom(4)
    cab += m
    cab += bytes(b ^ m[i % 4] for i, b in enumerate(d))
    sock.sendall(bytes(cab))


def recibir(sock):
    """Devuelve (payload_bytes, opcode) o None si se acabó."""
    def leer(n):
        out = b''
        while len(out) < n:
            c = sock.recv(n - len(out))
            if not c:
                return None
            out += c
        return out
    cab = leer(2)
    if not cab:
        return None
    op = cab[0] & 0x0F
    n = cab[1] & 0x7F
    if n == 126:
        n = struct.unpack('>H', leer(2))[0]
    elif n == 127:
        n = struct.unpack('>Q', leer(8))[0]
    return (leer(n) or b''), op


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--host', default='localhost')
    ap.add_argument('--puerto', type=int, default=9090)
    ap.add_argument('--seg', type=float, default=15.0)
    ap.add_argument('--topics', default='/odom,/scan,/battery_state')
    a = ap.parse_args()

    print('═' * 74)
    print(f'ROSBRIDGE — {a.host}:{a.puerto}')
    print('═' * 74)
    try:
        s = socket.create_connection((a.host, a.puerto), timeout=10)
        handshake(s, a.host)
    except Exception as e:                                  # noqa: BLE001
        print(f'  🔴 no se pudo conectar: {e}')
        print('     ¿corre el robot?  systemctl status atriz-robot')
        return 1
    print('  ✅ WebSocket establecido')

    topics = [t.strip() for t in a.topics.split(',') if t.strip()]
    for t in topics:
        enviar(s, json.dumps({'op': 'subscribe', 'topic': t}))
    print(f'  suscrito a: {", ".join(topics)}\n')

    cuenta = {t: [0, 0] for t in topics}      # [mensajes, bytes]
    s.settimeout(1.0)
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.seg:
        try:
            r = recibir(s)
        except socket.timeout:
            continue
        except Exception:                                   # noqa: BLE001
            break
        if r is None:
            break
        datos, op = r
        if op == 0x8:
            print('  ! el servidor cerró la conexión')
            break
        if op != 0x1:
            continue
        try:
            m = json.loads(datos)
        except Exception:                                   # noqa: BLE001
            continue
        t = m.get('topic')
        if t in cuenta:
            cuenta[t][0] += 1
            cuenta[t][1] += len(datos)
    dur = time.monotonic() - t0
    s.close()

    print(f'{"topic":18s} {"Hz":>7s} {"bytes/msg":>10s} {"kB/s":>8s}')
    print('─' * 48)
    tot = 0.0
    for t, (n, by) in cuenta.items():
        if not n:
            print(f'{t:18s}      —   (sin mensajes)')
            continue
        kbs = by / dur / 1024
        tot += kbs
        print(f'{t:18s} {n/dur:7.2f} {by/n:10.0f} {kbs:8.1f}')
    print('─' * 48)
    print(f'{"TOTAL":18s} {"":7s} {"":10s} {tot:8.1f} kB/s')
    print(f'\n  x16 robots  ->  {tot*16/1024:.2f} MB/s  =  {tot*16*8/1024:.1f} Mbit/s')
    print('\n  📝 Compara con los 42.2 kB/s BINARIOS de la evidencia 39: la')
    print('     diferencia es el coste de JSON, y es el número que decide si 16')
    print('     robots caben en un punto de acceso.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
