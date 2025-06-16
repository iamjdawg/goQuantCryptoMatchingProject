from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import asyncio
import json
import logging
from datetime import datetime, timezone
from ..core.matching_engine import matching_engine

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.market_data_connections : Dict[str, Set[WebSocket]] = {}
        self.trade_feed_connections : Dict[str, Set[WebSocket]] = {}
        self.all_connections : Set[WebSocket] = set()

    async def connect_market_data(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.market_data_connections:
            self.market_data_connections[symbol] = set()
        self.market_data_connections[symbol].add(websocket)
        self.all_connections.add(websocket)
        logger.info(f"Client connected to market data for {symbol}")

    async def connect_trade_feed(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.trade_feed_connections:
            self.trade_feed_connections[symbol] = set()
        self.trade_feed_connections[symbol].add(websocket)
        self.all_connections.add(websocket)
        logger.info(f"Client connected to trade feed for {symbol}")

    def disconnect(self, websocket: WebSocket):
        self.all_connections.discard(websocket)
        # Remove from market data connections
        for symbol_connections in self.market_data_connections.values():
            symbol_connections.discard(websocket)
        # Remove from trade feed connections
        for symbol_connections in self.trade_feed_connections.values():
            symbol_connections.discard(websocket)
        logger.info("Client disconnected")

    async def broadcast_market_data(self, symbol: str, data: dict):
        if symbol in self.market_data_connections:
            disconnected = set()
            for websocket in self.market_data_connections[symbol]:
                try:
                    await websocket.send_text(json.dumps(data, default=str))
                except Exception as e:
                    logger.error(f"Error sending market data: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws)

    async def broadcast_trade_execution(self, symbol: str, trade_data: dict):
        if symbol in self.trade_feed_connections:
            disconnected = set()
            for websocket in self.trade_feed_connections[symbol]:
                try:
                    await websocket.send_text(json.dumps(trade_data, default=str))
                except Exception as e:
                    logger.error(f"Error sending trade data: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws)

# Global connection manager instance
connection_manager = ConnectionManager()

# WebSocket endpoints
async def websocket_market_data_endpoint(websocket: WebSocket, symbol: str):
    await connection_manager.connect_market_data(websocket, symbol)
    
    # Send initial order book snapshot
    try:
        order_book = matching_engine.get_order_book(symbol)
        if order_book:
            market_data = {
                "type": "orderbook",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "bids": order_book.get_bids_snapshot(),
                "asks": order_book.get_asks_snapshot()
            }
            await websocket.send_text(json.dumps(market_data, default=str))
    except Exception as e:
        logger.error(f"Error sending initial snapshot: {e}")

    try:
        while True:
            # Keep connection alive and handle any incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

async def websocket_trade_feed_endpoint(websocket: WebSocket, symbol: str):
    await connection_manager.connect_trade_feed(websocket, symbol)
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

# Market data update functions (called by matching engine)
async def broadcast_order_book_update(symbol: str, order_book):
    """Called by matching engine when order book changes"""
    market_data = {
        "type": "orderbook",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "bids": order_book.get_bids_snapshot(),
        "asks": order_book.get_asks_snapshot()
    }
    await connection_manager.broadcast_market_data(symbol, market_data)

async def broadcast_trade_execution(symbol: str, trade):
    """Called by matching engine when trade executes"""
    trade_data = {
        "type": "trade",
        "timestamp": trade.timestamp.isoformat(),
        "symbol": symbol,
        "trade_id": trade.trade_id,
        "price": str(trade.price),
        "quantity": str(trade.quantity),
        "aggressor_side": trade.aggressor_side,
        "maker_order_id": trade.maker_order_id,
        "taker_order_id": trade.taker_order_id
    }
    await connection_manager.broadcast_trade_execution(symbol, trade_data)

async def broadcast_bbo_update(symbol: str, best_bid: tuple, best_ask: tuple):
    """Called by matching engine when BBO changes"""
    bbo_data = {
        "type": "bbo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "best_bid": {"price": str(best_bid[0]), "quantity": str(best_bid[1])} if best_bid else None,
        "best_ask": {"price": str(best_ask[0]), "quantity": str(best_ask[1])} if best_ask else None
    }
    await connection_manager.broadcast_market_data(symbol, bbo_data) 