import os
import streamlit as st
import requests
import json
from datetime import datetime

# Configure the page
st.set_page_config(page_title="Ngenux DAE Manager", layout="wide")

# Backend API URL — overridden by API_BASE_URL env var in Docker
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.title("Ngenux DAE Manager")

# Sidebar navigation
view = st.sidebar.radio(
    "Navigation",
    ["Execute Decision", "List Decisions", "Decision Detail"]
)

# --- Execute Decision View ---
if view == "Execute Decision":
    st.header("Execute Decision")
    
    with st.form("execute_decision_form"):
        st.subheader("Request Info")
        col1, col2 = st.columns(2)
        request_id = col1.text_input("Request ID", value=f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        decision_type = col2.text_input("Decision Type", value="LOAN_APPROVAL")
        
        st.subheader("Actor Info")
        col3, col4 = st.columns(2)
        actor_id = col3.text_input("Actor ID", value="system_agent_1")
        actor_role = col4.text_input("Actor Role", value="system")
        
        st.subheader("Policy Reference")
        policy_version = st.text_input("Policy Version", value="v1.0")
        
        st.subheader("Context Facts")
        facts_json = st.text_area("Facts (JSON Format)", value='{"credit_score": 750, "income": 50000}')
        
        submitted = st.form_submit_button("Submit Decision Request")
        
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
                    st.success("Decision successfully submitted!")
                    st.json(response.json())
                else:
                    st.error(f"Error submitting decision: {response.text}")
                    
            except json.JSONDecodeError:
                st.error("Invalid JSON provided in the Context Facts field.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# --- List Decisions View ---
elif view == "List Decisions":
    st.header("Decision History")
    
    try:
        response = requests.get(f"{API_BASE_URL}/decisions")
        if response.status_code == 200:
            decisions = response.json()
            if decisions:
                # Format for display in a dataframe
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

# --- Decision Detail View ---
elif view == "Decision Detail":
    st.header("Decision Detail")
    
    st.write("Enter a Decision ID to view its complete logs and payload.")
    decision_id_input = st.text_input("Decision ID")
    
    if st.button("Fetch Details") and decision_id_input:
        try:
            response = requests.get(f"{API_BASE_URL}/decisions/{decision_id_input}")
            if response.status_code == 200:
                detail = response.json()
                
                # Top metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", detail["status"])
                col2.metric("Decision Type", detail["decision_type"])
                col3.metric("Policy Used", detail["policy_version_used"])
                
                st.divider()
                
                # Context and Results
                colA, colB = st.columns(2)
                with colA:
                    st.subheader("Input Context")
                    st.json(detail["input_context"])
                with colB:
                    st.subheader("Output Result")
                    st.json(detail["output_result"])
                
                st.divider()

                # Explanation and Execution Metadata
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
                
                # Audit Logs
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
