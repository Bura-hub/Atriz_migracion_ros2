# Cliente de rosbridge — Plan de implementación

> **Para quien lo ejecute (persona o agente):** SUB-SKILL OBLIGATORIA — usa
> `superpowers:subagent-driven-development` (recomendada) o `superpowers:executing-plans` para
> implementarlo tarea a tarea. Los pasos llevan casilla (`- [ ]`) para ir marcándolos.

**Objetivo:** que un robot Sphero RVR se teleopere desde el navegador, con el desplazamiento
**medido con cinta**, sobre una capa de datos probada sin robot.

**Arquitectura:** un núcleo TypeScript **sin un solo import de React ni de Next**, en
`src/lib/rosbridge/`, que habla el protocolo JSON de rosbridge **a mano** (sin roslibjs) contra
`ws://rvr-NN.local:9090`. Dos de sus cinco módulos —`contrato` y `salud`— son **funciones puras** y
se prueban en Node, sin navegador y sin robot. Encima, una capa fina de hooks de React.

**Pila:** TypeScript 5 · Vitest (nueva, solo desarrollo) · Next.js 15 / React 19 ya presentes.

**Especificación:** [`2026-08-03-cliente-rosbridge-spec.md`](2026-08-03-cliente-rosbridge-spec.md).
**Contexto:** [plan de la Fase 5](2026-08-03-plataforma-web.md) y su
[revisión](2026-08-03-plataforma-web-revision.md).

## Restricciones globales

Se aplican a **todas** las tareas.

- **Repositorio:** `Bura-hub/atriz-lab`. Todas las rutas de este plan son **relativas a su raíz**.
  👤 **Precondición: el repositorio tiene que estar en privado antes del primer `push`.**
- **Español** en identificadores, comentarios, mensajes de error y commits. Es lo que hace el resto
  del proyecto (`_vigilar_silencio`, `limitar`, `secuencia_de_cierre`), y mezclar idiomas dentro de
  un mismo sistema es deuda.
- **`src/lib/rosbridge/` no importa React, Next, ni nada del navegador salvo `WebSocket`**, y este
  entra por inyección. Es lo que permite probarlo en Node.
- **Ninguna dependencia nueva de producción.** Solo `vitest` como dependencia de desarrollo.
- **TypeScript en `strict`.** Ya lo está en `tsconfig.json`.
- 🔴 **No se toca la lista blanca del robot.** Si algo obliga a abrir un glob de
  `robot.launch.py`, el diseño se torció: **para y consulta**.
- 🔴 **Nada se da por bueno por un código de salida.** Van seis casos documentados en este proyecto
  de «informa de éxito sin haber hecho nada». Cada tarea termina con una comprobación de **efecto**.
- **Valores medidos que el código debe respetar** (no son ajustables sin volver a medir):
  `/odom` 16,5 Hz · watchdog del driver **0,3 s** · umbral de silencio **3 s** · batería
  **7,0 V baja / 6,5 V crítica, histéresis 0,2** · `percentage` es **fracción 0-1** ·
  `antiguedad_*_s == -1.0` significa **«no se sabe»**.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/lib/rosbridge/contrato.ts` | Las tres listas blancas y los tipos de mensaje. **Puro.** |
| `src/lib/rosbridge/salud.ts` | Estado del robot a partir de antigüedades. **Puro.** |
| `src/lib/rosbridge/protocolo.ts` | Construcción de ops de rosbridge y el registro de llamadas pendientes con su timeout. |
| `src/lib/rosbridge/transporte.ts` | WebSocket, reconexión, resuscripción, reloj de llegadas. |
| `src/lib/rosbridge/teleoperacion.ts` | Bucle de 10 Hz, arranque del barrido, parada de emergencia. |
| `src/lib/rosbridge/index.ts` | API pública del núcleo. |
| `herramientas/comprobar_contrato.mjs` | Compara `contrato.ts` con `robot.launch.py` del robot. |
| `herramientas/medir_qos_rosbridge.mjs` | La medición marcada NO VERIFICADO en la spec. |

---

## Tarea 1 · Limpiar `atriz-lab` y poder ejecutar pruebas

Antes de añadir nada hay que quitar lo que miente. El repositorio contiene un backend cuyo camino
de ejecución tiene inyección de comandos, un reproductor de una cámara que no existe, y un botón
**STOP ALL sin manejador** — en un proyecto donde la parada de emergencia ha fallado cuatro veces.

**Ficheros:**
- Borrar: `backend/` (entero), `frontend/src/components/LaboratoryVideoCard.tsx`, `codes.txt`
- Modificar: `frontend/src/components/Dashboard.tsx`, `frontend/src/components/DashboardLayout.tsx`, `frontend/package.json`, `README.md`
- Crear: `frontend/vitest.config.ts`, `frontend/src/lib/rosbridge/.gitkeep`

- [ ] **Paso 1: Borrar el backend y la tarjeta de vídeo**

```bash
cd atriz-lab
git rm -r backend
git rm frontend/src/components/LaboratoryVideoCard.tsx codes.txt
```

Se borra `backend/` entero, no se parchea: acumula inyección de comandos por `script_name`,
`known_hosts=None` en las cinco conexiones SSH, ruta fija en el directorio temporal, un sandbox que
su propio docstring llama «simulado», y estado de tarea por `random.choice`.

- [ ] **Paso 2: Quitar la tarjeta de vídeo de la rejilla**

En `frontend/src/components/Dashboard.tsx`, eliminar el `import LaboratoryVideoCard` y su uso en la
rejilla, dejando el cuadrante vacío con este marcador:

```tsx
{/* Hueco del antiguo vídeo. No hay cámaras en los robots (decisión cerrada
    del proyecto). Aquí irá el estado del enlace cuando exista la capa de datos. */}
<div className="card flex items-center justify-center text-muted-foreground">
  Sin cámaras en este laboratorio
</div>
```

- [ ] **Paso 3: Desactivar el botón STOP ALL, que hoy no hace nada**

En `frontend/src/components/DashboardLayout.tsx`, al `<button>` de STOP ALL (el que no tiene
`onClick`) añadirle:

```tsx
disabled
title="Sin cablear todavía: no hay capa de datos. Un botón de parada que no para es peor que ninguno."
```

Un control de seguridad decorativo es la peor clase de artefacto en este proyecto. Se queda visible
y **desactivado** hasta que la Tarea 7 lo conecte.

- [ ] **Paso 4: Instalar Vitest**

```bash
cd frontend
npm install --save-dev vitest
```

En `frontend/package.json`, añadir a `scripts`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Paso 5: Crear la configuración de Vitest**

Crear `frontend/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // El nucleo de rosbridge se prueba en Node, sin navegador y sin robot.
    environment: 'node',
    include: ['src/lib/**/*.test.ts'],
  },
})
```

- [ ] **Paso 6: Reescribir el README con lo que es verdad**

Sustituir `README.md` entero. El actual promete «Ejecución segura con Docker + cgroups»,
PostgreSQL operativo, migraciones y monitoreo en tiempo real — **ninguna de las cuatro es cierta**.
El nuevo dice, como mínimo:

```markdown
# Atriz Lab — plataforma web del laboratorio de robótica

Cliente web de 16 robots Sphero RVR sobre ROS 2 Jazzy. Habla con cada robot por
**rosbridge** (un WebSocket por robot, `ws://rvr-NN.local:9090`).

## Estado real

- ✅ Sistema visual: tokens claro/oscuro en `src/app/globals.css`.
- 🚧 Capa de datos (`src/lib/rosbridge/`): en construcción.
- ❌ Autenticación: no existe. rosbridge 2.7.0 no la tiene.
- ❌ Ejecución de código del alumno: no existe.
- **No hay cámaras** en los robots.

