# -*- coding: utf-8 -*-
"""
Demo (paper trading) analiz botu - ana çalıştırma dosyası.

Kullanım:
    python main.py                  -> config.py'deki ayarlarla tek seferlik analiz + rapor
    python main.py --dongu 10       -> 10 kez, aralarla çalışır (gerçek zamanlı simülasyon)
    python main.py --test           -> ağ bağlantısı olmadan sahte veriyle mantığı test eder

Bu bot HİÇBİR ZAMAN gerçek emir göndermez. Tüm işlemler portfolio.py
içindeki SanalPortfoy sınıfı üzerinden, sadece bellekte/CSV'de simüle edilir.
"""

import argparse
import os
import time

import config as cfg
import data_fetcher as veri
import indicators as ind
import strategy as strat
from portfolio import SanalPortfoy
from report import rapor_olustur, rapor_yazdir, rapor_kaydet


def varlik_listesi_al():
    if cfg.PIYASA_TIPI == "bist":
        return cfg.BIST_HISSELERI
    return cfg.KRIPTO_PARITELERI


def veri_getir(sembol: str, test_modu: bool):
    if test_modu:
        return veri._sahte_veri_uret(bar_sayisi=cfg.GECMIS_BAR_SAYISI, baslangic_fiyat=100.0, seed=hash(sembol) % 1000)

    if cfg.PIYASA_TIPI == "bist":
        return veri.bist_veri_cek(sembol, periyot="60d", interval=cfg.ZAMAN_DILIMI)
    return veri.kripto_veri_cek(sembol, zaman_dilimi=cfg.ZAMAN_DILIMI, bar_sayisi=cfg.GECMIS_BAR_SAYISI)


def tek_tur_calistir(portfoy: SanalPortfoy, test_modu: bool):
    guncel_fiyatlar = {}

    for sembol in varlik_listesi_al():
        try:
            df = veri_getir(sembol, test_modu)
        except Exception as e:
            print(f"[UYARI] {sembol} için veri çekilemedi: {e}")
            continue

        df_indikatorlu = ind.tum_indikatorleri_hesapla(df, cfg)
        son_fiyat = float(df_indikatorlu["close"].iloc[-1])
        guncel_fiyatlar[sembol] = son_fiyat

        sinyal = strat.strateji_calistir(df_indikatorlu, cfg)

        print(f"\n[{sembol}] Fiyat: {son_fiyat:.4f} | Karar: {sinyal.karar} (skor: {sinyal.skor})")
        for g in sinyal.gerekce:
            print(f"   - {g}")

        sebep_ozeti = "; ".join(sinyal.gerekce[:2])

        if sinyal.karar == "AL":
            basarili = portfoy.al(sembol, son_fiyat, cfg.POZISYON_ORANI, sebep=sebep_ozeti)
            if basarili:
                print(f"   >> AL emri simüle edildi.")
            else:
                print(f"   >> Yetersiz nakit, AL simüle edilemedi.")
        elif sinyal.karar == "SAT":
            basarili = portfoy.sat(sembol, son_fiyat, oran=1.0, sebep=sebep_ozeti)
            if basarili:
                print(f"   >> SAT emri simüle edildi.")
            else:
                print(f"   >> Açık pozisyon yok, SAT simüle edilemedi.")
        else:
            print(f"   >> BEKLE - işlem yapılmadı.")

    portfoy.equity_kaydet(guncel_fiyatlar)
    return guncel_fiyatlar


def main():
    parser = argparse.ArgumentParser(description="Demo paper-trading analiz botu")
    parser.add_argument("--dongu", type=int, default=1, help="Kaç tur çalıştırılacağı")
    parser.add_argument("--bekleme", type=int, default=60, help="Turlar arası bekleme (saniye)")
    parser.add_argument("--test", action="store_true", help="Ağ bağlantısı olmadan sahte veriyle test et")
    parser.add_argument("--sifirla", action="store_true", help="Kayıtlı durumu silip portföyü sıfırdan başlatır")
    args = parser.parse_args()

    durum_dosyasi = os.path.join(cfg.LOG_KLASORU, "portfoy_durumu.json")

    if args.sifirla and os.path.exists(durum_dosyasi):
        os.remove(durum_dosyasi)
        print("[SIFIRLAMA] Önceki durum silindi, portföy sıfırdan başlıyor.\n")

    print(f"Bot başlıyor. Piyasa: {cfg.PIYASA_TIPI} | Başlangıç bakiye: {cfg.BASLANGIC_BAKIYE_TL:,.2f} TL")
    if args.test:
        print("[TEST MODU] Gerçek veri yerine sahte/simüle veri kullanılıyor.\n")

    # Önceki çalıştırmadan kalan durum varsa oradan devam eder (GitHub Actions gibi
    # her seferinde "temiz" ortamda başlayan sistemlerde hafızanın kalıcı olması için şart).
    portfoy = SanalPortfoy.durumu_yukle_veya_olustur(
        dosya_yolu=durum_dosyasi,
        baslangic_bakiye=cfg.BASLANGIC_BAKIYE_TL,
        komisyon_orani=cfg.KOMISYON_ORANI,
        log_klasoru=cfg.LOG_KLASORU,
        islem_log_dosyasi=cfg.ISLEM_LOG_DOSYASI,
    )
    print(f"Bu botun {portfoy.calisma_sayisi}. çalıştırılması (ilk çalıştırma: {portfoy.ilk_calisma_zamani})\n")

    guncel_fiyatlar = {}
    for tur in range(1, args.dongu + 1):
        print(f"\n########## TUR {tur}/{args.dongu} ##########")
        guncel_fiyatlar = tek_tur_calistir(portfoy, test_modu=args.test)

        if tur < args.dongu:
            time.sleep(args.bekleme)

    portfoy.durumu_kaydet(durum_dosyasi)

    rapor = rapor_olustur(portfoy, guncel_fiyatlar)
    rapor_yazdir(rapor)
    yol = rapor_kaydet(rapor, cfg.LOG_KLASORU, cfg.RAPOR_DOSYASI)
    print(f"Rapor kaydedildi: {yol}")
    print(f"İşlem geçmişi: {portfoy.islem_log_yolu}")
    print(f"Portföy durumu kaydedildi: {durum_dosyasi}")


if __name__ == "__main__":
    main()
