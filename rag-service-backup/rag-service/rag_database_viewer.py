#!/usr/bin/env python3
"""
RAG数据库内容查看器
类似于pgAdmin的界面，用于查看ChromaDB中的向量数据
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import chromadb
import json
from datetime import datetime
import time

class RAGDatabaseViewer:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.connected = False

    def connect(self):
        """连接到ChromaDB"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            # Test connection
            self.client.heartbeat()
            self.connected = True
            print("✅ 成功连接到ChromaDB")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    def show_database_overview(self):
        """显示数据库概览"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        print("\n" + "="*80)
        print("📊 RAG数据库概览")
        print("="*80)

        try:
            collections = self.client.list_collections()
            print(f"🗂️  集合总数: {len(collections)}")

            total_documents = 0
            for collection in collections:
                count = collection.count()
                total_documents += count
                print(f"   📁 {collection.name}: {count} 个文档")

            print(f"📄 文档总数: {total_documents}")
            print(f"🕐 查看时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f"❌ 获取概览失败: {e}")

    def list_collections(self):
        """列出所有集合"""
        if not self.connected:
            return []

        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except:
            return []

    def show_collection_details(self, collection_name):
        """显示集合详细信息"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        print(f"\n{'='*80}")
        print(f"📁 集合详情: {collection_name}")
        print("="*80)

        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()

            print(f"📊 基本信息:")
            print(f"   集合名称: {collection_name}")
            print(f"   文档数量: {count}")

            if count > 0:
                # 获取所有文档（如果数量不多）或者样本
                limit = min(count, 50)  # 最多显示50个文档

                results = collection.get(
                    limit=limit,
                    include=['documents', 'metadatas', 'embeddings']
                )

                print(f"\n📋 文档列表 (显示前{limit}个):")
                print("-" * 80)

                for i, doc_id in enumerate(results['ids']):
                    doc = results['documents'][i] if results['documents'] else 'No content'
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    embedding_dim = len(results['embeddings'][i]) if results['embeddings'] and results['embeddings'][i] else 0

                    print(f"\n{i+1}. 📄 ID: {doc_id}")
                    print(f"   📝 内容: {doc[:100]}{'...' if len(doc) > 100 else ''}")
                    print(f"   🏷️  元数据: {json.dumps(metadata, ensure_ascii=False, indent=6)}")
                    print(f"   🧮 向量维度: {embedding_dim}")
                    print("-" * 60)

                # 元数据统计
                self._show_metadata_stats(results['metadatas'])

        except Exception as e:
            print(f"❌ 获取集合详情失败: {e}")

    def _show_metadata_stats(self, metadatas):
        """显示元数据统计"""
        if not metadatas:
            return

        print(f"\n📈 元数据统计:")

        # 统计各字段
        field_stats = {}
        for metadata in metadatas:
            if metadata:
                for key, value in metadata.items():
                    if key not in field_stats:
                        field_stats[key] = {}

                    value_str = str(value)
                    if value_str not in field_stats[key]:
                        field_stats[key][value_str] = 0
                    field_stats[key][value_str] += 1

        for field, values in field_stats.items():
            print(f"\n   🏷️  {field}:")
            for value, count in sorted(values.items(), key=lambda x: x[1], reverse=True):
                print(f"      {value}: {count} 次")

    def search_documents(self, collection_name, query_text, limit=10):
        """搜索文档"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        print(f"\n{'='*80}")
        print(f"🔍 搜索结果: '{query_text}'")
        print(f"📁 集合: {collection_name}")
        print("="*80)

        try:
            collection = self.client.get_collection(collection_name)

            # 简单的文本搜索（基于内容匹配）
            all_results = collection.get(include=['documents', 'metadatas'])

            matching_docs = []
            for i, doc in enumerate(all_results['documents']):
                if query_text.lower() in doc.lower():
                    matching_docs.append({
                        'id': all_results['ids'][i],
                        'content': doc,
                        'metadata': all_results['metadatas'][i] if all_results['metadatas'] else {}
                    })

            print(f"📊 找到 {len(matching_docs)} 个匹配文档:")

            for i, doc in enumerate(matching_docs[:limit]):
                print(f"\n{i+1}. 📄 {doc['id']}")
                print(f"   📝 {doc['content'][:200]}{'...' if len(doc['content']) > 200 else ''}")
                print(f"   🏷️  {json.dumps(doc['metadata'], ensure_ascii=False)}")
                print("-" * 60)

        except Exception as e:
            print(f"❌ 搜索失败: {e}")

    def export_collection_to_json(self, collection_name, output_file=None):
        """导出集合到JSON文件"""
        if not self.connected:
            print("❌ 未连接到数据库")
            return

        try:
            collection = self.client.get_collection(collection_name)
            results = collection.get(include=['documents', 'metadatas', 'embeddings'])

            export_data = {
                'collection_name': collection_name,
                'export_time': datetime.now().isoformat(),
                'document_count': len(results['ids']),
                'documents': []
            }

            for i, doc_id in enumerate(results['ids']):
                doc_data = {
                    'id': doc_id,
                    'content': results['documents'][i] if results['documents'] else '',
                    'metadata': results['metadatas'][i] if results['metadatas'] else {},
                    'embedding_dimension': len(results['embeddings'][i]) if results['embeddings'] and results['embeddings'][i] else 0
                }
                export_data['documents'].append(doc_data)

            if not output_file:
                output_file = f"rag_export_{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 成功导出到文件: {output_file}")
            print(f"📊 导出了 {len(results['ids'])} 个文档")

        except Exception as e:
            print(f"❌ 导出失败: {e}")

    def interactive_mode(self):
        """交互式模式"""
        if not self.connect():
            return

        while True:
            print(f"\n{'='*60}")
            print("🎛️  RAG数据库查看器 - 交互模式")
            print("="*60)
            print("1. 📊 显示数据库概览")
            print("2. 📁 查看集合详情")
            print("3. 🔍 搜索文档")
            print("4. 💾 导出集合")
            print("5. 🔄 刷新连接")
            print("0. 🚪 退出")
            print("-" * 60)

            try:
                choice = input("请选择操作 (0-5): ").strip()

                if choice == '0':
                    print("👋 再见!")
                    break
                elif choice == '1':
                    self.show_database_overview()
                elif choice == '2':
                    collections = self.list_collections()
                    if not collections:
                        print("❌ 没有找到集合")
                        continue

                    print("\n📁 可用集合:")
                    for i, col in enumerate(collections):
                        print(f"   {i+1}. {col}")

                    try:
                        col_choice = int(input("选择集合 (输入序号): ")) - 1
                        if 0 <= col_choice < len(collections):
                            self.show_collection_details(collections[col_choice])
                        else:
                            print("❌ 无效选择")
                    except ValueError:
                        print("❌ 请输入有效数字")

                elif choice == '3':
                    collections = self.list_collections()
                    if not collections:
                        print("❌ 没有找到集合")
                        continue

                    print("\n📁 可用集合:")
                    for i, col in enumerate(collections):
                        print(f"   {i+1}. {col}")

                    try:
                        col_choice = int(input("选择集合 (输入序号): ")) - 1
                        if 0 <= col_choice < len(collections):
                            query = input("输入搜索关键词: ").strip()
                            if query:
                                self.search_documents(collections[col_choice], query)
                        else:
                            print("❌ 无效选择")
                    except ValueError:
                        print("❌ 请输入有效数字")

                elif choice == '4':
                    collections = self.list_collections()
                    if not collections:
                        print("❌ 没有找到集合")
                        continue

                    print("\n📁 可用集合:")
                    for i, col in enumerate(collections):
                        print(f"   {i+1}. {col}")

                    try:
                        col_choice = int(input("选择要导出的集合 (输入序号): ")) - 1
                        if 0 <= col_choice < len(collections):
                            self.export_collection_to_json(collections[col_choice])
                        else:
                            print("❌ 无效选择")
                    except ValueError:
                        print("❌ 请输入有效数字")

                elif choice == '5':
                    print("🔄 重新连接...")
                    self.connect()
                else:
                    print("❌ 无效选择，请输入 0-5")

            except KeyboardInterrupt:
                print("\n\n👋 再见!")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")

def main():
    print("🎛️  RAG数据库查看器")
    print("类似于pgAdmin的ChromaDB查看工具")
    print("="*60)

    viewer = RAGDatabaseViewer()

    # 提供命令行参数选项
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if not viewer.connect():
            return

        if command == 'overview':
            viewer.show_database_overview()
        elif command == 'collections':
            collections = viewer.list_collections()
            print(f"📁 可用集合: {collections}")
        elif command == 'export' and len(sys.argv) > 2:
            collection_name = sys.argv[2]
            viewer.export_collection_to_json(collection_name)
        else:
            print("❌ 未知命令")
            print("可用命令: overview, collections, export <collection_name>")
    else:
        # 启动交互模式
        viewer.interactive_mode()

if __name__ == "__main__":
    main()