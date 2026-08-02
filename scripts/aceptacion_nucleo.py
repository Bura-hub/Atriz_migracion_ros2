#!/usr/bin/env python3
"""Logica pura de la prueba de aceptacion: bandas, veredictos e informe.

🔴 SIN IMPORTS DE ROS, A PROPOSITO. Esto se prueba con pytest en cualquier
   maquina. Metido dentro del orquestador, la unica forma de ejercitar la logica
   de veredictos seria mover motores, y entonces nadie la probaria.

📎 Criterio y umbrales: 03_operacion/PRUEBA_ACEPTACION.md
"""
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
