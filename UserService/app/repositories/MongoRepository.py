from abc import ABC, abstractmethod
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import List, Optional, Dict, Any, TypeVar, Generic, Type
from pymongo import ASCENDING, DESCENDING
from pydantic import BaseModel
from enum import Enum
from datetime import date, datetime
import json
try:
    # pydantic v1 encoder for JSON-friendly conversion
    from pydantic.json import pydantic_encoder  # type: ignore
except Exception:  # pragma: no cover
    pydantic_encoder = None  # type: ignore
from bson import ObjectId

T = TypeVar('T', bound=BaseModel)


class MongoRepository(ABC, Generic[T]):
    """
    Abstract base repository class providing common CRUD operations for MongoDB collections.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.db = db
        self.collection: AsyncIOMotorCollection = db.get_collection(collection_name)
    
    @abstractmethod
    def get_model_class(self) -> Type[T]:
        """Return the model class for this repository."""
        pass
    
    def _document_to_model(self, doc: Dict[str, Any]) -> T:
        """Convert a MongoDB document to a model instance.
        Handles MongoDB _id fields (both top-level and nested in value objects like ssoId, Title, etc.).
        Converts ObjectId instances to strings for Pydantic compatibility.
        """
        if doc is None:
            return None
        
        # Recursively convert ObjectIds to strings and handle nested _id fields
        doc = self._convert_objectids_and_ids(doc)
        
        model_class = self.get_model_class()
        try:
            # Use model_validate for Pydantic V2 compatibility
            if hasattr(model_class, 'model_validate'):
                return model_class.model_validate(doc)
            else:
                # Fallback for older Pydantic versions
                return model_class(**doc)
        except Exception as e:
            print(f"Error creating {model_class.__name__}: {e}")
            print(f"Doc keys: {list(doc.keys())}")
            
            # Get the model's expected fields
            model_fields = set()
            if hasattr(model_class, 'model_fields'):
                model_fields = set(model_class.model_fields.keys())
            elif hasattr(model_class, '__fields__'):
                model_fields = set(model_class.__fields__.keys())
            
            # Filter doc to only include expected fields
            filtered_doc = {k: v for k, v in doc.items() if k in model_fields}
            print(f"Filtered to expected fields: {list(filtered_doc.keys())}")
            
            try:
                if hasattr(model_class, 'model_validate'):
                    return model_class.model_validate(filtered_doc)
                else:
                    return model_class(**filtered_doc)
            except Exception as inner_e:
                print(f"Still failed after filtering: {inner_e}")
                # Return empty model as last resort
                return model_class.model_validate({}) if hasattr(model_class, 'model_validate') else model_class()
    
    def _convert_objectids_and_ids(self, obj: Any) -> Any:
        """Recursively convert ObjectId instances to strings and handle nested _id fields.
        
        MongoDB uses ObjectId for database IDs and stores them as { _id: ObjectId(...) }.
        Pydantic expects string values. This method:
        1. Converts all ObjectId instances to strings
        2. Converts nested { _id: value } to { id: value } for value objects
        """
        if obj is None:
            return None
        
        # Handle ObjectId
        if isinstance(obj, ObjectId):
            return str(obj)
        
        # Handle dict
        if isinstance(obj, dict):
            converted = {}
            for key, value in obj.items():
                # Skip _class field from MongoDB Spring Data
                if key == '_class':
                    continue
                # Recursively convert nested values
                converted[key] = self._convert_objectids_and_ids(value)
            
            # Handle top-level _id -> id conversion
            if "_id" in converted and "id" not in converted:
                converted["id"] = converted.pop("_id")
            
            return converted
        
        # Handle list
        if isinstance(obj, list):
            return [self._convert_objectids_and_ids(item) for item in obj]
        
        # Return as-is for primitives (str, int, float, bool, etc.)
        return obj
    
    def _model_to_document(self, model: T) -> Dict[str, Any]:
        """Convert a model instance to a MongoDB document.
        Persist with internal field names (not aliases) so booleans remain 'is*' in storage.
        """
        # Prefer Pydantic v2 JSON-friendly dump
        if hasattr(model, 'model_dump'):
            try:
                # mode='json' ensures enums, dates, and datetimes are serialized to JSON-safe values
                doc = model.model_dump(by_alias=False, mode='json')  # type: ignore[arg-type]
                return self._to_bson_safe(doc)
            except TypeError:
                # Fallback to python mode if running on older minor versions
                doc = model.model_dump(by_alias=False)
                return self._to_bson_safe(doc)
        # Pydantic v1 fallback: use JSON round-trip to coerce enums/dates
        if hasattr(model, 'dict') and hasattr(model, 'json'):
            try:
                json_str = model.json(by_alias=False, default=pydantic_encoder) if pydantic_encoder else model.json(by_alias=False)
                return self._to_bson_safe(json.loads(json_str))
            except Exception:
                return self._to_bson_safe(model.dict(by_alias=False))
        # Last resort
        return self._to_bson_safe(dict(model))

    def _to_bson_safe(self, obj: Any) -> Any:
        """Recursively convert objects to Mongo-safe JSON-friendly values.
        - date/datetime -> ISO string
        - Enum -> value (string)
        - set/tuple -> list
        - dict/list -> recurse
        """
        if obj is None:
            return None
        if isinstance(obj, (date, datetime)):
            # Always store as ISO strings per requirement
            try:
                return obj.isoformat()
            except Exception:
                return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (list, tuple, set)):
            return [self._to_bson_safe(i) for i in list(obj)]
        if isinstance(obj, dict):
            return {k: self._to_bson_safe(v) for k, v in obj.items()}
        return obj
    
    @staticmethod
    def _id_query(entity_id: Any) -> Dict[str, Any]:
        """
        Build a robust _id filter that matches both ObjectId and string forms.
        This helps when some collections store _id as ObjectId and others as string.
        """
        candidates = []
        # If already an ObjectId, just use it
        if isinstance(entity_id, ObjectId):
            candidates.append(entity_id)
        else:
            # If it's a valid hex string, include both ObjectId and the raw string
            try:
                if isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                    candidates.append(ObjectId(entity_id))
            except Exception:
                # Ignore invalid conversions
                pass
            # Always include the original value to cover string-stored _id
            candidates.append(entity_id)
        # Deduplicate while preserving types
        seen = set()
        unique_candidates = []
        for c in candidates:
            key = (type(c), str(c))
            if key not in seen:
                seen.add(key)
                unique_candidates.append(c)
        return {"_id": unique_candidates[0]} if len(unique_candidates) == 1 else {"_id": {"$in": unique_candidates}}
    
    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find a document by its ID."""
        doc = await self.collection.find_one(self._id_query(entity_id))
        return self._document_to_model(doc) if doc else None
    
    async def find_all(self, skip: int = 0, limit: int = None, sort: Optional[List[tuple]] = None) -> List[T]:
        """Find all documents with optional pagination and sorting."""
        cursor = self.collection.find({})
        
        if skip > 0:
            cursor = cursor.skip(skip)
        
        if limit is not None:
            cursor = cursor.limit(limit)
        
        if sort:
            cursor = cursor.sort(sort)
        
        return [self._document_to_model(doc) async for doc in cursor]
    
    async def find_by_filter(self, filter_dict: Dict[str, Any], 
                           skip: int = 0, limit: int = None, 
                           sort: Optional[List[tuple]] = None) -> List[T]:
        """Find documents by filter criteria."""
        cursor = self.collection.find(filter_dict)
        
        if skip > 0:
            cursor = cursor.skip(skip)
        
        if limit is not None:
            cursor = cursor.limit(limit)
        
        if sort:
            cursor = cursor.sort(sort)
        
        return [self._document_to_model(doc) async for doc in cursor]
    
    async def find_one_by_filter(self, filter_dict: Dict[str, Any]) -> Optional[T]:
        """Find a single document by filter criteria."""
        doc = await self.collection.find_one(filter_dict)
        return self._document_to_model(doc) if doc else None
    
    async def find_by_ids(self, entity_ids: List[str]) -> List[T]:
        """Find multiple documents by their IDs."""
        if not entity_ids:
            return []
        # Build a mixed list containing both ObjectIds and strings for robustness
        mixed_ids = []
        seen = set()
        for eid in entity_ids:
            query = self._id_query(eid)
            vals = query["_id"]["$in"] if isinstance(query["_id"], dict) else [query["_id"]]
            for v in vals:
                key = (type(v), str(v))
                if key not in seen:
                    seen.add(key)
                    mixed_ids.append(v)
        cursor = self.collection.find({"_id": {"$in": mixed_ids}})
        return [self._document_to_model(doc) async for doc in cursor]
    
    async def create(self, entity: T) -> T:
        """Create a new document."""
        doc = self._model_to_document(entity)
        result = await self.collection.insert_one(doc)

        # Update the entity with the inserted ID if it wasn't set
        if hasattr(entity, 'id') and entity.id is None:
            entity.id = str(result.inserted_id)
        elif hasattr(entity, '_id') and getattr(entity, '_id') is None:
            setattr(entity, '_id', str(result.inserted_id))

        return entity
    
    async def create_many(self, entities: List[T]) -> List[T]:
        """Create multiple documents."""
        docs = [self._model_to_document(entity) for entity in entities]
        result = await self.collection.insert_many(docs)

        # Update entities with inserted IDs
        for i, entity in enumerate(entities):
            if hasattr(entity, 'id') and entity.id is None:
                entity.id = str(result.inserted_ids[i])
            elif hasattr(entity, '_id') and getattr(entity, '_id') is None:
                setattr(entity, '_id', str(result.inserted_ids[i]))

        return entities
    
    async def save(self, entity: T) -> T:
        """
        Java-style save method: Create or update a document.
        If entity has an ID and exists, update it. Otherwise, create new.
        """
        doc = self._model_to_document(entity)
        entity_id = doc.get('_id') or doc.get('id')
        
        if entity_id and await self.exists_by_id(entity_id):
            # Update existing entity
            await self.update(entity)
            return entity
        else:
            # Create new entity
            return await self.create(entity)
    
    async def saveAll(self, entities: List[T]) -> List[T]:
        """
        Java-style camelCase method: Save multiple entities (create or update).
        """
        saved_entities = []
        for entity in entities:
            saved_entity = await self.save(entity)
            saved_entities.append(saved_entity)
        return saved_entities
    
    async def findById(self, entity_id: str) -> Optional[T]:
        """Java-style camelCase method: Find a document by its ID."""
        return await self.find_by_id(entity_id)
    
    async def findAll(self, skip: int = 0, limit: int = None, sort: Optional[List[tuple]] = None) -> List[T]:
        """Java-style camelCase method: Find all documents."""
        return await self.find_all(skip, limit, sort)
    
    async def existsById(self, entity_id: str) -> bool:
        """Java-style camelCase method: Check if a document exists by its ID."""
        return await self.exists_by_id(entity_id)
    
    # Additional camelCase aliases for Java consistency
    async def findByFilter(self, filter_dict: Dict[str, Any], 
                          skip: int = 0, limit: int = None, 
                          sort: Optional[List[tuple]] = None) -> List[T]:
        """Java-style camelCase method: Find documents by filter criteria."""
        return await self.find_by_filter(filter_dict, skip, limit, sort)
    
    async def findOneByFilter(self, filter_dict: Dict[str, Any]) -> Optional[T]:
        """Java-style camelCase method: Find a single document by filter criteria."""
        return await self.find_one_by_filter(filter_dict)
    
    async def findByIds(self, entity_ids: List[str]) -> List[T]:
        """Java-style camelCase method: Find multiple documents by their IDs."""
        return await self.find_by_ids(entity_ids)
    
    async def createMany(self, entities: List[T]) -> List[T]:
        """Java-style camelCase method: Create multiple documents."""
        return await self.create_many(entities)
    
    async def updateById(self, entity_id: str, update_dict: Dict[str, Any]) -> bool:
        """Java-style camelCase method: Update a document by its ID."""
        return await self.update_by_id(entity_id, update_dict)
    
    async def updateManyByFilter(self, filter_dict: Dict[str, Any], 
                               update_dict: Dict[str, Any]) -> int:
        """Java-style camelCase method: Update multiple documents by filter criteria."""
        return await self.update_many_by_filter(filter_dict, update_dict)
    
    async def deleteManyByFilter(self, filter_dict: Dict[str, Any]) -> int:
        """Java-style camelCase method: Delete multiple documents by filter criteria."""
        return await self.delete_many_by_filter(filter_dict)
    
    async def existsByFilter(self, filter_dict: Dict[str, Any]) -> bool:
        """Java-style camelCase method: Check if any document exists matching the filter criteria."""
        return await self.exists_by_filter(filter_dict)
    
    async def findByField(self, field_name: str, field_value: Any) -> List[T]:
        """Java-style camelCase method: Find documents by a specific field value."""
        return await self.find_by_field(field_name, field_value)
    
    async def findOneByField(self, field_name: str, field_value: Any) -> Optional[T]:
        """Java-style camelCase method: Find a single document by a specific field value."""
        return await self.find_one_by_field(field_name, field_value)
    
    async def findByFields(self, **kwargs) -> List[T]:
        """Java-style camelCase method: Find documents by multiple field values."""
        return await self.find_by_fields(**kwargs)
    
    async def findOneByFields(self, **kwargs) -> Optional[T]:
        """Java-style camelCase method: Find a single document by multiple field values."""
        return await self.find_one_by_fields(**kwargs)
    
    async def update_by_id(self, entity_id: str, update_dict: Dict[str, Any]) -> bool:
        """Update a document by its ID."""
        # Ensure update values are BSON safe
        update_dict = self._to_bson_safe(update_dict)
        result = await self.collection.update_one(
            self._id_query(entity_id),
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    async def update(self, entity: T) -> bool:
        """Update a document using the entity's ID."""
        doc = self._model_to_document(entity)
        entity_id = doc.get('_id') or doc.get('id')
        
        if not entity_id:
            raise ValueError("Entity must have an ID to be updated")

        # Remove ID from the update document
        update_doc = {k: v for k, v in doc.items() if k not in ['_id', 'id']}
        update_doc = self._to_bson_safe(update_doc)

        result = await self.collection.update_one(
            self._id_query(entity_id),
            {"$set": update_doc}
        )
        return result.modified_count > 0
    
    async def update_many_by_filter(self, filter_dict: Dict[str, Any], 
                                  update_dict: Dict[str, Any]) -> int:
        """Update multiple documents by filter criteria."""
        update_dict = self._to_bson_safe(update_dict)
        result = await self.collection.update_many(
            filter_dict,
            {"$set": update_dict}
        )
        return result.modified_count
    
    async def delete_by_id(self, entity_id: str) -> bool:
        """Delete a document by its ID."""
        result = await self.collection.delete_one(self._id_query(entity_id))
        return result.deleted_count > 0
    
    async def delete(self, entity: T) -> bool:
        """Delete a document using the entity's ID."""
        doc = self._model_to_document(entity)
        entity_id = doc.get('_id') or doc.get('id')
        
        if not entity_id:
            raise ValueError("Entity must have an ID to be deleted")
        
        return await self.delete_by_id(entity_id)
    
    async def deleteById(self, entity_id: str) -> bool:
        """Java-style camelCase method: Delete a document by its ID."""
        return await self.delete_by_id(entity_id)
    
    async def deleteAll(self, entities: List[T] = None) -> int:
        """
        Java-style camelCase method: Delete all documents or specific entities.
        If entities list is provided, delete only those entities.
        If no entities provided, delete all documents in collection.
        """
        if entities is None:
            # Delete all documents in collection
            result = await self.collection.delete_many({})
            return result.deleted_count
        else:
            # Delete specific entities by their IDs
            entity_ids = []
            for entity in entities:
                doc = self._model_to_document(entity)
                entity_id = doc.get('_id') or doc.get('id')
                if entity_id:
                    entity_ids.append(entity_id)
            
            if entity_ids:
                # Expand IDs to include both ObjectId and string representations
                mixed_ids = []
                seen = set()
                for eid in entity_ids:
                    query = self._id_query(eid)
                    vals = query["_id"]["$in"] if isinstance(query["_id"], dict) else [query["_id"]]
                    for v in vals:
                        key = (type(v), str(v))
                        if key not in seen:
                            seen.add(key)
                            mixed_ids.append(v)
                result = await self.collection.delete_many({"_id": {"$in": mixed_ids}})
                return result.deleted_count
            return 0
    
    async def delete_many_by_filter(self, filter_dict: Dict[str, Any]) -> int:
        """Delete multiple documents by filter criteria."""
        result = await self.collection.delete_many(filter_dict)
        return result.deleted_count
    
    async def count(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching the filter criteria."""
        if filter_dict is None:
            filter_dict = {}
        return await self.collection.count_documents(filter_dict)
    
    async def exists_by_id(self, entity_id: str) -> bool:
        """Check if a document exists by its ID."""
        count = await self.collection.count_documents(self._id_query(entity_id), limit=1)
        return count > 0
    
    async def exists_by_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """Check if any document exists matching the filter criteria."""
        count = await self.collection.count_documents(filter_dict, limit=1)
        return count > 0
    
    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute an aggregation pipeline."""
        cursor = self.collection.aggregate(pipeline)
        return [doc async for doc in cursor]
    
    async def distinct(self, field: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Get distinct values for a field."""
        if filter_dict is None:
            filter_dict = {}
        return await self.collection.distinct(field, filter_dict)
    
    # Common query helpers
    async def find_by_field(self, field_name: str, field_value: Any) -> List[T]:
        """Find documents by a specific field value."""
        return await self.find_by_filter({field_name: field_value})
    
    async def find_one_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """Find a single document by a specific field value."""
        return await self.find_one_by_filter({field_name: field_value})
    
    async def find_by_fields(self, **kwargs) -> List[T]:
        """Find documents by multiple field values."""
        return await self.find_by_filter(kwargs)
    
    async def find_one_by_fields(self, **kwargs) -> Optional[T]:
        """Find a single document by multiple field values."""
        return await self.find_one_by_filter(kwargs)
    
    # Sorting helpers
    @staticmethod
    def sort_asc(field: str) -> tuple:
        """Create ascending sort tuple."""
        return (field, ASCENDING)
    
    @staticmethod
    def sort_desc(field: str) -> tuple:
        """Create descending sort tuple."""
        return (field, DESCENDING)
    
    # Additional Java Spring Data style methods
    async def findAllById(self, entity_ids: List[str]) -> List[T]:
        """Java-style camelCase method: Find multiple documents by their IDs."""
        return await self.find_by_ids(entity_ids)
    
    async def countAll(self) -> int:
        """Java-style method: Count all documents in the collection."""
        return await self.count()
    
    async def deleteAllById(self, entity_ids: List[str]) -> int:
        """Java-style camelCase method: Delete multiple documents by their IDs."""
        if not entity_ids:
            return 0
        result = await self.collection.delete_many({"_id": {"$in": entity_ids}})
        return result.deleted_count
    
    async def saveAndFlush(self, entity: T) -> T:
        """
        Java-style method: Save entity and ensure it's immediately persisted.
        In MongoDB context, this is the same as save since MongoDB doesn't have transactions by default.
        """
        return await self.save(entity)
    
    async def flush(self):
        """
        Java-style method: Flush pending changes.
        In MongoDB context, this is a no-op since changes are immediately persisted.
        """
        pass
    
    async def getOne(self, entity_id: str) -> T:
        """
        Java-style method: Get one entity by ID (throws exception if not found).
        """
        entity = await self.findById(entity_id)
        if entity is None:
            raise ValueError(f"Entity with id {entity_id} not found")
        return entity
    
    async def getReferenceById(self, entity_id: str) -> T:
        """
        Java-style method: Get a reference to entity by ID.
        In MongoDB context, this is the same as findById.
        """
        return await self.findById(entity_id)
    
    # Query by example style methods
    async def findByExample(self, example: T) -> List[T]:
        """
        Find entities matching the non-null fields of the example entity.
        """
        doc = self._model_to_document(example)
        # Remove None values and empty lists/dicts
        filter_dict = {k: v for k, v in doc.items() 
                      if v is not None and v != [] and v != {} and k not in ['_id', 'id']}
        return await self.find_by_filter(filter_dict)
    
    async def findOneByExample(self, example: T) -> Optional[T]:
        """
        Find one entity matching the non-null fields of the example entity.
        """
        doc = self._model_to_document(example)
        filter_dict = {k: v for k, v in doc.items() 
                      if v is not None and v != [] and v != {} and k not in ['_id', 'id']}
        return await self.find_one_by_filter(filter_dict)
    
    # Batch operations
    async def insertAll(self, entities: List[T]) -> List[T]:
        """
        Insert multiple entities (create only, don't update existing).
        """
        return await self.create_many(entities)
    
    async def upsert(self, entity: T) -> T:
        """
        Upsert operation: Insert if not exists, update if exists.
        """
        return await self.save(entity)
    
    async def updateAll(self, entities: List[T]) -> List[T]:
        """
        Update multiple entities.
        """
        updated_entities = []
        for entity in entities:
            await self.update(entity)
            updated_entities.append(entity)
        return updated_entities
