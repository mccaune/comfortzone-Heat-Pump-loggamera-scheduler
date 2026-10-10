# Security guidance

- **Never commit `.env`** or passwords, API keys, session cookies, device IDs, or internal IP addresses. `.gitignore` helps but does not replace checking `git status` and `git diff --cached`.
- Keep `.env` readable by its owner only: `chmod 600 .env`.
- Use a dedicated non-root Linux user where practical; the sample runs as a normal user and does not need root privileges for HTTP access.
- Do not expose SSH or this machine directly to the public internet. Install OS security updates.
- Do not change code to bypass authentication or security checks.
- Assume the unofficial web endpoint can change without notice. Monitor failures and retain the ability to control heating manually.
- If a credential is accidentally committed, **rotate it immediately**; deleting it in a later commit does not remove it from repository history.
- Never upload full request dumps, cookies, credentials, or device identifiers into public GitHub issues.
