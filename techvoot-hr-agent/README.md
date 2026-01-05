# 🤖 Techvoot AI HR Agent
> **Automating the First Round of Recruitment with Voice AI**

## 1. Project Overview
The **Techvoot AI HR Agent** is an intelligent recruitment platform designed to automate the initial screening process. Instead of HR managers manually calling hundreds of candidates, this system:
1.  **Parses Resumes** automatically using AI.
2.  **Screens Candidates** via autonomous voice calls.
3.  **Evaluates Answers** against dynamic role-based criteria.
4.  **Filters & Exports** the best talent for the next round.

---

## 2. Key Features (The "Wow" Factors)

### 🧠 Smart Resume Parsing
*   **What it does:** Drag & drop a PDF/Word resume.
*   **AI Logic:** Automatically extracts the **Name**, **Phone**, **Email**, and detects the **Job Role** (e.g., "React Developer") by analyzing keywords.
*   **Fixes Spacing:** Includes smart heuristic algorithms to clean up broken text from PDFs (e.g., "K a r t i k" -> "Kartik").

### 📞 Autonomous Voice Screening
*   **Powered by Omnidimension:** Uses advanced LLM-based voice agents to conduct natural, human-like conversations.
*   **Dynamic Context:** The system tells the AI *who* it is calling and *what* to ask based on the candidate's profile.

### 🎯 Dynamic Hiring Rules
*   **Role-Based Logic:** HR can define specific budgets and experience levels for different roles in **Settings**.
    *   *Example:* "If WordPress, Max Budget = 39k". "If React, Max Budget = 60k".
*   **Custom Questions:** HR can inject specific technical questions (e.g., "Ask about Redux") that the AI will only ask relevant candidates.

### 📊 Premium Analytics Dashboard
*   **Visual Insights:** Interactive charts showing Call Success Rate, Status Distribution, and Daily Activity.
*   **Live Status:** Real-time tracking of candidate status (Pending, Contacted, Selected).

### 📑 Smart Export & Google Sheets Sync
*   **Automated Decision Making:** When exporting to Google Sheets, the system **automatically evaluates** the candidate based on the interview transcript and your defined budget/experience rules, marking them as "Yes" or "No" for the next round.

---

## 3. How It Works (User Flow)
1.  **Upload:** HR uploads a resume. The system auto-fills candidate details.
2.  **Configure:** HR verifies the "Hiring Rules" (Budget/Questions) in Settings.
3.  **Initiate:** HR clicks "Call Now" or "Start Queue" for bulk processing.
4.  **Interview:** The AI calls the candidate, interviews them, and logs the transcript + recording.
5.  **Analyze:** The Dashboard updates with the outcome.
6.  **Export:** HR exports the filtered list to Google Sheets for the final interview loop.

---

## 4. Technical Stack
*   **Backend:** Python (Flask)
*   **Database:** SQLite (Lightweight, Relational)
*   **AI Core:** Omnidimension API (Voice & LLM)
*   **Frontend:** HTML5, CSS3 (Glassmorphism), JavaScript (Chart.js)
*   **Integrations:** Google Sheets API, PyPDF2, python-docx

---

## 5. Setup & Installation
1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure Environment:**
    *   Add your Omnidimension API Key in `config.py`.
    *   Add your `credentials.json` for Google Sheets.
3.  **Initialize Database:**
    ```bash
    python migrate_db.py
    ```
4.  **Run Server:**
    ```bash
    python app.py
    ```
    Access at: `http://localhost:5000`

---

*Built for Techvoot Solutions*