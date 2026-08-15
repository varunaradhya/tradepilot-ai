from dataclasses import dataclass


@dataclass(frozen=True)
class PaperRiskConfig:
    initial_capital: float = 100000.0
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.01
    trade_direction: str = "LONG_ONLY"


class PaperTradingEngine:
    """Deterministic virtual ledger; never sends broker orders."""
    def __init__(self, config: PaperRiskConfig = PaperRiskConfig()):
        if config.trade_direction not in {"LONG_ONLY", "LONG_SHORT"}:
            raise ValueError("trade_direction must be LONG_ONLY or LONG_SHORT")
        self.config=config; self.cash=config.initial_capital; self.realized_pnl=0.0; self.day_pnl=0.0; self.day=None; self.position=None; self.trades=[]; self.halted=False

    def new_session(self, session: str):
        if self.day != session:
            if self.position is not None: self.close(self.position['last_price'],'SESSION_CLOSE')
            self.day=session; self.day_pnl=0.0; self.halted=False

    def can_trade(self):
        return not self.halted and self.position is None and self.day_pnl > -(self.config.initial_capital*self.config.max_daily_loss)

    def enter(self, price: float, stop: float, target: float, direction: str = "LONG"):
        if direction != "LONG":
            return False
        if self.config.trade_direction != "LONG_ONLY" and direction not in {"LONG", "SHORT"}:
            return False
        if not self.can_trade() or price<=stop: return False
        qty=int((self.config.initial_capital*self.config.risk_per_trade)/(price-stop))
        qty=min(qty,int(self.cash/price))
        if qty<=0: return False
        self.cash-=qty*price; self.position={'entry':price,'stop':stop,'target':target,'quantity':qty,'last_price':price,'direction':'LONG'}; return True

    def close(self, price: float, reason: str):
        if self.position is None: return None
        p=self.position; proceeds=p['quantity']*price; pnl=proceeds-p['quantity']*p['entry']; self.cash+=proceeds; self.realized_pnl+=pnl; self.day_pnl+=pnl
        trade={'entry':p['entry'],'exit':price,'quantity':p['quantity'],'pnl':pnl,'reason':reason,'direction':p['direction']}; self.trades.append(trade); self.position=None
        if self.day_pnl <= -(self.config.initial_capital*self.config.max_daily_loss): self.halted=True
        return trade

    def on_bar(self, session: str, high: float, low: float, close: float):
        self.new_session(session)
        if self.position is None: return None
        self.position['last_price']=close
        # Conservative priority: if one candle touches both levels, stop wins.
        if low<=self.position['stop']: return self.close(self.position['stop'],'STOP')
        if high>=self.position['target']: return self.close(self.position['target'],'TARGET')
        return None

    def snapshot(self):
        return {'mode':'SIMULATION_ONLY','trade_direction':self.config.trade_direction,'cash':round(self.cash,2),'realized_pnl':round(self.realized_pnl,2),'day_pnl':round(self.day_pnl,2),'halted':self.halted,'open_position':self.position,'trades':len(self.trades)}
