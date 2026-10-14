import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import io
import re
import random
import hashlib
import smtplib
from email.mime.text import MIMEText

# --- 0. 設定頁面配置與極簡大格子 CSS ---
st.set_page_config(page_title="有其田 客服 CRM 系統", layout="wide", page_icon="🌾")

# 🔥 訂單來源選項 (已更新最新 14 項管道)
ORDER_SOURCES = [
    "未指定 / 自然流量", 
    "FB 再行銷", 
    "FB 新客", 
    "FB 自然貼文", 
    "Google 自然搜尋", 
    "Google 關鍵字搜尋", 
    "Google PMAX 廣告", 
    "Google Demand Gen", 
    "LINE 私訊訂", 
    "LINE 官網訂", 
    "廣播", 
    "簡訊", 
    "官網edm",
    "其他"
]

# 🚨 採用真空壓縮 CSS，字體全面加粗 (Bold) 且修正下拉選單亂碼問題
st.markdown("""
<style>
/* 🌟 字體全面加粗，高度放大 (精準避開系統隱藏圖示，防止亂碼) */
html, body, p, label, th, td, [class*="css"] { font-size: 20px !important; font-weight: 700 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", sans-serif !important; color: #2d3748 !important; }

/* 隱藏用來寫入 Cookie 的 0 高度 iframe */
iframe[height="0"] { display: none !important; }

/* 頂部分頁導覽列 (Tabs) */
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] { gap: 4px !important; padding-top: 10px !important; padding-bottom: 5px !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] { font-size: 20px !important; font-weight: 800 !important; background-color: #f8fafc !important; border-radius: 4px 4px 0 0 !important; border: 1px solid #cbd5e0 !important; border-bottom: none !important; padding: 10px 20px !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] { border-top: 5px solid #e53e3e !important; background-color: #ffffff !important; }

/* 標題與文字 (特粗體) */
h1 { font-size: 32px !important; font-weight: 900 !important; margin-bottom: 10px !important; }
h3 { font-size: 24px !important; font-weight: 900 !important; margin-top: 5px !important; margin-bottom: 10px !important; color: #2b6cb0 !important; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; }

/* 輸入框放大緊湊化 (高度 50px) */
input[type="text"], input[type="password"], input[type="number"], select, div[data-baseweb="select"] > div { font-size: 20px !important; font-weight: 700 !important; min-height: 50px !important; border-radius: 4px !important; border: 1px solid #a0aec0 !important; padding: 6px 12px !important; background-color: #ffffff !important; color: #1a202c !important; }
div[data-testid="stInputValue"] { min-height: 50px !important; }
textarea { font-size: 20px !important; font-weight: 700 !important; min-height: 140px !important; line-height: 1.5 !important; border: 1px solid #a0aec0 !important; border-radius: 4px !important; }

/* 一般按鈕 */
.stButton > button { min-height: 50px !important; font-size: 20px !important; font-weight: 900 !important; border-radius: 6px !important; border: 1px solid #cbd5e0 !important; }

/* 儲存按鈕專屬跳色設計 (淺藍半透明背景 + 藍色文字) */
button[kind="primary"] {
    background-color: rgba(190, 227, 248, 0.5) !important; 
    color: #2b6cb0 !important; 
    border: 2px solid #90cdf4 !important;
    font-size: 20px !important;
    font-weight: 900 !important;
    border-radius: 6px !important;
}
button[kind="primary"]:hover {
    background-color: rgba(190, 227, 248, 0.8) !important;
    border: 2px solid #63b3ed !important;
    color: #1e3a8a !important;
}

/* 水平排版的 Label 樣式 (淺藍色半透明背景塊) */
.lbl { 
    background-color: rgba(190, 227, 248, 0.5); 
    color: #2a4365; 
    font-weight: 900 !important; 
    font-size: 18px; 
    text-align: center; 
    border: 1px solid #90cdf4;
    border-radius: 4px;
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 1px;
}

hr { margin: 20px 0 !important; border: 0 !important; border-top: 1px solid #e2e8f0 !important; }
div.streamlit-expanderHeader { background-color: #f7fafc !important; border: 1px solid #cbd5e0 !important; border-radius: 4px !important; font-size: 18px !important; font-weight: 800 !important; }
div.streamlit-expanderHeader p { font-size: 18px !important; font-weight: 800 !important; color: #2d3748 !important; margin-bottom: 0px !important; }
</style>
""", unsafe_allow_html=True)

# --- 1. 自動發送驗證信與 5 天通行證加密模組 ---
def send_auth_code(to_email, code):
    sender = st.secrets["EMAIL_SENDER"]
    pwd = st.secrets["EMAIL_PASSWORD"].replace(" ", "")
    msg = MIMEText(f"您好，\n\n您的有其田 CRM 系統登入驗證碼為：【 {code} 】\n\n請在系統畫面輸入此驗證碼以完成登入。\n若非本人操作，請立刻回報管理員。", 'plain', 'utf-8')
    msg['Subject'] = "【有其田 CRM】系統安全登入驗證碼"
    msg['From'] = sender
    msg['To'] = to_email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, pwd)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"發送驗證碼信件失敗，請聯絡系統管理員。錯誤細節：{e}")
        return False

def make_auth_token(user, login_date_str=None):
    if not login_date_str: login_date_str = date.today().strftime("%Y%m%d")
    secret_salt = st.secrets.get("EMAIL_PASSWORD", "havefarm_crm_key")
    raw = f"{user}::{login_date_str}::{secret_salt}::havefarm_5days_v1"
    sig = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return f"{login_date_str}:{sig}"

def verify_auth_token(auth_str):
    if not auth_str or ":" not in str(auth_str): return None, None
    parts = str(auth_str).split(":")
    if len(parts) != 3: return None, None
    user, login_date_str, sig = parts[0].strip(), parts[1].strip(), parts[2].strip()
    AUTH_USERS = st.secrets["crm_users"]
    if user not in AUTH_USERS: return None, None
    try:
        login_dt = datetime.strptime(login_date_str, "%Y%m%d").date()
        if (date.today() - login_dt).days >= 5 or (date.today() - login_dt).days < 0: return None, None
    except: return None, None

    expected_token = make_auth_token(user, login_date_str)
    if f"{login_date_str}:{
