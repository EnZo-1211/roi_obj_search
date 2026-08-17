import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


class TaskHistoryManager:
    def __init__(self, storage_path: str = "/home/projects/discovery/roi_object_search/volumes/task_history.json"):
        import os
        # Force absolute path resolution
        self.storage_path = os.path.abspath(storage_path)
        self.ensure_storage_exists()
    
    def ensure_storage_exists(self):
        """Create storage file if it doesn't exist"""
        storage_dir = os.path.dirname(self.storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
        
        if not os.path.exists(self.storage_path):
            self.save_history({"tasks": []})
    
    def load_history(self) -> Dict[str, Any]:
        """Load task history from storage"""
        try:
            import os
            import fcntl
            abs_path = os.path.abspath(self.storage_path)
            print(f"TASK HISTORY DEBUG: Loading from path: {self.storage_path}")
            print(f"TASK HISTORY DEBUG: Absolute path: {abs_path}")
            print(f"TASK HISTORY DEBUG: Current working directory: {os.getcwd()}")
            with open(self.storage_path, 'r') as f:
                # Lock file to ensure consistent reads
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = json.load(f)
                print(f"TASK HISTORY DEBUG: Loaded {len(data.get('tasks', []))} tasks from file")
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading task history: {e}")
            return {"tasks": []}
    
    def save_history(self, history: Dict[str, Any]):
        """Save task history to storage"""
        try:
            import fcntl
            # Write to temp file first, then atomic rename
            temp_path = self.storage_path + '.tmp'
            with open(temp_path, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(history, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename ensures consistency
            os.rename(temp_path, self.storage_path)
            print(f"TASK HISTORY DEBUG: Successfully wrote {len(history['tasks'])} tasks to file")
        except Exception as e:
            print(f"Error saving task history: {e}")
            # Clean up temp file if it exists
            temp_path = self.storage_path + '.tmp'
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def add_task(self, task_data: Dict[str, Any]) -> str:
        """Add a new task to history"""
        try:
            print(f"TASK HISTORY DEBUG: Starting add_task for task_id: {task_data.get('task_id')}")
            history = self.load_history()
            print(f"TASK HISTORY DEBUG: Loaded history with {len(history['tasks'])} existing tasks")
            task_data['timestamp'] = datetime.utcnow().isoformat()
            history['tasks'].append(task_data)
            print(f"TASK HISTORY DEBUG: Added task, now have {len(history['tasks'])} tasks")
            
            # Keep only last 1000 tasks to prevent unlimited growth
            history['tasks'] = history['tasks'][-1000:]
            print(f"TASK HISTORY DEBUG: After cleanup, have {len(history['tasks'])} tasks")
            
            print(f"TASK HISTORY DEBUG: About to save history to {self.storage_path}")
            self.save_history(history)
            print(f"TASK HISTORY DEBUG: Successfully saved history")
            return task_data['task_id']
        except Exception as e:
            print(f"TASK HISTORY ERROR: Error adding task to history: {e}")
            import traceback
            print(f"TASK HISTORY ERROR: Full traceback: {traceback.format_exc()}")
            return task_data.get('task_id', '')
    
    def update_task_status(self, task_id: str, status: str, result_data: Dict[str, Any] = None):
        """Update task status and result data"""
        try:
            history = self.load_history()
            for task in history['tasks']:
                if task['task_id'] == task_id:
                    task['status'] = status
                    task['updated_at'] = datetime.utcnow().isoformat()
                    if result_data:
                        task.update(result_data)
                    break
            self.save_history(history)
        except Exception as e:
            print(f"Error updating task status: {e}")
    
    def get_history(self, project_id: Optional[int] = None, with_description_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
        """Get task history with optional filtering"""
        try:
            history = self.load_history()
            tasks = history['tasks']
            
            # Filter by project_id if specified
            if project_id:
                tasks = [t for t in tasks if t.get('project_id') == project_id]
            
            # Filter to only tasks with descriptions if specified
            if with_description_only:
                tasks = [t for t in tasks if t.get('description') and t.get('description').strip()]
            
            # Sort by timestamp (newest first) and limit
            tasks = sorted(tasks, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
            
            return tasks
        except Exception as e:
            print(f"Error getting task history: {e}")
            return []
    
    def get_completed_searches(self, project_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get completed searches with descriptions for dropdown"""
        try:
            history = self.load_history()
            tasks = history['tasks']
            
            # Filter for completed tasks with descriptions only
            tasks = [t for t in tasks 
                    if t.get('status') == 'completed' 
                    and t.get('description') 
                    and t.get('description').strip()
                    and t.get('hash_value')]
            
            # Filter by project_id if specified
            if project_id:
                tasks = [t for t in tasks if t.get('project_id') == project_id]
            
            # Sort by timestamp (newest first) and limit
            tasks = sorted(tasks, key=lambda x: x.get('updated_at', x.get('timestamp', '')), reverse=True)[:limit]
            
            # Return simplified data for dropdown
            return [{
                'description': task['description'],
                'hash_value': task['hash_value'],
                'project_id': task['project_id'],
                'timestamp': task.get('updated_at', task.get('timestamp', '')),
                'biosample': task.get('biosample'),
                'stain': task.get('stain')
            } for task in tasks]
        except Exception as e:
            print(f"Error getting completed searches: {e}")
            return []

    def get_active_tasks(self, project_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all active tasks (processing status) with descriptions"""
        try:
            history = self.load_history()
            tasks = history['tasks']
            
            # Filter for processing tasks with descriptions only
            tasks = [t for t in tasks 
                    if t.get('status') == 'processing' 
                    and t.get('description') 
                    and t.get('description').strip()]
            
            # Filter by project_id if specified
            if project_id:
                tasks = [t for t in tasks if t.get('project_id') == project_id]
            
            # Sort by timestamp (newest first) and limit
            tasks = sorted(tasks, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
            
            return tasks
        except Exception as e:
            print(f"Error getting active tasks: {e}")
            return []
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from history"""
        try:
            history = self.load_history()
            original_count = len(history['tasks'])
            history['tasks'] = [t for t in history['tasks'] if t['task_id'] != task_id]
            
            if len(history['tasks']) < original_count:
                self.save_history(history)
                return True
            return False
        except Exception as e:
            print(f"Error deleting task from history: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID (either generated task_id or celery_task_id)"""
        try:
            history = self.load_history()
            for task in history['tasks']:
                # Check both the generated task_id and the celery_task_id
                if (task.get('task_id') == task_id or 
                    task.get('celery_task_id') == task_id):
                    return task
            return None
        except Exception as e:
            print(f"Error getting task by ID: {e}")
            return None


# Global instance
task_history_manager = TaskHistoryManager()