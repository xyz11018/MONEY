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
import numpy as np
import requests
import google.generativeai as genai

# ==========================================
# 🔑 Gemini 全球操盤決策大腦 API 讀取機制
# ==========================================
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    MY_API_KEY = ""

# ==========================================
# 0. 核心抗封鎖安全通訊引擎
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 1. 頂級法人看盤室現代化 SaaS CSS 視覺系統
# ==========================================
st.set_page_config(layout="wide", page_title="機構級量化決策終端", page_icon="🏦")

privacy_mode = st.sidebar.toggle("👁️ 隱藏金額防窺 (Privacy Mode)", value=False)

def fmt_money(val, decimals=0):
    if privacy_mode: return "****"
    if decimals == 0: return f"{int(val):,}"
    return f"{float(val):,.{decimals}f}"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

/* 機構級模塊深邃標題 */
.market-header { 
    padding: 16px 24px; border-radius: 8px; font-weight: 900; 
    font-size: 1.3rem; color: #ffffff !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    text-transform: uppercase; letter-spacing: 1.5px;
    box-shadow: 0 4px 10px -2px rgba(0,0,0,0.2);
    margin-bottom: 24px; border-left: 6px solid #8b5cf6;
}
.tw-market { border-left-color: #10b981; }
.us-market { border-left-color: #3b82f6; }

/* 華爾街科技感懸浮卡片 */
.pro-card { 
    background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; 
    padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%;
    transition: all 0.25s ease-in-out;
}
.pro-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 20px -4px rgba(0,0,0,0.08);
    border-color: #cbd5e1;
}

/* 數據核心卡片 */
.kpi-card { 
    background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; 
    padding: 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); 
    display: flex; flex-direction: column; justify-content: center;
    transition: all 0.2s ease;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 15px -3px rgba(0,0,0,0.06); }

