# Traspaso — dónde estamos y cómo seguir

> **Léelo si retomas el proyecto** después de un tiempo, en otra máquina, o si la
> Raspberry Pi ya se reflasheó. Está escrito para que no haga falta reconstruir el
> contexto desde cero.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-19 (Pi, laboratorio) · EL MAPA BUENO DE LA ARENA, CON ORIGEN
> ANCLADO A UNA ESQUINA CONVENIDA**
> ═══════════════════════════════════════════════════════════════════════════════
> `~/mapas/arena.yaml` rehecho y **verificado por geometría**: extensión ocupada
> **3,95 × 4,00 m** con los muros rectos y alineados con los ejes, que es la
> arena real (medida con el LIDAR antes de arrancar: **cuadrada de ~3,8-4,0 m**).
> Los dos mapas del 08-18 salieron **en rombo** y quedan como `DESCARTADO_*`.
>
> **La convención, que es lo que hay que repetir** (y está en
> `mediciones_banco/mapear_arena.py`): robot en la esquina, **~55 cm de cada
> pared**, pared a su IZQUIERDA y morro **PARALELO** a ella →
> `/set_pos_and_yaw(0,0,0)` → arrancar `atriz-slam` **después** → comprobar que
> `map → base_footprint` da (0,000, 0,000, 0,0°) → conducir. Así **el (0,0) del
> mapa ES esa esquina**, con testigo, y desaparece la ambigüedad de una arena
> cuadrada — que es real: casar `/scan` contra el mapa dio **tres candidatos
> empatados** (0,003/0,004/0,004) y conducir 1 m **no** los desempató.
>
> 🔴 **Trampa nueva:** mover el robot a mano con SLAM vivo da el MISMO síntoma que
> la congelación del `collision_monitor` (evidencia 93) — `/scan` idéntico tramo
> tras tramo y giros de 0,0°. **Pregunta a quien está al lado del robot.**
>
> ⚠️ **Batería:** mapear cuesta ~0,1 V por pasada de 4 min, pero el intento del
> 08-18 murió agotado **y el corte reinició la Pi**. No mapees por debajo de
> ~7,6 V.
>
> ✅ **Y A5 QUEDÓ CERRADO EL MISMO DÍA, con cinta: la pose que fija
> `/initialpose` es correcta.** n=2, **2,7 y 6,9 cm** contra una banda de ≤10 cm
> declarada antes de medir, y con la **predicción escrita antes de que el usuario
> midiera** las dos veces. Aquí AMCL **no** es peor que la odometría (3,1/3,6 cm),
> al revés que en las tandas del 07-08 — ⚠️ contraste, no causa aislada.
> ⚠️ El **rumbo no se contrastó con cinta**, y 6,9 cm no se distingue bien del
> ruido de la medida (cinta contra LIDAR difieren ~2 cm sobre la misma pared).
> Guion: `mediciones_banco/a5_pose_cinta.py`.
>
> ✅ **AMCL con objetos: sin degradación medible** (0,6 cm; los objetos son el 2,6 %
> del barrido). ✅ **Nav2 navegando en la arena: llega a ~15 cm (n=2) y dice
> `SUCCEEDED` las dos veces** — la tolerancia de 10 cm NO se cumple, y el desenlace
> hereda el error de AMCL, así que no prueba llegada.
>
> ✅ **Y la configuración DURA de objetos también: sin degradación medible.** Con los dos
> objetos formando una puerta que el robot cruza, la ocupación del barrido subió a
> **18,6 %** (7× la fácil) y AMCL erró **1,2 cm** — dentro del ruido de la cinta, como las
> otras dos tandas. 📌 Lo que NO se ha probado y es el estresor de verdad: **tapar una
> pared entera**, que no añade ruido sino que quita restricción.
>
> ✅ **Y los HUECOS acotados, sin mover el robot** (costmap + `compute_path_to_pose`):
> con el mapa SIN los objetos, **40,3 cm → 1 celda · 45,0 → 2 · 48,1 → 2**. Puesto al lado
> de la curva de casa (con el mapa engordado: 38,6 → 0 · 47,1 → 1), **el mismo hueco vale
> ~7 cm más cuando los objetos no están en el mapa** — el engorde, medido por fin en el
> planificador.
> 🔴 Y dos fallos de método propios en esa tanda, los dos escritos: medir el coste sobre el
> **eje del robot** en vez de la línea de la puerta (invalidó una conclusión), y montar la
> puerta **en una sala abierta**, donde «¿el plan cruza?» mide si el rodeo es barato, no el
> ancho del paso.
>
> ⏳ **Siguiente:** la **travesía** de confirmación (celdas dicen que el paso existe; solo
> cruzar dice lo que cuesta), el caso **engordado en la arena**, y la **práctica 63**.
> `ATRIZ_MAPA` ya apunta a `arena.yaml`.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-18 (Pi, laboratorio) · LA ARENA MAPEADA POR PRIMERA VEZ** *(mapa
> superado por el del 08-19; el procedimiento de la curva sigue valiendo)*
> ═══════════════════════════════════════════════════════════════════════════════
> Primer pendiente del Bloque C cerrado. Conducción **autónoma** con
> `mediciones_banco/explorar_arena.py` (rebote sobre `atriz.py`): 19 m en dos
> pasadas, cero atascos, y la **meseta de la curva** como criterio de parada
> (12 m → 517 ocupadas · +7 m → 540, un 4 %). El `.pgm` contiene exactamente las
> 540 del mapa vivo. Detalle y lecciones en el CHANGELOG del día — incluida la
> nueva trampa: **una persona sujetando el robot con SLAM vivo produce el mismo
> síntoma que la congelación del collision_monitor** (lecturas idénticas, giros
> de 0,0°).
>
> ⏳ **El siguiente paso exacto, en orden:** 👤 (1) `ATRIZ_MAPA` →
> `/home/sphero/mapas/arena.yaml` en `/etc/default/atriz` y
> `sudo systemctl restart atriz-robot`; (2) `atriz-nav` sobre el mapa fresco y
> cerrar **A5**; (3) resto del Bloque C (AMCL con objetos, huecos 43/45).
> `atriz-slam` quedó parado y el barrido apagado (reposo normal).
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-17 · EL REDISEÑO ESTÁ EN `main`. LA RAMA `rediseno-2026-08` YA NO
> EXISTE**
> ═══════════════════════════════════════════════════════════════════════════════
> 👤 Decisión del usuario. Fusionado **sin merge commit** (avance rápido: `main`
> no tenía nada que la rama no tuviera), y la rama borrada después:
>
> ```
> atriz-lab         main  4df8fed → 468eace   (42 commits)
> atriz_migracion   main  dfe58db → fa35b54   (20 commits)
> ```
>
> - ✅ **Comprobado ANTES de fusionar y DESPUÉS, sobre `main`:** `tsc` y `eslint`
>   limpios, **1262 pruebas**, `npm run build` correcto (15 rutas), y
>   `comprobar_contrato.mjs` con los cuatro bloques coincidiendo.
> - 🔴 **`Atriz_rvr` NO se ha tocado, y no es un olvido:** allí `main` es **ROS 1**
>   y está 137 commits por detrás de `ros2`, que es la rama por defecto y la
>   buena. Fusionar `ros2` en aquel `main` habría destruido la separación que este
>   proyecto mantiene a propósito.
> - 📝 Las menciones a la rama que quedan por el repositorio están **dentro de
>   entradas fechadas** —CHANGELOG, ESTADO_ACTUAL, el plan— y se conservan: son el
>   registro de lo que era cierto entonces, no instrucciones.
>
> ⚠️ **Lo que la fusión NO significa.** `main` no ha visto un robot: sigue entero
> lo de `atriz-lab/VALIDAR_CON_EL_ROBOT.md` **§6d-§6l**, y dos casillas exigen
> **DOS robots**. Que el código esté en `main` dice que compila, que pasa sus
> pruebas y que su contrato cuadra con el robot — **no que funcione en el aula**.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-17, cierre (PC) · LO DEL ROBOT CONSUMIDO: CONDUCCIÓN IR EN LA
> PANTALLA, Y EL CUELGUE PARCIAL YA VISIBLE EN EL MURO**
> ═══════════════════════════════════════════════════════════════════════════════
> `atriz-lab` **a108416** y **8a4c5f5**. **1262 pruebas**, `tsc` y `eslint`
> limpios, `comprobar_contrato.mjs` con **15 servicios coincidiendo**.
>
> - ✅ **Los tres pasos que la Pi dejó anotados, hechos**: `/set_ir_conduccion`
>   en `contrato.ts`, el mando «Seguir o huir de otro robot» en Acciones, y la
>   prueba que **lee `SetIRConduccion.srv`** en vez de copiar el número.
> - 🔴🔴 **Y esa prueba pasó en verde DOS VECES sin leer nada.** La ruta estaba
>   mal (dos niveles, luego seis; son **cinco**) y las dos veces pasó, porque al
>   no encontrar el fichero se iba por un `return` con un `console.warn`.
>   **La aritmética no era el defecto: el `return` sí.** Una comprobación que se
>   salta cuando no encuentra su fuente **no distingue «todo bien» de «no he
>   mirado»**, y avisar por consola no lo arregla — nadie lee la consola de una
>   tanda en verde. Es la **nº14 del verificador del robot** cometida otra vez,
>   en la sesión que la cita. Ahora **falla**, ensayado en las dos direcciones.
> - 🔴 **La evidencia 129 afirmaba algo de la web que era cierto y no
>   cumplíamos**: «síntoma en el muro: telemetría vieja con latido vivo». **No se
>   podía ver** — el latido de la baldosa es `/motor_status`, que el driver
>   **republica a 1 Hz con su propio temporizador**, así que sigue puntual con el
>   RVR medio colgado: la baldosa salía **en verde con el voltaje congelado**.
>   ✅ Ya lo dice, con umbral **en mensajes perdidos y derivado** (tres
>   publicaciones de `/battery_state` = 90 s), callando si el latido está caído y
>   sin disparar con `null`. Se presenta como **sospecha**: n=1, y un mal rato de
>   WiFi lo produce igual.
> - ⏳ **Todo lo que queda necesita robots delante**: `VALIDAR_CON_EL_ROBOT.md`
>   §6d-§6l. **§6l exige DOS robots y medio metro libre** —el `collision_monitor`
>   no interviene con `seguir`/`huir`— y la casilla que importa es que **se
>   apague solo al vencer el plazo**. Si no lo hace, el diseño entero no sirve.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-17, noche (Pi) · LOS DOS SERVICIOS IR NUEVOS DESPLEGADOS — Y UN
> CUELGUE PARCIAL DEL RVR, CAZADO, DOCUMENTADO Y RECUPERADO**
> ═══════════════════════════════════════════════════════════════════════════════
> El driver de rvr-01 tiene ahora **21 servicios** y la lista blanca **QUINCE**:
>
> - **`/set_ir_baliza`** (`bool encender`): baliza continua que por construcción
>   no puede expresar `following`. TDD 3 pruebas, verificado por efecto.
> - **`/set_ir_conduccion`** (`modo` 0=off·1=seguir·2=huir · `segundos` en
>   (0, 30]): el encargo del PC, con el temporizador de un disparo que lo apaga
>   solo. TDD 10 pruebas (suite del driver 16/16) y los seis puntos del encargo
>   verificados por efecto con control y sellos del journal — **evidencia 128**.
>   El rearme apaga a 4,02 s de la SEGUNDA petición; la parada activa rechaza;
>   la parada en caliente cancela el plazo. ~~👉 Al PC le quedan sus tres pasos.~~
>   ✅ **LOS TRES HECHOS el mismo día** (`atriz-lab` a108416): `contrato.ts` con
>   quince servicios coincidiendo, el mando en `PanelInfrarrojos`, y la prueba
>   que **lee** `SetIRConduccion.srv` — ver el bloque de arriba.
> - **El caudal de `/estado_ir`, medido**: 412-414 B/msg a ~1 Hz = **0,40 kB/s**
>   (0,41 de cota) — evidencia 127. `presupuesto.ts` puede dejar de lanzar.
> - 🔴 **Evidencia 129 — modo de fallo NUEVO del RVR**: al apagar un `following`,
>   el procesador principal calló (telemetría/keepalive muertos) mientras el
>   Nordic seguía ACKeando comandos IR. Ni dormido, ni apagado (batería 96 %),
>   ni el puerto de la 126. Remedio: el botón del RVR; la Pi se reanudó SOLA
>   («el RVR VOLVIÓ tras 19 intentos»). Y de regalo, **el caso degradado de la
>   126 quedó verificado en ocurrencia natural**: latido a 1,000 Hz durante el
>   fallo y sondeo IR en pausa honesta.
> - 📝 Dos confesiones de instrumento: el CLI de `ros2` (~2-4 s/llamada) hizo
>   mentir al primer banco del rearme, y rosbridge deniega en silencio TAMBIÉN
>   en el journal. Las dos, ya en CLAUDE.md/herramientas.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-17, tarde · «LAS PESTAÑAS VAN LENTAS»: ERA `next dev`**
> ═══════════════════════════════════════════════════════════════════════════════
> Medido contra rvr-01 encendido, del CLIC al contenido:
>
> ```
> next dev en frío   1369-1665 ms  ·  caliente  195-238 ms  ·  PRODUCCIÓN  13-39 ms
> ```
>
> - 🔴🔴 **Setenta y cinco veces**, y en producción no había nada que optimizar.
>   Van **nueve** veces que miente el instrumento; la primera en que el
>   instrumento es el entorno de desarrollo entero.
> - 🔴 **La pantalla de carga que se pedía habría empeorado el producto**: un
>   destello sobre una transición de 20 ms. No se hizo, y por qué está escrito.
> - ✅ **Lo que sí costaba, y no era la red:** la cascada `.escalonado` se repetía
>   en cada pestaña (~540 ms, el **96 %** de la espera) → ahora una vez por robot;
>   y las tarjetas arrancaban vacías hasta **30 s** (`/battery_state`) → el
>   `Transporte` recuerda el último mensaje y `useTopicFechado` se siembra de él.
> - 🔴 **El recuerdo muere con el enlace** y el hook obliga a llevar la edad al
>   lado: un robot caído no puede seguir enseñando su último voltaje.
> - ⏳ **Falta el ojo**, y no lo cubre ninguna prueba: `VALIDAR_CON_EL_ROBOT.md`
>   **§6j** — la cascada, `prefers-reduced-motion`, y que un robot caído deje de
>   enseñar el voltaje viejo.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-17 · LA PUERTA DE SESIÓN, MEDIDA EN LAS TRECE RUTAS**
> ═══════════════════════════════════════════════════════════════════════════════
> Sin cambios de producto: lo que cambia es que la puerta pasa de estar escrita a
> estar **medida**, con un comando repetible que vive en `atriz-lab/CLAUDE.md`.
>
> ```
> /   200   ·   /entrar   307 -> /   ·   las otras once   307 -> /?volver=<ruta>
> ```
>
> - 🔴 **La portada no sirve de comprobación:** es pública, así que da 200 con el
>   `middleware.ts` roto. Lo que prueba la puerta es que **las otras doce
>   redirijan**.
> - ✅ **`/robot/99` redirige a la puerta en vez de dar 404, y eso está BIEN.**
>   Parece un fallo —solo hay dieciséis robots— y no lo es: el `notFound()` vive
>   detrás de la puerta, así que un 404 diría a quien no tiene sesión **qué
>   identificadores existen**. Queda escrito para que nadie lo «arregle».
> - 🔑 **`crear-cuenta.mjs` no escribe `rol`**, así que lo que crea se lee como
>   **profesor**. Los dos caminos de la API sí fallan cerrado (individual exige
>   `profesor` explícito, el lote clava `alumno`). ⚠️ **No es un agujero** —quien
>   puede ejecutarlo ya tiene shell en el servidor—, es higiene. 👤 La línea que lo
>   cierra está propuesta y **sin aplicar**.
> - ✅ **Regla 5:** `usuarios.json` está en `.gitignore`; ni un hash en el
>   repositorio, que importa porque `atriz-lab` es público.
> - ⏳ **Las once pantallas de dentro NO se han visto** en esta tanda: la barrida
>   mide la puerta, y pasar de ella exige credenciales.
>
> **✅ Y EL MISMO DÍA EL PI CERRÓ LOS DOS ENCARGOS**, así que lo que el bloque de
> abajo pedía **ya está hecho** y lo que queda es del PC:
>
> - ✅ **`/estado_ir` medido: 412-414 B/msg a ~1,0 Hz = 0,40 kB/s por robot** (n=2,
>   con un control que reprodujo la evidencia 110 **al byte**). 🔴 Y mi estimación de
>   ~421 B quedó **refutada por su propia medición**: mandan los `float32`
>   serializados a JSON, no el nombre del modo. Presupuesto del muro con los cuatro
>   topics: **~1,24 kB/s por robot, ~19,8 los dieciséis**. Evidencia 127.
> - ✅ **`/set_ir_baliza` desplegado en rvr-01** y en la lista blanca: `bool encender`,
>   así que **por construcción no existe la petición que produzca `following`** — que
>   era la condición. Verificado por efecto en vivo.
> - 📌 De rebote, un hallazgo que corrige a este repositorio: **rosbridge deniega en
>   silencio TAMBIÉN en el journal** (3 denegaciones provocadas → 0 líneas). El
>   epílogo de `probar_lista_blanca.py` aconsejaba un `grep` que no podía encontrar
>   nada; ahora manda comprobar por efecto.
>
> **✅ LAS TRES COSAS DEL PC, CERRADAS EL 2026-08-17** (`bc02eaf`, `cfe980b`):
>
> 1. ✅ **`/estado_ir` anotado** (0,40 kB/s). ⚠️ Tener la cifra **no** es llevarlo al
>    muro: subiría el coste por robot un 48 % y eso es decisión de producto, no un
>    hueco que rellenar porque ya se pueda. `TOPICS_MURO` sigue con tres.
> 2. ✅ **La baliza IR ya está en «Acciones»**, con los dos códigos del `.srv`.
> 3. ~~🔴 **Corregir la frase de la portada.**~~ ✅ **HECHO el 2026-08-17**
>    (`atriz-lab` 50c5597), pedido directamente por el usuario. Eran **dos** frases
>    falsas, no una. Hoy dice «la exige 1 de los 16» y la concordancia de número se
>    **deriva**, para que el día que valga 16 siga bien escrita. 👤 Cuando la Fase B
>    llegue a más robots: subir `ROBOTS_QUE_EXIGEN_CREDENCIAL`, una línea.
>
> ✅ **`motion` DESINSTALADA** —era lo único que separaba la rama de `main`—, con una
> prueba que impide que vuelva sin la guardia contra lo infinito.
>
> **⏳ Y a partir de aquí, todo lo que queda necesita un ROBOT DELANTE:**
> `atriz-lab/VALIDAR_CON_EL_ROBOT.md` **§6d-§6k**. Dos casillas —infrarrojos y baliza—
> **exigen DOS robots**: el único testigo de que se emitió es el otro robot.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-16 · F5 CERRADA — siete pantallas rehechas, y el instrumento que
> miraba mentía**
> ═══════════════════════════════════════════════════════════════════════════════
> Ocho commits en `atriz-lab`, rama `rediseno-2026-08` (`2dca601`..`ce40b7e`).
> **1210 pruebas**, `tsc` y `eslint` limpios, siete pantallas vistas en un navegador
> de verdad contra el doble. **Nada de esto toca el robot.**
>
> - 🔴🔴 **Lo primero, porque contamina lo demás: la herramienta de capturas
>   devolvía imágenes de OTRA pantalla**, enteras y nítidas. El CSS decía
>   `rgb(246, 245, 243)` y el píxel del PNG `rgb(24, 26, 27)`. Tres caminos lo
>   provocan y el tercero —desplazar la página— envenena hasta la captura simple.
>   Van **ocho** veces que miente el instrumento en este proyecto, y es la primera
>   en que el instrumento es el que existe para MIRAR. Hoy `recorte.mjs` compara la
>   foto con el token de fondo y **avisa** cuando no cuadran.
>   📝 Perseguirlo por parecido costó **cuatro atribuciones falsas** seguidas; lo
>   cerró una tabla cambiando una cosa cada vez.
> - **Muro, Navegar, Medidas, Conducir, Acciones, Lo que ve, Taller y Si no
>   obedece.** El detalle, en `CHANGELOG.md`.
> - 🔴 **Defectos de producto encontrados mirando, no leyendo:** el muro decía
>   «MIRAR 15» sobre quince baldosas que decían «no llegó»; la rueda de color
>   **descartaba el radio** y dibujaba un eje de saturación no seleccionable en el
>   **51,8 %** de su área; «Apagar» **destruía la saturación**; el tope de 0,20 m/s
>   era **el único de toda la cadena** mientras el Taller ya daba 0,40 por el mismo
>   topic; el teclado de conducir era **un segundo mapeo sin pruebas**; y
>   `dentroDeLoMedido` **no se llamaba en ningún sitio**.
> - 🔴🔴 **Y uno que sigue abierto: la portada afirma de los dieciséis lo que hoy
>   hace uno.** Dice que «el robot comprueba» la credencial; la Fase B está cerrada
>   **en rvr-01**. Quince robots aceptan hoy una conexión sin credencial.
>   👤 Revisado y propuesto el arreglo; **sin aplicar**, a la espera de decidir si
>   se corrige la frase o se despliega la Fase B a los otros quince.
> - ⏳ **Nada ha visto un robot.** Las casillas nuevas están en
>   `atriz-lab/VALIDAR_CON_EL_ROBOT.md` **§6d-6h**, y una **exige DOS robots**.
> - ~~👤 **Dos cosas para la Pi**: medir el caudal de `/estado_ir` y decidir si se abre
>   una **baliza IR**.~~ ✅ **LAS DOS CERRADAS POR EL PI EL 2026-08-17**, el día
>   siguiente: 0,40 kB/s medidos y `/set_ir_baliza` desplegado. Ver el bloque de
>   arriba.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-15 · EL TALLER VALIDADO CONTRA EL ROBOT, Y DOS PENDIENTES CERRADOS
> (evidencias 118-123)**
> ═══════════════════════════════════════════════════════════════════════════════
> Día largo, con el robot delante y un navegador de verdad. Lo que quedó:
>
> - ✅ **EL TALLER, CERRADO DE EXTREMO A EXTREMO.** Las **16 casillas** de
>   `VALIDAR_CON_EL_ROBOT.md` §4, contra rvr-01 y con navegador. Incluida la que nadie había
>   medido nunca: **un Ctrl-C por el PTY para al robot en 1,9 cm de mediana (n=5)**, contados
>   **desde el clic del navegador** — WiFi, agente, `killpg` y deceleración incluidos
>   (evidencia 118).
> - 🔴 **Y aparecieron OCHO fallos de producto, varios en código que ya estaba «en verde»**:
>   una regresión mía que **mataba la página entera** (`base64url` viajando al navegador desde
>   un módulo `'use client'`), `atriz.py` **apagando el barrido de otro** 3 de 5 veces (un plazo
>   de 1 s contra una latencia de descubrimiento DDS de hasta 1,7 s), y un **doble que mentía
>   sobre su manejo de errores** — daba verde sobre un camino que en el robot devuelve HTTP 500
>   (evidencias 119 y 120).
> - 🔴🔴 **`/initialpose` ESTABA DECLARADO Y SIN CONSTRUIR, y al construirlo el gesto MOVIÓ EL
>   ROBOT hasta enredarlo** (evidencia 121): un arrastre dispara además un `click`, y la guarda
>   escrita para impedirlo **se desactivaba a sí misma dos líneas antes**. El arreglo no puede
>   ser un `useState`; va en un `ref`, que se lee síncrono.
> - ✅ **A12 CERRADO: el log se escribía DOS VECES** (evidencia 122). `/var/log` de **106 a
>   40 MB**, retención de **23 h a ~7 días**, `rsyslog` parado. Y `ForwardToSyslog=no` **no
>   basta** —`imklog` lee el anillo del kernel sin pasar por journald—. Va en `fase_1`, así que
>   **la imagen dorada lo lleva sin tocar nada más**.
> - ✅ **A13 CERRADO, y su premisa RETIRADA** (evidencia 123): **apagar el RVR NO reinicia la
>   Pi** —`boot_id` idéntico, medido con control—. Lo que la reinicia es **cortar** la
>   corriente, o sea **manipular el robot: cinco veces en un día, sin un error en ningún log**.
>   Arranque en frío medido: **31 s** de la corriente a robot útil.
> - 📝 **Tres correcciones a afirmaciones MÍAS**, todas escritas sin medir: que
>   `MaxRetentionSec` diera retención (solo recorta), que apagar el RVR reiniciara la Pi, y un
>   control de retención que **daba rojo sobre el robot recién arreglado**. Van doce fallos
>   propios del verificador.
> - 📌 **Y dos veces el mismo patrón: la respuesta ya estaba en el repositorio.** La refutación
>   de la premisa de A13 llevaba escrita desde el 2026-08-06 sin cruzarse con ella, y el drop-in
>   del journal nació en un heredoc que el propio guion prohíbe catorce líneas más arriba.
>
> ✅ **Y A7 · Fase B se cerró EL MISMO DÍA, más tarde** (evidencia 124): **rvr-01 ya exige un
> testigo firmado para abrir rosbridge**, y la web se lo manda. Verificado de punta a punta con un
> navegador — telemetría viva en pantalla. Era lo que bloqueaba la Fase 5. 🔴 No hizo falta el
> proxy que el diseño pedía: `RosbridgeWebSocket` se importa por nombre, así que se parchea y se
> ejecuta el nodo original — **cero relevo** en la ruta de 80,7 kB/s por robot.
>
> **Lo que queda:** A5 (¿es correcta la pose fijada? — necesita mapa fresco), A8 (el aula), y de
> A7: **TLS** (el testigo y la telemetría viajan en claro) y **los otros 15 robots**, que llegan
> con la imagen dorada.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-14 · EL DÍA EN QUE EL ROBOT APRENDIÓ A CURARSE SOLO (evidencias 109-115)**
> ═══════════════════════════════════════════════════════════════════════════════
> Sesión remota (el robot en casa del usuario), tratando uno a uno los pendientes que no
> exigían el aula. Lo que quedó:
>
> - 🔴 **El mudo en DDS REAPARECIÓ — y desarma la explicación que teníamos** (evidencia 109):
>   esta vez los nodos nacieron **después** del salto de reloj, con las esperas cumplidas, y
>   DDS no cruzó igual. El arranque bueno y el malo son **indistinguibles en el journal**:
>   intermitente, causa próxima sin conocer (2 de 3 arranques fríos).
> - ✅ **Y por eso existe el VIGÍA DE DDS** (evidencia 113): `atriz-vigia-dds`, ExecStartPost
>   de atriz-robot — si `/estado_robot` no llega en 90 s, SIGINT al proceso principal y
>   `Restart=always` lo levanta. **Una vez por arranque, fallo abierto.** Sus dos primeros
>   disparos fueron **falsos positivos** (el lanzador sin `ROS_DOMAIN_ID` escuchaba en el
>   dominio 0) y la marca de una-sola-vez los contuvo — la lección: **la prueba fiel de un
>   ExecStartPost es con `env -i`**, no heredando tu shell.
> - ✅ **El LIDAR desenchufado también se cura solo** (evidencia 115): `atriz-lidar-reenganche`
>   por udev, verificado desenchufando de verdad — **~22 s a robot útil**. 🔴 Y cayó una
>   atribución falsa: el adaptador se alimenta **de la Pi** (lo que re-enumera es desenchufar
>   el cable, no apagar el RVR — testimonio del usuario + cero eventos USB medidos).
> - ✅ **Conflicto 2 CERRADO con la decisión B** (evidencia 114): nav/slam **devuelven el
>   barrido al estado que encontraron** (`on-recordando` + marca en `/run/atriz`). El alumno
>   que lo tenía encendido de antes ya no se queda ciego al pararse la nav. ⚠️ No cubre a
>   quien enciende *después* de arrancada la nav: para ese sigue el aviso de la web.
> - ✅ **El botón de Nav2, de extremo a extremo por primera vez** (evidencia 111): FUNCIONANDO
>   a los 28,4 s por `/estado_navegacion` (n=3 con B2), paro limpio en 10,5 s. Y el **latch se
>   limpia solo a los ~5 min** (evidencia 112) — la web puede decir «espera 5 minutos», y
>   `nav_latcheado=true` se vio por primera vez en su estado real.
> - ✅ **El caudal de `/estado_robot`, medido: 0,35 kB/s** (evidencia 110) — el «0,03» que
>   circulaba era el de `/battery_state` copiado, doce veces corto. El muro del PC queda con
>   los tres topics medidos (~0,83 kB/s por robot).
> - 🔴 **Dos retractaciones mías, corregidas en sitio:** el «negarse sin mapa: sin implementar»
>   (el guardia existía desde el 07, evidencia 80) y la atribución del LIDAR de arriba.
>
> - ✅ **Y el driver dejó de mentir con el RVR apagado** (evidencia 116, cierra el ⏳ de la 52):
>   «el RVR VOLVIÓ» solo al llegar una muestra, espera creciente 3→6→12→24→48→60 s medida en
>   el journal con un apagado real, y el detalle de `nav_latcheado` con el «caduca sola en
>   ~5 min». **Con esto, la tabla de pendientes del lado Pi quedó ENTERA en cero.**
>
> ⏳ **Lo que queda espera al aula:** Bloque C entero (mapa, AMCL con objetos, hueco 43/45),
> práctica 63, foto del conector USB, prueba de aceptación de un tirón, y la Fase 6 (imagen
> dorada) — que ahora llevará de serie los dos vigilantes y el barrido-que-devuelve-el-estado.
>
> 🆕 **Y EN LA MADRUGADA DEL 15, EL TALLER (el terminal del alumno) QUEDÓ AUDITADO Y VIVO EN
> rvr-01** (evidencia 117): la mitad-robot que el PC escribió sin poder ejecutarla se validó
> aquí — **cinco fallos cazados con experimento** (dos EN VIVO: el `PYTHONPATH` pisado que
> mataba `import rclpy`, y la cosecha doble que perdía el código de salida), 19 casillas de
> VALIDAR §4 en verde, y **la práctica 05 corriendo de punta a punta por el agente** con el
> sensor real. `atriz-agente` instalado y habilitado por `fase_7`, con clave Ed25519 **de
> prueba** — al PC le quedan la clave real y el navegador de verdad (lista completa en
> `ESTADO_ACTUAL.md`, «PARA TU PRÓXIMA SESIÓN»).
>
> ✅ **Y ESA MISMA TARDE EL PC LAS CERRÓ: LAS 16 CASILLAS DEL TALLER, EN VERDE** (evidencias
> 118-120). Clave real publicada y cruce Next→Python verificado por efecto (`4403` antes,
> `atriz_bienvenida` después); el requisito del PTY medido **desde la pantalla** (una línea cada
> **~510 ms**); `01_avanzar.py` a **60,0 cm de cinta contra 60,3 de odometría**; el `SIGINT` por
> PTY medido **por primera vez** (1,9 cm de mediana, n=5); y los cuatro `input()` de la práctica 4
> contestados desde el navegador.
> 🔴 **Y con un navegador de verdad aparecieron CINCO fallos más**: el `base64url` que tumbaba la
> página entera, la insignia que decía «listo» sin enlace, el `soy_el_dueno` que el agente
> difundía a todos por igual, `atriz.py` **apagando el barrido ajeno 3 de cada 5 veces** —dejaría
> ciega una navegación, en silencio— y un `HTTP 500` donde debía ir un cierre con motivo. Los
> cinco arreglados y verificados con control; el del barrido, **8 de 8 después** contra 2 de 5.
> 📝 Y la lección que dejó, porque vale para todo el proyecto: **dos arneses independientes pueden
> tener el MISMO punto ciego si los dos se escribieron desde el caso de uso feliz.**
>
> **Del Taller no queda nada pendiente entre el PC y la Pi.**
>
> 🟡 **Y la FASE 6 quedó LISTA Y EN ESPERA DE AUTORIZACIÓN (👤 decisión del 2026-08-14):** el
> pre-vuelo entero está hecho, `fase_6` endurecido antes de su estreno, y el procedimiento con
> sus cuatro consecuencias escrito en **`03_operacion/FLOTA.md`** («la imagen dorada está
> lista»). **No se ejecuta hasta que el usuario lo autorice explícitamente** — ni por agente ni
> por inercia: ejecutarla borra Claude Code, el token de git, los mapas y la identidad de rvr-01.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-13 · SEGUNDO DÍA EN EL LABORATORIO: EL BLOQUE ROJO DE ABAJO QUEDÓ CERRADO**
> ═══════════════════════════════════════════════════════════════════════════════
> Cinco evidencias (104-108) cierran casi todo lo que el bloque rojo de abajo tenía abierto:
>
> - ✅ **El arranque en frío real, visto entero** (evidencia 104): el reloj saltó **+22 h 15 min**
>   y las dos esperas acotadas de `atriz-robot.sh` **actuaron** (red tras 2 s, reloj antes del
>   launch) — DDS cruzó. n=1 sin contrafactual, pero es justo el escenario del incidente mudo.
> - ✅ **A11 CERRADO** (evidencia 105): «Ignoring the source» es **transitorio y con aritmética
>   exacta** — solo aparece cuando el último `/scan` es viejo porque el barrido está apagado
>   a propósito, que es el reposo normal. Con nav activa y barrido encendido: **0**. Y sin
>   `/scan` el monitor **bloquea**, no deja pasar: la capa de seguridad no está inerte.
> - ✅ **M10 MEDIDO** (evidencia 106): `PartOf=`+`Requires=` **vuelve con timestamp nuevo tras
>   `kill -9`** del proceso base; `BindsTo` (y «ambas») no vuelven. La unidad instalada ya era
>   `PartOf=`+`Requires=` desde el 2026-08-07 — el «sigue con BindsTo=» de abajo estaba rancio.
> - ✅ **B2/B3 CERRADOS — `atriz-nav` corrió BAJO SYSTEMD por primera vez** (evidencia 107):
>   **27,80 y 27,84 s** desde `systemctl start` hasta aceptar objetivos (n=2, Δ 0,04 s; holgura
>   4,3× sobre `TimeoutStartSec=120`). Y el **botón muerto confirmado n=2**: un start sin mapa
>   quema el `StartLimitBurst` — con el agravante de que `systemctl start` **devuelve 0** y la
>   unidad llega a `Started` antes de que el wrapper vea que no hay mapa. ~~🔴 Consecuencia de
>   diseño decidida y **sin implementar**: el servicio ROS debe **negarse antes** de llamar a
>   systemctl si no hay mapa.~~ ✅ **RETIRADO el 2026-08-14: ese guardia YA EXISTÍA** —
>   `supervisor_navegacion` se niega antes de systemctl desde el 2026-08-07, con los rechazos
>   verificados por efecto (evidencia 80). El negativo se escribió sin mirar el código (B3 midió
>   el camino directo a propósito). Lo que B3 aporta: ese guardia es lo único entre la web y el
>   latch.
> - ✅ **La sesión física docente, EN VERDE** (evidencia 108): `avanzar()` 58/59 cm, `girar(90)`
>   ~90° con transportador, Ctrl-C **5 de 5** (~1 cm de arrastre), `luces()` visto, y
>   `distancia_frontal()` a 1,1 cm de la cinta. ⏳ Solo queda la **práctica 63** (no había línea);
>   `mediciones_banco/calibrar_claro.py` quedó listo para ese día.
>
> ⏳ **Lo que el día dejó abierto:** el **mapa del aula** (no se llegó a mapear — Bloque C entero
> pendiente), ~~la decisión del **barrido-apagado-al-parar-nav** (conflicto 2, ahora con dato)~~
> (✅ decidida B e implementada el 14, evidencia 114: las unidades devuelven el estado que
> encontraron),
> ~~el «negarse sin mapa» del servicio ROS~~ (✅ retirado el 14: ya existía desde el 07,
> evidencia 80), y ~~si `StartLimitIntervalSec=300` limpia solo el contador~~ (✅ medido el 14,
> evidencia 112: **sí se limpia solo** a los ~5 min del último arranque). Y los cuatro fallos
> del instrumento de medida están contados en la evidencia 107 y arreglados en
> `scripts/medir_arranque_nav.sh`.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🔴 **LO PRIMERO: ejecuta `bash scripts/medir_recuperacion.sh` EN LA PI**
> ✅ *(pasado el 2026-08-13 sin hallazgos nuevos; el bloque se conserva como historia)*
> ═══════════════════════════════════════════════════════════════════════════════
> El **2026-08-06**, al poner el RVR a cargar con la Pi viva, el robot se quedó **sano por todos
> los indicadores habituales y mudo en lo que importaba**: `/odom` 95 msg en 6 s, `/estado_robot`
> bien, `rvr_responde: true`, `/tf` a 265 en 16 s — y **`/scan` a 0 y `/map` a 0**.
>
> Se concluyó «el driver se reinició» a partir de una prueba **indirecta**. **Encajan VARIAS
> explicaciones** y el journal las separa.
>
> 🔴🔴 **M6 QUEDÓ IRRECUPERABLE, y no por lo que se pensaba.** El guion preguntaba mal —usaba
> `NRestarts`, que es **del arranque actual**, y su guía decía «0 → el driver no se reinició»:
> un falso negativo—. Se arregló acotando por arranque… y entonces se vio que **el dato ya no
> existe**: los arranques anteriores salen en `--list-boots` **vacíos**, 0 líneas. La rotación
> se los comió. El registro más antiguo es del **4 de agosto**.
>
> **Y la ironía es del proyecto:** `SystemMaxUse=32M` lo puso `fase_1_higiene_so.sh` por una
> buena razón medida (784 MB sin límite daban 47 s de bloqueo I/O en 42 min ociosos), y es lo
> que destruyó la evidencia del único incidente que se ha querido investigar.
>
> 📌 La sospecha que ya no se puede comprobar: la Pi **reinició a las 16:17**, ocho minutos
> antes de relanzarse SLAM. Sería **la Pi entera**, no el driver — se alimenta del USB del RVR.
> ⚠️ **PRECISADO el 2026-08-15 (evidencia 123):** que se alimente del USB es cierto, pero **apagar
> el RVR NO la reinicia** — medido con control: `boot_id` idéntico y `uptime` subiendo. Lo que la
> tira es **cortar** la alimentación (quitar la batería, manipular el robot). 🔴 Y eso resultó ser
> **el caso normal**: cinco cortes en un solo día, los cinco por manipulación, sin un error en
> ningún log y con los bits de sub-tensión a cero.
>
> 🔴 **Y esto destapó dos cosas más importantes que M6**, las dos abiertas:
> **A11** · el `collision_monitor` escribe «Ignoring the source» sobre el LIDAR. Si es
> sostenido, **la capa de seguridad está inerte**. Medido después: el reloj está bien (0,5 s de
> desfase) y `/scan` va a 11,7 Hz, así que la hipótesis es un salto de reloj al sincronizar NTP
> —la Pi no tiene RTC—. ~~**SIN CONFIRMAR**, y el discriminante es un comando (ver el plan).
> **Va por delante de M10.**~~ ✅ **CERRADO el 2026-08-13 (evidencia 105): es transitorio, con
> aritmética exacta** — cada aparición cae en el instante en que la última muestra de `/scan`
> era vieja porque el barrido estaba apagado a propósito. Con nav activa y barrido encendido:
> 0 apariciones. Y la hipótesis del NTP era falsa: era la edad del `/scan`, no el reloj.
> ~~**A12** · con 32 MB este robot no conserva un incidente ni dos días. ⚠️ Y subir el tope **no
> garantiza retención**: eso lo dan `SystemMaxFiles` o `MaxRetentionSec`.~~
> ✅ **CERRADO el 2026-08-15 (evidencia 122).** Retención medida: **23 h 08 min**, peor de lo que
> decía esta línea. Y **la advertencia era AL REVÉS y mía**: `MaxRetentionSec` es una edad
> **máxima** y `SystemMaxFiles` un número máximo de ficheros — los dos solo pueden **RECORTAR**.
> Lo que da retención es `SystemMaxUse ÷ ritmo`, y nada más. Con 37 MB/día medidos, **256M ≈ 7
> días**.
> 🔴 **Y el tope de 32M no controlaba ni la mitad de las escrituras:** Ubuntu trae
> `ForwardToSyslog=yes` y rsyslog estaba activo, así que **cada línea se escribía dos veces** —
> `/var/log` en **106 MB**, el triple del tope, y fuera de su alcance. 🔴 **Y quitar el reenvío
> tampoco basta**: rsyslog carga `imklog`, que lee el anillo del kernel **sin pasar por
> journald**. Medido con control en las dos direcciones; hubo que **parar el servicio**.
> ⚠️ **La retención sigue sin estar garantizada** —es un cociente, y una inundación como la del
> ydlidar la hundiría—: son 8× más margen, no una promesa. Por eso el verificador la mide **por
> efecto**, no lee el parámetro.
>
> ~~**M10 sigue en pie y NO caduca:** ese guion mide si systemd propaga un **reinicio** a una
> unidad atada, de lo que depende que
> `atriz-nav.service` —que hoy usa `BindsTo=` + `Restart=on-failure`— no se quede muerta.~~
> ✅ **M10 MEDIDO el 2026-08-13 (evidencia 106):** `partof`+`Requires` **vuelve con timestamp
> nuevo** tras `kill -9`; `bindsto` y «ambas» quedan `inactive`. Y el «hoy usa `BindsTo=`»
> llevaba rancio desde el **2026-08-07**: la unidad instalada es byte-idéntica a la del repo,
> con `PartOf=` + `Requires=`.
>
> ~~⚠️ **NO levantes `atriz-nav` antes de M10.** Si el driver se reinicia a mitad, la navegación se
> para, **no vuelve**, y apaga el barrido de camino. La web no puede levantarla.~~
> ✅ **OBSOLETO desde el 2026-08-13:** M10 pasó y `atriz-nav` **ya corrió bajo systemd** (B2/B3,
> evidencia 107) — 27,8 s hasta aceptar objetivos, n=2.
>
> El análisis entero, con cuatro decisiones que son tuyas, en
> [`00_auditoria/planes/2026-08-06-plan-slam-color-arranque.md`](00_auditoria/planes/2026-08-06-plan-slam-color-arranque.md).
> El incidente, en
> [`00_auditoria/planes/2026-08-06-recuperacion-tras-apagar-el-rvr.md`](00_auditoria/planes/2026-08-06-recuperacion-tras-apagar-el-rvr.md).
>
> ✅ **Y lo que sí quedó cerrado el 2026-08-06, contra rvr-01:** conducir desde el navegador de
> punta a punta (**cinta 30,0 cm contra 29,7 de `/odom`**, 1,0 % de error); la lista blanca
> **deniega en silencio** (con control positivo); la parada de emergencia **puesta y liberada
> desde la web** con el robot confirmándolo; y el cliente ya habla **acciones**.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-09 · LA WEB, VALIDADA CONTRA rvr-01 — y tres fallos suyos**
> ═══════════════════════════════════════════════════════════════════════════════
> Pasada entera de **`atriz-lab/VALIDAR_CON_EL_ROBOT.md`**, que es donde está el detalle. Lo
> construido los días 07 y 08 se había hecho contra un doble; esto es el contraste.
>
> ✅ **Los seis estados de SLAM**, arrancado y parado **desde la web**: `apagado → arrancando ·
> 4 → 9 → 14 s → funcionando` en ~18 s. `CIEGO` forzado apagando el barrido con SLAM vivo, y
> `MUDO` **apareció solo** al parar. `CIEGO` es el que justifica el diseño: es exactamente el
> estado que `systemctl is-active` llamaría `active`.
>
> ✅ **Las cuatro casillas del 2×2 del sensor de color**, por la interfaz. La misma pantalla roja
> da `R/G = 5,0` con la luz apagada («es rojo») y **`0,57` con ella encendida** —el sensor lee
> más verde que rojo— y ahí la pantalla **se calla**.
>
> 🔴 **Tres fallos de la web, encontrados por el robot:** un «es verde» sobre **ruido**
> (`R=0 G=1 B=0`); un acuse que decía «espera» un minuto después de haber llegado; y **el
> apagado automático de la luz, que NO saltó** —14 min 38 s encendida sin lector, apagada a
> mano—. Los tres corregidos; el tercero se convirtió en *«apágala tú»*, porque una promesa
> incumplida sobre la batería es de las peores que puede hacer esa interfaz.
>
> ✅ **RESUELTAS POR EL ROBOT EL MISMO DÍA** (evidencia 87), y las dos con más fondo del que yo
> les vi: `get_param` **sí funciona** —el nombre va `<nodo>:<parámetro>`, mi llamada estaba mal
> formada— y debajo había algo peor: **esa llamada mata rosapi ~30 s después**, con `systemctl` en
> verde. Arreglado con `respawn`. Y `ATRIZ_MAPA` apunta a `/home/sphero/mapas/cuarto3.yaml`.
> 🔴 **Mi conclusión —«la web no puede preguntar por la configuración del robot»— era un rediseño
> entero apoyado en un error mío.** Sin consecuencias: la web **no usa `rosapi`** en ningún sitio.
>
> 📌 **Y AHORA DOS QUE LE DEVUELVO AL ROBOT**, del mismo tipo:
> 1. 🔴 **RETIRADA: esta devolución era falsa y el error fue mío.** Dije que el umbral de 7 días
>    «no existe en `verificar_robot.sh` ni en ningún otro script». **Existe**, en la línea 1459
>    (`-le 7`). Mi `grep` buscaba `7 días`, `604800`, `-mtime +7`: ninguno podía casar con `-le 7`
>    sobre una variable. **Un negativo sacado de una búsqueda que no podía encontrarlo.**
>    ✅ Lo que sí aguanta —y el robot lo acepta— es la **conclusión**: la pantalla no lleva umbral
>    porque `mapa_edad_s` es el `mtime` y copiar un mapa viejo lo rejuvenece, así que el semáforo
>    daría verde en el caso peor. En el **verificador** el umbral sí es razonable: es un aviso a
>    quien está junto al robot. **El mismo número puede ser correcto en un sitio y engañoso en
>    otro.**
> 2. **`comprobar_contrato.mjs` NO se puso en rojo** al añadir los campos, y el robot contaba con
>    que sí. Compara **nombres** de topics, servicios y tipos —de los tipos, solo que el `.msg`
>    exista—: **añadir campos a un `.msg` le es invisible.** Fiarse de ese rojo habría dejado los
>    dos campos sin llegar a la pantalla, con todo verde.
>
> 📌 **Lo de antes, conservado:**
> 1. **`ATRIZ_MAPA` apunta fuera de la ruta por defecto** — el directorio del código está
>    **vacío** en rvr-01 mientras `hay_mapa` dice `true`. No es un fallo, pero no está escrito
>    en ningún documento del PC y quien lea el código deduce la ruta equivocada.
> 2. **`rosapi/get_param` revienta**: `result=true` con `successful=false` y
>    `cannot access local variable 'node_name'`. Si `rosapi` no sirve para leer parámetros, la
>    web no puede preguntar por la configuración del robot y todo tiene que venir por topic o
>    servicio propio.
>
> ⏳ **Sin medir, con el motivo escrito:** el **tope duro de 900 s** de la luz (lo apagué a menos
> de dos segundos de cuando habría vencido), **`NO_SE_SABE`** (exige parar el supervisor por
> SSH) y **1c** (decisión de no mover el mapa recién hecho por una rama booleana).
> 🔴 **`BLOQUEADO` no está en esa lista: es inalcanzable desde la web A PROPÓSITO** — el
> supervisor se niega antes de llamar a `systemctl`. Mi lista de validación decía lo contrario
> y se corrigió **antes** de pedirle al usuario que tocara el robot.
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕 **2026-08-07 · NAV2 NAVEGA DE VERDAD, Y ERA EL MAPA**
> ═══════════════════════════════════════════════════════════════════════════════
> El robot se movió solo por primera vez en este proyecto, y con ello se abrió el problema que
> ocupó el día: **Nav2 declaraba el objetivo cumplido estando a 41 cm de él**, con 10 cm de
> tolerancia. Tres tandas y cuatro evidencias (81, 82, 83, 84) para separar **dos fallos
> distintos con el mismo síntoma aparente**:
>
> | | causa | arreglo | evidencia |
> |---|---|---|---|
> | el marco `map→odom` rotaba **98°** | la recuperación de «robot secuestrado» de AMCL | `recovery_alpha_slow/fast` a **0.0** | 82 |
> | AMCL erraba **45 cm** con el marco ya quieto | **el mapa** | remapear el sitio | 84 |
>
> 🔴 **Arreglar el primero dejó el segundo en pie**, y durante un rato pareció que no había
> mejorado nada. Y el segundo **solo se ve con dos distancias de cinta**: con la diagonal sola,
> odometría y AMCL parecían igual de buenas (2 cm) estando a 45 cm la una de la otra.
>
> ```
>                           mapa rancio    tanda 1    tanda 2
>   error de AMCL              45,0 cm      8,9 cm    15,2 cm
>   distancia real al objetivo 41,3 cm      6,1 cm    11,8 cm   (tolerancia 10)
>   ¿dentro de los 10 cm?        🔴 NO       ✅ SÍ      🔴 NO
>   lo que dijo Nav2           ✅ ÉXITO    ✅ ÉXITO   ✅ ÉXITO   <- 🔴 LAS TRES
> ```
>
> ✅ **Aguanta: el mapa era la causa dominante**, y es un salto enorme respecto a la evidencia 83,
> que decía que **no se podía prometer navegación útil**.
>
> 🔴 **RETIRADO el 2026-08-08: «el "llegué" de Nav2 ya es cierto».** Se escribió con n=1 y la
> réplica lo desmintió — `SUCCEEDED` a **11,8 cm** con 10 de tolerancia. **La cifra honesta es
> ~10-12 cm.** Y lo que de verdad importa para la web: **Nav2 dijo ÉXITO en las tres**, a 6,1, a
> 11,8 y a 41,3 cm — ninguna promesa de precisión puede apoyarse en el desenlace del objetivo.
>
> 🔴 **AMCL es peor que la odometría por un factor de 4**: 8,9 y 15,2 contra 4,2 y 2,2. La
> odometría lleva **n=3 contra cinta**: 1,5 · 4,2 · 2,2 cm.
>
> 🔴 **Y una condición operativa nueva, escalada a todo el repositorio: el mapa tiene que ser del
> sitio y estar FRESCO.** No hay ningún síntoma cuando no lo está. Por eso ahora:
> `fase_6_preparar_imagen_dorada.sh` **borra `~/mapas` y vacía `ATRIZ_MAPA`** (clonar el mapa del
> robot de referencia lo repartiría a 16 sitios distintos), `verificar_robot.sh` comprueba que el
> `.pgm` exista y **avisa a los 7 días**, y está escrito en `maps/README.md`,
> `ARRANQUE_NAVEGACION.md` y `CLAUDE.md`.
>
> 📝 De regalo, dos datos: la **deriva acumulada de la odometría** es **3,3 cm** tras un ciclo
> completo con giros de 125°; y los abortos de `follow_path` que parecían falta de asentamiento
> eran **la Pi saturada** (load 8,39/4 núcleos) — encadenar `ros2 service call` levanta un
> intérprete por llamada. **El instrumento competía por el recurso que medía**, y por eso la
> prueba vive ahora en **un solo proceso** (`mediciones_banco/prueba_navegacion_completa.py`).
>
> ═══════════════════════════════════════════════════════════════════════════════
> 🆕🔴 **2026-08-09 · UN OBSTÁCULO A MENOS DE 18 cm INMOVILIZA AL ROBOT POR COMPLETO**
>
> No gira, no avanza y **ni siquiera puede alejarse** (evidencia 93). Medido con la pared **detrás**
> a 16,8 cm y 188 cm libres delante: `avanzar -> 0.0 cm · girar -> 0.0° · retroceder -> 0.0 cm`.
> `approach` escala el mando entero por el tiempo hasta colisión y con un punto **ya dentro** del
> círculo ese factor es 0, **sin mirar si el movimiento acerca o aleja**. Sólo sale a mano.
> → ✅ **Y girando no rozaría nada**: con el monitor puenteado, 359,6° y 358,8° de 360 en 12,6 s,
>   sin tocar la pared (el usuario mirando). Radio circunscrito **14,06 cm** (18 × 21,6 cm medidos con cinta, LIDAR centrado) contra un círculo de 18:
>   **el monitor es más gordo que el robot.**
> → 🔴 **RETIRADO lo de «causa aislada bajando `radius` en caliente»:** `Aproximacion.radius` es
>   **INERTE en caliente** —`param set` lo guarda, el nodo NO reconstruye el polígono—, demostrado
>   con 0,30, que debería frenar mucho antes y da el perfil idéntico. Y aquella prueba tenía además
>   la pared a 18,3 cm, no a 16,8: ya estaba fuera del círculo. **Cambiar el radio exige editar el
>   YAML y reiniciar (👤 `sudo`), o sea es un cambio de imagen dorada, no un botón.**
> → ✅ **Y lo que sí queda medido: el hueco al parar con el radio real (0.18) a 0,25 m/s son
>   9,3 · 9,4 · 9,3 · 9,4 cm** (n=4, 1 mm de dispersión). Cuadra con el modelo y con los 9,9 cm del
>   fichero 17. El recorte es lineal: `mando ≈ 0,0125 × (distancia_LIDAR − 18 cm)`.
> → 🔴 **Desmiente el título del cap. 12.5 del manual** («No queda atrapado») y matiza la
>   evidencia 19 («PUDO SALIR: retrocedió 58 cm»). ⏳ Por qué unas geometrías salen y otras no:
>   **NO VERIFICADO** — falta repetirlo con la pared delante y al lado.
> → ⏳ **La configuración NO se ha tocado.** `radius` fija a la vez el hueco al parar y el pasillo
>   mínimo, y el 0.18 lo respalda «para a 20,8 cm sin chocar» de la aceptación. 👤 **Decisión tuya.**
> → 🔴 **Regla de operación mientras tanto, y vale para los 16:** no dejes un robot con nada a
>   menos de 20 cm. Si no obedece, mira `/collision_monitor_state` antes de pensar que se colgó.
>   El verificador ya comprueba el valor en cada robot.
>
> 🆕🔴 **2026-08-09 · EL UMBRAL DEL MONITOR ES EL MISMO EN LAS CUATRO DIRECCIONES, Y EL `radius` NO
> SE PUEDE TOCAR EN CALIENTE** (evidencia 94, 24 estaciones a mano por el usuario)
>
> Umbral desde `base_footprint`: intersección **(17,9 · 19,6)**, que contiene los 18,0 del círculo.
> **24 de 24 estaciones todo-o-nada.** Banda de defecto **3,6 cm en las cuatro direcciones**.
> → 🔴 **Retira la observación de la evidencia 19** («PUDO SALIR» con el obstáculo al lado a 17 cm):
>   aquí, a la izquierda y a 17,9, está bloqueado. No hay dependencia de la dirección.
> → 🔴🔴 **`Aproximacion.radius` es INERTE en caliente** —`param set` lo guarda, el nodo no
>   reconstruye el polígono—: con 0,18, 0,15 y **0,30** el perfil es idéntico. **Cambiarlo es editar
>   el YAML y reiniciar: un cambio de imagen dorada para los 16, no un botón.**
> → ✅ **Hueco al parar MEDIDO** con el valor en producción, a 0,25 m/s: **9,3 · 9,4 · 9,3 · 9,4 cm**.
> → ✅ **DECIDIDO Y APLICADO el 2026-08-09: `Aproximacion.radius` 0.18 → 0.15** (evidencia 95).
>   La banda de inmovilización baja de **3,6 a 0,6 cm** y la holgura a velocidad máxima queda en
>   **7,4 / 6,6 cm** (medida). Control decisivo: a 15,8 cm de la pared, con 0.18 congelado y con
>   0.15 girando 34,9°. La F6 se reajustó a **[14,0 · 19,0]**, cuyo techo detecta a un robot al que
>   **no le llegó el fichero**; `verificar_robot.sh` da **FALLO** si encuentra 0.18.
>   ⚠️ No arregla los 0,6 cm restantes, ni el centímetro ciego, ni que `approach` no distinga
>   acercarse de alejarse.
>
> 🆕 **2026-08-09 · LA GEOMETRÍA DEL ROBOT, MEDIDA DESDE EL EJE DEL LIDAR**
>
> `9,0 cm detrás · 10,8 a cada costado`, validado contra el propio LIDAR con **2 mm** de error
> (12,20 leídos contra 12,00 predichos, n=8268 rayos). Radio circunscrito **0,1406 m**.
> → 🔴 **Y tumba una afirmación de seguridad que estaba en el manual y en la configuración:** «el
>   punto ciego de 10 cm cae dentro del chasis, no hay zona muerta». Con la media longitud real
>   (0,090) **sobresale 1 cm por delante y por detrás**, y **ningún polígono puede cubrirlo**: no es
>   cuestión de ajustar `radius`, es que el sensor no da el dato. A los costados sí queda dentro.
> → ✅ **CERRADO el borde delantero, a favor del URDF:** con el robot tocando la pared de frente el
>   perfil perpendicular sale plano en ±24° con mediana **10,03 cm** (n=3478) y los rayos centrales
>   recortados en `range_min`. La cinta había dado 9,0 porque medía **al chasis**. `base_length
>   0.190` + `laser_x −0.005` da 9,0 detrás y 10,0 delante: **el URDF acierta en los tres ejes** y
>   el LIDAR **no está centrado**. Radio circunscrito desde `base_footprint`: **0,1442**.
>
> 🆕🔴🔴 **2026-08-09 · RETIRADO: EL MAPA DE slam_toolbox NO ESTABA CONGELADO, ERA SUBMUESTREO**
> (evidencia 96). Conduciendo de verdad crece monótonamente: 4→30 nodos, 54→606 celdas ocupadas,
> desconocido 89,3 %→41,4 % en 1346 cm. Lo anterior salía de **160 cm de vaivén** = 4 nodos, y con
> `min_pass_through: 2` la mayoría de celdas se cruzan por un solo rayo y se descartan.
> → ✅ **La Fase 6 NO está bloqueada por esto**, y se desbloquea la casilla «AMCL sobre un mapa que
>   SÍ contiene los objetos»: ya se puede construir ese mapa.
> → 📌 Regla con número: **un mapa utilizable necesita varios metros**; con ~3 m el desconocido ya
>   baja del 90 al 46 %.
> → 🔴 El error de método: **se midió un sistema que ACUMULA con una muestra que no acumulaba.** Un
>   giro de 360° no aporta nada nuevo con un LIDAR de 360°. Hacía falta la CURVA, no otro punto.
>
> 📌 **Lo que se afirmó y queda retirado:**
>
> 49 celdas ocupadas para un cuarto entero (una pared de 15 m a 5 cm serían ~300), **idéntico celda
> por celda** tras 360° de giro y 160 cm de vaivén, republicando cada 5 s con sello fresco y con 4
> nodos en el grafo. El LIDAR estaba sano (227/270 rayos, 11,7 Hz, 360°).
> → 🔴 **Es la ruta con la que se hacen los mapas del aula**, así que bloquea la Fase 6 más que
>   ningún otro pendiente de navegación. ⏳ Causa **NO VERIFICADA**.
> → 🔴 Y obliga a **matizar la evidencia 91**: su «el mapa engorda los objetos ~5 cm por lado» se
>   dedujo de **tres celdas** sobre un mapa así. El efecto en el costmap sigue medido; el mecanismo
>   se ha retirado.
> → ✅ **CERRADA la casilla el 2026-08-09 (evidencia 97): AMCL sobre un mapa que SÍ contiene los
>   objetos da plan RECTO (102 %), igual que sin ellos.** Lo que hacía rodear a Nav2 no era el mapa
>   ni SLAM contra AMCL: era **un mapa de cuatro nodos**.
> → ✅ **Y de ahí salió la curva del paso, con cinco anchos y el robot cruzando de verdad:**
>
> ```
> hueco     consultas con plan   travesía real
> 38,6 cm       0 de 6           — (no hay paso)
> 38,9 cm       0 de 8           —
> 41,1 cm       0 de 8           —
> 47,1 cm       3 de 8           3 de 3, DEGRADADA (5× desvío, 2,7× tiempo)
> 61,1 cm       8 de 8           1 de 1, limpia en 7,8 s
> ```
>
>   **Tres regímenes: `< ~45` no pasa · `~47-55` pasa y cuesta · `> 55` estable.** Justifica los
>   60 cm del guion de aceptación, que hasta hoy eran empíricos.
> → 🔴 **Y cayó una fórmula:** «la primera celda aparece en `2 × (14,5 + 5) = 39 cm`» encajaba con
>   38,6 cerrado, pero a **38,9 y 41,1 sigue cerrado**. El umbral está entre 41,1 y 47,1.
>   ⏳ Si es por **alineación de la rejilla** —y entonces dependería de dónde está la puerta, no
>   sólo de su ancho— o por un radio efectivo mayor: **NO VERIFICADO**.

