from server import Message


class TestMessages:
    MESSAGE_EXAMPLE = 'test message'

    def test_public_message_to_string(self, user):
        """Checking public message __repr__."""
        msg = Message(self.MESSAGE_EXAMPLE, user)

        assert str(msg) == 'nickname - test message'

    def test_private_message_to_string(self, user):
        """Checking private message __repr__."""
        msg = Message(self.MESSAGE_EXAMPLE, user, True)

        assert str(msg) == 'PRIVATE MESSAGE nickname - test message'
