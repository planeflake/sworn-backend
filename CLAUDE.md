# Sworn Backend Development Guidelines

## Running the Application
- Full app: `python run.py`
- API only: `uvicorn app.main:app --reload --port 8081 --host 0.0.0.0`
- Celery worker: `celery -A workers.celery_app worker --loglevel=info`
- Celery beat: `celery -A workers.celery_app beat --loglevel=info`

## Code Style
- **Naming**: PascalCase for classes, snake_case for functions/variables
- **Typing**: Always use type annotations for parameters and return values
- **Imports**: Standard first, third-party second, local third; alphabetical within groups
- **Error handling**: Use try/except blocks appropriately with specific exceptions
- **API**: Follow FastAPI conventions with Pydantic schemas for validation
- **Documentation**: Docstrings for classes and functions ("""triple quotes""")

## Project Structure
- `app/`: FastAPI application with routers by domain
- `models/`: Database ORM models
- `database/`: Connection and session management
- `workers/`: Celery background tasks
- `schemas/`: Pydantic data validation models