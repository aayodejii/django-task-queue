# Django Task Queue System

Async image resizing API with production-ready background task processing. Features retry logic with exponential backoff, idempotent task handling, and automated cleanup for long-term operation.

**Key capabilities:**

- Non-blocking image uploads with background processing
- Automatic retries for transient failures
- Idempotency prevents duplicate work from concurrent workers
- Scheduled cleanup manages storage costs

**Tech stack:** Django REST Framework, Celery, Redis, PostgreSQL

---

## Architecture

```
Client → Django API → Redis Queue → Celery Worker → PostgreSQL
                          ↓
                     Celery Beat (cleanup)
```

The system separates concerns: Django handles HTTP requests, Celery handles background processing, Redis queues tasks, and PostgreSQL stores durable job state. When a client uploads an image, the API immediately returns a job ID while resizing happens asynchronously in a worker process. This architecture keeps the API responsive even under heavy load.

**Components:**

- **Django REST API:** Receives uploads, creates job records, returns job IDs
- **Redis:** Message broker for task queue and result storage
- **Celery Workers:** Process resize tasks asynchronously
- **PostgreSQL:** Persistent storage for job metadata and status
- **Celery Beat:** Scheduler that triggers hourly cleanup of old jobs

---

## API Endpoints

### POST /jobs/

Upload an image for async resizing.

**Request:**

```bash
curl -X POST http://localhost:8000/jobs/ \
  -F "original_image=@photo.jpg"
```

**Response (201 Created):**

```json
{
  "id": "02f137ae-a727-4997-ad60-08a3784b55f2",
  "status": "pending",
  "original_image": "/media/originals/IMG-20240113-WA0130.jpg",
  "resized_image": null,
  "error_message": null,
  "created_at": "2025-11-05T00:47:15.267977Z"
}
```

---

### GET /jobs/{id}/

Check job status and retrieve result.

**Response (200 OK - Pending):**

```json
{
  "id": "02f137ae-a727-4997-ad60-08a3784b55f2",
  "status": "pending",
  "original_image": "/media/originals/IMG-20240113-WA0130.jpg",
  "resized_image": null,
  "error_message": null,
  "created_at": "2025-11-05T00:47:15.267977Z"
}
```

**Response (200 OK - Completed):**

```json
{
  "id": "02f137ae-a727-4997-ad60-08a3784b55f2",
  "status": "completed",
  "original_image": "/media/originals/IMG-20240113-WA0130.jpg",
  "resized_image": "/media/thumbnails/thumbnail-9f9500bc.jpg",
  "error_message": null,
  "created_at": "2025-11-05T00:47:15.267977Z"
}
```

**Response (200 OK - Failed):**

```json
{
  "id": "0ad307ae-a727-9997-ad60-01a3784b5902",
  "status": "failed",
  "original_image": "/media/originals/IMG-20240113-WA0130.jpg",
  "resized_image": null,
  "error_message": "Corrupted image file",
  "created_at": "2025-11-05T00:47:15.267977Z"
}
```

**Response (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

---

## Design Decisions

### Why Celery over threading?

Tasks need to survive server restarts. Celery persists jobs in Redis, so in-progress work isn't lost during deployments. Threading runs in the Django process if the server crashes, queued work is gone.

### Why separate workers?

Image processing is CPU-intensive. Separating workers from the API keeps response times fast even under load. The API can handle thousands of uploads while workers process at their own pace.

### Why PostgreSQL for job metadata?

Job records need durability guarantees. Once a user gets a job ID, that record must survive crashes. Redis handles the queue (speed matters), PostgreSQL handles the source of truth (durability matters).

### Why Redis as broker?

Redis provides sub-millisecond task delivery and built-in result storage. It's simpler to operate than RabbitMQ for this use case, and the performance is sufficient for image processing workloads.

### Why idempotency checks?

Multiple workers might pick up the same task during failure scenarios. Idempotency ensures that if a task runs twice, it doesn't duplicate work or corrupt data. The task checks job status before processing.

### Why automatic cleanup?

In production, unmanaged storage leads to cost bloat. The cleanup task runs hourly via Celery Beat to delete jobs older than 24 hours, keeping storage predictable.

### Why exponential backoff?

Transient failures (network issues, temporary file locks) often resolve quickly. Exponential backoff (1s, 2s, 4s) gives the system time to recover without hammering failing resources.

---

## Local Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Docker (for Redis)

### Installation

1. **Clone the repository:**

```bash
   git clone https://github.com/aayodejii/django-task-queue.git
   cd django-task-queue
```

2. **Install dependencies with uv:**

```bash
   uv sync
```

3. **Start Redis (using Docker):**

```bash
   docker run -d -p 6379:6379 redis:7-alpine
```

4. **Run migrations:**

```bash
   uv run python manage.py migrate
```

5. **Start the development server:**

```bash
   uv run python manage.py runserver
```

6. **Start Celery worker (in a new terminal):**

```bash
   uv run celery -A django_task_queue worker --loglevel=info
```

7. **Start Celery Beat (in another terminal):**

```bash
   uv run celery -A django_task_queue beat --loglevel=info
```

### Testing

```bash
uv run python manage.py test
```

## Production Deployment

### Prerequisites

- Railway/Render account (or similar PaaS)
- Managed Redis instance
- Managed PostgreSQL instance

### Configuration

1. **Environment variables:**

```bash
   DEBUG=False
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=your-domain.com

   # Database
   PGHOST=your-db-host
   PGDATABASE=your-db-name
   PGUSER=your-db-user
   PGPASSWORD=your-db-password
   PGPORT=5432

   # Redis
   REDIS_URL=redis://your-redis-host:6379
```

2. **Create `Procfile`:**

```
   web: gunicorn django_task_queue.wsgi
   worker: celery -A django_task_queue worker --loglevel=info
   beat: celery -A django_task_queue beat --loglevel=info
```

3. **Dependencies (managed via `pyproject.toml`):**

   Core packages:

   - Django 5.2+
   - Django REST Framework
   - Celery with Redis support
   - PostgreSQL adapter (psycopg2)
   - Gunicorn (production server)
   - Pillow (image processing)

   For deployment, export dependencies:

```bash
   uv pip compile pyproject.toml -o requirements.txt
```

4. **Deploy:**
   - Push to GitHub
   - Connect to Railway/Render
   - Add 3 services: web, worker, beat (same repo, different start commands)
   - Set environment variables
   - Deploy

### Post-Deployment

- Run migrations: `python manage.py migrate`
- Test with a sample upload
- Monitor Celery logs for task processing

---

## Testing Strategy

The test suite covers:

- **Image resize success:** Verifies thumbnail creation and job status updates
- **Error handling:** Tests task failure and retry behavior
- **Cleanup tasks:** Ensures old jobs and files are deleted correctly

Run tests with:

```bash
python manage.py test tasks.tests
```

---

## Future Enhancements

- [ ] Support multiple resize dimensions (e.g., small, medium, large)
- [ ] Add job listing endpoint with pagination
- [ ] Implement webhooks for job completion notifications
- [ ] Add progress tracking for long-running tasks
- [ ] S3 integration for file storage
- [ ] Rate limiting on upload endpoint

---

## License

MIT

---

## Contact

Built by Ayodeji Akenroye - https://www.linkedin.com/in/ayodeji-akenroye - aayodeji.f@gmail.com

**Looking for backend opportunities in Django/Python.** Open to discussing this project or potential roles.
