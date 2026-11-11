# Capital journey variant

Use this reference when one investor, security, cap table, or ownership
position changes through entry, partial exits, transfers, dilution, financing
marks, or listing. The reader job is to reconstruct the complete economic path,
not merely remember a terminal multiple.

This is a `roadmap` variant, not a separate template name.

## 1. Build the event ledger first

Record every ownership or cash-changing event in chronological order:

| Field | Required meaning |
|---|---|
| Date | Legal close, registration, or disclosed transaction date |
| Event type | `BUY`, `SELL`, `TRANSFER`, `DILUTION`, `MARK`, or `IPO` |
| Instrument / quantity | Shares, registered capital, units, or other legal interest |
| Cash flow | Amount paid or received by the subject; use zero when none |
| Ownership | Percentage before and after the event when available |
| Company value | Disclosed or transaction-implied pre/post value, with method |
| Evidence | Source ID and exact location |
| Boundary | Tax, fees, lock-up, look-through, control, or attribution caveat |

Do not merge legally different quantities. Registered capital, shares, and
ownership percentage may describe the same event but are not interchangeable.

## 2. Classify economic meaning before drawing

- `BUY`: external cash leaves the subject and beneficial ownership increases.
- `SELL`: an external buyer pays consideration and beneficial ownership falls.
- `TRANSFER`: ownership moves between the subject and a related or controlled
  vehicle. Treat it as an exit only when the evidence shows an external economic
  realization; a nominal internal transfer is normally a carrier migration.
- `DILUTION`: financing reduces the percentage without a sale by the subject;
  cash goes to the company, not to the holder.
- `MARK`: a financing or secondary transaction supplies an observable value but
  does not itself create holder cash flow.
- `IPO`: the listing or issue price marks remaining shares; it is unrealized
  unless a separately disclosed sale occurs.

If beneficial ownership, control, or platform allocation is uncertain, label
the classification as an assumption and keep the alternative interpretation in
`source.md`.

## 3. Use a three-layer composition

1. **Valuation staircase** — one shared vertical scale for disclosed or implied
   company value. Use event dates across the horizontal sequence.
2. **Transaction lane** — align the holder's `BUY`, `SELL`, `TRANSFER`,
   `DILUTION`, and `IPO` events beneath the relevant valuation point. At every
   real exit show quantity sold, consideration, ownership before/after, and the
   exit-time company value.
3. **Return bridge** — reconcile initial outflow, realized external proceeds,
   remaining attributed value, and simple total value or multiple.

Use color for event type, not alternating decoration. Recommended semantics:
entry / internal migration = one warm color; external sale = one positive cash
color; financing / hold / mark = one neutral color.

Mark at least one decisive exit and one classification boundary with
`data-annotation`, `data-source-ref`, and direct visible copy. A styled label
without `data-annotation` does not satisfy the audit contract.

## 4. Calculation rules

Use only formulas supported by disclosed inputs:

```text
financing post-money value = investment amount / post-money ownership acquired
secondary implied value    = consideration / company fraction sold
remaining marked value     = remaining shares × observable price
look-through value         = vehicle value × attributable economic percentage
simple total value         = realized external proceeds + remaining marked value
gross multiple             = simple total value / initial invested cash
```

Label each result as disclosed, transaction-implied, or attributed. Never mix a
pre-money value, post-money value, and secondary-trade value on one unlabeled
series.

Use a log vertical scale when `maximum / minimum >= 100` and the smaller events
would otherwise collapse. State `log` beside the axis. If horizontal positions
represent event order rather than elapsed time, say so explicitly.

Do not calculate IRR unless all material dated cash flows are available. Do not
present a gross multiple as annualized return. Keep tax, fees, carry, platform
distribution terms, lock-up, and liquidity outside the main calculation unless
they are evidenced.

## 5. Completeness and release gate

Before rendering, verify:

- every disclosed external cash event appears once in the transaction lane;
- internal transfers and dilution are visibly separated from real exits;
- each real exit displays what was sold, cash received, and exit-time value;
- remaining value is visibly marked as unrealized or price-based;
- the return bridge reconciles arithmetically to the displayed total;
- look-through percentages identify their source and whether they are rounded;
- decisive callouts carry `data-annotation` and evidence IDs;
- the source ledger contains formulas, units, dates, and contrary interpretations.

At full size and thumbnail size, a reader should be able to point to the initial
buy, each real sale, each non-cash ownership change, and the remaining position
without reading the methodology note.
