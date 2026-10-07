# gorkan-agent — PLAN (2026-10-07; ilk adım onay bekliyor)

> **Yeni oturum için:** bu dosyayı oku, sonra 0. ve 1. adımla başla. Görkan Python/ML'e yeni başladı (gorkanai projesinde
> 23 adım yaptı); Türkçe konuşulur, her adımda küçük ve çalışan bir şey, dürüst başarısızlıklar ders olarak kaydedilir.
> Her adımın sonunda `PROGRESS.md`'ye sonuç + ders yazılır (gorkanai'deki gibi).

## Hedef
Terminalde çalışan, şunları yapabilen küçük bir ajan:
1. Kullanıcıyla sohbet eder.
2. Gerektiğinde **araç** kullanır: dosyaları listeler/okur, dosya yazar/düzenler, komut çalıştırır.
3. Tehlikeli işlerden (dosya yazma, komut) önce **onay** ister.
4. İş bitene kadar "model → araç → sonuç → model" döngüsünü sürdürür.

## Ortam (laptop, 2026-10-07'de kontrol edildi)
- Apple M2 Pro, **16 GB RAM** → 7-8 milyar parametrelik modeller rahat; 14B sınırda; 30B+ sığmaz.
- Python 3.12 (Homebrew), **Ollama 0.24.0 kurulu**, inmiş modeller: `qwen2.5-coder:7b`, `qwen3:8b`, `deepseek-r1:8b`.
- Ajanın araç kullanabilmesi için modelin **tool calling** desteklemesi gerekir — 1. adımda hangi modelin desteklediği
  denenerek bulunur (ilk aday: `qwen3:8b`).
- Claude API (sonraki adımlar, isteğe bağlı): API anahtarı gerekir, kullandıkça ücretli. Model kimliğini ve fiyatı
  o adımda güncel dokümandan kontrol et, ezberden yazma.

## Yol haritası (her adım ~1 oturum)
| # | Adım | Ne öğrenilir |
|---|---|---|
| 0 | Kurulum: venv, `ollama` paketi, `ollama run qwen3:8b` ile elle deneme | Yerel model nasıl çalışır, ne kadar hızlı |
| 1 | **Sohbet döngüsü**: terminalde soru-cevap, konuşma geçmişi | Mesaj listesi, roller (system/user/assistant), bağlam |
| 2 | **İlk araçlar**: `list_files`, `read_file` (sadece okuma) | Tool calling: model "aracı çağır" der, program çalıştırır, sonucu geri verir |
| 3 | **Ajan döngüsü**: model "bitti" diyene kadar araç → sonuç → model | Çok adımlı görevler, sonsuz döngüye karşı sınır |
| 4 | **Yazma araçları + onay**: `write_file`, `edit_file` (diff göster, onay al) | Güvenlik, kullanıcı kontrolü |
| 5 | **Komut çalıştırma** + izin listesi (ör. `ls`, `python` serbest; `rm` hep sorulur) | Sandbox fikri, izin sistemi |
| 6 | **Değerlendirme**: 10 küçük görevlik bir test seti, başarı oranı | Ajanı ölçmek (gorkanai'deki dürüst ölçüm alışkanlığı) |
| 7 | **Claude API ile aynı ajan**: arka ucu değiştirilebilir yap, iki modeli aynı test setinde karşılaştır | Model kalitesinin ajana etkisi |
| 8+ | İsteğe bağlı: proje hafızası (AGENT.md), uzun konuşmayı özetleme, alt görevler | Bağlam yönetimi |

## İlkeler
- Her adımda **çalışan** bir şey; önce en basit hali, sonra iyileştirme.
- Ajan kendi klasörü dışında yazamaz (3-5. adımlarda kural olarak konur); denemeler `sandbox/` klasöründe.
- Başarısız denemeler silinmez, `PROGRESS.md`'ye ders olarak yazılır.
- Gizli bilgi (API anahtarı) koda/commit'e girmez: `.env` + `.gitignore`.
