"""
数据获取模块 - 从OKX获取市场数据
"""
import ccxt
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (TRADING_CONFIG, TIMEFRAME_CONFIG, DATA_POINTS, 
                    OKX_API_KEY, OKX_SECRET, OKX_PASSWORD,
                    OKX_TESTNET_API_KEY, OKX_TESTNET_SECRET, OKX_TESTNET_PASSWORD)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        """初始化OKX交易所连接"""
        # 检查是否使用模拟盘
        use_testnet = TRADING_CONFIG.get('use_testnet', False)
        
        # 根据环境选择API密钥
        if use_testnet:
            api_key = OKX_TESTNET_API_KEY
            secret = OKX_TESTNET_SECRET
            password = OKX_TESTNET_PASSWORD
            has_credentials = api_key and secret and password
        else:
            api_key = OKX_API_KEY
            secret = OKX_SECRET
            password = OKX_PASSWORD
            has_credentials = api_key and secret and password
        
        # 检查是否设置了代理
        proxies = {}
        if os.getenv('HTTP_PROXY'):
            proxies['http'] = os.getenv('HTTP_PROXY')
            proxies['https'] = os.getenv('HTTPS_PROXY', os.getenv('HTTP_PROXY'))
            print(f"🌐 使用代理: {proxies['http']}")
        
        if has_credentials:
            # if use_testnet:
            #     print(f"🧪 使用模拟盘连接OKX...")
            # else:
            #     print(f"🔑 使用实盘连接OKX...")  # 静默模式
            
            config = {
                'apiKey': api_key,
                'secret': secret,
                'password': password,
                'options': {
                    'defaultType': 'swap',  # 永续合约
                },
                'timeout': 30000,  # 30秒超时
                'enableRateLimit': True,
            }
            
            # 如果使用模拟盘，设置sandbox模式
            if use_testnet:
                config['sandbox'] = True
            
            if proxies:
                config['proxies'] = proxies
            
            self.exchange = ccxt.okx(config)
            
            # 注意：OKX的保证金模式是在每次开仓时通过tdMode参数指定的
            # 不需要在初始化时全局设置
            # mode_text = "模拟盘" if use_testnet else "实盘"
            # print(f"ℹ️  {mode_text} - 将使用全仓模式（cross）")  # 静默模式
        else:
            print(f"📡 使用公开API连接OKX（无需认证）...")
            config = {
                'options': {
                    'defaultType': 'swap',  # 永续合约
                },
                'timeout': 30000,
                'enableRateLimit': True,
            }
            if proxies:
                config['proxies'] = proxies
            self.exchange = ccxt.okx(config)
        
        # 关键：设置markets为空字典，防止自动加载
        self.exchange.markets = {}
        self.exchange.markets_by_id = {}
        
        # 默认使用第一个交易对，可以动态切换
        self.symbol = TRADING_CONFIG['symbols'][0] if 'symbols' in TRADING_CONFIG else TRADING_CONFIG.get('symbol', 'BTC/USDT:USDT')
        # print(f"[完成] OKX交易所连接成功: {self.symbol}")  # 静默模式
        
        # 不加载市场数据，直接使用交易对
        # load_markets()会调用不必要的API，可能导致错误
        # print(f"ℹ️  跳过市场数据预加载，将直接获取K线数据")  # 静默模式
    
    def fetch_ohlcv(self, timeframe: str = 'primary', limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        获取OHLCV数据
        
        Args:
            timeframe: 时间周期 ('primary', 'short', 'medium', 'long')
            limit: 数据点数量
        
        Returns:
            DataFrame或None
        """
        try:
            tf = TIMEFRAME_CONFIG.get(timeframe, '5m')
            data_limit = limit or DATA_POINTS.get(timeframe, 100)
            
            # print(f"[数据] 获取{tf}周期数据（{data_limit}根K线）...")  # 静默模式
            
            # 使用公开API直接调用，绕过市场加载
            # OKX的instId格式：BTC-USDT-SWAP
            inst_id = self.symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')
            
            params = {
                'instId': inst_id,
                'bar': tf,
                'limit': str(data_limit)
            }
            
            # 直接调用公开API
            response = self.exchange.public_get_market_candles(params)
            
            if response['code'] != '0':
                print(f"[失败] API返回错误: {response.get('msg', 'Unknown error')}")
                return None
            
            data = response['data']
            
            # 根据请求的数据量动态判断是否足够
            # 日线数据可能只有7根，这是正常的
            min_required = min(10, data_limit // 2)  # 至少需要请求量的一半
            if not data or len(data) < min_required:
                print(f"[失败] 数据不足：只获取到{len(data) if data else 0}根，需要至少{min_required}根")
                return None
            
            # OKX返回格式: [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
            # volume: 币本位成交量（如BTC数量）
            # volCcyQuote: USDT计价的成交额（更适合分析资金流）
            # 转换为DataFrame
            df = pd.DataFrame(
                data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume_coin', 'volCcy', 'volume', 'confirm']
            )
            
            # 只保留需要的列（使用volCcyQuote作为volume，即USDT计价的成交额）
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # 转换数据类型
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)  # 现在是USDT计价的成交额
            
            # OKX返回的数据是倒序的，需要反转
            df = df.iloc[::-1].reset_index(drop=True)
            
            # print(f"[完成] 成功获取{len(df)}根K线")  # 静默模式，只在异常时打印
            return df
            
        except Exception as e:
            print(f"[失败] 获取数据失败: {e}")
            print(f"   交易对: {self.symbol}")
            print(f"   时间周期: {tf}")
            print(f"   数据量: {data_limit}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_ticker(self) -> Optional[Dict]:
        """获取ticker数据"""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return ticker
        except Exception as e:
            print(f"[失败] 获取ticker失败: {e}")
            return None
    
    def fetch_balance(self) -> Optional[Dict]:
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            print(f"[失败] 获取余额失败: {e}")
            return None
    
    def fetch_positions(self) -> Optional[list]:
        """获取所有持仓（不限制币种）"""
        try:
            # 获取所有币种的持仓
            all_symbols = TRADING_CONFIG.get('symbols', [self.symbol])
            positions = self.exchange.fetch_positions(all_symbols)
            return positions
        except Exception as e:
            print(f"[失败] 获取持仓失败: {e}")
            # 尝试不指定币种，获取所有持仓
            try:
                positions = self.exchange.fetch_positions()
                return positions
            except Exception as e2:
                print(f"[失败] 获取所有持仓也失败: {e2}")
                return None
    
    def get_algo_orders(self, symbol: str = None) -> Optional[list]:
        """
        获取策略订单（止盈止损订单）
        
        Args:
            symbol: 交易对，如果为None则获取所有
        
        Returns:
            策略订单列表
        """
        try:
            params = {
                'ordType': 'conditional',  # 条件单
            }
            if symbol:
                params['instId'] = symbol.split(':')[0].replace('/', '-') + '-SWAP'
            
            orders = self.exchange.private_get_trade_orders_algo_pending(params)
            
            if orders and orders.get('code') == '0':
                return orders.get('data', [])
            return []
        except Exception as e:
            print(f"[失败] 获取策略订单失败: {e}")
            return []
    
    def get_current_position(self) -> Optional[Dict]:
        """
        获取当前持仓信息（格式化）
        返回第一个有效持仓，不限制币种
        
        Returns:
            持仓信息字典或None
        """
        try:
            positions = self.fetch_positions()
            
            if not positions:
                return None
            
            # 返回第一个有效持仓（不限制币种）
            for pos in positions:
                contracts = float(pos['contracts']) if pos['contracts'] else 0
                
                if contracts > 0:
                    contract_size = float(pos.get('contractSize', 0.01))
                    btc_amount = contracts * contract_size
                    
                    # 尝试从info字段获取原始OKX数据
                    pos_info = pos.get('info', {})
                    pos_id = pos_info.get('posId', '') or pos.get('id', '') or pos.get('posId', '')
                    inst_id = pos_info.get('instId', '') or pos.get('instId', '')
                    
                    # 调试：如果没有获取到posId，打印可用的字段
                    if not pos_id:
                        print(f"[警告] 调试：未找到posId，可用字段: {list(pos.keys())}")
                        if pos_info:
                            print(f"   info字段: {list(pos_info.keys())}")
                    
                    result = {
                        'side': pos['side'],  # 'long' or 'short'
                        'size': contracts,
                        'btc_amount': btc_amount,
                        'entry_price': float(pos['entryPrice']) if pos['entryPrice'] else 0,
                        'unrealized_pnl': float(pos['unrealizedPnl']) if pos['unrealizedPnl'] else 0,
                        'leverage': float(pos['leverage']) if pos['leverage'] else TRADING_CONFIG['leverage'],
                        'liquidation_price': float(pos.get('liquidationPrice', 0)) if pos.get('liquidationPrice') else 0,
                        'symbol': pos['symbol'],
                        'pos_id': pos_id,  # 持仓ID（从info中获取）
                        'inst_id': inst_id,  # 合约ID（从info中获取）
                        'uTime': pos.get('uTime'),  # 持仓更新时间（毫秒）
                        'cTime': pos.get('cTime'),  # 持仓创建时间（毫秒）
                    }
                    
                    # 获取止盈止损订单
                    try:
                        algo_orders = self.get_algo_orders(pos['symbol'])
                        if algo_orders:
                            for order in algo_orders:
                                # 止损订单
                                if order.get('slTriggerPx'):
                                    result['stop_loss'] = float(order['slTriggerPx'])
                                # 止盈订单
                                if order.get('tpTriggerPx'):
                                    result['take_profit'] = float(order['tpTriggerPx'])
                    except Exception as e:
                        print(f"[警告] 获取止盈止损失败: {e}")
                    
                    return result
            
            return None
            
        except Exception as e:
            print(f"[失败] 获取持仓失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        """
        获取指定币种的持仓信息
        
        Args:
            symbol: 币种符号，如 'SOL/USDT:USDT'
            
        Returns:
            持仓信息字典或None
        """
        try:
            positions = self.fetch_positions()
            
            if not positions:
                return None
            
            # 查找指定币种的持仓
            for pos in positions:
                if pos['symbol'] != symbol:
                    continue
                    
                contracts = float(pos['contracts']) if pos['contracts'] else 0
                
                if contracts > 0:
                    contract_size = float(pos.get('contractSize', 0.01))
                    btc_amount = contracts * contract_size
                    
                    # 尝试从info字段获取原始OKX数据
                    pos_info = pos.get('info', {})
                    pos_id = pos_info.get('posId', '') or pos.get('id', '') or pos.get('posId', '')
                    inst_id = pos_info.get('instId', '') or pos.get('instId', '')
                    
                    result = {
                        'side': pos['side'],  # 'long' or 'short'
                        'size': contracts,
                        'btc_amount': btc_amount,
                        'entry_price': float(pos['entryPrice']) if pos['entryPrice'] else 0,
                        'unrealized_pnl': float(pos['unrealizedPnl']) if pos['unrealizedPnl'] else 0,
                        'leverage': float(pos['leverage']) if pos['leverage'] else TRADING_CONFIG['leverage'],
                        'liquidation_price': float(pos.get('liquidationPrice', 0)) if pos.get('liquidationPrice') else 0,
                        'symbol': pos['symbol'],
                        'pos_id': pos_id,  # 持仓ID（从info中获取）
                        'inst_id': inst_id,  # 合约ID（从info中获取）
                        'uTime': pos.get('uTime'),  # 持仓更新时间（毫秒）
                        'cTime': pos.get('cTime'),  # 持仓创建时间（毫秒）
                    }
                    
                    # 获取止盈止损订单
                    try:
                        algo_orders = self.get_algo_orders(pos['symbol'])
                        if algo_orders:
                            for order in algo_orders:
                                # 止损订单
                                if order.get('slTriggerPx'):
                                    result['stop_loss'] = float(order['slTriggerPx'])
                                # 止盈订单
                                if order.get('tpTriggerPx'):
                                    result['take_profit'] = float(order['tpTriggerPx'])
                    except Exception as e:
                        print(f"[警告] 获取止盈止损失败: {e}")
                    
                    return result
            
            return None
            
        except Exception as e:
            print(f"[失败] 获取持仓失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_positions(self) -> list:
        """
        获取所有持仓信息
        
        Returns:
            持仓信息列表
        """
        try:
            positions = self.fetch_positions()
            
            if not positions:
                return []
            
            result = []
            # 遍历所有持仓
            for pos in positions:
                contracts = float(pos['contracts']) if pos['contracts'] else 0
                
                if contracts > 0:
                    contract_size = float(pos.get('contractSize', 0.01))
                    btc_amount = contracts * contract_size
                    
                    # 调试：打印原始时间字段
                    print(f"[调试] {pos['symbol']} 原始数据: cTime={pos.get('cTime')}, uTime={pos.get('uTime')}, cTime类型={type(pos.get('cTime'))}")
                    
                    pos_info = {
                        'side': pos['side'],  # 'long' or 'short'
                        'size': contracts,
                        'btc_amount': btc_amount,
                        'entry_price': float(pos['entryPrice']) if pos['entryPrice'] else 0,
                        'unrealized_pnl': float(pos['unrealizedPnl']) if pos['unrealizedPnl'] else 0,
                        'leverage': float(pos['leverage']) if pos['leverage'] else TRADING_CONFIG['leverage'],
                        'liquidation_price': float(pos.get('liquidationPrice', 0)) if pos.get('liquidationPrice') else 0,
                        'symbol': pos['symbol'],
                        'uTime': pos.get('uTime'),  # 持仓更新时间（毫秒）
                        'cTime': pos.get('cTime'),  # 持仓创建时间（毫秒）
                    }
                    
                    # 获取止盈止损订单
                    try:
                        algo_orders = self.get_algo_orders(pos['symbol'])
                        if algo_orders:
                            for order in algo_orders:
                                # 止损订单
                                if order.get('slTriggerPx'):
                                    pos_info['stop_loss'] = float(order['slTriggerPx'])
                                # 止盈订单
                                if order.get('tpTriggerPx'):
                                    pos_info['take_profit'] = float(order['tpTriggerPx'])
                    except Exception as e:
                        print(f"[警告] 获取止盈止损失败: {e}")
                    
                    result.append(pos_info)
            
            return result
            
        except Exception as e:
            print(f"[失败] 获取持仓失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def set_leverage(self, leverage: int = None):
        """设置杠杆"""
        # 测试模式下跳过杠杆设置
        if TRADING_CONFIG.get('test_mode', True):
            lev = leverage or TRADING_CONFIG['leverage']
            print(f"🧪 测试模式：跳过杠杆设置（目标: {lev}x）")
            return True
        
        try:
            lev = leverage or TRADING_CONFIG['leverage']
            self.exchange.set_leverage(
                lev,
                self.symbol,
                {'mgnMode': 'cross'}
            )
            print(f"[完成] 杠杆设置成功: {lev}x")
            return True
        except Exception as e:
            print(f"[失败] 设置杠杆失败: {e}")
            print(f"[警告]  如果只是获取数据，可以忽略此错误")
            return False


if __name__ == "__main__":
    # 测试代码
    print("=== 测试数据获取器 ===\n")
    
    fetcher = DataFetcher()
    
    # 测试获取K线数据
    df = fetcher.fetch_ohlcv('primary')
    if df is not None:
        print(f"\n最新价格: ${df['close'].iloc[-1]:,.2f}")
        print(f"数据范围: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
    
    # 测试获取余额
    balance = fetcher.fetch_balance()
    if balance:
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        print(f"\nUSDT余额: ${usdt_balance:,.2f}")
    
    # 测试获取持仓
    position = fetcher.get_current_position()
    if position:
        print(f"\n当前持仓: {position}")
    else:
        print("\n当前无持仓")
