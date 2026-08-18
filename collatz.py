"""
Collatz (3n+1) karsi-ornek arayicisi.

MANTIK
------
Bir sayinin Collatz sanisina UYMAMASI icin iki secenek var:
  1) Yorunge sonsuza gider (hicbir zaman 1'e varmaz)
  2) Icinde 1 olmayan yeni bir donguye girer

Her iki durum da su tek sarta esittir:
  "Sayi, kendi baslangic degerinin ALTINA hicbir zaman dusmez."

Cunku eger n bir noktada n'den kucuk bir m degerine duserse, ve m
zaten kontrol edilmisse (1'e gittigi biliniyorsa), n de 1'e gider.

Bu yuzden 1'e kadar tum yorungeyi surmeye gerek yok. Sayi baslangicin
altina indigi an "uyuyor" deriz. Hiz buradan geliyor.
"""

import math
import os
import random
import re
import sys
import time

# Python 3.11+ int->str donusumunde 4300 basamak siniri koyuyor.
# Dev sayilarla calisiyoruz, siniri aciyoruz.
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(2_000_000)

# Bugune kadar bilgisayarla dogrulanmis sinir (Baruna/Barina, ~2^71).
# Bu sinirin ALTINDAKI her sayi zaten test edilmis durumda.
DOGRULANMIS_SINIR = 2 ** 71

# Bir sayi bu kadar adimda hala baslangicin altina dusmediyse siradisi demektir.
# TABAN degerdir - buyuk sayilarda limit boyla birlikte olceklenir, cunku
# glide sayinin bit uzunlugu ile DOGRU ORANTILI buyuyor (olculdu: optimal
# yapida glide ~ 4 x bit). Sabit limit kullanilsaydi ~375.000 basamagin
# ustundeki her sayi yanlislikla "karsi ornek adayi" diye raporlanirdi.
ADIM_LIMITI = 5_000_000

# Olculen katsayilar (bkz. 1000-30000 basamak arasi olcumler):
#   glide ~  4 x bit   -> 30x kat guvenlik payi
#   delay ~ 12 x bit   -> 100x kat guvenlik payi
GLIDE_LIMIT_KAT = 30
DELAY_LIMIT_KAT = 100


def glide_limiti(n):
    return max(ADIM_LIMITI, GLIDE_LIMIT_KAT * n.bit_length())


def delay_limiti(n):
    return max(ADIM_LIMITI, DELAY_LIMIT_KAT * n.bit_length())

# Elek derinligi: 2^ELEK_K'ya gore kalan siniflari eliyoruz.
# 24 -> sayilarin %98.3'u tek islemde eleniyor, kurulum ~1 sn.
ELEK_K = 24


# ---------------------------------------------------------------------------
# ELEK: bir sayinin karsi ornek OLABILMESI icin gereken bicim
#
# n'yi  n = A*x + B  seklinde tutup adim adim ilerletiyoruz. Dusuk bitleri
# bildigimiz surece her adimda tek/cift belli. Katsayi A, baslangictaki
# 2^k'nin altina duserse o kalan sinifindaki TUM buyuk sayilar kesin duser
# -> aday olamaz. Sadece A'nin hic kuculmedigi kalanlar hayatta kalir.
# ---------------------------------------------------------------------------

_ELEK_KUME = None


def elek_kur(kmax=ELEK_K):
    """mod 2^kmax icin hayatta kalan kalanlar. Artimli kurulur (hizli)."""
    kalan = [0, 1]
    for k in range(1, kmax + 1):
        M = 1 << k
        yeni = []
        for r in kalan:
            # mod 2^(k-1) hayatta kalan r, mod 2^k'da r ve r + 2^(k-1) olur
            for r2 in (r, r + (M >> 1)):
                A, B, yasiyor = M, r2, True
                while A % 2 == 0:
                    if B % 2 == 0:
                        A //= 2
                        B //= 2
                    else:
                        A = 3 * A // 2
                        B = (3 * B + 1) // 2
                    if A < M:
                        yasiyor = False
                        break
                if yasiyor:
                    yeni.append(r2)
        kalan = sorted(set(yeni))
    return kalan


def elek_kume():
    global _ELEK_KUME
    if _ELEK_KUME is None:
        print(f"  (elek kuruluyor: mod 2^{ELEK_K} ...)", end="", flush=True)
        t = time.perf_counter()
        _ELEK_KUME = set(elek_kur())
        print(f" {len(_ELEK_KUME):,} kalan sinifi, {time.perf_counter()-t:.1f} sn")
    return _ELEK_KUME


def aday_mi(n):
    """False ise: bu sayi kesinlikle karsi ornek DEGIL, test etmeye gerek yok."""
    return (n % (1 << ELEK_K)) in elek_kume()


def sayi_oku(metin):
    """'2**71+3' gibi ifadeleri de kabul eder. Sadece sayi ve + - * ** ( ) izinli."""
    metin = metin.strip().replace(" ", "").replace("_", "")
    if not metin:
        return None
    if metin.isdigit():
        return int(metin)
    if not re.fullmatch(r"[0-9+\-*()]+", metin):
        return None

    # eval'i calistirmadan ONCE boyut kontrolu. "9**9**9" gibi bir ifade
    # hesaplanmaya kalkilsa program saatlerce donar (us kulesi).
    if "**" in metin:
        if re.search(r"\*\*[^*]*\*\*", metin):
            print("  Us kulesi (a**b**c) kabul edilmiyor - sonuc astronomik olur.")
            return None
        for taban, us in re.findall(r"(\d+)\s*\*\*\s*\(?\s*(\d+)", metin):
            if len(taban) * int(us) > 2 * MAX_BASAMAK:
                print(f"  Cok buyuk: ~{len(taban)*int(us):,} basamak "
                      f"(ust sinir {2*MAX_BASAMAK:,}).")
                return None
    try:
        return int(eval(metin, {"__builtins__": {}}, {}))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# BLOK HIZLANDIRMA (dev sayilar icin)
#
# Sayinin son BLOK_K biti, sonraki BLOK_K adimin tamamini belirler. Bunu
# onceden tabloya alirsak, n = a*2^K + b icin K adim tek islemde atilir:
#     n_yeni = a * CARP[b] + EKLE[b]
# Yani milyon basamakli sayiya K kez degil, BIR kez dokunuyoruz.
# Olculen kazanc: 20.000 basamakta ~15 kat.
# ---------------------------------------------------------------------------

BLOK_K = 16
BLOK_MASKE = (1 << BLOK_K) - 1
BLOK_ESIK = 4096          # bu bit uzunlugunun ustunde blok kullan
_BLOK = None


def blok_tablo():
    """CARP / EKLE / ADIM tablolari. Bir kez kurulur (~0.15 sn)."""
    global _BLOK
    if _BLOK is None:
        carp = [0] * (BLOK_MASKE + 1)
        ekle = [0] * (BLOK_MASKE + 1)
        adim = [0] * (BLOK_MASKE + 1)
        for b in range(BLOK_MASKE + 1):
            m, x, s = 1, b, 0
            for _ in range(BLOK_K):
                if x & 1:
                    m *= 3
                    x = (3 * x + 1) >> 1
                    s += 2          # 3n+1 ve /2 = 2 standart adim
                else:
                    x >>= 1
                    s += 1
            carp[b], ekle[b], adim[b] = m, x, s
        _BLOK = (carp, ekle, adim)
    return _BLOK


def _tek_adim(n):
    """Tek bir standart Collatz adimi."""
    return 3 * n + 1 if n & 1 else n >> 1


def _tepe_kesinlestir(tepe, kaynak, kalan_adim):
    """
    Blok yontemi tepeyi blok uclarindan gorur; gercek tepe (bir 3n+1 degeri)
    blogun icinde kalmis olabilir. Kaynak blogun basindan iki blok boyunca
    tek tek ilerleyip kesin tepeyi buluruz. Sadece bir kez calisir.

    kalan_adim: yorungenin GERCEKTEN gittigi adim sayisi. Bunu asarsak
    yorungede hic olusmamis degerleri tepe sanardik.
    """
    x = kaynak
    for _ in range(min(4 * BLOK_K, kalan_adim)):
        x = _tek_adim(x)
        if x > tepe:
            tepe = x
    return tepe


