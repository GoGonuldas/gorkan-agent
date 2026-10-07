"""Adım 4: Yazma araçları + onay — write_file, edit_file.

Okuma araçları (list_files, read_file) Adım 2'den, döngü Adım 3'ten geliyor. Yeni olanlar:
  - write_file(path, content)          : dosya oluştur / üzerine yaz
  - edit_file(path, old_text, new_text): dosyadaki bir parçayı değiştir (old_text tam olarak 1 kez geçmeli)
Güvenlik:
  - Yazma SADECE sandbox/ içinde (okuma tüm projede serbest). Ajan kendi kodunu bozamaz.
  - Diske yazmadan önce program farkı (diff) gösterir ve onay ister. Onayı model değil program sorar,
    model bu adımı atlayamaz. Reddedilirse model bunu (ve varsa nedenini) araç sonucu olarak görür.

Çalıştır:  .venv/bin/python step4_write.py [--no-think] [--maks-tur N] [--model AD] [--host URL]
Komutlar:  /sifirla   /cikis
"""
import difflib
import json

import step2_tools as okuma
from step3_agent import sohbet

KUM = okuma.KOK / "sandbox"

SYSTEM = (
    "Sen yardımsever bir kod asistanısın. Türkçe, kısa ve net cevap ver. "
    "Dosyalar hakkındaki sorular için araçları kullan; dosya içeriğini tahmin etme. "
    "Dosya yazma ve düzenleme sadece 'sandbox/' klasöründe yapılabilir, yollar 'sandbox/x.txt' gibi yazılır. "
    "sandbox/ dışındaki bir dosyanın değiştirilmesi istenirse yapma, başka bir dosyaya da yazma; "
    "kullanıcıya bunun yapılamayacağını söyle. "
    "Var olan bir dosyada küçük değişiklik için edit_file kullan; önce read_file ile dosyayı oku."
)


# --- Yazma araçları ---

def yazilabilir_yol(path):
    """Okuma kilidinden geçen yolun ayrıca sandbox/ içinde olmasını şart koşar."""
    yol = okuma.guvenli_yol(path)
    if not yol.is_relative_to(KUM):
        # "sandbox/<ad> dene" diye önermiyoruz: model isteği sessizce başka dosyaya yönlendirmesin
        raise ValueError(
            f"'{path}' sandbox/ dışında ve değiştirilemez. Başka dosyaya yazma; kullanıcıya bunun yapılamadığını söyle."
        )
    return yol


def onay_al(path, eski, yeni):
    """Farkı göster, kullanıcıya sor. Onay → None, red → modele gidecek açıklama."""
    # lineterm="" + "\n".join: dosya satır sonuyla bitmese de -/+ satırları birbirine yapışmaz
    fark = difflib.unified_diff(
        eski.splitlines(), yeni.splitlines(),
        fromfile=f"{path} (önce)", tofile=f"{path} (sonra)", lineterm="",
    )
    print("\n".join(fark) or "  (fark yok)")
    return sor(f"{path} değişsin mi?")


def sor(soru):
    """Kullanıcıya evet/hayır sorar. Onay → None, red → modele gidecek açıklama."""
    try:
        cevap = input(f"  ✋ {soru} [e/h] ").strip().lower()
        if cevap == "e":
            return None
        neden = input("  neden? (boş geçebilirsin) ").strip()
    except (EOFError, KeyboardInterrupt):  # cevap alınamazsa güvenli taraf: reddet
        print()
        neden = ""
    return "REDDEDİLDİ: kullanıcı onaylamadı, hiçbir şey yapılmadı." + (f" Neden: {neden}" if neden else "")


def write_file(path, content):
    yol = yazilabilir_yol(path)
    eski = yol.read_text(encoding="utf-8") if yol.exists() else ""
    red = onay_al(path, eski, content)
    if red:
        return red
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(content, encoding="utf-8")
    return f"yazıldı: {path} ({len(content)} karakter)"


def edit_file(path, old_text, new_text):
    yol = yazilabilir_yol(path)
    if not old_text:
        raise ValueError("old_text boş olamaz. Dosyanın tamamını değiştirmek için write_file kullan.")
    if old_text == new_text:
        # yoksa "fark yok" onaylanır ve model hiçbir şey değişmediği halde "düzenlendi" der
        raise ValueError("old_text ile new_text aynı; bu düzenleme hiçbir şeyi değiştirmez.")
    eski = yol.read_text(encoding="utf-8")
    adet = eski.count(old_text)
    if adet == 0:
        raise ValueError("old_text dosyada bulunamadı. Önce read_file ile oku, metni boşluklarıyla birebir kopyala.")
    if adet > 1:
        raise ValueError(f"old_text dosyada {adet} kez geçiyor; tek yeri seçecek kadar çevresiyle birlikte ver.")
    yeni = eski.replace(old_text, new_text)
    red = onay_al(path, eski, yeni)
    if red:
        return red
    yol.write_text(yeni, encoding="utf-8")
    return f"düzenlendi: {path}"


ARACLAR = {**okuma.ARACLAR, "write_file": write_file, "edit_file": edit_file}

TARIFLER = okuma.TARIFLER + [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "sandbox/ içinde bir dosya oluşturur veya tamamen üzerine yazar. Kullanıcı onayı gerekir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu, ör. 'sandbox/not.txt'"},
                    "content": {"type": "string", "description": "Dosyanın yeni içeriğinin tamamı"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "sandbox/ içindeki bir dosyada old_text'i new_text ile değiştirir. old_text dosyada birebir ve "
                "tam olarak bir kez geçmeli. Kullanıcı onayı gerekir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu, ör. 'sandbox/not.txt'"},
                    "old_text": {"type": "string", "description": "Değiştirilecek mevcut metin (birebir)"},
                    "new_text": {"type": "string", "description": "Yerine gelecek metin"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
]


def araci_calistir(cagri, araclar=ARACLAR):
    ad, argumanlar = cagri.function.name, cagri.function.arguments or {}
    goster = {k: (v[:60] + "…" if isinstance(v, str) and len(v) > 60 else v) for k, v in argumanlar.items()}
    print(f"  🔧 {ad}({json.dumps(goster, ensure_ascii=False)})")
    if ad not in araclar:
        return f"HATA: '{ad}' diye bir araç yok"
    try:
        return araclar[ad](**argumanlar)
    except Exception as e:
        return f"HATA: {e}"


if __name__ == "__main__":
    sohbet(SYSTEM, TARIFLER, araci_calistir)
