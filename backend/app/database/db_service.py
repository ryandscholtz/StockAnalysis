"""
Database service for stock analysis storage and retrieval
Supports both SQLite and DynamoDB backends
"""
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, date
from typing import Optional, Dict, List
from pathlib import Path
import os

from app.database.models import Base, StockAnalysis, BatchJob


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, db_path: str = "stock_analysis.db"):
        """
        Initialize database service
        
        Args:
            db_path: Path to SQLite database file
        """
        # Use absolute path or relative to project root
        if not os.path.isabs(db_path):
            # Assume backend directory
            db_path = str(Path(__file__).parent.parent.parent / db_path)
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def has_analysis_today(self, ticker: str, analysis_date: Optional[str] = None) -> bool:
        """
        Check if stock has been analyzed today
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            True if analysis exists for today
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        session = self.get_session()
        try:
            result = session.query(StockAnalysis).filter(
                and_(
                    StockAnalysis.ticker == ticker.upper(),
                    StockAnalysis.analysis_date == analysis_date,
                    StockAnalysis.status == 'success'
                )
            ).first()
            return result is not None
        finally:
            session.close()
    
    def get_analysis(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        """
        Get analysis for a ticker
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            Analysis data dictionary or None
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        session = self.get_session()
        try:
            result = session.query(StockAnalysis).filter(
                and_(
                    StockAnalysis.ticker == ticker.upper(),
                    StockAnalysis.analysis_date == analysis_date
                )
            ).first()
            
            if result:
                return result.to_dict()
            return None
        finally:
            session.close()
    
    def save_analysis(self, 
                     ticker: str,
                     analysis_data: Dict,
                     exchange: Optional[str] = None,
                     analysis_date: Optional[str] = None) -> bool:
        """
        Save analysis to database with comprehensive field extraction
        
        Args:
            ticker: Stock ticker symbol
            analysis_data: Full analysis data dictionary
            exchange: Exchange name (optional)
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            True if saved successfully
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        session = self.get_session()
        try:
            # Extract key fields for quick access
            # Pricing & Valuation
            fair_value = analysis_data.get('fairValue')
            current_price = analysis_data.get('currentPrice')
            margin_of_safety = analysis_data.get('marginOfSafety', {})
            margin_pct = margin_of_safety.get('percentage') if isinstance(margin_of_safety, dict) else margin_of_safety if isinstance(margin_of_safety, (int, float)) else None
            upside_potential = analysis_data.get('upsidePotential')
            price_to_intrinsic = analysis_data.get('priceToIntrinsicValue')
            recommendation = analysis_data.get('recommendation')
            
            # Valuation Breakdown
            valuation = analysis_data.get('valuation', {})
            dcf_value = valuation.get('dcfValue') if isinstance(valuation, dict) else None
            epv_value = valuation.get('epvValue') if isinstance(valuation, dict) else None
            asset_value = valuation.get('assetBasedValue') if isinstance(valuation, dict) else None
            
            # Scores
            financial_health = analysis_data.get('financialHealth', {})
            business_quality = analysis_data.get('businessQuality', {})
            management_quality = analysis_data.get('managementQuality', {})
            
            financial_health_score = financial_health.get('score') if isinstance(financial_health, dict) else None
            business_quality_score = business_quality.get('score') if isinstance(business_quality, dict) else None
            management_quality_score = management_quality.get('score') if isinstance(management_quality, dict) else None
            
            # Company Info
            company_name = analysis_data.get('companyName')
            market_cap = analysis_data.get('marketCap')  # May need to extract from nested data
            sector = analysis_data.get('sector')
            industry = analysis_data.get('industry')
            currency = analysis_data.get('currency')
            
            # Key Metrics
            price_ratios = analysis_data.get('priceRatios', {})
            growth_metrics = analysis_data.get('growthMetrics', {})
            
            pe_ratio = price_ratios.get('peRatio') if isinstance(price_ratios, dict) else None
            pb_ratio = price_ratios.get('pbRatio') if isinstance(price_ratios, dict) else None
            ps_ratio = price_ratios.get('psRatio') if isinstance(price_ratios, dict) else None
            
            revenue_growth = growth_metrics.get('revenueGrowth1Y') if isinstance(growth_metrics, dict) else None
            earnings_growth = growth_metrics.get('earningsGrowth1Y') if isinstance(growth_metrics, dict) else None
            
            # Check if record exists (using composite key)
            existing = session.query(StockAnalysis).filter(
                and_(
                    StockAnalysis.ticker == ticker.upper(),
                    StockAnalysis.analysis_date == analysis_date
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.analysis_data = analysis_data
                existing.company_name = company_name
                existing.current_price = current_price
                existing.fair_value = fair_value
                existing.margin_of_safety_pct = margin_pct
                existing.upside_potential_pct = upside_potential
                existing.price_to_intrinsic_value = price_to_intrinsic
                existing.recommendation = recommendation
                existing.dcf_value = dcf_value
                existing.epv_value = epv_value
                existing.asset_value = asset_value
                existing.financial_health_score = financial_health_score
                existing.business_quality_score = business_quality_score
                existing.management_quality_score = management_quality_score
                existing.market_cap = market_cap
                existing.sector = sector
                existing.industry = industry
                existing.currency = currency
                existing.pe_ratio = pe_ratio
                existing.pb_ratio = pb_ratio
                existing.ps_ratio = ps_ratio
                existing.revenue_growth_1y = revenue_growth
                existing.earnings_growth_1y = earnings_growth
                existing.analyzed_at = datetime.utcnow()
                existing.status = 'success'
                existing.error_message = None
            else:
                # Create new record
                new_analysis = StockAnalysis(
                    ticker=ticker.upper(),
                    analysis_date=analysis_date,
                    exchange=exchange,
                    company_name=company_name,
                    analysis_data=analysis_data,
                    current_price=current_price,
                    fair_value=fair_value,
                    margin_of_safety_pct=margin_pct,
                    upside_potential_pct=upside_potential,
                    price_to_intrinsic_value=price_to_intrinsic,
                    recommendation=recommendation,
                    dcf_value=dcf_value,
                    epv_value=epv_value,
                    asset_value=asset_value,
                    financial_health_score=financial_health_score,
                    business_quality_score=business_quality_score,
                    management_quality_score=management_quality_score,
                    market_cap=market_cap,
                    sector=sector,
                    industry=industry,
                    currency=currency,
                    pe_ratio=pe_ratio,
                    pb_ratio=pb_ratio,
                    ps_ratio=ps_ratio,
                    revenue_growth_1y=revenue_growth,
                    earnings_growth_1y=earnings_growth,
                    status='success'
                )
                session.add(new_analysis)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"Error saving analysis for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()
    
    def save_error(self,
                  ticker: str,
                  error_message: str,
                  exchange: Optional[str] = None,
                  analysis_date: Optional[str] = None) -> bool:
        """
        Save error record for a ticker
        
        Args:
            ticker: Stock ticker symbol
            error_message: Error message
            exchange: Exchange name (optional)
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            True if saved successfully
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        session = self.get_session()
        try:
            existing = session.query(StockAnalysis).filter(
                and_(
                    StockAnalysis.ticker == ticker.upper(),
                    StockAnalysis.analysis_date == analysis_date
                )
            ).first()
            
            if existing:
                existing.status = 'error'
                existing.error_message = error_message[:500]  # Limit length
                existing.analyzed_at = datetime.utcnow()
            else:
                new_analysis = StockAnalysis(
                    ticker=ticker.upper(),
                    exchange=exchange,
                    analysis_date=analysis_date,
                    analysis_data={},
                    status='error',
                    error_message=error_message[:500]
                )
                session.add(new_analysis)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"Error saving error for {ticker}: {e}")
            return False
        finally:
            session.close()
    
    def get_exchange_analyses(self, 
                             exchange: str,
                             analysis_date: Optional[str] = None,
                             limit: Optional[int] = None) -> List[Dict]:
        """
        Get all analyses for an exchange
        
        Args:
            exchange: Exchange name
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
            limit: Maximum number of results
        
        Returns:
            List of analysis dictionaries
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        session = self.get_session()
        try:
            from sqlalchemy import func
            # Use case-insensitive comparison for exchange
            query = session.query(StockAnalysis).filter(
                and_(
                    func.lower(StockAnalysis.exchange) == func.lower(exchange),
                    StockAnalysis.analysis_date == analysis_date,
                    StockAnalysis.status == 'success'
                )
            )
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            return [r.to_dict() for r in results]
        finally:
            session.close()
    
    def create_batch_job(self, exchange: str, ticker_list: List[str]) -> int:
        """
        Create a new batch job record
        
        Args:
            exchange: Exchange name
            ticker_list: List of tickers to process
        
        Returns:
            Batch job ID
        """
        session = self.get_session()
        try:
            job = BatchJob(
                exchange=exchange,
                total_tickers=len(ticker_list),
                ticker_list=ticker_list,
                status='running'
            )
            session.add(job)
            session.commit()
            return job.id
        finally:
            session.close()
    
    def update_batch_job(self, job_id: int, **kwargs) -> bool:
        """
        Update batch job progress
        
        Args:
            job_id: Batch job ID
            **kwargs: Fields to update (processed_tickers, successful_tickers, etc.)
        
        Returns:
            True if updated successfully
        """
        session = self.get_session()
        try:
            job = session.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error updating batch job {job_id}: {e}")
            return False
        finally:
            session.close()
    
    def complete_batch_job(self, job_id: int) -> bool:
        """Mark batch job as completed"""
        return self.update_batch_job(job_id, status='completed', completed_at=datetime.utcnow())

