# Especificación — El cliente de rosbridge de la web

> **Qué es.** La capa de datos entre el navegador y un robot. Es la primera pieza de la Fase 5 y la
> única que **ninguna medición pendiente puede invalidar**: diga lo que diga el AP del aula y exista
> o no el agente de sesión, el navegador tendrá que suscribirse a los topics y publicar en
> `/cmd_vel_raw` y `/emergency_stop`.
>
> **Dónde vive.** Repositorio `Bura-hub/atriz-lab` (decisión del usuario, 2026-08-03: pasa a ser
> **el** repositorio de la web y a **privado**). Pila ya presente: Next.js 15 · React 19 ·
> TypeScript · Tailwind 3.4.
>
> **Contexto:** [`2026-08-03-plataforma-web.md`](2026-08-03-plataforma-web.md) y su
> [revisión](2026-08-03-plataforma-web-revision.md).

---

## 1. Alcance

**Entra:** conexión y reconexión, suscripciones tipadas, publicación, llamadas a servicio, la acción
de navegación, el bucle de teleoperación, la parada de emergencia, y el estado de salud del robot.

**No entra, y se dice para que nadie lo dé por hecho:** interfaz de usuario, autenticación,
editor de código, ejecución de código del alumno, vista del profesor, mapa. Todo eso se apoya en
esta capa y ninguna de esas piezas está decidida todavía.

**Criterio de terminado:** un robot real se teleopera desde el navegador y el desplazamiento
**medido con cinta** coincide con el del mismo movimiento por SSH; y `probar_lista_blanca.py` sigue
dando exactamente lo mismo que antes.

---

## 2. El contrato con el robot

No se inventa: es `atriz_rvr_bringup/launch/robot.launch.py:320-360`, y es lo único que el robot
acepta. Se transcribe a `contrato.ts` **y una prueba lo compara con el fichero del robot**, porque
una lista blanca duplicada a mano es una deriva documental esperando a ocurrir.

| | |
|---|---|
| **Lectura** (12) | `/odom` `/imu` `/scan` `/battery_state` `/motor_status` `/encoders` `/color` `/map` `/tf` `/tf_static` `/collision_monitor_state` `/amcl_pose` |
| **Escritura** (3) | `/cmd_vel_raw` · `/emergency_stop` · `/initialpose` |
| **Servicios** (8) | `/start_scan` `/stop_scan` `/release_emergency_stop` `/set_pos_and_yaw` `/set_led_rgb` `/set_multiple_leds` `/set_leds` `/trigger_led_event` |
| **Acción** (1) | `/navigate_to_pose` |
| **Parámetros** | **ninguno** — `params_glob` es `'[]'` |

🔴 **`/cmd_vel` NO está y no debe estar.** Es la **salida** del `collision_monitor`: publicar ahí
funciona y salta la seguridad en silencio.

⚠️ **Cuatro entradas están muertas con el arranque por defecto** (`/map`, `/amcl_pose`,
`/initialpose`, `/navigate_to_pose`): las produce Nav2 o SLAM, y `atriz-nav.service` no está
habilitado. **El cliente degrada sin ellas; no las espera.**

---

## 3. Los módulos

Núcleo **sin un solo import de React**, para que se pruebe en Node sin navegador y sin robot.

```
src/lib/rosbridge/
  transporte.ts      WebSocket, reconexión, cola de salida, reloj de llegadas
  protocolo.ts       las ops de rosbridge y el timeout propio de cada llamada
  contrato.ts        la lista blanca y los tipos de los 12 topics  (funciones puras)
  salud.ts           el estado del robot a partir de las antigüedades  (funciones puras)
  teleoperacion.ts   el bucle de 10 Hz y la parada
src/hooks/           useRobot, useTopic — capa fina
```

### 3.1 `transporte.ts`

Un WebSocket por robot, a `rvr-NN.local:9090`, con la IP como override. **Al robot lo identifica la
conexión**: no hay namespace, así que el mismo código sirve para los 16.

- **Reconexión con espera creciente y tope: 1 s, duplicando, hasta 30 s**, y con ruido aleatorio de
  ±20 % para que 16 navegadores no reintenten a la vez. El driver ya tiene el antipatrón
  documentado: 123 reintentos, uno cada 4 s, **sin** espera creciente, y 8 «streaming reanudado» en
  30 s con el robot apagado. No se repite en el cliente.
- **Al reconectar se resuscribe a todo**, y no se confía en el primer valor de los latched
  (`/battery_state`, `/motor_status`, `/map`): rosbridge infiere el QoS mirando los publicadores en
  el instante de suscribirse y **no se reajusta**.
