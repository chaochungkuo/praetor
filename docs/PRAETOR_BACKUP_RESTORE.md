# Praetor Backup And Restore

Praetor's important state is in:

- `workspace/`
- `data/`
- `config/`

The current repo includes a simple backup script:

- [scripts/backup_praetor.sh](scripts/backup_praetor.sh)

## Create a backup

From the repo root:

```bash
bash scripts/backup_praetor.sh
```

This writes a timestamped archive under:

- `backups/`

## Restore

1. stop Praetor
2. unpack the archive into the repo root
3. restart Praetor

Example:

```bash
tar -xzf backups/praetor-backup-YYYYMMDD-HHMMSS.tar.gz -C .
```

## Notes

- back up before major model or runtime changes
- verify restore occasionally on a separate copy of the workspace
- for remote installs, copy the archive off-host as well
