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

.pro-card { 
    background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; 
    padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%;
    transition: all 0.25s ease-in-out;
}
.pro-card:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -4px rgba(0,0,0,0.08); border-color: #cbd5e1 !important; }

.kpi-card { 
    background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; 
    padding: 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); 
    display: flex; flex-direction: column; justify-content: center;
    transition: all 0.2s ease;
}
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

/* 指南手冊專用美化 */
.manual-highlight { background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-weight: 700; color: #0f172a; font-family: monospace; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# 🚀 智慧代碼正名資料庫
STOCK_NAME_DICT = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2308": "台達電",
    "2881": "富邦金", "2891": "中信金", "2412": "中華電", "2603": "長榮", "3231": "緯創",
    "6669": "緯穎", "2303": "聯電", "3711": "日月光投控", "6285": "啟碁", "2344": "華邦電", 
    "2337": "旺宏", "3034": "聯詠", "2379": "瑞昱", "0050": "元大台灣50", "006208": "富邦台50", 
    "0052": "富邦科技", "00881": "富邦台灣半導體", "0056": "元大高股息", "00878": "國泰永續高股息", 
    "00919": "群益台灣精選高息", "00929": "復華台灣科技優息", "00713": "元大台灣高息低波",
    "00631L": "元大台灣50正2", "00670L": "富邦NASDAQ正2", "00687B": "國泰20年美債", "00937B": "群益ESG投等債20+",
    "AAPL": "蘋果", "MSFT": "微軟", "NVDA": "輝達", "TSLA": "特斯拉", "AMD": "超微", 
    "QQQ": "納斯達克100", "VTI": "全美股市", "SCHD": "美國紅利", "VOO": "標普500", 
    "TQQQ": "納斯達克3倍多", "QLD": "納斯達克2倍多", "SOXL": "半導體3倍多"
}

TECH_CONCENTRATION_TICKERS = ["2330", "2454", "2382", "3231", "6669", "3034", "2379", "0052", "00881", "AAPL", "MSFT", "NVDA", "AMD", "QQQ", "TQQQ", "SOXL", "QLD"]

# ==========================================
# 🛡️ 智慧混合式資料庫引擎 (自我修復防呆版)
# ==========================================
DB_FILE = "portfolio_db.json"
USE_FIREBASE = False

try:
    if "firebase" in st.secrets:
        # 💡 自動清洗防呆：把多重 https:// 全部清掉，確保網址純淨
        raw_db_url = st.secrets["firebase"].get("databaseURL", "")
        clean_db_url = raw_db_url.replace("https://https://", "https://").strip()
        if not clean_db_url.startswith("https://"):
            clean_db_url = "https://" + clean_db_url
            
        cred_dict = dict(st.secrets["firebase"])
        cred_dict["private_key"] = cred_dict["private_key"].replace('\\n', '\n')
        
        # 💡 強制記憶體重置：檢查舊有連線是否卡住錯誤網址
        need_init = True
        if firebase_admin._apps:
            app = firebase_admin.get_app()
            if app.options.get('databaseURL') == clean_db_url:
                need_init = False
            else:
                # 發現網址更新！無情殺掉舊連線
                firebase_admin.delete_app(app)
                
        if need_init:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': clean_db_url
            })
            
        USE_FIREBASE = True
except Exception as e:
    st.sidebar.warning(f"⚠️ 雲端連線失敗，自動啟用「本機離線模式」保命。錯誤: {e}")
    USE_FIREBASE = False

def load_portfolio():
    default_data = {
        "global_goals": {"target_amt": 20000000, "target_years": 10}, 
        "settings": {"line_token": ""},
        "schemes": {"🎯 台股主力配置": {"market": "TW", "lots": [], "targets": {}}, "🎯 美股主力配置": {"market": "US", "lots": [], "targets": {}}}
    }
    
    if USE_FIREBASE:
        try:
            ref = db.reference('/quant_portfolio')
            data = ref.get()
            if data is None:
                ref.set(default_data)
                return default_data
            
            if "global_goals" not in data: data["global_goals"] = {"target_amt": 20000000, "target_years": 10}
            if "settings" not in data: data["settings"] = {"line_token": ""}
            if "schemes" not in data: data["schemes"] = default_data["schemes"]
            return data
        except Exception as e:
            st.error(f"雲端資料讀取失敗，載入預設值: {e}")
            return default_data
    else:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: 
                    data = json.load(f)
                    if "global_goals" not in data: data["global_goals"] = {"target_amt": 20000000, "target_years": 10}
                    if "settings" not in data: data["settings"] = {"line_token": ""}
                    if "schemes" in data: return data
            except: pass
        return default_data

def save_portfolio(data):
    if USE_FIREBASE:
        try:
            ref = db.reference('/quant_portfolio')
            ref.set(data)
        except Exception as e:
            st.error(f"寫入雲端資料庫失敗: {e}")
    else:
        with open(DB_FILE, "w", encoding="utf-8") as f: 
            json.dump(data, f, ensure_ascii=False, indent=4)

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

@st.cache_data(show_spinner=False, ttl=3600)
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
    if not ticker or ticker == "CASH": 
        return {"price": 1.0, "date": "最新匯率", "ma50": 1.0, "ma200": 1.0, "high52w": 1.0, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, "kd_k": 50.0, "atr": 0.0, "history_close": pd.Series(dtype=float)}
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
                high52w = max(float(recent_highs.max()), price)
                ma50 = float(df['MA2'].iloc[-1] or price) if len(closes) >= 50 else price
                ma200 = float(df['MA3'].iloc[-1] or price) if len(closes) >= 200 else price
                current_atr = float(df['ATR'].dropna().iloc[-1]) if not df['ATR'].dropna().empty else (price * 0.02)
                
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
                    "bias": bias, "rsi": current_rsi, "kd_k": current_k, "atr": current_atr, "history_close": closes, "full_df": df
                }
        
        if realtime_price > 0:
            fallback_df = pd.DataFrame({'Close': [realtime_price], 'High': [realtime_price], 'Low': [realtime_price], 'Open': [realtime_price], 'Volume': [0]}, index=[pd.Timestamp.now()])
            fallback_df['MA1'], fallback_df['MA2'], fallback_df['MA3'], fallback_df['Chandelier_Exit'] = realtime_price, realtime_price, realtime_price, realtime_price * 0.95
            return {
                "price": realtime_price, "date": "即時報價 (補齊)", "ma50": realtime_price, "ma200": realtime_price, 
                "high52w": realtime_price, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, "kd_k": 50.0, "atr": realtime_price*0.02, "history_close": pd.Series([realtime_price], dtype=float), "full_df": fallback_df
            }
    except: pass
    return None

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
    tw_tax_rate = 0.001 if (len(base_tk) == 5 or len(base_tk) == 6 or base_tk.startswith('00')) else 0.003

    if is_tw_market: est_buy_fee = max(tw_min_fee, int(round(gross_buy_amt * tw_standard_fee_rate * tw_discount))) if shares > 0 else 0
    else: est_buy_fee = max(us_min_fee, gross_buy_amt * us_fee_rate) if shares > 0 else 0
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
# 📊 左側邊欄：總經面板與 LINE Notify
# ==========================================
st.sidebar.title("🏦 Quant Terminal")
st.sidebar.markdown(f"📈 **宏觀匯率 USD/TWD：** `{current_rate:.2f}`")

