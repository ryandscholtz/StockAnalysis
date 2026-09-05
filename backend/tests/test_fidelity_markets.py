"""Fidelity International Trading market coverage and ticker normalisation."""
from app.config.markets import (
    FIDELITY_COUNTRIES,
    MARKET_TICKERS,
    fidelity_market_ids,
    infer_currency,
    is_international_ticker,
    normalize_ticker,
    to_yahoo_symbol,
)

# Primary Explore market id covering each Fidelity country code
_FIDELITY_COUNTRY_MARKET = {
    "US": "NYSE",
    "CA": "TSX",
    "MX": "BMV",
    "GB": "LSE",
    "DE": "XETRA",
    "FR": "EURONEXT_PA",
    "NL": "EURONEXT_AM",
    "BE": "EURONEXT_BR",
    "PT": "EURONEXT_LI",
    "IE": "EURONEXT_DU",
    "IT": "BORSA_IT",
    "ES": "BME",
    "SE": "NASDAQ_ST",
    "DK": "NASDAQ_CO",
    "FI": "NASDAQ_HE",
    "NO": "OSLO",
    "PL": "GPW",
    "AT": "WIENER",
    "CH": "SIX",
    "GR": "ATHEX",
    "AU": "ASX200",
    "HK": "HANGSENG",
    "JP": "TSE",
    "SG": "SGX",
    "NZ": "NZX",
    "ZA": "JSE",
}


def test_all_fidelity_countries_have_an_explore_market():
    assert set(_FIDELITY_COUNTRY_MARKET) == set(FIDELITY_COUNTRIES)
    for cc, market_id in _FIDELITY_COUNTRY_MARKET.items():
        assert market_id in MARKET_TICKERS, f"Missing market for Fidelity country {cc}"
        cfg = MARKET_TICKERS[market_id]
        assert cfg.get("region") == cc or cc == "US"
        assert cfg.get("tickers") or cfg.get("screener_exchange") or cfg.get("exchange_mic")


def test_fidelity_exchange_markets_have_fallback_or_screener_stocks():
    for market_id in fidelity_market_ids():
        cfg = MARKET_TICKERS[market_id]
        has_live = bool(cfg.get("screener_exchange") or cfg.get("exchange_mic"))
        has_fallback = bool(cfg.get("tickers"))
        assert has_live or has_fallback, f"{market_id} has no way to list stocks"
        if not has_live:
            assert len(cfg["tickers"]) >= 5


def test_normalize_fidelity_colon_symbols():
    assert normalize_ticker("SAP:DE") == "SAP.DE"
    assert normalize_ticker("npn:za") == "NPN.JO"
    assert normalize_ticker("7203:JP") == "7203.T"
    assert normalize_ticker("FPH:NZ") == "FPH.NZ"
    assert normalize_ticker("ETE:GR") == "ETE.AT"
    assert normalize_ticker("A5G:IE") == "A5G.IR"
    assert normalize_ticker("HIVE:CA") == "HIVE.TO"
    assert normalize_ticker("AAPL:US") == "AAPL"
    assert normalize_ticker("AAPL") == "AAPL"


def test_normalize_preserves_unknown_colon_symbols():
    # Share-class style, not a Fidelity country code
    assert normalize_ticker("BRK:B") == "BRK:B"


def test_normalize_hyphen_and_marketstack_suffixes():
    assert normalize_ticker("MRF-JO") == "MRF.JO"
    assert normalize_ticker("SAP-DE") == "SAP.DE"
    assert normalize_ticker("BEL.XJSE") == "BEL.JO"
    assert normalize_ticker("ETE.XATH") == "ETE.AT"


def test_to_yahoo_symbol_mic_conversion():
    assert to_yahoo_symbol("BEL.XJSE") == "BEL.JO"
    assert to_yahoo_symbol("SAP.DE") == "SAP.DE"
    assert to_yahoo_symbol("AAPL") == "AAPL"


def test_international_detection():
    assert is_international_ticker("SAP.DE")
    assert is_international_ticker("NPN:ZA")
    assert is_international_ticker("FPH.NZ")
    assert not is_international_ticker("AAPL")
    assert not is_international_ticker("MSFT")


def test_currency_inference_for_fidelity_markets():
    assert infer_currency("SAP.DE") == "EUR"
    assert infer_currency("ETE.AT") == "EUR"
    assert infer_currency("A5G.IR") == "EUR"
    assert infer_currency("FPH.NZ") == "NZD"
    assert infer_currency("HIVE.V") == "CAD"
    assert infer_currency("AMXL.MX") == "MXN"
    assert infer_currency("NOVO-B.CO") == "DKK"
    assert infer_currency("EQNR.OL") == "NOK"
    assert infer_currency("PKO.WA") == "PLN"
    assert infer_currency("NPN.JO") == "ZAR"
    assert infer_currency("BEL.XJSE") == "ZAC"
    assert infer_currency("7203.T") == "JPY"
    assert infer_currency("SHEL.L") == "GBP"
    assert infer_currency("AAPL") is None
    assert infer_currency(exchange="Athens Stock Exchange") == "EUR"
    assert infer_currency(exchange="NZX") == "NZD"
    assert infer_currency(exchange="Bolsa Mexicana") == "MXN"


def test_explore_markets_include_new_fidelity_venues():
    for market_id in ("AMEX", "TSXV", "EURONEXT_DU", "ATHEX", "NZX"):
        assert market_id in MARKET_TICKERS
        assert MARKET_TICKERS[market_id].get("continent")
        assert MARKET_TICKERS[market_id].get("screener_exchange")
        assert len(MARKET_TICKERS[market_id].get("tickers") or []) >= 5