> 🆕 **2026-08-08 · LAS PRÁCTICAS SE EJECUTARON POR FIN, Y SALIERON CUATRO FALLOS**
> ═══════════════════════════════════════════════════════════════════════════════
> El pendiente más viejo del material docente: las diez prácticas estaban escritas, revisadas y con
> 91 tests, y **nunca se habían corrido con el robot moviéndose**. Se corrieron ocho (falta el
> seguidor de línea, aparcado hasta el aula por decisión del usuario). **Ninguno de los fallos es
> visible leyendo el código.**
>
> | | qué pasó |
> |---|---|
> | 🔴 `girar()` | abortaba a los **5,5° de 90 pedidos SALIENDO CON CÓDIGO 0**, culpando a una odometría sana. Contaba **vueltas del bucle** en vez de segundos |
> | 🔴 `avanzar(0.20,3)` | **26,4 cm en vez de 60**, sin un mensaje: el polígono de seguridad es de **40 cm de ANCHO** y frena al 40 % por algo a 9 cm de un costado |
> | 🔴 La Pi no tiene RTC | los servicios que arrancan con ella quedan **19,5 h en el pasado**, y `journalctl --since` no los ve. **Invalidó una comprobación mía de A11 de esa misma sesión** |
> | 🔴 El verificador | declaró FALLO sobre una regla de polkit **que estaba puesta**: `-e` da falso si el directorio no es atravesable. **«No puedo verlo» no es «no está»** |
>
> Todo en la **evidencia 85**, y el arreglo de `girar()` en `Atriz_rvr`.
>
> ✅ **Y lo que sí funcionó:** cuadrado que **cierra a 11 cm** en 2,4 m · siete giros entre 89,7 y
> 90,8° · la patrulla **detectó un obstáculo y giró sola** · la 11 paró sobre negro · y la práctica
> 4 **disparó su propia lección** en vivo (el giro cruzó el salto de ±180°).
>
> 🆕 **Y el sensor de color resultó tener DOS modos.** Preguntó el usuario si serviría para un piso
> de baldosas LED. Sí — **apagando la luz del propio sensor**, porque encendida el reflejo especular
> sobre el vidrio **invierte el resultado**: una pantalla roja a tope da `R/G = 0,53`, menos rojo
> que verde. Validado con un **2×2** que diseñó él, cuya casilla de control da **cero absoluto**.
> Contrato para la web en **[`03_operacion/SENSOR_COLOR.md`](03_operacion/SENSOR_COLOR.md)**, y no
> hizo falta tocar el robot: `/enable_color` + `/get_rgbc_sensor_values` bastan. Evidencia 86.
>
> 📝 **Y una lección que salió TRES veces el mismo día:** un número correcto en su contexto se
> vuelve falso al mudarlo de sitio. El suelo daba **1275** en una habitación y **950** en otra; el
> móvil **150** y **42** según el brillo; y `/odom` tiene un peor hueco de **81 ms** en régimen
> permanente y **326 ms** recién reiniciado el driver — esto último **desmintió mi propio margen** y
> obligó a subir el umbral de `girar()` de 1,0 a 2,0 s.
>
> ═══════════════════════════════════════════════════════════════════════════════
> ✅ **2026-08-08 23:03 · LA PRUEBA DE ACEPTACIÓN, ENTERA POR PRIMERA VEZ**
> ═══════════════════════════════════════════════════════════════════════════════
> Diez fases, de F0 a F9. La última tanda (2026-08-02) había dejado **cinco en PENDIENTE**.
>
> ```
>   61 PASA · 8 REVISAR · 1 FALLO · 4 PENDIENTE
>   🔴 NO HAY VÍA LIBRE PARA LA FASE 5
> ```
>
> 🔴 **Un solo hallazgo real en 74 comprobaciones**, y no es el que parecía: el objetivo con
> obstáculo dio `ABORTED`, y lo primero fue ir al journal **porque ese mismo día se descubrió que
> `ABORTED` puede ser mentira** (evidencia 88). No lo era: `planner_server` abortó
> `compute_path_to_pose` **ocho veces** y Nav2 agotó sus recuperaciones. **Falla el PLANIFICADOR,
> no el controlador — no había plan que ejecutar.** Los otros dos números (46,5 cm y 162,6°) son
> aguas abajo: los 162° son los **dos `spin` de la recuperación**.
> ✅✅ **CERRADO POR SU EFECTO el 2026-08-09 15:07 (evidencia 92): F7 entera en verde con el hueco
> a 60 cm medido con cinta. 12 PASA · 0 REVISAR · 0 FALLO.** El objetivo con obstáculo da ahora
> `SUCCEEDED` (8,0 cm, rumbo 13,0°), y el log de Nav2 lo confirma por otra vía: **planificador 0
> fallos** (eran 8), 0 colisiones detectadas, 0 `patience exceeded`, **ninguna recuperación**.
>
> ✅ **CAUSA MEDIDA el 2026-08-09 (evidencia 91): era MONTAJE DEMASIADO JUSTO, y no por poco.** El mapa
> engorda los objetos **~5 cm por lado**, así que un hueco de 45 cm entra en él como 35; la
> inflación del radio inscrito (14,5 cm) lo cierra, NavFn **traza un rodeo** de 168-233 % de largo
> en un cuarto con 55 y 67 cm a los lados, el rodeo roza la inflación, y `failure_tolerance: 0.3`
> mata el objetivo en tres décimas. Cadena entera medida, con AMCL y con SLAM.
> → ✅ **Regla con número: hueco mínimo ≈ 49 cm para ser transitable, y entre 45 y 60 para que Nav2
>   no prefiera rodear.** La única tanda con plan recto fue la de 60 cm.
> → 🔴 **ALCANCE: eso vale CON SLAM, que es lo que lanza F7.** Con AMCL sobre un mapa que NO contiene
>   los objetos, 45 cm **sí pasan** (medido dos veces, plan recto al 109 %): allí la puerta la marca
>   sólo la capa de obstáculos del LIDAR, que es fina, y el canal queda abierto a coste 84.
>   ⏳ **Falta la casilla del aula:** AMCL sobre un mapa que **sí** contiene los objetos. Los mapas
>   del aula se hacen con slam_toolbox y se guardan, así que la predicción es que se comporte como
>   SLAM. **NO VERIFICADO.**
> → 📌 **No es defecto del robot.** El montaje del guion de aceptación tiene que respetar ese hueco.
>
> ✅ **Los otros 7 REVISAR son ruido explicado:** dos son nuestros reinicios del día (el propio
> guion dice cómo desempatarlo, con el `uptime`, y funcionó), cuatro son avisos conocidos del
> verificador, y dos son aguas abajo del FALLO.
>
> ✅ **Y valida los tres cambios del día**: el aviso «error final SEGUN AMCL» sale en las tres
> lecturas · `girar()` sin un falso aborto (87,9 · 174,2 · 357,8°, signo REP-103 correcto) · y los
> dos objetivos limpios de Nav2 en `SUCCEEDED` con el plazo de 1000 ms.
>
> ⚠️ **Batería 7,22 V durante toda la corrida.** No parece haber afectado —los giros salieron en
> línea con las bases— pero se anota. Evidencia 89.
>
> 🔴 **Y un texto del propio guion que hay que corregir:** el PENDIENTE «la credencial `sphero` sin
> rotar» **se rotó el 2026-08-04**. Lo que sigue abierto es el histórico de git, que es higiene y
> no exposición.
>
> Última actualización: **2026-08-13** (el día en el laboratorio: bloque nuevo arriba del todo).
>
> Antes de esta sesión, el **2026-08-04** se cerró **el direccionamiento de la flota**
> —una dirección por red, aplicada en rvr-01 y verificada desde el navegador (evidencias 74 y
> 75)— y dejar la **aplicación web** con sus seis rutas mirándose contra el robot vivo. Antes de
> eso: el **cliente de rosbridge** (movió un robot real, con cinta y control por SSH), la
> **revisión final de rama** y su oleada de arreglos. El material docente —`atriz.py` y las diez
> prácticas— está escrito, revisado y con **89 tests**, y **empujado a los dos repositorios**.
>
> 🔴 **Lo que falta es de dos clases, y las dos son del usuario:**
> 1. **La sesión física, a medias.** El **2026-08-03 se midieron cinco de las siete evidencias**
>    (57, 58, 59, 60, 61) y salió un fallo real: `girar()` sobregiraba **+4.01° constantes** por
>    no compensar la inercia — arreglado y remedido en la misma sesión (**+0.19°**). Faltan las
>    dos que necesitaban `sudo` y rearrancar con `color_detection:=true`: la 62 (las prácticas de
>    color) y la 63 (el seguidor de línea).
>    ✅ **LA 62 ESTÁ CERRADA desde el 2026-08-08, y el requisito que la bloqueaba YA NO EXISTE.**
>    Encender el sensor **en caliente** se verificó el 2026-08-06 (`/enable_color`, evidencia 76),
>    así que ni `sudo` ni reinicio. Corridas ese día con arnés que mide el efecto:
>    **05** lectura estable y **sin mover el robot** (que es lo que promete), **11** detectó negro
>    a `claro=396` tras **46,5 cm** y paró. Evidencia 85.
>    ⏳ **Solo queda la 63, el seguidor de línea.** *(Sigue siendo cierto el 2026-08-13: la
>    sesión física del resto quedó EN VERDE —evidencia 108— y la 63 no se corrió porque no
>    había línea en el aula.)*
>    🔴 **DECISIÓN del usuario, 2026-08-09: se aparca hasta el AULA, y no por la cinta.** Una
>    línea pegada en el suelo de una habitación no reproduce lo que la práctica tiene que
>    validar: el recorrido real, su iluminación y su contraste sobre el suelo del laboratorio.
>    Probarlo aquí daría un ✅ que **no se transfiere** — y este proyecto ya tiene medido que un
>    número correcto en su contexto se vuelve falso al mudarlo de sitio (el suelo dio `claro`
>    1275 en una habitación y ~950 en otra, con el mismo robot **el mismo día**).
>    📌 **Sale de «lo que falta hacer» y entra en «lo que espera al aula»**, junto al SSID, la
>    F0 del AP y el mapa del laboratorio.
> 2. ✅ **ROTADAS el 2026-08-04.** El usuario rotó la PSK del WiFi y la contraseña de `sphero`, y
>    a continuación se **archivó `Atriz_web_server`** (público, solo lectura). **Eso es lo que
>    cierra la exposición**, y ya está hecho.
>    ⚠️ **Lo que sigue abierto es higiene, no exposición:** el historial de `Atriz_rvr` conserva
>    las once líneas en `main` y en `ros2` — la **punta** de `ros2` está limpia (0) y la de `main`
>    no. Purgar el historial **no llega a los forks que ya existan**, así que nunca habría bastado
>    solo. Ahora que están rotadas, los valores del historial **ya no valen para nada**.
>    ⚠️ Y el borrado de `migracion-ros2` y `wip/scripts-estudiantes` del 2026-08-03 **no cerró
>    nada**: solo dejó de servirlas por esas dos puntas.
>
> Y falta también la corrida completa de la prueba de aceptación tras un reinicio real.
>
> 🆕 **Y desde el 2026-08-04 la Fase 5 está en marcha, y su capa de datos ya no es una promesa.**
> `atriz-lab` **movió un RVR real** con el código de producción (evidencia 70) y las tres
> comprobaciones que faltaban están **cerradas**:
> - **cinta métrica, n=2:** 30 y 30 cm de cinta contra **30,2 y 29,6** de odometría (T1).
> - **control por SSH:** 31 cm de cinta contra **31,3** — la misma secuencia, solo cambia el
>   transporte (T9).
> - **parada de emergencia con el robot EN MARCHA, por WebSocket: 4 de 4**, frenada de
>   **1,8–2,9 cm** contra los 9,9–10,7 del `collision_monitor`, con el flanco `false→true` visto
>   desde el robot (T2).
>
> **Aquel día** eran **358 pruebas** (`tsc` y `eslint` limpios), las seis rutas se abrían y se
> habían mirado **renderizadas con datos reales**, y el muro encontraba al robot **por su nombre**.
>
> ⚠️ **Esta cifra decía «Hoy son 358 pruebas» y se quedó rancia seis días.** Al **2026-08-10** son
> **620** en la suite normal, más **47 con navegador** que corren sin robot contra el doble y **4**
> que sí lo necesitan; y las rutas son **nueve**, no seis. La cifra viva está en el `README.md` de
> `atriz-lab`, que es su repositorio: **este fichero no es el sitio donde llevar la cuenta**, y por
> eso queda fechada en vez de actualizada.
> El diseño de la aplicación está en
> [`00_auditoria/planes/2026-08-04-estructura-app-web.md`](00_auditoria/planes/2026-08-04-estructura-app-web.md)
> y **todas las dudas abiertas, con recomendación**, en
> [`00_auditoria/planes/2026-08-04-dudas-abiertas.md`](00_auditoria/planes/2026-08-04-dudas-abiertas.md).
> ~~🔴 **El producto —el terminal— está bloqueado por la F0**, que necesita el aula~~
>
> ✅ **CONSTRUIDO EL 2026-08-14.** La F0 se descartó como riesgo el 2026-08-10 y el agente de
> sesión se escribió el 14. Un alumno abre una práctica **del robot**, la edita, la ejecuta,
> contesta a sus `input()` y la para — sin SSH. Diseño entero en
> [`docs/superpowers/specs/2026-08-14-el-taller-terminal-del-alumno-design.md`](docs/superpowers/specs/2026-08-14-el-taller-terminal-del-alumno-design.md).
>
> 🔴 **Y lo que falta ya no es un eslabón, es una MEDIDA: el PTY no ha tocado un robot.** Sus 13
> pruebas están escritas —cada una con su control contra una tubería— y **se saltan en Windows**,
> así que los dos requisitos que justifican el diseño siguen sin medir. Se cierran en **cualquier
> Linux, sin RVR**: `python3 -m pytest scripts/agente/pruebas/ -q` en `Atriz_rvr`.
>
> 👤 **Antes de instalarlo hay que quitar `~/.git-credentials` de los robots**: el código del
> alumno corre como `sphero` y puede leer el PAT de GitHub. Los repositorios ya son públicos.
>
> 🔴 **Y el modelo de amenaza cambia**: con `rclpy` nativo el alumno alcanza `raw_motors` y
> `set_ir_mode`, saltándose el `collision_monitor`. «`raw_motors` ya no es alcanzable» **deja de ser
> cierto mientras haya un programa corriendo**. Va escrito en la pantalla.
>
> 🆕 **Y desde el 2026-08-03 hay una tercera cosa, a medias:** el arranque de la navegación.
> `atriz-nav.service` está **escrita, INSTALADA y sin habilitar** (tareas 1, 2, 3 y 5 del plan
> `00_auditoria/planes/2026-08-03-arranque-navegacion.md`), ~~pero **nunca se ha arrancado bajo
> systemd**~~ ✅ **arrancada bajo systemd el 2026-08-13** (evidencia 107): 27,80/27,84 s hasta
> aceptar objetivos, `active/success` las dos vueltas, con `cuarto3.yaml` como mapa de mecanismo.
> ~~El `aula.yaml` de verdad sí espera al laboratorio.~~ ✅ **HECHO el 2026-08-19:
> `~/mapas/arena.yaml`**, mapeado en la arena y con `ATRIZ_MAPA` apuntando ahí.
> Detalle en `03_operacion/ARRANQUE_NAVEGACION.md`.

