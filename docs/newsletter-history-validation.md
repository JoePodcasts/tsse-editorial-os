# Newsletter History Validation Report

This validation report summarizes missing critical fields in `data/newsletter_history.csv` after conservative name normalization.

## Summary

- total records: 45
- records missing `connected_insight_guest`: 0
- records missing `startup_corner_company`: 3
- records missing `featured_guest`: 26
- records missing `featured_episode`: 27

## Records missing `startup_corner_company`

- issue 34
- issue 33
- issue 32

## Records missing `featured_guest`

- issue 72
- issue 71
- issue 67
- issue 66
- issue 65
- issue 64
- issue 63
- issue 62
- issue 54
- issue 53
- issue 52
- issue 51
- issue 49
- issue 44
- issue 43
- issue 42
- issue 40
- issue 39
- issue 38
- issue 37
- issue 36
- issue 35
- issue 34
- issue 33
- issue 32
- issue 31

## Records missing `featured_episode`

- issue 72
- issue 71
- issue 70
- issue 67
- issue 66
- issue 65
- issue 64
- issue 63
- issue 62
- issue 54
- issue 53
- issue 52
- issue 51
- issue 49
- issue 44
- issue 43
- issue 42
- issue 40
- issue 39
- issue 38
- issue 37
- issue 36
- issue 35
- issue 34
- issue 33
- issue 32
- issue 31

## Notes

- No connected insights guest values are missing after parsing.
- Missing `featured_guest` and `featured_episode` values are largely due to historical archive formatting that does not include explicit labeled episode/guest metadata in all older issues.
- Sector-specific improvements to the importer can help capture these fields from narrative text, but this validation report preserves the data as-is when fields are not clearly extracted.
