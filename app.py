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
# 🔑 終極安全 API Key 讀取機制 (背景靜默載入)
# ==========================================
try:
    # 系統會自動去 Streamlit Cloud 後台的 Secrets 抓取密碼
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    MY_API_KEY = ""

# ==========================================
# 0. 核心抗封鎖引擎
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 1. 頁面配置與 CSS 視覺優化
# ==========================================
st.set_page_config(layout="wide", page_title="資產配置決策系統", page_icon="🏦")

st.markdown("""
    <style>
    .market-header { 
        padding: 16px 20px; border-radius: 10px; font-weight: 700; 
        margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        letter-spacing: 1px;
    }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #00ffcc; }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #f97316; }
    .ticker-display { font-size: 2.2rem; font-weight: 900; line-height: 1.1; letter-spacing: 0.5px; }
    .stock-name-display { font-size: 1.1rem; color: #94a3b8; font-weight: 800; margin-top: 4px; margin-bottom: 4px; }
    .price-display { font-size: 1.1rem; font-weight: 600; opacity: 0.8; margin-top: 4px; }
    .date-display { font-size: 0.85rem; color: #94a3b8; margin-top: 2px; font-weight: 600;}
    .data-label { font-size: 0.95rem; opacity: 0.7; margin-bottom: 2px;}
    .data-value { font-size: 1.1rem; font-weight: 700; }
    .action-box { background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 10px; border-radius: 5px; margin-top: 15px; }
    
    /* 強制拔除所有 Plotly 隱藏工具列 */
    .modebar { display: none !important; }
    
    .dashboard-card {
        background-color: #f1f5f9 !important; 
        border-radius: 8px;
        padding: 14px;
        border-left: 5px solid #10b981;
        color: #0f172a !important; 
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    .dashboard-card b, .dashboard-card span {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 🛡️ 史詩級三維度解析引擎 (字典 + AI 防幻覺 + Yahoo API)
# ==========================================
STOCK_NAME_DICT = {
    "6285": "啟碁", "2344": "華邦電", "2337": "旺宏", "2330": "台積電", "2454": "聯發科",
    "2317": "鴻海", "2603": "長榮", "0050": "元大台灣50", "00631L": "元大台灣50正2",
    "0056": "元大高股息", "00878": "國泰永續高股息", "6669": "緯穎", "2382": "廣達",
    "2303": "聯電", "2881": "富邦金", "2891": "中信金", "2412": "中華電", "2609": "陽明",
    "3231": "緯創", "2308": "台達電", "00919": "群益台灣精選高息", "00929": "復華台灣科技優息",
    "5498": "凱崴", "2356": "英業達", "2324": "仁寶", "3034": "聯詠", "2379": "瑞昱",
    "AAPL": "蘋果 (Apple)", "MSFT": "微軟 (Microsoft)", "NVDA": "輝達 (NVIDIA)", 
    "TSLA": "特斯拉 (Tesla)", "AMD": "超微 (AMD)", "QQQ": "納斯達克100 ETF", 
    "VTI": "全美股市 ETF", "SCHD": "美國紅利 ETF"
}

def resolve_suffix(base_tk):
    if base_tk.endswith('.TW') or base_tk.endswith('.TWO'):
        try:
            if yf.Ticker(base_tk, session=yf_session).fast_info.get('lastPrice'): return base_tk
        except: pass
        return base_tk
    
    if not base_tk[0].isdigit() and not base_tk.startswith('00'): 
        try:
            if yf.Ticker(base_tk, session=yf_session).fast_info.get('lastPrice'): return base_tk
        except: pass
        
    for ext in [".TW", ".TWO"]:
        tk = f"{base_tk}{ext}"
        try:
            if yf.Ticker(tk, session=yf_session).fast_info.get('lastPrice'): return tk
        except: pass
        
    return f"{base_tk}.TW" if base_tk[0].isdigit() else base_tk

def get_yf_chinese_name(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(query)}&lang=zh-Hant-TW&region=TW"
        r = requests.get(url, headers=yf_session.headers, timeout=2)
        if r.status_code == 200:
            quotes = r.json().get('quotes', [])
            if quotes:
                for q in quotes:
                    if query in q.get('symbol', ''):
                        return q.get('shortname', '')
                return quotes[0].get('shortname', '')
    except: pass
    return ""

@st.cache_data(show_spinner=False, ttl=3600)
def smart_resolve_ticker(user_input, api_key=""):
    t = user_input.strip().upper()
    if not t: return "", ""
    if t in ["現金", "CASH"]: return "CASH", "台/外幣保留款"
    if t.startswith("^"): 
        idx_map = {"^TWII": "台灣加權指數", "^IXIC": "那斯達克", "^GSPC": "標普500", "^SOX": "費城半導體", "^VIX": "恐慌指數"}
        return t, idx_map.get(t, "大盤指數")

    clean_t = t.replace('.TW', '').replace('.TWO', '')
    
    if clean_t in STOCK_NAME_DICT:
        return resolve_suffix(clean_t), STOCK_NAME_DICT[clean_t]

    for tk, name in STOCK_NAME_DICT.items():
        if t == name.upper() or t in name.upper():
            return resolve_suffix(tk), name

    if re.match(r'^[A-Z0-9]+$', clean_t):
        valid_tk = resolve_suffix(clean_t)
        if valid_tk:
            zh_name = get_yf_chinese_name(clean_t)
            return valid_tk, zh_name if zh_name else clean_t

    ticker_result = ""
    name_result = t
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"你是一個專業的台灣股市系統。使用者輸入了股票名稱：「{t}」。請直接輸出對應的「股票代碼(純數字)」。如果不知道，請輸出「無」。注意：絕對不允許輸出其他文字、標點符號或思考過程。"
            res = model.generate_content(prompt).text.strip().upper()
            
            if re.match(r'^[A-Z0-9]+$', res) and res != "無":
                ticker_result = res
        except:
            pass
            
    if ticker_result:
        valid_tk = resolve_suffix(ticker_result)
        if valid_tk:
            return valid_tk, name_result

    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(t)}&lang=zh-Hant-TW&region=TW"
        r = requests.get(url, headers=yf_session.headers, timeout=3)
        if r.status_code == 200:
            quotes = r.json().get('quotes', [])
            if quotes:
                sym = quotes[0].get('symbol', '').upper()
                shortname = quotes[0].get('shortname', t)
                return sym, shortname
    except: pass

    return "", ""

def get_leverage(ticker):
    if ticker == "CASH": return 1.0
    t = ticker.upper()
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if t.endswith("R.TW") or t.endswith("R.TWO"): return -1.0
    us_3x = ["TQQQ", "SOXL", "UPRO", "UDOW", "TMF", "FAS", "TECL", "CURE", "NAIL", "YINN", "WEBL", "DPST", "FNGU"]
    us_2x = ["QLD", "SSO", "USD", "UWM", "MVV", "NVDL", "TSLL"]
    us_n3x = ["SQQQ", "SOXS", "SPXU", "SDOW", "TMV", "FAZ", "TECS", "WEBS", "FNGD"]
    base = t.split('.')[0]
    if base in us_3x: return 3.0
    if base in us_2x: return 2.0
    if base in us_n3x: return -3.0
    return 1.0

# ==========================================
# 3. 即時數據抓取
# ==========================================
def fetch_market_data(ticker):
    if not ticker or ticker == "CASH": 
        return {"price": 1.0, "date": "最新即時匯率", "ma200": 1.0, "high52w": 1.0, "drawdown": 0.0, "bias": 0.0}
    try:
        t_obj = yf.Ticker(ticker, session=yf_session)
        try: realtime_price = float(t_obj.fast_info['lastPrice'])
        except: realtime_price = None

        df = yf.download(ticker, period="2y", progress=False, session=yf_session)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            closes = df['Close'].dropna()
            highs = df['High'].dropna()
            if not closes.empty: 
                hist_last_price = float(closes.iloc[-1])
                date_str = closes.index[-1].strftime("%Y-%m-%d")
                
                price = realtime_price if realtime_price is not None else hist_last_price
                if realtime_price is not None: date_str = "最新即時收盤"

                high52w = float(highs.max())
                if price > high52w: high52w = price 
                
                ma200 = float(closes.rolling(window=200).mean().iloc[-1]) if len(closes) >= 200 else price
                drawdown = ((price - high52w) / high52w) * 100 if high52w > 0 else 0.0
                bias = ((price - ma200) / ma200) * 100 if ma200 > 0 else 0.0
                
                return {"price": price, "date": date_str, "ma200": ma200, "high52w": high52w, "drawdown": drawdown, "bias": bias}
    except: return None
    return None

def load_portfolio():
    default_data = {"tw_portfolio": [], "us_portfolio": []}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return default_data

def save_portfolio(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

twd_data = fetch_market_data("TWD=X")
current_rate = twd_data["price"] if twd_data else 32.5
vix_data = fetch_market_data("^VIX")
current_vix = vix_data["price"] if vix_data else 15.0

db_data = load_portfolio()

# --- 側邊欄 ---
st.sidebar.title("🏦 資產配置決策系統")
st.sidebar.markdown(f"📈 **即時匯率 USD/TWD：** `{current_rate:.2f}`")

vix_color = "#ef4444" if current_vix >= 25 else ("#f59e0b" if current_vix >= 20 else "#10b981")
vix_status = "⚠️ 極度恐慌" if current_vix >= 25 else ("⚡ 波動加劇" if current_vix >= 20 else "✅ 市場穩定")
st.sidebar.markdown(f"📉 **VIX 恐慌指數：** <span style='color:{vix_color}; font-weight:bold;'>{current_vix:.2f} ({vix_status})</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")

# 💡 隱藏了輸入框，系統在背景默默為您掛載 API Key
api_key = MY_API_KEY
if api_key:
    genai.configure(api_key=api_key)

app_mode = st.sidebar.radio("功能分頁導覽：", ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控", "🔍 全球 K 線分析"])
st.sidebar.markdown("---")

if app_mode == "🔍 全球 K 線分析":
    st.sidebar.header("🌍 大盤速查")
    market_choice = st.sidebar.radio("快速切換 K 線圖：", ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"])

if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    threshold = st.sidebar.slider("⚖️ 再平衡觸發門檻 (%)", 0.0, 10.0, 2.0, 0.5)
    num_assets = st.sidebar.number_input("🔢 展開標的輸入欄位數", value=max(3, len(db_data.get("tw_portfolio" if app_mode == "🇹🇼 台股持股監控" else "us_portfolio", []))), min_value=1)

# ==========================================
# 5. 主功能：資產動態監控盤
# ==========================================
if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    is_tw_mode = (app_mode == "🇹🇼 台股持股監控")
    market_label = "台股" if is_tw_mode else "美股"
    current_list_key = "tw_portfolio" if is_tw_mode else "us_portfolio"
    
    st.markdown(f'<h1>🏦 {app_mode.split(" ")[1]} 專業配置面板</h1>', unsafe_allow_html=True)
    
    with st.expander(f"⚙️ 點此調整：持有股數與目標權重 ({market_label})", expanded=(not db_data[current_list_key])):
        st.info(f"💡 提示：AI 引擎已啟動，支援輸入任何中文股名！修改完畢請點擊下方鎖定按鈕。")
        cols = st.columns([2, 2, 2])
        cols[0].markdown("**代碼 或 名稱**"); cols[1].markdown("**持有股數**"); cols[2].markdown("**目標權重%**")
        
        new_setup = []
        for i in range(int(num_assets)):
            r_cols = st.columns([2, 2, 2])
            hist = db_data[current_list_key][i] if i < len(db_data[current_list_key]) else {"ticker": "", "target_pct": 0, "init_shares": 0}
            display_tk = hist["ticker"].replace(".TWO", "").replace(".TW", "") if (".TW" in hist.get("ticker", "") or ".TWO" in hist.get("ticker", "")) else hist.get("ticker", "")
            safe_pct = min(100.0, max(0.0, float(hist.get("target_pct", 0.0))))
            safe_shares = max(0.0, float(hist.get("init_shares", 0.0)))
            
            raw_tk = r_cols[0].text_input(f"tk_{i}", display_tk, label_visibility="collapsed").strip()
            shares_input = r_cols[1].number_input(f"shares_{i}", min_value=0.0, value=safe_shares, step=100.0, label_visibility="collapsed")
            pct = r_cols[2].number_input(f"pct_{i}", min_value=0.0, max_value=100.0, value=safe_pct, step=5.0, label_visibility="collapsed")
            if raw_tk: new_setup.append({"raw_ticker": raw_tk, "target_pct": pct, "shares_input": shares_input})
        
        if st.button(f"📌 鎖定 {market_label} 庫存並更新系統", type="primary"):
            locked_assets = []
            error_tickers = []
            with st.spinner('AI 正在智慧解析股名與同步數據...'):
                for item in new_setup:
                    real_ticker, _ = smart_resolve_ticker(item["raw_ticker"], api_key)
                    m_data = fetch_market_data(real_ticker) if real_ticker else None
                    lev = get_leverage(real_ticker) if real_ticker else 1.0
                    if m_data and m_data["price"] > 0: 
                        locked_assets.append({"ticker": real_ticker, "target_pct": item["target_pct"], "leverage": lev, "init_shares": item["shares_input"], "init_price": m_data["price"], "is_tw": is_tw_mode})
                    else: error_tickers.append(item["raw_ticker"])
            
            if error_tickers: st.error(f"⚠️ 無法識別標的：{', '.join(error_tickers)}。若輸入中文失敗，請確認 API Key 是否已於後台綁定。")
            else:
                db_data[current_list_key] = locked_assets
                save_portfolio(db_data)
                st.success(f"🔒 {market_label} 組合分析模型建立成功！")
                st.rerun()

    current_view_data = []
    local_total_val, local_total_exp = 0, 0
    target_portfolio = db_data[current_list_key]
    
    if target_portfolio:
        with st.spinner(f"🔄 正在運算動態數據..."):
            for asset in target_portfolio:
                m_data = fetch_market_data(asset["ticker"])
                if m_data and m_data["price"] > 0:
                    now_p = m_data["price"]
                    date_str = m_data["date"]
                    lev = asset.get("leverage", 1.0)
                    if asset["ticker"].startswith("^"): now_val_ntd = asset.get("init_shares", 0) * (now_p / asset.get("init_price", now_p))
                    elif asset["ticker"] == "CASH": now_val_ntd = asset.get("init_shares", 0) * (1.0 if is_tw_mode else current_rate)
                    else: now_val_ntd = (now_p if is_tw_mode else (now_p * current_rate)) * asset.get("init_shares", 0)
                    
                    exposure_ntd = now_val_ntd * lev
                    local_total_val += now_val_ntd
                    local_total_exp += exposure_ntd
                    current_view_data.append({**asset, "now_p": now_p, "date": date_str, "now_val_ntd": now_val_ntd, "exposure_ntd": exposure_ntd, "drawdown": m_data["drawdown"], "ma200": m_data["ma200"], "bias": m_data["bias"]})

        if current_view_data:
            st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">{"🇹🇼 台灣市場" if is_tw_mode else "🇺🇸 美國市場"} 動態監控盤</div>', unsafe_allow_html=True)
            for item in current_view_data:
                c = st.columns([1.5, 1.3, 1.2, 1.5, 1.7, 2.8])
                real_pct = (item["now_val_ntd"] / local_total_val * 100) if local_total_val > 0 else 0
                diff = real_pct - item["target_pct"]
                target_val = local_total_val * (item["target_pct"] / 100.0)
                diff_val = target_val - item["now_val_ntd"]
                action_text = ""
                
                _, zh_name = smart_resolve_ticker(item["ticker"], api_key)
                
                if item["ticker"] == "CASH":
                    unit_str = "元" if is_tw_mode else "美元"
                    adjust_amt = int(diff_val / (1.0 if is_tw_mode else current_rate))
                    if adjust_amt > 0: action_text = f"需增加: {adjust_amt:,} {unit_str}"
                    elif adjust_amt < 0: action_text = f"需減少: {abs(adjust_amt):,} {unit_str}"
                    else: action_text = "無需調整"
                    c[0].markdown(f"<div class='ticker-display'>💵 現金</div><div class='stock-name-display'>台/外幣保留款</div><div class='price-display'>TWD/USD</div><div class='date-display'>{item['date']}</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>持有數量:</div><div class='data-value'>{int(item.get('init_shares', 0)):,}</div><div class='data-label' style='margin-top:4px;'>真實市值:</div><div class='data-value'>NTD {int(item['now_val_ntd']):,}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>目標設定:</div><div class='data-value'>{item['target_pct']}%</div><div class='data-label' style='margin-top:4px;'>槓桿:</div><div class='data-value'>1.0x</div>", unsafe_allow_html=True)
                    c[3].markdown(f"<div class='data-label'>長線趨勢:</div><div class='data-value' style='color:#10b981;'>穩定無風險</div><div class='data-label' style='margin-top:4px;'>回撤率:</div><div class='data-value'>0.0%</div>", unsafe_allow_html=True)
                    c[4].markdown(f"<div class='data-label'>乖離率 (BIAS):</div><div class='data-value'>---</div><div class='data-label' style='margin-top:4px;'>🧠 戰術建議:</div><div class='data-value' style='color:#94a3b8;'>資金水庫</div>", unsafe_allow_html=True)
                else:
                    clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                    if item["ticker"].startswith("^"):
                        adjust_amt = int(diff_val)
                        if adjust_amt > 0: action_text = f"需加碼: NTD {adjust_amt:,}"
                        elif adjust_amt < 0: action_text = f"需減碼: NTD {abs(adjust_amt):,}"
                        else: action_text = "無需調整"
                    else:
                        price_ntd = item["now_p"] if is_tw_mode else (item["now_p"] * current_rate)
                        adjust_shares = int(diff_val / price_ntd) if price_ntd > 0 else 0
                        if adjust_shares > 0: action_text = f"需買進: {adjust_shares:,} 股"
                        elif adjust_shares < 0: action_text = f"需賣出: {abs(adjust_shares):,} 股"
                        else: action_text = "無需調整"
                        
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='stock-name-display'>{zh_name}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {item['now_p']:.2f}</div><div class='date-display'>{item['date']}</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>{'📊 投入金額:' if item['ticker'].startswith('^') else '持有股數:'}</div><div class='data-value'>{int(item.get('init_shares', 0)):,} {'元' if item['ticker'].startswith('^') else '股'}</div><div class='data-label' style='margin-top:4px;'>真實市值:</div><div class='data-value'>NTD {int(item['now_val_ntd']):,}</div>", unsafe_allow_html=True)
                    c[2].markdown(f"<div class='data-label'>目標設定:</div><div class='data-value'>{item['target_pct']}%</div><div class='data-label' style='margin-top:4px;'>槓桿屬性:</div><div class='data-value'>{item.get('leverage', 1.0)}x</div>", unsafe_allow_html=True)
                    
                    is_bear = item['now_p'] < item['ma200']
                    trend_tag = "<span style='color:#ef4444; font-weight:700;'>🔴 破線空頭</span>" if is_bear else "<span style='color:#10b981; font-weight:700;'>🟢 多頭格局</span>"
                    dd_color = "#ef4444" if item['drawdown'] < -20 else ("#f59e0b" if item['drawdown'] < -10 else "#f8fafc")
                    c[3].markdown(f"<div class='data-label'>年線 (MA200):</div><div>{trend_tag}</div><div class='data-label' style='margin-top:4px;'>距高點回撤:</div><div class='data-value' style='color:{dd_color};'>{item['drawdown']:.1f}%</div>", unsafe_allow_html=True)
                    
                    bias_color = "#ef4444" if item['bias'] >= 25 else ("#f59e0b" if item['bias'] >= 15 else ("#10b981" if item['bias'] <= -15 else "#f8fafc"))
                    tactical_action = "<span style='color:#94a3b8;'>⚖️ 依原定比例持有</span>"
                    if item["bias"] >= 25: tactical_action = "<span style='color:#ef4444; font-weight:700;'>🚨 極度過熱 (考慮止盈)</span>"
                    elif is_bear and item.get("leverage", 1.0) >= 2.0: tactical_action = "<span style='color:#ef4444; font-weight:700;'>🔴 破線 (強烈建議降槓桿)</span>"
                    elif item["drawdown"] <= -50: tactical_action = "<span style='color:#10b981; font-weight:700;'>🟢 終極打擊區 (強力加碼)</span>"
                    elif item["drawdown"] <= -30: tactical_action = "<span style='color:#10b981; font-weight:700;'>🟡 階梯打擊區 (分批加碼)</span>"
                    elif item["drawdown"] <= -15 and item.get("leverage", 1.0) >= 2.0 and not is_bear: tactical_action = "<span style='color:#f97316; font-weight:700;'>🛡️ 動態防守 (移動停損警示)</span>"
                    c[4].markdown(f"<div class='data-label'>乖離率 (BIAS):</div><div class='data-value' style='color:{bias_color};'>{item['bias']:+.1f}%</div><div class='data-label' style='margin-top:4px;'>🧠 戰術建議:</div><div style='font-size:1.05rem;'>{tactical_action}</div>", unsafe_allow_html=True)

                if abs(diff) > threshold: c[5].warning(f"⚠️ 偏離 {diff:+.1f}% (佔比: {real_pct:.1f}%)\n\n👉 **{action_text}**")
                else: c[5].success(f"✅ 平衡區間 (佔比: {real_pct:.1f}%)\n\n👉 **{action_text}**")

        st.markdown("---")
        st.markdown("### 💰 動態資金加碼分配器")
        add_cash = st.number_input("打算加碼的總資金 (NTD)", min_value=0, value=0, step=10000)
        if add_cash > 0:
            st.markdown("<div class='action-box'>", unsafe_allow_html=True)
            st.markdown("#### 🎯 最佳注資建議清單：")
            ideal_total_val = local_total_val + add_cash
            buy_list = []
            for item in current_view_data:
                ideal_target_ntd = ideal_total_val * (item["target_pct"] / 100.0)
                shortfall_ntd = ideal_target_ntd - item["now_val_ntd"]
                if shortfall_ntd > 0:
                    if item["ticker"] == "CASH":
                        buy_units = shortfall_ntd / (1.0 if is_tw_mode else current_rate)
                        buy_list.append(f"💵 **現金**：建議增加 **{int(buy_units):,}** {'元' if is_tw_mode else '美元'} (投入約 NTD {int(shortfall_ntd):,})")
                    elif item["ticker"].startswith("^"): buy_list.append(f"📊 **{item['ticker']}**：建議加碼 **{int(shortfall_ntd):,}** 元")
                    else:
                        price_ntd = item["now_p"] if is_tw_mode else (item["now_p"] * current_rate)
                        shares_to_buy = int(shortfall_ntd / price_ntd) if price_ntd > 0 else 0
                        clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                        if shares_to_buy > 0: buy_list.append(f"🛒 **{clean_name}**：建議買進 **{shares_to_buy:,}** 股 (投入約 NTD {int(shares_to_buy * price_ntd):,})")
            if buy_list:
                for b in buy_list: st.markdown(f"- {b}")
            else: st.write("目前比例完美，可按目標比例投入。")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        footer_cols = st.columns([1, 1])
        with footer_cols[0]:
            st.subheader(f"💰 {market_label} 綜合指標總結")
            
            st.metric(f"總投資市值 (NTD)", f"{int(local_total_val):,}")
            
            if current_view_data:
                pie_df = pd.DataFrame([{"tk": "現金" if r["ticker"] == "CASH" else r["ticker"].replace('.TWO','').replace('.TW', ''), "val": r["now_val_ntd"]} for r in current_view_data])
                fig_pie = px.pie(pie_df, values='val', names='tk', hole=0.4, title=f"{market_label}資產 真實比重圖")
                fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0), template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                
        with footer_cols[1]:
            if current_view_data:
                st.subheader(f"📊 {market_label} 權重偏差分析")
                bar_df = pd.DataFrame([{"tk": "現金" if r["ticker"] == "CASH" else r["ticker"].replace('.TWO','').replace('.TW', ''), "Real": (r["now_val_ntd"]/local_total_val*100) if local_total_val > 0 else 0, "Target": r["target_pct"]} for r in current_view_data])
                fig_bar = go.Figure(data=[
                    go.Bar(name='真實權重 (%)', x=bar_df['tk'], y=bar_df['Real'], marker_color='#00ffcc'),
                    go.Bar(name='設定目標 (%)', x=bar_df['tk'], y=bar_df['Target'], marker_color='#475569')
                ])
                fig_bar.update_layout(barmode='group', height=400, margin=dict(t=40, b=0, l=0, r=0), template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

        # ==========================================
        # 🤖 AI 投資組合總體檢
        # ==========================================
        st.markdown("---")
        st.subheader("🤖 AI 投資組合總體檢")
        if st.button(f"✨ 讓 Gemini 診斷我的【{market_label}】持股配置", key="portfolio_ai_btn", type="secondary"):
            if not api_key:
                st.warning("⚠️ 請先確保您的 Gemini API Key 已在 Secrets 中設定成功！")
            else:
                with st.spinner("🧠 正在將您的資產結構傳送給 Gemini 3.5 進行深度解析..."):
                    portfolio_summary = f"總市值: NTD {int(local_total_val):,}\n"
                    for item in current_view_data:
                        tk_name = item['ticker'].replace('.TWO','').replace('.TW', '')
                        real_pct = (item["now_val_ntd"] / local_total_val * 100) if local_total_val > 0 else 0
                        portfolio_summary += f"- {tk_name}：目前佔比 {real_pct:.1f}% (設定目標 {item['target_pct']}%)，當前乖離率 {item['bias']:.1f}%，距高點回撤 {item['drawdown']:.1f}%\n"
                        
                    prompt = f"""
                    你現在是一位頂級的財富管理顧問與量化交易員。
                    請為我診斷以下的【{market_label}投資組合】目前狀態。
                    
                    【投資組合概況】
                    {portfolio_summary}
                    
                    請以專業但白話的繁體中文給出：
                    1. 資金配置健檢 (整體風險是否過度集中？防禦性部位是否足夠？)
                    2. 再平衡具體操作建議 (針對偏離目標權重過多、或乖離率/回撤異常的特定標的，提出該買或賣的具體建議)
                    3. 下階段總體戰略策略
                    """
                    try:
                        model = genai.GenerativeModel("gemini-3.5-flash")
                        response = model.generate_content(prompt)
                        st.success("✅ 成功產生 AI 投資組合診斷報告！")
                        st.info(response.text)
                    except Exception as ai_err:
                        err_str = str(ai_err)
                        if "429" in err_str or "quota" in err_str.lower():
                            st.warning("⚠️ 3.5 模型額度已滿，自動切換至 2.5 穩定版...")
                            try:
                                fallback_model = genai.GenerativeModel("gemini-2.5-flash")
                                fallback_response = fallback_model.generate_content(prompt)
                                st.success("✅ 自動降檔成功！對接 Gemini 2.5 模型，以下是診斷結果：")
                                st.info(fallback_response.text)
                            except: st.error("❌ 連線失敗，請稍候再試。")
                        else:
                            try:
                                fallback_model = genai.GenerativeModel("gemini-2.5-flash")
                                fallback_response = fallback_model.generate_content(prompt)
                                st.success("✅ 成功對接 Gemini 2.5 穩定版模型！")
                                st.info(fallback_response.text)
                            except Exception as fallback_err:
                                st.error("❌ 連線失敗，請檢查網路或 API 權限。")

# ==========================================
# 6. 分頁：全球 K 線分析
# ==========================================
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析")
    k_period = st.radio("選擇 K 線週期：", ["日K", "週K", "月K", "年K"], horizontal=True)
    
    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = "6285"
    
    if "active_kline_ticker" not in st.session_state:
        st.session_state.active_kline_ticker = default_ticker
    
    if market_choice == "自訂輸入個股": 
        raw_ticker_input = st.text_input("輸入欲分析的代碼或股名 (支援中文硬解)：", value=st.session_state.active_kline_ticker)
        if st.button("🔍 點擊開始解析個股數據", type="primary"):
            st.session_state.active_kline_ticker = raw_ticker_input
    else: 
        st.session_state.active_kline_ticker = default_ticker
    
    if "ai_data" not in st.session_state:
        st.session_state.ai_data = None
    
    target_to_parse = st.session_state.active_kline_ticker
    
    if target_to_parse:
        ticker_input, zh_name = smart_resolve_ticker(target_to_parse, api_key)
        
        if not ticker_input:
            st.error(f"❌ 查無此標的。若輸入中文失敗，請確認是否已成功綁定 API Key。")
        else:
            st.success(f"📊 智慧搜尋成功：系統已成功鎖定官方代碼為 ` {ticker_input} `")
            
            try:
                with st.spinner("正在載入戰情儀表板與技術圖表中..."):
                    period_map = {"日K": "2y", "週K": "5y", "月K": "10y", "年K": "max"}
                    interval_map = {"日K": "1d", "週K": "1wk", "月K": "1mo", "年K": "1mo"}
                    
                    df = yf.download(ticker_input, period=period_map[k_period], interval=interval_map[k_period], progress=False, session=yf_session)
                    if not df.empty:
                        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                        if k_period == "年K":
                            try: df = df.resample('YE').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                            except: df = df.resample('Y').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                        
                        df.dropna(subset=['Close'], inplace=True)
                        
                        delta = df['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        df['RSI'] = 100 - (100 / (1 + rs))
                        
                        if k_period == "日K": ma1, ma2, ma3, n1, n2, n3 = 5, 20, 200, "MA5 (週線)", "MA20 (月線)", "MA200 (年線)"
                        elif k_period == "週K": ma1, ma2, ma3, n1, n2, n3 = 4, 13, 52, "MA4 (月線)", "MA13 (季線)", "MA52 (年線)"
                        elif k_period == "月K": ma1, ma2, ma3, n1, n2, n3 = 6, 12, 60, "MA6 (半年線)", "MA12 (年線)", "MA60 (五年線)"
                        else: ma1, ma2, ma3, n1, n2, n3 = 3, 5, 10, "MA3 (三年線)", "MA5 (五年線)", "MA10 (十年線)"
                            
                        df['MA1'] = df['Close'].rolling(ma1).mean()
                        df['MA2'] = df['Close'].rolling(ma2).mean()
                        df['MA3'] = df['Close'].rolling(ma3).mean()
                        
                        try:
                            info = yf.Ticker(ticker_input, session=yf_session).info
                            try: pe = float(info.get('trailingPE', 0) or 0)
                            except: pe = 0
                            try: yield_pct = float(info.get('dividendYield', 0) or 0)
                            except: yield_pct = 0
                            sector = info.get('sector', '未提供')
                            industry = info.get('industry', '')
                            sector_str = f"{sector} - {industry}" if industry else sector
                        except: pe, yield_pct, sector_str = 0, 0, "未提供"
                            
                        rsi_val = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 0
                        
                        st.markdown("### 📊 多維度戰情儀表板")
                        cc1, cc2, cc3 = st.columns(3)
                        pe_str = f"{pe:.1f} 倍" if pe > 0 else "無/虧損"
                        yield_str = f"{yield_pct*100:.2f} %" if yield_pct > 0 else "無配息"
                        rsi_str = f"{rsi_val:.1f}"
                        rsi_status = "🔴 超買過熱" if rsi_val > 70 else ("🟢 超賣低估" if rsi_val < 30 else "🟡 中性盤整")
                        
                        card_style = "background-color: #f1f5f9; border-radius: 8px; padding: 14px; border-left: 5px solid #10b981; color: #0f172a; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 10px;"
                        
                        cc1.markdown(f"<div style='{card_style}'><b style='color: #0f172a;'>🏢 產業與板塊</b><br><span style='color: #0f172a; font-weight: 700; font-size: 1.1rem;'>{sector_str}</span></div>", unsafe_allow_html=True)
                        cc2.markdown(f"<div style='{card_style}'><b style='color: #0f172a;'>📈 核心基本面</b><br><span style='color: #0f172a; font-weight: 700; font-size: 1.1rem;'>本益比: {pe_str} | 殖利率: {yield_str}</span></div>", unsafe_allow_html=True)
                        cc3.markdown(f"<div style='{card_style}'><b style='color: #0f172a;'>⚡ 短線動能 (14期 RSI)</b><br><span style='color: #0f172a; font-weight: 700; font-size: 1.1rem;'>{rsi_str} ({rsi_status})</span></div>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        clean_title = ticker_input.replace('.TWO', '').replace('.TW', '')
                        st.subheader(f"📈 {clean_title} {zh_name} 技術走勢")
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA1'], mode='lines', name=n1, line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA2'], mode='lines', name=n2, line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA3'], mode='lines', name=n3, line=dict(color='#ef4444', width=2)), row=1, col=1)
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                        
                        if k_period == "日K": range_start = df.index.max() - pd.Timedelta(days=180)
                        elif k_period == "週K": range_start = df.index.max() - pd.Timedelta(days=365*2)
                        elif k_period == "月K": range_start = df.index.max() - pd.Timedelta(days=365*5)
                        else: range_start = df.index.min()
                        
                        fig.update_xaxes(range=[range_start, df.index.max()], row=1, col=1)
                        fig.update_xaxes(range=[range_start, df.index.max()], row=2, col=1)
                        
                        fig.update_layout(xaxis_rangeslider_visible=False, height=650, margin=dict(t=40, b=10, l=10, r=10), template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                        st.session_state.ai_data = {
                            "title": clean_title, "zh_name": zh_name, "k_period": k_period, "close": float(df['Close'].iloc[-1]),
                            "n3": n3, "ma3": float(df['MA3'].iloc[-1]), "rsi": rsi_val, "rsi_status": rsi_status,
                            "pe": pe_str, "yield": yield_str, "sector": sector_str
                        }
                    else: st.error("⚠️ 數據抓取失敗，請確認代碼後稍候重試。")
            except Exception as e:
                st.error(f"圖表載入失敗，請確認網路或輸入的名稱是否正確。")
                st.code(f"系統詳細錯誤日誌: {str(e)}")

    # ==========================================
    # 🤖 AI 單一個股診斷引擎
    # ==========================================
    if st.session_state.ai_data is not None:
        st.markdown("---")
        st.subheader("🤖 AI 專屬個股診斷")
        if st.button("✨ 讓 Gemini 分析目前盤勢", key="ai_btn", type="secondary"):
            if not api_key:
                st.warning("⚠️ 請先確認您的 Gemini API Key 已填寫！")
            else:
                d = st.session_state.ai_data
                with st.spinner("正在呼叫最新一代 Gemini 3.5 Flash 進行大數據診斷..."):
                    prompt = f"""
                    你現在是一位頂級的量化交易分析師。請根據以下最新抓取的股票數據，為我提供操作建議。
                    標的：{d['title']} {d['zh_name']}
                    K線週期：{d['k_period']}
                    最新收盤價：{d['close']:.2f}
                    關鍵長天期均線 ({d['n3']})：{d['ma3']:.2f}
                    14期 RSI：{d['rsi']:.1f} ({d['rsi_status']})
                    本益比：{d['pe']}
                    殖利率：{d['yield']}
                    所屬板塊：{d['sector']}
                    
                    請以繁體中文給出：
                    1. 盤勢總結 (一句話點出目前位階是便宜、昂貴、多頭還是空頭)
                    2. 多空風險評估 (結合 RSI 與均線判斷)
                    3. 短中線具體操作建議
                    """
                    
                    try:
                        model = genai.GenerativeModel("gemini-3.5-flash")
                        response = model.generate_content(prompt)
                        st.success("✅ 成功對接 Gemini 3.5 次世代模型！")
                        st.info(response.text)
                    except Exception as ai_err:
                        err_str = str(ai_err)
                        if "429" in err_str or "quota" in err_str.lower():
                            st.warning("⚠️ Gemini 3.5 的免費額度已達上限 (每分鐘最多 5 次)。系統正自動為您切換至高額度的 2.5 版穩定模型...")
                            try:
                                fallback_model = genai.GenerativeModel("gemini-2.5-flash")
                                fallback_response = fallback_model.generate_content(prompt)
                                st.success("✅ 自動降檔成功！對接 Gemini 2.5 模型，以下是診斷結果：")
                                st.info(fallback_response.text)
                            except Exception:
                                st.error("❌ 連線失敗，可能所有模型的免費額度皆已用盡，請等待 1 分鐘後再試。")
                        else:
                            try:
                                fallback_model = genai.GenerativeModel("gemini-2.5-flash")
                                fallback_response = fallback_model.generate_content(prompt)
                                st.success("✅ 成功對接 Gemini 2.5 穩定版模型！")
                                st.info(fallback_response.text)
                            except Exception as fallback_err:
                                st.error("❌ 連線失敗，請檢查網路或 API 權限。")
