import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json
import uuid

# ---------- إعداد الصفحة ----------
st.set_page_config(page_title="دفتر الحسابات", page_icon="📒", layout="wide")
st.title("📒 دفتر الحسابات - ريال يمني 🇾🇪")

# ---------- قاعدة بيانات بسيطة باستخدام ملف JSON ----------
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"persons": [], "transactions": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()
persons = data["persons"]
transactions = data["transactions"]

person_dict = {p["id"]: p["name"] for p in persons}
person_options = {p["name"]: p["id"] for p in persons}

# ---------- دوال مساعدة ----------
def add_person(name):
    new_id = str(uuid.uuid4())
    persons.append({"id": new_id, "name": name.strip()})
    data["persons"] = persons
    save_data(data)

def add_transaction(person_id, amount, trans_type, notes, trans_date):
    trans = {
        "id": str(uuid.uuid4()),
        "person_id": person_id,
        "amount": amount,
        "type": trans_type,
        "notes": notes,
        "date": trans_date.isoformat()
    }
    transactions.append(trans)
    data["transactions"] = transactions
    save_data(data)

# ---------- تجهيز بيانات الأرصدة ----------
if transactions:
    df_trans = pd.DataFrame(transactions)
    df_trans["date"] = pd.to_datetime(df_trans["date"])
    df_trans["person_name"] = df_trans["person_id"].map(person_dict)
    df_trans["effect"] = df_trans.apply(
        lambda row: row["amount"] if row["type"] == "دين لك" else -row["amount"], axis=1
    )
    balances = df_trans.groupby("person_id")["effect"].sum().reset_index()
    balances["person_name"] = balances["person_id"].map(person_dict)
    balances = balances[["person_name", "effect"]].rename(columns={"effect": "الرصيد"})
else:
    balances = pd.DataFrame(columns=["person_name", "الرصيد"])

# ---------- كود JavaScript للتعرف على الصوت (Web Speech API) ----------
voice_script = """
<script>
let recognition;
let isRecording = false;

function startRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('متصفحك لا يدعم التعرف على الصوت. الرجاء استخدام Chrome أو Edge.');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'ar-YE';  // العربية (اللهجة اليمنية)
    recognition.interimResults = false;
    recognition.continuous = false;
    
    recognition.onstart = function() {
        isRecording = true;
        document.getElementById('voice-status').innerText = '🎙️ جاري الاستماع... تحدث الآن';
        document.getElementById('start-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
    };
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('voice-result').value = transcript;
        document.getElementById('voice-status').innerText = '✅ تم الاستماع. اضغط "تحليل النص"';
        
        // إرسال النص إلى Streamlit
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: transcript
        }, '*');
    };
    
    recognition.onerror = function(event) {
        document.getElementById('voice-status').innerText = '❌ خطأ: ' + event.error;
        resetButtons();
    };
    
    recognition.onend = function() {
        resetButtons();
    };
    
    recognition.start();
}

function stopRecording() {
    if (recognition) {
        recognition.stop();
        document.getElementById('voice-status').innerText = '⏹️ تم الإيقاف';
    }
    resetButtons();
}

function resetButtons() {
    isRecording = false;
    document.getElementById('start-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
}

// إرسال النص إلى Streamlit عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    const resultField = document.getElementById('voice-result');
    resultField.addEventListener('change', function() {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: resultField.value
        }, '*');
    });
});
</script>

<div style="background-color: #e6f3ff; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4;">
    <h4>🎤 الإدخال الصوتي</h4>
    <p style="font-size: 0.9rem;">تحدث بالعربية أو اللهجة اليمنية</p>
    <button id="start-btn" onclick="startRecording()" style="padding: 8px 16px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;">🎙️ بدء التسجيل</button>
    <button id="stop-btn" onclick="stopRecording()" disabled style="padding: 8px 16px; background-color: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;">⏹️ إيقاف</button>
    <p id="voice-status" style="margin-top: 10px; font-weight: bold;"></p>
    <input type="hidden" id="voice-result">
</div>
"""

