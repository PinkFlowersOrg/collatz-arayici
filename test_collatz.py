"""
collatz.py icin test paketi.

    python test_collatz.py

Her test, hizli kodun sonucunu "altin standart" ile karsilastirir:
kisayolsuz, blok yok, her adimda kontrol eden en yavas ama en guvenilir
surum. Ayrica literaturdeki bilinen degerlere (ericr.nl/wondrous) bakar.
"""

import random
import sys
import time

import collatz as c


# ---------------------------------------------------------------------------
# ALTIN STANDART - hicbir kisayol yok, her adimda kontrol
# ---------------------------------------------------------------------------

def altin_glide(n):
    """Doner: (sonuc, adim, tepe). collatz.dusme_testi ile ayni olmali."""
    if n <= 2:
        return ("dustu", 0, n)
    bas, adim, tepe = n, 0, n
    limit = c.glide_limiti(bas)
    while True:
        n = 3 * n + 1 if n & 1 else n >> 1
        adim += 1
        if n > tepe:
            tepe = n
        if n < bas:
            return ("dustu", adim, tepe)
        if n == bas:
            return ("dongu", adim, tepe)
        if adim > limit:
            return ("limit", adim, tepe)


def altin_delay(n):
    """1'e kadar adim sayisi ve tepe."""
    adim, tepe = 0, n
    while n != 1:
        n = 3 * n + 1 if n & 1 else n >> 1
        adim += 1
        if n > tepe:
            tepe = n
    return adim, tepe


# ---------------------------------------------------------------------------

GECEN = 0
KALAN = 0


def kontrol(ad, sart, ayrinti=""):
    global GECEN, KALAN
    if sart:
        GECEN += 1
        print(f"  [OK]   {ad}")
    else:
        KALAN += 1
        print(f"  [HATA] {ad}   {ayrinti}")


def baslik(s):
    print()
    print("=" * 66)
    print(f"  {s}")
    print("=" * 66)


# ---------------------------------------------------------------------------

def test_literatur():
    """ericr.nl/wondrous glide rekor tablosundaki bilinen degerler."""
    baslik("1. LITERATUR DEGERLERI (glide)")
    bilinen = [(7, 11), (703, 132), (10087, 171), (35655, 220),
               (270271, 267), (362343, 269), (381727, 282)]
    for n, g in bilinen:
        olculen = c.dusme_testi(n)[1]
        kontrol(f"glide({n}) = {g}", olculen == g, f"olculen {olculen}")

    # Bilinen delay ve tepe degerleri
    kontrol("delay(27) = 111", c.tam_yorunge(27)[1] == 111)
    kontrol("tepe(27) = 9232", c.tam_yorunge(27)[2] == 9232)
    kontrol("glide(27) = 96", c.dusme_testi(27)[1] == 96)
    kontrol("delay(97) = 118", c.tam_yorunge(97)[1] == 118)
    kontrol("delay(871) = 178", c.tam_yorunge(871)[1] == 178)
    kontrol("delay(6171) = 261", c.tam_yorunge(6171)[1] == 261)
    kontrol("delay(77031) = 350", c.tam_yorunge(77031)[1] == 350)


def test_kucuk_sayilar():
    """1..50.000 arasi TUM sayilar icin hizli kod = altin standart."""
    baslik("2. KUCUK SAYILAR (1..50.000 tam kontrol)")
    hata = []
    for n in range(1, 50_001):
        a = altin_glide(n)
        b = c.dusme_testi(n)[:3]
        if a != b:
            hata.append((n, a, b))
            if len(hata) > 3:
                break
    kontrol("50.000 sayida glide/sonuc/tepe birebir",
            not hata, f"ilk hatalar: {hata[:3]}")

    hata = []
    for n in range(1, 20_001):
        d1 = altin_delay(n)
        durum, d2, t2, _ = c.tam_yorunge(n)
        if durum != "vardi" or (d2, t2) != d1:
            hata.append(n)
            if len(hata) > 3:
                break
    kontrol("20.000 sayida delay/tepe birebir", not hata, f"{hata[:3]}")


