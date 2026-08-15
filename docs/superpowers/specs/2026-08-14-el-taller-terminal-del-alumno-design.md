# El Taller — el terminal del alumno

**Fecha:** 2026-08-14 · **Escrito desde:** el PC · **Estado:** construido, y con la
mitad del robot **sin ejecutar**.

> 🔴 Este documento existe porque el diseño no puede vivir solo en un hilo de
> Claude. Es la regla del proyecto: *«si algo importa y solo vive en un hilo, en
> `memory/` o en un transcripto, no existe»*.

---

## 1 · Qué se construyó, y qué problema cerraba

`atriz-lab` tenía doce rutas verificadas contra hardware **y le faltaba el
producto**: la pantalla donde un alumno escribe y ejecuta su código. Hasta hoy lo
hacía por SSH (`python3 mi_script.py` en el robot), y la pestaña existía desde el
2026-08-04 como **chasis vacío a propósito** — decía «no construido», sin editor
y sin salida simulada.

Su criterio de revisión era una sola pregunta: *¿alguien podría creer que esto ya
funciona?* Al construirlo **el criterio no se relaja, se invierte**: ahora es
*¿alguien podría creer que hace algo que no hace?*

---

## 2 · La cadena de bloqueo, y por qué ya no bloquea

La pantalla la pintaba entera y en orden, con tres eslabones:

| eslabón | estado |
|---|---|
| **F0 · ¿el AP del aula aísla clientes?** | ✅ Descartado como riesgo el 2026-08-10 (SSH desde el laboratorio) y reforzado el 2026-08-12: `05-atriz-lab.network` casó a la primera |
| **Agente de sesión en el robot** | ✅ Escrito el 2026-08-14. Es la mitad nueva |
| **El terminal** | ✅ Esto |

📌 **Lo que queda ya no es un eslabón: es una medida.** El PTY del agente no ha
tocado un robot.

---

## 3 · Las decisiones, y quién las tomó

Ocho decisiones del usuario, tomadas antes de escribir una línea:

| | |
|---|---|
| **Alcance** | Las dos mitades: agente Python + terminal web + doble para probar sin robot |
| **Qué ejecuta** | Las prácticas del robot **y** el guion propio del alumno |
| **Autenticación** | Testigo **Ed25519** firmado por Next, verificado por el agente. Sin sesión no abre |
| **Concurrencia** | **Una ejecución por robot**, y el segundo ve quién la tiene |
| **Usuario** | Como `sphero`, y se quita el PAT de GitHub del robot |
| **Persistencia** | El guion vive en el servidor de Next; el robot recibe copia efímera en tmpfs |
| **TLS** | No por ahora (`ws://`), con el riesgo escrito |
| **Límites** | Tope de tiempo y de salida **ahora**; cgroups después |

Y dos del PC, con su argumento:

- **El editor es un `<textarea>`.** `atriz-lab` tiene la regla de **cero
  dependencias nuevas** —cinco en producción— y las prácticas son de ~30 líneas.
  Monaco son ~5 MB para poner colores.
- **El agente NO sustituye a rosbridge.** El plan de 2026-08-03 hacía que el
  agente fuera el único puerto, con rosbridge atado a `127.0.0.1`. **Aquí no**:
  eso rompe `probar_conexion_web.html` y `medir_aula.html` —las herramientas de
  banco del propio proyecto— y arrastra la Fase B entera, que tiene cuatro
  casillas sin decidir. El agente escucha en 9443 y **solo ejecuta**.
  ⚠️ El precio, escrito en la pantalla: **son dos enlaces**, y se puede ver la
  salida con la parada muerta.

---

## 4 · El protocolo

WebSocket en `ws://rvr-NN.local:9443`, JSON en las dos direcciones. El testigo
viaja en el **subprotocolo** (`atriz.token.<jwt>`; el agente responde siempre
`atriz.v1`, **incluso al rechazar** — si no devolviera ninguno, el navegador
cerraría con 1006 y sin motivo).

**Navegador → agente:** `atriz_adjuntar` · `atriz_listar` · `atriz_leer` ·
`atriz_exec` · `atriz_stdin` · `atriz_signal` · `atriz_parar` · `atriz_tamano`.

**Agente → navegador:** `atriz_bienvenida` · `atriz_estado` · `atriz_salida` ·
`atriz_recorte` · `atriz_fin` · `atriz_rechazo` · `atriz_listado` ·
`atriz_fichero` · `atriz_aviso`.

**Cierres:** los de `atriz_testigo.py` (`1013` reloj · `4401` sin testigo ·
`4403` testigo malo · `4404` otro robot), y **cada uno con su motivo en texto**.

### 🔴 `atriz_exec` lleva SIEMPRE el código, nunca «ejecuta el fichero N»

