"""
Database models for storing stock analysis results
"""
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
from typing import Optional, Dict
import json

Base = declarative_base()


class StockAnalysis(Base):
    """Store stock analysis results"""
    __tablename__ = 'stock_analyses'
    
    # Composite primary key (ticker + date allows multiple analyses per ticker)
    ticker = Column(String(20), primary_key=True)
    analysis_date = Column(String(10), primary_key=True, nullable=False)  # YYYY-MM-DD format
    
    exchange = Column(String(50), nullable=True, index=True)
    company_name = Column(String(200), nullable=True)
    
    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Analysis results (stored as JSON for flexibility)
    analysis_data = Column(JSON, nullable=False)
    
    # Quick access fields for filtering/sorting (extracted from JSON)
    # Pricing & Valuation
    current_price = Column(Float, nullable=True, index=True)
    fair_value = Column(Float, nullable=True, index=True)
    margin_of_safety_pct = Column(Float, nullable=True, index=True)
    upside_potential_pct = Column(Float, nullable=True)
    price_to_intrinsic_value = Column(Float, nullable=True)
    recommendation = Column(String(20), nullable=True, index=True)  # Strong Buy, Buy, Hold, Avoid
    
    # Valuation Breakdown
    dcf_value = Column(Float, nullable=True)
    epv_value = Column(Float, nullable=True)
    asset_value = Column(Float, nullable=True)
    
    # Scores
    financial_health_score = Column(Float, nullable=True, index=True)
    business_quality_score = Column(Float, nullable=True, index=True)
    management_quality_score = Column(Float, nullable=True)
    
    # Company Info
    market_cap = Column(Float, nullable=True, index=True)
    sector = Column(String(100), nullable=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    currency = Column(String(10), nullable=True)
    
    # Key Metrics (for filtering)
    pe_ratio = Column(Float, nullable=True, index=True)
    pb_ratio = Column(Float, nullable=True)
    ps_ratio = Column(Float, nullable=True)
    revenue_growth_1y = Column(Float, nullable=True)
    earnings_growth_1y = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default='success', nullable=False)  # success, error, partial
    error_message = Column(String(500), nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_ticker_date', 'ticker', 'analysis_date'),
        Index('idx_exchange_date', 'exchange', 'analysis_date'),
        Index('idx_recommendation_date', 'recommendation', 'analysis_date'),
        Index('idx_margin_safety', 'margin_of_safety_pct', 'analysis_date'),
        Index('idx_quality_scores', 'business_quality_score', 'financial_health_score'),
        Index('idx_sector_industry', 'sector', 'industry'),
    )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'ticker': self.ticker,
            'analysis_date': self.analysis_date,
            'exchange': self.exchange,
            'company_name': self.company_name,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'analysis_data': self.analysis_data,
            # Pricing & Valuation
            'current_price': self.current_price,
            'fair_value': self.fair_value,
            'margin_of_safety_pct': self.margin_of_safety_pct,
            'upside_potential_pct': self.upside_potential_pct,
            'price_to_intrinsic_value': self.price_to_intrinsic_value,
            'recommendation': self.recommendation,
            # Valuation Breakdown
            'dcf_value': self.dcf_value,
            'epv_value': self.epv_value,
            'asset_value': self.asset_value,
            # Scores
            'financial_health_score': self.financial_health_score,
            'business_quality_score': self.business_quality_score,
            'management_quality_score': self.management_quality_score,
            # Company Info
            'market_cap': self.market_cap,
            'sector': self.sector,
            'industry': self.industry,
            'currency': self.currency,
            # Key Metrics
            'pe_ratio': self.pe_ratio,
            'pb_ratio': self.pb_ratio,
            'ps_ratio': self.ps_ratio,
            'revenue_growth_1y': self.revenue_growth_1y,
            'earnings_growth_1y': self.earnings_growth_1y,
            # Status
            'status': self.status,
            'error_message': self.error_message
        }


class BatchJob(Base):
    """Track batch analysis jobs"""
    __tablename__ = 'batch_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default='running', nullable=False)  # running, completed, failed, cancelled
    total_tickers = Column(Integer, nullable=False)
    processed_tickers = Column(Integer, default=0)
    successful_tickers = Column(Integer, default=0)
    failed_tickers = Column(Integer, default=0)
    ticker_list = Column(JSON, nullable=True)  # List of tickers in this batch
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'exchange': self.exchange,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'total_tickers': self.total_tickers,
            'processed_tickers': self.processed_tickers,
            'successful_tickers': self.successful_tickers,
            'failed_tickers': self.failed_tickers,
            'progress_pct': (self.processed_tickers / self.total_tickers * 100) if self.total_tickers > 0 else 0
        }

