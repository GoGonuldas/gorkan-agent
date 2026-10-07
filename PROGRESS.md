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
