FROM python:3.10-slim

WORKDIR /app

# Khuyên dùng Gunicorn thay vì Flask dev server để chịu tải tốt hơn
RUN pip install flask requests

COPY . .

EXPOSE 5000

CMD ["python", "mock_jmeter_app.py"]