---

## En una frase

🔴 **El material docente estaba MUERTO, y además con credenciales en un repositorio público —
reescrito sobre una biblioteca propia y pendiente de UNA corrida contra el robot (2026-08-02).**
Los diez guiones y cinco documentos del curso venían en ROS 1: `import rospy` →
`ModuleNotFoundError` en la primera línea, 0 de 10 arrancaban, y 15 publicaciones a `/cmd_vel` en
8 ficheros — la **salida** del `collision_monitor`, así que si hubieran arrancado habrían saltado
la capa de seguridad entera. Y `00_LEEME_PRIMERO.md` / `GUIA_PASO_A_PASO.md` llevaban en texto
plano la **PSK del WiFi del laboratorio** y la contraseña del usuario `sphero`, empujadas al
remoto **público** `Atriz_rvr` en las cuatro ramas que entonces existían (`main`, `ros2`,
`migracion-ros2` y `wip/scripts-estudiantes`; las dos últimas borradas el 2026-08-03). Reescritos los diez guiones y los cinco documentos sobre `atriz.py`
—diseño en [`03_operacion/API_LABORATORIO.md`](03_operacion/API_LABORATORIO.md)—, con **61
tests** de las funciones puras y verificado que ningún guion importa `rospy` ni escribe en
`/cmd_vel`. **Nada se ha medido con el robot moviéndose todavía** — ver más abajo, «Material
docente: `atriz.py` y las diez prácticas», que es el siguiente paso exacto. Y las credenciales se
sacaron del **contenido** actual, no del historial: **rotarlas sigue siendo acción del usuario**,
y es lo único que cierra la exposición de verdad.

