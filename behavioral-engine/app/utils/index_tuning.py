"""
Dynamic index tuning utilities for pgvector
Automatically recommends and applies optimal index configurations
"""

import math
from typing import Dict, Any, List, Tuple
import logging

from app.database import execute_query, get_db_connection

logger = logging.getLogger(__name__)


class IndexTuner:
    """
    Utility for dynamic pgvector index tuning
    """
    
    async def get_table_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all tables with vector indexes
        
        Returns:
            Dictionary with table statistics
        """
        query = """
            SELECT 
                'behavioral_memory' as table_name,
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('behavioral_memory')) as total_size,
                pg_total_relation_size('behavioral_memory') as size_bytes
            FROM behavioral_memory
            UNION ALL
            SELECT 
                'chat_history' as table_name,
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('chat_history')) as total_size,
                pg_total_relation_size('chat_history') as size_bytes
            FROM chat_history
        """
        
        results = await execute_query(query)
        
        stats = {}
        for row in results:
            stats[row['table_name']] = {
                'row_count': int(row['row_count']),
                'total_size': row['total_size'],
                'size_bytes': int(row['size_bytes'])
            }
        
        return stats
    
    async def recommend_lists_parameter(
        self,
        table_name: str,
        row_count: int
    ) -> int:
        """
        Recommend optimal lists parameter for IVFFlat index
        
        Formula: lists = sqrt(row_count)
        Constraints: 50 <= lists <= 1000
        
        Args:
            table_name: Name of the table
            row_count: Number of rows in table
            
        Returns:
            Recommended lists parameter
        """
        if row_count < 1000:
            # For small datasets, use minimum
            recommended = 50
        elif row_count > 1000000:
            # For very large datasets, cap at 1000
            recommended = 1000
        else:
            # Use sqrt formula
            recommended = int(math.sqrt(row_count))
            # Ensure within bounds
            recommended = max(50, min(1000, recommended))
        
        logger.info(f"Recommended lists for {table_name} ({row_count} rows): {recommended}")
        return recommended
    
    async def get_current_index_config(
        self,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Get current index configuration
        
        Args:
            table_name: Name of the table
            
        Returns:
            Index configuration details
        """
        query = """
            SELECT 
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = $1
            AND indexname LIKE '%embedding%'
        """
        
        results = await execute_query(query, table_name)
        
        if results:
            row = results[0]
            # Extract lists parameter from indexdef
            indexdef = row['indexdef']
            lists = None
            if 'lists' in indexdef:
                # Parse lists = N from index definition
                import re
                match = re.search(r'lists\s*=\s*(\d+)', indexdef)
                if match:
                    lists = int(match.group(1))
            
            return {
                'index_name': row['indexname'],
                'index_def': indexdef,
                'index_size': row['index_size'],
                'current_lists': lists
            }
        
        return {}
    
    async def rebuild_index(
        self,
        table_name: str,
        index_name: str,
        new_lists: int
    ) -> bool:
        """
        Rebuild index with new lists parameter
        
        Args:
            table_name: Name of the table
            index_name: Name of the index
            new_lists: New lists parameter value
            
        Returns:
            Success status
        """
        try:
            async with get_db_connection() as conn:
                # Drop existing index
                logger.info(f"Dropping index {index_name}...")
                await conn.execute(f"DROP INDEX IF EXISTS {index_name}")
                
                # Create new index with updated lists
                logger.info(f"Creating index with lists={new_lists}...")
                create_query = f"""
                    CREATE INDEX {index_name} ON {table_name}
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {new_lists})
                """
                await conn.execute(create_query)
                
                # Analyze table
                logger.info(f"Analyzing {table_name}...")
                await conn.execute(f"ANALYZE {table_name}")
                
                logger.info(f"Index {index_name} rebuilt successfully with lists={new_lists}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to rebuild index {index_name}: {e}")
            return False
    
    async def auto_tune_indexes(
        self,
        dry_run: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Automatically tune all vector indexes
        
        Args:
            dry_run: If True, only recommend changes without applying
            
        Returns:
            List of tuning recommendations/actions
        """
        recommendations = []
        
        # Get table statistics
        stats = await self.get_table_stats()
        
        for table_name, table_stats in stats.items():
            row_count = table_stats['row_count']
            
            # Get current index config
            index_config = await self.get_current_index_config(table_name)
            
            if not index_config:
                logger.warning(f"No vector index found for {table_name}")
                continue
            
            # Recommend new lists parameter
            recommended_lists = await self.recommend_lists_parameter(table_name, row_count)
            current_lists = index_config.get('current_lists')
            
            # Check if tuning is needed
            if current_lists and abs(current_lists - recommended_lists) > 10:
                recommendation = {
                    'table': table_name,
                    'index': index_config['index_name'],
                    'current_lists': current_lists,
                    'recommended_lists': recommended_lists,
                    'row_count': row_count,
                    'index_size': index_config['index_size'],
                    'action': 'rebuild_recommended'
                }
                
                if not dry_run:
                    # Apply tuning
                    success = await self.rebuild_index(
                        table_name,
                        index_config['index_name'],
                        recommended_lists
                    )
                    recommendation['applied'] = success
                else:
                    recommendation['applied'] = False
                
                recommendations.append(recommendation)
            else:
                recommendations.append({
                    'table': table_name,
                    'index': index_config['index_name'],
                    'current_lists': current_lists,
                    'recommended_lists': recommended_lists,
                    'row_count': row_count,
                    'action': 'no_change_needed'
                })
        
        return recommendations
    
    async def get_index_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for vector indexes
        
        Returns:
            Performance statistics
        """
        query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan as index_scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes
            WHERE indexname LIKE '%embedding%'
        """
        
        results = await execute_query(query)
        
        stats = {}
        for row in results:
            stats[row['indexname']] = {
                'table': row['tablename'],
                'scans': int(row['index_scans']),
                'tuples_read': int(row['tuples_read']),
                'tuples_fetched': int(row['tuples_fetched'])
            }
        
        return stats


# Global instance
_index_tuner = None


async def get_index_tuner() -> IndexTuner:
    """
    Get or create the global index tuner instance
    
    Returns:
        IndexTuner instance
    """
    global _index_tuner
    if _index_tuner is None:
        _index_tuner = IndexTuner()
    return _index_tuner
