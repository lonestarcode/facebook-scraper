from setuptools import setup, find_packages

setup(
    name="facebook-marketplace-scraper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Web Scraping
        "requests>=2.28.0",
        "selenium>=4.0.0",
        "beautifulsoup4>=4.11.0",
        "playwright>=1.30.0",
        "aiohttp>=3.8.0",
        
        # Database
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "asyncpg>=0.27.0",
        "alembic>=1.9.0",
        
        # API Framework
        "fastapi>=0.95.0",
        "uvicorn>=0.21.0",
        "pydantic>=1.10.0",
        
        # Monitoring & Metrics
        "prometheus-client>=0.16.0",
        "grafana-api>=1.0.0",
        
        # Machine Learning
        "transformers>=4.27.0",
        "torch>=2.0.0",
        
        # Utilities
        "pyyaml>=6.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        'dev': [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "bandit>=1.7.0",
            "safety>=2.3.0",
        ]
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="An intelligent Facebook Marketplace scraper with anti-detection measures",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="facebook, scraper, marketplace, anti-detection, machine-learning",
    url="https://github.com/yourusername/facebook-marketplace-scraper",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.10",
) 