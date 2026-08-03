# API del laboratorio y material docente — plan de implementación

> **Para quien lo ejecute:** implementa tarea por tarea, en orden. Los pasos usan casillas
> (`- [ ]`) para seguimiento. **No saltes la tarea 1**: es lógica pura con tests, y las tareas 2-6
> dependen de sus nombres exactos. Las tareas 7-11 dependen de la API completa (tareas 1-6).

**Objetivo:** que las diez prácticas del curso vuelvan a arrancar, escritas sobre una biblioteca
del laboratorio que acierta por el alumno las siete cosas que este proyecto ya pagó.

**Arquitectura:** un solo fichero `atriz.py` junto a los scripts, sin instalar. Sus funciones puras
—límites, normalización de ángulos, acumulación de Δyaw— viven al **nivel de módulo**, así que se
prueban con `pytest` sin construir `Robot()` ni tocar el robot. La clase `Robot` levanta un nodo
propio con **ejecutor persistente en un hilo de fondo**, y todas las esperas se hacen sondeando el
futuro, **nunca** con `rclpy.spin_*` — mezclar las dos cosas ya costó una hora de diagnóstico falso
en este proyecto.

**Herramientas:** Python 3.12, `rclpy` (Jazzy), `pytest` 7.4.4, `atriz_rvr_msgs`.

📎 **Diseño aprobado:** [`03_operacion/API_LABORATORIO.md`](../../03_operacion/API_LABORATORIO.md).
Este plan lo implementa; si algo choca, manda el diseño.

📝 **Dónde vive este plan.** La skill sugiere `docs/superpowers/plans/`; se guarda en
`00_auditoria/planes/` junto al de la prueba de aceptación, para no abrir un árbol nuevo en un
repositorio ya organizado por fases.

🔴 **Este plan toca DOS repositorios.** `atriz.py`, los diez scripts y los cinco documentos van en
**`Atriz_rvr`, rama `ros2`**. Los tests y las evidencias van en **`atriz_migracion`**. Cada tarea
dice cuál. Haz `git fetch` en los dos antes de empezar (regla 1 del proyecto).

---

## Restricciones globales

Aplican a **todas** las tareas. Están en `CLAUDE.md` y no se negocian:

- **Sin secretos en el repositorio.** Ni contraseñas, ni claves, ni la PSK del WiFi. `Atriz_rvr`
  es **público**: lo que se escriba ahí lo ve cualquiera.
- **Nada se documenta sin ejecutarse.** Lo no ejecutado se marca **NO VERIFICADO**.
- **Nada se ejecuta sin documentarse.**
- **Medir antes de atribuir.** Ningún número inventado; cada umbral cita su fuente.
- **Nunca `pkill -f`.** Matar por `comm` con `ps`, comparando el prefijo truncado a 15 caracteres.
- **Sin trailers de co-autoría** en los commits.
- **Timeout en toda llamada a servicio.** Sin excepción.
- **Nunca `rclpy.spin_*` sobre un nodo que ya está en un ejecutor propio.**
- **Los pasos con `sudo`, apagar la Pi o mover físicamente el robot los ejecuta el usuario.**
  Prepáraselos como comando exacto.
- **Avisar de las acciones físicas** antes de ejecutarlas, y parar el robot al terminar.

### Constantes, con su fuente medida

Van en `atriz.py` y **no se cambian sin una medida nueva**:

| Constante | Valor | De dónde sale |
|---|---|---|
| `VEL_MAX` | `0.40` m/s | meseta real medida: 0.401 m/s comandando 0.40 (2026-07-31) |
| `VEL_GIRO_MAX` | `2.0` rad/s | 99–102 % del comandado en las cuatro medidas (2026-07-31) |
| `TIEMPO_MAX` | `10.0` s | tope por llamada; decisión de diseño, no una medida |
| `GRADOS_MAX` | `720.0` ° | ídem |
| `RITMO_HZ` | `10.0` Hz | el watchdog del driver corta a los **0.3 s** sin `cmd_vel` |
| `TOPIC_MANDO` | `'/cmd_vel_raw'` | `/cmd_vel` es la **salida** del `collision_monitor` |

---

## Estructura de ficheros

| Fichero | Repo | Responsabilidad |
|---|---|---|
| `scripts/estudiantes/atriz.py` | `Atriz_rvr` | **Crear.** La biblioteca entera: funciones puras + clase `Robot` |
| `scripts/pruebas/test_atriz_nucleo.py` | `atriz_migracion` | **Crear.** `pytest` de las funciones puras, sin robot |
| `scripts/estudiantes/0{1,2,3}_*.py`, `90_template.py` | `Atriz_rvr` | **Reescribir.** Movimiento básico |
| `scripts/estudiantes/04_giro_preciso.py` | `Atriz_rvr` | **Reescribir.** Lazo cerrado contra constante |
| `scripts/estudiantes/05_sensor_color.py`, `11_sensor_avanzado.py` | `Atriz_rvr` | **Reescribir.** Color |
| `scripts/estudiantes/10_movimiento_completo.py`, `99_test_ctrl_c.py` | `Atriz_rvr` | **Reescribir.** |
| `scripts/estudiantes/seguidor_linea_pid_demo.py` | `Atriz_rvr` | **Reescribir.** El PID no se toca |
| `scripts/estudiantes/*.md` (5) | `Atriz_rvr` | **Reescribir.** Y sacar las credenciales |
| `00_auditoria/evidencia/56_*.txt` … | `atriz_migracion` | **Crear.** Las medidas de cada tarea |

📝 **Por qué `atriz.py` es un solo fichero y no un paquete.** El material tiene que funcionar en 16
robots salidos de la imagen dorada con `python3 mi_script.py`. Un `setup.py`, un `colcon build` o un
`pip install` es un paso más que se rompe en clase y que hay que repetir por robot.

📝 **Y por qué los tests viven en el OTRO repositorio.** `atriz_migracion/scripts/pruebas/` ya tiene
la suite del proyecto (24 tests de `aceptacion_nucleo.py`). Meter tests en el material que ve el
alumno lo ensucia; separarlos mantiene una sola orden para pasar todo.

---

## Tarea 1: El núcleo puro de `atriz.py`

Las funciones que se pueden probar sin robot. Es la tarea que fija los nombres que usan todas las
demás.

**Ficheros:**
- Crear: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py`
- Crear: `~/atriz_migracion/scripts/pruebas/test_atriz_nucleo.py`

**Interfaces:**
- Consume: nada.
- Produce: `VEL_MAX`, `VEL_GIRO_MAX`, `TIEMPO_MAX`, `GRADOS_MAX`, `RITMO_HZ`, `TOPIC_MANDO`,
  `ErrorAtriz`, y las funciones
  `limitar(valor: float, tope: float, nombre: str, unidad: str) -> tuple[float, str | None]`,
  `normalizar(rad: float) -> float`,
  `acumular(yaw_anterior: float, yaw_actual: float, acumulado: float) -> float`,
  `yaw_de_cuaternion(x: float, y: float, z: float, w: float) -> float`,
  `alcanzado(acumulado: float, objetivo_rad: float) -> bool`,
  `velocidad_giro(restante_rad: float) -> float`.

- [ ] **Paso 1: escribe el test que falla**

Crea `~/atriz_migracion/scripts/pruebas/test_atriz_nucleo.py`:

```python
"""Las funciones puras de `atriz.py`: sin ROS, sin robot, sin motores.

🔴 El test que importa es `test_acumular_una_vuelta_entera_da_360`: leyendo el yaw
   ABSOLUTO una vuelta completa da 0°, porque `atan2` devuelve −π..π. Ese error es
   invisible hasta que alguien pide `girar(360)` y el robot no se mueve.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))

from atriz import (                                          # noqa: E402
    GRADOS_MAX, RITMO_HZ, TIEMPO_MAX, TOPIC_MANDO, VEL_GIRO_MAX, VEL_MAX,
    acumular, alcanzado, limitar, normalizar, velocidad_giro, yaw_de_cuaternion,
)


# ── Las constantes, con su fuente ────────────────────────────────────────────
def test_el_topic_de_mando_no_es_cmd_vel():
    """🔴 `/cmd_vel` es la SALIDA del collision_monitor: publicar ahí salta la
    capa de seguridad y FUNCIONA, que es lo que lo hace peligroso."""
    assert TOPIC_MANDO == '/cmd_vel_raw'


def test_los_topes_son_los_medidos():
    assert VEL_MAX == 0.40          # meseta real medida (2026-07-31)
    assert VEL_GIRO_MAX == 2.0
    assert TIEMPO_MAX == 10.0
    assert GRADOS_MAX == 720.0


def test_el_ritmo_bate_al_watchdog():
    """El driver corta a los 0.3 s sin cmd_vel; hay que publicar más rápido."""
    assert 1.0 / RITMO_HZ < 0.3


# ── limitar ──────────────────────────────────────────────────────────────────
def test_limitar_no_toca_ni_avisa_dentro_del_limite():
    valor, aviso = limitar(0.20, VEL_MAX, 'velocidad', 'm/s')
    assert valor == 0.20
    assert aviso is None


def test_limitar_recorta_y_avisa_en_voz_alta():
    valor, aviso = limitar(1.5, VEL_MAX, 'velocidad', 'm/s')
    assert valor == 0.40
    assert aviso is not None and '1.5' in aviso and '0.4' in aviso


def test_limitar_respeta_el_signo():
    valor, aviso = limitar(-1.5, VEL_MAX, 'velocidad', 'm/s')
    assert valor == -0.40
    assert aviso is not None


# ── normalizar ───────────────────────────────────────────────────────────────
def test_normalizar_deja_quieto_lo_que_ya_esta_en_rango():
    assert math.isclose(normalizar(math.radians(45.0)), math.radians(45.0))


def test_normalizar_359_es_menos_uno():
    assert math.isclose(normalizar(math.radians(359.0)), math.radians(-1.0),
                        abs_tol=1e-9)


def test_normalizar_devuelve_pi_y_no_menos_pi():
    """El intervalo es (−π, π]: el extremo cerrado es el positivo."""
    assert math.isclose(normalizar(-math.pi), math.pi, abs_tol=1e-9)


# ── acumular ─────────────────────────────────────────────────────────────────
def test_acumular_una_vuelta_entera_da_360():
    """🔴 EL TEST QUE JUSTIFICA LA FUNCIÓN. 36 pasos de 10°: leyendo el yaw
    absoluto el total sería 0, y `girar(360)` terminaría sin moverse."""
    acumulado, anterior = 0.0, 0.0
    for paso in range(1, 37):
        actual = normalizar(math.radians(10.0 * paso))
        acumulado = acumular(anterior, actual, acumulado)
        anterior = actual
    assert math.isclose(math.degrees(acumulado), 360.0, abs_tol=1e-6)


def test_acumular_cuenta_negativo_al_girar_al_reves():
    acumulado, anterior = 0.0, 0.0
    for paso in range(1, 10):
        actual = normalizar(math.radians(-10.0 * paso))
        acumulado = acumular(anterior, actual, acumulado)
        anterior = actual
    assert math.isclose(math.degrees(acumulado), -90.0, abs_tol=1e-6)


# ── yaw_de_cuaternion ────────────────────────────────────────────────────────
def test_yaw_de_cuaternion_identidad_es_cero():
    assert yaw_de_cuaternion(0.0, 0.0, 0.0, 1.0) == 0.0


def test_yaw_de_cuaternion_noventa_grados():
    mitad = math.radians(45.0)
    yaw = yaw_de_cuaternion(0.0, 0.0, math.sin(mitad), math.cos(mitad))
    assert math.isclose(math.degrees(yaw), 90.0, abs_tol=1e-9)


# ── alcanzado ────────────────────────────────────────────────────────────────
def test_alcanzado_hacia_la_izquierda():
    assert alcanzado(math.radians(91.0), math.radians(90.0))
    assert not alcanzado(math.radians(89.0), math.radians(90.0))


def test_alcanzado_hacia_la_derecha_no_confunde_el_signo():
    """girar(−90) termina en −π/2. Comparar valores absolutos daría por buena
    una vuelta en el sentido contrario."""
    assert alcanzado(math.radians(-91.0), math.radians(-90.0))
    assert not alcanzado(math.radians(-89.0), math.radians(-90.0))
    assert not alcanzado(math.radians(+91.0), math.radians(-90.0))


# ── velocidad_giro ───────────────────────────────────────────────────────────
def test_velocidad_giro_frena_al_acercarse():
    lejos = velocidad_giro(math.radians(90.0))
    medio = velocidad_giro(math.radians(20.0))
    cerca = velocidad_giro(math.radians(3.0))
    assert lejos > medio > cerca > 0.0


def test_velocidad_giro_nunca_pasa_del_tope():
    for grados in (0.5, 5.0, 45.0, 180.0, 720.0):
        assert 0.0 < velocidad_giro(math.radians(grados)) <= VEL_GIRO_MAX


def test_velocidad_giro_no_depende_del_signo():
    assert velocidad_giro(math.radians(45.0)) == velocidad_giro(math.radians(-45.0))
```

- [ ] **Paso 2: ejecuta el test para verificar que falla**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/test_atriz_nucleo.py -q
```

Esperado: **error de colección**, `ModuleNotFoundError: No module named 'atriz'`.

- [ ] **Paso 3: escribe el núcleo**

Crea `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py` con **solo** esta parte (la clase
`Robot` llega en la tarea 2):

```python
#!/usr/bin/env python3
"""La biblioteca del laboratorio Atriz — lo que usan las prácticas del curso.

    from atriz import Robot

    with Robot() as robot:
        robot.avanzar(0.20, 3)      # m/s durante segundos
        robot.girar(90)             # grados; positivo = a la izquierda

