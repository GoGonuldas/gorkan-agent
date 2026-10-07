"""Adım 0: Python'dan yerel modele tek bir soru sor, süreyi ve hızı ölç.

Çalıştır:  .venv/bin/python step0_hello.py
"""
import time

import ollama

MODEL = "qwen3:8b"
SORU = "Merhaba! Kendini tek cümleyle tanıt."

for think in (True, False):
    t0 = time.time()
    cevap = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": SORU}],
        think=think,  # qwen3 cevaptan önce "düşünebilir"; kapatınca daha hızlı
    )
    sure = time.time() - t0

    token = cevap.eval_count
    hiz = token / (cevap.eval_duration / 1e9)  # eval_duration nanosaniye cinsinden
    print(f"--- think={think} | {sure:.1f} sn | {token} token | {hiz:.1f} token/sn")
    if cevap.message.thinking:
        print(f"[düşünme: {len(cevap.message.thinking)} karakter]")
    print(cevap.message.content.strip())
    print()
