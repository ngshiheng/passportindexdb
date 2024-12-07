PYTHON := $(shell command -v python 2> /dev/null)
DATASETTE := $(shell command -v datasette 2> /dev/null)

.DEFAULT_GOAL := help
##@ Helper
.PHONY: help
help:	## display this help message.
	@echo "Welcome to passportdb."
	@awk 'BEGIN {FS = ":.*##"; printf "Use make \033[36m<target>\033[0m where \033[36m<target>\033[0m is one of:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Usage
.PHONY: run
run:	## run scraper.
	@$(PYTHON) scrape.py

.PHONY: datasette
datasette:	## run datasette.
	@if [ -z $(DATASETTE) ]; then echo "Datasette could not be found. See https://docs.datasette.io/en/stable/installation.html"; exit 2; fi
	@$(DATASETTE) data/passport.db --metadata data/metadata.json