El plan y las mediciones que sostienen este diseño están en el repositorio
`Atriz_migracion_ros2` (privado), en `00_auditoria/planes/`.
```

- [ ] **Paso 7: Comprobar que el proyecto sigue compilando y que las pruebas corren**

```bash
cd frontend
npm run build
npm test
```

Esperado: el `build` termina sin error, y `npm test` dice **«No test files found»** — que es correcto
todavía y demuestra que Vitest está instalado y configurado.

- [ ] **Paso 8: Commit**

```bash
git add -A
git commit -m "limpiar: fuera el backend de mentira, la camara que no existe y el STOP ALL decorativo"
```

---

## Tarea 2 · `contrato.ts` — la lista blanca y los tipos

**Ficheros:**
- Crear: `frontend/src/lib/rosbridge/contrato.ts`
- Test: `frontend/src/lib/rosbridge/contrato.test.ts`

**Interfaces:**
- Consume: nada.
- Produce: `TOPICS_LECTURA`, `TOPICS_ESCRITURA`, `SERVICIOS`, `ACCIONES`, `TIPOS`,
  `permitidoSuscribir(topic: string): boolean`, `permitidoPublicar(topic: string): boolean`,
  `permitidoLlamar(servicio: string): boolean`, `tipoDe(topic: string): string | undefined`,
  `porcentajeLegible(fraccion: number): number`, `nivelBateria(voltios: number): NivelBateria`,
  `interpretarAntiguedad(s: number): Frescura`.

- [ ] **Paso 1: Escribir la prueba que falla**

Crear `frontend/src/lib/rosbridge/contrato.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import {
  permitidoPublicar, permitidoSuscribir, permitidoLlamar, tipoDe, confirmaEfecto,
  porcentajeLegible, nivelBateria, interpretarAntiguedad,
} from './contrato'

describe('lista blanca', () => {
  it('permite publicar en los tres topics de escritura', () => {
    expect(permitidoPublicar('/cmd_vel_raw')).toBe(true)
    expect(permitidoPublicar('/emergency_stop')).toBe(true)
    expect(permitidoPublicar('/initialpose')).toBe(true)
  })

  // Esta es LA prueba de esta tarea. /cmd_vel es la SALIDA del collision_monitor:
  // publicar ahi FUNCIONA y salta la capa de seguridad en silencio.
  it('NO permite publicar en /cmd_vel', () => {
    expect(permitidoPublicar('/cmd_vel')).toBe(false)
  })

  it('permite suscribirse a los 12 de lectura y a nada mas', () => {
    expect(permitidoSuscribir('/odom')).toBe(true)
    expect(permitidoSuscribir('/collision_monitor_state')).toBe(true)
    expect(permitidoSuscribir('/ambient_light')).toBe(false)
  })

  it('permite los 8 servicios y rechaza los que se saltan la seguridad', () => {
    expect(permitidoLlamar('/start_scan')).toBe(true)
    expect(permitidoLlamar('/set_leds')).toBe(true)
    expect(permitidoLlamar('/raw_motors')).toBe(false)
    expect(permitidoLlamar('/move_timed')).toBe(false)
  })

  it('conoce el tipo de cada topic', () => {
    expect(tipoDe('/odom')).toBe('nav_msgs/msg/Odometry')
    expect(tipoDe('/emergency_stop')).toBe('std_msgs/msg/Empty')
    expect(tipoDe('/cmd_vel_raw')).toBe('geometry_msgs/msg/Twist')
  })

  // SetLeds.srv tiene la respuesta VACIA: es la unica operacion de la
  // superficie web que no puede fallar visiblemente. La UI no debe prometer
  // confirmacion de un cambio de color.
  it('sabe que /set_leds no puede confirmar su efecto', () => {
    expect(confirmaEfecto('/set_leds')).toBe(false)
    expect(confirmaEfecto('/start_scan')).toBe(true)
  })
})

describe('bateria', () => {
  // percentage es una FRACCION 0-1: leerla como 0-100 hizo que un robot al
  // 34 % pareciera estar al 0 % y provoco una falsa alarma.
  it('convierte la fraccion 0-1 a porcentaje', () => {
    expect(porcentajeLegible(0.34)).toBe(34)
    expect(porcentajeLegible(1)).toBe(100)
  })

  // El porcentaje decia 100 % con 8,29 V. La senal valida es el VOLTAJE.
  it('decide por voltaje, con los umbrales del firmware', () => {
    expect(nivelBateria(8.29)).toBe('OK')
    expect(nivelBateria(7.01)).toBe('OK')
    expect(nivelBateria(6.99)).toBe('BAJA')
    expect(nivelBateria(6.49)).toBe('CRITICA')
  })
})

describe('frescura de /motor_status', () => {
  // -1.0 significa «nunca se ha sabido nada», NO «todo bien».
  it('trata -1.0 como desconocido, no como cero', () => {
    expect(interpretarAntiguedad(-1)).toEqual({ conocido: false })
    expect(interpretarAntiguedad(0)).toEqual({ conocido: true, antiguedadS: 0 })
    expect(interpretarAntiguedad(30.5)).toEqual({ conocido: true, antiguedadS: 30.5 })
  })
})
```

- [ ] **Paso 2: Ejecutarla para comprobar que falla**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/contrato.test.ts`
Esperado: **FALLA** con `Failed to resolve import "./contrato"`.

- [ ] **Paso 3: Escribir la implementación mínima**

Crear `frontend/src/lib/rosbridge/contrato.ts`:

```ts
/**
 * El contrato con el robot. NO se inventa: es la lista blanca de rosbridge de
 * `atriz_rvr_bringup/launch/robot.launch.py:320-360` en el repositorio Atriz_rvr.
 *
 * `herramientas/comprobar_contrato.mjs` compara este fichero con aquel. Si
 * divergen, gana el robot: la web no puede ampliar su propia autorizacion.
 */

export const TOPICS_LECTURA = [
  '/odom', '/imu', '/scan', '/battery_state', '/motor_status', '/encoders',
  '/color', '/map', '/tf', '/tf_static', '/collision_monitor_state', '/amcl_pose',
] as const

/** 🔴 /cmd_vel NO esta y no debe estar: es la SALIDA del collision_monitor. */
export const TOPICS_ESCRITURA = ['/cmd_vel_raw', '/emergency_stop', '/initialpose'] as const

export const SERVICIOS = [
  '/start_scan', '/stop_scan', '/release_emergency_stop', '/set_pos_and_yaw',
  '/set_led_rgb', '/set_multiple_leds', '/set_leds', '/trigger_led_event',
] as const

export const ACCIONES = ['/navigate_to_pose'] as const

export const TIPOS: Readonly<Record<string, string>> = {
  '/odom': 'nav_msgs/msg/Odometry',
  '/imu': 'sensor_msgs/msg/Imu',
  '/scan': 'sensor_msgs/msg/LaserScan',
  '/battery_state': 'sensor_msgs/msg/BatteryState',
  '/motor_status': 'atriz_rvr_msgs/msg/MotorStatus',
  // 🔴 `Encoder`, SINGULAR. `Encoders.msg` no existe: el driver importa
  //    `from atriz_rvr_msgs.msg import (Color, ControlState, Encoder, ...)` y
  //    publica `create_publisher(Encoder, 'encoders', qos_tel)`. Un tipo mal
  //    escrito da `InvalidClassException` en rosbridge y el sintoma es «ese
  //    topic no llega», que se busca en el sitio equivocado.
  '/encoders': 'atriz_rvr_msgs/msg/Encoder',
  '/color': 'atriz_rvr_msgs/msg/Color',
  '/map': 'nav_msgs/msg/OccupancyGrid',
  '/tf': 'tf2_msgs/msg/TFMessage',
  '/tf_static': 'tf2_msgs/msg/TFMessage',
  // ⚠️ NO VERIFICADO: lo publica Nav2, que no esta clonado en ningun sitio, asi
  //    que el nombre del paquete es una suposicion. Se cierra con el robot:
  //    `ros2 topic type /collision_monitor_state`.
  '/collision_monitor_state': 'nav2_msgs/msg/CollisionMonitorState',
  '/amcl_pose': 'geometry_msgs/msg/PoseWithCovarianceStamped',
  '/cmd_vel_raw': 'geometry_msgs/msg/Twist',
  '/emergency_stop': 'std_msgs/msg/Empty',
  '/initialpose': 'geometry_msgs/msg/PoseWithCovarianceStamped',
}

const enLista = (lista: readonly string[], x: string) => lista.includes(x)

export const permitidoSuscribir = (topic: string) => enLista(TOPICS_LECTURA, topic)
export const permitidoPublicar = (topic: string) => enLista(TOPICS_ESCRITURA, topic)
export const permitidoLlamar = (servicio: string) => enLista(SERVICIOS, servicio)
export const tipoDe = (topic: string): string | undefined => TIPOS[topic]

/**
 * SetLeds.srv tiene la respuesta del servicio VACIA: no hay ningun campo debajo
 * del `---`. Es la unica operacion de la superficie web sin deteccion de fallo,
 * y en este firmware hay comandos de LED que se aceptan en silencio sin hacer
 * nada. La UI NO puede prometer que el color cambio.
 */
export const SERVICIOS_SIN_CONFIRMACION = ['/set_leds'] as const
export const confirmaEfecto = (servicio: string) => !enLista(SERVICIOS_SIN_CONFIRMACION, servicio)

/**
 * /battery_state.percentage es una FRACCION 0-1, no un porcentaje: lo manda
 * sensor_msgs/BatteryState y el driver lo respeta.
 */
export const porcentajeLegible = (fraccion: number) => Math.round(fraccion * 100)

export type NivelBateria = 'OK' | 'BAJA' | 'CRITICA'

/** Umbrales del propio firmware del RVR. El PORCENTAJE no sirve para decidir carga. */
export const V_BAJA = 7.0
export const V_CRITICA = 6.5

export function nivelBateria(voltios: number): NivelBateria {
  if (voltios < V_CRITICA) return 'CRITICA'
  if (voltios < V_BAJA) return 'BAJA'
  return 'OK'
}

export type Frescura = { conocido: false } | { conocido: true; antiguedadS: number }

/** -1.0 en antiguedad_atasco_s / _fallo_s / _termico_s es «no se sabe», no «todo bien». */
export function interpretarAntiguedad(s: number): Frescura {
  return s < 0 ? { conocido: false } : { conocido: true, antiguedadS: s }
}
```

