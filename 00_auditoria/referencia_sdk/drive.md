# Documentación oficial del protocolo del RVR — drive

> 🔴 **Copia de rescate.** `sdk.sphero.com` **ya no existe**. Esto viene de
> archive.org (captura de 2021-06-11) y lo encontró el usuario el 2026-08-01.
>
> ⚠️ Documenta el **protocolo del robot**, no el SDK de Python. Hay comandos aquí que la
> librería **no expone** — `get_motor_temperature` y `force_battery_refresh`, por ejemplo.
>
> Análisis de lo relevante en `../evidencia_24_04/43_documentacion_sdk_rescatada.txt`.

---

Drive
Raw Motors
Run left and right motors at a speed between 0 and 255. Set driving mode using flags.
Parameters:
LeftMode
- (
Raw Motor Modes
- uint8) Drive mode: 0x0-off, 0x1-forward, 0x2-reverse
LeftSpeed
- (uint8) Proportional to 0-255 input
RightMode
- (
Raw Motor Modes
- uint8) Drive mode: 0x0-off, 0x1-forward, 0x2-reverse
RightSpeed
- (uint8) Proportional to 0-255 input
Returns:
None
Reset Yaw
Sets current yaw angle to zero. (ie current direction is now considered 'forward'.)
Parameters:
None
Returns:
None
Drive With Heading
Drive towards a heading at a particular speed. Flags can be set to modify driving mode.
Parameters:
Speed
- (uint8) 0 to 255 value
Heading
- (uint16) 0 to 359 degrees (0 degrees is forward, 90 degrees is to the right, 180 degrees is back, and 270 is to the left)
Flags
- (
Drive Flags
- uint8) Relevant flags: Drive Reverse, Boost, Fast Turn Mode
Returns:
None
Enable Motor Stall Notify
Enables motor stall notifications.
Parameters:
IsEnabled
- (bool) True for enable.  False for disable
Returns:
None
Motor Stall Notify
Motor stall protection change notification.
Parameters:
None
Returns:
MotorIndex
- (
Motor Indexes
- uint8) ID of motor that we want an alert for when the status has changed.
IsTriggered
- (bool) True when protection triggered.  False when protection resumed normal
Enable Motor Fault Notify
Enables notification for when there is a motor fault.
Parameters:
IsEnabled
- (bool) True for enable.  False for disable
Returns:
None
Motor Fault Notify
Notification that a motor fault has occurred.
Parameters:
None
Returns:
IsFault
- (bool) True for fault.  False for no fault
Get Motor Fault State
Get the motor fault state.
Parameters:
None
Returns:
IsFault
- (bool) True for fault.  False for no fault
Enums:
Raw Motor Modes
Off
: 0
Forward
: 1
Reverse
: 2
Motor Indexes
Left Motor Index
: 0
Right Motor Index
: 1
Bitmasks:
Drive Flags
Drive Reverse
: bit 0
Boost
: bit 1
Fast Turn
: bit 2
Left Direction
: bit 3
Right Direction
: bit 4
Enable Drift
: bit 5
←
Connection
Io
→
Raw Motors
Reset Yaw
Drive With Heading
Enable Motor Stall Notify
Motor Stall Notify
Enable Motor Fault Notify
Motor Fault Notify
Get Motor Fault State
