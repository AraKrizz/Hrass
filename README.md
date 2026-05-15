

# 🤖 Autonomous AI Recruitment & Job Matching Agent

> An enterprise-ready, stateful AI agent that automates the exhausting administrative pipeline of recruitment—from secure login and context-aware resume screening to automated interview scheduling.

---

## 📌 Overview

Hiring should be about human connection, but recruiters spend up to **70% of their time** acting as data entry clerks. Traditional Applicant Tracking Systems (ATS) are passive digital filing cabinets—they don't "think" contextually, and they require endless manual coordination.

This platform bridges the gap by introducing a **stateful AI workforce**. Powered by advanced LLMs and robust security layers, the agent reads resumes like a human, maintains context across the entire workflow, and automatically handles the downstream logistics of scheduling and logging.

---

## ⚡ Key Features

*   **🔒 Enterprise Security:** Frictionless onboarding via Google SSO backed by a secure multi-tenant data gateway.
*   **🧠 Stateful Decision Making:** Uses short-term memory architecture to retain candidate profiles seamlessly across multi-page workflows.
*   **👁️ Contextual Resume Screening:** Moves past rigid keyword matching to evaluate real skill sets and career trajectories using deep Chain-of-Thought (CoT) reasoning.
*   **📅 Zero-Touch Automation:** Automatically updates external trackers, fires notifications, and handles calendar scheduling the moment a candidate qualifies.

---

## 🛠️ Tech Stack & Architecture

### 🔐 Identity, Access, & Security
*   **Google OAuth 2.0:** Handles secure corporate Single Sign-On (SSO) and user profile verification.
*   **Omnium:** Functions as the central API gateway utilizing JWT Bearer tokens and strict multi-tenant isolation to safeguard sensitive applicant data.

### 🧠 Core Brain & Workflow
*   **LangGraph / CrewAI (Python):** The multi-step orchestration framework enabling the agent to work *statefully* (remembering past actions as it executes downstream steps).
*   **Gemini Pro / GPT-4o:** Advanced LLM engines driving the deep contextual screening and scoring of candidate profiles.

### 🎨 User Interface
*   **Streamlit / Gradio:** A rapid-prototype Python frontend featuring an interactive dashboard to monitor the agent's reasoning in real-time.
*   **Streamlit Session State:** Acts as the system’s short-term memory bank—retaining candidate data (e.g., matching a candidate on Page 3 and auto-populating their email invite on Page 5) without blanking out.

### 🔌 Integrations & Operational APIs
*   **ATS Simulators:** Mock endpoints delivering structured payloads to Slack/Discord webhooks to simulate active pipeline progression (Lever, LinkedIn, Indeed).
*   **Google Calendar & Sheets APIs:** Programmatically blocks interview slots and appends evaluation logs directly into central tracking spreadsheets.
*   **SendGrid / Mailgun API:** Automates outbound, personalized transactional email invitations to qualified candidates.

---

## 📐 How It Works (The Data Pipeline)

1.  **Authenticate:** The recruiter logs in securely via **Google SSO** verified through **Omnium**.
2.  **Ingest:** The recruiter drops a job description and a batch of resumes into the **Streamlit** dashboard.
3.  **Evaluate:** **LangGraph** coordinates the pipeline while **Gemini Pro/GPT-4o** utilizes Chain-of-Thought reasoning to score candidates based on context, not just buzzwords.
4.  **Execute:** The **Streamlit Session State** passes the winning candidate's details down the line, prompting the **Google Calendar**, **SendGrid**, and **Sheets APIs** to finalize the invitation and log the metrics automatically.

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   Google Cloud Console Developer Account (for OAuth and Calendar credentials)
*   Omnium API Credentials

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/ai-recruitment-agent.git](https://github.com/yourusername/ai-recruitment-agent.git)
    cd ai-recruitment-agent
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and populate your keys:
    ```env
    GOOGLE_CLIENT_ID=your_google_client_id
    OMNIUM_API_KEY=your_omnium_key
    GEMINI_API_KEY=your_gemini_key
    SENDGRID_API_KEY=your_sendgrid_key
    SLACK_WEBHOOK_URL=your_webhook_url
    ```

5.  **Run the Application:**
    ```bash
    streamlit run app.py
    ```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
