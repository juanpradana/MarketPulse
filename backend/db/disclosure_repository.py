"""Disclosure repository for IDX disclosures operations."""
import pandas as pd
from typing import Optional, List, Dict, Tuple
from .connection import BaseRepository


class DisclosureRepository(BaseRepository):
    """Repository for IDX corporate disclosures."""
    
    def insert_disclosure(self, data: Dict):
        """
        Insert a single disclosure record into database.
        Uses INSERT OR IGNORE to skip duplicates based on download_url.
        
        Args:
            data: Disclosure data dictionary
        """
        conn = self._get_conn()
        try:
            query = """
            INSERT OR IGNORE INTO idx_disclosures 
            (ticker, title, published_date, download_url, local_path)
            VALUES (?, ?, ?, ?, ?)
            """
            
            row = (
                data.get('ticker', '').strip(),
                data.get('title'),
                data.get('date'),
                data.get('download_url'),
                data.get('local_path', '')
            )
            
            conn.execute(query, row)
            conn.commit()
        except Exception as e:
            print(f"[!] Error inserting disclosure: {e}")
        finally:
            conn.close()
    
    def get_disclosures(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch corporate disclosures from database.
        
        Args:
            ticker: Filter by ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records
            offset: Offset for pagination
        
        Returns:
            Pandas DataFrame with disclosures
        """
        conn = self._get_conn()
        try:
            query = "SELECT * FROM idx_disclosures WHERE 1=1"
            params = []

            # Ticker Filter
            if ticker and ticker != "^JKSE":
                # Handle cases where ticker passes in as "BBRI.JK" vs "BBRI"
                clean_ticker = ticker.replace(".JK", "")
                query += " AND ticker LIKE ?"
                params.append(f"%{clean_ticker}%")

            # Date Filter
            if start_date:
                query += " AND date(published_date) >= date(?)"
                params.append(str(start_date))

            if end_date:
                query += " AND date(published_date) <= date(?)"
                params.append(str(end_date))

            query += " ORDER BY published_date DESC"

            # Pagination
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
                if offset is not None:
                    query += " OFFSET ?"
                    params.append(offset)

            df = pd.read_sql(query, conn, params=params)
            return df

        except Exception as e:
            print(f"[!] Error fetching disclosures from DB: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def update_local_path(self, download_url: str, local_path: str, status: str = 'DOWNLOADED'):
        """
        Update local_path and processed_status for a disclosure by download_url.
        
        Args:
            download_url: The unique download URL identifier
            local_path: Local filesystem path where file was saved
            status: New status (default: DOWNLOADED)
        """
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE idx_disclosures SET local_path = ?, processed_status = ? WHERE download_url = ?",
                (local_path, status, download_url)
            )
            conn.commit()
        except Exception as e:
            print(f"[!] Error updating disclosure path: {e}")
        finally:
            conn.close()
    
    def update_status(self, doc_id: int, status: str, summary: Optional[str] = None):
        """
        Update processed_status and optionally ai_summary for a disclosure.
        
        Args:
            doc_id: The disclosure record ID
            status: New status (PENDING, DOWNLOADED, COMPLETED, FAILED)
            summary: Optional AI-generated summary
        """
        conn = self._get_conn()
        try:
            if summary is not None:
                conn.execute(
                    "UPDATE idx_disclosures SET processed_status = ?, ai_summary = ? WHERE id = ?",
                    (status, summary, doc_id)
                )
            else:
                conn.execute(
                    "UPDATE idx_disclosures SET processed_status = ? WHERE id = ?",
                    (status, doc_id)
                )
            conn.commit()
        except Exception as e:
            print(f"[!] Error updating disclosure status: {e}")
        finally:
            conn.close()
    
    def get_pending_disclosures(self) -> List[Tuple]:
        """
        Get disclosures that need processing (PENDING or DOWNLOADED status).
        
        Returns:
            List of (id, local_path, ticker, title) tuples
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, local_path, ticker, title FROM idx_disclosures "
                "WHERE processed_status IN ('PENDING', 'DOWNLOADED') "
                "AND local_path IS NOT NULL AND local_path != ''"
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"[!] Error fetching pending disclosures: {e}")
            return []
        finally:
            conn.close()
    
    def delete_disclosures_by_ids(self, doc_ids: List[int]):
        """
        Delete disclosure records by their IDs.
        
        Args:
            doc_ids: List of disclosure record IDs to delete
        """
        if not doc_ids:
            return
        conn = self._get_conn()
        try:
            placeholders = ",".join(["?" for _ in doc_ids])
            conn.execute(
                f"DELETE FROM idx_disclosures WHERE id IN ({placeholders})",
                doc_ids
            )
            conn.commit()
        except Exception as e:
            print(f"[!] Error deleting disclosures: {e}")
        finally:
            conn.close()
    
    def get_all_disclosures_paths(self) -> List[Tuple[int, str]]:
        """
        Get raw IDs and paths for all disclosures.
        
        Returns:
            List of (id, local_path) tuples
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, local_path FROM idx_disclosures")
            return cursor.fetchall()
        except Exception as e:
            print(f"[!] Error fetching disclosure paths: {e}")
            return []
        finally:
            conn.close()