def test_dev_sayilar():
    """Blok hizlandirmali yol = altin standart."""
    baslik("3. DEV SAYILAR (blok yolu, 500 rastgele)")
    random.seed(1234)
    s_h = a_h = t_h = 0
    tepe_sapma = []
    for _ in range(500):
        bit = random.randrange(4100, 8000)
        n = random.getrandbits(bit) | (1 << (bit - 1)) | 1
        r = random.random()
        if r < 0.35:
            n |= (1 << random.randrange(30, 400)) - 1
        elif r < 0.6:
            n |= (1 << random.randrange(400, 2500)) - 1
        a = altin_glide(n)
        b = c.dusme_testi(n)[:3]
        if a[0] != b[0]:
            s_h += 1
        if a[1] != b[1]:
            a_h += 1
        if a[2] != b[2]:
            t_h += 1
            tepe_sapma.append(abs(c.basamak(a[2]) - c.basamak(b[2])))
    kontrol("sonuc (dustu/dongu/limit) birebir", s_h == 0, f"{s_h} hata")
    kontrol("glide birebir", a_h == 0, f"{a_h} hata")
    kontrol(f"tepe sapmasi <= 1 basamak ({t_h}/500 farkli)",
            not tepe_sapma or max(tepe_sapma) <= 1,
            f"max sapma {max(tepe_sapma) if tepe_sapma else 0}")


def test_kenar_durumlar():
    baslik("4. KENAR DURUMLAR")
    kontrol("n=1 karsi ornek DEGIL", c.dusme_testi(1)[0] == "dustu",
            str(c.dusme_testi(1)[:3]))
    kontrol("n=2 karsi ornek DEGIL", c.dusme_testi(2)[0] == "dustu")
    kontrol("n=4 karsi ornek DEGIL", c.dusme_testi(4)[0] == "dustu")
    kontrol("tam_yorunge(1) = 0 adim", c.tam_yorunge(1)[1] == 0)
    kontrol("basamak(0) = 1", c.basamak(0) == 1)
    kontrol("basamak(9) = 1", c.basamak(9) == 1)
    kontrol("basamak(10) = 2", c.basamak(10) == 2)

    # basamak() dev sayilarda str() ile ayni mi
    hata = 0
    for k in (4299, 4300, 4301, 9999, 50_000):
        if c.basamak(10 ** k) != k + 1 or c.basamak(10 ** k - 1) != k:
            hata += 1
    kontrol("basamak() 4300+ basamakta dogru", hata == 0)

    for _ in range(2000):
        n = random.randrange(1, 10 ** random.randrange(1, 40))
        if c.basamak(n) != len(str(n)):
            hata += 1
            break
    kontrol("basamak() = len(str(n))  (2000 rastgele)", hata == 0)


def test_elek():
    baslik("5. ELEK")
    kalan = c.elek_kume()
    kontrol("mod 2^24 -> 286.581 sinif", len(kalan) == 286_581, str(len(kalan)))

    # Bilinen dizi: her derinlikte hayatta kalan sayisi
    beklenen = [1, 1, 2, 3, 4, 8, 13, 19, 38, 64, 128, 226, 367, 734]
    olculen = [len(c.elek_kur(k)) for k in range(1, 15)]
    kontrol("elek dizisi literaturle ayni", olculen == beklenen,
            f"{olculen}")

    # Elenen bir sayi GERCEKTEN dusuyor mu? (elek ispatli olmali)
    hata = 0
    denendi = 0
    for _ in range(20_000):
        n = random.randrange(10 ** 22, 10 ** 23) | 1
        if not c.aday_mi(n):
            denendi += 1
            if c.dusme_testi(n)[0] != "dustu":
                hata += 1
    kontrol(f"elenen {denendi:,} sayinin hepsi gercekten dustu", hata == 0)

    # 24+ tane 1 ile biten her sayi elekten gecmeli
    gecti = all(c.aday_mi((random.randrange(10 ** 22, 10 ** 23) >> 30 << 30)
                          | ((1 << 30) - 1)) for _ in range(500))
    kontrol("24+ tane 1 ile bitenler elekten geciyor", gecti)


