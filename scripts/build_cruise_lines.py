"""Rebuild the cruise line pages from the public totals feed.

Run once a day by .github/workflows/cruise-line-totals.yml, or by hand:

    python scripts/build_cruise_lines.py

It reads one public address that returns totals per cruise line and nothing
about any member, then writes:

    cruise-lines/index.html            the list of every cruise line
    cruise-lines/<line>/index.html     one page per cruise line
    cruise-lines/totals.json           the figures the pages were built from
    sitemap.xml                        so search engines find every page

If the figures have not changed since the last run it writes nothing, so the
"Updated" date on the pages is the day the figures last changed.

It refuses to write anything if the feed is unreachable or looks wrong. A day
with stale pages is better than a day with broken or empty ones.

Standard library only. No keys, no sign-in: the feed is public by design.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

FEED = "https://dpfadeuxbniufdonzkvy.supabase.co/functions/v1/cruise-line-totals"
SITE = "https://outtheretogether.com"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cruise-lines"
PLAY = "https://play.google.com/store/apps/details?id=com.blockbeam.outthere"
APPLE = "https://apps.apple.com/app/id6816005221"
WEB_APP = "https://app.outtheretogether.com/sign-in"
CSS_VERSION = "20261125-2"

# Pages that exist outside this script. Kept here so the sitemap is whole.
STATIC_PAGES = ["", "affiliate-disclosure/", "child-safety/", "terms/", "privacy/", "cookies/", "delete-account/"]

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", " and ")).strip("-")


def long_date(day: dt.date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def month_year(iso: str) -> str:
    day = dt.date.fromisoformat(iso)
    return f"{MONTHS[day.month - 1]} {day.year}"


def number(value: int) -> str:
    return f"{value:,}"


def members_phrase(count: int) -> str:
    """'9 Out There Together members have' / '1 Out There Together member has'."""
    if count == 1:
        return "1 Out There Together member has"
    return f"{number(count)} Out There Together members have"


def article(name: str) -> str:
    """'an' before a vowel sound, including initials said as letters (MSC)."""
    return "an" if re.match(r"(?i)[aeio]|MSC\b|NCL\b", name) else "a"


def join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def fetch() -> list[dict]:
    request = urllib.request.Request(FEED, headers={"User-Agent": "outthere-site-build"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    lines = payload.get("cruise_lines")
    if not isinstance(lines, list) or len(lines) < 5:
        raise SystemExit("Feed returned too few cruise lines; nothing written.")
    cleaned = []
    for row in lines:
        cleaned.append({
            "name": str(row["name"]).strip(),
            "is_charter_operator": bool(row["is_charter_operator"]),
            "members": int(row["members"]),
            "upcoming_sailings": int(row["upcoming_sailings"]),
            "ships": int(row["ships"]),
            "last_departure": str(row["last_departure"]),
        })
        facts = clean_facts(row.get("facts"))
        if facts:
            cleaned[-1]["facts"] = facts
        dt.date.fromisoformat(cleaned[-1]["last_departure"])
        if not cleaned[-1]["name"] or cleaned[-1]["members"] < 0:
            raise SystemExit("Feed row failed checks; nothing written.")
    if len({slug(row["name"]) for row in cleaned}) != len(cleaned):
        raise SystemExit("Two cruise lines share an address; nothing written.")
    cleaned.sort(key=lambda row: (-row["members"], row["name"].lower()))
    return cleaned


# ------------------------------------------------------- facts about a line

# Itinerary lines that are scenery from the ship, not somewhere you go ashore.
NOT_A_PORT = re.compile(r"^(cruise in|cruising|scenic)\b|glacier viewing|\bstrait$", re.I)
# The directory's catch-all region, worded for a reader.
REGION_LABELS = {"Other / Mixed": "Other regions"}


def clean_facts(raw: object) -> dict | None:
    """Keep only well-formed facts. Anything odd is dropped, never published."""
    if not isinstance(raw, dict):
        return None

    def counted(key: str, label: str, count: str, limit: int) -> list[tuple[str, int]]:
        out = []
        for item in raw.get(key) or []:
            if not isinstance(item, dict):
                continue
            name, value = item.get(label), item.get(count)
            if isinstance(name, (str, int)) and str(name).strip() and isinstance(value, int) and value > 0:
                out.append((str(name).strip(), value))
        return out[:limit]

    nights = raw.get("nights") if isinstance(raw.get("nights"), dict) else {}
    common = []
    for item in nights.get("common") or []:
        if isinstance(item, dict) and isinstance(item.get("nights"), int) and isinstance(item.get("sailings"), int):
            common.append((item["nights"], item["sailings"]))

    sailings = []
    for item in raw.get("lgbtq_sailings") or []:
        if not isinstance(item, dict):
            continue
        try:
            departs = dt.date.fromisoformat(str(item.get("departs")))
            returns = dt.date.fromisoformat(str(item.get("returns")))
        except ValueError:
            continue
        company, ship = item.get("company"), item.get("ship")
        if not (isinstance(company, str) and company.strip() and isinstance(ship, str) and ship.strip()):
            continue
        sailings.append({
            "company": company.strip(), "ship": ship.strip(),
            "ship_line": str(item.get("ship_line") or "").strip(),
            "departs": departs.isoformat(), "returns": returns.isoformat(),
            "from": str(item.get("from") or "").strip(),
        })

    # Country guidance: only entries whose source is a named Wikipedia article
    # are published, so every country on the page links to where it came from.
    safety = raw.get("criminalised_calls") if isinstance(raw.get("criminalised_calls"), dict) else {}
    countries = []
    for item in safety.get("countries") or []:
        if not isinstance(item, dict) or not isinstance(item.get("sailings"), int) or item["sailings"] <= 0:
            continue
        match = re.fullmatch(r"Wikipedia, (LGBTQ rights in (.+?)) \(en\.wikipedia\.org\)\.?", str(item.get("source") or "").strip())
        if not match:
            continue
        try:
            reviewed = dt.date.fromisoformat(str(item.get("reviewed"))).isoformat()
        except ValueError:
            continue
        place = re.sub(r"^the ", "", match.group(2))
        countries.append({
            "name": place,
            "sailings": item["sailings"],
            "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(match.group(1).replace(" ", "_")),
            "reviewed": reviewed,
        })
    with_itinerary = safety.get("sailings_with_itinerary")
    flagged = safety.get("sailings")
    safe_ok = (isinstance(with_itinerary, int) and isinstance(flagged, int)
               and 0 < flagged <= with_itinerary and countries)

    return {
        "regions": [(REGION_LABELS.get(n, n), v) for n, v in counted("regions", "name", "sailings", 6)],
        "departure_ports": counted("departure_ports", "name", "sailings", 6),
        "ships": counted("ships", "name", "sailings", 20),
        "ports_of_call": [(n, v) for n, v in counted("ports_of_call", "name", "calls", 10) if not NOT_A_PORT.search(n)],
        "nights_common": common[:5],
        "nights_shortest": nights.get("shortest") if isinstance(nights.get("shortest"), int) else None,
        "nights_longest": nights.get("longest") if isinstance(nights.get("longest"), int) else None,
        "lgbtq_sailings": sailings[:24],
        "safety": {"sailings": flagged, "with_itinerary": with_itinerary, "countries": countries} if safe_ok else None,
    }


def date_range(start_iso: str, end_iso: str) -> str:
    start, end = dt.date.fromisoformat(start_iso), dt.date.fromisoformat(end_iso)
    if start.year != end.year:
        return f"{long_date(start)} to {long_date(end)}"
    if start.month != end.month:
        return f"{start.day} {MONTHS[start.month - 1]} to {long_date(end)}"
    return f"{start.day} to {long_date(end)}"


def bar_card(heading: str, rows: list[tuple[str, int]], note: str = "") -> str:
    if len(rows) < 2:
        return ""
    top = max(value for _, value in rows)
    items = "".join(
        f'<li><span>{esc(name)}</span><span class="bar"><i style="width:{max(3, round(value / top * 100))}%"></i></span>'
        f'<span class="n">{number(value)}</span></li>'
        for name, value in rows
    )
    extra = f'<p class="cl-fact-note">{esc(note)}</p>' if note else ""
    return f'<div class="cl-fact-card"><h3>{esc(heading)}</h3><ul class="cl-bars">{items}</ul>{extra}</div>'


def facts_sections(row: dict, lines: list[dict]) -> str:
    """The parts of a line page that are about that line and no other."""
    facts = row.get("facts")
    if not facts:
        return ""
    safe = esc(row["name"])
    known = {line["name"]: slug(line["name"]) for line in lines}
    out = []

    # Bars mean little for a company with a handful of sailings; those get the list below.
    if row["upcoming_sailings"] >= 10:
        ships = facts["ships"]
        ship_note = f"And {len(ships) - 8} more." if len(ships) > 8 else ""
        nights = [(f"{n} night" + ("" if n == 1 else "s"), count) for n, count in facts["nights_common"]]
        nights_note = ""
        if facts["nights_shortest"] and facts["nights_longest"] and facts["nights_shortest"] != facts["nights_longest"]:
            nights_note = f"Shortest {facts['nights_shortest']} nights, longest {facts['nights_longest']}."
        cards = "".join(card for card in [
            bar_card("Where the sailings go", facts["regions"]),
            bar_card("Where they leave from", facts["departure_ports"]),
            bar_card("The ships", ships[:8], ship_note),
            bar_card("How long", nights, nights_note),
        ] if card)
        if cards:
            out.append(f"""    <section class="wrap cl-section">
      <h2>{safe} at a glance</h2>
      <p>Counted from the upcoming {safe} sailings in the app, so the figures move as sailings are added and depart.</p>
      <div class="cl-facts">{cards}</div>
    </section>""")

        ports = facts["ports_of_call"]
        if len(ports) >= 3:
            chips = "".join(f"<li>{esc(name)}<b>{number(calls)}</b></li>" for name, calls in ports)
            out.append(f"""    <section class="wrap cl-section">
      <h2>The ports you are most likely to call at</h2>
      <p>The number is how many upcoming {safe} sailings in the app call there.</p>
      <ul class="cl-chips">{chips}</ul>
    </section>""")


        safety = facts.get("safety")
        if safety:
            share = safety["sailings"] / safety["with_itinerary"] * 100
            percent = "Under 1%" if share < 1 else f"{round(share)}%"
            ranked = sorted(safety["countries"], key=lambda c: -c["sailings"])
            links = join_names([
                f'<a href="{esc(c["url"])}" rel="noopener">{esc(c["name"])}</a>'
                for c in ranked
            ])
            order_note = ", with the most visited first" if len(ranked) > 1 else ""
            link_note = "Each name links" if len(ranked) > 1 else "The name links"
            checked = long_date(max(dt.date.fromisoformat(c["reviewed"]) for c in safety["countries"]))
            country_word = "country is" if len(safety["countries"]) == 1 else "countries are"
            out.append(f"""    <section class="wrap cl-section">
      <h2>Ports where same-sex relationships are against the law</h2>
      <p>Some itineraries call at countries where same-sex relationships are a criminal offence or are prosecuted. We count them so you know before you book, not after.</p>
      <div class="cl-safety">
        <div class="cl-safety-figure"><strong>{percent}</strong><span>of upcoming {safe} sailings with an itinerary in the app call at one of these ports.</span></div>
        <div>
          <p>The {country_word} {links}{order_note}.</p>
          <p>{link_note} to the Wikipedia article our guidance is drawn from, last checked {checked}. Laws change, so read the article before you travel.</p>
          <p>This counts the itinerary. It says nothing about the policies of {safe} or how you are treated on board. In the app, every port on your sailing carries its own guidance.</p>
        </div>
      </div>
    </section>""")

    sailings = facts["lgbtq_sailings"]
    if sailings:
        cards = []
        for item in sailings:
            when = date_range(item["departs"], item["returns"])
            place = f" · from {esc(item['from'])}" if item["from"] else ""
            if row["is_charter_operator"]:
                line = item["ship_line"]
                on = (f'<a href="../{known[line]}/">{esc(line)}</a>' if line in known and line != row["name"]
                      else esc(line))
                title = esc(item["ship"]) + (f" <small>({on})</small>" if line and line != row["name"] else "")
            else:
                company = item["company"]
                title = (f'<a href="../{known[company]}/">{esc(company)}</a>' if company in known else esc(company))
                title += f" on {esc(item['ship'])}"
            cards.append(f'<li><span class="when">{when}{place}</span><strong>{title}</strong></li>')
        if row["is_charter_operator"]:
            heading = f"Upcoming {safe} sailings"
            intro = f"Every upcoming {safe} sailing in the app. Find yours and see who else is going."
        else:
            heading = f"Sailings run for LGBTQ+ travellers on {safe} ships"
            intro = (f"Some companies take a whole ship, or a group on one, for LGBTQ+ travellers. "
                     f"These are the ones on {safe} ships in the app.")
        out.append(f"""    <section class="wrap cl-section">
      <h2>{heading}</h2>
      <p>{intro}</p>
      <ul class="cl-sailings">{"".join(cards)}</ul>
    </section>""")

    return ("\n\n".join(out) + "\n\n") if out else ""


# ---------------------------------------------------------------- page shell

def shell(*, root: str, title: str, description: str, path: str, body: str,
          schema: list[dict], lines_href: str, robots: str = "index,follow") -> str:
    graph = json.dumps({"@context": "https://schema.org", "@graph": schema},
                       ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{esc(title)} | Out There Together</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{SITE}/{path}">
  <meta name="theme-color" content="#090B24">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Out There Together">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{SITE}/{path}">
  <meta property="og:image" content="{SITE}/og-image.png?v=20261026-3">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{SITE}/og-image.png?v=20261026-3">
  <script type="application/ld+json">
{graph}
  </script>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/assets/brand/favicon-32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{root}assets/homepage.css?v=20261125-3">
  <link rel="stylesheet" href="{root}assets/cruise-lines.css?v={CSS_VERSION}">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <svg class="icon-definitions" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <symbol id="icon-apple" viewBox="0 0 24 24"><path d="M16.4 12.7c0-2.5 2-3.6 2.1-3.7-1.2-1.7-3-1.9-3.6-2-1.5-.2-3 .9-3.8.9-.8 0-2-.9-3.3-.9-1.7 0-3.2 1-4.1 2.5-1.8 3.1-.5 7.6 1.3 10.1.9 1.2 1.9 2.6 3.2 2.5 1.3-.1 1.8-.8 3.3-.8s2 .8 3.3.8c1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9-.1 0-2.9-1.1-2.9-4Zm-2.5-7.4c.7-.9 1.2-2 1.1-3.3-1 0-2.3.7-3 1.6-.7.8-1.3 2-1.1 3.2 1.1.1 2.3-.6 3-1.5Z"/></symbol>
    <symbol id="icon-play" viewBox="0 0 24 24"><path d="M5 3.5v17c0 .8.9 1.3 1.6.9l14-8.5c.6-.4.6-1.4 0-1.8l-14-8.5c-.7-.4-1.6.1-1.6.9Z"/></symbol>
    <symbol id="icon-globe" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9S14.5 18.3 12 21c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z"/></symbol>
    <symbol id="icon-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
  </svg>

  <header class="site-header">
    <nav class="wrap nav" aria-label="Main navigation">
      <a class="brand-link" href="{root}" aria-label="Out There Together home">
        <img class="brand-logo" src="{root}assets/brand/logo-full-180.png" alt="Out There Together" width="509" height="180">
      </a>
      <div class="nav-links"><a href="{root}#how-it-works">How it works</a><a href="{lines_href}">Cruise lines</a><a href="{root}#safety">Safety</a><a href="{root}#download">Download</a></div>
      <div class="nav-actions">
        <a class="text-link nav-signin" href="{WEB_APP}">Sign in</a>
        <a class="button button-small" href="{PLAY}"><span class="cta-wide">Get it on Google Play</span><span class="cta-compact">Google Play</span></a>
        <a class="button button-small button-apple" href="{APPLE}"><span class="cta-wide">Download on the App Store</span><span class="cta-compact">App Store</span></a>
      </div>
    </nav>
  </header>

  <main id="main">
{body}
  </main>

  <footer class="wrap site-footer">
    <div class="footer-top">
      <div>
        <a class="brand-link" href="{root}" aria-label="Out There Together home"><img class="brand-logo" src="{root}assets/brand/logo-full-180.png" alt="Out There Together" width="509" height="180" loading="lazy"></a>
        <p>The LGBTQ+ cruise social app.</p>
      </div>
      <nav aria-label="Footer navigation"><a href="{WEB_APP}">Sign in</a><a href="{lines_href}">Cruise lines</a><a href="{root}privacy/">Privacy</a><a href="{root}terms/">Terms</a><a href="{root}cookies/">Cookies</a><a href="{root}affiliate-disclosure/">Affiliate disclosure</a><a href="{root}delete-account/">Delete your account</a><a href="mailto:hello@outtheretogether.com">Contact</a></nav>
    </div>
    <div class="footer-bottom"><span>© 2026 Out There Together. Operated by Blockbeam Ltd.</span><span>A social app, not a travel agent.</span></div>
  </footer>
  <script>function loadScript(callback){{var head=document.getElementsByTagName('head')[0],script=document.createElement('script');script.type='text/javascript';script.src='https://tracker.metricool.com/resources/be.js';script.onreadystatechange=callback;script.onload=callback;head.appendChild(script)}}loadScript(function(){{beTracker.t({{hash:'cc92ce15d015ab891d6dd799d8574ec9'}})}});</script>
</body>
</html>
"""


