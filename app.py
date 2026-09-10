import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import io
import re
import random
import smtplib
from email.mime.text import MIMEText

# --- 0. 設定頁面配置與「物理放大降維打擊」CSS ---
st.set_page_config(page_title="有其田 客服 CRM 系統", layout="wide", page_icon="🌾")

# 🔥 顧客來源選項 (Phase 1 廣告追蹤)
SOURCES_LIST = [
    "未指定 / 自然流量", 
    "FB 再行銷", 
    "FB 新客", 
    "Google 關鍵字 (Search)", 
    "Google PMAX 廣告", 
    "Google Demand Gen", 
    "LINE 官方帳號", 
    "廣播", 
    "簡訊", 
    "其他"
]

# 🚨 採用無空白行真空壓縮，防止 Streamlit 解析器切斷 CSS
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 24px !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif !important; }
div[data-testid="stTabs"] { overflow: visible !important; }
div[data-testid="stTabs"] > div { overflow: visible !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] { gap: 50px !important; padding-top: 35px !important; padding-bottom: 10px !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] { transform: scale(1.8) !important; transform-origin: left bottom !important; background-color: #f7fafc !important; border-radius: 6px 6px 0 0 !important; border: 1px solid #cbd5e0 !important; border-bottom: none !important; margin-right: 25px !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] * { font-weight: 900 !important; color: #4a5568 !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] { border-top: 4px solid #e53e3e !important; background-color: #fff5f5 !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] * { color: #e53e3e !important; }
h1 { font-size: 45px !important; font-weight: 900 !important; margin-bottom: 24px !important; }
h2, h3 { font-size: 34px !important; font-weight: 800 !important; margin-top: 20px !important; margin-bottom: 16px !important; }
h4, h5 { font-size: 28px !important; font-weight: 700 !important; margin-top: 16px !important; color: #2b6cb0 !important; }
label, label p, [data-testid="stWidgetLabel"] p { font-size: 26px !important; font-weight: 900 !important; color: #1a1a1a !important; margin-bottom: 12px !important; }
input[type="text"], input[type="password"], input[type="number"], select, div[data-baseweb="select"] > div { font-size: 26px !important; min-height: 70px !important; border-radius: 12px !important; border: 2px solid #718096 !important; padding: 12px 20px !important; background-color: #ffffff !important; font-weight: 700 !important; color: #1a202c !important; }
div[data-testid="stInputValue"] { min-height: 70px !important; }
div[data-baseweb="select"] span { font-size: 26px !important; font-weight: 700 !important; }
textarea { font-size: 26px !important; min-height: 140px !important; line-height: 1.6 !important; border: 2px solid #718096 !important; }
.stButton > button { min-height: 72px !important; font-size: 28px !important; font-weight: 900 !important; border-radius: 12px !important; padding: 0 40px !important; margin-top: 14px !important; border: 2px solid #3182ce !important; }
[data-testid="stMetricValue"] { font-size: 46px !important; font-weight: 900 !important; color: #2b6cb0 !important; }
[data-testid="stMetricLabel"] p { font-size: 26px !important; font-weight: 800 !important; }
details summary p, details summary span { font-size: 26px !important; font-weight: 800 !important; color: #2c5282 !important; }
div[data-testid="stDataFrame"] { font-size: 22px !important; }
div[data-testid="column"] { padding: 0 16px !important; }
hr { margin: 36px 0 !important; border: 0 !important; border-top: 3px solid #cbd5e0 !important; }

/* 🌟 電訪區塊專屬：淺綠色視覺區隔 */
div.streamlit-expanderHeader:has(span:contains("電訪追蹤紀錄")) { background-color: #f0fff4 !important; border: 2px solid #38a169 !important; border-radius: 10px !important; }
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
    st.markdown(f"### 👤 目前使用者：`:blue[{st.session_state.username}]`")
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

def get_source_idx(src):
    if src in SOURCES_LIST:
        return SOURCES_LIST.index(src)
    return 0

# --- 4. 主介面排版 ---
st.title("🌾 有其田 客服管理系統")

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
# TAB 1: 舊客戶速查與編輯
# ==========================================
with tab1:
    st.markdown("### 🔍 舊客戶電話 / 代號 / 姓名極速速查")
    
    col_search, _ = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "請輸入查詢關鍵字（姓名、手機或代號）", 
            placeholder="例：蔡汶容、0912345678、或輸入 8761 查詢 CRM008761",
            key="accurate_cust_search"
        ).strip()

    if search_query:
        matched_custs = search_customers_fast(search_query)
        if not matched_custs:
            st.warning(f"⚠️ 查無包含『{search_query}』的客戶資料！若為新客戶請至上方【🆕 建立全新會員名單】分頁。")
        else:
            if len(matched_custs) > 1:
                st.info(f"🔎 找到 {len(matched_custs)} 位符合條件的客戶，請選擇：")
                cust_options = {f"[{c[1]}] {c[2]} (電話:{c[5]} / 地址:{str(c[9])[:20]}...)": c[0] for c in matched_custs}
                selected_cid = st.selectbox("請選擇客戶：", list(cust_options.keys()), key="search_multi_select")
                target_cid = cust_options[selected_cid]
            else:
                target_cid = matched_custs[0][0]

            cust = get_customer_by_id(target_cid)
            if cust:
                cid = cust['customer_id']
                ccode = cust['customer_code']
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

                st.success(f"🎯 已調出客戶：【{cname}】（代號：{ccode}）")

                m1, m2, m3 = st.columns(3)
                m1.metric("累積購買次數", f"{total_orders} 次")
                m2.metric("累積消費金額", f"NT$ {total_spent:,}")
                m3.metric("初次建檔時間", str(ccreated).split()[0] if ccreated else "-")

                with st.expander(f"✏️ 點擊展開／收合【{cname}】的基本資料與收件人設定", expanded=True):
                    with st.form(key=f"edit_cust_form_tab1_{cid}"):
                        st.markdown("##### 👤 【本人】基本資料與常用收件地址")
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            edit_code = st.text_input("客戶代號", value=ccode if ccode else "")
                            edit_name = st.text_input("客戶姓名 *", value=cname if cname else "")
                            edit_gender = st.selectbox("性別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2))
                        with ec2:
                            edit_phone = st.text_input("主要手機 *", value=cphone if cphone else "")
                            edit_phone_bak = st.text_input("備用手機", value=cphone_bak if cphone_bak else "")
                            edit_tel = st.text_input("市話電話", value=ctel if ctel else "")
                        with ec3:
                            edit_id_card = st.text_input("身分證號 / 統編", value=cid_card if cid_card else "")
                            edit_email = st.text_input("EMAIL", value=cemail if cemail else "")
                            edit_source = st.selectbox("顧客來源 (廣告追蹤)", SOURCES_LIST, index=get_source_idx(csource))

                        edit_addr = st.text_input("常用收件地址 (本人) *", value=caddr if caddr else "")
                        edit_pref = st.text_input("飲食偏好 / 重要備註", value=cpref if cpref else "", placeholder="例：只吃無糖、全素、需代收")

                        st.markdown("##### 🎁 【送禮專用 / 第二收件人】資料")
                        r2_c1, r2_c2 = st.columns(2)
                        with r2_c1:
                            edit_r2_name = st.text_input("第二收件人姓名 (送禮對象)", value=cr2_name if cr2_name else "")
                        with r2_c2:
                            edit_r2_phone = st.text_input("第二收件人手機 (送禮電話)", value=cr2_phone if cr2_phone else "")
                        edit_r2_addr = st.text_input("第二收件地址 (送禮地址)", value=cr2_addr if cr2_addr else "")

                        save_cust_btn = st.form_submit_button("💾 儲存並更新客戶資料")

                        if save_cust_btn:
                            if not edit_name or not edit_phone or not edit_addr:
                                st.error("姓名、主要手機與常用收件地址不可為空！")
                            else:
                                update_customer_db(cid, edit_code, edit_name, edit_gender, edit_id_card, edit_phone, edit_phone_bak, edit_tel, edit_email, edit_addr, edit_r2_name, edit_r2_phone, edit_r2_addr, edit_pref, edit_source)
                                st.success(f"✅ 客戶【{edit_name}】資料已成功更新！")
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

                st.markdown("#### 📜 歷史購買紀錄 (點擊可展開編輯與刪除)")
                render_editable_orders(history_df, "tab1")

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
        n_pref = st.text_input("飲食偏好 / 客戶備註", placeholder="例：只吃無糖、全素、需代收")

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
# TAB 3: 歷史訂購紀錄
# ==========================================
with tab3:
    col_t3_title, col_t3_search = st.columns([1, 1])
    with col_t3_title:
        st.subheader("👤 客戶檔案 與 歷史訂購紀錄")
    with col_t3_search:
        t3_search = st.text_input("🔍 搜尋客戶 (請輸入姓名、手機或代號)：", key="tab3_search").strip()

    df_cache = get_cached_customers_df()
    if t3_search:
        matched_t3 = search_customers_fast(t3_search)
        if matched_t3:
            c_opts = {f"[{c[1]}] {c[2]} ({c[5]})": c[0] for c in matched_t3}
        else:
            c_opts = {}
    else:
        c_opts = {f"[{row['customer_code']}] {row['name']} ({row['phone']})": row['customer_id'] for _, row in df_cache.iterrows()}

    if c_opts:
        sel_label = st.selectbox("選擇要檢視或編輯的客戶：", list(c_opts.keys()), key="timeline_select_cust")
        sel_cid = c_opts[sel_label]
        
        cust = get_customer_by_id(sel_cid)
        h_df = get_customer_history(sel_cid)

        if cust:
            cid = cust['customer_id']
            ccode = cust['customer_code']
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

            with st.expander(f"✏️ 點擊展開／收合【{cname}】的基本資料與收件人設定", expanded=True):
                with st.form(key=f"edit_cust_form_tab3_{cid}"):
                    st.markdown("##### 👤 本人資料與常用地址")
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        t_code = st.text_input("客戶代號", value=ccode if ccode else "")
                        t_name = st.text_input("客戶姓名 *", value=cname if cname else "")
                        t_gender = st.selectbox("性別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2))
                    with tc2:
                        t_phone = st.text_input("主要手機 *", value=cphone if cphone else "")
                        t_phone_bak = st.text_input("備用手機", value=cphone_bak if cphone_bak else "")
                        t_tel = st.text_input("市話電話", value=ctel if ctel else "")
                    with tc3:
                        t_id_card = st.text_input("身分證號 / 統編", value=cid_card if cid_card else "")
                        t_email = st.text_input("EMAIL", value=cemail if cemail else "")
                        t_source = st.selectbox("顧客來源 (廣告追蹤)", SOURCES_LIST, index=get_source_idx(csource))

                    t_addr = st.text_input("常用收件地址 (本人) *", value=caddr if caddr else "")
                    t_pref = st.text_input("飲食偏好 / 客戶備註", value=cpref if cpref else "")

                    st.markdown("##### 🎁 送禮 / 第二收件人")
                    tr2_1, tr2_2 = st.columns(2)
                    with tr2_1:
                        t_r2_name = st.text_input("第二收件人姓名 (送禮對象)", value=cr2_name if cr2_name else "")
                    with tr2_2:
                        t_r2_phone = st.text_input("第二收件人手機 (送禮電話)", value=cr2_phone if cr2_phone else "")
                    t_r2_addr = st.text_input("第二收件地址 (送禮地址)", value=cr2_addr if cr2_addr else "")

                    t_save_btn = st.form_submit_button("💾 儲存並更新客戶基本資料")
                    if t_save_btn:
                        update_customer_db(cid, t_code, t_name, t_gender, t_id_card, t_phone, t_phone_bak, t_tel, t_email, t_addr, t_r2_name, t_r2_phone, t_r2_addr, t_pref, t_source)
                        st.success("✅ 客戶資料已同步更新！")
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
            st.write("**⏳ 歷史訂單與購買軌跡（支援修改或刪除）：**")
            render_editable_orders(h_df, "tab3")
    else:
        st.info("⚠️ 查無符合條件的客戶。")

# ==========================================
# TAB 4: 客戶名冊總表
# ==========================================
with tab4:
    st.subheader("📊 客戶名冊總表")
    
    col_filter, _ = st.columns([3, 1])
    with col_filter:
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
            (SELECT STRING_AGG(order_date::text || ' (' || channel || '): ' || product || ' $' || amount::text, ' | ' ORDER BY order_date DESC) FROM orders WHERE customer_id = c.customer_id) AS "歷史訂購紀錄明細"
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id
        ORDER BY c.customer_code DESC, c.customer_id DESC
    """)

    if not df_all.empty:
        if tab4_search:
            search_upper = tab4_search.upper()
            df_filtered = df_all[
                df_all["姓名"].str.contains(tab4_search, na=False) | 
                df_all["主要手機"].str.contains(tab4_search, na=False) |
                df_all["客戶代號"].str.contains(search_upper, na=False)
            ]
        else:
            df_filtered = df_all

        df_filtered_idx = df_filtered.set_index("customer_id")
        display_df = df_filtered_idx.drop(columns=["歷史訂購紀錄明細"])

        st.markdown("💡 **小提示：可以點擊欄位進行編輯。修改完畢，務必點擊下方的「儲存」按鈕。**")
        
        edited_df = st.data_editor(
            display_df, 
            use_container_width=True,
            hide_index=True,
            disabled=["客戶代號", "最後購買管道", "總購買次數", "歷史消費金額", "最後購買日"]
        )
        
        if st.button("💾 儲存", type="primary"):
            changes_count = 0
            for cid, row in edited_df.iterrows():
                orig_row = display_df.loc[cid]
                if not row.equals(orig_row):
                    execute_query("""
                        UPDATE customers 
                        SET name = :name, customer_source = :src, gender = :gender, 
                            phone = :phone, phone_backup = :phone_bak, tel = :tel, address = :addr
                        WHERE customer_id = :cid
                    """, {
                        "name": row["姓名"], "src": row["顧客來源"], "gender": row["性別"],
                        "phone": row["主要手機"], "phone_bak": row["備用手機"], "tel": row["市話"],
                        "addr": row["常用地址"], "cid": cid
                    })
                    changes_count += 1
            
            if changes_count > 0:
                st.cache_data.clear()
                st.success(f"✅ 成功將 {changes_count} 位客戶的修改同步至資料庫！請按 F5 重新整理網頁。")
            else:
                st.info("尚未偵測到任何修改。")

        st.markdown("---")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtered.drop(columns=["customer_id"]).to_excel(writer, index=False, sheet_name='客戶名冊')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 匯出顯示的名冊與全部訂購歷史 (XLSX Excel檔)",
            data=excel_data,
            file_name="有其田_客戶完整名冊.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
    st.subheader("📥 智慧匯入中心（支援舊會員名單與官網訂單報表）")
    st.info("💡 系統會自動辨識您上傳的 Excel 格式（支援舊客建檔名單 或 官網訂單報表）。上傳官網報表時，會自動去除多商品拆列的小計重複，精準抓取「訂單編號、訂單金額、訂購商品」寫入對應會員！")
    
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
                max_crm_num = 8759

                for _, r in existing_cust_df.iterrows():
                    cid = int(r['customer_id'])
                    c_code = str(r['customer_code']).strip() if pd.notna(r['customer_code']) else ""
                    c_phone = str(r['phone']).strip() if pd.notna(r['phone']) else ""
                    if c_code:
                        code_to_id[c_code] = cid
                        m = re.search(r"CRM(\d+)", c_code)
                        if m and int(m.group(1)) > max_crm_num:
                            max_crm_num = int(m.group(1))
                    if c_phone:
                        phone_to_id[c_phone] = cid

                # 讀取現有訂單代號/編號，防止重複匯入
                existing_orders_df = read_query("SELECT customer_id, raw_date_code FROM orders WHERE raw_date_code != ''")
                existing_order_set = set(zip(existing_orders_df['customer_id'].astype(int), existing_orders_df['raw_date_code'].astype(str)))

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cust_inserts = []
                order_tasks = []

                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=str)
                    
                    # 🔍 自動判斷是否為「官網訂單報表格式」
                    columns_str = "".join(df.columns)
                    is_official_web_report = "訂單編號" in columns_str and "訂單金額" in columns_str

                    if is_official_web_report:
                        status.info("⚡ 偵測到【官網訂單報表】格式，正在進行智慧去重與欄位對應...")
                        
                        # 依「訂單編號」分群，確保買多樣商品產生的多列能被正確合併去重
                        # 每一筆訂單取第一列的時間、名稱、手機、訂單金額、訂購商品
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

                            # 萃取訂購日期
                            match_date = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", time_str)
                            order_date = match_date.group(1).replace("/", "-") if match_date else str(date.today())

                            # 將同訂單編號的所有商品串接起來
                            products = [str(p).strip() for p in group.get("訂購商品", []) if pd.notna(p) and str(p).strip()]
                            product_desc = " / ".join(products) if products else "官網訂購品項"

                            if not name or not phone:
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
                                max_crm_num += 1
                                cust_code = f"CRM{max_crm_num:06d}"

                                cust_inserts.append({
                                    "customer_code": cust_code, "name": name, "gender": "女", "id_card": "",
                                    "phone": p1, "phone_backup": "", "tel": "", "address": "官網匯入地址", "created_at": now_str,
                                    "customer_source": "官網"
                                })
                                if p1:
                                    phone_to_id[p1] = cust_code
                                code_to_id[cust_code] = cust_code

                                order_tasks.append({
                                    "target": cust_code,
                                    "channel": ord_item["channel"],
                                    "product": ord_item["product"],
                                    "amount": ord_item["amount"],
                                    "order_date": ord_item["order_date"],
                                    "raw_date_code": r_code,
                                    "status": "已結案"
                                })

                    else:
                        # 舊版一般會員名單格式
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
                                    max_crm_num += 1
                                    cust_code = f"CRM{max_crm_num:06d}"

                                cust_inserts.append({
                                    "customer_code": cust_code, "name": name, "gender": gender, "id_card": id_card,
                                    "phone": p1, "phone_backup": p2, "tel": t1, "address": addr, "created_at": now_str,
                                    "customer_source": "未指定 / 自然流量"
                                })
                                if p1:
                                    phone_to_id[p1] = cust_code
                                code_to_id[cust_code] = cust_code

                                for o_chan, o_date, r_code in row_orders:
                                    order_tasks.append({
                                        "target": cust_code,
                                        "channel": o_chan,
                                        "product": "常態訂購品項",
                                        "amount": 0,
                                        "order_date": o_date,
                                        "raw_date_code": r_code,
                                        "status": "歷史完成"
                                    })

                bar.progress(50)
                status.info(f"⚡ [2/3] 正在安全寫入 {len(cust_inserts)} 位全新客戶...")

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
                            "order_notes": f"代號/單號: {task['raw_date_code']}"
                        })

                if final_orders:
                    orders_df = pd.DataFrame(final_orders)
                    orders_df = orders_df.drop_duplicates(subset=["customer_id", "raw_date_code"])
                    orders_df.to_sql("orders", engine, if_exists="append", index=False, method="multi", chunksize=1000)

                st.cache_data.clear()

                bar.progress(100)
                status.empty()
                st.success(f"🎉 智慧匯入大成功！成功新增 **{len(cust_inserts)}** 位新會員，並精準寫入 **{len(final_orders)}** 筆訂單記錄（已自動排除重複小計與商品列）！")
        except Exception as e:
            st.error(f"匯入錯誤：{e}")
