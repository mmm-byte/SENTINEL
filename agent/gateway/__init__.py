from agent.gateway.server import run as run_gateway


def run():
    """Start the gateway server on port 9003."""
    run_gateway(host="127.0.0.1", port=9003)


if __name__ == "__main__":
    run()