🔴 **LA RED DE LA FLOTA SE DIO POR RESUELTA EL 2026-08-01 Y NO LO ESTABA.** Aquel día un
navegador abrió `ws://rvr-01.local:9090` resolviendo **por nombre** y se dio por cerrado. **La
medición era correcta y la conclusión incompleta:** se verificó desde el punto de vista del
**robot** —¿puede tener tres direcciones a la vez?— y nunca desde el del **cliente**.

El 2026-08-04, con la web ya construida, el usuario avisó de que «no funciona nada en flota».
`rvr-NN.local` resolvía a **cuatro** direcciones y el navegador probaba en un orden en el que las
dos primeras —el `fe80::` sin zona y la estática del otro sitio— **no fallaban: se colgaban** ~21 s
cada una. En el aula funcionaba **por suerte**, porque `10.14.7.7` ordenaba antes que las de casa.
→ Rediseñado: **una dirección por red**, emparejada por SSID.
[`00_auditoria/planes/2026-08-04-direccionamiento-flota.md`](00_auditoria/planes/2026-08-04-direccionamiento-flota.md).

✅ **APLICADO en rvr-01 y VERIFICADO DESDE EL CLIENTE, el 2026-08-04 por la tarde**
(evidencias [74](00_auditoria/evidencia/74_una_direccion_por_red.txt) y
[75](00_auditoria/evidencia/75_navegador_por_nombre.txt)):
`hostname -I` da **una sola** dirección, `[Match] SSID=` casó el fichero de casa sin scripts, y
**`ws://rvr-01.local:9090` ABRE en el navegador** — 4339 ms con la caché mDNS fría, 2331 caliente.
El muro pinta `rvr-01 · 7,67 V · en línea` **por nombre y sin override**.

🔴 **Hizo falta `publish-aaaa-on-ipv4=no` ADEMÁS de `use-ipv6=no`**: el primero apaga el
*transporte* IPv6, pero el registro `AAAA` **se seguía anunciando por el transporte IPv4**.
⚠️ Y un testigo falso casi lo da por cerrado antes de tiempo: `getent ahosts` **desde la Pi** dio
una sola dirección mientras el PC recibía dos. **`getent` no ve lo que la Pi anuncia al cable.**

✅ **CERRADO EL 2026-08-12, EN EL LABORATORIO: `05-atriz-lab.network` CASÓ.** Aquí ponía «nunca ha
casado con nada» y era el riesgo de que 16 robots se quedaran sin dirección estática con los alumnos
delante. Medido sobre rvr-01 el primer día en el aula: única SSID intentada `Atriz-server`, a la
primera, `Network File: /etc/systemd/network/05-atriz-lab.network`, `Address: 10.14.7.7`,
`routable (configured)`, `online`, y con salida a NTP. ⏳ **n=1**: falta rvr-02 y la imagen dorada.
Evidencia 102.

✅ **Lo del arranque en frío ya NO está pendiente: cerrado el 2026-08-11 con rvr-02**, que es
literalmente el caso que este párrafo temía («lo que hará el robot 7»). Se escribió su `red.txt`,
se generaron los `.network` con `first-boot.sh --solo-red` y **se aplicaron reiniciando**, nunca en
caliente. El verificador tras el arranque: `✓ wlan0 con UNA sola dirección IPv4: 192.168.1.201/24`
· `✓ wlan0 sin dirección del DHCP` · `✓ el .network de «…» está aplicado`. **El emparejamiento por
SSID ocurre en el arranque.** Queda solo el perfil del aula, que solo puede probarse allí.

Ancho de banda medido dos veces con dos clientes distintos: **80.7 kB/s navegando → 10.3 Mbit/s
los 16**, y `/scan` es el **83 %**. Manual, **cap. 19**.

**🟢 La migración funciona: el robot corre sobre ROS 2 Jazzy y SLAM ya mapea.** Ubuntu Server
24.04.4 + Jazzy instalados, driver portado a `rclpy` (`/odom` a 16.67 Hz), URDF y árbol TF
enteros, LIDAR publicando `/scan`, y `slam_toolbox` activo publicando `/map`.

✅ **Y el enlace ya aguanta solo.** El RVR se dormía a los **300.6 s** y el nodo no se
enteraba; desde el 2026-07-31 el driver le habla cada 30 s, publica `/battery_state`, y avisa
y reanuda si aun así deja de llegar telemetría. Verificado: 12 min sin un hueco, contra 2
huecos sin el arreglo (manual, cap. 9.8).

✅ **Y la Fase 4 está CERRADA.** `slam_toolbox` mapea de verdad: moviendo el robot 1.78 m el
mapa pasó de **2367 a 3299 celdas** (5.92 → 8.25 m²). Hicieron falta tres arreglos y corregir
dos herramientas propias, y **ninguno de los fallos daba un error** (manual, cap. 9.11).

✅ **Y la deriva de la localización está resuelta.** Con 24 corridas apareció que **~1 de cada
5 se iba a 6–56 cm**; la causa era que **el robot no volvía a su sitio** (~8 cm de deriva por
corrida). Referenciando la posición antes de cada corrida: **0 fallos de 12**, peor caso
**4.4 cm**, y la deriva **no crece con la distancia** (1.55 cm a 1.6 m, 0.90 cm a 2.3 m). Muy
por debajo de la tolerancia de 10 cm de Nav2. Manual, **cap. 9.12c**.

✅ **Y los TRES bugs de marcos de referencia de `/odom` están arreglados y verificados.** Los
sensores del RVR siempre estuvieron bien —`Velocity` es exacto, el locator acierta con 1 mm en
1 m—; lo que fallaba era cómo el driver los combinaba. Ahora el yaw arranca en **+0.00°**, la
dirección de avance coincide con él (**+0.03°**), y `odom.twist.linear` da la velocidad en el
marco del robot con un **2 % de error** mire donde mire (`15_velocidad_odom.txt`).

✅ **Y Nav2 NAVEGA.** Dos objetivos autónomos completados con **9–10 cm de «error final»** ⚠️ (🔴 corregido el 2026-08-08: esa cifra es la **tolerancia repetida**, no una medida — con cinta salió 6,1 · 11,8 · y 41,3 cm con mapa rancio, `SUCCEEDED` las tres), que
es la tolerancia configurada. Coste: ~89 % de **un** núcleo con todo el stack, `loadavg` 2.53
sobre 4, sin throttling. Manual, **cap. 11**.

✅ **Y la capa de seguridad está puesta y medida.** El `collision_monitor` para el robot a
**8 cm de una pared a 0.25 m/s y a 9 cm a 0.40 m/s**, sin dejarlo atrapado, y sin LIDAR
**bloquea la conducción por completo** (0.0 cm de movimiento, comprobado matando el nodo).
De paso destapó un agujero: el `behavior_server` de Nav2 publicaba en `/cmd_vel`
**saltándose la seguridad**. Manual, **cap. 12**.

✅ **Y ya navega a 0.40 m/s**, el máximo del robot: meseta medida en **0.407 m/s**, dos
objetivos `SUCCEEDED` con **8 cm** de error cada uno — *mejor* que los 9–10 cm de las corridas
a 0.25. La capa de seguridad solo se activó cuatro veces y ninguna fue una parada.

