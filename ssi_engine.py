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


# Tái sử dụng kết nối TCP/TLS giúp tải toàn sàn nhanh hơn 3-5 lần
HTTP_SESSION = requests.Session()
_adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=1)
HTTP_SESSION.mount("https://", _adapter)
HTTP_SESSION.mount("http://", _adapter)
HTTP_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
})


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

BASKETS = {
    "🔥 TOÀN SÀN HOSE (~400 Cổ phiếu)": "ALL_HOSE",
    "⚡ TOÀN BỘ 3 SÀN (HOSE + HNX + UPCOM)": "ALL_ALL",
    "VN30 (30 Cổ phiếu vốn hóa lớn HOSE)": [
        "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
        "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
        "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
    ],
    "Rổ VN100 (Top 100 HOSE)": [
        "AAA", "ACB", "ANV", "ASM", "BCG", "BCM", "BFC", "BID", "BMP", "BSI",
        "BVH", "BWE", "CII", "CMG", "CTD", "CTG", "CTR", "CTS", "DBC", "DCM",
        "DGC", "DGW", "DIG", "DPM", "DSE", "DXG", "DXS", "EIB", "EVF", "FPT",
        "FRT", "FTS", "GAS", "GEX", "GMD", "GVR", "HAG", "HAH", "HCM", "HDB",
        "HDC", "HDG", "HHV", "HPG", "HSG", "HT1", "IMP", "KBC", "KDC", "KDH",
        "KOS", "LPB", "MBB", "MSB", "MSN", "MWG", "NAB", "NKG", "NLG", "NT2",
        "NVL", "OCB", "ORS", "PAN", "PC1", "PDR", "PET", "PHR", "PLX", "PNJ",
        "POW", "PPC", "PTB", "PVD", "PVT", "REE", "SAB", "SAM", "SBT", "SCS",
        "SHB", "SJS", "SSB", "SSI", "STB", "SZC", "TCB", "TCH", "TLG", "TPB",
        "VCB", "VCG", "VCI", "VGC", "VHC", "VHM", "VIB", "VIC", "VIX", "VJC",
        "VND", "VNM", "VPB", "VPI", "VRE", "VSC", "VTP"
    ],
    "Nhóm Trụ & Thanh Khoản (Bank / Chứng / Thép / BĐS)": [
        "SSI", "VND", "VCI", "HCM", "FTS", "BSI", "CTS", "MBS", "SHS", "ORS",
        "VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "HDB", "STB", "LPB", "SHB",
        "HPG", "HSG", "NKG", "VGS", "VHM", "VIC", "VRE", "NVL", "PDR", "DIG", "DXG", "KDH", "NLG", "KBC"
    ]
}


def get_market_symbols(market_type="HOSE"):
    try:
        if market_type == "HOSE":
            url = "https://finfo-api.vndirect.com.vn/v4/stocks?q=type:stock~status:listed~floor:HOSE&size=3000"
        else:
            url = "https://finfo-api.vndirect.com.vn/v4/stocks?q=type:stock~status:listed~floor:HOSE,HNX,UPCOM&size=3000"

        resp = HTTP_SESSION.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            symbols = [
                item.get("code", "").strip().upper()
                for item in data
                if len(item.get("code", "").strip()) == 3 and item.get("code", "").strip().isalpha()
            ]
            if len(symbols) > 200:
                return sorted(list(set(symbols)))
    except Exception:
        pass

    return sorted(list(set(HOSE_FULL_FALLBACK)))


