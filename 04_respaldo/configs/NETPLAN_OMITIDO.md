# Configuración de red — deliberadamente NO incluida

`/etc/netplan/50-cloud-init.yaml` contiene la **PSK del WiFi en texto plano** y por
eso no se versiona en este repositorio.

Estructura (sin credenciales) para reconstruirla tras reinstalar:

```yaml
network:
  version: 2
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      access-points:
        "<SSID>":
          password: "<PSK>"
```

En Ubuntu 24.04 lo habitual es dejar que **Raspberry Pi Imager** preconfigure el WiFi
durante el flasheo, en cuyo caso este fichero se genera solo.

> Ver también §5.1 del plan: la contraseña del usuario `sphero` está expuesta en el repositorio
> público `Atriz_web_server` y debe rotarse.
