# Direccionamiento de la flota — una dirección por red, y que el nombre funcione

**Estado:** ✅ **APLICADO en rvr-01 el 2026-08-04 por la tarde, y verificado desde el cliente.**
Evidencias [74](../evidencia/74_una_direccion_por_red.txt) (el robot) y
[75](../evidencia/75_navegador_por_nombre.txt) (el navegador).

- `hostname -I` da **una sola** dirección; `[Match] SSID=` casó el fichero de casa sin scripts.
- 🔴 Hizo falta **`publish-aaaa-on-ipv4=no` además de `use-ipv6=no`** — este apaga el *transporte*
  IPv6, pero el registro `AAAA` **se seguía anunciando por el transporte IPv4**. No estaba en este
  plan: salió al medir.
- ✅ `ws://rvr-01.local:9090` **abre en el navegador** (4339 ms en frío, 2331 caliente) y el muro
  entra **por nombre**.

⏳ **Sigue sin probarse el aula entera:** `05-atriz-lab.network` **nunca ha casado con nada**, no
está probado que networkd re-evalúe el `[Match] SSID=` al mudarse sin reiniciar, ni que todo
sobreviva a un **arranque en frío** — que es justo lo que hará el robot 7.

---

## Contexto: por qué se rehace algo que estaba «verificado»

El 2026-08-01 se cerró una decisión con un ✅ en `CLAUDE.md` y en `FLOTA.md`:

> **«Estática y DHCP CONVIVEN en `wlan0`»** — 3 direcciones IPv4 a la vez. *Era la suposición
> «A VERIFICAR» que sostenía todo el diseño de flota.* **«Este robot se lleva al laboratorio sin
> tocar un solo comando.»**

**La medición era correcta y la conclusión incompleta.** Se verificó desde el punto de vista del
**robot** —¿puede tener las tres direcciones a la vez?— y nunca desde el del **cliente**. El
2026-08-04, con la web ya construida, el usuario avisó de que «no funciona nada en flota». Medido
en el navegador, con el robot encendido y sano (evidencia del PC, `CHANGELOG` parte 13):

```
ws://rvr-01.local:9090     🔴 12 s sin abrir, sin error y sin cierre
ws://10.14.7.7:9090        🔴 12 s igual   <- LA MISMA FIRMA
ws://192.168.1.58:9090     ✅ abre
ws://192.168.1.200:9090    ✅ abre
```

`rvr-01.local` resuelve a **cuatro** direcciones y el resolutor las devuelve en este orden:
`fe80::…` (IPv6 link-local **sin zona**, que el navegador no puede usar), `10.14.7.7` (la
estática del laboratorio, un agujero negro desde casa), y **después** las dos que sirven. Las dos
primeras no fallan: **se cuelgan**, y un SYN sin respuesta tarda ~21 s en rendirse.

🔴 **Para un cliente, desde cualquier red al menos una de las direcciones del robot es un agujero
negro.** En el aula ocurre lo mismo al revés, y allí funciona **por suerte**: `10.14.7.7` ordena
antes que las de casa.

⚠️ **Y el diagnóstico fácil engaña:** `ping rvr-01.local` responde en **1 ms** —elige el `fe80::`
con su zona— y `Resolve-DnsName` lista las cuatro sin quejarse. Las dos herramientas dicen que el
nombre está bien. Lo que falla es abrir un TCP **desde el navegador**.

📌 El PC ya puso un **paliativo** en `atriz-lab`: plazo de conexión de 5 s (necesario por sí
mismo: un socket colgado nunca llama a `onclose`, así que la reconexión con espera creciente no
llegaba a arrancar) y **dirección escrita a mano por robot**. Esto último no escala a 16 robots
que además se mudan, y es lo que este diseño viene a retirar.

## Restricciones, confirmadas con el usuario

| | |
|---|---|
| Las IP del laboratorio **las asigna el administrador de red**, una por robot | no se pueden cambiar ni sustituir por reservas DHCP |
| En casa la dirección es **`192.168.1.200`** | elección del usuario |
| Las dos redes dan **puerta de enlace y DNS, con internet** | apagar el DHCP **no** cuesta NTP |
| La Pi **no tiene RTC** | sin NTP arranca con la hora mal, y el agente de sesión se niega a arrancar con el reloj sin sincronizar |
| Un robot inalcanzable | obliga a ir físicamente al edificio. Son 16 |

## Lo que se descartó, y por qué

**Un gancho de `networkd-dispatcher`** que aplicara la dirección según el SSID. Fue la primera
propuesta y la tumbaron tres revisiones independientes. Motivos medidos:

