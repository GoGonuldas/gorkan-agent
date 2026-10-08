"""Adım 8a: Proje hafızası — AGENT.md.

Her oturum boş başlıyor: önceki oturumda öğrenilen ("bu projede şöyle yapılır") bir sonrakinde yok.
Çözüm: proje kökündeki AGENT.md her başlangıçta okunup system mesajına eklenir.
  - Kullanıcı AGENT.md'yi elle yazabilir (proje kuralları, alışkanlıklar).
  - Ajan hatirla(not) aracıyla dosyanın sonuna tek satır ekleyebilir; kullanıcı onayı gerekir.
    Bu, "sadece sandbox/'a yaz" kuralının tek istisnası: yol modelden alınmaz, hep AGENT.md'dir,
    ve sadece ekleme yapılır (var olan satırlar silinemez/değişemez).
Hafıza her istekte bağlamda yer kaplar, bu yüzden boyut sınırı var.

Çalıştır:  .venv/bin/python step8_memory.py [--no-think] [--dusunme-siniri SN] [--maks-tur N] [--model AD] [--host URL]
Komutlar:  /sifirla   /cikis
"""
import step2_tools as okuma
import step4_write as yazma
import step5_shell as kabuk
from step3_agent import sohbet

HAFIZA = okuma.KOK / "AGENT.md"
MAKS_HAFIZA = 4_000  # karakter; aşarsa baştan kesilir ve uyarı eklenir
MAKS_NOT = 300


def hafizayi_oku():
    """AGENT.md'yi system mesajına eklenecek metin olarak döndürür (yoksa boş)."""
    if not HAFIZA.exists():
        return ""
    metin = HAFIZA.read_text(encoding="utf-8").strip()
    if len(metin) > MAKS_HAFIZA:
        metin = metin[:MAKS_HAFIZA] + f"\n…(AGENT.md kısaltıldı, toplam {len(metin)} karakter)"
    return f"\n\nProje hafızası (AGENT.md; önceki oturumlardan notlar, bunlara uy):\n{metin}"


def system_mesaji():
    return kabuk.SYSTEM + (
        " Kullanıcı bir şeyi hatırlamanı isterse ya da projede sonraki oturumlarda da geçerli olacak bir kural "
        "öğrenirsen hatirla aracını kullan; geçici şeyleri hatırlama."
    ) + hafizayi_oku()


def hatirla(note):
    note = " ".join(note.split())  # tek satır: not dosyanın yapısını bozamasın
    if not note:
        raise ValueError("not boş olamaz")
    if len(note) > MAKS_NOT:
        raise ValueError(f"not çok uzun ({len(note)} karakter, en fazla {MAKS_NOT}); kısalt.")
    red = yazma.sor(f"AGENT.md'ye eklensin mi: '- {note}'")
    if red:
        return red
    eski = HAFIZA.read_text(encoding="utf-8") if HAFIZA.exists() else "# AGENT.md — proje hafızası\n"
    if not eski.endswith("\n"):
        eski += "\n"
    HAFIZA.write_text(eski + f"- {note}\n", encoding="utf-8")
    return "AGENT.md'ye eklendi (sonraki oturumlarda da görülecek)"


ARACLAR = {**kabuk.ARACLAR, "hatirla": hatirla}

TARIFLER = kabuk.TARIFLER + [
    {
        "type": "function",
        "function": {
            "name": "hatirla",
            "description": (
                "Proje hafızasına (AGENT.md) tek satırlık bir not ekler; not sonraki oturumlarda da system "
                "mesajında görünür. Kalıcı kurallar ve tercihler için kullan. Not, bu konuşmayı hiç görmemiş biri "
                "okuduğunda da anlaşılır olmalı: sadece değeri değil kuralın tamamını yaz (ne, ne zaman, nasıl). "
                "Kullanıcı onayı gerekir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": (
                            "Tek satırlık, kendi başına anlaşılır not. İyi: 'Kullanıcı her cevabın sonunda tek "
                            "cümlelik özet istiyor.' Kötü: 'tek cümle özet'"
                        ),
                    },
                },
                "required": ["note"],
            },
        },
    },
]


def araci_calistir(cagri):
    return yazma.araci_calistir(cagri, ARACLAR)


if __name__ == "__main__":
    sohbet(system_mesaji(), TARIFLER, araci_calistir)
