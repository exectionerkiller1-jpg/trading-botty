# -*- coding: utf-8 -*-
"""
Sanal (paper trading) portföy motoru.

ÖNEMLİ: Bu modül hiçbir zaman gerçek bir borsaya emir göndermez.
Tüm AL/SAT işlemleri sadece bellekte/CSV dosyasında simüle edilir.
"""

import os
import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Islem:
    zaman: str
    sembol: str
    yon: str          # "AL" veya "SAT"
    fiyat: float
    miktar: float
    tutar: float       # fiyat * miktar
    komisyon: float
    sebep: str          # strateji gerekçesi özeti


class SanalPortfoy:
    def __init__(self, baslangic_bakiye: float, komisyon_orani: float, log_klasoru: str, islem_log_dosyasi: str):
        self.baslangic_bakiye = baslangic_bakiye
        self.nakit = baslangic_bakiye
        self.komisyon_orani = komisyon_orani
        self.pozisyonlar = {}       # {sembol: {"miktar": float, "ortalama_maliyet": float}}
        self.islem_gecmisi: list[Islem] = []
        self.toplam_komisyon = 0.0
        self.equity_egrisi = []     # (zaman, toplam_deger) çiftleri

        self.ilk_calisma_zamani = datetime.now().isoformat(timespec="seconds")
        self.calisma_sayisi = 0  # bot kaç kez tetiklendi (her ayrı çalıştırma +1)

        self.log_klasoru = log_klasoru
        self.islem_log_yolu = os.path.join(log_klasoru, islem_log_dosyasi)
        os.makedirs(log_klasoru, exist_ok=True)
        self._csv_baslik_yaz()

    def _csv_baslik_yaz(self):
        if not os.path.exists(self.islem_log_yolu):
            with open(self.islem_log_yolu, "w", newline="", encoding="utf-8") as f:
                yazici = csv.writer(f)
                yazici.writerow(["zaman", "sembol", "yon", "fiyat", "miktar", "tutar", "komisyon", "sebep"])

    def _csv_satir_ekle(self, islem: Islem):
        with open(self.islem_log_yolu, "a", newline="", encoding="utf-8") as f:
            yazici = csv.writer(f)
            yazici.writerow([islem.zaman, islem.sembol, islem.yon, f"{islem.fiyat:.4f}",
                              f"{islem.miktar:.6f}", f"{islem.tutar:.2f}", f"{islem.komisyon:.2f}", islem.sebep])

    def al(self, sembol: str, fiyat: float, pozisyon_orani: float, sebep: str = "") -> bool:
        """Nakdin pozisyon_orani kadarıyla alım yapar. Yetersiz nakitte False döner."""
        harcanacak_tutar = self.nakit * pozisyon_orani
        komisyon = harcanacak_tutar * self.komisyon_orani
        net_tutar = harcanacak_tutar - komisyon

        if harcanacak_tutar <= 0 or harcanacak_tutar > self.nakit:
            return False

        miktar = net_tutar / fiyat

        self.nakit -= harcanacak_tutar
        self.toplam_komisyon += komisyon

        if sembol not in self.pozisyonlar:
            self.pozisyonlar[sembol] = {"miktar": 0.0, "ortalama_maliyet": 0.0}

        mevcut = self.pozisyonlar[sembol]
        yeni_miktar = mevcut["miktar"] + miktar
        yeni_maliyet = (mevcut["miktar"] * mevcut["ortalama_maliyet"] + miktar * fiyat) / yeni_miktar
        self.pozisyonlar[sembol] = {"miktar": yeni_miktar, "ortalama_maliyet": yeni_maliyet}

        islem = Islem(
            zaman=datetime.now().isoformat(timespec="seconds"),
            sembol=sembol, yon="AL", fiyat=fiyat, miktar=miktar,
            tutar=harcanacak_tutar, komisyon=komisyon, sebep=sebep
        )
        self.islem_gecmisi.append(islem)
        self._csv_satir_ekle(islem)
        return True

    def sat(self, sembol: str, fiyat: float, oran: float = 1.0, sebep: str = "") -> bool:
        """Elde tutulan pozisyonun oran kadarını satar (varsayılan: tamamı)."""
        if sembol not in self.pozisyonlar or self.pozisyonlar[sembol]["miktar"] <= 0:
            return False

        pozisyon = self.pozisyonlar[sembol]
        satilacak_miktar = pozisyon["miktar"] * oran
        brut_tutar = satilacak_miktar * fiyat
        komisyon = brut_tutar * self.komisyon_orani
        net_tutar = brut_tutar - komisyon

        self.nakit += net_tutar
        self.toplam_komisyon += komisyon
        pozisyon["miktar"] -= satilacak_miktar
        if pozisyon["miktar"] <= 1e-9:
            del self.pozisyonlar[sembol]

        islem = Islem(
            zaman=datetime.now().isoformat(timespec="seconds"),
            sembol=sembol, yon="SAT", fiyat=fiyat, miktar=satilacak_miktar,
            tutar=brut_tutar, komisyon=komisyon, sebep=sebep
        )
        self.islem_gecmisi.append(islem)
        self._csv_satir_ekle(islem)
        return True

    def toplam_deger_hesapla(self, guncel_fiyatlar: dict) -> float:
        """Nakit + tüm açık pozisyonların güncel değeri."""
        pozisyon_degeri = sum(
            pos["miktar"] * guncel_fiyatlar.get(sembol, pos["ortalama_maliyet"])
            for sembol, pos in self.pozisyonlar.items()
        )
        return self.nakit + pozisyon_degeri

    def equity_kaydet(self, guncel_fiyatlar: dict):
        toplam = self.toplam_deger_hesapla(guncel_fiyatlar)
        self.equity_egrisi.append((datetime.now().isoformat(timespec="seconds"), toplam))

    # ------------------------------------------------------------------
    # Durum kaydetme / yükleme: bot her çalıştığında sıfırdan başlamasın
    # diye portföyün tüm hali bir JSON dosyasına yazılır ve bir sonraki
    # çalıştırmada oradan geri yüklenir. GitHub Actions gibi her seferinde
    # "temiz" bir ortamda başlayan sistemlerde bu dosya olmasa hafıza kalıcı
    # olmaz.
    # ------------------------------------------------------------------
    def durumu_kaydet(self, dosya_yolu: str):
        veri = {
            "baslangic_bakiye": self.baslangic_bakiye,
            "nakit": self.nakit,
            "komisyon_orani": self.komisyon_orani,
            "pozisyonlar": self.pozisyonlar,
            "toplam_komisyon": self.toplam_komisyon,
            "equity_egrisi": self.equity_egrisi,
            "ilk_calisma_zamani": self.ilk_calisma_zamani,
            "calisma_sayisi": self.calisma_sayisi,
            "islem_gecmisi": [asdict(islem) for islem in self.islem_gecmisi],
        }
        os.makedirs(os.path.dirname(dosya_yolu), exist_ok=True)
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)

    @classmethod
    def durumu_yukle_veya_olustur(cls, dosya_yolu: str, baslangic_bakiye: float,
                                   komisyon_orani: float, log_klasoru: str, islem_log_dosyasi: str):
        """
        dosya_yolu'nda kayıtlı bir durum varsa oradan devam eder (nakit, pozisyonlar,
        geçmiş işlemler korunur). Yoksa (ilk çalıştırma) sıfırdan yeni bir portföy açar.
        """
        portfoy = cls(baslangic_bakiye, komisyon_orani, log_klasoru, islem_log_dosyasi)

        if os.path.exists(dosya_yolu):
            with open(dosya_yolu, "r", encoding="utf-8") as f:
                veri = json.load(f)

            portfoy.baslangic_bakiye = veri["baslangic_bakiye"]
            portfoy.nakit = veri["nakit"]
            portfoy.komisyon_orani = veri["komisyon_orani"]
            portfoy.pozisyonlar = veri["pozisyonlar"]
            portfoy.toplam_komisyon = veri["toplam_komisyon"]
            portfoy.equity_egrisi = [tuple(e) for e in veri["equity_egrisi"]]
            portfoy.ilk_calisma_zamani = veri["ilk_calisma_zamani"]
            portfoy.calisma_sayisi = veri.get("calisma_sayisi", 0)
            portfoy.islem_gecmisi = [Islem(**d) for d in veri["islem_gecmisi"]]

        portfoy.calisma_sayisi += 1
        return portfoy
