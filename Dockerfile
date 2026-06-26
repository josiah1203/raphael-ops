# Build from ~/Projects:
#   docker build -f raphael-ops/Dockerfile .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY raphael-contracts /deps/raphael-contracts
RUN uv pip install --system /deps/raphael-contracts
COPY raphael-ops/pyproject.toml raphael-ops/README.md ./
COPY raphael-ops/src ./src
RUN python3 -c "import re; from pathlib import Path; p=Path('pyproject.toml'); p.write_text(re.sub(r'\n\[tool\.uv\.sources\][^\[]*','\n',p.read_text(),flags=re.S))"
RUN uv pip install --system -e .
ENV RAPHAEL_SERVICE_PORT=8103
EXPOSE 8103
CMD ["uvicorn", "raphael_ops.app:app", "--host", "0.0.0.0", "--port", "8103"]
