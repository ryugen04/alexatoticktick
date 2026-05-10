from alexa_ticktick_bridge.logging import mask_email, redact_mapping, stable_hash


def test_redacts_secrets_and_item_names() -> None:
    data = {
        "email": "person@example.com",
        "password": "secret",
        "token_response": {"access_token": "abc"},
        "title": "milk",
    }

    redacted = redact_mapping(data)

    assert redacted["email"] == "p***@example.com"
    assert redacted["password"] == "<redacted>"
    assert redacted["token_response"] == "<redacted>"
    assert redacted["title"] == "<item:redacted>"


def test_stable_hash_is_stable() -> None:
    assert stable_hash("milk") == stable_hash("milk")
    assert stable_hash("milk") != stable_hash("eggs")
    assert mask_email("not-an-email") == "<redacted>"
