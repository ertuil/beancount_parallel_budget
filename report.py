#!/usr/bin/env python3
"""
parallel_budget CLI 报表 — 在终端里直接看预算执行情况。

用法:
    python3 report.py path/to/main.beancount

依赖: 需要 beancount (pip install beancount)
      需要将 parallel_budget.py 所在目录加入 PYTHONPATH

输出:
    ┌──────────────────────────────────────────────────────────┐
    │  📊 预算执行报告                                          │
    ├──────────┬────────┬──────────┬──────────┬───────┬───────┤
    │  类别     │  预算    │  已支出    │  余额     │  使用率 │  周期  │
    ├──────────┼────────┼──────────┼──────────┼───────┼───────┤
    │  Food    │ 2000   │ 230.50   │ 1769.50  │ 11.5% │ mon   │
    │  Reno..  │ 20000  │ 780.00   │ 19220.00 │  3.9% │ once  │
    └──────────┴────────┴──────────┴──────────┴───────┴───────┘
"""

import sys
import os
from decimal import Decimal
from collections import defaultdict

try:
    from beancount.loader import load_file
    from beancount.core import account_types, data
except ImportError:
    print("❌ 需要安装 beancount: pip install beancount", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <beancount_file>")
        sys.exit(1)

    ledger_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(ledger_path):
        print(f"❌ 账本文件不存在: {ledger_path}", file=sys.stderr)
        sys.exit(1)

    entries, errors, options_map = load_file(ledger_path)
    if errors:
        for e in errors:
            print(f"⚠️  加载警告: {e.message}", file=sys.stderr)
        print()

    # 解析 budget 定义
    budgets = {}
    for e in entries:
        if isinstance(e, data.Custom) and e.type == "parallel_budget":
            try:
                v = e.values
                name = v[0].value.rsplit(':', 1)[-1] if ':' in v[0].value else v[0].value
                budgets[name] = {
                    'period': v[1].value,
                    'amount': v[2].value.number,
                    'currency': v[2].value.currency,
                }
            except Exception:
                pass

    if not budgets:
        print("❌ 未找到 parallel_budget 定义。")
        return

    # 统计 Equity:Budget:* 余额
    balances = defaultdict(Decimal)
    expenses = defaultdict(Decimal)
    for e in entries:
        if isinstance(e, data.Transaction):
            for p in e.postings:
                acct = p.account
                if not p.units:
                    continue
                if acct.startswith('Equity:Budget:Balance:') and not acct.endswith(':Income'):
                    name = acct.rsplit(':', 1)[-1]
                    balances[name] += p.units.number
                if acct.startswith('Equity:Budget:Expenses:'):
                    name = acct.rsplit(':', 1)[-1]
                    expenses[name] += p.units.number

    # 输出报表
    _print_report(budgets, balances, expenses)


def _print_report(budgets, balances, expenses):
    max_name_len = max(len(n) for n in budgets) + 2
    max_name_len = max(max_name_len, len('类别'))
    width = max(
        max_name_len + 10 + 10 + 10 + 7 + 7 + 18,
        60
    )

    sep = f"├{'─' * (max_name_len+2)}┼{'─' * 10}┼{'─' * 10}┼{'─' * 10}┼{'─' * 7}┼{'─' * 7}┤"
    top = f"┌{'─' * (width-2)}┐"
    bot = f"└{'─' * (width-2)}┘"

    # 标题
    print()
    print(top)
    title = "📊  预算执行报告"
    print(f"│{title:^{width-2}}│")
    print(f"├{'─' * (max_name_len+2)}┬{'─' * 10}┬{'─' * 10}┬{'─' * 10}┬{'─' * 7}┬{'─' * 7}┤")

    # 表头
    header = (
        f"│ {'类别':^{max_name_len}} │ {'预算':>8} │ {'已支出':>8} │ {'余额':>8} │ {'使用率':>5} │ {'周期':>5} │"
    )
    print(header)
    print(f"├{'─' * (max_name_len+2)}┼{'─' * 10}┼{'─' * 10}┼{'─' * 10}┼{'─' * 7}┼{'─' * 7}┤")

    # 数据行
    total_budget = Decimal('0')
    total_expense = Decimal('0')
    total_balance = Decimal('0')

    for name in sorted(budgets.keys()):
        b = budgets[name]
        amt = b['amount']
        exp = expenses.get(name, Decimal('0'))
        bal = balances.get(name, Decimal('0'))

        total_budget += amt
        total_expense += exp
        total_balance += bal

        pct = (exp / amt * 100) if amt > 0 else Decimal('0')

        period_map = {'monthly': '月', 'yearly': '年', 'once': '一次', 'daily': '日'}
        period = period_map.get(b['period'], b['period'])

        display_name = name if len(name) <= max_name_len else name[:max_name_len-3] + '..'

        print(
            f"│ {display_name:<{max_name_len}} "
            f"│ {amt:>8,.0f} "
            f"│ {exp:>8,.0f} "
            f"│ {bal:>8,.0f} "
            f"│ {pct:>5.1f}% "
            f"│ {period:>5} │"
        )

    # 合计
    total_pct = (total_expense / total_budget * 100) if total_budget > 0 else Decimal('0')
    print(f"├{'─' * (max_name_len+2)}┼{'─' * 10}┼{'─' * 10}┼{'─' * 10}┼{'─' * 7}┼{'─' * 7}┤")
    print(
        f"│ {'合计':<{max_name_len}} "
        f"│ {total_budget:>8,.0f} "
        f"│ {total_expense:>8,.0f} "
        f"│ {total_balance:>8,.0f} "
        f"│ {total_pct:>5.1f}% "
        f"│ {'':>5} │"
    )
    print(bot)
    print()
    print("  💡 预算余额 = 周期初预算额 - 已累计支出（含跨周期累积）")
    print("  📅 每周期初自动充值，过往周期余额不归零")
    print()


if __name__ == '__main__':
    main()