def _dusme_blok(n):
    """
    Dev sayilar icin blok hizlandirmali dusme testi.

    KRITIK: blok sadece uc noktayi gorur. Sayi blogun ICINDE baslangicin
    altina inip tekrar cikarsa blok bunu kacirir. Bu yuzden:

      - n, baslangictan BLOK_K+1 bitten fazla buyukse:  blok guvenli.
        (bir blok en fazla 2^BLOK_K kat kucultebilir, altina inemez)
      - yaklastiginda:  tek tek adim at, kesin sonuc.

    Boylece uzun tirmanis hizli gecilir, kritik bolge kesin taranir.
    """
    carp, ekle, badim = blok_tablo()
    baslangic = n
    guvenli_bit = baslangic.bit_length() + BLOK_K + 1
    limit = glide_limiti(n)
    adim = 0
    tepe = n
    # Gercek tepe (bir 3n+1 degeri) her zaman, en yuksek blok-ucunu ureten
    # blogun ya kendisinde ya da hemen sonrakinde olur: yorunge o noktaya
    # kadar yukselip sonra duser. Bu yuzden o blogun BASLANGICINI saklayip
    # sonunda sadece o iki blogu tek tek tariyoruz.
    tepe_kaynak = n
    tepe_kaynak_adim = 0

    while True:
        if n.bit_length() > guvenli_bit:
            onceki = n
            b = n & BLOK_MASKE
            n = (n >> BLOK_K) * carp[b] + ekle[b]
            adim += badim[b]
            if n > tepe:
                tepe = n
                tepe_kaynak = onceki
                tepe_kaynak_adim = adim - badim[b]
            if adim > limit:
                return ("limit", adim, _tepe_kesinlestir(tepe, tepe_kaynak, adim - tepe_kaynak_adim))
        else:
            n = _tek_adim(n)
            adim += 1
            if n > tepe:
                tepe = n
            if n < baslangic:
                return ("dustu", adim, _tepe_kesinlestir(tepe, tepe_kaynak, adim - tepe_kaynak_adim))
            if n == baslangic:
                return ("dongu", adim, _tepe_kesinlestir(tepe, tepe_kaynak, adim - tepe_kaynak_adim))
            if adim > limit:
                return ("limit", adim, _tepe_kesinlestir(tepe, tepe_kaynak, adim - tepe_kaynak_adim))


def dusme_testi(n):
    """
    n baslangic degerinin altina dusene kadar calisir.

    Doner: (sonuc, adim, tepe, sure)
      sonuc = "dustu"  -> uyuyor, karsi ornek degil
      sonuc = "dongu"  -> KARSI ORNEK (yeni dongu)
      sonuc = "limit"  -> adim limiti asildi, siradisi durum
    """
    # n = 1 zaten 4-2-1 dongusunun icinde. Kendine geri dondugu icin "dongu"
    # gorunur ve YANLISLIKLA karsi ornek diye raporlanirdi - ozel durum.
    if n <= 2:
        return ("dustu", 0, n, 0.0)

    if n.bit_length() > BLOK_ESIK and n % 2:
        t0 = time.perf_counter()
        s, a, tp = _dusme_blok(n)
        return (s, a, tp, time.perf_counter() - t0)

    baslangic = n
    adim = 0
    tepe = n
    limit = glide_limiti(n)
    t0 = time.perf_counter()

    # Cift sayilar zaten ilk adimda yariya iner, o yuzden tek sayiya indirgiyoruz.
    if n % 2 == 0:
        return ("dustu", 1, n, time.perf_counter() - t0)

    while True:
        # Tek sayi: 3n+1. Tepe HER ZAMAN burada olusur (bolme sadece kucultur),
        # o yuzden karsilastirma bolmeden ONCE yapilmali.
        v = 3 * n + 1
        adim += 1
        if v > tepe:
            tepe = v

        # Tum 2 carpanlarini tek islemde at (hizli yol).
        sifirlar = (v & -v).bit_length() - 1
        w = v >> sifirlar

        if w >= baslangic:
            # Kaydirma sirasinda hicbir ara deger baslangicin altina inmedi
            # (bolme monoton azalir, en kucugu w). Hepsini birden sayabiliriz.
            adim += sifirlar
            n = w
            if n == baslangic:
                return ("dongu", adim, tepe, time.perf_counter() - t0)
            if adim > limit:
                return ("limit", adim, tepe, time.perf_counter() - t0)
        else:
            # Bu kaydirma sirasinda ILK KEZ altina indi. Glide'in tanimi
            # "her adimda kontrol" oldugu icin tam adimi bulmak zorundayiz.
            for j in range(1, sifirlar + 1):
                adim += 1
                u = v >> j
                if u < baslangic:
                    return ("dustu", adim, tepe, time.perf_counter() - t0)
                if u == baslangic:
                    return ("dongu", adim, tepe, time.perf_counter() - t0)


def tam_yorunge(n, kayit_tut=False):
    """
    1'e kadar tam yorunge. Doner: (durum, adim, tepe, yol)
      durum = "vardi" -> 1'e ulasti, YAKINSAMA ISPATLANDI
      durum = "dongu" -> baslangica geri dondu, KARSI ORNEK
      durum = "limit" -> adim limiti asildi, sonuc belirsiz
    """
    baslangic = n
    adim = 0
    tepe = n
    limit = delay_limiti(n)
    yol = [n] if kayit_tut else None

    while n != 1:
        n = 3 * n + 1 if n % 2 else n >> 1
        adim += 1
        if n > tepe:
            tepe = n
        if kayit_tut and len(yol) < 200:
            yol.append(n)
        if n == baslangic:
            return ("dongu", adim, tepe, yol)
        if adim > limit:
            return ("limit", adim, tepe, yol)
    return ("vardi", adim, tepe, yol)


LOG2_10 = math.log10(2)


def basamak(n):
    """
    Basamak sayisi. str(n) KULLANMAZ - dev sayilarda hem yavas hem de
    Python'un 4300 basamak sinirina takiliyordu. Bit uzunlugundan hesaplar.
    """
    if n < 0:
        n = -n
    if n < 10:
        return 1
    d = int(n.bit_length() * LOG2_10) + 1
    # Yuvarlama yuzunden 1 sapabilir, duzelt
    if 10 ** (d - 1) > n:
        d -= 1
    elif 10 ** d <= n:
        d += 1
    return d


def sayi_ozet(n, esik=100):
    """Uzun sayilari konsolda kisaltir: bas...son (N basamak)"""
    b = basamak(n)
    if b <= esik:
        return str(n)
    s = str(n)
    return f"{s[:45]}...{s[-45:]}  [{b} basamak]"


def sayi_kayit(n, tam_sinir=2000):
    """
    Kayit dosyasi icin sayi bicimi. Rekor satirlarinda dev sayilarin tamamini
    yazmak dosyayi okunamaz hale getiriyor (9999 basamak = 10.000 karakterlik
    tek satir), o yuzden buyukleri kisaltiyoruz.

    KARSI ORNEK bulunursa bu fonksiyon KULLANILMAZ - orada tam sayi yazilir.
    """
    b = basamak(n)
    if b <= tam_sinir:
        return str(n)
    s = str(n)
    return f"{s[:60]}...{s[-60:]}  [{b} basamak, ortasi kisaltildi]"


KAYIT_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "collatz_kayit.txt")


def kayit_yaz(*satirlar):
    """Sonuclari diske yazar - tarama coksede kaybolmasin."""
    try:
        with open(KAYIT_DOSYASI, "a", encoding="utf-8") as f:
            for s in satirlar:
                f.write(s + "\n")
    except OSError as e:
        print(f"  [kayit yazilamadi: {e}]")


