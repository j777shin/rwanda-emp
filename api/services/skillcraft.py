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


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def _get_answers(result_data: dict, key: str) -> dict[int, float]:
    """Extract {questionNumber: answer} map from a test scores field.

    Handles both list-of-dicts and single-dict formats.
    """
    raw = result_data.get(key)
    if not raw:
        return {}
    items = raw if isinstance(raw, list) else [raw]
    return {
        item["questionNumber"]: item["answer"]
        for item in items
        if item.get("questionNumber") is not None and isinstance(item.get("answer"), (int, float))
    }


def _survey_score(answers: dict[int, float], questions: list[int], recode: list[int] | None = None) -> float | None:
    """Compute normalized survey sub-score: (avg - 1) / 4.

    Applies reverse-coding (6 - answer) for question IDs in `recode`.
    """
    if not answers:
        return None
    recode_set = set(recode or [])
    values = []
    for q in questions:
        v = answers.get(q)
        if v is None:
            continue
        if q in recode_set:
            v = 6 - v
        values.append(v)
    if not values:
        return None
    return _clamp((sum(values) / len(values) - 1) / 4)


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

    # ------------------------------------------------------------------
    # Shared sub-score helpers (used by both W_score and E_score)
    # ------------------------------------------------------------------

    def _digit_span_score(self, result_data: dict) -> tuple[float | None, dict]:
        """Digit Span sub-score (shared by W_score and E_score).

        Part A (Forward): longest n with acc=1 for trials 3-14, /9, cap 1.
        Part B (Backward): longest n with acc=1, /8, cap 1.
        Score: average of Part A and Part B.
        """
        trials = result_data.get("digitSpanScores") or []
        if not isinstance(trials, list):
            trials = [trials]

        forward_max_n = 0
        backward_max_n = 0
        for t in trials:
            acc = t.get("acc")
            n = t.get("n")
            assess_type = t.get("assessType")
            if acc != 1 or n is None:
                continue
            # assessType 0 = forward, 1 = backward (based on SkillCraft convention)
            # The PDF says forward trials are 3-14
            if assess_type == 0 and 3 <= (t.get("practice", n)) <= 14:
                forward_max_n = max(forward_max_n, n)
            elif assess_type == 1:
                backward_max_n = max(backward_max_n, n)

        part_a = _clamp(forward_max_n / 9) if forward_max_n else None
        part_b = _clamp(backward_max_n / 8) if backward_max_n else None

        parts = [p for p in [part_a, part_b] if p is not None]
        score = sum(parts) / len(parts) if parts else None

        detail = {"forward_max_n": forward_max_n, "part_a": part_a,
                  "backward_max_n": backward_max_n, "part_b": part_b, "score": score}
        return score, detail

    def _conscientiousness_score(self, big_five: dict[int, float]) -> tuple[float | None, dict]:
        """Conscientiousness (shared by W_score and E_score).

        Recode Q3, Q8, Q28 as 6-answer.
        Avg of Q3r, Q8r, Q13, Q18, Q23, Q28r. Then (avg-1)/4.
        """
        score = _survey_score(big_five, [3, 8, 13, 18, 23, 28], recode=[3, 8, 28])
        return score, {"score": score}

    # ------------------------------------------------------------------
    # W_score: 14 sub-scores (Wage Employment)
    # ------------------------------------------------------------------

    def compute_w_score(self, result_data: dict) -> tuple[float | None, dict]:
        """Compute W_score from raw /result data per Algorithm Part 1.

        Returns (w_score, sub_scores_dict).
        """
        if not result_data:
            return None, {}

        sub: dict = {}
        components: list[float] = []

        # Helper to collect a sub-score
        def _add(name: str, value: float | None, detail: dict | None = None):
            sub[name] = {"score": value, **(detail or {})}
            if value is not None:
                components.append(value)

        # 1. Corsi Block-Tapping: min(max_span / 7, 1)
        corsi_trials = result_data.get("corsiGameScores") or []
        if not isinstance(corsi_trials, list):
            corsi_trials = [corsi_trials]
        spans = [t.get("highestCorsiSpan") for t in corsi_trials
                 if isinstance(t.get("highestCorsiSpan"), (int, float))]
        max_span = max(spans) if spans else None
        corsi_score = _clamp(max_span / 7) if max_span is not None else None
        _add("corsi", corsi_score, {"max_span": max_span})

        # 2. CPT: percentCorrect / 100
        cpt_meta = result_data.get("cptMetadata") or {}
        pct = cpt_meta.get("percentCorrect")
        cpt_score = _clamp(pct / 100) if isinstance(pct, (int, float)) else None
        _add("cpt", cpt_score, {"percent_correct": pct})

        # 3. Digit Span (shared)
        ds_score, ds_detail = self._digit_span_score(result_data)
        _add("digit_span", ds_score, ds_detail)

        # 4. TMT: Part A = clamp((120-trailATime)/83), Part B = clamp((300-trailBTime)/257), avg
        tmt_meta = result_data.get("tmtMetadata") or {}
        trail_a = tmt_meta.get("trailATime")
        trail_b = tmt_meta.get("trailBTime")
        tmt_a = _clamp((120 - trail_a) / 83) if isinstance(trail_a, (int, float)) else None
        tmt_b = _clamp((300 - trail_b) / 257) if isinstance(trail_b, (int, float)) else None
        tmt_parts = [p for p in [tmt_a, tmt_b] if p is not None]
        tmt_score = sum(tmt_parts) / len(tmt_parts) if tmt_parts else None
        _add("tmt", tmt_score, {"trail_a_time": trail_a, "part_a": tmt_a,
                                 "trail_b_time": trail_b, "part_b": tmt_b})

        # --- Emotional Test sub-scores (5, 6, 7) ---
        emotional = _get_answers(result_data, "emotionalTestScores")

        # 5. Social Awareness: Q2,4,9,11,13 → (avg-1)/4
        _add("social_awareness", _survey_score(emotional, [2, 4, 9, 11, 13]))

        # 6. Self-Management: Q1,3,6,8,12 → (avg-1)/4
        _add("self_management", _survey_score(emotional, [1, 3, 6, 8, 12]))

        # 7. Self-Awareness: Q5,7,10 → (avg-1)/4
        _add("self_awareness", _survey_score(emotional, [5, 7, 10]))

        # --- Big Five sub-scores (8, 9) ---
        big_five = _get_answers(result_data, "bigFiveTestScores")

        # 8. Agreeableness: recode Q7,17,27; avg Q2,7r,12,17r,22,27r → (avg-1)/4
        _add("agreeableness", _survey_score(big_five, [2, 7, 12, 17, 22, 27], recode=[7, 17, 27]))

        # 9. Conscientiousness (shared)
        consc_score, consc_detail = self._conscientiousness_score(big_five)
        _add("conscientiousness", consc_score, consc_detail)

        # --- RIASEC sub-scores (10-14) ---
        riasec = _get_answers(result_data, "riasecTestScores")

        # 10. Realistic: Q1,7,13,19,25 → (avg-1)/4
        _add("realistic", _survey_score(riasec, [1, 7, 13, 19, 25]))

        # 11. Investigative: Q2,8,14,20,26 → (avg-1)/4
        _add("investigative", _survey_score(riasec, [2, 8, 14, 20, 26]))

        # 12. Artistic: Q3,9,15,21,27 → (avg-1)/4
        _add("artistic", _survey_score(riasec, [3, 9, 15, 21, 27]))

        # 13. Social: Q4,10,16,22,28 → (avg-1)/4
        _add("social", _survey_score(riasec, [4, 10, 16, 22, 28]))

        # 14. Conventional: Q6,12,18,24,30 → (avg-1)/4
        _add("conventional", _survey_score(riasec, [6, 12, 18, 24, 30]))

        # Final W_score = average of 14 components
        w_score = round(sum(components) / len(components), 4) if components else None
        return w_score, sub

    # ------------------------------------------------------------------
    # E_score: 9 sub-scores (Entrepreneurship)
    # ------------------------------------------------------------------

    def compute_e_score(self, result_data: dict) -> tuple[float | None, dict]:
        """Compute E_score from raw /result data per Algorithm Part 1.

        Returns (e_score, sub_scores_dict).
        """
        if not result_data:
            return None, {}

        sub: dict = {}
        components: list[float] = []

        def _add(name: str, value: float | None, detail: dict | None = None):
            sub[name] = {"score": value, **(detail or {})}
            if value is not None:
                components.append(value)

        # 1. Digit Span (shared)
        ds_score, ds_detail = self._digit_span_score(result_data)
        _add("digit_span", ds_score, ds_detail)

        # 2. HMT: sum correct for trials where X >= 3, /10
        hmt_trials = result_data.get("hmtScores") or []
        if not isinstance(hmt_trials, list):
            hmt_trials = [hmt_trials]
        # Trials where index/key >= 3 (non-practice trials)
        hmt_real = [t for t in hmt_trials if not t.get("practice")]
        hmt_correct_sum = sum(t.get("correct", 0) for t in hmt_real)
        hmt_score = _clamp(hmt_correct_sum / 10) if hmt_real else None
        _add("hmt", hmt_score, {"correct_sum": hmt_correct_sum, "num_trials": len(hmt_real)})

        # 3. Conscientiousness (shared)
        big_five = _get_answers(result_data, "bigFiveTestScores")
        consc_score, consc_detail = self._conscientiousness_score(big_five)
        _add("conscientiousness", consc_score, consc_detail)

        # 4. Openness: recode Q10,20,30; avg Q5,10r,15,20r,25,30r → (avg-1)/4
        _add("openness", _survey_score(big_five, [5, 10, 15, 20, 25, 30], recode=[10, 20, 30]))

        # 5. Growth Mindset: recode ALL Q1-4 as 6-answer, avg → (avg-1)/4
        growth = _get_answers(result_data, "growthMindsetTestScores")
        _add("growth_mindset", _survey_score(growth, [1, 2, 3, 4], recode=[1, 2, 3, 4]))

        # 6. BRET: min(meanParcelsCollected / 25, 1)
        bret_meta = result_data.get("bretMetadata") or {}
        mean_parcels = bret_meta.get("meanParcelsCollected")
        bret_score = _clamp(mean_parcels / 25) if isinstance(mean_parcels, (int, float)) else None
        _add("bret", bret_score, {"mean_parcels_collected": mean_parcels})

        # 7. Proactive Personality: avg all answers → (avg-1)/4
        proactive = _get_answers(result_data, "proactiveTestScores")
        all_q = sorted(proactive.keys())
        _add("proactive", _survey_score(proactive, all_q) if all_q else None)

        # 8. MTPT: if mtptScores.3.maxCompletionPercent == 1 → 1.0
        #          else roundTime / 127000, cap 1
        mtpt_trials = result_data.get("mtptScores") or []
        if not isinstance(mtpt_trials, list):
            mtpt_trials = [mtpt_trials]
        # Find round 3 (index 3 or the 4th element, non-practice)
        # The PDF says "mtptScores.3" — this is the trial at key/index 3
        non_practice = [t for t in mtpt_trials if not t.get("isPractice")]
        round_3 = non_practice[0] if non_practice else None  # first non-practice round
        # If mtptScores is keyed by round ID "3", try to find it
        if isinstance(result_data.get("mtptScores"), dict):
            round_3 = result_data["mtptScores"].get("3") or result_data["mtptScores"].get(3)
        mtpt_score = None
        mtpt_detail: dict = {}
        if round_3:
            mcp = round_3.get("maxCompletionPercent")
            rt = round_3.get("roundTime")
            mtpt_detail = {"max_completion_percent": mcp, "round_time": rt}
            if mcp == 1:
                mtpt_score = 1.0
            elif isinstance(rt, (int, float)):
                mtpt_score = _clamp(rt / 127000)
        _add("mtpt", mtpt_score, mtpt_detail)

        # 9. Enterprising (RIASEC): Q5,11,17,23,29 → (avg-1)/4
        riasec = _get_answers(result_data, "riasecTestScores")
        _add("enterprising", _survey_score(riasec, [5, 11, 17, 23, 29]))

        # Final E_score = average of 9 components
        e_score = round(sum(components) / len(components), 4) if components else None
        return e_score, sub

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
        """Sign in, fetch assessment and raw result, compute W/E scores."""
        sign_in_result = await self.sign_in(email)
        if "error" in sign_in_result:
            return {"error": sign_in_result["error"]}

        token = sign_in_result["access_token"]
        result = await self.get_result(token)

        if not result or not result.get("finished"):
            return {
                "score": None,
                "w_score": None,
                "e_score": None,
                "scores": None,
                "finished": False,
                "synced_at": datetime.utcnow().isoformat(),
            }

        assessment = await self.get_assessment(token)
        score = self.compute_score(assessment)

        # Get the raw result data (first entry in data array)
        raw_data = result.get("data", [{}])
        first_result = raw_data[0] if raw_data else result

        # Compute W_score and E_score per Algorithm Part 1
        w_score, w_sub = self.compute_w_score(first_result)
        e_score, e_sub = self.compute_e_score(first_result)

        return {
            "score": score,
            "w_score": w_score,
            "e_score": e_score,
            "scores": {"w_sub_scores": w_sub, "e_sub_scores": e_sub},
            "finished": True,
            "synced_at": datetime.utcnow().isoformat(),
        }


skillcraft_service = SkillCraftService()
