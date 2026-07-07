# PS5 Hunter 🎮🛒

PS5 Hunter is a production-ready, 24/7 web application designed to monitor PlayStation 5 stock across multiple Indian retailers and send instant notifications the moment stock becomes available.

## Features

- **Store Integrations:** Monitors Amazon India, Flipkart, Blinkit, Zepto, Reliance Digital, Croma, and Vijay Sales.
- **Concurrent Workers:** Uses asyncio workers to scan all stores concurrently every 15-30 seconds.
- **Notification Channels:** Supports Telegram Bot (primary), Discord Webhooks, and SMTP Email alerts.
- **Real-Time Dashboard:** A sleek dark-themed responsive glassmorphic dashboard showcasing real-time status, average response time, scanning logs, and metrics (with Recharts charts).
- **Admin Configuration Panel:** Turn stores on/off, modify target product URLs, configure chat IDs/tokens, set cooldown periods, and trigger test alerts.
- **Database Logs:** Tracks stock event transitions (out-of-stock -> in-stock), duration in stock, and error tracking.

---

## Architecture Overview

- **Backend:** Python (FastAPI, SQLAlchemy, SQLite/PostgreSQL, Playwright, HTTPX, BeautifulSoup)
- **Frontend:** Next.js (React, TypeScript, Tailwind CSS, WebSockets, Recharts)
- **Deployment:** Docker & Docker Compose support.

---

## Getting Started

### 1. Docker Compose (Recommended Setup)

To deploy both backend and frontend with a single command:

1. Clone or copy this repository.
2. Edit the `.env` file to set your notification tokens (Telegram Bot Token, Chat ID, etc.).
3. Run the following command:
   ```bash
   docker-compose up --build
   ```
4. Access the web dashboard at `http://localhost:3000`.

### 2. Local Manual Installation (No Docker)

#### Backend Setup

1. Change directory to backend:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Playwright browser engines:
   ```bash
   playwright install chromium
   ```
5. Start the backend development server:
   ```bash
   uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. Change directory to frontend:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Visit `http://localhost:3000`.

---

## Plugin Architecture

To add a new Indian retailer to the monitor list:
1. Create a new file in `backend/app/monitors/` inheriting from `BaseMonitor`.
2. Implement your parsing logic inside the `async def check(self, url: str)` method.
3. Register the new monitor in `backend/app/monitors/registry.py`.
4. Run the app, add the URL in Settings, and configure notifications.