# 📲 LINE Notify 設定區
with st.sidebar.expander("📲 LINE Notify 警報推播設定"):
    current_line_token = db_data.get("settings", {}).get("line_token", "")
    new_token = st.text_input("輸入 LINE Notify Token", value=current_line_token, type="password")
    if new_token != current_line_token:
        db_data["settings"]["line_token"] = new_token
        save_portfolio(db_data)
        st.rerun()
    if st.button("🔔 測試發送警報", use_container_width=True):
        if not new_token: st.warning("請先輸入 Token")
        else:
            success = send_line_notify(new_token, "✅ Quant Terminal 警報系統連線成功！您的量化大腦已上線。")
            if success: st.success("發送成功！請檢查手機。")
            else: st.error("發送失敗，請檢查 Token 是否正確。")

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
today = datetime.date.today()
if today.day >= 10 and today.day <= 15:
    st.sidebar.warning("📅 **本週總經預警**：\n即將公布 CPI 或 PPI 數據，請留意市場雙向洗盤，嚴禁重壓高槓桿部位。")

if MY_API_KEY: genai.configure(api_key=MY_API_KEY)

app_mode = st.sidebar.radio("系統導覽 (Modules)：", ["🏠 宏觀資產矩陣 (Dashboard)", "🇹🇼 台股主力量化倉位", "🇺🇸 美股主力量化倉位", "💸 現金流與稅務水庫", "🧪 戰略回測實驗室", "🔍 全球宏觀市場終端", "📖 系統操作指南 (User Manual)"])
st.sidebar.markdown("---")