Abrir una práctica es leerla al editor y ejecutar lo que hay en el editor. Tres
consecuencias, y las tres importan:

1. **Un solo camino de ejecución** que probar, no dos.
2. El alumno puede **modificar una práctica y correrla**, que es como se aprende.
3. La pantalla puede afirmar **sin adivinar** que lo que corre es lo que se ve —
   el agente devuelve la huella de lo que lanzó, y si el texto cambia después, se
   dice.

---

## 5 · Las piezas

| fichero | qué | probado |
|---|---|---|
| `atriz-lab/frontend/src/lib/sesion/testigo_robot.ts` | Firma Ed25519 con `node:crypto` | ✅ 14 pruebas |
| `atriz-lab/frontend/src/app/api/sesion/testigo/route.ts` | `GET ?robot=NN`, exige sesión | ✅ contra el servidor vivo |
| `atriz-lab/frontend/src/lib/taller/{protocolo,sesion_taller,salida}.ts` | Puro: protocolo, máquina de estados, búfer | ✅ 48 pruebas |
| `atriz-lab/frontend/src/componentes/robot/useAgente.ts` | El segundo socket | ✅ contra el agente REAL de rvr-01 (2026-08-15) |
| `atriz-lab/frontend/src/componentes/robot/PanelTerminal.tsx` | La pantalla | ✅ 42 guardas **contra el robot real**, y las 16 casillas de VALIDAR §4 |
| `atriz-lab/herramientas/agente_de_mentira.mjs` | El doble | ✅ verifica Ed25519 de verdad |
| `Atriz_rvr/scripts/agente/agente_nucleo.py` | Lo que **decide** | ✅ **36 pruebas** (31 + 5 de los fallos de la 117 y la 4-10) |
| `Atriz_rvr/scripts/agente/agente_pty.py` | `pty.fork`, señales al grupo | ✅ **17/17 en la Pi** (13 + 4 de la 117). ⚠️ Se saltan en Windows, y eso **no es que pasen** |
| `Atriz_rvr/scripts/agente/agente_sesion.py` | tornado, el pegamento | ✅ **en producción desde el 2026-08-15**, auditado (ev. 117) con 5 fallos cazados, más 2 más el mismo día (`soy_el_dueno` difundido, y el 500 sin subprotocolo) |
| `Atriz_rvr/scripts/agente/atriz-agente.{service,sh}` | La unidad y su envoltorio | ✅ instalada y **habilitada por `fase_7`**; sobrevivió a un arranque en frío (cambio de batería) |

---

## 6 · Lo que se verificó de verdad

### 🔴 El cruce de los dos lenguajes, que nadie había probado nunca

`atriz_testigo.py` firma y verifica con `cryptography`; `testigo_robot.test.ts`
firma y verifica con `node:crypto`. **Las dos baterías pasarían con el contrato
roto**: basta con que cada lado sea coherente consigo mismo, y el fallo
aparecería en la Pi la primera vez que un alumno pulsara Ejecutar.

Cruzado en dos niveles:

- Un **testigo de ejemplo versionado** (`atriz-lab/herramientas/testigo_ejemplo.json`),
  emitido a mano según el estándar y verificado por el Python del robot, con el
  reloj congelado para que no caduque solo una tarde cualquiera.
- Y **contra el servidor vivo**:

```
entrar 200 · GET testigo?robot=7 200 · sin sesión 401 · robot=99 400 · por IP 400

atriz_testigo.verificar(ese testigo, 7) -> ok=True  sujeto='bura_hub'
atriz_testigo.verificar(ese testigo, 3) -> 4404 «es para el robot 7, y este es el 3»
```

**La trampa que esto caza:** `exp` e `iat` van en **segundos** —lo impone el
verificador, que los compara contra `time.time()`— mientras el testigo de sesión
usa milisegundos. Mutado a milisegundos, caen dos pruebas.

### El núcleo del agente, mutado en tres direcciones

Empezar la parada por `SIGKILL`, dejar pasar la ranura ocupada, y no validar
nombres: **caen las tres**.

---

## 7 · 🔴 Lo que NO está verificado

**El PTY no ha tocado nada.** Los requisitos 1 y 2 del taller tienen sus 13
pruebas escritas **con su control contra una tubería** —sin el control, «funciona
con PTY» no distingue que el PTY lo arregle de que funcionara igual— y **se
saltan en Windows**. El PC no tiene WSL con Python ni el demonio de Docker.

> **`skipped` no es `passed`.** Mientras salgan saltadas, los requisitos siguen
> sin medir.

Se cierran en **cualquier Linux, sin RVR**:

```bash
cd ~/atriz_ws/src/Atriz_rvr && python3 -m pytest scripts/agente/pruebas/ -q
```

