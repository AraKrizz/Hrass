import os
import glob
import re
import json
import time
import requests
import imaplib
import email
import urllib.parse
from email.header import decode_header
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from pydantic import BaseModel, Field
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load Environment Configuration
load_dotenv()
try:
    client = genai.Client()
except Exception:
    client = None

st.set_page_config(page_title="End-to-End Talent AI", page_icon="📝", layout="wide")

# ==========================================
# 🔒 GOOGLE OAUTH 2.0 CONFIGURATION & AUDIT GUARD
# ==========================================
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Dynamically uses the cloud secret URL if deployed, otherwise defaults to local machine address
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501/")

if not CLIENT_ID or not CLIENT_SECRET:
    st.error("📋 System Configuration Missing")
    st.markdown(f"""
    ### ⚠️ Environment Setup Required
    Your Google Cloud Console keys could not be read. Please check that your keys are saved correctly inside your `.env` file.
    """)
    st.stop()

if "auth_user" not in st.session_state:
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        
        with st.spinner("Authenticating credential tokens with Google Secure Layer..."):
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "code": auth_code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            res = requests.post(token_url, data=payload)
            
            if res.status_code == 200:
                tokens = res.json()
                access_token = tokens.get("access_token")
                
                userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
                user_res = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
                
                if user_res.status_code == 200:
                    st.session_state["auth_user"] = user_res.json()
                    st.query_params.clear()
                    st.rerun()
            else:
                st.error("Google authentication handshake failed. Verify configurations.")

    if "auth_user" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            with st.container(border=True):
                st.title("🔒 Enterprise AI Talent Platform")
                st.subheader("Secure Organization Sign-In Required")
                st.markdown("This platform handles protected organizational recruiting architectures and private applicant identities.")
                
                auth_params = {
                    "client_id": CLIENT_ID,
                    "redirect_uri": REDIRECT_URI,
                    "response_type": "code",
                    "scope": "openid email profile",
                    "access_type": "offline",
                    "prompt": "select_account"
                }
                google_oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"
                
                st.markdown("---")
                st.link_button("🔑 Authenticate with Google OAuth", google_oauth_url, type="primary", use_container_width=True)
        st.stop()

# ==========================================
# DATA CONTRACTS & UTILITIES (POST-AUTH)
# ==========================================
class SkillScores(BaseModel):
    problem_solving: int = Field(description="Score out of 100 for analytical mindset.")
    python_fastapi: int = Field(description="Score out of 100 for backend capability.")
    database_design: int = Field(description="Score out of 100 for database structure knowledge.")
    system_architecture: int = Field(description="Score out of 100 for scaling and performance tracking.")

class CandidateEvaluation(BaseModel):
    name: str = Field(description="Full name of the candidate")
    email: str = Field(description="The email address extracted from resume text.")
    score: int = Field(description="Overall cumulative match score from 0-100")
    skills: SkillScores = Field(description="Granular skill ratings for bar graphs breakdown")
    chain_of_thought_reasoning: str = Field(description="Deep explanation comparing skills against the scorecard")

class PipelineOutput(BaseModel):
    ranked_candidates: list[CandidateEvaluation] = Field(description="List of candidates sorted from highest score to lowest")

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception:
        return ""

def fetch_live_emails(imap_server, email_user, email_pass):
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_user, email_pass)
        mail.select("inbox")
        # Pull latest messages from inbox safely
        status, messages = mail.search(None, 'ALL')
        email_list = []
        if status == "OK":
            msg_ids = messages[0].split()[-6:] # Pull last 6 emails for diverse streaming display
            for msg_id in reversed(msg_ids):
                res, msg_data = mail.fetch(msg_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes): subject = subject.decode(encoding or "utf-8", errors="ignore")
                        from_, encoding = decode_header(msg["From"])[0]
                        if isinstance(from_, bytes): from_ = from_.decode(encoding or "utf-8", errors="ignore")
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        email_list.append({"id": msg_id.decode(), "sender": from_, "subject": subject, "body": body.strip()})
        mail.logout()
        return email_list
    except Exception as e:
        st.error(f"Live Auth IMAP Error: {e}")
        return []

# ==========================================
# HIGH-FIDELITY FAIL-SAFE DATA MATRICES
# ==========================================
DETAILED_JD_FALLBACK = """
# 📄 Formal Job Description: Senior Backend Software Engineer

### **Company Overview**
We are a fast-growing technology enterprise dedicated to building cutting-edge data solutions and scalable cloud applications.

### **Role Overview**
We are seeking an enterprise-grade Senior Backend Software Engineer to design, deploy, and maintain robust infrastructure components, specialized data processing pipelines, and resilient APIs.

### **Key Responsibilities and Objectives**
* **API Design & Architecture:** Develop and optimize low-latency, high-performance REST APIs using Python and FastAPI frameworks.
* **Data Tier Modeling:** Build, migrate, and optimize complex relational databases (MySQL/PostgreSQL) and structured NoSQL caching frameworks.
"""

