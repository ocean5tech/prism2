#!/usr/bin/env python3
"""
统一归档管理系统
规范化数据归档命名和存储
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
import hashlib

class ArchiveManager:
    def __init__(self):
        # 确保归档目录存在
        self.archive_dir = "/home/wyatt/prism2/rag-service/archive_data"
        os.makedirs(self.archive_dir, exist_ok=True)

        # 统一命名规范
        self.naming_convention = {
            'rss_news': 'financial_rss_{timestamp}.json',
            'akshare_data': 'market_data_{timestamp}.json',
            'high_value_content': 'investment_insights_{timestamp}.json',
            'macro_analysis': 'economic_analysis_{timestamp}.json',
            'company_fundamentals': 'company_analysis_{timestamp}.json',
            'industry_research': 'industry_reports_{timestamp}.json',
            'complete_archive': 'complete_dataset_{timestamp}.json'
        }

    def get_timestamp(self) -> str:
        """获取标准时间戳格式"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    def generate_archive_filename(self, data_type: str, custom_suffix: str = None) -> str:
        """生成标准归档文件名"""
        timestamp = self.get_timestamp()

        if data_type in self.naming_convention:
            filename = self.naming_convention[data_type].format(timestamp=timestamp)
        else:
            # 未知类型使用通用命名
            filename = f"rag_data_{data_type}_{timestamp}.json"

        if custom_suffix:
            # 插入自定义后缀
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{custom_suffix}{ext}"

        return os.path.join(self.archive_dir, filename)

    def save_archive(self, data: Any, data_type: str, metadata: Dict = None, custom_suffix: str = None) -> str:
        """保存数据到归档"""
        filename = self.generate_archive_filename(data_type, custom_suffix)

        # 准备归档记录
        archive_record = {
            'metadata': {
                'data_type': data_type,
                'created_at': datetime.now().isoformat(),
                'file_size': 0,  # 将在保存后更新
                'record_count': 0,
                'data_hash': '',
                **(metadata or {})
            },
            'data': data
        }

        # 计算数据统计
        if isinstance(data, list):
            archive_record['metadata']['record_count'] = len(data)
        elif isinstance(data, dict):
            archive_record['metadata']['record_count'] = len(data.get('documents', []))

        # 计算数据哈希
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        archive_record['metadata']['data_hash'] = hashlib.md5(data_str.encode()).hexdigest()

        # 保存文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(archive_record, f, ensure_ascii=False, indent=2, default=str)

            # 更新文件大小
            file_size = os.path.getsize(filename)
            archive_record['metadata']['file_size'] = file_size

            # 重新保存更新后的元数据
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(archive_record, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 归档保存: {os.path.basename(filename)}")
            print(f"   📊 记录数: {archive_record['metadata']['record_count']}")
            print(f"   💾 文件大小: {file_size:,} bytes")

            return filename

        except Exception as e:
            print(f"❌ 归档保存失败: {e}")
            return None

    def list_archives(self, data_type: str = None) -> List[Dict]:
        """列出归档文件"""
        archives = []

        for filename in os.listdir(self.archive_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.archive_dir, filename)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        archive = json.load(f)

                    # 过滤数据类型
                    if data_type and archive.get('metadata', {}).get('data_type') != data_type:
                        continue

                    archive_info = {
                        'filename': filename,
                        'filepath': file_path,
                        'metadata': archive.get('metadata', {}),
                        'file_size': os.path.getsize(file_path)
                    }

                    archives.append(archive_info)

                except Exception as e:
                    print(f"⚠️ 读取归档失败 {filename}: {e}")

        # 按创建时间排序
        archives.sort(key=lambda x: x['metadata'].get('created_at', ''), reverse=True)
        return archives

    def load_archive(self, filename: str) -> Dict:
        """加载归档数据"""
        if not filename.endswith('.json'):
            filename += '.json'

        file_path = os.path.join(self.archive_dir, filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载归档失败: {e}")
            return None

    def get_archive_stats(self) -> Dict:
        """获取归档统计"""
        archives = self.list_archives()

        stats = {
            'total_files': len(archives),
            'total_size': sum(a['file_size'] for a in archives),
            'data_types': {},
            'oldest_archive': None,
            'newest_archive': None
        }

        # 按数据类型统计
        for archive in archives:
            data_type = archive['metadata'].get('data_type', 'unknown')
            if data_type not in stats['data_types']:
                stats['data_types'][data_type] = {
                    'count': 0,
                    'total_records': 0,
                    'total_size': 0
                }

            stats['data_types'][data_type]['count'] += 1
            stats['data_types'][data_type]['total_records'] += archive['metadata'].get('record_count', 0)
            stats['data_types'][data_type]['total_size'] += archive['file_size']

        # 最新和最旧归档
        if archives:
            stats['newest_archive'] = archives[0]['filename']
            stats['oldest_archive'] = archives[-1]['filename']

        return stats

    def show_archive_summary(self):
        """显示归档摘要"""
        print(f"\n📁 RAG归档数据摘要")
        print(f"📂 归档目录: {self.archive_dir}")
        print("="*60)

        stats = self.get_archive_stats()

        print(f"📊 总体统计:")
        print(f"   文件数量: {stats['total_files']}")
        print(f"   总大小: {stats['total_size']:,} bytes ({stats['total_size']/1024/1024:.1f} MB)")

        if stats['data_types']:
            print(f"\n📋 数据类型分布:")
            for data_type, info in stats['data_types'].items():
                print(f"   {data_type}: {info['count']} 个文件, {info['total_records']} 条记录")

        if stats['newest_archive']:
            print(f"\n⏰ 时间范围:")
            print(f"   最新: {stats['newest_archive']}")
            print(f"   最旧: {stats['oldest_archive']}")

    def cleanup_old_archives(self, keep_count: int = 10, data_type: str = None):
        """清理旧归档（保留最新N个）"""
        archives = self.list_archives(data_type)

        if len(archives) <= keep_count:
            print(f"📁 归档数量 {len(archives)} <= {keep_count}，无需清理")
            return

        # 删除旧文件
        to_delete = archives[keep_count:]
        deleted_count = 0

        for archive in to_delete:
            try:
                os.remove(archive['filepath'])
                print(f"🗑️ 删除旧归档: {archive['filename']}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败 {archive['filename']}: {e}")

        print(f"✅ 清理完成，删除了 {deleted_count} 个旧归档")

def main():
    """演示归档管理功能"""
    manager = ArchiveManager()

    # 显示当前归档状态
    manager.show_archive_summary()

    # 演示保存新归档
    print(f"\n🧪 演示归档保存:")
    test_data = {
        'articles': [
            {'title': '测试新闻1', 'content': '测试内容1'},
            {'title': '测试新闻2', 'content': '测试内容2'}
        ]
    }

    manager.save_archive(
        data=test_data,
        data_type='rss_news',
        metadata={'source': 'test', 'quality': 'high'},
        custom_suffix='demo'
    )

    # 更新后的摘要
    print(f"\n📊 更新后归档状态:")
    manager.show_archive_summary()

if __name__ == "__main__":
    main()