# ---------- دالة تحليل النص المستخرج ----------
def parse_voice_command(text: str, persons_list: list):
    """تحليل النص العربي لاستخراج اسم الشخص والمبلغ والنوع."""
    import re
    
    text = text.strip()
    original_text = text
    
    # تنظيف النص
    text = re.sub(r'[،,\.\?\!]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # كلمات دالة على الأرقام
    number_words = {
        "صفر": 0, "واحد": 1, "اثنين": 2, "ثلاثة": 3, "اربعة": 4, "أربعة": 4,
        "خمسة": 5, "ستة": 6, "سبعة": 7, "ثمانية": 8, "تسعة": 9, "عشرة": 10,
        "عشرين": 20, "ثلاثين": 30, "اربعين": 40, "خمسين": 50,
        "ستين": 60, "سبعين": 70, "ثمانين": 80, "تسعين": 90,
        "مية": 100, "مئة": 100, "ميه": 100, "ميتين": 200, "مئتين": 200,
        "ثلاثميه": 300, "اربعميه": 400, "خمسميه": 500,
        "ستميه": 600, "سبعميه": 700, "ثمانميه": 800, "تسعميه": 900,
        "الف": 1000, "ألف": 1000, "الفين": 2000, "ألفين": 2000,
        "ريال": 1, "ريالات": 1
    }
    
    # تحديد نوع المعاملة
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["علي", "عليه", "دين علي", "مدين", "له"]):
        trans_type = "دين عليك"
    elif any(kw in text_lower for kw in ["لي", "دين لي", "دائن", "عندي", "لصالح"]):
        trans_type = "دين لك"
    else:
        trans_type = "دين عليك" if "دين" in text_lower else "دين لك"
    
    # استخراج المبلغ
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
    
    # استخراج اسم الشخص
    keywords_to_remove = ["دين", "علي", "لي", "بمبلغ", "أضف", "مبلغ", "بـ", "قدره", "قدرها",
                          "ريال", "ريالات", "دولار", "دينار", "عليه", "مدين", "دائن", "عندي",
                          "لصالح", "من", "إلى", "عن", "سجل", "ضيف", "حط", "خلي", "عند"]
    for kw in keywords_to_remove:
        text_clean = re.sub(rf'\b{kw}\b', '', text_clean, flags=re.IGNORECASE)
    text_clean = re.sub(r'\d+', '', text_clean)
    name_candidate = re.sub(r'\s+', ' ', text_clean).strip()
    if not name_candidate:
        name_candidate = original_text[:20]
    
    # مطابقة الاسم مع الأشخاص الموجودين
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

