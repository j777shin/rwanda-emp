"""
SkillCraft psychometric assessment platform integration.
Connects to the SkillCraft API to manage user assessments and sync scores.
"""

import logging
from datetime import datetime

import httpx

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SkillCraftService:
    """Service that integrates with the SkillCraft psychometric assessment API."""

    def __init__(self):
        self.base_url = settings.skillcraft_api_url.rstrip("/")
        self.pilot_group = settings.skillcraft_pilot_group

    async def sign_in(self, email: str) -> dict:
        """Sign in (or auto-register) a user on SkillCraft.

        Returns {"access_token": str, "skillcraft_user_id": str} or
        {"error": str} on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/auth/signin",
                    json={
                        "identifier": email,
                        "identifierType": "email",
                        "identifierHash": "",
                        "authByReferral": False,
                        "phoneNumber": "",
                        "username": "",
                        "pilotGroup": self.pilot_group,
                    },
                )
                if response.status_code not in (200, 201):
                    logger.warning(
                        "SkillCraft sign-in failed: %s %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return {"error": f"Sign-in failed: {response.status_code}"}

                data = response.json()
                token = data.get("accessToken", "")

                # Fetch user profile to get the SkillCraft user ID
                user_resp = await client.get(
                    f"{self.base_url}/user",
                    headers={"Authorization": f"Bearer {token}"},
                )
                user_id = ""
                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    user_id = str(user_data.get("_id", ""))

                return {"access_token": token, "skillcraft_user_id": user_id}
        except httpx.RequestError as e:
            logger.warning("Could not connect to SkillCraft: %s", e)
            return {"error": f"Connection failed: {e}"}

    async def get_result(self, token: str) -> dict | None:
        """Fetch the user's latest result from SkillCraft.

        Returns the result dict (with 'finished' flag) or None on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/result",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code != 200:
                    logger.warning("SkillCraft /result failed: %s", response.status_code)
                    return None
                return response.json()
        except httpx.RequestError as e:
            logger.warning("Could not fetch SkillCraft result: %s", e)
            return None

    async def get_assessment(self, token: str) -> dict | None:
        """Fetch the user's primary assessment (computed scores).

        Returns the assessment dict or None on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/result/primary-assessment",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code != 200:
                    logger.warning(
                        "SkillCraft /result/primary-assessment failed: %s",
                        response.status_code,
                    )
                    return None
                return response.json()
        except httpx.RequestError as e:
            logger.warning("Could not fetch SkillCraft assessment: %s", e)
            return None

    def compute_score(self, assessment: dict) -> float | None:
        """Compute a single 0-100 score from the SkillCraft assessment.

        Averages non-null values within each category, then averages
        across categories.
        """
        if not assessment:
            return None

        category_scores = []

        # Cognitive (0-1 each)
        cognitive = assessment.get("cognitive") or {}
        cog_fields = ["memory", "adaptability", "attention", "problemSolving", "speed", "persistence"]
        cog_values = [cognitive[f] for f in cog_fields if cognitive.get(f) is not None]
        if cog_values:
            category_scores.append(sum(cog_values) / len(cog_values))

        # Behavior (0-1 each, skip riskBehavior which is a string)
        behavior = assessment.get("behavior") or {}
        beh_fields = ["proactivity", "growthMindset"]
        beh_values = [behavior[f] for f in beh_fields if behavior.get(f) is not None and isinstance(behavior.get(f), (int, float))]
        if beh_values:
            category_scores.append(sum(beh_values) / len(beh_values))

        # Emotional Intelligence (0-1 each)
        ei = assessment.get("emotionalIntelligence") or {}
        ei_fields = ["empathy", "selfAwareness", "selfManagement", "socialAwareness"]
        ei_values = [ei[f] for f in ei_fields if ei.get(f) is not None]
        if ei_values:
            category_scores.append(sum(ei_values) / len(ei_values))

        # Personality / Big Five (0-1 each)
        personality = assessment.get("personality") or {}
        per_fields = ["conscientiousness", "emotionalStability", "extraversion", "agreeableness", "openness"]
        per_values = [personality[f] for f in per_fields if personality.get(f) is not None]
        if per_values:
            category_scores.append(sum(per_values) / len(per_values))

        if not category_scores:
            return None

        return round((sum(category_scores) / len(category_scores)) * 100, 2)

    async def get_test_status(self, email: str) -> dict:
        """Get the full test status for a user by email.

        Signs in, checks if finished, and fetches assessment if available.
        """
        sign_in_result = await self.sign_in(email)
        if "error" in sign_in_result:
            return {
                "status": "error",
                "score": None,
                "finished": False,
                "assessment": None,
                "url": f"https://skillcraft.app/{self.pilot_group}",
                "error": sign_in_result["error"],
            }

        token = sign_in_result["access_token"]
        result = await self.get_result(token)

        finished = False
        if result:
            finished = result.get("finished", False)

        assessment = None
        score = None
        if finished:
            assessment = await self.get_assessment(token)
            score = self.compute_score(assessment)

        return {
            "status": "completed" if finished else "in_progress",
            "score": score,
            "finished": finished,
            "assessment": assessment,
            "url": f"https://skillcraft.app/{self.pilot_group}",
        }

    async def sync_score(self, email: str) -> dict:
        """Sign in, fetch assessment, compute and return score."""
        sign_in_result = await self.sign_in(email)
        if "error" in sign_in_result:
            return {"error": sign_in_result["error"]}

        token = sign_in_result["access_token"]
        result = await self.get_result(token)

        if not result or not result.get("finished"):
            return {
                "score": None,
                "finished": False,
                "synced_at": datetime.utcnow().isoformat(),
            }

        assessment = await self.get_assessment(token)
        score = self.compute_score(assessment)

        return {
            "score": score,
            "finished": True,
            "synced_at": datetime.utcnow().isoformat(),
        }


skillcraft_service = SkillCraftService()
