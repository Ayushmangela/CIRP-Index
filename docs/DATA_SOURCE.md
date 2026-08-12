# Data source — IBBI order listings

Read this before writing or changing any ingestion code.

## Endpoints

Primary listing:
`https://www.ibbi.gov.in/en/orders/nclt?page=N`

Same parser shape, add later:
`/en/orders/nclat`, `/en/orders/supreme-court`, `/en/orders/high-court`

Pagination is zero-indexed and runs past page 1400 on the NCLT listing.

## Table columns as observed (confirmed live, 2026-08-12)

`table.reporttable` (also carries class `cols-4`), 4 `<td>` per row — the
`thead` shows 4 headers (Sr.No. / Orders Date / Subject / Orders Remarks) but
**Subject and the PDF link/size are one physical cell**, not two:

```html
<tr>
  <td>1</td>
  <td>10 Aug, 2026</td>
  <td>
    <a href=/uploads/order/e64505f4f94926ca0b6195615e432b25.pdf download>
      In the matter of TEERTH GOPICON LIMITED [CP (IB) 408(AHM)2025]&nbsp;
      <img src="/img/pdf.jpg" width="15">(693.09 KB)
    </a>
  </td>
  <td>Admission - Final Order</td>
</tr>
```

- `order_date` from td[1], format `DD Mon, YYYY` (e.g. `10 Aug, 2026`)
- `subject_raw` = the `<a>` text before the `<img>`, `&nbsp;` stripped
- `pdf_url` = `href` (relative), resolve against `https://ibbi.gov.in` — the
  `www.ibbi.gov.in` host 301-redirects there, fetch the canonical host directly
- `file_size_bytes` parsed from the trailing `(693.09 KB)` / `(1.2 MB)`
- `remarks_raw` = td[3] text

Pager reports total row/page counts live (`<p>Total Records : N</p>`, last
page link) — read each run, never hardcode.

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

Confirmed live (2026-08-12, ~80 rows across 4 pages) — **this list is wider
and messier than originally assumed, and is not exhaustive**:

`Admission - Final Order`, `ADMITTED`, `Appointment - Appointment of
Liquidator`, `APPOINTMENT OF RP IN PG CASE`, `Others` / `OTHERS`, `Rejected`,
`Dismissed`, `Dissolution`, `Approval of Resolution Plan`, `RESOLUTION PLAN`,
`Extension of CIRP Period`, `EXTENSION OF TIME (CIRP)`, `Closure-12A /
appeal/ review or settlement`, `CIRP-WITHDRAWN` / `CIPR-WITHDRAWN` (source
typo) / `CIRP Withdrawn` / `WITHDRAWN`, `Approval of Repayment Plan in PG
case`, `DISMISSAL OF APPLICATION IN PG CASE`, `Liquidation`.

Casing is inconsistent in the source (`ADMITTED` vs `Admitted` vs `Admission
- Final Order` all occur). Normalise (strip + lower-case) for lookup, store
the original in `remarks_raw`. Anything not in the explicit mapping
dictionary (`ingestion/ibbi_listing.py:OUTCOME_MAP`) becomes
`outcome = 'unclassified'` and is logged. Never fuzzy-match an outcome.

**Known taxonomy gap:** `Rejected` and `Dismissed` describe a real outcome
(application not admitted) that has no corresponding value in the `outcome`
enum. They currently map to `unclassified`, which is correct per rule 3 but
loses information. Whether to add a `rejected` enum value is a schema
decision — see `docs/SCHEMA.md` (not something to change without discussion,
since enum changes need a migration).

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
