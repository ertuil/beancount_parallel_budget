"""Parallel Budget Plugin for Beancount — 平行记账 (单交易差额方案).

每个周期开头生成一笔交易，将 Balance 补/减到预算金额。
过往周期的余额自然归零。

Usage:
    plugin "parallel_budget"
    option "insert_pythonpath" "TRUE"

Budget:
    2026-01-01 custom "parallel_budget" "Life" "monthly" 9600 CNY
    2026-01-01 custom "parallel_budget" "Decoration" "once" 300000 CNY
"""

from beancount.core import data as bd
from beancount.core.amount import Amount
from beancount.core.data import Transaction, Posting, Open, Custom
import datetime, sys
from decimal import Decimal

__plugins__ = ['parallel_budget']


def parallel_budget(entries, options_map):
    errors = []
    defs = _parse(entries, errors)
    if not defs:
        return (entries, errors)

    _log(f"[平行记账] {len(defs)}个预算: {', '.join(defs)}")
    today = datetime.date.today()

    # 1. Tag expenses with budget legs
    tagged, mod = _tag(defs, entries)

    # 2. Generate ONE adjustment transaction per period
    adjust_txns = _adjust(defs, tagged, today)

    # 3. Merge
    all_entries = adjust_txns + tagged
    opens = _open_accts(all_entries)
    all_entries = opens + all_entries
    all_entries.sort(key=lambda e: getattr(e, 'date', datetime.date.min))

    _log(f"[平行记账] +{len(adjust_txns)}调整 ~{mod}标记")
    return (all_entries, errors)


def _parse(entries, errors):
    d = {}
    for e in entries:
        if isinstance(e, Custom) and e.type == "parallel_budget":
            try:
                v = e.values
                name = v[0].value.rsplit(':', 1)[-1] if ':' in v[0].value else v[0].value
                d[name] = {'period': v[1].value, 'amount': v[2].value, 'date': e.date}
            except Exception as ex:
                errors.append(bd.Error(e.meta, f"格式: {ex}"))
    return d


def _adjust(defs, tagged_entries, today):
    """Generate ONE adjustment transaction per period.

    Computes running Balance at period start, then adjusts to budget amount.
    """
    txns = []

    for name, cfg in defs.items():
        period, amt, start = cfg['period'], cfg['amount'], cfg['date']
        cur = amt.currency

        if period == 'once':
            dates = [start]
        elif period == 'monthly':
            dates = _month_starts(start, today)
        elif period == 'yearly':
            dates = _year_starts(start, today)
        elif period == 'daily':
            dates = _day_starts(start, today)
        else:
            continue

        # Chronological scan: recompute combined as we generate transactions
        running = Decimal('0')

        for d in dates:
            # Compute running balance BEFORE this date using ALL entries
            combined = sorted(tagged_entries + txns,
                              key=lambda e: getattr(e, 'date', datetime.date.min))
            running = Decimal('0')
            for e in combined:
                if not isinstance(e, Transaction) or e.date >= d:
                    continue
                for p in e.postings:
                    if p.account == f'Equity:Budget:Balance:{name}' and p.units:
                        running += p.units.number

            # Adjust: set Balance to budget amount
            adj = amt.number - running
            if abs(adj) < Decimal('0.001'):
                continue  # No adjustment needed

            txn = Transaction(
                meta=bd.new_metadata('', 0),
                date=d, flag='*', payee='', narration=f'预算-{name}',
                tags=frozenset(), links=frozenset(),
                postings=[
                    Posting(f'Equity:Budget:Balance:{name}',
                            Amount(adj, cur), None, None, None, None),
                    Posting(f'Equity:Budget:Income:{name}',
                            Amount(-adj, cur), None, None, None, None),
                ])
            txns.append(txn)
            running += adj  # now = amt.number

    return txns


def _month_starts(start, today):
    r = []
    cur = datetime.date(start.year, start.month, 1)
    end = datetime.date(today.year, today.month, 1)
    while cur <= end:
        r.append(cur)
        cur = _next_month(cur)
    return r


def _year_starts(start, today):
    r = []
    cur = datetime.date(start.year, 1, 1)
    while cur <= datetime.date(today.year, today.month, 1):
        r.append(cur)
        cur = datetime.date(cur.year + 1, 1, 1)
    return r


def _day_starts(start, today):
    r = []
    cur = start
    while cur <= today:
        r.append(cur)
        cur += datetime.timedelta(days=1)
    return r


def _next_month(d):
    if d.month == 12:
        return datetime.date(d.year + 1, 1, 1)
    return datetime.date(d.year, d.month + 1, 1)


def _tag(defs, entries):
    """Add Equity:Budget:Expenses/Balance legs to expense transactions."""
    pref = {}
    earliest = None
    for n, c in defs.items():
        pref[f'Expenses:{n}'] = n
        if earliest is None or c['date'] < earliest:
            earliest = c['date']

    result = []
    mod = 0
    for e in entries:
        if not isinstance(e, Transaction) or e.date < earliest:
            result.append(e)
            continue
        if any(p.account.startswith('Equity:Budget:') for p in e.postings):
            result.append(e)
            continue

        totals = {}
        new_ps = []
        for p in e.postings:
            new_ps.append(p)
            for prefix, bname in pref.items():
                if p.account == prefix or p.account.startswith(prefix + ':'):
                    totals[bname] = totals.get(bname, 0) + (
                        p.units.number if p.units else 0)
                    break

        if not totals:
            result.append(e)
            continue

        for bname, total in totals.items():
            if abs(total) < Decimal('0.001'):
                continue
            new_ps.append(Posting(f'Equity:Budget:Expenses:{bname}',
                                  Amount(total, 'CNY'), None, None, None, None))
            new_ps.append(Posting(f'Equity:Budget:Balance:{bname}',
                                  Amount(-total, 'CNY'), None, None, None, None))

        result.append(e._replace(postings=new_ps))
        mod += 1
    return result, mod


def _open_accts(entries):
    existing = set()
    for e in entries:
        if isinstance(e, Open) and e.account.startswith('Equity:Budget:'):
            existing.add(e.account)
    needed = set()
    for e in entries:
        if isinstance(e, Transaction):
            for p in e.postings:
                if p.account.startswith('Equity:Budget:') and p.account not in existing:
                    needed.add(p.account)
    if not needed:
        return []
    meta = bd.new_metadata('', 0)
    return [Open(meta=meta, date=datetime.date.min, account=a,
                 currencies=None, booking=None) for a in sorted(needed)]


def _log(msg):
    print(msg, file=sys.stderr)