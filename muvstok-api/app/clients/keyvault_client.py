from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

from app.core.config import Settings


class KeyVaultClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._credential = DefaultAzureCredential()
        self._client = SecretClient(
            vault_url=settings.azure_key_vault_url, credential=self._credential
        )

    async def get_secret(self, name: str) -> str:
        secret = await self._client.get_secret(name)
        return secret.value or ""

    async def set_secret(self, name: str, value: str) -> None:
        await self._client.set_secret(name, value)

    async def close(self) -> None:
        await self._client.close()
        await self._credential.close()
