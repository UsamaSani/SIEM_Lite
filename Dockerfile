WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p results sample_data

ENTRYPOINT ["python", "src/siem_pipeline.py"]