# Name Normalization Report

This report documents the conservative name normalization proposals for `data/newsletter_history.csv`.

## Approach

Normalization was intentionally conservative. Changes were limited to:

- removing trailing organization names appended to guest names (e.g. `from NGP`)
- removing unnecessary suffixes such as `from partner`
- normalizing whitespace only where needed
- preserving capitalization and names unless the modification was clearly a formatting issue
- avoiding any inferred name replacements unless confidence was very high

## Proposed Modifications

| Issue | Field | Original Value | Proposed Normalized Value |
|------:|-------|----------------|---------------------------|
| 74 | `featured_guest` | `Gilad Shai from BMI` | `Gilad Shai` |
| 73 | `featured_guest` | `Debjit Mukerji from NGP` | `Debjit Mukerji` |
| 69 | `featured_guest` | `Mark Suster from Upfront` | `Mark Suster` |
| 68 | `featured_guest` | `Sheel Mohnot from Better` | `Sheel Mohnot` |
| 57 | `featured_guest` | `Scott Barclay of Insight` | `Scott Barclay` |
| 56 | `featured_guest` | `Rajan Maruthavanan of Upekkha` | `Rajan Maruthavanan` |
| 47 | `featured_guest` | `Mark Suster from partner` | `Mark Suster` |

## Notes

- The normalization targets only obvious formatting problems in guest names.
- No connected insights, startup corner, or community organization fields were modified because their values were already in acceptable form or required context that would be unsafe to infer.
- The `featured_guest` value for issue 70 remains unchanged because the text is not a simple formatting issue but a mistaken extraction.

## Summary

- Proposed modifications: 7
- Fields targeted: `featured_guest`
- No name replacements were made unless confidence was high and the change was clearly a formatting cleanup.
