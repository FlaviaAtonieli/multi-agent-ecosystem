#!/bin/sh
# Monta a configuração do Prometheus a partir das variáveis do App Service, sobe o
# Prometheus em segundo plano e entrega o processo principal ao Grafana.
set -eu

: "${BACKEND_HOST:?Defina BACKEND_HOST (host do App Service do backend).}"
: "${METRICS_TOKEN:?Defina METRICS_TOKEN (o mesmo do backend).}"

mkdir -p /tmp/monitoring /tmp/prometheus-data
# O token vai para um arquivo, que o Prometheus lê; nunca entra no log.
printf '%s' "$METRICS_TOKEN" > /tmp/monitoring/metrics_token
sed -e "s|__BACKEND_HOST__|${BACKEND_HOST}|" -e "s|__BACKEND_SCHEME__|${BACKEND_SCHEME:-https}|" \
  /etc/monitoring/prometheus.yml.template > /tmp/monitoring/prometheus.yml

prometheus \
  --config.file=/tmp/monitoring/prometheus.yml \
  --storage.tsdb.path=/tmp/prometheus-data \
  --storage.tsdb.retention.time="${PROMETHEUS_RETENTION:-15d}" \
  --web.listen-address=127.0.0.1:9090 &

exec /run.sh
