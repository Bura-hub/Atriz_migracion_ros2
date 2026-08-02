# Prueba de aceptación — plan de implementación

> **Para quien lo ejecute:** implementa tarea por tarea, en orden. Los pasos usan casillas
> (`- [ ]`) para seguimiento. **No saltes las tareas 1 y 2**: son lógica pura con tests, y las
> tareas 4-11 dependen de sus nombres exactos.

**Objetivo:** una prueba de aceptación guiada, de arranque en frío a navegación autónoma, que
diga si se puede empezar la plataforma web sobre este robot.

**Arquitectura:** la lógica pura (bandas, veredictos, informe) va en `aceptacion_nucleo.py`, sin
ROS y con tests unitarios. Todo lo que toca hardware va en `prueba_aceptacion.py`, un proceso con
un nodo ROS persistente y diez fases guiadas. Se separan porque **el veredicto se puede probar sin
robot y el hardware no**: si van juntos, la lógica de decisión solo se ejercita moviendo motores.

**Herramientas:** Python 3.12, `rclpy` (Jazzy), `pytest` 7.4.4, `nav2_msgs/NavigateToPose`.

📎 **Diseño aprobado:** `03_operacion/PRUEBA_ACEPTACION.md`. Este plan lo implementa; si algo
choca, manda el diseño.

📝 **Dónde vive este plan.** La skill sugiere `docs/superpowers/plans/`; se guarda en
`00_auditoria/planes/` para no abrir un árbol nuevo en un repositorio ya organizado por fases.

---

## Restricciones globales

Aplican a **todas** las tareas. Están en `CLAUDE.md` y no se negocian:

- **Sin secretos en el repositorio.** Ni contraseñas, ni claves, ni la PSK del WiFi.
- **Nada se documenta sin ejecutarse.** Lo no ejecutado se marca **NO VERIFICADO**.
- **Nada se ejecuta sin documentarse.**
- **Medir antes de atribuir.** Ningún número inventado; cada umbral cita su fuente.
- **Nunca `pkill -f`.** Matar por `comm` con `ps`, comparando el prefijo truncado a 15 caracteres.
- **Sin trailers de co-autoría** en los commits.
- **Timeout en toda llamada a servicio y a acción.** Sin excepción.
- Avisar de las acciones físicas; parar el nodo al terminar una prueba.

---

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `scripts/aceptacion_nucleo.py` | **Crear.** Lógica pura: `Resultado`, las bandas, los cuatro veredictos, la regla de vía libre y el formato del informe. **Cero imports de ROS** |
| `scripts/pruebas/test_aceptacion_nucleo.py` | **Crear.** Tests unitarios del núcleo. Corren sin robot |
| `scripts/prueba_aceptacion.py` | **Crear.** Orquestador: nodo ROS persistente, guardas, Ctrl-C, puertas, las diez fases y la CLI |
| `03_operacion/PRUEBA_ACEPTACION.md` | **Modificar** al final: añadir la sección «Cómo leer el informe» |
| `CHANGELOG.md`, `TRASPASO.md` | **Modificar** al final |

**Por qué dos ficheros y no uno:** el núcleo se prueba con `pytest` en un portátil, sin robot y
sin ROS. Metido en el orquestador, la única forma de ejercitar la lógica de veredictos sería
mover motores — y entonces nadie la probaría.

---

## Tarea 1: El núcleo — resultados y bandas

**Ficheros:**
- Crear: `scripts/aceptacion_nucleo.py`
- Crear: `scripts/pruebas/test_aceptacion_nucleo.py`

**Interfaces:**
- Consume: nada.
- Produce: `Resultado` (dataclass), las constantes `PASA/REVISAR/FALLO/PENDIENTE`,
  `juzgar_banda(concepto, valor, lo, hi, base, fase, unidad='') -> Resultado`,
  `juzgar_categorico(concepto, ok, fase, detalle='') -> Resultado`,
  `no_verificado(concepto, fase, motivo) -> Resultado`.

- [ ] **Paso 1: Escribir los tests que fallan**

