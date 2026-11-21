import time
import json
import threading
import requests
from requests.adapters import HTTPAdapter
import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import websocket

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))


def get_vn_now() -> datetime.datetime:
    return datetime.datetime.now(VN_TZ)


def get_vn_today() -> datetime.date:
    return get_vn_now().date()


def is_vn_market_hours() -> bool:
    now = get_vn_now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return datetime.time(8, 45) <= t <= datetime.time(15, 15)


# Mỗi thread dùng riêng 1 requests.Session (an toàn đa luồng + tái sử dụng TCP/TLS)
_THREAD_LOCAL = threading.local()

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

SSI_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://iboard.ssi.com.vn",
    "Referer": "https://iboard.ssi.com.vn/",
}

# Circuit breaker: tránh lãng phí hàng trăm request khi IP server bị SSI chặn tạm thời (403/timeout)
_SSI_CB_LOCK = threading.Lock()
_SSI_CHART_FAIL_STREAK = 0
_SSI_CHART_BLOCKED_UNTIL = 0.0
_SSI_IBOARD_BLOCKED_UNTIL = 0.0


def reset_ssi_circuit_breaker():
    global _SSI_CHART_FAIL_STREAK, _SSI_CHART_BLOCKED_UNTIL, _SSI_IBOARD_BLOCKED_UNTIL
    with _SSI_CB_LOCK:
        _SSI_CHART_FAIL_STREAK = 0
        _SSI_CHART_BLOCKED_UNTIL = 0.0
        _SSI_IBOARD_BLOCKED_UNTIL = 0.0


def _get_http_session() -> requests.Session:
    sess = getattr(_THREAD_LOCAL, "session", None)
    if sess is None:
        sess = requests.Session()
        adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=1)
        sess.mount("https://", adapter)
        sess.mount("http://", adapter)
        sess.headers.update(BASE_HEADERS)
        _THREAD_LOCAL.session = sess
    return sess


def is_valid_vn_ticker(sym: str) -> bool:
    """Mã cổ phiếu VN chuẩn gồm 3 ký tự chữ/số và bắt đầu bằng chữ cái (bao gồm PC1, NT2, HT1, C32, D2D...)."""
    s = str(sym or "").strip().upper()
    return len(s) == 3 and s.isalnum() and s[0].isalpha()


def _is_raw_vnd_series(close_series: pd.Series) -> bool:
    """Phân biệt đơn vị VND gốc (VD: 26500) với Nghìn đồng (VD: 26.5 hoặc VNZ 450.0)."""
    valid = close_series.dropna()
    valid = valid[valid > 0]
    if valid.empty:
        return False
    med = float(valid.median())
    if med >= 2000:
        return True
    if med >= 300:
        # Nếu là đơn vị VND gốc thì giá luôn là số nguyên chia hết cho 10 (bước giá 10/50/100đ)
        is_int = ((valid % 1).abs() < 1e-6).mean() > 0.95
        is_mult10 = ((valid % 10).abs() < 1e-6).mean() > 0.90
        return bool(is_int and is_mult10)
    return False

# Tên các bảng/rổ giữ đúng tên gốc trên bảng giá SSI iBoard
BASKETS = {
    "HOSE": ("exchange", "hose"),
    "VN30": ("group", "VN30"),
    "VN100": ("group", "VN100"),
    "VNAllShare (VNALL)": ("group", "VNALL"),
    "VNMidCap (VNMID)": ("group", "VNMID"),
    "VNSmallCap (VNSML)": ("group", "VNSML"),
    "HNX": ("exchange", "hnx"),
    "HNX30": ("group", "HNX30"),
    "UPCOM": ("exchange", "upcom"),
    "HOSE + HNX + UPCOM": ("all", "ALL"),
    "📡 WebSocket SSI (Trực tiếp trong phiên)": ("ws", "WS_LIVE"),
}

