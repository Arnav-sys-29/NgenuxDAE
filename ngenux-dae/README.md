# Ngenux Decision Automation Engine (DAE)

The Ngenux DAE is a robust, Python-based rules engine designed to automate complex business decisions. It evaluates structured inputs against configurable policies and provides consistent, trackable outcomes with full audit logging and metadata tracking (latency, cost, and rule provenance).

## 🚀 How to Run Locally (from GitHub)

This project is **100% Dockerized**, making it incredibly easy to run on any system. You do not need to manually install Python, configure virtual environments, or set up a local database.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- Git

### 1. Clone the Repository
Open your terminal and clone the code directly from GitHub:
```bash
git clone https://github.com/Arnav-sys-29/NgenuxDAE.git
cd NgenuxDAE/ngenux-dae
```

### 2. Start the Application
Run the following command to build the images and spin up the database, API, and UI containers:
```bash
docker-compose up -d --build
```

### 3. Seed the Database
The decision engine reads dynamic business rules from the database. Run this script to automatically inject all five industry policies (Banking, HR, Insurance, Procurement, Leave) into your local database:
```bash
docker-compose exec api python seed_policy.py
```

### 4. Access the Application
- **Frontend (Streamlit UI):** [http://localhost:8501](http://localhost:8501)
  - *Use this to test rule evaluations interactively.*
- **Backend API (FastAPI Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
  - *Explore the Swagger UI to see endpoints for Decisions and Policy Management.*
- **Database (PostgreSQL):** `localhost:5432`
  - *User: `postgres` | Pass: `postgres` | DB: `ngenux_dae`*

---

## 🛑 Stopping the Application
To stop the containers and free up your ports without deleting your database data:
```bash
docker-compose stop
```
*(To completely destroy the containers and wipe the database, use `docker-compose down -v`)*

---

## 🏗️ Architecture

1. **Streamlit UI (`ui/app.py`)**: A 3-view dashboard for submitting requests, viewing history, and analyzing decision metadata.
2. **FastAPI Backend (`app/main.py`)**: Exposes REST endpoints for policy management and decision evaluation. 
3. **Decision Engine (`app/services.py`)**: Executes business rules loaded from the Policy Store.
4. **PostgreSQL Database**: Persists Decisions, Audit Logs, Policies, and Policy Versions using SQLAlchemy and Alembic.
