# Medicine Inventory Tracker - Operations Runbook

## 🎯 Purpose

This runbook provides troubleshooting procedures and operational guidance for the Medicine Inventory Tracker application running on AWS EKS.

---

## 📋 Quick Reference

### Application Information
- **Namespace:** `tom-wakhungu`
- **EKS Cluster:** `innovation`
- **Region:** `eu-west-1`
- **Frontend URL:** `https://tom-wakhungu.capstone.company.com`

### Key Commands

```bash
# Connect to cluster
aws eks update-kubeconfig --region eu-west-1 --name innovation

# Check all resources
kubectl get all -n tom-wakhungu

# View logs
kubectl logs -n tom-wakhungu -l app=backend --tail=100
kubectl logs -n tom-wakhungu -l app=frontend --tail=100

# Check pod status
kubectl get pods -n tom-wakhungu
kubectl describe pod <pod-name> -n tom-wakhungu
```

---

## 🚨 Common Issues and Solutions

### Issue 1: Pod Stuck in CrashLoopBackOff

**Symptoms:**
```
NAME                        READY   STATUS             RESTARTS   AGE
backend-xxxxx-xxxxx         0/1     CrashLoopBackOff   5          10m
```

**Diagnosis Steps:**

1. Check pod logs:
```bash
kubectl logs -n tom-wakhungu backend-xxxxx-xxxxx
```

2. Check previous container logs:
```bash
kubectl logs -n tom-wakhungu backend-xxxxx-xxxxx --previous
```

3. Describe the pod:
```bash
kubectl describe pod -n tom-wakhungu backend-xxxxx-xxxxx
```

**Common Causes & Solutions:**

#### A. Database Connection Failure

**Error in logs:**
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check if database secret exists
kubectl get secret db-credentials -n tom-wakhungu

# Verify secret contents (base64 encoded)
kubectl get secret db-credentials -n tom-wakhungu -o yaml

# Recreate secret if needed
kubectl delete secret db-credentials -n tom-wakhungu
kubectl create secret generic db-credentials \
  --from-literal=host=<DB_HOST> \
  --from-literal=database=<DB_NAME> \
  --from-literal=username=<DB_USER> \
  --from-literal=password=<DB_PASSWORD> \
  --from-literal=port=<DB_PORT> \
  --namespace=tom-wakhungu

# Restart deployment
kubectl rollout restart deployment/backend -n tom-wakhungu
```

#### B. Image Pull Failure

**Error in pod description:**
```
Failed to pull image: authorization failed
```

**Solution:**
```bash
# Verify ECR repository exists
aws ecr describe-repositories --region eu-west-1 | grep tom-wakhungu

# Re-run CI/CD pipeline to push images
git commit --allow-empty -m "Trigger rebuild"
git push origin main
```

#### C. Insufficient Resources

**Error in pod description:**
```
0/3 nodes are available: 3 Insufficient cpu
```

**Solution:**
```bash
# Reduce resource requests in deployment
# Edit k8s/deployment-backend.yaml or k8s/deployment-frontend.yaml
# Lower the CPU/memory requests

# Apply changes
kubectl apply -f k8s/ -n tom-wakhungu
```

---

### Issue 2: Pod Stuck in Pending State

**Symptoms:**
```
NAME                        READY   STATUS    RESTARTS   AGE
frontend-xxxxx-xxxxx        0/1     Pending   0          5m
```

**Diagnosis:**
```bash
kubectl describe pod -n tom-wakhungu frontend-xxxxx-xxxxx
```

**Common Causes & Solutions:**

#### A. Node Resources Exhausted

**Error:** `0/3 nodes are available: 3 Insufficient memory`

**Solution:**
```bash
# Check node resources
kubectl top nodes

# Reduce resource requests
# Edit deployment files and lower requests/limits
kubectl apply -f k8s/deployment-frontend.yaml -n tom-wakhungu
```

#### B. ImagePullBackOff

**Solution:**
```bash
# Check if image exists in ECR
aws ecr describe-images \
  --repository-name tom-wakhungu/frontend \
  --region eu-west-1

# Trigger new build
git push origin main
```

---

### Issue 3: High Latency / Slow Response

**Symptoms:**
- Application responds slowly (>3 seconds)
- Timeouts on API calls

**Diagnosis:**

1. Check pod resource usage:
```bash
kubectl top pods -n tom-wakhungu
```

2. Check pod count:
```bash
kubectl get deployment -n tom-wakhungu
```

3. Check backend logs for errors:
```bash
kubectl logs -n tom-wakhungu -l app=backend --tail=100
```

**Solutions:**

#### A. Database Connection Pool Exhausted

**Solution:**
```bash
# Scale up backend replicas
kubectl scale deployment/backend --replicas=3 -n tom-wakhungu

# Monitor rollout
kubectl rollout status deployment/backend -n tom-wakhungu
```

#### B. Resource Limits Too Low

**Solution:**
```bash
# Increase resource limits in deployment files
# k8s/deployment-backend.yaml
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi

# Apply changes
kubectl apply -f k8s/deployment-backend.yaml -n tom-wakhungu
```

---

### Issue 4: Ingress Not Working / 404 Errors

**Symptoms:**
- Cannot access `https://tom-wakhungu.capstone.company.com`
- Getting 404 or 502 errors

**Diagnosis:**

1. Check ingress status:
```bash
kubectl get ingress -n tom-wakhungu
kubectl describe ingress medicine-inventory-ingress -n tom-wakhungu
```

2. Check if services exist:
```bash
kubectl get svc -n tom-wakhungu
```

3. Test service endpoints:
```bash
kubectl run -it --rm debug --image=busybox --restart=Never -n tom-wakhungu -- /bin/sh
# Inside the pod:
wget -O- http://frontend
wget -O- http://backend:8000/health
```

