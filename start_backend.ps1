$env:PYTHONPATH="src"
python -m uvicorn hackguard.api.main:app --reload
