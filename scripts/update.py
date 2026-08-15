#!/usr/bin/env python3
"""Fetch the current BEVCO price lists, parse them, write data.json.

Run locally against already-downloaded PDFs:
    python scripts/update.py --local imfl.pdf fmfl.pdf

Run for real (what CI does):
    python scripts/update.py
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests

LIST_PAGE = "https://bevco.in/price-list-2/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data.json")
BREAK = os.path.join(ROOT, "breakdown.json")
HIST = os.path.join(ROOT, "history.json")
TPL = os.path.join(ROOT, "index.template.html")
PAGE = os.path.join(ROOT, "index.html")

PREFIX = {'11':'Brandy','51':'Brandy','62':'Brandy','12':'Whisky','52':'Whisky',
          '13':'Rum','53':'Rum','14':'Gin','54':'Gin','15':'Wine','55':'Wine',
          '16':'Vodka','56':'Vodka','21':'Beer','57':'Tequila','59':'Liqueur'}
STRONG = [('Whisky', r'\bWHISK(?:E)?Y\b'), ('Brandy', r'\bBRANDY\b|\bCOGNAC\b'),
          ('Rum', r'\bRUM\b'), ('Vodka', r'\bVODKA\b'), ('Gin', r'\bGIN\b'),
          ('Tequila', r'\bTEQUILA\b'), ('Beer', r'\bBEER\b'), ('Wine', r'\bWINE\b')]
TYPES = ['Whisky','Brandy','Rum','Vodka','Gin','Beer','Wine','Tequila','Liqueur']
NUM = re.compile(r"^[\d,]+(?:\.\d+)?$")


# ---------------------------------------------------------------- discovery
def find_pdfs():
    """Scrape the price-list page for the newest IMFL and FMFL PDF links."""
    r = requests.get(LIST_PAGE, headers={"User-Agent": UA}, timeout=60, verify=False)
    r.raise_for_status()
    hrefs = re.findall(r'href=["\']([^"\']+\.pdf)["\']', r.text, re.I)
    found = {}
    for kind, pat in (("imfl", r"IMFL.*BEER.*WINE"), ("fmfl", r"FMFL")):
        cands = [urljoin(LIST_PAGE, h) for h in hrefs if re.search(pat, h, re.I)]
        if not cands:
            raise SystemExit(f"No {kind} PDF link found on {LIST_PAGE} — page layout changed.")
        # filenames start PRICE-LIST___DD-MM-YYYY_ ; sort by that date, newest wins
        def keyfn(u):
            m = re.search(r"PRICE-LIST_+(\d{2})-(\d{2})-(\d{4})", u)
            return (m.group(3), m.group(2), m.group(1)) if m else ("0", "0", "0")
        found[kind] = sorted(cands, key=keyfn)[-1]
    return found


def download(url, dest):
    for attempt in range(5):
        try:
            print(f"Downloading {url} (Attempt {attempt + 1})...")
            r = requests.get(url, headers={"User-Agent": UA}, timeout=180, verify=False)
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                raise SystemExit(f"{url} did not return a PDF.")
            open(dest, "wb").write(r.content)
            return dest
        except Exception as e:
            print(f"Connection dropped: {e}. Retrying in 5 seconds...")
            time.sleep(5)
    raise SystemExit(f"Failed to download {url} after 5 attempts.")

# ------------------------------------------------------------------ parsing
def to_text(pdf):
    return subprocess.run(["pdftotext", "-layout", pdf, "-"],
                          capture_output=True, text=True, check=True).stdout


def joined_lines(text):
    """Rejoin rows whose long description pushed the numbers onto the next line."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        cur = lines[i]
        starts_row = re.match(r"^\s*\d+\s+[0-9A-Z]{9,12}\s+\S", cur)
        if (starts_row and not re.search(r"\d+\.\d{2}\s*$", cur)
                and i + 1 < len(lines) and re.match(r"^\s+[\d.,\s]+$", lines[i + 1])):
            cur = cur + " " + lines[i + 1].strip()
            i += 1
        out.append(cur)
        i += 1
    return out


