import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import datetime
import pandas as pd
import json
import os
import re
import requests

# ==========================================
# 0. 核心抗封鎖引擎
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 1. 頁面配置與專業金融視覺優化
# ==========================================
st.set_page_config(layout="wide", page_title="資產配置決策系統", page_icon="🏦")

st.markdown("""
    <style>
    .market-header { padding: 16px 20px; border-radius: 10px; font-weight: 700; margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); letter-spacing: 1px; }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #00ffcc; }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #f97316; }
    .ticker-display { font-size: 2.2rem; font-weight: 900; line-height: 1.1; }
    .price-display { font-size: 1.1rem; font-weight: 600; opacity: 0.8; margin-top: 4px; }
    .date-display { font-size: 0.85rem; color: #94a3b8; margin-top: 2px; font-weight: 600;}
    .data-label { font-size: 0.95rem; opacity: 0.7; margin-bottom: 2px;}
    .data-value { font-size: 1.1rem; font-weight: 700; }
    .action-box { background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 10px; border-radius: 5px; margin-top: 15px; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 🧠 智慧大腦解析引擎
# ==========================================
@st.cache_data(ttl=86400)
def get_tw_stock_dict():
    tw_dict = {}
    try:
        res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5)
        if res.status_code == 200:
            for item in res.json(): tw_dict[item["Name"].strip()] = f"{item['Code'].strip()}.TW"
    except: pass
    try:
        res = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", timeout=5)
        if res.status_code == 200:
            for item in res.json(): tw_dict[item["CompanyName"].strip()] = f"{item['SecuritiesCompanyCode'].strip()}.TWO"
    except: pass
    return tw_dict

def resolve_ticker(user_input):
    t = user_input.strip()
    if not t: return ""
    t_upper = t.upper()
    if t_upper in ["現金", "CASH"]: return "CASH"
    if t_upper.startswith("^") or t_upper.endswith(".TW") or t_upper.endswith(".TWO"): return t_upper
    
    dynamic_tw_dict = get_tw_stock_dict()
    local_map = {
        "台積電": "2330.TW", "正2": "00631L.TW", "蘋果": "AAPL", "微軟": "MSFT", "輝達": "NVDA"
    }
    
    if t in local_map: return local_map[t]
    if t in dynamic_tw_dict: return dynamic_tw_dict[t]
    
    if re.match(r'^\d+$', t_upper):
        try:
            if yf.Ticker(f"{t_upper}.TW", session=yf_session).fast_info.get('lastPrice'): return f"{t_upper}.TW"
        except: pass
        return f"{t_upper}.TW"

    for name, ticker in dynamic_tw_dict.items():
        if t in name or name in t: return ticker
    return t_upper

def get_leverage(ticker):
    if ticker == "CASH": return 1.0
    t = ticker.upper()
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if t.endswith("R.TW") or t.endswith("R.TWO"): return -1.0
    us_3x = ["TQQQ", "SOXL", "UPRO", "UDOW", "TMF", "FAS", "TECL", "CURE", "NAIL", "YINN", "WEBL", "DPST", "FNGU"]
    us_2x = ["QLD", "SSO", "USD", "UWM", "MVV", "NVDL", "TSLL"]
    return 1.0

# ==========================================
# 3. 數據獲取引擎
# ==========================================
def fetch_market_data(ticker):
    if ticker == "CASH": return {"price": 1.0, "date": "即時", "ma200": 1.0, "high52w": 1.0, "drawdown": 0.0, "bias": 0.0}
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        price = float(t_obj.fast_info['lastPrice'])
        df = yf.download(ticker, period="2y", progress=False, session=yf_session)
        closes = df['Close'].dropna()
        high52w = float(df['High'].max())
        ma200 = float(closes.rolling(window=200).mean().iloc[-1]) if len(closes) >= 200 else price
        return {"price": price, "date": "最新", "ma200": ma200, "high52w": high52w, "drawdown": ((price-high52w)/high52w)*100, "bias": ((price-ma200)/ma200)*100}
    except: return None

def load_portfolio():
    data = {"tw_portfolio": [], "us_portfolio": []}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    return data

def save_portfolio(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

db_data = load_portfolio()
current_rate = fetch_market_data("TWD=X")["price"] if fetch_market_data("TWD=X") else 32.5

# ==========================================
# 4. 主介面
# ==========================================
st.sidebar.title("🏦 資產配置決策系統")
st.sidebar.markdown(f"📈 **即時匯率 USD/TWD：** `{current_rate:.2f}`")
st.sidebar.markdown("---")
app_mode = st.sidebar.radio("功能導覽：", ["🇹🇼 台股監控", "🇺🇸 美股監控", "🔍 技術分析"])
threshold = st.sidebar.slider("⚖️ 再平衡門檻 (%)", 0.0, 10.0, 2.0, 0.5)

if app_mode in ["🇹🇼 台股監控", "🇺🇸 美股監控"]:
    is_tw = (app_mode == "🇹🇼 台股監控")
    key = "tw_portfolio" if is_tw else "us_portfolio"
    st.markdown(f"<h1>{'🇹🇼' if is_tw else '🇺🇸'} {market_label} 配置決策面板</h1>", unsafe_allow_html=True)
    
    with st.expander("⚙️ 編輯持股配置", expanded=(not db_data[key])):
        cols = st.columns([2, 1, 1])
        cols[0].markdown("**代碼 / 名稱**"); cols[1].markdown("**持股數量**"); cols[2].markdown("**目標權重%**")
        new_assets = []
        for i in range(5):
            r = st.columns([2, 1, 1])
            tk = r[0].text_input(f"tk{i}", db_data[key][i]["ticker"] if i<len(db_data[key]) else "", label_visibility="collapsed")
            sh = r[1].number_input(f"sh{i}", value=db_data[key][i]["init_shares"] if i<len(db_data[key]) else 0, label_visibility="collapsed")
            pt = r[2].number_input(f"pt{i}", value=db_data[key][i]["target_pct"] if i<len(db_data[key]) else 0, label_visibility="collapsed")
            if tk: new_assets.append({"ticker": resolve_ticker(tk), "init_shares": sh, "target_pct": pt, "leverage": get_leverage(tk), "is_tw": is_tw})
        if st.button("鎖定配置"):
            db_data[key] = new_assets
            save_portfolio(db_data)
            st.rerun()

    # 運算與繪圖區
    current_data = []
    total_val = 0
    for asset in db_data[key]:
        m = fetch_market_data(asset["ticker"])
        if m:
            val = (m["price"] * (1 if asset["is_tw"] else current_rate)) * asset["init_shares"]
            total_val += val
            current_data.append({**asset, **m, "val": val})
    
    for item in current_data:
        real_pct = (item["val"] / total_val * 100) if total_val > 0 else 0
        diff = real_pct - item["target_pct"]
        c = st.columns([1.5, 1.2, 1, 1.5, 1.5, 2])
        c[0].markdown(f"<div class='ticker-display'>{item['ticker'].split('.')[0]}</div>", unsafe_allow_html=True)
        c[1].markdown(f"<div class='data-label'>股數:</div><div class='data-value'>{int(item['init_shares']):,}</div>", unsafe_allow_html=True)
        c[2].markdown(f"<div class='data-label'>權重:</div><div class='data-value'>{item['target_pct']}%</div>", unsafe_allow_html=True)
        c[3].markdown(f"<div class='data-label'>趨勢:</div><div class='data-value'>{'🔴破線' if item['now_p']<item['ma200'] else '🟢多頭'}</div>", unsafe_allow_html=True)
        # 戰術腦
        tactical = "持守"
        if item['bias'] >= 25: tactical = "🚨考慮止盈"
        elif item['now_p'] < item['ma200'] and item['leverage'] >= 2: tactical = "🔴降槓桿"
        elif item['drawdown'] <= -30: tactical = "🟢進場區間"
        c[4].markdown(f"<div class='data-label'>戰術:</div><div class='data-value' style='color:#10b981;'>{tactical}</div>", unsafe_allow_html=True)
        # 再平衡指示
        status = c[5].success if abs(diff) <= threshold else c[5].warning
        status(f"偏離: {diff:+.1f}%\n{'買進' if diff<0 else '賣出'}: {abs(int((total_val*(item['target_pct']/100) - item['val'])/item['price'])):,} 股")

elif app_mode == "🔍 技術分析":
    st.title("🔍 全球金融標的技術分析")
    q = st.text_input("輸入欲分析代碼或名稱：")
    if q:
        tk = resolve_ticker(q)
        df = yf.download(tk, period="2y", session=yf_session)
        df['MA200'] = df['Close'].rolling(200).mean()
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="年線"))
        st.plotly_chart(fig, use_container_width=True)
