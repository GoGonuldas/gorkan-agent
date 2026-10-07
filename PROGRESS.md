# gorkan-agent — PROGRESS

## Adım 0 — Kurulum ve elle deneme (2026-10-07) ✅

**Yapılan**
- `.venv` (Python 3.12.14) kuruldu, `ollama` Python paketi 0.6.3 yüklendi.
- Ollama 0.24.0 sunucusu çalışıyor; modeller: `qwen3:8b`, `qwen2.5-coder:7b`, `deepseek-r1:8b`.
- `ollama run qwen3:8b --verbose` ile terminalden, `step0_hello.py` ile Python'dan tek soru soruldu.

**Sonuç** (qwen3:8b, M2 Pro 16 GB)
| Ölçüm | Değer |
|---|---|
| Modelin belleğe ilk yüklenmesi | ~3.8 sn (sonraki çağrılarda ~0) |
| Üretim hızı | ~31-33 token/sn |
| Aynı soru, düşünme açık | 4.5 sn, 134 token (487 karakter düşünme) |
| Aynı soru, düşünme kapalı (`think=False`) | 1.1 sn, 29 token |

**Dersler**
- qwen3 varsayılan olarak cevaptan önce İngilizce bir "düşünme" metni üretir; basit sorularda token'ların çoğu buna gider.
  Python'da `think=False` ile kapatılabiliyor → ~4 kat hızlı. Ajanda hangisinin daha iyi araç seçtiğini ileride ölçmek lazım.
- Hız token başına sabit (~32 token/sn); süreyi belirleyen, kaç token ürettiği.
- İlk çağrı modeli belleğe yüklediği için yavaş; ölçerken ilk çağrıyı ayrı değerlendirmek gerekir.
- Türkçe cevap akıcı ama biraz kalıp ("bilgi, destek ve çözümler sunabilirim").

**Sıradaki:** Adım 1 — sohbet döngüsü (konuşma geçmişiyle terminalde soru-cevap).

## Adım 1 — Sohbet döngüsü (2026-10-07) ✅

**Yapılan**
- `step1_chat.py`: terminalde soru-cevap. Mesajlar bir listede tutuluyor (`system` → `user` → `assistant` → …) ve
  her turda listenin tamamı modele gönderiliyor. Cevap `stream=True` ile yazıldıkça ekrana basılıyor.
