# Story Agent MVP

A CLI-first automated fiction-writing backend system powered by local LLMs (Ollama), MySQL, FalkorDB, and Celery.

## Architecture

- **Agent Types**: Planner, Writer, Reviewer, Memory Update.
- **Data Layers**:
  - **MySQL**: Primary authoritative source of truth (stories, outlines, chapters, reviews, agent runs, deterministic states).
  - **FalkorDB**: Graph projection layer holding `Character` and `Story` nodes, connected by `RELATES_TO` edges with dynamic property weights (`trust_score`, `hostility_score`).
- **Orchestration**:
  - **Scheduler**: APScheduler triggers daily planning.
  - **Queue**: Celery + Redis handles async execution of agent tasks (Write -> Review -> Memory Update).
- **No UI**: Operates purely off Typer CLI commands for maximum testability.

## Local Deployment Instructions

Ensure Docker and Docker Compose are installed. 

### 1. Configure Environment

```bash
cp .env.example .env
```
*(Optional: customize Ollama model name or DB credentials in `.env`)*

### 2. Start Services

Starts MySQL, Redis, FalkorDB, Celery Worker, Scheduler, and an interactive `app` shell container. Note: First Ollama boot may take time.

```bash
docker-compose up -d
```

### 3. Initialize Databases
From your host machine, run Typer commands against the `app` container:

```bash
docker-compose exec app python -m app.cli init-db
```
*(This creates MySQL tables and FalkorDB indexes)*

### 4. Create Demo Story

```bash
docker-compose exec app python -m app.cli seed-demo
```

### 5. Execute Pipeline

You can run the full automated sequence step-by-step:

```bash
# 1. Generate tomorrow's outline
docker-compose exec app python -m app.cli plan-daily

# 2. Process tasks created by the Planner
docker-compose exec app python -m app.cli write-due

# 3. Score the drafted chapters
docker-compose exec app python -m app.cli review-due

# 4. If any chapter failed review, run rewrites
docker-compose exec app python -m app.cli rewrite-due

# 5. Extract states and character graph changes
docker-compose exec app python -m app.cli update-memory
```

Or instantly trigger the full sequence manually:
```bash
docker-compose exec app python -m app.cli run-once
```

## Local LLM Setup
By default, the `ollama` service container inside `docker-compose` handles generation.
**Note**: You must manually pull your specified base model inside the container once:

```bash
docker-compose exec ollama ollama pull llama3
```
