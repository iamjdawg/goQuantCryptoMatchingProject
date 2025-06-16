# Cryptocurrency Matching Engine

A high-performance cryptocurrency matching engine implementing REG NMS-inspired **price-time priority matching** with sub-millisecond order processing.

---

## 🚀 Features

- **Price-Time Priority Matching** – FIFO ordering within price levels  
- **Multiple Order Types** – Market, Limit, IOC, FOK  
- **Real-time Data** – WebSocket market data and trade feeds  
- **RESTful API** – Complete order management  
- **Sub-millisecond Processing** – Optimized for HFT environments  

---

## 🧪 Getting Started

Engine starts on:  
**http://localhost:8000**

---

## 🔑 Key Endpoints

### 📝 Orders

- `POST /orders` – Submit a new order  
- `DELETE /orders/{id}` – Cancel an existing order  

### 📈 Market Data

- `GET /market-data/{symbol}/depth` – Get order book depth  
- `GET /market-data/{symbol}/bbo` – Get best bid/offer  
- `ws://localhost:8000/ws/market-data/{symbol}` – Real-time market data (WebSocket)  
- `ws://localhost:8000/ws/trades/{symbol}` – Trade feed (WebSocket)  

---

## ⚡ Performance

- 100k+ orders/second throughput  
- **O(1)** order lookup, **O(log n)** price operations  
- Memory-efficient, heap-based order books  
- Asynchronous, non-blocking order processing with `async/await`  

---

> Built for speed. Tuned for traders.  
