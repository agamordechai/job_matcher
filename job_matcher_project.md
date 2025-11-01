# Job Matching Microservice System

## Project Overview
A microservice that automatically fetches LinkedIn jobs, matches them against your CV, scores compatibility, identifies skill gaps, generates optimized CV summaries, and notifies you of opportunities via email.

## Tech Stack Recommendations
- **Backend**: Python with FastAPI and poetry or UV
- **Database**: PostgreSQL or NoSQL(what fits better)
- **Job Queue**: Redis-backed or RabitMQ
- **LinkedIn Scraping**: Playwright or LinkedIn API alternatives(maybe use playwright MCP?)
- **AI/LLM**: Anthropic Claude API for CV analysis
- **Email**: Any
- **File Storage**: Local filesystem s3-like or MinIO
- **Environment**: Docker & Docker Compose

## System Architecture

```
┌─────────────────┐
│   Scheduler     │ (Cron Queue - runs every hour)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Job Fetcher    │ (LinkedIn scraper/API)
│   Service       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Database     │ (Jobs storage with deduplication)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CV Analyzer    │ (AI-powered matching & scoring)
│    Service      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Email Notifier  │ (Send job matches & summaries)
│    Service      │
└─────────────────┘
```
## Core Features Implementation

### 1. CV Upload API
**Endpoint**: `POST /api/cv/upload`
```javascript
// Parse CV file (PDF/DOCX)
// Extract text content using pdf-parse or mammoth
// Store file and parsed content in database
// Return success response
```

### 2. Job Fetching Service
**Strategy Options**:
- **Option A**: Use Playwright to scrape LinkedIn (may violate ToS)
- **Option B**: Use third-party APIs like RapidAPI's LinkedIn Job Search
- **Option C**: Use official LinkedIn API (requires partnership)
- **Recommended**: Start with a mock API or free alternatives like Adzuna, The Muse API

**Implementation**:
```javascript
async function fetchJobs(filters) {
    // Fetch jobs based on filters from search_filters table
    // Deduplicate against existing jobs in DB (by linkedin_job_id)
    // Insert only new jobs with status 'pending'
    // Return count of new jobs
}
```

### 3. CV Matching & Scoring Service
**Endpoint**: Internal service, triggered by scheduler

**Logic example**:
```javascript
async function analyzeJobMatch(job, cvContent) {
    const prompt = `
        CV Content: ${cvContent}
        
        Job Description: ${job.description}
        
        Tasks:
        1. Score compatibility: HIGH (90%+ match), MEDIUM (60-89%), LOW (<60%)
        2. List 3-5 missing requirements from job description
        3. Determine if CV summary should be modified
        4. If yes, generate a new summary (2-3 sentences) optimized for this job
        
        Return JSON:
        {
            "score": "high|medium|low",
            "missingRequirements": ["req1", "req2"],
            "needsSummaryChange": true/false,
            "suggestedSummary": "new summary text or null"
        }
    `;
    
    // Call OpenAI/Claude API
    // Parse response
    // Update job record in database
}
```

### 4. Scheduler Service

### 5. Email Notification Service
**Endpoint**: Internal service, triggered after analysis

## API Endpoints

### CV Management
- `POST /api/cv/upload` - Upload CV file (PDF/DOCX)
- `GET /api/cv` - Get current CV details
- `PUT /api/cv/summary` - Update CV summary manually

### Job Management
- `GET /api/jobs` - List all jobs (with filters: score, notified, date)
- `GET /api/jobs/:id` - Get specific job details
- `PUT /api/jobs/:id/notified` - Mark job as seen/notified

### Search Filters
- `GET /api/filters` - Get active search filters
- `POST /api/filters` - Create/update search filters
- `DELETE /api/filters/:id` - Delete filter

### System Control
- `POST /api/scheduler/trigger` - Manually trigger job fetch & analysis
- `GET /api/scheduler/status` - Get scheduler status
- `PUT /api/scheduler/config` - Update schedule interval

## Configuration (Environment Variables)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jobmatcher
REDIS_URL=redis://localhost:6379

# AI Service
OPENAI_API_KEY=your_openai_key
# OR
ANTHROPIC_API_KEY=your_anthropic_key

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
NOTIFICATION_EMAIL=your_email@gmail.com

# LinkedIn (if using scraping/API)
LINKEDIN_EMAIL=your_linkedin@email.com
LINKEDIN_PASSWORD=your_password
# OR
RAPIDAPI_KEY=your_rapidapi_key

# Scheduler
FETCH_INTERVAL_MINUTES=60
TIMEZONE=America/New_York

# Application
PORT=3000
NODE_ENV=development
```

## Development Phases

### Phase 1: Setup & Core Infrastructure
- [ ] Initialize project
- [ ] Setup database
- [ ] Setup queue
- [ ] Create database schema & migrations

### Phase 2: CV Management
- [ ] Implement CV upload API
- [ ] Integrate PDF/DOCX parser
- [ ] Store CV content in database
- [ ] Create CV retrieval endpoint

### Phase 3: Job Fetching
- [ ] Choose job source (mock data, API, or scraper)
- [ ] Implement job fetching service
- [ ] Implement deduplication logic
- [ ] Store jobs in database

### Phase 4: AI Matching
- [ ] Integrate Claude API
- [ ] Implement CV-to-job matching logic
- [ ] Calculate compatibility scores
- [ ] Identify missing requirements
- [ ] Generate suggested summaries

### Phase 5: Scheduling & Automation
- [ ] Setup queue
- [ ] Implement recurring job scheduler
- [ ] Configure interval settings
- [ ] Add manual trigger endpoint

### Phase 6: Email Notifications
- [ ] Setup email service (SMTP/SendGrid)
- [ ] Create email templates
- [ ] Implement notification logic
- [ ] Track notification status

### Phase 7: Testing & Documentation
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Create API documentation (Swagger/Postman)
- [ ] Write comprehensive README

### Phase 8: Deployment
- [ ] Dockerize application
- [ ] Setup Docker Compose for local dev
- [ ] Deploy to cloud (Currently on openstack)
- [ ] Setup monitoring & logging

## Testing Strategy
- **Unit Tests**: Services, utils, models
- **Integration Tests**: API endpoints, database operations
- **E2E Tests**: Full workflow from job fetch to email
- **Load Tests**: Scheduler performance with many jobs

## Key Challenges & Solutions

### Challenge 1: LinkedIn Scraping Legality
**Solution**: Use official APIs, third-party job APIs, or start with mock data for demo

### Challenge 2: AI API Costs
**Solution**: Cache results, batch process, use cheaper models for initial filtering

### Challenge 3: Email Deliverability
**Solution**: Use SendGrid/AWS SES, implement proper SPF/DKIM

### Challenge 4: Deduplication
**Solution**: Use unique linkedin_job_id, hash job descriptions for similarity

## Demo Data & Showcase Tips
1. Create mock job data for demo if LinkedIn access is limited
2. Record video demo showing: upload CV → trigger fetch → receive email
3. Include Postman collection for API testing
4. Add health check endpoints for monitoring
5. Implement basic frontend dashboard (bonus points)

## Future Enhancements
- [ ] Support multiple CV versions
- [ ] A/B test different summaries
- [ ] Job application tracker
- [ ] Integration with job boards
- [ ] Chrome extension for one-click applications
- [ ] Analytics dashboard
- [ ] Multi-user support
