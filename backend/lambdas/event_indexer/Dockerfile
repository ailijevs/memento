FROM public.ecr.aws/lambda/python:3.11

# Copy requirements first (better layer caching)
COPY lambdas/event_indexer/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy shared app code
COPY app app

# Copy handler
COPY lambdas/event_indexer/handler.py .

# Lambda entrypoint
CMD ["handler.handler"]