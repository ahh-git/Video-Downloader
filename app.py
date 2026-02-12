import streamlit as st
import pandas as pd
import os
import shutil
import requests
import psutil
import plotly.express as px
from google_auth_oauthlib.flow import Flow
from db_handler import *
from downloader import get_video_info, download_video

# --- CONFIGURATION ---
ADMIN_EMAIL = "your-email@gmail.com" # <--- REPLACE THIS

st.set_page_config(page_title="UniSaver", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# --- AUTH SETUP ---
CLIENT_CONFIG = {
    "web": {
        "client_id": "859044972753-6ggdqcb5suckc4uutr081lv82fqm1buo.apps.googleusercontent.com",
        "project_id": "gen-lang-client-0416543248",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": ["https://univideosaver.streamlit.app"],
        "javascript_origins": ["https://univideosaver.streamlit.app"]
    }
}
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"]

# --- INIT ---
init_db()
if 'init_done' not in st.session_state:
    increment_visitor()
    st.session_state['init_done'] = True

# --- CLEAN UI CSS (NO EMOJIS) ---
st.markdown("""
<style>
    .stApp { background: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif; }
    
    /* Card Style */
    .glass-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Buttons */
    div.stButton > button {
        background: #3b82f6;
        color: white; border: none; border-radius: 8px; height: 45px; font-weight: 500;
        transition: background 0.2s;
    }
    div.stButton > button:hover { background: #2563eb; }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        background: #0f172a !important; color: white !important; border: 1px solid #334155 !important;
    }
    
    /* Footer Buttons */
    .footer-btn { background: transparent; color: #94a3b8; border: none; font-size: 12px; cursor: pointer; }
    .footer-btn:hover { color: #3b82f6; text-decoration: underline; }
    
    /* Cookie Box */
    .cookie-container {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: #1e293b; border-top: 1px solid #3b82f6;
        padding: 15px; text-align: center; z-index: 9999;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION ---
if 'cookies_accepted' not in st.session_state: st.session_state['cookies_accepted'] = False
if 'user' not in st.session_state: st.session_state['user'] = None

# --- AUTH LOGIC (FIXED) ---
def login_flow():
    # If already logged in, do nothing
    if st.session_state['user']: return

    # Check for code in URL
    code = st.query_params.get("code")
    if code:
        try:
            flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0])
            flow.fetch_token(code=code)
            u = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', params={'access_token': flow.credentials.token}, headers={'Authorization': f'Bearer {flow.credentials.token}'}).json()
            
            # Set Session
            st.session_state['user'] = {"email": u.get('email'), "name": u.get('name'), "photo": u.get('picture')}
            add_user(u.get('email'), u.get('name'), u.get('picture'))
            
            # Clean URL and Refresh
            st.query_params.clear()
            st.rerun()
        except:
            st.error("Authentication Error. Please try again.")

def logout(): 
    st.session_state['user'] = None
    st.rerun()

login_flow()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### UniSaver")
    
    msg, maintenance = get_config()
    if msg: st.info(msg)
    
    if st.session_state['user']:
        u = st.session_state['user']
        st.image(u['photo'], width=50)
        st.write(f"**{u['name']}**")
        
        # Profile Section
        with st.expander("My Profile"):
            joined, banned = get_user_details(u['email'])
            st.write(f"Joined: {joined}")
            st.write(f"Status: {'Active' if banned==0 else 'Restricted'}")
            
            new_name = st.text_input("Edit Name", value=u['name'])
            if st.button("Update Name"):
                update_user_name(u['email'], new_name)
                st.session_state['user']['name'] = new_name
                st.success("Name Updated")
                st.rerun()

            st.write(f"Downloads: {get_user_stats(u['email'])}")
            if st.button("Clear History"): 
                clear_user_history(u['email'])
                st.success("History Wiped")

        if st.button("Sign Out"): logout()
    else:
        st.write("Guest Access")
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0])
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.link_button("Login with Google", auth_url, use_container_width=True)

# --- MAINTENANCE MODE ---
if maintenance == 1 and (not st.session_state['user'] or st.session_state['user']['email'] != ADMIN_EMAIL):
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<div class='glass-card' style='text-align:center'>", unsafe_allow_html=True)
        st.image("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3Z6cW55cnZ6cW55ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/LdObojZLi8XWe493lq/giphy.gif", width=200)
        st.markdown("### Under Maintenance")
        st.write("We are upgrading our servers. Please check back later.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.session_state['user'] and check_ban(st.session_state['user']['email']):
    st.error("Account Suspended")
    st.stop()

# --- MAIN UI ---
tabs = ["Download", "Batch Mode"]
if st.session_state['user'] and st.session_state['user']['email'] == ADMIN_EMAIL:
    tabs.append("Admin Console")

active = st.tabs(tabs)

# --- TAB 1: DOWNLOAD ---
with active[0]:
    st.markdown("<div class='glass-card'><h3>Video Downloader</h3></div>", unsafe_allow_html=True)
    
    url = st.text_input("Paste Link Here", placeholder="https://...")
    
    if url:
        if not st.session_state['user']: st.info("Login required for high-speed downloads.")
        else:
            with st.spinner("Analyzing..."):
                info = get_video_info(url)
            
            if info:
                c1, c2 = st.columns([1, 2])
                with c1: 
                    if info.get('thumbnail'): st.image(info.get('thumbnail'), use_container_width=True)
                with c2:
                    st.write(f"**{info.get('title')}**")
                    
                    opts = {}
                    for f in info.get('formats', []):
                        if f.get('height'): opts[f"{f['height']}p ({f['ext']})"] = f['format_id']
                    
                    sorted_opts = sorted(opts.keys(), key=lambda x: int(x.split('p')[0]) if x[0].isdigit() else 0, reverse=True)
                    opts["Audio Only (MP3)"] = "bestaudio/best"
                    choice = st.selectbox("Format", ["Audio Only (MP3)"] + sorted_opts)
                    
                    if st.button("Download"):
                        with st.status("Processing...", expanded=True) as status:
                            path, title, err = download_video(url, opts.get(choice))
                            if path and os.path.exists(path):
                                status.update(label="Complete", state="complete")
                                log_download(st.session_state['user']['email'], title, url, choice)
                                mime = "audio/mpeg" if "Audio" in choice else "video/mp4"
                                with open(path, "rb") as f:
                                    st.download_button("Save File", f, file_name=os.path.basename(path), mime=mime, use_container_width=True)
                            else:
                                status.update(label="Failed", state="error")
                                st.error(err)
            else: st.error("Invalid Link")

# --- TAB 2: BATCH ---
with active[1]:
    st.markdown("<div class='glass-card'><h3>Batch Downloader</h3><p>One link per line</p></div>", unsafe_allow_html=True)
    batch = st.text_area("Links", height=150)
    if st.button("Process Batch"):
        if not st.session_state['user']: st.error("Login Required")
        else:
            links = batch.split('\n')
            for l in links:
                if l.strip():
                    info = get_video_info(l)
                    if info:
                        p, t, e = download_video(l, "best")
                        if p:
                            with open(p, "rb") as f:
                                st.download_button(f"Save {t[:10]}...", f, file_name=os.path.basename(p), key=l)

# --- TAB 3: ADMIN ---
if len(tabs) > 2:
    with active[2]:
        st.markdown("### Admin Dashboard")
        
        # Stats
        c1, c2, c3 = st.columns(3)
        c1.metric("CPU", f"{psutil.cpu_percent()}%")
        c2.metric("RAM", f"{psutil.virtual_memory().percent}%")
        c3.metric("Disk", f"{psutil.disk_usage('/').percent}%")
        
        # Chart
        st.divider()
        daily = get_daily_downloads()
        if not daily.empty:
            fig = px.bar(daily, x='timestamp', y='count')
            st.plotly_chart(fig, use_container_width=True)

        # Config
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Cookies")
            up = st.file_uploader("Upload cookies.txt", type=['txt'])
            if up:
                with open("cookies.txt", "wb") as f: f.write(up.getbuffer())
                st.success("Updated")
        with c2:
            st.markdown("#### Config")
            new_msg = st.text_input("Broadcast", value=msg)
            m_mode = st.toggle("Maintenance Mode", value=(maintenance==1))
            if st.button("Save"):
                set_config(new_msg, 1 if m_mode else 0)
                st.success("Saved")

        # Files
        st.divider()
        if os.path.exists("downloads"):
            for f in os.listdir("downloads"):
                c1, c2 = st.columns([3, 1])
                c1.write(f)
                if c2.button("Delete", key=f):
                    os.remove(f"downloads/{f}")
                    st.rerun()

# --- COOKIE CONSENT (NATIVE) ---
if not st.session_state['cookies_accepted']:
    with st.container():
        st.info("🍪 We use cookies to ensure you get the best experience.")
        if st.button("Accept Cookies"):
            st.session_state['cookies_accepted'] = True
            st.rerun()

# --- FOOTER ---
st.markdown("<br><hr>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)

# Modal Functions for Footer
@st.experimental_dialog("Terms of Service")
def show_terms():
    st.write("1. Usage Policy: Personal use only.\n2. Copyright: Do not distribute content.\n3. Liability: We are not responsible for downloads.")

@st.experimental_dialog("Privacy Policy")
def show_privacy():
    st.write("We do not store personal data other than your email for login authentication. Cookies are used for session management.")

@st.experimental_dialog("DMCA")
def show_dmca():
    st.write("If you believe content infringes your copyright, please contact the admin email to block the URL.")

with col1:
    if st.button("Terms", use_container_width=True): show_terms()
with col2:
    if st.button("Privacy", use_container_width=True): show_privacy()
with col3:
    if st.button("DMCA", use_container_width=True): show_dmca()

st.markdown("<div style='text-align:center; color:grey; margin-top:10px;'>© 2026 UniSaver. All rights reserved.</div>", unsafe_allow_html=True)
