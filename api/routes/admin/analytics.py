from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotConversation, ChatbotResult
from models.survey import SurveyResponse
from middleware.auth import require_admin
from utils.helpers import test_account_user_ids_subquery

router = APIRouter()


@router.get("/overview")
async def get_overview(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    total = (await db.execute(select(func.count()).select_from(Beneficiary).where(exc))).scalar()
    selected = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.selection_status == "selected")
    )).scalar()
    employment = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == "employment")
    )).scalar()
    entrepreneurship = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == "entrepreneurship")
    )).scalar()

    avg_skillcraft = (await db.execute(
        select(func.avg(Beneficiary.skillcraft_score)).where(exc, Beneficiary.skillcraft_score.is_not(None))
    )).scalar()
    avg_pathways = (await db.execute(
        select(func.avg(Beneficiary.pathways_completion_rate)).where(exc, Beneficiary.pathways_completion_rate.is_not(None))
    )).scalar()
    avg_eligibility = (await db.execute(
        select(func.avg(Beneficiary.eligibility_score)).where(exc, Beneficiary.eligibility_score.is_not(None))
    )).scalar()

    chatbot_sessions = (await db.execute(
        select(func.count(func.distinct(ChatbotConversation.beneficiary_id)))
    )).scalar()

    return {
        "total_beneficiaries": total,
        "selected_count": selected,
        "employment_track": employment,
        "entrepreneurship_track": entrepreneurship,
        "avg_skillcraft_score": float(avg_skillcraft) if avg_skillcraft else None,
        "avg_pathways_rate": float(avg_pathways) if avg_pathways else None,
        "avg_eligibility_score": float(avg_eligibility) if avg_eligibility else None,
        "chatbot_sessions": chatbot_sessions,
    }


@router.get("/demographics")
async def get_demographics(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    # Gender distribution
    gender_result = await db.execute(
        select(Beneficiary.gender, func.count()).where(exc).group_by(Beneficiary.gender)
    )
    gender = {row[0] or "unknown": row[1] for row in gender_result.all()}

    # Age distribution
    age_result = await db.execute(
        select(
            case(
                (Beneficiary.age.between(15, 19), "15-19"),
                (Beneficiary.age.between(20, 24), "20-24"),
                (Beneficiary.age.between(25, 29), "25-29"),
                (Beneficiary.age.between(30, 35), "30-35"),
            ).label("age_group"),
            func.count(),
        ).where(exc).group_by("age_group")
    )
    age = {row[0]: row[1] for row in age_result.all() if row[0]}

    # Education distribution
    edu_result = await db.execute(
        select(Beneficiary.education_level, func.count())
        .where(exc, Beneficiary.education_level.is_not(None))
        .group_by(Beneficiary.education_level)
    )
    education = {row[0]: row[1] for row in edu_result.all()}

    # District distribution
    district_result = await db.execute(
        select(Beneficiary.district, func.count())
        .where(exc, Beneficiary.district.is_not(None))
        .group_by(Beneficiary.district)
        .order_by(func.count().desc())
    )
    districts = {row[0]: row[1] for row in district_result.all()}

    # Marriage status distribution
    married_count = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.marriage_status == True)
    )).scalar()
    unmarried_count = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.marriage_status == False)
    )).scalar()
    marriage_status = {"Married": married_count, "Unmarried": unmarried_count}

    # Disability distribution
    disabled_count = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.disability == True)
    )).scalar()
    no_disability_count = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.disability == False)
    )).scalar()
    disability = {"Has Disability": disabled_count, "No Disability": no_disability_count}

    # Occupation distribution
    has_occupation = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.occupation == True)
    )).scalar()
    no_occupation = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.occupation == False)
    )).scalar()
    occupation = {"Has Occupation": has_occupation, "No Occupation": no_occupation}

    # Informal working distribution
    informal_yes = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.informal_working == True)
    )).scalar()
    informal_no = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.informal_working == False)
    )).scalar()
    informal_working = {"Informal": informal_yes, "Formal / None": informal_no}

    # Household size distribution
    hh_result = await db.execute(
        select(
            case(
                (Beneficiary.household_size.between(1, 2), "1-2"),
                (Beneficiary.household_size.between(3, 4), "3-4"),
                (Beneficiary.household_size.between(5, 6), "5-6"),
                (Beneficiary.household_size >= 7, "7+"),
            ).label("hh_group"),
            func.count(),
        ).where(exc, Beneficiary.household_size > 0).group_by("hh_group")
    )
    household_size_groups = {row[0]: row[1] for row in hh_result.all() if row[0]}

    return {
        "gender": gender,
        "age_groups": age,
        "education": education,
        "districts": districts,
        "marriage_status": marriage_status,
        "disability": disability,
        "occupation": occupation,
        "informal_working": informal_working,
        "household_size_groups": household_size_groups,
    }


