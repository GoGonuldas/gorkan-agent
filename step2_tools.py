"""Adım 2: İlk araçlar — list_files, read_file (sadece okuma).

Tool calling nasıl işler:
  1. Modele araçların tarifini (ad, açıklama, parametreler) veririz.
  2. Model gerekirse metin yerine "şu aracı şu argümanla çağır" der (message.tool_calls).
  3. Aracı BİZ çalıştırırız, sonucu {"role": "tool"} mesajı olarak listeye ekleriz.
  4. Modeli tekrar çağırırız; sonucu görüp cevabını yazar.
Bu adımda araç turu tek: model sonuçtan sonra yine araç isterse işlemiyoruz (o iş Adım 3'ün döngüsü).

Çalıştır:  .venv/bin/python step2_tools.py
Komutlar:  /sifirla   /cikis
"""
import json
from pathlib import Path

import ollama

MODEL = "qwen3:8b"
KOK = Path(__file__).resolve().parent  # araçlar bu klasörün dışına çıkamaz
MAKS_KARAKTER = 10_000  # çok büyük dosya bağlamı doldurmasın

SYSTEM = (
    "Sen yardımsever bir asistansın. Türkçe, kısa ve net cevap ver. "
    "Dosyalar hakkındaki sorular için araçları kullan; dosya içeriğini tahmin etme. "
    "Dosya ve klasör adlarını aynen yaz, Türkçeye çevirme (ör. 'step2_tools.py', 'adım2_araçlar.py' değil)."
)


# --- Araçların kendisi (sıradan Python fonksiyonları) ---

def guvenli_yol(path):
    """Yolu proje klasörüne göre çözer; dışarı çıkıyorsa hata verir."""
    yol = (KOK / path).resolve()
    if not yol.is_relative_to(KOK):
        # mesaj modele gider: sadece "yasak" demek yetmez, nasıl düzelteceğini de söyle
        raise ValueError(
            f"'{path}' proje klasörünün dışında. Yollar proje köküne göre ve başında '/' olmadan "
            "yazılmalı, ör. 'README.md' veya 'sandbox/x.txt'."
        )
    return yol


def list_files(path="."):
    yol = guvenli_yol(path)
    ogeler = sorted(yol.iterdir())
    satirlar = [p.name + ("/" if p.is_dir() else "") for p in ogeler if not p.name.startswith(".")]
    return "\n".join(satirlar) or "(boş klasör)"


def read_file(path):
    metin = guvenli_yol(path).read_text(encoding="utf-8")
    if len(metin) > MAKS_KARAKTER:
        metin = metin[:MAKS_KARAKTER] + f"\n…(kısaltıldı, toplam {len(metin)} karakter)"
    return metin


ARACLAR = {"list_files": list_files, "read_file": read_file}

# --- Araçların modele verilen tarifi (JSON şeması) ---

TARIFLER = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Bir klasördeki dosya ve alt klasörleri listeler (alt klasörler '/' ile biter).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Proje köküne göre klasör yolu. Kök için '.'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Bir metin dosyasının içeriğini döndürür.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Proje köküne göre dosya yolu, ör. 'README.md'"},
                },
                "required": ["path"],
            },
        },
    },
]


def araci_calistir(cagri):
    ad, argumanlar = cagri.function.name, cagri.function.arguments or {}
    print(f"  🔧 {ad}({json.dumps(argumanlar, ensure_ascii=False)})")
    if ad not in ARACLAR:
        return f"HATA: '{ad}' diye bir araç yok"
    try:
        return ARACLAR[ad](**argumanlar)
    except Exception as e:  # hatayı modele geri ver, program çökmesin
        return f"HATA: {e}"


def main():
    mesajlar = [{"role": "system", "content": SYSTEM}]
    print(f"Model: {MODEL}  araçlar: {', '.join(ARACLAR)}  (komutlar: /sifirla, /cikis)")

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
        cevap = ollama.chat(model=MODEL, messages=mesajlar, tools=TARIFLER, think=False)
        mesajlar.append(cevap.message)

        if cevap.message.tool_calls:
            for cagri in cevap.message.tool_calls:
                sonuc = araci_calistir(cagri)
                print(f"     → {len(sonuc)} karakter")
                mesajlar.append({"role": "tool", "content": sonuc, "tool_name": cagri.function.name})
            # sonuçlarla modeli bir kez daha çağır
            cevap = ollama.chat(model=MODEL, messages=mesajlar, tools=TARIFLER, think=False)
            mesajlar.append(cevap.message)
            if cevap.message.tool_calls:
                print("  (model yine araç istedi; çok adımlı döngü Adım 3'te)")

        print(f"model> {cevap.message.content.strip()}")


if __name__ == "__main__":
    main()
