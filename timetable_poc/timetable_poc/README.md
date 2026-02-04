# Timetable Generation System

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Supabase credentials:
```bash
# .env file
SUPABASE_DB_HOST=db.xxxxx.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your_password
```

### 3. **Run the Application** ⭐
```bash
python app.py
```

**That's it!** 🎉 The Flask server will start on `http://localhost:5000`

> **Note:** You only need to run `app.py`. The timetable generation is handled through the API endpoint `/api/hod/generate-timetable` - you don't need to run `main.py` separately unless you're testing the generator standalone.

## 📁 Project Structure

- **`app.py`** - Main Flask application (API server) - **RUN THIS FILE**
- **`main.py`** - Standalone timetable generator (for testing only)
- **`db.py`** - Database connection module
- **`generator.py`** - Core timetable generation logic
- **`constraints.py`** - Constraint validation
- **`diagnostic_check.py`** - Database diagnostic tool
- **`.env`** - Environment variables (DO NOT COMMIT)
- **`.env.example`** - Template for environment variables

## 🔑 API Endpoints

### Authentication
- `POST /api/login` - User login

### HOD (Head of Department)
- `GET /hod/dashboard` - HOD dashboard
- `POST /api/hod/generate-timetable` - Generate timetable
- `GET /api/hod/timetable` - View generated timetable
- `POST /api/hod/add-subject-with-load` - Add subject with load
- `POST /api/hod/approve-preferences` - Approve faculty preferences

### Faculty
- `GET /faculty/dashboard` - Faculty dashboard
- `POST /api/faculty/preferences` - Submit subject preferences

## 🛠️ Optional Tools

### Test Database Connection
```bash
python -c "from db import get_connection; conn = get_connection(); print('✅ Connected to Supabase!'); conn.close()"
```

### Run Diagnostic Check
```bash
python diagnostic_check.py
```

### Standalone Timetable Generation (Testing)
```bash
python main.py
```

## 🔐 Security

- Never commit `.env` file to version control
- `.env` is already in `.gitignore`
- Share `.env.example` with team members

## 📝 Notes

- The application uses **Supabase** as the PostgreSQL database
- All database credentials are loaded from environment variables
- The timetable generation happens through the API endpoint `/api/hod/generate-timetable`
- You don't need to run `main.py` unless you're testing the generator independently
