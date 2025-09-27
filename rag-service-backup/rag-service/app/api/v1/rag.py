from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import logging
import time
import uuid
from typing import List

from app.core.dependencies import get_db
from app.models.requests import (
    RAGSearchRequest,
    DocumentEmbedRequest,
    BootstrapRequest,
    ContextEnhancementRequest,
    SimilarityRequest
)
from app.models.responses import (
    RAGSearchResponse,
    EmbedResponse,
    BootstrapResponse,
    BootstrapProgress,
    RAGContextResponse,
    SimilarityResponse
)
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.core.database import BootstrapTask

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(request: RAGSearchRequest):
    """语义搜索API - 检索相关文档"""
    try:
        logger.info(f"收到搜索请求: {request.query[:100]}...")

        # 根据搜索类型选择不同的搜索策略
        if request.search_type == "semantic":
            response = await rag_service.semantic_search(request)
        elif request.search_type == "hybrid":
            response = await rag_service.hybrid_search(request)
        else:
            # 默认使用语义搜索
            response = await rag_service.semantic_search(request)

        logger.info(f"搜索完成，返回 {len(response.results)} 个结果")
        return response

    except Exception as e:
        logger.error(f"搜索请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/embed", response_model=EmbedResponse)
async def embed_documents(request: DocumentEmbedRequest):
    """文档嵌入API - 将文档添加到向量数据库"""
    try:
        logger.info(f"收到文档嵌入请求，文档数量: {len(request.documents)}")
        start_time = time.time()

        # 1. 批量生成向量
        texts = [doc.content for doc in request.documents]
        embeddings = embedding_service.embed_batch(texts, batch_size=32)

        # 2. 添加到向量数据库
        processed_count, failed_docs = vector_service.add_documents(
            documents=request.documents,
            embeddings=embeddings,
            collection_name=request.collection_name
        )

        processing_time = time.time() - start_time

        logger.info(f"文档嵌入完成，成功: {processed_count}, 失败: {len(failed_docs)}, 耗时: {processing_time:.2f}秒")

        return EmbedResponse(
            success=len(failed_docs) == 0,
            processed_count=processed_count,
            failed_documents=failed_docs,
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"文档嵌入失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档嵌入失败: {str(e)}")


@router.post("/bootstrap", response_model=BootstrapResponse)
async def start_bootstrap(
    request: BootstrapRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动系统初始化 - 批量导入历史数据"""
    try:
        logger.info(f"收到系统初始化请求，数据源: {request.data_sources}")

        # 1. 创建初始化任务记录
        task_id = str(uuid.uuid4())
        task = BootstrapTask(
            task_id=task_id,
            data_sources={"sources": request.data_sources},
            time_range=request.time_range,
            status="pending"
        )

        db.add(task)
        db.commit()

        # 2. 估算任务参数
        estimated_docs, estimated_hours = _estimate_bootstrap_task(request.data_sources)

        # 3. 启动后台任务
        background_tasks.add_task(
            _execute_bootstrap_task,
            task_id,
            request,
            db
        )

        logger.info(f"初始化任务已启动，任务ID: {task_id}")

        return BootstrapResponse(
            task_id=task_id,
            estimated_documents=estimated_docs,
            estimated_time_hours=estimated_hours,
            status="started",
            progress_url=f"/api/rag/bootstrap/{task_id}"
        )

    except Exception as e:
        logger.error(f"启动系统初始化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动初始化失败: {str(e)}")


@router.get("/bootstrap/{task_id}", response_model=BootstrapProgress)
async def get_bootstrap_progress(task_id: str, db: Session = Depends(get_db)):
    """查询初始化进度"""
    try:
        task = db.query(BootstrapTask).filter(BootstrapTask.task_id == uuid.UUID(task_id)).first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 计算预估剩余时间 (简单估算)
        if task.progress_percentage > 0:
            estimated_remaining = (100 - task.progress_percentage) / task.progress_percentage * 60  # 分钟
        else:
            estimated_remaining = 120.0  # 默认2小时

        return BootstrapProgress(
            task_id=str(task.task_id),
            status=task.status,
            progress_percentage=task.progress_percentage,
            processed_documents=task.processed_documents,
            total_documents=task.total_documents,
            current_stage=task.current_stage or "初始化",
            stages_completed=task.stages_completed or [],
            estimated_remaining_time=estimated_remaining,
            error_count=task.error_count,
            last_update_time=task.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询初始化进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询进度失败: {str(e)}")


@router.post("/context", response_model=RAGContextResponse)
async def enhance_context(request: ContextEnhancementRequest):
    """上下文增强API - 为AI生成提供增强上下文"""
    try:
        logger.info(f"收到上下文增强请求: {request.query[:100]}...")

        response = await rag_service.enhance_context(request)

        logger.info(f"上下文增强完成，上下文长度: {response.token_count} tokens")
        return response

    except Exception as e:
        logger.error(f"上下文增强失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上下文增强失败: {str(e)}")


@router.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(request: SimilarityRequest):
    """相似度计算API"""
    try:
        logger.info(f"收到相似度计算请求，文档对数量: {len(request.document_pairs)}")
        start_time = time.time()

        similarities = []

        for doc_id1, doc_id2 in request.document_pairs:
            # 获取文档向量
            doc1 = vector_service.get_document_by_id(doc_id1)
            doc2 = vector_service.get_document_by_id(doc_id2)

            if doc1 and doc2:
                # 需要从向量数据库获取嵌入向量，这里简化处理
                # 实际实现需要存储或重新计算向量
                similarity = 0.0  # 占位符
                similarities.append(similarity)
            else:
                similarities.append(0.0)

        computation_time = time.time() - start_time

        return SimilarityResponse(
            similarities=similarities,
            computation_time=computation_time
        )

    except Exception as e:
        logger.error(f"相似度计算失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"相似度计算失败: {str(e)}")


def _estimate_bootstrap_task(data_sources: List[str]) -> tuple[int, float]:
    """估算初始化任务的文档数量和时间"""
    estimates = {
        "historical_announcements": 50000,
        "financial_reports": 15000,
        "research_reports": 30000,
        "policy_documents": 2000,
        "historical_news": 100000
    }

    total_docs = sum(estimates.get(source, 10000) for source in data_sources)
    estimated_hours = total_docs / 5000  # 假设每小时处理5000个文档

    return total_docs, estimated_hours


async def _execute_bootstrap_task(task_id: str, request: BootstrapRequest, db: Session):
    """执行后台初始化任务"""
    try:
        logger.info(f"开始执行初始化任务: {task_id}")

        # 更新任务状态
        task = db.query(BootstrapTask).filter(BootstrapTask.task_id == uuid.UUID(task_id)).first()
        if task:
            task.status = "running"
            task.current_stage = "数据采集"
            db.commit()

        # TODO: 实现具体的数据初始化逻辑
        # 这里需要调用 BootstrapManager 来执行实际的数据采集和处理

        logger.info(f"初始化任务 {task_id} 模拟完成")

        # 更新任务为完成状态
        if task:
            task.status = "completed"
            task.progress_percentage = 100.0
            task.current_stage = "完成"
            db.commit()

    except Exception as e:
        logger.error(f"执行初始化任务失败: {str(e)}")
        # 更新任务为失败状态
        task = db.query(BootstrapTask).filter(BootstrapTask.task_id == uuid.UUID(task_id)).first()
        if task:
            task.status = "failed"
            task.error_count += 1
            task.error_details = {"error": str(e)}
            db.commit()