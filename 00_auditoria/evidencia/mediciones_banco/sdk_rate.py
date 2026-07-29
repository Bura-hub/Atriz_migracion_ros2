import asyncio, sys, time, statistics
sys.path.insert(0, '/home/sphero/atriz_git/devel/lib/python3/dist-packages')
from sphero_sdk import SpheroRvrAsync, SerialAsyncDal, RvrStreamingServices

loop = asyncio.get_event_loop()
rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))
T = {}
def mk(n):
    T[n] = []
    async def h(data, n=n): T[n].append(time.time())
    return h

INTERVAL = int(sys.argv[1])

async def main():
    await rvr.wake(); await asyncio.sleep(2)
    await rvr.sensor_control.clear()
    for name, svc in (('locator', RvrStreamingServices.locator),
                      ('imu', RvrStreamingServices.imu),
                      ('velocity', RvrStreamingServices.velocity)):
        await rvr.sensor_control.add_sensor_data_handler(service=svc, handler=mk(name))
    await rvr.sensor_control.start(interval=INTERVAL)
    print(f"streaming a interval={INTERVAL} ms, midiendo 12 s...", flush=True)
    await asyncio.sleep(12)
    await rvr.sensor_control.clear(); await rvr.close()

loop.run_until_complete(main())
print()
for n, ts in T.items():
    if len(ts) < 3: print(f"  {n:9}: {len(ts)} muestras"); continue
    gaps = [(ts[i+1]-ts[i])*1000 for i in range(len(ts)-1)]
    print(f"  {n:9}: {len(ts):4d} msgs -> {(len(ts)-1)/(ts[-1]-ts[0]):5.2f} Hz | mediana {statistics.median(gaps):6.1f} ms | sigma {statistics.pstdev(gaps):5.1f} ms")
