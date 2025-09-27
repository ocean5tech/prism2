#!/usr/bin/env python3
"""
获取ChromaDB基线数据
"""
import chromadb
import json
from datetime import datetime

def get_chromadb_baseline():
    try:
        # 连接到ChromaDB服务
        client = chromadb.HttpClient(host="localhost", port=8000)

        # 获取所有集合
        collections = client.list_collections()

        baseline_data = {
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "total_collections": len(collections),
            "collections": {}
        }

        # 获取每个集合的详细信息
        for collection in collections:
            try:
                coll = client.get_collection(collection.name)
                count = coll.count()
                baseline_data["collections"][collection.name] = {
                    "vector_count": count,
                    "metadata": collection.metadata if hasattr(collection, 'metadata') else {}
                }
                print(f"集合 '{collection.name}': {count} 个向量")
            except Exception as e:
                baseline_data["collections"][collection.name] = {
                    "error": str(e),
                    "vector_count": "unknown"
                }
                print(f"获取集合 '{collection.name}' 信息失败: {e}")

        if len(collections) == 0:
            print("ChromaDB中没有发现任何集合")

        return baseline_data

    except Exception as e:
        return {
            "status": "connection_failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    print("连接ChromaDB获取基线数据...")
    result = get_chromadb_baseline()

    # 输出结果
    print("\n=== ChromaDB基线数据 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 保存到文件
    with open("/home/wyatt/prism2/chromadb_baseline.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n基线数据已保存到: /home/wyatt/prism2/chromadb_baseline.json")