# ---------- الشريط الجانبي ----------
with st.sidebar:
    st.header("➕ إضافة معاملة")
    
    # اختيار الشخص
    if persons:
        selected_person_name = st.selectbox("👤 اختر الشخص", list(person_options.keys()))
        selected_person_id = person_options[selected_person_name]
    else:
        st.warning("لا يوجد أشخاص. أضف شخصاً:")
        selected_person_id = None

    # إضافة شخص جديد
    with st.expander("➕ إضافة شخص جديد"):
        new_name = st.text_input("الاسم")
        if st.button("إضافة") and new_name:
            add_person(new_name)
            st.success(f"تمت إضافة {new_name}")
            st.rerun()

    # إدخال يدوي
    amount = st.number_input("💰 المبلغ (﷼)", min_value=0.0, step=100.0, format="%.2f")
    trans_type = st.selectbox("📌 النوع", ["دين لك", "دين عليك"])
    notes = st.text_input("📝 ملاحظات")
    trans_date = st.date_input("📅 التاريخ", value=datetime.today())

    if st.button("💾 حفظ", type="primary", use_container_width=True):
        if selected_person_id and amount > 0:
            add_transaction(selected_person_id, amount, trans_type, notes, trans_date)
            st.success("تم الحفظ")
            st.rerun()
        else:
            st.error("اختر شخصاً وأدخل مبلغاً")

    st.markdown("---")

    # ---------- قسم الإدخال الصوتي ----------
    st.components.v1.html(voice_script, height=200)
    
    # استقبال النص من JavaScript
    voice_text = st.session_state.get("voice_text", "")
    
    # زر تحليل النص
    if st.button("🔄 تحليل النص الصوتي", use_container_width=True):
        if voice_text:
            st.session_state["voice_text"] = voice_text
        else:
            st.warning("الرجاء تسجيل صوت أولاً")
    
    # معالجة النص الصوتي
    if "voice_text" in st.session_state and st.session_state["voice_text"]:
        transcribed = st.session_state["voice_text"]
        st.success(f"**النص:** {transcribed}")
        
        parsed = parse_voice_command(transcribed, persons)
        
        with st.expander("✅ تأكيد البيانات", expanded=True):
            # اختيار الشخص
            person_names = list(person_options.keys())
            default_idx = 0
            if parsed['matched_person']:
                default_idx = person_names.index(parsed['matched_person']['name'])
            selected_person_name_v = st.selectbox("👤 تأكيد الشخص", person_names, index=default_idx, key="voice_person")
            selected_person_id_v = person_options[selected_person_name_v]
            
            # المبلغ
            amount_v = st.number_input("💰 المبلغ (﷼)", value=float(parsed['amount']), min_value=0.0, step=100.0, key="voice_amount")
            
            # النوع
            type_idx = 0 if parsed['trans_type'] == "دين لك" else 1
            trans_type_v = st.selectbox("📌 النوع", ["دين لك", "دين عليك"], index=type_idx, key="voice_type")
            
            # ملاحظات
            notes_v = st.text_area("📝 ملاحظات", value=transcribed[:100], key="voice_notes")
            
            if st.button("💾 حفظ المعاملة الصوتية", type="primary", use_container_width=True):
                if selected_person_id_v and amount_v > 0:
                    add_transaction(selected_person_id_v, amount_v, trans_type_v, notes_v, datetime.today())
                    st.success("تم الحفظ بنجاح!")
                    st.session_state["voice_text"] = ""
                    st.rerun()
                else:
                    st.error("الرجاء التأكد من البيانات")

# ---------- المحتوى الرئيسي ----------
tab1, tab2 = st.tabs(["📊 الأرصدة", "📋 كشف الحسابات"])

with tab1:
    st.subheader("الأرصدة الحالية")
    if not balances.empty:
        st.dataframe(
            balances.style.format({"الرصيد": "{:,.2f}"}).applymap(
                lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else ''),
                subset=['الرصيد']
            ),
            use_container_width=True
        )
        fig = px.bar(balances, x="person_name", y="الرصيد", color="الرصيد",
                     color_continuous_scale=["red", "lightgray", "green"])
        st.plotly_chart(fig, use_container_width=True)
        
        total_credit = balances[balances["الرصيد"] > 0]["الرصيد"].sum()
        total_debit = abs(balances[balances["الرصيد"] < 0]["الرصيد"].sum())
        c1, c2 = st.columns(2)
        c1.metric("💰 الديون لك", f"{total_credit:,.2f} ﷼")
        c2.metric("💸 الديون عليك", f"{total_debit:,.2f} ﷼")
    else:
        st.info("لا توجد معاملات بعد")

with tab2:
    st.subheader("سجل المعاملات")
    if transactions:
        df_display = df_trans[["date", "person_name", "type", "amount", "notes"]]
        df_display.columns = ["التاريخ", "الشخص", "النوع", "المبلغ", "ملاحظات"]
        st.dataframe(
            df_display.sort_values("التاريخ", ascending=False).style.format({"المبلغ": "{:,.2f}"}),
            use_container_width=True
        )
    else:
        st.info("لا توجد معاملات مسجلة")
