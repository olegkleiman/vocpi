import os
import redis

# from glide import (
#     NodeAddress,
#     GlideClient,
#     GlideClientConfiguration,
#     GlideClusterClientConfiguration,
# )

# _valkey_client: GlideClient | None = None
_redis_client: redis.Redis | None = None

async def get_redis():

    global _redis_client

    host = os.getenv("VALKEY_HOST")
    port = int(os.getenv("VALKEY_PORT", "6379"))
    use_tls = os.getenv("VALKEY_TLS", "false").lower() == "true"
    cluster = os.getenv("VALKEY_CLUSTER", "false").lower() == "true"

    _redis_client = redis.Redis(
        host=host,
        port=port,
        decode_responses=True
    )

    return _redis_client

# async def get_valkey() -> GlideClient | None:
#     """
#     FastAPI dependency - returns None if connection fails
#     """
#     global _valkey_client

#     # "vocpicache-5lobxd.serverless.use1.cache.amazonaws.com",
#     host = os.getenv("VALKEY_HOST")
#     port = int(os.getenv("VALKEY_PORT", "6379"))
#     use_tls = os.getenv("VALKEY_TLS", "false").lower() == "true"
#     cluster = os.getenv("VALKEY_CLUSTER", "false").lower() == "true"


#     if _valkey_client is None:
#         try:
        
#             if cluster:
#                 config = GlideClusterClientConfiguration(addresses=[NodeAddress(host, port)], use_tls=use_tls)
#                 from glide import GlideClusterClient
#                 _valkey_client = await GlideClusterClient.create(config)
#             else:
#                 config = GlideClientConfiguration(addresses=[NodeAddress(host, port)], use_tls=use_tls)
#                 _valkey_client = await GlideClient.create(config)

#             return _valkey_client
        
#         except Exception as e:
#             print(f"Valkey connection failed: {e}")
#             return None

#     return _valkey_client