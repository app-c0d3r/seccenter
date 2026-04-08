# n8n Workflow Storage

Version-controlled n8n workflow storage. Workflows are built manually in the n8n canvas and exported here for IaC.

## Export workflows from n8n

```bash
docker exec n8n-orchestrator n8n export:workflow --backup --output=/home/node/.n8n/workflows/
```

## Import workflows into n8n

```bash
docker exec n8n-orchestrator n8n import:workflow --input=/home/node/.n8n/workflows/
```

## Linux permission fix

If you get EACCES errors on Linux:

```bash
chown -R 1000:1000 ./infrastructure/n8n/workflows
```
