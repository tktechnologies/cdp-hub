"""Dealership location enrichment for API Diversos demand rows."""

from __future__ import annotations

import csv
import io
import logging
import re
import time
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger("muvstok.dealership_directory")


@dataclass(frozen=True, slots=True)
class DealershipInfo:
    id_empresa: str
    id_grupoempresa: str = ""
    projeto: str = ""
    montadora: str = ""
    nm_corporacao: str = ""
    uf: str = ""
    cnpj: str = ""
    nome_fantasia: str = ""
    apelido: str = ""
    grupo_empresa: str = ""
    cidade: str = ""
    bairro: str = ""
    endereco: str = ""
    numero: str = ""
    cep: str = ""

    @property
    def company_label(self) -> str:
        return self.nome_fantasia or self.grupo_empresa or self.apelido

    @property
    def branch_label(self) -> str:
        return self.apelido or self.nome_fantasia or self.grupo_empresa


class CompanyLocationReader(Protocol):
    async def list_all(self) -> list[Any]:
        """Return persisted company-location rows."""
        ...


def normalize_dealership_id(value: Any) -> str:
    """Normalize Google Sheets numeric IDs and upstream filial codes to comparable text."""
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.replace(",", ".")
    try:
        number = Decimal(normalized)
    except InvalidOperation:
        return re.sub(r"\D", "", text)
    if number == number.to_integral_value():
        return str(int(number))
    return re.sub(r"\D", "", text)