# Dự phòng khẩn cấp khi server Cloud bị chặn IP hoàn toàn
HOSE_FULL_FALLBACK = [
    "AAA", "AAM", "AAT", "ABR", "ABS", "ABT", "ACB", "ACC", "ACG", "ACL", "ADG", "ADP", "ADS", "AGG", "AGM", "AGR",
    "AMD", "ANV", "APC", "APG", "APH", "ASG", "ASM", "ASP", "AST", "BAF", "BBC", "BCE", "BCG", "BCM", "BFC", "BHN",
    "BIC", "BID", "BKG", "BMC", "BMI", "BMP", "BRC", "BSI", "BTP", "BTT", "BVH", "BWE", "C32", "C47", "CCI", "CCL",
    "CDC", "CHP", "CIG", "CII", "CKG", "CLC", "CLL", "CLW", "CMG", "CMV", "CMX", "CNG", "COM", "CRC", "CRE", "CSM",
    "CSV", "CTD", "CTF", "CTG", "CTI", "CTR", "CTS", "CVT", "D2D", "DAG", "DAH", "DAT", "DBC", "DBD", "DBT", "DC4",
    "DCL", "DCM", "DGC", "DGW", "DHA", "DHC", "DHG", "DHM", "DIG", "DLG", "DMC", "DPG", "DPM", "DPR", "DQC", "DRC",
    "DRH", "DRL", "DSE", "DSN", "DTA", "DTL", "DTT", "DVP", "DXG", "DXS", "DXV", "EIB", "ELC", "EMC", "EVE", "EVF",
    "EVG", "FCM", "FCN", "FDC", "FIR", "FIT", "FMC", "FPT", "FRT", "FTS", "GAB", "GAS", "GDT", "GEG", "GEX", "GIL",
    "GMC", "GMD", "GMH", "GSP", "GTA", "GVR", "HAG", "HAH", "HAI", "HAP", "HAR", "HAS", "HAX", "HBC", "HCD", "HCM",
    "HDB", "HDC", "HDG", "HHP", "HHS", "HHV", "HID", "HII", "HMC", "HNA", "HNG", "HPG", "HPX", "HQC", "HRC", "HSG",
    "HSL", "HT1", "HTI", "HTL", "HTN", "HTV", "HU1", "HU3", "HUB", "HVH", "HVN", "HVX", "ICT", "IDI", "IJC", "ILB",
    "IMP", "ITA", "ITC", "ITD", "JVC", "KBC", "KDC", "KDH", "KHG", "KHP", "KMR", "KOS", "KPF", "KSB", "L10", "LAF",
    "LBM", "LCG", "LCM", "LDG", "LEC", "LGC", "LGL", "LHG", "LIX", "LM8", "LPB", "LSS", "MBB", "MCG", "MCP", "MDG",
    "MHC", "MIG", "MSB", "MSH", "MSN", "MWG", "NAB", "NAF", "NAV", "NBB", "NCT", "NHA", "NHH", "NHT", "NKG", "NLG",
    "NNC", "NO1", "NSC", "NT2", "NTL", "NVL", "NVT", "OCB", "OGC", "OPC", "ORS", "PAC", "PAN", "PC1", "PDN", "PDR",
    "PET", "PGC", "PGD", "PGI", "PGV", "PHC", "PHR", "PIT", "PJT", "PLP", "PLX", "PMG", "PNC", "PNJ", "POM", "POW",
    "PPC", "PSH", "PTB", "PTC", "PTL", "PVD", "PVP", "PVT", "QBS", "QCG", "RAL", "RDP", "REE", "S4A", "SAB", "SAM",
    "SAV", "SBA", "SBT", "SBV", "SC5", "SCD", "SCR", "SCS", "SFC", "SFG", "SFI", "SGN", "SGR", "SGT", "SHA", "SHB",
    "SHI", "SHP", "SIP", "SJD", "SJF", "SJS", "SKG", "SMA", "SMB", "SMC", "SPM", "SRC", "SRF", "SSB", "SSC", "SSI",
    "ST8", "STB", "STG", "STK", "SVC", "SVD", "SVI", "SVT", "SZC", "SZL", "TBC", "TCB", "TCD", "TCH", "TCI", "TCL",
    "TCM", "TCO", "TCR", "TCT", "TDC", "TDG", "TDH", "TDM", "TDP", "TDW", "TEG", "VGG", "THG", "THI", "TIP", "TIX",
    "TLD", "TLG", "TLH", "TMP", "TMS", "TMT", "TN1", "TNA", "TNC", "TNH", "TNI", "TNT", "TPB", "TPC", "TRA", "TRC",
    "TSC", "TTA", "TTE", "TTF", "TV2", "TVB", "TVS", "TVT", "TYA", "UIC", "VAF", "VCA", "VCB", "VCF", "VCG", "VCI",
    "VDP", "VDS", "VFG", "VGC", "VHC", "VHM", "VIB", "VIC", "VID", "VIP", "VIX", "VJC", "VMD", "VND", "VNE", "VNG",
    "VNL", "VNM", "VNS", "VOS", "VPB", "VPD", "VPG", "VPH", "VPI", "VPS", "VRC", "VRE", "VSC", "VSH", "VSI", "VTB",
    "VTO", "VTP", "YBM", "YEG"
]


