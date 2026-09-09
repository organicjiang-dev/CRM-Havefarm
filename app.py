import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import io
import re

# --- 0. 設定頁面配置與「解除 Streamlit 防縮小」CSS ---
st.set_page_config(page_title="有其田 客服 CRM 系統", layout="wide", page_icon="🌾")

st.markdown("""
<style>
    /* 全域基準字體放大 */
    html, body, [class*="css"] {
        font-size: 24px !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif !important;
    }

    /* =========================================
       🔥 針對 Streamlit 原生 .stTabs 進行完美破解
       ========================================= */
    
    /* 1. 拉開按鈕之間的距離，並允許超出螢幕時可以滑動 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px !important;
        padding-bottom: 10px !important;
        overflow-x: auto !important; /* 允許分頁橫向滑動，避免被強制擠壓 */
    }

    /* 2. 設定按鈕本體的框線與背景，最重要的是 flex-shrink: 0 拒絕被系統縮小！ */
    .stTabs [data-baseweb="tab"] {
        height: 85px !important;
        padding: 0px 35px !important;
        background-color: #f7fafc !important;
        border-radius: 12px 12px 0 0 !important;
        border: 2px solid #cbd5e0 !important;
        border-bottom: none !important;
        flex-shrink: 0 !important; /* 🌟 核心魔法：拒絕系統自動縮小！ 🌟 */
    }

    /* 3. 精準鎖定文字容器，放大至 35px (最適合的巨型尺寸) */
    .stTabs [data-baseweb="tab"] [data-testid="stMarkdownContainer"] p {
        font-size: 35px !important;  
        font-weight: 900 !important;
        color: #4a5568 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 4. 被選中時的樣式 (紅線 + 紅字) */
    .stTabs [aria-selected="true"] {
        background-color: #fff5f5 !important;
        border-top: 8px solid #e53e3e !important;
    }
    .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
        color: #e53e3e !important; /* 點選時文字變紅色 */
    }
    /* ========================================= */

    /* 大標題與副標題 */
    h1 { font-size: 45px !important; font-weight: 900 !important; margin-bottom: 24px !important; }
    h2, h3 { font-size: 34px !important; font-weight: 800 !important; margin-top: 20px !important; margin-bottom: 16px !important; }
    h4, h5 { font-size: 28px !important; font-weight: 700 !important; margin-top: 16px !important; color: #2b6cb0 !important; }

    /* 輸入欄位標籤文字 (Label) */
    label, label p, [data-testid="stWidgetLabel"] p {
        font-size: 26px !important;
        font-weight: 900 !important;
        color: #1a1a1a !important;
        margin-bottom: 12px !important;
    }

    /* 所有輸入框、下拉選單格子「極致加高加大」 */
    input[type="text"], input[type="password"], input[type="number"], select, div[data-baseweb="select"] > div {
        font-size: 26px !important;
        min-height: 70px !important;
        border-radius: 12px !important;
        border: 2px solid #718096 !important;
        padding: 12px 20px !important;
        background-color: #ffffff !important;
        font-weight: 700 !important;
        color: #1a202c !important;
    }
    
    /* 日期選擇器專屬高度 */
    div[data-baseweb="input"] {
        min-height: 70px !important;
    }

    /* 下拉選單內部選項字體 */
    div[data-baseweb="select"] span {
        font-size: 26px !important;
        font-weight: 700 !important;
    }

    /* 多行備註文字框加大 */
    textarea {
        font-size: 26px !important;
        min-height: 140px !important;
        line-height: 1.6 !important;
        border: 2px solid #718096 !important;
    }

    /* 表單按鈕加大 */
    .stButton > button {
        min-height: 72px !important;
        font-size: 28px !important;
        font-weight: 900 !important;
        border-radius: 12px !important;
        padding: 0 40px !important;
        margin-top: 14px !important;
        border: 2px solid #3182ce !important;
    }

    /* 關鍵數據指標卡片 (Metrics) */
    [data-testid="stMetricValue"] {
        font-size: 46px !important;
        font-weight: 900 !important;
        color: #2b6cb0 !important;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 26px !important;
        font-weight: 800 !important;
    }

    /* 展開摺疊面板 (Expander) 標題加大 */
    details summary p, details summary span {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #2c5282 !important;
    }

    /* 表格字體放大 */
    div[data-testid="stDataFrame"] {
        font-size: 22px !important;
    }

    div[data-testid="column"] { padding: 0 16px !important; }
    hr { margin: 36px 0 !important; border: 0 !important; border-top: 3px solid #cbd5e0 !important; }
</style>
""", unsafe_allow_html=True)

