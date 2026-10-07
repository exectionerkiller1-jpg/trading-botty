# -*- coding: utf-8 -*-
"""
Teknik indikatörleri hesaplayan modül. Harici bağımlılık yok (sadece pandas/numpy),
ta-lib gibi kütüphanelere ihtiyaç duymadan RSI/MACD/ATR formülleri elle yazıldı.
"""

import pandas as pd
import numpy as np


def rsi_hesapla(close: pd.Series, periyot: int = 14) -> pd.Series:
    delta = close.diff()
    kazanc = delta.clip(lower=0)
    kayip = -delta.clip(upper=0)

    ort_kazanc = kazanc.ewm(alpha=1 / periyot, min_periods=periyot, adjust=False).mean()
    ort_kayip = kayip.ewm(alpha=1 / periyot, min_periods=periyot, adjust=False).mean()

    rs = ort_kazanc / ort_kayip.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)  # yetersiz veri durumunda nötr değer


def macd_hesapla(close: pd.Series, hizli: int = 12, yavas: int = 26, signal: int = 9):
    ema_hizli = close.ewm(span=hizli, adjust=False).mean()
    ema_yavas = close.ewm(span=yavas, adjust=False).mean()
    macd_cizgisi = ema_hizli - ema_yavas
    signal_cizgisi = macd_cizgisi.ewm(span=signal, adjust=False).mean()
    histogram = macd_cizgisi - signal_cizgisi
    return macd_cizgisi, signal_cizgisi, histogram


def sma_hesapla(close: pd.Series, periyot: int) -> pd.Series:
    return close.rolling(window=periyot, min_periods=1).mean()


def ema_hesapla(close: pd.Series, periyot: int) -> pd.Series:
    return close.ewm(span=periyot, adjust=False).mean()


def volatilite_hesapla(df: pd.DataFrame, periyot: int = 14) -> pd.Series:
    """ATR (Average True Range) tabanlı volatilite ölçümü."""
    high, low, close = df["high"], df["low"], df["close"]
    onceki_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - onceki_close).abs()
    tr3 = (low - onceki_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = true_range.rolling(window=periyot, min_periods=1).mean()
    return atr


def trend_belirle(close: pd.Series, sma_kisa_periyot: int = 20, sma_uzun_periyot: int = 50) -> str:
    """Kısa/uzun SMA ilişkisine göre genel trend yönünü döner: 'YUKARI', 'ASAGI', 'YATAY'."""
    sma_kisa = sma_hesapla(close, sma_kisa_periyot).iloc[-1]
    sma_uzun = sma_hesapla(close, sma_uzun_periyot).iloc[-1]

    fark_yuzde = (sma_kisa - sma_uzun) / sma_uzun * 100

    if fark_yuzde > 0.5:
        return "YUKARI"
    elif fark_yuzde < -0.5:
        return "ASAGI"
    return "YATAY"


def tum_indikatorleri_hesapla(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """
    Verilen OHLCV df'ine tüm indikatör kolonlarını ekler ve döner.
    cfg: config modülü (RSI_PERIYOT, MACD_HIZLI vb. parametreleri içerir)
    """
    sonuc = df.copy()

    sonuc["rsi"] = rsi_hesapla(sonuc["close"], cfg.RSI_PERIYOT)

    macd, macd_signal, macd_hist = macd_hesapla(
        sonuc["close"], cfg.MACD_HIZLI, cfg.MACD_YAVAS, cfg.MACD_SIGNAL
    )
    sonuc["macd"] = macd
    sonuc["macd_signal"] = macd_signal
    sonuc["macd_hist"] = macd_hist

    sonuc["sma_kisa"] = sma_hesapla(sonuc["close"], cfg.SMA_KISA)
    sonuc["sma_uzun"] = sma_hesapla(sonuc["close"], cfg.SMA_UZUN)

    sonuc["atr"] = volatilite_hesapla(sonuc, cfg.VOLATILITE_PERIYOT)
    sonuc["volatilite_yuzde"] = (sonuc["atr"] / sonuc["close"]) * 100

    return sonuc
