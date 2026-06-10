"""Production test SKU pool — random sample of 5 per audit run.

Pool = meeting batch SKUs + known production smoke SKUs. Each run picks 5
without replacement (same draw can repeat on a later run, but is unlikely).
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any

ACTIVE_SITES = ("gm", "ml", "vw", "eu", "pecadireta", "melibox")

# Meeting / operator SKU set (scripts/archive/batch_meeting_skus.py)
_MEETING_SKUS: tuple[tuple[str, str], ...] = (
    ("60910T14M00ZZ", ""),
    ("661003M6M00ZZ", ""),
    ("621003M6M00ZZ", ""),
    ("767203M6M01", ""),
    ("846403M6M01ZA", ""),
    ("793251Y000", ""),
    ("53486204", ""),
    ("84035768", ""),
    ("8.77E+15", ""),
    ("52274186", ""),
    ("51789373", ""),
    ("52063874", ""),
    ("631008317R", ""),
    ("52200024", ""),
    ("K8EP17LR0A", ""),
    ("868857LR8A", ""),
    ("868847LR8A", ""),
    ("D3BB/ 15B200/AA/5UA", ""),
    ("C1BB/ 15A222/DA/5YZ", ""),
    ("04601T7TM00ZZ", ""),
)

# Known-good production smoke SKUs (scripts/production_scraper_curl_smoke.py + audits)
_SMOKE_SKUS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("22781768", "GM", ("gm",)),
    ("93240598", "GM", ("gm",)),
    ("51766536", "", ("ml",)),
    ("06K907811B", "", ("ml",)),
    ("5U6867287Y20", "VW", ("vw",)),
    ("06K907811B", "VW", ("eu",)),
    ("06K907811B", "", ("pecadireta",)),
)


@dataclass(frozen=True)
class PoolEntry:
    sku: str
    brand: str = ""
    preferred_sites: tuple[str, ...] | None = None


def _build_pool() -> list[PoolEntry]:
    seen: set[str] = set()
    pool: list[PoolEntry] = []

    def add(sku: str, brand: str = "", preferred_sites: tuple[str, ...] | None = None) -> None:
        key = sku.strip().upper()
        if not key or key in seen:
            return
        seen.add(key)
        pool.append(PoolEntry(sku=sku.strip(), brand=brand, preferred_sites=preferred_sites))

    for sku, brand, sites in _SMOKE_SKUS:
        add(sku, brand, sites)
    for sku, brand in _MEETING_SKUS:
        add(sku, brand)

    return pool


FULL_POOL: list[PoolEntry] = _build_pool()


def resolve_seed(seed: int | str | None = None) -> int | None:
    if seed is not None:
        return int(seed)
    raw = os.environ.get("PRODUCTION_TEST_SKU_SEED", "").strip()
    return int(raw) if raw else None


def sample_cases(
    count: int = 5,
    *,
    seed: int | str | None = None,
    one_site_per_sku: bool = True,
    batch_sites: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Return `count` random cases as dicts: id, sku, brand, sites."""
    rng = random.Random(resolve_seed(seed))
    n = min(count, len(FULL_POOL))
    picked = rng.sample(FULL_POOL, n)

    cases: list[dict[str, Any]] = []
    for entry in picked:
        if one_site_per_sku:
            if entry.preferred_sites:
                sites = [entry.preferred_sites[0]]
            else:
                sites = [rng.choice(ACTIVE_SITES)]
        else:
            sites = list(batch_sites or ACTIVE_SITES)

        safe_id = "".join(c if c.isalnum() else "-" for c in entry.sku)[:40].strip("-")
        cases.append(
            {
                "id": f"rand-{safe_id}",
                "sku": entry.sku,
                "brand": entry.brand,
                "sites": sites,
            }
        )
    return cases


def sample_batch_job_items(
    count: int = 5,
    *,
    seed: int | str | None = None,
    sites: tuple[str, ...] | None = None,
) -> tuple[list[dict[str, str]], list[str], list[dict[str, Any]]]:
    """Items for POST /jobs plus site list and case metadata for reports."""
    cases = sample_cases(count, seed=seed, one_site_per_sku=False, batch_sites=sites)
    job_sites = list(sites or ("gm", "pecadireta", "melibox"))
    items = [{"sku": c["sku"], "brand": c["brand"]} for c in cases]
    return items, job_sites, cases
