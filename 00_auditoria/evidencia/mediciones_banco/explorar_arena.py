#!/usr/bin/env python3
"""⚠️ MUEVE EL ROBOT varios metros: conduccion autonoma para alimentar a SLAM.

Es el guion que hizo `~/mapas/arena.yaml` el 2026-08-18 (ver CHANGELOG de ese
dia): 19 m en dos pasadas, cero atascos, meseta de la curva como criterio de
parada. Requiere el barrido ENCENDIDO y SLAM corriendo (atriz-slam); vigila la
curva del mapa por fuera (celdas ocupadas/libres), no este log.

🔴 Si alguien toca o mueve el robot durante la pasada, el sintoma es venenoso:
lecturas de /scan IDENTICAS tramo tras tramo y giros de 0,0 grados — parece la
congelacion del collision_monitor (evidencia 93) y no lo es. Pregunta a quien
este al lado antes de atribuir.

Estrategia: rebote con sensor — avanza hacia delante mientras haya hueco,
gira hacia el lado mas despejado, y cada pocos tramos gira aunque haya
hueco para cubrir el interior. Acotado en tramos y en tiempo.

Usa atriz.py (la via bendecida): watchdog, limites y cierre seguro ya
resueltos. El barrido esta encendido de antes, asi que atriz.py NO lo
apagara al salir (apaga solo lo que enciende el).
"""
import sys, math, time

sys.path.insert(0, '/home/sphero/atriz_ws/src/Atriz_rvr/scripts/estudiantes')
from atriz import Robot, ErrorAtriz

VEL = 0.15            # m/s, suave para mapear
FRENTE_MIN = 0.70     # m: por debajo, no se avanza, se gira
MARGEN = 0.50         # m que se dejan sin recorrer hasta el obstaculo
TRAMO_MAX = 1.2       # m por tramo
TRAMOS = 18
DURACION_MAX = 360.0  # s

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def claros(robot):
    """Distancia mediana en tres conos: frente, izquierda (+90), derecha (-90)."""
    barrido = robot._ultimo('_scan', timeout=5.0, que='/scan')
    def cono(centro_deg, semi_deg=15.0):
        centro = math.radians(centro_deg)
        semi = math.radians(semi_deg)
        vals = []
        for i, d in enumerate(barrido.ranges):
            a = barrido.angle_min + i * barrido.angle_increment
            a = math.atan2(math.sin(a - centro), math.cos(a - centro))
            if abs(a) <= semi and barrido.range_min < d < barrido.range_max:
                vals.append(d)
        if not vals:
            return None  # sin retorno valido: o muy lejos o ciego — se trata aparte
        vals.sort()
        return vals[len(vals) // 2]
    return cono(0), cono(90), cono(-90)

def posicion(robot):
    p = robot._ultimo('_odom', timeout=5.0, que='/odom').pose.pose.position
    return p.x, p.y

def main():
    recorrido = 0.0
    with Robot(velocidad_maxima=0.20) as r:
        log(f"bateria al empezar: {r.bateria():.2f} V")
        t0 = time.monotonic()
        atascos = 0
        for tramo in range(TRAMOS):
            if time.monotonic() - t0 > DURACION_MAX:
                log("plazo de exploracion vencido")
                break
            f, izq, der = claros(r)
            f_txt = 'sin retorno' if f is None else f'{f:.2f} m'
            log(f"tramo {tramo}: frente {f_txt} · izq {izq if izq is None else round(izq,2)} · der {der if der is None else round(der,2)}")

            avanzo = 0.0
            # None en el frente = probablemente lejos; se avanza un paso corto y prudente
            frente = 1.0 if f is None else f
            if frente >= FRENTE_MIN:
                objetivo = min(frente - MARGEN, TRAMO_MAX)
                x0, y0 = posicion(r)
                r.avanzar(VEL, min(objetivo / VEL, 8.0))
                x1, y1 = posicion(r)
                avanzo = math.hypot(x1 - x0, y1 - y0)
                recorrido += avanzo
                log(f"  avance pedido {objetivo:.2f} m · odometria {avanzo:.2f} m · total {recorrido:.2f} m")

            # girar si no hay hueco, o cada tercer tramo para cubrir el interior
            if frente < FRENTE_MIN or tramo % 3 == 2:
                izq_v = izq if izq is not None else 3.0
                der_v = der if der is not None else 3.0
                lado = 1 if izq_v >= der_v else -1
                angulo = 105 if frente < FRENTE_MIN else 70
                girado = r.girar(lado * angulo)
                girado = 0.0 if girado is None else girado
                log(f"  giro pedido {lado*angulo} · girado {girado:.1f}")
                if abs(girado) < 20 and avanzo < 0.05:
                    atascos += 1
                    log(f"  posible congelacion del collision_monitor ({atascos})")
                    # retroceso corto y prudente por donde se vino (sin seguridad atras)
                    r.avanzar(-0.10, 1.5)
                    r.girar(-lado * 90)
                    if atascos >= 3:
                        log("tres atascos: se termina la exploracion")
                        break
                else:
                    atascos = 0
        r.parar()
        log(f"fin: {recorrido:.2f} m recorridos · bateria {r.bateria():.2f} V")

if __name__ == '__main__':
    main()