**Solutions:**

#### A. Ingress Not Created

```bash
# Apply ingress
kubectl apply -f k8s/ingress.yaml -n tom-wakhungu

# Verify
kubectl get ingress -n tom-wakhungu
```

#### B. Service Selector Mismatch

```bash
# Check if service selects correct pods
kubectl get endpoints -n tom-wakhungu

# If empty, check pod labels match service selector
kubectl get pods -n tom-wakhungu --show-labels
```

---

### Issue 5: Frontend Cannot Reach Backend

**Symptoms:**
- Frontend loads but shows "Error connecting to backend"
- Network errors in browser console

**Diagnosis:**

1. Check browser console (F12):
```
Failed to fetch: http://tom-wakhungu.capstone.company.com/api/medicines
```

2. Test backend directly:
```bash
curl https://tom-wakhungu.capstone.company.com/health
curl https://tom-wakhungu.capstone.company.com/api/medicines
```

**Solutions:**

#### A. CORS Configuration

Check backend logs for CORS errors. Backend already has CORS configured for all origins in `main.py`.

#### B. Ingress Path Configuration

Verify ingress routes both `/` and `/api`:
```bash
kubectl get ingress medicine-inventory-ingress -n tom-wakhungu -o yaml
```

Should see paths for both frontend and backend.

---

### Issue 6: Database Connection Issues

**Symptoms:**
- Backend logs show database connection errors
- API returns 500 errors

**Diagnosis:**

1. Check secret:
```bash
kubectl get secret db-credentials -n tom-wakhungu -o yaml
```

2. Decode and verify values:
```bash
kubectl get secret db-credentials -n tom-wakhungu -o jsonpath='{.data.host}' | base64 -d
```

3. Test database connection from pod:
```bash
kubectl exec -it deployment/backend -n tom-wakhungu -- /bin/sh
# Inside container:
python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', database='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD')"
```

**Solutions:**

#### A. Wrong Credentials

```bash
# Delete and recreate secret with correct values
kubectl delete secret db-credentials -n tom-wakhungu
kubectl create secret generic db-credentials \
  --from-literal=host=<CORRECT_HOST> \
  --from-literal=database=<CORRECT_DB> \
  --from-literal=username=<CORRECT_USER> \
  --from-literal=password=<CORRECT_PASSWORD> \
  --from-literal=port=<CORRECT_PORT> \
  --namespace=tom-wakhungu

# Restart backend
kubectl rollout restart deployment/backend -n tom-wakhungu
```

#### B. Database Not Initialized

Contact DevOps team to verify database exists and table schema is created.

---

## 📊 Monitoring Commands

### Check Application Health

```bash
# Overall status
kubectl get all -n tom-wakhungu

# Pod status with more details
kubectl get pods -n tom-wakhungu -o wide

# Resource usage
kubectl top pods -n tom-wakhungu

# Recent events
kubectl get events -n tom-wakhungu --sort-by='.lastTimestamp'
```

### View Logs

```bash
# Backend logs
kubectl logs -n tom-wakhungu -l app=backend --tail=100 -f

# Frontend logs
kubectl logs -n tom-wakhungu -l app=frontend --tail=100 -f

# All pods in namespace
kubectl logs -n tom-wakhungu --all-containers=true --tail=50
```

### Test Endpoints

```bash
# Health checks
curl https://tom-wakhungu.capstone.company.com/health

# API endpoints
curl https://tom-wakhungu.capstone.company.com/api/medicines
```

---

## 🔄 Deployment Procedures

### Rolling Update

```bash
# Update image tag in deployment
kubectl set image deployment/backend \
  backend=024848484634.dkr.ecr.eu-west-1.amazonaws.com/tom-wakhungu/backend:new-tag \
  -n tom-wakhungu

# Monitor rollout
kubectl rollout status deployment/backend -n tom-wakhungu

# Check history
kubectl rollout history deployment/backend -n tom-wakhungu
```

### Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/backend -n tom-wakhungu

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2 -n tom-wakhungu
```

### Scale Application

```bash
# Scale up
kubectl scale deployment/backend --replicas=4 -n tom-wakhungu

# Scale down
kubectl scale deployment/frontend --replicas=1 -n tom-wakhungu

# Verify
kubectl get deployment -n tom-wakhungu
```

---

## 🔧 Maintenance Tasks

### Restart All Pods

```bash
# Restart backend
kubectl rollout restart deployment/backend -n tom-wakhungu

# Restart frontend
kubectl rollout restart deployment/frontend -n tom-wakhungu

# Restart all
kubectl rollout restart deployment -n tom-wakhungu
```

### Update Configuration

```bash
# Apply changes from manifests
kubectl apply -f k8s/ -n tom-wakhungu

# Verify changes
kubectl get deployment -n tom-wakhungu -o yaml
```

### Clean Up Resources

```bash
# Delete all resources in namespace
kubectl delete all --all -n tom-wakhungu

# Delete namespace (WARNING: This deletes everything)
kubectl delete namespace tom-wakhungu
```

---

## 📞 Escalation

If issues persist after troubleshooting:

1. **Gather diagnostics:**
```bash
kubectl get all -n tom-wakhungu > diagnostics.txt
kubectl describe pods -n tom-wakhungu >> diagnostics.txt
kubectl logs -n tom-wakhungu --all-containers=true --tail=200 >> diagnostics.txt
```

2. **Contact DevOps Team:**
   - dan@tiberbu.com
   - njoroge@tiberbu.com
   - elvis@tiberbu.com

3. **Include in your message:**
   - Description of the issue
   - Steps already taken
   - Diagnostic output
   - Time when issue started

---

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)