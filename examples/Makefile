.PHONY: run report clean

run:
	cd .. && PYTHONPATH=. bean-report examples/main.beancount

report:
	cd .. && PYTHONPATH=. bean-query examples/main.beancount \
	  "SELECT date, account, position WHERE account ~ 'Equity:Budget'"

fava:
	cd .. && PYTHONPATH=. fava examples/main.beancount

clean:
	rm -f *.html *.csv