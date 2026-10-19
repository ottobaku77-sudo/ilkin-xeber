# İlkin xəbər

Azərbaycan xəbərləri aqreqatoru — əsas dil **Azərbaycan dili**. Statik sayt, GitHub Actions hər 30 dəqiqədən bir
açıq RSS lentlərindən başlıqları, qısa anonsları və orijinala keçidləri yığır və GitHub Pages-ə yerləşdirir.

- `index.html` — bütün xəbərlər (rubrikalar: Futbol, Siyasət, İqtisadiyyat, Cəmiyyət, Hadisə, İdman, Dünya, Mədəniyyət, Digər)
- `futbol.html` — ⚽ Futbol bölməsi, alt filtrlər: **Real Madrid**, **Barselona**
- `AZ / RU` düyməsi: defolt AZ; rus dilli lentlər ikinci dərəcəlidir. Komanda filtrlərində AZ + RU birlikdə göstərilir.
- Vaxt Bakı vaxtı ilə (UTC+4).

Lentlər və rubrika qaydaları `build.py` faylındadır. Lokal: `pip install feedparser && python build.py` → `site/`.

## 🌍 Dünya futbolu

`futbol.html?world=1` — dünyanın aparıcı idman nəşrlərindən futbol xəbərləri (BBC Sport, Sky Sports, The Guardian,
The Independent, CBS Sports, Football365, Football Italia, Marca, AS, Mundo Deportivo, Sport, La Gazzetta dello Sport,
Corriere dello Sport, Kicker; ESPN və UEFA lentləri əlçatan olanda avtomatik qoşulur). Hər mənbədən ən çox 20 xəbər, son 3 gün.

- Yalnız **başlıq + qısa anons** (≈200 simvol) götürülür və `translate.py` ilə avtomatik Azərbaycan dilinə tərcümə olunur
  (Google-un pulsuz ictimai tərcümə ünvanı, açar tələb etmir). Tam mətn kopyalanmır — hər kartda orijinal mənbə nişanı
  və «Mənbədə oxu» keçidi var. Tərcümə alınmasa, orijinal mətn göstərilir.
- Tərcümədən əvvəl klub/oyunçu/turnir adları standart Azərbaycan yazılışına çevrilir (Barça → Barselona, Man Utd →
  Mançester Yunayted, Champions League → Çempionlar Liqası ...), tərcümədən sonra futbol lüğəti ilə düzəlişlər edilir
  (menecer → baş məşqçi, məqsəd vurdu → qol vurdu, ahəng qanununa uyğun şəkilçilər, böyük hərf, cümlə sərhədində kəsmə).
- Keş: `cache/translations.json` (GitHub Actions-da `actions/cache` ilə saxlanılır) — eyni başlıq yenidən tərcümə olunmur.
- Real Madrid / Barselona filtrlərinə Marca, AS, Mundo Deportivo və Sport xəbərləri də düşür.