```python
# scripts/pruebas/test_aceptacion_nucleo.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aceptacion_nucleo import (
    PASA, REVISAR, FALLO, PENDIENTE,
    Resultado, juzgar_banda, juzgar_categorico, no_verificado,
)


def test_dentro_de_banda_pasa():
    r = juzgar_banda('move_timed 2 s', 30.3, 24.0, 37.0, 'evidencia 26: 30.3 cm', 'F4', 'cm')
    assert r.veredicto == PASA
    assert r.medido == 30.3


def test_fuera_de_banda_es_revisar_no_fallo():
    # 🔴 La regla que define esta prueba: con n=1 detras, un numero raro NO es
    #    un suspenso. Si esto se convierte en FALLO, el diseño esta roto.
    r = juzgar_banda('move_timed 2 s', 12.0, 24.0, 37.0, 'evidencia 26: 30.3 cm', 'F4', 'cm')
    assert r.veredicto == REVISAR


def test_los_extremos_de_la_banda_entran():
    assert juzgar_banda('x', 24.0, 24.0, 37.0, 'b', 'F4').veredicto == PASA
    assert juzgar_banda('x', 37.0, 24.0, 37.0, 'b', 'F4').veredicto == PASA


def test_valor_ausente_es_no_verificado_no_pasa():
    # Un None no puede colarse como aprobado: es justo el fallo que esta prueba
    # existe para evitar (un hueco leido como «bien»).
    r = juzgar_banda('ritmo de /odom', None, 13.0, 99.0, 'Fase 4: 16.5 Hz', 'F1', 'Hz')
    assert r.veredicto == PENDIENTE
    assert 'NO VERIFICADO' in r.detalle


def test_categorico_falso_es_fallo():
    r = juzgar_categorico('la parada de emergencia para', False, 'F4')
    assert r.veredicto == FALLO


def test_categorico_cierto_pasa():
    assert juzgar_categorico('nodo rvr_driver presente', True, 'F0').veredicto == PASA


def test_no_verificado_lleva_el_motivo():
    r = no_verificado('netplan 60-atriz.yaml', 'F0', 'necesita root')
    assert r.veredicto == PENDIENTE
    assert 'necesita root' in r.detalle


def test_el_detalle_dice_contra_que_se_comparo():
    r = juzgar_banda('collision_monitor', 22.0, 0.0, 15.0, 'CHANGELOG:1824: 9.9 cm', 'F6', 'cm')
    assert '22.0' in r.detalle and 'CHANGELOG:1824' in r.detalle
```

- [ ] **Paso 2: Correr los tests para verificar que fallan**

Ejecuta: `cd ~/atriz_migracion && python3 -m pytest scripts/pruebas/ -v`
Esperado: FALLAN todos con `ModuleNotFoundError: No module named 'aceptacion_nucleo'`.

- [ ] **Paso 3: Escribir la implementación mínima**

```python
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
```

- [ ] **Paso 4: Correr los tests para verificar que pasan**

Ejecuta: `cd ~/atriz_migracion && python3 -m pytest scripts/pruebas/ -v`
Esperado: **8 passed**.

- [ ] **Paso 5: Commit**

```bash
cd ~/atriz_migracion
git add scripts/aceptacion_nucleo.py scripts/pruebas/test_aceptacion_nucleo.py
git commit -F - <<'EOF'
El nucleo de la prueba de aceptacion: bandas y veredictos, con tests

Logica pura, sin ROS, para que se pueda probar sin robot. La regla que define el
diseño esta cubierta por un test: fuera de banda es REVISAR, NUNCA fallo, porque
casi todas las bases son n=1 a n=4.

Y un valor ausente da PENDIENTE, no PASA: un hueco leido como «bien» es justo el
fallo que esta prueba existe para evitar.
EOF
```

---

## Tarea 2: El núcleo — informe y regla de vía libre

**Ficheros:**
- Modificar: `scripts/aceptacion_nucleo.py`
- Modificar: `scripts/pruebas/test_aceptacion_nucleo.py`

**Interfaces:**
- Consume: `Resultado`, `PASA/REVISAR/FALLO/PENDIENTE`, `BLOQUEAN` de la tarea 1.
- Produce: `PENDIENTES_CONOCIDOS` (lista de `Resultado`), `hay_via_libre(resultados) -> bool`,
  `resumen(resultados) -> dict[str,int]`, `formatear_informe(resultados, cabecera) -> str`.

- [ ] **Paso 1: Escribir los tests que fallan**