/* 專業看盤字體與排版 */
.ticker-display { font-size: 1.85rem; font-weight: 900; line-height: 1.1; color: #0f172a; letter-spacing: -0.5px; }
.stock-name-display { font-size: 1rem; color: #475569; font-weight: 700; margin-top: 4px; margin-bottom: 8px; }
.price-display { font-size: 1.45rem; font-weight: 800; color: #0f172a; margin-top: 6px; font-variant-numeric: tabular-nums; }
.date-display { font-size: 0.8rem; color: #94a3b8; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}

.data-label { font-size: 0.75rem; color: #64748b; margin-bottom: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
.data-value { font-size: 1.2rem; font-weight: 800; color: #1e293b; font-variant-numeric: tabular-nums; }

/* 專業決策指示徽章 */
.badge-buy { display: inline-block; padding: 6px 14px; border-radius: 6px; background-color: #ecfdf5; color: #166534; font-weight: 900; font-size: 0.85rem; border: 1px solid #a7f3d0; text-transform: uppercase; letter-spacing: 0.5px;}
.badge-sell { display: inline-block; padding: 6px 14px; border-radius: 6px; background-color: #fef2f2; color: #991b1b; font-weight: 900; font-size: 0.85rem; border: 1px solid #fecaca; text-transform: uppercase; letter-spacing: 0.5px;}
.badge-hold { display: inline-block; padding: 6px 14px; border-radius: 6px; background-color: #f8fafc; color: #475569; font-weight: 900; font-size: 0.85rem; border: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;}
.badge-lev { font-size:0.75rem; color:#b45309; background:#fef3c7; padding:2px 6px; border-radius:4px; font-weight:900; border:1px solid #fde68a; margin-left:4px; }

.action-box { background: #f8fafc; border: 1px solid #e2e8f0; border-left: 6px solid #0f172a; padding: 24px; border-radius: 12px; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.03); }

.stNumberInput input { font-weight: 800 !important; color: #0f172a !important; font-size: 1.1rem !important;}
.modebar { display: none !important; }
hr { border-color: #e2e8f0; margin: 2rem 0; border-style: dashed; }

/* 導覽分頁 Tabs 法人美化 */
.stTabs [data-baseweb="tab-list"] { gap: 12px; border-bottom: 2px solid #cbd5e1; padding-bottom: 0px;}
.stTabs [data-baseweb="tab"] { height: 52px; white-space: pre-wrap; background-color: transparent; border-radius: 8px 8px 0 0; padding: 0 28px; color: #64748b; font-weight: 700; border: none; font-size: 0.95rem; letter-spacing: 0.5px;}
.stTabs [aria-selected="true"] { background-color: #0f172a !important; color: white !important; border-bottom: none !important; }
</style>
""", unsafe_allow_html=True)

# 🚀 智慧代碼正名資料庫
STOCK_NAME_DICT = {
    "6285": "啟碁", "2344": "華邦電", "2337": "旺宏", "2330": "台積電", "2454": "聯發科",
    "2317": "鴻海", "2603": "長榮", "0050": "元大台灣50", "00631L": "元大台灣50正2",
    "0056": "元大高股息", "00878": "國泰永續高股息", "6669": "緯穎", "2382": "廣達",
    "2303": "聯電", "2881": "富邦金", "2891": "中信金", "2412": "中華電", "2609": "陽明",
    "3231": "緯創", "2308": "台達電", "00919": "群益台灣精選高息", "00929": "復華台灣科技優息",
    "5498": "凱崴", "2356": "英業達", "2324": "仁寶", "3034": "聯詠", "2379": "瑞昱",
    "6548": "長華科", "00915": "凱基優選高股息30", "00713": "元大台灣高息低波",
    "00939": "統一台灣高息動能", "00940": "元大台灣價值高息", "006208": "富邦台50",
    "00679B": "元大美債20年", "00687B": "國泰20年美債", "00937B": "群益ESG投等債20+",
    "00936": "台新永續高息中小", "00772B": "中信高評級公司債",
    "AAPL": "蘋果 (Apple)", "MSFT": "微軟 (Microsoft)", "NVDA": "輝達 (NVIDIA)", 
    "TSLA": "特斯拉 (Tesla)", "AMD": "超微 (AMD)", "QQQ": "納斯達克100 ETF", 
    "VTI": "全美股市 ETF", "SCHD": "美國紅利 ETF", "VOO": "標普500 ETF", 
    "TQQQ": "納斯達克3倍做多", "QLD": "納斯達克2倍做多"
}

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 🛡️ 智慧識別與核心演算引擎
# ==========================================
def resolve_suffix(base_tk):
    if base_tk.endswith('.TW') or base_tk.endswith('.TWO'): return base_tk
    if not base_tk[0].isdigit() and not base_tk.startswith('00'): return base_tk
    for ext in [".TW", ".TWO"]:
        tk = f"{base_tk}{ext}"
        try:
            if yf.Ticker(tk, session=yf_session).fast_info.get('lastPrice'): return tk
        except: pass
    return f"{base_tk}.TW" if base_tk[0].isdigit() else base_tk

@st.cache_data(show_spinner=False, ttl=3600)
def smart_resolve_ticker(user_input, api_key=""):
    t = user_input.strip().upper()
    if not t: return "", ""
    if t in ["現金", "CASH"]: return "CASH", "台/外幣保留款"
    if t.startswith("^"): 
        idx_map = {"^TWII": "台灣加權指數", "^IXIC": "那斯達克", "^GSPC": "標普500", "^SOX": "費城半導體", "^VIX": "恐慌指數"}
        return t, idx_map.get(t, "大盤指數")

    clean_t = t.split('.')[0]
    if clean_t in STOCK_NAME_DICT: return resolve_suffix(clean_t), STOCK_NAME_DICT[clean_t]
    for tk, name in STOCK_NAME_DICT.items():
        if t == name.upper() or t in name.upper(): return resolve_suffix(tk), name

    ticker_result, name_result = "", t
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            res = model.generate_content(f"台灣股市系統。輸入：「{t}」。輸出「代碼(純數字)+後綴」及「中文簡稱」，逗號分隔。找不到輸出「無」。").text.strip().upper()
            if res != "無" and "," in res:
                ticker_result, name_result = res.split(',')[0].strip(), res.split(',')[1].strip()
        except: pass
            
    if ticker_result:
        valid_tk = resolve_suffix(ticker_result)
        if valid_tk: return valid_tk, name_result

    try:
        r = requests.get(f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(t)}&lang=zh-Hant-TW&region=TW", headers=yf_session.headers, timeout=3)
        if r.status_code == 200 and r.json().get('quotes'):
            return r.json()['quotes'][0].get('symbol', '').upper(), r.json()['quotes'][0].get('shortname', clean_t)
    except: pass
    
    if re.match(r'^[A-Z0-9]+$', clean_t): return resolve_suffix(clean_t), clean_t
    return "", ""

def get_leverage(ticker):
    if ticker == "CASH": return 0.0
    t = ticker.upper()
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if t.endswith("R.TW") or t.endswith("R.TWO"): return -1.0
    us_3x = ["TQQQ", "SOXL", "UPRO", "UDOW", "TMF", "FAS", "TECL", "CURE", "NAIL", "YINN", "WEBL", "DPST", "FNGU"]
    us_2x = ["QLD", "SSO", "USD", "UWM", "MVV", "NVDL", "TSLL"]
    if t.split('.')[0] in us_3x: return 3.0
    if t.split('.')[0] in us_2x: return 2.0
    return 1.0

# ==========================================
# 3. 📈 即時大數據同步引擎 (歷史深度 10 年)
# ==========================================
def fetch_market_data(ticker):
    if not ticker or ticker == "CASH": 
        return {"price": 1.0, "date": "最新匯率", "ma50": 1.0, "ma200": 1.0, "high52w": 1.0, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, "kd_k": 50.0, "history_close": pd.Series(dtype=float)}
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        realtime_price = float(t_obj.fast_info.get('lastPrice', 0) or 0)
        df = yf.download(ticker, period="10y", progress=False, session=yf_session)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df.dropna(subset=['Close'], inplace=True)
            closes, highs, lows = df['Close'], df['High'], df['Low']
            
            if not closes.empty: 
                price = realtime_price if realtime_price > 0 else float(closes.iloc[-1] or 0)
                date_str = "即時市場報價" if realtime_price > 0 else closes.index[-1].strftime("%Y-%m-%d")
                
                recent_highs = highs.tail(252) if len(highs) > 252 else highs
                high52w = max(float(recent_highs.max()), price)
                
                ma50 = float(closes.rolling(window=50).mean().iloc[-1] or price) if len(closes) >= 50 else price
                ma200 = float(closes.rolling(window=200).mean().iloc[-1] or price) if len(closes) >= 200 else price
                
                drawdown = ((price - high52w) / high52w) * 100 if high52w > 0 else 0.0
                bias = ((price - ma200) / ma200) * 100 if ma200 > 0 else 0.0
                
                delta = closes.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi_series = 100 - (100 / (1 + rs))
                current_rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0
                
                roll_low, roll_high = lows.rolling(window=9).min(), highs.rolling(window=9).max()
                rsv = (closes - roll_low) / (roll_high - roll_low) * 100
                current_k = float(rsv.ewm(com=2, adjust=False).mean().dropna().iloc[-1]) if not rsv.dropna().empty else 50.0

                return {
                    "price": price, "date": date_str, "ma50": ma50, "ma200": ma200, "high52w": high52w, "drawdown": drawdown, 
                    "bias": bias, "rsi": current_rsi, "kd_k": current_k, "history_close": closes
                }
    except: pass
    return None

def load_portfolio():
    default_data = {
        "global_goals": {"target_amt": 20000000, "target_years": 10},
        "schemes": {
            "🎯 台股主力配置": {"market": "TW", "lots": [], "targets": {}},
            "🎯 美股主力配置": {"market": "US", "lots": [], "targets": {}}
        }
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
                if "global_goals" not in data: data["global_goals"] = {"target_amt": 20000000, "target_years": 10}
                if "schemes" in data: return data
        except: pass
    return default_data

def save_portfolio(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

db_data = load_portfolio()

def aggregate_lots(lots, targets):
    agg = {}
    has_cash = False
    for lot in lots:
        tk = str(lot.get("ticker", "")).strip().upper()
        if not tk or tk in ["NAN", "NONE"]: continue
        if tk == "CASH": has_cash = True
        
        clean_tk = tk.split('.')[0]
        if tk not in agg:
            agg[tk] = {"ticker": tk, "init_shares": 0.0, "total_cost": 0.0, "target_pct": targets.get(clean_tk, 0.0), "earliest_buy_date": None}
        
        try: shares = float(lot.get("shares", 0))
        except: shares = 0.0
        try: price = float(lot.get("buy_price", 0))
        except: price = 0.0
        
        agg[tk]["init_shares"] += shares
        if tk == "CASH": agg[tk]["total_cost"] += shares
        else: agg[tk]["total_cost"] += shares * price
        
        d = str(lot.get("buy_date", "")).strip()
        if d and tk != "CASH":
            if agg[tk]["earliest_buy_date"] is None or d < agg[tk]["earliest_buy_date"]:
                agg[tk]["earliest_buy_date"] = d
    
    if not has_cash:
        agg["CASH"] = {"ticker": "CASH", "init_shares": 0.0, "total_cost": 0.0, "target_pct": targets.get("CASH", 0.0), "earliest_buy_date": None}

    res = []
    for tk, v in agg.items():
        if v["init_shares"] > 0:
            v["buy_price"] = 1.0 if tk == "CASH" else (v["total_cost"] / v["init_shares"])
        else: v["buy_price"] = 0.0
        v["leverage"] = get_leverage(tk)
        res.append(v)
    return res

# ==========================================
# 🎯 永豐金交割交割帳戶費用精算引擎
# ==========================================
def calculate_net_pnl_stats(item, is_tw_market, fx_rate):
    base_tk = item['ticker'].split('.')[0]
    shares = item.get('init_shares', 0)
    avg_buy_p = item.get('buy_price', 0)
    current_p = item.get('now_p', 0)
    gross_buy_amt = shares * avg_buy_p
    
    if item['ticker'].startswith("^") or item['ticker'] == "CASH":
        return gross_buy_amt, (current_p * fx_rate * shares) if item['ticker'] != "CASH" else shares, 0, 0, 0, 0
    
    tw_standard_fee_rate = 0.001425
    tw_discount = 0.2
    tw_min_fee = 1.0
    us_fee_rate = 0.0018
    us_min_fee = 3.0
    
    is_etf = len(base_tk) == 5 or len(base_tk) == 6 or base_tk.startswith('00')
    tw_tax_rate = 0.001 if is_etf else 0.003

    if is_tw_market:
        est_buy_fee = max(tw_min_fee, int(round(gross_buy_amt * tw_standard_fee_rate * tw_discount))) if shares > 0 else 0
        net_buy_cost_curr = gross_buy_amt + est_buy_fee
    else:
        est_buy_fee = max(us_min_fee, gross_buy_amt * us_fee_rate) if shares > 0 else 0
        net_buy_cost_curr = gross_buy_amt + est_buy_fee

    gross_sell_amt = shares * current_p
    if is_tw_market:
        est_sell_fee = max(tw_min_fee, int(round(gross_sell_amt * tw_standard_fee_rate * tw_discount))) if shares > 0 else 0
        est_sell_tax = int(round(gross_sell_amt * tw_tax_rate)) if shares > 0 else 0
        net_sell_amt_curr = gross_sell_amt - est_sell_fee - est_sell_tax
    else:
        est_sell_fee = max(us_min_fee, gross_sell_amt * us_fee_rate) if shares > 0 else 0
        est_sell_tax = (gross_sell_amt * 0.0000278) + min(shares * 0.000166, 8.32) if shares > 0 else 0
        net_sell_amt_curr = gross_sell_amt - est_sell_fee - est_sell_tax
        
    mult = 1.0 if is_tw_market else fx_rate
    net_buy_cost_ntd = net_buy_cost_curr * mult
    net_sell_amt_ntd = net_sell_amt_curr * mult
    total_estimated_fees_ntd = (est_buy_fee + est_sell_fee) * mult
    total_estimated_tax_ntd = est_sell_tax * mult
    
    net_pnl_ntd = net_sell_amt_ntd - net_buy_cost_ntd
    net_pnl_pct = (net_pnl_ntd / net_buy_cost_ntd * 100) if net_buy_cost_ntd > 0 else 0
    
    return net_buy_cost_ntd, net_sell_amt_ntd, total_estimated_fees_ntd, total_estimated_tax_ntd, net_pnl_ntd, net_pnl_pct

# ==========================================
# 🏛️ 總經公債殖利率曲線倒掛追蹤器
# ==========================================
@st.cache_data(show_spinner=False, ttl=14400)
def fetch_yield_curve_spread():
    try:
        tnx = yf.Ticker("^TNX", session=yf_session).fast_info.get('lastPrice', 0)
        irx = yf.Ticker("^IRX", session=yf_session).fast_info.get('lastPrice', 0)
        if tnx > 0 and irx > 0: return float(tnx - irx)
    except: pass
    return 0.25

yield_spread = fetch_yield_curve_spread()

# ==========================================
# 📊 全域宏觀指標抓取 (匯率 & VIX)
# ==========================================
twd_data = fetch_market_data("TWD=X")
current_rate = twd_data["price"] if twd_data and twd_data["price"] > 0 else 32.5

vix_data = fetch_market_data("^VIX")
current_vix = vix_data["price"] if vix_data and vix_data["price"] > 0 else 15.0

for scheme in db_data["schemes"].values():
    scheme["lots"] = [lot for lot in scheme["lots"] if str(lot.get("ticker", "")).strip().upper() not in ["", "NAN", "NONE"]]

# ==========================================
# 📊 左側邊欄：控制台面板
# ==========================================
st.sidebar.title("🏦 Quant Terminal")
st.sidebar.markdown(f"📈 **宏觀匯率 USD/TWD：** `{current_rate:.2f}`")

if yield_spread < 0: macro_color, macro_status = "#ef4444", "🚨 殖利率曲線倒掛 (全域防守)"
else: macro_color, macro_status = "#10b981", "🟢 總經擴張格局 (利差正常)"
st.sidebar.markdown(f"""
<div style='padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {macro_color}; border-radius:8px; margin-bottom:12px;'>
    <div style='color:#64748b; font-size:0.75rem; font-weight:800; margin-bottom:4px; text-transform:uppercase;'>🏛️ 美債長短天期利差 (10Y-3M)</div>
    <div style='color:#0f172a; font-size:1.15rem; font-weight:900;'>{yield_spread:+.2f}% <span style='font-size:0.75rem; color:{macro_color}; font-weight:800;'><br>{macro_status}</span></div>
</div>
""", unsafe_allow_html=True)

if current_vix >= 30: vix_color, vix_status = "#10b981", "極度恐慌 (超賣)"
elif current_vix <= 12: vix_color, vix_status = "#ef4444", "極低波動 (過熱)"
elif current_vix >= 20: vix_color, vix_status = "#f59e0b", "波動加劇"
else: vix_color, vix_status = "#64748b", "市場穩定"

st.sidebar.markdown(f"""
<div style='padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {vix_color}; border-radius:8px; margin-bottom:12px;'>
    <div style='color:#64748b; font-size:0.75rem; font-weight:800; margin-bottom:4px; text-transform:uppercase;'>📉 VIX 恐慌指數</div>
    <div style='color:#0f172a; font-size:1.3rem; font-weight:900;'>{current_vix:.2f} <span style='font-size:0.85rem; color:{vix_color}; font-weight:800;'><br>{vix_status}</span></div>
</div>
""", unsafe_allow_html=True)

cnn_val = 65 
if cnn_val >= 80: cnn_color, cnn_status = "#ef4444", "極度貪婪 (勿追高)"
elif cnn_val >= 60: cnn_color, cnn_status = "#f59e0b", "貪婪區間"
elif cnn_val <= 30: cnn_color, cnn_status = "#10b981", "恐懼 (找買點)"
else: cnn_color, cnn_status = "#64748b", "市場中立"

st.sidebar.markdown(f"""
<div style='padding:14px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {cnn_color}; border-radius:8px; margin-bottom:14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);'>
    <div style='color:#64748b; font-size:0.75rem; font-weight:800; margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>🦅 CNN 恐懼與貪婪</div>
    <div style='color:#0f172a; font-size:1.4rem; font-weight:900;'>{cnn_val} <span style='font-size:0.85rem; color:{cnn_color}; font-weight:800;'>{cnn_status}</span></div>
</div>
""", unsafe_allow_html=True)

tw_light_signal = "🟢 綠燈 (31分)"  
st.sidebar.markdown(f"""
<div style='padding:14px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid #10b981; border-radius:8px; margin-bottom:14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);'>
    <div style='color:#64748b; font-size:0.75rem; font-weight:800; margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>🚦 台股景氣對策信號</div>
    <div style='color:#0f172a; font-size:1.1rem; font-weight:900;'>{tw_light_signal}</div>
</div>
""", unsafe_allow_html=True)

api_key = MY_API_KEY
if api_key: genai.configure(api_key=api_key)

st.sidebar.markdown("---")
app_mode = st.sidebar.radio("系統導覽 (Modules)：", ["🏠 宏觀資產矩陣 (Dashboard)", "🇹🇼 台股主力量化倉位", "🇺🇸 美股主力量化倉位", "🔍 全球宏觀市場終端"])
st.sidebar.markdown("---")

# ==========================================
# 🏠 1. 宏觀資產矩陣 (Dashboard)
# ==========================================
if app_mode == "🏠 宏觀資產矩陣 (Dashboard)":
    st.markdown("<div class='market-header global-market'>🏠 全資產戰略控制台 (Global Portfolio Matrix)</div>", unsafe_allow_html=True)
    
    with st.expander("🎯 設定AUM戰略目標 (Strategic AUM Target)"):
        g_cols = st.columns(2)
        cur_target_amt = db_data["global_goals"].get("target_amt", 20000000)
        cur_target_years = db_data["global_goals"].get("target_years", 10)
        goal_amt = g_cols[0].number_input("設定總目標資產 (NTD)", min_value=0, value=int(cur_target_amt), step=100000)
        goal_yrs = g_cols[1].number_input("預估達成年數 (Years)", min_value=1, value=int(cur_target_years), step=1)
        if st.button("💾 寫入戰略目標"):
            db_data["global_goals"] = {"target_amt": goal_amt, "target_years": goal_yrs}
            save_portfolio(db_data)
            st.success("戰略目標更新完畢！")
            st.rerun()

    total_aum_ntd, tw_aum_ntd, us_aum_ntd = 0, 0, 0
    total_cost_ntd = 0
    total_div_ntd = 0
    combined_hist_df = pd.DataFrame()
    cash_total_ntd = 0
    pie_data = []

    with st.spinner("🔄 正在聚合全球資產矩陣與演算歷史軌跡..."):
        for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
            is_tw = "台股" in scheme_name
            raw_lots = db_data["schemes"][scheme_name].get("lots", [])
            raw_targets = db_data["schemes"][scheme_name].get("targets", {})
            agg_assets = aggregate_lots(raw_lots, raw_targets)
            
            for asset in agg_assets:
                m_data = fetch_market_data(asset.get("ticker", ""))
                if m_data and m_data.get("price", 0) > 0:
                    now_p = m_data["price"]
                    rate = 1.0 if is_tw else current_rate
                    init_sh = asset.get("init_shares", 0)
                    
                    if asset.get("ticker", "") == "CASH": 
                        now_val_ntd = init_sh * rate
                        asset_cost_ntd = now_val_ntd
                        cash_total_ntd += now_val_ntd
                    else: 
                        now_val_ntd = now_p * rate * init_sh
                        net_cost, _, _, _, _, _ = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw, rate)
                        asset_cost_ntd = net_cost
                        try: yield_pct = float(yf.Ticker(asset["ticker"], session=yf_session).info.get('dividendYield', 0) or 0)
                        except: yield_pct = 0.0
                        
                        hist_series = m_data.get("history_close")
                        if not hist_series.empty and not asset["ticker"].startswith("^"):
                            val_series = hist_series * init_sh * rate
                            if combined_hist_df.empty: combined_hist_df = val_series.to_frame(name=asset["ticker"])
                            else:
                                if asset["ticker"] in combined_hist_df.columns: combined_hist_df[asset["ticker"]] = combined_hist_df[asset["ticker"]].add(val_series, fill_value=0)
                                else: combined_hist_df = combined_hist_df.join(val_series.rename(asset["ticker"]), how='outer')

                    total_aum_ntd += now_val_ntd
                    if is_tw: tw_aum_ntd += now_val_ntd
                    else: us_aum_ntd += now_val_ntd
                    total_cost_ntd += asset_cost_ntd
                    total_div_ntd += (now_val_ntd * yield_pct)
                    
                    if now_val_ntd > 0:
                        pie_data.append({"Asset": asset.get("ticker", "").split('.')[0], "Value": now_val_ntd})

    if not combined_hist_df.empty:
        combined_hist_df = combined_hist_df.ffill()
        combined_hist_df['Total'] = combined_hist_df.sum(axis=1) + cash_total_ntd
        
        ytd_date = str(datetime.datetime.now().year) + "-01-01"
        one_year_ago_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        try: val_ytd = combined_hist_df['Total'].loc[ytd_date:].iloc[0]
        except: val_ytd = combined_hist_df['Total'].iloc[0]
        try: val_1y = combined_hist_df['Total'].loc[one_year_ago_date:].iloc[0]
        except: val_1y = combined_hist_df['Total'].iloc[0]
        val_now = combined_hist_df['Total'].iloc[-1]
        
        return_ytd = ((val_now / val_ytd) - 1) * 100 if val_ytd > 0 else 0
        return_1y = ((val_now / val_1y) - 1) * 100 if val_1y > 0 else 0
    else:
        return_ytd, return_1y = 0.0, 0.0

    target_amount = db_data["global_goals"].get("target_amt", 20000000)
    target_years = db_data["global_goals"].get("target_years", 10)
    shortfall = max(0, target_amount - total_aum_ntd)
    req_cagr = ((target_amount / total_aum_ntd) ** (1 / max(1, target_years)) - 1) * 100 if total_aum_ntd > 0 and target_amount > total_aum_ntd else 0.0
    cumulative_ret = ((total_aum_ntd / total_cost_ntd) - 1) * 100 if total_cost_ntd > 0 else 0.0

    st.markdown("### 🎯 總體戰略績效矩陣")
    g1, g2, g3, g4 = st.columns(4)
    g1.markdown(f"<div class='kpi-card' style='border-top: 4px solid #8b5cf6;'><div class='data-label'>設定目標資產 (Target AUM)</div><div style='font-size:1.9rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(target_amount)}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='kpi-card' style='border-top: 4px solid #ef4444;'><div class='data-label'>資產缺口 (Capital Shortfall)</div><div style='font-size:1.9rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(shortfall)}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='kpi-card' style='border-top: 4px solid #10b981;'><div class='data-label'>隱含要求回報率 (Req. CAGR)</div><div style='font-size:1.9rem; font-weight:900; color:#0f172a;'>{req_cagr:.2f}%</div></div>", unsafe_allow_html=True)
    pnl_c_global = "#10b981" if cumulative_ret >= 0 else "#ef4444"
    g4.markdown(f"<div class='kpi-card' style='border-top: 4px solid {pnl_c_global};'><div class='data-label'>淨值累積回報率 (Net Cum. Return)</div><div style='font-size:1.9rem; font-weight:900; color:{pnl_c_global};'>{cumulative_ret:+.2f}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 📊 全球板塊資金分佈與配置可視化")
    d_col1, d_col2 = st.columns([1, 1.2])
    with d_col1:
        if pie_data:
            df_pie = pd.DataFrame(pie_data)
            fig_pie = px.pie(df_pie, values='Value', names='Asset', hole=0.55, template="plotly_white")
            # 🛡️ 修復 AttributeError 採用自訂高級法人漸層色系
            custom_colors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899', '#84cc16', '#14b8a6', '#f43f5e']
            fig_pie.update_traces(textinfo='percent+label', marker=dict(colors=custom_colors))
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True, key="global_donut_chart", config={'displayModeBar': False})
        else:
            st.info("暫無持倉數據可供繪製配置圖。")
            
    with d_col2:
        kpi_html = f"""
        <div style='display:flex; flex-direction:column; gap:12px;'>
            <div class='kpi-card' style='border-left: 5px solid #8b5cf6; padding:14px; background-color:#f8fafc;'>
                <div class='data-label'>🌍 全球投資淨市值 (Total AUM)</div>
                <div style='font-size:1.8rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(total_aum_ntd)}</div>
            </div>
            <div style='display:flex; gap:12px;'>
                <div class='kpi-card' style='flex:1; border-left: 4px solid #10b981; padding:12px;'>
                    <div class='data-label'>🇹🇼 台股市值</div>
                    <div style='font-size:1.3rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(tw_aum_ntd)}</div>
                </div>
                <div class='kpi-card' style='flex:1; border-left: 4px solid #3b82f6; padding:12px;'>
                    <div class='data-label'>🇺🇸 美股市值</div>
                    <div style='font-size:1.3rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(us_aum_ntd)}</div>
                </div>
            </div>
            <div style='display:flex; gap:12px;'>
                <div class='kpi-card' style='flex:1; padding:12px;'>
                    <div class='data-label'>今年回報 (YTD)</div>
                    <div style='font-size:1.3rem; font-weight:900; color:{"#10b981" if return_ytd >=0 else "#ef4444"};'>{return_ytd:+.2f}%</div>
                </div>
                <div class='kpi-card' style='flex:1; padding:12px;'>
                    <div class='data-label'>近一年績效</div>
                    <div style='font-size:1.3rem; font-weight:900; color:{"#10b981" if return_1y >=0 else "#ef4444"};'>{return_1y:+.2f}%</div>
                </div>
            </div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)

    if not combined_hist_df.empty:
        st.markdown(f'<div class="market-header global-market" style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-left-color: #8b5cf6;">📈 全球資產歷史結算走勢</div>', unsafe_allow_html=True)
        chart_period = st.radio("時間重採樣週期：", ["日線 (Daily)", "週線 (Weekly)", "月線 (Monthly)"], horizontal=True, key="dashboard_radio")
        chart_df = combined_hist_df[['Total']].copy()
        if chart_period == "週線 (Weekly)": chart_df = chart_df.resample('W').last()
        elif chart_period == "月線 (Monthly)": chart_df = chart_df.resample('ME').last()
        
        if privacy_mode:
            chart_df['Total'] = (chart_df['Total'] / chart_df['Total'].iloc[0] - 1) * 100
            y_title = "淨值成長率 (%)"
            ht = "結算時間: %{x|%Y年%m月}<br>累積成長率: %{y:.2f}%<extra></extra>"
        else: 
            y_title = "資產淨市值 (NTD)"
            ht = "結算時間: %{x|%Y年%m月}<br>淨市值: NTD %{y:,.0f}<extra></extra>"

        fig_eq = px.line(chart_df, x=chart_df.index, y='Total', template="plotly_white")
        fig_eq.update_traces(line=dict(color='#8b5cf6', width=2.5), fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.08)', hovertemplate=ht)
        fig_eq.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), yaxis_title=y_title, xaxis_title="", hovermode="x unified")
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False}, key="dashboard_global_eq_chart")

# ==========================================
# 🇹🇼 / 🇺🇸 2. 核心操盤分頁模組 (主力量化倉位)
# ==========================================
elif app_mode in ["🇹🇼 台股主力量化倉位", "🇺🇸 美股主力量化倉位"]:
    is_tw_mode = (app_mode == "🇹🇼 台股主力量化倉位")
    market_label = "台股" if is_tw_mode else "美股"
    current_scheme_name = "🎯 台股主力配置" if is_tw_mode else "🎯 美股主力配置"
    
    st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">💼 {market_label} 核心量化倉位 (Quant Book)</div>', unsafe_allow_html=True)
    
    tab_monitor, tab_edit, tab_inject = st.tabs(["📊 動態監控儀表板 (Live Dashboard)", "📓 歷史交易日誌明細 (Trade Blotter)", "💰 增量資金注水策略 (Capital Injection)"])
    
    current_view_data = []
    local_total_val, local_total_cost, local_total_exposure = 0, 0, 0
    target_portfolio = aggregate_lots(db_data["schemes"][current_scheme_name].get("lots", []), db_data["schemes"][current_scheme_name].get("targets", {}))
    
    if target_portfolio:
        with st.spinner(f"🔄 正在同步雲端即時報價與風險 Beta 矩陣..."):
            for asset in target_portfolio:
                m_data = fetch_market_data(asset.get("ticker", ""))
                if m_data and m_data.get("price", 0) > 0:
                    now_p = m_data.get("price", 0)
                    date_str = m_data.get("date", "")
                    
                    net_cost, net_val, total_fees, total_tax, net_pnl, net_pnl_pct = calculate_net_pnl_stats(
                        {**asset, "now_p": now_p}, is_tw_mode, current_rate
                    )
                    
                    gross_now_val = net_val if asset["ticker"] != "CASH" else asset.get("init_shares", 0) * (1.0 if is_tw_mode else current_rate)
                    lev = asset.get("leverage", 1.0)
                    exposure_val = gross_now_val * lev
                    
                    local_total_val += gross_now_val
                    local_total_cost += net_cost
                    local_total_exposure += exposure_val
                    
                    current_view_data.append({
                        **asset, "now_p": now_p, "date": date_str, 
                        "now_val_ntd": gross_now_val, "net_buy_cost": net_cost, "net_real_val": net_val,
                        "exposure_val": exposure_val, "leverage": lev,
                        "net_pnl": net_pnl, "net_pnl_pct": net_pnl_pct, "total_fees": total_fees, "total_tax": total_tax,
                        "drawdown": m_data.get("drawdown", 0), "ma50": m_data.get("ma50", 0), "ma200": m_data.get("ma200", 0), "bias": m_data.get("bias", 0),
                        "rsi": m_data.get("rsi", 50), "kd_k": m_data.get("kd_k", 50),
                        "earliest_buy_date": asset.get("earliest_buy_date"),
                        "history_close": m_data.get("history_close", pd.Series(dtype=float))
                    })

    # 📓 子分頁 2: 歷史結算明細
    with tab_edit:
        st.markdown("### ⚡ 極速當日交易快速登錄 (Flash Trade Execution)")
        with st.form(key=f"quick_add_form_{market_label}"):
            qa_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5])
            qa_tk = qa_cols[0].text_input("資產代碼 / 簡稱 (如: 00631L)", placeholder="不需打後綴")
            qa_shares = qa_cols[1].number_input("成交數量 (Shares)", min_value=0, step=100, format="%d")
            qa_price = qa_cols[2].number_input("成交單價 (Price)", min_value=0.0, step=1.0)
            qa_date = qa_cols[3].date_input("交割日期 (Date)", value=datetime.date.today())
            submit_quick_add = qa_cols[4].form_submit_button("➕ 寫入建倉日誌", use_container_width=True)
            
            if submit_quick_add:
                if qa_tk and qa_shares > 0:
                    real_tk, resolved_name = smart_resolve_ticker(qa_tk, api_key)
                    if real_tk:
                        db_data["schemes"][current_scheme_name]["lots"].append({
                            "ticker": real_tk, "shares": float(qa_shares),
                            "buy_price": float(qa_price), "buy_date": qa_date.strftime("%Y-%m-%d")
                        })
                        save_portfolio(db_data)
                        st.success(f"✅ 交易確認已入帳：{resolved_name} ({real_tk}) {qa_shares}股！")
                        st.rerun()
                    else: st.error("⚠️ 無法識別此代碼商品。")
                else: st.warning("⚠️ 數量與標的不能為空。")
                    
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### 📜 完整交易明細總帳與歷史編修 (Blotter Ledger)")
        
        lots_df = pd.DataFrame(db_data["schemes"][current_scheme_name].get("lots", []))
        if lots_df.empty: lots_df = pd.DataFrame(columns=["ticker", "shares", "buy_price", "buy_date"])
        else: 
            lots_df = lots_df[["ticker", "shares", "buy_price", "buy_date"]]
            lots_df["ticker"] = lots_df["ticker"].apply(lambda x: str(x).split('.')[0] if pd.notna(x) else "")
            
        lots_df.columns = ["資產代碼 (Ticker)", "持有數量 (Shares)", "建倉均價 (Avg. Cost)", "建倉日期 (Date)"]
        edited_lots = st.data_editor(lots_df, num_rows="dynamic", use_container_width=True, key=f"editor_{market_label}")
        
        if st.button(f"📌 確認同步並寫入永豐金交割資料庫", type="primary", key=f"save_btn_{market_label}"):
            with st.spinner('正在同步儲存庫...'):
                new_lots = []
                for _, row in edited_lots.iterrows():
                    tk_raw = row["資產代碼 (Ticker)"]
                    if pd.isna(tk_raw): continue
                    tk = str(tk_raw).strip().upper()
                    if not tk or tk in ["NAN", "NONE"]: continue
                    
                    real_ticker, _ = smart_resolve_ticker(tk, api_key)
                    if real_ticker:
                        new_lots.append({
                            "ticker": real_ticker,
                            "shares": float(row["持有數量 (Shares)"] if not pd.isna(row["持有數量 (Shares)"]) else 0),
                            "buy_price": float(row["建倉均價 (Avg. Cost)"] if not pd.isna(row["建倉均價 (Avg. Cost)"]) else 0),
                            "buy_date": str(row["建倉日期 (Date)"]) if not pd.isna(row["建倉日期 (Date)"]) else ""
                        })
                db_data["schemes"][current_scheme_name]["lots"] = new_lots
                save_portfolio(db_data)
                st.success("🔒 交割總帳儲存成功！")
                st.rerun()

    with tab_monitor:
        if current_view_data:
            local_total_profit = local_total_val - local_total_cost
            local_cumulative_ret = (local_total_profit / local_total_cost) * 100 if local_total_cost > 0 else 0.0
            total_leverage_ratio = local_total_exposure / local_total_val if local_total_val > 0 else 0.0
            
            pnl_color = "#10b981" if local_total_profit >= 0 else "#ef4444"
            pnl_sign = "+" if local_total_profit >= 0 else ""
            
            st.markdown(f"""
            <div style='display:flex; gap: 16px; margin-bottom: 24px; flex-wrap:wrap;'>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #3b82f6;'>
                    <div class='data-label'>建倉總成本 (Gross Cost Basis)</div>
                    <div style='font-size:1.8rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(local_total_cost)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #8b5cf6;'>
                    <div class='data-label'>即時變現淨市值 (Mark-to-Market)</div>
                    <div style='font-size:1.8rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(local_total_val)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #f59e0b; background-color:#fffbeb;'>
                    <div class='data-label' style='color:#b45309;'>資產組合加權波動風險 (Portfolio Beta)</div>
                    <div style='font-size:2rem; font-weight:900; color:#b45309;'>{total_leverage_ratio:.2f}x</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid {pnl_color};'>
                    <div class='data-label'>未實現淨損益 (Net Unrealized PnL)</div>
                    <div style='font-size:1.8rem; font-weight:900; color:{pnl_color};'>{pnl_sign}NTD {fmt_money(local_total_profit)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid {pnl_color};'>
                    <div class='data-label'>絕對報酬率 (Net ROI)</div>
                    <div style='font-size:1.8rem; font-weight:900; color:{pnl_color};'>{pnl_sign}{local_cumulative_ret:.2f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            rebalance_threshold = st.slider("⚖️ 演算法容錯閾值 (Rebalance Threshold %)", 0.0, 10.0, 2.0, 0.5)
            
            rebalance_orders = []
            for item in current_view_data:
                mult = 1.0 if is_tw_mode else current_rate
                now_v = item.get("now_val_ntd", 0)
                tgt_p = item.get("target_pct", 0)
                lev = item.get("leverage", 1.0)
                ma50_v = item.get("ma50", 1)
                ma200_v = item.get("ma200", 1)
                
                real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                diff_pct = real_pct - tgt_p
                target_val = local_total_val * (tgt_p / 100.0)
                diff_val = target_val - now_v
                
                if abs(diff_pct) > rebalance_threshold:
                    clean_name = item.get("ticker", "").split('.')[0]
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: 
                            rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>💵 <b>現金儲備部位</b> ➡️ 建議 <span style='color:#166534; font-weight:900; background:#dcfce7; padding:4px 10px; border-radius:6px; margin-right:12px;'>注資存入 (ADD)</span> <b>{fmt_money(diff_amt)} {unit}</b></li>")
                        else: 
                            rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>💵 <b>現金儲備部位</b> ➡️ 建議 <span style='color:#991b1b; font-weight:900; background:#fee2e2; padding:4px 10px; border-radius:6px; margin-right:12px;'>部位提領 (SUB)</span> <b>{fmt_money(abs(diff_amt))} {unit}</b></li>")
                    else:
                        price_ntd = item.get("now_p", 1) * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        is_bear_cross = (ma50_v < ma200_v)
                        
                        if shares_diff > 0:
                            if lev >= 2.0 and is_bear_cross:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <b>{clean_name}</b> ➡️ 本應加碼，但目前 <span style='color:#b45309; font-weight:900; background:#fffbeb; padding:4px 10px; border-radius:6px; margin-right:12px;'>⚠️ 雙均線死叉（空頭防守）</span> <b>建議暫緩執行建倉</b>，避免波動內耗。</li>")
                            else:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <b>{clean_name}</b> ➡️ 比例不足，建議 <span style='color:#166534; font-weight:900; background:#dcfce7; padding:4px 10px; border-radius:6px; margin-right:12px; border:1px solid #a7f3d0;'>執行建倉 (BUY TO OPEN)</span> <b>{fmt_money(shares_diff)} 股</b> <span style='color:#64748b; font-size:0.9rem;'>(約 NTD {fmt_money(shares_diff * price_ntd)})</span></li>")
                        elif shares_diff < 0:
                            if lev >= 2.0 and is_bear_cross:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>📉 <b>{clean_name}</b> ➡️ 比例過高且 <span style='color:#991b1b; font-weight:900; background:#fef2f2; padding:4px 10px; border-radius:6px; margin-right:12px; border:1px solid #fecaca;'>🚨 槓桿破線強烈平倉</span> 建議加速 <span style='color:#991b1b; font-weight:900; background:#fee2e2; padding:4px 10px; border-radius:6px; margin-right:12px;'>執行平倉 (SELL TO CLOSE)</span> <b>{fmt_money(abs(shares_diff))} 股</b></li>")
                            else:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>📉 <b>{clean_name}</b> ➡️ 比例過高，建議 <span style='color:#991b1b; font-weight:900; background:#fee2e2; padding:4px 10px; border-radius:6px; margin-right:12px;'>執行平倉 (SELL TO CLOSE)</span> <b>{fmt_money(abs(shares_diff))} 股</b></li>")
            
            if rebalance_orders:
                st.markdown(f"<div class='action-box' style='background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #f59e0b; padding:24px; border-radius:12px; margin-bottom:30px; box-shadow:0 4px 6px rgba(0,0,0,0.05);'><h4 style='color:#b45309; font-weight:900; margin-top:0; font-size:1.3rem; letter-spacing:0.5px;'>⚡ 演算法再平衡平衡指令單 (Algorithmic Balancing Orders)</h4><div style='color:#64748b; margin-bottom:16px; font-size:0.95rem; font-weight:600;'>已綜合評估「資產偏離度」與「中長線移動平均線（50MA/200MA）」交叉狀態，請依據下表指引操作：</div><ul style='margin-bottom:0; padding-left:0; list-style-type:none;'>{''.join(rebalance_orders)}</ul></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='action-box' style='background:#f0fdf4; border:1px solid #bbf7d0; border-left:6px solid #10b981; padding:24px; border-radius:12px; margin-bottom:30px; box-shadow:0 4px 6px rgba(0,0,0,0.05);'><h4 style='color:#166534; font-weight:900; margin-top:0; font-size:1.3rem; letter-spacing:0.5px;'>✅ 資金權重配置穩健 (Risk Balanced)</h4><div style='color:#166534; font-size:1rem; font-weight:600;'>目前全體底層現貨與槓桿部位均完美收斂於演算法安全區間。</div></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            for item in current_view_data:
                c = st.columns([1.5, 1.6, 1.5, 1.2, 1.3, 2.9])
                
                now_v = item.get("now_val_ntd", 0)
                lev = item.get("leverage", 1.0)
                tgt_p = item.get("target_pct", 0)
                a_cost = item.get("asset_cost", 0)
                n_p = item.get("now_p", 0)
                ma50_v = item.get("ma50", 1)
                ma200_v = item.get("ma200", 1)
                
                real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                
                _, zh_name = smart_resolve_ticker(item.get("ticker", ""), api_key)
                if not zh_name or zh_name == item.get("ticker"): zh_name = STOCK_NAME_DICT.get(item.get("ticker", "").split('.')[0], item.get("ticker", ""))
                
                clean_name = item.get("ticker", "").split('.')[0]
                
                if item.get("ticker") == "CASH":
                    c[0].markdown(f"<div class='ticker-display'>💵 現金部位</div><div class='stock-name-display'>台/外幣保留款 (CASH)</div><div class='price-display'>TWD/USD</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>持倉帳戶餘額 (Account Bal.):</div><div class='data-value'>NTD {fmt_money(item.get('net_buy_cost', 0))}</div><div class='data-label' style='margin-top:12px;'>法幣淨等值 (Fiat Val.):</div><div class='data-value'>NTD {fmt_money(now_v)}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>未實現損益 (Net Pnl):</div><div class='data-value' style='color:#94a3b8;'>---</div><div class='data-label' style='margin-top:12px;'>絕對報酬率 (Return):</div><div class='data-value' style='color:#94a3b8;'>---</div>", unsafe_allow_html=True)
                    c[3].markdown(f"<div class='data-label'>風險波動係數 (Beta):</div><div class='data-value' style='color:#10b981;'>0.00x (避險資產)</div><div class='data-label' style='margin-top:12px;'>最大回撤 (Max DD):</div><div class='data-value' style='color:#94a3b8;'>0.0%</div>", unsafe_allow_html=True)
                    c[4].markdown(f"<div class='data-label'>乖離率 (BIAS):</div><div class='data-value' style='color:#94a3b8;'>---</div><div class='data-label' style='margin-top:12px;'>🧠 終端戰術 (Tactics):</div><div class='data-value' style='color:#64748b;'>現金水庫調度</div>", unsafe_allow_html=True)
                else:
                    pnl_ntd = item.get('net_pnl', 0)
                    pnl_pct = item.get('net_pnl_pct', 0)
                    item_pnl_color = "#10b981" if pnl_ntd >= 0 else "#ef4444"
                    item_pnl_sign = "+" if pnl_ntd >= 0 else ""
                    
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='stock-name-display'>{zh_name}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {n_p:.2f}</div><div class='date-display'>平均建倉成本: {item.get('buy_price',0):.2f}</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>建倉成本 (Cost Basis):</div><div class='data-value'>NTD {fmt_money(item.get('net_buy_cost', 0))}</div><div class='data-label' style='margin-top:12px;'>預估淨變現市值 (Value):</div><div class='data-value'>NTD {fmt_money(item.get('net_real_val', 0))}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>未實現損益 (Net Pnl):</div><div class='data-value' style='color:{item_pnl_color};'>{item_pnl_sign}{fmt_money(pnl_ntd)}</div><div class='data-label' style='margin-top:12px;'>絕對報酬率 (Return):</div><div class='data-value' style='color:{item_pnl_color};'>{item_pnl_sign}{pnl_pct:.2f}%</div>", unsafe_allow_html=True)
                    
                    is_bear = n_p < item.get('ma200', 0)
                    trend_tag = "<span style='color:#ef4444; font-weight:900;'>🔴 空頭破線 (Bear)</span>" if is_bear else "<span style='color:#10b981; font-weight:900;'>🟢 多頭排列 (Bull)</span>"
                    dd_color = "#ef4444" if item.get('drawdown', 0) < -20 else ("#f59e0b" if item.get('drawdown', 0) < -10 else "#64748b")
                    c[3].markdown(f"<div class='data-label'>趨勢掃描 (MA200):</div><div>{trend_tag}</div><div class='data-label' style='margin-top:12px;'>高點回撤 (Drawdown):</div><div class='data-value' style='color:{dd_color};'>{item.get('drawdown',0):.1f}%</div>", unsafe_allow_html=True)
                    
                    bias_color = "#ef4444" if item.get('bias', 0) >= 25 else ("#f59e0b" if item.get('bias', 0) >= 15 else ("#10b981" if item.get('bias', 0) <= -15 else "#64748b"))
                    k_val = item.get("kd_k", 50.0)
                    rsi_val = item.get("rsi", 50.0)
                    tactical_action = "<span style='color:#64748b;'>⚖️ 戰略中立持有</span>"
                    if is_bear and lev >= 2.0: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🛑 破線停損 (STOP)</span>"
                    elif k_val < 20 or rsi_val < 30: tactical_action = "<span style='color:#10b981; font-weight:900;'>🟢 逢低加碼 (BUY)</span>"
                    elif k_val > 80: tactical_action = "<span style='color:#f59e0b; font-weight:900;'>⚠️ 高檔鈍化 (WATCH)</span>"
                    elif item.get("bias", 0) >= 25: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🚨 獲利解平 (TAKE)</span>"
                    c[4].markdown(f"<div class='data-label'>乖離率掃描 (BIAS):</div><div class='data-value' style='color:{bias_color};'>{item.get('bias',0):+.1f}%</div><div class='data-label' style='margin-top:12px;'>🧠 終端戰術 (Tactics):</div><div style='font-size:0.95rem;'>{tactical_action}</div>", unsafe_allow_html=True)

                with c[5]:
                    st.markdown("<div class='data-label'>戰略目標權重 (%) ✍️</div>", unsafe_allow_html=True)
                    clean_tk_tgt = item.get('ticker', '').split('.')[0]
                    new_tgt = st.number_input(
                        "Target", value=float(tgt_p), step=1.0, min_value=0.0, max_value=100.0,
                        key=f"tgt_{current_scheme_name}_{clean_tk_tgt}", label_visibility="collapsed"
                    )
                    
                    if new_tgt != float(tgt_p):
                        db_data["schemes"][current_scheme_name]["targets"][clean_tk_tgt] = new_tgt
                        save_portfolio(db_data)
                        st.rerun()

                    diff = real_pct - new_tgt
                    target_val = local_total_val * (new_tgt / 100.0)
                    diff_val = target_val - now_v
                    
                    box_bg = "#f8fafc" if abs(diff) <= rebalance_threshold else "#fffbeb"
                    box_border = "#e2e8f0" if abs(diff) <= rebalance_threshold else "#fde68a"
                    title_color = "#0f172a" if abs(diff) <= rebalance_threshold else "#92400e"
                    title_text = "✅ 配置達模型最佳化" if abs(diff) <= rebalance_threshold else f"⚠️ 占比偏離 {diff:+.1f}%"
                    
                    progress_html = f"<div style='margin-top:8px; margin-bottom:6px; font-size:0.8rem; color:#64748b; font-weight:700;'>現時占比 {real_pct:.1f}% / 戰略目標 {new_tgt}%</div><div style='width: 100%; background-color: #e2e8f0; border-radius: 99px; height: 10px; overflow:hidden;'><div style='width: {min(100, real_pct)}%; background-color: {'#10b981' if abs(diff) <= rebalance_threshold else '#f59e0b'}; height: 100%; border-radius: 99px;'></div></div>"
                    
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-buy'>ADD 注資</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a; margin-left:8px;'>{fmt_money(diff_amt)} {unit}</span></div>"
                        elif diff_amt < 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-sell'>SUB 提領</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a; margin-left:8px;'>{fmt_money(abs(diff_amt))} {unit}</span></div>"
                        else: action_msg = f"<div style='margin-top:16px;'><span class='badge-hold'>無指示</span></div>"
                    else:
                        price_ntd = n_p * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        if shares_diff > 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-buy'>BUY 執行建倉</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a; margin-left:8px;'>{fmt_money(shares_diff)} 股</span></div>"
                        elif shares_diff < 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-sell'>SELL 執行平倉</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a; margin-left:8px;'>{fmt_money(abs(shares_diff))} 股</span></div>"
                        else: action_msg = f"<div style='margin-top:16px;'><span class='badge-hold'>無指示</span></div>"

                    action_html = f"<div class='pro-card' style='background-color:{box_bg}; border-color:{box_border}; padding:18px; margin-top:4px;'><div style='color:{title_color}; font-weight:800; font-size:0.95rem; text-transform:uppercase;'>{title_text}</div>{progress_html}{action_msg}</div>"
                    st.markdown(action_html, unsafe_allow_html=True)

                if item.get("ticker") != "CASH":
                    with st.expander(f"📈 展開 {clean_name} 歷史淨利累積軌跡分析 (Profit Slicing)"):
                        tf_col, _ = st.columns([1.2, 2])
                        tf = tf_col.radio("圖表重採樣週期：", ["日線", "週線", "月線", "年線"], horizontal=True, key=f"tf_chart_{market_label}_{item.get('ticker')}")
                        
                        hist_close = item.get("history_close", pd.Series(dtype=float))
                        buy_date = item.get("earliest_buy_date")
                        
                        if not hist_close.empty:
                            if buy_date:
                                try:
                                    pd.to_datetime(buy_date)
                                    hist_close = hist_close.loc[buy_date:]
                                except: pass
                            else:
                                one_yr_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
                                hist_close = hist_close.loc[one_yr_ago:]
                                
                            if not hist_close.empty:
                                if tf == "週線": hist_close = hist_close.resample('W').last()
                                elif tf == "月線": hist_close = hist_close.resample('ME').last()
                                elif tf == "年線": 
                                    try: hist_close = hist_close.resample('YE').last()
                                    except: hist_close = hist_close.resample('Y').last()
                                
                                stock_pnl_series = (hist_close - item.get("buy_price",0)) * item.get("init_shares",0) * mult
                                pnl_df = stock_pnl_series.to_frame(name="Profit_Value")
                                
                                if privacy_mode:
                                    pnl_df["Display_Value"] = ((hist_close - item.get("buy_price",0)) / (item.get("buy_price",1) if item.get("buy_price",0) > 0 else 1)) * 100
                                    y_axis_label = "淨利回報率 (%)"
                                    ht = "結算時間: %{x|%Y年%m月}<br>累積回報率: %{y:.2f}%<extra></extra>"
                                else:
                                    pnl_df["Display_Value"] = pnl_df["Profit_Value"]
                                    y_axis_label = "未實現淨利 (NTD)"
                                    ht = "結算時間: %{x|%Y年%m月}<br>未實現淨利: NTD %{y:,.0f}<extra></extra>"
                                    
                                fig_pnl = px.line(pnl_df, x=pnl_df.index, y="Display_Value", template="plotly_white")
                                curve_color = '#10b981' if pnl_df["Display_Value"].iloc[-1] >= 0 else '#ef4444'
                                fig_pnl.update_traces(line=dict(color=curve_color, width=2.5), fill='tozeroy', fillcolor=f"rgba({ '16,185,129' if curve_color=='#10b981' else '239,68,68' }, 0.08)", hovertemplate=ht)
                                fig_pnl.update_layout(height=300, margin=dict(t=15, b=15, l=15, r=15), yaxis_title=y_axis_label, xaxis_title="", hovermode="x unified")
                                st.plotly_chart(fig_pnl, use_container_width=True, config={'displayModeBar': False}, key=f"pnl_chart_{market_label}_{item.get('ticker')}_{tf}")
                            else: st.info("該標的在交割日期後無有效報價，無法進行回測追蹤。")
                        else: st.info("無有效歷史價格陣列。")

                st.markdown("<hr>", unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🤖 AI 量化戰略兵推 (Quant Intelligence)")
            st.info("💡 點擊下方按鈕，AI 將自動對持倉偏離與技術指標(均線/KD/RSI)進行全域動態對沖推演。")
            if st.button(f"✨ 啟動 Gemini 演算法兵推", key="manual_portfolio_ai_btn", type="primary", use_container_width=True):
                if not api_key: st.warning("⚠️ 系統連線失敗：請先配置您的 Gemini API Key。")
                else:
                    with st.spinner("🧠 神經網絡戰略推演中 (Connecting to Quant Engine...)"):
                        portfolio_summary = f"【美債 10Y-3M 利差狀態】: {yield_spread:+.2f}% ({'倒掛警戒中' if yield_spread < 0 else '擴張格局正軌'})\n\n"
                        for item in current_view_data:
                            tk_name = item.get('ticker', '').split('.')[0]
                            now_v = item.get("now_val_ntd", 0)
                            real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                            diff_pct = real_pct - item.get('target_pct', 0)
                            portfolio_summary += (
                                f"🔹 標的：{tk_name} (波動風險: {item.get('leverage',1.0)}x)\n"
                                f"   - 戰略狀態：目標 {item.get('target_pct', 0)}% / 實際 {real_pct:.1f}% (偏離 {diff_pct:+.1f}%)\n"
                                f"   - 均線位階：50MA = {item.get('ma50',0):.2f} / 200MA = {item.get('ma200',0):.2f} ({'黃金交叉多頭' if item.get('ma50',0) > item.get('ma200',0) else '死亡交叉空頭'})\n"
                                f"   - 技術動能：14期RSI {item.get('rsi', 50):.1f} / 乖離率 {item.get('bias', 0):+.1f}%\n\n"
                            )
                        prompt = f"你是對沖基金首席操盤手。請根據數據下達指令：\n{portfolio_summary}\n請給出：1. 宏觀組合與總經風控診斷 2. 均線死叉標的精確操盤指令 3. 演算法再平衡平衡調配。用專業繁體金融術語回覆。"
                        try:
                            model = genai.GenerativeModel("gemini-3.5-flash")
                            st.info(model.generate_content(prompt).text)
                        except:
                            model = genai.GenerativeModel("gemini-2.5-flash")
                            st.info(model.generate_content(prompt).text)

    # 💰 子分頁 3: 增量注水策略
    with tab_inject:
        st.markdown("### 💰 增量資金注水策略 (Capital Injection Strategy)")
        st.info("💡 **模組說明**：當帳戶獲得額外現金流時，輸入增量金額，演算模型將自動產出「收斂偏離佔比」的最優化建倉比例。")
        add_cash = st.number_input("設定預定注水本金 (NTD)", min_value=0, value=0, step=10000, format="%d")
        
        if add_cash > 0 and current_view_data:
            st.markdown("<div class='action-box'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:#0f172a; font-weight:900; margin-top:0;'>🎯 演算法注水配置指令：</h4>", unsafe_allow_html=True)
            ideal_total_val = local_total_val + add_cash
            buy_list = []
            for item in current_view_data:
                ideal_target_ntd = ideal_total_val * (item.get("target_pct", 0) / 100.0)
                shortfall_ntd = ideal_target_ntd - item.get("now_val_ntd", 0)
                if shortfall_ntd > 0:
                    if item.get("ticker") == "CASH":
                        buy_units = shortfall_ntd / (1.0 if is_tw_mode else current_rate)
                        buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>💵 <span style='font-weight:900; width:120px; display:inline-block;'>保留資金部位</span>：建議存入 <b>{fmt_money(buy_units)}</b> {'元' if is_tw_mode else '美元'}</li>")
                    elif item.get("ticker", "").startswith("^"): 
                        buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>📊 <span style='font-weight:900; width:120px; display:inline-block;'>{item.get('ticker', '')}</span>：建議額外加碼配置 <b>NTD {fmt_money(shortfall_ntd)}</b></li>")
                    else:
                        price_ntd = item.get("now_p", 1) if is_tw_mode else (item.get("now_p", 1) * current_rate)
                        shares_to_buy = int(shortfall_ntd / price_ntd) if price_ntd > 0 else 0
                        clean_name = item.get("ticker", "").split('.')[0]
                        if shares_to_buy > 0: 
                            buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{clean_name}</span>：建議 <span style='color:#166534; font-weight:800; background:#dcfce7; padding:4px 10px; border-radius:6px;'>執行建倉 (BUY)</span> <span style='font-weight:900; margin-left:8px;'>{fmt_money(shares_to_buy)} 股</span> <span style='color:#64748b; font-size:0.95rem; margin-left:12px;'>(約消耗淨資產 NTD {fmt_money(shares_to_buy * price_ntd)})</span></li>")
            
            if buy_list: st.markdown(f"<ul style='list-style-type:none; padding-left:0;'>{''.join(buy_list)}</ul>", unsafe_allow_html=True)
            else: st.write("目前資產池無顯著配置缺口。")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 🔍 分頁：全球宏觀市場終端
# ==========================================
elif app_mode == "🔍 全球宏觀市場終端":
    st.sidebar.header("🌍 宏觀大盤快搜 (Global Indices)")
    market_choice = st.sidebar.radio("快速切換分析標的：", ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"])

    st.markdown("<div class='market-header global-market'>📊 全球宏觀市場終端 (Global Macro Terminal)</div>", unsafe_allow_html=True)
    k_period = st.radio("選擇量化回測週期 (Timeframe)：", ["日K", "週K", "月K", "年K"], horizontal=True)
    st.markdown("---")

    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = ""
    
    if market_choice == "自訂輸入個股": 
        target_to_parse = st.text_input("輸入欲調研的資產代碼 (輸入完畢按 Enter)：", value="", placeholder="例如：2330 或 QQQ")
    else: target_to_parse = default_ticker
    
    if target_to_parse:
        ticker_input, zh_name = smart_resolve_ticker(target_to_parse, api_key)
        
        if ticker_input:
            try:
                with st.spinner("連接雲端伺服器，載入量化數據矩陣..."):
                    period_map = {"日K": "2y", "週K": "5y", "月K": "10y", "年K": "max"}
                    interval_map = {"日K": "1d", "週K": "1wk", "月K": "1mo", "年K": "1mo"}
                    df = yf.download(ticker_input, period=period_map[k_period], interval=interval_map[k_period], progress=False, session=yf_session)
                    
                    if not df.empty:
                        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                        df.dropna(subset=['Close'], inplace=True)
                        
                        delta = df['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        df['RSI'] = 100 - (100 / (1 + rs))
                        
                        if k_period == "日K": ma1, ma2, ma3, n1, n2, n3 = 5, 20, 200, "MA5", "MA20", "MA200"
                        else: ma1, ma2, ma3, n1, n2, n3 = 5, 10, 50, "MA5", "MA10", "MA50"
                            
                        df['MA1'] = df['Close'].rolling(ma1).mean()
                        df['MA2'] = df['Close'].rolling(ma2).mean()
                        df['MA3'] = df['Close'].rolling(ma3).mean()
                        
                        rsi_val = float(df['RSI'].dropna().iloc[-1]) if not df['RSI'].dropna().empty else 50.0
                        rsi_status = "🔴 過熱超買 (OVERBOUGHT)" if rsi_val > 70 else ("🟢 超跌低估 (OVERSOLD)" if rsi_val < 30 else "🟡 盤整 (NEUTRAL)")
                        
                        last_close = float(df['Close'].dropna().iloc[-1]) if not df['Close'].dropna().empty else 0.0
                        ma200_val = float(df['MA3'].dropna().iloc[-1]) if not df['MA3'].dropna().empty else last_close
                        high_52w = float(df['High'].max()) if not pd.isna(df['High'].max()) else last_close
                        dd_pct = ((last_close - high_52w) / high_52w) * 100 if high_52w > 0 else 0.0

                        st.markdown("### 📊 量化多維戰略儀表板 (Market Metrics)")
                        cc1, cc2, cc3 = st.columns(3)
                        
                        if ticker_input.startswith("^"):
                            cc1.markdown(f"<div class='pro-card'><div class='data-label'>📈 最新大盤指數點位</div><div class='data-value' style='font-size:1.8rem;'>{fmt_money(last_close)} <span style='font-size:1rem; color:#64748b;'>點</span></div><div style='color:#64748b; font-size:0.85rem; margin-top:8px;'>長線牛熊分界 ({n3}): {fmt_money(ma200_val)}</div></div>", unsafe_allow_html=True)
                            cc2.markdown(f"<div class='pro-card'><div class='data-label'>📉 歷史極值與波段回撤</div><div class='data-value' style='font-size:1.8rem; color:#ef4444;'>{dd_pct:.2f}%</div><div style='color:#64748b; font-size:0.85rem; margin-top:8px;'>歷史頂部估值: {fmt_money(high_52w)} 點</div></div>", unsafe_allow_html=True)
                        else:
                            try:
                                info = yf.Ticker(ticker_input, session=yf_session).info
                                pe_str = f"{float(info.get('trailingPE', 0) or 0):.1f} 倍"
                                yd_str = f"{float(info.get('dividendYield', 0) or 0)*100:.2f} %"
                                sec_str = info.get('sector', '未提供')
                            except: pe_str, yd_str, sec_str = "無/虧損", "無配息", "未提供"
                            cc1.markdown(f"<div class='pro-card'><div class='data-label'>🏢 系統歸屬板塊 (Sector)</div><div class='data-value' style='font-size:1.8rem;'>{sec_str}</div></div>", unsafe_allow_html=True)
                            cc2.markdown(f"<div class='pro-card'><div class='data-label'>🏦 核心基本面矩陣 (Fundamentals)</div><div class='data-value' style='font-size:1.6rem;'>PE: {pe_str}</div><div style='color:#64748b; font-size:1rem; font-weight:700; margin-top:4px;'>股息率 (Yield): {yd_str}</div></div>", unsafe_allow_html=True)
                        
                        cc3.markdown(f"<div class='pro-card'><div class='data-label'>⚡ 短線技術動能掃描 (RSI)</div><div class='data-value' style='font-size:1.8rem;'>{rsi_val:.1f}</div><div style='color:#0f172a; font-size:1rem; font-weight:700; margin-top:4px;'>系統診斷: {rsi_status}</div></div>", unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        clean_title = ticker_input.split('.')[0]
                        st.markdown(f"<h3 style='margin-bottom: 20px; border-left: 6px solid #3b82f6; padding-left: 12px;'>📈 {clean_title} {zh_name} 歷史技術軌跡 (Price Action)</h3>", unsafe_allow_html=True)
                        
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA1'], mode='lines', name=n1, line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA2'], mode='lines', name=n2, line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA3'], mode='lines', name=n3, line=dict(color='#ef4444', width=2)), row=1, col=1)
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="市場成交量", marker_color="#cbd5e1"), row=2, col=1)
                        
                        if privacy_mode:
                            fig.update_yaxes(showticklabels=False, row=1, col=1)
                            fig.update_yaxes(showticklabels=False, row=2, col=1)
                            
                        fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_white", margin=dict(t=30, b=10, l=10, r=10), hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"terminal_stock_chart_{clean_title}")

                        tab1, tab2 = st.tabs(["📈 AI 神經網絡戰略分析", "📰 全球市場事件與情緒掃描"])
                        
                        with tab1:
                            st.markdown("### 🤖 標的資產量化解析 (AI Analysis)")
                            if st.button("✨ 啟動 Gemini 神經網絡推演", key="ai_btn", type="secondary", use_container_width=True):
                                if not api_key: st.warning("⚠️ 請先於系統後台掛載 Gemini API Key。")
                                else:
                                    with st.spinner("🧠 連接 AI 運算矩陣進行深度解析..."):
                                        prompt = f"你是華爾街頂尖機構分析師。請根據數據產出專屬戰略洞察：標的：{clean_title} {zh_name} | 結算價：{last_close:.2f} | RSI：{rsi_val:.1f}，跌破長天期均線需提示風險，請用專業繁體中文給出操作建議。"
                                        try:
                                            model = genai.GenerativeModel("gemini-3.5-flash")
                                            st.info(model.generate_content(prompt).text)
                                        except:
                                            model = genai.GenerativeModel("gemini-2.5-flash")
                                            st.info(model.generate_content(prompt).text)

                        with tab2:
                            st.markdown(f"### 📰 {clean_title} 核心市場事件觸發 (Catalysts)")
                            try: news_list = yf.Ticker(ticker_input, session=yf_session).news[:5]
                            except: news_list = []
                                
                            if news_list:
                                news_text_for_ai = ""
                                for i, n in enumerate(news_list):
                                    title = n.get('title', '無標題')
                                    publisher = n.get('publisher', '未知新聞源')
                                    link = n.get('link', '#')
                                    st.markdown(f"**{i+1}. [{title}]({link})** _(來源: {publisher})_")
                                    news_text_for_ai += f"標題: {title}\n來源: {publisher}\n\n"
                                
                                st.markdown("---")
                                if st.button("✨ 讓 Gemini 總結市場多空動能情緒", key="news_ai_btn", type="primary", use_container_width=True):
                                    if not api_key: st.warning("⚠️ 系統連線失敗：未偵測到 API Key。")
                                    else:
                                        with st.spinner("🧠 啟動事件驅動分析引擎..."):
                                            news_prompt = f"請判讀以下新聞的隱含多空情緒：\n\n{news_text_for_ai}"
                                            try:
                                                model = genai.GenerativeModel("gemini-2.5-flash")
                                                st.info(model.generate_content(news_prompt).text)
                                            except Exception as e: st.error("❌ 運算模組解析失敗。")
                            else: st.info("目前資料庫無收錄該資產近期重點催化劑事件。")
            except Exception as e: st.error(f"❌ 模組載入中斷，底層錯誤：{str(e)}")