- [ ] **Paso 4: Ejecutar la prueba y comprobar que pasa**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/contrato.test.ts`
Esperado: **PASA**, 7 pruebas.

- [ ] **Paso 5: Commit**

```bash
git add frontend/src/lib/rosbridge/contrato.ts frontend/src/lib/rosbridge/contrato.test.ts
git commit -m "contrato: la lista blanca del robot y la semantica que ya provoco falsas alarmas"
```

---

## Tarea 3 · Que el contrato no pueda derivar del robot

Una lista blanca duplicada a mano es deriva documental esperando a ocurrir, y este proyecto tuvo
**cuatro casos de deriva en un solo día**.

**Ficheros:**
- Crear: `herramientas/comprobar_contrato.mjs`
- Modificar: `frontend/package.json`

**Interfaces:**
- Consume: `TOPICS_LECTURA`, `TOPICS_ESCRITURA`, `SERVICIOS`, `ACCIONES` de la Tarea 2.
- Produce: el script `npm run contrato -- <ruta a Atriz_rvr>`, código de salida ≠ 0 si divergen.

- [ ] **Paso 1: Escribir el comprobador**

Crear `herramientas/comprobar_contrato.mjs`:

```js
#!/usr/bin/env node
/**
 * Compara la lista blanca de `contrato.ts` con la de `robot.launch.py`.
 * Si divergen, GANA EL ROBOT: la web no puede ampliar su propia autorizacion.
 *
 *   node herramientas/comprobar_contrato.mjs ../Atriz_rvr
 */
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// Todas las rutas se resuelven contra la RAIZ DEL PROYECTO, no contra el
// directorio de trabajo: npm ejecuta los guiones desde `frontend/`, asi que
// una ruta relativa al CWD apuntaria al sitio equivocado segun quien lo llame.
const raizProyecto = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const raizRvr = resolve(raizProyecto, process.argv[2] ?? '../Atriz_rvr')

const rutaLaunch = join(raizRvr, 'atriz_rvr_bringup/launch/robot.launch.py')
if (!existsSync(rutaLaunch)) {
  // 🔴 CODIGO 2, no 0. En este proyecto el 2 significa «no concluye», y esto es
  // exactamente eso: no se comparo nada. Salir con 0 seria una comprobacion
  // muerta que cuenta como aprobada — el patron que ya costo caro aqui.
  // Convencion: probar_lista_blanca.py:169 (return 2 cuando el control no
  // responde), verificar_robot.sh:1423, atriz-escaneo.sh:135, compilar.sh:44.
  // Un CI bloquea con != 0 por defecto, asi que no hace falta ninguna bandera.
  console.error(`🔴 NO SE COMPARÓ NADA: no encuentro ${rutaLaunch}. Esto no es un aprobado.`)
  console.error('   Uso: node herramientas/comprobar_contrato.mjs ../Atriz_rvr')
  process.exit(2)
}

const launch = readFileSync(rutaLaunch, 'utf8')
const contrato = readFileSync(join(raizProyecto, 'frontend/src/lib/rosbridge/contrato.ts'), 'utf8')

/** Saca las cadenas '/loquesea' de un bloque `NOMBRE = [ ... ]`. */
function bloquePython(fuente, nombre) {
  // El anclaje lleva `[ \t]*` porque las constantes NO estan a nivel de modulo:
  // viven indentadas dentro de la funcion del launch. Con `^${nombre}` no casa
  // nada y el script muere con «no encuentro el bloque LEER». Medido.
  const m = fuente.match(new RegExp(`^[ \\t]*${nombre}\\s*=\\s*\\[([\\s\\S]*?)\\]`, 'm'))
  if (!m) throw new Error(`no encuentro el bloque ${nombre} en robot.launch.py`)
  return [...m[1].matchAll(/'(\/[^']+)'/g)].map((x) => x[1]).sort()
}

function bloqueTs(fuente, nombre) {
  const m = fuente.match(new RegExp(`export const ${nombre}\\s*=\\s*\\[([\\s\\S]*?)\\]`, 'm'))
  if (!m) throw new Error(`no encuentro ${nombre} en contrato.ts`)
  return [...m[1].matchAll(/'(\/[^']+)'/g)].map((x) => x[1]).sort()
}

const pares = [
  ['LEER', 'TOPICS_LECTURA'],
  ['ESCRIBIR', 'TOPICS_ESCRITURA'],
  ['SERVICIOS', 'SERVICIOS'],
]

let fallos = 0
for (const [enPython, enTs] of pares) {
  const a = bloquePython(launch, enPython)
  const b = bloqueTs(contrato, enTs)
  const soloRobot = a.filter((x) => !b.includes(x))
  const soloWeb = b.filter((x) => !a.includes(x))
  if (soloRobot.length || soloWeb.length) {
    fallos++
    console.error(`🔴 ${enPython} / ${enTs} divergen`)
    if (soloRobot.length) console.error(`   solo en el ROBOT: ${soloRobot.join(' ')}`)
    if (soloWeb.length) console.error(`   solo en la WEB:   ${soloWeb.join(' ')}  <-- la web NO puede ampliarse sola`)
  } else {
    console.log(`✅ ${enPython}: ${a.length} entradas, coinciden`)
  }
}
process.exit(fallos ? 1 : 0)
```

- [ ] **Paso 2: Añadir el guion a `package.json`**

```json
"contrato": "node ../herramientas/comprobar_contrato.mjs"
```

- [ ] **Paso 3: Ejecutarlo contra el repositorio real**

Ejecutar, desde la raíz de `atriz-lab`:

```bash
node herramientas/comprobar_contrato.mjs "../Atriz_rvr"
```

Esperado: tres líneas `✅` con **12**, **3** y **8** entradas respectivamente.

- [ ] **Paso 4: Comprobar que detecta una divergencia de verdad**

Un comprobador que nunca ha fallado no está comprobado. Añadir temporalmente `'/cmd_vel'` a
`TOPICS_ESCRITURA` en `contrato.ts` y volver a ejecutarlo.

Esperado: `🔴 ESCRIBIR / TOPICS_ESCRITURA divergen`, con `solo en la WEB: /cmd_vel`, y **código de
salida 1**. Después, **deshacer el cambio** y comprobar que vuelve a dar `✅`.

- [ ] **Paso 5: Commit**

```bash
git add herramientas/comprobar_contrato.mjs frontend/package.json
git commit -m "contrato: comprobador contra robot.launch.py, probado rompiendolo"
```

---

## Tarea 4 · `salud.ts` — el estado del robot, sin adivinar

**Ficheros:**
- Crear: `frontend/src/lib/rosbridge/salud.ts`
- Test: `frontend/src/lib/rosbridge/salud.test.ts`

**Interfaces:**
- Consume: nada.
- Produce: `UMBRAL_SILENCIO_MS`, `EstadoRobot`, `EntradaSalud`, `Salud`,
  `evaluarSalud(e: EntradaSalud): Salud`.

- [ ] **Paso 1: Escribir la prueba que falla**

Crear `frontend/src/lib/rosbridge/salud.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { evaluarSalud, UMBRAL_SILENCIO_MS } from './salud'

const base = { conectado: true, msDesdeUltimoOdom: 0, msDesdeUltimoScan: 0, frenando: false }

