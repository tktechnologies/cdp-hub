from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CompanyLocation
from app.services.dealership_directory import normalize_dealership_id

COMPANY_LOCATION_FIELDS = (
    "id_empresa",
    "id_grupoempresa",
    "projeto",
    "montadora",
    "nm_corporacao",
    "grupo_empresa",
    "cnpj",
    "nome_fantasia",
    "apelido",
    "cep",
    "endereco",
    "numero",
    "uf",
    "cidade",
    "bairro",
)


class CompanyLocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(CompanyLocation))
        return int(result.scalar_one())

    async def get_by_id_empresa(self, id_empresa: Any) -> CompanyLocation | None:
        key = normalize_dealership_id(id_empresa)
        if not key:
            return None
        result = await self._session.execute(
            select(CompanyLocation).where(CompanyLocation.id_empresa == key)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[CompanyLocation]:
        result = await self._session.execute(
            select(CompanyLocation).order_by(CompanyLocation.id_empresa)
        )
        return list(result.scalars().all())

    async def upsert_many(self, records: Iterable[dict[str, Any]]) -> int:
        count = 0
        for raw in records:
            values = self._clean_record(raw)
            if not values["id_empresa"]:
                continue
            existing = await self.get_by_id_empresa(values["id_empresa"])
            if existing is None:
                self._session.add(CompanyLocation(**values))
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
            count += 1
        await self._session.flush()
        return count

    @staticmethod
    def _clean_record(record: dict[str, Any]) -> dict[str, str]:
        values = {field: str(record.get(field) or "").strip() for field in COMPANY_LOCATION_FIELDS}
        values["id_empresa"] = normalize_dealership_id(values["id_empresa"])
        values["cnpj"] = "".join(ch for ch in values["cnpj"] if ch.isdigit())
        if len(values["cnpj"]) != 14:
            values["cnpj"] = ""
        values["uf"] = values["uf"].upper()[:2] if len(values["uf"].strip()) >= 2 else ""
        return values
