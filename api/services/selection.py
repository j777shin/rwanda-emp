import random
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.beneficiary import Beneficiary
from models.survey import SurveyResponse
from services.pmt_scoring import calculate_pmt_score
from utils.helpers import test_account_user_ids_subquery

# Phase 1 survey question IDs (1-5 Likert scale)
_PHASE1_SURVEY_QUESTIONS = [
    "overall_training_quality",
    "content_relevance",
    "instructor_quality",
    "facility_quality",
    "would_recommend",
]

# Word pool for generating business development text
_BUSINESS_WORDS = [
    "I", "want", "to", "start", "a", "small", "business", "in", "my", "community",
    "selling", "agricultural", "products", "from", "local", "farmers", "and", "markets",
    "plan", "open", "shop", "provide", "services", "tailoring", "hairdressing",
    "mobile", "money", "agent", "motorcycle", "transport", "food", "processing",
    "retail", "wholesale", "trading", "vegetables", "fruits", "grains", "livestock",
    "poultry", "farming", "fish", "dairy", "milk", "eggs", "honey", "coffee",
    "tea", "crafts", "handmade", "goods", "clothing", "shoes", "electronics",
    "repair", "construction", "materials", "building", "carpentry", "welding",
    "restaurant", "catering", "bakery", "juice", "bar", "salon", "barber",
    "cleaning", "laundry", "photography", "printing", "internet", "cafe",
    "training", "education", "tutoring", "childcare", "healthcare", "pharmacy",
    "grow", "expand", "hire", "employees", "create", "jobs", "youth", "women",
    "cooperative", "savings", "group", "investment", "capital", "loan", "profit",
    "sustainable", "innovative", "digital", "technology", "online", "platform",
    "Rwanda", "Kigali", "district", "sector", "village", "market", "customers",
    "quality", "affordable", "reliable", "delivery", "supply", "chain", "value",
]


def _generate_business_text() -> str:
    """Generate random business development text of 20-100 words."""
    length = random.randint(20, 100)
    words = random.choices(_BUSINESS_WORDS, k=length)
    # Capitalize first word and add period at end
    text = " ".join(words)
    return text[0].upper() + text[1:] + "."


async def calculate_all_pmt_scores(db: AsyncSession) -> dict:
    """Calculate PMT scores for all non-test beneficiaries and store as eligibility_score."""
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    result = await db.execute(select(Beneficiary).where(exc))
    beneficiaries = result.scalars().all()

    count = 0
    for ben in beneficiaries:
        data = {
            "cooking_firewood": ben.cooking_firewood,
            "cooking_gas": ben.cooking_gas,
            "cooking_charcoal": ben.cooking_charcoal,
            "floor_earth_sand": ben.floor_earth_sand,
            "floor_tiles": ben.floor_tiles,
            "lighting": ben.lighting,
            "num_phone": ben.num_phone,
            "num_radio": ben.num_radio,
            "num_tv": ben.num_tv,
            "num_cattle": ben.num_cattle,
            "num_goats": ben.num_goats,
            "num_sheep": ben.num_sheep,
            "num_pigs": ben.num_pigs,
            "land_ownership": ben.land_ownership,
            "children_under_18": ben.children_under_18,
            "household_size": ben.household_size,
            "hh_head_university": ben.hh_head_university,
            "hh_head_primary": ben.hh_head_primary,
            "hh_head_secondary": ben.hh_head_secondary,
            "hh_head_married": ben.hh_head_married,
            "hh_head_widow": ben.hh_head_widow,
            "hh_head_divorced": ben.hh_head_divorced,
            "hh_head_female": ben.hh_head_female,
            "district": ben.district,
        }
        pmt_score = calculate_pmt_score(data)
        ben.eligibility_score = round(100 - pmt_score, 2)
        count += 1

    await db.commit()
    return {"scored": count}


async def select_phase1_beneficiaries(db: AsyncSession, count: int = 9000) -> dict:
    """Select top N most vulnerable non-test beneficiaries (highest eligibility scores) for Phase 1."""
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    # Get all pending beneficiaries ordered by eligibility score (descending = most vulnerable first)
    result = await db.execute(
        select(Beneficiary)
        .where(exc)
        .where(Beneficiary.selection_status == "pending")
        .where(Beneficiary.eligibility_score.is_not(None))
        .order_by(Beneficiary.eligibility_score.desc())
    )
    all_pending = result.scalars().all()

    selected = all_pending[:count]
    rejected = all_pending[count:]

    for ben in selected:
        ben.selection_status = "selected"

    for ben in rejected:
        ben.selection_status = "rejected"

    await db.commit()

    return {
        "selected": len(selected),
        "rejected": len(rejected),
        "total_processed": len(all_pending),
    }


