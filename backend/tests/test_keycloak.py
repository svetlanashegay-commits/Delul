import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from app.core import deps
from app.core.security import KeycloakVerifier, identity_from_claims
from app.models import User
from app.services.errors import ForbiddenError, ServiceUnavailableError, UnauthorizedError

ISSUER = "http://localhost:8080/realms/delul"


@pytest.fixture(scope="module")
def keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key()


@pytest.fixture
def signer(keys):
    private, public = keys
    claims = {
        "iss": ISSUER,
        "aud": "delul-api",
        "sub": str(uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "typ": "Bearer",
        "email": "sso@example.com",
        "name": "SSO Student",
        "group_name": "CS-1",
        "realm_access": {"roles": ["student"]},
    }
    verifier = KeycloakVerifier(ISSUER, ISSUER + "/protocol/openid-connect/certs", "delul-api")
    verifier._jwks = SimpleNamespace(
        get_signing_key_from_jwt=Mock(return_value=SimpleNamespace(key=public))
    )

    def encode(changes=None, remove=()):
        data = {**claims, **(changes or {})}
        for field in remove:
            data.pop(field, None)
        return jwt.encode(data, private, algorithm="RS256", headers={"kid": "test-key"})

    return claims, verifier, encode


def test_signed_access_token_and_role_priority(signer):
    _, verifier, encode = signer
    identity = identity_from_claims(verifier.verify(encode()))
    assert identity.role == "student" and identity.group_name == "CS-1"
    identity = identity_from_claims(
        verifier.verify(
            encode(
                {
                    "realm_access": {"roles": ["student", "teacher", "admin", "offline_access"]},
                }
            )
        )
    )
    assert identity.role == "admin"


@pytest.mark.parametrize(
    "changes",
    [
        {"aud": "another-api"},
        {"iss": "https://untrusted.example/realm"},
        {"exp": int(time.time()) - 1},
        {"iat": int(time.time()) + 3600},
        {"typ": "ID"},
    ],
)
def test_invalid_access_claims_are_rejected(signer, changes):
    _, verifier, encode = signer
    with pytest.raises(UnauthorizedError):
        verifier.verify(encode(changes))


@pytest.mark.parametrize("field", ["exp", "iat", "iss", "sub", "aud"])
def test_required_claims_cannot_be_omitted(signer, field):
    _, verifier, encode = signer
    with pytest.raises(UnauthorizedError):
        verifier.verify(encode(remove=[field]))


def test_unsigned_hmac_and_wrong_rsa_signature_are_rejected(signer):
    claims, verifier, _ = signer
    for algorithm, key in [("none", None), ("HS256", "x" * 64)]:
        token = jwt.encode(claims, key, algorithm=algorithm)
        with pytest.raises(UnauthorizedError):
            verifier.verify(token)
    verifier._jwks.get_signing_key_from_jwt.assert_not_called()
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(UnauthorizedError):
        verifier.verify(jwt.encode(claims, wrong, algorithm="RS256", headers={"kid": "test-key"}))


def test_unknown_or_malformed_roles_are_forbidden(signer):
    _, verifier, encode = signer
    for roles in [["offline_access"], "admin", [1]]:
        with pytest.raises(ForbiddenError):
            identity_from_claims(verifier.verify(encode({"realm_access": {"roles": roles}})))


def test_real_jwks_client_caches_signing_keys(keys, signer, monkeypatch):
    _, public = keys
    _, _, encode = signer
    key = jwt.algorithms.RSAAlgorithm.to_jwk(public, as_dict=True)
    key.update(kid="test-key", use="sig", alg="RS256")
    fetch = Mock(return_value={"keys": [key]})
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fetch)
    verifier = KeycloakVerifier(ISSUER, ISSUER + "/certs", "delul-api")
    assert verifier.verify(encode())["aud"] == "delul-api"
    assert verifier.verify(encode())["aud"] == "delul-api"
    assert fetch.call_count == 1