describe('estado del robot', () => {
  it('sin WebSocket es SIN_CONEXION', () => {
    expect(evaluarSalud({ ...base, conectado: false }).estado).toBe('SIN_CONEXION')
  })

  it('con /odom fresco es EN_LINEA', () => {
    expect(evaluarSalud(base).estado).toBe('EN_LINEA')
  })

  // Se barre la BANDA ENTERA, no solo los extremos: un test de tres puntos
  // «representativos» ya dejo pasar un bug en el seguidor de linea.
  it('la frontera esta exactamente en el umbral', () => {
    expect(evaluarSalud({ ...base, msDesdeUltimoOdom: UMBRAL_SILENCIO_MS - 1 }).estado).toBe('EN_LINEA')
    expect(evaluarSalud({ ...base, msDesdeUltimoOdom: UMBRAL_SILENCIO_MS }).estado).toBe('EN_LINEA')
    expect(evaluarSalud({ ...base, msDesdeUltimoOdom: UMBRAL_SILENCIO_MS + 1 }).estado).toBe('SIN_DATOS')
  })

  it('si /odom nunca llego, es SIN_DATOS', () => {
    expect(evaluarSalud({ ...base, msDesdeUltimoOdom: null }).estado).toBe('SIN_DATOS')
  })

  // 🔴 Lo mas importante del modulo: SIN_DATOS NO es averia, y el cliente
  // NO puede saber cual de las tres causas es.
  it('sin /odom ni /scan ofrece las tres causas y no elige', () => {
    const s = evaluarSalud({ ...base, msDesdeUltimoOdom: null, msDesdeUltimoScan: null })
    expect(s.estado).toBe('SIN_DATOS')
    expect(s.causasPosibles).toHaveLength(3)
    expect(s.esAveria).toBe(false)
  })

  // La UNICA de las tres que se distingue, y es gratis.
  it('si /scan llega y /odom no, senala la excepcion en un manejador', () => {
    const s = evaluarSalud({ ...base, msDesdeUltimoOdom: null, msDesdeUltimoScan: 0 })
    expect(s.causasPosibles).toHaveLength(1)
    expect(s.causasPosibles[0]).toContain('manejador')
  })

  it('frenando es informativo y no cambia el estado', () => {
    const s = evaluarSalud({ ...base, frenando: true })
    expect(s.estado).toBe('EN_LINEA')
    expect(s.frenando).toBe(true)
  })
})
```

- [ ] **Paso 2: Ejecutarla para comprobar que falla**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/salud.test.ts`
Esperado: **FALLA** con `Failed to resolve import "./salud"`.

- [ ] **Paso 3: Escribir la implementación mínima**

Crear `frontend/src/lib/rosbridge/salud.ts`:

```ts
/**
 * La salud se mide por RITMO y por ANTIGUEDAD, nunca por que el topic exista:
 * `ros2 topic list` conserva topics de nodos muertos, y el log del driver
 * escribe «streaming reanudado» con el robot apagado.
 */

/**
 * 3 s es el MISMO umbral que usa el detector de silencio del driver, para que
 * cliente y robot coincidan en cuando algo va mal.
 *
 * Se decide por LLEGADAS y no por Hz a proposito: una comprobacion de «> 10 Hz»
 * de este proyecto PASABA midiendo 11,3 Hz sobre un robot que iba a 16,5.
 */
export const UMBRAL_SILENCIO_MS = 3000

export type EstadoRobot = 'SIN_CONEXION' | 'EN_LINEA' | 'SIN_DATOS'

export interface EntradaSalud {
  conectado: boolean
  /** ms desde la ultima llegada, o null si no llego ninguna. */
  msDesdeUltimoOdom: number | null
  msDesdeUltimoScan: number | null
  frenando: boolean
}

export interface Salud {
  estado: EstadoRobot
  frenando: boolean
  /** Vacio salvo en SIN_DATOS. El cliente NO elige entre ellas. */
  causasPosibles: string[]
  /** Siempre false: nada de lo que este modulo ve prueba una averia. */
  esAveria: boolean
}

const fresco = (ms: number | null) => ms !== null && ms <= UMBRAL_SILENCIO_MS

export function evaluarSalud(e: EntradaSalud): Salud {
  if (!e.conectado) {
    return { estado: 'SIN_CONEXION', frenando: false, causasPosibles: [], esAveria: false }
  }
  if (fresco(e.msDesdeUltimoOdom)) {
    return { estado: 'EN_LINEA', frenando: e.frenando, causasPosibles: [], esAveria: false }
  }

  // 🔴 SIN_DATOS no es averia. Con 16 robots, «el RVR apagado y la Pi viva» es
  //    el estado COTIDIANO de carga: pintarlo rojo saca la flota entera en rojo.
  const causasPosibles = fresco(e.msDesdeUltimoScan)
    ? ['una excepcion dentro de un manejador de telemetria del driver: /scan llega y /odom no']
    : [
        'el robot esta cargando: RVR apagado y Raspberry Pi encendida',
        'el RVR se durmio',
        'una excepcion dentro de un manejador de telemetria del driver',
      ]

  return { estado: 'SIN_DATOS', frenando: e.frenando, causasPosibles, esAveria: false }
}
```

- [ ] **Paso 4: Ejecutar la prueba y comprobar que pasa**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/salud.test.ts`
Esperado: **PASA**, 7 pruebas.

- [ ] **Paso 5: Commit**

```bash
git add frontend/src/lib/rosbridge/salud.ts frontend/src/lib/rosbridge/salud.test.ts
git commit -m "salud: por ritmo y no por existencia del topic, y sin adivinar la causa"
```

---

## Tarea 5 · `protocolo.ts` — las ops y el timeout que rosbridge no da

rosbridge **deniega en silencio**: registra un aviso y hace `return`, sin respuesta al cliente. Sin
timeout propio, una llamada denegada se manifiesta como «la web no responde».

**Ficheros:**
- Crear: `frontend/src/lib/rosbridge/protocolo.ts`
- Test: `frontend/src/lib/rosbridge/protocolo.test.ts`

**Interfaces:**
- Consume: `permitidoPublicar`, `permitidoSuscribir`, `permitidoLlamar`, `tipoDe` (Tarea 2).
- Produce: `opSubscribe`, `opUnsubscribe`, `opAdvertise`, `opPublish`, `opCallService`,
  `RegistroPendientes` con `registrar(id, ms): Promise<unknown>`, `resolver(id, valor)`,
  `cancelarTodas(motivo)`.

- [ ] **Paso 1: Escribir la prueba que falla**

Crear `frontend/src/lib/rosbridge/protocolo.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest'
import { opAdvertise, opPublish, opSubscribe, opCallService, RegistroPendientes } from './protocolo'

describe('construccion de ops', () => {
  it('subscribe lleva el tipo del contrato', () => {
    expect(opSubscribe('/odom')).toEqual({ op: 'subscribe', topic: '/odom', type: 'nav_msgs/msg/Odometry' })
  })

  it('advertise de la parada lleva su tipo', () => {
    expect(opAdvertise('/emergency_stop')).toEqual({
      op: 'advertise', topic: '/emergency_stop', type: 'std_msgs/msg/Empty',
    })
  })

  // La lista blanca se comprueba EN EL CLIENTE para no caer en el silencio.
  it('se niega a publicar en /cmd_vel, con un mensaje que lo explica', () => {
    expect(() => opPublish('/cmd_vel', {})).toThrowError(/lista blanca/)
  })

  it('se niega a suscribirse a algo fuera de la lista', () => {
    expect(() => opSubscribe('/ambient_light')).toThrowError(/lista blanca/)
  })

  it('call_service lleva id para poder emparejar la respuesta', () => {
    expect(opCallService('/start_scan', {}, 'abc')).toEqual({
      op: 'call_service', service: '/start_scan', args: {}, id: 'abc',
    })
  })
})

describe('llamadas pendientes', () => {
  it('resuelve cuando llega la respuesta', async () => {
    const r = new RegistroPendientes()
    const p = r.registrar('x', 5000)
    r.resolver('x', { values: true })
    await expect(p).resolves.toEqual({ values: true })
  })

  // El mensaje NO debe elegir entre «denegado» y «robot caido»: no se pueden distinguir.
  it('al vencer el plazo dice las dos posibilidades y no elige', async () => {
    vi.useFakeTimers()
    const r = new RegistroPendientes()
    const p = r.registrar('y', 5000)
    const capturado = expect(p).rejects.toThrowError(/denegad[ao].*|.*ca[ií]d/)
    vi.advanceTimersByTime(5001)
    await capturado
    vi.useRealTimers()
  })

  it('cancelar todas rechaza las pendientes al caerse el enlace', async () => {
    const r = new RegistroPendientes()
    const p = r.registrar('z', 5000)
    r.cancelarTodas('se cerro el WebSocket')
    await expect(p).rejects.toThrowError(/WebSocket/)
  })
})
```

- [ ] **Paso 2: Ejecutarla para comprobar que falla**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/protocolo.test.ts`
Esperado: **FALLA** con `Failed to resolve import "./protocolo"`.

