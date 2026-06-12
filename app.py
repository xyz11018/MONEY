import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import datetime
import pandas as pd
import json
import os

# 1. 網頁全寬配置與深色模式美化
st.set_page_config(layout="wide", page_title="全球資產再平衡系統", page_icon="📈")

# 自訂 CSS 區隔台美股視覺卡片
st.markdown("""
    <style>
    .market-header { padding: 10px 15px; border-radius: 8px; font-weight: bold; margin-bottom: 12px; margin-top: 10px; font-size: 1.1em;}
    .tw-market { background-color: #0f172a; border-left: 6px solid #00ffcc; color: #00ffcc; }
    .us-market { background-color: #0f172a; border-left: 6px solid #ff9900; color: #ff9900; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# ==================== 核心功能：永久存檔與讀檔機制 ====================
def save_portfolio_to_local(funds, assets):
    data = {"init_funds": funds, "locked_portfolio": assets}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_portfolio_from_local():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return None
    return None

local_data = load_portfolio_from_local()

# ==================== 核心功能：自動獲取最新台美匯率 ====================
@st.cache_data(ttl=3600)
def get_usd_twd_rate():
    try:
        usd_twd = yf.download("TWD=X", period="2d", progress=False)
        if not usd_twd.empty:
            if isinstance(usd_twd.columns, pd.MultiIndex):
                usd_twd.columns = usd_twd.columns.get_level_values(0)
            return float(usd_twd['Close'].iloc[-1])
    except: pass
    return 32.5

current_usdtwd_rate = get_usd_twd_rate()

# ==================== 側邊欄：功能選單 ====================
st.sidebar.title("🎛️ 操盤控制台")
app_mode = st.sidebar.radio(
    "請選擇您目前要操作的功能：",
    ["📊 初始定格與每日波動再平衡盤", "🔍 全球 K 線技術分析"]
)
st.sidebar.markdown("---")

# 初始化 Session State
if "locked_portfolio" not in st.session_state:
    st.session_state.locked_portfolio = local_data["locked_portfolio"] if local_data else None
if "init_funds" not in st.session_state:
    st.session_state.init_funds = local_data["init_funds"] if local_data else 100000
if "num_assets" not in st.session_state:
    st.session_state.num_assets = len(st.session_state.locked_portfolio) if st.session_state.locked_portfolio else 3

# ====================================================================
# 🎯 分頁一：初始定格與每日波動再平衡盤
# ====================================================================
if app_mode == "📊 初始定格與每日波動再平衡盤":
    st.title("📊 全球資產初始定格與每日波動監控系統")
    
    # 側邊欄控制
    st.sidebar.header("⚙️ 初始投入設定")
    st.sidebar.markdown(f"💱 **當前美金兌台幣匯率：** `{current_usdtwd_rate:.2f}`")
    threshold = st.sidebar.slider("⚖️ 再平衡觸發閾值 (%)", 0.0, 10.0, 2.0, 0.5)
    
    init_funds = st.sidebar.number_input("💵 初始總投入資金 (NTD)：", min_value=0, value=int(st.session_state.init_funds), step=10000)
    num_assets = st.sidebar.number_input("🔢 我的資產標的數量：", min_value=1, max_value=10, value=int(st.session_state.num_assets), step=1)
    
    st.session_state.init_funds = init_funds
    st.session_state.num_assets = num_assets

    # 第一步：設定區
    st.subheader("第一步：設定並鎖定您的初始資產配置")
    with st.expander("📌 點此展開設定初始庫存", expanded=(st.session_state.locked_portfolio is None)):
        input_cols = st.columns([2, 2, 2, 6])
        input_cols[0].markdown("**✍️ 股票/指數代碼**")
        input_cols[1].markdown("**🎯 目標權重 (%)**")
        input_cols[2].markdown("**⚡ 槓桿倍數**")
        
        setup_data = []
        total_setup_pct = 0.0
        
        for i in range(int(num_assets)):
            row_cols = st.columns([2, 2, 2, 6])
            d_tk, d_pct, d_lev = "", 0.0, 1.0
            if st.session_state.locked_portfolio and i < len(st.session_state.locked_portfolio):
                d_tk = st.session_state.locked_portfolio[i]["ticker"]
                d_pct = st.session_state.locked_portfolio[i]["target_pct"]
                d_lev = st.session_state.locked_portfolio[i].get("leverage", 1.0)
                
            tk = row_cols[0].text_input(f"代碼 #{i+1}", value=d_tk, key=f"tk_{i}", label_visibility="collapsed").strip()
            pct = row_cols[1].number_input(f"權重 #{i+1}", min_value=0.0, max_value=100.0, value=d_pct, step=5.0, key=f"pct_{i}", label_visibility="collapsed")
            lev = row_cols[2].number_input(f"槓桿 #{i+1}", value=float(d_lev), step=0.5, key=f"lev_{i}", label_visibility="collapsed")
            
            total_setup_pct += pct
            if tk != "":
                setup_data.append({"ticker": tk, "target_pct": pct, "leverage": lev})
                
        btn_col1, btn_col2 = st.columns([2, 10])
        with btn_col1:
            lock_btn = st.button("📌 鎖定初始投入庫存", type="primary", use_container_width=True)
        with btn_col2:
            if total_setup_pct != 100.0: st.warning(f"⚠️ 權重加總為 `{total_setup_pct}%`，請調整至 100%。")
            else: st.success("🎉 權重剛好 100%，可點擊鎖定！")

        if lock_btn and total_setup_pct == 100.0:
            locked_list = []
            with st.spinner('正在定格初始股數並存檔...'):
                for item in setup_data:
                    tk = item["ticker"]
                    try:
                        stock_info = yf.download(tk, period="5d", progress=False)
                        if not stock_info.empty:
                            if isinstance(stock_info.columns, pd.MultiIndex):
                                stock_info.columns = stock_info.columns.get_level_values(0)
                            init_price = float(stock_info['Close'].iloc[-1])
                            allocated_ntd = init_funds * (item["target_pct"] / 100.0)
                            
                            is_tw = ".TW" in tk or tk.startswith("^")
                            if is_tw: init_shares = 1 if tk.startswith("^") else int(allocated_ntd / init_price)
                            else: init_shares = int(allocated_ntd / (init_price * current_usdtwd_rate))
                                
                            locked_list.append({"ticker": tk, "target_pct": item["target_pct"], "leverage": item["leverage"], "init_shares": init_shares, "init_price": init_price})
                    except Exception as e:
                        st.error(f"代碼 {tk} 失敗: {str(e)}")
            
            st.session_state.locked_portfolio = locked_list
            save_portfolio_to_local(init_funds, locked_list)
            st.rerun()

    # 第二步：監控盤
    st.markdown("---")
    st.subheader("第二步：台美股市場即時監控盤")
    
    if st.session_state.locked_portfolio:
        tw_portfolio, us_portfolio = [], []
        today_total_market_value_ntd = 0.0
        
        with st.spinner('同步全球最新價格中...'):
            for s_item in st.session_state.locked_portfolio:
                tk = s_item["ticker"]
                try:
                    stock_info = yf.download(tk, period="5d", progress=False)
                    if not stock_info.empty:
                        if isinstance(stock_info.columns, pd.MultiIndex): stock_info.columns = stock_info.columns.get_level_values(0)
                        today_price = float(stock_info['Close'].iloc[-1])
                        
                        is_tw = ".TW" in tk or tk.startswith("^")
                        today_price_in_ntd = today_price if is_tw else (today_price * current_usdtwd_rate)
                        
                        if tk.startswith("^"):
                            init_p = s_item.get("init_price", today_price)
                            val_ntd = init_funds * (s_item["target_pct"] / 100.0) * (today_price / init_p if init_p > 0 else 1.0)
                        else:
                            val_ntd = today_price_in_ntd * s_item["init_shares"]
                            
                        today_total_market_value_ntd += val_ntd
                        
                        asset_data = {**s_item, "today_price": today_price, "today_price_in_ntd": today_price_in_ntd, "val_ntd": val_ntd, "is_tw": is_tw}
                        if is_tw: tw_portfolio.append(asset_data)
                        else: us_portfolio.append(asset_data)
                except: pass

        plot_data = []

        # 渲染台灣市場
        if tw_portfolio:
            st.markdown('<div class="market-header tw-market">🇹🇼 台灣股市與大盤指數 (TWD)</div>', unsafe_allow_html=True)
            for res in tw_portfolio:
                cols = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2, 2.6])
                real_pct = (res["val_ntd"] / today_total_market_value_ntd * 100) if today_total_market_value_ntd > 0 else 0
                diff = real_pct - res["target_pct"]
                plot_data.append({"股票代碼": res["ticker"], "今日真實權重 (%)": round(real_pct, 2), "目標理想權重 (%)": res["target_pct"], "今日市值": res["val_ntd"]})
                
                cols[0].write(f"**{res['ticker']}**")
                cols[1].write("📊 指數" if res["ticker"].startswith("^") else f"{res['init_shares']:,} 股")
                cols[2].write(f"{res['target_pct']}% (`{res['leverage']}x`)")
                cols[3].write(f"NTD {res['today_price']:.2f}")
                cols[4].write(f"NTD {int(res['val_ntd']):,}")
                cols[5].write(f"`{real_pct:.2f}%` \n(偏離: {diff:+.2f}%)")
                if abs(diff) > threshold: cols[6].warning(f"⚠️ 偏離 {diff:+.1f}% 需調整")
                else: cols[6].success("✅ 完美平衡")

        # 渲染美國市場
        if us_portfolio:
            st.markdown('<div class="market-header us-market">🇺🇸 美國股市與全球大盤 (USD / 換算台幣)</div>', unsafe_allow_html=True)
            for res in us_portfolio:
                cols = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2, 2.6])
                real_pct = (res["val_ntd"] / today_total_market_value_ntd * 100) if today_total_market_value_ntd > 0 else 0
                diff = real_pct - res["target_pct"]
                plot_data.append({"股票代碼": res["ticker"], "今日真實權重 (%)": round(real_pct, 1), "目標理想權重 (%)": res["target_pct"], "今日市值": res["val_ntd"]})
                
                cols[0].write(f"**{res['ticker']}**")
                cols[1].write("📊 指數" if res["ticker"].startswith("^") else f"{res['init_shares']:,} 股")
                cols[2].write(f"{res['target_pct']}% (`{res['leverage']}x`)")
                cols[3].write(f"USD {res['today_price']:.1f}\n(台幣:{res['today_price_in_ntd']:.1f})")
                cols[4].write(f"NTD {res['val_ntd']:.1f}")
                cols[5].write(f"`{real_pct:.1f}%` \n(偏離: {diff:+.1f}%)")
                if abs(diff) > threshold: cols[6].warning(f"⚠️ 偏離 {diff:+.1f}% 需調整")
                else: cols[6].success("✅ 完美平衡")

        # 繪圖區
        if plot_data:
            st.markdown("---")
            c1, c2 = st.columns([1, 1])
            df_plot = pd.DataFrame(plot_data)
            
            with c1:
                st.subheader(f"💼 總資產：NTD {int(today_total_market_value_ntd):,}")
                growth = ((today_total_market_value_ntd - init_funds) / init_funds * 100) if init_funds > 0 else 0
                st.metric("累積總投報率", f"{growth:.2f} %", f"{int(today_total_market_value_ntd - init_funds):,} NTD")
                fig_pie = px.pie(df_plot, values='今日市值', names='股票代碼', hole=0.4, template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with c2:
                st.subheader("📊 權重偏離對比")
                fig_bar = go.Figure(data=[
                    go.Bar(name='今日真實權重 (%)', x=df_plot['股票代碼'], y=df_plot['今日真實權重 (%)'], marker_color='#00ffcc'),
                    go.Bar(name='初始目標權重 (%)', x=df_plot['股票代碼'], y=df_plot['目標理想權重 (%)'], marker_color='#ff9900')
                ])
                fig_bar.update_layout(barmode='group', template="plotly_dark", height=380, margin=dict(t=30, b=20, l=20, r=20))
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("💡 請先設定代碼並點擊「鎖定初始投入庫存」。")

# ====================================================================
# 🎯 分頁二：全球 K 線技術分析
# ====================================================================
elif app_mode == "🔍 全球 K 線技術分析":
    st.title("🔍 全球個股與大盤技術分析")
    st.sidebar.header("🌍 全球大盤速查")
    market_choice = st.sidebar.radio("快速切換大盤 K 線圖：", ["自訂輸入個股", "台灣加權指數 (台股)", "那斯達克 (美股科技)", "標普 500 (美股大盤)", "費城半導體"])
    
    if market_choice == "台灣加權指數 (台股)": default_ticker = "^TWII"
    elif market_choice == "那斯達克 (美股科技)": default_ticker = "^IXIC"
    elif market_choice == "標普 500 (美股大盤)": default_ticker = "^GSPC"
    elif market_choice == "費城半導體": default_ticker = "^SOX"
    else: default_ticker = "2330.TW"
        
    ticker = st.text_input("請輸入想看圖的股票或大盤代碼：", default_ticker)
    start_date = "2025-01-01"
    today_date = datetime.date.today()
    
    try:
        chart_data = yf.download(ticker, start=start_date, end=today_date, progress=False)
        if not chart_data.empty:
            if isinstance(chart_data.columns, pd.MultiIndex):
                chart_data.columns = chart_data.columns.get_level_values(0)
            chart_data['MA5'] = chart_data['Close'].rolling(window=5).mean()
            chart_data['MA20'] = chart_data['Close'].rolling(window=20).mean()
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="K線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA5'], mode='lines', name='MA5 (週線)', line=dict(color='#ff9900', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA20'], mode='lines', name='MA20 (月線)', line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
            fig.add_trace(go.Bar(x=chart_data.index, y=chart_data['Volume'], name='成交量', marker=dict(color='#666666')), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=550, margin=dict(t=20, b=20, l=20, r=20))
            fig.update_xaxes(type='date', autorange=True)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"圖表載入失敗: {str(e)}")
