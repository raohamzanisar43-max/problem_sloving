# Deployment

Production: https://novuradar.novulabs.net — Docker Compose in `/opt/novu-radar` behind the host nginx
(`deploy/novuradar.novulabs.net.conf`), TLS by certbot.

## CI/CD

`.github/workflows/ci-cd.yml` runs backend tests and the frontend build on every push/PR.
Pushes to `main` that pass then deploy over SSH and run a smoke test.

The deploy key on the server is restricted in `~/.ssh/authorized_keys` to a single command:

```
command="/usr/local/bin/novu-radar-deploy",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAA… github-actions-novu-radar
```

Repository secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (private key), `DEPLOY_KNOWN_HOSTS`.

Server setup (once): install `deploy/novu-radar-deploy.sh` to `/usr/local/bin/novu-radar-deploy` (mode 755) and make
`/opt/novu-radar` a git checkout of this repo. `.env` stays on the server and is git-ignored.
