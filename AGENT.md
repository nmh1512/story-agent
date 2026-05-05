You are a senior software architect, senior backend engineer, AI workflow engineer, and Python infrastructure engineer.

Build a complete MVP backend system that runs entirely through CLI, with no UI, using Python and local LLMs, for an automated fiction-writing workflow with multiple AI agents.

The system must support:
1. A Planner agent that creates daily story ideas, genres, themes, outlines, and writing tasks.
2. A Writer agent that writes new chapters based on outlines and story memory.
3. A Reviewer agent that evaluates chapter quality, scores the chapter, and creates rewrite tasks when needed.
4. A Memory Update layer that extracts structured state from each chapter and updates long-term memory.
5. A character relationship layer using FalkorDB for graph-based character relationships.

The system must be production-minded, modular, Dockerized, and runnable locally with CLI commands for testing.

# 1. Primary Goal

Build a CLI-first automated story generation backend with daily orchestration.

The workflow is:

- Planner generates daily story outlines and writing tasks.
- Writer consumes due writing tasks and writes chapters.
- Reviewer reads written chapters, scores them, and creates rewrite tasks if quality is below threshold.
- Memory updater extracts summaries, events, character states, relation changes, and unresolved hooks from written chapters.
- Character relationship data is stored and queried in FalkorDB.
- MySQL remains the primary source of truth for structured business data.

No UI is needed.
No web frontend is needed.
No FastAPI is required.
Everything should be testable via CLI and Docker.

# 2. Mandatory Tech Stack

Use exactly this stack unless absolutely necessary to adjust a small detail:

- Python 3.11+
- Typer for CLI
- SQLAlchemy 2.x for ORM
- Alembic for database migrations
- MySQL 8 for primary relational database
- Redis for queue, cache, and locking
- Celery for background jobs
- APScheduler or Celery Beat for daily scheduling
- Pydantic 2 for schema validation
- FalkorDB for graph-based character relationships
- Local LLM runtime:
  - prefer Ollama local HTTP API by default
  - design the code so it can be swapped with LM Studio, vLLM, or any OpenAI-compatible local endpoint
- Docker + Docker Compose for all services
- Python logging for structured logging

Do NOT use:
- frontend frameworks
- web UI
- PostgreSQL
- Neo4j
- cloud-only services

# 3. High-Level Architecture

Design the project with a clean modular architecture:

- app/cli.py                 -> CLI entrypoint
- app/core/                  -> config, logging, constants
- app/db/                    -> SQLAlchemy base, session, models
- app/graph/                 -> FalkorDB client and graph services
- app/schemas/               -> Pydantic schemas
- app/prompts/               -> prompt templates
- app/agents/                -> planner, writer, reviewer, memory updater
- app/services/              -> orchestration and business logic
- app/jobs/                  -> Celery tasks
- app/scheduler/             -> scheduled jobs
- app/utils/                 -> utility helpers
- alembic/                   -> migrations

Separate clearly:
- persistence logic
- agent logic
- graph logic
- orchestration logic
- queue logic
- CLI logic

# 4. Agent Relationship Model

Design the core relation between agents as:

Planner -> Writer -> Reviewer
   ^          |         |
   |          v         |
   +------ Memory ------+

Explanation:
- Planner creates daily outlines and writing tasks.
- Writer writes chapters from due tasks.
- Reviewer scores chapters and decides whether rewrite is needed.
- Memory updater extracts structured long-term memory from finished chapters.
- FalkorDB stores and updates graph relationships between characters.
- If Reviewer flags a rewrite, Writer gets a rewrite task with review notes.

Even though there are 3 main AI agents, the system must include:
- a dedicated memory update layer
- a dedicated FalkorDB graph service

# 5. Long-Term Memory Design

Do NOT rely on the LLM to remember previous chapters implicitly.
Do NOT feed the whole novel every time.

Use layered memory:

1. Full chapter text
2. Per-chapter summary
3. Current story state
4. Current character state
5. Character relationship graph in FalkorDB
6. Story events timeline
7. Open / resolved story hooks

The Writer agent must build context from these layers rather than from the full story history.

# 6. Writer Context Strategy

When Writer writes a new chapter, build context using:

- story bible / genre / tone / world rules
- current story state
- current character states for relevant characters
- relationship graph snapshot from FalkorDB
- open hooks
- full text of the 1-2 most recent chapters
- summaries of older relevant chapters
- the target outline
- rewrite notes if this is a rewrite task

Implement code that assembles this context deterministically from MySQL + FalkorDB.

# 7. Databases and Responsibilities

Use the following data responsibilities:

## MySQL
MySQL is the primary source of truth for:
- stories
- outlines
- tasks
- chapters
- chapter summaries
- reviews
- story states
- characters
- character states
- story events
- story hooks
- agent runs

## FalkorDB
FalkorDB stores graph data for:
- character nodes
- relationship edges
- relation properties:
  - relation_type
  - trust_score
  - affection_score
  - hostility_score
  - note
  - updated_in_chapter

MySQL remains the authoritative business database.
FalkorDB is the graph projection layer for character relationships and graph queries.

# 8. Required MySQL Tables

Design a clean MySQL schema with indexes, foreign keys, status enums, and JSON fields where appropriate.

## 8.1 stories
Fields:
- id
- code
- title
- genre
- premise
- style_guide
- world_bible_json
- status
- created_at
- updated_at

## 8.2 story_outlines
Fields:
- id
- story_id
- outline_date
- chapter_no
- theme
- summary
- outline_json
- status
- created_at
- updated_at

## 8.3 story_tasks
Fields:
- id
- story_id
- outline_id nullable
- chapter_id nullable
- task_type: plan / write / review / rewrite / memory_update
- payload_json
- priority
- scheduled_for
- status: pending / processing / done / failed / cancelled
- retry_count
- error_message
- created_at
- updated_at

## 8.4 chapters
Fields:
- id
- story_id
- outline_id nullable
- chapter_no
- title
- content LONGTEXT
- word_count
- version_no
- status
- review_score nullable
- needs_rewrite boolean
- created_at
- updated_at

## 8.5 chapter_summaries
Fields:
- id
- chapter_id
- story_id
- chapter_no
- summary
- key_events_json
- character_updates_json
- items_json
- foreshadow_json
- created_at
- updated_at

## 8.6 chapter_reviews
Fields:
- id
- chapter_id
- story_id
- score
- verdict
- strengths_json
- weaknesses_json
- notes
- rewrite_notes_json
- created_at
- updated_at

## 8.7 story_states
Fields:
- id
- story_id
- current_chapter_no
- current_arc
- current_goal
- current_conflict
- world_state_json
- active_summary
- updated_at

## 8.8 characters
Fields:
- id
- story_id
- code
- name
- role
- description
- personality_json
- background
- status
- created_at
- updated_at

## 8.9 character_states
Fields:
- id
- story_id
- character_id
- chapter_no
- realm
- status
- goal
- emotion
- location
- inventory_json
- secrets_known_json
- state_summary
- updated_at

## 8.10 story_events
Fields:
- id
- story_id
- chapter_id nullable
- chapter_no
- event_type
- summary
- characters_involved_json
- impact_level
- is_active
- created_at
- updated_at

## 8.11 story_hooks
Fields:
- id
- story_id
- chapter_no_created
- hook_text
- related_character_id nullable
- status: open / resolved
- resolved_in_chapter nullable
- created_at
- updated_at

## 8.12 agent_runs
Fields:
- id
- agent_name
- task_id nullable
- story_id nullable
- chapter_id nullable
- input_json
- output_json
- status
- error_message
- started_at
- finished_at
- created_at

Requirements:
- Use MySQL-compatible types.
- Add proper foreign keys.
- Add indexes for story_id, chapter_no, status, scheduled_for, task_type.
- Use JSON fields where useful.
- Create SQLAlchemy models and Alembic migrations.

# 9. FalkorDB Graph Model

Design a FalkorDB graph schema for character relationships.

## Node Labels

### Character
Properties:
- character_id
- story_id
- code
- name
- role
- realm
- status
- location

### Story
Properties:
- story_id
- code
- title
- genre

## Relationship Types

### BELONGS_TO
(Character)-[:BELONGS_TO]->(Story)

