# Monitoring and Logging Guide

## Overview

This guide covers monitoring and logging setup for the Medicine Inventory Tracker application.

## Monitoring Stack

### Prometheus Metrics

The application exposes metrics that can be scraped by Prometheus:

- **Backend metrics**: Request count, latency, error rates
- **Frontend metrics**: Page views, API call success rates
- **System metrics**: CPU, memory, pod restarts

### ServiceMonitor Configuration

ServiceMonitors are already configured in `k8s/servicemonitor.yaml`. These tell Prometheus how to scrape metrics from your services.
```bash
# Apply ServiceMonitors (requires Prometheus Operator)
kubectl apply -f k8s/servicemonitor.yaml

# Verify ServiceMonitors
kubectl get servicemonitor -n tom-wakhungu
```

### Access Prometheus (if installed on cluster)
```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090

# Open in browser
http://localhost:9090
```

### Useful Prometheus Queries
```promql
# Request rate by endpoint
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Pod restarts
kube_pod_container_status_restarts_total{namespace="tom-wakhungu"}

# Memory usage
container_memory_usage_bytes{namespace="tom-wakhungu"}

# CPU usage
rate(container_cpu_usage_seconds_total{namespace="tom-wakhungu"}[5m])
```

## Grafana Dashboards

### Access Grafana (if installed on cluster)
```bash
# Port-forward to Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Open in browser
http://localhost:3000
# Default credentials: admin / prom-operator
```

### Import Dashboard

1. Go to Dashboards → Import
2. Use Dashboard ID: `13770` (Kubernetes / Views / Pods)
3. Select Prometheus datasource
4. Click Import

### Custom Dashboard Queries

**Medicine Inventory Specific Metrics:**

- Total medicines in inventory
- Low stock alerts
- API response times
- Database connection status
- Failed requests

## Logging

### View Application Logs
```bash
# Backend logs
kubectl logs -n tom-wakhungu -l app=backend --tail=100 -f

# Frontend logs
kubectl logs -n tom-wakhungu -l app=frontend --tail=100 -f

# All pods logs
kubectl logs -n tom-wakhungu --all-containers=true --tail=50
```

### CloudWatch Logs (if EFK/Fluentd configured)

If the cluster has Fluentd configured to send logs to CloudWatch:

1. Go to AWS Console → CloudWatch → Log Groups
2. Find log group: `/aws/eks/innovation/tom-wakhungu`
3. Filter by:
   - Backend: `{ $.kubernetes.labels.app = "backend" }`
   - Frontend: `{ $.kubernetes.labels.app = "frontend" }`

### Log Queries
```bash
# Search for errors in backend
kubectl logs -n tom-wakhungu -l app=backend | grep -i error

# Search for specific API endpoint calls
kubectl logs -n tom-wakhungu -l app=backend | grep "/api/medicines"

# View last 5 minutes of logs
kubectl logs -n tom-wakhungu -l app=backend --since=5m

# Export logs to file
kubectl logs -n tom-wakhungu -l app=backend > backend-logs.txt
```## Alerting

### PrometheusRules for Alerts

Create alerts for critical conditions:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: medicine-inventory-alerts
  namespace: tom-wakhungu
spec:
  groups:
  - name: medicine-inventory
    interval: 30s
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5..",namespace="tom-wakhungu"}[5m]) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"
        description: "Error rate is above 5% for 5 minutes"
    
    - alert: PodDown
      expr: kube_pod_status_phase{namespace="tom-wakhungu",phase!="Running"} > 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Pod is down"
        description: "Pod {{ $labels.pod }} is not running"
    
    - alert: HighMemoryUsage
      expr: container_memory_usage_bytes{namespace="tom-wakhungu"} / container_spec_memory_limit_bytes{namespace="tom-wakhungu"} > 0.9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage"
        description: "Memory usage is above 90%"
```

## Health Checks

### Application Health Endpoints
```bash
# Frontend health
curl http://ELB-URL/tom-wakhungu/health

# Backend health  
curl http://ELB-URL/tom-wakhungu/api/health

# Check from within cluster
kubectl run curl-test --rm -it --image=curlimages/curl --restart=Never -- \
  curl http://backend.tom-wakhungu:8000/health
```

### Kubernetes Health Status
```bash
# Check pod health
kubectl get pods -n tom-wakhungu

# Check readiness/liveness probes
kubectl describe pod -n tom-wakhungu <pod-name> | grep -A 10 "Liveness\|Readiness"

# Check events for issues
kubectl get events -n tom-wakhungu --sort-by='.lastTimestamp'
```

## Performance Monitoring

### Resource Usage
```bash
# Current resource usage
kubectl top pods -n tom-wakhungu

# Watch resource usage
watch kubectl top pods -n tom-wakhungu

# Node resource usage
kubectl top nodes
```

### HPA Metrics
```bash
# Check HPA status
kubectl get hpa -n tom-wakhungu

# Describe HPA for detailed metrics
kubectl describe hpa backend-hpa -n tom-wakhungu

# Watch HPA in action
watch kubectl get hpa -n tom-wakhungu
```

## Troubleshooting Dashboard

Create a simple monitoring dashboard script:
```bash
#!/bin/bash
# monitor.sh - Simple monitoring dashboard

echo "=== Medicine Inventory Monitoring Dashboard ==="
echo ""
echo "Pods Status:"
kubectl get pods -n tom-wakhungu
echo ""
echo "HPA Status:"
kubectl get hpa -n tom-wakhungu
echo ""
echo "Resource Usage:"
kubectl top pods -n tom-wakhungu
echo ""
echo "Recent Events:"
kubectl get events -n tom-wakhungu --sort-by='.lastTimestamp' | tail -5
echo ""
echo "Service Endpoints:"
kubectl get endpoints -n tom-wakhungu
```

Make it executable:
```bash
chmod +x monitor.sh
./monitor.sh
```

## Best Practices

1. **Set up alerts** for critical metrics (pod restarts, high error rates)
2. **Monitor resource usage** to optimize requests/limits
3. **Track API latency** to identify performance issues
4. **Review logs regularly** for errors and warnings
5. **Use dashboards** for quick health checks
6. **Set up log aggregation** for easier debugging
7. **Monitor database connections** to prevent connection pool exhaustion

## Next Steps

- Set up Grafana dashboards for visualization
- Configure AlertManager for notifications (email, Slack)
- Implement distributed tracing with Jaeger
- Set up log aggregation with EFK stack
- Create custom metrics for business KPIs (low stock alerts, etc.)