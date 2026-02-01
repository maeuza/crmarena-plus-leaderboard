command: 
      - |
        echo "-- Configurando Entorno --"
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests
        
        python3 -c "
        import urllib.request, tarfile, os
        url = 'https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz'
        urllib.request.urlretrieve(url, '/tmp/a2a.tar.gz')
        with tarfile.open('/tmp/a2a.tar.gz', 'r:gz') as tar:
            tar.extractall('/tmp/a2a_raw')
        os.rename('/tmp/a2a_raw/' + os.listdir('/tmp/a2a_raw')[0], '/tmp/a2a')
        "
        
        echo "-- Esperando agentes en puerto 9009 --"
        python3 -c "
        import socket, time
        for host in ['green-agent', 'salesforce_participant']:
            while socket.socket().connect_ex((host, 9009)):
                time.sleep(2)
        "

        echo "-- Ejecutando Evaluación Real --"
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/a2a/src
        
        # El comando final que genera el archivo results.json
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
