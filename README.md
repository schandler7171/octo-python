# octo-python

A Python wrapper around Screaming Frog SEO Spider that automates site audits
end to end - sitemap discovery, batched crawling via the CLI, combined export,
and a client-ready summary - in one script.

Built because Screaming Frog's GUI struggles on sites with tens of thousands of
URLs. Running the CLI in 1,000-URL batches gets around the memory ceiling and
makes the whole pipeline resumable.

_Last updated: August 2025_

---

## What it does

Given a domain and a sitemap URL, the script will:

1. Download `robots.txt` and `llms.txt` for the domain.
2. Recursively parse the sitemap (handles sitemap indexes pointing at
   nested sitemaps - the common pattern on big sites).
3. Save the full URL list to a master text file.
4. Split the URL list into 1,000-URL batches.
5. Run the Screaming Frog CLI on each batch, exporting `internal:all` to CSV.
6. Combine every batch CSV into a single Excel workbook.
7. Write a plain-text summary with subdomain counts, robots.txt / llms.txt
   status, and the sitemap source.

Output lands in `C:\K-ScreamingFrog\<sanitized-domain>\` by default.

---

## Requirements

- **Python 3.9+**
- **Screaming Frog SEO Spider** (licensed - the CLI is gated behind a paid
  license). Default install path on Windows:
  `C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe`
- Python packages:
  - `requests`
  - `pandas`
  - `openpyxl` (for `.xlsx` export)

Install the Python dependencies:

```bash
pip install requests pandas openpyxl
```

---

## Configuration

All configuration lives at the top of `crawl.py` under `# === CONFIGURATION ===`:

```python
domain        = "https://www.exampledomain.com"
sitemap_url   = "https://www.exampledomain.com/sitemap.xml"
cli_path      = r'"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli"'
base_folder   = r"C:\K-ScreamingFrog"
sf_export_name = "internal_all.csv"
batch_size    = 1000
```

| Variable | What it controls |
|---|---|
| `domain` | The site you're auditing (used for folder naming and robots.txt / llms.txt fetch). |
| `sitemap_url` | The root sitemap. Can be a sitemap index - the parser walks nested sitemaps. |
| `cli_path` | Full path to Screaming Frog's CLI binary. Quotes are required if the path has spaces. |
| `base_folder` | Where output folders are created. Each domain gets its own subfolder. |
| `sf_export_name` | Name of the CSV Screaming Frog exports per batch (rarely needs changing). |
| `batch_size` | Number of URLs per Screaming Frog invocation. 1,000 is conservative and resumable. Bump higher on beefy machines. |

---

## Usage

```bash
python crawl.py
```

That's it - the script runs all four phases sequentially and prints progress to
stdout. Expect output like:

```
🌐 Extracting URLs from sitemap: https://www.exampledomain.com/sitemap.xml
✅ Master list saved: C:\K-ScreamingFrog\www.exampledomain.com\list_www.exampledomain.com.txt (38214 URLs)
🚀 Crawling batch 1 with 1000 URLs...
✅ Exported: C:\K-ScreamingFrog\...\batch1_internal_all.csv
...
📘 Excel saved: C:\K-ScreamingFrog\...\full_combined_output.xlsx
📄 Summary saved: C:\K-ScreamingFrog\...\summary.txt
```

---

## Output

After a successful run, the domain output folder contains:

```
<base>/<sanitized-domain>/
  ├─ robots.txt                 # downloaded from the site
  ├─ llms.txt                   # downloaded if present
  ├─ list_<domain>.txt          # master list of every sitemap URL
  ├─ batch1_internal_all.csv    # per-batch SF export
  ├─ batch2_internal_all.csv
  ├─ ...
  ├─ full_combined_output.xlsx  # everything stitched into one workbook
  └─ summary.txt                # totals + subdomain breakdown
```

The Excel is the audit deliverable. The summary is the executive-summary
companion. The batch CSVs are kept around so you can re-run analysis without
re-crawling.

---

## Notes on resumability

Every batch is independent. If the script dies partway through:

- Batches that already wrote a CSV are done - leave them alone.
- The current batch's input text file is removed in a `finally` block, so it
  won't interfere with a rerun.
- Re-running the script re-fetches the sitemap and re-batches. If you want to
  skip re-crawling the already-done batches, comment out the loop entries you
  want to skip, or extend the script with a "skip if output CSV exists" check
  (one-line addition).

The combine phase (Phase 3) and summary phase (Phase 4) can be run independently
by removing the crawl loop - they just read whatever batch CSVs are on disk.

---

## Common issues

**`403 Forbidden` on sitemap or robots.txt fetch.** The script sends a desktop
Chrome User-Agent to bypass naive WAFs. Some sites require additional headers
or cookies - add them to the `headers` dict near the top.

**Screaming Frog CLI not found.** Check `cli_path`. On Windows the binary is
named `ScreamingFrogSEOSpiderCli.exe` (the script uses the quoted version
without the `.exe` because Windows resolves it). On macOS/Linux installations
the binary is named differently - adjust accordingly.

**Excel write fails.** Make sure `openpyxl` is installed. Pandas can't write
`.xlsx` without it.

**Some batches crash silently.** Screaming Frog occasionally hangs on
problematic URLs. The script logs these and continues. The summary will tell
you which batch had no output.

---

## License

MIT. Free to fork, modify, ship, and use commercially. Attribution appreciated
but not required.

---

## Author

Scott Chandler
[chandlerdigital.ca](https://chandlerdigital.ca)
[LinkedIn](https://www.linkedin.com/in/schandler7171)