def fetch_ssi_symbol_history(symbol: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Tải lịch sử OHLCV chuẩn hóa múi giờ Việt Nam (UTC+7) và đơn vị Nghìn đồng"""
    sym = symbol.upper()
    buffer_start = start_date - datetime.timedelta(days=330)
    from_ts = int(datetime.datetime.combine(buffer_start, datetime.time.min, tzinfo=VN_TZ).timestamp())
    to_ts = int(datetime.datetime.combine(end_date, datetime.time.max, tzinfo=VN_TZ).timestamp())

    vnd_url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={sym}&from={from_ts}&to={to_ts}"
    try:
        resp = HTTP_SESSION.get(vnd_url, headers={"Referer": "https://dchart.vndirect.com.vn/"}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("s") == "ok" and data.get("t"):
                vn_dates = pd.to_datetime(pd.Series(data["t"], dtype="int64") + 25200, unit="s").dt.normalize()
                df = pd.DataFrame({
                    "Date": vn_dates,
                    "Ticker": sym,
                    "Open": pd.to_numeric(data["o"], errors="coerce"),
                    "High": pd.to_numeric(data["h"], errors="coerce"),
                    "Low": pd.to_numeric(data["l"], errors="coerce"),
                    "Close": pd.to_numeric(data["c"], errors="coerce"),
                    "Volume": pd.to_numeric(data["v"], errors="coerce")
                })
                df.drop_duplicates(subset=["Date"], keep="last", inplace=True)
                return df
    except Exception:
        pass

    ssi_sym = "VN-INDEX" if sym == "VNINDEX" else sym
    ssi_url = f"https://iboard-api.ssi.com.vn/statistics/charts/history?resolution=1D&symbol={ssi_sym}&from={from_ts}&to={to_ts}"
    try:
        resp = HTTP_SESSION.get(ssi_url, headers={"Referer": "https://iboard.ssi.com.vn/"}, timeout=6)
        if resp.status_code == 200:
            data = resp.json().get("data", resp.json())
            if data.get("s") == "ok" and data.get("t"):
                vn_dates = pd.to_datetime(pd.Series(data["t"], dtype="int64") + 25200, unit="s").dt.normalize()
                df = pd.DataFrame({
                    "Date": vn_dates,
                    "Ticker": sym,
                    "Open": pd.to_numeric(data["o"], errors="coerce"),
                    "High": pd.to_numeric(data["h"], errors="coerce"),
                    "Low": pd.to_numeric(data["l"], errors="coerce"),
                    "Close": pd.to_numeric(data["c"], errors="coerce"),
                    "Volume": pd.to_numeric(data["v"], errors="coerce")
                })
                if sym != "VNINDEX" and df["Close"].median() > 300:
                    for col in ["Open", "High", "Low", "Close"]:
                        df[col] = df[col] / 1000.0
                df.drop_duplicates(subset=["Date"], keep="last", inplace=True)
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
    Hybrid Realtime Engine chuẩn hóa UTC+7, chống Zombie Thread và hỗ trợ cả 3 sàn.
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
                cls._instance.active_symbols = list(HOSE_FULL_FALLBACK)
                cls._instance.source_name = "Đang khởi tạo..."
                cls._instance.last_sync_str = "--:--:--"
                cls._instance.data_lock = threading.Lock()
        return cls._instance

    def set_symbols(self, symbols: list):
        if symbols:
            self.active_symbols = list(set(symbols))

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
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://iboard.ssi.com.vn",
            "Referer": "https://iboard.ssi.com.vn/"
        }
        urls = ["https://iboard-query.ssi.com.vn/stock/exchange/hose?boardId=MAIN"]
        if len(self.active_symbols) > 450:
            urls.extend([
                "https://iboard-query.ssi.com.vn/stock/exchange/hnx?boardId=MAIN",
                "https://iboard-query.ssi.com.vn/stock/exchange/upcom?boardId=MAIN"
            ])

        count = 0
        for url in urls:
            try:
                resp = HTTP_SESSION.get(url, headers=headers, timeout=4)
                if resp.status_code == 200:
                    items = resp.json().get("data", [])
                    if isinstance(items, list) and len(items) > 0:
                        for item in items:
                            sym = item.get("stockSymbol") or item.get("sym") or item.get("code")
                            if not sym:
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
            r = HTTP_SESSION.get(url, headers={"Referer": "https://dchart.vndirect.com.vn/"}, timeout=4)
            if r.status_code == 200:
                d = r.json()
                if d.get("s") == "ok" and d.get("t"):
                    last_dt = pd.to_datetime(int(d["t"][-1]) + 25200, unit="s").normalize()
                    self._normalize_and_store(
                        ticker=sym,
                        price=float(d["c"][-1]),
                        vol=float(d["v"][-1]),
                        high=float(d["h"][-1]),
                        low=float(d["l"][-1]),
                        open_p=float(d["o"][-1]),
                        date_obj=last_dt,
                        is_vnd_unit=False
                    )
                    return True
        except Exception:
            pass
        return False

    def _poll_vnd_intraday_batch(self) -> int:
        targets = ["VNINDEX"] + self.active_symbols
        updated = 0
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(self._fetch_single_intraday_vnd, s) for s in targets]
            for f in as_completed(futures):
                if f.result():
                    updated += 1
        return updated

    def _run_polling_worker(self):
        while self.is_running:
            try:
                self._fetch_single_intraday_vnd("VNINDEX")
                ssi_cnt = self._poll_ssi_iboard_snapshot()
                if ssi_cnt > 10:
                    self.source_name = "SSI iBoard Live Stream"
                    self.last_sync_str = get_vn_now().strftime("%H:%M:%S")
                    time.sleep(3)
                else:
                    vnd_cnt = self._poll_vnd_intraday_batch()
                    if vnd_cnt > 0:
                        self.source_name = "Intraday Realtime (SSI/VND Hybrid)"
                        self.last_sync_str = get_vn_now().strftime("%H:%M:%S")
                    time.sleep(5)
            except Exception:
                time.sleep(3)

    def on_message(self, ws, message):
        if not is_vn_market_hours():
            return
        try:
            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="ignore")
            data = json.loads(message)
            payload = data.get("data", data)
            if isinstance(payload, dict):
                ticker = payload.get("sym") or payload.get("stockSymbol") or payload.get("symbol") or payload.get(
                    "indexId")
                if ticker:
                    raw_price = float(payload.get("lastPrice") or payload.get("matchedPrice") or payload.get(
                        "matchPrice") or payload.get("price") or payload.get("indexValue") or 0)
                    vol = float(
                        payload.get("totalVol") or payload.get("nmTotalTradedQty") or payload.get("totalVolume") or 0)
                    high = float(payload.get("highPrice") or payload.get("highest") or raw_price)
                    low = float(payload.get("lowPrice") or payload.get("lowest") or raw_price)
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
        while self.is_running:
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
            time.sleep(5)

    def start(self, symbols=None):
        if symbols:
            self.set_symbols(symbols)
        with self._lock:
            if not self.is_running:
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
            if self.ws:
                try:
                    self.ws.close()
                except Exception:
                    pass

    def get_all_realtime(self):
        with self.data_lock:
            return dict(self.market_data)


feed = SSIRealtimeFeed()