# --- 1. 客服人員帳號密碼設定 (安全升級：從雲端金鑰讀取) ---
AUTH_USERS = st.secrets["crm_users"]

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if not st.session_state.logged_in:
        col_space1, col_login, col_space2 = st.columns([1, 2, 1])
        with col_login:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("## 🌾 有其田 客服系統 - 登入驗證")
            st.info("🔒 為保護客戶個資安全，請輸入內部客服人員帳號與密碼以進入系統。")

            with st.form("login_form"):
                user_input = st.text_input("客服人員帳號", placeholder="請輸入帳號（例如: admin 或 service）").strip()
                pass_input = st.text_input("登入密碼", type="password", placeholder="請輸入密碼").strip()
                login_btn = st.form_submit_button("🔐 登入系統")

                if login_btn:
                    if user_input in AUTH_USERS and AUTH_USERS[user_input] == pass_input:
                        st.session_state.logged_in = True
                        st.session_state.username = user_input
                        st.success("✅ 驗證成功，正在進入系統...")
                        st.rerun()
                    else:
                        st.error("❌ 帳號或密碼錯誤，請重新輸入！")
        return False
    return True

if not check_login():
    st.stop()

with st.sidebar:
    st.markdown(f"### 👤 目前使用者：`:blue[{st.session_state.username}]`")
    st.caption("連線狀態：🟢 Supabase 雲端資料庫已加密連線")
    if st.button("🚪 登出系統"):
        st.session_state.logged_in = False
        st.session_state.username = ""
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

# --- 3. 輔助轉換與精準搜尋 ---
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
    df = read_query("SELECT customer_code FROM customers WHERE customer_code LIKE 'CRM%'")
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

def search_customers_accurate(query_str):
    q = str(query_str).strip()
    if not q:
        return []
    clean_q = clean_phone(q)
    
    conditions = ["name LIKE :q_name"]
    params = {"q_name": f"%{q}%"}

    if q.upper().startswith("CRM"):
        conditions.append("customer_code LIKE :q_code")
        params["q_code"] = f"%{q.upper()}%"

    if clean_q and len(clean_q) >= 4:
        conditions.append("phone LIKE :q_phone")
        conditions.append("phone_backup LIKE :q_phone")
        conditions.append("recipient2_phone LIKE :q_phone")
        conditions.append("tel LIKE :q_phone")
        params["q_phone"] = f"%{clean_q}%"

    sql = f"""
        SELECT customer_id, customer_code, name, gender, id_card, phone, phone_backup, tel, email, 
               address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at
        FROM customers
        WHERE {" OR ".join(conditions)}
        ORDER BY customer_id DESC
    """
    df = read_query(sql, params)
    return df.to_records(index=False).tolist()

def get_customer_by_id(cid):
    df = read_query("""
        SELECT customer_id, customer_code, name, gender, id_card, phone, phone_backup, tel, email, 
               address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at
        FROM customers WHERE customer_id = :cid
    """, {"cid": cid})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def get_customer_history(customer_id):
    return read_query("""
        SELECT order_id, channel, product, amount, order_date, raw_date_code, status, order_notes
        FROM orders
        WHERE customer_id = :cid
        ORDER BY order_date DESC, order_id DESC
    """, {"cid": customer_id})