- 🔴 **Corre antes de que llegue la concesión del DHCP.** Con estáticas, `wlan0` pasa a
  `routable` al ponerse la primera, **antes** de la concesión; el gancho borraría la otra y
  después networkd añadiría la del DHCP. **Quedarían dos IPv4 igualmente** — el objetivo no se
  cumple ni en el mejor caso.
- 🔴 `networkd-dispatcher` está **`inactive`** (`ConditionResult=no`): su unidad solo arranca si
  ya existe un fichero en `routable.d/`, y la condición se evalúa al arrancar. Copiar el fichero
  no la levanta.
- 🔴 **Dos dueños de la misma dirección:** cualquier `netplan apply` o reconfiguración de
  networkd deshace un `ip addr del`. Nada de lo que hace el gancho es persistente.
- 🔴 `promote_secondaries=1` **medido** en `wlan0`: al borrar una dirección, las conexiones TCP
  atadas a ella **no reciben RST, se cuelgan**.

**Reservas DHCP por MAC:** imposible, las direcciones vienen asignadas.

**Dejarlo en el cliente** (el paliativo actual): 16 direcciones a mano, dos por robot según dónde
esté, y alguien cambiándolas al mudarse.

---

## El diseño

### Tres capas, un dueño cada una

Hoy hay **dos dueños peleando por la capa 3**. El diseño los separa:

| capa | quién | qué hace |
|---|---|---|
| **Asociación wifi** | netplan → `netplan-wpa-wlan0.service` | autenticarse contra el SSID. **No se toca** |
| **Direccionamiento** | `/etc/systemd/network/*.network` con `[Match] SSID=` | una dirección y una puerta, la del sitio donde esté |
| **Publicación** | avahi | anunciar **solo** lo que un cliente puede usar |

Funciona porque asociación y capa 3 **ya están separadas** en este sistema: `netplan-wpa-wlan0.service`
corre aparte y se ocupa del WPA (verificado: unidad activa e independiente), mientras el `.network`
solo decide direcciones.

`SSID=` existe en `[Match]` — verificado en el `man systemd.network` de este robot (systemd 255):
*«A whitespace-separated list of shell-style globs matching the SSID of the currently connected
wireless LAN»*.

**El orden hace el resto:** `05-atriz-lab.network` y `06-atriz-casa.network` en `/etc` ordenan
antes que el `10-netplan-wlan0.network` que netplan deja en `/run`, y `/etc` tiene prioridad
(verificado: `/etc/systemd/network/` está hoy vacío y netplan escribe en `/run`). **Si el SSID no
casa con ninguno, cae al de netplan** — el comportamiento de hoy, intacto. El «si no sé, no toco»
lo implementa el emparejador, no un script.

### Componentes y flujo del dato

**Fuente de verdad única: `/boot/firmware/red.txt`.** No se añade ninguna fuente nueva.

```
LAB_SSID   ─┐                          /etc/systemd/network/05-atriz-lab.network
LAB_IP     ─┼─→  first-boot.sh    ─→     [Match]   Name=wlan0  SSID=<LAB_SSID>
LAB_GATEWAY─┘     --solo-red             [Network] Address=<LAB_IP>/<LAB_PREFIJO>
                                                   Gateway=<LAB_GATEWAY>
CASA_SSID  ─┐                          /etc/systemd/network/06-atriz-casa.network
CASA_IP    ─┼─→                    ─→    (lo mismo con los de casa)
CASA_GATEWAY┘
```

Categoría **B** del criterio de `scripts/sistema/README.md`: el repositorio tiene el **generador**,
no el fichero, porque hay que interpolar el SSID y la IP de cada robot. Se comprueba **por efecto**.

### Tres cambios que van juntos, y ninguno sirve solo

1. **`DHCP=no`** en `red.txt`. Sin esto la dirección del DHCP se queda **gane quien gane** el
   emparejamiento, y el objetivo no se cumple. Es lo que hundió la propuesta descartada.
2. **El netplan deja de llevar `addresses:`** — solo asociación y `dhcp4: false`. Si las conserva,
   vuelven las dos estáticas.
3. **`use-ipv6=no`** en `/etc/avahi/avahi-daemon.conf`. Deja de publicarse el `AAAA fe80::`, que el
   navegador **no puede usar** y en el que se cuelga 21 s. Sin esto, aunque quede una sola IPv4,
   el `fe80::` sigue ordenando primero y **no se arregla nada**.

### Dos correcciones de datos que entran aquí

- 🔴 **`LAB_IP` se deriva** de `LAB_BASE`+`LAB_OCTETO`+`robot_id` cuando está vacía
  (`first-boot.sh:157`). El generador de los `.network` tiene que usar **la IP ya derivada**, no
  releer la clave: con la plantilla tal cual, `LAB_IP=` está **vacía** y en 15 de los 16 robots no
  se escribiría nada. Fue el error exacto de la propuesta descartada.
