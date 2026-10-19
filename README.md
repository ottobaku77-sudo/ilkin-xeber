# İlkin xəbər

Azərbaycan xəbərləri aqreqatoru — əsas dil **Azərbaycan dili**. Statik sayt, GitHub Actions hər 30 dəqiqədən bir
açıq RSS lentlərindən başlıqları, qısa anonsları və orijinala keçidləri yığır və GitHub Pages-ə yerləşdirir.

- `index.html` — bütün xəbərlər (rubrikalar: Futbol, Siyasət, İqtisadiyyat, Cəmiyyət, Hadisə, İdman, Dünya, Mədəniyyət, Digər)
- `futbol.html` — ⚽ Futbol bölməsi, alt filtrlər: **Real Madrid**, **Barselona**
- `AZ / RU` düyməsi: defolt AZ; rus dilli lentlər ikinci dərəcəlidir. Komanda filtrlərində AZ + RU birlikdə göstərilir.
- Vaxt Bakı vaxtı ilə (UTC+4).

Lentlər və rubrika qaydaları `build.py` faylındadır. Lokal: `pip install feedparser && python build.py` → `site/`.
