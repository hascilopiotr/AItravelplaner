# About the place data

- Places come from OpenStreetMap. Names and locations are reliable; other fields less so.
- **Prices** are not in the data. Estimate realistic local prices per person in the
  trip's currency (typical museum ticket, a main course with a drink, a coffee and
  cake). `usually_free` marks places that normally have no entry fee.
- **Opening hours** may be missing (`null`). For the key stops of a day, prefer places
  with known opening hours. Parks, monuments and landmarks without hours can be
  treated as always accessible during the day.
- Many museums and galleries are **closed on Mondays** — check their `opening_hours`.
- Some entries are minor (small plaques, chain fast-food). Prefer places that are
  clearly worth a visitor's time.
