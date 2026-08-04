"""Pure token/password tests — no DB needed."""
import time

from app.services import auth


def test_password_hash_roundtrip():
    hp = auth.hash_password("correct horse battery staple")
    assert auth.verify_password("correct horse battery staple", hp["salt"], hp["hash"])


def test_password_hash_rejects_wrong_password():
    hp = auth.hash_password("correct horse battery staple")
    assert not auth.verify_password("wrong password", hp["salt"], hp["hash"])


def test_token_roundtrip():
    token = auth.create_token("alice")
    assert auth.verify_token(token) == "alice"


def test_token_rejects_tampered_body():
    token = auth.create_token("alice")
    body, sig = token.split(".", 1)
    tampered = auth._b64(auth._unb64(body).replace(b"alice", b"bobby")) + "." + sig
    assert auth.verify_token(tampered) is None


def test_token_rejects_expired():
    old_ttl = auth.TOKEN_TTL
    auth.TOKEN_TTL = -1
    try:
        token = auth.create_token("alice")
    finally:
        auth.TOKEN_TTL = old_ttl
    time.sleep(0.01)
    assert auth.verify_token(token) is None


def test_token_rejects_garbage():
    assert auth.verify_token("not-a-real-token") is None
    assert auth.verify_token("") is None
