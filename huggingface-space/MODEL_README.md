---
license: apache-2.0
tags:
- hvac
- fastapi
- agents
pipeline_tag: other
---

# HVAC agents API

FastAPI backend and **O1–O20** supervisory agents (simulation BMS, writes disabled). **No frontend.**

The Next.js Control Center is deployed on **Vercel**.

## Run locally

```bash
pip install -r backend/requirements.txt
set PYTHONPATH=.
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Hugging Face Docker Space (PRO required)

This repo includes a `Dockerfile` that serves uvicorn on port **7860**. Free Hugging Face accounts cannot host Docker Spaces (HTTP 402). After [PRO](https://huggingface.co/pro):

```bash
python scripts/sync_hf_space.py --space
```

Then set Vercel env:

- `HVAC_API_ORIGIN=https://<you>-hvac-api.hf.space`
- `NEXT_PUBLIC_API_URL=https://<you>-hvac-api.hf.space/api`
