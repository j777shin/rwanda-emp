"""
Core chatbot service that manages multi-stage conversations with Mistral API.

Chat history is NOT persisted to the database. The frontend sends the full
conversation history with each message. When a stage is completed, the
conversation is summarized by the LLM and the summary is saved to the
ChatbotStage.stage_data field.
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
    api_messages = [{"role": "system", "content": system_prompt}]

    # Use conversation history from frontend
    if conversation_history:
        for msg in conversation_history:
            role = "user" if msg.get("is_user") else "assistant"
            api_messages.append({"role": role, "content": msg.get("message", "")})

    # Add current message
    api_messages.append({"role": "user", "content": user_message})

    # Call Mistral API
    ai_response = await call_mistral_api(api_messages)

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
        current_stage.stage_data = {"summary": summary}

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

    summary = await call_mistral_api(summary_messages)
    return summary.strip()


async def call_mistral_api(messages: list[dict]) -> str:
    """Call the Mistral AI API."""
    if not settings.mistral_api_key:
        # Fallback mock response for development without API key
        return _mock_response(messages)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.mistral_api_url,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.mistral_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500,
            },
        )

        if response.status_code != 200:
            return f"I'm having trouble connecting right now. Please try again. (Error: {response.status_code})"

        data = response.json()
        return data["choices"][0]["message"]["content"]


def _mock_response(messages: list[dict]) -> str:
    """Generate a mock response for development without Mistral API key."""
    user_msg = messages[-1]["content"] if messages else ""
    system_msg = messages[0]["content"] if messages else ""

    # Check if this is a summarization request
    if "summarizer" in system_msg.lower() or "summarize this conversation" in user_msg.lower():
        return "The participant discussed their business idea and shared insights about their target market and goals."

    msg_count = len([m for m in messages if m["role"] == "user"])

    # Determine stage from system prompt
    if "STAGE 1" in system_msg:
        if msg_count >= 5:
            return "That's great! Based on our conversation, your business idea is well thought out. You have a clear understanding of your target market and the problem you're solving. [STAGE_COMPLETE]\n\nLet's move on to analyzing your market in more detail."
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
