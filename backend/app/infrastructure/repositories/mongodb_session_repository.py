from typing import List, Optional
from datetime import datetime, timezone
from backend.domain.session import Session
from backend.infrastructure.documents.session_document import SessionDocument
from backend.domain.repositories.session_repository import SessionRepository

class MongoDBSessionRepository(SessionRepository):
    """MongoDB会话仓储实现"""
    
    def __init__(self, db: Database):
        self.db = db
        self.collection = db.sessions
    
    async def create(self, session: Session) -> Session:
        """创建会话"""
        session_doc = SessionDocument(
            session_id=session.session_id,
            agent_id=session.agent_id,
            task_id=session.task_id,
            title=session.title,
            unread_message_count=session.unread_message_count,
            latest_message=session.latest_message,
            latest_message_at=session.latest_message_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
            events=session.events,
            status=session.status,
            file_list=session.file_list
        )
        await session_doc.insert()
        return session
    
    async def get_by_id(self, session_id: str) -> Optional[Session]:
        """根据ID获取会话"""
        session_doc = await SessionDocument.find_one({"session_id": session_id})
        if not session_doc:
            return None
        return self._to_domain(session_doc)
    
    async def update(self, session: Session) -> Session:
        """更新会话"""
        session_doc = await SessionDocument.find_one({"session_id": session.session_id})
        if not session_doc:
            raise ValueError(f"Session {session.session_id} not found")
        
        session_doc.agent_id = session.agent_id
        session_doc.task_id = session.task_id
        session_doc.title = session.title
        session_doc.unread_message_count = session.unread_message_count
        session_doc.latest_message = session.latest_message
        session_doc.latest_message_at = session.latest_message_at
        session_doc.updated_at = session.updated_at
        session_doc.events = session.events
        session_doc.status = session.status
        session_doc.file_list = session.file_list
        
        await session_doc.save()
        return session
    
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        result = await SessionDocument.find_one({"session_id": session_id}).delete()
        return result.deleted_count > 0
    
    async def list_by_agent(self, agent_id: str, skip: int = 0, limit: int = 20) -> List[Session]:
        """获取代理的会话列表"""
        sessions = await SessionDocument.find(
            {"agent_id": agent_id}
        ).skip(skip).limit(limit).to_list()
        return [self._to_domain(session) for session in sessions]
    
    async def add_file(self, session_id: str, file_id: str) -> bool:
        """添加文件到会话"""
        result = await self.collection.update_one(
            {"session_id": session_id},
            {
                "$addToSet": {"file_list": file_id},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0
    
    async def remove_file(self, session_id: str, file_id: str) -> bool:
        """从会话中移除文件"""
        result = await self.collection.update_one(
            {"session_id": session_id},
            {
                "$pull": {"file_list": file_id},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0
    
    async def get_files(self, session_id: str) -> List[str]:
        """获取会话的文件列表"""
        session = await SessionDocument.find_one({"session_id": session_id})
        if not session:
            return []
        return session.file_list
    
    def _to_domain(self, doc: SessionDocument) -> Session:
        """将文档转换为领域模型"""
        return Session(
            session_id=doc.session_id,
            agent_id=doc.agent_id,
            task_id=doc.task_id,
            title=doc.title,
            unread_message_count=doc.unread_message_count,
            latest_message=doc.latest_message,
            latest_message_at=doc.latest_message_at,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            events=doc.events,
            status=doc.status,
            file_list=doc.file_list
        ) 