```python
# añadir al final de scripts/pruebas/test_aceptacion_nucleo.py
from aceptacion_nucleo import (
    PENDIENTES_CONOCIDOS, hay_via_libre, resumen, formatear_informe,
)


def test_sin_fallos_ni_pendientes_hay_via_libre():
    assert hay_via_libre([juzgar_categorico('x', True, 'F0')]) is True


def test_un_fallo_bloquea():
    assert hay_via_libre([juzgar_categorico('x', False, 'F0')]) is False


def test_revisar_solo_no_bloquea():
    r = juzgar_banda('x', 99.0, 0.0, 1.0, 'b', 'F4')
    assert r.veredicto == REVISAR
    assert hay_via_libre([r]) is True


def test_un_pendiente_bloquea():
    assert hay_via_libre([no_verificado('x', 'F0', 'sin root')]) is False


def test_los_pendientes_conocidos_bloquean_una_pasada_perfecta():
    # 🔴 Consecuencia elegida a proposito: aunque el robot este impecable, la
    #    primera pasada NO da via libre, porque rosbridge sigue sin autenticacion.
    todo_bien = [juzgar_categorico('x', True, 'F0')]
    assert hay_via_libre(todo_bien) is True
    assert hay_via_libre(todo_bien + PENDIENTES_CONOCIDOS) is False


def test_rosbridge_sin_autenticacion_esta_entre_los_pendientes():
    assert any('rosbridge' in p.concepto.lower() for p in PENDIENTES_CONOCIDOS)


def test_resumen_cuenta_cada_veredicto():
    c = resumen([juzgar_categorico('a', True, 'F0'),
                 juzgar_categorico('b', False, 'F0'),
                 no_verificado('c', 'F0', 'm')])
    assert c[PASA] == 1 and c[FALLO] == 1 and c[PENDIENTE] == 1 and c[REVISAR] == 0


def test_el_informe_niega_la_via_libre_cuando_hay_fallo():
    txt = formatear_informe([juzgar_categorico('la parada para', False, 'F4')], 'cabecera')
    assert 'VIA LIBRE' not in txt.replace('NO HAY VIA LIBRE', '')
    assert 'la parada para' in txt


def test_el_informe_da_via_libre_cuando_todo_pasa():
    txt = formatear_informe([juzgar_categorico('x', True, 'F0')], 'cabecera')
    assert 'VIA LIBRE PARA LA FASE 5' in txt
```

- [ ] **Paso 2: Correr los tests para verificar que fallan**

Ejecuta: `cd ~/atriz_migracion && python3 -m pytest scripts/pruebas/ -v`
Esperado: los 9 nuevos fallan con `ImportError: cannot import name 'PENDIENTES_CONOCIDOS'`.

- [ ] **Paso 3: Escribir la implementación**

```python
# añadir al final de scripts/aceptacion_nucleo.py

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
```

- [ ] **Paso 4: Correr los tests para verificar que pasan**

Ejecuta: `cd ~/atriz_migracion && python3 -m pytest scripts/pruebas/ -v`
Esperado: **17 passed**.

- [ ] **Paso 5: Commit**

```bash
cd ~/atriz_migracion
git add scripts/aceptacion_nucleo.py scripts/pruebas/test_aceptacion_nucleo.py
git commit -F - <<'EOF'
Informe y regla de via libre, con los cuatro pendientes que la bloquean

`hay_via_libre` solo es cierto con CERO fallos y CERO pendientes; REVISAR no
bloquea. Los cuatro pendientes conocidos viven en el codigo y no en el documento
para que no se desincronicen.

📝 Un test fija la consecuencia elegida a proposito: aunque el robot este
   impecable, la primera pasada NO dara via libre, porque rosbridge sigue sin
   autenticacion. «Robot perfecto» y «via libre» no son lo mismo.
EOF
```

---

## Tarea 3: El orquestador — nodo, guardas, Ctrl-C y puertas

**Ficheros:**
- Crear: `scripts/prueba_aceptacion.py`

**Interfaces:**
- Consume: todo el núcleo de las tareas 1 y 2.
- Produce: clase `Aceptacion` con `.nodo`, `.res` (lista de `Resultado`), `.add(r)`,
  `.puerta(texto)`, `.parada_emergencia()`, `.llamar(cliente, req, timeout)`,
  `.esperar(topic, tipo, qos, segundos) -> list`, `.pos_yaw() -> (x, y, yaw_rad)`;
  y las funciones sueltas `driver_corriendo()`, `matar_por_comm(prefijo)`.

- [ ] **Paso 1: Escribir el esqueleto con las guardas**