- Komutlar: `/gecmis` (listeyi göster), `/sifirla` (sadece system mesajı kalır), `/cikis`. Ctrl+D / Ctrl+C ile de çıkılır.
- `think=False` (Adım 0'daki ölçüme göre sohbette 4 kat hızlı).

**Test** (girdi boruyla verildi)
| Girdi | Cevap | Bağlam |
|---|---|---|
| "Benim adım Görkan, en sevdiğim renk yeşil." | "Merhaba Görkan! Yeşil renk çok güzel bir tercih…" | 57 token |
| "Benim adım ne, en sevdiğim renk ne?" | "Adın Görkan, en sevdiğin renk yeşildir." ✅ hatırladı | 114 token |
| `/sifirla`, sonra "Benim adım ne?" | "Senin adım henüz belirlenmemiş…" ✅ unuttu | 46 token |

**Dersler**
- Modelin hafızası yok; "hatırlama" tamamen bizim gönderdiğimiz mesaj listesi. Listeyi silince model de unutuyor.
- Bağlam her turda büyüyor (57 → 114 token): tüm geçmiş her seferinde yeniden işleniyor. Uzun sohbette bu yavaşlar
  ve modelin bağlam sınırına dayanır → Adım 8'deki "uzun konuşmayı özetleme" konusunun sebebi bu.
- System mesajıyla ("Türkçe, kısa ve net") cevaplar kısa geldi (18-35 token); system mesajı olmadan karşılaştırmadım,
  etkisini ayrıca ölçmek gerekir.
- 8B model Türkçede ara sıra hata yapıyor ("Senin adım" yerine "Senin adın").

**Sıradaki:** Adım 2 — ilk araçlar (`list_files`, `read_file`), tool calling.

## Adım 2 — İlk araçlar: list_files, read_file (2026-10-07) ✅

**Önce (Adım 1'de yapılması gerekirken atlanmıştı):** hangi model araç kullanabiliyor? `ollama show` ile bakıldı:
`qwen3:8b` ✅ tools + thinking, `qwen2.5-coder:7b` ✅ tools, `deepseek-r1:8b` ❌ (sadece thinking) → ajan için kullanılamaz.

**Yapılan**
- `step2_tools.py`: Adım 1'in sohbetine iki araç eklendi. Modele araçların JSON şeması (ad, açıklama, parametreler)
  veriliyor; model `tool_calls` döndürürse aracı program çalıştırıyor, sonucu `{"role": "tool"}` olarak ekleyip
  modeli bir kez daha çağırıyor. Araç turu bilerek tek (çok adımlı döngü Adım 3).
- Güvenlik: `guvenli_yol()` her yolu proje klasörüne göre çözüyor, dışarı çıkanı reddediyor. Dosya 10.000 karakterde
  kesiliyor. Araç hatası (olmayan dosya vb.) programı çökertmiyor, "HATA: …" metni olarak modele geri gidiyor.

**Test**
| Girdi | Ne oldu |
|---|---|
| "2 artı 2 kaç?" | Araç çağırmadı, "4." ✅ gereksiz araç yok |
| "Bu klasörde hangi dosyalar var?" | `list_files(".")` → doğru liste ✅ |
| "README.md'yi oku, 2 cümleyle özetle" | `read_file("README.md")` → doğru özet ✅ |
| "/etc/passwd dosyasını oku." | ❌ **Araç çağırmadı**, "sadece root okuyabilir" diye uydurdu (yanlış: macOS'ta herkes okuyabilir). Kilit hiç devreye girmedi. |
| "yok.txt'de ne yazıyor?" | `read_file` → HATA metni → "dosya bulunamadı" dedi ✅ hatayı doğru aktardı |
| "Python dosyalarından en küçük numaralının ne yaptığını söyle. Önce listele, sonra oku." | `list_files` çağırdı, sonra yine araç istedi → tek tur sınırına takıldı, **boş cevap** ⚠️ (beklenen; Adım 3'ün sebebi) |
| Kilit doğrudan test: `/etc/passwd`, `../README.md`, `sandbox/../../x` | Üçü de engellendi ✅, `PLAN.md` serbest ✅ |

**Dersler**
- Aracı model değil program çalıştırıyor; model sadece "şunu çağır" diyor. Bu yüzden güvenlik kontrolü programda olmalı,
  modelin iyi niyetine bırakılmamalı.
- Model aracı çağırmak yerine **uydurabiliyor** (/etc/passwd). System mesajında "tahmin etme" demek yetmedi. Bu sefer
  araç çağrılmadığı için kilit hiç sınanmadı (ayrıca doğrudan test edildi); cevap ise yanlıştı → doğruluğu ölçmek için
  Adım 6'daki test seti gerekli.
- Hata mesajını modele geri vermek işe yarıyor: model hatayı kullanıcıya anlaşılır biçimde anlattı.
- Çok adımlı görevde tek tur yetmiyor: model listeyi gördü, okumak için ikinci araç istedi, program durdu → kullanıcı
  boş cevap gördü.

**Sıradaki:** Adım 3 — ajan döngüsü (model araç istemeyi bırakana kadar araç → sonuç → model, tur sınırıyla).

## Adım 3 — Ajan döngüsü (2026-10-07) ✅

**Yapılan**
- `step3_agent.py`: model araç istemeyi bırakana kadar `model → araç → sonuç → model` döngüsü. Araçlar Adım 2'den
  import ediliyor. Tur sınırı (`--maks-tur`, varsayılan 10) aşılırsa döngü durup bunu açıkça söylüyor.
  `--think` ile qwen3'ün düşünme modu açılabiliyor.
- `step2_tools.py`'de klasör kilidinin hata mesajı değişti: eskisi sadece "izin yok: … proje klasörünün dışında" diyordu,
  yenisi yolun nasıl yazılacağını söylüyor ("başında '/' olmadan, ör. 'README.md'"). Kilidin kendisi aynı.

**Test**
| Görev | Ne oldu |
|---|---|
| "En küçük numaralı adımın dosyası ne yapıyor? Önce listele, sonra oku." (Adım 2'de takılmıştı) | 2 tur: `list_files` → `read_file("step0_hello.py")` → doğru açıklama ✅ |
| Aynı görev, `--maks-tur 1` | 1 turdan sonra "(durduruldu: 1 tur sınırına ulaşıldı…)" ✅ |
| "Her stepN dosyasında MODEL değişkeni hangi modele ayarlı?" — **eski** hata mesajıyla | ❌ `/PROGRESS.md`, `/README.md`, `/PLAN.md` denedi, hepsi reddedildi; step dosyalarını hiç okumadı; "dosya izinleri kontrol edilmeli" dedi |
| Aynı görev, yeni hata mesajı, think kapalı, deneme 1 | Yanlış yolu düzeltti ama step dosyalarını okumadı (PROGRESS, PLAN, README okudu); ❌ **soruyu cevaplamak yerine sahte bir "Adım 3 ✅" PROGRESS bölümü uydurdu** |
| deneme 2 | `/home/runner/work/...` diye yol uydurdu, düzeltti, 4 dosyayı da okudu → ✅ "qwen3:8b" |
| deneme 3 | Yine uydurma yol, düzeltti; `step0_hello.py`'yi **okumadan** "her dosyada qwen3:8b" dedi → cevap doğru ama kanıtsız ⚠️ |
| Aynı görev, `--think` | Hiç hatalı yol yok, 4 dosyayı sırayla okudu → ✅ doğru ve eksiksiz (57 sn) |

Özet (az örnek!): think kapalı 3 denemenin 1'i tamamen doğru, 1'i doğru ama eksik okumayla, 1'i yanlış; think açık 1/1.

**Dersler**
- Döngü, Adım 2'deki "boş cevap" sorununu çözdü; tur sınırı da beklendiği gibi çalışıyor.
- **Hata mesajları modelin talimatıdır.** "izin yok" deyince model sorunu "dosya izni" sandı; nasıl düzelteceğini
  söyleyen mesajdan sonra 3 denemenin 3'ünde yanlış yolu bir sonraki turda düzeltti.
- Model eğitim verisinden ezberlediği yolları uyduruyor (`/home/runner/work/...`); program bunları kilitle yakalıyor.
- Döngü olunca yeni bir hata türü çıktı: **görevden sapma**. Deneme 1'de model, okuduğu PROGRESS.md'nin biçimini taklit
  edip olmayan bir bölüm uydurdu. Ayrıca "her dosyada" deyip bir dosyayı okumadan atladı.
- Düşünme açıkken bu görevde daha düzenli çalıştı ama 1 deneme kanıt değil, yavaşlık da maliyet. Adım 6'daki test
  setinde think açık/kapalı karşılaştırılmalı.
- Model her çalıştırmada farklı davranıyor; tek bir denemeye bakıp "çalışıyor" demek yanıltıcı.

**Sıradaki:** Adım 4 — yazma araçları + onay (`write_file`, `edit_file`, diff göster, onay al).
