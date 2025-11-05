# Job Matcher

An intelligent job matching system that automatically fetches job postings, matches them against your CV using AI, and sends email notifications for relevant opportunities.

## Features

- **CV Management**: Upload and manage your CV (PDF/DOCX format)
- **Job Fetching**: Automated scraping of job boards (LinkedIn, Drushim, etc.)
- **AI Matching**: Smart job matching using Claude AI
- **Filtering**: Customizable search filters (keywords, location, salary, etc.)
- **Scheduling**: Automated job fetching with configurable intervals
- **Email Notifications**: Get notified about matching jobs

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd job_matcher
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```   
   Edit `.env` and add your API keys and configuration.

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

4. **Check service health**:
   ```bash
   curl http://localhost:8000/api/health
   ```

5. **Access API documentation**:
   Open http://localhost:8000/docs in your browser

### Local Development (without Docker)

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   # Create virtual environment and install dependencies
   uv sync
   
   # Or manually:
   uv venv
   source .venv/bin/activate  # On macOS/Linux
   uv pip install -e .
   ```

3. **Start PostgreSQL and Redis** (via Docker):
   ```bash
   docker-compose up -d postgres redis
   ```

4. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Run Celery worker** (in another terminal):
   ```bash
   celery -A app.celery_worker worker --loglevel=info
   ```

6. **Run Celery beat** (in another terminal):
   ```bash
   celery -A app.celery_worker beat --loglevel=info
   ```

## API Endpoints

### System
- `GET /api/health` - Health check

### CV Management
- `POST /api/cv/upload` - Upload CV (PDF/DOCX)
- `GET /api/cv` - Get active CV
- `GET /api/cv/all` - Get all CVs
- `PUT /api/cv/summary` - Update CV summary
- `DELETE /api/cv/{id}` - Delete CV

### Job Management
- `GET /api/jobs` - List jobs (with filters)
- `GET /api/jobs/{id}` - Get job details
- `PUT /api/jobs/{id}/notified` - Mark as notified
- `DELETE /api/jobs/{id}` - Delete job

### Search Filters
- `GET /api/filters` - Get all filters
- `GET /api/filters/{id}` - Get filter by ID
- `POST /api/filters` - Create filter
- `PUT /api/filters/{id}` - Update filter
- `DELETE /api/filters/{id}` - Delete filter

### Scheduler
- `POST /api/scheduler/trigger` - Trigger job fetch
- `GET /api/scheduler/status` - Get status
- `PUT /api/scheduler/config` - Update config

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
- `ANTHROPIC_API_KEY` - Claude API key for AI matching
- `SMTP_*` - Email configuration
- `NOTIFICATION_EMAIL` - Recipient email address

## Development Roadmap

- [x] Phase 1: Setup & Core Infrastructure
- [x] Phase 2: CV Management (basic implementation)
- [x] Phase 3: Job Fetching (stub implementation)
- [ ] Phase 4: AI Matching (TODO)
- [ ] Phase 5: Scheduling & Automation (basic setup done)
- [ ] Phase 6: Email Notifications (TODO)
- [ ] Phase 7: Testing & Documentation
- [ ] Phase 8: Deployment

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

MIT License
