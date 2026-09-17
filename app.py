import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import io
import re
import random
import smtplib
from email.mime.text import MIMEText

# --- 0. 設定頁面配置與極簡大格子 CSS ---
st.set_page_config(page_title="有其田 客服 CRM 系統", layout="wide", page_icon="🌾")

# 🚨 採用無空白行真空壓縮，防止 Streamlit 解析器切斷 CSS
st.markdown("""
<style>
/* 整體極簡字體與色彩設定 (放大至 20px 提升清晰度) */
html, body, [class*="css"] { font-size: 20px !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif !important; color: #2d3748 !important; }

/* 頂部分頁導覽列 (Tabs) */
div[data-testid="stTabs"] { overflow: visible !important; }
div[data-testid="stTabs"] > div { overflow: visible !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] { gap: 10px !important; padding-top: 15px !important; padding-bottom: 10px !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] { font-size: 22px !important; background-color: #f8fafc !important; border-radius: 6px 6px 0 0 !important; border: 1px solid #cbd5e0 !important; border-bottom: none !important; margin-right: 4px !important; padding: 12px 24px !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] * { font-weight: 700 !important; color: #718096 !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] { border-top: 5px solid #e53e3e !important; background-color: #ffffff !important; border-left: 1px solid #cbd5e0 !important; border-right: 1px solid #cbd5e0 !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] * { color: #e53e3e !important; }

/* 標題與文字層級 */
h1 { font-size: 36px !important; font-weight: 900 !important; margin-bottom: 16px !important; color: #1a202c !important; }
h2, h3 { font-size: 28px !important; font-weight: 800 !important; margin-top: 16px !important; margin-bottom: 12px !important; color: #2d3748 !important; }
h4, h5 { font-size: 22px !important; font-weight: 700 !important; margin-top: 12px !important; color: #2b6cb0 !important; }
label, label p, [data-testid="stWidgetLabel"] p { font-size: 18px !important; font-weight: 800 !important; color: #2d3748 !important; margin-bottom: 8px !important; }

/* 輸入框與按鈕精緻大格子化 */
input[type="text"], input[type="password"], input[type="number"], select, div[data-baseweb="select"] > div { font-size: 20px !important; min-height: 56px !important; border-radius: 8px !important; border: 2px solid #a0aec0 !important; padding: 10px 16px !important; background-color: #ffffff !important; color: #1a202c !important; font-weight: 600 !important; }
div[data-testid="stInputValue"] { min-height: 56px !important; }
div[data-baseweb="select"] span { font-size: 20px !important; font-weight: 600 !important; }
textarea { font-size: 20px !important; min-height: 180px !important; line-height: 1.6 !important; border: 2px solid #a0aec0 !important; border-radius: 8px !important; font-weight: 600 !important; }
.stButton > button { min-height: 56px !important; font-size: 20px !important; font-weight: 800 !important; border-radius: 8px !important; padding: 0 30px !important; margin-top: 10px !important; border: 2px solid #cbd5e0 !important; }

/* 統計數字與表格 */
[data-testid="stMetricValue"] { font-size: 36px !important; font-weight: 900 !important; color: #2b6cb0 !important; }
[data-testid="stMetricLabel"] p { font-size: 18px !important; font-weight: 700 !important; color: #4a5568 !important; }
details summary p, details summary span { font-size: 20px !important; font-weight: 800 !important; color: #2c5282 !important; }
div[data-testid="stDataFrame"] { font-size: 18px !important; }
div[data-testid="column"] { padding: 0 16px !important; }
hr { margin: 30px 0 !important; border: 0 !important; border-top: 2px solid #e2e8f0 !important; }

/* 🌟 置中大格子專屬極簡背景色與微陰影 */
.search-header-box { background-color: #e2e8f0; padding: 16px 24px; border-radius: 10px 10px 0 0; border: 2px solid #cbd5e0; border-bottom: none; }
.search-content-box { padding: 30px; border: 2px solid #cbd5e0; border-radius: 0 0 10px 10px; background-color: #ffffff; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.edit-header-box { background-color: #bee3f8; padding: 16px 24px; border-radius: 10px 10px 0 0; border: 2px solid #90cdf4; border-bottom: none; }
.edit-content-box { padding: 30px; border: 2px solid #90cdf4; border-radius: 0 0 10px 10px; background-color: #ffffff; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
div.streamlit-expanderHeader:has(span:contains("電訪追蹤紀錄")) { background-color: #f0fff4 !important; border: 2px solid #9ae6b4 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# --- 1. 自動發送驗證信模組 ---
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

# --- 2. 雙重認證登入系統 ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.pwd_verified = False
        st.session_state.auth_code = ""

    if st.session_state.logged_in:
        return True

    col_space1, col_login, col_space2 = st.columns([1, 2, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🌾 有其田 客服系統 - 登入驗證")

        if not st.session_state.pwd_verified:
            st.info("🔒 為保護客戶個資安全，請輸入內部客服人員帳號與密碼。")
            with st.form("login_form"):
                user_input = st.text_input("客服人員帳號", placeholder="請輸入帳號（例如: admin 或 service）").strip()
                pass_input = st.text_input("登入密碼", type="password", placeholder="請輸入密碼").strip()
                login_btn = st.form_submit_button("🔐 進行身分驗證")

                if login_btn:
                    AUTH_USERS = st.secrets["crm_users"]
                    if user_input in AUTH_USERS and AUTH_USERS[user_input] == pass_input:
                        st.session_state.username = user_input
                        st.session_state.pwd_verified = True
                        code = str(random.randint(100000, 999999))
                        st.session_state.auth_code = code
                        
                        RECEIVER_EMAILS = st.secrets["crm_emails"]
                        to_email = RECEIVER_EMAILS.get(user_input, st.secrets["EMAIL_SENDER"])
                        
                        with st.spinner("系統正在發送驗證碼至您的信箱，請稍候..."):
                            if send_auth_code(to_email, code):
                                masked_email = f"{to_email[:3]}...@{to_email.split('@')[1]}"
                                st.success(f"✅ 帳密正確！驗證碼已發送至信箱：{masked_email}")
                                st.rerun()
                            else:
                                st.session_state.pwd_verified = False
                    else:
                        st.error("❌ 帳號或密碼錯誤，請重新輸入！")
            return False

        else:
            st.warning("📧 系統已發送【6位數驗證碼】至設定的電子信箱，請前往收信並填寫。")
            with st.form("2fa_form"):
                code_input = st.text_input("請輸入 6 位數驗證碼", placeholder="例如：123456").strip()
                verify_btn = st.form_submit_button("🚀 確認並登入系統")
                cancel_btn = st.form_submit_button("返回重新登入")

                if verify_btn:
                    if code_input == st.session_state.auth_code:
                        st.session_state.logged_in = True
                        st.success("✅ 雙重驗證成功，正在進入系統...")
                        st.rerun()
                    else:
                        st.error("❌ 驗證碼錯誤，請重新輸入！")
                
                if cancel_btn:
                    st.session_state.pwd_verified = False
                    st.session_state.auth_code = ""
                    st.rerun()
            return False

if not check_login():
    st.stop()

# ==================== 以下為原本的系統主要功能 ====================

with st.sidebar:
    st.markdown(f"### 👤 目前使用者：**{st.session_state.username}**")
    st.caption("連線狀態：🟢 Supabase 雲端資料庫已加密連線")
    if st.button("🚪 登出系統"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.pwd_verified = False
        st.session_state.auth_code = ""
        st.rerun()

# --- 2. 雲端資料庫連線 (Supabase PostgreSQL) ---
@st.cache_resource
def get_db_engine():
    db_url = st.secrets["SUPABASE_DB_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    connect_args = {}
    if "sslmode" not in db_url:
        connect_args["sslmode"] = "require"

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args
    )

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

# 🚀 【效能加速優化】快取全體客戶基礎名單，實現毫秒級搜尋
@st.cache_data(ttl=600)
def get_cached_customers_df():
    return read_query("""
        SELECT customer_id, customer_code, name, gender, id_card, phone, phone_backup, tel, email, 
               address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at, customer_source
        FROM customers
        ORDER BY customer_code DESC, customer_id DESC
    """)

# --- 3. 輔助轉換與極速記憶體搜尋 ---
def parse_date_code(val_str, default_channel="官網"):
    raw = str(val_str).strip()
    channel = default_channel
    code_body = raw

    if raw.startswith("A") or raw.startswith("a"):
        channel = "官網"
        code_body = raw[1:].strip()
    elif raw.startswith("B") or raw.startswith("b"):
        channel = "電話訂購"
        code_body = raw[1:].strip()
    elif raw.startswith("L") or raw.startswith("l"):
        channel = "LINE訂購"
        code_body = raw[1:].strip()

    match = re.search(r"(\d{2,3})[-/.]?(\d{2})[-/.]?(\d{2})", code_body)
    if match:
        roc_year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        ad_year = roc_year + 1911
        standard_date = f"{ad_year:04d}-{month:02d}-{day:02d}"
        return channel, standard_date, raw

    return channel, raw, raw

def get_next_crm_code():
    df = get_cached_customers_df()
    max_num = 8759
    for _, r in df.iterrows():
        code_str = str(r['customer_code']).strip()
        match = re.search(r"CRM(\d+)", code_str)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    next_num = max_num + 1
    return f"CRM{next_num:06d}"

def clean_phone(p):
    if pd.isna(p) or not p:
        return ""
    s = str(p).strip().replace(".0", "")
    s = re.sub(r"[^\d+]", "", s)
    if s.startswith("+886"):
        s = "0" + s[4:]
    elif s.startswith("886"):
        s = "0" + s[3:]
    elif len(s) == 9 and s.startswith("9"):
        s = "0" + s
    return s

def search_customers_fast(query_str):
    q = str(query_str).strip()
    if not q:
        return []
    
    df = get_cached_customers_df()
    if df.empty:
        return []
    
    q_lower = q.lower()
    q_clean = clean_phone(q)

    mask = (
        df['name'].str.lower().str.contains(q_lower, na=False) |
        df['customer_code'].str.lower().str.contains(q_lower, na=False)
    )

    if q_clean and len(q_clean) >= 3:
        mask = mask | (
            df['phone'].str.contains(q_clean, na=False) |
            df['phone_backup'].str.contains(q_clean, na=False) |
            df['recipient2_phone'].str.contains(q_clean, na=False) |
            df['tel'].str.contains(q_clean, na=False)
        )

    matched_df = df[mask]
    return matched_df.to_records(index=False).tolist()

def get_customer_by_id(cid):
    df = get_cached_customers_df()
    target = df[df['customer_id'] == cid]
    if not target.empty:
        return target.iloc[0].to_dict()
    return None

def get_customer_history(customer_id):
    return read_query("""
        SELECT order_id, channel, product, amount, order_date, raw_date_code, status, order_notes
        FROM orders
        WHERE customer_id = :cid
        ORDER BY order_date DESC, order_id DESC
    """, {"cid": customer_id})

def update_customer_db(cid, code, name, gender, id_card, phone, phone_bak, tel, email, addr, r2_name, r2_phone, r2_addr, pref, source):
    execute_query("""
        UPDATE customers 
        SET customer_code = :code, name = :name, gender = :gender, id_card = :id_card, 
            phone = :phone, phone_backup = :phone_bak, tel = :tel, email = :email, 
            address = :addr, recipient2_name = :r2_name, recipient2_phone = :r2_phone, 
            recipient2_address = :r2_addr, dietary_preference = :pref, customer_source = :source
        WHERE customer_id = :cid
    """, {
        "code": code, "name": name, "gender": gender, "id_card": id_card,
        "phone": clean_phone(phone), "phone_bak": phone_bak, "tel": tel, "email": email,
        "addr": addr, "r2_name": r2_name, "r2_phone": clean_phone(r2_phone), "r2_addr": r2_addr, "pref": pref, "source": source, "cid": cid
    })
    st.cache_data.clear()

def delete_customer(cid):
    execute_query("DELETE FROM orders WHERE customer_id = :cid", {"cid": cid})
    execute_query("DELETE FROM telemarketing_logs WHERE customer_id = :cid", {"cid": cid})
    execute_query("DELETE FROM customers WHERE customer_id = :cid", {"cid": cid})
    st.cache_data.clear()

def delete_order(order_id):
    execute_query("DELETE FROM orders WHERE order_id = :oid", {"oid": order_id})

def render_editable_orders(history_df, prefix_key):
    if history_df.empty:
        st.write("目前尚無訂單紀錄。")
    else:
        for _, r in history_df.iterrows():
            oid = r['order_id']
            code_tag = f" `代碼:{r['raw_date_code']}`" if r['raw_date_code'] else ""
            
            with st.expander(f"🗓️ {r['order_date']}{code_tag} | {r['channel']} | 金額：NT$ {r['amount']:,} | 狀態：{r['status']}", expanded=False):
                with st.form(key=f"edit_order_form_{prefix_key}_{oid}"):
                    ec_o1, ec_o2, ec_o3 = st.columns(3)
                    with ec_o1:
                        o_chan = st.selectbox("購買管道", ["電話訂購", "官網", "LINE訂購", "其他"], index=0 if "電話" in r['channel'] else (1 if "官網" in r['channel'] else 2))
                        o_date = st.text_input("訂購日期", value=str(r['order_date']))
                    with ec_o2:
                        o_prod = st.text_input("訂購商品", value=str(r['product']))
                        o_amt = st.number_input("訂單金額", min_value=0, step=50, value=int(r['amount']))
                    with ec_o3:
                        o_status = st.selectbox("狀態", ["歷史完成", "已完成", "已出貨", "已接單/待出貨", "售後追蹤中", "取消/退貨"], index=0 if r['status']=="歷史完成" else 1)
                        o_notes = st.text_input("訂單備註", value=str(r['order_notes']) if pd.notna(r['order_notes']) else "")

                    save_order_btn = st.form_submit_button("💾 儲存此筆訂單修改")
                    if save_order_btn:
                        execute_query("""
                            UPDATE orders 
                            SET channel = :chan, product = :prod, amount = :amt, order_date = :odate, status = :status, order_notes = :notes
                            WHERE order_id = :oid
                        """, {
                            "chan": o_chan, "prod": o_prod, "amt": o_amt,
                            "odate": o_date, "status": o_status, "notes": o_notes, "oid": oid
                        })
                        st.success(f"✅ 訂單 #{oid} 修改成功！")
                        st.rerun()

                st.markdown("---")
                del_confirm = st.checkbox(f"⚠️ 確認要刪除此筆訂單 (#{oid})？", key=f"chk_del_{prefix_key}_{oid}")
                if del_confirm:
                    if st.button("🚨 確認刪除", key=f"btn_del_{prefix_key}_{oid}"):
                        delete_order(oid)
                        st.success(f"✅ 已刪除訂單 #{oid}！")
                        st.rerun()

# --- 4. 主介面排版 ---
st.title("🌾 有其田 客服管理系統")

if "jump_search_query" not in st.session_state:
    st.session_state.jump_search_query = ""

tab1, tab2, tab3, tab4, tab7, tab6, tab5 = st.tabs([
    "🔍 舊客速查與編輯", 
    "🆕 建立新名單", 
    "👤 歷史訂購紀錄", 
    "📊 客戶名冊總表",
    "🎯 智慧回購清單",
    "📅 報表與匯出",
    "📥 匯入舊名單與官網訂單報表"
])

# ==========================================
# TAB 1: 舊客戶速查與編輯 (🌟 全版展開直覺版)
# ==========================================
with tab1:
    col_left_spacer, col_main_center, col_right_spacer = st.columns([1, 4, 1])
    
    with col_main_center:
        st.markdown('<div class="search-header-box"><h3 style="margin:0; color:#2d3748;">🔍 客戶資料查詢</h3></div>', unsafe_allow_html=True)
        st.markdown('<div class="search-content-box">', unsafe_allow_html=True)
        
        default_search = st.session_state.jump_search_query
        if default_search:
            st.session_state.jump_search_query = ""

        search_query = st.text_input(
            "請輸入 姓名 / 手機 / 代號 / 身分證號 進行速查：", 
            value=default_search,
            placeholder="例：蔡汶容、0912345678、或輸入 8761 查詢 CRM008761",
            key="accurate_cust_search"
        ).strip()
        st.markdown('</div>', unsafe_allow_html=True)

        if search_query:
            matched_custs = search_customers_fast(search_query)
            if not matched_custs:
                st.warning(f"⚠️ 查無包含『{search_query}』的客戶資料！若為新客戶請至上方【🆕 建立全新會員名單】分頁。")
            else:
                if len(matched_custs) > 1:
                    st.info(f"🔎 找到 {len(matched_custs)} 位符合條件的客戶，請選擇：")
                    cust_options = {f"[{c[1] if str(c[1]).strip() else '待查'}] {c[2]} (電話:{c[5]} / 地址:{str(c[9])[:20]}...)": c[0] for c in matched_custs}
                    selected_cid = st.selectbox("請選擇客戶：", list(cust_options.keys()), key="search_multi_select")
                    target_cid = cust_options[selected_cid]
                else:
                    target_cid = matched_custs[0][0]

                cust = get_customer_by_id(target_cid)
                if cust:
                    cid = cust['customer_id']
                    ccode = str(cust['customer_code']).strip() if pd.notna(cust['customer_code']) else ""
                    cname = cust['name']
                    cgender = cust['gender']
                    cid_card = cust['id_card']
                    cphone = cust['phone']
                    cphone_bak = cust['phone_backup']
                    ctel = cust['tel']
                    cemail = cust['email']
                    caddr = cust['address']
                    cr2_name = cust['recipient2_name']
                    cr2_phone = cust['recipient2_phone']
                    cr2_addr = cust['recipient2_address']
                    cpref = cust['dietary_preference']
                    ccreated = cust['created_at']
                    csource = cust.get('customer_source') or "未指定 / 自然流量"

                    history_df = get_customer_history(cid)
                    total_orders = len(history_df)
                    total_spent = history_df['amount'].sum() if total_orders > 0 else 0

                    display_code = ccode if ccode else "⚠️ 待確認 / 無代號"
                    st.success(f"🎯 已調出客戶：【{cname}】（代號：{display_code}）")

                    m1, m2, m3 = st.columns(3)
                    m1.metric("累積購買次數", f"{total_orders} 次")
                    m2.metric("累積消費金額", f"NT$ {total_spent:,}")
                    m3.metric("初次建檔時間", str(ccreated).split()[0] if ccreated else "-")

                    # 🌟 移除 expander，直接展開顯示基本資料 (精簡欄位版)
                    st.markdown('<div class="edit-header-box"><h3 style="margin:0; color:#2c5282;">✏️ 基本資料編輯</h3></div>', unsafe_allow_html=True)
                    st.markdown('<div class="edit-content-box">', unsafe_allow_html=True)
                    
                    with st.form(key=f"edit_cust_form_tab1_{cid}"):
                        ec_left, ec_right = st.columns(2)
                        
                        with ec_left:
                            next_avail = get_next_crm_code()
                            code_label = "客戶代號" if ccode else f"客戶代號 (系統建議新號：{next_avail})"
                            edit_code = st.text_input(code_label, value=ccode)
                            edit_name = st.text_input("姓  名 *", value=cname if cname else "")
                            edit_phone = st.text_input("行 動 (1) *", value=cphone if cphone else "")
                            edit_tel = st.text_input("電 話 (1)", value=ctel if ctel else "")
                            
                        with ec_right:
                            edit_id_card = st.text_input("身分證號 / 統編", value=cid_card if cid_card else "")
                            edit_gender = st.selectbox("性  別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2))
                            edit_phone_bak = st.text_input("行 動 (2)", value=cphone_bak if cphone_bak else "")
                            st.markdown("<br><br>", unsafe_allow_html=True) # 佔位對齊

                        edit_addr = st.text_input("地  址 *", value=caddr if caddr else "")
                        
                        # 🌟 備註改為大區塊 text_area
                        edit_pref = st.text_area("備註 (客戶習慣/特殊需求)", value=cpref if cpref else "", placeholder="例：只吃無糖、全素、需代收")

                        st.markdown("---")
                        st.markdown("##### 🎁 送禮專用 / 第二收件人 (選填)")
                        r2_c1, r2_c2 = st.columns(2)
                        with r2_c1:
                            edit_r2_name = st.text_input("第二收件人姓名", value=cr2_name if cr2_name else "")
                        with r2_c2:
                            edit_r2_phone = st.text_input("第二收件人行動", value=cr2_phone if cr2_phone else "")
                        edit_r2_addr = st.text_input("第二收件地址", value=cr2_addr if cr2_addr else "")

                        st.markdown("<br>", unsafe_allow_html=True)
                        save_cust_btn = st.form_submit_button("💾 儲存並更新客戶資料", use_container_width=True)

                        if save_cust_btn:
                            if not edit_name or not edit_phone or not edit_addr:
                                st.error("姓名、主要手機與地址不可為空！")
                            else:
                                # 保持背景資料庫不變，未顯示的欄位填回原本的值
                                update_customer_db(cid, edit_code, edit_name, edit_gender, edit_id_card, edit_phone, edit_phone_bak, edit_tel, cemail, edit_addr, edit_r2_name, edit_r2_phone, edit_r2_addr, edit_pref, csource)
                                st.success(f"✅ 客戶【{edit_name}】資料已成功更新！")
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                    with st.expander("⚠️ 危險操作區：刪除此會員帳號", expanded=False):
                        st.warning("若此會員為重複建檔的幽靈帳號，確認後可點擊下方按鈕將其永久刪除（包含歷史訂單）。")
                        del_cust_chk = st.checkbox(f"我確定要刪除客戶 【{cname}】", key=f"chk_del_cust_{cid}")
                        if del_cust_chk:
                            if st.button(f"🚨 確認永久刪除此會員", key=f"btn_del_cust_{cid}", type="primary"):
                                delete_customer(cid)
                                st.success(f"✅ 已成功刪除會員 【{cname}】！")
                                st.rerun()

                    with st.expander("📞 電訪追蹤紀錄與下次提醒（點擊展開/收合）", expanded=False):
                        st.markdown("##### ➕ 新增一通電訪紀錄")
                        with st.form(key=f"tele_form_tab1_{cid}", clear_on_submit=True):
                            tc_col1, tc_col2 = st.columns(2)
                            with tc_col1:
                                call_status = st.selectbox("撥打狀態", ["成功下單", "考慮中", "無人接聽", "拒絕/空號"])
                                next_date = st.date_input("下次提醒再訪日 (選填)", value=None)
                            with tc_col2:
                                call_notes = st.text_area("電訪筆記與備註", placeholder="例：詢問燕麥奶庫存狀況，表示下週回電。")

                            save_call_btn = st.form_submit_button("📞 儲存這通電訪紀錄")
                            if save_call_btn:
                                execute_query("""
                                    INSERT INTO telemarketing_logs (customer_id, agent_name, call_status, call_notes, next_followup_date)
                                    VALUES (:cid, :agent, :status, :notes, :ndate)
                                """, {
                                    "cid": cid,
                                    "agent": st.session_state.username,
                                    "status": call_status,
                                    "notes": call_notes,
                                    "ndate": next_date if next_date else None
                                })
                                st.success("✅ 電訪紀錄已成功儲存！")
                                st.rerun()

                        past_logs = read_query("SELECT log_id, agent_name, call_status, call_notes, next_followup_date, created_at FROM telemarketing_logs WHERE customer_id = :cid ORDER BY created_at DESC", {"cid": cid})
                        if not past_logs.empty:
                            st.markdown("---")
                            st.markdown("##### ✏️ 歷史電訪紀錄（展開可直接修改）")
                            for _, plog in past_logs.iterrows():
                                log_id = plog['log_id']
                                nd_display = str(plog['next_followup_date']) if pd.notna(plog['next_followup_date']) else "無"
                                
                                with st.expander(f"🕒 [{str(plog['created_at'])[:16]}] 專員: {plog['agent_name']} | 狀態: {plog['call_status']} | 提醒: {nd_display}", expanded=False):
                                    with st.form(key=f"edit_tele_form_{cid}_{log_id}"):
                                        e_t1, e_t2 = st.columns(2)
                                        with e_t1:
                                            e_status = st.selectbox("撥打狀態", ["成功下單", "考慮中", "無人接聽", "拒絕/空號"], index=["成功下單", "考慮中", "無人接聽", "拒絕/空號"].index(plog['call_status']) if plog['call_status'] in ["成功下單", "考慮中", "無人接聽", "拒絕/空號"] else 0)
                                            try:
                                                default_nd = datetime.strptime(str(plog['next_followup_date']), "%Y-%m-%d").date() if pd.notna(plog['next_followup_date']) else None
                                            except:
                                                default_nd = None
                                            e_ndate = st.date_input("下次提醒再訪日", value=default_nd)
                                        with e_t2:
                                            e_notes = st.text_area("電訪筆記", value=str(plog['call_notes']) if pd.notna(plog['call_notes']) else "")

                                        e_save_btn = st.form_submit_button("💾 儲存此筆電訪修改")
                                        if e_save_btn:
                                            execute_query("""
                                                UPDATE telemarketing_logs 
                                                SET call_status = :status, call_notes = :notes, next_followup_date = :ndate
                                                WHERE log_id = :lid
                                            """, {
                                                "status": e_status,
                                                "notes": e_notes,
                                                "ndate": e_ndate if e_ndate else None,
                                                "lid": log_id
                                            })
                                            st.success("✅ 電訪紀錄修改成功！")
                                            st.rerun()

                                    del_tele_chk = st.checkbox(f"⚠️ 確認刪除此筆電訪紀錄 (#{log_id})？", key=f"del_tele_chk_{log_id}")
                                    if del_tele_chk:
                                        if st.button("🚨 確認刪除電訪", key=f"btn_del_tele_{log_id}"):
                                            execute_query("DELETE FROM telemarketing_logs WHERE log_id = :lid", {"lid": log_id})
                                            st.success("✅ 已刪除該筆電訪紀錄！")
                                            st.rerun()

                    st.markdown("---")
                    
                    st.subheader(f"📦 為【{cname}】新增訂單")
                    with st.form(key=f"add_order_for_tab1_{cid}", clear_on_submit=True):
                        oc1, oc2, oc3 = st.columns(3)
                        with oc1:
                            new_order_chan = st.selectbox("購買管道 *", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])
                            new_order_date = st.date_input("訂購日期 *", value=datetime.today())
                        with oc2:
                            new_order_prod = st.text_input("訂購商品名稱與規格 *", placeholder="例：有機三色藜麥片 3罐組")
                            new_order_amt = st.number_input("訂單金額 (NT$)", min_value=0, step=50, value=0)
                        with oc3:
                            new_order_status = st.selectbox("訂單狀態", ["已接單/待出貨", "已出貨", "已完成", "售後追蹤中", "取消/退貨"])
                            new_order_notes = st.text_input("本次訂單備註", placeholder="例：送禮給第二收件人")

                        add_order_btn = st.form_submit_button("➕ 建立這筆新訂單")
                        if add_order_btn:
                            if not new_order_prod:
                                st.error("請填寫訂購商品！")
                            else:
                                chan_clean = "電話訂購" if "電話" in new_order_chan else ("官網" if "官網" in new_order_chan else new_order_chan)
                                execute_query("""
                                    INSERT INTO orders (customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes)
                                    VALUES (:cid, :chan, :prod, :amt, :odate, '', :status, :notes)
                                """, {
                                    "cid": cid, "chan": chan_clean, "prod": new_order_prod,
                                    "amt": new_order_amt, "odate": str(new_order_date),
                                    "status": new_order_status, "notes": new_order_notes
                                })
                                st.success(f"🎉 已成功為【{cname}】新增訂單！")
                                st.rerun()

                    st.markdown("---")
                    st.markdown("#### 📜 歷史購買紀錄 (點擊展開檢視/編輯/刪除)")
                    with st.expander(f"📁 點擊展開【{cname}】的 {total_orders} 筆歷史訂單明細", expanded=False):
                        render_editable_orders(history_df, "tab1")

# ==========================================
# TAB 2: 建立全新會員名單
# ==========================================
with tab2:
    st.subheader("🆕 建立全新會員名單（系統自動編排 CRM 代號）")
    auto_code = get_next_crm_code()
    st.info(f"系統已自動指派下一位會員代號：`:blue[**{auto_code}**]`")

    with st.form("create_new_customer_form", clear_on_submit=True):
        st.markdown("##### 👤 【本人】基本資料與常用地址")
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            n_code = st.text_input("客戶代號", value=auto_code)
            n_name = st.text_input("客戶姓名 *")
            n_gender = st.selectbox("性別", ["女", "男", "其他"])
        with nc2:
            n_phone = st.text_input("主要手機 *", placeholder="例：0912345678")
            n_phone_bak = st.text_input("備用手機 (選填)")
            n_tel = st.text_input("市話電話 (選填)")
        with nc3:
            n_id_card = st.text_input("身分證號 / 統編 (選填)")
            n_email = st.text_input("EMAIL (選填)")
            n_source = st.selectbox("顧客來源 (廣告追蹤) *", SOURCES_LIST)

        n_addr = st.text_input("常用收件地址 (本人) *")
        n_pref = st.text_area("備註 (客戶習慣/特殊需求)", placeholder="例：只吃無糖、全素、需代收")

        st.markdown("##### 🎁 【送禮專用 / 第二收件人】資料 (選填)")
        nr2_1, nr2_2 = st.columns(2)
        with nr2_1:
            n_r2_name = st.text_input("第二收件人姓名 (送禮對象)")
        with nr2_2:
            n_r2_phone = st.text_input("第二收件人手機 (送禮電話)")
        n_r2_addr = st.text_input("第二收件地址 (送禮地址)")

        st.markdown("##### 📦 首次訂購品項（選填）")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            n_prod = st.text_input("訂購商品名稱與規格", placeholder="例：有機三色藜麥片 3罐組")
            n_channel = st.selectbox("首次接觸管道", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])
        with fc2:
            n_amt = st.number_input("訂單金額", min_value=0, step=50, value=0)
        with fc3:
            n_date = st.date_input("訂購日期", value=datetime.today())

        submit_new_cust = st.form_submit_button("🚀 建立全新會員檔案並存檔")

        if submit_new_cust:
            clean_np = clean_phone(n_phone)
            if not n_name or not clean_np or not n_addr:
                st.error("請完整填寫『客戶姓名』、『主要手機』與『常用收件地址』！")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                res = execute_query("""
                    INSERT INTO customers (customer_id, customer_code, name, gender, id_card, phone, phone_backup, tel, email, 
                                           address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at, customer_source)
                    VALUES (DEFAULT, :code, :name, :gender, :id_card, :phone, :phone_bak, :tel, :email, 
                            :addr, :r2_name, :r2_phone, :r2_addr, :pref, :created_at, :source)
                    RETURNING customer_id
                """, {
                    "code": n_code, "name": n_name, "gender": n_gender, "id_card": n_id_card,
                    "phone": clean_np, "phone_bak": n_phone_bak, "tel": n_tel, "email": n_email,
                    "addr": n_addr, "r2_name": n_r2_name, "r2_phone": clean_phone(n_r2_phone),
                    "r2_addr": n_r2_addr, "pref": n_pref, "created_at": now_str, "source": n_source
                })
                new_cid = res.fetchone()[0]
                st.cache_data.clear()

                if n_prod:
                    chan_clean = "電話訂購" if "電話" in n_channel else ("官網" if "官網" in n_channel else n_channel)
                    execute_query("""
                        INSERT INTO orders (customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes)
                        VALUES (:cid, :chan, :prod, :amt, :odate, '', '已接單/待出貨', '')
                    """, {
                        "cid": new_cid, "chan": chan_clean, "prod": n_prod,
                        "amt": n_amt, "odate": str(n_date)
                    })

                st.success(f"🎉 成功建立新會員【{n_name}】（代號：{n_code}，來源：{n_source}）！")
                st.rerun()

# ==========================================
# TAB 3: 歷史訂購紀錄 (🌟 同步升級為直接展開版)
# ==========================================
with tab3:
    col_left_spacer_t3, col_main_center_t3, col_right_spacer_t3 = st.columns([1, 4, 1])
    
    with col_main_center_t3:
        st.markdown('<div class="search-header-box"><h3 style="margin:0; color:#2d3748;">👤 歷史訂單紀錄查詢</h3></div>', unsafe_allow_html=True)
        st.markdown('<div class="search-content-box">', unsafe_allow_html=True)
        
        t3_search = st.text_input("🔍 搜尋客戶 (請輸入姓名、手機或代號)：", key="tab3_search").strip()
        st.markdown('</div>', unsafe_allow_html=True)

        df_cache = get_cached_customers_df()
        if t3_search:
            matched_t3 = search_customers_fast(t3_search)
            if matched_t3:
                c_opts = {f"[{c[1] if str(c[1]).strip() else '待查'}] {c[2]} ({c[5]})": c[0] for c in matched_t3}
            else:
                c_opts = {}
        else:
            c_opts = {f"[{row['customer_code']}] {row['name']} ({row['phone']})": row['customer_id'] for _, row in df_cache.iterrows()}

        if c_opts:
            sel_label = st.selectbox("選擇要檢視的客戶：", list(c_opts.keys()), key="timeline_select_cust")
            sel_cid = c_opts[sel_label]
            
            cust = get_customer_by_id(sel_cid)
            h_df = get_customer_history(sel_cid)

            if cust:
                cid = cust['customer_id']
                ccode = str(cust['customer_code']).strip() if pd.notna(cust['customer_code']) else ""
                cname = cust['name']
                cgender = cust['gender']
                cid_card = cust['id_card']
                cphone = cust['phone']
                cphone_bak = cust['phone_backup']
                ctel = cust['tel']
                cemail = cust['email']
                caddr = cust['address']
                cr2_name = cust['recipient2_name']
                cr2_phone = cust['recipient2_phone']
                cr2_addr = cust['recipient2_address']
                cpref = cust['dietary_preference']
                csource = cust.get('customer_source') or "未指定 / 自然流量"

                m1, m2 = st.columns(2)
                m1.metric("累積購買次數", f"{len(h_df)} 次")
                m2.metric("累積消費金額", f"NT$ {h_df['amount'].sum():,}")

                # 🌟 移除 expander，直接顯示與 Tab 1 相同的編輯版面
                st.markdown('<div class="edit-header-box"><h3 style="margin:0; color:#2c5282;">✏️ 基本資料編輯</h3></div>', unsafe_allow_html=True)
                st.markdown('<div class="edit-content-box">', unsafe_allow_html=True)
                
                with st.form(key=f"edit_cust_form_tab3_{cid}"):
                    tc_left, tc_right = st.columns(2)
                    
                    with tc_left:
                        next_avail_t3 = get_next_crm_code()
                        code_label_t3 = "客戶代號" if ccode else f"客戶代號 (系統建議新號：{next_avail_t3})"
                        t_code = st.text_input(code_label_t3, value=ccode)
                        t_name = st.text_input("姓  名 *", value=cname if cname else "")
                        t_phone = st.text_input("行 動 (1) *", value=cphone if cphone else "")
                        t_tel = st.text_input("電 話 (1)", value=ctel if ctel else "")
                        
                    with tc_right:
                        t_id_card = st.text_input("身分證號 / 統編", value=cid_card if cid_card else "")
                        t_gender = st.selectbox("性  別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2))
                        t_phone_bak = st.text_input("行 動 (2)", value=cphone_bak if cphone_bak else "")
                        st.markdown("<br><br>", unsafe_allow_html=True) # 佔位對齊

                    t_addr = st.text_input("地  址 *", value=caddr if caddr else "")
                    t_pref = st.text_area("備註 (客戶習慣/特殊需求)", value=cpref if cpref else "")

                    st.markdown("---")
                    st.markdown("##### 🎁 送禮 / 第二收件人")
                    tr2_1, tr2_2 = st.columns(2)
                    with tr2_1:
                        t_r2_name = st.text_input("第二收件人姓名 (送禮對象)", value=cr2_name if cr2_name else "")
                    with tr2_2:
                        t_r2_phone = st.text_input("第二收件人手機 (送禮電話)", value=cr2_phone if cr2_phone else "")
                    t_r2_addr = st.text_input("第二收件地址 (送禮地址)", value=cr2_addr if cr2_addr else "")

                    t_save_btn = st.form_submit_button("💾 儲存並更新客戶基本資料", use_container_width=True)
                    if t_save_btn:
                        update_customer_db(cid, t_code, t_name, t_gender, t_id_card, t_phone, t_phone_bak, t_tel, cemail, t_addr, t_r2_name, t_r2_phone, t_r2_addr, t_pref, csource)
                        st.success("✅ 客戶資料已同步更新！")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                with st.expander("⚠️ 危險操作區：刪除此會員帳號", expanded=False):
                    st.warning("若此會員為重複建檔的幽靈帳號，確認後可點擊下方按鈕將其永久刪除（包含歷史訂單）。")
                    del_cust_chk_t3 = st.checkbox(f"我確定要刪除客戶 【{cname}】", key=f"chk_del_cust_t3_{cid}")
                    if del_cust_chk_t3:
                        if st.button(f"🚨 確認永久刪除此會員", key=f"btn_del_cust_t3_{cid}", type="primary"):
                            delete_customer(cid)
                            st.success(f"✅ 已成功刪除會員 【{cname}】！")
                            st.rerun()

                with st.expander("📞 電訪追蹤紀錄與下次提醒（點擊展開/收合）", expanded=False):
                    st.markdown("##### ➕ 新增一通電訪紀錄")
                    with st.form(key=f"tele_form_tab3_{cid}", clear_on_submit=True):
                        tc_col1, tc_col2 = st.columns(2)
                        with tc_col1:
                            call_status = st.selectbox("撥打狀態", ["成功下單", "考慮中", "無人接聽", "拒絕/空號"])
                            next_date = st.date_input("下次提醒再訪日 (選填)", value=None)
                        with tc_col2:
                            call_notes = st.text_area("電訪筆記與備註", placeholder="例：詢問燕麥奶庫存狀況，表示下週回電。")

                        save_call_btn = st.form_submit_button("📞 儲存這通電訪紀錄")
                        if save_call_btn:
                            execute_query("""
                                INSERT INTO telemarketing_logs (customer_id, agent_name, call_status, call_notes, next_followup_date)
                                VALUES (:cid, :agent, :status, :notes, :ndate)
                            """, {
                                "cid": cid,
                                "agent": st.session_state.username,
                                "status": call_status,
                                "notes": call_notes,
                                "ndate": next_date if next_date else None
                            })
                            st.success("✅ 電訪紀錄已成功儲存！")
                            st.rerun()

                    past_logs = read_query("SELECT log_id, agent_name, call_status, call_notes, next_followup_date, created_at FROM telemarketing_logs WHERE customer_id = :cid ORDER BY created_at DESC", {"cid": cid})
                    if not past_logs.empty:
                        st.markdown("---")
                        st.markdown("##### ✏️ 歷史電訪紀錄（展開可直接修改）")
                        for _, plog in past_logs.iterrows():
                            log_id = plog['log_id']
                            nd_display = str(plog['next_followup_date']) if pd.notna(plog['next_followup_date']) else "無"
                            
                            with st.expander(f"🕒 [{str(plog['created_at'])[:16]}] 專員: {plog['agent_name']} | 狀態: {plog['call_status']} | 提醒: {nd_display}", expanded=False):
                                with st.form(key=f"edit_tele_form_t3_{cid}_{log_id}"):
                                    e_t1, e_t2 = st.columns(2)
                                    with e_t1:
                                        e_status = st.selectbox("撥打狀態", ["成功下單", "考慮中", "無人接聽", "拒絕/空號"], index=["成功下單", "考慮中", "無人接聽", "拒絕/空號"].index(plog['call_status']) if plog['call_status'] in ["成功下單", "考慮中", "無人接聽", "拒絕/空號"] else 0)
                                        try:
                                            default_nd = datetime.strptime(str(plog['next_followup_date']), "%Y-%m-%d").date() if pd.notna(plog['next_followup_date']) else None
                                        except:
                                            default_nd = None
                                        e_ndate = st.date_input("下次提醒再訪日", value=default_nd)
                                    with e_t2:
                                        e_notes = st.text_area("電訪筆記", value=str(plog['call_notes']) if pd.notna(plog['call_notes']) else "")

                                    e_save_btn = st.form_submit_button("💾 儲存此筆電訪修改")
                                    if e_save_btn:
                                        execute_query("""
                                            UPDATE telemarketing_logs 
                                            SET call_status = :status, call_notes = :notes, next_followup_date = :ndate
                                            WHERE log_id = :lid
                                        """, {
                                            "status": e_status,
                                            "notes": e_notes,
                                            "ndate": e_ndate if e_ndate else None,
                                            "lid": log_id
                                        })
                                        st.success("✅ 電訪紀錄修改成功！")
                                        st.rerun()

                                del_tele_chk = st.checkbox(f"⚠️ 確認刪除此筆電訪紀錄 (#{log_id})？", key=f"del_tele_chk_t3_{log_id}")
                                if del_tele_chk:
                                    if st.button("🚨 確認刪除電訪", key=f"btn_del_tele_t3_{log_id}"):
                                        execute_query("DELETE FROM telemarketing_logs WHERE log_id = :lid", {"lid": log_id})
                                        st.success("✅ 已刪除該筆電訪紀錄！")
                                        st.rerun()

                st.markdown("---")
                st.subheader(f"📦 為【{cname}】新增訂單")
                with st.form(key=f"add_order_for_tab3_{cid}", clear_on_submit=True):
                    oc1, oc2, oc3 = st.columns(3)
                    with oc1:
                        new_order_chan = st.selectbox("購買管道 *", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])
                        new_order_date = st.date_input("訂購日期 *", value=datetime.today())
                    with oc2:
                        new_order_prod = st.text_input("訂購商品名稱與規格 *", placeholder="例：有機三色藜麥片 3罐組")
                        new_order_amt = st.number_input("訂單金額 (NT$)", min_value=0, step=50, value=0)
                    with oc3:
                        new_order_status = st.selectbox("訂單狀態", ["已接單/待出貨", "已出貨", "已完成", "售後追蹤中", "取消/退貨"])
                        new_order_notes = st.text_input("本次訂單備註", placeholder="例：送禮給第二收件人")

                    add_order_btn = st.form_submit_button("➕ 建立這筆新訂單")
                    if add_order_btn:
                        if not new_order_prod:
                            st.error("請填寫訂購商品！")
                        else:
                            chan_clean = "電話訂購" if "電話" in new_order_chan else ("官網" if "官網" in new_order_chan else new_order_chan)
                            execute_query("""
                                INSERT INTO orders (customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes)
                                VALUES (:cid, :chan, :prod, :amt, :odate, '', :status, :notes)
                            """, {
                                "cid": cid, "chan": chan_clean, "prod": new_order_prod,
                                "amt": new_order_amt, "odate": str(new_order_date),
                                "status": new_order_status, "notes": new_order_notes
                            })
                            st.success(f"🎉 已成功為【{cname}】新增訂單！")
                            st.rerun()

                st.markdown("---")
                st.markdown("#### 📜 歷史購買紀錄 (點擊展開檢視/編輯/刪除)")
                with st.expander(f"📁 點擊展開【{cname}】的 {len(h_df)} 筆歷史訂單明細", expanded=False):
                    render_editable_orders(h_df, "tab3")
        else:
            st.info("⚠️ 查無符合條件的客戶。")

# ==========================================
# 🌟 Python 處理歷史訂單匯出格式函數 (西元轉民國, 附帶管道代碼)
# ==========================================
def format_export_order(dstr, channel_prefix):
    if pd.isna(dstr) or not str(dstr).strip(): 
        return ""
    try:
        d = pd.to_datetime(dstr)
        roc_year = d.year - 1911
        return f"{channel_prefix}{roc_year}-{d.strftime('%m%d')}"
    except:
        return ""

# ==========================================
# TAB 4: 客戶名冊總表
# ==========================================
with tab4:
    st.subheader("📊 客戶名冊總表")
    
    col_filter, _ = st.columns([3, 1])
    with col_filter:
        show_pending_only = st.checkbox("🔍 只顯示「無代號 / 待確認」的名單")
        tab4_search = st.text_input("🔍 在總表中搜尋 (請輸入姓名、手機號碼或客戶代號)：", key="tab4_search").strip()

    df_all = read_query("""
        SELECT 
            c.customer_id,
            c.customer_code AS "客戶代號",
            c.name AS "姓名",
            c.customer_source AS "顧客來源",
            c.gender AS "性別",
            c.phone AS "主要手機",
            c.phone_backup AS "備用手機",
            c.tel AS "市話",
            c.address AS "常用地址",
            (SELECT channel FROM orders WHERE customer_id = c.customer_id ORDER BY order_date DESC LIMIT 1) AS "最後購買管道",
            COUNT(o.order_id) AS "總購買次數",
            COALESCE(SUM(o.amount), 0) AS "歷史消費金額",
            MAX(o.order_date) AS "最後購買日",
            (SELECT STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) FROM orders WHERE customer_id = c.customer_id) AS "所有訂購明細",
            (SELECT STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) FROM orders WHERE customer_id = c.customer_id AND channel LIKE '%官網%') AS "官網訂單",
            (SELECT STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) FROM orders WHERE customer_id = c.customer_id AND (channel LIKE '%電話%' OR channel LIKE '%廣播%')) AS "電話訂單"
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id
        ORDER BY c.customer_code DESC, c.customer_id DESC
    """)

    if not df_all.empty:
        df_filtered = df_all

        if show_pending_only:
            df_filtered = df_filtered[(df_filtered["客戶代號"].isna()) | (df_filtered["客戶代號"].str.strip() == "")]

        if tab4_search:
            search_upper = tab4_search.upper()
            df_filtered = df_filtered[
                df_filtered["姓名"].str.contains(tab4_search, na=False) | 
                df_filtered["主要手機"].str.contains(tab4_search, na=False) |
                df_filtered["客戶代號"].str.contains(search_upper, na=False)
            ]

        st.markdown("💡 **小提示：此總表為純檢視模式，載入最為快速。若需刪除重複會員或編輯補上代號，請直接切換至「🔍 舊客速查與編輯」頁面操作。**")

        display_df = df_filtered.drop(columns=["所有訂購明細", "官網訂單", "電話訂單", "customer_id"], errors='ignore')
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            
            base_cols = ["客戶代號", "姓名", "顧客來源", "性別", "主要手機", "備用手機", "市話", "常用地址", "最後購買管道", "總購買次數", "歷史消費金額", "最後購買日"]
            
            export_all = df_filtered[base_cols + ["所有訂購明細"]].copy()
            export_all["所有訂購明細"] = export_all["所有訂購明細"].fillna("")
            split_all = export_all["所有訂購明細"].str.split(r"\|\|\|", regex=True, expand=True)
            if not split_all.empty and split_all.shape[1] > 0:
                for col in split_all.columns:
                    split_all[col] = split_all[col].apply(lambda x: format_export_order(x, "A") if isinstance(x, str) else "")
                split_all.columns = [f"購{i+1}" for i in range(split_all.shape[1])]
                export_all = export_all.drop(columns=["所有訂購明細"]).join(split_all)
            else:
                export_all = export_all.drop(columns=["所有訂購明細"])
            export_all.to_excel(writer, index=False, sheet_name='綜合名單總表')

            export_web = df_filtered[df_filtered["官網訂單"].notna()][base_cols + ["官網訂單"]].copy()
            split_web = export_web["官網訂單"].str.split(r"\|\|\|", regex=True, expand=True)
            if not split_web.empty and split_web.shape[1] > 0:
                for col in split_web.columns:
                    split_web[col] = split_web[col].apply(lambda x: format_export_order(x, "A") if isinstance(x, str) else "")
                split_web.columns = [f"購{i+1}" for i in range(split_web.shape[1])]
                export_web = export_web.drop(columns=["官網訂單"]).join(split_web)
            else:
                export_web = export_web.drop(columns=["官網訂單"])
            export_web.to_excel(writer, index=False, sheet_name='官網客戶名單')

            export_phone = df_filtered[df_filtered["電話訂單"].notna()][base_cols + ["電話訂單"]].copy()
            split_phone = export_phone["電話訂單"].str.split(r"\|\|\|", regex=True, expand=True)
            if not split_phone.empty and split_phone.shape[1] > 0:
                for col in split_phone.columns:
                    split_phone[col] = split_phone[col].apply(lambda x: format_export_order(x, "B") if isinstance(x, str) else "")
                split_phone.columns = [f"購{i+1}" for i in range(split_phone.shape[1])]
                export_phone = export_phone.drop(columns=["電話訂單"]).join(split_phone)
            else:
                export_phone = export_phone.drop(columns=["電話訂單"])
            export_phone.to_excel(writer, index=False, sheet_name='電話客戶名單')

        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 匯出精準分類名冊 (內含：綜合總表 / 官網名單 / 電話名單 三個工作表)",
            data=excel_data,
            file_name="有其田_客戶完整名冊.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.info("尚無客戶資料。")

# ==========================================
# TAB 7: 🎯 智慧回購清單與電銷戰情室
# ==========================================
with tab7:
    st.subheader("🎯 智慧回購清單與電銷追蹤戰情室")
    st.markdown("系統自動幫您篩選出「今日需要再次電訪」以及「超過 180 天未回購的沉睡客」名單，點擊即可直接展開聯繫！")

    today_str = date.today().strftime("%Y-%m-%d")

    st.markdown("#### 🔔 今日預定再訪清單 (依電訪提醒日)")
    followup_df = read_query("""
        SELECT DISTINCT c.customer_id, c.customer_code, c.name, c.phone, t.next_followup_date, t.call_status, t.call_notes
        FROM telemarketing_logs t
        JOIN customers c ON t.customer_id = c.customer_id
        WHERE t.next_followup_date <= :today
        ORDER BY t.next_followup_date ASC
    """, {"today": today_str})

    if followup_df.empty:
        st.info("🎉 目前沒有設定今天必須回訪的客戶！")
    else:
        st.dataframe(followup_df.drop(columns=["customer_id"]), use_container_width=True)

    st.markdown("---")

    st.markdown("#### 💤 潛在沉睡客喚醒名單 (超過 180 天未回購)")
    
    raw_orders_for_dormant = read_query("""
        SELECT 
            c.customer_id,
            c.customer_code AS "客戶代號",
            c.name AS "姓名",
            c.phone AS "主要手機",
            o.order_date,
            o.amount
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
    """)

    if raw_orders_for_dormant.empty:
        st.info("目前尚無訂單資料。")
    else:
        raw_orders_for_dormant['parsed_date'] = pd.to_datetime(raw_orders_for_dormant['order_date'], errors='coerce')
        
        agg_df = raw_orders_for_dormant.groupby(['customer_id', '客戶代號', '姓名', '主要手機']).agg(
            最後購買日=('parsed_date', 'max'),
            歷史消費金額=('amount', 'sum')
        ).reset_index()

        cutoff_date = pd.Timestamp(date.today() - timedelta(days=180))
        
        valid_dormant = agg_df.dropna(subset=['最後購買日'])
        dormant_df = valid_dormant[valid_dormant['最後購買日'] < cutoff_date].sort_values(by='歷史消費金額', ascending=False).head(50)
        dormant_df['最後購買日'] = dormant_df['最後購買日'].dt.strftime('%Y-%m-%d')

        if dormant_df.empty:
            st.info("目前沒有超過 180 天未回購的沉睡客。")
        else:
            st.dataframe(dormant_df.drop(columns=["customer_id"]), use_container_width=True)
            
            dormant_output = io.BytesIO()
            with pd.ExcelWriter(dormant_output, engine='xlsxwriter') as writer:
                dormant_df.drop(columns=["customer_id"]).to_excel(writer, index=False, sheet_name='沉睡客名單')
            dormant_excel = dormant_output.getvalue()

            st.download_button(
                label="📥 匯出這批沉睡客名單 (XLSX)",
                data=dormant_excel,
                file_name="有其田_沉睡客喚醒名單.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ==========================================
# TAB 6: 期間訂單報表與電銷績效匯出
# ==========================================
with tab6:
    st.subheader("📅 期間訂單紀錄與電話行銷成效報表")
    
    report_type = st.radio("選擇要產生的報表類型：", ["📦 期間訂單明細報表", "📞 電話行銷漏斗與客服績效報表"], horizontal=True)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("起始日期", value=date.today().replace(day=1))
    with col_d2:
        end_date = st.date_input("結束日期", value=date.today())

    if st.button("📊 產生並下載報表"):
        if start_date > end_date:
            st.error("起始日期不能大於結束日期！")
        else:
            if report_type == "📦 期間訂單明細報表":
                report_sql = """
                    SELECT 
                        o.order_date AS "訂購日期",
                        c.customer_code AS "客戶代號",
                        c.name AS "客戶姓名",
                        c.phone AS "手機號碼",
                        c.customer_source AS "顧客來源",
                        o.product AS "商品名稱",
                        o.amount AS "訂單金額",
                        o.channel AS "購買管道",
                        o.status AS "訂單狀態",
                        o.order_notes AS "訂單備註"
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    WHERE o.order_date >= :s_date AND o.order_date <= :e_date
                    ORDER BY o.order_date DESC, o.order_id DESC
                """
                report_df = read_query(report_sql, {"s_date": str(start_date), "e_date": str(end_date)})

                if report_df.empty:
                    st.warning("⚠️ 此區間內無訂單紀錄。")
                else:
                    st.success(f"✅ 成功撈取 **{len(report_df)}** 筆訂單，總金額：NT$ {report_df['訂單金額'].sum():,}")
                    st.dataframe(report_df, use_container_width=True)

                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
                        report_df.to_excel(w, index=False, sheet_name='訂單報表')
                    st.download_button("📥 下載訂單明細 (XLSX)", out.getvalue(), f"有其田_訂單報表_{start_date}至{end_date}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            else:
                tele_sql = """
                    SELECT 
                        agent_name AS "客服專員",
                        call_status AS "撥打狀態",
                        COUNT(*) AS "通話次數"
                    FROM telemarketing_logs
                    WHERE created_at::date >= :s_date AND created_at::date <= :e_date
                    GROUP BY agent_name, call_status
                    ORDER BY agent_name, "通話次數" DESC
                """
                tele_df = read_query(tele_sql, {"s_date": str(start_date), "e_date": str(end_date)})

                if tele_df.empty:
                    st.warning("⚠️ 此區間內無電訪紀錄。")
                else:
                    st.success("✅ 成功產生電銷漏斗與專員績效統計！")
                    st.dataframe(tele_df, use_container_width=True)

                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
                        tele_df.to_excel(w, index=False, sheet_name='電銷績效報表')
                    st.download_button("📥 下載電銷績效報表 (XLSX)", out.getvalue(), f"有其田_電銷績效報表_{start_date}至{end_date}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# TAB 5: 批次匯入舊名單與官網訂單報表
# ==========================================
with tab5:
    st.subheader("📥 智慧匯入中心（自動隔離待查名單與去重）")
    st.info("💡 支援官網訂單報表與舊名單上傳。系統會自動依「手機號碼」防重複建檔。")
    
    uploaded_file = st.file_uploader("上傳 Excel 檔案（.xlsx）", type=["xlsx", "xls"], key="excel_uploader_tab5")

    if uploaded_file is not None:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            st.write(f"📂 偵測到工作表：`{', '.join(excel_file.sheet_names)}`")
            
            if st.button("🚀 確認並開始智慧增量匯入"):
                bar = st.progress(10)
                status = st.empty()

                status.info("⚡ [1/3] 正在載入現有資料庫快取與解析 Excel...")
                existing_cust_df = read_query("SELECT customer_id, customer_code, phone FROM customers")
                code_to_id = {}
                phone_to_id = {}

                for _, r in existing_cust_df.iterrows():
                    cid = int(r['customer_id'])
                    c_code = str(r['customer_code']).strip() if pd.notna(r['customer_code']) else ""
                    c_phone = str(r['phone']).strip() if pd.notna(r['phone']) else ""
                    if c_code:
                        code_to_id[c_code] = cid
                    if c_phone:
                        phone_to_id[c_phone] = cid

                existing_orders_df = read_query("SELECT customer_id, raw_date_code FROM orders WHERE raw_date_code != ''")
                existing_order_set = set(zip(existing_orders_df['customer_id'].astype(int), existing_orders_df['raw_date_code'].astype(str)))

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cust_inserts = []
                order_tasks = []

                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=str)
                    
                    columns_str = "".join(df.columns)
                    is_official_web_report = "訂單編號" in columns_str and "訂單金額" in columns_str

                    if is_official_web_report:
                        status.info("⚡ 偵測到【官網訂單報表】格式，正在以手機號碼進行智慧對應與去重...")
                        
                        cleaned_orders = []
                        for order_id, group in df.groupby('訂單編號'):
                            if pd.isna(order_id) or not str(order_id).strip():
                                continue
                            first_row = group.iloc[0]
                            name = str(first_row.get("會員名稱", "")).strip()
                            phone = clean_phone(first_row.get("會員手機號碼", ""))
                            time_str = str(first_row.get("時間", "")).strip()
                            order_amt = first_row.get("訂單金額", 0)
                            try:
                                amt_val = float(order_amt) if pd.notna(order_amt) else 0.0
                            except:
                                amt_val = 0.0

                            match_date = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", time_str)
                            order_date = match_date.group(1).replace("/", "-") if match_date else str(date.today())

                            products = [str(p).strip() for p in group.get("訂購商品", []) if pd.notna(p) and str(p).strip()]
                            product_desc = " / ".join(products) if products else "官網訂購品項"

                            if not phone:
                                continue

                            cleaned_orders.append({
                                "name": name,
                                "phone": phone,
                                "order_id_code": str(order_id).strip(),
                                "order_date": order_date,
                                "amount": amt_val,
                                "product": product_desc,
                                "channel": "官網"
                            })

                        for ord_item in cleaned_orders:
                            p1 = ord_item["phone"]
                            name = ord_item["name"]
                            r_code = ord_item["order_id_code"]

                            matched_cid = phone_to_id.get(p1)

                            if matched_cid:
                                if (matched_cid, r_code) not in existing_order_set:
                                    order_tasks.append({
                                        "target": matched_cid,
                                        "channel": ord_item["channel"],
                                        "product": ord_item["product"],
                                        "amount": ord_item["amount"],
                                        "order_date": ord_item["order_date"],
                                        "raw_date_code": r_code,
                                        "status": "已結案"
                                    })
                                    existing_order_set.add((matched_cid, r_code))
                            else:
                                cust_code = ""

                                cust_inserts.append({
                                    "customer_code": cust_code, "name": name, "gender": "女", "id_card": "",
                                    "phone": p1, "phone_backup": "", "tel": "", "address": "官網匯入地址", "created_at": now_str,
                                    "customer_source": "官網"
                                })
                                phone_to_id[p1] = p1

                                order_tasks.append({
                                    "target": p1,
                                    "channel": ord_item["channel"],
                                    "product": ord_item["product"],
                                    "amount": ord_item["amount"],
                                    "order_date": ord_item["order_date"],
                                    "raw_date_code": r_code,
                                    "status": "已結案"
                                })

                    else:
                        default_channel = "官網" if "官網" in sheet_name else "電話訂購"

                        for _, row in df.iterrows():
                            cust_code = str(row.get("客戶代號", "")).strip() if pd.notna(row.get("客戶代號")) else ""
                            name = str(row.get("姓名", "")).strip() if pd.notna(row.get("姓名")) else ""
                            p1 = clean_phone(row.get("行動(1)", ""))
                            p2 = clean_phone(row.get("行動(2)", ""))
                            t1 = str(row.get("電話(1)", "")).strip() if pd.notna(row.get("電話(1)")) else ""
                            addr = str(row.get("地址", "")).strip() if pd.notna(row.get("地址")) else ""
                            gender = str(row.get("性別", "")).strip() if pd.notna(row.get("性別")) else ""
                            id_card = str(row.get("身分證號", "")).strip() if pd.notna(row.get("身分證號")) else ""

                            if not name or (not p1 and not t1 and not cust_code):
                                continue

                            row_orders = []
                            for col_name, val in row.items():
                                if pd.notna(val) and str(val).strip() != "":
                                    col_str = str(col_name)
                                    val_str = str(val).strip()
                                    
                                    if (col_str.startswith("購") and "商品" not in col_str) or col_str.startswith("Unnamed"):
                                        if (("-" in val_str) or ("/" in val_str) or val_str.upper().startswith("A") or val_str.upper().startswith("B") or val_str.upper().startswith("L")):
                                            o_chan, o_date, r_code = parse_date_code(val_str, default_channel)
                                            row_orders.append((o_chan, o_date, r_code))

                            matched_cid = None
                            if cust_code and cust_code in code_to_id:
                                matched_cid = code_to_id[cust_code]
                            elif p1 and p1 in phone_to_id:
                                matched_cid = phone_to_id[p1]

                            if matched_cid:
                                for o_chan, o_date, r_code in row_orders:
                                    if (matched_cid, r_code) not in existing_order_set:
                                        order_tasks.append({
                                            "target": matched_cid,
                                            "channel": o_chan,
                                            "product": "常態訂購品項",
                                            "amount": 0,
                                            "order_date": o_date,
                                            "raw_date_code": r_code,
                                            "status": "歷史完成"
                                        })
                                        existing_order_set.add((matched_cid, r_code))
                            else:
                                if not cust_code:
                                    cust_code = ""

                                cust_inserts.append({
                                    "customer_code": cust_code, "name": name, "gender": gender, "id_card": id_card,
                                    "phone": p1, "phone_backup": p2, "tel": t1, "address": addr, "created_at": now_str,
                                    "customer_source": "未指定 / 自然流量"
                                })
                                if p1:
                                    phone_to_id[p1] = p1 if not cust_code else cust_code
                                if cust_code:
                                    code_to_id[cust_code] = cust_code

                                for o_chan, o_date, r_code in row_orders:
                                    order_tasks.append({
                                        "target": cust_code if cust_code else p1,
                                        "channel": o_chan,
                                        "product": "常態訂購品項",
                                        "amount": 0,
                                        "order_date": o_date,
                                        "raw_date_code": r_code,
                                        "status": "歷史完成"
                                    })

                bar.progress(50)
                status.info(f"⚡ [2/3] 正在寫入 {len(cust_inserts)} 位待確認名單...")

                engine = get_db_engine()
                if cust_inserts:
                    new_cust_df = pd.DataFrame(cust_inserts)
                    new_cust_df.to_sql("customers", engine, if_exists="append", index=False, method="multi", chunksize=500)

                bar.progress(80)
                status.info(f"⚡ [3/3] 正在同步檢索並寫入新增的訂單軌跡與金額...")

                fresh_cust_df = read_query("SELECT customer_id, customer_code, phone FROM customers")
                code_map = {}
                phone_map = {}
                for _, r in fresh_cust_df.iterrows():
                    cid = int(r['customer_id'])
                    if pd.notna(r['customer_code']) and str(r['customer_code']).strip():
                        code_map[str(r['customer_code']).strip()] = cid
                    if pd.notna(r['phone']) and str(r['phone']).strip():
                        phone_map[str(r['phone']).strip()] = cid

                final_orders = []
                for task in order_tasks:
                    target_ref = task["target"]
                    final_cid = None
                    if isinstance(target_ref, int):
                        final_cid = target_ref
                    elif str(target_ref) in code_map:
                        final_cid = code_map[str(target_ref)]
                    elif str(target_ref) in phone_map:
                        final_cid = phone_map[str(target_ref)]

                    if final_cid:
                        final_orders.append({
                            "customer_id": int(final_cid),
                            "channel": task["channel"],
                            "product": task["product"],
                            "amount": task["amount"],
                            "order_date": task["order_date"],
                            "raw_date_code": task["raw_date_code"],
                            "status": task["status"],
                            "order_notes": f"單號: {task['raw_date_code']}"
                        })

                if final_orders:
                    orders_df = pd.DataFrame(final_orders)
                    orders_df = orders_df.drop_duplicates(subset=["customer_id", "raw_date_code"])
                    orders_df.to_sql("orders", engine, if_exists="append", index=False, method="multi", chunksize=1000)

                st.cache_data.clear()

                bar.progress(100)
                status.empty()
                st.success(f"🎉 智慧匯入大成功！成功載入 **{len(cust_inserts)}** 筆名單，並精準寫入 **{len(final_orders)}** 筆訂單與金額！未配對成功的帳號已放置於「待確認名單」中供您查詢。")
        except Exception as e:
            st.error(f"匯入錯誤：{e}")
            
    st.markdown("---")
    st.subheader("🛠️ 資料庫進階維護區：修復重複歷史訂單")
    st.warning("若您先前匯入舊名單產生了「0元 常態訂購品項」的佔位訂單，後來又匯入含有真實金額的「官網報表」導致同一天出現兩筆訂單，請點擊下方按鈕進行智慧清理。")
    if st.button("🧹 一鍵自動清理「同日重複的 0 元佔位訂單」"):
        try:
            cleanup_sql = """
                DELETE FROM orders o1
                WHERE o1.amount = 0
                  AND EXISTS (
                      SELECT 1 
                      FROM orders o2
                      WHERE o2.customer_id = o1.customer_id
                        AND o2.order_date = o1.order_date
                        AND o2.order_id != o1.order_id
                        AND o2.amount > 0
                  );
            """
            execute_query(cleanup_sql)
            st.success("✅ 已經成功掃描並清除了所有重複的 0 元佔位訂單！您的客戶歷史訂購紀錄已經完全乾淨了！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"清理失敗，請聯絡管理員：{e}")