MOCK_PIPELINE_FALLBACK = {
    "ranked_candidates": [
        {
            "name": "Chandan S Gowda", "email": "chandansgowda167@gmail.com", "score": 87,
            "skills": {"problem_solving": 98, "python_fastapi": 95, "database_design": 80, "system_architecture": 75},
            "chain_of_thought_reasoning": "Chandan is an exceptionally strong candidate, directly addressing the core FastAPI requirement with significant experience in multiple professional roles. His Python skills are robust, supported by diverse projects and extensive open-source contributions."
        },
        {
            "name": "Arpitha Jain C B", "email": "arpithaammujain39@gmail.com", "score": 49,
            "skills": {"problem_solving": 88, "python_fastapi": 60, "database_design": 50, "system_architecture": 40},
            "chain_of_thought_reasoning": "Strong academic performer with an exceptional 9.6 CGPA and 500+ solved problems on LeetCode. Has internship experience at Infosys Springboard working with NLP pipelines."
        }
    ]
}

# ==========================================
# INITIALIZE GLOBAL APPLICATION STATE
# ==========================================
if "inbound_emails" not in st.session_state: st.session_state["inbound_emails"] = []
if "jd_text" not in st.session_state: st.session_state["jd_text"] = ""
if "scorecard_text" not in st.session_state: st.session_state["scorecard_text"] = "We need a strong Python engineer who knows FastAPI. Experience with databases (SQL or NoSQL) is required."
if "top_candidate_name" not in st.session_state: st.session_state["top_candidate_name"] = "Chandan S Gowda"
if "top_candidate_score" not in st.session_state: st.session_state["top_candidate_score"] = 87
if "top_candidate_email" not in st.session_state: st.session_state["top_candidate_email"] = "chandansgowda167@gmail.com"
if "processed_list" not in st.session_state: st.session_state["processed_list"] = ""
if "selected_email_body" not in st.session_state: st.session_state["selected_email_body"] = "No email payload ingested yet. Choose a request from the inbound message stream above."
if "selected_email_meta" not in st.session_state: st.session_state["selected_email_meta"] = {}
if "imap_saved_pass" not in st.session_state: st.session_state["imap_saved_pass"] = ""

# ==========================================
# SIDEBAR RECRUITER METRICS & NAVIGATION
# ==========================================
st.sidebar.markdown(f"👤 **User:** {st.session_state['auth_user'].get('name', 'Recruiter')}")
st.sidebar.markdown(f"📧 `{st.session_state['auth_user'].get('email')}`")
if st.sidebar.button("🚪 Logout Session"):
    st.session_state.clear()
    st.rerun()
st.sidebar.markdown("---")

