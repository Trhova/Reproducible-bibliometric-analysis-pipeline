PYTHONPATH=src
PYTHON=python3
CLI=$(PYTHON) -m ahr_bibliometrics.cli

.PHONY: fetch preprocess analyze figures all clean

fetch:
	PYTHONPATH=$(PYTHONPATH) $(CLI) fetch

preprocess:
	PYTHONPATH=$(PYTHONPATH) $(CLI) preprocess

analyze:
	PYTHONPATH=$(PYTHONPATH) $(CLI) analyze

figures:
	PYTHONPATH=$(PYTHONPATH) $(CLI) figures

all:
	PYTHONPATH=$(PYTHONPATH) $(CLI) all

clean:
	rm -f data/raw/*.jsonl.gz data/raw/*.csv
	rm -f data/processed/*.csv.gz data/processed/*.json
	rm -f output/tables/*.csv output/tables/*.json
	rm -f output/figures/* output/figure_methods/*
	touch output/figures/.gitkeep output/figure_methods/.gitkeep

