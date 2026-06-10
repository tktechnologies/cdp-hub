"""Database repositories."""

from app.repositories.company_location_repository import CompanyLocationRepository
from app.repositories.muvstok_api_data_repository import MuvstokApiDataRepository

__all__ = ["CompanyLocationRepository", "MuvstokApiDataRepository"]
