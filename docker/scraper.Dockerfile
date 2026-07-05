FROM python:3.11-slim
WORKDIR /app
COPY scraping-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
COPY scraping-service/ .
CMD ["python", "-c", "from scraper import EcommerceScraper; print('Scraper ready')"]
