from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from src.modules.ai_client import AIClient
from src.modules.db_manager import DBManager
from src.modules.pump_portal_client import PumpPortalClient
from src.modules.social_media_manager import SocialMediaManager
from src.modules.solana_client import SolanaClient


class TradeType(Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

@dataclass
class Trade:
    id: str
    symbol: str
    trade_type: TradeType
    quantity: float
    price: float
    timestamp: datetime
    status: TradeStatus = TradeStatus.PENDING

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    market_value: float

class TradeManager:
    def __init__(self, solana_client: SolanaClient, pump_portal_client: PumpPortalClient, db_manager: DBManager, ai_client: AIClient, social_media_manager: SocialMediaManager):
        self.solana_client = solana_client
        self.pump_portal_client=pump_portal_client
        self.db_manager=db_manager
        self.ai_client= ai_client
        self.social_media_manager=social_media_manager

        self.trades: Dict[str, Trade] = {}
        self.positions: Dict[str, Position] = {}
        self.balance: float = 0.0
        
    def add_funds(self, amount: float) -> None:
        """Add funds to trading account"""
        if amount > 0:
            self.balance += amount
    
    def place_trade(self, symbol: str, trade_type: TradeType, quantity: float, price: float) -> str:
        """Place a new trade order"""
        trade_id = f"{symbol}_{trade_type.value}_{datetime.now().timestamp()}"
        
        trade = Trade(
            id=trade_id,
            symbol=symbol,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            timestamp=datetime.now()
        )
        
        self.trades[trade_id] = trade
        return trade_id
    
    def execute_trade(self, trade_id: str, execution_price: Optional[float] = None) -> bool:
        """Execute a pending trade"""
        if trade_id not in self.trades:
            return False
            
        trade = self.trades[trade_id]
        if trade.status != TradeStatus.PENDING:
            return False
            
        exec_price = execution_price or trade.price
        total_cost = exec_price * trade.quantity
        
        if trade.trade_type == TradeType.BUY:
            if self.balance < total_cost:
                return False
            self.balance -= total_cost
            self._update_position(trade.symbol, trade.quantity, exec_price)
        else:  # SELL
            if not self._has_sufficient_position(trade.symbol, trade.quantity):
                return False
            self.balance += total_cost
            self._update_position(trade.symbol, -trade.quantity, exec_price)
        
        trade.status = TradeStatus.EXECUTED
        trade.price = exec_price
        return True
    
    def cancel_trade(self, trade_id: str) -> bool:
        """Cancel a pending trade"""
        if trade_id in self.trades and self.trades[trade_id].status == TradeStatus.PENDING:
            self.trades[trade_id].status = TradeStatus.CANCELLED
            return True
        return False
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all current positions"""
        return {k: v for k, v in self.positions.items() if v.quantity != 0}
    
    def get_trade_history(self) -> List[Trade]:
        """Get all trades sorted by timestamp"""
        return sorted(self.trades.values(), key=lambda t: t.timestamp, reverse=True)
    
    def get_portfolio_value(self, market_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value"""
        portfolio_value = self.balance
        for symbol, position in self.positions.items():
            if position.quantity > 0 and symbol in market_prices:
                portfolio_value += position.quantity * market_prices[symbol]
        return portfolio_value
    
    def _update_position(self, symbol: str, quantity: float, price: float) -> None:
        """Update position after trade execution"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol, 0, 0, 0)
        
        pos = self.positions[symbol]
        
        if pos.quantity == 0:
            pos.quantity = quantity
            pos.avg_price = price
        else:
            total_value = pos.quantity * pos.avg_price + quantity * price
            pos.quantity += quantity
            if pos.quantity != 0:
                pos.avg_price = total_value / pos.quantity
            else:
                pos.avg_price = 0
        
        pos.market_value = pos.quantity * price
    
    def _has_sufficient_position(self, symbol: str, quantity: float) -> bool:
        """Check if sufficient position exists for selling"""
        if symbol not in self.positions:
            return False
        return self.positions[symbol].quantity >= quantity
