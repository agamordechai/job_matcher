# Job Matcher

An intelligent job matching system that automatically fetches job postings from LinkedIn and other job boards, matches them against your CV using AI, and sends email notifications for relevant opportunities.

## ✨ Features

- **CV Management**: Upload and manage your CV (PDF/DOCX format)
- **Job Fetching**: Automated job fetching from LinkedIn via JSearch API (can also search Indeed, Glassdoor)
- **AI Matching**: Smart job matching using Claude AI (Phase 4 - Coming Soon)
- **Filtering**: Customizable search filters (keywords, location, job type, experience level)
- **Scheduling**: Automated job fetching with configurable intervals (default: every 8 hours)
- **Email Notifications**: Get notified about high-match jobs (Phase 6 - Coming Soon)
- **Deduplication**: Automatic duplicate job detection
- **Rich Data**: Full job details including salary, requirements, description, and direct application links

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker Desktop installed and running
- RapidAPI account with JSearch API subscription (free tier available)

### Setup Steps

1. **Get your RapidAPI key**:
   - Sign up at [RapidAPI](https://rapidapi.com/)
   - Subscribe to [JSearch API](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) (FREE tier: 150 requests/month)
   - Copy your API key

2. **Configure environment**:
   ```bash
   # Edit .env file and add your API key
   RAPIDAPI_KEY=your_actual_rapidapi_key_here
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Upload CV and create filter**:
   ```bash
   # Upload CV
   curl -X POST "http://localhost:8000/api/cv/upload" -F "file=@cv.pdf"
   
   # Create default filter
   curl -X POST "http://localhost:8000/api/filters/default"
   
   # Trigger job fetch
   curl -X POST "http://localhost:8000/api/scheduler/trigger"
   
   # View jobs
   curl "http://localhost:8000/api/jobs/" | jq
   ```

5. **Access API docs**: Open http://localhost:8000/docs

---

## 📋 Detailed Setup

### For Docker Setup (Recommended)
- **Docker**: [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Docker Compose**: Included with Docker Desktop

### For Local Development
- **Python 3.12 or higher**: [Download Python](https://www.python.org/downloads/)
- **UV Package Manager**: Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker** (for PostgreSQL and Redis): [Install Docker Desktop](https://www.docker.com/products/docker-desktop)

## Installation

### Using Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd job_matcher
   ```

2. **Set up environment variables**:
   
   The `.env` file should already exist. If not, create it from the example:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```bash
   # Required: Add your RapidAPI key for job fetching
   # Sign up at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
   # Subscribe to JSearch API (free tier: 150 requests/month)
   RAPIDAPI_KEY=your_rapidapi_key_here
   RAPIDAPI_HOST=jsearch.p.rapidapi.com
   
   # Optional: Add your Anthropic API key for AI matching (Phase 4)
   ANTHROPIC_API_KEY=your_actual_api_key_here
   
   # Optional: Configure email notifications (Phase 6)
   SMTP_USER=your_email@gmail.com
   SMTP_PASS=your_app_password
   NOTIFICATION_EMAIL=your_email@gmail.com
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```
   
   This will start:
   - PostgreSQL database
   - Redis cache
   - FastAPI application
   - Celery worker
   - Celery beat scheduler

4. **Check service health**:
   ```bash
   curl http://localhost:8000/api/health
   ```
   
   You should see:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "redis": "connected",
     "timestamp": "..."
   }
   ```

5. **Access API documentation**:
   
   Open http://localhost:8000/docs in your browser for interactive API docs

6. **View logs** (if needed):
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f app
   docker-compose logs -f celery_worker
   ```

7. **Stop services**:
   ```bash
   docker-compose down
   ```

### Local Development (without Docker)

This approach runs the FastAPI app locally but uses Docker for PostgreSQL and Redis.

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Add UV to PATH (for zsh on macOS)
   echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

2. **Install dependencies**:
   ```bash
   # This creates a virtual environment and installs all dependencies
   uv sync
   
   # Activate the virtual environment
   source .venv/bin/activate
   ```

3. **Start PostgreSQL and Redis** (via Docker):
   ```bash
   docker-compose up -d postgres redis
   
   # Verify they're running
   docker-compose ps
   ```

