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

# ==========================================
# 1. 頁面配置與專業金融視覺優化
# ==========================================
st.set_page_config(layout="wide", page_title="全球資產動態平衡系統", page_icon="🏦")

st.markdown("""
    <style>
    :root { --bg-panel: #1e293b; --text-main: #f8fafc; --accent-tw: #00ffcc; --accent-us: #f97316; }
    .market-header { 
        padding: 16px 20px; border-radius: 10px; font-weight: 700; 
        margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        letter-spacing: 1px;
    }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid var(--accent-tw); }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid var(--accent-us); }
    .adv-market { background: linear-gradient(135deg, #171717 0%, #262626 100%); border-left: 8px solid #a855f7; }
    
    /* 專屬高亮代碼字體樣式 */
    .ticker-display { font-size: 2.2rem; font-weight: 900; color: #ffffff; line-height: 1.2; letter-spacing: 0.5px; }
    .price-display { font-size: 1.2rem; font-weight: 600; color: #94a3b8; margin-top: 4px; }
    .data-label { font-size: 1rem; color: #cbd5e1; margin-bottom: 2px;}
    .data-value { font-size: 1.1rem; font-weight: 700; color: #f8fafc;}
    
    label, .stMarkdown p { font-weight: 500; }
    hr { border-color: #334155; }
    .status-safe { color: #10b981; font-weight: bold; }
    .status-warn { color: #ef4444; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 智慧代碼解析與槓桿自動偵測引擎
# ==========================================
def resolve_ticker(user_input):
    t = user_input.strip().upper()
    if not t: return ""
    if t in ["現金", "CASH"]: return "CASH"
    
    if t.startswith("^") or t.endswith(".TW") or t.endswith(".TWO"): return t
    if re.match(r'^\d+[A-Z]?$', t):
        test_tw = yf.download(f"{t}.TW", period="1d", progress=False)
        if not test_tw.empty: return f"{t}.TW"
        test_two = yf.download(f"{t}.TWO", period="1d", progress=False)
        if not test_two.empty: return f"{t}.TWO"
        return f"{t}.TW"
    if re.search(r'[\u4e00-\u9fff]', t):
        try:
            res = yf.Search(t, max_results=1).quotes
            if res: return res[0]['symbol']
        except: pass
    return t

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

@st.cache_data(ttl=86400)
def fetch_yield(ticker):
    if ticker == "CASH": return 0.0
    try:
        info = yf.Ticker(ticker).info
        raw_yield = info.get('dividendYield', 0.0)
        return float(raw_yield) * 100 if raw_yield else 0.0
    except:
        return 0.0

# ==========================================
# 3. 核心功能：獨立存檔機制
# ==========================================
def load_portfolio():
    default_data = {
        "init_funds": 1000000, "tw_portfolio": [], "us_portfolio": [],
        "watchlist": [{"ticker": "6285.TW", "target_price": 267.0}, {"ticker": "QQQ", "target_price": 420.0}],
        "pledge_loan": 0.0, "pledge_rate": 2.5
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
                for k in default_data.keys():
                    if k not in data: data[k] = default_data[k]
                return data
        except: pass
    return default_data

def save_portfolio(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@st.cache_data(ttl=3600)
def fetch_realtime_data(ticker):
    if ticker == "CASH": return 1.0 
    try:
        data = yf.download(ticker, period="5d", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            valid_closes = data['Close'].dropna() 
            if not valid_closes.empty: return float(valid_closes.iloc[-1])
    except: return None
    return None

current_rate = fetch_realtime_data("TWD=X") or 32.5
db_data = load_portfolio()

# ==========================================
# 4. 側邊欄配置
# ==========================================
st.sidebar.title("🎛️ 策略監控中心")
st.sidebar.markdown(f"📈 **即時匯率 USD/TWD：** `{current_rate:.2f}`")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "功能分頁導覽：", 
    ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控", "🎯 進階：質押與觀察清單", "🔍 全球 K 線分析"]
)
st.sidebar.markdown("---")

if app_mode == "🔍 全球 K 線分析":
    st.sidebar.header("🌍 大盤速查")
    market_choice = st.sidebar.radio("快速切換 K 線圖：", ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"])

if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    threshold = st.sidebar.slider("⚖️ 再平衡觸發門檻 (%)", 0.0, 10.0, 2.0, 0.5)
    init_funds = st.sidebar.number_input("💵 單一市場投入本金 (NTD)", value=int(db_data.get("init_funds", 1000000)), step=10000)
    num_assets = st.sidebar.number_input("🔢 展開標的輸入欄位數", value=len(db_data.get("tw_portfolio" if app_mode == "🇹🇼 台股持股監控" else "us_portfolio", [])) or 3, min_value=1)
    db_data["init_funds"] = init_funds

# ==========================================
# 5. 主功能：資產動態監控盤
# ==========================================
if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    is_tw_mode = (app_mode == "🇹🇼 台股持股監控")
    market_label = "台股" if is_tw_mode else "美股"
    current_list_key = "tw_portfolio" if is_tw_mode else "us_portfolio"
    
    st.markdown(f'<h1>🏦 {app_mode.split(" ")[1]} 專業分析面板</h1>', unsafe_allow_html=True)
    
    with st.expander(f"⚙️ 編輯 {market_label} 初始配置 (該市場總權重應為 100%)", expanded=(not db_data[current_list_key])):
        st.info(f"💡 提示：若想配置備用資金，請在代碼直接輸入 **「現金」** 或 **「CASH」**。殖利率可留空由系統自動檢索。")
        cols = st.columns([2, 2, 2])
        cols[0].markdown("**代碼 / 現金**"); cols[1].markdown("**目標權重%**"); cols[2].markdown("**預估殖利率% (可填0)**")
        
        new_setup = []
        for i in range(int(num_assets)):
            r_cols = st.columns([2, 2, 2])
            hist = db_data[current_list_key][i] if i < len(db_data[current_list_key]) else {"ticker": "", "target_pct": 0, "yield_pct": 0.0}
            
            display_tk = hist["ticker"].replace(".TWO", "").replace(".TW", "") if (".TW" in hist.get("ticker", "") or ".TWO" in hist.get("ticker", "")) else hist.get("ticker", "")
            raw_tk = r_cols[0].text_input(f"tk_{i}", display_tk, label_visibility="collapsed", placeholder="代碼 或 現金").strip()
            
            safe_pct = min(100.0, max(0.0, float(hist.get("target_pct", 0.0))))
            safe_yld = min(1000.0, max(0.0, float(hist.get("yield_pct", 0.0))))
            
            pct = r_cols[1].number_input(f"pct_{i}", min_value=0.0, max_value=100.0, value=safe_pct, step=5.0, label_visibility="collapsed")
            yld = r_cols[2].number_input(f"yld_{i}", min_value=0.0, max_value=1000.0, value=safe_yld, step=0.5, label_visibility="collapsed")
            
            if raw_tk: new_setup.append({"raw_ticker": raw_tk, "target_pct": pct, "yield_pct": yld})
        
        if st.button(f"📌 鎖定 {market_label} 庫存並更新系統", type="primary"):
            locked_assets = []
            error_tickers = []
            with st.spinner('正在解析代碼並同步市場數據...'):
                for item in new_setup:
                    real_ticker = resolve_ticker(item["raw_ticker"])
                    p = fetch_realtime_data(real_ticker)
                    lev = get_leverage(real_ticker)
                    
                    if p and p > 0: 
                        alloc_ntd = init_funds * (item["target_pct"] / 100)
                        price_ntd = p if is_tw_mode else (p * current_rate)
                        shares = int(alloc_ntd / price_ntd) if not real_ticker.startswith("^") else 1
                        
                        auto_yld = fetch_yield(real_ticker)
                        final_yield = item["yield_pct"] if item["yield_pct"] > 0 else auto_yld
                        
                        locked_assets.append({
                            "ticker": real_ticker, "target_pct": item["target_pct"], "leverage": lev, 
                            "init_shares": shares, "init_price": p, "yield_pct": final_yield,
                            "is_tw": is_tw_mode # 絕對領域標記：強制綁定當前國籍！
                        })
                    else: error_tickers.append(item["raw_ticker"])
            
            if error_tickers: st.error(f"⚠️ 無法抓取以下代碼：{', '.join(error_tickers)}")
            else:
                db_data[current_list_key] = locked_assets
                save_portfolio(db_data)
                st.success(f"🔒 {market_label} 組合分析模型建立成功！")
                st.rerun()

    # 📌 數據處理與渲染
    current_view_data = []
    tw_total_market_val, us_total_market_val = 0, 0
    tw_total_exposure, us_total_exposure = 0, 0
    tw_dividend, us_dividend = 0, 0
    
    all_assets_list = db_data["tw_portfolio"] + db_data["us_portfolio"]
    
    if all_assets_list:
        with st.spinner("🔄 正在運算最新現金流與估值..."):
            for asset in all_assets_list:
                now_p = fetch_realtime_data(asset["ticker"])
                if now_p and now_p > 0:
                    # 讀取絕對領域標記，若無標記(舊資料)才使用名稱盲猜
                    is_tw = asset.get("is_tw", (".TW" in asset["ticker"] or ".TWO" in asset["ticker"] or asset["ticker"].startswith("^") or asset["ticker"] == "CASH"))
                    lev = asset.get("leverage", 1.0)
                    
                    if asset["ticker"].startswith("^"):
                        now_val_ntd = db_data["init_funds"] * (asset["target_pct"] / 100) * (now_p / asset.get("init_price", now_p))
                    else:
                        price_ntd = now_p if is_tw else (now_p * current_rate)
                        now_val_ntd = price_ntd * asset.get("init_shares", 0)
                    
                    exposure_ntd = now_val_ntd * lev
                    div_cash = now_val_ntd * (asset.get("yield_pct", 0) / 100)
                    
                    record = {**asset, "now_p": now_p, "now_val_ntd": now_val_ntd, "exposure_ntd": exposure_ntd, "div_cash": div_cash, "is_tw": is_tw}
                    
                    if is_tw:
                        tw_total_market_val += now_val_ntd
                        tw_total_exposure += exposure_ntd
                        tw_dividend += div_cash
                        if is_tw_mode: current_view_data.append(record)
                    else:
                        us_total_market_val += now_val_ntd
                        us_total_exposure += exposure_ntd
                        us_dividend += div_cash
                        if not is_tw_mode: current_view_data.append(record)

        local_total_val = tw_total_market_val if is_tw_mode else us_total_market_val
        local_total_exp = tw_total_exposure if is_tw_mode else us_total_exposure
        local_dividend = tw_dividend if is_tw_mode else us_dividend

        if current_view_data:
            st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">{"🇹🇼 台灣市場" if is_tw_mode else "🇺🇸 美國市場"} 動態監控盤</div>', unsafe_allow_html=True)
            for item in current_view_data:
                c = st.columns([1.5, 1.2, 1.2, 1.5, 1.5, 2.6])
                real_pct = (item["now_val_ntd"] / local_total_val * 100) if local_total_val > 0 else 0
                diff = real_pct - item["target_pct"]
                
                # 專屬高亮渲染
                if item["ticker"] == "CASH":
                    currency_str = "TWD" if item['is_tw'] else "USD"
                    unit_str = "元" if item['is_tw'] else "美元"
                    c[0].markdown(f"<div class='ticker-display'>💵 現金</div><div class='price-display'>{currency_str} 保留款</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>持有額:</div><div class='data-value'>{int(item.get('init_shares', 0)):,} {unit_str}</div>", unsafe_allow_html=True)
                else:
                    clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='price-display'>{'NTD' if item['is_tw'] else 'USD'} {item['now_p']:.2f}</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>{'📊 指數追蹤' if item['ticker'].startswith('^') else '持有股數:'}</div><div class='data-value'>{item.get('init_shares', 0):,} 股</div>", unsafe_allow_html=True)
                
                c[2].markdown(f"<div class='data-label'>目標設定:</div><div class='data-value'>{item['target_pct']}%</div><div class='data-label' style='margin-top:4px;'>殖利率:</div><div class='data-value'>{item.get('yield_pct', 0):.1f}%</div>", unsafe_allow_html=True)
                c[3].markdown(f"<div class='data-label'>真實市值:</div><div class='data-value'>NTD {int(item['now_val_ntd']):,}</div>", unsafe_allow_html=True)
                c[4].markdown(f"<div class='data-label'>槓桿: <span style='color:#f8fafc; font-weight:700;'>{item.get('leverage', 1.0)}x</span></div><div class='data-label' style='margin-top:4px;'>曝險規模:</div><div class='data-value'>{int(item['exposure_ntd']):,}</div>", unsafe_allow_html=True)
                
                if abs(diff) > threshold: c[5].warning(f"⚠️ 偏離 {diff:+.1f}%\n(真實佔比: {real_pct:.1f}%)")
                else: c[5].success(f"✅ 平衡區間\n(真實佔比: {real_pct:.1f}%)")

        # 📌 底部結算與圖表
        st.markdown("---")
        footer_cols = st.columns([1, 1])
        with footer_cols[0]:
            st.subheader(f"💰 {market_label} 綜合指標總結")
            overall_leverage = local_total_exp / local_total_val if local_total_val > 0 else 1.0
            
            sc1, sc2 = st.columns(2)
            sc1.metric(f"{market_label} 總市值 (NTD)", f"{int(local_total_val):,}")
            sc2.metric(f"{market_label} 總曝險 (NTD)", f"{int(local_total_exp):,}")
            
            sc3, sc4 = st.columns(2)
            sc3.metric(f"{market_label} 槓桿水位", f"{overall_leverage:.2f} 倍")
            sc4.metric("預估年被動收入 (NTD)", f"{int(local_dividend):,}")

            if current_view_data:
                pie_df = pd.DataFrame([{"tk": "現金" if r["ticker"] == "CASH" else r["ticker"].replace('.TWO','').replace('.TW', ''), "val": r["now_val_ntd"]} for r in current_view_data])
                fig_pie = px.pie(pie_df, values='val', names='tk', hole=0.4, title=f"{market_label}資產真實分佈", color_discrete_sequence=px.colors.qualitative.Prism)
                fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with footer_cols[1]:
            if current_view_data:
                st.subheader(f"📊 {market_label} 權重偏差分析")
                bar_df = pd.DataFrame([{"tk": "現金" if r["ticker"] == "CASH" else r["ticker"].replace('.TWO','').replace('.TW', ''), "Real": (r["now_val_ntd"]/local_total_val*100), "Target": r["target_pct"]} for r in current_view_data])
                fig_bar = go.Figure(data=[
                    go.Bar(name='真實權重 (%)', x=bar_df['tk'], y=bar_df['Real'], marker_color='#00ffcc'),
                    go.Bar(name='設定目標 (%)', x=bar_df['tk'], y=bar_df['Target'], marker_color='#334155')
                ])
                fig_bar.update_layout(barmode='group', height=400, margin=dict(t=30, b=0, l=0, r=0), template="plotly_dark")
                st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# 7. 分頁：進階質押與觀察清單
# ==========================================
elif app_mode == "🎯 進階：質押與觀察清單":
    st.markdown('<div class="market-header adv-market">🎯 長期投資風險與目標控管中心</div>', unsafe_allow_html=True)
    
    total_val_for_pledge, annual_div_for_pledge = 0, 0
    for asset in db_data["tw_portfolio"]:
        now_p = fetch_realtime_data(asset["ticker"])
        if now_p and now_p > 0:
            if asset["ticker"].startswith("^"): val = db_data["init_funds"] * (asset["target_pct"] / 100) * (now_p / asset.get("init_price", now_p))
            else: val = now_p * asset.get("init_shares", 0) 
            total_val_for_pledge += val
            annual_div_for_pledge += val * (asset.get("yield_pct", 0) / 100)
            
    for asset in db_data["us_portfolio"]:
        now_p = fetch_realtime_data(asset["ticker"])
        if now_p and now_p > 0:
            if asset["ticker"].startswith("^"): val = db_data["init_funds"] * (asset["target_pct"] / 100) * (now_p / asset.get("init_price", now_p))
            else: val = (now_p * current_rate) * asset.get("init_shares", 0)
            total_val_for_pledge += val
            annual_div_for_pledge += val * (asset.get("yield_pct", 0) / 100)

    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        st.subheader("🏦 資金成本與質押維持率監控")
        pledge_loan = st.number_input("💸 目前總借款/質押金額 (NTD)", value=float(db_data.get("pledge_loan", 0.0)), step=10000.0)
        pledge_rate = st.number_input("📉 銀行質押/融資利率 (%)", value=float(db_data.get("pledge_rate", 2.5)), step=0.1)
        
        if st.button("更新質押數據"):
            db_data["pledge_loan"] = pledge_loan
            db_data["pledge_rate"] = pledge_rate
            save_portfolio(db_data)
            st.success("數據已更新")
            
        st.markdown("---")
        maintenance_ratio = (total_val_for_pledge / pledge_loan * 100) if pledge_loan > 0 else 0
        annual_interest = pledge_loan * (pledge_rate / 100)
        net_cash_flow = annual_div_for_pledge - annual_interest
        
        m1, m2 = st.columns(2)
        if pledge_loan > 0:
            status_color = "status-safe" if maintenance_ratio >= 160 else "status-warn"
            m1.markdown(f"**全局維持率：** <span class='{status_color}'>{maintenance_ratio:.1f}%</span>", unsafe_allow_html=True)
        else: m1.markdown("**維持率：** 無借款")
        m2.markdown(f"**全局預估年利息：** NTD {int(annual_interest):,}")
        
        cash_status = "status-safe" if net_cash_flow > 0 else "status-warn"
        st.markdown(f"#### 全局預估淨現金流 (股息 - 利息)： <span class='{cash_status}'>NTD {int(net_cash_flow):,}</span>", unsafe_allow_html=True)

    with col_p2:
        st.subheader("🎯 狙擊手觀察清單")
        new_tk = st.text_input("新增觀察標的代碼", placeholder="例如: 2330 或 QQQ")
        new_tp = st.number_input("設定目標進場價", min_value=0.0, step=1.0)
        if st.button("加入觀察清單"):
            real_tk = resolve_ticker(new_tk)
            if real_tk:
                db_data["watchlist"].append({"ticker": real_tk, "target_price": new_tp})
                save_portfolio(db_data)
                st.rerun()

        st.markdown("---")
        wl_data = []
        for w in db_data["watchlist"]:
            p = fetch_realtime_data(w["ticker"])
            if p:
                dist = ((p - w["target_price"]) / w["target_price"]) * 100
                wl_data.append({
                    "代碼": w["ticker"].replace('.TWO','').replace('.TW', ''),
                    "目前市價": round(p, 2),
                    "打擊目標價": w["target_price"],
                    "距離目標": f"{dist:+.1f}%",
                    "狀態": "🟢 進場區間" if p <= w["target_price"] else "⏳ 等待回檔"
                })
        if wl_data: st.dataframe(pd.DataFrame(wl_data), use_container_width=True, hide_index=True)

# ==========================================
# 8. 分頁：全球 K 線分析
# ==========================================
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析")
    
    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = "6285"
    
    if market_choice == "自訂輸入個股":
        raw_ticker_input = st.text_input("輸入欲分析代碼：", default_ticker)
    else: raw_ticker_input = default_ticker
    
    if raw_ticker_input:
        ticker_input = resolve_ticker(raw_ticker_input)
        try:
            with st.spinner("載入圖表與計算均線中..."):
                df_k = yf.download(ticker_input, period="2y", interval="1d", progress=False)
                if not df_k.empty:
                    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
                    df_k['MA5'] = df_k['Close'].rolling(window=5).mean()
                    df_k['MA20'] = df_k['Close'].rolling(window=20).mean()
                    df_k['MA200'] = df_k['Close'].rolling(window=200).mean()
                    
                    clean_title = ticker_input.replace('.TWO', '').replace('.TW', '')
                    fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                    fig_k.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="K線"), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA5'], mode='lines', name='MA5 (週線)', line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA20'], mode='lines', name='MA20 (月線)', line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA200'], mode='lines', name='MA200 (年線)', line=dict(color='#ef4444', width=2)), row=1, col=1)
                    fig_k.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                    
                    last_6mo = df_k.index.max() - pd.Timedelta(days=180)
                    fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=1, col=1)
                    fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=2, col=1)
                    fig_k.update_layout(xaxis_rangeslider_visible=False, height=650, template="plotly_dark")
                    st.plotly_chart(fig_k, use_container_width=True)
        except: st.error("代碼有誤或暫無數據。")