def update_customer_db(cid, code, name, gender, id_card, phone, phone_bak, tel, email, addr, r2_name, r2_phone, r2_addr, pref):
    execute_query("""
        UPDATE customers 
        SET customer_code = :code, name = :name, gender = :gender, id_card = :id_card, 
            phone = :phone, phone_backup = :phone_bak, tel = :tel, email = :email, 
            address = :addr, recipient2_name = :r2_name, recipient2_phone = :r2_phone, 
            recipient2_address = :r2_addr, dietary_preference = :pref
        WHERE customer_id = :cid
    """, {
        "code": code, "name": name, "gender": gender, "id_card": id_card,
        "phone": clean_phone(phone), "phone_bak": phone_bak, "tel": tel, "email": email,
        "addr": addr, "r2_name": r2_name, "r2_phone": clean_phone(r2_phone), "r2_addr": r2_addr, "pref": pref, "cid": cid
    })

def delete_order(order_id):
    execute_query("DELETE FROM orders WHERE order_id = :oid", {"oid": order_id})

# --- 4. 主介面排版 ---
st.title("🌾 有其田 客服管理系統 (🌟CRM 旗艦升級版🌟)")

tab1, tab2, tab3, tab4, tab6, tab5 = st.tabs([
    "🔍 舊客速查與編輯", 
    "🆕 建立新名單", 
    "👤 歷程與時間軸", 
    "📊 客戶名冊總表",
    "📅 報表與匯出",
    "📥 匯入舊名單"
])

