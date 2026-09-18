.PHONY: install run test seed migrate revision concurrent clean

install:
	pip install -r requirements.txt

run:           ## Chạy server, mở http://localhost:8000/docs
	uvicorn app.main:app --reload --port 8000

test:          ## Chạy test; -rs để xem lý do skip
	pytest -rs

seed:          ## Nạp dữ liệu mẫu (viết scripts/seed.py trước)
	python -m scripts.seed

migrate:       ## Áp migration lên database
	alembic upgrade head

revision:      ## Sinh migration sau khi sửa model:  make revision m="them bang booking"
	alembic revision --autogenerate -m "$(m)"

concurrent:    ## Kiểm chứng chống overbooking (server phải đang chạy port 8000)
	python -m scripts.test_concurrent

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f *.db
