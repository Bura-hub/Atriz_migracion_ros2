#!/usr/bin/env python3
"""¿Dice la documentación lo que de verdad pasa? Auditoría mecánica del repositorio.

    python3 scripts/auditar_documentacion.py          # informe
    python3 scripts/auditar_documentacion.py --breve  # solo los fallos

Sale con código ≠ 0 si encuentra algo. No toca ningún fichero y no necesita ROS.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════════
La auditoría original del proyecto señaló **la deriva entre documentación y
realidad** como el problema de fondo. El 2026-08-01 aparecieron CUATRO casos en
una sola sesión, y ninguno era descuidado — todos eran documentos de ESTADO que
se quedaron atrás mientras las evidencias estaban al día:

  · el índice del manual daba por «no escritos» cuatro capítulos verificados
  · el plan decía «Nav2 ⏳ pendiente» con Nav2 navegando desde hacía un día
  · y lo peor: el manual 15.3 afirmaba que **la parada de emergencia no cancela
    Nav2** y que estaba «sin comprobar». Las dos cosas eran falsas desde el 31
    de julio. **Una función de seguridad descrita como rota cuando funciona.**

🔴 Un aviso que se ignora cuatro veces no es un aviso: es una tarea pendiente.
   Por eso esto es un comando, como `compilar.sh`.

═══════════════════════════════════════════════════════════════════════════════
LO QUE ESTA HERRAMIENTA **NO** PUEDE HACER
═══════════════════════════════════════════════════════════════════════════════
No sabe si una afirmación es VERDAD. Puede decir que un enlace apunta a un
fichero que no existe, o que se cita un capítulo inexistente; no puede decirte
que «la parada no cancela Nav2» sea mentira.

→ Para eso está la regla, no el script: **al cerrar algo, actualiza el plan y
  `TRASPASO.md` en el MISMO commit que la evidencia.** Y busca TODAS las
  menciones, no la primera: corregir la cabecera del capítulo 4 del plan y
  dejar la subsección 4b diciendo lo contrario ya pasó.
"""
import argparse
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL = os.path.join(RAIZ, '02_manual', 'MANUAL_ATRIZ_ROS2.md')

#: Frases que fueron ciertas y dejaron de serlo. Cada una costó encontrarla.
#: Añade aquí lo que corrijas, para que no vuelva por la puerta de atrás.
OBSOLETAS = [
    (r'todav[íi]a no lo llama',      'provision.sh SÍ llama a fase_7_systemd.sh desde 2026-08-01'),
    (r'9[14] (?:aserciones|comprobaciones)', 'el recuento del verificador cambió: mídelo con --hardware'),
    (r'Falta el multiplicador JSON', 'medido el 2026-08-01: ~2x, 80.7 kB/s por robot'),
    (r'SIN DECIDIR.*namespace',      'CERRADO 2026-08-01: sin namespace'),
    (r'la parada no corta lo que venga de Nav2', 'FALSO: cancelar_nav2 lo hace, verificado con control'),
]


def ficheros(exts=('.md',)):
    for base, dirs, fs in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d != '.git']
        for f in fs:
            if f.endswith(exts):
                yield os.path.join(base, f)


def enlaces_rotos():
    """🔴 Se resuelven RESPECTO AL FICHERO que los contiene, no a la raíz.
    Hacerlo desde la raíz da falsos positivos en cuanto hay subdirectorios, y un
    verificador con falsos positivos se acaba ignorando."""
    malos = []
    for ruta in ficheros():
        base = os.path.dirname(ruta)
        texto = open(ruta, encoding='utf-8', errors='ignore').read()
        for enlace in re.findall(r'\]\(([^)]+)\)', texto):
            enlace = enlace.split('#')[0].strip()
            if not enlace or enlace.startswith(('http://', 'https://', 'mailto:')):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, enlace))):
                malos.append((os.path.relpath(ruta, RAIZ), enlace))
    return malos


def secciones_del_manual():
    texto = open(MANUAL, encoding='utf-8').read()
    return set(re.findall(r'^#{2,4} (?:Capítulo )?(\d+\.?\d*[a-z]?)', texto, re.M))


def citas_rotas():
    """Un `cap. 8.5a` que no existe manda a alguien a buscar durante diez minutos."""
    secs = secciones_del_manual()
    malas = {}
    for ruta in ficheros(('.md', '.txt')):
        texto = open(ruta, encoding='utf-8', errors='ignore').read()
        for c in set(re.findall(r'cap\.?\s*(\d+\.\d+[a-z]?)', texto)):
            if c not in secs:
                malas.setdefault(c, []).append(os.path.relpath(ruta, RAIZ))
    return malas


