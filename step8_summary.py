"""Adım 8b: Uzun konuşmayı özetleme.

Bağlam penceresi sınırlı (step3_agent.NUM_CTX). Ollama aşılınca hata vermiyor, en eski mesajları sessizce atıyor:
kullanıcının ilk söyledikleri gider. Burada kesmeyi Ollama'ya bırakmıyoruz:
  - Her model çağrısından önce konuşmanın kaç token tutacağı tahmin edilir: son çağrının gerçek sayısı
    (Ollama'nın döndürdüğü) + o çağrıdan sonra eklenen mesajlar için karakter/3.
  - Tahmin ESIK'i aşarsa, son kullanıcı isteğinden önceki her şey (system hariç) modele özetletilir ve
    tek bir özet mesajıyla değiştirilir. Son istek ve onun araç çağrıları/sonuçları olduğu gibi kalır.
Bilinen sınır: tek bir istek (ör. çok büyük dosyalar okuyan uzun bir araç zinciri) tek başına pencereyi
doldurursa özetlenecek eski mesaj yoktur; o zaman sadece uyarı verilir.

Araçlar ve hafıza Adım 8a'dan (step8_memory) geliyor.

Çalıştır:  .venv/bin/python step8_summary.py [--no-think] [--dusunme-siniri SN] [--num-ctx N] [--maks-tur N] [--model AD] [--host URL]
Komutlar:  /sifirla   /cikis
"""
import json

import step3_agent as ajan
import step8_memory as hafiza

ESIK = 0.6  # pencerenin bu oranı dolunca özetle; kalan yer yeni araç sonuçları ve cevap için
KARAKTER_TOKEN = 3  # kaba tahmin; ölçülen: Türkçe metin ~2.5, kod/JSON ~3.4 karakter/token
MAKS_DOKUM = 1_500  # özet isteğinde her mesajdan en fazla bu kadar karakter (özet isteği de pencereye sığmalı)

OZET_SYSTEM = "Sen bir özetleyicisin. Sana verilen konuşma dökümünü özetlersin; dökümdeki sorulara cevap vermezsin."
# Talimat dökümden SONRA da tekrarlanıyor: ilk denemede model dökümü sürdürüp son soruyu cevapladı (Adım 8b).
OZET_ISTEGI = '''Aşağıda bir kod asistanı ile kullanıcı arasındaki konuşmanın eski kısmı var (<dokum> içinde).

<dokum>
{dokum}
</dokum>

Bu dökümün TAMAMINI özetle (sadece sonunu değil); dökümdeki isteklere cevap verme. Özet, konuşmayı hiç görmemiş
biri işe devam edebilsin diye yazılır. Tam olarak şu üç başlığı kullan, Türkçe ve kısa:

Kullanıcının verdiği bilgiler ve tercihler: (isimler, kelimeler, sayılar BİREBİR; dökümde önceki bir özet varsa
oradakileri de taşı)
Yapılanlar: (okunan/değiştirilen dosyalar ve ne öğrenildiği, birer cümle; dosya içeriğini kopyalama)
Yarım kalan işler: (yoksa "yok")'''


def karakter(m):
    """Bir mesajın token tahmini için karakter sayısı (araç çağrıları dahil)."""
    if isinstance(m, dict):
        return len(m.get("content") or "")
    return len(m.content or "") + len(json.dumps([c.function.model_dump() for c in m.tool_calls or []]))


def token_tahmini(mesajlar, tarifler):
    s = ajan.SAYAC
    if 0 < s["mesaj"] <= len(mesajlar):  # son gerçek sayım + sonradan eklenenler
        return s["token"] + sum(karakter(m) for m in mesajlar[s["mesaj"] + 1:]) // KARAKTER_TOKEN
    toplam = sum(karakter(m) for m in mesajlar) + len(json.dumps(tarifler, ensure_ascii=False))
    return toplam // KARAKTER_TOKEN


def dokum(mesajlar):
    """Mesajları özetleyicinin okuyacağı düz metne çevirir; uzun içerikler kısaltılır."""
    satirlar = []
    for m in mesajlar:
        rol = m["role"] if isinstance(m, dict) else m.role
        icerik = (m.get("content") if isinstance(m, dict) else m.content) or ""
        if not isinstance(m, dict) and m.tool_calls:
            icerik += " [araç çağırdı: " + ", ".join(
                f"{c.function.name}({json.dumps(c.function.arguments, ensure_ascii=False)[:200]})" for c in m.tool_calls
            ) + "]"
        if rol == "tool":
            rol = f"araç sonucu ({m.get('tool_name', '?')})"
        if len(icerik) > MAKS_DOKUM:
            icerik = icerik[:MAKS_DOKUM] + f" …(kısaltıldı, {len(icerik)} karakter)"
        satirlar.append(f"### {rol}\n{icerik.strip()}")
    return "\n\n".join(satirlar)


OZET_BASI = "[Bağlam dolduğu için önceki konuşma silindi; özeti aşağıda. Buna cevap verme.]"


def ozetle_gerekirse(mesajlar, tarifler):
    """Gerekirse mesajlar listesini YERİNDE kısaltır (sohbet aynı listeyi kullanmaya devam ediyor)."""
    tahmin = token_tahmini(mesajlar, tarifler)
    if tahmin < ESIK * ajan.NUM_CTX:
        return
    # son kullanıcı isteği ve sonrası kalır: araç çağrısı ile sonucu birbirinden ayrılmasın
    son_istek = max(i for i, m in enumerate(mesajlar) if isinstance(m, dict) and m.get("role") == "user")
    eski = mesajlar[1:son_istek]
    if not eski or (len(eski) == 1 and isinstance(eski[0], dict) and eski[0]["content"].startswith(OZET_BASI)):
        # tek başına önceki özeti yeniden özetlemek bağlamı küçültmez, sadece bir model çağrısı harcar
        print(f"  (uyarı: bağlam ~{tahmin}/{ajan.NUM_CTX} token ama özetlenecek eski mesaj yok)")
        return
    print(f"  (bağlam ~{tahmin}/{ajan.NUM_CTX} token → {len(eski)} eski mesaj özetleniyor)")
    r = ajan.ISTEMCI.chat(
        model=ajan.MODEL, think=False, options={"num_ctx": ajan.NUM_CTX},
        messages=[{"role": "system", "content": OZET_SYSTEM},
                  {"role": "user", "content": OZET_ISTEGI.format(dokum=dokum(eski))}],
    )
    ozet = r.message.content.strip()
    mesajlar[1:son_istek] = [{
        "role": "user",
        "content": f"{OZET_BASI}\n{ozet}",
    }]
    ajan.SAYAC["mesaj"] = 0  # eski sayım artık bu listeye ait değil; bir sonraki tahmin karakterden
    print(f"  (özet: {len(ozet)} karakter; yeni tahmin ~{token_tahmini(mesajlar, tarifler)} token)")


if __name__ == "__main__":
    ajan.sohbet(hafiza.system_mesaji(), hafiza.TARIFLER, hafiza.araci_calistir,
                hazirla=lambda m: ozetle_gerekirse(m, hafiza.TARIFLER))
