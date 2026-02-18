"""
Mock SkillCraft API connector.
Replace with real API integration when documentation is available.
"""

import random
from datetime import datetime


class SkillCraftService:
    """Mock service that simulates SkillCraft API responses."""

    async def get_test_status(self, skillcraft_user_id: str | None) -> dict:
        if not skillcraft_user_id:
            return {"status": "not_started", "score": None, "url": None}

        # Mock: simulate that user has taken the test
        return {
            "status": "completed",
            "score": round(random.uniform(40, 95), 1),
            "url": f"https://skillcraft.example.com/test/{skillcraft_user_id}",
        }

    async def start_test(self, beneficiary_id: str) -> dict:
        """Generate a SkillCraft user ID and test URL."""
        skillcraft_id = f"sc_{beneficiary_id[:8]}"
        return {
            "skillcraft_user_id": skillcraft_id,
            "test_url": f"https://skillcraft.example.com/test/{skillcraft_id}",
        }

    async def sync_score(self, skillcraft_user_id: str) -> dict:
        """Mock sync - in production, this would call the SkillCraft API."""
        score = round(random.uniform(40, 95), 1)
        return {
            "score": score,
            "synced_at": datetime.utcnow().isoformat(),
        }


skillcraft_service = SkillCraftService()
