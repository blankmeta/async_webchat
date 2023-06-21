import asyncio
import logging
from asyncio import StreamWriter, StreamReader
from typing import Union

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class Message:
    def __init__(self, message: str, sender):
        self.__message = message
        self.__sender = sender

    @property
    def message(self):
        return self.__message

    @property
    def sender(self):
        return self.__sender

    def __repr__(self):
        return f'{self.sender} - {self.message}'


class User:
    def __init__(self,
                 address,
                 reader: StreamReader,
                 writer: StreamWriter) -> None:
        self.__address = address
        self.__reader = reader
        self.__writer = writer

    @property
    def address(self):
        return self.__address

    async def send_message(self, msg: Union[Message, str]):
        """Sending a message from user."""
        self.__writer.write((str(msg) + '\n').encode('utf8'))

    async def get_message(self) -> Message:
        """Getting a new message from user."""
        data = await self.__reader.read(1024)
        return Message(message=data.decode()[:-1], sender=self)

    def __repr__(self) -> str:
        return ':'.join(map(str, self.address))


class Server:
    def __init__(self, host="127.0.0.1", port=8000):
        self.__host = host
        self.__port = port
        self.__users = []
        self.__history = []

    @property
    def users(self):
        return self.__users

    @property
    def history(self):
        return self.__history

    async def client_connected(self, reader: StreamReader,
                               writer: StreamWriter):
        """Handling a connected user."""
        address = writer.get_extra_info('peername')
        logger.info(f'New connection from {address}')
        new_user = User(address, reader, writer)
        self.users.append(new_user)
        await self._send_to_group_chat(
            Message(sender=new_user,
                    message='has been connected')
        )

        await self._send_chat_history(new_user)
        await self._listen(new_user)
        print('Client connected')

    async def start_server(self):
        """Starting a server."""
        srv = await asyncio.start_server(
            self.client_connected, self.__host, self.__port
        )
        logging.info(f'Server started on {self.__host}:{self.__port}')

        async with srv:
            await srv.serve_forever()

    async def _listen(self, user):
        """Listening for user messages."""
        while True:
            msg = await user.get_message()
            logger.info(f'Got new message {msg.message} from {msg.sender}')
            await self._send_to_group_chat(msg)

    async def _send_chat_history(self, user):
        for msg in self.history:
            await user.send_message(msg)

    async def _send_to_group_chat(self, msg: Message):
        self.history.append(msg)
        for user in self.users:
            if user != msg.sender:
                await user.send_message(msg)


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start_server())
