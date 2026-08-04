# Encargo de diseño de interfaz — para pegar en Google Stitch

> 🔴🔴 **SUSTITUIDO EL 2026-08-04 POR [`DESIGN.md`](DESIGN.md). NO PEGUES ESTE EN STITCH.**
>
> `DESIGN.md` lo reemplaza entero y va más lejos en tres cosas que aquí faltaban: describe
> **cada pantalla una a una**, trae los **valores exactos** ya implementados en `globals.css`
> (con su tabla de correspondencia) y **anula explícitamente las cinco reglas por defecto** de
> la guía de estilo de Stitch que en un instrumento son dañinas — sobre todo el
> «bucle infinito en todo componente activo», que aquí fabricaría latido donde no lo hay.
>
> Este fichero se conserva **solo como registro** de por dónde pasó el diseño. Su contenido
> no es falso, es incompleto.

> **Cómo usarlo.** Pega la sección «EL ENCARGO» tal cual. Está escrito para una
> herramienta que genera pantallas a partir de una descripción, así que dice
> **qué se ve y cómo está colocado**, no cómo se implementa.
>
> 🔴 **La sección «LO QUE NO PUEDE APARECER» es la que más importa y la que una
> herramienta de diseño va a ignorar por defecto.** Un encargo genérico de
> «panel de control de robots» produce marcas verdes, indicadores inventados y
> un cartel de «Sistema operacional» — que es exactamente el modo de fallo que
> este proyecto persigue, y que la web anterior ya tenía. Si Stitch devuelve una
> pantalla bonita llena de verdes, el encargo ha fallado aunque sea preciosa.
>
> 📝 Lo que salga de Stitch sirve como **lenguaje visual**: rejilla, tipografía,
> jerarquía, espaciado, componentes. La lógica de qué se puede afirmar ya está
> resuelta en `lib/interfaz/` y no se sustituye por lo que dibuje una IA.

---

## EL ENCARGO

Diseña una aplicación web en **español** para un laboratorio universitario de
robótica. Hay **16 robots pequeños con orugas**, cada uno con un sensor LIDAR
que gira. Los alumnos están **en la misma sala que los robots**, con el robot
delante, midiendo con cinta métrica y transportador.

No es un panel de administración de servidores ni un producto de consumo: es un
**instrumento de laboratorio**. Densidad de información alta, decoración baja,
todo legible sin esfuerzo.

### Dos personas la usan, y necesitan cosas opuestas

**El alumno** mira **un solo robot**, de cerca, en un portátil. Escribe código,
lo ejecuta y observa qué hace el robot. Necesita detalle y necesita conducir.

**El profesor** mira **los 16 a la vez**, desde el otro lado del aula, a veces
proyectado. Solo necesita saber a cuál tiene que ir. Los números pequeños no le
sirven: tiene que distinguir de un vistazo, a tres metros.

### Pantallas

**1 · Portada.** Muy simple. El título del laboratorio, un acceso al muro de
flota, y una rejilla con los 16 robots numerados 01 a 16 para entrar a uno.
Debajo, un bloque de aviso —tono ámbar, no rojo— titulado «Lo que todavía no
funciona», con tres puntos en texto llano. **Ese bloque es parte del diseño, no
un pegote temporal**: la portada dice lo que la aplicación no sabe hacer.

**2 · Muro de flota.** Rejilla de 16 baldosas, 4×4. Cada baldosa: el número del
robot **muy grande** (es lo que se lee desde lejos), el voltaje de su batería, y
una franja o borde de color que indica si hay que ir a mirarlo. Tres niveles
solamente: *nada que hacer*, *mirar*, *ir*. Sin gráficas, sin porcentajes, sin
iconos decorativos. Una baldosa de la que no se sabe nada se ve **claramente
distinta** de una que está bien — gris apagada con la palabra «sin señal de
vida», nunca roja de alarma.

**3 · Espacio de trabajo de un robot.** Cabecera fija con el nombre del robot,
el estado del enlace y la batería. Debajo, pestañas: **Terminal · Telemetría ·
Conducir · LIDAR · Diagnóstico**.

- **Terminal** (la pestaña principal, la razón de ser de la app): a la izquierda
  un editor de código de unas 30 líneas; a la derecha la salida del programa,
  como una consola, **con una línea de entrada** porque los programas piden al
  alumno que mida algo y pulse Enter. Abajo, una barra con «Ejecutar», «Parar» y
  un **botón grande y rojo de parada de emergencia** siempre visible.
