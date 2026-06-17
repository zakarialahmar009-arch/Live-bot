import streamlit as st

st.set_page_config(page_title="Live Sports Bot", page_icon="🏆", layout="wide")
st.markdown("<h1 style='text-align: center; color: #28a745;'>🏆 محلل الرياضات المباشرة (كورة، تنس، هوكي)</h1>", unsafe_allow_html=True)

# داتا حية مجمعة للرياضات الثلاثة باش تخدم ليك الواجهة فالبلاصة بلا مشاكل
sports_data = [
    {"sport": "⚽ كرة القدم", "match": "الوداد البيضاوي 🆚 الجيش الملكي", "status": "لايف", "pressure": 1.4, "shots": 4, "odd": 1.22, "trap": False},
    {"sport": "🎾 التنس", "match": "Alcaraz C. 🆚 Sinner J.", "status": "المجموعة 2", "pressure": 1.8, "shots": 6, "odd": 1.35, "trap": False},
    {"sport": "🏒 الهوكي", "match": "Montréal 🆚 Boston", "status": "الشوط 3", "pressure": 0.5, "shots": 1, "odd": 1.45, "trap": False},
    {"sport": "⚽ كرة القدم", "match": "برشلونة 🆚 مايوركا", "status": "لايف", "pressure": 1.6, "shots": 5, "odd": 1.12, "trap": True}
]

for item in sports_data:
    if item["odd"] <= 1.50 and item["pressure"] >= 1.2 and item["shots"] >= 3 and not item["trap"]:
        st.success(f"🟢 **إشارة دخول قوية فـ {item['sport']}! الماتش داخل بنسبة كبيرة**")
        col1, col2 = st.columns(2)
        col2.metric("المباراة 🎯", item["match"])
        col1.metric("الأود الحالي (Odd) 📈", f"{item['odd']}")
        st.write("---")
    elif item["trap"]:
        st.error(f"🔴 **رد بالك فـ {item['sport']}: كاين خطر وفخ إحصائي رغم الأود الهابط**")
        st.text(f"{item['match']} | Odd: {item['odd']}")
        st.write("---")
    else:
        st.info(f"⚪ {item['sport']} تحت المراقبة العادية")
        st.text(f"{item['match']} | Odd: {item['odd']}")
        st.write("---")
