# Rediseño completo de `atriz-lab` — plan para revisión de la Pi

**Fecha:** 2026-08-16 · **Estado:** 🔴 **NADA IMPLEMENTADO. Esperando tu revisión.**
**Punto de retorno:** etiqueta `antes-del-rediseno` en `atriz-lab` (`4df8fed`) y en
`atriz_migracion` (`dfe58db`), las dos subidas. Rama de trabajo: `rediseno-2026-08`.

---

## 👉 Lo que necesito de ti, y va primero

Este plan **no toca el robot**: ni un `.msg`, ni un servicio, ni la lista blanca de rosbridge, ni
`atriz_rvr_driver`. `Atriz_rvr` no tiene un solo cambio pendiente por esto. Pero hay **tres cosas**
donde tu criterio decide, y una es una pregunta técnica que solo puedes contestar tú.

### 1 · 🔴 La pregunta técnica: ¿puede el muro saber quién tiene cada robot?

Es el defecto funcional nº2 de la auditoría y, con 16 alumnos, **la pregunta que más se hace el
profesor**: *«¿quién tiene el 07?»*. Hoy **no hay ninguna pantalla que lo pueda contestar**.

El dato existe: el **agente del Taller** (puerto 9443) sabe el nombre del ocupante
(`estado.ocupacion.nombre`). Pero el muro solo escucha **tres topics baratos** de rosbridge
(`/battery_state`, `/motor_status`, `/estado_robot`) ≈ 7,7 kB/s los dieciséis. Abrir además 16
sockets de agente desde el muro es caro y no se ha medido.

**La pregunta:** ¿puede `/estado_robot` llevar el nombre del ocupante, o hay un canal mejor?
Si la respuesta es que no compensa, **se documenta como límite** y el muro dirá que no lo sabe —
que es lo que esta aplicación hace siempre. No se finge.

⚠️ Si dices que sí, eso **sí** sería un cambio de `.msg`, y entonces aplica la trampa conocida:
`comprobar_contrato.mjs` compara campos contra una instantánea, así que habría que aceptarla a
mano en el mismo commit.

### 2 · Los 16 alumnos necesitan cuenta, y eso es operación del aula

👤 Decidido por el usuario: **una cuenta por alumno** (identidad real) y **dos roles**
(profesor / alumno). Hoy existe **una sola cuenta** y `/usuarios` solo sabe crear — no borra, no
resetea contraseñas, no da de alta por lote.

Desde la Fase B esto ya no es opcional: **sin sesión no se abre ni un socket con ningún robot**.
Lo que te pido no es aprobar el código, es confirmar que el modelo encaja con cómo se da la clase.

**Propuesta de qué reserva el rol de profesor** (dime si sobra o falta algo):

| Acción | Alumno | Profesor |
|---|---|---|
| Conducir, medir, LIDAR, Taller, cuaderno | ✅ | ✅ |
| **Liberar la parada de emergencia** | ❌ | ✅ |
| Arrancar / parar SLAM y Nav2 | ❌ | ✅ |
| Crear, borrar y resetear cuentas | ❌ | ✅ |
| Ver el muro de flota | ✅ | ✅ |

⚠️ **El riesgo que le veo:** si solo el profesor libera la parada y no está en el aula, un robot se
queda parado. Alternativa barata si te parece mejor: que **cualquiera libere la del robot en el que
tiene la sesión abierta**.

### 3 · Textos que tus pruebas verifican literalmente

`pantallas_reales.test.ts` y `tarjetas_vivas.test.ts` exigen **frases exactas** —«ningún programa
corriendo», «saltándose la capa de seguridad», «PUEDE SER» en mayúsculas, «no puede salir solo»…—.
Un rediseño reescribe copy. **Las pruebas se mueven en el mismo commit y no se relajan**: si la
frase nueva es mejor, la prueba pasa a exigir la nueva. Te lo digo para que no te sorprenda ver
esos literales cambiar.

---

## Por qué se hace esto

El usuario pidió un rediseño **mucho más profesional y moderno, que no parezca estándar**,
investigando antes el stack, con **login obligatorio** al inicio, y por fases entregables.

La aplicación hoy **funciona y es honesta** —se niega a afirmar lo que no ha medido, y eso está
ganado a base de fallos documentados—. Lo que le falta:

