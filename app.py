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

# --- CONFIG ---
ADMIN_EMAIL = "nazmusshakibshihan01@gmail.com" # <--- REPLACE THIS

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

# --- CSS (RESPONSIVE) ---
st.markdown("""
<style>
    .stApp { background: #0f172a; color: white; }
    
    /* Mobile-First Card */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Buttons */
    div.stButton > button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white; border: none; border-radius: 12px;
        height: 50px; font-weight: 600; width: 100%;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        transition: transform 0.2s;
    }
    div.stButton > button:active { transform: scale(0.96); }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        background: #1e293b !important;
        border: 1px solid #475569 !important;
        color: white !important;
        border-radius: 12px;
    }
    
    /* Navbar Hide on Mobile */
    [data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }
    
    /* Animations */
    @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    .animate { animation: slideUp 0.5s ease-out; }
</style>
""", unsafe_allow_html=True)

# --- AUTH LOGIC ---
if 'user' not in st.session_state: st.session_state['user'] = None

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
        except: st.error("Login Failed")

def logout(): st.session_state['user'] = None; st.rerun()
login()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3075/3075977.png", width=50)
    st.title("UniSaver")
    
    msg, maintenance = get_config()
    if msg: st.info(msg)
    
    if st.session_state['user']:
        u = st.session_state['user']
        c1, c2 = st.columns([1, 3])
        with c1: st.image(u['photo'], width=50)
        with c2: st.write(f"**{u['name']}**")
        if st.button("Logout"): logout()
    else:
        st.write("Guest Mode")
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0])
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.link_button("🔵 Google Login", auth_url, use_container_width=True)

# --- MAINTENANCE GUARD ---
if maintenance == 1 and (not st.session_state['user'] or st.session_state['user']['email'] != ADMIN_EMAIL):
    st.markdown("<div class='glass-card' style='text-align:center;'><h2>🚧 Maintenance</h2><p>We'll be back shortly.</p></div>", unsafe_allow_html=True)
    st.stop()

if st.session_state['user'] and check_ban(st.session_state['user']['email']):
    st.error("🚫 Account Suspended")
    st.stop()

# --- MAIN UI ---
tabs = ["⬇️ Single", "📦 Batch"]
if st.session_state['user'] and st.session_state['user']['email'] == ADMIN_EMAIL:
    tabs.append("🛡️ Admin")

active = st.tabs(tabs)

# --- TAB 1: SINGLE DOWNLOAD ---
with active[0]:
    st.markdown("<div class='animate'>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'><h3>🚀 Quick Download</h3></div>", unsafe_allow_html=True)
    
    url = st.text_input("Paste Link", placeholder="https://...")
    
    if url:
        if not st.session_state['user']: st.info("🔒 Login required.")
        else:
            with st.spinner("Processing..."):
                info = get_video_info(url)
            
            if info:
                st.image(info.get('thumbnail'), use_container_width=True)
                st.write(f"**{info.get('title')}**")
                
                # Quality
                opts = {}
                for f in info.get('formats', []):
                    if f.get('height'): opts[f"{f['height']}p ({f['ext']})"] = f['format_id']
                
                sorted_opts = sorted(opts.keys(), key=lambda x: int(x.split('p')[0]) if x[0].isdigit() else 0, reverse=True)
                opts["🎵 Audio Only (MP3)"] = "bestaudio/best"
                choice = st.selectbox("Format", ["🎵 Audio Only (MP3)"] + sorted_opts)
                
                if st.button("Download"):
                    with st.status("Downloading...", expanded=True) as status:
                        path, title, err = download_video(url, opts.get(choice))
                        if path and os.path.exists(path):
                            status.update(label="✅ Ready!", state="complete")
                            log_download(st.session_state['user']['email'], title, url, choice)
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
    st.markdown("<div class='glass-card'><h3>📦 Batch Downloader</h3><p>Download multiple videos at once (One link per line)</p></div>", unsafe_allow_html=True)
    
    batch_urls = st.text_area("Paste Links Here", height=150)
    
    if st.button("🚀 Process Batch"):
        if not st.session_state['user']: st.error("Login required.")
        else:
            links = batch_urls.split('\n')
            for link in links:
                if link.strip():
                    with st.status(f"Downloading {link}...", expanded=False) as status:
                        info = get_video_info(link)
                        if info:
                            path, title, err = download_video(link, "best")
                            if path:
                                st.write(f"✅ {title}")
                                with open(path, "rb") as f:
                                    st.download_button(f"💾 Save {title[:15]}...", f, file_name=os.path.basename(path), key=link)

# --- TAB 3: ADMIN ---
if len(tabs) > 2:
    with active[2]:
        st.markdown("## 🛡️ Admin Dashboard")
        
        # ANALYTICS
        st.markdown("### 📈 Trends")
        daily_data = get_daily_downloads()
        if not daily_data.empty:
            fig = px.bar(daily_data, x='timestamp', y='count', title="Downloads (Last 7 Days)", color_discrete_sequence=['#8b5cf6'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Not enough data for charts yet.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🍪 Cookies")
            up = st.file_uploader("Upload cookies.txt", type=['txt'])
            if up:
                with open("cookies.txt", "wb") as f: f.write(up.getbuffer())
                st.success("Updated!")
        
        with col2:
            st.markdown("### 📢 Config")
            new_msg = st.text_input("Broadcast", value=msg)
            m_mode = st.toggle("Maintenance Mode", value=(maintenance==1))
            if st.button("Save Config"):
                set_config(new_msg, 1 if m_mode else 0)
                st.success("Saved!")
        
        # FILE EXPLORER
        st.divider()
        st.markdown("### 📂 Server File Manager")
        if os.path.exists("downloads"):
            files = os.listdir("downloads")
            if files:
                for f in files:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    size_mb = os.path.getsize(f"downloads/{f}") / (1024*1024)
                    c1.write(f"📄 {f}")
                    c2.write(f"{size_mb:.2f} MB")
                    if c3.button("🗑️", key=f"del_{f}"):
                        os.remove(f"downloads/{f}")
                        st.toast(f"Deleted {f}")
                        st.rerun()
            else: st.caption("No files on server.")
        
        # USER MANAGEMENT
        st.divider()
        st.markdown("### 👥 Users")
        users = get_all_users()
        if not users.empty:
            for i, row in users.iterrows():
                with st.expander(f"{row['name']} ({row['email']})"):
                    st.write(f"Joined: {row['joined_at']}")
                    if row['email'] != ADMIN_EMAIL:
                        btn = "Unban" if row['is_banned'] else "Ban"
                        if st.button(btn, key=row['email']):
                            toggle_ban(row['email'], row['is_banned'])
                            st.rerun()
