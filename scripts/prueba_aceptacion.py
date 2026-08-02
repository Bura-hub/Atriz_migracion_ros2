#!/usr/bin/env python3
"""Prueba de aceptacion de un robot: de arranque en frio a navegacion autonoma.

    python3 prueba_aceptacion.py            # las diez fases
    python3 prueba_aceptacion.py --desde F4 # retomar sin repetir

⚠️ EL ROBOT SE MUEVE en F4, F5, F6 y F7, y enciende LEDs en F3. Es GUIADA: se
   para y te dice que hacer antes de cada fase fisica.

⛔ Ctrl-C en cualquier momento PARA EL ROBOT (parada de emergencia).

📎 Criterio, umbrales y por que de cada fase: 03_operacion/PRUEBA_ACEPTACION.md
"""
import argparse
import math
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from aceptacion_nucleo import (                                  # noqa: E402
    PASA, REVISAR, FALLO, PENDIENTE, PENDIENTES_CONOCIDOS, Resultado,
    juzgar_banda, juzgar_categorico, no_verificado,
    hay_via_libre, formatear_informe,
)

import rclpy                                                     # noqa: E402
from rclpy.node import Node                                      # noqa: E402
from rclpy.executors import SingleThreadedExecutor               # noqa: E402
from rclpy.qos import (QoSProfile, ReliabilityPolicy,            # noqa: E402
                       DurabilityPolicy)
from rclpy.signals import SignalHandlerOptions                   # noqa: E402
from std_msgs.msg import Empty                                   # noqa: E402
from std_srvs.srv import Empty as EmptySrv                       # noqa: E402

#: Umbral de aborto. 7.0 V es el «baja» que devuelve el FIRMWARE, verificado en
#: el journal el 2026-08-01. Por debajo, los motores dan menos y mediriamos una
#: regresion que no existe.
BATERIA_MINIMA_V = 7.0
#: Tope para «el servicio subio EN EL ARRANQUE». Medido: 23 s tras el boot
#: (evidencia 47). Con 120 s hay holgura de sobra, y si alguien lo levanto a mano
#: la diferencia serian minutos u horas, no segundos.
ARRANQUE_MAXIMO_S = 120.0

BE = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
FIABLE = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


def driver_corriendo() -> bool:
    """🔴 `ps -o comm` TRUNCA A 15 CARACTERES y `rvr_driver_node` mide 15 justos."""
    try:
        s = subprocess.run(['ps', '-eo', 'comm'], capture_output=True,
                           text=True, timeout=5)
        return any(c.startswith('rvr_driver_nod') for c in s.stdout.split())
    except Exception:                                            # noqa: BLE001
        return True                          # ante la duda, se asume que si


def matar_por_comm(prefijo: str) -> int:
    """Mata por nombre de proceso. 🔴 NUNCA `pkill -f`: su patron casa con la
    linea de comando entera, asi que alcanza a procesos que solo MENCIONAN el
    nombre — incluida esta misma prueba.

    🔴 Hallazgo de revisión (2026-08-02): hoy no colisiona —el `comm` de este
       proceso es `python3` y `rvr_driver_nod` no lo alcanza— pero la tarea 7
       reutiliza esto para matar SLAM y Nav2 con prefijos más genéricos, donde sí
       podría alcanzar a esta misma prueba o a su padre (el shell que la lanzó).
       Se excluyen los dos por PID, no por nombre: un `comm` truncado a 15
       caracteres puede coincidir por accidente.
    """
    n = 0
    propio, padre = os.getpid(), os.getppid()
    try:
        s = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True,
                           text=True, timeout=5)
        for linea in s.stdout.splitlines()[1:]:
            partes = linea.split(None, 1)
            if len(partes) != 2:
                continue
            pid = int(partes[0])
            if pid in (propio, padre):
                continue
            if partes[1].strip().startswith(prefijo[:15]):
                os.kill(pid, signal.SIGINT)
                n += 1
    except Exception:                                            # noqa: BLE001
        pass
    return n


