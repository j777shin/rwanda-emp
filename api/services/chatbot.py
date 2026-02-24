"""
Core chatbot service that manages multi-stage conversations with Mistral API.

The frontend sends the full conversation history with each message. When a
stage is completed (either by the LLM or by the user clicking "Finish Stage"),
the conversation is summarized and both the summary and full conversation are
saved to the ChatbotStage.stage_data field. Previous stage summaries are
injected into the system prompt for continuity.
"""

from datetime import datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotResult, ChatbotStage
from services.chatbot_prompts import STAGES, get_stage_system_prompt

settings = get_settings()


async def initialize_stages(db: AsyncSession, beneficiary_id: UUID) -> list[dict]:
    """Create all 5 chatbot stages for a beneficiary."""
    stages = []
    for stage_config in STAGES:
        existing = await db.execute(
            select(ChatbotStage).where(
                ChatbotStage.beneficiary_id == beneficiary_id,
                ChatbotStage.stage_number == stage_config["number"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        stage = ChatbotStage(
            beneficiary_id=beneficiary_id,
            stage_number=stage_config["number"],
            stage_name=stage_config["name"],
            status="not_started",
        )
        db.add(stage)
        stages.append({
            "stage_number": stage_config["number"],
            "stage_name": stage_config["name"],
            "status": "not_started",
        })

    # Set first stage to in_progress
    first = await db.execute(
        select(ChatbotStage).where(
            ChatbotStage.beneficiary_id == beneficiary_id,
            ChatbotStage.stage_number == 1,
        )
    )
    first_stage = first.scalar_one_or_none()
    if first_stage and first_stage.status == "not_started":
        first_stage.status = "in_progress"
        first_stage.started_at = datetime.utcnow()

    await db.commit()
    return stages


async def get_current_stage(db: AsyncSession, beneficiary_id: UUID) -> ChatbotStage | None:
    """Get the current active stage."""
    result = await db.execute(
        select(ChatbotStage)
        .where(
            ChatbotStage.beneficiary_id == beneficiary_id,
            ChatbotStage.status == "in_progress",
        )
        .order_by(ChatbotStage.stage_number)
    )
    return result.scalar_one_or_none()


async def send_message(
    db: AsyncSession,
    beneficiary_id: UUID,
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    """Process a user message and get AI response.

    conversation_history is provided by the frontend (messages are not persisted).
    """
    # Get current stage
    current_stage = await get_current_stage(db, beneficiary_id)
    if not current_stage:
        return {"error": "No active chatbot stage. All stages may be completed."}

    # Build messages for Mistral API
    system_prompt = get_stage_system_prompt(current_stage.stage_number)

    # Inject the beneficiary's business development goal as context
    ben_result = await db.execute(
        select(Beneficiary).where(Beneficiary.id == beneficiary_id)
    )
    ben = ben_result.scalar_one_or_none()
    if ben and ben.business_development_text:
        system_prompt += (
            "\n\n=== PARTICIPANT'S BUSINESS DEVELOPMENT GOAL ===\n"
            f"{ben.business_development_text}\n"
            "=== END BUSINESS GOAL ===\n"
            "The participant has already written this business development goal. "
            "Acknowledge it, reference it, and build upon it in your conversation. "
            "Do NOT ask them to describe their business idea from scratch — they have already done that. "
            "Instead, ask deeper follow-up questions to refine and strengthen their plan."
        )

    # Inject context from previous completed stages
    previous_context = await _build_previous_stage_context(db, beneficiary_id, current_stage.stage_number)
    if previous_context:
        system_prompt = system_prompt + "\n\n" + previous_context

    api_messages = [{"role": "system", "content": system_prompt}]

    # Use conversation history from frontend
    if conversation_history:
        for msg in conversation_history:
            role = "user" if msg.get("is_user") else "assistant"
            api_messages.append({"role": role, "content": msg.get("message", "")})

    # Add current message
    api_messages.append({"role": "user", "content": user_message})

    # Call Mistral API
    ai_response = await call_llm_api(api_messages)

    # Check if stage is complete
    stage_completed = "[STAGE_COMPLETE]" in ai_response
    chatbot_completed = "[CHATBOT_COMPLETE]" in ai_response

    # Clean markers from displayed response
    clean_response = ai_response.replace("[STAGE_COMPLETE]", "").replace("[CHATBOT_COMPLETE]", "").strip()

    if stage_completed:
        # Summarize the stage conversation and save to stage_data
        full_stage_history = list(conversation_history or [])
        full_stage_history.append({"message": user_message, "is_user": True})
        full_stage_history.append({"message": clean_response, "is_user": False})

        summary = await summarize_stage_conversation(full_stage_history, current_stage.stage_name)

        current_stage.status = "completed"
        current_stage.completed_at = datetime.utcnow()
        current_stage.stage_data = {"summary": summary, "conversation": full_stage_history}

        if not chatbot_completed:
            # Advance to next stage
            next_stage_num = current_stage.stage_number + 1
            next_result = await db.execute(
                select(ChatbotStage).where(
                    ChatbotStage.beneficiary_id == beneficiary_id,
                    ChatbotStage.stage_number == next_stage_num,
                )
            )
            next_stage = next_result.scalar_one_or_none()
            if next_stage:
                next_stage.status = "in_progress"
                next_stage.started_at = datetime.utcnow()

        if chatbot_completed:
            # Generate final report
            await generate_report(db, beneficiary_id, clean_response)

    await db.commit()

    return {
        "response": clean_response,
        "stage_completed": stage_completed,
        "chatbot_completed": chatbot_completed,
        "current_stage": current_stage.stage_number,
        "current_stage_name": current_stage.stage_name,
    }


async def summarize_stage_conversation(
    conversation: list[dict], stage_name: str
) -> str:
    """Summarize a stage's conversation into 1-2 sentences using the LLM."""
    # Build a text representation of the conversation
    lines = []
    for msg in conversation:
        role = "Participant" if msg.get("is_user") else "Mentor"
        lines.append(f"{role}: {msg.get('message', '')}")

    conversation_text = "\n".join(lines)

    summary_messages = [
        {
            "role": "system",
            "content": (
                "You are a summarizer. Given a chatbot conversation from a stage called "
                f'"{stage_name}" in an entrepreneurship mentoring program, '
                "produce a 1-2 sentence summary focusing on what the participant discussed "
                "and the key decisions or insights they shared. Be concise and factual."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this conversation:\n\n{conversation_text}",
        },
    ]

    summary = await call_llm_api(summary_messages)
    return summary.strip()


async def call_llm_api(messages: list[dict]) -> str:
    """Call the OpenAI chat completions API."""
    if not settings.openai_api_key:
        # Fallback mock response for development without API key
        return _mock_response(messages)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.openai_api_url,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500,
            },
        )

        if response.status_code != 200:
            detail = ""
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            print(f"OpenAI API error {response.status_code}: {detail}")
            return f"I'm having trouble connecting right now. Please try again. (Error: {response.status_code}: {detail})"

        data = response.json()
        return data["choices"][0]["message"]["content"]


def _mock_response(messages: list[dict]) -> str:
    """Generate a mock response for development without Mistral API key."""
    user_msg = messages[-1]["content"] if messages else ""
    system_msg = messages[0]["content"] if messages else ""

    # Check if this is a summarization request
    if "summarizer" in system_msg.lower() or "summarize this conversation" in user_msg.lower():
        return "The participant discussed their business idea and shared insights about their target market and goals."

    # Check if this is an assessment generation request (for manual stage 5 finish)
    if "assessment evaluator" in system_msg.lower():
        return """Entrepreneurship Readiness Score: 68/100
Readiness Level: Intermediate

Key Strengths:
- Shows initiative and willingness to learn
- Has identified a potential market need
- Demonstrates basic understanding of business concepts

Areas for Improvement:
- Needs more detailed financial planning
- Should develop competitive analysis further
- Marketing strategy needs refinement

Top 3 Recommendations:
1. Conduct detailed market research in your local area
2. Develop a simple financial projection spreadsheet
3. Connect with local business mentors through Rwanda's BDF"""

    msg_count = len([m for m in messages if m["role"] == "user"])

    # Check if business goal is in the system prompt
    has_goal = "BUSINESS DEVELOPMENT GOAL" in system_msg

    # Determine stage from system prompt
    if "STAGE 1" in system_msg:
        if msg_count >= 5:
            return "That's great! Based on our conversation, your business idea is well thought out. You have a clear understanding of your target market and the problem you're solving. [STAGE_COMPLETE]\n\nLet's move on to analyzing your market in more detail."
        if has_goal:
            prompts = [
                "Welcome! I've read your business development goal and it's a solid foundation. You've already outlined what you want to do, who you're targeting, and your experience. Let's build on that — how do you plan to attract your first paying customers in the early days?",
                "That makes sense. Have you researched how much competitors in your area charge for similar services? How will you set your prices to stay affordable but still profitable?",
                "Good thinking. What is the one thing that could go wrong in the first few months, and how would you handle it?",
                "Looking ahead, you mentioned wanting to hire others and expand. What revenue milestone would you need to hit before you're ready to bring on your first employee?",
                "Last question for this stage — what kind of support or training do you still feel you need before launching?",
            ]
        else:
            prompts = [
                "Welcome! I'm excited to help you develop your business idea. Let's start - what product or service do you want to offer?",
                "That sounds interesting! Who are your target customers? Who would buy this product or service?",
                "Good thinking. What specific problem does your business solve for these customers?",
                "What makes your idea unique or different from what's already available?",
                "Finally, what skills or experience do you bring that will help you succeed in this business?",
            ]
        return prompts[min(msg_count, len(prompts) - 1)]

    elif "STAGE 2" in system_msg:
        if msg_count >= 5:
            return "Excellent market analysis! You've identified key competitors, market size, and potential challenges. [STAGE_COMPLETE]\n\nNow let's work on your business model."
        prompts = [
            "Now let's look at your market. Who are your main competitors in this space?",
            "How large do you think your potential market is? How many customers could you serve?",
            "Describe your ideal customer - their age, location, income level, and habits.",
            "What current trends in Rwanda's market could benefit your business?",
            "What challenges or barriers do you see in entering this market?",
        ]
        return prompts[min(msg_count, len(prompts) - 1)]

    elif "STAGE 3" in system_msg:
        if msg_count >= 5:
            return "Your business model is taking shape. You have clear revenue streams and understand your costs. [STAGE_COMPLETE]\n\nLet's now plan your finances."
        prompts = [
            "Let's design your business model. How will you make money - through sales, services, or subscriptions?",
            "What will your pricing strategy be? How will you set your prices?",
            "What key resources will you need - equipment, workspace, technology, or staff?",
            "Who are your key partners or suppliers? Who will you need to work with?",
            "What are your main costs, both fixed (rent, salaries) and variable (materials, marketing)?",
        ]
        return prompts[min(msg_count, len(prompts) - 1)]

    elif "STAGE 4" in system_msg:
        if msg_count >= 5:
            return "Your financial plan shows good awareness of costs and revenue potential. [STAGE_COMPLETE]\n\nLet's create your action plan to bring this all together."
        prompts = [
            "Time for financial planning. How much money do you estimate you'll need to start?",
            "What will your monthly operating costs be once you're running?",
            "How much revenue do you expect to generate in the first 6 months?",
            "How do you plan to fund your startup? Savings, loans, grants, or investors?",
            "When do you expect to break even - when will revenue cover all your costs?",
        ]
        return prompts[min(msg_count, len(prompts) - 1)]

    elif "STAGE 5" in system_msg:
        if msg_count >= 5:
            return """Congratulations on completing the entrepreneurship assessment!

Here's your final summary:

Entrepreneurship Readiness Score: 72/100
Readiness Level: Intermediate

Key Strengths:
- Clear business idea with identified market need
- Good understanding of target customers
- Realistic financial expectations

Areas for Improvement:
- Develop a more detailed competitive analysis
- Create a more specific marketing strategy
- Build stronger financial projections

Top 3 Recommendations:
1. Start with a minimum viable product to test your market
2. Seek mentorship from established entrepreneurs in your area
3. Apply for youth entrepreneurship grants available in Rwanda

[STAGE_COMPLETE] [CHATBOT_COMPLETE]"""
        prompts = [
            "Let's create your action plan. What are the first 3 concrete steps you'll take to launch?",
            "What's your timeline for the first 6 months? Key dates and goals?",
            "What milestones will you use to track your progress?",
            "What additional support, training, or mentoring do you still need?",
            "Based on everything we've discussed, how ready do you feel to start your business?",
        ]
        return prompts[min(msg_count, len(prompts) - 1)]

    return "Thank you for sharing. Let me help you think through this further."


async def finish_stage(
    db: AsyncSession,
    beneficiary_id: UUID,
    conversation_history: list[dict],
) -> dict:
    """User-initiated stage completion. Saves conversation, summarizes, advances."""
    current_stage = await get_current_stage(db, beneficiary_id)
    if not current_stage:
        return {"error": "No active chatbot stage. All stages may be completed."}

    # Summarize the conversation via LLM
    summary = await summarize_stage_conversation(
        conversation_history, current_stage.stage_name
    )

    # Save full conversation + summary into stage_data
    current_stage.status = "completed"
    current_stage.completed_at = datetime.utcnow()
    current_stage.stage_data = {
        "summary": summary,
        "conversation": conversation_history,
    }

    is_final_stage = current_stage.stage_number == 5
    chatbot_completed = is_final_stage

    if not is_final_stage:
        # Advance to next stage
        next_stage_num = current_stage.stage_number + 1
        next_result = await db.execute(
            select(ChatbotStage).where(
                ChatbotStage.beneficiary_id == beneficiary_id,
                ChatbotStage.stage_number == next_stage_num,
            )
        )
        next_stage = next_result.scalar_one_or_none()
        if next_stage:
            next_stage.status = "in_progress"
            next_stage.started_at = datetime.utcnow()
    else:
        # For stage 5, generate the final report from all stage data
        report_response = await _generate_assessment_from_history(db, beneficiary_id)
        await generate_report(db, beneficiary_id, report_response)

    await db.commit()

    return {
        "stage_completed": True,
        "chatbot_completed": chatbot_completed,
        "completed_stage": current_stage.stage_number,
        "completed_stage_name": current_stage.stage_name,
    }


async def _build_previous_stage_context(
    db: AsyncSession,
    beneficiary_id: UUID,
    current_stage_number: int,
) -> str:
    """Build context string from all completed previous stages."""
    if current_stage_number <= 1:
        return ""

    result = await db.execute(
        select(ChatbotStage)
        .where(
            ChatbotStage.beneficiary_id == beneficiary_id,
            ChatbotStage.stage_number < current_stage_number,
            ChatbotStage.status == "completed",
        )
        .order_by(ChatbotStage.stage_number)
    )
    previous_stages = result.scalars().all()

    if not previous_stages:
        return ""

    parts = [
        "=== BACKGROUND CONTEXT FROM PREVIOUS STAGES (do NOT repeat this to the user) ==="
    ]
    for stage in previous_stages:
        if stage.stage_data:
            summary = stage.stage_data.get("summary", "")
            if summary:
                parts.append(f"Stage {stage.stage_number} ({stage.stage_name}): {summary}")

    parts.append(
        "=== END BACKGROUND CONTEXT ===\n\n"
        "Use this context to personalize your questions and advice, "
        "but do not tell the user you have this information."
    )
    return "\n".join(parts)


async def _generate_assessment_from_history(
    db: AsyncSession,
    beneficiary_id: UUID,
) -> str:
    """Generate a final assessment report from all stage summaries when user finishes stage 5 manually."""
    all_stages = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == beneficiary_id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = all_stages.scalars().all()

    context_parts = []
    for s in stages:
        if s.stage_data:
            summary = s.stage_data.get("summary", "")
            if summary:
                context_parts.append(f"Stage {s.stage_number} ({s.stage_name}): {summary}")

    context_text = "\n".join(context_parts)

    assessment_messages = [
        {
            "role": "system",
            "content": (
                "You are an entrepreneurship assessment evaluator for a youth employment program in Rwanda. "
                "Based on the following stage summaries from a multi-stage mentoring conversation, provide:\n"
                "- An entrepreneurship readiness score from 1-100\n"
                "- A readiness level: Beginner, Intermediate, or Advanced\n"
                "- Key strengths identified\n"
                "- Areas for improvement\n"
                "- Top 3 recommendations\n\n"
                "Format the score as 'XX/100' so it can be parsed."
            ),
        },
        {
            "role": "user",
            "content": f"Here are the stage summaries:\n\n{context_text}\n\nProvide the final assessment.",
        },
    ]

    return await call_llm_api(assessment_messages)


async def go_to_stage(
    db: AsyncSession,
    beneficiary_id: UUID,
    target_stage_number: int,
) -> dict:
    """Reset to a previous stage so the user can redo it.

    - The target stage is set to ``in_progress`` (its stage_data is cleared).
    - All stages after it are reset to ``not_started``.
    - Stages before it keep their data (summaries remain as LLM context).
    - Any existing ChatbotResult is deleted since the assessment is no longer valid.
    """
    if target_stage_number < 1 or target_stage_number > 5:
        return {"error": "Invalid stage number."}

    # Load all stages
    result = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == beneficiary_id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = result.scalars().all()
    if not stages:
        return {"error": "No stages found."}

    previous_conversation: list[dict] = []

    for stage in stages:
        if stage.stage_number == target_stage_number:
            # Keep the old conversation so we can return it to the frontend
            if stage.stage_data:
                previous_conversation = stage.stage_data.get("conversation", [])
            stage.status = "in_progress"
            stage.started_at = datetime.utcnow()
            stage.completed_at = None
            stage.stage_data = None
        elif stage.stage_number > target_stage_number:
            stage.status = "not_started"
            stage.started_at = None
            stage.completed_at = None
            stage.stage_data = None

    # Delete any existing report
    existing_report = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == beneficiary_id)
    )
    report = existing_report.scalar_one_or_none()
    if report:
        await db.delete(report)

    await db.commit()

    return {
        "success": True,
        "current_stage": target_stage_number,
        "previous_conversation": previous_conversation,
    }


async def generate_report(db: AsyncSession, beneficiary_id: UUID, final_response: str) -> None:
    """Generate a chatbot result report from the final stage response."""
    # Extract score from response (look for patterns like "72/100" or "Score: 72")
    import re
    score_match = re.search(r"(\d{1,3})/100", final_response)
    score = float(score_match.group(1)) if score_match else 65.0

    # Determine readiness level
    if score >= 80:
        readiness = "Advanced"
    elif score >= 60:
        readiness = "Intermediate"
    else:
        readiness = "Beginner"

    # Check if report already exists
    existing = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == beneficiary_id)
    )
    result = existing.scalar_one_or_none()

    if result:
        result.entrepreneurship_score = score
        result.readiness_level = readiness
        result.summary = final_response
        result.recommendations = "See summary for detailed recommendations."
    else:
        result = ChatbotResult(
            beneficiary_id=beneficiary_id,
            entrepreneurship_score=score,
            readiness_level=readiness,
            summary=final_response,
            recommendations="See summary for detailed recommendations.",
        )
        db.add(result)
