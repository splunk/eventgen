# should install docker-compose on circle ci env, but do not impact local mac os env
if [[ ! -f /usr/local/bin/docker-compose ]]; then
  echo "Installing Linux docker-compose to /usr/local/bin"
  sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-Linux-x86_64" -o /usr/local/bin/docker-compose
	sudo chmod +x /usr/local/bin/docker-compose
fi
