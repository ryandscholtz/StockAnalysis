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
import json

from app.database.models import Base, StockAnalysis, BatchJob, AIExtractedFinancialData, PDFJob, Watchlist


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
    
    def get_latest_analysis(self, ticker: str) -> Optional[Dict]:
        """
        Get the latest analysis for a ticker (most recent analysis_date)
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Latest analysis data dictionary or None
        """
        session = self.get_session()
        try:
            result = session.query(StockAnalysis).filter(
                StockAnalysis.ticker == ticker.upper()
            ).order_by(StockAnalysis.analysis_date.desc()).first()
            
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
                # New fields
                existing.business_type = analysis_data.get('businessType')
                analysis_weights = analysis_data.get('analysisWeights')
                if analysis_weights:
                    import json
                    existing.analysis_weights = json.dumps(analysis_weights) if isinstance(analysis_weights, dict) else analysis_weights
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
                    status='success',
                    business_type=analysis_data.get('businessType'),
                    analysis_weights=json.dumps(analysis_data.get('analysisWeights')) if analysis_data.get('analysisWeights') else None
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
    
    # PDF Job Management
    def create_pdf_job(self, ticker: str, filename: str = None, total_pages: int = 0) -> int:
        """
        Create a new PDF processing job
        
        Args:
            ticker: Stock ticker symbol
            filename: PDF filename (optional)
            total_pages: Total number of pages in PDF
        
        Returns:
            PDF job ID
        """
        session = self.get_session()
        try:
            job = PDFJob(
                ticker=ticker.upper(),
                filename=filename,
                total_pages=total_pages,
                status='running'
            )
            session.add(job)
            session.commit()
            return job.id
        finally:
            session.close()
    
    def get_pdf_job(self, job_id: int) -> Optional[Dict]:
        """Get PDF job by ID"""
        session = self.get_session()
        try:
            job = session.query(PDFJob).filter(PDFJob.id == job_id).first()
            if job:
                return job.to_dict()
            return None
        finally:
            session.close()
    
    def update_pdf_job(self, job_id: int, **kwargs) -> bool:
        """
        Update PDF job progress
        
        Args:
            job_id: PDF job ID
            **kwargs: Fields to update (pages_processed, current_page, current_task, status, etc.)
        
        Returns:
            True if updated successfully
        """
        session = self.get_session()
        try:
            job = session.query(PDFJob).filter(PDFJob.id == job_id).first()
            if job:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error updating PDF job {job_id}: {e}")
            return False
        finally:
            session.close()
    
    def complete_pdf_job(self, job_id: int, result: Dict = None, extraction_details: Dict = None) -> bool:
        """Mark PDF job as completed with results"""
        return self.update_pdf_job(
            job_id,
            status='completed',
            completed_at=datetime.utcnow(),
            result=result,
            extraction_details=extraction_details
        )
    
    def fail_pdf_job(self, job_id: int, error_message: str) -> bool:
        """Mark PDF job as failed"""
        return self.update_pdf_job(
            job_id,
            status='failed',
            completed_at=datetime.utcnow(),
            error_message=error_message
        )
    
    def save_ai_extracted_data(self, 
                               ticker: str,
                               data_type: str,
                               period: str,
                               data: Dict,
                               source: str = 'pdf_upload',
                               extraction_method: str = 'llama_vision') -> bool:
        """
        Save AI-extracted financial data to database
        
        Args:
            ticker: Stock ticker symbol
            data_type: Type of data (income_statement, balance_sheet, cashflow, key_metrics)
            period: Period identifier (YYYY-MM-DD or 'latest')
            data: Financial data dictionary
            source: Source of data (pdf_upload, manual_entry, etc.)
            extraction_method: Method used (llama_vision, etc.)
        
        Returns:
            True if saved successfully
        """
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            
            # Check if record exists
            existing = session.query(AIExtractedFinancialData).filter(
                and_(
                    AIExtractedFinancialData.ticker == ticker_upper,
                    AIExtractedFinancialData.data_type == data_type,
                    AIExtractedFinancialData.period == period
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.data = data
                existing.extracted_at = datetime.utcnow()
                existing.source = source
                existing.extraction_method = extraction_method
            else:
                # Create new record
                new_record = AIExtractedFinancialData(
                    ticker=ticker_upper,
                    data_type=data_type,
                    period=period,
                    data=data,
                    source=source,
                    extraction_method=extraction_method
                )
                session.add(new_record)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error saving AI-extracted data for {ticker}: {e}")
            return False
        finally:
            session.close()
    
    def get_ai_extracted_data(self, ticker: str, data_type: Optional[str] = None) -> Dict:
        """
        Get AI-extracted financial data for a ticker
        
        Args:
            ticker: Stock ticker symbol
            data_type: Optional filter for specific data type (income_statement, balance_sheet, etc.)
        
        Returns:
            Dictionary organized by data_type and period
        """
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            
            query = session.query(AIExtractedFinancialData).filter(
                AIExtractedFinancialData.ticker == ticker_upper
            )
            
            if data_type:
                query = query.filter(AIExtractedFinancialData.data_type == data_type)
            
            records = query.all()
            
            # Organize by data_type and period
            result = {
                'income_statement': {},
                'balance_sheet': {},
                'cashflow': {},
                'key_metrics': {}
            }
            
            for record in records:
                if record.data_type in result:
                    result[record.data_type][record.period] = record.data
            
            # Remove empty sections
            result = {k: v for k, v in result.items() if v}
            
            return result
        except Exception as e:
            print(f"Error getting AI-extracted data for {ticker}: {e}")
            return {}
        finally:
            session.close()
    
    def has_ai_extracted_data(self, ticker: str) -> bool:
        """Check if AI-extracted data exists for a ticker"""
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            count = session.query(AIExtractedFinancialData).filter(
                AIExtractedFinancialData.ticker == ticker_upper
            ).count()
            return count > 0
        except Exception as e:
            print(f"Error checking AI-extracted data for {ticker}: {e}")
            return False
        finally:
            session.close()
    
    # Watchlist methods
    def add_to_watchlist(self, ticker: str, company_name: Optional[str] = None, exchange: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """Add a stock to the watchlist"""
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            # Check if already in watchlist
            existing = session.query(Watchlist).filter(Watchlist.ticker == ticker_upper).first()
            if existing:
                # Update existing entry
                if company_name:
                    existing.company_name = company_name
                if exchange:
                    existing.exchange = exchange
                if notes is not None:
                    existing.notes = notes
                existing.updated_at = datetime.utcnow()
            else:
                # Create new entry
                watchlist_item = Watchlist(
                    ticker=ticker_upper,
                    company_name=company_name,
                    exchange=exchange,
                    notes=notes
                )
                session.add(watchlist_item)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error adding to watchlist: {e}")
            return False
        finally:
            session.close()
    
    def remove_from_watchlist(self, ticker: str) -> bool:
        """Remove a stock from the watchlist"""
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            watchlist_item = session.query(Watchlist).filter(Watchlist.ticker == ticker_upper).first()
            if watchlist_item:
                session.delete(watchlist_item)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error removing from watchlist: {e}")
            return False
        finally:
            session.close()
    
    def get_watchlist(self) -> List[Dict]:
        """Get all stocks in the watchlist"""
        session = self.get_session()
        try:
            items = session.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
            return [item.to_dict() for item in items]
        except Exception as e:
            print(f"Error getting watchlist: {e}")
            return []
        finally:
            session.close()
    
    def get_latest_analyses_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get latest analysis for multiple tickers in one efficient query"""
        session = self.get_session()
        try:
            from sqlalchemy import and_
            latest_analyses = {}
            
            # Get latest analysis for each ticker
            for ticker in tickers:
                ticker_upper = ticker.upper()
                latest = session.query(StockAnalysis).filter(
                    StockAnalysis.ticker == ticker_upper
                ).order_by(StockAnalysis.analysis_date.desc()).first()
                
                if latest:
                    latest_analyses[ticker_upper] = {
                        'analysis_date': latest.analysis_date,
                        'current_price': latest.current_price,
                        'fair_value': latest.fair_value,
                        'margin_of_safety_pct': latest.margin_of_safety_pct,
                        'recommendation': latest.recommendation,
                        'analyzed_at': latest.analyzed_at.isoformat() if latest.analyzed_at else None,
                        'financial_health_score': latest.financial_health_score,
                        'business_quality_score': latest.business_quality_score,
                        'market_cap': latest.market_cap,
                        'sector': latest.sector,
                        'industry': latest.industry
                    }
            
            return latest_analyses
        except Exception as e:
            print(f"Error getting latest analyses batch: {e}")
            return {}
        finally:
            session.close()
    
    def get_watchlist_item(self, ticker: str) -> Optional[Dict]:
        """Get a specific watchlist item"""
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            item = session.query(Watchlist).filter(Watchlist.ticker == ticker_upper).first()
            if item:
                return item.to_dict()
            return None
        except Exception as e:
            print(f"Error getting watchlist item: {e}")
            return None
        finally:
            session.close()
    
    def update_watchlist_item(self, ticker: str, company_name: Optional[str] = None, exchange: Optional[str] = None, notes: Optional[str] = None, 
                              current_price: Optional[float] = None, fair_value: Optional[float] = None, 
                              margin_of_safety_pct: Optional[float] = None, recommendation: Optional[str] = None,
                              last_analyzed_at: Optional[datetime] = None) -> bool:
        """Update a watchlist item with analysis data"""
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            item = session.query(Watchlist).filter(Watchlist.ticker == ticker_upper).first()
            if item:
                if company_name is not None:
                    item.company_name = company_name
                if exchange is not None:
                    item.exchange = exchange
                if notes is not None:
                    item.notes = notes
                if current_price is not None:
                    item.current_price = current_price
                if fair_value is not None:
                    item.fair_value = fair_value
                if margin_of_safety_pct is not None:
                    item.margin_of_safety_pct = margin_of_safety_pct
                if recommendation is not None:
                    item.recommendation = recommendation
                if last_analyzed_at is not None:
                    item.last_analyzed_at = last_analyzed_at
                item.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error updating watchlist item: {e}")
            return False
        finally:
            session.close()
    
    def is_in_watchlist(self, ticker: str) -> bool:
        """Check if a ticker is in the watchlist"""
        session = self.get_session()
        try:
            ticker_upper = ticker.upper()
            count = session.query(Watchlist).filter(Watchlist.ticker == ticker_upper).count()
            return count > 0
        except Exception as e:
            print(f"Error checking watchlist: {e}")
            return False
        finally:
            session.close()