✅ **Y rodea obstáculos.** Cuatro navegaciones seguidas esquivando una caja de 16 cm puesta en
medio del camino: **todas `SUCCEEDED`, todas por la derecha, 8–9 cm de error** — el mismo que
sin obstáculo. Manual, **cap. 11.13**.

🔴 **Y el paso estrecho dio el límite: con `radius: 0.18` NO cruza 40 cm.** El robot entró en
la boca, con el camino despejado delante y sin tocar nada, y se bloqueó — el borde estaba a
17 cm y su círculo mide 18. Salió marcha atrás sin problema. No es un fallo: es el compromiso
`parar lejos de las paredes` ↔ `cruzar huecos estrechos`, ahora medido.

🔴 **Y por el camino salió que el URDF tenía largo y ancho CRUZADOS.** El robot mide **18.2 ×
21.7 cm** (medido con orugas), no 21.8 × 18.5. Los huecos publicados salían 2 cm cortos
—corregidos— y **`robot_radius: 0.11` estaba mal**: el circunscrito real es 0.142. Corregido a
0.145.

✅ **El robot se midió entero el mismo día**
([`03_operacion/MEDIDAS_ROBOT.md`](03_operacion/MEDIDAS_ROBOT.md)), y salieron dos cosas más:

- 🔴 **El plano de barrido está 2 cm más bajo de lo documentado**: **15.5 cm**, no 17.45. La
  ficha del RVR daba 11.4 cm de alto y son **7.0**. El robot **ve mejor** de lo que decíamos.
- 🔴 **La inclinación de ~8° NO EXISTE** (ver abajo). Un problema abierto desde el principio,
  cerrado con una regla.

✅ **Y las paradas contra pared se repitieron con las cotas buenas**: **9.9 cm** a 0.25 m/s y
**10.6 / 10.7 cm** a 0.40 — a 1–2 mm del recálculo, y con 1 mm de dispersión entre las dos
corridas a 0.40. Ya no hay ningún número recalculado sin verificar.

✅ **Y la inclinación del RVR está resuelta**: no es el robot, es el **acelerómetro**, que da
`|g|` un 3.8 % corto y un error **fijo en el marco del robot**. Son **6.9° y viven en el PITCH**
(el roll es de 1°), no «~8° de roll» como decía la documentación. Costó **dos conclusiones mías
retiradas**; están explicadas en el **cap. 13** porque las dos son errores de método fáciles de
repetir.

⚠️ **El experimento de la deriva con y sin ese roll NO responde la pregunta**: el efecto buscado
era de ~1 cm y apareció el fallo de 12–56 cm que lo entierra.

✅ ~~Lo siguiente es el fallo bimodal a 2.3 m~~ — **cerrado el 2026-07-31** con
`referenciar_posicion.py`: 0 fallos de 12 y peor caso 4.4 cm.

✅ **CERRADO EN DOS TIEMPOS — 2026-08-08 (ocho prácticas corridas, evidencia 85) y 2026-08-13
(los cinco ensayos con el usuario midiendo, evidencia 108). Solo queda la práctica 63.** El
párrafo se conserva porque explica qué había que medir y por qué:

🔴 ~~**LO SIGUIENTE DE VERDAD, HOY: la SESIÓN FÍSICA del material docente.**~~ El código de las diez
prácticas y `atriz.py` está escrito, revisado y con 89 tests — pero **nada de lo que depende de
mover el robot está medido**: ni los ~60 cm de `avanzar()`, ni los ángulos de `girar()` con
transportador, ni las cinco corridas de Ctrl-C, ni que los faros enciendan, ni que
`distancia_frontal()` apunte de verdad hacia delante, ni el seguidor de línea con edge-following
sobre una línea real, ni ninguna de las diez prácticas ejecutada de principio a fin. Detalle y
comando exacto en «Material docente: `atriz.py` y las diez prácticas», más abajo.

📌 **Y después de la sesión física, según el orden acordado del proyecto: decidir el arranque
automático de Nav2/SLAM.** Es el punto que queda abierto en
[`03_operacion/API_LABORATORIO.md`](03_operacion/API_LABORATORIO.md) (última línea, «Lo que este
trabajo NO cierra») y que el diseño de la Fase 5 (`Atriz_web_server`) va a necesitar tener
decidido antes de arrancar.

⏳ **Y sigue pendiente, sin fecha fija: migrar el robot 2** →
[`03_operacion/FLOTA.md`, «Robot 2: instalación LIMPIA»](03_operacion/FLOTA.md). Levanta la
✅ suposición ya levantada (`provision.sh` ejecutado entero el 2026-08-11), da el
segundo robot para el IR, y valida la imagen dorada antes de replicarla catorce veces. Se
pospuso por la aparición de las credenciales expuestas en `Atriz_rvr` (2026-08-02), que subió
de prioridad al material docente.

---

## Qué está verificado (con mediciones, no suposiciones)

| Componente | 20.04 + Noetic | **24.04** | Evidencia |
|---|---|---|---|
| Raspberry Pi 4B 8 GB | ✅ 57 °C, cero throttling | ✅ 63.7 °C, `throttled=0x0` | `evidencia*/` |
| Enlace UART Pi ↔ RVR | ✅ PL011 vía `/dev/rvr` | ✅ **el RVR contesta**, firmware 9.1.462 | `raw_uart_2026-07-30.txt` |
| YDLIDAR X2 | ✅ 100 % checksums, 11.4 Hz | ✅ **100 %, 11.48 Hz** | `lidar_x2_2026-07-30.txt` |
| Higiene del SO | receta documentada | ✅ **aplicada** | `02_higiene_aplicada_*.txt` |
| Telemetría del RVR a 16.59 Hz | ✅ 12 min, 0 huecos, 0 pérdidas | ✅ **12 min, 0 huecos** con el driver ROS 2 y keepalive | `12_keepalive_rvr.txt` |
| SDK de Sphero | ✅ GO en Python 3.8 | 🟢 **GO en 3.12**, 16.67 Hz | `04_gonogo_sdk_py312_*.txt` |
| Enlace estable sin tocar nada | — | ✅ el RVR se dormía a los **300.6 s**; arreglado | `12_keepalive_rvr.txt` |
| Sensor de color **encendido en caliente** | ✅ servicio `enable_color` (así funcionaba) | ✅ **recuperado el 2026-08-06**: `/color` no-cero 0→53→0, claro 1→1320→0 | `76_color_en_caliente.txt` |

Firmware del RVR: **9.1.462** (Nordic), confirmado también en 24.04 leyendo el payload de
`get_version` (`09 00 01 01`).

⚠️ Las dos líneas base son distintas y **no se mezclan**: `00_auditoria/evidencia/` es el
sistema viejo, `00_auditoria/evidencia_24_04/` el nuevo.

## El SDK del RVR, explorado (2026-08-01) — 16 consultas de 62 métodos

De los 62 métodos que el driver no usaba se **probaron las 16 consultas** que podían aportar algo. Los otros 46 son **notificaciones** —cuyo estado es **NO VERIFICADO**, no «no emiten»: la de atasco **sí** llega— y modos de conducción alternativos que no hacen falta. Resumen para no repetirlo:

| | |
|---|---|
| ✅ **Batería con voltaje y umbrales del firmware** | implementado y verificado. `voltage` 8.28 V · umbrales **7.0 / 6.5 V** leídos del propio firmware. 🔴 **La web debe mirar `voltage`, no `percentage`**: el porcentaje decía 100 % a 1.29 V del umbral de «baja» |
| 🔴 **El atasco SÍ se detecta**, y dice **qué oruga** | 3 de 3 con el robot bloqueado. La conclusión anterior («las notificaciones no llegan») era **falsa**, y la causa es **el tiempo**: el ensayo original duró **3 s** y la detección tardó **~5 s** (⚠️ n=1, de un par de marcas del journal con resolución de 1 s: **5 ±2 s**, y a otra velocidad que el ensayo fallido). Y el RVR **enciende LEDs amarillos y rojos** por su cuenta |
| 🔴 **No hay rumbo absoluto** — limitación del hardware | `get_magnetometer_reading` da `bad_cid` y `magnetometer_calibrate_to_north` **no hace nada**. El firmware ya está en la última versión. **La pose inicial tendrá que venir del mapa o del operador** |
| 🔴 **No hay corriente de motores** | `bad_cid`. Ya no importa: el atasco se detecta por notificación |
| ⚠️ **Térmica y fallo: NO VERIFICADAS** | la prueba llegó a 40 °C y no podía disparar nada. No se persigue: el sondeo cada 30 s ya da el dato |
| 📚 **Documentación del protocolo rescatada** | `sdk.sphero.com` ya no existe. Copia en `00_auditoria/referencia_sdk/` |

✅ ~~**Lo único que queda necesita un segundo robot: todo el IR robot-a-robot**~~ — **PROBADO
el 2026-08-11 con rvr-01 y rvr-02**, que es la primera vez que se ha podido. Emisión, `following`,
`evading` y `off` responden y el comportamiento físico lo confirmó 👤 el usuario. Evidencia 99.

🔴 **Y destapó un agujero de seguridad real, encontrado ejecutando y no leyendo:** con la parada de
emergencia **activa**, `set_ir_evading` se negaba —correcto— pero **`set_ir_mode following`
respondía `success=True` y el RVR se ponía a conducir**. Los dos son modos del firmware: no pasan
por `cmd_vel`, así que ni el watchdog ni el `collision_monitor` los ven. Es el MISMO agujero que se
tapó el 2026-08-01 para `evading`, dejado abierto para `following` porque aquel arreglo se dio por
bueno mirando el servicio que se arreglaba en vez de buscar los demás que mueven el robot.
Arreglado en `Atriz_rvr` (`19884e7`), y auditados los demás: era el único.

📌 Y esto responde a la frase que estaba aquí — *«el arreglo de `set_ir_evading` está verificado
por código, nunca con un emisor delante»*. Verificado por código era, en efecto, insuficiente: el
que faltaba estaba al lado.

✅ **La RECEPCIÓN se implementó ese mismo día, y el firmware SÍ la entrega** — al revés que las
notificaciones de motor. Medido en rvr-01 con rvr-02 emitiendo:

```
enable IR recibido: respuesta = None
PRIMER mensaje IR recibido. Payload CRUDO: {'infrared_code': 3}
```

🔴 **Y el payload desmonta el tipo de mensaje.** La notificación trae **una sola clave**,
`infrared_code`. Los cuatro `*_strength` de `InfraredMessage.msg` **no existen en la recepción**:
son parámetros del ENVÍO. El tipo describe algo que el robot no manda nunca.

🔴 **Y ROS 1 nunca recibió nada, tampoco.** Su handler leía `datos['InfraredMessage']['Code']`
contra ese payload: `KeyError` en la primera línea. Además `/ir_messages` se **anunciaba y nunca se
publicaba** — así que la frase «ROS 1 publicaba los dos topics con los mismos datos», que está en el
propio driver y en el CHANGELOG, **es falsa**: uno estaba vacío y el otro reventaba.

✅ **Y por eso el IR entero SE REDISEÑÓ ese mismo día** (👤 decisión del usuario) en vez de
parchear la clave: el tipo de mensaje es incorrecto, `atriz.py` no expone nada de IR, no hay ni una
prueba automatizada válida para ROS 2, y **la detección direccional del SDK no la usa nadie** pese a
que `get_bot_to_bot_infrared_readings` **responde** (evidencia 41: `0xFFFFFFFF` = los cuatro
sensores vacíos, que es lo correcto con un solo robot).

📝 **Dos datos que la Fase 5 necesita saber:** un motor bloqueado sube **+11.1 °C en 90 s** de bloqueo (ritmo NO constante, 5→10 °C/min, n=1)
(sirve de corroboración de atasco), y **la temperatura publicada puede tener 30 s de retraso** —
una temperatura plana **no** significa «estable», puede ser el mismo dato repetido.

---

## Qué está roto y confirmado

| Problema | Gravedad | Estado |
|---|---|---|
| ~~El RVR se duerme solo y el driver no se entera~~ | seguridad operativa | ✅ **resuelto 2026-07-31**: timeout medido en **300.6 s**, keepalive cada 30 s + detector de silencio. 2 huecos → 0 |
| ~~La velocidad de `/odom` sale en el marco equivocado~~ | bloqueaba Nav2 | ✅ **resuelto 2026-07-31**: rotación −90° + proyección sobre el rumbo. **2 % de error** con el robot a 84° |
| ~~La posición y la orientación de `/odom` tienen manos contrarias~~ | bloqueaba Nav2 | ✅ **resuelto**: sobraba el `−Y`. Ahora giran igual (+89.87° vs +90.00°) |
| ~~El eje X del locator está 90° girado~~ | bloqueaba Nav2 | ✅ **resuelto**: `R(−90°)·(x,y) = (y,−x)` en `_h_locator` |
| 📝 `reset_yaw()` **no hace nada** — el yaw se pone a cero al **encender** el RVR | menor | ✅ **corregido**: el driver mide `yaw₀` al conectar y lo resta. Cinco arranques dieron cinco offsets distintos |
| ~~`inverted` del LIDAR sin verificar~~ | corrompe mapas | ✅ **verificado 2026-07-31**: `true` es CORRECTO. El equivocado era el yaw de `/odom` |
| ~~El robot está inclinado ~8°~~ | calidad de Nav2 | ✅ **resuelto 2026-07-31**: NO está inclinado. Las «tres vías» eran **una sola contada tres veces** (todas salen de la IMU). El acelerómetro crudo **no gira con el robot** y `\|g\|` sale 3.8 % corto → está **descalibrado**. El driver publica la orientación plana (`publicar_inclinacion: false`). Manual, cap. 13 |
| ~~La parada de emergencia de la web no hace nada~~ | seguridad | ✅ **resuelta 2026-07-31**. Había **tres** causas, no una: nombre, **namespace** (`/rvr/`) y **QoS** (`TRANSIENT_LOCAL` en el suscriptor no empareja con nadie). Verificada por los tres nombres, 0 avisos de QoS. Manual, cap. 15 |
| **Credencial del usuario `sphero` expuesta** en `Atriz_web_server` público, sin rotar | seguridad | 🔴 abierto — **acción del usuario**. Y no basta con rotarla: hay que quitarla del **historial** de git, no solo del último commit |
| ~~Sin arranque automático~~ | operación | ✅ **resuelto 2026-07-31**: `atriz-robot.service`, probado con un reinicio real. Falta que `provision.sh` lo instale |
| ~~La integración con el SDK NO está completa~~ | funcionalidad | ✅ **explorado el 2026-08-01**: el driver usa **37 de 99** métodos, y de los 62 restantes se probaron **las 16 consultas útiles** (evidencias 41–44); los otros 46 son notificaciones y modos de conducción alternativos. De lo que faltaba, **solo uno era aprovechable y ya está puesto** (voltaje de batería). 🔴 **El atasco SÍ se detecta** — la conclusión contraria era falsa. 🔴 **No hay rumbo absoluto**, cerrado con evidencia. ✅ **El IR está CERRADO el 2026-08-11**: probado con dos robots, rediseñado entero y medido. Emisión, recepción, seguimiento y evasión funcionan; la detección direccional da **tres estados, no cuatro**, y la máscara del SDK —que es del BOLT— **no describe al RVR**. Evidencias 99 y 100 |
| ~~No hay watchdog de `cmd_vel`~~ | seguridad | ✅ **resuelto**: para en 527 ms / 7.9 cm |
| ~~No hay URDF → árbol TF partido~~ | bloqueante | ✅ **resuelto**: `atriz_rvr_description` |
| ~~Driver ROS del LIDAR no instalado~~ | bloqueante | ✅ **resuelto**: `/scan` a 10.1 Hz |
| ~~Sin SLAM~~ | bloqueante | ✅ **Fase 4 CERRADA 2026-07-31**: el mapa crece al moverse (2367 → 3299 celdas) |
| ~~`imu.angular_velocity` en deg/s~~ | calidad de SLAM | ✅ **resuelto**: rad/s (REP-103) |

---

## 🔴 Prueba de aceptación: las diez fases escritas, falta UNA corrida completa (2026-08-02)

Antes de abrir la Fase 5 se construyó una **prueba de aceptación de extremo a extremo**:
`scripts/prueba_aceptacion.py`, diez fases, de arranque en frío a navegación autónoma. Diseño en
[`03_operacion/PRUEBA_ACEPTACION.md`](03_operacion/PRUEBA_ACEPTACION.md).

**Las diez fases (F0–F9) están escritas y cada una se ha ejecutado con éxito por separado.** Lo
que falta es correrlas **de un tirón**, tras un reinicio real (paso 2 del diseño) — no se ha
hecho todavía porque exige `sudo reboot`, que es un paso del usuario.

| Fase | Estado | Fuente |
|---|---|---|
| F0 arranque en frío | ✅ 11 OK · **`Restart=always` ejercitado por primera vez** (PID 725→12608) | corrida F0-F5 |
| F1 telemetría | ✅ `/odom` 16.58 Hz · `/imu` 16.56 · 7.75 V · deriva de yaw **0.002°/30 s** | corrida F0-F5 |
| F2 LIDAR | ✅ arranca apagado · 11.81 Hz · 213/260 finitos · el parche del journal aguanta | corrida F0-F5 |
| F3 luces | ⏳ los servicios responden; **falta la confirmación visual de una persona** | corrida F0-F5 |
| F4 movimiento | ✅ 29.9 / 30.4 cm · **parada de emergencia en 1.5 cm** y rechaza `move_timed` | corrida F0-F5 |
| F5 **ángulos** | ✅ **90°→86.6° · 180°→179.6° · 360°→358.4°** · signo REP-103 · ⚠️ n=1. Evidencia 48 | corrida F0-F5 |
| F6 seguridad | ✅ paró solo · 0.0 cm tras soltar `cmd_vel` · ⚠️ REVISAR de banda ya corregido en código (ver abajo) | `47_..._133324.txt` |
| F7 autónomo | ✅ 3/3 objetivos `SUCCEEDED` · errores 10.5 / 7.6 cm · ⚠️ REVISAR de marco (`map`/`odom`) ya corregido en código (ver abajo) | `47_..._133324.txt` |
| F8 web (rosbridge) | ✅ handshake `101` · **`/odom` sí llega** por una suscripción real, no solo «el puerto abierto» | `47_..._141016.txt` |
| F9 veredicto | ✅ imprime y añade los 4 `PENDIENTES_CONOCIDOS`. Con F8+F9: **2 PASA · 0 REVISAR · 0 FALLO · 4 PENDIENTE** | `47_..._141016.txt` |

⚠️ **El REVISAR de F6** (18.9 cm de `/scan` contra una banda `[0,15]` medida con otro `radius` de
`collision_monitor.yaml`) y **los dos de F7** (error 40.7 cm y desvío 13.9 cm, por mezclar el
marco `odom` de `pos_yaw()` con el objetivo mandado en `map`) están **arreglados en el código
commiteado** — banda corregida a `[15,24]` y medida por `pos_mapa()` (TF real) — pero **no se han
vuelto a verificar con una corrida nueva**, porque esta tarea tenía prohibido mover el robot.
✅ **Y el usuario contrastó F6 a mano con cinta** (evidencia 49): el `/scan` decía 18.9 cm pero el
**borde del chasis** quedó a **7–8 cm reales** (no choca), y «se movió torcido, pero fue y
regresó» es la observación física del **mismo** bug de marcos que ya explicaba el 40.7 cm.
⏳ Y salió un pendiente nuevo, sin cerrar: `laser_x = 0` es un **supuesto sin cinta detrás** (a
diferencia de `laser_z`, que sí se midió y estaba 2 cm mal) — con el LIDAR centrado el borde
debería quedar a 9.8 cm y se midieron 7–8: faltan ~2 cm sin explicar.

⚠️ **La vía libre está BLOQUEADA**, y es lo acordado: los **tres** pendientes conocidos —empezando
por **rosbridge sin autenticación**— impiden decir «se puede empezar la web» aunque el robot esté
impecable. F8 lo confirma de nuevo: rosbridge sirve datos reales (no solo el puerto abierto), y
sigue **sin autenticación**.

🔴 **Cómo lanzarla:** el modo guiado **exige un terminal de verdad**. Ni el prefijo `!` de Claude
Code ni las herramientas de un agente dan TTY, y desde el 2026-08-02 la prueba **aborta con
código 2** en vez de mover el robot sin confirmación.

```bash
ssh sphero@rvr-01.local
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash && source ~/atriz_ws/install/setup.bash
python3 -u scripts/prueba_aceptacion.py            # entera, o --desde F4
```

🔴 **El siguiente paso exacto: `sudo reboot` y correr las diez fases de un tirón** (paso 2 del
diseño). Es lo único que falta para el informe definitivo de esta prueba — todo lo demás ya está
escrito, ejecutado por partes y con sus arreglos commiteados.

---

## 🔴 Material docente: `atriz.py` y las diez prácticas — escrito, pendiente de la sesión física (2026-08-02)

> ✅ **CERRADO SALVO LA 63 (2026-08-13).** Todo lo que esta sección lista como «NO verificado»
> se midió después: ocho prácticas corridas el 2026-08-08 (evidencia 85, con cuatro fallos
> reales arreglados), y los cinco ensayos físicos —avanzar, girar, Ctrl-C ×5, luces,
> distancia_frontal— **en banda el 2026-08-13 con el usuario midiendo** (evidencia 108).
> ⏳ Falta únicamente la **práctica 63** (seguidor de línea), que espera a que haya línea en el
> aula; el calibrador de umbral (`calibrar_claro.py`) ya está en el banco. La sección se
> conserva como estaba porque documenta el plan de la sesión.

