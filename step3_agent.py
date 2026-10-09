"""Adım 3: Ajan döngüsü — model araç istemeyi bırakana kadar araç → sonuç → model.

Adım 2'de araç turu tekti; çok adımlı görevde (önce listele, sonra oku) program yarıda kalıyordu.
Şimdi döngü:
    model'i çağır
    araç istemediyse  → cevap hazır, dur
    araç istediyse    → araçları çalıştır, sonuçları ekle, başa dön
Model hep araç isteyebilir (sonsuz döngü), bu yüzden tur sınırı var.

Araçlar Adım 2'den geliyor (list_files, read_file; proje klasörü dışına çıkamaz).

Düşünme takılırsa (DUSUNME_SINIRI saniyeyi aşar ya da boş sonuç verirse) aynı istek düşünmeden yeniden sorulur.

Çalıştır:  .venv/bin/python step3_agent.py [--no-think] [--dusunme-siniri SN] [--num-ctx N] [--maks-tur N] [--model AD] [--host URL]
           ör. --model qwen3:14b --host http://gorkans-mac-mini.local:11434  (model başka makinede çalışır,
           araçlar yine bu bilgisayarda)
Komutlar:  /sifirla   /cikis
"""
import argparse
import json
import time

import httpx
import ollama

from step2_tools import SYSTEM, TARIFLER, araci_calistir

MODEL = "qwen3:8b"
# ollama.Client'ın varsayılan zaman aşımı yok: Adım 7c'de sunucu sessiz kaldı, çağrı 70 dk bekleyip
# "Connection reset" ile düştü. Okuma sınırı = sunucudan hiç veri gelmeden geçebilecek en uzun süre
# (akışta iki parça arası; akışsız çağrıda tüm cevap + gerekirse model yükleme).
ZAMAN_ASIMI = httpx.Timeout(180, connect=10)
ISTEMCI = ollama.Client(timeout=ZAMAN_ASIMI)  # host verilmezse OLLAMA_HOST ya da localhost:11434
# Adım 7b'de 8b bir istekte 24 dk düşünüp boş cevap verdi. Normal düşünme çağrı başına genelde 10-30 sn.
DUSUNME_SINIRI = 60
# Ollama'nın varsayılanı 4096 token. Aşılınca hata vermiyor: en eski mesajları sessizce atıyor, tek mesaj sığmazsa
# onun başını kesiyor (Adım 8b). Büyüdükçe bellek de artar (qwen3:8b'de 8192 ≈ +0.7 GB).
NUM_CTX = 8192
# son çağrının gerçek token sayısı (prompt + cevap) ve o çağrıda kaç mesaj vardı; bağlam takibi için
SAYAC = {"mesaj": 0, "token": 0}
# Aynı araç + aynı argüman + aynı sonuç tekrar gelirse sonuca uyarı eklenir. Denemede 8b aynı başarısız edit_file'ı
# 8 kez gönderip tur sınırına takıldı (Adım 10).
TEKRAR_UYARISI = True
TEKRAR_NOTU = (
    "\n\nNOT: Bu aracı aynı argümanlarla daha önce çağırdın ve sonuç aynıydı. Aynısını tekrar deneme: farklı bir yol "
    "dene (ör. dosyayı read_file ile okuyup write_file ile baştan yaz) ya da yapamadığını kullanıcıya söyle."
)
# Adım 10j: modelin düşünmesi assistant mesajında kalırsa Ollama onu sonraki her çağrıda geri gönderiyor (2100
# karakter → +784 prompt token); bir isteğin bütün turlarının düşünmesi birikiyordu. False: konuşmaya düşünmesiz eklenir.
DUSUNCE_SAKLA = False
THINK = True  # sohbet() komut satırından ayarlar; alt görevler (Adım 8c) aynı ayarla çalışsın diye burada


def ayarla(model=None, host=None, think=True):
    """Hangi modelin, hangi makinede çalışacağını seçer. Kullanılacak think değerini döndürür:
    modelin düşünme desteği yoksa (ör. qwen3-coder) think=True hata verirdi, kapatır."""
    global MODEL, ISTEMCI
    if host:
        ISTEMCI = ollama.Client(host=host, timeout=ZAMAN_ASIMI)
    if model:
        MODEL = model
    if think and "thinking" not in (ISTEMCI.show(MODEL).capabilities or []):
        print(f"(not: {MODEL} düşünme modunu desteklemiyor, think kapatıldı)")
        return False
    return think


