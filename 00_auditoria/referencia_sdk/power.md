# Documentación oficial del protocolo del RVR — power

> 🔴 **Copia de rescate.** `sdk.sphero.com` **ya no existe**. Esto viene de
> archive.org (captura de 2021-06-11) y lo encontró el usuario el 2026-08-01.
>
> ⚠️ Documenta el **protocolo del robot**, no el SDK de Python. Hay comandos aquí que la
> librería **no expone** — `get_motor_temperature` y `force_battery_refresh`, por ejemplo.
>
> Análisis de lo relevante en `../evidencia_24_04/43_documentacion_sdk_rescatada.txt`.

---

Power
Sleep
Put robot into a soft sleep state. Driving, LEDS, and sensors are disabled.
Parameters:
None
Returns:
None
Wake
Wake up the system from soft sleep. Nothing to do if awake.
Parameters:
None
Returns:
None
Get Battery Percentage
Get usable battery percentage remaining.
Parameters:
None
Returns:
Percentage
- (uint8) Percent of battery that is remaining.
Get Battery Voltage State
Returns the current battery state
Parameters:
None
Returns:
State
- (
Battery Voltage States
- uint8) The current battery state.
Will Sleep Notify
Notification triggered 10 seconds before soft/deep sleep.
Parameters:
None
Returns:
None
Did Sleep Notify
Notification triggered when robot has entered soft/deep sleep.
Parameters:
None
Returns:
None
Enable Battery Voltage State Change Notify
Enables or disables notifications for changes to battery voltage state.
Parameters:
IsEnabled
- (bool) Indicates whether battery voltage state notifications should be enabled. True is enabled. False is disabled.
Returns:
None
Battery Voltage State Change Notify
Notification for battery voltage state change.
Parameters:
None
Returns:
State
- (
Battery Voltage States
- uint8) An enum representing the battery voltage state: 0 = unknown, 1 = ok, 2 = low, 3 = critical.
Get Battery Voltage In Volts
Returns the most recent battery voltage reading in volts. This results in a 'Command Failed' API error if the platform does not support calibration. Note that this command does not get a new voltage reading; it returns the most recently read value, which is updated once per second on most robots. To force the battery system to read a new value, use the 'Force Battery Refresh' command.
Parameters:
ReadingType
- (
Battery Voltage Reading Types
- uint8) Integer value indicating the type of reading you are seeking.
Returns:
Voltage
- (float, volts) Most recently read voltage of the battery.
Get Battery Voltage State Thresholds
Returns the battery voltage state thresholds and hysteresis value. The hysteresis value is added to the thresholds for rising voltages -- e.g., the voltage must be less than the low threshold to change the state to 'low battery' but it must be greater than (low threshold + hysteresis) to go back to the 'ok battery' state.
Parameters:
None
Returns:
CriticalThreshold
- (float) Float value indicating the voltage under which the battery should be read as 'critical'.
LowThreshold
- (float) Float value indicating the voltage under which the battery should be read as 'low'.
Hysteresis
- (float) Float value containing the amount by which the voltage must be above the critical or low thresholds in order for the battery to not be considered 'critical' or 'low'.
Get Current Sense Amplifier Current
Get the current draw, in AMPS, from a current sense amplifier
Parameters:
AmplifierId
- (
Amplifier Ids
- uint8) Motor amplifier id
Returns:
AmplifierCurrent
- (float) The value of the current coming from the amplifier specified in the input.
Enums:
Battery Voltage Reading Types
Calibrated And Filtered
: 0
Calibrated And Unfiltered
: 1
Uncalibrated And Unfiltered
: 2
Amplifier Ids
Left Motor
: 0
Right Motor
: 1
←
Io
Sensor
→
Sleep
Wake
Get Battery Percentage
Get Battery Voltage State
Will Sleep Notify
Did Sleep Notify
Enable Battery Voltage State Change Notify
Battery Voltage State Change Notify
Get Battery Voltage In Volts
Get Battery Voltage State Thresholds
Get Current Sense Amplifier Current
