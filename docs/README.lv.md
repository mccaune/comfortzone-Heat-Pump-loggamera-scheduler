# Comfort Zone siltumsūkņa temperatūras plānotājs

**Neoficiāls Python risinājums**, lai noteiktās stundās mainītu Comfort Zone siltumsūkņa telpas temperatūras iestatījumu, izmantojot Loggamera tīmekļa portālu. Darbojas uz Ubuntu Server un Raspberry Pi 3 bez grafiskās vides.

## Kāpēc tas nepieciešams?

Mērķis ir automātiski pielāgot vēlamo telpas temperatūru elektroenerģijas cenu grafikam. Piemēra grafiks: 02:00 un 12:00 iestatīt 24 °C, savukārt 06:00 un 16:00 — 19 °C. Faktiskais ietaupījums nav aprēķināts vai pierādīts; tas atkarīgs no apkures sistēmas un mājas.

Izstrādes laikā tika meklēta iespēja izmantot pieejamo API, bet ar to **neizdevās panākt nepieciešamo temperatūras iestatījuma maiņu**. Tā nav pretenzija, ka ražotājam vispār nav rakstīšanas API. Praktiski izdevās izmantot Loggamera tīmekļa portāla autentificētu pieprasījumu `POST /LoggameraPro/SetParameter` ar `SetIndoorTemp`. Šis nav oficiāli dokumentēts publiskais API un portāla izmaiņas var salauzt risinājumu.

## Darbība

1. `systemd` taimeris palaiž skriptu norādītajā laikā.
2. Python nosaka aktuālo temperatūru pēc grafika un laika zonas.
3. Izveido Loggamera sesiju, ielogojas un nosūta temperatūras maiņu.
4. Veiksmi konstatē tikai tad, ja serveris atgriež `OK`; kļūdas gadījumā veic līdz trim mēģinājumiem un beidz darbu ar kļūdas kodu.
5. Darbības rezultāts redzams `journalctl`.

## Instalēšana

Pilna instrukcija angļu valodā ir [README.md](../README.md). Īsā versija:

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone https://github.com/YOUR-USERNAME/comfortzone-loggamera-scheduler.git
cd comfortzone-loggamera-scheduler
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
nano .env
```

Aizpildi savu e-pastu, paroli un **savas ierīces ID**. Nekad nepublicē aizpildīto `.env` failu.

```bash
set -a
source .env
set +a
.venv/bin/python comfortzone_scheduler.py --once
```

Šī komanda **tiešām maina siltumsūkņa iestatījumu**. Pārbaudi rezultātu uz iekārtas. Automātiskai palaišanai izmanto `systemd/comfortzone.service` un `systemd/comfortzone.timer` paraugus no repozitorija; lietotājvārds un failu ceļi tajos jāpielāgo savam datoram. Grafika laikiem `.env` un taimera failā jāsakrīt.

## Pārbaudītais un ierobežojumi

Risinājums pārbaudīts ar Python 3.12, Ubuntu Server 24.04 un Raspberry Pi 3. Komanda ar 19 °C tika veiksmīgi pieņemta un iestatījums apstiprināts arī pašā siltumsūknī. Pēc pārstartēšanas taimeris turpināja darboties. Nav pierādīta visu modeļu savietojamība vai elektroenerģijas ietaupījums. `302` pāradresācijas kļūdu konkrētajā uzstādījumā izraisīja nepareiza `.env` parole, kaut arī sākotnējā login pārbaude ziņoja par veiksmi.
