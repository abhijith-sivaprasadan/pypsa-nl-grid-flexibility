.PHONY: install run dashboard test clean

install:
	pip install -r requirements.txt
	pip install -e .

run:
	python -m pypsa_nl_grid_flexibility.run_all

dashboard:
	streamlit run src/pypsa_nl_grid_flexibility/dashboard_streamlit.py

test:
	pytest -q

clean:
	rm -rf outputs/figures/*.png outputs/tables/*.csv outputs/reports/*.md data/processed/*.csv
