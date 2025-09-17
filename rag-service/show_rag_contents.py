#!/usr/bin/env python3
"""
显示RAG库详细内容
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import chromadb
import json
from datetime import datetime

def show_rag_contents():
    """显示RAG库详细内容"""
    print("📊 RAG数据库内容详细报告")
    print("=" * 80)

    # Clear proxy variables
    for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if proxy_var in os.environ:
            del os.environ[proxy_var]

    try:
        # Connect to ChromaDB
        client = chromadb.HttpClient(host='localhost', port=8000)
        client.heartbeat()
        print("✅ 成功连接到ChromaDB")

        # Get collection
        collection = client.get_collection("financial_documents")
        count = collection.count()

        print(f"\n🗂️  集合: financial_documents")
        print(f"📄 文档总数: {count}")
        print(f"🕐 查看时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if count > 0:
            # Get all documents
            results = collection.get(
                include=['documents', 'metadatas', 'embeddings']
            )

            print(f"\n📋 所有文档详情:")
            print("=" * 80)

            for i, doc_id in enumerate(results['ids']):
                doc_content = results['documents'][i] if results['documents'] else 'No content'
                metadata = results['metadatas'][i] if results['metadatas'] else {}
                embedding_dim = len(results['embeddings'][i]) if results['embeddings'] is not None and i < len(results['embeddings']) and results['embeddings'][i] is not None else 0

                print(f"\n📄 文档 {i+1}: {doc_id}")
                print("-" * 60)
                print(f"📝 内容: {doc_content}")
                print(f"🧮 向量维度: {embedding_dim}")
                print(f"🏷️  元数据:")
                for key, value in metadata.items():
                    print(f"   {key}: {value}")

            # Show metadata statistics
            print(f"\n📈 元数据统计:")
            print("=" * 40)

            # Count by document type
            doc_types = {}
            sources = {}
            importance_levels = []

            for metadata in results['metadatas']:
                if metadata:
                    # Document types
                    doc_type = metadata.get('doc_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

                    # Sources
                    source = metadata.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1

                    # Importance levels
                    importance = metadata.get('importance')
                    if importance:
                        importance_levels.append(importance)

            print(f"📊 按文档类型分布:")
            for doc_type, count in sorted(doc_types.items()):
                print(f"   {doc_type}: {count} 个文档")

            print(f"\n📊 按来源分布:")
            for source, count in sorted(sources.items()):
                print(f"   {source}: {count} 个文档")

            if importance_levels:
                avg_importance = sum(importance_levels) / len(importance_levels)
                print(f"\n📊 重要性统计:")
                print(f"   平均重要性: {avg_importance:.1f}")
                print(f"   最高重要性: {max(importance_levels)}")
                print(f"   最低重要性: {min(importance_levels)}")

            # Test semantic search
            print(f"\n🔍 语义搜索测试:")
            print("=" * 40)

            test_queries = [
                ("银行", "查找银行相关文档"),
                ("政策", "查找政策相关文档"),
                ("人工智能", "查找AI相关文档")
            ]

            for query_term, description in test_queries:
                print(f"\n🔍 搜索: '{query_term}' ({description})")

                # Simple text-based search
                matching_docs = []
                for i, doc in enumerate(results['documents']):
                    if query_term in doc:
                        matching_docs.append({
                            'id': results['ids'][i],
                            'content': doc[:100] + '...' if len(doc) > 100 else doc,
                            'metadata': results['metadatas'][i]
                        })

                print(f"   📊 找到 {len(matching_docs)} 个匹配文档:")
                for j, match in enumerate(matching_docs[:3]):  # Show top 3
                    print(f"      {j+1}. {match['id']}")
                    print(f"         {match['content']}")

        else:
            print("❌ 集合为空，没有文档")

        return True

    except Exception as e:
        print(f"❌ 查看RAG库内容失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    show_rag_contents()