def modeli_cagir(mesajlar, tarifler, think):
    """Modeli bir kez çağırır, assistant mesajını döndürür.

    think=True ise cevap parça parça (stream) alınır. Düşünme DUSUNME_SINIRI saniyeyi geçer ve hâlâ ne metin ne
    araç çağrısı gelmemişse bağlantı kesilir (Ollama üretimi durdurur) ve aynı istek düşünmeden yeniden sorulur.
    Düşünme bitip sonuç boş çıkarsa ya da sunucu ZAMAN_ASIMI boyunca hiç veri göndermezse de aynısı yapılır.
    Düşünmeden çağrıda zaman aşımı olursa hata yukarı çıkar (sonsuza kadar beklemek yerine).
    """
    secenek = {"num_ctx": NUM_CTX}
    if not think:
        r = ISTEMCI.chat(model=MODEL, messages=mesajlar, tools=tarifler, think=False, options=secenek)
        kaydet(mesajlar, r)
        return r.message

    # monotonic: macOS'ta uykuda ilerlemiyor. time.time() ile Mac düşünme sırasında uyuyunca uyanışta süre aşılmış
    # sayılıyor, yedek boşuna tetikleniyordu (Adım 10f: 10 yedeğin hepsi uykudan).
    t0 = time.monotonic()
    icerik, dusunce, araclar = "", "", []
    akis = ISTEMCI.chat(model=MODEL, messages=mesajlar, tools=tarifler, think=True, stream=True, options=secenek)
    try:
        for parca in akis:
            m = parca.message
            dusunce += m.thinking or ""
            icerik += m.content or ""
            araclar += m.tool_calls or []
            if parca.done:
                kaydet(mesajlar, parca)
            if not icerik and not araclar and time.monotonic() - t0 > DUSUNME_SINIRI:
                akis.close()
                print(f"  (düşünme {DUSUNME_SINIRI} sn'yi aştı → düşünmeden yeniden soruluyor)")
                return modeli_cagir(mesajlar, tarifler, think=False)
    except httpx.TimeoutException:
        # süre kontrolü sadece parça gelince çalışır; sunucu hiç parça göndermezse onu burası yakalar
        print(f"  (sunucu {ZAMAN_ASIMI.read:.0f} sn hiç veri göndermedi → düşünmeden yeniden soruluyor)")
        return modeli_cagir(mesajlar, tarifler, think=False)

    if not icerik.strip() and not araclar:
        print("  (düşünme boş sonuç verdi → düşünmeden yeniden soruluyor)")
        return modeli_cagir(mesajlar, tarifler, think=False)
    return ollama.Message(role="assistant", content=icerik, thinking=dusunce or None, tool_calls=araclar or None)


def kaydet(mesajlar, cevap):
    SAYAC["mesaj"] = len(mesajlar)
    SAYAC["token"] = (cevap.prompt_eval_count or 0) + (cevap.eval_count or 0)


def ajan_turu(mesajlar, think, maks_tur, tarifler=TARIFLER, calistir=araci_calistir, hazirla=None):
    """Bir kullanıcı isteği için döngüyü çalıştırır; son cevabı döndürür.

    tarifler/calistir: sonraki adımlar kendi araç setleriyle aynı döngüyü kullanabilsin diye parametre.
    hazirla(mesajlar): her model çağrısından önce çalışır, listeyi yerinde değiştirebilir (Adım 8b: özetleme).
    """
    onceki = {}  # (araç adı, argümanlar) → son sonuç; bu istek boyunca
    for tur in range(1, maks_tur + 1):
        if hazirla:
            hazirla(mesajlar)
        mesaj = modeli_cagir(mesajlar, tarifler, think)
        if not DUSUNCE_SAKLA and mesaj.thinking:
            mesaj = ollama.Message(role=mesaj.role, content=mesaj.content, tool_calls=mesaj.tool_calls)
        mesajlar.append(mesaj)

        if not mesaj.tool_calls:  # araç istemedi → iş bitti
            return mesaj.content.strip()

        print(f"  [tur {tur}]")
        for cagri in mesaj.tool_calls:
            sonuc = calistir(cagri)
            anahtar = (cagri.function.name, json.dumps(cagri.function.arguments, sort_keys=True, ensure_ascii=False))
            tekrar = TEKRAR_UYARISI and onceki.get(anahtar) == sonuc
            onceki[anahtar] = sonuc
            if tekrar:
                sonuc += TEKRAR_NOTU
                print("     (tekrar: aynı çağrı, aynı sonuç → uyarı eklendi)")
            print(f"     → {len(sonuc)} karakter")
            mesajlar.append({"role": "tool", "content": sonuc, "tool_name": cagri.function.name})

    return f"(durduruldu: {maks_tur} tur sınırına ulaşıldı, model hâlâ araç istiyordu)"


def sohbet(system=SYSTEM, tarifler=TARIFLER, calistir=araci_calistir, hazirla=None):
    """Terminal sohbeti: argümanları okur, kullanıcıdan istek alır, her isteği ajan_turu ile işler.

    Sonraki adımlar kendi system mesajı ve araç setiyle bunu çağırır.
    """
    global DUSUNME_SINIRI, NUM_CTX, THINK
    ap = argparse.ArgumentParser()
    # varsayılan açık: Adım 6'da think açık %97, kapalı %63 (ama ~6.5 kat yavaş). Kapatmak için --no-think
    ap.add_argument("--think", action=argparse.BooleanOptionalAction, default=True, help="qwen3'ün düşünme modu")
    ap.add_argument("--maks-tur", type=int, default=10, help="bir istek için en fazla araç turu")
    ap.add_argument("--dusunme-siniri", type=float, default=DUSUNME_SINIRI,
                    help="düşünme bu kadar saniyeyi aşarsa düşünmeden yeniden sor")
    ap.add_argument("--num-ctx", type=int, default=NUM_CTX, help="bağlam penceresi (token)")
    ap.add_argument("--model", help=f"Ollama model adı (varsayılan {MODEL})")
    ap.add_argument("--host", help="Ollama sunucusu, ör. http://gorkans-mac-mini.local:11434")
    args = ap.parse_args()
    args.think = ayarla(args.model, args.host, args.think)
    DUSUNME_SINIRI = args.dusunme_siniri
    NUM_CTX = args.num_ctx
    THINK = args.think

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
        try:
            print(f"model> {ajan_turu(mesajlar, args.think, args.maks_tur, tarifler, calistir, hazirla)}")
            print(f"  (bağlam: {SAYAC['token']}/{NUM_CTX} token)")
        except httpx.TimeoutException:
            print(f"(hata: sunucu {ZAMAN_ASIMI.read:.0f} sn cevap vermedi; tekrar dene ya da /sifirla)")


if __name__ == "__main__":
    sohbet()
