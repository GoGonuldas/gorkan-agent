"""Adım 8c: Alt görevler — işi temiz bağlamlı bir alt ajana ver, sadece kısa sonucu geri al.

Adım 8b'nin sınırı: tek bir istek (ör. 5 büyük dosyayı okumak) pencereyi tek başına doldurursa özetlenecek eski
mesaj yoktur. Çözüm: alt_gorev(gorev) aracı. Ana ajan bir parçayı alt ajana verir; alt ajan BOŞ bir konuşmayla
(kendi system mesajı + görev) başlar, araçlarını kullanır, kısa bir cevap döndürür. Ana konuşmaya dosya içerikleri
değil sadece bu cevap girer.
  - Alt ajan sadece okuyabilir (list_files, read_file): yazma/komut onayları ana ajanda kalsın, alt ajan da kendi
    alt görevini açamasın (sonsuz iç içe geçme olmasın).
  - Alt ajan da aynı step3_agent döngüsünü kullanıyor; o döngünün token sayacı (SAYAC) ana konuşmaya ait, bu yüzden
    alt görev bitince geri yükleniyor (yoksa 8b'nin özetleme tahmini alt ajanın sayısıyla bozulur).

Araçlar, hafıza ve özetleme Adım 8a/8b'den geliyor.

Çalıştır:  .venv/bin/python step8_subtask.py [--no-think] [--dusunme-siniri SN] [--num-ctx N] [--maks-tur N] [--model AD] [--host URL]
Komutlar:  /sifirla   /cikis
"""
import step2_tools as okuma
import step3_agent as ajan
import step4_write as yazma
import step8_memory as hafiza
import step8_summary as ozet

ALT_MAKS_TUR = 8
MAKS_SONUC = 2_000

ALT_SYSTEM = (
    "Sen bir alt ajansın. Ana ajanın sana verdiği tek görevi araçlarla yap. Türkçe cevap ver. "
    "Yollar proje köküne göre, başında '/' olmadan yazılır, ör. 'README.md' veya 'sandbox/x.txt'. "
    "Cevabını sadece ana ajan görecek ve o dosyaları görmeyecek: istenen bilgiyi kısa ve kendi başına anlaşılır yaz, "
    "dosya içeriğini kopyalama. Bulamadığın bir şeyi uydurma, bulamadığını söyle."
)

SYSTEM = hafiza.system_mesaji() + (
    " Birden çok dosyayı okumayı ya da çok uzun çıktıları gerektiren işleri alt_gorev ile parçala: her dosya ya da "
    "parça için ayrı bir alt görev ver (bir çağrıda birden çok alt görev verebilirsin). Alt ajan bu konuşmayı "
    "görmez; görevi kendi başına anlaşılır yaz. Sonuçları birleştirip kullanıcıya sen cevap ver."
)


def alt_gorev(gorev):
    yedek = dict(ajan.SAYAC)
    mesajlar = [{"role": "system", "content": ALT_SYSTEM}, {"role": "user", "content": gorev}]
    print(f"  ┌─ alt görev: {gorev[:80]}")
    try:
        sonuc = ajan.ajan_turu(mesajlar, ajan.THINK, ALT_MAKS_TUR, okuma.TARIFLER, alt_araci_calistir)
    finally:
        ajan.SAYAC.update(yedek)
    print(f"  └─ alt görev bitti ({len(sonuc)} karakter)")
    if not sonuc:
        return "Alt ajan boş cevap döndü."
    if len(sonuc) > MAKS_SONUC:
        sonuc = sonuc[:MAKS_SONUC] + f"\n…(kısaltıldı, toplam {len(sonuc)} karakter)"
    return sonuc


def alt_araci_calistir(cagri):
    return yazma.araci_calistir(cagri, okuma.ARACLAR)


# Adım 10h: bağlam koruması. 10g'de tarif yönlendirmesi #12'de ilk turda 0/3 tuttu; model 3 dosyayı kendisi okuyup
# pencereyi aşıyordu (özetleme yardım edemez: hepsi son isteğe ait). Okunan dosya, konuşmanın tahmini + dosyanın
# tahmini KORUMA_ESIK'i geçecekse içerik yerine not döner. Kalan pay düşünme ve cevap için (düşünme 1000–2000 token).
KORUMA_ESIK = 0.75
KONUSMA = {"mesajlar": None}  # ana konuşmanın listesi; hazirla() her model çağrısından önce bağlar


