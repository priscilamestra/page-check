# Stage 21A — GitHub star link (optional)

A small GitHub star action is now part of **Tools**, after **Connection** and before
**Developer tools**. No login, GitHub API, token, or new dependency is required.

## Behavior

- **Development** (without a URL): a muted, disabled *Star on GitHub* preview
  is visible in the Tools popover.
- **Production** (without a URL): the action is hidden entirely.
- **With a valid public repository URL**: a subtle link opens the GitHub
  repository in a new tab. The visitor must click GitHub's own **Star** button.
- **Invalid URL**: the link is not rendered. Only HTTPS URLs in the form
  `https://github.com/OWNER/REPOSITORY` are accepted.
- It does **not** need the user's GitHub username separately: a repository URL
  contains both its owner and repository name. Do not use a profile-only URL.

## Configure locally (PowerShell)

When the public repository exists, before starting Streamlit:

```powershell
$env:PAGECHECK_GITHUB_REPO_URL="https://github.com/SEU_USUARIO/SEU_REPOSITORIO"
uv run streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

For a Render deployment, configure the same variable in the Streamlit
service's environment variables. No URL is hardcoded in source code.

## Test

```powershell
uv run pytest tests/unit/test_github_link_stage21a.py -v
uv run pytest -q
```

This incremental update does not change the storage architecture, audit engines,
SQLite/Neon selection, production security gate, or report presentation.
