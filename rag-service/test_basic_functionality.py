#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import asyncio
import json
from typing import List
import requests
import time

def test_service_startup():
    """Test if the RAG service can start without errors"""
    print("=== Testing Basic RAG Service Functionality ===\n")

    # Test 1: Basic imports
    print("1. Testing imports...")
    try:
        from app.core.config import settings
        from app.services.vector_service import vector_service
        print("✓ Core imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

    # Test 2: ChromaDB connection
    print("\n2. Testing ChromaDB connection...")
    try:
        # Unset proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        success = vector_service.connect()
        if success:
            print("✓ ChromaDB connection successful")

            # Test collection operations
            stats = vector_service.get_collection_stats()
            print(f"✓ Collection stats: {stats}")
        else:
            print("❌ ChromaDB connection failed")
            return False
    except Exception as e:
        print(f"❌ ChromaDB connection error: {e}")
        return False

    # Test 3: Basic document operations (without embedding)
    print("\n3. Testing basic document operations...")
    try:
        from app.models.requests import DocumentInput

        # Create test documents
        test_docs = [
            DocumentInput(
                id="test_doc_1",
                content="这是一个测试文档，包含股票分析内容。公司业绩良好，股价上涨。",
                metadata={
                    "doc_type": "test",
                    "stock_code": "000001",
                    "source": "test_source"
                }
            ),
            DocumentInput(
                id="test_doc_2",
                content="另一个测试文档，讨论市场趋势和投资策略。建议长期持有优质股票。",
                metadata={
                    "doc_type": "test",
                    "stock_code": "000002",
                    "source": "test_source"
                }
            )
        ]

        print(f"✓ Created {len(test_docs)} test documents")

        # Test embedding service (mock vectors for now)
        print("\n4. Testing mock embedding...")
        mock_embeddings = [
            [0.1] * 768,  # Mock 768-dim vector for doc 1
            [0.2] * 768   # Mock 768-dim vector for doc 2
        ]

        # Test vector storage
        processed_count, failed_docs = vector_service.add_documents(
            documents=test_docs,
            embeddings=mock_embeddings
        )

        print(f"✓ Stored documents - Success: {processed_count}, Failed: {len(failed_docs)}")

        # Test document retrieval
        doc = vector_service.get_document_by_id("test_doc_1")
        if doc:
            print(f"✓ Retrieved document: {doc.document_id[:20]}...")
        else:
            print("⚠ Document retrieval returned None")

        # Test collection stats after adding documents
        stats = vector_service.get_collection_stats()
        print(f"✓ Updated collection stats: {stats}")

        return True

    except Exception as e:
        print(f"❌ Document operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_text_processing():
    """Test text processing utilities"""
    print("\n=== Testing Text Processing ===")

    try:
        from app.utils.text_processing import clean_text, split_text_into_chunks, calculate_text_quality_score

        # Test text cleaning
        test_text = "<p>这是一个包含HTML标签的测试文本。</p>\n\n包含多余空白。"
        cleaned = clean_text(test_text)
        print(f"✓ Text cleaning: '{test_text[:30]}...' → '{cleaned[:30]}...'")

        # Test text chunking
        long_text = "这是一个很长的文本。" * 50  # Create a long text
        chunks = split_text_into_chunks(long_text, max_chunk_size=100, overlap_size=20)
        print(f"✓ Text chunking: {len(long_text)} chars → {len(chunks)} chunks")

        # Test quality scoring
        score = calculate_text_quality_score(cleaned)
        print(f"✓ Quality score: {score:.3f}")

        return True

    except Exception as e:
        print(f"❌ Text processing failed: {e}")
        return False

def test_database_connection():
    """Test database connection and models"""
    print("\n=== Testing Database Connection ===")

    try:
        from app.core.database import engine, BootstrapTask, BatchProcessingLog, DocumentQualityScore
        from sqlalchemy import text

        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ PostgreSQL connection successful")

        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure PostgreSQL is running and DATABASE_URL is correct")
        return False

def cleanup_test_data():
    """Clean up test data from ChromaDB"""
    print("\n=== Cleaning Up Test Data ===")
    try:
        from app.services.vector_service import vector_service

        # Try to delete test documents
        vector_service.delete_document("test_doc_1")
        vector_service.delete_document("test_doc_2")
        print("✓ Test documents cleaned up")

    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")

if __name__ == "__main__":
    print("🚀 Starting RAG Service Basic Functionality Test\n")

    tests = [
        ("Service Startup", test_service_startup),
        ("Text Processing", test_text_processing),
        ("Database Connection", test_database_connection)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)

        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name} - PASSED")
            else:
                print(f"\n❌ {test_name} - FAILED")
        except Exception as e:
            print(f"\n💥 {test_name} - CRASHED: {e}")

    # Cleanup
    cleanup_test_data()

    print(f"\n{'='*50}")
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    print('='*50)

    if passed == total:
        print("🎉 All basic tests passed!")
        print("✨ RAG Service core functionality is working")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        print("Check the error messages above")