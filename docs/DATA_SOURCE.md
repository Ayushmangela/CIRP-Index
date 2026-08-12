# Data source — IBBI order listings

Read this before writing or changing any ingestion code.

## Endpoints

Primary listing:
`https://www.ibbi.gov.in/en/orders/nclt?page=N`

Same parser shape, add later:
`/en/orders/nclat`, `/en/orders/supreme-court`, `/en/orders/high-court`

Pagination is zero-indexed and runs past page 1400 on the NCLT listing.

## Table columns as published

| Column | Contains |
|---|---|
| Orders Date | e.g. `21 Jan, 2022` |
| Subject | Matter name and case number in one free-text string |
| Orders | PDF link, with file size in parentheses e.g. `(599.85 KB)` |
| Remarks | Outcome label, e.g. `Admitted`, `Liquidation`, `12a-withdrawn` |

**Fetch a page and inspect the actual HTML before writing the parser.** The
table shape above is what was observed, not a contract. IBBI can change it.

## Case number formats seen in Subject

```
CP(IB) No. 155/9/HDB/2020
IA(IBC)-66-2022 in CP(IB) No. 155-9-HDB-2020
CP(IBC)-24(KOB)-2021
IA(IBC)/170,171 & 172/KOB/2021 in IBA/43,44,45/KOB/2021
I.A. No. 4692 of 2021 in C.P. No. (IB)-1644 (PB)-2018
IB No. 3013-ND-2019
```

Separators vary between `/` and `-` for the same case. Bench codes appear as
`HDB`, `KOB`, `PB`, `MB`, `CHE`. An `X in Y` string means X is an application
inside parent case Y — that relationship drives case linking.

Always keep `subject_raw` untouched alongside the parsed fields.

## Remarks values observed

`Admitted`, `Liquidation`, `Dissolution`, `Cirp-withdrawn`, `12a-withdrawn`,
`Others`, `Appointment Of Rp In Pg Case`, `Others In Pg Case`

Casing is inconsistent in the source. Normalise for lookup, store the original
in `remarks_raw`. Anything not in the explicit mapping dictionary becomes
`outcome = 'unclassified'` and is logged. Never fuzzy-match an outcome.

## Access rules

- One request per 2 seconds, single connection, no parallelism
- `User-Agent: CIRPIndex/0.1 (research project; your-email@example.com)`
- Exponential backoff on 5xx, give up after 4 attempts and record the failure
- Never rotate IPs or user agents to work around throttling

## PDF handling

A meaningful minority of older orders are scanned images. Detection: average
extractable characters per page below 100 means `is_scanned = true`.

Scanned orders are **skipped, not OCR'd**, and counted. The percentage goes in
the README as a stated limitation. This is a deliberate scope decision — see
docs/decisions/0002-skip-scanned-orders.md.

Other failure modes to handle with distinct statuses: 404, timeout,
password-protected, zero-byte response, HTML error page served at a `.pdf` URL.

## Attribution and disclaimer

IBBI states that orders on its site are received from various sources, are not
authenticated by IBBI, and are not certified copies issued by judicial
authorities. This must appear in the UI footer on every page and in the README.
Do not describe any figure in this product as authoritative.

## Sources deliberately excluded

NSE and BSE terms prohibit systematic automated collection. MCA has no public
API, charges per document, and prohibits bulk scraping. eCourts uses captcha.
Indian Kanoon's API is metered and paid. None of these are to be added.
