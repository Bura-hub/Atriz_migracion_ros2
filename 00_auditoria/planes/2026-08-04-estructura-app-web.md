# La estructura de la aplicación web — diseño

> **Qué es esto.** El diseño de la aplicación, no de la capa de datos. La capa de datos ya existe:
> `atriz-lab`, `frontend/src/lib/rosbridge/`, **97 pruebas**, y el 2026-08-04 **movió un robot real
> 60 cm** con el código de producción. Lo que nunca se diseñó es la aplicación que la usa.
>
> **Escrito el 2026-08-04 desde el PC**, sobre lo decidido y lo medido. Todo lo que aquí se afirma
> del robot está medido; lo que no, va marcado.

---

## 1 · Qué es esta aplicación, y qué no es

**Decisión 17, cerrada:** la web es un **taller presencial sin SSH**. El alumno está en el aula con
el robot delante. **El producto es el TERMINAL**; la teleoperación va la última, porque **ninguna de
las diez prácticas teleopera**.

| Es | No es |
|---|---|
| El sitio donde el alumno **escribe y ejecuta** su código, en vez de entrar por SSH | Un laboratorio remoto: las prácticas miden con cinta y transportador |
| El sitio donde **ve lo que el robot ve** mientras su código corre | Un simulador ni un gemelo digital |
| El sitio donde el **profesor ve los 16** y sabe quién está atascado | Un sistema de reservas: el profesor asigna, robot fijo dentro de la clase |
| Un **botón de parada** que funciona | Una consola de administración del robot |

---

## 2 · La aplicación tiene DOS MITADES, y una está bloqueada

Esto gobierna todo el orden de construcción y conviene verlo antes que el mapa de rutas.

| Mitad | Por dónde habla | Estado |
|---|---|---|
| **Telemetría, salud, LEDs, LIDAR, teleoperación** | **rosbridge**, `ws://rvr-NN.local:9090` | ✅ **Construible hoy.** La capa de datos existe y está probada contra el robot |
| **El terminal: escribir y ejecutar código del alumno** | **El agente de sesión**, `wss://rvr-NN.local:9443` | 🔴 **Bloqueada.** El agente no existe, y su diseño está gateado por la F0 (aislamiento de clientes del AP del aula) |

🔴 **La ironía que hay que asumir: el producto —el terminal— es la mitad bloqueada.** Lo construible
hoy es todo lo demás. No es un problema de prioridades mal puestas: es que la F0 puede tirar el
diseño de transporte entero, y construir el terminal antes de medirla es apostar.

→ **Consecuencia para el diseño:** la aplicación se estructura para que **el terminal encaje después
sin reescribir nada**. Por eso el transporte de rosbridge y el del agente son dos módulos separados
desde el primer día, y por eso `Transporte` no sabe nada de quién lo consume.

---

## 3 · Mapa de rutas

Next.js App Router. Rutas en español, como el resto del proyecto.

```
/                        → redirige según el rol (alumno → su robot · profesor → /flota)
/entrar                  → autenticación                        🔴 BLOQUEADA (ver §7)
/flota                   → el muro del profesor: 16 baldosas
/robot/[id]              → el espacio de trabajo del alumno
   ├── (índice)          → EL TERMINAL                          🔴 BLOQUEADO (mitad 2)
   ├── /telemetria       → lo que el robot está midiendo ahora
   ├── /conducir         → teleoperación                        ← la última, por decisión 17
   └── /diagnostico      → el panel hondo: ritmos, antigüedades, estado del enlace
```

**Por qué `/robot/[id]` y no `/robot?id=`:** el `id` gobierna **una conexión WebSocket**, y una ruta
por robot deja que el ciclo de vida de React la abra y la cierre sin ambigüedad. Con parámetro de
consulta, cambiar de robot no desmonta nada y la conexión vieja se queda viva — que es exactamente
el fallo que la capa de datos tuvo y que costó dos rondas de arreglo.

---

## 4 · Estructura de ficheros

