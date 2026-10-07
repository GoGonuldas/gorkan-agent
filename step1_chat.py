"""Adım 1: Terminalde konuşma geçmişini hatırlayan sohbet.

Model hiçbir şeyi kendisi hatırlamaz: her turda konuşmanın TAMAMINI (mesaj listesi) yeniden gönderiyoruz.
Roller: system (kurallar), user (sen), assistant (model).

Çalıştır:  .venv/bin/python step1_chat.py
Komutlar:  /sifirla (geçmişi sil)   /gecmis (listeyi göster)   /cikis
"""
import ollama

MODEL = "qwen3:8b"
SYSTEM = "Sen yardımsever bir asistansın. Türkçe, kısa ve net cevap ver."


def yeni_gecmis():
    return [{"role": "system", "content": SYSTEM}]


def main():
    mesajlar = yeni_gecmis()
    print(f"Model: {MODEL}  (komutlar: /sifirla, /gecmis, /cikis)")

    while True:
        try:
            soru = input("\nsen> ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D / Ctrl+C
            print()
            break

        if not soru:
            continue
        if soru == "/cikis":
            break
        if soru == "/sifirla":
            mesajlar = yeni_gecmis()
            print("(geçmiş silindi)")
            continue
        if soru == "/gecmis":
            for m in mesajlar:
                print(f"  [{m['role']}] {m['content'][:80]}")
            continue

        mesajlar.append({"role": "user", "content": soru})

        # stream=True: cevap parça parça gelir, yazıldıkça ekrana basarız
        print("model> ", end="", flush=True)
        cevap = ""
        for parca in ollama.chat(model=MODEL, messages=mesajlar, think=False, stream=True):
            print(parca.message.content, end="", flush=True)
            cevap += parca.message.content
            if parca.done:
                print(f"\n  ({parca.eval_count} token, bağlam: {parca.prompt_eval_count} token)")

        mesajlar.append({"role": "assistant", "content": cevap})


if __name__ == "__main__":
    main()
