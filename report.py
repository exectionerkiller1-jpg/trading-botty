# -*- coding: utf-8 -*-
"""
Gün sonu / çalıştırma sonu performans raporu üretir.
"""

import json
import os
from datetime import datetime


def rapor_olustur(portfoy, guncel_fiyatlar: dict) -> dict:
    ilk_zaman = datetime.fromisoformat(portfoy.ilk_calisma_zamani)
    gecen_sure = datetime.now() - ilk_zaman
    gun_sayisi = round(gecen_sure.total_seconds() / 86400, 2)

    guncel_deger = portfoy.toplam_deger_hesapla(guncel_fiyatlar)
    kar_zarar = guncel_deger - portfoy.baslangic_bakiye
    getiri_yuzde = (kar_zarar / portfoy.baslangic_bakiye) * 100

    # Kapanmış işlem çiftlerinden (AL->SAT) kâr/zarar hesabı (başarı oranı için)
    kazanan = 0
    kaybeden = 0
    realized_pnl_listesi = []

    acik_pozisyon_maliyet = {}  # basit FIFO yerine ortalama maliyet mantığıyla eşleştirme
    for islem in portfoy.islem_gecmisi:
        if islem.yon == "AL":
            acik_pozisyon_maliyet.setdefault(islem.sembol, []).append((islem.miktar, islem.fiyat))
        elif islem.yon == "SAT":
            kalan = islem.miktar
            toplam_maliyet = 0.0
            kuyruk = acik_pozisyon_maliyet.get(islem.sembol, [])
            while kalan > 1e-9 and kuyruk:
                miktar, maliyet_fiyat = kuyruk[0]
                kullanilan = min(kalan, miktar)
                toplam_maliyet += kullanilan * maliyet_fiyat
                kalan -= kullanilan
                if kullanilan >= miktar:
                    kuyruk.pop(0)
                else:
                    kuyruk[0] = (miktar - kullanilan, maliyet_fiyat)

            satis_geliri = islem.miktar * islem.fiyat - islem.komisyon
            pnl = satis_geliri - toplam_maliyet
            realized_pnl_listesi.append(pnl)
            if pnl > 0:
                kazanan += 1
            elif pnl < 0:
                kaybeden += 1

    toplam_kapanan_islem = kazanan + kaybeden
    basari_orani = (kazanan / toplam_kapanan_islem * 100) if toplam_kapanan_islem > 0 else 0.0

    # Maksimum düşüş (equity eğrisinden)
    max_dusus_yuzde = 0.0
    if portfoy.equity_egrisi:
        tepe = portfoy.equity_egrisi[0][1]
        for _, deger in portfoy.equity_egrisi:
            if deger > tepe:
                tepe = deger
            dusus = (tepe - deger) / tepe * 100 if tepe > 0 else 0
            max_dusus_yuzde = max(max_dusus_yuzde, dusus)

    rapor = {
        "ilk_calisma_zamani": portfoy.ilk_calisma_zamani,
        "rapor_zamani": datetime.now().isoformat(timespec="seconds"),
        "gecen_gun_sayisi": gun_sayisi,
        "bot_kac_kez_calisti": portfoy.calisma_sayisi,
        "baslangic_bakiye_tl": round(portfoy.baslangic_bakiye, 2),
        "guncel_portfoy_degeri_tl": round(guncel_deger, 2),
        "kar_zarar_tl": round(kar_zarar, 2),
        "getiri_yuzde": round(getiri_yuzde, 2),
        "toplam_islem_sayisi": len(portfoy.islem_gecmisi),
        "kapanan_islem_sayisi": toplam_kapanan_islem,
        "kazanan_islem": kazanan,
        "kaybeden_islem": kaybeden,
        "basari_orani_yuzde": round(basari_orani, 2),
        "maksimum_dusus_yuzde": round(max_dusus_yuzde, 2),
        "toplam_komisyon_tl": round(portfoy.toplam_komisyon, 2),
        "acik_pozisyonlar": {
            sembol: {
                "miktar": round(pos["miktar"], 6),
                "ortalama_maliyet": round(pos["ortalama_maliyet"], 4),
                "guncel_fiyat": guncel_fiyatlar.get(sembol),
            }
            for sembol, pos in portfoy.pozisyonlar.items()
        },
    }
    return rapor


def rapor_yazdir(rapor: dict):
    print("\n" + "=" * 50)
    print("GÜN SONU / ÇALIŞTIRMA RAPORU")
    print("=" * 50)
    print(f"İlk çalıştırma        : {rapor['ilk_calisma_zamani']}")
    print(f"Geçen süre            : {rapor['gecen_gun_sayisi']} gün")
    print(f"Bot kaç kez çalıştı   : {rapor['bot_kac_kez_calisti']}")
    print(f"Başlangıç bakiye     : {rapor['baslangic_bakiye_tl']:,.2f} TL")
    print(f"Güncel portföy değeri : {rapor['guncel_portfoy_degeri_tl']:,.2f} TL")
    print(f"Kâr / Zarar           : {rapor['kar_zarar_tl']:,.2f} TL  ({rapor['getiri_yuzde']:+.2f}%)")
    print(f"Toplam işlem sayısı   : {rapor['toplam_islem_sayisi']}")
    print(f"Kapanan işlem         : {rapor['kapanan_islem_sayisi']} "
          f"(Kazanan: {rapor['kazanan_islem']} / Kaybeden: {rapor['kaybeden_islem']})")
    print(f"Başarı oranı          : %{rapor['basari_orani_yuzde']}")
    print(f"Maksimum düşüş        : %{rapor['maksimum_dusus_yuzde']}")
    print(f"Toplam komisyon       : {rapor['toplam_komisyon_tl']:,.2f} TL")
    if rapor["acik_pozisyonlar"]:
        print("\nAçık pozisyonlar:")
        for sembol, pos in rapor["acik_pozisyonlar"].items():
            print(f"  {sembol}: {pos['miktar']} adet, ort. maliyet {pos['ortalama_maliyet']}")
    print("=" * 50 + "\n")


def rapor_kaydet(rapor: dict, log_klasoru: str, dosya_adi: str):
    os.makedirs(log_klasoru, exist_ok=True)
    yol = os.path.join(log_klasoru, dosya_adi)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    return yol
