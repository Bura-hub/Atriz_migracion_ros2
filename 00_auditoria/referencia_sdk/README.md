# Documentación del protocolo del RVR — copia de rescate

🔴 **`sdk.sphero.com` ya no existe.** Esta es la única copia que tenemos de la documentación
oficial del protocolo, recuperada de archive.org (captura del 2021-06-11) el 2026-08-01.

⚠️ **Documenta el PROTOCOLO DEL ROBOT, no el SDK de Python.** Por eso describe comandos que la
librería vendorizada **no expone**. Cuando el SDK y el robot no cuadren, mira aquí antes de
teorizar — este proyecto ya dio por «roto» un comando que era **asíncrono por diseño**.

| Fichero | Qué cubre | Lo más útil |
|---|---|---|
| [`sensor.md`](sensor.md) | sensores, color, IR, streaming, térmica | 🔴 `Get Motor Temperature` («calculated from **motor current**») · máscara de los 4 sensores IR · `Set Locator Flags` |
| [`drive.md`](drive.md) | conducción, atasco, fallo de motor | confirma que **no existe** `get_motor_stall_state` · banderas `Boost`/`Fast Turn`/`Enable Drift` |
| [`power.md`](power.md) | batería y sueño | umbrales e **histéresis** de la alerta de batería · `Force Battery Refresh` |
| [`system_info.md`](system_info.md) | identidad del robot | MAC, SKU, revisión de placa — ya los usa el driver |
| [`io.md`](io.md) | LEDs | los grupos y la máscara |
| [`connection.md`](connection.md) | enlace | — |

**El análisis de lo que afecta a este proyecto está en
[`../evidencia_24_04/43_documentacion_sdk_rescatada.txt`](../evidencia_24_04/43_documentacion_sdk_rescatada.txt)**,
incluidos **dos errores propios** que esta documentación destapó.