```
frontend/src/
  app/
    layout.tsx                     tema claro/oscuro, tipografía, el <html>
    page.tsx                       redirección por rol
    flota/page.tsx                 el muro del profesor
    robot/[id]/
      layout.tsx                   🔑 ABRE la conexión de ESTE robot y la cierra al salir
      page.tsx                     el terminal            🔴 bloqueado
      telemetria/page.tsx
      conducir/page.tsx
      diagnostico/page.tsx

  lib/rosbridge/                   ✅ EXISTE — 97 pruebas, sin un import de React
    contrato · salud · protocolo · transporte · teleoperacion · index

  lib/flota/                       🆕 el modelo del profesor. Puro, sin React
    resumen.ts                     de qué se compone una baldosa y cómo se decide su color
    presupuesto.ts                 qué se puede suscribir con 16 robots y qué no (§6)

  lib/agente/                      🔴 el transporte del terminal. NO existe todavía
                                   Módulo aparte a propósito: otro puerto, otro protocolo,
                                   otra autenticación. No se mezcla con rosbridge.

  hooks/                           🆕 la capa fina que une el núcleo puro con React
    useTransporte.ts               da el Transporte del robot de la ruta actual
    useTopic.ts                    suscripción tipada, con baja automática al desmontar
    useSalud.ts                    evaluarSalud alimentado por el reloj de llegadas
    useTeleoperacion.ts

  componentes/
    flota/BaldosaRobot.tsx         una baldosa del muro
    robot/EstadoEnlace.tsx         SIN_CONEXION · EN_LINEA · SIN_DATOS · FRENANDO
    robot/Bateria.tsx              VOLTIOS, no percentage
    robot/EstadoMotores.tsx        con la ANTIGÜEDAD al lado de cada valor
    robot/VistaLidar.tsx           /scan en un canvas
    robot/BotonParada.tsx          el único control que no puede fallar en silencio
    ui/                            lo que ya hay: tarjetas, avisos, conmutador de tema
```

📌 **`lib/` es puro y se prueba en Node; `hooks/` y `componentes/` son la única parte que toca
React.** Es la misma frontera que hizo posible que la capa de datos moviera un robot desde una
prueba de Vitest, sin navegador.

---

## 5 · El modelo de conexión y de estado

**Sin Redux, sin Zustand, sin store global.** El estado que importa **no vive en la aplicación**:
vive en el robot y llega por WebSocket. Lo único que hay que gestionar es *qué conexión está viva*.

- **Un `Transporte` por robot**, creado en `robot/[id]/layout.tsx` y expuesto por un contexto de
  React. Al desmontar la ruta, `cerrar()`.
- **`useTopic('/odom')`** se suscribe al montar y **se da de baja al desmontar** — y esa baja llega
  al robot de verdad, con un `unsubscribe`, porque `/scan` es el **83 %** del tráfico y una
  suscripción olvidada cuesta ancho de banda para siempre.
- ✅ **Compatible con el `StrictMode` de React 19**, que monta dos veces en desarrollo:
  `conectar()` es **idempotente** y `cerrar()` seguido de `conectar()` funciona. Las dos propiedades
  están **medidas y protegidas por pruebas** — salieron de dos hallazgos críticos de la revisión.
- 🔴 **El oyente de `alCerrarse` NUNCA llama a `conectar()`.** Medido: reconectar de forma síncrona
  desde ese callback crea **4 sockets**. Reconectar es responsabilidad del transporte, con su espera
  creciente.

---

## 6 · La vista del profesor — y el presupuesto, que decide el diseño

Es el hueco número 1 de la revisión: *«profesor» aparece dos veces en 403 líneas del plan*. Y tiene
una restricción dura que **nadie había calculado**.

### El presupuesto, con los números medidos el 2026-08-04

