# Kubernetes Deployment

This guide explains how to deploy ocpp2mqtt on Kubernetes.

## Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Container registry access

## Deployment

### 1. Build and Push Image

```bash
docker build -t your-registry/ocpp2mqtt:latest .
docker push your-registry/ocpp2mqtt:latest
```

### 2. Create ConfigMap

Create a ConfigMap for your environment variables:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ocpp2mqtt-config
  namespace: default
data:
  MQTT_PORT: "1883"
  MQTT_HOSTNAME: "mqtt-broker.default.svc.cluster.local"
  MQTT_BASEPATH: "ocpp/"
  MQTT_USESTATIONNAME: "true"
  MQTT_TRANSPORT: "tcp"
  MQTT_KEEPALIVE: "60"
  MQTT_TIMEOUT: "30"
  MQTT_RECONNECT_BASE_DELAY: "5"
  MQTT_RECONNECT_MAX_DELAY: "60"
  LISTEN_PORT: "3000"
  LISTEN_ADDR: "0.0.0.0"
  LOG_FILE: "/var/log/ocpp2mqtt/app.log"
```

### 3. Create Secret (Optional)

For MQTT authentication:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ocpp2mqtt-secret
  namespace: default
type: Opaque
stringData:
  MQTT_USERNAME: "your-username"
  MQTT_PASSWORD: "your-password"
  AUTHORIZED_TAG_ID_LIST: '["tag1","tag2"]'
```

### 4. Deploy Application

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocpp2mqtt
  namespace: default
  labels:
    app: ocpp2mqtt
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ocpp2mqtt
  template:
    metadata:
      labels:
        app: ocpp2mqtt
    spec:
      containers:
      - name: ocpp2mqtt
        image: your-registry/ocpp2mqtt:latest
        ports:
        - containerPort: 3000
          name: ocpp
        envFrom:
        - configMapRef:
            name: ocpp2mqtt-config
        - secretRef:
            name: ocpp2mqtt-secret
            optional: true
        volumeMounts:
        - name: logs
          mountPath: /var/log/ocpp2mqtt
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          tcpSocket:
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          tcpSocket:
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: ocpp2mqtt
  namespace: default
spec:
  selector:
    app: ocpp2mqtt
  ports:
  - port: 3000
    targetPort: 3000
    name: ocpp
  type: ClusterIP
```

### 5. Ingress Configuration (Optional)

For WebSocket support through an ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ocpp2mqtt-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"
spec:
  rules:
  - host: ocpp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ocpp2mqtt
            port:
              number: 3000
```

## Scaling Considerations

- Each charging station maintains a WebSocket connection, so session affinity is important
- Consider using `sessionAffinity: ClientIP` on the Service if scaling horizontally
- For HA setups, ensure `MQTT_CLIENT_ID` is unique per replica

## Monitoring

### View logs

```bash
kubectl logs -f deployment/ocpp2mqtt
```

### Check pod status

```bash
kubectl get pods -l app=ocpp2mqtt
```

## Troubleshooting

1. **Connection issues**: Verify the MQTT broker is reachable from within the cluster
2. **WebSocket timeouts**: Adjust ingress timeout annotations
3. **Memory issues**: Increase resource limits if handling many charge points
