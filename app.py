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
# 🔑 終極安全 API Key 讀取機制
# ==========================================
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    MY_API_KEY = ""

# ==========================================
# 0. 核心抗封鎖引擎
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 1. 頁面配置與現代化 SaaS 級 CSS
# ==========================================
st.set_page_config(layout="wide", page_title="機構級量化決策終端", page_icon="🏦")

privacy_mode = st.sidebar.toggle("👁️ 隱藏金額防窺 (Privacy Mode)", value=False)

def fmt_money(val, decimals=0):
    if privacy_mode: return "****"
    if decimals == 0: return f"{int(val):,}"
    return f"{float(val):,.{decimals}f}"

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
    
    .market-header { 
        padding: 12px 18px; border-radius: 6px; font-weight: 800; 
        margin-bottom: 20px; font-size: 1.15rem; color: #f8fafc !important;
        background: #0f172a; text-transform: uppercase; letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .tw-market { border-left: 5px solid #059669; }
    .us-market { border-left: 5px solid #2563eb; }
    .global-market { border-left: 5px solid #8b5cf6; }
    
    .pro-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); height: 100%; }
    .kpi-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center; }
    
    .ticker-display { font-size: 1.6rem; font-weight: 900; line-height: 1.1; color: #0f172a; letter-spacing: -0.5px; }
    .stock-name-display { font-size: 0.9rem; color: #64748b; font-weight: 700; margin-top: 4px; margin-bottom: 8px; }
    .price-display { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-top: 4px; }
    .date-display { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; font-weight: 600; text-transform: uppercase; }
    
    .data-label { font-size: 0.75rem; color: #64748b; margin-bottom: 4px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .data-value { font-size: 1.05rem; font-weight: 800; color: #1e293b; }
    
    .badge-pnl { display: inline-block; padding: 4px 10px; border-radius: 4px; color: white; font-weight: 800; font-size: 0.9rem; }
    .pnl-pos { background-color: #10b981; }
    .pnl-neg { background-color: #ef4444; }
    
    .modebar { display: none !important; }
    hr { border-color: #e2e8f0; margin: 2rem 0; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f8fafc; border-radius: 6px 6px 0 0; padding: 0 20px; color: #64748b; font-weight: 700;}
    .stTabs [aria-selected="true"] { background-color: #0f172a !important; color: white !important; border-bottom: 3px solid #10b981; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 🛡️ 史詩級三維度解析引擎
# ==========================================
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
    if ticker == "CASH": return 1.0
    t = ticker.upper()
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if t.endswith("R.TW") or t.endswith("R.TWO"): return -1.0
    us_3x = ["TQQQ", "SOXL", "UPRO", "UDOW", "TMF", "FAS", "TECL", "CURE", "NAIL", "YINN", "WEBL", "DPST", "FNGU"]
    us_2x = ["QLD", "SSO", "USD", "UWM", "MVV", "NVDL", "TSLL"]
    if t.split('.')[0] in us_3x: return 3.0
    if t.split('.')[0] in us_2x: return 2.0
    return 1.0

# ==========================================
# 3. 📉 即時數據與量化指標抓取引擎
# ==========================================
def fetch_market_data(ticker):
    if not ticker or ticker == "CASH": 
        return {"price": 1.0, "date": "最新即時匯率", "ma200": 1.0, "high52w": 1.0, "drawdown": 0.0, "bias": 0.0, "rsi": 50.0, "kd_k": 50.0, "history_close": pd.Series(dtype=float)}
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        realtime_price = float(t_obj.fast_info.get('lastPrice', 0) or 0)
        df = yf.download(ticker, period="1y", progress=False, session=yf_session)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df.dropna(subset=['Close'], inplace=True)
            closes, highs, lows = df['Close'], df['High'], df['Low']
            
            if not closes.empty: 
                price = realtime_price if realtime_price > 0 else float(closes.iloc[-1] or 0)
                date_str = "最新即時報價" if realtime_price > 0 else closes.index[-1].strftime("%Y-%m-%d")
                high52w = max(float(highs.max()), price)
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
                    "price": price, "date": date_str, "ma200": ma200, "high52w": high52w, "drawdown": drawdown, 
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
                for s_name, s_data in data.get("schemes", {}).items():
                    if "assets" in s_data and "lots" not in s_data:
                        s_data["lots"], s_data["targets"] = [], {}
                        for a in s_data["assets"]:
                            tk = a.get("ticker", "")
                            if tk:
                                clean_tk = tk.split('.')[0]
                                s_data["lots"].append({
                                    "ticker": tk, "shares": a.get("init_shares", 0),
                                    "buy_price": a.get("buy_price", a.get("init_price", 0)), "buy_date": a.get("buy_date", "")
                                })
                                s_data["targets"][clean_tk] = a.get("target_pct", 0.0)
                        del s_data["assets"]
                return data
        except: pass
    return default_data

def save_portfolio(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

db_data = load_portfolio()

def aggregate_lots(lots, targets):
    agg = {}
    for lot in lots:
        tk = lot["ticker"]
        if not tk or tk.upper() == "NAN": continue
        clean_tk = tk.split('.')[0]
        if tk not in agg:
            agg[tk] = {"ticker": tk, "init_shares": 0.0, "total_cost": 0.0, "target_pct": targets.get(clean_tk, 0.0)}
        shares = float(lot.get("shares", 0))
        price = float(lot.get("buy_price", 0))
        agg[tk]["init_shares"] += shares
        if tk == "CASH": agg[tk]["total_cost"] += shares
        else: agg[tk]["total_cost"] += shares * price
    
    res = []
    for tk, v in agg.items():
        if v["init_shares"] > 0:
            v["buy_price"] = 1.0 if tk == "CASH" else (v["total_cost"] / v["init_shares"])
        else: v["buy_price"] = 0.0
        v["leverage"] = get_leverage(tk)
        res.append(v)
    return res

twd_data = fetch_market_data("TWD=X")
current_rate = twd_data["price"] if twd_data and twd_data["price"] > 0 else 32.5
vix_data = fetch_market_data("^VIX")
current_vix = vix_data["price"] if vix_data and vix_data["price"] > 0 else 15.0

# ==========================================
# 📊 左側邊欄：宏觀、情緒與💡費率設置
# ==========================================
st.sidebar.title("🏦 量化決策終端")
st.sidebar.markdown(f"📈 **匯率 USD/TWD：** `{current_rate:.2f}`")

# 💡 消滅 NAN Bug (強化過濾器)
for scheme in db_data["schemes"].values():
    scheme["lots"] = [lot for lot in scheme["lots"] if lot.get("ticker") and str(lot.get("ticker")).upper() != "NAN"]

if current_vix >= 30: vix_color, vix_status = "#10b981", "恐慌 (買點)"
elif current_vix <= 12: vix_color, vix_status = "#ef4444", "極低 (防守)"
elif current_vix >= 20: vix_color, vix_status = "#f59e0b", "波動加劇"
else: vix_color, vix_status = "#64748b", "市場穩定"

st.sidebar.markdown(f"""
<div style='padding:10px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {vix_color}; border-radius:6px; margin-bottom:10px;'>
    <div style='color:#64748b; font-size:0.8rem; font-weight:700; margin-bottom:2px;'>📉 VIX 恐慌指數</div>
    <div style='color:#0f172a; font-size:1.2rem; font-weight:900;'>{current_vix:.2f} <span style='font-size:0.85rem; color:{vix_color}; font-weight:700;'>{vix_status}</span></div>
</div>
""", unsafe_allow_html=True)

tw_light_signal = "🟢 綠燈 (31分)"  
st.sidebar.markdown(f"""
<div style='padding:10px; background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid #10b981; border-radius:6px; margin-bottom:10px;'>
    <div style='color:#64748b; font-size:0.8rem; font-weight:700; margin-bottom:2px;'>🚦 景氣對策信號 (台股)</div>
    <div style='color:#0f172a; font-size:1.0rem; font-weight:900;'>{tw_light_signal}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
# 💡 專業費率設置面板 (Req: 獲利扣除費用)
st.sidebar.subheader("⚙️ 費率自訂 (Fee Settings)")
with st.sidebar.expander("🇹🇼 台股交易費率", expanded=False):
    tw_fee_discount = st.slider("證券商手續費折扣 (折)", 1.0, 10.0, 2.8, 0.1, help="一般為  standard 1.425‰ 乘以折扣。網路下單通常為 6折 或更低。")
    tw_min_fee = st.number_input("台股手續費低消 (元)", value=20)
    
with st.sidebar.expander("🇺🇸 美股交易費率", expanded=False):
    us_fee_type = st.radio("美股計費方式", ["免手續費 (0)", "按股計費 (per share)", "按筆計費 (per order)"])
    if us_fee_type == "按股計費 (per share)": us_fee_val = st.number_input("每股費用 (USD)", value=0.005, format="%.4f")
    elif us_fee_type == "按筆計費 (per order)": us_fee_val = st.number_input("每筆費用 (USD)", value=5.0)
    else: us_fee_val = 0.0

st.sidebar.markdown("---")
api_key = MY_API_KEY
if api_key: genai.configure(api_key=api_key)

app_mode = st.sidebar.radio("模組導覽 (Modules)：", ["🏠 總體財富總覽", "🇹🇼 台股量化部位管理", "🇺🇸 美股量化部位管理", "🔍 全球市場量化終端"])
st.sidebar.markdown("---")

# ==========================================
# 🎯 核心費率精算引擎
# ==========================================
def calculate_net_pnl_stats(item, is_tw_market, fx_rate):
    """
    💡 核心精算函數：綜合買入、賣出費用與證交稅，計算「真實損益」
    """
    base_tk = item['ticker'].split('.')[0]
    
    # 0. 排除指數與現金
    if item['ticker'].startswith("^") or item['ticker'] == "CASH":
        gross_cost = item['asset_cost'] # 原本 Aggregation 算出的 Groos 成本
        current_val = item['now_val_ntd']
        return gross_cost, current_val, 0, 0, 0, 0

    shares = item['init_shares']
    avg_buy_p = item['buy_price'] # 這邊是 aggregate 的平均粗成本價格
    current_p = item['now_p']
    
    tw_standard_fee_rate = 0.001425
    
    # 💡 證交稅偵測：標準 0.3%，ETF 為 0.1%。
    is_etf = len(base_tk) == 5 or len(base_tk) == 6 or base_tk.startswith('00')
    tw_tax_rate = 0.001 if is_etf else 0.003

    # 1. 歷史買入成本精算 (Currency Symbol: Original)
    gross_buy_amt = shares * avg_buy_p
    
    if is_tw_market:
        est_buy_fee = max(tw_min_fee, gross_buy_amt * tw_standard_fee_rate * (tw_fee_discount/10.0))
        net_buy_cost_curr = gross_buy_amt + est_buy_fee
    else:
        if us_fee_type == "按股計費 (per share)": est_buy_fee = shares * us_fee_val
        elif us_fee_type == "按筆計費 (per order)": est_buy_fee = us_fee_val # 簡化假設
        else: est_buy_fee = 0.0
        net_buy_cost_curr = gross_buy_amt + est_buy_fee

    # 2. 預估賣出市值精算 (若是現在賣出)
    gross_sell_amt = shares * current_p
    
    if is_tw_market:
        est_sell_fee = max(tw_min_fee, gross_sell_amt * tw_standard_fee_rate * (tw_fee_discount/10.0))
        est_sell_tax = gross_sell_amt * tw_tax_rate
        net_sell_amt_curr = gross_sell_amt - est_sell_fee - est_sell_tax
    else:
        if us_fee_type == "按股計費 (per share)": est_sell_fee = shares * us_fee_val
        elif us_fee_type == "按筆計費 (per order)": est_sell_fee = us_fee_val
        else: est_sell_fee = 0.0
        est_sell_tax = 0.0 # 美股一般不代扣證交稅
        net_sell_amt_curr = gross_sell_amt - est_sell_fee
        
    # 3. 轉換為 NTD
    mult = 1.0 if is_tw_market else fx_rate
    net_buy_cost_ntd = net_buy_cost_curr * mult
    net_sell_amt_ntd = net_sell_amt_curr * mult
    total_estimated_fees_ntd = (est_buy_fee + est_sell_fee) * mult
    total_estimated_tax_ntd = est_sell_tax * mult
    
    # 4. 真實精算獲利
    net_pnl_ntd = net_sell_amt_ntd - net_buy_cost_ntd
    net_pnl_pct = (net_pnl_ntd / net_buy_cost_ntd * 100) if net_buy_cost_ntd > 0 else 0
    
    # 返回：精算總成本, 精算淨市值, 總手續費, 證交稅, 淨獲利, 淨獲利%
    return net_buy_cost_ntd, net_sell_amt_ntd, total_estimated_fees_ntd, total_estimated_tax_ntd, net_pnl_ntd, net_pnl_pct

# ==========================================
# 5. 主功能：總體財富總覽 (Dashboard)
# ==========================================
if app_mode == "🏠 總體財富總覽":
    st.markdown("<h1>🏠 總體財富總覽 (Wealth精算版)</h1>", unsafe_allow_html=True)
    
    with st.expander("🎯 設定全球財務自由目標 (Global Financial Goals)"):
        g_cols = st.columns(2)
        cur_target_amt = db_data["global_goals"]["target_amt"]
        cur_target_years = db_data["global_goals"]["target_years"]
        goal_amt = g_cols[0].number_input("設定總目標資產 (NTD)", min_value=0, value=int(cur_target_amt), step=100000)
        goal_yrs = g_cols[1].number_input("預估達成年數 (Years)", min_value=1, value=int(cur_target_years), step=1)
        if st.button("儲存總目標"):
            db_data["global_goals"] = {"target_amt": goal_amt, "target_years": goal_yrs}
            save_portfolio(db_data)
            st.success("目標儲存成功！")
            st.rerun()

    total_aum_ntd, tw_aum_ntd, us_aum_ntd = 0, 0, 0
    total_cost_ntd = 0 # 💡 這裡將改為存儲淨成本
    combined_hist_df = pd.DataFrame()
    cash_total_ntd = 0

    with st.spinner("🔄 正在聚合全球資產與精算歷史軌跡..."):
        for scheme_name in ["🎯 台股主力配置", "🎯 美股主力配置"]:
            is_tw = "台股" in scheme_name
            raw_lots = db_data["schemes"][scheme_name]["lots"]
            raw_targets = db_data["schemes"][scheme_name]["targets"]
            agg_assets = aggregate_lots(raw_lots, raw_targets)
            
            for asset in agg_assets:
                m_data = fetch_market_data(asset["ticker"])
                if m_data and m_data["price"] > 0:
                    now_p = m_data["price"]
                    rate = 1.0 if is_tw else current_rate
                    
                    if asset["ticker"] == "CASH": 
                        now_val_ntd = asset.get("init_shares", 0) * rate
                        asset_cost_ntd = now_val_ntd
                        cash_total_ntd += now_val_ntd
                    else: 
                        now_val_ntd = now_p * rate * asset.get("init_shares", 0)
                        buy_p = asset.get("buy_price", now_p)
                        if buy_p == 0: buy_p = now_p
                        
                        # 💡 兵推：利用 Gross Aggregation 資料，呼叫精算引擎計算 YTD/1Y 所需的成本
                        net_cost, _, _, _, _, _ = calculate_net_pnl_stats({**asset, "now_p": now_p}, is_tw, rate)
                        asset_cost_ntd = net_cost
                        
                        hist_series = m_data.get("history_close")
                        if not hist_series.empty and not asset["ticker"].startswith("^"):
                            val_series = hist_series * asset.get("init_shares", 0) * rate
                            if combined_hist_df.empty: combined_hist_df = val_series.to_frame(name=asset["ticker"])
                            else:
                                if asset["ticker"] in combined_hist_df.columns: combined_hist_df[asset["ticker"]] = combined_hist_df[asset["ticker"]].add(val_series, fill_value=0)
                                else: combined_hist_df = combined_hist_df.join(val_series.rename(asset["ticker"]), how='outer')

                    # 💡 這裡統一使用「淨市值」來做 AUM。雖然 calculate_net_pnl_stats 有淨市值，但 CASH 需要獨立處理，所以這裡直接加。
                    # AUM 此處簡化為 Gross，因為淨獲利%主要是看成本 vs 淨市值
                    total_aum_ntd += now_val_ntd
                    if is_tw: tw_aum_ntd += now_val_ntd
                    else: us_aum_ntd += now_val_ntd
                    total_cost_ntd += asset_cost_ntd

    if not combined_hist_df.empty:
        combined_hist_df = combined_hist_df.ffill()
        combined_hist_df['Total'] = combined_hist_df.sum(axis=1) + cash_total_ntd
        
        ytd_date = str(datetime.datetime.now().year) + "-01-01"
        try: val_ytd = combined_hist_df['Total'].loc[ytd_date:].iloc[0]
        except: val_ytd = combined_hist_df['Total'].iloc[0]
        val_now = combined_hist_df['Total'].iloc[-1]
        
        return_ytd = ((val_now / val_ytd) - 1) * 100 if val_ytd > 0 else 0
    else: return_ytd = 0.0

    target_amount = db_data["global_goals"]["target_amt"]
    target_years = db_data["global_goals"]["target_years"]
    shortfall = max(0, target_amount - total_aum_ntd)
    req_cagr = ((target_amount / total_aum_ntd) ** (1 / max(1, target_years)) - 1) * 100 if total_aum_ntd > 0 and target_amount > total_aum_ntd else 0.0
    
    # 💡 真實累積報酬：使用淨成本
    cumulative_ret = ((total_aum_ntd / total_cost_ntd) - 1) * 100 if total_cost_ntd > 0 else 0.0

    st.markdown("### 🎯 全球財務自由與淨獲利績效")
    g1, g2, g3, g4 = st.columns(4)
    g1.markdown(f"<div class='kpi-card' style='border-left: 5px solid #8b5cf6;'><div class='data-label'>目標金額 ({target_years}年)</div><div style='font-size:1.8rem; font-weight:900;'>NTD {fmt_money(target_amount)}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='kpi-card' style='border-left: 5px solid #ef4444;'><div class='data-label'>目前資金缺口</div><div style='font-size:1.8rem; font-weight:900;'>NTD {fmt_money(shortfall)}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='kpi-card' style='border-left: 5px solid #10b981;'><div class='data-label'>所需年化報酬 (CAGR)</div><div style='font-size:1.8rem; font-weight:900;'>{req_cagr:.2f}%</div></div>", unsafe_allow_html=True)
    
    # 💡 呈現真實累積報酬
    pnl_c = "#10b981" if cumulative_ret >= 0 else "#ef4444"
    g4.markdown(f"<div class='kpi-card' style='border-left: 5px solid {pnl_c};'><div class='data-label'>真實精算累積報酬</div><div style='font-size:1.8rem; font-weight:900; color:{pnl_c};'>{cumulative_ret:+.2f}%</div><div class='data-display' style='font-size:0.7rem; color:#94a3b8;'>總淨成本: NTD {fmt_money(total_cost_ntd)}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 全球資產板塊概況 (Global AUM)")
    
    kpi_html = f"""
    <div style='display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap;'>
        <div class='kpi-card' style='flex:1; min-width:200px; border-left: 5px solid #8b5cf6; background-color:#f8fafc;'>
            <div class='data-label' style='color:#475569;'>🌍 全球總投資市值 (Total)</div>
            <div style='font-size:2.2rem; font-weight:900; color:#0f172a;'>NTD {fmt_money(total_aum_ntd)}</div>
        </div>
        <div class='kpi-card' style='flex:1; min-width:200px; border-left: 5px solid #059669;'>
            <div class='data-label'>🇹🇼 台股總部位</div>
            <div style='font-size:1.8rem; font-weight:900;'>NTD {fmt_money(tw_aum_ntd)}</div>
        </div>
        <div class='kpi-card' style='flex:1; min-width:200px; border-left: 5px solid #2563eb;'>
            <div class='data-label'>🇺🇸 美股總部位</div>
            <div style='font-size:1.8rem; font-weight:900;'>NTD {fmt_money(us_aum_ntd)}</div>
        </div>
        <div class='kpi-card' style='flex:1; min-width:200px; border-left: 5px solid #10b981;'>
            <div class='data-label'>今年報酬 (YTD)</div>
            <div style='font-size:1.8rem; font-weight:900; color:{"#10b981" if return_ytd >=0 else "#ef4444"};'>{return_ytd:+.2f}%</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)
    st.markdown("ℹ️ *累積報酬率與總淨成本已包含預估的買賣手續費與證交稅，YTD與線圖為原始市值走勢。*")

# ==========================================
# 5. 主功能：個別量化部位管理 (TW / US) -> 💡 雙分頁架構
# ==========================================
elif app_mode in ["🇹🇼 台股量化部位管理", "🇺🇸 美股量化部位管理"]:
    is_tw_mode = (app_mode == "🇹🇼 台股量化部位管理")
    market_label = "台股" if is_tw_mode else "美股"
    current_scheme_name = "🎯 台股主力配置" if is_tw_mode else "🎯 美股主力配置"
    currency_symbol = "NTD" if is_tw_mode else "USD"
    
    st.markdown(f'<h1>💼 {market_label} 量化部位管理 (Portfolio)</h1>', unsafe_allow_html=True)
    
    tab_monitor, tab_edit = st.tabs(["📊 動態量化監控 (Live Dashboard)", "📓 歷史建倉明細與配置 (Trade Lots)"])
    
    with tab_edit:
        # 💡 閃電建倉區域 (日期預設今天)
        st.markdown("### ⚡ 快速新增當日建倉 (Quick Add Trade)")
        st.info("💡 **提示**：買進新標的？直接在此輸入代碼或股名，**不需打 .TW 後綴**，系統會預設為今日日期寫入下方的完整日誌中。")
        with st.form(key=f"quick_add_form_{market_label}"):
            qa_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5])
            qa_tk = qa_cols[0].text_input("標的代碼或名稱 (如: 0050)", placeholder="請輸入標的")
            qa_shares = qa_cols[1].number_input("股數 (現金填金額)", min_value=0, step=100, format="%d")
            qa_price = qa_cols[2].number_input("買進成交價", min_value=0.0, step=1.0)
            qa_date = qa_cols[3].date_input("買進日期", value=datetime.date.today())
            submit_quick_add = qa_cols[4].form_submit_button("➕ 寫入建倉日誌", use_container_width=True)
            
            if submit_quick_add:
                if qa_tk and qa_shares > 0:
                    real_tk, resolved_name = smart_resolve_ticker(qa_tk, api_key)
                    if real_tk:
                        db_data["schemes"][current_scheme_name]["lots"].append({
                            "ticker": real_tk,
                            "shares": float(qa_shares),
                            "buy_price": float(qa_price),
                            "buy_date": qa_date.strftime("%Y-%m-%d")
                        })
                        save_portfolio(db_data)
                        st.success(f"✅ 成功寫入：{resolved_name} ({real_tk}) {qa_shares}股！")
                        st.rerun()
                    else:
                        st.error("⚠️ 無法識別該標的，請重新輸入。")
                else:
                    st.warning("⚠️ 請輸入標的名稱與股數。")
                    
        st.markdown("<hr style='margin: 1rem 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)
        
        # 📜 完整建倉日誌 (💡 自動隱藏 .TW 後綴)
        st.markdown("### 📜 完整建倉日誌與修改 (Trade Lots)")
        st.info("💡 **提示**：可在此處一次性修改多筆歷史紀錄，標的代碼會智慧隱藏 `.TW` 後綴，空白列將自動被系統忽略。")
        
        lots_df = pd.DataFrame(db_data["schemes"][current_scheme_name].get("lots", []))
        if lots_df.empty: 
            lots_df = pd.DataFrame(columns=["ticker", "shares", "buy_price", "buy_date"])
        else: 
            lots_df = lots_df[["ticker", "shares", "buy_price", "buy_date"]]
            # 💡 智慧無痕顯示：去除 .TW
            lots_df["ticker"] = lots_df["ticker"].apply(lambda x: str(x).split('.')[0] if pd.notna(x) else "")
            
        lots_df.columns = ["標的(Ticker)", "股數(Shares)", "買進均價(Price)", "日期(YYYY-MM-DD)"]
        
        edited_lots = st.data_editor(lots_df, num_rows="dynamic", use_container_width=True, key=f"editor_{market_label}")
        
        st.markdown("### 🎯 戰略目標權重設定 (Target Weight %)")
        
        # 盾牌防呆過濾
        unique_tickers = []
        for tk in edited_lots["標的(Ticker)"].dropna():
            tk_str = str(tk).strip().upper()
            if tk_str and tk_str not in ["NAN", "NONE"]:
                unique_tickers.append(tk_str)
        unique_tickers = list(dict.fromkeys(unique_tickers)) 
        
        old_targets = db_data["schemes"][current_scheme_name].get("targets", {})
        target_data = []
        for tk in unique_tickers:
            clean_tk = tk.split('.')[0]
            target_data.append({"標的": clean_tk, "目標權重(%)": old_targets.get(clean_tk, 0.0)})
            
        targets_df = pd.DataFrame(target_data)
        edited_targets = pd.DataFrame()
        if not targets_df.empty:
            edited_targets = st.data_editor(targets_df, disabled=["標的"], use_container_width=True, key=f"target_{market_label}")
        
        if st.button(f"📌 儲存 {market_label} 庫存與權重配置", type="primary"):
            with st.spinner('儲存並同步雲端數據中...'):
                new_lots = []
                for _, row in edited_lots.iterrows():
                    tk_raw = row["標的(Ticker)"]
                    if pd.isna(tk_raw): continue
                    tk = str(tk_raw).strip().upper()
                    if not tk or tk in ["NAN", "NONE"]: continue
                    
                    real_ticker, _ = smart_resolve_ticker(tk, api_key)
                    if real_ticker:
                        new_lots.append({
                            "ticker": real_ticker,
                            "shares": float(row["股數(Shares)"] if not pd.isna(row["股數(Shares)"]) else 0),
                            "buy_price": float(row["買進均價(Price)"] if not pd.isna(row["買進均價(Price)"]) else 0),
                            "buy_date": str(row["日期(YYYY-MM-DD)"]) if not pd.isna(row["日期(YYYY-MM-DD)"]) else ""
                        })
                
                new_targets = {}
                if not edited_targets.empty:
                    for _, row in edited_targets.iterrows():
                        new_targets[str(row["標的"]).strip()] = float(row["目標權重(%)"])
                
                db_data["schemes"][current_scheme_name]["lots"] = new_lots
                db_data["schemes"][current_scheme_name]["targets"] = new_targets
                save_portfolio(db_data)
                st.success("🔒 儲存成功！請切換至左方【📊 動態量化監控】分頁查看精算數據。")

    with tab_monitor:
        current_view_data = []
        local_total_val, local_total_net_cost = 0, 0
        
        target_portfolio = aggregate_lots(db_data["schemes"][current_scheme_name]["lots"], db_data["schemes"][current_scheme_name]["targets"])
        
        if target_portfolio:
            with st.spinner(f"🔄 正在同步雲端報價並精算淨損益..."):
                for asset in target_portfolio:
                    m_data = fetch_market_data(asset["ticker"])
                    if m_data and m_data["price"] > 0:
                        now_p = m_data["price"]
                        fx = 1.0 if is_tw_mode else current_rate
                        
                        # 💡 兵推：呼叫費率精算引擎，計算此標的的「真實淨獲利狀態」
                        net_cost, net_val, total_fees, total_tax, net_pnl, net_pnl_pct = calculate_net_pnl_stats(
                            {**asset, "now_p": now_p}, is_tw_mode, current_rate
                        )
                        
                        local_total_val += (now_p * fx * asset['init_shares'])
                        local_total_net_cost += net_cost
                        
                        current_view_data.append({
                            **asset, "now_p": now_p, "date": m_data["date"], 
                            "net_buy_cost": net_cost, "net_real_val": net_val,
                            "total_fees": total_fees, "total_tax": total_tax,
                            "net_pnl": net_pnl, "net_pnl_pct": net_pnl_pct,
                            "drawdown": m_data["drawdown"], "ma200": m_data["ma200"], "bias": m_data["bias"],
                            "rsi": m_data["rsi"], "kd_k": m_data["kd_k"]
                        })

            if current_view_data:
                # 計算組合整理累積報酬
                local_cumulative_ret = ((local_total_val / local_total_net_cost) - 1) * 100 if local_total_net_cost > 0 else 0.0
                
                # 呈現組合整理 KPI
                st.markdown("### 組合淨獲利與再平衡指標 (Net P&L)")
                kpi_cols = st.columns(3)
                
                pnl_c = "#10b981" if local_cumulative_ret >= 0 else "#ef4444"
                kpi_cols[0].markdown(f"<div class='kpi-card' style='border-left: 5px solid {pnl_c};'><div class='data-label'>真實精算累積報酬</div><div style='font-size:2rem; font-weight:900; color:{pnl_c};'>{local_cumulative_ret:+.2f}%</div><div class='data-display' style='font-size:0.75rem; color:#94a3b8;'>總淨成本: NTD {fmt_money(local_total_net_cost)}</div></div>", unsafe_allow_html=True)
                
                threshold = st.slider("⚖️ 再平衡觸發門檻 (Threshold %)", 0.0, 10.0, 2.0, 0.5, help="當偏離目標權重超過此百分比時，標記為⚠️偏離。")
                
                kpi_cols[2].markdown(f"""
                <div class='kpi-card' style='border-left: 5px solid #64748b; background-color:#f8fafc; color:#64748b;'>
                    <div class='data-label' style='color:#64748b;'>費率設置狀態</div>
                    <div style='font-size:0.85rem; font-weight:700;'>
                        台股折扣: {tw_fee_discount:.1f}折<br>
                        美股費率: {us_fee_type}
                    </div>
                    <div class='data-display' style='font-size:0.75rem; color:#94a3b8;'>於側邊欄修改。損益已預扣費用。</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">動態量化監控盤 ( Live Dashboard)</div>', unsafe_allow_html=True)

                for item in current_view_data:
                    c = st.columns([1.6, 1.4, 1.4, 1.4, 1.4, 2.8])
                    
                    # 💡 這裡市值採用原始Gross市值來算權重，與財務總覽一致
                    mult = 1.0 if is_tw_mode else current_rate
                    gross_now_val = item['now_p'] * mult * item['init_shares']
                    
                    real_pct = (gross_now_val / local_total_val * 100) if local_total_val > 0 else 0
                    diff = real_pct - item["target_pct"]
                    diff_val = (local_total_val * item["target_pct"]/100.0) - gross_now_val # Gross 的偏離金額
                    
                    _, zh_name = smart_resolve_ticker(item["ticker"], api_key)
                    if not zh_name or zh_name == item["ticker"]: zh_name = STOCK_NAME_DICT.get(item["ticker"].split('.')[0], item["ticker"])
                    
                    box_bg = "#f8fafc" if abs(diff) <= threshold else "#fffbeb"
                    box_border = "#e2e8f0" if abs(diff) <= threshold else "#fde68a"
                    title_color = "#0f172a" if abs(diff) <= threshold else "#92400e"
                    title_text = "✅ 權重符合標準" if abs(diff) <= threshold else f"⚠️ 權重偏離 {diff:+.1f}%"
                    
                    # 1. 標的資訊 (💡 智慧隱藏尾碼)
                    clean_name = item["ticker"].split('.')[0]
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='stock-name-display'>{zh_name}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {item['now_p']:.2f}</div><div class='date-display'>平均成本: {item.get('buy_price',0):.2f}</div>", unsafe_allow_html=True)
                    
                    # 2. 持有狀態與精算損益 (Req: 扣除費用)
                    pnl_ntd = item['net_pnl']
                    pnl_pct = item['net_pnl_pct']
                    pnl_c = "#10b981" if pnl_ntd >= 0 else "#ef4444"
                    pnl_bg = "pnl-pos" if pnl_ntd >= 0 else "pnl-neg"
                    
                    if item['ticker'] == "CASH":
                        c[1].markdown(f"<div class='data-label'>持有總額:</div><div class='data-value'>{fmt_money(item.get('init_shares', 0))}</div><div class='data-label' style='margin-top:10px;'>真實市值:</div><div class='data-value'>NTD {fmt_money(item['net_buy_cost'])}</div>", unsafe_allow_html=True)
                    else:
                        c[1].markdown(f"""
                        <div class='data-label'>總持有數量:</div><div class='data-value'>{fmt_money(item.get('init_shares', 0))} 股</div>
                        <div class='data-label' style='margin-top:10px;'>真實精算淨損益:</div>
                        <div class='badge-pnl {pnl_bg}'>{fmt_money(pnl_ntd)} <span style='font-size:0.75rem;'>({pnl_pct:+.1f}%)</span></div>
                        <div class='data-display' style='font-size:0.7rem; color:#94a3b8;'>總費用+稅: NTD {fmt_money(item['total_fees']+item['total_tax'])}</div>
                        """, unsafe_allow_html=True)
                    
                    # 3. 權重監控
                    progress_html = f"""
                    <div style='margin-top:4px; margin-bottom:4px; font-size:0.75rem; color:#64748b; font-weight:700;'>實際 {real_pct:.1f}% / 目標 {item['target_pct']}%</div>
                    <div style='width: 100%; background-color: #f1f5f9; border-radius: 4px; height: 6px; overflow:hidden;'>
                        <div style='width: {min(100, real_pct)}%; background-color: {"#10b981" if abs(diff) <= threshold else "#f59e0b"}; height: 100%;'></div>
                    </div>
                    """
                    c[2].markdown(f"<div class='data-label'>資產佔比監控:</div>{progress_html}", unsafe_allow_html=True)
                    
                    # 4. 長線趨勢
                    is_bear = item['now_p'] < item['ma200']
                    trend_tag = "<span style='color:#ef4444; font-weight:800;'>🔴 破線空頭</span>" if is_bear else "<span style='color:#10b981; font-weight:800;'>🟢 多頭格局</span>"
                    dd_color = "#ef4444" if item['drawdown'] < -20 else ("#f59e0b" if item['drawdown'] < -10 else "#64748b")
                    c[3].markdown(f"<div class='data-label'>年線 (MA200):</div><div>{trend_tag}</div><div class='data-label' style='margin-top:10px;'>距高點回撤:</div><div class='data-value' style='color:{dd_color};'>{item['drawdown']:.1f}%</div>", unsafe_allow_html=True)
                    
                    # 5. 短線乖離與戰術
                    bias_color = "#ef4444" if item['bias'] >= 25 else ("#f59e0b" if item['bias'] >= 15 else ("#10b981" if item['bias'] <= -15 else "#64748b"))
                    tactical_action = "<span style='color:#64748b;'>⚖️ 持有</span>"
                    if not item['ticker'] == "CASH":
                        if is_bear and item.get("leverage", 1.0) >= 2.0: tactical_action = "<span style='color:#ef4444; font-weight:800;'>🛑 破線 (減碼防內耗)</span>"
                        elif item.get("kd_k", 50) < 20: tactical_action = "<span style='color:#10b981; font-weight:800;'>🟢 恐慌 (分批買)</span>"
                    c[4].markdown(f"<div class='data-label'>乖離率 (BIAS):</div><div class='data-value' style='color:{bias_color};'>{item['bias']:+.1f}%</div><div class='data-label' style='margin-top:10px;'>🧠 戰術建議:</div><div style='font-size:0.95rem;'>{tactical_action}</div>", unsafe_allow_html=True)

                    # 6. 再平衡動作
                    if item['ticker'] == "CASH":
                        unit = "元" if is_tw_mode else "美元"
                        diff_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                        if diff_amt > 0: action_msg = f"<div class='badge-buy'>ADD 存入</div> <span style='font-weight:800; font-size:1.2rem;'>{fmt_money(diff_amt)} {unit}</span>"
                        elif diff_amt < 0: action_msg = f"<div class='badge-sell'>SUB 提領</div> <span style='font-weight:800; font-size:1.2rem;'>{fmt_money(abs(diff_amt))} {unit}</span>"
                        else: action_msg = f"<div class='badge-hold'>無需調整</div>"
                    else:
                        price_ntd = item["now_p"] * mult
                        shares_diff = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        if shares_diff > 0: action_msg = f"<div class='badge-buy'>BUY 買進</div> <span style='font-weight:900; font-size:1.2rem;'>{fmt_money(shares_diff)} 股</span>"
                        elif shares_diff < 0: action_msg = f"<div class='badge-sell'>SELL 賣出</div> <span style='font-weight:900; font-size:1.2rem;'>{fmt_money(abs(shares_diff))} 股</span>"
                        else: action_msg = f"<div class='badge-hold'>無需動作</div>"

                    action_html = f"""
                    <div class='pro-card' style='background-color:{box_bg}; border-color:{box_border}; display:flex; flex-direction:column; justify-content:center;'>
                        <div style='color:{title_color}; font-weight:800; font-size:0.9rem; margin-bottom: 12px; text-transform:uppercase; letter-spacing:0.5px;'>{title_text}</div>
                        <div>{action_msg}</div>
                    </div>
                    """
                    c[5].markdown(action_html, unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 1rem 0; border-color: #f1f5f9;'>", unsafe_allow_html=True)

# ==========================================
# 6. 分頁：全球 K 線分析
# ==========================================
elif app_mode == "🔍 全球市場量化終端":
    st.sidebar.header("🌍 大盤快搜 (Indices)")
    market_choice = st.sidebar.radio("快速切換分析標的：", ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"])

    st.title("📊 全球市場量化終端 (Market Terminal)")
    k_period = st.radio("選擇 K 線週期 (Timeframe)：", ["日K", "週K", "月K", "年K"], horizontal=True)
    st.markdown("---")

    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = ""
    
    if market_choice == "自訂輸入個股": 
        target_to_parse = st.text_input("輸入欲分析的代碼或股名 (輸入完畢按 Enter)：", value="", placeholder="例如：2330 或 台積電")
    else: 
        target_to_parse = default_ticker
    
    if target_to_parse:
        ticker_input, zh_name = smart_resolve_ticker(target_to_parse, api_key)
        
        if ticker_input:
            try:
                with st.spinner("載入量化數據與繪製圖表中..."):
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
                        
                        if k_period == "日K": ma3, n3 = 200, "MA200"
                        else: ma3, n3 = 50, "MA50"
                        df['MA3'] = df['Close'].rolling(ma3).mean()
                        
                        rsi_val = float(df['RSI'].dropna().iloc[-1]) if not df['RSI'].dropna().empty else 50.0
                        rsi_status = "🔴 超買過熱" if rsi_val > 70 else ("🟢 超賣低估" if rsi_val < 30 else "🟡 中性盤整")
                        last_close = float(df['Close'].dropna().iloc[-1])
                        ma200_val = float(df['MA3'].dropna().iloc[-1]) if not df['MA3'].dropna().empty else last_close
                        high_52w = float(df['High'].max())
                        dd_pct = ((last_close - high_52w) / high_52w) * 100 if high_52w > 0 else 0.0

                        st.markdown("### 📊 量化戰情儀表板")
                        cc1, cc2, cc3 = st.columns(3)
                        
                        # 處理大盤單位
                        fmt_unit = "點" if ticker_input.startswith("^") else "元"
                        
                        cc1.markdown(f"<div class='pro-card'><div class='data-label'>📉 最新價格 / 長線({n3})</div><div class='data-value'>{fmt_money(last_close)} {fmt_unit}</div><div style='color:#64748b; font-size:0.8rem; margin-top:8px;'>均線價: {fmt_money(ma200_val)}</div></div>", unsafe_allow_html=True)
                        cc2.markdown(f"<div class='pro-card'><div class='data-label'>波段高點回撤率</div><div class='data-value' style='color:#ef4444;'>{dd_pct:.2f}%</div><div style='color:#64748b; font-size:0.8rem; margin-top:8px;'>52周高: {fmt_money(high_52w)}</div></div>", unsafe_allow_html=True)
                        cc3.markdown(f"<div class='pro-card'><div class='data-label'>短線技術動能 (RSI)</div><div class='data-value'>{rsi_val:.1f}</div><div style='color:#0f172a; font-size:0.9rem; font-weight:700; margin-top:8px;'>狀態: {rsi_status}</div></div>", unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.subheader(f"📈 {ticker_input.split('.')[0]} {zh_name} 技術走勢")
                        
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA3'], mode='lines', name=n3, line=dict(color='#ef4444', width=2)), row=1, col=1)
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color="#cbd5e1"), row=2, col=1)
                        
                        fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_white", margin=dict(t=30, b=10, l=10, r=10))
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            except Exception as e:
                st.error(f"❌ 數據載入失敗: {str(e)}")