| Suscripción | Por robot | × 16 |
|---|---|---|
| `/battery_state` + `/motor_status` | **0,48 kB/s** | **7,7 kB/s** ✅ |
| + `/odom` | 13,5 kB/s | 216 kB/s = **1,7 Mbit/s** ⚠️ |
| + `/scan` | 81 kB/s | **10,3 Mbit/s** 🔴 el WiFi entero del aula |

🔴 **Y `throttle_rate` NO sirve para arreglarlo.** Verificado en el fuente:
`subscribe.py:225` → `self.throttle_rate = min(f("throttle_rate"))`. **Gana el cliente más rápido,
para todos.** En cuanto un alumno esté suscrito a `/odom` sin límite en ese robot, el profesor
recibe a 16,5 Hz aunque haya pedido 1. El *throttle* sirve para bajar el coste **cuando eres el
único**, no para protegerte de los demás.

### El diseño que sale de ahí

**La baldosa del profesor se suscribe SOLO a `/battery_state` y `/motor_status`.** 7,7 kB/s para los
16, que es gratis. Y muestra:

- **Voltaje** (7,0 baja · 6,5 crítica), **nunca** `percentage` — que además es fracción 0-1
- **Estado de motores** con su **antigüedad al lado**: `-1.0` es «no se sabe», no «todo bien», y la
  temperatura puede tener 30 s de retraso
- **Estado del enlace**: si el WebSocket abre o no

### 🔴 Y lo que la vista del profesor NO puede hacer hoy, y hay que decirlo

**No puede saber si un robot está vivo.** Para eso haría falta el ritmo de `/odom`, y `/odom` cuesta
1,7 Mbit/s por 16. `/motor_status` llega a 1 Hz **republicado con el último valor conocido**, así que
llega igual con el RVR mudo — lo medí esta noche y por poco lo interpreto mal.

→ **Se cierra con una línea en el driver:** un `/latido` a 1 Hz con un contador monótono. Cuesta
~0,03 kB/s por robot (**0,5 kB/s los 16**) y da liveness de verdad. Ver §9.

Hasta que exista, **la baldosa dice «sin señal de vida» y no «averiado»** — con 16 robots cargando a
la vez, adivinar pinta la flota entera en rojo.

---

## 7 · El terminal del alumno — diseñado, bloqueado en implementación

Es **el producto**, y por eso se diseña aunque no se pueda construir.

```
┌─ /robot/07 ────────────────────────────────────────────────┐
│  editor Monaco          │  salida del programa (PTY)        │
│  practica_04.py         │  > mide el angulo y pulsa Enter   │
│                         │  _                     ← stdin    │
├─────────────────────────┴───────────────────────────────────┤
│  ▶ Ejecutar   ⏹ Parar   🔴 PARADA        enlace ● batería   │
└─────────────────────────────────────────────────────────────┘
```

**Lo que el diseño tiene que respetar, y cada punto es una medición:**

- **PTY, no tubería.** `04_giro_preciso.py` tiene **cuatro** `input()` y `99_test_ctrl_c.py` un
  quinto: el alumno mide con transportador y pulsa Enter. Sin stdin bidireccional, **dos prácticas
  de diez están muertas**. Y `print()` contra tubería es *block-buffered*: la salida aparecería a
  bloques minutos tarde.
- **El código corre EN el robot**, con `rclpy` nativo sobre `atriz.py`, no por rosbridge.
  `robot.color()` llama a `/get_rgbc_sensor_values`, que **no está en la lista blanca**: cualquier
  diseño que pase la lógica del alumno por rosbridge obliga a ensanchar lo que la Fase A cerró.
- **Un solo programa por robot.** `atriz.py` crea `Node('atriz_alumno')` con **nombre fijo**: dos a
  la vez son dos nodos homónimos en el mismo dominio.
- **La parada viaja por el mismo socket que la salida.** Si el alumno ve texto, la parada llegará.
- 🔴 **El alumno tiene MÁS autoridad que la web.** Con `rclpy` nativo alcanza `raw_motors`,
  `move_timed`, `move_to_pose` y `set_ir_mode('following')` — los seis caminos que **se saltan el
  `collision_monitor`**. La frase «`raw_motors` ya no es alcanzable, 0,00 cm verificado» **deja de
  ser cierta mientras haya una sesión en marcha**. Es el precio de esta arquitectura y va escrito.

