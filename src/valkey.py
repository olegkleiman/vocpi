import os
from glide import (
    NodeAddress,
    GlideClient,
    GlideClusterClient,
    GlideClientConfiguration,
    GlideClusterClientConfiguration,
)

_valkey_client: GlideClusterClient | None = None

async def get_valkey() -> GlideClusterClient | None:
    """
    FastAPI dependency - returns None if connection fails
    """
    global _valkey_client

    # "vocpicache-5lobxd.serverless.use1.cache.amazonaws.com",
    VALKEY_HOST = os.getenv("VALKEY_HOST")
    VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
    VALKEY_TLS = os.getenv("VALKEY_TLS", "false").lower() == "true"

    if _valkey_client is None:
        try:
            config = GlideClientConfiguration(
                addresses = [NodeAddress(
                    VALKEY_HOST, VALKEY_PORT,
                )],
                use_tls=VALKEY_TLS,
            )

            # _valkey_client = await GlideClusterClient.create(config)
            _valkey_client = await GlideClient.create(config)
        except Exception as e:
            print(f"Valkey connection failed: {e}")
            return None

    return _valkey_client