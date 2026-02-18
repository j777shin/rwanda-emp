from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from routes.auth import router as auth_router
from routes.admin.beneficiaries import router as admin_beneficiaries_router
from routes.admin.accounts import router as admin_accounts_router
from routes.admin.registration import router as admin_registration_router
from routes.admin.selection import router as admin_selection_router
from routes.admin.analytics import router as admin_analytics_router
from routes.admin.chatbot_analytics import router as admin_chatbot_analytics_router
from routes.admin.phase_dashboards import router as admin_phase_dashboards_router
from routes.admin.surveys import router as admin_surveys_router
from routes.admin.sync import router as admin_sync_router
from routes.beneficiary.skillcraft import router as beneficiary_skillcraft_router
from routes.beneficiary.pathways import router as beneficiary_pathways_router
from routes.beneficiary.business_dev import router as beneficiary_business_dev_router
from routes.beneficiary.chatbot import router as beneficiary_chatbot_router
from routes.beneficiary.surveys import router as beneficiary_surveys_router
from routes.beneficiary.dashboard import router as beneficiary_dashboard_router

settings = get_settings()

app = FastAPI(title="Rwanda Youth Training MVP", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Admin routes
app.include_router(admin_beneficiaries_router, prefix="/admin/beneficiaries", tags=["Admin - Beneficiaries"])
app.include_router(admin_accounts_router, prefix="/admin/accounts", tags=["Admin - Accounts"])
app.include_router(admin_registration_router, prefix="/admin/registration", tags=["Admin - Registration"])
app.include_router(admin_selection_router, prefix="/admin/selection", tags=["Admin - Selection"])
app.include_router(admin_analytics_router, prefix="/admin/analytics", tags=["Admin - Analytics"])
app.include_router(admin_chatbot_analytics_router, prefix="/admin/chatbot", tags=["Admin - Chatbot Analytics"])
app.include_router(admin_phase_dashboards_router, prefix="/admin", tags=["Admin - Phase Dashboards"])
app.include_router(admin_surveys_router, prefix="/admin/surveys", tags=["Admin - Surveys"])
app.include_router(admin_sync_router, prefix="/admin/sync", tags=["Admin - Sync"])

# Beneficiary routes
app.include_router(beneficiary_dashboard_router, prefix="/beneficiary/dashboard", tags=["Beneficiary - Dashboard"])
app.include_router(beneficiary_skillcraft_router, prefix="/beneficiary/skillcraft", tags=["Beneficiary - SkillCraft"])
app.include_router(beneficiary_pathways_router, prefix="/beneficiary/pathways", tags=["Beneficiary - Pathways"])
app.include_router(beneficiary_business_dev_router, prefix="/beneficiary/business-dev", tags=["Beneficiary - Business Dev"])
app.include_router(beneficiary_chatbot_router, prefix="/beneficiary/chatbot", tags=["Beneficiary - Chatbot"])
app.include_router(beneficiary_surveys_router, prefix="/beneficiary/surveys", tags=["Beneficiary - Surveys"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
