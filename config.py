# -*- coding: utf-8 -*-
"""
Genel ayarlar. Burayı değiştirerek botun davranışını kontrol edersin.
"""

# ---- Portföy ayarları ----
BASLANGIC_BAKIYE_TL = 100_000.0
KOMISYON_ORANI = 0.001  # %0.1 - her işlemde alınan sanal komisyon (Binance/aracı kurum ortalaması)

# ---- Varlık ayarları ----
# PIYASA_TIPI: "bist" veya "kripto"
PIYASA_TIPI = "kripto"

# BIST için yfinance ticker formatı (örn: "THYAO.IS", "ASELS.IS")
BIST_HISSELERI = ["THYAO.IS", "ASELS.IS", "GARAN.IS"]

# Kripto için Binance sembol formatı
KRIPTO_PARITELERI = ["BTC/USDT", "ETH/USDT"]

# ---- Veri ayarları ----
ZAMAN_DILIMI = "1h"      # 1m, 5m, 15m, 1h, 4h, 1d
GECMIS_BAR_SAYISI = 200  # indikatör hesaplamak için çekilecek mum sayısı

# ---- Strateji parametreleri ----
RSI_PERIYOT = 14
RSI_ASIRI_SATIM = 30     # bunun altı -> alım sinyaline katkı
RSI_ASIRI_ALIM = 70      # bunun üstü -> satım sinyaline katkı

MACD_HIZLI = 12
MACD_YAVAS = 26
MACD_SIGNAL = 9

SMA_KISA = 20
SMA_UZUN = 50

VOLATILITE_PERIYOT = 14  # ATR benzeri volatilite penceresi

# Pozisyon büyüklüğü: her AL sinyalinde nakdin yüzde kaçı kullanılsın
POZISYON_ORANI = 0.25  # %25

# ---- Log ----
LOG_KLASORU = "logs"
ISLEM_LOG_DOSYASI = "islemler.csv"
RAPOR_DOSYASI = "gun_sonu_raporu.json"
