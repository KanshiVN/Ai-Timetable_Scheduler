# 🚀 How to Deploy on Vercel

Since your project is already set up with `vercel.json` and Supabase, deployment is simple!

## Option 1: Using Vercel CLI (Recommended)

1.  **Open your terminal** in this project folder.
2.  Install Vercel CLI (if not installed):
    ```bash
    npm install -g vercel
    ```
3.  Login to Vercel:
    ```bash
    vercel login
    ```
4.  Deploy:
    ```bash
    vercel
    ```
    - Follow the prompts (Select `y` to deploy, choose your scope, link to existing project: `N`, project name: `timetable-poc`, code location: `.` (current directory)).

## Option 2: Using GitHub + Vercel Dashboard

1.  **Push your code** to a GitHub repository.
2.  Go to [Vercel Dashboard](https://vercel.com/dashboard).
3.  Click **"Add New..."** -> **"Project"**.
4.  Import your GitHub repository.
5.  Vercel will auto-detect the configuration.

---

## ⚠️ CRITICAL: Environment Variables

For the app to connect to your database, you **MUST** add these Environment Variables in Vercel project settings:

**Go to:** `Settings` -> `Environment Variables` on Vercel dashboard.

Add the following keys (copy values from your local `.env` file):

| Key | Value (Example) |
| :-- | :-- |
| `SUPABASE_DB_HOST` | `db.xxxxxxxx.supabase.co` |
| `SUPABASE_DB_PORT` | `5432` |
| `SUPABASE_DB_NAME` | `postgres` |
| `SUPABASE_DB_USER` | `postgres` |
| `SUPABASE_DB_PASSWORD` | `YOUR_DB_PASSWORD` |

> **Note:** Do NOT wrap values in quotes in the Vercel dashboard.

---

## ✅ Post-Deployment

Once deployed, Vercel will give you a URL (e.g., `https://timetable-poc.vercel.app`).
Open it, and you should see the **Landing Page**!
