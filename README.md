(A workspace README was added by the assistant.)

Script: script/gpt_funding_crawler.py

Quick start

1. Create and activate a Python virtualenv, then install dependencies:

	pip install -r requirements.txt

2. Set your OpenAI API key (Windows PowerShell example):

	setx OPENAI_API_KEY "sk-..."

	Or for the current PowerShell session only:

	$env:OPENAI_API_KEY = "sk-..."

3. Run the crawler (example):

	python script/gpt_funding_crawler.py \
		 --start-url https://example.org/opportunities \
		 --allow-domain example.org \
		 --output-dir ./out \
		 --max-pages 200 \
		 --max-depth 3

Notes
- The crawler uses the OpenAI client if `OPENAI_API_KEY` is set. Without it the script uses simple keyword heuristics only.
- The script is intentionally standalone so you can try it without modifying the main project flow.
