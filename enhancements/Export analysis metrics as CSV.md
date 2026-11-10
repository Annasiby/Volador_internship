## Summary
Add an option to export the analysis metrics already used in the application and PDF report as a machine-readable CSV file. This would let users inspect area and change summaries in spreadsheet tools without manually copying values from the report.

## Acceptance criteria
- Users can download a CSV for a completed analysis from the relevant results view or report workflow.
- The CSV includes clearly named columns, units, and the same metric values shown in the analysis results.
- Empty or unavailable metrics are represented consistently and do not produce a malformed file.
- Add or update tests to check the CSV contents and edge cases.

## Impact estimate
**Impact: High** — makes results easier to compare, share, and use in downstream analysis. **Effort: Medium** — requires connecting existing metrics to an export path and testing the output.
