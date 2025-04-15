"""Kafka consumer module for processing Facebook Marketplace listings"""

import asyncio
import json
import logging
import signal
import threading
from typing import Dict, List, Callable, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor

from confluent_kafka import Consumer, KafkaError, KafkaException
import prometheus_client as prom
from opentelemetry import trace

# Configure logger
logger = logging.getLogger(__name__)

# Prometheus metrics
MESSAGES_PROCESSED = prom.Counter(
    'processor_messages_processed_total',
    'Total number of Kafka messages processed',
    ['topic', 'result']
)

PROCESSING_TIME = prom.Histogram(
    'processor_message_processing_seconds',
    'Time taken to process a message',
    ['topic']
)

# Tracer
tracer = trace.get_tracer(__name__)

class KafkaConsumerManager:
    """Manager for Kafka consumers to handle marketplace listing messages"""
    
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        auto_offset_reset: str = 'earliest',
        enable_auto_commit: bool = True,
        health_check_callback: Optional[Callable[[str, bool, str], None]] = None
    ):
        """Initialize Kafka consumer manager
        
        Args:
            bootstrap_servers: Comma-separated list of Kafka broker addresses
            group_id: Consumer group ID
            auto_offset_reset: Where to start consuming when no offset is stored
            enable_auto_commit: Whether to auto-commit offsets
            health_check_callback: Callback to update health check status
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.health_check_callback = health_check_callback
        
        self.consumers: Dict[str, Union[Consumer, Any]] = {}
        self.handlers: Dict[str, Dict[str, Callable]] = {}
        self.running = False
        self.consumer_threads: List[threading.Thread] = []
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # Set initial health status
        if self.health_check_callback:
            self.health_check_callback("kafka-consumer", False, "Not started yet")
    
    def add_topic_handler(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add a handler for a specific topic
        
        Args:
            topic: Kafka topic name
            handler: Function to process messages from this topic
        """
        if topic not in self.handlers:
            self.handlers[topic] = {}
        
        # Use the handler function name as the key
        handler_name = handler.__name__
        self.handlers[topic][handler_name] = handler
        logger.info(f"Added handler {handler_name} for topic {topic}")
    
    def _create_consumer(self, topics: List[str]) -> Consumer:
        """Create a Kafka consumer for the given topics
        
        Args:
            topics: List of topic names to subscribe to
            
        Returns:
            Configured Kafka consumer
        """
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': f"{self.group_id}-{'_'.join(topics)}",
            'auto.offset.reset': self.auto_offset_reset,
            'enable.auto.commit': self.enable_auto_commit,
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 60000,     # 1 minute
        }
        
        consumer = Consumer(config)
        consumer.subscribe(topics)
        
        logger.info(f"Created consumer for topics: {topics}")
        return consumer
    
    def _consume_loop(self, consumer: Consumer, topics: List[str]) -> None:
        """Main consumption loop for a consumer
        
        Args:
            consumer: Kafka consumer
            topics: List of topics this consumer is handling
        """
        try:
            while self.running:
                try:
                    # Poll for a message
                    msg = consumer.poll(timeout=1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition, not an error
                            continue
                        else:
                            logger.error(f"Kafka error: {msg.error()}")
                            if self.health_check_callback:
                                self.health_check_callback(
                                    "kafka-consumer", 
                                    False, 
                                    f"Kafka error: {msg.error()}"
                                )
                            continue
                    
                    # Process the message
                    topic = msg.topic()
                    try:
                        # Parse the message
                        value = json.loads(msg.value().decode('utf-8'))
                        
                        # Submit to thread pool for processing
                        with PROCESSING_TIME.labels(topic).time():
                            with tracer.start_as_current_span(f"process_{topic}_message"):
                                # Call all handlers for this topic
                                if topic in self.handlers:
                                    for handler_name, handler in self.handlers[topic].items():
                                        try:
                                            # Use thread pool to avoid blocking the consumer
                                            self.thread_pool.submit(handler, value)
                                        except Exception as e:
                                            logger.exception(f"Handler {handler_name} failed: {str(e)}")
                                            MESSAGES_PROCESSED.labels(topic=topic, result="error").inc()
                                else:
                                    logger.warning(f"No handlers registered for topic {topic}")
                        
                        # Increment successful processing counter
                        MESSAGES_PROCESSED.labels(topic=topic, result="success").inc()
                        
                    except json.JSONDecodeError:
                        logger.exception(f"Failed to parse message as JSON from topic {topic}")
                        MESSAGES_PROCESSED.labels(topic=topic, result="invalid_json").inc()
                    except Exception as e:
                        logger.exception(f"Error processing message: {str(e)}")
                        MESSAGES_PROCESSED.labels(topic=topic, result="error").inc()
                
                except Exception as e:
                    logger.exception(f"Consumer loop error: {str(e)}")
                    if self.health_check_callback:
                        self.health_check_callback(
                            "kafka-consumer", 
                            False, 
                            f"Consumer error: {str(e)}"
                        )
            
            # Clean exit from loop
            logger.info(f"Consumer for topics {topics} exiting")
        except Exception as e:
            logger.exception(f"Consumer thread error: {str(e)}")
        finally:
            try:
                consumer.close()
                logger.info(f"Consumer for topics {topics} closed")
            except Exception as e:
                logger.exception(f"Error closing consumer: {str(e)}")
    
    async def start(self) -> None:
        """Start all configured consumers"""
        if self.running:
            logger.warning("Consumers already running")
            return
        
        self.running = True
        
        # Create a consumer for each topic with handlers
        for topic in self.handlers.keys():
            if topic not in self.consumers:
                consumer = self._create_consumer([topic])
                self.consumers[topic] = consumer
                
                # Start a thread for this consumer
                thread = threading.Thread(
                    target=self._consume_loop,
                    args=(consumer, [topic]),
                    daemon=True
                )
                thread.start()
                self.consumer_threads.append(thread)
                logger.info(f"Started consumer thread for topic {topic}")
        
        # Update health check status
        if self.health_check_callback:
            self.health_check_callback("kafka-consumer", True, "Connected and consuming")
        
        logger.info("All Kafka consumers started")
    
    async def stop(self) -> None:
        """Stop all consumers gracefully"""
        if not self.running:
            logger.warning("Consumers not running")
            return
        
        logger.info("Stopping Kafka consumers...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.consumer_threads:
            thread.join(timeout=5.0)
        
        # Close consumers
        for topic, consumer in self.consumers.items():
            try:
                consumer.close()
                logger.info(f"Closed consumer for topic {topic}")
            except Exception as e:
                logger.exception(f"Error closing consumer for topic {topic}: {str(e)}")
        
        # Update health check status
        if self.health_check_callback:
            self.health_check_callback("kafka-consumer", False, "Stopped")
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("All Kafka consumers stopped")

# Example handler functions
async def process_listing(message: Dict[str, Any]) -> None:
    """Process a marketplace listing message
    
    Args:
        message: Parsed JSON message containing listing data
    """
    with tracer.start_as_current_span("process_listing_details"):
        listing_id = message.get("id", "unknown")
        logger.info(f"Processing listing {listing_id}")
        # Actual processing logic here
        
async def process_alert(message: Dict[str, Any]) -> None:
    """Process an alert message
    
    Args:
        message: Parsed JSON message containing alert data
    """
    with tracer.start_as_current_span("process_alert"):
        alert_id = message.get("id", "unknown")
        logger.info(f"Processing alert {alert_id}")
        # Actual alert processing logic here 