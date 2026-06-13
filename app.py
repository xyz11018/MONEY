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
# 1. 頁面配置
# ==========================================
st.set_page_config(layout="wide", page_title="資金配置決策系統", page_icon="🏦")
st.markdown("""<style>
    .market-header { padding: 16px; border-radius: 10px; font-weight: 700; margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important; }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #00ffcc; }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #f97316; }
    .ticker-display { font-size: 1.8rem; font-weight: 900; }
    .data-label { font-size: 0.8rem; opacity: 0.6; }
    .data-value { font-weight: 700; font-size: 1rem; }
    .action-box { background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 10px; margin-top: 10px; border-radius: 5px; }
</style>""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 智慧解析引擎
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
    if t in ["現金", "CASH"]: return "CASH"
    if t.startswith("^") or t.endswith(".TW") or t.endswith(".TWO"): return t.upper()
    
    tw_dict = get_tw_stock_dict()
    if t in tw_dict: return tw_dict[t]
    for name, ticker in tw_dict.items():
        if t in name or name in t: return ticker
    if re.match(r'^\d+$', t): return f"{t}.TW"
    return t.upper()

def get_leverage(ticker):
    t = ticker.upper()
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if any(x in t for x in ["TQQQ", "SOXL", "UPRO", "TMF", "FNGU"]): return 3.0
    if any(x in t for x in ["QLD", "SSO", "NVDL", "TSLL"]): return 2.0
    return 1.0

# ==========================================
# 3. 資料獲取引擎
# ==========================================
def fetch_market_data(ticker):
    if ticker == "CASH": return {"price": 1.0, "ma200": 1.0, "drawdown": 0.0, "bias": 0.0, "date": "即時"}
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        price = float(t_obj.fast_info.get('lastPrice', 0))
        df = yf.download(ticker, period="2y", progress=False, session=yf_session)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        closes = df['Close'].dropna()
        high = float(df['High'].max())
        ma200 = float(closes.rolling(window=200).mean().iloc[-1])
        return {"price": price, "ma200": ma200, "drawdown": ((price-high)/high)*100, "bias": ((price-ma200)/ma200)*100, "date": "最新"}
    except: return None

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {"tw_portfolio": [], "us_portfolio": []}

db_data = load_db()
rate = fetch_market_data("TWD=X")["price"] if fetch_market_data("TWD=X") else 32.5

# ==========================================
# 4. 主介面：側邊欄與導覽
# ==========================================
st.sidebar.title("🏦 資金配置決策系統")
app_mode = st.sidebar.radio("導覽：", ["🇹🇼 台股監控", "🇺🇸 美股監控", "🔍 技術分析"])
threshold = st.sidebar.slider("再平衡門檻 (%)", 0.0, 10.0, 2.0, 0.5)

# ==========================================
# 5. 資產監控面板
# ==========================================
if app_mode in ["🇹🇼 台股監控", "🇺🇸 美股監控"]:
    is_tw = (app_mode == "🇹🇼 台股監控")
    key = "tw_portfolio" if is_tw else "us_portfolio"
    
    with st.expander("⚙️ 編輯持股配置", expanded=(not db_data[key])):
        cols = st.columns([2, 1, 1])
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

    total_val = 0
    items = []
    for asset in db_data[key]:
        m = fetch_market_data(asset["ticker"])
        if m:
            val = m["price"] * (1 if is_tw else rate) * asset["init_shares"]
            total_val += val
            items.append({**asset, **m, "val": val})
    
    for item in items:
        real_pct = (item["val"] / total_val * 100) if total_val > 0 else 0
        diff = real_pct - item["target_pct"]
        c = st.columns([1.5, 1, 1, 1, 1, 2])
        c[0].markdown(f"<div class='ticker-display'>{item['ticker'].split('.')[0]}</div>", unsafe_allow_html=True)
        c[1].metric("權重", f"{real_pct:.1f}%")
        c[2].metric("目標", f"{item['target_pct']}%")
        c[3].markdown(f"<div class='data-label'>乖離</div><div class='data-value'>{item['bias']:.1f}%</div>", unsafe_allow_html=True)
        
        tactical = "持守"
        if item['bias'] >= 25: tactical = "🚨止盈"
        elif item['price'] < item['ma200'] and item['leverage'] >= 2: tactical = "🔴降槓桿"
        elif item['drawdown'] <= -30: tactical = "🟢加碼"
        c[4].markdown(f"<div class='data-label'>戰術</div><div class='data-value'>{tactical}</div>", unsafe_allow_html=True)
        
        if abs(diff) > threshold:
            c[5].warning(f"調整: {'賣出' if diff>0 else '買進'} {abs(int((total_val*(item['target_pct']/100)-item['val'])/item['price'])):,} 股")
        else: c[5].success("平衡區間")

# ==========================================
# 6. 技術分析與戰情儀表板
# ==========================================
elif app_mode == "🔍 技術分析":
    st.title("🔍 全球金融標的技術分析")
    
    # 週期選擇器
    k_period = st.radio("選擇 K 線週期：", ["日K", "週K", "月K", "年K"], horizontal=True)
    q = st.text_input("輸入欲分析代碼或名稱：")
    
    if q:
        tk = resolve_ticker(q)
        st.caption(f"📊 系統解析為：`{tk}`")
        
        with st.spinner("載入多維度戰情儀表板與技術圖表中..."):
            # 1. 配置下載參數
            period_map = {"日K": "2y", "週K": "5y", "月K": "10y", "年K": "max"}
            interval_map = {"日K": "1d", "週K": "1wk", "月K": "1mo", "年K": "1mo"}
            
            df = yf.download(tk, period=period_map[k_period], interval=interval_map[k_period], progress=False, session=yf_session)
            
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                # 若為年K，將月資料重取樣
                if k_period == "年K":
                    try: df = df.resample('YE').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                    except: df = df.resample('Y').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                
                # 計算 RSI (14)
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 動態調整均線參數
                if k_period == "日K":
                    ma1, ma2, ma3 = 5, 20, 200
                    n1, n2, n3 = "MA5 (週線)", "MA20 (月線)", "MA200 (年線)"
                elif k_period == "週K":
                    ma1, ma2, ma3 = 4, 13, 52
                    n1, n2, n3 = "MA4 (月線)", "MA13 (季線)", "MA52 (年線)"
                elif k_period == "月K":
                    ma1, ma2, ma3 = 6, 12, 60
                    n1, n2, n3 = "MA6 (半年線)", "MA12 (年線)", "MA60 (五年線)"
                else: # 年K
                    ma1, ma2, ma3 = 3, 5, 10
                    n1, n2, n3 = "MA3 (三年線)", "MA5 (五年線)", "MA10 (十年線)"
                    
                df['MA1'] = df['Close'].rolling(ma1).mean()
                df['MA2'] = df['Close'].rolling(ma2).mean()
                df['MA3'] = df['Close'].rolling(ma3).mean()
                
                # 2. 獲取基本面資訊
                try:
                    info = yf.Ticker(tk, session=yf_session).info
                    pe = info.get('trailingPE', 0)
                    yield_pct = info.get('dividendYield', 0)
                    sector = info.get('sector', '未提供')
                    industry = info.get('industry', '')
                    sector_str = f"{sector} - {industry}" if industry else sector
                except:
                    pe, yield_pct, sector_str = 0, 0, "未提供"
                    
                rsi_val = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 0
                
                # 3. 繪製戰情儀表板
                st.markdown("### 📊 多維度戰情儀表板")
                cc1, cc2, cc3 = st.columns(3)
                
                pe_str = f"{pe:.1f} 倍" if pe and pe > 0 else "無/虧損"
                yield_str = f"{yield_pct*100:.2f} %" if yield_pct and yield_pct > 0 else "無配息"
                rsi_str = f"{rsi_val:.1f}"
                rsi_status = "🔴 超買過熱" if rsi_val > 70 else ("🟢 超賣低估" if rsi_val < 30 else "🟡 中性盤整")
                
                cc1.markdown(f"<div class='action-box'><b>🏢 產業與板塊</b><br><span style='font-size:1.1rem; color:#f8fafc;'>{sector_str}</span></div>", unsafe_allow_html=True)
                cc2.markdown(f"<div class='action-box'><b>📈 核心基本面</b><br><span style='font-size:1.1rem; color:#00ffcc;'>本益比: {pe_str} | 殖利率: {yield_str}</span></div>", unsafe_allow_html=True)
                cc3.markdown(f"<div class='action-box'><b>⚡ 短線動能 (14期 RSI)</b><br><span style='font-size:1.1rem; color:#f97316;'>{rsi_str} ({rsi_status})</span></div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 4. 繪製 K 線圖
                st.subheader(f"📈 {tk.replace('.TWO','').replace('.TW','')} 技術走勢")
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA1'], mode='lines', name=n1, line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA2'], mode='lines', name=n2, line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA3'], mode='lines', name=n3, line=dict(color='#ef4444', width=2)), row=1, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                
                # X軸範圍控制
                if k_period == "日K": range_start = df.index.max() - pd.Timedelta(days=180)
                elif k_period == "週K": range_start = df.index.max() - pd.Timedelta(days=365*2)
                elif k_period == "月K": range_start = df.index.max() - pd.Timedelta(days=365*5)
                else: range_start = df.index.min()
                
                fig.update_xaxes(range=[range_start, df.index.max()], row=1, col=1)
                fig.update_xaxes(range=[range_start, df.index.max()], row=2, col=1)
                
                # 【重要修正】利用 margin t=60 將圖表頂部壓低，徹底解決 Toolbar 遮擋問題
                fig.update_layout(
                    xaxis_rangeslider_visible=False, 
                    height=650, 
                    margin=dict(t=60, b=10, l=10, r=10), 
                    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='gray', activecolor='#00ffcc')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("⚠️ 查無資料，請確認代碼或網路狀態。")