- **Artesanía visual.** El propio repositorio lo reconoce por escrito (`atriz-lab/CLAUDE.md:77-100`,
  *«lo que esta tabla NO es: una excusa para no diseñar»*, escrito **tras que el usuario tuviera que
  pedirlo cinco veces**): honestidad y artesanía son separables, y **solo la primera está ganada**.
- **Doce defectos funcionales** que no son de pintura.
- Y **la puerta de sesión de la Fase B, que la interfaz nunca reconoció**.

---

## Lo que encontró la auditoría

Tres agentes recorrieron el sistema visual, el inventario de pantallas y el stack. **Verifiqué yo
mismo** los tres hallazgos que sostienen el plan, porque si alguno fuera falso cambiaría el
argumento entero:

```
motion instalada, imports en src/     0          -> la regla «cero dependencias» ya la rompió el repo
middleware.ts                         no existe  -> ninguna ruta está protegida
.trama-* en globals.css / consumidores  3 / 0    -> el tercer código de accesibilidad NO existe
```

### 🔴 Tres hallazgos que reordenan todo

**1 · La regla «cero dependencias nuevas» ya está rota por el propio repositorio, y su texto miente
sobre su estado.** `atriz-lab/CLAUDE.md:147-149` dice *«ni una librería de animación, ni una fuente,
ni un paquete de iconos»* y cita `lucide-react` como instalada:

```
lucide-react   BORRADO (commit 68959e2)
geist          INSTALADA (commit 9b49659, el MISMO día que se escribió la regla)
motion ^12.43  INSTALADA … y CON CERO IMPORTS EN TODO src/
```

La regla **real**, la única con un ejecutor detrás (`estilo.ts:410`), es **cero peticiones a la red
en tiempo de ejecución**. Su caso testigo: Google Stitch pidió Material Symbols a Google Fonts, la
fuente no llegó, y los nombres de los iconos salieron **como texto suelto** en mitad de la interfaz.
→ Un paquete que **se empaqueta en el bundle** no viola el motivo de la regla. La viñeta se corrige.

**2 · No existe `middleware.ts`. Ninguna ruta está protegida.** Sin sesión se ve el **100 %** de la
interfaz y no funciona el **92 %**. Y el punto ciego que queda: **una sesión que caduca a mitad de
clase no se detecta** — `ProveedorSesion` pregunta una sola vez, al montar, así que el raíl sigue
mostrando tu nombre con la sesión ya muerta.

**3 · 🔴 El «tercer código» de accesibilidad está documentado como irrenunciable y NO EXISTE.**
`globals.css` declara que el estado se codifica por **color + palabra + trama**, con el argumento de
que *«una de cada doce personas no distingue el lima del coral, y este muro se proyecta»*.
`.trama-mirar` y `.trama-ir` están en la hoja con **cero consumidores**. La redundancia hoy la lleva
una píldora en `text-xs` que el propio proyecto admite **ilegible a tres metros**.
→ No es una mejora estética: es un **defecto de accesibilidad abierto**, y el rediseño lo cierra.

### Los doce defectos funcionales

| # | Defecto | Qué no puede hacer la persona |
|---|---|---|
| 1 | 🔴 La **parada de emergencia hace scroll fuera de pantalla** en 6 de 7 pestañas | Pararlo sin buscarlo. *La ranura `parada` de `RailNavegacion` existe, está documentada y **nunca se rellena**: código muerto* |
| 2 | 🔴 El profesor **no sabe quién tiene qué robot** | *(La pregunta 1 de arriba)* |
| 3 | 🔴 Sin sesión se ve todo y no funciona nada | La portada enumera 16 robots como destinos vivos **sin una palabra** |
| 4 | 🔴 La caducidad de sesión no se detecta | Trabajar media clase creyendo que sigue dentro |
| 5 | 🔴 `PanelEnlace` **sigue culpando al robot** | Es el fallo del 2026-08-16 sin cerrar del todo: dice *«puede estar apagado, fuera de la red»* cuando falta la sesión del PC |
| 6 | 🔴 En `/conducir` hay que saber que **sin `/scan` el robot no se mueve** | Pulsa, no pasa nada, y la explicación está a 600 px de scroll |
| 7 | 🔴 `/no-obedece` es la mejor pantalla y **nadie llega a ella** | `/conducir` duplica su diagnóstico en vez de derivar |
| 8 | 🔴 El cuaderno **no lee ni un número del robot** | Copiar a mano la mitad de lo que la pantalla existe para comparar |
| 9 | 🔴 Portada y muro **aterrizan en pantallas distintas** del mismo robot; no hay salto robot→robot | Moverse entre 16 robots |
| 10 | 🔴 **No se puede conducir con el teclado** | …en un control con `focus-ring`, que promete que sí |
| 11 | 🔴 **8 implementaciones** de «rótulo + cifra + ausencia», **3** de la caja de aviso | Cambiar el sistema sin tocar 25 sitios |
| 12 | 🔴 A 375 px hay **desbordes reales** | *(Móvil no es prioridad; se anota y se arregla el desborde)* |

