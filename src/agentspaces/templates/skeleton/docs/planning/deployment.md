---
name: deployment
description: Read when deploying or troubleshooting environments. Setup, configuration, verification.
category: operational
when_to_use:
  - Deploying the application for the first time
  - Setting up a new environment
  - Onboarding ops team members
  - Troubleshooting deployment issues
dependencies:
  - architecture.md
variables:
  required:
    - project_name
  optional:
    - platforms
    - prerequisites
    - env_vars
    - deployment_steps
    - post_deployment_checklist
    - health_endpoints
    - monitoring_options
    - rollback_instructions
---

# Deployment Guide

How to deploy {{ project_name }} to production.

## Recommended Platforms

{% if platforms %}
| Platform | Free Tier | Notes |
|----------|-----------|-------|
{% for p in platforms %}
| {{ p.name }} | {{ p.free_tier }} | {{ p.notes }} |
{% endfor %}
{% else %}
| Platform | Free Tier | Notes |
|----------|-----------|-------|
| Railway | 500 hours/month | Simple, good DX |
| Render | 750 hours/month | Easy setup |
| Fly.io | 3 shared VMs | Global edge deployment |

Choose based on your requirements and preference.
{% endif %}

## Prerequisites

{% if prerequisites %}
{% for prereq in prerequisites %}
{{ loop.index }}. {{ prereq }}
{% endfor %}
{% else %}
1. GitHub repository with code
2. Platform account (Railway, Render, or Fly.io)
3. Environment variables ready (see below)
4. Domain name (optional)
{% endif %}

## Environment Variables

{% if env_vars %}
| Variable | Required | Description |
|----------|----------|-------------|
{% for var in env_vars %}
| `{{ var.name }}` | {{ "Yes" if var.required else "No" }} | {{ var.description }} |
{% endfor %}
{% else %}
| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Random string for cryptographic operations |
| `DATABASE_URL` | Yes | Database connection string |
| `ENVIRONMENT` | No | `development` or `production` |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
{% endif %}

## Deployment Steps

{% if deployment_steps %}
{% for platform, steps in deployment_steps.items() %}
### {{ platform }}

{% for step in steps %}
#### {{ loop.index }}. {{ step.title }}

{{ step.content }}

{% if step.code %}
```{{ step.code_lang | default("bash") }}
{{ step.code }}
```
{% endif %}
{% endfor %}

{% endfor %}
{% else %}
### Railway

#### 1. Connect Repository

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects Python

#### 2. Configure Environment

In Railway dashboard → Variables, add your environment variables.

#### 3. Configure Build

Create `railway.toml` if needed:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
```

#### 4. Add Persistent Storage

For SQLite or file storage:

1. Railway dashboard → Add Volume
2. Mount path: `/app/data`
3. Update app to use `/app/data` for storage

#### 5. Custom Domain (Optional)

1. Settings → Domains
2. Add custom domain
3. Configure DNS CNAME

### Render

#### 1. Create Web Service

1. Go to [render.com](https://render.com)
2. New → Web Service
3. Connect GitHub repository

#### 2. Configure Service

```yaml
# render.yaml
services:
  - type: web
    name: {{ project_name | lower | replace(" ", "-") }}
    env: python
    buildCommand: pip install -e .
    startCommand: uvicorn src.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: SECRET_KEY
        generateValue: true
```

#### 3. Add Persistent Disk

1. Service settings → Add Disk
2. Mount path: `/app/data`
3. Size: 1GB (adjust as needed)
{% endif %}

## Post-Deployment Checklist

{% if post_deployment_checklist %}
{% for item in post_deployment_checklist %}
- [ ] {{ item }}
{% endfor %}
{% else %}
- [ ] Health check endpoint responds: `GET /health`
- [ ] Application loads without errors
- [ ] Can perform core functionality
- [ ] Error tracking working (if configured)
- [ ] SSL certificate active
- [ ] Environment variables set correctly
{% endif %}

## Health Checks

{% if health_endpoints %}
```
{% for endpoint in health_endpoints %}
{{ endpoint.method }} {{ endpoint.path }}  → {{ endpoint.description }}
{% endfor %}
```
{% else %}
```
GET /health        → Basic liveness
GET /health/ready  → Dependencies OK
```
{% endif %}

## Monitoring

{% if monitoring_options %}
{% for option in monitoring_options %}
- {{ option }}
{% endfor %}
{% else %}
### Uptime Monitoring

Set up external monitoring (free options):
- UptimeRobot
- Checkly
- Better Uptime

Configure to check `/health` every 5 minutes.

### Error Tracking

- Sentry (recommended)
- LogRocket
- Rollbar
{% endif %}

## Scaling

For MVP scale (50-100 users), single instance is sufficient.

If needed:
1. Increase instance size before adding instances
2. Consider managed database if SQLite becomes bottleneck
3. Add caching layer for frequently accessed data

## Rollback

{% if rollback_instructions %}
{% for platform, instructions in rollback_instructions.items() %}
**{{ platform }}:**
{% for step in instructions %}
{{ loop.index }}. {{ step }}
{% endfor %}

{% endfor %}
{% else %}
If deployment fails:

**Railway:**
1. Deployments → Select previous successful deploy
2. Click "Redeploy"

**Render:**
1. Events → Find previous deploy
2. Click "Rollback"
{% endif %}

## Troubleshooting

### Application Won't Start

1. Check logs for error messages
2. Verify all environment variables are set
3. Ensure port binding uses `$PORT` environment variable
4. Check that dependencies are installed correctly

### Database Connection Issues

1. Verify `DATABASE_URL` is set correctly
2. Check if persistent storage is mounted
3. Ensure database file permissions are correct

### SSL Certificate Issues

1. Wait up to 24 hours for certificate provisioning
2. Verify DNS records are correct
3. Check platform-specific SSL settings
