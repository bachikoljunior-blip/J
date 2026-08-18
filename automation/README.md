# Hourly AGI prompt automation

The workflow `.github/workflows/hourly-agi-root-problem.yml` runs every hour at minute 53 and can also be started manually.

It sends `automation/PROMPT_JA.txt` to GitHub Copilot CLI without changing the prompt text. The agent receives an isolated snapshot of this repository, writes its work under an `artifacts/` directory, and the workflow records the complete run under `runs/<JST timestamp>_github_actions_<run id>/`.

The workflow uses `gpt-5.4` and the job-scoped `GITHUB_TOKEN` with `copilot-requests: write`. In a personally owned repository, Copilot usage is charged against the repository owner's Copilot entitlement. Disable the workflow from the Actions tab or remove its `schedule` trigger to stop hourly runs.
