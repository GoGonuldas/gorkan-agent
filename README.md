# gorkan-agent

Sıfırdan, adım adım kendi **kod ajanını** (Claude Code'un çok küçük bir benzeri) yazmak: bir dil modeline dosya okuma,
düzenleme ve komut çalıştırma araçları verip onu bir döngüde çalıştırmak. Odak: öğrenmek — her adımda çalışan bir şey,
her adımda bir sınır ve nedeni.

Beyin: bilgisayarda ücretsiz çalışan **qwen3:8b** (Ollama). Karşılaştırma (Adım 7) Claude API yerine Mac mini'deki daha
büyük yerel modellerle yapıldı.

**Durum: Adım 0–10 tamamlandı (2026-10-15).** Ayrıntılar, ölçümler ve dersler: [PROGRESS.md](PROGRESS.md).
Plan: [PLAN.md](PLAN.md).

## Ne yapabiliyor
- Terminalde sohbet; gerektiğinde araç kullanır: `list_files`, `read_file`, `write_file`, `edit_file`, `run_command`,
  `hatirla` (proje hafızası, `AGENT.md`), `alt_gorev` (temiz bağlamlı alt ajan).
- Yazma ve komutlardan önce **onay** ister (diff gösterir); yazma sadece `sandbox/` içinde.
- Komutlar macOS **sandbox-exec** içinde çalışır: onay "evet" olsa bile `sandbox/` dışına yazamaz, ağa çıkamaz.
- Uzun konuşmayı özetler, bağlamı aşacak dosyaları vermez, düşünme takılırsa düşünmeden yeniden sorar.
- Bitirmeden önce kendini kontrol eder: cevaptaki çıktı iddiaları gerçekten bir araç sonucunda geçiyor mu, kullanıcıya
  bıraktığı bir adım var mı — varsa modele "ya yap ya çıkar" notu (en fazla iki kez).

## Ne kadar iyi (qwen3:8b, düşünme açık)
| ölçüm | sonuç |
|---|---|
| Eval (`step6_eval.py`, 14 görev ×3) | 38/42 |
| Gerçek işler (`step10_gercek.py`, 5 iş ×3) | 9/15 (Adım 10 başında 1/5) |

Bilinen sınırlar (düzenlemeyi alt göreve vermek, kodu yanlış anlama, alt görevin okumadan tahmini, ara sıra uydurma):
PROGRESS.md → "Adım 10 — Kapanış".

## Çalıştırma
```sh
python3 -m venv .venv && .venv/bin/pip install ollama
ollama pull qwen3:8b
.venv/bin/python step9_sandbox.py            # tam ajan (sohbet)
caffeinate -i .venv/bin/python step6_eval.py --ajan tam --think acik --tekrar 3   # eval (~1 saat)
caffeinate -i .venv/bin/python step10_gercek.py                                   # gerçek işler (~1 saat)
```
Sonuçlar `eval_sonuclar/` altına JSON olarak yazılır. Mac'te ölçümleri `caffeinate -i` ile çalıştır (uyku süreleri bozar, Adım 10f).

## Dosyalar
Her adım bir öncekinin üstüne kurulur (öncekini içe aktarıp genişletir).
| dosya | adım |
|---|---|
| `step0_hello.py`, `step1_chat.py` | kurulum, sohbet döngüsü |
| `step2_tools.py` | okuma araçları, tool calling |
| `step3_agent.py` | ajan döngüsü, düşünme yedeği, bitiş kancası |
| `step4_write.py` | yazma araçları + onay |
| `step5_shell.py` | komut çalıştırma + izin listesi, kanıt kontrolü |
| `step6_eval.py` | değerlendirme seti |
| `step8_memory.py`, `step8_summary.py`, `step8_subtask.py` | hafıza, özetleme, alt görevler |
| `step9_sandbox.py` | işletim sistemi sandbox'ı — **tam ajan** |
| `step10_gercek.py` | gerçek işler denemesi |

- Önceki proje: [gorkanai](https://github.com/GoGonuldas/gorkanai) (Türkçe duygu analizi, Adım 1-23, kapandı)