def test_jwks_outage_is_not_reported_as_success(signer):
    _, verifier, encode = signer
    verifier._jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError(
        "network details"
    )
    with pytest.raises(ServiceUnavailableError, match="public keys are unavailable"):
        verifier.verify(encode())


@pytest.fixture
def sso(demo, signer, monkeypatch):
    client, db, config = demo
    _, verifier, encode = signer
    from app.main import app
    app.dependency_overrides.pop(deps.get_current_user, None)
    config.auth_mode = "keycloak"
    monkeypatch.setattr(deps, "get_keycloak_verifier", lambda: verifier)
    return client, db, encode


def test_bearer_creates_stable_profile_without_password(sso):
    client, db, encode = sso
    headers = {"Authorization": "Bearer " + encode()}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    user_id = response.json()["id"]
    assert "password" not in response.text
    assert client.get("/api/auth/me", headers=headers).json()["id"] == user_id
    local = db.scalar(select(User).where(User.email == "sso@example.com"))
    assert not hasattr(local, "password_hash") and local.keycloak_issuer == ISSUER
    assert client.get("/api/users", headers=headers).status_code == 403
    assert client.get("/api/quizzes").status_code == 401  # Demo identity is not a fallback.
    assert (
        client.post(
            "/api/auth/session", json={"email": "student@demo.kz", "password": "ignored"}
        ).status_code
        == 404
    )


def test_email_collision_never_links_an_existing_account(sso):
    client, db, encode = sso
    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer "
            + encode(
                {
                    "email": "teacher@demo.kz",
                    "realm_access": {"roles": ["teacher"]},
                }
            )
        },
    )
    assert response.status_code == 409
    teacher = db.scalar(select(User).where(User.email == "teacher@demo.kz"))
    assert teacher.keycloak_id == "8cbdda86-8d0c-52a8-a00a-5fdf8bad7829"




def test_realm_defaults_pkce_audience_and_local_demo_accounts():
    root = Path(__file__).resolve().parents[2]
    realm = json.loads((root / "keycloak/realm-delul.json").read_text(encoding="utf-8"))
    assert realm["realm"] == "delul" and realm["accessTokenLifespan"] == 300
    assert realm["registrationAllowed"] and realm["registrationEmailAsUsername"]
    defaults = set(realm["defaultRole"]["composites"]["realm"])
    assert defaults == {"student", "offline_access", "uma_authorization"}
    client = realm["clients"][0]
    assert client["clientId"] == "delul-web" and client["publicClient"] and "secret" not in client
    assert client["standardFlowEnabled"] and not client["directAccessGrantsEnabled"]
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    audience = next(
        m for m in client["protocolMappers"] if m["protocolMapper"] == "oidc-audience-mapper"
    )
    assert audience["config"]["included.custom.audience"] == "delul-api"
    assert audience["config"]["access.token.claim"] == "true"
    assert audience["config"]["id.token.claim"] == "false"
    assert {u["email"] for u in realm["users"]} == {
        "student@demo.kz",
        "teacher@demo.kz",
        "admin@demo.kz",
    }
    assert not (root / "keycloak/realm-quizai.json").exists()


@pytest.mark.parametrize("changes", [
    {"iss": "https://foreign.invalid/realm"},
    {"aud": "foreign-api"},
    {"exp": 1},
])
def test_api_rejects_invalid_claims(sso, changes):
    client, _, encode = sso
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + encode(changes)}).status_code == 401


def test_api_rejects_missing_garbage_role_and_old_password_routes(sso):
    client, _, encode = sso
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + encode({"realm_access": {"roles": []}})}).status_code == 403
    for route in ["register", "login", "session", "logout"]:
        assert client.post("/api/auth/" + route, json={}).status_code == 404


def test_api_key_outage_returns_503(sso, signer):
    client, _, encode = sso
    _, verifier, _ = signer
    verifier._jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError("offline")
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + encode()}).status_code == 503
