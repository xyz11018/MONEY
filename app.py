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
    /* 全域字體與專業感配色 */
    :root { --bg-panel: #1e293b; --text-main: #f8fafc; --accent-tw: #00ffcc; --accent-us: #f97316; }
    
    /* 質感標題區塊 */
    .market-header { 
        padding: 16px 20px; border-radius: 10px; font-weight: 700; 
        margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        letter-spacing: 1px;
    }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid var(--accent-tw); }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid var(--accent-us); }
    .adv-market { background: linear-gradient(135deg, #171717 0%, #262626 100%); border-left: 8px solid #a855f7; }
    
    /* 數據卡片優化 */
    div[data-testid="stMetricValue"] { font-weight: 800 !important; font-size: 2rem !important; }
    label, .stMarkdown p { font-weight: 500; }
    hr { border-color: #334155; }
    
    /* 狀態提示色 */
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
# 3. 核心功能：獨立存檔與進階資料結構
# ==========================================
def load_portfolio():
    default_data = {
        "init_funds": 1000000, "tw_portfolio": [], "us_portfolio": [],
        "watchlist": [{"ticker": "6285.TW", "target_price": 267.0}, {"ticker": "QQQ", "target_price": 420.0}, {"ticker": "SCHD", "target_price": 75.0}],
        "pledge_loan": 0.0, "pledge_rate": 2.5
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
                if "locked_portfolio" in data: # 舊版兼容
                    data = {"init_funds": data.get("init_funds", 1000000), "tw_portfolio": data["locked_portfolio"], "us_portfolio": [], "watchlist": default_data["watchlist"], "pledge_loan": 0.0, "pledge_rate": 2.5}
                # 確保新欄位存在
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
# 4. 側邊欄：主選單與全局設定
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
    market_choice = st.sidebar.radio(
        "快速切換 K 線圖：", 
        ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"]
    )

if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    threshold = st.sidebar.slider("⚖️ 再平衡觸發門檻 (%)", 0.0, 10.0, 2.0, 0.5)
    init_funds = st.sidebar.number_input("💵 初始投入總資金 (NTD)", value=int(db_data.get("init_funds", 1000000)), step=10000)
    num_assets = st.sidebar.number_input("🔢 展開標的輸入欄位數", value=len(db_data.get("tw_portfolio" if app_mode == "🇹🇼 台股持股監控" else "us_portfolio", [])) or 3, min_value=1)
    db_data["init_funds"] = init_funds

# ==========================================
# 5. 主功能：資產動態監控盤 (台美獨立)
# ==========================================
if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    is_tw_mode = (app_mode == "🇹🇼 台股持股監控")
    market_label = "台股" if is_tw_mode else "美股"
    current_list_key = "tw_portfolio" if is_tw_mode else "us_portfolio"
    
    st.markdown(f'<h1>🏦 {app_mode.split(" ")[1]} 專業分析面板</h1>', unsafe_allow_html=True)
    
    # 📌 獨立設定區 (新增產業與殖利率)
    with st.expander(f"⚙️ 編輯 {market_label} 初始配置 (板塊與現金流)", expanded=(not db_data[current_list_key])):
        st.info(f"💡 建立您的長期部位：填入代碼、權重，並為標的設定**產業分類**（如：AI伺服器/硬體、高股息）與**預估殖利率**。")
        cols = st.columns([1.5, 1, 1.5, 1])
        cols[0].markdown("**代碼**"); cols[1].markdown("**目標權重%**"); cols[2].markdown("**產業分類**"); cols[3].markdown("**殖利率%**")
        
        new_setup = []
        for i in range(int(num_assets)):
            r_cols = st.columns([1.5, 1, 1.5, 1])
            hist = db_data[current_list_key][i] if i < len(db_data[current_list_key]) else {"ticker": "", "target_pct": 0, "sector": "", "yield_pct": 0.0}
            
            display_tk = hist["ticker"].replace(".TWO", "").replace(".TW", "") if (".TW" in hist.get("ticker", "") or ".TWO" in hist.get("ticker", "")) else hist.get("ticker", "")
            raw_tk = r_cols[0].text_input(f"tk_{i}", display_tk, label_visibility="collapsed", placeholder="例如: 6285 或 QQQ").strip()
            pct = r_cols[1].number_input(f"pct_{i}", 0.0, 100.0, float(hist.get("target_pct", 0)), 5.0, label_visibility="collapsed")
            sec = r_cols[2].text_input(f"sec_{i}", hist.get("sector", ""), label_visibility="collapsed", placeholder="例如: AI硬體、科技")
            yld = r_cols[3].number_input(f"yld_{i}", 0.0, 30.0, float(hist.get("yield_pct", 0.0)), 0.5, label_visibility="collapsed")
            
            if raw_tk: new_setup.append({"raw_ticker": raw_tk, "target_pct": pct, "sector": sec if sec else "未分類", "yield_pct": yld})
        
        if st.button(f"📌 鎖定 {market_label} 庫存並更新系統", type="primary"):
            locked_assets = []
            error_tickers = []
            with st.spinner('正在同步市場數據與板塊結構...'):
                for item in new_setup:
                    real_ticker = resolve_ticker(item["raw_ticker"])
                    p = fetch_realtime_data(real_ticker)
                    lev = get_leverage(real_ticker)
                    
                    if p and p > 0: 
                        is_tw = ".TW" in real_ticker or ".TWO" in real_ticker or real_ticker.startswith("^")
                        alloc_ntd = init_funds * (item["target_pct"] / 100)
                        price_ntd = p if is_tw else (p * current_rate)
                        shares = int(alloc_ntd / price_ntd) if not real_ticker.startswith("^") else 1
                        locked_assets.append({
                            "ticker": real_ticker, "target_pct": item["target_pct"], "leverage": lev, 
                            "init_shares": shares, "init_price": p, "sector": item["sector"], "yield_pct": item["yield_pct"]
                        })
                    else: error_tickers.append(item["raw_ticker"])
            
            if error_tickers: st.error(f"⚠️ 無法抓取以下代碼：{', '.join(error_tickers)}")
            else:
                db_data[current_list_key] = locked_assets
                save_portfolio(db_data)
                st.success(f"🔒 {market_label} 組合分析模型建立成功！")
                st.rerun()

    # 📌 監控顯示區
    current_view_data = []
    total_market_val_ntd, total_exposure_val_ntd, expected_annual_dividend = 0, 0, 0
    all_assets_list = db_data["tw_portfolio"] + db_data["us_portfolio"]
    
    if all_assets_list:
        with st.spinner("🔄 正在運算全球投資組合現金流與估值..."):
            for asset in all_assets_list:
                now_p = fetch_realtime_data(asset["ticker"])
                if now_p and now_p > 0:
                    is_tw = ".TW" in asset["ticker"] or ".TWO" in asset["ticker"] or asset["ticker"].startswith("^")
                    lev = asset.get("leverage", 1.0)
                    
                    if asset["ticker"].startswith("^"):
                        now_val_ntd = db_data["init_funds"] * (asset["target_pct"] / 100) * (now_p / asset.get("init_price", now_p))
                    else:
                        price_ntd = now_p if is_tw else (now_p * current_rate)
                        now_val_ntd = price_ntd * asset.get("init_shares", 0)
                    
                    exposure_ntd = now_val_ntd * lev
                    div_cash = now_val_ntd * (asset.get("yield_pct", 0) / 100)
                    
                    total_market_val_ntd += now_val_ntd
                    total_exposure_val_ntd += exposure_ntd
                    expected_annual_dividend += div_cash
                    
                    record = {**asset, "now_p": now_p, "now_val_ntd": now_val_ntd, "exposure_ntd": exposure_ntd, "div_cash": div_cash, "is_tw": is_tw}
                    if is_tw_mode and is_tw: current_view_data.append(record)
                    elif not is_tw_mode and not is_tw: current_view_data.append(record)

        if current_view_data:
            st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">{"🇹🇼 台灣市場" if is_tw_mode else "🇺🇸 美國市場"} 動態監控盤</div>', unsafe_allow_html=True)
            for item in current_view_data:
                c = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2.6])
                real_pct = (item["now_val_ntd"] / total_market_val_ntd * 100) if total_market_val_ntd > 0 else 0
                diff = real_pct - item["target_pct"]
                
                clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                c[0].metric(clean_name, f"{'NTD' if item['is_tw'] else 'USD'} {item['now_p']:.2f}")
                c[1].write(f"板塊: `{item.get('sector', '未分類')}`\n殖利率: {item.get('yield_pct', 0)}%")
                c[2].write(f"目標: {item['target_pct']}%")
                c[3].write(f"市值: NTD {int(item['now_val_ntd']):,}")
                c[4].write(f"系統偵測: **{item.get('leverage', 1.0)}x**槓桿\n曝險部位: {int(item['exposure_ntd']):,}")
                
                if abs(diff) > threshold: c[5].warning(f"⚠️ 偏離 {diff:+.1f}%\n(佔比: {real_pct:.1f}%)")
                else: c[5].success(f"✅ 平衡區間\n(佔比: {real_pct:.1f}%)")

        # 📌 底部結算與產業板塊圖表
        st.markdown("---")
        footer_cols = st.columns([1, 1])
        with footer_cols[0]:
            st.subheader("📊 產業板塊曝險分析")
            if current_view_data:
                # 繪製產業板塊分布圓餅圖
                sector_df = pd.DataFrame([{"sec": r.get("sector", "未分類"), "val": r["now_val_ntd"]} for r in current_view_data])
                sector_grouped = sector_df.groupby("sec").sum().reset_index()
                fig_sec = px.pie(sector_grouped, values='val', names='sec', hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
                fig_sec.update_layout(margin=dict(t=10, b=0, l=0, r=0))
                st.plotly_chart(fig_sec, use_container_width=True)
                
        with footer_cols[1]:
            st.subheader("💰 組合綜合指標總結")
            overall_leverage = total_exposure_val_ntd / total_market_val_ntd if total_market_val_ntd > 0 else 1.0
            
            sc1, sc2 = st.columns(2)
            sc1.metric("總市值本金 (NTD)", f"{int(total_market_val_ntd):,}")
            sc2.metric("總曝險規模 (NTD)", f"{int(total_exposure_val_ntd):,}")
            
            sc3, sc4 = st.columns(2)
            sc3.metric("整體槓桿水位", f"{overall_leverage:.2f} 倍")
            sc4.metric("預估年被動收入 (NTD)", f"{int(expected_annual_dividend):,}")

# ==========================================
# 6. 分頁：進階 質押與觀察清單
# ==========================================
elif app_mode == "🎯 進階：質押與觀察清單":
    st.markdown('<div class="market-header adv-market">🎯 長期投資風險與目標控管中心</div>', unsafe_allow_html=True)
    
    # 結算總庫存市值以供應質押計算
    total_val_for_pledge = 0
    annual_div_for_pledge = 0
    for asset in (db_data["tw_portfolio"] + db_data["us_portfolio"]):
        now_p = fetch_realtime_data(asset["ticker"])
        if now_p and now_p > 0:
            is_tw = ".TW" in asset["ticker"] or ".TWO" in asset["ticker"] or asset["ticker"].startswith("^")
            if asset["ticker"].startswith("^"):
                val = db_data["init_funds"] * (asset["target_pct"] / 100) * (now_p / asset.get("init_price", now_p))
            else:
                val = (now_p if is_tw else now_p * current_rate) * asset.get("init_shares", 0)
            total_val_for_pledge += val
            annual_div_for_pledge += val * (asset.get("yield_pct", 0) / 100)

    col_p1, col_p2 = st.columns([1, 1])
    
    with col_p1:
        st.subheader("🏦 資金成本與質押維持率監控")
        st.info("計算目前的借貸風險，並評估股息是否能完全 Cover 利息支出。")
        
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
            m1.markdown(f"**維持率：** <span class='{status_color}'>{maintenance_ratio:.1f}%</span>", unsafe_allow_html=True)
            if maintenance_ratio < 160: st.error("⚠️ 維持率低於 160% 警戒線，請留意斷頭風險！")
        else:
            m1.markdown("**維持率：** 無借款")
            
        m2.markdown(f"**預估年利息：** NTD {int(annual_interest):,}")
        
        cash_status = "status-safe" if net_cash_flow > 0 else "status-warn"
        st.markdown(f"#### 預估淨現金流 (股息 - 利息)： <span class='{cash_status}'>NTD {int(net_cash_flow):,}</span>", unsafe_allow_html=True)

    with col_p2:
        st.subheader("🎯 狙擊手觀察清單 (打擊區)")
        st.info("設定感興趣標的的理想進場價，系統會為您盯盤評估安全邊際。")
        
        new_tk = st.text_input("新增觀察標的代碼", placeholder="例如: 2330 或 SCHD")
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
        
        if wl_data:
            st.dataframe(pd.DataFrame(wl_data), use_container_width=True, hide_index=True)

# ==========================================
# 7. 分頁：全球 K 線分析 (含 MA200 年線)
# ==========================================
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析")
    
    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = "6285"
    
    if market_choice == "自訂輸入個股":
        st.info("💡 支援純數字、字母混合或中文（如: `0050`、`6285`、`台積電`、`AAPL`）")
        raw_ticker_input = st.text_input("輸入欲分析代碼：", default_ticker)
    else:
        raw_ticker_input = default_ticker
        st.success(f"目前追蹤大盤：**{market_choice}**")
    
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
                    st.subheader(f"目前顯示標的：{clean_title}")
                    
                    fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                    fig_k.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="K線"), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA5'], mode='lines', name='MA5 (週線)', line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA20'], mode='lines', name='MA20 (月線)', line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA200'], mode='lines', name='MA200 (年線)', line=dict(color='#ef4444', width=2)), row=1, col=1)
                    fig_k.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                    
                    last_6mo = df_k.index.max() - pd.Timedelta(days=180)
                    fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=1, col=1)
                    fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=2, col=1)
                    
                    fig_k.update_layout(xaxis_rangeslider_visible=False, height=650)
                    st.plotly_chart(fig_k, use_container_width=True)
        except:
            st.error("代碼有誤或暫無數據，請嘗試更換輸入名稱。")