class Aceptacion:
    def __init__(self, guiada=True):
        self.res: list[Resultado] = []
        self.guiada = guiada
        self._cerrado = False       # ver Aceptacion.cerrar(): la hace idempotente
        # 🔴🔴 `SignalHandlerOptions.NO` NO ES OPCIONAL, Y ES LO QUE HACE QUE LA
        #    PARADA DE EMERGENCIA FUNCIONE. `rclpy.init()` a secas instala su
        #    propio manejador de SIGINT que **invalida el contexto** antes de que
        #    el `except KeyboardInterrupt` llegue a publicar:
        #        RCLError: Failed to publish: publisher's context is invalid
        #    Medido el 2026-08-02 con el driver escuchando: por defecto **0
        #    lineas** de «PARADA DE EMERGENCIA» en el journal; con NO, **5**.
        #    ⚠️ Y es INTERMITENTE segun donde caiga el Ctrl-C, que es como paso la
        #       verificacion del 2026-08-01. Un fallo de seguridad que funciona a
        #       veces es peor que uno que no funciona nunca.
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        self.nodo = Node('prueba_aceptacion')
        self.ex = SingleThreadedExecutor()
        self.ex.add_node(self.nodo)
        self.parada_pub = self.nodo.create_publisher(Empty, 'emergency_stop', FIABLE)
        self.liberar = self.nodo.create_client(EmptySrv, 'release_emergency_stop')

    # ── registro ──────────────────────────────────────────────────────────
    def add(self, r: Resultado) -> Resultado:
        icono = {PASA: '  ok ', REVISAR: ' REV ', FALLO: 'FALLO', PENDIENTE: 'PEND '}
        print(f'    [{icono[r.veredicto]}] {r.concepto}')
        if r.detalle:
            print(f'            {r.detalle}')
        self.res.append(r)
        return r

    # ── puertas ───────────────────────────────────────────────────────────
    def puerta(self, texto: str) -> None:
        """Se para hasta que el usuario confirme. NO se salta nunca en las fases
        que mueven el robot: arrancar un motor con algo delante que nadie
        esperaba es como se rompen robots y dedos."""
        print('\n' + '─' * 74)
        print(f'  🔴 {texto}')
        print('─' * 74)
        if not self.guiada:
            print('     (--sin-puertas: se continua)')
            time.sleep(2)
            return
        # 🔴🔴 SIN TERMINAL, LA PUERTA NO PARABA NADA. `sys.stdin.readline()`
        #    devuelve '' AL INSTANTE cuando stdin no es interactivo (una tuberia,
        #    `nohup`, `< /dev/null`, o un agente lanzandolo desde una herramienta).
        #    O sea que la puerta que existe para que nadie arranque un motor con
        #    algo delante **se saltaba sola, en silencio**, justo en el modo que
        #    la pide. Encontrado el 2026-08-02 al ir a lanzar F4 en guiado.
        #    📝 Es el mismo patron que este proyecto lleva documentado media
        #       docena de veces: algo que devuelve sin error y no hace su trabajo.
        if not sys.stdin.isatty():
            print('\n  🔴 ABORTADO: modo guiado SIN TERMINAL INTERACTIVO.')
            print('     La puerta no puede pararse, asi que el robot se moveria')
            print('     sin que nadie hubiera confirmado nada. Ejecutalo tu en una')
            print('     terminal, o usa --sin-puertas si NO hay nadie delante y')
            print('     asumes el riesgo.')
            raise SystemExit(2)
        print('     Pulsa Enter cuando este listo (o Ctrl-C para abortar)…')
        sys.stdin.readline()

    # ── seguridad ─────────────────────────────────────────────────────────
    def parada_emergencia(self) -> None:
        """Publica la parada por el camino canonico y espera a que salga.

        🔴 `move_timed` y los demas servicios de movimiento corren EN EL DRIVER.
           Matar este proceso no para el robot: lo unico que lo corta es esto.
        """
        for _ in range(5):
            self.parada_pub.publish(Empty())
            self.ex.spin_once(timeout_sec=0.05)
        time.sleep(0.3)

    def liberar_parada(self) -> bool:
        if not self.liberar.wait_for_service(timeout_sec=5.0):
            return False
        fut = self.liberar.call_async(EmptySrv.Request())
        fin = time.monotonic() + 5.0
        while not fut.done() and time.monotonic() < fin:
            self.ex.spin_once(timeout_sec=0.05)
        return fut.done()

    # ── utilidades ────────────────────────────────────────────────────────
    def llamar(self, cliente, req, timeout=10.0):
        """🔴 TODA llamada lleva tope. Una sola sin el cuelga la prueba entera en
        silencio — paso con get_battery_percentage() el 2026-07-30."""
        if not cliente.wait_for_service(timeout_sec=timeout):
            return None
        fut = cliente.call_async(req)
        fin = time.monotonic() + timeout
        while not fut.done() and time.monotonic() < fin:
            self.ex.spin_once(timeout_sec=0.05)
        return fut.result() if fut.done() else None

    def esperar(self, topic, tipo, qos, segundos=5.0) -> list:
        """Recoge mensajes con el ejecutor PERSISTENTE.

        🔴 `rclpy.spin_once(nodo, ...)` en bucle PIERDE MENSAJES: engancha el nodo
           al ejecutor global y lo desengancha al salir, y en ese hueco se pierde
           lo que llegue. Dio 11.3 Hz sobre un robot que iba a 16.5.
        """
        buf = []
        sub = self.nodo.create_subscription(tipo, topic, lambda m: buf.append(m), qos)
        try:
            fin = time.monotonic() + segundos
            while time.monotonic() < fin:
                self.ex.spin_once(timeout_sec=0.05)
        finally:
            # 🔴 Hallazgo de revisión: si `spin_once` revienta, la version anterior
            #    dejaba la suscripcion colgando para siempre. La heredan `guardas()`,
            #    `ritmo()` y `pos_yaw()`, y las fases futuras que llamen a `esperar()`.
            self.nodo.destroy_subscription(sub)
        return buf

    def ritmo(self, topic, tipo, qos, segundos=5.0):
        """Hz reales: (n-1) intervalos entre el primer y el ultimo sello.

        🔴 `mensajes / duracion` SUBESTIMA: mete el descubrimiento de DDS en el
           denominador. Se mide entre el primer y el ultimo mensaje recibidos.
        """
        buf = self.esperar(topic, tipo, qos, segundos)
        if len(buf) < 3:
            return None
        t = [m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 for m in buf]
        span = t[-1] - t[0]
        return (len(t) - 1) / span if span > 0 else None

    def pos_yaw(self):
        """(x, y, yaw en radianes) de /odom. None si no llega nada."""
        from nav_msgs.msg import Odometry
        b = self.esperar('odom', Odometry, BE, 2.0)
        if not b:
            return None
        p, q = b[-1].pose.pose.position, b[-1].pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                         1 - 2 * (q.y ** 2 + q.z ** 2))
        return p.x, p.y, yaw

    def pos_yaw_rapido(self):
        """Solo el yaw del ultimo /odom ya recibido, SIN esperar.

        F5 tiene que muestrear mientras el robot gira: si llamara a pos_yaw()
        —que espera 2 s— se perderia el giro entero y el acumulado saldria mal.
        """
        from nav_msgs.msg import Odometry
        if not hasattr(self, '_sub_odom'):
            self._odom_buf = []
            self._sub_odom = self.nodo.create_subscription(
                Odometry, 'odom', lambda m: self._odom_buf.append(m), BE)
        if not self._odom_buf:
            return None
        q = self._odom_buf[-1].pose.pose.orientation
        return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))

    def cerrar(self):
        """Para el robot y libera rclpy.

        🔴 Hallazgo de revisión: IDEMPOTENTE a propósito. La ruta normal
           (`return ejecutar(...)`) y la de Ctrl-C pueden acabar llamándola las
           dos sobre el mismo objeto — mejor que sea seguro llamarla dos veces
           a intentar adivinar por qué rama se pasó.
        """
        if self._cerrado:
            return
        self._cerrado = True
        try:
            self.parada_emergencia()
            self.liberar_parada()
        except Exception:                                        # noqa: BLE001
            pass
        try:
            self.nodo.destroy_node()
            rclpy.shutdown()
        except Exception:                                        # noqa: BLE001
            pass


def delta_angulo(a, b) -> float:
    """b - a normalizado a (-pi, pi].

    🔴 Sin esto NO SE PUEDE MEDIR UN GIRO DE 360°: atan2 devuelve -pi..pi, asi que
       una vuelta entera se lee como ~0. F5 acumula estos deltas.

    🔴 Hallazgo de revisión: con `inf` el `while` de abajo NO TERMINA NUNCA
       (`inf - 2*pi` sigue siendo `inf`) — verificado con `timeout 3`, salida
       124. `nan` salía bien de casualidad (toda comparación con NaN es Falsa,
       así que ningún `while` llega a entrar). F5 llama a esto en un bucle
       acumulando, así que un solo yaw corrupto colgaba la fase entera sin
       ninguna traza. Se rechaza lo no finito ANTES de normalizar, con una
       excepción que el llamador pueda distinguir de un ángulo válido — devolver
       NaN se habría sumado en silencio sin que nadie lo notara.
    """
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError(f'delta_angulo recibió un valor no finito: a={a!r} b={b!r}')
    d = b - a
    while d > math.pi:
        d -= 2 * math.pi
    while d <= -math.pi:
        d += 2 * math.pi
    return d