# ==========================================
# 📖 新增：系統操作指南 (User Manual)
# ==========================================
if app_mode == "📖 系統操作指南 (User Manual)":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left-color: #64748b;'>📖 量化終端實戰操作指南 (Quant Playbook)</div>", unsafe_allow_html=True)
    
    st.info("這份手冊將教您如何將這個系統從『單純的記帳軟體』晉升為『為您賺錢的量化大腦』。請按照以下 4 個階段熟悉您的戰鬥中心。")
    
    with st.expander("📍 第一階段：新手起步 (如何建立與管理庫存)", expanded=True):
        st.markdown("""
        ### 1. 建立您的第一筆庫存
        要讓系統為您精算損益，您必須告訴系統您買了什麼。
        * **步驟**：點擊左側選單的 `🇹🇼 台股主力量化倉位` 或 `🇺🇸 美股` ➡️ 切換到 `📓 量化覆盤與日誌審判室` 分頁。
        * **操作**：在「交易日誌快速登錄」表單中，選擇 **🟢 開倉買進 (BUY)**，輸入代碼（例如 `0050` 或 `2330`）、股數、單價與日期。
        * **備註 (Memo)**：強烈建議填寫您買進的理由（例如「看均線黃金交叉買進」），這會在未來的 AI 覆盤中發揮極大作用。
        
        ### 2. 如何賣出並計算獲利？
        系統採用專業的**「平均成本結算法」**。
        * 當您選擇 **🔴 減碼賣出 (SELL)** 時，系統會自動用您當時的「平均買進成本」來扣除成本，並將賺到的錢記錄到 **「歷史已實現淨利」** 中。
        * 若您將某檔股票「全數賣出」且把目標權重設為 0%，系統會自動將它從盤面上隱藏，保持版面乾淨。
        """)

    with st.expander("📍 第二階段：日常盯盤 (看懂系統發出的買賣訊號)"):
        st.markdown("""
        ### 1. 看懂總經大盤的「三大紅綠燈」
        在畫面最左邊側邊欄，有三個決定您能否開槓桿的指標：
        * **🏛 利差 (10Y-3M)**：若亮紅燈代表債券倒掛（衰退前兆），嚴禁重壓。
        * **📉 VIX 恐慌指數**：衡量市場恐慌度。若數值大於 25，系統的演算法會強迫將您持有的槓桿部位（如 TQQQ, 00631L）的建議權重**強制砍半**。
        * **🕸️ 市場寬度 (S&P500)**：判斷現在是「真牛市」還是「拉抬權值股的假牛市」。若破線，系統會拒絕加碼槓桿。

        ### 2. 認識個股面板的「戰鬥指示燈」
        在 `📊 動態監控矩陣` 每個個股的最右側卡片，系統會比對您的「目標權重」與「實際市值」，給出以下精確指令：
        * <span class='badge-buy'>🟢 BUY TO OPEN</span>：比例不足，且均線多頭，建議立刻買進補齊。
        * <span class='badge-sell'>🔴 SELL TO CLOSE</span>：比例過高，建議賣出部分停利。
        * <span class='badge-hold'>🟡 MA BEARISH 暫緩</span>：雖然您的比例不足，但目前該股處於「均線死亡交叉（空頭）」，系統為保護您，**強制鎖定買進建議**，避免左側接刀。
        * <span class='badge-sell' style='background:#b91c1c; color:white;'>🚨 SELL ALL 觸發清倉</span>：股價跌破了「ATR 吊燈停利線」，請**無條件全數平倉**保住利潤！
        """, unsafe_allow_html=True)

    with st.expander("📍 第三階段：資金控管 (如何加碼與停損)"):
        st.markdown("""
        ### 1. 使用「ATR 吊燈移動停利 (Chandelier Exit)」
        * 這套系統最核心的防守機制！在監控盤上方有一個拉桿 **「📉 ATR 吊燈停利乘數」**。
        * **原理**：系統會自動記住您建倉以來的「最高價」，並向下減去 N 倍的「真實波動均值 (ATR)」。
        * **好處**：0050 的波動小，停損線就會設得很近；TQQQ 的波動大，停損線會自動拉寬。一旦 K 線實體跌破這條紅色的虛線，代表趨勢徹底反轉，請絕對遵守紀律執行清倉。

        ### 2. 智慧增量資金注水 (Pyramiding)
        每個月發薪水想定期定額？請到 **`💰 智慧階梯式增量資金注水控制台`** 分頁。
        輸入您這個月要投入的現金（如 30,000），並選擇策略：
        * **⚖️ 標準配置**：哪一檔低於目標比例，就補哪一檔。
        * **📈 右側順勢加碼**：把錢全部集中打在「目前均線呈現多頭排列」的強勢股上，讓獲利奔跑。
        * **📉 左側分批抄底**：只把錢拿去買 RSI < 40 的超跌委屈股。
        """)

    with st.expander("📍 第四階段：進階優化 (AI 覆盤與現金流收租)"):
        st.markdown("""
        ### 1. 讓 AI 當您的毒舌交易教練
        在交易日誌分頁的下方，點擊 **[✨ 讓 Gemini 檢討我的交易決策]**。
        AI 會讀取您每一筆交易的「備註」，算出您的勝率與「非理性交易佔比」，無情地戳破您的情緒化操作盲點！

        ### 2. 領取股息與二代健保避雷
        當您投資的 ETF 配息時：
        * 請到交易日誌選 <span class='manual-highlight'>💸 領取股息 (DIVIDEND)</span> 寫入總金額。
        * 到左側選單進入 **`💸 現金流與稅務水庫`**。系統會幫您算出每檔股票真實的「持倉成本殖利率 (YoC)」。
        * **稅務預警**：系統若算出您某檔台股單次配息將超過 **20,000 元台幣**，會立刻亮起紅燈，警告您將被扣取 2.11% 的二代健保補充保費，建議您提早規劃！
        
        ### 3. 戰略實驗室回測
        想知道 0050 用 50MA 還是 60MA 比較準？進入 **`🧪 戰略回測實驗室`**，輸入代碼並拖拉參數，系統會瞬間跑完過去 10 年的歷史數據，畫出對比圖表，用數學證明您的策略能否打敗大盤死抱策略。
        """, unsafe_allow_html=True)

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
    
    with st.expander("🎯 設定AUM戰略目標 (Strategic AUM Target)"):
        g_cols = st.columns(2)
        cur_target_amt = db_data["global_goals"].get("target_amt", 20000000)
        cur_target_years = db_data["global_goals"].get("target_years", 10)
        goal_amt = g_cols[0].number_input("設定總目標資產 (NTD)", min_value=0, value=int(cur_target_amt), step=100000)
        goal_yrs = g_cols[1].number_input("預估達成年數 (Years)", min_value=1, value=int(cur_target_years), step=1)
        if st.button("💾 寫入戰略目標"):
            db_data["global_goals"] = {"target_amt": goal_amt, "target_years": goal_yrs}
            save_portfolio(db_data)
            st.toast("✅ 戰略目標更新完畢！", icon="✅")
            st.rerun()

    total_aum_ntd, tw_aum_ntd, us_aum_ntd = 0, 0, 0
    total_cost_ntd = 0
    total_div_ntd, global_realized_pnl = 0, 0
    combined_hist_df = pd.DataFrame()
    price_hist_for_corr = pd.DataFrame() 
    cash_total_ntd = 0
    pie_data = []

    with st.spinner("🔄 正在聚合全球資產矩陣與演算歷史軌跡..."):
        for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
            is_tw = "台股" in scheme_name
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
                    
                    if asset.get("ticker", "") == "CASH": 
                        now_val_ntd = init_sh * rate
                        asset_cost_ntd = now_val_ntd
                        cash_total_ntd += now_val_ntd
                    else: 
                        now_val_ntd = now_p * rate * init_sh
                        net_cost, _, _, _, _, _ = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw, rate)
                        asset_cost_ntd = net_cost
                        
                        hist_series = m_data.get("history_close")
                        if not hist_series.empty and not asset["ticker"].startswith("^"):
                            val_series = hist_series * init_sh * rate
                            if combined_hist_df.empty: combined_hist_df = val_series.to_frame(name=asset["ticker"])
                            else:
                                if asset["ticker"] in combined_hist_df.columns: combined_hist_df[asset["ticker"]] = combined_hist_df[asset["ticker"]].add(val_series, fill_value=0)
                                else: combined_hist_df = combined_hist_df.join(val_series.rename(asset["ticker"]), how='outer')
                                    
                            clean_tk_name = asset["ticker"].split('.')[0]
                            if price_hist_for_corr.empty: price_hist_for_corr = hist_series.to_frame(name=clean_tk_name)
                            elif clean_tk_name not in price_hist_for_corr.columns: price_hist_for_corr = price_hist_for_corr.join(hist_series.rename(clean_tk_name), how='outer')

                    total_aum_ntd += now_val_ntd
                    if is_tw: tw_aum_ntd += now_val_ntd
                    else: us_aum_ntd += now_val_ntd
                    total_cost_ntd += asset_cost_ntd
                    if now_val_ntd > 0: pie_data.append({"Asset": asset.get("ticker", "").split('.')[0], "Value": now_val_ntd})

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
    cumulative_ret = (((total_aum_ntd + global_realized_pnl + total_div_ntd) / total_cost_ntd) - 1) * 100 if total_cost_ntd > 0 else 0.0

    g1, g2, g3, g4 = st.columns(4)
    g1.markdown(f"<div class='kpi-card' style='border-top: 5px solid #8b5cf6;'><div class='data-label'>設定目標資產 (Target AUM)</div><div class='ticker-display'>NTD {fmt_money(target_amount)}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='kpi-card' style='border-top: 5px solid #ef4444;'><div class='data-label'>資產缺口 (Capital Shortfall)</div><div class='ticker-display'>NTD {fmt_money(shortfall)}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='kpi-card' style='border-top: 5px solid #10b981;'><div class='data-label'>隱含要求回報率 (Req. CAGR)</div><div class='ticker-display'>{req_cagr:.2f}%</div></div>", unsafe_allow_html=True)
    pnl_c_global = "#10b981" if cumulative_ret >= 0 else "#ef4444"
    g4.markdown(f"<div class='kpi-card' style='border-top: 5px solid {pnl_c_global};'><div class='data-label'>含息總和回報率 (Total Return)</div><div class='ticker-display' style='color:{pnl_c_global} !important;'>{cumulative_ret:+.2f}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 📊 全球板塊資金分佈與歷史戰績")
    d_col1, d_col2 = st.columns([1, 1.2])
    with d_col1:
        if pie_data:
            df_pie = pd.DataFrame(pie_data)
            fig_pie = px.pie(df_pie, values='Value', names='Asset', hole=0.55, template="plotly_white")
            custom_colors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899', '#84cc16', '#14b8a6', '#f43f5e']
            fig_pie.update_traces(textinfo='percent+label', marker=dict(colors=custom_colors, line=dict(color='#ffffff', width=2)))
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True, key="global_donut_chart", config={'displayModeBar': False})
        else:
            st.info("暫無持倉數據可供繪製配置圖。")
            
    with d_col2:
        kpi_html = f"""
        <div style='display:flex; flex-direction:column; gap:12px;'>
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
        st.markdown(f'<div class="market-header global-market" style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-left-color: #8b5cf6;">📈 全球資產歷史淨值走勢 (Historical AUM Curve)</div>', unsafe_allow_html=True)
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
        fig_eq.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), yaxis_title=y_title, xaxis_title="", hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False}, key="dashboard_global_eq_chart")

    with st.expander("🕸️ 系統性風險防禦矩陣：持倉資產相關性熱力圖 (Correlation Heatmap)"):
        st.info("💡 **量化避險指南**：深藍色 (+1.0) 代表完全正相關 (同漲同跌，風險集中)；深紅色 (-1.0) 代表負相關 (具備避險與平滑淨值之功能)。若大量部位超過 +0.8，建議增加美債或現金部位。")
        if not price_hist_for_corr.empty and len(price_hist_for_corr.columns) > 1:
            price_hist_for_corr = price_hist_for_corr.ffill().dropna()
            corr_matrix = price_hist_for_corr.pct_change().corr()
            fig_corr = px.imshow(corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu", zmin=-1, zmax=1, template="plotly_white")
            fig_corr.update_layout(height=500, margin=dict(t=30, b=30, l=30, r=30))
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.warning("目前持倉標的種類不足（或數據缺失），無法繪製關聯性熱力圖。")

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
    local_total_val, local_total_cost, local_total_exposure = 0, 0, 0
    tech_exposure_val = 0
    
    target_portfolio, tab_perf = aggregate_lots(db_data["schemes"][current_scheme_name].get("lots", []), db_data["schemes"][current_scheme_name].get("targets", {}))
    
    if target_portfolio:
        with st.spinner(f"🔄 正在同步雲端即時報價與風險 Beta 矩陣..."):
            for asset in target_portfolio:
                m_data = fetch_market_data(asset.get("ticker", ""))
                if m_data and m_data.get("price", 0) > 0:
                    now_p = m_data.get("price", 0)
                    date_str = m_data.get("date", "")
                    
                    net_cost, net_val, total_fees, total_tax, net_pnl, net_pnl_pct = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw_mode, current_rate)
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
                    dist_52w = ((now_p - m_data.get("high52w", now_p)) / m_data.get("high52w", now_p) * 100) if m_data.get("high52w", 0) > 0 else 0.0
                    
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
                        "rsi": m_data.get("rsi", 50), "kd_k": m_data.get("kd_k", 50), "atr": m_data.get("atr", 0.0),
                        "earliest_buy_date": asset.get("earliest_buy_date"), "history_close": hist_close, "full_df": m_data.get("full_df")
                    })

    # 📓 子分頁 2: 歷史交易明細與 AI 覆盤
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
                        st.toast(f"✅ 交易確認已入帳：{resolved_name} ({real_tk}) {act_str}！", icon="✅")
                        st.rerun()
                    else: st.error("⚠️ 無法識別此代碼商品。")
                else: st.warning("⚠️ 數量與標的不能為空。")
                    
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.subheader("🏆 量化風控教練與歷史戰績 (Performance Review)")
        total_trades = tab_perf["wins"] + tab_perf["losses"]
        win_rate = (tab_perf["wins"] / total_trades * 100) if total_trades > 0 else 0.0
        irr_score = (tab_perf["irrational_trades"] / max(tab_perf["total_actions"], 1) * 100)
        
        c_perf1, c_perf2, c_perf3, c_perf4 = st.columns(4)
        c_perf1.metric("已實現總淨利 (Realized PnL)", fmt_money(tab_perf["realized_pnl"]))
        c_perf2.metric("累積領取股息 (Dividends)", fmt_money(tab_perf["total_div"]))
        c_perf3.metric("歷史交易勝率 (Win Rate)", f"{win_rate:.1f}%", f"{tab_perf['wins']}勝 {tab_perf['losses']}敗")
        c_perf4.metric("⚖️ 凱利公式建議最高押注比", f"{tab_perf['kelly_pct']:.1f}%", "防破產最佳資金模型")
        
        if irr_score > 20: st.warning(f"⚠️ **心魔警告**：系統從您的備註欄偵測到，您有 **{irr_score:.1f}%** 的操作屬於「情緒化交易 (追高/手癢)」，請嚴守紀律！")
        
        st.markdown("### 📜 歷史交割明細明細表")
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
        
        if st.button(f"📌 確認同步並寫入雲端資料庫", type="primary", key=f"save_btn_{market_label}"):
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
                st.toast("✅ 交割總帳儲存成功！", icon="✅")
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("✨ 讓 Gemini 檢討我的交易決策與備註", key=f"review_ai_btn_{market_label}", use_container_width=True):
            if not MY_API_KEY: st.warning("⚠️ 請先掛載 Gemini API Key。")
            else:
                with st.spinner("🧠 正在分析您的歷史備註與情緒指徵..."):
                    history_str = lots_df.to_string(index=False)
                    prompt = f"你是嚴格的華爾街量化交易教練。這是我近期的歷史交易明細：\n{history_str}\n我的總勝率是 {win_rate:.1f}%。請審判我的進出場理由是否具有理性邏輯，用專業繁體中文給予教練指導。"
                    try:
                        model = genai.GenerativeModel("gemini-3.5-flash")
                        st.info(model.generate_content(prompt).text)
                    except:
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        st.info(model.generate_content(prompt).text)

    # 📊 子分頁 1: 動態監控盤
    with tab_monitor:
        if current_view_data:
            local_total_profit = local_total_val - local_total_cost
            local_cumulative_ret = (local_total_profit / local_total_cost) * 100 if local_total_cost > 0 else 0.0
            total_leverage_ratio = local_total_exposure / local_total_val if local_total_val > 0 else 0.0
            tech_ratio = (tech_exposure_val / local_total_val * 100) if local_total_val > 0 else 0
            
            pnl_color = "#10b981" if local_total_profit >= 0 else "#ef4444"
            pnl_sign = "+" if local_total_profit >= 0 else ""
            
            st.markdown(f"""
            <div style='display:flex; gap: 16px; margin-bottom: 24px; flex-wrap:wrap;'>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #3b82f6;'>
                    <div class='data-label'>建倉總成本 (Gross Cost Basis)</div>
                    <div class='ticker-display'>NTD {fmt_money(local_total_cost)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #8b5cf6;'>
                    <div class='data-label'>即時變現淨市值 (Mark-to-Market)</div>
                    <div class='ticker-display'>NTD {fmt_money(local_total_val)}</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid #f59e0b;'>
                    <div class='data-label'>組合風險波動放大率 (Portfolio Beta)</div>
                    <div class='ticker-display' style='color:#f59e0b !important;'>{total_leverage_ratio:.2f}x</div>
                </div>
                <div class='kpi-card' style='flex:1; min-width:180px; border-top: 4px solid {pnl_color};'>
                    <div class='data-label'>多頭未實現損益 (Unrealized PnL)</div>
                    <div class='ticker-display' style='color:{pnl_color} !important;'>{pnl_sign}NTD {fmt_money(local_total_profit)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if tech_ratio > 70:
                st.warning(f"⚠️ **Beta 集中度警報**：您的持倉中科技與半導體資產（如 2330, 0052, QQQ 等）的權重已高達 **{tech_ratio:.1f}%**。一旦板塊震盪將承受集體重挫風險，請謹慎增建槓桿部位！")
            
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
                    rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>📉 <b>{clean_name}</b> ➡️ 價格跌破 ATR 吊燈安全線 <b>{stop_loss_price:.2f}</b>，觸發 <span class='badge-sell'>🚨 CHANDELIER EXIT (強制清倉停利)</span> 建議全數平倉保護獲利。</li>")
                elif abs(diff_pct) > rebalance_threshold:
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: 
                            rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>💵 <b>現金保留款水位</b> ➡️ 建議 <span class='badge-buy'>🟢 BUY TO OPEN (增量注水)</span> <b>{fmt_money(diff_amt)} {unit}</b></li>")
                        else: 
                            rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>💵 <b>現金保留款水位</b> ➡️ 建議 <span class='badge-sell'>🔴 SELL TO CLOSE (提領退守)</span> <b>{fmt_money(abs(diff_amt))} {unit}</b></li>")
                    else:
                        price_ntd = item.get("now_p", 1) * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        is_bear_cross = (ma50_v < ma200_v)
                        
                        vix_warning_text = ""
                        if dynamic_tgt_p != tgt_p: vix_warning_text = f" <span style='color:#ef4444; font-size:0.9rem;'>(VIX 恐慌調節)</span>"
                        
                        if shares_diff > 0:
                            if lev >= 2.0 and is_bear_cross:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <b>{clean_name}</b> ➡️ 權重不足，但目前觸發 <span class='badge-hold'>🟡 MA BEARISH (空頭防守暫緩)</span> <b>系統已鎖定買進權限</b>，避免左側接刀內耗。</li>")
                            elif not market_breadth_bullish and lev >= 2.0:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <b>{clean_name}</b> ➡️ 權重不足，但因 <span class='badge-hold'>⚠️ 市場寬度跌破均線</span> <b>建議暫停放大槓桿部位</b>。</li>")
                            else:
                                rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <b>{clean_name}</b> ➡️ 比例不足{vix_warning_text}，指引 <span class='badge-buy'>🟢 BUY TO OPEN (順勢建倉)</span> <b>{fmt_money(shares_diff)} 股</b> <span style='color:#64748b; font-size:0.9rem;'>(約 NTD {fmt_money(shares_diff * price_ntd)})</span></li>")
                        elif shares_diff < 0:
                            rebalance_orders.append(f"<li style='margin-bottom:12px; font-size:1.1rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>📉 <b>{clean_name}</b> ➡️ 比例過高{vix_warning_text}，指引 <span class='badge-sell'>🔴 SELL TO CLOSE (減碼平倉)</span> <b>{fmt_money(abs(shares_diff))} 股</b></li>")
            
            if rebalance_orders:
                st.markdown(f"<div class='action-box'><h4 style='color:#b45309 !important; font-weight:900; margin-top:0; font-size:1.3rem; letter-spacing:0.5px;'>⚡ 演算法交易控制台指令單 (Algorithmic Balancing Orders)</h4><div style='color:#475569 !important; margin-bottom:16px; font-size:0.95rem; font-weight:600;'>已綜合精算「ATR 吊燈移動停利線」、「資產偏離度」與「中長線移動平均線」狀態：</div><ul style='margin-bottom:0; padding-left:0; list-style-type:none;'>{''.join(rebalance_orders)}</ul></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='action-box' style='background:#f0fdf4; border:1px solid #cbd5e1; border-left:6px solid #10b981;'><h4 style='color:#166534 !important; font-weight:900; margin-top:0; font-size:1.3rem; letter-spacing:0.5px;'>✅ 全域風險資產結構穩健 (Risk Balanced)</h4><div style='color:#166534 !important; font-size:1rem; font-weight:600;'>目前全體底層現貨與槓桿部位均完美收斂於演算法安全容錯區間，未觸及任何停損條件。</div></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            for item in current_view_data:
                if item.get("init_shares") <= 0.001 and item.get("target_pct") <= 0: continue

                c = st.columns([1.5, 1.6, 1.5, 1.2, 1.3, 2.9])
                
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
                    c[0].markdown(f"<div class='ticker-display'>💵 現金部位</div><div class='stock-name-display'>台/外幣保留款 (CASH)</div><div class='price-display'>TWD/USD</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>持倉帳戶餘額 (Account Bal.):</div><div class='data-value'>NTD {fmt_money(item.get('net_buy_cost', 0))}</div><div class='data-label' style='margin-top:12px;'>法幣淨等值 (Fiat Val.):</div><div class='data-value'>NTD {fmt_money(now_v)}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>未實現淨損益 (Net Pnl):</div><div class='data-value' style='color:#64748b !important;'>---</div><div class='data-label' style='margin-top:12px;'>絕對報酬率 (Return):</div><div class='data-value' style='color:#64748b !important;'>---</div>", unsafe_allow_html=True)
                    c[3].markdown(f"<div class='data-label'>風險波動係數 (Beta):</div><div class='data-value' style='color:#10b981 !important;'>0.00x (無風險)</div><div class='data-label' style='margin-top:12px;'>歷史已實現淨利 (Realized PnL):</div><div class='data-value' style='color:#10b981 !important;'>NTD {fmt_money(item.get('realized_pnl', 0))}</div>", unsafe_allow_html=True)
                    c[4].markdown(f"<div class='data-label'>乖離率 (BIAS):</div><div class='data-value' style='color:#64748b !important;'>---</div><div class='data-label' style='margin-top:12px;'>🧠 終端戰術 (Tactics):</div><div class='data-value' style='color:#64748b !important;'>現金水庫調度</div>", unsafe_allow_html=True)
                else:
                    pnl_ntd = item.get('net_pnl', 0)
                    pnl_pct = item.get('net_pnl_pct', 0)
                    item_pnl_color = "#10b981" if pnl_ntd >= 0 else "#ef4444"
                    item_pnl_sign = "+" if pnl_ntd >= 0 else ""
                    
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='stock-name-display'>{zh_name}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {n_p:.2f}</div><div style='margin-top:6px; font-size:0.95rem; font-weight:900; color:#0f172a !important;'>📦 庫存: {fmt_money(shares_qty)} 股</div><div class='date-display'>持倉天數: {item.get('holding_days', 0)} 天</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>建倉總均價成本 (Cost):</div><div class='data-value'>NTD {fmt_money(item.get('net_buy_cost', 0))}</div><div class='data-label' style='margin-top:12px;'>預估變現淨市值 (M2M Val):</div><div class='data-value'>NTD {fmt_money(item.get('net_real_val', 0))}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>未實現淨損益 (PnL):</div><div class='data-value' style='color:{item_pnl_color} !important;'>{item_pnl_sign}{fmt_money(pnl_ntd)}</div><div class='data-label' style='margin-top:12px;'>全時年化報酬率 (Ann. ROI):</div><div class='data-value' style='color:{item_pnl_color} !important;'>{item_pnl_sign}{item.get('ann_roi', 0):.1f}%</div>", unsafe_allow_html=True)
                    
                    is_bear = n_p < ma200_v
                    is_bear_cross = ma50_v < ma200_v
                    if not is_bear_cross: trend_tag = "<span style='color:#10b981; font-weight:900;'>🟢 多頭黃金交叉</span>"
                    else: trend_tag = "<span style='color:#ef4444; font-weight:900;'>🔴 空頭死亡交叉</span>"
                        
                    trail_color = "#ef4444" if is_trailing_stop else "#64748b"
                    c[3].markdown(f"<div class='data-label'>中長線趨勢位階:</div><div>{trend_tag}</div><div class='data-label' style='margin-top:12px;'>ATR 吊燈停損線 (Stop):</div><div class='data-value' style='color:{trail_color} !important;'>{stop_loss_price:.2f} ({trail_dd:.1f}%)</div>", unsafe_allow_html=True)
                    
                    bias_color = "#ef4444" if item.get('bias', 0) >= 25 else ("#f59e0b" if item.get('bias', 0) >= 15 else ("#10b981" if item.get('bias', 0) <= -15 else "#64748b"))
                    k_val = item.get("kd_k", 50.0)
                    rsi_val = item.get("rsi", 50.0)
                    bias_val = item.get('bias', 0)
                    yoc_val = item.get('yoc', 0)
                    
                    tactical_action = "<span style='color:#64748b;'>⚖️ 戰略中立持有</span>"
                    if is_trailing_stop: tactical_action = f"<span style='color:#ef4444; font-weight:900;'>🚨 觸發 ATR 停利退出</span>"
                    elif is_bear_cross and lev >= 2.0: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🛑 均線死叉避險</span>"
                    elif not is_bear and (k_val < 25 or rsi_val < 35): tactical_action = "<span style='color:#10b981; font-weight:900;'>🟢 逢低抄底買點</span>"
                    elif k_val > 80 or rsi_val > 75: tactical_action = "<span style='color:#f59e0b; font-weight:900;'>⚠️ 動能過熱警戒</span>"
                    elif bias_val >= 20: tactical_action = "<span style='color:#ef4444; font-weight:900;'>🚨 乖離過大止盈</span>"
                        
                    c[4].markdown(f"<div class='data-label'>52週高點乖離 (52W):</div><div class='data-value' style='color:#3b82f6 !important;'>{item.get('dist_52w',0):+.1f}%</div><div class='data-label' style='margin-top:12px;'>🧠 終端戰術 (Tactics):</div><div style='font-size:0.95rem; font-weight:700;'>{tactical_action}</div>", unsafe_allow_html=True)

                with c[5]:
                    st.markdown("<div class='data-label'>戰略目標權重模型比例 (%) ✍️</div>", unsafe_allow_html=True)
                    clean_tk_tgt = item.get('ticker', '').split('.')[0]
                    new_tgt = st.number_input(
                        "Target", value=float(tgt_p), step=1.0, min_value=0.0, max_value=100.0,
                        key=f"tgt_{current_scheme_name}_{clean_tk_tgt}", label_visibility="collapsed"
                    )
                    
                    if new_tgt != float(tgt_p):
                        db_data["schemes"][current_scheme_name]["targets"][clean_tk_tgt] = new_tgt
                        save_portfolio(db_data)
                        st.rerun()

                    diff = real_pct - dynamic_tgt_p
                    target_val = local_total_val * (dynamic_tgt_p / 100.0)
                    diff_val = target_val - now_v
                    
                    box_bg = "#ffffff" if abs(diff) <= rebalance_threshold else "#fffbeb"
                    box_border = "#e2e8f0" if abs(diff) <= rebalance_threshold else "#f59e0b"
                    title_color = "#0f172a" if abs(diff) <= rebalance_threshold else "#b45309"
                    title_text = "✅ 權重配置達最佳化" if abs(diff) <= rebalance_threshold else f"⚠️ 模型偏離 {diff:+.1f}%"
                    if is_trailing_stop and item.get("ticker") != "CASH": box_bg, box_border, title_color, title_text = "#fef2f2", "#f87171", "#b91c1c", "🚨 ATR 強制清倉平倉"
                    
                    vix_warn_str = f" <span style='color:#ef4444;'>(VIX風險調節 ➡️ {dynamic_tgt_p}%)</span>" if dynamic_tgt_p != new_tgt else ""
                    progress_html = f"<div style='margin-top:8px; margin-bottom:6px; font-size:0.8rem; color:#475569; font-weight:700;'>現時占比 {real_pct:.1f}% / 成本殖利率 YoC: <span style='color:#059669;'>{yoc_val:.1f}%</span> / 目標 {new_tgt}%{vix_warn_str}</div><div style='width: 100%; background-color: #cbd5e1; border-radius: 99px; height: 10px; overflow:hidden;'><div style='width: {min(100, real_pct)}%; background-color: {'#10b981' if abs(diff) <= rebalance_threshold else '#f59e0b'}; height: 100%; border-radius: 99px;'></div></div>"
                    
                    if item.get("ticker") == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-buy'>🟢 ADD 注資</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a !important; margin-left:8px;'>{fmt_money(diff_amt)} {unit}</span></div>"
                        elif diff_amt < 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-sell'>🔴 SUB 提領</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a !important; margin-left:8px;'>{fmt_money(abs(diff_amt))} {unit}</span></div>"
                        else: action_msg = f"<div style='margin-top:16px;'><span class='badge-hold'>無指示</span></div>"
                    else:
                        price_ntd = n_p * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        if is_trailing_stop: action_msg = f"<div style='margin-top:16px;'><span class='badge-sell' style='background:#b91c1c; color:white;'>🚨 SELL ALL 觸發清倉</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a !important; margin-left:8px;'>{fmt_money(shares_qty)} 股</span></div>"
                        elif shares_diff > 0: 
                            if lev >= 2.0 and is_bear_cross: action_msg = f"<div style='margin-top:16px;'><span class='badge-hold'>🟡 MA BEARISH 暫緩</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a !important; margin-left:8px;'>{fmt_money(shares_diff)} 股</span></div>"
                            else: action_msg = f"<div style='margin-top:16px;'><span class='badge-buy'>🟢 BUY TO OPEN 建倉</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a !important; margin-left:8px;'>{fmt_money(shares_diff)} 股</span></div>"
                        elif shares_diff < 0: action_msg = f"<div style='margin-top:16px;'><span class='badge-sell'>🔴 SELL TO CLOSE 平倉</span> <span style='font-weight:900; font-size:1.15rem; color:#0f172a !important; margin-left:8px;'>{fmt_money(abs(shares_diff))} 股</span></div>"
                        else: action_msg = f"<div style='margin-top:16px;'><span class='badge-hold'>無指示</span></div>"

                    action_html = f"<div class='pro-card' style='background-color:{box_bg} !important; border-color:{box_border} !important; padding:18px; margin-top:4px;'><div style='color:{title_color} !important; font-weight:800; font-size:0.95rem; text-transform:uppercase;'>{title_text}</div>{progress_html}{action_msg}</div>"
                    st.markdown(action_html, unsafe_allow_html=True)

                if item.get("ticker") != "CASH":
                    with st.expander(f"📈 展開 {clean_name} 歷史 K 線與買賣點位標註 (Trade Annotations)"):
                        df_full = item.get("full_df")
                        if df_full is not None and not df_full.empty and 'MA1' in df_full.columns:
                            fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                            fig_k.add_trace(go.Candlestick(x=df_full.index, open=df_full['Open'], high=df_full['High'], low=df_full['Low'], close=df_full['Close'], name="K線"), row=1, col=1)
                            
                            if 'Chandelier_Exit' in df_full.columns:
                                fig_k.add_trace(go.Scatter(x=df_full.index, y=df_full['Chandelier_Exit'], mode='lines', name="ATR 吊燈停利線", line=dict(color='#ef4444', width=1.5, dash='dot')), row=1, col=1)
                                
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
                                    y_shift = 20 if t_action == "B" else -20
                                    fig_k.add_annotation(x=t_date, y=t_price, text=t_action, showarrow=True, arrowhead=1, arrowcolor=marker_color, arrowsize=1, arrowwidth=2, font=dict(color="white", size=10, family="Inter"), bgcolor=marker_color, opacity=0.8, ay=y_shift, row=1, col=1)
                                except: pass

                            fig_k.add_trace(go.Bar(x=df_full.index, y=df_full['Volume'], name="成交量", marker_color="#cbd5e1"), row=2, col=1)
                            fig_k.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white", margin=dict(t=30, b=10, l=10, r=10), hovermode="x unified")
                            st.plotly_chart(fig_k, use_container_width=True, config={'displayModeBar': False}, key=f"kline_{market_label}_{clean_name}")
                        else: st.info("無有效 K 線圖陣列。")

                st.markdown("<hr>", unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🤖 AI 量化戰略兵推 (Quant Intelligence)")
            st.info("💡 點擊下方按鈕，AI 將綜合審視您的「美債利差」、「均線交叉」、「ATR 停損」與「市場寬度」，下達頂級決策邏輯。")
            
            if st.button(f"✨ 啟動 Gemini 演算法兵推", key=f"ai_btn_{market_label}", type="primary", use_container_width=True):
                if not MY_API_KEY: st.warning("⚠️ 系統連線失敗：請先配置您的 Gemini API Key。")
                else:
                    with st.spinner("🧠 機構級神經網絡交易模型推演中..."):
                        portfolio_summary = f"【美債 10Y-3M 利差狀態】: {yield_spread:+.2f}% ({'倒掛警戒中' if yield_spread < 0 else '擴張格局正軌'})\n【S&P 500 市場寬度】: {'均線之上(多頭)' if market_breadth_bullish else '均線之下(系統風險)'}\n\n"
                        for item in current_view_data:
                            tk_name = item.get('ticker', '').split('.')[0]
                            now_v = item.get("now_val_ntd", 0)
                            lev = item.get("leverage", 1.0)
                            real_pct = (now_v / local_total_val * 100) if local_total_val > 0 else 0
                            
                            tgt = item.get('target_pct', 0)
                            dynamic_tgt_p = tgt
                            if lev >= 2.0:
                                if current_vix > 30.0: dynamic_tgt_p = 0.0
                                elif current_vix > 25.0: dynamic_tgt_p = tgt * 0.5
                            
                            diff_pct = real_pct - dynamic_tgt_p
                            portfolio_summary += (
                                f"🔹 標的：{tk_name} (波動風險: {lev}x)\n"
                                f"   - 戰略狀態：原目標 {tgt}% / 動態 VIX 調降後目標 {dynamic_tgt_p}% / 實際 {real_pct:.1f}% (偏離 {diff_pct:+.1f}%)\n"
                                f"   - 均線位階：50MA = {item.get('ma50',0):.2f} / 200MA = {item.get('ma200',0):.2f} ({'黃金交叉' if item.get('ma50',0) > item.get('ma200',0) else '死亡交叉'})\n"
                                f"   - 風險指標：目前已從建倉高點回落 {item.get('trailing_dd',0):.1f}% (ATR停利線設於 -{atr_multiplier*item.get('atr',0)/max(1,item.get('max_since_buy',1))*100:.1f}%)\n\n"
                            )
                        prompt = f"你是對沖基金首席操盤手。請根據數據下達指令：\n{portfolio_summary}\n請給出：1. 宏觀組合與總經風控診斷 2. 是否觸及 ATR 停利或均線死叉標的精確操盤指令 3. 演算法再平衡平衡調配。用專業繁體金融術語回覆。"
                        try:
                            model = genai.GenerativeModel("gemini-3.5-flash")
                            st.info(model.generate_content(prompt).text)
                        except:
                            model = genai.GenerativeModel("gemini-2.5-flash")
                            st.info(model.generate_content(prompt).text)

    # 💰 子分頁 3: 智慧增量資金注水控制台
    with tab_inject:
        st.markdown("### 💰 智慧型增量資金金流加碼控制台")
        add_cash = st.number_input("設定預定注水注入現款金額 (NTD)", min_value=0, value=0, step=10000, format="%d")
        inject_mode = st.radio("注入資金模型戰術選擇：", ["⚖️ 標準配置再平衡 (維持戰略分配)", "📈 右側順勢加碼 (僅挹注金叉多頭排列標的)", "📉 左側分批抄底 (僅挹注 RSI<40 短線超跌標的)"], horizontal=True)
        
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
                
            if not eligible_items: st.write("當前戰術篩選條件下，無符合資格之現貨標的。")
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
                                buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{item.get('ticker').split('.')[0]}</span>：應配本金 NTD {fmt_money(shortfall_ntd)}，因觸發 <span class='badge-hold'>🟡 MA BEARISH 暫緩</span> <b>自動轉入現金儲備</b>。</li>")
                            elif not market_breadth_bullish and lev >= 2.0:
                                buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{item.get('ticker').split('.')[0]}</span>：應配本金 NTD {fmt_money(shortfall_ntd)}，因 <span class='badge-hold'>⚠️ 大盤寬度背離</span> <b>拒絕加碼槓桿</b>。</li>")
                            else:
                                price_ntd = item.get("now_p", 1) if is_tw_mode else (item.get("now_p", 1) * current_rate)
                                shares_to_buy = int(shortfall_ntd / price_ntd) if price_ntd > 0 else 0
                                clean_name = item.get("ticker", "").split('.')[0]
                                if shares_to_buy > 0: 
                                    buy_list.append(f"<li style='margin-bottom:12px; font-size:1.15rem; border-bottom:1px solid #e2e8f0; padding-bottom:8px;'>🛒 <span style='font-weight:900; width:120px; display:inline-block;'>{clean_name}</span>：下達 <span class='badge-buy'>🟢 BUY TO OPEN (加碼)</span> <span style='font-weight:900; color:#0f172a; margin-left:8px;'>{fmt_money(shares_to_buy)} 股</span> <span style='color:#64748b; font-size:0.95rem; margin-left:12px;'>(需資金 NTD {fmt_money(shares_to_buy * price_ntd)})</span></li>")
                
                if buy_list: st.markdown(f"<ul style='list-style-type:none; padding-left:0;'>{''.join(buy_list)}</ul>", unsafe_allow_html=True)
                else: st.write("模型比例完美收斂，資金建議留存無風險儲備款水庫。")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 💸 3. 新增分頁：現金流與稅務水庫
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
                        total_tax_warning.append(f"⚠️ <b>{asset['ticker'].split('.')[0]}</b>：預估單次配息將達 <b>NTD {fmt_money(est_single_div)}</b>，突破兩萬元限制，將被依法強制扣取 <b>2.11% 二代健保補充保費 (預估損失 NTD {fmt_money(est_single_div * 0.0211)})</b>。")

                all_div_records.append({
                    "資產代碼": asset['ticker'].split('.')[0], "庫存市值 (NTD)": val_ntd,
                    "當前股息殖利率": yield_val * 100, "持倉均價成本殖利率 YoC": asset.get('yoc', 0),
                    "預期年化股利被動收入 (NTD)": expected_annual_div
                })
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("預測未來 12 個月總配息", f"NTD {fmt_money(total_expected_div)}")
    monthly_cashflow = total_expected_div / 12
    col_kpi2.metric("預測平均月被動收入", f"NTD {fmt_money(monthly_cashflow)}")
    col_kpi3.metric("被動收入可覆蓋基本開銷率", f"{(monthly_cashflow / 50000)*100:.1f}%", "以基本開銷月支 5 萬計")
    
    st.markdown("---")
    st.subheader("📆 被動收益分配現況表")
    if all_div_records:
        df_div = pd.DataFrame(all_div_records)
        st.dataframe(df_div.style.format({"庫存市值 (NTD)": "{:,.0f}", "當前股息殖利率": "{:.2f}%", "持倉均價成本殖利率 YoC": "{:.2f}%", "預期年化股利被動收入 (NTD)": "{:,.0f}"}), use_container_width=True)
    else: st.info("目前持倉中無高配息資產標的。")
        
    if total_tax_warning:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<div class='action-box' style='background-color:#fffbeb; border-color:#b45309;'><h4 style='color:#b45309 !important;'>🚨 二代健保補充保費漏洞預警</h4><div style='font-size:1rem; line-height:1.6; color:#0f172a;'>{('<br>'.join(total_tax_warning))}</div></div>", unsafe_allow_html=True)
        
    st.subheader("❄️ DRIP 股息自動再投資複利效應模擬")
    future_value = total_expected_div * (1.08 ** 10)
    st.info(f"📈 依據複利齒輪模型，將今年配息全數進行 **DRIP (股息再買回現貨)**，在指數年化 8% 報酬率下，10 年後這筆無本利息將滾大為 **NTD {fmt_money(future_value)}**！")

# ==========================================
# 🧪 新增分頁 5: 戰略回測實驗室 (Backtesting Lab)
# ==========================================
elif app_mode == "🧪 戰略回測實驗室":
    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #4338ca 0%, #0f172a 100%); border-left-color: #34d399;'>🧪 歷史量化回測與策略沙盒 (Backtesting Sandbox)</div>", unsafe_allow_html=True)
    st.info("💡 **模組說明**：輸入資產代碼並調整您的量化指標（均線與 ATR 停利）。系統將模擬在歷史資料中套用您的策略，對比「無腦死抱」的報酬率，檢驗您的戰略是否能打敗大盤。")

    c_b1, c_b2, c_b3, c_b4, c_b5 = st.columns([1.5, 1, 1, 1, 1])
    test_ticker = c_b1.text_input("輸入測試標的", value="0050", placeholder="例如: 0050, QQQ, TQQQ")
    test_period = c_b2.selectbox("回測歷史長度", ["1y", "3y", "5y", "10y"], index=2)
    short_ma_days = c_b3.number_input("短均線 (MA Short)", min_value=5, max_value=60, value=50)
    long_ma_days = c_b4.number_input("長均線 (MA Long)", min_value=20, max_value=300, value=200)
    test_atr_mult = c_b5.number_input("ATR 停利乘數", min_value=1.0, max_value=5.0, value=2.5, step=0.1)

    if st.button("🚀 啟動演算法歷史回測", type="primary", use_container_width=True):
        resolved_tk, tk_name = smart_resolve_ticker(test_ticker, MY_API_KEY)
        if resolved_tk:
            with st.spinner(f"正在針對 {tk_name} ({resolved_tk}) 進行高頻歷史模擬回測..."):
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
                    
                    # 💡 回測核心演算法：多頭均線 且 股價大於停損線 = 買進(1)，否則 = 空手(0)
                    df_test['Signal'] = np.where((df_test['MA_S'] > df_test['MA_L']) & (df_test['Close'] > df_test['Stop_Loss']), 1, 0)
                    df_test['Position'] = df_test['Signal'].shift(1).fillna(0) # 避免前瞻偏差
                    
                    df_test['Market_Returns'] = df_test['Close'].pct_change()
                    df_test['Strategy_Returns'] = df_test['Position'] * df_test['Market_Returns']
                    
                    df_test['Buy_and_Hold'] = (1 + df_test['Market_Returns']).cumprod() * 100
                    df_test['Quant_Strategy'] = (1 + df_test['Strategy_Returns']).cumprod() * 100
                    
                    bh_return = df_test['Buy_and_Hold'].iloc[-1] - 100
                    strat_return = df_test['Quant_Strategy'].iloc[-1] - 100
                    
                    st.markdown("### 🏆 回測戰績結算報告")
                    c_res1, c_res2 = st.columns(2)
                    c_res1.metric("無腦買進並持有 (Buy & Hold) 總報酬", f"{bh_return:.2f}%")
                    c_res2.metric("量化模型策略 (Quant Strategy) 總報酬", f"{strat_return:.2f}%", f"{strat_return - bh_return:+.2f}% vs B&H")
                    
                    if strat_return > bh_return: st.success("🎉 您的演算法成功打敗大盤死抱策略！在空頭市場成功發揮了停損避險的作用。")
                    else: st.warning("⚠️ 在這段歷史區間，市場呈現單邊瘋漲或頻繁雙巴，導致您的策略因反覆停損而內耗，未能跑贏無腦抱股。建議放寬均線或調高 ATR 乘數。")

                    fig_bt = go.Figure()
                    fig_bt.add_trace(go.Scatter(x=df_test.index, y=df_test['Buy_and_Hold'], name='無腦買進 (Buy & Hold)', line=dict(color='#64748b', width=2)))
                    fig_bt.add_trace(go.Scatter(x=df_test.index, y=df_test['Quant_Strategy'], name='量化策略 (Quant Strategy)', line=dict(color='#10b981', width=3)))
                    fig_bt.update_layout(title="資金累積成長淨值曲線 (基準: 100)", hovermode="x unified", template="plotly_white", height=500)
                    st.plotly_chart(fig_bt, use_container_width=True)
                else: st.error("無歷史數據可供回測。")
        else: st.error("無效的資產代碼。")

# ==========================================
# 🔍 6. 全球宏觀市場終端
# ==========================================
elif app_mode == "🔍 全球宏觀市場終端":
    st.sidebar.header("🌍 宏觀大盤快搜 (Global Indices)")
    market_choice = st.sidebar.radio("快速切換分析標的：", ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"])

    st.markdown("<div class='market-header global-market' style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); margin-bottom: 24px;'>📊 全球宏觀市場終端 (Global Macro Terminal)</div>", unsafe_allow_html=True)
    k_period = st.radio("選擇量化回測週期 (Timeframe)：", ["日K", "週K", "月K", "年K"], horizontal=True)
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
                        dd_pct = ((last_close - high_52w) / high_52w) * 100 if high52w > 0 else 0.0

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
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"terminal_stock_chart_{clean_title}")

                        tab1, tab2 = st.tabs(["📈 AI 神經網絡戰略分析", "📰 全球市場事件與情緒掃描"])
                        
                        with tab1:
                            st.markdown("### 🤖 標的資產量化解析 (AI Analysis)")
                            if st.button("✨ 啟動 Gemini 神經網絡推演", key=f"ai_btn_{clean_title}", type="secondary", use_container_width=True):
                                if not MY_API_KEY: st.warning("⚠️ 請先於系統後台掛載 Gemini API Key。")
                                else:
                                    with st.spinner("🧠 連接 AI 運算矩陣進行深度解析..."):
                                        prompt = f"你是華爾街頂尖機構分析師。請根據數據產出專屬戰略洞察：標的：{clean_title} {zh_name} | 結算價：{last_close:.2f} | RSI：{rsi_val:.1f}，請用專業繁體中文給出操作建議。"
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
                                if st.button("✨ 讓 Gemini 總結市場多空動能情緒", key=f"news_ai_btn_{clean_title}", type="primary", use_container_width=True):
                                    if not MY_API_KEY: st.warning("⚠️ 系統連線失敗：未偵測到 API Key。")
                                    else:
                                        with st.spinner("🧠 啟動事件驅動分析引擎..."):
                                            news_prompt = f"請判讀以下新聞的隱含多空情緒：\n\n{news_text_for_ai}"
                                            try:
                                                model = genai.GenerativeModel("gemini-2.5-flash")
                                                st.info(model.generate_content(news_prompt).text)
                                            except Exception as e: st.error("❌ 運算模組解析失敗。")
                            else: st.info("目前資料庫無收錄該資產近期重點催化劑事件。")
            except Exception as e: st.error(f"❌ 模組載入中斷，底層錯誤：{str(e)}")
