#!/usr/bin/env python3
"""Logica pura de la prueba de aceptacion: bandas, veredictos e informe.

🔴 SIN IMPORTS DE ROS, A PROPOSITO. Esto se prueba con pytest en cualquier
   maquina. Metido dentro del orquestador, la unica forma de ejercitar la logica
   de veredictos seria mover motores, y entonces nadie la probaria.

📎 Criterio y umbrales: 03_operacion/PRUEBA_ACEPTACION.md
"""
import math
from dataclasses import dataclass, field

PASA = 'PASA'
REVISAR = 'REVISAR'
FALLO = 'FALLO'
PENDIENTE = 'PENDIENTE'

#: Los que impiden decir «via libre». Ver el diseño, «El veredicto».
BLOQUEAN = (FALLO, PENDIENTE)


@dataclass
class Resultado:
    fase: str
    concepto: str
    veredicto: str
    detalle: str = ''
    medido: float | None = None
    base: str = ''


def delta_angulo(a, b) -> float:
    """b - a normalizado a (-pi, pi].

    🔴 Hallazgo de revisión (D1): es logica pura — la funcion que se colgaba con
       `inf` — y hasta ahora no la cubria ni un test, porque vivia en
       `prueba_aceptacion.py`, que importa rclpy y no se puede ejercitar sin ROS.
       Movida aqui para que pytest la alcance sin robot. `prueba_aceptacion.py`
       la importa de vuelta, asi que el resto del codigo no cambia.

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


def juzgar_banda(concepto, valor, lo, hi, base, fase, unidad='') -> Resultado:
    """Un numero contra su banda. Fuera de banda es REVISAR, NUNCA fallo.

    🔴 Casi todas las bases son n=1 a n=4. Llamar «suspenso» a una desviacion
       del 20 % sobre una sola medida seria fingir una precision que no hay.
    """
    if valor is None:
        return Resultado(fase, concepto, PENDIENTE,
                         f'NO VERIFICADO: no se pudo medir (base {base})', None, base)
    u = f' {unidad}' if unidad else ''
    dentro = lo <= valor <= hi
    return Resultado(
        fase, concepto, PASA if dentro else REVISAR,
        f'{valor}{u} · banda [{lo}, {hi}]{u} · base {base}', valor, base)


def juzgar_categorico(concepto, ok, fase, detalle='') -> Resultado:
    """O funciona o no. Aqui no hay banda que valga."""
    return Resultado(fase, concepto, PASA if ok else FALLO, detalle)


def no_verificado(concepto, fase, motivo) -> Resultado:
    """Un hueco NO es un aprobado. Bloquea hasta que alguien lo mire."""
    return Resultado(fase, concepto, PENDIENTE, f'NO VERIFICADO: {motivo}')


#: 🔴 Las decisiones abiertas que NINGUNA ejecucion cierra. Bloquean la via libre
#: por decision del usuario (2026-08-01): «los pendientes bloquean el paso a la
#: web». Se mantienen AQUI y no en el documento, para que no se desincronicen.
#: Cuando una se cierre, se borra de esta lista y se anota en el CHANGELOG.
PENDIENTES_CONOCIDOS = [
    Resultado('F9', 'rosbridge sin autenticacion en el 9090', PENDIENTE,
              'expone raw_motors, que se salta el collision_monitor y no tiene corte '
              'automatico. Hay que decidirlo ANTES de escribir el cliente: cambia su '
              'arquitectura. Ver 03_operacion/ARQUITECTURA.md'),
    Resultado('F9', 'el hueco de los precipicios', PENDIENTE,
              'collision_monitor solo mira /scan, y un LIDAR 2D no ve un vacio a ninguna '
              'altura. Mitigado solo por la regla de laboratorio (suelo continuo y '
              'cerrado). Ver manual cap. 12.2b'),
    Resultado('F9', 'la PSK del WiFi es legible por cualquier usuario', PENDIENTE,
              'falta fmask=0177,dmask=0077 en /etc/fstab. chmod NO sirve: es FAT'),
    Resultado('F9', 'la credencial sphero sin rotar', PENDIENTE,
              'y sin purgar del historico de git'),
]


def hay_via_libre(resultados) -> bool:
    """Solo con CERO fallos y CERO pendientes. REVISAR no bloquea."""
    return not any(r.veredicto in BLOQUEAN for r in resultados)


def resumen(resultados) -> dict:
    c = {PASA: 0, REVISAR: 0, FALLO: 0, PENDIENTE: 0}
    for r in resultados:
        c[r.veredicto] = c.get(r.veredicto, 0) + 1
    return c


_ICONO = {PASA: 'OK  ', REVISAR: 'REV ', FALLO: 'FALLO', PENDIENTE: 'PEND'}


def formatear_informe(resultados, cabecera) -> str:
    lin = ['=' * 78, cabecera, '=' * 78, '']
    fase_actual = None
    for r in resultados:
        if r.fase != fase_actual:
            fase_actual = r.fase
            lin.append(f'\n── {fase_actual} ' + '─' * (72 - len(fase_actual)))
        lin.append(f'  [{_ICONO[r.veredicto]:5}] {r.concepto}')
        if r.detalle:
            lin.append(f'          {r.detalle}')

    c = resumen(resultados)
    lin += ['', '=' * 78,
            f'  {c[PASA]} PASA · {c[REVISAR]} REVISAR · {c[FALLO]} FALLO · '
            f'{c[PENDIENTE]} PENDIENTE', '=' * 78, '']

    if hay_via_libre(resultados):
        lin += ['  ✅ VIA LIBRE PARA LA FASE 5', '',
                '     Cero fallos y cero pendientes: se puede empezar la web.']
    else:
        lin += ['  🔴 NO HAY VIA LIBRE PARA LA FASE 5', '', '     Lo que lo impide:']
        for r in resultados:
            if r.veredicto in BLOQUEAN:
                lin.append(f'       · [{r.veredicto}] {r.concepto}')
    if c[REVISAR]:
        lin += ['', f'  ⚠️ Y {c[REVISAR]} numero(s) fuera de banda. No bloquean, pero '
                    'miralos:']
        for r in resultados:
            if r.veredicto == REVISAR:
                lin.append(f'       · {r.concepto}: {r.detalle}')
    lin.append('=' * 78)
    return '\n'.join(lin)
