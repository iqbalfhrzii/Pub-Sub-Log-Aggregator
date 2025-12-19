@echo off
echo === UAS Sistem Terdistribusi - Startup Script ===
echo.

echo 1. Starting Docker Compose...
docker compose up -d --build

if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to start Docker Compose
    echo Please make sure Docker Desktop is running
    pause
    exit /b 1
)

echo.
echo 2. Waiting for services to be ready...
timeout /t 10 /nobreak > nul

echo.
echo 3. Checking service health...
curl -s http://localhost:8080/health

echo.
echo 4. System is ready!
echo.
echo Available endpoints:
echo   - Health Check: http://localhost:8080/health
echo   - Publish Event: POST http://localhost:8080/publish
echo   - Get Events: http://localhost:8080/events
echo   - Statistics: http://localhost:8080/stats
echo.
echo To run tests: python run_tests.py
echo To stop system: docker compose down
echo.
pause