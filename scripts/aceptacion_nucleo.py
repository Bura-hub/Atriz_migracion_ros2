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
