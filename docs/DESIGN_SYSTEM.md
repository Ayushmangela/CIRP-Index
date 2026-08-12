# Design system

A research instrument for lawyers, journalists and analysts. Closer to a court
record than to a SaaS dashboard. Dense, quiet, typographically serious.

## Tokens

```
--bg          #FAF9F6   warm off-white
--text        #1A1A1A
--muted       #6B6B66
--rule        #E3E1DA   1px hairlines
--accent      #1F3A5F   deep ink blue
```

Outcome colours:
```
admitted            #4A6FA5  slate blue
cirp_ongoing        #B8860B  amber
resolution_approved #2D5F3F  deep green
liquidation         #A0432B  rust red
dissolved           #7A7873  warm grey
withdrawn           #6B5B7B  muted lilac
unclassified        #9A9892
```

## Typography

Sans-serif grotesque for UI. Monospace for case numbers, dates and rupee
amounts — always. Rupee figures right-aligned and tabular.

## Forbidden

No gradients. No drop shadows. No rounded card stacks. No 3D. No illustrations.
No purple-blue tech gradient. Separate content with hairlines, not cards.

## Components

- **Status pill** — flat, 1px border in the outcome colour, transparent fill,
  small uppercase letter-spaced label
- **Field row** — label left in muted small caps, value right, hairline below,
  superscript source marker linking into the evidence panel
- **Evidence panel** — sticky right column, shows the quoted span highlighted
  in pale yellow with a page caption beneath

## Screens — exactly three

1. **Search results** — left filter sidebar (outcome with counts and colour
   squares, bench, section, year, amount range), dense table, active filter
   chips above, monospace pagination below
2. **Case detail** — header with debtor name, case number, metadata chips,
   outcome badge right-aligned; horizontal timeline of the case's orders;
   two-column body with fields left and evidence panel right
3. **Bench analytics** — four flat stat tiles, horizontal bar chart of median
   duration by bench, stacked area chart of outcome mix by year

Do not add a fourth screen.

## Mandatory footer

Small italic muted grey, every page:

> Orders are facilitation copies sourced from the public IBBI order listing and
> are not certified copies issued by any judicial authority. Verify against the
> original before relying on any figure.

## Accessibility

Outcome is never communicated by colour alone — the pill always carries text.
Minimum 4.5:1 contrast on body text. Every interactive element keyboard
reachable, visible focus ring in the accent colour.
