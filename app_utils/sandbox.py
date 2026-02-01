import docker

client = docker.from_env()

def run_code_in_docker(code_snippet):
    """
    Spins up a disposable container, runs python code, returns output.
    Forces IPv4-only environment logic for 24.04 compatibility.
    """
    container = None
    try:
        # Safety: Ensure image exists or pull
        image_tag = "rabid-sandbox:heavy"
        
        container = client.containers.run(
            image_tag,
            command=["python", "-c", code_snippet],
            detach=True,
            mem_limit="512m",
            network_mode="none", # Internet-killswitch for security
            stderr=True,
            stdout=True
        )
        
        # Wait for result with a hard 10s cutoff
        result = container.wait(timeout=10)
        logs = container.logs().decode("utf-8")
        
        container.remove(force=True)
        return logs if logs else "✅ Execution successful (No output)."

    except Exception as e:
        if container:
            try: container.remove(force=True)
            except: pass
        return f"☢️ SANDBOX CRITICAL ERROR: {str(e)}"