def guardas(a: Aceptacion) -> str | None:
    """Devuelve el motivo de aborto, o None si se puede seguir."""
    if not driver_corriendo():
        return ('el driver no esta corriendo. Esta prueba lo necesita:\n'
                '     sudo systemctl start atriz-robot')

    # 🔴 35 s, NO 8. `/battery_state` se publica **cada 30 s exactos** (es el
    #    latido del keepalive), asi que una ventana de 8 s casi nunca ve un
    #    mensaje y la guarda abortaria por «no llega» con la bateria perfecta.
    #    Medido el 2026-08-02: **1 mensaje en 40 s, el primero a los 15.3 s**.
    from sensor_msgs.msg import BatteryState
    print('    esperando a /battery_state (se publica cada 30 s)…')
    b = a.esperar('battery_state', BatteryState, FIABLE, 35.0)
    if not b:
        return ('no llega /battery_state en 35 s. Sin saber la bateria no se mueve\n'
                '     nada. ¿Esta el driver publicando? journalctl -u atriz-robot -n 40')
    v = b[-1].voltage
    if v == v and v < BATERIA_MINIMA_V:     # v==v descarta NaN
        return (f'bateria a {v:.2f} V, por debajo de {BATERIA_MINIMA_V} V (umbral '
                f'«baja» del firmware).\n     Con la bateria caida los motores dan '
                f'menos y mediriamos una regresion que no existe. Cargalo.')
    print(f'    bateria {v:.2f} V · {b[-1].percentage * 100:.0f} %')
    return None


FASES = []          # se llena con @fase en las tareas 4-11


def fase(clave, titulo, mueve=False):
    def deco(fn):
        FASES.append((clave, titulo, mueve, fn))
        return fn
    return deco


NODOS_DEL_SERVICIO = ['rvr_driver', 'ydlidar_ros2_driver_node', 'collision_monitor',
                      'lifecycle_manager_seguridad', 'robot_state_publisher',
                      'rosbridge_websocket']


