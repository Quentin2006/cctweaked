import asyncio
import websockets


# WebSocket handler on port 3000
async def handle(ws):
    print(f"Client connected: {ws.remote_address}")

    async def reader():
        async for msg in ws:
            print(f"Received: {msg}")

            match msg:
                case "w" | "W":
                    await ws.send("turtle.forward()")
                case "a" | "A":
                    await ws.send("turtle.turnLeft()")
                case "s" | "S":
                    await ws.send("turtle.backward()")
                case "d" | "D":
                    await ws.send("turtle.turnRight()")
                case "e":
                    await ws.send("turtle.up()")
                case "q":
                    await ws.send("turtle.down()")
                case _:
                    await ws.send("Invalid command!")

    async def periodic():
        while True:
            await asyncio.sleep(5)  # every 5 seconds
            await ws.send("turtle.up()")

    await asyncio.gather(reader(), periodic())


async def main():
    async with websockets.serve(handle, "0.0.0.0", 3000):
        print("WebSocket server on port 3000")
        await asyncio.Future()


asyncio.run(main())