def tek_sayi_kontrol(n):
    print()
    print("=" * 62)
    print(f"Sayi   : {sayi_ozet(n)}")
    print(f"Basamak: {basamak(n)}  |  Bit: {n.bit_length()}")

    if n < 1:
        print("HATA: 1 veya daha buyuk pozitif tam sayi girmelisin.")
        print("=" * 62)
        return

    if n < DOGRULANMIS_SINIR:
        print(f"NOT    : Bu sayi 2^71 sinirinin altinda -> zaten dogrulanmis")
        print(f"         bolgede. Karsi ornek CIKMASI imkansiz.")
    else:
        gecti = aday_mi(n)
        if gecti:
            print("ELEK   : GECTI - bu sayi bicim olarak aday olabilir.")
        else:
            print(f"ELEK   : ELENDI - n mod 2^{ELEK_K} kalani hemen dusuyor.")
            print("         Bu sayi kesinlikle karsi ornek DEGIL.")

    sonuc, adim, tepe, sure = dusme_testi(n)
    print("-" * 62)

    if sonuc == "dustu":
        # Dusme testi tek basina sadece "en kucuk karsi ornek degil" der.
        # Kesin sonuc icin yorungeyi 1'e kadar suruyoruz.
        t0 = time.perf_counter()
        durum, t_adim, t_tepe, _ = tam_yorunge(n)
        t_tam = time.perf_counter() - t0
        if durum == "vardi":
            print("SONUC  : UYUYOR  (yakinsama ISPATLANDI)")
            print(f"         Dusme testi : {adim:,} adimda altina dustu "
                  f"({sure * 1000:.2f} ms)")
            print(f"         Tam yorunge : {t_adim:,} adimda 1'e vardi "
                  f"({sure_yazi(t_tam)})")
            print(f"         Tepe        : {basamak(t_tepe):,} basamak "
                  f"(baslangic {basamak(n):,}, +{basamak(t_tepe)-basamak(n)})")
            print(f"         {sayi_ozet(t_tepe)}")
        elif durum == "dongu":
            print("!" * 62)
            print("SONUC  : *** UYMUYOR - YENI DONGU BULUNDU ***")
            print(f"         {t_adim} adim sonra kendine geri dondu.")
            print("!" * 62)
        else:
            print("SONUC  : BELIRSIZ - dusme testini gecti ama 1'e varmadi.")
            print(f"         {t_adim} adimda adim limiti asildi.")
    elif sonuc == "dongu":
        print("!" * 62)
        print("SONUC  : *** UYMUYOR - YENI DONGU BULUNDU ***")
        print(f"         Sayi {adim} adim sonra kendine geri dondu.")
        print(f"         Tepe deger: {tepe}")
        print("!" * 62)
    else:
        print("!" * 62)
        print("SONUC  : *** SIRADISI - ADIM LIMITI ASILDI ***")
        print(f"         {adim} adimdir baslangicin altina dusmedi.")
        print(f"         Su anki tepe: {basamak(tepe)} basamakli sayi")
        print(f"         Sure: {sure:.2f} sn")
        print("         (Limiti artirip tekrar dene: ADIM_LIMITI)")
        print("!" * 62)

    print("=" * 62)


def aralik_tara(bas, son):
    """
    Bir araligi tarar.

    Optimizasyon: sadece n % 4 == 3 olan sayilari test etmek yeterli.
      - Cift sayilar: ilk adimda yariya iner, hemen duser.
      - n = 4k+1 : birkac adimda 3k+1 < n olur, hemen duser.
      Geriye sadece 4k+3 kaliyor. Yani isin %75'i bedava eleniyor.
    """
    if bas < 1:
        bas = 1
    print()
    print(f"Taraniyor: {bas} .. {son}")
    print("(sadece n mod 4 == 3 olanlar test ediliyor - digerleri ispatli)")
    print("Durdurmak icin Ctrl+C")
    print("-" * 62)

    # Ilk 4k+3 sayiya hizala
    n = bas + ((3 - bas % 4) % 4)
    sayac = 0
    en_uzun = (0, 0)      # (adim, sayi)
    en_yuksek = (0, 0)    # (tepe, sayi)
    t0 = time.perf_counter()
    son_rapor = t0

    try:
        while n <= son:
            sonuc, adim, tepe, _ = dusme_testi(n)

            if sonuc != "dustu":
                print()
                print("!" * 62)
                print(f"*** KARSI ORNEK ADAYI: {sayi_ozet(n)}  ({sonuc}) ***")
                print(f"    adim={adim}")
                print("!" * 62)
                kayit_yaz("", "!!! KARSI ORNEK ADAYI (aralik tarama) !!!",
                          f"durum : {sonuc}",
                          f"adim  : {adim}",
                          f"n     : {n}",
                          f"tepe  : {tepe}", "")
                return

            if adim > en_uzun[0]:
                en_uzun = (adim, n)
            if tepe > en_yuksek[0]:
                en_yuksek = (tepe, n)

            sayac += 1
            simdi = time.perf_counter()
            if simdi - son_rapor > 1.0:
                gecen = simdi - t0
                hiz = sayac / gecen
                oran = (n - bas) / (son - bas) if son > bas else 1
                kalan = gecen * (1 - oran) / oran if oran > 0 else 0
                print(f"\r  {n:>22}  |  {oran*100:>6.2f}%  |  "
                      f"{hiz:>9,.0f} test/sn  |  kalan {sure_yazi(kalan):>12}",
                      end="", flush=True)
                son_rapor = simdi

            n += 4
    except KeyboardInterrupt:
        print("\n  [durduruldu]")

    gecen = time.perf_counter() - t0
    print()
    print("-" * 62)
    print(f"Test edilen : {sayac:,}")
    print(f"Sure        : {gecen:.2f} sn"
          f"  ({sayac / gecen if gecen else 0:,.0f} test/sn)")
    print(f"En cok adim : {en_uzun[0]} adim -> n = {en_uzun[1]}")
    print(f"En yuksek   : {basamak(en_yuksek[0])} basamak -> n = {en_yuksek[1]}")
    if bas <= DOGRULANMIS_SINIR:
        # Kucukten basladik: altimizdaki her sayi zaten dogrulanmis,
        # dolayisiyla "dustu" = "yakinsadi". Sonuc kesin.
        print("KARSI ORNEK BULUNAMADI. (yakinsama ispatli)")
    else:
        print("EN KUCUK KARSI ORNEK ADAYI BULUNAMADI.")
        print("(Aralik 2^71'in ustunde basladigi icin 'dustu' sonucu")
        print(" yakinsamayi ispatlamaz, sadece en kucuk olmadigini gosterir.)")
    print("-" * 62)


def sure_yazi(saniye):
    """Saniyeyi okunabilir sureye cevirir: 0.83 sn / 12dk 4sn / 3g 4sa 12dk"""
    if saniye < 10:
        return f"{saniye:.2f} sn"
    saniye = int(saniye)
    g, saniye = divmod(saniye, 86400)
    sa, saniye = divmod(saniye, 3600)
    dk, sn = divmod(saniye, 60)
    if g:
        return f"{g}g {sa}sa {dk}dk"
    if sa:
        return f"{sa}sa {dk}dk"
    if dk:
        return f"{dk}dk {sn}sn"
    return f"{sn}sn"


# Ust sinirlar. 10**b bir tamsayi olarak bellekte tutuluyor: 1.000.000
# basamak ~415 KB, sorun degil. Asil maliyet tam yorungede (bkz. asagi).
MAX_BASAMAK = 1_000_000
# Kac farkli boy istenebilir: her boy icin iki dev sayi saklaniyor.
MAX_BOY_SAYISI = 1000
# Bu boya kadar tam yorunge otomatik calisir; ustunde kullaniciya sorulur.
TAM_YORUNGE_OTOMATIK = 20_000


# ---------------------------------------------------------------------------
# SURE TAHMINI ve MAKINE KALIBRASYONU
#
# Bu kod her makinede farkli hizda calisir. Sabit bir tahmin yazmak yerine
# programin kendisi bir olcum yapip kendi makinesine gore olcekliyor.
#
# Olculen model (bkz. 2.000-60.000 basamak arasi olcumler):
#     glide  ~  6.25 x (1-dizisi uzunlugu)
#     sure   ~  K x basamak x glide
# Ikisi de genis araliklarda sabit cikti (oran 6.19 - 6.54).
# ---------------------------------------------------------------------------

