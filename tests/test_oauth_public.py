"""Consent and durable OAuth use generated local secrets and synthetic clients."""

import base64
import hashlib
import secrets

import pytest
from mcp.server.auth.provider import AuthorizationParams, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from investmcp import consent_gate
from investmcp.oauth_provider import PersonalOAuthProvider


async def test_consent_pkce_durable_tokens_rotation_and_revocation(
    tmp_path, monkeypatch
):
    approval = secrets.token_urlsafe(32)
    monkeypatch.setenv(
        "MCP_OAUTH_APPROVAL_HASH", consent_gate.hash_passphrase(approval)
    )
    monkeypatch.setenv("CONSENT_GATE_REDIRECT_ORIGINS", '["https://example.com"]')
    monkeypatch.setattr(consent_gate, "_GATE", consent_gate.ConsentGate())
    provider = PersonalOAuthProvider(
        None,
        None,
        state_path=tmp_path / "oauth.sqlite3",
        resource_url="https://example.com",
    )
    client = OAuthClientInformationFull(
        client_id="synthetic-client",
        client_name="Synthetic",
        redirect_uris=[AnyUrl("https://example.com/callback")],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
        scope="read",
    )
    await provider.register_client(client)
    verifier = secrets.token_urlsafe(32)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    params = AuthorizationParams(
        redirect_uri=AnyUrl("https://example.com/callback"),
        redirect_uri_provided_explicitly=True,
        code_challenge=challenge,
        state="synthetic-state",
        scopes=["read"],
        resource="https://example.com/",
    )
    with pytest.raises(TokenError):
        await provider.authorize(client, params)
    cookie = secrets.token_urlsafe(32)
    nonce = await provider.begin_consent(client, params, cookie)
    code, _ = await provider.complete_consent(
        nonce, approval, cookie, params, client.client_id
    )
    authorization = await provider.load_authorization_code(client, code)
    assert authorization.code_challenge == challenge
    token = await provider.exchange_authorization_code(client, authorization)
    persisted = PersonalOAuthProvider(
        None,
        None,
        state_path=tmp_path / "oauth.sqlite3",
        resource_url="https://example.com",
    )
    assert await persisted.load_access_token(token.access_token) is not None
    assert token.access_token.encode() not in (tmp_path / "oauth.sqlite3").read_bytes()
    refresh = await persisted.load_refresh_token(client, token.refresh_token)
    rotated = await persisted.exchange_refresh_token(client, refresh, ["read"])
    access = await persisted.load_access_token(rotated.access_token)
    assert access is not None
    await persisted.revoke_token(access)
    assert await persisted.load_access_token(rotated.access_token) is None
