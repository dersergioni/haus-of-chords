PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
export SOURCE_DATE_EPOCH ?= $(shell git log -1 --format=%ct 2>/dev/null)   # the PDF's dates: the last commit's, so a build is reproducible

.PHONY: all pdf web audit preview serve

all: web audit

pdf:
	$(PY) src/build_en.py

web: pdf
	$(PY) src/build_site.py

audit:            # all three checks run; make fails if any of them finds a problem
	$(PY) src/audit_data.py; d=$$?; $(PY) src/audit_pdf.py; p=$$?; $(PY) src/audit_site.py; s=$$?; exit $$((d + p + s))

preview:
	$(PY) src/preview.py

serve:
	$(PY) -m http.server 8000 --bind 127.0.0.1 --directory dist/site
