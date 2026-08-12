# Documentation workflow

This repository is maintained as a professional portfolio rather than a dump of completed exercises.

## As work progresses

1. Create or update the project README while technical decisions are fresh.
2. Keep credentials in a local `.env` file and provide only a safe `.env.example`.
3. Save useful screenshots under the project's `assets/` folder after checking them for tenant IDs, keys, email addresses, and other sensitive details.
4. Use small, meaningful commits that describe the outcome.
5. Record known platform or course issues instead of silently changing the result.

## Before publishing a project

- Confirm that the demonstration works or clearly record why it cannot currently run.
- Remove secrets, personal data, customer data, internal URLs, and private teaching materials.
- Check the Git history as well as the current files for exposed credentials.
- Identify copied or adapted starter code and link to its source and licence.
- Use synthetic or safely anonymised example data.
- Check that setup instructions work from a clean environment.
- Add screenshots and a concise architecture explanation.
- Review whether the project needs its own licence.

## Commit message examples

- `docs: add architecture for generative chat project`
- `feat: add streamed response handling`
- `fix: use project deployment name from environment`
- `security: replace endpoint values with placeholders`
