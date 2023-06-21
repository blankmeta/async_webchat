import asyncio
import pickle

from aioconsole import ainput


class Client:
    def __init__(self, host='127.0.0.1', port=8000):
        self.__host = host
        self.__port = port
        self.__reader = None
        self.__writer = None

    async def connect(self) -> None:
        self.__reader, self.__writer = await asyncio.open_connection(
            self.__host,
            self.__port
        )
        await asyncio.gather(self.receive_messages(),
                             self.send_to_server())

    async def receive_messages(self):
        while True:
            data = await self.__reader.read(1024)
            message = data.decode()[:-1]
            print(message)

    async def send_to_server(self) -> None:
        while True:
            text = await ainput()
            text += '\r\n'
            self.__writer.write(text.encode('utf8'))
            await self.__writer.drain()


if __name__ == "__main__":
    try:
        asyncio.run(Client().connect())
    except Exception as e:
        print(e)
