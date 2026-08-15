# Setup guide

Three services, one job each:

- **Your computer** — where the files live before anyone sees them.
- **GitHub** — stores the files online, and runs the weekly refresh robot.
- **Vercel** — watches GitHub and shows the page at a real URL.

Once set up, the loop runs without you:

> Robot in GitHub wakes Monday → visits bevco.in → writes new prices into `data.json`
> → Vercel notices the change → the live site updates.

---

## What's in this folder

    bevco-site/
    ├── index.html          the page you deploy (built — do not hand-edit)
    ├── index.template.html the page you EDIT; __SEED__ gets replaced on build
    ├── data.json           the 4,435 prices — nothing else
    ├── vercel.json         tells browsers not to cache stale prices
    ├── requirements.txt    what the robot needs to install
    ├── README.md           project notes
    ├── SETUP.md            this file
    ├── scripts/
    │   └── update.py       the robot's instructions
    └── .github/
        └── workflows/
            └── update-prices.yml    the robot's alarm clock

`.github` starts with a dot, so it is HIDDEN by default.
- Mac Finder: press Cmd + Shift + .  to reveal hidden files
- Windows Explorer: View → Show → Hidden items

If you can't see it, it is still there. Confirm from a terminal:

    ls -a bevco-site

---

## Step 1 — Test on your own computer first

    cd bevco-site
    python3 -m http.server 8000

Open http://localhost:8000 in a browser. Press Ctrl+C to stop.

You CAN also just double-click index.html — the page carries a full copy of the
prices inside it as a fallback, so it works with no server at all. The header
will say "Snapshot" instead of "Live".

With a server it says "Live", because it successfully read data.json. That is
the mode Vercel will run in, so test that way before deploying.

Why the fallback exists: browsers block a file opened from your hard drive from
reading another local file (the same-origin policy). Without the embedded copy,
double-clicking index.html shows an empty page and makes you think it's broken.

You should see: dark page, "Effective 11-05-2026", search box, spirit chips,
size chips, price slider. Type "jawan" — you should get results.

---

## Step 2 — Upload to GitHub

1. github.com → + (top right) → New repository
2. Name: bevco-rates
3. Public
4. Do NOT tick "Add a README file" — this folder already has one
5. Create repository
6. On the empty repo page, click the link: "uploading an existing file"
7. Drag in everything INSIDE bevco-site (not the folder itself)
8. Commit changes

"Commit" means: save this version permanently, with a timestamp. Unlike saving a
document, a commit never erases the previous version. That is why you will later
be able to see exactly which brands changed price and when.

CHECK: the repo should list index.html, data.json, README.md, SETUP.md,
requirements.txt, vercel.json, and a scripts folder.

The .github folder will probably be MISSING — GitHub's drag-and-drop uploader
often skips dot-folders, silently. Step 4 fixes it.

---

## Step 3 — Connect Vercel

1. vercel.com → Add New → Project
2. Import bevco-rates
3. Framework Preset: Other
4. Build Command: leave EMPTY
5. Output Directory: leave EMPTY
6. Deploy

Leave those blank because there is nothing to compile. A Next.js site needs a
build step; this is already a finished HTML page.

About 20 seconds later you get a URL like bevco-rates.vercel.app

---

## Step 4 — Create .github if it didn't upload

In the repo: Add file → Create new file

In the filename box type exactly:

    .github/workflows/update-prices.yml

Watch as you type each slash — GitHub creates the folders automatically. This is
the reliable way to make dot-folders on GitHub.

Paste in the contents of update-prices.yml from this folder, then
Commit new file.

---

## Step 5 — Let the robot write to the repo

Repo → Settings → Actions (left sidebar) → General
→ scroll to "Workflow permissions"
→ select "Read and write permissions"
→ Save

By default GitHub robots can only READ. Yours needs to write, because its whole
job is updating data.json. Skip this and the robot runs perfectly for 50 seconds
and then fails on the very last step.

