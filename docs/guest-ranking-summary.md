# Guest Ranking Summary

This document summarizes `data/guest_rankings.csv`.

## Overview

- Total guest rows: 179
- Total Rank 4 guests: 54
- Unique Rank 4 guest names: 54

## Top 20 Rank 4 guests by episode number

1. Episode 2 — Gokul Rajaram
2. Episode 8 — Naeem Zafar
3. Episode 9 — Ian Rountree
4. Episode 10 — Kamal Hassan
5. Episode 11 — Pat Matthews
6. Episode 12 — Ravi Belani
7. Episode 14 — Shruti Gandhi
8. Episode 16 — Manan Mehta
9. Episode 17 — Lo Toney
10. Episode 20 — Sheel Mohnot
11. Episode 25 — Ullas Naik
12. Episode 26 — Ashmeet Sidana
13. Episode 34 — Vivek Krishnamurthy
14. Episode 50 — Arjan Schutte
15. Episode 51 — Hans Morris
16. Episode 53 — Sunil Nagaraj
17. Episode 54 — Satya Patel
18. Episode 55 — Ramneek Gupta
19. Episode 60 — Mark Fernandes
20. Episode 63 — Galym Imanbayev

## Duplicate or malformed records

### Duplicate guest names

- `Scott Barclay` appears twice (episodes 3 and 123)
- `Geoff Ralston` appears twice (episodes 33 and 167)

### Malformed records

- Line 179: `Steve Kim` has an empty `URL` field but a valid Rank 4 value.
- Line 180: contains only `54` in the `GUEST RANK` column and is otherwise empty; this row is malformed and should be removed or corrected.

## Notes

- The duplicate guest names are not necessarily invalid in this dataset; they may represent separate appearances and should be validated against editorial intent.
- The malformed trailing row should be cleaned before importing or using `guest_rankings.csv` as a structured source.
