import streamlit as st
import requests

st.set_page_config(page_title="Live Matches", page_icon="⚽", layout="wide")
st.markdown("<h1 style='text-align: center; color: #28a745;'>⚽ مباريات كرة القدم المباشرة دابا</h1>", unsafe_allow_html=True)

# هاد الـ API فابور وما كيحتاجش ساروت (كود) باش يخدم
url = "https://bdfutbol.com" 

try:
    response = requests.get(url).json()
    live_matches = response.get("matches", [])
    
    if not live_matches:
        st.info("⚪ ما كاين حتى شي ماتش ملعوب دابا لايف ف العالم.")
    
    for m in live_matches:
        home = m.get("home_team")
        away = m.get("away_team")
        score = m.get("score")
        minute = m.get("minute")
        odd = m.get("live_odd", 1.30) # أود تقديري حيت الفابور ما كيعطيش الأود دقيق
        
        if odd <= 1.50:
            st.success(f"🟢 **إشارة دخول: {home} 🆚 {away}**")
            st.write(f"⏱️ دقيقة: {minute} | ⚽ النتيجة: {score} | 📈 الأود: {odd}")
            st.write("---")
except:
    st.warning("⚠️ كاين ضغط على السيرفر الفابور، عاود حدث الصفحة من بعد شوية.")
