.PHONY: example report

example:
	PYTHONPATH=. bean-report examples/main.beancount

report:
	PYTHONPATH=. bean-query examples/main.beancount \
	  "SELECT date, account, position WHERE account ~ 'Equity:Budget'"

fava:
	PYTHONPATH=. fava examples/main.beancount