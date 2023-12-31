import asyncio
import logging
from asyncio import StreamWriter, StreamReader
from datetime import datetime, timedelta
from threading import Timer
from typing import Union, ForwardRef

from exceptions import CommandException

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class Message:
    def __init__(self, message: str,
                 sender: ForwardRef('User'),
                 is_private: bool = False
                 ):
        self.__message = message
        self.__sender = sender
        self.__is_private = is_private

    @property
    def message(self):
        return self.__message

    @property
    def sender(self):
        return self.__sender

    def __repr__(self):
        text = f'{self.sender} - {self.message}'
        if self.__is_private:
            text = 'PRIVATE MESSAGE ' + text
        return text


class User:
    def __init__(self,
                 address,
                 reader: StreamReader,
                 writer: StreamWriter) -> None:
        self.__address = address
        self.__reader = reader
        self.__writer = writer
        self.__nickname = ''
        self.__reports = set()
        self.__messages_count = 0
        self.__first_message_datetime = None

    @property
    def is_banned(self):
        return len(self.__reports) >= Server.MAX_REPORTS_COUNT

    @property
    def is_throttled(self):
        return (self.__messages_count >= 20 and
                (self.__first_message_datetime + timedelta(
                    seconds=Server.THROTTLING_TIME)) > datetime.now()
                )

    @property
    def address(self):
        return self.__address

    @property
    def nickname(self):
        return self.__nickname

    @nickname.setter
    def nickname(self, value):
        self.__nickname = value

    @property
    def reports(self):
        return self.__reports

    @reports.setter
    def reports(self, value):
        self.__reports = value

    @property
    def messages_count(self):
        return self.__messages_count

    @messages_count.setter
    def messages_count(self, value):
        self.__messages_count = value

    @property
    def first_message_datetime(self):
        return self.__first_message_datetime

    @first_message_datetime.setter
    def first_message_datetime(self, value):
        self.__first_message_datetime = value

    async def send_message(self, msg: Union[Message, str]):
        """Sending a message to user."""
        logger.info(f'Sent message '
                    f'{str(msg)}')
        self.__writer.write((str(msg) + '\n').encode('utf8'))
        await self.__writer.drain()

    async def get_message(self) -> Message:
        """Getting a new message from user."""
        data = await self.__reader.read(1024)
        message = data.decode()[:-1]
        return Message(message=message, sender=self)

    def clear_reports(self) -> None:
        """Clearing user's reports to unban him."""
        logger.info(f'{self} has been unbanned')
        self.__reports = set()

    def clear_messages_count(self) -> None:
        logger.info(f'Cleared messages count for {self}')
        self.__messages_count = 0

    def __repr__(self) -> str:
        return self.nickname


class Server:
    NEWBIE_MESSAGES_LIMIT = 20  # Limit of group chat messages history
    MAX_REPORTS_COUNT = 3  # Reports count to block a user
    MESSAGE_LIFETIME = 60 * 60  # Message lifetime before its deleting
    BAN_TIME = 4 * 60 * 60  # Time user will be blocked in the group chat
    THROTTLING_TIME = 60 * 60  # Time to flush user's message throttling
    PRIVATE_COMMAND = '/p'
    REPORT_COMMAND = '/report'
    QUIT_COMMAND = '/quit'

    def __init__(self, host='127.0.0.1', port=8000):
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
        await asyncio.sleep(1)
        address = writer.get_extra_info('peername')
        logger.info(f'New connection from {address}')
        new_user = User(address, reader, writer)
        await new_user.send_message('Please type your nickname\n')
        await self._set_nickname(new_user)
        connected_message = Message(sender=new_user,
                                    message='has been connected')
        await self._send_to_group_chat(connected_message)
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
            logger.info(f'Got new message {msg.message}')

            if msg.message.startswith(self.QUIT_COMMAND):
                await msg.sender.send_message('Goodbye!')
                await self._quit(msg.sender)
                break
            if msg.message[0] == '/':
                await self._parse_command(msg)
            else:
                await self._send_to_group_chat(msg)

    async def _send_chat_history(self, user: User) -> None:
        """Sending a group chat history."""
        await user.send_message(
            'Group chat history:\n' +
            '\n'.join(map(str, self.history[:self.NEWBIE_MESSAGES_LIMIT])) +
            '\n'
        )

    async def _send_to_group_chat(self, msg: Message) -> None:
        """Sending a message to the group chat."""
        sender = msg.sender

        if sender.is_banned:
            await sender.send_message('You have been banned for 4 hours')
        elif sender.is_throttled:
            throttling_time_end = (sender.first_message_datetime + timedelta(
                seconds=Server.THROTTLING_TIME))
            await sender.send_message(f'Only 20 messages per hour\n'
                                      f'Retry after {throttling_time_end}')
        else:
            if msg.message.strip():
                if sender.messages_count >= 20:
                    sender.messages_count = 0
                if sender.messages_count == 0:
                    sender.first_message_datetime = datetime.now()
                sender.messages_count += 1
                self.history.append(msg)
                Timer(self.MESSAGE_LIFETIME, self._delete_message,
                      args=(msg,)).start()
                for user in self.users.values():
                    if user != sender:
                        await user.send_message(msg)

    async def _parse_command(self, msg: Message) -> None:
        """Parsing a user's command."""
        try:
            command, body = msg.message.split(maxsplit=1)
            if command == self.PRIVATE_COMMAND:
                await self._send_private_message(body, msg)
            if command == self.REPORT_COMMAND:
                await self._report_user(msg.sender, body[:-1])
            else:
                raise CommandException('Wrong command\n')
        except CommandException as e:
            await msg.sender.send_message(e)
        except ValueError:
            await msg.sender.send_message('Incorrect command format\n')
        except Exception as e:
            logger.error(e)

    async def _set_nickname(self, user: User) -> None:
        """Setting new user's nickname."""
        while True:
            msg = await user.get_message()
            nickname = msg.message[:-1]
            if await self._is_valid_nickname(nickname):
                break
            await user.send_message(
                'User with this nickname is already in chat\n'
                'Please choose another one')
        user.nickname = nickname
        self.users[nickname] = user
        await user.send_message(f'Welcome here, {nickname}\n')

    async def _is_valid_nickname(self, nickname: str) -> bool:
        """User's unique nickname validation."""
        if nickname:
            if nickname not in self.users:
                return True
        return False

    async def _send_private_message(self, body: str,
                                    msg: Message) -> None:
        """Sending a private message to another user."""
        nickname, text = body.split(maxsplit=1)
        try:
            user = self.users[nickname]
            if user == msg.sender:
                raise CommandException('You cant send messages to you')
        except KeyError:
            raise CommandException('User not found')
        await user.send_message(
            Message(text, msg.sender, is_private=True))

    def _delete_message(self, msg: Message) -> None:
        """Deleting a message from chat history."""
        logger.info(f'{msg} has been removed from history due to the lifetime')
        self.history.remove(msg)

    async def _report_user(self, user: User,
                           user_to_block_nickname: str
                           ) -> None:
        """Reporting a user."""
        user_to_block = self.users[user_to_block_nickname]
        if user_to_block == user:
            raise CommandException('You cant report yourself')
        user_to_block.reports.add(user)
        if len(user_to_block.reports) == self.MAX_REPORTS_COUNT:
            Timer(self.BAN_TIME, user_to_block.clear_reports).start()
        await user.send_message('Report is sent')

    async def _quit(self, sender: User) -> None:
        self.__users.pop(sender.nickname)


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start_server())
