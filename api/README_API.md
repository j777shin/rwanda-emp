# Rwanda Employment API Server

FastAPI backend for the Rwanda Youth Training and Employment Platform.

## 🚀 Quick Start

### Option 1: Automated Startup (Recommended)

```bash
cd /Users/j777shin/code/rwanda/rwanda-emp/api
./start_api.sh
```

The script will:
1. ✓ Check Python version
2. ✓ Set up virtual environment
3. ✓ Install dependencies
4. ✓ Create .env file (if needed)
5. ✓ Verify database connection
6. ✓ Start the API server on port 8000

### Option 2: Manual Startup

```bash
cd /Users/j777shin/code/rwanda/rwanda-emp/api

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Create .env file (first time only)
cp .env.example .env
# Edit .env with your settings

# Start server
uvicorn main:app --reload --port 8000
```

## 📋 Prerequisites

1. **PostgreSQL** installed and running
   ```bash
   brew services start postgresql@15
   ```

2. **Database** initialized with data
   ```bash
   cd ../data
   python load_data_to_db.py
   python create_test_accounts.sh
   ```

3. **Python 3.11+** installed

## ⚙️ Configuration

Edit `.env` file with your settings:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=              # Empty for Homebrew PostgreSQL
DB_NAME=rwanda_emp

# JWT Authentication
JWT_SECRET=your-secret-key-here-change-in-production
JWT_EXPIRY_HOURS=24

# AI Chatbot (Optional)
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest

# Frontend
FRONTEND_URL=http://localhost:5173
```

### Generate JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📚 API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Login

```bash
# Admin login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@rwanda.gov.rw", "password": "Admin@2024"}'

# Beneficiary login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test.beneficiary@gmail.com", "password": "Beneficiary@2024"}'
```

Response:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "...",
    "email": "...",
    "role": "admin"
  }
}
```

### Using the Token

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🛣️ API Routes

### Authentication
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user

### Admin Routes
- `GET /admin/beneficiaries` - List all beneficiaries
- `GET /admin/beneficiaries/{id}` - Get beneficiary details
- `POST /admin/registration/upload` - Upload bulk registration
- `GET /admin/selection/eligible` - Get eligible beneficiaries
- `POST /admin/selection/select` - Select beneficiaries
- `GET /admin/analytics/overview` - Dashboard analytics
- `GET /admin/analytics/export` - Export data as PDF

### Beneficiary Routes
- `GET /beneficiary/dashboard` - Beneficiary dashboard
- `GET /beneficiary/skillcraft/status` - SkillCraft status
- `POST /beneficiary/skillcraft/sync` - Sync SkillCraft data
- `GET /beneficiary/pathways/status` - Pathways status
- `POST /beneficiary/pathways/sync` - Sync Pathways data
- `POST /beneficiary/chatbot/message` - Send chatbot message
- `GET /beneficiary/chatbot/result` - Get entrepreneurship assessment

## 🗄️ Database

The API uses PostgreSQL with async SQLAlchemy.

### Connection
- **Host**: localhost
- **Port**: 5432
- **Database**: rwanda_emp
- **User**: postgres

### Check Connection

```bash
# Via psql
psql -h localhost -U postgres -d rwanda_emp -c "SELECT COUNT(*) FROM users;"

# Via Python
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://postgres@localhost/rwanda_emp'))"
```

## 🧪 Testing

### Health Check

```bash
curl http://localhost:8000/
```

Expected response:
```json
{"message": "Rwanda Youth Training API"}
```

### Test Login

```bash
# Admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@rwanda.gov.rw","password":"Admin@2024"}'

# Beneficiary
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test.beneficiary@gmail.com","password":"Beneficiary@2024"}'
```

## 🐛 Troubleshooting

### Port 8000 already in use

```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --reload --port 8001
```

### Database connection error

```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Start PostgreSQL
brew services start postgresql@15

# Test connection
psql -h localhost -U postgres -l
```

### ModuleNotFoundError

```bash
# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### CORS errors in frontend

Make sure `FRONTEND_URL` in `.env` matches your frontend URL:
```bash
FRONTEND_URL=http://localhost:5173
```

## 📝 Development

### Project Structure

```
api/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration and settings
├── database.py            # Database connection and session
├── models/                # SQLAlchemy models
│   ├── user.py
│   ├── beneficiary.py
│   └── chatbot.py
├── routes/                # API route handlers
│   ├── auth.py
│   ├── admin/
│   └── beneficiary/
├── services/              # Business logic
│   ├── chatbot.py
│   ├── skillcraft.py
│   └── pathways.py
├── middleware/            # Authentication middleware
└── utils/                 # Helper functions
```

### Adding New Routes

1. Create route handler in `routes/`
2. Import in `main.py`
3. Include router with prefix and tags

Example:
```python
# routes/new_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_feature():
    return {"message": "New feature"}

# main.py
from routes.new_feature import router as new_feature_router
app.include_router(new_feature_router, prefix="/new-feature", tags=["New Feature"])
```

## 🔒 Security

- ✅ JWT authentication
- ✅ Password hashing with bcrypt
- ✅ CORS protection
- ✅ SQL injection prevention (SQLAlchemy)
- ⚠️ Change `JWT_SECRET` in production
- ⚠️ Use HTTPS in production
- ⚠️ Set strong database passwords

## 📊 Monitoring

### Logs

The API logs all requests with uvicorn's built-in logging.

```bash
# View logs in real-time
tail -f logs/api.log  # If log file is configured
```

### Performance

Monitor with:
```bash
# Check server status
curl http://localhost:8000/

# Response time
time curl http://localhost:8000/auth/me -H "Authorization: Bearer TOKEN"
```

## 🚀 Production Deployment

For production deployment:

1. Set environment variables securely
2. Use production ASGI server (Gunicorn + Uvicorn workers)
3. Enable HTTPS
4. Set up database connection pooling
5. Configure logging
6. Set up monitoring (e.g., Sentry)
7. Use reverse proxy (nginx)

Example production command:
```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile -
```

## 📞 Support

- Check API documentation: http://localhost:8000/docs
- Review test credentials: `/data/TEST_CREDENTIALS.md`
- Database setup guide: `/data/README.md`