@router.get("/engagement")
async def get_engagement(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    # SkillCraft completion
    sc_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.selection_status == "selected")
    )).scalar()
    sc_completed = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.skillcraft_score.is_not(None))
    )).scalar()

    # Pathways enrollment
    pw_enrolled = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.pathways_user_id.is_not(None))
    )).scalar()

    # Business dev submissions
    bd_submitted = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.wants_entrepreneurship == True)
    )).scalar()

    # Chatbot engagement
    chatbot_users = (await db.execute(
        select(func.count(func.distinct(ChatbotConversation.beneficiary_id)))
    )).scalar()
    total_messages = (await db.execute(
        select(func.count()).select_from(ChatbotConversation)
    )).scalar()

    return {
        "skillcraft": {"total": sc_total, "completed": sc_completed},
        "pathways": {"enrolled": pw_enrolled},
        "business_development": {"submitted": bd_submitted},
        "chatbot": {"unique_users": chatbot_users, "total_messages": total_messages},
    }


@router.get("/socioeconomic")
async def get_socioeconomic(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    # Land ownership
    land_owners = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.land_ownership == True)
    )).scalar()
    total = (await db.execute(select(func.count()).select_from(Beneficiary).where(exc))).scalar()

    # Avg livestock
    avg_cattle = (await db.execute(select(func.avg(Beneficiary.num_cattle)).where(exc))).scalar()
    avg_goats = (await db.execute(select(func.avg(Beneficiary.num_goats)).where(exc))).scalar()

    # Housing
    earth_floor = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.floor_earth_sand == True)
    )).scalar()
    has_lighting = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.lighting == True)
    )).scalar()

    # Avg household size
    avg_hh = (await db.execute(select(func.avg(Beneficiary.household_size)).where(exc))).scalar()

    # --- Distribution arrays for charts ---

    # Livestock ownership: count of owners per type
    livestock_types = [
        ("Cattle", Beneficiary.num_cattle),
        ("Goats", Beneficiary.num_goats),
        ("Sheep", Beneficiary.num_sheep),
        ("Pigs", Beneficiary.num_pigs),
    ]
    livestock_ownership = []
    for label, col in livestock_types:
        owners = (await db.execute(
            select(func.count()).select_from(Beneficiary).where(exc, col > 0)
        )).scalar() or 0
        livestock_ownership.append({
            "category": label,
            "owners": owners,
            "percentage": round(owners / total * 100, 1) if total else 0,
        })

    # Land ownership distribution by size
    land_size_buckets = [
        ("No Land", Beneficiary.land_ownership == False),
        ("< 0.5 ha", (Beneficiary.land_ownership == True) & (Beneficiary.land_size < 0.5)),
        ("0.5–1 ha", (Beneficiary.land_ownership == True) & (Beneficiary.land_size >= 0.5) & (Beneficiary.land_size < 1)),
        ("1–2 ha", (Beneficiary.land_ownership == True) & (Beneficiary.land_size >= 1) & (Beneficiary.land_size < 2)),
        ("2+ ha", (Beneficiary.land_ownership == True) & (Beneficiary.land_size >= 2)),
    ]
    land_ownership_dist = []
    for label, condition in land_size_buckets:
        cnt = (await db.execute(
            select(func.count()).select_from(Beneficiary).where(exc, condition)
        )).scalar() or 0
        land_ownership_dist.append({"category": label, "value": cnt})

    # Housing quality indicators
    tiles_floor = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.floor_tiles == True)
    )).scalar() or 0
    uses_gas = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.cooking_gas == True)
    )).scalar() or 0
    uses_charcoal = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.cooking_charcoal == True)
    )).scalar() or 0
    uses_firewood = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.cooking_firewood == True)
    )).scalar() or 0
    housing_quality = [
        {"quality": "Earth/Sand Floor", "count": earth_floor or 0},
        {"quality": "Tile Floor", "count": tiles_floor},
        {"quality": "Has Lighting", "count": has_lighting or 0},
        {"quality": "Cooks w/ Gas", "count": uses_gas},
        {"quality": "Cooks w/ Charcoal", "count": uses_charcoal},
        {"quality": "Cooks w/ Firewood", "count": uses_firewood},
    ]

    # Assets distribution
    assets_types = [
        ("Radio", Beneficiary.num_radio),
        ("Phone", Beneficiary.num_phone),
        ("TV", Beneficiary.num_tv),
    ]
    assets_distribution = []
    for label, col in assets_types:
        owners = (await db.execute(
            select(func.count()).select_from(Beneficiary).where(exc, col > 0)
        )).scalar() or 0
        assets_distribution.append({
            "category": label,
            "owners": owners,
            "percentage": round(owners / total * 100, 1) if total else 0,
        })

    return {
        "land_ownership_rate": land_owners / total if total else 0,
        "avg_cattle": float(avg_cattle) if avg_cattle else 0,
        "avg_goats": float(avg_goats) if avg_goats else 0,
        "earth_floor_rate": earth_floor / total if total else 0,
        "lighting_rate": has_lighting / total if total else 0,
        "avg_household_size": float(avg_hh) if avg_hh else 0,
        "total": total,
        "livestock_ownership": livestock_ownership,
        "land_ownership": land_ownership_dist,
        "housing_quality": housing_quality,
        "assets_distribution": assets_distribution,
    }


