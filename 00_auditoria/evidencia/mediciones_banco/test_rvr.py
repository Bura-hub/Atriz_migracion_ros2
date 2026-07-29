import asyncio, sys, time
sys.path.insert(0, '/home/sphero/atriz_git/devel/lib/python3/dist-packages')
from sphero_sdk import SpheroRvrAsync, SerialAsyncDal

# Igual que Atriz_rvr_node.py: se construye FUERA de un loop en ejecucion,
# porque SpheroRvrAsync.__init__ hace run_until_complete() para el fw check.
loop = asyncio.get_event_loop()
print("[i] construyendo SpheroRvrAsync (incluye check de firmware)...", flush=True)
t0 = time.time()
try:
    rvr = SpheroRvrAsync(dal=SerialAsyncDal(loop))
    print(f"[OK] construido en {time.time()-t0:.1f}s -> el RVR RESPONDE", flush=True)
except Exception as e:
    print(f"[FALLO] en construccion tras {time.time()-t0:.1f}s: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)

async def main():
    await rvr.wake()
    await asyncio.sleep(2)
    bat = await asyncio.wait_for(rvr.get_battery_percentage(), timeout=10)
    print(f"[OK] BATERIA: {bat}", flush=True)
    v = await asyncio.wait_for(rvr.get_main_application_version(), timeout=10)
    print(f"[OK] FIRMWARE: {v}", flush=True)
    await rvr.close()

try:
    loop.run_until_complete(asyncio.wait_for(main(), timeout=30))
    print("\n[RESULTADO] ENLACE UART FUNCIONANDO", flush=True)
except asyncio.TimeoutError:
    print("\n[RESULTADO] TIMEOUT - el RVR no responde", flush=True)
except Exception as e:
    print(f"\n[RESULTADO] {type(e).__name__}: {e}", flush=True)