def test_uretim():
    baslik("6. ADAY URETIMI")
    kal = sorted(c.elek_kume())
    M = 1 << c.ELEK_K
    for bas in (23, 40, 200):
        ar, _ = c.aralik_hazirla(bas, bas)
        hata_b = hata_e = hata_s = hata_1 = 0
        bir = c.optimal_bir(bas)
        for _ in range(1500):
            n = c.rastgele_aday(ar, kal, M, bir)
            if c.basamak(n) != bas:
                hata_b += 1
            if not c.aday_mi(n):
                hata_e += 1
            if n < c.DOGRULANMIS_SINIR:
                hata_s += 1
            b = bin(n)[2:]
            if len(b) - len(b.rstrip("1")) < bir:
                hata_1 += 1
        kontrol(f"{bas} basamak: dogru boy", hata_b == 0, f"{hata_b} hata")
        kontrol(f"{bas} basamak: elekten geciyor", hata_e == 0)
        kontrol(f"{bas} basamak: 2^71 ustunde", hata_s == 0)
        kontrol(f"{bas} basamak: {bir} tane 1 ile bitiyor", hata_1 == 0)


def test_sayi_oku():
    baslik("7. GIRDI GUVENLIGI")
    kontrol("'27' -> 27", c.sayi_oku("27") == 27)
    kontrol("'2**71+3' dogru", c.sayi_oku("2**71+3") == 2 ** 71 + 3)
    kontrol("'3**13*2**54-1' dogru",
            c.sayi_oku("3**13*2**54-1") == 3 ** 13 * 2 ** 54 - 1)
    kontrol("bosluklu '2 ** 8' dogru", c.sayi_oku("2 ** 8") == 256)
    kontrol("harf reddediliyor", c.sayi_oku("import os") is None)
    kontrol("__import__ reddediliyor",
            c.sayi_oku("__import__('os')") is None)
    t = time.perf_counter()
    r = c.sayi_oku("9**9**9")
    kontrol("us kulesi reddediliyor (donmuyor)",
            r is None and time.perf_counter() - t < 1.0)
    t = time.perf_counter()
    r = c.sayi_oku("999999999999**999999")
    kontrol("dev us reddediliyor (donmuyor)",
            r is None and time.perf_counter() - t < 1.0)


def test_sirali():
    baslik("8. SIRALI TARAMA")
    M = 1 << 54
    alt, ust = 10 ** 22, 10 ** 23 - 1
    m_bas = (alt + 1 + M - 1) // M
    m_son = (ust + 1) // M
    kontrol("ilk aday 23 basamakli",
            c.basamak(m_bas * M - 1) == 23)
    kontrol("son aday 23 basamakli",
            c.basamak(m_son * M - 1) == 23)
    kontrol("ilk aday 2^71 ustunde", m_bas * M - 1 > c.DOGRULANMIS_SINIR)
    kontrol("bir onceki aday 22 basamakli",
            c.basamak((m_bas - 1) * M - 1) == 22)
    kontrol("bir sonraki aday 24 basamakli",
            c.basamak((m_son + 1) * M - 1) == 24)


def test_limitler():
    baslik("9. ADIM LIMITLERI (yanlis alarm olmamali)")
    # Glide ~ 4 x bit. Limit her boyda bunun uzerinde olmali.
    for bas in (23, 1_000, 100_000, 1_000_000):
        bit = int(bas * 3.3219)
        n = 1 << bit
        beklenen = 6.25 * c.optimal_bir(bas)
        kontrol(f"{bas:>9,} basamak: limit > beklenen glide",
                c.glide_limiti(n) > beklenen * 2,
                f"limit {c.glide_limiti(n):,} vs beklenen {beklenen:,.0f}")


