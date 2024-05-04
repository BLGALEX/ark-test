run:
	python -m uvicorn schema:app --reload

fmt:
	ruff check -s --fix --exit-zero .

lint list_strict:
	mypy .
	ruff check .

lint_fix: fmt lint

migrate:
	python -m yoyo apply -vvv --batch --database "postgresql+psycopg://postgres:postgres@localhost:5432/books" ./migrations