- [ ] **Paso 3: Escribir la implementación mínima**

Crear `frontend/src/lib/rosbridge/protocolo.ts`:

```ts
import { permitidoLlamar, permitidoPublicar, permitidoSuscribir, tipoDe } from './contrato'

export interface OpSalida {
  op: string
  [clave: string]: unknown
}

/**
 * ⚠️ NO VERIFICADO: que campos de QoS acepta rosbridge 2.7.0 en `advertise` y
 * `subscribe`. Su fuente no esta en ningun repositorio del proyecto, asi que
 * todo lo que creemos saber de su protocolo es de SEGUNDA MANO.
 * Hasta medirlo (herramientas/medir_qos_rosbridge.mjs) NO se manda campo `qos`:
 * rosbridge se suscribe con qos_profile_sensor_data (BEST_EFFORT), que empareja
 * con publicadores BEST_EFFORT y RELIABLE por igual.
 */

const exigir = (permitido: boolean, que: string, donde: string) => {
  if (!permitido) {
    throw new Error(
      `«${que}» no esta en la lista blanca de ${donde} del robot (robot.launch.py). ` +
        `Si de verdad hace falta, se amplia EN EL ROBOT, no aqui.`,
    )
  }
}

export function opSubscribe(topic: string): OpSalida {
  exigir(permitidoSuscribir(topic), topic, 'lectura')
  return { op: 'subscribe', topic, type: tipoDe(topic)! }
}

export const opUnsubscribe = (topic: string): OpSalida => ({ op: 'unsubscribe', topic })

export function opAdvertise(topic: string): OpSalida {
  exigir(permitidoPublicar(topic), topic, 'escritura')
  return { op: 'advertise', topic, type: tipoDe(topic)! }
}

export function opPublish(topic: string, msg: unknown): OpSalida {
  exigir(permitidoPublicar(topic), topic, 'escritura')
  return { op: 'publish', topic, msg }
}

export function opCallService(service: string, args: unknown, id: string): OpSalida {
  exigir(permitidoLlamar(service), service, 'servicios')
  return { op: 'call_service', service, args, id }
}

/** Empareja respuestas con llamadas, y pone el plazo que rosbridge no pone. */
export class RegistroPendientes {
  private pendientes = new Map<
    string,
    { resolver: (v: unknown) => void; rechazar: (e: Error) => void; plazo: ReturnType<typeof setTimeout> }
  >()

  registrar(id: string, ms: number): Promise<unknown> {
    return new Promise((resolver, rechazar) => {
      const plazo = setTimeout(() => {
        this.pendientes.delete(id)
        // No se elige entre las dos: desde el navegador son indistinguibles.
        rechazar(new Error(
          `sin respuesta en ${ms / 1000} s. Puede estar denegado por la lista blanca ` +
            `(rosbridge deniega en silencio) o el robot puede estar caido.`,
        ))
      }, ms)
      this.pendientes.set(id, { resolver, rechazar, plazo })
    })
  }

  resolver(id: string, valor: unknown): void {
    const p = this.pendientes.get(id)
    if (!p) return
    clearTimeout(p.plazo)
    this.pendientes.delete(id)
    p.resolver(valor)
  }

  cancelarTodas(motivo: string): void {
    for (const [id, p] of this.pendientes) {
      clearTimeout(p.plazo)
      p.rechazar(new Error(`llamada cancelada: ${motivo}`))
      this.pendientes.delete(id)
    }
  }
}
```

- [ ] **Paso 4: Ejecutar la prueba y comprobar que pasa**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/protocolo.test.ts`
Esperado: **PASA**, 9 pruebas (6 de «lista blanca», 2 de «bateria», 1 de «frescura»).

- [ ] **Paso 5: Commit**

```bash
git add frontend/src/lib/rosbridge/protocolo.ts frontend/src/lib/rosbridge/protocolo.test.ts
git commit -m "protocolo: las ops de rosbridge, y el plazo que rosbridge no da"
```

---

## Tarea 6 · `transporte.ts` — WebSocket, reconexión y reloj de llegadas

**Ficheros:**
- Crear: `frontend/src/lib/rosbridge/transporte.ts`
- Test: `frontend/src/lib/rosbridge/transporte.test.ts`

**Interfaces:**
- Consume: `RegistroPendientes`, `opSubscribe`, `opAdvertise`, `opPublish`, `opCallService` (Tarea 5).
- Produce: `esperaReconexion(intento, aleatorio)`, `urlDeRobot(idOrHost)`, `class Transporte` con
  `conectar()`, `cerrar()`, `suscribir(topic, cb): () => void`, `publicar(topic, msg)`,
  `llamar(servicio, args, ms?): Promise<unknown>`, `msDesdeUltimo(topic): number | null`,
  `conectado: boolean`.

- [ ] **Paso 1: Escribir la prueba que falla**

Crear `frontend/src/lib/rosbridge/transporte.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest'
import { esperaReconexion, urlDeRobot, Transporte } from './transporte'

describe('espera de reconexion', () => {
  // El driver tiene el ANTIPATRON medido: 123 reintentos, uno cada 4 s, sin
  // espera creciente. No se repite aqui.
  it('duplica desde 1 s y topa en 30 s', () => {
    const sinRuido = () => 0.5   // 0.8 + 0.4*0.5 = 1.0 exacto
    expect(esperaReconexion(0, sinRuido)).toBe(1000)
    expect(esperaReconexion(1, sinRuido)).toBe(2000)
    expect(esperaReconexion(5, sinRuido)).toBe(30000)
    expect(esperaReconexion(50, sinRuido)).toBe(30000)
  })

  // Para que 16 navegadores no reintenten a la vez.
  it('mete ruido de +-20 %', () => {
    expect(esperaReconexion(0, () => 0)).toBe(800)
    expect(esperaReconexion(0, () => 1)).toBe(1200)
  })
})

describe('direccion del robot', () => {
  it('convierte un numero de robot en su nombre mDNS', () => {
    expect(urlDeRobot(1)).toBe('ws://rvr-01.local:9090')
    expect(urlDeRobot(16)).toBe('ws://rvr-16.local:9090')
  })

  it('acepta una IP u host como override', () => {
    expect(urlDeRobot('192.168.1.58')).toBe('ws://192.168.1.58:9090')
  })
})

/** WebSocket de mentira, para probar sin navegador ni robot. */
class WSFalso {
  static ultimo: WSFalso
  enviados: string[] = []
  onopen?: () => void
  onmessage?: (e: { data: string }) => void
  onclose?: () => void
  constructor(public url: string) { WSFalso.ultimo = this }
  send(d: string) { this.enviados.push(d) }
  close() { this.onclose?.() }
  abrir() { this.onopen?.() }
  recibir(obj: unknown) { this.onmessage?.({ data: JSON.stringify(obj) }) }
}

describe('Transporte', () => {
  it('al suscribirse manda la op y entrega los mensajes', () => {
    const t = new Transporte('ws://x:9090', (u) => new WSFalso(u) as unknown as WebSocket)
    t.conectar()
    WSFalso.ultimo.abrir()

    const recibidos: unknown[] = []
    t.suscribir('/odom', (m) => recibidos.push(m))

    expect(JSON.parse(WSFalso.ultimo.enviados[0])).toMatchObject({ op: 'subscribe', topic: '/odom' })

    WSFalso.ultimo.recibir({ op: 'publish', topic: '/odom', msg: { twist: 1 } })
    expect(recibidos).toEqual([{ twist: 1 }])
  })

  it('anota cuando llego el ultimo mensaje de cada topic', () => {
    const t = new Transporte('ws://x:9090', (u) => new WSFalso(u) as unknown as WebSocket)
    t.conectar()
    WSFalso.ultimo.abrir()
    t.suscribir('/odom', () => {})

    expect(t.msDesdeUltimo('/odom')).toBeNull()   // todavia no llego ninguno
    WSFalso.ultimo.recibir({ op: 'publish', topic: '/odom', msg: {} })
    expect(t.msDesdeUltimo('/odom')).toBeGreaterThanOrEqual(0)
  })

  it('al reconectar vuelve a suscribirse a todo', () => {
    const t = new Transporte('ws://x:9090', (u) => new WSFalso(u) as unknown as WebSocket)
    t.conectar()
    WSFalso.ultimo.abrir()
    t.suscribir('/odom', () => {})
    t.suscribir('/scan', () => {})

    const anterior = WSFalso.ultimo
    anterior.onclose?.()
    t.conectar()
    WSFalso.ultimo.abrir()

    const ops = WSFalso.ultimo.enviados.map((s) => JSON.parse(s))
    expect(ops.filter((o) => o.op === 'subscribe').map((o) => o.topic).sort()).toEqual(['/odom', '/scan'])
  })

  // Sin esto, esperaReconexion seria codigo muerto: el transporte solo se
  // reconectaria si alguien llamara a conectar() a mano.
  it('se reconecta solo, esperando lo que dice esperaReconexion', () => {
    vi.useFakeTimers()
    const t = new Transporte('ws://x:9090', (u) => new WSFalso(u) as unknown as WebSocket, {
      reconectar: true, aleatorio: () => 0.5,
    })
    t.conectar()
    WSFalso.ultimo.abrir()
    const primero = WSFalso.ultimo

    primero.onclose?.()
    expect(WSFalso.ultimo).toBe(primero)          // todavia no
    vi.advanceTimersByTime(1000)                  // esperaReconexion(0) = 1000
    expect(WSFalso.ultimo).not.toBe(primero)      // ya hay socket nuevo
    vi.useRealTimers()
  })

  it('avisa a quien escuche cuando se cae el enlace', () => {
    const t = new Transporte('ws://x:9090', (u) => new WSFalso(u) as unknown as WebSocket)
    let caidas = 0
    t.alCerrarse(() => caidas++)
    t.conectar()
    WSFalso.ultimo.abrir()
    WSFalso.ultimo.onclose?.()
    expect(caidas).toBe(1)
  })
})
```

- [ ] **Paso 2: Ejecutarla para comprobar que falla**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/transporte.test.ts`
Esperado: **FALLA** con `Failed to resolve import "./transporte"`.

