PYTHONPATH=src
PYTHON=python3
CLI=$(PYTHON) -m bibliometric_pipeline.cli

.PHONY: fetch preprocess analyze figures report all clean

fetch:
	PYTHONPATH=$(PYTHONPATH) $(CLI) fetch

preprocess:
	PYTHONPATH=$(PYTHONPATH) $(CLI) preprocess

analyze:
	PYTHONPATH=$(PYTHONPATH) $(CLI) analyze

figures:
	PYTHONPATH=$(PYTHONPATH) $(CLI) figures

report:
	PYTHONPATH=$(PYTHONPATH) $(CLI) report

all:
	PYTHONPATH=$(PYTHONPATH) $(CLI) all

clean:
	rm -f data/raw/*.jsonl.gz data/raw/*.csv
	rm -f data/processed/*.csv.gz data/processed/*.json
	rm -f output/tables/*.csv output/tables/*.json
	rm -f output/figures/* output/figure_methods/*
	rm -f output/reports/*
	touch output/figures/.gitkeep output/figure_methods/.gitkeep output/reports/.gitkeep
