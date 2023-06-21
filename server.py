import asyncio
import logging
from asyncio import StreamWriter, StreamReader
from typing import Union, ForwardRef

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class Message:
    def __init__(self, message: str, sender: ForwardRef('User')):
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
        self.__nickname = ''

    @property
    def address(self):
        return self.__address

    @property
    def nickname(self):
        return self.__nickname

    @nickname.setter
    def nickname(self, value):
        self.__nickname = value

    async def send_message(self, msg: Union[Message, str]):
        """Sending a message to user."""
        logger.info(f'Sent message \n'
                    f'{str(msg)} \n'
                    f'to {self}')
        self.__writer.write((str(msg) + '\n').encode('utf8'))
        await self.__writer.drain()

    async def get_message(self) -> Message:
        """Getting a new message from user."""
        data = await self.__reader.read(1024)
        message = data.decode()[:-1]
        logger.info(f'Got a new message\n'
                    f'{message}\n'
                    f'from {self}')
        return Message(message=message, sender=self)

    def __repr__(self) -> str:
        return self.nickname


class Server:
    GROUP_MESSAGES_LIMIT = 20

    def __init__(self, host="127.0.0.1", port=8000):
        self.__host = host
        self.__port = port
        self.__users = dict()
        self.__history = []

    @property
    def users(self):
        return self.__users

    @property
    def history(self):
        return self.__history

    @history.setter
    def history(self, value):
        self.__history = value

    async def client_connected(self, reader: StreamReader,
                               writer: StreamWriter):
        """Handling a connected user."""
        address = writer.get_extra_info('peername')
        logger.info(f'New connection from {address}')
        new_user = User(address, reader, writer)
        await new_user.send_message('Please type your nickname\n')
        await self._set_nickname(new_user)
        print(new_user)

        connected_message = Message(sender=new_user,
                                    message='has been connected')
        await self._send_to_group_chat(connected_message)

        print(connected_message)

        await self._send_chat_history(new_user)
        await self._listen(new_user)

    async def start_server(self):
        """Starting a server."""
        srv = await asyncio.start_server(
            self.client_connected, self.__host, self.__port
        )
        logging.info(f'Server started on {self.__host}:{self.__port}')

        async with srv:
            await srv.serve_forever()

    async def _listen(self, user: User) -> None:
        """Listening for user messages."""
        while True:
            msg = await user.get_message()
            logger.info(f'Got new message {msg.message} from {msg.sender}')

            # if msg.message[0] == '/':
            #     await self._parse_command(msg)
            # else:
            await self._send_to_group_chat(msg)

    async def _send_chat_history(self, user: User) -> None:
        await user.send_message(
            'Group chat history:\n' +
            '\n'.join(map(str, self.history)) +
            '\n'
        )

    async def _send_to_group_chat(self, msg: Message) -> None:
        if msg.message[:-1]:
            self.history.append(msg)
            self.history = self.history[:self.GROUP_MESSAGES_LIMIT]
            for user in self.users.values():
                if user != msg.sender:
                    await user.send_message(msg)

    def _parse_command(self, msg):
        command, body = msg.message.split(maxsplit=1)
        if command == '/private':
            try:
                nickname, text = body.split(maxsplit=1)
            except Exception as e:
                logger.error(e)
                logger.error(e)
                logger.error(e)

    async def _set_nickname(self, user):
        nickname = None
        while not self._is_valid_nickname(nickname):
            msg = await user.get_message()
            nickname = msg.message[:-1]

            await user.send_message('User with nickname is already in chat\n'
                                    'Please choose another one')
        user.nickname = nickname
        self.users[nickname] = user
        await user.send_message(f'Welcome here, {nickname}\n\n')

    def _is_valid_nickname(self, nickname):
        if nickname:
            if nickname not in self.users:
                return True
        return False


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start_server())
