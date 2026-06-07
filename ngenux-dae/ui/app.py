import os
import streamlit as st
import requests
import json
from datetime import datetime

# Configure the page
st.set_page_config(page_title="Ngenux DAE Manager", layout="wide")

# Backend API URL — overridden by API_BASE_URL env var in Docker
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

def apply_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif !important;
            }

            .stApp {
                background: radial-gradient(circle at 15% 50%, rgba(45, 20, 75, 0.6), rgba(15, 15, 20, 1) 40%),
                            radial-gradient(circle at 85% 30%, rgba(20, 60, 80, 0.5), rgba(15, 15, 20, 1) 40%);
                background-color: #0d0d12;
                color: #e0e0e0;
            }

            section[data-testid="stSidebar"] {
                background-color: rgba(20, 20, 30, 0.4) !important;
                backdrop-filter: blur(12px) !important;
                -webkit-backdrop-filter: blur(12px) !important;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }

            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}

            div.stButton > button {
                background: linear-gradient(135deg, rgba(100, 50, 200, 0.8), rgba(50, 100, 200, 0.8));
                color: white !important;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 0.6rem 1.2rem;
                font-weight: 600;
                transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            }
            div.stButton > button:hover {
                transform: translateY(-2px) scale(1.02);
                box-shadow: 0 8px 25px rgba(100, 100, 250, 0.5);
                border-color: rgba(255, 255, 255, 0.3);
            }
            div.stButton > button:active {
                transform: translateY(1px) scale(0.98);
            }

            .stTextInput > div > div > input,
            .stTextArea > div > textarea,
            .stSelectbox > div > div {
                background-color: rgba(30, 30, 45, 0.6) !important;
                color: #fff !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 6px !important;
                transition: all 0.2s ease !important;
            }
            .stTextInput > div > div > input:focus,
            .stTextArea > div > textarea:focus {
                border-color: rgba(100, 150, 255, 0.5) !important;
                box-shadow: 0 0 10px rgba(100, 150, 255, 0.2) !important;
            }

            div[data-testid="stMetric"] {
                background: rgba(30, 30, 40, 0.5);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 1rem;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            div[data-testid="stMetric"]:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3), 0 0 15px rgba(100, 150, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            .stDataFrame, div[data-testid="stJson"] {
                background: rgba(20, 20, 30, 0.4) !important;
                border-radius: 8px;
                padding: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)

apply_custom_css()

# ── Decision type templates (auto-populate facts JSON) ────────────────────────
DECISION_TEMPLATES = {
    "LOAN_APPROVAL": {
        "credit_score": 750,
        "income": 50000
    },
    "HR_HIRING": {
        "years_experience": 3,
        "degree": "Bachelor"
    },
    "INSURANCE_CLAIM": {
        "claim_amount": 20000,
        "days_since_incident": 10,
        "policy_active": True
    },
    "VENDOR_ONBOARDING": {
        "compliance_score": 80,
        "years_in_business": 4,
        "blacklisted": False
    },
    "EMPLOYEE_LEAVE": {
        "days_requested": 5,
        "notice_days_given": 3,
        "leave_balance_remaining": 12
    }
}

st.title("Ngenux DAE Manager")

# Sidebar navigation via dropdown
view = st.sidebar.selectbox(
    "Navigation",
    ["Execute Decision", "List Decisions", "Decision Detail"]
)

# ─────────────────────────────────────────────────────────────────────────────
# VIEW 1: Execute Decision
# ─────────────────────────────────────────────────────────────────────────────
if view == "Execute Decision":
    st.header("Execute Decision")

    # Decision type dropdown OUTSIDE the form so it reactively changes the JSON
    col1, col2 = st.columns(2)
    request_id = col1.text_input("Request ID", value=f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    decision_type = col2.selectbox(
        "Decision Type",
        list(DECISION_TEMPLATES.keys())
    )

    # Auto-populate the facts JSON when the decision type changes
    default_facts = json.dumps(DECISION_TEMPLATES[decision_type], indent=2)

    with st.form("execute_decision_form"):
        st.subheader("Actor Info")
        col3, col4 = st.columns(2)
        actor_id = col3.text_input("Actor ID", value="system_agent_1")
        actor_role = col4.text_input("Actor Role", value="system")

        st.subheader("Policy Reference")
        policy_version = st.text_input("Policy Version", value="v1.0")

        st.subheader("Context Facts")
        facts_json = st.text_area(
            "Facts (JSON Format — auto-populated from selected type)",
            value=default_facts,
            height=160
        )

        submitted = st.form_submit_button("🚀 Submit Decision Request")

        if submitted:
            try:
                facts_dict = json.loads(facts_json)
                payload = {
                    "request_info": {
                        "request_id": request_id,
                        "decision_type": decision_type
                    },
                    "actor_info": {
                        "actor_id": actor_id,
                        "role": actor_role
                    },
                    "policy_reference": {
                        "policy_version": policy_version
                    },
                    "context_facts": {
                        "facts": facts_dict
                    }
                }

                response = requests.post(f"{API_BASE_URL}/decisions", json=payload)
                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status", "UNKNOWN")
                    if status == "APPROVED" or status == "HIRED":
                        st.success(f"✅ Decision Result: **{status}**")
                    else:
                        st.error(f"❌ Decision Result: **{status}**")
                    st.json(result)
                else:
                    st.error(f"Error submitting decision: {response.text}")

            except json.JSONDecodeError:
                st.error("Invalid JSON provided in the Context Facts field.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# ─────────────────────────────────────────────────────────────────────────────
# VIEW 2: List Decisions
# ─────────────────────────────────────────────────────────────────────────────
elif view == "List Decisions":
    st.header("Decision History")

    try:
        response = requests.get(f"{API_BASE_URL}/decisions")
        if response.status_code == 200:
            decisions = response.json()
            if decisions:
                display_data = []
                for d in decisions:
                    display_data.append({
                        "Decision ID": d["decision_id"],
                        "Request ID": d["request_id"],
                        "Type": d["decision_type"],
                        "Status": d["status"]
                    })
                st.dataframe(display_data, use_container_width=True)
                st.info("To view details, copy a Decision ID and navigate to the 'Decision Detail' view.")
            else:
                st.write("No decisions found in the database.")
        else:
            st.error(f"Failed to fetch decisions: {response.text}")
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the backend. Is the FastAPI server running?")

# ─────────────────────────────────────────────────────────────────────────────
# VIEW 3: Decision Detail
# ─────────────────────────────────────────────────────────────────────────────
elif view == "Decision Detail":
    st.header("Decision Detail")

    st.write("Enter a Decision ID to view its complete logs and payload.")
    decision_id_input = st.text_input("Decision ID")

    if st.button("Fetch Details") and decision_id_input:
        try:
            response = requests.get(f"{API_BASE_URL}/decisions/{decision_id_input}")
            if response.status_code == 200:
                detail = response.json()

                col1, col2, col3 = st.columns(3)
                col1.metric("Status", detail["status"])
                col2.metric("Decision Type", detail["decision_type"])
                col3.metric("Policy Used", detail["policy_version_used"])

                st.divider()

                colA, colB = st.columns(2)
                with colA:
                    st.subheader("Input Context")
                    st.json(detail["input_context"])
                with colB:
                    st.subheader("Output Result")
                    st.json(detail["output_result"])

                st.divider()

                colC, colD = st.columns(2)
                with colC:
                    st.subheader("🧠 Structured Explanation")
                    explanation = detail.get("explanation", {})
                    if explanation:
                        st.info(explanation.get("reason", "No reason provided."))
                        details = explanation.get("details", {})
                        if details:
                            st.json(details)
                    else:
                        st.write("No explanation available.")
                with colD:
                    st.subheader("📊 Execution Metadata")
                    metadata = detail.get("execution_metadata", {})
                    if metadata:
                        m1, m2 = st.columns(2)
                        m1.metric("Latency", f"{metadata.get('latency_ms', 0):.2f} ms")
                        m2.metric("Cost", f"${metadata.get('cost_usd', 0):.4f}")
                    else:
                        st.write("No metadata available.")

                st.divider()

                st.subheader("Audit Logs")
                if detail["audit_logs"]:
                    log_data = []
                    for log in detail["audit_logs"]:
                        log_data.append({
                            "Timestamp": log["timestamp"],
                            "Action": log["action"],
                            "Actor": log["actor"]
                        })
                    st.table(log_data)
                else:
                    st.write("No audit logs found for this decision.")

            elif response.status_code == 404:
                st.warning("Decision not found.")
            else:
                st.error(f"Error fetching decision: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the backend. Is the FastAPI server running?")
