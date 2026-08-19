.PHONY: test verify demo graph vault clean

test:
	python3 -m unittest discover -s tests -v

verify:
	python3 -m protoos.verify

demo:
	python3 demo.py

graph:
	python3 -m protoos.graph out/

vault:
	python3 -m protoos.vault vault.zip

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf out/ vault.zip *.egg-info build dist
