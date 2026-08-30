#!/usr/bin/env python3
"""
Tallinna Sadama kruiisigraafik -> iCalendar (.ics)

REEGLID:
- Näidatakse ainult laevu pikkusega >= MIN_LENGTH_M.
- Ühel kalendripäeval on maksimaalselt ÜKS sündmus.
- Kui samal päeval on mitu sobivat laeva, koondatakse need ühe sündmuse alla.
- Sündmuse kirjelduses on iga laeva nimi ning saabumise ja väljumise kellaaeg.
"""

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from config import (
    SOURCE_URL, MIN_LENGTH_M, CALENDAR_NAME, CALENDAR_DESCRIPTION,
    OUTPUT_FILE, TIMEZONE
)

TZ = ZoneInfo(TIMEZONE)

DATE_TIME_RE = re.compile(
    r"Saabumine\s+(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}).*?"
    r"Väljumine\s+(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}).*?"
    r"Saabumise sadam\s+(.+?)\s+Laeva nimi\s+(.+?)\s+Agent\s+(.+?)\s+Kai nr\s+(\S+)",
    re.S | re.I,
)

DETAIL_RE = re.compile(
    r"Lähtekoht\s+(.+?)\s+Sihtkoht\s+(.+?)\s+"
    r"Saabumise kuupäev\s+(\d{2}\.\d{2}\.\d{4})\s+"
    r"Saabumise aeg\s+(\d{2}:\d{2})\s+"
    r"Väljumise kuupäev\s+(\d{2}\.\d{2}\.\d{4})\s+"
    r"Väljumise aeg\s+(\d{2}:\d{2})\s+"
    r"Pikkus\s+(\d+(?:[,.]\d+)?)",
    re.S | re.I,
)


def clean(value: str) -> str:
    return " ".join(value.split())


def fetch_text() -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CruiseCalendarBot/2.0)"}
    response = requests.get(SOURCE_URL, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return clean(soup.get_text(" ", strip=True))


def parse_dt(date_s: str, time_s: str) -> datetime:
    return datetime.strptime(
        f"{date_s} {time_s}", "%d.%m.%Y %H:%M"
    ).replace(tzinfo=TZ)


def parse_ships(text: str):
    mains = list(DATE_TIME_RE.finditer(text))
    ships = []

    for i, main in enumerate(mains):
        start = main.end()
        end = mains[i + 1].start() if i + 1 < len(mains) else len(text)
        details_text = text[start:end]
        detail = DETAIL_RE.search(details_text)

        if not detail:
            length_match = re.search(
                r"Pikkus\s+(\d+(?:[,.]\d+)?)", details_text, re.I
            )
            if not length_match:
                continue
            length = float(length_match.group(1).replace(",", "."))
            origin = destination = ""
        else:
            length = float(detail.group(7).replace(",", "."))
            origin = clean(detail.group(1))
            destination = clean(detail.group(2))

        arrival_date, arrival_time, departure_date, departure_time, port, ship, agent, quay = main.groups()

        ships.append({
            "arrival": parse_dt(arrival_date, arrival_time),
            "departure": parse_dt(departure_date, departure_time),
            "port": clean(port),
            "ship": clean(ship),
            "agent": clean(agent),
            "quay": clean(quay),
            "length": length,
            "origin": origin,
            "destination": destination,
        })

    unique = {}
    for ship in ships:
        key = (ship["ship"], ship["arrival"], ship["departure"], ship["quay"])
        unique[key] = ship
    return list(unique.values())


def ics_escape(value: str) -> str:
    return (str(value)
            .replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n"))


def ics_dt(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")


def group_by_day(ships):
    """Koondab kõik samal saabumiskuupäeval olevad laevad üheks sündmuseks."""
    groups = defaultdict(list)
    for ship in ships:
        local_day = ship["arrival"].astimezone(TZ).date()
        groups[local_day].append(ship)
    return groups


def event_uid(day, ships):
    raw = "|".join(
        [str(day)] +
        sorted(f'{s["ship"]}:{s["arrival"].isoformat()}' for s in ships)
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24] + "@suured-laevad"


def make_event_summary(ships):
    names = [s["ship"] for s in sorted(ships, key=lambda x: x["arrival"])]
    if len(names) == 1:
        return f"🚢 {names[0]} Tallinnas"
    # Nimede näitamine pealkirjas teeb kalendri kiirelt loetavaks.
    return f"🚢 {len(names)} laeva Tallinnas: " + ", ".join(names)


def make_event_description(ships):
    lines = [f"Laevu sadamas: {len(ships)}", ""]
    for s in sorted(ships, key=lambda x: x["arrival"]):
        arr = s["arrival"].astimezone(TZ)
        dep = s["departure"].astimezone(TZ)
        lines.extend([
            f"🚢 {s['ship']}",
            f"   Saabub: {arr.strftime('%H:%M')}",
            f"   Väljub:  {dep.strftime('%H:%M')}",
            f"   Pikkus:  {s['length']:.2f} m",
            "",
        ])
    lines.extend(["Allikas:", SOURCE_URL])
    return "\n".join(lines)


def make_ics(ships):
    now = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Suured Laevad Tallinnas//ET",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(CALENDAR_NAME)}",
        f"X-WR-CALDESC:{ics_escape(CALENDAR_DESCRIPTION)}",
        "X-WR-TIMEZONE:Europe/Tallinn",
    ]

    groups = group_by_day(ships)

    for day in sorted(groups):
        day_ships = sorted(groups[day], key=lambda x: x["arrival"])

        # Üks sündmus päevas. Visuaalne kestus: esimese saabumisest
        # kuni viimase väljumiseni.
        start = min(s["arrival"] for s in day_ships)
        end = max(s["departure"] for s in day_ships)

        ports = sorted(set(s["port"] for s in day_ships))
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event_uid(day, day_ships)}",
            f"DTSTAMP:{now}",
            f"DTSTART:{ics_dt(start)}",
            f"DTEND:{ics_dt(end)}",
            f"SUMMARY:{ics_escape(make_event_summary(day_ships))}",
            f"DESCRIPTION:{ics_escape(make_event_description(day_ships))}",
            f"LOCATION:{ics_escape(', '.join(ports) + ', Tallinn')}",
            f"URL:{SOURCE_URL}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    print(f"Laen: {SOURCE_URL}")
    text = fetch_text()
    all_ships = parse_ships(text)
    selected = [s for s in all_ships if s["length"] >= MIN_LENGTH_M]

    output = Path(OUTPUT_FILE)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(make_ics(selected), encoding="utf-8")

    grouped = group_by_day(selected)
    print(f"Leitud kokku: {len(all_ships)} laevakülastust")
    print(f"Filtrile >= {MIN_LENGTH_M:.0f} m vastab: {len(selected)}")
    print(f"Kalendrisse luuakse: {len(grouped)} päevapõhist sündmust")
    for day, day_ships in sorted(grouped.items()):
        names = ", ".join(s["ship"] for s in day_ships)
        print(f" - {day.strftime('%d.%m.%Y')}: {names}")
    print(f"\nValmis: {output}")


if __name__ == "__main__":
    main()