Las diez prácticas y los cinco documentos del curso estaban en **ROS 1** y no arrancaban
(`import rospy` → `ModuleNotFoundError` en la primera línea, 0 de 10), y hacían **15
publicaciones a `/cmd_vel`** en 8 ficheros — la **salida** del `collision_monitor`: si hubieran
arrancado, habrían saltado la capa de seguridad entera. Reescritos sobre una biblioteca del
laboratorio, `atriz.py`. Diseño completo, con lo verificado y lo NO VERIFICADO marcado ficha a
ficha, en [`03_operacion/API_LABORATORIO.md`](03_operacion/API_LABORATORIO.md).

### Lo que sí está verificado, por ejecución

- **89 tests** de las funciones puras de `atriz.py` y del seguidor de línea:
  `cd ~/atriz_migracion && python3 -m pytest scripts/pruebas/ -q`.
- **`Robot()` conecta, enciende el barrido y lo deja apagado al cerrar** — 10 corridas seguidas
  con código 0.
- **Un arranque fallido no deja el LIDAR encendido** — forzando el fallo de verdad, no simulado.
- **La parada de emergencia llega al driver y se libera con un acto explícito**, nunca sola.
- **`color()` avisa en vez de devolver ceros** si el robot no arrancó con
  `color_detection:=true`, y **`luces()` rechaza tipos que no son enteros**.
- **Ningún guion importa `rospy` ni escribe en `/cmd_vel`**:
  `grep -rn "cmd_vel" *.py | grep -v cmd_vel_raw` sobre `scripts/estudiantes/` da solo dos
  líneas, y las dos son comentarios de `atriz.py` que **explican** por qué no se usa, no un uso
  real.
- **Las credenciales salieron del contenido** de los cinco documentos reescritos (tarea 12,
  commit `d543cdd` en `Atriz_rvr`).

### 🔴 Lo que NO está verificado — nada se ha medido con el robot moviéndose

- Los **~60 cm** que debería recorrer `avanzar()`, con cinta.
- Los **ángulos** de `girar()` en lazo cerrado, con transportador (n≥3 a 90°, 180° y 360° —
  contra los mismos ángulos por tiempo, que es el argumento pedagógico central del documento: si
  el lazo cerrado no le gana a la constante calibrada, el argumento es falso).
- Las **cinco corridas de Ctrl-C** con el desplazamiento posterior medido con cinta — el fallo de
  `rclpy.init()` sin `SignalHandlerOptions.NO` es **intermitente** (medido: 0 líneas de parada
  contra 5 con la opción puesta, pero no siempre), así que una sola pasada verde no basta.
- Que **los faros se enciendan** de verdad (`robot.luces()`).
- **Ninguna de las diez prácticas ejecutada de principio a fin.**
- Que **`distancia_frontal()` apunte de verdad hacia delante**: el ángulo 0 de `/scan` nunca se
  contrastó con cinta.
- El **seguidor de línea con edge-following**, que nunca se ha probado sobre una línea real (ver
  abajo).
- La rama del `join` expirado en `cerrar()`: escrita, nunca ejercitada.

### 🔴 El diseño original del seguidor de línea estaba mal, y se corrigió durante la implementación

`API_LABORATORIO.md` especificaba un **PID de umbral único** sobre el canal `claro`. **No puede
funcionar**: con un solo sensor mirando hacia abajo, desviarse a la izquierda de la línea y
desviarse a la derecha dan **la misma lectura** — el signo del error no lleva información sobre
el lado, así que el PID acierta el giro la mitad de las veces y aleja al robot de la línea la
otra mitad. No se detectó al diseñar, sino al implementar (tarea 11): estaba ya escrito en
`SEGUIDOR_LINEA_EXPLICACION.md` de la versión ROS 1 que se reemplazó, y nadie lo había cruzado
contra el diseño nuevo. **Rediseñado a edge-following** por decisión del usuario: el PID (sin
tocar) decide la **magnitud** del giro; un estado que se arrastra entre vueltas del bucle
(`lado_borde`, no una lectura instantánea) decide el **signo**, y se invierte si el robot lleva
más de `tiempo_perdido_max` segundos sin reencontrar el borde. Costó además una segunda ronda: el
signo y la magnitud medían desde fronteras distintas y había un tramo (`claro` 701-949) con
**realimentación positiva** — arreglado midiendo las dos desde el mismo centro.
`API_LABORATORIO.md` está corregido para contar esto, no para esconderlo. Ver también
`CLAUDE.md`, trampas, y `.superpowers/sdd/2026-08-02-api-laboratorio/tarea-11-report.md` para el
detalle completo de las tres rondas.

### El siguiente paso exacto: la sesión física

```bash
# el usuario: reinicia el robot primero — es la única forma de comprobar que el material
# funciona sobre el estado real con el que un alumno se lo encuentra (barrido apagado, nada
# tocado). Esperar ~40 s tras el reinicio.
#   sudo reboot

cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && source /opt/ros/jazzy/setup.bash
# 🔴 99_test_ctrl_c.py NO va en este bucle: su Ctrl-C llega a TODO el grupo de
#    procesos en primer plano, asi que romperia el bucle entero — y su salida
#    correcta (130) se imprimiria como «FALLO». Va aparte y CINCO veces, porque
#    el fallo que busca es intermitente.
for f in 01_avanzar.py 02_girar.py 03_cuadrado.py 04_giro_preciso.py \
         10_movimiento_completo.py 90_template.py; do
  read -p "Coloca el robot y pulsa Enter para $f..." _
  python3 "$f" && echo "OK $f" || echo "FALLO $f"
done

# y este, suelto y repetido, midiendo con cinta lo que recorre TRAS el Ctrl-C:
python3 99_test_ctrl_c.py        # x5, pulsando a distintas alturas
# 🔴 CADUCADO: aqui ponia que 05, 11 y el seguidor "necesitan arrancar el driver
#    con color_detection:=true". YA NO. El encendido en caliente esta verificado
#    desde el 2026-08-06 (/enable_color, evidencia 76): las practicas lo hacen
#    solas. 05 y 11 se corrieron asi el 2026-08-08 (evidencia 85).
#    Del seguidor lo unico que falta es CINTA, no configuracion.
```

🔴 **Un script que «no da error» y no mueve el robot NO cuenta como verificado.** Hay que
mirarlo, no solo leer el código de salida.

📌 **Y después de esta sesión, según el orden acordado del proyecto: decidir el arranque
automático de Nav2/SLAM** — el punto que queda abierto al cierre de `API_LABORATORIO.md` y que
la Fase 5 (`Atriz_web_server`) va a necesitar tener resuelto.

---

## ⏳ PENDIENTE DE VALIDAR CON EL ROBOT ENCENDIDO (2026-08-02)

El robot se apagó para cargar (batería a **7.14 V, 20 %**; la guarda aborta a 7.00). Estas tres
cosas están **hechas y sin validar contra hardware**. Es lo primero al volver.

| Qué | Cómo se valida | Por qué no basta lo hecho |
|---|---|---|
| ✅ **La lista blanca de rosbridge** | **YA VALIDADO** el 2026-08-02: `raw_motors` al 30 % por WebSocket → **0.00 cm** de desplazamiento, y el log con las dos denegaciones. Evidencia 53 | **Cerrado.** Era el recíproco de la trampa de siempre: que no llegue respuesta no prueba que la orden no pasara |
| 🔴 **B1 y B2 de la prueba de aceptación** | `python3 -u scripts/prueba_aceptacion.py --solo F4,F6` | ✅ Ya validado el 2026-08-02: parada **1.8 cm** (rota daría 45) y watchdog **2.6 cm** (rota daría 75). **Esto ya está cerrado** |
| ⏳ **`base_length` 18.2 vs 19.0 cm** | Con escuadra, el robot quieto | Dos medidas con cinta que difieren 0.8 cm, y las dos anotadas como medidas. `laser_x = −0.005` **sí** quedó cerrado |

**El comando de la primera, preparado:**

```bash
# 1. Enciende el RVR y déjale ~2 m despejados por delante
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/probar_lista_blanca.py
# 2. Y la comprobación que la herramienta NO puede hacer sola: mandar raw_motors
#    con velocidad REAL desde un cliente y MIRAR si el robot se mueve.
#    Debe quedarse quieto. Si se mueve, la lista blanca no sirve.
```

---

## El siguiente paso, exacto

### ✅ Hecho el 2026-07-31: el keepalive del driver

**El RVR se dormía a los 300.6 s = 5.01 min** y el nodo no se enteraba. Medido y arreglado
(manual cap. 9.8a–9.8c). Se durmió **dos veces** en 12 min sin keepalive, y las dos aguantó
300.6 s **exactos**: es un temporizador del firmware.

- **`_keepalive`** cada 30 s con `get_battery_percentage()` — y publica **`/battery_state`**,
  que no existía ni en ROS 1.
- **`_vigilar_silencio`** a 1 Hz: si pasan 3 s sin muestras, avisa e intenta reanudar.
  Verificado: detectó a los 3.4 s y reanudó en 4 ms, las dos veces, 0 fallos.

Contraste: **2 huecos sin keepalive, 0 con él**, en 12 min cada prueba.

### ✅ Hecho el 2026-07-31: Fase 4 CERRADA

`slam_toolbox` mapea. Verificado moviendo el robot: **2367 → 3299 celdas**, 5.92 → 8.25 m².
Manual cap. 9, evidencia `13_fase4_cerrada.txt`.

Hicieron falta tres arreglos y corregir dos herramientas propias, y **ninguno daba un error**:

- **El yaw de `/odom` tenía el signo invertido** — el RVR reporta el cuaternión y el locator
  en FRD y el driver los copiaba crudos. `/scan` y `/odom` decían que giraba en sentidos
  contrarios. ✅ `inverted: true` del LIDAR **era correcto**; el LIDAR nunca fue el problema.
- **El acelerómetro venía en `g`**, no en m/s². Ni el driver de ROS 1 lo convertía.
- **`fixed_resolution: false`** hacía que `slam_toolbox` descartara barridos (254/255 puntos).
- **Mi herramienta medía algo imposible**: giraba en el sitio y esperaba que el mapa creciera.

### ✅ Hecho el 2026-07-31: la deriva, caracterizada

**Es pequeña y estable.** 6 corridas con las variables controladas (mismo pasillo de 3 m,
`slam_toolbox` reiniciado de cero en cada una, sin nadie cruzando):

| Recorrido | n | Deriva mediana | Peor caso | σ |
|---|---|---|---|---|
| ~159 cm | 3 | **1.0 cm** y 1.3° | 2.7 cm | 1.0 cm |
| ~237 cm | 3 | **2.7 cm** y 2.3° | 3.2 cm | 0.6 cm |

El error **cabe dentro de una celda del mapa** (5 cm). ✅ **La localización ya no es un
bloqueante para Nav2.** Los 87.8 cm de la Fase 4 fueron una anomalía, 30 veces peor que lo
normal a distancia comparable — muy probablemente por rozar obstáculos, aunque **no se
reprodujo a propósito**, así que no es una causa demostrada.

### ✅ Hecho: los TRES bugs de marcos, arreglados y verificados

**Medido, implementado pieza a pieza y verificado cada una por separado**
(evidencia `15_velocidad_odom.txt`). Los sensores del RVR estaban bien; lo que fallaba era
cómo el driver combinaba sus marcos.

| Pieza | Qué se hizo | Verificación |
|---|---|---|
| **1. Orientación** | restar el yaw del arranque | yaw en reposo: **+0.00°** (antes −74.6° / +64.9°) |
| **2. Posición** | quitar el `−Y` y rotar −90° | dirección vs yaw: **+0.03°** (antes −89.7°), y giran en el **mismo** sentido |
| **3. Velocidad** | la misma rotación + proyectar sobre el rumbo | con el robot a 84°: **(+0.101, +0.001)** vs 0.099 real (antes daba `(-0.000, -0.200)`) |

📝 Cinco arranques dieron cinco offsets de yaw distintos (+51.1°, +52.7°, +56.5°, −74.6°,
+64.9°): confirma que no había constante posible y que solo se puede medir en cada arranque.

🔴 **Y una trampa nueva que costó dar por fallida una corrección correcta:** `colcon build`
lanzado desde `src/Atriz_rvr` en vez de la raíz del workspace crea ahí dentro un **workspace
parásito**, dice «Finished», y el cambio **nunca llega al sistema**. Pasó dos veces. Está en
`CLAUDE.md` con cómo detectarlo.

### ✅ Hecho: Nav2 instalado, medido y configurado

- **`ros-jazzy-navigation2`, NO `nav2-bringup`** — 309 paquetes contra 621. `bringup` arrastra
  Gazebo, dos TurtleBots de simulación y `pocketsphinx-en-us`. Verificado: cero paquetes de
  simulador instalados, disco +900 MB.
- ✅ **`save_map` arreglado**: con `nav2-map-server` devuelve `result=0` y genera el `.pgm` +
  `.yaml`. El diagnóstico del capítulo 9.5 era correcto.
- ✅ **Velocidades medidas**: lineal **0.401 m/s** (100 % de lo comandado, en ~0.5 s) y angular
  **99–102 %** hasta 2.0 rad/s. ⚠️ Esto **retracta** el «0.40 → 63 %» que este documento llegó
  a tener: era la ventana de medida.
- **`nav2_atriz.yaml` con los valores medidos**, no los del ejemplo — el `robot_radius` del
  TurtleBot es **el doble** del real, y con él el robot se negaría a pasar por huecos por los
  que cabe.

### ✅ Hecho: Nav2 navega

| | Desde | Hasta | Resultado | Error |
|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.00, −0.03) | **SUCCEEDED** | **10 cm** |
| vuelta | (0.90, 0.00) | (0.00, 0.00) | **SUCCEEDED** | **9 cm** |

✅ El riesgo del QoS de `/scan` era **infundado**: tres suscriptores, todos BEST_EFFORT, y los
costmaps ven obstáculos de verdad (905 y 1983 celdas ocupadas).

🔴 **El primer objetivo abortó**, y no era la configuración: `Lookup would require extrapolation
into the future` en `odom → map`. Se comprobó antes de tocar nada — tolerancias puestas,
`use_sim_time` coherente, y `map → odom` a 50.0 Hz con **cero** huecos > 200 ms. Era el buffer
TF del controlador, aún sin llenar con los nodos recién arrancados. ⚠️ **Da unos segundos entre
activar Nav2 y el primer objetivo.**

### ✅ Hecho: la capa de seguridad

| Prueba | Resultado |
|---|---|
| parada contra pared a 0.25 m/s | **9.9 cm** de hueco |
| parada contra pared a 0.40 m/s | **10.6 / 10.7 cm** — más margen, no menos |
| escape pegado a la pared (1.1 cm) | retrocedió **196 cm** ✅ |
| LIDAR muerto, comandando 0.10 m/s | **0.0 cm** ✅ bloqueado |
| Nav2 con la seguridad en medio | **SUCCEEDED**, 9 cm de error |

🔴 **Dos hallazgos que no daban ningún error:**

1. **El `behavior_server` de Nav2 publicaba en `/cmd_vel`** — cinco publicadores, uno por
   conducta de recuperación (`spin`, `backup`…), saltándose el monitor. Y son justo las que se
   ejecutan cuando el robot está atascado, o sea pegado a algo. Salió de **contar
   publicadores**: salían seis donde debía haber uno. Arreglado.
2. **`approach` no es una parada de seguridad, es un frenado suave.** Con `radius: 0.11` el
   robot paró a **1.1 cm** de la pared: la asíntota del controlador es el contacto. La holgura
   se consigue **inflando el círculo** — `hueco ≈ radius − 0.091`.

🔴 **El límite que ninguna configuración arregla:** el plano del LIDAR está a **15.5 cm** del
suelo. Todo lo más bajo es **invisible** y el robot lo embestirá. Tiene que ir en las
instrucciones a los estudiantes.

### ✅ Hecho: navegando a 0.40 m/s

| | Desde | Hasta | Resultado | Error | v (p90) |
|---|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.50, 0.00) | **SUCCEEDED** | **8 cm** | 0.412 m/s |
| vuelta | (1.42, −0.01) | (0.00, 0.00) | **SUCCEEDED** | **8 cm** | 0.409 m/s |

Lo que había que comprobar no era que llegara, sino que **de verdad fuera a 0.40**: meseta de
**0.407 m/s** alcanzada en 0.9 s. Y subir la velocidad **no empeoró la precisión** — 8 cm
contra los 9–10 de antes.

Se subió con las tres condiciones medidas: dos navegaciones limpias a 0.25, el
`collision_monitor` verificado, y **a 0.40 la seguridad deja más hueco que a 0.25** (10.6 cm
contra 8.0). Ese último dato es el que quitaba el miedo.

🔴 **Y salió un fallo nuevo: `save_map` da 255 de forma intermitente.** No es el de la Fase 4
(`Package 'nav2_map_server' not found`): aquí el `map_saver` arranca y **se queda sin mapa**.
Es una carrera entre `map_update_interval: 5.0` y el `save_map_timeout: 2.0` del saver. Arreglo
propuesto en el manual 11.11, **sin verificar**.

### ✅ Hecho: rodea obstáculos

Objetivo a 1.50 m —el mismo que la corrida limpia, para que el obstáculo fuera la única
variable— con una caja de 16 cm a 0.75 m bloqueando la recta:

```
x=+0.00 y=+0.00 → x=+0.62 y=-0.29 → x=+0.79 y=-0.30 → x=+1.28 y=-0.03
                                     ↑ justo a la altura del obstáculo
```

| | Resultado | | Error | Junto al obstáculo |
|---|---|---|---|---|
| ida 1 | **SUCCEEDED** | 5 s | 8 cm | derecha, y=−0.26 |
| vuelta 1 | **SUCCEEDED** | 13 s | 8 cm | derecha, y=−0.32 |
| ida 2 | **SUCCEEDED** | 5 s | 9 cm | derecha, y=−0.26 |
| vuelta 2 | **SUCCEEDED** | 12 s | 8 cm | derecha, y=−0.30 |

Rodea siempre por el lado con más hueco (63 cm por la derecha contra 44 por la izquierda), con
el mismo desvío. **Es repetible.**

🔴 **El hallazgo: la capa de seguridad hizo abortar a Nav2.** `Failed to make progress` → el
`SimpleProgressChecker` exige 0.5 m en 10 s (5 cm/s) y el `collision_monitor` había frenado al
40 %. **Con una capa de seguridad delante, ir despacio ya no es prueba de estar atascado.**
Relajado a 0.25 m en 15 s; tras el cambio, **cero abortos en cuatro navegaciones**.

✅ **Y `save_map` queda arreglado y verificado**: el servicio con su timeout de 2 s falla ~1 de
cada 3 (0, **255**, 0); `map_saver_cli` con `save_map_timeout:=10.0` funciona. Confirma que era
una carrera contra el `map_update_interval: 5.0`.

### ✅ Hecho: el paso de 40 cm, y las cotas corregidas

Con `radius: 0.18` **no cruzaba**. Y el compromiso queda cuantificado:

| `radius` | para a | pasillo mínimo | banda de inmovilización |
|---|---|---|---|
| 0.14 | 5 cm | 28 cm | 0 — pero por debajo del ruido del LIDAR |
| **0.15** | **6.3 cm medido** | **30 cm** | **0.6 cm** ← el actual desde 2026-08-09 |
| 0.18 | 9.3 cm medido | 36 cm | 3.6 cm ← el anterior |
| 0.20 | 11 cm | 40 cm | 5.6 cm |

🔄 **Cambiado a `0.15` el 2026-08-09** (evidencia 94), con el hueco al parar medido a las dos
velocidades y la aceptación F6 verificada. El pasillo mínimo baja de 36 a **30 cm**.

Para 16 robots en un laboratorio remoto **donde nadie puede levantarlos**, parar a 9–11 cm de
las paredes vale más que cruzar huecos de 40 cm — pero es una **decisión de laboratorio**.

**Corregido:** URDF a 18 × 22 cm y `robot_radius` 0.11 → **0.145**. Ningún frame TF se mueve.

⚠️ **Retirado:** intenté medir el mismo paso con `radius: 0.15` para dar la curva completa, y
el buscador eligió **otro hueco** (33.9 cm, a −61.5° de rumbo). Cruzó *un* hueco, no *el*
hueco. No cuenta.

### ✅ Hecho: el robot medido entero

| Cota | Medido | Antes |
|---|---|---|
| frente-atrás | **18.2 cm** | 21.8 (ficha, cruzado) |
| lado a lado | **21.7 cm** | 18.5 (ficha, cruzado) |
| suelo → tapa | **7.0 cm** | 11.4 (ficha) |
| **suelo → centro del disco (`laser_z`)** | **15.5 cm** | 17.45 (derivado) |
| ancho de oruga | **3.5 cm** | 2.5 (ficha) |
| `wheel_separation` (entre centros) | **18.3 cm** | 15.0 (ficha) |
| `wheel_radius` (suelo → eje) | **3.5 cm** | 3.2 (ficha) |

✅ **Cierra por dos caminos independientes**: `14.8 + 2 × 3.5 = 21.8 ≈ 21.7` de ancho, y
`wheel_radius 3.5` da una oruga de 7 cm de diámetro = `base_height`, así que la caja del chasis
va del suelo a 7 cm — justo como se ve el RVR.

