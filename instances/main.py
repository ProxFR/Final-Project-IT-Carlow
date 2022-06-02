from cmath import log
from lib2to3.pgen2 import token
from time import sleep
import digitalocean
import os 

def destroy(droplet_id):
  droplet = digitalocean.Droplet(token=os.getenv('DO_TOKEN'),id=droplet_id)
  droplet.destroy()

class drop:
    def __init__(self, name, region, image, size, user_data):        
        if os.getenv('DO_TOKEN') is None:
            print("You need to set your DO_TOKEN environment variable")

        self.token = os.getenv('DO_TOKEN')
        self.manager = digitalocean.Manager(token = self.token)
        keys = self.manager.get_all_sshkeys()

        self.droplet = digitalocean.Droplet(token=self.manager.token,
                            name=name,
                            region=region,
                            image=image,
                            size_slug=size,
                            user_data=user_data,
                            ssh_keys=keys,
                            backups=False,
                            private_networking=True,
                            monitoring=True)

        self.name = name
        self.region = region
        self.image = image
        self.size = size

    def create(self):
        self.droplet.create()

    def load(self):
        dropInfo = self.droplet.load()
        return dropInfo


class hashcat(drop):
    def __init__(self, name, region, image, size, api_token, hash, wordlist_url, wordlist_name):
        self.generate_user_data(api_token, hash, wordlist_url, wordlist_name)
        super().__init__(name, region, image, size, self.user_data)
        
    def create(self):
        self.droplet.create()
    
    def generate_user_data(self, parm_api_token, parm_hash, parm_wordlist_url, parm_wordlist_name):
        api_url = os.getenv('APP_URL')
        monitoring_url = os.getenv('MONITORING_URL')
        api_token = parm_api_token
        hash = parm_hash
        wordlist_url = parm_wordlist_url
        wordlist_name = parm_wordlist_name

        self.user_data = '''#!/bin/bash
export API_URL={}
export API_TOKEN={}
export HASH={}
export WORDLIST_URL={}
export WORDLIST_NAME={}
export MONITORING_URL={}
sleep 5 #Wait for network to be up
tee /root/grafana_agent.sh<<EOBF
#!/bin/bash
# Create grafana-agent user
groupadd --system grafana-agent
useradd -s /sbin/nologin --system -g grafana-agent grafana-agent

# Install dependencies
apt install -y wget unzip curl htop

# Download and install grafana agent
wget https://github.com/grafana/agent/releases/download/v0.24.2/agent-linux-amd64.zip -P /tmp
unzip /tmp/agent-linux-amd64*.zip -d /tmp
cp /tmp/agent-linux-amd64 /usr/local/bin/grafana-agent
chmod +x /usr/local/bin/grafana-agent

# Create service
tee /etc/systemd/system/grafana-agent.service<<'EOF'
[Unit]
Description=Monitoring system and forwarder
Documentation=https://grafana.com/docs/agent/latest/
Wants=network-online.target
After=network-online.target

[Service]
Restart=always
User=grafana-agent
#Environment=HOSTNAME=%H
#EnvironmentFile=/etc/sysconfig/grafana-agent
ExecStart=/usr/local/bin/grafana-agent --config.file /etc/grafana-agent.yaml
# If running the Agent in scraping service mode, you will want to override this value with
# something larger to allow the Agent to gracefully leave the cluster. 4800s is recommend.
TimeoutStopSec=20s
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
EOF

# Config Grafana-agent
tee /etc/grafana-agent.yaml<<EOF
server:
  http_listen_address: '127.0.0.1'
  http_listen_port: 9090

metrics:
  global:
    scrape_interval: 1m
  wal_directory: '/tmp/wal-grafana-agent'
  configs:
    - name: default
      scrape_configs:
        - job_name: "node_exporter"
          metrics_path: /integrations/node_exporter/metrics
          static_configs:
            - targets: ["localhost:9090"]
              labels:
                instance: "`cat /etc/hostname`"
          relabel_configs:
            - source_labels: [__address_]
              target_label: instance
              replacement: ''
              regex: '([^:]+)(:[0-9]+)?'

      remote_write:
      - url: "$MONITORING_URL/prometheus/api/v1/write"
      
logs:
  configs:
  - name: default
    positions:
      filename: /tmp/positions.yaml
    scrape_configs:
      - job_name: varlogs
        static_configs:
          - targets: [localhost]
            labels:
              instance: "`cat /etc/hostname`"
              job: varlogs
              __path__: /var/log/*log
              
    clients:
      - url: "$MONITORING_URL/loki/loki/api/v1/push"

integrations:
  agent:
    enabled: true
  node_exporter:
    enabled: true
    include_exporter_metrics: true
EOF
# Enable and start service
systemctl daemon-reload
systemctl enable grafana-agent.service
sleep 2
systemctl start grafana-agent.service
EOBF
bash /root/grafana_agent.sh
apt-get update -y && apt-get install -y hashcat
mkdir /root/hashcat
wget $WORDLIST_URL -P /root/hashcat/
curl --request POST --url $API_URL/api/created --header 'Content-Type: application/json' --header 'Token: '$API_TOKEN'' --data '{{ "instance_status": "Ready" }}'
tee /root/hashcat/hashcat.py<<EOF
import subprocess
import requests

cmd = ["/bin/hashcat", "$HASH", "/root/hashcat/$WORDLIST_NAME", "-o", "/root/hashcat/result.txt", "--potfile-disable", "--status","--quiet", "-O", "--status-json", "--force", "-m", "0", "--status-timer", "1"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
headers = {{
    'Content-Type': "application/json",
    'Token': '$API_TOKEN'
    }}
while True:
    line = p.stdout.readline()
    print(line)
    if not line:
        break
    response = requests.request("POST", "$API_URL/api/status", data = line, headers = headers)
    print(response.status_code, response.reason, response.text)
EOF

python3 /root/hashcat/hashcat.py

if [ -s /root/hashcat/result.txt ]; then
    # The file is not-empty.
    curl --request POST --url $API_URL/api/result/OK --header 'Content-Type: application/json' --header 'Token: '$API_TOKEN'' --data '{{ "Result": "'"$(head -n 1 /root/hashcat/result.txt)"'" }}'
else
    # The file is empty.
    curl --request POST --url $API_URL/api/result/FAILED --header 'Content-Type: application/json' --header 'Token: '$API_TOKEN'' --data '{{ "Result": "FAILED" }}'
fi
'''.format(api_url,api_token,hash,wordlist_url,wordlist_name,monitoring_url)