```python
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
    nombre — incluida esta misma prueba."""
    n = 0
    try:
        s = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True,
                           text=True, timeout=5)
        for linea in s.stdout.splitlines()[1:]:
            partes = linea.split(None, 1)
            if len(partes) == 2 and partes[1].strip().startswith(prefijo[:15]):
                os.kill(int(partes[0]), signal.SIGINT)
                n += 1
    except Exception:                                            # noqa: BLE001
        pass
    return n


class Aceptacion:
    def __init__(self, guiada=True):
        self.res: list[Resultado] = []
        self.guiada = guiada
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
        fin = time.monotonic() + segundos
        while time.monotonic() < fin:
            self.ex.spin_once(timeout_sec=0.05)
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

    def cerrar(self):
        self.parada_emergencia()
        self.liberar_parada()
        try:
            self.nodo.destroy_node()
            rclpy.shutdown()
        except Exception:                                        # noqa: BLE001
            pass


def delta_angulo(a, b) -> float:
    """b - a normalizado a (-pi, pi].

    🔴 Sin esto NO SE PUEDE MEDIR UN GIRO DE 360°: atan2 devuelve -pi..pi, asi que
       una vuelta entera se lee como ~0. F5 acumula estos deltas.
    """
    d = b - a
    while d > math.pi:
        d -= 2 * math.pi
    while d <= -math.pi:
        d += 2 * math.pi
    return d
```

- [ ] **Paso 2: Añadir las guardas de arranque y el manejo de Ctrl-C**

```python
# añadir a scripts/prueba_aceptacion.py

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
            a.cerrar()
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
        finally:
            signal.signal(signal.SIGINT, previo)
        a.cerrar()
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Paso 3: Añadir el despachador de fases y el informe**

```python
# añadir a scripts/prueba_aceptacion.py, ANTES de main()

FASES = []          # se llena con @fase en las tareas 4-11


def fase(clave, titulo, mueve=False):
    def deco(fn):
        FASES.append((clave, titulo, mueve, fn))
        return fn
    return deco


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
    print(formatear_informe(a.res, cabecera()))
    print(f'\n  📄 informe: {ruta}')
    return 0 if hay_via_libre(a.res) else 2


def cabecera() -> str:
    return (f'PRUEBA DE ACEPTACION · {os.uname().nodename} · '
            f'{time.strftime("%Y-%m-%d %H:%M:%S")}')


def escribir_informe(a: Aceptacion, abortada=False) -> str:
    """Se escribe SIEMPRE, pase o falle. Un informe que solo aparece cuando todo
    va bien no sirve para depurar nada."""
    res = list(a.res) + PENDIENTES_CONOCIDOS
    d = pathlib.Path.home() / 'atriz_migracion' / '00_auditoria' / 'evidencia_24_04'
    d.mkdir(parents=True, exist_ok=True)
    ruta = d / f'47_aceptacion_{time.strftime("%Y%m%d_%H%M%S")}.txt'
    cab = cabecera() + ('  ⚠️ ABORTADA POR Ctrl-C' if abortada else '')
    ruta.write_text(formatear_informe(res, cab), encoding='utf-8')
    a.res = res
    return str(ruta)
```

- [ ] **Paso 4: Verificar que arranca y que `--help` NO mueve nada**

```bash
cd ~/atriz_migracion
python3 -c "import ast; ast.parse(open('scripts/prueba_aceptacion.py').read())" && echo "sintaxis ok"
python3 scripts/prueba_aceptacion.py --help          # NO debe tocar el robot
python3 scripts/prueba_aceptacion.py --desde F9      # sin fases aun: informe vacio
```
Esperado: `--help` imprime las opciones sin despertar nada; `--desde F9` da
`🔴 fase «F9» desconocida` porque aún no hay fases registradas.

- [ ] **Paso 5: Verificar que Ctrl-C para el robot de verdad**

```bash
# En una terminal:
cd ~/atriz_migracion && python3 scripts/prueba_aceptacion.py --desde F0 &
sleep 6 && kill -INT %1
# Comprobar que la parada llego AL DRIVER, no solo que el script imprimio algo:
journalctl -u atriz-robot --since "-1 min" --no-pager | grep "PARADA DE EMERGENCIA"
```
Esperado: al menos una línea `PARADA DE EMERGENCIA` en el journal del driver, y
salida 130. **Si no aparece en el journal, el manejador no sirve** — no basta con
que el script diga que la envió.

- [ ] **Paso 6: Commit**

```bash
cd ~/atriz_migracion
git add scripts/prueba_aceptacion.py
git commit -F - <<'EOF'
Esqueleto de la prueba de aceptacion: nodo persistente, guardas y Ctrl-C

Un solo nodo ROS para las diez fases, en vez de doce herramientas arrancando y
parando la suya y despertando al RVR cada vez.

