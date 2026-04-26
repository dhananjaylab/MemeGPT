# System Maintenance and Update Procedures

## Overview

This document outlines the procedures for maintaining MemeGPT in production, including regular maintenance tasks, updates, and troubleshooting.

## Table of Contents

- [Daily Maintenance](#daily-maintenance)
- [Weekly Maintenance](#weekly-maintenance)
- [Monthly Maintenance](#monthly-maintenance)
- [Database Maintenance](#database-maintenance)
- [Storage Maintenance](#storage-maintenance)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Troubleshooting](#troubleshooting)
- [Disaster Recovery](#disaster-recovery)

## Daily Maintenance

### Health Checks
```bash
# Check all services
docker-compose ps

# Backend health
curl http://localhost:8000/api/health

# Database connectivity
docker-compose exec postgres pg_isready -U memegpt

# Redis connectivity
docker-compose exec redis redis-cli PING
```

### Log Review
```bash
# Check for errors
docker-compose logs --since 24h | grep -i error

# Watch live logs
docker-compose logs -f backend

# Archive logs
docker run --rm -v memegpt_logs:/logs \
  busybox tar czf /logs/archive-$(date +%Y%m%d).tar.gz
```

### Performance Monitoring
- CPU usage < 80%
- Memory usage < 85%
- Disk usage < 90%
- API response time < 500ms
- Error rate < 1%

## Weekly Maintenance

### Database Optimization
```sql
-- Vacuum (weekly)
VACUUM ANALYZE;

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Backup Verification
```bash
# Test backup restoration
docker-compose exec postgres pg_restore -C -d memegpt_test \
  < backup_latest.sql

# Verify R2 backup integrity
aws s3 ls s3://memegpt-images-prod/backups/ --recursive
```

### Security Updates
```bash
# Check for package updates
npm audit
pip check

# Update dependencies
npm update
pip install --upgrade -r requirements.txt
```

## Monthly Maintenance

### Full System Backup
```bash
# Create full backup
./scripts/deploy.sh production backup

# Verify backup
tar -tzf backups/full-backup-latest.tar.gz | head -20
```

### Database Cleanup
```sql
-- Delete old job records
DELETE FROM jobs 
WHERE created_at < NOW() - INTERVAL '90 days'
AND status IN ('completed', 'failed');

-- Delete old analytics
DELETE FROM analytics_events
WHERE timestamp < NOW() - INTERVAL '30 days';

-- Reindex all tables
REINDEX DATABASE memegpt;
```

### Storage Cleanup
```bash
# Remove old temporary files
find /app/output -type f -mtime +7 -delete

# Clean S3/R2 old uploads
aws s3 rm s3://memegpt-images-prod/temp/ --recursive
```

### Performance Tuning Review
- Review slow query logs
- Optimize N+1 queries
- Review cache hit rates
- Update database statistics

## Database Maintenance

### Connection Pool Monitoring
```python
# Check pool status
from backend.services.query_optimizer import DatabaseConnectionPoolOptimizer

diagnostics = DatabaseConnectionPoolOptimizer.get_diagnostics(engine)
print(f"Pool size: {diagnostics['pool_size']}")
print(f"Checked out: {diagnostics['checkedout']}")
```

### Query Performance Tuning
```bash
# Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

# Review slow queries
SELECT query, calls, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

### Replication and HA
- Monitor replication lag
- Test failover procedures
- Verify replica data consistency

## Storage Maintenance

### R2 Bucket Optimization
```python
# Analyze storage
from backend.services.r2_monitoring import R2MonitoringService

monitor = R2MonitoringService()
metrics = monitor.get_storage_metrics()
cost = monitor.estimate_monthly_cost(metrics)

print(f"Total size: {metrics.total_size_gb} GB")
print(f"Monthly cost: ${cost['total_estimated_monthly_cost']}")
```

### CDN Cache Invalidation
```bash
# Clear CloudFlare cache
curl -X POST \
  https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache \
  -H "X-Auth-Email: {email}" \
  -H "X-Auth-Key: {api_key}" \
  -d '{"files": ["/path/to/file.jpg"]}'
```

### Storage Growth Analysis
```sql
-- Analyze growth trends
SELECT
  DATE_TRUNC('month', created_at) as month,
  COUNT(*) as memes,
  SUM(file_size) as total_size
FROM memes
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC
LIMIT 12;
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Application Metrics**
   - Request rate (req/sec)
   - Error rate (errors/sec)
   - Response time (p50, p95, p99)
   - Active connections

2. **Database Metrics**
   - Query execution time
   - Connection pool usage
   - Replication lag
   - Table bloat

3. **Infrastructure Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network bandwidth

### Alert Rules
```yaml
# Critical alerts
- API error rate > 5%
- Database response time > 5 seconds
- Disk usage > 90%
- Memory usage > 95%

# Warning alerts
- API response time > 1 second
- Database query time > 500ms
- Disk usage > 85%
- Memory usage > 80%
```

### Notification Channels
- Slack integration
- Email alerts
- PagerDuty for critical
- SMS for severe outages

## Troubleshooting

### High Memory Usage
```bash
# Check memory usage
docker stats

# Memory by process
ps aux --sort=-%mem | head -10

# Redis memory usage
docker-compose exec redis redis-cli INFO memory
```

**Solutions:**
- Increase container limits
- Enable Redis eviction policy
- Clear old cache entries
- Restart services

### Slow Queries
```sql
-- Find slow queries
SELECT query, calls, mean_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC;

-- Get query plan
EXPLAIN ANALYZE SELECT ...;
```

**Solutions:**
- Add indexes
- Optimize query logic
- Use caching
- Implement pagination

### High API Response Time
```bash
# Check API logs
docker-compose logs -f backend | grep -i duration

# Monitor real-time
curl http://localhost:8000/metrics
```

**Solutions:**
- Check database performance
- Review rate limiting
- Check external API delays
- Increase worker concurrency

### Storage Issues
```bash
# Check disk usage
df -h

# Cleanup old files
find /app -type f -mtime +30 -delete

# Clean Docker
docker system prune -a
```

**Solutions:**
- Archive old data
- Remove temporary files
- Compress backups
- Implement retention policies

## Disaster Recovery

### Database Recovery
```bash
# Restore from backup
docker-compose exec postgres pg_restore -C -d memegpt \
  < backup_latest.sql

# Verify restoration
docker-compose exec postgres psql -U memegpt -d memegpt \
  -c "SELECT COUNT(*) FROM memes;"
```

### R2 Storage Recovery
```python
# Restore from R2 backup
from backend.services.r2_monitoring import R2BackupManager

manager = R2BackupManager()
manager.restore_from_backup("20240401_120000")
```

### System Restore Procedure
1. Stop all services
2. Backup current state
3. Restore database from latest backup
4. Restore R2 storage
5. Verify data integrity
6. Restart services
7. Run health checks
8. Monitor closely

### Recovery Time Objectives (RTO)
- Database: 30 minutes
- Storage: 1 hour
- Full system: 2 hours

### Recovery Point Objective (RPO)
- Database: 15 minutes (hourly backups)
- Storage: 24 hours (daily backups)
- Full system: 24 hours

## Update Procedures

### Dependency Updates
```bash
# Backend
pip install --upgrade -r backend/requirements.txt

# Frontend
cd frontend && npm update

# Docker images
docker-compose pull
```

### Application Updates
```bash
# Build new images
docker-compose build

# Deploy with zero downtime (blue-green)
./scripts/deploy.sh production deploy

# Verify deployment
curl http://localhost:8000/api/health
```

### Rollback Procedure
```bash
# If update fails
./scripts/deploy.sh production rollback

# Verify rollback
docker-compose ps
curl http://localhost:8000/api/health
```

## Documentation

### Maintenance Log
```bash
# Create maintenance log entry
echo "$(date): Performed database optimization" >> maintenance.log

# Archive logs monthly
tar czf maintenance-logs-$(date +%Y%m).tar.gz maintenance.log
```

### Runbook Template
```markdown
## [Incident Name]

### Symptoms
- Service is down
- High error rate
- Slow response times

### Diagnosis Steps
1. Check service status
2. Review logs
3. Check metrics

### Resolution Steps
1. ...
2. ...

### Prevention
- ...
```

## Maintenance Checklist

### Daily
- [ ] Service health checks
- [ ] Error log review
- [ ] Performance monitoring

### Weekly
- [ ] Database optimization
- [ ] Backup verification
- [ ] Security updates

### Monthly
- [ ] Full system backup
- [ ] Database cleanup
- [ ] Performance tuning
- [ ] Storage analysis

### Quarterly
- [ ] Full audit
- [ ] Disaster recovery drill
- [ ] Capacity planning
- [ ] Security review

## Emergency Contacts

- On-call: [phone/email]
- Database admin: [contact]
- DevOps lead: [contact]
- Management escalation: [contact]
