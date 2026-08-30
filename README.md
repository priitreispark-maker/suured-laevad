# 🚢 Suured kruiisilaevad Tallinnas → iPhone kalender

Projekt loeb Tallinna Sadama kruiisigraafikut ja genereerib automaatselt `.ics` kalendri.

## Uued kalendrireeglid

- Näidatakse ainult laevu pikkusega **vähemalt 250 m**.
- **Samal päeval sadamas olevad laevad koondatakse üheks kalendrisündmuseks.**
- Sündmuse pealkirjas on laeva nimi või mitme laeva puhul kõik nimed.
- Sündmuse kirjelduses kuvatakse iga laeva kohta:
  - laeva nimi;
  - saabumise kellaaeg;
  - väljumise kellaaeg;
  - pikkus;

### Näide ühe laevaga

**🚢 SKY PRINCESS Tallinnas**

Kirjeldus:

    🚢 SKY PRINCESS
       Saabub: 08:00
       Väljub:  18:00
       Pikkus:  329.81 m

### Näide mitme laevaga samal päeval

**🚢 3 laeva Tallinnas: SKY PRINCESS, BRITANNIA, MSC MAGNIFICA**

Ühe sündmuse kirjelduses:

    🚢 SKY PRINCESS
       Saabub: 07:00
       Väljub:  17:00
       Pikkus: 329.81 m

    🚢 BRITANNIA
       Saabub: 08:00
       Väljub:  18:00
       Pikkus: 330.00 m

    🚢 MSC MAGNIFICA
       Saabub: 09:00
       Väljub:  19:00
       Pikkus: 293.80 m

## Käivitamine

```bash
pip install -r requirements.txt
python generate_calendar.py
```

Valmis kalender:

`docs/suured-laevad.ics`

## iPhone

Avalda `docs` kaust GitHub Pages'i kaudu ja lisa `.ics` URL iPhone'is
tellitud kalendriks.

## Automaatne uuendamine

GitHub Actions käivitab kalendri uuendamise kord kuus ning seda saab
Actions menüüst ka käsitsi käivitada.
