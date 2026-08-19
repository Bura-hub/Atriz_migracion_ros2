#!/usr/bin/env python3
"""⚠️ MUEVE EL ROBOT: mapeo de la arena, con origen convenido.

Convencion: el robot ARRANCA abajo-izquierda de la arena (~50-60 cm de cada
pared), con la pared a su IZQUIERDA y el morro PARALELO a ella. Asi el origen
del mapa (0,0) es esa esquina y los ejes quedan alineados con las paredes.

Dos fases:
  1. PERIMETRO (2 vueltas): avanza hasta ~0,5 m de la pared de enfrente y gira
     90 grados a la DERECHA (sigue la pared izquierda, sentido horario). En una
     arena cuadrada eso traza el contorno, y repetirlo da cierres de lazo.
  2. INTERIOR: rebote hacia el lado mas despejado, para rellenar el centro.
"""
import sys, math, time

sys.path.insert(0, '/home/sphero/atriz_ws/src/Atriz_rvr/scripts/estudiantes')
from atriz import Robot

VEL = 0.15
FRENTE_MIN = 0.70
MARGEN = 0.50
TRAMO_MAX = 1.4
LEGS_PERIMETRO = 12          # ~2 vueltas en una arena cuadrada
LEGS_INTERIOR = 10
DURACION_MAX = 420.0

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def claros(robot):
    barrido = robot._ultimo('_scan', timeout=5.0, que='/scan')
    def cono(centro_deg, semi_deg=15.0):
        centro = math.radians(centro_deg); semi = math.radians(semi_deg)
        vals = []
        for i, d in enumerate(barrido.ranges):
            a = barrido.angle_min + i * barrido.angle_increment
            a = math.atan2(math.sin(a - centro), math.cos(a - centro))
            if abs(a) <= semi and barrido.range_min < d < barrido.range_max:
                vals.append(d)
        if not vals:
            return None
        vals.sort()
        return vals[len(vals) // 2]
    return cono(0), cono(90), cono(-90)

def posicion(robot):
    p = robot._ultimo('_odom', timeout=5.0, que='/odom').pose.pose.position
    return p.x, p.y

def avanza_hasta_pared(r, frente, recorrido):
    if frente is None:
        frente = 1.0
    if frente < FRENTE_MIN:
        return recorrido, 0.0
    objetivo = min(frente - MARGEN, TRAMO_MAX)
    x0, y0 = posicion(r)
    r.avanzar(VEL, min(objetivo / VEL, 9.0))
    x1, y1 = posicion(r)
    d = math.hypot(x1 - x0, y1 - y0)
    return recorrido + d, d

def main():
    recorrido = 0.0
    atascos = 0
    with Robot(velocidad_maxima=0.20) as r:
        log(f"bateria al empezar: {r.bateria():.2f} V")
        t0 = time.monotonic()

        log("== FASE 1: perimetro (giros de 90 a la derecha, pared a la izquierda) ==")
        for tramo in range(LEGS_PERIMETRO):
            if time.monotonic() - t0 > DURACION_MAX * 0.6:
                log("plazo de la fase 1 vencido"); break
            f, izq, der = claros(r)
            log(f"P{tramo}: frente {f if f is None else round(f,2)} · izq {izq if izq is None else round(izq,2)} · der {der if der is None else round(der,2)}")
            recorrido, d = avanza_hasta_pared(r, f, recorrido)
            if d > 0:
                log(f"  avanzo {d:.2f} m · total {recorrido:.2f} m")
            f2, _, _ = claros(r)
            if f2 is None or f2 < FRENTE_MIN or d == 0.0:
                g = r.girar(-90)
                log(f"  giro -90 -> {g:.1f}")
                if abs(g) < 20 and d < 0.05:
                    atascos += 1
                    log(f"  atasco ({atascos})")
                    r.avanzar(-0.10, 1.5)
                    r.girar(45)
                    if atascos >= 3:
                        log("tres atascos: se aborta"); return
                else:
                    atascos = 0

        log("== FASE 2: interior (rebote al lado despejado) ==")
        for tramo in range(LEGS_INTERIOR):
            if time.monotonic() - t0 > DURACION_MAX:
                log("plazo total vencido"); break
            f, izq, der = claros(r)
            log(f"I{tramo}: frente {f if f is None else round(f,2)} · izq {izq if izq is None else round(izq,2)} · der {der if der is None else round(der,2)}")
            recorrido, d = avanza_hasta_pared(r, f, recorrido)
            if d > 0:
                log(f"  avanzo {d:.2f} m · total {recorrido:.2f} m")
            frente = 1.0 if f is None else f
            if frente < FRENTE_MIN or tramo % 2 == 1:
                izq_v = izq if izq is not None else 3.0
                der_v = der if der is not None else 3.0
                lado = 1 if izq_v >= der_v else -1
                ang = 115 if frente < FRENTE_MIN else 65
                g = r.girar(lado * ang)
                log(f"  giro {lado*ang} -> {g:.1f}")
                if abs(g) < 20 and d < 0.05:
                    atascos += 1
                    log(f"  atasco ({atascos})")
                    r.avanzar(-0.10, 1.5)
                    r.girar(-lado * 90)
                    if atascos >= 3:
                        log("tres atascos: se termina"); break
                else:
                    atascos = 0
        r.parar()
        x, y = posicion(r)
        log(f"fin: {recorrido:.2f} m · odom final ({x:+.2f},{y:+.2f}) · bateria {r.bateria():.2f} V")

if __name__ == '__main__':
    main()