- [ ] **Paso 3: Escribir la implementación mínima**

Crear `frontend/src/lib/rosbridge/transporte.ts`:

```ts
import { RegistroPendientes, opAdvertise, opCallService, opPublish, opSubscribe } from './protocolo'

/**
 * Un WebSocket por robot. NO hay namespace: al robot lo identifica la CONEXION,
 * asi que el mismo codigo sirve para los 16.
 */
export function urlDeRobot(robot: number | string): string {
  const host = typeof robot === 'number' ? `rvr-${String(robot).padStart(2, '0')}.local` : robot
  return `ws://${host}:9090`
}

/** 1 s duplicando hasta 30 s, con +-20 % de ruido. */
export function esperaReconexion(intento: number, aleatorio: () => number = Math.random): number {
  const base = Math.min(1000 * 2 ** intento, 30000)
  return Math.round(base * (0.8 + 0.4 * aleatorio()))
}

type Manejador = (msg: unknown) => void
type FabricaWS = (url: string) => WebSocket

interface OpcionesTransporte {
  reconectar?: boolean
  aleatorio?: () => number
  programar?: (fn: () => void, ms: number) => ReturnType<typeof setTimeout>
}

export class Transporte {
  private ws: WebSocket | null = null
  private suscripciones = new Map<string, Set<Manejador>>()
  private anunciados = new Set<string>()
  private ultimaLlegada = new Map<string, number>()
  private pendientes = new RegistroPendientes()
  private oyentesCierre = new Set<() => void>()
  private contador = 0
  private intentos = 0

  constructor(
    private url: string,
    private fabrica: FabricaWS = (u) => new WebSocket(u),
    private opciones: OpcionesTransporte = {},
  ) {}

  get conectado(): boolean {
    return this.ws !== null && this.ws.readyState === 1
  }

  /** Para que la teleoperacion pueda cortar su bucle al caerse el enlace. */
  alCerrarse(cb: () => void): () => void {
    this.oyentesCierre.add(cb)
    return () => this.oyentesCierre.delete(cb)
  }

  conectar(): void {
    const ws = this.fabrica(this.url)
    this.ws = ws
    ws.onopen = () => {
      this.intentos = 0
      // Al reconectar se resuscribe a TODO y se reanuncia: rosbridge infiere el
      // QoS mirando los publicadores al suscribirse y no se reajusta despues.
      for (const topic of this.suscripciones.keys()) this.enviar(opSubscribe(topic))
      for (const topic of this.anunciados) this.enviar(opAdvertise(topic))
    }
    ws.onmessage = (e: MessageEvent) => this.entrante(JSON.parse(String(e.data)))
    ws.onclose = () => {
      this.ws = null
      this.anunciados.clear()   // el socket nuevo tendra que reanunciar
      this.pendientes.cancelarTodas('se cerro el WebSocket')
      for (const cb of this.oyentesCierre) cb()
      // 🔴 NO se libera la parada de emergencia al reconectar: liberarla es
      //    siempre un acto humano deliberado.
      if (this.opciones.reconectar) {
        const espera = esperaReconexion(this.intentos++, this.opciones.aleatorio)
        const programar = this.opciones.programar ?? setTimeout
        programar(() => this.conectar(), espera)
      }
    }
  }

  cerrar(): void {
    this.ws?.close()
    this.ws = null
  }

  private enviar(op: unknown): void {
    this.ws?.send(JSON.stringify(op))
  }

  private entrante(m: { op: string; topic?: string; msg?: unknown; id?: string; values?: unknown }): void {
    if (m.op === 'publish' && m.topic) {
      this.ultimaLlegada.set(m.topic, Date.now())
      for (const cb of this.suscripciones.get(m.topic) ?? []) cb(m.msg)
      return
    }
    if (m.op === 'service_response' && m.id) this.pendientes.resolver(m.id, m.values)
  }

  suscribir(topic: string, cb: Manejador): () => void {
    const nueva = !this.suscripciones.has(topic)
    if (nueva) this.suscripciones.set(topic, new Set())
    this.suscripciones.get(topic)!.add(cb)
    if (nueva && this.conectado) this.enviar(opSubscribe(topic))
    return () => { this.suscripciones.get(topic)?.delete(cb) }
  }

  publicar(topic: string, msg: unknown): void {
    if (!this.anunciados.has(topic)) {
      this.enviar(opAdvertise(topic))
      this.anunciados.add(topic)
    }
    this.enviar(opPublish(topic, msg))
  }

  llamar(servicio: string, args: unknown = {}, ms = 5000): Promise<unknown> {
    const id = `atriz-${++this.contador}`
    const p = this.pendientes.registrar(id, ms)
    this.enviar(opCallService(servicio, args, id))
    return p
  }

  /** null = no ha llegado ninguno todavia. Es lo que alimenta salud.ts. */
  msDesdeUltimo(topic: string): number | null {
    const t = this.ultimaLlegada.get(topic)
    return t === undefined ? null : Date.now() - t
  }
}
```

- [ ] **Paso 4: Ejecutar la prueba y comprobar que pasa**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/transporte.test.ts`
Esperado: **PASA**, 7 pruebas.

- [ ] **Paso 5: Commit**

```bash
git add frontend/src/lib/rosbridge/transporte.ts frontend/src/lib/rosbridge/transporte.test.ts
git commit -m "transporte: un socket por robot, espera creciente y resuscripcion al volver"
```

---

## Tarea 7 · `teleoperacion.ts` — el bucle de 10 Hz, el barrido y la parada

**Ficheros:**
- Crear: `frontend/src/lib/rosbridge/teleoperacion.ts`, `frontend/src/lib/rosbridge/index.ts`
- Test: `frontend/src/lib/rosbridge/teleoperacion.test.ts`

**Interfaces:**
- Consume: `Transporte` (Tarea 6).
- Produce: `PERIODO_MS`, `twist(v, w)`, `class Teleoperacion` con `arrancarBarrido(): Promise<void>`,
  `mover(v, w)`, `parar()`, `paradaEmergencia()`, `detener()`.

- [ ] **Paso 1: Escribir la prueba que falla**

