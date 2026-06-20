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
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# ==========================================
# 🔑 Gemini 與 LINE Notify 權限機制
# ==========================================
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    MY_API_KEY = ""

def send_line_notify(token, msg):
    if not token or token == "": return False
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {token}'}
    data = {'message': f'\n{msg}'}
    try:
        r = requests.post(url, headers=headers, data=data, timeout=5)
        return r.status_code == 200
    except:
        return False

# ==========================================
# 0. 核心通訊與視覺配置 (Institutional UI/UX)
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

st.set_page_config(layout="wide", page_title="Institutional Quant Terminal", page_icon="🏦")
privacy_mode = st.sidebar.toggle("👁️ 隱私防窺模式 (Privacy Mode)", value=False)

def fmt_money(val, decimals=0):
    if privacy_mode: return "****"
    if decimals == 0: return f"{int(val):,}"
    return f"{float(val):,.{decimals}f}"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; color: #1e293b; }
.market-header { 
    padding: 18px 28px; border-radius: 10px; font-weight: 900; 
    font-size: 1.4rem; color: #ffffff !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    text-transform: uppercase; letter-spacing: 2px;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    margin-bottom: 28px; border-left: 6px solid #3b82f6;
}
.tw-market { border-left-color: #10b981; }
.us-market { border-left-color: #3b82f6; }
.pro-card { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03); transition: all 0.2s ease-in-out; }
.pro-card:hover { transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08); border-color: #cbd5e1 !important; }
.kpi-card { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center; transition: all 0.2s ease; }
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 6px 10px -2px rgba(0,0,0,0.05); }
.ticker-display { font-size: 1.75rem; font-weight: 900; line-height: 1.1; color: #0f172a !important; letter-spacing: -0.5px; }
.stock-name-display { font-size: 0.95rem; color: #64748b !important; font-weight: 700; margin-top: 4px; margin-bottom: 12px; }
.price-display { font-size: 1.5rem; font-weight: 800; color: #0f172a !important; margin-top: 4px; font-variant-numeric: tabular-nums; }
.data-label { font-size: 0.75rem; color: #64748b !important; margin-bottom: 4px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.data-value { font-size: 1.15rem; font-weight: 800; color: #0f172a !important; font-variant-numeric: tabular-nums; }
.badge-buy { display: inline-block; padding: 4px 10px; border-radius: 4px; background-color: #ecfdf5; color: #047857; font-weight: 800; font-size: 0.8rem; border: 1px solid #10b981; }
.badge-sell { display: inline-block; padding: 4px 10px; border-radius: 4px; background-color: #fde8e8; color: #b91c1c; font-weight: 800; font-size: 0.8rem; border: 1px solid #f87171; }
.badge-hold { display: inline-block; padding: 4px 10px; border-radius: 4px; background-color: #f1f5f9; color: #475569; font-weight: 800; font-size: 0.8rem; border: 1px solid #cbd5e1; }
.action-box { background: #f8fafc; border: 1px solid #e2e8f0; border-left: 6px solid #0f172a; padding: 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 25px; color: #0f172a !important; }
.action-box h4, .action-box div, .action-box li { color: #0f172a !important; }
.stNumberInput input { font-weight: 800 !important; color: #0f172a !important; font-size: 1.1rem !important;}
.modebar { display: none !important; }
hr { border-color: #e2e8f0; margin: 2rem 0; border-style: solid; border-width: 1px; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #cbd5e1; padding-bottom: 0px;}
.stTabs [data-baseweb="tab"] { height: 48px; white-space: pre-wrap; background-color: transparent; border-radius: 8px 8px 0 0; padding: 0 24px; color: #64748b; font-weight: 700; border: none; font-size: 0.95rem;}
.stTabs [aria-selected="true"] { background-color: #0f172a !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# 🚀 智慧代碼正名資料庫
STOCK_NAME_DICT = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2308": "台達電",
    "2881": "富邦金", "2891": "中信金", "2412": "中華電", "2603": "長榮", "3231": "緯創",
    "6669": "緯穎", "2303": "聯電", "3711": "日月光投控", "6285": "啟碁", "2344": "華邦電", 
    "2337": "旺宏", "3034": "聯詠", "2379": "瑞昱", "5498": "凱崴", "6548": "長科*", "8070": "長華*",
    "0050": "元大台灣50", "006208": "富邦台50", "0052": "富邦科技", "00881": "富邦台灣半導體", 
    "0056": "元大高股息", "00878": "國泰永續高股息", "00919": "群益台灣精選高息", 
    "00929": "復華台灣科技優息", "00713": "元大台灣高息低波", "00915": "凱基優選高股息30", 
    "00918": "大華優利高填息30", "00939": "統一台灣高息動能", "00940": "元大台灣價值高息",
    "00631L": "元大台灣50正2", "00670L": "富邦NASDAQ正2", "00687B": "國泰20年美債", "00937B": "群益ESG投等債20+",
    "AAPL": "蘋果", "MSFT": "微軟", "NVDA": "輝達", "TSLA": "特斯拉", "AMD": "超微", 
    "QQQ": "納斯達克100", "VTI": "全美股市", "SCHD": "美國紅利", "VOO": "標普500", 
    "TQQQ": "納斯達克3倍多", "QLD": "納斯達克2倍多", "SOXL": "半導體3倍多"
}
TECH_CONCENTRATION_TICKERS = ["2330", "2454", "2382", "3231", "6669", "3034", "2379", "0052", "00881", "AAPL", "MSFT", "NVDA", "AMD", "QQQ", "TQQQ", "SOXL", "QLD"]

# ==========================================
# 🛡️ 智慧混合式資料庫引擎 (Data Healer)
# ==========================================
DB_FILE = "portfolio_db.json"
USE_FIREBASE = False

try:
    if "firebase" in st.secrets:
        raw_db_url = st.secrets["firebase"].get("databaseURL", "")
        clean_db_url = raw_db_url.replace("https://https://", "https://").strip()
        if not clean_db_url.startswith("https://"): clean_db_url = "https://" + clean_db_url
            
        cred_dict = dict(st.secrets["firebase"])
        cred_dict["private_key"] = cred_dict["private_key"].replace('\\n', '\n')
        
        need_init = True
        if firebase_admin._apps:
            app = firebase_admin.get_app()
            if app.options.get('databaseURL') == clean_db_url: need_init = False
            else: firebase_admin.delete_app(app)
                
        if need_init:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': clean_db_url})
            
        USE_FIREBASE = True
except Exception as e:
    st.sidebar.warning(f"⚠️ 雲端連線失敗，自動啟用「本機離線快取模式」。")
    USE_FIREBASE = False

@st.cache_data(show_spinner=False, ttl=60)
def load_portfolio():
    default_data = {
        "global_goals": {"target_amt": 20000000, "target_years": 10}, 
        "settings": {"line_token": "", "tw_discount": 0.28, "us_fee": 0.0},
        "schemes": {
            "🎯 台股主力配置": {"market": "TW", "lots": [], "targets": {}}, 
            "🎯 美股主力配置": {"market": "US", "lots": [], "targets": {}}
        }
    }
    data = None
    if USE_FIREBASE:
        try: data = db.reference('/quant_portfolio').get()
        except: pass
    else:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            except: pass

    if not data: data = default_data
    if "global_goals" not in data: data["global_goals"] = default_data["global_goals"]
    if "settings" not in data: data["settings"] = default_data["settings"]
    if "tw_discount" not in data["settings"]: data["settings"]["tw_discount"] = 0.28
    if "us_fee" not in data["settings"]: data["settings"]["us_fee"] = 0.0
    if "schemes" not in data: data["schemes"] = default_data["schemes"]
    
    for s_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
        if s_name not in data["schemes"]: data["schemes"][s_name] = default_data["schemes"][s_name]
        if "lots" not in data["schemes"][s_name]: data["schemes"][s_name]["lots"] = []
        if "targets" not in data["schemes"][s_name]: data["schemes"][s_name]["targets"] = {}
    return data

def save_portfolio(data):
    if USE_FIREBASE:
        try: db.reference('/quant_portfolio').set(data)
        except Exception as e: st.error(f"寫入雲端失敗: {e}")
    else:
        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

db_data = load_portfolio()

# ==========================================
# 2. 🛡️ 智慧識別與核心演算引擎
# ==========================================
def resolve_suffix(base_tk):
    base_tk = str(base_tk).upper().strip()
    if base_tk.endswith('.TW') or base_tk.endswith('.TWO'): return base_tk
    if not base_tk[0].isdigit() and not base_tk.startswith('00'): return base_tk
    for ext in [".TW", ".TWO"]:
        tk = f"{base_tk}{ext}"
        try:
            if yf.Ticker(tk, session=yf_session).fast_info.get('lastPrice'): return tk
        except: pass
    return f"{base_tk}.TW" if base_tk[0].isdigit() else base_tk

@st.cache_data(show_spinner=False, ttl=3599)
def smart_resolve_ticker(user_input, api_key=""):
    t = user_input.strip().upper()
    if not t: return "", ""
    if t in ["現金", "CASH"]: return "CASH", "台/外幣保留款"
    if t.startswith("^"): 
        idx_map = {"^TWII": "台灣加權指數", "^IXIC": "那斯達克", "^GSPC": "標普500", "^SOX": "費城半導體", "^VIX": "恐慌指數"}
        return t, idx_map.get(t, "大盤指數")

    potential_tk = t
    match = re.search(r'([A-Z0-9]{2,8})', t)
    if match: potential_tk = match.group(1)

    if potential_tk in STOCK_NAME_DICT: return resolve_suffix(potential_tk), STOCK_NAME_DICT[potential_tk]
    for tk, name in STOCK_NAME_DICT.items():
        if t == name.upper() or name.upper() in t: return resolve_suffix(tk), name

    try:
        r_tw = requests.get(f"https://tw.stock.yahoo.com/quote/{potential_tk}", headers=yf_session.headers, timeout=3)
        if r_tw.status_code == 200:
            title_match = re.search(r'<title>(.*?)\s*\([A-Za-z0-9.]+\)', r_tw.text)
            if title_match:
                zh_name = title_match.group(1).strip()
                if zh_name and "Yahoo" not in zh_name and zh_name != potential_tk:
                    return resolve_suffix(potential_tk), zh_name
    except: pass

    try:
        r = requests.get(f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(potential_tk)}&lang=zh-Hant-TW&region=TW", headers=yf_session.headers, timeout=3)
        if r.status_code == 200 and r.json().get('quotes'):
            return r.json()['quotes'][0].get('symbol', '').upper(), r.json()['quotes'][0].get('shortname', potential_tk)
    except: pass
    
    if potential_tk and re.match(r'^[A-Z0-9]+$', potential_tk): return resolve_suffix(potential_tk), t if t != potential_tk else f"標的 {potential_tk}"
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

@st.cache_data(show_spinner=False, ttl=600)
def fetch_market_data(ticker):
    default_res = {
        "price": 1.0, "date": "即時報價", "ma50": 1.0, "ma200": 1.0, 
        "high_52w": 1.0, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, 
        "kd_k": 50.0, "atr": 0.0, "history_close": pd.Series(dtype=float), "full_df": None
    }
    if not ticker or ticker == "CASH": 
        default_res["date"] = "法幣基準"
        return default_res
        
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        realtime_price = float(t_obj.fast_info.get('lastPrice', 0) or 0)
        df = yf.download(ticker, period="10y", progress=False, session=yf_session)
        
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df.dropna(subset=['Close'], inplace=True)
            
            if not df.empty:
                df['MA1'] = df['Close'].rolling(window=5).mean()
                df['MA2'] = df['Close'].rolling(window=50).mean()
                df['MA3'] = df['Close'].rolling(window=200).mean()
                
                df['H-L'] = df['High'] - df['Low']
                df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
                df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
                df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
                df['ATR'] = df['TR'].rolling(window=14).mean()
                
                closes, highs, lows = df['Close'], df['High'], df['Low']
                price = realtime_price if realtime_price > 0 else float(closes.iloc[-1] or 0)
                date_str = "即時市場報價" if realtime_price > 0 else closes.index[-1].strftime("%Y-%m-%d")
                
                recent_highs = highs.tail(252) if len(highs) > 252 else highs
                high_52w = float(recent_highs.max()) if not pd.isna(recent_highs.max()) else price
                high_52w = max(high_52w, price)
                
                ma50 = float(df['MA2'].iloc[-1] or price) if len(closes) >= 50 else price
                ma200 = float(df['MA3'].iloc[-1] or price) if len(closes) >= 200 else price
                current_atr = float(df['ATR'].dropna().iloc[-1]) if not df['ATR'].dropna().empty else (price * 0.02)
                
                drawdown = ((price - high_52w) / high_52w) * 100 if high_52w > 0 else 0.0
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
                    "price": price, "date": date_str, "ma50": ma50, "ma200": ma200, "high_52w": high_52w, "drawdown": drawdown, 
                    "bias": bias, "rsi": current_rsi, "kd_k": current_k, "atr": current_atr, "history_close": closes, "full_df": df
                }
    except: pass
    return default_res

def aggregate_lots(lots, targets):
    agg = {}
    perf = {"realized_pnl": 0.0, "total_div": 0.0, "wins": 0, "losses": 0, "sum_win_amt": 0.0, "sum_loss_amt": 0.0, "irrational_trades": 0}
    has_cash = False
    sorted_lots = sorted(lots, key=lambda x: str(x.get("date", x.get("buy_date", ""))))
    irrational_keywords = ["手癢", "追高", "新聞", "報紙", "貪", "衝動", "別人說", "明牌"]
    
    for lot in sorted_lots:
        tk = str(lot.get("ticker", "")).strip().upper()
        if not tk or tk in ["NAN", "NONE"]: continue
        if tk == "CASH": has_cash = True
        
        action = lot.get("action", "")
        shares_val = float(lot.get("shares", 0))
        price_val = float(lot.get("price", lot.get("buy_price", 0)))
        date_str = str(lot.get("date", lot.get("buy_date", ""))).strip()
        memo_str = str(lot.get("memo", ""))
        
        if any(kw in memo_str for kw in irrational_keywords): perf["irrational_trades"] += 1
        if not action: action = "BUY" if shares_val >= 0 else "SELL"
            
        shares_abs = abs(shares_val)
        clean_tk = tk.split('.')[0]
        
        if tk not in agg:
            agg[tk] = {"ticker": tk, "init_shares": 0.0, "total_cost": 0.0, "target_pct": targets.get(clean_tk, 0.0), "earliest_buy_date": None, "dividends": 0.0, "realized_pnl": 0.0, "trade_history": []}
        
        if action == "BUY":
            if date_str and tk != "CASH":
                if agg[tk]["earliest_buy_date"] is None or date_str < agg[tk]["earliest_buy_date"]: agg[tk]["earliest_buy_date"] = date_str
            agg[tk]["init_shares"] += shares_abs
            agg[tk]["total_cost"] += shares_abs * price_val if tk != "CASH" else shares_abs
            agg[tk]["trade_history"].append({"date": date_str, "action": "B", "price": price_val})
            
        elif action == "SELL":
            if tk == "CASH":
                agg[tk]["init_shares"] -= shares_abs
                agg[tk]["total_cost"] -= shares_abs
            else:
                if agg[tk]["init_shares"] > 0:
                    avg_cost = agg[tk]["total_cost"] / agg[tk]["init_shares"]
                    trade_pnl = (price_val - avg_cost) * shares_abs
                    agg[tk]["realized_pnl"] += trade_pnl
                    perf["realized_pnl"] += trade_pnl
                    if trade_pnl > 0: 
                        perf["wins"] += 1
                        perf["sum_win_amt"] += trade_pnl
                    elif trade_pnl < 0: 
                        perf["losses"] += 1
                        perf["sum_loss_amt"] += abs(trade_pnl)
                    
                    agg[tk]["init_shares"] -= shares_abs
                    agg[tk]["total_cost"] -= shares_abs * avg_cost
                    agg[tk]["trade_history"].append({"date": date_str, "action": "S", "price": price_val})
                    if agg[tk]["init_shares"] <= 0.001:
                        agg[tk]["init_shares"], agg[tk]["total_cost"], agg[tk]["earliest_buy_date"] = 0.0, 0.0, None

        elif action == "DIVIDEND":
            agg[tk]["dividends"] += price_val
            perf["total_div"] += price_val

    if not has_cash: agg["CASH"] = {"ticker": "CASH", "init_shares": 0.0, "total_cost": 0.0, "target_pct": targets.get("CASH", 0.0), "earliest_buy_date": None, "dividends": 0.0, "realized_pnl": 0.0, "trade_history": []}

    res = []
    for tk, v in agg.items():
        if v["init_shares"] <= 0.001 and v["target_pct"] <= 0 and v["realized_pnl"] == 0 and v["dividends"] == 0: continue
        v["buy_price"] = 1.0 if tk == "CASH" else (v["total_cost"] / v["init_shares"] if v["init_shares"] > 0 else 0.0)
        v["leverage"] = get_leverage(tk)
        
        v["holding_days"] = 0
        if v["earliest_buy_date"] and tk != "CASH":
            try: v["holding_days"] = (datetime.date.today() - datetime.datetime.strptime(v["earliest_buy_date"], '%Y-%m-%d').date()).days
            except: pass
            
        res.append(v)
        
    total_trades = perf["wins"] + perf["losses"]
    if total_trades > 0:
        win_rate = perf["wins"] / total_trades
        avg_win = perf["sum_win_amt"] / perf["wins"] if perf["wins"] > 0 else 0
        avg_loss = perf["sum_loss_amt"] / perf["losses"] if perf["losses"] > 0 else 1
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 99
        if win_loss_ratio > 0:
            kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)
            perf["kelly_pct"] = max(0.0, kelly_pct * 100)
        else: perf["kelly_pct"] = 0.0
    else: perf["kelly_pct"] = 0.0
        
    perf["total_actions"] = len(sorted_lots)
    return res, perf

def calculate_net_pnl_stats(item, is_tw_market, fx_rate, tw_discount=0.28, us_fee_val=0.0):
    base_tk = item['ticker'].split('.')[0]
    shares = item.get('init_shares', 0)
    avg_buy_p = item.get('buy_price', 0)
    current_p = item.get('now_p', 0)
    gross_buy_amt = shares * avg_buy_p
    
    if item['ticker'].startswith("^") or item['ticker'] == "CASH":
        return gross_buy_amt, (current_p * fx_rate * shares) if item['ticker'] != "CASH" else shares, 0, 0, 0, 0
    
    tw_standard_fee_rate = 0.001425
    tw_min_fee = 20.0
    tw_tax_rate = 0.001 if (len(base_tk) == 5 or len(base_tk) == 6 or base_tk.startswith('00')) else 0.003

    if is_tw_market: 
        est_buy_fee = gross_buy_amt * tw_standard_fee_rate * tw_discount
        if est_buy_fee < tw_min_fee and gross_buy_amt > 0: est_buy_fee = tw_min_fee
        est_buy_fee = int(round(est_buy_fee))
    else: 
        est_buy_fee = us_fee_val if shares > 0 else 0
        
    net_buy_cost_curr = gross_buy_amt + est_buy_fee

    gross_sell_amt = shares * current_p
    if is_tw_market:
        est_sell_fee = gross_sell_amt * tw_standard_fee_rate * tw_discount
        if est_sell_fee < tw_min_fee and gross_sell_amt > 0: est_sell_fee = tw_min_fee
        est_sell_fee = int(round(est_sell_fee))
        est_sell_tax = int(round(gross_sell_amt * tw_tax_rate))
        net_sell_amt_curr = gross_sell_amt - est_sell_fee - est_sell_tax
    else:
        est_sell_fee = us_fee_val if shares > 0 else 0
        est_sell_tax = (gross_sell_amt * 0.0000278) if shares > 0 else 0
        net_sell_amt_curr = gross_sell_amt - est_sell_fee - est_sell_tax
        
    mult = 1.0 if is_tw_market else fx_rate
    net_buy_cost_ntd = net_buy_cost_curr * mult
    net_sell_amt_ntd = net_sell_amt_curr * mult
    
    net_pnl_ntd = net_sell_amt_ntd - net_buy_cost_ntd
    net_pnl_pct = (net_pnl_ntd / net_buy_cost_ntd * 100) if net_buy_cost_ntd > 0 else 0
    
    return net_buy_cost_ntd, net_sell_amt_ntd, (est_buy_fee+est_sell_fee)*mult, est_sell_tax*mult, net_pnl_ntd, net_pnl_pct

@st.cache_data(show_spinner=False, ttl=14400)
def fetch_yield_curve_spread():
    try:
        tnx = yf.Ticker("^TNX", session=yf_session).fast_info.get('lastPrice', 0)
        irx = yf.Ticker("^IRX", session=yf_session).fast_info.get('lastPrice', 0)
        if tnx > 0 and irx > 0: return float(tnx - irx)
    except: pass
    return 0.25

@st.cache_data(show_spinner=False, ttl=14400)
def fetch_sp500_breadth():
    try:
        df = yf.download("^GSPC", period="1y", progress=False, session=yf_session)
        if not df.empty:
            closes = df['Close']
            if isinstance(closes, pd.DataFrame): closes = closes.iloc[:, 0]
            ma200 = closes.rolling(window=200).mean().iloc[-1]
            return float(closes.iloc[-1]), float(ma200)
    except: pass
    return 1.0, 1.0

# ==========================================
# 🌍 總經大腦運算
# ==========================================
yield_spread = fetch_yield_curve_spread()
sp500_price, sp500_ma200 = fetch_sp500_breadth()
market_breadth_bullish = sp500_price > sp500_ma200

twd_data = fetch_market_data("TWD=X")
current_rate = twd_data["price"] if twd_data and twd_data["price"] > 0 else 32.5
vix_data = fetch_market_data("^VIX")
current_vix = vix_data["price"] if vix_data and vix_data["price"] > 0 else 15.0

# ==========================================
# 📊 左側邊欄：導覽與總經氣象站
# ==========================================
st.sidebar.title("🏦 Quant Terminal")
st.sidebar.markdown(f"📈 **宏觀匯率 USD/TWD：** `{current_rate:.2f}`")
st.sidebar.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

if yield_spread < 0: macro_color, macro_status = "#ef4444", "🚨 倒掛警戒 (降載防守)"
else: macro_color, macro_status = "#10b981", "🟢 擴張格局 (正常順勢)"
st.sidebar.markdown(f"""
<div style='padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {macro_color}; border-radius:8px; margin-bottom:12px;'>
    <div style='color:#475569 !important; font-size:0.75rem; font-weight:700; margin-bottom:4px; text-transform:uppercase;'>🏛 利差 (10Y-3M) [景氣吹哨者]</div>
    <div style='color:#0f172a !important; font-size:1.15rem; font-weight:900;'>{yield_spread:+.2f}% <span style='font-size:0.8rem; color:{macro_color}; font-weight:800;'><br>{macro_status}</span></div>
</div>
""", unsafe_allow_html=True)

if current_vix >= 30: vix_color, vix_status = "#ef4444", "🚨 極度恐慌 (槓桿強迫清零)"
elif current_vix >= 25: vix_color, vix_status = "#f59e0b", "⚠️ 高波動警戒 (槓桿強迫砍半)"
elif current_vix <= 12: vix_color, vix_status = "#3b82f6", "❄️ 極低波動 (過熱)"
else: vix_color, vix_status = "#10b981", "🟢 市場穩定 (順勢擴張)"
st.sidebar.markdown(f"""
<div style='padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {vix_color}; border-radius:8px; margin-bottom:12px;'>
    <div style='color:#475569 !important; font-size:0.75rem; font-weight:700; margin-bottom:4px; text-transform:uppercase;'>📉 VIX 恐慌指數 [情緒溫度計]</div>
    <div style='color:#0f172a !important; font-size:1.3rem; font-weight:900;'>{current_vix:.2f} <span style='font-size:0.85rem; color:{vix_color}; font-weight:800;'><br>{vix_status}</span></div>
</div>
""", unsafe_allow_html=True)

breadth_color = "#10b981" if market_breadth_bullish else "#ef4444"
breadth_status = "安全多頭" if market_breadth_bullish else "系統性破線風險 (拒絕左側)"
st.sidebar.markdown(f"""
<div style='padding:14px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {breadth_color}; border-radius:8px; margin-bottom:14px;'>
    <div style='color:#475569 !important; font-size:0.75rem; font-weight:700; margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>🕸️ 市場寬度 (S&P500)</div>
    <div style='color:#0f172a !important; font-size:0.95rem; font-weight:900;'>{breadth_status}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
if MY_API_KEY: genai.configure(api_key=MY_API_KEY)

app_mode = st.sidebar.radio("系統導覽 (Modules)：", [
    "🏠 宏觀資產矩陣 (Dashboard)", 
    "🇹🇼 台股主力量化倉位", 
    "🇺🇸 美股主力量化倉位", 
    "💸 現金流與稅務水庫", 
    "🧪 戰略回測實驗室", 
    "🧬 機構級阿爾法模型 (Alpha Quants)",
    "🤖 24H 守望者腳本 (Cron Bot)",
    "🔍 全球宏觀市場終端", 
    "📖 系統操作指南 (User Manual)",
    "⚙️ 系統全域設定 (Settings)"
])
st.sidebar.markdown("---")

# ==========================================
# 📊 頂層全域分頁路由
# ==========================================
if app_mode == "⚙️ 系統全域設定 (Settings)":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #334155 0%, #0f172a 100%); border-left-color: #94a3b8;'>⚙️ 系統全域參數與資料庫管裡 (Settings & Backup)</div>", unsafe_allow_html=True)
    c_set1, c_set2 = st.columns(2)
    with c_set1.expander("🎯 戰略目標資產設定 (AUM Target)", expanded=True):
        cur_target_amt = db_data["global_goals"].get("target_amt", 20000000)
        cur_target_years = db_data["global_goals"].get("target_years", 10)
        goal_amt = st.number_input("設定總目標資產 (NTD)", min_value=0, value=int(cur_target_amt), step=100000)
        goal_yrs = st.number_input("預估達成年數 (Years)", min_value=1, value=int(cur_target_years), step=1)
        if st.button("💾 寫入戰略目標", use_container_width=True):
            db_data["global_goals"] = {"target_amt": goal_amt, "target_years": goal_yrs}
            save_portfolio(db_data)
            st.toast("✅ 戰略目標更新完畢！", icon="✅")
            st.rerun()

    with c_set2.expander("📲 LINE Notify 警報推播", expanded=True):
        current_line_token = db_data.get("settings", {}).get("line_token", "")
        new_token = st.text_input("輸入 LINE Notify Token", value=current_line_token, type="password")
        if new_token != current_line_token:
            db_data["settings"]["line_token"] = new_token
            save_portfolio(db_data)
            st.rerun()
        if st.button("🔔 測試發送警報", use_container_width=True):
            success = send_line_notify(new_token, "✅ Quant Terminal 警報系統連線成功！")
            if success: st.success("發送成功！請檢查手機。")
            else: st.error("發送失敗，請檢查 Token 或網路連線。")

    st.markdown("---")
    st.subheader("💾 資料庫手動備份與還原保險箱")
    st.info("若未綁定 Firebase 雲端資料庫，建議每週手動下載 JSON 備份以防伺服器休眠重置。")
    c_bak1, c_bak2 = st.columns(2)
    json_string = json.dumps(db_data, ensure_ascii=False, indent=4)
    c_bak1.download_button("⬇️ 點此下載最新資料庫備份 (JSON)", file_name=f"quant_portfolio_backup_{datetime.date.today()}.json", mime="application/json", data=json_string, use_container_width=True)
    uploaded_file = c_bak2.file_uploader("⬆️ 上傳備份檔案以還原", type=["json"], label_visibility="collapsed")
    if uploaded_file is not None:
        if c_bak2.button("⚠️ 確認覆蓋並還原資料", use_container_width=True):
            try:
                new_data = json.load(uploaded_file)
                save_portfolio(new_data)
                st.success("還原成功！系統將自動重啟。")
                st.rerun()
            except: st.error("檔案損毀。")

elif app_mode == "📖 系統操作指南 (User Manual)":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left-color: #64748b;'>📖 機構級量化操盤手實戰指南 (Prop-Trader Playbook)</div>", unsafe_allow_html=True)
    st.info("💡 歡迎來到您的專屬量化大腦。這套系統已將華爾街對沖基金的「趨勢動能」、「資金控管」與「風險模型」徹底黑盒化。請遵循以下五大章節，拔除主觀情緒，讓數學為您賺錢。")
    
    with st.expander("第一章：基礎建設與真實帳戶對齊 (Data Initialization)", expanded=True):
        st.markdown("""
        ### 1. 建立您的第一筆庫存
        量化模型需要歷史成本才能精算您的阿爾法(Alpha)。
        * **操作動線**：進入左側導覽列 `🇹🇼 台股主力量化倉位` ➡️ 切換到 `📓 交易交割總帳與 AI 審判室` 分頁。
        * **輸入格式**：在快速登錄表單中填入代碼（如 2330 ）、股數、單價與建倉日期。
        * **心魔備註 (Memo)**：這是對決心魔的關鍵！請務必寫下真實買進理由（如：「看均線金叉買進」或「聽隔壁老王說的」）。未來交給 AI 覆盤時，它會冷酷地幫您算出「非理性交易佔比」。
        
        ### 2. 券商 APP 利潤損益完美對齊 (Gross vs Net PnL)
        散戶記帳最痛恨的就是「軟體算出來賺錢，APP 打開卻少了一大截手續費」。
        * **解決方案**：在 `📊 機構級量化風控與盯盤中心` 的最上方，點開 **⚙️ 券商交易稅費與折讓率設定**。
        * **操作設定**：輸入您真實的台股券商手續費折扣（例如您的券商給您 2.8 折，請輸入 `0.28`）或美股單筆低消。
        * **系統反應**：設定完畢後，系統將啟動**法人級雙重對齊**，在下方戰鬥卡片中顯示已徹底扣除買進/賣出雙向規費與證交稅的「真實實質保後淨損益 (Net PnL)」，保證與對帳單完美同步。
        """)

    with st.expander("第二章：總經大局觀與風控閥門 (Macro & Wind Controls)"):
        st.markdown("""
        身為操盤手，每天打開系統第一眼要看的是左側邊欄的「三大紅綠燈」。它們決定了您今天踩油門與煞車的力度。

        ### 1. 🏛 10Y-3M 利差 (Yield Spread) —— 經濟衰退吹哨者
        * **這是什麼**：美國 10 年期公債殖利率減去 3 個月期殖利率的差額。正常情況下長天期利息應較高（正值）。
        * **研判與行動**：若數值變為負數，系統會亮起「🔴 倒掛警戒」。這代表市場極度悲觀，通常是經濟衰退的前兆。此時應**嚴禁重壓高槓桿現貨擴張 (如 TQQQ, 正2 ETF)**，並將獲利部位轉入法幣保留款水庫。

        ### 2. 📉 VIX 恐慌指數 —— 市場情緒溫度計
        * **這是什麼**：衡量標普 500 未來 30 天的隱含波動率。
        * **研判與行動**：數值低於 15 代表安定；若 VIX 大於 25 (恐慌)，系統的動態降載演算法會被觸發，**強迫將您所有「槓桿係數大於 2.0x」的資產目標權重直接砍半**（若 VIX>30 則直接歸零）。請無條件聽從系統產生之紅色 SELL 減碼指令單。

        ### 3. 🕸️ 市場寬度 (Market Breadth) —— 真假牛市照妖鏡
        * **這是什麼**：對比美股大盤(S&P 500)是否穩站於 200 日均線（牛熊分界線）之上。
        * **研判與行動**：若亮起「🔴 系統性破線風險」，代表大多頭格局已被破壞（下跌家數多於上漲家數）。此時系統將自動鎖定並拒絕任何「左側抄底加碼」的建議。
        """)

    with st.expander("第三章：微觀動能與戰鬥卡片 (Micro Trends & Tactical Cards)"):
        st.markdown("""
        ### 1. 高密度持倉動能矩陣 (Sparklines Table)
        法人沒有時間一張一張圖表點開看。在盯盤中心的最上方，系統將您所有持股的「近 30 日走勢」壓縮成了微型折線圖嵌在表格內。
        * **🎯 實戰殺招**：點擊表頭的 **「距停損線(%)」** 欄位進行由小到大排序。您可以一秒鐘揪出目前距離死亡線最近的危險資產！

        ### 2. 個股戰鬥卡片核心判讀
        * **🚨 ATR 吊燈移動防守線 (Chandelier Exit)**
            * **定義**：系統會自動追蹤您建倉以來的「最高價」，並向下減去 N 倍的「真實波動均值 (ATR)」。
            * **特性**：這是一條只會跟著股價上升、絕不下降的移動停利/停損線。
            * **SOP 行動**：若今日股價實體跌破此防禦線，卡片將亮起奪目的紅色警報 **「🚨 SELL ALL / 破防平倉退出」**。看到此訊號時，請摒除一切人性僥倖，**無條件按市價平倉清空該檔庫存**。這是量化交易避開毀滅性熊市的最核心鐵律。
        
        * **📉 乖離率 (BIAS) 與 RSI 動能**
            * **乖離率 > +20%**：股價短線噴漲偏離年線過遠，隨時可能回檔修復。AI 戰術會建議「🚨 乖離過大」，您可適度減碼獲利了結。
            * **RSI < 30**：代表被市場恐慌錯殺超跌。在多頭市場中，AI 戰術會顯示「🟢 逢低加碼點」。

        * **🐢 1% 海龜風險規模限制 (Position Sizing)**
            * 系統在建議買進時，會同步精算一組數字：「海龜1%規模限制」。這是告訴您：以目前這檔股票的震幅(ATR)，如果您只願意承受帳戶總資金 1% 的損失風險，您這把最多只能買這麼多股。**這能完美杜絕您重倉單筆爆倉的悲劇。**
        """)

    with st.expander("第四章：智慧資金注水與阿爾法模型 (Alpha Quants)"):
        st.markdown("""
        ### 1. 💰 智慧階梯式增量資金注水控制台
        當您發薪水、有新資金入帳，或是賣出股票抱有滿手現金時：
        1. 輸入預定投入的現款金額。
        2. 選擇戰略模組：
            * **⚖️ 標準配置再平衡**：乖乖補齊偏離目標權重最多的股票。
            * **📈 右側順勢加碼**：強者恆強，系統將拒絕買進正在跌的股票，把資金全集中打在「站上多頭均線」的標的上，讓獲利奔跑。
            * **📉 左側分批抄底**：逆勢操作，只買 RSI < 40 被嚴重錯殺的股票。
        3. 系統會瞬間產出一張極度精確的「演算法自動化注水配置比例單」，您只需打開券商 APP 照著下單即可。

        ### 2. 🧬 機構級阿爾法模型 (Alpha Quants)
        不要再靠直覺分配資金，讓科學來說話：
        * **🧠 馬可維茲效率前緣 (MVO)**：選擇資產池後點擊執行，電腦會跑 5000 次蒙地卡羅模擬（Monte Carlo），找出「風險最低、期望報酬最高」的黃金權重。請直接參考 AI 算出的 `AI 最佳化建議 Target (%)` 來修正您卡片中的目標設定。
        * **⚔️ 曼斯菲爾德相對強弱 (RS)**：將您的庫存與大盤(TWII或GSPC)進行績效 PK。如果某檔股票的 RS 指數長年為負數 (顯示 🚨 嚴重落後)，請勇敢砍掉這個拖油瓶，把資金轉入 RS 排名為「🔥 遠超大盤」的領頭羊板塊。
        * **🌪️ 歷史 VaR 壓力測試**：模擬明日若發生 1% 機率的黑天鵝股災，您的帳戶「單日最大可能蒸發多少台幣」。若您看到這個預估虧損數字會睡不著覺，代表您現在的槓桿開太大了，請立刻調降股票權重，轉入現金。
        """)

    with st.expander("第五章：自動化無頭守望者 (Cron Bot)"):
        st.markdown("""
        ### 讓系統 24 小時為您守夜
        量化交易最大的痛點是：網頁關閉時，系統就停止運作了。如果半夜美股崩盤跌破 ATR 怎麼辦？
        
        * **解決方案**：
            1. 進入 `🤖 24H 守望者腳本 (Cron Bot)` 分頁。
            2. 系統已經根據您的庫存名單與 LINE Token，客製化寫好了一支 Python 獨立腳本 (`cron_bot.py`)。
            3. 將該腳本下載後，部署至免費的雲端排程平台（如 GitHub Actions）。
            4. 設定為每天收盤後（台股 14:30 / 美股早上 06:30）自動執行。
        * **成效**：機器人會像一位無情的警衛，每天自動幫您巡邏所有股票有沒有跌破 ATR 停損線，或是 VIX 有沒有飆高，並將警報或平安報告直接發送到您的 LINE 裡面！
        """)

elif app_mode == "🏠 宏觀資產矩陣 (Dashboard)":
    st.markdown("<div class='market-header global-market'>🏠 全資產戰略控制台 (Global Portfolio Matrix)</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='display:flex; justify-content:space-between; background:#f8fafc; padding:12px 24px; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:20px;'>
        <span style='color:#0f172a !important; font-weight:800;'>全域風險燈號狀態：</span>
        <span style='color:#475569 !important;'>美債利差: <span style='color:{macro_color}; font-weight:900;'>{'正常' if yield_spread>0 else '倒掛警戒'}</span></span>
        <span style='color:#475569 !important;'>VIX 動能: <span style='color:{vix_color}; font-weight:900;'>{vix_status}</span></span>
        <span style='color:#475569 !important;'>大盤寬度: <span style='color:{breadth_color}; font-weight:900;'>{'安全多頭' if market_breadth_bullish else '破線空頭'}</span></span>
    </div>
    """, unsafe_allow_html=True)
    
    total_aum_ntd, tw_aum_ntd, us_aum_ntd = 0.0, 0.0, 0.0
    total_cost_ntd, total_div_ntd, global_realized_pnl = 0.0, 0.0, 0.0
    combined_hist_df = pd.DataFrame()
    cash_total_ntd = 0.0
    treemap_data = []

    tw_discount_pref = db_data.get("settings", {}).get("tw_discount", 0.28)
    us_fee_pref = db_data.get("settings", {}).get("us_fee", 0.0)

    for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
        is_tw = "台股" in scheme_name
        market_cat = "台股 (TW)" if is_tw else "美股 (US)"
        agg_assets, perf_metrics = aggregate_lots(db_data["schemes"][scheme_name].get("lots", []), db_data["schemes"][scheme_name].get("targets", {}))
        
        rate_for_perf = 1.0 if is_tw else current_rate
        global_realized_pnl += perf_metrics["realized_pnl"] * rate_for_perf
        total_div_ntd += perf_metrics["total_div"] * rate_for_perf
        
        for asset in agg_assets:
            m_data = fetch_market_data(asset.get("ticker", ""))
            if m_data and m_data.get("price", 0) > 0:
                now_p = m_data["price"]
                rate = 1.0 if is_tw else current_rate
                init_sh = asset.get("init_shares", 0)
                clean_tk_name = asset["ticker"].split('.')[0]
                
                if asset.get("ticker", "") == "CASH": 
                    now_val_ntd = init_sh * rate
                    cash_total_ntd += now_val_ntd
                    if now_val_ntd > 0: treemap_data.append({"Market": "法幣保留款 (CASH)", "Asset": "現金 (Cash)", "Value_NTD": now_val_ntd, "PnL_Pct": 0.0})
                else: 
                    now_val_ntd = now_p * rate * init_sh
                    net_cost, _, _, _, _, net_pnl_pct = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw, rate, tw_discount=tw_discount_pref, us_fee_val=us_fee_pref)
                    total_cost_ntd += net_cost
                    
                    hist_series = m_data.get("history_close")
                    if not hist_series.empty and not asset["ticker"].startswith("^"):
                        val_series = hist_series * init_sh * rate
                        if combined_hist_df.empty: combined_hist_df = val_series.to_frame(name=asset["ticker"])
                        else:
                            if asset["ticker"] in combined_hist_df.columns: combined_hist_df[asset["ticker"]] = combined_hist_df[asset["ticker"]].add(val_series, fill_value=0)
                            else: combined_hist_df = combined_hist_df.join(val_series.rename(asset["ticker"]), how='outer')
                    
                    if now_val_ntd > 0: treemap_data.append({"Market": market_cat, "Asset": clean_tk_name, "Value_NTD": now_val_ntd, "PnL_Pct": net_pnl_pct})
                total_aum_ntd += now_val_ntd
                if is_tw: tw_aum_ntd += now_val_ntd
                else: us_aum_ntd += now_val_ntd

    if not combined_hist_df.empty:
        combined_hist_df = combined_hist_df.ffill()
        combined_hist_df['Total'] = combined_hist_df.sum(axis=1) + cash_total_ntd
    
    target_amount = db_data["global_goals"].get("target_amt", 20000000)
    target_years = db_data["global_goals"].get("target_years", 10)
    shortfall = max(0.0, target_amount - total_aum_ntd)
    req_cagr = ((target_amount / total_aum_ntd) ** (1 / max(1, target_years)) - 1) * 100 if total_aum_ntd > 0 and target_amount > total_aum_ntd else 0.0
    cumulative_ret = (((total_aum_ntd + global_realized_pnl + total_div_ntd) / (total_cost_ntd if total_cost_ntd > 0 else 1.0)) - 1) * 100 if total_cost_ntd > 0 else 0.0

    g1, g2, g3, g4 = st.columns(4)
    g1.markdown(f"<div class='kpi-card' style='border-top: 5px solid #8b5cf6;'><div class='data-label'>設定目標資產 (Target AUM)</div><div class='ticker-display'>NTD {fmt_money(target_amount)}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='kpi-card' style='border-top: 5px solid #ef4444;'><div class='data-label'>資產缺口 (Capital Shortfall)</div><div class='ticker-display'>NTD {fmt_money(shortfall)}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='kpi-card' style='border-top: 5px solid #10b981;'><div class='data-label'>隱含要求回報率 (Req. CAGR)</div><div class='ticker-display'>{req_cagr:.2f}%</div></div>", unsafe_allow_html=True)
    
    # 💡 淨空 f-string 變數區塊
    global_pnl_color = "#10b981" if cumulative_ret >= 0 else "#ef4444"
    global_pnl_sign = "+" if cumulative_ret >= 0 else ""
    g4.markdown(f"<div class='kpi-card' style='border-top: 5px solid {global_pnl_color};'><div class='data-label'>含息總報酬率 (Total Return)</div><div class='ticker-display' style='color:{global_pnl_color} !important;'>{global_pnl_sign}{cumulative_ret:.2f}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 法人級資產板塊配置熱力矩陣 (Portfolio Treemap)")
    d_col1, d_col2 = st.columns([1.5, 1])
    with d_col1:
        if treemap_data:
            df_tree = pd.DataFrame(treemap_data)
            fig_tree = px.treemap(df_tree, path=[px.Constant("全域資產配置"), 'Market', 'Asset'], values='Value_NTD', color='PnL_Pct', color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
            fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{customdata[0]:.1f}%", textfont=dict(size=14, family="Inter", color="white"))
            fig_tree.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_tree, use_container_width=True, config={'displayModeBar': False})
        else: st.info("暫無有效淨持倉數據。")
    with d_col2:
        # 💡 淨空 f-string 變數區塊
        hist_pnl_color = "#10b981" if global_realized_pnl >= 0 else "#ef4444"
        hist_pnl_sign = "+" if global_realized_pnl >= 0 else ""
        
        kpi_html = f"""
        <div style='display:flex; flex-direction:column; gap:10px;'>
            <div class='kpi-card' style='border-left: 5px solid #8b5cf6; padding:14px; background-color:#f8fafc;'>
                <div class='data-label'>🌍 全球投資總淨市值 (Total AUM)</div>
                <div class='ticker-display'>NTD {fmt_money(total_aum_ntd)}</div>
            </div>
            <div style='display:flex; gap:10px;'>
                <div class='kpi-card' style='flex:1; border-left: 4px solid #10b981; padding:12px;'>
                    <div class='data-label'>🇹🇼 台股總變現淨值</div>
                    <div class='price-display' style='font-size:1.25rem;'>NTD {fmt_money(tw_aum_ntd)}</div>
                </div>
                <div class='kpi-card' style='flex:1; border-left: 4px solid #3b82f6; padding:12px;'>
                    <div class='data-label'>🇺🇸 美股總變現淨值</div>
                    <div class='price-display' style='font-size:1.25rem;'>NTD {fmt_money(us_aum_ntd)}</div>
                </div>
            </div>
            <div style='display:flex; gap:10px;'>
                <div class='kpi-card' style='flex:1; padding:12px;'>
                    <div class='data-label'>歷史平倉已實現利潤</div>
                    <div class='price-display' style='font-size:1.25rem; color:{hist_pnl_color} !important;'>{hist_pnl_sign}NTD {fmt_money(global_realized_pnl)}</div>
                </div>
                <div class='kpi-card' style='flex:1; padding:12px;'>
                    <div class='data-label'>全期累計領取紅利股息</div>
                    <div class='price-display' style='font-size:1.25rem;'>NTD {fmt_money(total_div_ntd)}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)

    if not combined_hist_df.empty:
        st.markdown(f'<div class="market-header global-market" style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-left-color: #8b5cf6; margin-top:15px;">📈 全球資產歷史權益曲線 (Historical AUM Growth Curve)</div>', unsafe_allow_html=True)
        chart_df = combined_hist_df[['Total']].copy()
        chart_df = chart_df.resample('D').last().ffill()
        if privacy_mode:
            chart_df['Total'] = (chart_df['Total'] / (chart_df['Total'].iloc[0] if chart_df['Total'].iloc[0]>0 else 1) - 1) * 100
            y_title, ht = "淨值累積成長率 (%)", "%{y:.2f}%"
        else: y_title, ht = "資產淨市值 (NTD)", "NTD %{y:,.0f}"
        fig_eq = px.line(chart_df, x=chart_df.index, y='Total', template="plotly_white")
        fig_eq.update_traces(line=dict(color='#8b5cf6', width=2.5), fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.08)', hovertemplate=ht)
        fig_eq.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), yaxis_title=y_title, xaxis_title="", hovermode="x unified")
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})

elif app_mode in ["🇹🇼 台股主力量化倉位", "🇺🇸 美股主力量化倉位"]:
    is_tw_mode = (app_mode == "🇹🇼 台股主力量化倉位")
    market_label = "台股" if is_tw_mode else "美股"
    current_scheme_name = "🎯 台股主力配置" if is_tw_mode else "🎯 美股主力配置"
    
    market_css_class = "tw-market" if is_tw_mode else "us-market"
    st.markdown(f"<div class='market-header {market_css_class}'>💼 {market_label} 核心量化資產簿 (Quant Book)</div>", unsafe_allow_html=True)
    tab_monitor, tab_edit, tab_inject = st.tabs(["📊 機構級量化風控與盯盤中心", "📓 交易交割總帳與 AI 審判室", "💰 智慧階梯式增量資金注水控制台"])
    
    current_view_data = []
    local_total_val, local_total_cost, local_total_exposure = 0.0, 0.0, 0.0
    tech_exposure_val = 0.0
    
    tw_discount_input = db_data.get("settings", {}).get("tw_discount", 0.28)
    us_fee_input = db_data.get("settings", {}).get("us_fee", 0.0)
    
    target_portfolio, tab_perf = aggregate_lots(db_data["schemes"][current_scheme_name].get("lots", []), db_data["schemes"][current_scheme_name].get("targets", {}))
    
    if target_portfolio:
        for asset in target_portfolio:
            m_data = fetch_market_data(asset.get("ticker", ""))
            if m_data and m_data.get("price", 0) > 0:
                now_p = m_data.get("price", 0)
                net_cost, net_val, _, _, net_pnl, net_pnl_pct = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw_mode, current_rate, tw_discount=tw_discount_input, us_fee_val=us_fee_input)
                gross_now_val = net_val if asset["ticker"] != "CASH" else asset.get("init_shares", 0) * (1.0 if is_tw_mode else current_rate)
                lev = asset.get("leverage", 1.0)
                
                local_total_val += gross_now_val
                local_total_cost += net_cost
                local_total_exposure += gross_now_val * lev
                if asset["ticker"].split('.')[0] in TECH_CONCENTRATION_TICKERS: tech_exposure_val += gross_now_val
                
                high_52w_val = m_data.get("high_52w", now_p)
                dist_52w = ((now_p - high_52w_val) / high_52w_val * 100) if high_52w_val > 0 else 0.0
                hist_close = m_data.get("history_close", pd.Series(dtype=float))
                
                max_since_buy = now_p
                if not hist_close.empty and asset.get("earliest_buy_date") and asset["ticker"] != "CASH":
                    try:
                        h_sb = hist_close.loc[asset.get("earliest_buy_date"):]
                        if not h_sb.empty: max_since_buy = max(h_sb.max(), now_p)
                    except: pass
                
                current_view_data.append({
                    **asset, "now_p": now_p, "date": m_data.get("date", ""), 
                    "now_val_ntd": gross_now_val, "net_buy_cost": net_cost, "net_real_val": net_val,
                    "leverage": lev, "net_pnl": net_pnl, "net_pnl_pct": net_pnl_pct, "ann_roi": (((1 + net_pnl_pct / 100) ** (365 / max(asset.get("holding_days", 1), 1)) - 1) * 100) if asset.get("holding_days", 0) > 0 else net_pnl_pct,
                    "yoc": (asset.get("dividends", 0) * (1.0 if is_tw_mode else current_rate) / net_cost * 100) if net_cost > 0 else 0.0, "dist_52w": dist_52w,
                    "max_since_buy": max_since_buy, "ma50": m_data.get("ma50", 0), "ma200": m_data.get("ma200", 0), "bias": m_data.get("bias", 0),
                    "rsi": m_data.get("rsi", 50), "kd_k": m_data.get("kd_k", 50), "atr": m_data.get("atr", 0.0), "history_close": hist_close, "full_df": m_data.get("full_df")
                })

    with tab_monitor:
        if current_view_data:
            local_total_profit = local_total_val - local_total_cost
            total_leverage_ratio = (local_total_exposure / local_total_val) if local_total_val > 0 else 0.0
            tech_ratio = (tech_exposure_val / local_total_val * 100) if local_total_val > 0 else 0.0
            
            pnl_color = "#10b981" if local_total_profit >= 0 else "#ef4444"
            pnl_sign = "+" if local_total_profit >= 0 else ""
            
            st.markdown(f"""
            <div style='display:flex; gap: 16px; margin-bottom: 20px; flex-wrap:wrap;'>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #3b82f6;'>
                    <div class='data-label'>實質開倉總淨成本 (Gross Net Cost)</div>
                    <div class='ticker-display'>NTD {fmt_money(local_total_cost)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #8b5cf6;'>
                    <div class='data-label'>即時可變現淨市值 (Mark-to-Market)</div>
                    <div class='ticker-display'>NTD {fmt_money(local_total_val)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #f59e0b;'>
                    <div class='data-label'>組合槓桿曝險放大率 (Portfolio Beta)</div>
                    <div class='ticker-display' style='color:#f59e0b !important;'>{total_leverage_ratio:.2f}x</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid {pnl_color};'>
                    <div class='data-label'>已扣除雙向稅費・實質淨損益 (Net PnL) 🏦</div>
                    <div class='ticker-display' style='color:{pnl_color} !important;'>{pnl_sign}NTD {fmt_money(local_total_profit)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if tech_ratio > 70: st.warning(f"⚠️ **Beta 集中度警報**：您的持倉中科技與半導體資產的權重已高達 **{tech_ratio:.1f}%**。請謹慎增建槓桿部位！")
            
            with st.expander("⚙️ 演算法動態風控閥值微調 (Algorithmic Wind Controls)"):
                c_sl1, c_fee_cal = st.columns([2, 1])
                atr_multiplier = c_sl1.slider("📉 Trailing ATR 吊燈停利線乘數", 1.5, 5.0, 2.5, 0.1, key=f"atr_sl_{market_label}")
                rebalance_threshold = c_sl1.slider("⚖️ 演算法模型再平衡容錯閾值 (%)", 0.5, 10.0, 2.0, 0.5, key=f"reb_sl_{market_label}")
                new_discount = c_fee_cal.number_input("變更台股手續費折讓折扣", min_value=0.0, max_value=1.0, value=float(tw_discount_input))
                new_us_fee = c_fee_cal.number_input("變更美股單筆規費低消", min_value=0.0, value=float(us_fee_input))
                if new_discount != tw_discount_input or new_us_fee != us_fee_input:
                    db_data["settings"]["tw_discount"] = new_discount
                    db_data["settings"]["us_fee"] = new_us_fee
                    save_portfolio(db_data)
                    st.rerun()

            spark_data = []
            for item in current_view_data:
                if item.get("init_shares") <= 0.001 and item.get("target_pct") <= 0: continue
                hist_series = item.get("history_close")
                spark_list = hist_series.tail(30).tolist() if not hist_series.empty else [0]
                real_pct = (item.get("now_val_ntd", 0) / local_total_val * 100) if local_total_val > 0 else 0
                
                n_p = item.get("now_p", 0)
                stop_loss_price = item.get("max_since_buy", n_p) - (atr_multiplier * item.get("atr", 0.0))
                dist_to_stop = ((n_p - stop_loss_price) / n_p * 100) if n_p > 0 and item.get("ticker") != "CASH" else 999.0
                
                spark_data.append({
                    "資產標的": f"{item.get('ticker').split('.')[0]} {STOCK_NAME_DICT.get(item.get('ticker').split('.')[0], '')}",
                    "持倉數量": int(item.get('init_shares', 0)),
                    "保後淨利(%)": item.get('net_pnl_pct', 0.0),
                    "距停損線(%)": dist_to_stop if item.get("ticker") != "CASH" else None,
                    "市值配置佔比": real_pct,
                    "近30日動能走勢": spark_list
                })
                
            if spark_data:
                st.markdown("### 🔭 全持倉動能巡邏矩陣 (High-Density Sparklines Matrix)")
                st.dataframe(pd.DataFrame(spark_data), column_config={
                    "保後淨利(%)": st.column_config.NumberColumn(format="%.2f%%"),
                    "距停損線(%)": st.column_config.NumberColumn(format="%.1f%%", help="負數或趨近零代表已跌破停損線，請堅決平倉！可點擊欄位排序。"),
                    "市值配置佔比": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "近30日動能走勢": st.column_config.LineChartColumn(y_min=0)
                }, hide_index=True, use_container_width=True)

            rebalance_orders = []
            for item in current_view_data:
                mult = 1.0 if is_tw_mode else current_rate
                now_v = item.get("now_val_ntd", 0)
                tgt_p = item.get("target_pct", 0)
                lev = item.get("leverage", 1.0)
                dynamic_tgt_p = tgt_p if current_vix <= 25 else (tgt_p * 0.5 if current_vix <= 30 else 0.0) if lev >= 2.0 else tgt_p
                real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                diff_pct = real_pct - dynamic_tgt_p
                diff_val = (local_total_val * (dynamic_tgt_p / 100.0)) - now_v
                clean_name = item.get("ticker", "").split('.')[0]
                stop_loss_price = item.get("max_since_buy", item.get("now_p", 0)) - (atr_multiplier * item.get("atr", 0.0))
                is_trailing_stop = (item.get("now_p", 0) < stop_loss_price) and (item.get("ticker") != "CASH") and (item.get("init_shares") > 0)
                
                if is_trailing_stop:
                    rebalance_orders.append(f"<li>📉 <b>{clean_name}</b>: 破安全停損線 ({stop_loss_price:.2f}) ➡️ <span class='badge-sell'>🚨 強制平倉清倉 (SELL ALL)</span></li>")
                elif abs(diff_pct) > rebalance_threshold:
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: rebalance_orders.append(f"<li>💵 <b>現金儲備水庫</b>: 偏離過大 ➡️ <span class='badge-buy'>🟢 挹注注水 (ADD)</span> <b>{fmt_money(diff_amt)} {unit}</b></li>")
                        else: rebalance_orders.append(f"<li>💵 <b>現金儲備水庫</b>: 偏離過大 ➡️ <span class='badge-sell'>🔴 提領退守 (SUB)</span> <b>{fmt_money(abs(diff_amt))} {unit}</b></li>")
                    else:
                        price_ntd = item.get("now_p", 1) * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        vix_warning_text = " (VIX動態降載)" if dynamic_tgt_p != tgt_p else ""
                        if shares_diff > 0:
                            if lev >= 2.0 and item.get("ma50", 0) < item.get("ma200", 0): rebalance_orders.append(f"<li>🛒 <b>{clean_name}</b>: 權重不足，但觸發 <span class='badge-hold'>🟡 MA死叉防守鎖定</span> 暫緩建倉。</li>")
                            elif not market_breadth_bullish and lev >= 2.0: rebalance_orders.append(f"<li>🛒 <b>{clean_name}</b>: 權重不足，但因 <span class='badge-hold'>⚠️ 大盤寬度背離</span> 拒絕加碼槓桿。</li>")
                            else: rebalance_orders.append(f"<li>🛒 <b>{clean_name}</b>: 權重不足{vix_warning_text} ➡️ <span class='badge-buy'>🟢 買進再平衡</span> <b>{fmt_money(shares_diff)} 股</b></li>")
                        elif shares_diff < 0:
                            rebalance_orders.append(f"<li>📉 <b>{clean_name}</b>: 權重過高{vix_warning_text} ➡️ <span class='badge-sell'>🔴 賣出停利</span> <b>{fmt_money(abs(shares_diff))} 股</b></li>")
            
            if rebalance_orders: st.markdown(f"<div class='action-box'><h4 style='color:#b45309 !important; font-weight:900; margin-top:0; font-size:1.05rem;'>⚡ 演算法自動化指令單 (Balancing Execution Orders)</h4><ul style='margin-bottom:0; padding-left:20px;'>{''.join(rebalance_orders)}</ul></div>", unsafe_allow_html=True)
            else: st.markdown(f"<div class='action-box' style='background:#f0fdf4; border-color:#cbd5e1; border-left-color:#10b981;'><h4 style='color:#166534 !important; font-weight:900; margin-top:0; font-size:1.05rem;'>✅ 全組合現貨與槓桿曝險均完美收斂於安全容錯區間。</h4></div>", unsafe_allow_html=True)

            # 💡 淨空渲染卡片時的 f-string 引號衝突
            for item in current_view_data:
                if item.get("init_shares") <= 0.001 and item.get("target_pct") <= 0: continue
                mult = 1.0 if is_tw_mode else current_rate
                c_card = st.columns([1.8, 1.8, 1.4, 1.6, 2.4])
                
                now_v = item.get("now_val_ntd", 0)
                tgt_p = item.get("target_pct", 0)
                n_p = item.get("now_p", 0)
                shares_qty = item.get('init_shares', 0)
                stop_loss_price = item.get("max_since_buy", n_p) - (atr_multiplier * item.get("atr", 0.0))
                is_trailing_stop = (n_p < stop_loss_price) and (item.get("ticker") != "CASH") and (shares_qty > 0)
                dynamic_tgt_p = tgt_p if current_vix <= 25 else (tgt_p * 0.5 if current_vix <= 30 else 0.0) if item.get("leverage", 1.0) >= 2.0 else tgt_p
                real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                clean_name = item.get("ticker", "").split('.')[0]
                
                if item.get("ticker") == "CASH":
                    c_card[0].markdown(f"<div class='ticker-display'>💵 CASH</div><div class='stock-name-display'>台/外幣保留款水庫</div><div class='price-display'>TWD/USD</div><div style='margin-top:8px; font-size:0.95rem; font-weight:800; color:#475569;'>庫存: <span style='color:#0f172a;'>{fmt_money(shares_qty)}</span> 單位</div>", unsafe_allow_html=True)
                    c_card[1].markdown(f"<div class='data-label'>法幣保留款淨等值市值:</div><div class='data-value'>NTD {fmt_money(now_v)}</div>", unsafe_allow_html=True)
                    c_card[2].markdown(f"<div class='data-label'>累積平倉已實現利潤:</div><div class='data-value' style='color:#10b981 !important;'>NTD {fmt_money(item.get('realized_pnl', 0))}</div>", unsafe_allow_html=True)
                    c_card[3].markdown(f"<div class='data-label'>計量 Beta 風險暴露:</div><div class='data-value'>0.00x</div>", unsafe_allow_html=True)
                else:
                    item_pnl_val = item.get("net_pnl", 0)
                    item_pnl_pct = item.get("net_pnl_pct", 0.0)
                    item_pnl_color = "#10b981" if item_pnl_val >= 0 else "#ef4444"
                    item_pnl_sign = "+" if item_pnl_val >= 0 else ""
                    
                    trend_tag = "<span style='color:#10b981; font-weight:900;'>🟢 多頭</span>" if item.get("ma50", 0) >= item.get("ma200", 0) else "<span style='color:#ef4444; font-weight:900;'>🔴 空頭</span>"
                    trail_color = "#ef4444" if is_trailing_stop else "#64748b"
                    
                    tactical_action = "<span style='color:#64748b;'>⚖️ 中立持有</span>"
                    if is_trailing_stop: tactical_action = f"<span style='color:#ef4444; font-weight:900;'>🚨 破防平倉退出</span>"
                    elif item.get("ma50", 0) < item.get("ma200", 0) and item.get("leverage", 1.0) >= 2.0: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🛑 均線死叉避險</span>"
                    elif item.get("kd_k", 50.0) < 25 or item.get("rsi", 50.0) < 35: tactical_action = "<span style='color:#10b981; font-weight:900;'>🟢 逢低加碼點</span>"
                    
                    c_card[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='stock-name-display'>{STOCK_NAME_DICT.get(clean_name, clean_name)}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {n_p:.2f}</div><div style='margin-top:8px; font-size:0.95rem; font-weight:800; color:#475569;'>庫存: <span style='color:#0f172a;'>{fmt_money(shares_qty)}</span> 股</div>", unsafe_allow_html=True)
                    c_card[1].markdown(f"<div class='data-label'>未平倉變現淨市值:</div><div class='data-value'>NTD {fmt_money(item.get('net_real_val', 0))}</div><div class='data-label' style='margin-top:8px;'>實質保後淨損益 (PnL):</div><div class='data-value' style='color:{item_pnl_color} !important;'>{item_pnl_sign}{fmt_money(item_pnl_val)} ({item_pnl_pct:.2f}%)</div>", unsafe_allow_html=True)
                    c_card[2].markdown(f"<div class='data-label'>中長線趨勢排列:</div><div>{trend_tag}</div><div class='data-label' style='margin-top:8px;'>ATR 吊燈移動防守線:</div><div class='data-value' style='color:{trail_color} !important;'>{stop_loss_price:.2f}</div>", unsafe_allow_html=True)
                    c_card[3].markdown(f"<div class='data-label'>基期年線乖離 (BIAS):</div><div class='data-value' style='color:#3b82f6 !important;'>{item.get('bias', 0):+.1f}%</div><div class='data-label' style='margin-top:8px;'>AI 即時終端戰術:</div><div style='font-size:0.95rem; font-weight:700;'>{tactical_action}</div>", unsafe_allow_html=True)

                with c_card[4]:
                    st.markdown("<div class='data-label'>戰略目標權重 Target (%) ✍️</div>", unsafe_allow_html=True)
                    clean_tk_tgt = item.get('ticker', '').split('.')[0]
                    new_tgt = st.number_input("Target", value=float(tgt_p), step=1.0, min_value=0.0, max_value=100.0, key=f"tgt_{current_scheme_name}_{clean_tk_tgt}", label_visibility="collapsed")
                    if new_tgt != float(tgt_p):
                        db_data["schemes"][current_scheme_name]["targets"][clean_tk_tgt] = new_tgt
                        save_portfolio(db_data)
                        st.rerun()

                    diff_val = (local_total_val * (dynamic_tgt_p / 100.0)) - now_v
                    vix_warn_str = f" <span style='color:#ef4444;'>(VIX降載 ➡️ {dynamic_tgt_p}%)</span>" if dynamic_tgt_p != new_tgt else ""
                    
                    prog_color = "#10b981" if abs(real_pct - dynamic_tgt_p) <= rebalance_threshold else "#f59e0b"
                    progress_html = f"<div style='margin-top:6px; margin-bottom:4px; font-size:0.75rem; color:#475569; font-weight:700;'>實際 {real_pct:.1f}% / 目標 {dynamic_tgt_p}%{vix_warn_str}</div><div style='width: 100%; background-color: #cbd5e1; border-radius: 99px; height: 5px; overflow:hidden;'><div style='width: {min(100, real_pct)}%; background-color: {prog_color}; height: 100%;'></div></div>"
                    
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        action_msg = f"<div style='margin-top:8px;'><span class='badge-buy'>🟢 ADD</span> <b>{fmt_money(diff_amt)} {unit}</b></div>" if diff_amt > 0 else f"<div style='margin-top:8px;'><span class='badge-sell'>🔴 SUB</span> <b>{fmt_money(abs(diff_amt))} {unit}</b></div>" if diff_amt < 0 else "<div style='margin-top:8px;'><span class='badge-hold'>OK</span></div>"
                    else:
                        price_ntd = n_p * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        risk_amount = local_total_val * 0.01
                        max_shares_1pct = int(risk_amount / (item.get("atr", 1) * mult)) if item.get("atr", 0) > 0 else 0
                        
                        if is_trailing_stop: action_msg = f"<div style='margin-top:8px;'><span class='badge-sell' style='background:#b91c1c; color:white;'>🚨 SELL ALL</span> <b>{fmt_money(item.get('init_shares',0))} 股</b></div>"
                        elif shares_diff > 0:
                            if item.get("leverage", 1.0) >= 2.0 and item.get("ma50", 0) < item.get("ma200", 0): action_msg = "<div style='margin-top:8px;'><span class='badge-hold'>🟡 死叉鎖定</span></div>"
                            else: action_msg = f"<div style='margin-top:8px;'><span class='badge-buy'>🟢 BUY</span> <b>{fmt_money(shares_diff)} 股</b><div style='font-size:0.7rem; color:#64748b; margin-top:2px;'>🐢 海龜1%規模限制: {fmt_money(max_shares_1pct)} 股</div></div>"
                        elif shares_diff < 0: action_msg = f"<div style='margin-top:8px;'><span class='badge-sell'>🔴 SELL</span> <b>{fmt_money(abs(shares_diff))} 股</b></div>"
                        else: action_msg = "<div style='margin-top:8px;'><span class='badge-hold'>配置完美</span></div>"

                    card_bg = "#fffbeb" if abs(real_pct - dynamic_tgt_p) > rebalance_threshold else "#ffffff"
                    st.markdown(f"<div class='pro-card' style='background-color:{card_bg} !important; padding:10px; margin-top:2px;'>{progress_html}{action_msg}</div>", unsafe_allow_html=True)

                if item.get("ticker") != "CASH":
                    with st.expander(f"📈 展開 {clean_name} 歷史量化 K 線與「動態停損線」連動軸"):
                        df_full = item.get("full_df")
                        if df_full is not None and not df_full.empty and 'MA1' in df_full.columns:
                            df_chart = df_full.copy()
                            df_chart['Dynamic_Stop'] = df_chart['High'].rolling(22).max() - (atr_multiplier * df_chart['ATR'])
                            
                            fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
                            fig_k.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="K線"), row=1, col=1)
                            fig_k.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Dynamic_Stop'], mode='lines', name=f"ATR 吊燈線 ({atr_multiplier}x)", line=dict(color='#ef4444', width=1.5, dash='dot')), row=1, col=1)
                            fig_k.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA2'], mode='lines', name="50MA", line=dict(color='#10b981', width=1.5)), row=1, col=1)
                            fig_k.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA3'], mode='lines', name="200MA", line=dict(color='#3b82f6', width=2)), row=1, col=1)
                            
                            for t in item.get("trade_history", []):
                                try:
                                    t_action = t["action"]
                                    marker_color = "#10b981" if t_action == "B" else "#ef4444"
                                    fig_k.add_annotation(x=pd.to_datetime(t["date"]), y=t["price"], text=t_action, showarrow=True, arrowhead=1, arrowcolor=marker_color, bgcolor=marker_color, font=dict(color="white", size=9), ay=15 if t_action == "B" else -15, row=1, col=1)
                                except: pass
                            colors_vol = ['#ef4444' if row['Open'] - row['Close'] > 0 else '#10b981' for idx_r, row in df_chart.iterrows()]
                            fig_k.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], name="成交量", marker_color=colors_vol), row=2, col=1)
                            fig_k.update_layout(xaxis_rangeslider_visible=False, height=450, template="plotly_white", margin=dict(t=10, b=10, l=10, r=10), hovermode="x unified")
                            st.plotly_chart(fig_k, use_container_width=True, config={'displayModeBar': False}, key=f"kline_{market_label}_{clean_name}")

    with tab_edit:
        st.markdown("### ⚡ 交易日誌快速登錄 (Flash Trade Execution)")
        with st.form(key=f"quick_form_{market_label}"):
            qa_cols = st.columns([1.2, 1.5, 1.2, 1.2, 1.2, 1.8])
            qa_action = qa_cols[0].selectbox("類別", ["🟢 開倉買進 (BUY)", "🔴 減碼賣出 (SELL)", "💸 領取股息 (DIVIDEND)"], key=f"act_sel_{market_label}")
            qa_tk = qa_cols[1].text_input("商品代碼", placeholder="如: 6548", key=f"tk_in_{market_label}")
            qa_shares = qa_cols[2].number_input("股數", min_value=0, step=100, key=f"sh_in_{market_label}")
            qa_price = qa_cols[3].number_input("單價/息額", min_value=0.0, step=1.0, key=f"pr_in_{market_label}")
            qa_date = qa_cols[4].date_input("交割日期", value=datetime.date.today(), key=f"dt_in_{market_label}")
            qa_memo = qa_cols[5].text_input("決策防心魔備註", placeholder="例：均線糾結扣底突破", key=f"me_in_{market_label}")
            if st.form_submit_button("➕ 寫入全球交割總帳", use_container_width=True):
                if qa_tk and (qa_shares > 0 or "DIVIDEND" in qa_action):
                    real_tk, _ = smart_resolve_ticker(qa_tk, MY_API_KEY)
                    if real_tk:
                        act_str = "BUY" if "買進" in qa_action else "SELL" if "賣出" in qa_action else "DIVIDEND"
                        db_data["schemes"][current_scheme_name]["lots"].append({
                            "action": act_str, "ticker": real_tk, "shares": float(qa_shares) if act_str=="BUY" else -float(qa_shares) if act_str=="SELL" else 0.0,
                            "price": float(qa_price), "date": qa_date.strftime("%Y-%m-%d"), "memo": qa_memo
                        })
                        save_portfolio(db_data)
                        st.toast("✅ 交割單確認入帳！系統快取已刷新。", icon="✅")
                        st.rerun()

        st.markdown("### 📜 歷史交割明細表 (帳目自我修正)")
        raw_lots = db_data["schemes"][current_scheme_name].get("lots", [])
        f_lots = []
        for l in raw_lots:
            f_lots.append({
                "動作": "💸 配息" if l.get("action")=="DIVIDEND" else "🟢 買進" if l.get("shares",0)>=0 else "🔴 賣出",
                "代碼": l.get("ticker", "").split('.')[0], "數量": abs(l.get("shares", 0)),
                "價格/總息": float(l.get("price", 0)), "日期": str(l.get("date", "")), "決策備註": str(l.get("memo", ""))
            })
        lots_df = pd.DataFrame(f_lots) if f_lots else pd.DataFrame(columns=["動作", "代碼", "數量", "價格/總息", "日期", "決策備註"])
            
        edited_lots = st.data_editor(lots_df, num_rows="dynamic", use_container_width=True, key=f"editor_final_{market_label}")
        if st.button(f"📌 確認變更並同步雲端資料庫", type="primary", key=f"final_save_btn_{market_label}"):
            new_lots = []
            for _, row in edited_lots.iterrows():
                if pd.isna(row["代碼"]) or str(row["代碼"]).strip() == "": continue
                real_ticker, _ = smart_resolve_ticker(str(row["代碼"]), MY_API_KEY)
                if real_ticker:
                    act_type = "DIVIDEND" if "配息" in str(row["動作"]) else "BUY" if "買進" in str(row["動作"]) else "SELL"
                    qty_col = "數量" if "數量" in row else row.keys()[2]
                    sh_val = float(row[qty_col]) if act_type=="BUY" else -float(row[qty_col]) if act_type=="SELL" else 0.0
                    new_lots.append({
                        "action": act_type, "ticker": real_ticker, "shares": sh_val, "price": float(row["價格/總息"]),
                        "date": str(row["日期"]), "memo": str(row["決策備註"])
                    })
            db_data["schemes"][current_scheme_name]["lots"] = new_lots
            save_portfolio(db_data)
            st.rerun()

    with tab_inject:
        st.markdown("### 💰 智慧型增量資金金流加碼控制台")
        add_cash = st.number_input("設定預定注水注入現款金額 (NTD)", min_value=0, value=0, step=10000, format="%d", key=f"cash_final_input_{market_label}")
        inject_mode = st.radio("注入資金模型戰術選擇：", ["⚖️ 標準配置再平衡", "📈 右側順勢加碼 (僅挹注金叉多頭)", "📉 左側分批抄底 (僅挹注 RSI<40)"], horizontal=True, key=f"mode_final_input_{market_label}")
        
        if add_cash > 0 and current_view_data:
            st.markdown("<div class='action-box'>", unsafe_allow_html=True)
            global_tgt_sum = sum(item.get("target_pct", 0) for item in current_view_data if item.get("ticker") != "CASH")
            if global_tgt_sum == 0:
                st.warning("⚠️ **系統防呆攔截**：偵測到您尚未設定「目標權重 Target (%)」！請先至上方卡片內輸入期望持倉比例。")
            else:
                ideal_total_val = local_total_val + add_cash
                buy_list = []
                eligible_items = []
                for item in current_view_data:
                    ma50_v, ma200_v, rsi_val = item.get("ma50", 1), item.get("ma200", 1), item.get("rsi", 50)
                    is_bear_cross = (ma50_v < ma200_v)
                    if "右側" in inject_mode and is_bear_cross and item.get("ticker") != "CASH": continue
                    if "左側" in inject_mode and rsi_val >= 40 and item.get("ticker") != "CASH": continue
                    eligible_items.append(item)
                    
                total_eligible_tgt = sum(item.get("target_pct", 0) for item in eligible_items if item.get("ticker") != "CASH")
                
                if not eligible_items: 
                    st.write("在您選擇的戰術條件下，目前無符合資格之標的。")
                elif total_eligible_tgt == 0 and ("右側" in inject_mode or "左側" in inject_mode):
                    st.warning("⚠️ **無加碼目標**：在您選擇的「順勢/抄底」條件下，篩選出來的股票您都將目標權重設為了 0。系統不會買進您不想持有的股票。")
                else:
                    for item in eligible_items:
                        tgt = item.get("target_pct", 0)
                        lev = item.get("leverage", 1.0)
                        dynamic_tgt_p = (tgt if current_vix <= 25 else (tgt * 0.5 if current_vix <= 30 else 0.0)) if lev >= 2.0 else tgt
                        shortfall_ntd = (ideal_total_val * (dynamic_tgt_p / 100.0)) - item.get("now_val_ntd", 0)
                        
                        if shortfall_ntd > 0:
                            if item.get("ticker") == "CASH":
                                buy_units = shortfall_ntd / (1.0 if is_tw_mode else current_rate)
                                buy_list.append(f"<li>💵 <b>保留法幣資金</b>：注入 <b style='color:#0f172a;'>{fmt_money(buy_units)}</b> {'元' if is_tw_mode else '美元'} 進入備用庫。</li>")
                            else:
                                price_ntd = item.get("now_p", 1) * (1.0 if is_tw_mode else current_rate)
                                shares_to_buy = int(shortfall_ntd / price_ntd) if price_ntd > 0 else 0
                                if shares_to_buy > 0:
                                    buy_list.append(f"<li>🛒 <b>{item.get('ticker').split('.')[0]}</b>: 下達 <span class='badge-buy'>🟢 BUY (加碼)</span> <b>{fmt_money(shares_to_buy)} 股</b> <span style='color:#64748b; font-size:0.85rem;'>(約配本金 NTD {fmt_money(shares_to_buy * price_ntd)})</span></li>")
                    if buy_list: 
                        st.markdown(f"<ul style='list-style-type:none; padding-left:0;'>{''.join(buy_list)}</ul>", unsafe_allow_html=True)
                    else: 
                        st.info("💡 目前您的庫存配比已完全收斂，或在當前「順勢/抄底」策略過濾下暫無標的符合加碼標準。資金建議暫時留存為現金儲備。")
            st.markdown("</div>", unsafe_allow_html=True)

elif app_mode == "💸 現金流與稅務水庫":
    st.markdown("<div class='market-header global-market'>💸 被動現金流水庫與二代健保避稅預警 (Cashflow Terminal)</div>", unsafe_allow_html=True)
    all_div_records = []
    total_expected_div = 0
    total_tax_warning = []
    
    for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
        is_tw = "台股" in scheme_name
        raw_lots = db_data["schemes"][scheme_name].get("lots", [])
        raw_targets = db_data["schemes"][scheme_name].get("targets", {})
        agg_assets, _ = aggregate_lots(raw_lots, raw_targets)
        
        for asset in agg_assets:
            if asset['ticker'] == 'CASH' or asset['init_shares'] <= 0: continue
            try:
                info = yf.Ticker(asset['ticker'], session=yf_session).info
                yield_val = float(info.get('dividendYield', 0) or 0)
                price = float(info.get('currentPrice', info.get('previousClose', 0)) or 0)
            except: yield_val, price = 0.0, 0.0
            
            if yield_val > 0 and price > 0:
                mult = 1.0 if is_tw else current_rate
                val_ntd = asset['init_shares'] * price * mult
                expected_annual_div = val_ntd * yield_val
                total_expected_div += expected_annual_div
                
                if is_tw:
                    freq = 4 if '00' in asset['ticker'] else 1
                    est_single_div = expected_annual_div / freq
                    if est_single_div > 20000:
                        total_tax_warning.append(f"⚠️ <b>{asset['ticker'].split('.')[0]}</b>：預估單次配息達 <b>NTD {fmt_money(est_single_div)}</b>，將扣 <b>2.11% 二代健保 (損失 NTD {fmt_money(est_single_div * 0.0211)})</b>。")

                all_div_records.append({
                    "資產代碼": asset['ticker'].split('.')[0], "庫存市值 (NTD)": val_ntd,
                    "當前股息殖利率": yield_val * 100, "持倉均價成本殖利率 YoC": asset.get('yoc', 0),
                    "預期年化股利被動收入 (NTD)": expected_annual_div
                })
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("預測未來 12 個月總配息", f"NTD {fmt_money(total_expected_div)}")
    col_kpi2.metric("預測平均月被動收入", f"NTD {fmt_money(total_expected_div / 12)}")
    col_kpi3.metric("被動收入可覆蓋基本開銷率", f"{((total_expected_div / 12) / 50000)*100:.1f}%")
    
    st.markdown("---")
    st.subheader("📆 被動收益分配現況表")
    if all_div_records: st.dataframe(pd.DataFrame(all_div_records), use_container_width=True)
    else: st.info("目前持倉中無高配息資產標的。")
    if total_tax_warning: st.markdown(f"<div class='action-box' style='background-color:#fffbeb; border-color:#b45309;'><h4 style='color:#b45309 !important;'>🚨 二代健保補充保費漏洞預警</h4><div style='font-size:1rem; line-height:1.6; color:#0f172a;'>{('<br>'.join(total_tax_warning))}</div></div>", unsafe_allow_html=True)

elif app_mode == "🧪 戰略回測實驗室":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #4338ca 0%, #0f172a 100%); border-left-color: #34d399;'>🧪 歷史量化回測與策略沙盒 (Backtesting Sandbox)</div>", unsafe_allow_html=True)
    c_b1, c_b2, c_b3, c_b4, c_b5 = st.columns([1.5, 1, 1, 1, 1])
    test_ticker = c_b1.text_input("輸入測試標的", value="0050")
    test_period = c_b2.selectbox("回測歷史長度", ["1y", "3y", "5y", "10y"], index=2)
    short_ma_days = c_b3.number_input("短均線 (MA Short)", min_value=5, max_value=60, value=50)
    long_ma_days = c_b4.number_input("長均線 (MA Long)", min_value=20, max_value=300, value=200)
    test_atr_mult = c_b5.number_input("ATR 停利乘數", min_value=1.0, max_value=5.0, value=2.5, step=0.1)

    if st.button("🚀 啟動演算法歷史回測", type="primary", use_container_width=True):
        resolved_tk, tk_name = smart_resolve_ticker(test_ticker, MY_API_KEY)
        if resolved_tk:
            with st.spinner(f"針對 {tk_name} 進行高頻歷史模擬回測..."):
                df_test = yf.download(resolved_tk, period=test_period, progress=False, session=yf_session)
                if not df_test.empty:
                    if isinstance(df_test.columns, pd.MultiIndex): df_test.columns = df_test.columns.get_level_values(0)
                    df_test.dropna(subset=['Close'], inplace=True)
                    df_test['MA_S'] = df_test['Close'].rolling(window=short_ma_days).mean()
                    df_test['MA_L'] = df_test['Close'].rolling(window=long_ma_days).mean()
                    df_test['H-L'] = df_test['High'] - df_test['Low']
                    df_test['H-PC'] = abs(df_test['High'] - df_test['Close'].shift(1))
                    df_test['L-PC'] = abs(df_test['Low'] - df_test['Close'].shift(1))
                    df_test['TR'] = df_test[['H-L', 'H-PC', 'L-PC']].max(axis=1)
                    df_test['ATR'] = df_test['TR'].rolling(window=14).mean()
                    df_test['Stop_Loss'] = df_test['High'].rolling(window=22).max() - (test_atr_mult * df_test['ATR'])
                    df_test.dropna(inplace=True)
                    
                    df_test['Signal'] = np.where((df_test['MA_S'] > df_test['MA_L']) & (df_test['Close'] > df_test['Stop_Loss']), 1, 0)
                    df_test['Position'] = df_test['Signal'].shift(1).fillna(0)
                    df_test['Market_Returns'] = df_test['Close'].pct_change()
                    df_test['Strategy_Returns'] = df_test['Position'] * df_test['Market_Returns']
                    
                    bh_return = ((1 + df_test['Market_Returns']).cumprod().iloc[-1] - 1) * 100
                    strat_return = ((1 + df_test['Strategy_Returns']).cumprod().iloc[-1] - 1) * 100
                    
                    df_test['BnH_Peak'] = (1 + df_test['Market_Returns']).cumprod().cummax()
                    bnh_mdd = (((1 + df_test['Market_Returns']).cumprod() - df_test['BnH_Peak']) / df_test['BnH_Peak']).min() * 100
                    df_test['Strat_Peak'] = (1 + df_test['Strategy_Returns']).cumprod().cummax()
                    strat_mdd = (((1 + df_test['Strategy_Returns']).cumprod() - df_test['Strat_Peak']) / df_test['Strat_Peak']).min() * 100
                    
                    st.markdown("### 🏆 基準對照：法人級績效淚表 (Tearsheet)")
                    c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                    c_res1.metric("B&H 死抱總報酬", f"{bh_return:.2f}%")
                    c_res2.metric("B&H 最大回撤 (MDD)", f"{bnh_mdd:.2f}%")
                    c_res3.metric("量化策略總報酬", f"{strat_return:.2f}%", f"{strat_return - bh_return:+.2f}%")
                    c_res4.metric("量化策略最大回撤", f"{strat_mdd:.2f}%", f"{abs(bnh_mdd) - abs(strat_mdd):+.2f}% 避險縮減")
                    
                    fig_bt = go.Figure()
                    fig_bt.add_trace(go.Scatter(x=df_test.index, y=(1 + df_test['Market_Returns']).cumprod()*100, name='Buy & Hold', line=dict(color='#64748b')))
                    fig_bt.add_trace(go.Scatter(x=df_test.index, y=(1 + df_test['Strategy_Returns']).cumprod()*100, name='Quant Strategy', line=dict(color='#10b981')))
                    st.plotly_chart(fig_bt, use_container_width=True)

elif app_mode == "🧬 機構級阿爾法模型 (Alpha Quants)":
    st.markdown("<div class='market-header global-market'>🧬 機構級阿爾法實驗室 (MVO & VaR & RS)</div>", unsafe_allow_html=True)
    target_scheme = st.selectbox("請選擇要分析的資產池：", ["🎯 台股主力配置", "🎯 美股主力配置"], key="alpha_pool_select")
    raw_lots = db_data["schemes"][target_scheme].get("lots", [])
    raw_targets = db_data["schemes"][target_scheme].get("targets", {})
    agg_assets, _ = aggregate_lots(raw_lots, raw_targets)
    valid_tickers = [a["ticker"] for a in agg_assets if a["ticker"] != "CASH" and a["init_shares"] > 0]
    
    if not valid_tickers: st.warning("⚠️ 該資產池目前沒有足夠的有效持倉進行運算。")
    else:
        benchmark_tk = "^TWII" if "台股" in target_scheme else "^GSPC"
        df_all = yf.download(valid_tickers + [benchmark_tk], period="1y", interval="1d", progress=False, session=yf_session)['Close']
        if isinstance(df_all, pd.Series): df_all = df_all.to_frame()
        df_all.dropna(inplace=True)
        
        if not df_all.empty:
            tab_rs, tab_mvo, tab_var = st.tabs(["⚔️ 曼斯菲爾德相對強弱 (RS)", "🧠 馬可維茲效率前緣 (MVO)", "🌪️ VaR 黑天鵝壓力測試"])
            with tab_rs:
                calc_days = min(252, len(df_all) - 1)
                bm_ret = (df_all[benchmark_tk].iloc[-1] / df_all[benchmark_tk].iloc[-calc_days]) - 1
                rs_data = []
                for tk in valid_tickers:
                    if tk in df_all.columns:
                        tk_ret = (df_all[tk].iloc[-1] / df_all[tk].iloc[-calc_days]) - 1
                        rs_score = ((1 + tk_ret) / (1 + bm_ret) - 1) * 100
                        _, zh_name = smart_resolve_ticker(tk, MY_API_KEY)
                        rs_data.append({"代碼": f"{tk.split('.')[0]} {zh_name}", "RS 領先大盤點數": float(f"{rs_score:.2f}"), "強度判定": "🔥 遠超大盤" if rs_score > 10 else "🟢 強於大盤" if rs_score > 0 else "🚨 嚴重落後"})
                if rs_data:
                    df_rs = pd.DataFrame(rs_data).sort_values(by="RS 領先大盤指數" if 'RS 領先大盤指數' in rs_data[0] else "RS 領先大盤點數", ascending=False)
                    st.dataframe(df_rs, use_container_width=True)
            with tab_mvo:
                if len(valid_tickers) >= 2 and st.button("🚀 啟動 5000 次蒙地卡羅模擬演算", type="primary"):
                    returns = df_all[valid_tickers].pct_change().dropna()
                    mean_returns = returns.mean() * 252
                    cov_matrix = returns.cov() * 252
                    num_portfolios = 5000
                    results = np.zeros((3, num_portfolios))
                    weights_record = []
                    for i in range(num_portfolios):
                        weights = np.random.random(len(valid_tickers))
                        weights /= np.sum(weights)
                        weights_record.append(weights)
                        results[0,i] = np.sum(weights * mean_returns)
                        results[1,i] = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                        results[2,i] = results[0,i] / results[1,i]
                    max_sharpe_idx = np.argmax(results[2])
                    optimal_weights = weights_record[max_sharpe_idx]
                    
                    fig_mvo = px.scatter(x=results[1]*100, y=results[0]*100, color=results[2], labels={'x': '預期波動率 %', 'y': '預期報酬率 %'})
                    st.plotly_chart(fig_mvo, use_container_width=True)
                    
                    opt_data = [{"代碼": tk.split('.')[0], "AI 最佳建議 %": round(optimal_weights[idx]*100, 1)} for idx, tk in enumerate(valid_tickers)]
                    st.dataframe(pd.DataFrame(opt_data), use_container_width=True)
            with tab_var:
                current_vals = [df_all[tk].iloc[-1] * next((a["init_shares"] for a in agg_assets if a["ticker"] == tk), 0) for tk in valid_tickers]
                total_eq_val = sum(current_vals)
                if total_eq_val > 0:
                    cur_weights = np.array(current_vals) / total_eq_val
                    port_returns = df_all[valid_tickers].pct_change().dropna().dot(cur_weights)
                    var_99 = np.percentile(port_returns, 1) * 100
                    st.error(f"🌪️ 99% 信心水準極端壓力測試：單日最大回撤預估 {var_99:.2f}%，等值蒸發約 NTD {fmt_money(abs(var_99/100 * total_eq_val))}")

elif app_mode == "🤖 24H 守望者腳本 (Cron Bot)":
    st.markdown("<div class='market-header global-market'>🤖 24H 無頭守望者腳本產生器</div>", unsafe_allow_html=True)
    user_line_token = db_data.get('settings', {}).get('line_token', '')
    safe_token = user_line_token if user_line_token else "請在系統全域設定配置Token"
    
    tks_us = [a['ticker'] for a in aggregate_lots(db_data['schemes']['🎯 美股主力配置'].get('lots', []), {})[0] if a['ticker'] != 'CASH']
    tks_tw = [a['ticker'] for a in aggregate_lots(db_data['schemes']['🎯 台股主力配置'].get('lots', []), {})[0] if a['ticker'] != 'CASH']
    bot_tickers = tks_us + tks_tw
    
    bot_code = f"""import yfinance as yf
import pandas as pd
import requests

LINE_TOKEN = "{safe_token}"
TICKERS = {bot_tickers}

def send_line(msg):
    if not LINE_TOKEN or "請在" in LINE_TOKEN: return
    requests.post('https://notify-api.line.me/api/notify', headers={{'Authorization': f'Bearer {{LINE_TOKEN}}'}}, data={{'message': msg}})

def run_check():
    alerts = []
    try:
        vix = yf.Ticker("^VIX").fast_info['lastPrice']
        if vix > 25: alerts.append(f"⚠️ 大盤 VIX 飆高至 {{vix:.2f}}，系統建議啟動槓桿降載。")
    except: pass

    for tk in TICKERS:
        try:
            df = yf.download(tk, period="1y", progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            df['ATR'] = df['TR'].rolling(14).mean()
            
            cur_p = float(df['Close'].iloc[-1])
            max_p = float(df['High'].tail(60).max())
            stop_p = max_p - (2.5 * float(df['ATR'].iloc[-1]))
            if cur_p < stop_p: alerts.append(f"🚨 {{tk}} 跌破 ATR 移動安全線 ({{stop_p:.2f}})！目前股價: {{cur_p:.2f}}。")
        except: pass
    if alerts: send_line("\\n".join(["[🤖 Quant 每日巡邏報告]"] + alerts))
    else: send_line("[🤖 Quant 每日巡邏報告]\\n✅ 全數資產均於安全風控範圍內，無破線異常。")

if __name__ == "__main__":
    run_check()"""
    st.code(bot_code, language="python")
    st.download_button("⬇ 點此下載守望者巡邏自動化 cron_bot.py", file_name="cron_bot.py", data=bot_code)

elif app_mode == "🔍 全球宏觀市場終端":
    st.markdown("<div class='market-header global-market'>📊 全球宏觀市場終端 (Global Macro Terminal)</div>", unsafe_allow_html=True)
    c_m1, c_m2 = st.columns([1, 2])
    market_choice = c_m1.radio("🌍 快速切換分析大盤標的：", ["台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體", "自訂輸入個股"], horizontal=True)
    k_period = c_m2.radio("選擇技術分析週期：", ["日K", "週K", "月K"], horizontal=True)
    target_to_parse = "^TWII" if "台灣" in market_choice else "^IXIC" if "那斯達克" in market_choice else "^GSPC" if "標普" in market_choice else "^SOX" if "費城" in market_choice else st.text_input("輸入欲調研的資產代碼：", value="2330")
    
    if target_to_parse:
        ticker_input, zh_name = smart_resolve_ticker(target_to_parse, MY_API_KEY)
        if ticker_input:
            df = yf.download(ticker_input, period="2y", interval="1d", progress=False, session=yf_session)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=zh_name), row=1, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量"), row=2, col=1)
                fig.update_layout(xaxis_rangeslider_visible=False, height=550, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