No hace falta instalar nada: este fichero vive junto a los scripts.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE, EN UNA LÍNEA
═══════════════════════════════════════════════════════════════════════════════
Un programa escrito contra `rclpy` a pelo tiene que acertar, cada vez y sin
ayuda, en siete cosas que este laboratorio ha aprendido a base de fallos. Aquí
se aciertan una vez, y el alumno escribe robótica.

Están documentadas una a una en `03_operacion/API_LABORATORIO.md`.
"""
import math

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES — cada una tiene una medida detrás. No se cambian sin otra.
# ═══════════════════════════════════════════════════════════════════════════

# 🔴 EL TOPIC. `/cmd_vel` es la SALIDA del collision_monitor: publicar ahí
#    FUNCIONA y salta la capa de seguridad entera, sin un solo aviso. Es el
#    agujero más silencioso del sistema, y los diez scripts de ROS 1 lo hacían.
TOPIC_MANDO = '/cmd_vel_raw'

VEL_MAX = 0.40        # m/s — meseta REAL medida: 0.401 comandando 0.40 (2026-07-31)
VEL_GIRO_MAX = 2.0    # rad/s — 99-102 % del comandado en las cuatro medidas
TIEMPO_MAX = 10.0     # s por llamada — decisión de diseño, no una medida
GRADOS_MAX = 720.0    # ° por llamada — ídem

# 🔴 El watchdog del driver corta a los 0.3 s sin `cmd_vel`. Un `sleep(3)` entre
#    dos publicaciones deja al robot PARADO casi todo el tiempo, y el alumno ve
#    un robot que «no obedece». Hay que republicar más rápido que eso.
RITMO_HZ = 10.0


class ErrorAtriz(Exception):
    """Algo del laboratorio no está como debería. El mensaje dice qué hacer."""


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES PURAS — sin ROS, sin robot. Tienen tests en atriz_migracion.
# ═══════════════════════════════════════════════════════════════════════════

def limitar(valor, tope, nombre, unidad):
    """Recorta `valor` a ±`tope`. Devuelve (valor, aviso o None).

    Recorta en vez de lanzar, y AVISA en vez de recortar en silencio: un
    programa que se muere a mitad deja el robot conduciendo, y uno que recorta
    calladito enseña al alumno que su número se aplicó.
    """
    if abs(valor) <= tope:
        return valor, None
    recortado = math.copysign(tope, valor)
    return recortado, (
        f'AVISO: {nombre} {valor:g} {unidad} pasa del limite del laboratorio '
        f'({tope:g} {unidad}); se usa {recortado:g}.')


def normalizar(rad):
    """Lleva un ángulo al intervalo (−π, π]."""
    angulo = math.fmod(rad, 2.0 * math.pi)
    if angulo > math.pi:
        angulo -= 2.0 * math.pi
    elif angulo <= -math.pi:
        angulo += 2.0 * math.pi
    return angulo


def acumular(yaw_anterior, yaw_actual, acumulado):
    """Suma el INCREMENTO de rumbo, normalizado. Nunca el yaw absoluto.

    🔴 `atan2` devuelve −π..π, así que una vuelta entera leída en absoluto
       vuelve al punto de partida y se lee como 0°. Acumular el incremento
       normalizado es lo que hace que 360° sean 360°.
    """
    return acumulado + normalizar(yaw_actual - yaw_anterior)


def yaw_de_cuaternion(x, y, z, w):
    """El rumbo (giro alrededor de Z) de un cuaternión de ROS, en radianes."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def alcanzado(acumulado, objetivo_rad):
    """¿Se llegó al objetivo? Con signo: girar(−90) termina en −π/2.

    Comparar valores absolutos daría por buena una vuelta en el sentido
    contrario, que es exactamente el fallo que no se vería en un pasillo.
    """
    if objetivo_rad >= 0.0:
        return acumulado >= objetivo_rad
    return acumulado <= objetivo_rad


def velocidad_giro(restante_rad):
    """Rad/s para lo que queda de giro: rápido lejos, lento cerca.

    Es la rampa que hace que el lazo cerrado no se pase de largo. El signo lo
    pone quien llama, no esta función.
    """
    restante = abs(restante_rad)
    if restante > math.radians(30.0):
        return 0.80
    if restante > math.radians(8.0):
        return 0.40
    return 0.20
```

- [ ] **Paso 4: ejecuta los tests para verificar que pasan**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/ -q
```

Esperado: **todos en verde**, los 18 nuevos más los 24 de `aceptacion_nucleo`.

- [ ] **Paso 5: commit en los dos repositorios**

```bash
cd ~/atriz_ws/src/Atriz_rvr && git add scripts/estudiantes/atriz.py && git commit -m \
"atriz.py: el nucleo puro de la API del laboratorio

Constantes con su medida detras y las funciones que se pueden probar sin robot.
La que importa es acumular(): leyendo el yaw absoluto una vuelta entera da 0
grados, porque atan2 devuelve -pi..pi."

cd ~/atriz_migracion && git add scripts/pruebas/test_atriz_nucleo.py && git commit -m \
"18 tests del nucleo de atriz.py, sin robot"
```

---

## Tarea 2: Conectar, cerrar, y las dos comprobaciones del arranque

La parte que decide si el alumno ve un robot que funciona o uno que parece averiado.

**Ficheros:**
- Modificar: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py` (añadir la clase `Robot`)

**Interfaces:**
- Consume: todo lo de la tarea 1.
- Produce: `Robot(velocidad_maxima: float = VEL_MAX)`, con
  `__enter__() -> Robot`, `__exit__(*_) -> None`, `cerrar() -> None`,
  `_llamar(cliente, peticion, timeout: float, que: str)` (interno, lo usan las tareas 3-5),
  `_ultimo(atributo: str, timeout: float, que: str)` (interno, ídem),
  y el atributo público `hay_color: bool`.

- [ ] **Paso 1: añade la clase `Robot` a `atriz.py`**

Añade los imports que faltan **al principio del fichero**, después de `import math`:

```python
import signal
import sys
import threading
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rcl_interfaces.srv import GetParameters
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy)
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import BatteryState, LaserScan
from std_msgs.msg import Empty
from std_srvs.srv import Empty as EmptySrv
```

Y al final del fichero:

```python
# ═══════════════════════════════════════════════════════════════════════════
# EL ROBOT
# ═══════════════════════════════════════════════════════════════════════════

