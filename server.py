import asyncio
import websockets

# test


async def handle(ws):
    print("Computer connected!")
    async for msg in ws:
        print(f"Received: {msg}")
        await ws.send('print("Hello from Python on NAS!")')


async def main():
    async with websockets.serve(handle, "0.0.0.0", 3000, compression=None):
        await asyncio.Future()


asyncio.run(main())