### RELATES_TO
(Character)-[:RELATES_TO]->(Character)
Properties:
- relation_type
- trust_score
- affection_score
- hostility_score
- note
- updated_in_chapter
- updated_at

Optionally support:
- KNOWS_SECRET_OF
- OWES_DEBT_TO
- ALLIED_WITH
- ENEMY_OF
But at minimum, RELATES_TO must exist and support rich properties.

## FalkorDB Requirements
Implement:
- graph client abstraction
- graph initialization
- upsert story node
- upsert character node
- upsert relation edge
- query relation snapshot for a story
- query direct relations for a character
- query suspicious/high-hostility/high-trust relation chains
- sync character relation changes from MySQL memory updates into FalkorDB

# 10. Pydantic Schemas for Each Agent

Create explicit Pydantic schemas for agent inputs and outputs.

## 10.1 Planner Agent Schema

### PlannerInput
Fields:
- story_id: int
- story_title: str
- genre: str
- premise: str
- style_guide: str | None
- world_bible: dict
- current_story_state: dict | None
- recent_chapter_summaries: list[dict]
- open_hooks: list[dict]
- planner_mode: str   # "new_story_arc" or "next_chapter_outline"
- target_date: str
- target_chapter_no: int

### PlannerOutput
Fields:
- story_id: int
- chapter_no: int
- theme: str
- summary: str
- outline: dict
- must_include: list[str]
- must_avoid: list[str]
- continuity_notes: list[str]
- suggested_characters: list[int]
- creates_write_task: bool

## 10.2 Writer Agent Schema

### WriterInput
Fields:
- story_id: int
- outline_id: int
- chapter_no: int
- genre: str
- premise: str
- style_guide: str | None
- world_bible: dict
- current_story_state: dict
- relevant_character_states: list[dict]
- relation_snapshot: list[dict]
- open_hooks: list[dict]
- recent_full_chapters: list[dict]
- older_summaries: list[dict]
- outline: dict
- mode: str   # "write" or "rewrite"
- rewrite_notes: list[str] | None
- target_word_count: int | None

### WriterOutput
Fields:
- story_id: int
- chapter_no: int
- title: str
- content: str
- word_count: int
- new_facts: list[str]
- newly_introduced_hooks: list[str]
- affected_character_ids: list[int]
- continuity_notes: list[str]

## 10.3 Reviewer Agent Schema

### ReviewerInput
Fields:
- story_id: int
- chapter_id: int
- chapter_no: int
- chapter_title: str
- chapter_content: str
- outline: dict | None
- current_story_state: dict | None
- recent_summaries: list[dict]
- target_quality_threshold: int

### ReviewerOutput
Fields:
- story_id: int
- chapter_id: int
- score: int
- verdict: str
- strengths: list[str]
- weaknesses: list[str]
- notes: str
- rewrite_notes: list[str]
- should_rewrite: bool

## 10.4 Memory Update Agent Schema

### MemoryUpdateInput
Fields:
- story_id: int
- chapter_id: int
- chapter_no: int
- chapter_title: str
- chapter_content: str
- previous_story_state: dict | None
- previous_character_states: list[dict]
- previous_open_hooks: list[dict]
- previous_relation_snapshot: list[dict]

### MemoryUpdateOutput
Fields:
- story_id: int
- chapter_id: int
- chapter_no: int
- chapter_summary: str
- key_events: list[dict]
- character_state_updates: list[dict]
- relation_updates: list[dict]
- new_hooks: list[dict]
- resolved_hooks: list[dict]
- new_story_state: dict

# 11. CLI Commands

Use Typer and implement these commands:

- init-db
- seed-demo
- create-story
- plan-daily
- write-due
- review-due
- rewrite-due
- update-memory
- sync-graph
- run-once
- worker
- scheduler-start

Required behavior:

## init-db
- initialize schema
- support alembic upgrade

## seed-demo
- insert one demo story, demo characters, and seed states

## create-story
- create a new story from CLI options or JSON file

## plan-daily
- run Planner agent
- create outline rows
- create write tasks

## write-due
- find due write tasks
- run Writer agent
- save chapter
- create review task
- create memory_update task

