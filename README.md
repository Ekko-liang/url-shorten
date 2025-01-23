# URL Shortener

A simple and efficient URL shortener service built with Flask and deployed on Vercel.

## Features

- Create short URLs from long ones
- Copy shortened URLs to clipboard
- Automatic redirection to original URLs
- Clean and responsive UI

## Tech Stack

- Python 3.9+
- Flask
- SQLite (in-memory for Vercel)
- HTML/CSS/JavaScript

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Visit `http://localhost:5003` in your browser

## Deployment

This application is configured for deployment on Vercel. Simply push to the main branch and Vercel will automatically deploy the changes.
