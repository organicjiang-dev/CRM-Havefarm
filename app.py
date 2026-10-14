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
    if f"{login_date_str}:{sig}" == expected_token: return user, expected_token
    return None, None

def set_browser_auth_cookie(user, token):
    val = f"{user}:{token}"
    components.html(f"""<script>try {{ window.parent.document.cookie = "crm_auth={val}; path=/; max-age=432000; SameSite=Lax"; }} catch(e) {{}}</script>""", height=0)

def clear_browser_auth_cookie():
    components.html("""<script>try { window.parent.document.cookie = "crm_auth=; path=/; max-age=0; SameSite=Lax"; } catch(e) {}</script>""", height=0)

# --- 2. 雙重認證登入系統 ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.auth_token = ""
        st.session_state.pwd_verified = False
        st.session_state.auth_code = ""
        st.session_state.manual_logout = False

    if not st.session_state.logged_in and not st.session_state.manual_logout:
        auth_token_str = st.query_params.get("auth", "")
        if not auth_token_str:
            try: auth_token_str = st.context.cookies.get("crm_auth", "")
            except: auth_token_str = ""
        
        valid_user, valid_token = verify_auth_token(auth_token_str)
        if valid_user and valid_token:
            st.session_state.logged_in = True
            st.session_state.username = valid_user
            st.session_state.auth_token = valid_token
            st.query_params["auth"] = f"{valid_user}:{valid_token}"

    if st.session_state.logged_in: return True

    col_space1, col_login, col_space2 = st.columns([1, 2, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🌾 有其田 客服系統 - 登入驗證")
        if not st.session_state.pwd_verified:
            with st.form("login_form"):
                user_input = st.text_input("客服人員帳號", placeholder="請輸入帳號").strip()
                pass_input = st.text_input("登入密碼", type="password", placeholder="請輸入密碼").strip()
                login_btn = st.form_submit_button("🔐 進行身分驗證", type="primary")
                if login_btn:
                    AUTH_USERS = st.secrets["crm_users"]
                    if user_input in AUTH_USERS and AUTH_USERS[user_input] == pass_input:
                        st.session_state.username = user_input
                        st.session_state.pwd_verified = True
                        st.session_state.manual_logout = False
                        code = str(random.randint(100000, 999999))
                        st.session_state.auth_code = code
                        RECEIVER_EMAILS = st.secrets["crm_emails"]
                        to_email = RECEIVER_EMAILS.get(user_input, st.secrets["EMAIL_SENDER"])
                        with st.spinner("系統正在發送驗證碼至您的信箱，請稍候..."):
                            if send_auth_code(to_email, code):
                                st.success(f"✅ 帳密正確！驗證碼已發送至信箱。")
                                st.rerun()
                            else: st.session_state.pwd_verified = False
                    else: st.error("❌ 帳號或密碼錯誤，請重新輸入！")
            return False
        else:
            with st.form("2fa_form"):
                code_input = st.text_input("請輸入 6 位數驗證碼", placeholder="例如：123456").strip()
                verify_btn = st.form_submit_button("🚀 確認並登入系統", type="primary")
                cancel_btn = st.form_submit_button("返回重新登入")
                if verify_btn:
                    if code_input == st.session_state.auth_code:
                        st.session_state.logged_in = True
                        st.session_state.manual_logout = False
                        user = st.session_state.username
                        token = make_auth_token(user)
                        st.session_state.auth_token = token
                        st.query_params["auth"] = f"{user}:{token}"
                        st.success("✅ 雙重驗證成功，正在進入系統...")
                        st.rerun()
                    else: st.error("❌ 驗證碼錯誤，請重新輸入！")
                if cancel_btn:
                    st.session_state.pwd_verified = False
                    st.session_state.auth_code = ""
                    st.rerun()
            return False

if not check_login(): st.stop()

if st.session_state.get("auth_token"):
    set_browser_auth_cookie(st.session_state.username, st.session_state.auth_token)

# ==================== 以下為系統主要功能 ====================

@st.cache_resource
def get_db_engine():
    db_url = st.secrets["SUPABASE_DB_URL"]
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
    connect_args = {"sslmode": "require"} if "sslmode" not in db_url else {}
    return create_engine(db_url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)

def execute_query(query, params=None):
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        return result

def read_query(query, params=None):
    engine = get_db_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})

