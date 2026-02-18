from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.beneficiary import Beneficiary
from services.pmt_scoring import calculate_pmt_score


async def calculate_all_pmt_scores(db: AsyncSession) -> dict:
    """Calculate PMT scores for all beneficiaries and store as eligibility_score."""
    result = await db.execute(select(Beneficiary))
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
        ben.eligibility_score = pmt_score
        count += 1

    await db.commit()
    return {"scored": count}


async def select_phase1_beneficiaries(db: AsyncSession, count: int = 9000) -> dict:
    """Select top N most vulnerable beneficiaries (lowest PMT scores) for Phase 1."""
    # Get all pending beneficiaries ordered by PMT score (ascending = most vulnerable first)
    result = await db.execute(
        select(Beneficiary)
        .where(Beneficiary.selection_status == "pending")
        .where(Beneficiary.eligibility_score.is_not(None))
        .order_by(Beneficiary.eligibility_score.asc())
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
