#!/usr/bin/env python3
"""
RAG交互式查询工具
类似数据库查询界面，支持实时查看和搜索RAG库
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import chromadb
import json
import time
from datetime import datetime

class RAGQueryTool:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.collection = None
        self.connected = False

    def connect(self):
        """连接到RAG数据库"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()
            self.collection = self.client.get_collection("financial_documents")
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    def show_status(self):
        """显示数据库状态"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        try:
            count = self.collection.count()
            print(f"\n📊 RAG数据库状态:")
            print(f"   集合: financial_documents")
            print(f"   文档数: {count}")
            print(f"   状态: {'✅ 正常' if count > 0 else '⚠️ 空集合'}")
            print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")

    def list_documents(self, limit=10):
        """列出文档"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        try:
            results = self.collection.get(
                limit=limit,
                include=['documents', 'metadatas']
            )

            print(f"\n📋 文档列表 (前{limit}个):")
            print("-" * 80)

            for i, doc_id in enumerate(results['ids']):
                doc = results['documents'][i] if results['documents'] else 'No content'
                metadata = results['metadatas'][i] if results['metadatas'] else {}

                doc_type = metadata.get('doc_type', '未知')
                source = metadata.get('source', '未知')
                importance = metadata.get('importance', 'N/A')

                print(f"{i+1:2d}. 📄 {doc_id}")
                print(f"    类型: {doc_type} | 来源: {source} | 重要性: {importance}")
                print(f"    内容: {doc[:100]}{'...' if len(doc) > 100 else ''}")
                print("-" * 80)

        except Exception as e:
            print(f"❌ 列出文档失败: {e}")

    def search_by_keyword(self, keyword, limit=5):
        """按关键词搜索"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        try:
            start_time = time.time()
            results = self.collection.get(include=['documents', 'metadatas'])

            matching_docs = []
            for i, doc in enumerate(results['documents']):
                if keyword.lower() in doc.lower():
                    matching_docs.append({
                        'id': results['ids'][i],
                        'content': doc,
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })

            search_time = time.time() - start_time

            print(f"\n🔍 搜索结果: '{keyword}'")
            print(f"   耗时: {search_time:.3f} 秒")
            print(f"   找到: {len(matching_docs)} 个文档")
            print("-" * 80)

            for i, match in enumerate(matching_docs[:limit]):
                metadata = match['metadata']
                doc_type = metadata.get('doc_type', '未知')
                source = metadata.get('source', '未知')

                print(f"{i+1}. 📄 {match['id']}")
                print(f"   类型: {doc_type} | 来源: {source}")
                print(f"   内容: {match['content']}")
                print("-" * 60)

        except Exception as e:
            print(f"❌ 搜索失败: {e}")

    def filter_by_type(self, doc_type):
        """按文档类型过滤"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        try:
            results = self.collection.get(include=['documents', 'metadatas'])

            filtered_docs = []
            for i, metadata in enumerate(results['metadatas']):
                if metadata and metadata.get('doc_type') == doc_type:
                    filtered_docs.append({
                        'id': results['ids'][i],
                        'content': results['documents'][i],
                        'metadata': metadata
                    })

            print(f"\n📁 文档类型: '{doc_type}'")
            print(f"   找到: {len(filtered_docs)} 个文档")
            print("-" * 80)

            for i, doc in enumerate(filtered_docs):
                metadata = doc['metadata']
                source = metadata.get('source', '未知')
                publish_date = metadata.get('publish_date', '未知')

                print(f"{i+1}. 📄 {doc['id']}")
                print(f"   来源: {source} | 日期: {publish_date}")
                print(f"   内容: {doc['content'][:150]}{'...' if len(doc['content']) > 150 else ''}")
                print("-" * 60)

        except Exception as e:
            print(f"❌ 过滤失败: {e}")

    def show_document_detail(self, doc_id):
        """显示文档详情"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        try:
            results = self.collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas', 'embeddings']
            )

            if not results['ids']:
                print(f"❌ 未找到文档: {doc_id}")
                return

            doc = results['documents'][0]
            metadata = results['metadatas'][0] if results['metadatas'] else {}
            embedding_dim = len(results['embeddings'][0]) if results['embeddings'] and results['embeddings'][0] else 0

            print(f"\n📄 文档详情: {doc_id}")
            print("=" * 80)
            print(f"📝 内容:\n{doc}")
            print(f"\n🧮 向量维度: {embedding_dim}")
            print(f"\n🏷️  元数据:")
            for key, value in metadata.items():
                print(f"   {key}: {value}")

        except Exception as e:
            print(f"❌ 获取文档详情失败: {e}")

    def interactive_mode(self):
        """交互模式"""
        print("🎛️  RAG交互式查询工具")
        print("=" * 60)

        if not self.connect():
            print("❌ 无法连接到RAG数据库")
            return

        print("✅ 成功连接到RAG数据库")

        while True:
            print(f"\n{'='*50}")
            print("🔍 RAG查询工具 - 选择操作:")
            print("="*50)
            print("1. 📊 显示数据库状态")
            print("2. 📋 列出所有文档")
            print("3. 🔍 关键词搜索")
            print("4. 📁 按类型过滤")
            print("5. 📄 查看文档详情")
            print("6. 🔄 刷新连接")
            print("0. 🚪 退出")
            print("-" * 50)

            try:
                choice = input("请选择 (0-6): ").strip()

                if choice == '0':
                    print("👋 再见!")
                    break

                elif choice == '1':
                    self.show_status()

                elif choice == '2':
                    try:
                        limit = int(input("显示文档数量 (默认10): ") or "10")
                        self.list_documents(limit)
                    except ValueError:
                        self.list_documents()

                elif choice == '3':
                    keyword = input("输入搜索关键词: ").strip()
                    if keyword:
                        try:
                            limit = int(input("最大结果数 (默认5): ") or "5")
                            self.search_by_keyword(keyword, limit)
                        except ValueError:
                            self.search_by_keyword(keyword)

                elif choice == '4':
                    print("\n📁 可用文档类型:")
                    print("   - quarterly_analysis (季度分析)")
                    print("   - policy_news (政策新闻)")
                    print("   - sector_research (行业研究)")
                    print("   - market_analysis (市场分析)")
                    print("   - company_news (公司新闻)")

                    doc_type = input("输入文档类型: ").strip()
                    if doc_type:
                        self.filter_by_type(doc_type)

                elif choice == '5':
                    doc_id = input("输入文档ID: ").strip()
                    if doc_id:
                        self.show_document_detail(doc_id)

                elif choice == '6':
                    print("🔄 重新连接...")
                    self.connect()

                else:
                    print("❌ 无效选择")

            except KeyboardInterrupt:
                print("\n\n👋 再见!")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")

def main():
    print("🎯 RAG交互式查询工具")
    print("支持实时查看和搜索RAG向量数据库")
    print("-" * 60)

    tool = RAGQueryTool()
    tool.interactive_mode()

if __name__ == "__main__":
    main()