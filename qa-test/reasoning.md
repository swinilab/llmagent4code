# Reasoning and Trade-off Analysis

## NFR 1.1 — Response Time (Server-side Caching)
To minimize round-trip latency under load for core journeys (search, cart, checkout), implementing a server-side caching layer is the most effective architectural mechanism. Caching avoids expensive database queries and recomputation.

### Library Selection & Trade-offs
1. **redis-py**: The industry standard for distributed caching. High performance, supports various data structures, and TTLs. Trade-off: Requires a separate Redis server infrastructure.
2. **pymemcache**: A lightweight, pure Python Memcached client. Extremely fast for simple key-value pairs. Trade-off: Lacks advanced data structures compared to Redis.
3. **diskcache**: Excellent for local, persistent caching without external dependencies. Great for caching large objects. Trade-off: Slower than in-memory caches; I/O bound by disk speed.
4. **aiocache**: Provides an async-first interface, crucial for non-blocking I/O in modern web frameworks (FastAPI, aiohttp). Trade-off: Adds an abstraction layer which might slightly complicate debugging.
5. **cashews**: Offers decorator-based caching with built-in support for invalidation and fallbacks. Trade-off: Less granular control compared to manual cache management.

## NFR 1.2 — Concurrency & Resource Utilization (Asynchronous I/O)
To exploit server resources with minimal queuing, the system must use non-blocking I/O operations. This prevents worker threads from sitting idle while waiting for network or disk responses.

### Library Selection & Trade-offs
1. **asyncio**: The standard library solution for event loops. Highly integrated and universally supported. Trade-off: Requires async/await syntax throughout the codebase.
2. **uvloop**: A drop-in replacement for the asyncio event loop built on libuv. Offers 2-4x performance improvements. Trade-off: C-extension dependency, not available on Windows natively.
3. **trio**: A more structured alternative to asyncio, using "nurseries" to prevent abandoned tasks. Trade-off: Smaller ecosystem compared to asyncio.
4. **gevent**: Uses greenlets and monkey-patching to make synchronous code asynchronous without syntax changes. Trade-off: Monkey-patching can lead to subtle, hard-to-debug compatibility issues.
5. **anyio**: An abstraction layer over asyncio and trio, allowing code to run on either backend. Trade-off: Adds a slight learning curve for its specific synchronization primitives.

## NFR 1.3 — Queue Management (Message Queues)
To prevent sudden traffic spikes from crashing the system, a message queue (broker) decouples the request ingestion from the processing. This acts as a shock absorber.

### Library Selection & Trade-offs
1. **celery**: The most feature-rich distributed task queue in Python. Supports complex routing, retries, and scheduling. Trade-off: Can be heavy and complex to configure for simple tasks.
2. **rq (Redis Queue)**: A lightweight alternative to Celery. Very simple to use and integrates perfectly with Redis. Trade-off: Lacks advanced features like task chaining and complex routing.
3. **pika**: A robust RabbitMQ client. Allows fine-grained control over AMQP features like exchanges, routing keys, and dead-letter queues. Trade-off: Requires writing boilerplate code for consumer loops.
4. **confluent-kafka**: High-performance Kafka client. Excellent for high-throughput, persistent event streaming. Trade-off: Kafka infrastructure is complex to deploy and manage.
5. **boto3 (SQS)**: Fully managed AWS message queue. No infrastructure to manage, infinite scaling. Trade-off: Vendor lock-in and potential latency compared to local brokers.

## NFR 2.1 — Graceful Degradation (Circuit Breaker)
Under extreme contention, non-essential features (like recommendations) must fail without affecting core checkout. A Circuit Breaker pattern detects failures and trips, failing fast and allowing fallback logic.

### Library Selection & Trade-offs
1. **pybreaker**: A robust, thread-safe implementation of the circuit breaker pattern. Easy to use with decorators. Trade-off: Synchronous only.
2. **circuitbreaker**: A very simple, lightweight library. Easy to understand and modify. Trade-off: Lacks some advanced features like monitoring hooks out-of-the-box.
3. **aiobreaker**: Provides async support for circuit breaking, essential for modern async web apps. Trade-off: Niche library, smaller community.
4. **purgatory**: An async circuit breaker factory that integrates well with modern Python. Trade-off: Relatively new, fewer production battle scars.
5. **tenacity**: While primarily a retry library, it is frequently used for graceful degradation by providing fallbacks after exhausted retries. Trade-off: Not a true circuit breaker, meaning it will still attempt connections during high failure rates.

## NFR 2.2 — Fault Detection and Recovery (Health Checks)
The system must detect internal failures and recover automatically. Health checks and service discovery ensure that failed instances are removed from rotation and potentially restarted.

### Library Selection & Trade-offs
1. **python-consul**: Integrates with HashiCorp Consul for service discovery and health checking. Highly scalable. Trade-off: Requires a Consul cluster.
2. **kazoo**: A Zookeeper client. Excellent for distributed coordination and ephemeral nodes for liveness. Trade-off: Zookeeper is complex and Java-heavy.
3. **etcd3**: A client for etcd, commonly used in Kubernetes. Leases provide robust liveness checks. Trade-off: gRPC-based, dependency management can be tricky.
4. **psutil**: Local system monitoring. Can detect high CPU/memory and trigger internal recovery logic or alerts. Trade-off: Only monitors local node, not distributed state.
5. **supervisor**: Process control system. Can automatically restart crashed Python processes. Trade-off: Not a distributed solution, only works on a single host.

## NFR 2.3 — State Preservation (Event Sourcing / WAL)
In case of a process crash, the system must restore its state and resume pending orders. Write-Ahead Logging (WAL) or Event Sourcing ensures every state change is recorded to a durable medium before acknowledging success.

### Library Selection & Trade-offs
1. **sqlite3**: Native Python library. WAL mode provides excellent durability and crash recovery for single-node applications. Trade-off: Not suitable for distributed, high-concurrency writes.
2. **psycopg2**: PostgreSQL driver. Relational databases provide ACID guarantees and WAL out of the box. Trade-off: Requires managing database schemas and connections.
3. **zodb**: An object-oriented database that preserves the native Python object graph. Transactions are atomic. Trade-off: Not designed for high-throughput, distributed scenarios.
4. **redis-py**: Redis AOF (Append Only File) persistence can act as a WAL for fast state recovery. Trade-off: Persistence is asynchronous by default, risking minimal data loss unless configured with `appendfsync always`.
5. **pymongo**: MongoDB driver. Uses journaling to ensure durability. Trade-off: Schema-less nature requires careful application-level validation to ensure state consistency.