def parse(text, imported, ncols=13):
    rows, skipped = [], 0
    last_desc = ""
    for line in joined_lines(text):
        if re.search(r"Supplier\s*:", line):
            last_desc = ""
            continue
        m = re.match(r"^\s*(\d+)\s+([0-9A-Z]{9,12})\s+(.*)$", line)
        if not m:
            continue
        sl, code, rest = m.groups()
        if code[:2] not in PREFIX:
            continue
        rest = re.sub(r"([A-Za-z])(\d{3,4})(?=\s+\d+\s+\d)", r"\1 \2", rest)
        toks = rest.split()
        tail = []
        while toks and NUM.match(toks[-1]) and len(tail) < ncols:
            tail.insert(0, toks.pop().replace(",", ""))
        if len(tail) < ncols:
            skipped += 1
            continue
        desc = " ".join(toks).strip()
        if desc:
            last_desc = desc
        else:
            desc = last_desc
        if not desc:
            skipped += 1
            continue
        n = [float(x) for x in tail]
        # columns: ml, bot/case, proof, landed cost, excise duty, import fee,
        # cess, WH before/tax/after, FL1 before/tax/after
        rows.append({"sl": int(sl), "code": code, "brand": desc,
                     "ml": int(n[0]), "price": round(n[12]), "imported": imported,
                     "bpc": n[1], "landed": n[3], "excise": n[4], "imp": n[5],
                     "cess": n[6], "fl1_before": n[10], "fl1_tax": n[11],
                     "fl1_after": n[12]})
    return rows, skipped


def spirit(code, brand):
    base = PREFIX[code[:2]]
    hits = [t for t, p in STRONG if re.search(p, brand.upper())]
    return hits[0] if len(hits) == 1 and hits[0] != base else base


def dates_from(text):
    head = text[:4000]
    eff = re.search(r"[Ww]ith effect from\s+(\d{2}-\d{2}-\d{4})", head)
    pub = re.search(r"(\d{2}-[A-Za-z]{3}-\d{2})", head)
    return (eff.group(1) if eff else None), (pub.group(1) if pub else None)


# ------------------------------------------------------------------- output
def build(imfl_text, fmfl_text):
    a, sa = parse(imfl_text, 0)
    b, sb = parse(fmfl_text, 1)
    rows = a + b
    if len(rows) < 3000:
        raise SystemExit(f"Only {len(rows)} rows parsed — refusing to publish a truncated list.")
    if sa + sb > len(rows) * 0.02:
        raise SystemExit(f"{sa+sb} unparsed lines — parser likely broken against a new layout.")

    brands, bidx, data, codes, parts = [], {}, [], [], []
    tidx = {t: i for i, t in enumerate(TYPES)}
    bad = 0
    for r in rows:
        if r["brand"] not in bidx:
            bidx[r["brand"]] = len(brands)
            brands.append(r["brand"])
        data.append([bidx[r["brand"]], r["ml"], r["price"],
                     tidx[spirit(r["code"], r["brand"])], r["imported"]])
        codes.append(r["code"])

        # Per-bottle cost stack. Landed/excise/import are quoted per CASE;
        # cess and the FL1 columns are already per bottle. Verified across the
        # whole list: FL1 before + tax + cess == FL1 after, exactly.
        bpc = r["bpc"] or 1
        liquor = r["landed"] / bpc
        excise = r["excise"] / bpc
        imp = r["imp"] / bpc
        margin = r["fl1_before"] - (liquor + excise + imp)
        if abs((r["fl1_before"] + r["fl1_tax"] + r["cess"]) - r["fl1_after"]) > 0.05:
            bad += 1
        if margin < -0.05:
            bad += 1
        parts.append([round(liquor, 2), round(excise, 2), round(imp, 2),
                      round(margin, 2), round(r["fl1_tax"], 2), round(r["cess"], 2)])

    if bad:
        raise SystemExit(f"{bad} rows failed the cost-stack check — refusing to publish.")

    eff, pub = dates_from(imfl_text)
    checked = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    main = {"effective": eff, "published": pub, "checked": checked,
            "count": len(data), "b": brands, "t": TYPES, "d": data, "k": codes}
    extra = {"effective": eff, "published": pub, "checked": checked,
             "k": codes, "d": parts}
    return main, extra


