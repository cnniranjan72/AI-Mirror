"""Embeddings now call Hugging Face's hosted Inference API instead of
loading sentence-transformers in-process — same model, same 384 dims, just
a different transport. No live DB or network needed; the HTTP call itself
is mocked.
"""
import pytest

from app.services import embedding


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeAsyncClient.last_call = {"url": url, "headers": headers, "json": json}
        n = len(json["inputs"])
        return _FakeResponse([[0.1] * 384 for _ in range(n)])


@pytest.mark.asyncio
async def test_encode_batch_returns_384_dim_vectors(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "hf_fake_token")
    monkeypatch.setattr(embedding.httpx, "AsyncClient", _FakeAsyncClient)

    vectors = await embedding.encode_batch(["hello world", "second text"])
    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)
    assert _FakeAsyncClient.last_call["headers"]["Authorization"] == "Bearer hf_fake_token"


@pytest.mark.asyncio
async def test_encode_single_delegates_to_batch(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "hf_fake_token")
    monkeypatch.setattr(embedding.httpx, "AsyncClient", _FakeAsyncClient)

    vector = await embedding.encode("hello world")
    assert len(vector) == 384


@pytest.mark.asyncio
async def test_encode_batch_requires_token(monkeypatch):
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="HF_API_TOKEN"):
        await embedding.encode_batch(["hello"])