Y lo que exige el robot está en `atriz-lab/VALIDAR_CON_EL_ROBOT.md` §4: doce
casillas, cada una **con qué la refutaría**.

---

## 8 · Tres hallazgos que cambiaron el diseño

### 8.1 · La lista de prácticas de la web no era la del robot

`espacio.ts` nombraba diez ficheros; **cinco no existían**:

```
01_primer_movimiento.py → 01_avanzar.py          10_navegacion.py  → 10_movimiento_completo.py
02_giro.py              → 02_girar.py            90_practica_libre → 90_template.py
seguidor_linea.py       → seguidor_linea_pid_demo.py
```

Y faltaban las cinco de IR, añadidas por el robot el 2026-08-11. Mientras esa
tabla solo decía cuánto despejar era cosmético; **con el terminal ejecutando, un
nombre equivocado es un botón que falla**.

→ **La lista la da el AGENTE**, leyendo el directorio real. La tabla se queda con
lo que alguien midió, se casa por nombre, y lo que no reconoce sale con «no tengo
la cuenta de este fichero».

### 8.2 · 🔴 Un fallo cruzado entre dos unidades de systemd

`atriz-robot.service` declara `RuntimeDirectory=atriz` **con**
`RuntimeDirectoryPreserve=yes`, y ahí vive la marca del vigía de DDS que
garantiza «una sola cura por arranque».

Si la unidad del agente declarara el mismo `RuntimeDirectory` **sin** el
`Preserve`, **parar el agente borraría `/run/atriz`** y con él esa marca: el
robot volvería a reiniciarse solo más de una vez por arranque, en mitad de una
clase, sin que nada apuntara al agente.

`systemd-analyze verify` no lo ve, y leer cualquiera de las dos por separado
tampoco.

### 8.3 · Los `while True` legítimos no son dos, son ocho

El diseño original justificaba el tope de tiempo diciendo «dos prácticas son
`while True` legítimos». Contadas hoy: **ocho de quince** (05, 11, las cinco de
IR y el seguidor).

→ Tope de **600 s**, prorrogable, **con cuenta atrás visible**. Un tope que mate
la práctica 22 a mitad de clase es peor que no tenerlo.

---

## 9 · Dos cosas del plan que resultaron imposibles

1. **«`PYTHONPATH` en solo lectura».** El agente corre como `sphero` y
   `scripts/estudiantes/` es de `sphero`: mismo usuario, mismo derecho de
   escritura. → Se **copia `atriz.py` a la carpeta de la sesión** en cada
   lanzamiento: consigue lo que se quería y es más fuerte, porque se regenera.
   ⚠️ No cierra que el guion escriba en el directorio real con `open()`.
2. **Llamar a `/stop_scan` tras cada ejecución.** `atriz.py` solo apaga el
   barrido si lo encendió él, para no dejar ciega una navegación en curso. →
   `comprobar_efecto()` devuelve hoy **«no lo sé» en todos sus campos**;
   devolver `false` sería afirmar «he mirado y no pasa nada».

---

## 10 · 🔴 Lo que este terminal ABRE, y va en la pantalla

El programa del alumno corre con **`rclpy` nativo**. Desde ahí alcanza
`raw_motors`, `move_timed` y `set_ir_mode('following')` — los caminos que **se
saltan el `collision_monitor`** y que la lista blanca cierra al navegador.

**La frase «`raw_motors` ya no es alcanzable, 0,00 cm verificado» deja de ser
cierta mientras haya un programa corriendo.**

No se puede impedir sin quitarle Python al alumno. Lo que se hace es **decirlo**,
y que la parada de emergencia siga funcionando pase lo que pase.

👤 Y por eso hay que **quitar `~/.git-credentials` de los robots**: el código del
alumno puede leer lo que `sphero` lea, y ahí está el PAT de GitHub.

---

## 11 · Lo que queda abierto

| | |
|---|---|
| ✅ ~~El PTY, sin medir~~ | **Medido el 2026-08-15 desde el navegador**: `05_sensor_color.py` imprimió una línea cada **~510 ms** durante 20 s, no un bloque al final. Y las 17 pruebas (13 + 4 de la 117), 17/17 en la Pi |
| ⏳ **`comprobar_efecto()` devuelve «no lo sé»** | Implementarlo exige hablar con rosbridge y medirlo en el robot |
| ⏳ **cgroups** | Decidido para después: hoy hay tope de pared y de salida |
| ⏳ **TLS** | El testigo viaja en claro. Dura 10 min y se pide antes de cada conexión |
| ⏳ **El terminal por dirección IP** | No puede funcionar: el testigo lleva el número dentro. La pantalla lo dice |
| ⏳ **Las prácticas 20-24** | Necesitan **dos robots**, y dos de ellas se mueven sin capa de seguridad |
