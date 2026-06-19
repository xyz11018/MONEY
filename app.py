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
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {token}'}
    data = {'message': f'\n{msg}'}
    try:
        r = requests.post(url, headers=headers, data=data)
        return r.status_code == 200
    except:
        return False

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
.market-header { 
    padding: 16px 24px; border-radius: 8px; font-weight: 900; 
    font-size: 1.3rem; color: #ffffff !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    text-transform: uppercase; letter-spacing: 1.5px;
    box-shadow: 0 4px 10px -2px rgba(0,0,0,0.2);
    margin-bottom: 24px; border-left: 6px solid #3b82f6;
}
.tw-market { border-left-color: #10b981; }
.us-market { border-left-color: #3b82f6; }
.pro-card { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%; transition: all 0.25s ease-in-out; }
.pro-card:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -4px rgba(0,0,0,0.08); border-color: #cbd5e1 !important; }
.kpi-card { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; padding: 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center; transition: all 0.2s ease; }
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 15px -3px rgba(0,0,0,0.06); }
.ticker-display { font-size: 1.85rem; font-weight: 900; line-height: 1.1; color: #0f172a !important; letter-spacing: -0.5px; }
.stock-name-display { font-size: 1rem; color: #475569 !important; font-weight: 700; margin-top: 4px; margin-bottom: 8px; }
.price-display { font-size: 1.45rem; font-weight: 800; color: #0f172a !important; margin-top: 6px; font-variant-numeric: tabular-nums; }
.date-display { font-size: 0.8rem; color: #64748b !important; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
.data-label { font-size: 0.75rem; color: #475569 !important; margin-bottom: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
.data-value { font-size: 1.2rem; font-weight: 800; color: #0f172a !important; font-variant-numeric: tabular-nums; }
.badge-buy { display: inline-block; padding: 6px 14px; border-radius: 6px; background-color: #ecfdf5; color: #047857; font-weight: 900; font-size: 0.85rem; border: 1px solid #10b981; text-transform: uppercase; letter-spacing: 0.5px;}
.badge-sell { display: inline-block; padding: 6px 14px; border-radius: 6px; background-color: #fde8e8; color: #b91c1c; font-weight: 900; font-size: 0.85rem; border: 1px solid #f87171; text-transform: uppercase; letter-spacing: 0.5px;}
.badge-hold { display: inline-block; padding: 6px 14px; border-radius: 6px; background-color: #f1f5f9; color: #475569; font-weight: 900; font-size: 0.85rem; border: 1px solid #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px;}
.action-box { background: #f8fafc; border: 1px solid #e2e8f0; border-left: 6px solid #0f172a; padding: 24px; border-radius: 12px; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.03); color: #0f172a !important; }
.action-box h4, .action-box div, .action-box li { color: #0f172a !important; }
.stNumberInput input { font-weight: 800 !important; color: #0f172a !important; font-size: 1.1rem !important;}
.modebar { display: none !important; }
hr { border-color: #e2e8f0; margin: 2rem 0; border-style: dashed; }
.stTabs [data-baseweb="tab-list"] { gap: 12px; border-bottom: 2px solid #cbd5e1; padding-bottom: 0px;}
.stTabs [data-baseweb="tab"] { height: 52px; white-space: pre-wrap; background-color: transparent; border-radius: 8px 8px 0 0; padding: 0 28px; color: #64748b; font-weight: 700; border: none; font-size: 0.95rem; letter-spacing: 0.5px;}
.stTabs [aria-selected="true"] { background-color: #0f172a !important; color: white !important; border-bottom: none !important; }
.manual-highlight { background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-weight: 700; color: #0f172a; font-family: monospace; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# 🚀 智慧代碼正名資料庫 (已擴充)
STOCK_NAME_DICT = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2308": "台達電",
    "2881": "富邦金", "2891": "中信金", "2412": "中華電", "2603": "長榮", "3231": "緯創",
    "6669": "緯穎", "2303": "聯電", "3711": "日月光投控", "6285": "啟碁", "2344": "華邦電", 
    "2337": "旺宏", "3034": "聯詠", "2379": "瑞昱", "5498": "凱崴", "6548": "長華*",
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
    st.sidebar.warning(f"⚠️ 雲端連線失敗，自動啟用「本機離線模式」。")
    USE_FIREBASE = False

def load_portfolio():
    default_data = {
        "global_goals": {"target_amt": 20000000, "target_years": 10}, 
        "settings": {"line_token": ""},
        "schemes": {
            "🎯 台股主力配置": {"market": "TW", "lots": [], "targets": {}}, 
            "🎯 美股主力配置": {"market": "US", "lots": [], "targets": {}}
        }
    }
    data = None
    if USE_FIREBASE:
        try:
            ref = db.reference('/quant_portfolio')
            data = ref.get()
        except: pass
    else:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            except: pass

    if not data: data = default_data
    if "global_goals" not in data: data["global_goals"] = default_data["global_goals"]
    if "settings" not in data: data["settings"] = default_data["settings"]
    if "schemes" not in data: data["schemes"] = default_data["schemes"]
    for s_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
        if s_name not in data["schemes"]: data["schemes"][s_name] = default_data["schemes"][s_name]
        if "lots" not in data["schemes"][s_name]: data["schemes"][s_name]["lots"] = []
        if "targets" not in data["schemes"][s_name]: data["schemes"][s_name]["targets"] = {}
    return data

def save_portfolio(data):
    if USE_FIREBASE:
        try:
            ref = db.reference('/quant_portfolio')
            ref.set(data)
        except Exception as e: st.error(f"寫入雲端資料庫失敗: {e}")
    else:
        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

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

# 💡 核心升級：強制 TTL Cache Bust，確保新版爬蟲立刻生效
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

    # 1. 優先查閱內建高速快取字典
    if potential_tk in STOCK_NAME_DICT: return resolve_suffix(potential_tk), STOCK_NAME_DICT[potential_tk]
    for tk, name in STOCK_NAME_DICT.items():
        if t == name.upper() or name.upper() in t: return resolve_suffix(tk), name

    # 2. 💡 終極解法：強制爬取 Yahoo 奇摩股市原生中文標題 (支援台/美股)
    try:
        r_tw = requests.get(f"https://tw.stock.yahoo.com/quote/{potential_tk}", headers=yf_session.headers, timeout=3)
        if r_tw.status_code == 200:
            # 擷取 `<title>凱崴 (5498.TWO) 股價...` 中的中文名稱
            title_match = re.search(r'<title>(.*?)\s*\([A-Za-z0-9.]+\)', r_tw.text)
            if title_match:
                zh_name = title_match.group(1).strip()
                if zh_name and "Yahoo" not in zh_name and zh_name != potential_tk:
                    return resolve_suffix(potential_tk), zh_name
    except: pass

    # 3. 若網頁爬取失敗，退回使用 API
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

# ==========================================
# 3. 📈 即時大數據與 ATR 動態防護同步引擎
# ==========================================
def fetch_market_data(ticker):
    default_res = {
        "price": 1.0, "date": "即時報價", "ma50": 1.0, "ma200": 1.0, 
        "high_52w": 1.0, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, 
        "kd_k": 50.0, "atr": 0.0, "history_close": pd.Series(dtype=float), "full_df": None
    }
    if not ticker or ticker == "CASH": 
        default_res["date"] = "最新匯率"
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
                df['Chandelier_Exit'] = df['High'].rolling(window=22).max() - (2.5 * df['ATR'])
                
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
        
        if realtime_price > 0:
            fallback_df = pd.DataFrame({'Close': [realtime_price], 'High': [realtime_price], 'Low': [realtime_price], 'Open': [realtime_price], 'Volume': [0]}, index=[pd.Timestamp.now()])
            fallback_df['MA1'], fallback_df['MA2'], fallback_df['MA3'], fallback_df['Chandelier_Exit'] = realtime_price, realtime_price, realtime_price, realtime_price * 0.95
            return {
                "price": realtime_price, "date": "即時報價 (補齊)", "ma50": realtime_price, "ma200": realtime_price, 
                "high_52w": realtime_price, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, "kd_k": 50.0, "atr": realtime_price*0.02, "history_close": pd.Series([realtime_price], dtype=float), "full_df": fallback_df
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
        
        if not action:
            if tk == "CASH": action = "BUY" if shares_val >= 0 else "SELL"
            else: action = "BUY" if shares_val > 0 else "SELL"
            
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

yield_spread = fetch_yield_curve_spread()
sp500_price, sp500_ma200 = fetch_sp500_breadth()
market_breadth_bullish = sp500_price > sp500_ma200

twd_data = fetch_market_data("TWD=X")
current_rate = twd_data["price"] if twd_data and twd_data["price"] > 0 else 32.5
vix_data = fetch_market_data("^VIX")
current_vix = vix_data["price"] if vix_data and vix_data["price"] > 0 else 15.0

# ==========================================
# 📊 左側邊欄：總經面板
# ==========================================
st.sidebar.title("🏦 Quant Terminal")
st.sidebar.markdown(f"📈 **宏觀匯率 USD/TWD：** `{current_rate:.2f}`")
st.sidebar.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

if yield_spread < 0: macro_color, macro_status = "#ef4444", "🚨 倒掛警戒 (防守)"
else: macro_color, macro_status = "#10b981", "🟢 擴張格局 (正常)"
st.sidebar.markdown(f"""
<div style='padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {macro_color}; border-radius:8px; margin-bottom:12px;'>
    <div style='color:#475569 !important; font-size:0.75rem; font-weight:700; margin-bottom:4px; text-transform:uppercase;'>🏛 利差 (10Y-3M)</div>
    <div style='color:#0f172a !important; font-size:1.15rem; font-weight:900;'>{yield_spread:+.2f}% <span style='font-size:0.75rem; color:{macro_color}; font-weight:800;'><br>{macro_status}</span></div>
</div>
""", unsafe_allow_html=True)

if current_vix >= 30: vix_color, vix_status = "#ef4444", "極度恐慌 (超賣降載)"
elif current_vix >= 25: vix_color, vix_status = "#f59e0b", "高波動 (減碼防禦)"
elif current_vix <= 12: vix_color, vix_status = "#3b82f6", "極低波動 (過熱)"
else: vix_color, vix_status = "#10b981", "市場穩定 (順勢擴張)"
st.sidebar.markdown(f"""
<div style='padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {vix_color}; border-radius:8px; margin-bottom:12px;'>
    <div style='color:#475569 !important; font-size:0.75rem; font-weight:700; margin-bottom:4px; text-transform:uppercase;'>📉 VIX 恐慌指數</div>
    <div style='color:#0f172a !important; font-size:1.3rem; font-weight:900;'>{current_vix:.2f} <span style='font-size:0.85rem; color:{vix_color}; font-weight:800;'><br>{vix_status}</span></div>
</div>
""", unsafe_allow_html=True)

breadth_color = "#10b981" if market_breadth_bullish else "#ef4444"
breadth_status = "大盤企穩均線" if market_breadth_bullish else "系統性破線風險"
st.sidebar.markdown(f"""
<div style='padding:14px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {breadth_color}; border-radius:8px; margin-bottom:14px;'>
    <div style='color:#475569 !important; font-size:0.75rem; font-weight:700; margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>🕸️ 市場寬度 (S&P500)</div>
    <div style='color:#0f172a !important; font-size:1.05rem; font-weight:900;'>{breadth_status}</div>
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
# ⚙️ 系統全域設定 (Settings)
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
            if not new_token: st.warning("請先輸入 Token")
            else:
                success = send_line_notify(new_token, "✅ Quant Terminal 警報系統連線成功！")
                if success: st.success("發送成功！請檢查手機。")
                else: st.error("發送失敗，請檢查 Token。")

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
            except Exception as e: st.error("檔案損毀。")

# ==========================================
# 📖 系統操作指南 (User Manual)
# ==========================================
elif app_mode == "📖 系統操作指南 (User Manual)":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left-color: #64748b;'>📖 量化終端實戰操作指南 (Quant Playbook)</div>", unsafe_allow_html=True)
    st.info("這份手冊將教您如何將這個系統從『單純的記帳軟體』晉升為『為您賺錢的量化大腦』。請按照以下階段熟悉您的戰鬥中心。")
    
    with st.expander("📍 第一階段：新手起步 (如何建立與管理庫存)", expanded=True):
        st.markdown("### 1. 建立您的第一筆庫存\n要讓系統為您精算損益，您必須告訴系統您買了什麼。\n* **步驟**：點擊左側選單的 `🇹🇼 台股主力量化倉位` 或 `🇺🇸 美股` ➡️ 切換到 `📓 量化覆盤與日誌審判室` 分頁。\n* **操作**：在「交易日誌快速登錄」表單中，選擇 **🟢 開倉買進 (BUY)**，輸入代碼（例如 `0050` 或 `2330`）、股數、單價與日期。\n* **備註 (Memo)**：強烈建議填寫您買進的理由（例如「看均線黃金交叉買進」），這會在未來的 AI 覆盤中發揮極大作用。\n\n### 2. 如何賣出並計算獲利？\n系統採用專業的**「平均成本結算法」**。\n* 當您選擇 **🔴 減碼賣出 (SELL)** 時，系統會自動用您當時的「平均買進成本」來扣除成本，並將賺到的錢記錄到 **「歷史已實現淨利」** 中。\n* 若您將某檔股票「全數賣出」且把目標權重設為 0%，系統會自動將它從盤面上隱藏，保持版面乾淨。")

    with st.expander("📍 第二階段：日常盯盤 (看懂系統發出的買賣訊號)"):
        st.markdown("### 1. 看懂總經大盤的「三大紅綠燈」\n在畫面最左邊側邊欄，有三個決定您慢步建倉的指標：\n* **🏛 利差 (10Y-3M)**：若亮紅燈代表債券倒掛（衰退前兆），嚴禁重壓。\n* **📉 VIX 恐慌指數**：衡量市場恐慌度。若數值大於 25，系統的演算法會強迫將您持有的槓桿部位的建議權重**強制砍半**。\n* **🕸️ 市場寬度 (S&P500)**：若破線，系統會拒絕加碼槓桿。\n\n### 2. 認識高密度微型矩陣 (Sparklines)\n法人是沒空一張一張圖表點開看的。在 `📊 🛡️ 機構級量化風控與盯盤中心` 的最上方，我們為您準備了 **「持倉動能總覽矩陣」**，您可以直接在表格中看到近 30 日的微型走勢，一眼掃描全庫存多空！")

    with st.expander("📍 第三階段：資金控管與進階模型 (加碼、停損、最佳化)"):
        st.markdown("### 1. 智慧增量資金注水 (Pyramiding)\n每個月發薪水想定期定額？請到 **`💰 智慧階梯式增量資金注水控制台`** 分頁。\n輸入您這個月要投入的現金，並選擇策略：\n* **📈 右側順勢加碼**：把錢全部集中打在「目前均線呈現多頭排列」的強勢股上，讓獲利奔跑。\n* **📉 左側分批抄底**：只把錢拿去買 RSI < 40 的超跌委屈股。\n\n### 2. 🧬 機構級阿爾法模型 (Alpha Quants)\n* **馬可維茲效率前緣 (MVO)**：讓電腦跑 5000 次隨機試算，告訴您最完美的持股比例是多少，以達到最高夏普值。\n* **曼斯菲爾德強弱 (RS)**：淘汰跑輸大盤的平庸股票。\n* **歷史 VaR 壓力測試**：模擬如果遇到像 2020 疫情崩盤那樣的 5% 黑天鵝機率，您的帳戶一天會蒸發多少錢。")

# ==========================================
# 🏠 1. 宏觀資產矩陣 (Dashboard)
# ==========================================
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
    
    total_aum_ntd, tw_aum_ntd, us_aum_ntd = 0, 0, 0
    total_cost_ntd = 0
    total_div_ntd, global_realized_pnl = 0, 0
    combined_hist_df = pd.DataFrame()
    cash_total_ntd = 0
    treemap_data = []

    with st.spinner("🔄 正在聚合全球資產矩陣與演算歷史軌跡..."):
        for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
            is_tw = "台股" in scheme_name
            market_cat = "台股 (TW)" if is_tw else "美股 (US)"
            raw_lots = db_data["schemes"][scheme_name].get("lots", [])
            raw_targets = db_data["schemes"][scheme_name].get("targets", {})
            agg_assets, perf_metrics = aggregate_lots(raw_lots, raw_targets)
            
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
                        asset_cost_ntd = now_val_ntd
                        cash_total_ntd += now_val_ntd
                        if now_val_ntd > 0:
                            treemap_data.append({"Market": "法幣保留款 (CASH)", "Asset": "現金 (Cash)", "Value_NTD": now_val_ntd, "PnL_Pct": 0.0})
                    else: 
                        now_val_ntd = now_p * rate * init_sh
                        net_cost, _, _, _, _, net_pnl_pct = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw, rate, tw_discount=0.28, us_fee_val=0.0)
                        asset_cost_ntd = net_cost
                        
                        hist_series = m_data.get("history_close")
                        if not hist_series.empty and not asset["ticker"].startswith("^"):
                            val_series = hist_series * init_sh * rate
                            if combined_hist_df.empty: combined_hist_df = val_series.to_frame(name=asset["ticker"])
                            else:
                                if asset["ticker"] in combined_hist_df.columns: combined_hist_df[asset["ticker"]] = combined_hist_df[asset["ticker"]].add(val_series, fill_value=0)
                                else: combined_hist_df = combined_hist_df.join(val_series.rename(asset["ticker"]), how='outer')
                        
                        if now_val_ntd > 0:
                            treemap_data.append({"Market": market_cat, "Asset": clean_tk_name, "Value_NTD": now_val_ntd, "PnL_Pct": net_pnl_pct})

                    total_aum_ntd += now_val_ntd
                    if is_tw: tw_aum_ntd += now_val_ntd
                    else: us_aum_ntd += now_val_ntd
                    total_cost_ntd += asset_cost_ntd

    if not combined_hist_df.empty:
        combined_hist_df = combined_hist_df.ffill()
        combined_hist_df['Total'] = combined_hist_df.sum(axis=1) + cash_total_ntd
        val_ytd = combined_hist_df['Total'].loc[str(datetime.datetime.now().year)+"-01-01":].iloc[0] if not combined_hist_df['Total'].loc[str(datetime.datetime.now().year)+"-01-01":].empty else combined_hist_df['Total'].iloc[0]
        val_now = combined_hist_df['Total'].iloc[-1]
    else: val_ytd, val_now = 0, 0

    target_amount = db_data["global_goals"].get("target_amt", 20000000)
    target_years = db_data["global_goals"].get("target_years", 10)
    shortfall = max(0, target_amount - total_aum_ntd)
    req_cagr = ((target_amount / total_aum_ntd) ** (1 / max(1, target_years)) - 1) * 100 if total_aum_ntd > 0 and target_amount > total_aum_ntd else 0.0
    cumulative_ret = (((total_aum_ntd + global_realized_pnl + total_div_ntd) / total_cost_ntd) - 1) * 100 if total_cost_ntd > 0 else 0.0

    g1, g2, g3, g4 = st.columns(4)
    g1.markdown(f"<div class='kpi-card' style='border-top: 5px solid #8b5cf6;'><div class='data-label'>設定目標資產 (Target AUM)</div><div class='ticker-display'>NTD {fmt_money(target_amount)}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='kpi-card' style='border-top: 5px solid #ef4444;'><div class='data-label'>資產缺口 (Capital Shortfall)</div><div class='ticker-display'>NTD {fmt_money(shortfall)}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='kpi-card' style='border-top: 5px solid #10b981;'><div class='data-label'>隱含要求回報率 (Req. CAGR)</div><div class='ticker-display'>{req_cagr:.2f}%</div></div>", unsafe_allow_html=True)
    pnl_c_global = "#10b981" if cumulative_ret >= 0 else "#ef4444"
    g4.markdown(f"<div class='kpi-card' style='border-top: 5px solid {pnl_c_global};'><div class='data-label'>含息總回報 (Total Return)</div><div class='ticker-display' style='color:{pnl_c_global} !important;'>{cumulative_ret:+.2f}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 📊 法人級持倉熱力矩陣 (Portfolio Treemap)")
    d_col1, d_col2 = st.columns([1.5, 1])
    with d_col1:
        if treemap_data:
            df_tree = pd.DataFrame(treemap_data)
            fig_tree = px.treemap(
                df_tree, 
                path=[px.Constant("全域資產配置"), 'Market', 'Asset'], 
                values='Value_NTD',
                color='PnL_Pct',
                color_continuous_scale='RdYlGn',
                color_continuous_midpoint=0,
                hover_data=['PnL_Pct', 'Value_NTD'],
                custom_data=['PnL_Pct']
            )
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>%{customdata[0]:.1f}%",
                textfont=dict(size=16, family="Inter", color="white")
            )
            fig_tree.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_tree, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("暫無持倉數據可供繪製熱力圖。")
            
    with d_col2:
        kpi_html = f"""
        <div style='display:flex; flex-direction:column; gap:12px; height:100%; justify-content:space-between;'>
            <div class='kpi-card' style='border-left: 5px solid #8b5cf6; padding:14px; background-color:#f8fafc;'>
                <div class='data-label'>🌍 全球投資淨市值 (Total AUM)</div>
                <div class='ticker-display'>NTD {fmt_money(total_aum_ntd)}</div>
            </div>
            <div style='display:flex; gap:12px;'>
                <div class='kpi-card' style='flex:1; border-left: 4px solid #10b981; padding:12px;'>
                    <div class='data-label'>🇹🇼 台股市值</div>
                    <div class='price-display'>NTD {fmt_money(tw_aum_ntd)}</div>
                </div>
                <div class='kpi-card' style='flex:1; border-left: 4px solid #3b82f6; padding:12px;'>
                    <div class='data-label'>🇺🇸 美股市值</div>
                    <div class='price-display'>NTD {fmt_money(us_aum_ntd)}</div>
                </div>
            </div>
            <div style='display:flex; gap:12px;'>
                <div class='kpi-card' style='flex:1; padding:12px;'>
                    <div class='data-label'>歷史已實現淨利 (Realized PnL)</div>
                    <div class='price-display' style='color:{"#10b981" if global_realized_pnl >=0 else "#ef4444"} !important;'>{"+" if global_realized_pnl >=0 else ""}NTD {fmt_money(global_realized_pnl)}</div>
                </div>
                <div class='kpi-card' style='flex:1; padding:12px;'>
                    <div class='data-label'>歷史總領取股息 (Total Div.)</div>
                    <div class='price-display'>NTD {fmt_money(total_div_ntd)}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)

    if not combined_hist_df.empty:
        st.markdown(f'<div class="market-header global-market" style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-left-color: #8b5cf6; margin-top:20px;">📈 全球資產歷史淨值走勢 (Historical AUM Curve)</div>', unsafe_allow_html=True)
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
        fig_eq.update_traces(line=dict(color='#8b5cf6', width=2.5), fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.15)', hovertemplate=ht)
        fig_eq.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), yaxis_title=y_title, xaxis_title="", hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 🇹🇼 / 🇺🇸 2. 核心操盤分頁模組 (主力量化倉位)
# ==========================================
elif app_mode in ["🇹🇼 台股主力量化倉位", "🇺🇸 美股主力量化倉位"]:
    is_tw_mode = (app_mode == "🇹🇼 台股主力量化倉位")
    market_label = "台股" if is_tw_mode else "美股"
    current_scheme_name = "🎯 台股主力配置" if is_tw_mode else "🎯 美股主力配置"
    
    st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">💼 {market_label} 核心量化倉位 (Quant Book)</div>', unsafe_allow_html=True)
    
    tab_monitor, tab_edit, tab_inject = st.tabs(["📊 🛡️ 機構級量化風控與盯盤中心", "📓 量化覆盤與日誌審判室", "💰 智慧階梯式增量資金注水控制台"])
    
    current_view_data = []
    local_total_val, local_total_cost, local_total_exposure = 0.0, 0.0, 0.0
    tech_exposure_val = 0.0
    
    with tab_monitor:
        with st.expander("⚙️ 券商交易稅費與折讓率設定 (Broker Fee & Tax Calibration)"):
            c_fee1, c_fee2 = st.columns(2)
            if is_tw_mode:
                tw_discount_input = c_fee1.number_input("台股手續費折讓折扣 (例如: 2.8折請輸入 0.28)", min_value=0.0, max_value=1.0, value=0.28, step=0.01)
                us_fee_input = 0.0
            else:
                tw_discount_input = 0.28
                us_fee_input = c_fee2.number_input("美股單筆交易低消/手續費 (免手續費請填 0)", min_value=0.0, value=0.0, step=1.0)
    
    target_portfolio, tab_perf = aggregate_lots(db_data["schemes"][current_scheme_name].get("lots", []), db_data["schemes"][current_scheme_name].get("targets", {}))
    
    if target_portfolio:
        with st.spinner(f"🔄 正在同步雲端即時報價與風險 Beta 矩陣..."):
            for asset in target_portfolio:
                m_data = fetch_market_data(asset.get("ticker", ""))
                if m_data and m_data.get("price", 0) > 0:
                    now_p = m_data.get("price", 0)
                    date_str = m_data.get("date", "")
                    
                    net_cost, net_val, total_fees, total_tax, net_pnl, net_pnl_pct = calculate_net_pnl_stats(
                        {**asset, "now_p": now_p}, is_tw_mode, current_rate, 
                        tw_discount=tw_discount_input if 'tw_discount_input' in locals() else 0.28,
                        us_fee_val=us_fee_input if 'us_fee_input' in locals() else 0.0
                    )
                    gross_now_val = net_val if asset["ticker"] != "CASH" else asset.get("init_shares", 0) * (1.0 if is_tw_mode else current_rate)
                    
                    lev = asset.get("leverage", 1.0)
                    exposure_val = gross_now_val * lev
                    
                    local_total_val += gross_now_val
                    local_total_cost += net_cost
                    local_total_exposure += exposure_val
                    
                    clean_tk = asset.get("ticker", "").split('.')[0]
                    if clean_tk in TECH_CONCENTRATION_TICKERS: tech_exposure_val += gross_now_val
                    
                    h_days = asset.get("holding_days", 0)
                    ann_roi = (((1 + net_pnl_pct / 100) ** (365 / max(h_days, 1)) - 1) * 100) if h_days > 0 else net_pnl_pct
                    yoc = (asset.get("dividends", 0) * (1.0 if is_tw_mode else current_rate) / net_cost * 100) if net_cost > 0 else 0.0
                    
                    high_52w_val = m_data.get("high_52w", now_p)
                    dist_52w = ((now_p - high_52w_val) / high_52w_val * 100) if high_52w_val > 0 else 0.0
                    
                    hist_close = m_data.get("history_close", pd.Series(dtype=float))
                    buy_date = asset.get("earliest_buy_date")
                    max_since_buy = now_p
                    if not hist_close.empty and buy_date and asset["ticker"] != "CASH":
                        try:
                            hist_since_buy = hist_close.loc[buy_date:]
                            if not hist_since_buy.empty: max_since_buy = max(hist_since_buy.max(), now_p)
                        except: pass
                    
                    trailing_dd = ((now_p - max_since_buy) / max_since_buy * 100) if max_since_buy > 0 else 0.0

                    current_view_data.append({
                        **asset, "now_p": now_p, "date": date_str, 
                        "now_val_ntd": gross_now_val, "net_buy_cost": net_cost, "net_real_val": net_val,
                        "exposure_val": exposure_val, "leverage": lev,
                        "net_pnl": net_pnl, "net_pnl_pct": net_pnl_pct, "ann_roi": ann_roi, "yoc": yoc, "dist_52w": dist_52w,
                        "drawdown": m_data.get("drawdown", 0), "trailing_dd": trailing_dd, "max_since_buy": max_since_buy,
                        "ma50": m_data.get("ma50", 0), "ma200": m_data.get("ma200", 0), "bias": m_data.get("bias", 0),
                        "rsi": m_data.get("rsi", 50), "kd_k": m_data.get("kd_k", 50), 
                        "earliest_buy_date": asset.get("earliest_buy_date"), "history_close": hist_close, "full_df": m_data.get("full_df")
                    })

    # 📊 子分頁 1: 動態監控盤內層渲染
    with tab_monitor:
        if current_view_data:
            local_total_profit = local_total_val - local_total_cost
            total_leverage_ratio = (local_total_exposure / local_total_val) if local_total_val > 0 else 0.0
            tech_ratio = (tech_exposure_val / local_total_val * 100) if local_total_val > 0 else 0.0
            
            pnl_color = "#10b981" if local_total_profit >= 0 else "#ef4444"
            pnl_sign = "+" if local_total_profit >= 0 else ""
            
            st.markdown(f"""
            <div style='display:flex; gap: 16px; margin-bottom: 24px; flex-wrap:wrap;'>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #3b82f6;'>
                    <div class='data-label'>含稅費建倉淨成本 (Net Cost Basis)</div>
                    <div class='ticker-display'>NTD {fmt_money(local_total_cost)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #8b5cf6;'>
                    <div class='data-label'>即時可折現淨市值 (Mark-to-Market)</div>
                    <div class='ticker-display'>NTD {fmt_money(local_total_val)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #f59e0b;'>
                    <div class='data-label'>組合風險波動放大率 (Portfolio Beta)</div>
                    <div class='ticker-display' style='color:#f59e0b !important;'>{total_leverage_ratio:.2f}x</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid {pnl_color};'>
                    <div class='data-label'>已扣稅費・淨損益 (Net PnL)</div>
                    <div class='ticker-display' style='color:{pnl_color} !important;'>{pnl_sign}NTD {fmt_money(local_total_profit)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if tech_ratio > 70:
                st.warning(f"⚠️ **Beta 集中度警報**：您的持倉中科技與半導體資產的權重已高達 **{tech_ratio:.1f}%**。請謹慎增建槓桿部位！")
            
            spark_data = []
            for item in current_view_data:
                if item.get("init_shares") <= 0.001 and item.get("target_pct") <= 0: continue
                clean_name = item.get("ticker", "").split('.')[0]
                _, zh_name = smart_resolve_ticker(item.get("ticker", ""), MY_API_KEY)
                hist_series = item.get("history_close")
                spark_list = hist_series.tail(30).tolist() if not hist_series.empty else [0]
                real_pct = (item.get("now_val_ntd", 0) / local_total_val * 100) if local_total_val > 0 else 0
                
                spark_data.append({
                    "標的": f"{clean_name} {zh_name}",
                    "庫存 (股/元)": int(item.get('init_shares', 0)),
                    "未實現實質保後損益(%)": item.get('net_pnl_pct', 0.0),
                    "現市值佔比": real_pct,
                    "近30日動能趨勢": spark_list
                })
                
            if spark_data:
                st.markdown("### 🔭 高密度持倉動能矩陣總覽 (Sparklines Overview)")
                df_spark = pd.DataFrame(spark_data)
                st.dataframe(
                    df_spark,
                    column_config={
                        "未實現實質保後損益(%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "現市值佔比": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                        "近30日動能趨勢": st.column_config.LineChartColumn(y_min=0)
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            with st.expander("⚙️ 演算法動態參數微調 (Algorithm Settings)"):
                c_slider1, c_slider2 = st.columns(2)
                rebalance_threshold = c_slider1.slider("⚖️ 演算法模型配置容錯閾值 (%)", 0.0, 10.0, 2.0, 0.5)
                atr_multiplier = c_slider2.slider("📉 ATR 吊燈停利乘數 (Chandelier Exit)", 1.0, 5.0, 2.5, 0.1)

            rebalance_orders = []
            for item in current_view_data:
                mult = 1.0 if is_tw_mode else current_rate
                now_v = item.get("now_val_ntd", 0)
                tgt_p = item.get("target_pct", 0)
                lev = item.get("leverage", 1.0)
                ma50_v = item.get("ma50", 1)
                ma200_v = item.get("ma200", 1)
                n_p = item.get("now_p", 0)
                max_since_buy = item.get("max_since_buy", n_p)
                atr_val = item.get("atr", 0.0)
                
                dynamic_tgt_p = tgt_p
                if lev >= 2.0:
                    if current_vix > 30.0: dynamic_tgt_p = 0.0
                    elif current_vix > 25.0: dynamic_tgt_p = tgt_p * 0.5
                
                real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                diff_pct = real_pct - dynamic_tgt_p
                target_val = local_total_val * (dynamic_tgt_p / 100.0)
                diff_val = target_val - now_v
                clean_name = item.get("ticker", "").split('.')[0]
                
                stop_loss_price = max_since_buy - (atr_multiplier * atr_val)
                is_trailing_stop = (n_p < stop_loss_price) and (item.get("ticker") != "CASH") and (item.get("init_shares") > 0)
                
                if is_trailing_stop:
                    rebalance_orders.append(f"<li style='margin-bottom:8px;'>📉 <b>{clean_name}</b>: 跌破 ATR 停利線 ({stop_loss_price:.2f}) ➡️ <span class='badge-sell'>🚨 SELL ALL (強制清倉)</span></li>")
                elif abs(diff_pct) > rebalance_threshold:
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: rebalance_orders.append(f"<li style='margin-bottom:8px;'>💵 <b>現金儲備</b>: <span class='badge-buy'>🟢 BUY (注水)</span> <b>{fmt_money(diff_amt)} {unit}</b></li>")
                        else: rebalance_orders.append(f"<li style='margin-bottom:8px;'>💵 <b>現金儲備</b>: <span class='badge-sell'>🔴 SELL (提領)</span> <b>{fmt_money(abs(diff_amt))} {unit}</b></li>")
                    else:
                        price_ntd = item.get("now_p", 1) * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        is_bear_cross = (ma50_v < ma200_v)
                        vix_warning_text = " (VIX降載)" if dynamic_tgt_p != tgt_p else ""
                        
                        if shares_diff > 0:
                            if lev >= 2.0 and is_bear_cross: rebalance_orders.append(f"<li style='margin-bottom:8px;'>🛒 <b>{clean_name}</b>: 權重不足，但 <span class='badge-hold'>🟡 MA 死叉暫緩買進</span></li>")
                            elif not market_breadth_bullish and lev >= 2.0: rebalance_orders.append(f"<li style='margin-bottom:8px;'>🛒 <b>{clean_name}</b>: 權重不足，但 <span class='badge-hold'>⚠️ 大盤破線拒絕槓桿</span></li>")
                            else: rebalance_orders.append(f"<li style='margin-bottom:8px;'>🛒 <b>{clean_name}</b>: 偏離過大{vix_warning_text} ➡️ <span class='badge-buy'>🟢 BUY (建倉)</span> <b>{fmt_money(shares_diff)} 股</b></li>")
                        elif shares_diff < 0: rebalance_orders.append(f"<li style='margin-bottom:8px;'>📉 <b>{clean_name}</b>: 比例過高{vix_warning_text} ➡️ <span class='badge-sell'>🔴 SELL (減碼)</span> <b>{fmt_money(abs(shares_diff))} 股</b></li>")
            
            if rebalance_orders: st.markdown(f"<div class='action-box'><h4 style='color:#b45309 !important; font-weight:900; margin-top:0; font-size:1.1rem;'>⚡ 演算法自動化指令單</h4><ul style='margin-bottom:0; padding-left:20px;'>{''.join(rebalance_orders)}</ul></div>", unsafe_allow_html=True)
            else: st.markdown(f"<div class='action-box' style='background:#f0fdf4; border-color:#cbd5e1; border-left-color:#10b981;'><h4 style='color:#166534 !important; font-weight:900; margin-top:0; font-size:1.1rem;'>✅ 全域風險資產結構穩健，未觸及任何停損。</h4></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### ⚔️ 個別部位戰鬥卡片 (Tactical Cards)")

            for item in current_view_data:
                if item.get("init_shares") <= 0.001 and item.get("target_pct") <= 0: continue
                
                mult = 1.0 if is_tw_mode else current_rate

                c = st.columns([1.8, 1.8, 1.4, 1.6, 2.4])
                
                now_v = item.get("now_val_ntd", 0)
                lev = item.get("leverage", 1.0)
                tgt_p = item.get("target_pct", 0)
                a_cost = item.get("asset_cost", 0)
                n_p = item.get("now_p", 0)
                ma50_v = item.get("ma50", 1)
                ma200_v = item.get("ma200", 1)
                shares_qty = item.get('init_shares', 0)
                trail_dd = item.get("trailing_dd", 0.0)
                atr_val = item.get("atr", 0.0)
                max_since_buy = item.get("max_since_buy", n_p)
                stop_loss_price = max_since_buy - (atr_multiplier * atr_val)
                is_trailing_stop = (n_p < stop_loss_price) and (item.get("ticker") != "CASH") and (shares_qty > 0)
                
                dynamic_tgt_p = tgt_p
                if lev >= 2.0:
                    if current_vix > 30.0: dynamic_tgt_p = 0.0
                    elif current_vix > 25.0: dynamic_tgt_p = tgt_p * 0.5
                
                real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                
                _, zh_name = smart_resolve_ticker(item.get("ticker", ""), MY_API_KEY)
                if not zh_name or zh_name == item.get("ticker"): zh_name = STOCK_NAME_DICT.get(item.get("ticker", "").split('.')[0], item.get("ticker", ""))
                clean_name = item.get("ticker", "").split('.')[0]
                
                if item.get("ticker") == "CASH":
                    c[0].markdown(f"<div class='ticker-display'>💵 CASH</div><div class='stock-name-display'>現金保留款</div><div class='price-display'>TWD/USD</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>淨等值市值 (Val):</div><div class='data-value'>NTD {fmt_money(now_v)}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>已實現淨利 (Realized):</div><div class='data-value' style='color:#10b981 !important;'>NTD {fmt_money(item.get('realized_pnl', 0))}</div>", unsafe_allow_html=True)
                    c[3].markdown(f"<div class='data-label'>Beta 風險:</div><div class='data-value'>0.00x</div>", unsafe_allow_html=True)
                else:
                    pnl_ntd = item.get('net_pnl', 0)
                    pnl_pct = item.get('net_pnl_pct', 0.0)
                    item_pnl_color = "#10b981" if pnl_ntd >= 0 else "#ef4444"
                    item_pnl_sign = "+" if pnl_ntd >= 0 else ""
                    
                    is_bear = n_p < ma200_v
                    is_bear_cross = ma50_v < ma200_v
                    trend_tag = "<span style='color:#10b981; font-weight:900;'>🟢 多頭</span>" if not is_bear_cross else "<span style='color:#ef4444; font-weight:900;'>🔴 空頭</span>"
                    trail_color = "#ef4444" if is_trailing_stop else "#64748b"
                    
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='stock-name-display'>{zh_name}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {n_p:.2f}</div><div style='margin-top:4px; font-size:0.9rem; font-weight:900;'>庫存: {fmt_money(shares_qty)} 股</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>可變現資產淨值 (M2M):</div><div class='data-value'>NTD {fmt_money(item.get('net_real_val', 0))}</div><div class='data-label' style='margin-top:12px;'>實質保後淨損益 (Net PnL):</div><div class='data-value' style='color:{item_pnl_color} !important;'>{item_pnl_sign}{fmt_money(pnl_ntd)} ({pnl_pct:.2f}%)</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>長線趨勢 (Trend):</div><div>{trend_tag}</div><div class='data-label' style='margin-top:12px;'>ATR 吊燈防守線:</div><div class='data-value' style='color:{trail_color} !important;'>{stop_loss_price:.2f}</div>", unsafe_allow_html=True)
                    
                    bias_val = item.get('bias', 0)
                    k_val, rsi_val = item.get("kd_k", 50.0), item.get("rsi", 50.0)
                    tactical_action = "<span style='color:#64748b;'>⚖️ 中立持有</span>"
                    if is_trailing_stop: tactical_action = f"<span style='color:#ef4444; font-weight:900;'>🚨 破線撤退</span>"
                    elif is_bear_cross and lev >= 2.0: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🛑 死叉避險</span>"
                    elif not is_bear and (k_val < 25 or rsi_val < 35): tactical_action = "<span style='color:#10b981; font-weight:900;'>🟢 逢低抄底</span>"
                    elif k_val > 80 or rsi_val > 75: tactical_action = "<span style='color:#f59e0b; font-weight:900;'>⚠️ 過熱警戒</span>"
                    elif bias_val >= 20: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🚨 乖離過大</span>"
                        
                    c[3].markdown(f"<div class='data-label'>乖離率 (BIAS):</div><div class='data-value' style='color:#3b82f6 !important;'>{bias_val:+.1f}%</div><div class='data-label' style='margin-top:12px;'>AI 終端戰術:</div><div style='font-size:1rem;'>{tactical_action}</div>", unsafe_allow_html=True)

                with c[4]:
                    st.markdown("<div class='data-label'>目標權重 Target (%) ✍️</div>", unsafe_allow_html=True)
                    clean_tk_tgt = item.get('ticker', '').split('.')[0]
                    new_tgt = st.number_input("Target", value=float(tgt_p), step=1.0, min_value=0.0, max_value=100.0, key=f"tgt_{current_scheme_name}_{clean_tk_tgt}", label_visibility="collapsed")
                    
                    if new_tgt != float(tgt_p):
                        db_data["schemes"][current_scheme_name]["targets"][clean_tk_tgt] = new_tgt
                        save_portfolio(db_data)
                        st.rerun()

                    diff = real_pct - dynamic_tgt_p
                    diff_val = (local_total_val * (dynamic_tgt_p / 100.0)) - now_v
                    
                    box_bg = "#ffffff" if abs(diff) <= rebalance_threshold else "#fffbeb"
                    box_border = "#e2e8f0" if abs(diff) <= rebalance_threshold else "#f59e0b"
                    
                    vix_warn_str = f" <span style='color:#ef4444;'>(VIX降載)</span>" if dynamic_tgt_p != new_tgt else ""
                    progress_html = f"<div style='margin-top:8px; margin-bottom:6px; font-size:0.8rem; color:#475569; font-weight:700;'>實際 {real_pct:.1f}% / 目標 {dynamic_tgt_p}%{vix_warn_str}</div><div style='width: 100%; background-color: #cbd5e1; border-radius: 99px; height: 6px; overflow:hidden;'><div style='width: {min(100, real_pct)}%; background-color: {'#10b981' if abs(diff) <= rebalance_threshold else '#f59e0b'}; height: 100%;'></div></div>"
                    
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: action_msg = f"<div style='margin-top:12px;'><span class='badge-buy'>🟢 ADD</span> <span style='font-weight:900; font-size:1rem;'>{fmt_money(diff_amt)}{unit}</span></div>"
                        elif diff_amt < 0: action_msg = f"<div style='margin-top:12px;'><span class='badge-sell'>🔴 SUB</span> <span style='font-weight:900; font-size:1rem;'>{fmt_money(abs(diff_amt))}{unit}</span></div>"
                        else: action_msg = f"<div style='margin-top:12px;'><span class='badge-hold'>OK</span></div>"
                    else:
                        price_ntd = n_p * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        if is_trailing_stop: action_msg = f"<div style='margin-top:12px;'><span class='badge-sell' style='background:#b91c1c; color:white;'>🚨 SELL ALL</span> <span style='font-weight:900; font-size:1rem;'>{fmt_money(shares_qty)}股</span></div>"
                        elif shares_diff > 0: 
                            if lev >= 2.0 and is_bear_cross: action_msg = f"<div style='margin-top:12px;'><span class='badge-hold'>🟡 MA死叉 暫停</span></div>"
                            else: action_msg = f"<div style='margin-top:12px;'><span class='badge-buy'>🟢 BUY</span> <span style='font-weight:900; font-size:1rem;'>{fmt_money(shares_diff)}股</span></div>"
                        elif shares_diff < 0: action_msg = f"<div style='margin-top:12px;'><span class='badge-sell'>🔴 SELL</span> <span style='font-weight:900; font-size:1rem;'>{fmt_money(abs(shares_diff))}股</span></div>"
                        else: action_msg = f"<div style='margin-top:12px;'><span class='badge-hold'>配置完美</span></div>"

                    st.markdown(f"<div class='pro-card' style='background-color:{box_bg} !important; border-color:{box_border} !important; padding:12px; margin-top:2px;'>{progress_html}{action_msg}</div>", unsafe_allow_html=True)

                if item.get("ticker") != "CASH":
                    with st.expander(f"📈 展開 {clean_name} 詳細 K 線分析"):
                        df_full = item.get("full_df")
                        if df_full is not None and not df_full.empty and 'MA1' in df_full.columns:
                            fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                            fig_k.add_trace(go.Candlestick(x=df_full.index, open=df_full['Open'], high=df_full['High'], low=df_full['Low'], close=df_full['Close'], name="K線"), row=1, col=1)
                            if 'Chandelier_Exit' in df_full.columns: fig_k.add_trace(go.Scatter(x=df_full.index, y=df_full['Chandelier_Exit'], mode='lines', name="ATR 吊燈停利線", line=dict(color='#ef4444', width=1.5, dash='dot')), row=1, col=1)
                            fig_k.add_trace(go.Scatter(x=df_full.index, y=df_full['MA1'], mode='lines', name="5MA", line=dict(color='#ff9900', width=1)), row=1, col=1)
                            fig_k.add_trace(go.Scatter(x=df_full.index, y=df_full['MA2'], mode='lines', name="50MA", line=dict(color='#10b981', width=1.5)), row=1, col=1)
                            fig_k.add_trace(go.Scatter(x=df_full.index, y=df_full['MA3'], mode='lines', name="200MA", line=dict(color='#3b82f6', width=2)), row=1, col=1)
                            
                            trade_hist = item.get("trade_history", [])
                            for t in trade_hist:
                                try:
                                    t_date = pd.to_datetime(t["date"])
                                    t_action = t["action"]
                                    t_price = t["price"]
                                    marker_color = "#10b981" if t_action == "B" else "#ef4444"
                                    fig_k.add_annotation(x=t_date, y=t_price, text=t_action, showarrow=True, arrowhead=1, arrowcolor=marker_color, bgcolor=marker_color, font=dict(color="white", size=10), ay=20 if t_action == "B" else -20, row=1, col=1)
                                except: pass
                            fig_k.add_trace(go.Bar(x=df_full.index, y=df_full['Volume'], name="成交量", marker_color="#cbd5e1"), row=2, col=1)
                            fig_k.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white", margin=dict(t=10, b=10, l=10, r=10), hovermode="x unified")
                            st.plotly_chart(fig_k, use_container_width=True, config={'displayModeBar': False})
                st.markdown("<hr>", unsafe_allow_html=True)

    # 📓 子分頁 2: 歷史交易明細
    with tab_edit:
        st.markdown("### ⚡ 交易日誌快速登錄 (Flash Trade Execution)")
        with st.form(key=f"quick_add_form_{market_label}"):
            qa_cols = st.columns([1.2, 1.5, 1.2, 1.2, 1.2, 1.8])
            qa_action = qa_cols[0].selectbox("類別", ["🟢 開倉買進 (BUY)", "🔴 減碼賣出 (SELL)", "💸 領取股息 (DIVIDEND)"])
            qa_tk = qa_cols[1].text_input("代碼/簡稱", placeholder="如: 0050")
            qa_shares = qa_cols[2].number_input("股數 (Shares)", min_value=0, step=100, format="%d")
            qa_price = qa_cols[3].number_input("單價/總息", min_value=0.0, step=1.0)
            qa_date = qa_cols[4].date_input("日期", value=datetime.date.today())
            qa_memo = qa_cols[5].text_input("決策備註 (Memo)", placeholder="例如：手癢跟風/均線扣底買")
            submit_quick_add = st.form_submit_button("➕ 寫入交易總帳", use_container_width=True)
            
            if submit_quick_add:
                if qa_tk and (qa_shares > 0 or "DIVIDEND" in qa_action):
                    real_tk, resolved_name = smart_resolve_ticker(qa_tk, MY_API_KEY)
                    if real_tk:
                        if "BUY" in qa_action: act_str = "BUY"
                        elif "SELL" in qa_action: act_str = "SELL"
                        else: act_str = "DIVIDEND"
                        
                        final_shares = float(qa_shares) if act_str == "BUY" else (-float(qa_shares) if act_str == "SELL" else 0.0)
                        
                        db_data["schemes"][current_scheme_name]["lots"].append({
                            "action": act_str, "ticker": real_tk, "shares": final_shares,
                            "price": float(qa_price), "date": qa_date.strftime("%Y-%m-%d"), "memo": qa_memo
                        })
                        save_portfolio(db_data)
                        st.toast(f"✅ 交易確認已入帳！", icon="✅")
                        st.rerun()
                    else: st.error("⚠️ 無法識別此代碼商品。")
                else: st.warning("⚠️ 數量與標的不能為空。")
                    
        st.markdown("<hr>", unsafe_allow_html=True)
        
        c_perf1, c_perf2, c_perf3, c_perf4 = st.columns(4)
        total_trades = tab_perf["wins"] + tab_perf["losses"]
        win_rate = (tab_perf["wins"] / total_trades * 100) if total_trades > 0 else 0.0
        c_perf1.metric("已實現總淨利 (Realized PnL)", fmt_money(tab_perf["realized_pnl"]))
        c_perf2.metric("累積領取股息 (Dividends)", fmt_money(tab_perf["total_div"]))
        c_perf3.metric("歷史交易勝率 (Win Rate)", f"{win_rate:.1f}%", f"{tab_perf['wins']}勝 {tab_perf['losses']}敗")
        c_perf4.metric("⚖️ 凱利公式建議押注比", f"{tab_perf['kelly_pct']:.1f}%")
        
        st.markdown("### 📜 歷史交割明細表")
        raw_lots = db_data["schemes"][current_scheme_name].get("lots", [])
        formatted_lots = []
        for l in raw_lots:
            sh = float(l.get("shares", 0))
            act = l.get("action", "BUY" if sh >= 0 else "SELL")
            if act == "DIVIDEND": act_str = "💸 配息"
            elif act == "BUY": act_str = "🟢 買進"
            else: act_str = "🔴 賣出"
                
            formatted_lots.append({
                "動作": act_str, "代碼": l.get("ticker", "").split('.')[0],
                "數量": abs(sh), "價格/總息": float(l.get("price", l.get("buy_price", 0))),
                "日期": str(l.get("date", l.get("buy_date", ""))), "決策備註": str(l.get("memo", ""))
            })
            
        lots_df = pd.DataFrame(formatted_lots)
        if lots_df.empty: lots_df = pd.DataFrame(columns=["動作", "代碼", "數量", "價格/總息", "日期", "決策備註"])
        edited_lots = st.data_editor(lots_df, num_rows="dynamic", use_container_width=True, key=f"editor_{market_label}")
        
        if st.button(f"📌 確認同步並寫入儲存庫", type="primary", key=f"save_btn_{market_label}"):
            with st.spinner('正在同步儲存庫...'):
                new_lots = []
                for _, row in edited_lots.iterrows():
                    tk_raw = row["代碼"]
                    if pd.isna(tk_raw): continue
                    tk = str(tk_raw).strip().upper()
                    if not tk or tk in ["NAN", "NONE"]: continue
                    
                    real_ticker, _ = smart_resolve_ticker(tk, MY_API_KEY)
                    if real_ticker:
                        act_val = str(row["動作"]).strip()
                        if "配息" in act_val: final_act = "DIVIDEND"
                        elif "買" in act_val: final_act = "BUY"
                        else: final_act = "SELL"
                        
                        sh_val = float(row["數量"] if not pd.isna(row["數量"]) else 0)
                        if final_act == "SELL": sh_val = -sh_val
                        elif final_act == "DIVIDEND": sh_val = 0.0
                        
                        new_lots.append({
                            "action": final_act, "ticker": real_ticker, "shares": sh_val,
                            "price": float(row["價格/總息"] if not pd.isna(row["價格/總息"]) else 0),
                            "date": str(row["日期"]) if not pd.isna(row["日期"]) else "",
                            "memo": str(row["決策備註"]) if not pd.isna(row["決策備註"]) else ""
                        })
                db_data["schemes"][current_scheme_name]["lots"] = new_lots
                save_portfolio(db_data)
                st.rerun()

    # 💰 子分頁 3: 智慧注水
    with tab_inject:
        st.markdown("### 💰 智慧型增量資金金流加碼控制台")
        add_cash = st.number_input("設定預定注水注入現款金額 (NTD)", min_value=0, value=0, step=10000, format="%d")
        inject_mode = st.radio("注入資金模型戰術選擇：", ["⚖️ 標準配置再平衡", "📈 右側順勢加碼 (僅挹注金叉多頭)", "📉 左側分批抄底 (僅挹注 RSI<40)"], horizontal=True)
        
        if add_cash > 0 and current_view_data:
            st.markdown("<div class='action-box'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:#0f172a !important; font-weight:900; margin-top:0;'>🎯 演算法自動化注水配置比例單：</h4>", unsafe_allow_html=True)
            ideal_total_val = local_total_val + add_cash
            buy_list = []
            
            eligible_items = []
            for item in current_view_data:
                ma50_v, ma200_v, rsi_val = item.get("ma50", 1), item.get("ma200", 1), item.get("rsi", 50)
                is_bear_cross = (ma50_v < ma200_v)
                if "右側順勢" in inject_mode and is_bear_cross and item.get("ticker") != "CASH": continue
                if "左側抄底" in inject_mode and rsi_val >= 40 and item.get("ticker") != "CASH": continue
                eligible_items.append(item)
                
            if not eligible_items: st.write("無符合資格之現貨標的。")
            else:
                for item in eligible_items:
                    tgt = item.get("target_pct", 0)
                    lev = item.get("leverage", 1.0)
                    dynamic_tgt_p = tgt
                    if lev >= 2.0:
                        if current_vix > 30.0: dynamic_tgt_p = 0.0
                        elif current_vix > 25.0: dynamic_tgt_p = tgt * 0.5
                    
                    ideal_target_ntd = ideal_total_val * (dynamic_tgt_p / 100.0)
                    shortfall_ntd = ideal_target_ntd - item.get("now_val_ntd", 0)
                    ma50_v = item.get("ma50", 1)
                    ma200_v = item.get("ma200", 1)
                    is_bear_cross = (ma50_v < ma200_v)
    
                    if shortfall_ntd > 0:
                        if item.get("ticker") == "CASH":
                            buy_units = shortfall_ntd / (1.0 if is_tw_mode else current_rate)
                            buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>💵 <span style='font-weight:900; width:120px; display:inline-block;'>保留資金部位</span>：建議存入 <b style='color:#0f172a;'>{fmt_money(buy_units)}</b> {'元' if is_tw_mode else '美元'}</li>")
                        elif item.get("ticker", "").startswith("^"): 
                            buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>📊 <span style='font-weight:900; width:120px; display:inline-block;'>{item.get('ticker', '')}</span>：建議加碼 <b style='color:#0f172a;'>NTD {fmt_money(shortfall_ntd)}</b></li>")
                        else:
                            if lev >= 2.0 and is_bear_cross:
                                buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{item.get('ticker').split('.')[0]}</span>：應配 NTD {fmt_money(shortfall_ntd)}，<span class='badge-hold'>🟡 死叉暫緩</span> 轉入現金儲備。</li>")
                            elif not market_breadth_bullish and lev >= 2.0:
                                buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{item.get('ticker').split('.')[0]}</span>：應配 NTD {fmt_money(shortfall_ntd)}，<span class='badge-hold'>⚠️ 大盤破線拒絕槓桿</span>。</li>")
                            else:
                                price_ntd = item.get("now_p", 1) if is_tw_mode else (item.get("now_p", 1) * current_rate)
                                shares_to_buy = int(shortfall_ntd / price_ntd) if price_ntd > 0 else 0
                                clean_name = item.get("ticker", "").split('.')[0]
                                if shares_to_buy > 0: 
                                    buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{clean_name}</span>：下達 <span class='badge-buy'>🟢 BUY TO OPEN</span> <span style='font-weight:900; color:#0f172a; margin-left:8px;'>{fmt_money(shares_to_buy)} 股</span> <span style='color:#64748b; font-size:0.95rem; margin-left:12px;'>(需 NTD {fmt_money(shares_to_buy * price_ntd)})</span></li>")
                
                if buy_list: st.markdown(f"<ul style='list-style-type:none; padding-left:0;'>{''.join(buy_list)}</ul>", unsafe_allow_html=True)
                else: st.write("模型比例完美收斂。")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 💸 3. 現金流與稅務水庫
# ==========================================
elif app_mode == "💸 現金流與稅務水庫":
    st.markdown("<div class='market-header global-market'>💸 被動現金流水庫與二代健保避稅預警 (Cashflow Terminal)</div>", unsafe_allow_html=True)
    
    all_div_records = []
    total_expected_div = 0
    total_tax_warning = []
    
    for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
        is_tw = "台股" in scheme_name
        raw_lots = db_data["schemes"][scheme_name].get("lots", [])
        raw_targets = db_data["schemes"][scheme_name].get("targets", {})
        agg_assets, perf_metrics = aggregate_lots(raw_lots, raw_targets)
        
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
    monthly_cashflow = total_expected_div / 12
    col_kpi2.metric("預測平均月被動收入", f"NTD {fmt_money(monthly_cashflow)}")
    col_kpi3.metric("被動收入可覆蓋基本開銷率", f"{(monthly_cashflow / 50000)*100:.1f}%", "以開銷 5 萬計")
    
    st.markdown("---")
    st.subheader("📆 被動收益分配現況表")
    if all_div_records:
        df_div = pd.DataFrame(all_div_records)
        st.dataframe(df_div.style.format({"庫存市值 (NTD)": "{:,.0f}", "當前股息殖利率": "{:.2f}%", "持倉均價成本殖利率 YoC": "{:.2f}%", "預期年化股利被動收入 (NTD)": "{:,.0f}"}), use_container_width=True)
    else: st.info("目前持倉中無高配息資產標的。")
        
    if total_tax_warning:
        st.markdown(f"<div class='action-box' style='background-color:#fffbeb; border-color:#b45309;'><h4 style='color:#b45309 !important;'>🚨 二代健保補充保費漏洞預警</h4><div style='font-size:1rem; line-height:1.6; color:#0f172a;'>{('<br>'.join(total_tax_warning))}</div></div>", unsafe_allow_html=True)

# ==========================================
# 🧬 機構級阿爾法模型 (Alpha Quants)
# ==========================================
elif app_mode == "🧬 機構級阿爾法模型 (Alpha Quants)":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-left-color: #8b5cf6;'>🧬 機構級阿爾法實驗室 (MVO & VaR & RS)</div>", unsafe_allow_html=True)
    st.info("💡 **模組說明**：本區包含華爾街法人的核心計量模型，包含馬可維茲最佳化權重、相對強弱矩陣與極端壓力測試。")
    
    target_scheme = st.selectbox("請選擇要分析的資產池：", ["🎯 台股主力配置", "🎯 美股主力配置"])
    raw_lots = db_data["schemes"][target_scheme].get("lots", [])
    raw_targets = db_data["schemes"][target_scheme].get("targets", {})
    agg_assets, _ = aggregate_lots(raw_lots, raw_targets)
    
    valid_tickers = [a["ticker"] for a in agg_assets if a["ticker"] != "CASH" and a["init_shares"] > 0]
    
    if not valid_tickers: st.warning("⚠️ 該資產池目前沒有足夠的有效持倉進行運算。")
    else:
        benchmark_tk = "^TWII" if "台股" in target_scheme else "^GSPC"
        fetch_tickers = valid_tickers + [benchmark_tk]
        
        with st.spinner("🧠 正在啟動蒙地卡羅引擎與下載 1 年期歷史回報矩陣..."):
            try:
                df_all = yf.download(fetch_tickers, period="1y", interval="1d", progress=False, session=yf_session)['Close']
                if isinstance(df_all, pd.Series): df_all = df_all.to_frame()
                df_all.dropna(inplace=True)
            except Exception as e:
                st.error("資料下載失敗，請稍後再試。")
                df_all = pd.DataFrame()
                
        if not df_all.empty:
            tab_rs, tab_mvo, tab_var = st.tabs(["⚔️ 曼斯菲爾德相對強弱 (RS)", "🧠 馬可維茲效率前緣 (MVO)", "🌪️ VaR 黑天鵝壓力測試"])
            
            with tab_rs:
                st.markdown("### ⚔️ 個股 vs 大盤相對強弱矩陣 (Mansfield RS)")
                rs_period = st.radio("選擇 RS 比較週期：", ["近半年 (120天)", "近一年 (252天)"], horizontal=True)
                days = 120 if "半年" in rs_period else 252
                
                if len(df_all) < 20: st.warning("歷史數據天數不足。")
                else:
                    calc_days = min(days, len(df_all) - 1)
                    bm_ret = (df_all[benchmark_tk].iloc[-1] / df_all[benchmark_tk].iloc[-calc_days]) - 1
                    
                    rs_data = []
                    for tk in valid_tickers:
                        if tk in df_all.columns:
                            tk_ret = (df_all[tk].iloc[-1] / df_all[tk].iloc[-calc_days]) - 1
                            rs_score = ((1 + tk_ret) / (1 + bm_ret) - 1) * 100
                            _, zh_name = smart_resolve_ticker(tk, MY_API_KEY)
                            
                            trend_emoji = "🔥 遠超大盤" if rs_score > 10 else ("🟢 強於大盤" if rs_score > 0 else ("🟡 略微落後" if rs_score > -10 else "🚨 嚴重落後"))
                            rs_data.append({
                                "代碼": f"{tk.split('.')[0]} {zh_name}", 
                                f"期間報酬率 ({calc_days}天)": f"{tk_ret*100:.2f}%", 
                                "RS 領先大盤指數": float(f"{rs_score:.2f}"),
                                "強度判定": trend_emoji
                            })
                    
                    if rs_data:
                        df_rs = pd.DataFrame(rs_data).sort_values(by="RS 領先大盤指數", ascending=False)
                        
                        def color_rs(val):
                            if isinstance(val, (int, float)):
                                color = '#10b981' if val > 0 else '#ef4444'
                                return f'color: {color}; font-weight: 800;'
                            return ''
                            
                        try:
                            styled_df = df_rs.style.map(color_rs, subset=['RS 領先大盤指數'])
                        except:
                            styled_df = df_rs.style.applymap(color_rs, subset=['RS 領先大盤指數'])
                            
                        st.dataframe(styled_df, use_container_width=True)
                        st.info("💡 **解讀**：正數代表跑贏大盤。資金注水時，應優先考慮加碼排名靠前的強勢股。")

            with tab_mvo:
                st.markdown("### 🧠 馬可維茲效率前緣最佳化 (Markowitz Efficient Frontier)")
                if len(valid_tickers) < 2: st.warning("⚠️ 最佳化至少需要 2 檔以上的資產。")
                else:
                    if st.button("🚀 啟動 5000 次蒙地卡羅模擬演算", type="primary"):
                        with st.spinner("正在進行矩陣運算與最佳化求解..."):
                            df_assets = df_all[valid_tickers]
                            returns = df_assets.pct_change().dropna()
                            mean_returns = returns.mean() * 252
                            cov_matrix = returns.cov() * 252
                            
                            num_portfolios = 5000
                            results = np.zeros((3, num_portfolios))
                            weights_record = []
                            
                            for i in range(num_portfolios):
                                weights = np.random.random(len(valid_tickers))
                                weights /= np.sum(weights)
                                weights_record.append(weights)
                                
                                p_return = np.sum(weights * mean_returns)
                                p_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                                results[0,i] = p_return
                                results[1,i] = p_std
                                results[2,i] = p_return / p_std
                                
                            max_sharpe_idx = np.argmax(results[2])
                            optimal_weights = weights_record[max_sharpe_idx]
                            
                            fig_mvo = px.scatter(
                                x=results[1]*100, y=results[0]*100, color=results[2],
                                labels={'x': '預期年化波動率 (Risk %)', 'y': '預期年化報酬率 (Return %)', 'color': '夏普值 (Sharpe)'},
                                title="5000 次模擬效率前緣分佈", template="plotly_white", color_continuous_scale="Viridis"
                            )
                            fig_mvo.add_trace(go.Scatter(x=[results[1, max_sharpe_idx]*100], y=[results[0, max_sharpe_idx]*100], mode='markers', marker=dict(color='red', size=15, symbol='star'), name='最高夏普黃金點'))
                            st.plotly_chart(fig_mvo, use_container_width=True)
                            
                            st.markdown("#### 🏆 演算法建議最佳黃金權重 (Optimal Target %)")
                            opt_data = []
                            for idx, tk in enumerate(valid_tickers):
                                clean_tk = tk.split('.')[0]
                                current_tgt = raw_targets.get(clean_tk, 0.0)
                                opt_data.append({"代碼": clean_tk, "目前 Target (%)": float(current_tgt), "AI 建議 Target (%)": round(optimal_weights[idx] * 100, 1)})
                            st.dataframe(pd.DataFrame(opt_data), use_container_width=True)

            with tab_var:
                st.markdown("### 🌪️ 歷史 VaR (Value at Risk) 黑天鵝壓力測試")
                current_vals = []
                for tk in valid_tickers:
                    cur_p = df_all[tk].iloc[-1]
                    shares = next((a["init_shares"] for a in agg_assets if a["ticker"] == tk), 0)
                    current_vals.append(cur_p * shares)
                
                total_eq_val = sum(current_vals)
                if total_eq_val == 0: st.warning("股票資產淨值為 0，無須壓力測試。")
                else:
                    cur_weights = np.array(current_vals) / total_eq_val
                    df_assets = df_all[valid_tickers]
                    returns = df_assets.pct_change().dropna()
                    port_returns = returns.dot(cur_weights)
                    
                    var_95_pct = np.percentile(port_returns, 5) * 100
                    var_99_pct = np.percentile(port_returns, 1) * 100
                    
                    st.markdown(f"<div style='background:#fef2f2; padding:20px; border-radius:10px; border:1px solid #fecaca; margin-bottom:20px;'><h4 style='color:#b91c1c; margin-top:0;'>📉 壓力測試兵推結果 (股票部位：NTD {fmt_money(total_eq_val)})</h4><ul style='font-size:1.1rem; color:#0f172a; margin-bottom:0;'><li><b>95% 信心水準 (20日發生1次)</b>：單日最差跌幅 <b>{var_95_pct:.2f}%</b>，帳戶蒸發 <b>NTD {fmt_money(abs(var_95_pct/100 * total_eq_val))}</b></li><li style='margin-top:10px;'><b>99% 信心水準 (黑天鵝股災)</b>：單日最差跌幅 <b>{var_99_pct:.2f}%</b>，帳戶蒸發 <b style='color:#ef4444;'>NTD {fmt_money(abs(var_99_pct/100 * total_eq_val))}</b></li></ul></div>", unsafe_allow_html=True)

# ==========================================
# 🤖 24H 守望者腳本 (Cron Bot)
# ==========================================
elif app_mode == "🤖 24H 守望者腳本 (Cron Bot)":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #0f766e 0%, #064e3b 100%); border-left-color: #34d399;'>🤖 24H 無頭守望者腳本產生器 (Cron Bot)</div>", unsafe_allow_html=True)
    st.success("✅ **機器人腳本生成成功！** 下方為系統為您專屬客製化寫好的自動化程式碼，請直接點擊下方下載按鈕。")
    st.markdown("### 📝 第一步：下載您的專屬守望者機器人")
    
    user_line_token = db_data.get('settings', {}).get('line_token', '')
    if not user_line_token: user_line_token = "請填入您的LINE_TOKEN"
        
    tks_us = [a['ticker'] for a in aggregate_lots(db_data['schemes']['🎯 美股主力配置'].get('lots', []), {})[0] if a['ticker'] != 'CASH']
    tks_tw = [a['ticker'] for a in aggregate_lots(db_data['schemes']['🎯 台股主力配置'].get('lots', []), {})[0] if a['ticker'] != 'CASH']
    bot_tickers = tks_us + tks_tw
    
    bot_code = f"""import yfinance as yf
import pandas as pd
import requests

# 您的設定
LINE_TOKEN = "{user_line_token}"
TICKERS = {bot_tickers}

def send_line(msg):
    if not LINE_TOKEN or LINE_TOKEN == "請填入您的LINE_TOKEN": return
    requests.post('https://notify-api.line.me/api/notify', headers={{'Authorization': f'Bearer {{LINE_TOKEN}}'}}, data={{'message': msg}})

def run_check():
    alerts = []
    try:
        vix = yf.Ticker("^VIX").fast_info['lastPrice']
        if vix > 25: alerts.append(f"⚠️ 大盤 VIX 飆高至 {{vix:.2f}}，系統建議啟動槓桿降載防禦。")
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
            atr_v = float(df['ATR'].iloc[-1])
            stop_p = max_p - (2.5 * atr_v)
            
            if cur_p < stop_p: alerts.append(f"🚨 {{tk}} 跌破 ATR 吊燈停損線 ({{stop_p:.2f}})！目前股價: {{cur_p:.2f}}。")
        except: pass
        
    if alerts: send_line("\\n".join(["[🤖 Quant 每日巡邏報告]"] + alerts))
    else: send_line("[🤖 Quant 每日巡邏報告]\\n✅ 全數資產皆在 ATR 安全線上，無異常。")

if __name__ == "__main__":
    run_check()
"""
    st.code(bot_code, language="python")
    st.download_button("⬇️ 點此下載 cron_bot.py", file_name="cron_bot.py", mime="text/x-python", data=bot_code)
    
    st.markdown("""
    ### ⚙️ 第二步：如何讓它每天免費自動執行？(使用 GitHub Actions)
    1. 在 GitHub 建立一個私有 (Private) 儲存庫。
    2. 將剛才下載的 `cron_bot.py` 以及一份 `requirements.txt` (寫入 `yfinance\\npandas\\nrequests`) 放進儲存庫。
    3. 在儲存庫裡建立資料夾與檔案：`.github/workflows/main.yml`。
    4. 將以下代碼貼入 `main.yml` 並存檔：
```yaml
    name: Daily Quant Bot Check
    on:
      schedule:
        - cron: '30 6 * * *'
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v2
          - name: Set up Python
            uses: actions/setup-python@v2
            with:
              python-version: '3.10'
          - name: Install dependencies
            run: pip install -r requirements.txt
          - name: Run Bot
            run: python cron_bot.py
    ```
    5. 完成！GitHub 會在每天台灣時間下午 2:30 免費啟動虛擬主機巡邏並發送 LINE 報告。
    """)

# ==========================================
# 🔍 全球宏觀市場終端
# ==========================================
elif app_mode == "🔍 全球宏觀市場終端":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); margin-bottom: 24px;'>📊 全球宏觀市場終端 (Global Macro Terminal)</div>", unsafe_allow_html=True)
    
    c_m1, c_m2 = st.columns([1, 2])
    market_choice = c_m1.radio("🌍 快速切換分析標的：", ["台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體", "自訂輸入個股"], horizontal=True)
    k_period = c_m2.radio("選擇量化回測週期 (Timeframe)：", ["日K", "週K", "月K", "年K"], horizontal=True)
    st.markdown("---")

    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = ""
    
    if market_choice == "自訂輸入個股": target_to_parse = st.text_input("輸入欲調研的資產代碼 (輸入完畢按 Enter)：", value="", placeholder="例如：2330 或 QQQ")
    else: target_to_parse = default_ticker
    
    if target_to_parse:
        ticker_input, zh_name = smart_resolve_ticker(target_to_parse, MY_API_KEY)
        if ticker_input:
            try:
                with st.spinner("連接雲端伺服器..."):
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
                        rsi_status = "🔴 過熱超買" if rsi_val > 70 else ("🟢 超跌低估" if rsi_val < 30 else "🟡 盤整")
                        
                        last_close = float(df['Close'].dropna().iloc[-1]) if not df['Close'].dropna().empty else 0.0
                        ma200_val = float(df['MA3'].dropna().iloc[-1]) if not df['MA3'].dropna().empty else last_close
                        
                        high_52w = float(df['High'].max()) if 'High' in df.columns and not pd.isna(df['High'].max()) else last_close
                        high_52w = max(high_52w, last_close)
                        
                        dd_pct = ((last_close - high_52w) / high_52w) * 100 if high_52w > 0 else 0.0

                        st.markdown("### 📊 量化多維戰略儀表板 (Market Metrics)")
                        cc1, cc2, cc3 = st.columns(3)
                        
                        if ticker_input.startswith("^"):
                            cc1.markdown(f"<div class='pro-card'><div class='data-label'>📈 最新大盤指數點位</div><div class='price-display'>{fmt_money(last_close)} 點</div><div style='color:#64748b; font-size:0.85rem; margin-top:8px;'>長線牛熊分界 ({n3}): {fmt_money(ma200_val)}</div></div>", unsafe_allow_html=True)
                            cc2.markdown(f"<div class='pro-card'><div class='data-label'>📉 歷史極值與波段回撤</div><div class='price-display' style='color:#ef4444 !important;'>{dd_pct:.2f}%</div><div style='color:#64748b; font-size:0.85rem; margin-top:8px;'>歷史頂部估值: {fmt_money(high_52w)} 點</div></div>", unsafe_allow_html=True)
                            pe_str, yd_str, sec_str = "大盤指數", "大盤指數", "大盤指數"
                        else:
                            try:
                                info = yf.Ticker(ticker_input, session=yf_session).info
                                pe_str = f"{float(info.get('trailingPE', 0) or 0):.1f} 倍"
                                yd_str = f"{float(info.get('dividendYield', 0) or 0)*100:.2f} %"
                                sec_str = info.get('sector', '未提供')
                            except: pe_str, yd_str, sec_str = "無/虧損", "無配息", "未提供"
                            cc1.markdown(f"<div class='pro-card'><div class='data-label'>🏢 系統歸屬板塊 (Sector)</div><div class='price-display' style='font-size:1.3rem;'>{sec_str}</div></div>", unsafe_allow_html=True)
                            cc2.markdown(f"<div class='pro-card'><div class='data-label'>🏦 核心基本面矩陣 (Fundamentals)</div><div class='price-display' style='font-size:1.2rem;'>PE: {pe_str} | 股息率: {yd_str}</div></div>", unsafe_allow_html=True)
                        
                        cc3.markdown(f"<div class='pro-card'><div class='data-label'>⚡ 短線技術動能掃描 (RSI)</div><div class='price-display'>{rsi_val:.1f}</div><div style='color:#0f172a; font-size:1rem; font-weight:700; margin-top:4px;'>系統診斷: {rsi_status}</div></div>", unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        clean_title = ticker_input.split('.')[0]
                        st.markdown(f"<h3 style='margin-bottom: 20px; border-left: 6px solid #3b82f6; padding-left: 12px;'>📈 {clean_title} {zh_name} 歷史技術軌跡 (Price Action)</h3>", unsafe_allow_html=True)
                        
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA1'], mode='lines', name=n1, line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA2'], mode='lines', name=n2, line=dict(color='#10b981', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA3'], mode='lines', name=n3, line=dict(color='#3b82f6', width=2)), row=1, col=1)
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="市場成交量", marker_color="#cbd5e1"), row=2, col=1)
                        fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_white", margin=dict(t=30, b=10, l=10, r=10), hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                        tab1, tab2 = st.tabs(["📈 AI 神經網絡戰略分析", "📰 全球市場事件與情緒掃描"])
                        with tab1:
                            if st.button("✨ 啟動 Gemini 神經網絡推演", key=f"ai_btn_{clean_title}", type="secondary", use_container_width=True):
                                if not MY_API_KEY: st.warning("⚠️ 請先於系統後台掛載 API Key。")
                                else:
                                    with st.spinner("🧠 連接 AI 運算矩陣..."):
                                        prompt = f"產出專屬戰略洞察：標的：{clean_title} {zh_name} | 結算價：{last_close:.2f} | RSI：{rsi_val:.1f}，請用專業繁體中文給出操作建議。"
                                        try:
                                            model = genai.GenerativeModel("gemini-3.5-flash")
                                            st.info(model.generate_content(prompt).text)
                                        except:
                                            model = genai.GenerativeModel("gemini-2.5-flash")
                                            st.info(model.generate_content(prompt).text)

                        with tab2:
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
                                if st.button("✨ 讓 Gemini 總結市場多空動能情緒", key=f"news_ai_btn_{clean_title}", type="primary", use_container_width=True):
                                    if not MY_API_KEY: st.warning("⚠️ 未偵測到 API Key。")
                                    else:
                                        with st.spinner("🧠 啟動事件驅動分析引擎..."):
                                            news_prompt = f"請判讀以下新聞的隱含多空情緒：\n\n{news_text_for_ai}"
                                            try:
                                                model = genai.GenerativeModel("gemini-2.5-flash")
                                                st.info(model.generate_content(news_prompt).text)
                                            except Exception as e: st.error("❌ 運算模組解析失敗。")
                            else: st.info("目前資料庫無收錄近點催化劑事件。")
            except Exception as e: st.error(f"❌ 底層錯誤：{str(e)}")