# ==========================================
# TAB 1: 舊客戶速查與編輯
# ==========================================
with tab1:
    st.markdown("### 🔍 舊客戶電話 / 代號 / 姓名速查")
    
    col_search, _ = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "請輸入查詢關鍵字（客戶姓名、主要手機、備用手機、市話或 CRM 代號）", 
            placeholder="例：蔡汶容、0912345678、08-9355127 或 CRM007122",
            key="accurate_cust_search"
        ).strip()

    if search_query:
        matched_custs = search_customers_accurate(search_query)
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

                history_df = get_customer_history(cid)
                total_orders = len(history_df)
                total_spent = history_df['amount'].sum() if total_orders > 0 else 0

                st.success(f"🎯 已調出客戶：【{cname}】（代號：{ccode}）")

                m1, m2, m3 = st.columns(3)
                m1.metric("累積購買次數", f"{total_orders} 次")
                m2.metric("累積消費金額", f"NT$ {total_spent:,}")
                m3.metric("初次建檔時間", str(ccreated).split()[0] if ccreated else "-")

                with st.expander(f"📜 點擊檢視【{cname}】的 {total_orders} 筆歷史購買紀錄", expanded=True):
                    if history_df.empty:
                        st.write("目前尚無訂單紀錄。")
                    else:
                        for _, r in history_df.iterrows():
                            oid = r['order_id']
                            code_tag = f" `代碼: {r['raw_date_code']}`" if r['raw_date_code'] else ""
                            st.markdown(f"🗓️ **{r['order_date']}**{code_tag} | 管道：**{r['channel']}** | 金額：**NT$ {r['amount']:,}** | 狀態：`{r['status']}`")
                            st.markdown(f"* **商品**：**{r['product']}** | **備註**：{r['order_notes'] if r['order_notes'] else '無'}")
                            
                            col_del_btn, _ = st.columns([2, 8])
                            with col_del_btn:
                                if st.button(f"🗑️ 刪除此筆訂單 (#{oid})", key=f"del_order_tab1_{oid}"):
                                    delete_order(oid)
                                    st.success(f"✅ 已刪除訂單 #{oid}！")
                                    st.rerun()
                            st.divider()

                st.markdown("---")
                st.subheader("✏️ 編輯客戶基本資料與收件資訊")

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
                            update_customer_db(cid, edit_code, edit_name, edit_gender, edit_id_card, edit_phone, edit_phone_bak, edit_tel, edit_email, edit_addr, edit_r2_name, edit_r2_phone, edit_r2_addr, edit_pref)
                            st.success(f"✅ 客戶【{edit_name}】資料已成功更新！")
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
            n_channel = st.selectbox("首次接觸管道 *", ["電話訂購 (B)", "官網 (A)", "LINE訂購", "其他"])

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
                                           address, recipient2_name, recipient2_phone, recipient2_address, dietary_preference, created_at)
                    VALUES (DEFAULT, :code, :name, :gender, :id_card, :phone, :phone_bak, :tel, :email, 
                            :addr, :r2_name, :r2_phone, :r2_addr, :pref, :created_at)
                    RETURNING customer_id
                """, {
                    "code": n_code, "name": n_name, "gender": n_gender, "id_card": n_id_card,
                    "phone": clean_np, "phone_bak": n_phone_bak, "tel": n_tel, "email": n_email,
                    "addr": n_addr, "r2_name": n_r2_name, "r2_phone": clean_phone(n_r2_phone),
                    "r2_addr": n_r2_addr, "pref": n_pref, "created_at": now_str
                })
                new_cid = res.fetchone()[0]

                if n_prod:
                    chan_clean = "電話訂購" if "電話" in n_channel else ("官網" if "官網" in n_channel else n_channel)
                    execute_query("""
                        INSERT INTO orders (customer_id, channel, product, amount, order_date, raw_date_code, status, order_notes)
                        VALUES (:cid, :chan, :prod, :amt, :odate, '', '已接單/待出貨', '')
                    """, {
                        "cid": new_cid, "chan": chan_clean, "prod": n_prod,
                        "amt": n_amt, "odate": str(n_date)
                    })

                st.success(f"🎉 成功建立新會員【{n_name}】（代號：{n_code}）！")
                st.rerun()

# ==========================================
# TAB 3: 客戶詳細歷程與時間軸
# ==========================================
with tab3:
    st.subheader("👤 客戶檔案與歷史訂購時間軸")
    all_df = read_query("SELECT customer_id, customer_code, name, phone FROM customers ORDER BY customer_id DESC")

    if not all_df.empty:
        c_opts = {f"[{row['customer_code']}] {row['name']} ({row['phone']})": row['customer_id'] for _, row in all_df.iterrows()}
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
                        update_customer_db(cid, t_code, t_name, t_gender, t_id_card, t_phone, t_phone_bak, t_tel, t_email, t_addr, t_r2_name, t_r2_phone, t_r2_addr, t_pref)
                        st.success("✅ 客戶資料已同步更新！")
                        st.rerun()

            st.markdown("---")
            st.write("**⏳ 歷史訂單與購買軌跡（支援修改或刪除）：**")
            if h_df.empty:
                st.info("尚無歷史訂單紀錄。")
            else:
                for _, r in h_df.iterrows():
                    oid = r['order_id']
                    code_badge = f" `原始紀錄:{r['raw_date_code']}`" if r['raw_date_code'] else ""
                    with st.expander(f"🗓️ {r['order_date']}{code_badge} | {r['channel']} | 金額：NT$ {r['amount']:,} | 狀態：{r['status']}", expanded=False):
                        with st.form(key=f"edit_order_form_{oid}"):
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

                        if st.button(f"🗑️ 刪除此筆訂單紀錄 (#{oid})", key=f"del_timeline_order_{oid}"):
                            delete_order(oid)
                            st.success(f"✅ 已刪除訂單 #{oid}！")
                            st.rerun()

# ==========================================
# TAB 4: 客戶名冊總表
# ==========================================
with tab4:
    st.subheader("📊 客戶名冊總表")
    df_all = read_query("""
        SELECT 
            c.customer_id AS "系統編號",
            c.customer_code AS "客戶代號",
            c.name AS "姓名",
            c.gender AS "性別",
            c.phone AS "主要手機",
            c.phone_backup AS "備用手機",
            c.tel AS "市話",
            c.address AS "常用地址",
            c.recipient2_name AS "第二收件人",
            c.recipient2_phone AS "第二收件電話",
            c.recipient2_address AS "第二收件地址",
            c.dietary_preference AS "飲食偏好",
            COUNT(o.order_id) AS "總購買次數",
            MAX(o.order_date) AS "最後購買日"
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id
        ORDER BY c.customer_id DESC
    """)

    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True)
        csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 匯出完整名冊 (CSV)", csv_data, "有其田_客戶完整名冊.csv", "text/csv")

        st.markdown("---")
        st.subheader("✏️ 從名冊快速選取客戶進行編輯")
        list_opts = {f"[{row['客戶代號']}] {row['姓名']} ({row['主要手機']}) - ID:{row['系統編號']}": row['系統編號'] for _, row in df_all.iterrows()}
        edit_select_label = st.selectbox("選擇要編輯的客戶：", list(list_opts.keys()), key="list_edit_select")
        edit_target_cid = list_opts[edit_select_label]

        cust = get_customer_by_id(edit_target_cid)
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

            with st.form(key=f"edit_cust_form_tab4_{cid}"):
                st.markdown("##### 👤 本人資料與常用地址")
                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    l_code = st.text_input("客戶代號", value=ccode if ccode else "")
                    l_name = st.text_input("姓名 *", value=cname if cname else "")
                    l_gender = st.selectbox("性別", ["女", "男", "其他"], index=0 if cgender == "女" else (1 if cgender == "男" else 2))
                with lc2:
                    l_phone = st.text_input("主要手機 *", value=cphone if cphone else "")
                    l_phone_bak = st.text_input("備用手機", value=cphone_bak if cphone_bak else "")
                    l_tel = st.text_input("市話電話", value=ctel if ctel else "")
                with lc3:
                    l_id_card = st.text_input("身分證號 / 統編", value=cid_card if cid_card else "")
                    l_email = st.text_input("EMAIL", value=cemail if cemail else "")

                l_addr = st.text_input("常用收件地址 (本人) *", value=caddr if caddr else "")
                l_pref = st.text_input("飲食偏好 / 客戶備註", value=cpref if cpref else "")

                st.markdown("##### 🎁 送禮 / 第二收件人")
                lr2_1, lr2_2 = st.columns(2)
                with lr2_1:
                    l_r2_name = st.text_input("第二收件人姓名 (送禮對象)", value=cr2_name if cr2_name else "")
                with lr2_2:
                    l_r2_phone = st.text_input("第二收件人手機 (送禮電話)", value=cr2_phone if cr2_phone else "")
                l_r2_addr = st.text_input("第二收件地址 (送禮地址)", value=cr2_addr if cr2_addr else "")

                l_save_btn = st.form_submit_button("💾 儲存並更新名冊資料")
                if l_save_btn:
                    update_customer_db(cid, l_code, l_name, l_gender, l_id_card, l_phone, l_phone_bak, l_tel, l_email, l_addr, l_r2_name, l_r2_phone, l_r2_addr, l_pref)
                    st.success(f"✅ 名冊客戶【{l_name}】資料已成功修改並同步覆蓋！")
                    st.rerun()
    else:
        st.info("尚無客戶資料。")

# ==========================================
# TAB 6: 期間訂單報表與匯出
# ==========================================
with tab6:
    st.subheader("📅 期間訂單紀錄撈取與報表匯出")
    st.markdown("請選擇您要查詢的日期區間（以訂單建立日期為準）：")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("起始日期", value=date.today().replace(day=1))
    with col_d2:
        end_date = st.date_input("結束日期", value=date.today())

    if st.button("📊 產生期間報表"):
        if start_date > end_date:
            st.error("起始日期不能大於結束日期，請重新選擇！")
        else:
            report_sql = """
                SELECT 
                    o.order_date AS "訂購日期",
                    c.customer_code AS "客戶代號",
                    c.name AS "客戶姓名",
                    c.phone AS "手機號碼",
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
                st.warning(f"⚠️ 在 {start_date} 至 {end_date} 期間內，沒有找到任何訂單紀錄。")
            else:
                total_amount = report_df["訂單金額"].sum()
                st.success(f"✅ 成功撈取 **{len(report_df)}** 筆訂單紀錄！此區間累積金額為：**NT$ {total_amount:,}**")
                
                st.dataframe(report_df, use_container_width=True)

                csv_data = report_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 下載 {start_date} 至 {end_date} 訂單明細 (CSV)",
                    data=csv_data,
                    file_name=f"有其田_期間訂單報表_{start_date}至{end_date}.csv",
                    mime="text/csv"
                )

