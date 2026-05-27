"""Create database schema manually"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.database import init_db

if __name__ == "__main__":
    print("Creating database schema...")
    asyncio.run(init_db())
    print("Schema created successfully!")