def faq_block(items: list[tuple[str, str]]) -> str:
    """items are (question, answer as HTML). The first one starts open."""
    rows = []
    for index, (question, answer) in enumerate(items):
        opened = " open" if index == 0 else ""
        rows.append(
            f'        <details{opened}><summary>{esc(question)}<svg class="icon" aria-hidden="true">'
            f'<use href="#icon-plus"/></svg></summary><p>{answer}</p></details>'
        )
    return (
        '    <section class="wrap faq" aria-labelledby="faq-heading">\n'
        '      <h2 id="faq-heading">Frequently asked questions</h2>\n'
        '      <div>\n' + "\n".join(rows) + '\n      </div>\n    </section>'
    )


def faq_schema(items: list[tuple[str, str]]) -> dict:
    plain = lambda text: html.unescape(re.sub(r"<[^>]+>", "", text))
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": question,
             "acceptedAnswer": {"@type": "Answer", "text": plain(answer)}}
            for question, answer in items
        ],
    }


def crumbs_schema(trail: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": position, "name": name, "item": f"{SITE}/{path}"}
            for position, (name, path) in enumerate(trail, start=1)
        ],
    }


def cta(heading: str) -> str:
    return f"""    <section class="wrap cl-cta">
      <h2>{esc(heading)}</h2>
      <p>Free on iPhone and Android, or in your browser.</p>
      <div class="store-buttons store-buttons-centre">
        <a class="store-button store-button-play" href="{PLAY}"><svg class="icon" aria-hidden="true"><use href="#icon-play"/></svg><span><small>Get it on</small>Google Play</span></a>
        <a class="store-button store-button-apple" href="{APPLE}"><svg class="icon" aria-hidden="true"><use href="#icon-apple"/></svg><span><small>Download on the</small>App Store</span></a>
        <a class="store-button store-button-web" href="{WEB_APP}"><svg class="icon" aria-hidden="true"><use href="#icon-globe"/></svg><span><small>Open in your</small>browser</span></a>
      </div>
    </section>"""