def test_zaman_modeli():
    baslik("10. SURE TAHMINI")
    kal = sorted(c.elek_kume())
    M = 1 << c.ELEK_K
    # Kucuk sayilar: toplu tahmin (mod 4'te gosterilen TOPLAM satiri).
    # Eski model burada "0.00 sn" diyordu, gercek 0.4 sn idi.
    for bas, bir, adet in ((23, 0, 20_000), (23, 49, 5_000), (300, 0, 5_000)):
        ar, _ = c.aralik_hazirla(bas, bas)
        ns = [c.rastgele_aday(ar, kal, M, bir) for _ in range(200)]
        t = time.perf_counter()
        for i in range(adet):
            c.dusme_testi(ns[i % 200])
        gercek = time.perf_counter() - t
        tahmin = c.sure_tahmini(bas, bir, adet)
        oran = gercek / tahmin if tahmin else 999
        kontrol(f"{bas} basamak x {adet:,} toplu tahmin 3 kat icinde",
                0.33 < oran < 3.0,
                f"tahmin {tahmin:.3f}s gercek {gercek:.3f}s (oran {oran:.2f})")

    for bas in (5_000, 30_000):
        bir = c.optimal_bir(bas)
        ar, _ = c.aralik_hazirla(bas, bas)
        n = c.rastgele_aday(ar, kal, M, bir)
        t = time.perf_counter()
        _, g, _, _ = c.dusme_testi(n)
        gercek = time.perf_counter() - t
        tahmin = c.sure_tahmini(bas, bir)
        oran = gercek / tahmin if tahmin else 999
        kontrol(f"{bas:,} basamak tahmin/gercek 3 kat icinde",
                0.33 < oran < 3.0,
                f"tahmin {tahmin:.3f}s gercek {gercek:.3f}s (oran {oran:.2f})")
        gt = c.tahmini_glide(bir)
        kontrol(f"{bas:,} basamak glide tahmini 1.5 kat icinde",
                0.66 < g / gt < 1.5, f"tahmin {gt:,} gercek {g:,}")


def test_bilgi():
    baslik("11. BILGI EKRANI")
    kontrol("7 konu var", len(c.BILGI) == 7, str(len(c.BILGI)))
    hata = [k for k, (b, m) in c.BILGI.items() if not b or len(m) < 100]
    kontrol("her konunun basligi ve metni dolu", not hata, str(hata))
    uzun = [k for k, (b, m) in c.BILGI.items()
            if any(len(s) > 72 for s in m.split("\n"))]
    kontrol("hicbir satir 72 karakteri gecmiyor", not uzun, str(uzun))
    banner_uzun = [s for s in c.BANNER.split("\n") if len(s) > 72]
    kontrol("banner satirlari 72 karakteri gecmiyor", not banner_uzun)
    ascii_disi = [k for k, (b, m) in c.BILGI.items()
                  if not (b + m).isascii()]
    kontrol("bilgi metinleri saf ASCII (kodlama sorunu cikmaz)",
            not ascii_disi, str(ascii_disi))
    kontrol("banner saf ASCII", c.BANNER.isascii())


def main():
    print()
    print("#" * 66)
    print("#  collatz.py TEST PAKETI")
    print("#" * 66)
    t0 = time.perf_counter()
    random.seed(2026)

    test_literatur()
    test_kucuk_sayilar()
    test_dev_sayilar()
    test_kenar_durumlar()
    test_elek()
    test_uretim()
    test_sayi_oku()
    test_sirali()
    test_limitler()
    test_zaman_modeli()
    test_bilgi()

    print()
    print("=" * 66)
    print(f"  GECEN: {GECEN}    HATA: {KALAN}    "
          f"sure: {time.perf_counter() - t0:.1f} sn")
    print("=" * 66)
    return 1 if KALAN else 0


if __name__ == "__main__":
    sys.exit(main())