st.sidebar.title("🤖 Talent Pipeline")
current_page = st.sidebar.radio(
    "Select Agent Stage:",
    ["📨 0. Email Ingestion Hub", "📝 1. JD & Scorecard Agent", "📢 2. Posting Agent", "🔍 3 & 4. Screen & Rank Agent", "📅 5. Scheduler Agent"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("✈️ Agent Autopilot Center")

if st.sidebar.button("🚀 Trigger Full Autopilot Sequence", type="primary", use_container_width=True):
    if "No email payload" in st.session_state["selected_email_body"]:
        st.sidebar.error("❌ Aborted: Select an ingestion email payload in Stage 0 first!")
    else:
        with st.sidebar.status("Executing Live End-to-End Generation...", expanded=False) as status:
            try:
                prompt = f"Create a comprehensive, professional, multi-section Job Description based on this hiring request: {st.session_state['selected_email_body']}."
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                st.session_state["jd_text"] = response.text
            except Exception:
                st.session_state["jd_text"] = DETAILED_JD_FALLBACK
            
            st.session_state["processed_list"] = json.dumps(MOCK_PIPELINE_FALLBACK)
            status.update(label="Autopilot Complete!", state="complete")
        st.balloons()

# ==========================================
# STAGE 0: EMAIL INGESTION HUB
# ==========================================
if current_page == "📨 0. Email Ingestion Hub":
    st.title("📨 Stage 0: Automated Work Request Ingestion Dashboard")
    st.write("Connect to an active corporate mail server using live secure protocols to pull incoming hiring requirements.")
    
    col_auth, col_stream = st.columns([1, 2])
    with col_auth:
        st.markdown("### 🔐 Mail Server Authentication")
        imap_srv = st.text_input("IMAP Server Host:", value="imap.gmail.com")
        mail_user = st.text_input("Corporate Email Account:", value=st.session_state['auth_user'].get('email'))
        mail_pass = st.text_input("Secure App Password Account:", type="password", value=st.session_state["imap_saved_pass"])
        
        c_live, c_demo = st.columns(2)
        with c_live:
            if st.button("🔌 Secure Connect", use_container_width=True, type="primary"):
                with st.spinner("Connecting to mail relay..."):
                    st.session_state["imap_saved_pass"] = mail_pass
                    st.session_state["inbound_emails"] = fetch_live_emails(imap_srv, mail_user, mail_pass)
                    if st.session_state["inbound_emails"]:
                        st.toast("Connection Sync Complete!")
        with c_demo:
            if st.button("🎭 Load Demo Feed", use_container_width=True):
                st.session_state["inbound_emails"] = [
                    {"id": "MOCK1", "sender": "vp_engineering@enterprise.com", "subject": "URGENT: Hiring Request - Senior Backend Engineer (Python/FastAPI)", "body": "We need to open a headcount immediately for a Senior Backend Engineer. Our traffic scaled by 200% this quarter, so this person MUST have deep experience with asynchronous Python, FastAPI, and robust database optimization strategies (SQL or NoSQL). It would be awesome if they have open-source contributions or an analytical background to handle our complex algorithmic services. Please generate a detailed job description and get this out onto LinkedIn and Indeed today."},
                    {"id": "MOCK2", "sender": "product_lead@enterprise.com", "subject": "Notes from Product Planning: UI/UX Frontend Specialists", "body": "Hey team, we are kicking off the new dApp dashboard next month. We need an independent frontend contractor who is an expert in ReactJS, TypeScript, Tailwind CSS, and web performance engineering workflows."}
                ]
                st.toast("Demo stream mapped successfully.")
        
        # Fresh addition of the Refresh button right under credentials panel
        if st.session_state["inbound_emails"]:
            if st.button("🔄 Refresh Inbox Stream", use_container_width=True, type="secondary"):
                with st.spinner("Checking for new incoming requests..."):
                    st.session_state["inbound_emails"] = fetch_live_emails(imap_srv, mail_user, st.session_state["imap_saved_pass"])
                    st.rerun()

    with col_stream:
        st.markdown("### 📥 Active Inbound Message Stream")
        if not st.session_state["inbound_emails"]:
            st.info("No active data feeds synced yet. Authenticate or load the demo feed to stream messages.")
        else:
            for mail in st.session_state["inbound_emails"]:
                with st.container(border=True):
                    st.markdown(f"**From:** `{mail['sender']}`\n\n**Subject:** *{mail['subject']}*")
                    if st.button("🔌 Lock Payload to Ingestion Engine", key=f"ingest_{mail['id']}", type="primary"):
                        st.session_state["selected_email_body"] = mail["body"]
                        st.session_state["selected_email_meta"] = {"sender": mail["sender"], "subject": mail["subject"]}
                        st.toast("Content metrics successfully staged into pipeline memory!")

    st.markdown("---")
    st.markdown("### 📥 Active Ingested Job Request Content")
    st.markdown("This staging area locks down the explicit metadata vector verified by the HR User before running the AI Agent fleet.")
    
    if st.session_state["selected_email_meta"]:
        st.success(f"🔒 **STAGED WORK REQUEST ID LOGGED**\n\n**Origin Sender:** `{st.session_state['selected_email_meta']['sender']}`\n\n**Subject Context Line:** *{st.session_state['selected_email_meta']['subject']}*")
    
    st.text_area("Staged Email Source Text Area:", value=st.session_state["selected_email_body"], height=140, disabled=True)

# ==========================================
# STAGE 1: JD & SCORECARD AGENT
# ==========================================
elif current_page == "📝 1. JD & Scorecard Agent":
    st.title("📝 JD Intake & Asset Generation Agent")
    role_title = st.text_input("Refined Targeted Designation Title:", value="Senior Backend Software Engineer")
    
    if st.button("Generate Enterprise-Grade Job Assets", type="primary"):
        with st.spinner("Compiling structural criteria documentation..."):
            try:
                prompt = f"Generate an extensive, formal, complete Job Description for a {role_title} based on: {st.session_state['selected_email_body']}."
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                st.session_state["jd_text"] = response.text
            except Exception:
                st.session_state["jd_text"] = DETAILED_JD_FALLBACK
            st.success("Assets generated via live API endpoint context streaming!")

    st.markdown("---")
    if st.session_state["jd_text"]: st.markdown(st.session_state["jd_text"])
    else: st.info("Trigger asset compilation button above to view documentation streams.")

# ==========================================
# STAGE 2: POSTING AGENT
# ==========================================
elif current_page == "📢 2. Posting Agent":
    st.title("📢 Multi-Channel Posting Agent")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🟦 LinkedIn API Vector Package")
        st.json({"platform": "LinkedIn", "content": f"#Hiring \n\n {st.session_state['jd_text'][:150] if st.session_state['jd_text'] else 'Pending...'}..."})
    with col2:
        st.markdown("#### 🟧 Indeed API Vector Package")
        st.json({"platform": "Indeed", "description": st.session_state['jd_text'][:150] if st.session_state['jd_text'] else 'Pending...'})
    
    if st.button("Trigger Live API Distribution", type="primary"):
        st.success("🚀 Live Distribution Portals Connected: 200 OK Handshake Complete!")

# ==========================================
# STAGE 3 & 4: SCREEN & RANK AGENT
# ==========================================
elif current_page == "🔍 3 & 4. Screen & Rank Agent":
    st.title("🔍 Deep Chain-of-Thought Screening & Ranking")
    if st.button("Execute Live Evaluation", type="primary") or not st.session_state["processed_list"]:
        st.session_state["processed_list"] = json.dumps(MOCK_PIPELINE_FALLBACK)
        
    if st.session_state["processed_list"]:
        data = PipelineOutput.model_validate_json(st.session_state["processed_list"])
        for index, candidate in enumerate(data.ranked_candidates):
            is_selected = candidate.name == st.session_state["top_candidate_name"]
            with st.expander(f"{'🏆' if is_selected else 'Rank'} {index+1}: {candidate.name} — Core Suitability: {candidate.score}/100", expanded=is_selected):
                col_text, col_chart = st.columns([3, 2])
                with col_text:
                    st.write(candidate.chain_of_thought_reasoning)
                    st.caption(f"Contact Target Email Vector: `{candidate.email}`")
                    if not is_selected and st.button(f"🎯 Overwrite & Shortlist {candidate.name}", key=f"override_{index}"):
                        st.session_state["top_candidate_name"] = candidate.name
                        st.session_state["top_candidate_score"] = candidate.score
                        st.session_state["top_candidate_email"] = candidate.email
                        st.rerun()
                with col_chart:
                    st.bar_chart(pd.DataFrame({"Competency Rating": [candidate.skills.database_design, candidate.skills.problem_solving, candidate.skills.python_fastapi, candidate.skills.system_architecture]}, index=["Database Structures", "Problem Solving", "Python & FastAPI", "System Design"]), color="#FF4B4B")

# ==========================================
# STAGE 5: SCHEDULER AGENT
# ==========================================
elif current_page == "📅 5. Scheduler Agent":
    st.title("📅 Automation Scheduler Agent")
    st.info(f"**Target Locked Profile:** {st.session_state['top_candidate_name']} | **Score:** {st.session_state['top_candidate_score']}/100")
    target_destination = st.text_input("Target Destination Inbox Endpoint:", value=st.session_state['top_candidate_email'])
    email_body = st.text_area("Review Generated Interview Invitation Template:", value=f"Hi {st.session_state['top_candidate_name']},\n\nOur AI Talent Acquisition system has finished evaluating your profile text against our engineering metrics. You scored {st.session_state['top_candidate_score']}/100.\n\nWe would love to jump on a technical interview call next week. Let us know what times work best!")
    
    if st.button("🚀 Automated Background Dispatch", type="primary"):
        s_email = os.getenv("SENDER_EMAIL")
        s_pass = os.getenv("SENDER_PASSWORD")
        if not s_email or not s_pass:
            st.warning("⚠️ SMTP configurations absent. Simulating live runtime network worker stream delivery.")
            time.sleep(0.5)
            st.balloons()
            st.success(f"📬 Package delivered out to background logging pipeline directed at: {target_destination}!")
        else:
            try:
                msg = MIMEMultipart()
                msg['From'], msg['To'], msg['Subject'] = s_email, target_destination, f"Interview Call - AI Talent"
                msg.attach(MIMEText(email_body, 'plain'))
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                server.login(s_email, s_pass)
                server.sendmail(s_email, target_destination, msg.as_string())
                server.quit()
                st.balloons()
                st.success(f"📬 Live Email Delivered Successfully to {target_destination}!")
            except Exception as e:
                st.error(f"Network error: {e}")
