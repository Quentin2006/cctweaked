import asyncio
import websockets


# WebSocket handler on port 3000
async def handle(ws):
    print("Computer connected!")
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


async def main():
    async with websockets.serve(handle, "0.0.0.0", 3000, compression=None):
        print(f"WebSocket server on port 3000")
        await asyncio.Future()


asyncio.run(main())