4. **Run the application**:
   ```bash
   # Make sure the virtual environment is activated
   source .venv/bin/activate
   
   # Start the FastAPI server
   uvicorn app.main:app --reload --port 8000
   ```
   
   The application will be available at http://localhost:8000

5. **Run Celery worker** (in a new terminal):
   ```bash
   cd /path/to/job_matcher
   source .venv/bin/activate
   celery -A app.celery_worker worker --loglevel=info
   ```

6. **Run Celery beat** (in another terminal):
   ```bash
   cd /path/to/job_matcher
   source .venv/bin/activate
   celery -A app.celery_worker beat --loglevel=info
   ```

## 🔑 API Configuration

### Required API Keys

#### 1. RapidAPI Key (Required - Job Fetching)

**Get your key**:
1. Sign up at [RapidAPI](https://rapidapi.com/)
2. Subscribe to [JSearch API](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
3. Choose the **Basic plan** (FREE - 150 requests/month)
4. Copy your API key from the code snippet

**Add to `.env`**:
```bash
RAPIDAPI_KEY=your_actual_rapidapi_key_here
RAPIDAPI_HOST=jsearch.p.rapidapi.com
```

**Free Tier Limits**:
- 150 requests per month (~5 per day)
- Each request can fetch up to 10 jobs
- Sufficient for testing and moderate usage

#### 2. Anthropic API Key (Optional - AI Matching - Phase 4)

**Get your key**:
1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Create an API key (starts with `sk-ant-`)

**Add to `.env`**:
```bash
ANTHROPIC_API_KEY=your_actual_anthropic_key_here
```

#### 3. Email Configuration (Optional - Notifications - Phase 6)

**For Gmail**:
1. Enable 2-factor authentication
2. Generate an [App Password](https://myaccount.google.com/apppasswords)

**Add to `.env`**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_16_char_app_password
NOTIFICATION_EMAIL=your_email@gmail.com
```

### Job Search Configuration

Customize job search filters in `.env`:

```bash
# Job titles to search for (comma-separated)
SEARCH_KEYWORDS=Software Engineer,Backend Developer,Full Stack Engineer

# Location
SEARCH_LOCATION=United States

# Job type (full-time, part-time, contract, internship)
SEARCH_JOB_TYPE=full-time

# Experience level (internship, entry, mid, senior, lead)
SEARCH_EXPERIENCE_LEVEL=mid

# Remote only jobs (true/false)
SEARCH_REMOTE_ONLY=false

# Date posted filter (all, today, 3days, week, month)
SEARCH_DATE_POSTED=week

# Fetch interval (minutes, default: 480 = 8 hours)
FETCH_INTERVAL_MINUTES=480
```

## 📚 API Endpoints

### System
- `GET /api/health` - Health check (database and Redis status)
- `GET /` - Root endpoint with API information

### CV Management
- `POST /api/cv/upload` - Upload CV (PDF/DOCX)
- `GET /api/cv/` - Get active CV
- `GET /api/cv/all` - Get all CVs
- `PUT /api/cv/summary` - Update CV summary
- `DELETE /api/cv/{id}` - Delete CV

### Job Management
- `GET /api/jobs/` - List jobs (with filters)
- `GET /api/jobs/{id}` - Get job details
- `GET /api/jobs/top/matches` - Get top matching jobs
- `GET /api/jobs/stats/summary` - Get job statistics
- `PUT /api/jobs/{id}/notified` - Mark as notified
- `DELETE /api/jobs/{id}` - Delete job

### Search Filters
- `GET /api/filters/` - Get all filters
- `GET /api/filters/{id}` - Get filter by ID
- `POST /api/filters/` - Create filter
- `POST /api/filters/default` - Create filter from .env defaults
- `PUT /api/filters/{id}` - Update filter
- `DELETE /api/filters/{id}` - Delete filter

### Scheduler
- `POST /api/scheduler/trigger` - Trigger job fetch manually
- `GET /api/scheduler/status` - Get scheduler status
- `PUT /api/scheduler/config` - Update scheduler configuration

## 🎯 Usage Examples

### 1. Upload Your CV

```bash
curl -X POST "http://localhost:8000/api/cv/upload" \
  -F "file=@/path/to/your/cv.pdf"
```

Or use the interactive API docs at http://localhost:8000/docs

### 2. Create a Search Filter

**Option A: Use defaults from `.env`**:
```bash
curl -X POST "http://localhost:8000/api/filters/default"
```

**Option B: Create custom filter**:
```bash
curl -X POST "http://localhost:8000/api/filters/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Backend Jobs - Remote",
    "keywords": ["Software Engineer", "Backend Developer"],
    "location": "United States",
    "remote_only": true,
    "is_active": true
  }'
```

### 3. Fetch Jobs

**Manual trigger**:
```bash
curl -X POST "http://localhost:8000/api/scheduler/trigger"
```

**Automatic**: Jobs are fetched automatically based on `FETCH_INTERVAL_MINUTES` (default: 8 hours)

Watch the logs:
```bash
docker-compose logs -f celery_worker
```

### 4. View Jobs

**List all jobs**:
```bash
curl "http://localhost:8000/api/jobs/" | jq
```

**Filter by score**:
```bash
curl "http://localhost:8000/api/jobs/?score=high" | jq
```

**Top matches**:
```bash
curl "http://localhost:8000/api/jobs/top/matches?limit=10" | jq
```

**Statistics**:
```bash
curl "http://localhost:8000/api/jobs/stats/summary" | jq
```

### 5. Manage Filters

**List filters**:
```bash
curl "http://localhost:8000/api/filters/"
```

**Update filter**:
```bash
curl -X PUT "http://localhost:8000/api/filters/1" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

**Delete filter**:
```bash
curl -X DELETE "http://localhost:8000/api/filters/1"
```

## 🔧 Troubleshooting

### Job Fetching Issues

1. **"No active search filters found" - Job fetch skipped**
   
   **Solution**: Create a filter first:
   ```bash
   curl -X POST "http://localhost:8000/api/filters/default"
   ```

2. **"403 Forbidden" or "You are not subscribed to this API"**
   
   **Causes**:
   - Not subscribed to JSearch API on RapidAPI
   - Invalid API key in `.env`
   - API key not loaded (need restart)
   
   **Solution**:
   ```bash
   # 1. Verify subscription at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
   # 2. Check RAPIDAPI_KEY in .env file
   # 3. Restart services
   docker-compose restart
   ```

3. **"429 Too Many Requests" - Rate limited**
   
   **Free tier limits**: 150 requests/month (~5/day)
   
   **Solution**:
   - Wait for rate limit to reset (check RapidAPI dashboard)
   - Increase fetch interval: `FETCH_INTERVAL_MINUTES=720` (12 hours)
   - Monitor usage at https://rapidapi.com/developer/dashboard

4. **No jobs returned (0 fetched)**
   
   **Possible causes**:
   - Keywords too specific (try "Software Engineer" instead of "Senior React Redux Engineer")
   - Location too narrow (try "United States" or "Remote")
   - Too many filters applied
   - No LinkedIn jobs match criteria
   
   **Solution**:
   ```bash
   # Try minimal filter
   curl -X POST "http://localhost:8000/api/filters/" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test",
       "keywords": ["Software Engineer"],
       "location": "United States",
       "remote_only": true,
       "is_active": true
     }'
   ```

5. **"Job already exists" warnings**
   
   This is normal! The system automatically prevents duplicates.

### Service Issues

1. **Port already in use**:
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Kill the process or use a different port
   uvicorn app.main:app --port 8001
   ```

2. **Database connection errors**:
   ```bash
   # Ensure PostgreSQL is running
   docker-compose ps postgres
   
   # Check PostgreSQL logs
   docker-compose logs postgres
   
   # Restart PostgreSQL
   docker-compose restart postgres
   ```

3. **Redis connection errors**:
   ```bash
   # Ensure Redis is running
   docker-compose ps redis
   
   # Test Redis connection
   docker-compose exec redis redis-cli ping
   ```

4. **Import errors or missing dependencies**:
   ```bash
   # Reinstall dependencies
   uv sync --reinstall
   
   # Or manually reinstall
   uv pip install --reinstall -e .
   ```

5. **"No active CV found" errors**:
   - Upload a CV via the API: `POST /api/cv/upload`
   - Or use the interactive docs at http://localhost:8000/docs

6. **Docker build issues**:
   ```bash
   # Rebuild without cache
   docker-compose build --no-cache
   
   # Remove old containers and volumes
   docker-compose down -v
   docker-compose up -d
   ```

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f app
docker-compose logs -f celery_worker
docker-compose logs -f postgres

# Local development
# Logs are printed to the terminal where you ran uvicorn/celery
```

## 💡 Tips & Best Practices

### Optimizing Job Search

1. **Use broad keywords**: "Software Engineer" > "Senior Full Stack React Engineer"
2. **Test filters manually**: Use RapidAPI playground to verify queries work
3. **Start with remote jobs**: More results, easier to match
4. **Monitor your quota**: Check RapidAPI dashboard regularly
5. **Adjust frequency**: Start with 8-12 hour intervals

### Filter Examples

**Remote Python Developer**:
```json
{
  "name": "Python Remote",
  "keywords": ["Python Developer", "Backend Engineer"],
  "location": "United States",
  "remote_only": true,
  "is_active": true
}
```

**Senior Frontend - New York**:
```json
{
  "name": "Senior Frontend NYC",
  "keywords": ["Frontend Engineer", "React Developer"],
  "location": "New York, NY",
  "experience_level": "senior",
  "job_type": "full-time",
  "is_active": true
}
```

**Entry Level Data Analyst**:
```json
{
  "name": "Entry Data Analyst",
  "keywords": ["Data Analyst", "Business Analyst"],
  "location": "Remote",
  "experience_level": "entry",
  "remote_only": true,
  "is_active": true
}
```

## 📝 Important Notes

### LinkedIn-Only Configuration

By default, the system is configured to **only search LinkedIn** for jobs. This provides the most reliable results.

To enable other job boards (Indeed, Glassdoor), see `app/services/jsearch_service.py` and modify the `google_domain` parameter.

### API Rate Limits

**Free Tier**: 150 requests/month (~5 per day)
- Each search filter = 1 request per fetch cycle
- Default: 3 filters × 3 fetches/day = 9 requests/day ⚠️ Too much!
- Recommended: 1-2 filters with `FETCH_INTERVAL_MINUTES=480` (8 hours)

**Monitor usage**: https://rapidapi.com/developer/dashboard

## 🗺️ Development Roadmap

- [x] **Phase 1**: Setup & Core Infrastructure
- [x] **Phase 2**: CV Management
- [x] **Phase 3**: Job Fetching (JSearch API - LinkedIn integration)
- [ ] **Phase 4**: AI Matching with Claude (Coming Soon)
- [x] **Phase 5**: Scheduling & Automation (Basic setup complete)
- [ ] **Phase 6**: Email Notifications (Coming Soon)
- [ ] **Phase 7**: Testing & Documentation
- [ ] **Phase 8**: Deployment

## 📂 Project Structure

```
job_matcher/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── celery_worker.py     # Celery tasks
│   ├── routers/             # API endpoints
│   │   ├── cv.py           # CV management
│   │   ├── jobs.py         # Job endpoints
│   │   ├── filters.py      # Filter management
│   │   ├── scheduler.py    # Scheduler control
│   │   └── system.py       # System health
│   ├── services/            # Business logic
│   │   ├── cv_service.py
│   │   ├── job_service.py
│   │   ├── jsearch_service.py
│   │   ├── filter_service.py
│   │   └── scheduler_service.py
│   └── utils/               # Utility functions
│       └── file_parser.py
├── storage/
│   ├── cvs/                 # Uploaded CV files
│   └── temp/                # Temporary files
├── docker-compose.yml       # Docker services configuration
├── Dockerfile               # Application container
├── pyproject.toml           # Python dependencies
├── .env                     # Environment variables (create this)
└── README.md                # This file
```

## 💾 Database Schema

The application uses PostgreSQL with the following main tables:
- `cvs` - CV storage with parsed content
- `jobs` - Job postings with match scores
- `search_filters` - Job search criteria
- `scheduler_config` - Scheduler settings
- `notification_logs` - Email notification history

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📄 License

MIT License

---

**Last Updated**: November 2025  
**Version**: Phase 3 Complete

