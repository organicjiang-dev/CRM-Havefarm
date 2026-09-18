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

# 🔥 訂單來源選項
ORDER_SOURCES = [
    "未指定 / 自然流量", 
    "FB 再行銷", 
    "FB 新客", 
    "FB 自然貼文", 
    "Google 關鍵字搜尋", 
    "Google PMAX 廣告", 
    "Google Demand Gen", 
    "LINE 訂購", 
    "廣播", 
    "簡訊", 
    "其他"
]

# 🚨 採用真空壓縮 CSS，字體全面加粗 (Bold) 與按鈕優化設計
st.markdown("""
<style>
/* 🌟 1. 字體全面加粗，高度放大，達到極致舒適大格子 */
html, body, [class*="css"], p, span, div { font-size: 20px !important; font-weight: 700 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", sans-serif !important; color: #2d3748 !important; }

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
            with st.form("login_form"):
                user_input = st.text_input("客服人員帳號", placeholder="請輸入帳號").strip()
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
                                st.success(f"✅ 帳密正確！驗證碼已發送至信箱。")
                                st.rerun()
                            else:
                                st.session_state.pwd_verified = False
                    else:
                        st.error("❌ 帳號或密碼錯誤，請重新輸入！")
            return False
        else:
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

# ==================== 以下為系統主要功能 ====================

@st.cache_resource
def get_db_engine():
    db_url = st.secrets["SUPABASE_DB_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    connect_args = {}
    if "sslmode" not in db_url:
        connect_args["sslmode"] = "require"
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

# 🚀 全快取記憶體架構
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
    return read_query("""
        SELECT order_id, customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes
        FROM orders
        ORDER BY order_date DESC, order_id DESC
    """)

def get_next_crm_code():
    df = get_cached_customers_df()
    codes = df['customer_code'].dropna().astype(str)
    nums = codes.str.extract(r'CRM(\d+)')[0].dropna().astype(int)
    if not nums.empty:
        return f"CRM{nums.max() + 1:06d}"
    return "CRM008760"

def clean_phone(p):
    if pd.isna(p) or not p: return ""
    s = str(p).strip().replace(".0", "")
    s = re.sub(r"[^\d+]", "", s)
    if s.startswith("+886"): s = "0" + s[4:]
    elif s.startswith("886"): s = "0" + s[3:]
    elif len(s) == 9 and s.startswith("9"): s = "0" + s
    return s

def search_customers_fast(query_str):
    q = str(query_str).strip()
    if not q: return []
    df = get_cached_customers_df()
    if df.empty: return []
    q_lower = q.lower()
    q_clean = clean_phone(q)
    mask = (df['name'].str.lower().str.contains(q_lower, na=False) | df['customer_code'].str.lower().str.contains(q_lower, na=False))
    if q_clean and len(q_clean) >= 3:
        mask = mask | (df['phone'].str.contains(q_clean, na=False) | df['phone_backup'].str.contains(q_clean, na=False) | df['recipient2_phone'].str.contains(q_clean, na=False) | df['tel'].str.contains(q_clean, na=False))
    return df[mask].to_records(index=False).tolist()

def get_customer_by_id(cid):
    df = get_cached_customers_df()
    target = df[df['customer_id'] == cid]
    return target.iloc[0].to_dict() if not target.empty else None

def get_customer_history(customer_id):
    df = get_cached_orders_df()
    return df[df['customer_id'] == customer_id]

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
    st.cache_data.clear()

def render_editable_orders(history_df, prefix_key):
    if history_df.empty:
        st.write("目前尚無訂單紀錄。")
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
                        execute_query("UPDATE orders SET channel = :chan, product = :prod, amount = :amt, order_date = :odate, status = :source, order_notes = :notes WHERE order_id = :oid", 
                                      {"chan": o_chan, "prod": o_prod, "amt": o_amt, "odate": o_date, "source": o_source, "notes": o_notes, "oid": oid})
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
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.pwd_verified = False
        st.session_state.auth_code = ""
        st.rerun()

if "jump_search_query" not in st.session_state:
    st.session_state.jump_search_query = ""

tab1, tab2, tab3, tab4, tab7, tab6, tab5 = st.tabs([
    "🔍 舊客速查與編輯", "🆕 建立新名單", "👤 歷史訂購紀錄", "📊 客戶名冊總表", "🎯 智慧回購清單", "📅 報表與匯出", "📥 匯入中心"
])

# ==========================================
# TAB 1: 舊客戶速查與編輯
# ==========================================
with tab1:
    col_left_spacer, col_main_center, col_right_spacer = st.columns([1, 8, 1])
    
    with col_main_center:
        st.markdown("### 🔍 客戶資料查詢")
        
        default_search = st.session_state.jump_search_query
        if default_search:
            st.session_state.jump_search_query = ""

        search_query = st.text_input(
            "輸入 姓名 / 手機 / 統編 / 代號 進行速查：", 
            value=default_search,
            placeholder="例：蔡汶容、0912345678",
            key="accurate_cust_search"
        ).strip()

        if search_query:
            matched_custs = search_customers_fast(search_query)
            if not matched_custs:
                st.warning(f"⚠️ 查無此人！請至【🆕 建立新名單】建檔。")
            else:
                if len(matched_custs) > 1:
                    cust_options = {f"[{c[1] if str(c[1]).strip() else '待查'}] {c[2]} ({c[5]})": c[0] for c in matched_custs}
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
                    csource = cust.get('customer_source') or "未指定 / 自然流量"

                    history_df = get_customer_history(cid)
                    total_orders = len(history_df)
                    total_spent = history_df['amount'].sum() if total_orders > 0 else 0

                    m1, m2 = st.columns(2)
                    m1.metric("累積購買次數", f"{total_orders} 次")
                    m2.metric("累積消費金額", f"NT$ {total_spent:,}")

                    with st.form(key=f"edit_cust_form_tab1_{cid}"):
                        st.markdown("### ✏️ 基本資料編輯")
                        
                        # Row 1 (代號 / 統編)
                        c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                        c1.markdown('<div class="lbl">客戶代號</div>', unsafe_allow_html=True)
                        edit_code = c2.text_input("客戶代號", value=ccode, label_visibility="collapsed")
                        c3.markdown('<div class="lbl">統編</div>', unsafe_allow_html=True)
                        edit_id_card = c4.text_input("統編", value=cid_card, label_visibility="collapsed")
                        
                        # Row 2 (姓名 / 性別)
                        c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                        c1.markdown('<div class="lbl">姓名 *</div>', unsafe_allow_html=True)
                        edit_name = c2.text_input("姓名", value=cname, label_visibility="collapsed")
                        c3.markdown('<div class="lbl">性別</div>', unsafe_allow_html=True)
                        edit_gender = c4.selectbox("性別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2), label_visibility="collapsed")
                        
                        # Row 3 (手機 1 / 手機 2)
                        c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                        c1.markdown('<div class="lbl">手機 1 *</div>', unsafe_allow_html=True)
                        edit_phone = c2.text_input("手機 1", value=cphone, label_visibility="collapsed")
                        c3.markdown('<div class="lbl">手機 2</div>', unsafe_allow_html=True)
                        edit_phone_bak = c4.text_input("手機 2", value=cphone_bak, label_visibility="collapsed")
                        
                        # Row 4 (市話 1 / 市話 2)
                        c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                        c1.markdown('<div class="lbl">市話 1</div>', unsafe_allow_html=True)
                        
                        old_tel1, old_tel2 = ctel, ""
                        if ctel and "/" in ctel:
                            parts = ctel.split("/")
                            old_tel1 = parts[0].strip()
                            old_tel2 = parts[1].strip() if len(parts) > 1 else ""

                        edit_tel = c2.text_input("市話 1", value=old_tel1, label_visibility="collapsed")
                        c3.markdown('<div class="lbl">市話 2</div>', unsafe_allow_html=True)
                        edit_tel2 = c4.text_input("市話 2", value=old_tel2, label_visibility="collapsed", placeholder="選填")

                        # Row 5 (地址)
                        ca1, ca2 = st.columns([1.5, 8.5])
                        ca1.markdown('<div class="lbl">地址 *</div>', unsafe_allow_html=True)
                        edit_addr = ca2.text_input("地址", value=caddr, label_visibility="collapsed")
                        
                        # Row 6 (第二地址)
                        ca1, ca2 = st.columns([1.5, 8.5])
                        ca1.markdown('<div class="lbl">第二地址</div>', unsafe_allow_html=True)
                        edit_r2_addr = ca2.text_input("第二地址", value=cr2_addr, label_visibility="collapsed")
                        
                        # Row 7 (收件人2)
                        c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                        c1.markdown('<div class="lbl">收件人2姓名</div>', unsafe_allow_html=True)
                        edit_r2_name = c2.text_input("收件人2姓名", value=cr2_name, label_visibility="collapsed")
                        c3.markdown('<div class="lbl">收件人2手機</div>', unsafe_allow_html=True)
                        edit_r2_phone = c4.text_input("收件人2手機", value=cr2_phone, label_visibility="collapsed")

                        # Row 8 (備註)
                        cn1, cn2 = st.columns([1.5, 8.5])
                        cn1.markdown('<div class="lbl" style="height:160px;">備註</div>', unsafe_allow_html=True)
                        edit_pref = cn2.text_area("備註", value=cpref, label_visibility="collapsed")

                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        btn_col1, btn_col2, btn_col3 = st.columns([3, 4, 3])
                        with btn_col2:
                            save_cust_btn = st.form_submit_button("💾 儲存資料", type="primary", use_container_width=True)

                        if save_cust_btn:
                            if not edit_name or not edit_phone or not edit_addr:
                                st.error("姓名、手機 1 與地址不可為空！")
                            else:
                                final_tel = edit_tel.strip()
                                if edit_tel2.strip():
                                    final_tel += f" / {edit_tel2.strip()}"
                                update_customer_db(cid, edit_code, edit_name, edit_gender, edit_id_card, edit_phone, edit_phone_bak, final_tel, cemail, edit_addr, edit_r2_name, edit_r2_phone, edit_r2_addr, edit_pref, csource)
                                st.success(f"✅ 更新成功！")
                                st.rerun()

                    st.markdown("---")
                    st.markdown("### 📦 新增訂單")
                    with st.form(key=f"add_order_for_tab1_{cid}", clear_on_submit=True):
                        oc1, oc2, oc3 = st.columns(3)
                        with oc1:
                            new_order_chan = st.selectbox("購買管道 *", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])
                            new_order_date = st.date_input("訂購日期 *", value=datetime.today())
                        with oc2:
                            new_order_prod = st.text_input("訂購商品名稱與規格 *", placeholder="例：有機三色藜麥片 3罐組")
                            new_order_amt = st.number_input("訂單金額 (NT$)", min_value=0, step=50, value=0)
                        with oc3:
                            new_order_source = st.selectbox("訂單來源", ORDER_SOURCES)
                            new_order_notes = st.text_input("本次訂單備註")

                        st.markdown("<br>", unsafe_allow_html=True)
                        btn_c1, btn_c2, btn_c3 = st.columns([3, 4, 3])
                        with btn_c2:
                            add_order_btn = st.form_submit_button("➕ 建立這筆新訂單", type="primary", use_container_width=True)
                            
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
                                    "status": new_order_source, "notes": new_order_notes
                                })
                                st.cache_data.clear() 
                                st.success(f"🎉 已成功新增訂單！")
                                st.rerun()

                    st.markdown("---")
                    st.markdown("### 📜 歷史購買紀錄")
                    render_editable_orders(history_df, "tab1")

# ==========================================
# TAB 2: 建立全新會員名單
# ==========================================
with tab2:
    col_left_spacer_t2, col_main_center_t2, col_right_spacer_t2 = st.columns([1, 8, 1])
    with col_main_center_t2:
        st.markdown("### 🆕 建立全新會員名單")
        auto_code = get_next_crm_code()
        
        with st.form("create_new_customer_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
            c1.markdown('<div class="lbl">客戶代號</div>', unsafe_allow_html=True)
            n_code = c2.text_input("客戶代號", value=auto_code, label_visibility="collapsed")
            c3.markdown('<div class="lbl">統編</div>', unsafe_allow_html=True)
            n_id_card = c4.text_input("統編", label_visibility="collapsed")
            
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
            c1.markdown('<div class="lbl">姓名 *</div>', unsafe_allow_html=True)
            n_name = c2.text_input("姓名", label_visibility="collapsed")
            c3.markdown('<div class="lbl">性別</div>', unsafe_allow_html=True)
            n_gender = c4.selectbox("性別", ["女", "男", "其他"], label_visibility="collapsed")
            
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
            c1.markdown('<div class="lbl">手機 1 *</div>', unsafe_allow_html=True)
            n_phone = c2.text_input("手機 1", label_visibility="collapsed")
            c3.markdown('<div class="lbl">手機 2</div>', unsafe_allow_html=True)
            n_phone_bak = c4.text_input("手機 2", label_visibility="collapsed")
            
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
            c1.markdown('<div class="lbl">市話 1</div>', unsafe_allow_html=True)
            n_tel = c2.text_input("市話 1", label_visibility="collapsed")
            c3.markdown('<div class="lbl">市話 2</div>', unsafe_allow_html=True)
            n_tel2 = c4.text_input("市話 2", label_visibility="collapsed", placeholder="選填")

            ca1, ca2 = st.columns([1.5, 8.5])
            ca1.markdown('<div class="lbl">地址 *</div>', unsafe_allow_html=True)
            n_addr = ca2.text_input("地址", label_visibility="collapsed")
            
            ca1, ca2 = st.columns([1.5, 8.5])
            ca1.markdown('<div class="lbl">第二地址</div>', unsafe_allow_html=True)
            n_r2_addr = ca2.text_input("第二地址", label_visibility="collapsed")
            
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
            c1.markdown('<div class="lbl">收件人2姓名</div>', unsafe_allow_html=True)
            n_r2_name = c2.text_input("收件人2姓名", label_visibility="collapsed")
            c3.markdown('<div class="lbl">收件人2手機</div>', unsafe_allow_html=True)
            n_r2_phone = c4.text_input("收件人2手機", label_visibility="collapsed")

            cn1, cn2 = st.columns([1.5, 8.5])
            cn1.markdown('<div class="lbl" style="height:160px;">備註</div>', unsafe_allow_html=True)
            n_pref = cn2.text_area("備註", label_visibility="collapsed")

            st.markdown("---")
            st.markdown("### 📦 首次訂購品項（選填）")
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                n_prod = st.text_input("訂購商品名稱", placeholder="例：有機三色藜麥片 3罐組")
                n_channel = st.selectbox("首次接觸管道", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])
            with fc2:
                n_amt = st.number_input("訂單金額", min_value=0, step=50, value=0)
            with fc3:
                n_date = st.date_input("訂購日期", value=datetime.today())
                n_source = st.selectbox("訂單來源", ORDER_SOURCES)

            st.markdown("<br>", unsafe_allow_html=True)
            btn_c1, btn_c2, btn_c3 = st.columns([3, 4, 3])
            with btn_c2:
                submit_new_cust = st.form_submit_button("🚀 儲存資料", type="primary", use_container_width=True)

            if submit_new_cust:
                clean_np = clean_phone(n_phone)
                if not n_name or not clean_np or not n_addr:
                    st.error("請填寫『姓名』、『手機 1』與『地址』！")
                else:
                    final_ntel = n_tel.strip()
                    if n_tel2.strip(): final_ntel += f" / {n_tel2.strip()}"
                        
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    res = execute_query("""
                        INSERT INTO customers (customer_id, customer_code, name, gender, id_card, phone, phone_backup, tel, email, 
                                               address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at, customer_source)
                        VALUES (DEFAULT, :code, :name, :gender, :id_card, :phone, :phone_bak, :tel, '', 
                                :addr, :r2_name, :r2_phone, :r2_addr, :pref, :created_at, '未指定 / 自然流量')
                        RETURNING customer_id
                    """, {
                        "code": n_code, "name": n_name, "gender": n_gender, "id_card": n_id_card,
                        "phone": clean_np, "phone_bak": n_phone_bak, "tel": final_ntel,
                        "addr": n_addr, "r2_name": n_r2_name, "r2_phone": clean_phone(n_r2_phone),
                        "r2_addr": n_r2_addr, "pref": n_pref, "created_at": now_str
                    })
                    new_cid = res.fetchone()[0]
                    st.cache_data.clear()

                    if n_prod:
                        chan_clean = "電話訂購" if "電話" in n_channel else ("官網" if "官網" in n_channel else n_channel)
                        execute_query("""
                            INSERT INTO orders (customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes)
                            VALUES (:cid, :chan, :prod, :amt, :odate, '', :status, '')
                        """, {
                            "cid": new_cid, "chan": chan_clean, "prod": n_prod,
                            "amt": n_amt, "odate": str(n_date), "status": n_source
                        })
                        st.cache_data.clear()
                    st.success(f"🎉 成功建立新會員【{n_name}】！")
                    st.rerun()

# ==========================================
# TAB 3: 歷史訂購紀錄
# ==========================================
with tab3:
    col_left_spacer_t3, col_main_center_t3, col_right_spacer_t3 = st.columns([1, 8, 1])
    with col_main_center_t3:
        st.markdown("### 👤 歷史訂購紀錄查詢")
        t3_search = st.text_input("🔍 輸入姓名 / 手機 / 代號：", key="tab3_search").strip()

        df_cache = get_cached_customers_df()
        if t3_search:
            matched_t3 = search_customers_fast(t3_search)
            c_opts = {f"[{c[1] if str(c[1]).strip() else '待查'}] {c[2]} ({c[5]})": c[0] for c in matched_t3} if matched_t3 else {}
        else:
            c_opts = {f"[{row['customer_code']}] {row['name']} ({row['phone']})": row['customer_id'] for _, row in df_cache.iterrows()}

        if c_opts:
            sel_label = st.selectbox("選擇客戶：", list(c_opts.keys()), key="timeline_select_cust")
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

                with st.form(key=f"edit_cust_form_tab3_{cid}"):
                    st.markdown("### ✏️ 基本資料編輯")
                    
                    c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                    c1.markdown('<div class="lbl">客戶代號</div>', unsafe_allow_html=True)
                    t_code = c2.text_input("客戶代號", value=ccode, label_visibility="collapsed")
                    c3.markdown('<div class="lbl">統編</div>', unsafe_allow_html=True)
                    t_id_card = c4.text_input("統編", value=cid_card, label_visibility="collapsed")
                    
                    c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                    c1.markdown('<div class="lbl">姓名 *</div>', unsafe_allow_html=True)
                    t_name = c2.text_input("姓名", value=cname, label_visibility="collapsed")
                    c3.markdown('<div class="lbl">性別</div>', unsafe_allow_html=True)
                    t_gender = c4.selectbox("性別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2), label_visibility="collapsed")
                    
                    c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                    c1.markdown('<div class="lbl">手機 1 *</div>', unsafe_allow_html=True)
                    t_phone = c2.text_input("手機 1", value=cphone, label_visibility="collapsed")
                    c3.markdown('<div class="lbl">手機 2</div>', unsafe_allow_html=True)
                    t_phone_bak = c4.text_input("手機 2", value=cphone_bak, label_visibility="collapsed")
                    
                    c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                    c1.markdown('<div class="lbl">市話 1</div>', unsafe_allow_html=True)
                    
                    old_tel1, old_tel2 = ctel, ""
                    if ctel and "/" in ctel:
                        parts = ctel.split("/")
                        old_tel1 = parts[0].strip()
                        old_tel2 = parts[1].strip() if len(parts) > 1 else ""

                    t_tel = c2.text_input("市話 1", value=old_tel1, label_visibility="collapsed")
                    c3.markdown('<div class="lbl">市話 2</div>', unsafe_allow_html=True)
                    t_tel2 = c4.text_input("市話 2", value=old_tel2, label_visibility="collapsed", placeholder="選填")

                    ca1, ca2 = st.columns([1.5, 8.5])
                    ca1.markdown('<div class="lbl">地址 *</div>', unsafe_allow_html=True)
                    t_addr = ca2.text_input("地址", value=caddr, label_visibility="collapsed")
                    
                    ca1, ca2 = st.columns([1.5, 8.5])
                    ca1.markdown('<div class="lbl">第二地址</div>', unsafe_allow_html=True)
                    t_r2_addr = ca2.text_input("第二地址", value=cr2_addr, label_visibility="collapsed")
                    
                    c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 3.5])
                    c1.markdown('<div class="lbl">收件人2姓名</div>', unsafe_allow_html=True)
                    t_r2_name = c2.text_input("收件人2姓名", value=cr2_name, label_visibility="collapsed")
                    c3.markdown('<div class="lbl">收件人2手機</div>', unsafe_allow_html=True)
                    t_r2_phone = c4.text_input("收件人2手機", value=cr2_phone, label_visibility="collapsed")

                    cn1, cn2 = st.columns([1.5, 8.5])
                    cn1.markdown('<div class="lbl" style="height:160px;">備註</div>', unsafe_allow_html=True)
                    t_pref = cn2.text_area("備註", value=cpref, label_visibility="collapsed")

                    st.markdown("<br>", unsafe_allow_html=True)
                    btn_c1, btn_c2, btn_c3 = st.columns([3, 4, 3])
                    with btn_c2:
                        t_save_btn = st.form_submit_button("💾 儲存資料", type="primary", use_container_width=True)

                    if t_save_btn:
                        final_tel_t3 = t_tel.strip()
                        if t_tel2.strip(): final_tel_t3 += f" / {t_tel2.strip()}"
                        update_customer_db(cid, t_code, t_name, t_gender, t_id_card, t_phone, t_phone_bak, final_tel_t3, cemail, t_addr, t_r2_name, t_r2_phone, t_r2_addr, t_pref, csource)
                        st.success("✅ 更新成功！")
                        st.rerun()

                st.markdown("---")
                st.markdown("### 📦 新增訂單")
                with st.form(key=f"add_order_for_tab3_{cid}", clear_on_submit=True):
                    oc1, oc2, oc3 = st.columns(3)
                    with oc1:
                        new_order_chan = st.selectbox("購買管道 *", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])
                        new_order_date = st.date_input("訂購日期 *", value=datetime.today())
                    with oc2:
                        new_order_prod = st.text_input("訂購商品名稱與規格 *", placeholder="例：有機三色藜麥片 3罐組")
                        new_order_amt = st.number_input("訂單金額 (NT$)", min_value=0, step=50, value=0)
                    with oc3:
                        new_order_source = st.selectbox("訂單來源", ORDER_SOURCES)
                        new_order_notes = st.text_input("本次訂單備註")

                    st.markdown("<br>", unsafe_allow_html=True)
                    btn_c1, btn_c2, btn_c3 = st.columns([3, 4, 3])
                    with btn_c2:
                        add_order_btn = st.form_submit_button("➕ 建立這筆新訂單", type="primary", use_container_width=True)
                        
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
                                "status": new_order_source, "notes": new_order_notes
                            })
                            st.cache_data.clear() 
                            st.success(f"🎉 已成功為【{cname}】新增訂單！")
                            st.rerun()

                st.markdown("---")
                st.markdown("### 📜 歷史購買紀錄")
                render_editable_orders(h_df, "tab3")
        else:
            st.info("⚠️ 查無符合條件的客戶。")

# ==========================================
# 🌟 Python 處理歷史訂單匯出格式函數
# ==========================================
def format_export_order(dstr, channel_prefix):
    if pd.isna(dstr) or not str(dstr).strip(): return ""
    try:
        d = pd.to_datetime(dstr)
        return f"{channel_prefix}{d.year - 1911}-{d.strftime('%m%d')}"
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
            c.customer_id, c.customer_code AS "客戶代號", c.name AS "姓名", c.customer_source AS "顧客來源",
            c.gender AS "性別", c.phone AS "主要手機", c.phone_backup AS "備用手機", c.tel AS "市話",
            c.address AS "常用地址",
            (SELECT channel FROM orders WHERE customer_id = c.customer_id ORDER BY order_date DESC LIMIT 1) AS "最後購買管道",
            COUNT(o.order_id) AS "總購買次數", COALESCE(SUM(o.amount), 0) AS "歷史消費金額", MAX(o.order_date) AS "最後購買日",
            (SELECT STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) FROM orders WHERE customer_id = c.customer_id) AS "所有訂購明細",
            (SELECT STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) FROM orders WHERE customer_id = c.customer_id AND channel LIKE '%官網%') AS "官網訂單",
            (SELECT STRING_AGG(order_date::text, '|||' ORDER BY order_date ASC) FROM orders WHERE customer_id = c.customer_id AND (channel LIKE '%電話%' OR channel LIKE '%廣播%')) AS "電話訂單"
        FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id ORDER BY c.customer_code DESC, c.customer_id DESC
    """)

    if not df_all.empty:
        df_filtered = df_all
        if show_pending_only: df_filtered = df_filtered[(df_filtered["客戶代號"].isna()) | (df_filtered["客戶代號"].str.strip() == "")]
        if tab4_search:
            search_upper = tab4_search.upper()
            df_filtered = df_filtered[df_filtered["姓名"].str.contains(tab4_search, na=False) | df_filtered["主要手機"].str.contains(tab4_search, na=False) | df_filtered["客戶代號"].str.contains(search_upper, na=False)]

        st.markdown("💡 **小提示：此總表為純檢視模式，載入最為快速。**")
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

        st.download_button(label="📥 匯出精準分類名冊", data=output.getvalue(), file_name="有其田_客戶完整名冊.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    else: st.info("尚無客戶資料。")

# ==========================================
# TAB 7: 🎯 智慧回購清單與電銷戰情室
# ==========================================
with tab7:
    st.subheader("🎯 智慧回購清單與電銷追蹤戰情室")
    
    st.markdown("#### 🔍 進階撈單：精準行銷與自訂沉睡客篩選")
    st.info("💡 設定「最後購買日」區間，找出特定期間流失的客人。例如：設定 2024/01/01 ~ 2024/12/31，代表「最後一次買是在 2024 年，之後就再也沒買過」的客人。")
    
    with st.form("advanced_filter_form"):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_start = st.date_input("最後購買日 (起)", value=date.today() - timedelta(days=365))
        with col_f2:
            filter_end = st.date_input("最後購買日 (迄)", value=date.today() - timedelta(days=180))
        with col_f3:
            min_amount = st.number_input("歷史總消費金額大於 (NT$)", min_value=0, value=1000, step=500)
            
        st.markdown("<br>", unsafe_allow_html=True)
        btn_f1, btn_f2, btn_f3 = st.columns([3, 4, 3])
        with btn_f2:
            filter_btn = st.form_submit_button("🔍 撈出精準電訪名單", type="primary", use_container_width=True)
        
    if filter_btn:
        if filter_start > filter_end:
            st.error("「起」日期不能大於「迄」日期！")
        else:
            adv_sql = """
                WITH CustomerStats AS (
                    SELECT 
                        c.customer_id,
                        c.customer_code AS "客戶代號",
                        c.name AS "姓名",
                        c.phone AS "主要手機",
                        MAX(o.order_date) AS last_purchase_date,
                        SUM(o.amount) AS total_spent,
                        COUNT(o.order_id) AS total_orders
                    FROM customers c
                    JOIN orders o ON c.customer_id = o.customer_id
                    GROUP BY c.customer_id, c.customer_code, c.name, c.phone
                )
                SELECT 
                    "客戶代號", "姓名", "主要手機", 
                    last_purchase_date AS "最後購買日",
                    total_orders AS "累積購買次數",
                    total_spent AS "歷史消費金額"
                FROM CustomerStats
                WHERE last_purchase_date >= :s_date 
                  AND last_purchase_date <= :e_date
                  AND total_spent >= :min_amt
                ORDER BY "歷史消費金額" DESC, "最後購買日" DESC
            """
            adv_df = read_query(adv_sql, {
                "s_date": str(filter_start), 
                "e_date": str(filter_end), 
                "min_amt": min_amount
            })
            
            if adv_df.empty:
                st.warning("⚠️ 查無符合條件的客戶名單。")
            else:
                st.success(f"✅ 成功撈出 **{len(adv_df)}** 位符合條件的客戶！")
                st.dataframe(adv_df, use_container_width=True, hide_index=True)
                
                adv_out = io.BytesIO()
                with pd.ExcelWriter(adv_out, engine='xlsxwriter') as w:
                    adv_df.to_excel(w, index=False, sheet_name='精準電訪名單')
                st.download_button(
                    "📥 下載此精準電訪名單 (XLSX)", 
                    adv_out.getvalue(), 
                    f"有其田_精準電訪名單_{filter_start}至{filter_end}.xlsx", 
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

    st.markdown("---")
    today_str = date.today().strftime("%Y-%m-%d")
    st.markdown("#### 🔔 今日預定再訪清單")
    followup_df = read_query("SELECT DISTINCT c.customer_id, c.customer_code, c.name, c.phone, t.next_followup_date, t.call_status, t.call_notes FROM telemarketing_logs t JOIN customers c ON t.customer_id = c.customer_id WHERE t.next_followup_date <= :today ORDER BY t.next_followup_date ASC", {"today": today_str})
    if followup_df.empty: st.info("🎉 目前沒有設定今天必須回訪的客戶！")
    else: st.dataframe(followup_df.drop(columns=["customer_id"]), use_container_width=True)

# ==========================================
# TAB 6: 期間訂單報表與電銷績效匯出
# ==========================================
with tab6:
    st.subheader("📅 期間訂單紀錄與電話行銷成效報表")
    report_type = st.radio("選擇要產生的報表類型：", ["📦 期間訂單明細報表", "📞 電話行銷漏斗與客服績效報表"], horizontal=True)
    col_d1, col_d2 = st.columns(2)
    with col_d1: start_date = st.date_input("起始日期", value=date.today().replace(day=1))
    with col_d2: end_date = st.date_input("結束日期", value=date.today())

    if st.button("📊 產生並下載報表"):
        if start_date > end_date: st.error("起始日期不能大於結束日期！")
        else:
            if report_type == "📦 期間訂單明細報表":
                report_df = read_query("SELECT o.order_date AS \"訂購日期\", c.customer_code AS \"客戶代號\", c.name AS \"客戶姓名\", c.phone AS \"手機號碼\", c.customer_source AS \"顧客來源\", o.product AS \"商品名稱\", o.amount AS \"訂單金額\", o.channel AS \"購買管道\", o.status AS \"訂單來源\", o.order_notes AS \"訂單備註\" FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_date >= :s_date AND o.order_date <= :e_date ORDER BY o.order_date DESC, o.order_id DESC", {"s_date": str(start_date), "e_date": str(end_date)})
                if report_df.empty: st.warning("⚠️ 此區間內無訂單紀錄。")
                else:
                    st.success(f"✅ 成功撈取 **{len(report_df)}** 筆訂單，總金額：NT$ {report_df['訂單金額'].sum():,}")
                    st.dataframe(report_df, use_container_width=True)
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as w: report_df.to_excel(w, index=False, sheet_name='訂單報表')
                    st.download_button("📥 下載訂單明細 (XLSX)", out.getvalue(), f"有其田_訂單報表_{start_date}至{end_date}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                tele_df = read_query("SELECT agent_name AS \"客服專員\", call_status AS \"撥打狀態\", COUNT(*) AS \"通話次數\" FROM telemarketing_logs WHERE created_at::date >= :s_date AND created_at::date <= :e_date GROUP BY agent_name, call_status ORDER BY agent_name, \"通話次數\" DESC", {"s_date": str(start_date), "e_date": str(end_date)})
                if tele_df.empty: st.warning("⚠️ 此區間內無電訪紀錄。")
                else:
                    st.success("✅ 成功產生電銷漏斗與專員績效統計！")
                    st.dataframe(tele_df, use_container_width=True)
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as w: tele_df.to_excel(w, index=False, sheet_name='電銷績效報表')
                    st.download_button("📥 下載電銷績效報表 (XLSX)", out.getvalue(), f"有其田_電銷績效報表_{start_date}至{end_date}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# TAB 5: 批次匯入舊名單與官網訂單報表
# ==========================================
with tab5:
    col_left_spacer_t5, col_main_center_t5, col_right_spacer_t5 = st.columns([1, 8, 1])
    with col_main_center_t5:
        st.subheader("📥 智慧匯入中心")
        uploaded_file = st.file_uploader("上傳 Excel 檔案（.xlsx）", type=["xlsx", "xls"], key="excel_uploader_tab5")

        if uploaded_file is not None:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                if st.button("🚀 確認並開始智慧增量匯入", type="primary"):
                    bar = st.progress(10)
                    status = st.empty()
                    existing_cust_df = read_query("SELECT customer_id, customer_code, phone FROM customers")
                    code_to_id, phone_to_id = {}, {}
                    for _, r in existing_cust_df.iterrows():
                        cid = int(r['customer_id'])
                        c_code = str(r['customer_code']).strip() if pd.notna(r['customer_code']) else ""
                        c_phone = str(r['phone']).strip() if pd.notna(r['phone']) else ""
                        if c_code: code_to_id[c_code] = cid
                        if c_phone: phone_to_id[c_phone] = cid

                    existing_orders_df = read_query("SELECT customer_id, raw_date_code FROM orders WHERE raw_date_code != ''")
                    existing_order_set = set(zip(existing_orders_df['customer_id'].astype(int), existing_orders_df['raw_date_code'].astype(str)))

                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cust_inserts, order_tasks = [], []

                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=str)
                        columns_str = "".join(df.columns)
                        is_official_web_report = "訂單編號" in columns_str and "訂單金額" in columns_str

                        if is_official_web_report:
                            cleaned_orders = []
                            for order_id, group in df.groupby('訂單編號'):
                                if pd.isna(order_id) or not str(order_id).strip(): continue
                                first_row = group.iloc[0]
                                name = str(first_row.get("會員名稱", "")).strip()
                                phone = clean_phone(first_row.get("會員手機號碼", ""))
                                time_str = str(first_row.get("時間", "")).strip()
                                order_amt = first_row.get("訂單金額", 0)
                                try: amt_val = float(order_amt) if pd.notna(order_amt) else 0.0
                                except: amt_val = 0.0
                                match_date = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", time_str)
                                order_date = match_date.group(1).replace("/", "-") if match_date else str(date.today())
                                products = [str(p).strip() for p in group.get("訂購商品", []) if pd.notna(p) and str(p).strip()]
                                product_desc = " / ".join(products) if products else "官網訂購品項"
                                if not phone: continue
                                cleaned_orders.append({"name": name, "phone": phone, "order_id_code": str(order_id).strip(), "order_date": order_date, "amount": amt_val, "product": product_desc, "channel": "官網"})

                            for ord_item in cleaned_orders:
                                p1, name, r_code = ord_item["phone"], ord_item["name"], ord_item["order_id_code"]
                                matched_cid = phone_to_id.get(p1)
                                if matched_cid:
                                    if (matched_cid, r_code) not in existing_order_set:
                                        order_tasks.append({"target": matched_cid, "channel": ord_item["channel"], "product": ord_item["product"], "amount": ord_item["amount"], "order_date": ord_item["order_date"], "raw_date_code": r_code, "status": "未指定 / 自然流量"})
                                        existing_order_set.add((matched_cid, r_code))
                                else:
                                    cust_code = ""
                                    cust_inserts.append({"customer_code": cust_code, "name": name, "gender": "女", "id_card": "", "phone": p1, "phone_backup": "", "tel": "", "address": "官網匯入地址", "created_at": now_str, "customer_source": "官網"})
                                    phone_to_id[p1] = p1
                                    order_tasks.append({"target": p1, "channel": ord_item["channel"], "product": ord_item["product"], "amount": ord_item["amount"], "order_date": ord_item["order_date"], "raw_date_code": r_code, "status": "未指定 / 自然流量"})
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
                                if not name or (not p1 and not t1 and not cust_code): continue

                                row_orders = []
                                for col_name, val in row.items():
                                    if pd.notna(val) and str(val).strip() != "":
                                        col_str, val_str = str(col_name), str(val).strip()
                                        if (col_str.startswith("購") and "商品" not in col_str) or col_str.startswith("Unnamed"):
                                            if (("-" in val_str) or ("/" in val_str) or val_str.upper().startswith("A") or val_str.upper().startswith("B") or val_str.upper().startswith("L")):
                                                o_chan, o_date, r_code = parse_date_code(val_str, default_channel)
                                                row_orders.append((o_chan, o_date, r_code))

                                matched_cid = code_to_id.get(cust_code) or phone_to_id.get(p1)
                                if matched_cid:
                                    for o_chan, o_date, r_code in row_orders:
                                        if (matched_cid, r_code) not in existing_order_set:
                                            order_tasks.append({"target": matched_cid, "channel": o_chan, "product": "常態訂購品項", "amount": 0, "order_date": o_date, "raw_date_code": r_code, "status": "未指定 / 自然流量"})
                                            existing_order_set.add((matched_cid, r_code))
                                else:
                                    if not cust_code: cust_code = ""
                                    cust_inserts.append({"customer_code": cust_code, "name": name, "gender": gender, "id_card": id_card, "phone": p1, "phone_backup": p2, "tel": t1, "address": addr, "created_at": now_str, "customer_source": "未指定 / 自然流量"})
                                    if p1: phone_to_id[p1] = p1 if not cust_code else cust_code
                                    if cust_code: code_to_id[cust_code] = cust_code
                                    for o_chan, o_date, r_code in row_orders:
                                        order_tasks.append({"target": cust_code if cust_code else p1, "channel": o_chan, "product": "常態訂購品項", "amount": 0, "order_date": o_date, "raw_date_code": r_code, "status": "未指定 / 自然流量"})

                    bar.progress(50)
                    engine = get_db_engine()
                    if cust_inserts:
                        pd.DataFrame(cust_inserts).to_sql("customers", engine, if_exists="append", index=False, method="multi", chunksize=500)

                    bar.progress(80)
                    fresh_cust_df = read_query("SELECT customer_id, customer_code, phone FROM customers")
                    code_map = {str(r['customer_code']).strip(): int(r['customer_id']) for _, r in fresh_cust_df.iterrows() if pd.notna(r['customer_code']) and str(r['customer_code']).strip()}
                    phone_map = {str(r['phone']).strip(): int(r['customer_id']) for _, r in fresh_cust_df.iterrows() if pd.notna(r['phone']) and str(r['phone']).strip()}

                    final_orders = []
                    for task in order_tasks:
                        target_ref = task["target"]
                        final_cid = target_ref if isinstance(target_ref, int) else (code_map.get(str(target_ref)) or phone_map.get(str(target_ref)))
                        if final_cid:
                            final_orders.append({"customer_id": int(final_cid), "channel": task["channel"], "product": task["product"], "amount": task["amount"], "order_date": task["order_date"], "raw_date_code": task["raw_date_code"], "status": task["status"], "order_notes": f"單號: {task['raw_date_code']}"})

                    if final_orders:
                        orders_df = pd.DataFrame(final_orders).drop_duplicates(subset=["customer_id", "raw_date_code"])
                        orders_df.to_sql("orders", engine, if_exists="append", index=False, method="multi", chunksize=1000)

                    st.cache_data.clear()
                    bar.progress(100)
                    st.success(f"🎉 智慧匯入大成功！")
            except Exception as e: st.error(f"匯入錯誤：{e}")
                
        st.markdown("---")
        st.subheader("🛠️ 資料庫進階維護區：修復重複歷史訂單")
        if st.button("🧹 一鍵自動清理「同日重複的 0 元佔位訂單」"):
            try:
                execute_query("""
                    DELETE FROM orders o1 WHERE o1.amount = 0 AND EXISTS (SELECT 1 FROM orders o2 WHERE o2.customer_id = o1.customer_id AND o2.order_date = o1.order_date AND o2.order_id != o1.order_id AND o2.amount > 0);
                """)
                st.success("✅ 已經成功清除了所有重複的 0 元佔位訂單！")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"清理失敗：{e}")
