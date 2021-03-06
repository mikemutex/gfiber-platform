INSTALL?=install
PREFIX=$(DESTDIR)/usr
BINDIR=$(PREFIX)/bin
LIBDIR=$(PREFIX)/waveguide
PYTHON?=python
GPYLINT=$(shell \
    if which gpylint >/dev/null; then \
      echo gpylint; \
    else \
      echo 'echo "(gpylint-missing)" >&2'; \
    fi \
)

all:

%.test: %_test.py
	$(PYTHON) $<

%.test: %_test.sh
	./$<

runtests: \
	$(patsubst %_test.py,%.test,$(wildcard *_test.py)) \
	$(patsubst %_test.sh,%.test,$(wildcard *_test.sh))

lint: $(filter-out options.py,$(wildcard *.py))
	$(GPYLINT) $^

test_only: all
	PYTHONPATH=..:$(PYTHONPATH) ./wvtest/wvtestrun $(MAKE) runtests

# Use a submake here, only because otherwise GNU make (3.81) will not print
# an error about 'test' itself failing if one of the two sub-targets fails.
# Without such output, 'lint' could fail long before test_only fails, and
# the test_only output could scroll off the top of the screen, leaving the
# misleading impression that everything tested successfully.
test: all
	$(MAKE) test_only lint

install:
	mkdir -p $(LIBDIR) $(BINDIR)
	$(INSTALL) -m 0644 $(filter-out %_test.py, $(wildcard *.py)) $(LIBDIR)/
	$(INSTALL) -m 0755 waveguide.py $(LIBDIR)/
	$(INSTALL) -m 0755 waveguide $(BINDIR)/

install-libs:
	@echo "No libs to install."

clean:
	rm -rf *~ .*~ *.pyc *.tmp */*~ fake/scanresults.*