- **Nunca libera la parada de emergencia al reconectar.** Liberarla es siempre un acto humano
  deliberado.
- Registra la **marca de tiempo de la última llegada por topic**. Es lo que alimenta `salud.ts`.

### 3.2 `protocolo.ts`

Las ops que se usan: `subscribe`, `unsubscribe`, `advertise`, `unadvertise`, `publish`,
`call_service`, `send_action_goal`, `cancel_action_goal`. Entrantes: `publish`, `service_response`,
`action_result`, `action_feedback`, `status`, `fragment`.

🔴 **Toda llamada lleva timeout propio.** rosbridge **deniega en silencio** —`warn` y `return`, sin
respuesta al cliente—, así que sin timeout una llamada denegada se manifiesta como «la web no
responde». Y el cliente **no puede distinguir «denegado» de «robot caído»**: eso se resuelve más
tarde, en el agente de sesión, que lleva su copia de los globs y contesta.

⚠️ **NO VERIFICADO — primera medición de la sesión:** qué campos de QoS acepta rosbridge 2.7.0 en
`advertise` y en `subscribe`, y si `throttle_rate`, `queue_length` y `fragment_size` funcionan como
se documentan. **El fuente de rosbridge no está en ninguno de los tres repositorios**: todo lo que
el proyecto cree saber de su protocolo es de segunda mano. Hasta medirlo, el cliente **no asume
control de QoS**: se apoya en que rosbridge se suscribe con `qos_profile_sensor_data` (BEST_EFFORT),
que empareja con publicadores BEST_EFFORT y RELIABLE por igual.

### 3.3 `contrato.ts` — funciones puras

Los tipos de los 12 topics, los 8 servicios y la acción, y **las tres listas blancas transcritas**.
Una llamada a algo fuera de la lista **falla en el cliente, con un mensaje que lo dice**, en vez de
irse al silencio de rosbridge.

Semántica que va aquí porque ya ha provocado falsas alarmas:

- **`battery_state.percentage` es una FRACCIÓN 0-1.** `0.34` son 34 %. Y la señal para decidir carga
  es **`voltage`** (umbrales del firmware: baja 7,0 V, crítica 6,5 V, histéresis 0,2). El porcentaje
  decía 100 % con 8,29 V.
- **`motor_status.antiguedad_*_s == -1.0` significa «nunca se ha sabido nada»**, no «todo bien». Son
  **tres** estados por campo. Pintarlo verde es una falsa tranquilidad.
- **La temperatura puede tener 30 s de retraso** — solo cambia cuando corre el sondeo. Una
  temperatura plana puede ser el mismo dato repetido: se pinta **con su antigüedad al lado**.
- **`/ambient_light` no está en la lista blanca y no se usa.** El sensor mira hacia arriba y el piso
  blanco del LIDAR le refleja los LEDs del propio robot.

### 3.4 `salud.ts` — funciones puras, y la parte más delicada

**La salud se mide por RITMO y por antigüedad, nunca por que el topic exista.** `ros2 topic list`
conserva topics de nodos muertos, y el log del driver dice «streaming reanudado» con el robot
apagado.

| Estado | Cómo se decide | Cómo se pinta |
|---|---|---|
| `SIN_CONEXION` | el WebSocket no está abierto | gris |
| `EN_LINEA` | ha llegado **al menos un `/odom` en los últimos 3 s** | verde |
| `SIN_DATOS` | el WebSocket va y `/odom` lleva **> 3 s** sin llegar | **ámbar, NO rojo** |
| `FRENANDO` | `/collision_monitor_state` dice que la seguridad actúa | azul, informativo |

**Por qué «llegadas en los últimos 3 s» y no un umbral en Hz:** los 3 s son **el mismo umbral que
usa el detector de silencio del driver**, así que el cliente y el robot coinciden en cuándo algo va
mal. Y evita la trampa que este proyecto ya pisó: una comprobación de «> 10 Hz» **pasaba** midiendo
11,3 Hz sobre un robot que iba a 16,5 — un umbral laxo convierte una medida mala en un aprobado. El
ritmo se muestra como número informativo; **no decide el estado**.

🔴 **`SIN_DATOS` NO es una avería, y el cliente no puede saber cuál de estas tres cosas es:**

1. el robot está **cargando** — RVR apagado y Pi viva, que es un estado **cotidiano** con 16 robots;
2. el RVR se **durmió**;
3. hay una **excepción dentro de un manejador** del driver, que mata `/odom` e `/imu` en silencio
   con los topics existiendo.

