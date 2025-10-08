"""
AWS Athena client for AR tool
Handles database operations and S3 integration
"""

import boto3
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
import time

from config.database import DATABASE_CONFIG, AWS_CONFIG, ATHENA_CONFIG
from data.models import NormalizedContent, ContentScores, AuthenticityRatio

logger = logging.getLogger(__name__)

class AthenaClient:
    """Client for AWS Athena operations"""
    
    def __init__(self):
        self.athena_client = boto3.client(
            'athena',
            region_name=AWS_CONFIG['region'],
            aws_access_key_id=AWS_CONFIG['access_key_id'],
            aws_secret_access_key=AWS_CONFIG['secret_access_key']
        )
        self.s3_client = boto3.client(
            's3',
            region_name=AWS_CONFIG['region'],
            aws_access_key_id=AWS_CONFIG['access_key_id'],
            aws_secret_access_key=AWS_CONFIG['secret_access_key']
        )
    
    def execute_query(self, query: str, wait: bool = True) -> str:
        """Execute Athena query and return execution ID"""
        response = self.athena_client.start_query_execution(
            QueryString=query,
            WorkGroup=DATABASE_CONFIG['workgroup'],
            ResultConfiguration={
                'OutputLocation': ATHENA_CONFIG['output_location'],
                'EncryptionConfiguration': ATHENA_CONFIG['encryption_configuration']
            }
        )
        
        execution_id = response['QueryExecutionId']
        logger.info(f"Started query execution: {execution_id}")
        
        if wait:
            self._wait_for_completion(execution_id)
        
        return execution_id
    
    def _wait_for_completion(self, execution_id: str) -> None:
        """Wait for query completion"""
        while True:
            response = self.athena_client.get_query_execution(
                QueryExecutionId=execution_id
            )
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                logger.info(f"Query {execution_id} completed successfully")
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                raise Exception(f"Query {execution_id} failed: {reason}")
            
            time.sleep(1)
    
    def get_query_results(self, execution_id: str) -> pd.DataFrame:
        """Get query results as DataFrame"""
        response = self.athena_client.get_query_results(
            QueryExecutionId=execution_id
        )
        
        # Parse results
        columns = [col['Label'] for col in response['ResultSet']['ResultSetMetadata']['ColumnInfo']]
        rows = []
        
        for row in response['ResultSet']['Rows'][1:]:  # Skip header
            rows.append([field.get('VarCharValue', '') for field in row['Data']])
        
        return pd.DataFrame(rows, columns=columns)
    
    def upload_normalized_content(self, content_list: List[NormalizedContent], 
                                brand_id: str, source: str, run_id: str) -> None:
        """Upload normalized content to S3 as Parquet"""
        import pyarrow as pa
        import pyarrow.parquet as pq
        from io import BytesIO
        
        # Convert to DataFrame
        data = []
        for content in content_list:
            data.append({
                'content_id': content.content_id,
                'src': content.src,
                'platform_id': content.platform_id,
                'author': content.author,
                'title': content.title,
                'body': content.body,
                'rating': content.rating,
                'upvotes': content.upvotes,
                'helpful_count': content.helpful_count,
                'event_ts': content.event_ts,
                'run_id': run_id,
                'meta': json.dumps(content.meta)
            })
        
        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        
        # Create Parquet in memory
        buffer = BytesIO()
        pq.write_table(table, buffer, compression='snappy')
        buffer.seek(0)
        
        # Upload to S3
        key = f"brand_id={brand_id}/source={source}/run_id={run_id}/normalized_content.parquet"
        self.s3_client.put_object(
            Bucket='ar-ingestion-normalized',
            Key=key,
            Body=buffer.getvalue(),
            ContentType='application/octet-stream'
        )
        
        logger.info(f"Uploaded {len(content_list)} normalized content items to s3://ar-ingestion-normalized/{key}")
    
    def upload_content_scores(self, scores_list: List[ContentScores], 
                            brand_id: str, source: str, run_id: str) -> None:
        """Upload content scores to S3 as Parquet"""
        import pyarrow as pa
        import pyarrow.parquet as pq
        from io import BytesIO
        
        # Convert to DataFrame
        data = []
        for score in scores_list:
            data.append({
                'content_id': score.content_id,
                'brand': score.brand,
                'src': score.src,
                'event_ts': score.event_ts,
                'score_provenance': score.score_provenance,
                'score_resonance': score.score_resonance,
                'score_coherence': score.score_coherence,
                'score_transparency': score.score_transparency,
                'score_verification': score.score_verification,
                'class_label': score.class_label,
                'is_authentic': score.is_authentic,
                'rubric_version': score.rubric_version,
                'run_id': run_id,
                'meta': score.meta
            })
        
        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        
        # Create Parquet in memory
        buffer = BytesIO()
        pq.write_table(table, buffer, compression='snappy')
        buffer.seek(0)
        
        # Upload to S3
        key = f"scores/brand_id={brand_id}/source={source}/run_id={run_id}/content_scores.parquet"
        self.s3_client.put_object(
            Bucket='ar-ingestion-normalized',
            Key=key,
            Body=buffer.getvalue(),
            ContentType='application/octet-stream'
        )
        
        logger.info(f"Uploaded {len(scores_list)} content scores to s3://ar-ingestion-normalized/{key}")
    
    def calculate_authenticity_ratio(self, brand_id: str, run_id: str, 
                                   sources: List[str] = None) -> AuthenticityRatio:
        """Calculate AR using the KPI query from schema"""
        if sources is None:
            sources = DATABASE_CONFIG['supported_sources']
        
        source_filter = "', '".join(sources)
        
        query = f"""
        SELECT
            n.brand_id, n.source, n.run_id,
            COUNT(*) AS total_items,
            SUM(CASE WHEN s.is_authentic THEN 1 ELSE 0 END) AS authentic_items,
            SUM(CASE WHEN s.class_label = 'suspect' THEN 1 ELSE 0 END) AS suspect_items,
            SUM(CASE WHEN s.class_label = 'inauthentic' THEN 1 ELSE 0 END) AS inauthentic_items,
            100.0 * SUM(CASE WHEN s.is_authentic THEN 1 ELSE 0 END) / COUNT(*) AS authenticity_ratio_pct
        FROM {DATABASE_CONFIG['view_name']} n
        JOIN {DATABASE_CONFIG['scores_table']} s
            ON n.content_id = s.content_id
           AND n.brand_id = s.brand_id
           AND n.source = s.source
           AND n.run_id = s.run_id
        WHERE n.brand_id = '{brand_id}' 
          AND n.run_id = '{run_id}'
          AND n.source IN ('{source_filter}')
        GROUP BY n.brand_id, n.source, n.run_id
        ORDER BY n.run_id DESC
        """
        
        execution_id = self.execute_query(query)
        results = self.get_query_results(execution_id)
        
        if results.empty:
            return AuthenticityRatio(
                brand_id=brand_id,
                source=','.join(sources),
                run_id=run_id,
                total_items=0,
                authentic_items=0,
                suspect_items=0,
                inauthentic_items=0,
                authenticity_ratio_pct=0.0
            )
        
        # Aggregate across sources
        total_items = results['total_items'].sum()
        authentic_items = results['authentic_items'].sum()
        suspect_items = results['suspect_items'].sum()
        inauthentic_items = results['inauthentic_items'].sum()
        ar_pct = results['authenticity_ratio_pct'].mean()
        
        return AuthenticityRatio(
            brand_id=brand_id,
            source=','.join(sources),
            run_id=run_id,
            total_items=int(total_items),
            authentic_items=int(authentic_items),
            suspect_items=int(suspect_items),
            inauthentic_items=int(inauthentic_items),
            authenticity_ratio_pct=float(ar_pct)
        )
    
    def repair_tables(self) -> None:
        """Repair partition projection tables (from schema comments)"""
        tables = [DATABASE_CONFIG['normalized_table'], DATABASE_CONFIG['scores_table']]
        
        for table in tables:
            # Disable projection
            disable_query = f"ALTER TABLE {table} SET TBLPROPERTIES ('partition_projection.enabled'='false')"
            self.execute_query(disable_query)
            
            # Repair partitions
            repair_query = f"MSCK REPAIR TABLE {table}"
            self.execute_query(repair_query)
            
            # Re-enable projection
            enable_query = f"ALTER TABLE {table} SET TBLPROPERTIES ('partition_projection.enabled'='true')"
            self.execute_query(enable_query)
            
            logger.info(f"Repaired table {table}")