✅ **El modelo geométrico está completo.** Solo falta `imu_z`, que exige abrir el robot y hoy
no afecta a nada. El LIDAR está confirmado **centrado y nivelado**.

### ✅ Hecho: referenciar la posición, y con eso los fallos desaparecen

El problema no era de SLAM: era del banco de pruebas. Las herramientas repetían N corridas
dando por hecho que el robot volvía al punto de partida, y **no volvía**.

`referenciar_posicion.py` ajusta una recta a la pared frontal, conduce a la distancia objetivo y
**luego** se alinea (ese orden importa: al revés, conducir vuelve a torcer el rumbo).

| | sin referenciar | con referenciar |
|---|---|---|
| dispersión de posición, adelante | 0.47 m | **0.06 m** |
| dispersión lateral | 0.81 m | **0.03 m** |
| fallos > 5 cm | **5 de 24** | **0 de 12** |
| peor caso | **56.1 cm** | **4.4 cm** |

⚠️ **Fisher exacto de 0/12 contra 5/24 da p = 0.113**: sugerente, no concluyente al 5 %. Lo
indiscutible es la dispersión de posición; que los fallos se vayan a la vez es coherente pero
pide otra tanda para cerrarlo.

### ✅ Decidido: no se persigue el roll — y el driver deja de publicarlo

Con el ruido bajado, las dos distancias apuntaban en el mismo sentido (CORTA +1.30 cm, LARGA
+1.40) con la magnitud predicha, pero **p = 0.142** con n=6 por rama. Cerrarlo costaría **~62
corridas y 5.2 horas de robot** para un efecto de ~1 cm sobre una tolerancia de **10 cm**.
**Decisión del usuario el 2026-07-31: no se persigue.**

🔴 **Pero eso no deja el roll publicado.** `publicar_inclinacion` pasa a **`false` por
defecto**, y la razón **no depende** de la medida que no se va a hacer: la inclinación **es
falsa** (suelo plano con nivel, error del acelerómetro fijo en el marco del robot, `|g|` un
3.8 % corto). Publicar 6.9° que no existen en `odom → base_footprint` es publicar un dato
incorrecto. Verificado: `/odom` da `roll +0.00° pitch +0.00°`.

### ✅ Hecho: Fase 4c — `map_server` + AMCL

El ciclo completo funciona: **mapear → guardar → localizar → navegar** sobre el mapa, sin SLAM.

```
mapear con slam_toolbox      celdas 486 → 2774
guardar con map_saver_cli    mapa_amcl.pgm
parar SLAM                   `map` deja de existir  ✅
localizar                    map_server y amcl active [3]
seguir la pose               ODOM 61.8 cm · AMCL 61.9 · dif 0.1 cm
navegar con Nav2             SUCCEEDED, error 8 cm · dif ODOM/AMCL 1.1 cm
```

✅ **Y el launch se niega a arrancar** si `slam_toolbox` está vivo o si el mapa no existe — las
dos probadas. Los dos publican `map → odom` y juntos parten el árbol TF **sin dar error**.

🔴 **AMCL cuesta casi el doble que SLAM** (8.8 % contra 4.8 %), al revés de lo que suponía.
**El argumento para AMCL es el marco compartido, no el coste.**

⚠️ **Sin resolver:** la σyaw sube a **18°** navegando (mapa pequeño y poco distintivo, sin
comprobar), y **la pose inicial tendrá que venir por robot** para la flota. Manual, **cap. 14**.

### ✅ Hecho: la parada de emergencia, que fallaba por TRES causas

Falló tres veces y siempre en silencio, con `200 OK` en la web: **nombre** de topic (ROS 1),
**namespace** `/rvr/` (al portar), y **QoS** — el driver se suscribía `TRANSIENT_LOCAL`, que en
un suscriptor **solo restringe** y no empareja con ningún publicador por defecto.

Verificada disparando los tres nombres: **3 paradas, 3 liberaciones, 0 avisos de QoS**.
Manual, **cap. 15**.

✅ ~~Pero no corta lo que venga de Nav2~~ — **FALSO, y ya estaba arreglado cuando se escribió
esto.** El nodo `cancelar_nav2` manda `CANCEL_ALL` a `NavigateToPose`. Verificado con control:
objetivo `CANCELED` y **0.0 cm** al liberar la parada; sin él, objetivo **ACTIVO** y el robot
**arrancó solo 34.7 cm** (manual, cap. 15.4).

🔴 Es la **tercera** vez que esta misma frase sobrevive en un fichero distinto tras corregirla.
Es el caso que `CLAUDE.md` usa como ejemplo canónico de deriva documental — **una función de
seguridad descrita como rota cuando funciona**.

### ✅ Hecho: los servicios del driver, de 1 a 18

Todos **probados contra el robot**, y en orden de riesgo: primero lo que no mueve nada.

```
move_timed  2 s a 0.15 m/s   ->  30.3 cm medidos contra 30   (101 %)
raw_motors  reversa 25 %     ->  30.7 cm, para al mandar modo 0
move_to_pos_and_yaw 0.20 m   ->  19.5 cm                     ( 97 %)
con la parada de emergencia  ->  success=False, 0.0 cm       ✅
```

🔴 **Y destapó que `/color` publicaba `[0,0,0]` desde siempre.** El sensor no da nada sin su
luz —canal claro **4 apagada contra 741 encendida**, 185×— y el driver **nunca la encendía**.
El topic estaba en la lista de «verificado». Arreglado con el parámetro `color_detection`
(por defecto `false`, porque enciende un LED bajo el chasis).

✅ Y **SÍ se puede encender bajo demanda**, desde el 2026-08-06: servicio
**`enable_color`** (`std_srvs/SetBool`), y en la biblioteca del alumno
`robot.sensor_color(True)`. Canal claro **1 apagada contra 1320 encendida**, reversible.
🔴 Aquí ponía lo contrario —«con el streaming ya configurado no hace nada»— y **nunca estuvo
medido**: la prueba de julio encendía y apagaba dentro de la misma llamada. Evidencia 76.

⚠️ **Los servicios de movimiento se saltan el `collision_monitor` y el watchdog** — hablan al
RVR por el puerto serie, no por un topic. Solo los para la parada de emergencia. Manual,
**cap. 16**.

### ✅ Hecho: `provision.sh` y `verificar_robot.sh` al día

🔴 **`provision.sh` nunca instalaba `navigation2`.** Un robot aprovisionado con el script tenía
driver, LIDAR y SLAM — y **no podía navegar, ni tenía capa de seguridad, ni localización**.
Añadido, comprobando además que los binarios existan y que no entre el simulador.

**`verificar_robot.sh` pasa de 50 a 84 comprobaciones** (con `--hardware`, y esa misma tarde a **91**): los binarios de
Nav2, los 9 ficheros de config y launch, los **valores medidos** (`robot_radius` 0.145, URDF
0.182 × 0.217 —hoy **0.190 × 0.217**, cerrado el 2026-08-09 con el LIDAR—, `laser_z` 0.155), los valores **por defecto que son decisiones**
(`publicar_inclinacion` y `color_detection` en `false`, la parada en VOLATILE), y los **18
servicios preguntando a un cliente** — no a `ros2 service list`, que miente por omisión.

🔴 **Y el verificador tenía tres fallos propios** —esa misma tarde salieron **tres más**, van seis (evidencia 32)—, encontrados al ejecutarlo: comprobaba el
driver de **ROS 1**, contaba un **comentario** como si fuera un ajuste, y daba el LIDAR por roto
cuando el driver tenía el puerto ocupado. Los tres corregidos.

```
sin --hardware   76 correctas · 1 aviso · 0 fallos
con --hardware   105 correctas · 0 fallos   (2026-08-01)
sin  --hardware   154 correctas · 3 avisos · 0 fallos   (2026-08-11)
rvr-02 --hardware 151 correctas · 0 fallos   (2026-08-11, recien aprovisionado)
```

### ✅ Dos decisiones CERRADAS el 2026-08-01 (eran los últimos bloqueos de la Fase 5)

Las dos las destapó alinear `ARQUITECTURA.md` con el robot real, y las dos afectan al cliente
web: cambiarlas después obligaría a tocar los 16 robots **y** el cliente a la vez.

**1. ✅ SIN NAMESPACE.** Los topics son `/odom`, no `/rvr_01/odom`.

- El **`ROS_DOMAIN_ID` por robot** ya da aislamiento DDS **total** — los robots no se ven entre sí
  ni queriendo. El namespace resolvería un problema que no existe.
- La web habla por **un WebSocket por robot** (`ws://rvr-07.local:9090`). Poner `/rvr_07/odom`
  dentro de un canal que solo alcanza al robot 7 es escribir el número dos veces.
- 🔴 **Y la parada de emergencia ya falló una vez POR UN NAMESPACE**: al portar de ROS 1 se coló
  un `/rvr/` y falló en silencio con `200 OK`. Van cuatro fallos de la parada; no se le regala el
  quinto multiplicado por 16.

⚠️ Un namespace **no renombra los `frame_id` de TF**, así que ni siquiera resuelve el caso para el
que suele invocarse. El argumento `namespace` de los launch se deja como camino de escape — y al
cerrar esto se descubrió que **ese camino estaba roto**: dos `frame_id` a fuego en el driver, ya
convertidos en el parámetro `body_frame`.

**2. ✅ EL OFICIAL ES `/emergency_stop`**, con QoS **RELIABLE + VOLATILE** (`TRANSIENT_LOCAL` fue
la tercera causa de fallo, y rosbridge no lo es).

El driver **sigue escuchando los tres** y eso no se toca: con un botón de emergencia el modo de
fallo que importa es «el mensaje no llega». Escuchar de más no cuesta nada.

### 📌 El tercer repositorio: `Atriz_web_server`

**No está clonado en este robot ni se ha tocado**, a propósito: la web es la Fase 5 y es un
repositorio **público con una credencial expuesta**.

Lo que le afecta de todo lo hecho está recogido en
`00_auditoria/evidencia_24_04/28_pendiente_web.txt`, para que quien abra la Fase 5 no tenga que
reconstruirlo. En resumen:

- ✅ **La parada de emergencia ya funciona sin tocar la web**: el driver escucha
  `/rvr/emergency_stop` con el QoS que usa rosbridge, y desde el 2026-07-31 **también cancela
  los objetivos de Nav2** — antes, al *liberarla*, el robot arrancaba solo (34.7 cm medidos).
- 🔴 **NUEVO Y OBLIGATORIO: la web tendrá que llamar a `/start_scan` al empezar una sesión.**
  Los robots arrancan solos pero con el barrido del lidar **parado**, y sin `/scan` el
  `collision_monitor` bloquea el movimiento. Un robot recién encendido **no obedece `cmd_vel`**,
  y desde la web se verá igual que uno averiado.
- 📝 La web ya **no tiene que arrancar nada por SSH**: `atriz-robot.service` lo hace, y se
  recupera solo de un reinicio (probado).
- La web puede usar ya **doce servicios** por la lista blanca —de los 19 del driver más los dos
  del `supervisor_navegacion`— y **15 topics de lectura**. 🔴 Con dos avisos: los servicios de
  movimiento **se saltan la capa de seguridad**, y hay que publicar en **`/cmd_vel_raw`**, no en
  `/cmd_vel`.
- ✅ **Y desde el 2026-08-07 puede arrancar y parar SLAM y Nav2**: `/pedir_slam` y `/pedir_nav`
  (`std_srvs/SetBool`), con `/estado_navegacion` diciendo si funcionan de verdad. Los dos
  verificados de extremo a extremo (evidencia 80).
- 📝 `/color` publica `[0,0,0]` hasta encender la luz con `/enable_color`, que funciona **en
  caliente** desde el 2026-08-06 (evidencia 76). El parámetro `color_detection` solo fija el
  estado inicial.
- 🔴 La **credencial sigue expuesta**, y quitarla exige limpiar el **historial** de git.

### ✅ ~~Suposición aceptada: `provision.sh` no se ha probado entero~~ — **LEVANTADA el 2026-08-11**

**`provision.sh` se ha ejecutado ENTERO sobre un 24.04 limpio: 96 ✓ · 16 avisos · 0 fallos.** La
suposición más cara del proyecto está cerrada. Paso a paso completo en la evidencia 98.

No a la primera: tiró los dos últimos pasos con **el mismo fallo del 2026-08-10** —o sea
reproducible—, causado por un `install -d -o usuario .../atriz_ws/src` que deja el **padre**
`atriz_ws` de root. Arreglado en el guion, con reparación de lo ya creado, y
`verificar_robot.sh` pasa a vigilar el dueño del workspace.

> Lo de abajo es el estado del 2026-08-10, ya superado. Se conserva porque describe el fallo que
> resultó ser reproducible.

⏳ ~~**No ha terminado.** Parado en `colcon build` (`Permission denied: 'log'`), con `fase_7`
negándose en cadena. ✅ Descartado que lo cause el guion —compila con `sudo -u` y crea el
workspace con el dueño correcto—; ⏳ **la causa real, sin determinar**.~~

🔴 **Y aquí está la frase que retrasó el diagnóstico un día entero:** *«Descartado que lo cause el
guion — crea el workspace con el dueño correcto»*. **Era exactamente al revés: lo causaba el
guion, y precisamente por el dueño del workspace.** Se descartó leyendo el código —que dice
`install -d -o "$USUARIO"`, y suena bien— en vez de mirar el directorio, que decía `root`. Es la
regla del proyecto incumplida: *comprueba el efecto, no el código*. Aplicada a un guion, mirar el
fuente **es** mirar el código de salida.

📌 **Regla para lo que salga: va al guion, no se arregla a mano.** Lo que frene a rvr-02 frenará
a los catorce siguientes si se queda en una sesión de SSH.

**Texto original, conservado porque explica la decisión:** Decisión del usuario el 2026-07-31: no
se reflashea rvr-01. Es el único robot montado y probar el script de principio a fin exigiría un
24.04 limpio. Se **asume** que funciona hasta tener una tarjeta de repuesto.

✅ **Verificado:** sintaxis, una pasada con `--simular` (código 0 recorriendo las nueve
secciones), la comprobación de los cuatro binarios de Nav2 —que **no** se simula— y la
idempotencia.

🔴 **Sin verificar, y es lo que importa:** la simulación convierte en no-operación **justo lo
que instala y compila** — el `full-upgrade`, el arreglo del UART, la higiene del SO, el
`apt install`, compilar YDLidar-SDK y el `colcon build`. De una pasada limpia **no se ha probado
nada**.

