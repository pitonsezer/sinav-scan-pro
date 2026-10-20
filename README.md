# SINAV SCAN PRO – GitHub Actions EXE

Python'u kendi bilgisayariniza kurmaniz gerekmez.

## GitHub'da EXE olusturma
1. GitHub'da yeni, bos bir depo acin (ornegin `sinav-scan-pro`).
2. Bu paketin **icindeki** `sinav_scan_pro.py`, `requirements.txt` ve `.github/workflows/windows-exe.yml` dosyalarini, klasor yapisini koruyarak depoya yukleyin. (Gizli `.github` klasorunun da yuklendiginden emin olun.)
3. Depoda **Actions > Windows EXE Derle > Run workflow** tiklayin. Alternatif olarak `main` dalina dosya eklenince derleme baslar.
4. Tamamlaninca is akisi sayfasinin **Artifacts** bolumunden `SINAV_SCAN_PRO_Windows_EXE` dosyasini indirin.
5. ZIP'ten `SINAV_SCAN_PRO.exe` dosyasini cikartip calistirin.

## Test
- Ilk olarak programa iki sayfalik bir deneme PDF'si yukleyin ve her 2 sayfayi tek dosyaya ayirmayi deneyin.
- Dogrudan tarama icin ayrica Windows tarayici surucusu ve [NAPS2](https://www.naps2.com/) gerekir.
- Canon MF635Cx ve HP 8710 baglantisi henuz fiziksel cihazlarda test edilmemistir.
- İlk ADF denemesinde iki fiziksel yaprak kullanin; sirayi ve ciktilari dogrulayin.
- Kimlik gizleme uygulamadan cikan PDF'ler icin gecerlidir; kaynak PDF yerel bilgisayarda korunur.

Bu paket EXE dosyasinin kendisi degil, GitHub'in EXE uretmesi icin gerekli kaynak ve is akisidir.
