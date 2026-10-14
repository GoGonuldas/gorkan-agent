"""Adım 5: Komut çalıştırma + izin listesi — run_command.

Okuma/yazma araçları Adım 2 ve 4'ten, döngü Adım 3'ten geliyor. Yeni olan run_command(command).
Güvenlik:
  - Kabuk YOK: komut parçalanıp doğrudan çalıştırılır. ; && || | > < gibi işleçler reddedilir. Kabuk olsaydı
    "ls; rm -rf ~" izin listesinden "ls" diye geçerdi.
  - Üç seviye:
      SERBEST : onaysız çalışır (ls, cat, python, …) — ama argüman proje dışını gösteriyorsa (/…, ~…, ..) onay ister
      YASAK   : hiç çalışmaz (sudo, dd, …)
      diğerleri (rm dahil): her seferinde kullanıcı onayı
  - Proje kökünde çalışır (dosya araçlarıyla aynı yollar: 'sandbox/x.py'), 30 sn zaman aşımı, çıktı kısaltılır.
Bilinen açık: python serbest, yani `python -c "import os; os.remove(...)"` hiçbir kontrole takılmaz.
Komut adına bakan bir izin listesi, programın İÇİNDE ne yaptığını bilemez; gerçek sandbox işletim sistemi
seviyesinde (konteyner, ayrı kullanıcı) olur. → Adım 9 (step9_sandbox.py) bunu sandbox-exec ile kapatıyor.

Çalıştır:  .venv/bin/python step5_shell.py [--no-think] [--dusunme-siniri SN] [--num-ctx N] [--maks-tur N] [--model AD] [--host URL]
Komutlar:  /sifirla   /cikis
"""
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import step2_tools as okuma
import step4_write as yazma
import step3_agent as ajan
from step3_agent import sohbet

SERBEST = {"ls", "cat", "head", "tail", "wc", "grep", "pwd", "echo", "python", "python3"}
PYTHONLAR = {"python", "python3"}
YASAK = {"sudo", "su", "dd", "mkfs", "shutdown", "reboot"}
ISLECLER = {";", "&", "&&", "|", "||", ">", ">>", "<", "(", ")"}
ZAMAN_ASIMI = 30
MAKS_CIKTI = 5_000

SYSTEM = yazma.SYSTEM + (
    " Komut çalıştırmak için run_command kullan. Komutlar proje kökünde çalışır; yollar dosya araçlarındaki gibi "
    "yazılır: proje kökündeki dosya 'README.md', sandbox'taki dosya 'sandbox/selam.py'. "
    "Kabuk yok: ; && | > kullanma, her çağrıda tek komut çalıştır. "
    # Adım 10p: 10l-b'nin "testleri kendin çalıştır, çalıştırmadığının sonucunu yazma" kuralı kaldırıldı — modeli işi
    # kullanıcıya bırakmaya itiyordu (#11–14 kurallı 6/12, kuralsız 11/12). Testlerin çalıştırılmasını bitiş kancası denetliyor.
    "Onay gerektiren işlerde kullanıcıdan sohbette izin isteme: aracı doğrudan çağır, onayı program sorar."
)


def parcala(command):
    """Komutu kabuk gibi parçalar ama çalıştırmaz; işleçleri ayrı parça olarak yakalar (tırnak içindekiler hariç)."""
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def izin_seviyesi(argv):
    """('serbest' | 'yasak' | 'onay', neden) döndürür."""
    ad = Path(argv[0]).name  # /bin/rm → rm
    if ad in YASAK:
        return "yasak", f"'{ad}' bu ajanda hiç çalıştırılamaz"
    if ad not in SERBEST:
        return "onay", f"'{ad}' izin listesinde değil"
    for arg in argv[1:]:
        if arg == "/" and ad in PYTHONLAR:  # betiğe verilen bölme işareti (hesap.py 10 2 /), yol değil
            continue
        if arg.startswith(("/", "~")) or ".." in Path(arg).parts:
            return "onay", f"'{arg}' proje klasörünün dışını gösteriyor olabilir"
    return "serbest", ""


def sarmala(argv):
    """Çalıştırmadan hemen önce komutu sarmalar. Burada olduğu gibi döner; Adım 9 bunu sandbox-exec ile değiştirir."""
    return argv


