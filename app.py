# -*- coding: utf-8 -*-
"""محلل الماتشات اللايف — Streamlit + API-Football (أود ما قبل الماتش + ضغط حي)"""
import requests
import streamlit as st


# ============================================================
# الإعدادات — حط المفتاح ديالك هنا
# ============================================================
API_KEY = st.secrets.get("API_KEY", "YOUR_API_KEY_HERE")  # ولا بدّلها مباشرة بالنص
PROVIDER = "DIRECT"  # "DIRECT" (api-sports.io) ولا "RAPIDAPI"

if PROVIDER == "RAPIDAPI":
    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
    HEADERS = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "api-football-v1.p.rapidapi.com"}
else:
    BASE_URL = "https://v3.football.api-sports.io"
    HEADERS = {"x-apisports-key": API_KEY}

ODD_MAX = 1.50
ATT_RATE_MIN = 1.2
SOT_RECENT_MIN = 3
RECENT_WINDOW = 15
PRESSURE_GREEN = 60

# ============================================================
# الواجهة + CSS للموبايل
# ============================================================
st.set_page_config(page_title="محلل الماتشات اللايف", page_icon="⚽", layout="centered")
st.markdown("""
<style>
.stApp { direction: rtl; background:#020617; }
.block-container { padding:0.8rem 0.8rem 3rem; max-width:480px; }
h1,h2,h3,p,span,div { color:#e2e8f0; }
.card { border-radius:18px; padding:14px; margin-bottom:12px; border:2px solid #334155; background:#0f172a; }
.card.green { border-color:#10b981; background:#022c22; }
.card.trap  { border-color:#f43f5e; background:#2c0512; }
.card.amber { border-color:#f59e0b; }
.row { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.chip { font-size:12px; font-weight:700; padding:4px 10px; border-radius:999px; }
.chip.green{background:#10b981;color:#022c22;} .chip.trap{background:#f43f5e;color:#2c0512;}
.chip.amber{background:#f59e0b;color:#3a2a02;} .chip.normal{background:#334155;color:#e2e8f0;}
.score { font-family:monospace; font-size:24px; font-weight:800; background:#020617; padding:2px 10px; border-radius:10px; }
.mkt { background:#020617; border-radius:12px; padding:8px 10px; margin:10px 0; }
.odd { font-family:monospace; font-size:18px; font-weight:800; color:#7dd3fc; }
.bar-bg { height:10px; background:#1e293b; border-radius:999px; overflow:hidden; margin:4px 0 10px; }
.bar { height:100%; border-radius:999px; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.stat { background:#020617; border-radius:12px; padding:8px; }
.stat .lbl{ font-size:11px; color:#94a3b8; } .stat .val{ font-family:monospace; font-size:17px; font-weight:700; }
.warn { background:#2c0512; color:#fecdd3; font-size:12px; border-radius:12px; padding:8px; margin-top:8px; }
.team { font-size:15px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# نداءات API
# ============================================================
def to_num(v):
    if v is None: return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace("%", "").strip()
    try: return float(s)
    except ValueError: return 0.0

def _get(endpoint, params, ttl):
    @st.cache_data(ttl=ttl, show_spinner=False)
    def call(ep, pr):
        if API_KEY == "YOUR_API_KEY_HERE": return None
        try:
            r = requests.get(f"{BASE_URL}/{ep}", headers=HEADERS, params=pr, timeout=15)
            return r.json().get("response", []) if r.status_code == 200 else None
        except requests.RequestException:
            return None
    return call(endpoint, frozenset(params.items()) and params)

def get_live():       return _get("fixtures", {"live": "all"}, 15) or []
def get_stats(fid):   return _get("fixtures/statistics", {"fixture": fid}, 25) or []
def get_odds(fid):    return _get("odds", {"fixture": fid}, 3600) or []

# ============================================================
# تحليل
# ============================================================
def parse_team(block):
    s = {i.get("type"): i.get("value") for i in block.get("statistics", [])}
    return {
        "id": block.get("team", {}).get("id"),
        "name": block.get("team", {}).get("name", "?"),
        "shots_on": to_num(s.get("Shots on Goal")),
        "shots_total": to_num(s.get("Total Shots")),
        "shots_inbox": to_num(s.get("Shots insidebox")),
        "corners": to_num(s.get("Corner Kicks")),
        "poss": to_num(s.get("Ball Possession")),
        "red": to_num(s.get("Red Cards")),
        "xg": s.get("expected_goals"),
    }

def recent_delta(fid, tid, cur, minute):
    key = f"snap_{fid}_{tid}"
    hist = st.session_state.setdefault(key, [])
    hist.append({"m": minute, "s": cur})
    hist[:] = [h for h in hist if minute - h["m"] <= RECENT_WINDOW + 5]
    base = next((h for h in hist if minute - h["m"] >= 1), None)
    if not base: return None, 0
    span = max(1, minute - base["m"])
    return {
        "shots_on": cur["shots_on"] - base["s"]["shots_on"],
        "shots_total": cur["shots_total"] - base["s"]["shots_total"],
        "shots_inbox": cur["shots_inbox"] - base["s"]["shots_inbox"],
        "corners": cur["corners"] - base["s"]["corners"],
    }, span

def att_rate(d, span):
    if not d or span <= 0: return 0.0
    return max(0.0, d["shots_total"] + d["corners"] + d["shots_inbox"]) / span

def pressure(t, d, span):
    p = min(t["poss"], 75) / 75 * 25
    so = min(t["shots_on"], 8) / 8 * 25
    rso = min(d["shots_on"], 4) / 4 * 25 if d else 0
    rt = min(att_rate(d, span), 2.0) / 2.0 * 25
    return p + so + rso + rt

def parse_prematch_odds(payload):
    """من /odds: كناخدو أول بوكميكر وكنقلبو على Match Winner + Over 0.5."""
    out = {}
    if not payload: return out
    books = payload[0].get("bookmakers", [])
    if not books: return out
    for bet in books[0].get("bets", []):
        name = (bet.get("name") or "").lower()
        for v in bet.get("values", []):
            val = str(v.get("value", "")).lower().replace(" ", "")
            odd = to_num(v.get("odd"))
            if odd <= 1.0: continue
            if "winner" in name or "result" in name:
                if val == "home": out["win_home"] = odd
                elif val == "away": out["win_away"] = odd
            elif "over/under" in name or "goals" in name:
                if val == "over0.5": out["over_0_5"] = odd
    return out

def evaluate(stats, odds, fid, minute, gh, ga):
    if len(stats) < 2: return []
    a, b = parse_team(stats[0]), parse_team(stats[1])
    for t in (a, b):
        d, span = recent_delta(fid, t["id"], t, minute)
        t["pressure"] = pressure(t, d, span)
        t["rate"] = att_rate(d, span)
        t["rsot"] = d["shots_on"] if d else 0
    leading = a if gh >= ga else b
    scored = (gh + ga) > 0
    res = []
    for key, label, actor in [("win_home", f"فوز {a['name']}", a),
                              ("win_away", f"فوز {b['name']}", b),
                              ("over_0_5", "أكثر من 0.5 هدف", a if a["pressure"] >= b["pressure"] else b)]:
        odd = odds.get(key)
        if odd is None or odd > ODD_MAX: continue
        traps = []
        if (actor["red"] >= 1): traps.append("الفريق اللي كنراهنو عليه عندو كارط حمرا")
        if leading["poss"] and leading["poss"] < 38: traps.append("الاستحواذ ديال المتقدم هبط تحت 38%")
        live_ok = actor["rate"] > ATT_RATE_MIN and actor["rsot"] >= SOT_RECENT_MIN
        press_ok = actor["pressure"] >= PRESSURE_GREEN
        if traps: status = "trap"
        elif (live_ok and press_ok) or (key == "over_0_5" and scored): status = "green"
        elif press_ok or live_ok: status = "amber"
        else: status = "normal"
        res.append({"label": label, "odd": odd, "actor": actor, "status": status,
                    "traps": traps, "implied": 100 / odd})
    return res

# ============================================================
# العرض
# ============================================================
TXT = {"green": "🟢 ماتش يستاهل المتابعة", "trap": "🔴 رد بالك: كاين خطر",
       "amber": "🟡 ضغط موجود ولكن مازال", "normal": "⚪ تحت التحليل"}
BAR = {"green": "#34d399", "trap": "#fb7185", "amber": "#fbbf24", "normal": "#64748b"}

def card_html(home, away, gh, ga, minute, ev):
    a = ev["actor"]
    xg = a["xg"] if a["xg"] is not None else "—"
    warn = f'<div class="warn">🚨 {" · ".join(ev["traps"])}</div>' if ev["traps"] else ""
    note = ('<div style="font-size:12px;color:#6ee7b7;margin-top:8px;">'
            'الأود ≤ 1.50 + ضغط قوي دابا — ماشي ضمانة ربح.</div>') if ev["status"] == "green" else ""
    return f"""
<div class="card {ev['status']}">
  <div class="row">
    <span class="chip {ev['status']}">{TXT[ev['status']]}</span>
    <span style="font-family:monospace;color:#cbd5e1;">⏱️ {int(minute)}'</span>
  </div>
  <div class="row" style="margin-top:10px;">
    <div><div class="team">{home}</div><div class="team">{away}</div></div>
    <span class="score">{int(gh)} - {int(ga)}</span>
  </div>
  <div class="mkt row"><span>🎯 {ev['label']}</span><span class="odd">{ev['odd']:.2f}</span></div>
  <div style="font-size:12px;color:#94a3b8;display:flex;justify-content:space-between;">
    <span>مؤشر الضغط دابا</span><span style="font-family:monospace;color:#e2e8f0;">{ev['actor']['pressure']:.0f}/100</span>
  </div>
  <div class="bar-bg"><div class="bar" style="width:{min(100, ev['actor']['pressure']):.0f}%;background:{BAR[ev['status']]};"></div></div>
  <div class="grid">
    <div class="stat"><div class="lbl">احتمال السمسار</div><div class="val">{ev['implied']:.0f}%</div></div>
    <div class="stat"><div class="lbl">تسديدات/مرمى (فترة)</div><div class="val">{int(ev['actor']['rsot'])}</div></div>
    <div class="stat"><div class="lbl">نشاط هجومي/دقيقة</div><div class="val">{ev['actor']['rate']:.1f}</div></div>
    <div class="stat"><div class="lbl">xG</div><div class="val">{xg}</div></div>
  </div>
  {warn}{note}
</div>"""

# ---- الرأس ----
st.markdown("<h1 style='font-size:22px;'>⚽ محلل الماتشات اللايف</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8;font-size:14px;margin-top:-8px;'>الأود ≤ 1.50 + تحليل الضغط الحالي</p>", unsafe_allow_html=True)
st.markdown("""<div style="background:#451a03;border:1px solid #b45309;border-radius:12px;padding:10px;font-size:12px;color:#fcd34d;margin-bottom:12px;">
ℹ️ <b>رد بالك:</b> ماكاين حتا رهان مضمون. الأود فيه احتمال السمسار ديجا (1÷الأود). "مؤشر الضغط" وصف للوضع الحالي ماشي ضمانة. الأود هنا ديال قبل الماتش وماكيتحركش فاللعب. لعب بمسؤولية، 18+.
</div>""", unsafe_allow_html=True)

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60000, key="refresh")
except ImportError:
    st.caption("💡 للتحديث التلقائي: زيد streamlit-autorefresh فـ requirements")

c1, c2 = st.columns([1, 1])
if c1.button("🔄 تحديث دابا", use_container_width=True):
    st.cache_data.clear(); st.rerun()
max_n = c2.slider("ماتشات بالتفصيل", 1, 15, 6)

if API_KEY == "YOUR_API_KEY_HERE":
    st.error("🔑 حط API_KEY ديالك (فالكود ولا فـ Secrets)."); st.stop()

fixtures = get_live()
if not fixtures:
    st.info("ماكاين حتا ماتش لايف دابا (ولا مشكل فالمفتاح/الاتصال)."); st.stop()

st.markdown(f"<p style='color:#cbd5e1;'>الماتشات اللايف: <b>{len(fixtures)}</b> · كنحللو {min(max_n, len(fixtures))}</p>", unsafe_allow_html=True)

greens = 0
for fx in fixtures[:max_n]:
    fid = fx["fixture"]["id"]
    minute = fx["fixture"]["status"].get("elapsed") or 0
    home, away = fx["teams"]["home"]["name"], fx["teams"]["away"]["name"]
    gh, ga = to_num(fx["goals"]["home"]), to_num(fx["goals"]["away"])
    evals = evaluate(get_stats(fid), parse_prematch_odds(get_odds(fid)), fid, minute, gh, ga)
    if not evals:
        st.markdown(f"<div class='card'><div class='row'><div class='team'>{home} ضد {away}</div>"
                    f"<span class='score'>{int(gh)} - {int(ga)}</span></div>"
                    f"<p style='color:#64748b;font-size:12px;margin-top:6px;'>⏱️ {int(minute)}' · ماكاين حتا أود ≤ {ODD_MAX}</p></div>",
                    unsafe_allow_html=True)
        continue
    for ev in evals:
        if ev["status"] == "green": greens += 1
        st.markdown(card_html(home, away, gh, ga, minute, ev), unsafe_allow_html=True)

if greens == 0:
    st.info("ماكاين حتا ماتش وصل للأخضر دابا. صبر وعاود شوف.")
st.markdown("<p style='text-align:center;color:#475569;font-size:11px;margin-top:20px;'>كيتحدّث كل 60 ثانية · لعب بمسؤولية، 18+</p>", unsafe_allow_html=True)

