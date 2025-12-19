import json
import logging
from pathlib import Path
from typing import Optional, List, Union

logger = logging.getLogger(__name__)


class LocalBlobStorage:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized LocalBlobStorage at {self.base_path}")
    
    def save_file(self, blob_path: str, content: Union[bytes, dict, str]):
        file_path = self.base_path / blob_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(content, dict):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
        elif isinstance(content, str):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)
        
        logger.debug(f"Saved file: {blob_path}")
    
    def read_file(self, blob_path: str) -> Optional[Union[bytes, dict]]:
        file_path = self.base_path / blob_path
        if not file_path.exists():
            return None
        
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(file_path, 'rb') as f:
                return f.read()
    
    def file_exists(self, blob_path: str) -> bool:
        file_path = self.base_path / blob_path
        return file_path.exists()
    
    def list_files(self, prefix: str) -> List[str]:
        prefix_path = self.base_path / prefix
        if not prefix_path.exists():
            return []
        
        files = []
        for file_path in prefix_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.base_path)
                files.append(str(relative_path).replace('\\', '/'))
        
        return files
    
    def delete_file(self, blob_path: str):
        file_path = self.base_path / blob_path
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted file: {blob_path}")


class LocalTableStorage:
    def __init__(self, table_file_path: str):
        self.table_file_path = Path(table_file_path)
        self.table_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_table()
    
    def _load_table(self):
        if self.table_file_path.exists():
            with open(self.table_file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {}
    
    def _save_table(self):
        with open(self.table_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get_entity(self, partition_key: str, row_key: str) -> Optional[dict]:
        table_name = self.table_file_path.stem
        if table_name not in self.data:
            return None
        if partition_key not in self.data[table_name]:
            return None
        return self.data[table_name][partition_key].get(row_key)
    
    def create_entity(self, entity: dict):
        table_name = self.table_file_path.stem
        partition_key = entity['PartitionKey']
        row_key = entity['RowKey']
        
        if table_name not in self.data:
            self.data[table_name] = {}
        if partition_key not in self.data[table_name]:
            self.data[table_name][partition_key] = {}
        
        self.data[table_name][partition_key][row_key] = entity
        self._save_table()
    
    def update_entity(self, entity: dict):
        self.create_entity(entity)
    
    def upsert_entity(self, entity: dict):
        self.create_entity(entity)