def run_command(command):
    try:
        argv = parcala(command)
    except ValueError as e:  # ör. kapanmamış tırnak
        raise ValueError(f"komut ayrıştırılamadı ({e}); tırnakları kontrol et.")
    if not argv:
        raise ValueError("boş komut")
    islecler = [p for p in argv if p in ISLECLER]
    if islecler:
        raise ValueError(
            f"kabuk işleci kullanılamaz: {' '.join(islecler)}. Her run_command çağrısında tek komut çalıştır; "
            "çıktıyı dosyaya yazmak için write_file kullan."
        )

    seviye, neden = izin_seviyesi(argv)
    print(f"  ⚙️  {seviye}" + (f" ({neden})" if neden else ""))
    if seviye == "yasak":
        return f"YASAK: {neden}. Bunu deneme, kullanıcıya söyle."
    if seviye == "onay":
        red = yazma.sor(f"komut çalışsın mı: {command}")
        if red:
            return red

    if argv[0] in ("python", "python3"):
        argv[0] = sys.executable  # projenin venv'indeki python
    try:
        sonuc = subprocess.run(sarmala(argv), cwd=okuma.KOK, capture_output=True, text=True, timeout=ZAMAN_ASIMI)
    except FileNotFoundError:
        return f"HATA: '{argv[0]}' diye bir komut bulunamadı"
    except subprocess.TimeoutExpired:
        return f"HATA: komut {ZAMAN_ASIMI} saniyede bitmedi, durduruldu"

    cikti = f"çıkış kodu: {sonuc.returncode}\n--- stdout ---\n{sonuc.stdout}\n--- stderr ---\n{sonuc.stderr}"
    if len(cikti) > MAKS_CIKTI:
        cikti = cikti[:MAKS_CIKTI] + f"\n…(kısaltıldı, toplam {len(cikti)} karakter)"
    return cikti


def kanitsiz_iddialar(cevap, kanit):
    """Cevaptaki çıktı iddialarından hiçbir kanıtta geçmeyenler.

    İddia: kod bloklarının satırları (python blokları hariç) ve satır içi `…` kodlar — 10k-b ölçümünde modeller
    çıktıları hep satır içi yazdı (`1 2 4` → `2.33`). Çalıştırılmamış bir `python …` komutu tek başına öneridir
    (testi kullanıcıya bırakmak, ayrı sorun); ama aynı satırda bir sonuç gösteriliyorsa (→, "çıktı") çalıştırılmış
    gibi sunulmuştur, iddia sayılır (10l: "`python sandbox/hesap.py 2 3 *` → 6.0", hiç çalıştırılmamıştı).
    10q: aynısı her komut için (ilk kelimesi PATH'te olan) — #5'te "kontrol etmek isterseniz `cat sandbox/merhaba.txt`"
    önerisi iddia sanılıp iki gereksiz uyarı veriyordu.
    kanit: run_command çıktıları + çalıştırılan komutlar + yazılan dosya metinleri (tam, kısaltılmamış).
    Başarıyı değiştirmez, sadece işaretler; etiketler ("hiç sayı") yanlış alarm verebilir, elle bakılır.
    Sınır: işaretsiz düz metindeki iddiaları ("sonuç 2.33") ve gerçek bir çıktıyla aynı olan uydurmayı görmez.
    """
    iddialar = []
    for dil, blok in re.findall(r"```(\w*)\n(.*?)```", cevap, re.S):
        if dil.lower() not in ("python", "py"):
            iddialar += [(satir, "") for satir in blok.splitlines()]
    for satir in re.sub(r"```.*?```", "", cevap, flags=re.S).splitlines():
        iddialar += [(kod, satir) for kod in re.findall(r"`([^`\n]+)`", satir)]
    supheli = []
    for iddia, satir in iddialar:
        iddia = re.sub(r"^\$\s*", "", iddia.strip())  # "$ python3 …" → komut
        if len(iddia) < 2 or any(iddia in k for k in kanit):
            continue
        komut = re.match(r"python3? ", iddia) or shutil.which(iddia.split()[0])  # PATH'te python olmayabilir
        if komut and not re.search(r"→|çıktı", satir.split(iddia, 1)[-1], re.I):
            continue  # sonuç gösterilmeyen öneri
        supheli.append(iddia)
    return supheli


def calistirilmamis_komutlar(cevap, calisanlar):
    """Adım 10o — cevapta önerilen ama run_command ile hiç çalıştırılmamış `python …` komutları.

    10n'de eksik testin baskın nedeni: model toplamayı çalıştırıp "Şimdi diğer işlemleri test edelim: `python …`"
    deyip bitiriyordu; sonuç iddiası olmadığı için kanitsiz_iddialar görmüyordu.
    10q: araç adıyla yazılmış sözde komutlar da (10o kodunda #14: "bu adımları takip et" + `read_file sandbox/oyun.py`,
    `edit_file sandbox/menu.py …`, `run_command python …`). Sadece argümanlı olanlar (yol içeren): #12'de görev
    araç adlarını listelemek, tek başına `read_file` normal.
    calisanlar: run_command'a gerçekten verilen komutlar + diğer araçlar için "araç yol" (kanıt değil: alt görevin
    yazdığı komut çalıştırılmış sayılmaz).
    """
    adaylar = []
    for dil, blok in re.findall(r"```(\w*)\n(.*?)```", cevap, re.S):
        if dil.lower() not in ("python", "py"):
            adaylar += blok.splitlines()
    adaylar += re.findall(r"`([^`\n]+)`", re.sub(r"```.*?```", "", cevap, flags=re.S))
    calisan = {" ".join(k.split()) for k in calisanlar}
    komutlar = []
    for a in adaylar:
        a = " ".join(re.sub(r"^\$\s*", "", a.strip()).split())
        if a.startswith("run_command "):
            a = a.split(" ", 1)[1].strip("'\"")
        if m := re.match(r"(read_file|write_file|edit_file|list_files) (\S*[./]\S*)", a):
            a = f"{m[1]} {m[2]}"  # metin/değişiklik argümanları karşılaştırmaya girmez, yol yeter
        elif not re.match(r"python3? \S+\.py", a):
            continue
        if a not in calisan and a not in komutlar:
            komutlar.append(a)
    return komutlar


