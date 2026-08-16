> # 🔴🔴 SUPERADO EL 2026-08-15 — LA FASE B **NO** LLEVA PROXY
>
> Este plan se ejecutó en otra forma y **el proxy no se construyó**. Al leer el fuente de
> rosbridge en la Pi apareció que `RosbridgeWebSocket` se importa **por nombre**
> (`rosbridge_websocket.py:54` y `:221`), así que basta con parchear sus métodos y ejecutar el
> nodo original. Lo que hoy corre en rvr-01 es
> `Atriz_rvr/atriz_rvr_bringup/scripts/atriz_rosbridge.py`, ~250 líneas.
>
> | | proxy (este plan) | lo que se hizo |
> |---|---|---|
> | ruta de datos | 🔴 un salto de Python a **80,7 kB/s por robot** | **cero** |
> | puerto / unidad | uno nuevo de cada | ninguno |
> | `address: 127.0.0.1` | imprescindible | innecesario |
> | TLS | había que implementarlo | `certfile`/`keyfile`, ya soportados |
>
> 🔴 Y el proxy **contradecía en silencio la Decisión 2 de `ARQUITECTURA.md`**: prometía que los
> datos siguen yendo robot → navegador directos, y con un relevo eso dejaba de ser cierto dentro
> de la Pi.
>
> **Se conserva entero** porque su análisis sigue valiendo —el testigo en el subprotocolo, la Pi
> sin reloj, qué se rompe al atar rosbridge a `127.0.0.1`, TLS— y porque enseña que un diseño
> razonable puede caer entero al **leer el fuente del componente** en vez de razonar sobre él.
>
> ⚠️ **`scripts/atriz_proxy.py` es código MUERTO.** No lo instales. Ver la evidencia **124**.

# Fase B · el proxy autenticador — diseño y código

**Fecha:** 2026-08-10 · **Escrito desde:** el PC · 🔴 **NADA DE ESTO ESTÁ EJECUTADO**

> Este documento y el código que lo acompaña (`scripts/atriz_proxy.py`) se han escrito **sin poder
> instalarlos ni medirlos**. En este proyecto eso no es un cierre: es un plan con código. Cada
> afirmación sobre comportamiento lleva su marca, y el apartado 7 dice exactamente qué hay que
> medir para que deje de ser una promesa.

---

## 1 · Qué cierra, y qué no

`SEGURIDAD_ROSBRIDGE.md` ya fija la forma:

```
navegador ──wss://rvr-NN.local:9443──► proxy (en la Pi) ──ws://127.0.0.1:9090──► rosbridge
                  con testigo            valida y filtra
```

| Requisito | Fase A (hecho) | Fase B |
|---|---|---|
| 3 · cerrar `raw_motors` y compañía | ✅ | ✅ |
| 2 · que nadie sin permiso mueva un robot | ❌ | ✅ |
| 1 · que un alumno no mueva el robot de otro | ❌ | ✅ |
| 4 · que no se pueda espiar la telemetría | ❌ | ✅ con TLS |

**Por qué el proxy va en cada robot y no en el centro:** un proxy central daría la misma identidad,
pero los **10,3 Mbit/s** medidos de los 16 robots atravesarían el servidor — justo lo que la
Decisión 2 evitó a propósito. Con el proxy en cada Pi, los datos siguen yendo **robot → navegador
directos**.

---

## 2 · 🔴 «Token en el WebSocket quedó descartado por imposible» — hay que precisar esa frase

Está en `CLAUDE.md` y, tal como suena, **es falsa y bloquearía este diseño**. Lo que es cierto es
más estrecho:

- ✅ **Cierto: `rosbridge` no puede consumir un testigo.** No tiene autenticación —`rosauth` no es
  dependencia, no existe el parámetro `authenticate`, y `check_origin()` devuelve `True`
  incondicionalmente—. No hay dónde metérselo.
- ✅ **Cierto: el navegador NO puede poner cabeceras en un WebSocket.** No hay API. Así que
  `Authorization: Bearer …` está descartado, y ahí es donde nace la frase.
- 🔴 **Falso: que no haya forma de mandarlo.** Hay **dos**, y las dos son estándar:

| vía | cómo | problema |
|---|---|---|
| **subprotocolo** | `new WebSocket(url, ['atriz.v1', 'atriz.token.' + jwt])` | el testigo va en una cabecera de *handshake*; el servidor **debe** devolver uno de los ofrecidos |
| cadena de consulta | `wss://…:9443/?t=<jwt>` | acaba en registros de acceso y en el historial del navegador |