SELL_ANSWER = (
    "No. Out There Together is a social app, not a travel agent. When you are ready to book, "
    "we point you to the cruise line or an authorised agent, and some of those partners pay us "
    'a referral fee. Details are in our <a href="{root}affiliate-disclosure/">affiliate disclosure</a>.'
)


# ------------------------------------------------------------ shared pieces

def line_link(row: dict, prefix: str) -> str:
    return f'<a href="{prefix}{slug(row["name"])}/">{esc(row["name"])}</a>'


def robots_for(row: dict) -> str:
    """A page that can only say "nobody yet" stays out of search until a member joins.

    It is still built, linked and followed, so it is ready the day that changes.
    """
    return "index,follow" if row["members"] else "noindex,follow"


def other_lines(row: dict, lines: list[dict]) -> str:
    links = "".join(f"<li>{line_link(other, '../')}</li>" for other in lines if other["name"] != row["name"])
    return f"""    <section class="wrap cl-section">
      <h2>Other cruise lines</h2>
      <ul class="cl-links">{links}</ul>
    </section>"""


# ------------------------------------------------------------------ the list

def table(rows: list[dict], first_heading: str, tag_charters: bool) -> str:
    out = [
        '      <table class="cl-table">',
        f'        <thead><tr><th>{first_heading}</th><th class="num">Members with a sailing shortlisted or booked</th>'
        '<th class="num hide-narrow">Upcoming sailings in the app</th></tr></thead>',
        '        <tbody>',
    ]
    for row in rows:
        tag = "<small>Runs sailings for LGBTQ+ travellers</small>" if tag_charters and row["is_charter_operator"] else ""
        count = f'<strong>{number(row["members"])}</strong>' if row["members"] else "Be the first"
        out.append(
            f'          <tr><td><a href="{slug(row["name"])}/">{esc(row["name"])}</a>{tag}</td>'
            f'<td class="num">{count}</td><td class="num hide-narrow">{number(row["upcoming_sailings"])}</td></tr>'
        )
    out += ['        </tbody>', '      </table>']
    return "\n".join(out)


