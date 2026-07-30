#!/usr/bin/env python3
"""¿De dónde sacamos la velocidad de `/odom`? Mide las CUATRO opciones a la vez.

    python3 medir_velocidad_rvr.py --calibrar    # 🚗 avanza 1 m y para. Mide tú con cinta
    python3 medir_velocidad_rvr.py               # 🚗 barrido de velocidades

⚠️  MUEVE EL ROBOT, y más rápido que las otras pruebas: hasta 0.40 m/s.
⚠️  NO uses ROS a la vez: este script abre /dev/rvr en exclusiva. Para el driver.

═══════════════════════════════════════════════════════════════════════════════
EL PROBLEMA
═══════════════════════════════════════════════════════════════════════════════

`odom.twist.twist.linear` sale del stream `Velocity` del RVR, y ese stream es
**basura**: medido el 2026-07-30, reportaba **0.001 m/s** con el robot moviéndose
a **0.147 m/s** comprobados por desplazamiento.

Eso no bloquea SLAM (que usa la posición) pero **sí bloquea Nav2**, que necesita
saber a qué velocidad va el robot para controlarlo.

Hay CUATRO fuentes posibles, y ninguna estaba probada:

  1. `Velocity` (X, Y)   el que se usa hoy. Se mide para confirmar que es basura
                         y no una mala interpretación de una prueba anterior.
  2. `Speed` (escalar)   🔴 EXISTE Y NADIE LO HABÍA MIRADO. Es un servicio de
                         streaming distinto, con su propio ID (0x0008). Si
                         funciona, es el arreglo más barato posible.
  3. `Encoders`          ticks de rueda izquierda y derecha. Necesita calibrar
                         cuántos ticks son un metro, y patina en suelo liso.
  4. Derivar el locator  posición ÷ tiempo. Sin hardware nuevo, pero derivar a
                         16.7 Hz amplifica el ruido: hay que medir cuánto.

Esta herramienta las mide **todas a la vez, contra la misma verdad**, en la misma
corrida. Comparar corridas distintas no valdría: la velocidad real depende de la
batería, del suelo y de la carga.

🔴 LA VERDAD ES EL DESPLAZAMIENTO, NO OTRO SENSOR. Se toma del locator, que es
   el único ya validado contra una cinta métrica. Por eso `--calibrar` existe:
   revalida el locator contra una medida FÍSICA antes de apoyar en él la
   decisión, y de paso da los ticks por metro de los encoders.

📝 `Locator`, `Velocity`, `Speed` y `Encoders` comparten el mismo slot de
   streaming (token 2). Puede que no quepan los cuatro; si alguno no llega, el
   informe lo dirá en vez de callarlo.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import asyncio
import math
import statistics
import sys
import time

sys.path.insert(0, '/home/sphero/atriz_ws/src/Atriz_rvr/atriz_rvr_driver/scripts')

from sphero_sdk import RvrStreamingServices, SerialAsyncDal, SpheroRvrAsync  # noqa: E402

INTERVALO_MS = 60          # el mínimo del firmware; 16.7 Hz
#: Velocidades a barrer, en m/s. La última es 4x la de las pruebas de SLAM.
VELOCIDADES = [0.10, 0.15, 0.20, 0.30, 0.40]
#: Se descarta el primer tramo de cada corrida: el robot está acelerando y ahí
#: ninguna fuente puede coincidir con la media.
DESCARTE_S = 0.7


class Muestras:
    """Guarda lo que llega de cada stream, con marca de tiempo."""

    def __init__(self) -> None:
        self.locator: list[tuple[float, float, float]] = []   # t, x, y
        self.velocity: list[tuple[float, float, float]] = []  # t, vx, vy
        self.speed: list[tuple[float, float]] = []            # t, speed
        self.encoders: list[tuple[float, int, int]] = []      # t, izq, der
        self.yaw: float = 0.0

    def limpiar(self) -> None:
        self.locator.clear(); self.velocity.clear()
        self.speed.clear(); self.encoders.clear()


M = Muestras()


async def h_locator(d):
    v = d['Locator']
    M.locator.append((time.monotonic(), float(v['X']), float(v['Y'])))


async def h_velocity(d):
    v = d['Velocity']
    M.velocity.append((time.monotonic(), float(v['X']), float(v['Y'])))


async def h_speed(d):
    M.speed.append((time.monotonic(), float(d['Speed']['Speed'])))


async def h_quaternion(d):
    q = d['Quaternion']
    M.yaw = math.atan2(2.0 * (float(q['W']) * float(q['Z']) + float(q['X']) * float(q['Y'])),
                       1.0 - 2.0 * (float(q['Y']) ** 2 + float(q['Z']) ** 2))


async def h_encoders(d):
    v = d['Encoders']
    M.encoders.append((time.monotonic(), int(v['LeftTicks']), int(v['RightTicks'])))


def recorrido(loc: list[tuple[float, float, float]]) -> float:
    """Distancia recorrida sumando paso a paso, en metros."""
    return sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(loc, loc[1:]))


async def conducir(rvr, v: float, segundos: float) -> float:
    """Conduce a `v` m/s durante `segundos`. Devuelve cuándo dejó de conducir.

    🔴 Devolver ese instante NO es un detalle. Tras `drive_stop()` hay 1.2 s de
    muestras con el robot YA PARADO, y una version anterior de `marco()` cogia
    "las ultimas 20 muestras" — es decir, justo esas. Las magnitudes salian de
    un robot quieto (0.010 m/s con 0.20 comandados) y el veredicto se apoyaba en
    el signo del RUIDO. Filtra siempre por [inicio+DESCARTE, t_parada].
    """
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        await rvr.drive_rc_si_units(linear_velocity=v, yaw_angular_velocity=0.0, flags=0)
        await asyncio.sleep(0.1)
    t_parada = time.monotonic()
    await rvr.drive_stop()
    await asyncio.sleep(1.2)      # que se asiente antes de leer nada
    return t_parada


async def arrancar_streams(rvr) -> None:
    sc = rvr.sensor_control
    await sc.add_sensor_data_handler(RvrStreamingServices.locator, h_locator)
    await sc.add_sensor_data_handler(RvrStreamingServices.velocity, h_velocity)
    await sc.add_sensor_data_handler(RvrStreamingServices.speed, h_speed)
    await sc.add_sensor_data_handler(RvrStreamingServices.encoders, h_encoders)
    await sc.add_sensor_data_handler(RvrStreamingServices.quaternion, h_quaternion)
    await sc.start(interval=INTERVALO_MS)


async def calibrar(rvr) -> None:
    """Avanza ~1 m y para, para que una persona lo mida con cinta."""
    print("\n" + "═" * 74)
    print("CALIBRACIÓN — la verdad física")
    print("═" * 74)
    print("  El robot va a avanzar en línea recta y parar.")
    print("  🔴 MARCA EL PUNTO DE PARTIDA antes de que se mueva.\n")
    for i in (3, 2, 1):
        print(f"    {i}…", flush=True)
        await asyncio.sleep(1)

    M.limpiar()
    t0 = time.monotonic()
    await conducir(rvr, 0.20, 5.0)      # ~1.0 m a 0.20 m/s
    dt = time.monotonic() - t0

    d = recorrido(M.locator)
    print(f"\n  ── lo que dice el robot ──")
    print(f"  locator:  {d * 100:.1f} cm   (en {dt:.1f} s)")
    if M.encoders:
        di = M.encoders[-1][1] - M.encoders[0][1]
        dd = M.encoders[-1][2] - M.encoders[0][2]
        print(f"  encoders: {di} ticks izquierda, {dd} ticks derecha")
        if d > 0.05:
            print(f"            -> {(di + dd) / 2 / d:.0f} ticks/m  (media de las dos ruedas)")
    else:
        print("  encoders: 🔴 NO LLEGÓ NINGUNA MUESTRA")

    print("\n  ══════════════════════════════════════════════════════════")
    print("  👤 MIDE AHORA CON LA CINTA los centímetros REALES recorridos")
    print("  ══════════════════════════════════════════════════════════")
    print("\n  Con ese número se valida el locator, que es la referencia de")
    print("  todo lo demás, y se calibran los ticks/m de los encoders.")

    # 🔴 VOLVER AL INICIO. Sin esto el robot se queda 1 m adelantado y la
    # siguiente prueba arranca desde ahí. Paso el 2026-07-31 y el robot choco:
    # `reset_locator_x_and_y()` pone a cero la ODOMETRIA, no devuelve el robot
    # a su sitio. El cero de software se mueve CON el robot, asi que todo
    # parece correcto en los numeros mientras se sale del pasillo.
    print("\n  ▸ volviendo al punto de partida…", flush=True)
    await conducir(rvr, -0.20, 5.0)
    print(f"    de vuelta (el robot deberia estar sobre la marca)")


async def marco(rvr) -> None:
    """¿`Velocity` viene en el marco del MUNDO o en el del ROBOT?

    🔴 ES LA PREGUNTA QUE DECIDE SI HAY UN BUG EN EL DRIVER, y explica por qué
    una medición del 2026-07-30 concluyó que este stream era basura.

    En ROS, `odom.twist` va expresado en `child_frame_id`, es decir en el marco
    del ROBOT: avanzar siempre da `linear.x` positivo, mire donde mire. Si el RVR
    lo reporta en el marco del MUNDO, copiarlo tal cual es incorrecto en cuanto
    el robot deja de estar encarado al eje X.

    LA PRUEBA: girar 180° en el sitio y avanzar.

        marco del ROBOT:  Velocity.X sale POSITIVA (avanza = +x, siempre)
        marco del MUNDO:  Velocity.X sale NEGATIVA (se aleja por -X del mundo)

    Se eligió 180° y no 90° porque cabe en el mismo pasillo: tras girar, el robot
    avanza por donde vino. Con 90° se saldría de lado.
    """
    print("\n" + "═" * 74)
    print("¿MARCO DEL MUNDO O DEL ROBOT? — la prueba que decide")
    print("═" * 74)

    # 🔴 LA PRUEBA NO NECESITA GIRAR NADA, y esa es la clave.
    #
    # Dos versiones anteriores giraron 180° para comparar signos, y 180° es
    # EXACTAMENTE el angulo donde el signo de un giro es ambiguo: +180 y -180
    # son el mismo giro. (El mismo error se cometio antes al determinar el signo
    # del yaw. Dos veces.)
    #
    # No hace falta. Basta UN tramo recto y comparar dos direcciones que ya se
    # miden en el mismo marco:
    #
    #   direccion del DESPLAZAMIENTO del locator   (a donde fue el robot)
    #   direccion del vector Velocity              (a donde dice que va)
    #
    #   coinciden       -> Velocity esta en el marco del LOCATOR (mundo)
    #   Velocity ~ +x   -> Velocity esta en el marco del ROBOT
    #
    # Y no depende del yaw, ni de su convencion de signos, ni de donde estuviera
    # el cero cuando se llamo a reset_yaw().
    print("\n  ▸ un tramo recto hacia delante (no hace falta girar)")
    M.limpiar()
    t0 = time.monotonic()
    t_par = await conducir(rvr, 0.20, 3.5)
    ini = t0 + DESCARTE_S
    vel = [m for m in M.velocity if ini <= m[0] <= t_par]
    loc = [m for m in M.locator if ini <= m[0] <= t_par]
    if len(vel) < 5 or len(loc) < 5:
        print("    🔴 muy pocas muestras en movimiento")
        return

    vx = statistics.mean(m[1] for m in vel)
    vy = statistics.mean(m[2] for m in vel)
    dx, dy = loc[-1][1] - loc[0][1], loc[-1][2] - loc[0][2]
    dt = loc[-1][0] - loc[0][0]
    v_real = math.hypot(dx, dy) / dt if dt > 0 else 0.0

    dir_desp = math.degrees(math.atan2(dy, dx))
    dir_vel = math.degrees(math.atan2(vy, vx))
    dif = abs(math.degrees(math.atan2(math.sin(math.radians(dir_vel - dir_desp)),
                                      math.cos(math.radians(dir_vel - dir_desp)))))

    print(f"\n    velocidad real (desplazamiento):  {v_real:.3f} m/s")
    print(f"    módulo de Velocity:               {math.hypot(vx, vy):.3f} m/s")
    print(f"\n    dirección del desplazamiento:     {dir_desp:+7.1f}°")
    print(f"    dirección de Velocity:            {dir_vel:+7.1f}°")
    print(f"    diferencia:                       {dif:7.1f}°")
    print(f"\n    Velocity = ({vx:+.3f}, {vy:+.3f})")
    print(f"    si fuera marco ROBOT sería        ({v_real:+.3f}, +0.000)")

    print("\n" + "═" * 74)
    print("VEREDICTO")
    print("═" * 74)
    err_mod = abs(math.hypot(vx, vy) - v_real)
    print(f"  el MÓDULO acierta con {err_mod:.3f} m/s de error "
          f"({100 * err_mod / v_real:.0f} %)" if v_real > 0.02 else "")

    if dif < 20:
        print(f"\n  🔴 `Velocity` viene en el MARCO DEL LOCATOR (mundo).")
        print(f"     Su dirección coincide con la del desplazamiento ({dif:.0f}° de")
        print("     diferencia), no con el eje de avance del robot.")
        print("\n     -> El driver copia Velocity.X a odom.twist.twist.linear.x, que en")
        print("        ROS va en el marco del ROBOT (child_frame_id). ES UN BUG.")
        print("        Y explica el hallazgo del 2026-07-30: con el robot encarado")
        print("        a ~90° del eje X del locator, Velocity.X vale ~0 mientras el")
        print("        robot se mueve perfectamente. El stream NO era basura.")
        print("\n        Arreglo: proyectar sobre el rumbo.")
        print("          vx_robot =  vx*cos(yaw) + vy*sin(yaw)")
        print("          vy_robot = -vx*sin(yaw) + vy*cos(yaw)")
    elif abs(vx - v_real) < 0.05 and abs(vy) < 0.05:
        print("\n  ✅ `Velocity` viene en el MARCO DEL ROBOT: copiarlo a linear.x es correcto.")
    else:
        print("\n  ⚠️  NO CONCLUYENTE: no encaja con ninguna de las dos.")
        print("     Repite con el robot bien alineado y sin patinar.")

    print("\n  ▸ volviendo al punto de partida…", flush=True)
    await conducir(rvr, -0.20, 3.5)


async def barrido(rvr) -> None:
    print("\n" + "═" * 74)
    print("BARRIDO DE VELOCIDADES — las cuatro fuentes contra el desplazamiento")
    print("═" * 74)

    # 🔴 CADA velocidad va y VUELVE, en vez de alternar el sentido entre
    # velocidades. La version anterior alternaba, y como el robot no alcanza la
    # velocidad comandada por igual en cada tramo, los recorridos no se
    # compensaban: acumulo +76 cm y se salio del pasillo (2026-07-31).
    # Ir y volver en la misma velocidad deja el neto en ~0 SIEMPRE.
    resultados = []
    for v in VELOCIDADES:
        # A más velocidad, menos tiempo: todos recorren ~0.8 m de ida.
        segundos = max(2.5, 0.8 / v)
        print(f"\n  ▸ {v:.2f} m/s durante {segundos:.1f} s (ida y vuelta)", flush=True)

        M.limpiar()
        t0 = time.monotonic()
        await conducir(rvr, v, segundos)

        # Solo el tramo de velocidad constante.
        corte = t0 + DESCARTE_S
        loc = [m for m in M.locator if m[0] >= corte]
        if len(loc) < 5:
            print("    🔴 muy pocas muestras del locator; se salta")
            continue

        dt_real = loc[-1][0] - loc[0][0]
        v_real = recorrido(loc) / dt_real if dt_real > 0 else 0.0

        vel = [math.hypot(m[1], m[2]) for m in M.velocity if corte <= m[0] <= loc[-1][0]]
        spd = [m[1] for m in M.speed if corte <= m[0] <= loc[-1][0]]

        # Derivada del locator, muestra a muestra. Su RUIDO es lo que interesa:
        # la media siempre saldrá bien porque es la propia verdad.
        deriv = [math.hypot(b[1] - a[1], b[2] - a[2]) / (b[0] - a[0])
                 for a, b in zip(loc, loc[1:]) if b[0] > a[0]]

        enc = [m for m in M.encoders if corte <= m[0] <= loc[-1][0]]
        v_enc = None
        if len(enc) >= 2 and (enc[-1][0] - enc[0][0]) > 0:
            ticks = ((enc[-1][1] - enc[0][1]) + (enc[-1][2] - enc[0][2])) / 2
            v_enc = ticks / (enc[-1][0] - enc[0][0])      # ticks/s, se escala luego

        r = {
            'comandada': v,
            'real': v_real,
            'velocity': statistics.mean(vel) if vel else None,
            'speed': statistics.mean(spd) if spd else None,
            'deriv_media': statistics.mean(deriv) if deriv else None,
            'deriv_sigma': statistics.stdev(deriv) if len(deriv) > 1 else None,
            'enc_ticks_s': v_enc,
            'n_loc': len(loc), 'n_vel': len(vel), 'n_spd': len(spd), 'n_enc': len(enc),
        }
        resultados.append(r)
        print(f"    real {v_real:.3f} m/s  ·  Velocity {_f(r['velocity'])}  ·  "
              f"Speed {_f(r['speed'])}  ·  encoders {_f(v_enc, ' t/s')}", flush=True)

        # Vuelta, para dejar el neto en cero antes de la siguiente velocidad.
        await conducir(rvr, -v, segundos)

    informe(resultados)


def _f(x, suf=' m/s') -> str:
    return '—' if x is None else f"{x:.3f}{suf}"


def informe(res: list[dict]) -> None:
    if not res:
        print("\n🔴 sin resultados.")
        return

    print("\n" + "═" * 74)
    print("RESULTADO")
    print("═" * 74)
    print(f"  {'comandada':>10} {'REAL':>8} {'Velocity':>10} {'Speed':>10} "
          f"{'deriv':>8} {'σ deriv':>8} {'encoders':>10}")
    for r in res:
        print(f"  {r['comandada']:>10.2f} {r['real']:>8.3f} "
              f"{_f(r['velocity'], ''):>10} {_f(r['speed'], ''):>10} "
              f"{_f(r['deriv_media'], ''):>8} {_f(r['deriv_sigma'], ''):>8} "
              f"{_f(r['enc_ticks_s'], ''):>10}")

    print("\n  ── muestras recibidas (si alguna columna es 0, ese stream no cabe) ──")
    for r in res:
        print(f"    {r['comandada']:.2f} m/s: locator {r['n_loc']}  velocity {r['n_vel']}  "
              f"speed {r['n_spd']}  encoders {r['n_enc']}")

    print("\n" + "═" * 74)
    print("VEREDICTO")
    print("═" * 74)

    def error_rel(clave):
        vs = [(abs(r[clave] - r['real']) / r['real'])
              for r in res if r.get(clave) is not None and r['real'] > 0.02]
        return statistics.median(vs) if vs else None

    e_vel, e_spd = error_rel('velocity'), error_rel('speed')

    if e_vel is None:
        print("  `Velocity` : 🔴 no llegó ninguna muestra")
    else:
        print(f"  `Velocity` : error mediano del {e_vel * 100:.0f} %"
              + ("  ✅ USABLE" if e_vel < 0.15 else "  🔴 INSERVIBLE"))
    if e_spd is None:
        print("  `Speed`    : 🔴 no llegó ninguna muestra")
    else:
        print(f"  `Speed`    : error mediano del {e_spd * 100:.0f} %"
              + ("  ✅ USABLE" if e_spd < 0.15 else "  🔴 INSERVIBLE"))

    sigmas = [r['deriv_sigma'] for r in res if r['deriv_sigma'] is not None]
    if sigmas:
        s = statistics.median(sigmas)
        print(f"  derivar el locator: σ = {s:.3f} m/s de ruido muestra a muestra")
        print("      (la media coincide con la verdad por construcción: lo que")
        print("       decide si sirve es ese ruido. Se puede filtrar, pero eso")
        print("       mete retardo, y para Nav2 el retardo también importa.)")

    if any(r['enc_ticks_s'] for r in res):
        print("  encoders   : llegan ticks. Hacen falta los ticks/m de `--calibrar`")
        print("      para convertirlos a m/s, y ojo: en suelo liso PATINAN al")
        print("      acelerar, así que medirán de más justo cuando más importa.")
    else:
        print("  encoders   : 🔴 no llegó ninguna muestra")

    print("\n  Elige la fuente MÁS SIMPLE que pase la prueba. `Speed` sería un")
    print("  cambio de tres líneas; los encoders, un stream nuevo y una")
    print("  calibración por robot que puede derivar con el desgaste de las ruedas.")


async def principal(args, rvr) -> None:
    print("  despertando el RVR…", flush=True)
    await rvr.wake()
    await asyncio.sleep(2)
    await rvr.reset_yaw()
    await rvr.reset_locator_x_and_y()
    await arrancar_streams(rvr)
    await asyncio.sleep(1.5)

    if not M.locator:
        print("\n🔴 no llega el locator. ¿Está el RVR encendido? ¿Hay otro proceso")
        print("   usando /dev/rvr? (el driver de ROS lo abre en exclusiva)")
        return

    faltan = [n for n, v in (('Velocity', M.velocity), ('Speed', M.speed),
                             ('Encoders', M.encoders)) if not v]
    if faltan:
        print(f"  ⚠️  sin muestras todavía de: {', '.join(faltan)}")
        print("      (comparten slot con el locator; puede que no quepan todos)")

    try:
        if args.calibrar:
            await calibrar(rvr)
        elif args.marco:
            await marco(rvr)
        else:
            await barrido(rvr)
    finally:
        await rvr.drive_stop()
        await rvr.sensor_control.clear()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--calibrar', action='store_true',
                    help='Solo avanza ~1 m y para, para medirlo con cinta.')
    ap.add_argument('--marco', action='store_true',
                    help='¿Velocity viene en marco del mundo o del robot? Gira 180°.')
    args = ap.parse_args()

    print("═" * 74)
    print("MEDIR LA VELOCIDAD DEL RVR — las cuatro fuentes a la vez")
    print("═" * 74)
    print("⚠️  El robot se mueve. Ctrl-C para abortar.")
    print("⚠️  COLOCA EL ROBOT EN EL CENTRO DEL PASILLO ANTES DE CADA MODO.")
    print("    Cada modo vuelve al punto de partida al terminar, pero si arranca")
    print("    descolocado, acaba mas descolocado todavia.")

    # 🔴 El objeto del SDK se construye con el loop PARADO. Su constructor hace
    # `asyncio.get_event_loop().run_until_complete(...)`, así que crearlo dentro
    # de una corrutina ya en marcha falla con "This event loop is already
    # running" — y el fallo se presenta como "no llegan datos", no como error.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    t0 = time.monotonic()
    rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop, port_id='/dev/rvr'))
    dt = time.monotonic() - t0
    # El tiempo de construcción es diagnóstico: ~0 s = responde, ~10 s = no.
    print(f"  SpheroRvrAsync construido en {dt:.2f} s"
          + ("  🔴 son timeouts: el RVR no responde" if dt > 5 else ""))

    try:
        loop.run_until_complete(principal(args, rvr))
    except KeyboardInterrupt:
        print("\n⚠️  abortado — frenando")
        loop.run_until_complete(rvr.drive_stop())
    finally:
        loop.run_until_complete(rvr.close())
        loop.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