# 🚀 全域共用快取工具區
@st.cache_data(ttl=600, show_spinner=False)
def df_to_excel_cached(df, sheet_name="Sheet1"):
    """通用的超高速 Excel 轉換快取函數"""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w: 
        df.to_excel(w, index=False, sheet_name=sheet_name)
    return out.getvalue()

def format_export_order(dstr, channel_prefix):
    if pd.isna(dstr) or not str(dstr).strip(): return ""
    try:
        d = pd.to_datetime(dstr)
        return f"{channel_prefix}{d.year - 1911}-{d.strftime('%m%d')}"
    except: return ""

@st.cache_data(ttl=600, show_spinner=False)
def generate_tab4_excel_cached(df_filtered):
    """將 Tab 4 複雜的 Excel 轉換邏輯封裝並加入快取"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        base_cols = ["客戶代號", "姓名", "收件人2姓名", "顧客來源", "性別", "主要手機", "備用手機", "收件人2手機", "市話", "常用地址", "最後購買管道", "總購買次數", "歷史消費金額", "最後購買日"]
        
        export_all = df_filtered[base_cols + ["所有訂購明細"]].copy()
        export_all["所有訂購明細"] = export_all["所有訂購明細"].fillna("")
        split_all = export_all["所有訂購明細"].str.split(r"\|\|\|", regex=True, expand=True)
        if not split_all.empty and split_all.shape[1] > 0:
            for col in split_all.columns: split_all[col] = split_all[col].apply(lambda x: format_export_order(x, "A") if isinstance(x, str) else "")
            split_all.columns = [f"購{i+1}" for i in range(split_all.shape[1])]
            export_all = export_all.drop(columns=["所有訂購明細"]).join(split_all)
        else: export_all = export_all.drop(columns=["所有訂購明細"])
        export_all.to_excel(writer, index=False, sheet_name='綜合名單總表')

        export_web = df_filtered[df_filtered["官網訂單"].notna()][base_cols + ["官網訂單"]].copy()
        split_web = export_web["官網訂單"].str.split(r"\|\|\|", regex=True, expand=True)
        if not split_web.empty and split_web.shape[1] > 0:
            for col in split_web.columns: split_web[col] = split_web[col].apply(lambda x: format_export_order(x, "A") if isinstance(x, str) else "")
            split_web.columns = [f"購{i+1}" for i in range(split_web.shape[1])]
            export_web = export_web.drop(columns=["官網訂單"]).join(split_web)
        else: export_web = export_web.drop(columns=["官網訂單"])
        export_web.to_excel(writer, index=False, sheet_name='官網客戶名單')

        export_phone = df_filtered[df_filtered["電話訂單"].notna()][base_cols + ["電話訂單"]].copy()
        split_phone = export_phone["電話訂單"].str.split(r"\|\|\|", regex=True, expand=True)
        if not split_phone.empty and split_phone.shape[1] > 0:
            for col in split_phone.columns: split_phone[col] = split_phone[col].apply(lambda x: format_export_order(x, "B") if isinstance(x, str) else "")
            split_phone.columns = [f"購{i+1}" for i in range(split_phone.shape[1])]
            export_phone = export_phone.drop(columns=["電話訂單"]).join(split_phone)
        else: export_phone = export_phone.drop(columns=["電話訂單"])
        export_phone.to_excel(writer, index=False, sheet_name='電話客戶名單')
    return output.getvalue()

@st.cache_data(ttl=600)
def get_cached_period_orders(s_date, e_date):
    return read_query("SELECT o.order_date AS \"訂購日期\", c.customer_code AS \"客戶代號\", c.name AS \"客戶姓名\", c.phone AS \"手機號碼\", c.customer_source AS \"顧客來源\", o.product AS \"商品名稱\", o.amount AS \"訂單金額\", o.channel AS \"購買管道\", o.status AS \"訂單來源\", o.order_notes AS \"訂單備註\" FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_date >= :s AND o.order_date <= :e ORDER BY o.order_date DESC, o.order_id DESC", {"s": s_date, "e": e_date})

@st.cache_data(ttl=600)
def get_cached_period_tele(s_date, e_date):
    return read_query("SELECT agent_name AS \"客服專員\", call_status AS \"撥打狀態\", COUNT(*) AS \"通話次數\" FROM telemarketing_logs WHERE created_at::date >= :s AND created_at::date <= :e GROUP BY agent_name, call_status ORDER BY agent_name, \"通話次數\" DESC", {"s": s_date, "e": e_date})

# --- 基本快取架構 ---
@st.cache_data(ttl=600)
def get_cached_customers_df():
    return read_query("""
        SELECT customer_id, customer_code, name, gender, id_card, phone, phone_backup, tel, email, 
               address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at, customer_source
        FROM customers
        ORDER BY customer_code DESC, customer_id DESC
    """)

@st.cache_data(ttl=600)
def get_cached_orders_df():
    return read_query("SELECT order_id, customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes FROM orders ORDER BY order_date DESC, order_id DESC")

@st.cache_data(ttl=600)
def get_cached_tab4_report():
    return read_query("""
        WITH OrderAgg AS (
            SELECT customer_id, COUNT(order_id) AS total_orders, COALESCE(SUM(amount), 0) AS total_spent, MAX(order_date) AS last_order_date,
                   STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) AS all_dates,
                   STRING_AGG(CASE WHEN channel LIKE '%官網%' THEN order_date::text END, '|||' ORDER BY order_date ASC) AS web_dates,
                   STRING_AGG(CASE WHEN channel LIKE '%電話%' OR channel LIKE '%廣播%' THEN order_date::text END, '|||' ORDER BY order_date ASC) AS phone_dates
            FROM orders GROUP BY customer_id
        ), LastChannel AS (
            SELECT DISTINCT ON (customer_id) customer_id, channel FROM orders ORDER BY customer_id, order_date DESC, order_id DESC
        )
        SELECT c.customer_id, c.customer_code AS "客戶代號", c.name AS "姓名", c.recipient2_name AS "收件人2姓名", c.recipient2_phone AS "收件人2手機", c.customer_source AS "顧客來源", c.gender AS "性別", c.phone AS "主要手機", c.phone_backup AS "備用手機", c.tel AS "市話", c.address AS "常用地址", COALESCE(lc.channel, '') AS "最後購買管道", COALESCE(oa.total_orders, 0) AS "總購買次數", COALESCE(oa.total_spent, 0) AS "歷史消費金額", oa.last_order_date AS "最後購買日", oa.all_dates AS "所有訂購明細", oa.web_dates AS "官網訂單", oa.phone_dates AS "電話訂單"
        FROM customers c LEFT JOIN OrderAgg oa ON c.customer_id = oa.customer_id LEFT JOIN LastChannel lc ON c.customer_id = lc.customer_id
        ORDER BY c.customer_code DESC, c.customer_id DESC
    """)

@st.cache_data(ttl=600)
def get_cached_rfm_report():
    return read_query("SELECT c.customer_id, c.customer_code AS \"客戶代號\", c.name AS \"姓名\", c.phone AS \"主要手機\", MAX(o.order_date) AS last_purchase_date, SUM(o.amount) AS total_spent, COUNT(o.order_id) AS total_orders FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_code, c.name, c.phone")

@st.cache_data(ttl=600)
def get_cached_followup(today_str):
    return read_query("SELECT DISTINCT c.customer_id, c.customer_code, c.name, c.phone, t.next_followup_date, t.call_status, t.call_notes FROM telemarketing_logs t JOIN customers c ON t.customer_id = c.customer_id WHERE t.next_followup_date <= :today ORDER BY t.next_followup_date ASC", {"today": today_str})

def get_next_crm_code():
    df = get_cached_customers_df()
    codes = df['customer_code'].dropna().astype(str)
    nums = codes.str.extract(r'CRM(\d+)')[0].dropna().astype(int)
    if not nums.empty: return f"CRM{nums.max() + 1:06d}"
    return "CRM008760"

def clean_phone(p):
    if pd.isna(p) or not p: return ""
    s = str(p).strip().replace(".0", "")
    s = re.sub(r"[^\d+]", "", s)
    if s.startswith("+886"): s = "0" + s[4:]
    elif s.startswith("886"): s = "0" + s[3:]
    elif len(s) == 9 and s.startswith("9"): s = "0" + s
    return s

def parse_date_code(val_str, default_channel="官網"):
    raw = str(val_str).strip()
    channel = default_channel
    code_body = raw
    if raw.startswith("A") or raw.startswith("a"): channel, code_body = "官網", raw[1:].strip()
    elif raw.startswith("B") or raw.startswith("b"): channel, code_body = "電話訂購", raw[1:].strip()
    elif raw.startswith("L") or raw.startswith("l"): channel, code_body = "LINE訂購", raw[1:].strip()
    match = re.search(r"(\d{2,3})[-/.]?(\d{2})[-/.]?(\d{2})", code_body)
    if match: return channel, f"{int(match.group(1)) + 1911:04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}", raw
    return channel, raw, raw

# 🌟 全域無敵搜尋：包含「收件人2」姓名與手機
def search_customers_fast(query_str):
    q = str(query_str).strip()
    if not q: return []
    df = get_cached_customers_df()
    if df.empty: return []
    q_lower = q.lower()
    
    mask = (df['name'].str.lower().str.contains(q_lower, na=False) | 
            df['customer_code'].str.lower().str.contains(q_lower, na=False) | 
            df['recipient2_name'].str.lower().str.contains(q_lower, na=False) | 
            df['phone'].astype(str).str.contains(q_lower, na=False) | 
            df['phone_backup'].astype(str).str.contains(q_lower, na=False) | 
            df['tel'].astype(str).str.contains(q_lower, na=False) | 
            df['recipient2_phone'].astype(str).str.contains(q_lower, na=False))
    
    q_digits = re.sub(r"[^\d]", "", q_lower)
    if q_digits and len(q_digits) >= 3:
        if q_digits.startswith("886"): q_digits = "0" + q_digits[3:]
        elif len(q_digits) == 9 and q_digits.startswith("9"): q_digits = "0" + q_digits
        for col in ['phone', 'phone_backup', 'tel', 'recipient2_phone']:
            col_digits = df[col].astype(str).str.replace(r"[^\d]", "", regex=True)
            mask = mask | col_digits.str.contains(q_digits, na=False)
    return df[mask].to_records(index=False).tolist()

def get_customer_by_id(cid):
    df = get_cached_customers_df()
    target = df[df['customer_id'] == cid]
    return target.iloc[0].to_dict() if not target.empty else None

def get_customer_history(customer_id):
    df = get_cached_orders_df()
    return df[df['customer_id'] == customer_id]

def update_customer_db(cid, code, name, gender, id_card, phone, phone_bak, tel, email, addr, r2_name, r2_phone, r2_addr, pref, source):
    execute_query("UPDATE customers SET customer_code = :code, name = :name, gender = :gender, id_card = :id_card, phone = :phone, phone_backup = :phone_bak, tel = :tel, email = :email, address = :addr, recipient2_name = :r2_name, recipient2_phone = :r2_phone, recipient2_address = :r2_addr, dietary_preference = :pref, customer_source = :source WHERE customer_id = :cid", {"code": code, "name": name, "gender": gender, "id_card": id_card, "phone": clean_phone(phone), "phone_bak": phone_bak, "tel": tel, "email": email, "addr": addr, "r2_name": r2_name, "r2_phone": clean_phone(r2_phone), "r2_addr": r2_addr, "pref": pref, "source": source, "cid": cid})
    st.cache_data.clear()

def delete_customer(cid):
    execute_query("DELETE FROM orders WHERE customer_id = :cid", {"cid": cid})
    execute_query("DELETE FROM telemarketing_logs WHERE customer_id = :cid", {"cid": cid})
    execute_query("DELETE FROM customers WHERE customer_id = :cid", {"cid": cid})
    st.cache_data.clear()

def delete_order(order_id):
    execute_query("DELETE FROM orders WHERE order_id = :oid", {"oid": order_id})
    st.cache_data.clear()

def render_editable_orders(history_df, prefix_key):
    if history_df.empty: st.write("目前尚無訂單紀錄。")
    else:
        for _, r in history_df.iterrows():
            oid = r['order_id']
            code_tag = f" `單號:{r['raw_date_code']}`" if r['raw_date_code'] else ""
            with st.expander(f"🗓️ {r['order_date']}{code_tag} | {r['channel']} | 金額：NT$ {r['amount']:,} | 來源：{r['status']}", expanded=False):
                with st.form(key=f"edit_order_form_{prefix_key}_{oid}"):
                    ec_o1, ec_o2, ec_o3 = st.columns(3)
                    with ec_o1:
                        o_chan = st.selectbox("購買管道", ["電話訂購", "官網", "LINE訂購", "其他"], index=0 if "電話" in r['channel'] else (1 if "官網" in r['channel'] else 2))
                        o_date = st.text_input("訂購日期", value=str(r['order_date']))
                    with ec_o2:
                        o_prod = st.text_input("訂購商品", value=str(r['product']))
                        o_amt = st.number_input("訂單金額", min_value=0, step=50, value=int(r['amount']))
                    with ec_o3:
                        source_idx = ORDER_SOURCES.index(r['status']) if r['status'] in ORDER_SOURCES else 0
                        o_source = st.selectbox("訂單來源", ORDER_SOURCES, index=source_idx)
                        o_notes = st.text_input("訂單備註", value=str(r['order_notes']) if pd.notna(r['order_notes']) else "")
                    st.markdown("<br>", unsafe_allow_html=True)
                    btn_c1, btn_c2, btn_c3 = st.columns([3, 4, 3])
                    with btn_c2:
                        save_order_btn = st.form_submit_button("💾 儲存資料", type="primary", use_container_width=True)
                    if save_order_btn:
                        execute_query("UPDATE orders SET channel = :chan, product = :prod, amount = :amt, order_date = :odate, status = :source, order_notes = :notes WHERE order_id = :oid", {"chan": o_chan, "prod": o_prod, "amt": o_amt, "odate": o_date, "source": o_source, "notes": o_notes, "oid": oid})
                        st.cache_data.clear()
                        st.success(f"✅ 訂單修改成功！")
                        st.rerun()
                del_confirm = st.checkbox(f"⚠️ 確認要刪除此筆訂單 (#{oid})？", key=f"chk_del_{prefix_key}_{oid}")
                if del_confirm:
                    if st.button("🚨 確認刪除", key=f"btn_del_{prefix_key}_{oid}"):
                        delete_order(oid)
                        st.success(f"✅ 已刪除！")
                        st.rerun()

# --- 🌟 主介面頂部設計 (無側邊欄) ---
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title("🌾 有其田 客服管理系統")
with col_user:
    st.markdown(f"<div style='text-align: right; padding-top: 15px; font-weight: bold; color: #2b6cb0;'>👤 使用者：{st.session_state.username}</div>", unsafe_allow_html=True)
    if st.button("🚪 登出系統", use_container_width=True):
        st.
