from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="Facebook Marketplace Scraper API",
    description="API for scraping and managing Facebook Marketplace listings",
    version="1.0.0"
)

app.include_router(router)
