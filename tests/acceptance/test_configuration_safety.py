"""Fail-closed production configuration and diagnostic redaction acceptance."""
import pytest
from pydantic import ValidationError
from app.config import Settings


@pytest.mark.parametrize("values", [
    {"env":"production","dev_auth":True},
    {"env":"production","database_url":"sqlite:///:memory:"},
    {"allowed_origins":["*"]},
    {"trusted_hosts":["*"]},
    {"stale_after_seconds":600,"offline_after_seconds":120},
])
def test_unsafe_configuration_is_rejected(values):
    with pytest.raises(ValidationError):
        Settings(**values)


@pytest.mark.parametrize("field,marker", [("admin_password","QA_BOOT_SECRET"),("adapter_token","QA_ADAPTER_SECRET")])
def test_boot_validation_errors_do_not_echo_raw_secrets(field, marker):
    with pytest.raises(ValidationError) as exc:
        Settings(**{field:marker})
    assert marker not in str(exc.value), "Settings startup diagnostics must not print raw credentials"
