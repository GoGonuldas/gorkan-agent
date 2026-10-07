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
