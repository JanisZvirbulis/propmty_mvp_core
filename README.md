# Propmty - Property Management Platform

Propmty ir multifunkcionāla īpašumu pārvaldības platforma, kas izstrādāta kā SaaS (Software as a Service) risinājums ar multi-tenant arhitektūru, kas paredzēta īpašumu īpašniekiem, pārvaldniekiem un īrniekiem.

## Projekta pārskats

Propmty platforma nodrošina pilnīgu īpašumu pārvaldības ekosistēmu:

- **Multi-tenant arhitektūra** - katrs uzņēmums darbojas nošķirti savā vidē
- **Pielāgojami abonementi** - dažādi plāni ar dažādiem ierobežojumiem un funkcionalitāti
- **Lietotāju lomas** - uzņēmumu īpašnieki, pārvaldnieki, dalībnieki un īrnieki ar dažādām piekļuves tiesībām
- **Īpašumu pārvaldība** - pilnīga īpašumu un telpu uzskaite
- **Īres līgumu pārvaldība** - digitāla īres līgumu pārvaldība un automātiska rēķinu ģenerēšana
- **Skaitītāju uzskaite** - ūdens, elektrības, gāzes un apkures skaitītāju rādījumu reģistrēšana un patēriņa aprēķini
- **Rēķinu sistēma** - automātiska rēķinu ģenerēšana, iekļaujot īres maksu un komunālos maksājumus
- **Problēmu ziņošanas sistēma** - īrnieki var ziņot par problēmām, kas tiek pārvaldītas platformā
- **Īrnieku portāls** - īrniekiem pieejams portāls rēķinu apskatei, problēmu ziņošanai un skaitītāju rādījumu iesniegšanai

## Tehnoloģijas

- **Backend:** Python 3.9+, Django 5.1
- **Frontend:** Bootstrap 5.3, JavaScript
- **Datu bāze:** PostgreSQL
- **E-pasta pakalpojumi:** SMTP (Gmail)
- **Drošība:** Django iebūvētā autentifikācijas sistēma
- **Failu/Bilžu uzglabāšana:** AWS S3 

## Projekta struktūra

Projekts sastāv no 7 galvenajām Django aplikācijām:

1. **core** - bāzes funkcionalitāte, middleware komponentes un tenant arhitektūra
2. **companies** - uzņēmumu pārvaldība, dalībnieku uzaicināšana
3. **users** - lietotāju pārvaldība, autentifikācija, profili
4. **properties** - īpašumu un telpu pārvaldība, skaitītāju uzskaite
5. **inspections** - īpašumu apsekošana, problēmu ziņojumi
6. **leases** - īres līgumu pārvaldība
7. **subscriptions** - abonementu plānu pārvaldība
8. **tenant_portal** - īrnieku portāls ar pielāgotu skatu un funkcionalitāti

## Galvenās funkcijas

### Multi-tenant arhitektūra

Sistēma izmanto URL bāzētu multi-tenant arhitektūru, kur katram uzņēmumam ir savs unikāls slug, kas parādās URL adresē:

```
https://example.com/{company_slug}/...
```

Middleware komponente analizē katru pieprasījumu, atrod atbilstošo uzņēmumu un piesaista to pieprasījumam, nodrošinot datu nošķirtību starp uzņēmumiem.

### Lietotāju lomas

Sistēma atbalsta šādas lietotāju lomas:

- **Uzņēmuma īpašnieks** - pilnīga piekļuve uzņēmuma datiem un iestatījumiem
- **Administrators** - piekļuve lielākajai daļai funkcionalitātes
- **Pārvaldnieks** - piekļuve īpašumu un īres līgumu pārvaldībai
- **Dalībnieks** - ierobežota piekļuve uzņēmuma datiem
- **Īrnieks** - piekļuve īrnieku portālam, saviem rēķiniem un īrētajam īpašumam

### Īpašumu pārvaldība

Platforma ļauj pārvaldīt:

- Dažādu veidu īpašumus (dzīvojamās mājas, komerciāli īpašumi)
- Telpas vai dzīvokļus īpašumos
- Skaitītājus katrai telpai
- Skaitītāju rādījumus un patēriņa aprēķinus

### Īres līgumu pārvaldība

- Īres līgumu izveidošana konkrētām telpām
- Īrnieku uzaicināšana uz platformu
- Īres perioda un maksas pārvaldība
- Īres līgumu pagarināšana vai izbeigšana

### Rēķinu sistēma

- Automātiska rēķinu ģenerēšana, balstoties uz īres līgumiem
- Skaitītāju rādījumu iekļaušana rēķinos
- Rēķinu statusa izsekošana (izsniegts, samaksāts, kavēts)
- E-pasta paziņojumi īrniekiem par jauniem rēķiniem

### Problēmu ziņošanas sistēma

- Īrnieki var ziņot par problēmām savās telpās
- Fotoattēlu augšupielāde
- Problēmu statusa izsekošana
- Uzdevumu piešķiršana pārvaldniekiem vai tehniskajam personālam

### Abonementu sistēma

- Dažādi abonementu plāni ar atšķirīgiem ierobežojumiem
- Ierobežojumi īpašumu, telpu un lietotāju skaitam
- Funkcionalitātes ierobežojumi atkarībā no abonementa

## Instalācija

### Priekšnosacījumi

- Python 3.9+
- PostgreSQL
- Git
- AWS priekš fileupload

### Instalācijas soļi

1. Klonējiet repozitoriju:
   ```
   git clone https://github.com/JanisZvirbulis/propmty_mvp_core.git
   cd propmty_mvp_core
   ```

2. Izveidojiet un aktivizējiet virtuālo vidi:
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Instalējiet nepieciešamās pakotnes:
   ```
   pip install -r requirements.txt
   ```

4. Izveidojiet `.env` failu ar sekojošiem mainīgajiem:
   ```
   DB_NAME=your_db_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   EMAIL_HOST_USER=your_email@gmail.com
   EMAIL_HOST_PASSWORD=your_email_app_password
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_STORAGE_BUCKET_NAME=your_storage_bucket_name
   AWS_S3_CUSTOM_DOMAIN=your_bucket_name.s3.eu-north-1.amazonaws.com
   AWS_S3_SIGNATURE_VERSION=s3v4
   AWS_S3_REGION_NAME=you_aws_s3_region_name
   ```

5. Veiciet migrācijas:
   ```
   python manage.py migrate
   ```

6. Izveidojiet superuser:
   ```
   python manage.py createsuperuser
   ```

7. Palaidiet serveri:
   ```
   python manage.py runserver
   ```

## Lietošana

### Pirmā palaišana

1. Izveidojiet jaunu kontu kā uzņēmuma īpašnieks
2. Izveidojiet uzņēmumu ar unikālu nosaukumu
3. Pievienojiet īpašumus un telpas
4. Uzaiciniet īrniekus vai citus uzņēmuma dalībniekus

### Īres pārvaldība

1. Izveidojiet īres līgumu konkrētai telpai
2. Uzaiciniet īrnieku
3. Sekojiet līdzi īres maksājumiem
4. Ģenerējiet rēķinus

### Skaitītāju pārvaldība

1. Pievienojiet skaitītājus telpām
2. Reģistrējiet skaitītāju rādījumus
3. Aprēķiniet patēriņu un iekļaujiet to rēķinos

## Izstrādes ceļvedis

- [ ] Papildu valodu atbalsts
- [ ] Maksājumu integrācija (Stripe, PayPal)
- [ ] Mobila aplikācija īrniekiem
- [ ] API priekš trešo pušu integrācijām
- [ ] Plašāka atskaišu ģenerēšana
- [ ] Notikumu plānotājs
- [ ] Dokumentu pārvaldība un glabāšana

## Licence

Šis projekts ir licencēts ar [jūsu izvēlētā licence] - skatīt LICENSE failu detalizētākai informācijai.

## Autori

- Jānis Zvirbulis - galvenais izstrādātājs
- Nauris Soltums - UI/UX izstrādātājs
