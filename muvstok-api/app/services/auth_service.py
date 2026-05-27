from datetime import UTC, datetime, timedelta

from app.clients.keyvault_client import KeyVaultClient
from app.clients.muvstok_client import MuvstokClient
from app.core.config import Settings


class AuthService:
    def __init__(
        self,
        settings: Settings,
        keyvault_client: KeyVaultClient | None,
        muvstok_client: MuvstokClient,
    ) -> None:
        self._settings = settings
        self._keyvault_client = keyvault_client
        self._muvstok_client = muvstok_client

    async def get_token(self, *, force_refresh: bool = False) -> str:
        if not force_refresh and self._keyvault_client is not None:
            cached = await self._keyvault_client.get_secret(
                self._settings.key_vault_token_secret_name
            )
            if cached.strip():
                return cached.strip()

        username, password = await self._resolve_credentials()
        token = await self._muvstok_client.authenticate(username, password)
        if self._keyvault_client is not None:
            await self._keyvault_client.set_secret(
                self._settings.key_vault_token_secret_name,
                token,
            )
        return token

    async def _resolve_credentials(self) -> tuple[str, str]:
        user = self._settings.muvstok_user.strip()
        password = self._settings.muvstok_password
        if self._keyvault_client is not None:
            if not user:
                user = (
                    await self._keyvault_client.get_secret(
                        self._settings.key_vault_muvstok_user_secret_name
                    )
                ).strip()
            if not password:
                password = await self._keyvault_client.get_secret(
                    self._settings.key_vault_muvstok_password_secret_name
                )
        if not user or not password.strip():
            msg = (
                "API Diversos credentials are missing. Set MUVSTOK_USER/MUVSTOK_PASSWORD "
                "or Key Vault secrets muvstok-user / muvstok-password."
            )
            raise ValueError(msg)
        return user, password.strip()

    @staticmethod
    def token_expires_at(settings: Settings) -> datetime:
        return datetime.now(UTC) + timedelta(hours=settings.muvstok_token_ttl_hours)
