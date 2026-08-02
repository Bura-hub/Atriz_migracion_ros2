#!/usr/bin/env python3
"""¿La lista blanca de rosbridge deniega de verdad, y deja pasar lo que debe?

    python3 probar_lista_blanca.py                  # contra localhost
    python3 probar_lista_blanca.py --host rvr-01.local

⚠️ NO MUEVE EL ROBOT a propósito. Los comandos de movimiento que manda son de
   velocidad CERO: lo que se comprueba es si rosbridge los deja pasar, no qué
   hace el robot con ellos.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ ESTA HERRAMIENTA TIENE QUE EXISTIR
═══════════════════════════════════════════════════════════════════════════════
🔴 **ROSBRIDGE DENIEGA EN SILENCIO.** Cuando un topic o un servicio no está en la
   lista blanca, registra un `warn` en SU log y hace `return` — **no manda
   respuesta de error al cliente** (`capabilities/call_service.py:109-113`,
   `publish.py:96-99`, `subscribe.py:296-299`).

   Consecuencia: una lista blanca mal puesta **se manifiesta como «la web no
   responde»**, no como un fallo. Y este proyecto lleva toda la migración pagando
   esa clase de error.

🔴 Y de ahí sale el problema de método de esta prueba: **«no llegó respuesta» es
   la señal esperada de una denegación, pero también es lo que se ve si el
   servicio está roto, si el driver está caído o si el nombre está mal escrito.**
   Los dos casos son indistinguibles mirando solo lo denegado.

   → Por eso cada comprobación de denegación va acompañada de un **CONTROL**: un
     servicio o topic que SÍ está en la lista y que **tiene que responder**. Si
     el control tampoco responde, la prueba no concluye nada y lo dice, en vez de
     cantar victoria porque «no pasó nada».

═══════════════════════════════════════════════════════════════════════════════
QUÉ COMPRUEBA
═══════════════════════════════════════════════════════════════════════════════
  DEBE RECHAZAR   raw_motors · move_timed · publicar en /cmd_vel · leer /rosout
  DEBE PERMITIR   /odom · /battery_state · publicar en cmd_vel_raw ·
                  /start_scan · /set_pos_and_yaw · rosapi

📝 `/cmd_vel` merece una explicación: es la **salida** del collision_monitor.
   Publicar ahí funciona y **salta la capa de seguridad entera** sin ningún
   aviso, así que es el agujero más silencioso de los que cierra la lista.
"""
import argparse
import base64
import json
import os
import socket
import struct
import sys
import time

VERDE, ROJO, AMAR, GRIS, FIN = '\033[92m', '\033[91m', '\033[93m', '\033[90m', '\033[0m'