@fase('F0', 'Arranque en frio — ¿arranco solo?')
def f0(a: Aceptacion) -> None:
    # ── ¿el servicio subio SOLO, en el arranque y a la primera? ──
    # 🔴 NO se mira el uptime: eso CADUCA. Si preparar la prueba lleva media hora
    #    la comprobacion falla sin que nada este roto. Lo que se quiere probar se
    #    lee sin reloj — ver evidencia 47_arranque_en_frio_20260801.txt.
    up = float(open('/proc/uptime').read().split()[0])
    arranque = time.time() - up
    def _mostrar(prop):
        return subprocess.run(['systemctl', 'show', 'atriz-robot', '-p', prop,
                               '--value'], capture_output=True, text=True,
                              timeout=10).stdout.strip()
    activo_us = _mostrar('ActiveEnterTimestampMonotonic')     # us desde el boot
    retraso = float(activo_us) / 1e6 if activo_us.isdigit() else None
    a.add(juzgar_banda(
        'el servicio subio EN EL ARRANQUE (no lo levanto nadie)',
        None if retraso is None else round(retraso, 1), 0.0, ARRANQUE_MAXIMO_S,
        'evidencia 47: 23 s tras el boot', 'F0', 's'))
    print(f'    uptime {up / 60:.1f} min · boot {time.strftime("%H:%M:%S", time.localtime(arranque))}')

    n_re = _mostrar('NRestarts')
    # ⚠️ REVISAR y no FALLO: F0 deja este contador a 1 al ejercitar Restart=always,
    #    asi que una SEGUNDA pasada sobre el mismo arranque ya no vera 0. Las dos
    #    lecturas se dicen en el detalle; lo desempata el journal.
    a.add(Resultado('F0', 'el servicio subio a la primera (NRestarts)',
                    PASA if n_re == '0' else REVISAR,
                    f'NRestarts = {n_re}. Si no es 0: o es una repeticion de esta '
                    f'misma prueba (F0 mata el driver a proposito), o el driver se '
                    f'cayo de verdad. Lo desempata el journal'))

    # ── el servicio, sin que nadie lo tocara ──
    act = subprocess.run(['systemctl', 'is-active', 'atriz-robot'],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    a.add(juzgar_categorico('atriz-robot arranco solo', act == 'active', 'F0',
                            f'systemctl is-active = {act}'))

    # ── los seis nodos ──
    vivos = {n for n, _ in a.nodo.get_node_names_and_namespaces()}
    for n in NODOS_DEL_SERVICIO:
        a.add(juzgar_categorico(f'nodo {n}', n in vivos, 'F0',
                                '' if n in vivos else f'no esta. Vivos: {sorted(vivos)}'))

    # ── el journal, y SOLO AQUI ──
    # 🔴 Esta comprobacion NO puede repetirse al final: el driver registra la
    #    parada de emergencia con nivel ERROR, y F4 y F6 la provocan a proposito.
    #    Buscarla despues encontraria los errores que la propia prueba causo.
    j = subprocess.run(['journalctl', '-u', 'atriz-robot', '-p', 'err', '-b',
                        '--no-pager'], capture_output=True, text=True, timeout=20)
    errores = [l for l in j.stdout.splitlines()
               if l.strip() and not l.startswith('-- ')]
    a.add(juzgar_categorico(
        'journal sin errores desde el arranque', not errores, 'F0',
        '' if not errores else f'{len(errores)} linea(s): {errores[0][:110]}'))

    # ── las 105 comprobaciones estaticas ──
    v = subprocess.run(['bash', str(pathlib.Path.home() / 'atriz_migracion' /
                                    'scripts' / 'verificar_robot.sh')],
                       capture_output=True, text=True, timeout=300)
    malas = [l.strip() for l in v.stdout.splitlines() if l.strip().startswith('✗')]
    avisos = [l.strip() for l in v.stdout.splitlines() if l.strip().startswith('!')]
    a.add(juzgar_categorico('verificar_robot.sh sin fallos', not malas, 'F0',
                            f'{len(malas)} fallo(s); {len(avisos)} aviso(s). '
                            + (malas[0][:110] if malas else '')))
    for av in avisos:
        # ⚠️ Los avisos NO son FALLO. Se informan tal cual; los que son decisiones
        #    abiertas ya estan en PENDIENTES_CONOCIDOS y bloquean desde alli.
        a.add(Resultado('F0', f'aviso: {av[:90]}', REVISAR, ''))

    # ── Restart=always, documentado como SIN EJERCITAR ──
    pid0 = subprocess.run(['systemctl', 'show', 'atriz-robot', '-p', 'MainPID',
                           '--value'], capture_output=True, text=True,
                          timeout=10).stdout.strip()
    print(f'    ejercitando Restart=always (PID {pid0})… vuelve en ~40 s')
    try:
        os.kill(int(pid0), signal.SIGKILL)
    except Exception as e:                                       # noqa: BLE001
        a.add(no_verificado('Restart=always', 'F0', f'no se pudo matar el PID: {e}'))
        return
    fin = time.monotonic() + 90
    pid1 = pid0
    while time.monotonic() < fin:
        time.sleep(3)
        pid1 = subprocess.run(['systemctl', 'show', 'atriz-robot', '-p', 'MainPID',
                               '--value'], capture_output=True, text=True,
                              timeout=10).stdout.strip()
        if pid1 not in ('0', '', pid0) and driver_corriendo():
            break
    a.add(juzgar_categorico('Restart=always revive el driver',
                            pid1 not in ('0', '', pid0), 'F0',
                            f'PID {pid0} → {pid1}. Primera vez que se ejercita'))
    time.sleep(10)          # que el driver termine de suscribirse


@fase('F1', 'Telemetria — los sentidos del robot')
def f1(a: Aceptacion) -> None:
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu, BatteryState
    from atriz_rvr_msgs.msg import MotorStatus

    for topic, tipo, lo, hi in [('odom', Odometry, 13.0, 25.0),
                                ('imu', Imu, 13.0, 25.0)]:
        a.add(juzgar_banda(f'ritmo de /{topic}', a.ritmo(topic, tipo, BE, 6.0),
                           lo, hi, 'Fase 4: 16.5 Hz', 'F1', 'Hz'))

    # 🔴 40 s, NO 8. Mismo fallo que ya se arreglo en `guardas()` y que aqui se
    #    quedo sin arreglar: `/battery_state` se publica **cada 30 s exactos**.
    #    📝 Es el patron que este proyecto tiene documentado: arreglar dos de tres
    #       llamadas deja el fallo intacto. Aqui costo TRES comprobaciones, no una:
    #       al no llegar el mensaje se saltaban EN SILENCIO la banda de voltaje y
    #       la de temperatura NaN, y el informe enseñaba un solo PENDIENTE donde
    #       deberia haber tres.
    #    ⚠️ Y son 40 y no 35 porque **F0 acaba de reiniciar el driver**: el nuevo
    #       proceso tarda en publicar su primera lectura. Medido el 2026-08-02:
    #       con 35 s justo despues de F0, NO llegaba.
    print('    esperando a /battery_state (cada 30 s, y el driver acaba de reiniciarse)…')
    b = a.esperar('battery_state', BatteryState, FIABLE, 40.0)
    if not b:
        a.add(no_verificado('/battery_state', 'F1',
                            'no llego ningun mensaje en 40 s. ⚠️ Con el se pierden '
                            'TAMBIEN la banda de voltaje y la de temperatura NaN'))
    else:
        m = b[-1]
        a.add(juzgar_banda('voltaje de bateria', round(m.voltage, 2),
                           6.5, 8.5, 'firmware: critica 6.50, baja 7.00', 'F1', 'V'))
        # 🔴 El RVR no da temperatura de BATERIA. Debe ser NaN, no 0.0: un 0.0
        #    es un dato, no un hueco, y la web lo pintaria como «bateria helada».
        a.add(juzgar_categorico('temperatura de bateria es NaN y no 0.0',
                                m.temperature != m.temperature, 'F1',
                                f'temperature = {m.temperature}'))

    ms = a.esperar('motor_status', MotorStatus, FIABLE, 35.0)   # se sondea cada 30 s
    if not ms:
        a.add(no_verificado('/motor_status', 'F1', 'nada en 35 s (se sondea cada 30)'))
    else:
        t = ms[-1]
        a.add(juzgar_banda('temperatura del motor izquierdo',
                           round(t.temperatura_izquierdo, 1), 10.0, 55.0,
                           'reposo medido: 27.5 / 28.3 °C', 'F1', '°C'))
        a.add(juzgar_categorico('en reposo no hay atasco ni fallo',
                                not (t.atascado_izquierdo or t.atascado_derecho
                                     or t.fallo), 'F1'))

    # ── deriva de yaw en reposo (NO valor absoluto: ver el diseño) ──
    p0 = a.pos_yaw()
    time.sleep(30)
    p1 = a.pos_yaw()
    if p0 and p1:
        d = abs(math.degrees(delta_angulo(p0[2], p1[2])))
        a.add(juzgar_banda('deriva de yaw en 30 s de reposo', round(d, 3),
                           0.0, 0.5, 'medido 2026-08-01: 0.01°/60 s', 'F1', '°'))
    else:
        a.add(no_verificado('deriva de yaw', 'F1', 'no llego /odom'))


@fase('F2', 'LIDAR — arranca, barre y para')
def f2(a: Aceptacion) -> None:
    from sensor_msgs.msg import LaserScan
    from std_srvs.srv import Empty as E

    arrancar = a.nodo.create_client(E, 'start_scan')
    parar = a.nodo.create_client(E, 'stop_scan')

    # El robot arranca CON EL BARRIDO APAGADO, por decision. Debe estar mudo.
    antes = a.esperar('scan', LaserScan, BE, 4.0)
    a.add(juzgar_categorico('arranca con el barrido APAGADO', not antes, 'F2',
                            f'{len(antes)} mensajes con el barrido parado'))

    a.add(juzgar_categorico('start_scan responde',
                            a.llamar(arrancar, E.Request(), 20.0) is not None, 'F2'))
    time.sleep(3)
    # 🔴 BANDA CORREGIDA, y la version anterior citaba una fuente EQUIVOCADA.
    #    Decia «manual cap. 12: 9.997 Hz · σ 0.35 ms» — pero esos 9.997 Hz son de
    #    `/prueba_atriz`, un topic SINTETICO de String publicado con
    #    `ros2 topic pub -r 10` para probar DDS. **No tienen nada que ver con el
    #    LIDAR.** La pista estaba a la vista: σ 0.35 ms es un jitter imposible
    #    para un motor que gira libre.
    #    📝 Lo destapo un subagente al medir 11.84 Hz y negarse a tocar la banda
    #       por su cuenta: dijo que dos fuentes del proyecto se contradecian.
    #    Las medidas REALES de /scan en este robot, las tres con el driver ROS 2:
    #        10.1 Hz  (2026-07-30)   12.00 Hz (2026-08-01)   11.84 Hz (2026-08-02)
    #    Varian porque **el motor del X2 va libre**: el proyecto ya tiene medido
    #    que su parametro `frequency` no hace nada. Por eso la banda es ancha.
    a.add(juzgar_banda('ritmo de /scan', a.ritmo('scan', LaserScan, BE, 8.0),
                       9.5, 13.0, 'medido: 10.1 · 11.84 · 12.00 Hz (el motor va libre)',
                       'F2', 'Hz'))

    b = a.esperar('scan', LaserScan, BE, 3.0)
    if b:
        s = b[-1]
        finitos = [r for r in s.ranges if math.isfinite(r) and r > 0]
        a.add(juzgar_categorico('el barrido trae rangos utiles',
                                len(finitos) > len(s.ranges) * 0.3, 'F2',
                                f'{len(finitos)}/{len(s.ranges)} finitos · '
                                f'min {min(finitos):.2f} max {max(finitos):.2f} m'
                                if finitos else 'NINGUN rango finito'))

    a.add(juzgar_categorico('stop_scan responde',
                            a.llamar(parar, E.Request(), 20.0) is not None, 'F2'))
    time.sleep(3)
    despues = a.esperar('scan', LaserScan, BE, 4.0)
    a.add(juzgar_categorico('stop_scan calla /scan de verdad', not despues, 'F2',
                            f'{len(despues)} mensajes DESPUES de parar'))

    # ── el parche contra la inundacion del journal ──
    n0 = len(subprocess.run(['journalctl', '-u', 'atriz-robot', '--since', '-20s',
                             '--no-pager'], capture_output=True, text=True,
                            timeout=20).stdout.splitlines())
    time.sleep(20)
    n1 = len(subprocess.run(['journalctl', '-u', 'atriz-robot', '--since', '-20s',
                             '--no-pager'], capture_output=True, text=True,
                            timeout=20).stdout.splitlines())
    a.add(juzgar_categorico('el parche del YDLIDAR aguanta (no inunda el journal)',
                            n1 < 60, 'F2',
                            f'{n1} lineas en 20 s con el barrido parado (antes del '
                            f'parche eran miles). Referencia previa: {n0}'))


@fase('F3', 'Luces — esta la confirmas TU con los ojos')
def f3(a: Aceptacion) -> None:
    from atriz_rvr_msgs.srv import SetLEDRGB, SetMultipleLEDs

    a.puerta('MIRA EL ROBOT. Voy a encender los LEDs en secuencia.\n'
             '     No hay forma de leer un LED desde el software: el robot no\n'
             '     tiene con que mirarse. Esta fase la juzgas tu.')

    rgb = a.nodo.create_client(SetLEDRGB, 'set_led_rgb')
    varios = a.nodo.create_client(SetMultipleLEDs, 'set_multiple_leds')

    TODAS = 11                    # 'all_lights' — rvr_driver_node.py:659
    respondieron = True
    for nombre, r, g, b in [('ROJO', 255, 0, 0), ('VERDE', 0, 255, 0),
                            ('AZUL', 0, 0, 255)]:
        print(f'    → todas en {nombre}')
        req = SetLEDRGB.Request()
        req.led_id, req.red, req.green, req.blue = TODAS, r, g, b
        resp = a.llamar(rgb, req, 8.0)
        if resp is None or not resp.success:
            respondieron = False
            print(f'      🔴 {getattr(resp, "message", "sin respuesta")}')
        time.sleep(2)

    a.add(juzgar_categorico('set_led_rgb responde con success', respondieron, 'F3'))

    # Los faros por separado: comprueba que led_id direcciona de verdad y no
    # enciende siempre lo mismo.
    print('    → faro IZQUIERDO rojo, faro DERECHO verde (a la vez)')
    req = SetMultipleLEDs.Request()
    req.led_ids = [0, 1]                     # headlight_left, headlight_right
    req.red_values, req.green_values, req.blue_values = [255, 0], [0, 255], [0, 0]
    resp = a.llamar(varios, req, 8.0)
    a.add(juzgar_categorico('set_multiple_leds responde con success',
                            resp is not None and resp.success, 'F3',
                            getattr(resp, 'message', 'sin respuesta')))
    time.sleep(3)

    if not a.guiada:
        a.add(no_verificado('los LEDs se encienden', 'F3', 'nadie estaba mirando'))
    else:
        print('\n    ¿Viste ROJO, VERDE y AZUL, y luego un faro de cada color?')
        print('    [s/N] ', end='', flush=True)
        visto = sys.stdin.readline().strip().lower() == 's'
        a.add(juzgar_categorico('los LEDs se encienden, cambian y se direccionan',
                                visto, 'F3', 'confirmado a ojo por el operador'))

    # Apagar: dejarlas encendidas gasta bateria y confunde a quien pase al lado.
    req = SetLEDRGB.Request()
    req.led_id, req.red, req.green, req.blue = TODAS, 0, 0, 0
    a.llamar(rgb, req, 8.0)


@fase('F4', 'Movimiento basico y parada de emergencia', mueve=True)
def f4(a: Aceptacion) -> None:
    from atriz_rvr_msgs.srv import MoveTimed

    a.puerta('PASILLO DESPEJADO y nadie delante del robot.\n'
             '     Va a avanzar ~30 cm, retroceder, y luego se le mandara una\n'
             '     parada de emergencia a mitad de un avance.')

    mv = a.nodo.create_client(MoveTimed, 'move_timed')

    def avanzar(v, seg):
        p0 = a.pos_yaw()
        req = MoveTimed.Request()
        req.linear, req.angular, req.duration = float(v), 0.0, float(seg)
        fut = mv.call_async(req)
        fin = time.monotonic() + seg + 4
        while time.monotonic() < fin:
            a.ex.spin_once(timeout_sec=0.05)
        p1 = a.pos_yaw()
        if not (p0 and p1):
            return None
        return math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 100      # cm

    if not mv.wait_for_service(timeout_sec=15.0):
        a.add(juzgar_categorico('move_timed responde', False, 'F4'))
        return

    d = avanzar(0.15, 2.0)
    a.add(juzgar_banda('move_timed 2 s a 0.15 m/s', None if d is None else round(d, 1),
                       24.0, 37.0, 'evidencia 26: 30.3 cm (101 %)', 'F4', 'cm'))
    time.sleep(2)

    d = avanzar(-0.15, 2.0)
    a.add(juzgar_banda('marcha atras 2 s a 0.15 m/s',
                       None if d is None else round(d, 1),
                       24.0, 37.0, 'simetrico a la ida', 'F4', 'cm'))
    time.sleep(2)

    # ── la parada de emergencia, a mitad de un avance ──
    print('    → parada de emergencia a mitad de un avance de 4 s…')
    p0 = a.pos_yaw()
    req = MoveTimed.Request()
    req.linear, req.angular, req.duration = 0.15, 0.0, 4.0
    mv.call_async(req)
    fin = time.monotonic() + 1.5
    while time.monotonic() < fin:
        a.ex.spin_once(timeout_sec=0.05)
    pm = a.pos_yaw()
    a.parada_emergencia()
    time.sleep(2.5)
    p1 = a.pos_yaw()
    if p0 and pm and p1:
        tras = math.hypot(p1[0] - pm[0], p1[1] - pm[1]) * 100
        a.add(juzgar_banda('recorrido DESPUES de la parada de emergencia',
                           round(tras, 1), 0.0, 12.0,
                           'watchdog: 527 ms · ~7.9 cm (CHANGELOG:3303)', 'F4', 'cm'))
    else:
        a.add(no_verificado('parada de emergencia', 'F4', 'no llego /odom'))

    # 🔴 Que la parada BLOQUEA los servicios, no solo que frena.
    req2 = MoveTimed.Request()
    req2.linear, req2.angular, req2.duration = 0.10, 0.0, 1.0
    r = a.llamar(mv, req2, 8.0)
    a.add(juzgar_categorico('con la parada activa, move_timed es rechazado',
                            r is not None and not r.success, 'F4',
                            f'success = {getattr(r, "success", "sin respuesta")}'))

    a.add(juzgar_categorico('release_emergency_stop devuelve el control',
                            a.liberar_parada(), 'F4'))


@fase('F5', 'ANGULOS — el hueco que nadie habia medido', mueve=True)
def f5(a: Aceptacion) -> None:
    """🔴 SIEMPRE Δyaw, NUNCA yaw absoluto.

    `reset_yaw()` no pone el yaw a cero (rvr_driver_node.py:316, medido el
    2026-07-31): solo se pone a cero AL ENCENDER EL RVR, y `sudo reboot` reinicia
    la Pi, no el RVR. El origen viene arrastrado de quien sabe cuando.

    📝 Y sin acumular deltas no se puede medir un giro de 360°: atan2 devuelve
       -pi..pi, asi que una vuelta entera se leeria como ~0.
    """
    from atriz_rvr_msgs.srv import MoveTimed

    a.puerta('ESPACIO PARA GIRAR EN EL SITIO. El robot no avanza, pero gira\n'
             '     90°, 180° y una vuelta entera. Aparta lo que tenga al lado.')

    mv = a.nodo.create_client(MoveTimed, 'move_timed')
    if not mv.wait_for_service(timeout_sec=15.0):
        a.add(juzgar_categorico('move_timed responde', False, 'F5'))
        return

    def girar(vel_rad_s, seg):
        """Gira y devuelve el Δyaw acumulado en grados (con signo)."""
        p = a.pos_yaw()
        if not p:
            return None, None
        prev, acum = p[2], 0.0
        req = MoveTimed.Request()
        req.linear, req.angular, req.duration = 0.0, float(vel_rad_s), float(seg)
        mv.call_async(req)
        fin = time.monotonic() + seg + 3
        while time.monotonic() < fin:
            a.ex.spin_once(timeout_sec=0.02)
            q = a.pos_yaw_rapido()
            if q is not None:
                # 🔴 Hallazgo de revision (task 6): delta_angulo() lanza ValueError
                #    ante un yaw no finito (nan/inf) A PROPOSITO — ver su docstring.
                #    F5 acumula en bucle, asi que dejar la excepcion sin coger
                #    abortaria la fase entera por UNA muestra corrupta de /odom.
                #    Se descarta la muestra (no se actualiza `prev`, no se suma
                #    nada) y se sigue muestreando: un solo dato malo no debe tirar
                #    un giro completo por la borda.
                try:
                    acum += delta_angulo(prev, q)
                    prev = q
                except ValueError:
                    pass
        p1 = a.pos_yaw()
        desliz = math.hypot(p1[0] - p[0], p1[1] - p[1]) * 100 if p1 else None
        return math.degrees(acum), desliz

    # 1.0 rad/s durante pi/2 s ≈ 90°. Se comanda por tiempo porque move_timed
    # toma velocidad y duracion, no un angulo: NO hay servicio «gira 90°».
    for grados, seg in [(90, math.pi / 2), (180, math.pi), (360, 2 * math.pi)]:
        print(f'    → izquierda {grados}°…')
        medido, desliz = girar(1.0, seg)
        if medido is None:
            a.add(no_verificado(f'giro de {grados}°', 'F5', 'no llego /odom'))
            continue
        # ⚠️ BANDA DE CORDURA, NO DE ACEPTACION: el angulo NUNCA se habia medido,
        #    asi que no hay base contra la que suspender. Esta pasada la fija.
        a.add(juzgar_banda(f'giro comandado de {grados}° (Δyaw acumulado)',
                           round(medido, 1), grados * 0.6, grados * 1.4,
                           'SIN BASE HISTORICA — esta pasada fija la referencia',
                           'F5', '°'))
        if desliz is not None:
            a.add(juzgar_banda(f'deslizamiento girando {grados}°', round(desliz, 1),
                               0.0, 15.0, 'giro en el sitio: deberia ser ~0', 'F5', 'cm'))
        time.sleep(2)

    # ── el convenio de signo ──
    print('    → derecha 90° (para fijar el signo)…')
    medido, _ = girar(-1.0, math.pi / 2)
    # 🔴 Hallazgo de revision (task 6): el brief formatea `medido` con `.1f` sin
    #    comprobar antes que no sea None — si /odom no llega, `girar()` devuelve
    #    (None, None) y el f-string original reventaria con TypeError. Se protege
    #    el detalle sin tocar la condicion del veredicto (esa ya contemplaba None).
    a.add(juzgar_categorico(
        'angular positivo gira a la IZQUIERDA (regla de la mano derecha)',
        medido is not None and medido < 0, 'F5',
        (f'con angular NEGATIVO el Δyaw fue {medido:.1f}° '
         f'(negativo = derecha, como manda REP-103)') if medido is not None
        else 'no llego /odom'))


@fase('F6', 'Seguridad — collision_monitor y watchdog', mueve=True)
def f6(a: Aceptacion) -> None:
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import LaserScan
    from std_srvs.srv import Empty as E

    a.puerta('PARED U OBSTACULO GRANDE A ~1 m POR DELANTE del robot.\n'
             '     Va a conducir hacia el y la capa de seguridad debe pararlo\n'
             '     sola. Base: 9.9 cm a 0.25 m/s.')

    # El collision_monitor necesita /scan: sin barrido no ve nada.
    a.llamar(a.nodo.create_client(E, 'start_scan'), E.Request(), 20.0)
    time.sleep(3)

    pub = a.nodo.create_publisher(Twist, 'cmd_vel_raw', FIABLE)
    p0 = a.pos_yaw()

    # ── collision_monitor ──
    t = Twist()
    t.linear.x = 0.25
    fin = time.monotonic() + 8
    while time.monotonic() < fin:
        pub.publish(t)
        a.ex.spin_once(timeout_sec=0.05)
    pub.publish(Twist())
    time.sleep(1.5)

    b = a.esperar('scan', LaserScan, BE, 2.0)
    frontal = None
    if b:
        s = b[-1]
        i = len(s.ranges) // 2
        v = [r for r in s.ranges[i - 8:i + 8] if math.isfinite(r) and r > 0]
        frontal = min(v) * 100 if v else None
    a.add(juzgar_banda('distancia frontal a la que quedo parado',
                       None if frontal is None else round(frontal, 1),
                       0.0, 15.0, 'CHANGELOG:1824: 9.9 cm a 0.25 m/s', 'F6', 'cm'))
    p1 = a.pos_yaw()
    a.add(juzgar_categorico('el robot avanzo y se detuvo solo',
                            bool(p0 and p1 and math.hypot(p1[0] - p0[0],
                                                          p1[1] - p0[1]) > 0.05),
                            'F6', 'si no avanzo nada, la prueba no demuestra nada'))

    # ── watchdog: dejar de publicar debe pararlo ──
    a.puerta('SITIO LIBRE POR DETRAS: retrocede un poco y luego se deja de\n'
             '     publicar cmd_vel a proposito. El watchdog debe cortarlo.')
    t = Twist()
    t.linear.x = -0.15
    fin = time.monotonic() + 2
    while time.monotonic() < fin:
        pub.publish(t)
        a.ex.spin_once(timeout_sec=0.05)
    pm = a.pos_yaw()
    time.sleep(3)                       # ← se deja de publicar A PROPOSITO
    pf = a.pos_yaw()
    if pm and pf:
        a.add(juzgar_banda('recorrido tras dejar de publicar cmd_vel',
                           round(math.hypot(pf[0] - pm[0], pf[1] - pm[1]) * 100, 1),
                           0.0, 12.0,
                           'CHANGELOG:3303: quieto en 527 ms, ~7.9 cm', 'F6', 'cm'))
    else:
        a.add(no_verificado('watchdog', 'F6', 'no llego /odom'))


@fase('F7', 'Autonomo — SLAM, Nav2 y sorteo de obstaculos', mueve=True)
def f7(a: Aceptacion) -> None:
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionClient
    from geometry_msgs.msg import PoseStamped

    a.puerta('PASILLO LIBRE, 2 m POR DELANTE. Se lanzan SLAM y Nav2 y el robot\n'
             '     ira solo a un objetivo a 1.50 m. Tarda ~1 min en arrancar.')

    # 🔴 LOS DOS `Popen` VAN DENTRO DEL `try`. La version anterior los lanzaba
    #    FUERA, asi que si el segundo fallaba despues de arrancar el primero,
    #    **SLAM quedaba huerfano**: ~5 % de un nucleo, un `map -> odom` que nadie
    #    esperaba, y peleando por los recursos con la siguiente corrida. Nadie lo
    #    habria visto: el fallo se atribuiria a Nav2.
    #    📝 Encontrado por lectura en la revision de la tarea 7, no ejecutando.
    procs = []
    cli = ActionClient(a.nodo, NavigateToPose, 'navigate_to_pose')
    try:
        for paquete, fichero in [('atriz_rvr_bringup', 'slam.launch.py'),
                                 ('atriz_rvr_bringup', 'nav2.launch.py')]:
            print(f'    lanzando {fichero}…')
            procs.append(subprocess.Popen(['ros2', 'launch', paquete, fichero],
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL))
            time.sleep(20)

        listo = cli.wait_for_server(timeout_sec=90.0)
        a.add(juzgar_categorico('Nav2 levanta y su action server responde',
                                listo, 'F7'))
        if not listo:
            return

        def objetivo(dx, etiqueta):
            p0 = a.pos_yaw()
            g = NavigateToPose.Goal()
            g.pose.header.frame_id = 'map'
            g.pose.header.stamp = a.nodo.get_clock().now().to_msg()
            g.pose.pose.position.x = p0[0] + dx
            g.pose.pose.position.y = p0[1]
            g.pose.pose.orientation.w = 1.0

            fut = cli.send_goal_async(g)
            fin = time.monotonic() + 20
            while not fut.done() and time.monotonic() < fin:
                a.ex.spin_once(timeout_sec=0.05)
            if not fut.done() or not fut.result().accepted:
                a.add(juzgar_categorico(f'{etiqueta}: objetivo aceptado', False, 'F7'))
                return
            rf = fut.result().get_result_async()
            fin = time.monotonic() + 120
            desvio = 0.0
            while not rf.done() and time.monotonic() < fin:
                a.ex.spin_once(timeout_sec=0.05)
                p = a.pos_yaw()
                if p:
                    desvio = max(desvio, abs(p[1] - p0[1]) * 100)
            if not rf.done():
                a.add(juzgar_categorico(f'{etiqueta}: llego en 120 s', False, 'F7'))
                return
            p1 = a.pos_yaw()
            err = math.hypot(p1[0] - (p0[0] + dx), p1[1] - p0[1]) * 100
            a.add(juzgar_banda(f'{etiqueta}: error final', round(err, 1), 0.0, 15.0,
                               'TRASPASO:289: 8 cm; otra tanda 9-10', 'F7', 'cm'))
            return desvio

        objetivo(1.50, 'objetivo limpio a 1.50 m')

        a.puerta('COLOCA EL OBSTACULO a ~0.75 m por delante, escorado un poco a\n'
                 '     la izquierda del eje. Algo de ~16 cm de ancho (una caja).\n'
                 '     Deja ~60 cm libres por la derecha para que pueda rodearlo.')
        # Volver al punto de partida a mano es mas fiable que otro objetivo.
        a.puerta('DEVUELVE EL ROBOT a donde empezo, mirando al mismo sitio.')

        desvio = objetivo(1.50, 'objetivo CON obstaculo')
        if desvio is not None:
            a.add(juzgar_banda('desvio lateral rodeando el obstaculo',
                               round(desvio, 1), 15.0, 50.0,
                               'manual 11.13: 30 cm y vuelve al eje', 'F7', 'cm'))

        # 🔴 El aborto que costo encontrar: el SimpleProgressChecker de fabrica
        #    exigia 5 cm/s, y con el collision_monitor frenando eso se dispara.
        #    Arreglado con required_movement_radius 0.25 / 15 s. Que no vuelva.
        j = subprocess.run(['journalctl', '--since', '-4min', '--no-pager'],
                           capture_output=True, text=True, timeout=20).stdout
        a.add(juzgar_categorico('sin «Failed to make progress»',
                                'Failed to make progress' not in j, 'F7',
                                'el arreglo del SimpleProgressChecker sigue en pie'))
    finally:
        # 🔴 Por comm, NUNCA pkill -f: su patron casaria con esta misma prueba.
        for p in procs:
            p.send_signal(signal.SIGINT)
        matar_por_comm('async_slam_tool')
        for n in ('controller_server', 'planner_server', 'bt_navigator',
                  'behavior_server'):
            matar_por_comm(n)
        time.sleep(5)


def ejecutar(a: Aceptacion, desde: str) -> int:
    claves = [f[0] for f in FASES]
    if desde not in claves:
        print(f'🔴 fase «{desde}» desconocida. Hay: {", ".join(claves)}')
        return 1
    for clave, titulo, mueve, fn in FASES[claves.index(desde):]:
        print(f'\n{"═" * 74}\n  {clave} · {titulo}' +
              ('   ⚠️ MUEVE EL ROBOT' if mueve else '') + f'\n{"═" * 74}')
        try:
            fn(a)
        except KeyboardInterrupt:
            raise
        except Exception as e:                                   # noqa: BLE001
            a.parada_emergencia()
            a.add(juzgar_categorico(f'{clave} completa', False, clave,
                                    f'la fase reventó: {type(e).__name__}: {e}'))
            print(f'\n  🔴 {clave} reventó. El robot esta parado.')
            print('     ¿Sigues con las demas fases? [s/N] ', end='', flush=True)
            if sys.stdin.readline().strip().lower() != 's':
                break
    ruta = escribir_informe(a)
    # 🔴 Hallazgo de revisión: antes `escribir_informe` mutaba `a.res` para que
    #    esta línea viera los PENDIENTES_CONOCIDOS ya sumados. Ya no muta nada
    #    (ver escribir_informe), así que la misma lista se construye aquí.
    res_final = list(a.res) + PENDIENTES_CONOCIDOS
    print(formatear_informe(res_final, cabecera()))
    print(f'\n  📄 informe: {ruta}')
    return 0 if hay_via_libre(res_final) else 2


def cabecera() -> str:
    return (f'PRUEBA DE ACEPTACION · {os.uname().nodename} · '
            f'{time.strftime("%Y-%m-%d %H:%M:%S")}')


def escribir_informe(a: Aceptacion, abortada=False) -> str:
    """Se escribe SIEMPRE, pase o falle. Un informe que solo aparece cuando todo
    va bien no sirve para depurar nada.

    🔴 Hallazgo de revisión: la versión anterior hacía `a.res = res` al final,
       mutando el estado compartido. Se la llama desde `ejecutar()` Y desde el
       manejador de Ctrl-C; si el Ctrl-C llegaba justo después de que
       `ejecutar()` ya hubiera mutado `a.res` (que ya incluía los 4 pendientes)
       pero antes de que `ejecutar()` retornara, el segundo informe salía con
       8 pendientes en vez de 4. No se toca `a.res`: se construye la lista
       local y se usa solo para escribir este informe.
    """
    res = list(a.res) + PENDIENTES_CONOCIDOS
    d = pathlib.Path.home() / 'atriz_migracion' / '00_auditoria' / 'evidencia_24_04'
    d.mkdir(parents=True, exist_ok=True)
    ruta = d / f'47_aceptacion_{time.strftime("%Y%m%d_%H%M%S")}.txt'
    cab = cabecera() + ('  ⚠️ ABORTADA POR Ctrl-C' if abortada else '')
    ruta.write_text(formatear_informe(res, cab), encoding='utf-8')
    return str(ruta)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--desde', default='F0', help='retomar desde una fase (F0…F9)')
    ap.add_argument('--sin-puertas', action='store_true',
                    help='no esperar confirmacion (solo para las fases sin movimiento)')
    args = ap.parse_args()          # 🔴 argparse LO PRIMERO: `--help` no debe mover nada

    a = Aceptacion(guiada=not args.sin_puertas)
    try:
        motivo = guardas(a)
        if motivo:
            print(f'\n🔴 {motivo}')
            return 1
        return ejecutar(a, args.desde)
    except KeyboardInterrupt:
        print('\n\n  ⛔ Ctrl-C — PARANDO EL ROBOT…')
        # 🔴 Y SE BLOQUEA LA SEÑAL: la recuperacion tarda varios segundos, y quien
        #    ve que el robot no para al primer Ctrl-C pulsa un segundo. Ese
        #    segundo abortaba la recuperacion a medias.
        previo = signal.signal(signal.SIGINT, signal.SIG_IGN)
        print('     (Ctrl-C ignorado hasta que termine — deja que acabe)')
        try:
            a.parada_emergencia()
            print('     ✅ parada enviada. Suelta el robot.')
            a.liberar_parada()
            escribir_informe(a, abortada=True)
        except Exception as e:                                   # noqa: BLE001
            # 🔴 Hallazgo de revisión: antes esto se propagaba sin capturar y se
            #    saltaba tanto `a.cerrar()` como el `return 130` de abajo — un
            #    Ctrl-C con traza y código arbitrario en vez de una parada
            #    garantizada.
            print(f'\n  🔴 fallo al parar tras Ctrl-C: {type(e).__name__}: {e}')
        finally:
            # 🔴 Hallazgo de revisión: `cerrar()` (segundo intento de parada) va
            #    DENTRO de esta protección, con el SIGINT todavía bloqueado —
            #    antes quedaba fuera del try/finally, así que un fallo a mitad
            #    del primer intento se saltaba el segundo.
            a.cerrar()
            signal.signal(signal.SIGINT, previo)
        return 130
    finally:
        # 🔴 Hallazgo de revisión: la ruta normal (`return ejecutar(...)`) no
        #    llamaba a `cerrar()` nunca — al completar las diez fases bien, el
        #    caso común, no había `rclpy.shutdown()` ni parada final. `cerrar()`
        #    es idempotente, así que da igual si la rama de Ctrl-C ya la llamó.
        a.cerrar()


if __name__ == '__main__':
    raise SystemExit(main())