---

## Step 6 — Test the robot now, not next Monday

Repo → Actions tab → "Refresh BEVCO prices" (left sidebar)
→ Run workflow → Run workflow

Takes about a minute. GitHub rents a fresh Ubuntu machine, installs the
PDF-reading tool, runs the script, then discards the machine.

Reading the result:

  Green tick, log says "No change — nothing to commit"
      Perfect. It reached bevco.in, parsed the PDFs, prices match.

  Green tick, and a new commit appears
      Prices changed since 3 Aug. Vercel is already redeploying.

  Red X on "Fetch and parse the current price lists"
      Couldn't reach bevco.in, or BEVCO changed the PDF layout.

  Red X on "Commit if prices changed"
      You skipped Step 5. Set write permissions.

---

## After that

Every Monday 08:00 IST this repeats on its own. When prices change you get an
email about the new commit, and the site is already updated.

Worth doing: click into a price-change commit and view the diff. Red lines are
old prices, green are new. Over a year that becomes a record of every Kerala
liquor price revision.

---

## Features

  Search        multi-word AND matching ("old monk 750"), recent-search chips
  Filters       9 spirit types, 8 sizes, imported-only, log-scaled price range
  Sort          cheapest / priciest / best value (per 100 ml) / A-Z
  Compare       tap up to 4 cards; a sticky tray shows which is best value
  Badges        BEST VALUE on the cheapest tenth per 100 ml within its spirit
  Value bar     where this bottle sits in its spirit's per-100ml spread
  Size family   every size of the same brand, cheapest per ml highlighted
  Summary       cheapest / median / priciest / best per 100 ml / brand count
  Layout        roomy card grid or compact one-line rows
  Endless       scrolls through all matches, 60 at a time
  Surprise me   jumps to a random matching bottle and highlights it
  Shareable     filters live in the URL; "Copy link" puts it on the clipboard
  Keyboard      / focus, Esc clear, 1-9 spirits, 0 clear, s sort, d density,
                r surprise, ? help
  Empty state   tells you which filter is doing the excluding, and offers a fix
  Print         a clean black-on-white list; the chrome is hidden

---


## The extra tools

Four buttons above the results open full-screen panels. None of them clutter
the main list.

  Breakdown   pick any bottle and see the whole cost stack: liquor, excise
              duty, import fee, trade margin, sales tax, cess. Verified across
              all 4,435 rows — the parts add up to the shelf price exactly.
              Median state take is 84%.
  Budget      type an amount, get the best bottle in each spirit at or under
              it, ranked by value per 100 ml rather than by price.
  Size traps  the 870 brand/size pairs where the BIGGER bottle costs more per
              100 ml than the smaller one.
  Changes     what moved since the last revision, up and down, with percentages.

## Files the updater now writes

  data.json        prices (includes product codes)
  breakdown.json   the per-bottle cost stack, loaded only when you open the
                   Breakdown panel
  history.json     one column per revision, keyed by product code; a new column
                   is appended only when prices actually move
  index.html       rebuilt from the template with a slim offline snapshot baked
                   in (codes stripped — they only join against files that
                   cannot load offline anyway)

Cards grow a small sparkline once a product has at least two DIFFERENT prices
on record. With one snapshot there is nothing to draw, which is correct.

## Installing it to a phone

manifest.json plus sw.js make it a PWA: "Add to home screen" gives it an icon
and it opens with no signal. The service worker needs https, so it only kicks
in on the deployed site, never from file:// — the registration is guarded.

Data files are network-first (a stale price is worse than a slow one); the page
shell is cache-first so it opens instantly. Bump CACHE in sw.js when the shell
changes.

---

## Credit, warning, and the Kerala details

At the foot of the page sits an embossed maker's seal — the kind of mark
pressed into the base of a glass bottle. "Created by The_Deja_Vu" runs along
the TOP HALF of the ring on an SVG textPath, with a bottle glyph in the centre,
two small gold diamonds where the arc ends, and "Kerala · 2026" flat beneath.
It sits at 66% opacity and comes up to full on hover.