**Bloqueado por:** el agente de sesión (F2) → que está bloqueado por la **F0**: si el AP del aula
aísla clientes, el transporte entero se replantea. **Esa medición necesita el aula.**

---

## 8 · Los estados de la interfaz, y lo que NO se promete

Esta es la parte donde este proyecto se ha equivocado más veces, así que va explícita.

| Estado | Cuándo | Color | Qué dice |
|---|---|---|---|
| `SIN_CONEXION` | el WebSocket no abre | gris | «no llego al robot» |
| `EN_LINEA` | `/odom` en los últimos 3 s | verde | — |
| `SIN_DATOS` | el enlace va y `/odom` calla > 3 s | **ámbar, NUNCA rojo** | **las tres causas, sin elegir** |
| `FRENANDO` | `/collision_monitor_state` actúa | azul | «va lento porque la seguridad frena, no está averiado» |

🔴 **`SIN_DATOS` no es avería, y el cliente no puede saber cuál de las tres es:** el robot está
**cargando** (RVR apagado, Pi viva — el estado **cotidiano**), el RVR se **durmió**, o hay una
**excepción en un manejador** del driver. Con 16 robots, adivinar saca la flota entera en rojo.

📝 **La única de las tres que se distingue es gratis:** si `/scan` llega y `/odom` no, es la
excepción en el manejador. ⚠️ Pero solo funciona **si alguien mantiene la suscripción a `/scan`**, y
`arrancarBarrido()` se da de baja tras la primera muestra — correcto, porque es el 83 % del tráfico.
**Es un acoplamiento, no un fallo**, y está documentado en `salud.ts`.

**Lo que la interfaz NO promete, y por qué:**

- **Nunca «color cambiado, confirmado».** Ningún servicio del robot confirma un efecto físico: los
  cuatro con respuesta vacía no dicen nada, y los cuatro con `bool success` solo dicen que la
  corrutina del SDK **no lanzó**. Medido: `undercarriage_white` devuelve `success=True` **sin
  encender el LED**.
- **Nunca «parada activa».** El driver **no publica su bandera de parada** — 7 publicadores y ninguno
  es de la parada. La interfaz muestra «parada enviada», que es lo que sabe.
- **Nunca una cifra de latencia.** El extremo a extremo navegador→motores **no está medido**.
- **Nunca «robot averiado»** por ausencia de datos. Ver arriba.

---

## 9 · 🔴 Lo que el ROBOT necesita para que esta interfaz sea honesta

Tres señales que el driver **no publica**, y sin las cuales la interfaz tiene que decir «no lo sé».
Las tres son pequeñas y aparecieron por separado; juntas son la lista de la compra:

| Señal | Para qué | Coste |
|---|---|---|
| **`/latido` a 1 Hz**, contador monótono | Liveness de verdad para el muro del profesor, sin pagar `/odom` | ~0,03 kB/s · **0,5 kB/s los 16** |
| **La bandera de parada** publicada | Que la interfaz pueda decir «parada ACTIVA» con un dato del robot, no con una suposición | latched, ~0 |
| **Un «estoy cargando»** (RVR apagado, Pi viva) | Que un robot cargando **no se pinte como roto**. Hoy es indistinguible de dormido y de excepción | ~0 |

Sin la primera, el muro del profesor no puede decir quién está vivo. Sin la segunda, el botón de
parada no puede confirmar. Sin la tercera, `SIN_DATOS` no se puede desambiguar nunca.

### ✅ Escritas el 2026-08-04, en la rama `feat/estado-robot` de `Atriz_rvr` — **NO VERIFICADAS**

Las tres van en **un solo topic**, `/estado_robot` a 1 Hz (`atriz_rvr_msgs/EstadoRobot`):

