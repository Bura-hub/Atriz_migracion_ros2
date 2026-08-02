# Prueba de aceptación de un robot — de arranque en frío a navegación autónoma

> **Para qué existe.** Todo en este proyecto se ha verificado **por partes**: los LEDs un día, el
> `collision_monitor` otro, Nav2 otro, siempre sobre un robot ya encendido y toqueteado a mano.
> Que cada pieza funcione por separado **no dice que arranquen juntas**. Esta prueba hace una sola
> pasada continua, desde un reinicio de verdad hasta un objetivo autónomo rodeando un obstáculo, y
> responde a una única pregunta: **¿se puede empezar la plataforma web sobre este robot?**
>
> Diseñada y acordada el **2026-08-01**, antes de abrir la Fase 5.

---

## Lo que esta prueba cierra, y lo que no

**Los tres huecos que la motivaron:**

| | |
|---|---|
| 🔴 **Nunca hubo una pasada de arranque en frío a navegación de un tirón** | Cada fase se probó en un momento distinto. Nadie ha comprobado que un robot recién reiniciado llegue solo hasta navegar |
| 🔴 **El ángulo nunca se ha medido** | `move_to_pos_and_yaw` está verificado en **distancia** (0.20 m comandados → 19.5 cm medidos, evidencia 26), pero **su componente de yaw no**, y `move_to_pose` figura como «✅» sin un número detrás |
| 🔴 **`verificar_robot.sh` no mueve el robot** | Ni con `--hardware`. Sus 105 comprobaciones son estáticas y de telemetría; toda la parte dinámica quedaba fuera |

**Lo que NO cierra, y hay que saberlo antes de empezar:** las decisiones abiertas (rosbridge sin
autenticación, el hueco de los precipicios, el `fmask` de la PSK, la rotación de la credencial).
Ninguna se arregla ejecutando nada. La prueba **las lista y se niega a dar vía libre** mientras
sigan abiertas — ver «El veredicto».

---

## Arquitectura

Un solo proceso, `scripts/prueba_aceptacion.py`, con **un nodo ROS propio y persistente** para
todas las fases.

📝 **Por qué un solo nodo y no reutilizar las herramientas de banco encadenadas:** esas
herramientas son **instrumentos de exploración, no jueces** — imprimen números, no dicen
«aprobado», y sacar un veredicto parseando su salida es frágil. Además cada una arranca y para su
propio nodo: doce arranques del SDK, con el RVR despertándose cada vez.

Se lanza por SSH después del reinicio. `--desde F4` retoma sin repetir lo ya pasado.

---

## Las diez fases

| | Fase | ¿Mueve? | Qué comprueba |
|---|---|---|---|
| **F0** | Arranque en frío | no | El robot arrancó **solo**: `uptime` (prueba que hubo reinicio de verdad), los 6 nodos del servicio, el journal limpio (ver abajo), y delega las 105 comprobaciones estáticas en `verificar_robot.sh`. Al final ejercita `Restart=always`, hoy **sin ejercitar** |
| **F1** | Telemetría | no | Los topics con su QoS y su ritmo, medidos con **ejecutor persistente**. Voltaje, estado y umbrales de batería. Que la temperatura no medida sea `NaN` y no `0.0`. Deriva de yaw en reposo |
| **F2** | LIDAR | no | `start_scan` → `/scan` a ~10 Hz con rangos sanos → `stop_scan` → se para. Y que el parche del journal aguanta: nada de inundación con el barrido parado |
| **F3** | Luces | no | 🔴 **Puerta: miras el robot.** Los cuatro servicios de LED. Lo confirmas tú con los ojos: no hay forma de leerlo desde el software |
| **F4** | Movimiento básico | **sí** | 🔴 **Puerta: pasillo despejado.** `move_timed` adelante y atrás. Y **parada de emergencia a mitad de un avance**, midiendo cuánto recorre después de recibirla |
| **F5** | **Ángulos** | **sí** | El hueco. Giros en el sitio de 90°, 180° y 360°, por `move_to_pos_and_yaw` y por `move_timed`, midiendo el **Δyaw** logrado contra `/odom` (nunca el yaw absoluto — ver abajo). También el convenio de signo |
| **F6** | Seguridad | **sí** | 🔴 **Puerta: pared enfrente.** `collision_monitor` frenando y el watchdog cortando al dejar de publicar `cmd_vel` |
| **F7** | Autónomo | **sí** | Lanza SLAM + Nav2, espera al lifecycle activo, manda el objetivo de 1.50 m. Luego 🔴 **puerta: obstáculo a 0.75 m** y repite. Vigila que no reaparezca el `Failed to make progress` |
| **F8** | Web | no | rosbridge de verdad: conectar, suscribirse y llamar a un servicio |
| **F9** | Veredicto | no | Los cuatro niveles y la lista de pendientes que bloquean |