Extra: `PanelLidar` crea una **segunda instancia de `Teleoperacion`**, rompiendo una garantía escrita
· `/api/sesion/entrar` **no limita por IP**, y el bloqueo por usuario es en sí mismo un oráculo de
qué cuentas existen.

---

## Lo que el rediseño NO puede tocar

Cada punto tiene una medición, una prueba o una persona detrás. **No son gusto.** Si ves que me
dejo alguno, dímelo — esta lista es media revisión.

**Accesibilidad y escena de uso**
- Triple codificación del estado: **color + palabra + trama** *(y hay que implementarla)*.
- Los tonos de estado están **calculados para tinta sobre papel**: los «bonitos» (verde
  `74 222 128`, ámbar `251 191 36`) bajan de **2:1** sobre papel. Ilegibles, no «suaves».
- **Contrastes medidos con WCAG**, y el criterio del muro es **una persona a tres metros**.
- **Tema claro**, fijado por la escena (aula iluminada), **no heredado del SO**. El modo proyección
  es **un botón**: *«la decisión la toma quien proyecta, no su portátil»*.
- **`prefers-reduced-motion` conserva color y opacidad a 200 ms.** Matarlas devuelve el
  estroboscopio a quien pidió menos movimiento.

**Honestidad del instrumento**
- El rojo `--destructive` es **exclusivo de la parada de emergencia**.
- **Ninguna animación infinita** sobre dato, enlace o salud. Excepción nominal: los dos orbes.
- **Nada se anima al llegar un dato** (`/odom` a 16,5 Hz).
- **`<data value>` solo cuando hay valor.** La ausencia es una raya, nunca un cero.
- **Cero peticiones externas** en tiempo de ejecución.
- Los motivos **no se esconden** tras un desplegable: *«el motivo ES la acción»*.
- `src/lib/rosbridge/` no se toca. **Nunca se llama a `/rosapi/*`.**

---

## La dirección visual: la decide una tirada, no mi gusto

El encargo dice **«que no sea estándar»**. El manual de rediseño de la skill `impeccable` trae la
calibración de en qué caen los rediseños automáticos cuando nadie los vigila —crema con serif de
alto contraste y terracota · casi-negro con neón y halos · editorial de hairlines— más una **lista
negra de fuentes** que son el default (Space Grotesk, IBM Plex, Inter-como-display, DM Sans,
Outfit, Plus Jakarta, Fraunces, Playfair…). Hay que apuntar deliberadamente fuera.

**El hogar cultural NO es «paneles de control».** Es el mundo de la **metrología**: documentos cuyo
oficio entero consiste en decir un valor **junto a su incertidumbre y su método**, y callar lo que
no se midió. Es literalmente la tesis de esta aplicación, hecha objeto.

Siete sistemas candidatos, del mundo real de esta gente, en cuatro familias materiales: el
**certificado de calibración**, el **cuaderno de campo**, la **norma de acotación ISO**, el
**frontal de instrumento de banco**, el **tejido nariñense**, la **lámina topográfica** y la
**señalética de transporte**.

Los dos últimos y el textil me interesan por una razón que no es estética: traen **tramas** en su
gramática nativa — que es exactamente la pieza de accesibilidad que este proyecto declara
obligatoria y nunca construyó. La redundancia dejaría de ser un parche y pasaría a ser la identidad.

**Cuál se construye lo asigna un script** (`concept-seed.mjs`), no yo: *«la tirada es el mecanismo
que impide que cada ejecución converja en el default de la categoría»*.

---

## Las siete fases

🔴 **El orden cambió respecto a mi primer borrador, y la corrección es importante.** Yo había
puesto los cimientos visuales primero y la sesión al final. Está mal, por dos razones que son
dependencias duras y no preferencias:

- **La puerta va ANTES que el diseño visual**, porque **cambia qué pantallas existen**. La portada
  de hoy enumera 16 robots; la portada pública es **otra pantalla**. Y la puerta cambia el estado
  vacío de las otras diez. Diseñar diez pantallas y descubrir después que la mitad vive detrás de
  una puerta obliga a rehacer todos los vacíos.
- **Las cuentas van ANTES que la puerta.** Hoy los 16 alumnos usan la app **sin entrar** (está
  escrito en `layout.tsx:98-101` y en `reglas.ts`). Cerrar la puerta sin haber dado de alta a 16
  personas **deja al aula fuera**. La secuencia es forzosa.

| Fase | Qué | Deja la app… |
|---|---|---|
| **F0** | Desarmar las trampas: el parser, el contraste ejecutable, el fotograma huérfano, la brecha de Tailwind, y borrar lo muerto | **Idéntica**, cero cambio visual |
| **F1** | Cuentas, roles y **alta masiva** | Idéntica + `/usuarios` completo |
| **F2** | La puerta de sesión | **Cerrada, con todos dentro** |
| **F3** | Cimientos: paleta, tipografía, primitivos, **y el tercer código** | Repintada, misma estructura |
| **F4** | Armazón, navegación, **la parada** y el teclado | Navegable de verdad |
| **F5** | Pantalla por pantalla (12 entregas) | Cada una, al terminarla |
| **F6** | Pulido, contraste y verificación humana | Terminada |

📌 F1/F2 tocan `src/lib/sesion/**` y los `layout.tsx`; F3 toca `globals.css` y `ui/**`. Son
conjuntos **disjuntos**: si hay dos manos, van en paralelo.

### 🔴 Cuatro trampas localizadas, y una es peor de lo que yo creía

1. **El parser de `:root` de `estilo.test.ts` funciona HOY POR ACCIDENTE.** Yo dije que exigía dos
   espacios de sangría; el análisis fino es peor: `:root` cierra con `}` **en columna 0** (línea
   373), así que `enBloque(':root {')` **no para ahí** — sigue hasta el `  }` del `body` dentro de
   `@layer base` (línea 436). El resultado sale bien **solo porque entre medias no hay ningún otro
   `--sintaxis-*`**. Casi cualquier reescritura lo rompe, y una de las formas de romperlo
   (`indexOf` → `-1`, `slice(i,-1)` se traga el fichero) da **los dos conjuntos iguales por
   basura**: aprobado sobre nada. Se arregla en F0 con conteo de llaves y **control verde antes y
   después** con el CSS byte a byte igual.
2. **`@keyframes entrar` lo genera Tailwind** solo porque `animate-entrar` se usa en **un** sitio
   (`MuroFlota.tsx:401`), y `.escalonado` lo consume para las 7 pestañas. Si el rediseño lo quita,
   **dejan de animar en silencio**. Se declara a mano en F0 + guardia de fotogramas huérfanos.
3. 🔴 **Al cerrar la puerta, `pantallas_reales.test.ts` y `tarjetas_vivas.test.ts` SE MUEREN**:
   abren páginas sin sesión. Y como se saltan sin su variable de entorno, **«saltada» se lee como
   «pasada»** — que es exactamente el fallo del 2026-08-15. Meterles una cookie firmada
   (`Network.setCookie` en `navegador_cdp.ts`) es **parte de F2**, no un arreglo posterior.
4. **Cambiar `Carga` en `testigo.ts` (para meter el rol) invalida todos los testigos vivos.** Solo
   es aceptable si va **en el mismo despliegue que el alta masiva**, fuera de horario de clase.

### La puerta: por qué el middleware NO verifica la firma

`testigo.ts` usa `node:crypto` (`createHmac`, `timingSafeEqual`) y el middleware de Next corre en
runtime **Edge**. Se comprobó en `node_modules/next@15.5.6`: existe `loadNodeMiddleware` en el
servidor pero **no hay ninguna opción `nodeMiddleware` en el esquema de configuración**. Apoyarse
en eso sería apoyarse en una bandera experimental no documentada.

→ **El middleware solo mira que la cookie ESTÉ** (y redirige con el origen para volver);
**el layout de servidor verifica la firma**. Una sola implementación del testigo.
Se rechazó reescribir la verificación con WebCrypto: serían **dos verificadores de firma**, que es
justo lo que `peticion.ts` existe para evitar.

