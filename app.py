import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import datetime
import pandas as pd
import json
import os

# --- 1. 頁面全寬配置與深色模式視覺優化 ---
st.set_page_config(layout="wide", page_title="全球資產動態平衡系統", page_icon="🏦")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 700; margin-bottom: 20px; color: #f8fafc; }
    .market-header { padding: 15px; border-radius: 10px; font-weight: bold; margin-bottom: 15px; font-size: 1.2rem; }
    .tw-market { background-color: #0f172a; border-left: 8px solid #00ffcc; color: #00ffcc; }
    .us-market { background-color: #0f172a; border-left: 8px solid #f97316; color: #f97316; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# --- 2. 核心功能：存檔機制與資料處理 ---
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
        # 抓取5天數據避免遇到長假
        data = yf.download(ticker, period="5d", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            # 終極防呆：過濾掉所有的 NaN 空值，確保取到的是真實數字
            valid_closes = data['Close'].dropna()
            if not valid_closes.empty:
                return float(valid_closes.iloc[-1])
    except: return None
    return None

# 獲取當前匯率
current_rate = fetch_realtime_data("TWD=X") or 32.5
data = load_portfolio()

# --- 3. 側邊欄控制台 ---
st.sidebar.title("🎛️ 監控中心設定")
st.sidebar.markdown(f"📈 **美金匯率：** `{current_rate:.2f}`")
app_mode = st.sidebar.radio("切換功能頁面：", ["📊 資產動態監控盤", "🔍 全球 K 線分析"])
st.sidebar.markdown("---")

threshold = st.sidebar.slider("⚖️ 再平衡觸發門檻 (%)", 0.0, 10.0, 2.0, 0.5, help="偏離超過此百分比時會標記提醒")
init_funds = st.sidebar.number_input("💵 初始投入總資金 (NTD)", value=int(data.get("init_funds", 1000000)), step=10000)
num_assets = st.sidebar.number_input("🔢 設定標的數量", value=len(data.get("locked_portfolio", [])) or 3, min_value=1)

# --- 4. 主功能：資產動態監控盤 ---
if app_mode == "📊 資產動態監控盤":
    st.markdown('<div class="main-title">🏦 全球資產動態再平衡儀表板</div>', unsafe_allow_html=True)
    
    # 設定區
    with st.expander("⚙️ 調整初始配置與槓桿鎖定", expanded=(not data["locked_portfolio"])):
        cols = st.columns([2, 1.5, 1, 5])
        cols[0].markdown("**代碼**"); cols[1].markdown("**目標權重%**"); cols[2].markdown("**槓桿**")
        
        new_setup = []
        total_pct = 0
        for i in range(int(num_assets)):
            r_cols = st.columns([2, 1.5, 1, 5])
            hist = data["locked_portfolio"][i] if i < len(data["locked_portfolio"]) else {"ticker": "", "target_pct": 0, "leverage": 1}
            
            tk = r_cols[0].text_input(f"tk_{i}", hist["ticker"], label_visibility="collapsed", placeholder="2330.TW / QQQ").strip()
            pct = r_cols[1].number_input(f"pct_{i}", 0.0, 100.0, float(hist["target_pct"]), 5.0, label_visibility="collapsed")
            lev = r_cols[2].number_input(f"lev_{i}", 0.5, 5.0, float(hist.get("leverage", 1.0)), 0.5, label_visibility="collapsed")
            
            total_pct += pct
            if tk: new_setup.append({"ticker": tk, "target_pct": pct, "leverage": lev})
        
        if st.button("📌 鎖定初始庫存並存檔", type="primary"):
            if total_pct != 100:
                st.error(f"目前總權重為 {total_pct}%，請調整至 100% 後再鎖定。")
            else:
                locked_assets = []
                error_tickers = []
                with st.spinner('正在鎖定全球資產股數，請稍候...'):
                    for item in new_setup:
                        p = fetch_realtime_data(item["ticker"])
                        # 第二層防呆：確定抓到的價格不僅存在，而且大於 0
                        if p and p > 0: 
                            is_tw = ".TW" in item["ticker"] or item["ticker"].startswith("^")
                            alloc_ntd = init_funds * (item["target_pct"] / 100)
                            price_ntd = p if is_tw else (p * current_rate)
                            
                            shares = int(alloc_ntd / price_ntd) if not item["ticker"].startswith("^") else 1
                            locked_assets.append({**item, "init_shares": shares, "init_price": p})
                        else:
                            error_tickers.append(item["ticker"])
                
                # 如果有抓不到價格的無效代碼，提示使用者，避免整盤崩潰
                if error_tickers:
                    st.error(f"⚠️ 無法成功抓取以下代碼的價格：{', '.join(error_tickers)}。鎖定失敗，請確認代碼是否輸入正確 (例如：台股需加上 .TW)。")
                else:
                    save_portfolio(init_funds, locked_assets)
                    st.success("🔒 初始庫存定格成功！資料已儲存至雲端。")
                    st.rerun()

    # 監控顯示區
    if data["locked_portfolio"]:
        tw_view, us_view = [], []
        total_market_val_ntd = 0
        
        with st.spinner("🔄 正在從全球交易所獲取最新數據..."):
            for asset in data["locked_portfolio"]:
                now_p = fetch_realtime_data(asset["ticker"])
                if now_p and now_p > 0:
                    is_tw = ".TW" in asset["ticker"] or asset["ticker"].startswith("^")
                    
                    # 計算市值
                    if asset["ticker"].startswith("^"): # 大盤指數模式
                        ret = now_p / asset.get("init_price", now_p)
                        now_val_ntd = init_funds * (asset["target_pct"] / 100) * ret
                    else: # 一般個股模式
                        price_ntd = now_p if is_tw else (now_p * current_rate)
                        now_val_ntd = price_ntd * asset.get("init_shares", 0)
                    
                    total_market_val_ntd += now_val_ntd
                    record = {**asset, "now_p": now_p, "now_val_ntd": now_val_ntd, "is_tw": is_tw}
                    if is_tw: tw_view.append(record)
                    else: us_view.append(record)

        # 1. 台灣市場面板
        if tw_view:
            st.markdown('<div class="market-header tw-market">🇹🇼 台灣市場監控盤 (TWD)</div>', unsafe_allow_html=True)
            for item in tw_view:
                c = st.columns([1.5, 1.5, 1.5, 1.5, 2, 2])
                real_pct = (item["now_val_ntd"] / total_market_val_ntd * 100) if total_market_val_ntd > 0 else 0
                diff = real_pct - item["target_pct"]
                
                c[0].metric(item["ticker"], f"NTD {item['now_p']:.2f}")
                c[1].write(f"持有: {item.get('init_shares', 0):,} 股" if not item["ticker"].startswith("^") else "大盤追蹤")
                c[2].write(f"目標: {item['target_pct']}%")
                c[3].write(f"槓桿: {item.get('leverage', 1.0)}x")
                c[4].write(f"當前市值: **{int(item['now_val_ntd']):,}**")
                
                if abs(diff) > threshold:
                    c[5].warning(f"⚠️ 偏離 {diff:+.1f}%")
                else:
                    c[5].success(f"✅ 平衡 ({real_pct:.1f}%)")

        # 2. 美國市場面板
        if us_view:
            st.markdown('<div class="market-header us-market">🇺🇸 美國市場監控盤 (USD / 台幣結算)</div>', unsafe_allow_html=True)
            for item in us_view:
                c = st.columns([1.5, 1.5, 1.5, 1.5, 2, 2])
                real_pct = (item["now_val_ntd"] / total_market_val_ntd * 100) if total_market_val_ntd > 0 else 0
                diff = real_pct - item["target_pct"]
                
                c[0].metric(item["ticker"], f"USD {item['now_p']:.1f}")
                c[1].write(f"持有: {item.get('init_shares', 0):,} 股" if not item["ticker"].startswith("^") else "大盤追蹤")
                c[2].write(f"目標: {item['target_pct']}%")
                c[3].write(f"槓桿: {item.get('leverage', 1.0)}x")
                c[4].write(f"市值: **NTD {int(item['now_val_ntd']):,}**")
                
                if abs(diff) > threshold:
                    c[5].warning(f"⚠️ 偏離 {diff:+.1f}%")
                else:
                    c[5].success(f"✅ 平衡 ({real_pct:.1f}%)")

        # 3. 底部結算與圖表
        if tw_view or us_view:
            st.markdown("---")
            footer_cols = st.columns([1, 1])
            with footer_cols[0]:
                st.subheader("💰 投資組合總結")
                st.metric("總市值 (NTD)", f"{int(total_market_val_ntd):,}", f"{int(total_market_val_ntd - init_funds):,} 自初始定格")
                
                pie_df = pd.DataFrame([{"tk": r["ticker"], "val": r["now_val_ntd"]} for r in (tw_view + us_view)])
                fig_pie = px.pie(pie_df, values='val', names='tk', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel, template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with footer_cols[1]:
                st.subheader("📊 權重偏差分析")
                bar_df = pd.DataFrame([{"tk": r["ticker"], "Real": (r["now_val_ntd"]/total_market_val_ntd*100), "Target": r["target_pct"]} for r in (tw_view + us_view)])
                fig_bar = go.Figure(data=[
                    go.Bar(name='真實權重', x=bar_df['tk'], y=bar_df['Real'], marker_color='#00ffcc'),
                    go.Bar(name='目標權重', x=bar_df['tk'], y=bar_df['Target'], marker_color='#334155')
                ])
                fig_bar.update_layout(barmode='group', template="plotly_dark", height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("請展開上方設定區，輸入股票代碼與比例並完成鎖定。")

# --- 5. 分頁：全球 K 線分析 ---
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析")
    ticker_input = st.text_input("輸入欲分析代碼 (如 2330.TW, TSLA, ^TWII)：", "^TWII")
    
    if ticker_input:
        try:
            df_k = yf.download(ticker_input, period="6mo", interval="1d", progress=False)
            if not df_k.empty:
                if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
                
                fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                fig_k.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="K線"), row=1, col=1)
                fig_k.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                fig_k.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600)
                st.plotly_chart(fig_k, use_container_width=True)
        except:
            st.error("代碼有誤或暫無數據。")
