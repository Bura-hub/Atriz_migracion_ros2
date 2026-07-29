import asyncio, sys, time, statistics
sys.path.insert(0, '/home/sphero/atriz_git/devel/lib/python3/dist-packages')
from sphero_sdk import SpheroRvrAsync, SerialAsyncDal, RvrStreamingServices

loop = asyncio.get_event_loop()
rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))
INTERVAL = int(sys.argv[1])

# Los 8 servicios que registra Atriz_rvr_node.py
SVCS = [('locator', RvrStreamingServices.locator), ('quaternion', RvrStreamingServices.quaternion),
        ('gyroscope', RvrStreamingServices.gyroscope), ('velocity', RvrStreamingServices.velocity),
        ('accelerometer', RvrStreamingServices.accelerometer), ('imu', RvrStreamingServices.imu),
        ('ambient_light', RvrStreamingServices.ambient_light), ('color', RvrStreamingServices.color_detection)]
T = {}
def mk(n):
    T[n] = []
    async def h(d, n=n): T[n].append(time.time())
    return h

async def main():
    await rvr.wake(); await asyncio.sleep(2)
    await rvr.sensor_control.clear()
    ok = []
    for name, svc in SVCS:
        try:
            await rvr.sensor_control.add_sensor_data_handler(service=svc, handler=mk(name)); ok.append(name)
        except Exception as e:
            print(f"  [!] {name}: {type(e).__name__}")
    await rvr.sensor_control.start(interval=INTERVAL)
    print(f"{len(ok)} sensores @ interval={INTERVAL} ms, midiendo 15 s...", flush=True)
    await asyncio.sleep(15)
    await rvr.sensor_control.clear(); await rvr.close()

loop.run_until_complete(main())
print()
tot = 0
for n, ts in T.items():
    if len(ts) < 3: print(f"  {n:14}: {len(ts)} muestras"); continue
    tot += len(ts)
    gaps = [(ts[i+1]-ts[i])*1000 for i in range(len(ts)-1)]
    print(f"  {n:14}: {(len(ts)-1)/(ts[-1]-ts[0]):5.2f} Hz | mediana {statistics.median(gaps):6.1f} ms | sigma {statistics.pstdev(gaps):5.1f} ms")
print(f"\n  TOTAL {tot} paquetes en 15 s = {tot/15:.0f} paq/s")
