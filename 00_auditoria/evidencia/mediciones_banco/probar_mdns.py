#!/usr/bin/env python3
"""¿Responde un robot a su nombre `.local`?  Consulta mDNS sin instalar nada.

    python3 probar_mdns.py                  # busca rvr-01.local
    python3 probar_mdns.py rvr-07.local
    python3 probar_mdns.py --flota 16       # barre rvr-01 .. rvr-16: quién está vivo

No toca el robot ni el RVR: solo manda un paquete UDP al grupo multicast.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE, Y POR QUÉ NO USA UNA LIBRERÍA
═══════════════════════════════════════════════════════════════════════════════
Con 16 robots, «¿cuáles están encendidos?» es la pregunta de todos los días. Y la
respuesta no puede depender de saberse 16 direcciones IP de memoria.

📝 `zeroconf` y `avahi-utils` lo harían en dos líneas, pero **habría que
   instalarlos en los 16 robots** para poder diagnosticar. Un diagnóstico que
   exige desplegar software no sirve el día que hay una avería. Esto es DNS
   crudo sobre UDP multicast: 100 líneas y cero dependencias.

═══════════════════════════════════════════════════════════════════════════════
LA TRAMPA QUE ESTE SCRIPT EXISTE PARA VER
═══════════════════════════════════════════════════════════════════════════════
🔴 `ping rvr-01.local` desde Windows respondió con `fe80::da3a:...%10` — una
   dirección **IPv6 link-local**, no la IPv4 del robot. El ping funciona y aun
   así la respuesta no dice lo que parece:

     · link-local solo vale **dentro del mismo segmento de red**, y arrastra un
       índice de zona (`%10`) que es local al PC que pregunta.
     · que conteste la AAAA **no prueba** que publique también la A (IPv4).

   Por eso aquí se piden **las dos** por separado y se enseñan las dos. Si un día
   la web no conecta pero el `ping` va, la diferencia estará en esta salida.
"""
import argparse
import random
import socket
import struct
import sys
import time

GRUPO, PUERTO = '224.0.0.251', 5353
TIPOS = {1: 'A', 28: 'AAAA'}


def _codificar(nombre: str) -> bytes:
    out = b''
    for parte in nombre.rstrip('.').split('.'):
        out += bytes([len(parte)]) + parte.encode()
    return out + b'\0'


def _saltar_nombre(datos: bytes, i: int) -> int:
    while i < len(datos):
        n = datos[i]
        if n == 0:
            return i + 1
        if n & 0xC0:           # puntero de compresión: 2 bytes y se acabó
            return i + 2
        i += 1 + n
    return i


def consultar(nombre: str, espera: float = 2.0) -> dict:
    """Devuelve {'A': [...], 'AAAA': [...]}. Pregunta por los dos tipos."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    s.bind(('', 0))
    s.settimeout(0.3)

    tid = random.randint(0, 0xFFFF)
    for qtype in (1, 28):
        # cabecera: id, flags=0 (consulta), 1 pregunta, 0 respuestas
        q = struct.pack('!6H', tid, 0, 1, 0, 0, 0)
        q += _codificar(nombre) + struct.pack('!2H', qtype, 1)
        s.sendto(q, (GRUPO, PUERTO))

    hallado = {'A': [], 'AAAA': []}
    t0 = time.monotonic()
    while time.monotonic() - t0 < espera:
        try:
            datos, _ = s.recvfrom(9000)
        except socket.timeout:
            continue
        if len(datos) < 12:
            continue
        _, flags, nq, nr, _, _ = struct.unpack('!6H', datos[:12])
        if not (flags & 0x8000) or nr == 0:      # solo respuestas
            continue
        i = 12
        for _ in range(nq):                      # saltar la sección de preguntas
            i = _saltar_nombre(datos, i) + 4
        for _ in range(nr):
            i = _saltar_nombre(datos, i)
            if i + 10 > len(datos):
                break
            tipo, _, _, rdlen = struct.unpack('!HHIH', datos[i:i + 10])
            i += 10
            rdata = datos[i:i + rdlen]
            i += rdlen
            try:
                if tipo == 1 and rdlen == 4:
                    v = socket.inet_ntop(socket.AF_INET, rdata)
                elif tipo == 28 and rdlen == 16:
                    v = socket.inet_ntop(socket.AF_INET6, rdata)
                else:
                    continue
            except OSError:
                continue
            if v not in hallado[TIPOS[tipo]]:
                hallado[TIPOS[tipo]].append(v)
    s.close()
    return hallado


def _informar(nombre: str, r: dict) -> bool:
    a, aaaa = r['A'], r['AAAA']
    ll = [x for x in aaaa if x.lower().startswith('fe80')]
    if not a and not aaaa:
        print(f'  🔴 {nombre:18s} sin respuesta')
        return False
    print(f'  ✅ {nombre:18s} A={",".join(a) or "—":16s} AAAA={",".join(aaaa) or "—"}')
    if not a:
        print('       🔴 NO publica IPv4. La web tendrá que ir por IPv6.')
    if ll and not a:
        print('       🔴 y la AAAA es link-local: solo funciona en el mismo segmento.')
    return bool(a or aaaa)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('nombre', nargs='?', default='rvr-01.local')
    ap.add_argument('--flota', type=int, metavar='N',
                    help='barre rvr-01.local .. rvr-NN.local')
    ap.add_argument('--espera', type=float, default=2.0)
    a = ap.parse_args()

    print('═' * 74)
    print('mDNS — ¿responden los robots a su nombre .local?')
    print('═' * 74)
    if a.flota:
        vivos = 0
        for n in range(1, a.flota + 1):
            if _informar(f'rvr-{n:02d}.local', consultar(f'rvr-{n:02d}.local', a.espera)):
                vivos += 1
        print(f'\n  {vivos} de {a.flota} robots responden')
        return 0
    ok = _informar(a.nombre, consultar(a.nombre, a.espera))
    print('\n  📝 Desde el propio robot, su nombre responde SIEMPRE (se contesta a sí')
    print('     mismo). La prueba que vale es desde OTRA máquina.')
    print('═' * 74)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
