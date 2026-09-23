import pytest
from models import User

def test_user_creation():
    user = User(id=1, name="John Doe")
    assert user.id == 1
    assert user.name == "John Doe"

def test_user_creation_invalid():
    with pytest.raises(ValueError):
        User(id=2, name="Jane")
