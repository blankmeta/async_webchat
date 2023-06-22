from datetime import datetime


class TestUsers:
    def test_user_is_banned(self, user):
        """Check user is_banned flag."""
        for i in range(3):
            user.reports.add(i)

        assert user.is_banned

    def test_user_is_throttled(self, user):
        """Check user is_throttled flag."""
        user.first_message_datetime = datetime.now()
        user.messages_count = 20

        assert user.is_throttled

    def test_user_clear_reports(self, user):
        """Check if user's reports can be flashed."""
        for i in range(3):
            user.reports.add(i)
        user.clear_reports()

        assert len(user.reports) == 0

    def test_user_to_string(self, user):
        """Checking __repr__."""
        user.nickname = 'nickname'

        assert str(user) == user.nickname
