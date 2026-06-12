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
# 1. 頁面配置與高對比視覺優化
# ==========================================
st.set_page_config(layout="wide", page_title="全球資產動態平衡系統", page_icon="🏦")

st.markdown("""
    <style>
    .market-header { padding: 15px; border-radius: 8px; font-weight: bold; margin-bottom: 15px; font-size: 1.2rem; color: #ffffff !important; }
    .tw-market { background-color: #1e293b; border-left: 8px solid #00ffcc; }
    .us-market { background-color: #1e293b; border-left: 8px solid #f97316; }
    label, .stMarkdown p { font-weight: 500; }
    div[data-testid="stMetricValue"] { font-weight: 700 !important; }
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
    
    # 台股純數字或帶字母 (如 0050, 00631L, 2330, 00981A)
    if re.match(r'^\d+[A-Z]?$', t):
        # 自動測試上市或上櫃
        test_tw = yf.download(f"{t}.TW", period="1d", progress=False)
        if not test_tw.empty: return f"{t}.TW"
        test_two = yf.download(f"{t}.TWO", period="1d", progress=False)
        if not test_two.empty: return f"{t}.TWO"
        return f"{t}.TW"
        
    # 中文名稱搜尋
    if re.search(r'[\u4e00-\u9fff]', t):
        try:
            res = yf.Search(t, max_results=1).quotes
            if res: return res[0]['symbol']
        except: pass
        
    return t

def get_leverage(ticker):
    """自動偵測標的槓桿倍數"""
    t = ticker.upper()
    # 台股槓桿/反向
    if t.endswith("L.TW") or t.endswith("L.TWO"): return 2.0
    if t.endswith("R.TW") or t.endswith("R.TWO"): return -1.0
    # 美股常見槓桿
    us_3x = ["TQQQ", "SOXL", "UPRO", "UDOW", "TMF", "FAS", "TECL", "CURE", "NAIL", "YINN", "WEBL", "DPST", "FNGU"]
    us_2x = ["QLD", "SSO", "USD", "UWM", "MVV", "NVDL", "TSLL"]
    us_n3x = ["SQQQ", "SOXS", "SPXU", "SDOW", "TMV", "FAZ", "TECS", "WEBS", "FNGD"]
    base = t.split('.')[0]
    if base in us_3x: return 3.0
    if base in us_2x: return 2.0
    if base in us_n3x: return -3.0
    return 1.0

# ==========================================
# 3. 核心功能：獨立存檔機制
# ==========================================
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
                # 兼容舊版資料結構
                if "locked_portfolio" in data:
                    return {"init_funds": data.get("init_funds", 1000000), "tw_portfolio": data["locked_portfolio"], "us_portfolio": []}
                return data
        except: pass
    return {"init_funds": 1000000, "tw_portfolio": [], "us_portfolio": []}

def save_portfolio(funds, tw_assets, us_assets):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"init_funds": funds, "tw_portfolio": tw_assets, "us_portfolio": us_assets}, f, ensure_ascii=False, indent=4)

@st.cache_data(ttl=3600)
def fetch_realtime_data(ticker):
    try:
        data = yf.download(ticker, period="5d", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            valid_closes = data['Close'].dropna() 
            if not valid_closes.empty:
                return float(valid_closes.iloc[-1])
    except: return None
    return None

current_rate = fetch_realtime_data("TWD=X") or 32.5
db_data = load_portfolio()

# ==========================================
# 4. 側邊欄：主選單與全局設定
# ==========================================
st.sidebar.title("🎛️ 監控中心設定")
st.sidebar.markdown(f"📈 **美金匯率：** `{current_rate:.2f}`")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "切換功能頁面：", 
    ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控", "🔍 全球 K 線分析"]
)
st.sidebar.markdown("---")

if app_mode == "🔍 全球 K 線分析":
    st.sidebar.header("🌍 大盤速查")
    market_choice = st.sidebar.radio(
        "快速切換 K 線圖：", 
        ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"]
    )
    st.sidebar.markdown("---")

if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    threshold = st.sidebar.slider("⚖️ 再平衡觸發門檻 (%)", 0.0, 10.0, 2.0, 0.5)
    init_funds = st.sidebar.number_input("💵 初始投入總資金 (NTD)", value=int(db_data.get("init_funds", 1000000)), step=10000)
    num_assets = st.sidebar.number_input("🔢 本頁面標的數量", value=len(db_data.get("tw_portfolio" if app_mode == "🇹🇼 台股持股監控" else "us_portfolio", [])) or 3, min_value=1)

# ==========================================
# 5. 主功能：資產動態監控盤 (台美完全獨立)
# ==========================================
if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    is_tw_mode = (app_mode == "🇹🇼 台股持股監控")
    market_label = "台股" if is_tw_mode else "美股"
    current_list_key = "tw_portfolio" if is_tw_mode else "us_portfolio"
    
    st.markdown(f'<h1>🏦 {app_mode.split(" ")[1]}儀表板</h1>', unsafe_allow_html=True)
    
    # 📌 獨立設定區
    with st.expander(f"⚙️ 點擊展開：編輯{market_label}初始配置", expanded=(not db_data[current_list_key])):
        st.info(f"💡 提示：輸入代碼與權重即可，系統會**自動偵測並計算槓桿倍數**。")
        cols = st.columns([3, 3, 6])
        cols[0].markdown("**代碼**"); cols[1].markdown("**目標權重%**")
        
        new_setup = []
        for i in range(int(num_assets)):
            r_cols = st.columns([3, 3, 6])
            hist = db_data[current_list_key][i] if i < len(db_data[current_list_key]) else {"ticker": "", "target_pct": 0}
            
            display_tk = hist["ticker"].replace(".TWO", "").replace(".TW", "") if (".TW" in hist.get("ticker", "") or ".TWO" in hist.get("ticker", "")) else hist.get("ticker", "")
            raw_tk = r_cols[0].text_input(f"tk_{i}", display_tk, label_visibility="collapsed", placeholder="代碼").strip()
            pct = r_cols[1].number_input(f"pct_{i}", 0.0, 100.0, float(hist.get("target_pct", 0)), 5.0, label_visibility="collapsed")
            
            if raw_tk: new_setup.append({"raw_ticker": raw_tk, "target_pct": pct})
        
        if st.button(f"📌 鎖定{market_label}庫存並存檔", type="primary"):
            locked_assets = []
            error_tickers = []
            with st.spinner('正在自動解析代碼並計算初始股數...'):
                for item in new_setup:
                    real_ticker = resolve_ticker(item["raw_ticker"])
                    p = fetch_realtime_data(real_ticker)
                    lev = get_leverage(real_ticker) # 自動取得槓桿倍數
                    
                    if p and p > 0: 
                        is_tw = ".TW" in real_ticker or ".TWO" in real_ticker or real_ticker.startswith("^")
                        alloc_ntd = init_funds * (item["target_pct"] / 100)
                        price_ntd = p if is_tw else (p * current_rate)
                        shares = int(alloc_ntd / price_ntd) if not real_ticker.startswith("^") else 1
                        locked_assets.append({"ticker": real_ticker, "target_pct": item["target_pct"], "leverage": lev, "init_shares": shares, "init_price": p})
                    else:
                        error_tickers.append(item["raw_ticker"])
            
            if error_tickers: st.error(f"⚠️ 無法識別或抓取以下代碼：{', '.join(error_tickers)}。")
            else:
                if is_tw_mode: save_portfolio(init_funds, locked_assets, db_data["us_portfolio"])
                else: save_portfolio(init_funds, db_data["tw_portfolio"], locked_assets)
                st.success(f"🔒 {market_label}庫存定格成功！")
                st.rerun()

    # 📌 監控顯示區
    current_view_data = []
    total_market_val_ntd = 0 
    total_exposure_val_ntd = 0 # 用於計算總槓桿曝險
    
    # 為了全盤總結，必須計算台美股的總和
    all_assets_list = db_data["tw_portfolio"] + db_data["us_portfolio"]
    
    if all_assets_list:
        with st.spinner("🔄 正在獲取全球交易所最新數據..."):
            for asset in all_assets_list:
                now_p = fetch_realtime_data(asset["ticker"])
                if now_p and now_p > 0:
                    is_tw = ".TW" in asset["ticker"] or ".TWO" in asset["ticker"] or asset["ticker"].startswith("^")
                    lev = asset.get("leverage", 1.0)
                    
                    # 計算市值 (不含槓桿的真實本金價值)
                    if asset["ticker"].startswith("^"):
                        now_val_ntd = init_funds * (asset["target_pct"] / 100) * (now_p / asset.get("init_price", now_p))
                    else:
                        price_ntd = now_p if is_tw else (now_p * current_rate)
                        now_val_ntd = price_ntd * asset.get("init_shares", 0)
                    
                    # 計算曝險價值 (含槓桿放大)
                    exposure_ntd = now_val_ntd * lev
                    
                    total_market_val_ntd += now_val_ntd
                    total_exposure_val_ntd += exposure_ntd
                    
                    record = {**asset, "now_p": now_p, "now_val_ntd": now_val_ntd, "exposure_ntd": exposure_ntd, "is_tw": is_tw}
                    if is_tw_mode and is_tw: current_view_data.append(record)
                    elif not is_tw_mode and not is_tw: current_view_data.append(record)

        # 渲染選定的市場面板
        if current_view_data:
            st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">{"🇹🇼 台灣市場" if is_tw_mode else "🇺🇸 美國市場"}監控盤</div>', unsafe_allow_html=True)
                
            for item in current_view_data:
                c = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2.6])
                real_pct = (item["now_val_ntd"] / total_market_val_ntd * 100) if total_market_val_ntd > 0 else 0
                diff = real_pct - item["target_pct"]
                
                clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                c[0].metric(clean_name, f"{'NTD' if item['is_tw'] else 'USD'} {item['now_p']:.2f}")
                c[1].write("📊 指數" if item["ticker"].startswith("^") else f"{item.get('init_shares', 0):,} 股")
                c[2].write(f"目標: {item['target_pct']}%")
                
                c[3].write(f"市值: NTD {int(item['now_val_ntd']):,}")
                
                c[4].write(f"系統偵測: **{item.get('leverage', 1.0)}x**槓桿\n曝險部位: {int(item['exposure_ntd']):,}")
                
                if abs(diff) > threshold: c[5].warning(f"⚠️ 偏離 {diff:+.1f}%\n(真實佔比: {real_pct:.1f}%)")
                else: c[5].success(f"✅ 完美平衡\n(真實佔比: {real_pct:.1f}%)")

        # 📌 底部結算與圖表 (顯示全盤總覽，幫助掌握大局)
        st.markdown("---")
        footer_cols = st.columns([1, 1])
        with footer_cols[0]:
            st.subheader("💰 全球投資組合總結")
            overall_leverage = total_exposure_val_ntd / total_market_val_ntd if total_market_val_ntd > 0 else 1.0
            
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("總市值本金 (NTD)", f"{int(total_market_val_ntd):,}")
            sc2.metric("總曝險市值 (NTD)", f"{int(total_exposure_val_ntd):,}")
            sc3.metric("整體槓桿水位", f"{overall_leverage:.2f} 倍")
            
            if current_view_data:
                pie_df = pd.DataFrame([{"tk": r["ticker"].replace('.TWO','').replace('.TW', ''), "val": r["now_val_ntd"]} for r in current_view_data])
                fig_pie = px.pie(pie_df, values='val', names='tk', hole=0.4, title=f"{market_label}市值分佈", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with footer_cols[1]:
            if current_view_data:
                st.subheader("📊 權重偏差分析")
                bar_df = pd.DataFrame([{"tk": r["ticker"].replace('.TWO','').replace('.TW', ''), "Real": (r["now_val_ntd"]/total_market_val_ntd*100), "Target": r["target_pct"]} for r in current_view_data])
                fig_bar = go.Figure(data=[
                    go.Bar(name='真實權重', x=bar_df['tk'], y=bar_df['Real'], marker_color='#00ffcc'),
                    go.Bar(name='目標權重', x=bar_df['tk'], y=bar_df['Target'], marker_color='#334155')
                ])
                fig_bar.update_layout(barmode='group', height=350, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# 6. 分頁：全球 K 線分析 (重磅加入 MA200)
# ==========================================
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析")
    
    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = "0050"
    
    if market_choice == "自訂輸入個股":
        st.info("💡 支援輸入純數字、字母混合或中文（如: `0050`、`00631L`、`台積電`、`AAPL`）")
        raw_ticker_input = st.text_input("輸入欲分析代碼：", default_ticker)
    else:
        raw_ticker_input = default_ticker
        st.success(f"目前追蹤大盤：**{market_choice}**")
    
    if raw_ticker_input:
        ticker_input = resolve_ticker(raw_ticker_input)
        try:
            with st.spinner("載入圖表與計算均線中..."):
                # 為了計算 200 日均線，必須抓取更長的時間 (以 2 年確保有足夠的 K 棒)
                df_k = yf.download(ticker_input, period="2y", interval="1d", progress=False)
                if not df_k.empty:
                    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
                    
                    # 計算均線
                    df_k['MA5'] = df_k['Close'].rolling(window=5).mean()
                    df_k['MA20'] = df_k['Close'].rolling(window=20).mean()
                    df_k['MA200'] = df_k['Close'].rolling(window=200).mean() # 加入 200日年線
                    
                    clean_title = ticker_input.replace('.TWO', '').replace('.TW', '')
                    st.subheader(f"目前顯示標的：{clean_title}")
                    
                    fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                    
                    # K線與均線
                    fig_k.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="K線"), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA5'], mode='lines', name='MA5 (週線)', line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA20'], mode='lines', name='MA20 (月線)', line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                    fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA200'], mode='lines', name='MA200 (年線)', line=dict(color='#ef4444', width=2)), row=1, col=1) # 紅色年線
                    
                    # 成交量
                    fig_k.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                    
                    # 將 X 軸顯示範圍縮放至最近 6 個月，讓畫面不要太擠，但保有 200 日均線的數值
                    last_6mo = df_k.index.max() - pd.Timedelta(days=180)
                    fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=1, col=1)
                    fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=2, col=1)
                    
                    fig_k.update_layout(xaxis_rangeslider_visible=False, height=650)
                    st.plotly_chart(fig_k, use_container_width=True)
        except:
            st.error("代碼有誤或暫無數據，請嘗試更換輸入名稱。")
