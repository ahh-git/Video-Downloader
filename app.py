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
ADMIN_EMAIL = "your-email@gmail.com" # <--- REPLACE WITH YOUR REAL EMAIL

st.set_page_config(page_title="UniSaver Pro", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

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

# --- GLOBAL STYLES & ANIMATIONS ---
st.markdown("""
<style>
    /* Dark Theme & Glassmorphism */
    .stApp { background: radial-gradient(circle at top left, #1e293b, #0f172a); color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    /* Animations */
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    .animate { animation: fadeInUp 0.6s ease-out; }
    
    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white; border: none; border-radius: 12px; height: 50px; font-weight: 600; width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(59, 130, 246, 0.4); }
    div.stButton > button:active { transform: scale(0.98); }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        background: #0f172a !important; color: white !important; border: 1px solid #334155 !important; border-radius: 12px;
    }
    
    /* Cookie Popup */
    .cookie-box {
        position: fixed; bottom: 20px; right: 20px;
        background: rgba(15, 23, 42, 0.95); padding: 20px; border-radius: 15px; border: 1px solid #3b82f6;
        z-index: 9999; max-width: 300px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATES ---
if 'cookies_accepted' not in st.session_state: st.session_state['cookies_accepted'] = False
if 'user' not in st.session_state: st.session_state['user'] = None
if 'remember_me' not in st.session_state: st.session_state['remember_me'] = False

# --- AUTH LOGIC ---
def login():
    code = st.query_params.get("code")
    if code:
        try:
            flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0])
            flow.fetch_token(code=code)
            u = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', params={'access_token': flow.credentials.token}, headers={'Authorization': f'Bearer {flow.credentials.token}'}).json()
            st.session_state['user'] = {"email": u.get('email'), "name": u.get('name'), "photo": u.get('picture')}
            add_user(u.get('email'), u.get('name'), u.get('picture'))
            st.query_params.clear()
            st.rerun()
        except: st.error("Login Error")

def logout(): st.session_state['user'] = None; st.rerun()
login()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2965/2965363.png", width=60)
    st.title("UniSaver")
    
    msg, maintenance = get_config()
    if msg: st.info(f"📢 {msg}")
    
    if st.session_state['user']:
        u = st.session_state['user']
        c1, c2 = st.columns([1, 3])
        with c1: st.image(u['photo'], width=50)
        with c2: st.write(f"**{u['name']}**")
        
        if st.button("Logout"): logout()
        st.divider()
        st.write(f"Downloads: **{get_user_stats(u['email'])}**")
        if st.button("🗑️ Clear History"): 
            clear_user_history(u['email'])
            st.toast("History Cleared!")
    else:
        st.warning("Guest Mode")
        st.session_state['remember_me'] = st.toggle("Remember Me (30 Days)")
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0])
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.link_button("🔵 Google Login", auth_url, use_container_width=True)

# --- MAINTENANCE & BAN CHECK ---
if maintenance == 1 and (not st.session_state['user'] or st.session_state['user']['email'] != ADMIN_EMAIL):
    st.markdown("<div class='glass-card' style='text-align:center;'><h2>🚧 Maintenance Mode</h2><p>Server upgrade in progress.</p></div>", unsafe_allow_html=True)
    st.stop()

if st.session_state['user'] and check_ban(st.session_state['user']['email']):
    st.error("🚫 Your account is suspended.")
    st.stop()

# --- COOKIE POPUP ---
if not st.session_state['cookies_accepted']:
    st.markdown("""
    <div class="cookie-box">
        <strong style="color:white;">🍪 We use cookies</strong><br>
        <span style="color:#94a3b8; font-size:0.9em;">To ensure you get the best experience.</span><br><br>
        <button onclick="document.querySelector('.cookie-box').style.display='none'" style="background:#3b82f6; color:white; border:none; padding:5px 15px; border-radius:5px; width:100%;">Accept</button>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN UI ---
tabs = ["⬇️ Download", "📦 Batch"]
if st.session_state['user'] and st.session_state['user']['email'] == ADMIN_EMAIL:
    tabs.append("🛡️ Admin Console")

active = st.tabs(tabs)

# --- TAB 1: SINGLE DOWNLOAD ---
with active[0]:
    st.markdown("<div class='animate'>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'><h3>🚀 Universal Downloader</h3></div>", unsafe_allow_html=True)
    
    url = st.text_input("Paste Video Link", placeholder="YouTube, TikTok, Instagram...")
    
    if url:
        if not st.session_state['user']: st.info("🔒 Login required for high-speed downloads.")
        else:
            with st.spinner("Processing..."):
                info = get_video_info(url)
            
            if info:
                c1, c2 = st.columns([1, 2])
                with c1: 
                    if info.get('thumbnail'): st.image(info.get('thumbnail'), use_container_width=True)
                with c2:
                    st.write(f"**{info.get('title')}**")
                    st.caption(f"Source: {info.get('extractor_key')}")
                    
                    opts = {}
                    for f in info.get('formats', []):
                        if f.get('height'): opts[f"{f['height']}p ({f['ext']})"] = f['format_id']
                    
                    sorted_opts = sorted(opts.keys(), key=lambda x: int(x.split('p')[0]) if x[0].isdigit() else 0, reverse=True)
                    opts["🎵 Audio Only (MP3)"] = "bestaudio/best"
                    choice = st.selectbox("Select Quality", ["🎵 Audio Only (MP3)"] + sorted_opts)
                    
                    if st.button("🔥 Download Now"):
                        with st.status("🚀 Initializing Download...", expanded=True) as status:
                            path, title, err = download_video(url, opts.get(choice))
                            if path and os.path.exists(path):
                                status.update(label="✅ Success!", state="complete")
                                log_download(st.session_state['user']['email'], title, url, choice)
                                st.balloons()
                                mime = "audio/mpeg" if "Audio" in choice else "video/mp4"
                                with open(path, "rb") as f:
                                    st.download_button("💾 Save File", f, file_name=os.path.basename(path), mime=mime, use_container_width=True)
                            else:
                                status.update(label="❌ Failed", state="error")
                                st.error(err)
            else: st.error("Invalid Link")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 2: BATCH DOWNLOAD ---
with active[1]:
    st.markdown("<div class='glass-card'><h3>📦 Batch Mode</h3><p>Download multiple videos at once.</p></div>", unsafe_allow_html=True)
    batch = st.text_area("Paste links (one per line)", height=150)
    if st.button("Start Batch"):
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
                                st.download_button(f"💾 {t[:15]}...", f, file_name=os.path.basename(p), key=l)

# --- TAB 3: ADMIN (HIDDEN) ---
if len(tabs) > 2:
    with active[2]:
        st.markdown("## 🛡️ Admin Dashboard")
        
        # Diagnostics
        st.markdown("### 🖥️ System Health")
        c1, c2, c3 = st.columns(3)
        c1.metric("CPU", f"{psutil.cpu_percent()}%")
        c2.metric("RAM", f"{psutil.virtual_memory().percent}%")
        c3.metric("Disk", f"{psutil.disk_usage('/').percent}%")
        
        # Analytics Chart
        st.divider()
        st.markdown("### 📈 Download Trends (7 Days)")
        daily = get_daily_downloads()
        if not daily.empty:
            fig = px.bar(daily, x='timestamp', y='count', color_discrete_sequence=['#8b5cf6'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data yet.")

        # Tools
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🍪 Fix 403 Errors")
            up = st.file_uploader("Upload cookies.txt", type=['txt'])
            if up:
                with open("cookies.txt", "wb") as f: f.write(up.getbuffer())
                st.success("Global Cookies Updated!")
        with c2:
            st.markdown("### 📢 Server Config")
            new_msg = st.text_input("Broadcast Message", value=msg)
            m_mode = st.toggle("Maintenance Mode", value=(maintenance==1))
            if st.button("Save Config"):
                set_config(new_msg, 1 if m_mode else 0)
                st.success("Saved!")

        # File Manager
        st.divider()
        st.markdown("### 📂 File Manager")
        if os.path.exists("downloads"):
            for f in os.listdir("downloads"):
                c1, c2 = st.columns([3, 1])
                c1.write(f"📄 {f}")
                if c2.button("Delete", key=f):
                    os.remove(f"downloads/{f}")
                    st.rerun()

# --- FOOTER ---
st.markdown("""
<br><hr style="border-color:rgba(255,255,255,0.1);">
<div style="text-align:center; color:#94a3b8; font-size:0.8em;">
    © 2024 UniSaver Ultimate. All rights reserved.<br>
    <a href="#" style="color:#64748b;">Terms</a> | <a href="#" style="color:#64748b;">Privacy</a> | <a href="#" style="color:#64748b;">DMCA</a>
</div>
""", unsafe_allow_html=True)
