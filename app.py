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
# 1. 頁面配置與雙主題高對比視覺優化
# ==========================================
st.set_page_config(layout="wide", page_title="全球資產動態平衡系統", page_icon="🏦")

st.markdown("""
    <style>
    /* 質感標題區塊 */
    .market-header { 
        padding: 16px 20px; border-radius: 10px; font-weight: 700; 
        margin-bottom: 20px; font-size: 1.3rem; color: #ffffff !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        letter-spacing: 1px;
    }
    .tw-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #00ffcc; }
    .us-market { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #f97316; }
    
    /* 專業金融數據字體板塊 */
    .ticker-display { font-size: 2.2rem; font-weight: 900; line-height: 1.1; letter-spacing: 0.5px; }
    .price-display { font-size: 1.1rem; font-weight: 600; opacity: 0.8; margin-top: 4px; }
    .data-label { font-size: 0.95rem; opacity: 0.7; margin-bottom: 2px;}
    .data-value { font-size: 1.1rem; font-weight: 700; }
    
    .news-card {
        padding: 15px; border-radius: 8px; 
        background-color: rgba(148, 163, 184, 0.08); 
        border: 1px solid rgba(148, 163, 184, 0.15);
        margin-bottom: 12px;
    }
    
    label, .stMarkdown p { font-weight: 500; }
    hr { border-color: rgba(148, 163, 184, 0.2); }
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

# ==========================================
# 3. 核心功能：獨立存檔機制
# ==========================================
def load_portfolio():
    default_data = {"tw_portfolio": [], "us_portfolio": []}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
                return {k: data[k] for k in default_data.keys() if k in data}
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
    ["🇹🇼 台股持股監控", "🇺🇸 美股持股監控", "🔍 全球 K 線分析"]
)
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
    
    st.markdown(f'<h1>🏦 {app_mode.split(" ")[1]} 專業分析面板</h1>', unsafe_allow_html=True)
    
    # 📌 獨立設定區 (改為手動輸入真實持股)
    with st.expander(f"⚙️ 編輯 {market_label} 初始配置 (直接輸入持股)", expanded=(not db_data[current_list_key])):
        st.info(f"💡 提示：請直接輸入您真實持有的「股數」。若為現金或大盤指數，請輸入投入的「總金額」。")
        cols = st.columns([2, 2, 2])
        cols[0].markdown("**代碼 / 現金**"); cols[1].markdown("**目標權重%**"); cols[2].markdown("**持有股數 / 現金金額**")
        
        new_setup = []
        for i in range(int(num_assets)):
            r_cols = st.columns([2, 2, 2])
            hist = db_data[current_list_key][i] if i < len(db_data[current_list_key]) else {"ticker": "", "target_pct": 0, "init_shares": 0}
            
            display_tk = hist["ticker"].replace(".TWO", "").replace(".TW", "") if (".TW" in hist.get("ticker", "") or ".TWO" in hist.get("ticker", "")) else hist.get("ticker", "")
            raw_tk = r_cols[0].text_input(f"tk_{i}", display_tk, label_visibility="collapsed", placeholder="代碼 或 現金").strip()
            
            safe_pct = min(100.0, max(0.0, float(hist.get("target_pct", 0.0))))
            safe_shares = max(0.0, float(hist.get("init_shares", 0.0)))
            
            pct = r_cols[1].number_input(f"pct_{i}", min_value=0.0, max_value=100.0, value=safe_pct, step=5.0, label_visibility="collapsed")
            shares_input = r_cols[2].number_input(f"shares_{i}", min_value=0.0, value=safe_shares, step=100.0, label_visibility="collapsed")
            
            if raw_tk: new_setup.append({"raw_ticker": raw_tk, "target_pct": pct, "shares_input": shares_input})
        
        if st.button(f"📌 鎖定 {market_label} 庫存並更新系統", type="primary"):
            locked_assets = []
            error_tickers = []
            with st.spinner('正在解析代碼並同步市場數據...'):
                for item in new_setup:
                    real_ticker = resolve_ticker(item["raw_ticker"])
                    p = fetch_realtime_data(real_ticker)
                    lev = get_leverage(real_ticker)
                    
                    if p and p > 0: 
                        locked_assets.append({
                            "ticker": real_ticker, "target_pct": item["target_pct"], "leverage": lev, 
                            "init_shares": item["shares_input"], "init_price": p, "is_tw": is_tw_mode
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
    local_total_val, local_total_exp = 0, 0
    target_portfolio = db_data[current_list_key]
    
    if target_portfolio:
        with st.spinner(f"🔄 正在運算最新動態數據..."):
            for asset in target_portfolio:
                now_p = fetch_realtime_data(asset["ticker"])
                if now_p and now_p > 0:
                    lev = asset.get("leverage", 1.0)
                    is_tw = asset.get("is_tw", is_tw_mode)
                    
                    # 計算市值邏輯：大盤/現金使用金額，股票使用股數*價格
                    if asset["ticker"].startswith("^"):
                        now_val_ntd = asset.get("init_shares", 0) * (now_p / asset.get("init_price", now_p))
                    elif asset["ticker"] == "CASH":
                        now_val_ntd = asset.get("init_shares", 0) * (1.0 if is_tw_mode else current_rate)
                    else:
                        price_ntd = now_p if is_tw_mode else (now_p * current_rate)
                        now_val_ntd = price_ntd * asset.get("init_shares", 0)
                    
                    exposure_ntd = now_val_ntd * lev
                    
                    local_total_val += now_val_ntd
                    local_total_exp += exposure_ntd
                    
                    current_view_data.append({**asset, "now_p": now_p, "now_val_ntd": now_val_ntd, "exposure_ntd": exposure_ntd})

        if current_view_data:
            st.markdown(f'<div class="market-header {"tw-market" if is_tw_mode else "us-market"}">{"🇹🇼 台灣市場" if is_tw_mode else "🇺🇸 美國市場"} 動態監控盤</div>', unsafe_allow_html=True)
            for item in current_view_data:
                c = st.columns([1.5, 1.3, 1.2, 1.5, 1.5, 2.6])
                real_pct = (item["now_val_ntd"] / local_total_val * 100) if local_total_val > 0 else 0
                diff = real_pct - item["target_pct"]
                
                if item["ticker"] == "CASH":
                    currency_str = "TWD" if is_tw_mode else "USD"
                    unit_str = "元" if is_tw_mode else "美元"
                    c[0].markdown(f"<div class='ticker-display'>💵 現金</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>持倉總額:</div><div class='data-value'>{int(item.get('init_shares', 0)):,} {unit_str}</div>", unsafe_allow_html=True)
                else:
                    clean_name = item["ticker"].replace('.TWO', '').replace('.TW', '')
                    c[0].markdown(f"<div class='ticker-display'>{clean_name}</div><div class='price-display'>{'NTD' if is_tw_mode else 'USD'} {item['now_p']:.2f}</div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='data-label'>{'📊 投入金額:' if item['ticker'].startswith('^') else '持股總數:'}</div><div class='data-value'>{int(item.get('init_shares', 0)):,} {'元' if item['ticker'].startswith('^') else '股'}</div>", unsafe_allow_html=True)
                
                c[2].markdown(f"<div class='data-label'>目標設定:</div><div class='data-value'>{item['target_pct']}%</div>", unsafe_allow_html=True)
                c[3].markdown(f"<div class='data-label'>真實市值:</div><div class='data-value'>NTD {int(item['now_val_ntd']):,}</div>", unsafe_allow_html=True)
                c[4].markdown(f"<div class='data-label'>槓桿水位:</div><div class='data-value'>{item.get('leverage', 1.0)}x</div><div class='data-label' style='margin-top:4px;'>總曝險額:</div><div class='data-value'>NTD {int(item['exposure_ntd']):,}</div>", unsafe_allow_html=True)
                
                if abs(diff) > threshold: c[5].warning(f"⚠️ 偏離 {diff:+.1f}%\n(真實佔比: {real_pct:.1f}%)")
                else: c[5].success(f"✅ 平衡區間\n(真實佔比: {real_pct:.1f}%)")

        # 📌 底部指標與圖表
        st.markdown("---")
        footer_cols = st.columns([1, 1])
        with footer_cols[0]:
            st.subheader(f"💰 {market_label} 綜合指標總結")
            overall_leverage = local_total_exp / local_total_val if local_total_val > 0 else 1.0
            
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric(f"總市值 (NTD)", f"{int(local_total_val):,}")
            sc2.metric(f"總曝險 (NTD)", f"{int(local_total_exp):,}")
            sc3.metric(f"實際整體槓桿", f"{overall_leverage:.2f} 倍")

            if current_view_data:
                pie_df = pd.DataFrame([{"tk": "現金" if r["ticker"] == "CASH" else r["ticker"].replace('.TWO','').replace('.TW', ''), "val": r["now_val_ntd"]} for r in current_view_data])
                fig_pie = px.pie(pie_df, values='val', names='tk', hole=0.4, title=f"{market_label}資產 真實比重圖")
                fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0), template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with footer_cols[1]:
            if current_view_data:
                st.subheader(f"📊 {market_label} 權重偏差分析")
                bar_df = pd.DataFrame([{"tk": "現金" if r["ticker"] == "CASH" else r["ticker"].replace('.TWO','').replace('.TW', ''), "Real": (r["now_val_ntd"]/local_total_val*100), "Target": r["target_pct"]} for r in current_view_data])
                fig_bar = go.Figure(data=[
                    go.Bar(name='真實權重 (%)', x=bar_df['tk'], y=bar_df['Real'], marker_color='#00ffcc'),
                    go.Bar(name='設定目標 (%)', x=bar_df['tk'], y=bar_df['Target'], marker_color='#475569')
                ])
                fig_bar.update_layout(barmode='group', height=400, margin=dict(t=40, b=0, l=0, r=0), template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
                st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# 6. 分頁：全球 K 線分析 + 智慧新聞終端
# ==========================================
elif app_mode == "🔍 全球 K 線分析":
    st.title("🔍 全球金融標的技術分析與即時情報")
    
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
        
        k_col, news_col = st.columns([6, 4])
        
        with k_col:
            try:
                with st.spinner("載入量化技術圖表中..."):
                    df_k = yf.download(ticker_input, period="2y", interval="1d", progress=False)
                    if not df_k.empty:
                        if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
                        df_k['MA5'] = df_k['Close'].rolling(window=5).mean()
                        df_k['MA20'] = df_k['Close'].rolling(window=20).mean()
                        df_k['MA200'] = df_k['Close'].rolling(window=200).mean()
                        
                        clean_title = ticker_input.replace('.TWO', '').replace('.TW', '')
                        st.subheader(f"📈 {clean_title} 技術走勢 (含MA200年線)")
                        
                        fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        fig_k.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="K線"), row=1, col=1)
                        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA5'], mode='lines', name='MA5 (週線)', line=dict(color='#ff9900', width=1.5)), row=1, col=1)
                        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA20'], mode='lines', name='MA20 (月線)', line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
                        fig_k.add_trace(go.Scatter(x=df_k.index, y=df_k['MA200'], mode='lines', name='MA200 (年線)', line=dict(color='#ef4444', width=2)), row=1, col=1)
                        fig_k.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], name="成交量", marker_color="#475569"), row=2, col=1)
                        
                        last_6mo = df_k.index.max() - pd.Timedelta(days=180)
                        fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=1, col=1)
                        fig_k.update_xaxes(range=[last_6mo, df_k.index.max()], row=2, col=1)
                        fig_k.update_layout(xaxis_rangeslider_visible=False, height=600, margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig_k, use_container_width=True)
            except: st.error("圖表載入失敗，請確認網路或代碼。")
            
        with news_col:
            st.subheader("📰 市場即時動態與新聞")
            if ticker_input == "CASH":
                st.info("現金資產暫無特定的全球市場新聞。")
            else:
                try:
                    with st.spinner("正在檢索最新消息..."):
                        t_obj = yf.Ticker(ticker_input)
                        news_list = t_obj.news
                        clean_title = ticker_input.replace('.TWO', '').replace('.TW', '')
                        
                        # 雙引擎防護：如果有抓到新聞，就顯示卡片；如果 API 為空，就提供可靠的備用搜尋按鈕
                        if news_list and len(news_list) > 0:
                            bull_keywords = ['創高', '大漲', '營收新高', '利多', '優於預期', '暴增', '買進', '成長', '噴發', 'HIGH', 'GROWTH', 'BULL', 'BEAT', 'UPGRADE']
                            bear_keywords = ['衰退', '大跌', '利空', '低於預期', '虧損', '賣出', '修正', '重挫', 'DROP', 'FALL', 'BEAR', 'MISS', 'DOWNGRADE']
                            
                            for news in news_list[:6]:
                                title = news.get('title', '')
                                publisher = news.get('publisher', '')
                                link = news.get('link', '')
                                
                                title_upper = title.upper()
                                if any(k in title_upper for k in bull_keywords):
                                    tag = "<span style='color:#10b981; font-weight:bold;'>🟢 潛在利多</span>"
                                elif any(k in title_upper for k in bear_keywords):
                                    tag = "<span style='color:#ef4444; font-weight:bold;'>🔴 潛在利空</span>"
                                else:
                                    tag = "<span style='color:#38bdf8; font-weight:bold;'>ℹ️ 市場動態</span>"
                                
                                st.markdown(f"""
                                <div class='news-card'>
                                    <div style='margin-bottom: 6px;'>{tag} <span style='font-size:0.85rem; opacity:0.6;'> | 來源: {publisher}</span></div>
                                    <div style='font-size:1.05rem; font-weight:600; line-height:1.3; margin-bottom:8px;'>{title}</div>
                                    <a href='{link}' target='_blank' style='font-size:0.9rem; color:#4f46e5; text-decoration:none; font-weight:600;'>🔗 閱讀完整報導 →</a>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            # 備用方案：Google 財經新聞直接搜尋連結 (保證絕對有資料)
                            search_url = f"https://www.google.com/search?q={clean_title}+股票+新聞&tbm=nws"
                            st.warning(f"💡 雅虎財經 API 暫無回傳最新新聞。")
                            st.markdown(f"""
                                <div class='news-card' style='text-align:center; padding:30px;'>
                                    <h4 style='margin-bottom:15px;'>👉 點擊下方按鈕獲取最新可靠資訊</h4>
                                    <a href='{search_url}' target='_blank' style='display:inline-block; background-color:#4f46e5; color:white; padding:10px 20px; border-radius:5px; text-decoration:none; font-weight:bold; font-size:1.1rem;'>
                                        🔍 搜尋【{clean_title}】Google 即時新聞
                                    </a>
                                </div>
                            """, unsafe_allow_html=True)
                except:
                    st.info("ℹ️ 網路延遲，暫時無法取得即時新聞流。")
