# Deploy the backend on Oracle Cloud

This guide deploys the current sample API to an Oracle Cloud Infrastructure
(OCI) Compute VM with Ubuntu 24.04 LTS, Python, systemd, and Caddy. Run the Linux
commands over SSH on the VM unless a step says otherwise. Replace the repository
URL, IP address, and example hostname with your own values.

The deployment runs the existing fictional, in-memory fixtures. Restarting the
service recreates the fixtures. There is no database, extractor, notification
worker, Docker image, or automatic deployment pipeline in this starter.

## 1. Create the VM and configure networking

In the OCI Console, create a Compute instance in your tenancy's home region.
Choose an eligible Ubuntu 24.04 LTS image and an available `VM.Standard.A1.Flex`
shape; 1 OCPU and 6 GB RAM is a small starting configuration for this sample.
A1 uses Arm, so select a matching image. Save the SSH private key securely.
Use a public subnet, an internet gateway, a default route to that gateway,
and a public IPv4 address on the instance.

Review the Console cost estimate and your tenancy's remaining allocation before
creation. Oracle currently documents 1,500 A1 OCPU hours and 9,000 GB hours per
month (equivalent to 2 OCPUs and 12 GB RAM for Always Free tenancies), shared
across usage. Capacity can be unavailable and idle Always Free VMs may be
reclaimed. Check the [official Always Free limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
when provisioning; a free allocation is not an uptime guarantee.

Attach a network security group (NSG), or configure the subnet security list,
with these stateful ingress rules. Retain required platform networking rules.

| Destination TCP port | Source | Purpose |
| --- | --- | --- |
| 22 | Your administrator public IP, `/32` | SSH |
| 80 | `0.0.0.0/0` | HTTP redirect and certificate validation |
| 443 | `0.0.0.0/0` | Public HTTPS API |

Keep 8000 private to the VM. Allow outbound DNS and HTTPS for package downloads
and certificate issuance. A public DNS `A` record such as `api.example.com`
must resolve to the instance's public IP before enabling HTTPS. Only add an
`AAAA` record if IPv6 routing and corresponding firewall rules are configured.

OCI network rules and the Ubuntu guest firewall both need to permit the public
ports. Inspect the image's existing rules and preserve SSH and OCI platform
rules when adding persistent TCP 80/443 allowances. OCI Ubuntu images can have
iptables rules that make UFW-only changes ineffective; follow
[Oracle's Ubuntu networking guidance](https://blogs.oracle.com/developers/enabling-network-traffic-to-ubuntu-images-in-oracle-cloud-infrastructure).
See also [OCI security lists and NSGs](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm).

From your local PowerShell terminal, connect using the Ubuntu image's login user:

```powershell
ssh -i "C:\path\to\oci-private-key" ubuntu@YOUR_PUBLIC_IP
```

See [Oracle's Linux SSH instructions](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm)
if connection or private-key permissions fail.

## 2. Install the backend on the VM

Use a clone of the `backend` branch that includes the `backend/` directory layout.
Push the desired local commit before cloning or pulling it on the VM. For a
private repository, configure a read-only deploy key for the SSH login user.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv git curl openssl
sudo install -d -o "$USER" -g "$(id -gn)" /opt/sport-reporter
git clone --branch backend --single-branch YOUR_REPOSITORY_URL /opt/sport-reporter
cd /opt/sport-reporter/backend
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install .
sudo useradd --system --user-group --home-dir /opt/sport-reporter --shell /usr/sbin/nologin sport-reporter
```

Python must be 3.11 or newer. Keep `/opt/sport-reporter` and its parent directories
readable and traversable by the `sport-reporter` service account. The SSH login
user owns the checkout; the service account only needs read/execute access.

## 3. Store the API key outside Git

Create a root-readable environment file for systemd:

```bash
sudo install -d -m 700 /etc/sport-reporter
sudo install -m 600 /dev/null /etc/sport-reporter/backend.env
openssl rand -hex 32
sudoedit /etc/sport-reporter/backend.env
```

Copy the generated token into this line, replacing the placeholder:

```dotenv
SPORT_REPORTER_API_KEY=YOUR_GENERATED_TOKEN
```

Systemd reads this file and supplies the variable to the service. The application
itself does not load `.env` files. Store a copy of the token in your password
manager and configure API clients with it. No database URL or Oracle API key is
required by the current sample.

## 4. Run the API with systemd

Create `/etc/systemd/system/sport-reporter.service` using `sudoedit`:

```ini
[Unit]
Description=Sport Reporter sample backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=sport-reporter
Group=sport-reporter
WorkingDirectory=/opt/sport-reporter/backend
EnvironmentFile=/etc/sport-reporter/backend.env
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/sport-reporter/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict

[Install]
WantedBy=multi-user.target
```

Keep one worker while fixtures live in process memory. Bind to loopback and trust
forwarded headers only from the local proxy; see the
[Uvicorn settings](https://uvicorn.dev/settings/). Use the service without `--reload`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sport-reporter
sudo systemctl status sport-reporter --no-pager
curl --fail http://127.0.0.1:8000/health
```

The health response should be `{"status":"ok","data_source":"sample"}`.

## 5. Enable HTTPS with Caddy

Install Caddy using its [official Ubuntu package instructions](https://caddyserver.com/docs/install#debian-ubuntu-raspbian).
That package provides the `caddy` systemd service. Edit `/etc/caddy/Caddyfile`
with `sudoedit` and replace the hostname:

```caddyfile
api.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
```

Caddy obtains and renews the HTTPS certificate when DNS and ports 80/443 are
reachable. See the [official reverse proxy guide](https://caddyserver.com/docs/quick-starts/reverse-proxy).
Clients should use the HTTPS hostname for all authenticated requests.

## 6. Verify from outside the VM

Run these commands in a local Bash terminal. `read -s` avoids storing the token
in shell history; paste the same token you configured in the environment file.

```bash
curl --fail https://api.example.com/health
curl -i https://api.example.com/upcoming
read -r -s -p 'API token: ' SPORT_REPORTER_API_KEY
printf '\n'
curl --fail 'https://api.example.com/upcoming?leagues=lck,nba&hours=24' \
  -H "Authorization: Bearer $SPORT_REPORTER_API_KEY"
unset SPORT_REPORTER_API_KEY
```

Expect HTTP 200 for health, HTTP 401 for the unauthenticated match request, and
HTTP 200 with sample matches for the authenticated request. Interactive API docs
are available at `https://api.example.com/docs`; use **Authorize** with the token.

If the loopback health check works but public HTTPS fails, check DNS, public IP,
internet gateway routing, OCI ingress rules, the guest firewall, and Caddy logs.

```bash
sudo journalctl -u sport-reporter -n 100 --no-pager
sudo journalctl -u caddy -n 100 --no-pager
sudo ss -ltnp
```

A backend startup error about `SPORT_REPORTER_API_KEY` means the environment file
is missing the variable or contains an empty value. After editing it, restart
the backend service.

## 7. Update and operate

Deploy a reviewed commit from the `backend` branch using the SSH login user:

```bash
cd /opt/sport-reporter
git status --short
git rev-parse HEAD
```

Proceed with a clean checkout and record the current commit as the rollback
reference. Then update and restart; the service will briefly be unavailable:

```bash
git pull --ff-only origin backend
cd backend
.venv/bin/python -m pip install .
sudo systemctl restart sport-reporter
curl --fail http://127.0.0.1:8000/health
```

Repeat the external verification after updating. If the update fails, restore
the recorded commit with `git switch --detach PREVIOUS_COMMIT`, reinstall from
its `backend` directory, and restart. Before the next normal update, switch back
to `backend`. Dependency versions currently use ranges; exact environment
rollback also requires retaining the previous environment or a dependency lock.

For automated health monitoring, query the public `/health` endpoint. Keep the
SSH key and API token backed up outside the VM. Plan PostgreSQL persistence,
idempotent extractors, notification deduplication, database backups, and API rate
limits before relying on this starter for unattended real match notifications.
OCI hosting does not add these features to the application.

For future UAT, use a separate service, environment file, API token, loopback port
(for example 8001), and hostname. Once persistence exists, UAT also needs a
separate database. Keep production and UAT deployment checkouts separate.

Cloud and proxy references checked on 2026-10-21. Review the linked official
instructions when provisioning or changing the deployment.
