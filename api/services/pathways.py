"""
Pathways (wb-e-learning) integration service.
Connects to the Strapi-based e-learning platform to retrieve course progress.
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.beneficiary import Beneficiary
from models.user import User

settings = get_settings()
logger = logging.getLogger(__name__)

# Cache for paths data (rarely changes)
_paths_cache: list[dict] | None = None
_paths_cache_time: datetime | None = None
CACHE_TTL_SECONDS = 300  # 5 minutes


class PathwaysService:
    """Service that integrates with the Strapi wb-e-learning platform."""

    def __init__(self):
        self.base_url = settings.pathways_api_url.rstrip("/")

    async def _fetch_paths(self) -> list[dict]:
        """Fetch all pathways with their courses from Strapi. Cached for 5 minutes."""
        global _paths_cache, _paths_cache_time

        if (
            _paths_cache is not None
            and _paths_cache_time is not None
            and (datetime.utcnow() - _paths_cache_time).total_seconds() < CACHE_TTL_SECONDS
        ):
            return _paths_cache

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/paths")
                if response.status_code != 200:
                    logger.warning("Failed to fetch paths from Strapi: %s %s", response.status_code, response.text[:200])
                    return _paths_cache or []
                try:
                    paths = response.json()
                except Exception:
                    logger.warning("Strapi /paths returned non-JSON response")
                    return _paths_cache or []
                if not isinstance(paths, list):
                    logger.warning("Strapi /paths returned unexpected type: %s", type(paths))
                    return _paths_cache or []
                _paths_cache = paths
                _paths_cache_time = datetime.utcnow()
                return paths
        except httpx.RequestError as e:
            logger.warning("Could not connect to Strapi: %s", e)
            return _paths_cache or []

    def _compute_completion_rate(self, progress_json: dict, paths: list[dict]) -> float:
        """Compute completion rate from progressJson and paths data.

        Matches the analytics logic in wb-e-learning:
        - Count total courses across all pathways
        - Count entries with dataLevel == "completedCourse" in progressJson
        - Rate = (completed / total) * 100
        """
        if not progress_json or not paths:
            return 0.0

        total_courses = 0
        for path in paths:
            courses = path.get("courses") or []
            total_courses += len(courses)

        if total_courses == 0:
            return 0.0

        completed_courses = 0
        for pathway_id, entries in progress_json.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and entry.get("dataLevel") == "completedCourse":
                    completed_courses += 1

        return round((completed_courses / total_courses) * 100, 2)

    def _compute_course_progress(self, progress_json: dict, paths: list[dict]) -> dict:
        """Compute per-course completion from progressJson and paths data.

        Returns dict keyed by pathway_id with course-level completion info.
        """
        # Build set of completed course IDs from progressJson
        completed_course_ids = set()
        for pathway_id, entries in (progress_json or {}).items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and entry.get("dataLevel") == "completedCourse":
                    completed_course_ids.add(str(entry.get("id", "")))

        result = {}
        for path in paths:
            path_id = str(path.get("id", ""))
            courses_data = {}
            for course in (path.get("courses") or []):
                course_id = str(course.get("id", ""))
                courses_data[course_id] = {
                    "course_name": course.get("name", ""),
                    "order_number": course.get("orderNumber", 0),
                    "completed": course_id in completed_course_ids,
                }
            result[path_id] = {
                "pathway_name": path.get("name", ""),
                "order_number": path.get("orderNumber", 0),
                "courses": courses_data,
            }
        return result

    def _count_modules(self, progress_json: dict) -> dict:
        """Count completed courses and pathways from progressJson."""
        completed_courses = 0
        completed_pathways = 0

        if not progress_json:
            return {"completed_courses": 0, "completed_pathways": 0}

        for pathway_id, entries in progress_json.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                dl = entry.get("dataLevel")
                if dl == "completedCourse":
                    completed_courses += 1
                elif dl == "completedPathway":
                    completed_pathways += 1

        return {
            "completed_courses": completed_courses,
            "completed_pathways": completed_pathways,
        }

    async def get_progress(self, email: str | None) -> dict:
        """Get a user's learning progress from Strapi by email."""
        if not email:
            return {"status": "not_enrolled", "completion_rate": 0, "url": None}

        paths = await self._fetch_paths()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Strapi users have username set to email
                response = await client.get(
                    f"{self.base_url}/users",
                    params={"username": email},
                )
                if response.status_code != 200:
                    logger.warning("Failed to fetch user from Strapi: %s", response.status_code)
                    return self._mock_progress()

                try:
                    users = response.json()
                except Exception:
                    logger.warning("Strapi /users returned non-JSON response")
                    return self._mock_progress()
                if not users:
                    return {"status": "not_enrolled", "completion_rate": 0, "url": None}

                strapi_user = users[0] if isinstance(users, list) else users
                progress_json = strapi_user.get("progressJson") or {}
                completion_rate = self._compute_completion_rate(progress_json, paths)
                modules = self._count_modules(progress_json)
                course_progress = self._compute_course_progress(progress_json, paths)

                total_courses = sum(len(p.get("courses") or []) for p in paths)

                return {
                    "status": "in_progress" if completion_rate < 100 else "completed",
                    "completion_rate": completion_rate,
                    "modules_completed": modules["completed_courses"],
                    "total_modules": total_courses,
                    "pathways_completed": modules["completed_pathways"],
                    "total_pathways": len(paths),
                    "course_progress": course_progress,
                    "url": "http://localhost:3000",
                }
        except httpx.RequestError as e:
            logger.warning("Could not connect to Strapi for user progress: %s", e)
            return self._mock_progress()

    async def enroll(self, email: str, password: str = "Pathways2024!") -> dict:
        """Register a user on the Strapi e-learning platform."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/auth/local/register",
                    json={
                        "username": email,
                        "email": email,
                        "password": password,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    strapi_user = data.get("user", {})
                    return {
                        "pathways_user_id": str(strapi_user.get("id", "")),
                        "platform_url": "http://localhost:3000",
                    }

                # User might already exist - try to find them
                if response.status_code == 400:
                    find_resp = await client.get(
                        f"{self.base_url}/users",
                        params={"username": email},
                    )
                    if find_resp.status_code == 200:
                        users = find_resp.json()
                        if users:
                            user = users[0] if isinstance(users, list) else users
                            return {
                                "pathways_user_id": str(user.get("id", "")),
                                "platform_url": "http://localhost:3000",
                            }

                logger.warning("Failed to register user on Strapi: %s", response.status_code)
                return self._mock_enroll(email)
        except httpx.RequestError as e:
            logger.warning("Could not connect to Strapi for enrollment: %s", e)
            return self._mock_enroll(email)

    async def sync_progress(self, email: str | None) -> dict:
        """Fetch latest progress for a single user from Strapi."""
        if not email:
            return {"completion_rate": 0, "synced_at": datetime.utcnow().isoformat()}

        progress = await self.get_progress(email)
        return {
            "completion_rate": progress.get("completion_rate", 0),
            "synced_at": datetime.utcnow().isoformat(),
        }

    async def sync_all_progress(self, db: AsyncSession) -> dict:
        """Bulk sync: fetch all Strapi users, match by email, update beneficiaries."""
        paths = await self._fetch_paths()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{self.base_url}/users",
                    params={"_limit": -1},
                )
                if response.status_code != 200:
                    return {"error": f"Failed to fetch Strapi users: {response.status_code}"}

                strapi_users = response.json()
        except httpx.RequestError as e:
            return {"error": f"Could not connect to Strapi: {e}"}

        # Build email -> progressJson map from Strapi
        strapi_progress = {}
        for su in strapi_users:
            email = (su.get("email") or su.get("username") or "").lower().strip()
            if email:
                strapi_progress[email] = su.get("progressJson") or {}

        # Fetch all beneficiaries with their users
        result = await db.execute(
            select(Beneficiary, User).join(User, Beneficiary.user_id == User.id)
        )
        rows = result.all()

        matched = 0
        updated = 0
        now = datetime.utcnow()

        for ben, user in rows:
            email = (user.email or "").lower().strip()
            if email in strapi_progress:
                matched += 1
                progress_json = strapi_progress[email]
                rate = self._compute_completion_rate(progress_json, paths)
                course_progress = self._compute_course_progress(progress_json, paths)

                if ben.pathways_completion_rate is None or float(ben.pathways_completion_rate) != rate:
                    ben.pathways_completion_rate = rate
                    ben.pathways_course_progress = course_progress
                    ben.pathways_last_sync = now
                    updated += 1
                elif ben.pathways_course_progress != course_progress:
                    ben.pathways_course_progress = course_progress
                    ben.pathways_last_sync = now

        await db.commit()

        return {
            "matched": matched,
            "updated": updated,
            "total_strapi_users": len(strapi_users),
            "total_beneficiaries": len(rows),
        }

    def _mock_progress(self) -> dict:
        """Fallback when Strapi is unreachable."""
        return {
            "status": "unknown",
            "completion_rate": 0,
            "modules_completed": 0,
            "total_modules": 0,
            "url": None,
            "note": "Pathways platform is currently unreachable",
        }

    def _mock_enroll(self, email: str) -> dict:
        """Fallback enrollment response when Strapi is unreachable."""
        return {
            "pathways_user_id": None,
            "platform_url": None,
            "note": "Pathways platform is currently unreachable",
        }


pathways_service = PathwaysService()
