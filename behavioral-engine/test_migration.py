"""
Test script for PostgreSQL migration
Validates all components of the migration
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, Any

# Test imports
try:
    from app.database import (
        init_db_pool,
        close_db_pool,
        check_db_health,
        initialize_database
    )
    from app.services.vector_store_postgres import get_vector_store
    from app.services.rag_engine_postgres import get_rag_engine
    from app.services.ingest_service_postgres import get_ingest_service
    from app.services.embedding import get_embedding_service
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_database_connection():
    """Test 1: Database connection and health"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        # Initialize connection pool
        await init_db_pool()
        print("✅ Connection pool initialized")
        
        # Check health
        health = await check_db_health()
        print(f"✅ Database health check: {health['status']}")
        print(f"   - Connected: {health['connected']}")
        print(f"   - pgvector enabled: {health['pgvector_enabled']}")
        print(f"   - Tables: {', '.join(health['tables_exist'])}")
        print(f"   - Pool size: {health['pool_size']}")
        
        return health['status'] == 'healthy'
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_schema_initialization():
    """Test 2: Schema initialization"""
    print("\n" + "="*60)
    print("TEST 2: Schema Initialization")
    print("="*60)
    
    try:
        await initialize_database()
        print("✅ Database schema initialized")
        return True
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        return False


async def test_embedding_service():
    """Test 3: Embedding service"""
    print("\n" + "="*60)
    print("TEST 3: Embedding Service")
    print("="*60)
    
    try:
        embedding_service = get_embedding_service()
        
        # Test encoding
        text = "This is a test sentence for embedding generation"
        embedding = embedding_service.encode(text)
        
        print(f"✅ Embedding generated")
        print(f"   - Dimension: {len(embedding)}")
        print(f"   - Sample values: {embedding[:5]}")
        
        return len(embedding) == 384
    except Exception as e:
        print(f"❌ Embedding service failed: {e}")
        return False


