from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database import get_db
from models.survey import SurveyResponse
from models.beneficiary import Beneficiary
from middleware.auth import require_admin
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/{survey_type}")
async def get_survey_results(
    survey_type: str,
    district: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Get survey responses for a specific survey type with filtering
    """
    # Validate survey type
    valid_types = ['phase1', 'employment', 'entrepreneurship']
    if survey_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid survey type. Must be one of: {valid_types}")

    # Build query
    query = (
        select(SurveyResponse, Beneficiary)
        .join(Beneficiary, SurveyResponse.beneficiary_id == Beneficiary.id)
        .where(SurveyResponse.survey_type == survey_type)
    )

    # Apply filters
    if district:
        query = query.where(Beneficiary.district == district)

    if search:
        query = query.where(
            Beneficiary.name.ilike(f"%{search}%")
        )

    # Get total count
    count_query = select(func.count()).select_from(SurveyResponse).where(
        SurveyResponse.survey_type == survey_type
    )
    if district:
        count_query = count_query.join(Beneficiary).where(Beneficiary.district == district)

    result = await db.execute(count_query)
    total = result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(SurveyResponse.completed_at.desc())
    result = await db.execute(query)
    rows = result.all()

    # Format response
    responses = []
    for survey, beneficiary in rows:
        responses.append({
            "id": str(survey.id),
            "beneficiary": {
                "id": str(beneficiary.id),
                "name": beneficiary.name,
                "age": beneficiary.age,
                "gender": beneficiary.gender,
                "district": beneficiary.district,
            },
            "survey_type": survey.survey_type,
            "responses": survey.responses,
            "completion_time": survey.completion_time,
            "completed_at": survey.completed_at.isoformat() if survey.completed_at else None,
        })

    return {
        "total": total,
        "results": responses,
        "skip": skip,
        "limit": limit
    }


@router.get("/{survey_type}/stats")
async def get_survey_stats(
    survey_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics for a specific survey type
    """
    valid_types = ['phase1', 'employment', 'entrepreneurship']
    if survey_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid survey type. Must be one of: {valid_types}")

    # Total responses
    result = await db.execute(
        select(func.count()).select_from(SurveyResponse)
        .where(SurveyResponse.survey_type == survey_type)
    )
    total_responses = result.scalar()

    # Average completion time
    result = await db.execute(
        select(func.avg(SurveyResponse.completion_time))
        .where(SurveyResponse.survey_type == survey_type)
    )
    avg_time = result.scalar()

    # Total eligible beneficiaries (selected)
    result = await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(Beneficiary.selection_status == 'selected')
    )
    total_eligible = result.scalar()

    # Completion rate
    completion_rate = (total_responses / total_eligible * 100) if total_eligible > 0 else 0

    return {
        "survey_type": survey_type,
        "total_responses": total_responses,
        "total_eligible": total_eligible,
        "completion_rate": round(completion_rate, 1),
        "average_completion_time": round(avg_time) if avg_time else None,
        "average_time_formatted": f"{round(avg_time / 60)} minutes" if avg_time else "N/A"
    }


@router.get("/{survey_type}/{response_id}")
async def get_survey_response(
    survey_type: str,
    response_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single survey response by ID
    """
    result = await db.execute(
        select(SurveyResponse, Beneficiary)
        .join(Beneficiary, SurveyResponse.beneficiary_id == Beneficiary.id)
        .where(
            and_(
                SurveyResponse.id == response_id,
                SurveyResponse.survey_type == survey_type
            )
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Survey response not found")

    survey, beneficiary = row

    return {
        "id": str(survey.id),
        "beneficiary": {
            "id": str(beneficiary.id),
            "name": beneficiary.name,
            "age": beneficiary.age,
            "gender": beneficiary.gender,
            "district": beneficiary.district,
            "education_level": beneficiary.education_level,
            "contact": beneficiary.contact,
        },
        "survey_type": survey.survey_type,
        "responses": survey.responses,
        "completion_time": survey.completion_time,
        "completed_at": survey.completed_at.isoformat() if survey.completed_at else None,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
    }


@router.get("/{survey_type}/export")
async def export_survey_results(
    survey_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Export survey results as CSV
    """
    valid_types = ['phase1', 'employment', 'entrepreneurship']
    if survey_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid survey type. Must be one of: {valid_types}")

    # Get all responses
    result = await db.execute(
        select(SurveyResponse, Beneficiary)
        .join(Beneficiary, SurveyResponse.beneficiary_id == Beneficiary.id)
        .where(SurveyResponse.survey_type == survey_type)
        .order_by(SurveyResponse.completed_at.desc())
    )
    rows = result.all()

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Response ID',
        'Beneficiary Name',
        'Age',
        'Gender',
        'District',
        'Completed At',
        'Completion Time (seconds)',
        'Responses (JSON)'
    ])

    # Write data
    for survey, beneficiary in rows:
        import json
        writer.writerow([
            str(survey.id),
            beneficiary.name,
            beneficiary.age,
            beneficiary.gender,
            beneficiary.district,
            survey.completed_at.isoformat() if survey.completed_at else '',
            survey.completion_time or '',
            json.dumps(survey.responses)
        ])

    # Create response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=survey_{survey_type}_results.csv"
        }
    )


@router.get("/{survey_type}/insights")
async def get_survey_insights(
    survey_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated insights from survey responses
    """
    valid_types = ['phase1', 'employment', 'entrepreneurship']
    if survey_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid survey type. Must be one of: {valid_types}")

    # Get all responses for this survey type
    result = await db.execute(
        select(SurveyResponse.responses)
        .where(SurveyResponse.survey_type == survey_type)
    )
    all_responses = [row[0] for row in result.all()]

    if not all_responses:
        return {"message": "No survey responses found", "insights": []}

    # Aggregate insights (this is a simple example - customize based on your survey structure)
    insights = {}

    # Count responses for each question
    for response in all_responses:
        for question, answer in response.items():
            if question not in insights:
                insights[question] = {}

            # Convert answer to string for counting
            answer_str = str(answer)
            if answer_str not in insights[question]:
                insights[question][answer_str] = 0
            insights[question][answer_str] += 1

    # Format insights
    formatted_insights = []
    for question, answers in insights.items():
        total = sum(answers.values())
        formatted_insights.append({
            "question": question,
            "total_responses": total,
            "distribution": [
                {
                    "answer": answer,
                    "count": count,
                    "percentage": round((count / total) * 100, 1)
                }
                for answer, count in answers.items()
            ]
        })

    return {
        "survey_type": survey_type,
        "total_responses": len(all_responses),
        "insights": formatted_insights
    }