⚠️ **No construyas la imagen dorada sin levantar esto.** El riesgo no es que falle: es que falle
**en el robot 7 de 16**, con seis ya desplegados.
Detalle: `00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.

### 1. ✅ Las unidades systemd — FUNCIONANDO, probadas con un reinicio

✅ Instalado, habilitado y **arrancado** el 2026-07-31, comprobado por efecto: `ExecStartPost`
`status=0/SUCCESS`, `/scan` a **0.00 Hz** (barrido parado), `/odom` a **16.54 Hz** y `/cmd_vel`
con un solo publicador.

✅ **Y probado con un reinicio de verdad:** volvió solo (PID 711), `/scan` a 0.00 Hz, `/odom` a
16.49, y el robot **bloqueado sin barrido** — 0.0 cm contra 9.9 del control.

📝 Sin ejercitar: la espera de puertos del envoltorio (siempre `tras 0s`) y `Restart=always`.
Son redes de seguridad sin estrenar. Evidencia 33.

✅ **`provision.sh` YA lo instala** (paso 8/9), desde el 2026-08-01. Era un requisito para la
imagen dorada: construirla antes habría dado 16 robots sin arranque automático. Manual, cap. 17.

🔴 **Y tiene que arrancar con el lidar PARADO.** Medido el 2026-07-31: el X2 gira siempre, a
2.7 Hz en reposo y 11.8 Hz escaneando. Hoy se queda en 2.7 porque no hay nada corriendo; en
cuanto los 16 robots levanten `robot.launch.py` solos, pasará a **11.8 Hz permanentes, 24/7, en
los 16**. Sería peor que ahora, y llegaría como efecto secundario de una tarea que no habla de
lidares.

El driver ya trae `/stop_scan` y `/start_scan` (verificados, y frenan el motor de verdad), así
que basta con arrancar parado y activar al empezar la sesión. La seguridad encaja sola: sin
`/scan` el `collision_monitor` no deja conducir. Manual, cap. 8.4a.

Todo lo de hoy —`collision_monitor`, localización con AMCL, URDF corregido,
`publicar_inclinacion`, `color_detection`, `robot_radius`, los 18 servicios— **tiene que estar
en el script de aprovisionamiento y en el verificador**, o la imagen dorada no lo tendrá. Es la
regla del propio proyecto: *la imagen dorada es el atajo, `provision.sh` es la verdad*.

✅ **Ya hecho:** las unidades **systemd** de arranque automático están instaladas, probadas con
un reinicio real, y `provision.sh` las instala (paso 8/9). Quedan sin
portar `ConfigureStreaming` y `StartStreaming` —a propósito: pueden romper la telemetría del
propio driver.

📌 **Aplazado hasta tener el circuito definitivo:** mapear el laboratorio real y la pose inicial
por robot.

### ✅ Hecho: las paradas re-medidas

| velocidad | n | **medido** | recalculado | dif |
|---|---|---|---|---|
| 0.25 m/s | 1 | **9.9 cm** | 9.8 | +0.1 |
| 0.40 m/s | 2 | **10.6 / 10.7 cm** | 10.8 | −0.2 |

El modelo afinado: asíntota `0.18 − 0.091 = 8.9 cm`, y el margen sobre ella **crece con la
velocidad** (+1.0 cm a 0.25, +1.8 a 0.40). La holgura **no se degrada al acelerar: mejora**.

🔄 **Actualizado el 2026-08-09** (evidencias 94 y 95): la media longitud real es **0.095** —no
0.091— y el `radius` pasó a **0.15**, así que la asíntota vigente es `0.15 − 0.095 = 5.5 cm`.
Medido con el valor nuevo: **6.3 cm a 0.25 m/s y 7.4 / 6.6 a 0.40**. La conclusión de que el margen
crece con la velocidad **se conserva**: +0.8 cm a 0.25 y +1.5 a 0.40.

📝 Cambiar `laser_z` y `wheel_radius` **no alteró el comportamiento**, como se preveía: son
traslaciones en Z y el monitor trabaja en el plano.

### ✅ ~~Cargar el robot y medir la deriva con y sin el roll~~ — CERRADO, no se persigue

El interruptor ya está: `robot.launch.py publicar_inclinacion:=false`. Lo que falta es
ejecutar **12 corridas** de `caracterizar_deriva_slam.py`, 6 por condición.

**El diseño, y por qué no se puede recortar:**

- 🔴 **La línea base anterior no vale.** Se hizo con `laser_z = 0.1745`, y el desplazamiento
  lateral que induce el roll escala con esa altura: 2.4 cm entonces, **2.2 cm ahora**.
- 🔴 **Las condiciones se ALTERNAN**, no 6 y 6. Así un corte por batería deja datos
  **balanceados**, y el nivel de carga deja de poder colarse como variable.
- ⚠️ **No se puede bajar a 2 por condición.** El efecto buscado es de ~**1 cm** y la dispersión
  ya medida es **σ = 0.6–1.0 cm**: saldría dentro del ruido.

⏳ Y falta un dato que el proyecto no tiene y hará falta con 16 robots: **cuánto consume el RVR
por minuto conduciendo**. Es lo que impide saber si un 34 % aguanta 40 min.

Después: el **barrido de `radius`** contra un mismo paso estrecho.

### 2. ✅ RESUELTO: la inclinación de ~8° no existe

El usuario midió del suelo al disco del LIDAR **en cuatro puntos** y salen **iguales**. 8°
habrían dado ~1.1 cm de diferencia sobre los 7.6 cm del disco: se habrían visto. **El robot
está físicamente horizontal.**

Y las «tres vías independientes» **no eran independientes**: el árbol TF sale de
`odom.pose.pose.orientation`, que el driver copia del cuaternión del RVR, que calcula la IMU —
y el acelerómetro es el mismo chip. **Una sola fuente contada tres veces.** El TF no
confirmaba: repetía.

✅ **YA APLICADO** (2026-07-31): `publicar_inclinacion` es `false` por defecto y `/odom` sale
con `roll +0.00° pitch +0.00°`. ⚠️ Y no eran «~8° de roll»: son **6.9° y están en el PITCH**.
Texto original: el driver publica un roll falso de ~8° en `/odom` y en TF. Eso
inclina el plano del láser y comprime los alcances un **1 %** (~1 cm por metro) — y la deriva
de SLAM medida es de **1–3 cm**. El orden de magnitud coincide: **podría ser parte de ella**.
La corrección es una línea y **no se aplica sin medirla**. Manual, **cap. 13**.

<details><summary>Lo que decía antes de resolverse</summary>

### 🔴 La inclinación de ~8°, confirmada por TRES vías

Árbol TF, `Roll` de la IMU y el acelerómetro con unidades correctas. Causa sin determinar.

📝 La caracterización de la deriva **acota su gravedad**: con la inclinación presente, la
deriva es de 2.7 cm, así que no está arruinando el emparejado. Hay que resolverla para Nav2
—por REP-105 `odom → base_footprint` debería ser plana— pero **no es urgente**.

</details>

---

## Histórico de fases cerradas

**Fase 2 del plan — portar el driver a `rclpy`.** Era el trabajo grande.

✅ **La Fase 2 está ARRANCADA y el núcleo funciona** (2026-07-30, rama **`ros2`**, commit
`80e1cbf`). **Verificado contra el robot real** — no lo repitas:

| | |
|---|---|
| `atriz_rvr_msgs` | ✅ portado a `ament_cmake` + `rosidl`, 6 msg + 20 srv |
| `atriz_rvr_driver` | ✅ portado a `ament_python`, el nodo corre |
| `/odom` | ✅ **16.671 Hz**, σ 0.47 ms (ROS 1 daba 16.59) |
| `imu.angular_velocity` | ✅ rad/s (antes deg/s, violaba REP-103) |
| árbol TF | ✅ `odom → base_footprint` (antes `rvr_base_link`, partido; y `base_link` fue mal hasta la Fase 4, ver abajo) |
| `cmd_vel` | ✅ 34 cm a 0.15 m/s en 2 s |
| watchdog | ✅ quieto en 527 ms, ~7.9 cm. **Primera vez que se prueba** |
| Fase 2.1 limpieza | ✅ 79 ficheros y 700 KB menos |

**Lo que queda del nodo:** 16 de los 20 servicios y 4 topics, listados al final de
`rvr_driver_node.py`.

✅ **Fase 3 COMPLETA, incluido el LIDAR** (commit `b117791`). Un comando arranca el robot
entero: `ros2 launch atriz_rvr_bringup robot.launch.py` → `/odom` 16.99 Hz, `/scan` 10.1 Hz,
árbol TF resuelto.

✅ **El riesgo del QoS de `/scan` era infundado**, comprobado en la Fase 4: `slam_toolbox` se
suscribe con **BEST_EFFORT**, igual que publica el driver del LIDAR. Emparejan. Sigue siendo
cierto que **`rclpy` pide RELIABLE por defecto**, así que cualquier suscriptor propio a `/scan`
tiene que pedir BEST_EFFORT explícitamente o no recibirá nada, sin error.

✅ **Fase 4 PARCIAL** (manual cap. 9, evidencia `11_slam_fase4.txt`). `slam_toolbox` arranca,
se activa y publica `/map` a 0.200 Hz; el árbol TF llega hasta `map`. Coste: **4.5 % de CPU**,
y ~24 % con todo a la vez. Dos hallazgos que hubo que arreglar:

- **Es un nodo de ciclo de vida**: arrancaba en `unconfigured`, vivo y sin hacer nada.
  `slam.launch.py` ahora usa `LifecycleNode` + `configure`/`activate`.
- **`base_link` tenía dos padres** (`odom → base_link` del driver y `base_footprint →
  base_link` del URDF) → el árbol se partía y `slam_toolbox` repetía `Failed to compute odom
  pose`. El driver publica ahora **`odom → base_footprint`** (REP-105).

⚠️ **Y la Fase 3 lo había dado por bueno**: su comprobación `tf2_echo odom laser` **pasaba**,
resolviendo por el camino equivocado. **Comprueba el transform que pide el consumidor, con sus
frames exactos** — aquí `tf2_echo odom base_footprint`.

📝 **`save_map` no funciona sin Nav2** (`result=255`, `Package 'nav2_map_server' not found`).
Para guardar un mapa hoy: `serialize_map`, que es nativo (`result=0`).

✅ **Fase 3.1 cerrada** (commit `719c769`): el paquete `atriz_rvr_description` une el árbol TF, que
estaba partido en dos y era el bloqueante raíz de SLAM. **Verificado sobre el robot:**
`tf2_echo odom laser` resuelve con `Translation: [-0.018, -0.002, 0.141]`, y antes respondía
«Could not find a connection».

Medida del LIDAR: **17.45 cm** sobre el suelo (centrado, 4 cm de hueco medidos). El proyecto
arrastraba `0.10`, que se quedaba **7.4 cm corto** y habría inclinado el mapa.

> ⚠️ **Ese 17.45 también resultó estar mal**, y por lo mismo: era una **suma derivada** con el
> alto del RVR sacado de su ficha (11.4 cm cuando son **7.0**). Medido con regla el 2026-07-31,
> el plano de barrido está a **15.5 cm**. Manual, cap. 12.8.

⚠️ **RETRACTADO el 2026-07-31 — se conserva porque explica cómo se llegó al error.**

Esto decía: «un bloqueante nuevo antes de SLAM: la velocidad de `/odom` es basura. El stream
`Velocity` del RVR reporta 0.001 m/s con el robot a 0.147 m/s reales».

**La observación era cierta; la conclusión, falsa.** `Velocity` es **exacto** (0 % de error en
módulo, 0.1° en dirección) y viene en el marco del **mundo**. Se leyó solo su componente X con
el robot encarado a ~90° de ese eje, donde X vale ~0 aunque el robot cruce la habitación.
El fallo está en el **driver**, no en el sensor. Ver `15_velocidad_odom.txt`.

🔴 **Hasta que esto se haga, el driver del robot NO se ha ejecutado nunca en este sistema — y
no puede.** No es «pendiente de probar», es **imposible**: `Atriz_rvr_node.py` es ROS 1.
Medido el 2026-07-30 sobre `migracion-ros2` (`24c7749`):

| | |
|---|---|
| `Atriz_rvr_node.py` | **1704 líneas** |
| referencias a `rospy.*` | **99** (y `rospy` no existe en ROS 2) |
| llamadas a `asyncio.run()` | **48**, cada una crea y destruye un event loop entero |
| paquetes | 3, los tres **catkin** — no `ament` |
| interfaces | 6 `.msg` + 20 `.srv`, todas registradas correctamente |

`colcon build` fallará, y **debe** fallar. Lo que sí está validado es el **SDK** (Etapa D, 🟢
GO): es la pieza insustituible, la única que sabe hablar con el RVR. El driver es código propio
y por tanto reescribible.

**Lo que el port tiene que incluir** (plan, Fase 2, apartados 2.1 a 2.4):

1. **Limpieza previa.** Borrar lastre en vez de portarlo: los `.cpp` y `src/rvr++/`
   (`hardware_interface` que nunca se ejecutó), el paquete `atriz_rvr_serial`, y
   `scripts/rvr-ros.py` — confirmado el 2026-07-30 que **no tiene bit de ejecución**.
2. **Los 3 paquetes catkin → `ament`**, y `atriz_rvr_msgs` a `rosidl`.
3. **El arreglo estructural.** Hoy el event loop de asyncio solo avanza en ráfagas dentro de un
   `while not rospy.is_shutdown()`. Pasa a vivir en su propio hilo, y los comandos entran con
   `asyncio.run_coroutine_threadsafe` en lugar de crear un loop por cada `cmd_vel`.
4. ✅ ~~Watchdog de `cmd_vel` — hoy no existe~~ — **existía ya en ROS 1** y sigue en el port:
   `cmd_vel_timeout` = **0.3 s**, medido en **527 ms / 7.9 cm**. Este párrafo cita el plan de la
   Fase 2, que estaba equivocado. Texto original: si cae la red, el robot sigue
   ejecutando el último comando indefinidamente. Debe parar los motores si no llega `cmd_vel`
   en 500 ms.
5. 🔴 **`imu.angular_velocity` a rad/s.** Hoy va en deg/s y viola REP-103, lo que degrada la
   calidad de SLAM. Y `gyroscope_handler` publica **dos veces**, en unidades distintas.
6. Parametrizar `serial_port` (por defecto `/dev/rvr`), `baud`, los frames y
   `streaming_interval_ms` con `declare_parameter`. Nada hardcodeado.

**Lo que NO hay que volver a tocar:** el `interval=60` ya está aplicado (16.59 Hz medidos), y
el puerto ya es `/dev/rvr`. Ambos verificados hoy en el SDK.

**Después del port viene la Fase 3, el URDF**, que el plan llama **el bloqueante raíz**: el
árbol TF está partido en dos (`odom → rvr_base_link` por un lado, el LIDAR colgando de
`base_link` por otro) y sin un árbol conectado SLAM es imposible por bien que funcione el
driver.

✅ **El `~/.bashrc` ya no es un problema (2026-08-03).** Lo era por dos motivos y los dos están
cerrados:

- `ROS_DOMAIN_ID` salió de ahí el 2026-07-31 y lo pone `/etc/profile.d/atriz-robot.sh`.
- El **entorno de ROS** (los dos `source`) vivía solo en el `.bashrc` y **ningún script lo
  escribía**, así que un robot montado desde cero con los repositorios habría tenido shells sin
  `ros2`. Ahora está en `scripts/sistema/atriz-ros.sh` → `/etc/profile.d/atriz-ros.sh`, **sin
  identidad dentro**, y lo instala `fase_7_systemd.sh`.

En el `.bashrc` queda **una línea**, que `fase_7` añade de forma idempotente: el puente para los
shells interactivos que **no** son de login (`tmux`, `su`, un `bash` suelto), que no leen
`/etc/profile.d`. `verificar_robot.sh` lo comprueba **lanzando un shell limpio con `env -i`**, no
con un `grep`: la primera versión de esa aserción heredaba el PATH del padre y pasaba con el
puente y sin él.

Con eso desaparece la trampa del «el `.bashrc` se lee después y gana», que el proyecto
documentaba en cuatro sitios distintos.

### Ya hecho, no lo repitas

| Etapa | Estado |
|---|---|
| **A** — imagen `dd` del sistema Noetic | ✅ hecha **y verificada**. La reversión existe |
| **B** — instalar 24.04, `cmdline.txt`, `config.txt`, UART, `/dev/rvr` | ✅ verificado 2026-07-30 |
| **B5** — actualizaciones cerradas y credenciales de git | ✅ 2026-07-30 |
| **C** — higiene del SO (arranque 1min39s → **8.7 s**) | ✅ verificado 2026-07-30 |
| **D** — **GO/NO-GO del SDK en Python 3.12** | ✅ 🟢 **GO** — 16.67 Hz, firmware 9.1.462 |
| **E3/E4** — verificación de UART y LIDAR | ✅ hechas ya, sobre 24.04 |

Y para no repetir la verificación a mano: **`bash scripts/verificar_robot.sh --hardware`**
hace 48 comprobaciones y sale con código ≠ 0 si algo falla. En `rvr-01`, el 2026-07-30: **48
correctas, 0 fallos**.

✅ **El `stash@{0}` ya está rescatado.** Contenía tres scripts de estudiantes que solo
existían en un stash local — y los stashes **no viajan a un remoto**, así que se habrían
perdido al reflashear. Están preservados sin modificar en la rama
**`wip/scripts-estudiantes`** (commit `62e0313`). El stash original se conserva intacto
(se usó `stash apply`, no `pop`).

⚠️ **Decisión pendiente sobre `01_avanzar.py`.** No está modificado: está **reemplazado**.
El tutorial «ULTRA SIMPLE: solo avanza el robot» ya no existe en esa rama; en su lugar hay
una clase `SeguidorBordeRojo` que sigue el borde de una línea roja con `/color` y el servicio
`/enable_color`. Parece un experimento escrito encima del fichero equivocado — es el
**primer** script que ejecutan los estudiantes y ya no hace lo que su nombre promete.
Además `origin/main` ya trae `scripts/estudiantes/seguidor_linea_pid_demo.py`, que aborda el
mismo problema.

Hay que decidir: **(a)** mover el seguidor a su propio fichero y restaurar el tutorial, o
**(b)** descartarlo por estar superado por `seguidor_linea_pid_demo.py`. Por eso la rama es
WIP y **no debe mezclarse con `main`** hasta resolverlo.

⚠️ **Antes de apagar la Pi en cualquier momento, comprueba que no queda nada sin subir.** Es
lo que hace `fase_0_3_respaldo.sh`, pero conviene saber por qué: un commit local o un stash
**no existen** para nadie más, y desaparecen con la tarjeta.

```bash
for r in ~/atriz_ws/src/Atriz_rvr ~/atriz_migracion; do
  echo "── $r"; git -C $r status -sb | head -1; git -C $r stash list
done
```

🔴 **Y comprueba que PUEDES subir.** En un sistema recién instalado no hay credenciales, así que
los commits se quedan solo en la tarjeta. Pasó el 2026-07-30 — ver `CLAUDE.md`, «Antes de subir
nada».

```bash
git -C ~/atriz_migracion push --dry-run origin HEAD && echo "OK: SÍ puedo subir"
```

⚠️ **Corregido el 2026-08-11.** Aquí ponía *«el repositorio es privado: `git fetch` falla con
`could not read Username`»* y el comando era `git fetch origin`. Desde que el repositorio es
**público**, `git fetch` va **anónimo** y ese control pasa siempre — daba una falsa confirmación
de que podías subir. Solo escribir exige autenticación, de ahí el `push --dry-run`.

### Reinstalar con ayuda de un agente

Tras grabar Ubuntu Server 24.04 y clonar este repositorio, basta con arrancar Claude Code
en `~/atriz_migracion` y decirle:

> Lee CLAUDE.md y sigue INSTALACION.md para poner el sistema a punto.

`CLAUDE.md` se carga solo y le da las reglas, las trampas conocidas y los valores de
referencia de **ambos** sistemas.

**Estado de los capítulos del manual tras la sesión del 2026-07-30:**

| Cap. | Contenido | Estado |
|---|---|---|
| 1 | Enlace UART | ✅ verificado en 20.04 **y en 24.04** |
| 3 | Flasheo de 24.04, `cmdline.txt`, `config.txt` | ✅ **verificado** — dejó de ser NO VERIFICADO |
| 4 | Higiene del SO | ✅ **verificado** — dejó de ser NO VERIFICADO |
| 5 | ROS 2 Jazzy y workspace | ✅ **verificado 2026-07-30** — 201 paquetes, `ros2 doctor` 5/5 |
| 8 | YDLIDAR X2 | ✅ hardware verificado en ambos; driver ROS pendiente |

Los capítulos 3 y 4 se recorrieron y **se corrigieron sobre la marcha**, que es lo que pedía
la nota. El 5 sigue sin ejecutarse: al recorrerlo, corregirlo en el momento y cambiar su marca
a ✅ con la fecha. **En el repositorio, no en un mensaje de chat.**

---

## Estado de los repositorios

| Repo | Rama | Commit | Contenido |
|---|---|---|---|
| `Atriz_migracion_ros2` | `main` | — | Este repositorio: auditoría, plan, manual, scripts |
| `Atriz_rvr` | `main` | `6f48ae1` | Original + **el arreglo del UART** (cherry-pick de `67c8776`) |
| `Atriz_rvr` | **`ros2`** ← rama de trabajo actual | `1b1239a` (histórico) → **`ff2ea8a`** (2026-08-03, **empujado** a `origin/ros2`) | `atriz_rvr_msgs` portado a ament+rosidl, y desde el 2026-08-02 el material docente reescrito sobre `atriz.py` — ver «Material docente», arriba |
| ~~`Atriz_rvr`~~ | ~~`migracion-ros2`~~ | `24c7749` | 🗑️ **Borrada el 2026-08-03.** Era ancestro estricto de `ros2` (73 commits detrás, 0 propios): no se perdió nada, y `24c7749` sigue alcanzable desde `origin/ros2` |
| ~~`Atriz_rvr`~~ | ~~`wip/scripts-estudiantes`~~ | `62e0313` | 🗑️ **Borrada el 2026-08-03.** Stash rescatado; su decisión pendiente la contestaron los hechos (el tutorial está restaurado y el seguidor tiene su fichero). El mecanismo que valía está conservado en `CLAUDE.md` |
| `Atriz_web_server` | `pruebas` | `924d659` | Sin tocar — se aborda al final |

✅ **Cerrado el 2026-08-04: `ros2` es la rama por defecto de `Atriz_rvr`.** Hasta entonces
`origin/HEAD` apuntaba a `main` —ROS 1, **75 commits** por detrás—, así que un `git clone` a
secas daba eso; era la misma trampa que hizo que las dos auditorías de `Atriz_web_server` se
contradijeran. Verificado **por efecto**, clonando sin `-b`: sale `ros2`, con el material
docente sobre `rclpy` dentro. `main` sigue existiendo y sigue siendo ROS 1.

📝 `migracion-ros2` se había creado **desde `origin/main`**, no desde el clon local. Importante:
ver la lección de abajo.

### ⚠️ Por qué el arreglo del UART también está en `main`

La imagen de respaldo de la Fase 0.3 se crea sobre un sistema que **ya tiene
`dtoverlay=disable-bt` aplicado**, así que en él `/dev/ttyS0` **ya no lleva el UART**.

Si se restaurara esa imagen y se trabajara desde `main` con el código original, el robot
parecería roto sin motivo aparente: el driver abriría un puerto que existe pero no está
conectado a nada. Por eso el commit del UART se llevó también a `main` (cherry-pick
`6f48ae1`).

**Regla general:** cualquier arreglo que dependa de la configuración del sistema operativo
—no solo de ROS— debe estar en `main`, porque `main` es lo que se ejecuta si algo se revierte.

### Ficheros sueltos sin versionar

`carro.py` (**0 bytes**, nada que salvar) y `prueba.py` (92 líneas) siguen sin trackear.

`prueba.py` es un tercer intento de seguidor de línea y **está roto**: define
`def _init_(self)` con **un solo guion bajo** en lugar de `__init__`, así que el constructor
nunca se ejecuta y la clase no hace nada. Además se suscribe a `/color_sensor_left` y
`/color_sensor_right`, que **no existen** — el driver publica únicamente `/color`.

Están respaldados como ficheros en `04_respaldo/sin_commitear/archivos/`. **Decisión
pendiente:** versionarlos o descartarlos. Recomendación: borrar `carro.py` y no recuperar
`prueba.py`, ya que `seguidor_linea_pid_demo.py` (en `origin/main`) resuelve lo mismo y
funciona.

---

## Cinco lecciones que ahorran horas

**1. `git fetch` antes de auditar cualquier cosa.** Se hizo una auditoría completa sobre un
clon **5 commits por detrás** al que **nunca se le había hecho `fetch`**. Tres hallazgos
resultaron falsos. Es el error más caro de la sesión.

**2. Un robot dormido parece un cable roto.** Cero bytes de respuesta, idéntico síntoma.
**Apaga y enciende el robot antes de tocar configuración.** Se perdió un buen rato
persiguiendo un problema de device-tree que no existía.

**3. Que el nodo arranque no prueba que el enlace funcione.** `rvr_fw_check_async.py` hace
`except (asyncio.TimeoutError, Exception)` y continúa en silencio. Pero el **tiempo de
construcción** sí es diagnóstico: **0 s** = el robot responde, **~10 s** = dos timeouts = no
responde.

**4. No uses `pkill -f Atriz_rvr_node`.** El patrón coincide con la propia línea de comando
del shell que lo ejecuta y **mata tu terminal**. Pasó dos veces. Usa `pgrep -f "[A]triz..."`
con el corchete, o el PID.

**5. Mide antes de atribuir.** La auditoría culpó al bucle de asyncio de la odometría a
4 Hz. Midiendo el SDK **sin ROS** salió idéntico: la causa era un solo parámetro. El arreglo
fue **una línea** en vez de una reescritura.

---

## Herramientas de diagnóstico disponibles

Todas en `00_auditoria/evidencia/mediciones_banco/`, con su README:

```bash
raw_uart.py      # ¿contesta el RVR a nivel de bytes?     <- el más útil
x2_parse.py      # ¿funciona el LIDAR? (sin driver ROS)
medir_ritmo_ros2.py  # frecuencia y jitter de /odom, /imu y /scan
#                     ⚠️ medir.py es de ROS 1 y YA NO ARRANCA
sdk_full.py 60   # ritmo del SDK con los 8 sensores
estabilidad.py   # 12 min: huecos, pérdidas, fugas de memoria
test_rvr.py      # diálogo básico con el SDK
```
Y en `scripts/`: `fase_0_1_fix_uart.sh`, `diag_uart_pins.sh`,
`fase_0_3_respaldo.sh`, `fase_1_validar_sdk_py312.py`.

---

## Decisiones ya tomadas — no volver a discutirlas

| Decisión | Dónde está razonada |
|---|---|
| Ubuntu Server 24.04 + ROS 2 Jazzy (soporte a mayo 2029) | plan, Contexto |
| Reinstalar **sobre la misma microSD**; reversión por imagen `dd` | plan, Fase 0.3 |
| **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total | `ARQUITECTURA.md`, D1 |
| La web habla por **rosbridge**, no por SSH | `ARQUITECTURA.md`, D2 |
| Los robots se despliegan desde **tags**, no ramas | `ARQUITECTURA.md`, D4 |
| **Sin cámara** en los robots | confirmado por el usuario |
| La plataforma web **al final**, cuando el robot esté funcional | decisión del usuario |

---

## Lo que sigue sin medir

- **Ancho de banda por robot con rosbridge activo.** Es el **riesgo principal del escalado**
  y la decisión de compra de red más cara. Medir con un robot en la Fase 5 y extrapolar.
- Si Nav2 cabe en el Pi 4 junto al resto (referencia: el driver solo ya usa 29.5 % de un núcleo).
- Latencia de `cmd_vel` de extremo a extremo, y el impacto de las **48** llamadas a
  `asyncio.run()` en callbacks.
- Si el driver del X2 puede fijar la velocidad de giro (afectaría a la resolución del mapa).
- Si los 16 adaptadores USB comparten el mismo `SerialNumber "0001"`.