async def assign_tracks(
    db: AsyncSession,
    beneficiary_ids: list[str],
    track: str,
) -> dict:
    """Assign beneficiaries to employment or entrepreneurship track."""
    count = 0
    for bid in beneficiary_ids:
        result = await db.execute(select(Beneficiary).where(Beneficiary.id == bid))
        ben = result.scalar_one_or_none()
        if ben and ben.selection_status == "selected":
            ben.track = track
            count += 1

    await db.commit()
    return {"assigned": count, "track": track}


def _generate_skillcraft_scores() -> dict:
    """Generate random W/E sub-scores matching the Algorithm Part 1 structure."""
    def _rand() -> float:
        return round(random.uniform(0.1, 1.0), 4)

    w_sub = {
        "corsi": {"score": _rand(), "max_span": random.randint(3, 7)},
        "cpt": {"score": _rand(), "percent_correct": round(random.uniform(50, 100), 1)},
        "digit_span": {"score": _rand(), "forward_max_n": random.randint(3, 9), "part_a": _rand(),
                        "backward_max_n": random.randint(2, 8), "part_b": _rand()},
        "tmt": {"score": _rand(), "trail_a_time": round(random.uniform(20, 120), 1), "part_a": _rand(),
                "trail_b_time": round(random.uniform(40, 300), 1), "part_b": _rand()},
        "social_awareness": {"score": _rand()},
        "self_management": {"score": _rand()},
        "self_awareness": {"score": _rand()},
        "agreeableness": {"score": _rand()},
        "conscientiousness": {"score": _rand()},
        "realistic": {"score": _rand()},
        "investigative": {"score": _rand()},
        "artistic": {"score": _rand()},
        "social": {"score": _rand()},
        "conventional": {"score": _rand()},
    }
    e_sub = {
        "digit_span": w_sub["digit_span"],
        "hmt": {"score": _rand(), "correct_sum": random.randint(3, 10), "num_trials": 10},
        "conscientiousness": w_sub["conscientiousness"],
        "openness": {"score": _rand()},
        "growth_mindset": {"score": _rand()},
        "bret": {"score": _rand(), "mean_parcels_collected": round(random.uniform(5, 25), 1)},
        "proactive": {"score": _rand()},
        "mtpt": {"score": _rand(), "max_completion_percent": round(random.uniform(0.5, 1.0), 2),
                 "round_time": random.randint(30000, 127000)},
        "enterprising": {"score": _rand()},
    }
    w_score = round(sum(s["score"] for s in w_sub.values()) / 14, 4)
    e_score = round(sum(s["score"] for s in e_sub.values()) / 9, 4)
    # skillcraft_score = average of all sub-scores × 100
    all_scores = [s["score"] for s in w_sub.values()] + [s["score"] for s in e_sub.values()]
    skillcraft_score = round(sum(all_scores) / len(all_scores) * 100, 2)
    return {
        "skillcraft_score": skillcraft_score,
        "w_score": w_score,
        "e_score": e_score,
        "scores": {"w_sub_scores": w_sub, "e_sub_scores": e_sub},
    }


async def apply_phase1_results(db: AsyncSession) -> dict:
    """Generate simulated Phase 1 training results for all selected beneficiaries."""
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    result = await db.execute(
        select(Beneficiary).where(exc, Beneficiary.selection_status == "selected")
    )
    beneficiaries = result.scalars().all()

    ent_count = 0
    for ben in beneficiaries:
        # --- SkillCraft scores (simulated) ---
        sc = _generate_skillcraft_scores()
        ben.skillcraft_score = sc["skillcraft_score"]
        ben.w_score = sc["w_score"]
        ben.e_score = sc["e_score"]
        ben.skillcraft_scores = sc["scores"]

        # --- Other Phase 1 results (simulated) ---
        ben.pathways_completion_rate = random.randint(20, 100)
        ben.offline_attendance = random.randint(7, 10)
        ben.wants_entrepreneurship = random.random() < 0.70
        if ben.wants_entrepreneurship:
            ben.business_development_text = _generate_business_text()
            ent_count += 1
        else:
            ben.business_development_text = None

    await db.commit()
    return {"updated": len(beneficiaries), "ent_applicants": ent_count}


