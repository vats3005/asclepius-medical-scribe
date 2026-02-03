import streamlit as st
from groq import Groq
from fpdf import FPDF
import pandas as pd
import os
import re
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import urllib.parse
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="Asclepius V8 Clinical", page_icon="⚕️")

# --- OLYMPIAN GOLD THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@400;700&display=swap');
    
    .stApp {
        background-color: #050A10;
        background-image: 
            radial-gradient(at 10% 10%, rgba(20, 80, 100, 0.4) 0px, transparent 50%),
            radial-gradient(at 90% 0%, rgba(212, 175, 55, 0.15) 0px, transparent 50%),
            radial-gradient(at 50% 100%, rgba(10, 30, 50, 0.5) 0px, transparent 50%);
        background-attachment: fixed;
    }

    /* TYPOGRAPHY */
    h1, h2, h3 { 
        font-family: 'Cinzel', serif !important; 
        text-transform: uppercase; 
        color: #D4AF37 !important;
    }
    p, label, div, span { font-family: 'Lato', sans-serif; color: #e0e0e0; }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #0b111a;
        border-right: 1px solid #D4AF37;
    }

    /* INPUTS */
    .stTextArea textarea, .stTextInput input {
        background-color: rgba(10, 15, 20, 0.8) !important;
        border: 1px solid #444 !important;
        border-left: 3px solid #D4AF37 !important;
        color: #fff !important;
    }
    
    /* BUTTONS */
    .stButton>button {
        width: 100%;
        border: 1px solid #D4AF37;
        color: #D4AF37;
        background: transparent;
        font-family: 'Cinzel', serif;
        font-weight: 600;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #D4AF37, #B8860B);
        color: #000;
        border-color: #B8860B;
    }
    
    /* GRID HEADERS */
    .grid-header { color: #D4AF37; font-weight: bold; padding: 10px 0; border-bottom: 2px solid #D4AF37; letter-spacing: 1px; }
    .grid-row { border-bottom: 1px solid #333; padding: 15px 0; }
</style>
""", unsafe_allow_html=True)

# 2. SETTINGS ENGINE
SETTINGS_FILE = "clinic_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"doctor_name": "Dr. Strange", "email_user": "", "email_pass": ""}

def save_settings(name, email, password):
    data = {"doctor_name": name, "email_user": email, "email_pass": password}
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)
    st.session_state.doctor_name = name
    st.session_state.email_user = email
    st.session_state.email_pass = password

saved_config = load_settings()
if "doctor_name" not in st.session_state: st.session_state.doctor_name = saved_config["doctor_name"]
if "email_user" not in st.session_state: st.session_state.email_user = saved_config["email_user"]
if "email_pass" not in st.session_state: st.session_state.email_pass = saved_config["email_pass"]

# 3. DATA ENGINE (UPDATED FOR AGE & NOTES)
DB_FILE = "patient_records.csv"
COLUMNS = ["Date", "Time", "Doctor", "Patient Name", "Age", "Diagnosis", "Full_Prescription", "Doctors_Notes", "BP", "Pulse", "Weight", "Temp"]

def clean_text_forcefully(text):
    if not isinstance(text, str): return str(text)
    clean = re.sub(r'\*\*|##|\*', '', text)
    return clean.encode('ascii', 'ignore').decode('ascii')

def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=COLUMNS)
    
    df = pd.read_csv(DB_FILE)
    # Ensure new columns exist if loading old CSV
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = "--"
            
    for col in ["Patient Name", "Diagnosis", "Full_Prescription", "Doctors_Notes"]:
        df[col] = df[col].astype(str).apply(clean_text_forcefully)
        
    return df.sort_values(by=["Date", "Time"], ascending=[False, False])

def save_data(doctor, name, age, diagnosis, full_text, notes, bp, pulse, weight, temp):
    df = load_data()
    new_entry = pd.DataFrame({
        "Date": [datetime.now().strftime("%Y-%m-%d")],
        "Time": [datetime.now().strftime("%H:%M")],
        "Doctor": [doctor],
        "Patient Name": [name],
        "Age": [age],
        "Diagnosis": [diagnosis],
        "Full_Prescription": [full_text],
        "Doctors_Notes": [notes],
        "BP": [bp], "Pulse": [pulse], "Weight": [weight], "Temp": [temp]
    })
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def delete_record(index):
    df = load_data()
    df = df.drop(index)
    df.to_csv(DB_FILE, index=False)

# 4. PDF ENGINE (UPDATED LAYOUT)
def create_pdf(doctor_name, name, age, text, notes, vitals):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Times", 'B', 24)
    pdf.cell(0, 10, "ASCLEPIUS MEDICAL CENTER", ln=True, align='C')
    pdf.set_font("Times", 'I', 12)
    pdf.cell(0, 10, f"Physician: {doctor_name}", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(15)
    
    # Patient Info Row
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"Patient: {name}", ln=0)
    pdf.cell(90, 10, f"Age: {age} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=1, align='R')
    pdf.ln(5)

    # Vitals Grid
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(45, 8, f"BP: {vitals.get('BP', '--')}", 1, 0, 'C', 1)
    pdf.cell(45, 8, f"Pulse: {vitals.get('Pulse', '--')} bpm", 1, 0, 'C', 1)
    pdf.cell(45, 8, f"Weight: {vitals.get('Weight', '--')} kg", 1, 0, 'C', 1)
    pdf.cell(45, 8, f"Temp: {vitals.get('Temp', '--')} F", 1, 1, 'C', 1)
    pdf.ln(10)

    # Prescription Body
    pdf.set_font("Arial", size=11)
    clean_rx = clean_text_forcefully(text)
    
    # Remove redundant Name/Diagnosis lines from body if printed in header
    clean_lines = []
    for line in clean_rx.split('\n'):
        if "Patient Name:" not in line:
            clean_lines.append(line)
            
    for line in clean_lines:
        line = line.strip()
        if not line: pdf.ln(5); continue
        if line.endswith(":") or "Diagnosis:" in line:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, line, ln=True)
        else:
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 7, line)

    # Doctor's Notes Section
    if notes and notes.strip() != "":
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Clinical Notes / Remarks:", ln=True)
        pdf.set_font("Arial", 'I', 11)
        pdf.multi_cell(0, 7, clean_text_forcefully(notes))

    return pdf.output(dest='S').encode('latin-1')

# 5. COMMUNICATION
def send_email(sender, password, recipient, pdf_bytes, patient_name):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"Prescription for {patient_name}"
        msg.attach(MIMEText("Please find your medical prescription attached.", 'plain'))
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={patient_name}.pdf")
        msg.attach(part)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True, "Email Sent Successfully"
    except Exception as e:
        return False, str(e)

def get_whatsapp_link(phone, text):
    final_msg = f"*Prescription Summary*\n\n{text}\n\n_(Official PDF attached below)_"
    encoded = urllib.parse.quote(final_msg)
    return f"https://wa.me/{phone}?text={encoded}"

# 6. CONFIG & SECRETS
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    client = Groq(api_key="YOUR_API_KEY_HERE_IF_LOCAL")

# 7. UI NAVIGATION
with st.sidebar:
    st.title("🏛️ Asclepius V8")
    st.caption(f"Physician: {st.session_state.doctor_name}")
    st.markdown("---")
    menu = st.radio("NAVIGATION", ["Consultation Chamber", "Archive & Records", "Analytics Dashboard", "Settings"])

# --- CONSULTATION CHAMBER (UPDATED) ---
if menu == "Consultation Chamber":
    st.header(f"🎙️ Session with {st.session_state.doctor_name}")
    
    # Initialize Session State Variables
    if "draft" not in st.session_state: st.session_state.draft = None
    if "v_age" not in st.session_state: st.session_state.v_age = ""
    if "v_bp" not in st.session_state: st.session_state.v_bp = ""
    if "v_pulse" not in st.session_state: st.session_state.v_pulse = ""
    if "v_weight" not in st.session_state: st.session_state.v_weight = ""
    if "v_temp" not in st.session_state: st.session_state.v_temp = ""
    if "v_notes" not in st.session_state: st.session_state.v_notes = ""
    
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        st.markdown("### 1. Audio Input")
        audio = st.audio_input("Recorder")
        if audio and st.button("Analyze Audio ⚡"):
            transcription = client.audio.transcriptions.create(file=("rec.wav", audio), model="whisper-large-v3", response_format="text")
            
            # --- MEDICAL CROSS-CHECK PROMPT ---
            system_prompt = """
            You are an expert Medical Scribe and Editor.
            Your Goal: Create a perfect prescription.
            CRITICAL RULE: Cross-check drug names against the diagnosis.
            - If the user says "Nagstorm" for Migraine, correct it to "Naxdom" or "Naproxen".
            - If the user says "Dolo" for fever, write "Dolo-650 (Paracetamol)".
            - Fix phonetic errors.
            Format:
            Patient Name: [Name]
            Diagnosis: [Diagnosis]
            Rx: [Medications with dosage]
            """
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": transcription}]
            )
            st.session_state.draft = clean_text_forcefully(res.choices[0].message.content)
            st.rerun()
            
    with col2:
        st.markdown("### 2. Vitals & Patient Info")
        # NEW: 5-Column Grid (Age + Vitals)
        v0, v1, v2, v3, v4 = st.columns(5)
        st.session_state.v_age = v0.text_input("Age", st.session_state.v_age)
        st.session_state.v_bp = v1.text_input("BP", st.session_state.v_bp)
        st.session_state.v_pulse = v2.text_input("Pulse", st.session_state.v_pulse)
        st.session_state.v_weight = v3.text_input("Weight", st.session_state.v_weight)
        st.session_state.v_temp = v4.text_input("Temp", st.session_state.v_temp)

        st.markdown("### 3. Prescription & Notes")
        if st.session_state.draft:
            body = st.text_area("Prescription Draft", st.session_state.draft, height=300)
            
            # NEW: Doctor's Notes
            notes = st.text_area("👨‍⚕️ Doctor's Private Notes / Remarks (Optional)", st.session_state.v_notes, height=100)
            
            # Parsing for Auto-Title
            name = "Unknown"
            if "Patient Name:" in body: name = body.split("Patient Name:")[1].split("\n")[0].strip()
            diag = "Pending"
            if "Diagnosis:" in body: diag = body.split("Diagnosis:")[1].split("\n")[0].strip()
            
            if st.button("✅ Finalize & Archive"):
                save_data(st.session_state.doctor_name, name, st.session_state.v_age, diag, body, notes,
                          st.session_state.v_bp, st.session_state.v_pulse, st.session_state.v_weight, st.session_state.v_temp)
                st.success("Record Archived Successfully!")
                # Reset fields
                st.session_state.v_age = ""
                st.session_state.v_bp = ""
                st.session_state.v_pulse = ""
                st.session_state.v_weight = ""
                st.session_state.v_temp = ""
                st.session_state.v_notes = ""
                st.rerun()

# --- ARCHIVES ---
elif menu == "Archive & Records":
    st.header("📂 Archives")
    df = load_data()
    
    if not df.empty:
        c1, c2, c3, c4 = st.columns([2, 2, 4, 3])
        c1.markdown("<div class='grid-header'>DATE</div>", unsafe_allow_html=True)
        c2.markdown("<div class='grid-header'>TIME</div>", unsafe_allow_html=True)
        c3.markdown("<div class='grid-header'>PATIENT</div>", unsafe_allow_html=True)
        c4.markdown("<div class='grid-header'>ACTIONS</div>", unsafe_allow_html=True)
        
        for index, row in df.iterrows():
            st.markdown("<div class='grid-row'>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([2, 2, 4, 3])
            
            c1.write(f"📅 {row['Date']}")
            c2.write(f"🕒 {row['Time']}")
            # Show Name AND Age in the list
            age_display = f"(Age: {row['Age']})" if row['Age'] and row['Age'] != "--" else ""
            c3.markdown(f"**{row['Patient Name']}** {age_display}\n\n_{row['Diagnosis']}_")
            
            with c4:
                b1, b2 = st.columns(2)
                # Pack vitals & notes for PDF
                vitals_dict = {"BP": row.get("BP", "--"), "Pulse": row.get("Pulse", "--"), "Weight": row.get("Weight", "--"), "Temp": row.get("Temp", "--")}
                pdf_data = create_pdf(row['Doctor'], row['Patient Name'], row['Age'], row['Full_Prescription'], row.get('Doctors_Notes', ''), vitals_dict)
                b1.download_button("📄 PDF", pdf_data, file_name=f"{row['Patient Name']}.pdf", key=f"pdf_{index}")
                
                if b2.button("🗑️ DEL", key=f"del_{index}"):
                    delete_record(index)
                    st.rerun()
            
            with st.expander(f"📤 Send to {row['Patient Name']}"):
                s1, s2 = st.columns(2)
                with s1:
                    st.markdown("**WhatsApp**")
                    ph = st.text_input("Phone", key=f"ph_{index}")
                    if ph:
                        link = get_whatsapp_link(ph, row['Full_Prescription'])
                        st.markdown(f"[**➤ Open Chat**]({link})")
                with s2:
                    st.markdown("**Email**")
                    em = st.text_input("Email", key=f"em_{index}")
                    if st.button("Send 📧", key=f"snd_{index}"):
                        if st.session_state.email_user:
                            suc, msg = send_email(st.session_state.email_user, st.session_state.email_pass, em, pdf_data, row['Patient Name'])
                            if suc: st.success("Sent!")
                            else: st.error(msg)
                        else: st.error("Configure Settings.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No records found.")

# --- ANALYTICS ---
elif menu == "Analytics Dashboard":
    st.header("📊 Clinic Analytics")
    df = load_data()
    
    if df.empty:
        st.warning("Not enough data.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Patients", len(df))
        m2.metric("Patients Today", len(df[df['Date'] == datetime.now().strftime("%Y-%m-%d")]))
        m3.metric("Top Diagnosis", df['Diagnosis'].mode()[0] if not df['Diagnosis'].empty else "N/A")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Disease Prevalence")
            st.bar_chart(df['Diagnosis'].value_counts(), color="#D4AF37")
        with c2:
            st.subheader("Patient Traffic")
            st.line_chart(df['Date'].value_counts().sort_index(), color="#D4AF37")

# --- SETTINGS ---
elif menu == "Settings":
    st.header("⚙️ Settings")
    new_name = st.text_input("Physician Name", value=st.session_state.doctor_name)
    e_user = st.text_input("Gmail", value=st.session_state.email_user)
    e_pass = st.text_input("App Password", value=st.session_state.email_pass, type="password")
    
    if st.button("Save Settings"):
        save_settings(new_name, e_user, e_pass)
        st.success("Saved!")
        st.rerun()