## review-due
- find due review tasks
- run Reviewer agent
- save review
- create rewrite task if needed

## rewrite-due
- process rewrite tasks
- run Writer in rewrite mode
- save new chapter version
- create new review task

## update-memory
- process memory_update tasks
- save chapter summary
- update story state
- update character states
- update events
- update hooks
- produce relation updates

## sync-graph
- sync relation changes to FalkorDB
- upsert character nodes and RELATES_TO edges

## run-once
Run the full sequence:
- plan-daily
- write-due
- review-due
- rewrite-due
- update-memory
- sync-graph

## worker
- run Celery worker

## scheduler-start
- run APScheduler or equivalent recurring scheduler

# 12. LLM Client Abstraction

Implement a provider abstraction:

- BaseLLMClient
- OllamaClient
- OpenAICompatibleLocalClient

Requirements:
- configurable provider via environment variables
- default to Ollama
- model name configurable
- timeout configurable
- metadata logging
- simple retry support
- do not log huge content bodies unnecessarily
- easy to swap providers later

# 13. Prompt Templates

Create prompt templates for:

## Planner
Responsibilities:
- create next chapter outline or arc
- respect story continuity
- not break existing world logic
- output strict JSON

## Writer
Responsibilities:
- write a complete chapter
- follow outline
- respect continuity and world rules
- use structured memory context
- if rewrite mode, obey rewrite notes
- output strict JSON

## Reviewer
Responsibilities:
- evaluate hook, pacing, emotional pull, logic, consistency
- output strict JSON

## Memory Updater
Responsibilities:
- summarize chapter
- extract events
- update character states
- update relation changes
- detect new hooks and resolved hooks
- output strict JSON

Requirements:
- all prompts must request strict JSON output
- create validators and fallback repair logic for malformed JSON

# 14. Celery, Scheduling, and Orchestration

Use Dockerized services for:

- app       -> manual CLI usage
- worker    -> Celery worker
- scheduler -> recurring task scheduler
- mysql
- redis
- ollama
- falkordb

Requirements:
- Docker Compose setup
- Dockerfile for Python app
- healthchecks where appropriate
- environment configuration
- containers wait for dependencies
- worker must wait for MySQL and Redis
- app container must be able to run all CLI commands

# 15. Docker Requirements

Provide all of the following:

1. Dockerfile
2. docker-compose.yml
3. .env.example
4. entrypoint script if needed
5. healthcheck recommendations
6. volume mappings for:
   - source code
   - MySQL data
   - Redis data if needed
   - Ollama model data
   - FalkorDB persistence if applicable

The docker-compose services must include:
- app
- worker
- scheduler
- mysql
- redis
- ollama
- falkordb

# 16. Logging and Error Handling

Implement robust logging:
- console logging
- file logging
- configurable levels
- log every agent run
- log task state transitions

Implement error handling:
- task failure increments retry_count
- after max retries, mark task failed
- write error_message to MySQL
- persist failures in agent_runs
- avoid crashing the whole pipeline due to one failed task

# 17. Code Quality Requirements

Write clean, modular, realistic MVP code:
- full type hints
- short docstrings
- clear module boundaries
- minimal but real implementation
- avoid pseudo-code where practical
- keep the architecture extensible
- do not overengineer

# 18. Output Format Required

Return the implementation in this order:

1. Project folder structure
2. Short architecture explanation
3. Full source code for the MVP
4. SQLAlchemy models
5. Alembic migration
6. Pydantic agent schemas
7. FalkorDB graph client and graph service
8. CLI commands with Typer
9. Agent classes
10. Service layer
11. LLM client abstraction
12. Prompt templates
13. Celery tasks
14. Scheduler setup
15. Dockerfile
16. docker-compose.yml
17. .env.example
18. README with local Docker instructions

# 19. Additional Constraints

- No UI
- No frontend
- No FastAPI unless absolutely necessary
- MySQL is the primary business database
- FalkorDB must be used for character graph relationships
- DB is the source of truth
- The system must be runnable locally with Docker
- CLI commands must be enough for testing
- The design should allow future vector memory support, but do not implement vector DB yet
- Do not return only high-level ideas; generate concrete runnable MVP code

Start implementing now.