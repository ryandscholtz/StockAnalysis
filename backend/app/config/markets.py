"""
Fidelity-supported markets, ticker symbology, and currency inference.

Fidelity International Trading covers US exchanges plus 25 foreign markets.
Trades are quoted as ROOT:CC (e.g. SAP:DE, NPN:ZA). This module converts that
symbology to Yahoo Finance suffixes used throughout the app, and defines the
Explore catalog for those markets.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Fidelity International Trading — country code → Yahoo suffix
# https://www.fidelity.com/stock-trading/faqs-international
# ---------------------------------------------------------------------------

FIDELITY_COUNTRY_TO_YAHOO_SUFFIX: Dict[str, str] = {
    "AU": ".AX",   # Australia — ASX
    "AT": ".VI",   # Austria — Vienna
    "BE": ".BR",   # Belgium — Euronext Brussels
    "CA": ".TO",   # Canada — TSX (Venture uses .V; default to TSX)
    "DK": ".CO",   # Denmark — Nasdaq Copenhagen
    "FI": ".HE",   # Finland — Nasdaq Helsinki
    "FR": ".PA",   # France — Euronext Paris
    "DE": ".DE",   # Germany — Xetra / Frankfurt
    "GR": ".AT",   # Greece — Athens
    "HK": ".HK",   # Hong Kong — HKEX
    "IE": ".IR",   # Ireland — Euronext Dublin
    "IT": ".MI",   # Italy — Borsa Italiana
    "JP": ".T",    # Japan — Tokyo
    "MX": ".MX",   # Mexico — BMV
    "NL": ".AS",   # Netherlands — Euronext Amsterdam
    "NZ": ".NZ",   # New Zealand — NZX
    "NO": ".OL",   # Norway — Oslo
    "PL": ".WA",   # Poland — Warsaw
    "PT": ".LS",   # Portugal — Euronext Lisbon
    "SG": ".SI",   # Singapore — SGX
    "ZA": ".JO",   # South Africa — JSE
    "ES": ".MC",   # Spain — Bolsa de Madrid
    "SE": ".ST",   # Sweden — Nasdaq Stockholm
    "CH": ".SW",   # Switzerland — SIX
    "GB": ".L",    # United Kingdom — LSE
    "US": "",      # United States — no suffix
}

FIDELITY_COUNTRIES = frozenset(FIDELITY_COUNTRY_TO_YAHOO_SUFFIX.keys())

# MarketStack MIC → Yahoo Finance suffix
MIC_TO_YAHOO_SUFFIX: Dict[str, str] = {
    "XNYS": "",
    "XNAS": "",
    "XASE": "",
    "XTSE": ".TO",
    "XTSX": ".V",
    "XMEX": ".MX",
    "XLON": ".L",
    "XETR": ".DE",
    "XPAR": ".PA",
    "XAMS": ".AS",
    "XMIL": ".MI",
    "XMAD": ".MC",
    "XSTO": ".ST",
    "XCSE": ".CO",
    "XOSL": ".OL",
    "XBRU": ".BR",
    "XLIS": ".LS",
    "XWAR": ".WA",
    "XWBO": ".VI",
    "XHEL": ".HE",
    "XSWX": ".SW",
    "XATH": ".AT",
    "XDUB": ".IR",
    "XASX": ".AX",
    "XHKG": ".HK",
    "XTKS": ".T",
    "XSES": ".SI",
    "XNZE": ".NZ",
    "XJSE": ".JO",
}

# MarketStack-style "TICKER.XMIC" suffix → Yahoo suffix
MARKETSTACK_SUFFIX_TO_YAHOO: Dict[str, str] = {
    ".XJSE": ".JO",
    ".XATH": ".AT",
    ".XDUB": ".IR",
    ".XNZE": ".NZ",
    ".XTSX": ".V",
    ".XTSE": ".TO",
    ".XLON": ".L",
    ".XETR": ".DE",
    ".XPAR": ".PA",
    ".XAMS": ".AS",
    ".XBRU": ".BR",
    ".XLIS": ".LS",
    ".XMIL": ".MI",
    ".XMAD": ".MC",
    ".XSTO": ".ST",
    ".XCSE": ".CO",
    ".XHEL": ".HE",
    ".XOSL": ".OL",
    ".XWAR": ".WA",
    ".XWBO": ".VI",
    ".XSWX": ".SW",
    ".XASX": ".AX",
    ".XHKG": ".HK",
    ".XTKS": ".T",
    ".XSES": ".SI",
    ".XMEX": ".MX",
    ".XNYS": "",
    ".XNAS": "",
    ".XASE": "",
}

# Yahoo suffixes used by Fidelity markets (longest first so .IR beats .I, .AT beats .T)
YAHOO_SUFFIXES_LONGEST_FIRST: Tuple[str, ...] = (
    ".XJSE", ".JO",
    ".IR", ".AT", ".NZ", ".AX", ".HK", ".TO", ".MX",
    ".PA", ".DE", ".AS", ".BR", ".MI", ".MC", ".LS",
    ".SW", ".ST", ".CO", ".OL", ".HE", ".WA", ".VI",
    ".SI", ".L", ".V", ".T",
    ".SS", ".SZ", ".KS", ".KQ", ".TW", ".NS", ".BO",
    ".SA", ".SR", ".TA", ".JK",
)

# Suffixes that identify a non-US listing (used to skip SEC EDGAR)
INTERNATIONAL_YAHOO_SUFFIXES: Tuple[str, ...] = tuple(
    s for s in YAHOO_SUFFIXES_LONGEST_FIRST if s not in (".XJSE",)
)

TICKER_SUFFIX_TO_CURRENCY: Dict[str, str] = {
    ".L": "GBP", ".LN": "GBP",
    ".PA": "EUR", ".DE": "EUR", ".F": "EUR", ".AS": "EUR", ".BR": "EUR",
    ".MI": "EUR", ".MC": "EUR", ".LS": "EUR", ".IR": "EUR", ".AT": "EUR",
    ".VI": "EUR", ".HE": "EUR",
    ".SW": "CHF",
    ".AX": "AUD",
    ".NZ": "NZD",
    ".TO": "CAD", ".V": "CAD", ".CN": "CAD",
    ".T": "JPY",
    ".HK": "HKD",
    ".SI": "SGD",
    ".MX": "MXN",
    ".CO": "DKK",
    ".OL": "NOK",
    ".ST": "SEK",
    ".WA": "PLN",
    ".JO": "ZAR", ".XJSE": "ZAC", ".JSE": "ZAR", ".JNB": "ZAR",
    ".KS": "KRW", ".KQ": "KRW",
    ".BO": "INR", ".NS": "INR",
    ".SA": "BRL",
    ".SS": "CNY", ".SZ": "CNY",
    ".JK": "IDR",
}

# Bare suffixes (no leading dot) for hyphen→dot normalisation (MRF-JO → MRF.JO)
EXCHANGE_SUFFIX_TOKENS: Tuple[str, ...] = tuple(
    sorted(
        {s.lstrip(".").upper() for s in YAHOO_SUFFIXES_LONGEST_FIRST},
        key=len,
        reverse=True,
    )
)

GOOGLE_FINANCE_EXCHANGE_MAP: Dict[str, str] = {
    ".JO": "JSE",
    ".L": "LON",
    ".TO": "TSE",
    ".PA": "EPA",
    ".DE": "ETR",
    ".HK": "HKG",
    ".SS": "SHA",
    ".SZ": "SHE",
    ".T": "TYO",
    ".AS": "AMS",
    ".BR": "EBR",   # Euronext Brussels (Yahoo .SA is Brazil)
    ".MX": "MEX",
    ".SA": "BVMF",  # Brazil B3
    ".SW": "SWX",
    ".VI": "VIE",
    ".ST": "STO",
    ".OL": "OSL",
    ".CO": "CPH",
    ".HE": "HEL",
    ".LS": "LIS",
    ".MC": "BME",
    ".MI": "BIT",
    ".WA": "WSE",
    ".V": "CVE",    # TSX Venture
    ".AT": "ATH",
    ".IR": "ISE",
    ".NZ": "NZE",
    ".AX": "ASX",
    ".SI": "SGX",
    ".TW": "TPE",
    ".NS": "NSE",
    ".TA": "TLV",
}


def _split_suffix(ticker: str) -> Tuple[str, str]:
    """Return (base, suffix_with_dot_or_empty) using longest matching suffix."""
    upper = ticker.upper()
    for suffix in YAHOO_SUFFIXES_LONGEST_FIRST:
        if upper.endswith(suffix):
            return ticker[: -len(suffix)], suffix
    return ticker, ""


def to_yahoo_symbol(ticker: str) -> str:
    """Convert MarketStack MIC-style suffixes (BEL.XJSE) to Yahoo (BEL.JO)."""
    if not ticker:
        return ticker
    upper = ticker.upper()
    for mic_suffix, yahoo_suffix in MARKETSTACK_SUFFIX_TO_YAHOO.items():
        if upper.endswith(mic_suffix):
            base = ticker[: -len(mic_suffix)]
            return base + yahoo_suffix if yahoo_suffix else base
    return ticker


def normalize_ticker(ticker: str) -> str:
    """
    Normalise a user-entered symbol to Yahoo Finance form.

    Accepts:
      - Yahoo: SAP.DE, NPN.JO, AAPL
      - Fidelity: SAP:DE, NPN:ZA, 7203:JP
      - Hyphen exchange suffix: MRF-JO, SAP-DE
    """
    if not ticker:
        return ticker
    raw = ticker.strip().upper()

    # Fidelity ROOT:CC
    if ":" in raw:
        root, _, cc = raw.partition(":")
        root, cc = root.strip(), cc.strip()
        if root and cc in FIDELITY_COUNTRY_TO_YAHOO_SUFFIX:
            return root + FIDELITY_COUNTRY_TO_YAHOO_SUFFIX[cc]
        return raw

    # Hyphenated exchange suffix (MRF-JO → MRF.JO), not class shares like BRK-B
    for token in EXCHANGE_SUFFIX_TOKENS:
        if raw.endswith(f"-{token}") and len(raw) > len(token) + 1:
            return raw[: -(len(token) + 1)] + "." + token

    return to_yahoo_symbol(raw)


def is_international_ticker(ticker: str) -> bool:
    """True when the ticker has a non-US exchange suffix."""
    if not ticker:
        return False
    upper = normalize_ticker(ticker).upper()
    return any(upper.endswith(s) for s in INTERNATIONAL_YAHOO_SUFFIXES)


def infer_currency(ticker: Optional[str] = None, exchange: Optional[str] = None) -> Optional[str]:
    """Infer ISO currency from exchange name or Yahoo/Fidelity ticker suffix."""
    if exchange:
        ex = exchange.upper()
        hints = (
            ("LSE", "GBP"), ("LONDON", "GBP"), ("XLON", "GBP"),
            ("PARIS", "EUR"), ("XPAR", "EUR"), ("EURONEXT", "EUR"),
            ("FRANKFURT", "EUR"), ("XETRA", "EUR"), ("XETR", "EUR"),
            ("AMSTERDAM", "EUR"), ("XAMS", "EUR"),
            ("BRUSSELS", "EUR"), ("XBRU", "EUR"),
            ("MILAN", "EUR"), ("XMIL", "EUR"), ("BIT", "EUR"),
            ("MADRID", "EUR"), ("XMAD", "EUR"), ("BME", "EUR"),
            ("LISBON", "EUR"), ("XLIS", "EUR"),
            ("ATHENS", "EUR"), ("ATHEX", "EUR"), ("XATH", "EUR"),
            ("DUBLIN", "EUR"), ("ISE", "EUR"), ("XDUB", "EUR"),
            ("VIENNA", "EUR"), ("XWBO", "EUR"),
            ("HELSINKI", "EUR"), ("XHEL", "EUR"),
            ("SWISS", "CHF"), ("SIX", "CHF"), ("XSWX", "CHF"),
            ("AUSTRALIA", "AUD"), ("ASX", "AUD"), ("XASX", "AUD"),
            ("NEW ZEALAND", "NZD"), ("NZX", "NZD"), ("XNZE", "NZD"),
            ("TORONTO", "CAD"), ("TSX", "CAD"), ("XTSE", "CAD"), ("VENTURE", "CAD"),
            ("TOKYO", "JPY"), ("TSE", "JPY"), ("XTKS", "JPY"),
            ("HONG KONG", "HKD"), ("HKEX", "HKD"), ("XHKG", "HKD"),
            ("SINGAPORE", "SGD"), ("SGX", "SGD"), ("XSES", "SGD"),
            ("JOHANNESBURG", "ZAR"), ("JSE", "ZAR"), ("XJSE", "ZAR"),
            ("MEXICO", "MXN"), ("MEXICAN", "MXN"), ("BMV", "MXN"), ("XMEX", "MXN"),
            ("COPENHAGEN", "DKK"), ("XCSE", "DKK"),
            ("OSLO", "NOK"), ("XOSL", "NOK"),
            ("STOCKHOLM", "SEK"), ("XSTO", "SEK"),
            ("WARSAW", "PLN"), ("GPW", "PLN"), ("XWAR", "PLN"),
            ("KOREA", "KRW"), ("KRX", "KRW"),
            ("INDIA", "INR"), ("NSE", "INR"), ("BSE", "INR"),
        )
        for needle, currency in hints:
            if needle in ex or ex == needle:
                return currency

    if ticker:
        original = ticker.strip().upper()
        for suffix, currency in sorted(TICKER_SUFFIX_TO_CURRENCY.items(), key=lambda kv: len(kv[0]), reverse=True):
            if original.endswith(suffix):
                return currency
        upper = normalize_ticker(ticker).upper()
        for suffix, currency in sorted(TICKER_SUFFIX_TO_CURRENCY.items(), key=lambda kv: len(kv[0]), reverse=True):
            if upper.endswith(suffix):
                return currency
    return None


# ---------------------------------------------------------------------------
# Explore catalog — Fidelity primary exchanges (screener-driven) + indices
# ---------------------------------------------------------------------------

MARKET_TICKERS: Dict[str, Dict] = {
    # ── Americas ────────────────────────────────────────────────────────────
    "NYSE": {
        "name": "NYSE",
        "description": "New York Stock Exchange – all listed companies",
        "region": "US", "continent": "Americas",
        "screener_exchange": "NYQ",
        "fidelity": True,
        "tickers": [],
    },
    "NASDAQ": {
        "name": "NASDAQ",
        "description": "NASDAQ – all listed companies",
        "region": "US", "continent": "Americas",
        "screener_exchange": "NMS",
        "fidelity": True,
        "tickers": [],
    },
    "AMEX": {
        "name": "NYSE American",
        "description": "NYSE American (AMEX) – all listed companies",
        "region": "US", "continent": "Americas",
        "screener_exchange": "ASE",
        "fidelity": True,
        "tickers": ["GDX", "GDXJ", "UNG", "USO", "UVXY", "VXX", "PEO", "NGD"],
    },
    "TSX": {
        "name": "TSX",
        "description": "Toronto Stock Exchange – all listed Canadian companies",
        "region": "CA", "continent": "Americas",
        "screener_exchange": "TOR",
        "yahoo_suffix": ".TO",
        "exchange_mic": "XTSE",
        "fidelity": True,
        "tickers": [
            "RY.TO", "TD.TO", "BNS.TO", "BMO.TO", "CM.TO", "ENB.TO", "CNR.TO",
            "TRP.TO", "SU.TO", "ABX.TO", "MFC.TO", "SLF.TO", "CP.TO", "BCE.TO",
            "T.TO", "CNQ.TO", "PPL.TO", "ATD.TO", "GWO.TO", "AEM.TO", "SHOP.TO",
        ],
    },
    "TSXV": {
        "name": "TSX Venture",
        "description": "TSX Venture Exchange – all listed Canadian venture companies",
        "region": "CA", "continent": "Americas",
        "screener_exchange": "VAN",
        "yahoo_suffix": ".V",
        "exchange_mic": "XTSX",
        "fidelity": True,
        "tickers": [
            "HIVE.V", "BITF.V", "LGD.V", "SKE.V", "NFG.V", "VLE.V", "GWM.V",
        ],
    },
    "BMV": {
        "name": "Bolsa Mexicana",
        "description": "Bolsa Mexicana de Valores – all listed Mexican companies",
        "region": "MX", "continent": "Americas",
        "screener_exchange": "MEX",
        "yahoo_suffix": ".MX",
        "exchange_mic": "XMEX",
        "fidelity": True,
        "tickers": [
            "AMXL.MX", "WALMEXV.MX", "FEMSAUBD.MX", "GFNORTEO.MX", "CEMEXCPO.MX",
            "BIMBOA.MX", "GMEXICOB.MX", "GAPB.MX", "ASURB.MX", "AC.MX",
        ],
    },
    "SP500": {
        "name": "S&P 500",
        "description": "S&P 500 – largest US public companies by market cap",
        "region": "US", "continent": "Americas",
        "fidelity": True,
        "tickers": [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "JPM",
            "V", "UNH", "XOM", "MA", "AVGO", "JNJ", "HD", "PG", "COST", "ABBV",
            "MRK", "CVX", "KO", "WMT", "PEP", "BAC", "CRM", "NFLX", "TMO", "ORCL",
            "AMD", "ABT", "ACN", "LIN", "MCD", "DHR", "CSCO", "TXN", "NEE", "PM",
            "ADBE", "WFC", "MS", "RTX", "INTU", "DIS", "BMY", "UPS", "AMGN", "LOW",
        ],
    },
    "NASDAQ100": {
        "name": "NASDAQ 100",
        "description": "NASDAQ 100 – top 100 non-financial NASDAQ companies",
        "region": "US", "continent": "Americas",
        "fidelity": True,
        "tickers": [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "AVGO", "COST",
            "NFLX", "TMUS", "AMD", "CSCO", "ADBE", "PEP", "TXN", "QCOM", "HON", "INTU",
            "AMAT", "AMGN", "ISRG", "MU", "BKNG", "LRCX", "REGN", "ADI", "VRTX", "PANW",
            "KLAC", "SNPS", "MRVL", "CDNS", "GILD", "SBUX", "ADP", "MDLZ", "PYPL", "CTAS",
            "ABNB", "ORLY", "FTNT", "MELI", "MNST", "CRWD", "PCAR", "KDP", "INTC", "ASML",
        ],
    },
    "DOW30": {
        "name": "Dow Jones 30",
        "description": "Dow Jones Industrial Average – 30 blue-chip stocks",
        "region": "US", "continent": "Americas",
        "fidelity": True,
        "tickers": [
            "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
            "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
            "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT",
        ],
    },
    # ── Europe ──────────────────────────────────────────────────────────────
    "LSE": {
        "name": "London Stock Exchange",
        "description": "London Stock Exchange – all listed UK companies",
        "region": "GB", "continent": "Europe",
        "screener_exchange": "LSE",
        "yahoo_suffix": ".L",
        "exchange_mic": "XLON",
        "fidelity": True,
        "tickers": [
            "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "BATS.L", "GSK.L", "RIO.L",
            "DGE.L", "REL.L", "BA.L", "LSEG.L", "PRU.L", "NG.L", "VOD.L", "LLOY.L",
            "BARC.L", "NWG.L", "STAN.L", "AAL.L",
        ],
    },
    "XETRA": {
        "name": "Frankfurt (XETRA)",
        "description": "Deutsche Börse XETRA – all listed German companies",
        "region": "DE", "continent": "Europe",
        "screener_exchange": "GER",
        "yahoo_suffix": ".DE",
        "exchange_mic": "XETR",
        "fidelity": True,
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "DTE.DE", "BAYN.DE", "BMW.DE",
            "VOW3.DE", "MUV2.DE", "DB1.DE", "RWE.DE", "BAS.DE", "MRK.DE", "ADS.DE",
            "IFX.DE", "DHER.DE",
        ],
    },
    "EURONEXT_PA": {
        "name": "Euronext Paris",
        "description": "Euronext Paris – all listed French companies",
        "region": "FR", "continent": "Europe",
        "screener_exchange": "PAR",
        "yahoo_suffix": ".PA",
        "exchange_mic": "XPAR",
        "fidelity": True,
        "tickers": [
            "MC.PA", "TTE.PA", "SAN.PA", "OR.PA", "AIR.PA", "SU.PA", "BNP.PA", "AI.PA",
            "KER.PA", "RMS.PA", "DSY.PA", "ACA.PA", "GLE.PA", "SAF.PA",
        ],
    },
    "EURONEXT_AM": {
        "name": "Euronext Amsterdam",
        "description": "Euronext Amsterdam – all listed Dutch companies",
        "region": "NL", "continent": "Europe",
        "screener_exchange": "AMS",
        "yahoo_suffix": ".AS",
        "exchange_mic": "XAMS",
        "fidelity": True,
        "tickers": [
            "ASML.AS", "HEIA.AS", "PHIA.AS", "ABN.AS", "ING.AS", "NN.AS", "AKZA.AS",
            "AD.AS", "WKL.AS", "RAND.AS", "IMCD.AS", "BESI.AS",
        ],
    },
    "EURONEXT_BR": {
        "name": "Euronext Brussels",
        "description": "Euronext Brussels – all listed Belgian companies",
        "region": "BE", "continent": "Europe",
        "screener_exchange": "BRU",
        "yahoo_suffix": ".BR",
        "exchange_mic": "XBRU",
        "fidelity": True,
        "tickers": [
            "ABI.BR", "UCB.BR", "SOLB.BR", "ACKB.BR", "GBLB.BR", "KBC.BR",
            "PROX.BR", "COLR.BR", "AGS.BR", "WDP.BR",
        ],
    },
    "EURONEXT_LI": {
        "name": "Euronext Lisbon",
        "description": "Euronext Lisbon – all listed Portuguese companies",
        "region": "PT", "continent": "Europe",
        "screener_exchange": "LIS",
        "yahoo_suffix": ".LS",
        "exchange_mic": "XLIS",
        "fidelity": True,
        "tickers": ["EDP.LS", "GALP.LS", "JMT.LS", "NOS.LS", "BCP.LS", "EDPR.LS", "CTT.LS"],
    },
    "EURONEXT_DU": {
        "name": "Euronext Dublin",
        "description": "Euronext Dublin – all listed Irish companies",
        "region": "IE", "continent": "Europe",
        "screener_exchange": "ISE",
        "yahoo_suffix": ".IR",
        "exchange_mic": "XDUB",
        "fidelity": True,
        "tickers": [
            "A5G.IR", "BIRG.IR", "KRZ.IR", "KRX.IR", "RYA.IR", "SK3.IR", "GL9.IR",
            "IRES.IR", "UDG.IR", "GRW.IR",
        ],
    },
    "BORSA_IT": {
        "name": "Borsa Italiana",
        "description": "Borsa Italiana – all listed Italian companies",
        "region": "IT", "continent": "Europe",
        "screener_exchange": "MIL",
        "yahoo_suffix": ".MI",
        "exchange_mic": "XMIL",
        "fidelity": True,
        "tickers": [
            "ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "STLAM.MI", "RACE.MI", "STM.MI",
            "LDO.MI", "MONC.MI", "G.MI", "SRG.MI", "TRN.MI",
        ],
    },
    "BME": {
        "name": "Bolsa de Madrid",
        "description": "Bolsa de Madrid – all listed Spanish companies",
        "region": "ES", "continent": "Europe",
        "screener_exchange": "MCE",
        "yahoo_suffix": ".MC",
        "exchange_mic": "XMAD",
        "fidelity": True,
        "tickers": [
            "ITX.MC", "SAN.MC", "BBVA.MC", "IBE.MC", "TEF.MC", "REP.MC", "AMS.MC",
            "CABK.MC", "FER.MC", "AENA.MC",
        ],
    },
    "NASDAQ_ST": {
        "name": "Nasdaq Stockholm",
        "description": "Nasdaq Stockholm – all listed Swedish companies",
        "region": "SE", "continent": "Europe",
        "screener_exchange": "STO",
        "yahoo_suffix": ".ST",
        "exchange_mic": "XSTO",
        "fidelity": True,
        "tickers": [
            "VOLV-B.ST", "ERIC-B.ST", "INVE-B.ST", "ATCO-A.ST", "HM-B.ST", "SEB-A.ST",
            "SHB-A.ST", "SWED-A.ST", "NIBE-B.ST", "SAND.ST",
        ],
    },
    "NASDAQ_CO": {
        "name": "Nasdaq Copenhagen",
        "description": "Nasdaq Copenhagen – all listed Danish companies",
        "region": "DK", "continent": "Europe",
        "screener_exchange": "CPH",
        "yahoo_suffix": ".CO",
        "exchange_mic": "XCSE",
        "fidelity": True,
        "tickers": [
            "NOVO-B.CO", "MAERSK-B.CO", "ORSTED.CO", "DSV.CO", "VWS.CO", "GMAB.CO",
            "CARL-B.CO", "COLO-B.CO", "NZYM-B.CO", "PNDORA.CO",
        ],
    },
    "NASDAQ_HE": {
        "name": "Nasdaq Helsinki",
        "description": "Nasdaq Helsinki – all listed Finnish companies",
        "region": "FI", "continent": "Europe",
        "screener_exchange": "HEL",
        "yahoo_suffix": ".HE",
        "exchange_mic": "XHEL",
        "fidelity": True,
        "tickers": [
            "NOKIA.HE", "NESTE.HE", "SAMPO.HE", "KNEBV.HE", "WRT1V.HE",
            "METSO.HE", "FORTUM.HE", "STERV.HE", "ORNBV.HE", "KESKOB.HE",
        ],
    },
    "OSLO": {
        "name": "Oslo Børs",
        "description": "Oslo Stock Exchange – all listed Norwegian companies",
        "region": "NO", "continent": "Europe",
        "screener_exchange": "OSL",
        "yahoo_suffix": ".OL",
        "exchange_mic": "XOSL",
        "fidelity": True,
        "tickers": [
            "EQNR.OL", "DNB.OL", "TEL.OL", "ORK.OL", "YAR.OL", "MOWI.OL",
            "AKRBP.OL", "NHY.OL", "AUTO.OL", "KOG.OL",
        ],
    },
    "GPW": {
        "name": "Warsaw Stock Exchange",
        "description": "Warsaw Stock Exchange – all listed Polish companies",
        "region": "PL", "continent": "Europe",
        "screener_exchange": "WSE",
        "yahoo_suffix": ".WA",
        "exchange_mic": "XWAR",
        "fidelity": True,
        "tickers": [
            "PKN.WA", "PKO.WA", "PZU.WA", "KGHM.WA", "PGE.WA", "OPL.WA",
            "CDR.WA", "LPP.WA", "PEO.WA", "DNP.WA",
        ],
    },
    "WIENER": {
        "name": "Vienna Stock Exchange",
        "description": "Vienna Stock Exchange – all listed Austrian companies",
        "region": "AT", "continent": "Europe",
        "screener_exchange": "VIE",
        "yahoo_suffix": ".VI",
        "exchange_mic": "XWBO",
        "fidelity": True,
        "tickers": ["OMV.VI", "VOE.VI", "ANDR.VI", "EBS.VI", "RBI.VI", "VIG.VI", "VER.VI"],
    },
    "SIX": {
        "name": "SIX Swiss Exchange",
        "description": "SIX Swiss Exchange – all listed Swiss companies",
        "region": "CH", "continent": "Europe",
        "screener_exchange": "ZRH",
        "yahoo_suffix": ".SW",
        "exchange_mic": "XSWX",
        "fidelity": True,
        "tickers": [
            "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "CFR.SW", "ABBN.SW",
            "ZURN.SW", "SIKA.SW", "LONN.SW", "GIVN.SW",
        ],
    },
    "ATHEX": {
        "name": "Athens Stock Exchange",
        "description": "Athens Stock Exchange – all listed Greek companies",
        "region": "GR", "continent": "Europe",
        "screener_exchange": "ATH",
        "yahoo_suffix": ".AT",
        "exchange_mic": "XATH",
        "fidelity": True,
        "tickers": [
            "ETE.AT", "EUROB.AT", "ALPHA.AT", "TPEIR.AT", "OPAP.AT", "HTO.AT",
            "MYTIL.AT", "PPC.AT", "MOH.AT", "BELA.AT", "TITC.AT", "LAMDA.AT",
        ],
    },
    "FTSE100": {
        "name": "FTSE 100",
        "description": "London Stock Exchange – largest UK companies by market cap",
        "region": "GB", "continent": "Europe",
        "fidelity": True,
        "tickers": [
            "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "BATS.L", "GSK.L", "RIO.L",
            "DGE.L", "REL.L", "BA.L", "LSEG.L", "PRU.L", "NG.L", "VOD.L",
            "LLOY.L", "BARC.L", "NWG.L", "STAN.L", "AAL.L",
        ],
    },
    "DAX": {
        "name": "DAX 40",
        "description": "Frankfurt Stock Exchange – largest German companies",
        "region": "DE", "continent": "Europe",
        "fidelity": True,
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "DTE.DE", "BAYN.DE", "BMW.DE",
            "VOW3.DE", "MUV2.DE", "DB1.DE", "RWE.DE", "BAS.DE", "MRK.DE", "ADS.DE",
        ],
    },
    "CAC40": {
        "name": "CAC 40",
        "description": "Euronext Paris – largest French companies",
        "region": "FR", "continent": "Europe",
        "fidelity": True,
        "tickers": [
            "MC.PA", "TTE.PA", "SAN.PA", "OR.PA", "AIR.PA", "SU.PA", "BNP.PA", "AI.PA",
            "KER.PA", "RMS.PA", "SAF.PA", "DG.PA", "EL.PA", "ORA.PA",
        ],
    },
    # ── Asia Pacific ────────────────────────────────────────────────────────
    "ASX200": {
        "name": "ASX",
        "description": "Australian Securities Exchange – all listed Australian companies",
        "region": "AU", "continent": "Asia Pacific",
        "screener_exchange": "ASX",
        "yahoo_suffix": ".AX",
        "exchange_mic": "XASX",
        "fidelity": True,
        "tickers": [
            "BHP.AX", "CSL.AX", "CBA.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX",
            "MQG.AX", "RIO.AX", "TLS.AX", "WOW.AX", "FMG.AX", "WDS.AX", "GMG.AX",
        ],
    },
    "HANGSENG": {
        "name": "HKEX",
        "description": "Hong Kong Stock Exchange – all listed companies",
        "region": "HK", "continent": "Asia Pacific",
        "screener_exchange": "HKG",
        "yahoo_suffix": ".HK",
        "exchange_mic": "XHKG",
        "fidelity": True,
        "tickers": [
            "0700.HK", "9988.HK", "0939.HK", "1398.HK", "3988.HK", "0005.HK",
            "0388.HK", "2318.HK", "0941.HK", "0883.HK", "1299.HK", "3690.HK",
        ],
    },
    "TSE": {
        "name": "Tokyo Stock Exchange",
        "description": "Tokyo Stock Exchange – all listed Japanese companies",
        "region": "JP", "continent": "Asia Pacific",
        "screener_exchange": "TKS",
        "yahoo_suffix": ".T",
        "exchange_mic": "XTKS",
        "fidelity": True,
        "tickers": [
            "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "8316.T",
            "9432.T", "4063.T", "7974.T", "6098.T", "8035.T", "9983.T",
        ],
    },
    "SGX": {
        "name": "Singapore Exchange",
        "description": "Singapore Exchange – all listed companies",
        "region": "SG", "continent": "Asia Pacific",
        "screener_exchange": "SGX",
        "yahoo_suffix": ".SI",
        "exchange_mic": "XSES",
        "fidelity": True,
        "tickers": [
            "D05.SI", "O39.SI", "U11.SI", "Z74.SI", "C6L.SI", "BN4.SI",
            "S63.SI", "C38U.SI", "9CI.SI", "F34.SI",
        ],
    },
    "NZX": {
        "name": "NZX",
        "description": "New Zealand Stock Exchange – all listed companies",
        "region": "NZ", "continent": "Asia Pacific",
        "screener_exchange": "NZE",
        "yahoo_suffix": ".NZ",
        "exchange_mic": "XNZE",
        "fidelity": True,
        "tickers": [
            "FPH.NZ", "AIA.NZ", "SPK.NZ", "MEL.NZ", "CEN.NZ", "MFT.NZ",
            "ATM.NZ", "FBU.NZ", "IFT.NZ", "EBO.NZ", "RYM.NZ", "CNU.NZ",
            "KPG.NZ", "SUM.NZ", "GNE.NZ",
        ],
    },
    "NIKKEI": {
        "name": "Nikkei 225",
        "description": "Tokyo Stock Exchange – top Japanese companies",
        "region": "JP", "continent": "Asia Pacific",
        "fidelity": True,
        "tickers": [
            "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "8316.T",
            "9432.T", "4063.T", "7974.T", "6098.T", "8035.T", "9983.T",
        ],
    },
    # ── Middle East & Africa ────────────────────────────────────────────────
    "JSE": {
        "name": "JSE",
        "description": "Johannesburg Stock Exchange – all listed companies",
        "region": "ZA", "continent": "Middle East & Africa",
        "screener_exchange": "JNB",
        "exchange_mic": "XJSE",
        "yahoo_suffix": ".JO",
        "fidelity": True,
        "tickers": [
            "NPN.JO", "PRX.JO", "CPI.JO", "FSR.JO", "SBK.JO", "MTN.JO", "AGL.JO",
            "SOL.JO", "SHP.JO", "WHL.JO", "ABG.JO", "NED.JO", "GFI.JO", "HAR.JO",
            "ANG.JO", "SLM.JO", "VOD.JO", "BVT.JO",
        ],
    },
}


def fidelity_market_ids() -> List[str]:
    """Explore market IDs that map to a Fidelity-tradable exchange (not index subsets)."""
    return [
        key for key, val in MARKET_TICKERS.items()
        if val.get("fidelity") and (val.get("screener_exchange") or val.get("exchange_mic"))
    ]


def fidelity_country_coverage() -> List[str]:
    """ISO country codes Fidelity International Trading supports, including US."""
    return sorted(FIDELITY_COUNTRIES)