def secciones_desordenadas():
    """Insertar una sección antes del capítulo siguiente en vez de antes de la
    sección siguiente la deja fuera de orden. Pasó al añadir el 8.4b."""
    # 🔴 Solo DENTRO de cada capítulo. El manual está ordenado por TEMA y no por
    #    número —el capítulo 8 va antes que el 3, a propósito y documentado—, así
    #    que comparar entre capítulos da un falso positivo garantizado.
    texto = open(MANUAL, encoding='utf-8').read()
    ultimo, fallos = {}, []
    for m in re.finditer(r'^### (\d+)\.(\d+)([a-z]?)', texto, re.M):
        cap, sec, suf = int(m.group(1)), int(m.group(2)), m.group(3)
        prev = ultimo.get(cap)
        if prev and (sec, suf) < prev:
            fallos.append(f"{cap}.{sec}{suf} va después de {cap}.{prev[0]}{prev[1]}")
        ultimo[cap] = (sec, suf)
    return fallos


def frases_obsoletas():
    malas = []
    for ruta in ficheros(('.md', '.txt')):
        rel = os.path.relpath(ruta, RAIZ)
        if 'CHANGELOG' in rel or '00_auditoria/evidencia' in rel:
            continue          # son bitácoras: DEBEN conservar lo que se dijo
        texto = open(ruta, encoding='utf-8', errors='ignore').read()
        for patron, porque in OBSOLETAS:
            for m in re.finditer(patron, texto, re.I):
                linea = texto[:m.start()].count('\n') + 1
                # 🔴 Una frase falsa CITADA para dejar constancia de que lo era no
                #    es deriva: es memoria. Las correcciones van en bloque `>`.
                if texto.splitlines()[linea - 1].lstrip().startswith('>'):
                    continue
                malas.append((rel, linea, m.group(0)[:50], porque))
    return malas


def indice_del_manual():
    """El índice se desvió del contenido y nadie lo notó en semanas."""
    texto = open(MANUAL, encoding='utf-8').read()
    reales = set(re.findall(r'^## Capítulo (\d+)', texto, re.M))
    # Las filas del índice son `> | 7 | URDF y árbol TF | ✅ ... |`, y van dentro
    # de una cita al principio. Se buscan en TODO el fichero: acotar por el primer
    # `---` cortaba antes de la tabla y daba «20 capítulos sin listar».
    listados = set(re.findall(r'^> \| (\d+)(?:bis)? \|', texto, re.M))
    return sorted(reales - listados, key=int), sorted(listados - reales, key=int)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--breve', action='store_true')
    a = ap.parse_args()
    fallos = 0

    def bloque(titulo, items, fmt):
        nonlocal fallos
        if items:
            fallos += len(items)
            print(f"\n🔴 {titulo}: {len(items)}")
            for i in items:
                print("   " + fmt(i))
        elif not a.breve:
            print(f"✅ {titulo}: 0")

    print("=" * 74)
    print("AUDITORÍA DE DOCUMENTACIÓN — ¿dice lo que de verdad pasa?")
    print("=" * 74)

    bloque("Enlaces a ficheros que no existen", enlaces_rotos(),
           lambda x: f"{x[0]}  →  {x[1]}")
    bloque("Capítulos citados que no existen",
           [(c, r) for c, rs in citas_rotas().items() for r in rs],
           lambda x: f"cap. {x[0]}  (citado en {x[1]})")
    bloque("Secciones del manual fuera de orden", secciones_desordenadas(), str)
    bloque("Frases que ya son falsas", frases_obsoletas(),
           lambda x: f"{x[0]}:{x[1]}  «{x[2]}»\n      → {x[3]}")

    sin_indice, sin_cuerpo = indice_del_manual()
    bloque("Capítulos escritos que el índice no lista", sin_indice,
           lambda c: f"capítulo {c}")
    bloque("Capítulos que el índice lista y no existen", sin_cuerpo,
           lambda c: f"capítulo {c}")

    print("\n" + "=" * 74)
    if fallos:
        print(f"  🔴 {fallos} problema(s). Corrígelos y vuelve a pasarlo.")
    else:
        print("  ✅ Sin deriva mecánica detectable.")
        print("  ⚠️ Pero esto NO comprueba si una afirmación es VERDAD.")
        print("     La regla sigue siendo tuya: al cerrar algo, actualiza el plan y")
        print("     TRASPASO.md en el MISMO commit que la evidencia — y busca TODAS")
        print("     las menciones, no la primera.")
    print("=" * 74)
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