VN30_FALLBACK = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "LPB", "MBB", "MSN", "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]

HNX30_FALLBACK = [
    "BVS", "CAP", "CEO", "DHT", "DP3", "DTD", "DVM", "DXP", "HGM", "HUT",
    "IDC", "IDV", "L14", "L18", "LAS", "LHC", "MBS", "NTP", "NVB", "PLC",
    "PSD", "PVB", "PVC", "PVI", "PVS", "SHS", "SLS", "TMB", "TNG", "VC3"
]


def _extract_ssi_items(items: list) -> dict:
    """Trích xuất mã cổ phiếu và tên doanh nghiệp gốc từ JSON SSI iBoard, giữ nguyên thứ tự gốc của SSI."""
    stock_map = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("stockSymbol") or item.get("sym") or item.get("code") or "").strip().upper()
        if not is_valid_vn_ticker(sym):
            continue

        # Lọc đúng cổ phiếu thường theo stockType của SSI (bỏ ETF, CW, trái phiếu nếu có)
        stock_type = str(item.get("stockType") or "").strip().lower()
        if stock_type and stock_type not in ("s", "stock", "st"):
            continue

        comp_name = str(
            item.get("companyNameVi")
            or item.get("companyName")
            or item.get("companyNameEn")
            or item.get("stockName")
            or ""
        ).strip()

        if sym not in stock_map or (not stock_map[sym] and comp_name):
            stock_map[sym] = comp_name
    return stock_map


def _fetch_ssi_endpoint(url: str) -> dict:
    global _SSI_IBOARD_BLOCKED_UNTIL
    now = time.time()
    with _SSI_CB_LOCK:
        if now < _SSI_IBOARD_BLOCKED_UNTIL:
            return {}
    try:
        resp = _get_http_session().get(url, headers=SSI_HEADERS, timeout=7)
        if resp.status_code == 200:
            payload = resp.json()
            items = payload.get("data", []) if isinstance(payload, dict) else []
            if isinstance(items, list) and items:
                return _extract_ssi_items(items)
        elif resp.status_code in (401, 403, 429):
            with _SSI_CB_LOCK:
                _SSI_IBOARD_BLOCKED_UNTIL = time.time() + 180
    except Exception:
        pass
    return {}


def _fetch_vnd_fallback(floors: str) -> dict:
    try:
        url = f"https://finfo-api.vndirect.com.vn/v4/stocks?q=type:stock~status:listed~floor:{floors}&size=3000"
        resp = _get_http_session().get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            res = {}
            for item in data:
                code = str(item.get("code") or "").strip().upper()
                if is_valid_vn_ticker(code):
                    res[code] = str(item.get("companyName") or item.get("shortName") or "").strip()
            return res
    except Exception:
        pass
    return {}


def get_ssi_master_names() -> dict:
    """Lấy bảng tra cứu tên doanh nghiệp gốc toàn thị trường từ SSI iBoard (HOSE + HNX + UPCOM)."""
    urls = [
        "https://iboard-query.ssi.com.vn/stock/exchange/hose?boardId=MAIN",
        "https://iboard-query.ssi.com.vn/stock/exchange/hnx?boardId=MAIN",
        "https://iboard-query.ssi.com.vn/stock/exchange/upcom?boardId=MAIN",
    ]
    master = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        for res in ex.map(_fetch_ssi_endpoint, urls):
            master.update(res)
    if not master:
        master = _fetch_vnd_fallback("HOSE,HNX,UPCOM")
    return master


