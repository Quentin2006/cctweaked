import asyncio
from TurtleManager import TurtleManager, Move


async def main():
    manager = TurtleManager()
    await manager.start()

    while True:
        await manager.move(Move.UP, 5)
        await asyncio.sleep(5)
        await manager.move(Move.DOWN, 5)


asyncio.run(main())