Crear `frontend/src/lib/rosbridge/teleoperacion.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest'
import { PERIODO_MS, Teleoperacion, twist } from './teleoperacion'

function transporteFalso() {
  const publicados: { topic: string; msg: unknown }[] = []
  const llamados: string[] = []
  let manejadorScan: ((m: unknown) => void) | undefined
  let alCaerse: (() => void) | undefined
  return {
    publicados, llamados,
    llegaUnScan: () => manejadorScan?.({ ranges: [1, 2, 3] }),
    caerElEnlace: () => alCaerse?.(),
    t: {
      publicar: (topic: string, msg: unknown) => publicados.push({ topic, msg }),
      llamar: async (s: string) => { llamados.push(s); return {} },
      suscribir: (topic: string, cb: (m: unknown) => void) => {
        if (topic === '/scan') manejadorScan = cb
        return () => {}
      },
      alCerrarse: (cb: () => void) => { alCaerse = cb; return () => {} },
    },
  }
}

describe('twist', () => {
  it('rellena los seis campos que espera geometry_msgs/Twist', () => {
    expect(twist(0.2, 0)).toEqual({
      linear: { x: 0.2, y: 0, z: 0 }, angular: { x: 0, y: 0, z: 0 },
    })
  })
})

describe('arranque del barrido', () => {
  // 🔴 Se espera un /scan DE VERDAD, no el codigo de retorno del servicio.
  //    Sin /scan el collision_monitor bloquea el movimiento: 0,0 cm medidos
  //    contra 9,9 del control, y el robot PARECE averiado.
  it('no se da por arrancado hasta que llega un /scan real', async () => {
    const f = transporteFalso()
    const tele = new Teleoperacion(f.t as never)
    let listo = false
    const p = tele.arrancarBarrido().then(() => { listo = true })

    await Promise.resolve()
    expect(f.llamados).toEqual(['/start_scan'])
    expect(listo).toBe(false)      // el servicio respondio y AUN NO vale

    f.llegaUnScan()
    await p
    expect(listo).toBe(true)
  })
})

describe('bucle de teleoperacion', () => {
  // El watchdog del driver corta a los 0,3 s: hay que republicar a ~10 Hz.
  it('republica el mismo Twist mientras dure la orden', () => {
    vi.useFakeTimers()
    const f = transporteFalso()
    const tele = new Teleoperacion(f.t as never)

    tele.mover(0.2, 0)
    vi.advanceTimersByTime(PERIODO_MS * 5)

    const aCmd = f.publicados.filter((p) => p.topic === '/cmd_vel_raw')
    expect(aCmd.length).toBeGreaterThanOrEqual(5)
    expect(aCmd[0].msg).toEqual(twist(0.2, 0))
    tele.detener()
    vi.useRealTimers()
  })

  it('parar manda un Twist cero y corta el bucle', () => {
    vi.useFakeTimers()
    const f = transporteFalso()
    const tele = new Teleoperacion(f.t as never)
    tele.mover(0.2, 0)
    vi.advanceTimersByTime(PERIODO_MS * 2)
    tele.parar()
    const cuantos = f.publicados.length
    vi.advanceTimersByTime(PERIODO_MS * 10)

    expect(f.publicados[f.publicados.length - 1].msg).toEqual(twist(0, 0))
    expect(f.publicados.length).toBe(cuantos)      // ya no publica mas
    vi.useRealTimers()
  })
})

describe('parada de emergencia', () => {
  it('publica en /emergency_stop y corta el bucle', () => {
    vi.useFakeTimers()
    const f = transporteFalso()
    const tele = new Teleoperacion(f.t as never)
    tele.mover(0.2, 0)
    tele.paradaEmergencia()

    expect(f.publicados.some((p) => p.topic === '/emergency_stop')).toBe(true)
    const cuantos = f.publicados.length
    vi.advanceTimersByTime(PERIODO_MS * 10)
    expect(f.publicados.length).toBe(cuantos)
    vi.useRealTimers()
  })

  // Liberar la parada es un acto humano deliberado: NO lo hace esta clase.
  it('no expone ninguna forma de liberar la parada', () => {
    const tele = new Teleoperacion(transporteFalso().t as never)
    expect((tele as unknown as Record<string, unknown>).liberarParada).toBeUndefined()
  })
})

describe('enlace caido', () => {
  // Publicar contra un socket muerto hace que la UI parezca que sigue mandando.
  it('corta el bucle solo cuando se cae el WebSocket', () => {
    vi.useFakeTimers()
    const f = transporteFalso()
    const tele = new Teleoperacion(f.t as never)
    tele.mover(0.2, 0)
    vi.advanceTimersByTime(PERIODO_MS * 2)

    f.caerElEnlace()
    const cuantos = f.publicados.length
    vi.advanceTimersByTime(PERIODO_MS * 10)
    expect(f.publicados.length).toBe(cuantos)
    vi.useRealTimers()
  })
})
```

- [ ] **Paso 2: Ejecutarla para comprobar que falla**

Ejecutar: `cd frontend && npx vitest run src/lib/rosbridge/teleoperacion.test.ts`
Esperado: **FALLA** con `Failed to resolve import "./teleoperacion"`.

- [ ] **Paso 3: Escribir la implementación mínima**

Crear `frontend/src/lib/rosbridge/teleoperacion.ts`:

```ts
import type { Transporte } from './transporte'

/**
 * El watchdog del driver corta a los 0,3 s sin cmd_vel (medido: para en 527 ms
 * y 7,9 cm). Hay que REPUBLICAR a ~10 Hz mientras dure la orden: un `sleep`
 * entre publicaciones deja el robot parado casi todo el tiempo.
 */
export const RITMO_HZ = 10
export const PERIODO_MS = 1000 / RITMO_HZ

export interface Twist {
  linear: { x: number; y: number; z: number }
  angular: { x: number; y: number; z: number }
}

export const twist = (v: number, w: number): Twist => ({
  linear: { x: v, y: 0, z: 0 },
  angular: { x: 0, y: 0, z: w },
})

export class Teleoperacion {
  private bucle: ReturnType<typeof setInterval> | null = null
  private quitarOyente: () => void

  constructor(private t: Transporte) {
    // Si se cae el enlace, seguir publicando contra un socket muerto haria que
    // la UI pareciera estar mandando. El watchdog del driver ya para el robot;
    // el cliente no debe fingir lo contrario.
    this.quitarOyente = this.t.alCerrarse(() => this.detener())
  }

  /** Suelta el oyente del transporte. Llamar al desmontar la vista. */
  desmontar(): void {
    this.detener()
    this.quitarOyente()
  }

  /**
   * 🔴 Espera un /scan DE VERDAD, no el codigo de retorno de /start_scan.
   *    Sin /scan el collision_monitor bloquea el movimiento y el robot parece
   *    averiado sin estarlo.
   */
  async arrancarBarrido(): Promise<void> {
    await this.t.llamar('/start_scan')
    await new Promise<void>((listo) => {
      const quitar = this.t.suscribir('/scan', () => { quitar(); listo() })
    })
  }

  mover(v: number, w: number): void {
    this.detener()
    const orden = twist(v, w)
    this.t.publicar('/cmd_vel_raw', orden)
    this.bucle = setInterval(() => this.t.publicar('/cmd_vel_raw', orden), PERIODO_MS)
  }

  parar(): void {
    this.detener()
    this.t.publicar('/cmd_vel_raw', twist(0, 0))
  }

  /**
   * La parada va SOLO a /emergency_stop. Los otros dos nombres que el driver
   * escucha estan fuera de topics_pub_glob, aunque el README del robot diga
   * lo contrario.
   *
   * No hay metodo para LIBERARLA: es un acto humano deliberado, con
   * confirmacion, y ademas exige comprobar antes que no haya objetivo de Nav2
   * activo (sin cancelar_nav2 vivo, el robot reanuda solo: 34,7 cm medidos).
   */
  paradaEmergencia(): void {
    this.detener()
    this.t.publicar('/emergency_stop', {})
  }

  detener(): void {
    if (this.bucle !== null) {
      clearInterval(this.bucle)
      this.bucle = null
    }
  }
}
```

Crear `frontend/src/lib/rosbridge/index.ts`:

```ts
export * from './contrato'
export * from './salud'
export * from './protocolo'
export * from './transporte'
export * from './teleoperacion'
```

- [ ] **Paso 4: Ejecutar toda la batería y comprobar que pasa**

Ejecutar: `cd frontend && npm test`
Esperado: **PASA**. Los cinco ficheros de prueba, **39 pruebas** en total: 8 de `contrato`,
7 de `salud`, 8 de `protocolo`, 9 de `transporte` y 7 de `teleoperacion`.

- [ ] **Paso 5: Commit**

```bash
git add frontend/src/lib/rosbridge/teleoperacion.ts frontend/src/lib/rosbridge/teleoperacion.test.ts frontend/src/lib/rosbridge/index.ts
git commit -m "teleoperacion: 10 Hz contra el watchdog, el barrido por EFECTO y la parada"
```

---

## Tarea 8 · Medir contra rvr-01 lo que está marcado NO VERIFICADO

Hasta aquí no se ha tocado un robot. Esta tarea cierra la única suposición del diseño.

**Ficheros:**
- Crear: `herramientas/medir_qos_rosbridge.mjs`

**Interfaces:**
- Consume: nada del núcleo (es un script suelto, para no acoplar la medición al código medido).
- Produce: un informe por consola con lo que rosbridge 2.7.0 acepta y con los kB/s reales.