# Referans makinede (gelistirme makinesi) olculen degerler
KALIBRE_SAYI_US = (6000, 20000)      # 3^6000 * 2^20000 - 1  (8.884 basamak)
KALIBRE_REFERANS_SN = 0.0145         # o makinede dusme testi suresi
K_SURE = 1.10e-11                    # sure = K * basamak * glide
GLIDE_KAT = 6.25                     # glide = GLIDE_KAT * bir_sayisi

_MAKINE_FAKTORU = None


def makine_faktoru():
    """
    Bu makinenin referans makineye gore hiz orani.
    1.0 = ayni hiz, 2.0 = iki kat yavas, 0.5 = iki kat hizli.
    Bir kez olculur (~0.05 sn).
    """
    global _MAKINE_FAKTORU
    if _MAKINE_FAKTORU is None:
        blok_tablo()                                   # isinma
        a, b = KALIBRE_SAYI_US
        n = 3 ** a * 2 ** b - 1
        t = time.perf_counter()
        dusme_testi(n)
        olculen = time.perf_counter() - t
        _MAKINE_FAKTORU = max(0.05, olculen / KALIBRE_REFERANS_SN)
    return _MAKINE_FAKTORU


def tahmini_glide(bir_sayisi):
    """1-dizisi uzunlugundan beklenen glide."""
    return max(70, int(GLIDE_KAT * bir_sayisi))


# Adim basina maliyetin alt siniri. Kucuk sayilarda maliyet basamak
# sayisiyla degil, Python'un sabit islem yuku ile belirleniyor - olculdu:
# 23 basamakta 8.9e-8, 100 basamakta 1.0e-7 sn/adim.
TABAN_ADIM_SN = 1.0e-7
# Blok esiginin ALTINDA blok hizlandirma calismaz; adim basina maliyet
# ~BLOK_K kat yuksektir (olculdu: 1000 basamakta 2.3e-7 vs beklenen 1.1e-8).
KUCUK_YOL_KAT = 16


def adim_maliyeti(basamak):
    """Bu boyda bir adimin kac saniye surdugu (makine faktorusuz)."""
    bit = basamak * 3.3219
    kat = KUCUK_YOL_KAT if bit <= BLOK_ESIK else 1
    return max(TABAN_ADIM_SN, kat * K_SURE * basamak)


def sure_tahmini(basamak, bir_sayisi, adet=1):
    """Dusme testinin bu makinede kac saniye surecegi."""
    return (adim_maliyeti(basamak) * tahmini_glide(bir_sayisi)
            * adet * makine_faktoru())


def yorunge_tahmin(d):
    """Tam yorunge (1'e kadar) tahmini. Dusme testinden ~3 kat uzun."""
    return 3.0 * K_SURE * d * (12 * int(d * 3.3219) / 6.25) * makine_faktoru()


def makine_bilgisi():
    """Kullaniciya gosterilecek makine ozeti."""
    import platform
    f = makine_faktoru()
    if f < 0.7:
        yorum = "referanstan HIZLI"
    elif f < 1.5:
        yorum = "referansa yakin"
    elif f < 3:
        yorum = "referanstan yavas"
    else:
        yorum = "referanstan cok yavas"
    islemci = platform.processor() or platform.machine() or "bilinmiyor"
    return f, yorum, islemci


def aralik_hazirla(bas_basamak, son_basamak):
    """
    Basamak araligini dogrular ve her boy icin (alt, ust) sinirlarini hazirlar.
    Hata varsa (None, None) doner.
    """
    if bas_basamak < 22:
        print(f"  UYARI: {bas_basamak} basamak, 2^71 sinirinin altinda kalir.")
        print("         En az 22 (guvenli olmasi icin 23) basamak gir.")
        return None, None
    if bas_basamak > MAX_BASAMAK:
        print(f"  UYARI: {bas_basamak:,} basamak cok fazla.")
        print(f"         Ust sinir {MAX_BASAMAK:,} basamak.")
        print(f"         (Daha buyugu icin bellek ve sure makul olmaktan cikiyor)")
        return None, None
    if son_basamak < bas_basamak:
        son_basamak = bas_basamak
    if son_basamak > MAX_BASAMAK:
        print(f"  NOT: ust sinir {MAX_BASAMAK:,} basamaga kirpildi.")
        son_basamak = MAX_BASAMAK
    if son_basamak - bas_basamak + 1 > MAX_BOY_SAYISI:
        eski = son_basamak
        son_basamak = bas_basamak + MAX_BOY_SAYISI - 1
        print(f"  NOT: en fazla {MAX_BOY_SAYISI:,} farkli boy secilebilir.")
        print(f"       Aralik {bas_basamak:,}-{eski:,} yerine "
              f"{bas_basamak:,}-{son_basamak:,} yapildi.")

    print(f"  (aralik hazirlaniyor...)", end="", flush=True)
    t0 = time.perf_counter()
    araliklar = [(10 ** (b - 1), 10 ** b - 1)
                 for b in range(bas_basamak, son_basamak + 1)]
    print(f"\r  (aralik hazir, {time.perf_counter() - t0:.1f} sn)      ")
    return araliklar, son_basamak


def rastgele_aday(araliklar, kalanlar, M, bir_sayisi=0):
    """
    Elekten gecen, 2^71'in ustunde rastgele bir sayi uretir.
    Once boy secilir (her boy esit sansli), sonra o boydan rastgele taban,
    sonra elekten gecen bir kalan sinifina oturtulur.

    bir_sayisi > 0 ise: sayinin son N biti 1 yapilir (n = m*2^N - 1 bicimi).
    Bu yapi rekortmenlerde gozlenen yapidir - sayi N tur boyunca kesintisiz
    yukselir, her turda 1.5 katina cikarak. Olculen etki: ortalama adim
    sayisi ~4 kat artiyor, en uc deger ~1.4 kat.

    Not: son 24+ biti 1 olan bir sayi elegi zaten otomatik gecer (bu, en uzun
    tirmanan kalan sinifinin ta kendisi), o yuzden ayrica elek kontrolu yok.
    """
    while True:
        alt, ust = random.choice(araliklar)
        taban = random.randrange(alt, ust + 1)
        if bir_sayisi > 0:
            n = taban | ((1 << bir_sayisi) - 1)
            if bir_sayisi < ELEK_K and (n % M) not in elek_kume():
                continue
        else:
            n = (taban - taban % M) + random.choice(kalanlar)
        if n >= DOGRULANMIS_SINIR:
            return n


def optimal_bir(basamak):
    """
    O boy icin optimal 1-dizisi uzunlugu: bit sayisinin %65'i.
    Bu oran olculdu (bkz. 23 basamakta yapilan tarama): uc glide degerini
    en yukseye cikaran nokta. Daha azi tirmanisi kisaltiyor, daha fazlasi
    sayiyi tamamen belirlenmis hale getirip sansa yer birakmiyor.
    """
    bit = int(basamak * 3.3219)          # basamak -> bit
    return max(ELEK_K, int(bit * 0.65))


