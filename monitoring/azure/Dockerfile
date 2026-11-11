# Prometheus e Grafana numa imagem só, para rodar 24h no Azure App Service, no
# mesmo plano do backend (sem custo a mais: o plano é cobrado, não cada app).
# O Prometheus escuta só dentro do contêiner; o Grafana, com login, é o único
# ponto exposto. Ver docs/deployment/monitoring.md.
#
# Contexto de build: a pasta monitoring/, para reaproveitar o painel e os alertas
# usados no docker compose local:  docker build -f monitoring/azure/Dockerfile monitoring
FROM prom/prometheus:v2.55.1 AS prometheus

FROM grafana/grafana:11.3.0
COPY --from=prometheus /bin/prometheus /usr/local/bin/prometheus

COPY azure/prometheus.yml.template /etc/monitoring/prometheus.yml.template
COPY prometheus/alerts.yml /etc/monitoring/alerts.yml
COPY azure/provisioning/datasources /etc/grafana/provisioning/datasources
COPY grafana/provisioning/dashboards /etc/grafana/provisioning/dashboards
COPY grafana/dashboards /var/lib/grafana/dashboards
COPY --chmod=0755 azure/start.sh /usr/local/bin/start-monitoring.sh

ENV GF_USERS_ALLOW_SIGN_UP=false \
    GF_AUTH_ANONYMOUS_ENABLED=false \
    GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/agenthub-overview.json

# Usuário sem privilégios da imagem do Grafana: Prometheus e Grafana não rodam como root.
USER grafana
EXPOSE 3000
ENTRYPOINT ["/usr/local/bin/start-monitoring.sh"]