→ ✅ **Se elige el SUBPROTOCOLO.** No aparece en la URL, así que no se filtra al historial, ni a un
`Referer`, ni a un `journal` que alguien pegue en un informe. Es el mecanismo que usan las APIs de
Kubernetes y de los servidores de notebooks para exactamente este problema.

⚠️ **Y trae una trampa propia, que es de las que este proyecto paga:** si el servidor **no
devuelve** uno de los subprotocolos ofrecidos, el navegador **cierra la conexión él mismo**, con
código 1006 y sin motivo. Es la firma de «no llego» otra vez. El proxy tiene que responder
`atriz.v1` siempre, y hay una prueba para eso.

---

## 3 · Quién firma el testigo — y ya no es FastAPI

`SEGURIDAD_ROSBRIDGE.md` dice «el JWT que emite FastAPI». **Eso está rancio**: la web se rehízo y
hoy es Next.js con sesión propia —`scrypt` para la contraseña, cookie `httpOnly` firmada con
HMAC—. FastAPI ya no está en el camino.

→ **Firma el servidor de Next**, que es quien ya sabe quién es cada persona.

### 🔴 Y la clave NO se comparte: firma asimétrica

La tentación es HMAC con un secreto compartido, porque no añade dependencias. **No.** Con 16 robots
en un aula, ese secreto vive en 16 tarjetas microSD a las que cualquiera tiene acceso físico, y
**quien saque una puede emitir testigos para las otras quince**. La superficie es el laboratorio
entero.

→ **Ed25519.** El servidor guarda la clave privada; cada robot solo lleva la **pública**, que no
sirve para firmar nada. Una microSD robada no permite emitir testigos.

⚠️ **Coste, y hay que verificarlo:** el proxy necesita `python3-cryptography`. Ubuntu lo empaqueta
y es probable que ya esté por otras dependencias, **pero no está comprobado en la Pi**. Si no
estuviera, es un `apt install` en `provision.sh`, no un cambio de diseño.

### Qué dice el testigo

```json
{ "sub": "ana", "rob": 7, "exp": 1754870000, "iat": 1754860000 }
```

- **`rob`** es el requisito 1 entero: el proxy compara con **su** número de robot y no necesita
  saber nada de usuarios ni de reservas.
- **`exp`** dura lo que una clase. Un testigo caducado no abre.

---

## 4 · 🔴🔴 LA TRAMPA QUE UN DISEÑO GENÉRICO SE COMERÍA: **la Pi no tiene reloj**

Está medido en este proyecto (evidencia 85): **la Pi arranca con el reloj restaurado a la última
marca guardada** —hasta **19,5 h en el pasado**— y NTP lo salta hacia delante ~18 s después.

Un JWT se valida contra el reloj. Con el reloj 19 h atrasado:

```
exp del testigo   2026-08-10 09:00
reloj de la Pi    2026-08-09 13:30      <- 19,5 h antes
resultado         el testigo parece EMITIDO EN EL FUTURO  ->  rechazado
```

**Todos los alumnos rechazados, en los primeros segundos tras encender, y sin ninguna pista.** Y al
revés es peor: un reloj adelantado aceptaría testigos caducados.

→ ✅ **El proxy NO valida tiempos hasta que el reloj está sincronizado.** Pregunta a
`systemd-timesyncd` (`NTPSynchronized` por D-Bus, o el fichero
`/run/systemd/timesync/synchronized`) y, mientras no lo esté:

- **rechaza toda conexión**, con un motivo explícito — nunca acepta «por si acaso»;
- lo dice en el cierre: `1013 · el robot aún no tiene la hora, espera unos segundos`.

**Cerrar es más seguro que abrir**, y sobre todo **es explicable**: un alumno que lee «espera unos
segundos» espera; uno que ve «no autorizado» va a buscar a un profesor.

⚠️ `After=time-sync.target` en la unidad **ayuda pero no basta**: garantiza el orden de arranque,
no que NTP haya contestado. La comprobación en vivo es la que cierra el caso.

---

## 5 · Qué se rompe al atar rosbridge a `127.0.0.1`

Es la otra mitad, y hay que decir a quién deja fuera:

| Quién | Hoy | Después |
|---|---|---|
| el navegador del alumno | `ws://rvr-NN.local:9090` | `wss://rvr-NN.local:9443` con testigo |
| **las herramientas de banco** del proyecto | `ws://rvr-NN.local:9090` | 🔴 **dejan de funcionar** |
| `probar_conexion_web.html`, `medir_aula.html` | igual | 🔴 igual |
| algo corriendo **en** la Pi | `localhost:9090` | ✅ sigue igual |

