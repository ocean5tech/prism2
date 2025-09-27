#!/usr/bin/env python3
"""
验证ChromaDB数据库状态和向量数据
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import chromadb
import json

def verify_chromadb_state():
    """验证ChromaDB状态和数据"""
    print("🔍 ChromaDB 数据库状态验证")
    print("=" * 50)

    # Clear proxy variables
    for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if proxy_var in os.environ:
            del os.environ[proxy_var]

    try:
        # Connect to ChromaDB
        client = chromadb.HttpClient(host='localhost', port=8000)
        print("✓ ChromaDB连接成功")

        # List all collections
        collections = client.list_collections()
        print(f"\n📚 集合总数: {len(collections)}")

        for collection in collections:
            print(f"\n🗂️  集合: {collection.name}")

            # Get collection stats
            count = collection.count()
            print(f"  文档数量: {count}")

            if count > 0:
                # Get a few sample documents
                results = collection.get(limit=5, include=['documents', 'metadatas', 'embeddings'])

                print(f"  📄 样本文档 (前5个):")
                for i, doc_id in enumerate(results['ids']):
                    doc_content = results['documents'][i] if results['documents'] else 'No content'
                    doc_meta = results['metadatas'][i] if results['metadatas'] else {}
                    embedding_dim = len(results['embeddings'][i]) if results['embeddings'] and results['embeddings'][i] else 0

                    print(f"    {i+1}. ID: {doc_id}")
                    print(f"       内容: {doc_content[:80]}{'...' if len(doc_content) > 80 else ''}")
                    print(f"       元数据: {json.dumps(doc_meta, ensure_ascii=False, indent=8)}")
                    print(f"       向量维度: {embedding_dim}")
                    print()

                # Test a sample query
                if results['embeddings'] and results['embeddings'][0]:
                    print("  🔍 测试查询 (使用第一个文档的向量):")
                    query_results = collection.query(
                        query_embeddings=[results['embeddings'][0]],
                        n_results=3,
                        include=['documents', 'distances', 'metadatas']
                    )

                    print(f"    查询结果数量: {len(query_results['ids'][0])}")
                    for j, result_id in enumerate(query_results['ids'][0]):
                        distance = query_results['distances'][0][j]
                        similarity = 1 - distance
                        print(f"      {j+1}. {result_id} (相似度: {similarity:.4f})")

        print("\n" + "=" * 50)
        print("✅ ChromaDB状态验证完成")
        return True

    except Exception as e:
        print(f"❌ ChromaDB验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_operations():
    """测试向量操作"""
    print("\n🧮 向量操作测试")
    print("=" * 30)

    try:
        client = chromadb.HttpClient(host='localhost', port=8000)
        collection_name = "test_vector_ops"

        # Create test collection
        try:
            collection = client.get_collection(collection_name)
            client.delete_collection(collection_name)
            print(f"✓ 删除已存在的测试集合")
        except:
            pass

        collection = client.create_collection(collection_name)
        print(f"✓ 创建测试集合: {collection_name}")

        # Test data
        test_vectors = [
            [0.1] * 768,  # Vector 1
            [0.2] * 768,  # Vector 2
            [0.3] * 768,  # Vector 3
        ]

        test_documents = [
            "这是第一个测试文档，讨论股票市场分析。",
            "第二个文档关于货币政策对经济的影响。",
            "第三个文档分析科技行业的投资机会。"
        ]

        test_metadata = [
            {"type": "market_analysis", "importance": 8},
            {"type": "policy_news", "importance": 9},
            {"type": "sector_research", "importance": 7}
        ]

        test_ids = ["test_vec_1", "test_vec_2", "test_vec_3"]

        # Add vectors
        collection.add(
            embeddings=test_vectors,
            documents=test_documents,
            metadatas=test_metadata,
            ids=test_ids
        )
        print(f"✓ 添加了 {len(test_vectors)} 个测试向量")

        # Verify count
        count = collection.count()
        print(f"✓ 集合文档数量: {count}")

        # Test similarity search
        query_vector = [0.15] * 768  # Between vector 1 and 2
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=3,
            include=['documents', 'distances', 'metadatas']
        )

        print(f"✓ 查询测试:")
        for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
            similarity = 1 - distance
            print(f"  {i+1}. {doc_id}: 相似度 {similarity:.4f}")

        # Cleanup
        client.delete_collection(collection_name)
        print(f"✓ 清理测试集合")

        return True

    except Exception as e:
        print(f"❌ 向量操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 ChromaDB 数据库完整性验证\n")

    # Test 1: Verify database state
    state_ok = verify_chromadb_state()

    # Test 2: Test vector operations
    vector_ok = test_vector_operations()

    print("\n" + "=" * 60)
    print("📊 验证总结:")
    print(f"  数据库状态: {'✅ 正常' if state_ok else '❌ 异常'}")
    print(f"  向量操作: {'✅ 正常' if vector_ok else '❌ 异常'}")

    if state_ok and vector_ok:
        print("\n🎉 ChromaDB 数据库功能完全正常!")
        print("✨ RAG Service 向量化存储系统已就绪")
    else:
        print("\n⚠️  发现问题，请检查上述错误信息")