⚠️ **`/api/*` queda FUERA del matcher, deliberadamente.** Una API tiene que contestar **401 JSON**,
nunca un 307 a HTML: un `fetch()` sigue la redirección y parsea HTML como JSON, y el fallo se lee
como «el servidor devuelve basura».

⚠️ Y `?volver=` es una **redirección abierta** de manual si no se valida. Se cierra con una función
pura y sus casos (`//evil.com`, `/\evil.com`, `https://evil`, `%2f%2f`).

### Dependencias: entran dos, y sale una

**Entran** `@radix-ui/react-dialog` (~12 kB gz) y `@radix-ui/react-popover` (~14 kB gz), **solo por
comportamiento y accesibilidad**: trampa de foco, restauración al cerrar, `Escape`, inertizar el
fondo, colocación con colisión de viewport. Escribir eso a mano son ~250 líneas **que aquí no se
pueden probar** (no hay jsdom y no se instala). La capa visual se escribe a mano.

🔴 **`shadcn/ui` (el CLI) se rechaza con motivo:** `npx shadcn init` **reescribiría `globals.css`**
con su propio vocabulario e instalaría `tailwindcss-animate`, que trae **`animate-pulse` y
`animate-bounce` — literalmente prohibidas por `estilo.ts:52`**. Sería el rediseño destruyendo sus
propias guardias en un comando.

🔴 **`clsx` / `tailwind-merge` se rechazan:** `gruposDeClases()` parsea `className`. Un helper
`cn(...)` haría **invisibles** las clases a la guardia de colisión de `transition` — el defecto que
estuvo vivo todo el desarrollo y que ninguna otra herramienta ve.

🔴 **Y sale `motion`, contra mi propio argumento inicial.** Yo dije «ya está instalada, es la
palanca más fuerte». El análisis lo da la vuelta y tiene razón: **`estilo.ts` vigila CSS y
`className`, y NO puede ver `{ repeat: Infinity }` dentro de un objeto JS**. Adoptarla abriría una
categoría entera de animación infinita **invisible para la guardia**, en la aplicación cuya regla
número uno es que nada late para siempre. Lo que aportaría de verdad —animar la salida de algo que
se desmonta— lo da Radix gratis con `data-state="open|closed"` + `@keyframes`, que **sí** pasa por
delante del ejecutor.
→ `npm rm motion`. Si se prefiere conservarla, entonces es **obligatorio** añadir antes
`repeat:\s*Infinity` a las prohibiciones — si no, mantenerla es un agujero, no una preferencia.

**Gráficas: ninguna dependencia, y es la respuesta correcta.** Una chispa es un `<path d="…">` a
partir de un array. Toda librería trae animación de entrada por defecto, su propia paleta (rompiendo
los cuatro ejes) y 40-180 kB. Y lo decisivo aquí: **la función pura se prueba en Node; una librería
sería imposible de probar en este repositorio.**

---

## Cómo se verifica

**Automático:** `npm run comprobar` (typecheck + lint + 908 pruebas + contrato) · las guardias de
`estilo.test.ts` · `pantallas_reales.test.ts` con `ATRIZ_ROBOT=1` · `tarjetas_vivas.test.ts` con
`ATRIZ_VIVAS=1` (sin robot) · `npm run enlace`.

**🔴 Lo que NO se puede probar solo, y se dice:** no hay jsdom ni `@testing-library` y no se van a
instalar. **Ninguna prueba renderiza un componente.** Colores, espaciado, jerarquía y si algo **se
lee a tres metros** exigen una persona mirando. El criterio de aceptación del muro lo escribe el
propio proyecto nueve veces: **una persona a tres metros.**

---

## El anti-brief, que vale más que el brief

El usuario nombró **las cuatro** formas de fallar, y la cuarta es la que más te importa a ti:

1. Que se parezca a cualquier dashboard.
2. Que sea más bonito y **más lento de usar** — en clase, con el robot en marcha, eso se paga.
3. Oscuro, neón y «futurista» — y aquí además se proyecta en un aula iluminada.
4. 🔴 **Que pierda la honestidad.** Indicadores decorativos, progreso inventado, luces que finjan
   estado.

**El 4 es una restricción dura, no una preferencia.** Si una regla de diseño choca con una de
honestidad, **gana la honestidad**: está escrito en `atriz-lab/CLAUDE.md` y no se toca.