def list_page(lines: list[dict], updated: dt.date) -> str:
    with_members = [row for row in lines if row["members"]]
    charters = [row for row in lines if row["is_charter_operator"]]
    waiting = [row for row in lines if not row["members"] and not row["is_charter_operator"]]
    top_mainstream = [row["name"] for row in with_members if not row["is_charter_operator"]][:3]
    charter_names = join_names([row["name"] for row in charters])

    following = f"The surest answer is the companies that run sailings for LGBTQ+ travellers: {esc(charter_names)}. "
    if top_mainstream:
        following += (
            "Among the mainstream lines, Out There Together members have most often shortlisted or booked sailings with "
            f"{esc(join_names(top_mainstream))}. "
        )
    following += "Our totals are still small, so treat them as an early signal."

    faqs = [
        ("Which cruise lines have a big LGBTQ+ following?", following),
        ("How do I find other LGBTQ+ people on my cruise?",
         "Find your sailing in the Out There Together app, then add it to your shortlist or mark it Booked. Verified members can "
         "see who else is on the same sailing, say hello in the sailing chat and plan meetups before anyone boards."),
        ("Do you sell cruises?", SELL_ANSWER.format(root="../")),
        ("Can anyone see that I am on a sailing?",
         "Not from this page. Only cruise line totals are public. Inside the app, you choose what is visible, "
         "and only verified members can see who is on a sailing."),
    ]

    waiting_section = ""
    if waiting:
        waiting_section = f"""
    <section class="wrap cl-section">
      <h2>Also in the app, waiting for a first member</h2>
      <p>{join_names([line_link(row, "") for row in waiting])}. If you are sailing with one of them, mark your sailing and you will be the first name others see.</p>
    </section>
"""

    body = f"""    <section class="wrap cl-hero">
      <p class="eyebrow">Cruise lines <span>·</span> Member totals</p>
      <h1>Which cruise lines are LGBTQ+ travellers sailing with?</h1>
      <p class="cl-lede">These are the cruise lines that Out There Together members have shortlisted or booked sailings with. The totals come straight from the app and refresh every day. No names, no profiles, just numbers.</p>
      <p class="cl-updated">Updated {long_date(updated)}</p>

      <div class="cl-stats">
        <div class="cl-stat cl-stat-lead"><strong>{len(with_members)}</strong><span>cruise lines with sailings members have shortlisted or booked</span></div>
        <div class="cl-stat"><strong>{len(lines)}</strong><span>cruise lines and charter companies in the app</span></div>
        <div class="cl-stat"><strong>{len(charters)}</strong><span>companies running sailings for LGBTQ+ travellers</span></div>
      </div>
    </section>

    <section class="wrap cl-section">
      <h2>Members by cruise line</h2>
      <p>Each member is counted once per cruise line, however many sailings they have joined with it.</p>
{table(with_members, "Cruise line", tag_charters=True)}
      <p class="cl-note"><strong>Read these as a start, not a census.</strong> Out There Together opened to the public in October 2026, so the totals are small and growing. They count members of the app, not every LGBTQ+ person on board, so the real numbers on any ship will be higher.</p>
    </section>

    <section class="wrap cl-section">
      <h2>Sailings run for LGBTQ+ travellers</h2>
      <p>Some companies charter a whole ship, or take a group on one, for LGBTQ+ travellers. If you want to be sure of the crowd, these are the place to start. All {len(charters)} are in the app.</p>
{table(charters, "Company", tag_charters=False)}
    </section>
{waiting_section}
    <section class="wrap cl-section">
      <h2>How we count</h2>
      <p>A member is counted for a cruise line when they have shortlisted or booked at least one upcoming sailing with that line. Sailings that have already returned are not counted. We publish the total for each cruise line and nothing else: never a name, a photo, a profile or the sailing someone is on. The <a href="../privacy/">privacy policy</a> explains this in full.</p>
    </section>

{faq_block(faqs)}

{cta("Add your sailing to the count.")}"""

    return shell(
        root="../",
        lines_href="./",
        title="Cruise lines LGBTQ+ travellers sail with",
        description="The cruise lines Out There Together members have shortlisted or booked sailings with, counted from the "
                    "app and refreshed every day. Totals only, never names.",
        path="cruise-lines/",
        body=body,
        schema=[faq_schema(faqs), crumbs_schema([("Home", ""), ("Cruise lines", "cruise-lines/")])],
    )


