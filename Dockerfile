FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-report.txt .
RUN python -m pip install --no-cache-dir -r requirements-report.txt
COPY scripts/setup_reports.py scripts/setup_reports.py
RUN python -c "import runpy; runpy.run_path('scripts/setup_reports.py')['install_compiler']()"
COPY src/osdagbridge/core/reports/ src/osdagbridge/core/reports/
COPY src/osdagbridge/core/utils/common.py src/osdagbridge/core/utils/common.py
COPY src/osdagbridge/core/utils/codes/irc6_2017.py src/osdagbridge/core/utils/codes/irc6_2017.py
COPY src/osdagbridge/core/utils/codes/irc5_2015.py src/osdagbridge/core/utils/codes/irc5_2015.py
COPY src/osdagbridge/core/utils/codes/keyfile.py src/osdagbridge/core/utils/codes/keyfile.py
COPY src/osdagbridge/core/boq/boq_generator.py src/osdagbridge/core/boq/boq_generator.py
COPY ["src/osdagbridge/core/data/ResourceFiles/vectors/Osdag Logo.png", "src/osdagbridge/core/data/ResourceFiles/vectors/Osdag Logo.png"]
COPY run_report.py .
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "run_report.py"]
CMD ["--demo", "--output", "/output"]
