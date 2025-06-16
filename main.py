# import asyncio
# import signal
# import sys
# import uvicorn
# from fastapi import FastAPI
# import logging
# from typing import List
# import threading

# # Import your existing modules
# from src.core.matching_engine import MatchingEngine
# from src.api.rest_api import create_rest_api
# from src.api.websocket_api import create_websocket_server
# from config import Config

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('matching_engine.log'),
#         logging.StreamHandler(sys.stdout)
#     ]
# )

# logger = logging.getLogger(__name__)

# class MatchingEngineApplication:
#     def __init__(self):
#         self.matching_engine = MatchingEngine()
#         self.rest_app = None
#         self.websocket_server = None
#         self.rest_server = None
#         self.websocket_server_task = None
#         self.shutdown_event = asyncio.Event()
        
#     async def startup(self):
#         """Initialize and start all services"""
#         logger.info("Starting Cryptocurrency Matching Engine...")
        
#         # Create REST API with the matching engine
#         self.rest_app = create_rest_api(self.matching_engine)
        
#         # Create WebSocket server
#         self.websocket_server = create_websocket_server(self.matching_engine)
        
#         # Start WebSocket server in background
#         self.websocket_server_task = asyncio.create_task(
#             self.websocket_server.serve(
#                 host=Config.WEBSOCKET_HOST, 
#                 port=Config.WEBSOCKET_PORT
#             )
#         )
        
#         logger.info(f"WebSocket server started on {Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}")
#         logger.info(f"REST API will start on {Config.REST_HOST}:{Config.REST_PORT}")
        
#     async def shutdown(self):
#         """Graceful shutdown"""
#         logger.info("Shutting down Matching Engine...")
        
#         if self.websocket_server:
#             self.websocket_server.close()
#             await self.websocket_server.wait_closed()
            
#         if self.websocket_server_task:
#             self.websocket_server_task.cancel()
#             try:
#                 await self.websocket_server_task
#             except asyncio.CancelledError:
#                 pass
                
#         self.shutdown_event.set()
#         logger.info("Shutdown complete")

# # Global application instance
# app_instance = MatchingEngineApplication()

# def create_app() -> FastAPI:
#     """Create FastAPI application for uvicorn"""
#     return app_instance.rest_app

# async def main():
#     """Main entry point"""
    
#     def signal_handler(signum, frame):
#         logger.info(f"Received signal {signum}")
#         asyncio.create_task(app_instance.shutdown())
    
#     # Setup signal handlers
#     signal.signal(signal.SIGINT, signal_handler)
#     signal.signal(signal.SIGTERM, signal_handler)
    
#     try:
#         # Initialize application
#         await app_instance.startup()
        
#         # Start REST API server
#         config = uvicorn.Config(
#             app=app_instance.rest_app,
#             host=Config.REST_HOST,
#             port=Config.REST_PORT,
#             log_level="info"
#         )
#         server = uvicorn.Server(config)
        
#         # Run server
#         await server.serve()
        
#     except KeyboardInterrupt:
#         logger.info("Received keyboard interrupt")
#     except Exception as e:
#         logger.error(f"Application error: {e}")
#     finally:
#         await app_instance.shutdown()

# if __name__ == "__main__":
#     asyncio.run(main())




import uvicorn
import asyncio
import logging
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.rest_api import create_rest_api
from src.api.websocket_api import websocket_market_data_endpoint, websocket_trade_feed_endpoint
from src.core.matching_engine import matching_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('matching_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Cryptocurrency Matching Engine...")
    
    # Initialize matching engine
    await matching_engine.start()
    logger.info("Matching engine started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down matching engine...")
    await matching_engine.stop()
    logger.info("Matching engine stopped")

app = FastAPI(
    title="Cryptocurrency Matching Engine",
    description="High-performance matching engine with REG NMS-inspired principles",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_rest_api(app, matching_engine)

# WebSocket endpoints
@app.websocket("/ws/market-data/{symbol}")
async def websocket_market_data(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time market data"""
    await websocket_market_data_endpoint(websocket, symbol.upper())

@app.websocket("/ws/trades/{symbol}")
async def websocket_trades(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time trade feed"""
    await websocket_trade_feed_endpoint(websocket, symbol.upper())

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = await matching_engine.get_statistics()  # Add await here
    return {
        "status": "healthy",
        "engine_status": "running" if matching_engine.is_running else "stopped",
        "supported_symbols": list(matching_engine.order_books.keys())
    }

# Engine statistics endpoint
@app.get("/stats")
async def get_engine_stats():
    """Get matching engine statistics"""
    return await matching_engine.get_statistics()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
