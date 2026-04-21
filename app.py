import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json
import uuid
import speech_recognition as sr
from st_audiorec import st_audiorec
import tempfile

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

# ---------- دالة تحويل الصوت إلى نص ----------
def transcribe_audio(audio_bytes):
    """تحويل الصوت (بايتات) إلى نص عربي باستخدام Google Speech Recognition."""
    r = sr.Recognizer()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with sr.AudioFile(tmp_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="ar-YE")  # عربي يمني
            return text
    except sr.UnknownValueError:
        return None
    except Exception as e:
        return f"خطأ: {e}"
    finally:
        os.unlink(tmp_path)

def parse_voice_command(text: str, persons_list: list):
    """تحليل النص العربي لاستخراج بيانات المعاملة."""
    import re
    text = text.strip()
    original = text
    text = re.sub(r'[،,\.\?\!]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # قاموس الأرقام
    number_words = {
        "صفر":0,"واحد":1,"اثنين":2,"ثلاثة":3,"اربعة":4,"خمسة":5,"ستة":6,"سبعة":7,
        "ثمانية":8,"تسعة":9,"عشرة":10,"عشرين":20,"ثلاثين":30,"اربعين":40,"خمسين":50,
        "ستين":60,"سبعين":70,"ثمانين":80,"تسعين":90,"مية":100,"مئة":100,"ميه":100,
        "ميتين":200,"ثلاثميه":300,"اربعميه":400,"خمسميه":500,"ستميه":600,"سبعميه":700,
        "ثمانميه":800,"تسعميه":900,"الف":1000,"ألف":1000,"الفين":2000,"ريال":1
    }

    # نوع المعاملة
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["علي", "عليه", "دين علي", "مدين", "له"]):
        trans_type = "دين عليك"
    elif any(kw in text_lower for kw in ["لي", "دين لي", "دائن", "عندي"]):
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
        for w in words:
            if w in number_words:
                val = number_words[w]
                if val >= 1000:
                    current = current or 1
                    total += current * val
                    current = 0
                elif val >= 100:
                    current = current or 1
                    total += current * val
                    current = 0
                else:
                    current += val
        total += current
        amount = float(total)

    # استخراج الاسم
    keywords = ["دين","علي","لي","بمبلغ","أضف","مبلغ","بـ","قدره","ريال","ريالات","عليه","مدين","دائن","عندي"]
    for kw in keywords:
        text_clean = re.sub(rf'\b{kw}\b', '', text_clean, flags=re.IGNORECASE)
    text_clean = re.sub(r'\d+', '', text_clean)
    name_candidate = re.sub(r'\s+', ' ', text_clean).strip() or original[:20]

    matched_person = None
    for p in persons_list:
        if p["name"].strip() in name_candidate or name_candidate in p["name"]:
            matched_person = p
            break

    return {
        "trans_type": trans_type,
        "amount": amount,
        "person_name": matched_person["name"] if matched_person else name_candidate,
        "matched_person": matched_person,
        "raw_text": original
    }

# ---------- الشريط الجانبي ----------
with st.sidebar:
    st.header("➕ إضافة معاملة")

    if persons:
        selected_person_name = st.selectbox("👤 اختر الشخص", list(person_options.keys()))
        selected_person_id = person_options[selected_person_name]
    else:
        st.warning("لا يوجد أشخاص. أضف شخصاً:")
        selected_person_id = None

    with st.expander("➕ إضافة شخص جديد"):
        new_name = st.text_input("الاسم")
        if st.button("إضافة") and new_name:
            add_person(new_name)
            st.success(f"تمت إضافة {new_name}")
            st.rerun()

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

    # ---------- ميزة التسجيل الصوتي باستخدام st_audiorec ----------
    st.subheader("🎤 الإدخال الصوتي")
    st.caption("اضغط على الميكروفون للتسجيل (يحتاج إنترنت مؤقت للتحليل)")

    wav_audio_data = st_audiorec()

    if wav_audio_data is not None:
        st.audio(wav_audio_data, format='audio/wav')

        if st.button("🔄 تحليل الصوت", type="secondary", use_container_width=True):
            with st.spinner("جاري تحويل الصوت إلى نص..."):
                transcribed = transcribe_audio(wav_audio_data)
                if transcribed is None:
                    st.error("لم نتمكن من فهم الصوت. حاول مرة أخرى بوضوح.")
                elif transcribed.startswith("خطأ"):
                    st.error(transcribed)
                else:
                    st.success(f"**النص:** {transcribed}")
                    parsed = parse_voice_command(transcribed, persons)

                    with st.expander("✅ تأكيد البيانات", expanded=True):
                        # قائمة الأشخاص
                        names = list(person_options.keys())
                        idx = names.index(parsed["matched_person"]["name"]) if parsed["matched_person"] else 0
                        sel_name = st.selectbox("👤 الشخص", names, index=idx, key="v_person")
                        sel_id = person_options[sel_name]

                        amt = st.number_input("💰 المبلغ", value=float(parsed['amount']), min_value=0.0, step=100.0, key="v_amount")
                        typ = st.selectbox("📌 النوع", ["دين لك", "دين عليك"],
                                          index=0 if parsed['trans_type']=="دين لك" else 1, key="v_type")
                        note = st.text_area("📝 ملاحظات", value=transcribed[:100], key="v_notes")

                        if st.button("💾 حفظ المعاملة الصوتية", type="primary", use_container_width=True):
                            if sel_id and amt > 0:
                                add_transaction(sel_id, amt, typ, note, datetime.today())
                                st.success("تم الحفظ!")
                                st.rerun()
                            else:
                                st.error("تأكد من البيانات")

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

        credit = balances[balances["الرصيد"] > 0]["الرصيد"].sum()
        debit = abs(balances[balances["الرصيد"] < 0]["الرصيد"].sum())
        c1, c2 = st.columns(2)
        c1.metric("💰 الديون لك", f"{credit:,.2f} ﷼")
        c2.metric("💸 الديون عليك", f"{debit:,.2f} ﷼")
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