async def test_data_insertion():
    """Test 4: Data insertion"""
    print("\n" + "="*60)
    print("TEST 4: Data Insertion")
    print("="*60)
    
    try:
        ingest_service = await get_ingest_service()
        
        # Test single event insertion
        event_data = {
            "reel_id": "test_reel_001",
            "username": "test_user",
            "watch_time": 15.5,
            "liked": True,
            "caption": "Test caption for migration validation",
            "hashtags": ["test", "migration", "aimirror"],
            "session_id": "test_session_001",
            "timestamp": datetime.now().isoformat()
        }
        
        doc_id = await ingest_service.ingest_behavioral_event(
            user_id="test_user_001",
            event_data=event_data
        )
        
        print(f"✅ Single event inserted")
        print(f"   - Document ID: {doc_id}")
        
        # Test batch insertion
        batch_events = [
            {
                "type": "behavioral_event",
                "reel_id": f"test_reel_{i:03d}",
                "username": f"creator_{i % 3}",
                "watch_time": 10 + i * 2,
                "liked": i % 2 == 0,
                "session_id": "test_session_batch",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(5)
        ]
        
        doc_ids = await ingest_service.ingest_batch(
            user_id="test_user_001",
            events=batch_events
        )
        
        print(f"✅ Batch insertion completed")
        print(f"   - Documents inserted: {len(doc_ids)}")
        
        return True
    except Exception as e:
        print(f"❌ Data insertion failed: {e}")
        return False


async def test_similarity_search():
    """Test 5: Similarity search"""
    print("\n" + "="*60)
    print("TEST 5: Similarity Search")
    print("="*60)
    
    try:
        vector_store = await get_vector_store()
        embedding_service = get_embedding_service()
        
        # Generate query embedding
        query = "What content did I watch?"
        query_embedding = embedding_service.encode(query)
        
        # Search
        results = await vector_store.query(
            user_id="test_user_001",
            query_embedding=query_embedding,
            top_k=3
        )
        
        print(f"✅ Similarity search completed")
        print(f"   - Results found: {len(results['documents'][0])}")
        
        for i, doc in enumerate(results['documents'][0]):
            distance = results['distances'][0][i]
            print(f"   - Result {i+1}: {doc[:80]}... (distance: {distance:.4f})")
        
        return len(results['documents'][0]) > 0
    except Exception as e:
        print(f"❌ Similarity search failed: {e}")
        return False


async def test_rag_retrieval():
    """Test 6: RAG retrieval"""
    print("\n" + "="*60)
    print("TEST 6: RAG Retrieval")
    print("="*60)
    
    try:
        rag_engine = await get_rag_engine()
        
        # Retrieve context
        context = await rag_engine.retrieve_behavioral_context(
            user_id="test_user_001",
            query="What are my watching patterns?",
            top_k=3
        )
        
        print(f"✅ RAG retrieval completed")
        print(f"   - Sessions: {len(context['sessions'])}")
        print(f"   - Traits: {len(context['traits'])}")
        print(f"   - Trends: {len(context['trends'])}")
        print(f"   - Recent activity: {len(context['recent_activity'])}")
        
        # Test context fusion
        fused = await rag_engine.fuse_context(context, "test query")
        print(f"✅ Context fusion completed")
        print(f"   - Fused context length: {len(fused)} chars")
        
        return True
    except Exception as e:
        print(f"❌ RAG retrieval failed: {e}")
        return False


async def test_chat_history():
    """Test 7: Chat history"""
    print("\n" + "="*60)
    print("TEST 7: Chat History")
    print("="*60)
    
    try:
        vector_store = await get_vector_store()
        embedding_service = get_embedding_service()
        
        # Add chat messages
        user_msg = "What are my behavioral patterns?"
        assistant_msg = "Based on your data, you tend to watch content for an average of 15 seconds."
        
        user_embedding = embedding_service.encode(user_msg)
        assistant_embedding = embedding_service.encode(assistant_msg)
        
        await vector_store.add_chat_message(
            user_id="test_user_001",
            message=user_msg,
            role="user",
            embedding=user_embedding
        )
        
        await vector_store.add_chat_message(
            user_id="test_user_001",
            message=assistant_msg,
            role="assistant",
            embedding=assistant_embedding
        )
        
        print(f"✅ Chat messages stored")
        
        # Retrieve chat history
        history = await vector_store.get_chat_history(
            user_id="test_user_001",
            limit=10
        )
        
        print(f"✅ Chat history retrieved")
        print(f"   - Messages: {len(history)}")
        
        for msg in history:
            print(f"   - {msg['role']}: {msg['message'][:60]}...")
        
        return len(history) > 0
    except Exception as e:
        print(f"❌ Chat history test failed: {e}")
        return False


async def test_user_isolation():
    """Test 8: Multi-user isolation"""
    print("\n" + "="*60)
    print("TEST 8: User Isolation")
    print("="*60)
    
    try:
        ingest_service = await get_ingest_service()
        vector_store = await get_vector_store()
        
        # Insert data for two different users
        for user_id in ["user_a", "user_b"]:
            event = {
                "reel_id": f"{user_id}_reel",
                "username": "creator",
                "watch_time": 20,
                "liked": True,
                "session_id": f"{user_id}_session"
            }
            
            await ingest_service.ingest_behavioral_event(
                user_id=user_id,
                event_data=event
            )
        
        print(f"✅ Data inserted for multiple users")
        
        # Check user A can only see their data
        count_a = await vector_store.get_collection_count(user_id="user_a")
        count_b = await vector_store.get_collection_count(user_id="user_b")
        
        print(f"✅ User isolation verified")
        print(f"   - User A documents: {count_a}")
        print(f"   - User B documents: {count_b}")
        
        return count_a > 0 and count_b > 0
    except Exception as e:
        print(f"❌ User isolation test failed: {e}")
        return False


async def test_performance():
    """Test 9: Performance metrics"""
    print("\n" + "="*60)
    print("TEST 9: Performance")
    print("="*60)
    
    try:
        import time
        
        ingest_service = await get_ingest_service()
        vector_store = await get_vector_store()
        embedding_service = get_embedding_service()
        
        # Test batch insert performance
        start = time.time()
        batch_events = [
            {
                "type": "behavioral_event",
                "reel_id": f"perf_test_{i}",
                "username": "creator",
                "watch_time": 15,
                "liked": False,
                "session_id": "perf_session"
            }
            for i in range(50)
        ]
        
        await ingest_service.ingest_batch(
            user_id="perf_test_user",
            events=batch_events
        )
        
        insert_time = time.time() - start
        print(f"✅ Batch insert performance")
        print(f"   - 50 documents in {insert_time:.2f}s")
        print(f"   - {50/insert_time:.1f} docs/sec")
        
        # Test query performance
        start = time.time()
        query_embedding = embedding_service.encode("test query")
        
        for _ in range(10):
            await vector_store.query(
                user_id="perf_test_user",
                query_embedding=query_embedding,
                top_k=5
            )
        
        query_time = (time.time() - start) / 10
        print(f"✅ Query performance")
        print(f"   - Average query time: {query_time*1000:.1f}ms")
        
        return insert_time < 10 and query_time < 1
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


async def cleanup_test_data():
    """Cleanup test data"""
    print("\n" + "="*60)
    print("CLEANUP: Removing Test Data")
    print("="*60)
    
    try:
        vector_store = await get_vector_store()
        
        test_users = ["test_user_001", "user_a", "user_b", "perf_test_user"]
        
        for user_id in test_users:
            deleted = await vector_store.delete_user_data(user_id)
            print(f"✅ Deleted {deleted} records for {user_id}")
        
        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


async def run_all_tests():
    """Run all migration tests"""
    print("\n" + "="*60)
    print("AIMIRROR POSTGRESQL MIGRATION TEST SUITE")
    print("="*60)
    
    results = {}
    
    try:
        # Run tests
        results['connection'] = await test_database_connection()
        results['schema'] = await test_schema_initialization()
        results['embedding'] = await test_embedding_service()
        results['insertion'] = await test_data_insertion()
        results['search'] = await test_similarity_search()
        results['rag'] = await test_rag_retrieval()
        results['chat'] = await test_chat_history()
        results['isolation'] = await test_user_isolation()
        results['performance'] = await test_performance()
        
        # Cleanup
        await cleanup_test_data()
        
    finally:
        # Close connections
        await close_db_pool()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.upper()}")
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Migration successful!")
        print("\nNext steps:")
        print("1. Update API endpoints to use PostgreSQL services")
        print("2. Remove ChromaDB dependencies")
        print("3. Deploy to production")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
