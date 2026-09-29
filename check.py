import json, os, re, sys
import requests
from bs4 import BeautifulSoup

TOPIC = os.environ["NTFY_TOPIC"]
FACILITIES = {
    "豊洲みずべ": "https://koto-kosodate-portal.jp/mizube/general/refresh_cal_50.html",
    "有明みずべ": "https://koto-kosodate-portal.jp/mizube/general/refresh_cal_60.html",
}
STATE = "state.json"


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    slots = {}
    for h2 in soup.find_all("h2"):
        m = re.match(r"(\d{4})年(\d{1,2})月", h2.get_text(strip=True))
        table = h2.find_next("table") if m else None
        if not table:
            continue
        for td in table.find_all("td"):
            text = td.get_text(" ", strip=True)
            d = re.match(r"(\d+)", text)
            if not d:
                continue
            for ampm in ("AM", "PM"):
                v = re.search(ampm + r"\s*(\S+)", text)
                if v:
                    key = f"{m.group(1)}-{int(m.group(2)):02d}-{int(d.group(1)):02d} {ampm}"
                    slots[key] = v.group(1)
    return slots


old = json.load(open(STATE)) if os.path.exists(STATE) else {}
new, msgs = {}, []
for name, url in FACILITIES.items():
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    r.encoding = "utf-8"
    slots = parse(r.text)
    if not slots:
        sys.exit(f"{name}: カレンダーを読み取れませんでした")
    print(f"OK: {name} {len(slots)}枠を読み取り")
    for key, v in slots.items():
        k = f"{name} {key}"
        avail = (v.isdigit() and int(v) > 0) or "抽" in v
        new[k] = avail
        if avail and not old.get(k, False):
            msgs.append(f"{name} {key} (残り{v})")

if msgs:
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data="\n".join(msgs).encode("utf-8"),
        headers={"Title": "Hitotoki hoiku: opening found",
                 "Click": "https://koto-kosodate-portal.jp/mizube/refresh/index.html"},
        timeout=30,
    )
json.dump(new, open(STATE, "w"), ensure_ascii=False)