**No hay ninguna señal hoy que los separe** — hace falta que el driver la publique (hueco 3 de la
revisión). Hasta entonces el cliente **muestra los tres como una posibilidad y no elige**. Un panel
que pinte rojo el estado 1 saca la flota entera en rojo cada vez que los robots se cargan.

📝 Pista que sí sirve y es gratis: **si `/scan` llega y `/odom` no, y no hay aviso de silencio, es
una excepción en un manejador.** Es la única de las tres que se distingue, y se distingue así.

### 3.5 `teleoperacion.ts`

- **Republica el `Twist` a 10 Hz mientras dure la orden.** El watchdog del driver corta a los 0,3 s;
  medido, para en 527 ms / 7,9 cm. Un `sleep` entre publicaciones deja el robot parado casi todo el
  tiempo.
- **Antes de habilitar la teleoperación: `/start_scan`, y esperar un `/scan` de verdad** — no el
  código de retorno del servicio. Sin `/scan` el `collision_monitor` bloquea el movimiento (0,0 cm
  contra 9,9 del control) y **el robot parece averiado**. El estado del barrido es visible en la UI.
- **La parada** se publica en `/emergency_stop` (`std_msgs/Empty`) y **solo ahí**. Los otros dos
  nombres que el driver escucha están fuera de `topics_pub_glob`, aunque el README del robot diga lo
  contrario.
- **Liberar la parada** es un botón aparte con confirmación, nunca automático. Y **no se ofrece si
  hay un objetivo de Nav2 activo**: liberar solo baja una bandera, y sin `cancelar_nav2` vivo el
  robot reanuda la navegación solo (34,7 cm medidos contra 0,0 con el arreglo).

---

## 4. Manejo de errores

El principio del proyecto: **comprobar el efecto, no el código de salida.** Van seis casos
documentados de «informa de éxito sin haber hecho nada».

| Situación | Qué hace el cliente |
|---|---|
| Llamada sin respuesta | vence su timeout y lo dice: «sin respuesta en N s — puede estar denegado o el robot caído». **No inventa cuál** |
| `/set_leds` | su `.srv` tiene la **respuesta vacía**: no hay forma de confirmar el efecto. La UI **no promete confirmación** |
| Topic sin datos | ver `salud.ts`: ámbar y las tres posibilidades, nunca «averiado» |
| WebSocket caído | espera creciente con tope, y **la teleoperación se corta sola** — el watchdog ya lo hace, pero el cliente no debe fingir que sigue mandando |
| Robot fuera de la lista blanca | falla **en el cliente**, con el nombre del topic y la lista donde debería estar |

---

## 5. Verificación

Ninguna de estas se da por buena con un `desenlace=0`.

1. **Funciones puras** (`contrato.ts`, `salud.ts`): tests en Node, sin navegador ni robot. Incluyen
   los casos que ya mordieron: `percentage` 0-1, `-1.0` como tercer estado, y **la banda intermedia**
   de la máquina de salud — no solo los extremos, que es justo lo que dejó pasar un bug en el
   seguidor de línea.
2. **`probar_lista_blanca.py` da exactamente lo mismo** antes y después. Si el cliente obliga a
   abrir un glob, el diseño se torció.
3. 🔴 **Con cinta métrica:** teleoperar 3 s a 0,20 m/s desde el navegador contra los ~60 cm del mismo
   movimiento por SSH. **Es la única prueba de que el alumno puede mover el robot.**
4. **La parada, publicando de verdad y mirando el log del driver.** El nombre y el QoS solo se
   comprueban así: leer el código da el nombre pero no el namespace resuelto ni el QoS.
5. **kB/s reales medidos en el navegador**, contra los 80,7 kB/s de referencia. `/scan` es el 83 %.
   Nada sobre CBOR se cita hasta medirlo: el plan lo marca **teórico**.
6. **Un robot cargando no se pinta como roto.** Se comprueba apagando el RVR con la Pi encendida,
   que es el estado que nadie había probado hasta el 2026-08-02.

---

## 6. Lo que esta especificación deja abierto

- **El QoS del protocolo de rosbridge** — medición 1, arriba. Puede cambiar `protocolo.ts`.
- **Cómo distinguir «cargando» de «mudo»** — necesita una señal del driver que hoy no existe.
- **`compression: "cbor"`** — no se implementa hasta medir si el ahorro es real.
- **Autenticación** — no existe en rosbridge 2.7.0. Este cliente habla con un puerto abierto, y eso
  es correcto **solo mientras rosbridge siga en `0.0.0.0`**. El día que se ate a `127.0.0.1`, el
  cliente apunta al agente y **el protocolo no cambia**: por eso el transporte está aislado.
