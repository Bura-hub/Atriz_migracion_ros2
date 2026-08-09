# Auditoría de `atriz-lab` desde el robot

> Encargo del usuario: *«revisa toda la estructura de cómo está funcionando atriz-lab… una
> auditoría desde tu punto de vista, que conoces todo el funcionamiento»*.
>
> **Lo que aporta este ángulo y no otro:** no auditar TypeScript —eso lo hace su `tsc`, su
> `eslint` y sus 578 pruebas—, sino **cruzar la aplicación contra las trampas que este proyecto
> pagó midiendo en el robot**. Son cosas que no se ven leyendo el código de la web, porque viven
> en el otro lado del cable.
>
> Fecha: **2026-08-08** · sobre `9813c9e` · clonado a un directorio temporal, **fuera del robot**,
> para que no acabe en la imagen dorada.

---

## Veredicto

**La aplicación está sana, y bastante mejor de lo que esperaba.** Las **once** trampas del robot
que podían habérsele colado están cubiertas, con prueba y con el porqué escrito al lado.

🔴 **El único hueco serio que encontré es del ROBOT, no de la web**: no le damos el dato que
necesitaría para avisar del fallo más peligroso que hemos medido. Va en el §3.

---

## 1 · Lo que crucé, y cómo salió

| # | La trampa (medida en el robot) | Resultado |
|---|---|---|
| 1 | **Publicar en `/cmd_vel`** — es la SALIDA del `collision_monitor`: funciona y salta la seguridad entera | ✅ **la rechaza con excepción**, y con dos pruebas |
| 2 | **Mandar `qos` en `subscribe`** — el primer cliente impone el QoS a todos; uno incompatible los deja MUDOS | ✅ `opSubscribe` **no acepta el parámetro en absoluto** |
| 3 | **`throttle_rate` como protección** — rosbridge hace `min()` entre clientes: gana el más rápido | ✅ **descartado a propósito**, con el razonamiento y el fuente citado |
| 4 | **Depender de `/rosapi`** — se muere solo (evidencia 87) | ✅ **cero dependencias**. Le pasa por encima |
| 5 | **Asumir el tamaño de `/scan`** — no es constante: 250·253·254·255·270 | ✅ recorre `ranges.length`, y hay prueba contra ello |
| 6 | **Copiar umbrales de silencio en ms entre topics de ritmos distintos** | ✅ constantes separadas, con prueba que impide unificarlas |
| 7 | **Sin plazo de conexión**, un socket colgado nunca llama a `onclose` | ✅ `PLAZO_CONEXION_MS`, con prueba de las **dos** paredes de plazo |
| 8 | **Confundir `result` (rosbridge) con `success` (driver)** | ✅ los distingue en el transporte |
| 9 | **Usar `/ambient_light`** — decidido que no se usa: ve los LEDs del propio robot | ✅ **prohibido en la lista blanca**, con prueba |
| 10 | **`battery.percentage` leído como 0-100** — es una fracción 0-1 | ✅ y además **usa voltios, nunca el porcentaje** |
| 11 | **`claro = 0` tratado como fallo en modo emisión** | ✅ `hayLectura = (l) => l.success`. Ya incorporaron `SENSOR_COLOR.md` |

**Y el contrato coincide con el robot exactamente**, comprobado leyendo el `robot.launch.py` con
AST y `contrato.ts` con expresión regular:

```
  TOPICS_LECTURA     robot 14 · web 14   ✅
  TOPICS_ESCRITURA   robot  3 · web  3   ✅
  SERVICIOS          robot 12 · web 12   ✅
  ACCIONES           robot  1 · web  1   ✅
  TIPOS: 17 declarados, ninguno sin tipo
```

---

## 2 · La estructura, en frío

```
  17 681 líneas de TS/TSX (sin pruebas)   ·   41 ficheros de prueba   ·   578 casos
  fichero más grande: 671 líneas (PanelLidar.tsx)
  deuda declarada (TODO/FIXME): ninguna real
```

✅ **Nada desproporcionado.** El fichero más grande son 671 líneas de un panel con canvas, que es
donde toca que haya volumen. La lógica pura vive separada en `lib/` y es lo que tiene las pruebas
— que es exactamente la forma que permite probar sin navegador y sin robot.