```
uint64  latido                  contador monotono. La señal de vida DEL NODO
bool    parada_emergencia       la bandera del driver, que hoy no sale
bool    rvr_responde            false = hace mas de silence_timeout que no llega muestra
float32 antiguedad_muestra_s    -1.0 = «no se sabe» (nunca «cero»)
uint32  reanudaciones_fallidas  0 = bien · 1-2 = pudo ser una siesta · >2 = el RVR no esta
```

🔴 **En rama aparte a propósito: no hay robot, y `ros2` queda intacta.** Tocar el driver a ciegas es
donde este proyecto se ha hecho daño — *«una excepción en un manejador mata `/odom` e `/imu` en
silencio»*. El riesgo real del parche **no es que `/estado_robot` no funcione: es que se lleve por
delante la telemetría**, y esa es la comprobación que manda al fusionarlo.

**Tres cosas que salieron al escribirlo y que la interfaz tiene que saber:**

1. 🔴 **`reanudaciones_fallidas` no podía apoyarse en `_t_ultima_muestra`**, que es lo que decía el
   encargo: ese campo lo reinician **también** `_conectar_rvr` y `_recuperar_streaming`, así que
   significa *«hace poco que pasó algo»*, no *«hace poco que llegó un dato»*. Apoyarse en él habría
   hecho que una reanudación con el RVR **apagado** pareciera un éxito — **el fallo del 2026-08-02
   reproducido dentro del campo escrito para detectarlo**. Se resolvió con un espejo que solo tocan
   los manejadores.
2. 🔴 **El latido va `TRANSIENT_LOCAL`, así que un suscriptor nuevo puede recibir el ÚLTIMO valor
   latcheado.** **La interfaz tiene que comparar DOS lecturas separadas en el tiempo**; una sola no
   dice nada. Y apunta en la misma dirección que lo ya medido: *«`TRANSIENT_LOCAL` en el publicador
   no garantiza que un suscriptor tardío reciba el último valor»* (2 de 3 no recibieron nada en
   10 s). **Lo que da la garantía es la republicación a 1 Hz, no el QoS.**
3. ⚠️ **Los umbrales `1-2` / `>2` NO están calibrados.** Nadie ha cronometrado cuántos intentos
   tarda una siesta real en recuperarse; la medida de la que salen (123 intentos con el robot
   apagado) solo fija el extremo. Van como **orientación**, no como criterio.

⚠️ Y el coste «~0,03 kB/s» es **aritmética, no una medida** — por rosbridge va en JSON, que abulta
más.

---

## 10 · Orden de construcción

Cada paso deja algo **usable**, y ninguno depende de la F0 salvo el último.

| # | Qué | Depende de |
|---|---|---|
| **1** | `hooks/` — `useTransporte`, `useTopic`, `useSalud` | nada. La capa de datos existe |
| **2** | `robot/[id]/diagnostico` — ritmos, antigüedades, estado del enlace | 1 |
| **3** | `robot/[id]/telemetria` — batería en voltios, motores con antigüedad, LEDs | 1 |
| **4** | `flota/` — el muro, solo con topics baratos | 1 · mejora mucho con `/latido` |
| **5** | `robot/[id]/conducir` — teleoperación y **el botón de parada** | 1 |
| **6** | El terminal | 🔴 **el agente** → 🔴 **la F0** |

📌 **El diagnóstico va primero a propósito.** Es la pantalla que hace visible lo que la capa de datos
ya sabe, y la que dirá si algo no encaja **antes** de que haya nada bonito encima. En este proyecto
la pantalla que mide vale más que la que decora.

📌 **La autenticación no está en la lista, y no es olvido:** rosbridge 2.7.0 **no tiene**, y el sitio
donde se pone es el agente de sesión (Fase B). Mientras tanto **cualquiera en el aula puede
teleoperar cualquier robot**, y eso ya está escrito como pendiente. Poner un login en la web que no
proteja nada sería exactamente el estado engañoso que la web anterior tenía.
