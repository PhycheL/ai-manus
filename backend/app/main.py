from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.interfaces.api.routes import router
from app.application.services.agent_service import AgentService
from app.infrastructure.config import get_settings
from app.infrastructure.logging import setup_logging
from app.interfaces.errors.exception_handlers import register_exception_handlers
from app.infrastructure.storage.mongodb import get_mongodb
from app.infrastructure.storage.redis import get_redis
from app.infrastructure.external.search.google_search import GoogleSearchEngine
from app.infrastructure.external.llm.openai_llm import OpenAILLM
from app.infrastructure.external.sandbox.docker_sandbox import DockerSandbox
from app.infrastructure.repositories.mongo_agent_repository import MongoAgentRepository
from app.infrastructure.repositories.mongo_session_repository import MongoSessionRepository
from app.infrastructure.repositories.gridfs_file_repository import GridFSFileRepository
from app.infrastructure.external.task.redis_task import RedisStreamTask
from app.interfaces.api.routes import get_agent_service
from app.interfaces.api.file_routes import get_file_service
from app.infrastructure.models.documents import AgentDocument, SessionDocument
from app.infrastructure.models.file_document import FileDocument
from app.infrastructure.utils.llm_json_parser import LLMJsonParser
from app.application.services.file_service import FileService
from beanie import init_beanie

# Initialize logging system
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
settings = get_settings()


def create_agent_service() -> AgentService:
    search_engine = None
    # Initialize search engine only if both API key and engine ID are set
    if settings.google_search_api_key and settings.google_search_engine_id:
        logger.info("Initializing Google Search Engine")
        search_engine = GoogleSearchEngine(
            api_key=settings.google_search_api_key, 
            cx=settings.google_search_engine_id
        )
    else:
        logger.warning("Google Search Engine not initialized: missing API key or engine ID")

    return AgentService(
        llm=OpenAILLM(),
        agent_repository=MongoAgentRepository(),
        session_repository=MongoSessionRepository(),
        sandbox_cls=DockerSandbox,
        task_cls=RedisStreamTask,
        json_parser=LLMJsonParser(),
        search_engine=search_engine,
    )

# Create agent service instance
agent_service = create_agent_service()

# File service will be created after MongoDB initialization
file_service = None

def create_file_service() -> FileService:
    return FileService(
        file_repository=GridFSFileRepository(get_mongodb().client[settings.mongodb_database])
    )

def get_file_service_instance() -> FileService:
    """获取文件服务实例的依赖注入函数"""
    if file_service is None:
        raise RuntimeError("FileService not initialized yet")
    return file_service

async def shutdown() -> None:
    """Cleanup function that will be called when the application is shutting down"""
    logger.info("Graceful shutdown...")
    
    try:
        # Create task for agent service shutdown with timeout
        shutdown_task = asyncio.create_task(agent_service.shutdown())
        try:
            await asyncio.wait_for(shutdown_task, timeout=30.0)  # 30 seconds timeout
            logger.info("Successfully completed graceful shutdown")
        except asyncio.TimeoutError:
            logger.warning("Shutdown timed out after 30 seconds")
            
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Create lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code executed on startup
    logger.info("Application startup - Manus AI Agent initializing")
    
    # Initialize MongoDB and Beanie
    await get_mongodb().initialize()

    # Initialize Beanie
    await init_beanie(
        database=get_mongodb().client[settings.mongodb_database],
        document_models=[AgentDocument, SessionDocument, FileDocument]
    )
    logger.info("Successfully initialized Beanie")
    
    # Create file service after MongoDB initialization
    global file_service
    file_service = create_file_service()
    logger.info("Successfully initialized FileService")
    
    # Initialize Redis
    await get_redis().initialize()
    
    try:
        yield
    finally:
        # Code executed on shutdown
        logger.info("Application shutdown - Manus AI Agent terminating")
        # Disconnect from MongoDB
        await get_mongodb().shutdown()
        # Disconnect from Redis
        await get_redis().shutdown()
        await shutdown()

app = FastAPI(title="Manus AI Agent", lifespan=lifespan, timeout_graceful_shutdown=5)
app.dependency_overrides[get_agent_service] = lambda: agent_service
app.dependency_overrides[get_file_service] = get_file_service_instance

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register routes with dependency injection
app.include_router(router, prefix="/api/v1")