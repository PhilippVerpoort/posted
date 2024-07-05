# Define variables
PYTHON_POSTED_DIR := python/posted
R_DIR := R
PYTHON_DOC_SCRIPT := make_python_docs.py
R_DOC_SCRIPT := make_r_docs.R

# Get the list of R and Python posted files
PYTHON_POSTED_FILES := $(shell find $(PYTHON_POSTED_DIR) -type f -name '*.py')
R_FILES := $(shell find $(R_DIR) -type f -name '*.R')


# Set the default target to run both r_docs and python_docs
.PHONY: all
all: python_docs r_docs

# Define the targets
python_docs: $(R_FILES) $(PYTHON_POSTED_FILES)
	python $(PYTHON_DOC_SCRIPT)

r_docs: $(R_FILES) $(PYTHON_POSTED_FILES)
	Rscript $(R_DOC_SCRIPT)


# Clean target (optional)
.PHONY: clean
clean:
	rm -f $(R_DOC_SCRIPT) $(PYTHON_DOC_SCRIPT)