Lo aprendido en la auditoria del 2026-08-01, aplicado desde el principio:

  · Ctrl-C publica la parada de emergencia y ENMASCARA LA SEÑAL mientras dura la
    recuperacion. move_timed corre en el DRIVER: matar el cliente no para nada.
  · Toda llamada a servicio lleva tope. Una sola sin el cuelga la prueba entera
    en silencio.
  · El ritmo se mide con ejecutor PERSISTENTE y entre el primer y el ultimo
    sello, no mensajes/duracion.
  · `ps -o comm` trunca a 15 caracteres, y nunca `pkill -f`.
  · argparse lo primero: `--help` no despierta el robot.

Y dos guardas: bateria por debajo de 7.0 V aborta (con la bateria caida
mediriamos una regresion que no existe), y si el driver no corre no arranca.
EOF
```

---

## Tarea 4: F0 arranque en frío y F1 telemetría

**Ficheros:**
- Modificar: `scripts/prueba_aceptacion.py`

**Interfaces:**
- Consume: `Aceptacion`, `fase`, `juzgar_*`, `no_verificado`, `Resultado`, `ARRANQUE_MAXIMO_S`.
- Produce: las fases `F0` y `F1` registradas en `FASES`.

- [ ] **Paso 1: Escribir F0**

```python
# añadir a scripts/prueba_aceptacion.py, antes de ejecutar()

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
```

- [ ] **Paso 2: Escribir F1**

```python
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
```

- [ ] **Paso 3: Ejecutar F0 y F1 contra el robot**

```bash
cd ~/atriz_migracion && python3 scripts/prueba_aceptacion.py --desde F0
```
Esperado: F0 avisa de que el `uptime` es alto si no acabas de reiniciar (**eso es
correcto**: la fase hace su trabajo), los 6 nodos en `ok`, `Restart=always` con
PID cambiado, y F1 con `/odom` e `/imu` sobre 13 Hz.
⚠️ F0 **mata el driver a propósito**. Tarda ~40 s en volver.

- [ ] **Paso 4: Commit**

```bash
cd ~/atriz_migracion
git add scripts/prueba_aceptacion.py
git commit -F - <<'EOF'
F0 arranque en frio y F1 telemetria

F0 comprueba el uptime antes que nada: sin eso la prueba «pasaria» sobre un
sistema encendido hace dias y arreglado a mano, que es el sesgo que existe para
eliminar. Y ejercita Restart=always, documentado hasta hoy como SIN EJERCITAR.

🔴 El journal se mira SOLO en F0, y esta comentado por que: el driver registra la
   parada de emergencia con nivel ERROR y F4/F6 la provocan a proposito, asi que
   repetir la comprobacion al final encontraria los errores que la propia prueba
   causo y los llamaria regresion.

F1 mide DERIVA de yaw, nunca el valor absoluto: reset_yaw() no pone el yaw a cero
y `sudo reboot` reinicia la Pi, no el RVR.
EOF
```

---

## Tarea 5: F2 LIDAR y F3 luces

**Ficheros:**
- Modificar: `scripts/prueba_aceptacion.py`

**Interfaces:**
- Consume: `Aceptacion.puerta`, `.llamar`, `.ritmo`, `.esperar`.
- Produce: las fases `F2` y `F3`.

- [ ] **Paso 1: Escribir F2**

```python
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
```

- [ ] **Paso 2: Escribir F3**

Las interfaces reales, inspeccionadas en el robot el 2026-08-01 — **no son las que
uno supondría**:

| Servicio | Tipo | Petición | Respuesta |
|---|---|---|---|
| `/set_led_rgb` | `atriz_rvr_msgs/srv/SetLEDRGB` (**«LED» en mayúsculas**) | `int32 led_id, red, green, blue` | `bool success, string message` |
| `/set_multiple_leds` | `SetMultipleLEDs` | `int32[] led_ids, red_values, green_values, blue_values` | `bool success, string message` |
| `/set_leds` | `SetLeds` | `int32[] rgb_color` | **ninguna** — no tiene `success` |

`led_id` indexa `rvr_driver_node.py:659` — `0` es `headlight_left` y **`11` es
`all_lights`**. El driver pone `all_lights` el último a propósito, para que
`led_id=0` sea una luz concreta y no «todas».

```python
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
```

- [ ] **Paso 3: Ejecutar F2 y F3**

```bash
cd ~/atriz_migracion && python3 scripts/prueba_aceptacion.py --desde F2
```
Esperado: `/scan` a ~10 Hz mientras barre y **cero mensajes** antes y después;
los tres colores visibles en el robot.
📝 Las interfaces de LED **ya están inspeccionadas en el robot** (tabla de
arriba), así que el código de F3 usa los tipos y campos reales, no supuestos.

- [ ] **Paso 4: Commit**

```bash
cd ~/atriz_migracion
git add scripts/prueba_aceptacion.py
git commit -m "F2 LIDAR y F3 luces

