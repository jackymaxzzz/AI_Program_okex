"""
简化版主程序 - 完全信任AI的判断
"""
import time
import sys
import os
from datetime import datetime
from typing import Dict, Optional
from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, TRADING_CONFIG, validate_config
from ai import PureAITrader
from data import DataFetcher, TradeDatabase, calculate_technical_indicators, format_market_data
from mcp import MCPDatabaseSync
from core import TradingExecutor, PositionManager, OrderSync


class Logger:
    """同时输出到终端和文件的日志类"""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()


class SimpleAITradingBot:
    """AI交易机器人 - Power by DeepSeek AI"""
    
    def __init__(self):
        """初始化交易机器人"""
        print(f"\n{'='*70}")
        print("[AI] 初始化AI交易机器人")
        print(f"{'='*70}\n")
        
        # 验证配置
        validate_config()
        
        # 初始化组件
        self.ai_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        self.ai_trader = PureAITrader(self.ai_client)
        self.data_fetcher = DataFetcher()
        self.trade_db = TradeDatabase()
        
        # 初始化MCP与数据库同步器
        self.mcp_sync = MCPDatabaseSync(self.ai_trader.mcp_memory, self.trade_db)
        print("[同步] MCP数据库同步器已初始化")
        
        # 初始化新模块（传递MCP记忆系统）
        self.trading_executor = TradingExecutor(
            self.data_fetcher, 
            self.trade_db,
            mcp_memory=self.ai_trader.mcp_memory  # 传递MCP记忆
        )
        self.position_manager = PositionManager(self.data_fetcher, self.trade_db)
        self.order_sync = OrderSync(self.data_fetcher, self.trade_db)
        
        # 从数据库加载历史交易到MCP（必须在OrderSync之前，因为数据库可能已有历史数据）
        try:
            print("[MCP] 正在从数据库加载历史交易...")
            self.ai_trader.mcp_memory._restore_from_database()
        except Exception as e:
            print(f"[警告] 从数据库加载MCP失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 加载历史MCP记忆文件
        try:
            self.ai_trader.mcp_filesystem.import_mcp_memory(self.ai_trader.mcp_memory)
            print("[加载] MCP历史记忆文件已加载")
        except Exception as e:
            print(f"[警告] 加载MCP记忆文件失败: {e}")
        
        # 状态
        self.current_trade_id = None
        self.cycle_count = 0
        
        # 指数退避相关
        self.consecutive_holds = 0  # 连续HOLD次数
        self.skip_cycles = 0  # 需要跳过的周期数
        
        # 安全机制：记录待确认的开仓决策（支持多个币种）
        self.pending_open_decisions = {}  # {'BTC': {'signal': 'BUY', 'cycle': 123}, 'ETH': {...}}
        
        print("\n" + "="*70)
        print("初始化完成")
        print("="*70 + "\n")
    
    def run_cycle(self):
        """运行一个交易周期"""
        try:
            self.cycle_count += 1
            
            # 指数退避：如果需要跳过本周期
            if self.skip_cycles > 0:
                self.skip_cycles -= 1
                print(f"\n{'='*70}")
                print(f"⏭️  周期 #{self.cycle_count} - 跳过AI分析（连续HOLD优化）")
                print(f"   剩余跳过周期: {self.skip_cycles}")
                print(f"{'='*70}\n")
                return
            
            print(f"\n{'='*70}")
            print(f"周期 #{self.cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")
            
            # 1. 获取多币种市场数据
            all_market_data = {}
            
            for symbol in TRADING_CONFIG['symbols']:
                coin = symbol.split('/')[0]  # 提取币种名称 (BTC, ETH)
                # print(f"\n📡 获取{coin}数据...")  # 静默模式
                
                # 临时切换交易对
                original_symbol = self.data_fetcher.symbol
                self.data_fetcher.symbol = symbol
                
                # 获取15分钟数据
                df_15m = self.data_fetcher.fetch_ohlcv('primary')
                if df_15m is None:
                    print(f"[失败] {coin} 15分钟数据获取失败")
                    self.data_fetcher.symbol = original_symbol
                    continue
                
                # 获取4小时数据
                df_4h = self.data_fetcher.fetch_ohlcv('long')
                
                # 获取日线数据（7天）
                df_1d = self.data_fetcher.fetch_ohlcv('daily')
                
                # 计算技术指标
                df_15m = calculate_technical_indicators(df_15m)
                if df_4h is not None:
                    df_4h = calculate_technical_indicators(df_4h)
                if df_1d is not None:
                    df_1d = calculate_technical_indicators(df_1d)
                
                # 格式化数据
                coin_data = format_market_data(df_15m)
                if df_4h is not None:
                    coin_data['long_timeframe'] = format_market_data(df_4h)
                if df_1d is not None:
                    coin_data['daily_timeframe'] = format_market_data(df_1d)
                
                all_market_data[coin] = coin_data
                
                # 根据价格大小动态调整显示精度
                price = coin_data['price']
                if price < 0.01:
                    price_str = f"${price:.6f}"
                elif price < 1:
                    price_str = f"${price:.4f}"
                elif price < 100:
                    price_str = f"${price:,.2f}"
                else:
                    price_str = f"${price:,.0f}"
                print(f"{coin}当前价格: {price_str}")
                
                # 恢复原始交易对
                self.data_fetcher.symbol = original_symbol
            
            if not all_market_data:
                print("[失败] 所有币种数据获取失败，跳过本周期")
                return
            
            # 4. 获取账户信息
            balance_info = self.data_fetcher.fetch_balance()
            available_balance = 0  # 可用余额
            if balance_info:
                # 直接从OKX获取账户权益
                # 使用info字段中的totalEq（账户总权益）
                if 'info' in balance_info and 'data' in balance_info['info']:
                    data = balance_info['info']['data']
                    if data and len(data) > 0:
                        # totalEq是账户总权益（包含所有持仓的未实现盈亏）
                        total_eq = data[0].get('totalEq', '0')
                        balance = float(total_eq) if total_eq else 0
                        
                        # availEq在账户级别可能是空的，需要从details中获取USDT的可用余额
                        avail_eq = data[0].get('availEq', '0')
                        if not avail_eq or avail_eq == '':
                            # 从details中查找USDT的availEq
                            details = data[0].get('details', [])
                            for detail in details:
                                if detail.get('ccy') == 'USDT':
                                    avail_eq = detail.get('availEq', '0')
                                    break
                        
                        available_balance = float(avail_eq) if avail_eq else 0
                    else:
                        balance = balance_info.get('USDT', {}).get('total', 0)
                        available_balance = balance_info.get('USDT', {}).get('free', 0)
                else:
                    balance = balance_info.get('USDT', {}).get('total', 0)
                    available_balance = balance_info.get('USDT', {}).get('free', 0)
            else:
                balance = TRADING_CONFIG.get('initial_balance', 200.0)
                available_balance = balance
            
            # 5. 获取所有持仓并同步数据库
            all_positions = self.data_fetcher.get_all_positions()
            current_position = all_positions[0] if all_positions else None  # 保持向后兼容
            
            # 5.1 从API同步历史成交到数据库
            synced_count = self.order_sync.sync_filled_orders_from_api()
            
            # 5.1.1 如果有新同步的交易，重新加载MCP
            if synced_count > 0:
                print(f"[MCP] 检测到{synced_count}笔新交易，重新加载MCP数据...")
                self.ai_trader.mcp_memory._restore_from_database()
            
            # 5.2 同步数据库：关闭所有不在持仓中的交易
            self.position_manager.sync_database_with_positions(current_position)
            
            # 显示所有持仓
            if all_positions:
                print(f"当前持仓数量: {len(all_positions)}")
                for pos in all_positions:
                    amount = pos.get('btc_amount', 0)
                    if amount < 1:
                        amount_str = f"{amount:.4f}"
                    else:
                        amount_str = f"{amount:.2f}"
                    
                    print(f"   - {pos.get('symbol')} {pos.get('side')} {amount_str} | 盈亏: ${pos.get('unrealized_pnl', 0):,.2f}")
            # else:
            #     print("[数据] 当前无持仓")  # 静默模式，无持仓时不打印
            
            # 5.5 设置账户统计（如果有的话）
            # TODO: 从API获取真实的账户统计
            # 示例数据（替换为实际API调用）:
            # self.ai_trader.set_account_stats(
            #     total_return_pct=116.25,
            #     total_value=21624.9,
            #     sharpe_ratio=0.468,
            #     available_cash=13654.1,
            #     all_positions=[
            #         {'symbol': 'ETH', 'quantity': 5.74, 'entry_price': 4189.12, ...},
            #         {'symbol': 'BTC', 'quantity': 0.12, 'entry_price': 107343.0, ...},
            #         ...
            #     ]
            # )
            
            # 6. AI分析并决策
            print("\n[AI] AI分析中...\n")
            
            # 传递当前交易ID、周期号和待确认决策给AI
            self.ai_trader.current_trade_id = self.current_trade_id
            self.ai_trader.current_cycle = self.cycle_count
            self.ai_trader.pending_decisions = self.pending_open_decisions
            self.ai_trader.available_balance = available_balance  # 传递可用余额
            
            decision = self.ai_trader.analyze_multi_coins(
                all_coins_data=all_market_data,
                account_balance=balance,
                all_positions=all_positions
            )
            
            # 7. 检测连续HOLD并应用指数退避
            signal = decision.get('signal', 'HOLD')
            has_position = current_position is not None
            
            if signal == 'HOLD' and not has_position and TRADING_CONFIG.get('backoff_enabled', True):
                # 无持仓且HOLD，且启用了退避
                self.consecutive_holds += 1
                
                # 指数退避策略
                threshold = TRADING_CONFIG.get('backoff_threshold', 3)
                max_skip = TRADING_CONFIG.get('backoff_max_skip', 8)
                
                if self.consecutive_holds >= threshold:
                    # 达到阈值后开始退避
                    # 退避周期 = min(2^(n-threshold+1), max_skip)
                    self.skip_cycles = min(2 ** (self.consecutive_holds - threshold + 1), max_skip)
                    print(f"\n💤 连续{self.consecutive_holds}次HOLD，启动指数退避")
                    print(f"   下次AI分析将在{self.skip_cycles + 1}个周期后")
            else:
                # 有交易信号或有持仓，重置计数
                if self.consecutive_holds > 0:
                    print(f"\n[同步] 检测到交易信号，重置退避计数")
                self.consecutive_holds = 0
                self.skip_cycles = 0
            
            # 9. 执行主要交易决策
            if decision.get('signal') != 'HOLD':
                symbol = decision.get('symbol', 'BTC')
                # 清理symbol格式，只保留币种名称
                if '/' in symbol:
                    symbol = symbol.split('/')[0]
                coin_data = all_market_data.get(symbol, {})
                # 使用新的交易执行器
                # 传递周期号和待确认决策
                self.trading_executor.current_cycle = self.cycle_count
                self.trading_executor.pending_open_decisions = self.pending_open_decisions
                
                self.current_trade_id = self.trading_executor.execute_trade(
                    decision, coin_data.get('price', 0), coin_data, 
                    self.current_trade_id, all_market_data
                )
                
                # 同步待确认决策
                self.pending_open_decisions = self.trading_executor.pending_open_decisions
            
            # 10. 执行持仓管理建议（包括平仓、调整止损止盈、以及可能的新开仓）
            position_reviews = decision.get('position_reviews', [])
            if position_reviews:
                if not TRADING_CONFIG.get('test_mode', False):
                    self.trading_executor.execute_position_reviews(position_reviews, all_market_data, all_positions)
                else:
                    print("\n[测试] 测试模式：跳过持仓管理执行")
            
            print(f"\n{'='*70}")
            print(f"周期 #{self.cycle_count} 完成")
            print(f"{'='*70}\n")
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\n[失败] 周期执行出错: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self, interval: int = None):
        """
        运行主循环
        
        Args:
            interval: 循环间隔（秒），默认从配置文件读取
        """
        if interval is None:
            interval = TRADING_CONFIG.get('cycle_interval', 300)
        
        print(f"\n{'='*70}")
        print(f"[启动] 开始运行")
        print(f"   循环间隔: {interval}秒")
        print(f"   测试模式: {'开启' if TRADING_CONFIG.get('test_mode') else '关闭'}")
        print(f"{'='*70}\n")
        
        try:
            while True:
                # 运行一个周期
                self.run_cycle()
                
                # 每10个周期导出一次MCP记忆
                if self.cycle_count % 10 == 0:
                    try:
                        if hasattr(self.ai_trader, 'mcp_filesystem') and hasattr(self.ai_trader, 'mcp_memory'):
                            self.ai_trader.mcp_filesystem.export_mcp_memory(self.ai_trader.mcp_memory)
                    except Exception as e:
                        print(f"[警告] 导出MCP记忆失败: {e}")
                
                # 每24小时同步一次MCP到数据库
                if self.cycle_count % 288 == 0:  # 假设5分钟一个周期，288个周期=24小时
                    try:
                        synced = self.mcp_sync.auto_sync_if_needed(interval_hours=24)
                        if synced > 0:
                            print(f"[同步] 已同步{synced}笔交易到数据库")
                    except Exception as e:
                        print(f"[警告] 同步到数据库失败: {e}")
                
                # 可中断的等待
                print(f"⏳ 等待{interval}秒后开始下一个周期...")
                print(f"   (按 Ctrl+C 停止)\n")
                
                # 分段sleep，每秒检查一次，便于快速响应Ctrl+C
                for i in range(interval):
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print("收到停止信号")
            print(f"{'='*70}\n")
            self.stop()
    
    def stop(self):
        """停止机器人"""
        # AI统计
        ai_stats = self.ai_trader.get_conversation_stats()
        
        # 交易统计
        trade_stats = self.trade_db.get_trade_statistics()
        
        print(f"[数据] 运行统计:")
        print(f"   总周期数: {self.cycle_count}")
        print(f"   对话轮数: {ai_stats['total_rounds']}")
        print(f"   总消息数: {ai_stats['total_messages']}")
        
        print(f"\n[上涨] 交易统计:")
        print(f"   总交易数: {trade_stats['total_trades']}")
        print(f"   未平仓: {trade_stats['open_trades']}")
        print(f"   已平仓: {trade_stats['closed_trades']}")
        if trade_stats['closed_trades'] > 0:
            print(f"   胜率: {trade_stats['win_rate']:.1f}%")
            print(f"   总盈亏: ${trade_stats['total_pnl']:.2f}")
        
        print(f"\n{'='*70}")
        print("交易机器人已停止")
        print(f"{'='*70}\n")


def main():
    """主函数"""
    bot = SimpleAITradingBot()
    
    # 运行（从配置文件读取间隔）
    bot.run()


if __name__ == "__main__":
    # 设置日志文件
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"trading_{datetime.now().strftime('%Y%m%d')}.log")
    sys.stdout = Logger(log_file)
    sys.stderr = sys.stdout
    
    print(f"[日志] 日志文件: {log_file}")
    
    main()
