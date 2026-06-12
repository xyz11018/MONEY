import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import datetime
import pandas as pd
import json
import os

# 1. 網頁全寬配置與深色模式美化
st.set_page_config(layout="wide", page_title="全球資產再平衡系統", page_icon="📈")

# 自訂 CSS 美化
st.markdown("""
    <style>
    .market-header { padding: 10px; border-radius: 8px; font-weight: bold; margin-bottom: 10px; }
    .tw-market { background-color: #0f172a; border-left: 6px solid #00ffcc; color: #00ffcc; }
    .us-market { background-color: #0f172a; border-left: 6px solid #ff9900; color: #ff9900; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "portfolio_db.json"

# 載入與存檔函數 (強化版)
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"init_funds": 100000, "locked_portfolio": []}

# 獲取價格函數
@st.cache_data(ttl=3600)
def get_price(ticker):
    try:
        df = yf.download(ticker, period="2d", progress=False)
        return float(df['Close'].iloc[-1])
    except: return None

# 匯率
rate = get_price("TWD=X") or 32.5

# 側邊欄
st.sidebar.title("🎛️ 操盤控制台")
app_mode = st.sidebar.radio("功能選擇", ["📊 資產再平衡監控盤", "🔍 技術分析"])
data = load_data()

# -------------------------------------------------------------------------
# 主頁面：資產監控盤 (台美股分流)
# -------------------------------------------------------------------------
if app_mode == "📊 資產再平衡監控盤":
    st.title("📊 全球資產動態再平衡系統")
    
    # 配置設定
    with st.expander("📌 設定與鎖定資產配置", expanded=False):
        num = st.number_input("資產數量", 1, 10, len(data["locked_portfolio"]) or 3)
        setup = []
        for i in range(num):
            c = st.columns([2, 1, 1])
            tk = c[0].text_input(f"代碼 {i+1}", value=(data["locked_portfolio"][i]["ticker"] if i < len(data["locked_portfolio"]) else ""), key=f"tk{i}")
            pct = c[1].number_input(f"目標權重%", value=(data["locked_portfolio"][i]["target_pct"] if i < len(data["locked_portfolio"]) else 0.0), key=f"pct{i}")
            lev = c[2].number_input(f"槓桿", value=(data["locked_portfolio"][i].get("leverage", 1.0) if i < len(data["locked_portfolio"]) else 1.0), key=f"lev{i}")
            if tk: setup.append({"ticker": tk, "target_pct": pct, "leverage": lev})
        
        if st.button("鎖定初始庫存"):
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump({"init_funds": 100000, "locked_portfolio": setup}, f)
            st.rerun()

    # 監控邏輯
    if data["locked_portfolio"]:
        tw_assets, us_assets = [], []
        total_val = 0
        
        for item in data["locked_portfolio"]:
            p = get_price(item["ticker"])
            if p:
                is_tw = ".TW" in item["ticker"] or item["ticker"].startswith("^")
                val_ntd = (p if is_tw else (p * rate)) * (item["leverage"] * 10000) # 簡化計算
                item_data = {**item, "val": val_ntd, "price": p, "is_tw": is_tw}
                if is_tw: tw_assets.append(item_data)
                else: us_assets.append(item_data)
                total_val += val_ntd

        # 渲染區塊
        for label, assets, cls in [("🇹🇼 台灣股市/指數", tw_assets, "tw-market"), ("🇺🇸 美國股市/指數", us_assets, "us-market")]:
            if assets:
                st.markdown(f'<div class="market-header {cls}">{label}</div>', unsafe_allow_html=True)
                for r in assets:
                    cols = st.columns([2, 2, 2, 2])
                    val_display = f"{r['val']:.1f}" if not r["is_tw"] else f"{int(r['val']):,}"
                    cols[0].metric(r["ticker"], f"NTD {val_display}")
                    cols[1].write(f"目標權重: {r['target_pct']}%")
                    cols[2].write(f"槓桿: {r['leverage']}x")
                    cols[3].write("✅ 平衡" if abs((r["val"]/total_val*100) - r["target_pct"]) < 2 else "⚠️ 需調整")
    else:
        st.info("請設定代碼並鎖定庫存。")

# -------------------------------------------------------------------------
# 分頁二：技術分析 (原代碼架構)
# -------------------------------------------------------------------------
elif app_mode == "🔍 技術分析":
    # (此處沿用你原本的 K 線圖代碼即可)
    st.title("🔍 K 線技術分析")
    ticker = st.text_input("輸入代碼", "2330.TW")
    # ... (K 線圖渲染邏輯)