# ------------------------------------------------------- one cruise line page

def line_page(row: dict, lines: list[dict], updated: dt.date) -> str:
    name, safe = row["name"], esc(row["name"])
    count, date = row["members"], long_date(updated)
    charter = row["is_charter_operator"]
    top = max(line["members"] for line in lines)
    sole_top = count == top and count > 0 and sum(1 for line in lines if line["members"] == top) == 1
    sailing_word = "sailing" if row["upcoming_sailings"] == 1 else "sailings"
    ship_word = "ship" if row["ships"] == 1 else "ships"
    runs = f"{safe} runs sailings for LGBTQ+ travellers. " if charter else ""

    if count:
        lede = f"{runs}{members_phrase(count)} shortlisted or booked an upcoming {safe} sailing."
        if sole_top:
            lede += " That is the most of any cruise line in the app today."
        member_word = "member" if count == 1 else "members"
        lead_stat = (f'<div class="cl-stat cl-stat-lead"><strong>{number(count)}</strong>'
                     f'<span>{member_word} with {article(name)} {safe} sailing shortlisted or booked</span></div>')
        first_answer = (f"Yes. {members_phrase(count)} shortlisted or booked an upcoming {safe} sailing, "
                        f"as of {date}. That only counts members of the app, so the real number is higher.")
    else:
        lede = (f"{runs}No Out There Together member has marked an upcoming {safe} sailing yet. "
                "Mark yours and you will be the first name others see.")
        lead_stat = (f'<div class="cl-stat cl-stat-lead cl-stat-text"><strong>Be the first</strong>'
                     f'<span>to shortlist or book {article(name)} {safe} sailing</span></div>')
        first_answer = (f"No Out There Together member has marked an upcoming {safe} sailing yet, as of {date}. "
                        "That only reflects members of the app, which opened to the public in October 2026. "
                        f"It says nothing about who sails with {safe}.")

    first_question = (f"Who else is going on {name} sailings?" if charter
                      else f"Are there LGBTQ+ travellers on {name}?")
    if charter and count:
        first_answer = first_answer.removeprefix("Yes. ")

    faqs = [
        (first_question, first_answer),
        (f"How do I meet other LGBTQ+ travellers on {article(name)} {name} sailing?",
         f"Find your {safe} sailing in the Out There Together app, then add it to your shortlist or mark it Booked. Verified "
         "members can see who else is on the same sailing, say hello in the sailing chat and plan meetups before boarding."),
        (f"Can I book {article(name)} {name} sailing through Out There Together?", SELL_ANSWER.format(root="../../")),
        ("Does this page show who is on which sailing?",
         "No. Only the total for the cruise line is public. Names, photos, profiles and the sailing each person "
         "is on stay inside the app, where you choose what is visible."),
    ]

    body = f"""    <section class="wrap cl-hero">
      <p class="cl-crumbs"><a href="../">Cruise lines</a> / {safe}</p>
      <p class="eyebrow">{safe} <span>·</span> Member totals</p>
      <h1>LGBTQ+ travellers on {safe}</h1>
      <p class="cl-lede">{lede}</p>
      <p class="cl-updated">Updated {date}</p>

      <div class="cl-stats">
        {lead_stat}
        <div class="cl-stat"><strong>{number(row["upcoming_sailings"])}</strong><span>upcoming {safe} {sailing_word} in the app, to {month_year(row["last_departure"])}</span></div>
        <div class="cl-stat"><strong>{number(row["ships"])}</strong><span>{safe} {ship_word} you can search</span></div>
      </div>
    </section>

{facts_sections(row, lines)}    <section class="wrap cl-section">
      <h2>See who else is going on your {safe} sailing</h2>
      <div class="cl-steps">
        <article class="step"><h3>Find your sailing</h3><p>Search {safe} by ship, port and month. If yours is missing, add it.</p></article>
        <article class="step"><h3>Mark it</h3><p>Add it to your shortlist while you decide, or mark it Booked once you have. That is what adds you to the total on this page.</p></article>
        <article class="step"><h3>Meet your shipmates</h3><p>Verified members can see who else is on the sailing, join its chat and plan sailaway drinks or a day ashore.</p></article>
      </div>
    </section>

    <section class="wrap cl-section">
      <h2>What this number means</h2>
      <p>It counts members of Out There Together who have shortlisted or booked at least one upcoming {safe} sailing. Each person is counted once. It does not count every LGBTQ+ person sailing with {safe}, so the real number on board will be higher.</p>
      <p class="cl-note"><strong>We do not rate cruise lines.</strong> This page reports what our members are doing, not how welcoming a cruise line is. Out There Together opened to the public in October 2026, so the totals are small and growing. See <a href="../">every cruise line's total</a>.</p>
    </section>

{faq_block(faqs)}

{other_lines(row, lines)}

{cta(f"Sailing with {name}? Add yours.")}"""

    return shell(
        root="../../",
        lines_href="../",
        title=f"LGBTQ+ travellers on {name}",
        description=f"How many Out There Together members have shortlisted or booked {article(name)} {name} sailing, refreshed every "
                    "day, and how to see who else is going on your sailing.",
        path=f"cruise-lines/{slug(name)}/",
        robots=robots_for(row),
        body=body,
        schema=[faq_schema(faqs), crumbs_schema([
            ("Home", ""), ("Cruise lines", "cruise-lines/"), (name, f"cruise-lines/{slug(name)}/"),
        ])],
    )