def _generate_phase1_survey() -> tuple[dict, float]:
    """Generate random phase 1 survey responses and compute satisfaction score.

    Returns (responses_dict, satisfaction_score_0_100).
    """
    responses = {}
    for q in _PHASE1_SURVEY_QUESTIONS:
        # Weighted heavily towards 4-5 to target average ~4.3+
        responses[q] = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 7, 35, 55])[0]

    ratings = list(responses.values())
    avg_score = sum(ratings) / len(ratings) * 20  # Scale 1-5 → 0-100
    return responses, round(avg_score, 1)


async def run_phase2_selection(db: AsyncSession, ent_count: int = 3000) -> dict:
    """Auto-assign tracks: top ent_count entrepreneurship applicants → ent track, rest → emp track."""
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    result = await db.execute(
        select(Beneficiary).where(exc, Beneficiary.selection_status == "selected")
    )
    beneficiaries = result.scalars().all()

    # --- Generate Phase 1 survey results for all selected beneficiaries ---
    survey_count = 0
    # Collect existing survey beneficiary IDs to avoid duplicates
    existing_result = await db.execute(
        select(SurveyResponse.beneficiary_id).where(
            SurveyResponse.survey_type == "phase1"
        )
    )
    existing_survey_ids = {row[0] for row in existing_result.all()}

    for ben in beneficiaries:
        responses, score = _generate_phase1_survey()
        ben.phase1_satisfactory = score

        if ben.id not in existing_survey_ids:
            survey = SurveyResponse(
                beneficiary_id=ben.id,
                survey_type="phase1",
                responses=responses,
                completion_time=random.randint(120, 600),
                completed_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.add(survey)
            survey_count += 1

    # Score entrepreneurship applicants
    # Composite = skillcraft_score + pathways_completion_rate + offline_attendance*10 + e_score*100 + word_count
    ent_applicants = []
    non_applicants = []
    for ben in beneficiaries:
        if ben.wants_entrepreneurship:
            word_count = len(ben.business_development_text.split()) if ben.business_development_text else 0
            composite = (
                float(ben.skillcraft_score or 0)
                + float(ben.pathways_completion_rate or 0)
                + float(ben.offline_attendance or 0) * 10
                + float(ben.e_score or 0) * 100
                + word_count
            )
            ent_applicants.append((ben, composite))
        else:
            non_applicants.append(ben)

    # Sort by composite score descending (highest = best candidate)
    ent_applicants.sort(key=lambda x: x[1], reverse=True)

    # Top ent_count → entrepreneurship, rest → employment
    ent_selected = 0
    emp_selected = 0
    ent_beneficiaries = []

    for i, (ben, _score) in enumerate(ent_applicants):
        if i < ent_count:
            ben.track = "entrepreneurship"
            ent_selected += 1
            ent_beneficiaries.append(ben)
        else:
            ben.track = "employment"
            emp_selected += 1

    for ben in non_applicants:
        ben.track = "employment"
        emp_selected += 1

    # --- Generate outcome data for entrepreneurship track ---
    if ent_beneficiaries:
        random.shuffle(ent_beneficiaries)

        # 400 receive grants
        grant_recipients = ent_beneficiaries[:400]
        # 80 get 1,250,000 RWF, 320 get 500,000 RWF
        for i, ben in enumerate(grant_recipients):
            ben.grant_received = True
            ben.grant_amount = 1250000 if i < 80 else 500000

        # 40 newly hired, 5 self-employed (from the full ent pool)
        random.shuffle(ent_beneficiaries)
        for i, ben in enumerate(ent_beneficiaries[:40]):
            ben.hired = True
        for i, ben in enumerate(ent_beneficiaries[40:45]):
            ben.self_employed = True

    await db.commit()
    return {
        "entrepreneurship": ent_selected,
        "employment": emp_selected,
        "grants_awarded": min(400, len(ent_beneficiaries)),
        "newly_hired": min(40, len(ent_beneficiaries)),
        "self_employed": min(5, max(0, len(ent_beneficiaries) - 40)),
        "phase1_surveys_generated": survey_count,
    }