class Puente:
    """Cliente WebSocket mínimo contra rosbridge, sin dependencias.

    📝 A mano y no con `websockets` a propósito: es el mismo criterio que el
       resto de herramientas de este proyecto y que `probar_conexion_web.html`.
       Una dependencia menos que instalar en 16 robots.
    """

    def __init__(self, host, puerto=9090, timeout=6.0):
        self.s = socket.create_connection((host, puerto), timeout=timeout)
        clave = base64.b64encode(os.urandom(16)).decode()
        self.s.send(f'GET / HTTP/1.1\r\nHost: {host}:{puerto}\r\n'
                    f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                    f'Sec-WebSocket-Key: {clave}\r\n'
                    f'Sec-WebSocket-Version: 13\r\n\r\n'.encode())
        resp = self.s.recv(4096)
        if b'101' not in resp[:20]:
            raise RuntimeError(f'el handshake falló: {resp[:80]!r}')
        self.resto = b''

    def enviar(self, obj):
        d = json.dumps(obj).encode()
        cab = bytearray([0x81])
        m = os.urandom(4)
        if len(d) < 126:
            cab.append(0x80 | len(d))
        elif len(d) < 65536:
            cab.append(0x80 | 126)
            cab += struct.pack('>H', len(d))
        else:
            cab.append(0x80 | 127)
            cab += struct.pack('>Q', len(d))
        cab += m + bytes(b ^ m[i % 4] for i, b in enumerate(d))
        self.s.send(bytes(cab))

    def recibir(self, segundos):
        """Devuelve la lista de mensajes JSON recibidos en esa ventana."""
        fin = time.monotonic() + segundos
        fuera = []
        while time.monotonic() < fin:
            self.s.settimeout(max(0.1, fin - time.monotonic()))
            try:
                trozo = self.s.recv(65536)
            except (socket.timeout, TimeoutError):
                break
            if not trozo:
                break
            self.resto += trozo
            # Desenmarcado mínimo: el servidor no enmascara, y aquí solo llegan
            # tramas de texto. Basta con localizar los JSON completos.
            texto = self.resto.decode('utf-8', 'ignore')
            for pieza in texto.split('{"op"'):
                if not pieza.strip():
                    continue
                try:
                    fuera.append(json.loads('{"op"' + pieza[:pieza.rindex('}') + 1]))
                except Exception:                                # noqa: BLE001
                    pass
            self.resto = b''
        return fuera

    def cerrar(self):
        try:
            self.s.close()
        except Exception:                                        # noqa: BLE001
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--puerto', type=int, default=9090)
    a = ap.parse_args()          # argparse lo primero: `--help` no toca nada

    print('═' * 74)
    print(f'LISTA BLANCA DE ROSBRIDGE — {a.host}:{a.puerto}')
    print('═' * 74)

    try:
        p = Puente(a.host, a.puerto)
    except Exception as e:                                       # noqa: BLE001
        print(f'{ROJO}🔴 no se pudo conectar: {e}{FIN}')
        print('   ¿corre el robot? systemctl is-active atriz-robot')
        return 1
    print(f'{VERDE}  ✅ handshake WebSocket{FIN}\n')

    fallos, avisos = [], []

    # ── 1. EL CONTROL, ANTES QUE NADA ────────────────────────────────────────
    # 🔴 Si esto no llega, NADA de lo de abajo concluye: no se puede distinguir
    #    «rosbridge deniega» de «aquí no funciona nada».
    # 🔴 DOS CONTROLES, Y EL ORDEN IMPORTA. El primero que se intentó fue
    #    `/odom`, y falló la primera vez que se corrió esto — no por la lista
    #    blanca, sino porque **el RVR estaba apagado cargando**, un estado que va
    #    a ser habitual con 16 robots. Un control que solo vale con el robot
    #    encendido deja la herramienta inservible justo cuando más cómodo es
    #    tocar la configuración.
    #    → El control BUENO es `rosapi`: responde con el RVR apagado, porque no
    #      depende de él. `/odom` se conserva como control ADICIONAL, y su
    #      ausencia degrada la prueba en vez de abortarla.
    print(f'{GRIS}── control: ¿responde rosbridge a lo permitido? ────────{FIN}')
    p.enviar({'op': 'call_service', 'id': 'c0', 'service': '/rosapi/topics',
              'args': {}})
    control_ok = any(m.get('id') == 'c0' for m in p.recibir(8))
    if control_ok:
        print(f'{VERDE}  ✅ rosapi responde — el control es válido{FIN}')
    else:
        print(f'{ROJO}  🔴 rosapi NO responde.{FIN}')
        print('     ⚠️ SIN CONTROL LA PRUEBA NO CONCLUYE NADA: una denegación y un')
        print('        rosbridge roto se ven exactamente igual desde aquí.')
        print('     ¿está levantado `rosapi_node`?  ros2 node list | grep rosapi')
        p.cerrar()
        return 2

    p.enviar({'op': 'subscribe', 'topic': '/odom',
              'type': 'nav_msgs/msg/Odometry'})
    llega_odom = any(m.get('topic') == '/odom' for m in p.recibir(6))
    if llega_odom:
        print(f'{VERDE}  ✅ /odom llega — telemetría comprobable{FIN}')
    else:
        print(f'{AMAR}  ⚠️ /odom no llega. NO es un fallo de la lista blanca si el{FIN}')
        print(f'{AMAR}     RVR está apagado (cargando). Las comprobaciones que{FIN}')
        print(f'{AMAR}     dependen de telemetría quedan NO VERIFICADAS.{FIN}')
        avisos.append('/odom sin comprobar: ¿RVR apagado?')
    p.enviar({'op': 'unsubscribe', 'topic': '/odom'})

    # ── 2. LO QUE DEBE RECHAZARSE ────────────────────────────────────────────
    print(f'\n{GRIS}── debe RECHAZAR ──────────────────────────────────────{FIN}')

    prohibidos = [
        ('raw_motors', 'servicio', {
            'op': 'call_service', 'id': 'p1', 'service': '/raw_motors',
            'args': {'left_mode': 0, 'left_speed': 0,
                     'right_mode': 0, 'right_speed': 0}}),
        ('move_timed', 'servicio', {
            'op': 'call_service', 'id': 'p2', 'service': '/move_timed',
            'args': {'linear': 0.0, 'angular': 0.0, 'duration': 0.1}}),
    ]
    for nombre, clase, msg in prohibidos:
        p.enviar(msg)
        respuestas = [m for m in p.recibir(4)
                      if m.get('op') == 'service_response' and m.get('id') == msg['id']]
        if respuestas:
            print(f'{ROJO}  🔴 {nombre}: RESPONDIÓ. La lista blanca NO lo bloquea{FIN}')
            fallos.append(nombre)
        else:
            print(f'{VERDE}  ✅ {nombre}: sin respuesta (rechazado){FIN}')

    # Publicar en /cmd_vel: el agujero más silencioso, porque salta el
    # collision_monitor entero y el robot obedece.
    p.enviar({'op': 'advertise', 'topic': '/cmd_vel',
              'type': 'geometry_msgs/msg/Twist'})
    p.enviar({'op': 'publish', 'topic': '/cmd_vel',
              'msg': {'linear': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                      'angular': {'x': 0.0, 'y': 0.0, 'z': 0.0}}})
    p.recibir(2)
    print(f'{AMAR}  ⚠️ /cmd_vel: publicado sin error — es lo esperado, rosbridge{FIN}')
    print(f'{AMAR}     NUNCA responde a un publish. Se comprueba abajo, de otra forma.{FIN}')
    avisos.append('/cmd_vel exige comprobación por el log del servidor')

    # ── 3. LO QUE DEBE PERMITIRSE ────────────────────────────────────────────
    print(f'\n{GRIS}── debe PERMITIR ──────────────────────────────────────{FIN}')

    permitidos = [
        ('/start_scan', {'op': 'call_service', 'id': 'a1',
                         'service': '/start_scan', 'args': {}}),
        # 🔴 Los campos REALES, leidos con `ros2 interface show`. La primera
        #    version mandaba {'x','y','yaw'} planos y rosbridge respondia
        #    `NonexistentFieldException: ... does not have a field x`.
        ('/set_pos_and_yaw', {'op': 'call_service', 'id': 'a2',
                              'service': '/set_pos_and_yaw',
                              'args': {'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                                       'yaw': 0.0}}),
    ]
    for nombre, msg in permitidos:
        p.enviar(msg)
        # 🔴🔴 NO BASTA CON QUE LLEGUE UNA RESPUESTA. La primera version hacia
        #    exactamente eso, y dio ✅ sobre un `set_pos_and_yaw` que habia
        #    respondido con **NonexistentFieldException** porque los campos que
        #    le mandaba estaban mal. O sea: la herramienta que existe para cazar
        #    falsos positivos tenia uno dentro.
        #    → rosbridge marca el fracaso con `result: false` y, cuando el error
        #      es de tipo, manda `op: 'status'` con `level: 'error'` en vez de un
        #      `service_response`. Se miran las dos cosas.
        respuestas = p.recibir(8)
        errores = [m for m in respuestas
                   if m.get('op') == 'status' and m.get('level') == 'error']
        buenas = [m for m in respuestas
                  if m.get('op') == 'service_response' and m.get('id') == msg['id']
                  and m.get('result') is not False]
        if buenas and not errores:
            print(f'{VERDE}  ✅ {nombre}: responde y acepta{FIN}')
        elif errores:
            print(f'{ROJO}  🔴 {nombre}: respondio con ERROR — no es la lista{FIN}')
            print(f'{ROJO}     blanca, es la llamada: {errores[0].get("msg","")[:90]}{FIN}')
            fallos.append(f'{nombre} (error de llamada)')
        else:
            print(f'{ROJO}  🔴 {nombre}: NO responde — la lista blanca lo está{FIN}')
            print(f'{ROJO}     bloqueando, y la web lo necesita{FIN}')
            fallos.append(nombre)

    print(f'{VERDE}  ✅ rosapi: ya comprobado arriba como control{FIN}')

    p.cerrar()

    # ── veredicto ────────────────────────────────────────────────────────────
    print('\n' + '═' * 74)
    if fallos:
        print(f'{ROJO}  🔴 LA LISTA BLANCA NO ESTÁ BIEN: {", ".join(fallos)}{FIN}')
    else:
        print(f'{VERDE}  ✅ La lista blanca deniega lo prohibido y deja pasar lo{FIN}')
        print(f'{VERDE}     necesario.{FIN}')
    print()
    print('  ⚠️ Y ESTO NO BASTA. Quedan dos cosas que esta herramienta NO puede')
    print('     comprobar sola, y hay que hacerlas a mano:')
    print()
    print('  1. Que el LOG DEL SERVIDOR registre las denegaciones. Un publish')
    print('     nunca responde, así que la única prueba de que /cmd_vel se')
    print('     bloqueó está ahí:')
    print('       journalctl -u atriz-robot --since "-2 min" | grep -i "not allowed\\|glob"')
    print()
    print('  2. 🔴 QUE EL ROBOT NO SE MUEVA. Que no llegue respuesta NO prueba')
    print('     que la orden no pasara. Con el RVR encendido y espacio libre,')
    print('     manda `raw_motors` con velocidad real y MIRA EL ROBOT.')
    print('     Es el único instrumento que no se puede enredar.')
    print('═' * 74)
    return 1 if fallos else 0


if __name__ == '__main__':
    raise SystemExit(main())