- 🔴 **rvr-01 no sigue el esquema de la flota:** tiene `10.14.7.7`, y `LAB_BASE=10.14.7` +
  `LAB_OCTETO=100` daría `10.14.7.101`. Como las direcciones **las asigna el administrador**, se
  retiran `LAB_BASE`/`LAB_OCTETO` de la plantilla y `LAB_IP` pasa a ser obligatoria. Un esquema
  derivado que nadie usa es una trampa esperando.

## Modos de fallo

| camino | qué pasa | por qué se acepta |
|---|---|---|
| SSID no casa con ninguno | gana el `.network` de netplan → comportamiento de hoy | el robot **sigue alcanzable** |
| `red.txt` sin `LAB_GATEWAY` o sin `LAB_IP` | el generador **se niega** y no escribe ese fichero | mejor no arrancar que arrancar sin ruta |
| `.network` mal escrito | networkd lo ignora y cae al de netplan | mismo suelo |
| Se pierde la asociación wifi | no afecta: la hace `netplan-wpa-wlan0.service` | separación de capas |

🔴 **El riesgo real:** con `use-ipv6=no` **y** la IPv4 del sitio mal, se pierden **las dos vías**.
Hoy el `fe80::` es la red de rescate por SSH. Por eso el **orden de aplicación no es negociable**:
primero el direccionamiento, comprobar que la IPv4 responde, y **solo entonces** tocar avahi.

⏳ **NO VERIFICADO, y no se va a fingir que se sabe:** si `networkd` re-evalúa el `[Match] SSID=`
al saltar de una red a otra **sin reiniciar**. El manual lo describe; eso es haberlo leído. Si
resultara que no, el diseño **sigue sirviendo** —el robot arranca ya en la red correcta— pero
pierde el «se muda en caliente», y eso se escribe en vez de suponerse.

## Verificación

Se comprueba **el efecto, desde el lado del cliente**, que es donde falló la vez anterior.

```
1 · en casa  →  ip -4 addr show wlan0   UNA sola dirección: 192.168.1.200
2 ·          →  ip route show default   existe, vía 192.168.1.1
3 ·          →  resolver rvr-01.local   UNA dirección, y es la .200
4 ·          →  abrir ws://rvr-01.local:9090 DESDE EL NAVEGADOR   ← el criterio
5 · mudanza  →  repetir 1-4 en el aula, sin tocar comandos
```

🔴 **El paso 4 es el único que vale, y necesita control:** *antes* del cambio tiene que **fallar**
con la firma medida —12 s sin abrir, sin error y sin cierre—. Si no falla antes, no se está
midiendo lo que se cree.
🔴 **`ping` y `Resolve-DnsName` NO sirven como verificación**: las dos daban verde con el fallo
presente.
⚠️ Se aplica con `sudo netplan try --timeout 90`, que **revierte solo** si deja al robot
incomunicado.

## Lo que este diseño NO resuelve

**El aislamiento de clientes del AP del aula.** Si el punto de acceso aísla clientes, mDNS no
llega y el navegador no ve al robot **haga lo que haga este diseño**. Sigue siendo la F0 sin medir,
y necesita estar en el aula.

## Alcance documental

**21 ficheros** mencionan direccionamiento o imagen dorada, y hay **once líneas que quedan falsas**.
Se actualizan las que afirman estado actual:

| fichero | qué queda falso |
|---|---|
| `03_operacion/FLOTA.md` | «Estática y DHCP conviven — verificado», «se muda sin tocar un solo comando», «no hace falta reserva DHCP» y la tabla de asignación |
| `CLAUDE.md` | **dos decisiones marcadas ✅** en la tabla de decisiones cerradas |
| `TRASPASO.md` | «resolviendo por nombre, sin ninguna IP; `wlan0` lleva tres direcciones a la vez» |
| `scripts/red.txt.ejemplo` | `DHCP`, y retirar `LAB_BASE`/`LAB_OCTETO` |
| `02_manual/MANUAL_ATRIZ_ROS2.md` | cap. 19, el ejemplo de `red.txt` y la lista que «verifica que conviven» |
| `scripts/first-boot.sh` | el generador |
| `scripts/verificar_robot.sh` | la sección 12 cuenta 3 IPv4 como correcto; pasa a exigir **una** |

📝 **El `CHANGELOG` NO se reescribe.** La decisión vieja se corrige con una entrada nueva que
explique por qué era incompleta, no borrando la anterior: es la bitácora, y su valor está en que
se pueda ver cómo se llegó al error.
