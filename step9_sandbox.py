"""Adım 9: İşletim sistemi seviyesinde sandbox — run_command'ı macOS sandbox-exec içinde çalıştır.

Adım 5'in bilinen açığı: izin listesi komutun ADINA bakıyor. `python` serbest, yani
`python -c "import os; os.remove('README.md')"` hiçbir kontrole takılmıyordu. Program içinde ne yaptığını
komut adından bilemeyiz; kısıtı çekirdeğe (kernel) koymak gerekir.

sandbox-exec (macOS'un yerleşik Seatbelt aracı) komutu ve onun başlattığı her alt süreci şu kurallarla çalıştırır:
  - yazma : sadece sandbox/ (ve /dev/null)
  - okuma : ev klasöründe dosya İÇERİĞİ yasak (~/.ssh, ~/.zshrc…), proje klasörü ve projenin Python'u hariç.
            Dosya bilgisi (metadata) serbest: Python başlarken yol çözerken üst klasörlere bakıyor.
  - ağ    : yok
İzin seviyeleri (Adım 5) aynen duruyor: rm yine onay ister. Ama onay verilse bile sandbox/ dışına yazılamaz.
Sınırlar: kural listesi "her şeye izin ver, şunları yasakla" biçiminde (süreç başlatma, IPC vb. serbest);
sandbox-exec Apple'ın "deprecated" dediği ama hâlâ çalışan bir araç; sadece macOS.

Araçlar, hafıza, özetleme ve alt görevler Adım 8'den geliyor.

Çalıştır:  .venv/bin/python step9_sandbox.py [--no-think] [--dusunme-siniri SN] [--num-ctx N] [--maks-tur N] [--model AD] [--host URL]
Komutlar:  /sifirla   /cikis
"""
import shutil
import sys
from pathlib import Path

import step2_tools as okuma
import step3_agent as ajan
import step4_write as yazma
import step5_shell as kabuk
import step8_subtask as alt

# Yollar profile metin olarak gömülmez, -D ile parametre verilir: yolda tırnak vb. olsa profil bozulmaz.
PROFIL = """
(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath (param "KUM")) (literal "/dev/null"))
(deny file-read-data (subpath (param "EV")))
(allow file-read-data (subpath (param "KOK")) (subpath (param "PYTHON")))
"""


def sandbox_icinde(argv):
    """argv'yi sandbox-exec ile sarar. Yollar her çağrıda okunur (eval KOK/KUM'u geçici kopyaya çeviriyor)."""
    yol = shutil.which(argv[0])
    if yol is None:  # sandbox-exec'in kendi hatası yerine run_command'ın bildiği hata
        raise FileNotFoundError(argv[0])
    # resolve(): sandbox gerçek yollara bakar (/var → /private/var; Adım 6'daki tuzak)
    parametreler = {
        "KUM": yazma.KUM.resolve(),
        "KOK": okuma.KOK.resolve(),
        "EV": Path.home().resolve(),
        "PYTHON": Path(sys.prefix).resolve(),  # .venv: eval'de KOK geçici kopya olunca da python okunabilsin
    }
    d = [x for ad, deger in parametreler.items() for x in ("-D", f"{ad}={deger}")]
    return ["sandbox-exec", "-p", PROFIL, *d, yol, *argv[1:]]


kabuk.sarmala = sandbox_icinde  # step5'in run_command'ı artık her komutu sandbox içinde çalıştırır

SYSTEM = alt.SYSTEM + (
    " Komutlar işletim sistemi sandbox'ında çalışır: sadece sandbox/ klasörüne yazabilir, ağa çıkamaz. "
    "'Operation not permitted' hatası bu yüzdendir; aşmaya çalışma, kullanıcıya söyle."
)

if __name__ == "__main__":
    ajan.sohbet(SYSTEM, alt.TARIFLER, alt.araci_calistir, hazirla=alt.hazirla)