def get_ssi_basket(basket_label: str):
    """
    Trả về: (symbols_list, symbol_names_dict, source_info)
    Ưu tiên lấy trực tiếp từ SSI iBoard + WebSocket SSI, giữ nguyên tên gốc từ SSI.
    """
    source_type, code = BASKETS.get(basket_label, ("exchange", "hose"))

    # 1. Rổ lấy trực tiếp từ luồng WebSocket SSI
    if source_type == "ws":
        ws_map = feed.discover_ws_symbols(wait_seconds=3.5)
        if ws_map:
            master_names = get_ssi_master_names()
            enriched = {
                sym: (name or master_names.get(sym, ""))
                for sym, name in ws_map.items()
            }
            return list(enriched.keys()), enriched, "WebSocket SSI (wss://iboard-pushstream.ssi.com.vn)"

        # Ngoài giờ giao dịch WebSocket không đẩy lệnh -> lấy bảng HOSE gốc của SSI để không trống dữ liệu
        hose_map = _fetch_ssi_endpoint("https://iboard-query.ssi.com.vn/stock/exchange/hose?boardId=MAIN")
        if hose_map:
            return list(hose_map.keys()), hose_map, "WebSocket ngoài giờ → Tự đồng bộ bảng HOSE gốc SSI"
        vnd_hose = _fetch_vnd_fallback("HOSE")
        if vnd_hose:
            return list(vnd_hose.keys()), vnd_hose, "WebSocket ngoài giờ → Dự phòng bảng HOSE (VNDirect)"
        return list(HOSE_FULL_FALLBACK), {s: "" for s in HOSE_FULL_FALLBACK}, "Dự phòng cục bộ (WebSocket & SSI không phản hồi)"

    # 2. Lấy theo sàn / rổ gốc của SSI iBoard
    stock_map = {}
    if source_type == "exchange":
        stock_map = _fetch_ssi_endpoint(f"https://iboard-query.ssi.com.vn/stock/exchange/{code}?boardId=MAIN")
    elif source_type == "group":
        stock_map = _fetch_ssi_endpoint(f"https://iboard-query.ssi.com.vn/stock/group/{code}")
    elif source_type == "all":
        urls = [
            "https://iboard-query.ssi.com.vn/stock/exchange/hose?boardId=MAIN",
            "https://iboard-query.ssi.com.vn/stock/exchange/hnx?boardId=MAIN",
            "https://iboard-query.ssi.com.vn/stock/exchange/upcom?boardId=MAIN",
        ]
        with ThreadPoolExecutor(max_workers=3) as ex:
            for res in ex.map(_fetch_ssi_endpoint, urls):
                stock_map.update(res)

    if stock_map:
        source_info = f"SSI iBoard Gốc ({code.upper()})"
        # Nếu đang bật WebSocket và xem toàn thị trường, tự hợp nhất các mã mới phát hiện trên luồng WebSocket
        ws_live = feed.get_ws_discovered_symbols()
        if ws_live and source_type == "all":
            added = 0
            for sym, nm in ws_live.items():
                if sym not in stock_map:
                    stock_map[sym] = nm
                    added += 1
            if added > 0:
                source_info += f" + {added} mã WebSocket"
        return list(stock_map.keys()), stock_map, source_info

    # 3. Fallback nếu IP Cloud bị tường lửa SSI chặn tạm thời
    if code == "VN30":
        vnd_names = _fetch_vnd_fallback("HOSE")
        vn30_map = {s: vnd_names.get(s, "") for s in VN30_FALLBACK}
        return list(vn30_map.keys()), vn30_map, "Dự phòng rổ VN30 (SSI iBoard tạm không phản hồi)"
    if code == "HNX30":
        vnd_names = _fetch_vnd_fallback("HNX")
        hnx30_map = {s: vnd_names.get(s, "") for s in HNX30_FALLBACK}
        return list(hnx30_map.keys()), hnx30_map, "Dự phòng rổ HNX30 (SSI iBoard tạm không phản hồi)"

    floor_map = {"hose": "HOSE", "hnx": "HNX", "upcom": "UPCOM", "ALL": "HOSE,HNX,UPCOM"}
    vnd_floor = floor_map.get(code, "HOSE")
    vnd_map = _fetch_vnd_fallback(vnd_floor)
    if vnd_map:
        note = f"sàn {vnd_floor}" if code not in floor_map else code.upper()
        return list(vnd_map.keys()), vnd_map, f"Dự phòng VNDirect ({note} — SSI iBoard tạm không phản hồi)"

    return list(HOSE_FULL_FALLBACK), {s: "" for s in HOSE_FULL_FALLBACK}, "Dự phòng danh sách HOSE cục bộ"