F2 comprueba las tres cosas del barrido: que arranca APAGADO (por decision), que
da ~10 Hz con rangos utiles, y que stop_scan lo calla de verdad. Ademas vigila
que el parche contra la inundacion del journal siga puesto.

F3 la juzga el operador: no hay forma de leer un LED desde el software, el robot
no tiene con que mirarse. Si nadie mira, queda NO VERIFICADO — no PASA."
```

---

## Tarea 6: F4 movimiento básico y F5 ángulos

**Ficheros:**
- Modificar: `scripts/prueba_aceptacion.py`

**Interfaces:**
- Consume: `Aceptacion.pos_yaw`, `.puerta`, `.parada_emergencia`, `delta_angulo`.
- Produce: las fases `F4` y `F5`.

- [ ] **Paso 1: Escribir F4**

```python
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
```

- [ ] **Paso 2: Escribir F5, la fase que cierra el hueco**

```python
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
                acum += delta_angulo(prev, q)
                prev = q
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
    a.add(juzgar_categorico(
        'angular positivo gira a la IZQUIERDA (regla de la mano derecha)',
        medido is not None and medido < 0, 'F5',
        f'con angular NEGATIVO el Δyaw fue {medido:.1f}° '
        f'(negativo = derecha, como manda REP-103)'))
```

- [ ] **Paso 3: Añadir el lector rápido de yaw que F5 necesita**

```python
# añadir dentro de la clase Aceptacion, junto a pos_yaw()

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
```

- [ ] **Paso 4: Ejecutar F4 y F5**

```bash
cd ~/atriz_migracion && python3 scripts/prueba_aceptacion.py --desde F4
```
Esperado: ~30 cm de ida y de vuelta; la parada de emergencia corta en menos de
12 cm y **rechaza `move_timed` con `success=False`**; y los tres giros con su
Δyaw medido. **Anota los tres números: son la referencia que no existía.**

- [ ] **Paso 5: Commit**

```bash
cd ~/atriz_migracion
git add scripts/prueba_aceptacion.py
git commit -F - <<'EOF'
F4 movimiento y F5 ANGULOS, el hueco que nadie habia medido

move_to_pos_and_yaw estaba verificado en DISTANCIA (0.20 m -> 19.5 cm) pero su
componente de yaw no, y move_to_pose figuraba como «✅» sin un numero detras.

F5 mide Δyaw ACUMULADO, nunca yaw absoluto, y esta comentado por que:

  · reset_yaw() no pone el yaw a cero (rvr_driver_node.py:316). Solo se pone a
    cero AL ENCENDER EL RVR, y `sudo reboot` reinicia la Pi, no el RVR.
  · Y sin acumular deltas no se puede medir un giro de 360°: atan2 devuelve
    -pi..pi, asi que una vuelta entera se leeria como ~0.

Su banda es DE CORDURA, no de aceptacion (±40 %): no hay base historica contra la
que suspender, asi que esta pasada fija la referencia. Marcado en el propio texto
del resultado para que nadie lo lea como un aprobado medido.

F4 comprueba ademas que la parada de emergencia no solo FRENA sino que RECHAZA
los servicios de movimiento con success=False.
EOF
```

---

## Tarea 7: F6 seguridad y F7 autónomo

**Ficheros:**
- Modificar: `scripts/prueba_aceptacion.py`

**Interfaces:**
- Consume: `Aceptacion`, `matar_por_comm`, `delta_angulo`.
- Produce: las fases `F6` y `F7`.

- [ ] **Paso 1: Escribir F6**

```python
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
```

- [ ] **Paso 2: Escribir F7**

```python
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
```

- [ ] **Paso 3: Ejecutar F6 y F7**

```bash
cd ~/atriz_migracion && python3 scripts/prueba_aceptacion.py --desde F6
```
Esperado: el robot se para solo antes de la pared (≤15 cm); el watchdog corta al
dejar de publicar; Nav2 completa los dos objetivos y **no aparece
`Failed to make progress`**.
⚠️ Si Nav2 no levanta en 90 s, mira `ros2 lifecycle list` — probablemente algún
nodo se quedó en `unconfigured`, y eso es un FALLO real que hay que investigar,
no un timeout que subir.

- [ ] **Paso 4: Commit**

```bash
cd ~/atriz_migracion
git add scripts/prueba_aceptacion.py
git commit -F - <<'EOF'
F6 seguridad y F7 navegacion autonoma con sorteo de obstaculos