def hazirla(mesajlar):
    KONUSMA["mesajlar"] = mesajlar
    ozet.ozetle_gerekirse(mesajlar, TARIFLER)


def korumali_read_file(path):
    metin = okuma.read_file(path)
    if KONUSMA["mesajlar"] is None:
        return metin
    simdi = ozet.token_tahmini(KONUSMA["mesajlar"], TARIFLER)
    dosya = len(metin) // ozet.KARAKTER_TOKEN
    if simdi + dosya <= KORUMA_ESIK * ajan.NUM_CTX:
        return metin
    print(f"     (koruma: {path} ~{dosya} token, bağlam ~{simdi}/{ajan.NUM_CTX} → içerik verilmedi)")
    return (
        f"OKUNMADI: {path} yaklaşık {dosya} token; bağlam şu an ~{simdi}/{ajan.NUM_CTX} token. Okursan bağlam dolar ve "
        "konuşmanın başı kaybolur. Bu dosyadan bilgi çıkarmak için alt_gorev kullan: dosyanın tam adını ve ne "
        "istediğini yaz. Dosyayı değiştirmen gerekiyorsa kullanıcıya bağlamın yetmediğini söyle."
    )


ARACLAR = {**hafiza.ARACLAR, "read_file": korumali_read_file, "alt_gorev": alt_gorev}

# Ana ajanın read_file tarifine yönlendirme notu. qwen3:8b system mesajındaki "alt_gorev ile parçala" kuralını
# tartmıyor, araç tariflerine bakıyor (Adım 10g: #12'nin ilk turunda alt_gorev system'de 0/5, tarifte 2–3/5).
# Kopya: aynı sözlük alt ajanın (okuma.TARIFLER) read_file'ı, o değişmemeli.
READ_NOTU = (
    " Birden çok dosyayı sadece okuyup bilgi çıkaracaksan read_file kullanma; her dosya için ayrı bir alt_gorev çağır "
    "(hepsi aynı turda verilebilir), böylece bağlam dolmaz. Dosyayı değiştireceksen read_file ile kendin oku: "
    "edit_file için tam metni görmen gerekir."
)


def _read_notlu(t):
    if t["function"]["name"] != "read_file":
        return t
    return {**t, "function": {**t["function"], "description": t["function"]["description"] + READ_NOTU}}


TARIFLER = [_read_notlu(t) for t in hafiza.TARIFLER] + [
    {
        "type": "function",
        "function": {
            "name": "alt_gorev",
            "description": (
                "Bir işi temiz bağlamla başlayan bir alt ajana verir ve onun kısa cevabını döndürür. Alt ajan "
                "dosyaları listeleyip okuyabilir ama yazamaz, komut çalıştıramaz ve bu konuşmayı görmez. Büyük "
                "dosyaları okuyup özetlemek ya da birçok dosyayı tek tek incelemek için kullan: bu konuşmanın "
                "bağlamı dosya içerikleriyle dolmaz."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "gorev": {
                        "type": "string",
                        "description": (
                            # 10b'deki '<dosya> dosyasını oku; …' kalıbı birebir kopyalandı (Adım 10g: 5 denemenin
                            # 2'sinde '<dosya>' kaldı, birinde dosya adı hiç yoktu); düz tarifle 2/2 doğru.
                            "Kendi başına anlaşılır görev. Okunacak dosyanın tam adını ve kullanıcının o dosya "
                            "hakkında tam olarak ne istediğini yaz; alt ajan başka hiçbir şey bilmiyor."
                        ),
                    },
                },
                "required": ["gorev"],
            },
        },
    },
]


def araci_calistir(cagri):
    return yazma.araci_calistir(cagri, ARACLAR)


if __name__ == "__main__":
    ajan.sohbet(SYSTEM, TARIFLER, araci_calistir, hazirla=hazirla)