class Robot:
    """El robot del laboratorio. Se conecta al construirlo.

        with Robot() as robot:
            robot.avanzar(0.20, 3)

    Usa `with`: así el robot se para y el barrido se apaga aunque tu programa
    falle a la mitad.
    """

    def __init__(self, velocidad_maxima=VEL_MAX):
        self._vel_max = min(abs(float(velocidad_maxima)), VEL_MAX)
        self._cerrado = False

        # 🔴 signal_handler_options=NO, Y NO ES OPCIONAL.
        #    `rclpy.init()` instala SU manejador de SIGINT e invalida su propio
        #    contexto: el `except KeyboardInterrupt` que intenta parar el robot
        #    muere con «publisher's context is invalid». Medido el 2026-08-02:
        #    0 lineas de parada con el defecto, 5 con esta opcion. Y ES
        #    INTERMITENTE, que es lo que lo hizo pasar desapercibido.
        if not rclpy.ok():
            rclpy.init(args=None,
                       signal_handler_options=SignalHandlerOptions.NO)

        self._nodo = Node('atriz_alumno')

        # QoS de la telemetria: BEST_EFFORT. Un suscriptor RELIABLE NO RECIBE
        # NADA, sin error — DDS no empareja. Es la misma trampa de QoS que costo
        # la parada de emergencia.
        sensor = QoSProfile(depth=10,
                            reliability=QoSReliabilityPolicy.BEST_EFFORT)
        # La bateria es la excepcion: el driver la publica RELIABLE +
        # TRANSIENT_LOCAL cada 30 s. Pidiendo lo mismo, el ultimo valor llega al
        # suscribirse en vez de esperar medio minuto.
        latch = QoSProfile(depth=1,
                           reliability=QoSReliabilityPolicy.RELIABLE,
                           durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

        self._odom = None
        self._scan = None
        self._bateria = None
        self._nodo.create_subscription(
            Odometry, '/odom', lambda m: setattr(self, '_odom', m), sensor)
        self._nodo.create_subscription(
            LaserScan, '/scan', lambda m: setattr(self, '_scan', m), sensor)
        self._nodo.create_subscription(
            BatteryState, '/battery_state',
            lambda m: setattr(self, '_bateria', m), latch)

        self._pub_mando = self._nodo.create_publisher(Twist, TOPIC_MANDO, 1)
        # La parada: RELIABLE + VOLATILE. Es el QoS que costo el tercer fallo de
        # este boton — TRANSIENT_LOCAL en el suscriptor solo RESTRINGE.
        self._pub_parada = self._nodo.create_publisher(
            Empty, '/emergency_stop',
            QoSProfile(depth=1,
                       reliability=QoSReliabilityPolicy.RELIABLE,
                       durability=QoSDurabilityPolicy.VOLATILE))

        self._cli_iniciar = self._nodo.create_client(EmptySrv, '/start_scan')
        self._cli_parar_barrido = self._nodo.create_client(EmptySrv, '/stop_scan')
        self._cli_param = self._nodo.create_client(
            GetParameters, '/rvr_driver/get_parameters')

        # 🔴 EJECUTOR PROPIO Y PERSISTENTE, en un hilo de fondo.
        #    `rclpy.spin_once(nodo)` en bucle engancha y desengancha el nodo del
        #    ejecutor global en cada llamada, y en ese hueco se PIERDEN mensajes:
        #    11.3 Hz medidos sobre un robot que iba a 16.5.
        #    Y por eso este fichero NO llama a `rclpy.spin_*` en ningun sitio:
        #    mezclarlo con un ejecutor propio ya costo una hora de diagnostico
        #    falso en este proyecto.
        self._ejecutor = SingleThreadedExecutor()
        self._ejecutor.add_node(self._nodo)
        self._hilo = threading.Thread(target=self._ejecutor.spin, daemon=True,
                                      name='atriz-ejecutor')
        self._hilo.start()

        signal.signal(signal.SIGINT, self._al_ctrl_c)

        print('Conectando con el robot...')
        self._encender_barrido()
        self.hay_color = self._comprobar_color()
        print('Robot listo.')

    # ── Puertas de entrada y salida ─────────────────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()
        return False

    def cerrar(self):
        """Para el robot y apaga el barrido. Se puede llamar dos veces."""
        if self._cerrado:
            return
        self._cerrado = True
        try:
            self._mandar(0.0, 0.0, repeticiones=5)
            self._llamar(self._cli_parar_barrido, EmptySrv.Request(),
                         timeout=5.0, que='/stop_scan')
        except Exception as e:                               # noqa: BLE001
            print(f'AVISO al cerrar: {e}')
        finally:
            # El barrido se apaga SIEMPRE que se pueda: si no, el X2 se queda
            # girando a 11.8 Hz en vez de 2.7, 24/7 y por 16 robots.
            self._ejecutor.shutdown()
            self._nodo.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()

    def _al_ctrl_c(self, _signum, _frame):
        """Ctrl-C: para el robot y sale. NO dispara la parada de emergencia.

        🔴 Y es a proposito. La parada SE QUEDA ENGANCHADA hasta que alguien
           llame a /release_emergency_stop, asi que un Ctrl-C que la disparara
           dejaria el SIGUIENTE script del alumno sin funcionar y sin
           explicacion. El camino correcto para terminar es el normal: cero, y
           el watchdog de 0.3 s por debajo.
        """
        print('\nCtrl-C: parando el robot...')
        self.cerrar()
        sys.exit(130)

    # ── Arranque ────────────────────────────────────────────────────────────
    def _encender_barrido(self):
        """🔴 Sin /scan el robot NO OBEDECE, y parece averiado.

        El barrido arranca apagado a proposito (si no, el X2 gira a 11.8 Hz
        24/7). Sin `/scan` el collision_monitor bloquea el movimiento: medido
        0.0 cm contra 9.9 del control. Desde fuera es identico a un robot roto.
        """
        self._llamar(self._cli_iniciar, EmptySrv.Request(),
                     timeout=10.0, que='/start_scan')
        # Que el servicio conteste no prueba que lleguen barridos: se espera al
        # EFECTO, que es un /scan de verdad.
        self._ultimo('_scan', timeout=8.0, que='/scan')

    def _comprobar_color(self):
        """¿Se arranco el robot con el sensor de color encendido?

        🔴 No se puede encender bajo demanda: con el streaming ya montado,
           `enable_color_detection` NO HACE NADA (481 mensajes, todos ceros). Se
           decide en el arranque, y el servicio systemd usa el defecto: false.
           Sin esta comprobacion, `color()` devuelve negro y parece un dato.
        """
        peticion = GetParameters.Request()
        peticion.names = ['color_detection']
        try:
            resp = self._llamar(self._cli_param, peticion, timeout=5.0,
                                que='/rvr_driver/get_parameters')
            activo = bool(resp.values[0].bool_value)
        except Exception:                                    # noqa: BLE001
            print('AVISO: no se pudo consultar color_detection. '
                  'color() puede devolver ceros.')
            return False
        if not activo:
            print('AVISO: el sensor de color esta APAGADO en este robot.\n'
                  '       color() devolvera ceros. Para usarlo, el robot tiene\n'
                  '       que arrancar asi (lo hace el profesor):\n'
                  '         sudo systemctl stop atriz-robot\n'
                  '         ros2 launch atriz_rvr_bringup robot.launch.py '
                  'color_detection:=true')
        return activo

    # ── Fontaneria ──────────────────────────────────────────────────────────
    def _llamar(self, cliente, peticion, timeout, que):
        """Llama a un servicio y espera SONDEANDO el futuro.

        🔴 No se usa `rclpy.spin_until_future_complete`: este nodo ya esta en un
           ejecutor propio, y mezclarlos deja de atender las suscripciones. Aqui
           el futuro lo completa el hilo de fondo; este solo mira si ya esta.
        """
        if not cliente.wait_for_service(timeout_sec=timeout):
            raise ErrorAtriz(
                f'{que} no aparece. Comprueba que el robot esta encendido:\n'
                f'  systemctl is-active atriz-robot')
        futuro = cliente.call_async(peticion)
        limite = time.monotonic() + timeout
        while not futuro.done() and time.monotonic() < limite:
            time.sleep(0.01)
        if not futuro.done():
            raise ErrorAtriz(f'{que} no contesto en {timeout:.0f} s.')
        return futuro.result()

    def _ultimo(self, atributo, timeout, que):
        """El ultimo mensaje recibido de un topic, esperando si aun no llego."""
        limite = time.monotonic() + timeout
        while getattr(self, atributo) is None and time.monotonic() < limite:
            time.sleep(0.02)
        mensaje = getattr(self, atributo)
        if mensaje is None:
            raise ErrorAtriz(
                f'no llega nada por {que} en {timeout:.0f} s. El topic puede '
                f'existir y estar mudo: mira el RITMO, no la lista de topics.')
        return mensaje

    def _mandar(self, lineal, angular, repeticiones=1):
        """Publica una velocidad en cmd_vel_raw. NUNCA en /cmd_vel."""
        orden = Twist()
        orden.linear.x = float(lineal)
        orden.angular.z = float(angular)
        for _ in range(repeticiones):
            self._pub_mando.publish(orden)
            time.sleep(1.0 / RITMO_HZ)
```

- [ ] **Paso 2: comprueba que el fichero sigue siendo válido y los tests pasan**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/ -q
python3 -c "import sys; sys.path.insert(0, '$HOME/atriz_ws/src/Atriz_rvr/scripts/estudiantes'); import atriz; print('importa bien')"
```

Esperado: tests en verde e `importa bien`.

- [ ] **Paso 3: pruébalo contra el robot — NO MUEVE EL ROBOT**

⚠️ **Acción física: esto ENCIENDE EL BARRIDO del LIDAR** (el motor pasa de 2.7 a 11.8 Hz) y
despierta el RVR. No mueve las orugas. Al terminar deja el barrido apagado.

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 -c "
from atriz import Robot
with Robot() as r:
    print('hay_color =', r.hay_color)
    print('/scan llego, con', len(r._scan.ranges), 'puntos')
"
```

Esperado: `Robot listo.`, el aviso de que el color está apagado, `hay_color = False`, y ~250
puntos. Si dice `no llega nada por /scan`, el `start_scan` no tuvo efecto — que es exactamente lo
que esta comprobación existe para detectar.

- [ ] **Paso 4: comprueba que el barrido quedó APAGADO**

```bash
source /opt/ros/jazzy/setup.bash && timeout 8 ros2 topic hz /scan 2>&1 | tail -3
```

Esperado: **ningún mensaje** — `cerrar()` llamó a `/stop_scan`. Si sigue publicando, el camino de
cierre está roto y el X2 se queda a 11.8 Hz.

- [ ] **Paso 5: guarda la evidencia y commitea**

```bash
cd ~/atriz_migracion
cat > 00_auditoria/evidencia/56_atriz_conexion.txt <<'FIN'
Tarea 2 — conexion y cierre de atriz.py. 2026-08-02.
(pega aqui la salida de los pasos 3 y 4)
FIN
git add 00_auditoria/evidencia/56_atriz_conexion.txt && git commit -m \
"Evidencia 56: atriz.py conecta, enciende el barrido y lo deja apagado al cerrar"

cd ~/atriz_ws/src/Atriz_rvr && git add scripts/estudiantes/atriz.py && git commit -m \
"atriz.py: conexion, cierre y las dos comprobaciones del arranque

Enciende el barrido y espera un /scan de verdad, no la respuesta del servicio.
Consulta color_detection y avisa en voz alta en vez de devolver ceros.
Ejecutor propio en un hilo, y ni un rclpy.spin_* en todo el fichero."
---

## Tarea 3: `avanzar()` y `parar()`

**Ficheros:**
- Modificar: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py`

**Interfaces:**
- Consume: `limitar`, `VEL_MAX`, `TIEMPO_MAX`, `RITMO_HZ`, `Robot._mandar`.
- Produce: `Robot.avanzar(velocidad: float, segundos: float) -> None`,
  `Robot.parar() -> None`.

- [ ] **Paso 1: añade los dos métodos a la clase `Robot`**

Van justo después de `_mandar`:

```python
    # ── Movimiento ──────────────────────────────────────────────────────────
    def avanzar(self, velocidad, segundos):
        """Avanza a `velocidad` m/s durante `segundos`. Negativo = hacia atras.

            robot.avanzar(0.20, 3)     # 20 cm/s durante 3 segundos

        Republica la orden a 10 Hz: el driver corta a los 0.3 s sin recibir
        nada, asi que un `sleep` largo entre publicaciones deja al robot
        parandose y arrancando.
        """
        velocidad, aviso = limitar(velocidad, self._vel_max, 'velocidad', 'm/s')
        if aviso:
            print(aviso)
        segundos, aviso = limitar(abs(segundos), TIEMPO_MAX, 'tiempo', 's')
        if aviso:
            print(aviso)

        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            self._mandar(velocidad, 0.0)
        self.parar()

    def parar(self):
        """Para el robot: velocidad cero, repetida por si se pierde un mensaje."""
        self._mandar(0.0, 0.0, repeticiones=5)
```

- [ ] **Paso 2: comprueba el límite sin mover el robot**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 -c "
from atriz import limitar, VEL_MAX
print(limitar(5.0, VEL_MAX, 'velocidad', 'm/s'))
"
```

Esperado: `(0.4, 'AVISO: velocidad 5 m/s pasa del limite...')`.

- [ ] **Paso 3: mide con cinta métrica**

🔴 **PIDE ESTO AL USUARIO. Mueve el robot.** Necesita el pasillo despejado: **1 m por delante**
del robot, y ten en cuenta que el LIDAR barre a **15.5 cm del suelo**, así que «despejado a ras de
suelo» no basta.

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 -c "
from atriz import Robot
with Robot() as r:
    input('Marca donde esta el robot y pulsa Enter...')
    r.avanzar(0.20, 3)
    input('Mide cuanto avanzo y pulsa Enter...')
"
```

Esperado: **~60 cm** (0.20 m/s × 3 s). Rango aceptable **55–65 cm**.

🔴 **Si mide ~6 cm, el watchdog está cortando** y `RITMO_HZ` no se está respetando: es el fallo
que este paso existe para detectar, no un robot lento.

⚠️ **Si mide bastante menos y hay una pared cerca, no es un fallo del código.** El polígono
`Precaucion` frena al **40 %** cuando algo está dentro de 0.36 m, **aunque el robot se aleje**:
30 cm comandados dieron 14 medidos (evidencia 49). Repite con más sitio antes de tocar nada.

- [ ] **Paso 4: guarda la evidencia y commitea**

```bash
cd ~/atriz_migracion
# escribe en 00_auditoria/evidencia/57_atriz_avanzar.txt: comandado, medido, y
# cuanto sitio habia. Sin la tercera columna la medida no se puede replicar.
git add 00_auditoria/evidencia/57_atriz_avanzar.txt && git commit -m \
"Evidencia 57: avanzar() medido con cinta"

cd ~/atriz_ws/src/Atriz_rvr && git add scripts/estudiantes/atriz.py && git commit -m \
"atriz.py: avanzar() y parar(), republicando a 10 Hz contra el watchdog"
```

---

## Tarea 4: `girar()` en lazo cerrado

La pieza con contenido docente. Un lazo cerrado le gana a una constante calibrada, y el robot tiene
un déficit de fábrica que lo demuestra: **86.6 / 86.2 / 87.7°** pidiendo 90 (n=3, 2026-08-02, con
baterías del 55 % al 100 %, así que no depende de la carga).

**Ficheros:**
- Modificar: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py`

**Interfaces:**
- Consume: `acumular`, `alcanzado`, `velocidad_giro`, `yaw_de_cuaternion`, `limitar`,
  `GRADOS_MAX`, `Robot._ultimo`, `Robot._mandar`, `Robot.parar`.
- Produce: `Robot.girar(grados: float) -> float` — devuelve los grados **realmente** girados,
  medidos en `/odom`. Y `Robot.rumbo() -> float`, el yaw actual en grados.

- [ ] **Paso 1: añade los dos métodos**

```python
    def rumbo(self):
        """El rumbo actual en grados, leido de /odom."""
        q = self._ultimo('_odom', timeout=5.0, que='/odom').pose.pose.orientation
        return math.degrees(yaw_de_cuaternion(q.x, q.y, q.z, q.w))

    def girar(self, grados):
        """Gira `grados` sobre el eje. Positivo = a la IZQUIERDA (REP-103).

            robot.girar(90)      # un cuarto de vuelta a la izquierda
            robot.girar(-90)     # a la derecha

        Devuelve los grados que giro DE VERDAD, medidos en /odom.

        ═══════════════════════════════════════════════════════════════════
        POR QUE ESTO ES UN LAZO CERRADO Y NO UNA CONSTANTE
        ═══════════════════════════════════════════════════════════════════
        Pidiendole 90 grados por tiempo, este robot hace 86.6 / 86.2 / 87.7
        (n=3, medido). La salida barata es multiplicar por 1.04 y seguir. Aqui
        se mide el rumbo real y se para al llegar: la constante se equivoca en
        cuanto cambie el suelo, la carga o el robot; el lazo, no.

        🔴 Y se acumula el INCREMENTO de rumbo, nunca el yaw absoluto: `atan2`
           devuelve -pi..pi, asi que una vuelta entera leida en absoluto vuelve
           al punto de partida y `girar(360)` terminaria sin haberse movido.
        """
        grados, aviso = limitar(grados, GRADOS_MAX, 'giro', 'grados')
        if aviso:
            print(aviso)
        objetivo = math.radians(grados)
        if abs(objetivo) < math.radians(0.5):
            return 0.0

        sentido = 1.0 if objetivo >= 0.0 else -1.0
        anterior = math.radians(self.rumbo())
        acumulado = 0.0

        # Tope de tiempo: lo que tardaria al ritmo mas lento de la rampa, con
        # margen. Sin el, un robot atascado gira para siempre.
        limite = time.monotonic() + abs(objetivo) / 0.20 + 5.0

        while not alcanzado(acumulado, objetivo):
            if time.monotonic() > limite:
                print(f'AVISO: el giro se quedo en {math.degrees(acumulado):.1f} '
                      f'de {grados:g} grados. Robot atascado o algo lo frena.')
                break
            self._mandar(0.0, sentido * velocidad_giro(objetivo - acumulado))
            q = self._ultimo('_odom', timeout=2.0,
                             que='/odom').pose.pose.orientation
            actual = yaw_de_cuaternion(q.x, q.y, q.z, q.w)
            acumulado = acumular(anterior, actual, acumulado)
            anterior = actual

        self.parar()
        # El robot sigue rodando un poco tras el ultimo comando: se espera y se
        # vuelve a medir, para devolver lo que paso de verdad y no lo que se
        # habia mandado.
        time.sleep(0.5)
        q = self._ultimo('_odom', timeout=2.0, que='/odom').pose.pose.orientation
        acumulado = acumular(anterior, yaw_de_cuaternion(q.x, q.y, q.z, q.w),
                             acumulado)
        return math.degrees(acumulado)
```

- [ ] **Paso 2: mide con transportador, n=3 en tres ángulos**

🔴 **PIDE ESTO AL USUARIO. Gira el robot sobre el sitio.** Necesita ~40 cm libres alrededor.

⚠️ **Y hay un confusor que hay que evitar:** la deriva de yaw es **~1000× mayor** en los primeros
minutos tras encender el RVR (0.97 °/30 s recién encendido contra 0.001 siete minutos después).
**Deja el robot encendido 10 minutos antes de medir**, o la medida no dice nada del lazo.

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 -c "
from atriz import Robot
with Robot() as r:
    for pedido in (90, 90, 90, 180, 180, 180, 360, 360, 360):
        input(f'Marca el rumbo con cinta y pulsa Enter para pedir {pedido} grados...')
        logrado = r.girar(pedido)
        print(f'  pedido {pedido:4d}  /odom dice {logrado:7.2f}  -> mide con transportador')
"
```

Esperado: `/odom` dentro de **±2°** del pedido en los nueve, y el transportador de acuerdo con
`/odom` dentro del error del propio instrumento.

🔴 **Si el lazo cerrado NO bate a los 86.6 / 179.6 / 358.4 del giro por tiempo, el argumento de
todo este diseño es falso** y hay que volver al documento, no ajustar el código hasta que salga.

- [ ] **Paso 3: guarda la evidencia**

```bash
cd ~/atriz_migracion
# 00_auditoria/evidencia/58_atriz_girar.txt: las nueve corridas con TRES
# columnas — pedido, lo que dice /odom, y lo que dice el transportador.
# La tercera es la unica que no puede estar de acuerdo consigo misma.
git add 00_auditoria/evidencia/58_atriz_girar.txt && git commit -m \
"Evidencia 58: girar() en lazo cerrado, n=3 a 90/180/360 grados"
```

- [ ] **Paso 4: commitea la biblioteca**

```bash
cd ~/atriz_ws/src/Atriz_rvr && git add scripts/estudiantes/atriz.py && git commit -m \
"atriz.py: girar() en lazo cerrado sobre el Delta-yaw de /odom

Devuelve los grados girados de verdad, no los pedidos. Acumula el incremento
normalizado: leyendo el yaw absoluto, girar(360) terminaria sin moverse."
```

---

## Tarea 5: sensores, luces y la parada explícita

**Ficheros:**
- Modificar: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py`

**Interfaces:**
- Consume: `Robot._llamar`, `Robot._ultimo`, `Robot.hay_color`.
- Produce: `Robot.color() -> tuple[int, int, int, int]` (r, g, b, claro),
  `Robot.distancia_frontal() -> float` (metros),
  `Robot.bateria() -> float` (voltios),
  `Robot.luces(rojo: int, verde: int, azul: int) -> None`,
  `Robot.parada_emergencia() -> None`.

- [ ] **Paso 1: añade los imports que faltan**

Junto a los demás, arriba del fichero:

```python
from atriz_rvr_msgs.srv import GetRGBCSensorValues, SetLeds
```

Y en `__init__`, junto a los otros clientes:

```python
        self._cli_color = self._nodo.create_client(
            GetRGBCSensorValues, '/get_rgbc_sensor_values')
        self._cli_luces = self._nodo.create_client(SetLeds, '/set_leds')
```

- [ ] **Paso 2: añade los cinco métodos**

```python
    # ── Sensores ────────────────────────────────────────────────────────────
    def color(self):
        """El color que ve el robot: (rojo, verde, azul, claro).

        📝 Sale del servicio /get_rgbc_sensor_values y no del topic /color, y
           por una razon medida: el mensaje `Color` NO trae el canal `claro`, y
           `claro` es el que discrimina de verdad — 12.6x entre blanco y negro,
           contra un RGB que apenas se mueve. El servicio cuesta 13-20 ms, asi
           que cabe de sobra en un lazo de control a 10 Hz.

        Normaliza por VERDE, que es el canal mas sensible: rojo sube R/G de 0.48
        a 2.74, azul sube B/G a 0.86.
        """
        if not self.hay_color:
            print('AVISO: el sensor de color esta apagado; esto seran ceros.')
        r = self._llamar(self._cli_color, GetRGBCSensorValues.Request(),
                         timeout=5.0, que='/get_rgbc_sensor_values')
        return (r.red_channel_value, r.green_channel_value,
                r.blue_channel_value, r.clear_channel_value)

    def distancia_frontal(self):
        """Metros hasta lo mas cercano que hay DELANTE, en un cono de +-10 grados.

        ⚠️ Un solo barrido no ve un objeto fino: a 0.68 m el X2 tira un rayo
           cada 1.7 cm, asi que algo de 5 cm da 2-3 puntos y puede desaparecer.
           Para geometria fina hay que acumular varios barridos.
        """
        barrido = self._ultimo('_scan', timeout=5.0, que='/scan')
        cono = math.radians(10.0)
        cerca = math.inf
        for i, distancia in enumerate(barrido.ranges):
            angulo = barrido.angle_min + i * barrido.angle_increment
            if abs(normalizar(angulo)) > cono:
                continue
            if barrido.range_min < distancia < barrido.range_max:
                cerca = min(cerca, distancia)
        if not math.isfinite(cerca):
            raise ErrorAtriz('no hay ningun punto valido delante del robot.')
        return cerca

    def bateria(self):
        """Voltios de la bateria del RVR.

        🔴 Voltios y no porcentaje: el porcentaje dijo 100 % con la bateria a
           8.29 V, a 1.29 V del umbral de «baja» del propio firmware (7.0 V;
           critica 6.5). Es una estimacion gruesa.
        """
        return float(self._ultimo('_bateria', timeout=35.0,
                                  que='/battery_state').voltage)

    # ── Luces y parada ──────────────────────────────────────────────────────
    def luces(self, rojo, verde, azul):
        """Pone TODOS los faros del robot a un color (0-255 cada canal)."""
        for nombre, valor in (('rojo', rojo), ('verde', verde), ('azul', azul)):
            if not 0 <= int(valor) <= 255:
                raise ErrorAtriz(f'{nombre}={valor}: cada canal va de 0 a 255.')
        peticion = SetLeds.Request()
        peticion.rgb_color = [int(rojo), int(verde), int(azul)]
        self._llamar(self._cli_luces, peticion, timeout=5.0, que='/set_leds')

    def parada_emergencia(self):
        """Parada de emergencia: el driver descarta TODO comando hasta liberarla.

        🔴 NO se libera sola, ni aqui ni al cerrar. Liberar es un acto explicito
           del profesor:  ros2 service call /release_emergency_stop std_srvs/srv/Empty
           Ese fue el cuarto fallo de este boton: al SOLTARLA, no al pulsarla,
           el robot arrancaba solo.
        """
        for _ in range(3):
            self._pub_parada.publish(Empty())
            time.sleep(0.05)
        print('PARADA DE EMERGENCIA enviada. El robot no obedecera hasta que\n'
              'alguien la libere:  ros2 service call /release_emergency_stop '
              'std_srvs/srv/Empty')
```

- [ ] **Paso 3: pruébalo — ENCIENDE LOS FAROS, no mueve el robot**

⚠️ **Acción física: los faros del robot se van a encender.** Mira el robot: es la única forma de
comprobar los LEDs, no hay manera de leerlo desde el software.

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 -c "
import time
from atriz import Robot
with Robot() as r:
    print('bateria:', r.bateria(), 'V')
    print('distancia frontal:', round(r.distancia_frontal(), 3), 'm')
    print('color:', r.color())
    for nombre, rgb in (('ROJO', (255,0,0)), ('VERDE', (0,255,0)), ('AZUL', (0,0,255))):
        r.luces(*rgb); print('mira el robot:', nombre); time.sleep(2)
    r.luces(0, 0, 0)
"
```

Esperado: voltaje entre **6.5 y 8.3 V**, una distancia coherente con lo que tienes delante
(compárala con una cinta), `color()` con el canal claro en **1** si el sensor está apagado, y los
faros cambiando de color a la vista.

- [ ] **Paso 4: comprueba la parada explícita, y libérala**

```bash
source /opt/ros/jazzy/setup.bash
python3 -c "
from atriz import Robot
import sys; sys.path.insert(0, '.')
with Robot() as r: r.parada_emergencia()
"
journalctl -u atriz-robot --since "-25 s" --no-pager | grep -ci "parada"
```

⚠️ **`--since "-25 s"`, no `date -u`**: `date -u` da hora UTC y `journalctl` la interpreta como
local, así que en este robot (UTC−5) la ventana cae **cinco horas en el futuro** y cuenta 0 aunque
la parada haya llegado.

Esperado: **≥1**. Después libérala, o el robot no se moverá en la tarea siguiente:

```bash
source /opt/ros/jazzy/setup.bash
ros2 service call /release_emergency_stop std_srvs/srv/Empty
```

- [ ] **Paso 5: evidencia y commit**

```bash
cd ~/atriz_migracion
# 00_auditoria/evidencia/59_atriz_sensores.txt: salidas de los pasos 3 y 4,
# y que los faros cambiaron de color CONFIRMADO POR EL USUARIO mirando el robot.
git add 00_auditoria/evidencia/59_atriz_sensores.txt && git commit -m \
"Evidencia 59: sensores, luces y parada explicita de atriz.py"

cd ~/atriz_ws/src/Atriz_rvr && git add scripts/estudiantes/atriz.py && git commit -m \
"atriz.py: color(), distancia_frontal(), bateria(), luces() y parada_emergencia()

color() usa el servicio y no el topic: el mensaje Color no trae el canal claro,
que es el que discrimina (12.6x entre blanco y negro). bateria() da voltios, no
porcentaje: el porcentaje dijo 100 % con la bateria a 8.29 V."
```

---

## Tarea 6: que Ctrl-C pare el robot, verificado como se verifica un fallo intermitente

Esta es la protección que **ya falló en silencio** y cuya verificación anterior **pasó por
casualidad**. Una sola pasada verde sobre un fallo intermitente es indistinguible de que no haya
fallo, así que se repite.

**Ficheros:**
- Ninguno nuevo. Se verifica lo escrito en la tarea 2.

**Interfaces:**
- Consume: `Robot._al_ctrl_c`, `Robot.avanzar`.
- Produce: nada de código. Produce **evidencia**.

- [ ] **Paso 1: escribe el guion de prueba**

Crea `~/atriz_migracion/scripts/probar_ctrl_c_atriz.py`:

```python
#!/usr/bin/env python3
"""¿Para el robot un Ctrl-C a mitad de un avance? — se mide el DESPLAZAMIENTO.

    python3 probar_ctrl_c_atriz.py

⚠️ MUEVE EL ROBOT. Necesita 1 m despejado por delante.

🔴 Por que se repite: `rclpy.init()` sin `SignalHandlerOptions.NO` invalida su
   propio contexto en el SIGINT, y el fallo es INTERMITENTE — segun donde caiga
   el Ctrl-C, a veces la parada si sale. Por eso la verificacion del 2026-08-01
   de otra herramienta paso con el fallo dentro. Una pasada no concluye.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'atriz_ws/src/Atriz_rvr/scripts/estudiantes'))
from atriz import Robot                                      # noqa: E402

print(__doc__)
print('Avanzando 10 s a 0.15 m/s. Pulsa Ctrl-C a los ~3 s y mide con cinta\n'
      'CUANTO RECORRE EL ROBOT DESPUES de que pulses.\n')
with Robot() as robot:
    input('Marca la posicion inicial y pulsa Enter...')
    robot.avanzar(0.15, 10)
    print('Llego al final sin Ctrl-C: repite y pulsalo antes.')
```

- [ ] **Paso 2: ejecútalo CINCO veces**

🔴 **PIDE ESTO AL USUARIO. Mueve el robot.** Cinco corridas, midiendo con cinta el recorrido
**posterior** al Ctrl-C.

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 scripts/probar_ctrl_c_atriz.py     # x5, midiendo cada vez
```

Esperado: **las cinco** paran. El recorrido posterior debe ser del orden de la parada del
`collision_monitor` (**9.9 cm a 0.25 m/s**) o menos.

🔴 **Una sola corrida que no pare invalida la protección** aunque las otras cuatro vayan. No se
promedia: se arregla.

- [ ] **Paso 3: comprueba que no quedó la parada de emergencia enganchada**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 -c "
from atriz import Robot
with Robot() as r: r.avanzar(0.15, 1)
"
```

Esperado: **el robot se mueve** (~15 cm). Si no se mueve, el Ctrl-C está disparando la parada de
emergencia y dejándola enganchada — que es exactamente la trampa que el diseño decidió evitar.

- [ ] **Paso 4: evidencia y commit**

```bash
cd ~/atriz_migracion
# 00_auditoria/evidencia/60_atriz_ctrl_c.txt: las CINCO corridas, con el
# desplazamiento posterior de cada una. Y el resultado del paso 3.
git add 00_auditoria/evidencia/60_atriz_ctrl_c.txt scripts/probar_ctrl_c_atriz.py
git commit -m "Evidencia 60: Ctrl-C para el robot en 5 de 5, y no deja la parada enganchada"
```

---

## Tarea 7: los tres scripts de movimiento básico y la plantilla

**Ficheros:**
- Reescribir: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/01_avanzar.py`, `02_girar.py`,
  `03_cuadrado.py`, `90_template.py`

**Interfaces:**
- Consume: `Robot`, `avanzar`, `girar`, `parar`.
- Produce: nada que use otra tarea.

- [ ] **Paso 1: reescribe `01_avanzar.py`**

```python
#!/usr/bin/env python3
"""Practica 1 — Avanzar.

    python3 01_avanzar.py

El robot avanza 3 segundos y para.

Antes de ejecutarlo: deja 1 metro despejado por delante del robot. El LIDAR
barre a 15.5 cm del suelo, asi que una caja baja NO la ve.
"""
from atriz import Robot

# `with` se encarga de parar el robot y apagar el barrido pase lo que pase:
# aunque tu programa falle a la mitad, o aunque pulses Ctrl-C.
with Robot() as robot:
    print('Avanzando...')
    robot.avanzar(0.20, 3)      # 0.20 metros por segundo, durante 3 segundos
    print('Listo.')

# EJERCICIOS
#   1. Cambia la velocidad a 0.30. Mide con una cinta: ¿avanzo la mitad mas?
#   2. Pon una velocidad negativa. ¿Que hace?
#   3. Pide 1.5 m/s. El robot no llega ahi: mira lo que imprime el programa.
```

- [ ] **Paso 2: reescribe `02_girar.py`**

```python
#!/usr/bin/env python3
"""Practica 2 — Girar.

    python3 02_girar.py

El robot gira 90 grados a la izquierda.

Antes de ejecutarlo: deja unos 40 cm libres alrededor del robot.
"""
from atriz import Robot

with Robot() as robot:
    print('Girando 90 grados a la izquierda...')
    logrado = robot.girar(90)       # positivo = izquierda
    print(f'Giro {logrado:.1f} grados de verdad.')

# EJERCICIOS
#   1. Gira -90. ¿Hacia donde va?
#   2. Comprueba con un transportador cuanto giro. ¿Coincide con lo que imprime?
#   3. ¿Por que girar() devuelve un numero en vez de no devolver nada?
```

- [ ] **Paso 3: reescribe `03_cuadrado.py`**

```python
#!/usr/bin/env python3
"""Practica 3 — Un cuadrado.

    python3 03_cuadrado.py

Cuatro lados y cuatro giros de 90 grados.

Antes de ejecutarlo: necesitas un cuadrado libre de ~1.5 m de lado.
"""
from atriz import Robot

LADO_SEGUNDOS = 3      # a 0.20 m/s son unos 60 cm

with Robot() as robot:
    for lado in range(1, 5):
        print(f'Lado {lado} de 4...')
        robot.avanzar(0.20, LADO_SEGUNDOS)
        logrado = robot.girar(90)
        print(f'  esquina: {logrado:.1f} grados')

# EJERCICIOS
#   1. ¿Vuelve el robot al punto de partida? Marcalo con cinta y mide el error.
#   2. Suma los cuatro giros que imprime. ¿Cuanto se aleja de 360?
#   3. Haz un triangulo. ¿Cuantos grados hay que girar en cada esquina?
```

- [ ] **Paso 4: reescribe `90_template.py`**

```python
#!/usr/bin/env python3
"""Plantilla — copia este fichero para empezar tu propio programa.

    cp 90_template.py mi_programa.py
    python3 mi_programa.py

Lo que puedes pedirle al robot:

    robot.avanzar(velocidad, segundos)   # m/s (max 0.40) durante segundos
    robot.girar(grados)                  # + izquierda, - derecha; devuelve los reales
    robot.parar()
    robot.rumbo()                        # grados
    robot.distancia_frontal()            # metros hasta lo que tienes delante
    robot.color()                        # (rojo, verde, azul, claro)
    robot.bateria()                      # voltios
    robot.luces(rojo, verde, azul)       # 0-255 cada canal
    robot.parada_emergencia()            # el profesor tiene que liberarla
"""
from atriz import Robot

with Robot() as robot:

    # ── Tu programa va aqui ─────────────────────────────────────────────────
    robot.avanzar(0.20, 2)
    robot.girar(90)
    # ────────────────────────────────────────────────────────────────────────

    print('Bateria:', robot.bateria(), 'V')
```

- [ ] **Paso 5: ejecuta los cuatro contra el robot**

🔴 **PIDE ESTO AL USUARIO. Mueven el robot.** `03_cuadrado.py` necesita ~1.5 m de lado.

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
for f in 01_avanzar.py 02_girar.py 03_cuadrado.py 90_template.py; do
  read -p "Coloca el robot y pulsa Enter para $f..." _
  python3 "$f" || echo "FALLO en $f"
done
```

🔴 **«No dio error» no cuenta como verificado: el robot tiene que MOVERSE.** Míralo.

- [ ] **Paso 6: commit**

```bash
cd ~/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/01_avanzar.py scripts/estudiantes/02_girar.py \
        scripts/estudiantes/03_cuadrado.py scripts/estudiantes/90_template.py
git commit -m "Practicas 1-3 y plantilla, sobre la API del laboratorio

Salen de rospy, que no arranca en este sistema, y de /cmd_vel, que es la salida
del collision_monitor."
```

---

## Tarea 8: `04_giro_preciso.py` — el lazo cerrado contra la constante

Es la práctica con el contenido de robótica de verdad, y por eso va sola.

**Ficheros:**
- Reescribir: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/04_giro_preciso.py`

**Interfaces:**
- Consume: `Robot.girar`, `Robot.rumbo`, `Robot.parar`, `Robot._mandar`, `limitar`,
  `VEL_GIRO_MAX`, `TIEMPO_MAX`.
- Produce: `Robot.girar_por_tiempo(velocidad: float, segundos: float) -> None` — el lazo
  **abierto**, que la tarea 11 no usa y ninguna otra práctica debe usar.

- [ ] **Paso 1: añade a la API el giro por tiempo, que es el lazo abierto**

La práctica compara los dos lazos, así que necesita poder hacer el malo. La API no lo expone
todavía, y hay que decidir de dónde sale:

| | Salida | Por qué no / sí |
|---|---|---|
| (a) | que la práctica publique ella misma en `TOPIC_MANDO` | 🔴 **No.** Le enseña al alumno a publicar a pelo, que es justo lo que esta API quita de en medio, y le pone `/cmd_vel_raw` en las manos sin las siete protecciones |
| (b) | añadir `Robot.girar_por_tiempo()` a la API, documentado como «esto es el lazo abierto» | ✅ **Sí.** El alumno sigue dentro de la API, y el método lleva escrito por qué no debe usarlo para girar de verdad |

Añade a `atriz.py`, junto a `girar()`:

```python
    def girar_por_tiempo(self, velocidad, segundos):
        """Gira a `velocidad` rad/s durante `segundos`. LAZO ABIERTO.

        📝 Existe SOLO para la practica 4, que compara el lazo abierto con el
           cerrado. Para girar de verdad usa `girar(grados)`: mide el rumbo y
           acierta, y esta no — pidiendole 90 grados asi salen 86.6 / 86.2 /
           87.7 (n=3, medido en este robot).
        """
        velocidad, aviso = limitar(velocidad, VEL_GIRO_MAX, 'giro', 'rad/s')
        if aviso:
            print(aviso)
        segundos, aviso = limitar(abs(segundos), TIEMPO_MAX, 'tiempo', 's')
        if aviso:
            print(aviso)
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            self._mandar(0.0, velocidad)
        self.parar()
```

- [ ] **Paso 2: reescribe la práctica**

```python
#!/usr/bin/env python3
"""Practica 4 — Girar bien: lazo abierto contra lazo cerrado.

    python3 04_giro_preciso.py

Antes de ejecutarlo: ~40 cm libres alrededor, y un transportador o una cinta
para marcar el rumbo.

⚠️ Y deja el robot encendido unos 10 minutos antes de medir. La odometria deriva
   ~1 grado cada 30 s los primeros minutos tras encender el RVR, y 0.001 siete
   minutos despues: midiendo en frio no sabrias si el error es del lazo o de eso.

═══════════════════════════════════════════════════════════════════════════════
LA IDEA
═══════════════════════════════════════════════════════════════════════════════
Girar «durante el tiempo justo» es un LAZO ABIERTO: mandas la orden y confias.
En este robot, pidiendo 90 grados asi salen 86.6 / 86.2 / 87.7 — un deficit de
unos 3 grados que NO depende de la bateria (se midio del 55 % al 100 %).

La salida barata seria multiplicar por 1.04. Funcionaria hoy, en este suelo, con
este robot y esta bateria. `robot.girar()` hace otra cosa: MIDE el rumbo
mientras gira y para cuando llega. Eso es un LAZO CERRADO.

Este programa hace los dos y te deja comparar.
"""
import math
import time

from atriz import Robot

OBJETIVO = 90.0
VELOCIDAD_GIRO = 0.8        # rad/s

with Robot() as robot:

    # ── Lazo abierto ────────────────────────────────────────────────────────
    # Cuanto «deberia» tardar: el angulo en radianes partido por la velocidad.
    segundos = math.radians(OBJETIVO) / VELOCIDAD_GIRO

    input('\n[1/2] LAZO ABIERTO. Marca el rumbo actual y pulsa Enter...')
    antes = robot.rumbo()
    robot.girar_por_tiempo(VELOCIDAD_GIRO, segundos)
    time.sleep(0.5)                  # el robot sigue rodando un poco
    logrado_abierto = robot.rumbo() - antes
    print(f'      pedido {OBJETIVO:.0f}, /odom dice {logrado_abierto:.1f}')
    input('      Mide con el transportador y pulsa Enter...')

    # ── Lazo cerrado ────────────────────────────────────────────────────────
    input('\n[2/2] LAZO CERRADO. Marca el rumbo actual y pulsa Enter...')
    logrado_cerrado = robot.girar(OBJETIVO)
    print(f'      pedido {OBJETIVO:.0f}, logrado {logrado_cerrado:.1f}')
    input('      Mide con el transportador y pulsa Enter...')

    print(f'\nError del lazo abierto: {abs(OBJETIVO - logrado_abierto):.1f} grados')
    print(f'Error del lazo cerrado: {abs(OBJETIVO - logrado_cerrado):.1f} grados')

# EJERCICIOS
#   1. ¿Cual de los dos se acerco mas? ¿Cuanto?
#   2. Repite los dos tres veces. ¿Cual REPITE mejor? (no es lo mismo que acertar)
#   3. Pon el robot sobre una alfombra y repite. ¿Cual aguanta el cambio?
#   4. ¿Que necesita el lazo cerrado que el abierto no? (pista: un sensor)
#   5. Cambia OBJETIVO a 360. Ojo: ¿por que no sale 0?
```

📝 **Ese ejercicio 5 no es un adorno.** Es el error que la función `acumular()` de la biblioteca
existe para evitar, y el alumno lo ve desde fuera: leyendo el rumbo absoluto, una vuelta entera
vuelve al punto de partida.

⚠️ **Y ojo con `logrado_abierto = robot.rumbo() - antes` en el caso de 360:** ahí sí da ~0, porque
resta rumbos absolutos. Es correcto para 90 y **es un ejemplo del problema** para 360 — déjalo así
y que el ejercicio 5 lo destape.

- [ ] **Paso 3: ejecútalo, n=3**

🔴 **PIDE ESTO AL USUARIO. Gira el robot.** Deja el robot encendido 10 minutos antes (deriva de
yaw del arranque en frío).

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
for i in 1 2 3; do python3 04_giro_preciso.py; done
```

Esperado: el lazo abierto en torno a **86–88°**, el cerrado dentro de **±2°** de 90. Si el cerrado
no gana, este diseño se equivoca y hay que decirlo, no ajustar hasta que salga.

- [ ] **Paso 4: evidencia y commit**

```bash
cd ~/atriz_migracion
# 00_auditoria/evidencia/61_practica_04.txt: las tres corridas, con las dos
# medidas de cada una (odom y transportador) para los dos lazos.
git add 00_auditoria/evidencia/61_practica_04.txt && git commit -m \
"Evidencia 61: la practica 4 mide el lazo abierto contra el cerrado, n=3"

cd ~/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/04_giro_preciso.py scripts/estudiantes/atriz.py
git commit -m "Practica 4: lazo abierto contra lazo cerrado, con el deficit medido delante

girar_por_tiempo() se anade a la API SOLO para que la practica pueda comparar, y
lo dice en su docstring. La alternativa era que el alumno publicara a pelo en
cmd_vel_raw, que es justo lo que esta API quita de en medio."
```

---

## Tarea 9: los dos scripts de color

Son los que usan `/enable_color`, que **no existe**. Cambian de fondo, no de sintaxis.

**Ficheros:**
- Reescribir: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/05_sensor_color.py`,
  `11_sensor_avanzado.py`

**Interfaces:**
- Consume: `Robot.color`, `Robot.hay_color`, `Robot.avanzar`, `Robot.parar`.
- Produce: nada.

- [ ] **Paso 1: reescribe `05_sensor_color.py`**

```python
#!/usr/bin/env python3
"""Practica 5 — El sensor de color.

    python3 05_sensor_color.py

🔴 ESTA PRACTICA NECESITA UN ARRANQUE ESPECIAL DEL ROBOT. Lo hace el profesor:

    sudo systemctl stop atriz-robot
    ros2 launch atriz_rvr_bringup robot.launch.py color_detection:=true

Por que: el sensor de color lleva su PROPIA LUZ debajo del robot, y sin ella no
ve nada — el canal claro pasa de 741 encendida a 4 apagada, 185 veces menos. Esa
luz se enciende ANTES de configurar el sensor y NO se puede encender despues, asi
que se decide en el arranque. El arranque normal la deja apagada a proposito,
porque es un LED blanco encendido todo el rato bajo el chasis.

Si arrancas normal, este programa te lo dira y saldra: no te devolvera ceros
haciendolos pasar por «negro».
"""
import sys
import time

from atriz import Robot

with Robot() as robot:
    if not robot.hay_color:
        print('\nEl sensor de color esta apagado. Lee la cabecera de este fichero.')
        sys.exit(1)

    print('Pon distintas superficies bajo el robot. Ctrl-C para salir.\n')
    print(f'{"rojo":>6} {"verde":>6} {"azul":>6} {"claro":>6}   R/G    B/G')
    while True:
        rojo, verde, azul, claro = robot.color()
        # Se normaliza por VERDE porque es el canal mas sensible: sobre rojo,
        # R/G sube de 0.48 a 2.74; sobre azul, B/G sube a 0.86.
        rg = rojo / verde if verde else 0.0
        bg = azul / verde if verde else 0.0
        print(f'{rojo:6d} {verde:6d} {azul:6d} {claro:6d}  {rg:5.2f}  {bg:5.2f}')
        time.sleep(0.5)

# EJERCICIOS
#   1. Prueba blanco, negro, rojo y azul. ¿Que columna cambia mas?
#   2. `claro` va de ~181 sobre negro a ~2288 sobre blanco. ¿Y R/G?
#   3. ¿Por que dividimos por verde en vez de usar el rojo a secas?
```

- [ ] **Paso 2: reescribe `11_sensor_avanzado.py`**

```python
#!/usr/bin/env python3
"""Practica 11 — Reaccionar a lo que ve: parar sobre negro.

    python3 11_sensor_avanzado.py

🔴 NECESITA EL ARRANQUE CON color_detection:=true. Lee la cabecera de la
   practica 5.

Antes de ejecutarlo: 1 metro despejado por delante, y una franja de cinta negra
cruzando el camino del robot.
"""
import sys

from atriz import Robot

# El canal claro va de ~181 sobre negro a ~2288 sobre blanco (medido). El umbral
# se pone a la mitad del recorrido, no a ojo.
UMBRAL_NEGRO = 400

with Robot() as robot:
    if not robot.hay_color:
        print('\nEl sensor de color esta apagado. Lee la practica 5.')
        sys.exit(1)

    print('Avanzando hasta encontrar negro...')
    # No se usa avanzar(), que bloquea los segundos que le pidas: aqui hay que
    # mirar el sensor MIENTRAS se avanza.
    while True:
        _, _, _, claro = robot.color()
        if claro < UMBRAL_NEGRO:
            print(f'Negro detectado (claro={claro}). Parando.')
            robot.parar()
            break
        robot.avanzar(0.10, 0.2)     # tramos cortos: 20 cm/s durante 0.2 s

# EJERCICIOS
#   1. Baja el umbral a 200. ¿Se le pasa la linea?
#   2. Sube la velocidad a 0.30. ¿Que le pasa a la distancia de parada?
#   3. Haz que retroceda 20 cm despues de encontrar el negro.
```

- [ ] **Paso 3: ejecútalos con el arranque especial**

🔴 **PIDE ESTO AL USUARIO. Requiere `sudo` y mueve el robot.**

```bash
# 1) el profesor rearranca el robot con el sensor encendido
sudo systemctl stop atriz-robot
source /opt/ros/jazzy/setup.bash
setsid nohup ros2 launch atriz_rvr_bringup robot.launch.py color_detection:=true \
  < /dev/null > /tmp/robot_color.log 2>&1 &

# 2) las dos practicas
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
python3 05_sensor_color.py        # Ctrl-C para salir
python3 11_sensor_avanzado.py     # con cinta negra cruzando el camino

# 3) devolver el robot a su estado normal
ps -eo pid,comm | awk '$2=="ros2"{print $1}' | xargs -r kill -INT
sudo systemctl start atriz-robot
```

⚠️ **`ps -eo comm`, nunca `pkill -f`**: el patrón coincide con la propia línea de comando del shell
y **mata tu terminal**. Ha pasado dos veces en este proyecto.

Esperado: en la 5, `claro` recorriendo de **~181 sobre negro a ~2288 sobre blanco**; en la 11, el
robot parándose sobre la cinta.

- [ ] **Paso 4: comprueba que sin el arranque especial AVISA en vez de mentir**

```bash
# con el robot ya en su arranque normal
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 05_sensor_color.py; echo "codigo de salida: $?"
```

Esperado: el aviso y **código de salida 1**. Nunca una tabla de ceros.

- [ ] **Paso 5: evidencia y commit**

```bash
cd ~/atriz_migracion
# 00_auditoria/evidencia/62_practicas_color.txt: las lecturas sobre las cuatro
# superficies, el robot parandose sobre la cinta, y el aviso del paso 4.
git add 00_auditoria/evidencia/62_practicas_color.txt && git commit -m \
"Evidencia 62: las practicas de color, con y sin color_detection"

cd ~/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/05_sensor_color.py scripts/estudiantes/11_sensor_avanzado.py
git commit -m "Practicas 5 y 11: fuera /enable_color, que no existe

Usan el canal claro, que es el que discrimina (12.6x entre blanco y negro) y que
el topic /color no trae. Y si el robot arranco sin color_detection lo dicen y
salen, en vez de imprimir ceros como si fueran negro."
```

---

## Tarea 10: `10_movimiento_completo.py` y `99_test_ctrl_c.py`

**Ficheros:**
- Reescribir: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/10_movimiento_completo.py`,
  `99_test_ctrl_c.py`

**Interfaces:**
- Consume: `Robot` y su API pública.
- Produce: nada.

- [ ] **Paso 1: reescribe `10_movimiento_completo.py`**

```python
#!/usr/bin/env python3
"""Practica 10 — Tu propia clase: un robot que patrulla.

    python3 10_movimiento_completo.py

Antes de ejecutarlo: un cuadrado libre de ~1.5 m de lado.

La idea: `Robot` te da las ordenes basicas. Aqui construyes ENCIMA una clase con
el comportamiento que tu quieres. Es como se organiza el codigo de un robot de
verdad: capas, cada una apoyada en la de abajo.
"""
from atriz import Robot


class Patrulla:
    """Recorre un recinto y avisa cuando se acerca demasiado a algo."""

    def __init__(self, robot, distancia_minima=0.35):
        self.robot = robot
        self.distancia_minima = distancia_minima
        self.giros = 0

    def hay_sitio(self):
        """¿Cabe seguir avanzando?"""
        return self.robot.distancia_frontal() > self.distancia_minima

    def un_tramo(self):
        """Avanza mientras haya sitio; si no, gira."""
        if self.hay_sitio():
            self.robot.avanzar(0.20, 1)
        else:
            print(f'  algo a menos de {self.distancia_minima} m: giro')
            self.robot.girar(90)
            self.giros += 1

    def patrullar(self, tramos):
        for numero in range(1, tramos + 1):
            print(f'Tramo {numero} de {tramos}  '
                  f'(frontal: {self.robot.distancia_frontal():.2f} m)')
            self.un_tramo()
        print(f'Fin. Giro {self.giros} veces.')


with Robot() as robot:
    Patrulla(robot).patrullar(tramos=12)

# EJERCICIOS
#   1. Cambia `distancia_minima` a 0.60. ¿Gira antes o despues?
#   2. Haz que gire -90 en vez de 90. ¿Cambia el recorrido?
#   3. Anade un metodo que encienda las luces en rojo cuando vaya a girar.
#   4. ¿Por que `un_tramo` avanza solo 1 segundo y no 10?
```

- [ ] **Paso 2: reescribe `99_test_ctrl_c.py`**

```python
#!/usr/bin/env python3
"""Prueba 99 — ¿Para el robot cuando pulsas Ctrl-C?

    python3 99_test_ctrl_c.py

⚠️ MUEVE EL ROBOT. Necesita 1 metro despejado por delante.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTA PRUEBA EXISTE Y NO ES UNA CURIOSIDAD
═══════════════════════════════════════════════════════════════════════════════
En este laboratorio, Ctrl-C YA FALLO. `rclpy.init()` instala su propio manejador
de la senal e invalida su contexto: el codigo que intenta parar el robot muere
con «publisher's context is invalid». Medido: 0 lineas de parada con el defecto,
5 con la opcion correcta.

Y el fallo es INTERMITENTE — segun donde caiga el Ctrl-C, a veces si para. Por
eso esta prueba se corre VARIAS VECES: una pasada verde sobre un fallo
intermitente es indistinguible de que no haya fallo.

Debajo, el driver tiene un watchdog que corta a los 0.3 s sin recibir ordenes.
Asi que aunque mataras el programa a lo bruto, el robot se para. Ctrl-C es el
primer cinturon; el watchdog, el segundo.
"""
from atriz import Robot

print(__doc__)
with Robot() as robot:
    input('Marca la posicion del robot y pulsa Enter...')
    print('Avanzando 8 s. Pulsa Ctrl-C cuando quieras y MIDE cuanto recorre')
    print('el robot DESPUES de que lo pulses.\n')
    robot.avanzar(0.15, 8)
    print('Llegue al final sin que pulsaras Ctrl-C.')

# EJERCICIOS
#   1. Repitelo cinco veces. ¿Paro las cinco?
#   2. Mide el recorrido posterior. ¿Cuanto varia entre corridas?
#   3. Prueba a cerrar la terminal en vez de pulsar Ctrl-C. ¿Que pasa? ¿Por que?
```

- [ ] **Paso 3: ejecútalos**

🔴 **PIDE ESTO AL USUARIO. Mueven el robot.** La 10 necesita ~1.5 m de lado.

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
python3 10_movimiento_completo.py
python3 99_test_ctrl_c.py       # x3, pulsando Ctrl-C a distintas alturas
```

Esperado: la patrulla girando al acercarse a algo, y las tres corridas de la 99 parando.

- [ ] **Paso 4: commit**

```bash
cd ~/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/10_movimiento_completo.py scripts/estudiantes/99_test_ctrl_c.py
git commit -m "Practicas 10 y 99 sobre la API del laboratorio

La 99 gana valor: ahora prueba una proteccion que fallo de verdad en este
proyecto, y su cabecera explica por que se repite."
```

---

## Tarea 11: el seguidor de línea

El PID es lo que se enseña y **no se toca**. Cambia de dónde saca el color y a dónde manda la
velocidad.

**Ficheros:**
- Reescribir: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/seguidor_linea_pid_demo.py`
- Revisar: `seguidor_config.json`, `calibracion_colores.json`

**Interfaces:**
- Consume: `Robot.color`, `Robot._mandar` **no** — se usa `avanzar` en tramos cortos.
- Produce: nada.

- [ ] **Paso 1: añade a la API el mando continuo que el PID necesita**

Un lazo de control no puede usar `avanzar(v, t)`, que bloquea. Añade a `atriz.py`:

```python
    def mover(self, velocidad, giro):
        """Manda UNA orden de velocidad y vuelve enseguida. Para lazos de control.

        📝 A diferencia de `avanzar()`, esta NO bloquea ni republica: la tienes
           que llamar tu en tu bucle, MAS DE TRES VECES POR SEGUNDO. Si no, el
           watchdog del driver corta a los 0.3 s y el robot ira a tirones.
        """
        velocidad, aviso = limitar(velocidad, self._vel_max, 'velocidad', 'm/s')
        if aviso:
            print(aviso)
        giro, aviso = limitar(giro, VEL_GIRO_MAX, 'giro', 'rad/s')
        if aviso:
            print(aviso)
        orden = Twist()
        orden.linear.x = float(velocidad)
        orden.angular.z = float(giro)
        self._pub_mando.publish(orden)
```

- [ ] **Paso 2: reescribe el seguidor**

Conserva la clase `PID` **tal cual está** (es el contenido docente) y sustituye la parte de ROS:

```python
#!/usr/bin/env python3
"""Seguidor de linea con control PID.

    python3 seguidor_linea_pid_demo.py

🔴 NECESITA EL ARRANQUE CON color_detection:=true. Lee la practica 5.

Antes de ejecutarlo: una linea negra sobre suelo claro, y el robot encima de
ella mirando en la direccion de avance.

El PID de este fichero es el mismo que antes: es lo que se estudia. Lo que
cambia es de donde sale el color y a donde va la velocidad.
"""
import json
import sys
import time
from pathlib import Path

from atriz import Robot


class PID:
    """Control proporcional-integral-derivativo.

    error -> salida. Kp reacciona a lo que pasa AHORA, Ki a lo acumulado, Kd a
    lo rapido que cambia.
    """

    def __init__(self, kp=0.5, ki=0.0, kd=0.3, limite=1.5):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.limite = limite
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.error_anterior = 0.0
        self.instante_anterior = None

    def calcular(self, error):
        ahora = time.monotonic()
        dt = 0.1 if self.instante_anterior is None else ahora - self.instante_anterior
        self.instante_anterior = ahora
        if dt <= 0.0:
            dt = 1e-3

        self.integral += error * dt
        derivada = (error - self.error_anterior) / dt
        self.error_anterior = error

        salida = self.kp * error + self.ki * self.integral + self.kd * derivada
        return max(-self.limite, min(self.limite, salida))


CONFIG = Path(__file__).parent / 'seguidor_config.json'
ajustes = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}

VELOCIDAD = ajustes.get('velocidad', 0.08)          # m/s
UMBRAL = ajustes.get('umbral_claro', 400)           # claro por debajo = linea
PERIODO = 0.1                                       # s -> 10 Hz, y el watchdog
                                                    #     corta a los 0.3

with Robot() as robot:
    if not robot.hay_color:
        print('\nEl sensor de color esta apagado. Lee la practica 5.')
        sys.exit(1)

    pid = PID(**ajustes.get('pid', {}))
    print('Siguiendo la linea. Ctrl-C para parar.\n')

    while True:
        inicio = time.monotonic()
        _, _, _, claro = robot.color()

        # El error: cuanto se aleja el sensor de estar sobre la linea.
        # Normalizado para que el PID no dependa de la escala del sensor.
        error = (claro - UMBRAL) / UMBRAL

        robot.mover(VELOCIDAD, -pid.calcular(error))

        # 🔴 El ritmo lo marca este sleep, y tiene que ser menor que 0.3 s: es
        #    lo que tarda el watchdog del driver en cortar. Leer el color cuesta
        #    13-20 ms, asi que cabe de sobra.
        time.sleep(max(0.0, PERIODO - (time.monotonic() - inicio)))

# EJERCICIOS
#   1. Pon Kd a 0. ¿Que le pasa al robot en las curvas?
#   2. Sube Kp hasta que oscile. Eso es la ganancia critica.
#   3. Sube VELOCIDAD a 0.20. ¿Sigue valiendo el mismo PID?
#   4. Sube PERIODO a 0.5. ¿Por que va a tirones? (pista: el watchdog)
```

- [ ] **Paso 3: revisa los dos JSON**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && cat seguidor_config.json calibracion_colores.json
```

`seguidor_config.json` tiene que tener las claves que lee el script (`velocidad`, `umbral_claro`,
`pid`). Si trae claves de ROS 1 (`velocidad_maxima`, `~algo`), **actualízalo**.
`calibracion_colores.json`: si nada lo lee, **bórralo** — un fichero que nadie usa es deuda.

- [ ] **Paso 4: ejecútalo**

🔴 **PIDE ESTO AL USUARIO. Mueve el robot y requiere `sudo` para el arranque especial.** Usa el
mismo procedimiento del paso 3 de la tarea 9.

Esperado: el robot siguiendo la línea. **Si va a tirones, mira el `sleep` antes de tocar el PID**:
un período por encima de 0.3 s reproduce exactamente ese síntoma, y no es culpa de las ganancias.

- [ ] **Paso 5: evidencia y commit**

```bash
cd ~/atriz_migracion
# 00_auditoria/evidencia/63_seguidor_linea.txt: si siguio la linea, cuanto
# aguanto, y con que ajustes.
git add 00_auditoria/evidencia/63_seguidor_linea.txt && git commit -m \
"Evidencia 63: el seguidor de linea sobre la API del laboratorio"

cd ~/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/seguidor_linea_pid_demo.py scripts/estudiantes/seguidor_config.json \
        scripts/estudiantes/atriz.py
git commit -m "Seguidor de linea sobre la API. El PID no se toca

mover() se anade para lazos de control: manda una orden y vuelve. Lo que si
cambia es el umbral, que ahora usa el canal claro — el que discrimina."
```

---

## Tarea 12: los cinco documentos, y sacar las credenciales

🔴 **La tarea con consecuencias fuera del repositorio.** `Atriz_rvr` es **público**.

**Ficheros:**
- Reescribir: `00_LEEME_PRIMERO.md`, `GUIA_PASO_A_PASO.md`, `README.md`, `REFERENCIAS.md`,
  `SEGUIDOR_LINEA_EXPLICACION.md` (todos en `Atriz_rvr/scripts/estudiantes/`)

**Interfaces:**
- Consume: la API completa (tareas 1-11), para que los ejemplos que citan sean los reales.
- Produce: nada de código.

- [ ] **Paso 1: mide qué hay que sacar, antes de tocar nada**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
grep -rncE "rospy|roscore|/cmd_vel|enable_color|Contrase|SSID|catkin" *.md
```

Guarda esta salida: es el «antes» contra el que se compara el paso 4.

- [ ] **Paso 2: reescribe los cinco, con este contenido**

**`00_LEEME_PRIMERO.md`** — lo primero que abre el alumno el primer día. Secciones, en este orden:

1. **Qué es esto** (3 líneas): un robot Sphero RVR con un LIDAR, gobernado desde su Raspberry Pi.
2. **Conectarte al robot**: la red del laboratorio y `ssh sphero@rvr-NN.local`.
   🔴 **La PSK y la contraseña NO van aquí**: «te las da el profesor».
3. **Tu primer programa**, entero y sin explicar nada todavía:
   ```bash
   cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
   python3 01_avanzar.py
   ```
4. **Qué hace el robot al empezar**, que es lo que evita el primer «no funciona»: la biblioteca
   **enciende el barrido del LIDAR** al conectar, y **sin barrido el robot no obedece** — no está
   roto.
5. **La tabla de la API**, la misma que la cabecera de `90_template.py`.
6. **Cuando algo no va**: los cuatro síntomas de abajo, con su causa.
7. **Al terminar**: usa `with`, y si tu programa se cuelga, Ctrl-C.

**`GUIA_PASO_A_PASO.md`** — el recorrido de las 16 h. Una sección por práctica, en el orden
`01 → 02 → 03 → 04 → 05 → 10 → 11 → seguidor → 90`, y cada una con: qué se aprende, qué hace falta
en el suelo, el comando, qué debería verse, y los ejercicios. Al final, **las cuatro cosas que
sorprenden y no son fallos**:

| Síntoma | Qué es de verdad |
|---|---|
| El robot no se mueve y no hay error | Falta `/scan`, o hay una parada de emergencia enganchada. La libera el profesor |
| Va mucho más despacio de lo pedido | El polígono de precaución frena al **40 %** si hay algo a menos de 0.36 m, **aunque el robot se aleje**: 30 cm comandados → 14 medidos |
| Los ángulos se van acumulando mal | La odometría deriva **~1 °/30 s** los primeros minutos tras encender el RVR, y 0.001 siete minutos después |
| El LIDAR no ve una caja baja | Barre a **15.5 cm del suelo**. «Despejado a ras de suelo» no basta |

**`README.md`** — índice de la carpeta: qué fichero es cada cosa, en una tabla. Y una línea sobre
`atriz.py`: «la biblioteca del laboratorio; no hace falta instalar nada».

**`REFERENCIAS.md`** — la referencia completa de la API: cada método con su firma, qué devuelve,
sus límites y **el porqué de cada protección**, con la medida detrás.
🔴 Fuera todo lo de ROS 1: `rospy`, `rosrun`, `catkin`, las tablas de servicios de ROS 1.
⚠️ **No pongas un enlace a `03_operacion/API_LABORATORIO.md`**: vive en `atriz_migracion`, que es
**otro repositorio y además privado**. Un enlace roto en un repositorio público es exactamente la
deriva documental que este proyecto audita. Cítalo por nombre, sin enlazar.

**`SEGUIDOR_LINEA_EXPLICACION.md`** — el PID explicado. **Es el documento que menos cambia**: la
teoría es la misma. Cambian los ejemplos de código y la sección de dónde sale el color, que ahora
es el **canal claro** (`~181` sobre negro, `~2288` sobre blanco).

Y lo que **sale** de los cinco:

| Fuera | Por qué |
|---|---|
| 🔴 **La PSK del WiFi y la contraseña de usuario** | Es material que ven los alumnos, en un repositorio público. Se sustituyen por «pídeselas al profesor» |
| `roscore` y arrancar el driver a mano | El robot arranca solo desde el 2026-07-31 (`atriz-robot.service`) |
| `/enable_color` | No existe |
| `/cmd_vel` como topic al que escribir | Es la salida del `collision_monitor` |
| `catkin`, `rospy`, `rosrun` | Es ROS 2 |

Lo que **entra**, y hoy no está:

| Dentro | Por qué |
|---|---|
| Que la biblioteca **enciende el barrido** al conectar | Sin `/scan` el robot no obedece y parece averiado. Es el primer «no funciona» del curso |
| Que la parada de emergencia es un **acto explícito** y **la libera el profesor** | Si no, el siguiente alumno se encuentra un robot mudo |
| Que **ir despacio no es estar atascado** | El polígono de precaución frena al 40 % **aunque el robot se aleje**: 30 cm comandados → 14 medidos |
| Que la odometría **deriva mucho más los primeros minutos** tras encender el RVR | ~1 °/30 s recién encendido contra 0.001 siete minutos después: decenas de grados sobre una práctica de 15 min |
| Que el LIDAR barre a **15.5 cm del suelo** | «Despejado a ras de suelo» no basta |
| La tabla de la API | Es lo que el alumno mira cada cinco minutos |

- [ ] **Paso 3: comprueba que no queda ningún secreto**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
grep -rniE "contrase|password|psk|ssid|passwd" *.md *.py
```

Esperado: **solo** las líneas que dicen «pídesela al profesor». Ninguna con un valor.

- [ ] **Paso 4: comprueba el resto de la limpieza**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
grep -rncE "rospy|roscore|/cmd_vel|enable_color|catkin" *.md *.py
```

Esperado: **0 en todos**, salvo menciones explícitas de por qué algo **no** se usa —
`/cmd_vel` aparecerá citado en la explicación de por qué se escribe en `cmd_vel_raw`. Revisa una a
una: este proyecto ya contó dos veces **un comentario sobre un ajuste como si fuera el ajuste**.

- [ ] **Paso 5: commit, y deja escrito lo que ESTO NO ARREGLA**

```bash
cd ~/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/*.md && git commit -m \
"Documentacion del curso reescrita: fuera ROS 1 y fuera las credenciales

Salen la PSK del WiFi y la contrasena de usuario, que estaban en texto plano en
un repositorio publico. Sale roscore, arrancar el driver a mano, /enable_color y
/cmd_vel. Entra lo que hoy falta y se necesita el primer dia: que el barrido se
enciende, que la parada la libera el profesor, y que ir despacio no es estar
atascado."
```

🔴 **Y AVISA AL USUARIO, en voz alta, de que esto NO cierra la exposición:**

> Sacar el texto del contenido actual **no borra el historial**. Las credenciales siguen siendo
> alcanzables por el SHA de los commits viejos en `main`, `ros2`, `migracion-ros2` y
> `wip/scripts-estudiantes`, y **cualquier fork se las queda para siempre**.
>
> **Lo que lo cierra es rotarlas**, y es acción tuya: cambiar la PSK del WiFi del laboratorio y la
> contraseña del usuario. Purgar el historial después es higiene, y es incompleta por naturaleza.
> **Al revés no sirve de nada.**

---

## Tarea 13: la pasada completa, y cerrar

**Ficheros:**
- Modificar: `~/atriz_migracion/CLAUDE.md`, `TRASPASO.md`, `CHANGELOG.md`
- Modificar: `~/atriz_migracion/03_operacion/API_LABORATORIO.md` (marcar lo verificado)

**Interfaces:**
- Consume: todo.
- Produce: el veredicto.

- [ ] **Paso 1: pasa los verificadores**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/ -q
python3 scripts/auditar_documentacion.py
bash scripts/verificar_robot.sh --hardware
```

Esperado: los tres en verde. Los tests son **42** (24 de `aceptacion_nucleo` + 18 nuevos).

- [ ] **Paso 2: los diez scripts, de un tirón, sobre un robot RECIÉN REINICIADO**

🔴 **PIDE ESTO AL USUARIO: reinicia el robot.** Es la única forma de comprobar que el material
funciona sobre el estado en el que un alumno se lo encuentra — con el barrido apagado y sin que
nadie haya tocado nada.

```bash
# el usuario:  sudo reboot   · esperar ~40 s
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
for f in 01_avanzar.py 02_girar.py 03_cuadrado.py 04_giro_preciso.py \
         10_movimiento_completo.py 90_template.py 99_test_ctrl_c.py; do
  read -p "Coloca el robot y pulsa Enter para $f..." _
  python3 "$f" && echo "OK $f" || echo "FALLO $f"
done
# los tres de color van aparte: necesitan color_detection:=true (tarea 9)
```

🔴 **Un script que «no da error» y no mueve el robot NO cuenta.** Míralo.

- [ ] **Paso 3: comprueba que el alumno no puede saltarse la seguridad sin querer**

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
grep -rn "cmd_vel" *.py | grep -v "cmd_vel_raw"
```

Esperado: **ninguna línea**, salvo comentarios que expliquen por qué no se usa. Era el error que
cometían los diez scripts anteriores, quince veces.

- [ ] **Paso 4: actualiza el estado del proyecto**

- `CLAUDE.md`: en «Herramientas de diagnóstico», añade `probar_ctrl_c_atriz.py`. Y en las
  decisiones, que **el material docente corre sobre `atriz.py`, no sobre `rclpy`**.
- `TRASPASO.md`: el material docente cerrado, y el siguiente paso del orden acordado —
  **la decisión del arranque automático de Nav2/SLAM**.
- `CHANGELOG.md`: una entrada con lo medido en las evidencias 56-63.
- `03_operacion/API_LABORATORIO.md`: marca qué quedó verificado y **qué no**. Lo no ejecutado va
  como **NO VERIFICADO**, no se omite.

⚠️ **Busca TODAS las menciones, no la primera.** Corregir la cabecera de un capítulo y dejar una
subsección diciendo lo contrario ya pasó en este proyecto, el mismo día.

- [ ] **Paso 5: commit de cierre en los dos repositorios**

```bash
cd ~/atriz_migracion
git add CLAUDE.md TRASPASO.md CHANGELOG.md 03_operacion/API_LABORATORIO.md
git commit -m "Material docente cerrado: las diez practicas corren sobre atriz.py

Verificado ejecutandolas contra el robot tras un reinicio de verdad. Evidencias
56-63. Lo que queda abierto va marcado NO VERIFICADO."
git push origin main

cd ~/atriz_ws/src/Atriz_rvr && git push origin ros2
```

🔴 **Antes del `push`, comprueba que puedes:** `git fetch origin`. En un sistema recién instalado
no hay credenciales y los commits se quedan solo en la tarjeta.

---

## Lo que este plan NO hace

- **No rota las credenciales expuestas** ni purga el historial. Es acción del usuario, sobre
  GitHub y con la red del laboratorio delante.
- **No toca la plataforma web.** La API corre en el robot, para el alumno que trabaja en el robot.
- **No arregla la deriva de yaw del arranque en frío.** Se documenta; desaparece sola.
- **No prueba nada en un segundo robot.** Los 15 restantes están montados y esperando, pero el
  aprovisionamiento va después en el orden acordado.