NOT_ONEKI = "NOT (bitiş kontrolü): "  # kendi notlarımız kanıt sayılmasın diye tanınır
KANIT_NOTU = (
    NOT_ONEKI + "Cevabındaki şu sonuçlar hiçbir komut çıktısında geçmiyor: {}. Listedeki HER biri için ayrı bir "
    "run_command çağır ya da onu cevaptan çıkar; sadece birini çalıştırıp diğerlerini bırakma. Çalıştırmadığın "
    "bir şeyin sonucunu yazma. Sonra cevabını sadece gerçek çıktılarla yeniden yaz."
)
DEVIR_NOTU = (
    NOT_ONEKI + "Cevabında kendin yapmadığın adımlar var: {}. Bunları araçlarınla (run_command, read_file, "
    "write_file, edit_file) kendin yapabilirsin; kullanıcıya bırakma. Test istendiyse her birini ayrı çalıştırıp gerçek çıktıyı yaz. Çalıştırmaman için bir "
    "neden varsa (ör. tehlikeli, kullanıcı istemedi) bunu cevabında kısaca söyle."
)


def kanit_kontrolu(mesajlar, cevap):
    """Ajanın bitiş kontrolü: kanıtsız çıktı iddiaları (10m) ve kullanıcıya bırakılan komutlar (10o) için modele not
    (yoksa None). 10l-b'de sistem mesajındaki kural yetmedi (#11'de uydurma 2/10, eksik test 7/10)."""
    kanit, calisanlar = [], []
    for m in mesajlar:
        rol = m.get("role") if isinstance(m, dict) else m.role
        icerik = (m["content"] if isinstance(m, dict) else m.content) or ""
        # kendi notumuz kanıt değil: şüpheli iddiaları listeliyor, sayılsa ikinci kontrolde "kanıtlı" görünürdü
        if rol == "tool" or (rol == "user" and not icerik.startswith(NOT_ONEKI)):
            kanit.append(icerik)
        for c in (None if isinstance(m, dict) else m.tool_calls) or []:
            arg = c.function.arguments or {}
            kanit += [str(v) for v in arg.values()]
            if c.function.name == "run_command":
                calisanlar.append(str(arg.get("command", "")))
            elif "path" in arg:
                calisanlar.append(f"{c.function.name} {arg['path']}")
    notlar = []
    if supheli := kanitsiz_iddialar(cevap or "", kanit):
        notlar.append(KANIT_NOTU.format(", ".join(f"'{x}'" for x in supheli)))
    if devir := [k for k in calistirilmamis_komutlar(cevap or "", calisanlar) if k not in supheli]:
        notlar.append(DEVIR_NOTU.format(", ".join(f"'{x}'" for x in devir)))
    return "\n".join(notlar) or None


ajan.BITIS_KONTROLU = kanit_kontrolu

ARACLAR = {**yazma.ARACLAR, "run_command": run_command}

TARIFLER = yazma.TARIFLER + [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Proje kökünde tek bir komut çalıştırır ve çıkış kodunu, stdout ve stderr'i döndürür. "
                "Kabuk yok: ; && | > kullanılamaz. ls, cat, python gibi komutlar serbest; diğerleri kullanıcı "
                "onayı ister; sudo gibi bazıları yasaktır. Dosya silme, taşıma, klasör oluşturma da bununla yapılır "
                "(ör. 'rm sandbox/x.txt', 'mv sandbox/a.txt sandbox/b.txt'); onayı program sorar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Çalıştırılacak komut, ör. 'python sandbox/selam.py'"},
                },
                "required": ["command"],
            },
        },
    },
]


def araci_calistir(cagri):
    return yazma.araci_calistir(cagri, ARACLAR)


if __name__ == "__main__":
    sohbet(SYSTEM, TARIFLER, araci_calistir)
