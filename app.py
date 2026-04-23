import streamlit as st
import base64
import requests
import json

# ========== إعدادات الصفحة ==========
st.set_page_config(
    page_title="المنصة التعليمية أكس",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== تنسيقات CSS ==========
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

    * { font-family: 'Cairo', sans-serif; }

    .main-header {
        text-align: center;
        padding: 30px 0 10px 0;
    }

    .platform-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }

    .platform-subtitle {
        color: #666;
        font-size: 1rem;
        margin-bottom: 30px;
    }

    .step-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        margin-bottom: 20px;
        border-right: 4px solid #2c5364;
    }

    .step-number {
        background: linear-gradient(135deg, #0f2027, #2c5364);
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: 700;
        margin-left: 8px;
    }

    .result-box {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 24px;
        border-right: 6px solid #2c5364;
        direction: rtl;
        text-align: right;
        line-height: 2;
        margin-top: 16px;
        white-space: pre-wrap;
        overflow-x: auto;
    }

    .stButton > button {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: white;
        border-radius: 50px;
        border: none;
        padding: 14px 28px;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }

    .footer-text {
        text-align: center;
        color: #999;
        padding: 30px 0 15px 0;
        font-size: 0.85rem;
    }

    hr {
        border: 1px solid #eee;
        margin: 30px 0;
    }
</style>
""", unsafe_allow_html=True)

# ========== رأس الصفحة ==========
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.markdown('<h1 class="platform-title">🧾 المنصة التعليمية أكس</h1>', unsafe_allow_html=True)
st.markdown('<p class="platform-subtitle">للتدرب على نموذج اختبار الأستاذ صلاح باوزير</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ========== الشريط الجانبي لإعدادات API ==========
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=80)
    st.markdown("## ⚙️ الإعدادات")
    groq_api_key = st.text_input("🔑 أدخل مفتاح Groq API", type="password")
    st.markdown("---")
    st.markdown("👨‍💻 منصة أكس | غيل باوزير")
    st.markdown("📚 محاكاة لنموذج الأستاذ صلاح باوزير")

# ========== دوال Groq ==========
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def call_groq(messages, model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.3):
    if not groq_api_key:
        st.error("⚠️ الرجاء إدخال مفتاح Groq API في الشريط الجانبي")
        return None
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024
    }
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال بـ Groq: {e}")
        return None

# ========== قاعدة بيانات النموذج الأصلي (نصوص وصور مرمزة) ==========
# هنا قمنا بتضمين النص الكامل للتمرين كما ورد من الأستاذ صلاح باوزير
ORIGINAL_MODEL_TEXT = """
ميزان المراجعة في 31/12/2010م:
بضاعة أول المدة 460000 (مدين)
المشتريات 13440000 (مدين)
المبيعات 13960000 (دائن)
مردودات المشتريات 60000 (دائن)
مردودات المبيعات 200000 (مدين)
مصاريف نقل المشتريات 88000 (مدين)
الخصم المكتسب 380000 (دائن)
الخصم المسموح به 130000 (مدين)
المرتبات 440000 (مدين)
الإيجار 240000 (مدين)
م. التأمين 320000 (مدين)
إيراد أوراق مالية 140000 (دائن)
المسحوبات 280000 (مدين)
النقدية 312000 (مدين)
البنك 680000 (مدين)
المدينون 3300000 (مدين)
الدائنون 2000000 (دائن)
الأوراق المالية 1200000 (مدين)
السيارات 2400000 (مدين)
م.د.م فيها 120000 (دائن)
مجمع إهلاك السيارات 840000 (دائن)
المباني 1200000 (مدين)
مجمع إهلاك المباني 200000 (دائن)
ديون معدومة 150000 (مدين)
رأس المال 7000000 (دائن)

التسويات:
1- بضاعة آخر المدة 1800000 ريال.
2- المرتبات الشهرية 40000 ريال.
3- الإيجار الشهري 20000 ريال، عقد الإيجار يبدأ من 1/4/2010.
4- إيراد أوراق مالية مستحق 30000 ريال.
5- دين معدوم 100000 ريال.
6- تكوين م.د.م فيها بنسبة 10% من المدينين.
7- إهلاك السيارات 10% قسط ثابت.
8- إهلاك المباني 5% قسط ثابت.
9- سعر الأوراق المالية في السوق 1000000 ريال.

المطلوب:
1- قيود التسوية والإقفال.
2- إعداد الحسابات الختامية (حـ/ المتاجرة، حـ/ أ.خ).
3- إعداد الميزانية العمومية (بيان، جزئي، كلي).

الحل النموذجي المرفق:
قيود التسوية:
من حـ/ بضاعة آخر المدة 1800000 إلى حـ/ المتاجرة 1800000
من حـ/ أ.خ 480000 إلى حـ/ المرتبات 480000
من حـ/ أ.خ 180000 إلى حـ/ الإيجار 180000
من حـ/ الإيجار المقدم 60000 إلى حـ/ الإيجار 60000
من حـ/ إيراد أوراق مالية مستحقة 30000 إلى حـ/ إيراد أوراق مالية 30000
من حـ/ أ.خ 170000 إلى حـ/ إيراد أوراق مالية 170000
من حـ/ ديون معدومة 100000 إلى حـ/ المدينون 100000
من حـ/ أ.خ 250000 إلى حـ/ ديون معدومة 250000
من حـ/ أ.خ 200000 إلى حـ/ م.د.م فيها 200000
من حـ/ أ.خ 240000 إلى حـ/ مجمع إهلاك السيارات 240000
من حـ/ أ.خ 50000 إلى حـ/ مجمع إهلاك المباني 50000
من حـ/ أ.خ 20000 إلى حـ/ مخصص هبوط أسعار أوراق مالية 20000

حـ/ المتاجرة (حرف T):
مدين: بضاعة أول 460000، مشتريات 13440000، نقل مشتريات 88000، مجمل ربح 1952000
دائن: مبيعات 13960000، مردودات مشتريات 380000، بضاعة آخر 1800000

حـ/ أ.خ (حرف T):
مدين: مرتبات 480000، إيجار 180000، ديون معدومة 250000، م.د.م فيها 200000، إهلاك سيارات 240000، إهلاك مباني 50000، مخصص هبوط أسعار 20000، صافي ربح 272000
دائن: مجمل ربح 1952000، خصم مكتسب 130000، إيراد أوراق مالية 170000

الميزانية العمومية (بيان/جزئي/كلي):
الأصول: أصول ثابتة 2270000 (سيارات 2400000 - مجمع 1080000 = 1320000، مباني 1200000 - مجمع 250000 = 950000)، أصول متداولة 3882000 (نقدية 312000، بنك 680000، مدينون 288000، أوراق مالية 1000000، بضاعة 1800000، إيجار مقدم 60000، إيراد أوراق مالية مستحق 30000). إجمالي الأصول = 9332000.
الخصوم وحقوق الملكية: رأس مال 7000000 + صافي ربح 272000 = 7272000، مطلوبات (دائنون 2000000، مرتبات مستحقة 40000، إيراد عقار مقدم 20000) = 2060000. إجمالي الخصوم وحقوق الملكية = 9332000.
"""

# تحضير الصور المرمزة (يجب استبدال المسارات بصور النموذج الفعلية)
# في النسخة الحية، ترفع الصور مع التطبيق وتوضع في مجلد 'assets'
import os
ASSETS_DIR = "assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

# ========== الخطوة 1: شرح النموذج ==========
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown('<h3><span class="step-number">1</span> 📝 شرح النموذج الأصلي</h3>', unsafe_allow_html=True)
st.markdown('اضغط الزر ليقوم الأستاذ بشرح النموذج كاملاً بنفس طريقته (حرف T، قيود، جداول).')

if st.button("🧑‍🏫 اشرح لي النموذج", key="explain_btn"):
    with st.spinner("الأستاذ يجهز الشرح..."):
        # بناء المطالبة مع النموذج الكامل
        prompt_text = f"""
        أنت أستاذ محاسبة متمرس وتتبع طريقة الأستاذ صلاح باوزير في التدريس. ستشرح النموذج التالي خطوة بخطوة، تماماً كما يفعل في حصصه.
        استخدم أسلوباً ودوداً ومبسطاً، وابدأ جملتك بعبارات مثل "طيب يا بطل"، "نطبق قاعدة"، "إذن نعمل قيد كذا".
        قم بتقسيم الشرح إلى:
        1- قراءة سريعة لميزان المراجعة.
        2- شرح كل تسوية مع سبب القيد.
        3- كتابة قيود التسوية.
        4- إعداد حساب المتاجرة (حرف T) واستخراج مجمل الربح.
        5- إعداد حساب الأرباح والخسائر (حرف T) واستخراج صافي الربح.
        6- إعداد الميزانية العمومية (بيان، جزئي، كلي).

        محتوى النموذج:
        {ORIGINAL_MODEL_TEXT}
        """
        messages = [{"role": "user", "content": prompt_text}]
        response = call_groq(messages, model="llama-3.1-8b-instant")
        if response:
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.markdown(response)
            st.markdown('</div>', unsafe_allow_html=True)
            st.success("✅ تم الشرح! انتقل للخطوة 2 إذا عندك أسئلة.")
st.markdown('</div>', unsafe_allow_html=True)

# ========== الخطوة 2: المحادثة ==========
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown('<h3><span class="step-number">2</span> 💬 اسأل الأستاذ</h3>', unsafe_allow_html=True)
st.markdown('اسأل أي سؤال عن النموذج، وسيرد عليك الأستاذ مباشرة.')

if "chat_x" not in st.session_state:
    st.session_state.chat_x = []

for msg in st.session_state.chat_x:
    avatar = "🧑‍🎓" if msg["role"] == "user" else "🧑‍🏫"
    with st.chat_message(msg["role"]):
        st.write(f"{avatar} {msg['content']}")

if prompt := st.chat_input("اسأل الأستاذ..."):
    st.chat_message("user").write(f"🧑‍🎓 {prompt}")
    st.session_state.chat_x.append({"role": "user", "content": prompt})

    # إعداد السياق: النموذج الأصلي + آخر شرح تم
    context = ORIGINAL_MODEL_TEXT
    system_msg = f"""أنت أستاذ محاسبة بنفس طريقة الأستاذ صلاح باوزير. أجب عن أسئلة الطالب حول النموذج التالي:
    {context}
    كن ودوداً ومبسطاً، وشجع الطالب."""
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]
    response = call_groq(messages, model="llama-3.1-8b-instant", temperature=0.7)
    answer = response if response else "عذراً، حدث خطأ. حاول لاحقاً."
    st.chat_message("assistant").write(f"🧑‍🏫 {answer}")
    st.session_state.chat_x.append({"role": "assistant", "content": answer})
st.markdown('</div>', unsafe_allow_html=True)

# ========== الخطوة 3: اختبار توليدي ==========
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown('<h3><span class="step-number">3</span> ⚡ اختبار توليدي</h3>', unsafe_allow_html=True)
st.markdown('بعد أن فهمت الدرس، ولّد اختباراً جديداً بنفس مستوى النموذج.')

col1, col2 = st.columns(2)
with col1:
    if st.button("🎲 ولّد اختباراً جديداً", key="gen_btn"):
        with st.spinner("جاري توليد اختبار جديد..."):
            gen_prompt = f"""
            أنشئ اختباراً محاسبياً جديداً تماماً بنفس تنسيق النموذج الأصلي التالي، لكن بأرقام وبيانات مختلفة.
            حافظ على نفس أنواع الأسئلة والتسويات، واجعل الاختبار كاملاً (ميزان مراجعة، تسويات، مطلوب).
            لا تضمن الحل في هذه المرحلة.

            النموذج الأصلي:
            {ORIGINAL_MODEL_TEXT}
            """
            messages = [{"role": "user", "content": gen_prompt}]
            test_content = call_groq(messages, model="llama-3.1-8b-instant", temperature=0.7)
            if test_content:
                st.session_state.generated_test = test_content
                st.success("✅ تم توليد الاختبار! حلّه ثم اضغط 'أظهر الحل'.")

with col2:
    if st.button("✅ أظهر الحل", key="solution_btn"):
        if "generated_test" in st.session_state:
            with st.spinner("جاري تجهيز الحل..."):
                solve_prompt = f"""
                قم بحل الاختبار التالي بنفس طريقة الأستاذ صلاح باوزير بالتفصيل:
                {st.session_state.generated_test}
                """
                messages = [{"role": "user", "content": solve_prompt}]
                solution = call_groq(messages, model="llama-3.1-8b-instant")
                if solution:
                    st.markdown('<div class="result-box">', unsafe_allow_html=True)
                    st.markdown("### 📝 حل الاختبار التوليدي")
                    st.markdown(solution)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ ولّد اختباراً أولاً!")

if "generated_test" in st.session_state:
    st.markdown('<div class="result-box">', unsafe_allow_html=True)
    st.markdown("### 📝 الاختبار التوليدي")
    st.markdown(st.session_state.generated_test)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ========== تذييل ==========
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown('<p class="footer-text">🎭 المنصة التعليمية أكس | غيل باوزير - حضرموت | © 2026</p>', unsafe_allow_html=True)