### Dos decisiones que conviene tener a la vista

**F5 no tiene base histórica.** El ángulo nunca se midió, así que esa fase **no puede suspender
contra un número que no existe**: la primera pasada **establece la referencia** y solo avisa si
sale de una banda de cordura amplia. Llamarlo aprobado o suspenso sería fingir un criterio que no
hay.

**F0 comprueba el `uptime`.** Sin eso, la prueba «pasaría» sobre un sistema que lleva días
encendido y arreglado a mano — que es justo el sesgo que esta prueba existe para eliminar.

### El journal solo se mira en F0, y hay que decir exactamente qué se mira

Concretamente: `journalctl -u atriz-robot -p err --boot`. Dos precisiones que evitan falsos
suspensos, y las dos son trampas reales de este sistema:

- 🔴 **La comprobación del journal NO puede repetirse al final.** El driver registra la parada de
  emergencia con **nivel ERROR** (`[ERROR] PARADA DE EMERGENCIA`), y F4 y F6 la provocan a
  propósito. Buscar errores después de mover el robot encontraría **los que la propia prueba
  causó** y los llamaría regresión. Por eso va en F0, antes de que nada se mueva.
- ⚠️ **Los 5 avisos de `verificar_robot.sh` no son FALLO.** F0 los traduce uno a uno, y ninguno a
  FALLO:

  | Aviso | Se traduce a |
  |---|---|
  | `red.txt` en 755, la PSK legible | **PENDIENTE** nº 3 |
  | mDNS por enlace: `wlan0` no lo tiene | **PENDIENTE** (drop-in de systemd-networkd, manual 19.5) |
  | los `.bak-*` de apt | cosmético, se informa y ya |
  | no se pudo leer `60-atriz.yaml` (necesita root) | no concluyente: se **reintenta con `sudo -n`**, y si no hay privilegio se marca **NO VERIFICADO**, que no es lo mismo que «bien» |
  | yaw de `/odom` en reposo lejos de 0 | **se informa y no se juzga** — ver abajo, la premisa de ese aviso es falsa |

### 🔴 El yaw NO se pone a cero al reiniciar la Pi, y eso condiciona F5

Una primera versión de este diseño daba por hecho que `/odom` arrancaría en 0 tras el reinicio.
**Es falso, y estaba documentado en el propio driver desde el 2026-07-31**
(`rvr_driver_node.py:316`): `reset_yaw()` **no pone el yaw a cero**. El yaw solo se pone a cero
**al encender el RVR**, y `sudo reboot` reinicia **la Pi**, no el RVR — que tiene su propia
batería y su propio botón. El RVR arrastra su origen desde el último encendido: con uno limpio da
+0.5°, pero si se ha movido, cualquier cosa (+64.9° medido entonces; −75.9° medido hoy).

**Las dos consecuencias:**

1. **F5 mide Δyaw, nunca yaw absoluto.** Un giro de 90° se juzga por *cuánto cambió* la
   orientación, no por a dónde apunta. Es lo correcto de todos modos, pero ahora se sabe **por
   qué** y no se puede «arreglar» a la ligera.
2. **El aviso de yaw de `verificar_robot.sh` tiene una premisa falsa.** Dice «se esperaba ~0», y
   eso solo vale tras un encendido limpio del RVR. F0 lo informa sin traducirlo a nada.
   ⏳ Queda anotado como defecto a corregir en ese script, fuera del alcance de esta prueba.

📝 Si alguna vez quieres el origen limpio, hay que **apagar y encender el RVR**, no la Pi.

---

## Umbrales

**Todos salen de mediciones registradas en este repositorio. Ninguno es inventado.**

| Medida | Base medida | Fuente | Banda de aceptación |
|---|---|---|---|
| `/odom`, `/imu`, `/encoders` | 16.5 Hz | Fase 4 | ≥ 13 Hz |
| `/scan` | 9.997 Hz · σ 0.35 ms | manual cap. 12 | 9–11 Hz |
| `move_timed` 2 s @ 0.15 m/s | **30.3 cm** (101 %) | evidencia 26 | 24–37 cm |
| `move_to_pos_and_yaw` 0.20 m | **19.5 cm** (97 %) | evidencia 26 | 16–24 cm |
| `collision_monitor` | **9.9 cm** @ 0.25 · 10.6 @ 0.40 | CHANGELOG:1824 | ≤ 15 cm |
| watchdog de `cmd_vel` | **527 ms · ~7.9 cm** | CHANGELOG:3303 | ≤ 12 cm |
| Nav2, error final | **8 cm**; 9–10 en otra tanda | TRASPASO:289 | ≤ 15 cm |
| Nav2, meseta de velocidad | **0.407 m/s** · p90 0.412 | TRASPASO:293 | ≥ 0.35 m/s |
| Obstáculo, desvío lateral | **30 cm**, y vuelve al eje | manual 11.13 | 15–50 cm |
| Yaw en reposo (**deriva**, no valor) | **0.01° / 60 s** | medido 2026-08-01 | ≤ 0.5° |
| Umbrales de batería | baja 7.00 V · crítica 6.50 V | firmware | exactos |
| **Ángulos (F5)** — siempre **Δyaw** | **no hay** | — | banda de cordura; la primera pasada fija la base |

