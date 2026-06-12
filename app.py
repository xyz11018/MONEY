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
# 1. 頁面配置與「高對比」視覺優化
# ==========================================
st.set_page_config(layout="wide", page_title="全球資產動態平衡系統", page_icon="🏦")

st.markdown("""
    <style>
    /* 全域文字與卡片高對比設定 */
    .market-header { padding: 15px; border-radius: 8px; font-weight: bold; margin-bottom: 15px; font-size: 1.2rem; color: #ffffff !important; }
    .tw-market { background-color: #1e293b; border-left: 8px solid #00ffcc; }
    .us-market { background-color: #1e293b; border-left: 8px solid #f97316; }
    
    /* 確保輸入框與標籤在淺色/深色模式都能看清楚 */
    label, .stMarkdown p { font-weight: 500; }
    div[data-testid="stMetricValue"] { font-weight: 700 !important; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==========================================
# 2. 智慧代碼解析引擎 (完美支援 00631L、00981A、中文與上櫃股票)
# ==========================================
def resolve_ticker(user_input):
    user_input = user_input.strip()
    if not user_input: return ""
    
    user_input_upper = user_input.upper()
    
    # 規則 1: 如果是大盤指數（以 ^ 開頭），直接大寫回傳
    if user_input_upper.startswith("^"):
        return user_input_upper
        
    # 規則 2: 只要開頭是數字（純數字如 2330、帶字母如 00631L）或是含有中文名稱
    if user_input_upper[0].isdigit() or re.search(r'[\u4e00-\u9fff]', user_input):
        try:
            # 優先透過 Yahoo 搜尋引擎尋找精準代碼 (能自動識別上市 .TW 或上櫃 .TWO)
            search_result = yf.Search(user_input_upper, max_results=1).quotes
            if search_result:
                return search_result[0]['symbol']
        except: pass
        
        # 保底補丁：若 Yahoo 搜尋失效且開頭為數字，且無後綴，則自動補上 .TW
        if user_input_upper[0].isdigit():
            if not (user_input_upper.endswith(".TW") or user_input_upper.endswith(".TWO")):
                return f"{user_input_upper}.TW"
                
    # 規則 3: 純美股代碼（如 AAPL, QQQ, TMF），轉大寫直接回傳
    return user_input_upper

# ==========================================
# 3. 核心功能：存檔機制與安全數據獲取
# ==========================================
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"init_funds": 1000000, "locked_portfolio": []}

def save_portfolio(funds, assets):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"init_funds": funds, "locked_portfolio": assets}, f, ensure_ascii=False, indent=4)

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

# 獲取當前匯率
current_rate = fetch_realtime_data("TWD=X") or 32.5
data = load_portfolio()

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

# 當處於 K 線分析時，動態顯示大盤快選單
if app_mode == "🔍 全球 K 線分析":
    st.sidebar.header("🌍 大盤速查")
    market_choice = st.sidebar.radio(
        "快速切換 K 線圖：", 
        ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"]
    )
    st.sidebar.markdown("---")

if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    threshold = st.sidebar.slider("⚖️ 再平衡觸發門檻 (%)", 0.0, 10.0, 2.0, 0.5)
    init_funds = st.sidebar.number_input("💵 初始投入總資金 (NTD)", value=int(data.get("init_funds", 1000000)), step=10000)
    num_assets = st.sidebar.number_input("🔢 全球設定標的數量", value=len(data.get("locked_portfolio", [])) or 4, min_value=1)

# ==========================================
# 5. 主功能：資產動態監控盤
# ==========================================
if app_mode in ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控"]:
    st.markdown(f'<h1>🏦 {app_mode.split(" ")[1]}儀表板</h1>', unsafe_allow_html=True)
    
    # 📌 設定區
    with st.expander("⚙️ 點擊展開：編輯全部初始配置與槓桿鎖定 (台美股皆在此編輯)", expanded=(not data["locked_portfolio"])):
        st.info("💡 智慧輸入提示：台股可直接輸入 `00631L`、`2330` 或 `元大台灣50正2`。系統會自動精準識別上市櫃字尾！")
        cols = st.columns([2, 1.5, 1, 5])
        cols[0].markdown("**代碼 (免加字尾)**"); cols[1].markdown("**目標權重%**"); cols[2].markdown("**槓桿**")
        
        new_setup = []
        total_pct = 0
        for i in range(int(num_assets)):
            r_cols = st.columns([2, 1.5, 1, 5])
            hist = data["locked_portfolio"][i] if i < len(data["locked_portfolio"]) else {"ticker": "", "target_pct": 0, "leverage": 1}
            
            # 潔淨化顯示名稱
            display_tk = hist["ticker"].replace(".TWO", "").replace(".TW", "") if (".TW" in hist.get("ticker", "") or ".TWO" in hist.get("ticker", "")) else hist.get("ticker", "")
            raw_tk = r_cols[0].text_input(f"tk_{i}", display_tk, label_visibility="collapsed", placeholder="例如: 00631L, 2330, QQQ").strip()
            pct = r_cols[1].number_input(f"pct_{i}", 0.0, 100.0, float(hist.get("target_pct", 0)), 5.0, label_visibility="collapsed")
            lev = r_cols[2].number_input(f"lev_{i}", 0.5, 5.0, float(hist.get("leverage", 1.0)), 0.5, label_visibility="collapsed")
            
            total_pct += pct
            if raw_tk: new_setup.append({"raw_ticker": raw_tk, "target_pct": pct, "leverage": lev})
        
        if st.button("📌 鎖定初始庫存並存檔", type="primary"):
            if total_pct != 100:
                st.error(f"目前總權重為 {total_pct}%，請調整至 100% 後再鎖定。")
            else:
                locked_assets = []
                error_tickers = []
                with st.spinner('正在智慧辨識跨國市場代碼並計算股數...'):
                    for item in new_setup:
                        real_ticker = resolve_ticker(item["raw_ticker"])
                        p = fetch_realtime_data(real_ticker)
                        
                        if p and p > 0: 
                            is_tw = ".TW" in real_ticker or ".TWO" in real_ticker or real_ticker.startswith("^")
                            alloc_ntd = init_funds * (item["target_pct"] / 100)
                            price_ntd = p if is_tw else (p * current_rate)
                            
                            shares = int(alloc_ntd / price_ntd) if not real_ticker.startswith("^") else 1
                            locked_assets.append({"ticker": real_ticker, "target_pct": item["target_pct"], "leverage": item["leverage"], "init_shares": shares, "init_price": p})
                        else:
                            error_tickers.append(item["raw_ticker"])
                
                if error_tickers: st.error(f"⚠️ 無法識別或抓取以下代碼：{', '.join(error_tickers)}。請確認名稱。")
                else:
                    save_portfolio(init_funds, locked_assets)
                    st.success("🔒 跨市場初始庫存定格成功！")
                    st.rerun()

    # 📌 監控顯示區
    if data["locked_portfolio"]:
        current_view_data = []
        total_market_val_ntd = 0 
        
        with st.spinner("🔄 正在獲取全球交易所最新數據..."):
            for asset in data["locked_portfolio"]:
                now_p = fetch_realtime_data(asset["ticker"])
                if now_p and now_p > 0:
                    is_tw = ".TW" in asset["ticker"] or ".TWO" in asset["ticker"] or asset["ticker"].startswith("^")
                    
                    if asset["ticker"].startswith("^"):
                        ret = now_p / asset.get("init_price", now_p)
                        now_val_ntd = init_funds * (asset["target_pct"] / 100) * ret
                    else:
                        price_ntd = now_p if is_tw else (now_p * current_rate)
                        now_val_ntd = price_ntd * asset.get("init_shares", 0)
                    
                    total_market_val_ntd += now_val_ntd
                    record = {**asset, "now_p": now_p, "now_val_ntd": now_val_ntd, "is_tw": is_tw}
                    
                    if app_mode == "🇹🇼 台股持股監控" and is_tw: current_view_data.append(record)
                    elif app_mode == "🇺🇸 美股持股監控" and not is_tw: current_view_data.append(record)

        if current_view_data:
            if app_mode == "🇹🇼 台股持股監控":
                st.markdown('<div class="market-header tw-market">🇹🇼 台灣市場監控盤 (TWD)</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="market-header us-market">🇺🇸 美國市場監控盤 (USD / 台幣結算)</div>', unsafe_allow_html=True)
                
            for item in current_view_data:
                c = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2.6])
                real_pct = (item["now_val_ntd"] / total_market_val_ntd * 100) if total_market_val_ntd > 0 else 0
                diff = real_pct - item["target_pct"]
                
                clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                c[0].metric(clean_name, f"{'NTD' if item['is_tw'] else 'USD'} {item['now_p']:.2f}")
                c[1].write("📊 指數" if item["ticker"].startswith("^") else f"{item.get('init_shares', 0):,} 股")
                c[2].write(f"{item['target_pct']}% (`{item.get('leverage', 1.0)}x`)")
                
                if item['is_tw']: c[3].write(f"NTD {int(item['now_val_ntd']):,}")
                else: c[3].write(f"市值: NTD {int(item['now_val_ntd']):,}\n(匯率:{current_rate:.2f})")
                
                c[4].write(f"`真實佔比: {real_pct:.1f}%` \n(偏離: {diff:+.1f}%)")
                if abs(diff) > threshold: c[5].warning(f"⚠️ 偏離 {diff:+.1f}%")
                else: c[5].success("✅ 完美平衡")

        # 📌 底部結算與圖表
        st.markdown("---")
        footer_cols = st.columns([1, 1])
        with footer_cols[0]:
            st.subheader("💰 全球投資組合總結")
            st.metric("總市值 (NTD)", f"{int(total_market_val_ntd):,}", f"{int(total_market_val_ntd - init_funds):,} 自初始定格")
            
            all_assets = []
            for a in data["locked_portfolio"]:
                p = fetch_realtime_data(a["ticker"])
                if p and p > 0:
                    is_tw = ".TW" in a["ticker"] or ".TWO" in a["ticker"] or a["ticker"].startswith("^")
                    if a["ticker"].startswith("^"): val = init_funds * (a["target_pct"] / 100) * (p / a.get("init_price", p))
                    else: val = (p if is_tw else p * current_rate) * a.get("init_shares", 0)
                    all_assets.append({"tk": a["ticker"].replace('.TWO','').replace('.TW', ''), "val": val, "target": a["target_pct"]})

            if all_assets:
                pie_df = pd.DataFrame(all_assets)
                fig_pie = px.pie(pie_df, values='val', names='tk', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with footer_cols[1]:
            if all_assets:
                st.subheader("📊 全球權重偏差分析")
                bar_df = pd.DataFrame(all_assets)
                bar_df['Real'] = bar_df['val'] / bar_df['val'].sum() * 100
                fig_bar = go.Figure(data=[
                    go.Bar(name='真實權重', x=bar_df['tk'], y=bar_df['Real'], marker_color='#00ffcc'),
                    go.Bar(name='目標權重', x=bar_df['tk'], y=bar_df['target'], marker_color='#334155')
                ])
                fig_bar.update_layout(barmode='group', height=350)
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("請展開上方設定區，輸入股票代碼與比例並完成鎖定。")

# ==========================================
# 6. 分頁：全球 K 線分析
# ==========================================
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析")
    
    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = "2330"
    
    if market_choice == "自訂輸入個股":
        st.info("💡 支援純數字、字母混合或中文（如: `00631L`、`元大台灣50正2`、`AAPL`）")
        raw_ticker_input = st.text_input("輸入欲分析代碼：", default_ticker)
    else:
        raw_ticker_input = default_ticker
        st.success(f"目前追蹤大盤：**{market_choice}**")
    
    if raw_ticker_input:
        ticker_input = resolve_ticker(raw_ticker_input)
        try:
            with st.spinner("載入圖表中..."):
                df_k = yf.download(ticker_input, period="6mo", interval="1d", progress=False)
                if not df_k.empty:
                    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
                    
                    clean_title = ticker_input.replace('.TWO', '').replace('.TW', '')
                    st.subheader(f"目前顯示標的：{clean_title}")
                    fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                    fig_k.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="K線"), row=1, col=1)
                    fig_k.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                    fig_k.update_layout(xaxis_rangeslider_visible=False, height=600)
                    st.plotly_chart(fig_k, use_container_width=True)
        except:
            st.error("代碼有誤或暫無數據，請嘗試更換輸入名稱。")
