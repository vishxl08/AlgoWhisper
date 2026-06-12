# AlgoWhisper

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)](https://t.me/)

## The Problem

When I practice LeetCode problems, I constantly face these frustrating challenges:

- **Getting stuck for hours** without knowing where to turn — discussions are often too verbose or give away the solution entirely
- **Needing hints without spoilers** — most resources either explain nothing or reveal the complete answer, ruining the learning experience
- **Losing track of progress** — no easy way to maintain streaks, track time spent, or see which topics need more practice
- **Forgetting solutions** — solving a problem once doesn't mean I'll remember it when it comes up in an interview
- **Inconsistent practice routine** — without daily reminders and motivation, it's easy to skip days and break momentum

## The Idea

**AlgoWhisper** is a **Retrieval-Augmented Generation (RAG)** system that solves these problems through a Telegram bot. It provides smart hints without spoilers, full explanations, progress tracking, and personalized learning — all grounded in your ingested problem data.

## Work Done

Built a complete RAG pipeline with:

- **Data Ingestion**: Scrapes and processes LeetCode problems, NeetCode transcripts, and personal strategy notes
- **Vector Database**: Uses ChromaDB for semantic search and retrieval
- **LLM Integration**: Powered by Groq API for fast, accurate responses
- **Telegram Bot**: 30+ commands for different learning modes and progress tracking
- **FastAPI Backend**: RESTful API for programmatic access
- **Session Management**: Redis for conversation history, SQLite for progress tracking
- **Daily Digest**: Automated problem recommendations to keep you consistent

---

## Features

### Core Features

- **Smart Hints** — Get nudges toward the solution without spoilers
- **Full Explanations** — Step-by-step walkthroughs when you're ready
- **Complexity Analysis** — Time and space complexity with trade-offs
- **Similar Problems** — Discover related problems to practice next
- **Progress Tracking** — Track streaks, solve count, and time spent
- **Daily Digest** — Automated problem recommendations to stay consistent
- **Personalized Learning** — Set your preferred language and skill level
- **Interview Mode** — Practice with interview-style questions
- **Code Review** — Paste your code for feedback
- **Save Notes** — Save strategies and retrieve them later

### Key Commands

| Command | Description |
|---------|-------------|
| `/set <slug>` | Set current problem (e.g., `/set two-sum`) |
| `/hint` | Get a nudge without the full solution |
| `/explain` | Full step-by-step walkthrough |
| `/complexity` | Time & space complexity analysis |
| `/similar` | Related problems to practice |
| `/solved` | Mark problem as solved |
| `/stats` | View your progress and streaks |
| `/stuck` | Context-aware help when genuinely stuck |
| `/interview` | Mock interview mode |
| `/check <code>` | Paste code for review |
| `/menu` | Interactive command menu |

---

## How to Run and Use

### Prerequisites

- Python 3.10+
- Groq API key ([console.groq.com](https://console.groq.com))
- Telegram Bot Token (create via [@BotFather](https://t.me/BotFather))
- Redis (optional, for session storage)

### Installation

```bash
# Clone the repository
git clone https://github.com/vishxl08/AlgoWhisper.git
cd AlgoWhisper/leetcode-mentor-bot

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your GROQ_API_KEY and TELEGRAM_TOKEN
```

### Ingest Data

```bash
python scripts/ingest.py
```

Add your problem data to `data/raw/` before running ingestion.

### Start the Services

```bash
# Terminal 1 — Start API
python run_api.py

# Terminal 2 — Start Bot
python run_bot.py
```

### Using the Bot

1. Start a chat with your Telegram bot
2. Use `/set <slug>` to set a problem
3. Use commands like `/hint`, `/explain`, `/complexity`
4. Track progress with `/stats` and `/solved`

---

## Tech Stack

- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector DB**: ChromaDB (persistent storage)
- **LLM**: Groq API (Llama 3 70B)
- **API**: FastAPI (async REST endpoints)
- **Bot**: python-telegram-bot (v20+)
- **Sessions**: Redis (conversation history)
- **Progress**: SQLite (user progress tracking)
- **Scheduling**: APScheduler (daily digests)
- **HTTP Client**: httpx (async API calls)

---

## Project Structure

```
AlgoWhisper/
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI application with REST endpoints
├── bot/
│   ├── __init__.py
│   ├── api_client.py        # Async HTTP client for API communication
│   ├── commands_catalog.py  # Command definitions and metadata
│   ├── commands_setup.py    # Command registration
│   ├── handlers.py          # Telegram message/command handlers
│   ├── help_text.py         # Help message templates
│   ├── main.py              # Telegram bot initialization
│   ├── menu.py              # Interactive menu system
│   ├── progress.py          # Progress tracking logic
│   ├── scheduler.py         # Daily digest scheduling
│   └── session.py           # Session management
├── data/
│   └── raw/                 # Raw problem data for ingestion
├── ingestion/
│   ├── __init__.py
│   ├── chunker.py           # Text chunking for embeddings
│   ├── embedder.py          # Embedding generation
│   └── scraper.py           # LeetCode data scraping
├── rag/
│   ├── __init__.py
│   ├── llm.py               # LLM integration (Groq API)
│   ├── prompt_builder.py    # Prompt templates and construction
│   ├── retriever.py         # Semantic search and retrieval
│   ├── service.py           # RAG pipeline orchestration
│   └── vectorstore.py       # ChromaDB operations
├── scripts/
│   └── ingest.py            # Data ingestion script
├── .env                     # Environment variables
├── .gitignore
├── config.py                # Configuration management
├── requirements.txt         # Python dependencies
├── run_api.py               # API server entry point
└── run_bot.py               # Bot entry point
```

---

## Architecture Overview

### RAG Pipeline Flow

1. **Data Ingestion**
   - Scrapes LeetCode problems, NeetCode transcripts, and strategy notes
   - Processes and chunks text into optimal segments (500-1000 tokens)
   - Generates embeddings using sentence-transformers
   - Stores in ChromaDB with metadata (difficulty, tags, slug)

2. **Retrieval**
   - User query embedded using same model
   - Semantic search finds top-k relevant chunks
   - Re-ranks results based on problem context and user history

3. **Generation**
   - Constructs context-aware prompts with retrieved chunks
   - Sends to Groq API (Llama 3 70B) for response generation
   - Applies prompt engineering for hint vs. explanation modes
   - Returns structured responses with code examples

### Bot Architecture

- **Async Handlers**: All bot operations use async/await for concurrency
- **Session Management**: Redis stores conversation context per user
- **Progress Tracking**: SQLite database for solved problems and streaks
- **Scheduler**: APScheduler triggers daily digest at user-specified times
- **Error Handling**: Comprehensive try-catch with user-friendly messages

### API Architecture

- **FastAPI**: Async REST framework with automatic OpenAPI docs
- **Endpoints**: `/hint`, `/explain`, `/complexity`, `/similar`, `/stats`
- **Validation**: Pydantic models for request/response validation
- **CORS**: Configured for cross-origin requests

---

## Bot Availability Status

⚠️ **Important**: The bot is currently **not available 24/7**. The bot runs on a local development environment and may experience downtime. We are working on deploying the bot to a cloud infrastructure (likely AWS/GCP) to ensure 24/7 availability. This issue will be fixed soon. Stay tuned for updates!

---

---

## License

MIT License — feel free to use for personal or commercial purposes.

---

**Made with ❤️ by [vishxl08](https://github.com/vishxl08)**
