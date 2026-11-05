"""Contract freeze: a missing or invalid credential is a 401 in strict mode."""

from __future__ import annotations

import inspect

from identity_access.interfaces.errors import AuthenticationRequiredError
from identity_access.interfaces.ports import PrincipalPort


def test_authentication_required_is_a_401_with_a_stable_code() -> None:
    error = AuthenticationRequiredError()

    assert error.status_code == 401
    assert error.code == "UNAUTHENTICATED"
    assert error.envelope("req_contract").code == "UNAUTHENTICATED"


def test_principal_port_declares_resolve_api_key() -> None:
    signature = inspect.signature(PrincipalPort.resolve)

    assert list(signature.parameters) == ["self", "api_key"]
