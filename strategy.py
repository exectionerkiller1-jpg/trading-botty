# -*- coding: utf-8 -*-
"""
İndikatör değerlerinden AL / SAT / BEKLE kararı üreten strateji modülü.

Mantık: Her indikatör -1 (satış eğilimi), 0 (nötr) veya +1 (alış eğilimi) oyu verir.
Oyların toplamı eşik değeri geçerse AL/SAT sinyali üretilir, aksi halde BEKLE.
Bu basit "oy çokluğu" yaklaşımı tek bir indikatöre aşırı bağımlı olmayı önler.
"""

from dataclasses import dataclass
from indicators import trend_belirle


@dataclass
class Sinyal:
    karar: str          # "AL", "SAT", "BEKLE"
    skor: int            # -3 ile +3 arası toplam oy
    gerekce: list        # karara katkıda bulunan sebepler (insan okunabilir)


def strateji_calistir(df_indikatorlu, cfg) -> Sinyal:
    son = df_indikatorlu.iloc[-1]
    gerekce = []
    skor = 0

    # --- RSI oyu ---
    if son["rsi"] < cfg.RSI_ASIRI_SATIM:
        skor += 1
        gerekce.append(f"RSI {son['rsi']:.1f} -> aşırı satım, alış sinyali")
    elif son["rsi"] > cfg.RSI_ASIRI_ALIM:
        skor -= 1
        gerekce.append(f"RSI {son['rsi']:.1f} -> aşırı alım, satış sinyali")

    # --- MACD oyu (histogram pozitif/negatif) ---
    if son["macd_hist"] > 0 and son["macd"] > son["macd_signal"]:
        skor += 1
        gerekce.append("MACD sinyal çizgisinin üstünde -> momentum yukarı")
    elif son["macd_hist"] < 0 and son["macd"] < son["macd_signal"]:
        skor -= 1
        gerekce.append("MACD sinyal çizgisinin altında -> momentum aşağı")

    # --- Hareketli ortalama kesişimi ---
    if son["sma_kisa"] > son["sma_uzun"]:
        skor += 1
        gerekce.append("Kısa SMA, uzun SMA üstünde -> yükseliş trendi")
    elif son["sma_kisa"] < son["sma_uzun"]:
        skor -= 1
        gerekce.append("Kısa SMA, uzun SMA altında -> düşüş trendi")

    # --- Genel trend filtresi (bilgi amaçlı, skora dahil değil ama raporlanır) ---
    trend = trend_belirle(df_indikatorlu["close"], cfg.SMA_KISA, cfg.SMA_UZUN)
    gerekce.append(f"Genel trend: {trend}")

    # --- Volatilite uyarısı (bilgi amaçlı) ---
    if son["volatilite_yuzde"] > 3:
        gerekce.append(f"Yüksek volatilite (%{son['volatilite_yuzde']:.1f}) -> risk artmış olabilir")

    # --- Karar eşiği ---
    if skor >= 2:
        karar = "AL"
    elif skor <= -2:
        karar = "SAT"
    else:
        karar = "BEKLE"

    return Sinyal(karar=karar, skor=skor, gerekce=gerekce)
