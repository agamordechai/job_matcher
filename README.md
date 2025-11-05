# Job Matcher

An intelligent job matching system that automatically fetches job postings, matches them against your CV using AI, and sends email notifications for relevant opportunities.

## Features

- **CV Management**: Upload and manage your CV (PDF/DOCX format)
- **Job Fetching**: Automated scraping of job boards (LinkedIn, Drushim, etc.)
- **AI Matching**: Smart job matching using Claude AI
- **Filtering**: Customizable search filters (keywords, location, salary, etc.)
- **Scheduling**: Automated job fetching with configurable intervals
- **Email Notifications**: Get notified about matching jobs

## Prerequisites

Before you begin, ensure you have the following installed:

### For Docker Setup (Recommended)
- **Docker**: [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Docker Compose**: Included with Docker Desktop

### For Local Development
- **Python 3.12 or higher**: [Download Python](https://www.python.org/downloads/)
- **UV Package Manager**: Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker** (for PostgreSQL and Redis): [Install Docker Desktop](https://www.docker.com/products/docker-desktop)

## Quick Start

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
   # Required: Add your Anthropic API key for AI matching
   ANTHROPIC_API_KEY=your_actual_api_key_here
   
   # Optional: Configure email notifications
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

## API Endpoints

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
- `PUT /api/jobs/{id}/notified` - Mark as notified
- `DELETE /api/jobs/{id}` - Delete job

### Search Filters
- `GET /api/filters/` - Get all filters
- `GET /api/filters/{id}` - Get filter by ID
- `POST /api/filters/` - Create filter
- `PUT /api/filters/{id}` - Update filter
- `DELETE /api/filters/{id}` - Delete filter

### Scheduler
- `POST /api/scheduler/trigger` - Trigger job fetch manually
- `GET /api/scheduler/status` - Get scheduler status
- `PUT /api/scheduler/config` - Update scheduler configuration

## Database Schema

The application uses PostgreSQL with the following main tables:
- `cvs` - CV storage with parsed content
- `jobs` - Job postings with match scores
- `search_filters` - Job search criteria
- `scheduler_config` - Scheduler settings
- `notification_logs` - Email notification history

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ANTHROPIC_API_KEY` - **Required**: Claude API key for AI matching
- `SMTP_HOST` - Email server (default: smtp.gmail.com)
- `SMTP_PORT` - Email port (default: 587)
- `SMTP_USER` - Email username
- `SMTP_PASS` - Email password/app password
- `NOTIFICATION_EMAIL` - Recipient email address
- `FETCH_INTERVAL_MINUTES` - Job fetch interval (default: 60)
- `TIMEZONE` - Timezone for scheduling (default: UTC)

## Troubleshooting

### Common Issues

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

## Development Roadmap

- [x] Phase 1: Setup & Core Infrastructure
- [x] Phase 2: CV Management (basic implementation)
- [x] Phase 3: Job Fetching (stub implementation)
- [ ] Phase 4: AI Matching (TODO)
- [ ] Phase 5: Scheduling & Automation (basic setup done)
- [ ] Phase 6: Email Notifications (TODO)
- [ ] Phase 7: Testing & Documentation
- [ ] Phase 8: Deployment

## Project Structure

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
│   ├── services/            # Business logic
│   └── utils/               # Utility functions
├── storage/
│   ├── cvs/                 # Uploaded CV files
│   └── temp/                # Temporary files
├── docker-compose.yml       # Docker services configuration
├── Dockerfile               # Application container
├── pyproject.toml           # Python dependencies
└── README.md                # This file
```

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

MIT License
