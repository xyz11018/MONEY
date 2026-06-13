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
# 0. 核心引擎配置 (含偽裝瀏覽器抗封鎖)
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})

st.set_page_config(layout="wide", page_title="資產配置決策系統", page_icon="🏦")

# CSS 美化 (自動適應亮/暗模式)
st.markdown("""
    <style>
    .market-header { padding: 16px; border-radius: 10px; font-weight: 700; margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important; }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #00ffcc; }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #f97316; }
    .ticker-display { font-size: 2rem; font-weight: 900; }
    .price-display { font-size: 1rem; opacity: 0.8; }
    .data-value { font-weight: 700; }
    .action-box { background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 1. 智慧解析引擎 (包含官方字典直連)
# ==========================================
@st.cache_data(ttl=86400)
def get_tw_stock_dict():
    tw_dict = {}
    try:
        res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5)
        if res.status_code == 200:
            for item in res.json(): tw_dict[item["Name"].strip()] = f"{item['Code'].strip()}.TW"
    except: pass
    return tw_dict

def resolve_ticker(user_input):
    t = user_input.strip()
    if not t: return ""
    t_upper = t.upper()
    if t_upper in ["現金", "CASH"]: return "CASH"
    
    dynamic_tw_dict = get_tw_stock_dict()
    if t in dynamic_tw_dict: return dynamic_tw_dict[t]
    for name, ticker in dynamic_tw_dict.items():
        if t in name or name in t: return ticker
        
    if re.match(r'^\d+$', t_upper): return f"{t_upper}.TW"
    return t_upper

def get_leverage(ticker):
    t = ticker.upper()
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if t.endswith("R.TW") or t.endswith("R.TWO"): return -1.0
    if any(x in t for x in ["TQQQ", "SOXL", "UPRO", "TMF", "FNGU"]): return 3.0
    if any(x in t for x in ["QLD", "SSO", "NVDL", "TSLL"]): return 2.0
    return 1.0

# ==========================================
# 2. 市場數據獲取 (即時化)
# ==========================================
def fetch_market_data(ticker):
    if ticker == "CASH": return {"price": 1.0, "date": "即時", "ma200": 1.0, "drawdown": 0.0, "bias": 0.0}
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        price = float(t_obj.fast_info['lastPrice'])
        df = yf.download(ticker, period="2y", progress=False, session=yf_session)
        closes = df['Close'].dropna()
        high = float(df['High'].max())
        ma200 = float(closes.rolling(window=200).mean().iloc[-1])
        return {"price": price, "date": "最新", "ma200": ma200, "drawdown": ((price-high)/high)*100, "bias": ((price-ma200)/ma200)*100}
    except: return None

# ==========================================
# 3. 配置管理
# ==========================================
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f: db_data = json.load(f)
else: db_data = {"tw_portfolio": [], "us_portfolio": []}

# ==========================================
# 4. 主介面
# ==========================================
st.sidebar.title("🏦 資產配置決策系統")
app_mode = st.sidebar.radio("功能導覽：", ["🇹🇼 台股監控", "🇺🇸 美股監控", "🔍 技術分析"])
threshold = st.sidebar.slider("⚖️ 再平衡門檻 (%)", 0.0, 10.0, 2.0, 0.5)

if app_mode in ["🇹🇼 台股監控", "🇺🇸 美股監控"]:
    is_tw = (app_mode == "🇹🇼 台股監控")
    key = "tw_portfolio" if is_tw else "us_portfolio"
    st.markdown(f"<h1>{'🇹🇼' if is_tw else '🇺🇸'} {'台股' if is_tw else '美股'} 決策面板</h1>", unsafe_allow_html=True)
    
    with st.expander("⚙️ 編輯持股配置", expanded=(not db_data[key])):
        cols = st.columns([2, 1, 1])
        cols[0].markdown("**代碼 / 名稱**"); cols[1].markdown("**持股數量**"); cols[2].markdown("**目標權重%**")
        new_assets = []
        for i in range(8):
            r = st.columns([2, 1, 1])
            tk = r[0].text_input(f"tk{i}", db_data[key][i]["ticker"] if i<len(db_data[key]) else "", label_visibility="collapsed")
            sh = r[1].number_input(f"sh{i}", value=db_data[key][i]["init_shares"] if i<len(db_data[key]) else 0, label_visibility="collapsed")
            pt = r[2].number_input(f"pt{i}", value=db_data[key][i]["target_pct"] if i<len(db_data[key]) else 0, label_visibility="collapsed")
            if tk: new_assets.append({"ticker": resolve_ticker(tk), "init_shares": sh, "target_pct": pt, "leverage": get_leverage(tk)})
        if st.button("鎖定配置"):
            db_data[key] = new_assets
            with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False)
            st.rerun()

    # 運算列表
    total_val = 0
    data_list = []
    for asset in db_data[key]:
        m = fetch_market_data(asset["ticker"])
        if m:
            val = m["price"] * asset["init_shares"]
            total_val += val
            data_list.append({**asset, **m, "val": val})
    
    for item in data_list:
        real_pct = (item["val"] / total_val * 100) if total_val > 0 else 0
        diff = real_pct - item["target_pct"]
        c = st.columns([1.5, 1, 1, 1, 1, 2])
        c[0].markdown(f"<div class='ticker-display'>{item['ticker'].split('.')[0]}</div>", unsafe_allow_html=True)
        c[1].metric("權重", f"{real_pct:.1f}%")
        c[2].metric("目標", f"{item['target_pct']}%")
        c[3].markdown(f"<div class='data-label'>乖離</div><div class='data-value'>{item['bias']:.1f}%</div>", unsafe_allow_html=True)
        # 戰術建議
        tactical = "持守"
        if item['bias'] >= 25: tactical = "🚨止盈"
        elif item['price'] < item['ma200'] and item['leverage'] >= 2: tactical = "🔴降槓桿"
        elif item['drawdown'] <= -30: tactical = "🟢加碼"
        c[4].markdown(f"<div class='data-label'>戰術</div><div class='data-value'>{tactical}</div>", unsafe_allow_html=True)
        # 再平衡指示
        if abs(diff) > threshold:
            c[5].warning(f"調整: {'賣出' if diff>0 else '買進'} {abs(int((total_val*(item['target_pct']/100)-item['val'])/item['price'])):,} 股")
        else: c[5].success("平衡區間")

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
