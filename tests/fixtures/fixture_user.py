import pytest

from server import User


@pytest.fixture
def user():
    """Simple user with nickname."""
    user = User(('127.0.0.1', 52345), None, None)
    user.nickname = 'nickname'

    return user
