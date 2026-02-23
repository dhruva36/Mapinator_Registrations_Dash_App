# EJM Registrations Dashboard

Dashboard for tracking applicant registrations on EconJobMarket. Pulls data from the EJM API and plots cumulative registration curves by academic year (Jun-May).

Filters: degree type, primary field, country, university tier. You can also toggle between enrollment date and last login date to see different patterns.

Deployed on Render.

## Running locally

```
pip install -r requirements.txt
python registrations.py
```

Opens at localhost:8050.