# ==========================================
# TAB 5: 批次匯入舊名單
# ==========================================
with tab5:
    st.subheader("📥 匯入 Excel 名單（兩段式秒級終極匯入）")
    uploaded_file = st.file_uploader("上傳 Excel 檔案（.xlsx）", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            st.write(f"📂 偵測到工作表：`{', '.join(excel_file.sheet_names)}`")
            
            if st.button("🚀 確認並開始 3 秒極速匯入"):
                bar = st.progress(10)
                status = st.empty()

                status.info("⚡ [1/3] 正在載入比對快取並解析 Excel...")
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

                existing_orders_df = read_query("SELECT customer_id, raw_date_code FROM orders WHERE raw_date_code != ''")
                existing_order_set = set(zip(existing_orders_df['customer_id'].astype(int), existing_orders_df['raw_date_code'].astype(str)))

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cust_inserts = []
                order_tasks = []

                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=str)
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
                                if (col_str.startswith("購") or col_str.startswith("Unnamed")) and (("-" in val_str) or ("/" in val_str) or val_str.startswith("A") or val_str.startswith("B")):
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
                                    order_tasks.append((matched_cid, False, o_chan, o_date, r_code))
                                    existing_order_set.add((matched_cid, r_code))
                        else:
                            if not cust_code:
                                max_crm_num += 1
                                cust_code = f"CRM{max_crm_num:06d}"

                            cust_inserts.append({
                                "customer_code": cust_code, "name": name, "gender": gender, "id_card": id_card,
                                "phone": p1, "phone_backup": p2, "tel": t1, "address": addr, "created_at": now_str
                            })
                            if p1:
                                phone_to_id[p1] = cust_code
                            code_to_id[cust_code] = cust_code

                            for o_chan, o_date, r_code in row_orders:
                                order_tasks.append((cust_code, True, o_chan, o_date, r_code))

                bar.progress(50)
                status.info(f"⚡ [2/3] 正在極速寫入 {len(cust_inserts)} 位新客戶...")

                engine = get_db_engine()
                if cust_inserts:
                    new_cust_df = pd.DataFrame(cust_inserts)
                    new_cust_df.to_sql("customers", engine, if_exists="append", index=False, method="multi", chunksize=500)

                bar.progress(80)
                status.info(f"⚡ [3/3] 正在整批連結並寫入 {len(order_tasks)} 筆訂單軌跡...")

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
                for target_ref, is_new, o_chan, o_date, r_code in order_tasks:
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
                            "channel": o_chan,
                            "product": "常態訂購品項",
                            "amount": 0,
                            "order_date": o_date,
                            "raw_date_code": r_code,
                            "status": "歷史完成",
                            "order_notes": f"原始代碼: {r_code}"
                        })

                if final_orders:
                    orders_df = pd.DataFrame(final_orders)
                    orders_df = orders_df.drop_duplicates(subset=["customer_id", "raw_date_code"])
                    orders_df.to_sql("orders", engine, if_exists="append", index=False, method="multi", chunksize=1000)

                bar.progress(100)
                status.empty()
                st.success(f"🎉 極速匯入大成功！成功建檔 **{len(cust_inserts)}** 位會員，並完整寫入 **{len(final_orders)}** 筆購買軌跡！")
        except Exception as e:
            st.error(f"匯入錯誤：{e}")
