# Use the official Playwright image which has all browsers and dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.44.0

# Set the working directory inside the container
WORKDIR /app

# Install build-time dependencies for PyAV and the C compiler
RUN apt-get update && apt-get install -y build-essential pkg-config python3-dev libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev

# Copy the requirements file into the container
COPY requirements.txt .

# Install our Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy our application code into the container
COPY ./app .

# Expose the port the app will run on
EXPOSE 8001

# The command to run when the container starts
# We use --host 0.0.0.0 to make it accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
