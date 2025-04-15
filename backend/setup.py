from setuptools import setup, find_packages

setup(
    name="facebook-marketplace-scraper",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        # These are the core dependencies that will be installed
        # Service-specific dependencies are in each service's requirements.txt
        "pydantic>=2.0.0",
        "sqlalchemy>=2.0.0",
        "confluent-kafka>=2.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "prometheus-client>=0.16.0",
        "opentelemetry-api>=1.16.0",
        "opentelemetry-sdk>=1.16.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="Facebook Marketplace Scraper - Microservices Architecture",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="facebook, scraper, marketplace, microservices, kafka",
    url="https://github.com/yourusername/facebook-marketplace-scraper",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.10",
) 