def tek_tek_dene(bas_basamak, son_basamak, bir_sayisi=0):
    """
    Mod 5: aralik bir kez secilir, sonra her 'y' icin tek bir rastgele sayi
    denenir ve sonucu tam olarak gosterilir. 'n' menuye doner.
    """
    araliklar, son_basamak = aralik_hazirla(bas_basamak, son_basamak)
    if araliklar is None:
        return
    M = 1 << ELEK_K
    kalanlar = sorted(elek_kume())

    boy = (f"{bas_basamak}" if bas_basamak == son_basamak
           else f"{bas_basamak}-{son_basamak}") + " basamak"
    if bir_sayisi:
        boy += f"  |  son {bir_sayisi} bit = 1"
    print()
    print("=" * 62)
    print(f"TEK TEK DENEME MODU  |  {boy}")
    ort = (bas_basamak + son_basamak) // 2
    fak, yorum, islemci = makine_bilgisi()
    print(f"Islemci: {islemci}")
    print(f"Hiz    : {fak:.2f}x referans ({yorum})")
    print(f"Sayi basina beklenen sure: "
          f"~{sure_yazi(sure_tahmini(ort, bir_sayisi))}")
    print("Enter/y = yeni sayi   h = son sayinin haritasi   n = cikis")
    print("=" * 62)

    sayac = 0
    son_test = None          # 'h' komutu icin: son denenen sayinin sonuclari

    while True:
        try:
            cevap = input(f"\n[{sayac}] > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if cevap in ("n", "q", "cikis", "hayir", "hayır", "exit"):
            print("  Menuye donuluyor.")
            return

        if cevap in ("h", "harita", "map"):
            if son_test is None:
                print("  Once bir sayi dene (Enter).")
            else:
                harita_goster(*son_test)
            continue

        if cevap not in ("", "y", "e", "evet", "yes"):
            print("  Enter/y = yeni sayi,  h = harita,  n = cikis")
            continue

        sayac += 1
        n = rastgele_aday(araliklar, kalanlar, M, bir_sayisi)
        try:
            sonuc, adim, tepe, sure = dusme_testi(n)
        except KeyboardInterrupt:
            print("\n  [test durduruldu - Enter ile devam]")
            continue

        son_test = (n, sonuc, adim, tepe, sure)

        if sonuc == "dustu":
            # HIZLI MOD: tek satir ozet. Ayrinti isteyen 'h' basar.
            yak = "~" if n.bit_length() > BLOK_ESIK else ""
            print(f"[{sayac:>4}] elendi | glide {adim:>12,} | tepe {yak}+"
                  f"{basamak(tepe) - basamak(n):,} basamak | {sure_yazi(sure)}")
        else:
            print("!" * 62)
            print(f"[{sayac}] *** KARSI ORNEK ADAYI ({sonuc}) ***")
            print(f"    {adim:,} adimdir baslangicin altina dusmedi")
            print(f"    TAM SAYI -> {KAYIT_DOSYASI}")
            print("!" * 62)
            kayit_yaz("", "!!! KARSI ORNEK ADAYI (tek tek deneme) !!!",
                      f"durum : {sonuc}", f"adim  : {adim}",
                      f"n     : {n}", "")


def harita_goster(n, sonuc, adim, tepe, sure):
    """'h' komutu: son denenen sayinin ayrintili raporu + tam yorunge."""
    print()
    print("-" * 62)
    print(f"Sayi   : {sayi_ozet(n)}")
    print(f"Basamak: {basamak(n):,}  |  Bit: {n.bit_length():,}")

    if sonuc != "dustu":
        print(f"Dusme  : DUSMEDI ({sonuc}) - {adim:,} adim")
        print("-" * 62)
        return

    yak = "~" if n.bit_length() > BLOK_ESIK else ""
    print(f"Glide  : {adim:,} adimda baslangicin altina dustu "
          f"({sure_yazi(sure)})")
    print(f"Tepe   : {yak}{basamak(tepe):,} basamak "
          f"(+{basamak(tepe) - basamak(n):,})"
          + ("   (blok yontemi: +-1 basamak)" if yak else ""))

    d = basamak(n)
    if d > TAM_YORUNGE_OTOMATIK:
        print(f"NOT    : tam yorunge ~{sure_yazi(yorunge_tahmin(d))} surebilir")
        try:
            c = input("         Calistirilsin mi? (y/n) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if c not in ("", "y", "e", "evet", "yes"):
            print("SONUC  : EN KUCUK KARSI ORNEK DEGIL "
                  "(tam yorunge calistirilmadi)")
            print("-" * 62)
            return

    t0 = time.perf_counter()
    try:
        durum, t_adim, t_tepe, _ = tam_yorunge(n)
    except KeyboardInterrupt:
        print("\n  [tam yorunge durduruldu]")
        print("-" * 62)
        return
    t_tam = time.perf_counter() - t0

    if durum == "vardi":
        print(f"SONUC  : UYUYOR - yorunge 1'e vardi, {t_adim:,} adim "
              f"({sure_yazi(t_tam)})")
    elif durum == "dongu":
        print("!" * 62)
        print(f"SONUC  : *** UYMUYOR - DONGU *** ({t_adim:,} adim)")
        print(f"         TAM SAYI -> {KAYIT_DOSYASI}")
        print("!" * 62)
        kayit_yaz("", "!!! KARSI ORNEK (tek tek deneme) !!!",
                  "durum : dongu", f"adim  : {t_adim}", f"n     : {n}", "")
    else:
        print(f"SONUC  : BELIRSIZ - dustu ama 1'e varmadi "
              f"({t_adim:,} adimda limit asildi)")
    print("-" * 62)


DURUM_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "collatz_durum.txt")


def durum_oku(basamak, bir_sayisi):
    """Ayni ayarla yarim kalmis tarama varsa kaldigi m degerini doner."""
    try:
        with open(DURUM_DOSYASI, encoding="utf-8") as f:
            b, k, m = f.read().split()
        if int(b) == basamak and int(k) == bir_sayisi:
            return int(m)
    except (OSError, ValueError):
        pass
    return None


def durum_yaz(basamak, bir_sayisi, m):
    try:
        with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
            f.write(f"{basamak} {bir_sayisi} {m}")
    except OSError:
        pass


def sirali_tara(basamak, bir_sayisi, devam=True):
    """
    SIRALI tarama: n = m * 2^k - 1 bicimindeki TUM sayilari, m'yi birer birer
    artirarak dener. Rastgele taramanin aksine:
      - her aday tam olarak BIR kez test edilir (tekrar yok)
      - kapsama yuzdesi gercek anlam tasir
      - uzay bitince "bu bicimde karsi ornek YOKTUR" denebilir - kesin sonuc
    Ctrl+C ile durdurulur, ayni komutla kaldigi yerden devam eder.
    """
    k = bir_sayisi
    if k < ELEK_K:
        print(f"  UYARI: sirali tarama icin son bit sayisi en az {ELEK_K} olmali")
        print(f"         (kucuk k'da uzay cok buyuk, sirali bitmez).")
        return
    M = 1 << k
    alt, ust = 10 ** (basamak - 1), 10 ** basamak - 1
    m_bas = (alt + 1 + M - 1) // M
    m_son = (ust + 1) // M
    if m_son < m_bas:
        print(f"  {basamak} basamakta son {k} biti 1 olan sayi yok.")
        return
    toplam = m_son - m_bas + 1

    m = m_bas
    if devam:
        kaldi = durum_oku(basamak, k)
        if kaldi is not None and m_bas <= kaldi <= m_son:
            m = kaldi
            print(f"  (kaldigi yerden devam: {m - m_bas:,} / {toplam:,})")

    print()
    print(f"SIRALI TARAMA  |  {basamak} basamak, n = m * 2^{k} - 1")
    print(f"Toplam aday : {toplam:,}")
    print(f"Kalan       : {m_son - m + 1:,}")
    print("Durdurmak icin Ctrl+C (kaldigi yerden devam eder)")
    print("-" * 62)
    kayit_yaz("=" * 70,
              f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SIRALI tarama: "
              f"{basamak} basamak, m*2^{k}-1, m={m:,}..{m_son:,}")

    en_uzun = (0, 0)
    sayac = 0
    t0 = time.perf_counter()
    son_rapor = t0
    try:
        while m <= m_son:
            n = m * M - 1
            if n >= DOGRULANMIS_SINIR:
                sonuc, adim, tepe, _ = dusme_testi(n)
                if sonuc != "dustu":
                    print()
                    print("!" * 62)
                    print(f"*** KARSI ORNEK ({sonuc}) ***")
                    print(f"    n = {sayi_ozet(n)}")
                    print(f"    m = {m}   adim = {adim}")
                    print(f"    TAM SAYI -> {KAYIT_DOSYASI}")
                    print("!" * 62)
                    kayit_yaz("", "!!! KARSI ORNEK (sirali tarama) !!!",
                              f"durum : {sonuc}", f"adim  : {adim}",
                              f"m     : {m}", f"n     : {n}", "")
                    durum_yaz(basamak, k, m)
                    return
                if adim > en_uzun[0]:
                    en_uzun = (adim, n)
                    kayit_yaz(f"[adim rekoru] {adim} adim | m={m} | "
                              f"n = {sayi_kayit(n)}")
                sayac += 1
            m += 1

            simdi = time.perf_counter()
            if simdi - son_rapor > 1.0:
                gecen = simdi - t0
                hiz = sayac / gecen if gecen else 0
                bitti = m - m_bas
                oran = bitti / toplam
                kalan = (m_son - m) / hiz if hiz else 0
                print(f"\r  {bitti:>13,} / {toplam:,}  |  {oran:>7.3%}  |  "
                      f"{hiz:>9,.0f}/sn  |  kalan {sure_yazi(kalan):>12}",
                      end="", flush=True)
                son_rapor = simdi
                durum_yaz(basamak, k, m)
    except KeyboardInterrupt:
        durum_yaz(basamak, k, m)
        print(f"\n  [durduruldu - m={m:,} kaydedildi, ayni komutla devam eder]")
        return

    gecen = time.perf_counter() - t0
    durum_yaz(basamak, k, m_son + 1)
    print()
    print("-" * 62)
    print(f"TAMAMLANDI. {sayac:,} aday, {sure_yazi(gecen)}")
    print(f"En cok adim : {en_uzun[0]}")
    if en_uzun[1]:
        print(f"              n = {sayi_ozet(en_uzun[1])}")
    print()
    print(f"SONUC: {basamak} basamakli, m*2^{k}-1 bicimindeki")
    print(f"       HICBIR sayi karsi ornek DEGIL. Uzay tamamen tarandi.")
    kayit_yaz(f"[TAMAMLANDI] {basamak} basamak m*2^{k}-1 uzayi bitti, "
              f"{sayac:,} aday, karsi ornek yok", "")
    print("-" * 62)


def aday_tara(bas_basamak, son_basamak, adet, bir_sayisi=0):
    """
    Belirtilen basamak ARALIGINDA rastgele ADAY sayilar uretip test eder.

    Ornek: bas=50, son=51 -> 50 ve 51 basamakli sayilar arasindan secer.

    2^71'in otesi o kadar buyuk ki sirali taramanin anlami yok. Bunun yerine
    dev bolgeden rastgele orneklem aliyoruz - ama sadece elekten gecenleri,
    yani bicim olarak karsi ornek olma ihtimali olanlari.

    Basamak sayisi once esit olasilikla secilir, sonra o boydan rastgele bir
    sayi uretilir. Boylece "50-60 basamak" dendiginde sonuclarin tamami en
    buyuk boyda toplanmaz, her boy esit temsil edilir.
    """
    araliklar, son_basamak = aralik_hazirla(bas_basamak, son_basamak)
    if araliklar is None:
        return
    M = 1 << ELEK_K
    kalanlar = sorted(elek_kume())

    print()
    if bas_basamak == son_basamak:
        print(f"{bas_basamak} basamakli {adet:,} aday test ediliyor")
    else:
        print(f"{bas_basamak}-{son_basamak} basamak arasi {adet:,} aday "
              f"test ediliyor")
        print(f"({son_basamak - bas_basamak + 1} farkli boy, esit dagilimli)")
    if bir_sayisi:
        print(f"(hepsi son {bir_sayisi} biti 1 olan sayilar - rekortmen yapisi)")
        # Uzay kucukse rastgele secim ayni sayilari tekrar tekrar dener.
        # (10**b degerlerini yeniden hesaplamiyoruz - araliklar'da hazir;
        #  dev basamaklarda bu tekrar cok pahali olurdu.)
        M2 = 1 << bir_sayisi
        uzay = sum(max(0, (ust + 1) // M2 - (alt + M2) // M2 + 1)
                   for alt, ust in araliklar)
        if uzay and adet > uzay // 2:
            print()
            print("  ! UYARI: bu ayarda toplam aday sayisi sadece "
                  f"{uzay:,}")
            print(f"  ! {adet:,} test istedin - uzaydan buyuk. Rastgele secim")
            print("  ! ayni sayilari tekrar tekrar deneyecek (bosa calisma).")
            print(f"  ! Bunun yerine: python collatz.py sirali "
                  f"{bas_basamak} {bir_sayisi}")
            print()
    else:
        print(f"(hepsi mod 2^{ELEK_K} eleginden gecmis)")
    print("-" * 62)
    kayit_yaz("=" * 70,
              f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
              f"tarama: {bas_basamak}-{son_basamak} basamak, {adet:,} aday",
              "  'adim rekoru' = o ana kadarki en cok adim atan sayi.",
              "  Dev sayilar kisaltilir; KARSI ORNEK cikarsa tam yazilir.")

    # Kullaniciya BASTAN ne kadar surecegini soyle. Tahmin bu makinede
    # olculmus hiza gore olcekleniyor - baska bilgisayarda baska cikar.
    ort_bas = (bas_basamak + son_basamak) // 2
    tek_sure = sure_tahmini(ort_bas, bir_sayisi)
    fak, yorum, islemci = makine_bilgisi()
    print(f"Islemci    : {islemci}")
    print(f"Hiz        : {fak:.2f}x referans ({yorum})")
    print(f"Aday basina: ~{sure_yazi(tek_sure)}")
    print(f"TOPLAM     : ~{sure_yazi(tek_sure * adet)}")
    print("-" * 62)

    en_uzun = (0, 0)
    en_yuksek = (0, 0)
    t0 = time.perf_counter()
    son_rapor = t0
    # Aday basina 2 sn'den uzun suruyorsa toplu ilerleme satiri ise yaramaz
    # (ekranda dakikalarca hicbir sey gorunmez) - her adayi tek tek bildir.
    yavas = tek_sure > 2.0

    try:
        for i in range(adet):
            if yavas:
                gecen = time.perf_counter() - t0
                kalan = (tek_sure * (adet - i) if i == 0
                         else (gecen / i) * (adet - i))
                print(f"\r  aday {i+1:,}/{adet:,} calisiyor..."
                      f"  (kalan ~{sure_yazi(kalan)})          ",
                      end="", flush=True)
            n = rastgele_aday(araliklar, kalanlar, M, bir_sayisi)

            sonuc, adim, tepe, _ = dusme_testi(n)

            if sonuc != "dustu":
                print()
                print("!" * 62)
                print(f"*** KARSI ORNEK ADAYI: {sayi_ozet(n)}  ({sonuc}) ***")
                print(f"    adim={adim}")
                print(f"    TAM SAYI -> {KAYIT_DOSYASI}")
                print("!" * 62)
                kayit_yaz("", "!!! KARSI ORNEK ADAYI !!!",
                          f"durum : {sonuc}",
                          f"adim  : {adim}",
                          f"n     : {n}",
                          f"tepe  : {tepe}", "")
                return

            if adim > en_uzun[0]:
                en_uzun = (adim, n)
                kayit_yaz(f"[adim rekoru] {adim} adim | {basamak(n)} basamak"
                          f" | n = {sayi_kayit(n)}")
            if tepe > en_yuksek[0]:
                en_yuksek = (tepe, n)

            simdi = time.perf_counter()
            if not yavas and simdi - son_rapor > 0.5:
                gecen = simdi - t0
                hiz = (i + 1) / gecen
                kalan = (adet - i - 1) / hiz if hiz else 0
                print(f"\r  {i+1:>13,} / {adet:,}  |  {(i+1)/adet*100:>6.2f}%"
                      f"  |  {hiz:>9,.0f} test/sn"
                      f"  |  kalan {sure_yazi(kalan):>12}",
                      end="", flush=True)
                son_rapor = simdi
    except KeyboardInterrupt:
        print("\n  [durduruldu]")

    gecen = time.perf_counter() - t0
    print()
    print("-" * 62)
    print(f"Sure       : {sure_yazi(gecen)} ({gecen:.1f} sn)")
    if en_uzun[1]:
        print(f"En cok adim: {en_uzun[0]} adim ({basamak(en_uzun[1])} basamakli)")
        print(f"             n = {sayi_ozet(en_uzun[1])}")
        print(f"En yuksek  : {basamak(en_yuksek[0])} basamaga cikti "
              f"(baslangic {basamak(en_yuksek[1])})")
    kayit_yaz(f"[bitti] {sure_yazi(gecen)} | en cok adim: {en_uzun[0]}", "")
    print(f"Kayit      : {KAYIT_DOSYASI}")
    print("EN KUCUK KARSI ORNEK ADAYI BULUNAMADI.")
    print("(Bu mod dev bolgeden rastgele orneklem alir. Bir sayinin dusmesi")
    print(" 'en kucuk karsi ornek degil' demektir; 1'e vardigini ispatlamaz.")
    print(" Kesin sonuc icin o sayiyi mod 1'de tek tek kontrol et.)")
    print("-" * 62)


def yorunge_goster(n):
    durum, adim, tepe, yol = tam_yorunge(n, kayit_tut=True)
    print()
    print(f"{sayi_ozet(n)} yorungesi (ilk 200 adim):")
    print("  " + " -> ".join(sayi_ozet(x, esik=40) for x in yol))
    if adim >= 200:
        print(f"  ... (toplam {adim} adim)")
    print(f"\nToplam adim: {adim}   Tepe: {sayi_ozet(tepe)}")
    if durum == "dongu":
        print("*** DONGU TESPIT EDILDI ***")
    elif durum == "limit":
        print("*** ADIM LIMITI ASILDI - 1'e varmadi ***")


BANNER = """
+--------------------------------------------------------------------+
|  COLLATZ (3n+1) KARSI-ORNEK ARAYICISI                              |
+--------------------------------------------------------------------+
|  ARADIGIMIZ SEY: kendi baslangicinin altina HIC dusmeyen bir sayi.  |
|  Boyle bir sayi saninin yanlis oldugunu gosterir. 1937'den beri     |
|  bulunamadi. Bir sayinin dusmeden once attigi adim = GLIDE.         |
+--------------------------------------------------------------------+
|  1 - Tek sayi kontrol     ( 2**71+3 gibi ifade de yazabilirsin )    |
|  2 - Aralik tara          ( kucuk sayilar, sirali )                 |
|  3 - Yorunge goster       ( adim adim yol )                         |
|  4 - Rastgele tara        ( dev bolgeden toplu orneklem )           |
|  5 - Tek tek dene         ( aralik + 1 dizisini sen sec )           |
|  6 - DEV dene             ( sadece basamak sor, gerisi otomatik )   |
|  b - BILGI / ogretici     <-- ilk kez kullaniyorsan buradan basla   |
|  q - Cikis                                                         |
+--------------------------------------------------------------------+
|  BILMEN GEREKEN 3 SEY:                                             |
|   * 2^71'in ALTI zaten test edildi. Ustundeki her sey bakir -       |
|     23 basamak da 1 milyon basamak kadar denenmemis durumda.        |
|   * Elek sayilarin %98,3'unu ISPATLI olarak eliyor. Gerisi aday.    |
|   * Sondaki 1 dizisi glide'i buyutur ama arama alanini daraltir.    |
|     Karsi ornek ariyorsan 0 yaz;  glide rekoru ariyorsan acik birak.|
|                                                     ( ayrinti: b )  |
+--------------------------------------------------------------------+
"""


BILGI = {
    "1": ("PROBLEM NEDIR", """
Bir sayi al. Ciftse ikiye bol, tekse 3 ile carpip 1 ekle. Tekrarla.

   7 -> 22 -> 11 -> 34 -> 17 -> 52 -> 26 -> 13 -> 40 -> 20 -> 10 -> 5
     -> 16 -> 8 -> 4 -> 2 -> 1

Collatz sanisi der ki: HER pozitif tam sayi eninde sonunda 1'e varir.
1937'den beri kimse ispatlayamadi, kimse de aksini gosteremedi.

Sani YANLIS olsaydi, bunu gosteren sayi (karsi ornek) su iki seyden
birini yapardi:
   1) Sonsuza giderdi, hicbir zaman 1'e varmazdi
   2) Icinde 1 olmayan YENI bir donguye girerdi

Bu programin aradigi sey iste o sayi."""),

    "2": ("GLIDE - isin can damari", """
GLIDE = bir sayinin, KENDI baslangic degerinin altina inene kadar
attigi adim sayisi.

   n = 7:   7 -> 22 -> 11 -> 34 -> 17 -> 52 -> 26 -> 13 -> 40
              -> 20 -> 10 -> 5
   11. adimda 5'e indi, 5 < 7  =>  glide(7) = 11

Neden 1'e kadar gitmiyoruz? Cunku gerek yok. Sayi kendi altina
indiginde, indigi yer zaten test edilmis bir bolgedir - oradan 1'e
gidecegi bilinir. Programin hizi buradan geliyor.

VE ARADIGIMIZ SEY BUNUN DILINDE SUDUR:
   karsi ornek = glide'i HIC BITMEYEN sayi

Not: DELAY ise 1'e varana kadarki toplam adim. 27 icin
glide = 96, delay = 111.

Bilinen en buyuk glide: 1639 (19 basamakli bir sayida).
Her ek basamak icin glide ancak ~94 artiyor - dogrusal."""),

    "3": ("ELEK - ispatli eleme", """
Bir sayinin son 24 biti, sonraki ~24 adimin tamamini belirler.
Cunku tek/cift olmak son bite bakar, ikiye bolmek de bitleri kaydirir.
Bastaki milyonlarca basamagin ilk adimlarda hicbir etkisi yoktur.

Bunu kullanip 2^24 = 16.777.216 kalan sinifinin hepsini onceden
inceledik. Sonuc:

   16.490.635 sinif  ->  KESIN duser, karsi ornek olamaz  (%98,3)
      286.581 sinif  ->  hayatta kalir, aday olabilir     (%1,7)

Bu ELEME BIR ISPATTIR, tahmin degil. Sayinin son 24 biti elenen
siniflardan birindeyse, o sayi kesinlikle karsi ornek DEGILDIR -
22 basamakli da olsa, 1 milyon basamakli da olsa.

Program bu yuzden sayilarin %98,3'unu hic test etmeden atiyor."""),

    "4": ("SONDAKI 1 DIZISI - dikkat, tuzak var", """
Sayi ikilik tabanda k tane 1 ile bitiyorsa, k tur boyunca KESINTISIZ
yukselir, her turda 1,5 katina cikarak. Glide rekortmenlerinin ortak
ozelligi budur.

AMA BU BIR ISPAT DEGIL, SADECE BIR TERCIH. Ve pahaliya mal oluyor:

  Elekten gecen 286.581 mesru adayin dagilimi:
     2-4 tane 1 ile bitenler : %53,7
     20+ tane 1 ile bitenler : %0,006

  Yani karsi ornek, uzun 1 dizisiyle bitmemeye COK DAHA YATKIN -
  sirf oyle sayilar cok daha fazla oldugu icin.

  54 tane 1 zorlarsan, mesru adaylarin 3,2 x 10^-15 kadarina
  bakarsin. Ustelik 8 kat yavas calisirsin.

KURAL:
   Glide rekoru araniyorsa  -> 1 dizisi ACIK  (onerilen %65)
   Karsi ornek araniyorsa   -> 1 dizisi KAPALI (0 yaz)"""),

    "5": ("HANGI MODU NE ZAMAN", """
1  Tek sayi kontrol  - aklindaki bir sayiyi dene. 2**71+3 gibi
                       ifade de yazabilirsin.
2  Aralik tara       - kucuk sayilar icin sirali tarama.
3  Yorunge goster    - bir sayinin adim adim yolunu gor.
4  Rastgele tara     - dev bolgeden rastgele orneklem, toplu.
5  Tek tek dene      - aralik + 1 dizisini sen sec, Enter'la dene.
6  DEV dene          - sadece basamak sor, gerisi otomatik.

Komut satirindan:
   python collatz.py 27              tek sayi
   python collatz.py dev 100000      dev sayi dongusu
   python collatz.py tara 23 0       rastgele surekli tarama
   python collatz.py sirali 23 54    SIRALI - her adayi bir kez

SIRALI en degerlisi: uzayi bitirince "bu bicimde karsi ornek
YOKTUR" diyebilirsin. Rastgele tarama bunu asla veremez, ustelik
kucuk uzaylarda ayni sayilari tekrar tekrar dener."""),

    "6": ("NEREDE ARAMALI", """
Dogrulanmis sinir: 2^71 = 2.361.183.241.434.822.606.848
(David Barina, 15 Ocak 2025, Journal of Supercomputing)

Bunun ALTINDAKI her sayi tek tek test edildi. Ustundeki HICBIRI
test edilmedi. Yani:

   23 basamakli bir sayi, 10.000 basamakli bir sayi kadar bakirdir.
   "Denenmemislik" bir derece degil, acma-kapama dugmesidir.

BUYUK SAYI SECMENIN FAYDASI YOK, ZARARI VAR:
   23 basamak      -> saniyede ~150.000 test, sonuc KESIN
   10.000 basamak  -> saniyede ~5 test, sonuc BELIRSIZ

"Kesin" sunun icin: 2^71'in hemen ustunde bir sayi kendi altina
dusmuyorsa, altindaki her sey dogrulanmis oldugu icin o sayi
DOGRUDAN karsi ornektir. Buyuk sayilarda bu netlik kayboluyor."""),

    "7": ("GERCEKCI OL - bulma ihtimalin", """
Olculen: glide'i 100 artirmanin bedeli 7,5 KAT daha fazla test.

   hedef glide      gereken test         bu makinede sure
   -----------      ------------         ----------------
        1.000            178.000              saniyeler
        1.109          1.600.000              1 dakika
        1.500      4.200.000.000              2 gun
        1.639     69.500.000.000              31 gun  (dunya rekoru)
        2.000    100 trilyon                  122 yil
      SONSUZ          SONSUZ                  ASLA

Karsi ornek "cok buyuk glide" degil, "SONSUZ glide" demek.
Maliyet ustel, hedef sonsuz. Aradaki fark nicel degil.

Buna ragmen deger mi? Kararini sen ver - ama sunu bilerek ver:
her SIRALI tarama, geride kapatilmis bir bolge birakir. Bu,
"belki bulurum" ile gecen saatlerden daha fazlasidir.

Gercekten bulunabilir bir hedef istersen: ericr.nl/wondrous
sitesinde aktif bir dagitik CLASS RECORD arama projesi var
(NVidia GPU + Windows). Orada rekor kirmak mumkun."""),
}


def bilgi_goster():
    """'b' komutu: ogretici bilgi ekrani."""
    while True:
        print()
        print("+" + "-" * 60 + "+")
        print(f"|  {'BILGI / OGRETICI':<57}|")
        print("+" + "-" * 60 + "+")
        for k in sorted(BILGI):
            print(f"|  {k}  {BILGI[k][0]:<54}|")
        print(f"|  q  {'Menuye don':<54}|")
        print("+" + "-" * 60 + "+")
        try:
            s = input("Konu > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if s in ("q", "n", "", "cikis"):
            return
        if s in BILGI:
            baslik, metin = BILGI[s]
            print()
            print("=" * 62)
            print(f"  {baslik}")
            print("=" * 62)
            print(metin)
            print("=" * 62)
        else:
            print("  1-7 arasi bir konu ya da q gir.")


def bir_sayisi_sor(basamak):
    """
    Rekortmen yapisi: sayinin son N bitini 1 yapmak.

    ONEMLI: dogru N, sayinin BOYUNA baglidir - bit sayisinin ~%65'i.
    23 basamak icin ~50, 1.000.000 basamak icin ~2.159.235. Sabit bir
    sayi (eski surumde 40) buyuk sayilarda hicbir ise yaramaz: 3,3 milyon
    bitin 40'ini 1 yapmak tirmanisi neredeyse hic uzatmaz.
    """
    onerilen = optimal_bir(basamak)
    bit = int(basamak * 3.3219)
    ham = input(f"  Son kac bit 1 olsun? "
                f"(bos = onerilen {onerilen:,}, 0 = kapali) > ").strip()
    if not ham:
        return onerilen
    v = sayi_oku(ham)
    if v is None or v < 0 or v > bit:
        print(f"  0 ile {bit:,} arasinda bir sayi gir (veya bos birak).")
        return None
    return v


def main():
    print(BANNER)

    # Dev aday uret ve test et: python collatz.py dev [basamak]
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("dev", "buyuk"):
        bas = sayi_oku(sys.argv[2]) if len(sys.argv) > 2 else 1000
        if bas is None or bas < 22:
            print("Kullanim: python collatz.py dev [basamak]   (en az 22)")
            return
        tek_tek_dene(bas, bas, optimal_bir(bas))
        return

    # Sirali tarama: python collatz.py sirali [basamak] [1-sayisi]
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("sirali", "seq"):
        bas = sayi_oku(sys.argv[2]) if len(sys.argv) > 2 else 23
        bir = sayi_oku(sys.argv[3]) if len(sys.argv) > 3 else 54
        if bas is None or bir is None:
            print("Kullanim: python collatz.py sirali [basamak] [1-sayisi]")
            return
        sirali_tara(bas, bir)
        return

    # Rastgele tarama: python collatz.py tara [basamak] [1-sayisi]
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("tara", "scan"):
        bas = sayi_oku(sys.argv[2]) if len(sys.argv) > 2 else 23
        bir = sayi_oku(sys.argv[3]) if len(sys.argv) > 3 else 54
        if bas is None or bir is None:
            print("Kullanim: python collatz.py tara [basamak] [1-sayisi]")
            return
        print(f"Surekli tarama: {bas} basamak, son {bir} bit = 1")
        print("Durdurmak icin Ctrl+C\n")
        aday_tara(bas, bas, 10 ** 12, bir)
        return

    # Komut satirindan direkt sayi verilebilir: python collatz.py 27
    if len(sys.argv) > 1:
        n = sayi_oku(" ".join(sys.argv[1:]))
        if n is not None:
            tek_sayi_kontrol(n)
        return

    while True:
        try:
            secim = input("\nSecim (1-6, b=bilgi, q=cikis) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if secim in ("q", "quit", "exit", "cikis"):
            return

        if secim in ("b", "bilgi", "help", "?"):
            bilgi_goster()
            continue

        if secim == "1":
            ham = input("  Sayi > ")
            n = sayi_oku(ham)
            if n is None:
                print("  Gecersiz giris.")
            else:
                tek_sayi_kontrol(n)

        elif secim == "2":
            b = sayi_oku(input("  Baslangic > "))
            s = sayi_oku(input("  Bitis      > "))
            if b is None or s is None or s < b:
                print("  Gecersiz aralik.")
            else:
                aralik_tara(b, s)

        elif secim == "4":
            b1 = sayi_oku(input("  En az kac basamak? (min 22) > "))
            ham2 = input("  En fazla kac basamak? (bos = ayni) > ")
            b2 = b1 if not ham2.strip() else sayi_oku(ham2)
            a = sayi_oku(input("  Kac tane test edilsin? > "))
            bs = bir_sayisi_sor(b1) if b1 else None
            if b1 is None or b2 is None or a is None or a < 1 or bs is None:
                print("  Gecersiz giris.")
            else:
                aday_tara(b1, b2, a, bs)

        elif secim == "6":
            b = sayi_oku(input("  Kac basamakli? (min 22) > "))
            if b is None or b < 22:
                print("  Gecersiz giris (en az 22).")
            else:
                tek_tek_dene(b, b, optimal_bir(b))

        elif secim == "5":
            b1 = sayi_oku(input("  En az kac basamak? (min 22) > "))
            ham2 = input("  En fazla kac basamak? (bos = ayni) > ")
            b2 = b1 if not ham2.strip() else sayi_oku(ham2)
            bs = bir_sayisi_sor(b1) if b1 else None
            if b1 is None or b2 is None or bs is None:
                print("  Gecersiz giris.")
            else:
                tek_tek_dene(b1, b2, bs)

        elif secim == "3":
            n = sayi_oku(input("  Sayi > "))
            if n is None or n < 1:
                print("  Gecersiz giris.")
            else:
                yorunge_goster(n)

        else:
            # Dogrudan sayi yazildiysa onu kontrol et
            n = sayi_oku(secim)
            if n is not None:
                tek_sayi_kontrol(n)
            else:
                print("  1-6 arasi, b (bilgi) veya q gir.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C bir hata degil - kullanici durdurdu. Yigin izi basma.
        print("\n[durduruldu]")
        sys.exit(0)
