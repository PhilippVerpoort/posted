# Define variables
R_DIR := R
PYTHON_POSTED_DIR := python/posted
R_DOC_SCRIPT := make_r_docs.R
PYTHON_DOC_SCRIPT := make_python_docs.py

# Get the list of R and Python posted files
R_FILES := $(shell find $(R_DIR) -type f -name '*.R')
PYTHON_POSTED_FILES := $(shell find $(PYTHON_POSTED_DIR) -type f)

# Set the default target to run both r_docs and python_docs
.PHONY: all
all: r_docs python_docs

# Define the targets
r_docs: $(R_FILES) $(PYTHON_POSTED_FILES)
	Rscript $(R_DOC_SCRIPT)

python_docs: $(R_FILES) $(PYTHON_POSTED_FILES)
	python $(PYTHON_DOC_SCRIPT)



# Clean target (optional)
.PHONY: clean
clean:
	rm -f $(R_DOC_SCRIPT) $(PYTHON_DOC_SCRIPT)


