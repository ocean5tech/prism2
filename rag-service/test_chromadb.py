#!/usr/bin/env python3

import chromadb
from chromadb.config import Settings
import os

def test_chromadb_connection():
    """Test ChromaDB connection with different configurations"""

    # Unset proxy variables
    for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if proxy_var in os.environ:
            del os.environ[proxy_var]

    configs = [
        {
            'name': 'Basic HTTP Client',
            'client': lambda: chromadb.HttpClient(host='localhost', port=8000)
        },
        {
            'name': 'HTTP Client with anonymous auth',
            'client': lambda: chromadb.HttpClient(
                host='localhost',
                port=8000,
                settings=Settings(anonymized_telemetry=False)
            )
        },
        {
            'name': 'HTTP Client with disabled auth',
            'client': lambda: chromadb.HttpClient(
                host='localhost',
                port=8000,
                settings=Settings(
                    anonymized_telemetry=False,
                    chroma_server_authn_credentials="admin:admin"
                )
            )
        }
    ]

    for config in configs:
        print(f"\n--- Testing {config['name']} ---")
        try:
            client = config['client']()

            # Test basic operations
            print("✓ Client created successfully")

            # Test heartbeat (this might not exist in all versions)
            try:
                heartbeat = client.heartbeat()
                print(f"✓ Heartbeat: {heartbeat}")
            except Exception as e:
                print(f"⚠ Heartbeat failed: {e}")

            # Test list collections
            try:
                collections = client.list_collections()
                print(f"✓ Collections listed: {len(collections)} collections")
                for col in collections:
                    print(f"  - {col.name}")
            except Exception as e:
                print(f"⚠ List collections failed: {e}")

            # Try to create a test collection
            try:
                test_collection = client.get_or_create_collection("test_connection")
                print(f"✓ Test collection created/retrieved: {test_collection.name}")

                # Test basic operations on collection
                count = test_collection.count()
                print(f"✓ Collection count: {count}")

                # Clean up test collection
                try:
                    client.delete_collection("test_connection")
                    print("✓ Test collection cleaned up")
                except:
                    pass

            except Exception as e:
                print(f"⚠ Collection operations failed: {e}")

            print(f"✅ {config['name']} - SUCCESS")
            return True

        except Exception as e:
            print(f"❌ {config['name']} - FAILED: {e}")
            import traceback
            traceback.print_exc()
            continue

    return False

if __name__ == "__main__":
    success = test_chromadb_connection()
    if success:
        print("\n🎉 ChromaDB connection test passed!")
    else:
        print("\n💥 All ChromaDB connection attempts failed!")
        print("Check if ChromaDB container is running: podman ps | grep chroma")
        print("Check ChromaDB logs: podman logs prism2-chromadb")