F6 conduce contra una pared y comprueba que la capa de seguridad para sola
(base 9.9 cm a 0.25 m/s), y que dejar de publicar cmd_vel tambien corta
(base: quieto en 527 ms, ~7.9 cm).

F7 lanza SLAM y Nav2, manda el objetivo limpio de 1.50 m y luego el mismo con el
obstaculo, midiendo el desvio lateral contra los 30 cm del manual 11.13.

🔴 Y vigila que no reaparezca «Failed to make progress»: el SimpleProgressChecker
   de fabrica exigia 5 cm/s de media, y con el collision_monitor frenando eso se
   dispara solo. Con una capa de seguridad delante, ir despacio ya no es prueba
   de estar atascado. El arreglo (required_movement_radius 0.25 / 15 s) tiene que
   seguir en pie.

SLAM y Nav2 se matan por comm, nunca con pkill -f: ese patron casaria con la
linea de comando de esta misma prueba.
EOF
```

---

## Tarea 8: F8 web, F9 veredicto y documentación

**Ficheros:**
- Modificar: `scripts/prueba_aceptacion.py`
- Modificar: `03_operacion/PRUEBA_ACEPTACION.md`, `CHANGELOG.md`, `TRASPASO.md`

**Interfaces:**
- Consume: todo lo anterior.
- Produce: las fases `F8` y `F9`; la prueba completa ejecutable de F0 a F9.

- [ ] **Paso 1: Escribir F8 y F9**

```python
@fase('F8', 'Web — rosbridge de verdad, no «el puerto esta abierto»')
def f8(a: Aceptacion) -> None:
    import json
    import socket
    import base64
    import struct

    # Handshake WebSocket a mano: no hay dependencia de websockets en el robot,
    # y meterla solo para esto no compensa.
    try:
        s = socket.create_connection(('127.0.0.1', 9090), timeout=10)
    except OSError as e:
        a.add(juzgar_categorico('rosbridge acepta conexiones en el 9090',
                                False, 'F8', str(e)))
        return
    clave = base64.b64encode(os.urandom(16)).decode()
    s.send(f'GET / HTTP/1.1\r\nHost: 127.0.0.1:9090\r\nUpgrade: websocket\r\n'
           f'Connection: Upgrade\r\nSec-WebSocket-Key: {clave}\r\n'
           f'Sec-WebSocket-Version: 13\r\n\r\n'.encode())
    resp = s.recv(4096)
    a.add(juzgar_categorico('rosbridge completa el handshake WebSocket',
                            b'101' in resp[:20], 'F8', resp[:60].decode('latin1')))

    def enviar(obj):
        d = json.dumps(obj).encode()
        cab = bytearray([0x81])
        m = os.urandom(4)
        if len(d) < 126:
            cab.append(0x80 | len(d))
        else:
            cab.append(0x80 | 126)
            cab += struct.pack('>H', len(d))
        cab += m
        cab += bytes(b ^ m[i % 4] for i, b in enumerate(d))
        s.send(bytes(cab))

    enviar({'op': 'subscribe', 'topic': '/odom', 'type': 'nav_msgs/msg/Odometry'})
    s.settimeout(12)
    recibido = False
    try:
        for _ in range(6):
            if b'/odom' in s.recv(65536):
                recibido = True
                break
    except socket.timeout:
        pass
    s.close()
    a.add(juzgar_categorico('la web recibe /odom por rosbridge', recibido, 'F8',
                            'suscripcion real, no solo el puerto abierto'))


@fase('F9', 'Veredicto')
def f9(a: Aceptacion) -> None:
    print('\n  Los pendientes conocidos se añaden al informe y BLOQUEAN la via')
    print('  libre por decision del 2026-08-01. Ver PENDIENTES_CONOCIDOS.')
```

- [ ] **Paso 2: Correr la prueba entera contra el robot, tras un reinicio real**

```bash
sudo reboot
# esperar, entrar por SSH, y:
cd ~/atriz_migracion && python3 scripts/prueba_aceptacion.py
```
Esperado: llega a F9 y escribe el informe. **Va a terminar sin vía libre**
aunque el robot esté impecable, porque los cuatro pendientes bloquean — es el
comportamiento acordado, no un fallo.

- [ ] **Paso 3: Añadir «Cómo leer el informe» al diseño**

```markdown
## Cómo leer el informe

