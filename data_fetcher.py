# -*- coding: utf-8 -*-
"""
Gerçek piyasa verisini çeken modül.

- BIST hisseleri için: yfinance (Yahoo Finance) kullanılır.
- Kripto için: ccxt üzerinden Binance public API kullanılır (API key gerekmez,
  çünkü sadece fiyat verisi okunuyor, işlem gönderilmiyor).

Not: Bu dosya gerçek ağ isteği atar. Claude'un sohbet sanal ortamında borsa
API'lerine erişim kapalı olduğu için test burada mock veriyle yapıldı;
kendi bilgisayarında normal internet bağlantısıyla sorunsuz çalışır.
"""

import pandas as pd


def bist_veri_cek(ticker: str, periyot: str = "60d", interval: str = "1h") -> pd.DataFrame:
    """
    BIST hissesi için OHLCV verisi çeker (Yahoo Finance üzerinden).

    ticker: "THYAO.IS" gibi .IS uzantılı sembol
    periyot: "60d", "6mo", "1y" gibi
    interval: "1h", "1d" gibi
    """
    import yfinance as yf

    df = yf.download(ticker, period=periyot, interval=interval, progress=False)
    if df.empty:
        raise ValueError(f"{ticker} için veri bulunamadı. Sembolü ve internet bağlantısını kontrol et.")

    # yfinance bazen MultiIndex kolon döndürür (tek ticker'da bile) - düzleştir
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume"
    })
    return df[["open", "high", "low", "close", "volume"]]


def kripto_veri_cek(sembol: str, zaman_dilimi: str = "1h", bar_sayisi: int = 200) -> pd.DataFrame:
    """
    Kripto pariteleri için OHLCV verisi çeker (Binance public API, ccxt ile).

    sembol: "BTC/USDT" gibi
    zaman_dilimi: "1m", "5m", "15m", "1h", "4h", "1d"
    bar_sayisi: kaç mum çekileceği
    """
    import ccxt

    borsa = ccxt.binance()
    ham_veri = borsa.fetch_ohlcv(sembol, timeframe=zaman_dilimi, limit=bar_sayisi)

    df = pd.DataFrame(ham_veri, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")
    return df


def anlik_fiyat_kripto(sembol: str) -> float:
    """Tek bir kripto paritenin anlık fiyatını döner (ticker endpoint)."""
    import ccxt
    borsa = ccxt.binance()
    ticker = borsa.fetch_ticker(sembol)
    return float(ticker["last"])


def anlik_fiyat_bist(ticker: str) -> float:
    """Tek bir BIST hissesinin son kapanış fiyatını döner."""
    df = bist_veri_cek(ticker, periyot="5d", interval="1d")
    return float(df["close"].iloc[-1])


# ---------------------------------------------------------------------------
# Test/demo amaçlı sahte veri üretici (ağ erişimi olmayan ortamlarda mantığı
# doğrulamak için). Gerçek botu çalıştırırken bu fonksiyona ihtiyacın yok.
# ---------------------------------------------------------------------------
def _sahte_veri_uret(bar_sayisi: int = 200, baslangic_fiyat: float = 100.0, seed: int = 42) -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(seed)
    getiriler = rng.normal(loc=0.0003, scale=0.01, size=bar_sayisi)
    fiyatlar = baslangic_fiyat * (1 + getiriler).cumprod()

    high = fiyatlar * (1 + rng.uniform(0, 0.005, bar_sayisi))
    low = fiyatlar * (1 - rng.uniform(0, 0.005, bar_sayisi))
    openp = fiyatlar * (1 + rng.normal(0, 0.002, bar_sayisi))
    volume = rng.uniform(1000, 5000, bar_sayisi)

    tarih = pd.date_range(end=pd.Timestamp.now(), periods=bar_sayisi, freq="h")
    df = pd.DataFrame({
        "open": openp, "high": high, "low": low,
        "close": fiyatlar, "volume": volume
    }, index=tarih)
    return df
