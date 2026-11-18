import os
import sys
import datetime
import streamlit as st
from streamlit.runtime import exists
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ssi_engine import (
    BASKETS,
    get_market_symbols,
    fetch_ssi_basket_history,
    fetch_ssi_symbol_history,
    get_vn_today,
    feed
)

if __name__ == '__main__' and not exists():
    import streamlit.web.cli as stcli

    sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
    sys.exit(stcli.main())

st.set_page_config(
    page_title="Hệ thống Giao dịch Minervini Pro - Toàn Sàn",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. CSS GIAO DIỆN SAAS TÀI CHÍNH ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #f8fafc; }

    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 96% !important; }

    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 20px 28px;
        border-radius: 14px;
        margin-bottom: 16px;
        color: white;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .main-header h1 { font-weight: 800; font-size: 1.55rem; margin: 0; letter-spacing: -0.4px; color: #ffffff; }
    .main-header p { opacity: 0.85; margin: 4px 0 0 0; font-size: 0.86rem; font-weight: 400; color: #cbd5e1; }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 15px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -4px rgba(0,0,0,0.06);
        border-color: #cbd5e1;
    }
    .metric-title { font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.3px;}
    .metric-value { font-size: 1.6rem; font-weight: 800; color: #0f172a; line-height: 1.1; margin-bottom: 8px;}
    .metric-delta { font-size: 0.73rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;}

    .badge-up { background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 6px; font-weight: 700; }
    .badge-down { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 6px; font-weight: 700; }
    .badge-neutral { background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 6px; font-weight: 600; }

    .chart-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 20px 8px 20px;
        margin-top: 16px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .chart-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 10px;
        margin-bottom: 8px;
    }
    .chart-title { font-size: 1rem; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 8px; }
    .chart-subtitle { font-size: 0.78rem; color: #64748b; font-weight: 500; }

    .health-bar {
        display: inline-flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        padding: 7px 16px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 0.82rem;
        margin-bottom: 14px;
    }
    .health-bullish { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .health-bearish { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    .health-neutral { background-color: #fef9c3; color: #b45309; border: 1px solid #fde047; }

    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.76rem;
        font-weight: 700;
        color: #047857;
        background: #ecfdf5;
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid #6ee7b7;
        margin-bottom: 14px;
        margin-right: 10px;
    }
    .pulse-dot {
        width: 8px; height: 8px; background-color: #10b981; border-radius: 50%;
        animation: pulse 1.2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .stTabs [data-baseweb="tab-list"] { background-color: #f1f5f9; padding: 4px; border-radius: 10px; gap: 6px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 18px; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background-color: white !important; box-shadow: 0 1px 3px rgba(0,0,0,0.08); color: #0284c7 !important; }

    header { background: transparent !important; }
    .stApp > header { background-color: transparent !important; }
</style>
""", unsafe_allow_html=True)


# --- 2. CACHE DỮ LIỆU CHUNG TRÊN CLOUD (TIẾT KIỆM RAM & TĂNG TỐC) ---
@st.cache_data(ttl=3600, show_spinner=False)
def cached_market_symbols(market_type: str):
    return get_market_symbols(market_type)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_market_history(symbols_tuple: tuple, start_d: datetime.date, end_d: datetime.date):
    df_r = fetch_ssi_basket_history(list(symbols_tuple), start_d, end_d, max_workers=20)
    df_v = fetch_ssi_symbol_history("VNINDEX", start_d, end_d)
    return df_r, df_v


# --- 3. XỬ LÝ DỮ LIỆU & CHỐNG NHIỄU GIÁ REALTIME (SANITY GUARD) ---
def process_market_and_stocks(df_raw, df_vnindex, rt_ticks=None):
    df = df_raw.copy()
    max_market_date = df['Date'].max()
    vn_today_ts = pd.Timestamp(get_vn_today())

    if rt_ticks:
        last_indices = df.groupby('Ticker')['Date'].idxmax()
        new_rows = []
        for idx in last_indices:
            tk = df.at[idx, 'Ticker']
            if tk in rt_ticks:
                t = rt_ticks[tk]
                prev_close = float(df.at[idx, 'Close'])
                if prev_close <= 0:
                    continue

                t_price = float(t['price'])
                t_high = float(t['high'])
                t_low = float(t['low'])
                t_open = float(t.get('open', t_price))
                t_vol = float(t.get('volume', 0))

                if t_price / prev_close > 100:
                    t_price /= 1000.0
                    t_high /= 1000.0
                    t_low /= 1000.0
                    t_open /= 1000.0

                if t_price <= 0 or abs(t_price - prev_close) / prev_close > 0.20:
                    continue

                if t_high <= 0 or abs(t_high - t_price) / t_price > 0.20:
                    t_high = t_price
                if t_low <= 0 or abs(t_low - t_price) / t_price > 0.20:
                    t_low = t_price
                if t_open <= 0 or abs(t_open - t_price) / t_price > 0.20:
                    t_open = t_price

                t_high = max(t_high, t_price, t_open)
                t_low = min(t_low, t_price, t_open)

                tick_date = pd.Timestamp(t.get('date', max_market_date)).normalize()
                last_date = pd.Timestamp(df.at[idx, 'Date']).normalize()

                if tick_date > last_date and tick_date <= vn_today_ts:
                    new_rows.append({
                        'Date': tick_date,
                        'Ticker': tk,
                        'Open': round(t_open, 2),
                        'High': round(t_high, 2),
                        'Low': round(t_low, 2),
                        'Close': round(t_price, 2),
                        'Volume': t_vol
                    })
                elif tick_date == last_date:
                    df.at[idx, 'Close'] = round(t_price, 2)
                    df.at[idx, 'High'] = round(max(df.at[idx, 'High'], t_high), 2)
                    df.at[idx, 'Low'] = round(min(df.at[idx, 'Low'], t_low), 2)
                    if t_vol > 0:
                        df.at[idx, 'Volume'] = max(df.at[idx, 'Volume'], t_vol)

        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            df.sort_values(by=['Ticker', 'Date'], inplace=True)
            df.reset_index(drop=True, inplace=True)

    grouped = df.groupby('Ticker', sort=False)
    for ma in [20, 50, 150, 200]:
        df[f'MA{ma}'] = grouped['Close'].rolling(ma).mean().reset_index(level=0, drop=True)

    df['Vol_MA20'] = grouped['Volume'].rolling(20, min_periods=5).mean().reset_index(level=0, drop=True)
    df['Vol_MA50'] = grouped['Volume'].rolling(50, min_periods=10).mean().reset_index(level=0, drop=True)
    df['MA200_20D_ago'] = grouped['MA200'].shift(20)

    df['Peak_52W'] = grouped['High'].rolling(252, min_periods=60).max().reset_index(level=0, drop=True)
    df['Bottom_52W'] = grouped['Low'].rolling(252, min_periods=60).min().reset_index(level=0, drop=True)

    c = df['Close']
    c_63 = grouped['Close'].shift(63)
    c_126 = grouped['Close'].shift(126)
    c_252 = grouped['Close'].shift(252)

    r_63 = (c / c_63 - 1)
    r_126 = (c / c_126 - 1)
    r_252 = (c / c_252 - 1)

    df['Momentum'] = np.where(
        c_252.notna(), (r_63 * 0.4 + r_126 * 0.3 + r_252 * 0.3) * 100,
        np.where(c_126.notna(), (r_63 * 0.6 + r_126 * 0.4) * 100, r_63 * 100)
    )

    df['Pct_From_Bottom'] = np.where(df['Bottom_52W'] > 0, ((c - df['Bottom_52W']) / df['Bottom_52W']) * 100, np.nan)
    df['Pct_From_Peak'] = np.where(df['Peak_52W'] > 0, ((c - df['Peak_52W']) / df['Peak_52W']) * 100, np.nan)

    df['Has_52W'] = df['Bottom_52W'].notna().astype(int)
    df['Is_Bottoming'] = ((df['Pct_From_Bottom'] <= 10) & df['Bottom_52W'].notna()).astype(int)

    df['Above_MA200'] = ((df['Close'] > df['MA200']) & df['MA200'].notna()).astype(int)
    df['Has_MA200'] = df['MA200'].notna().astype(int)

    df['Below_MA20'] = ((df['Close'] < df['MA20']) & df['MA20'].notna()).astype(int)
    df['Has_MA20'] = df['MA20'].notna().astype(int)

    daily = df.groupby('Date').agg(
        avg_price=('Close', 'mean'),
        total_with_52w=('Has_52W', 'sum'),
        total_with_ma=('Has_MA200', 'sum'),
        above_ma=('Above_MA200', 'sum'),
        total_with_ma20=('Has_MA20', 'sum'),
        below_ma20=('Below_MA20', 'sum'),
        bottoming=('Is_Bottoming', 'sum')
    ).reset_index()

    daily['pct_above_ma'] = np.where(
        daily['total_with_ma'] > 0,
        (daily['above_ma'] / daily['total_with_ma']) * 100,
        np.nan
    )
    daily['pct_below_ma20'] = np.where(
        daily['total_with_ma20'] > 0,
        (daily['below_ma20'] / daily['total_with_ma20']) * 100,
        np.nan
    )
    daily['pct_bottoming'] = np.where(
        daily['total_with_52w'] > 0,
        (daily['bottoming'] / daily['total_with_52w']) * 100,
        np.nan
    )

    if not df_vnindex.empty:
        vni_map = df_vnindex.set_index('Date')['Close'].to_dict()
        daily['hose_index'] = daily['Date'].map(vni_map).ffill().bfill()
        if rt_ticks and "VNINDEX" in rt_ticks:
            vni_rt = float(rt_ticks["VNINDEX"]['price'])
            last_vni = float(daily['hose_index'].iloc[-1])
            if last_vni > 0 and abs(vni_rt - last_vni) / last_vni <= 0.10:
                daily.loc[daily.index[-1], 'hose_index'] = vni_rt
    else:
        daily['hose_index'] = daily['avg_price']

    return daily, df


# --- 4. BỘ LỌC MINERVINI & VCP ---
def filter_minervini_stocks(sf, min_rs=60, min_vol=0):
    if sf.empty:
        return pd.DataFrame()

    cond1 = (sf['Close'] > sf['MA150']) & (sf['Close'] > sf['MA200'])
    cond2 = (sf['MA150'] > sf['MA200'])
    cond3 = (sf['MA200'] > sf['MA200_20D_ago'])
    cond4 = (sf['MA50'] > sf['MA150']) & (sf['MA50'] > sf['MA200'])
    cond5 = (sf['Close'] > sf['MA50'])
    cond6 = (sf['Pct_From_Bottom'] >= 25)
    cond7 = (sf['Pct_From_Peak'] >= -25)
    cond8 = (sf['RS_Rating'] >= min_rs)
    cond_vol = (sf['Vol_MA20'].fillna(0) >= min_vol)

    mask = cond1 & cond2 & cond3 & cond4 & cond5 & cond6 & cond7 & cond8 & cond_vol
    filtered = sf[mask].copy()

    if not filtered.empty:
        filtered = filtered.sort_values(by=['RS_Rating', 'Momentum'], ascending=[False, False])
    return filtered


def detect_vcp_pattern(stock_data, current_date, lookback_days=150):
    data = stock_data[(stock_data['Date'] <= current_date) &
                      (stock_data['Date'] >= (current_date - pd.Timedelta(days=lookback_days)))].copy()
    if len(data) < 35:
        return None

    closes = data['Close'].values
    dates = data['Date'].values
    highs = data['High'].values if 'High' in data.columns else closes
    lows = data['Low'].values if 'Low' in data.columns else closes
    vols = data['Volume'].values if 'Volume' in data.columns else np.zeros(len(closes))
    vol_ma50 = data['Vol_MA50'].values if 'Vol_MA50' in data.columns else np.zeros(len(closes))

    reversal_pct = 0.028
    swings = []
    current_mode = 'peak'
    extreme_val = highs[0]
    extreme_date = dates[0]

    for i in range(1, len(closes)):
        if current_mode == 'peak':
            if highs[i] >= extreme_val:
                extreme_val, extreme_date = highs[i], dates[i]
            elif (extreme_val - lows[i]) / extreme_val >= reversal_pct:
                swings.append(('peak', extreme_date, extreme_val))
                current_mode, extreme_val, extreme_date = 'valley', lows[i], dates[i]
        else:
            if lows[i] <= extreme_val:
                extreme_val, extreme_date = lows[i], dates[i]
            elif (highs[i] - extreme_val) / extreme_val >= reversal_pct:
                swings.append(('valley', extreme_date, extreme_val))
                current_mode, extreme_val, extreme_date = 'peak', highs[i], dates[i]

    swings.append((current_mode, extreme_date, extreme_val))

    clean_swings = []
    for s in swings:
        if not clean_swings:
            clean_swings.append(s)
        elif clean_swings[-1][0] == s[0]:
            if s[0] == 'peak' and s[2] > clean_swings[-1][2]:
                clean_swings[-1] = s
            elif s[0] == 'valley' and s[2] < clean_swings[-1][2]:
                clean_swings[-1] = s
        else:
            clean_swings.append(s)

    contractions = []
    for i in range(len(clean_swings) - 1):
        if clean_swings[i][0] == 'peak' and clean_swings[i + 1][0] == 'valley':
            p_val, v_val = clean_swings[i][2], clean_swings[i + 1][2]
            contractions.append({
                'peak_date': clean_swings[i][1], 'peak_val': p_val,
                'valley_date': clean_swings[i + 1][1], 'valley_val': v_val,
                'depth': ((p_val - v_val) / p_val) * 100
            })

    if len(contractions) < 2:
        return None

    for num_c in [4, 3, 2]:
        if len(contractions) >= num_c:
            cand = contractions[-num_c:]
            depths = [c['depth'] for c in cand]
            valleys = [c['valley_val'] for c in cand]
            peaks = [c['peak_val'] for c in cand]

            base_days = (pd.to_datetime(cand[-1]['valley_date']) - pd.to_datetime(cand[0]['peak_date'])).days
            if (base_days >= 15 and
                    all(depths[i] > depths[i + 1] for i in range(len(depths) - 1)) and
                    all(valleys[i] <= valleys[i + 1] * 1.015 for i in range(len(valleys) - 1)) and
                    depths[-1] <= 8.5 and
                    all(p <= peaks[0] * 1.04 for p in peaks)):

                pivot = cand[-1]['peak_val']
                curr_price = closes[-1]
                pct_from_pivot = ((curr_price - pivot) / pivot) * 100
                curr_vol_ratio = (vols[-1] / vol_ma50[-1] * 100) if (len(vol_ma50) > 0 and vol_ma50[-1] > 0) else np.nan

                if 0 <= pct_from_pivot <= 5.0:
                    status, priority = "🟢 Điểm Mua Chuẩn (<= 5%)", 0
                elif -5.0 <= pct_from_pivot < 0:
                    status, priority = f"⏳ Sát Pivot ({pct_from_pivot:.1f}%)", 1
                elif pct_from_pivot < -5.0:
                    status, priority = f"⏳ Chờ Pivot ({pct_from_pivot:.1f}%)", 2
                else:
                    status, priority = f"⚠️ Quá Điểm Mua (+{pct_from_pivot:.1f}%)", 3

                zz_dates, zz_vals = [], []
                for c_item in cand:
                    zz_dates.extend([c_item['peak_date'], c_item['valley_date']])
                    zz_vals.extend([c_item['peak_val'], c_item['valley_val']])

                return {
                    'is_vcp': True, 'buy_point': pivot, 'ranges': [round(d, 1) for d in depths],
                    'pct_from_pivot': pct_from_pivot, 'status': status, 'priority': priority,
                    'num_contractions': num_c, 'base_days': base_days, 'vol_ratio': curr_vol_ratio,
                    'zigzag_dates': zz_dates, 'zigzag_vals': zz_vals
                }
    return None


def evaluate_stock_phase(tk):
    ma200 = tk['MA200']
    ma200_20d = tk['MA200_20D_ago']
    ma200_slope = ((ma200 - ma200_20d) / ma200_20d * 100) if (pd.notna(ma200_20d) and ma200_20d > 0) else 0
    close, ma50 = tk['Close'], tk['MA50']
    pct_from_peak, pct_from_bottom = tk['Pct_From_Peak'], tk['Pct_From_Bottom']

    if close > ma50 and ma50 > ma200 and close > ma200 and ma200_slope >= 0:
        if pct_from_bottom >= 25 and pct_from_peak >= -25:
            return "GIAI ĐOẠN 2 (TĂNG TỐC - UPTREND MẠNH)", "#10b981", "Cổ phiếu đạt chuẩn Stage 2 của Minervini: Cấu trúc xu hướng hoàn hảo, MA dốc lên, sát đỉnh 52 tuần. Ưu tiên điểm MUA theo đà tăng."
        return "GIAI ĐOẠN 2 (ĐANG TRONG XU HƯỚNG TĂNG)", "#059669", "Nằm trên MA50 & MA200 dốc lên. Xu hướng tăng chủ đạo, có thể xuất hiện nhịp tích lũy tự nhiên."
    if close <= ma50 and close > ma200 and ma50 > ma200 and ma200_slope >= 0.8:
        return "GIAI ĐOẠN 2 (ĐIỀU CHỈNH LÀNH MẠNH)", "#0284c7", "Cổ phiếu đang kéo ngược về hỗ trợ MA50 trong khi MA200 vẫn dốc mạnh lên. Đây là nhịp tích lũy tự nhiên của Giai đoạn 2."
    if pct_from_peak >= -25 and abs(ma200_slope) < 0.6 and (close < ma50 or close < ma200):
        return "GIAI ĐOẠN 3 (PHÂN PHỐI - TẠO ĐỈNH)", "#f59e0b", "MA200 bắt đầu đi ngang, mất đà tăng trưởng. Giá dao động lỏng lẻo quanh MA50/MA200. Cân nhắc chốt lời từng phần."
    if abs(ma200_slope) <= 0.8 and abs(close - ma200) / ma200 <= 0.12 and pct_from_peak < -25:
        return "GIAI ĐOẠN 1 (TÍCH LŨY - TẠO ĐÁY)", "#3b82f6", "Giá dao động biên hẹp quanh đường MA200 đang phẳng ra sau chu kỳ giảm dài."
    if close < ma200 and ma50 < ma200:
        return "GIAI ĐOẠN 4 (SUY THOÁI - DOWNTREND)", "#ef4444", "Cổ phiếu trong xu hướng giảm dài hạn (Stage 4). Giá và MA50 nằm hoàn toàn dưới MA200. TUYỆT ĐỐI KHÔNG BẮT ĐÁY!"
    if close < ma200 and close < ma50:
        return "CHUYỂN GIAO SANG GIAI ĐOẠN 4", "#f97316", "Giá đã xuyên thủng MA200 và MA50, cảnh báo rủi ro cao rơi vào chu kỳ giảm giá dài hạn."
    if close > ma200:
        return "CHUYỂN GIAO (TỪ GIAI ĐOẠN 1 SANG 2)", "#8b5cf6", "Giá đã bứt lên trên MA200, các đường trung bình ngắn hạn đang chuẩn bị giao cắt vàng."
    return "GIAI ĐOẠN 4 (SUY THOÁI)", "#ef4444", "Xu hướng giảm chi phối, giá nằm dưới MA200."


def render_metric_card(title, value, delta_val, delta_text, is_percentage=False, invert_color=False, icon=""):
    d_class, d_sign = "badge-neutral", ""
    if delta_val > 0:
        d_class = "badge-down" if invert_color else "badge-up"
        d_sign = "▲"
    elif delta_val < 0:
        d_class = "badge-up" if invert_color else "badge-down"
        d_sign = "▼"
    val_str = f"{value:.2f}%" if is_percentage else f"{value:,.2f}"
    delta_str = f"{abs(delta_val):.2f}%" if is_percentage else f"{abs(delta_val):,.2f}"
    html = f"""<div class="metric-card"><div class="metric-title">{icon} {title}</div><div class="metric-value">{val_str}</div><div class="metric-delta"><span class="{d_class}">{d_sign} {delta_str}</span> <span style="color:#94a3b8; font-weight:500; font-size:0.72rem; margin-left:4px;">{delta_text}</span></div></div>"""
    st.markdown(html, unsafe_allow_html=True)


def highlight_rs(val):
    if pd.isna(val):
        return ''
    val = int(val)
    if val >= 90:
        return 'background-color: #8b5cf6; color: white; font-weight: bold; border-radius: 4px;'
    elif val >= 80:
        return 'background-color: #10b981; color: white; font-weight: bold; border-radius: 4px;'
    elif val >= 70:
        return 'background-color: #f59e0b; color: white; font-weight: bold; border-radius: 4px;'
    return 'color: #64748b;'


# --- 5. DASHBOARD REALTIME AUTO-REFRESH FRAGMENT ---
def render_dashboard_body(df_raw, df_vnindex, symbols, fetch_start, fetch_end, show_ma20_line, min_vol_filter):
    rt_ticks = feed.get_all_realtime() if feed.is_running else {}
    daily_all, df_history = process_market_and_stocks(df_raw, df_vnindex, rt_ticks)

    start_ts = pd.to_datetime(fetch_start)
    end_ts = pd.to_datetime(max(fetch_end, get_vn_today()))
    data_plot = daily_all[(daily_all['Date'] >= start_ts) & (daily_all['Date'] <= end_ts)].copy()

    if data_plot.empty:
        st.warning("⚠️ Không có dữ liệu để vẽ đồ thị trong khoảng thời gian đã chọn.")
        return

    actual_eval_date = df_history[df_history['Date'] <= end_ts]['Date'].max()
    latest_data = df_history[df_history['Date'] == actual_eval_date].copy()
    latest_data['RS_Rating'] = (
        (latest_data['Momentum'].rank(pct=True, ascending=True, na_option='keep') * 98)
        .round().fillna(0).astype(int) + 1
    )

    latest_hose = data_plot['hose_index'].iloc[-1]
    prev_hose = data_plot['hose_index'].iloc[-2] if len(data_plot) > 1 else latest_hose

    latest_pct = data_plot['pct_above_ma'].iloc[-1]
    prev_pct = data_plot['pct_above_ma'].iloc[-2] if len(data_plot) > 1 else latest_pct

    latest_below_ma20 = data_plot['pct_below_ma20'].iloc[-1]
    prev_below_ma20 = data_plot['pct_below_ma20'].iloc[-2] if len(data_plot) > 1 else latest_below_ma20

    latest_bot = data_plot['pct_bottoming'].iloc[-1]
    prev_bot = data_plot['pct_bottoming'].iloc[-2] if len(data_plot) > 1 else latest_bot

    peak_row = data_plot.loc[data_plot['hose_index'].idxmax()]
    peak_price, peak_date = peak_row['hose_index'], peak_row['Date']
    pct_drop = ((peak_price - latest_hose) / peak_price) * 100 if peak_price > 0 else 0

    cum_peak_historical = data_plot['hose_index'].cummax()
    data_plot['pct_drop_from_peak'] = ((cum_peak_historical - data_plot['hose_index']) / cum_peak_historical) * 100

    if latest_below_ma20 >= 80:
        st_short_term = f"⚡ Ngắn hạn: QUÁ BÁN CỰC ĐẠI ({latest_below_ma20:.1f}% < MA20) - Dễ hồi kỹ thuật"
    elif latest_below_ma20 <= 20:
        st_short_term = f"🔥 Ngắn hạn: HƯNG PHẤN / QUÁ MUA ({latest_below_ma20:.1f}% < MA20) - Tránh FOMO"
    elif latest_below_ma20 >= 65:
        st_short_term = f"⚠️ Ngắn hạn: Áp lực điều chỉnh cao ({latest_below_ma20:.1f}% < MA20)"
    else:
        st_short_term = f"⚖️ Ngắn hạn: Cân bằng ({latest_below_ma20:.1f}% < MA20)"

    status_line = ""
    if feed.is_running:
        status_line += (
            f"<div class='live-indicator'><div class='pulse-dot'></div> "
            f"LIVE TRONG PHIÊN: {len(rt_ticks)} mã nhận tick • Nguồn: {feed.source_name} • Lúc: {feed.last_sync_str}</div>"
        )

    if latest_pct >= 50:
        status_line += f"<div class='health-bar health-bullish'>🟢 DÀI HẠN: UPTREND ({latest_pct:.1f}% > MA200) &nbsp;|&nbsp; {st_short_term}</div>"
    elif latest_pct <= 20 and latest_bot >= 40:
        status_line += f"<div class='health-bar health-bearish'>🔴 DÀI HẠN: DÒ ĐÁY NGUY HIỂM ({latest_bot:.1f}% sát đáy 52T) &nbsp;|&nbsp; {st_short_term}</div>"
    elif latest_pct <= 20:
        status_line += f"<div class='health-bar health-bearish'>🔴 DÀI HẠN: QUÁ BÁN ({latest_pct:.1f}% > MA200) &nbsp;|&nbsp; {st_short_term}</div>"
    else:
        status_line += f"<div class='health-bar health-neutral'>🟡 DÀI HẠN: ĐI NGANG / PHÂN HÓA ({latest_pct:.1f}% > MA200) &nbsp;|&nbsp; {st_short_term}</div>"
    st.markdown(status_line, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_metric_card("Chỉ Số HOSE (VN-INDEX)", latest_hose, latest_hose - prev_hose, "so với phiên trước",
                           icon="🏛️")
    with c2:
        render_metric_card("Độ Rộng (> MA200)", latest_pct, latest_pct - prev_pct, "so với phiên trước",
                           is_percentage=True, icon="🌊")
    with c3:
        render_metric_card("Ngắn Hạn (< MA20)", latest_below_ma20, latest_below_ma20 - prev_below_ma20,
                           "so với phiên trước", is_percentage=True, invert_color=True, icon="⚡")
    with c4:
        render_metric_card("% CP Dò Đáy (<=10% Đáy)", latest_bot, latest_bot - prev_bot, "so với phiên trước",
                           is_percentage=True, invert_color=True, icon="🕳️")
    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📉 HOSE SỤT GIẢM TỪ ĐỈNH</div>
            <div class="metric-value"><span style="color:#ef4444;">-{pct_drop:.2f}%</span></div>
            <div class="metric-delta"><span class="badge-neutral">Đỉnh: {peak_price:,.2f} ({peak_date.strftime('%d/%m/%Y')})</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="chart-box">
        <div class="chart-header">
            <div class="chart-title">📈 Biểu Đồ Tương Quan Chỉ Số HOSE (VN-INDEX) & Độ Rộng Nội Tại ({len(symbols)} Mã)</div>
            <div class="chart-subtitle">Dữ liệu từ {fetch_start.strftime('%d/%m/%Y')} đến {actual_eval_date.strftime('%d/%m/%Y')}</div>
        </div>
    """, unsafe_allow_html=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=data_plot['Date'], y=data_plot['hose_index'], name="Chỉ số HOSE (VN-INDEX)",
        mode='lines', line=dict(color='#0284c7', width=3.0),
        customdata=data_plot['pct_drop_from_peak'],
        hovertemplate="<b>HOSE (VN-INDEX): %{y:,.2f}</b> (Cách đỉnh: -%{customdata:.2f}%)<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=data_plot['Date'], y=data_plot['pct_above_ma'], name="% Trên MA200 (Dài hạn)",
        mode='lines', line=dict(color='#f59e0b', width=2.2),
        hovertemplate="Độ rộng > MA200: <b>%{y:.1f}%</b><extra></extra>"
    ), secondary_y=True)

    if show_ma20_line:
        fig.add_trace(go.Scatter(
            x=data_plot['Date'], y=data_plot['pct_below_ma20'], name="% Dưới MA20 (Ngắn hạn)",
            mode='lines', line=dict(color='rgba(236, 72, 153, 0.55)', width=1.4, dash='dot'),
            hovertemplate="Áp lực < MA20: <b>%{y:.1f}%</b><extra></extra>"
        ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=data_plot['Date'], y=data_plot['pct_bottoming'], name="% Đang Dò Đáy 52T",
        mode='lines', line=dict(color='#8b5cf6', width=1.8, dash='dash'),
        hovertemplate="% Dò đáy 52T: <b>%{y:.1f}%</b><extra></extra>"
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=[peak_date], y=[peak_price], mode='markers+text',
        marker=dict(color='#ef4444', size=9, line=dict(color='white', width=2)),
        text=[f"ĐỈNH: {peak_price:,.2f}"], textposition="top center",
        textfont=dict(family="Inter", size=11, color="#b91c1c"),
        showlegend=False, hoverinfo='skip'
    ), secondary_y=False)

    fig.add_hline(y=80, line_dash="dot", line_color="rgba(236, 72, 153, 0.5)",
                  annotation_text="80% (Quá bán ngắn hạn)", annotation_position="top left",
                  annotation_font=dict(color="#db2777", size=10), secondary_y=True)
    fig.add_hline(y=50, line_dash="dash", line_color="rgba(148, 163, 184, 0.6)",
                  annotation_text="50% (Cân bằng)", annotation_position="top left",
                  annotation_font=dict(color="#64748b", size=10), secondary_y=True)
    fig.add_hline(y=20, line_dash="dash", line_color="rgba(239, 68, 68, 0.6)",
                  annotation_text="20% (Hoảng loạn dài hạn)", annotation_position="bottom left",
                  annotation_font=dict(color="#dc2626", size=10), secondary_y=True)

    hose_min = float(data_plot['hose_index'].min())
    hose_max = float(data_plot['hose_index'].max())
    hose_pad = max((hose_max - hose_min) * 0.15, 50)

    fig.update_layout(
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(255,255,255,0.96)", font_size=12, font_color="#0f172a", bordercolor="#cbd5e1"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(family="Inter", size=11.5), bgcolor="rgba(255,255,255,0)"
        ),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=28, b=10), height=450
    )

    fig.update_xaxes(
        showgrid=True, gridcolor='#f1f5f9', linecolor='#cbd5e1',
        hoverformat="%d/%m/%Y", tickfont=dict(family="Inter", size=11, color="#475569")
    )
    fig.update_yaxes(
        title_text="Chỉ số HOSE (VN-INDEX)", title_font=dict(size=12, color="#0284c7", family="Inter"),
        range=[hose_min - hose_pad, hose_max + hose_pad * 1.3],
        showgrid=True, gridcolor='#f1f5f9', tickfont=dict(color="#0284c7", size=11),
        secondary_y=False
    )
    fig.update_yaxes(
        title_text="Độ Rộng Thị Trường (%)", title_font=dict(size=12, color="#d97706", family="Inter"),
        range=[0, 105], showgrid=False, tickfont=dict(color="#d97706", size=11),
        ticksuffix="%", secondary_y=True
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    base_stocks = filter_minervini_stocks(latest_data, min_rs=60, min_vol=min_vol_filter)
    vcp_list = []
    vcp_tickers_set = set()

    if not base_stocks.empty:
        min_lookback_date = actual_eval_date - pd.Timedelta(days=150)
        recent_df = df_history[
            (df_history['Date'] >= min_lookback_date) &
            (df_history['Date'] <= actual_eval_date) &
            (df_history['Ticker'].isin(base_stocks['Ticker']))
        ]
        recent_grouped = dict(tuple(recent_df.groupby('Ticker', sort=False)))

        for _, row in base_stocks.iterrows():
            tk_name = row['Ticker']
            tk_hist = recent_grouped.get(tk_name, pd.DataFrame())
            if not tk_hist.empty:
                res_vcp = detect_vcp_pattern(tk_hist, actual_eval_date, lookback_days=150)
                if res_vcp:
                    vcp_tickers_set.add(tk_name)
                    vcp_list.append({
                        'Live': "⚡ LIVE" if tk_name in rt_ticks else "EOD",
                        'Mã CP': tk_name,
                        'RS Rating': int(row['RS_Rating']),
                        'Giá Hiện Tại': row['Close'],
                        'Điểm Pivot (Mua)': res_vcp['buy_point'],
                        '% Cách Pivot': res_vcp['pct_from_pivot'],
                        'Số Vòng Thu Hẹp': f"{res_vcp['num_contractions']}T ({' -> '.join([str(r) + '%' for r in res_vcp['ranges']])})",
                        'Nền Giá (Ngày)': res_vcp['base_days'],
                        'KL / MA50 (%)': res_vcp['vol_ratio'],
                        'Trạng Thái Mua': res_vcp['status'],
                        '_priority': res_vcp['priority'],
                        '_abs_dist': abs(res_vcp['pct_from_pivot'])
                    })

    tabs = st.tabs(["🚀 Quét Siêu Cổ Phiếu (Minervini)", "📐 Mẫu Hình Cốc / VCP", "🔍 Chẩn Đoán Cổ Phiếu Đơn & Đồ Thị"])

    with tabs[0]:
        st.markdown(f"### 🏆 Bảng Xếp Hạng Cổ Phiếu Dẫn Dắt (Ngày {actual_eval_date.strftime('%d/%m/%Y')})")
        col_f1, _ = st.columns([1, 3])
        with col_f1:
            rs_threshold = st.slider("Lọc theo RS Rating tối thiểu:", min_value=50, max_value=95, value=70, step=5)

        if not latest_data.empty:
            minervini_stocks = filter_minervini_stocks(latest_data, min_rs=rs_threshold, min_vol=min_vol_filter)
            if not minervini_stocks.empty:
                st.success(
                    f"🔥 Phát hiện **{len(minervini_stocks)} / {len(symbols)}** cổ phiếu thỏa mãn Trend Template (RS >= {rs_threshold}, KLGD TB 20P >= {min_vol_filter:,.0f} CP).")
                disp_df = minervini_stocks[
                    ['Ticker', 'Close', 'RS_Rating', 'Pct_From_Peak', 'Pct_From_Bottom', 'Vol_MA20', 'MA20', 'MA50',
                     'MA150', 'MA200']
                ].rename(columns={
                    'Ticker': 'Mã CP', 'Close': 'Giá Hiện Tại', 'Pct_From_Peak': '% Từ Đỉnh 52T',
                    'Pct_From_Bottom': '% Hồi Từ Đáy 52T', 'RS_Rating': 'RS Rating', 'Vol_MA20': 'KLGD TB 20P'
                })
                styled_df = disp_df.style \
                    .map(highlight_rs, subset=['RS Rating']) \
                    .background_gradient(cmap='OrRd_r', subset=['% Từ Đỉnh 52T']) \
                    .background_gradient(cmap='Blues', subset=['% Hồi Từ Đáy 52T']) \
                    .format({
                        'Giá Hiện Tại': '{:.2f}', 'MA20': '{:.2f}', 'MA50': '{:.2f}', 'MA150': '{:.2f}', 'MA200': '{:.2f}',
                        '% Từ Đỉnh 52T': '{:.1f}%', '% Hồi Từ Đáy 52T': '{:.1f}%',
                        'RS Rating': '{:.0f}', 'KLGD TB 20P': '{:,.0f}'
                    })
                st.dataframe(styled_df, use_container_width=True, height=450, hide_index=True)
            else:
                st.warning(
                    f"⚠️ Không có mã nào đạt đủ tiêu chí Trend Template với RS Rating >= {rs_threshold} tại ngày này.")

    with tabs[1]:
        st.markdown("### 📐 Tín hiệu Điểm Mua Mô hình Thu hẹp Biến động (VCP)")
        st.caption(
            "Các cổ phiếu thỏa mãn Trend Template được quét cấu trúc VCP (Lookback 150 ngày, nền giá >= 15 ngày).")

        if vcp_list:
            vcp_df = pd.DataFrame(vcp_list)
            vcp_df = vcp_df.sort_values(by=['_priority', '_abs_dist', 'RS Rating'], ascending=[True, True, False]).drop(
                columns=['_priority', '_abs_dist'])
            st.success(f"🎯 Phát hiện **{len(vcp_df)}** mã có cấu trúc giá tích lũy VCP hợp lệ.")

            def style_vcp_status(val):
                if "Chuẩn" in val:
                    return 'background-color: #dcfce7; color: #166534; font-weight: bold; border-radius: 4px;'
                elif "Quá" in val:
                    return 'background-color: #fee2e2; color: #991b1b; font-weight: bold; border-radius: 4px;'
                elif "Sát" in val:
                    return 'background-color: #e0f2fe; color: #0369a1; font-weight: bold; border-radius: 4px;'
                return 'background-color: #fef3c7; color: #92400e; font-weight: bold; border-radius: 4px;'

            styled_vcp = vcp_df.style \
                .map(highlight_rs, subset=['RS Rating']) \
                .map(style_vcp_status, subset=['Trạng Thái Mua']) \
                .format({
                    'Giá Hiện Tại': '{:.2f}', 'Điểm Pivot (Mua)': '{:.2f}',
                    '% Cách Pivot': '{:+.1f}%', 'KL / MA50 (%)': '{:.0f}%'
                }, na_rep="-")
            st.dataframe(styled_vcp, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa phát hiện cổ phiếu nào hình thành cấu trúc VCP hợp lệ trong danh mục tại ngày này.")

    with tabs[2]:
        st.markdown("### 🔍 Chẩn Đoán Cổ Phiếu Đơn & Đồ Thị Kỹ Thuật")

        all_tickers = sorted(latest_data['Ticker'].unique().tolist())
        minervini_set = set(base_stocks['Ticker'].tolist()) if not base_stocks.empty else set()
        rs_map = dict(zip(latest_data['Ticker'], latest_data['RS_Rating']))

        vcp_sorted = [item['Mã CP'] for item in vcp_list]
        minervini_only = [t for t in base_stocks['Ticker'].tolist() if
                          t not in vcp_tickers_set] if not base_stocks.empty else []
        other_tickers = [t for t in all_tickers if t not in vcp_tickers_set and t not in minervini_set]
        ordered_tickers = vcp_sorted + minervini_only + other_tickers

        def format_ticker_label(t):
            rs_val = rs_map.get(t, 0)
            if t in vcp_tickers_set:
                return f"📐 {t} — [Mô hình VCP | RS: {rs_val}]"
            elif t in minervini_set:
                return f"🔥 {t} — [Chuẩn Minervini | RS: {rs_val}]"
            return f"{t} (RS: {rs_val})"

        col_sel1, col_sel2 = st.columns([2, 1])
        with col_sel1:
            selected_ticker = st.selectbox(
                "Chọn hoặc gõ mã cổ phiếu muốn phân tích:",
                options=ordered_tickers, index=0 if ordered_tickers else None,
                format_func=format_ticker_label
            )
        with col_sel2:
            chart_type = st.radio("Kiểu biểu đồ giá:", ["Biểu đồ Nến (Candlestick)", "Biểu đồ Đường (Close)"],
                                  horizontal=True)

        if selected_ticker:
            tk_data = latest_data[latest_data['Ticker'] == selected_ticker]
            if not tk_data.empty:
                tk = tk_data.iloc[0]
                phase_title, phase_color, phase_desc = evaluate_stock_phase(tk)

                stock_history = df_history[df_history['Ticker'] == selected_ticker].copy()
                vcp_diag = detect_vcp_pattern(stock_history, actual_eval_date, lookback_days=150)

                st.markdown(f"""
                <div style='border: 1px solid {phase_color}; border-left: 8px solid {phase_color}; padding: 14px 18px; border-radius: 8px; background-color: #ffffff; margin-bottom: 14px;'>
                    <div style='color: {phase_color}; font-weight: 800; font-size: 1.1rem; margin-bottom: 3px;'>🧭 {phase_title}</div>
                    <div style='color: #475569; font-size: 0.88rem;'>{phase_desc}</div>
                </div>
                """, unsafe_allow_html=True)

                if vcp_diag:
                    st.markdown(f"""
                    <div style='border: 1px solid #8b5cf6; border-left: 8px solid #8b5cf6; padding: 12px 16px; border-radius: 8px; background-color: #f5f3ff; margin-bottom: 16px;'>
                        <span style='color: #6d28d9; font-weight: 800;'>📐 MÔ HÌNH VCP HỢP LỆ ({vcp_diag['base_days']} ngày):</span>
                        Số vòng thu hẹp: <b>{vcp_diag['num_contractions']}T ({' -> '.join([str(r) + '%' for r in vcp_diag['ranges']])})</b> |
                        Điểm Pivot: <b>{vcp_diag['buy_point']:.2f}</b> | Cách Pivot: <b>{vcp_diag['pct_from_pivot']:+.1f}%</b> ({vcp_diag['status']})
                    </div>
                    """, unsafe_allow_html=True)

                colA, colB, colC = st.columns(3)
                with colA:
                    st.markdown("**Cấu trúc Xu hướng & MA:**")
                    st.write(
                        f"- Giá ({tk['Close']:.2f}) vs MA20 ({tk['MA20']:.2f}): {'✅ Nằm trên' if tk['Close'] >= tk['MA20'] else '❌ Gãy MA20'}")
                    st.write(
                        f"- Giá vs MA50 ({tk['MA50']:.2f}): {'✅ Nằm trên' if tk['Close'] > tk['MA50'] else '❌ Nằm dưới'}")
                    st.write(
                        f"- Giá vs MA150 & MA200: {'✅ Nằm trên' if (tk['Close'] > tk['MA150'] and tk['Close'] > tk['MA200']) else '❌ Nằm dưới'}")
                with colB:
                    st.markdown("**Vị thế Đỉnh / Đáy 52 Tuần:**")
                    st.write(f"- Đỉnh 52T: **{tk['Peak_52W']:.2f}** (Cách: **{tk['Pct_From_Peak']:.1f}%**)")
                    st.write(f"- Đáy 52T: **{tk['Bottom_52W']:.2f}** (Cách: **+{tk['Pct_From_Bottom']:.1f}%**)")
                    st.write(
                        f"- Độ dốc MA200: {'✅ Dốc lên' if tk['MA200'] > tk['MA200_20D_ago'] else '❌ Đi ngang / Dốc xuống'}")
                with colC:
                    st.markdown("**Sức mạnh & Thanh khoản:**")
                    st.markdown(
                        f"Điểm RS Rating: <span style='font-size:1.4rem; font-weight:800; color:#8b5cf6;'>{tk['RS_Rating']}</span> / 99",
                        unsafe_allow_html=True)
                    st.write(f"- KLGD phiên: **{tk['Volume']:,.0f}** CP")
                    st.write(f"- KLGD TB 20P: **{tk['Vol_MA20']:,.0f}** CP")

                st.markdown("<br>", unsafe_allow_html=True)
                stock_plot = stock_history[stock_history['Date'] <= actual_eval_date].tail(160).copy()

                if not stock_plot.empty:
                    fig_stock = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                                              row_heights=[0.74, 0.26])

                    if "Nến" in chart_type:
                        fig_stock.add_trace(go.Candlestick(
                            x=stock_plot['Date'], open=stock_plot['Open'], high=stock_plot['High'],
                            low=stock_plot['Low'], close=stock_plot['Close'], name="Giá (OHLC)",
                            increasing_line_color='#10b981', decreasing_line_color='#ef4444'
                        ), row=1, col=1)
                    else:
                        fig_stock.add_trace(go.Scatter(
                            x=stock_plot['Date'], y=stock_plot['Close'], name="Giá đóng cửa",
                            line=dict(color='#0284c7', width=2.5)
                        ), row=1, col=1)

                    fig_stock.add_trace(go.Scatter(x=stock_plot['Date'], y=stock_plot['MA20'], name="MA20",
                                                   line=dict(color='#10b981', width=1.3, dash='dot')), row=1, col=1)
                    fig_stock.add_trace(go.Scatter(x=stock_plot['Date'], y=stock_plot['MA50'], name="MA50",
                                                   line=dict(color='#f97316', width=1.5, dash='dash')), row=1, col=1)
                    fig_stock.add_trace(go.Scatter(x=stock_plot['Date'], y=stock_plot['MA150'], name="MA150",
                                                   line=dict(color='#8b5cf6', width=1.5, dash='dash')), row=1, col=1)
                    fig_stock.add_trace(go.Scatter(x=stock_plot['Date'], y=stock_plot['MA200'], name="MA200",
                                                   line=dict(color='#ef4444', width=2)), row=1, col=1)

                    if vcp_diag:
                        fig_stock.add_trace(go.Scatter(
                            x=vcp_diag['zigzag_dates'], y=vcp_diag['zigzag_vals'],
                            mode='lines+markers', name=f"Sóng VCP ({vcp_diag['num_contractions']}T)",
                            line=dict(color='#6d28d9', width=2, dash='dot'), marker=dict(size=7, color='#6d28d9')
                        ), row=1, col=1)
                        fig_stock.add_hline(
                            y=vcp_diag['buy_point'], line_dash="dot", line_color="#8b5cf6", line_width=2,
                            annotation_text=f"Pivot: {vcp_diag['buy_point']:.2f}", annotation_position="top right",
                            row=1, col=1
                        )

                    vol_colors = np.where(stock_plot['Close'] >= stock_plot['Open'], '#10b981', '#ef4444')
                    fig_stock.add_trace(
                        go.Bar(x=stock_plot['Date'], y=stock_plot['Volume'], name="Khối lượng", marker_color=vol_colors,
                               opacity=0.75), row=2, col=1)
                    fig_stock.add_trace(go.Scatter(x=stock_plot['Date'], y=stock_plot['Vol_MA50'], name="MA50 Volume",
                                                   line=dict(color='#0284c7', width=1.5)), row=2, col=1)

                    fig_stock.update_layout(
                        hovermode="x unified", height=540, xaxis_rangeslider_visible=False,
                        margin=dict(l=50, r=20, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_stock.update_xaxes(showgrid=True, gridcolor='#f1f5f9', linecolor='#e2e8f0',
                                           hoverformat="%d/%m/%Y", rangebreaks=[dict(bounds=["sat", "mon"])])
                    fig_stock.update_yaxes(title_text="Giá", showgrid=True, gridcolor='#f1f5f9', linecolor='#e2e8f0',
                                           row=1, col=1)
                    fig_stock.update_yaxes(title_text="Volume", showgrid=True, gridcolor='#f1f5f9', linecolor='#e2e8f0',
                                           row=2, col=1)
                    st.plotly_chart(fig_stock, use_container_width=True)


@st.fragment(run_every="5s")
def render_live_fragment(df_raw, df_vnindex, symbols, fetch_start, fetch_end, show_ma20_line, min_vol_filter):
    render_dashboard_body(df_raw, df_vnindex, symbols, fetch_start, fetch_end, show_ma20_line, min_vol_filter)


# --- 6. GIAO DIỆN CHÍNH ---
def main():
    st.markdown("""
    <div class="main-header">
        <div>
            <h1>⚡ Hệ thống Định lượng & Phân tích Chu kỳ Minervini (HOSE Direct)</h1>
            <p>Biểu đồ HOSE (VN-INDEX) & Độ rộng Thị trường • Chu kỳ 4 Giai đoạn • Quét Siêu Cổ Phiếu VCP Realtime</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    today = get_vn_today()
    default_start_date = today - datetime.timedelta(days=550)

    with st.sidebar:
        st.markdown("### 📡 Nguồn Dữ Liệu")
        basket_choice = st.selectbox("Chọn rổ danh mục theo dõi:", list(BASKETS.keys()), index=0)
        custom_tickers = st.text_input("Hoặc gõ danh sách mã riêng:", placeholder="VD: FPT, SSI, HPG, VCB")

        if custom_tickers.strip():
            symbols = [s.strip().upper() for s in custom_tickers.split(",") if len(s.strip()) == 3]
        else:
            choice_val = BASKETS[basket_choice]
            if choice_val == "ALL_HOSE":
                symbols = cached_market_symbols("HOSE")
            elif choice_val == "ALL_ALL":
                symbols = cached_market_symbols("ALL")
            else:
                symbols = choice_val

        st.success(f"🎯 Số lượng mã theo dõi: **{len(symbols)}** cổ phiếu")

        st.markdown("---")
        st.markdown("### 📅 Dải Ngày Phân Tích (Tối thiểu 400 ngày)")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fetch_start = st.date_input("Từ ngày:", value=default_start_date, max_value=today)
        with col_d2:
            fetch_end = st.date_input("Đến ngày:", value=today, max_value=today)

        diff_days = (fetch_end - fetch_start).days
        if fetch_start >= fetch_end:
            st.error("⚠️ Ngày bắt đầu phải nhỏ hơn ngày kết thúc!")
            return
        elif diff_days < 400:
            st.warning(f"⚠️ Dải ngày hiện tại ({diff_days} ngày) chưa đủ 400 ngày để tính MA200.")
            return
        else:
            st.caption(f"✅ Biên độ hiển thị: **{diff_days}** ngày (+330 ngày đệm tính MA200)")

        st.markdown("---")
        st.markdown("### ⚙️ Tùy Chỉnh Biểu Đồ & Thanh Khoản")
        show_ma20_line = st.checkbox("Hiển thị đường % Dưới MA20 (Ngắn hạn)", value=True)
        min_vol_filter = st.number_input(
            "KLGD TB 20 phiên tối thiểu (CP):",
            min_value=0, max_value=5000000, value=50000, step=10000
        )

        realtime_on = st.toggle("⚡ Bật Realtime Trong Phiên (Live Engine)", value=feed.is_running)
        if realtime_on:
            feed.start(symbols)
        elif not realtime_on and feed.is_running:
            feed.stop()

        if st.button("🔄 Tải mới toàn bộ dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner(f"⏳ Đang đồng bộ dữ liệu lịch sử ({len(symbols)} cổ phiếu) từ máy chủ..."):
        df_raw, df_vnindex = cached_market_history(tuple(symbols), fetch_start, fetch_end)

    if df_raw.empty:
        st.error("⚠️ Không tải được dữ liệu từ API. Vui lòng kiểm tra lại kết nối mạng!")
        return

    if realtime_on:
        render_live_fragment(df_raw, df_vnindex, symbols, fetch_start, fetch_end, show_ma20_line, min_vol_filter)
    else:
        render_dashboard_body(df_raw, df_vnindex, symbols, fetch_start, fetch_end, show_ma20_line, min_vol_filter)


if __name__ == '__main__':
    main()