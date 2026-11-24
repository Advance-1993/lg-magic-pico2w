# START HIER — klaarzetten voor GitHub

Deze map is een aparte, opgeschoonde publicatiekopie. Het publiceren hiervan
wijzigt de werkende installatie of de aangesloten Pico niet.

## Voor gebruikers van het project

Begin bij **README.md**. De volledige handleiding vanaf een lege Pico 2 W staat
in **docs/SETUP.md**. De documentatie is Engelstalig voor een internationaal publiek.

## Wat staat erin?

Broncode, twee nieuwe privacyvriendelijke firmwarebuilds, companion, tests,
bouwinstructies, licentieteksten en GitHub-templates. De hoofdversie is 0.25.
Privélogs, flashback-ups, pairinggegevens, TV-automatisering, lokale instellingen,
oude Git-geschiedenis, screenshots, ontwikkeltools en persoonlijke paden zijn
niet meegenomen. Bewaar je privé-werkmap apart; voeg daaruit niet alsnog alles toe.

## Eenmalig publiceren via de browser

1. Kies op GitHub een nieuwe repository, bijvoorbeeld `lg-magic-pico2w`.
2. Maak die leeg aan: geen automatisch README-, license- of gitignore-bestand;
   deze map bevat die al. Kies de zichtbaarheid bewust.
3. Gebruik de GitHub-uploadpagina in je bestaande browsersessie. Hiervoor is geen
   Git Credential Manager, OAuth-toestemming of nieuwe blijvende Git-aanmelding
   nodig. Zet in je account vooraf **Keep my email addresses private** aan zodat
   webcommits je no-reply-adres gebruiken. Controleer de commitmetadata achteraf.
4. Controleer de te publiceren bestanden. Publiceer nooit `backups/`, `logs/`,
   `_runtime/`, `.venv/`, credentials of andere lokale configuratie.
5. Sleep de inhoud van een schone publicatiemap naar de uploadpagina, inclusief
   `.github`, `.gitignore` en `.gitattributes`. Upload maximaal 100 bestanden per
   groep; splits zo nodig broncode/documentatie en tests. Behoud de submappen en
   voeg nooit een lokale `.git`-map toe. Kies **Commit changes** pas na controle.
   Maak daarna eventueel Release `v0.25` met de twee UF2's,
   SHA256SUMS.txt en de bijbehorende licentieteksten. Laat GitHub de bron-ZIP maken.
6. Controleer op GitHub of README, documentatielinks en verborgen templates werken.
   Actions is voorbereid; de cloudtest is pas na upload daadwerkelijk uitgevoerd.

Logins, tokens, account-e-mail en andere aanmeldgegevens horen nooit in deze map.

GitHub uploadinformatie: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository

## Belangrijke grenzen

Alleen Pico 2 W en MR25GA zijn praktisch getest. MR26GA is niet bewezen compatibel.
De bestaande upstreamlicenties blijven gelden; presenteer het volledige project
niet als uitsluitend MIT of zonder meer commercieel vrij te gebruiken.
De publieke UF2's zijn opnieuw gebouwd om lokale compilatiepaden te verwijderen;
deze exacte nieuwe bytes zijn niet op de aangesloten Pico geflasht.
Zie docs/VALIDATION.md voor de scheiding tussen praktijkbewijs en exportcontroles.