- **Telemetría**: fichas de dato en rejilla. Cada ficha lleva una etiqueta, un
  valor grande, y **debajo, en pequeño, cuándo se midió**. Ese «hace 12 s» va en
  todas y es tan importante como el número.
- **Conducir**: una cruceta o zona táctil para mover el robot, y el botón rojo
  de parada, grande, siempre visible sin hacer scroll.
- **LIDAR**: un lienzo cuadrado que dibuja lo que el sensor ve alrededor del
  robot: puntos sobre anillos de distancia concéntricos, con el robot dibujado
  en el centro y una marca de hacia dónde mira. Fondo neutro, puntos en un solo
  color.
- **Diagnóstico**: tabla densa de ritmos y tiempos, estilo consola. Es la
  pantalla fea a propósito.

### Aspecto

Sobrio, plano, sin sombras marcadas ni degradados. Tipografía de sistema, y
**monoespaciada para todo número medido**. Tarjetas con borde fino y esquinas
poco redondeadas. Mucho espacio en blanco entre bloques, poco dentro de ellos.

**Modo claro y oscuro, los dos de primera** — el aula tiene el proyector
encendido y las persianas bajadas.

Color usado **solo para significar**, nunca para decorar. Una paleta corta:
neutro para lo normal, ámbar para «mira esto», rojo **reservado exclusivamente**
a la parada de emergencia y a un fallo confirmado. Si en una pantalla hay más de
dos elementos de color, sobra alguno.

---

## 🔴 LO QUE NO PUEDE APARECER

Esta parte no es estilo: es el encargo. Un panel de robots «bonito» por defecto
inventa tranquilidad, y aquí **la tranquilidad inventada es el fallo**.

- ❌ **Ningún «Sistema operativo / Todo correcto / OK» global.** No existe un
  dato que respalde esa frase.
- ❌ **Ninguna marca de verificación verde**, ningún semáforo con el verde por
  defecto. El verde solo puede salir de un dato reciente y concreto.
- ❌ **Ningún porcentaje de batería.** Se muestran **voltios**. Un porcentaje
  marcaba «100 %» con la batería casi en el umbral de apagado.
- ❌ **Ningún número sin su antigüedad.** Un dato de hace 40 segundos y uno de
  hace medio segundo no se pintan igual.
- ❌ **Ningún gráfico de tendencia, medidor circular, velocímetro ni barra de
  progreso.** No hay series temporales que mostrar y sugieren precisión que no
  existe.
- ❌ **Ningún dato de ejemplo, ninguna cifra de relleno.** Si no hay valor, la
  pantalla dice «no se sabe» — y eso tiene que verse **distinto** de un cero.
- ❌ **Ninguna afirmación de que una orden se cumplió.** El robot casi nunca
  puede confirmarlo. Se dice «orden enviada».
- ❌ **Ninguna cifra de latencia o de retardo.** No está medida.
- ❌ **Ningún inicio de sesión.** Todavía no hay control de acceso, y una
  pantalla de login sugeriría que sí.

## ✅ LO QUE SÍ TIENE QUE VERSE, Y CUESTA DE DIBUJAR

- **«No se sabe» como estado de primera clase**, con su propio aspecto —ni
  bueno ni malo, apagado— y presente en muchas fichas a la vez sin que la
  pantalla parezca rota.
- **Estados ambiguos con varias causas listadas**, sin elegir una: un bloque que
  dice «puede ser A, B o C» y no aparenta ser un error.
- **La distinción entre «te he mandado la orden» y «el robot dice que la
  cumplió»**, visualmente separadas en el mismo bloque.
- **Un aviso de coste**: una de las pantallas consume mucho ancho de banda y lo
  advierte.
- **El botón de parada de emergencia**, que tiene que ser el elemento más
  llamativo de cualquier pantalla donde aparezca, sin volverla estridente.

---

## Notas para quien lea el resultado

- **La aplicación ya existe y funciona** (`atriz-lab`): rutas, componentes y
  lógica. Lo que se busca en Stitch es **lenguaje visual**, no estructura.
- Los textos que devuelva la herramienta **no se copian tal cual**: las frases
  que la interfaz puede decir están fijadas en `lib/interfaz/lenguaje.ts`, con
  una prueba que recorre los componentes y falla si aparece una prohibida.
- Si el resultado es una pantalla bonita y tranquilizadora, **descártala**. Este
  proyecto ya tuvo una: 1134 líneas que enseñaban un estado de robot inventado.