def sitemap(lines: list[dict], updated: dt.date) -> str:
    """Static pages keep the date already in the sitemap; cruise line pages take the new one."""
    existing = {}
    current = ROOT / "sitemap.xml"
    if current.exists():
        for loc, lastmod in re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", current.read_text("utf-8")):
            existing[loc] = lastmod
    entries = []
    for page in STATIC_PAGES:
        loc = f"{SITE}/{page}"
        entries.append((loc, existing.get(loc, updated.isoformat())))
    entries.append((f"{SITE}/cruise-lines/", updated.isoformat()))
    for row in lines:
        if row["members"]:
            entries.append((f"{SITE}/cruise-lines/{slug(row['name'])}/", updated.isoformat()))
    rows = "\n".join(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>" for loc, lastmod in entries)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + '\n</urlset>\n')


def main() -> int:
    lines = fetch()
    snapshot_path = OUT / "totals.json"
    if snapshot_path.exists() and "--force" not in sys.argv:
        previous = json.loads(snapshot_path.read_text("utf-8"))
        if previous.get("cruise_lines") == lines:
            print("Figures unchanged; nothing written.")
            return 0

    today = dt.datetime.now(dt.timezone.utc).date()
    wanted = {slug(row["name"]) for row in lines}

    OUT.mkdir(exist_ok=True)
    # A cruise line that has left the feed loses its page, so no stale total stays public.
    for folder in OUT.iterdir():
        if folder.is_dir() and folder.name not in wanted:
            for item in folder.iterdir():
                item.unlink()
            folder.rmdir()

    (OUT / "index.html").write_text(list_page(lines, today), "utf-8", newline="\n")
    for row in lines:
        folder = OUT / slug(row["name"])
        folder.mkdir(exist_ok=True)
        (folder / "index.html").write_text(line_page(row, lines, today), "utf-8", newline="\n")
    (ROOT / "sitemap.xml").write_text(sitemap(lines, today), "utf-8", newline="\n")
    snapshot_path.write_text(
        json.dumps({"updated": today.isoformat(), "cruise_lines": lines}, indent=2, ensure_ascii=False) + "\n",
        "utf-8", newline="\n",
    )
    print(f"Wrote {len(lines)} cruise line pages, the list and the sitemap for {today.isoformat()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
