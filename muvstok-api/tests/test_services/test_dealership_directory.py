from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.dealership_directory import (
    DealershipDirectory,
    normalize_dealership_id,
    parse_dealership_csv,
)


def test_normalize_dealership_id_handles_sheet_numbers() -> None:
    assert normalize_dealership_id("917.0") == "917"
    assert normalize_dealership_id(" 005 ") == "5"
    assert normalize_dealership_id("id 123") == "123"


def test_parse_dealership_csv_indexes_id_empresa() -> None:
    directory = parse_dealership_csv(
        "id_grupoempresa,id_empresa,grupo_empresa,cnpj,nome_fantasia,apelido,Uf,Cidade,Bairro\n"
        "277,917,AZZURRA JEEP,68743038000864,AZZURRA JEEP BOTAFOGO,JEEP BOTAFOGO,RJ,Rio de Janeiro,Botafogo\n"
    )

    info = directory["917"]
    assert info.uf == "RJ"
    assert info.cnpj == "68743038000864"
    assert info.company_label == "AZZURRA JEEP BOTAFOGO"


@pytest.mark.asyncio
async def test_enrich_row_from_codigo_filial() -> None:
    settings = Settings(muvstok_dealership_directory_enabled=True)
    directory = DealershipDirectory(settings)
    directory._cache = parse_dealership_csv(  # noqa: SLF001 - targeted cache fixture
        "id_empresa,grupo_empresa,cnpj,nome_fantasia,apelido,Uf,Cidade,Bairro,Endereco\n"
        "917,AZZURRA JEEP,68743038000864,AZZURRA JEEP BOTAFOGO,JEEP BOTAFOGO,RJ,Rio de Janeiro,Botafogo,Rua General Polidoro\n"
    )
    directory._loaded_at = 10**9  # noqa: SLF001 - keep test cache hot

    row = await directory.enrich_row(
        {"codigoFilial": "917.0", "nomeFilial": "Original Branch", "valorPrecoVenda": 10}
    )

    assert row["uf"] == "RJ"
    assert row["cnpj"] == "68743038000864"
    assert row["empresa"] == "AZZURRA JEEP BOTAFOGO"
    assert row["nomeFilial"] == "Original Branch"
