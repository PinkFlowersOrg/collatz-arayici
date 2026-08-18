# Collatz (3n+1) Karşı-Örnek Arayıcısı

> ### Bu araç tamamen Claude (Anthropic) ile yazıldı
>
> Kod, testler ve bu dokümantasyon dahil her şey. Bunu baştan söylüyorum çünkü
> aklına gelen ilk soru muhtemelen *"yapay zekâ yazmış, bir yerinde sessizce
> yanlıştır"* olacak — ve bu haklı bir şüphe. Cevabı şu:
>
> **README'deki hiçbir rakam uydurulmadı.** Bütün ölçümler (hız tabloları, glide
> oranları, elek dağılımı) gerçek çalıştırmalarla elde edildi. Doğruluk da senin
> sözüme güvenmene bırakılmadı:
>
> ```bash
> python test_collatz.py     # 74 kontrol, ~4 saniye
> ```
>
> Testler hızlı kodu, kısayolsuz bir "altın standart" uygulamayla ve
> [literatürdeki yayınlanmış değerlerle](https://www.ericr.nl/wondrous/)
> karşılaştırıyor. Kendin çalıştır, gör.
>
> ### Lisans: MIT
>
> İstediğin gibi kullan, değiştir, dağıt, sat. Tek şart: kopyalarda telif ve
> lisans bildirimini koru. Geliştirmeler, hata bildirimleri, PR'lar açığa açık —
> [@pinkflowersorg](https://github.com/pinkflowersorg)

Collatz sanısına uymayan bir sayı arayan, tek dosyalık bir Python aracı.
Bağımlılığı yok, Python 3.8+ ile çalışır.

```bash
python collatz.py
```

## Önce dürüst olalım

**Bu araç büyük ihtimalle karşı örnek bulmayacak.** Sanı 1937'den beri açık ve
2^71'e kadar (2.361.183.241.434.822.606.848) her sayı süperbilgisayarlarla test
edildi. Ev bilgisayarıyla o sınırın ötesinde rastgele arama yapmanın başarı
ihtimali sıfıra çok yakındır.

Bu araç şunlar için iyi:

- Problemi **anlamak** — elek nasıl kurulur, glide nedir, neden zor
- **Tamamlanmış** taramalar yapmak (`sirali` modu) — "bu bölgede karşı örnek
  yoktur" diyebileceğin kesin sonuçlar
- Dev sayılarla hızlı deney yapmak (1 milyon basamak ~4 dakika)

Karşı örnek bulmak için değil, **doğru düzgün aramak** için yazıldı.

## Temel kavramlar

**Glide** — Bir sayının, kendi başlangıç değerinin altına inene kadar attığı
adım sayısı.

```
7 → 22 → 11 → 34 → 17 → 52 → 26 → 13 → 40 → 20 → 10 → 5
                                                       ↑
                                          11. adımda 5 < 7  ⇒  glide(7) = 11
```

Karşı örnek = **glide'ı hiç bitmeyen** sayı. Bir sayı kendi altına indiği an
elenir, çünkü indiği yer zaten doğrulanmış bölgedir. Yörüngeyi 1'e kadar
sürmeye gerek yok — hız buradan geliyor.

**Elek** — Bir sayının son 24 biti, sonraki ~24 adımın tamamını belirler.
2^24 = 16.777.216 kalan sınıfının hepsi önceden incelendi:

| | Sınıf | Oran |
|---|---|---|
| Kesin düşer, aday olamaz | 16.490.635 | %98,3 |
| Hayatta kalır, aday olabilir | 286.581 | %1,7 |

Bu **ispatlı** bir elemedir. Sayının son 24 biti elenen sınıflardan birindeyse
o sayı kesinlikle karşı örnek değildir — 22 basamaklı da olsa, 1 milyon
basamaklı da olsa.

## Modlar

```
1  Tek sayı kontrol     2**71+3 gibi ifade de kabul eder
2  Aralık tara          küçük sayılar için sıralı tarama
3  Yörünge göster       adım adım yol
4  Rastgele tara        dev bölgeden toplu örneklem
5  Tek tek dene         aralık + 1 dizisini sen seç
6  DEV dene             sadece basamak sor, gerisi otomatik
b  Bilgi / öğretici     7 konuluk açıklama
```

Komut satırından:

```bash
python collatz.py 27                # tek sayı
python collatz.py "2**71+3"         # ifade
python collatz.py dev 100000        # 100.000 basamaklı sayı döngüsü
python collatz.py tara 23 0         # rastgele sürekli tarama
python collatz.py sirali 23 54      # SIRALI — her adayı tam bir kez
```

`sirali` en değerlisi: uzayı bitirdiğinde *"bu biçimde karşı örnek yoktur"*
diyebilirsin. Ctrl+C ile durur, aynı komutla kaldığı yerden devam eder.

## Sondaki 1 dizisi — dikkat

Sayı ikilik tabanda `k` tane 1 ile bitiyorsa `k` tur boyunca kesintisiz
yükselir (her turda 1,5 katına). Glide rekortmenlerinin ortak özelliği budur.

**Ama bu bir ispat değil, sadece bir tercih — ve pahalı.** Elekten geçen meşru
adayların %53,7'si 4 veya daha az 1 ile bitiyor; 20+ ile bitenler %0,006.
54 tane 1 zorlarsan meşru adayların 3,2×10⁻¹⁵ kadarına bakarsın ve 8 kat yavaş
çalışırsın.

| Amaç | Ayar |
|---|---|
| Glide rekoru aramak | 1 dizisi **açık** (önerilen %65) |
| Karşı örnek aramak | 1 dizisi **kapalı** (`0` yaz) |

## Ne kadar sürer

Program açılışta kendi makinesini ölçüp tahminleri ona göre ölçekler — başka
bilgisayarda başka değer çıkar, elle ayar gerekmez.

Referans makinede (Intel Core Ultra, tek çekirdek) düşme testi:

| Basamak | Süre |
|---|---|
| 23 | ~7 μs |
| 10.000 | 0,02 sn |
| 100.000 | ~2 sn |
| 1.000.000 | ~4 dk |

Ölçülen model: `glide ≈ 6,25 × (1 dizisi)`, `süre ≈ adım_maliyeti × glide`.

## Hız

Dev sayılar için **blok hızlandırma** var: sayının son 16 biti sonraki 16 adımı
belirlediğinden, bu önceden tabloya alınıp 16 adım tek çarpmayla atılıyor.
Milyon basamaklı sayıya 16 kez değil bir kez dokunuluyor.

| Basamak | Blok öncesi | Blok ile | Kazanç |
|---|---|---|---|
| 20.000 | 0,61 sn | 0,05 sn | 11x |
| 50.000 | 6,59 sn | 0,55 sn | 12x |
| 100.000 | 20,6 sn | 2,07 sn | 10x |

Blok yöntemi sayı başlangıcına yaklaşınca otomatik olarak tek-tek adıma geçer,
böylece blok içinde olup biten hiçbir şey kaçmaz.

## Test

```bash
python test_collatz.py
```

74 test, ~5 saniye. Hızlı kodun sonucu her seferinde **altın standartla**
karşılaştırılır: kısayolsuz, bloksuz, her adımda kontrol eden en yavaş sürüm.

- 1..50.000 arası **tüm** sayılarda glide/sonuç/tepe birebir aynı
- 500 rastgele dev sayıda (4100–8000 bit) sonuç ve glide birebir aynı
- Literatürdeki bilinen değerler: glide(703)=132, glide(270271)=267,
  delay(27)=111, tepe(27)=9232 vb.
- Elek dizisi (1, 1, 2, 3, 4, 8, 13, 19, 38, 64, …) bilinen diziyle aynı
- Girdi güvenliği: `9**9**9` gibi ifadeler donmadan reddediliyor

Tepe değeri dev sayılarda blok yöntemi yüzünden ±1 basamak şaşabilir; çıktıda
`~` ile işaretlidir. Sonuç ve glide her zaman kesindir.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `collatz.py` | Programın tamamı |
| `test_collatz.py` | Test paketi |
| `collatz_kayit.txt` | Bulunan rekorlar ve karşı örnek adayları (otomatik) |
| `collatz_durum.txt` | Sıralı taramanın kaldığı yer (otomatik) |

## Gerçekçi beklenti

Ölçülen: glide'ı 100 artırmanın bedeli **7,5 kat** daha fazla test.

| Hedef glide | Gereken test | Referans makinede |
|---|---|---|
| 1.109 | 1,6 milyon | 1 dakika |
| 1.639 | 69,5 milyar | 31 gün *(dünya rekoru)* |
| 2.000 | 100 trilyon | 122 yıl |
| **∞** *(karşı örnek)* | **∞** | **asla** |

Maliyet üstel, hedef sonsuz. Gerçekten bulunabilir bir hedef arıyorsan
[ericr.nl/wondrous](https://www.ericr.nl/wondrous/) sitesindeki dağıtık
**class record** arama projesine katılabilirsin (NVidia GPU + Windows).

## Kaynaklar

- [Eric Roosendaal — On the 3x+1 problem](https://www.ericr.nl/wondrous/) —
  glide/delay/class rekor tabloları
- [David Bařina — Convergence verification](https://pcbarina.fit.vutbr.cz/) —
  2^71 doğrulama sınırı (Journal of Supercomputing, 2025)
- [Terence Tao — Almost all orbits of the Collatz map attain almost bounded
  values](https://arxiv.org/abs/1909.03562) (2019)

## Lisans

**MIT** — Copyright (c) 2026 [@pinkflowersorg](https://github.com/pinkflowersorg)

Kullan, değiştir, dağıt, ticari işlerde kullan; izin sorman gerekmez. Tek
koşul: kopyalarda ve türev çalışmalarda telif bildirimi ile lisans metnini
koru. Ayrıntı için [LICENSE](LICENSE).
