# CLAUDE.md

Claude Code reference file for BiliNote - AI video note generation tool.

## Project Overview

BiliNote is an AI-powered video note-taking assistant that extracts content from video platforms (Bilibili, YouTube, TikTok, etc.) and generates structured Markdown notes.

**Architecture:**
- Frontend: React + Vite + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- Database: SQLAlchemy
- Task Queue: Celery + Redis
- AI: OpenAI API, DeepSeek, Qwen, etc.
- Audio Processing: Fast-Whisper + FFmpeg

## Development Commands

### Frontend (BillNote_frontend/)
```bash
# Install dependencies
pnpm install

# Development server
pnpm dev

# Build for production
pnpm build

# Lint code
pnpm lint

# Preview production build
pnpm preview
```

### Backend (backend/)
```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
python main.py

# Start with Celery workers (for async tasks)
celery -A app.core.celery_app worker --loglevel=info
```

## Project Structure

```
BiliNote/
├── BillNote_frontend/          # React frontend
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API services
│   │   ├── utils/             # Utility functions
│   │   └── constant/          # Constants and configs
│   ├── package.json
│   └── vite.config.ts
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── routers/          # API routes
│   │   ├── services/         # Business logic
│   │   ├── downloaders/      # Video downloaders
│   │   ├── db/              # Database models and DAOs
│   │   ├── validators/       # Input validators
│   │   ├── tasks/           # Celery tasks
│   │   └── core/            # Core configurations
│   ├── main.py
│   └── requirements.txt
└── docker-compose.yml         # Docker deployment
```

## Key Features

- Multi-platform video support (Bilibili, YouTube, TikTok, local videos)
- Multiple note formats and styles
- Multimodal video understanding
- Version history tracking
- Custom GPT model configuration
- Local audio transcription (Fast-Whisper)
- Automatic screenshot insertion
- Content jump links to original video
- Task scheduling and management

## Environment Setup

1. Copy `.env.example` to `.env` and configure:
   - OpenAI API keys
   - Database URLs
   - Redis configuration
   - Video platform API keys

2. Install FFmpeg (required for audio processing):
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt install ffmpeg
   ```

3. Optional: CUDA acceleration for Fast-Whisper

## Testing

The project uses standard testing frameworks. Check package.json and requirements.txt for test-related dependencies.

## Docker Deployment

Use `docker-compose.yml` for containerized deployment. See deployment documentation for details.

## API Endpoints

Key backend routes:
- `/note` - Note generation and management
- `/scheduled_tasks` - Task scheduling
- `/health` - Health checks

## Recent Changes

- Added scheduled task management
- Enhanced video platform support (added Tencent platform)
- Improved error handling and UI
- Added Celery async task processing
- Enhanced Docker deployment options