PARENT_DIR := $(abspath ..)

.PHONY: run report query clean

run:
	PYTHONPATH=$(PARENT_DIR) bean-report $(PARENT_DIR)/examples/main.beancount

report:
	PYTHONPATH=$(PARENT_DIR) bean-query $(PARENT_DIR)/examples/main.beancount \
	  "SELECT date, account, position WHERE account ~ 'Equity:Budget'"

fava:
	PYTHONPATH=$(PARENT_DIR) fava $(PARENT_DIR)/examples/main.beancount

clean:
	rm -f *.html *.csv