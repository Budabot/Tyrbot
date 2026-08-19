# Workspace Rules & Instructions

## Testing Instructions
1. **Branching**: Always create and work on a dedicated git branch for new work before making modifications.
2. **Containerized Execution**: All Python commands, scripts, and tests must be executed inside a Docker container (e.g., using `Dockerfile.test`).
3. **Database Isolation**: When running tests in Docker, isolate the database by mounting a dedicated file volume over `/app/data/database.db` so `data/database.db` is never affected:
   ```bash
   # Run all unit tests inside container
   docker run --rm -v "%CD%:/app" -v "%CD%/data/test_db.sqlite:/app/data/database.db" tyrbot-test python -m unittest discover -p "*_test.py"

   # Run specific test module inside container
   docker run --rm -v "%CD%:/app" -v "%CD%/data/test_db.sqlite:/app/data/database.db" tyrbot-test python -m unittest test/modules/extra/ai_controller_test.py
   ```

## Static Analysis
Before finalizing any code implementation or declaring a task complete, you MUST run static analysis on the modified Python files.
1. Run mypy and/or pylint against the files you modified.
2. Fix any type errors, syntax issues, or linting warnings caught by these tools before proceeding.
3. Like tests, ensure these are run inside the Docker container if the environment requires it.
