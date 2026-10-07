# Demo Trading Bot (Paper Trading)

Gerçek piyasa verisiyle çalışan ama **gerçek emir göndermeyen** sanal analiz/alım-satım botu.
Başlangıç bakiyesi: 100.000 TL (config.py içinden değiştirilebilir).

## Kurulum

```bash
pip install yfinance ccxt pandas numpy
```

## Çalıştırma

```bash
# Tek seferlik analiz (tüm varlıkları bir kez tarar, rapor üretir)
python main.py

# 10 tur, turlar arası 5 dakika (300 sn) bekleyerek sürekli çalıştır
python main.py --dongu 10 --bekleme 300

# İnternet olmadan / mantığı test etmek için sahte veriyle dene
python main.py --test
```

## Ayarlar (config.py)

| Ayar | Açıklama |
|---|---|
| `BASLANGIC_BAKIYE_TL` | Sanal portföyün başlangıç bakiyesi |
| `PIYASA_TIPI` | `"bist"` veya `"kripto"` |
| `BIST_HISSELERI` | yfinance formatında ticker listesi (örn. `THYAO.IS`) |
| `KRIPTO_PARITELERI` | Binance formatında parite listesi (örn. `BTC/USDT`) |
| `ZAMAN_DILIMI` | Mum aralığı: `1m, 5m, 15m, 1h, 4h, 1d` |
| `POZISYON_ORANI` | Her AL sinyalinde nakdin ne kadarının kullanılacağı |
| `KOMISYON_ORANI` | Simüle edilen işlem komisyonu (varsayılan %0.1) |

## Strateji Mantığı

RSI, MACD ve SMA kesişimi "oy" verir (-1/0/+1). Toplam skor ±2 ve üzerine
çıkarsa AL/SAT sinyali üretilir, aksi halde BEKLE. `strategy.py` içinden
eşik değerlerini ve ağırlıkları değiştirebilirsin.

## Çıktılar

- `logs/islemler.csv` — her AL/SAT işleminin detaylı kaydı
- `logs/gun_sonu_raporu.json` — kâr/zarar, başarı oranı, maksimum düşüş, komisyon maliyeti

## GitHub Actions ile 7/24 Otomatik Çalıştırma

Bilgisayarın kapalı olsa bile botun arka planda sürekli çalışmasını istiyorsan,
GitHub Actions (ücretsiz) kullanılabilir. Repo `.github/workflows/trading_bot.yml`
dosyasını içeriyor; bunu GitHub'a yüklediğinde GitHub'ın sunucuları botu otomatik
olarak her 30 dakikada bir çalıştırır ve sonuçları (logs/ klasörü) repoya geri yazar.

Kurulum adımları:
1. github.com'da ücretsiz hesap aç
2. Yeni bir **private** repository oluştur (örn. "trading-bot")
3. Bu klasördeki tüm dosyaları (gizli `.github` klasörü dahil) repoya yükle
4. Repo sayfasında "Actions" sekmesine git, workflow'u etkinleştir (gerekirse "I understand my workflows, go ahead and enable them" de)
5. İlk çalıştırmayı denemek için Actions sekmesinde "Trading Bot Otomatik Çalıştırma" > "Run workflow" butonuna bas

Bot her çalıştığında `logs/portfoy_durumu.json` dosyasını günceller ve bir önceki
çalıştırmadan kaldığı yerden devam eder — nakit, açık pozisyonlar ve işlem geçmişi
hiç kaybolmaz. 1 hafta sonra `logs/gun_sonu_raporu.json` dosyasını açtığında
`gecen_gun_sayisi` ve `bot_kac_kez_calisti` alanlarıyla birlikte tüm dönemin
kâr/zarar özetini görürsün.

Sıfırdan başlamak istersen (örn. yeni bir hafta için): `python main.py --sifirla`

## Önemli Notlar

- **Bu bot hiçbir zaman gerçek emir göndermez.** `portfolio.py` içindeki
  `SanalPortfoy` sınıfı tüm işlemleri sadece bellekte/CSV'de simüle eder.
- BIST verisi Yahoo Finance üzerinden ücretsiz ama gecikmeli/sınırlı olabilir.
- Kripto verisi Binance public API'den gelir, API key gerekmez (sadece okuma).
- Gerçek paraya geçmeden önce stratejiyi uzun süre paper trading'de test et —
  burada verilen strateji basit bir başlangıç noktasıdır, yatırım tavsiyesi değildir.
