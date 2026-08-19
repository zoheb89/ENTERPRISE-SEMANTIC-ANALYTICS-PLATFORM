# Capgemini DataPrepAI — Production Deployment

## Streamlit Cloud

1. Push this repository to the approved private Git repository.
2. Create a Streamlit app with `app.py` as the entry point.
3. Add secrets in Streamlit Cloud → Manage app → Settings → Secrets.
4. Use the shared login block:

```toml
[DATAPREPAI_AUTH]
email = "cinvent@capgemini.com"
password = "REPLACE_WITH_NEW_SECRET"
role = "Admin"
name = "DataPrepAI Shared User"
```

5. Add the existing Databricks and Capgemini LLM secrets required by the environment.
6. Deploy.
7. Test the full workflow:
   Onboard → Data Preparation → Semantic AI Analysis → Semantic Intelligence → Business Model → QA → Publish → Analytics → AI/BI Dashboard → Ask AI / Genie.

## Security

The shared credential is server-side in Streamlit Secrets and is never committed to source code.
For enterprise production, use Entra ID/OIDC/SSO instead of a shared identity.

## Raw data

DataPrepAI accepts imperfect input and profiles it before semantic analysis. Preparation actions are deterministic and reviewable. Business-specific corrections still require human approval.