def rebuild_page():
    """Bake the current data.json into index.html as an offline fallback."""
    if not os.path.exists(TPL):
        print("No index.template.html — skipping page rebuild.")
        return
    tpl = open(TPL, encoding="utf-8").read()
    # The seed is only ever the OFFLINE fallback. Product codes exist to join
    # against breakdown.json / history.json, and neither of those can load
    # offline, so carrying ~50 KB of codes inside the page buys nothing.
    slim = json.load(open(OUT, encoding="utf-8"))
    slim.pop("k", None)
    seed = json.dumps(slim, separators=(",", ":"), ensure_ascii=False)
    if "</script" in seed.lower():
        raise SystemExit("Refusing to embed data containing a script tag.")
    if "__SEED__" not in tpl:
        raise SystemExit("index.template.html is missing the __SEED__ placeholder.")
    open(PAGE, "w", encoding="utf-8").write(tpl.replace("__SEED__", seed))
    print("Rebuilt index.html with the current snapshot.")


def update_history(main):
    """Append a column to history.json whenever prices actually move.

    Keyed by BEVCO product code, which is stable across revisions; row order
    is not. Codes that appear or disappear get null in the columns where they
    did not exist, so every series stays the same length as `dates`.
    """
    prices = {}
    for code, row in zip(main["k"], main["d"]):
        prices[code] = row[2]

    hist = {"dates": [], "series": {}}
    if os.path.exists(HIST):
        try:
            hist = json.load(open(HIST, encoding="utf-8"))
        except Exception:
            pass

    n = len(hist["dates"])
    if n:
        same = all(hist["series"].get(c, [None] * n)[-1] == p for c, p in prices.items()) \
               and len(prices) == sum(1 for c in hist["series"]
                                      if hist["series"][c][-1] is not None)
        if same:
            print(f"History unchanged ({n} snapshot{'s' if n != 1 else ''} on file).")
            return hist

    stamp = main["effective"] or main["checked"]
    if stamp in hist["dates"]:
        stamp = stamp + "+" + main["checked"]
    hist["dates"].append(stamp)
    n = len(hist["dates"])
    for code in set(list(hist["series"].keys()) + list(prices.keys())):
        ser = hist["series"].setdefault(code, [None] * (n - 1))
        while len(ser) < n - 1:
            ser.append(None)
        ser.append(prices.get(code))
    with open(HIST, "w", encoding="utf-8") as f:
        json.dump(hist, f, separators=(",", ":"), ensure_ascii=False)
    print(f"history.json now holds {n} snapshot{'s' if n != 1 else ''}.")
    return hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", nargs=2, metavar=("IMFL_PDF", "FMFL_PDF"))
    args = ap.parse_args()

    if args.local:
        imfl_pdf, fmfl_pdf = args.local
    else:
        urls = find_pdfs()
        print("IMFL:", urls["imfl"])
        print("FMFL:", urls["fmfl"])
        tmp = tempfile.mkdtemp()
        imfl_pdf = download(urls["imfl"], os.path.join(tmp, "imfl.pdf"))
        time.sleep(2)
        fmfl_pdf = download(urls["fmfl"], os.path.join(tmp, "fmfl.pdf"))

    payload, extra = build(to_text(imfl_pdf), to_text(fmfl_pdf))

    old = None
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            pass

    if bool(old) and old.get("d") == payload["d"] and old.get("k") == payload.get("k"):
        print(f"No price changes ({payload['count']} items).")
    else:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
        changed = "first run" if not old else f"{len(payload['d'])} rows, was {len(old.get('d', []))}"
        print(f"Wrote data.json — {changed}; effective {payload['effective']}, "
              f"published {payload['published']}")

    with open(BREAK, "w", encoding="utf-8") as f:
        json.dump(extra, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Wrote breakdown.json — {len(extra['d'])} cost stacks.")

    update_history(payload)
    rebuild_page()


if __name__ == "__main__":
    main()
