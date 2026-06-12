import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import datetime
import pandas as pd
import json
import os

# 1. 網頁全寬配置
st.set_page_config(layout="wide")

# 定義本機存檔的路徑名稱
DB_FILE = "portfolio_db.json"

# ==================== 核心功能：永久存檔與讀檔機制 ====================
def save_portfolio_to_local(funds, assets):
    """將設定與鎖定的庫存永久存入本機檔案"""
    data = {
        "init_funds": funds,
        "locked_portfolio": assets
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_portfolio_from_local():
    """從本機檔案讀取過往鎖定的資料"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

# 初始化時，先嘗試從本機檔案撈取歷史紀錄
local_data = load_portfolio_from_local()
# ====================================================================

# ==================== 核心功能：自動獲取最新台美匯率 ====================
@st.cache_data(ttl=3600)
def get_usd_twd_rate():
    try:
        usd_twd = yf.download("TWD=X", period="2d")
        if not usd_twd.empty:
            if isinstance(usd_twd.columns, pd.MultiIndex):
                usd_twd.columns = usd_twd.columns.get_level_values(0)
            return float(usd_twd['Close'].iloc[-1])
    except:
        pass
    return 32.5

current_usdtwd_rate = get_usd_twd_rate()
# ====================================================================

# 左側側邊欄
st.sidebar.title("功能選單")
app_mode = st.sidebar.radio(
    "請選擇您目前要操作的功能：",
    ["📊 初始定格與每日波動再平衡盤", "🔍 全球 K 線技術分析"]
)
st.sidebar.markdown("---")

if app_mode == "📊 初始定格與每日波動再平衡盤":
    st.title("📊 全球資產初始定格與每日波動監控系統")
    st.markdown("此系統會**鎖定並永久保存**您初始投入時的配置。隨著每日股市波動，即使按 F5 重新整理，資料也不會消失。")
    
    st.sidebar.header("⚙️ 初始投入設定")
    st.sidebar.markdown(f"💱 **當前美金兌台幣匯率：** `{current_usdtwd_rate:.2f}`")
    
    # 透過記憶體與本機檔案雙重初始化
    if "locked_portfolio" not in st.session_state:
        st.session_state.locked_portfolio = local_data["locked_portfolio"] if local_data else None
    if "init_funds" not in st.session_state:
        st.session_state.init_funds = local_data["init_funds"] if local_data else 100000
    if "num_assets" not in st.session_state:
        st.session_state.num_assets = len(st.session_state.locked_portfolio) if st.session_state.locked_portfolio else 3

    # 設定初始資金與標的數量
    init_funds = st.sidebar.number_input("💵 初始總投入資金 (NTD)：", min_value=0, value=int(st.session_state.init_funds), step=10000)
    num_assets = st.sidebar.number_input("🔢 我的資產標的數量：", min_value=1, max_value=10, value=int(st.session_state.num_assets), step=1)
    
    st.session_state.init_funds = init_funds
    st.session_state.num_assets = num_assets

    st.subheader("第一步：設定並鎖定您的初始資產配置（鎖定後會永久保存）")
    
    input_cols = st.columns([2, 2, 8])
    input_cols[0].markdown("**✍️ 股票代碼**")
    input_cols[1].markdown("**🎯 初始目標權重 (%)**")
    
    setup_data = []
    total_setup_pct = 0.0
    
    for i in range(int(num_assets)):
        row_cols = st.columns([2, 2, 8])
        
        # 如果本機有歷史檔案，預設欄位帶出歷史紀錄，方便查看與修改
        d_tk, d_pct = "", 0.0
        if st.session_state.locked_portfolio and i < len(st.session_state.locked_portfolio):
            d_tk = st.session_state.locked_portfolio[i]["ticker"]
            d_pct = st.session_state.locked_portfolio[i]["target_pct"]
        else:
            if i == 0: d_tk, d_pct = "2330.TW", 40.0
            elif i == 1: d_tk, d_pct = "2317.TW", 30.0
            elif i == 2: d_tk, d_pct = "NVDA", 30.0
            
        tk = row_cols[0].text_input(f"代碼 #{i+1}", value=d_tk, key=f"setup_tk_{i}", label_visibility="collapsed").strip()
        pct = row_cols[1].number_input(f"權重% #{i+1}", min_value=0.0, max_value=100.0, value=d_pct, step=5.0, key=f"setup_pct_{i}", label_visibility="collapsed")
        
        total_setup_pct += pct
        if tk != "":
            setup_data.append({"ticker": tk, "target_pct": pct})
            
    btn_col1, btn_col2 = st.columns([2, 10])
    with btn_col1:
        lock_btn = st.button("📌 鎖定初始投入庫存", type="primary", use_container_width=True)
    with btn_col2:
        if total_setup_pct != 100.0:
            st.warning(f"⚠️ 目前設定的初始權重加總為 `{total_setup_pct}%`。請調整至 100% 以利精準鎖定。")
        else:
            st.success("🎉 權重分配合計 100%，您可以點擊按鈕鎖定或覆蓋歷史庫存了！")

    # 點擊鎖定：計算股數、同步寫入記憶體與本機 JSON 檔
    if lock_btn and total_setup_pct == 100.0:
        locked_list = []
        with st.spinner('正在根據當前市場即時價定格初始購買股數並存檔...'):
            for item in setup_data:
                tk = item["ticker"]
                try:
                    stock_info = yf.download(tk, period="5d")
                    if not stock_info.empty:
                        if isinstance(stock_info.columns, pd.MultiIndex):
                            stock_info.columns = stock_info.columns.get_level_values(0)
                        init_price = float(stock_info['Close'].iloc[-1])
                        allocated_ntd = init_funds * (item["target_pct"] / 100.0)
                        
                        if ".TW" in tk or tk.startswith("^"):
                            init_shares = int(allocated_ntd / init_price)
                        else:
                            price_in_ntd = init_price * current_usdtwd_rate
                            init_shares = int(allocated_ntd / price_in_ntd)
                            
                        locked_list.append({
                            "ticker": tk,
                            "target_pct": item["target_pct"],
                            "init_shares": init_shares
                        })
                except Exception as e:
                    st.error(f"代碼 {tk} 鎖定失敗: {str(e)}")
            
            # 同步更新與儲存
            st.session_state.locked_portfolio = locked_list
            save_portfolio_to_local(init_funds, locked_list)
            st.toast("🔒 初始庫存已成功鎖定，並已同步永久儲存至本機檔案！")
            st.rerun() # 強制刷新畫面顯示最新鎖定狀態

    st.markdown("---")
    st.subheader("第二步：跟隨每日市場波動監控盤（隨時回來看這區）")
    
    if st.session_state.locked_portfolio is None:
        st.info("💡 請先在上方設定好代碼與比例，並點擊「📌 鎖定初始投入庫存」按鈕。")
    else:
        st.success(f"🔒 目前系統正持續監控您鎖定的歷史資產（已安全留存於本機檔案）。下方數據為跟隨今日最新股市波動之結果：")
        
        show_cols = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2, 2.6])
        show_cols[0].markdown("**✍️ 股票代碼**")
        show_cols[1].markdown("**🔒 鎖定初始股數**")
        show_cols[2].markdown("**🎯 理想目標權重**")
        show_cols[3].markdown("**💰 今日最新市價**")
        show_cols[4].markdown("**💵 今日最新市值 (NTD)**")
        show_cols[5].markdown("**📈 今日真實權重**")
        show_cols[6].markdown("**⚖️ 一鍵再平衡調整建議**")
        
        st.markdown("---")
        
        running_portfolio = []
        today_total_market_value_ntd = 0.0
        
        with st.spinner('正在同步全球交易所最新價格中...'):
            for s_item in st.session_state.locked_portfolio:
                tk = s_item["ticker"]
                try:
                    stock_info = yf.download(tk, period="5d")
                    if not stock_info.empty:
                        if isinstance(stock_info.columns, pd.MultiIndex):
                            stock_info.columns = stock_info.columns.get_level_values(0)
                        today_price = float(stock_info['Close'].iloc[-1])
                        
                        if ".TW" in tk or tk.startswith("^"):
                            currency = "TWD"
                            today_price_in_ntd = today_price
                        else:
                            currency = "USD"
                            today_price_in_ntd = today_price * current_usdtwd_rate
                            
                        today_item_value_ntd = today_price_in_ntd * s_item["init_shares"]
                        today_total_market_value_ntd += today_item_value_ntd
                        
                        running_portfolio.append({
                            "ticker": tk, "init_shares": s_item["init_shares"], "target_pct": s_item["target_pct"],
                            "currency": currency, "today_price": today_price, "today_price_in_ntd": today_price_in_ntd,
                            "today_value_ntd": today_item_value_ntd, "show_cols": show_cols
                        })
                except:
                    st.error(f"無法更新 {tk} 的今日現價。")
                    
        if running_portfolio:
            plot_data = []
            for index, res in enumerate(running_portfolio):
                r_cols = st.columns([1.5, 1.2, 1.2, 1.5, 2, 2, 2.6])
                today_real_pct = (res["today_value_ntd"] / today_total_market_value_ntd * 100) if today_total_market_value_ntd > 0 else 0.0
                today_ideal_value_ntd = today_total_market_value_ntd * (res["target_pct"] / 100.0)
                diff_ntd = today_ideal_value_ntd - res["today_value_ntd"]
                diff_shares = diff_ntd / res["today_price_in_ntd"] if res["today_price_in_ntd"] > 0 else 0
                
                plot_data.append({
                    "股票代碼": res["ticker"], "今日真實權重 (%)": round(today_real_pct, 2),
                    "目標理想權重 (%)": res["target_pct"], "今日最新市值 (NTD)": res["today_value_ntd"]
                })
                
                r_cols[0].write(f"**{res['ticker']}**")
                r_cols[1].write(f"{res['init_shares']:,} 股")
                r_cols[2].write(f"{res['target_pct']}%")
                
                if res["currency"] == "USD":
                    r_cols[3].write(f"USD {res['today_price']}\n(台幣:{round(res['today_price_in_ntd'],1)})")
                else:
                    r_cols[3].write(f"NTD {res['today_price']}")
                    
                r_cols[4].write(f"NTD {round(res['today_value_ntd'], 2):,}")
                r_cols[5].write(f"`{today_real_pct:.2f}%` \n(🎯 偏離: {round(today_real_pct - res['target_pct'], 2)}%)")
                
                if diff_shares >= 0.5:
                    r_cols[6].success(f"➕ 補配：**買進 {int(diff_shares)} 股**\n(投入 NTD {round(diff_ntd):,})")
                elif diff_shares <= -0.5:
                    r_cols[6].error(f"➖ 獲利：**賣出 {abs(int(diff_shares))} 股**\n(收回 NTD {round(abs(diff_ntd)):,})")
                else:
                    r_cols[6].info("✅ 平衡：與目標一致\n不需變動")
                    
            st.markdown("---")
            col1, col2 = st.columns([1, 1])
            df_plot = pd.DataFrame(plot_data)
            
            with col1:
                st.subheader(f"💼 今日資產總規模：約 NTD {round(today_total_market_value_ntd, 2):,} 元")
                growth_rate = ((today_total_market_value_ntd - init_funds) / init_funds * 100) if init_funds > 0 else 0.0
                st.metric(label="📈 投後累積總投報率", value=f"{growth_rate:.2f} %", delta=f"{round(today_total_market_value_ntd - init_funds):,} NTD")
                
                fig_pie = px.pie(df_plot, values='今日最新市值 (NTD)', names='股票代碼', title="今日最新真實市場波動占比圖", hole=0.4, template="plotly_dark")
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col2:
                st.subheader("📊 因股市波動造成的權重偏離對比")
                fig_bar = go.Figure(data=[
                    go.Bar(name='今日真實權重 (%)', x=df_plot['股票代碼'], y=df_plot['今日真實權重 (%)'], marker_color='#00ffcc'),
                    go.Bar(name='初始目標權重 (%)', x=df_plot['股票代碼'], y=df_plot['目標理想權重 (%)'], marker_color='#ff9900')
                ])
                fig_bar.update_layout(barmode='group', template="plotly_dark", height=380, margin=dict(t=30, b=20, l=20, r=20))
                st.plotly_chart(fig_bar, use_container_width=True)

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
        chart_data = yf.download(ticker, start=start_date, end=today_date)
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
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500, margin=dict(t=20, b=20, l=20, r=20))
            fig.update_xaxes(type='date', autorange=True)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"圖表載入失敗: {str(e)}")
