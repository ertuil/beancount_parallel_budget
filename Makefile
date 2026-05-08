.PHONY: example report budget-report fava

example:
	PYTHONPATH=. bean-report examples/main.beancount

report:
	PYTHONPATH=. bean-query examples/main.beancount \
	  "SELECT date, account, position WHERE account ~ 'Equity:Budget'"

budget-report:
	PYTHONPATH=. python3 report.py examples/main.beancount

fava:
	PYTHONPATH=. fava examples/main.beancount