def _norm_key(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _name_key(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"^solicitou cancelamento\s*-\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _pick(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _values(row: dict[str, Any], *keys: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        value = row.get(key)
        text = str(value).strip() if value is not None else ""
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out


def _normalize_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) == 14 else ""


def _normalize_uf(value: str) -> str:
    text = str(value or "").strip().upper()
    return text if re.fullmatch(r"[A-Z]{2}", text) else ""


class DealershipDirectory:
    """Cached lookup from Muvstok `codigoFilial` to dealership metadata."""

    def __init__(
        self,
        settings: Settings,
        company_locations: CompanyLocationReader | None = None,
    ) -> None:
        self._settings = settings
        self._company_locations = company_locations
        self._cache: dict[str, DealershipInfo] = {}
        self._name_cache: dict[str, DealershipInfo] = {}
        self._loaded_at = 0.0

    async def get(self, codigo_filial: Any) -> DealershipInfo | None:
        key = normalize_dealership_id(codigo_filial)
        if not key:
            return None
        directory = await self._load()
        return directory.get(key)

    async def get_by_name(self, *names: Any) -> DealershipInfo | None:
        await self._load()
        for name in names:
            key = _name_key(name)
            if key and key in self._name_cache:
                return self._name_cache[key]
        return None

    async def enrich_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self._settings.muvstok_dealership_directory_enabled:
            return rows
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(await self.enrich_row(row))
        return out

    async def enrich_row(self, row: dict[str, Any]) -> dict[str, Any]:
        codigo_filial = _pick(
            row,
            "codigoFilial",
            "codigo_filial",
            "codigoEmpresa",
            "codigo_empresa",
            "id_empresa",
            "idEmpresa",
        )
        info = await self.get(codigo_filial)
        if info is None:
            info = await self.get_by_name(
                *_values(
                    row,
                    "nomeFilial",
                    "nomefilial",
                    "branch_name",
                    "apelidoFilial",
                    "apelidofilial",
                    "vendedor",
                    "seller",
                    "nome_fantasia",
                    "nomeFantasia",
                    "apelido",
                )
            )
        if info is None:
            return row

        enriched = dict(row)
        if not _pick(enriched, "id_empresa", "idEmpresa"):
            enriched["id_empresa"] = info.id_empresa
        if not _pick(enriched, "uf", "UF", "seller_uf", "ufFilial"):
            enriched["uf"] = info.uf
        if not _pick(enriched, "cnpj", "CNPJ", "seller_cnpj", "cnpjFilial", "cnpjEmpresa"):
            enriched["cnpj"] = info.cnpj
        if not _pick(enriched, "empresa", "nomeEmpresa", "razaoSocial", "company_name"):
            enriched["empresa"] = info.company_label
        if not _pick(enriched, "nomeFilial", "nomefilial", "branch_name", "apelidoFilial"):
            enriched["nomeFilial"] = info.branch_label
        if not _pick(enriched, "cidade", "municipio"):
            enriched["cidade"] = info.cidade
        if not _pick(enriched, "bairro"):
            enriched["bairro"] = info.bairro
        if not _pick(enriched, "endereco", "endereço"):
            enriched["endereco"] = info.endereco
        return enriched

    async def _load(self) -> dict[str, DealershipInfo]:
        ttl = max(60, int(self._settings.muvstok_dealership_directory_ttl_seconds))
        if self._cache and time.monotonic() - self._loaded_at < ttl:
            return self._cache
        if self._company_locations is not None:
            try:
                rows = await self._company_locations.list_all()
                self._set_cache(
                    {
                        info.id_empresa: info
                        for row in rows
                        if (info := dealership_info_from_company_location(row)).id_empresa
                    }
                )
                logger.info(
                    "dealership_directory_db_loaded",
                    extra={"row_count": len(self._cache)},
                )
                if (
                    self._cache
                    or not self._settings.muvstok_dealership_directory_url_fallback_enabled
                ):
                    return self._cache
            except Exception as exc:
                logger.warning("dealership_directory_db_load_failed", extra={"error": str(exc)})
                self._loaded_at = time.monotonic()
                if not self._settings.muvstok_dealership_directory_url_fallback_enabled:
                    return self._cache
        url = self._settings.muvstok_dealership_directory_url.strip()
        if not url:
            self._set_cache({})
            return self._cache
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.muvstok_timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
            self._set_cache(parse_dealership_csv(response.text))
            logger.info("dealership_directory_loaded", extra={"row_count": len(self._cache)})
        except Exception as exc:
            logger.warning("dealership_directory_load_failed", extra={"error": str(exc)})
            self._loaded_at = time.monotonic()
        return self._cache

    def _set_cache(self, directory: dict[str, DealershipInfo]) -> None:
        self._cache = directory
        self._name_cache = _index_dealership_names(directory.values())
        self._loaded_at = time.monotonic()


def parse_dealership_csv(text: str) -> dict[str, DealershipInfo]:
    out: dict[str, DealershipInfo] = {}
    for record in parse_company_location_csv(text):
        info = DealershipInfo(**record)
        out[info.id_empresa] = info
    return out


def _index_dealership_names(infos: Iterable[DealershipInfo]) -> dict[str, DealershipInfo]:
    index: dict[str, DealershipInfo] = {}
    ambiguous: set[str] = set()
    for info in infos:
        for name in (
            info.branch_label,
            info.nome_fantasia,
            info.apelido,
        ):
            key = _name_key(name)
            if not key:
                continue
            existing = index.get(key)
            if existing is not None and existing.id_empresa != info.id_empresa:
                ambiguous.add(key)
                continue
            if key not in ambiguous:
                index[key] = info
    for key in ambiguous:
        index.pop(key, None)
    return index


def parse_company_location_csv(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    records: list[dict[str, str]] = []
    for raw in reader:
        row = {_norm_key(k): (v or "").strip() for k, v in raw.items() if k is not None}
        key = normalize_dealership_id(row.get("id_empresa"))
        if not key:
            continue
        records.append(
            {
                "id_empresa": key,
                "id_grupoempresa": normalize_dealership_id(row.get("id_grupoempresa")),
                "projeto": row.get("projeto", ""),
                "montadora": row.get("montadora", ""),
                "nm_corporacao": row.get("nm_corporacao", ""),
                "grupo_empresa": row.get("grupo_empresa", ""),
                "cnpj": _normalize_cnpj(row.get("cnpj", "")),
                "nome_fantasia": row.get("nome_fantasia", ""),
                "apelido": row.get("apelido", ""),
                "cep": row.get("cep", ""),
                "endereco": row.get("endereco", ""),
                "numero": row.get("numero", ""),
                "uf": _normalize_uf(row.get("uf", "")),
                "cidade": row.get("cidade", ""),
                "bairro": row.get("bairro", ""),
            }
        )
    return records


def dealership_info_from_company_location(row: Any) -> DealershipInfo:
    def value(name: str) -> str:
        return str(getattr(row, name, "") or "").strip()

    return DealershipInfo(
        id_empresa=normalize_dealership_id(value("id_empresa")),
        id_grupoempresa=normalize_dealership_id(value("id_grupoempresa")),
        projeto=value("projeto"),
        montadora=value("montadora"),
        nm_corporacao=value("nm_corporacao"),
        uf=_normalize_uf(value("uf")),
        cnpj=_normalize_cnpj(value("cnpj")),
        nome_fantasia=value("nome_fantasia"),
        apelido=value("apelido"),
        grupo_empresa=value("grupo_empresa"),
        cidade=value("cidade"),
        bairro=value("bairro"),
        endereco=value("endereco"),
        numero=value("numero"),
        cep=value("cep"),
    )