The arc deliberately stops at the halfway mark. A full ring at this radius is
308 units and the old, longer label needed 227 of them — so its tail carried on
round the bottom and printed straight over the date. Confining the text to the
163-unit top arc leaves 19 units of slack at each end and nothing at the bottom
to collide with. Tests assert the arc path, the fitted text width, and that the
date's baseline stays below the arc and inside the outer ring.

Directly above it, the statutory warning in Malayalam and English:
  മദ്യപാനം ആരോഗ്യത്തിന് ഹാനികരം
  Consumption of alcohol is injurious to health

Kerala touches, added WITHOUT altering the palette or type:
  - the kasavu border — two fine gold lines, the way a Kerala mundu is edged —
    used under the hero and above and below the footer plate
  - കേരളം in the eyebrow, beside the English
  - Malayalam always paired with English, so nothing is lost if a device has
    no Malayalam font installed

--hot, --bg and every other theme variable are unchanged.

## Motion, part two

  Cork pop     adding a bottle to the list pops a gold cork off the card and
               lifts the card slightly. Fires on ADD only, never on remove.
  Tap ripple   filter chips ripple from the exact point you touched. The
               ripple is white when the chip is turning ON (an orange ripple
               would disappear into the orange fill) and orange when it is
               turning off.

Both are skipped entirely under prefers-reduced-motion.

---

## Motion

The page animates: staggered hero entrance, the outlined word draining its fill
once, a count-up on the stat and result counters, FLIP transitions when filters
change (surviving cards glide to their new position, newcomers fade up, hops
longer than ~1.2 screens just cut), spine and bottle reactions on hover, a
sweeping fill on the filter tabs, a shimmering skeleton while loading, a
compacting toolbar, a scroll-progress bar and a back-to-top button.

All of it is CSS and SVG — no GIFs, no video, no image files.

The sticky toolbar tightens as you scroll, but the SIZE FILTER NEVER COLLAPSES
— hiding it made the active size invisible. Only the price range and the
recent-search chips fold away.

Anyone with "reduce motion" enabled in their OS gets the whole thing static.
That is handled by a prefers-reduced-motion block plus a JS flag, so even the
count-ups and FLIP moves are skipped.

Only the first 90 cards take part in FLIP measurement, and only the first 25
stagger their entrance, so a 300-card grid stays smooth on older phones.

---

## Editing the design

Edit index.template.html, NOT index.html. index.html is generated by pasting the
price data into the template, and the updater overwrites it on every refresh.
Any change you make directly to index.html will be lost.

To rebuild after editing the template:

    python3 scripts/update.py --local imfl.pdf fmfl.pdf

---

## Running the updater by hand on your own machine

    pip install -r requirements.txt
    python3 scripts/update.py

Against PDFs you already downloaded:

    python3 scripts/update.py --local imfl.pdf fmfl.pdf

Needs pdftotext. On Ubuntu/Debian: sudo apt install poppler-utils
On Mac with Homebrew: brew install poppler

---

## One decision to make

bevco.in's robots.txt asks automated programs not to visit. Once a week is
gentler than a person refreshing the page, and this is public government pricing
— but it is their stated preference.

To respect it, open .github/workflows/update-prices.yml and delete these lines:

      schedule:
        - cron: "30 2 * * 1"

The "Run workflow" button still works. You just refresh it yourself when you want.

---

## Safety rails already built in

The script refuses to publish if:
  - fewer than 3,000 rows parse (something broke)
  - more than 2% of candidate lines fail (BEVCO changed the layout)
  - the download isn't actually a PDF

And if prices are unchanged it writes nothing at all, so there's no pointless
commit and no pointless redeploy.

A failure shows up as "the robot didn't run" rather than "the site is quietly
showing wrong prices." That is the safer way round.
