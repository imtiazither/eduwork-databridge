from typing import Annotated

from fastapi import Header, HTTPException

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.security.identity import Actor, DemoIdentityProvider
from eduwork_databridge.settings import get_settings

DemoUserHeader = Annotated[str | None, Header(alias="X-Demo-User")]


def get_actor(x_demo_user: DemoUserHeader = None) -> Actor:
    settings = get_settings()
    provider = DemoIdentityProvider(
        enabled=settings.demo_identity_enabled and settings.demo_mode,
        environment=settings.environment,
    )
    try:
        return provider.authenticate(x_demo_user)
    except ConnectorError as exc:
        raise HTTPException(status_code=401, detail=exc.safe_message) from exc
