import asyncio

from aioconsole import ainput


class Client:
    def __init__(self, host='127.0.0.1', port=8000):
        self.__host = host
        self.__port = port
        self.__reader = None
        self.__writer = None

    @property
    def writer(self):
        return self.__writer

    async def connect(self) -> None:
        """Creating a new connection."""
        self.__reader, self.__writer = await asyncio.open_connection(
            self.__host,
            self.__port
        )
        await asyncio.gather(self.receive(),
                             self.send())

    async def receive(self) -> None:
        """Getting a new message."""
        while True:
            data = await self.__reader.read(1024)
            message = data.decode()[:-1]
            print(message)

    async def send(self) -> None:
        """Sending a message."""
        while True:
            text = await ainput()
            text += '\r\n'
            self.__writer.write(text.encode('utf8'))
            await self.__writer.drain()


if __name__ == "__main__":
    client = Client()
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt as e:
        client.writer.write('/quit\r\n'.encode('utf8'))
