# Use the official Playwright image which has browsers pre-installed
FROM mcr.microsoft.com/playwright/python:v1.44.0

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install our Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy our application code into the container
# Creates /app/app structure for proper module import
COPY ./app ./app

# Expose the port the app will run on
EXPOSE 8001

# The command to run when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
