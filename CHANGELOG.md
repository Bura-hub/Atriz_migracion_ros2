# Bitácora

Una entrada por sesión de trabajo. Formato: qué se hizo, qué se verificó, qué quedó pendiente.

---

## 2026-08-11 (PC) — El sistema de infrarrojos llega a la web, y la brújula que no se pintó

El robot rehízo el IR entero y dejó escrito en `ESTADO_ACTUAL.md` qué le tocaba al PC. Integrado en
`atriz-lab`. **El quinto control de `comprobar_contrato.mjs` —el de campos— sirvió por primera vez:**
se puso en rojo por sí solo con los dos `.msg` nuevos, que es exactamente el fallo que el 2026-08-08
dejó pasar en silencio.

Contrato después: **LEER 16 · ESCRIBIR 3 · SERVICIOS 13 · TIPOS 7/7 · CAMPOS 53 en 7 `.msg`**.

### Lo que se construyó

- **`lib/robot/infrarrojos.ts`**, que interpreta `EstadoIR` **sin inventar dirección**, con 17
  pruebas.
- **Tarjeta en «por qué no obedece»** cuando `conduciendo_por_ir` es `true` — el único campo que
  delata a un robot conducido por su firmware, que no pasa por `cmd_vel` y por tanto es invisible
  para el vigilante y para el `collision_monitor`.
- **`--conduciendo-ir`** en el doble de rosbridge, para poder pintar ese caso sin dos robots.

### 🔴 La decisión que más importa: NO se pintó una brújula de cuatro cuadrantes

El robot midió con los dos robots (evidencia 100) que los cuatro `sensor_N` **no son cuatro
direcciones**: DELANTE y DERECHA dan el mismo patrón y `sensor_0` no lleva datos nunca. Discrimina
**tres** zonas. Pintar cuatro habría mentido **con datos reales**.

La rama por descarte **no adivina** —dice «hay alguien, no sé dónde»—, que es el fallo del
clasificador de color de este mismo proyecto («si no, verde» sobre una cuenta de ruido). Y la
antigüedad decide **antes** que los sensores: por encima de 1 s la lectura está caducada y los
cuatro `255` no se leen como «no hay nadie».

La prueba que lo sostiene barre **las 64 entradas posibles**. Mutada en dos direcciones —quitar la
caducidad, hacer que la rama por descarte adivine—: **caen las dos**.

### 🔴 Dos fallos propios, los dos encontrados MIRANDO y no razonando

1. **El titular tapaba el aviso.** Con el robot conduciendo por IR y todo lo demás sano, la pantalla
   decía «Ninguna de las causas conocidas encaja» **justo encima** de la tarjeta que avisa de que el
   robot se mueve solo. Las dos frases eran ciertas por separado. **Ninguna prueba de
   `diagnosticar()` podía verlo**: se vio en el volcado de lo que el navegador acaba pintando.
   Arreglado sin marcar la causa como confirmada —eso afirmaría una causalidad no medida—, sino
   dejando de decir «ninguna» cuando hay algo.
2. **Comprobé el código fuente en vez de la pantalla.** La prueba de navegador buscaba `puede ser` y
   la etiqueta se ve en MAYÚSCULAS. Falló, y falló bien: es justo lo que esas pruebas existen para
   no dejar pasar.

### 📝 Y uno de operación, que costó que la web no cargara

El servidor de desarrollo se lanzó como `npm run dev | head -40`. Al llegar a la línea 40 `head`
termina, se cierra la tubería y el servidor se queda escribiendo contra un extremo muerto: **el
puerto sigue en LISTENING y no sirve ni la raíz**. Lo vio el usuario antes que yo. Es la misma
familia de todo este proyecto — una comprobación de existencia que no prueba el efecto.

### ⏳ Lo que queda, y es una sola cosa para el robot

**Medir el caudal de `/estado_ir` en kB/s.** No está en el muro de la flota porque
`presupuesto.ts` **lanza** ante un topic sin caudal medido, a propósito. Con ese número entra en
`CAUDAL_KBS` y se puede decidir; sin él se queda fuera. Sí está en la pantalla por robot, que es
donde hace falta.

⏳ **Nada de esto ha visto un `/estado_ir` de verdad.** La casilla está en
`atriz-lab/VALIDAR_CON_EL_ROBOT.md` §2ter y **exige dos robots**: es la primera pantalla que no se
puede validar con uno.

---

## 2026-08-11 (Pi) — La tarjeta de rvr-02 se formatea, y al ir a grabarla aparece un agujero de cuatro documentos

Se reinicia el despliegue de rvr-02 desde una microSD en blanco, para documentar el proceso entero
en vez de arrastrar el estado a medias del 2026-08-10.

**Lo encontró el usuario, no el repositorio:** al ir a grabar preguntó por qué no se decía si el
SSH del Imager va por contraseña o por clave pública. **No se decía en ninguno de los cuatro sitios
donde se describe el Imager** — `FLOTA.md`, `MANUAL_ATRIZ_ROS2.md` §3.2, `INSTALACION.md` B1 y
`PLAN_MIGRACION_ROS2.md` ponían «activar SSH» y nada más.

Importa porque el Pi va headless y `preparar_tarjeta.sh` le quita la consola serie: con «sólo clave
pública» y una clave que no sea la del PC de acceso, el robot arranca **inaccesible** y hay que
regrabar la tarjeta.

**Medido en rvr-01** (no deducido): `PasswordAuthentication` comentado —o sea `yes` por defecto— y
`~/.ssh/authorized_keys` de **0 bytes**. A rvr-01 sólo se entra por contraseña. Ese es el criterio
para los 16.

### Qué se cambió

- Los cuatro documentos, con el porqué y no sólo la instrucción.
- **`preparar_tarjeta.sh`: paso 4/5 nuevo.** Lee `ssh_pwauth` de `user-data` con la tarjeta aún en
  el PC y **aborta con salida 1** si está en `false` — que es cuando arreglarlo todavía es gratis.
  Pasa de «hace tres cosas» a cuatro. Probado en seco contra cinco particiones falsas, verificando
  el resultado: el caso `false` **para de verdad** (salida 1, el paso 5/5 no llega a imprimirse), y
  un señuelo `password:` sembrado en las cinco **no aparece en la salida** — `user-data` lleva el
  hash de la contraseña y la PSK, así que se comprueba la presencia de claves y no se imprime.
- **`verificar_robot.sh`:** comprueba el `PasswordAuthentication` efectivo y **falla** si está en
  `no`.

### 🆕 El sistema de infrarrojos, rehecho entero

👤 «haz el rediseño completo ahora», después de probar el IR con dos robots por primera vez —
hasta el 2026-08-10 solo había uno y esto no se podía ni intentar.

**Lo que la prueba destapó, y por qué el rediseño no era pulir sino corregir una premisa:**

- El firmware **sí** entrega la notificación IR. Payload real: `{'infrared_code': 3}`, **una sola
  clave**. Los cuatro `*_strength` de `InfraredMessage.msg` **eran ficción** — son parámetros del
  envío, no llegan nunca en la recepción.
- **El IR de ROS 1 nunca recibió un solo mensaje.** Su handler leía
  `datos['InfraredMessage']['Code']`: `KeyError` en la primera línea. Y su `/ir_messages` se
  anunciaba y **nunca se publicaba**. Así que *«ROS 1 publicaba los dos topics con los mismos
  datos»*, que está en el driver y en este mismo fichero, **es falso**.
- Su `evading` llamaba a `infrared_control.start_infrared_evading()`, **un método que no existe**.
- Y ROS 2 había **perdido** la validación de rangos que ROS 1 sí tenía.

**Diseño** (`docs/superpowers/specs/2026-08-11-sistema-ir-robot-a-robot-design.md`): evento y
estado separados, como ya hace `/estado_robot`. `/infrared_messages` para el evento, `/estado_ir`
a 1 Hz para el estado.

🔴 **Lo que más valor tiene: `conduciendo_por_ir`.** `get_active_control_system_id()` devuelve 8
mientras el firmware conduce el robot por IR — y hasta ahora, con `following` activo, **nada en ROS
sabía que el robot se estaba moviendo**: no pasa por `cmd_vel`, así que ni el watchdog ni el
`collision_monitor` lo ven.

🔴 **Y la garantía nº 8 de la biblioteca del alumno:** `secuencia_de_cierre` pasa de tres pasos a
cuatro, y `apagar_ir` va **el primero**. Parar antes dejaría al robot arrancando otra vez en la
siguiente detección — el mismo fallo que ya mordió a la parada de emergencia. Sin eso, **un Ctrl-C
deja un robot conduciendo por el aula**. 77 tests en verde, tres nuevos que provocan el fallo.

### ✅ Y la prueba de viabilidad, ejecutada: **la máscara del BOLT no describe al RVR**

Medido con los **dos robots**, cada uno haciendo de vigilante por turnos, girándolos 360°:

| dónde está el emisor | rvr-01 | rvr-02 |
|---|---|---|
| **delante** | `[2,3]` | `[2,3]` |
| **a la izquierda** | `[1]` | `[1]` |
| **detrás** | `[1,3]` | `[1,2,3]` |
| **a la derecha** | `[2,3]` | `[2,3]` |
| | 🔴 `sensor_0`: **nunca** | 🔴 `sensor_0`: **nunca** |

✅ **Reproducible entre robots**, y el ciclo cierra al girar 360°: hay direccionalidad real, atada
al cuerpo del robot. 🟡 **Pero son tres estados, no cuatro** — delante y derecha dan exactamente lo
mismo. Y `sensor_0` no lleva datos jamás, lo que **retira una hipótesis que llegué a proponer**: que
rvr-01 tuviera un sensor averiado. Con rvr-02 igual, es sistemático.

**Se aplica el criterio tal como estaba escrito antes de medir**, en vez de estirarlo: los campos
**no se renombran**, `quien_hay_cerca()` se queda **sin prometer las cuatro direcciones**, y el
campo `crudo` se queda para poder reinterpretar la medición si algún día aparece documentación real
del RVR. Evidencia 100.

📌 Si hubiéramos creído a la máscara, `atriz.py` estaría prometiendo hoy «tienes un robot a tu
izquierda-delantera» sobre unos bytes que no distinguen delante de derecha y uno que no existe. En
dieciséis robots. **El coste de comprobarlo fue una tarde con dos robots.**

📌 **Y una corrección que salió del usuario:** «el robot no es BOLT, es Sphero RVR». La máscara que
asignaría cada sensor a una esquina está documentada **para el BOLT**. Por eso los campos se llaman
`sensor_0..3` y por eso `EstadoIR` lleva el `uint32` **crudo**: si parto mal los bytes, la
evidencia sobrevive. ⏳ La prueba de viabilidad que los bautiza está escrita y es **física**.

### ✅ rvr-02 PASA el verificador: 151 ✓ · 6 avisos · 0 fallos

El primer pase dio 4 fallos y **los cuatro eran el mismo hueco**: ningún guion del proyecto metía
al usuario en `dialout` ni en `video`. rvr-01 los tiene de su montaje **manual** original.

**No se habría visto nunca.** La imagen dorada clona `/etc/group`, así que los robots 3-16 los
heredarían de rvr-01 y todo parecería bien — *«la imagen es el ATAJO, el script es la VERDAD»*.
Divergían, y sólo una instalación limpia podía enseñarlo.

Y no saltó antes porque `atriz-robot.service` lleva `SupplementaryGroups=dialout`: **el servicio**
habla con el RVR aunque el usuario no esté en el grupo. De ahí que el verificador diera
`✓ /odom a 15.32 Hz` dos secciones antes de decir «el RVR NO contesta». Lo que se rompe es todo lo
interactivo, y eso incluye **`atriz.py`, el producto que ejecuta el alumno**.

⚠️ **Una hipótesis mía retirada:** del cuarto fallo (`get_encoders` no responde) dije que
«probablemente el intento fallido de hablar con el RVR dejó el enlace ocupado», y lo marqué **sin
diagnosticar** en vez de darlo por explicado. Menos mal: era falso. El verificador hace esa llamada
abriendo `/dev/rvr`, y sin `dialout` no podía.

**Dos fallos del propio verificador, los dos míos y del mismo día:** un `grep -c … || echo 0` que
con el fichero vacío producía `0\n0` y reventaba con `[[: syntax error`; y un aviso que pedía el
`radius` **0.18** —el valor antiguo— contradiciendo a la comprobación del nodo vivo, que exige
0.15. Segunda vez en el día con ese patrón: por la mañana fue `authorized_keys`.

**Y un pendiente que ya estaba resuelto y nadie había tachado:** `red.txt` en 755 / la PSK legible
figuraba abierto en `PRUEBA_ACEPTACION.md` (×2) y `ESTADO_ACTUAL.md`. Medido: **los dos robots**
tienen `fmask=0177,dmask=0077` en el `fstab` y `/boot/firmware` en `drwx------`.

⚠️ **Y una corrección mía, del mismo día:** marqué como riesgo abierto las credenciales del
historial de los repositorios públicos. **Se rotaron el 2026-08-04** — están muertas, y así estaba
escrito en `ESTADO_ACTUAL.md`. Sacarlas del historial es higiene, no urgencia. La lección: antes de
marcar algo como riesgo abierto, mirar si el repositorio ya registra que se cerró.

### 🔴🔴 Y lo grande: **`provision.sh` se ha ejecutado ENTERO por primera vez**

Era, textualmente, «la suposición más peligrosa que le queda al proyecto»: el guion del que sale
la imagen dorada de los 16 robots solo se había probado con `--simular`, que convierte en
no-operación justo lo que instala. **96 ✓ · 16 avisos · 0 fallos**, sobre un 24.04 limpio.

**No a la primera.** La primera pasada tiró los dos últimos pasos, y con **el mismo fallo del
2026-08-10** — o sea reproducible, que es exactamente para lo que servía tener un segundo robot.

La causa, escondida a plena vista en `provision.sh:244`:

```
drwxr-xr-x root:root  ~/atriz_ws        ← el padre
drwxr-xr-x sphero     ~/atriz_ws/src    ← el hijo
```

`install -d -o sphero -g sphero .../atriz_ws/src` **no aplica `-o`/`-g` a los padres que crea de
paso**. El manual de coreutils: *«Parent directories are created with mode `u=rwx,go=rx` (755),
regardless of the `-m` option»… «giving them the default attributes»*. Con `sudo`, «por defecto»
es root. Después `colcon build` corre como el usuario y muere con `Permission denied: 'log'`, y de
rebote `fase_7` se niega porque el workspace no compiló. **Dos de los nueve pasos caídos por el
dueño de un directorio.**

Cuatro arreglos, todos en el guion y ninguno a mano: nombrar los dos directorios; reparar lo ya
creado con `chown -R` (sin eso, «idempotente» no serviría, porque la primera víctima es un robot
que ya existe); dejar de mandar la salida de `colcon build` a `/dev/null` —el único paso que falló
había borrado su propia evidencia, 9.075 líneas para decir «✗ colcon build falló»—; y que
**`verificar_robot.sh` vigile el dueño del workspace, que no vigilaba nadie**.

🔴 **Una conclusión anterior retirada, y es la que costó el día:** el 2026-08-10 quedó escrito
«✅ Descartado que lo cause el guion — crea el workspace con el dueño correcto». Era exactamente al
revés. Se descartó **leyendo el código**, que dice `install -d -o "$USUARIO"` y suena bien, en vez
de mirar el directorio, que decía `root`. Aplicada a un guion, la regla *«comprueba el efecto, no
el código de salida»* significa que **mirar el fuente es mirar el código de salida**.

✅ **Y de propina se cierra el ⏳ del `ID_PATH` del LIDAR**, abierto desde el 2026-08-04 y la última
incógnita grande antes de la imagen dorada: el puerto USB da el **mismo `ID_PATH` en otro Pi**.
`provision.sh` lo comprobó solo (`✓ /dev/ydlidar existe: la regla CASA en este robot`), y el robot
tiene `/dev/ydlidar → ttyUSB0` y `/dev/rvr → ttyAMA0`. La regla udev es clonable tal cual.

Actualizadas **todas** las menciones al estado de `provision.sh`, no la primera: `README.md` (×2),
`scripts/README.md`, `CLAUDE.md`, `TRASPASO.md` (×2), `INSTALACION.md` y `FLOTA.md` (×2 para el
`ID_PATH`).

### Tarde: rvr-02 desde la tarjeta en blanco, y lo que arrastró el repositorio público

Paso a paso completo en `00_auditoria/evidencia/98_rvr02_de_la_tarjeta_en_blanco.txt`.

**`preparar_tarjeta.sh` deja de estar 🟡 «probado en seco»** —lo estaba desde el 2026-07-30— y pasa
a ✅ verificado sobre hardware real. Lo que lo cierra no es la salida del guion, sino lo que dijo
el robot ya arrancado: `soc/serial@7e215040/status → disabled` y `aliases/serial0 → PL011`. El
`console=serial` quitado y el `dtoverlay=disable-bt` bajo `[all]` **surtieron efecto en la placa**,
que es la única prueba posible de que la trampa de la cabecera `[all]` se esquivó. Actualizadas las
tres menciones del estado, no solo la del guion.

**Y un fallo del guion que salió en la primera pasada en seco:** imprimía `✓ quitado
console=serial*` y dos líneas más abajo enseñaba el fichero con `console=serial0,115200` todavía
puesto. En `--simular` se salta la escritura (correcto) pero el ✓ se imprimía igual y en pasado, y
el `contenido:` hacía `cat` del fichero sin tocar. El único modo cuyo propósito es ver el efecto por
adelantado afirmaba lo que no había hecho. Arreglado con prefijos `SE HARÍA →` / `HECHO →` y con dos
controles del efecto que no existían.

**Windows/WSL**, que `FLOTA.md` no contemplaba: Docker Desktop secuestra `wsl` (su distro es la
predeterminada, se reconoce por `/mnt/host/c/` y `sudo: not found`), y `wsl --install -d Ubuntu`
falla con `ERROR_ALREADY_EXISTS` si Ubuntu ya está aunque figure `Stopped`.

**Los repositorios son públicos** —👤 decisión del usuario, para no repartir un PAT en 16 microSD—
y eso arrastra tres cosas:

- ✅ **Decae el bloqueante nº 1 de la Fase 6**: `~/.git-credentials` ya no tiene que viajar en la
  imagen dorada. Retirado del paso 5 de `FLOTA.md`, que lo pedía explícitamente.
- 🔴 **El control de «comprueba que PUEDES subir» dejó de servir.** Era `git fetch origin && echo
  "OK: hay credenciales"`, en `CLAUDE.md`, `TRASPASO.md` e `INSTALACION.md`. Con el repositorio
  público, `fetch` va anónimo y **pasa siempre**. Sustituido por `git push --dry-run origin HEAD`,
  porque escribir sí exige autenticación. Clonar no necesita PAT; subir, sí.
- 🔴 **`MANUAL_SPHERO_original.docx` sigue versionado con la contraseña en texto plano**, y se
  conservaba justificándolo con «por eso este repositorio es privado» —frase que estaba en
  `README.md` y `CLAUDE.md`, y que ya es falsa—. Corregidas las dos; el fichero sigue ahí,
  👤 decisión del usuario. Esa contraseña ya se daba por comprometida (`Atriz_web_server`, público),
  así que es una fuente más, no una fuga nueva.

### Y un duplicado que casi se cuela

La primera versión añadía **una segunda** comprobación de `authorized_keys` en `verificar_robot.sh`
**con la polaridad contraria** a la que ya existía desde el 2026-08-03: la vieja marca «vacío» como
aviso (un canal automático se cuelga esperando la contraseña), la nueva lo marcaba como ✓. Se vio
al ejecutar el verificador y ver salir las dos líneas. Las dos afirmaciones son ciertas —son dos
consecuencias del mismo hecho—, así que se fundieron en una sola comprobación que dice ambas, en
lugar de dejar dos que se contradicen. 📌 *Otra vez la regla de «busca TODAS las menciones, no la
primera», y esta vez me la salté yo.*

📌 Para la imagen dorada: las claves **de host** se regeneran en el primer arranque; `authorized_keys`
**no**, se clona. Una clave en el robot de referencia abriría los 16.

---

## 2026-08-10 (PC) — **Hay un segundo robot, y con él caen dos suposiciones grandes**

Sesión de traspaso. Las dos cosas las trae el usuario, y las dos levantan bloqueos que llevaban
semanas escritos como «no se puede saber desde aquí».

### 1 · `provision.sh` se está ejecutando de verdad, por primera vez

Desde el 2026-07-31 el proyecto asumía que el guion funciona, porque probarlo exigía reflashear
rvr-01 —«el único robot montado»—. Con el riesgo escrito al lado: *«no es que falle: es que falle
en el robot 7 de 16, con seis ya desplegados»*.

**Ya hay un `rvr-02` y el guion corre sobre él.** Y está encontrando cosas, que es para lo que
servía. Parado aquí:

```
colcon build                      Permission denied: 'log'
fase_7_systemd.sh --id 02         ✗ el workspace está compilado
                                  ✗ existe robot.launch.py instalado
                                  ✗ 2 comprobaciones fallaron. No se instala nada.
```

Es **un solo problema en cadena**: `fase_7` se niega porque el workspace no compiló.

✅ **Descartado leyendo el guion, para que nadie lo persiga:** no lo causa `provision.sh`. Compila
con `sudo -u "$USUARIO"` (`:519`) y crea el workspace con `install -d -o "$USUARIO"` (`:244`), así
que un `~/atriz_ws` de `root` vendría de algo lanzado a mano con `sudo`.
⏳ **La causa real NO está determinada.** Falta el diagnóstico desde el robot.

🔴 **Y la trampa que hay que descartar antes de tocar nada: el workspace parásito.** Este proyecto
se equivocó **seis veces en una sesión** con esto — `colcon` lanzado desde `src/Atriz_rvr` crea ahí
su `build/`, `install/` y `log/`, compila contra ellos y dice «Finished» con el cambio sin llegar
al sistema. Encaja con un `log/` que no se puede escribir. Por eso el arreglo pasa por
`scripts/compilar.sh`, que **avisa del parásito**, y no por `colcon build` a pelo.

📌 **La regla que hace que esto valga la pena, y va escrita en los tres sitios: lo que frene a
rvr-02 va AL GUION, no se arregla a mano.** Si se queda en una sesión de SSH, los catorce
siguientes tropiezan igual.

### 2 · El aula: el aislamiento de clientes queda DESCARTADO

👤 El usuario entró por `ssh sphero@rvr-02.local` **desde el laboratorio**, y funcionó.

- **El AP no aísla.** El aislamiento de clientes actúa en **capa 2**: bloquea todo el tráfico entre
  dispositivos inalámbricos, sea el puerto que sea. Si el SSH llegó, no hay aislamiento.
- **mDNS funciona ahí.** El nombre `.local` resolvió, así que no capa multicast.

Esas dos eran las que podían **tirar el diseño del transporte**, y salen a favor.

🔴 **Lo que no cierra:** que SSH llegue no prueba que el navegador llegue — en este proyecto
`ping` y `Resolve-DnsName` dieron verde con el navegador colgado 12 s. Esa causa se arregló el
2026-08-04, así que el riesgo es bajo, pero SSH prueba SSH.
⏳ Sigue sin saberse **qué IP coge el robot en ese SSID**: `05-atriz-lab.network` nunca ha casado
con nada.

📝 **Y corrijo mi propia insistencia:** llevaba varias respuestas diciendo que los diez minutos en
el aula eran «lo que decide si construir o rediseñar». **Con este dato ya está decidido, y a
favor.** Baja a confirmación de 30 s. Lo que sube al primer puesto es el **agente de sesión**, que
yo mismo había aparcado *hasta saber esto*.

### Alineado

`ESTADO_ACTUAL.md` (el canal, con el diagnóstico accionable arriba del todo), `CLAUDE.md`,
`TRASPASO.md` y `FLOTA.md` — las cuatro afirmaciones de «rvr-01 es el único robot montado» que
sostenían la decisión de no probar el guion.

---

## 2026-08-09 (PC) — **«No se puede verificar» también es una afirmación, y la mía era falsa**

Salió de una pregunta del usuario: *«¿qué falta aquí por probar?»*. Al ir a contestarla con la
lista en la mano en vez de de memoria, la lista se cayó.

Yo había escrito ese mismo día —en el CHANGELOG, en el README y en el canal del robot— que las
tarjetas de `APROXIMACION` y del mapa **no se podían verificar aquí**: *«son de cliente, no están
en el HTML del servidor, y ninguna prueba las mira»*.

🔴 **Lo segundo era cierto. Lo primero, falso.** `pantallas_reales.test.ts` no hace `fetch`: trae
un **cliente CDP completo, sin dependencias**, que arranca Chromium headless y lee el DOM ya
hidratado. Estaba a un fichero de distancia y **lo había ejecutado esa misma noche** sin reparar
en lo que permitía.

📝 **La lección, que es la de este proyecto con otra cara:** *«no se puede medir» necesita la misma
comprobación que «se puede». La mía se apoyaba en no haber mirado* — la versión de esta sesión del
error del `grep` que no podía casar lo que buscaba.

### Lo hecho

- **`navegador_cdp.ts`**, extraído de la prueba donde vivía privado. `pantallas_reales.test.ts`
  ahora lo importa: sigue dando **42 en verde**, así que la extracción no cambió nada.
- **`tarjetas_vivas.test.ts`**, nueva: levanta el doble **ella misma** —uno por caso, porque las
  banderas se leen al arrancar— y comprueba lo que el navegador **acaba pintando**. **5 de 5**, y
  **sin robot**.
- **`rosbridge_de_mentira.mjs --aproximacion`** y su control `--moviendose`, añadidos para esto.

📌 **El control es lo que la hace una prueba y no una foto:** mismo `action_type` en los dos casos,
`/odom` distinto, y el mensaje **tiene que cambiar**. Si no cambiara, la pantalla estaría
*afirmando* un congelamiento que no ha visto — el error simétrico del que se corrigió.

### 🔴 Y dos errores más, los dos míos, que la propia prueba destapó

**1 · Mi instrucción de validación no hablaba con el doble.** El documento decía «abre
`/robot/1/conducir`», y ese segmento hace que la app conecte a **`rvr-01.local`**. Con el robot
apagado la página sale vacía y **las comprobaciones de ausencia pasan todas** — que es exactamente
el fallo que `pantallas_reales.test.ts` ya tenía documentado («18 de 19 pasaron sobre seis páginas
404») y que volví a cometer. Lo correcto es `/robot/127.0.0.1/...`, que la ruta acepta como IPv4
literal.

**2 · Dos falsos positivos en mi propia prueba**, la tercera vez que un detector mío acusa a código
sano por mirar de más:

```
«la tarjeta no dice 40 %»   -> sobre la PAGINA entera, cazaba el bloque permanente
                               que explica el 40 % de `Precaucion`, y es correcto
«no digas mapa viejo»       -> cazaba «copiar un mapa viejo lo rejuvenece», que
                               OTRA prueba del mismo fichero EXIGE
```

→ **Se busca el veredicto, no la palabra; y se mira la tarjeta, no lo que hay alrededor.** El
informe del navegador devuelve ahora los `[role="status"]` por separado para poder hacerlo.

**Verificación:** 615 en la suite normal · 42 + 5 con navegador, **sin robot** · `tsc` y `eslint`
limpios · contrato `LEER 14 · ESCRIBIR 3 · SERVICIOS 12 · TIPOS 5/5 · CAMPOS 36`.

**Lo que queda sin poder probarse aquí, y ahora son sólo 4 pruebas:** barrido real, dos de
acciones y la parada de emergencia en marcha. Todas necesitan el robot. Y que la tarjeta roja *se
vea* como urgente sigue exigiendo una persona: esto lee texto, no diseño.

---

## 2026-08-09 (PC, madrugada) — **El robot revisó mi código y corrigió un texto que él me dictó**

Sesión corta de integración. El robot clonó `atriz-lab` para revisar `37aa119`, dio tres cosas
por buenas y **encontró una mala, que era suya**: en `PanelNavegar.tsx` yo había escrito «por
debajo de ~50 cm Nav2 no se cuela, los **RODEA**», con el engorde del mapa como mecanismo — tal
como me lo había pasado unas horas antes.

**Era falso en dos sentidos** (evidencia 97): el rodeo no lo causaba el ancho del hueco sino **un
mapa de SLAM construido con 160 cm de recorrido** —4 nodos, 49 celdas—, y por debajo del umbral
**no rodea: no hay ruta** y el planificador se niega.

```
hueco       ¿hay ruta?    ¿cruza?
< ~45 cm     NO           no cruza: el planificador se niega
~47-55       a ratos      cruza, pero hasta 5x de desvio y 2,7x de tiempo
> 55 cm      siempre      cruza limpio en ~8 s
```

📌 **Y la corrección mejora el texto en algo que yo no habría visto solo:** distinguir «no hay
ruta» de «rodea» no es un matiz, son **dos desenlaces que se explican distinto** a quien mira. Yo
tenía los dos en una frase.

**Lo corrigió él en mi repositorio** (`atriz-lab@ac3c3ae`) avisando de que **no podía pasar las
pruebas** —no hay `node` ni `npm` en la Pi— y pidiendo que lo verificara aquí. Hecho: `tsc` y
`eslint` limpios, **615 pruebas**, las doce rutas a 200.

### Y lo aprovechable de su mensaje, que era el punto 2

*«Si la web ofrece navegar justo después de mapear, el robot estará navegando sobre un mapa casi
vacío.»* **Ese caso lo crea el propio panel**: arrancar SLAM, pararlo y pasar a Navegar.

La tarjeta del mapa ya avisaba de que una fecha **vieja** puede mentir (el `mtime` rejuvenece un
mapa copiado). Ahora avisa del **otro extremo, que es peor** porque «guardado hace 2 minutos» se
lee como buena noticia:

```
160 cm de recorrido  ->   4 nodos ·  49 celdas · 89,3 % desconocido -> Nav2 sin ruta por 47 cm
781 cm de recorrido  ->  17 nodos · 506 celdas · 47,4 %             -> el MISMO hueco, plan recto
```

🔴 **Sigue sin haber semáforo, y ahora por los DOS extremos.** No es prudencia: es que la web **no
puede medirlo** — `EstadoNavegacion` trae nombre y edad, y ni nodos ni cobertura viajan. Y un
umbral de «demasiado nuevo» sería falso: un mapa de 8 m puede tener dos minutos y estar perfecto.
**Antes de poner un umbral, pregunta si la magnitud que mides es la que falla** — aquí no lo es en
ninguna de las dos direcciones, y una segunda prueba lo impide por abajo como la primera lo impedía
por arriba.

📌 Y queda anotada **cuál sería la palanca** si algún día se quiere que la web avise sola: un campo
con los **metros recorridos** o el **número de nodos** del mapa. No se pide — la pantalla enseña el
dato y pregunta, que es lo acordado dos veces.

**Verificación:** 615 pruebas (eran 614) · `tsc` y `eslint` limpios · contrato `LEER 14 ·
ESCRIBIR 3 · SERVICIOS 12 · TIPOS 5/5 · CAMPOS 36` · doce rutas a 200.

**NO VERIFICADO, y por eso está escrito:** la tarjeta del mapa y la de `APROXIMACION` son de
cliente, así que no están en el HTML del servidor y **ninguna prueba las mira**. Se pueden ver hoy
y **sin robot** con `rosbridge_de_mentira.mjs`; el procedimiento queda en
`VALIDAR_CON_EL_ROBOT.md` §2bis.

---

## 2026-08-09 (robot, cierre) — **Respuesta al PC, y una corrección que me hicieron**

El PC respondió al bloque urgente de la inmovilización, y su respuesta traía algo que no esperaba:
**la web no es que no lo dijera — decía lo contrario en las tres pantallas donde importa.** La peor,
`no_obedece.ts`, que es literalmente la pantalla que abre alguien cuyo robot no obedece: contestaba
«el robot SÍ obedece» sobre un robot que daba 0,0 cm en las tres direcciones, y lo mandaba a repetir
la orden y a probar marcha atrás — **las dos cosas que estaban medidas como inútiles**.

🔴 **Y me corrigieron a mí, con razón:** mi lista para el PC seguía pidiendo `mapa_nombre` y
`mapa_edad_s` en `contrato.ts` **cuando estaban hechos desde el 2026-08-08**. *«Es tu fichero el que
se quedó atrás, no mi contrato.»* Es exactamente el fallo que este canal existe para evitar, y lo
cometí **en el canal**. Retirado.

✅ **Contestada su validación `VALIDAR_CON_EL_ROBOT.md` §2bis**, que pedía comprobar el bloqueo «en
las dos direcciones, incluido el error simétrico». **Ya estaba medido** con las 24 estaciones:

```
BLOQUEADO   <= 17,8 cm desde base_footprint · las tres órdenes a 0,0 · APROXIMACION
SE MUEVE    >= 19,6 cm · gira 34,9° · avanza 6,0 cm · FRENADO
error simétrico: con radius 0.15, a 15,8 cm el robot SÍ se mueve y el monitor dice FRENADO
```

⚠️ Lo que no puedo validar es que **su pantalla** lo renderice así: el 2bis completo sigue
necesitando abrir la web con el robot delante.

🔴 **Y les avisé de algo mío que quedó obsoleto en su web:** habían adaptado «el rodeo por huecos de
<~50 cm» con el mecanismo que yo les di, y **ese mecanismo era incorrecto** — lo corregí unas horas
después (evidencia 97). No es el ancho del hueco: era un mapa de SLAM de 160 cm. Lo que sí aguanta
son los **tres regímenes**, con el del medio —pasa pero tarda el triple— que **no hay que pintar
como fallo**.

📌 Lo del 1,68 m de AMCL al añadir una silla a un cuarto ya mapeado **sigue medido y en pie**.

## 2026-08-09 (robot, noche 5) — **La curva del paso, y una fórmula mía que cayó**

Cerrada la casilla que quedaba abierta desde la evidencia 91 —**AMCL sobre un mapa que SÍ contiene
los objetos**— y de paso medida la curva entera del paso con **cinco anchos**.

**La casilla:** con un mapa nuevo hecho conduciendo 781 cm y con la puerta puesta, AMCL da plan
**RECTO al 102 %**, igual que sin objetos. **Lo que hacía rodear a Nav2 no era el mapa, ni SLAM
contra AMCL: era un mapa de cuatro nodos.**

**La curva**, con el robot cruzando de verdad y no sólo consultando:

```
hueco     celdas en la pinza      consultas    travesía real
38,6 cm   0 · cerrada 37/37        0 de 6      — (no hay paso)
38,9 cm   —                        0 de 8      —
41,1 cm   —                        0 de 8      —
47,1 cm   1 · cerrada 19/49        3 de 8      3 de 3, DEGRADADA
61,1 cm   2-3 · cerrada 0/50       8 de 8      1 de 1, limpia en 7,8 s
```

**Tres regímenes: `< ~45` no pasa · `~47-55` pasa y cuesta —hasta 5× de desvío lateral y 2,7× de
tiempo— · `> 55` estable.** Justifica los **60 cm** del guion de aceptación, que hasta hoy eran un
número empírico sin mecanismo detrás.

🔴 **Y dos correcciones a conclusiones propias del mismo día:**

1. **«El robot no había pasado ni una vez: todo eran planes.»** Lo vio el usuario. Ocho consultas,
   dos anchos y una regla general, y **cero travesías**. `compute_path_to_pose` devuelve una
   promesa. Al medir travesías reales resultó que **la tasa de consulta no predice fallo, predice
   coste**: con 3 de 8 planes el robot cruzó **3 de 3**, porque Nav2 replanifica hasta 35 veces por
   trayecto y le basta con que el hueco esté abierto en algún instante.
2. **Cayó la fórmula.** Se escribió que la primera celda aparece en `2 × (14,5 + 5) = 39 cm`, y con
   38,6 cerrado el ajuste parecía perfecto — llegué a llamarlo «casi incómodo de lo bueno».
   **Casualidad**: a 38,9 y a 41,1 sigue cerrado. **Un punto que casa no valida un modelo.**
   ⏳ Si el umbral depende de la **alineación de la rejilla** —y entonces dependería de dónde está
   la puerta y no sólo de su ancho— o de un radio efectivo mayor: **NO VERIFICADO**.

Evidencia 97.

## 2026-08-09 (robot, noche 4) — **El mapa de SLAM no estaba congelado: era submuestreo**

Retractación, y de las que duelen porque **el falso defecto ya había llegado al canal del PC**
presentado como el bloqueo principal de la Fase 6.

Se había escrito que «el mapa de slam_toolbox está congelado y casi vacío: 49 celdas ocupadas para
un cuarto entero, idéntico tras 360° de giro y 160 cm de recorrido». **Falso.** Conduciendo de
verdad, con el cuarto despejado y muestreando **grafo y rejilla a la vez** contra la distancia:

```
recorrido    nodos   ocupadas   libres   desconocido
     0 cm        4         54      549       89,3 %
   276 cm       10        406     2822       45,9 %
   650 cm       17        506     2949       42,9 %
  1346 cm       30        606     3029       41,4 %      20 hashes distintos de 23
```

**Crece monótonamente:** ×11 en ocupadas, ×5,5 en libres, el desconocido de 89 a 41 %. Y la forma de
la curva es la de un SLAM sano — casi todo el relleno en los primeros ~3 m, luego se aplana según el
robot repasa terreno visto.

**Por qué el anterior era pobre, y era lo correcto:** `minimum_travel_distance: 0.3` → 160 cm son
4 nodos, y el grafo tenía exactamente 4. Con `min_pass_through: 2`, una celda cruzada por un solo
rayo se descarta. **Un mapa 91,8 % vacío es la salida correcta de ese recorrido.**

🔴 **El error de método, que es lo que hay que no repetir: se midió un sistema que ACUMULA con una
muestra que no acumulaba.** Un giro de 360° no aporta nada con un LIDAR de 360°, y un vaivén vuelve
al mismo sitio. **Hacía falta la CURVA, no otro punto.** Y el precedente estaba delante desde el
principio: **`cuarto3` existe y es un mapa de verdad.**

⚠️ **El coste no fue la conclusión, fue el canal.** Llegó a `ESTADO_ACTUAL.md` como bloqueo de la
Fase 6. Un falso bloqueo en el canal del otro equipo es peor que no escribir nada. Corregido ahí
primero.

✅ **Lo que desbloquea:** la Fase 6 no está parada por esto, y se puede construir por fin el mapa
**con los objetos dentro** que hacía falta para la casilla pendiente de la evidencia 91.

📌 **Regla operativa con número:** un mapa utilizable necesita **varios metros** de recorrido, no
unos centímetros. Con ~3 m el desconocido ya baja del 90 al 46 %.

Y un fallo del banco que vio el usuario: la primera versión conducía «gira 40° a ciegas, avanza si
puedes», y con la pared a 29-36 cm y la guardia en 35 **avanzar devolvía False siempre** — el robot
se quedó dando tumbos sin acumular un nodo. *«Está atrapado frente a la pared, deberías darle una
exploración un poco más adaptativa»*. Ahora **gira hasta que el frente se abre**, hacia el lado con
más sitio: 1346 cm en 4 minutos sin atascarse.

Evidencia 96.
## 2026-08-09 (PC, noche) — **La web llamaba «va más despacio» a un robot muerto**

Al integrar los 17 commits del robot, el bloque urgente de `ESTADO_ACTUAL.md` pedía que la
pantalla dijera con todas las letras que un obstáculo dentro del círculo de seguridad
**inmoviliza al robot**. Al ir a escribirlo apareció que la web no es que no lo dijera:
**decía lo contrario, en los tres sitios donde importa.**

```
seguridad.ts   APROXIMACION -> «el robot va mas despacio de lo que se le pide»
               queHacer     -> «si vas marcha atras alejandote, tambien frena»
no_obedece.ts  titulo       -> «te esta frenando, y el robot SI obedece»
               remedio      -> «despeja los LADOS y repite la medida»
espacio.ts     aviso        -> «hacia atras no hay capa de seguridad»
```

Lo medido por el robot (evidencias 93, 94 y 95; 24 estaciones a mano en las cuatro
direcciones): con un punto dentro del círculo, `approach` multiplica el mando **entero**
—lineal y angular— por el tiempo hasta colisión, y ese factor es **cero**.

```
pared DETRAS a 16,8 cm, 188 cm libres delante, por /cmd_vel_raw
  AVANZAR alejandose -> 0,0 cm    GIRAR -> 0,0°    RETROCEDER -> 0,0 cm
```

🔴 **Las tres agrupaban la acción 3 con `RALENTIZAR`, y con una razón escrita al lado:**
*«para quien mira la pantalla son lo mismo: el robot obedece pero más despacio»*. Sonaba
razonable y llevaba ahí desde que se escribió la pantalla. **Era una hipótesis sobre el
efecto, y hay que medirla como cualquier otra** — es la lección de esta entrada.

🔴 **Y dónde estaba la peor:** en `no_obedece.ts`, o sea **LA pantalla que abre alguien
cuyo robot no obedece**. Le contestaba «y el robot SÍ obedece» a quien tenía delante un
robot con tres ceros, y lo mandaba a **repetir la orden** y a **probar marcha atrás** — las
dos cosas que están medidas y no funcionan.

**Lo hecho:**

| | |
|---|---|
| `APROXIMACION` va **sola** | efectos nuevos `INMOVILIZA` y `PUEDE_INMOVILIZAR` |
| dice **«no puede salir solo»** | con los tres ceros, y que el giro tampoco lo saca |
| `sinSalidaDesdeLaWeb` | ningún botón, y una prueba impide que un remedio sugiera alejarse |
| **15 cm**, no 18 | una prueba falla si aparece «18 cm»: sería un robot sin el fichero nuevo |
| *recortado* ≠ *congelado* | se decide **mirando `/odom`**, no deduciéndolo del `action_type` |

📌 **La conjunción es del robot, y es lo que hace honesto el mensaje.** Escribió *«cuando
`action_type = 3` **y el robot no se mueva**»*: `approach` cubre desde «un poco más lento»
hasta cero con **el mismo** `action_type`, así que sin mirar el efecto no se puede elegir.
El umbral de «quieto» **no se inventa**: es la resolución de lo que la pantalla pinta (tres
decimales), así que quien lea «no se mueve» ve un `0,000` al lado y puede comprobarlo.

**Y una tercera afirmación falsa, en el taller.** `AVISOS_ESPACIO` le decía al alumno que
*«hacia atrás no hay capa de seguridad: un retroceso no está protegido por nada»*. Falso por
dos vías, las dos ya medidas en este repositorio: el círculo es un **círculo** (17,8 detrás ·
16,1 delante · 17,9 y 17,9 a los lados) y `Precaucion` llega a **−0,24 m**, o sea 24 cm por
detrás. **No era prudencia de más: enseñaba a desconfiar de una protección que existe**, y de
paso callaba la que de verdad muerde. Sustituido por los dos hechos medidos, incluido el
**~1 cm ciego** (`range_min` 10 cm contra un borde a 9) que ningún parámetro cubre.

**Tres pruebas defendían lo retirado. Se reescriben con el invariante contrario, no se
borran**, para que el diff enseñe qué se retiró y por qué: `espacio.test.ts` exigía la frase
del «hacia atrás»; `seguridad.test.ts` afirmaba que la acción 3 «se presenta como va más
despacio, no como avería».

### ✅ Y el punto ciego de `comprobar_contrato.mjs`, cerrado — lo propuso el robot

Comparaba que el `.msg` **existiera** y nunca lo que hay dentro. El 2026-08-08 el robot
añadió dos campos y avisó de que *«el contrato estará en rojo hasta que alinees»*: **no lo
estuvo**, y fiarse de ese rojo habría dejado los dos campos sin llegar a la pantalla **con
todo en verde** — justo los campos que avisan del fallo de los 41,3 cm.

Ahora guarda `herramientas/campos_msg.json` (**36 campos en 5 `.msg`**) y se pone en rojo
ante cualquier alta, baja o cambio, hasta que alguien lo acepte con
`npm run contrato -- --aceptar-campos`.

✅ **Verificado por efecto y con control en las dos direcciones**, no por ejecutarlo:
añadido `float32 campo_de_prueba` al `EstadoNavegacion.msg` **real** → `código 1`
nombrándolo; restaurado → `código 0`. Reproduce exactamente el caso del 08.

⚠️ **Lo que sigue sin cubrir:** que el campo llegue a la **pantalla**. Un campo aceptado en
la instantánea y no usado sigue sin llegar a nadie. Y las **constantes** del `.msg` quedan
fuera a propósito (no viajan en el mensaje), así que un estado nuevo en un enum **hay que
avisarlo por este canal**.

**También adaptado:** en Navegar, el rodeo de Nav2 por huecos de <~50 cm —168-233 % de la
recta, y si no cabe aborta— como causa a mirar cuando el robot de verdad no llegó; y que
**añadir** una silla a un cuarto ya mapeado lleva AMCL a **1,68 m** de error, que es un
mecanismo más útil que «vuelve a mapear».

**Verificación:** 614 pruebas (eran 590), 46 saltadas · `tsc` y `eslint` limpios ·
contrato `LEER 14 · ESCRIBIR 3 · SERVICIOS 12 · TIPOS 5/5 · CAMPOS 36`.

**Pendiente:** `VALIDAR_CON_EL_ROBOT.md` §2bis — el robot está cargando. Es el punto más
barato de esa lista (una pared a 17 cm y una cinta) y lleva **qué lo refutaría en las dos
direcciones**, incluido el error simétrico: decir «BLOQUEADO» con el robot moviéndose.

---

## 2026-08-09 (robot, noche 3) — **`Aproximacion.radius` bajado de 0.18 a 0.15**

Decisión del usuario, con toda la tabla medida delante. **Es un cambio de imagen dorada** y toca la
capa de seguridad, así que se documenta con lo que se gana, lo que se pierde y lo que no arregla.

**La clave es una simetría:**

```
banda de inmovilización  =  margen ante el error del LIDAR  =  radius − 0,1442
```

**Son el mismo número.** Por debajo del radio circunscrito el bloqueo es correcto —la esquina
barrería el obstáculo—; por encima es un robot congelado sin motivo. Por eso el **0.145** que
coincidiría con el `robot_radius` de Nav2 **no vale**: 0,1 cm de margen contra un ruido de LIDAR
**medido** de ±0,3 cm autorizaría a girar cuando el robot no cabe.

```
                          0.18            0.15
cero del mando            18 cm           15 cm
hueco al parar 0,25 m/s   9,3 9,4 9,3 9,4  6,3 6,3
hueco al parar 0,40 m/s   10,9 (fich. 17)  7,4 6,6     <- velocidad MÁXIMA
banda de inmovilización   3,6 cm          0,6 cm
pasillo mínimo (2×r)      36 cm           30 cm
aceptación F6             pasa            pasa
```

✅ **El control decisivo, a la misma distancia con los dos valores:** pared a 15,8 cm de
`base_footprint` — con 0.18 **congelado**, con 0.15 **gira 34,9° y se aleja 5,7 cm**.

✅ **Y se comprobó que no rompe la aceptación ANTES de adoptarlo.** La banda de F6 se reajustó a
**[14,0 · 19,0]**, y su techo no es cosmético: **un robot que pare a ~19,4 es exactamente lo que
hacía con 0.18, o sea uno al que no le llegó el fichero nuevo.** Con la imagen dorada
repartiéndose a 16 robots, esa banda es lo que lo detecta. `verificar_robot.sh` hace lo mismo: da
**FALLO**, no aviso, si encuentra 0.18.

⚠️ **Lo que NO arregla, escrito para que nadie lo lea como resuelto:** quedan **0,6 cm** de banda
donde el robot sigue congelado sin tocar nada; el **centímetro ciego** de `range_min` sigue igual
porque no depende de este parámetro; y `approach` sigue sin distinguir acercarse de alejarse.

🔴 **No es un botón:** el parámetro **no se puede cambiar en caliente** (evidencia 94), así que
aplicarlo exige editar el YAML y reiniciar `atriz-robot` con 👤 `sudo`.

Alineado en los dos repositorios: `collision_monitor.yaml` (imagen dorada), `prueba_aceptacion.py`
(banda y justificación), `verificar_robot.sh` (FALLO ante 0.18), manual cap. 12, `CLAUDE.md` con su
tabla de valores de referencia, `TRASPASO.md` e `INSTALACION.md`.

Evidencia 95.

## 2026-08-09 (robot, noche 2) — **El barrido de pared, y un parámetro que no hacía nada**

Lo propuso el usuario: el robot pegado a la pared y separándolo **de 2 en 2 cm en las cuatro
direcciones**, probando arrancar y girar en cada estación. Y eligió **moverlo a mano en las cuatro**
pudiendo automatizar dos, para que el método no cambiara entre direcciones. **24 estaciones,
75 filas, en `barrido_pared.csv`.**

**El umbral es el mismo en las cuatro direcciones**, medido desde `base_footprint`:

```
DETRAS     bloqueado hasta 17,8  ·  libre desde 19,6
DELANTE            "     16,1  ·      "      19,8
IZQUIERDA          "     17,9  ·      "      19,7
DERECHA            "     17,9  ·      "      19,7
-> intersección (17,9 · 19,6), que contiene los 18,0 de `Aproximacion.radius`
```

**24 de 24 estaciones todo-o-nada.** Y eso **retira la observación de la evidencia 19** («PUDO
SALIR» con el obstáculo al lado a 17 cm): aquí, a la izquierda y a 17,9, está bloqueado. No hay
dependencia de la dirección. **Banda de defecto: 3,6 cm en las cuatro.**

🔴🔴 **Y el barrido destapó que la evidencia 93 se equivocaba en su punto central.** Decía «causa
aislada bajando `Aproximacion.radius` a 0.12 en caliente». Falso por **dos motivos independientes**:

1. **El parámetro es INERTE en caliente.** `param set` lo guarda, `get` lo devuelve, y el nodo **no
   reconstruye el polígono**. Demostrado con 0,30 —que debería frenar mucho antes— dando el perfil
   idéntico a 0,18 y 0,15: `mando ≈ 0,0125 × (distancia_LIDAR − 18 cm)` en los tres.
2. **El control estaba roto igualmente:** aquella prueba tenía la pared a **18,3 cm**, no a 16,8. Ya
   estaba fuera del círculo y se habría movido con cualquier radio.

⚠️ **Consecuencia práctica que sube el listón:** cambiar el radio es **editar el YAML y reiniciar**,
o sea un cambio de imagen dorada para los 16 robots, no un botón.

✅ **Lo que sí queda medido, y era la única columna que faltaba: el hueco al parar.** Con el valor
en producción (0.18) a 0,25 m/s: **9,3 · 9,4 · 9,3 · 9,4 cm** (n=4, 1 mm de dispersión). Cuadra con
la asíntota y con los 9,9 cm del fichero 17.

✅ **Y se cerró el conflicto del borde delantero a favor del URDF**: con el robot tocando la pared de
frente, perfil perpendicular plano en ±24° con mediana **10,03 cm** (n=3478) y rayos centrales
recortados en `range_min`. La cinta había dado 9,0 porque medía **al chasis**. `base_length 0.190` +
`laser_x −0.005` da 9,0 detrás y 10,0 delante: **el URDF acierta en los tres ejes**, y el LIDAR **no
está centrado**.

📌 Y queda claro que **la referencia que importa es `base_footprint`, no el LIDAR**: el polígono se
centra ahí. Radio circunscrito real **0,1442**.

⏳ **Dos cosas sin explicar, escritas como tales:** un sesgo sistemático de ~1 cm en los costados
entre cinta y LIDAR, y la estación `DELANTE 8`, que leyó más lejos que la de 10 y no se promedia.

⏳ **Y la decisión del radio, cuantificada pero sin tomar:** `banda de trampa = margen ante el error
del LIDAR = radius − 14,42`. **Son el mismo número**, así que no se puede encoger uno sin el otro —
por eso el 0,145 que coincidiría con el `robot_radius` de Nav2 **no vale**: 1 mm de margen contra un
ruido medido de 3. Probar 0,15 exige YAML + reinicio. **La configuración NO se ha tocado.**

Evidencia 94.

## 2026-08-09 (robot, noche) — **El robot atrapado por su propia seguridad**

El usuario, viendo un giro que salió torcido: *«cuando encuentra un obstáculo cercano se atrofia»*.
Aquel giro concreto no lo probaba —era una parada en lazo abierto mía—, pero **la intuición era
correcta y bastante peor de lo que sugería.**

**Con la pared detrás a 16,8 cm y 188 cm libres delante**, mandando por el camino normal:

```
AVANZAR alejándose de la pared  ->  0.0 cm    monitor: APROXIMACION
GIRAR en el sitio               ->  0.0°      monitor: APROXIMACION
RETROCEDER hacia la pared       ->  0.0 cm    monitor: APROXIMACION
```

**Inmovilización total: ni siquiera puede alejarse.** `approach` escala el mando entero por el
tiempo hasta colisión, y con un punto ya dentro del círculo ese factor es 0 **sin mirar si el
movimiento acerca o aleja**. Sólo sale a mano.

✅ **Y girando no rozaría nada.** Con el monitor puenteado —autorizado por el usuario, que lo
vigilaba— dio **359,6° y 358,8° de 360**, en 12,6 s, los mismos que en campo abierto. Su veredicto:
*«no ha tocado la pared en ningún momento»*. El radio circunscrito del robot es ~14,2 cm contra un
círculo de 18: **el monitor es más gordo que el robot.**

✅ **Causa aislada con una sola variable:** bajando `Aproximacion.radius` a 0.12 en caliente, las
tres órdenes funcionan y el monitor **frena al 40 %** en vez de congelar. Restaurado a 0.18.

🔴 **Contradice en parte la evidencia 19**, que anotó «PUDO SALIR: retrocedió 58 cm» — allí el
obstáculo estaba **al lado**, hoy **detrás**. ⏳ Por qué: NO VERIFICADO.

⏳ **No se ha tocado la configuración.** `radius` fija a la vez el hueco al parar y el pasillo
mínimo, y el 0.18 está respaldado por «para a 20,8 cm sin chocar». 👤 Decisión del usuario.

**Tres fallos del banco, y el usuario paró los tres.** El peor: **la métrica daba el mismo número
para «giró 360°» y para «no se movió»** —`wrap(yaw_final − yaw_inicial)` contra un pedido que
normaliza a 0—. Imprimí «error −0,1°» tres veces con el robot parado y **llegué a escribir una
evidencia entera concluyendo lo contrario de la verdad**; se retiró antes de subirla. Lo paró él
mirando el robot: *«es que ni siquiera giró»*.

🔴 **Y un defecto mayor que salió de rebote:** el mapa de slam_toolbox estaba **casi vacío y
congelado** —49 celdas ocupadas para un cuarto entero, idéntico celda por celda tras 360° de giro y
160 cm de vaivén, con el LIDAR sano—. Eso **bloquea la casilla pendiente** (AMCL sobre un mapa con
los objetos) y **obliga a matizar la evidencia 91**: su «engorde de 5 cm» se dedujo de tres celdas
sobre ese mapa. El efecto en el costmap sigue medido; el mecanismo no. ⏳ Causa NO VERIFICADA, y es
prioritaria: es la ruta con la que se hacen los mapas del aula.

**Y la geometría del robot, medida por el usuario y validada contra el LIDAR:** del eje del LIDAR
al borde hay **9,0 cm delante y detrás, 10,8 a cada costado** — o sea el LIDAR está **centrado** y el
robot mide **18 × 21,6 cm**, con radio circunscrito **0,1406 m**. Se validó separándolo 3 cm de la
pared: el LIDAR leyó **12,20 cm** donde la cinta predecía **12,00**, con n=8268 rayos y perfil plano
en ±20°. **2 mm de error.**

🔴 **Eso corrige una afirmación de `collision_monitor.yaml`**, que decía «el punto ciego de 10 cm cae
DENTRO del chasis, no hay zona muerta» — calculado con la media longitud **cruzada** del URDF
(0,109). Con la real de 0,090, el X2 **no ve el primer centímetro por delante ni por detrás** del
chasis. Ningún polígono puede cubrirlo: no es cuestión de ajustar `radius`, es que el sensor no da el
dato. Medido: con el robot **tocando** la pared se descartaron **10 277 rayos traseros** por debajo
de `range_min`, y sólo sobrevivió uno oblicuo recortado en 10,02 cm — que basta para que el monitor
siga congelando al robot.

⏳ **La tabla de decisión del radio ya tiene la geometría, pero le falta la medida que importa:**
la columna «para a» sale de un modelo (`≈ radius − 0,09`) y la única cifra real es «para a 20,8 cm
sin chocar» con 0,18. **Falta medir la distancia de frenado a cada radio candidato** — y hasta
entonces el radio no se toca.

**Y una segunda zona ciega que el manual negaba con sus propios números.** Decía «el punto ciego de
10 cm cae dentro del chasis (media longitud 0.091), no hay zona muerta» — pero `0.100 > 0.091`, así
que **sobresale**. Confirmado con el robot tocando la pared: **10 277 rayos traseros descartados** y
un solo superviviente oblicuo, recortado en 10,02 cm. **Ningún polígono puede cubrir ese
centímetro**: no es cuestión de ajustar `radius`, es que el sensor no da el dato. A los costados sí
queda dentro del chasis (media anchura 0,108).

⏳ **Y queda un conflicto abierto en el borde delantero**, que no se resuelve por decreto: la cinta
de hoy da **9,0 cm** y el URDF **10,0** (`base_length 0.190` con `laser_x −0.005`, medidos el
2026-08-02). El trasero cuadra exacto en las dos y es el único con desempate instrumental. Se cierra
repitiendo la misma prueba con el robot mirando a la pared. **No se toca el URDF mientras tanto:
cambiar un valor medido por otro medido sin desempate es como se metió el cruce de ejes original.**

Alineado en los dos repositorios: `collision_monitor.yaml` (imagen dorada), manual cap. 12,
`CLAUDE.md`, `TRASPASO.md`, evidencia 93 y el banco `medir_limite_del_monitor.py`.

Evidencia 93.

## 2026-08-09 (robot, 15:07) — **El `FALLO` del obstáculo, cerrado por su efecto**

Se aplicó la regla que salió de las evidencias 90 y 91 —**hueco de 60 cm medido con cinta**— y se
volvió a correr `prueba_aceptacion.py --solo F7`. **12 PASA · 0 REVISAR · 0 FALLO.** El objetivo con
obstáculo, que era el único hallazgo real de las 74 comprobaciones del 2026-08-08, da `SUCCEEDED`
con 8,0 cm de error y 13,0° de rumbo.

**Y se comprobó por una vía independiente, porque «PASA» también puede mentir:**

```
                                 2026-08-08        hoy
  planificador «failed to plan»       8              0
  «detected collision ahead»          —              0
  «Controller patience exceeded»     sí              0
  recuperaciones          spin→backup→spin       NINGUNA
  desenlaces                   Goal failed   3 SUCCEEDED · 0 failed
```

Nav2 no tuvo que recuperarse ni una vez. Coincide con lo que predecía la 91: con 60 cm el plan sale
recto y no hay rodeo que se coma el cuarto.

⚠️ **Un margen justo que queda anotado, no celebrado:** el desvío lateral dio **17,2 cm sobre una
banda [15, 50]** — pasa por 2,2 cm. El suelo de esa banda existe para demostrar que el robot
**rodeó**; con 60 cm el plan es casi recto, así que los 17,2 cm salen sobre todo de que el obstáculo
va escorado 6 cm. **Si alguien ensancha el hueco «para ir sobre seguro», el desvío bajará de 15 y la
comprobación dará FALLO con el robot habiéndolo hecho bien.** La banda **no se toca** sin medir.

✅ **Y el aviso añadido esa misma tarde se ganó el sitio en la primera tanda.** El usuario preguntó
antes de lanzar: *«el robot quedó torcido, ¿el obstáculo va delante de este nuevo POV o del
inicial?»*. La corrida imprimió `rumbo tras el regreso: +53° (partida +62° -> desvio -8°)` y
`A 0.75 m, -8° desplazan «delante» 11 cm de lado`. Sin ese número el montaje se habría hecho sobre
el eje equivocado.

⏳ **Sigue sin haber vía libre, y es correcto:** con `--solo F7` las otras nueve fases quedan
PENDIENTE por diseño. Hace falta una corrida entera F0-F9. De los cuatro pendientes de F9 ninguno es
del robot: rosbridge Fase B, y tres del usuario (precipicios, PSK, histórico de git).

⏳ **Y una casilla que se escapó:** F7 construye un mapa de SLAM **con el obstáculo dentro** —el
artefacto exacto que hace falta para probar «AMCL sobre un mapa que sí contiene los objetos»— pero
**lo levanta y lo tira, no lo guarda.** Habrá que mapear aparte con `map_saver_cli`.

Evidencia 92.

## 2026-08-09 (robot, tarde) — **La variante con SLAM: el mapa engorda los objetos**

Se hizo lo que la evidencia 90 dejó pendiente —**quitar a AMCL del medio usando SLAM**— y el
resultado obligó a **retirar la explicación de esa misma evidencia**, escrita horas antes.

**Lo que se retira:** «AMCL casa contra un mapa sin los objetos, el ajuste es malo y la pose
resbala». Con SLAM, que mapea la puerta en vivo, el robot **falla igual**: `ABORTED` a los 5,7 s con
`map -> odom` en **0,035 m** (contra 1,68 m con AMCL). La deriva era real, pero era otro síntoma,
no la causa.

**Lo que sí es la causa, medido con los tres instrumentos sobre la misma fila:**

```
LIDAR crudo (retornos)   ... (82,-21)   [HUECO 44,8 cm]   (82,+24) ...
cinta del usuario                          45 cm
MAPA DE SLAM en x=85     ocupado en -20, -15  y en +20  ->  hueco 35 cm
```

**El mapa engorda los objetos ~5 cm por lado.** Un hueco de 45 cm entra como 35, la inflación del
radio inscrito (14,5 cm) lo deja en **una celda a coste 96**, y en la fila exacta de los objetos en
ninguna. NavFn no puede cruzar y **traza un rodeo**: 168-233 % de largo, 68-115 cm de desvío
lateral, en un cuarto con 55 y 67 cm a los lados. El rodeo roza la inflación, el controlador ve
colisión, y `failure_tolerance: 0.3` lo mata en tres décimas.

✅ **Eso explica el único `FALLO` de la prueba de aceptación del 2026-08-08.** Y da una regla con
número: **hueco mínimo ≈ 49 cm para ser transitable, y entre 45 y 60 para que Nav2 no prefiera
rodear** — con SLAM; ver la corrección de alcance más abajo.

**La herramienta que lo cerró, y la lección que vale más que el resultado:** `compute_path_to_pose`
**planifica sin mover el robot**. Cuatro tandas con el robot en marcha —dos con AMCL, dos con
SLAM, un choque y 66 puntos de batería— no distinguieron «Nav2 traza recto y el robot no sigue» de
«Nav2 traza un rodeo». Una consulta de dos minutos sí. Nueva: `mediciones_banco/consultar_plan.py`.

**Dos hipótesis propias probadas y descartadas**, que cuesta lo mismo y vale igual: vaciar las capas
de obstáculos acumuladas no cambió nada, y bajar `inflation_radius` a 0.18 en caliente tampoco
—se restauró a 0.25 y se verificó—. Y una acusación falsa que desmontó el usuario: «la odometría se
inventó dos metros» era, en realidad, que él había recogido el robot tras un choque. El control lo
confirma: **31,1 cm de odometría contra 32,1 de LIDAR.**

**Cuatro fallos más del banco, van diez** — el séptimo es el peor: `/set_pos_and_yaw` con SLAM viva
**corrompe el mapa**, porque mueve el origen de `odom` bajo los pies de slam_toolbox. Mover el robot
a mano hace lo mismo: después hay que **reiniciar SLAM**.

🔴 **Y una corrección que pidió el usuario en el mismo turno, sobre la conclusión recién escrita:**
*«pero en la prueba inicial con AMCL sí pasó por 45 cm»*. Cierto, y estaba en la tabla de la
evidencia 90. Se repitió con el robot en la marca y la puerta en 45: **con AMCL el plan sale RECTO**
(109 %, 13 cm) en cuatro consultas. El perfil del costmap dice por qué — con AMCL la puerta la marca
**sólo la capa de obstáculos del LIDAR**, fina, y el canal queda abierto a coste 84; con SLAM entra
en la **capa estática engordada** y se cierra. **La regla de los 49 cm vale CON SLAM**, que es lo que
lanza F7 y donde apareció el FALLO. ⏳ Falta la casilla del aula: AMCL sobre un mapa que **sí**
contiene los objetos — los mapas del aula se hacen con slam_toolbox y se guardan, así que la
predicción es que se comporte como SLAM. **NO VERIFICADO.**

Evidencia 91. Escalado a `CLAUDE.md`: el engorde del mapa con su regla, `compute_path_to_pose` como
primer instrumento, que **99 en el costmap es intransitable, no «casi»**, el teletransporte de SLAM,
la exclusión SLAM/AMCL del supervisor, y `failure_tolerance` anotado pero **sin tocar**.

## 2026-08-09 (web, 5) — **Barrido de lo retirado a medias**

Alineación final de la sesión. Al repasar los documentos apareció el descuido que este proyecto
persigue con el nombre de *«busca TODAS las menciones, no la primera»*, cometido dos veces:

| dónde | qué decía todavía |
|---|---|
| `README.md`, fila de SLAM | Empezaba retractando *«los servicios no existen en el robot»*… y **terminaba repitiéndolo** tres líneas más abajo. Y decía «sigue sin verificar esta pantalla», con la pantalla ya validada |
| `navegacion.ts`, cabecera | *«TODO ESTE FICHERO ES NO VERIFICADO CONTRA EL ROBOT»* — cierto el 07, falso desde el 09 |

📝 **Un «no verificado» que ya no lo es manda a desconfiar de código que funciona**, y gasta la
credibilidad de los avisos que sí importan. Misma regla que hizo quitar el aviso de «los LEDs se
encienden al arrancar el driver», que llevaba meses siendo falso.

✅ **Y lo que sí se conserva a propósito:** las citas de lo retirado **dentro de sus bloques de
retractación**. Se distinguen de la deriva en que van con el «esto era falso» al lado — la forma
del fallo vuelve, y borrarlas dejaría el camino abierto otra vez.

Añadidas además dos filas al README que faltaban: la de SLAM ya validada —con `CIEGO` y `MUDO`
vistos de verdad— y la del **desenlace de Nav2, que no se cree en ninguna dirección**.

**590 pruebas** · contrato 14 · 3 · 12 · `tsc`, `eslint` y el auditor de documentación limpios.

---

## 2026-08-09 (web, 4) — **El desenlace de Nav2 miente en las DOS direcciones**

Revisadas las cinco actualizaciones del robot. Una recae de lleno en la web y ya está adaptada; el
resto —PSK, `fmask`, la prueba de aceptación entera— es de robot y de flota.

### 🔴 `ABORTED` también miente

La evidencia 88 midió `default_server_timeout: 20` —**veinte milisegundos** para que el controlador
acusara recibo— y `bt_navigator` rindiéndose mientras `controller_server` conducía:

```
  22:18:57  Received a goal, begin computing control effort
  22:18:57  Timed out … Aborting handle · Goal failed
  22:19:07  Reached the goal!            ← DIEZ SEGUNDOS DESPUÉS
```

El robot recorrió 67 cm y llegó, con la acción marcada como fallida. **Tres tandas dadas por
fallidas eran buenas.**

Ya se sabía que `SUCCEEDED` puede estar equivocado en 41 cm. **Ahora las dos direcciones fallan**,
así que el desenlace no informa de nada:

- el título del aviso deja de decir «el objetivo falló» y dice **«la acción falló · el robot puede
  haber llegado igual»**;
- y los dos textos hablan de la **acción**, no del robot.

✅ **Y se hace lo que el robot pidió con esas palabras:** *«lo que sí se puede mostrar es el
desplazamiento por `/odom`, que es la fuente que acierta a 0,3-4,2 cm»*. La pantalla anota la
posición al mandar el objetivo y enseña el recorrido en el desenlace, gane o pierda. En vez de
«mira el robot» a secas, **un número**.
⚠️ Y no es la distancia al objetivo, es **cuánto se movió**: lo primero exigiría cruzar `map` con
`odom`, que es justo el cruce que se equivoca. Se muestra lo que se sabe.

📊 Los números pasan a **n=3** sobre mapa fresco: **6,1 · 11,8 · 11,3 cm**, con **dos de tres
fuera** de la tolerancia de 10.

### 📌 Una restricción dura nueva, por si acaso

`/initialpose` está en la lista blanca y **la web no lo usa**. Si algún día lo usa, **el sello va a
cero**: el banco del robot lo publicaba 69 ms por delante de TF y AMCL lo descartó **en las diez
tandas de la historia del proyecto**, sin que nadie se enterara —no hay respuesta ni error—. Un
`Date.now()` del navegador sería peor todavía: ni siquiera comparte reloj con el robot.

### ⚠️ Y el doble se había quedado atrás otra vez

`rosbridge_de_mentira.mjs` no publicaba `mapa_nombre` ni `mapa_edad_s`, así que la pantalla pintaba
su texto de reserva sobre un doble que simplemente no los mandaba. **Mismo descuido que costó los
nombres de campo de `/encoders`.** Queda escrito en el fichero: al cambiar un `.msg`, el doble va
detrás en el mismo tirón.

**590 pruebas** · contrato 14 · 3 · 12 · `tsc` y `eslint` limpios.
## 2026-08-09 (robot) — **El seguidor de línea se aparca hasta el aula, y no por la cinta**

Decisión del usuario. Lo que importa es **el motivo**, porque cambia dónde vive el pendiente.

La razón obvia sería «no hay cinta». **No es ésa.** Una línea pegada en el suelo de una habitación
**no reproduce lo que esa práctica tiene que validar**: el recorrido real, su iluminación y el
contraste sobre el suelo del laboratorio.

📌 **Y no es una precaución teórica.** El seguidor decide **por umbral del canal `claro`**, y esta
misma semana se midió que el suelo da **1275 en una habitación y ~950 en otra, con el mismo robot y
el mismo día**. Validarlo aquí mediría **el suelo, no el algoritmo** — y daría un ✅ que no se
transfiere.

✅ **Reclasificado: sale de «lo que falta hacer» y entra en «lo que espera al aula»**, junto al
SSID que nunca ha casado, la F0 del AP y el mapa del laboratorio.

⚠️ **Lo que no cambia:** el seguidor **nunca se ha probado sobre una línea real**. Sus funciones
puras tienen tests y su diseño se corrigió durante la implementación —el original, un PID de umbral
único, **no podía funcionar** con un solo sensor mirando abajo— pero el robot no ha seguido una
línea física ni una vez. Sigue **NO VERIFICADO**, ahora con la fecha de cuándo podrá verificarse.

📝 **La lección de método:** aparcar algo por la razón equivocada lo deja mal colocado. «Falta
cinta» lo pone en la lista de mañana; «hace falta el laboratorio» lo pone en la del despliegue.
**Son dos planificaciones distintas.**

---

## 2026-08-09 (web, 3) — **Corrección: el umbral de 7 días SÍ existía. El error fue mío**

El robot cerró la sesión devolviéndome una de mis dos devoluciones, y tiene razón.

Escribí —en el `CHANGELOG`, en `TRASPASO.md`, en `CLAUDE.md`, en el código y en dos mensajes de
commit— que el umbral de 7 días para la edad del mapa *«no existe en `verificar_robot.sh` ni en
ningún otro script»*. **Existe:** `verificar_robot.sh:1459`, `if [[ "$DIAS_MAPA" -le 7 ]]`, puesto
el día anterior.

🔴 **Por qué no lo encontré, que es lo que hay que aprender:** mi `grep` buscaba `7 días`,
`604800`, `-mtime +7`, `days=7`. El código dice **`-le 7` sobre una variable**. Ninguno de esos
patrones podía casarlo. **Concluí «no existe» de una búsqueda que no podía encontrarlo.**

📝 Es la versión con `grep` del error que este proyecto persigue desde el principio: *«antes de
concluir que algo NO ocurre, pregunta cuánto tendrías que haber esperado»*. Aquí la pregunta
equivalente es **«¿podía mi patrón casar con lo que busco?»**, y no me la hice. Y duele más porque
el negativo se usó para **desacreditar a quien tenía razón**.

✅ **Lo que no cambia:** la web sigue **sin umbral**, y el robot lo acepta explícitamente —*«su
conclusión es mejor que mi cita: gana el suyo»*—. Pero el motivo bueno era el segundo, no el
primero: **`mapa_edad_s` es el `mtime`, así que copiar un mapa viejo lo rejuvenece y un semáforo
daría verde justo en el caso peor.** Eso se sostiene solo, sin necesidad de discutir la cita.

⚠️ Y una diferencia de contexto que sí vale: **en el verificador el umbral es razonable** —es un
aviso para quien está en el robot, que puede mirar el aula— y en la pantalla no, porque ahí se
leería como un veredicto. **El mismo número puede ser correcto en un sitio y engañoso en otro**,
que es la lección que este fichero ya tiene escrita para los umbrales en milisegundos.

### ✅ Y lo que el robot cerró por su lado

- **El disparador de `girar()` NO se reprodujo**: siete hipótesis descartadas midiendo (~32 tandas
  y un soak de 5 min), racha máxima **1** contra un umbral de 250 ms. Documentado como **negativo
  útil**: acota el fenómeno y mide el margen del arreglo (2,0 s son 20× el peor caso producible).
  ⚠️ Con lo que no se puede decir dicho: **el arreglo no está verificado contra el disparador
  real**. Un fallo que sale 1 de 4 y luego no sale en 32 no está entendido.
- Y cayó la hipótesis que parecía la buena —`/scan` compitiendo en el mismo ejecutor—: **108,2 ms
  contra 107,8**.
- **La devolución del contrato era suya y la aceptan**: `comprobar_contrato.mjs:228` solo hace
  `existsSync(rutaMsg)`. Cambian su proceso: al tocar un `.msg`, lo dicen explícitamente en vez de
  confiar en que el contrato lo cace.

---

## 2026-08-09 (web, 2) — **El mapa con nombre y fecha, y dos cosas que le devuelvo al robot**

Bajados los cinco commits del robot. Su auditoría de `atriz-lab` da **11 de 11 trampas cubiertas**
y su único hallazgo serio era suyo —faltaba el dato para avisar de la edad del mapa—, que
resolvieron el mismo día con `mapa_nombre` y `mapa_edad_s`. Ya están en la pantalla.

✅ **Verificado contra rvr-01:** *«Mapa en uso: cuarto3.yaml · guardado hace 1 día»*, que coincide
con los 104 976 s que publica el topic.

### 🔴 Sin semáforo, y no por pereza

El robot proponía avisar a los 7 días *«que es el mismo umbral que ya usa `verificar_robot.sh`»*.
**Fui a mirarlo y ese umbral no existe** — ni en ese script ni en ningún otro del proyecto.

Pero el motivo de fondo es mejor que la cita: **la edad no mide lo que falla.** El fallo no es «el
mapa es viejo», es «el mapa **no es de este sitio**», y uno de ayer del cuarto equivocado es igual
de peligroso que uno de hace un mes. Y `mapa_edad_s` es el `mtime`: **copiar un mapa viejo lo
rejuvenece**, así que un semáforo daría **verde justo en el caso peor**.

→ La pantalla no gradúa: **pregunta**. Es lo que dice el propio `.msg` — *«el robot da los dos
datos y la persona decide»*. Una prueba impide que alguien añada el umbral sin justificarlo.

### 📌 Y lo segundo, que es del método: `comprobar_contrato.mjs` NO se puso en rojo

El robot escribió: *«Le toca al PC añadir los dos campos a `contrato.ts`; `comprobar_contrato.mjs`
estará en rojo hasta entonces, que es lo correcto»*.

**No lo estuvo.** Se ejecutó antes de tocar nada y dio los cuatro ✅. El comprobador compara los
**nombres** de topics, servicios y tipos —y de los tipos solo que el `.msg` exista—, así que
**añadir campos a un `.msg` es invisible para él**. Si me hubiera fiado de su rojo, los dos campos
seguirían sin llegar a la pantalla y todo verde.

📝 Es exactamente la forma que este proyecto persigue: **una comprobación que se creía que cubría
algo y no lo cubre**. Misma familia que «`ros2 topic list` incluye topics de nodos muertos» y que
los ocho fallos propios del verificador. ⏳ Cerrarlo sería que el comprobador leyera los campos
del `.msg` y los cruzara con la interfaz de TypeScript — **no se hace hoy**, pero queda dicho para
que nadie vuelva a apoyarse en un rojo que no va a salir.

### ✅ Y lo que el robot cerró de mis dos pendientes

- **`rosapi/get_param` sí funciona**: el nombre va como `<nodo>:<parámetro>`. Mi conclusión —*«la
  web no puede preguntar por la configuración del robot»*— era **un rediseño entero apoyado en una
  llamada mal formada mía**. Y debajo había algo peor: **esa llamada mata el nodo ~30 s después**,
  con `systemctl` en verde. Arreglado con `respawn`.
  ✅ **Sin agujero abierto en la web:** no usa `rosapi` en ningún sitio — la auditoría lo confirma
  («cero dependencias, le pasa por encima»).
- **`ATRIZ_MAPA`** apunta a `/home/sphero/mapas/cuarto3.yaml`, y los dos directorios son correctos
  y distintos: el del paquete es el mapa **de la flota**, `~/mapas` es lo que **SLAM produce aquí**.

📝 **La lección que ellos escribieron y me llevo:** *«el que ve el síntoma no ve el log»*. El
`[WARN] Malformed parameter name` estaba en el journal desde mi primera llamada, y desde el PC no
hay forma de verlo.

---

## 2026-08-09 — **La web, validada contra rvr-01. Tres fallos que solo se ven con el robot**

Pasada entera de `atriz-lab/VALIDAR_CON_EL_ROBOT.md` con el robot encendido. Todo lo construido
los días 07 y 08 se había hecho contra un doble; esto es el contraste.

### ✅ Los seis estados de SLAM, vistos de verdad

```
  apagado -> arrancando · 4 → 9 → 14 s -> funcionando        ~18 s
  CIEGO    apagando el barrido con SLAM vivo
  MUDO     aparecio SOLO al parar SLAM
  parar    funcionando -> MUDO -> apagado
```

`CIEGO` es el que justifica el diseño: *«levantado, pero no le llega el barrido — el robot no
conducirá»*, con el detalle del robot literal —«encendido pero SIN barrido: no puede funcionar»—.
**Es exactamente el estado que `systemctl is-active` llamaría `active`.** Un interruptor lo habría
pintado verde.

SLAM además construyó un mapa real (71×82 celdas a 5 cm) que la pantalla dibujó, distinguiendo
*«esto parece SLAM, no Nav2»* por la ausencia de `/amcl_pose`.

### 🎯 El 2×2 del sensor de color, las cuatro casillas por la web

```
  MISMA pantalla roja      luz APAGADA          luz ENCENDIDA
  lectura               R 78 · G 15 · B 3   R 409 · G 721 · B 357
  R/G                          5,0                  0,57
  veredicto                «es rojo» ✅     «no se puede decir» ✅

  MISMO papel rojo mate    luz APAGADA          luz ENCENDIDA
  lectura                  0 · 0 · 0 · 0     R 583 · G 197 · B 62
  veredicto           «no se puede decir» ✅     «es rojo» ✅
```

Factor **9** entre los dos cocientes de la pantalla, sobre el mismo objeto físico y a lados
opuestos de 1. **Con la regla ingenua —`R/G > 1` es rojo, si no verde por descarte— la casilla de
arriba a la derecha habría dicho «verde» sobre una pantalla roja.**

### 🔴 Los tres fallos que encontró la pasada

**1 · Ruido no es un color.** Robot sobre suelo mate en modo emisión: `R=0 G=1 B=0`, y la pantalla
afirmó *«la luz que sale de la superficie es verde»*. Verde era el caso **por descarte** y una sola
cuenta se coló por el borde de una guarda que comprobaba `verde === 0`.
📝 Es la lección que este proyecto tiene escrita —*«un test que barre tres puntos representativos
puede dejar sin cubrir justo el tramo donde vive el bug»*— cometida en el fichero donde la cité.
El arreglo lleva el umbral **derivado**: las cuentas son enteras, el error de `R/G` es ±1/G, y con
G=1 eso es ±100 %. La prueba nueva barre el tramo entero, no tres puntos.

**2 · El acuse de petición mentía dos veces.** Seguía diciendo *«no dirá "funcionando" hasta que
lo esté»* **un minuto después** de estar funcionando, con la palabra escrita tres centímetros más
arriba; y ese mismo texto salía tras pulsar PARAR, donde no significa nada.

**3 · 🔴 El apagado automático de la luz NO saltó.** Pestaña cerrada tras la última lectura, la luz
siguió encendida **14 min 38 s** —visto en el robot por el usuario, no solo en `color_activo`— y se
apagó porque la apagué a mano. El apagado por inactividad son 120 s y pasaron 878.
⚠️ **El tope duro de 900 s queda sin medir, y por mi culpa:** lo apagué a menos de dos segundos de
cuando habría vencido.
📌 **Hipótesis, no medida:** el driver cuenta como actividad que alguien esté suscrito a `/color`, y
rosbridge puede conservar la suscripción cuando la pestaña se cierra de golpe. Se cierra con
`ros2 topic info /color` en el robot, con la web cerrada.
→ **La pantalla ya no promete que se apague sola.** Una promesa incumplida sobre la batería es de
las peores que puede hacer esta interfaz: el alumno se fía y el robot se queda sin clase.

### 🔴 Y una corrección de mi propia lista de validación

Decía que `BLOQUEADO` se produce pidiendo Nav2 sin mapa tres veces. **Es falso**, y se vio al
leer el supervisor **antes** de pedirle al usuario que quitara el mapa: comprueba `hay_mapa` y
devuelve un rechazo limpio **sin llamar a `systemctl`**. Su propia cabecera lo dice — *«por eso este
nodo se NIEGA antes de llamar a systemctl. Un `isfile` de coste cero evita el único estado del que
la web no puede salir sola»*. **`BLOQUEADO` es inalcanzable desde la web a propósito**: una
propiedad del diseño, no un hueco.
📝 Copié la consecuencia de un comentario del `.msg` que describe el `systemctl start` **a mano**,
o sea la situación anterior al supervisor, sin comprobar si el camino seguía abierto.

### 📌 Dos preguntas para el robot

1. **`ATRIZ_MAPA` apunta fuera de la ruta por defecto** — el directorio del código está vacío en
   rvr-01 mientras `hay_mapa` dice `true`. No es un fallo, pero **no está escrito en ningún
   documento del PC** y quien lea el código deduce la ruta equivocada.
2. **`rosapi/get_param` revienta**: `result=true` con `successful=false` y
   `cannot access local variable 'node_name'`. Error interno, no respuesta. Si `rosapi` no sirve
   para leer parámetros, la web no puede preguntar por la configuración del robot y todo tiene que
   venir por topic o servicio propio.

### 📝 Y tres veces que el instrumento fui yo

- los 7,3 s de apertura del WebSocket que me preocupaban eran **Node resolviendo mDNS**: desde el
  navegador son **2736 ms en frío y 16-25 en caliente**, dentro del plazo de 10 s;
- la primera medida de frecuencias contó 8 s desde el arranque del proceso con un socket que tardó
  7,3 en abrir → midió sobre 0,7 s y dio **0,5 Hz sobre un `/odom` a 16,58**;
- y el detector de tokens de color nació con **ocho falsos positivos**.

**579 pruebas** · contrato 14 · 3 · 12 · `tsc` y `eslint` limpios.

---

## 2026-08-08 (web, 2) — **La capa de seguridad deja de ser invisible para el alumno**

Barrido de los veinte commits del robot buscando lo que la web todavía no reflejaba. Quedaba el
más importante para quien está delante del robot.

### 🔴 «Pide 60 cm, obtiene 26, y no recibe ningún mensaje»

Es la frase de la evidencia 85, y describía exactamente lo que hacía la interfaz. La misma orden,
dos veces seguidas y sin tocar nada: **26,4 cm** y **59,5 cm**. No es un fallo —es el
`collision_monitor` frenando al 40 %— pero **el journal lo registra y la pantalla callaba**, así
que la conclusión natural del alumno es que el robot no le hace caso.

El dato que lo explica es **el ancho**, y la web solo decía el largo: `Precaucion` mide 60 cm de
largo por **40 de ancho** sobre un robot de 21,7. **Cualquier cosa a menos de ~9 cm de un
costado** lo frena — una pata de silla, un zócalo, tu propio pie— y lo frena **aunque el robot se
esté alejando de ella**.

- `PanelConducir` se suscribe a `/collision_monitor_state` y lo pinta **en vivo, pegado a
  «medido»**, que es donde aparece la discrepancia. En un pie de página sería no ponerlo.
  ⚠️ Cuesta ~0: el monitor publica **al cambiar**, no cada tanto.
- `no_obedece.ts` gana una causa, y su caso delicado es el silencio: **sin mensaje del monitor NO
  se descarta** — se dice «no se sabe»—, porque con el robot quieto no llega ni uno y tratar el
  silencio como «no está frenando» descartaría **la causa más probable** de que un avance salga
  corto. Es la misma forma que «`ros2 topic list` conserva topics de nodos muertos».
- Y separa `invalid source` —que es **falta de LIDAR**— de un obstáculo real: mandar a apartar
  algo que no existe es justo el falso diagnóstico que esa pantalla existe para evitar.

### ✅ El hueco de `/odom`: verificado, y una constante que NO se toca

El robot midió **325,7 ms** de peor hueco recién reiniciado el driver, contra 78-81 en régimen
permanente. `UMBRAL_SILENCIO_MS` (3000) **se queda** —sigue holgado—, pero:

- **el margen real es 9×, no 37×**, y quien lo baje tiene que compararlo contra 326. Una prueba lo
  fija contra el peor régimen medido, no contra el cómodo;
- y se **comprobó** que la constante sigue copiando la del driver (`silence_timeout=3.0` en
  `robot.launch.py`). Lo que subió a 2,0 s fue `SILENCIO_ODOM_S` de `atriz.py`, **otro consumidor**.
  📝 Merece decirse porque es la trampa de siempre: dos constantes con nombres parecidos, y la
  tentación de arrastrar una porque cambió la otra.

### 📋 `VALIDAR_CON_EL_ROBOT.md`

Con el robot apagado, todo lo nuevo está construido contra un doble. El fichero lista qué
comprobar **y qué lo refutaría** en cada punto —incluidos los tres estados que hay que provocar a
mano: `CIEGO` apagando el barrido, `MUDO` reiniciando el driver bajo SLAM, y `BLOQUEADO` pidiendo
Nav2 sin mapa tres veces—. Sin la línea de refutación, una pasada verde no distingue «funciona» de
«no llegué a probarlo».

**574 pruebas**, contrato 14 · 3 · 12, y las 42 guardias sobre pantallas reales en verde.

---

## 2026-08-08 (web) — **La web se pone al día: dos afirmaciones mías retiradas**

Veinte commits nuevos del robot. Tres tocan `atriz-lab`, y **dos desmienten cosas que la interfaz
decía en pantalla**.

### 🔴 Retirado 1 · «los servicios no existen en el robot»

`ControlNavegacion` nació con un aviso que decía *«NO VERIFICADO […] hasta que el supervisor corra,
`/pedir_slam` y `/pedir_nav` **no existirán en el robot**»*. **Era falso al escribirse:** el
supervisor lleva corriendo desde el 2026-08-07 y esa misma tarde los dos se usaron de verdad — uno
mapeó un cuarto, el otro levantó Nav2, que navegó.

📝 **La lección, en su versión de dos máquinas:** este cliente dedujo el estado del robot de
**cuándo se había subido el código**, no de haberlo consultado. **El repositorio dice qué existe;
solo el robot dice qué está corriendo.** Es la misma forma que «`ros2 topic list` incluye topics de
nodos muertos».

### 🔴 Retirado 2 · los 6 cm, que eran n=1 otra vez

El 07 corregí en `PanelNavegar` un *«el error al llegar es de 8-10 cm»*, y **al corregirlo escribí
«con el cuarto remapeado acabó a 6 cm»** — n=1 presentado como propiedad, exactamente el error que
acababa de señalar. La réplica del robot:

```
  tanda 1    6,1 cm   ✅ dentro de 10
  tanda 2   11,8 cm   🔴 fuera        <- y Nav2 dijo SUCCEEDED igual
  mapa viejo 41,3 cm  🔴 fuera        <- y Nav2 dijo SUCCEEDED igual
```

La pantalla ya no da una cifra de un día bueno: da **las tres**, y dice que **el desenlace no
informa de la precisión**. Esa es la forma, y es lo único sobre lo que se puede construir una
promesa para un alumno.

### ✅ Nuevo · el sensor de color y sus DOS modos

Siguiendo el «contrato para la web» que escribió `SENSOR_COLOR.md`, sin inventar un número:

| | reflejo | emisión |
|---|---|---|
| para qué | suelo, cinta, papel | pantalla, baldosa LED |
| la luz | encendida | **apagada** |

🔴 **No es una diferencia de precisión: es de signo.** Sobre una superficie que emite, medir con el
LED encendido da el resultado **invertido** — una pantalla roja a tope sale con `R/G = 0,66`, o sea
menos roja que verde. La interfaz **se niega a nombrar un color** dentro de la banda plana y dice
qué hacer, en vez de dar un nombre que acierta o se invierte según lo que haya debajo.

Tres decisiones que salieron de medidas, no de gusto:
- **El modo no tiene valor por defecto.** Lo tuvo, y abrir la pantalla contra un robot en reposo
  producía una queja antes de que nadie tocara nada. Elegirlo por lo que diga la luz sería peor: la
  luz apagada es el reposo de los 16, así que quien midiera el **suelo** entraría en emisión sin
  enterarse. **El modo afirma qué hay debajo del robot, y eso no se deduce.**
- **Verde a cero devuelve `null`, no un cociente.** La casilla «refleja + luz apagada» dio cero
  absoluto doce veces, todas con `success=true`. Y `NaN > 1` es `false`, así que un clasificador
  descuidado lo habría llamado **verde**.
- **El discriminante es `success`, no `claro`.** 42 cuentas son una lectura excelente en emisión y
  oscuridad en reflejo: el umbral depende del modo y no se copia.

### 📝 Y un defecto que me vi en la captura

Al añadir el selector quedaron **dos controles mandando sobre la misma luz** — el nuevo y el botón
viejo—: pulsar uno dejaba al otro describiendo algo que ya no era cierto. Se quitó el viejo. El
testigo de `color_activo` **no se pierde**: pasa de esperarse una vez tras pulsar a pintarse
continuamente, lo que además cubre el apagado automático a los 15 min — que ocurre sin que nadie
pulse nada y que un testigo de una sola vez no habría visto nunca.

**567 pruebas** (eran 546), contrato 14 · 3 · 12 coincidiendo con el robot, y las 42 guardias sobre
pantallas reales en verde.

---

## 2026-08-09 — **La PSK cerrada, y el DÉCIMO falso positivo del verificador**

Uno de los cinco bloqueantes de la Fase 5, cerrado por el usuario con una línea de `/etc/fstab`.

```
antes    -rwxr-xr-x  root:root  /boot/firmware/red.txt      ← lo leía cualquiera
después  drwx------  root:root  /boot/firmware              ← ni se puede entrar
         fmask=0177 · dmask=0077
```

### 🔴 `mount -o remount` tampoco lo aplica: devuelve 0 y no hace nada

Tras `systemctl daemon-reload` y `mount -o remount /boot/firmware`, `findmnt` **seguía dando
`fmask=0022`**. Hizo falta **reiniciar**. Es la misma forma que el `chmod` que este proyecto ya
tenía documentado, sobre el mismo fichero, con otra orden: **dos maneras distintas de dejar el
problema abierto con aspecto de resuelto.**

📌 Y lo único que lo detectó fue mirar el efecto —`ls -l`— en vez del código de salida. Por tercera
vez en dos días.

### 🔴🔴 Y arreglarlo rompió el verificador, el mismo día que el noveno

Al cerrar el directorio, `[[ -f /boot/firmware/red.txt ]]` da falso, y el guion decía:

```
  ! no hay /boot/firmware/robot_id.txt
  ! no hay /boot/firmware/red.txt: la red se queda en DHCP
```

**Los dos ficheros están ahí.** Es exactamente la lección del noveno —**«no puedo verlo» no es «no
está»**— reapareciendo en el otro extremo del sistema, en el mismo día, por la misma causa.

🔴 **Y aquí es peor que en el caso de polkit:** mandaba a **recrear el fichero que lleva la PSK**.
Rehacerlo mal deja al robot sin red.

✅ Arreglado con un guardia `BOOT_LEGIBLE` que distingue los dos casos — y en éste **«no puedo
verlo» ES la prueba de que está bien**, así que se reporta como ✅: *«la PSK está protegida»*.

📌 **Le pasará a los 16 en cuanto la imagen dorada lleve el `fmask`**, que es justo lo que se
quiere. Por eso se arregló en el verificador y no con un caso especial.

### 🔴 Y al escalarlo apareció la divergencia que la regla del proyecto existe para impedir

**Nada en el repositorio aplicaba el `fmask`.** `fase_1_higiene_so.sh` toca `/etc/fstab` —para el
`noatime` de la raíz— pero nunca la línea de `/boot/firmware`. Consecuencia:

```
  la imagen dorada        SÍ lo lleva      (un dd copia el fstab)
  provision.sh desde 0    NO lo aplicaba   → PSK expuesta
```

Y la regla del proyecto es explícita: **«la imagen dorada es el atajo; `provision.sh` es la verdad.
Si divergen, gana el script.»** Un robot reprovisionado saldría con la PSK expuesta mientras los
clonados no.

✅ **Añadido a `fase_1_higiene_so.sh`** (paso 8bis/9), con el mismo patrón que el `noatime`:
idempotente —salta si ya está—, y **comprueba `findmnt --verify` antes de que un reinicio estrene
el fstab**, porque un `fstab` roto deja la Pi sin arrancar y esta máquina es headless.

✅ **Y el verificador comprueba ahora el `fstab` en sí**, no solo el efecto. Hace falta: un robot
**sin** la máscara tiene el directorio atravesable, así que el guardia `BOOT_LEGIBLE` lo daría por
legible y la comprobación se iría por otro camino. Probado contra un `fstab` con y sin la máscara:
discrimina en los dos sentidos. **149 comprobaciones.**

### Y un pendiente que pedía algo ya hecho

`aceptacion_nucleo.py` listaba «la credencial `sphero` **sin rotar**» entre los bloqueantes. **Se
rotó el 2026-08-04**, junto con la PSK, y se archivó `Atriz_web_server` — **eso** es lo que cierra
la exposición. Lo que sigue abierto es **higiene**: el histórico de git, que además **no llega a
los forks que ya existan**, así que purgar nunca habría bastado solo.

📌 **Un guion que sigue pidiendo algo hecho gasta la credibilidad de los que sí faltan.**

---

## 2026-08-08 (11) — **Los `ABORTADO` eran mentira: el robot había llegado las tres veces**

Réplica de la navegación (n=3) que destapó **dos fallos de Nav2**, y el segundo llevaba desde el
principio del proyecto.

### 🔴 `default_server_timeout: 20` — veinte milisegundos para el acuse

```
  22:18:57  Received a goal, begin computing control effort   ← el controlador SÍ lo recibió
  22:18:57  Timed out while waiting for action server to acknowledge … follow_path
  22:18:57  Aborting handle · Goal failed
  22:19:07  Reached the goal!                                 ← DIEZ SEGUNDOS DESPUÉS
```

**`bt_navigator` se rinde esperando el acuse mientras `controller_server` conduce.** El robot
recorrió 67 cm y llegó, con la acción marcada como fallida.

📌 **Reinterpreta las tres tandas del 07 y 08 dadas por fallidas: el robot había navegado bien las
tres.** Se atribuyeron a saturación de la Pi —real y medida— pero **la causa próxima era el plazo**.
20 ms está muy por debajo del ruido de planificación de esta máquina (326 ms al reiniciar el
driver). ✅ Subido a **1000 ms** y verificado por efecto.

### 🔴 Y `/initialpose` se rechazó en las DIEZ tandas de la historia del proyecto

`Failed to transform initial pose in time (extrapolation into the future)` — el sello iba **69 ms**
por delante de lo último que tenía TF. **El banco creía fijar la pose y no la fijaba nunca.**

📌 **El daño fue menor y hay que decir por qué:** AMCL arranca en (0,0) por su `set_initial_pose`, y
el journal confirma `Begin navigating from current location (-0,02 · 0,00)`. Las evidencias 83 y 84
se sostienen. ✅ Arreglado con sello `0`.

### La réplica, con n=3

```
                        al objetivo  ¿<10cm?   odom   AMCL   carga
  mapa viejo (ev. 83)      41,3 cm    🔴 NO     1,5   45,0     —
  tanda 1                   6,1 cm    ✅ SÍ     4,2    8,9    5,3
  tanda 2                  11,8 cm    🔴 NO     2,2   15,2    6,5
  tanda 3                  11,3 cm    🔴 NO     0,3    8,2    9,0
```

🔴 **Dos de tres fuera de tolerancia**: la retirada de «el *llegué* de Nav2 ya es cierto» queda
confirmada, y la cifra honesta es **~10-12 cm**.
✅ **La odometría ya no admite discusión: 1,5 · 4,2 · 2,2 · 0,3 cm**, cuatro tandas, dos mapas y
cargas de 5 a 9.

### 📝 Y dos confusores avisados ANTES que no se materializaron

La tanda se tomó con **batería 7,25 V (28 %)** y **carga 9,0** — las peores condiciones de las
cuatro. Se avisó al usuario antes de medir, él decidió tirar, y quedan escritos. **Dieron el mejor
resultado de odometría de las cuatro (0,3 cm).**

📌 De regalo: **con la CPU al doble de carga la odometría no se degrada.** Y la forma correcta de
manejar un confusor conocido: **decirlo antes, decidir con quien tiene la responsabilidad, y
escribirlo pase lo que pase.** Lo que no vale es medir primero y buscar la explicación después.

---

## 2026-08-08 (10) — **El disparador de `girar()`: siete hipótesis fuera, y NO reproducido**

Sesión dedicada a aislar el fallo intermitente del apartado 1 de la evidencia 85. **Resultado: un
negativo**, y se escribe como tal.

### El instrumento que faltaba

Todo lo anterior medía `/odom` **desde otro proceso**. Un topic puede estar sano en el cable y
llegar tarde a un proceso concreto — y el guardia que abortó mira lo que llega a **su** proceso.
`mediciones_banco/medir_hambre_del_ejecutor.py` mide el hueco **como lo ve el proceso del alumno**,
sondeando a 20 Hz, que es el ritmo del bucle de `girar()`.

### Siete caminos cerrados con medida

```
  1 huecos reales de /odom (otro proceso)      n=3    78-81 ms        ✅ no
  2 sellos a cero o repetidos               166/166   distintos       ✅ no
  3 el arranque del LIDAR                            ya giraba        ✅ no
  4 /scan compitiendo en el ejecutor        45+45 s   108,2 vs 107,8  ✅ no
  5 la ventana de ARRANQUE (procesos nuevos)   10     racha 1         ✅ no
  6 el robot MOVIÉNDOSE (puerto serie)          8     racha 1         ✅ no
  7 un competidor a 500 Hz (el propio arnés)    6     racha 1         ✅ no
  + soak de 5 min   4976 muestras · peor 104,8 ms · racha 1
```

🔴 **NO REPRODUCIDO NI UNA VEZ.** La racha nunca pasó de **1** (~100 ms) contra un umbral de
**250**. No llegué ni a 2,5× del disparador.

### Por qué un negativo se documenta

- **Dice dónde no buscar.** Siete caminos cerrados con medida, no con razonamiento.
- **Acota el fenómeno.** En régimen normal el guardia no ve más de UNA vuelta sin sello nuevo:
  llegar a cinco exige un parón de ~300 ms, que es **una anomalía, no la cola de una
  distribución**.
- **Mide el margen del arreglo con datos propios:** 2,0 s son **20 veces** el peor caso que soy
  capaz de producir a propósito.

⚠️ **Lo que NO puedo decir:** que el arreglo esté verificado contra el disparador real. No lo está
— no sé cuál es. **Un fallo que aparece 1 de 4 veces y luego no aparece en 32 no está entendido.**

⏳ Queda sin descartar: el estado de descubrimiento DDS de aquel día (venía de tres tandas de
navegación, con participantes muertos que el daemon conserva) y una pausa del recolector de basura.
Las dos son difíciles de provocar a voluntad.

📝 Y una hipótesis mía que caía por su propio peso y aun así había que medir: **`/scan` compitiendo
en el mismo `SingleThreadedExecutor`**. `atriz.py` se suscribe a `/scan` (12 Hz, ~250 rangos) **en
todas las prácticas, incluidas las que no lo usan**, y las devoluciones se atienden en serie.
Parecía la explicación. **108,2 ms contra 107,8: no estorba nada.**

---

## 2026-08-08 (9) — **Auditoría de `atriz-lab` desde el robot, y el hueco era mío**

Encargo del usuario: auditar la web *«desde tu punto de vista, que conoces todo el
funcionamiento»*. El ángulo elegido: **no auditar TypeScript** —eso lo hacen sus 578 pruebas— sino
**cruzar la aplicación contra las trampas que este proyecto pagó midiendo en el robot**, que no se
ven leyendo su código porque viven al otro lado del cable.

### ✅ Las once, cubiertas

`/cmd_vel` rechazado con excepción y dos pruebas · `qos` que **ni se acepta como parámetro** ·
`throttle_rate` descartado con el razonamiento bueno · **cero dependencia de `/rosapi`** ·
`ranges.length` sin asumir · umbrales de silencio separados con prueba que impide unificarlos ·
plazo de conexión con sus dos paredes · `result`/`success` distinguidos · `/ambient_light`
prohibido · voltios en vez de porcentaje · `hayLectura = success` en el modo emisión.

**Y el contrato coincide exactamente**, leído con AST del `robot.launch.py` contra `contrato.ts`:
`14 · 3 · 12 · 1`, y los 17 tipos.

📌 **La postura de seguridad es honesta**, que era mi mayor sospecha: `testigo.ts` dice con todas
las letras que protege **la interfaz y no el robot**, y que cualquiera del aula puede abrir el
WebSocket desde la consola. Un inicio de sesión que se presentara como control de acceso sin serlo
sería el estado engañoso que este proyecto lleva meses quitando.

### 🔴 Y el único hueco serio era del ROBOT

`EstadoNavegacion` daba del mapa **un solo booleano**. Y un mapa que no es del sitio hace que Nav2
declare éxito **a 41,3 cm sin ningún otro síntoma**. **La única defensa es que una persona mire la
fecha — y la web, que es quien tiene delante a la persona, no podía.**

✅ **Arreglado el mismo día** (13 campos), y verificado en el topic:

```
  mapa_nombre  'cuarto3.yaml'
  mapa_edad_s  104976 s = 1,22 días     ← contra un fichero de hace ~29 h
```

⚠️ **Con su limitación escrita, no escondida:** es el `mtime` del **fichero**, no «cuándo se mapeó
ese espacio». Copiar un mapa viejo lo rejuvenece. Por eso va **el nombre al lado**: el robot da los
dos datos y **la persona decide**.

📝 **La lección de la auditoría:** buscaba fallos en la web y encontré uno mío. **Auditar el
trabajo de otro es también auditar la interfaz que le das** — y llevaba semanas escribiendo que un
mapa rancio es el fallo más peligroso del sistema sin darme cuenta de que **no le estaba dando a
nadie con qué detectarlo**.

⚠️ **Lo que NO se auditó, dicho:** no se ejecutó nada de la web, ni el diseño visual, ni el
rendimiento con 16 clientes reales — eso último es del aula.

---

## 2026-08-08 (8) — **El modo emisión, verificado por rosbridge (que es el camino de la web)**

Todo lo de la evidencia 86 estaba medido **por ROS**, con un cliente rclpy en el propio robot. La
web habla **rosbridge por WebSocket**, y en este proyecto «funciona por ROS» **no implica**
«funciona por la web»: `/start_scan` parecía tardar 4,6-6,5 s medido con `ros2 service call` y por
WebSocket son 1,4-2,1.

```
  /enable_color(true)    result=True · success=True     129 ms
  MODO REFLEJO           8/8 respuestas · mediana  43 ms · máx 113 ms
  /enable_color(false)   result=True · success=True     133 ms
  MODO EMISIÓN           8/8 respuestas · mediana  33 ms · máx  63 ms
```

✅ **Los dos modos funcionan enteros por rosbridge**, y el mensaje nuevo del driver llega intacto al
cliente. Con 33-43 ms de mediana cabe un lazo a 10 Hz de sobra; el sobrecoste del WebSocket sobre
la llamada nativa (20,6-20,8 ms) es de **~15-20 ms**.

🔴 **Y una distinción que la pantalla necesita:** `result` es de **rosbridge** («¿pude llamar?») y
`success` es del **driver** («¿contestó el sensor?»). Un `result=true` con `success=false` es un
diagnóstico completamente distinto de un timeout. Y **la lista blanca deniega en silencio**.

### 🔴 Pero la primera ejecución dijo que el servicio no contestaba

*«/enable_color no contestó en 8145 ms — ¿está en la lista blanca?»*. Estuve a punto de escribir
que rosbridge lo bloqueaba.

**El fallo era mío.** `recibir()` de `probar_rosbridge.py` devuelve una **tupla `(datos, opcode)`**,
no una cadena. Mi código hacía `json.loads(r)` directamente: reventaba con cada mensaje y **mi
propio `except ... continue` los tiraba en silencio**. Descartaba todas las respuestas.

📌 **Lo destapó comparar contra `probar_rosbridge.py`, que ya estaba verificado** — no releer mi
código. **Valida el instrumento contra uno bueno antes de acusar a lo medido.**

📝 Van **tres veces en esta sesión** que mi propio instrumento miente: el arnés gritando «no se
movió» sobre una práctica que no debe moverse, la medición que dio huecos de 253 ms donde había 81,
y esto. La cuenta del proyecto va por **ocho**.

---

## 2026-08-08 (7) — **El peor hueco de `/odom` no es el de régimen permanente**

Salió de una comprobación de salud **rutinaria** tras reiniciar el driver para desplegar otro
cambio. No se buscaba.

```
  régimen permanente   σ 2,0-2,5 ms  ·  peor hueco   78-81 ms    (n=3, 60 s cada una)
  recién reiniciado    σ  16-19 ms   ·  peor hueco  325,7 ms     (20 s tras arrancar)
```

🔴 **Dos consecuencias, y van en sentidos opuestos:**

- **Refuerza el arreglo de `girar()` más de lo que se sabía.** El umbral viejo eran 250 ms y acaba
  de medirse un hueco de **326**: no es que tuviera poco margen, **estaba por debajo de un hueco
  que ocurre de verdad**. Un `girar()` en los primeros segundos tras arrancar el driver **abortaba
  por construcción**.
- **Y desmiente mi propio «12× de margen»**, escrito unas horas antes. Era cierto **solo en
  régimen permanente**; contra el transitorio, 1,0 s dejaba **3×** — el margen que yo mismo había
  declarado insuficiente tres líneas más abajo.

✅ **`SILENCIO_ODOM_S` sube de 1,0 a 2,0 s.** 6× sobre el peor transitorio y 25× sobre el
permanente. Y la asimetría juega a favor: un falso aborto deja al alumno con el robot a 5° y sin
explicación; un aborto un segundo más tarde sobre una odometría muerta de verdad no cuesta nada.

✅ **Un test nuevo lo fija contra el caso PEOR MEDIDO**, no contra el cómodo (97 → 98). Y al subir
el umbral **falló otro test** —comprobaba un `1.5` absoluto—, que hizo exactamente su trabajo:
avisar de que el cambio movía el comportamiento. Se ató a la constante, porque **un número mágico
al lado de la constante que prueba se queda rancio solo**. Con el umbral viejo ahora **fallan dos**.

📝 **La lección: una medida tomada en un solo régimen no caracteriza el fenómeno.** El proyecto ya
lo tenía escrito para otro caso —«un umbral en milisegundos no es transferible entre topics de
ritmos distintos»—. Aquí no cambió el topic: **cambió el momento**.

⏳ **Y estrecha, sin cerrar, el disparador del fallo original.** El `girar()` que abortó no fue
tras un reinicio (el driver llevaba ~1 h en pie), así que este transitorio **no lo explica**. Pero
demuestra que existen huecos de 326 ms, y `atriz.py` arranca el LIDAR al conectar. **Hipótesis, no
medida.**

---

## 2026-08-08 (6) — **El sensor de color tiene DOS modos, y el segundo estaba sin nombre**

Encargo del usuario tras la evidencia 86: preparar la web para ofrecer **una segunda opción del
sensor — medir superficies luminosas, sin encender el LED del robot**.

### ✅ No hace falta ningún servicio nuevo

Las dos piezas ya existen, están en la lista blanca de rosbridge y están verificadas:
`/enable_color` (`SetBool`) elige el modo y `/get_rgbc_sensor_values` lee los cuatro canales. **La
única diferencia entre los dos modos es el estado de la luz.** Eso hace la pantalla muy simple: un
interruptor y el mismo lazo de lectura.

### 🔴 Pero al preparar el contrato salió lo que decide el diseño

```
  luz ENCENDIDA   topic /color -> 40 mensajes, 40 no-cero
  luz APAGADA     topic /color -> 39 mensajes,  0 no-cero     ← ceros
                  servicio     -> lecturas REALES
```

**En modo emisión el topic `/color` no sirve.** No es un fallo: `/color` sale del **streaming** del
RVR y el streaming se apaga con la detección; el servicio **consulta**, así que sigue dando datos.
Y el topic **no trae `claro`** de todas formas.

### 🔴 Y un mensaje del driver que afirmaba de más

Decía *«el sensor de color está APAGADO: estos valores son oscuridad»*. **Falso cuando la
superficie emite luz propia** — que ahora es un modo legítimo y medido. El driver no puede
distinguir «negro» de «pantalla apagada» de «no hay nada debajo». Reescrito para decir qué hacer en
cada caso **sin asegurar cuál es**.

📌 *Un aviso que asegura de más sobre lo que no puede saber es peor que no avisar* — la misma
familia que «`Failed to get scan`» con el barrido apagado a propósito.

### Documento nuevo: `03_operacion/SENSOR_COLOR.md`

Un solo sitio con lo que hasta hoy estaba repartido o en un chat: **qué es cada canal** (por qué
`claro` no lleva filtro y qué mide de verdad), **por qué no tiene unidades**, **por qué el color se
juzga por proporciones**, **los dos modos con su tabla medida**, el **contrato para la web** —
incluido lo que la pantalla NO debe hacer— y lo que **no se puede prometer**.

🔴 Tres avisos que la web necesita y que no son obvios:
- **`color_activo = false` no es «sensor apagado»**: en modo emisión es el estado correcto.
- **`claro = 0` no es un fallo**: el discriminante es `success`, no el valor.
- **Los mismos R/G/B significan cosas distintas** según el modo. No pintar un color sin decir de
  cuál viene.

### 📝 Y un susto que fue un error de método mío

Al medir el topic contra el servicio, con la luz apagada salió `R0 G0 B0 claro 0` — cuando diez
minutos antes daba 133/26/4/150. Pareció que la evidencia 86 se caía.

🔴 **Mi medición no miraba el campo `success`.** Sin él, «no hay nada que ver» y «el sensor no
contestó» son el mismo `(0,0,0,0)` — que es **exactamente** el fallo que `atriz.py` documenta en su
`color()`. Al mirarlo: `success=True`. Y al leer el código, el handler **consulta al RVR pase lo
que pase**. Los ceros eran una lectura real de que ya no había pantalla debajo — **lo dijo el
usuario antes que yo**: *«tal vez es porque no le estoy poniendo el móvil»*.

📌 **La lección: al replicar una medida propia, replica también sus condiciones.** Cambié la
superficie sin darme cuenta y estuve a punto de retirar un resultado correcto.

### Y de camino, dos limpiezas

- **`atriz.py` y el aviso que ve el alumno en TODAS las prácticas** decían «sin luz no hay
  lectura». Ahora distinguen reflejo de emisión.
- **Workspaces parásitos en `src/`**, del 2026-08-07 y en `.gitignore`, así que llevaban 24 h sin
  que nadie los viera. Los cazó el guardia de `compilar.sh`. La imagen dorada ya los borraba, así
  que la flota estaba a salvo.

---

## 2026-08-08 (5) — **Las nueve prácticas corridas, y un sensor que hace lo contrario de lo que creíamos**

### La pasada de prácticas, completa salvo el seguidor de línea

| práctica | medido por el arnés | qué demuestra |
|---|---|---|
| **01** avanzar | 59,5 cm de 60 | la distancia sale **si nadie está cerca** (ver la entrada (3)) |
| **02** girar | 7 giros: 89,7 – 90,8° | el lazo cerrado, tras arreglar el guardián |
| **03** cuadrado | **cierra a 11 cm** en 2,4 m · esquinas 90,6 · 90,3 · 89,9 · 90,0 | el error no se acumula |
| **04** giro preciso | abierto **1,5°** · cerrado **0,1°** | y **disparó su propia lección**: el giro cruzó el salto de ±180° y la práctica lo enseñó en vivo (`-268,5` contra `91,5`) |
| **05** sensor color | estable, **sin moverse** | lectura continua sobre una superficie |
| **10** patrulla | 155 cm · detectó algo a 0,36 m y **giró sola** | el lazo sentir-actuar con el LIDAR |
| **11** parar sobre negro | detectó a **claro=396** tras 46,5 cm | el lazo sentir-actuar con el color |
| **90** plantilla | 34,1 cm y 89,4° | el esqueleto que copia el alumno arranca |

⏳ **Falta el seguidor de línea**: hace falta cinta que el usuario no tiene.

⚠️ **Y un margen más estrecho de lo que promete el guion:** la 11 detectó con `claro=396` contra un
umbral de **400** — cuatro cuentas. El comentario dice *«400 se queda muy por debajo del suelo
(1275)»*, pero **aquí el suelo dio ~950**. El margen real fue 2,4× y no 3,2×. Depende de la luz de
la habitación y del suelo concreto; conviene saberlo antes del aula.

🔴 **Y mi propio arnés cantó un falso positivo:** dijo «EL ROBOT NO SE MOVIÓ» sobre la práctica 5,
**que no debe moverse**. Arreglado con `--no-mueve` y `--en-bucle` — y el caso contrario (una
práctica de sensores que SÍ mueva el robot) ahora también se detecta. *Un instrumento que grita
sobre lo normal se acaba ignorando*, que es lo que este proyecto lleva escrito nueve veces del
verificador y ahora una del arnés.

### 🔴 El RGBC sobre una superficie que EMITE luz: hay que APAGAR su LED

Lo preguntó el usuario —¿serviría para medir un piso de baldosas LED?— con la sospecha correcta ya
puesta: el vidrio reflejaría el blanco del propio sensor. **Es exactamente el obstáculo, y la
solución es quitar la iluminación, no mejorarla.**

```
                 LED del sensor OFF          LED del sensor ON
                R/G     B/G    claro       R/G     B/G    claro
  ROJO         5.12    0.15      150      0.66    0.49     1238
  VERDE        0.17    0.20      387      0.37    0.40     1467
  AZUL         0.11    4.57      190      0.46    0.73     1230
```

✅ Apagado, los tres se separan por un factor **25-30**. 🔴 Encendido, los seis cocientes viven
entre 0,37 y 0,73, y **el rojo da `R/G = 0,66` — menos rojo que verde sobre una pantalla roja a
tope**. No pierde precisión: engaña.

📌 **Un control interno que salió gratis, y vale más que el resultado.** El usuario preguntó si el
LED se había encendido de verdad, y la respuesta no está en el `success` del servicio: el LED
aportó **+1088, +1080 y +1040** de `claro` en los tres colores — 4 % de dispersión. Tiene que ser
así, porque es su reflejo sobre el mismo vidrio y **no depende de lo que muestre la pantalla**.

⚠️ **No se transfiere a una baldosa real:** saturación (aquí el máximo fue 387 contra 2288 del
blanco reflectante) y parpadeo PWM (aquí 2-4 cuentas; una baldosa más lenta podría batir contra la
integración). Todo lo demás del proyecto asume que el sensor necesita su luz — cierto **para
reflejar**, falso **para emitir**. Evidencia 86.

---

## 2026-08-08 (4) — **El noveno falso positivo del verificador, y la regla que sí estaba**

Al alinear la sesión con la flota, el verificador declaró un **FALLO**:

```
✗ /etc/polkit-1/rules.d/49-atriz-unidades.rules NO está instalado,
  y sí está en el repositorio
```

Y era mentira. **La regla estaba puesta y funcionando.**

### 🔴 «No puedo verlo» no es «no está»

```
drwxr-x--- 2 root polkitd  /etc/polkit-1/rules.d
```

`sphero` **no puede atravesar ese directorio**, así que `[[ -e fichero ]]` da falso **exista o no
el fichero**. Y el efecto demostraba que sí existía — el permiso por defecto de polkit para
`manage-units` es `auth_admin` en los tres niveles, y sin embargo:

```
systemctl start atriz-slam         ->  0                                   ✅
systemctl stop  atriz-slam         ->  0                                   ✅
systemctl reset-failed atriz-slam  ->  «Interactive authentication required» 🔴
```

**Esa asimetría solo la puede producir una lista blanca por verbo**, que es exactamente el diseño
de `49-atriz-unidades.rules` (`action.lookup("verb")`).

📌 Confundir las dos cosas manda a reinstalar lo que ya funciona — o peor, a **ignorar al
verificador**, que es lo que este proyecto lleva escrito ocho veces que no puede permitirse.

### Lo que se arregla, y no es solo polkit

- **Genérico:** si el directorio de destino no es atravesable, el manifiesto dice **«NO SE PUEDE
  COMPROBAR sin privilegio»** en vez de «no está». Y si el fichero existe pero no se puede leer,
  no se hace `cmp` — que habría dicho «DIVERGE», la misma mentira con otro signo.
- **Por efecto:** se comprueba que `sphero` pueda mandar `stop` a una unidad atriz **que ya está
  parada** — operación nula, no toca el robot, pero pasa por el mismo control de acceso. Y si la
  unidad estuviera activa **no se toca**: un verificador jamás puede parar la navegación de una
  clase en curso.
- 🔴 **Con CONTROL NEGATIVO**, sin el cual lo anterior no probaría nada: `reset-failed` **tiene que
  seguir denegado**. Si pasara, no sería que la regla funciona mejor — sería que `sphero` tiene
  permiso **general** sobre systemd, y **cualquiera que llegue por rosbridge lo hereda**.

### Por qué importa para la flota

De esa autorización depende que **la web pueda arrancar la navegación**. Si falta, `/pedir_nav`
acepta la petición y la unidad no arranca nunca — el peor modo de fallo, porque **el botón
responde bien**. Antes esto no se comprobaba de ninguna manera fiable en los 16 robots.

📝 **Y una mía, para que conste:** commiteé el cambio anterior **antes de mirar el resultado del
verificador** — filtré su salida con un `grep` que solo enseñaba el encabezado de FALLOS. El fallo
se descubrió al leer la línea siguiente. *Comprueba el efecto* incluye leer lo que imprime.

150 comprobaciones, 0 fallos, 8 avisos conocidos.

---

## 2026-08-08 (3) — **Las prácticas, con el robot moviéndose. Tres fallos.**

El pendiente más viejo del material docente: las diez prácticas estaban escritas, revisadas y con
91 tests, y **nunca se habían ejecutado con el robot en movimiento**. Se corrieron las que no
necesitan una línea pintada. Salieron tres fallos, y ninguno es visible leyendo el código.

### 🔴 `girar()` abortaba sobre un robot sano — y salía con código 0

```
pide girar(90)  ->  «Giro 5.5 grados de verdad»  ·  salida 0
AVISO: /odom no se actualiza hace ~0.25 s. Odometría perdida o desconectada.
```

Con `/odom` a **16,54 Hz, σ 2,5 ms, peor hueco 80,9 ms** — perfecto. La causa:

```python
MAX_SIN_CAMBIO = 5   # ~0.25 s a 20 Hz     <- cuenta VUELTAS, y SUPONE el ritmo
```

Mide en la unidad equivocada, el margen era 3× y no 10, y **al disparar mentía sobre la causa**.
🔴 **El modo de fallo es el peor posible: no falla, miente bajito** — termina, imprime y devuelve
0 con el robot a 5°. Reproducido **1 de 4**.

✅ Arreglado: tiempo de reloj desde la última muestra nueva, **1,0 s** = 12× el peor hueco medido.
El criterio se extrajo a `odom_rancia()` — **el fallo era justo que no se podía comprobar en
ningún sitio** — con **6 tests que discriminan** (91 → 97; con el umbral viejo, fallan). 4/4 en el
robot, ⚠️ que **no basta** para un fallo intermitente: lo que sostiene el arreglo es estructural.

⏳ El disparador **no se aisló**, y se descartaron tres hipótesis midiendo: huecos reales de
`/odom` (81 ms, no), sellos repetidos o a cero (166 de 166 distintos), y el arranque del LIDAR (en
el fallo **ya estaba girando**; los tres buenos lo arrancaron de cero — al revés).

### 🔴 `avanzar(0.20, 3)` no significa 60 cm

**26,4 cm** una vez, **59,5** la siguiente, sin tocar nada. Lo explicó el usuario mirando el robot
—«paró porque encontró un obstáculo con el LIDAR»— y el journal lo confirmó: dos de los tres
segundos al 40 % por el polígono `Precaucion`. Que resultó ser **40 cm de ancho**: cualquier cosa
a menos de ~9 cm de un costado frena el robot, aunque se aleje de ella.

📌 No es un fallo — es la capa de seguridad funcionando. Pero **el alumno pide 60 cm, obtiene 26 y
no recibe ningún mensaje**, y la práctica 3 dibuja un cuadrado.

### 🔴 La Pi no tiene RTC, y eso invalidó una comprobación de esta misma sesión

```
arranque de la Pi       2026-08-08 12:07:53
driver, según systemd   2026-08-07 16:40:39   <- 19,5 h ANTES de arrancar
NTP sincronizó          2026-08-08 12:08:11   <- 18 s después
```

Se había comprobado A11 con `journalctl --since "-6h"`, que **excluye justo el arranque**, que es
cuando ocurre el fenómeno. El resultado (0 ocurrencias) salió correcto **por casualidad**.
📌 **Para cualquier cosa del arranque, `journalctl -b`.** Y `ExecMainStartTimestamp` no sirve para
saber cuánto lleva vivo un servicio. Les pasa a los 16 robots en cada arranque.

### Lo que sí funcionó, y un instrumento nuevo

```
práctica 1   avanzar(0.20, 3)  ->  59,5 cm  (esperado 60)                    ✅
práctica 2   girar(90) × 7     ->  89,7 · 90,1 · 90,2 · 90,2 · 90,5 · 90,6 · 90,8°  ✅
```

Y las dos fuentes independientes coinciden: la práctica dice «90.2 grados de verdad» y el arnés,
midiendo `/odom` desde **otro proceso**, dice +90,2°.

📌 El arnés (`mediciones_banco/correr_practica.py`) hizo falta desde la primera práctica: imprimió
«Avanzando... Listo.» y salió con 0, que no dice nada. **Comprueba el efecto, no el código de
salida** — otra vez.

📝 **La lección: los tres fallos son invisibles desde el código.** Lo que los sacó fue ejecutar y
medir — un arnés externo, **el ojo del usuario**, y mirar por qué un número no cuadraba en vez de
redondearlo. Y **dos hipótesis mías cayeron**, las dos plausibles y las dos falsas.

⏳ Quedan las prácticas 3, 4, 10, 11 y 90 (falta espacio despejado) y el seguidor de línea (hace
falta cinta).

---

## 2026-08-08 (2) — **La prueba de aceptación no podía ver el fallo de 41 cm**

Al alinear el repositorio con la evidencia 84 apareció algo que no se buscaba, y es lo más
importante del día para la flota.

### 🔴 «Nav2, error final 9-10 cm» nunca fue una medida

El manual lo decía él solo sin darse cuenta:

> *«El error coincide con la `xy_goal_tolerance: 0.10` configurada — **no es casualidad**: el
> controlador para al entrar en tolerancia.»*

Eso es **circular**. El número sale de la pose que el propio sistema se atribuye, y el controlador
para cuando **cree** estar dentro de 10 cm: por construcción da ~10 cm, esté el robot donde esté.
La frase describía su propia circularidad **y se leyó durante ocho días como una confirmación**.

### 🔴🔴 Y la prueba de aceptación heredaba el defecto

`prueba_aceptacion.py` calcula el error con `a.pos_mapa()`, que es **la pose de AMCL**. Con los
datos reales de la evidencia 83:

```
  lo que habría reportado la aceptación    6,8 cm   → PASA ✅
  banda configurada                     [0, 15] cm
  donde estaba el robot de verdad         41,3 cm   🔴
```

🔴 **Es la prueba que decide si un robot de la flota está listo, y no podía detectar el peor fallo
de navegación medido en este proyecto.** Los 16 robots la habrían pasado.

📌 **No se cambia la banda ni se convierte en FALLO**, y es deliberado: sería fingir que el número
mide algo que no mide. Lo que se hace es **decirlo donde se lee** — la prueba ahora reporta
`error final SEGUN AMCL`, avisa por pantalla con el caso de los 41,3 cm, y remite a
`comparar_con_cinta.py`, que necesita **dos** distancias.

### Alineado en siete documentos más

`MANUAL 11.7` (con la tabla original conservada y el aviso al lado), el índice del manual,
`CLAUDE.md`, `TRASPASO.md`, `README.md`, `INSTALACION.md` ×2 y `PRUEBA_ACEPTACION.md`.

📝 **La lección, que es de segundo orden y la que vale:** la evidencia 84 no solo corrigió un
número — **invalidó el método con el que se habían tomado todos los números anteriores de esa
familia**. Corregir el dato y dejar el instrumento en pie habría dejado el fallo entero en su
sitio, listo para volver con la siguiente medición.

⚠️ **Consecuencia para la flota:** la prueba de aceptación **no puede aceptar ni rechazar la
precisión** de un robot. Verifica el mecanismo. La precisión de cada aula se comprueba **una vez,
con cinta**, al montarla.

---

## 2026-08-08 — **La réplica desmiente la mitad. Y era la mitad optimista.**

Se repitió la prueba de navegación sobre el mapa nuevo: misma marca `A` —el robot **encajado en
las cuatro esquinas**, así que también se reproduce el rumbo—, mismo `B`, mismo objetivo.

```
                         al objetivo   ¿dentro de 10 cm?   odom    AMCL   map→odom
  mapa viejo (ev. 83)       41,3 cm          🔴 NO          1,5    45,0     0,424
  mapa nuevo · tanda 1       6,1 cm          ✅ SÍ          4,2     8,9     0,028
  mapa nuevo · tanda 2      11,8 cm          🔴 NO          2,2    15,2     0,021
```

### 🔴 Lo que se retira

Ayer se escribió **«el "llegué" de Nav2 ya es cierto»**. **Con n=2 no se sostiene:** Nav2 declaró
`SUCCEEDED` a **11,8 cm** de un objetivo con **10 cm** de tolerancia. Sigue mintiendo — por 1,8 cm
en vez de por 31, pero mintiendo. Era **una tanda buena presentada como una propiedad**.

📝 Y es exactamente el error que ese mismo día se le señaló al PC por su *«el error al llegar es
de 8-10 cm, que es la tolerancia configurada»*. **Ver el error en el trabajo de otro no vacuna
contra cometerlo.** La advertencia «⏳ n=1, esto pide repetirse» estaba escrita **en el mismo
documento**, tres párrafos más abajo de la frase optimista. Escribirla no bastó.

### ✅ Lo que aguanta, y sale reforzado

- **El mapa era la causa dominante.** Sin discusión: AMCL de 45 cm a 8,9 y 15,2; la distancia al
  objetivo de 41,3 a 6,1 y 11,8. La hipótesis (a) de la evidencia 83 queda confirmada.
- **La odometría es excelente**, n=3 contra cinta entre los dos mapas: **1,5 · 4,2 · 2,2 cm**,
  dentro del ruido del propio instrumento (±1,7).
- 🔴 **AMCL es peor que la odometría por un factor de 4**: 8,9 y 15,2 contra 4,2 y 2,2. Con n=1
  esto se había escrito como «cerca del límite de la cinta»; la segunda tanda lo zanjó.

### 🔴 Lo que la web tiene que saber, y es la forma y no la cifra

**Nav2 dijo `SUCCEEDED` en las tres tandas: a 6,1, a 11,8 y a 41,3 cm.** El desenlace del objetivo
**no informa de la precisión**. Ninguna promesa que se le haga a un alumno puede apoyarse en él.
La cifra honesta sobre un mapa fresco es **~10-12 cm**, no la tolerancia de 10 que Nav2 anuncia.

### 📌 Una predicción escrita antes de medir, que acertó

La tanda 2 mostró el marco `map → odom` girando **8,5°** durante el recorrido, contra 1,1° en la
tanda 1. Se escribió **antes** de que el usuario midiera: *«si `BP` sale cerca de 1,20 la
odometría gana y ese giro es AMCL desviándose; si sale cerca de 1,31, era el robot el que se fue y
AMCL lo vio»*. Salió **1,18**. **Era AMCL.** El método discrimina.

⏳ **Lo que abre, y no se persigue hoy:** con la odometría a 2-4 cm y AMCL metiendo 9-15, la pose
sería mejor **sin** AMCL. Pero quitarlo cuesta el marco compartido entre los 16 robots, que es el
argumento entero para tenerlo. Se mide en el aula antes de tocar nada.

---

## 2026-08-07 (noche, 2) — **Revisión de la app entera: tres defectos que solo se ven mirando**

Se abrieron **las once rutas en un navegador de verdad**, con datos, y se midió lo que ninguna
prueba miraba. El disparador fue que la pantalla nueva de navegación traía tres defectos de esa
clase, y la pregunta obvia era si el resto de la aplicación tenía más. Tenía.

### Los tres reales, todos anteriores

| | dónde | por qué nadie lo vio |
|---|---|---|
| **once** cadenas con markdown sin renderizar | casi todas en «por qué no obedece» —la pantalla que lee un alumno cuyo robot no obedece— y una en diagnóstico | ese texto se pinta plano: un backtick sale como backtick. `tsc`, `eslint` y 538 pruebas verdes |
| `/api/sesion/quien` devolvía **401 en el estado normal** | las once rutas, en cada carga | el consumidor llevaba escrito «401 es la respuesta normal de quien no ha entrado: no es un error». El código lo sabía; el navegador no lee comentarios |
| «no llego» sin tilde | las **16 baldosas** del muro del profesor | dice «yo no llego» |

🔴 **El 401 es la forma exacta de un fallo que este proyecto ya pagó en el robot**: el nodo del
LIDAR escupía 25 errores por segundo en su estado *normal* y ahogaba cualquier error de verdad
—47 291 líneas de journal, el 99 % ruido—. Un error permanente en el sitio donde se buscan los
errores no es ruido inocente: **entrena a no mirar**. Ahora contesta `200` con `usuario: null`.
Las otras rutas conservan su 401 y no es incoherencia: `/usuarios` es una **puerta**, y esto es
una **pregunta** — «nadie» es una respuesta correcta.

📝 **Los once se encontraron en TRES tandas, y eso es lo interesante:** seis con el robot mudo,
tres más al darle datos al doble —la rama «el robot responde» no se alcanzaba antes—, y los dos
últimos con un barrido del fuente, porque viven en ramas que el doble no produce. **La cobertura
de una guardia que mira la pantalla depende del estado en que esté la pantalla.**

### Dos guardias nuevas

- **Markdown sin renderizar**, en la prueba que **abre el navegador** — no en un `grep` del
  fuente, donde un backtick es sintaxis legítima de plantilla y no se distingue.
- **`tokensQueNoPintan`**, en `estilo.ts` con 8 pruebas: un token que no existe o un triplete RGB
  sin `rgb()` son **CSS válido que no pinta nada**. Nació con **ocho falsos positivos** y por eso
  su código parece retorcido: hay que resolver la indirección y distinguir *asignar* de *pintar*.

### 🔴 Y seis falsas alarmas mías, todas comprobadas antes de reportarlas

Merecen listarse porque el coste de reportarlas habría sido mandar a arreglar lo que funciona:

- el **desajuste de hidratación** de `/diagnostico` era **mi propio servidor rancio**
- los **16 WebSocket fallidos** son correctos: el muro **debe** intentar los 16
- el «quitar» **cortado** del cuaderno es un `sr-only`, accesibilidad correcta
- los **anillos elípticos** del LIDAR eran mi ojo: el canvas mide 698×698 exactos y usa `arc()`
- «**PEDIDO 0,100 sin pulsar nada**» es deliberado y está razonado en el fuente
- tres palabras **sin tilde** eran nombres de fichero y de topic

⚠️ **Y el doble de rosbridge mintió**, que es lo de siempre: tenía mal los nombres de campo de
`/encoders` y `/motor_status` —el `.msg` dice `left_wheel_count` y `temperatura_izquierdo`—, así
que telemetría pintaba `—` **con datos llegando** y **parecía un fallo de la web**. Corregido
contra el `.msg`. Van **siete** veces que el instrumento miente en este proyecto.

---

## 2026-08-07 (noche) — **La web se alinea con el supervisor, y la captura destapa seis defectos**

Con el robot cargando, todo el trabajo es del lado web y **nada de esto está verificado contra
hardware**. El comprobador de contrato señalaba tres divergencias con el robot; se cierran y se
construye el control de SLAM y Nav2.

```
antes   🔴 LEER / TOPICS_LECTURA divergen · solo en el ROBOT: /estado_navegacion
        🔴 SERVICIOS divergen · solo en el ROBOT: /pedir_nav /pedir_slam
después ✅ LEER: 14 · ESCRIBIR: 3 · SERVICIOS: 12 · TIPOS: 5 de 5
```

El disparadero `toHaveLength(10)` cumplió su función: hizo fallar la prueba y obligó a clasificar
`/pedir_slam` y `/pedir_nav` en `confirmaEfecto()` **a mano**. Olvidarlo no habría dado error —
el fallback los clasifica solo y en silencio.

### Seis estados, no un interruptor

Es la decisión que sostiene la pantalla, y viene de un fallo ya medido en este proyecto: un
`slam_toolbox` que sobrevive a un reinicio del driver se queda con el búfer TF roto, `systemctl`
dice `active`, y **el mapa sale idéntico celda a celda tras mover el robot 80 cm**. Un booleano
pintaría verde justo ese caso. `CIEGO` y `MUDO` tienen casilla propia y **las dos son rojas, no
ámbar**: sin barrido el robot no conduce (0,0 cm contra 9,9 del control), que para el alumno es
indistinguible de una avería.

Y `slam_latcheado` evita una llamada de teléfono: con `StartLimitBurst=3`, **un solo arranque sin
mapa agota el presupuesto** y la unidad queda `failed`, de donde solo se sale con `reset-failed`
y privilegio. Sin ese campo, «no arrancó» y «bloqueado hasta que alguien entre por SSH» son el
mismo botón que no hace nada.

### 🔴 Un número de la pantalla, desmentido por el robot

`PanelNavegar` decía *«el error de posición medido al llegar es de 8-10 cm, que es la tolerancia
configurada»*. **Falso**, y lo desmintió la medición de la tarde: con el mapa rancio Nav2 dio el
objetivo por `SUCCEEDED` **a 41,3 cm**; remapeado, a 6,1. El error **no es una propiedad de Nav2**:
depende de lo viejo que sea el mapa, y Nav2 no puede saberlo porque se cree su localización. Era
una cifra de un día bueno presentada como una constante.

### 🔴🔴 Y la captura destapó lo que 538 pruebas verdes no veían

Se construyó un **rosbridge de mentira** (`atriz-lab/herramientas/`, sin dependencias) para
conducir la pantalla por estados que el robot tarda minutos en producir. Mirando el resultado:

| defecto | por qué no lo vio nadie |
|---|---|
| `--estado-bien` y `--estado-mal` **no existen**, y los tokens son tripletes RGB que hay que envolver en `rgb()` | la clase se genera y no pinta: **CIEGO y BLOQUEADO salían en negro**, los dos estados más graves indistinguibles de un texto normal |
| los backticks se pintaban **como caracteres** | ese texto es plano, no markdown ni JSX |
| la frase de estado se aplastaba contra el título | solo se ve en una captura |

Se añadió una guardia a `pantallas_reales.test.ts` — *ninguna marca de markdown sin renderizar* —
y **encontró cinco casos más, todos anteriores**, en «por qué no obedece» —la pantalla que lee un
alumno cuyo robot no obedece— y en diagnóstico, incluido un `**negrita**` sin renderizar.

📝 **Dos lecciones, y la segunda es la que vale:**
- Es la **segunda vez** que invento un token de color en este repositorio. El vocabulario se
  lee, no se recuerda.
- La guardia va en la prueba que **abre el navegador**, no en un `grep` del fuente: ahí un
  backtick es sintaxis legítima de plantilla y no se distingue. **Comprueba el efecto, no la
  intención** — otra vez.

🔴 **CORREGIDO DESDE EL ROBOT EL 2026-08-08 — esto ya era falso al escribirse.** Decía:

> ⏳ *«Pendiente y bloqueado por el hardware: el supervisor no ha corrido nunca. Hasta que esté
> instalado, `/pedir_slam` y `/pedir_nav` **no existen en el robot** y la llamada agota el plazo.
> Nada de esta entrada está verificado contra rvr-01.»*

**El supervisor lleva corriendo desde el 2026-08-07 y los dos servicios contestan.** Medido en
rvr-01:

```
ps -eo pid,comm        873 supervisor_nave     <- vivo
/pedir_slam            ✅ disponible
/pedir_nav             ✅ disponible
```

Y no solo existen: **la tarde del 07 se usaron los dos de verdad** — `/pedir_slam` levantó SLAM,
se mapeó el cuarto, y `/pedir_nav` levantó Nav2, que navegó y **paró a 6,1 cm del objetivo**
(evidencia 84). La pantalla del PC estaba, sin saberlo, describiendo como bloqueado algo que ya
funcionaba.

📝 **Y la lección es la de siempre, en su versión de dos máquinas:** el PC dedujo el estado del
robot de cuándo se había subido el código, no de haberlo consultado. **El repositorio dice qué
existe; solo el robot dice qué está corriendo.** Es la misma forma que «`ros2 topic list` incluye
topics de nodos muertos» — la lista y el proceso son cosas distintas.

✅ **Lo que sí sigue en pie de esa frase, y es lo útil:** que la pantalla **nombre el servicio** en
el mensaje de plazo agotado. Eso vale igual, porque el caso existe de verdad — un robot con el
driver caído o una unidad `latcheada` da exactamente esa firma.

✅ **Y lo que el robot CONFIRMA de esta entrada:** el contrato es correcto.

```
lista blanca de robot.launch.py, leída con AST:
  LEER       14   /amcl_pose /battery_state /collision_monitor_state /color /encoders
                  /estado_navegacion /estado_robot /imu /map /motor_status /odom /scan
                  /tf /tf_static
  ESCRIBIR    3   /cmd_vel_raw /emergency_stop /initialpose
  SERVICIOS  12   /enable_color /get_rgbc_sensor_values /pedir_nav /pedir_slam
                  /release_emergency_stop /set_led_rgb /set_leds /set_multiple_leds
                  /set_pos_and_yaw /start_scan /stop_scan /trigger_led_event
```

**14 · 3 · 12, exactamente lo que dice el PC.** El contrato y el robot coinciden.

---

## 2026-08-07 (tarde) — **Nav2 navega de verdad. Era el mapa.**

El robot se movió solo por primera vez en este proyecto. Y con ello se abrió el problema que
ocupó la tarde entera: **Nav2 declaraba el objetivo cumplido estando a 41 cm de él**, con una
tolerancia de 10.

Hicieron falta cuatro evidencias (81, 82, 83, 84) porque eran **dos fallos distintos con el mismo
síntoma aparente**, y arreglar el primero dejó el segundo en pie.

| | causa | arreglo | evidencia |
|---|---|---|---|
| el marco `map→odom` rotaba **98,46°** | la recuperación de «robot secuestrado» de AMCL — `recovery_alpha_slow/fast`, **los dos únicos parámetros del fichero sin una razón escrita al lado** | los dos a **0.0** | 82 |
| AMCL erraba **45 cm en posición** con el marco ya quieto | **el mapa** | remapear el sitio | 84 |

```
                          mapa rancio     mapa fresco
  error de AMCL              45,0 cm    →     8,9 cm
  corrección map → odom       0,424 m   →     0,028 m
  distancia real al objetivo  41,3 cm   →     6,1 cm     (tolerancia 10 cm)
  lo que dijo Nav2            ✅ ÉXITO      ✅ ÉXITO      🔴 LAS DOS VECES
```

✅ **Se puede prometer «ve a ese punto» con ~10 cm.** Es exactamente lo que la evidencia 83 decía
que **no** se podía. ⚠️ Con **n=1** sobre el mapa nuevo, y con AMCL todavía **peor que la
odometría** (8,9 contra 4,2 cm) — sigue añadiendo error, solo que poco.

### 🔴 Lo que se escaló a todo el repositorio

Porque el modo de fallo es silencioso y la imagen dorada lo habría repartido por 16:

| Dónde | Qué |
|---|---|
| `fase_6_preparar_imagen_dorada.sh` | **borra `~/mapas` y vacía `ATRIZ_MAPA`** — clonar el mapa del robot de referencia lo llevaría a 15 sitios donde no es del mismo cuarto |
| `verificar_robot.sh` | comprueba que **el `.pgm` exista** (el `.yaml` solo no basta) y **avisa a los 7 días**. Las tres probadas contra un mapa huérfano, uno sin `image:` y uno de hace 18 días |
| `maps/README.md` (Atriz_rvr) | reescrito: el fallo, los dos sitios donde viven los mapas, y el orden de marcado para medir |
| `ARRANQUE_NAVEGACION.md` · `CLAUDE.md` · `ESTADO_ACTUAL.md` | la condición operativa: **mapear es parte de montar el aula**, no una tarea de una sola vez |
| `localizacion_amcl.yaml` | el `⏳ NO VERIFICADO` de `recovery_alpha` era **rancio**: la evidencia 82 ya lo había verificado dos veces |

### 📝 Lo que se aprendió, que vale más que el arreglo

🔴 **Con UNA sola distancia de cinta no se puede saber dónde acabó el robot.** Deja al robot en
cualquier punto de una circunferencia. Con la diagonal sola, odometría y AMCL se separaban **2 cm**
mientras estaban a **45** la una de la otra: por eso las tres tandas anteriores no zanjaron nada.
Se resolvió con **trilateración desde dos marcas** (`mediciones_banco/comparar_con_cinta.py`).

🔴 **El instrumento competía por el recurso que medía.** Dos objetivos ABORTARON con
`Timed out while waiting for action server to acknowledge goal request (follow_path)`. No era
falta de asentamiento —se probó con 8 s—: era la **Pi saturada**, load **8,39 sobre 4 núcleos**,
con Claude Code al **21,6 %**. Cada `ros2 service call` levanta un intérprete de Python entero.
Arreglado juntando la prueba en **un solo proceso** que además **espera a que la carga baje**.
📝 Van **siete** veces que el medidor miente aquí, y esta es de familia nueva: no daba un número
falso, **perturbaba el sistema**.

🔴 **Y un error de método propio: se lanzó una tanda sin esperar a que el usuario marcara el
suelo.** «Lo anterior lo empezaste sin yo haber marcado nada». Esa tanda se descartó. También se
explicó mal dónde iba la marca `B` —«el lado corto del rectángulo»— y el usuario corrigió: la
línea tiene que pasar **por `A`**. Cuantificado después: 5 cm de desvío en `B` → ~2,4 cm de error.

📝 **De regalo:** la **deriva acumulada de la odometría** es **3,3 cm** tras un ciclo completo con
giros de 125°, medido por el usuario con cinta a la marca de partida. Quinta medida contra cinta,
y la odometría vuelve a salir reforzada.

### ⏳ Lo que queda

- **n=1.** La evidencia 82 ya enseñó que una tanda limpia puede sostener una conclusión que la
  réplica desmonta. Esto pide repetirse.
- **AMCL sigue siendo peor que la odometría.** 8,9 contra 4,2 cm, y esa diferencia está a ~2,7σ
  del error de la cinta: se distingue, sin mucho margen.
- **El aula sigue sin probarse**, y es un escenario **mejor** en las tres cosas que hacen difícil
  este cuarto: más grande, menos simétrico, y sin Claude Code comiendo un núcleo de la Pi.

---

## 2026-08-07 — SLAM y Nav2 desde la web, y **cinco instrumentos que mintieron**

El día que la web ganó los dos botones que faltaban. Y el día en que la misma
lección apareció **cinco veces seguidas**, que es lo que de verdad conviene
conservar de esta sesión.

### ✅ Lo que quedó funcionando

| | |
|---|---|
| `/pedir_slam` · `/pedir_nav` | `std_srvs/SetBool`. **PETICIÓN ACEPTADA**, jamás «arrancado» |
| `/estado_navegacion` | `EstadoNavegacion`, 11 campos, 1 Hz, **seis estados** |
| `supervisor_navegacion` | nodo aparte del driver: aísla el privilegio de `systemctl` |
| `atriz-slam.service` | nueva, instalada y **no habilitada** |
| `atriz-exclusion` | `ExecStartPre` de las dos, falla en 0,1 s antes de subir el X2 |
| `atriz-escaneo off-si-sobra` | apaga el barrido solo si nadie más lo necesita |
| `49-atriz-unidades.rules` | polkit acotado a **dos unidades y dos verbos** |
| `/etc/default/atriz` | **una** ruta del mapa, leída por las tres unidades |
| `atriz-nav.service` | `BindsTo=` → **`PartOf=` + `Requires=`** |

**Verificado de extremo a extremo**, con testigos independientes del supervisor:
unidad `active/success`, procesos vivos, los cinco nodos de ciclo de vida en
`active`, barrido encendido, y `/navigate_to_pose` **aceptando objetivos**.
⚠️ **No se envió ningún objetivo: el robot no se movió.** Que Nav2 *navegue*
sigue sin probarse.

### 📊 Los números que no existían

```
Nav2 hasta aceptar objetivos      24,3 s   (n=2, dispersión 0,44)
Nav2 hasta FUNCIONANDO             30,2 s   (n=1) ← ES EL QUE VE EL ALUMNO
systemctl start --no-block          0,05 s  (n=4)
systemctl start SIN --no-block     26,1 s   🔴
/pedir_nav, cliente persistente     0,22-1,02 s   (plazo de la web: 5,0 s)
```

### 🔴 CINCO INSTRUMENTOS QUE MINTIERON, Y ES LA MISMA LECCIÓN

1. **`is-active` sin timestamp.** La tabla `BindsTo`/`PartOf` registró solo
   `active`, que significa **dos cosas opuestas**. Con el PID como testigo:
   `PartOf=` **sí** devuelve la unidad, 9 de 9 → el diseño pasó de 4 unidades
   nuevas a 2 y se cayó el `Upholds=` entero.
2. **El cronómetro midiéndose a sí mismo.** Empezaba a contar cuando Python ya
   estaba en pie: el resultado hubo que darlo como intervalo (18-26 s). Con
   epoch y el observador arrancando antes, **24,3 s** exactos.
3. **`ros2 service call` como cronómetro.** Dio 6,3 s, **por encima del plazo de
   la web**. Es el arranque del CLI. Con cliente persistente, 0,22-1,02 s.
   📌 Este proyecto **ya se equivocó así en julio** con `/start_scan`.
4. **Un `param get` que no discriminaba.** El fichero decía lo mismo que el
   defecto del nodo, así que habría salido igual sin leerlo. Se cambió el valor
   y entonces sí probó algo.
5. **Dos supervisores a la vez.** Matar `ros2 run` no siempre se lleva al nodo
   hijo: la primera prueba de los rechazos fue contra el proceso viejo.

> **Antes de anotar una medida: ¿qué habría salido si la hipótesis fuera falsa?
> Si la respuesta es «lo mismo», no es una medida.**

### 🔴 Y `set -e` mordió por TERCERA vez

```
(( t++ )) con t=0                → desactivó la espera de puertos del LIDAR
[[ … ]] && kill                  → abortaba un banco de medición
EST=$(systemctl is-active …)     → dejaba el barrido ENCENDIDO
```

El tercero: `systemctl is-active` devuelve **3** para una unidad inactiva — eso
no es un error, es la respuesta. Con `set -e` la asignación mata el guion, y con
el `-` del `ExecStopPost` systemd se lo traga **en silencio**.

### Dos defectos que solo aparecen ejecutando

- 🔴 **El supervisor y la unidad miraban mapas distintos.** `PathJoinSubstitution`
  resuelve al directorio **instalado**; el script usa el **fuente**. Arreglado con
  `/etc/default/atriz`, que ataca la clase y no el síntoma.
- 🔴 **`CIEGO` en un arranque sano.** La máquina de estados lo comprobaba antes que
  `ARRANCANDO`, así que Nav2 pasaba ~1 s por «encendido pero SIN barrido». La web
  habría pintado una avería que no existe.

### Escalado a la imagen dorada

`fase_7_systemd.sh` en sus tres sitios, `MANIFIESTO.tsv` con cuatro líneas nuevas,
y **siete asertos** en `verificar_robot.sh` — el que más importa:

> **`User=sphero` es la línea de la que cuelga todo el modelo de seguridad.** La
> regla de polkit es inocua mientras los procesos corran como `sphero`. Si alguien
> pusiera `User=root`, se convertiría en ese instante en ejecución como root desde
> la red, y hasta hoy **ningún test lo veía**.

`145 comprobaciones correctas · 0 fallos.`

### Pendiente

- ⏳ **Que Nav2 navegue.** Mueve el robot y necesita espacio despejado.
- 🔴 **`off-si-sobra` con dos unidades activas NO SE PUEDE PROBAR**: son excluyentes
  por diseño. Esa rama solo se verifica por lógica, y así queda escrito.
- ⏳ Al PC: `contrato.ts` (12 servicios, 15 topics), `useTopic.ts` y las pantallas.

---

## 2026-08-06 (tarde) — El sensor de color SÍ se enciende en caliente

Una afirmación que este proyecto llevaba **seis días** dando por medida resultó no estarlo, y
bloqueaba una función que el usuario pedía. **No la destapó ninguna revisión de código —tres
pasadas la dieron por buena—: la destapó el usuario**, al recordar que en ROS 1 el ciclo
«encender el LED y luego leer el topic» funcionaba.

### 🔴 Lo que se creyó y era falso

> *«Con el streaming de `color_detection` ya configurado, `enable_color_detection` no hace nada —
> 481 mensajes de `/color`, todos ceros.»* (CLAUDE.md, MANUAL §16.2c, `rvr_driver_node.py:1218`,
> API_LABORATORIO.md, y el plan de la web.)

**La medida no probaba eso.** El servicio bajo prueba hacía `enable(True) → leer → enable(False)`
**en la misma llamada**, y 481 mensajes a 12,7 Hz son ~38 s: casi todos posteriores al apagado.
No distinguía «el enable no funciona» de «funcionó 200 ms y se apagó solo».

📌 **La regla que sale de aquí:** *una medida que da el mismo resultado tanto si la hipótesis es
cierta como si es falsa no es una medida.* Antes de escribir «medido», hay que poder decir qué se
habría visto si fuera falso.

### Lo verificado

Banco `mediciones_banco/probar_color_stream_caliente.py`, con el streaming corriendo a 250 ms,
reproduciendo la secuencia de ROS 1 (`clear→stop→handlers→start(250)` y **luego** el enable):

```
/color no-cero :  0/24 -> 24/24 -> 23/23 -> 0/24     reversible
canal claro    :  1 -> 1321 -> 1321 -> 1             1321x
RGB reales     :  (255, 223, 209)
```

Y después, ya implementado, **a través del driver y de rosbridge**:

```
/enable_color  std_srvs/SetBool
/color no-cero :  0 -> 53 -> 0
clear directo  :  1 -> 1320 -> 0
```

👤 El usuario vio encenderse el LED blanco bajo el chasis. Tercer testigo, y el que manda.

⚠️ **Defecto del banco, anotado**: el testigo de luz ambiente dio `0.0` en las cuatro fases,
incluida la línea base (bajo el driver real mide 4,99-19,98). El instrumento estaba muerto; no
contradice nada, pero deja el resultado con dos testigos automáticos en vez de tres.

### Lo implementado

- `rvr_driver_node.py`: servicio **`enable_color`** (`std_srvs/SetBool`) + `_encender_color()`,
  con el `sleep(0.1)` de ROS 1 dentro — sin él, quien lea al volver el servicio se lleva la
  muestra anterior (oscuridad) con `success=True`, que es el fallo de julio exacto.
- `robot.launch.py`: `/enable_color` y `/get_rgbc_sensor_values` en la lista blanca. **Van
  juntos**: sin LED no hay lectura, y sin lectura el LED no sirve.
- Corregida la afirmación falsa en CLAUDE.md, MANUAL §16.2c, API_LABORATORIO.md y el plan de la
  web. (Esta bitácora **no** se reescribe: es registro.)

### Y un hallazgo lateral que importa más

🔴 **Reiniciar el driver BAJA la parada de emergencia**: `self._parada_emergencia = False` en el
constructor (`rvr_driver_node.py:266`). Un robot que un humano detuvo a propósito vuelve a
aceptar `cmd_vel_raw`. Descarta la opción «reiniciar con el parámetro puesto» por seguridad, no
por incomodidad. **Sin resolver.**

### 🔴 Dos cosas que di por abiertas y estaban cerradas

Al recibir el informe del PC —que listaba «si Nav2 y SLAM arrancan solos» como decisión
pendiente— se cruzó con el repositorio y **no lo estaba**:

- **Decidida con el usuario el 2026-08-03**, en `ARRANQUE_NAVEGACION.md`: Nav2 instalada y **no
  habilitada** (no sobrevive a un reinicio), SLAM **a mano** por ser tarea de administrador. El
  dato que la decidió: la Pi se alimenta del USB del RVR, ~2 h de autonomía contra clases de
  2-3 h, y Nav2 son ~58 % de un núcleo.
- **Ratificada el 2026-08-06** por el panel de cuatro agentes (D2): `atriz-slam.service` instalada
  y no habilitada, A10 espera.

Es el mismo fallo que `ESTADO_ACTUAL.md` documenta en su primera sección — el 2026-08-05 se
listaron cuatro cosas ya hechas citando un fichero que se había quedado atrás. **Un documento de
decisión de tres días antes no se leyó.**

🔴 **Y peor: la «solución A recomendada»** de `2026-08-06-arrancar-desde-la-web.md` —servicios del
driver con `systemctl start` y polkit— **la había rechazado el panel esa misma mañana**, por
seguridad. Verificado en el código en vez de citarlo:

```
rosbridge_server/websocket_handler.py:233  def check_origin(self, origin) -> bool:
                                    :234      return True          sin condiciones
systemctl show atriz-robot -p User         →  User=sphero          el driver no es root
```

rosbridge no autentica a nadie, así que polkit convierte «cualquiera en la red del aula llama a un
servicio» en **«cualquiera en la red del aula hace que root arranque un proceso»**.

📌 Los cuatro requisitos de ese apartado **sí se quedan** —no bloquear `/release_emergency_stop`,
éxito por efecto, Nav2 sin mapa que se niegue—: valen para cualquier mecanismo. Lo que no vale es
el mecanismo.

⏳ **Lo único realmente abierto**, y es del panel (D2, razón 3): el argumento de Nav2 **no traslada
a SLAM**. Nav2 no se habilita porque cuesta 58 % de núcleo; **SLAM cuesta 4,8 %**, doce veces
menos. La conclusión puede seguir siendo la buena, pero por otras razones, y no están escritas.

### Escalado a todo lo que la imagen dorada necesita

Un servicio nuevo toca más sitios de los que parece. Alineado y **verificado
ejecutando**, no leyendo:

| dónde | qué |
|---|---|
| `verificar_robot.sh` | `enable_color` en la lista de clientes (18 → **19 servicios**), y un aserto nuevo: los **dos** servicios de color en la lista blanca. **Con control negativo**: sobre un launch sin ellos, falla |
| `atriz.py` | **`sensor_color(True/False)`**. `cerrar()` apaga la luz si la encendió el programa —paso 2 del cierre, después de parar el robot y sin tocar `secuencia_de_cierre()`, que es pura y tiene tests |
| prácticas 05, 11 y seguidor de línea | encienden la luz ellas solas; se cae el `sys.exit(1)` de las tres |
| `GUIA_PASO_A_PASO`, `REFERENCIAS`, `SEGUIDOR_LINEA_EXPLICACION` | ya no mandan pedirle al profesor que reinicie el robot |
| `ARQUITECTURA`, `SEGURIDAD_ROSBRIDGE`, `TRASPASO`, `README` de `Atriz_rvr` | 18 → **19 servicios**, con su aviso del LED |

```
91 tests           pasan (ninguno tocado)
biblioteca         color() (1,1,0,1) sin luz -> (411,758,310,1335) con luz
practica 05        lecturas reales sostenidas, claro ~1321-1335
cierre tras Ctrl-C sensor en clear=0 -> el LED quedo APAGADO
verificar_robot    126 correctas · 0 fallos · 6 avisos conocidos
```

📝 **Y un dato que refuerza al usuario:** dos guiones de alumno de ROS 1 ya
llamaban a `/enable_color`. La migración se dejó el servicio, y en vez de notarlo
se escribió que era imposible.

### La luz se apaga sola, y `color_activo` deja de ser opcional

El botón de la web puede encender un LED que gasta batería, y **el navegador no
puede prometer que lo apagará**: pestaña cerrada de golpe, recarga (que pierde el
flag, y es el caso más común en clase) o corte de WiFi —el transporte reconecta
solo y vuelve sin memoria de haber encendido nada—. Las tres dejan el LED puesto.

📌 **Cortesía en el navegador, garantía en el robot.**

🔴 **Y el diseño obvio estaba mal, lo destapó el usuario ANTES de escribir código.**
«Apagar si nadie está suscrito a `/color`» le habría cortado la práctica 5 a un
alumno a los 120 s: `atriz.py:903` lee **por servicio**, no por el topic. Más una
segunda pega suya: rosbridge abre **una sola** suscripción ROS para todos sus
clientes, así que una pestaña olvidada mantendría el contador a 1 para siempre.

Diseño final (`_vigilar_luz_color`, 1 Hz), la que ocurra antes:

```
color_apagado_inactividad_s  120.0   sin suscriptores Y sin llamadas al servicio
color_apagado_max_s          900.0   desde el enable, pase lo que pase
```

Parámetros del launch, no constantes. `0` los desactiva. La luz de
`color_detection:=true` **no** se apaga sola: la puso alguien a propósito.

**Medido — y las tres mitades importan** (evidencia 77):

```
sin actividad          color_activo True -> False a los 126 s · claro 1321 -> 1
                       log: «APAGADA sola: nadie la usa desde hace 121 s»
con servicio (alumno)  sigue encendida a los 160 s, umbral 120
con topic (la web)     sigue encendida a los 150 s, 14574 mensajes recibidos
```

Sin las dos últimas, la primera solo probaría que el apagado dispara — no que
dispare **cuando debe**. Un apagado que se dispara siempre es peor que ninguno.

🔴 El instrumento **no podía tocar `/color` ni el servicio** durante la espera:
las dos cosas cuentan como actividad y habrían reiniciado el contador medido.

**`EstadoRobot` pasa a 8 campos** con `bool color_activo`. Con apagado automático
el estado no se puede recordar: hay que leerlo. Y no vale mirar si `/color` trae
ceros — publica igual con la luz apagada, y una superficie negra de verdad también
da valores muy bajos. El topic dice qué se ve; el campo, si hay luz para verlo.

📝 Detalles que no son cosméticos: reloj **monótono** y no el de ROS (esto decide
una acción física y un salto de NTP no debe decidirla); se apaga con `_enviar` y
no con `_pedir`, porque bloquear en `g_salud` congelaría el latido y el detector
de silencio; y la bandera se baja **antes** de encolar, o el temporizador
dispararía en bucle cada segundo hasta que llegara el primer apagado.

**Verificador:** interroga ahora al `EstadoRobot` **instalado**, no al fichero.
Caza la trampa que avisó el usuario — tocar un `.msg` y compilar con `colcon
build` a secas dice «packages finished» y deja el mensaje viejo instalado; el
síntoma sale en el suscriptor como `AttributeError` y parece un fallo de la web.
126 correctas · 0 fallos · 7 avisos conocidos.

✅ **El tope duro, VERIFICADO el mismo día — y destapó un defecto.** El primer
intento no midió nada: `ros2 launch ... color_apagado_max_s:=20.0` se aceptaba
**en silencio** y el driver arrancaba con 900.0. Los dos parámetros estaban
declarados en el nodo y **no en `robot.launch.py`**, así que ajustarlos en el
aula habría obligado a editar ficheros — lo contrario de lo que se prometió.

📌 Lo destapó comprobar el parámetro **efectivo** en vez de fiarse de haberlo
escrito en la línea de comandos. **Un argumento aceptado no es un argumento
aplicado**, y es la misma clase de fallo silencioso que este proyecto persigue,
cometido al añadir la función escrita para evitar otro.

Arreglado y re-medido:

```
19.9s  claro=1321  color_activo=True
23.9s  claro=   0  color_activo=False      tope 20.0
```

Y la mitad que importa: se leyó el sensor **cada 3 s durante toda la prueba** y
**no lo salvó**. Eso separa el tope duro de la inactividad — ignora la actividad
a propósito, porque existe para la pestaña olvidada.

### Pendiente

- ✅ ~~Decisión del PC sobre cómo sabe la web el estado del color~~ — **resuelta la misma tarde**
  con `color_activo` en `/estado_robot`, y no como preferencia: el apagado automático la volvió
  obligatoria. Ver la sección de arriba.
- ⏳ **Al PC le toca ahora** `contrato.ts` (dos servicios + el campo nuevo de `EstadoRobot`),
  `useTopic.ts` y `PanelColor`, con `npm run contrato` en verde antes de dar nada por hecho.
- ⏳ SLAM y Nav2 desde la web siguen sin empezar: ahí el obstáculo es real (no son servicios ROS).

---

## 2026-08-06 (tarde) — El botón del color, y una afirmación que sobrevivió a su refutación

Lado **web** de `enable_color`. El robot lo implementó y midió; esto es lo que le tocaba a
`atriz-lab`, y lo que enseñó de paso.

### 🔴 Este cliente afirmó que ese botón no podía existir

`PanelColor` decía: *«no se puede encender desde aquí; con el streaming ya configurado,
`enable_color_detection` no hace nada — 481 mensajes de `/color`, todos ceros»*. Se copió del
driver, que lo llevaba marcado **«🔴 MEDIDO»**, y se citó como establecido — incluso para
recomendar **no construir el botón**.

**Aquella medida estaba mal hecha:** el servicio bajo prueba **se apagaba a sí mismo dentro de
la misma llamada**, así que casi todos aquellos mensajes eran posteriores al `enable(False)`.
Una medida que no separa las dos hipótesis no refuta ninguna.

📝 **La lección de segundo orden:** una trampa documentada también caduca, y esta venía con el
sello de «ya medido» que hizo que nadie la volviera a mirar en seis días.

### Lo que quedó en la web

| | |
|---|---|
| `contrato.ts` | `/enable_color` y `/get_rgbc_sensor_values`, los dos en `SOLO_QUE_NO_LANZO` |
| `useTopic.ts` | `color_activo` en `MensajeEstadoRobot` |
| `PanelColor` | el botón, **leyendo** `color_activo` en vez de recordarlo |

**El estado se lee, no se recuerda**, y ese es el punto del diseño: la luz se apaga sola, así
que un flag local pintaría el botón encendido sobre un sensor a oscuras.

### Dos correcciones que llegaron del robot, y las dos estaban en mi primera versión

1. **El testigo no podía ser «`/color` deja de ser `[0,0,0]`».** Sobre una superficie muy oscura
   eso puede no llegar **nunca** → falso negativo: el botón diría «no se encendió» con el LED
   encendido. Y no hay número que lo acote: **no está medido** cuánto da `/color` sobre negro con
   luz. El testigo es `color_activo`, exacto en los dos sentidos.
2. **El aviso anunciaba un plazo que nunca se cumple.** Con la pantalla abierta, estar suscrito a
   `/color` **ya cuenta como actividad**, así que los 120 s no saltan. Se anuncia el **tope duro
   de 15 min**, que ignora la actividad a propósito.

Y una tercera de cosecha propia: `/estado_robot` va `TRANSIENT_LOCAL`, así que el testigo lleva
la **guardia del `latido`** — el primer mensaje solo es referencia.

### El escalado, que es donde estuvo el trabajo de verdad

Pasar de ocho a diez servicios dejó deriva en **seis sitios**, y ninguno rompía nada:
`contrato.ts`, `contrato.test.ts`, `lenguaje.ts`, `lenguaje.test.ts`, la entrada de
`LO_QUE_NO_SE_PUEDE_DECIR` y el README.

🔴 **Y una era un hueco de cobertura, no prosa.** Las dos enumeraciones de `contrato.test.ts`
comprueban servicio por servicio **a propósito** —su comentario dice «la primera versión solo
miraba dos y dejaba pasar el error en los otros seis»— y se quedaron cubriendo **ocho de diez**.
La prueba de cobertura seguía en verde porque deriva de las constantes.

→ Se añadió un **cable trampa**: `expect(SERVICIOS).toHaveLength(10)`. No comprueba nada por sí
mismo; obliga a que alguien mire las enumeraciones al añadir un servicio.

**Verificado contra rvr-01**, por rosbridge y por el navegador:
`/color` no-cero 0 → 76 → 0 · `color_activo` false → true → false · el botón dijo «Hecho:
`color_activo` ha bajado».

508 pruebas · `npm run contrato`: 10 servicios, coinciden.

---

## 2026-08-06 — La sesión de la web, la navegación, y un mapa de verdad

Sesión larga y con **cuatro retractaciones propias**, tres de ellas destapadas por una revisión
multiagente de 9 agentes al final. Se listan primero porque son lo que más vale.

### 🔴 Lo que se creyó y era falso

1. **«La trampa de la durabilidad de `/map`».** Se escribió que `/map` podía no llegar NUNCA al
   navegador: va `TRANSIENT_LOCAL`, rosbridge se suscribe VOLATILE si no se le manda `qos`, y un
   VOLATILE —en teoría— no recibe lo ya publicado. Se llegó a escribir una rama entera de
   diagnóstico para esa firma. **Medido en cuanto hubo un mapa: cinco suscripciones NUEVAS a
   `/map` dieron 41 · 38 · 44 · 44 · 48 ms.** Sin entrega del latch habría que esperar ~2,5 s de
   media. **rosbridge SÍ entrega el valor latcheado**, y no hizo falta mandar `qos` — que era el
   arreglo obvio y el caro, porque el QoS del primer cliente gobierna a todos los demás.
   ⚠️ Medido contra `slam_toolbox`, que republica cada 5 s. Con AMCL publica `map_server`, que
   emite una sola vez: **sigue SIN MEDIR**.

2. **«El driver se reinició al cargar el RVR».** Se dio por establecido a partir de una prueba
   INDIRECTA —el barrido estaba apagado, que es lo que el `ExecStartPost` fuerza en cada
   arranque—. **Encajan TRES explicaciones**, y la tercera no se había considerado:
   `slam_toolbox` en `unconfigured` (proceso vivo, cero TF, cero `/map`, ni un error). Además está
   verificado que **el driver NO muere cuando el RVR se apaga**: `_recuperar_streaming` reintenta
   indefinidamente (evidencia 52: 123 reintentos con el proceso vivo). Lo zanja M6, que **caduca
   al reiniciar la Pi**.

3. **`rvr-01.local` «no resuelve».** Falso: era caché mDNS fría en el propio bucle de sondeo.
   2777 ms la primera vez, **13 ms** después. El arreglo del 2026-08-04 **sí sobrevivió a un
   arranque en frío**, que era justo lo que quedaba sin probar.

4. **`/odom` «a 6,08 Hz».** Falso, y es la **sexta** vez que el instrumento miente en este
   proyecto: el temporizador arrancaba antes de que el socket abriera y la resolución mDNS fría se
   comió media ventana. Medido con los sellos de tiempo del propio driver: **16,54 · 16,67 ·
   16,67 Hz**.

### ✅ Lo verificado contra rvr-01

| Qué | Resultado |
|---|---|
| **Conducir desde el navegador, de punta a punta** | Manteniendo pulsado «Adelante» con el ratón: 3 s a 0,100 m/s → `/odom` **29,7 cm**, **cinta 30,0 cm**. Error **0,3 cm (1,0 %)**. Rumbo −0,13° |
| **La lista blanca DENIEGA, y en silencio** | Con control positivo: `/stop_scan` contesta `result=true`; `/raw_motors` (a 80), `/move_timed` y `/move_to_pose` **no contestan nada**; publicar en `/cmd_vel` a 0,15 m/s da **0,00 cm**. **Cero** mensajes `op=status` |
| **Parada de emergencia y liberación** | Puesta por el camino de la web (`latido` 291 → la bandera sube en el 292) y **liberada desde el navegador**: la pantalla dijo «Liberada» y el robot lo confirmó |
| **Acciones de rosbridge** | `send_action_goal` funciona. Al fallar, `values` llega como **CADENA** («No action server available»), no como objeto. Y un `op` que rosbridge no entiende **no produce nada**: silencio absoluto en 4 s |
| **Un mapa de verdad** | Cuarto mapeado conduciendo el robot desde la web: 76 × 84 celdas a 5 cm, **7,41 m²** libres. Guardado en `~/mapas/cuarto.pgm` |

### 📐 «Frontera» en vez de «% sin explorar»

Mapeando, el porcentaje se plantó en 44,8 % y pareció que faltaba media habitación. **No faltaba
nada:** un relleno por inundación dio **2857 celdas desconocidas y UNA alcanzable**. La rejilla es
un rectángulo que envuelve al mapa, así que todo lo de fuera de las paredes cuenta como
desconocido para siempre. Ese número tuvo al robot dando vueltas buscando algo que no existía.

### La web

Sesión con `scrypt`, cookie `httpOnly` firmada con HMAC y bloqueo por intentos **en el servidor**,
con **cero dependencias nuevas**. Protege la interfaz, **no el robot**: rosbridge no tiene
autenticación y eso se dice en pantalla. Pantallas nuevas: `/entrar`, `/usuarios` y **Navegar**
(mapa, pose de AMCL, objetivo por clic, avance y cancelar). Y `/imu`, `/color` y
`/set_pos_and_yaw`, que estaban en el contrato sin consumidor.

Tres colisiones de color detectadas y cerradas, una de ellas **con un comentario que afirmaba
haberlas comprobado sin haberlo hecho**. Ahora lo mide una prueba.

### ⏳ Lo que queda abierto, y el plan

`00_auditoria/planes/2026-08-06-plan-slam-color-arranque.md` — cuatro análisis con sus cuatro
refutaciones. Cubre el color en caliente (A9), arrancar SLAM desde la web (A10) y la recuperación
tras apagar el RVR. Diez medidas pendientes (M1-M10) y cuatro decisiones (D1-D4).

🔴 **Dos hallazgos que no cubría ninguna propuesta:**
- **Si rosbridge muere solo, nadie se entera.** El nodo `puente` no lleva `on_exit` ni `respawn`:
  el launch sigue vivo, systemd en verde, `/odom` a 16,5 Hz — y el socket no abre nunca.
- **El estado `failed` de systemd es invisible desde la web** y exige `reset-failed` en el robot.

🔴 **Y uno de seguridad:** un reinicio del driver **baja la parada de emergencia sola**, y la web
**no la re-publica al reconectar**, a propósito. Nadie la repone.

---

## 2026-08-04 (parte 17) — Las diez pantallas construidas sobre lo que devolvió Stitch

Stitch generó las diez a partir de `PLATAFORMA_STITCH.md`. **Acertó el mundo visual y rellenó
todo lo demás de datos inventados** — exactamente lo que la §8 predecía y para lo que existe la
§10. La lista de revisión los cazó a los diez:

```
latencias        «Latencia: 42 ms» · «LATENCIA 14ms» · «latencia inferior a 90ms»
                 · «Retraso maximo de red: 2.4s»          en cuatro pantallas
animate-*        pulse / ping / infinite                  en cuatro pantallas
voltajes         12,10 V · 11,98 V · 11,42 V   (el RVR no pasa de ~8,3)
prosa            «sector 4-BETA», «Ultimo ping valido 14:02:11 Z»,
                 «CONFIRMAR RECEPCION»
ingles y rutas   MARCO_ROBOT_V1.0 · «Fleet Wall» · «Maps» —no hay mapa—
```

📝 **Y un detalle que vale como confirmación:** Stitch dejó **nombres de iconos como texto
suelto** —`visibility`, `shield`, `memory`— porque cargaba Material Symbols **desde Google y la
fuente no llegó**. Es literalmente el fallo por el que aquí la tipografía va empaquetada y los
iconos se dibujan.

**Lo que sí se adoptó**, porque resolvía tensiones que el documento tenía abiertas: el **modo
proyección** —que además responde a la objeción del análisis contra el mundo oscuro: el vidrio
resta contraste en la única pantalla que se mira a tres metros—, el **orden por número/atención**
y el **titular a dos líneas**. Se rechazó su orden «por voltaje»: la batería se decide por
umbrales, no por ranking.

**Dos rutas nuevas, las que propuso el análisis multiagente y no el encargo:**

- **`/robot/[id]/no-obedece`** — mira cinco causas contra lo que el robot ya dice. **No elige
  una** (devuelve todas las que encajan), **nunca dice que el robot esté bien**, y **no ofrece
  liberar la parada**. Verificada por efecto con el robot apagado: dijo «una causa encaja: no hay
  enlace» y no inventó las otras cuatro.
- **`/cuaderno`** — la pareja robot/cinta. No juzga: sin tolerancia medida por práctica, un
  semáforo sería un juicio que no puede emitir. Con un lado vacío la diferencia es `null`, no `0`.
  Verificado con los números de la tarea 9: 30,2 contra 30 → **−0,20 cm**.

**Y el Taller, que yo había dado por bloqueado y no lo estaba:** la F0 bloquea *conectarlo*, no
dibujarlo. Ahora es lo que la §5.4 pedía —la lista de requisitos **medidos** que el agente de
sesión tendrá que cumplir, con `fichero:línea`— más la **cuenta del espacio por práctica**, que va
antes de ejecutar porque `Robot()` enciende el barrido y a partir de ahí el robot ya obedece.

⚠️ **Y el estado real de la verificación, que es lo que importa:** la prueba de pantallas
renderizadas pasó de 6 a **9 rutas** y da **28 de 29**. La que falla es la de **presencia** —«que
los datos lleguen»— porque **rvr-01 está apagado** por batería. Que se niegue a pasar sin datos es
para lo que existe: *una batería de comprobaciones de ausencia la cumple una página vacía*.

`atriz-lab`: **391 pruebas + 31 saltadas**, nueve rutas a 200, `tsc` y `eslint` limpios.

---

## 2026-08-04 (parte 16) — La plataforma repensada para Stitch, y el sesgo que la retrasaba

**El usuario pidió cinco veces un diseño mejor y cinco veces contesté que «las skills no aplican
aquí».** Al ponerlo en fila se ve el patrón: las **cinco** propuestas que llegué a hacer —el gris
plano, el tablero verde, y las maquetas A·Galón, B·Carta y C·Esmalte— eran **la misma familia**:
apagadas, de papel, derivadas de un objeto físico, fondo claro, contenidas. Ese era mi sesgo, no
el encargo. El encargo llevaba desde el principio diciendo *color, animación, que se vea caro*.

📝 **La lección, y es de método:** cuando alguien rechaza varias propuestas seguidas, el error
rara vez está en la última — está en el **eje que todas comparten y que nadie nombró**.

**`03_operacion/PLATAFORMA_STITCH.md`**, nuevo, cubre **la plataforma entera** y no solo el
sistema: las ocho pantallas una a una, los componentes, los estados, el movimiento, el
responsive, y **prompts listos para pegar** en Stitch por pantalla.

Registro comprometido: **producto digital contemporáneo**, pozo oscuro azulado, tarjetas de
vidrio con desenfoque, dos orbes de luz ambiente fijos, acento eléctrico, tipografía grande y
entrada escalonada. Con **modo claro solo en el muro del profesor**, porque es la única pantalla
que se proyecta.

🔴 **Y lo que NO cambia:** la sección 8 —las prohibiciones— viaja entera desde el documento
anterior, palabra por palabra. Nada late, nada se anima al llegar un dato, ningún dato inventado,
el voltaje manda sobre el porcentaje, «no se sabe» se ve distinto de un cero. **Son fallos
medidos en el laboratorio, no preferencias estéticas**, y por eso sobreviven a un cambio total
de piel.

**Se borran** `DESIGN.md` y `ENCARGO_DISENO_UI.md`: describían la versión descartada y tenerlos
al lado del nuevo solo invita a pegar el equivocado.

📎 Seis maquetas en HTML quedan como referencia de acabado (A-F). Las tres nuevas —**D·Órbita**,
**E·Bloques**, **F·Aurora**— son el registro nuevo; las tres primeras, el viejo.

---

## 2026-08-04 (parte 15) — El cierre de la app: las pantallas ya se comprueban, y el acabado

**Paso 3 — las pruebas que miran lo PINTADO.** `pantallas_reales.test.ts`, guardada tras
`ATRIZ_ROBOT=1`: arranca un navegador headless por CDP —**sin instalar nada**, node 22 trae
`WebSocket` global—, abre las seis rutas contra el robot real y comprueba el HTML **ya
hidratado**, que es donde vivía «hace hace 7,9 s» y donde el HTML del servidor no llega.
**19 comprobaciones, 56 s, 19 de 19.**

🔴 **Y su primera ejecución enseñó más que la propia prueba.** Falló porque yo había puesto
`rvr-01.local` como segmento de `/robot/[id]`, y esa ruta da **404 a propósito**:
`interpretarIdRobot()` acepta solo un número 1–16 o una IPv4 literal, porque aceptar un anfitrión
cualquiera la convertiría en «abre un WebSocket a donde diga la URL» sobre una aplicación **sin
autenticación**.

O sea que las seis rutas eran páginas 404. Y **18 de las 19 comprobaciones pasaron sobre ellas**:
repetición, hueco disfrazado de dato y frase prohibida son todas de **ausencia**, y una página
vacía las cumple todas. Solo la que exige que los datos **lleguen** lo vio.

→ **Toda batería de comprobaciones de ausencia necesita al menos una de PRESENCIA**, o es una
  comprobación muerta que cuenta como aprobada. Este proyecto ya tuvo una: el bloque de `/odom`
  del verificador del robot solo corría si `/odom` salía en `topic list`, así que con el driver
  parado no corría **y contaba como correcto**.

**Paso 4 — el acabado.** Estados de foco: en la losa de 1 px el `outline-offset` invadía a la
baldosa vecina **y la vecina lo tapaba por dos lados** — foco partido justo en el muro. Y
transición de 200 ms al cambiar de estado, que es **anti-parpadeo**: con 16 baldosas, un hipo de
WiFi que cruce el umbral y vuelva da un estroboscopio.

🔴 **Y un defecto que apareció al mirar, no al planear:** la franja de atención era
`border-l-0 / -4 / -8`, así que cambiar de estado **desplazaba el contenido** 4 u 8 px y el
identificador quedaba **desalineado entre baldosas según el estado de cada una** — en una losa
4×4 se lee como un borde dentado. Ahora es una barra absoluta escalada por `transform`: no mueve
nada y las dieciséis alinean igual.

📌 **Lo que NO se hizo, y es una decisión:** «tarjetas que dejen de ser todas iguales». Aquí gana
`operate.md` —*«Consistency over surprise»*— y las tarjetas ya se diferencian por su **papel**.
Fabricar variación decorativa encima sería adorno en un instrumento.

⚠️ **Nota operativa:** la batería de rvr-01 fue **8,08 → 7,96 → 7,67 → 7,52 V** a lo largo de la
sesión. El umbral de «baja» del firmware son 7,0 V.

`atriz-lab`: **358 pruebas + 21 saltadas** (19 nuevas), `tsc`, `eslint` y `contrato` limpios.

---

## 2026-08-04 (parte 14) — Una dirección por red, y el navegador ya entra por nombre

**En el robot** (evidencias 74 y el plan `2026-08-04-direccionamiento-flota.md`): se pasó a
**una dirección por red**. `[Match] SSID=` de systemd-networkd elige el fichero según la red en
la que esté el robot, y en avahi `use-ipv6=no` **más `publish-aaaa-on-ipv4=no`**.

🔴 **Lo segundo no es un detalle:** `use-ipv6=no` apaga el *transporte* IPv6, pero el registro
`AAAA` **se seguía anunciando por el transporte IPv4** — la opción venía comentada, corriendo con
su valor por defecto (`yes`). Sin ella, `Resolve-DnsName` desde el PC seguía viendo la `fe80::`.

⚠️ Y ahí hubo un testigo falso que casi lo da por cerrado: `getent ahosts rvr-01.local` **desde la
Pi** devolvió una sola dirección mientras el PC recibía dos. **`getent` no ve lo que la Pi anuncia
al cable.**

**Desde el PC** (evidencia 75) se cierra el único punto que la 74 dejaba abierto de este lado:

> 🔴 **EL NAVEGADOR.** `Resolve-DnsName` ya dice lo correcto, y NO basta […]
> Falta abrir `ws://rvr-01.local:9090` y ver que ABRE. Es el único criterio.

> 🔴 **EL NAVEGADOR.** `Resolve-DnsName` ya dice lo correcto, y NO basta […]
> Falta abrir `ws://rvr-01.local:9090` y ver que ABRE. Es el único criterio.

```
ws://rvr-01.local:9090     ✅ ABRE   4339 ms (caché fría) · 2331 ms (caliente)
ws://192.168.1.200:9090    ✅ ABRE   4623 ms   (control por IP)
ws://10.14.7.7:9090        🔴 12 s sin onopen, sin onerror y sin onclose
```

Y el muro, de extremo a extremo y con control:

```
por NOMBRE, sin override      rvr-01 · 7,67 V · en línea    ✅  1 de 16
con override a 192.168.1.58   no llego                      ✅  0 de 16
```

📝 El segundo **también es correcto**: el DHCP está apagado, así que `.58` ya no existe. Confirma
que el override apunta a donde dice.

**Cuánto cuesta el nombre, y de dónde sale:** por nombre, cinco tomas seguidas dan
`7293 · 2 · 2 · 2 · 2 ms`; por IP, `2 · 1 · 2`. O sea que **el coste es entero de la primera
resolución mDNS**. Con `ipconfig /flushdns` antes de cada toma: **2716 · 2710 · 2729 ms**, muy
consistente. ⚠️ Aquel **7293 ms** fue la primerísima consulta tras el cambio, **no se ha vuelto a
reproducir y no se explica** — se anota en vez de redondearlo, porque es el peor caso observado.

🔴 **Y eso obligó a corregir algo mío: el plazo de conexión estaba en 5 s y era demasiado justo**
—400 ms de margen sobre los 4623 medidos, y la toma de 7,3 s lo habría pasado—. Un plazo corto no
da un fallo: da un «no llego» **intermitente** sobre un robot sano. Subido a **10 s**, que no
cuesta nada en pantalla: la baldosa ya dice «no llego» desde el primer instante y el plazo solo
decide cuándo se **reintenta**.

📌 **El plazo y el override se quedan** aunque la causa esté cerrada: un robot apagado da la misma
firma, sin `onclose` la reconexión no arranca, y **el aula sigue sin probarse entera**.

⚠️ **Y el diagnóstico fácil engañó DOS veces en este asunto**, en las dos direcciones:
`ping` + `Resolve-DnsName` daban verde con el navegador colgado; y al arreglarlo, `getent ahosts`
**desde la Pi** dio una sola dirección mientras el PC recibía dos. → **El testigo válido es el
cliente.**

---

## 2026-08-04 (parte 13) — Por qué el muro no encontraba a ningún robot

**El usuario avisó de que «no funciona nada en flota»**, y resultó no ser de la aplicación.
Medido en el navegador con el robot **encendido y sano**:

```
ws://rvr-01.local:9090     🔴 12 s sin abrir, sin error y sin cierre
ws://10.14.7.7:9090        🔴 12 s igual   <- LA MISMA FIRMA
ws://192.168.1.58:9090     ✅ abre
ws://192.168.1.200:9090    ✅ abre
```

`rvr-01.local` resuelve a **cuatro** direcciones y el resolutor las devuelve en este orden:
`fe80::…` (IPv6 link-local **sin zona**, inservible), `10.14.7.7` (la estática del laboratorio),
y **después** las dos que sirven. El navegador prueba en ese orden y **las dos primeras no
fallan: se cuelgan**; un SYN sin respuesta tarda ~21 s en rendirse.

🔴 **Es la consecuencia directa de la decisión «estática + DHCP conviven en `wlan0`»**, que sigue
siendo correcta para el robot. Para un cliente significa que **desde cualquier red al menos una
de sus direcciones es un agujero negro**. En el aula ocurre lo mismo al revés, y allí funciona
**por suerte**: `10.14.7.7` va antes que las de casa.

⚠️ **Y el diagnóstico fácil engaña:** `ping rvr-01.local` responde en **1 ms** —elige la `fe80`
con su zona `%10`— y `Resolve-DnsName` lista las cuatro sin quejarse. Las dos herramientas dicen
que el nombre está bien. Lo que falla es abrir un TCP **desde el navegador**.

✅ **Cerrado en `atriz-lab` con dos piezas** (decisión del usuario entre tres opciones):

- **Plazo de conexión de 5 s.** Sin él un socket colgado **nunca llama a `onclose`**, así que la
  reconexión con espera creciente —escrita justo para esto— no llegaba ni a arrancar, y el muro
  dejaba **16 conexiones colgadas para siempre**.
- **Dirección por robot**, escrita a mano y guardada en el navegador. JavaScript **no puede**
  enumerar lo que resolvió un nombre ni elegir dirección: no hay API.

**Verificado con control:** `0 de 16` baldosas vivas por nombre, **`1 de 16` con la dirección
puesta** (`rvr-01 · 7,96 V · en línea`).

📝 **La forma general: un fallo que se CUELGA es peor que uno que falla.** Sin `onerror` ni
`onclose` no hay nada que reintentar ni que registrar — el mismo perfil que el RVR dormido con el
nodo vivo y el nodo muerto con systemd en verde.

**Y de la misma sesión, mirando las pantallas con datos reales:**

- **`lib/interfaz/repeticion.ts`**, que caza el texto duplicado que las pruebas no veían. Sus dos
  parámetros salieron de **fallos propios**: `\b` en JavaScript es ASCII aunque lleve el flag `u`
  —«batería a 8,29 V, a 1,29 V» casaba como «a a»— y el corte etiqueta/prosa hay que medirlo en
  **palabras**, no en caracteres.
- **`Atasco [no se sabe] no se sabe`**, la misma frase dos veces, repartida entre la insignia y
  la antigüedad. Ningún detector la ve: trabajan sobre un solo elemento. La vio una captura.
- **La mitad derecha de la pantalla estaba vacía** en conducir y LIDAR: paneles de 1104 px con el
  texto capado a 600. No era oscuridad, era eso.

`atriz-lab`: **321 → 358 pruebas**, `tsc` y `eslint` limpios.

---

## 2026-08-04 (parte 12) — El encargo de diseño, replanteado pantalla a pantalla

**`03_operacion/DESIGN.md`**, escrito con la skill `stitch-design-taste` y en su formato, que es
el que interpreta Google Stitch. Sustituye a `ENCARGO_DISENO_UI.md`, que queda marcado y **no
debe pegarse en Stitch**.

**Lo que añade sobre el anterior:** las siete pantallas descritas una a una (portada, muro,
espacio del robot, terminal, telemetría, conducir, LIDAR, diagnóstico), la jerarquía de tres
niveles cifra/unidad/antigüedad, y el sexto estado vacío — **«no construido»**.

**🔴 Y lo que lo hace útil de verdad: anula CINCO reglas por defecto de la propia skill**, cada
una con su motivo medido. La que más importa:

```
la skill dice   «Perpetual micro-interactions: every active component should
                 have an infinite loop state (Pulse, Shimmer…)»
aquí            PROHIBIDO SIN EXCEPCIÓN
por qué         un pulso infinito en un indicador de estado es INDISTINGUIBLE
                de un latido real, y esta pantalla vigila 16 robots que pueden
                estar mudos
```

Las otras cuatro: nada de *skeleton loaders* («never invent progress»), el color es un
**vocabulario de cinco estados** y no un acento único, varianza bajada de 8 a **2** (un
instrumento no sorprende), y **ningún dato inventado** — ni redondo ni «orgánico», que es lo que
la skill recomienda para que no parezca relleno.

✅ **Contrastes calculados, no supuestos:** los **14 pares** (7 tintas × 2 fondos) pasan WCAG AA,
**0 fallos**. Peor caso **Neutro sobre Lino, 4,59:1** — justo por encima de 4,5, así que el gris
de «no se sabe» **no puede aclararse más**. Mejor caso 17,49:1.

✅ **Y no es una propuesta: es lo que ya corre.** Los ocho colores, las tres duraciones y las dos
curvas están tomados de `globals.css` y verificados uno a uno (`--background: 250 250 249` =
`#FAFAF9`, `--border: 214 211 209` = `#D6D3D1`, …). La §10 lleva la tabla de correspondencia,
para que lo que devuelva Stitch se pueda **contrastar contra la aplicación** en vez de admirarse
suelto — y para que se note si alguien cambia el CSS y deja el documento mentido.

📌 Se sube también `00_auditoria/planes/2026-08-04-cierre-app-web.md`, la especificación del
cierre aprobada antes de ejecutar, que estaba escrita y sin commitear.

⏳ **Pendiente y sin respuesta:** si `rvr-01.local` resuelve en el navegador **real** del
usuario. Medido en Edge headless: por nombre **no abre nunca** (3 de 3, 8 s de plazo; 0 de 16 en
el caso del muro), por IP **7 · 20 · 36 ms**. Headless no lleva resolutor mDNS, así que **la
medida puede ser del instrumento y no del sistema** — la trampa que este proyecto lleva
documentada cinco veces. No se diseña ningún arreglo hasta saberlo.

---

## 2026-08-04 (parte 11) — La comprobación cruzada, hecha; y una falsa alarma resuelta

**Cuarta corrida, y la primera con las dos mitades del mismo evento.** Hasta aquí cada lado se
creía a sí mismo.

```
lado PC   recorrido antes 27,8 cm · TRAS LA PARADA 1,8 cm · total 29,6 cm
lado Pi   log «PARADA DE EMERGENCIA» ×1  ·  Aug 04 11:46:13.890
          /estado_robot: FLANCO False -> True presenciado (latido=2181)
          código de salida 0
```

**4 de 4 corridas paran el robot.** Cuantificadas: **2,9 · 2,3 · 1,8 cm**, rango 1,1 — contra los
9,9-10,7 del `collision_monitor`. La parada corta en el driver; no ralentiza con un polígono.

⚠️ **Lo que NO cierra:** la latencia. Los dos relojes no están sincronizados a ese nivel y el
testigo de la Pi se muestrea a 1 Hz. Prueba que el camino entrega y que el driver aplica; no cuánto
tarda.

### 🔴 Y una falsa alarma del mismo día, resuelta: «`/odom` a 14,3 Hz»

Se anotó **desde las dos máquinas** que `/odom` iba a 14,3 Hz contra los 16,5 habituales, «sin
explicar». **El robot estaba sano. Mentía el medidor**, y medido en el mismo minuto:

```
ros2 topic hz /odom .......... 16,51 Hz   ← referencia (/imu 16,39-16,57)
spin_once(timeout_sec=0.0) ... 16,40 Hz   ✅
spin_once(timeout_sec=0.1) ... 15,02 Hz   🔴  (en otras tomas, 13,6-14,3)
```

`spin_once` procesa **un callback por llamada**: con `timeout_sec=0.1` el bucle gira ~10 veces por
segundo y el conteo queda capado por el **bucle**, no por el robot.

🔴 **Esto corrige el remedio que `CLAUDE.md` daba por bueno desde el 2026-07-31**, que decía
exactamente `timeout_sec=0.1` con el comentario «16.5 Hz — el valor real». La cifra era falsa y el
remedio, la mitad: lo que arregla el conteo es el `0.0`, no el ejecutor persistente por sí solo.

📝 **La lección de segundo orden, que es la que vale: una trampa documentada puede traer un remedio
que tampoco funciona**, y se usa sin comprobarlo porque viene con el sello de «ya medido». Van tres
cosas documentadas hoy que resultaron estar a medias — la espera de puertos de `atriz-robot.sh`, los
`✓` de `fase_7 --simular`, y esta.

⚠️ Una tercera variante —girar el ejecutor en un hilo— dio 13,70 Hz y **no se cree**: el proceso
volcó el core al cerrar. Queda **SIN MEDIR**.

---

## 2026-08-04 (parte 9) — `feat/estado-robot` probada en el robot y fusionada

Fusionada en `ros2` (`65ad124..2fdcf6c`, avance limpio, 3 commits). Se probó **antes** de fusionar,
en una rama local desechable: si algo hubiera fallado, `ros2` quedaba intacta con un `checkout`.

Compilada con el borrado obligatorio de `build/` e `install/` del paquete de mensajes (4 min 34 s),
y comprobado el **efecto** —el `.msg` instalado con sus seis campos— y no el «Finished» del colcon.

### Lo que había que comprobar no era el topic nuevo

```
/odom          16,528 Hz      ← intacto tras 225 líneas nuevas en el driver
/imu           16,679 Hz
/estado_robot   1,000 Hz      ← exacto
latido 360 → 367 · parada=False · rvr_responde=True
muestra=0,011 s · odom=0,012 s  ← los dos relojes pegados, la línea base sana
errores del driver en 5 min: 0
```

Los dos relojes juntos y cerca de cero es el discriminador **en su estado sano**: si un día llegan
cuatro de los cinco componentes, `muestra` se quedará abajo y `odom` empezará a crecer.

### ⏳ Y lo que NO está verificado, que es lo que justifica el mensaje

Está probado que **no estorba**; no que **sirva**. Ningún campo se ha visto en su estado de fallo:
`rvr_responde` nunca en `false`, `reanudaciones_fallidas` en 0, `parada_emergencia` nunca en `true`.
Y hay una ironía: la noche anterior tuvimos el estado de fallo durante quince minutos, y se cerró
apagando el robot **antes** de que este código existiera.

📌 De los cuatro, `parada_emergencia` **sí se puede cerrar sin esperar a que se rompa nada**:
publicar la parada con el robot en marcha. Ya estaba pendiente por otro motivo — ese botón ha
fallado **cinco veces** en este proyecto, cuatro devolviendo éxito con cero efecto.

### 🔴 Consecuencia para `atriz-lab`, que conviene saber antes de mirar su CI

`/estado_robot` entró en la lista blanca del robot (`LEER` pasa de 12 a 13), así que
`comprobar_contrato.mjs` sale con **código 1**:

```
🔴 LEER / TOPICS_LECTURA divergen
   solo en el ROBOT: /estado_robot
```

**Es correcto que falle** —la política es «gana el robot»— y se cierra añadiendo el topic a
`TOPICS_LECTURA` y su tipo `atriz_rvr_msgs/msg/EstadoRobot` a `TIPOS`. 👤 PC.

### 📝 Y una corrección de una regla del proyecto, que llevaba meses repitiéndose

`CLAUDE.md` decía **«despertar el robot enciende sus LEDs»** y ese aviso se daba antes de cada
reinicio. **Es falso:** cero llamadas a LEDs en `_conectar_rvr`; lo único que enciende algo es
`color_detection:=true`, que está en `false`. **Lo desmintió el usuario mirando el robot** —«que
sepas que no se encendieron los leds»— y se comprobó después en el código.
→ Avisar de un efecto que no ocurre gasta la credibilidad del aviso que sí importa. Y **el ojo de
  quien tiene el robot delante es el instrumento que manda**, que ya era regla escrita.

### 📝 Cuarta vez que miente un instrumento, hoy, y esta era de manual

Un contador propio con `spin_once(timeout_sec=0.1)` en bucle dio **14,3 Hz** sobre un robot a
**16,5**. `CLAUDE.md` tiene esa trampa documentada literalmente —«`rclpy.spin_once` EN BUCLE PIERDE
MENSAJES: 11.3 Hz sobre un robot que va a 16.5»— y aun así se usó toda la noche. El bueno es
`ros2 topic hz`.
→ Lo que salva las conclusiones anteriores: **un contador que pierde mensajes no inventa cuando no
  hay ninguno.** Los ceros eran ceros; los ritmos estaban subestimados.

---

## 2026-08-04 (parte 10) — El control por SSH: la TAREA 9 queda CERRADA

La especificacion del cliente pedia que el desplazamiento medido con cinta desde el navegador
coincidiera con el del **mismo movimiento por SSH**. Hecho, con la secuencia replicada EXACTA
—barrido, 0,20 m/s, 1,5 s, republicacion a 10 Hz, parada de emergencia— para que **lo unico
distinto sea el transporte**.

    corrida        antes de parar   frenada   TOTAL (odom)   CINTA
    web · 3            28.0           2.3        30.2         30
    web · 4            27.8           1.8        29.6         30
    SSH · control      29.0           2.3        31.3         31

✅ **La cinta valida la odometria por TERCERA vez** (31,3 contra 31). Tres corridas, dos
transportes, y la odometria acierta siempre dentro de la resolucion del instrumento.
✅ **La frenada es indistinguible entre los dos caminos**: 2,3 por SSH contra 1,8-2,9 por
WebSocket. La parada de emergencia se comporta igual venga por donde venga.
✅ **El criterio de aceptacion queda CUMPLIDO**: 30, 30 y 31 cm. El camino web **no introduce un
error de movimiento que importe**.

⚠️ **Y lo que NO se afirma:** el total sale ~1,4 cm mayor por SSH. **No se atribuye al transporte**
—es n=1 contra n=2, y la dispersion DENTRO del propio camino web ya es 0,6 cm—. Un efecto de 4,7 %
con esos tamaños de muestra no se distingue del ruido de corrida a corrida, y separarlo exigiria
repeticiones que **no compensan**: la tolerancia de objetivo de Nav2 son 10 cm.

📝 Anotado sin importancia para la distancia: el control dio «barrido listo en **0.08 s**» contra
2,10-2,50 s de las corridas web, o sea que el LIDAR **ya estaba barriendo**. El estado de partida no
era identico.

---

## 2026-08-04 (parte 9 bis) — Correccion: NO hubo medida desde el lado del robot

La evidencia 71 decia que la tercera corrida era «el mismo evento medido desde los dos lados». **Es
falso**: el observador de la Pi se lanzo, pero **fallo y no dejo registro**. La comprobacion cruzada
—que era la razon de repetir la corrida— **sigue sin hacerse**, y todo lo medido viene de UN lado.

📝 Lo escribi como hecho antes de saberlo: di por bueno lo que se **lanzo** en vez de lo que se
**comprobo**. Es exactamente el error que este proyecto persigue, cometido dentro del experimento
que existe para no cometerlo.

⚠️ Lo que NO cambia: los numeros del PC siguen valiendo (3 de 3, frenada 2,3-2,9 cm, la bandera del
driver a `true`) y **la cinta tampoco** (30 contra 30,2 cm), que es un testigo independiente de
verdad. Lo que falta es el tercero: el log del driver y el instante del corte vistos desde dentro.

---

## 2026-08-04 (parte 9) — La parada de emergencia, POR WEBSOCKET y con el robot en marcha

**Era la pata que faltaba, y es la que mas ha mentido.** La parada ha fallado CINCO veces en este
proyecto, cuatro devolviendo exito con cero efecto. El navegador **no publica con `rclpy`**: manda
`advertise` + `publish` por WebSocket y es **rosbridge, ya dentro del robot**, quien resuelve el
nombre y elige el QoS — que es justo donde vivieron dos de esos cuatro fallos. Ese camino no se
habia ejercido nunca.

Con `Transporte` y `Teleoperacion` de PRODUCCION, sin atajos. Evidencia 71.

    recorrido antes de la parada   25.6 cm  ·  28.0 cm
    RECORRIDO TRAS LA PARADA        2.9 cm  ·   2.3 cm     <- 3 de 3 corridas
    bandera de parada DESPUES        true   ·    true

✅ **2,3-2,9 cm.** El `collision_monitor` frena en 9,9-10,7: la parada de emergencia **corta en el
driver**, no ralentiza con un poligono, y se nota.
✅ **`/estado_robot.parada_emergencia` paso a `true`** — el testigo que se fusiono esta misma
mañana. **Es la primera vez que la web puede VER que la parada se aplico**, en vez de deducirlo de
un `200 OK`, que es exactamente como mintio cuatro veces.
✅ Y una sonda de solo lectura confirmo de paso que **`/estado_robot` atraviesa la lista blanca y
llega al navegador**, que `antiguedad_muestra_s` y `antiguedad_odom_s` salen **pegadas** en el caso
sano —el discriminante del tercer estado esta vivo—, y que la bandera **refleja el `release`**: la
mitad de «soltarla», donde fallo la cuarta vez, tambien tiene testigo ahora.

⚠️ **Lo que NO cubre:** avance recto a 0,20 m/s, sin Nav2, conexion ya abierta. **No** cubre parar
una meta de `/navigate_to_pose` en curso, que sigue abierto. Y el desplazamiento es odometria, no
cinta.

### 🔴 Y un fallo de instrumentacion que costo una corrida entera

**La primera corrida aprobo y no dejo ni un numero.** Vitest intercepta la consola y su reportero por
defecto no la imprime: quedo el verde y se perdio la medida — y con ella lo unico que decia si el
tercer testigo habia confirmado, porque ese caso **solo avisa, no falla**. Del `PASSED` no se podia
deducir.
→ Misma familia que «canalizar la salida de `ros2 topic hz` la esconde»: el instrumento estaba bien
  y **el canal de salida se comio el dato**. Van seis veces que el instrumento miente aqui.
→ Y repetir **no era gratis**: el robot queda con la parada puesta y liberarla es presencial.
  Arreglado escribiendo el informe a un fichero.

---

## 2026-08-04 (parte 8) — El tercer estado: /odom muerto con el enlace VIVO

Lo encontro la revision **desde el robot** de la rama `feat/estado-robot`, antes de fusionarla, y es
un hueco que el mensaje nuevo **no cubria**. Verificado en el fuente (`_quiza_publicar`, lineas
1979-1986).

Los espejos `_t_muestra_real` / `_n_muestras` avanzan **ANTES** del `return` que se toma cuando aun
no han llegado los cinco componentes de `/odom`. Y eso **es correcto** —lo que vigilan es que el RVR
siga ENVIANDO, y «faltan componentes» no es «el enlace callo»: reiniciar el streaming no arreglaria
lo primero—. Pero la consecuencia es un estado que **no detecta nadie**, ni el vigilante de silencio
ni `rvr_responde`:

    estado                      latido    rvr_responde   /odom
    todo bien                   avanza    true           publica
    la Pi va y el RVR no        avanza    false          0 Hz    ✅ cubierto
    llegan 4 de los 5           avanza    true           0 Hz    🔴 nadie avisa

🔴 **Desde el muro del profesor ese robot se pinta VERDE con la odometria muerta** — la familia de
fallos de siempre, esta vez dentro del mensaje escrito para evitarla.

📌 **Y no es hipotetico: es el estado que no se pudo descartar el 2026-08-04.** Los cinco topics del
stream a cero, el RVR contestando a consultas y el vigilante callado. Se cerro apagando el robot, asi
que **nunca se supo si faltaban todos los componentes o solo uno**.

✅ **Cerrado con `float32 antiguedad_odom_s`**, un tercer reloj que se pone **despues** del `return`,
o sea que solo avanza cuando un `/odom` se completa de verdad:

    antiguedad_muestra ~0  ·  antiguedad_odom CRECE  ->  faltan componentes
    las dos crecen                                   ->  el RVR callo

⚠️ **Y no valia un `odom_completo: bool`**, que era la solucion obvia: `_recibidos` **se vacia en
cada ciclo** y los componentes llegan asincronos a 16,5 Hz, asi que en un instante cualquiera esta
medio lleno **con el robot sano**. Muestreado a 1 Hz diria «incompleto» casi siempre.
📝 **Hay que medir cuanto hace que se completo uno, no si lo esta ahora.** Es la misma forma que ya
mordio con `ps -o %cpu` y con `spin_once`: **una foto instantanea de algo que oscila no dice nada**.

Se metio **antes** de fusionar, a proposito: el `.msg` obliga a `rm -rf build/ install/` del paquete
y ~4,5 min de compilacion, asi que hacerlo despues habria costado dos recompilaciones. Diff
puramente aditivo, `py_compile` OK, **NO VERIFICADO**.

---

## 2026-08-04 (parte 7) — Las pantallas. La app se puede abrir y mirar. 173 -> 250 pruebas

`atriz-lab`, `main`. Cinco rutas (`/`, `/flota`, `/robot/[id]/{diagnostico,telemetria,conducir}`),
sus componentes, y una capa pura nueva en `lib/interfaz/` con **77 pruebas**: toda la logica
probable vive ahi y los componentes solo dibujan.

### 🔴 La regla de «lo que la interfaz no puede decir» dejo de ser texto

`lib/interfaz/lenguaje.ts` tiene una prueba que **abre los ficheros de `componentes/` y `app/`** y
falla si aparece «parada activa», «led encendido», «robot averiado», «color cambiado» o «latencia»
— sin acentos, sin distinguir caja, y saltandose los comentarios para que siga siendo posible
explicar por que estan prohibidas.
✅ **Comprobado rompiendolo:** metiendo «La parada activa esta puesta y el LED encendido» en un
componente, la prueba falla **nombrando el fichero y las dos frases**. Retirado, verde otra vez.
📝 Es el primer sitio del proyecto donde una leccion de CLAUDE.md se convierte en una comprobacion
que corre sola, en vez de en un parrafo que hay que acordarse de leer.

### Verificado por el EFECTO, no por que compile

El agente levanto `npm run dev`, **condujo Edge headless por CDP** y **escribio un rosbridge falso a
mano** (RFC 6455, sin instalar nada) para no quedarse en `SIN_CONEXION`. Medido en pantalla y en el
cable: las 5 rutas dan 200 y `/robot/99` da 404 · 8,29 V y 27,5/28,3 °C con su antiguedad ·
`antiguedad_atasco_s = -1` sale como **«no se sabe»**, no «sin atasco» · `SIN_DATOS` pinta **ambar**
(`rgb(246,168,35)`, no el rojo) y lista **las tres causas sin elegir** · la parada sin enlace dice
**«LA PARADA NO SE HA ENVIADO»** con el motivo real · **0 subscribes con `qos`** · **0
publicaciones en `/cmd_vel`** · 14 twists en `/cmd_vel_raw` a ~10 Hz con el cero al soltar ·
cambiar de robot **cierra un socket y abre otro**.

Y un fallo real encontrado asi: un aviso de hidratacion porque **el modo oscuro forzado del
navegador reescribe los `style` en linea**. La muestra de color de los LEDs paso a ser una clase.

### 🔴 La portada era una maqueta que decia «Sistema operacional»

`/` renderizaba `Dashboard` de `src/components/`: **1134 lineas con datos inventados**, cero `fetch`
y cero `WebSocket`. O sea que lo PRIMERO que veia cualquiera al abrir la aplicacion era **la peor
familia de fallos de este proyecto** —una pantalla que parece sana sin haber hablado con nada— en la
portada, y con un cartel afirmando que el sistema esta operativo.
→ Portada nueva: enumera lo que existe, enlaza los 16 robots y el muro, y **dice lo que no
  funciona** (el terminal, la autenticacion, y que nada aqui confirma un efecto fisico).
  Las maquetas **no se borran** —su destino esta sin decidir— pero al dejar de importarlas quedan
  sin referenciar, que hace la decision barata en los dos sentidos.
→ Y los seis motivos del muro llevan ya **acentos**: son texto visible. Al cambiarlos fallaron tres
  pruebas, que es **lo correcto**: comparan contra el literal y no contra la constante.

### El comprobador de contrato ya dice contra que rama compara

Lee el arbol de trabajo de `Atriz_rvr`, asi que su veredicto depende de en que rama esta ESE
repositorio — y no aparecia por ningun lado. Con la rama `feat/estado-robot` puesta dio rojo
diciendo «solo en el ROBOT: /estado_robot», sin mencionarla; y **la salida natural —añadir el topic
a `contrato.ts`— habria sido el arreglo equivocado**. ✅ Comprobado en los dos casos.

### Lo que NO se construyo, con su motivo

- **`FRENANDO`**: saldria de `/collision_monitor_state`, cuyo `action_type` este proyecto **no ha
  caracterizado** y cuyo caudal nadie ha medido. En vez de un estado apoyado en una suposicion, el
  hueco **se declara en pantalla**. Se desbloquea midiendo esas dos cosas en el robot.
- **La vista del LIDAR**: `/scan` no esta modelado en `useTopic`, y modelarlo exigia editar
  `hooks/`, que el encargo protegia.
- **El terminal**: bloqueado por la F0.

---

## 2026-08-04 (parte 6) — La capa 1 de la app: hooks y modelo de flota. 97 -> 173 pruebas

`atriz-lab`, `main`, commit `0d23e89`. Lo puro en `lib/flota/` (`resumen.ts`, `presupuesto.ts`) y la
capa fina de React en `hooks/`. **`lib/rosbridge/` no se toco** — `git diff` sobre ese directorio
sale vacio.

**+76 pruebas, y 16 mutaciones aplicadas, 16 detectadas.** Una destapo un fallo de las propias
pruebas: con `TEXTO_SIN_SENAL` cambiado a «robot averiado» seguian verdes, porque comparaban contra
la constante y no contra la cadena. 📝 **Una prueba que compara contra la constante que el codigo usa
no prueba el texto: prueba que dos sitios leen la misma variable.**

### 🔴 Y un hallazgo que corrige un encargo mio, y vale como regla general

**UN UMBRAL DE SILENCIO EN MILISEGUNDOS NO ES TRANSFERIBLE ENTRE TOPICS DE RITMOS DISTINTOS.**

Mi encargo decia «el muro usa `evaluarSalud()`». Habria producido **un muro roto**: sus 3000 ms
estan calibrados contra `/odom` a **16,5 Hz**, o sea **50 mensajes perdidos**. El muro del profesor
no puede pagar `/odom` (13,05 kB/s x 16 = 209) y solo tiene `/motor_status` a **1 Hz**, donde los
mismos 3000 ms son **TRES** mensajes: **las 16 baldosas «sin señal de vida» al primer hipo de WiFi**,
que es exactamente el falso positivo que ese codigo existe para evitar.
→ El umbral se piensa en **mensajes perdidos** y se traduce con el periodo de **su** topic. Quedan
  dos constantes (`UMBRAL_SILENCIO_MS` 3000 · `UMBRAL_LATIDO_MURO_MS` 5000) **con una prueba que
  impide unificarlas**.
→ 📝 Misma familia que «`ps -o %cpu` da el promedio» y que los 11,3 Hz de `spin_once`: **una cifra
  correcta en su contexto se vuelve falsa al mudarla de sitio.**

### Lo que queda sin probar, y esta dicho

- **El cableado de React** (~10 lineas por hook: `useState`, `useMemo`, arrays de dependencias, el
  proveedor). No hay `jsdom` ni `@testing-library` y **no se instalan**. Riesgo concreto: que cambiar
  de robot **no re-monte la conexion**. Se comprueba a mano en el navegador.
- **Nada contra un robot real**: todo contra el doble de WebSocket.
- El `as` de `useTopic` es **aserción, no validación**.
- `Transporte` no tiene `alAbrirse`, asi que «conectado» se **muestrea** cada 500 ms.

⚠️ Y un efecto colateral que costo un rojo: el agente del driver dejo `Atriz_rvr` **en la rama
`feat/estado-robot`**, y `npm run contrato` compara contra el arbol de trabajo de ese repositorio.
Salio en rojo por `/estado_robot`. **Devuelto a `ros2` y verde otra vez.** 📝 Un comprobador que lee
un repositorio hermano depende de en que rama esta ese repositorio — y eso no se ve en el mensaje de
error.

---

## 2026-08-04 (parte 5) — Las tres señales que le faltan al robot, escritas y SIN VERIFICAR

Rama **`feat/estado-robot`** de `Atriz_rvr`. 🔴 **`ros2` intacta en `65ad124`** — el codigo no se
puede probar sin robot, y tocar el driver a ciegas es donde este proyecto se ha hecho daño.

Un solo topic, `/estado_robot` a 1 Hz (`atriz_rvr_msgs/EstadoRobot`), con lo que la interfaz web
necesita y hoy no existe:

    uint64  latido                  la señal de vida DEL NODO
    bool    parada_emergencia       la bandera del driver, que hoy no sale
    bool    rvr_responde            distingue «la Pi va y el RVR no» de «no llego a la Pi»
    float32 antiguedad_muestra_s    -1.0 = «no se sabe», nunca «cero»
    uint32  reanudaciones_fallidas  distingue CARGANDO de DORMIDO

El diff toca **4 lineas existentes** —la lista blanca, el reflujo de un `import` y un rotulo—; todo
lo demas es añadido, y el metodo nuevo va entero dentro de `try/except`.

🔴 **Y el encargo estaba MAL, lo encontro quien lo implementaba.** Yo dije que
`reanudaciones_fallidas` se apoyara en `_t_ultima_muestra`. Ese campo lo reinician **tambien**
`_conectar_rvr` y `_recuperar_streaming`, asi que significa «hace poco que paso algo», no «hace poco
que llego un dato» — y con el RVR apagado una reanudacion habria parecido un exito. O sea **el fallo
del 2026-08-02 reproducido dentro del campo escrito para detectarlo**. Resuelto con un espejo que
solo tocan los manejadores.

⚠️ **Y sospeche un segundo fallo que NO existe**, conviene decirlo: `g_salud` es
`MutuallyExclusiveCallbackGroup`, asi que temi que el keepalive bloqueara el latido justo cuando el
RVR esta muerto. **No pasa**: `_keepalive` y `_vigilar_silencio` usan `_enviar`, que es
fire-and-forget, no `_pedir`, que si bloquea 5 s. El driver ya tenia esa distincion hecha a
proposito.

⚠️ **Lo que hay que mirar al fusionarlo NO es el topic nuevo: es que `/odom` e `/imu` sigan
publicando.** El riesgo de este parche es llevarse por delante la telemetria, no fallar en lo suyo.
Y un `.msg` nuevo **no basta con `colcon build`**: hay que borrar `build/` e `install/` del paquete.

📝 Y tres cosas que quedan dichas y no medidas: los umbrales «1-2 / >2» **no estan calibrados**, el
coste «0,03 kB/s» es **aritmetica**, y el `TRANSIENT_LOCAL` del latido hace que un suscriptor nuevo
reciba el ultimo valor latcheado — **la interfaz tiene que comparar DOS lecturas**, una sola no dice
nada.

---

## 2026-08-04 (parte 4) — El auditor de documentacion no corria en el PC, y mentia

Dos fallos suyos, los dos **solo en Windows**, encontrados al pasarlo desde el PC por primera vez.
Van **cuatro** fallos propios del auditor: nacio con tres falsos positivos y aqui salen dos mas.

1. 🔴 **Reventaba entero al imprimir el primer emoji.** La consola de Windows es cp1252 y
   `UnicodeEncodeError` mataba el script **antes de decir una sola conclusion**. Nacio en la Pi, que
   es UTF-8, y desde hoy se trabaja tambien desde el PC.

2. 🔴 **Y el peor, porque daba un veredicto FALSO: una exclusion que existia y no hacia nada.**

       if 'CHANGELOG' in rel or '00_auditoria/evidencia' in rel:   # se salta las bitacoras

   En Windows `os.path.relpath` devuelve `00_auditoria\evidencia_24_04\...` con **barra
   invertida**, asi que el `in` daba `False` y el auditor **delataba las bitacoras como deriva**.
   Resultado: denunciaba «91 comprobaciones» en una evidencia del 2026-07-31, que es exactamente lo
   que esa evidencia **debe** decir — es memoria, no deriva.
   → Es la familia de fallo mas repetida de este proyecto: **una comprobacion que existe y no hace
     nada**, como `chmod` en `/boot/firmware` o `usercfg.txt` en 24.04. Y aqui con agravante: es el
     fallo que este auditor existe para no cometer. **Un verificador con falsos positivos se acaba
     ignorando, y eso es peor que no tenerlo.**

✅ **Comprobado por el efecto**, sin `PYTHONIOENCODING` y desde el PC: **0 problemas** donde antes
salia 1, y codigo de salida 0.

---

## 2026-08-04 (parte 3) — La web movio el robot, y la app ya tiene estructura

**Primera vez en el proyecto que el cliente web mueve un robot real.** 60 cm, con el codigo de
produccion de `atriz-lab` sobre el mismo WebSocket que usara el navegador. Evidencia 70.

    barrido listo en 1.48 s   <- arrancarBarrido() espero un /scan REAL
    MOVIENDO 0.20 m/s x 3 s
    desplazamiento segun odometria: 59.7 cm
    el barrido se apago solo al terminar

Se pudo ejecutar el cliente REAL desde Node porque el nucleo **no importa React ni nada del
navegador** — una decision del primer dia que hoy pago.

⏳ **La T9 NO esta cerrada:** falta la medida con CINTA y el control por SSH, y falta publicar la
PARADA DE EMERGENCIA con el robot en marcha mirando el log del driver.

### Los siete hallazgos del cliente, cerrados

Seis salieron de revisar el PR contra el robot real y uno de medir rosbridge. 87 -> **97 pruebas**.
El mas instructivo es el segundo, porque el arreglo anterior se habia quedado a medias:

🔴 **`confirmaEfecto()` prometia un efecto que este proyecto midio que NO ocurre.** El arreglo previo
miro la FORMA del `.srv` y marco como «sin confirmacion» los cuatro de respuesta vacia. Pero los
otros cuatro devuelven `bool success`, y en el driver ese campo es `resp.success = ok`, donde `ok`
significa **«la corrutina del SDK no lanzo»**, no «el LED cambio». Y hay un caso medido:
`undercarriage_white` devuelve `success=True` **sin encender nada**.
→ El tipo pasa a ser `'NINGUNA' | 'SOLO_QUE_NO_LANZO'`, **sin ningun miembro que diga «confirma»**:
  hoy es estructuralmente imposible que la interfaz prometa un efecto fisico.

Los otros seis: `arrancarBarrido()` ya escucha la caida del enlace y **deja de acusar al LIDAR**;
`tipoDe(topic)!` **lanza** en vez de mandar un `subscribe` sin tipo —el mismo silencio que costo el
`Encoders`—; `ACCIONES` deja de ser codigo mudo y el comprobador **dice** que no compara el glob de
acciones; la rama fina de `salud.ts` queda documentada como acoplamiento, no como fallo;
`opSubscribe` **ya no acepta `qos`** (ver abajo); y `opCallService` manda el `timeout` en el propio
op, con el plazo local por encima, **para que gane siempre el motivo real de rosbridge**.

### Y el diseño que faltaba: la estructura de la aplicacion

`00_auditoria/planes/2026-08-04-estructura-app-web.md`. La capa de datos existia y estaba probada;
**la aplicacion nunca se habia diseñado**. Rutas, ficheros, modelo de conexion, la vista del
profesor, el terminal, los estados de la interfaz y el orden de construccion.

🔴 **Y una medida que decide el diseño de la vista del profesor:** `throttle_rate` **no sirve** para
limitar el ancho de banda por cliente. `subscribe.py:225` hace `min(f("throttle_rate"))`: **gana el
cliente mas rapido, para todos**. Un profesor que pida 1 Hz recibira a 16,5 en cuanto un alumno este
suscrito sin limite en ese robot.
→ El muro del profesor se suscribe **solo a `/battery_state` y `/motor_status`**: 0,48 kB/s por
  robot, **7,7 kB/s los 16**. Con `/odom` serian 1,7 Mbit/s y con `/scan` **10,3**.
→ 🔴 **Pero asi no puede saber si un robot esta VIVO**, porque `/motor_status` llega republicado con
  el ultimo valor conocido y llega igual con el RVR mudo. Se cierra con **un `/latido` a 1 Hz en el
  driver**: 0,5 kB/s los 16.

📌 **Tres señales que el driver NO publica y sin las cuales la interfaz tiene que decir «no lo se»**:
el latido, la bandera de parada, y un «estoy cargando». Aparecieron por separado; juntas son la
lista de la compra del lado robot.

---

## 2026-08-04 (parte 2) — Nueve repositorios, y el público repartía el sistema muerto

Inventario completo del ecosistema, en [`03_operacion/REPOSITORIOS.md`](03_operacion/REPOSITORIOS.md).
Existe porque **la confusión entre repositorios ya costó tiempo real**: el día anterior se auditó
«el repositorio de la web» sin decir cuál de los tres era ni sobre qué rama, y dos auditorías
correctas llegaron a conclusiones opuestas.

**Son nueve, entre dos dueños** — cinco de `Bura-hub` y cuatro de la organización `atriz-udenar`,
de los cuales **tres son de solo lectura** (`admin: false`, comprobado por API): no son nuestros
para reorganizar.

### 🔴 El hallazgo, y no lo esperaba nadie

**`ATRIZ` es la única puerta pública del proyecto —tiene una estrella, o sea que alguien lo
encontró— y sus dos submódulos apuntaban al sistema muerto:** `driver_ros_node` a la rama `main` de
`Atriz_rvr`, que es **ROS 1 y no compila con `colcon`**, y `frontend_and_backend` a
`Atriz_web_server`, la plataforma abandonada **con credenciales dentro**. Quien llegara y clonara con
`--recursive` **se llevaba el stack antiguo entero**.

Corregido: el submódulo apunta ahora al driver en la rama `ros2` y a su punta actual, el de la web
se retiró, y el README dice dónde vive hoy cada componente. **Verificado por efecto**, clonando con
`--recursive` como lo haría un tercero: trae `heads/ros2` y paquetes `ament`.

Y se añadió al README el aviso que faltaba: **los dos PDF de `docs/` describen la arquitectura
ANTERIOR a la migración**, con funcionalidades descartadas después —entre ellas la transmisión de
vídeo, porque **los robots no llevan cámara**—.

### Lo demás

- **`atriz-udenar/ros_sphero_rvr` archivado.** Driver de ROS 1 (`catkin`, `rospy`), superado por
  `Atriz_rvr` rama `ros2`. Queda como registro, sin que nadie lo confunda con código vivo.
- ✅ **`Atriz_web_server` archivado — y en el orden correcto: DESPUÉS de que el usuario rotara.**
  Archivar deja el repositorio en solo lectura y **no cierra ninguna exposición**: los secretos
  siguen en el historial. **Rotar es lo único que lo cierra**, igual que se midió con las ramas de
  `Atriz_rvr` — borrar no cerró nada.
  📝 Y una comprobación que salió bien por hacerla: **la primera llamada a la API falló**
  (`Problems parsing JSON`, por el guion largo de la descripción al pasar por el shell) y el
  repositorio **siguió activo**. Se detectó porque se releyó el estado en vez de fiarse de que la
  orden se hubiera enviado. **Comprueba el efecto, no el código de salida** — van siete.
  ⚠️ Consecuencia: un repositorio archivado no admite escrituras, así que **purgar el historial
  exigiría desarchivarlo primero**. Con `forks = 0` sería efectivo, pero es higiene: la exposición
  ya está cerrada.
- **Nombres: propuesta registrada y NO aplicada**, por decisión del usuario. La que importa es
  `Atriz_migracion_ros2` → `atriz-ingenieria`: **nombra un evento temporal, no un propósito**, y el
  día que la migración acabe el nombre miente. El coste no es técnico —GitHub redirige— sino las
  decenas de referencias en la documentación y en los clones de la Pi.

---

## 2026-08-04 — El cliente de rosbridge, escrito y revisado hasta el hueso

Primera pieza de código de la Fase 5, y la única que ninguna medición pendiente puede invalidar.
Vive en **`atriz-lab`** —que pasa a ser **el** repositorio de la web, y a privado—, **fusionado en
`main`** por el PR #1 (merge `42e5895`). La rama `cliente-rosbridge` se borró tras comprobar que
`main` la contenía entera y que la batería pasaba sobre el resultado fusionado.

Cinco módulos en `frontend/src/lib/rosbridge/`, **sin un solo import de React ni de Next**, para
probarlos en Node sin navegador y sin robot: `contrato`, `salud`, `protocolo`, `transporte`,
`teleoperacion`. **87 pruebas**, `tsc` y `eslint` limpios, y `herramientas/comprobar_contrato.mjs`,
que compara la lista blanca de la web con `robot.launch.py` **del repositorio del robot** y **falla
si divergen** — probado rompiéndolo.

### 🔴 Lo que NO está hecho, y es lo que decide si esto sirve

**Nada de este núcleo se ha ejecutado nunca contra un robot ni en un navegador.** Faltan las tareas
8 y 9 del plan: medir qué acepta rosbridge **2.7.0** (no el upstream), cerrar los quince tipos con
`ros2 topic type`, y **la prueba con cinta métrica**. La revisión final lo dijo con estas palabras:
los defectos corregidos son **«trampas armadas esperando al primer consumidor»**.

### El método, que es lo que vale para la próxima vez

Siete tareas, cada una con implementador y **dos revisores independientes** —uno tras la
implementación y otro acotado tras cada arreglo—, más una revisión final de toda la rama con el
modelo más capaz. A los revisores se les exigió **ejecutar sondas y romper cada arreglo** para
comprobar que su prueba falla. Ocho rondas de arreglo; **en seis de ellas el arreglo abrió otro
hueco**, y las seis las cazó la misma instrucción: *«busca lo que este arreglo pueda haber roto»*.

### 📝 Veinte defectos del plan, y ninguno se encontró releyéndolo

Los veinte salieron de **ejecutar** algo. Los que dejan lección:

- **Una prueba en verde sobre una ficción.** Se diseñó un canal de avisos apoyado en el `status` de
  rosbridge, con una prueba que lo inyectaba por un doble. **rosbridge 2.7.0 no manda ese mensaje
  jamás**: `Protocol.log()` escribe en el logger del nodo y ahí acaba. Verificado en el fuente.
- **Un fallo real sustituido por una conjetura.** `result: false` se resolvía como éxito, así que el
  motivo que manda el robot se tiraba y ocho segundos después el alumno leía *«puede que el LIDAR no
  haya arrancado»*. **Mide antes de atribuir, al revés, y escrito en el mensaje que ve el alumno.**
- 🔴 **Transcribir fielmente una fuente equivocada da un ✅ perfecto.** Una revisión comparó
  `contrato.ts` carácter a carácter contra el plan y aprobó mientras el tipo de `/encoders` estaba
  mal —`Encoders` en vez de `Encoder`—, **porque el plan también lo estaba**. Lo encontró el usuario
  contra el robot. → **Un plan que trae el código escrito traslada sus errores intactos al
  repositorio.** El plan quedó marcado en rojo: *ya se ejecutó, y sus bloques reproducirían los
  defectos*.
- **`publicar()` perdía una parada de emergencia en silencio**, y **`cerrar()` no cerraba**: dejaba
  un socket vivo recibiendo `/scan` que nadie sabía que existía. Cuatro críticos que ninguna
  revisión por tarea podía ver, porque **ninguno vivía dentro de un solo módulo**.

### Decisión cerrada

**La web es un TALLER PRESENCIAL sin SSH**, no un laboratorio remoto: las diez prácticas miden con
cinta y transportador, y «sin cámaras» impide que un alumno en casa vea si el robot chocó. Lo remoto
se aplaza **con su condición escrita**. Revisión del plan, decisión 17.

### 👤 Pendiente, y es suyo

Rotar la **`SECRET_KEY`** de `Atriz_web_server` (está en las **tres** ramas de un repositorio
público) · las tareas 8 y 9 con el robot · y, tras la reescritura de historia para quitar las
coautorías, en la Pi: `git -C ~/atriz_migracion status` y luego `fetch` + `reset --hard origin/main`.

---

## 2026-08-04 — El LIDAR estaba muerto y el robot parecía sano

Cierra el `/start_scan → result:false` que la evidencia 68 §6 dejó abierto con «la causa está en
el robot». Lo era, y no era el servicio.

**El nodo del X2 tenía el descriptor muerto.** Abre su puerto una sola vez al arrancar y no lo
reabre nunca. El X2 se alimenta del RVR, así que apagar y encender el robot re-enumera su
adaptador USB: udev rehace `/dev/ydlidar` correctamente y **nadie se lo dice al proceso**.

```
nodo del lidar, fd 29  ->  /dev/ttyUSB0 (deleted)     <- descriptor MUERTO
proceso arrancado      ->  Aug  3 15:31:56
/dev/ttyUSB1 creado    ->  Aug  4 00:29:34            (nueve horas después)
```

De ahí salen los tres síntomas en cadena: `turnOn()` escribe en el fd muerto, el bucle sondea y
falla (`Failed to get scan` a 20 Hz), y rosbridge se rinde a los 5 s con un `result:false` cuyo
texto —«Timeout exceeded while waiting for service response»— **es suyo, no del robot**.

🔴 **Y todo esto con `systemctl` en `active`, el nodo vivo, sus servicios contestando y `/odom` a
16,58 Hz.** Misma familia que el RVR dormido con el nodo vivo. Sin `/scan` el `collision_monitor`
no deja conducir, así que el robot «no obedece» sin ninguna señal de avería.

📝 **La pista la puso el usuario**, no el análisis: *«seguramente es debido a la forma de arranque,
hay una forma en la que el lidar va y otra no»*. Era eso, con un matiz — no es cómo se arranca el
stack, es **cuándo respecto al robot**.

✅ Arreglado con `sudo systemctl restart atriz-robot` y verificado por efecto: fd vivo, 0 errores,
`/scan` a **11,90 Hz**.

⏳ **Que se recupere solo está SIN HACER**, y con 16 robots va a volver. Dos opciones sin decidir
en la evidencia 69 §6. Un `Restart=always` no sirve: el proceso no muere.

### 🔴🔴 Y la causa raíz, que no era ninguna de las dos: `set -e` + `(( t++ ))`

Los dos apartados de abajo dan por hecho que el launch muere mudo «porque falta
`/dev/ydlidar`». Es verdad a medias. **`atriz-robot.sh` ya tenía una espera con su mensaje de
error, y no se ejecutaba nunca.** Reproducido aislado:

```bash
set -euo pipefail
esperar() { local t=0; while [[ ! -e $1 ]]; do sleep 1; (( t++ )); done; }
# → código de salida 1 · duración 1 s · ni el 🔴 ni el final del script
```

**`(( t++ ))` devuelve el valor ANTERIOR de `t`.** Con `t=0` eso es `0`, falso en aritmética →
estado de salida **1** → `set -e` mata el script en la primera vuelta. El «1 segundo» del
síntoma es literalmente el `sleep 1` de esa vuelta.

Las tres consecuencias, activas desde que se escribió:

- la espera de **60 s** para que udev cree los enlaces **nunca ocurrió**
- el mensaje `🔴 /dev/ydlidar no apareció en 60s` era **inalcanzable**
- systemd solo veía `status=1/FAILURE`, **sin una línea de explicación**

🔴 Y lo que lo hace peor: **la salvaguarda estaba escrita contra el fallo que acabó causando.**
Su comentario dice *«sin esto el launch arranca, no encuentra el puerto y el nodo queda vivo y
mudo — el fallo más caro de diagnosticar de este proyecto»*.

✅ Arreglado con una asignación (`t=$(( t + 1 ))`) y **verificado por efecto**: con `ESPERA_HW=3`
y un dispositivo inexistente ahora **espera 3 s y escribe el mensaje**; antes moría en 1 s en
silencio. Buscado el patrón en **todos** los scripts con `set -e`, no solo en el que falló: una
sola aparición.

✅ **Y el diagnóstico del puerto se movió a donde ocurre el fallo.** Que el mensaje viviera solo
en `verificar_robot.sh` no basta: el modo de fallo es que el arranque muere y **nadie ejecuta el
verificador después**. Ahora lo escribe `atriz-robot.sh` en el journal, en el momento, con las
dos ramas ejercitadas.

### Puerta nueva en `provision.sh`: ¿casa la regla en ESTE robot?

El `ID_PATH` lleva el prefijo **de la placa** (`platform-fd500000.pcie-pci-0000:01:00.0`): con
una Pi de otra revisión no casa **en absoluto**, y el síntoma sería idéntico. Con la decisión de
puerto fijo eso deja de ser una nota. `provision.sh` lo comprueba tras instalar la regla, **por
efecto** (¿existe el enlace?) y no por que el fichero se copiara, y distingue las dos causas —que
piden cosas opuestas—: prefijo de placa distinto → la regla **no es clonable**, hay que generarla
en `first-boot.sh`; mismo Pi y otro sufijo → **mover el cable**. Suma a `FALLOS`, así que el
aprovisionamiento no acaba en verde con un robot que no tendrá `/scan`.

### Y el segundo fallo del mismo episodio: el puerto USB físico

Al intentar recuperar el robot se movió el LIDAR de conector **buscando que volviera a ser
`/dev/ttyUSB0`**. Ese número **no importa** —lo asigna el kernel por orden de aparición— y la
regla udev existe justamente para hacerlo irrelevante: el nodo abre `/dev/ydlidar`. Lo que
importa es el conector, porque la regla casa por `ID_PATH`.

```
la regla exige:   ...usb-0:1.2:1.0
estuvo en:        ...usb-0:1.1:1.0  ✗   y luego  ...usb-0:1.4:1.0  ✗
volvió a:         ...usb-0:1.2:1.0  ✅  ->  /dev/ydlidar apareció solo
```

🔴 **Y el síntoma vuelve a no parecerse a la causa:** sin `/dev/ydlidar` el launch **muere en
~1 s sin imprimir una palabra**, y el único error visible es del `ExecStartPost` —«`/stop_scan`
no respondió en 30s. ¿está corriendo robot.launch.py?»— que manda a mirar el launch. systemd
reintenta 3 veces y se rinde con `Start request repeated too quickly`, que exige `reset-failed`.
**Costó cuatro intentos de cable.**

✅ **Arreglado en `verificar_robot.sh`**, y ejercitando la rama de fallo, no solo la buena:

```
✗ el LIDAR esta en el PUERTO USB 1.4, y la regla udev espera el 1.2
   → MUEVE EL CABLE al conector 1.2 (cual es, en FLOTA.md). NO toques la regla:
     es la misma en los 16 robots
```

Y una segunda aserción para el descriptor muerto, que ninguna comprobación de «¿existe el
fichero?» puede ver: `✓ el nodo del LIDAR tiene un descriptor vivo (no re-enumerado)`.

👤 **DECIDIDO: el puerto fijo se mantiene, y el lidar va en el mismo conector en los 16.** Se
ofreció la alternativa —quitar el `ID_PATH` y casar solo por `10c4:ea60`, que es inequívoco
porque **hay un único dispositivo USB-serie** en el robot (el RVR habla por `ttyAMA0`, el UART
del SoC)— y se descartó por coherencia con la imagen dorada. **Consecuencia asumida: la foto del
conector en `FLOTA.md` pasa de recomendable a obligatoria, y sigue sin existir.**

### Dos veces que mintió el instrumento, en el mismo diagnóstico

- **`ros2 service call` dio 4,6-6,5 s para `/start_scan`** y se llegó a escribir que rozaba el
  tope de 5 s de rosbridge. **Falso:** arranca un nodo y hace descubrimiento en cada llamada. Con
  un cliente WebSocket ya conectado —el camino real de la web— son **1,4-2,1 s**, `result:true`
  6 de 6. Retractado en el acto. Van cinco.
- **El primer cliente WebSocket dijo «rosbridge no contesta en 15 s»** con las suscripciones
  funcionando (46 mensajes de `/odom` en 3 s). No era rosbridge: `probar_rosbridge.recibir()`
  devuelve la tupla `(payload, opcode)` y se le pasaba entera a `json.loads`, que lanzaba dentro
  de un `except: continue`. Lo destapó **mirar el journal del robot y ver que rosbridge no se
  había quejado de nada**.
- **Y una tercera al verificar el arreglo final:** el contador propio sobre el WebSocket dio
  «`/scan`: 0 mensajes en 8 s» con el LIDAR barriendo. Lo desmintieron el journal —«Real points
  251 > fixed points 250», o sea barridos de verdad— y un instrumento **distinto**:
  `ros2 topic hz /scan` = **11,97 Hz**.
  → La regla, en su forma más útil: **ante una medida rara el primer sospechoso es el medidor, y
  el desempate lo da un instrumento DISTINTO, no repetir el mismo.**

### Y un apunte para el cliente web, verificado en el rosbridge instalado

`call_service.py:92` — `timeout: float = message.get("timeout", self.default_call_service_timeout)`.
**El plazo de rosbridge lo puede fijar el cliente en el propio op**, y `opCallService()` de
`protocolo.ts` no lo manda: el `ms` de `Transporte.llamar()` solo arma un temporizador **local**,
así que subirlo no mueve la pared de los 5 s de rosbridge. Hoy no aprieta —ningún servicio medido
se acerca—, pero las dos paredes deberían moverse juntas.

---

## 2026-08-03 (parte 7) — Dos ramas muertas de `Atriz_rvr`, y un stash que ya sabía la respuesta

De las cuatro ramas remotas de `Atriz_rvr` quedan **dos**. Las otras dos se borraron hoy, y las
dos por motivos distintos.

### `migracion-ros2` — borrada, no perdía nada

Medido antes de tocarla: **ancestro estricto de `ros2`**, 73 commits por detrás, **0 commits
propios**. Su contenido es ROS 1 (`buildtool_depend: catkin`, 44 ficheros con `import rospy`,
0 con `rclpy`), o sea que el aviso que llevaba la documentación era correcto.

📝 **El nombre era la trampa: se llama «migracion-ros2» y no contiene una línea de ROS 2.**
Significaba «la rama DE la migración» —el ROS 1 sano del que se partió, con el UART a `/dev/rvr`
y el `interval` 250→60 ms que subió `/odom` de 3.85 a 16.59 Hz— no «la rama CON ROS 2». Cada vez
que se citaba había que gastar una línea en avisar. Una rama cuyo nombre necesita una advertencia
al lado ya no ayuda.

✅ Los dos commits que cita la documentación (`24c7749` y `67c8776`) **siguen alcanzables desde
`origin/ros2`**: ninguna cita se rompe.

### `wip/scripts-estudiantes` — borrada, y sí perdía algo, pero muy poco

Esta **no** era ancestro: 1 commit propio (`62e0313`), 3 ficheros. Era el rescate de un `git
stash` que solo vivía en la microSD, días antes de reflashear. De los tres ficheros, **dos eran
daño, no trabajo**:

| | Qué contenía |
|---|---|
| `02_girar.py` | el cambio entero es un typo de un pegado accidental: `del programa` → `del prograpythonma` |
| `11_sensor_avanzado.py` | menú recortado de 3 opciones a 1 **sin tocar el despacho**: dice «1. Modo Reacción» y al pulsar 1 ejecuta `calibrar_colores()` |
| `01_avanzar.py` | 🔴 el primer tutorial del curso, **reemplazado entero** por un `SeguidorBordeRojo` |

Y la decisión que aparcaba —«¿el seguidor a su propio fichero y se restaura el tutorial, o se
descarta?»— **ya la contestaron los hechos**: hoy `origin/ros2` tiene `01_avanzar.py` como
tutorial y `seguidor_linea_pid_demo.py` en su propio fichero.

🔴 **Pero ese seguidor ya tenía el mecanismo que el proyecto re-derivó cuatro días después**
—signo por estado arrastrado, invertido tras N ciclos sin ver el borde—, y nadie lo cruzó contra
el rediseño del 2026-08-02. **Conservado en `CLAUDE.md`**, con el fragmento de código y la regla:
antes de diseñar algo que el proyecto ya intentó, busca los intentos anteriores, incluidas las
ramas WIP.

### ✅ Y la trampa que esto destapó, cerrada al día siguiente

```
origin/main   ros2 tiene 75 commits de más   ·   último: 2026-07-29
```

**Un `git clone` a secas de `Atriz_rvr` daba `main`**, que es ROS 1 y no tiene ninguno de los 23
commits del 2026-08-03. Es la misma trampa que hizo que las dos auditorías de `Atriz_web_server`
se contradijeran (parte 6).

**Cerrado el 2026-08-04** cambiando la rama por defecto a `ros2` (API de GitHub; `gh` no está
instalado en la Pi). Y **verificado por efecto, no por el 200 de la API** — clonando de verdad
sin `-b`:

```
$ git ls-remote --symref … HEAD   →  ref: refs/heads/ros2	HEAD
$ git clone --depth 1 …           →  rama: ros2 · 65ad124 · scripts/estudiantes/atriz.py presente · usa rclpy
```

📝 Y eso dejó **falsas** las cuatro advertencias «clona con `-b ros2` porque `origin/HEAD` apunta
a `main`» escritas unas horas antes: corregidas en `CLAUDE.md`, `INSTALACION.md` (×2), el manual
y el mensaje de fallo de `verificar_robot.sh`. El `-b ros2` se deja explícito en los ejemplos
—`main` sigue existiendo y sigue siendo ROS 1—, pero ya no se justifica con una razón que no es
cierta.

### Exposición de credenciales: no mejora, y conviene decirlo

Borrar dos ramas **no cierra nada**. Reproducida hoy la medición documentada
(`grep -c "Contraseña"` sobre los dos ficheros del curso, por punta de rama):

```
origin/main                     8      ← sigue sirviéndolas
origin/ros2                     0      ✅
origin/wip/scripts-estudiantes  8      ← borrada
```

El **historial** de `main` y `ros2` las conserva igual. 👤 **Rotar la PSK y la contraseña de
`sphero` sigue siendo lo único que lo cierra.**

---

## 2026-08-03 (parte 6) — Nadie fijó la rama, y por eso las dos auditorías se contradijeron

`Atriz_web_server` tiene **TRES ramas que son códigos distintos**, y `compare` entre ellas devuelve
**HTTP 404: no comparten ancestro.** `master` (2026-02-09, la que da un `git clone` sin argumentos),
`develop` (2026-02-10) y **`pruebas` (2026-02-16)**, que es la más nueva y la que cita toda la
documentación del proyecto con el commit `924d659` (`INFORME_AUDITORIA.md:5`, `TRASPASO.md:1103`,
`CHANGELOG.md:4560`). **Manda `pruebas`**: `git clone -b pruebas …`.

**Las dos auditorías midieron bien. Midieron ramas distintas y ninguna lo dijo.** La de la mañana
(el plan, escrito en la Pi) midió `pruebas`; la corrección de la tarde (parte 5, desde el PC) midió
`master`, porque eso es lo que da un `git clone`.

### Lo que queda retractado de la parte 5

Las cuatro afirmaciones que se declararon falsas son falsas **en `master`** y **ciertas en
`pruebas`**, medido:

| | `master` | `pruebas` |
|---|---|---|
| `PythonCode.vue` | 2895 B, `<textarea>`+Prism | **10913 B, importa Monaco de verdad** |
| `ExecuteCommand.vue` | 404 | **5598 B** |
| `raspberry_config.py` | 404 | **413 B** |
| `POST /robots/execute/` | no existe | **existe**, `command` por formulario |
| `include_router` sin `dependencies=` | 5 | **6** ← lo que decía el plan |

Y **dos endpoints que no había visto nadie**, en `pruebas` y `develop`: `POST /robots/stop/` y
`POST /robots/emergency-stop/`, los dos con `robot_ip` por formulario y **sin autenticación**. Una
parada de emergencia sin autenticar también es una parada que cualquiera puede dejar inservible:
entra en el inventario de la Fase B.

### Lo que NO depende de la rama, medido en las tres

- **La autenticación escrita y sin conectar.** `get_current_user` importado y nunca llamado, y los
  routers sin `dependencies=`, en `master`, `pruebas` y `develop`.
- 🔐 **La `SECRET_KEY` de firma de los JWT** (`core/security.py`) está en **las tres**. Es la
  credencial que importa: con ella cualquiera **forja un token válido**, así que cablear
  `get_current_user` no serviría de nada hasta cambiarla.
- El veredicto **«se rehace»**, que sale reforzado.

📝 **Matiz sobre la otra credencial:** el `.env` commiteado con la de PostgreSQL está **solo en
`master`** (404 en las otras dos) y apunta a `localhost`. Es limpieza, no puerta abierta. La parte 5
lo dio como del repositorio entero.

### 📝 La lección, y es de método

**Un repositorio sin rama fijada no es una referencia.** Este proyecto ya tiene documentada la
trampa de auditar un clon desincronizado —tres hallazgos falsos, el error más caro de su historia—
y esta es la misma con otro disfraz.

Y una segunda, más incómoda: **corregir un error generó otro, por tercera vez.** La corrección de la
tarde imprimió `default_branch=master` en su propia salida de verificación **y no lo usó**. Una
corrección es una afirmación: necesita fijar sus condiciones con el mismo cuidado que lo que corrige.

Evidencias 66 (con cabecera de corrección) y 67.

---

## 2026-08-03 (parte 5) — Los repositorios web, leídos de primera mano

> ⚠️ **LEER LA PARTE 6 ANTES QUE ESTA.** Todo lo que sigue se midió sobre la rama **`master`** sin
> decirlo, y `master` no es la rama que manda. Las cuatro afirmaciones que esta entrada declara
> falsas son falsas en `master` y **ciertas en `pruebas`**. Lo que sí se sostiene: la autenticación
> sin conectar, la telemetría falsa, la `SECRET_KEY` (está en las tres ramas) y el veredicto.

Primera sesión **desde el PC de desarrollo**, no desde el robot. Se pusieron al día los dos clones
(`atriz_migracion` iba 9 commits por detrás; `Atriz_rvr` ya estaba en el head de `ros2`) y apareció
un **tercer repositorio** que el plan de la Fase 5 no conocía: `Bura-hub/atriz-lab`.

Al arrancar la Fase 5, lo primero era releer lo que el plan dice del repositorio de la web. El plan
declara en su propia sección 1 que se inspeccionó **«por la API de GitHub, sin clonarlo»**. Se
leyeron los ficheros.

### 🔴 Lo que se encontró leyendo (evidencia 66)

**Cuatro afirmaciones de la sección 1 del plan son falsas**, y una es la que más pesaba:

- **No hay Monaco.** `PythonCode.vue` son 2895 bytes y es un `<textarea>` con Prism.js. La única
  aparición de «Monaco» en el fichero es `font-family: "Fira Code", "Consolas", "Monaco"…` — **la
  tipografía de macOS**. `monaco-editor` está en `package.json` y no se importa nunca. Era **el
  único activo técnico que el plan daba por rescatable**: la Fase C sí parte de cero.
- **`POST /api/robots/execute/` no existe.** `robots.py` tiene dos rutas y ninguna es esa. El
  agujero real es `POST /scripts/upload/`, sin autenticación, y con tres defectos que el plan no
  vio: **inyección de argumentos** por `robot_ip` (un valor que empiece por `-o` lo interpretan
  scp/ssh como opción → código **en el servidor**), ruta fija `/tmp/user_script.py` en las **dos**
  máquinas, y `rosrun`, que es ROS 1.
- **`raspberry_config.py` da HTTP 404**, no el 200 que el plan afirma. No ha existido nunca.
- **Una cita entrecomillada «del código» no está en ningún fichero**: `simulad|desarrollo.tex` → 0
  coincidencias. La conclusión que sostenía —que el flujo de subida es teatro— **es cierta por otra
  evidencia**: `uploadScript()` no hace ni una llamada HTTP.

**🔐 Y dos credenciales NUEVAS en ese repositorio, que sigue público** (`private=False`,
`forks=0`): la de PostgreSQL en un **`.env` commiteado** y duplicada en `core/config.py`, y la
**`SECRET_KEY` de firma de los JWT** en `core/security.py`. La primera apunta a `localhost` y es de
desarrollo (limpieza); **la segunda importa: con ella cualquiera forja un token válido.** No estaban
en la lista de rotación, que solo vigilaba la PSK del WiFi y la contraseña de `sphero`.

### El hecho que unifica a los tres repositorios

**Ninguno ha hablado jamás con rosbridge.** Ni una línea de cliente: `atriz-lab` tiene **cero**
llamadas de red en todo `frontend/src`, y el viejo tiene **una**, el login. El único camino
web↔robot verificado del proyecto sigue siendo `03_operacion/probar_conexion_web.html`, escrito a
mano. → **La elección de repositorio pesa menos de lo que parecía**, porque el trabajo central no
está hecho en ninguno de los tres.

### Qué se hizo

- **Evidencia 66**, con el método (lecturas anónimas por `raw.githubusercontent.com`: la respuesta
  es a la vez el dato y la prueba de que el repositorio es público) y sin transcribir ningún valor
  de credencial, por la regla 5.
- **Sección 1 del plan corregida**, con el texto original conservado y marcado, para que no vuelva
  por la puerta de atrás.
- **`ESTADO_ACTUAL.md`**: fila nueva en los bloqueos y el aviso de la deriva.

### 📝 La lección, que ya estaba escrita en `CLAUDE.md` y volvió a morder

Un `grep` de una cadena suelta encuentra el ajuste **y lo que solo habla del ajuste**. Aquí cruzó
una dependencia declarada-y-nunca-importada con una `font-family` de CSS, y de ahí salió un activo
técnico inexistente. Es la tercera vez en el proyecto. **Y el correctivo es concreto: auditar un
repositorio por la API sin abrir los ficheros produce un inventario, no una medida.**

### Pendiente

- 👤 **Rotar** la credencial de PostgreSQL y sustituir la `SECRET_KEY`; borrar `.env` del
  repositorio. Con `forks=0`, purgar el historial aquí sí sería efectivo — **después** de rotar.
- 📝 **NO VERIFICADO dónde está la credencial de `sphero`** que `CLAUDE.md` da por expuesta en
  `Atriz_web_server`: no está en el código fuente propio (~33 KB), pero quedan 111 MB de
  `swarm_lab_env/` sin revisar. **No desmiente la exposición**: dice que no está donde se buscaría.
- El análisis de arquitectura de la Fase 5 (cuatro lentes independientes y sus escépticos) quedó
  **en marcha**, no cerrado.

---

## 2026-08-03 (parte 4) — Alinear el robot con el repositorio (bloque A)

Antes de replicar rvr-01 a los otros 15 hay que garantizar que **otro robot se pueda montar desde
cero solo con los repositorios**. Lo que exista únicamente en esta máquina se multiplicaría por 16.

Git estaba limpio: cero divergencia, cero sin commitear, cero sin empujar. El problema no estaba
en git — estaba en el hueco entre lo que el repositorio afirma y lo que hay instalado.

### 🔴 Lo que se encontró midiendo (evidencia 63)

**`atriz-nav.{sh,service}` NO estaban instalados.** Están en git, `fase_7_systemd.sh:237` los
instala, y `systemctl is-enabled atriz-nav` decía `not-found`. `atriz-robot.{sh,service}`
instalados divergían del repositorio (9 y 21 líneas, solo comentarios). Causa: `fase_7` no se
volvía a ejecutar desde el 2026-07-31 y las fuentes se editaron el 2026-08-03.
**Una imagen dorada hecha ese día habría salido sin navegación, en los 16 robots.**

**Y una anterior a esta ni siquiera habría tenido el dominio DDS bien.** Había **dos parsers** de
`robot_id.txt`: el de `first-boot.sh`/`verificar_robot.sh` anclado, y el de
`provision.sh`/`fase_7_systemd.sh` con `tr -dc '0-9' | head -c2`, que lee los dos primeros dígitos
del **fichero**, comentarios incluidos. La plantilla que escribe `fase_6` lleva «Rango válido:
01 a 16», así que el parser débil devolvía **`01` para cualquier `ROBOT_ID`**: los 16 robots en
`ROS_DOMAIN_ID=1`, viéndose todos entre sí, sin un solo error. Medido con las dos plantillas
extraídas de sus scripts (evidencia 64). En rvr-01 no mordía **por casualidad**: su ID es 01.

### Qué se hizo

- **`scripts/sistema/` + `MANIFIESTO.tsv`**, con un criterio sintáctico (A/B/C) para decidir qué
  se versiona: el repo tiene el **fichero** si el heredoc va entrecomillado y el contenido es
  igual en los 16; tiene solo el **generador** si interpola estado de la máquina. Los heredocs de
  `99-rvr.rules` y `cpu-performance.service` **se movieron, no se copiaron** — duplicarlos habría
  creado el mismo problema que esto viene a resolver. `wifi-no-powersave.service` NO se versiona:
  interpola `wlan0`, y una copia mentiría en el primer robot con la interfaz en `wlan1`.
- **`verificar_robot.sh` sección 13**, que compara **lo instalado** con el repositorio recorriendo
  el manifiesto. Probada rompiéndola: detecta `DIVERGE` ante una letra cambiada, `AUSENTE` con un
  fichero sin instalar, y **degrada a aviso** si no encuentra el repositorio (en un clon puede no
  estar). Y se le dio sufijo a la sección `9-H`: había **dos** numeradas 9.
- **Parser único** en los cuatro sitios, más la plantilla de `fase_6` sin dígitos en los
  comentarios — una plantilla que arma el fallo si alguien copia el parser viejo es una trampa.
  Y una aserción nueva: `ROS_DOMAIN_ID` efectivo **contra** `robot_id.txt`.
- **Puerta en `fase_6`**: si `verificar_robot.sh` falla, **no se prepara la imagen**. Probada con
  los tres códigos de salida. El 2 (solo avisos) **pregunta** en vez de bloquear: una puerta que
  siempre bloquea se acaba desactivando, y así es como muere un control.
- **Tres guardas que no guardaban**, arregladas y probadas *antes* de limpiar lo que no veían:
  `compilar.sh:76` miraba `src/*/build` —un nivel— y el parásito real estaba a cuatro;
  `fase_6:122` buscaba credenciales en tres rutas fijas y se le escapaba una **copia del token de
  GitHub** en `respaldo_pre_migracion/`; y `fase_6` paso 4 no limpiaba `~/.ros/log` (44 MB),
  `~/atriz_ws/log` (13 MB) ni los `build/` bajo `src/`.
- **Commits fijados** para el YDLidar-SDK y su driver ROS 2 en `provision.sh`: clonaba sin anclar
  nada, y el parche del driver se aplica con `patch -p1` — si upstream mueve esas líneas, falla o
  aplica con *fuzz* en el sitio equivocado.
- **`log/` estaba COMMITEADO** en este repositorio: 4 entradas de un `colcon version-check`.
  Fuera del índice y al `.gitignore`.
- **`~/src_externos/` (31 MB) borrado**, tras medir que era el upstream limpio y que la única
  diferencia con producción es el parche ya versionado (evidencia 65).

### Lo que se corrigió porque era falso

- `CHANGELOG.md` decía de `atriz-nav` «instalada pero NO habilitada». **No lo estaba.** Se deja la
  línea con una nota de corrección en vez de reescribirla: la bitácora registra lo que se creyó, y
  borrarlo perdería el aviso de que **escribir el instalador no es haberlo ejecutado**.
- 🔴 **`cfg80211.ieee80211_regdom=CO` está puesto y NO surte efecto.** El módulo lo recibe
  (`/sys/module/cfg80211/parameters/ieee80211_regdom` → `CO`) pero el firmware `brcmfmac` es
  *self-managed* y lo pisa: `iw reg get` dice **US**. Y **no lo escribe ningún script**, así que
  cada tarjeta saldría distinta. `preparar_tarjeta.sh` lo fija ahora de forma idempotente —no
  porque sirva, sino para que las 16 sean iguales— y el verificador compara el efecto con lo
  pedido. Hoy no rompe nada: 2.4 GHz está permitido en los dos dominios.
- **`~/.bashrc`**: sus líneas de ROS 2 no estaban versionadas en ningún sitio, así que un robot
  montado solo con los repositorios tendría shells **sin `ros2`**. Se creó
  `scripts/sistema/atriz-ros.sh` → `/etc/profile.d/atriz-ros.sh`, sin identidad dentro. De paso
  desaparece la trampa del «el `.bashrc` se lee después y gana», que el proyecto documentaba en
  cuatro sitios.

### Lo que NO se tocó, y por qué

`04_respaldo/configs/` **no es una copia desactualizada**: es la línea de retorno a Noetic de
`RECUPERACION.md:214-221`, y `README.md:120` ya la etiqueta «(del sistema viejo)». Sobrescribirla
con los ficheros actuales habría destruido el rollback. Tampoco se tocaron los `.bak` de Ubuntu y
de `flash-kernel`, ni los 16 binarios del YDLidar-SDK en `/usr/local/bin`, que parecen basura y no
lo son.

Y `LAB_BASE`/`LAB_OCTETO` en `red.txt.ejemplo` resultaron **no ser** una divergencia: son una
derivación opcional que `first-boot.sh:156` ya trata como tal, y el `.ejemplo` ya lo explicaba.

### Bloque B — ejecutado por el usuario, y medido (evidencia 63b)

`fase_7_systemd.sh` instaló los seis ficheros y se movieron los `.bak` de `/etc`. **Comprobado por
efecto, no por los `✓` del script:**

| | ANTES | AHORA |
|---|---|---|
| Pares repo↔sistema | 2 `DIVERGE`, 2 `AUSENTE` | **los 8 obligatorios `IGUAL`** |
| `atriz-nav` | `not-found` | `disabled` ← **el estado correcto**, no un fallo |
| `atriz-robot` | PID 699, `active` | **PID 699**, `active` — no se cayó al reinstalar encima |
| Verificador | 108 ✓ · 6 avisos · **7 FALLOS** | **120 ✓ · 5 avisos · 0 fallos** |

### 🔴 Dos mensajes falsos que destapó el ensayo del usuario

`--simular` existe para ver qué haría antes de hacerlo, y sirvió para exactamente eso:

- **«solo corre el driver del propio servicio (se reiniciará al aplicar esto)»** — **falso**.
  `fase_7` no tiene un solo `systemctl restart`. `install` cambia el inodo del fichero y
  `daemon-reload` recarga las unidades, pero **ninguna toca un proceso vivo**: el driver siguió con
  el código anterior (mismo PID 699). El mensaje hacía cerrar la sesión creyendo que el cambio
  estaba aplicado, y el fallo habría aparecido en el próximo reinicio sin nada que lo relacionara.
  Ahora avisa de que hay que reiniciar a mano, y de que eso despierta el robot.
- **«Instalado.»** aparecía también en `--simular`. Más barato de creer todavía: se lee el rótulo,
  no las líneas `[simular]`.

### Y una aserción mía que no podía fallar

La comprobación del puente del `~/.bashrc` hacía `bash -ic 'command -v ros2'`. El shell hijo
**hereda el PATH del padre**, y el verificador se lanza desde un shell con ROS cargado: pasaba con
el puente puesto **y sin él**. Se descubrió quitando el puente a propósito, no leyendo el código.
Corregida con `env -i`, y reprobada en los dos estados: ✓ con puente, ✗ sin él. **Quinto caso de
este tipo en el proyecto.**

### El `~/.bashrc`, cerrado del todo

El entorno de ROS pasó a `/etc/profile.d/atriz-ros.sh` (categoría A, versionado). En el `.bashrc`
queda **una línea** —el puente para `tmux`/`su`, que no leen `/etc/profile.d`— y la añade `fase_7`
de forma idempotente. El `.bashrc` **no se versiona**: pertenece a la distribución, así que por el
criterio del propio `scripts/sistema/README.md` es categoría B — se versiona el generador y se
asevera el efecto.

Con eso desaparece la trampa del «el `.bashrc` se lee después y gana», que estaba documentada en
cuatro sitios distintos.

### Pendiente

- 👤 **`red.txt` en 755**: la PSK del WiFi es legible por cualquier usuario. `chmod` no sirve (es
  FAT); van `fmask=0177,dmask=0077` en `/etc/fstab`. Es el único aviso del verificador que es una
  decisión tuya.
- 👤 **Rotar la PSK del WiFi y la contraseña de `sphero`** (sigue de antes).
- 📝 **NO VERIFICADO** — `provision.sh` no se ha recorrido de extremo a extremo en ningún robot: el
  SDK de rvr-01 se compiló a mano desde `src_externos` (md5 idéntico, y `~/YDLidar-SDK` no existe).
  El parser arreglado no se puede probar aquí: con `ROBOT_ID=01` los dos parsers coinciden. Y el
  puente del `.bashrc` se probó con `bash -lc`, no con un **`ssh` desde otra máquina**. Las tres
  cosas se comprueban en el robot 2.

---

## 2026-08-03 (parte 3) — El arranque de la navegación, decidido y a medio implementar

`ARQUITECTURA.md` arrastraba desde el 2026-08-02 una contradicción anotada: **nadie arrancaba
Nav2 ni AMCL**. `atriz-robot.service` levanta solo `robot.launch.py`, así que para navegar había
que entrar por SSH y lanzar dos launch a mano — y la Decisión 2, «el SSH ya no hace falta ni para
el ciclo de vida», era cierta **solo para teleoperación**.

### La decisión, y el dato que la tomó

**`atriz-nav.service`: una segunda unidad, instalada pero NO habilitada.** No fusionarla en

> 🔴 **CORRECCIÓN, 2026-08-03 (parte 4).** «Instalada» era **falso** cuando se escribió esta
> línea: `fase_7_systemd.sh` instala `atriz-nav.{sh,service}` pero **nadie volvió a ejecutarlo**,
> así que los dos ficheros estaban en git y **no en el sistema** —
> `systemctl is-enabled atriz-nav` decía `not-found`. Se midió al día siguiente:
> `00_auditoria/evidencia/63_alineacion_ANTES.txt`. Una imagen dorada hecha ese día habría salido
> sin navegación, en los 16 robots. Se deja la línea en su sitio con esta nota en vez de
> reescribirla: la bitácora registra lo que se creyó, y borrarlo perdería el aviso de que
> **escribir el instalador no es haberlo ejecutado**. Lo instalado de verdad se anota en la
> entrada de la parte 4. (`TRASPASO.md:25` decía «escrita, instalable y sin habilitar», que sí
> era correcto.)

`robot.launch.py` con un argumento —acoplaría los ciclos de vida y reiniciar Nav2 obligaría a
reiniciar el driver— ni un disparador desde la web, que no existe.

🔴 **El dato que decidió, y que no se dio por supuesto:** *«La Pi se alimenta del puerto USB del
RVR»* (`MANUAL_ATRIZ_ROS2.md:63`). **La carga de CPU sale de la batería del robot**, y Nav2 es la
pieza más pesada del sistema (**~58 % de un núcleo**) sobre una autonomía (~2 h) que ya no cubre
una clase (2-3 h).

📝 Y el argumento de más peso no fue una estimación: **la sesión de hoy vio la batería caer
7.60 → 7.28 V con el robot conduciendo unos pocos metros**. Casi todo el gasto fue estar
encendido. En una sesión de desarrollo el robot pasa la mayor parte del tiempo quieto mientras se
edita código — y ahí un Nav2 arrancado solo serían horas de 58 % de núcleo sin usarse.

⚠️ **Cuánto cuesta eso en batería NO está medido** y se anota como tal: lo que hay es 0.74 %/min
conduciendo, sin separar motores de Pi.

### Dos conflictos del barrido, encontrados al bajar el diseño a plan

Comprobado sobre el código: **ningún launch de navegación enciende el barrido**, y `slam` y
`nav2` lo necesitan. Así que arrancar navegación la dejaría **ciega** — sin `/scan` el
`collision_monitor` bloquea (0.0 cm contra 9.9 del control) y el robot parece averiado.

Y al revés: con navegación en marcha, `cerrar()` de `atriz.py` llamaba a `/stop_scan` y **dejaba a
Nav2 ciego en silencio**.

→ La unidad lo enciende (con `ExecStartPre` **sin `-`**: si no se puede encender, mejor no
arrancar). Y `atriz.py` ahora **deja las cosas como las encontró**: si al conectar ya llegaba
`/scan`, avisa y no lo apaga al salir. **91 tests** (eran 89), comprobados rompiendo la función.

### 🔴 Un hueco del diseño que apareció al escribir el plan

`localizacion.launch.py` exige el argumento `mapa` y **no tiene valor por defecto**, y
`atriz_rvr_bringup/maps/` **no existía**. Los mapas que hay viven en el repositorio privado, que
no llega al robot.

→ El mapa **viaja con el paquete** (lo reparten `provision.sh` y la imagen dorada, y los 16
robots comparten el mismo `map`). Y el envoltorio **falla alto** si no está, en vez de arrancar un
AMCL ciego.

⏳ **Pero el mapa del aula no existe todavía**: las medidas de hoy se tomaron en casa. La
verificación con el robot **no se puede cerrar fuera del laboratorio**.

### Y una trampa documentada que era medio falsa

`atriz-robot.service` afirmaba que `systemd-analyze verify` detecta `StartLimitIntervalSec` y
`StartLimitBurst` mal colocados en `[Service]`. **Medido en systemd 255:**

```
StartLimitIntervalSec en [Service] -> «Unknown key name … ignoring»   ✅ lo dice
StartLimitBurst       en [Service] -> ni una linea                    🔴 NO lo dice
control (directiva inventada)      -> la detecta, o sea que el verificador funciona
```

Corregido. Es la clase de error que ese fichero existe para evitar.

### Estado

Tareas 1, 2, 3 y 5 del plan **hechas**; la 4 —verificar con el robot— **pendiente y bloqueada por
el mapa del aula**. Nada de esto se ha arrancado nunca bajo systemd: **NO VERIFICADO**.

---

## 2026-08-03 (parte 2) — La revisión final dijo NO FUSIONAR, y tenía razón

Cerradas las trece tareas del plan `2026-08-02-api-laboratorio.md`, se lanzó la **revisión de toda
la rama**. Encontró **26 hallazgos**. Los **dos de seguridad** no los había visto ninguna de las trece
revisiones por separado: solo se ven mirando el conjunto. 📝 El resto no: diez venían de la lista
de menores que las propias revisiones por tarea habían ido difiriendo, y la oleada los cerró.

### 🔴 La garantía central de `atriz.py` tenía CUATRO agujeros, y el manual conducía a dos

La biblioteca promete que **el barrido del LIDAR se apaga pase lo que pase**. No lo cumplía en:

| Camino de salida | Qué pasaba |
|---|---|
| **Segundo Ctrl-C** | `cerrar()` tenía **dos `try` y un solo `finally`**, y `except Exception` no ve `SystemExit`. Al reentrar salía por el guardia y el `SystemExit` escapaba: **`/stop_scan` no se llamaba** |
| **Cerrar la terminal / perder el SSH** | Solo se manejaba `SIGINT`. Ni `SIGHUP` ni `SIGTERM` |
| **Ctrl-\ (`SIGQUIT`)** | Tampoco, y **sí se puede capturar** |
| **Ventana entre dos banderas** | `_cerrado = True` se ponía **antes** que `_cerrando = True`: una señal en ese hueco de dos sentencias reproducía el primer caso |

Comprobado provocando las señales sobre **procesos de prueba**, antes y después.
⚠️ **Es una tabla de MECANISMO, no una medida física:** lo medido es **si se llamó a
`/stop_scan`**, no el tambor del X2 girando. El efecto físico está **NO VERIFICADO** y va
en la sesión física.

```
antes   + SIGQUIT -> /stop_scan NO se llamo      despues -> /stop_scan LLAMADO
antes   + SIGTERM -> /stop_scan NO se llamo      despues -> /stop_scan LLAMADO
antes   + SIGHUP  -> /stop_scan NO se llamo      despues -> /stop_scan LLAMADO
ventana entre banderas: rastro []          ->  ['parar', '/stop_scan', 'desmontar']
```

🔴 **El código de salida es idéntico en los cuatro casos, antes y después.** Solo el efecto los
distingue — la regla del proyecto («comprueba el efecto, no el código de salida») apareciendo
dentro de su propia verificación.

📝 **Y el primer arreglo hizo el tercer agujero más probable:** al pedir «espera, ya estoy
cerrando» en el segundo Ctrl-C, empuja al alumno justo hacia probar Ctrl-\. Lo reconoció el propio
implementador. Arreglar un problema creó el camino hacia otro.

En un laboratorio remoto, **perder el SSH es rutina**. El coste no lo paga el alumno: lo pagan 16
X2 girando a 11.8 Hz en vez de 2.7 sin que nadie lo note.

→ Ahora se manejan las **cuatro señales** y además hay `atexit`, que cubre la salida normal sin
`with` y la excepción sin capturar. **Y está escrito lo que `atexit` NO cubre** —`os._exit()`,
`SIGKILL`, `SIGABRT`, caída dura— en vez de venderlo como garantía entera.

### 🔴 `limitar()` mapeaba las entradas menos fiables al máximo

```
limitar(nan) -> 0.4        limitar(inf) -> 0.4
=> avanzar(nan, nan) habria conducido 0.4 m/s x 10 s = 4 METROS
```

La función cuyo propósito documentado es «recortar a un valor seguro» convertía `NaN` en la
**velocidad máxima**, y con el tope de tiempo daba la **distancia máxima**. Ahora lanza
`ErrorAtriz`. 📝 Este repositorio ya lo resolvía bien en `aceptacion_nucleo.delta_angulo()`: la
disciplina existía y no se había aplicado.

### 🔴 El `NO VERIFICADO` estaba en el diseño y no llegó al alumno

`03_operacion/API_LABORATORIO.md` mantenía una lista honesta y exhaustiva de lo no medido. De esa
lista, **cero elementos** habían cruzado a los cinco documentos del curso. Las **ocho** secciones
«qué debería verse» de la guía describían un robot que **nunca ejecutó esos guiones**.

📝 **El proyecto fue riguroso consigo mismo y optimista con el estudiante**, que es exactamente al
revés de como debe ser. Corregido.

### Y una atribución falsa que llevaba cinco sitios

Los **86.6 / 86.2 / 87.7°** de la práctica 4 se citaban como «lo que da esta práctica». La
evidencia 48 dice que se midieron con **`move_timed`** —un servicio del driver— **a 1.0 rad/s**, y
la práctica usa `girar_por_tiempo()` **a 0.8 rad/s** publicando en `/cmd_vel_raw`: otro mecanismo,
otra velocidad, otro camino. Estaba en `atriz.py` (×2), `04_giro_preciso.py`, `REFERENCIAS.md` y
`GUIA_PASO_A_PASO.md`.

🔴 La ironía que hubo que deshacer: `atriz.py` **invocaba por escrito la regla «mide antes de
atribuir» ocho líneas después de incumplirla**.

### Lo que se verificó al cerrar

```
89 tests · auditar_documentacion.py exit 0 · pyflakes exit 0 · arboles limpios
publicaciones a /cmd_vel: 0 · rospy en los diez guiones: 0
/release_emergency_stop: 3 menciones, las TRES texto explicativo, ninguna es llamada
secretos: 1 coincidencia, y es la linea que dice que NO estan
```

### Lo que sigue abierto

- 🔴 **Rotar la PSK del WiFi y la contraseña de `sphero`.** Es lo único que cierra la exposición.
  Medido **tras el push**: la **punta** de `origin/ros2` ya está limpia (**0**), pero las
de `main`, `migracion-ros2` y `wip/scripts-estudiantes` siguen sirviéndolas (**11 cada una**), y
el **historial** de las cuatro las conserva de `Atriz_rvr`, que es público.
  ⚠️ Una re-revisión afirmó **56** en `origin/ros2`; **no se reproduce** — la medición propia da 11
  en las cuatro. Anotado como dato no confirmado.
- 🔴 **La sesión física entera.** Nada se ha medido con el robot moviéndose: ni distancias, ni
  ángulos, ni las corridas de Ctrl-C, ni los faros, ni el seguidor sobre una línea real.
- La rama del `join` expirado de `cerrar()` sigue **escrita y no ejercitada**.
- Decisión del usuario, tomada el 2026-08-03: **empujar los commits tal cual**, sabiendo que unos
  20 de ellos llevan las credenciales en texto plano. No crea exposición nueva —ya están en el
  historial público— pero añade sitios a cualquier limpieza futura.

---

## 2026-08-03 — Tarea 13: cierre del material docente — documentación al día, sesión física pendiente

Última tarea del plan `2026-08-02-api-laboratorio.md`. Alcance recortado por instrucción: **sin
tocar el robot, sin `sudo`, sin ejecutar los diez guiones** (eso es del usuario) y **sin `git
push`** en ningún repositorio.

### Qué se hizo

- Corridos los dos verificadores que no tocan hardware (ver abajo).
- `grep -rn "cmd_vel" *.py | grep -v cmd_vel_raw` sobre
  `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/`, revisado línea a línea.
- Actualizados `CLAUDE.md`, `TRASPASO.md` y `03_operacion/API_LABORATORIO.md` para que reflejen
  el trabajo de las tareas 1-12 (que hasta ahora no aparecía en ninguno de los tres): el diseño
  de `atriz.py`, las credenciales encontradas en `Atriz_rvr`, y el rediseño del seguidor de línea
  a edge-following. Se buscaron **todas** las menciones relacionadas, no la primera — en
  particular en `03_operacion/API_LABORATORIO.md`, que describía el PID de umbral único como
  diseño final en varios sitios (la sección de decisión, la tabla del alcance de la reescritura y
  el punto 3 de verificación) y había que corregir los tres, no solo el titular.

### Qué se verificó, con la salida literal

```
$ cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
$ python3 -m pytest scripts/pruebas/ -q
.............................................................            [100%]
61 passed in 2.05s

$ cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes && grep -rn "cmd_vel" *.py | grep -v "cmd_vel_raw"
atriz.py:44:# 🔴 EL TOPIC. `/cmd_vel` es la SALIDA del collision_monitor: publicar ahí
atriz.py:54:# 🔴 El watchdog del driver corta a los 0.3 s sin `cmd_vel`. Un `sleep(3)` entre
```

Las dos coincidencias son comentarios en `atriz.py` que **explican por qué NO se usa**
`/cmd_vel`, no un uso real — revisadas una a una, no solo contadas (este proyecto ya contó dos
veces un comentario *sobre* un ajuste como si fuera el ajuste).

`scripts/auditar_documentacion.py` marca **12 problemas**, los doce enlaces markdown dentro de un
bloque de diff pegado en `.superpowers/sdd/2026-08-02-api-laboratorio/tarea-12-paquete.md` (un
fichero de trabajo de la tarea 12, no documentación del proyecto), que apuntan a ficheros del
**otro** repositorio (`Atriz_rvr/scripts/estudiantes/`). Es un falso positivo del script — no
distingue un enlace real de uno dentro de una cita de diff — preexistente a esta tarea (no se
tocó ese fichero) y ajeno a los cuatro documentos que sí modifiqué. Los otros cinco bloques de la
auditoría (capítulos citados, secciones fuera de orden, frases obsoletas, índice del manual)
salen en **0**.

### Qué queda pendiente, sin suavizarlo

- 🔴 **La sesión física.** Nada de lo que depende de mover el robot está medido: los ~60 cm de
  `avanzar()`, los ángulos de `girar()` con transportador, las cinco corridas de Ctrl-C, que los
  faros enciendan, que `distancia_frontal()` apunte de verdad hacia delante, el seguidor de línea
  sobre una línea real, y ninguna de las diez prácticas de principio a fin. Comando exacto en
  `TRASPASO.md`, sección «Material docente».
- 🔴 **Rotar la PSK del WiFi y la contraseña de `sphero`.** Medido sobre las cuatro ramas remotas
  de `Atriz_rvr` (`main`, `ros2`, `migracion-ros2`, `wip/scripts-estudiantes`): 11 coincidencias
  cada una, ningún tag afectado, 2 commits tocan el valor. Las credenciales salieron del
  **contenido** (tarea 12), no del **historial** — rotarlas es lo único que cierra la exposición
  de verdad, y es acción del usuario. Purgar el historial después es higiene y es incompleta (no
  llega a los forks que ya existan); al revés no sirve de nada.
- 📌 **La decisión del arranque automático de Nav2/SLAM**, siguiente punto del orden acordado del
  proyecto tras la sesión física.
- **`git push`**: no se hizo en ninguno de los dos repositorios, por instrucción explícita de
  esta tarea. `atriz_migracion` queda `[ahead 19]` antes de este commit sobre `origin/main`;
  `Atriz_rvr` (`ros2`) queda `[ahead 21]` sobre `origin/ros2`. Es decisión del usuario.

---

## 2026-08-02 (parte 3) — el material docente está muerto, y además tiene credenciales en público

### Comprobado por ejecución, no deducido

Los diez scripts de `scripts/estudiantes/` no arrancan: `import rospy` →
`ModuleNotFoundError` en la primera línea. **10 de 10 con `rospy`, 0 con `rclpy`**, y
**15 publicaciones a `/cmd_vel`** en 8 ficheros — el topic prohibido, que es la SALIDA del
`collision_monitor`. Además `05` y `11` usan `/enable_color`, que **no existe**
(`ros2 service type /enable_color` no devuelve nada).

### 🔴 Hallazgo nuevo: la PSK del WiFi y una contraseña de usuario, en un repositorio PÚBLICO

`00_LEEME_PRIMERO.md` y `GUIA_PASO_A_PASO.md` las llevan en texto plano, y están **en el
remoto**, en cuatro ramas (`main`, `ros2`, `migracion-ros2`, `wip/scripts-estudiantes`).
`Bura-hub/Atriz_rvr` responde **200 sin autenticar**: es público.

Es un **segundo** caso, distinto del ya conocido (la credencial de `sphero` en
`Atriz_web_server`): otro fichero, otro repositorio, otras dos credenciales. Y una es la PSK
del WiFi, la misma que el `fmask` de `/boot/firmware` deja legible en el robot y que la imagen
dorada replicaría por 16.

→ **Rotar es lo que lo cierra, y es acción del usuario.** Reescribir el material saca el texto
del contenido actual, no del historial.

### Diseño escrito: `03_operacion/API_LABORATORIO.md`

El material se reescribe sobre una biblioteca del laboratorio, `atriz.py`, en vez de `rclpy` a
pelo: publica en `cmd_vel_raw`, enciende el barrido, republica a 10 Hz contra el watchdog, para
el robot con Ctrl-C (`SignalHandlerOptions.NO`), usa BEST_EFFORT, limita velocidad y tiempo, y
apaga el barrido al cerrar. `girar()` va en **lazo cerrado** sobre el Δyaw de `/odom`, no con una
constante calibrada — que es la idea de robótica que justifica el ejercicio.

Dos límites medidos y escritos en el diseño en vez de descubrirse en clase:
`ros2 param get /rvr_driver color_detection` → **False** en el arranque normal, así que
`robot.color()` avisa en vez de devolver `[0,0,0]`; y **el driver no publica ningún estado de
parada**, así que la API no puede afirmar que la respeta.

### Plan escrito: `00_auditoria/planes/2026-08-02-api-laboratorio.md`

Trece tareas, de las funciones puras a la pasada completa tras un reinicio de verdad. El código
del núcleo y sus 18 tests **se ejecutaron desde el propio plan** antes de darlo por bueno —
`18 passed`— y la clase `Robot` ensamblada pasa `pyflakes` limpia: 21 métodos, ningún nombre sin
definir. Un plan cuyo código no compila es un plan que se descubre roto en la tarea 7.

### Pendiente

Ejecutar el plan: implementar `atriz.py`, reescribir los 10 scripts y los 5 documentos, y
verificarlos **ejecutándolos contra el robot**. Y, fuera del plan y del usuario: **rotar la PSK del
WiFi y la contraseña de usuario** que están en público.

---

## 2026-08-02 (parte 2) — rosbridge cerrado, F7 completa, y tres regresiones mías

### 🔴 Fase A de seguridad: `raw_motors` deja de ser alcanzable

`robot.launch.py` pasaba solo `{'port': 9090}`, dejando los 18 servicios del driver expuestos a
cualquiera en la red. **Y no se arregla con autenticación: rosbridge 2.7.0 en Jazzy no la tiene** —
`rosauth` no es dependencia, no hay parámetro `authenticate`, la capacidad `Authentication` no está
en el protocolo, y `check_origin()` devuelve `True` incondicionalmente. Lo único que ofrece son
**listas blancas**.

Aplicadas y **verificadas con el efecto físico**, que era lo que faltaba:

```
raw_motors AL 30 % por WebSocket, con el RVR encendido:
    antes:   x=-0.0620  y=-0.0057
    después: x=-0.0620  y=-0.0057
    DESPLAZAMIENTO: 0.00 cm
```

📝 Hacía falta porque el resto se apoyaba en que rosbridge **no responde**, y **que no llegue
respuesta no prueba que la orden no pasara** — el recíproco de la trampa que este proyecto lleva
seis veces documentada. `raw_motors` no publica en ningún topic: habla al RVR por el puerto serie,
y **no tiene corte automático**.

⚠️ **La Fase A NO levanta el pendiente.** Cierra el agujero grave, pero cualquiera en el aula sigue
pudiendo teleoperar cualquier robot hasta la Fase B (proxy con JWT en cada robot).

### 🔴 Tres regresiones mías, las tres cazadas por la prueba de aceptación

1. **`verificar_robot.sh` buscaba `base_length 0.182`**, y por la mañana lo cambié a `0.190` con la
   medida de cinta del usuario. Daba FALLO **sobre un modelo correcto**. Van dos veces que ese
   verificador falla justo después de arreglar lo que comprueba.
2. **Mi arreglo A4 rompió F7.** Añadí que F6 apagara el barrido —para no dejar el X2 a 11.8 Hz— y
   **F7 nunca lo volvía a encender**: sin `/scan`, `slam_toolbox` no publicaba `map → odom` y los
   tres objetivos salieron NO VERIFICADO. Es el patrón ya escrito: *al cambiar el estado por
   defecto de un componente, comprueba qué hacen todos los que dependían de él.*
3. **«Volver al origen» no volvía al origen.** Calculaba el destino desde la pose *actual*, así que
   heredaba el error de rumbo y encima proyectaba sobre el rumbo torcido. Eso **invalidaba la
   comparación limpio-vs-obstáculo**, que es lo único que hace interpretable el desvío. **Lo vio el
   usuario mirando el robot**, no el informe.

### 🔴 Y una comprobación que anuncié como añadida y no existía

`err_yaw` se calculaba en F7 y **el `juzgar_banda` que lo reporta nunca llegó a añadirse**: el
parche apuntaba a un texto que ya había cambiado y **falló en silencio**. Quedó una variable
calculada y jamás usada.

📝 **Un `juzgar_banda` que no se llama no falla: desaparece.** Misma familia que una comprobación
bajo un `if` sin `else`.

Y la corrida demuestra que importaba: el tercer objetivo salió a **−10°** con la partida en **+1°**
— **11 grados** que Nav2 dio por `SUCCEEDED` (su `yaw_goal_tolerance` lo permite) y que **ningún
número del informe enseñaba**.

### ✅ F7 completa por primera vez

`partida x=-1.97 y=-0.26 yaw=+1°` · limpio **9.5 cm** · regreso **7.6 cm** · con obstáculo
**18.4 cm** (REVISAR) · desvío lateral **18.2 cm** · sin `Failed to make progress`.

### 🔴 La deriva de yaw es ~1000× mayor justo tras encender el RVR

```
21:01:36   0.97  °/30 s    motor 23.2 °C   RVR recién encendido
21:08:18   0.001 °/30 s    motor 24.1 °C   ~7 min después
```

Los 0.97° eran **transitorios**, así que la banda de F1 está bien puesta: **saltó sobre algo real**.
⚠️ La causa es una **hipótesis** (el giróscopo asentándose con la temperatura), no una medida: n=1.
🔴 Pero la consecuencia para la web es concreta: un alumno que empiece nada más encender el robot
acumulará decenas de grados de error en 15 minutos, y `set_pos_and_yaw(0,0,0)` **no lo arregla** —
pone el origen a cero, no corrige la deriva.

### Otros hallazgos del día

- **No hay cortafuegos, aunque `systemctl is-active ufw` diga `active`**: `ENABLED=no` hace que
  `ufw-init` salga con 0 sin cargar una sola regla. **Octava vez** que algo informa de éxito sin
  haber hecho nada.
- **`laser_x` no era 0**: el LIDAR está **0.5 cm por detrás del centro**, medido con cinta por el
  usuario. Y `laser_y = 0` deja de ser suposición. ⚠️ Queda abierto el conflicto del largo: 18.2
  contra 19.0 cm, dos medidas con cinta.
- 🔴 **La telemetría de la web actual es FALSA** — `Math.random()` generando batería, temperatura y
  el estado de los sensores, con retardos para que parezca ejecución real. Hallazgo nuevo, no
  estaba en la auditoría original.

---

## 2026-08-02 — Prueba de aceptación: las diez fases escritas, F8 verificado de verdad

Se diseñó y se construyó una **prueba de aceptación de extremo a extremo**, de arranque en frío
a navegación autónoma, para responder a una sola pregunta antes de abrir la Fase 5: **¿se puede
construir la web sobre este robot?** Diseño en
[`03_operacion/PRUEBA_ACEPTACION.md`](03_operacion/PRUEBA_ACEPTACION.md), plan en
`00_auditoria/planes/`.

**Estado: F0 a F5 corriendo. 12 PASA · 0 REVISAR · 0 FALLO** en la última corrida de esa mitad.

### Lo que se cierra

| | |
|---|---|
| ✅ **`Restart=always` EJERCITADO por primera vez** | `PID 725 → 12608`. Llevaba desde el principio documentado como «sin ejercitar» |
| ✅ **EL ÁNGULO, MEDIDO POR PRIMERA VEZ** | 90°→**86.6°** · 180°→**179.6°** · 360°→**358.4°** · deslizamiento **0.2–0.3 cm** · signo REP-103 confirmado. ⚠️ n=1 por ángulo. Evidencia 48 |
| ✅ **La parada de emergencia corta en 1.5 cm** | Cinco veces mejor que la base del watchdog (~7.9 cm), y además **rechaza** `move_timed` con `success=False` |

### 🔴 Y seis defectos encontrados, cinco de ellos MÍOS

Los subagentes que implementaron y revisaron cada tarea encontraron esto, y ninguno era del
robot:

1. 🔴🔴 **La parada de emergencia por Ctrl-C NO llegaba al driver.** `rclpy.init()` instala su
   propio manejador de SIGINT que **invalida el contexto** antes de poder publicar. Medido:
   **0 líneas** de «PARADA DE EMERGENCIA» por defecto contra **5** con `SignalHandlerOptions.NO`.
   ⚠️ **Es intermitente**, y por eso pasó la verificación del día anterior. Afectaba a **tres
   herramientas ya commiteadas**. Arregladas.
2. 🔴🔴 **La puerta de seguridad se saltaba sola sin terminal.** `sys.stdin.readline()` devuelve
   `''` al instante si stdin no es interactivo, así que la puerta que existe para que nadie
   arranque un motor con algo delante **no paraba nada** — justo en el escenario en que un agente
   podría lanzarla. Su docstring decía «NO se salta nunca en las fases que mueven el robot».
   Ahora aborta con código 2.
3. 🔴 **La banda de `/scan` citaba una fuente que no era del LIDAR.** «manual cap. 12: 9.997 Hz ·
   σ 0.35 ms» es de `/prueba_atriz`, un topic **sintético** publicado a 10 Hz para probar DDS.
   📝 La pista estaba a la vista: **σ 0.35 ms** es un jitter imposible en un motor que gira libre.
4. 🔴 **F1 esperaba `/battery_state` 8 s**, cuando se publica cada 30 — y ya se había arreglado en
   la guarda. **Arreglar dos de tres llamadas deja el fallo intacto.** Costó tres comprobaciones,
   no una: se saltaban **en silencio** la banda de voltaje y la del `NaN`.
5. 🔴 **`delta_angulo(0, inf)` se colgaba para siempre.** Verificado con `timeout`, salida 124. Y
   F5 la llama en bucle: una muestra corrupta habría colgado la fase sin dejar traza.
6. 🔴 **`cerrar()` no se llamaba en el camino de éxito**, así que al completar las diez fases bien
   —el caso normal— el nodo nunca se cerraba ni se mandaba parada final.

📝 **La lección que atraviesa a casi todos:** algo que **devuelve sin error y no hace su trabajo**.
Es el mismo patrón que `chmod` sobre FAT, `colcon build` desde el directorio malo, `set_all_leds`
con máscara corta y `netplan generate` que nunca llegó a ejecutarse. **Comprueba el efecto, no el
código de salida.**

### F6, F7, F8 y F9 escritas y ejecutadas — las diez fases existen

**F6 (seguridad) y F7 (autónomo con obstáculo), última corrida real** (informe
`47_aceptacion_20260802_133324.txt`): **10 PASA · 3 REVISAR · 0 FALLO · 4 PENDIENTE**. El
`collision_monitor` paró solo, Nav2 completó los tres objetivos (`SUCCEEDED`), y no reapareció
«Failed to make progress». Los tres REVISAR de esa corrida:

- distancia frontal de parada: **18.9 cm** contra una banda `[0, 15]` que citaba una base
  (`CHANGELOG:1824: 9.9 cm`) medida con **otro `radius`** de `collision_monitor.yaml` (0.11, no
  el 0.18 actual). **El robot tenía razón, la banda no** — corregida a `[15, 24]` en el código.
- objetivo con obstáculo, error final **40.7 cm**, y desvío lateral **13.9 cm**: los dos venían
  de que la fase medía el error en el marco **odom** (`pos_yaw()`) mientras el objetivo se
  mandaba en **map** — Nav2 decía `SUCCEEDED` sobre un objetivo que había llegado desplazado por
  el desfase `map↔odom`. Arreglado con `pos_mapa()` (TF `map → base_footprint`).

🔴🔴 **Los dos arreglos ya están en el código commiteado, pero no se ha vuelto a correr F6/F7
para confirmar 0 REVISAR con ellos puestos** — esta tarea (8) tenía prohibido mover el robot.
Queda para la corrida completa del paso 2 del diseño (reinicio real + `prueba_aceptacion.py`
entera), que le toca al usuario por el `sudo reboot`.

✅ **Y el usuario contrastó F6 a mano con cinta métrica** (evidencia 49,
`00_auditoria/evidencia_24_04/49_f6_f7_medido_a_cinta.txt`), y salieron tres cosas que el `/scan`
por sí solo no decía:

- La distancia que importa es la del **borde del chasis**, no la del LIDAR: **7–8 cm reales**
  tras la parada del `collision_monitor` (el `/scan` decía 18.9, medido desde el sensor). No
  choca.
- ⏳ **`laser_x = 0` es sospechoso**: con el LIDAR centrado, el borde debería quedar a
  `18.9 − 9.1 = 9.8 cm`, y se midieron 7–8. Faltan ~2 cm sin explicar. `laser_x` es del
  2026-07-30, anotado como «centrado» **sin cinta detrás**, a diferencia de `laser_z`, que se
  midió y resultó estar 2 cm mal. Pendiente de medir; afecta a dónde cree Nav2 que hay un
  obstáculo.
- El retroceso del watchdog comandó 30 cm y avanzó solo **14**: el polígono estático
  `Precaucion` se extiende 0.36 m **hacia delante** y frena al 40 % aunque el robot se aleje. No
  es un fallo del watchdog — es cómo funciona un polígono estático, y hay que decírselo a la web.

**F8 (web por rosbridge), ejecutado hoy sin mover el robot** (informe
`47_aceptacion_20260802_141016.txt`): **2 PASA**. Handshake WebSocket a mano →
`HTTP/1.1 101 Switching Protocols`, y una suscripción real a `/odom` que **sí** entrega mensaje —
no solo «el puerto está abierto».

**F9 (veredicto):** imprime el aviso de los pendientes y añade los cuatro `PENDIENTES_CONOCIDOS`
al informe. Con solo F8+F9 corridas: **2 PASA · 0 REVISAR · 0 FALLO · 4 PENDIENTE**, y
`🔴 NO HAY VÍA LIBRE PARA LA FASE 5` — el comportamiento acordado el 2026-08-01, no un fallo.

### Lo que queda

**Correr las diez fases de un tirón, tras un reinicio real** (paso 2 del diseño: `sudo reboot` →
`python3 -u scripts/prueba_aceptacion.py`), para confirmar en una sola pasada los arreglos de F6/F7
de más arriba y cerrar el informe definitivo. Y, siempre, **la vía libre sigue bloqueada** por los
cuatro pendientes conocidos, empezando por **rosbridge sin autenticación** — como se decidió:
«robot impecable» y «vía libre» no son lo mismo.

---


## 2026-08-01 (SDK) — Se exploró el SDK entero, y una conclusión del proyecto era falsa

El usuario preguntó por qué el driver usa «27 de 94» métodos del SDK. La cifra estaba vieja
(son **37 de 99**) y, sobre todo, nadie había **probado** los 62 restantes: se hablaba de ellos
por lo que dice la librería, que en este proyecto ya había mentido dos veces.

### 🔴 Lo importante: el atasco SÍ se detecta, y llevábamos días creyendo que no

`CLAUDE.md`, el manual y la evidencia 35 decían que «las notificaciones de motor no llegan». De
ahí salió que el atasco «se queda sin cubrir», que `antiguedad_atasco_s` valdría −1.0 para
siempre, y finalmente que la detección era **imposible**.

**Es falso.** Con el robot bloqueado a mano, tres corridas, tres detecciones, **acertando la
oruga las tres veces**:

```
18:08:07  🔴 MOTOR IZQUIERDO ATASCADO. El firmware ve corriente y no ve giro.
18:08:09  motor izquierdo: atasco resuelto
```

**Por qué la medida anterior falló:** forzó los motores **a 220/255**, o sea con `raw_motors`,
que es PWM crudo y **se salta el sistema de control del RVR** — y la detección de atasco vive
**dentro** de ese sistema. Con `drive_rc_si_units`, que es lo que usa `cmd_vel`, salta a los ~5 s.

📝 **Se probó una cosa y se concluyó sobre otra.** El resultado negativo era correcto para
`raw_motors` y falso para todo lo demás. **Prueba por el camino que el sistema usa de verdad.**

⚠️ Y encadenó tres investigaciones inútiles: buscar la corriente de los motores (`bad_cid`),
declarar el atasco imposible, e implementar un detector propio por encoders — **retirado**,
porque en la prueba ni llegó a ejecutarse y la notificación del firmware es estrictamente mejor
(ve la **corriente**, que nosotros no podemos leer).

✅ **Y lo vio el usuario mirando el robot:** durante el atasco el RVR **enciende LEDs amarillos y
rojos** por su cuenta. El driver no los toca. Diagnóstico sin abrir un terminal, con 16 robots.

### ✅ Implementado: `/battery_state` con voltaje y umbrales del firmware

El porcentaje decía **100 %** con la batería a **8.29 V**, a 1.29 V del umbral de «baja». Es una
estimación gruesa.

```
voltage 8.2803 V · estado ok · umbrales del firmware: baja 7.0 · crítica 6.5 · histéresis 0.2
```

Los umbrales se **leen del propio firmware** al arrancar, así no se codifican a mano en dos
sitios. Van en la misma pasada del keepalive, que ya llamaba al RVR cada 30 s.

⚠️ **«Batería baja» no se marca como averiada:** una batería descargada está **sana**, y forzar
`DEAD` engañaría a cualquier consumidor. La señal para la web es **`voltage`**.

### 🔴 Cerrado con evidencia: no hay rumbo absoluto

El usuario encontró la página de actualización de firmware y el hilo archivado del foro de
Sphero. Tres respuestas:

1. **El firmware ya está en la última versión** — la de «Fall 2022» es 9.1.462/9.2.482, justo la
   que tiene el robot.
2. **Un «SDK modificado» no puede ayudar:** el SDK solo serializa el protocolo, y `bad_cid` **lo
   responde el robot**.
3. El RVR **sí lleva magnetómetro** (IMU de 9 ejes), pero las **dos** vías fallan:
   `get_magnetometer_reading` da `bad_cid` y `magnetometer_calibrate_to_north` **se acepta y no
   hace nada** — ni gira ni avisa.

🔴 **Lo zanjó el usuario mirando el robot: «no giró».** Sin ese dato, «no llegó la notificación»
era ambiguo. Consecuencia: la pose inicial de cada robot tendrá que venir del mapa o del
operador. **Es una limitación del hardware, no una tarea pendiente.**

### 📚 Rescatada la documentación oficial del protocolo

`sdk.sphero.com` **ya no existe**. Guardada en `00_auditoria/referencia_sdk/` desde archive.org,
porque no hay otra copia. Documenta el **protocolo del robot**, no el SDK de Python — por eso
describe comandos que la librería no expone.

Y destapó **dos errores propios**: clasificar como «mudo» un comando que es **asíncrono por
diseño**, y consultar `get_temperature` con **IDs que no existen** dando el resultado por bueno
**porque parecía razonable**. 📝 *Un valor plausible no es un valor validado.*

### ⚠️ Térmica y fallo: repetidas por el camino bueno, y siguen NO VERIFICADAS

10 ciclos de bloqueo subieron los motores de 28.7 a **40.0 °C** sin que saltara nada. **No prueba
nada:** la protección térmica no actúa a 40 °C y el tope de seguridad de la prueba estaba en 65 —
**el ensayo nunca pudo dispararla**. No se persigue: el sondeo cada 30 s ya da temperatura y
estado, y el coste sería castigar la única unidad montada.

**Pero salieron dos datos que valen:**
- **Un motor bloqueado sube +11.1 °C en 90 s de bloqueo** — sirve de **corroboración** de atasco.
  ⚠️ Se publicó como «~6.5 °C/min». Es engañoso: el ritmo **no es constante y sube**
  (5.0 → 8.4 → 10.2 °C/min entre tramos de la MISMA tirada, n=1), y el denominador
  contaba 10 ciclos donde hay 9 intervalos. Corregido el 2026-08-01.
- 🔴 **La temperatura publicada puede tener 30 s de retraso.** La web **no debe leer una
  temperatura plana como «estable»**: puede ser el mismo dato repetido. Para eso está
  `antiguedad_termico_s`.

### Lo que queda del SDK

| | |
|---|---|
| 🔴 Necesita `rvr-02` | todo el IR robot-a-robot. Y el arreglo de seguridad de `set_ir_evading` está verificado **por código**, nunca con un emisor delante |
| ⏳ Probable hoy | `enable_color_detection_notify` (podría explicar la confianza 0 de `/color`) · `set_locator_flags` · replicar `reset_yaw` |
| 📝 Sin interés | `force_battery_refresh`, banderas `Boost`/`Fast Turn`/`Enable Drift`, modos de conducción alternativos |

---

## 2026-08-01 (cierre) — Namespace y parada de emergencia: las dos decisiones, cerradas

Eran los dos únicos bloqueos **de decisión** antes de la Fase 5. Cambiar cualquiera de las dos
después obligaría a tocar los 16 robots y el cliente a la vez.

### ✅ SIN NAMESPACE

Los topics son `/odom`, no `/rvr_01/odom`. Tres razones, en orden de peso:

1. **El aislamiento ya está resuelto:** un `ROS_DOMAIN_ID` por robot es aislamiento DDS total.
   Los robots no se ven entre sí ni queriendo.
2. **La web tampoco lo necesita:** habla por **un WebSocket por robot** (`ws://rvr-07.local:9090`).
   Poner `/rvr_07/odom` dentro de un canal que solo llega al robot 7 es escribir el número dos
   veces.
3. 🔴 **La parada de emergencia ya falló una vez POR UN NAMESPACE** — al portar de ROS 1 se coló
   un `/rvr/` y falló en silencio con `200 OK`. Van cuatro fallos de la parada; no se le regala
   el quinto, multiplicado por 16.

⚠️ Y un namespace **no renombra los `frame_id` de TF**, así que ni siquiera resolvería el caso
para el que suele invocarse. Protección parcial con aspecto de completa.

### ✅ El nombre oficial de la parada es `/emergency_stop`

Con **RELIABLE + VOLATILE** — `TRANSIENT_LOCAL` en el suscriptor fue la tercera causa de fallo, y
rosbridge no es TRANSIENT_LOCAL. El driver sigue escuchando los tres nombres **a propósito**: con
un botón de emergencia el modo de fallo que importa es «el mensaje no llega».

### 🔴 Y al cerrarlo apareció que el camino de escape estaba roto

Los launch aceptan un argumento `namespace` que se deja abierto por si algún día hacen falta
varios robots en un mismo RViz. Pero el driver tenía **dos `frame_id` escritos a fuego**
(`/ambient_light` y `/motor_status`) mientras `odom`, `base` e `imu` ya eran parámetros. Con el
namespace activo se habrían quedado sin prefijo **partiendo el árbol TF** — el mismo fallo que
costó la Fase 3.

Ahora es el parámetro `body_frame` (`base_link` por defecto), distinto de `base_frame`
(`base_footprint`) porque los sensores están en el cuerpo, no en la proyección en el suelo.
✅ Verificado tras recompilar y reiniciar: los dos siguen publicando con `base_link`.

---

## 2026-08-01 (noche) — El LIDAR inundaba el journal, y la primera solución era peor

`atriz-escaneo off` es el **estado normal en reposo** de los 16 robots. Con él, el nodo del
YDLIDAR emitía `Failed to get scan` **25 veces por segundo**: 47 291 de 47 551 líneas del
journal del servicio (**el 99 %**), 2.17 millones de mensajes al día por robot. Ahoga cualquier
error de verdad —y los peores fallos de este proyecto están documentados como silenciosos— y
son escrituras 24/7 sobre una **microSD**, que es lo que las mata.

### 🔴 Lo interesante no es el bug, es cómo se estuvo a punto de arreglar mal

La propuesta era **no levantar el nodo del LIDAR** hasta que hiciera falta. El usuario
desconfió —*«¿voy a perder esa automatización al encender el robot?»*— y pidió que se le
convenciera siendo imparcial. Al ir a argumentarlo hubo que leer el fuente, y la causa real
estaba ahí:

```cpp
while (ret && rclcpp::ok()) {
  if (laser.doProcessSimple(scan)) { ...publica... }
  else { RCLCPP_ERROR(node->get_logger(), "Failed to get scan"); }   // 20 Hz
}
```

`/stop_scan` y `/start_scan` son servicios **del propio nodo** y llaman a `turnOff()`/`turnOn()`,
pero **nadie guarda ese estado**. No era una consecuencia de apagar el barrido: **al driver le
falta una variable.**

Las tres opciones que se habían planteado atacaban el síntoma, y la recomendada además cambiaba
el arranque del robot para nada. **La desconfianza del usuario fue lo que forzó a mirar.**

### El arreglo: nueve líneas, y no cambia nada del arranque

Una bandera `std::atomic<bool> escaneando` que los dos servicios actualizan, y una salida
temprana en el bucle. ✅ Verificado en rvr-01:

| | antes | después |
|---|---|---|
| barrido apagado | 502 errores / 20 s | **0** |
| `atriz-escaneo on` | — | `/scan` a **12.00 Hz**, 250 puntos |
| `atriz-escaneo off` | — | 0 mensajes, **0 ruido** |

El nodo **sigue levantándose con el robot**, como antes.

### Y la otra mitad: que sobreviva a un reflasheo

`provision.sh` clona el ydlidar de GitHub y **le borra el `.git`**. Un cambio a mano se perdería
y este robot divergiría de uno recién aprovisionado — y la regla dice que **gana el script**.
Por eso el parche se versiona en `Atriz_rvr/atriz_rvr_bringup/patches/`, `provision.sh` lo
aplica tras clonar (idempotente), `patch` se añade a los paquetes de apt, y el verificador
comprueba **el fuente y el efecto**.

📝 Si el upstream lo arregla algún día, el parche fallará al aplicarse y `provision.sh` lo dirá.

### 📄 Y un tercer caso de deriva documental

El **plan** decía «Nav2 ⏳ pendiente» con Nav2 navegando desde el 31 de julio (9–10 cm de error,
4 de 4 rodeando obstáculos, AMCL a 0.1 cm). Van dos en un día, con el índice del manual. Los
documentos de **estado** se quedan atrás mientras las evidencias están al día. Regla escrita en
el propio plan: al cerrar algo, se actualiza **en el mismo commit** que la evidencia.

---

## 2026-08-01 (tarde) — La red de la flota, verificada de extremo a extremo

Cerró **la última incógnita grande antes de la Fase 5**: cómo hablan la web y 16 robots, y cómo
se pasa del PC de casa al laboratorio sin reconfigurar dieciséis tarjetas.

### ✅ La suposición que sostenía el diseño: verificada

Todo dependía de que una IP **estática** y el **DHCP** convivieran en la misma interfaz. Si no,
había que rehacerlo. Conviven:

```
wlan0  UP  10.14.7.7/21  192.168.1.200/24  192.168.1.58/24
            ^laboratorio  ^casa             ^DHCP
default via 192.168.1.1 dev wlan0 proto dhcp     ← la ruta la pone el DHCP, como se diseñó
```

**Este robot se lleva al laboratorio sin tocar un solo comando.**

### ✅ La web habla con el robot, probado desde un navegador de verdad

`ws://rvr-01.local:9090` desde el PC del usuario, con
[`03_operacion/probar_conexion_web.html`](03_operacion/probar_conexion_web.html) — sin
librerías y sin CDN, para que funcione sin internet. Funcionaron **las dos direcciones**:
telemetría llegando y `set_led_rgb` **encendiendo los faros de verdad**, confirmado con la
vista. Importaba: en este proyecto `success=true` ya devolvió `true` sobre un LED que no
alumbra.

```
navegador → WebSocket → rosbridge → servicio ROS 2 → driver → SDK → serie → RVR → LED
```

Y resolvió **por nombre**, sin escribir ninguna IP: eso es lo que permite que el mismo código
web funcione en las dos redes.

### ✅ Riesgo nº4 de `FLOTA.md`: cerrado, y con la estimación corregida

| Estado | por robot | ×16 |
|---|---|---|
| navegando | **80.7 kB/s** | **10.3 Mbit/s** |
| en reposo | **13.6 kB/s** | **1.7 Mbit/s** |

Se había estimado que el JSON de rosbridge multiplicaría por **3–5×**. El real es **~2×**, y esa
diferencia separa «hay que comprar red» de «cabe». Medido **dos veces con dos clientes
distintos en dos máquinas distintas**, que coincidieron al 3 % en reposo — en un proyecto donde
ya han mentido cuatro instrumentos, eso convierte la cifra en un hecho replicado.

🔴 **La palanca: `/scan` es el 83 % del tráfico.** La diferencia entre 1.7 y 10.3 Mbit/s es
`/scan` y nada más.

### 🔴 Tres fallos encontrados, dos de ellos míos

1. **`chmod 600` sobre `/boot/firmware` no hace nada, y devuelve 0.** Es FAT: no guarda
   permisos de Unix, los fija el montaje. **La PSK del WiFi queda legible por cualquier usuario
   de los 16 robots.** Y la instrucción `sudo chmod 600 red.txt` la di yo, en los pasos
   detallados: no solo era inútil, daba falsa confianza. Se cierra en `/etc/fstab` con
   `fmask=0177,dmask=0077` — **pendiente del usuario**.
2. **Un fichero rancio en `/tmp` inventó un fallo de netplan que nunca ocurrió.**
   `fs.protected_regular=2` impide a root escribir en un `/tmp/…` ajeno; si la redirección
   falla, **bash no ejecuta el comando**, y el `else` imprimió el contenido de seis horas antes
   como si fuera el error del momento. Arreglado con `mktemp` en `first-boot.sh` y en
   `provision.sh`, que tenía el mismo patrón.
3. **El índice del manual llevaba desviado del contenido.** Decía que los capítulos 9, 10, 11 y
   12 estaban «no escritos» cuando llevaban semanas escritos y verificados, y numeraba hasta 12
   mientras el manual llegaba al 18. Además había un «Capítulo 6» huérfano **entre el 16 y el
   17**. Es la deriva documentación↔realidad que la auditoría original señaló como el problema
   de fondo, reproducida dentro del documento que venía a arreglarla.

### Cambios

| Fichero | Qué |
|---|---|
| `scripts/first-boot.sh` | **`--solo-red`**: regenera el netplan sin reiniciar ni tocar la identidad · `mktemp` |
| `scripts/provision.sh` | `mktemp` para el `.deb` de ROS |
| `scripts/verificar_robot.sh` | **sección 12**: mDNS, netplan, `red.txt`, direcciones reales de `wlan0`, rosbridge en las dos familias, y una regresión que busca rutas fijas de `/tmp`. **102 correctas, 0 fallos** |
| `scripts/red.txt.ejemplo` | avisa de que `chmod` no sirve sobre la FAT |
| `03_operacion/probar_conexion_web.html` | **nuevo** — la prueba desde el navegador |
| `mediciones_banco/probar_mdns.py` | **nuevo** — mDNS crudo, sin dependencias · `--flota 16` |
| `mediciones_banco/probar_rosbridge.py` | **nuevo** — cliente WebSocket propio que mide bytes/s |
| `02_manual/…` | **capítulo 19** (red de la flota) · índice reescrito · capítulo 6 recolocado |
| `03_operacion/FLOTA.md`, `ARQUITECTURA.md`, `CLAUDE.md` | alineados |

### Pendiente

- 🔴 `/etc/fstab` para cerrar la PSK legible (sudo del usuario)
- mDNS **por enlace**: `wlan0: no` mientras `Global: yes`
- Aislamiento de clientes del AP del aula — sin comprobar
- ⏳ **Namespace `/rvr_NN` o sin namespace**, que hay que fijar **antes** de la Fase 5


## 2026-08-01 — `ARQUITECTURA.md` contra el robot real: una errata era un fallo de seguridad

Al responder a *«¿cómo esperamos cambiar la comunicación para que ya no sea por SSH?»* salió que
el **contrato de topics para la web** ya no describía este robot.

### 🔴 La grave: el contrato decía que la web publica en `cmd_vel`

**Publicar ahí salta el `collision_monitor`.** `/cmd_vel` es la **salida** del monitor y tiene un
solo publicador; la cadena es `web → cmd_vel_raw → collision_monitor → cmd_vel → driver`.
Publicar en `/cmd_vel` **funciona** —el robot obedece— y por eso es peligroso: la Fase 5 lo habría
implementado tal cual y el robot habría conducido sin capa de seguridad.

### El resto de erratas

- `battery` → el topic real es **`battery_state`**.
- Faltaban `motor_status`, `encoders`, `color`, y —lo importante— los servicios **`/start_scan`**
  y `/stop_scan`. `/start_scan` es **obligatorio**: sin él el robot no obedece y parece averiado.
- No decía que `odom`, `imu`, `scan` y `color` son **BEST_EFFORT**. Un suscriptor con el perfil
  por defecto **no recibe nada**, sin error.
- La fila del **SSH** decía «solo ciclo de vida: arrancar/parar el stack». **Ya no hace falta**:
  `atriz-robot.service` levanta el robot al encender y se recupera solo. El SSH sale de la
  operación normal y queda para mantenimiento.

### ⏳ Y dos decisiones que NO se han tomado

Se marcan como pendientes en vez de resolverlas por cuenta propia — son de diseño y afectan al
cliente web, así que cambiarlas después obliga a tocar los 16 robots **y** el cliente:

1. **Namespace `/rvr_NN` o sin namespace.** El diseño decía `/rvr_NN`; el driver corre hoy sin él.
2. **El nombre canónico de la parada de emergencia** — el driver escucha los tres a propósito.

---

## 2026-08-01 — La imagen dorada, auditada contra el estado real

Petición del usuario: *«revisa qué tan completa está la imagen dorada para pasarse a otro
sphero»*. **Veredicto: funcionalmente casi completa, pero no se debe clonar todavía.**

### 🔴 Y lo primero es una corrección: la imagen SÍ llevaría el arranque automático

Este proyecto documentó —lo escribí yo— que «si se construye la imagen antes de añadir systemd a
`provision.sh`, los 16 robots saldrán **sin** arranque automático». **Es falso.** Un `dd` copia el
disco entero: `/usr/local/bin` y `/etc/systemd/system` viajan con él.

El problema real es otro y es peor de razonar: **la imagen y `provision.sh` divergirían**, y la
regla del proyecto dice que **gana el script**. Un robot reprovisionado desde cero saldría
distinto de uno clonado.

📝 Y hay una segunda divergencia más silenciosa: **`provision.sh` no clona `~/atriz_migracion`**,
así que un robot provisionado se queda sin `verificar_robot.sh` ni `fase_7_systemd.sh`.

### 🔴 Los tres bloqueantes

1. **`~/.git-credentials` con el PAT viaja en la imagen.** `fase_6` avisa pero no lo borra —
   deliberado, puede ser un token compartido. Repartir uno personal en 16 microSD es una decisión
   👤, y se suma a que la imagen ya lleva la PSK del WiFi.
2. **rosbridge no está instalado**, y la web habla por ahí. Clonar antes de la Fase 5 = clonar dos
   veces, ~300 MB por robot sobre la única AP.
3. **La divergencia con `provision.sh`.**

### 🔴 Y dos bombas de relojería en `fase_6`, arregladas hoy

**No borraba `/var/lib/atriz-first-boot.done`.** El servicio de personalización lleva
`ConditionPathExists=!` sobre esa marca: si el robot de referencia ejecuta first-boot **una sola
vez**, la marca viaja en la imagen y **los 16 clones se saltan la personalización entera** —
mismo hostname, mismo `ROS_DOMAIN_ID`, los 16 viéndose en DDS. Y **sin dar ningún error**.

📝 Hoy la marca no existe, así que la imagen de hoy estaría bien. Es una bomba de una sola línea.

**No borraba `/etc/profile.d/atriz-robot.sh`.** El clon arrancaría con el `ROS_DOMAIN_ID=1` del
robot de referencia hasta que first-boot lo pisara; si first-boot fallara, se quedaría ahí para
siempre. → Ahora se borran los dos: la identidad **solo** puede venir de first-boot, y si falta,
el envoltorio del servicio **se niega a arrancar**.

✅ Y `fase_6` avisa ahora de los tres bloqueantes **antes** del `dd`, cuando aún se pueden
arreglar.

Evidencia 38.

---

## 2026-08-01 — El piso blanco del LIDAR, y dos huecos encontrados de rebote

### ✅ Por qué el sensor de luz ve los LEDs del robot — la explicación es física

La aportó el usuario y cierra el hallazgo: el sensor de luz ambiente **mira hacia arriba**, y
encima del Sphero está el **piso que sostiene el LIDAR** —los 4.6 cm ya documentados en
`MEDIDAS_ROBOT.md`— que es **blanco**. Ese piso le devuelve la luz de los propios LEDs del robot.

📝 **No se podía deducir de los datos.** Los datos decían «ve los LEDs»; el *porqué* es una
observación del montaje. Mismo patrón que la inclinación del robot y el LED de los bajos: **hay
cosas que solo se saben mirando el hardware.**

🔴 **Decisión: `/ambient_light` no se usa.** Un valor alto significa «el robot tiene LEDs
encendidos», no «hay luz». Se probó solo para saber si responde, y responde. Se deja publicado
porque es gratis, pero ningún consumidor debe apoyarse en él. No se arregla con software y nada
del laboratorio lo necesita.

### 🔴 Y al meter los topics nuevos en el verificador salieron dos huecos de operación

**(a) `TRANSIENT_LOCAL` no garantiza que un suscriptor tardío reciba el último valor.** El driver
lo daba por hecho para `/motor_status` y `/battery_state` — lo escribí yo. Medido: un suscriptor
nuevo se quedaba **sin recibir nada en 10 s, 2 de cada 3 veces**, incluso en su propio proceso.
Con el sondeo cada 30 s, eso dejaba a la web **medio minuto a ciegas** sobre un fallo de motor.
→ Arreglado republicando a **1 Hz**: gratis, no toca el puerto serie, y no depende de esa
semántica. 3 de 3 pasadas estables después.

**(b) 🔴🔴 Si un nodo muere, systemd no se entera.** Lo destapó un `SyntaxError` mío: el driver
estuvo **cuatro minutos muerto** con el servicio en **`active (running)`**. El PID principal es el
`ros2 launch`, que sobrevive a la muerte de un nodo, así que `Restart=always` —estrenado ayer y
funcionando— **no cubre este caso**.

⚠️ Es el peor modo de fallo para un laboratorio remoto: un robot inservible que **desde fuera
parece sano**. Exactamente el mismo patrón que el RVR dormido con el nodo vivo.

→ Arreglado con **`on_exit=Shutdown()`** en el nodo del driver. Verificado matando solo ese nodo:
`NRestarts` 12→13 y el robot entero de vuelta en **25 s**. Solo en el driver: sin él no hay robot,
mientras que sin LIDAR se puede teleoperar.

⏳ **Sin decidir:** si el `collision_monitor` debe llevarlo también. Un robot sin capa de seguridad
que parece sano es peligroso.

### El verificador

Sección nueva para `/encoders`, `/ambient_light` y `/motor_status` — comprueba que **publiquen**,
no que existan. **94 comprobaciones, 0 fallos.** `/ambient_light` se comprueba por ritmo y **no
por valor**, a propósito: su número depende de qué LEDs estén encendidos.

Evidencia 37 · manual cap. 18.4.

---

## 2026-08-01 — Los dos sensores ópticos: funcionan, y son DOS

Petición del usuario: *«el sistema tiene problemas con los sensores de color y de luz ambiental,
puedes probarlos con detalle»*. **Los dos funcionan.** Los «problemas» eran el LED apagado por
defecto, dos montajes de prueba mal hechos, y **dos afirmaciones mías que resultaron falsas**.

### ✅ El sensor de color acierta los cinco

| superficie | `clear` | R/G | B/G | `/color` |
|---|---|---|---|---|
| suelo | 1275 | 0.546 | 0.413 | (255, 220, 209) |
| blanco | **2288** | 0.482 | 0.498 | (244, 235, 255) |
| rojo | 565 | **2.743** | 0.355 | **(255, 31, 43)** |
| azul | 396 | 0.447 | **0.856** | **(88, 120, 201)** |
| negro | **181** | 0.480 | 0.460 | (28, 27, 29) |

12.6× entre blanco y negro, los ratios se mueven en la dirección correcta, y `/color` acierta a
ojo los cinco. 🔴 La **confianza es 0** en todos, y no es el sensor: es el **clasificador**, que
necesita una **paleta** (`load_color_palette` existe en el SDK y no se usa).

### ✅ Y el de luz ambiente es OTRO sensor, en otro sitio

Lo dijo el usuario, y la medida lo confirmó: encender los 10 grupos de LED sube la luz de **1.76 a
23.55** (13.3×), mientras el RGBC da valores **idénticos** con los LEDs en rojo, verde o azul.
→ ⚠️ **`/ambient_light` no mide la luz de la sala**: la dominan los LEDs del propio robot.

### 🔴 Dos afirmaciones retiradas, las dos documentadas ese mismo día

**«`/ambient_light` da 0.0 sin `color_detection`»** — falso. Las lecturas de 0.0 se tomaron **con
el robot sin levantar de verdad**, y el usuario lo confirmó *después*. → **Si tu medida depende de
que alguien haga algo físico, pregunta si lo hizo antes de concluir.**

**«cada reinicio del driver degrada el stream»** — falso. Era el **apagado limpio apagando los
LEDs**, como propuso el usuario. Su hipótesis descartó la mía.

### 🔴 Y dos montajes que daban resultados imposibles

- Deslizar el papel sin comprobar que tapa la ventana: el «blanco» dio **exactamente** los mismos
  números que la referencia. **Idéntico no es parecido: es la señal de que no cambiaste nada.**
- **Pegar el objeto contra la ventana tapa también el LED**: el blanco daba `clear=261` y el negro
  795, al revés de lo físicamente posible.

→ El protocolo que sí funciona lo propuso el usuario: **una superficie por vez, colocada y
confirmada antes de medir**. Con él salieron los cinco a la primera.

Evidencia 37 · manual cap. 18.4.

---

## 2026-08-01 — LEDs, luz ambiente y encoders: tres bugs que solo salen mirando el robot

El usuario pidió *«prueba todos los leds para ver si hay comunicación todavía»*. Los 12 grupos
devolvieron `success=True`. **Y dos no se encendieron.**

### 🔴 `led_group` es una máscara de bits, y `set_all_leds` quiere un brillo POR BIT

Los 10 grupos normales tienen **3 bits** (R, G, B), `all_lights` tiene **30** y
`undercarriage_white` **1**. El driver mandaba **siempre tres**: para los 10 acierta, y a los
otros dos el RVR les dice que sí y no hace nada.

📝 **Lo encontró el ojo del usuario, no el código:** *«no vi los bajos ni tampoco todos»*. Sin
eso, los doce ✅ del script habrían pasado por buenos. Arreglado contando bits; los tres
servicios de LED comparten ahora la misma regla, y el usuario confirmó ver `all_lights`.

### ✅ `/encoders` y `/ambient_light`, con dos bugs de camino

Las claves del stream son **`LeftTicks`/`RightTicks`**, no `Left`/`Right` — **la tabla de
documentación del propio SDK dice otra cosa que el payload**. Con las claves malas el handler
lanzaba `KeyError` y el topic quedaba registrado con **cero mensajes**: el síntoma exacto de un
RVR dormido. Y los ticks vienen **sin signo en 32 bits**: un retroceso llega como `4294965940`,
que son **−1356**.

Medido después: `/odom` 16.58 · `/imu` 16.57 · `/encoders` 16.57 · `/ambient_light` 13.06 Hz.
**Añadir dos sensores al stream no le cuesta ritmo a `/odom`.**

### 🔴 `/ambient_light` da 0.0 si el sensor de color está apagado

**0.0 constante** con `color_detection=false` — incluso con el robot **levantado** (247 muestras)
y por las dos vías, stream y consulta directa. Con `color_detection:=true`: **2.497**. Comparten
óptica. Es la misma trampa que dejó `/color` en `[0,0,0]` durante meses: el topic existe, el
ritmo es correcto, y el dato es un cero. El driver ahora lo avisa por el log.

✅ **Y eso contesta lo del LED de los bajos:** lo enciende `enable_color_detection`, **no** el
grupo `undercarriage_white` del SDK.

### 🔴 Una conclusión retirada, y grave: «un comando de LED mata la telemetría»

Durante un buen rato esta sesión creyó haber encontrado un fallo serio: tras cualquier comando de
LED, `/odom`, `/encoders` y la luz caían a **0.0 Hz**. Se llegó a **aislar** quitando los dos
sensores nuevos, seguía pasando, y se concluyó *«es preexistente»* — lo cual habría significado
que la web no puede encender un faro sin cegar al robot.

**Era falso. El fallo estaba en el instrumento.** El script mezclaba
`rclpy.spin_until_future_complete(nodo, f)` con un `SingleThreadedExecutor` que ya tenía ese
nodo: el nodo deja de ser atendido y **mis** suscripciones se callan. Con el ejecutor bien usado:
16.9 → 16.6 → 16.6 → 16.5 Hz. **El robot no había dejado de publicar ni un mensaje.**

Van **cuatro** veces que el instrumento miente en este proyecto. Ante una medida rara, sospecha
del medidor.

📝 Contribuyó un bug propio: `_avisar_una_vez` se apoyaba en `_recibidos`, que `_quiza_publicar`
**vacía en cada ciclo de `/odom`** — así que un aviso «una sola vez» salía **13 veces por
segundo** desde el hilo de asyncio.

### 🔴 Seis veces el mismo error de `colcon`, y por fin un arreglo

«Summary: 0 packages finished» no compila nada y no parece un error; lo siguiente es reiniciar el
nodo y leer un log del código viejo. Pasó **seis veces en esta sesión**, ya documentado. Y creó
un **workspace parásito** en `src/Atriz_rvr/build`, borrado.

→ Un aviso que se ignora seis veces no es un aviso: es una tarea pendiente. Ahora hay
**`scripts/compilar.sh`**, que se sitúa solo en la raíz, comprueba que compiló algo y detecta el
parásito. Probado a propósito desde el directorio malo: funciona, y encontró el parásito a la
primera.

### ⏳ Abierto

`/color` sigue publicando `(0,0,0)` **con la luz encendida** (166 mensajes). No se investigó y no
se da por bueno — hay que mirar `confidence` y contrastar el servicio contra el topic. Evidencia
36, sección 6.

---

## 2026-07-31 — «¿Está todo el Sphero en ROS?» — No: 27 de 94

Pregunta del usuario al cerrar el día. Se comprobó en vez de darla por buena, y la respuesta
cambia lo que va primero en la próxima sesión.

### Los números

`SpheroRvrAsync` expone **94 métodos públicos**. El driver usa **27**.

### Frente al driver de ROS 1 estamos casi completos… pero no del todo

Tenía 20 servicios; hay **18**, más **cuatro piezas que ROS 1 no tenía** (`set_leds`,
`trigger_led_event`, `set_pos_and_yaw`, y `battery_state` pasó de servicio a **topic**).

🔴 **Pero quedan cuatro huecos sin equivalente**, y el inventario que el propio driver llevaba
en un comentario **no los mencionaba** — decía «16 servicios pendientes», de los que 14 se
portaron esa misma tarde, y se quedó ahí:

- **`reset_odom`** — el locator se resetea al arrancar y **no hay forma de repetirlo en
  caliente**. La web lo va a pedir entre estudiantes. ⚠️ Y al implementarlo hay que decidir y
  **medir** si se re-fija también `yaw₀`: `reset_locator_x_and_y()` **realinea el marco**, no
  solo pone la posición a cero.
- **`ambient_light`** — el SDK lo expone, el sensor está verificado, y no llega a ROS.
- **Recibir IR** — se puede **enviar** pero no recibir, y el tipo de mensaje **ya está definido**
  en `atriz_rvr_msgs` sin que nadie lo publique.
- **Topic `encoders`** — hay servicio, falta el flujo continuo. Son la única fuente que no
  depende del marco de referencia.

Cuatro más están diferidos **a propósito**, cada uno con su razón medida
(`configure_streaming`/`start_streaming`, `enable_color`, `cmd_degrees`, `ir_messages`).

### 🔴 Y lo que más valor tendría no estaba ni en la lista

De los 67 métodos que no llegan a ROS, los que cambian la operación de un laboratorio remoto:

**`motor_stall_notify` y `motor_fault_notify`.** Hoy **un robot con una oruga trabada se ve
exactamente igual que uno que navega mal**. Con 16 robots en otro edificio, esa diferencia es la
que decide si alguien tiene que ir hasta allí.

También: `on_will_sleep_notify` (el RVR **avisa** antes de dormirse — el proyecto lo resolvió con
un keepalive y un detector de silencio), protección térmica de motores, magnetómetro, temperatura
y tensión de batería en voltios (que es lo que haría viable medir el consumo del lidar, pendiente
desde la evidencia 30).

### Lo que sí se puede afirmar

✅ «Todo lo que el laboratorio usaba en ROS 1 está en ROS 2», menos esos cuatro huecos y con
cuatro piezas nuevas. 🔴 **No** «está todo lo que el Sphero puede hacer».

Plan y costes en `00_auditoria/evidencia_24_04/34_que_falta_del_sphero.txt`. Los cuatro huecos son
trabajo de **rclpy**, no de averiguar si el hardware responde: los sensores están verificados
desde el 2026-07-30.

📝 Batería al cerrar la sesión: **26 %** (45 % tras la prueba de Nav2, 34 % al cerrar la parada
de emergencia). El servicio se dejó parado.

---

## 2026-07-31 — Revisión de alineación: la documentación contra el sistema real

Petición: *«revisa que todo lo realizado ahora esté alineado»*. No bastaba con releer — se
contrastó cada afirmación contra el sistema en marcha y contra los ficheros de configuración.

### Afirmaciones vigentes que habían dejado de ser ciertas

`TRASPASO` seguía listando «sin arranque automático — ninguna unidad systemd ⏳ pendiente»
(resuelto hacía una hora). Los conteos del verificador estaban en **84/76** en cuatro ficheros.
`CLAUDE.md` decía «tres fallos propios» cuando iban seis. `INSTALACION` decía «etapas A a F22».
Y `scripts/README` marcaba `fase_7_systemd.sh` como *«probado en seco, nunca se ha arrancado»*
después de haberlo arrancado con un reinicio real.

🔴 **Y una contradicción directa entre dos ficheros:** `fase_1_higiene_so.sh` se declaraba
**NO VERIFICADO en 24.04** mientras su propio `README` decía **✅ ejecutado y verificado**. Se
comprobó en el sistema —governor `performance`, `multi-user.target`, `iw` con power_save `off`,
netplan en 600, arranque de userspace en 16.6 s contra 1 min 39 s— y la razón la tenía el README.

### Dos comprobaciones que parecen fallar y no fallan

Al verificar lo anterior salieron dos trampas nuevas, las dos capaces de hacer creer que la
higiene del SO no funcionó:

- **`systemctl is-enabled cloud-init` dice `enabled`** — se desactiva con el **fichero**
  `/etc/cloud/cloud-init.disabled`, no con systemctl. Las tres unidades están `inactive`.
- **`ps -e | wc -l` da 166 contra el objetivo «< 120»** — pero **86 de esas tareas son de
  `atriz-robot.service`**: el SO solo tiene **80**. Y el objetivo estaba mal planteado de todos
  modos: `ps -e` cuenta ~123 hilos de kernel.

### 🔴 Y el verificador tenía DOS fallos más — van ocho

Los creó el trabajo del propio día, y los dos daban **FALLO sobre un robot recién arrancado y
sano**:

**7 · «el LIDAR no publica» sobre el estado NORMAL del robot.** Cierto que `/scan` daba 0: el
barrido **arranca parado a propósito**. El verificador declaraba roto el reposo. → Ahora, con
`--hardware`, lo **enciende, mide y lo deja como estaba**.

**8 · Contar un comentario como si fuera un ajuste. Otra vez.** Al quitar
`export ROS_DOMAIN_ID=1` del `.bashrc` se dejó un comentario explicando por qué ya no está, y el
`grep -q 'ROS_DOMAIN_ID'` casaba con él: **fallaba justo después de arreglar el problema**. Es el
mismo error que el fallo nº2, repetido a las pocas horas. → Anclado a
`^[[:space:]]*export[[:space:]]+ROS_DOMAIN_ID=`.

### El `.bashrc`, limpiado

`ROS_DOMAIN_ID` y `RMW_IMPLEMENTATION` vivían **en el `.bashrc` y en `/etc/profile.d`**. El
`.bashrc` se lee después y gana, así que un clon de la imagen dorada se habría quedado en el
dominio 1 fuera cual fuera su `robot_id` — la trampa que el propio bloque avisaba. Quitados del
`.bashrc`; los tres tipos de shell siguen dando 1, ahora desde **una sola fuente**.

### Valores contra la configuración real

`robot_radius` 0.145, `desired_linear_vel` 0.40, `radius` 0.18, `base_length` 0.182,
`base_width` 0.217, `laser_z` 0.155, `support_motor_dtr` true — **todos coinciden**. Solo falló
un comentario dentro de `collision_monitor.yaml`, que citaba un `robot_radius: 0.11` corregido a
0.145 ese mismo día.

### Estado final

**91 comprobaciones con `--hardware`** (89 sin él), **0 fallos**. El único aviso que queda es
real: los `.bak` de apt.

---

## 2026-07-31 — Barrido documental: llevar lo de hoy a los sitios donde se busca

Todo lo de esta sesión estaba en el manual, el CHANGELOG y las evidencias. **No estaba donde lo
buscaría alguien que solo quiere operar el robot.** Ocho ficheros corregidos.

### Lo más grave: el RUNBOOK decía cómo arrancar el robot, y ya no era así

Decía *«no hay arranque automático, hay que hacerlo a mano»* y su sección de parada de
emergencia seguía siendo de **ROS 1** (`rostopic`, `rosparam`), afirmando cosas ya arregladas.
Reescritas las dos, más una sección nueva —**«el robot no conduce pero todo lo demás va»**— que
es el síntoma que va a producir el nuevo diseño y que sin explicación parece una avería.

### `medir.py` estaba roto y aun así se recomendaba

Es de ROS 1: muere con `ModuleNotFoundError: rospy`. Seguía en `CLAUDE.md` y en el RUNBOOK como
herramienta de diagnóstico. **Una herramienta rota que se recomienda es peor que ninguna.**
Portada como `medir_ritmo_ros2.py`… y de paso volvió a morder lo mismo:

🔴 **Mi primera versión daba 15.03 Hz mientras su propio intervalo medio decía 60.4 ms** (=16.55).
La diferencia era el descubrimiento de DDS metido en el denominador. Con el ritmo calculado
desde los intervalos: **16.54 Hz**. Van **tres** formas distintas de medir mal una frecuencia en
este proyecto —`ros2 topic hz` (QoS), `spin_once` en bucle (pierde mensajes) y `mensajes/duración`
(descubrimiento)— y las tres dan números **bajos** sobre un robot sano.

### El repositorio del robot describía otro software

`README.md` y `CHANGELOG.md` de `Atriz_rvr` eran **enteros de ROS 1**: catkin, `/cmd_degrees` y
**5 servicios cuando hay 18**. Se conservan —documentan Noetic, que es la ruta de vuelta atrás—
pero ahora lo dicen en la primera línea, y encima llevan una referencia ROS 2 con lo que de
verdad corre. La lista de servicios se sacó **del código**, no de memoria.

### Y una afirmación sobre la web que hoy dejó de ser cierta

`28_pendiente_web.txt` decía que la parada de emergencia «no corta lo que venga de Nav2». Ya sí.
Y se le añadió lo que la Fase 5 **tendrá que** implementar:

🔴 **La web tendrá que llamar a `/start_scan` al empezar cada sesión.** Los robots arrancan solos
pero con el barrido parado, y sin `/scan` el `collision_monitor` bloquea el movimiento. Un robot
recién encendido **no obedece `cmd_vel`**, y desde la web se verá exactamente igual que uno
averiado. Es una línea de código, pero hay que saberla.

### El resto

`README.md` (el estado decía que el siguiente paso era caracterizar la deriva, hecho hace
horas), `INSTALACION.md` (la lista de pendientes repetía «systemd» **tres veces**),
`FLOTA.md`, `RECUPERACION.md` —con un **rescate de un comando** si el arranque automático da
problemas, y la nota de que el SSH no depende de él— y `CLAUDE.md`.

---

## 2026-07-31 — El robot se levanta solo al encender ✅

La prueba que justifica que exista `atriz-robot.service`: en un laboratorio remoto nadie puede
entrar a arrancar un proceso.

```
uptime                  1 min
Active: active (running) since 14:59:28
Main PID: 711 (ros2)                     <- del arranque, no de una mano
ExecStartPost=atriz-escaneo off          status=0/SUCCESS
systemd-analyze         5.5s kernel + 16.6s userspace
```

Y arrancó **en el estado correcto**, comprobado por efecto: `/scan` a **0.00 Hz**, `/odom` a
**16.49 Hz**, `/cmd_vel` con un solo publicador, `collision_monitor` en `active [3]`, y el
`ROS_DOMAIN_ID` viniendo de `/etc/profile.d` —no del `~/.bashrc`, que systemd no lee.

### La afirmación que sostiene el diseño, medida con control

Arrancar con el lidar parado solo es aceptable si el robot **no puede moverse** así:

| barrido | mismo comando por `/cmd_vel_raw` | desplazamiento |
|---|---|---|
| **apagado** | 0.10 m/s · 1.5 s | **0.0 cm** ✅ |
| **encendido** (control) | 0.10 m/s · 1.0 s | **9.9 cm** |

🔴 Sin el control, «0.0 cm» es indistinguible de un `cmd_vel` que nunca llegó.

📝 Corroboración accidental: una primera pasada del control falló por un bug de la herramienta
—esperaba `/odom` 2 s fijos y llegó a los 2.5— pero el robot **sí ejecutó** el comando, y se ve
en la pasada buena: la posición de partida era +0.092 m. Dos medidas del mismo efecto.

### 📝 Lo que NO se ha ejercitado, y no se va a presentar como si sí

- **La espera de puertos del envoltorio nunca ha llegado a esperar**: las tres veces `tras 0s`,
  también en frío. Red de seguridad **sin estrenar**.
- **`Restart=always` tampoco.** Y no arregla el fallo típico de este robot: el RVR dormido deja
  el proceso vivo.
- **n=1.** Un reinicio. Sin corte de corriente ni arranque con el hardware desconectado.

### El coste: cinco fallos, ninguno visible leyendo el código

Dos los cazaron `systemd-analyze verify` y `env -i` antes de instalar. Los otros tres solo
aparecieron al arrancarlo de verdad, y el peor fue **arreglar un fallo en un fichero y no
buscarlo en su hermano**: el `ExecStartPost` murió con `status=1/FAILURE` dejando el servicio
`active (running)` y el barrido **encendido** — el estado exacto que existía para evitar.

Batería al terminar: 34 %. Evidencia 33 · manual cap. 17.

---

## 2026-07-31 — systemd arrancado de verdad: cinco fallos que solo salen al ejecutar

El servicio quedó instalado, habilitado y **arrancado**, y comprobado por efecto:

```
Active: active (running)
ExecStartPost=/usr/local/bin/atriz-escaneo off   status=0/SUCCESS  (10 s)
/scan    0.00 Hz   · barrido parado, que es lo que se pedía
/odom   16.54 Hz   · el robot vive, a la frecuencia de referencia
/cmd_vel Publisher count: 1   · la capa de seguridad intacta
```

### Los cinco fallos, y el patrón que los une

**1 y 2 · antes de instalar** (`systemd-analyze verify` y `env -i`): `StartLimitIntervalSec` en
`[Service]` se ignora, y los `setup.bash` de ROS no son compatibles con `set -u`.

**3 · en el primer arranque real.** El mismo `set -u` **en el script hermano**, que se arregló
en `atriz-robot.sh` y no se buscó en `atriz-escaneo.sh`. El `ExecStartPost` murió con
`status=1/FAILURE`, el servicio quedó `active (running)` gracias al `-` de la unidad, y **el
barrido se quedó encendido** — exactamente el estado que ese `ExecStartPost` existía para evitar.

**4 y 5 · al arreglar el 3.** `ros2 topic echo /scan` se suscribe RELIABLE mientras `/scan` es
BEST_EFFORT (decía «apagado» con el LIDAR a 8 Hz); y ni con `--qos-reliability best_effort`,
porque con `--no-daemon` tiene que **descubrir el tipo** del topic y falla **2 de cada 3 veces**.
Reescrito como suscriptor propio: el tipo se dice, no se descubre. 3 de 3 en los dos estados.

🔴 **El patrón, que es lo que hay que llevarse:** arreglar un fallo en un fichero y **no buscarlo
en sus hermanos**. Costó el único paso que este diseño tenía que garantizar.

### Y un aviso engañoso, también corregido

Al reinstalar sobre un robot ya arrancado, el paso 2/5 señalaba al driver **del propio servicio**
como si fuera un lanzamiento a mano. Ahora se distingue por el cgroup. Un aviso que asusta sin
motivo se acaba ignorando igual que un fallo falso.

### ⏳ Falta

**El `sudo reboot`** — lo único que demuestra que un robot remoto se recupera solo, que es el
motivo por el que existe todo esto. Y añadirlo a `provision.sh` cuando se cierre el robot de
referencia.

Manual, cap. 17.

---

## 2026-07-31 — La parada de emergencia, verificada con control. Y el verificador mentía tres veces

### ✅ El agujero de la parada de emergencia, tapado y demostrado

Stack completo (driver + LIDAR + SLAM + Nav2), los cinco nodos de Nav2 en `active [3]` y
`/cmd_vel` con **un solo publicador**. Mismo protocolo en las dos condiciones:

| | objetivo tras la parada | movimiento al liberar |
|---|---|---|
| **con** `cancelar_nav2` | **CANCELED** | **0.0 cm** ✅ |
| **sin** él (control) | sigue **ACTIVO** | **34.7 cm** 🔴 arrancó solo |

🔴 **El control es la mitad que importa.** La primera pasada sola solo demuestra que el robot se
quedó quieto, no que lo consiga el arreglo. Con el control quedan cuatro medidas de acuerdo en
dos parejas opuestas — y el estado del objetivo lo da el propio action server, no una inferencia.

📝 n=1 por condición, y se acepta: el fenómeno **no es intermitente**, es determinista y trazado
en código. La regla de «replica antes de atribuir» se escribió para el fallo de SLAM, que sí lo
era (~21 %).

### 🔴 Y el verificador tenía TRES fallos más — van seis

Los tres daban veredictos **falsos sobre un robot sano**, que es lo peor que puede hacer un
verificador: uno con falsos positivos se acaba ignorando.

**4 · «el RVR está dormido» con el robot apagado.** La comprobación se guardaba con
`ros2 topic list | grep -qx '/odom'`, y **el daemon de ROS conserva topics de nodos muertos**. →
Mirar el **proceso**, no la lista.

**5 · `ros2 topic hz` no puede medir `/odom`. Nunca pudo.** `/odom` se publica **BEST_EFFORT** y
`ros2 topic hz` se suscribe RELIABLE **sin opción de cambiarlo** en Jazzy: DDS no empareja y da
0 Hz siempre. La misma trampa de QoS que costó la parada de emergencia, esta vez dentro del
verificador. Pasaba desapercibida porque el bloque solo corría si `/odom` aparecía en la lista, y
con el driver parado no aparecía: **una comprobación muerta que contaba como aprobada**.

**6 · Y mi primer arreglo también medía mal: 11.3 Hz sobre un robot a 16.5.** La comprobación
*pasaba* (el umbral es >10), así que habría llevado a «arreglar» un driver sano, a tocar
`streaming_interval_ms` o a documentar una degradación inexistente. Se salvó por comparar contra
el valor de referencia medido — que es exactamente para lo que existe esa tabla.

La causa: **`rclpy.spin_once(nodo, …)` en bucle pierde mensajes**, porque cada llamada engancha y
desengancha el nodo del ejecutor global. Con un `SingleThreadedExecutor` persistente el mismo
robot da **16.53 Hz**, intervalo 60.0 ms de mediana, σ 2.2 ms — o sea la referencia del proyecto,
intacta.

→ La regla, con dos ejemplos nuevos: comprobar el efecto y no la intención, y además
**comprobar el instrumento antes que la medida**.

### Estado del verificador

**86 comprobaciones con `--hardware`** (80 sin él), 0 fallos, 3 avisos — los tres reales: los
`.bak` de apt y las dos cosas de systemd, sin instalar a propósito.

Evidencia: `31_parada_cancela_nav2.txt` y `32_verificador_dos_fallos_mas.txt` · manual cap. 15.4.

---

## 2026-07-31 — La parada de emergencia: la cuarta causa, y estaba mal enunciada

En la lista de pendientes ponía *«la parada no cancela las acciones de Nav2, solo para los
motores»*. **Ese enunciado era falso.** El driver pone una bandera y `_cb_cmd_vel` descarta todo
lo que llega, así que con Nav2 mandando a 10 Hz el robot **sí se queda quieto**.

🔴 **El agujero estaba al LIBERAR.** `/release_emergency_stop` solo baja la bandera. El objetivo
de Nav2 seguía vivo, el `controller_server` nunca dejó de publicar, y no aborta enseguida porque
el progress checker está relajado a 0.25 m en 15 s a propósito. → **En el instante en que la
bandera baja, el robot arrancaba solo**, sin que nadie mandara nada. Que es lo contrario de lo
que debe hacer una parada de emergencia.

📝 Y encaja con el historial: esta función ya había fallado **tres** veces, siempre en silencio y
siempre devolviendo `200 OK` (nombre del topic, namespace, QoS). Esta es la cuarta, y también es
muda.

### El arreglo

Nodo nuevo `cancelar_nav2`, arrancado por `nav2.launch.py`. Llama a `_action/cancel_goal` con un
`CancelGoal.Request` **vacío**, que en `action_msgs` significa **CANCEL_ALL** — así no hay que
seguir la pista de handles que lanzó otro proceso (la web, RViz2, un script).

Va **aparte y no dentro del driver** porque el driver tiene que funcionar sin Nav2. QoS
**VOLATILE** en el suscriptor, no `TRANSIENT_LOCAL`: en un suscriptor no añade garantías, solo
exige que el publicador también lo sea — fue la tercera causa del fallo silencioso.

### Verificado sin mover el robot

El nodo recibe por `/rvr/emergency_stop` —el nombre absoluto que usa la web y que fallaba en
ROS 1— y sin Nav2 degrada bien. Eso cubre las causas 2 y 3. Compilado y comprobado el **efecto**:
el ejecutable instalado existe y el launch instalado lo contiene, sin workspace parásito.

### ⏳ Falta la prueba que importa

**NO VERIFICADO con Nav2 navegando.** Herramienta escrita y lista:
`mediciones_banco/medir_parada_nav2.py`. Necesita ~2.5 m despejados y mide **desplazamiento**,
no velocidad — un robot que arranca y frena da velocidad media ~0 y se ha movido 20 cm, que es
el error que ya se cometió midiendo el watchdog.

Manual, cap. 15.4 · evidencia `00_auditoria/evidencia_24_04/31_parada_cancela_nav2.txt`.

---

## 2026-07-31 — Arranque automático con systemd (escrito, sin arrancar todavía)

En un laboratorio remoto nadie puede entrar a arrancar un proceso: si un robot se reinicia
tiene que volver solo. Escritos `atriz-robot.service`, el envoltorio `atriz-robot.sh`, el
ayudante `atriz-escaneo` y el instalador `fase_7_systemd.sh`.

📝 **NO VERIFICADO de extremo a extremo:** el servicio nunca se ha arrancado bajo systemd.
Instalarlo requiere `sudo`. Lo que sí se ejecutó está abajo.

### Por qué hace falta un envoltorio y no un `ExecStart`

systemd no ejecuta un shell de login: no lee `~/.bashrc` ni `/etc/profile.d`. Un `ExecStart`
directo arrancaría **sin `ROS_DOMAIN_ID`**, o sea con los 16 robots en el dominio 0 viéndose
entre sí — la decisión D1 de `ARQUITECTURA.md` rota, sin ningún error. El envoltorio carga el
entorno, **se niega a arrancar si falta `ROS_DOMAIN_ID`**, espera a udev y hace `exec`.

### El robot arrancará con el barrido del LIDAR apagado

Consecuencia directa de lo medido hoy (11.8 vs 2.7 Hz): sin esto el arranque automático dejaría
el X2 a 11.8 Hz permanentes en los 16 robots. La unidad llama a `atriz-escaneo off` en su
`ExecStartPost`.

⚠️ Y hay que saberlo: **un robot recién arrancado no conduce**. No está roto — sin `/scan` el
`collision_monitor` bloquea el movimiento. Se activa con `atriz-escaneo on`.

### 🔴 Dos fallos que solo aparecieron al ejecutar

Los dos habrían fallado en el primer reinicio, con mensajes que no mencionan ni ROS ni systemd:

- **`StartLimitIntervalSec` en `[Service]` se ignora** — va en `[Unit]`. Lo dijo
  `systemd-analyze verify`. Efecto: bucle de reinicio **sin tope**.
- **Los `setup.bash` de ROS no son compatibles con `set -u`**:
  `AMENT_TRACE_SETUP_FILES: unbound variable`. Con `set -euo pipefail` mata el envoltorio antes
  de arrancar nada. Salió de ejecutarlo con `env -i`; leyéndolo no se ve.

Y un tercero, del propio instalador: creaba el fichero de identidad **durante la fase de
comprobación**, antes de decidir si instalaba, y en simulación el `> /dev/null` se tragaba su
propio aviso. Los dos corregidos.

### Ejecutado y comprobado

- `bash -n` en los tres scripts.
- `systemd-analyze verify` sobre la unidad: limpio tras mover las dos directivas.
- El envoltorio, con `env -i`: **se niega** sin `ROS_DOMAIN_ID` (código 1), y con él recorre
  todo —entorno, RMW, espera de `/dev/rvr` y `/dev/ydlidar`— hasta el `exec`.
- `fase_7_systemd.sh --simular --id 1`: recorre los cinco pasos.

### ⏳ Abierto

**`provision.sh` no instala esto todavía**, así que la imagen dorada saldría sin arranque
automático. Está sin hacer a propósito: mientras se desarrolla en el robot de referencia, un
servicio levantado pelearía por `/dev/rvr` con las pruebas a mano. Es una decisión del usuario.

Manual, cap. 17.

---

## 2026-07-31 — El lidar gira siempre: qué se puede hacer y qué no

Pregunta del usuario, al oír el robot: *«el lidar siempre está girando nada más encender el
sistema. Solo va más rápido cuando se usa. ¿No se ahorraría si girara solo cuando hace falta?»*

### La observación era correcta, y tiene un mecanismo

**DTR no enciende el motor del X2: elige su velocidad.** Medido alternando cada 12 s sin cerrar
el puerto entre tramos —cerrarlo reinicia las líneas de control y falsea la medida—:

| línea | giro (5 tramos) | checksums |
|---|---|---|
| `DTR=1` | 11.86 · 11.77 · 11.85 · 11.85 · 11.76 Hz | 99.8 % |
| `DTR=0` | 2.66 · 2.74 · 2.73 · 2.63 · 2.74 Hz | 99.8–100 % |

**4.3×**, diez tramos, ninguno fuera de sitio. ✅ Y **confirmado por oído**: el usuario escuchó
los dos minutos y reportó «cambio claro cada ~12 s». Dos vías de verdad independientes —una
mecánica, otra el contenido de las tramas— que es lo que este proyecto aprendió a exigir tras
el «confirmado por tres vías» que era una sola.

Además aparecieron `/stop_scan` y `/start_scan`, dos servicios del driver que no estaban
documentados aquí. Verificados en ROS (11.81 → 0.00 → 13.44 Hz) **y por oído**, que es lo que
demuestra que frenan el motor y no solo callan el topic.

### Y el usuario tenía razón en la objeción

*«Entonces simplemente son los estados de cuando el robot se enciende y cuando está escaneando,
o sea que no aporta nada.»* Exacto. **`/stop_scan` no baja de 2.7 Hz**: llega al mismo reposo al
que llega solo el lidar cuando no hay driver. Hoy, con el robot apagándose entre sesiones, no
hay nada que ahorrar — el salto grande ya ocurre solo. Y pararlo del todo no está en la mano del
software: el láser y la electrónica siguen alimentados mientras haya 5 V, y la Pi 4 no puede
cortar VBUS.

### 🔴 Dónde sí importa: el arranque automático, que es lo siguiente

En cuanto los 16 robots levanten `robot.launch.py` solos al encender, el lidar pasará a
**11.8 Hz permanentes, 24/7, en los 16**. Sería *peor* que ahora, y habría llegado como efecto
secundario de una tarea que no habla de lidares. → Las unidades systemd arrancarán con el
escaneo **parado**. La seguridad encaja sola: sin `/scan` el `collision_monitor` no deja
conducir, y eso ya estaba verificado.

### 🔴 Una medida retirada, y la regla que deja

Para saber si `/stop_scan` bajaba DTR se abrió un segundo descriptor sobre el tty y se hizo
`TIOCMGET`: daba `DTR=1` en los dos estados → «no toca el motor». **Falso.** Al validar el
lector poniendo `DTR=0` a propósito seguía diciendo `1`: no solo mentía, **además perturbaba el
estado que medía**, porque `open()` sobre un tty vuelve a levantar la línea.

→ **Antes de creerte un instrumento, pon el sistema en un estado que conozcas y comprueba que
el instrumento lo ve.** Dos minutos, y evitó documentar lo contrario de lo que pasa. El eslabón
se cerró con el oído del usuario, que no toca el puerto serie.

### ⏳ Sin medir, a propósito

**Cuánta corriente se ahorra entre 11.8 y 2.7 Hz: NO MEDIDO.** Serían horas de robot con
`/battery_state` para un número que solo matiza el systemd. Decisión del usuario: documentar y
seguir. No se estima de la ficha — la del RVR ya mintió en las tres dimensiones del robot.

📝 Y un coste que no es eléctrico y puede pesar más: el X2 gira **desde que se enciende la Pi
hasta que se apaga**, siempre. Desgaste de rodamiento continuo en 16 unidades; es el argumento
más fuerte para un interruptor físico en los 5 V.

Evidencia: `00_auditoria/evidencia_24_04/30_lidar_giro_dtr.txt` · manual, cap. 8.4a.

---

## 2026-07-31 — Una suposición aceptada a propósito: `provision.sh` sin probar entero

Cierre del día. `provision.sh` gana hoy la instalación de Nav2 y el verificador sube a 84
comprobaciones, pero **el script nunca se ha ejecutado de principio a fin sobre un Ubuntu
24.04 limpio** — haría falta reflashear rvr-01, que es el único robot montado.

**Decisión del usuario: no se reflashea.** Se asume que funciona hasta tener una tarjeta de
repuesto. Es razonable, y por eso mismo va escrita: la regla 2 del proyecto dice que nada se
documenta sin ejecutarse, así que una excepción consciente se registra en lugar de disolverse.

### Lo que sí se pudo verificar sin reflashear

`bash provision.sh --simular` recorre las nueve secciones y sale con **código 0**. Eso descarta
errores de sintaxis y de lógica en todo el camino. Y el bloque añadido hoy —la comprobación de
los binarios de Nav2— **no se simula**: se ejecuta de verdad, y pasan los cuatro
(`collision_monitor`, `map_server`, `amcl`, `controller_server`). La idempotencia también
responde: reconoce lo ya instalado en vez de repetirlo.

De paso salió un defecto cosmético: las secciones decían «2/7 … 6/7» y luego «7/8, 8/8».
Corregido a `0/8 … 8/8`.

### Lo que sigue sin verificar, que es lo que importa

La simulación convierte en no-operación **justo los pasos que instalan y compilan**: el
`full-upgrade`, el arreglo del UART, la higiene del SO, el `apt install`, compilar YDLidar-SDK
y el `colcon build`. De una pasada limpia no se ha probado **nada** de eso.

🔴 **Consecuencia operativa:** la regla «la imagen dorada es el atajo, `provision.sh` es la
verdad» **supone que el script funciona**, y esa suposición es la que está sin comprobar. El
riesgo no es que falle: es que falle en el robot 7 de 16, con seis ya desplegados.

Marcado en `CLAUDE.md`, `TRASPASO.md`, `INSTALACION.md` y —donde más falta hace— al principio
de `03_operacion/FLOTA.md`, que es la guía que construye la imagen. Detalle en
`00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.

**Se levanta** cuando haya una microSD de repuesto, o cuando rvr-01 deje de ser el único robot.

---

## 2026-07-31 — Barrido de deriva documental, y qué le falta al repositorio web

Cierre de la sesión: revisar que la documentación **no siga afirmando lo que hoy ha dejado de
ser cierto**, y dejar por escrito lo que afecta al tercer repositorio.

### Ocho afirmaciones obsoletas, corregidas

Lo de hoy cambió valores que estaban repetidos por varios ficheros:

| | decía | dice |
|---|---|---|
| plano del LIDAR | 17.45 / 17.5 cm | **15.5 cm** ✅ medido |
| media longitud del chasis | 0.109 m | **0.091 m** |
| el verificador | 50 comprobaciones / 48 aserciones | **84** |

Corregidas en `README.md`, `scripts/README.md`, `RUNBOOK.md`, `INSTALACION.md`, `TRASPASO.md`,
`CLAUDE.md`, `mediciones_banco/README.md` y el manual (dos sitios).

📝 **El `CHANGELOG` no se reescribe**: es el registro de lo que se creía cada día. Donde una
entrada antigua da un valor que luego cambió, se **anota** al lado en vez de falsearla. Y las
derivaciones que resultaron erróneas —como la suma que daba 17.45— **se conservan con su nota**,
porque explican la causa raíz: dos de sus tres sumandos venían de la ficha del fabricante.

### 📌 El tercer repositorio: `Atriz_web_server`

**No está clonado en este robot ni se ha tocado**, y es deliberado: la web es la **Fase 5** por
decisión del usuario, y es un repositorio **público con una credencial expuesta** — meterse ahí
antes de su turno es asumir un riesgo sin necesidad.

Lo que le afecta queda en `28_pendiente_web.txt` (nuevo):

- ✅ **La parada de emergencia ya funciona sin tocar la web.** El driver escucha
  `/rvr/emergency_stop` con `RELIABLE + VOLATILE`, que es el QoS que usa rosbridge por defecto.
  ⚠️ **Pero no corta lo que venga de Nav2**: para una parada de verdad hay que **cancelar la
  acción** `navigate_to_pose`, no solo parar los motores. Sin implementar.
- **18 servicios y 5 topics** disponibles. 🔴 Dos avisos: los de movimiento **se saltan la capa
  de seguridad** (hablan al RVR por el puerto serie), y para teleoperar hay que publicar en
  **`/cmd_vel_raw`**, no en `/cmd_vel`.
- 📝 `/color` publica `[0,0,0]` salvo `color_detection:=true`.
- 🔴 **La credencial sigue expuesta**, y rotarla no basta: hay que quitarla del **historial** de
  git. Acción del usuario, pendiente desde el 2026-07-29.

**Ficheros:** `28_pendiente_web.txt` (nuevo), `README.md`, `scripts/README.md`,
`03_operacion/RUNBOOK.md`, `00_auditoria/evidencia/mediciones_banco/README.md`,
`INSTALACION.md`, `TRASPASO.md`, `CLAUDE.md`, `02_manual/MANUAL_ATRIZ_ROS2.md`.

---

## 2026-07-31 — 🔴 `provision.sh` nunca instalaba Nav2. Verificador de 50 a 84

Evidencia: `00_auditoria/evidencia_24_04/27_provision_verificador.txt`.

Regla del proyecto: **la imagen dorada es el atajo, `provision.sh` es la verdad**. Todo lo hecho
desde la Fase 4b estaba **solo en este robot**.

### 🔴 `provision.sh` no instalaba `navigation2`

El paso 7/8 instalaba `xacro` y `slam_toolbox` y nada más. **Un robot aprovisionado con el
script tenía driver, LIDAR y SLAM — y no podía navegar, ni tenía capa de seguridad, ni
localización.**

De `navigation2` sale mucho más que navegar: `collision_monitor` (cap. 12), `map_server` + `amcl`
(cap. 14) y `map_saver_cli`, la única forma fiable de guardar mapas (cap. 11.11).

✅ Añadido, con la decisión documentada en el propio script —**`navigation2`, no
`nav2-bringup`**, que son 312 paquetes de TurtleBot simulado replicados por 16— y **comprobando
el efecto**: que los binarios existan, no que `apt` dijera que sí.

### `verificar_robot.sh`: de 50 a 84 comprobaciones

Los binarios de Nav2 y 0 paquetes de simulador · los 9 ficheros de config y launch · los
**valores medidos** (`robot_radius` 0.145 en los dos costmaps, URDF 0.182 × 0.217, `laser_z`
0.155) · los valores **por defecto que son decisiones** (`publicar_inclinacion` y
`color_detection` en `false`, `/rvr/emergency_stop`, QoS VOLATILE) · y con `--hardware`, **los
18 servicios**.

🔴 **Preguntando a un CLIENTE, no a `ros2 service list`**, que miente por omisión: dejó fuera
`set_drive_parameters` (17 de 18). Un verificador que usara la lista daría un fallo falso.

### 🔴 Y el verificador tenía TRES fallos propios

Aplicarle su propia regla —«comprobar el efecto»— los sacó:

1. **Comprobaba el driver de ROS 1.** Hacía grep sobre `Atriz_rvr_node.py`, que sigue en el
   repo como herencia: **la comprobación pasaba mirando un fichero que no se ejecuta.** Deriva
   silenciosa, justo lo que el script existe para evitar.
2. **Contaba un comentario.** `grep -c 'robot_radius: 0.145'` daba **3** —los dos ajustes más
   una mención en la cabecera— y fallaba con la configuración **correcta**.
3. **Daba el LIDAR por roto con el robot funcionando.** La prueba abre `/dev/ttyUSB0` en crudo,
   y con el `ydlidar_ros2_driver` vivo el puerto está ocupado. Ahora, si el driver corre, se
   comprueba por **`/scan`** — y es mejor prueba, porque cubre el driver ROS y el QoS. Medido:
   **89 barridos en 8 s, ~11 Hz**.

> 📝 **Un verificador con falsos positivos se acaba ignorando, y eso es peor que no tenerlo.**

### Resultado

```
sin --hardware   76 correctas · 1 aviso · 0 fallos
con --hardware   84 correctas · 1 aviso · 0 fallos
```

⏳ **`provision.sh` NO se ha ejecutado de principio a fin desde estos cambios.** Es idempotente y
el paso 7 se probó a mano, pero una pasada completa sobre un 24.04 limpio sigue **sin
verificar** — y es lo que decide si la imagen dorada sale bien.

**Ficheros:** `scripts/provision.sh`, `scripts/verificar_robot.sh`,
`27_provision_verificador.txt` (nuevo), `TRASPASO.md`, `INSTALACION.md` (F22 ✅ → F23),
`CLAUDE.md`.

---

## 2026-07-31 — ✅ Los servicios del driver, de 1 a 18. Y `/color` nunca funcionó

Evidencia: `00_auditoria/evidencia_24_04/26_servicios_driver.txt`, manual **cap. 16** (nuevo).
Herramienta nueva: `mediciones_banco/medir_sensor_color.py`.

### Los 18, portados en orden de riesgo

Primero lo que no mueve nada, para poder probarlo en banco sin espacio:

```
lecturas    get_encoders · get_system_info · get_control_state · get_rgbc_sensor_values
luces       set_led_rgb · set_multiple_leds · set_leds · trigger_led_event
IR          send_infrared_message · set_ir_mode · set_ir_evading (⚠️ este sí mueve)
config      set_drive_parameters · set_pos_and_yaw
movimiento  move_timed · raw_motors · move_to_pose · move_to_pos_and_yaw
```

Verificados **contra el robot**, no solo por que respondan:

```
move_timed  2 s a 0.15 m/s   ->  30.3 cm medidos contra 30   (101 %)
raw_motors  reversa 25 %     ->  30.7 cm, para al mandar modo 0
move_to_pos_and_yaw 0.20 m   ->  19.5 cm                     ( 97 %)
```

✅ **Y la parada de emergencia los bloquea**: `success=False` y **0.0 cm** de desplazamiento.

### 🔴🔴 `/color` llevaba publicando `[0,0,0]` desde siempre

Lo destapó una pregunta del usuario. **El sensor no da nada sin su luz** — medido:

| | Claro |
|---|---|
| sin luz | **4** |
| con luz | **741** |

**185×.** Y el driver **nunca la encendía**: el topic existía, publicaba a 16 Hz, y el dato era
oscuridad. Estaba en la lista de «verificado» desde la Fase 2.

🔴 **Y no se puede encender bajo demanda:** con el streaming de `color_detection` ya
configurado, `enable_color_detection` **no hace nada** — 481 mensajes de `/color`, todos ceros,
durante la llamada. La primera versión del servicio hacía justo eso y devolvía oscuridad con
`success=True`.

✅ **Arreglado** con el parámetro `color_detection` (por defecto `false`), que lo enciende
**antes** del streaming. Con `false`, el driver **avisa por el log**. Verificado: `/color` pasa
a dar `[164, 140, 119]` y el servicio 735 en el canal claro.

### 🔴 Y un fallo mío, que vio el usuario

El driver encendía el sensor y **no lo apagaba al morir**: el LED blanco se quedaba encendido
gastando batería. Es exactamente lo que avisa `CLAUDE.md` —«cada `(True)` necesita su `(False)`,
también en el camino de error»— cometido dos horas después de leerlo, y **lo detectó el ojo del
usuario, no el código**. Arreglado en `_apagar_rvr()`: apaga sensor y LEDs. Verificado,
`clear=733` → **`clear=0`** tras SIGINT.

### Lo que no se portó tal cual, y por qué

- **`set_pos_and_yaw` solo acepta (0,0,0)** y rechaza el resto **en vez de fingir**: el SDK no
  puede fijar una pose arbitraria, y `reset_yaw()` no hace nada.
- **`trigger_led_event`**: el RVR no tiene «eventos de LED». Se traducen a colores fijos.
- **`uptime_ms`**: el SDK no lo expone. Se dice en el `message` en vez de dejar un cero mudo.
- **`ConfigureStreaming` / `StartStreaming`: no portados a propósito** — pueden romper la
  telemetría del propio driver.

### ⚠️ Los servicios de movimiento se saltan la capa de seguridad

No publican en ningún topic: hablan al RVR por el puerto serie, así que ni el
`collision_monitor` ni el watchdog los ven. Solo los para la **parada de emergencia**. Y
`raw_motors` no tiene corte automático.

### 📝 `ros2 service list` no es autoritativo

Omitió `set_drive_parameters` (17 de 18) mientras `ros2 service type` sí lo encontraba y un
cliente con `wait_for_service` decía **disponible**. Es descubrimiento de DDS.
→ **Para saber si un servicio existe, usa un cliente.** En `CLAUDE.md`.

**Ficheros:** `rvr_driver_node.py`, `robot.launch.py`, `26_servicios_driver.txt` (nuevo),
`medir_sensor_color.py` (nuevo), manual cap. 16, `TRASPASO.md`, `INSTALACION.md` (F21 ✅ → F22),
`CLAUDE.md`.

---

## 2026-07-31 — 🔴 La parada de emergencia fallaba por TRES causas. Arreglada

Evidencia: `00_auditoria/evidencia_24_04/25_parada_emergencia.txt`, manual **cap. 15** (nuevo).

### Las tres, y las tres en silencio con `200 OK`

| | Causa | Cuándo |
|---|---|---|
| 1ª | **nombre de topic**: la web publica en `/rvr/emergency_stop`, el driver escuchaba `is_emergency_stop` | ROS 1, auditoría |
| 2ª | **namespace**: al portar se arregló el nombre y se coló el `/rvr/` | ROS 2, hoy |
| 3ª | **QoS incompatible** | ROS 2, hoy |

**La segunda.** El driver se suscribía a nombres **relativos**, que con el namespace vacío
resuelven a `/emergency_stop` y `/is_emergency_stop`:

```
$ ros2 topic info /rvr/emergency_stop
  Unknown topic '/rvr/emergency_stop'      ← el que usa la web
```

📝 Y el `TRASPASO.md` decía «el topic ya existe en el driver ROS 2». Existe **un** topic; no el
que la web usa. Corregido.

**La tercera, y solo aparece probándolo.** Con el nombre ya correcto:

```
New publisher discovered on topic '/rvr/emergency_stop', offering incompatible QoS.
No messages will be received from it. Last incompatible policy: DURABILITY
```

El driver se suscribía `RELIABLE + TRANSIENT_LOCAL`, justificado con «así un suscriptor que
llegue tarde recibe el último estado». **Ese razonamiento es del publicador.**

> 🔴 **En el suscriptor, `TRANSIENT_LOCAL` solo RESTRINGE:** exige que el publicador también lo
> sea, y ninguno lo es por defecto — ni `ros2 topic pub`, ni **rosbridge**, que es por donde
> hablará la web. `VOLATILE` empareja con todo y es estrictamente más compatible.

### ✅ El arreglo, verificado

El driver escucha **también `/rvr/emergency_stop`** (absoluto) y el QoS pasa a
`RELIABLE + VOLATILE`. Disparando los tres nombres uno a uno:

```
/rvr/emergency_stop  ✅   /emergency_stop  ✅   /is_emergency_stop  ✅
avisos de "incompatible QoS": 0 · paradas: 3 · liberaciones: 3
```

⚠️ **Tres suscripciones para una función es feo, y a propósito**: el modo de fallo de este botón
es «no llega el mensaje» y ha fallado dos veces por eso. La Fase 5 unifica a uno, **no antes**
de que el nuevo esté probado de extremo a extremo.

📝 **La lección de método:** las causas 2 y 3 **solo aparecen publicando de verdad**. Leer el
código da el nombre pero no el namespace resuelto ni el QoS; `ros2 topic list` da el namespace
pero no el QoS. En `CLAUDE.md`.

### 🔴 Y lo que sigue sin estar

**La parada no corta lo que venga de Nav2.** Pone el flag del driver, que ignora `cmd_vel` —
pero Nav2 seguiría mandando objetivos y su controlador publicando. Habría que **cancelar la
acción** además de parar los motores. **Sin comprobar.**

### 📝 De paso: workspace parásito borrado

Buscando el fichero instalado apareció `src/Atriz_rvr/{build,install,log}` — el parásito que
documenta `CLAUDE.md`, de los dos `colcon build` desde el directorio equivocado. Estaba inerte
(tenía `COLCON_IGNORE`) pero confunde. Borrado, 1.1 MB.

Y queda aclarado cómo funciona `--symlink-install` aquí: el módulo instalado **apunta al fichero
fuente**, así que editarlo cambia el comportamiento sin reinstalar. Pero `colcon build` sigue
haciendo falta para los launch y los YAML de bringup, que **sí** se copian.

**Ficheros:** `rvr_driver_node.py`, `25_parada_emergencia.txt` (nuevo), manual cap. 15,
`TRASPASO.md`, `INSTALACION.md` (F20 ✅ → F21), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Fase 4c: `map_server` + AMCL, y Nav2 navegando sobre el mapa

Evidencia: `00_auditoria/evidencia_24_04/24_fase4c_amcl.txt`, manual **cap. 14** (nuevo).
Nuevos: `config/localizacion_amcl.yaml` y `launch/localizacion.launch.py`.

### ✅ El ciclo completo, de principio a fin

```
a) MAPEAR con slam_toolbox         celdas 486 → 2774
b) GUARDAR con map_saver_cli       mapa_amcl.pgm, 5989 bytes
c) PARAR SLAM                      `map` deja de existir  ✅ punto de partida limpio
d) LOCALIZAR                       map_server y amcl active [3]
                                   map → odom: (−0.004, 0.011), yaw +0.65°
e) ¿SIGUE LA POSE?  60 cm          ODOM 61.8 · AMCL 61.9 · dif 0.1 cm  ✅
f) NAVEGAR con Nav2 sobre el mapa  SUCCEEDED, error 8 cm
                                   ODOM 73.4 · AMCL 72.3 · dif 1.1 cm  ✅
```

### 🔴 AMCL cuesta CASI EL DOBLE que SLAM — al revés de lo que suponía

| | CPU | RAM |
|---|---|---|
| `slam_toolbox` | **4.8 %** | 49.1 MB |
| `amcl` + `map_server` | **8.8 %** | 85.9 MB |

En el YAML había escrito «se espera menos, pero **se mide, no se supone**». Menos mal.

**El argumento para AMCL no es la CPU: es el marco compartido.** 16 robots sobre un mismo `map`
es lo que permite que la web diga «ve a la mesa 3» y que todos entiendan lo mismo. Con 16 SLAM
hay 16 mapas del mismo sitio, cada uno con su origen.

⚠️ **Nota de método que afecta a números ya publicados:** `ps -o %cpu` da el **promedio desde
que arrancó el proceso**, no el instantáneo. Las cifras de arriba se midieron muestreando
`/proc` dos veces con 20 s. Las anteriores del proyecto usaron `ps`; `slam_toolbox` vuelve a
salir 4.8 % con el método bueno, así que el orden de magnitud aguanta. En `CLAUDE.md`.

### ✅ Dos salvaguardas en el launch, probadas

🔴🔴 **AMCL y `slam_toolbox` publican los dos `map → odom`.** Juntos parten el árbol TF **sin dar
ningún error** — es el fallo que costó la Fase 4. El launch **se niega a arrancar** si
`slam_toolbox` está vivo, y también si el mapa no existe (y entonces dice cómo hacerlo).

📝 La comprobación usa `ps -eo comm`, **no `pgrep -f`**: el patrón de `-f` casa con la propia
línea de comando y eso ya ha matado la terminal dos veces en este proyecto.

### ⚠️ Lo que NO está resuelto

🔴 **La σyaw crece:** 6.7° tras avanzar 60 cm, **18.0°** tras navegar 80. Es mucho. La sospecha
es que el mapa es pequeño y poco distintivo, pero **no está comprobado**.

🔴 **La pose inicial.** AMCL cree que el robot está en (0,0,0). Si no lo está, empieza
equivocado y puede no recuperarse. ⏳ **Para la flota tendrá que venir por robot.**

⚠️ Y estas pruebas comprobaron la **consistencia** de la pose con la odometría (0.1 y 1.1 cm),
**no su corrección absoluta** — para eso haría falta una referencia externa medida con cinta.

**Ficheros:** `config/localizacion_amcl.yaml` (nuevo), `launch/localizacion.launch.py` (nuevo),
`24_fase4c_amcl.txt` (nuevo), manual cap. 14, `mapas/mapa_amcl.*` (nuevo), `TRASPASO.md`,
`INSTALACION.md` (F19 ✅ → F20), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Decidido: no se persigue el roll, y el driver deja de publicarlo

Decisión del usuario, y una consecuencia que **no** se deriva de ella.

### La decisión

**No se persigue el efecto del roll en la deriva.** Cerrarlo costaría **~62 corridas y
5.2 horas de robot** para un efecto de ~1 cm sobre una tolerancia de objetivo de Nav2 de
**10 cm**.

### 🔴 Pero eso no deja el roll publicado — son dos preguntas distintas

| | |
|---|---|
| ¿**afecta** la inclinación a la deriva? | sin responder, y se acepta así |
| ¿**existe** la inclinación? | **respondida: no** (cap. 13.3) |

Suelo plano medido con nivel (≤0.40°), error del acelerómetro **fijo en el marco del robot**, y
`\|g\|` un **3.8 % corto**. **Publicar 6.9° que no existen en `odom → base_footprint` es
publicar un dato que sabemos incorrecto**, se pueda medir su efecto o no. REP-105 espera ahí la
pose del robot.

✅ **Aplicado:** `publicar_inclinacion` pasa a **`false` por defecto**, en el driver y en
`robot.launch.py`. Verificado sobre el sistema instalado:

```
ros2 param get /rvr_driver publicar_inclinacion  ->  False
/odom  ->  roll +0.00°  pitch +0.00°   (296 muestras)
```

⚠️ Con `publicar_inclinacion:=true` se recupera lo anterior. Haría falta si un robot trabajara
en una superficie inclinada de verdad — pero entonces hay que **calibrar antes el
acelerómetro**, que no acierta ni el módulo.

📝 **Consecuencia para el futuro:** si algún día se mete `robot_localization` para fusionar la
IMU, hay que saber que ese sensor da una gravedad con **3.8 % de error de módulo y ~6.9° de
dirección**. Fusionarlo tal cual metería ese error en la pose.

**Ficheros:** `rvr_driver_node.py`, `robot.launch.py`, manual cap. 13.5 y 9.12d,
`23_referenciar_posicion.txt`, `TRASPASO.md`, `INSTALACION.md` (F18 ✅ → F19), `CLAUDE.md`
(nueva fila en «Decisiones ya tomadas»). Y `deriva_roll_resultados.jsonl` pasa a
`deriva_roll_tanda3.jsonl`, para que la siguiente tanda no lo pise.

---

## 2026-07-31 — ✅ Referenciar la posición: los fallos de SLAM desaparecen

Herramienta nueva: `mediciones_banco/referenciar_posicion.py`, que
`caracterizar_deriva_slam.py` llama **antes de cada corrida**. Evidencia:
`23_referenciar_posicion.txt`, manual **cap. 9.12c–9.12d**.

### ✅ El robot se queda donde debe — y esto no depende de ninguna estadística

| | adelante | derecha |
|---|---|---|
| **sin** referenciar | rango **0.47 m** | rango **0.81 m** (monótono) |
| **con** referenciar | rango **0.06 m** | rango **0.03 m** |

**8× menos dispersión hacia delante, 27× lateral**, y la deriva monótona desaparece.

### ✅ Y con ella, los fallos

| | fallos > 5 cm | peor caso |
|---|---|---|
| tandas 1+2, **sin** referenciar | **5 de 24** | **56.1 cm** |
| tanda 3, **con** referenciar | **0 de 12** | **4.4 cm** |

Las doce: `0.5 0.5 0.7 0.7 0.9 0.9 1.1 2.1 2.2 3.7 3.7 4.4`. **La distribución deja de ser
bimodal.**

⚠️ **Honestidad estadística:** Fisher exacto de 0/12 contra 5/24 da **p = 0.113** — sugerente,
**no concluyente al 5 %**. Con una tasa base del 21 %, sacar 0 de 12 por azar tiene un 6 % de
probabilidad. Lo indiscutible es la tabla de posiciones.

### ✅ Y la deriva NO crece con la distancia

```
CORTA (158 cm, n=6)   mediana 1.55 cm
LARGA (233 cm, n=6)   mediana 0.90 cm    ← recorre un 47 % más y sale MEJOR
```

Desmonta definitivamente la narrativa del fichero 14 («0.63 % del recorrido en las cortas,
1.14 % en las largas»). ✅ **Para Nav2: 1–4 cm en recorridos de 1.6–2.3 m**, muy por debajo de
la tolerancia de objetivo de 10 cm. **La localización deja de ser un bloqueante.**

### Cómo funciona, y dos decisiones que importan

Ajusta una recta a la pared frontal en el marco del robot —`x = m·y + c` da el rumbo `atan(m)`
y la distancia perpendicular `c·cos(θ)`— y entonces conduce a la distancia objetivo y se alinea.

🔴 **El orden es distancia y DESPUÉS rumbo**, y salió probando: al revés, conducir vuelve a
torcer el rumbo recién corregido (medido, **+0.41° → +2.53°**). Girar sobre el eje no cambia la
distancia perpendicular, porque el centro del robot no se mueve.

🔴 **No usa `/odom` ni el mapa, a propósito:** referenciar con odometría sería circular — es
justo lo que se está midiendo.

Precisión: **±0.2 cm y ±0.2°** en dos pasadas seguidas. La tolerancia se dejó en 3 cm porque la
frenada del RVR se come 1–2 cm y pedir menos impediría converger.

### ⚠️ La pregunta del roll: ahora se intuye, y sigue sin resolverse

```
CON roll  n=6  media 2.23 cm      SIN roll  n=6  media 1.33 cm      diferencia +0.90 cm
```

📝 **Las dos distancias apuntan en el mismo sentido**, cosa que antes no pasaba: CORTA +1.30 cm,
LARGA +1.40. El roll **siempre** sale peor, y la magnitud coincide con la predicha —`cos(6.9°)`
comprime los alcances un 0.7 %.

⚠️ **Pero p = 0.142** (permutación exacta sobre 924 particiones). Con n=6 por rama, no.

⏳ Con d = 0.64 harían falta **~31 corridas por rama → ~62 en total, unas 5.2 horas de robot**.
El efecto es de ~1 cm sobre una tolerancia de objetivo de 10 cm: **es una decisión, no un
pendiente automático.**

### Menor

⏳ `comparar_deriva_roll.py` captura la salida de `caracterizar_deriva_slam.py` y solo extrae
las líneas de CORTA/LARGA: **los residuos de cada referenciado se pierden**. Deberían ir al
`.jsonl` para poder cruzarlos con la deriva.

Batería, tercera medida: 69 % → 59 % en la tanda 3 — gasta más que las anteriores porque el
referenciado añade movimiento (bloques de 3.5 min en vez de 2.7). Estimación conjunta de las
tres tandas: **~0.5–0.9 %/min** conduciendo.

**Ficheros:** `mediciones_banco/referenciar_posicion.py` (nuevo),
`caracterizar_deriva_slam.py`, `23_referenciar_posicion.txt` (nuevo), manual cap. 9.12c–9.12d,
`deriva_roll_tanda1.jsonl` / `tanda2.jsonl` / `resultados.jsonl`, `TRASPASO.md`,
`INSTALACION.md` (F17 ✅ → F18), `CLAUDE.md`.

---

## 2026-07-31 — 🔴 La réplica desmonta mi conclusión: no es la distancia, es que el robot se va

Se repitió el experimento de deriva **con el mismo protocolo, una hora después**, añadiendo una
sola cosa: **registrar dónde está el robot** antes de cada bloque. Evidencia:
`22_replica_deriva.txt`, manual **cap. 9.12b**.

### 🔴 El fallo cambió de distancia

| | TANDA 1 | TANDA 2 (réplica) |
|---|---|---|
| CORTA (158 cm) | 1.0, 1.0, 1.2, 2.1, 2.2, 2.9 → **0 de 6** | 0.8, 0.8, 1.6, 2.7, **6.6**, **14.3** → **2 de 6** |
| LARGA (233 cm) | 0.9, 1.1, 1.2, **12**, **16**, **56** → **3 de 6** | 1.0, 1.9, 2.5, 2.7, 3.0, 3.3 → **0 de 6** |

En la tanda 1 fallaban las largas y las cortas iban perfectas. En la 2, al revés. **La distancia
no es la variable**, y la conclusión que escribí hace una hora —«SLAM es fiable hasta 1.6 m y
deja de serlo a 2.3 m»— **queda retirada**.

📝 Era coherente con sus datos y estaba equivocada. Es exactamente para lo que sirve replicar.

### Las 24 corridas juntas — lo que sí se sostiene

```
CORTA (n=12)   normales (10): mediana 1.40 cm, rango 0.8–2.9  ·  fallos (2): 6.6, 14.3  → 17 %
LARGA (n=12)   normales  (9): mediana 1.90 cm, rango 0.9–3.3  ·  fallos (3): 12, 16, 56 → 25 %
GLOBAL: 5 fallos de 24  →  ~21 %
```

✅ **Cuando funciona va bien, y casi igual a las dos distancias** (1.40 vs 1.90 cm) — lo que
además desmonta la narrativa del fichero 14 de que la deriva crecía proporcionalmente al
recorrido. Sus **medianas eran correctas**; lo que no vio con n=3 es **la cola**.

🔴 **Y una de cada cinco corridas falla**, de forma bimodal: o ≤3.3 cm o ≥6.6 cm.

### 🔴 La causa más probable: el robot se va del sitio y nadie lo corrige

| bloque | adelante | der | CORTA | recorrido |
|---|---|---|---|---|
| A1 | 2.06 m | **0.97** | **6.6** 🔴 | 159 |
| B1 | 2.11 | 0.42 | 1.6 | 158 |
| A2 | 2.01 | 0.30 | 0.8 | 156 |
| B2 | **1.64** | 0.26 | **14.3** 🔴 | **137** |
| A3 | 1.73 | 0.19 | 0.8 | 156 |
| B3 | 1.73 | **0.16** | 2.7 | 153 |

🔴 **`der` cae de forma monótona: 0.97 → 0.16 m.** El robot deriva a la derecha corrida tras
corrida y acaba **a 5 cm de rozar** (media anchura 11 cm). Y en la tanda 1: **94 cm de deriva
hacia delante en 12 corridas**, ~8 cm cada una.

> **La consecuencia de método, que es la importante:** `caracterizar_deriva_slam.py` y
> `comparar_deriva_roll.py` asumen que el robot vuelve al punto de partida y que las N corridas
> son repeticiones del **mismo** experimento. **No lo son.** Eso no es una repetición: es un
> barrido por posiciones distintas, sin control ni registro.

⏳ **El arreglo, no implementado:** re-referenciar la posición antes de cada corrida con `/scan`.
Hasta entonces ninguna de las dos herramientas da una distribución válida.

### La pregunta del roll, aplazada por tercera vez

La única comparación sin fallos dentro fue LARGA: **2.70 contra 2.50 cm**, diferencia de 0.20 cm
con σ 1.19 — **compatible con cero**. Pero con n=3 por rama y un efecto de ~1 cm eso **no
permite decir que el roll no afecte**: solo que no se ve. Y no se verá hasta controlar la
posición.

**24 corridas y hora y media de robot sin responder la pregunta** — porque el banco de pruebas
no controla la variable que más se mueve.

### Detalles menores

- El registro del entorno **falló en silencio** la primera vez (devolvía `None`): usé `repr()`
  en vez de `shlex.quote()` para pasar el código al shell, y `repr()` escapa los saltos de línea.
  Se pilló **probándolo antes** de lanzar.
- Consumo de batería, segunda medida: 81 % → 73 % en la tanda 2, más lento que la 1 (92 → 85).
  Estimación conjunta **~0.5–0.8 %/min** conduciendo, 2–3 h por carga. Sigue siendo gruesa.

**Ficheros:** `22_replica_deriva.txt` (nuevo), `21_deriva_roll_y_fallo_largo.txt` (retractación
de su sección 3), manual cap. 9.12a (retractado), 9.12b (nuevo) y 13.6,
`mediciones_banco/comparar_deriva_roll.py` (registro del entorno),
`deriva_roll_tanda1.jsonl` + `deriva_roll_resultados.jsonl`, `TRASPASO.md`,
`INSTALACION.md` (F16 ✅ → F17), `CLAUDE.md`.

---

## 2026-07-31 — 🔴 SLAM falla el 50 % a 2.3 m, y la inclinación es del acelerómetro

Evidencia: `00_auditoria/evidencia_24_04/21_deriva_roll_y_fallo_largo.txt`, manual **cap. 13**
(reescrito) y **9.12a** (nuevo). Herramienta nueva: `mediciones_banco/comparar_deriva_roll.py`.

### 🔴 El hallazgo: a 2.3 m, la mitad de las corridas fallan

Se iba a medir si el roll de la IMU empeora la deriva. **No respondió esa pregunta** — apareció
algo mayor. 12 corridas, `slam_toolbox` reiniciado de cero en cada una:

```
CORTA (158 cm, n=6)   0.9  1.0  1.0  1.2  2.1  2.2  2.9
  -> mediana 1.65 cm · peor 2.9 cm · corridas > 5 cm: 0 de 6        ✅

LARGA (233 cm, n=6)   0.9  1.1  1.2  |  12.0  16.0  56.1
  -> mediana 6.60 cm · peor 56.1 cm · corridas > 5 cm: 3 de 6  🔴 el 50 %
```

🔴 **Es BIMODAL: o ~1 cm o ≥12 cm, sin nada en medio.** No es deriva gradual — es el emparejado
de barridos **enganchando o perdiéndose**. Los errores angulares acompañan: 0.9–2.4° en las
buenas, **5.2–28.1°** en las malas.

**Corrige la caracterización anterior**, que con n=3 por distancia **tuvo suerte**:

| | fichero 14 (n=3) | ahora (n=6) |
|---|---|---|
| CORTA mediana | 1.0 cm | 1.65 cm |
| LARGA mediana | 2.7 cm | **6.60 cm** |
| **peor caso** | 3.2 cm | **56.1 cm** 🔴 |

**Y resucita la anomalía de la Fase 4** — aquella corrida de 2.62 m con 87.8 cm y 10.9° se
atribuyó a que el robot rozó obstáculos, y el fichero 14 la dio por explicada. **Es el mismo
fallo bimodal: no era una anomalía, es la mitad de las veces.**

⚠️ **Consecuencia para Nav2:** SLAM es fiable hasta ~1.6 m de recorrido y deja de serlo a
~2.3 m. Las navegaciones que salieron bien (8–10 cm de error) eran de **0.9–1.5 m**: por debajo
del umbral. **Objetivos más largos entran en la zona donde SLAM se pierde la mitad de las
veces.** Con 16 robots y estudiantes, no es desplegable así.

⏳ Causa sin determinar. Los tres fallos fueron corridas largas **contiguas** (2ª, 3ª y 4ª),
repartidas entre las dos ramas del experimento, y decrecientes (56.1 → 16.0 → 12.0). La firma
temporal apunta a algo del entorno que cambió y volvió, pero **no hay evidencia** y no se le
atribuye causa.

### ✅ La inclinación: es el acelerómetro, no el robot — tras dos retractaciones

**La cifra correcta:** `roll +1.10°`, `pitch +6.74°`, **total ~6.9°**. La documentación decía
«~8° de **roll**»: son ~6.9° y están casi todos en el **pitch**. ⚠️ Y **se reparten según el
rumbo** — lo único estable es el módulo.

🔴 **Dos conclusiones retiradas, y ninguno de los dos argumentos valía:**

1. «No existe, el LIDAR está nivelado en 4 puntos» — **la regla mide desde el SUELO**, así que
   no distingue «nivelado respecto al chasis» de «horizontal respecto a la gravedad».
2. «Es física, el pitch cambia de signo al girar 180°» — **el cambio de signo solo dice que el
   error está en el marco del MUNDO**, y eso lo producen dos causas: suelo inclinado **o**
   referencia de gravedad torcida. Presenté como resuelto un caso con dos explicaciones.

✅ **Lo que sí lo zanja**, y es el acelerómetro **crudo** porque no pasa por ninguna fusión:

| | ANTES | DESPUÉS del giro de 177.8° | |
|---|---|---|---|
| pitch | +6.72° | **−6.99°** | cambia de signo |
| `accel.x` | −1.091 | **−1.158** | **NO cambia** |

Error **fijo en el marco del robot** + suelo plano medido con nivel (≤0.40°) = **el sensor está
descalibrado**. Lo confirma el módulo: `|g| = 9.435` contra 9.807, **3.8 % corto**. Y no es la
referencia de arranque: se apagó, se dejó plano en el suelo y se encendió allí — igual.

⏳ **Sin explicar:** por qué el cuaternión fusionado gira con el rumbo mientras el sesgo del
acelerómetro no. Una traza de 90 s descarta que sea un transitorio. Se deja como pregunta
abierta, **sin inventarle mecanismo**.

### El experimento del roll queda sin responder

| | | mediana | σ |
|---|---|---|---|
| CORTA | CON roll / SIN roll | 2.10 / 1.20 cm | 0.95 / 0.64 |
| LARGA | CON roll / SIN roll | 1.10 / 12.00 cm | 8.66 / 29.08 |

El efecto buscado era de ~1 cm y la dispersión de las largas es de 30. **No se puede concluir
nada**, y repetirlo no serviría hasta arreglar el fallo bimodal.

📝 **El diseño alternado sí cumplió su función**: deja ver que los fallos **no** se reparten por
condición (1 CON roll, 2 SIN roll). Con 6 y 6 en bloque habrían caído todos en una rama y
habrían parecido su causa.

### 🔴 Un falso positivo del guardián — que aun así fue lo correcto

El primer lanzamiento abortó a los 2 min: el guardián comprobaba solo el **roll**, que valía
+0.11° porque la inclinación estaba entera en el pitch. Arreglado a `hypot(roll, pitch)`.
**Mejor un falso positivo a los 2 min que 45 min de datos con el interruptor sin efecto.**

### ✅ Consumo de batería — un dato que el proyecto no tenía

**92 % → 85 %** en 6 bloques; mediana **2 puntos** por bloque de 2.7 min → **~0.74 %/min**, del
orden de **2 horas de conducción** por carga. ⚠️ Estimación gruesa: `/battery_state` va en pasos
de 1 %, los bloques son cortos y el ritmo cayó (1.12 → 0.74 → 0.37 %/min).

**Ficheros:** `21_deriva_roll_y_fallo_largo.txt` (nuevo), `14_deriva_slam_caracterizada.txt`
(aviso de superado), manual cap. 13 (reescrito) y 9.12a (nuevo),
`mediciones_banco/comparar_deriva_roll.py` (nuevo), `caracterizar_deriva_slam.py`,
`medir_slam_ros2.py`, `TRASPASO.md`, `INSTALACION.md` (F15 ✅ → F16), `CLAUDE.md`.

---

## 2026-07-31 — ⏳ Interruptor del roll de la IMU: puesto y verificado, medida pendiente

Para poder **medir** si el roll falso de ~8° contribuye a la deriva de SLAM, en vez de
suponerlo. Evidencia: `20_interruptor_inclinacion.txt`, manual **cap. 13.4–13.5**.

### ✅ El interruptor

```bash
ros2 launch atriz_rvr_bringup robot.launch.py publicar_inclinacion:=false
```

Nuevo parámetro del driver, **por defecto `true`** (el comportamiento de siempre). Con `false`,
`_h_quaternion` pone `roll = pitch = 0` antes de componer la orientación que va a `/odom` y a
TF. **Verificado**: `roll +0.00° pitch +0.00°` sobre **414 muestras**.

Es un interruptor de **medición**, no de operación: el valor por defecto no se cambia hasta
tener el número.

### El diseño de la prueba, y por qué no se puede recortar

- 🔴 **La línea base anterior no vale.** Las 6 corridas del fichero 14 se hicieron con
  `laser_z = 0.1745`, y el desplazamiento lateral que induce el roll **escala con esa altura**:
  `0.1745 × sin(8°) = 2.4 cm` entonces, **2.2 cm ahora**. Hay que rehacer las dos mitades.
- 🔴 **Las condiciones se ALTERNAN**, no 6 con roll y luego 6 sin él. Si la batería corta a
  mitad, los datos siguen **balanceados**; y el nivel de carga y el calentamiento dejan de
  poder colarse como variable — que es el tipo de confusión que ya costó una retractación.
- ⚠️ **No se puede bajar a 2 corridas por condición.** El efecto buscado es de ~**1 cm** y la
  dispersión ya medida es **σ = 0.6–1.0 cm**: saldría dentro del ruido. Hacen falta ≥3
  repeticiones de cada distancia por condición — **12 corridas**.

⏳ **Pendiente de ejecutar.** Son ~40 min de robot moviéndose y la batería estaba al **34 %**.
Se decidió **cargar primero**: el consumo del RVR por minuto **no está medido**, y arriesgar un
corte a mitad daría un «no concluyente» habiendo gastado la carga.

### 🔴 Trampa nueva: una excepción en un manejador mata `/odom` en silencio

Montando el interruptor se escribió la asignación contra `self._silence_timeout` cuando la
variable real del driver se llama **`self._timeout_silencio`**. La línea no se insertó y
`self._publicar_inclinacion` quedó **usada sin existir**:

| | |
|---|---|
| `AttributeError` en `_h_quaternion` | **ni una línea en el log** |
| `/odom` y `/imu` | **cero mensajes**, con los topics existiendo |
| `/scan` | funcionando |
| el detector de silencio | **no saltó** |

Y no salta **por diseño**: mide el tiempo desde la última **muestra del RVR**, no desde la
última publicación. Las muestras llegaban — se ve el `origen del yaw fijado en +10.2°` en el
log, que sale de la primera. Lo que fallaba era el manejador que las convierte.

> **Atajo de diagnóstico:** si `/scan` va y `/odom` no, **y no hay error ni aviso de silencio**,
> sospecha de una excepción dentro de un manejador. El síntoma «el topic existe y no publica»
> es idéntico al de un RVR dormido, pero **el RVR dormido sí dispara el detector de silencio**.

📝 Es la **tercera** vez que el proyecto se topa con un fallo que no da error. Las anteriores:
el árbol TF partido y `slam_toolbox` en `unconfigured`. En `CLAUDE.md`.

### 📝 `/battery_state.percentage` es una fracción 0–1

Es lo que manda `sensor_msgs/BatteryState` («Charge percentage on 0 to 1 range») y el driver lo
respeta: `0.34` son **34 %**. Leerlo como 0–100 hace que un robot al 34 % parezca estar al
**0 %** — provocó una falsa alarma de batería agotada en esta misma sesión. En `CLAUDE.md`.

⏳ Y deja al descubierto un dato que el proyecto **no tiene** y que hará falta con 16 robots:
**cuánto consume el RVR por minuto conduciendo**.

**Ficheros:** `atriz_rvr_driver/scripts/atriz_rvr_driver/rvr_driver_node.py`,
`atriz_rvr_bringup/launch/robot.launch.py`, `20_interruptor_inclinacion.txt` (nuevo),
manual cap. 13.4–13.5, `mediciones_banco/caracterizar_deriva_slam.py` (17.5 → 15.5 cm),
`TRASPASO.md`, `INSTALACION.md` (F14 ✅ → F15), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Paradas contra pared re-medidas: el recálculo era correcto

Los huecos publicados estaban **recalculados, no vueltos a medir** — la corrección de las cotas
del robot había cambiado la constante sin repetir el experimento. Repetido con el robot ya bien
modelado (media longitud 0.091, `laser_z` 0.155, `wheel_radius` 0.035) y `radius: 0.18`:

| velocidad | n | **medido** | recalculado | dif |
|---|---|---|---|---|
| 0.25 m/s | 1 | **9.9 cm** | 9.8 | +0.1 |
| 0.40 m/s | 2 | **10.6 / 10.7 cm** | 10.8 | −0.2 |

**Las diferencias son de 1–2 mm**, por debajo de la resolución útil de la medida. Y **repite**:
las dos corridas a 0.40 dan 10.6 y 10.7, 1 mm de dispersión.

### El modelo, afinado

```
asíntota = radius − media longitud = 0.18 − 0.091 = 8.9 cm
a 0.25 m/s  →  9.9 cm    margen +1.0 cm
a 0.40 m/s  → 10.65 cm   margen +1.8 cm
```

📝 **El margen crece con la velocidad**, lo que confirma con más resolución lo que ya se había
visto: `approach` empieza a frenar antes cuanto más rápido va, así que la holgura **no se
degrada al acelerar — mejora**.

📝 Y cambiar `laser_z` (0.1745 → 0.155) y `wheel_radius` (0.032 → 0.035) **no alteró el
comportamiento**, como se preveía: son traslaciones en Z y el monitor trabaja en el plano. Los
números lo confirman en vez de suponerlo.

Comprobado al arrancar, con el URDF nuevo: `base_footprint → laser` = `[0.000, 0.000, 0.155]`,
exactamente lo medido con la regla.

**Ficheros:** `17_collision_monitor.txt` (bloque «RE-MEDIDO»), manual cap. 12.4,
`03_operacion/MEDIDAS_ROBOT.md`, `TRASPASO.md`, `INSTALACION.md` (F13 ✅ → F14), `CLAUDE.md`.

---

## 2026-07-31 — ✅ El robot medido entero, y la «inclinación de ~8°» resulta no existir

El usuario midió todas las cotas de
[`03_operacion/MEDIDAS_ROBOT.md`](03_operacion/MEDIDAS_ROBOT.md) con el robot apagado sobre
suelo plano. Evidencia: `19_paso_estrecho.txt` (ampliación), manual **cap. 13** (nuevo) y 12.8.

### La ficha del RVR mentía en las tres cotas

| | medido | URDF (ficha) |
|---|---|---|
| frente-atrás | **18.2 cm** | 21.8 |
| lado a lado | **21.7 cm** | 18.5 |
| suelo → tapa | **7.0 cm** | 11.4 |
| ancho de oruga | **3.5 cm** | 2.5 |
| `wheel_separation` (entre centros) | **18.3 cm** | 15.0 |

✅ **Y cierra solo:** `14.8` (borde interno a borde interno) `+ 2 × 3.5 = 21.8 ≈ 21.7` de ancho
total. **Las orugas ocupan todo el ancho del robot** — ahí estaban los 4.5 cm que no cuadraban
en la entrada anterior.

### 🔴 El plano de barrido está 2 cm más abajo de lo documentado

`laser_z` era una **suma derivada** con la altura del RVR sacada de la ficha. Medido en cadena:

```
suelo → tapa del RVR                 7.0 cm
tapa  → base del LIDAR (piso extra)  4.6 cm
base del LIDAR → centro del disco    3.9 cm
────────────────────────────────────────────
suelo → CENTRO DEL DISCO            15.5 cm   ← laser_z
suelo → extremo superior            16.5 cm
```

Comprobación cruzada: `7.0 + 4.6 + 5.0` (alto del LIDAR) `= 16.6 ≈ 16.5`. ✅

**El límite «por debajo de X cm el robot no ve nada» pasa de 17.45 a 15.5 cm**: el robot ve
**mejor** de lo que decíamos. Un error en `laser_z` es una traslación pura en Z, así que **no
afecta a SLAM 2D ni a Nav2** — solo a la visualización y a ese límite.

### 🔴 Y la «inclinación de ~8°» no existe

Un problema abierto desde el principio, cerrado **con una regla**.

El usuario midió del suelo al disco del LIDAR **en cuatro puntos** —delante, detrás, izquierda,
derecha— y salen **iguales**. El disco mide ~7.6 cm: 8° habrían dado **~1.1 cm** de diferencia.
Se habrían visto. **El robot está físicamente horizontal.**

Y las «**tres vías independientes**» que lo confirmaban **no eran independientes**:

| «vía» | de dónde sale de verdad |
|---|---|
| árbol TF | de `odom.pose.pose.orientation`… |
| cuaternión del RVR | …que el driver copia del cuaternión, **que calcula la IMU** |
| acelerómetro | el **mismo chip** |

**Una sola fuente contada tres veces.** El árbol TF no confirmaba nada: **repetía**. El driver
llevaba un comentario explícito —«esa inclinación es real, no un error de referencia»— apoyado
en esa falsa independencia. Corregido.

> Es la regla nº4 del proyecto fallando por el lado contrario: no se atribuyó sin medir, se
> **midió tres veces lo mismo** creyendo que eran tres cosas. Anotado en `CLAUDE.md`: **antes
> de decir «confirmado por N vías», traza de dónde sale el dato de cada una.**

⏳ **Consecuencia, SIN APLICAR:** el driver publica un roll falso de ~8° en `/odom` y en TF. Un
roll en `odom → base_footprint` inclina el plano del láser y comprime los alcances por
`cos(8°) = 0.990` — un **1 %**, ~1 cm por metro. La deriva de SLAM medida es de **1–3 cm** en
1.6–2.4 m: **el orden de magnitud coincide**, así que podría ser parte de ella.

La corrección es una línea (`roll = pitch = 0.0`) y **no se aplica sin medirla**, porque
hacerlo a ciegas sería repetir el error que la creó. Hace falta repetir
`caracterizar_deriva_slam.py` con y sin, y comparar.

### Ajuste fino

Media longitud 0.090 → **0.091**: los huecos publicados bajan 1 mm (9.9 → **9.8 cm** a 0.25
m/s, 10.9 → **10.8** a 0.40). El radio circunscrito sigue en **0.142**, así que
`robot_radius: 0.145` no cambia.

### ✅ Y el modelo cierra: `wheel_radius` **3.5 cm**, LIDAR centrado

La última cota, medida también: **3.5 cm** del suelo al centro del eje (la ficha decía 3.2). Y
el usuario confirmó el **centrado** del LIDAR con las cotas nuevas.

**El modelo cuadra ahora por dos caminos independientes:**

```
wheel_radius 0.035  →  oruga de 0.070 de diámetro
base_height         =  0.070   (medido del suelo a la tapa)
→ la caja del chasis va DEL SUELO A 7 cm, justo como se ve el RVR:
  las orugas ocupan todo el alto del lateral.

0.148 + 2 × 0.035 = 0.218 ≈ 0.217 de ancho total medido.
```

Verificado sobre el URDF compilado: `base_footprint → base_link` = 0.035, láser a **0.155 m**
sobre el suelo (= lo medido, exacto), caja del chasis de 0.000 a 0.070.

✅ **No queda ninguna cota medible sin medir.** Solo `imu_z` (0.05, suposición), que exige abrir
el robot y hoy no afecta a nada: la IMU no se fusiona con la odometría.

**Ficheros:** `atriz_rvr_description/urdf/rvr.urdf.xacro`,
`atriz_rvr_driver/scripts/atriz_rvr_driver/rvr_driver_node.py` (comentarios del cuaternión),
`03_operacion/MEDIDAS_ROBOT.md`, manual **cap. 13** (nuevo) y 12.3–12.10,
`19_paso_estrecho.txt`, `mediciones_banco/medir_collision_monitor.py`, `TRASPASO.md`,
`INSTALACION.md` (F12 ✅ → F13), `CLAUDE.md`.

---

## 2026-07-31 — 🔴 El paso de 40 cm no se cruza, y el URDF tenía las cotas cruzadas

Evidencia: `00_auditoria/evidencia_24_04/19_paso_estrecho.txt`, manual **cap. 12.10**.

### El límite, medido

Con `radius: 0.18` el robot **entró en la boca de un paso de 40 cm y se quedó bloqueado**:

```
ang −84°…−99°   objeto derecho, a 22 cm del centro
ang +72°…+87°   objeto izquierdo, a 17 cm del centro
al frente, a menos de 60 cm: NADA
```

No tocaba nada y tenía el camino despejado delante. Lo paró el monitor porque su círculo mide
18 cm y el borde estaba a 17: **le sobraba 1 cm**. ✅ Salió marcha atrás (58 cm) — `approach`
en vez de `stop`, otra vez.

📝 **Nav2 no llegó a intentarlo**: con el paso abierto por los lados (65 y 63 cm) el
planificador se fue por la ruta ancha, que es lo correcto. La prueba que responde es conducir
recto por `/cmd_vel_raw`, sin planificador que pueda escaquearse.

**No es un fallo: es el compromiso, ahora cuantificado.**

| `radius` | para a | pasillo mínimo |
|---|---|---|
| 0.14 | 5 cm | 28 cm |
| **0.18** | **9 cm** | **36 cm** ← el actual |
| 0.20 | 11 cm | 40 cm |

Para 16 robots en un laboratorio **remoto donde nadie puede levantarlos**, parar a 9–11 cm de
las paredes vale más que cruzar huecos de 40 cm. Es una **decisión de laboratorio**.

### 🔴 Y por el camino: el URDF tenía largo y ancho cruzados

El usuario midió el robot con una cinta, de punta a punta y con orugas:

| | medido | URDF (ficha, «NO MEDIDO») |
|---|---|---|
| frente-atrás | **18 cm** | 21.8 cm |
| lado-lado | **22 cm** | 18.5 cm |

**Dos consecuencias, de distinto peso:**

1. Los huecos publicados hoy salían **2 cm cortos** (media longitud 0.109 en vez de 0.09):
   8.0 → **9.9 cm** a 0.25 m/s, 9.0 → **10.9 cm** a 0.40. El modelo
   `hueco ≈ radius − media longitud + 1 cm` **no se cae**, solo cambia la constante, y las
   conclusiones del fichero 17 siguen valiendo. Están **recalculados, no vueltos a medir**.
2. 🔴 **`robot_radius: 0.11` estaba mal, y eso sí es un error real.** Lo escribí llamándolo
   «radio circunscrito» y es aritmética mal hecha: el circunscrito es **0.142** con las cotas
   medidas y **0.143 incluso con las del URDF**. Con cualquiera de los dos se queda corto — el
   planificador puede trazar rutas donde una **esquina** roza, **sin dar ningún error**. Lo
   tapaba el `collision_monitor` con sus 0.18, que es probablemente por qué `approach` saltaba
   al rodear obstáculos. **Corregido a 0.145** en los dos costmaps.

URDF corregido a 18 × 22. Solo cambia la caja de colisión y la inercia: las ruedas usan
`wheel_separation`, independiente, así que **ningún frame TF se mueve**.

### Nuevo: `03_operacion/MEDIDAS_ROBOT.md`

Lista **todas** las cotas del modelo, cuáles están medidas y cuáles vienen de una ficha, y qué
se rompe si cada una está mal. Lo urgente: **`laser_z`** —la altura a la que el robot ve, hoy
**derivada** de dos fichas de fabricante— y **si el LIDAR está nivelado**, que es la mejor
pista sobre la inclinación de ~8° que sigue abierta.

Explica también qué es `wheel_separation` y por qué aquí **no hace nada**: el RVR resuelve su
propia cinemática, así que solo dibuja las orugas en RViz. Pero está **inconsistente** —
0.150 + 0.025 dan 17.5 cm de oruga a oruga contra 22 cm de robot.

### Dos errores propios

- **Un `radius: 0.15` de contraste que no vale.** Lo lancé para dar la curva completa del
  compromiso y **midió otro hueco** (33.9 cm a −61.5° de rumbo, porque el robot se había
  reorientado). Cruzó *un* hueco, no *el* hueco. Descartado; el valor volvió a 0.18.
- **El X2 no ve un objeto fino en un solo barrido.** Los dos objetos daban 2 y 3 puntos; con un
  `/scan` suelto desaparecen y el detector de huecos deja de ver el paso. Los escaneos que
  funcionaron acumulaban 6–8 s. En `CLAUDE.md`.

**Ficheros:** `atriz_rvr_description/urdf/rvr.urdf.xacro`, `config/nav2_atriz.yaml`,
`config/collision_monitor.yaml`, `mediciones_banco/medir_collision_monitor.py`,
manual cap. 12.3–12.5 y 12.10, `19_paso_estrecho.txt` (nuevo), `17_collision_monitor.txt`
(aviso de corrección), `03_operacion/MEDIDAS_ROBOT.md` (nuevo), `TRASPASO.md`,
`INSTALACION.md` (F11 ✅ → F12), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Rodea obstáculos, y la seguridad hacía abortar a Nav2

Cierra la última laguna: hasta ahora todo se había probado **contra una pared frontal**, así
que estaba demostrado que el robot **para**, no que **rodee**. Evidencia:
`00_auditoria/evidencia_24_04/18_rodear_obstaculo.txt`, manual **cap. 11.13**.

### El obstáculo, caracterizado antes de mover nada

Con `/scan`, y el salto en las distancias es lo que lo **aísla de las paredes** — un umbral
tonto tipo «menos de 1.6 m» las etiqueta a ellas también:

| ángulo | dist | |
|---|---|---|
| −3° | 2.54 m | abierto |
| **0°…+9°** | **0.75–0.77 m** | ← obstáculo |
| +12° | 2.07 m | abierto |

A **0.75 m**, ~**16 cm de ancho**. El robot mide 18.5 cm: **bloquea la línea recta**. Holgura a
su altura: 63 cm por la derecha, 44 por la izquierda.

Los requisitos que se le pidieron al usuario salían todos de un número medido: **más de 25 cm
de alto** porque el plano del LIDAR está a 17.45 cm *(⚠️ ese valor se corrigió después a
**15.5 cm** — era derivado; ver la entrada del robot medido)*; **50 cm libres a un lado** porque el
`collision_monitor` trata al robot como un disco de 36 cm.

### ✅ Lo rodea, y de forma repetible

Objetivo a 1.50 m, **el mismo que la corrida limpia**, para que el obstáculo fuera la única
variable:

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

Siempre por el lado con más hueco y con el mismo desvío. **8–9 cm de error: el mismo que sin
obstáculo** — rodear no degradó la precisión.

### 🔴 El hallazgo: la capa de seguridad hacía abortar a Nav2

```
[controller_server] [ERROR] Failed to make progress
[controller_server] [WARN]  [follow_path] [ActionServer] Aborting handle.
```

El objetivo acabó en `SUCCEEDED` porque el árbol replanificó, pero el aborto es real y en un
paso más estrecho podría no recuperarse.

El `SimpleProgressChecker` de fábrica exige **0.5 m en 10 s = 5 cm/s**, y el
`collision_monitor` había frenado al 40 % (0.16 m/s) y `approach` bajó más la velocidad junto
al obstáculo.

> **Con una capa de seguridad delante, ir despacio ya no es prueba de estar atascado** — que es
> lo único que ese comprobador debería detectar. Un robot de verdad atascado se mueve 0 m y lo
> sigue disparando igual.

Relajado a **0.25 m en 15 s** (1.7 cm/s). Tras el cambio, en cuatro navegaciones:
`Failed to make progress` **0**, `Aborting handle` **0**, recuperaciones **0**,
`Control loop missed` **0** — y la seguridad **sí trabajó**: 2 `approach` + 5 `slowdown`,
8.1 s de frenado.

### ✅ `save_map`: hipótesis confirmada y arreglo verificado

La entrada anterior dejaba el arreglo propuesto **sin verificar**. Probado:

| | Resultado |
|---|---|
| servicio de `slam_toolbox`, timeout de 2 s | `0`, **`255`**, `0` — falla ~1 de cada 3 |
| `map_saver_cli` con `save_map_timeout:=10.0` | **`Map saved successfully`** |

Confirma la causa deducida —una carrera contra el `map_update_interval: 5.0`— y **el
procedimiento bueno pasa a ser `map_saver_cli`, no el servicio**. En `CLAUDE.md`.

**Ficheros:** `atriz_rvr_bringup/config/nav2_atriz.yaml`, manual cap. 11.11 y 11.13–11.14,
`18_rodear_obstaculo.txt` (nuevo), `mapas/mapa_rodeo.pgm`, `TRASPASO.md`,
`INSTALACION.md` (F10 ✅ → F11), `CLAUDE.md`.

---

## 2026-07-31 — ✅ Navegando a 0.40 m/s, el máximo del robot

`desired_linear_vel` sube de 0.25 a **0.40**. Evidencia:
`00_auditoria/evidencia_24_04/16_nav2_preparacion.txt` (sección final), manual **cap. 11.10**.

Se sube con las tres condiciones cumplidas y **medidas**, no por optimismo:

1. el robot navegó dos veces sin incidentes a 0.25 (cap. 11.7);
2. el `collision_monitor` está puesto y verificado (cap. 12);
3. y **a 0.40 la capa de seguridad deja *más* hueco que a 0.25** — 9.0 cm contra 8.0 —, porque
   `approach` empieza a frenar antes cuanto más rápido va. Ese es el dato que quitaba el miedo.

### Lo que había que comprobar no era que llegara, sino que fuera a 0.40

Perfil en `/odom` durante la ida de 1.50 m:

| t | v |
|---|---|
| 0.31 s | 0.057 m/s |
| 0.61 s | 0.357 m/s |
| **0.91 s** | **0.407 m/s** ← meseta |
| 2.00 s | 0.407 m/s |

Máxima 0.431 · percentil 90 **0.412 m/s**. Coherente con la rampa de ~0.5 s ya medida y con
`max_linear_accel: 0.8`.

| | Desde | Hasta | Resultado | Error | v (p90) |
|---|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.50, 0.00) | **SUCCEEDED** | **8 cm** | 0.412 m/s |
| vuelta | (1.42, −0.01) | (0.00, 0.00) | **SUCCEEDED** | **8 cm** | 0.409 m/s |

📝 **8 cm las dos veces, contra 9–10 cm a 0.25 m/s: subir la velocidad no empeoró la
precisión.** La vuelta tardó 16 s para 1.42 m, giro de 180° incluido.

### La capa de seguridad no estorbó

Cuatro frenados en toda la sesión —2125, 1582, 130 y 65 ms—, **ninguno una parada**, cero
conductas de recuperación y cero fallos de plan. ⚠️ No se ha aislado **qué** los disparó: se
registra el hecho, no una causa inventada.

### 🔴 Y salió un fallo nuevo: `save_map` da 255 de forma intermitente

```
[map_saver] Saving map from 'map' topic to '…' file
[map_saver] [ERROR] Failed to spin map subscription
```

**No es el fallo de la Fase 4.** Aquel era `Package 'nav2_map_server' not found` y se arregló
instalando `navigation2`. Aquí el paquete está, el `map_saver` arranca, se configura y **se
queda sin mapa**: perseguir la instalación sería perder el tiempo.

Causa, deducida de dos números del propio sistema: `map_update_interval: 5.0` en slam_toolbox
contra el `save_map_timeout: 2.0` por defecto del saver. **Es una carrera** — explica que
funcionara dos veces y fallara la tercera.

⏳ **Arreglo propuesto, NO VERIFICADO:** reintentar; o `map_saver_cli` con
`save_map_timeout:=10.0`; o bajar `map_update_interval`, que cuesta CPU. Hace falta resuelto
para la Fase 4c. Anotado en `CLAUDE.md` como trampa de diagnóstico.

**Ficheros:** `atriz_rvr_bringup/config/nav2_atriz.yaml`, manual cap. 11.10–11.12 y 12.9,
`16_nav2_preparacion.txt`, `TRASPASO.md`, `INSTALACION.md` (F9 ✅ → F10), `CLAUDE.md`.

---

## 2026-07-31 — ✅ La capa de seguridad: el robot para antes de chocar

`collision_monitor` configurado, medido contra una pared y verificado. Evidencia:
`00_auditoria/evidencia_24_04/17_collision_monitor.txt`, manual **cap. 12**.

### La decisión de arquitectura: no va con Nav2

El ejemplo oficial lo pone con la navegación. Aquí no, y la razón sale del propio proyecto:
**los estudiantes teleoperan sin Nav2** —la web hablará por rosbridge (plan, Fase 5)—, así que
con el monitor colgando de `nav2.launch.py` el caso peligroso de verdad, una persona
conduciendo el robot contra una pared **desde otro edificio**, no estaría protegido.

Vive en `robot.launch.py`, con su propio `lifecycle_manager`. Y la regla que lo hace funcionar:

```
    Nav2 (velocity_smoother) ─┐
    web / rosbridge          ─┼─► /cmd_vel_raw ─► collision_monitor ─► /cmd_vel ─► driver
    teleop / scripts         ─┘
```

**`/cmd_vel` tiene un solo publicador.** Publicar ahí funciona —el driver obedece— pero salta
la seguridad sin dar ningún aviso.

### 🔴 Un agujero real, encontrado contando publicadores

```
$ ros2 topic info /cmd_vel --verbose
Publisher count: 6      ← behavior_server ×5  +  collision_monitor
```

El `behavior_server` abre **un publicador por conducta** (`spin`, `backup`,
`drive_on_heading`, `wait`, `assisted_teleop`). Los cinco publicaban directamente al robot. Y
es el peor sitio posible: las conductas de recuperación se ejecutan justo cuando el robot está
**atascado**, o sea pegado a algo — `backup` habría retrocedido a ciegas.

Arreglado con un remapeo. **No lo delataba ningún error**: solo salió de mirar el número.

### 🔴 `approach` no es una parada de seguridad, y lo puse mal

Primera configuración, `radius: 0.11` (el `robot_radius` de los costmaps). El robot paró a
**1.1 cm de la pared**. El monitor actuó —el log muestra `slowdown` y `approach`—; lo que
estaba mal era mi modelo:

> `approach` escala la velocidad para que el choque caiga justo en `time_before_collision`.
> Según baja la distancia baja la velocidad, así que el robot se acerca **asintóticamente al
> contacto**. Es un frenado suave, no una parada.

Con media longitud de chasis 0.109 m, la asíntota era 0.1 cm. **Funcionó exactamente como está
escrito.** La holgura se consigue **inflando el círculo**: `hueco ≈ radius − 0.109 + ~1 cm`.

### ✅ Medido con `radius: 0.18`

| velocidad | recorrido | **hueco real** | predicción |
|---|---|---|---|
| 0.25 m/s | 191 cm | **8.0 cm** | 8 cm |
| 0.40 m/s | 191 cm | **9.0 cm** | — |

A 0.40 m/s —el máximo del robot— para **más lejos**, no más cerca: el controlador empieza a
frenar antes cuanto mayor es la velocidad.

### ✅ No queda atrapado, y sin LIDAR no conduce

Los dos polígonos son `approach` y `slowdown`, **nunca `stop`**, y la razón es operativa: un
`stop` fijo para *cualquier* movimiento mientras haya algo dentro, así que un robot pegado a
una pared se congela. En un laboratorio **remoto no hay nadie que lo levante**.

| Prueba | Resultado |
|---|---|
| escape desde 1.1 cm pegado a la pared | retrocedió **196 cm** ✅ |
| `kill -9` al LIDAR + comandar 0.10 m/s 2.5 s | **0.0 cm** ✅ bloqueado |
| Nav2 con la seguridad en medio | **SUCCEEDED**, 9 cm de error, 39 cm a la pared |

⚠️ Salir de un rincón es **lento**: la caja de precaución sigue viendo la pared y frena al
40 %. Conviene saberlo antes de pensar que el robot no responde.

### 🔴 El límite que ninguna configuración arregla

El plano de barrido del X2 está a **17.45 cm del suelo**. Todo lo más bajo —un zócalo, una
regleta, un pie de mesa que se ensancha abajo— es **invisible** y el robot lo embestirá sin
frenar. No es un fallo de configuración: es lo que un LIDAR 2D puede ver. **Tiene que ir en
las instrucciones a los estudiantes.**

📝 Lo que sí está cubierto: el `range_min: 0.1` del X2, montado en el centro, deja su punto
ciego **dentro del chasis**. No hay zona muerta alrededor del robot.

### Y un error propio, dos veces

Me maté el shell dos veces con `pgrep -f "…[y]"`: el truco del corchete protege de que el
patrón se encuentre a sí mismo, **no** de que la cadena buscada aparezca en otra parte de la
misma orden (un heredoc con la ruta, un `nohup` más abajo). Documentado en `CLAUDE.md` junto a
la trampa de `pkill -f` que ya estaba, con la alternativa: matar por `comm` con `ps`, sin `-f`.

**Ficheros:** `atriz_rvr_bringup/config/collision_monitor.yaml` (nuevo),
`launch/robot.launch.py`, `launch/nav2.launch.py`,
`mediciones_banco/medir_collision_monitor.py` (nuevo), manual cap. 12,
`17_collision_monitor.txt` (nuevo), `TRASPASO.md`, `INSTALACION.md` (F8 ✅ → F9),
`CLAUDE.md`.

---

## 2026-07-31 — ✅ Nav2 NAVEGA: primera navegación autónoma

**El robot llega solo a un punto del mapa.** Dos objetivos completados, ida y vuelta:

| | Desde | Hasta | Resultado | Error final |
|---|---|---|---|---|
| ida | (0.00, 0.00) | (1.00, −0.03) | **SUCCEEDED** | **10 cm** |
| vuelta | (0.90, 0.00) | (0.00, 0.00) | **SUCCEEDED** | **9 cm** |

El error coincide con la `xy_goal_tolerance: 0.10` configurada — el controlador para al entrar
en tolerancia, así que **no es casualidad**.

### El riesgo del QoS de `/scan` era infundado

Se avisaba en el cap. 11.6 de que un desemparejamiento BEST_EFFORT/RELIABLE dejaría el costmap
**vacío sin dar error**. Comprobado: `/scan` acabó con **tres** suscriptores —`slam_toolbox`,
`local_costmap` y `global_costmap`— todos BEST_EFFORT. Nav2 usa el perfil de datos de sensor,
que empareja con el driver.

Y no basta con que estén suscritos: se verificó que los costmaps **ven obstáculos de verdad**
— 905 celdas ocupadas en el local (60×60), 1983 en el global (148×139).

### 🔴 El primer objetivo abortó, y no era la configuración

```
[controller_server] [ERROR] [RPPPathHandler]: Exception in transformPose:
  Lookup would require extrapolation into the future … from frame [odom] to frame [map]
```

Antes de tocar nada se midió, en vez de suponer (regla nº4):

| Sospecha | Medido |
|---|---|
| ¿faltan tolerancias? | RPP **0.2**, costmaps **0.3** — puestas |
| ¿`use_sim_time` incoherente? | **False** en los cinco nodos, en SLAM y en el driver |
| ¿`map → odom` con huecos? | **50.0 Hz**, mediana 20.0 ms, **máximo 25 ms**, cero huecos > 200 ms |

**Era transitorio**: el buffer TF del controlador aún no se había llenado con los nodos recién
arrancados. El segundo objetivo, idéntico, funcionó.

⚠️ **Consecuencia práctica: dar unos segundos entre activar Nav2 y mandar el primer objetivo.**
Un `ABORTED` inmediato tras arrancar **no** significa que la configuración esté mal. Queda en
el manual (11.8) porque es exactamente el tipo de falso positivo que hace perder una tarde.

### El Pi 4 aguanta el stack entero

~**89 %** de un núcleo y ~477 MB entre los nueve procesos (driver 19.7 %, `bt_navigator`
14.4 %, `controller_server` 13.1 %…). `loadavg` **2.53** sobre 4 núcleos, **58.9 °C**,
`throttled=0x0`, RAM 1.5 GB de 7.6.

**Nav2 solo son ~58 % de un núcleo**: es la pieza más pesada con diferencia, como se preveía —
pero **queda margen para `rosbridge`** en la Fase 5.

### Lo que esto NO prueba

Las dos navegaciones fueron **en línea recta por un pasillo despejado**. Se ha probado que el
robot **llega**; no que **rodee** un obstáculo. Eso queda pendiente, junto con el
`collision_monitor` —la capa de seguridad, necesaria antes de dejar esto con estudiantes— y
subir `desired_linear_vel` de 0.25 a 0.40 (el robot llega a 0.40, ya medido).

Mapa guardado: `mapas/mapa_nav2_navegado.pgm` (20726 bytes).

**Ficheros:** `00_auditoria/evidencia_24_04/16_nav2_preparacion.txt` (sección final),
manual cap. 11.7–11.10, `TRASPASO.md`, `INSTALACION.md` (F7 ✅ → F8 = `collision_monitor`),
`CLAUDE.md` (valores de referencia).

---

## 2026-07-31 (parte 7) — Nav2 instalado, y otra retractación mía

### Nav2: `navigation2`, NO `nav2-bringup`

Comprobado **antes** de instalar nada:

| | Paquetes | Qué arrastra |
|---|---|---|
| `ros-jazzy-navigation2` | **309** | lo que se usa: amcl, bt-navigator, controller, costmap-2d, planners, `map-server`… |
| `ros-jazzy-nav2-bringup` | **621** | lo anterior **+ Gazebo**: `nav2-minimal-tb3-sim`, `tb4-sim`, `ros-gz-sim`, y `pocketsphinx-en-us` |

`nav2-bringup` son ficheros de ejemplo para TurtleBot **en simulador**. Los launch de Atriz los
escribimos nosotros, igual que con `slam_toolbox`, y esos 312 paquetes acabarían replicados en
los **16 robots** vía imagen dorada.

**Instalado y verificado:** 30 paquetes `nav2`, los diez que importan presentes, **cero** de
simulador, y el disco sube solo 900 MB (5.4 → 6.3 GB).

### ✅ `save_map` arreglado — el diagnóstico de la Fase 4 era correcto

Con `nav2-map-server` instalado, `/slam_toolbox/save_map` devuelve **`result=0`** y genera el
`.pgm` + `.yaml` que Nav2 carga. Antes fallaba con `result=255` y el error real solo aparecía
en el log de slam_toolbox: `Package 'nav2_map_server' not found`.

### La configuración de Nav2, con los valores medidos

`atriz_rvr_bringup/config/nav2_atriz.yaml` + `launch/nav2.launch.py`. **Todos** los valores del
robot sustituidos por los medidos:

| | Atriz | Ejemplo de Nav2 (TurtleBot) |
|---|---|---|
| `robot_radius` | **0.11 m** | 0.22 m — **el doble** |
| `max_vel` lineal | 0.40 m/s | 0.26 m/s |
| `max_vel` angular | 2.0 rad/s | 1.0 rad/s |
| alcance del LIDAR | **8.0 m** | 20.0 m |

El `robot_radius` es el que más duele: con 0.22 el robot se negaría a pasar por huecos por los
que cabe de sobra. Y un `raytrace_max_range` de 20 m haría que Nav2 despejara como «libre»
espacio que el sensor **nunca midió**.

Decisiones, con su porqué: **RPP** y no MPPI/DWB (mucho más barato en un Pi 4 que ya lleva el
driver al 23 %), **NavFn** y no Smac (el robot gira sobre su eje), costmap local de **3 × 3 m**,
`lookahead_dist: 0.4` escalado al robot, y **`desired_linear_vel: 0.25`** aunque llegue a 0.40 —
es la primera vez que navega solo.

**NO se configuran `map_server`/`amcl`**: Nav2 se apoya en `slam_toolbox`, ya verificado. Meter
AMCL ahora pondría **dos nodos publicando `map → odom`**, y eso parte el árbol TF sin dar error
— el fallo que costó la Fase 4. Ni el **`collision_monitor`**: hace falta antes de dejar esto
con estudiantes, pero configurar sus umbrales sin haber visto navegar al robot sería adivinar.

⏳ **Nada de esto se ha probado contra el robot todavía.**

### 🔴 Y una retractación: el robot SÍ alcanza la velocidad comandada

Al medir la velocidad **angular** para configurar Nav2 salió que sigue al comando al
**99–102 %** hasta 2.0 rad/s. Eso no cuadraba con la lineal, que según nuestra propia
documentación solo llegaba al 63 % a 0.40 m/s. Así que medí el **perfil en el tiempo** en vez
de la media:

```
comandado 0.20 m/s  ->  meseta 0.199  (100 %)   alcanzada en ~0.5 s
comandado 0.40 m/s  ->  meseta 0.401  (100 %)   alcanzada en ~0.5 s
```

**No hay tope.** La causa del error era la **ventana de medida**: iba hasta la última muestra
del locator, y `conducir()` duerme 1.2 s **después** de `drive_stop()`, así que la media
incluía el robot frenando y parado.

📝 Es **el mismo fallo** que ya había arreglado en la prueba de marcos y que dejé sin arreglar
en el barrido de velocidades. Arreglado ahora en `medir_velocidad_rvr.py`.

Lo que sí existe es una **rampa de aceleración de ~0.5 s**. Importa para Nav2 —el robot no
cambia de velocidad instantáneamente— pero es otra cosa, y se configura con `acc_lim`, no con
`max_vel`.

---

## 2026-07-31 (parte 6) — Los TRES bugs de marcos, arreglados y verificados

Implementa el arreglo que la parte 5 dejó definido. Evidencia: `15_velocidad_odom.txt`.
Código: `Atriz_rvr` rama `ros2`.

**Los sensores del RVR siempre estuvieron bien.** Lo que fallaba era cómo el driver combinaba
sus marcos. Las tres piezas se implementaron y **se verificaron una a una**, como se acordó —
no las tres de golpe.

| Pieza | Qué se hizo | Antes | Después |
|---|---|---|---|
| **1. Orientación** | restar el yaw del arranque | −74.6° / +64.9° en reposo | **+0.00°** |
| **2. Posición** | quitar el `−Y` y rotar −90° | dirección vs yaw: −89.7° | **+0.03°** |
| **3. Velocidad** | rotación + proyección sobre el rumbo | `(-0.000, -0.200)` avanzando recto | **`(+0.101, +0.001)`** vs 0.099 real |

Y la prueba B de la pieza 2: al girar 90°, el yaw cambió **+89.87°** y el desplazamiento
**+90.00°** — mismo sentido. Antes iban en sentidos opuestos.

📝 **Cinco arranques dieron cinco offsets de yaw distintos** (+51.1°, +52.7°, +56.5°, −74.6°,
+64.9°). Confirma que no había constante posible: solo se puede medir en cada arranque.

### 🔴 Una trampa nueva que costó dar por fallida una corrección correcta

**`colcon build` lanzado desde `src/Atriz_rvr` en vez de la raíz del workspace** crea ahí
dentro un **workspace parásito** (`build/`, `install/`, `log/`), compila contra él, dice
«Finished», y el cambio **nunca llega al sistema que se está ejecutando**. El mensaje de éxito
es idéntico al bueno.

Pasó **dos veces**. La primera hizo que la pieza 2 diera 🔴 con el código correcto; la segunda
casi cuela porque el `grep` de verificación usaba **ruta relativa** y acabó mirando el install
parásito.

→ Documentado en `CLAUDE.md` con cómo detectarlo. Y `log/` añadido al `.gitignore` de
`Atriz_rvr`: `build/` e `install/` ya estaban, `log/` no.

### Y un recordatorio sobre medir la referencia

Una primera corrida de la pieza 3 dio un 15 % de error aparente. **No era el driver**: la
ventana de medida eran 0.7 s justo después de un giro de 90°. Con 3 s de ventana el error baja
al 2 %. **La referencia también hay que medirla bien.**

---

## 2026-07-31 (parte 5) — El modelo de marcos del RVR, completo

Cierra la investigación de la parte 4. Evidencia: `15_velocidad_odom.txt`.
**No se implementa el arreglo**, a propósito: ver el final.

### Cinco medidas, y cada una descartó una hipótesis

| | yaw en reposo | desplazamiento | qué descartó |
|---|---|---|---|
| sesión previa ×2 | −74.6° | −90.2°, −90.0° | hay desfase, no se sabe de qué depende |
| tras apagar/encender | +64.9° | −90.0° | **no es constante** (−15° → −155°) |
| tras girar 90° + apagar/encender | **+0.5°** | −90.0° | **el yaw se pone a cero AL ENCENDER** |
| tras girar 90° a mano, sin apagar | −89.9° | −89.7° | el locator **se realinea al arrancar el driver** |
| girando con `cmd_vel`, sin reiniciar | +89.4° (Δ) | **−88.8°** (Δ) | 🔴 **manos contrarias** |

### El modelo que sale, y explica las cinco

1. **El marco del locator es FIJO** y se **realinea en cada `reset_locator_x_and_y()`** — es
   decir, al arrancar el driver. Su eje X queda **90° girado** respecto al «adelante» del
   robot: por eso avanzar recto da siempre −90°.
2. **El yaw se pone a cero al ENCENDER el RVR**, no con `reset_yaw()`, que no hace nada. Los
   valores raros de antes eran de un robot manipulado *después* de encenderse.
3. 🔴 **La posición y la orientación de `/odom` tienen manos contrarias.** El `−Y` que el
   driver aplica al locator **sobra**.

**El yaw es el bueno** — contrastado contra el LIDAR, un sensor físico con convención ROS
conocida. Y el `−Y` vino de una **inferencia inválida**: se dedujo midiendo que «al curvar a la
izquierda `dy` salía negativo», dando por hecho que el eje X del locator apuntaba adelante,
cuando está 90° girado. Es el mismo patrón que ya falló otras veces hoy: **deducir en vez de
medir**.

### El arreglo, definido pero NO implementado

| | Qué hacer |
|---|---|
| **Posición** | quitar el `−Y` del locator y **rotar −90°** |
| **Velocidad** | la misma rotación, y proyectar sobre el rumbo |
| **Orientación** | restar el yaw del arranque (`yaw − yaw₀`) |

No se implementa hoy **a propósito**: toca posición, velocidad y orientación a la vez, y esta
sesión ya acumuló tres errores por ir rápido (el choque, elegir 180° dos veces para una prueba
de signo, y este `−Y` deducido en vez de medido). Se verifica cada pieza por separado.

**Verificación cuando se haga:** una corrida recta debe dar la dirección del desplazamiento
**igual** al yaw publicado, y girar el robot debe mover ambas en el **mismo** sentido.

### 👤 El robot no quedó en su posición inicial

La última prueba lo dejó ~26 cm adelantado y ~19 cm de lado respecto a la marca. Recolocarlo
antes de retomar, y comprobar la orientación con un empujón de 10 cm.

---

## 2026-07-31 (parte 4) — 🔴 RETRACTACIÓN: el stream `Velocity` NO era basura

Manual, cap. 2 y 10. Evidencia: `00_auditoria/evidencia_24_04/15_velocidad_odom.txt`.
Herramienta nueva: `mediciones_banco/medir_velocidad_rvr.py`.

### Lo que este proyecto daba por firme, y era falso

Desde el 2026-07-30, en `CLAUDE.md`, el manual, `TRASPASO.md`, el CHANGELOG y en comentarios
del propio driver:

> «El stream `Velocity` del RVR no refleja la velocidad real. Con el robot avanzando a
> 0.147 m/s comprobados por desplazamiento, el sensor reportaba 0.001 m/s.»

Se usó para declarar la velocidad de `/odom` un **bloqueante de Nav2**.

### Lo medido

```
dirección del desplazamiento del locator:  +90.2°
dirección del vector Velocity:             +90.1°     ← 0.1° de diferencia
módulo real 0.199 m/s  ·  Velocity 0.200              ← 0 % de error
```

**`Velocity` es EXACTO.** La observación original era cierta, pero la conclusión no: el stream
viene en el marco del **MUNDO**, y se leyó solo su componente X con el robot encarado a ~90° de
ese eje. Ahí X vale ~0 aunque el robot cruce la habitación.

### 🔴 Bug A — el driver mete una velocidad del mundo en un campo del robot

`odom.twist` va expresado en `child_frame_id`, o sea en el marco del **robot**. Medido a través
de ROS con el robot avanzando recto a 0.199 m/s:

```
odom.twist.linear publicado:  (-0.000, -0.200)
debería ser:                  (+0.199, +0.000)
```

Solo coincide cuando el robot mira al eje X del odom — que es justo el caso en el que se probó.

### 🔴 Bug B (nuevo) — y tras apagar el robot resultó ser DOS problemas

Medido con el RVR apagado y encendido de por medio:

| | yaw en reposo | desplazamiento | desfase |
|---|---|---|---|
| sesión previa, medida 1 | −74.6° | −90.2° | −14.2° |
| sesión previa, medida 2 | −74.6° | −90.0° | −15.5° |
| **tras apagar y encender** | **+64.9°** | **−90.0°** | **−154.9°** |

🔴 **El desfase NO es constante**: pasó de ~−15° a −154.9° solo con apagar y encender.
**Una corrección constante no sirve.** Y la tabla separa dos problemas independientes que
hasta ahora se veían como uno:

1. **El yaw del cuaternión tiene un origen arbitrario en cada encendido.** `reset_yaw()` no
   lo corrige.
2. **El marco del locator está girado ~90° respecto al robot.** El robot avanza recto y su
   odometría dice que se mueve a −90.0°, en las **tres** medidas.

En los tres casos: `desfase = −90° − yaw_reposo`. Los «~15°» eran la suma casual de ambos.

⚠️ **Variable no controlada:** al apagar, el robot también se **recolocó** en el centro, así
que la orientación física pudo cambiar. Que el desplazamiento siguiera dando −90° **apunta** a
que el marco del locator es relativo al robot, pero **no lo demuestra**.

### La medida original que lo destapó

```
yaw en reposo justo tras arrancar el driver:  -74.6°   ← reset_yaw() NO lo pone a cero
desplazamiento -90.2°  ·  yaw publicado -76.0°  ->  desfase -14.2°
desplazamiento -90.0°  ·  yaw publicado -74.5°  ->  desfase -15.5°   (driver reiniciado)
```

**~15° entre la orientación y la posición del mismo mensaje.** ⚠️ **SIN DETERMINAR** si
sobrevive a un apagado del RVR: las dos medidas son de la misma sesión de encendido. 👤 Hace
falta apagar y encender el robot y repetir.

### No se arregla ninguno todavía, a propósito

El arreglo de A es proyectar sobre el rumbo, así que **depende de B**. Aplicarlo ahora daría un
3 % de error en la proyección y dejaría los 15° intactos. Los dos se documentan en el código y
se arreglan juntos.

### Lo demás que salió

| | |
|---|---|
| **Locator validado con cinta métrica** | 101.1 medidos contra **101.0 reales** — 1 mm en 1 m |
| **Encoders calibrados** | **7792 ticks/m**, contra la cinta y no contra otro sensor |
| `Speed` (escalar) | existe, y es el módulo de `Velocity`. Comprobación cruzada barata |
| ~~El robot no alcanza la velocidad comandada~~ | ⚠️ **RETRACTADO 2026-07-31** (parte 7): era la ventana de medida, que incluía el período tras la frenada. La meseta real es del **100 %** a 0.20 y a 0.40 m/s. Lo que sí hay es una **rampa de ~0.5 s** |

### Dos errores de método míos

- **Choqué el robot.** Ejecuté `--calibrar` (avanza 1 m y para) y después el barrido **sin
  recolocarlo**. La herramienta hace `reset_locator_x_and_y()`, así que su cero decía 0 mientras
  el robot estaba un metro adelantado. 🔴 **Poner a cero la odometría no es devolver el robot al
  inicio**: el cero de software se mueve con el robot. Sin daños. Arreglado en la herramienta —
  cada modo vuelve al punto de partida y el barrido va y vuelve en cada velocidad.
- **Elegí 180° para una prueba de signo. Dos veces.** 180° es exactamente el ángulo donde el
  signo de un giro es ambiguo, y ya me había pasado al determinar el yaw. La prueba buena no
  gira nada: compara la dirección de `Velocity` con la del desplazamiento del locator, que ya
  están en el mismo marco.

---

## 2026-07-31 (parte 3) — La deriva de SLAM, caracterizada: es pequeña

Cierra la única incógnita que dejó la Fase 4. Manual, cap. 9.12. Evidencia:
`00_auditoria/evidencia_24_04/14_deriva_slam_caracterizada.txt`.

**Herramienta nueva:** `mediciones_banco/caracterizar_deriva_slam.py`.

### El problema: dos medidas que se contradecían

```
corrida 1 (2.62 m de recorrido)  ->  87.8 cm y 10.9°
corrida 2 (1.78 m de recorrido)  ->   0.9 cm y  3.1°
```

Dos órdenes de magnitud, y diferían en **dos cosas a la vez**: la distancia recorrida y que en
la primera el robot rozó obstáculos. Con dos variables cambiando no se puede atribuir la causa
a ninguna.

### Cómo se controlaron las variables

- Mismo pasillo despejado de 3 m × 0.8 m, robot en el **centro**, punto de partida marcado.
- **Orientación comprobada ANTES de empezar** con un empujón de 10 cm. La vez anterior se
  movió primero y se perdió una corrida entera contra los obstáculos.
- Nadie cruzó la zona en los ~20 min — el LIDAR ve piernas a 17.5 cm perfectamente.
- **Dos distancias alternadas**, para separar «distancia» de «obstáculos».
- **`slam_toolbox` reiniciado de cero en cada corrida.** Sin esto las últimas parten con el
  mapa que construyeron las anteriores y la comparación no vale.

### Resultado: 6 corridas

| Recorrido | n | Deriva mediana | Peor caso | σ |
|---|---|---|---|---|
| ~159 cm | 3 | **1.0 cm** y 1.3° | 2.7 cm | 1.0 cm |
| ~237 cm | 3 | **2.7 cm** y 2.3° | 3.2 cm | 0.6 cm |

**El error cabe dentro de una celda del mapa** (5 cm) y es un orden de magnitud menor que el
radio del robot (~11 cm). Crece con la distancia de forma coherente (0.63 % del recorrido en
las cortas, 1.14 % en las largas): es el comportamiento normal de una odometría corregida por
emparejado de barridos, no el patrón de un fallo.

Y el mapa es **repetible**: las tres corridas largas dieron +2347, +2321 y +2334 celdas.

### 🔴 Los 87.8 cm de la Fase 4 eran una anomalía

La corrida larga de aquí recorre 237 cm —comparable a los 262 cm de aquella— y sale **30 veces
mejor**. ⚠️ **No se reprodujo la anomalía a propósito**, así que «rozar obstáculos» sigue
siendo la explicación más probable, **no una causa demostrada**. Lo que sí queda demostrado es
que no es el comportamiento normal del sistema.

### ✅ Consecuencia: un bloqueante menos para Nav2

La localización ya no bloquea. Quedan dos: la **velocidad de `/odom`** (que pasa a ser el
siguiente paso) y la **inclinación de ~8°** — cuya gravedad queda acotada por estos números:
con la inclinación presente, la deriva es de 2.7 cm, así que no está arruinando el emparejado.

### La lección de método

Con dos puntos que se contradicen no se puede concluir nada, y la tentación es quedarse con el
que conviene. Seis corridas con las variables controladas costaron 20 minutos y convirtieron
«no sabemos si sirve para Nav2» en un número con desviación típica.

---

## 2026-07-31 (parte 2) — Fase 4 CERRADA: SLAM mapea de verdad

```
celdas conocidas   657 -> 3110      área  1.64 -> 7.78 m²   (casi 5x)
nodos del grafo      4 -> 8         recorrido 262.5 cm
✅ EL MAPA CRECE AL MOVERSE
```

Manual cap. 9. Evidencia: `00_auditoria/evidencia_24_04/13_fase4_cerrada.txt` y
`mapas/mapa_fase4_cerrada.*`.

Para llegar aquí hubo que arreglar **tres cosas** y corregir **dos herramientas propias**.
Ninguna de las cinco daba un error: todas fallaban en silencio.

### 🔴 1. `/scan` y `/odom` se contradecían en el sentido de giro

Girando el robot y correlacionando el barrido de antes con el de después:

```
giro real (odom):          -47.0°
desplazamiento del scan:   -47.0°   <- MISMO signo; la física exige OPUESTOS
```

⚠️ **Y eso solo no dice cuál de los dos está mal.** La primera versión de
`verificar_inverted_lidar.py` concluyó «`/scan` está espejado» y **era concluir de más**:
los datos encajaban igual con «el yaw de `/odom` está invertido». Herramienta corregida
para reportar la contradicción y enumerar las dos causas.

**Lo desempató una observación física**, que ningún software del robot puede hacer: se
mandó un giro positivo y **se miró el robot** — giró a la izquierda. Como el SDK documenta
`yaw_angular_velocity` con la regla de la mano derecha y el driver pasa `angular.z` sin
tocarlo, el giro real fue +47°, el barrido (−47°) era correcto, y el equivocado era el yaw
de `/odom`.

✅ **`inverted: true` del YDLIDAR era correcto. El LIDAR nunca fue el problema.**

### 🔴 2. El RVR no usa una sola convención de ejes

Se aplicó la conversión FRD→FLU a los cuatro sensores **por analogía**, y eso rompió dos.
Hubo que medir cada uno por separado:

| Sensor | Estaba | Acción |
|---|---|---|
| cuaternión | yaw invertido | `(x, -y, -z, w)` |
| locator | `y` invertida | `-y` |
| giroscopio | **ya estaba bien** | solo deg/s → rad/s |
| acelerómetro | **ya estaba bien**, y en **g** | solo **g → m/s²** |

En reposo el acelerómetro daba módulo **0.973**: el RVR reporta en **g**, y el driver de
ROS 1 tampoco lo convertía. Ahora `(-1.314, -0.004, +9.281)`, módulo 9.374 m/s².

📝 De propina, el acelerómetro da la inclinación del robot por una **tercera vía
independiente**: `asin(1.314/9.374) = 8.1°`, coherente con los ~7° del árbol TF y del Roll.

Efecto sobre la coherencia de SLAM, misma prueba antes y después:

```
deriva tras un giro de 360° y volver al sitio
  antes:   6.6 cm y 30.0°
  después: 0.2 cm y  1.8°
```

### 🔴 3. `fixed_resolution: false` hacía que slam_toolbox descartara los barridos

El X2 entrega barridos de longitud **variable** (254 unas veces, 255 otras) y
`slam_toolbox` registra el sensor con el tamaño del primero, **descartando el resto**. Una
sola línea en su log, ningún error:

```
LaserRangeScan contains 254 range readings, expected 255
```

Ese parámetro se puso a `false` en la Fase 3.2 **para callar un aviso cosmético**. Cambiar
un parámetro para silenciar un aviso cambió un síntoma visible por uno invisible. Con
`true`: 142 barridos, **todos de 260 puntos**.

📝 El mismo problema reventaba `verificar_inverted_lidar.py` con `IndexError`. Corregido
remuestreando a una rejilla angular fija. Mismo origen, dos víctimas.

### 🔴 4. Mi propia herramienta daba un falso negativo

Con todo lo anterior arreglado, `medir_slam_ros2.py` **seguía** diciendo «el mapa no
creció». No era SLAM: era la prueba. Avanzaba 40 cm y retrocedía otros 40, y solo miraba
el mapa al final — con el robot otra vez donde empezó.

`slam_toolbox` cuenta la distancia **desde el último nodo del grafo**, no desde donde
empezó la prueba: con el umbral en 0.3 hicieron falta **~0.85 m**. Y girar en el sitio no
basta — cuatro vueltas y media seguidas no cambiaron ni una celda.

Lo demostró mirar el **grafo**, no el mapa, y compararlo contra la **configuración de
fábrica** (que se comportó igual, descartando de un golpe que fueran mis parámetros).

La herramienta ahora avanza en **tramos**, mide **después de cada uno**, y el veredicto usa
el mapa **más grande visto**, no el último.

### Coste en el Pi 4

| Proceso | CPU | RSS |
|---|---|---|
| `rvr_driver_node` | 33.6 % | 86.3 MB |
| `async_slam_toolbox_node` | 5.0 % | 50.3 MB |
| `ydlidar_ros2_driver_node` | 2.6 % | 30.8 MB |
| `robot_state_publisher` | 0.5 % | 32.4 MB |

64.2 °C. El driver sube de 15.9 % a 33.6 %: lleva ahora el keepalive, el detector de
silencio y las conversiones de ejes.

### ⚠️ Lo que queda abierto

### Segunda corrida, en espacio despejado — y contradice a la primera

La primera se hizo en un hueco demasiado justo y el robot llegó a **rozar obstáculos**. Se
repitió con 2 m × 0.8 m libres y el robot centrado:

```
recorrido 178.5 cm    celdas 2367 -> 3299 (+932)    área 5.92 -> 8.25 m²
✅ EL MAPA CRECE AL MOVERSE
deriva al volver al punto de partida:  0.9 cm y 3.1°
```

🟡 **La deriva NO está caracterizada: las dos medidas se contradicen.** Mismo binario, el
mismo día:

| Corrida | Recorrido | Deriva | Espacio |
|---|---|---|---|
| 1ª (`--pasos 3`) | 262.5 cm | **87.8 cm y 10.9°** | justo, rozó obstáculos |
| 2ª (`--pasos 2`) | 178.5 cm | **0.9 cm y 3.1°** | 2 m × 0.8 m despejados |

**Ninguna se presenta como «la buena».** En ambas el mapa crece y es utilizable, pero con dos
órdenes de magnitud de diferencia no se puede decir aún si la pose sirve para Nav2. **Hay que
repetir la prueba varias veces en espacio despejado antes de atribuir nada** — regla nº 4 del
proyecto, y aquí era fácil saltársela.

Tres sospechas **sin aislar**: rozar obstáculos en la primera, la inclinación de ~8° que hace
al LIDAR barrer un plano inclinado, y la velocidad de `/odom`, que sigue siendo basura.

📝 Y una lección de operación que costó una corrida entera: **hay que decir cuánto espacio
hace falta ANTES de mover el robot.** `medir_slam_ros2.py` necesita, con el robot en el
centro, 1 m por delante, 1 m por detrás y 40 cm a cada lado — y nada a menos de 60 cm, porque
el robot **no esquiva obstáculos**, solo tiene watchdog. Documentado ya en el manual 9.13 y en
`CLAUDE.md`.

🔴 La inclinación de ~8°, ahora confirmada por **tres** vías independientes. Causa sin
determinar.

---

## 2026-07-31 — El RVR se dormía a los 300.6 s: medido y arreglado

Cierra el fallo grave que abrió la Fase 4. Manual: **cap. 9.8a–9.8d**. Evidencia:
`00_auditoria/evidencia_24_04/12_keepalive_rvr.txt`.

### ✅ El timeout, medido: 300.6 s = 5.01 min

Arrancando el driver con el keepalive desactivado a propósito (`keepalive_period:=0.0`) y
vigilando el **ritmo** de `/odom` 12 minutos, el robot se durmió **dos veces**:

| | Aguantó | Detectado tras | Reanudado en |
|---|---|---|---|
| Sueño 1 (a los 3.9 min) | **300.6 s** | 3.4 s | 0.004 s |
| Sueño 2 (a los 9.0 min) | **300.6 s** | 3.4 s | 0.004 s |

**300.6 s idénticos a la décima de segundo no es una heurística: es un temporizador del
firmware.** Coincide con los 5 min documentados del RVR y cae dentro del intervalo 2–7.5 min
que los timestamps del fallo original solo permitían acotar. **Deja de estar NO VERIFICADO.**

### El arreglo: dos piezas, y hacen falta las dos

En `rvr_driver_node.py`, bloque nuevo «SALUD DEL ENLACE»:

- **`_keepalive`** — timer cada **30 s** que llama a `get_battery_percentage()`. Se eligió una
  **lectura** y no `wake()` a secas porque no cambia ningún estado del robot: no puede
  interferir con una maniobra en curso ni con la parada de emergencia. Y de paso publica
  **`/battery_state`** (`sensor_msgs/BatteryState`, RELIABLE + TRANSIENT_LOCAL), que no existía
  ni en el driver de ROS 1, con avisos al cruzar el 25 % y el 10 %.
- **`_vigilar_silencio`** — timer a 1 Hz que mira **cuánto hace que llegó la última muestra**,
  no si el nodo existe ni si el topic está registrado: las dos cosas eran ciertas mientras el
  robot estaba mudo. A los 3 s avisa e intenta reanudar (`wake` + `stop` + `start`).

El keepalive cubre la causa conocida; el vigilante cubre el resto (un cable flojo, un
`sensor_control` caído, un firmware atascado) y **convierte un fallo silencioso en uno
ruidoso**.

30 s frente a un timeout de 300 s son **10× de margen**. Se podría subir a 120 s sin riesgo,
pero un comando cada 30 s son ~2 bytes/s sobre un enlace que ya lleva 16.7 Hz.

Parámetros nuevos: `keepalive_period` y `silence_timeout`, expuestos también como argumentos
de `robot.launch.py`. A 0 se desactivan — que es como se reproduce el fallo para medirlo.

### ✅ Verificado: las dos pruebas, una al lado de la otra

Mismo robot, misma duración, mismo binario. Solo cambia `keepalive_period`:

| | A (`keepalive=0`) | B (`keepalive=30 s`) |
|---|---|---|
| duración | 12.0 min | 12.0 min |
| muestras de `/odom` | 11795 | 11909 |
| ritmo medio | 16.38 Hz | **16.54 Hz** |
| **huecos en `/odom`** | **2** (3.9 y 9.0 min) | **0** |
| avisos de silencio | 2 | 0 |
| reanudaciones | 2, **0 fallos** | 0 |
| lecturas de batería | 0 | **24**, cada 30.0 s exactos |

Se durmió **dos veces sin keepalive y ninguna con él**. En la prueba B el detector no tuvo
nada que detectar, que es el objetivo. El ritmo medio sube de 16.38 a 16.54 Hz: la diferencia
es exactamente el tiempo que estuvo mudo en la A.

### Herramienta nueva

`00_auditoria/evidencia/mediciones_banco/medir_keepalive_ros2.py` — vigila el **ritmo** de
`/odom`, no la existencia del topic. Se suscribe con **BEST_EFFORT** a propósito: con el
perfil por defecto de `rclpy` (RELIABLE) DDS no emparejaría y la herramienta no recibiría
nada, concluyendo que el robot está mudo cuando no lo está. Sería un falso positivo perfecto.

### Detalle de implementación que conviene no deshacer

El `finally` que libera `_recuperando` pase lo que pase. Sin él, una excepción durante la
recuperación dejaría la vigilancia muerta para siempre: **el fallo silencioso otra vez, esta
vez dentro del código escrito para evitarlo.**

Y `cerrar()` apaga la vigilancia **antes** de parar nada, para que una parada normal no
dispare un WARN alarmante en cada apagado.

---

## 2026-07-30 (parte 9) — Fase 4: SLAM arranca y mapea, pero aparece un fallo grave del driver

🟡 **Fase 4 PARCIAL.** `slam_toolbox` arranca, se activa, completa el árbol TF y publica
`/map`. **Lo que falta es la prueba que importa: que el mapa crezca al moverse.** Y en el
camino salió un fallo del driver que afecta a todo el laboratorio.

Manual: **capítulo 9 nuevo**. Evidencia cruda: `00_auditoria/evidencia_24_04/11_slam_fase4.txt`
y `mapas/`. Rama `ros2` de `Atriz_rvr`.

### 🔴🔴 El RVR se duerme solo y el nodo sigue pareciendo sano

El hallazgo grave, y no es de SLAM. A mitad de sesión, sin tocar nada, `/odom`, `/imu` y
`/color` dejaron de publicar **a la vez**:

```
ros2 topic hz /tf     -> average rate: 50.193      # 50 Hz = SOLO slam_toolbox
ros2 topic hz /odom   -> (nada)
ros2 topic info /odom -> Publisher count: 1  ·  Node name: rvr_driver
ps -p 56100           -> Sl  12.3 %  86.4 MB  ·  17 hilos     # el proceso VIVE
```

Ni un error en el log. Y la pista fácil engañaba: `/tf` a 50 Hz decía «TF va bien», pero 50 Hz
es exactamente el `transform_publish_period` de `slam_toolbox` **a solas** — con el driver
serían ~67 Hz.

**Causa, confirmada en el código:** `rvr_driver_node.py:367` llama a `wake()` **una sola vez al
arrancar**, y no vuelve a hablar con el RVR salvo cuando llega un `cmd_vel`. El SDK vendorizado
**no tiene** `set_inactivity_timeout`. Reiniciar el driver lo revive: `/odom` vuelve a
16.669 Hz.

⚠️ **NO VERIFICADO el tiempo exacto**: acotado entre ~2 y ~7.5 min por los timestamps
(arranque 00:03:43, último dato 00:05:35, muerto a las 00:11). Encaja con los 5 min
documentados del RVR, pero **no se ha medido** y no se escribe como hecho.

**Por qué es serio para el laboratorio:** un robot que espere 5 minutos a que el estudiante
empiece su práctica **estará mudo al empezar**, y la web no verá ningún error — el nodo está
vivo y los topics existen. Un `systemd` con `Restart=always` **no** lo arregla: el proceso no
muere.

**Arreglo pendiente**, en el driver: keepalive cada 60 s con `get_battery_percentage()` (es una
lectura, y de paso da la batería, que hoy no se publica) + un detector de silencio que avise en
vez de publicar nada con cara de sano.

### 🔴 `base_link` tenía DOS padres — bloqueante de la Fase 4, error de diseño propio

`slam_toolbox` repetía `Failed to compute odom pose`:

```
/tf         odom            -> base_link       (driver)
/tf_static  base_footprint  -> base_link       (URDF)
-> "Tf has two or more unconnected trees."
```

En TF un frame solo puede tener **un** padre. Arreglado: el driver publica
`odom → base_footprint`, que es además lo correcto por REP-105 y lo que pide el `base_frame` de
`slam_toolbox`. La IMU pasa a su propio `imu_frame` (`imu_link`).

**Y la lección de método, que vale más que el arreglo:** la verificación de la Fase 3 era
`tf2_echo odom laser` y **pasaba**, resolviendo por el camino equivocado
(`odom → base_link → laser`) mientras `base_footprint` colgaba de otro árbol. **Hay que
comprobar el transform que pide el consumidor, con sus frames exactos.** Un `tf2_echo` que
resuelve prueba que hay *un* camino, no que el árbol esté bien.

Tras el arreglo: un solo árbol, y `Failed to compute odom pose` **0 veces**.

### 🔴 `slam_toolbox` es un nodo de ciclo de vida en Jazzy

Arrancaba en `unconfigured`: proceso vivo, en `ros2 node list`, **sin hacer nada** —
`Subscription count: 0` en `/scan`, sin publicar `/map`, sin un solo error.

`slam.launch.py` reescrito con `LifecycleNode` + eventos `configure`→`activate` encadenados con
`OnStateTransition` (no con un `sleep`), siguiendo el patrón del `online_async_launch.py`
oficial. Argumento `autostart`, por defecto `true`. Resultado: `active [3]` automáticamente.

### ✅ El riesgo del QoS de `/scan` era infundado

`slam_toolbox` se suscribe con **BEST_EFFORT**, igual que publica el driver del LIDAR:
emparejan. Queda documentado porque comprobarlo cuesta un comando y perseguir un mapa vacío
cuesta una tarde. Al revés sí muerde: **`/map` es RELIABLE + TRANSIENT_LOCAL**.

### `save_map` no funciona sin Nav2; `serialize_map` sí

`save_map` devuelve `result=255`, y el error real está en el log de slam_toolbox, no en la
respuesta: `Package 'nav2_map_server' not found`. Este sistema tiene `ros-jazzy-ros-base` y
Nav2 llega en la Fase 5.

`serialize_map` (nativo, sin Nav2) → `result=0`, `.data` 11 KB + `.posegraph` **3.4 MB** con el
robot casi quieto. ⚠️ Vigilar ese tamaño antes de guardar mapas en los 16 robots.

### Un robot quieto da un mapa 92.9 % desconocido, y no es un fallo

`min_pass_through: 2` exige **dos rayos** por celda y los rayos de un LIDAR quieto divergen:
solo las celdas cercanas reciben dos (1.29 m² libres). Y `minimum_travel_distance: 0.3` deja el
grafo en **un solo nodo**. No hay que ajustar el solver, hay que mover el robot.

**Herramienta nueva:** `00_auditoria/evidencia/mediciones_banco/medir_slam_ros2.py` — mueve el
robot (giro 360° + avance/retroceso) y mide **cuántas celdas conocidas gana el mapa**. Mide el
**recorrido real en `odom`** para separar los dos fallos que se confunden: «el robot no se
movió» y «SLAM no procesó». Mide posición, nunca velocidad (el stream `Velocity` del RVR es
basura).

### ⏳ La prueba de mapeo con movimiento NO es válida: hay que repetirla

Se reinició **solo el driver** (había muerto), dejando el `slam_toolbox` viejo en marcha. Ese
`slam_toolbox` dejó de procesar: mapa **idéntico celda a celda** (515 conocidas antes y
después) tras un giro de 360° y 80 cm de recorrido.

→ **Reiniciar el driver por debajo de un `slam_toolbox` ya arrancado invalida la prueba**: se
queda con un hueco en su buffer TF y con el `odom` anterior. Arrancar los dos juntos,
`robot.launch.py` primero.

### Coste en el Pi 4 con todo a la vez

| Proceso | CPU | RSS |
|---|---|---|
| `rvr_driver_node` | 15.9 % | 86.3 MB |
| `async_slam_toolbox_node` | **4.5 %** | 49.3 MB |
| `ydlidar_ros2_driver_node` | 2.6 % | 31.3 MB |
| `robot_state_publisher` | 0.5 % | 32.6 MB |

`loadavg` 0.62 sobre 4 núcleos · 62.3 °C · `throttled=0x0`.

**SLAM sale barato (4.5 %).** El presupuesto de CPU lo consume el driver del RVR, así que
subir `throttle_scans` para «aliviar el Pi» sería optimizar lo que no cuesta.

### Pendiente al cerrar la sesión

| Qué | Por qué importa |
|---|---|
| **Keepalive del driver** | sin él, un robot idle 5 min llega mudo a la práctica |
| Repetir `medir_slam_ros2.py` con los dos launch desde cero | es la única prueba que cierra la Fase 4 |
| 🔴 Verificar `inverted` del LIDAR | si está al revés **el mapa sale espejado**, sin dar error |
| 🔴 Inclinación de ~7° del robot | `slam_toolbox` la absorbe en `map → odom`; para Nav2 hay que resolverla |
| Velocidad de `/odom` | sigue siendo basura; no bloquea SLAM, sí Nav2 |
| Los 16 servicios y 4 topics sin portar | diferido por el usuario a «cuando acabemos todo» |

---

## 2026-07-30 (parte 7) — Fase 3 COMPLETA: `/scan` funciona y el robot arranca con un comando

Paquete **nuevo** `atriz_rvr_bringup`, rama `ros2` commit `b117791`.

```bash
ros2 launch atriz_rvr_bringup robot.launch.py
```

Tres nodos que se reparten el árbol TF, verificado contra el hardware:

```
tf2_echo odom laser -> Translation: [-0.018, -0.002, 0.141]

/tf         odom -> base_link                              (driver, 16.989 Hz)
/tf_static  base_footprint -> base_link
            base_link -> {laser, imu_link, wheel_left, wheel_right}
/scan       10.1 Hz · frame_id: laser · 255 puntos, 226 válidos (89 %)
            0.326 – 3.134 m · arco −180° a 180° · resolución 1.42°
```

### No hay paquete apt del driver: se compila desde fuentes

Comprobado antes de compilar nada: `ros-jazzy-ydlidar-ros2-driver`, `ros-jazzy-ydlidar` y
`ros-jazzy-ydlidar-sdk` **no existen**, y `apt-cache search ydlidar` da 0 resultados.

**`YDLidar-SDK`** con cmake → 132 ficheros bajo `/usr/local`. Comprobado **en seco** con
`make install DESTDIR=/tmp/prueba` antes de ejecutarlo: **no pisa nada** del sistema de
paquetes. 📝 Instala 17 binarios de prueba en `/usr/local/bin` que sobran en la imagen dorada.

**`ydlidar_ros2_driver` rama `humble` compila en Jazzy sin cambios** (47.9 s). Driver 1.0.1,
SDK 1.2.20. Y **trae `params/X2.yaml` de fábrica**. Va en `~/atriz_ws/src/` **sin `.git`**: es
código de terceros y no se mezcla con `Atriz_rvr`.

### 🔴 El hallazgo más importante: el QoS de `/scan`

**El driver publica `/scan` como BEST_EFFORT, y `rclpy` pide RELIABLE por defecto.** Si no
coinciden, **DDS no empareja publicador y suscriptor y no llega nada** — sin error en el
suscriptor.

```
New subscription discovered on topic '/scan', requesting incompatible QoS.
No messages will be sent to it. Last incompatible policy: RELIABILITY_QOS_POLICY
```

**El primer test de esta sesión cayó justo ahí** y concluyó que `/scan` no llegaba. Con
BEST_EFFORT llegan 81 barridos en 8 s.

🔴 **Riesgo directo para la Fase 4:** si `slam_toolbox` se suscribe con RELIABLE, **no recibirá
un solo barrido y no dará ningún error** — solo un mapa vacío. **Comprobarlo antes de mapear.**

### ⚠️ `frequency` no funciona en el X2 — y eso cierra una vía de mejora

Se pidió `frequency: 10.0` y `/scan` salió a **10.1–11.75 Hz**. Sin driver, con `x2_parse.py`,
se midieron **11.48 Hz**. **El X2 de canal único ignora el parámetro:** el motor va libre.

**Consecuencia:** el apartado 8.3 del manual proponía bajar a 7 Hz para ganar resolución angular
(0.84° en vez de 1.37°). **Esa vía no existe por software.** La resolución real medida con el
driver es **1.42°**, coherente con los 1.39° de `x2_parse.py`. Corregido en el manual.

### Lo que queda sin verificar, y por qué importa

**`inverted`.** El `X2.yaml` oficial trae `false`; el launch de ROS 1 de Atriz tenía `true`.
Pero **ese launch nunca se ejecutó**, porque el driver del LIDAR no estaba instalado (hallazgo
nº3 de la auditoría). Así que `true` es una suposición heredada, no un valor validado.

**Si está mal, el mapa sale espejado** — y es de los fallos más desconcertantes de SLAM: parece
que funciona, y las paredes están en el lado contrario. Documentado cómo comprobarlo en
`config/ydlidar_x2.yaml`: un objeto plano a 1 m justo delante, y el mínimo de `ranges` debe caer
en el índice del ángulo 0.

**La regla udev entre robots.** Va por `ID_PATH` (el puerto USB físico) porque el CP2102
reporta serie `0001`, genérico. Comprobada en seco y en caliente en `rvr-01`, pero **si en otro
robot el lidar va en otro puerto físico, el `ID_PATH` será distinto y la regla no casará.**

### Avisos benignos, documentados para que nadie los persiga

`[error] Fail to get baseplate device information!` aparece **siempre**: el X2 de canal único no
responde a esa consulta, y el scan funciona igual. Y `Single Fixed Size: 270 / Sample Rate:
3.00K` es informativo y correcto.

### Documentado

- **Manual, cap. 8.5** — escrito completo: los dos pasos de compilación, la comprobación en
  seco del `make install`, la regla udev, **el QoS**, y la verificación con la salida real.
- **Manual, cap. 8.3** — corregido: la mejora de resolución bajando el giro **no es
  alcanzable**.
- **`CLAUDE.md`** — dos trampas nuevas: el QoS de `/scan` y el `frequency` inútil.
- **`verificar_robot.sh`** — comprueba el SDK, el driver compilado y `/dev/ydlidar`.

### Pendiente

1. **Fase 4: `slam_toolbox`.** Y lo PRIMERO es comprobar con qué QoS se suscribe a `/scan`.
2. 👤 **Comprobar `inverted`** con un objeto a 1 m delante del robot, antes de mapear.
3. **La velocidad de `/odom` sigue siendo basura** (parte 5). Afecta a `robot_localization` y a
   los controladores de Nav2, no a `slam_toolbox`, que usa el TF.
4. Los 16 servicios del driver sin portar.
5. 📝 El pitch de −7° del robot, sin determinar si es del suelo o del montaje.

---

## 2026-07-30 (parte 6) — Fase 3: el URDF, y el árbol TF deja de estar partido

Paquete **nuevo** `atriz_rvr_description`, rama `ros2` commit `89be510`. Antes de esto el
proyecto **no tenía ningún `.urdf` ni `.xacro`**.

### El bloqueante raíz, y por qué era invisible

```
   odom      ──► rvr_base_link      ← lo publicaba el driver
   base_link ──► laser              ← un static_transform_publisher del launch
```

**Nada unía `rvr_base_link` con `base_link`.** Dos árboles inconexos: no había forma de saber
dónde está el LIDAR respecto a la odometría, y sin eso SLAM y Nav2 son imposibles.

Lo peor es cómo falla: `tf2_echo odom laser` responde *«Could not find a connection»* y nada
más. **Ningún nodo se cae, ningún topic deja de publicar.** Otro fallo silencioso.

Ahora la cadena es una sola, canónica según REP-105:

```
   map ──► odom ──► base_footprint ──► base_link ──► { laser, imu_link, wheels }
```

Con el reparto explícito de quién publica qué — que es lo que más se confunde:

| Transform | Lo publica |
|---|---|
| `map → odom` | `slam_toolbox` (Fase 4, aún no existe) |
| **`odom → base_link`** | **el driver**, porque es el único que sabe dónde está el robot |
| `base_footprint → base_link`, `→ laser`, `→ imu_link`, ruedas | `robot_state_publisher`, desde el URDF |

### 🔴 El valor del LIDAR estaba 7.4 cm corto

```
  base_height    0.114     alto del RVR         📝 ficha, SIN MEDIR en esta unidad
+ laser_gap      0.040     hueco tapa→LIDAR     ✅ MEDIDO por el usuario
+ x2_height/2    0.0205    al centro del disco  📝 ficha del X2
─────────────────────────
  laser_z        0.1745  = 17.45 cm sobre el suelo
```

El proyecto arrastraba **`0.10`**. Venía del `static_transform_publisher` de
`lidar_only.launch`, y la propia `GUIA_COMPLETA_LIDAR.md` lo admitía: «se **asume** que el LIDAR
está en el centro del RVR y 0,1 m por encima. **Ajusta estos valores a tu montaje real**».
Nadie lo ajustó en toda la vida del proyecto.

**Por qué 7 cm no es cosmético:** un error en `laser_z` inclina el mapa entero; uno en `laser_x`
desplaza cada barrido respecto a la odometría, y SLAM lo lee como movimiento que no ocurrió. El
mapa sale torcido **sin un solo mensaje de error**.

El término dudoso es `base_height`, el único sin medir. Queda documentado que si el mapa sale
inclinado, ese es el primer sospechoso, y se resuelve con **una** medida del suelo al centro del
disco.

### Las ruedas son `fixed`, y es deliberado

Un joint `continuous` obligaría a publicar `/joint_states` con el ángulo de cada rueda, y el RVR
**no expone la posición angular** — solo conteos de encoder acumulados. Declararlas móviles
dejaría a `robot_state_publisher` esperando datos que nunca llegan, y el árbol se rompería con
un aviso poco claro. Como el RVR entrega la odometría ya integrada, son decorativas. Por eso el
launch tampoco arranca `joint_state_publisher`.

### Dos hallazgos menores pero reales

**`xacro` NO viene en `ros-jazzy-ros-base`.** Hay que instalarlo aparte
(`sudo apt install ros-jazzy-xacro`). `robot_state_publisher` y `tf2_tools` **sí** vienen.

**Un fallo latente evitado:** `install(DIRECTORY … rviz)` con el directorio vacío habría roto el
build **en un clon recién hecho**, porque git no versiona directorios vacíos. Se añadirá cuando
haya una configuración de RViz2 de verdad (Fase 4).

### Documentado

- **Manual, capítulo 7** — escrito. No existía. Con la tabla de quién publica cada transform,
  la procedencia de cada medida, y los comandos de verificación.
- **`verificar_robot.sh`** — comprobación nueva del árbol TF (`tf2_echo odom laser`) y de que
  `ros-jazzy-xacro` esté instalado.

### ✅ CERRADA — `odom → laser` resuelve

```
$ ros2 run tf2_ros tf2_echo odom laser
- Translation: [-0.018, -0.002, 0.141]
- Rotation: in RPY (degree) [1.603, -7.013, -5.000]

base_link   parent: odom        rate 16.699 Hz    <- el driver
laser       parent: base_link   rate 10000 Hz    <- robot_state_publisher
imu_link, wheel_*                rate 10000 Hz
```

La **z = 0.141** coincide con los 0.1425 del URDF, los 10000 Hz son la marca de `/tf_static`, y
`base_link` va al ritmo de la telemetría. **El bloqueante raíz de SLAM está resuelto.**

📝 **Dato colateral sin medir:** el RPY sale **[1.6°, −7.0°, −5.0°]**. Un pitch de −7° significa
chasis inclinado o suelo con pendiente. **El LIDAR lo está viendo.** No se ha determinado la
causa, y conviene recordarlo cuando salga el primer mapa.

### 🐛 Dos fallos propios más

**El launch falló con un error de los útiles**, y el fichero **ya llevaba un comentario
explicando la solución** que no se había implementado:

```
Unable to parse the value of parameter robot_description as yaml. If the parameter
is meant to be a string, try wrapping it in ParameterValue(value, value_type=str)
```

`robot_description` es XML y `launch` lo interpreta como YAML si no se le dice el tipo.

**Y un respaldo mal colocado hizo que `apt` avisara en cada ejecución.** Al añadir
`noble-updates` se dejó `ubuntu.sources.bak-…` **dentro** de `sources.list.d/`, y desde entonces
todo `apt install` terminaba con `N: Ignoring file … invalid filename extension`. Inofensivo,
pero en 16 robots es ruido permanente. Corregido en `provision.sh` (los respaldos van a
`/root/respaldos-apt/`), en el manual, y **`verificar_robot.sh` ahora lo detecta**.

### Pendiente
2. **La velocidad de `/odom` sigue siendo basura** (parte 5). Bloquea SLAM de calidad, no la
   estructura del árbol.
3. Los 16 servicios del driver sin portar.
4. Fase 4: `slam_toolbox`.

---

## 2026-07-30 (parte 5) — El driver corre sobre ROS 2, y el watchdog se prueba por primera vez

Rama **`ros2`** de `Atriz_rvr`, commit `80e1cbf`. **Verificado contra el robot real.**

```
/odom              16.671 Hz · sigma 0.47 ms      (ROS 1 daba 16.59 Hz)
angular_velocity   rad/s                          (antes deg/s, violaba REP-103)
árbol TF           odom -> base_link              (antes rvr_base_link, partido)
cmd_vel            34.0 cm a 0.15 m/s en 2 s      (esperado ~30 cm)
watchdog           quieto en 527 ms, ~7.9 cm      PRIMERA VEZ QUE SE PRUEBA
```

### Fase 2.1 — limpieza: 79 ficheros y 700 KB menos

Cada borrado verificado antes de hacerlo, no por lo que decía el plan:

| Borrado | Comprobación |
|---|---|
| `atriz_rvr_driver/src/` (38 ficheros) | El CMakeLists **sí** lo construía, pero **ningún launch lo invocaba** |
| `atriz_rvr_serial/` | Solo lo dependía el driver, y solo para ese C++ |
| `rvr-ros.py` (722 líneas) | Sin bit de ejecución, y su launch invocaba `rvr-ros-sim.py`, que **no existe** |
| `sphero_rvr_hw/` | Sin `package.xml`, huérfana |
| 3 `.launch` | Cadena entera colgando del C++ borrado |

### Fase 2.2 — `atriz_rvr_driver` a `ament_python`

Se van `roscpp`, `message_generation/runtime`, `transmission_interface`, `cv_bridge` (sin
cámara) y `joint_limit_interface` — que además estaba **mal escrito** (el real es
`joint_limits_interface`) y por eso `rosdep` fallaba.

**El SDK no se mueve** de `scripts/`: sus 196 ficheros usan imports absolutos y es la única
pieza validada en Python 3.12. Con `package_dir={'': 'scripts'}` sigue importándose igual.

### Fase 2.3/2.4 — el nodo: 1704 líneas → ~490 con el núcleo

Lo que se arregló, y lo que **ya estaba bien**. Ver la corrección del plan más abajo.

- **`imu.angular_velocity` a rad/s, convertido una sola vez.** El original lo asignaba en
  deg/s, publicaba, y solo después convertía — incrementando el contador de componentes **dos
  veces por muestra**, así que `/odom` podía salir con la velocidad angular en grados.
- **`run_coroutine_threadsafe`** en vez de las 48 `asyncio.run()`. Sin afirmar que fuera el
  cuello de botella: **no se ha medido**.
- **`odom → base_link`**, el bloqueante raíz de SLAM.
- Todo parametrizado, watchdog a 20 Hz (antes ~6 Hz), y la parada de emergencia con QoS
  *reliable + transient local* escuchando **los dos** nombres de topic.

### 🔴 Dos puntos del plan eran FALSOS — la misma causa de siempre

Verificado antes de escribir código: el plan decía que **no había watchdog de `cmd_vel`** y que
el **event loop avanzaba en ráfagas** dentro del bucle de ROS. **Las dos cosas ya estaban
resueltas** en `migracion-ros2`.

Se añadieron en `4ae8467` y `d8f182d`/`659364c`, que están **entre los 5 últimos commits de
`origin/main`** — exactamente el rango que le faltaba al clon desactualizado sobre el que se
hizo la auditoría. **Es la misma causa que los tres hallazgos ya retirados**, y van cinco.

Corregido en el plan, apartados 2.3 y 2.4, con la explicación completa.

### 🔴 HALLAZGO NUEVO: el stream `Velocity` del RVR no sirve

Medido aislando el SDK, sin ROS de por medio:

| Método | Recorrido real (locator) | `Velocity` reportada | Deriva tras `drive_stop` |
|---|---|---|---|
| `drive_rc_si_units(0.15)` | **29.4 cm** = 0.147 m/s | **0.001 m/s** | **1.1 cm** |
| `drive_with_heading(64)` | 45.6 cm | 0.028 m/s | **11.3 cm** |

> ⚠️ **RETRACTADO el 2026-07-31.** Lo que sigue se conserva como registro de lo que se midió
> aquel día, pero **la conclusión era falsa**: el stream `Velocity` es **exacto** (0 % de error
> en módulo, 0.1° en dirección). Viene en el marco del **mundo**, y aquí se leyó solo su
> componente X con el robot encarado a ~90° de ese eje. El fallo está en el **driver**, que la
> copia a un campo que ROS define en el marco del **robot**.
> Detalle en `00_auditoria/evidencia_24_04/15_velocidad_odom.txt`.

**Consecuencia grave:** el driver publica `odom.twist.twist.linear` desde ese sensor, así que
**la velocidad de `/odom` es basura**. Afecta a SLAM y a `robot_localization`. La **posición**
sí es buena (29.4 cm contra 30.0 esperados).

Dato colateral: `drive_rc_si_units` frena diez veces mejor que `drive_with_heading`.

**Pendiente decidir** de dónde sacar la velocidad: derivarla del locator, integrarla de los
encoders, o dejarla a cero y que la estime `robot_localization`. **Ninguna probada. No tocar
`/odom` hasta medirlo.**

### El watchdog, probado por primera vez en la historia del proyecto

Existía desde `d8f182d` y nunca se había verificado. Herramienta nueva:
`mediciones_banco/medir_watchdog_ros2.py`.

```
tiempo hasta quedar quieto      527 ms
  timeout del driver           ~300 ms   <- exactamente cmd_vel_timeout
  frenada + latencia + detección ~227 ms <- físico, no software
distancia tras el corte        ~7.9 cm
```

### Cuatro errores propios de esta sesión

1. **`_enviar()` tiraba los errores a la basura.** Encolaba la corrutina y se olvidaba del
   `Future`, así que una excepción de `drive_rc_si_units` moría en silencio. Corregido con
   `add_done_callback` y una etiqueta por comando.
2. **Falta `setup.cfg` → `ros2 run` dice «No executable found»** aunque `colcon build` diga
   *Finished*. El `console_script` acaba en `bin/`, que `ros2` no mira. Documentado en el
   propio fichero.
3. **Mi herramienta midió por velocidad y concluyó «el robot NUNCA se movió»** mientras el
   robot cruzaba la habitación. **Lo corrigió el usuario, mirándolo.** La herramienta ahora
   mide desplazamiento.
4. **Mi umbral de éxito del watchdog (350 ms) estaba mal calculado**: no contaba la frenada
   física ni que `/odom` llega cada 60 ms. Ahora es `timeout + 300 ms` y lo que se juzga es la
   **distancia recorrida**, que es lo que importa con obstáculos cerca.

Y un artefacto del test: publicaba un `Twist()` vacío «de cortesía» al terminar, que reactivaba
el watchdog y lo hacía disparar dos veces. Quitado.

### Pendiente

1. **Los 16 servicios que faltan** (LEDs, IR, encoders, system info, streaming, motores crudos,
   `move_to_pose`) y 4 topics. Listados al final de `rvr_driver_node.py`. **No se portan a
   ciegas.**
2. **Decidir la velocidad de `/odom`** — ver el hallazgo de arriba. Bloquea SLAM de calidad.
3. **Fase 3: el URDF**, que el plan llama el bloqueante raíz. El driver ya publica
   `odom → base_link`, así que la mitad del problema está resuelta.
4. Decidir `ir_messages` vs `infrared_messages` (dos topics para lo mismo) y el namespace.
5. ⚠️ **Antes de la imagen dorada:** quitar `ROS_DOMAIN_ID` de `~/.bashrc`.

---

## 2026-07-30 (parte 4) — Fase 2 arrancada: `atriz_rvr_msgs` corre sobre ROS 2

**El primer código del proyecto que compila sobre ROS 2 Jazzy.** Rama nueva **`ros2`** en
`Atriz_rvr`, desde `migracion-ros2` (`24c7749`), commit `1b1239a`.

```
colcon build          Finished <<< atriz_rvr_msgs [3min 46s]
ros2 interface list   6 mensajes + 20 servicios
ros2 interface show   std_msgs/Header resuelto correctamente
import desde Python   los 26 tipos importan e instancian
```

### El port fue menos trabajo de lo que parecía

| | ROS 1 (catkin) | ROS 2 (ament) |
|---|---|---|
| Build | `catkin_package()` + `add_message_files()` + `add_service_files()` + `generate_messages()` | **un solo** `rosidl_generate_interfaces()`, con msg y srv en la misma lista |
| Rutas | `Color.msg` | `msg/Color.msg` (con prefijo) |
| `package.xml` | `format=2`, `message_generation`/`message_runtime` | `format=3`, `rosidl_default_generators`/`rosidl_default_runtime` |
| Grupo | — | **`<member_of_group>rosidl_interface_packages</member_of_group>`**, obligatorio y fácil de olvidar |

**Los 6 mensajes no necesitaron ni un cambio.** Ya estaban en `snake_case` y sin tipos `time`
ni `duration`, que son las otras dos incompatibilidades típicas de ROS 1 → ROS 2.

**El único cambio de contenido en 26 ficheros:** tres `.srv` declaraban `Header header`, y en
ROS 2 `Header` a secas **no resuelve** — tiene que ser `std_msgs/Header`. Afectaba a
`MoveToPose`, `MoveToPosAndYaw` y `SetPosAndYaw`.

### `COLCON_IGNORE` en los otros dos paquetes

`atriz_rvr_driver` y `atriz_rvr_serial` siguen siendo catkin y romperían el build del
workspace entero. Llevan `COLCON_IGNORE` hasta que les toque el port. Es el mecanismo estándar
de colcon y deja `colcon list` mostrando solo lo que de verdad se puede construir.

### 🐛 La identidad de git es por repositorio, no global

El primer `git commit` en `Atriz_rvr` falló con *«Author identity unknown»*: el 2026-07-30 se
había configurado `user.name`/`user.email` **solo en `atriz_migracion`**, con `git config` sin
`--global`. Peor aún: el `git push` de la rama **sí funcionó** —subiéndola sin el commit—, así
que el fallo era fácil de pasar por alto.

Corregido con `git config --global`, para que el tercer repositorio (`Atriz_web_server`) no
repita el tropiezo. **Va a `provision.sh`** como parte del aprovisionamiento.

### El mapa del driver, medido antes de tocarlo

Para el port del nodo, que es lo siguiente:

| | |
|---|---|
| Publishers | 7: `odom`, `imu`, `color`, `encoders`, `ambient_light`, `infrared_messages`, `ir_messages` |
| Subscribers | 3: `cmd_vel`, `cmd_degrees`, `is_emergency_stop` |
| Servicios | 20 |
| Handlers async del SDK | 12 |
| Estructura | **funciones a nivel de módulo compartiendo estado global**, sin clase |

Esa última fila es el trabajo real: `rclpy` quiere un `Node`, así que el port no es sustituir
`rospy` por `rclpy` línea a línea, es **reestructurar**.

Dos cosas anotadas al hacer el mapa, para revisar durante el port:
- Hay **dos publishers para lo mismo**: `infrared_messages` e `ir_messages`. Decidir cuál se
  queda antes de portar los dos.
- `Publisher('odom')` y el resto van **sin namespace**. Con un `ROS_DOMAIN_ID` por robot el
  namespace `/rvr_NN` no es imprescindible para el aislamiento, pero `ARQUITECTURA.md` lo
  contempla y la web lo espera. Decidirlo en el port, no después.

### Pendiente

1. **Portar `Atriz_rvr_node.py` a `rclpy`** (Fase 2.3 y 2.4), con los dos puntos de seguridad:
   el **watchdog de `cmd_vel`** y `imu.angular_velocity` en **rad/s**.
2. **Limpieza previa** (Fase 2.1): borrar los `.cpp`, `src/rvr++/`, el paquete
   `atriz_rvr_serial` y `scripts/rvr-ros.py` en lugar de portarlos.
3. Decidir los dos puntos del mapa: `ir_messages` vs `infrared_messages`, y el namespace.

---

## 2026-07-30 (parte 3) — ROS 2 Jazzy instalado y verificado (Etapa E1)

```
ros2 doctor            All 5 checks passed
paquetes ros-jazzy     201 en estado 'ii', 0 a medio instalar
pub/sub sobre DDS      9.997 Hz · min 0.099 s · max 0.101 s · sigma 0.35 ms
entorno                ROS_DISTRO=jazzy · ROS_DOMAIN_ID=1 · rmw_fastrtps_cpp
disco                  4.0 GB usados de 29 GB
```

**σ de 0.35 ms sobre 10 Hz.** Dato de referencia útil: cuando la odometría real vaya a
16.5 Hz, ya sabemos que el jitter **no** lo introduce el middleware.

### 🔴 La imagen de 24.04 para Raspberry Pi viene sin `noble-updates`

El `apt install` falló con `held broken packages` en `zlib1g-dev`, `libzstd-dev`,
`liblz4-dev` y `dpkg-dev`. La pista estaba en el `apt update`: **dos** repositorios de Ubuntu
donde deberían haber tres.

`/etc/apt/sources.list.d/ubuntu.sources` solo lista `noble` y `noble-security`. El fichero
está fechado en la creación de la imagen y nadie lo había tocado: **es como se distribuye**.

El mecanismo no es obvio: las bibliotecas de runtime *sí* se actualizan desde
`noble-security` (a versiones con sufijo `.1`), pero sus `-dev`, que exigen una versión
**exacta** de la runtime, viven en `noble-updates`. Sin ese repositorio la dependencia es
insatisfacible. Y `ros-dev-tools` arrastra esos `-dev`, así que **sin ellos no hay
`colcon build`**: no es cosmético.

Tras el arreglo aparecieron además **46 paquetes actualizables** que llevaban sin llegar —
eran los bug fixes que no son de seguridad.

Atacado en los tres sitios: **manual 5.2.0** (nuevo, antes del 5.2, con el mensaje de error
literal para que sea encontrable), **`provision.sh`** (lo arregla antes del primer `apt
update`, así que queda dentro de la imagen dorada) y **`verificar_robot.sh`** (comprobación
nueva, probada: lo detecta y da el comando de arreglo).

### El método de las claves GPG había cambiado — el ⚠️ COMPROBAR estaba justificado

Se usa el paquete oficial **`ros2-apt-source` 1.2.0**, no el `curl` del keyring a mano,
porque **mantiene la clave actualizada por sí solo**. Con la clave puesta a mano, el día que
caduque —y ya pasó una vez, rompiendo `apt` en todas las instalaciones de ROS del mundo— se
rompen los 16 robots a la vez y hay que entrar en cada uno.

Auditado antes de instalarlo como root: **sin scripts de mantenedor** (solo `control` y
`md5sums`), solo coloca el keyring, el `.sources` y un symlink. Clave de Open Robotics,
huella `C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654`, **caduca 2030-06-01** — después del fin de
soporte de Jazzy (mayo 2029), así que no caducará a mitad del proyecto.

### 🐛 «Existe `setup.bash`» NO significa «ROS 2 está instalado»

Estuve a punto de dar la instalación por terminada mirando el fichero. `dpkg` decía otra cosa:

```
ls /opt/ros/jazzy/setup.bash            -> existe
source setup.bash; echo $ROS_DISTRO     -> jazzy
dpkg-query -W ros-jazzy-ros-base        -> install ok UNPACKED
dpkg -l 'ros-jazzy-*' | grep -c '^ii'   -> 0          <- CERO configurados
```

En un Pi 4, 509 paquetes tardan 15-20 min y `apt` los procesa en dos fases. Entre
desempaquetar y configurar, el sistema **parece** listo.

Es la misma lección que ya estaba dos veces en este repositorio: un nodo que arranca no
prueba que el UART funcione (cap. 1.5), y un servicio en verde no prueba que haya hecho su
trabajo (cap. 4.3). **Comprueba el efecto, no el indicio.** Documentado como cap. 5.4.1.

`verificar_robot.sh`, bloque 8 reescrito a partir de eso: cuenta paquetes en estado `ii` y
consulta `dpkg-query` por paquete distinguiendo `ok installed` de `unpacked`. **Probado en
vivo durante la propia instalación:** detectó «solo 35 paquetes configurados: la instalación
está a medias».

### 🐛 El capítulo 5.5 pedía algo imposible

`ros2 run demo_nodes_cpp talker` → **`Package 'demo_nodes_cpp' not found`**. No viene en
`ros-base`, es un paquete aparte. Sustituido por `ros2 topic pub`/`echo`/`hz`, que vienen en
`ros2cli` y verifican lo mismo **sin añadir un paquete a 16 robots**.

### Tres defectos propios más, todos del mismo patrón

1. **`grep -c` imprime `0` Y sale con código 1**, así que un `|| echo 0` concatenaba un
   segundo cero y la variable quedaba `"0\n0"`, rompiendo la aritmética. Es **el mismo patrón
   que rompió `systemctl is-enabled`** esta misma mañana. Tercera aparición del día.
2. Mi `pgrep -f 'listener'` encontró **`sshd`**, cuya línea de comando contiene literalmente
   `[listener]`. Falso positivo inofensivo porque matamos por PID, pero es exactamente la
   trampa del `pkill -f` ya documentada.
3. `bash -lc` no ejecuta `~/.bashrc` (el de Ubuntu tiene un `return` si no es interactivo),
   así que mi primera comprobación del entorno dio vacío y **parecía** que la configuración
   había fallado. Era la prueba, no la configuración.

### Un dato mío corregido

`FLOTA.md` decía **«~1.5 GB por robot»** como si fuera medido. Era una estimación **inflada
unas cinco veces**: el `apt` real dice **157 MB** de descarga para ROS 2 (509 paquetes,
703 MB en disco), del orden de **300 MB por robot** en total. La conclusión (imagen dorada) no
cambia, pero el número sí. Y se añade el argumento que de verdad pesa más: **el tiempo**,
15-20 min de instalación por robot contra ~8 min de grabar una tarjeta, en paralelo.

### El driver sigue sin poder ejecutarse, y eso es lo esperado

`Atriz_rvr_node.py` es **ROS 1**: 1704 líneas, **99 referencias a `rospy`**, 48
`asyncio.run()`, 3 paquetes **catkin**. No es «sin probar», es **imposible** hasta el port.
`colcon build` fallará y debe fallar. Lo validado es el **SDK**, que es la pieza
insustituible; el driver es código propio y por tanto reescribible.

**`verificar_robot.sh` pasa de 39 a 48 aserciones. En `rvr-01`: 48 correctas, 0 fallos,
código de salida 0.**

### Pendiente

1. **Fase 2 del plan — portar el driver a `rclpy`.** El trabajo grande, y merece su propia
   sesión: incluye el **watchdog de `cmd_vel`** (hoy si cae la red el robot sigue con el
   último comando), `imu.angular_velocity` a **rad/s** (hoy viola REP-103), sacar el event
   loop de asyncio a su propio hilo, y borrar el lastre de C++ que nunca se ejecutó.
2. **Fase 3 — URDF.** El plan lo llama **el bloqueante raíz**: el árbol TF está partido, y sin
   un árbol conectado SLAM es imposible por mucho que el driver funcione.
3. ⚠️ **Antes de la imagen dorada: quitar `ROS_DOMAIN_ID` de `~/.bashrc`.** Está puesto a mano
   ahí porque `atriz-first-boot` no está instalado todavía. El `.bashrc` se lee **después** de
   `/etc/profile.d/`, así que si se clona tal cual, **los 16 robots quedarían en el dominio 1**
   sin que nada avise. `verificar_robot.sh` ya comprueba esa colisión.
4. 👤 Reserva DHCP de `rvr-01`, dónde está guardada la imagen `dd`, y si la contraseña de
   `sphero` se rotó. Siguen abiertos de la parte 2.

---

## 2026-07-30 (parte 2) — 🟢 GO, y la infraestructura para los 15 robots restantes

### 🟢 GO — el SDK de Sphero funciona en Python 3.12

**Es la decisión que bloqueaba todo el proyecto, y sale a favor.**

| Comprobación | Resultado |
|---|---|
| Los 103 ficheros del SDK | compilan sin errores de sintaxis en 3.12 |
| `SpheroRvrAsync` construido en | **0.0 s** (el atajo: 0 s = responde, ~10 s = dos timeouts) |
| Batería | 100 % |
| Firmware Nordic | **9.1.462** — el documentado |
| Streaming con `interval=60` | **16.67 Hz** |

**16.67 Hz en Python 3.12 sobre 24.04, frente a 16.59 Hz en Python 3.8 sobre 20.04.** Mismo
rendimiento. El análisis estático del 2026-07-29 predijo un parche de ~4 líneas; resultaron ser
**cero**.

Lo que este GO **no** significa: el driver sigue siendo ROS 1 (catkin) y no compilará con
`colcon` hasta el port de la Fase 2. Lo validado es la pieza insustituible, el SDK.

### El primer intento dio un NO-GO FALSO, y el script tenía la culpa

`ModuleNotFoundError: No module named 'aiohttp'`. **No era una incompatibilidad con Python
3.12: era un paquete que faltaba.** `sphero_sdk/__init__.py` importa todo de golpe, y esa
cadena llega a `common/firmware/cms_fw_check_base.py:2`, que hace `import aiohttp` a nivel de
módulo. En 20.04 estaba instalado por casualidad (aparece en el `pip list` del respaldo), así
que la dependencia nunca se había notado.

El script marcaba `aiohttp` como «opcional, no afecta al backend serie» en el paso 2/6 **y
moría por él en el 4/6** — sugiriendo replantear la arquitectura del proyecto por un paquete
que se instala en diez segundos. Corregido: las tres dependencias son obligatorias y cada una
dice cómo instalarse.

Que `aiohttp` solo se **use** para consultar el firmware contra un servicio web de Sphero es
cierto e irrelevante: el import es incondicional.

### Las tres dependencias, y dónde va cada una

| Módulo | Cómo | Dónde queda |
|---|---|---|
| `pyserial` 3.5 | `apt` (`python3-serial`, ya venía) | `/usr/lib/python3/dist-packages` |
| `aiohttp` 3.9.1 | `apt` (`python3-aiohttp`) | `/usr/lib/python3/dist-packages` |
| `pyserial-asyncio` 0.6 | `pip3 --break-system-packages` | `/usr/local/lib/python3.12/dist-packages` |

`pyserial-asyncio` **no existe como paquete apt** (`apt-cache policy` vacío): es la única que
obliga a `pip`, y 24.04 aplica PEP 668.

**Error propio corregido:** se instaló primero con `pip --user`, dejándolo en
`/home/sphero/.local`. Funciona para la prueba, pero un servicio systemd puede no verlo según
su `User=` y en la imagen dorada quedaría enterrado en el home de un usuario. Reinstalado a
nivel de sistema y **eliminada la copia de usuario**, que enmascaraba la del sistema.

---

### Infraestructura para no repetir esto 15 veces

Tres scripts nuevos, escritos **después** de instalar `rvr-01` a mano — no antes, para no
automatizar suposiciones.

**`verificar_robot.sh`** — 39 aserciones, código de salida ≠ 0 si algo falla. Es la pieza más
valiosa: hoy se verificó este robot con ~25 comandos sueltos y aparecieron **cinco fallos
silenciosos**; repetir eso a ojo en 15 robots garantiza que algo se cuele.

Su regla es **comprobar el efecto, no la intención**, y cada decisión viene de un fallo real:
no mira `config.txt` para saber si `disable-bt` está aplicado sino el device-tree; no se fía de
`systemctl is-enabled snapd`, que hoy mintió; lee el power-save con `grep -oi` porque `iw`
imprime `Power save:` con mayúsculas; sabe que `is-enabled cloud-init` dice `enabled` aunque
esté desactivado y lo dice en voz alta; y no usa `ps -e | wc -l` como métrica.
**Probado en `rvr-01`: 39 correctas, 0 fallos.** (Ampliado a **48** al instalar ROS 2 — ver la entrada de la parte 3.)

**`provision.sh`** — de un 24.04 limpio a robot terminado, idempotente. No duplica nada:
orquesta `fase_0_1_fix_uart.sh` y `fase_1_higiene_so.sh`. Su bloque de ROS 2 está
**deliberadamente vacío**, porque la Etapa E no se había ejecutado al escribirlo y poner
comandos sin probar es lo que este proyecto no hace.

**`preparar_tarjeta.sh`** — corre en el **PC** sobre una tarjeta recién grabada: `cmdline.txt`,
`config.txt` con `[all]` y `robot_id.txt`. Elimina el editar ficheros con el Bloc de notas, que
para un robot es tolerable y para 15 es una fuente garantizada de errores silenciosos. Probado
en seco contra copias de la partición FAT, incluido un **caso de control**
(`dtoverlay=dwc2,dr_mode=host` bajo `[cm4]` se detecta como inactivo), que es lo que demuestra
que el `awk` distingue secciones de verdad.

### Por qué imagen dorada: es ancho de banda, no comodidad

Aprovisionar un robot descarga ~1.5 GB *(⚠️ estimación, corregida a ~300 MB medidos en la parte 3)*. Quince robots serían ~22 GB sobre la única AP del
laboratorio**, que es el riesgo nº4 de `FLOTA.md` — el que sigue sin medir y el más probable.
Con imagen dorada son **0 GB de red**.

Pero una imagen que nadie sabe reconstruir es una **caja negra**, y ese es exactamente el
problema del `MANUAL SPHERO.docx` original. De ahí la relación: `provision.sh` construye el
robot de referencia, la imagen se hace de él, y si divergen **gana el script**. Coste por robot
nuevo: **~3 minutos atendidos**.

### Un tercer defecto propio, encontrado al probar

`verificar_robot.sh --hardware` salía **siempre** con código 2, porque el aviso «esto despierta
el robot» —informativo— se estaba contando como problema. Eso deja el código de salida inútil
para automatizar «¿pasó este robot?». Corregido a mensaje informativo.

### Pendiente

1. **Etapa E1: instalar `ros-jazzy-ros-base`** (manual cap. 5.2, todavía NO VERIFICADO), y
   luego la Fase 2 del plan: portar el driver a `rclpy` con el **watchdog de `cmd_vel`** y las
   unidades en rad/s.
2. 👤 **Reserva DHCP para `rvr-01`** (MAC `d8:3a:dd:d6:c1:ee`). Hoy tiene IP dinámica
   `192.168.1.58` y puede cambiar. Mejor hacerlo con un robot que con dieciséis.
3. 👤 **Anotar dónde está guardada la imagen `dd`**, con sus dos copias. Hay una tabla
   esperándolo en `RECUPERACION.md`. Una imagen que nadie encuentra no es un respaldo.
4. 👤 **Confirmar si la contraseña de `sphero` se rotó** al grabar la imagen. No se puede
   comprobar desde el sistema. En cualquier caso sigue pendiente purgarla del historial de
   `Atriz_web_server`.
5. La regla udev de `/dev/ydlidar` por `ID_PATH` está **propuesta y NO VERIFICADA**: falta
   comprobar que el `ID_PATH` coincide entre dos robots. Si no coincidiera, no es clonable en
   la imagen dorada y habría que generarla en `first-boot.sh`.
6. Medir el arranque tras el próximo reinicio: `snapd.seeded` (3.5 s de los 8.7 s) ya está
   fuera, así que debería bajar. **No se anota ninguna cifra hasta medirla.**

---

## 2026-07-30 (parte 1) — Instalación de 24.04: etapas A, B y C recorridas y verificadas

**El sistema nuevo está instalado y a punto.** Ubuntu Server 24.04.4 LTS · aarch64 ·
Python 3.12.3 · `rvr-01`. Los capítulos **1, 3, 4 y 8** del manual dejan de estar
NO VERIFICADO. Falta el go/no-go del SDK (Etapa D), que es el siguiente paso.

### Los dos scripts fallaban justo donde tocaba usarlos

Ambos con la misma raíz: **fallo silencioso**.

**`fase_0_1_fix_uart.sh` abortaba en el paso 1/4.** Tenía
`USERCFG=/boot/firmware/usercfg.txt` fijo. En 24.04 ese fichero no existe, así que el `grep`
fallaba, caía al `else`, y el `cp -a` sobre un fichero inexistente mataba el script por
`set -euo pipefail` — **antes de escribir la regla udev**. Síntoma: `/dev/rvr` no aparecía.

**`fase_1_higiene_so.sh` no apagaba el power-save del WiFi.** El `ExecStart` era
`iw ... || true`, y **`iw` no viene instalado en Ubuntu Server 24.04**. El
`wifi-no-powersave.service` quedaba en verde sin hacer nada, para siempre. Ahora instala `iw`
(esperando el lock de dpkg, que en un robot recién grabado lo tiene `unattended-upgrades`),
quita el `|| true`, **comprueba el efecto real**, y acumula los pasos no aplicados para
imprimirlos al final y salir con código 1. Antes terminaba en verde pasara lo que pasara.

### Por qué no existe `usercfg.txt` — la respuesta, con evidencia

No falta: **Ubuntu abandonó el esquema en 24.04.** En 20.04, `config.txt` decía «DO NOT
modify» y terminaba en `include syscfg.txt` + `include usercfg.txt`, gestionados por
**`pibootctl`**. En 24.04 `pibootctl` **no se instala**, `config.txt` es la plantilla upstream
de Raspberry Pi OS (`vc4-kms-v3d`, `camera_auto_detect`, `[pi02]`, `[cm4]`) y **no tiene
ninguna línea `include`**. Búsqueda en todo el sistema: cero resultados.

**Crear `usercfg.txt` a mano sería un fichero fantasma** que el firmware nunca lee.

Y **la cabecera `[all]` es obligatoria**: la imagen termina en `[cm4]`, así que lo añadido al
final sin `[all]` quedaría restringido a esa placa y **no se aplicaría en un Pi 4** — existiría
en el fichero sin hacer nada. El script ahora respeta las secciones al comprobar si una clave
está activa; un `grep` normal habría dado por bueno un `disable-bt` colgando bajo `[cm4]`.

Dato colateral útil: `enable_uart=1` estaba en **ambas** versiones. Lo único que faltó siempre
fue `disable-bt`.

### `unattended-upgrades` viene activo y actualizó el kernel solo

Durante la propia sesión instaló 8 lotes de paquetes en 4 minutos, incluido
`linux-image-6.8.0-1060-raspi` sobre un sistema corriendo el `1047`, dejando
`/var/run/reboot-required`.

Obligó a reordenar el plan: **cerrar las actualizaciones y reiniciar antes de tocar el
device-tree**, o un mismo reinicio aplica dos cambios y un fallo posterior no es atribuible
(regla nº4). Nuevo apartado 3.5.1 del manual. El capítulo 4 lo deshabilita.

También aprovechó que `dtoverlay=disable-bt` **ya estaba en efecto** (editado desde Windows
antes del primer arranque) para ahorrarse un reinicio: la regla udev y los `systemctl` surten
efecto al instante, así que el script ahora solo pide reiniciar cuando de verdad hace falta.

### Verificado sobre el robot real

| Prueba | Resultado |
|---|---|
| `uart0` | `/soc/serial@7e201000` (PL011) · mini-UART `disabled` |
| `/dev/rvr` | → `ttyAMA0` |
| `raw_uart.py` | **el RVR CONTESTA (55 bytes)** · firmware `09 00 01 01` = **9.1.462** |
| `x2_parse.py` | **1144/1144 checksums = 100 %**, 2970 muestras/s, **11.48 Hz**, 1.39° |
| Higiene | `multi-user.target`, governor `performance`, `Power save: off`, `cloud-init` fuera, timers de `apt` fuera, `noatime`, `systemctl --failed` vacío |

El número de bytes de `raw_uart.py` varía entre ejecuciones (46 en 20.04, 55 aquí) porque el
RVR intercala notificaciones asíncronas. Lo que importa es que haya respuesta con checksum
válido, no la cifra.

### `x2_parse.py` mentía, y ya no

Imprimía **480 Hz** de frecuencia de giro en 20.04 y **741 Hz** en 24.04, para un sensor cuya
especificación son 6–12 Hz. Calculaba la mediana de los intervalos de llegada de paquetes, que
salen del buffer USB **a ráfagas** de ~1.3 ms. Ahora divide vueltas entre duración: **11.48
Hz**, coincidiendo con las 138 vueltas contadas a mano el 2026-07-29.

Queda la lección general: **un timestamp tomado al leer de un buffer no mide cuándo ocurrió el
evento.** `CLAUDE.md` pasa de «dos herramientas mienten» a una.

### Un falso positivo propio, y por qué se deja escrito

El mecanismo de fallo ruidoso que se añadió al script de higiene **reportó
`power-save NO quedó apagado` cuando sí lo estaba**. La causa era el verificador: buscaba
`power save:` en minúsculas e `iw 6.7` imprime `Power save: off`. Corregido con `grep -oi`.

Se documenta porque es el resultado honesto: el mecanismo funcionó a la primera y lo primero
que encontró fue a sí mismo. Sigue siendo preferible a un verificador que da verde mintiendo,
que es exactamente lo que hacía el script antes.

Segundo defecto del mismo estilo: `systemctl is-enabled` de una unidad ausente imprime
`not-found` **y** sale con código ≠ 0, así que el `|| echo no` concatenaba ambas cosas en la
misma variable.

### No se podía hacer `git push`

El sistema nuevo no tenía credenciales: `git fetch` fallaba con `could not read Username`, sin
credential helper, sin `~/.git-credentials` y con `~/.ssh/authorized_keys` **vacío**. El
respaldo de la Fase 0.3 copiaba `~/.ssh` pero **no el token**.

Corregido en `fase_0_3_respaldo.sh` (respalda `~/.git-credentials` y `~/.gitconfig`), y
documentado en `CLAUDE.md` e `INSTALACION.md` §B5 como paso propio de toda instalación nueva.
El script también deja de crear un `estado_sistema_*.txt` nuevo cuando el contenido no ha
cambiado: seis ejecuciones dejaron seis ficheros idénticos salvo la fecha.

### Estado de los tres repositorios — nada se perdió al reflashear

Verificado con `git ls-remote` contra GitHub:

| Repo | Rama | Commit |
|---|---|---|
| `Atriz_rvr` | `main` | `6f48ae1` |
| `Atriz_rvr` | `migracion-ros2` | `24c7749` |
| `Atriz_rvr` | `wip/scripts-estudiantes` | `62e0313` |
| `Atriz_web_server` | `pruebas` | `924d659` |

Coinciden exactamente con lo documentado en `TRASPASO.md`. El stash rescatado sobrevivió.

### Nueva carpeta de evidencia

`00_auditoria/evidencia_24_04/`, con su `README.md`, separada de `00_auditoria/evidencia/`
(el sistema viejo). **Comparar 24.04 contra los números de 20.04 es la deriva que este
repositorio existe para evitar**, así que la separación es deliberada y está avisada en los
seis sitios donde el manual pide «comparar con la línea base».

Línea base de 24.04 recién instalado: userspace **1 min 39 s** (`cloud-final` = 1 min 7 s),
187 tareas, journal 17.7 MB, `io.full total` 74.6 s / 34 min, governor `ondemand`,
`graphical.target`, 63.7 °C sin throttling.

### Pendiente

1. **Etapa D — el GO/NO-GO del SDK en Python 3.12.** Es el siguiente paso y el punto de
   decisión de toda la migración. No instalar ROS 2 antes.
2. **Medir la Etapa C con contadores a cero:** arranque, tareas y presión de I/O tras el
   reinicio. Los números pre-reinicio incluyen todo el trabajo de `apt` y no sirven.
3. **Confirmar si la contraseña de `sphero` se rotó de verdad** al grabar la imagen. No se
   puede comprobar desde el sistema; hay que preguntarlo. En cualquier caso sigue pendiente
   purgarla del historial de `Atriz_web_server`.
4. **Anotar dónde está guardada la imagen `dd`** (dos copias). Hay una tabla vacía esperándolo
   en `RECUPERACION.md`. Una imagen que nadie encuentra no es un respaldo.
5. La regla udev de `/dev/ydlidar` por `ID_PATH` está **propuesta y NO VERIFICADA**. Falta
   comprobar que el `ID_PATH` coincide entre dos robots distintos; si no, no es clonable en la
   imagen dorada y habría que generarla en `first-boot.sh`.
6. Siguen abiertas las decisiones de `01_avanzar.py` / `wip/scripts-estudiantes` y de
   `carro.py` / `prueba.py`.

---

## 2026-07-29 (tarde) — Fase 0.1 completada y auditoría corregida

**Fase 0.1 — completada y verificada sobre el robot real.**

### Lo más importante: el clon local estaba desactualizado

`~/atriz_git/src/Atriz_rvr` estaba **5 commits por detrás de GitHub** y **nunca se le
había hecho `git fetch`**. La auditoría de la mañana se hizo sobre código de octubre
de 2025, ignorando trabajo de marzo de 2026. **Tres hallazgos resultaron erróneos** —
ver «Correcciones tras verificar en banco» en el informe.

Lección para el resto del proyecto: `git fetch` **antes** de auditar nada.

### Estructura de ramas

- `main` local puesto al día con `origin/main` (`659364c`), fast-forward limpio.
- Rama nueva **`migracion-ros2`** creada **desde `origin/main`**, no desde el local obsoleto.
- Los 3 scripts de estudiantes sin commitear quedaron en `stash@{0}`.
- `migracion-ros2` **subida a GitHub** (`24c7749`).

### UART reparado y verificado

- `dtoverlay=disable-bt` + `enable_uart=1` en `/boot/firmware/usercfg.txt`
- `/etc/udev/rules.d/99-rvr.rules` → `/dev/rvr` → `ttyAMA0` (PL011)
- `bluetooth.service` deshabilitado (no había adaptador registrado)
- Verificado con paquetes crudos: el RVR responde con checksum válido

Falsa alarma que costó tiempo: `uart0_pins` queda con `brcm,pins` vacío tras
`disable-bt`. Decompilando el overlay se ve que **es intencional** — el firmware
asigna los pines, no el kernel. Los cero bytes iniciales eran simplemente que
**el robot estaba dormido**.

### Odometría: de 3.85 Hz a 16.59 Hz con una línea

| `interval` | Frecuencia | σ |
|---|---|---|
| 250 ms (original) | 3.85 Hz | 1.7 ms |
| 100 ms | 9.94 Hz | 2.4 ms |
| **60 ms (elegido)** | **16.59 Hz** | **2.8 ms** |
| 50 ms | no arranca | — |

El firmware cuantiza a múltiplos de 20 ms. Medido también a nivel del SDK sin ROS:
resultado **idéntico**, lo que demuestra que **el anti-patrón del event loop NO era
el cuello de botella**, como afirmaba la auditoría.

Cierra el riesgo «115200 baud no aguanta 20 Hz»: 125 paquetes/s a 60 ms, holgado.

### LIDAR X2 verificado — por primera vez en el proyecto

Nunca se había comprobado. Detectado como CP2102 en `/dev/ttyUSB0` y validado
decodificando el protocolo X2 a mano, **sin instalar el driver ROS**:

| Métrica | Resultado |
|---|---|
| Checksums válidos | **1147 / 1147 = 100 %** |
| Muestras | **2998/s** (especificación: 3000/s) |
| Giro | 138 vueltas en 12.1 s = **11.4 Hz** |
| Puntos por vuelta | 263 → resolución angular **1.37°** |
| Distancias | 0.445 – 3.158 m, mediana 1.205 m |

**Con esto, todo el hardware del robot está verificado.** Lo que queda es software.

Corrección documentada: `x2_parse.py` imprime "480.72 Hz de giro", que es **falso** —
mide intervalos de llegada de paquetes, que llegan a ráfagas desde el buffer USB. El
valor real sale de contar vueltas.

Aviso para la flota: el CP2102 reporta `SerialNumber "0001"`, genérico. Con 16
adaptadores iguales no se podrá hacer regla udev por serial.

### Commits en `migracion-ros2`

```
24c7749  Sensores: bajar el intervalo de streaming de 250 ms a 60 ms
67c8776  UART: usar /dev/rvr en lugar de /dev/ttyS0
```

### Pendiente

1. ~~Subir `migracion-ros2`~~ ✅ hecho (`24c7749` en GitHub).
2. **Fase 0.3 (bloqueante)** — imagen `dd` de la microSD antes de reflashear.
3. ~~Prueba de estabilidad larga~~ ✅ **SUPERADA**: 12 min, 11 962 mensajes a 16.59 Hz,
   **0 huecos**, **0 discontinuidades de secuencia**, **0 mensajes perdidos**, RSS plano
   en 53 MB, temperatura 55.5–57.9 °C. Evidencia en
   `00_auditoria/evidencia/mediciones_banco/estabilidad_12min_2026-07-29.txt`.
4. **Sin medir:** el impacto de las 48 llamadas a `asyncio.run()` en la latencia de
   `cmd_vel`. No afirmar nada sobre ello sin datos.
5. ~~Sin verificar: la parada de emergencia de la web~~ 🔴 **CONFIRMADA ROTA**. Probado
   de extremo a extremo: la web publica en `/rvr/emergency_stop`, que **no existe**;
   el flag no se mueve. Con el topic correcto (`is_emergency_stop`) sí funciona.
   Falla en silencio con `200 OK`. Evidencia en `estop_2026-07-29.txt`.

---

## 2026-07-29 (mañana) — Auditoría inicial y creación del repositorio

**Fase 00 — completada.** Repositorio publicado en
<https://github.com/Bura-hub/Atriz_migracion_ros2> (privado), commit `f714a74`.

### Qué se hizo

- Auditoría completa del sistema: hardware, SO, arranque, rendimiento, térmica,
  almacenamiento, red, UART, software y logs.
- Auditoría del repositorio `Atriz_rvr` (3 paquetes catkin, ~1650 líneas de driver).
- Auditoría de la plataforma web `Atriz_web_server` (rama `pruebas`).
- Transcripción del `MANUAL SPHERO.docx` a Markdown, con anotaciones de auditoría.
- Análisis de compatibilidad del SDK de Sphero con Python 3.12.
- Creación de este repositorio con auditoría, plan, manual y respaldos.

### Qué se verificó

| Medición | Valor |
|---|---|
| Temperatura en reposo-medio | 59.9 °C estable (5 muestras) |
| Throttling / under-voltage | 0 eventos en `dmesg` |
| CPU a 600 MHz | **59.6 %** del tiempo (`time_in_state`) |
| Bloqueo global por I/O | **46.97 s** en 42 min de uptime ocioso |
| Journal | 785 MB, `journald.conf` vacío |
| Arranque | 6.1 s kernel + 29.5 s userspace |
| Tareas en ejecución | 273, con ROS parado |
| Sesiones gráficas | 2 simultáneas (gdm + sphero) |
| WiFi | -62 dBm, 797 reintentos Tx, power-save **on** |
| `dtoverlay=disable-bt` | **ausente** en todos los ficheros de boot |
| `usercfg.txt` | **vacío** |
| Adaptador Bluetooth | **ninguno** (`hciconfig -a` sin salida), `bluetoothd` activo 2m21d |
| `/dev/serial0` | **no existe** |
| Driver YDLIDAR en el sistema | **no existe** (`find` → 0 resultados) |
| SDK Sphero: imports de ROS | **0** de 103 ficheros |
| SDK Sphero: patrones rotos en Py3.12 | **0** `@asyncio.coroutine`, **0** `loop=`, **0** `yield from` |
| SDK Sphero: `get_event_loop()` | 4, de los cuales 3 en el backend `observer` no usado |

Salidas crudas en [`00_auditoria/evidencia/`](00_auditoria/evidencia/).

### Decisiones tomadas

- **Migrar a Ubuntu Server 24.04 + ROS 2 Jazzy** (soporte hasta mayo 2029).
- **Reinstalar sobre la misma microSD**, no comprar tarjeta nueva.
  Reversión mediante imagen `dd` + el manual original.
- **La web hablará por rosbridge + roslibjs**, no por SSH.
- **Un `ROS_DOMAIN_ID` por robot** — aislamiento DDS total, coordinación en el servidor.
- Alcance objetivo para un robot: teleoperación + telemetría + LIDAR + SLAM + Nav2.
- **Sin cámara** en los robots (confirmado): no se instala `web_video_server`.

### Pendiente para la próxima sesión

1. **Fase 0.1** — aplicar `dtoverlay=disable-bt` + regla udev `/dev/rvr`, deshabilitar
   `bluetooth.service`. Validar 10 min de `/odom` sin cortes. Requiere `sudo` y reinicio.
2. **Fase 0.3 (bloqueante)** — imagen `dd` de la microSD antes de reflashear.
3. Commitear o descartar los 6 cambios sueltos de `Atriz_rvr`
   (respaldados en `04_respaldo/sin_commitear/`).

### Riesgos abiertos

- **Go/no-go de toda la migración:** que el SDK de Sphero funcione en Python 3.12.
  El análisis estático es muy favorable, pero **no está verificado en ejecución**.
  Se prueba al inicio de la Fase 1, antes de portar una sola línea del driver.
- **Sin verificar:** que la parada de emergencia de la web esté realmente rota.
  Los nombres de topic no coinciden (`/rvr/emergency_stop` vs `is_emergency_stop`),
  pero no se ha probado en banco. Es seguridad — verificar como prioridad.
- La credencial del usuario `sphero` está expuesta en GitHub público y **no se ha rotado**.
