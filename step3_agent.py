"""Adım 3: Ajan döngüsü — model araç istemeyi bırakana kadar araç → sonuç → model.

Adım 2'de araç turu tekti; çok adımlı görevde (önce listele, sonra oku) program yarıda kalıyordu.
Şimdi döngü:
    model'i çağır
    araç istemediyse  → cevap hazır, dur
    araç istediyse    → araçları çalıştır, sonuçları ekle, başa dön
Model hep araç isteyebilir (sonsuz döngü), bu yüzden tur sınırı var.

Araçlar Adım 2'den geliyor (list_files, read_file; proje klasörü dışına çıkamaz).

Çalıştır:  .venv/bin/python step3_agent.py [--think] [--maks-tur N]
Komutlar:  /sifirla   /cikis
"""
import argparse

import ollama

from step2_tools import SYSTEM, TARIFLER, araci_calistir

MODEL = "qwen3:8b"


def ajan_turu(mesajlar, think, maks_tur, tarifler=TARIFLER, calistir=araci_calistir):
    """Bir kullanıcı isteği için döngüyü çalıştırır; son cevabı döndürür.

    tarifler/calistir: sonraki adımlar kendi araç setleriyle aynı döngüyü kullanabilsin diye parametre.
    """
    for tur in range(1, maks_tur + 1):
        cevap = ollama.chat(model=MODEL, messages=mesajlar, tools=tarifler, think=think)
        mesajlar.append(cevap.message)

        if not cevap.message.tool_calls:  # araç istemedi → iş bitti
            return cevap.message.content.strip()

        print(f"  [tur {tur}]")
        for cagri in cevap.message.tool_calls:
            sonuc = calistir(cagri)
            print(f"     → {len(sonuc)} karakter")
            mesajlar.append({"role": "tool", "content": sonuc, "tool_name": cagri.function.name})

    return f"(durduruldu: {maks_tur} tur sınırına ulaşıldı, model hâlâ araç istiyordu)"


def sohbet(system=SYSTEM, tarifler=TARIFLER, calistir=araci_calistir):
    """Terminal sohbeti: argümanları okur, kullanıcıdan istek alır, her isteği ajan_turu ile işler.

    Sonraki adımlar kendi system mesajı ve araç setiyle bunu çağırır.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--think", action="store_true", help="qwen3'ün düşünme modunu aç")
    ap.add_argument("--maks-tur", type=int, default=10, help="bir istek için en fazla araç turu")
    args = ap.parse_args()

    mesajlar = [{"role": "system", "content": system}]
    adlar = ", ".join(t["function"]["name"] for t in tarifler)
    print(f"Model: {MODEL}  araçlar: {adlar}  think={args.think}  maks-tur={args.maks_tur}")

    while True:
        try:
            soru = input("\nsen> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not soru:
            continue
        if soru == "/cikis":
            break
        if soru == "/sifirla":
            mesajlar = mesajlar[:1]
            print("(geçmiş silindi)")
            continue

        mesajlar.append({"role": "user", "content": soru})
        print(f"model> {ajan_turu(mesajlar, args.think, args.maks_tur, tarifler, calistir)}")


if __name__ == "__main__":
    sohbet()
