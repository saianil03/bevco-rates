# BEVCO retail rates

Static, searchable mirror of the Kerala State Beverages Corporation FL-1 shop price list.

## How it stays current

`scripts/update.py` scrapes https://bevco.in/price-list-2/ for the newest
IMFL/Beer/Wine and FMFL/FMW price-list PDFs, parses them with `pdftotext -layout`,
and writes `data.json`. It then rebuilds `index.html` from `index.template.html`,
baking the same data into the page as an offline fallback, so the page still works
when opened directly from disk. A GitHub Action runs it every Monday at 08:00 IST.

**Edit `index.template.html`, never `index.html`** — the latter is generated.
If prices are unchanged the script writes nothing and the Action makes no commit.
When it does commit, Vercel redeploys automatically.

The script refuses to publish if it parses fewer than 3,000 rows or if more than
2% of candidate lines fail to parse — a layout change should break the build
loudly, not silently publish a half-empty price list.

## Deploy

Vercel → New Project → import this repo. Framework preset **Other**.
Leave build command and output directory blank.

## Run the updater by hand

    pip install -r requirements.txt
    python scripts/update.py

Against PDFs already on disk:

    python scripts/update.py --local imfl.pdf fmfl.pdf

Requires `pdftotext` (Debian/Ubuntu: `apt install poppler-utils`).

## Caveats

- Prices shown are the FL-1 counter price per bottle. The PDF's other price
  column is the warehouse price *per case* — roughly 10x larger.
- Spirit type is derived from the first two digits of the BEVCO product code,
  overridden by the bottle label where the two disagree.
- Unofficial. The price board at the shop is the authority.
