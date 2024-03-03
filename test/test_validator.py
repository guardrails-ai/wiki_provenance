import pytest
from guardrails import Guard
from validator import WikiProvenance

# Instantiate the validator
validator = WikiProvenance(on_fail="exception", topic_name="Apple company")


# Test happy path
@pytest.mark.parametrize(
    "value",
    [
        "Apple Inc. is an American multinational technology company headquartered in Cupertino, California, in Silicon Valley.",
        "Apple was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in April 1976 to develop and sell Wozniak's Apple I personal computer.",
    ],
)
def test_happy_path(value):
    """Test happy path."""
    guard = Guard.from_string(validators=[validator])
    response = guard.parse(value)
    print("Happy path response", response)
    assert response.validation_passed is True


# Test fail path
@pytest.mark.parametrize(
    "value",
    [
        "Apple Inc. is an Indian oil company headquartered in Mumbai, India.",
        "As of March 2023, Apple is the world's largest technology company by revenue. It was founded in October 2001 by Ratan Tata.",
    ],
)
def test_fail_path(value):
    """Test fail path."""
    guard = Guard.from_string(validators=[validator])
    with pytest.raises(Exception):
        response = guard.parse(value)
        print("Fail path response", response)