@router.get("/impact")
async def get_impact_dashboard(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    MIN_ATTENDANCE = 1
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    def _safe_pct(n: int, d: int) -> float:
        return round(n / d * 100, 1) if d else 0.0

    # --- Indicator 1: Newly Hired ---
    hired_or_self = (Beneficiary.hired == True) | (Beneficiary.self_employed == True)

    nh_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, hired_or_self)
    )).scalar()
    nh_female = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, hired_or_self, Beneficiary.gender == "female")
    )).scalar()
    wage_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.hired == True)
    )).scalar()
    wage_female = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.hired == True, Beneficiary.gender == "female")
    )).scalar()
    self_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.self_employed == True)
    )).scalar()
    self_female = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.self_employed == True, Beneficiary.gender == "female")
    )).scalar()

    # --- Indicator 2: Employability ---
    employable_filter = (
        exc,
        Beneficiary.skillcraft_score.is_not(None),
        Beneficiary.pathways_completion_rate >= 80,
        Beneficiary.offline_attendance > 8,
    )
    emp_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(*employable_filter)
    )).scalar()
    emp_female = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(*employable_filter, Beneficiary.gender == "female")
    )).scalar()

    # --- Indicator 3: Survey Completion ---
    survey_stats = {}
    for stype in ("phase1", "employment", "entrepreneurship"):
        st = (await db.execute(
            select(func.count(func.distinct(SurveyResponse.beneficiary_id)))
            .where(SurveyResponse.survey_type == stype)
        )).scalar()
        sf = (await db.execute(
            select(func.count(func.distinct(SurveyResponse.beneficiary_id)))
            .select_from(SurveyResponse)
            .join(Beneficiary, SurveyResponse.beneficiary_id == Beneficiary.id)
            .where(SurveyResponse.survey_type == stype, Beneficiary.gender == "female")
        )).scalar()
        survey_stats[stype] = {
            "total": st, "female_count": sf, "female_pct": _safe_pct(sf, st)
        }

    # --- Indicator 4: Phase Beneficiary Counts ---
    p1t = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.selection_status == "selected")
    )).scalar()
    p1f = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.selection_status == "selected", Beneficiary.gender == "female")
    )).scalar()
    p2et = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == "employment")
    )).scalar()
    p2ef = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.track == "employment", Beneficiary.gender == "female")
    )).scalar()
    p2nt = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == "entrepreneurship")
    )).scalar()
    p2nf = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.track == "entrepreneurship", Beneficiary.gender == "female")
    )).scalar()

    # --- Indicator 5: Grant Distribution ---
    grant_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.grant_received == True)
    )).scalar()
    grant_female = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.grant_received == True, Beneficiary.gender == "female")
    )).scalar()
    grant_sum = (await db.execute(
        select(func.coalesce(func.sum(Beneficiary.grant_amount), 0))
        .where(exc, Beneficiary.grant_received == True)
    )).scalar()
    grant_avg = (await db.execute(
        select(func.avg(Beneficiary.grant_amount))
        .where(exc, Beneficiary.grant_received == True, Beneficiary.grant_amount > 0)
    )).scalar()

    # Grant amount distribution buckets
    grant_ranges = [
        (0, 50000, "0-50K"),
        (50000, 100000, "50K-100K"),
        (100000, 200000, "100K-200K"),
        (200000, 500000, "200K-500K"),
        (500000, 1000000, "500K-1M"),
        (1000000, 100000000, "1M+"),
    ]
    grant_distribution = []
    for low, high, label in grant_ranges:
        cnt = (await db.execute(
            select(func.count()).select_from(Beneficiary)
            .where(
                exc,
                Beneficiary.grant_received == True,
                Beneficiary.grant_amount >= low,
                Beneficiary.grant_amount < high,
            )
        )).scalar()
        grant_distribution.append({"range": label, "count": cnt})

    return {
        "newly_hired": {
            "total": nh_total,
            "female_count": nh_female,
            "female_pct": _safe_pct(nh_female, nh_total),
            "wage_employment": {
                "total": wage_total,
                "female_count": wage_female,
                "female_pct": _safe_pct(wage_female, wage_total),
            },
            "self_employment": {
                "total": self_total,
                "female_count": self_female,
                "female_pct": _safe_pct(self_female, self_total),
            },
        },
        "employability": {
            "total": emp_total,
            "female_count": emp_female,
            "female_pct": _safe_pct(emp_female, emp_total),
        },
        "survey_completion": survey_stats,
        "phase_beneficiaries": {
            "phase1": {"total": p1t, "female_count": p1f, "female_pct": _safe_pct(p1f, p1t)},
            "phase2_employment": {"total": p2et, "female_count": p2ef, "female_pct": _safe_pct(p2ef, p2et)},
            "phase2_entrepreneurship": {"total": p2nt, "female_count": p2nf, "female_pct": _safe_pct(p2nf, p2nt)},
        },
        "grants": {
            "total_recipients": grant_total,
            "female_count": grant_female,
            "female_pct": _safe_pct(grant_female, grant_total),
            "total_amount": grant_sum,
            "avg_amount": round(float(grant_avg), 0) if grant_avg else 0,
            "distribution": grant_distribution,
        },
    }
