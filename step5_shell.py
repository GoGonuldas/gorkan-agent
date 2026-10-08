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
import shlex
import subprocess
import sys
from pathlib import Path

import step2_tools as okuma
import step4_write as yazma
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