✅ **La postura de seguridad es honesta**, que era mi mayor sospecha. `sesion/testigo.ts` dice con
todas las letras que el testigo **protege la interfaz y no el robot**, que cualquiera del aula
puede abrir `ws://rvr-07.local:9090` desde la consola, y por qué se firma igualmente (para que el
día de la Fase B solo haya que mudar el verificador). **Un inicio de sesión que se presentara como
control de acceso sin serlo sería justo el estado engañoso que este proyecto lleva meses
quitando** — y no lo hace.

---

## 3 · 🔴 EL HUECO, Y ES DEL ROBOT

**La web no puede avisar de la edad del mapa, porque no le damos el dato.**

`EstadoNavegacion` expone del mapa **un solo booleano**:

```
  bool hay_mapa        ← «existe un fichero»
```

Y lo que medimos el 2026-08-07 (evidencias 83 y 84) es que **un mapa que no es del sitio hace que
Nav2 declare el objetivo cumplido estando a 41,3 cm**, con `SUCCEEDED`, sin una línea de error en
ningún log. **No hay ningún otro síntoma.** El propio `ARRANQUE_NAVEGACION.md` dice que *mapear es
parte de montar el aula, no una tarea de una sola vez*.

🔴 **Así que la única defensa posible contra ese fallo es que alguien mire la fecha del mapa — y
la web, que es quien tiene delante a la persona, no puede.**

### Lo que propongo, y no lo hago sin que lo decidas

Dos campos en `EstadoNavegacion`:

```
  string  mapa_nombre       # p.ej. "cuarto3.yaml" — para que se vea CUÁL, no solo que hay
  float32 mapa_edad_s       # segundos desde su mtime; -1.0 si no hay mapa
```

Con eso la pantalla de navegación puede decir *«mapa `cuarto3`, hecho hace 3 días»* y avisar a los
7, que es el mismo umbral que ya usa `verificar_robot.sh`.

⚠️ **Coste y por qué no lo hago de oficio:** tocar un `.msg` obliga a borrar `build/` e `install/`
y recompilar (~4,5 min), a reiniciar el driver, y **deja el `comprobar_contrato.mjs` del PC en rojo
hasta que alinee** — que es el flujo normal del proyecto («gana el robot»), pero es una decisión de
coordinación, no una corrección.

---

## 4 · Lo que ya les comuniqué por `ESTADO_ACTUAL.md`

- **`rosapi/get_param` sí funciona** — lleva `<nodo>:<parámetro>` con dos puntos, y el nodo es
  `/rvr_driver`. Su conclusión de que «todo tiene que venir por topic o servicio propio» era un
  rediseño apoyado en una llamada mal formada. **Retirada.**
- 🔴 **Pero esa llamada MATA `rosapi`** ~30 s después, y es el caso normal de la web porque `amcl`
  y los nodos de Nav2 solo existen con la navegación arrancada. Mitigado en el robot con `respawn`.
  **A ellos no les afecta hoy** porque no usan `rosapi` — pero que no lo usen fue suerte, no
  diseño.
- ✅ **Su hipótesis del LED era exacta**: rosbridge conserva la suscripción a `/color` cuando el
  cliente se cae, el driver la cuenta como actividad y el apagado por inactividad no vence nunca.
  **Medido, ya no es hipótesis.**

---

## 5 · Lo que NO audité, y conviene saberlo

⚠️ **No ejecuté nada de la web.** Ni `npm test`, ni `tsc`, ni el navegador. Esta auditoría es
**estática más el cruce contra el robot**; lo dinámico ya lo cubre su propia validación
(`VALIDAR_CON_EL_ROBOT.md`), que además es la que encontró sus tres fallos reales.

⚠️ **No audité el diseño visual ni la accesibilidad.** No es mi ángulo y ellos ya tienen una
guardia que abre el navegador de verdad.

⚠️ **Y no audité el rendimiento con 16 robots**, que es la pregunta grande que queda: el muro se
apoya en `presupuesto.ts` con topics baratos (`/battery_state` + `/motor_status` = 0,48 kB/s por
robot), pero **eso está calculado, no medido con 16 clientes reales**. Es del aula.