🔴 **Ese segundo caso no es menor:** buena parte de la evidencia de este proyecto se ha tomado con
clientes WebSocket contra el puerto 9090 desde fuera. Al cerrarlo, **el banco necesita un testigo o
un túnel SSH**. Hay que decidirlo antes de aplicar la Fase B, no después.

→ Propuesta: el proxy acepta además un **testigo de banco** de larga duración, guardado en el
robot con permisos `600`, que `verificar_robot.sh` y las herramientas puedan leer **desde la
propia Pi**. Desde fuera se usa túnel SSH. ⏳ **Sin decidir — es del usuario.**

---

## 6 · TLS: sigue sin decidirse, y el diseño no lo fuerza

`SEGURIDAD_ROSBRIDGE.md` lo pospuso con el argumento bueno: lo **autofirmado obliga al alumno a
aceptar una excepción en cada uno de los 16 robots**, y eso enseña a dar a «aceptar siempre», que
es peor que no tener TLS.

→ El proxy se escribe **agnóstico**: habla `ws://` a secas si no se le dan certificados, y `wss://`
si se le dan. Así la decisión de TLS no bloquea el resto de la Fase B, y el requisito 4 queda
explícitamente **abierto** hasta que se tome.

⚠️ **Mientras no haya TLS, el testigo viaja en claro.** Quien esté en la WiFi del aula puede
copiarlo y usarlo hasta que caduque. Eso **hay que decirlo**: la Fase B sin TLS cierra los
requisitos 1 y 2 contra el error honesto y contra el curioso, **no contra alguien que esté
escuchando el aire**.

---

## 7 · 🔴 Cómo se comprueba que esto funciona — y ninguna está hecha

Nada de lo de arriba está medido. Esto es lo que lo convertiría en un hecho, **con su control en
cada punto**, que es lo que este proyecto exige:

| # | Qué | ✅ pasa si | 🔴 se refuta si |
|---|---|---|---|
| 1 | rosbridge deja de ser alcanzable | `ws://rvr-01.local:9090` **se cuelga o rechaza** desde el PC | abre — el `address` no se aplicó |
| 2 | el proxy deja pasar con testigo bueno | `/odom` llega por el 9443, y `topic hz` da ~16,5 | no llega nada |
| 3 | **sin testigo NO pasa** | cierre con motivo, **0 mensajes** | pasa algo: la comprobación es decorativa |
| 4 | **testigo de OTRO robot no pasa** | el proxy compara `rob` y cierra | pasa — el requisito 1 no está |
| 5 | testigo caducado no pasa | cierre con motivo | pasa |
| 6 | **firma manipulada no pasa** | cierre | pasa — se está decodificando sin verificar, que es el fallo clásico |
| 7 | **reloj sin sincronizar** | cierra con `1013` y su texto | acepta o rechaza en silencio |
| 8 | el subprotocolo se devuelve | el navegador **abre** | 1006 sin motivo, la firma de «no llego» |
| 9 | coste | ancho de banda y CPU comparados **con y sin** proxy | — |

🔴 **La 3, la 4 y la 6 son las que importan**, porque son las **negativas**. Un proxy que deja pasar
todo pasa las pruebas 1, 2, 8 y 9 sin problemas. Este proyecto ya tiene ocho falsos positivos
documentados en su propio verificador: una comprobación que solo mira el camino bueno no comprueba
nada.

---

## 8 · Lo que este documento NO resuelve

- ⏳ **Cómo llega el testigo al navegador.** Hoy la sesión de Next es una cookie `httpOnly`, que el
  JavaScript **no puede leer** — a propósito. Hará falta un `GET /api/sesion/testigo?robot=NN` que
  lo emita para el robot pedido. Eso es de la web y no está escrito.
- ⏳ **Qué pasa con una pestaña abierta cuando el testigo caduca.** El proxy valida al conectar;
  revalidar en vivo obligaría a cerrar sockets a mitad de una práctica. Sin decidir.
- ⏳ **El testigo de banco** (apartado 5).
- ⏳ **TLS** (apartado 6).
- ⏳ **Y la pregunta de fondo:** si la Fase B llega antes o después que el aula. Medir el AP
  (`medir_aula.html`) puede cambiar el transporte entero, y entonces parte de esto se reescribe.
