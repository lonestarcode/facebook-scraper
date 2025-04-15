"""Kafka client for event-driven communication between services."""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
import socket
from contextlib import contextmanager

from shared.config.settings import get_settings

# Configure logger
logger = logging.getLogger("kafka")

class KafkaClient:
    """
    Kafka client for producing and consuming messages.
    
    Provides:
    - Message publishing
    - Synchronous and asynchronous consumption
    - Topic management
    - Error handling and retries
    """
    
    def __init__(self, service_name: str):
        """
        Initialize Kafka client with service-specific configuration.
        
        Args:
            service_name: Name of the service using this client
        """
        self.settings = get_settings(service_name)
        self.service_name = service_name
        
        # Generate client id using hostname and service name for uniqueness
        hostname = socket.gethostname()
        self.client_id = f"{hostname}-{service_name}-{id(self)}"
        
        # Configure producer
        self.producer_config = {
            'bootstrap.servers': self.settings.kafka.bootstrap_servers,
            'client.id': f"{self.client_id}-producer",
            'acks': 'all',
            'retries': 3,
            'retry.backoff.ms': 500,
            'linger.ms': 5,
            'compression.type': 'snappy',
            'max.in.flight.requests.per.connection': 1,
        }
        
        # Configure consumer
        self.consumer_config = {
            'bootstrap.servers': self.settings.kafka.bootstrap_servers,
            'client.id': f"{self.client_id}-consumer",
            'group.id': f"{self.service_name}-group",
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 30000,     # 30 seconds
            'heartbeat.interval.ms': 10000,  # 10 seconds
        }
        
        # Configure admin client
        self.admin_config = {
            'bootstrap.servers': self.settings.kafka.bootstrap_servers,
            'client.id': f"{self.client_id}-admin",
        }
        
        # Initialize clients lazily
        self._producer = None
        self._consumer = None
        self._admin = None
    
    @property
    def producer(self) -> Producer:
        """
        Get or create Kafka producer.
        
        Returns:
            Configured Kafka producer
        """
        if self._producer is None:
            self._producer = Producer(self.producer_config)
        return self._producer
    
    @property
    def admin(self) -> AdminClient:
        """
        Get or create Kafka admin client.
        
        Returns:
            Configured Kafka admin client
        """
        if self._admin is None:
            self._admin = AdminClient(self.admin_config)
        return self._admin
    
    def get_consumer(self, topics: List[str] = None, group_id: str = None) -> Consumer:
        """
        Create a new consumer with optional custom configuration.
        
        Args:
            topics: List of topics to subscribe to
            group_id: Custom consumer group ID
            
        Returns:
            Configured Kafka consumer
        """
        config = self.consumer_config.copy()
        
        if group_id:
            config['group.id'] = group_id
        
        consumer = Consumer(config)
        
        if topics:
            consumer.subscribe(topics)
        
        return consumer
    
    def publish_event(self, topic: str, value: Dict[str, Any], key: str = None) -> None:
        """
        Publish an event to a Kafka topic.
        
        Args:
            topic: Kafka topic to publish to
            value: Event data to publish
            key: Optional message key for partitioning
        """
        try:
            # Serialize value to JSON
            serialized_value = json.dumps(value).encode('utf-8')
            
            # Serialize key if provided
            serialized_key = key.encode('utf-8') if key else None
            
            # Produce message
            self.producer.produce(
                topic=topic,
                key=serialized_key,
                value=serialized_value,
                on_delivery=self._delivery_callback
            )
            
            # Trigger any delivery callbacks
            self.producer.poll(0)
            
            logger.debug(f"Published event to {topic}: {value}")
            
        except Exception as e:
            logger.error(f"Failed to publish event to {topic}: {str(e)}")
            raise
    
    def flush(self, timeout: float = 10.0) -> None:
        """
        Flush the producer to ensure all messages are delivered.
        
        Args:
            timeout: Maximum time to wait for flush completion in seconds
        """
        try:
            self.producer.flush(timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to flush producer: {str(e)}")
            raise
    
    def _delivery_callback(self, err, msg) -> None:
        """
        Callback for message delivery reports.
        
        Args:
            err: Error information or None
            msg: Message information
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
    
    def consume_batch(
        self, 
        topics: List[str], 
        batch_size: int = 100, 
        timeout: float = 1.0,
        group_id: str = None
    ) -> List[Any]:
        """
        Consume a batch of messages synchronously.
        
        Args:
            topics: List of topics to consume from
            batch_size: Maximum number of messages to consume
            timeout: Maximum time to wait for messages in seconds
            group_id: Optional custom consumer group ID
            
        Returns:
            List of consumed messages
        """
        consumer = self.get_consumer(topics, group_id)
        
        try:
            messages = []
            
            # Poll for messages
            for _ in range(batch_size):
                msg = consumer.poll(timeout=timeout)
                
                if msg is None:
                    # No more messages within timeout
                    break
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break
                
                messages.append(msg)
            
            # Commit offsets
            if messages:
                consumer.commit(asynchronous=False)
            
            return messages
            
        finally:
            consumer.close()
    
    async def consume_async(
        self, 
        topics: List[str], 
        batch_size: int = 100,
        timeout: float = 1.0,
        group_id: str = None
    ):
        """
        Consume messages asynchronously using an async generator.
        
        Args:
            topics: List of topics to consume from
            batch_size: Maximum batch size for polling
            timeout: Maximum time to wait for messages in seconds
            group_id: Optional custom consumer group ID
            
        Yields:
            Consumed messages one by one
        """
        consumer = self.get_consumer(topics, group_id)
        
        try:
            while True:
                # Use asyncio to poll without blocking
                messages = await asyncio.to_thread(
                    self._poll_messages, consumer, batch_size, timeout
                )
                
                if not messages:
                    # No messages, yield control back to event loop
                    await asyncio.sleep(0.1)
                    continue
                
                # Yield messages one by one
                for msg in messages:
                    yield msg
                
                # Commit offsets
                await asyncio.to_thread(
                    consumer.commit, asynchronous=False
                )
                
        except Exception as e:
            logger.error(f"Error in async consumer: {str(e)}")
            raise
            
        finally:
            consumer.close()
    
    def _poll_messages(self, consumer: Consumer, batch_size: int, timeout: float) -> List[Any]:
        """
        Poll for messages from Kafka consumer.
        
        Args:
            consumer: Kafka consumer
            batch_size: Maximum number of messages to consume
            timeout: Maximum time to wait for messages in seconds
            
        Returns:
            List of consumed messages
        """
        messages = []
        
        for _ in range(batch_size):
            msg = consumer.poll(timeout=timeout)
            
            if msg is None:
                # No more messages within timeout
                break
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition, not an error
                    continue
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                    break
            
            messages.append(msg)
        
        return messages
    
    def ensure_topics_exist(self, topics: List[str], partitions: int = 3, replication: int = 1) -> None:
        """
        Ensure that the specified topics exist, creating them if necessary.
        
        Args:
            topics: List of topic names to ensure exist
            partitions: Number of partitions for new topics
            replication: Replication factor for new topics
        """
        admin = self.admin
        
        # Get existing topics
        metadata = admin.list_topics(timeout=10)
        existing_topics = metadata.topics
        
        # Filter out topics that already exist
        topics_to_create = [
            topic for topic in topics if topic not in existing_topics
        ]
        
        if not topics_to_create:
            logger.debug("All required topics already exist")
            return
        
        # Create new topic configurations
        new_topics = [
            NewTopic(
                topic,
                num_partitions=partitions,
                replication_factor=replication
            ) for topic in topics_to_create
        ]
        
        # Create the topics
        try:
            futures = admin.create_topics(new_topics)
            
            # Wait for operation to complete
            for topic, future in futures.items():
                future.result()
                logger.info(f"Created topic: {topic}")
                
        except KafkaException as e:
            logger.error(f"Failed to create topics: {str(e)}")
            raise
    
    def check_connection(self) -> bool:
        """
        Check if the Kafka connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Try to get metadata, which requires a connection
            self.admin.list_topics(timeout=5)
            return True
        except Exception as e:
            logger.error(f"Kafka connection check failed: {str(e)}")
            return False

# Global client cache
_kafka_clients: Dict[str, KafkaClient] = {}

def get_kafka_client(service_name: str) -> KafkaClient:
    """
    Get or create a Kafka client for the specified service.
    
    This function caches clients by service name.
    
    Args:
        service_name: Name of the service requesting the client
        
    Returns:
        Configured Kafka client
    """
    if service_name not in _kafka_clients:
        _kafka_clients[service_name] = KafkaClient(service_name)
    
    return _kafka_clients[service_name]

@contextmanager
def kafka_producer(service_name: str):
    """
    Context manager for Kafka producer operations.
    
    Ensures proper flushing of messages on exit.
    
    Args:
        service_name: Name of the service using the producer
        
    Yields:
        Kafka client ready for producing messages
    """
    client = get_kafka_client(service_name)
    try:
        yield client
    finally:
        # Ensure all messages are delivered before exiting
        client.flush() 