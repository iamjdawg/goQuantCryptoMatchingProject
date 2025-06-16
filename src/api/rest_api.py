from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
import logging
# from ..core.matching_engine import matching_engine

# configure logging
logger = logging.getLogger(__name__)

# pydantic models for request and response validation
class OrderRequest(BaseModel):
    symbol : str = Field(..., description = "Trading symbol, e.g., 'BTC-USDT'")
    order_type : str = Field(..., description= "Order type: market, limit, ioc, fok")
    side : str = Field(..., description= "Order side: buy or sell")
    quantity : float = Field(..., gt = 0, description= "Order quantity, must be positive.")
    price : Optional[float] = Field(None, gt = 0, description= "Order price(required for limit orders)")
    order_id : Optional[str] = Field(None, description = "Optional custom order ID")

    @validator('order_type')
    def validate_order_type(cls, v):
        if v.lower() not in ['market', 'limit', 'ioc', 'fok']:
            raise ValueError("Invalid order type. Must be one of: market, limit, ioc, fok.")
        return v.lower()

    @validator('side')
    def validate_side(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError("Invalid order side. Must be 'buy' or 'sell'.")
        return v.lower()
    
    @validator('price')
    def validate_price_for_limit_orders(cls, v, values):
        order_type = values.get('order_type', '').lower()
        if order_type in ['limit', 'ioc', 'fok'] and v is None:
            raise ValueError(f'price is required for {order_type} orders')
        return v
    
class OrderResponse(BaseModel):
    status : str
    order : Optional[dict] = None
    trades : Optional[List[dict]] = None
    message : Optional[str] = None

class CancelOrderRequest(BaseModel):
    order_id : str = Field(..., description = "ID of the order to cancel")

class MarketDataResponse(BaseModel):
    symbol: str
    bids: List[List[str]]
    asks: List[List[str]]
    timestamp: str


class BBOResponse(BaseModel):
    symbol: str
    best_bid: Optional[str]
    best_ask: Optional[str]
    spread: Optional[str]
    timestamp: str

def create_rest_api(app, matching_engine):
    """
    Create the FastAPI application with all endpoints.
    
    :param matching_engine: Instance of the MatchingEngine class
    :return: FastAPI app instance
    """
    # app = FastAPI(
    #     title = "CryptoCurrency Matching Engine API",
    #     description= "High-performance cryptocurrency matching engine with REG NMS-inspired principles",
    #     version= "1.0.0"
    # )

    @app.get("/")
    async def root():
        return {
            "message": "CryptoCurrency Matching Engine API",
            "status": "running",
            "version": "1.0.0"
        }

    @app.get("/health")
    async def health_check():
        # health check with engine statistics
        stats = matching_engine.get_statistics()
        return{
            "status" : "healthy",
            "engine_stats": stats
        }

    @app.post("/orders", response_model=OrderResponse)
    async def submit_order(order_request: OrderRequest):
        """
        Submit a new order to the matching engine.
        
        - **symbol**: Trading pair (e.g., "BTC-USDT")
        - **order_type**: Type of order (market, limit, ioc, fok)
        - **side**: buy or sell
        - **quantity**: Amount to trade (must be positive)
        - **price**: Price level (required for limit orders)
        """
        try:
            # Convert to dict for matching engine
            order_dict = order_request.dict()
            
            # Submit to matching engine
            result = await matching_engine.submit_order(order_dict)
            
            if result['status'] == 'success':
                return OrderResponse(**result)
            else:
                raise HTTPException(status_code=400, detail=result.get('message', 'Order submission failed'))
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    @app.delete("/orders/{order_id}")
    async def cancel_order(order_id: str):
        """Cancel an existing order by order ID."""
        try:
            result = await matching_engine.cancel_order(order_id)
            
            if result['status'] == 'success':
                return result
            else:
                raise HTTPException(status_code=404, detail=result.get('message', 'Order not found'))
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    @app.get("/orders/{order_id}")
    async def get_order_status(order_id: str):
        """Get the status of a specific order."""
        try:
            result = matching_engine.get_order_status(order_id)
            
            if result['status'] == 'success':
                return result
            else:
                raise HTTPException(status_code=404, detail=result.get('message', 'Order not found'))
                
        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/market-data/{symbol}/depth", response_model=MarketDataResponse)
    async def get_order_book_depth(symbol: str, levels: int = 10):
        """
        Get order book depth for a trading pair.
        
        - **symbol**: Trading pair symbol
        - **levels**: Number of price levels to return (default: 10)
        """
        try:
            if levels <= 0 or levels > 100:
                raise HTTPException(status_code=400, detail="levels must be between 1 and 100")
            
            depth = matching_engine.get_order_book_depth(symbol, levels)
            return MarketDataResponse(**depth)
            
        except Exception as e:
            logger.error(f"Error getting order book depth for {symbol}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    @app.get("/market-data/{symbol}/bbo", response_model=BBOResponse)
    async def get_best_bid_offer(symbol: str):
        """
        Get Best Bid and Offer (BBO) for a trading pair.
        
        - **symbol**: Trading pair symbol
        """
        try:
            bbo = matching_engine.get_bbo(symbol)
            return BBOResponse(**bbo)
            
        except Exception as e:
            logger.error(f"Error getting BBO for {symbol}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    @app.get("/trades/{symbol}")
    async def get_recent_trades(symbol: str, limit: int = 100):
        """
        Get recent trades for a trading pair.
        
        - **symbol**: Trading pair symbol  
        - **limit**: Maximum number of trades to return (default: 100)
        """
        try:
            if limit <= 0 or limit > 1000:
                raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
            
            trades = matching_engine.get_recent_trades(symbol, limit)
            return {
                "symbol": symbol,
                "trades": trades,
                "count": len(trades)
            }
            
        except Exception as e:
            logger.error(f"Error getting recent trades for {symbol}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/statistics")
    async def get_engine_statistics():
        """Get matching engine statistics and performance metrics."""
        try:
            stats = matching_engine.get_statistics()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    @app.get("/symbols")
    async def get_active_symbols():
        """Get list of active trading symbols."""
        try:
            stats = matching_engine.get_statistics()
            return {
                "symbols": stats.get('active_symbols', []),
                "count": stats.get('total_symbols', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting active symbols: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Error handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return HTTPException(status_code=400, detail=str(exc))


    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}")
        return HTTPException(status_code=500, detail="Internal server error")
    
    return app

if __name__ == "__main__":
    import uvicorn
    from ..core.matching_engine import matching_engine
    app = create_rest_api(matching_engine)
    uvicorn.run(app, host="0.0.0.0", port=8000)