`00_auditoria/evidencia_24_04/47_aceptacion_<fecha>.txt`. Se escribe **siempre**,
incluso si abortas con Ctrl-C — un informe que solo aparece cuando todo va bien
no sirve para depurar nada.

| Marca | Qué hacer |
|---|---|
| `[FALLO]` | **Para y arréglalo.** Es categórico: algo no funciona |
| `[PEND ]` | Una decisión abierta o algo que no se pudo medir. **Bloquea la vía libre** |
| `[REV  ]` | Un número fuera de banda. Míralo, pero recuerda que la base es n=1–4 |
| `[  ok ]` | Dentro de banda |

**Código de salida:** `0` con vía libre, `2` sin ella, `1` si abortaron las
guardas, `130` si paraste con Ctrl-C.
```

- [ ] **Paso 4: Actualizar CHANGELOG y TRASPASO con los números REALES**

⚠️ **No inventes los números.** Cópialos del informe que acabas de generar. Los
tres Δyaw de F5 son **referencia nueva**: hasta esta pasada no existían, así que
anótalos como base con su fecha y su `n=1`.

- [ ] **Paso 5: Commit**

```bash
cd ~/atriz_migracion
git add -A
git commit -F - <<'EOF'
F8 web y F9 veredicto: la prueba de aceptacion corre entera

F8 no se conforma con «el puerto 9090 esta abierto»: hace el handshake WebSocket
y se suscribe a /odom como haria la web, porque un puerto abierto no demuestra
que rosbridge sirva datos.

Primera pasada completa tras un reinicio de verdad. Los numeros del informe se
copian tal cual; los tres Δyaw de F5 son referencia NUEVA (n=1, con su fecha):
hasta ahora el angulo no se habia medido nunca.

📝 La pasada termina SIN via libre aunque el robot este impecable, porque los
   cuatro pendientes bloquean. Es lo acordado: «robot perfecto» y «via libre» no
   son lo mismo mientras rosbridge siga sin autenticacion.
EOF
```

---

## Autorrevisión de este plan

**Cobertura del diseño:** las diez fases tienen tarea (F0-F1 → t4, F2-F3 → t5,
F4-F5 → t6, F6-F7 → t7, F8-F9 → t8); los cuatro veredictos y la regla de vía
libre → t2; umbrales → t1 y en cada fase con su fuente; Ctrl-C, guardas y
puertas → t3; informe siempre escrito → t3; `--desde` → t3.

**Sin marcadores de posición:** cada paso lleva el código real. Los dos puntos
donde el implementador puede encontrarse algo distinto están marcados con qué
comando usar para averiguarlo (`ros2 service type` para los LED en t5,
`ros2 lifecycle list` para Nav2 en t7), no con un «ajusta si hace falta».

**Consistencia de nombres:** `juzgar_banda`, `juzgar_categorico`, `no_verificado`,
`hay_via_libre`, `formatear_informe`, `PENDIENTES_CONOCIDOS`, `Aceptacion.add`,
`.puerta`, `.llamar`, `.esperar`, `.ritmo`, `.pos_yaw`, `.pos_yaw_rapido`,
`delta_angulo`, `matar_por_comm`, `driver_corriendo` se usan con la misma firma
en todas las tareas. `pos_yaw_rapido` se define en t6 porque es donde primero
hace falta, y solo la usa F5.

**Un riesgo que se cerró durante esta revisión, en vez de dejarlo anotado:** la
primera versión de la tarea 5 suponía `SetLedRgb` con campos `red/green/blue`.
Inspeccionado en el robot, **las tres suposiciones eran falsas**: el tipo es
`SetLEDRGB` (mayúsculas), lleva un `led_id` obligatorio que faltaba, y `SetLeds`
toma `int32[] rgb_color` y **no devuelve `success`**. Corregido con las
interfaces reales y con `led_id=11` (`all_lights`) leído del driver.

📝 La lección vale para el resto del plan: los tipos de mensaje **se miran, no se
deducen del nombre del servicio**.

**Lo que sigue sin verificar, y hay que saberlo:** los umbrales de F5 son bandas
de cordura (±40 %) porque **no hay base histórica**. Y F7 depende de que SLAM
converja en el pasillo; si el mapa sale mal, el error final no significa nada.
La fase lo detectaría como objetivo no alcanzado, no como mapa malo — si eso
pasa, mira el mapa antes de culpar al controlador.
