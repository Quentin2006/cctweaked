import asyncio
from TurtleManager import TurtleManager, Move


async def main():
    manager = TurtleManager()
    await manager.start()


asyncio.run(main())