⚠️ **Casi todas son n=1 a n=4.** Por eso las bandas son anchas: un umbral que salta siempre no
vale nada, y uno que no salta nunca tampoco. Y por eso **salir de banda no es un suspenso**.

---

## El veredicto, en cuatro niveles

| | Significa | ¿Bloquea la Fase 5? |
|---|---|---|
| **FALLO** | Categórico: falta un nodo, un servicio no responde, el robot no se mueve, **la parada de emergencia no para**, Nav2 aborta, hay errores en el journal desde el arranque. Aquí no hay banda que valga: o funciona o no | **sí** |
| **REVISAR** | Funciona, pero el número se fue de banda. El informe dice cuánto y contra qué. Con n=1 detrás, llamar «suspenso» a un 20 % de desviación sería fingir una precisión que no tenemos | no por sí solo |
| **PASA** | Dentro de banda | no |
| **PENDIENTE** | Decisiones abiertas que ninguna ejecución cierra | **sí** |

**`✅ VÍA LIBRE PARA LA FASE 5` solo con cero FALLO y cero PENDIENTE.**

### Los PENDIENTE de hoy (2026-08-01)

1. 🔴 **rosbridge sin autenticación** en el 9090, exponiendo `raw_motors`, que se salta el
   `collision_monitor` y no tiene corte automático. Hay que decidirlo **antes** de escribir el
   cliente, porque cambia su arquitectura.
2. 🔴 **El hueco de los precipicios.** `collision_monitor` solo mira `/scan`, y un LIDAR 2D no ve
   un vacío a ninguna altura. Mitigado hoy solo por la regla de laboratorio (suelo continuo).
3. ⚠️ **La PSK del WiFi es legible** por cualquier usuario: falta `fmask=0177,dmask=0077` en
   `/etc/fstab`. `chmod` no sirve, es FAT.
4. ⚠️ **La credencial `sphero` sin rotar** y sin purgar del histórico de git.

📝 Esta lista se mantiene **en el propio script**, no aquí, para que no se queden desincronizados.
Este documento explica el criterio; el script lleva la cuenta.

---

## Cuando algo va mal

- **`Ctrl-C` en cualquier fase** → parada de emergencia por el camino canónico
  (`/emergency_stop`), **señal enmascarada durante la recuperación** y liberación al final.
  📝 Esto es la lección del 2026-08-01: `move_timed` corre **en el driver**, así que matar el
  cliente no para nada, y un segundo Ctrl-C durante la recuperación la abortaba a medias.
- **Una fase que revienta** → parada de emergencia, se marca FALLO, y **te pregunta si sigues** en
  vez de decidir sola.
- **Guarda de batería:** aborta por debajo de **7.0 V**, el umbral «baja» del firmware. Con la
  batería caída los motores dan menos y mediríamos una regresión que no existe.
- **Guarda de `/dev/rvr`:** si hay otro proceso hablando con el RVR, no arranca.
- **Timeout en toda llamada a servicio.** Una sola llamada sin tope cuelga la prueba entera en
  silencio — ya pasó con `get_battery_percentage()`.
- **SLAM y Nav2** se lanzan como subprocesos y se matan **por `comm`, nunca con `pkill -f`**.
- El informe se escribe **pase o falle**, en
  `00_auditoria/evidencia_24_04/47_aceptacion_<fecha>.txt`.

---

## Cómo se ejecuta

```bash
# 1. Reinicia el robot de verdad. F0 lo comprueba con el uptime.
sudo reboot

# 2. Espera a que vuelva y entra:
ssh sphero@rvr-01.local

# 3. Lánzala. Es guiada: se para y te dice qué hacer antes de cada fase física.
python3 ~/atriz_migracion/scripts/prueba_aceptacion.py

#    Retomar desde una fase concreta, sin repetir lo ya pasado:
python3 ~/atriz_migracion/scripts/prueba_aceptacion.py --desde F4
```

⚠️ **Necesitas el pasillo de siempre**: objetivos de 1.50 m y ~63 cm de holgura lateral para el
sorteo. Los umbrales están calibrados contra ese escenario, así que en otro sitio los números
**no son comparables** y REVISAR dejaría de significar nada.

⚠️ **Acciones físicas.** El robot se mueve en F4, F5, F6 y F7, y enciende LEDs en F3. Ten el
pasillo despejado y no te pongas delante.
