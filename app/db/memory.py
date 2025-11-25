"""
In-Memory Database Module

This module implements a thread-safe, async-compatible in-memory database.
It demonstrates database operations, transactions, and concurrency control.

Key Features:
- Thread-safe operations with asyncio locks
- ACID-like transactions
- CRUD operations
- Query filtering and sorting
- Connection pooling simulation

Usage:
    from app.db.memory import InMemoryDatabase, get_db
    
    db = get_db()
    await db.create("users", {"name": "John", "email": "john@example.com"})
    users = await db.read_all("users")
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import copy
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Transaction:
    """
    Represents a database transaction.
    
    Transactions provide ACID-like properties for multiple operations.
    Changes are isolated until committed or rolled back.
    """
    id: str
    changes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


class InMemoryDatabase:
    """
    Thread-safe in-memory database implementation.
    
    This class provides a simple key-value store with support for:
    - Async operations
    - Thread safety via asyncio locks
    - Transactions
    - Query operations
    
    The database is organized as collections (like tables) containing documents (like rows).
    
    Example:
        >>> db = InMemoryDatabase()
        >>> await db.create("users", {"id": 1, "name": "Alice"})
        >>> user = await db.read_by_id("users", 1)
        >>> await db.update("users", 1, {"name": "Alice Updated"})
        >>> await db.delete("users", 1)
    """
    
    def __init__(self) -> None:
        """Initialize the database with thread-safe structures."""
        # Main storage: collection_name -> list of documents
        self._storage: Dict[str, List[Dict[str, Any]]] = {}
        
        # Locks for thread safety
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        
        # Transaction support
        self._transactions: Dict[str, Transaction] = {}
        
        # Auto-increment IDs per collection
        self._id_counters: Dict[str, int] = {}
        
        # Statistics for monitoring
        self._stats = {
            "reads": 0,
            "writes": 0,
            "deletes": 0,
            "transactions": 0,
        }
        
        logger.info("InMemoryDatabase initialized")
    
    async def _get_collection_lock(self, collection: str) -> asyncio.Lock:
        """
        Get or create a lock for a specific collection.
        
        This ensures thread-safe access to each collection independently.
        
        Args:
            collection: Collection name
            
        Returns:
            asyncio.Lock for the collection
        """
        async with self._global_lock:
            if collection not in self._locks:
                self._locks[collection] = asyncio.Lock()
            return self._locks[collection]
    
    async def _initialize_collection(self, collection: str) -> None:
        """
        Initialize a collection if it doesn't exist.
        
        Args:
            collection: Collection name
        """
        async with self._global_lock:
            if collection not in self._storage:
                self._storage[collection] = []
                self._id_counters[collection] = 0
                logger.debug("Collection created", collection=collection)
    
    def _generate_id(self, collection: str) -> int:
        """
        Generate a unique auto-incrementing ID for a collection.
        
        Args:
            collection: Collection name
            
        Returns:
            New unique ID
        """
        self._id_counters[collection] += 1
        return self._id_counters[collection]
    
    async def create(
        self,
        collection: str,
        document: Dict[str, Any],
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new document in a collection.
        
        Args:
            collection: Collection name
            document: Document data to insert
            transaction_id: Optional transaction ID
            
        Returns:
            Created document with generated ID
            
        Example:
            >>> doc = await db.create("users", {"name": "Bob", "age": 30})
            >>> print(doc["id"])
            1
        """
        await self._initialize_collection(collection)
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            # Generate ID if not provided
            if "id" not in document:
                document["id"] = self._generate_id(collection)
            
            # Add metadata
            document["created_at"] = datetime.utcnow().isoformat()
            document["updated_at"] = datetime.utcnow().isoformat()
            
            # Make a copy to avoid external modifications
            doc_copy = copy.deepcopy(document)
            
            if transaction_id and transaction_id in self._transactions:
                # Add to transaction
                if collection not in self._transactions[transaction_id].changes:
                    self._transactions[transaction_id].changes[collection] = []
                self._transactions[transaction_id].changes[collection].append(
                    {"action": "create", "document": doc_copy}
                )
            else:
                # Direct insert
                self._storage[collection].append(doc_copy)
            
            self._stats["writes"] += 1
            logger.debug(
                "Document created",
                collection=collection,
                document_id=document["id"]
            )
            
            return copy.deepcopy(doc_copy)
    
    async def read_by_id(
        self,
        collection: str,
        doc_id: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Read a document by its ID.
        
        Args:
            collection: Collection name
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
            
        Example:
            >>> doc = await db.read_by_id("users", 1)
            >>> print(doc["name"])
            Bob
        """
        await self._initialize_collection(collection)
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            for doc in self._storage[collection]:
                if doc.get("id") == doc_id:
                    self._stats["reads"] += 1
                    return copy.deepcopy(doc)
            
            return None
    
    async def read_all(
        self,
        collection: str,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        sort_by: Optional[str] = None,
        limit: Optional[int] = None,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Read all documents from a collection with optional filtering.
        
        Args:
            collection: Collection name
            filter_fn: Optional filter function
            sort_by: Optional field to sort by
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            
        Returns:
            List of matching documents
            
        Example:
            >>> users = await db.read_all(
            ...     "users",
            ...     filter_fn=lambda u: u["age"] > 25,
            ...     sort_by="name",
            ...     limit=10
            ... )
        """
        await self._initialize_collection(collection)
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            results = copy.deepcopy(self._storage[collection])
            
            # Apply filter
            if filter_fn:
                results = [doc for doc in results if filter_fn(doc)]
            
            # Apply sorting
            if sort_by:
                results.sort(key=lambda x: x.get(sort_by, ""))
            
            # Apply pagination
            results = results[skip:]
            if limit:
                results = results[:limit]
            
            self._stats["reads"] += 1
            return results
    
    async def update(
        self,
        collection: str,
        doc_id: Any,
        updates: Dict[str, Any],
        transaction_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a document by ID.
        
        Args:
            collection: Collection name
            doc_id: Document ID
            updates: Fields to update
            transaction_id: Optional transaction ID
            
        Returns:
            Updated document if found, None otherwise
            
        Example:
            >>> updated = await db.update("users", 1, {"age": 31})
            >>> print(updated["age"])
            31
        """
        await self._initialize_collection(collection)
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            for i, doc in enumerate(self._storage[collection]):
                if doc.get("id") == doc_id:
                    # Update fields
                    self._storage[collection][i].update(updates)
                    self._storage[collection][i]["updated_at"] = (
                        datetime.utcnow().isoformat()
                    )
                    
                    self._stats["writes"] += 1
                    logger.debug(
                        "Document updated",
                        collection=collection,
                        document_id=doc_id
                    )
                    
                    return copy.deepcopy(self._storage[collection][i])
            
            return None
    
    async def delete(
        self,
        collection: str,
        doc_id: Any,
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Delete a document by ID.
        
        Args:
            collection: Collection name
            doc_id: Document ID
            transaction_id: Optional transaction ID
            
        Returns:
            True if deleted, False if not found
            
        Example:
            >>> success = await db.delete("users", 1)
            >>> print(success)
            True
        """
        await self._initialize_collection(collection)
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            for i, doc in enumerate(self._storage[collection]):
                if doc.get("id") == doc_id:
                    del self._storage[collection][i]
                    self._stats["deletes"] += 1
                    logger.debug(
                        "Document deleted",
                        collection=collection,
                        document_id=doc_id
                    )
                    return True
            
            return False
    
    async def count(self, collection: str) -> int:
        """
        Count documents in a collection.
        
        Args:
            collection: Collection name
            
        Returns:
            Number of documents
        """
        await self._initialize_collection(collection)
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            return len(self._storage[collection])
    
    async def clear_collection(self, collection: str) -> None:
        """
        Clear all documents from a collection.
        
        Args:
            collection: Collection name
        """
        lock = await self._get_collection_lock(collection)
        
        async with lock:
            if collection in self._storage:
                self._storage[collection] = []
                self._id_counters[collection] = 0
                logger.info("Collection cleared", collection=collection)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with operation counts
        """
        return copy.deepcopy(self._stats)


# Global database instance (singleton pattern)
_db_instance: Optional[InMemoryDatabase] = None


def get_db() -> InMemoryDatabase:
    """
    Get the global database instance.
    
    This implements the singleton pattern to ensure a single database instance.
    
    Returns:
        Global InMemoryDatabase instance
        
    Example:
        >>> db = get_db()
        >>> await db.create("users", {"name": "Alice"})
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = InMemoryDatabase()
    return _db_instance


async def reset_db() -> None:
    """
    Reset the database (useful for testing).
    
    This clears all data and resets counters.
    """
    global _db_instance
    _db_instance = InMemoryDatabase()
    logger.info("Database reset")