- [ ] **Paso 1: Escribir el medidor**

Crear `herramientas/medir_qos_rosbridge.mjs`:

```js
#!/usr/bin/env node
/**
 * Mide contra un robot REAL lo que la especificacion marca NO VERIFICADO:
 *   1. ¿acepta rosbridge 2.7.0 un campo `qos` en subscribe/advertise?
 *   2. ¿funcionan throttle_rate y queue_length?
 *   3. ¿cuantos kB/s cuesta cada topic de verdad?
 *
 *   node herramientas/medir_qos_rosbridge.mjs rvr-01.local
 *
 * ⚠️ Enciende el barrido del LIDAR (sube el X2 de 2,7 a 11,8 Hz) y lo APAGA al
 *    terminar. No mueve el robot.
 */
const host = process.argv[2] ?? 'rvr-01.local'
const ws = new WebSocket(`ws://${host}:9090`)

const bytes = new Map()
const cuenta = new Map()
let t0 = 0

const anotar = (topic, n) => {
  bytes.set(topic, (bytes.get(topic) ?? 0) + n)
  cuenta.set(topic, (cuenta.get(topic) ?? 0) + 1)
}

ws.onopen = async () => {
  console.log(`conectado a ${host}`)
  ws.send(JSON.stringify({ op: 'call_service', service: '/start_scan', args: {}, id: 'scan-on' }))

  // (1) subscribe CON campo qos. Si rosbridge lo ignora, seguiran llegando
  //     mensajes igual; si lo rechaza, mandara un `status` de tipo error.
  ws.send(JSON.stringify({
    op: 'subscribe', topic: '/odom', type: 'nav_msgs/msg/Odometry',
    qos: { reliability: 'best_effort', durability: 'volatile' },
  }))
  // (2) throttle_rate: pedimos 2 Hz sobre un topic que va a 16,5.
  ws.send(JSON.stringify({ op: 'subscribe', topic: '/imu', type: 'sensor_msgs/msg/Imu', throttle_rate: 500 }))
  ws.send(JSON.stringify({ op: 'subscribe', topic: '/scan', type: 'sensor_msgs/msg/LaserScan' }))

  t0 = Date.now()
  setTimeout(() => {
    const s = (Date.now() - t0) / 1000
    console.log(`\n--- ${s.toFixed(1)} s ---`)
    let total = 0
    for (const [topic, n] of bytes) {
      total += n
      console.log(`${topic.padEnd(20)} ${(n / s / 1024).toFixed(1)} kB/s   ${(cuenta.get(topic) / s).toFixed(2)} Hz`)
    }
    console.log(`${'TOTAL'.padEnd(20)} ${(total / s / 1024).toFixed(1)} kB/s   (referencia navegando: 80,7)`)
    console.log(`\n/imu a ~2 Hz => throttle_rate FUNCIONA. A ~16 Hz => se ignora.`)
    ws.send(JSON.stringify({ op: 'call_service', service: '/stop_scan', args: {}, id: 'scan-off' }))
    setTimeout(() => { ws.close(); process.exit(0) }, 500)
  }, 30000)
}

ws.onmessage = (e) => {
  const n = typeof e.data === 'string' ? e.data.length : e.data.byteLength
  const m = JSON.parse(String(e.data))
  if (m.op === 'publish') anotar(m.topic, n)
  // 🔴 Un `status` de nivel error es la respuesta a la pregunta (1).
  if (m.op === 'status' && m.level !== 'info') console.log(`STATUS ${m.level}: ${m.msg}`)
  if (m.op === 'service_response') console.log(`servicio ${m.id}: ${JSON.stringify(m.values)}`)
}
```

- [ ] **Paso 2: Ejecutarlo contra rvr-01**

👤 **Requiere el robot encendido y en la misma red.** No lo mueve, pero enciende el barrido.

```bash
node herramientas/medir_qos_rosbridge.mjs rvr-01.local
```

Anotar tres cosas: si aparece algún `STATUS error` al mandar `qos`; a qué frecuencia llega `/imu`;
y los kB/s de cada topic.

- [ ] **Paso 3: Escribir el resultado donde no se pierda**

Crear la evidencia en el repositorio `atriz_migracion`, en
`00_auditoria/evidencia/68_qos_de_rosbridge.txt`, con el formato de las demás: pregunta, método,
salida cruda, y qué queda decidido. **Si rosbridge acepta `qos`, actualizar el comentario de
`protocolo.ts` y añadirlo a `opSubscribe`; si lo ignora, dejarlo escrito para que nadie vuelva a
intentarlo.**

- [ ] **Paso 4: Commit en los dos repositorios**

```bash
# en atriz-lab
git add herramientas/medir_qos_rosbridge.mjs
git commit -m "herramientas: medir que acepta rosbridge 2.7.0, en vez de suponerlo"
```

---

## Tarea 9 · La prueba que de verdad importa: el robot se mueve

Nada de lo anterior prueba que un alumno pueda mover el robot. Esto sí.

**Ficheros:** ninguno nuevo. Es una sesión guiada, con cinta métrica.

- [ ] **Paso 1: Comprobar que la lista blanca sigue intacta**

En el robot:

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/probar_lista_blanca.py
```

Esperado: **exactamente el mismo resultado que antes del cliente**. Si algo cambió, el diseño se
torció y hay que parar.

- [ ] **Paso 2: Medir el movimiento por SSH, que es el control**

En el robot, con cinta en el suelo y marcando el punto de partida:

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && python3 -c "
from atriz import Robot
with Robot() as r: r.avanzar(0.20, 3)
"
```

Anotar los centímetros recorridos. Referencia esperada: **~60 cm**.

- [ ] **Paso 3: Medir el mismo movimiento desde el navegador**

Desde la consola del navegador, con la página de `atriz-lab` abierta y el robot en el mismo punto
de partida:

```js
const { Transporte, Teleoperacion, urlDeRobot } = await import('/src/lib/rosbridge/index.ts')
const t = new Transporte(urlDeRobot('rvr-01.local')); t.conectar()
const tele = new Teleoperacion(t)
await tele.arrancarBarrido()
tele.mover(0.20, 0); setTimeout(() => tele.parar(), 3000)
```

- [ ] **Paso 4: Comparar, y aceptar o rechazar**

🔴 **Criterio:** los dos desplazamientos coinciden dentro del error de la cinta. Si el del navegador
es **notablemente menor**, la causa más probable no es un fallo del cliente: es el
`collision_monitor` frenando al 40 % por un obstáculo delante — su polígono es **estático** y frena
igual aunque el robot se aleje. Comprobar `/collision_monitor_state` antes de culpar al código.

- [ ] **Paso 5: Probar la parada, mirando el log del driver**

Con el robot avanzando, pulsar la parada desde el navegador y en el robot:

```bash
journalctl -u atriz-robot --since "-25 s" | grep -i "PARADA DE EMERGENCIA"
```

⚠️ **`--since "-25 s"`, no `$(date -u +%T)`**: `date -u` da hora UTC y `journalctl` la interpreta
como local, así que en este robot (UTC−5) la ventana cae **cinco horas en el futuro** y cuenta 0
aunque la parada haya llegado.

Esperado: la línea aparece **y el robot está quieto**. El nombre y el QoS solo se comprueban
publicando de verdad: leer el código da el nombre, pero no el namespace resuelto ni el QoS.

- [ ] **Paso 6: Comprobar que un robot cargando NO se pinta como roto**

Es el estado **cotidiano** con 16 robots y el que nadie había probado hasta el 2026-08-02.

👤 **Apagar el RVR dejando la Raspberry Pi encendida** (que es lo que pasa al ponerlo a cargar), con
la web conectada.

Esperado: el estado pasa a **`SIN_DATOS` en ámbar**, con las tres causas posibles listadas y **sin
llamarlo avería**. Si sale rojo o dice «robot averiado», está mal: con 16 robots cargando a la vez,
el profesor vería la flota entera en rojo.

⚠️ Y comprobar de paso lo que dice el log del robot en ese estado, para que quede escrito:
`journalctl -u atriz-robot --since "-60 s" | grep -c "streaming reanudado"`. Lo medido en su día
fueron **8 en 30 s** con el robot apagado: el log dice que todo va bien y no va.

- [ ] **Paso 7: Escribir la evidencia y cerrar**

Crear `00_auditoria/evidencia/69_web_mueve_el_robot.txt` en `atriz_migracion` con los centímetros de
las dos medidas, la salida del `journalctl` y el veredicto. Actualizar `ESTADO_ACTUAL.md` y el
`CHANGELOG.md` **en el mismo commit**.