def _build_ohlcv_df(data: dict, sym: str, check_vnd_unit: bool = True) -> pd.DataFrame:
    t_arr = data.get("t") or []
    o_arr = data.get("o") or []
    h_arr = data.get("h") or []
    l_arr = data.get("l") or []
    c_arr = data.get("c") or []
    v_arr = data.get("v") or []
    n = min(len(t_arr), len(o_arr), len(h_arr), len(l_arr), len(c_arr), len(v_arr))
    if n == 0:
        return pd.DataFrame()

    vn_dates = pd.to_datetime(pd.Series(t_arr[:n], dtype="int64") + 25200, unit="s").dt.normalize()
    df = pd.DataFrame({
        "Date": vn_dates,
        "Ticker": sym,
        "Open": pd.to_numeric(o_arr[:n], errors="coerce"),
        "High": pd.to_numeric(h_arr[:n], errors="coerce"),
        "Low": pd.to_numeric(l_arr[:n], errors="coerce"),
        "Close": pd.to_numeric(c_arr[:n], errors="coerce"),
        "Volume": pd.to_numeric(v_arr[:n], errors="coerce").fillna(0.0)
    })
    df.dropna(subset=["Date", "Close"], inplace=True)
    df = df[df["Close"] > 0].copy()
    if df.empty:
        return pd.DataFrame()

    # Bù Open/High/Low nếu bị thiếu hoặc <= 0
    df["Open"] = df["Open"].where(df["Open"] > 0, df["Close"])
    df["High"] = df["High"].where(df["High"] > 0, df[["Open", "Close"]].max(axis=1))
    df["Low"] = df["Low"].where(df["Low"] > 0, df[["Open", "Close"]].min(axis=1))

    if check_vnd_unit and sym != "VNINDEX" and _is_raw_vnd_series(df["Close"]):
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = df[col] / 1000.0

    df.sort_values(by="Date", inplace=True)
    df.drop_duplicates(subset=["Date"], keep="last", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def fetch_ssi_symbol_history(symbol: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Tải lịch sử OHLCV chuẩn hóa múi giờ Việt Nam (UTC+7) và đơn vị Nghìn đồng"""
    global _SSI_CHART_FAIL_STREAK, _SSI_CHART_BLOCKED_UNTIL
    sym = symbol.upper()
    # Đệm 400 ngày lịch (~265 phiên giao dịch) để đủ tính MA200, MA200_20D_ago, 52W High/Low và Momentum 252 phiên
    buffer_start = start_date - datetime.timedelta(days=400)
    from_ts = int(datetime.datetime.combine(buffer_start, datetime.time.min, tzinfo=VN_TZ).timestamp())
    to_ts = int(datetime.datetime.combine(end_date, datetime.time.max, tzinfo=VN_TZ).timestamp())
    sess = _get_http_session()

    # Ưu tiên SSI Chart API trước (có circuit breaker nếu bị chặn), fallback sang VNDirect Chart API
    skip_ssi = False
    with _SSI_CB_LOCK:
        if time.time() < _SSI_CHART_BLOCKED_UNTIL:
            skip_ssi = True

    if not skip_ssi:
        ssi_sym = "VN-INDEX" if sym == "VNINDEX" else sym
        ssi_url = f"https://iboard-api.ssi.com.vn/statistics/charts/history?resolution=1D&symbol={ssi_sym}&from={from_ts}&to={to_ts}"
        try:
            resp = sess.get(ssi_url, headers=SSI_HEADERS, timeout=6)
            if resp.status_code == 200:
                raw_json = resp.json()
                data = raw_json.get("data", raw_json) if isinstance(raw_json, dict) else {}
                if isinstance(data, dict) and data.get("s") == "ok" and data.get("t"):
                    with _SSI_CB_LOCK:
                        _SSI_CHART_FAIL_STREAK = 0
                    df = _build_ohlcv_df(data, sym, check_vnd_unit=True)
                    if not df.empty:
                        return df
            elif resp.status_code in (401, 403, 429):
                with _SSI_CB_LOCK:
                    _SSI_CHART_FAIL_STREAK += 1
                    if _SSI_CHART_FAIL_STREAK >= 3:
                        _SSI_CHART_BLOCKED_UNTIL = time.time() + 300
        except Exception:
            with _SSI_CB_LOCK:
                _SSI_CHART_FAIL_STREAK += 1
                if _SSI_CHART_FAIL_STREAK >= 8:
                    _SSI_CHART_BLOCKED_UNTIL = time.time() + 180

    vnd_url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={sym}&from={from_ts}&to={to_ts}"
    try:
        resp = sess.get(vnd_url, headers={"Referer": "https://dchart.vndirect.com.vn/"}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and data.get("s") == "ok" and data.get("t"):
                df = _build_ohlcv_df(data, sym, check_vnd_unit=True)
                if not df.empty:
                    return df
    except Exception:
        pass

    return pd.DataFrame()


def fetch_ssi_basket_history(symbols: list, start_date: datetime.date, end_date: datetime.date, max_workers: int = 24,
                             progress_callback=None) -> pd.DataFrame:
    results = []
    total = len(symbols)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(fetch_ssi_symbol_history, sym, start_date, end_date): sym for sym in symbols}
        for future in as_completed(future_map):
            completed += 1
            if progress_callback and (completed % 10 == 0 or completed == total):
                progress_callback(completed, total)
            df_sym = future.result()
            if not df_sym.empty:
                results.append(df_sym)

    if not results:
        return pd.DataFrame()

    full_df = pd.concat(results, ignore_index=True)
    full_df.sort_values(by=["Ticker", "Date"], inplace=True)
    full_df.reset_index(drop=True, inplace=True)
    return full_df


class SSIRealtimeFeed:
    """
    Hybrid Realtime Engine SSI:
    - WebSocket Pushstream (wss://iboard-pushstream.ssi.com.vn/realtime): tự ghi nhận danh sách mã trực tiếp + nhận tick.
    - SSI iBoard Snapshot Polling: đồng bộ đầy đủ HOSE/HNX/UPCOM và tên doanh nghiệp gốc.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SSIRealtimeFeed, cls).__new__(cls)
                cls._instance.is_running = False
                cls._instance.ws = None
                cls._instance.ws_thread = None
                cls._instance.poll_thread = None
                cls._instance.market_data = {}
                cls._instance.ws_discovered_symbols = {}
                cls._instance.active_symbols = list(HOSE_FULL_FALLBACK)
                cls._instance.active_exchanges = ["hose"]
                cls._instance.source_name = "Đang khởi tạo..."
                cls._instance.last_sync_str = "--:--:--"
                cls._instance.data_lock = threading.Lock()
                cls._instance._stop_event = threading.Event()
        return cls._instance

    def set_symbols(self, symbols: list, basket_label: str = "HOSE"):
        if basket_label in ("HNX", "HNX30"):
            exchanges = ["hnx"]
        elif basket_label == "UPCOM":
            exchanges = ["upcom"]
        elif "HNX" in basket_label or "WS" in basket_label or "WebSocket" in basket_label:
            exchanges = ["hose", "hnx", "upcom"]
        else:
            exchanges = ["hose"]
        with self.data_lock:
            if symbols:
                self.active_symbols = list(dict.fromkeys(symbols))
            self.active_exchanges = exchanges

    def _record_ws_symbol(self, ticker: str, company_name: str = ""):
        ticker = str(ticker).strip().upper()
        if is_valid_vn_ticker(ticker):
            with self.data_lock:
                if ticker not in self.ws_discovered_symbols or (company_name and not self.ws_discovered_symbols[ticker]):
                    self.ws_discovered_symbols[ticker] = company_name

    def get_ws_discovered_symbols(self) -> dict:
        with self.data_lock:
            return dict(self.ws_discovered_symbols)

    def discover_ws_symbols(self, wait_seconds: float = 3.5) -> dict:
        """Kết nối WebSocket SSI để thu thập trực tiếp danh sách mã đang chạy trên luồng Pushstream."""
        existing = self.get_ws_discovered_symbols()
        if len(existing) >= 10:
            return existing

        was_running = self.is_running
        if not was_running:
            self.start()

        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if len(self.get_ws_discovered_symbols()) >= 30:
                break
            time.sleep(0.25)

        result = self.get_ws_discovered_symbols()
        if not was_running:
            self.stop()
        return result

    def _normalize_and_store(
            self,
            ticker: str,
            price: float,
            vol: float,
            high: float,
            low: float,
            open_p: float = 0.0,
            date_obj=None,
            is_vnd_unit: bool = True
    ):
        if price <= 0:
            return
        ticker = str(ticker).strip().upper()
        if ticker in ["VN-INDEX", "VNINDEX", "10"]:
            ticker = "VNINDEX"
        elif not is_valid_vn_ticker(ticker):
            return

        if ticker != "VNINDEX" and is_vnd_unit:
            price = price / 1000.0
            high = high / 1000.0 if high > 0 else price
            low = low / 1000.0 if low > 0 else price
            open_p = open_p / 1000.0 if open_p > 0 else price

        high = max(high, price) if high > 0 else price
        low = min(low, price) if low > 0 else price
        open_p = open_p if open_p > 0 else price

        if date_obj is None:
            date_obj = pd.Timestamp(get_vn_today())

        with self.data_lock:
            self.market_data[ticker] = {
                "price": round(price, 2),
                "volume": float(vol),
                "high": round(high, 2),
                "low": round(low, 2),
                "open": round(open_p, 2),
                "date": pd.Timestamp(date_obj).normalize(),
                "updated_at": time.time()
            }

    def _poll_ssi_iboard_snapshot(self) -> int:
        with self.data_lock:
            exchanges = list(self.active_exchanges)
        urls = [
            f"https://iboard-query.ssi.com.vn/stock/exchange/{ex}?boardId=MAIN"
            for ex in exchanges
        ]
        sess = _get_http_session()
        count = 0
        for url in urls:
            if not self.is_running:
                break
            try:
                resp = sess.get(url, headers=SSI_HEADERS, timeout=4)
                if resp.status_code == 200:
                    payload = resp.json()
                    items = payload.get("data", []) if isinstance(payload, dict) else []
                    if isinstance(items, list) and len(items) > 0:
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            sym = item.get("stockSymbol") or item.get("sym") or item.get("code")
                            if not sym or not is_valid_vn_ticker(sym):
                                continue

                            matched_price = float(item.get("matchedPrice") or item.get("lastPrice") or 0)
                            vol = float(item.get("nmTotalTradedQty") or item.get("totalVol") or 0)
                            if matched_price <= 0 or vol <= 0:
                                continue

                            high = float(item.get("highest") or item.get("highPrice") or matched_price)
                            low = float(item.get("lowest") or item.get("lowPrice") or matched_price)
                            open_p = float(item.get("openPrice") or matched_price)

                            raw_date = str(item.get("tradingDate") or "").strip()
                            if len(raw_date) == 8 and raw_date.isdigit():
                                dt_obj = pd.to_datetime(raw_date, format="%Y%m%d")
                            else:
                                dt_obj = pd.Timestamp(get_vn_today())

                            self._normalize_and_store(
                                ticker=sym,
                                price=matched_price,
                                vol=vol,
                                high=high,
                                low=low,
                                open_p=open_p,
                                date_obj=dt_obj,
                                is_vnd_unit=True
                            )
                            count += 1
            except Exception:
                continue
        return count

    def _fetch_single_intraday_vnd(self, sym: str):
        to_ts = int(time.time())
        from_ts = to_ts - (7 * 86400)
        url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={sym}&from={from_ts}&to={to_ts}"
        try:
            r = _get_http_session().get(url, headers={"Referer": "https://dchart.vndirect.com.vn/"}, timeout=4)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, dict) and d.get("s") == "ok" and d.get("t") and d.get("c"):
                    price = float(d["c"][-1])
                    if price <= 0:
                        return False
                    last_dt = pd.to_datetime(int(d["t"][-1]) + 25200, unit="s").normalize()
                    self._normalize_and_store(
                        ticker=sym,
                        price=price,
                        vol=float(d["v"][-1]) if d.get("v") else 0.0,
                        high=float(d["h"][-1]) if d.get("h") else price,
                        low=float(d["l"][-1]) if d.get("l") else price,
                        open_p=float(d["o"][-1]) if d.get("o") else price,
                        date_obj=last_dt,
                        is_vnd_unit=False
                    )
                    return True
        except Exception:
            pass
        return False

    def _poll_vnd_intraday_batch(self) -> int:
        with self.data_lock:
            targets = ["VNINDEX"] + list(self.active_symbols)
        updated = 0
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(self._fetch_single_intraday_vnd, s) for s in targets]
            for f in as_completed(futures):
                if not self.is_running:
                    break
                if f.result():
                    updated += 1
        return updated

    def _run_polling_worker(self):
        while self.is_running and not self._stop_event.is_set():
            try:
                self._fetch_single_intraday_vnd("VNINDEX")
                ssi_cnt = self._poll_ssi_iboard_snapshot()
                if ssi_cnt > 10:
                    self.source_name = "SSI iBoard Live Stream"
                    self.last_sync_str = get_vn_now().strftime("%H:%M:%S")
                    self._stop_event.wait(3)
                else:
                    vnd_cnt = self._poll_vnd_intraday_batch()
                    if vnd_cnt > 0:
                        self.source_name = "Intraday Realtime (SSI/VND Hybrid)"
                        self.last_sync_str = get_vn_now().strftime("%H:%M:%S")
                    self._stop_event.wait(5)
            except Exception:
                self._stop_event.wait(3)

    def on_message(self, ws, message):
        try:
            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="ignore")

            # Hỗ trợ cả định dạng JSON lẫn định dạng chuỗi phân cách '|' của SSI Pushstream
            if isinstance(message, str) and message.startswith("S#"):
                parts = message.split("|")
                if parts:
                    candidate = parts[0].replace("S#", "").strip().upper()
                    if is_valid_vn_ticker(candidate):
                        self._record_ws_symbol(candidate)
                    elif len(parts) > 1 and is_valid_vn_ticker(parts[1]):
                        self._record_ws_symbol(parts[1])
                return

            data = json.loads(message)
            payload = data.get("data", data)
            items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])

            for item in items:
                if not isinstance(item, dict):
                    continue
                ticker = item.get("sym") or item.get("stockSymbol") or item.get("symbol") or item.get("indexId")
                if not ticker:
                    continue

                comp_name = str(item.get("companyNameVi") or item.get("companyName") or "").strip()
                self._record_ws_symbol(ticker, comp_name)

                if not is_vn_market_hours():
                    continue

                raw_price = float(
                    item.get("lastPrice") or item.get("matchedPrice") or item.get("matchPrice")
                    or item.get("price") or item.get("indexValue") or 0
                )
                vol = float(item.get("totalVol") or item.get("nmTotalTradedQty") or item.get("totalVolume") or 0)
                high = float(item.get("highPrice") or item.get("highest") or raw_price)
                low = float(item.get("lowPrice") or item.get("lowest") or raw_price)
                if raw_price > 0 and vol > 0:
                    self._normalize_and_store(ticker, raw_price, vol, high, low, is_vnd_unit=True)
                    self.source_name = "SSI Pushstream WSS"
                    self.last_sync_str = get_vn_now().strftime("%H:%M:%S")
        except Exception:
            pass

    def on_open(self, ws):
        try:
            sub_msg = {"type": "sub", "ads": "all"}
            ws.send(json.dumps(sub_msg))
        except Exception:
            pass

    def _run_socket(self):
        ws_url = "wss://iboard-pushstream.ssi.com.vn/realtime"
        headers = [
            "Origin: https://iboard.ssi.com.vn",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]
        while self.is_running and not self._stop_event.is_set():
            try:
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    header=headers,
                    on_open=self.on_open,
                    on_message=self.on_message
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception:
                pass
            self._stop_event.wait(5)

    def start(self, symbols=None, basket_label: str = "HOSE"):
        if symbols:
            self.set_symbols(symbols, basket_label=basket_label)
        with self._lock:
            if not self.is_running:
                self._stop_event.clear()
                self.is_running = True
                if self.poll_thread is None or not self.poll_thread.is_alive():
                    self.poll_thread = threading.Thread(target=self._run_polling_worker, daemon=True)
                    self.poll_thread.start()
                if self.ws_thread is None or not self.ws_thread.is_alive():
                    self.ws_thread = threading.Thread(target=self._run_socket, daemon=True)
                    self.ws_thread.start()

    def stop(self):
        with self._lock:
            self.is_running = False
            self._stop_event.set()
            if self.ws:
                try:
                    self.ws.close()
                except Exception:
                    pass

    def get_all_realtime(self):
        with self.data_lock:
            return dict(self.market_data)


feed = SSIRealtimeFeed()
