"""Absolutely minimal test with no imports."""


def test_addition():
    """Test that doesn't import anything."""
    assert 1 + 1 == 2


def test_string():
    """Another test with no dependencies."""
    assert "hello" + "world" == "helloworld"


def test_list():
    """Test list operations."""
    my_list = [1, 2, 3]
    assert len(my_list) == 3
    assert sum(my_list) == 6