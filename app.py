# -*- coding: utf-8 -*-
"""
دفتر الحسابات - نسخة ويب احترافية كاملة
قاعدة بيانات SQLite محلية
يدعم الإدخال الصوتي للهجة اليمنية
العملة: ريال يمني (YER)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import whisper
import tempfile
import os
import re
import base64
from io import BytesIO
import sqlite3
import uuid
from streamlit_extras.colored_header import colored_header
from streamlit_extras.stylable_container import stylable_container
from streamlit_mic_recorder import mic_recorder

# ---------- إعدادات الصفحة ----------
st.set_page_config(
    page_title="دفتر الحسابات - يمني",
    page_icon="🇾🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- الثوابت ----------
CURRENCY = "ريال يمني"
CURRENCY_SYMBOL = "﷼"
DB_FILE = "database.db"

# ---------- دوال قاعدة البيانات SQLite ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            person_id TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('دين لك', 'دين عليك')),
            notes TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def get_persons():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM persons ORDER BY name", conn)
    conn.close()
    return df.to_dict('records')

def get_transactions():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('''
        SELECT t.*, p.name as person_name 
        FROM transactions t
        JOIN persons p ON t.person_id = p.id
        ORDER BY t.date DESC
    ''', conn)
    conn.close()
    return df.to_dict('records')

def add_person(name: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO persons (id, name) VALUES (?, ?)",
        (str(uuid.uuid4()), name.strip())
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()

def add_transaction(person_id: str, amount: float, trans_type: str, notes: str, trans_date: datetime):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (id, person_id, amount, type, notes, date) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), person_id, amount, trans_type, notes, trans_date.isoformat())
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()

init_db()

# ---------- دوال مساعدة للتصدير ----------
def get_table_download_link(df, filename="البيانات.csv", text="📥 تنزيل CSV"):
    csv = df.to_csv(index=False).encode('utf-8-sig')
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def get_excel_download_link(df, filename="البيانات.xlsx", text="📊 تنزيل Excel"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    b64 = base64.b64encode(processed_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
    return href

def get_image_download_script(element_id, filename="لقطة_الجدول.png"):
    html_code = f"""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <button id="capture-btn-{element_id}" style="padding: 0.5rem 1rem; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
        🖼️ التقاط صورة للجدول
    </button>
    <script>
    document.getElementById('capture-btn-{element_id}').addEventListener('click', function() {{
        var element = window.parent.document.querySelector('[data-testid="stDataFrame"]');
        if (!element) {{
            element = window.parent.document.querySelector('.stDataFrame');
        }}
        if (element) {{
            html2canvas(element, {{ scale: 2, backgroundColor: '#ffffff' }}).then(canvas => {{
                var link = document.createElement('a');
                link.download = '{filename}';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }}).catch(error => {{
                console.error('html2canvas error:', error);
                alert('تعذر التقاط الصورة.');
            }});
        }} else {{
            alert('لم يتم العثور على الجدول!');
        }}
    }});
    </script>
    """
    return html_code

# ---------- تحميل البيانات ----------
persons = get_persons()
transactions = get_transactions()

person_dict = {p["id"]: p["name"] for p in persons}
person_options = {p["name"]: p["id"] for p in persons}

# ---------- تجهيز بيانات الأرصدة ----------
if transactions:
    df_trans = pd.DataFrame(transactions)
    df_trans["date"] = pd.to_datetime(df_trans["date"])
    df_trans["effect"] = df_trans.apply(
        lambda row: row["amount"] if row["type"] == "دين لك" else -row["amount"], axis=1
    )
    balances = df_trans.groupby("person_id")["effect"].sum().reset_index()
    balances["person_name"] = balances["person_id"].map(person_dict)
    balances = balances[["person_name", "effect"]].rename(columns={"effect": "الرصيد"})
else:
    balances = pd.DataFrame(columns=["person_name", "الرصيد"])

# ---------- دوال التعرف على الصوت ----------
@st.cache_resource
def load_whisper_model():
    try:
        model = whisper.load_model("tiny")  # استخدام tiny لسرعة أكبر
        return model
    except Exception as e:
        st.error(f"فشل تحميل نموذج Whisper: {e}")
        return None

def parse_voice_command(text: str, persons_list: list):
    text = text.strip()
    original_text = text
    text = re.sub(r'[،,\.\?\!]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    number_words = {
        "صفر": 0, "واحد": 1, "واحِد": 1, "اثنين": 2, "اثنان": 2, "ثنتين": 2,
        "ثلاثة": 3, "ثلاث": 3, "اربعة": 4, "أربعة": 4, "خمسة": 5, "خمس": 5,
        "ستة": 6, "ست": 6, "سبعة": 7, "سبع": 7, "ثمانية": 8, "ثمان": 8,
        "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10,
        "عشرين": 20, "ثلاثين": 30, "اربعين": 40, "خمسين": 50,
        "ستين": 60, "سبعين": 70, "ثمانين": 80, "تسعين": 90,
        "مية": 100, "مئة": 100, "ميه": 100, "ميتين": 200, "مئتين": 200,
        "ثلاثميه": 300, "اربعميه": 400, "خمسميه": 500,
        "ستميه": 600, "سبعميه": 700, "ثمانميه": 800, "تسعميه": 900,
        "الف": 1000, "ألف": 1000, "الفين": 2000, "ألفين": 2000,
        "ثلاثة الاف": 3000, "اربعة الاف": 4000, "خمسة الاف": 5000,
        "ريال": 1, "ريالات": 1, "﷼": 1, "YER": 1
    }

    trans_type = None
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["علي", "عليه", "دين علي", "مدين", "له"]):
        trans_type = "دين عليك"
    elif any(kw in text_lower for kw in ["لي", "دين لي", "دائن", "عندي", "لصالح"]):
        trans_type = "دين لك"
    else:
        trans_type = "دين عليك" if "دين" in text_lower else "دين لك"

    amount = 0.0
    arabic_digits = {'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9'}
    text_clean = text
    for a, e in arabic_digits.items():
        text_clean = text_clean.replace(a, e)

    match = re.search(r'(\d+(?:\.\d+)?)', text_clean)
    if match:
        amount = float(match.group(1))
    else:
        words = text_clean.split()
        total = 0
        current = 0
        for word in words:
            if word in number_words:
                val = number_words[word]
                if val >= 1000:
                    current = current if current != 0 else 1
                    total += current * val
                    current = 0
                elif val >= 100:
                    current = current if current != 0 else 1
                    total += current * val
                    current = 0
                else:
                    current += val
        total += current
        amount = float(total)

    keywords_to_remove = ["دين", "علي", "لي", "بمبلغ", "أضف", "مبلغ", "بـ", "قدره", "قدرها",
                          "ريال", "ريالات", "دولار", "دينار", "عليه", "مدين", "دائن", "عندي",
                          "لصالح", "من", "إلى", "عن", "سجل", "ضيف", "حط", "خلي", "عند"]
    for kw in keywords_to_remove:
        text_clean = re.sub(rf'\b{kw}\b', '', text_clean, flags=re.IGNORECASE)
    text_clean = re.sub(r'\d+', '', text_clean)
    name_candidate = re.sub(r'\s+', ' ', text_clean).strip()
    if not name_candidate:
        name_candidate = original_text[:20]

    matched_person = None
    for p in persons_list:
        p_name = p["name"].strip()
        if (p_name in name_candidate) or (name_candidate in p_name) or (p_name.lower() == name_candidate.lower()):
            matched_person = p
            break

    return {
        "trans_type": trans_type,
        "amount": amount,
        "person_name": name_candidate if not matched_person else matched_person["name"],
        "matched_person": matched_person,
        "raw_text": original_text
    }

# ---------- واجهة المستخدم ----------
colored_header(
    label=f"📒 دفتر الحسابات - {CURRENCY} 🇾🇪",
    description="إدارة ديونك وحساباتك بكل سهولة مع دعم الإدخال الصوتي للهجة اليمنية",
    color_name="blue-70",
)

# ---------- الشريط الجانبي ----------
with st.sidebar:
    with stylable_container(
        key="sidebar_container",
        css_styles="""
            {
                background-color: #f0f2f6;
                padding: 1rem;
                border-radius: 10px;
            }
            """,
    ):
        st.header("➕ إضافة معاملة")
        if persons:
            selected_person_name = st.selectbox("👤 اختر الشخص", list(person_options.keys()))
            selected_person_id = person_options[selected_person_name]
        else:
            st.warning("لا يوجد أشخاص مسجلين. أضف شخصاً أولاً.")
            selected_person_id = None

        with st.expander("➕ إضافة شخص جديد"):
            new_name = st.text_input("اسم الشخص الجديد")
            if st.button("إضافة الشخص") and new_name:
                add_person(new_name)
                st.success(f"تمت إضافة {new_name}")
                st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(f"💰 المبلغ ({CURRENCY_SYMBOL})", min_value=0.0, step=100.0, format="%.2f")
        with col2:
            trans_type = st.selectbox("📌 نوع المعاملة", ["دين لك", "دين عليك"])
        notes = st.text_input("📝 ملاحظات (اختياري)")
        trans_date = st.date_input("📅 التاريخ", value=datetime.today())

        if st.button("💾 حفظ المعاملة", type="primary", use_container_width=True):
            if selected_person_id and amount > 0:
                add_transaction(selected_person_id, amount, trans_type, notes, trans_date)
                st.success("تم حفظ المعاملة بنجاح")
                st.rerun()
            else:
                st.error("الرجاء اختيار شخص وإدخال مبلغ صحيح")

    st.markdown("---")

    # ---------- الإدخال الصوتي (باستخدام mic_recorder) ----------
    with stylable_container(
        key="voice_container",
        css_styles="""
            {
                background-color: #e6f3ff;
                padding: 1rem;
                border-radius: 10px;
                border-left: 5px solid #1f77b4;
            }
            """,
    ):
        st.header("🎤 الإدخال الصوتي")
        st.caption("اضغط على الميكروفون وتحدث، ثم اضغط مرة أخرى للإيقاف")
        
        model = load_whisper_model()
        
        audio_data = mic_recorder(
            start_prompt="🎙️ بدء التسجيل",
            stop_prompt="⏹️ إيقاف التسجيل",
            just_once=False,
            use_container_width=True,
            format="wav",
            key="voice_recorder"
        )
        
        if audio_data is not None:
            st.audio(audio_data['bytes'], format='audio/wav')
            
            if st.button("🔄 تحليل الصوت", type="secondary", use_container_width=True):
                if model is None:
                    st.error("نموذج Whisper غير جاهز.")
                else:
                    with st.spinner("جاري تحويل الصوت إلى نص..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                            tmp_file.write(audio_data['bytes'])
                            tmp_file_path = tmp_file.name
                        
                        try:
                            result = model.transcribe(tmp_file_path, language="ar", task="transcribe")
                            transcribed_text = result["text"]
                            st.success(f"**النص المستخرج:** {transcribed_text}")
                            parsed = parse_voice_command(transcribed_text, persons)

                            with st.expander("✅ تأكيد البيانات المستخرجة", expanded=True):
                                st.write(f"**النص الأصلي:** {parsed['raw_text']}")
                                person_names = list(person_options.keys())
                                default_index = 0
                                if parsed['matched_person']:
                                    default_index = person_names.index(parsed['matched_person']['name'])
                                selected_person_name_voice = st.selectbox(
                                    "👤 تأكيد الشخص", person_names, index=default_index
                                )
                                selected_person_id_voice = person_options[selected_person_name_voice]
                                amount_voice = st.number_input(
                                    f"💰 المبلغ ({CURRENCY_SYMBOL})",
                                    value=float(parsed['amount']),
                                    min_value=0.0,
                                    step=100.0,
                                    format="%.2f"
                                )
                                type_index = 0 if parsed['trans_type'] == "دين لك" else 1
                                trans_type_voice = st.selectbox(
                                    "📌 نوع المعاملة", ["دين لك", "دين عليك"], index=type_index
                                )
                                notes_voice = st.text_area("📝 ملاحظات", value=transcribed_text[:100])
                                
                                if st.button("💾 حفظ المعاملة الصوتية", type="primary", use_container_width=True):
                                    if selected_person_id_voice and amount_voice > 0:
                                        add_transaction(
                                            selected_person_id_voice, amount_voice,
                                            trans_type_voice, notes_voice, datetime.today()
                                        )
                                        st.success("تم حفظ المعاملة بنجاح!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("الرجاء التأكد من البيانات.")
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء معالجة الصوت: {e}")
                        finally:
                            os.unlink(tmp_file_path)

# ---------- المحتوى الرئيسي ----------
tab1, tab2 = st.tabs(["📊 الأرصدة", "📋 كشف الحسابات"])

with tab1:
    colored_header("أرصدة الأشخاص الحالية", description=f"جميع المبالغ بـ {CURRENCY}", color_name="green-70")

    if not balances.empty:
        st.dataframe(
            balances.style.format({"الرصيد": "{:,.2f}"}).applymap(
                lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else ''),
                subset=['الرصيد']
            ),
            use_container_width=True,
            height=300
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(get_table_download_link(balances, filename="الارصدة.csv", text="📥 CSV"), unsafe_allow_html=True)
        with col2:
            st.markdown(get_excel_download_link(balances, filename="الارصدة.xlsx", text="📊 Excel"), unsafe_allow_html=True)
        with col3:
            st.markdown(get_image_download_script("balances_table", "لقطة_الأرصدة.png"), unsafe_allow_html=True)
        with col4:
            fig_balances = px.bar(
                balances, x="person_name", y="الرصيد",
                title="الأرصدة بالريال اليمني",
                color="الرصيد",
                color_continuous_scale=["red", "lightgray", "green"],
                labels={"الرصيد": f"الرصيد ({CURRENCY_SYMBOL})", "person_name": "الشخص"}
            )
            img_bytes = fig_balances.to_image(format="png", width=800, height=500)
            st.download_button(
                label="🖼️ رسم بياني PNG",
                data=img_bytes,
                file_name="الارصدة_رسم.png",
                mime="image/png"
            )

        st.plotly_chart(fig_balances, use_container_width=True)

        total_credit = balances[balances["الرصيد"] > 0]["الرصيد"].sum()
        total_debit = abs(balances[balances["الرصيد"] < 0]["الرصيد"].sum())
        c1, c2 = st.columns(2)
        with c1:
            st.metric("💰 إجمالي الديون لك (دائن)", f"{total_credit:,.2f} {CURRENCY_SYMBOL}")
        with c2:
            st.metric("💸 إجمالي الديون عليك (مدين)", f"{total_debit:,.2f} {CURRENCY_SYMBOL}")
    else:
        st.info("لا توجد معاملات بعد. أضف معاملة من الشريط الجانبي أو استخدم الإدخال الصوتي.")

with tab2:
    colored_header("سجل المعاملات", description="جميع الحركات المالية المسجلة", color_name="orange-70")

    if transactions:
        filter_person = st.selectbox("فلترة حسب الشخص", ["الكل"] + list(person_options.keys()))
        df_display = df_trans.copy()
        if filter_person != "الكل":
            df_display = df_display[df_display["person_name"] == filter_person]

        df_display = df_display[["date", "person_name", "type", "amount", "notes"]]
        df_display.columns = ["التاريخ", "الشخص", "النوع", "المبلغ", "ملاحظات"]
        df_display = df_display.sort_values("التاريخ", ascending=False)

        st.dataframe(
            df_display.style.format({"المبلغ": "{:,.2f}"}),
            use_container_width=True,
            height=400
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(get_table_download_link(df_display, filename="كشف_حساب.csv", text="📥 CSV"), unsafe_allow_html=True)
        with col2:
            st.markdown(get_excel_download_link(df_display, filename="كشف_حساب.xlsx", text="📊 Excel"), unsafe_allow_html=True)
        with col3:
            st.markdown(get_image_download_script("transactions_table", "لقطة_كشف_حساب.png"), unsafe_allow_html=True)

        if not df_display.empty:
            total_shown = df_display["المبلغ"].sum()
            st.metric("إجمالي المبالغ المعروضة", f"{total_shown:,.2f} {CURRENCY_SYMBOL}")
    else:
        st.info("لا توجد معاملات مسجلة.")

# ---------- تذييل ----------
st.markdown("---")
st.caption("🚀 تطبيق دفتر الحسابات - نسخة ويب مفتوحة المصدر | يدعم الإدخال الصوتي للهجة اليمنية 🇾🇪")
