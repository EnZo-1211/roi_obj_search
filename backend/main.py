from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import sys
import hashlib
import traceback
from pathlib import Path
import json
import datetime


# Using proper imports with PYTHONPATH

from obj_search_utils.obj_matching import run_object_matching
from task_history import TaskHistoryManager

# Use the same path as Celery worker  
task_history_manager = TaskHistoryManager('/apps/volumes/task_history.json')

def generate_task_id(bbox, project_id, biosample, section, stain):
    """Generate a unique task ID based on request parameters"""
    task_data = f"{bbox}_{project_id}_{biosample}_{section}_{stain}_{datetime.datetime.utcnow().timestamp()}"
    return hashlib.md5(task_data.encode("utf-8")).hexdigest()

def save_task_to_history(request, task_id, hash_value, status='processing', celery_task_id=None, save_for_mapping_only=False):
    """Save a task to history"""
    print(f"DEBUG: Saving task with description: '{request.description}'")
    print(f"DEBUG: Description check: {request.description and request.description.strip()}")
    print(f"DEBUG: save_for_mapping_only: {save_for_mapping_only}")
    try:
        task_data = {
            'task_id': task_id,
            'project_id': request.project_id,
            'biosample': request.biosample,
            'section': request.section,
            'stain': request.stain,
            'bbox': request.bbox,
            'hash_value': hash_value,
            'status': status
        }
        
        # Only include description if this is not a mapping-only save
        if not save_for_mapping_only:
            task_data['description'] = request.description
        # For mapping-only saves, we don't include description so it won't appear in dropdown
        
        # Store Celery task ID if provided (for async tasks)
        if celery_task_id:
            task_data['celery_task_id'] = celery_task_id
            print(f"DEBUG: Also storing Celery task ID: {celery_task_id}")
            
        task_history_manager.add_task(task_data)
        print(f"Task {task_id} saved to history with status: {status}")
    except Exception as e:
        print(f"Failed to save task to history: {e}")

def update_task_history_status(task_id, status, result_data=None):
    """Update task status in history"""
    try:
        task_history_manager.update_task_status(task_id, status, result_data)
        print(f"Task {task_id} status updated to: {status}")
    except Exception as e:
        print(f"Failed to update task history: {e}")

# Optional Celery imports - only load if needed
try:
    from obj_search_utils.section_counter import count_sections_for_project, count_sections_for_biosample
    from celery_config import celery_app
    from celery_tasks import process_object_matching
    CELERY_AVAILABLE = True
except ImportError as e:
    print(f"Celery components not available: {e}")
    CELERY_AVAILABLE = False

app = FastAPI(
    title="ROI Object Search API",
    description="API for running object matching across brain histological sections",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class ObjectMatchingRequest(BaseModel):
    bbox: List[float] = Field(..., description="Bounding box coordinates [x1, y1, x2, y2]", min_length=4, max_length=4)
    stain: str = Field(default="NISL", description="Tissue stain type")
    biosample: int = Field(..., description="Brain specimen identifier", gt=0)
    project_id: int = Field(..., description="Research project identifier", gt=0)
    section: int = Field(..., description="Histological section number", gt=0)
    description: Optional[str] = Field(None, description="Optional task description", max_length=500)

class ObjectMatchingResponse(BaseModel):
    success: bool
    message: str
    output_directory: str
    hash_value: str
    processed_sections: int
    bbox: List[float]
    biosample: int
    project_id: int
    section: int
    stain: str

class AsyncObjectMatchingRequest(BaseModel):
    bbox: List[float] = Field(..., description="Bounding box coordinates [x1, y1, x2, y2]", min_length=4, max_length=4)
    stain: str = Field(default="NISL", description="Tissue stain type")
    biosample: int = Field(..., description="Brain specimen identifier", gt=0)
    project_id: int = Field(..., description="Research project identifier", gt=0)
    section: int = Field(..., description="Histological section number", gt=0)
    description: Optional[str] = Field(None, description="Optional task description", max_length=500)

class AsyncTaskResponse(BaseModel):
    task_id: str
    message: str
    section_count: int
    processing_mode: str
    project_id: int
    estimated_time: str
    hash_value: Optional[str] = None
    celery_task_id: Optional[str] = None  # For debugging/advanced progress tracking

class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    current: Optional[int] = None
    total: Optional[int] = None
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # Biosample tracking fields
    current_biosample: Optional[int] = None
    total_biosamples: Optional[int] = None
    current_biosample_id: Optional[str] = None

class TaskHistoryItem(BaseModel):
    task_id: str
    description: Optional[str] = None
    timestamp: str
    project_id: int
    biosample: int
    section: int
    stain: str
    bbox: List[float]
    hash_value: str
    status: str
    updated_at: Optional[str] = None

class TaskHistoryResponse(BaseModel):
    tasks: List[TaskHistoryItem]
    total_count: int

class CompletedSearchItem(BaseModel):
    description: str
    hash_value: str
    project_id: int
    timestamp: str
    biosample: Optional[int] = None
    stain: Optional[str] = None

class CompletedSearchesResponse(BaseModel):
    searches: List[CompletedSearchItem]
    total_count: int

@app.get("/")
async def root():
    return {"message": "ROI Object Search API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "roi_object_search"}

@app.get("/task-history", response_model=TaskHistoryResponse)
async def get_task_history(
    project_id: Optional[int] = None,
    limit: int = 50,
    with_description_only: bool = True
):
    """
    Get task history, optionally filtered by project and description presence.
    
    - **project_id**: Filter by specific project ID (optional)
    - **limit**: Maximum number of tasks to return (default: 50)
    - **with_description_only**: Only return tasks that have descriptions (default: true)
    """
    try:
        tasks = task_history_manager.get_history(
            project_id=project_id,
            with_description_only=with_description_only,
            limit=limit
        )
        
        return TaskHistoryResponse(
            tasks=tasks,
            total_count=len(tasks)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving task history: {str(e)}"
        )

@app.get("/completed-searches", response_model=CompletedSearchesResponse)
async def get_completed_searches(
    project_id: Optional[int] = None,
    limit: int = 50
):
    """
    Get completed searches with descriptions for dropdown display.
    
    - **project_id**: Filter by specific project ID (optional)  
    - **limit**: Maximum number of searches to return (default: 50)
    """
    try:
        searches = task_history_manager.get_completed_searches(
            project_id=project_id,
            limit=limit
        )
        
        return CompletedSearchesResponse(
            searches=searches,
            total_count=len(searches)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving completed searches: {str(e)}"
        )

@app.get("/active-tasks")
async def get_active_tasks(project_id: Optional[int] = None):
    """
    Get all active tasks (processing status) with their current progress.
    
    - **project_id**: Filter by specific project ID (optional)
    """
    try:
        from src.celery_config import celery_app
        
        # Get all tasks with 'processing' status from history
        active_tasks = task_history_manager.get_active_tasks(project_id=project_id)
        
        # Also check for any processing tasks WITHOUT descriptions that might be stuck
        all_processing = task_history_manager.get_history(project_id=project_id, with_description_only=False, limit=100)
        processing_without_desc = [t for t in all_processing if t.get('status') == 'processing' and not (t.get('description') and t.get('description').strip())]
        
        if processing_without_desc:
            print(f"FOUND PROCESSING TASKS WITHOUT DESCRIPTIONS: {len(processing_without_desc)} tasks")
            for task in processing_without_desc:
                print(f"  Task {task['task_id'][:8]}... - Status: {task.get('status')} - No description")
                # Mark these as failed too since they won't show in UI but keep polling
                from datetime import datetime, timedelta
                try:
                    task_start = datetime.fromisoformat(task.get('timestamp', ''))
                    time_since_start = datetime.utcnow() - task_start
                    
                    if time_since_start > timedelta(minutes=2):
                        print(f"MARKING STALE TASK WITHOUT DESCRIPTION AS FAILED: {task['task_id'][:8]}...")
                        task_history_manager.update_task_status(
                            task['task_id'], 
                            'failed', 
                            {'error': f'Task without description stuck for {time_since_start.total_seconds()/60:.1f} minutes'}
                        )
                except:
                    pass
        
        # For each active task, get current progress from Celery
        tasks_with_progress = []
        for task in active_tasks:
            celery_task_id = task.get('celery_task_id')
            if celery_task_id:
                try:
                    # Get task status from Celery
                    celery_task = celery_app.AsyncResult(celery_task_id)
                    task_info = celery_task.info if celery_task.info else {}
                    celery_status = celery_task.status
                    
                    # Current progress values
                    current_progress = task_info.get('current_section', 0)
                    progress_percent = task_info.get('progress_percent', 0)
                    
                    # Check for stale progress (stuck for 3+ minutes)
                    from datetime import datetime, timedelta
                    now = datetime.utcnow()
                    
                    # Get last known progress from task history
                    last_progress = task.get('last_progress', {})
                    last_progress_value = last_progress.get('current', -1)
                    last_progress_time = last_progress.get('timestamp')
                    
                    # If progress hasn't changed and it's been more than 1 minute
                    if (last_progress_value == current_progress and 
                        last_progress_time and 
                        current_progress > 0):  # Only check if task has actually started
                        
                        try:
                            last_time = datetime.fromisoformat(last_progress_time)
                            time_stuck = now - last_time
                            time_stuck_minutes = time_stuck.total_seconds() / 60
                            
                            print(f"STALE TASK DEBUG: Task {task['task_id'][:8]}... stuck at progress {current_progress} for {time_stuck_minutes:.1f} minutes")
                            
                            if time_stuck > timedelta(minutes=1):
                                print(f"STALE TASK DETECTED: Marking task {task['task_id'][:8]}... as failed after {time_stuck_minutes:.1f} minutes without progress")
                                # Progress is stuck - mark task as failed
                                task_history_manager.update_task_status(
                                    task['task_id'], 
                                    'failed', 
                                    {'error': f'Task stuck at {current_progress} progress for {time_stuck_minutes:.1f} minutes'}
                                )
                                # Skip this task
                                continue
                        except Exception as e:
                            print(f"STALE TASK DEBUG ERROR: Failed to parse timestamp for task {task['task_id'][:8]}...: {e}")
                            # If timestamp parsing fails, continue normally
                            pass
                    
                    # Update progress tracking if progress has changed
                    if last_progress_value != current_progress:
                        print(f"PROGRESS UPDATE: Task {task['task_id'][:8]}... progress changed from {last_progress_value} to {current_progress}")
                        task_history_manager.update_task_status(
                            task['task_id'],
                            'processing',  # Keep as processing
                            {
                                'last_progress': {
                                    'current': current_progress,
                                    'timestamp': now.isoformat()
                                }
                            }
                        )
                    
                    # Check for failed/revoked Celery tasks
                    if celery_status in ['REVOKED', 'FAILURE']:
                        task_history_manager.update_task_status(
                            task['task_id'], 
                            'failed', 
                            {'error': f'Celery task {celery_status.lower()}'}
                        )
                        continue
                    
                    # Check for tasks stuck in PENDING status (workers down)
                    if celery_status == 'PENDING':
                        from datetime import datetime, timedelta
                        try:
                            task_start = datetime.fromisoformat(task.get('timestamp', ''))
                            time_since_start = datetime.utcnow() - task_start
                            
                            if time_since_start > timedelta(minutes=2):
                                print(f"STALE TASK DETECTED: Task {task['task_id'][:8]}... stuck in PENDING status for {time_since_start.total_seconds()/60:.1f} minutes - marking as failed")
                                task_history_manager.update_task_status(
                                    task['task_id'], 
                                    'failed', 
                                    {'error': f'Task stuck in PENDING status for {time_since_start.total_seconds()/60:.1f} minutes (workers likely down)'}
                                )
                                continue
                        except:
                            pass
                    
                    # Add progress information
                    task['progress'] = {
                        'current': current_progress,
                        'total': task_info.get('total_sections', 1),
                        'status_message': task_info.get('status', 'Processing...'),
                        'progress_percent': progress_percent,
                        'celery_status': celery_status
                    }
                    
                except Exception as e:
                    # If we can't get Celery info at all, likely worker is down
                    print(f"CELERY CONNECTION ERROR: Cannot get status for task {task['task_id'][:8]}... - {str(e)}")
                    
                    # Check if task has been stuck for too long
                    from datetime import datetime, timedelta
                    try:
                        task_start = datetime.fromisoformat(task.get('timestamp', ''))
                        time_since_start = datetime.utcnow() - task_start
                        
                        if time_since_start > timedelta(minutes=2):
                            print(f"STALE TASK DETECTED: Task {task['task_id'][:8]}... has no Celery connection for {time_since_start.total_seconds()/60:.1f} minutes - marking as failed")
                            task_history_manager.update_task_status(
                                task['task_id'], 
                                'failed', 
                                {'error': f'Worker connection lost for {time_since_start.total_seconds()/60:.1f} minutes'}
                            )
                            continue
                    except:
                        pass
                    
                    # If we can't get Celery info at all, mark as connection lost
                    task['progress'] = {
                        'current': 0,
                        'total': 1,
                        'status_message': 'Connection lost - checking status...',
                        'progress_percent': 0,
                        'celery_status': 'UNKNOWN'
                    }
            else:
                task['progress'] = {
                    'current': 0,
                    'total': 1,
                    'status_message': 'Starting...',
                    'progress_percent': 0,
                    'celery_status': 'PENDING'
                }
            
            tasks_with_progress.append(task)
        
        return {
            "active_tasks": tasks_with_progress,
            "total_count": len(tasks_with_progress)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving active tasks: {str(e)}"
        )

@app.delete("/task-history/{task_id}")
async def delete_task_history(task_id: str):
    """
    Delete a specific task from history.
    
    - **task_id**: The task identifier to delete
    """
    try:
        success = task_history_manager.delete_task(task_id)
        if success:
            return {"message": f"Task {task_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting task: {str(e)}"
        )

@app.put("/task-history/{task_id}/complete")
async def complete_task_history(task_id: str, processed_sections: int = 0):
    """
    Mark a task as completed in history.
    
    - **task_id**: The task identifier to mark as completed
    - **processed_sections**: Number of sections processed (optional)
    """
    try:
        # Check if task exists
        task = task_history_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task status to completed
        update_task_history_status(task_id, 'completed', {
            'processed_sections': processed_sections
        })
        
        return {"message": f"Task {task_id} marked as completed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error completing task: {str(e)}"
        )

@app.get("/task-history/{task_id}/redirect")
async def redirect_to_task_result(task_id: str):
    """
    Get redirect URL for a specific task's results.
    
    - **task_id**: The task identifier
    """
    try:
        task = task_history_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task['status'] != 'completed':
            raise HTTPException(status_code=400, detail=f"Task is {task['status']}, results not available")
        
        redirect_url = f"/roi/viewer/{task['project_id']}/{task['hash_value']}"
        return {"redirect_url": redirect_url, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting task redirect: {str(e)}"
        )


@app.get("/project/{project_id}/section-count")
async def get_project_section_count(project_id: int, stain: str = "NISL"):
    """
    Get the total number of sections for a project and biosample breakdown.
    
    - **project_id**: Research project identifier
    - **stain**: Tissue stain type (default: "NISL")
    """
    try:
        section_info = count_sections_for_project(project_id, stain)
        
        if "error" in section_info:
            raise HTTPException(status_code=400, detail=section_info["error"])
        
        return section_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving section count: {str(e)}"
        )

@app.get("/{project_id}/{hash_value}/{biosample}/{stain}/{filename}")
async def get_image(project_id: int, hash_value: str, biosample: int, stain: str, filename: str):
    """
    Serve result images from the analysis output directory.
    
    - **project_id**: Research project identifier
    - **hash_value**: Hash value from the analysis
    - **biosample**: Brain specimen identifier
    - **stain**: Tissue stain type
    - **filename**: Image filename (e.g., "1297.png")
    """
    try:
        # Check both possible file paths
        possible_paths = [
            f"/home/projects/discovery/roi_object_search/volumes/results/{project_id}/{hash_value}/{biosample}/{stain}/{filename}",
            f"/apps/volumes/results/{project_id}/{hash_value}/{biosample}/{stain}/{filename}"
        ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Return the image file
        return FileResponse(file_path)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error serving image: {str(e)}"
        )

@app.get("/results/{project_id}/{hash_value}")
async def get_results_tree(project_id: int, hash_value: str, request: Request):
    """
    Get all result images and metadata in a tree structure.
    
    - **project_id**: Research project identifier
    - **hash_value**: Hash value from the analysis
    
    Returns tree structure: project_id -> biosample -> stain -> sections (with image URLs)
    """
    try:
        # Check both possible result directories
        possible_paths = [
            f"/home/projects/discovery/roi_object_search/volumes/results/{project_id}/{hash_value}",
            f"/apps/volumes/results/{project_id}/{hash_value}"
        ]
        
        base_path = None
        for path in possible_paths:
            if os.path.exists(path):
                base_path = path
                break
        
        if not base_path:
            raise HTTPException(status_code=404, detail="Results not found for this project/hash combination")
        
        # Get base URL for constructing image URLs
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        results_tree = {}
        
        # Walk through the directory structure
        for biosample_dir in Path(base_path).iterdir():
            if biosample_dir.is_dir():
                biosample = biosample_dir.name
                results_tree[biosample] = {}
                
                for stain_dir in biosample_dir.iterdir():
                    if stain_dir.is_dir():
                        stain = stain_dir.name
                        results_tree[biosample][stain] = {}
                        
                        # Get all image files in this stain directory
                        image_files = []
                        for image_file in stain_dir.glob("*.png"):
                            section = image_file.stem  # filename without extension
                            image_url = f"{base_url}/{project_id}/{hash_value}/{biosample}/{stain}/{image_file.name}"
                            
                            image_files.append({
                                "section": section,
                                "image_url": image_url,
                                "filename": image_file.name
                            })
                        
                        # Sort by section number if they're numeric
                        try:
                            image_files.sort(key=lambda x: int(x["section"]))
                        except ValueError:
                            # If sections aren't numeric, sort alphabetically
                            image_files.sort(key=lambda x: x["section"])
                        
                        results_tree[biosample][stain] = image_files
        
        response = {
            "project_id": project_id,
            "hash_value": hash_value,
            "total_biosamples": len(results_tree),
            "results": results_tree
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving results: {str(e)}"
        )

@app.get("/roi/results/{project_id}/{hash_value}")
async def get_roi_results_tree(project_id: int, hash_value: str, request: Request):
    """
    ROI-prefixed endpoint for getting result images and metadata.
    This is what the plugin expects.
    """
    return await get_results_tree(project_id, hash_value, request)

@app.get("/roi/viewer/{project_id}/{hash_value}", response_class=HTMLResponse)
async def serve_viewer(project_id: int, hash_value: str):
    """
    Serve the ROI results viewer HTML page.
    
    - **project_id**: Research project identifier
    - **hash_value**: Hash value from the analysis
    """
    try:
        viewer_path = os.path.join(os.path.dirname(__file__), "viewer.html")
        with open(viewer_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Viewer not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving viewer: {str(e)}")

@app.post("/match-objects-async", response_model=AsyncTaskResponse)
async def match_objects_async(request: AsyncObjectMatchingRequest):
    print(f"DEBUG REQUEST: Received request with description: '{request.description}', type: {type(request.description)}")
    print(f"DEBUG REQUEST: Full request data: bbox={request.bbox}, project_id={request.project_id}, biosample={request.biosample}, section={request.section}, stain={request.stain}, description={request.description}")
    """
    Run object matching analysis with automatic queue management based on biosample size.
    
    If the biosample has >25 sections, the job will be processed asynchronously using Celery.
    If the biosample has ≤25 sections, it will be processed synchronously.
    
    - **bbox**: Bounding box coordinates as [x1, y1, x2, y2]
    - **stain**: Tissue stain type (default: "NISL")
    - **biosample**: Brain specimen identifier
    - **project_id**: Research project identifier  
    - **section**: Target histological section number
    """
    try:
        # Import Celery components only when needed
        from src.celery_tasks import process_object_matching
        
        # Count sections for the specific biosample within this project
        section_info = count_sections_for_biosample(request.biosample, request.stain, request.project_id)
        
        if "error" in section_info:
            raise HTTPException(status_code=400, detail=section_info["error"])
        
        total_sections = section_info["section_count"]
        
        if total_sections > 10:
            # Generate hash for async processing too
            hash_box = str(request.bbox)
            hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
            
            # Generate unique task ID for history tracking
            task_id = generate_task_id(request.bbox, request.project_id, request.biosample, request.section, request.stain)
            
            # Check if task has description for completion tracking
            print(f"DEBUG ASYNC: About to check description. Description: '{request.description}', stripped: '{request.description.strip() if request.description else None}'")
            has_description = bool(request.description and request.description.strip())
            
            # Use async Celery for large biosample (many sections)
            task = process_object_matching.delay(
                bbox=request.bbox,
                stain=request.stain,
                biosample=request.biosample,
                project_id=request.project_id,
                section=request.section,
                history_task_id=task_id if has_description else None
            )
            
            # Always save task for ID mapping, but only with description if provided
            if has_description:
                print(f"DEBUG ASYNC: Saving task to history with description")
                save_task_to_history(request, task_id, hash_value, 'processing', task.id)
                print(f"DEBUG ASYNC: Task saved. Verifying task exists in history...")
                # Verify the task was saved
                saved_task = task_history_manager.get_task(task_id)
                print(f"DEBUG ASYNC: Verification - task found: {saved_task is not None}")
                if saved_task:
                    print(f"DEBUG ASYNC: Verification - task has description: {bool(saved_task.get('description'))}")
                    print(f"DEBUG ASYNC: Verification - task description value: '{saved_task.get('description')}'")
                else:
                    print(f"DEBUG ASYNC: ERROR - Task not found immediately after saving!")
            else:
                print(f"DEBUG ASYNC: Saving task to history for ID mapping only (no description)")
                save_task_to_history(request, task_id, hash_value, 'processing', task.id, save_for_mapping_only=True)
            
            # Estimate processing time (rough estimate: 2 seconds per section)
            estimated_minutes = (total_sections * 2) // 60
            estimated_time = f"~{max(1, estimated_minutes)} minutes"
            
            return AsyncTaskResponse(
                task_id=task_id,  # Return generated task ID for history tracking
                message=f"Large biosample detected ({total_sections} sections). Processing asynchronously for biosample {request.biosample}.",
                section_count=total_sections,
                processing_mode="async",
                project_id=request.project_id,
                estimated_time=estimated_time,
                hash_value=hash_value,
                celery_task_id=task.id  # Celery task ID for progress tracking
            )
        else:
            # For smaller biosamples, use synchronous processing (original obj_matching behavior)
            # Generate hash and task ID before processing
            hash_box = str(request.bbox)
            hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
            task_id = generate_task_id(request.bbox, request.project_id, request.biosample, request.section, request.stain)
            
            # Save task to history before processing (if description provided)
            print(f"DEBUG SYNC: About to check description. Description: '{request.description}', stripped: '{request.description.strip() if request.description else None}'")
            has_description = bool(request.description and request.description.strip())
            if has_description:
                print(f"DEBUG SYNC: Description check passed, saving task to history")
                save_task_to_history(request, task_id, hash_value, 'processing')
            else:
                print(f"DEBUG SYNC: Description check failed, NOT saving to history")

            # Call original synchronous obj_matching function directly
            result = run_object_matching(
                bbox=request.bbox,
                stain=request.stain,
                biosample=request.biosample,
                project_id=request.project_id,
                section=request.section
            )
            
            if result["success"]:
                # Update task history to completed status (if description was provided)
                print(f"DEBUG SYNC COMPLETE: About to update task status. Description: '{request.description}', stripped: '{request.description.strip() if request.description else None}'")
                print(f"DEBUG SYNC COMPLETE: has_description stored value: {has_description}")
                if has_description:
                    print(f"DEBUG SYNC COMPLETE: Updating task status to completed")
                    update_task_history_status(task_id, 'completed', {
                        'processed_sections': result.get('processed_sections', total_sections)
                    })
                else:
                    print(f"DEBUG SYNC COMPLETE: Description check failed, NOT updating task status")
                
                # Return synchronous result in AsyncTaskResponse format for consistency
                return AsyncTaskResponse(
                    task_id=task_id,  # Return our generated task ID instead of "sync_completed"
                    message=f"Small biosample detected ({total_sections} sections). Processed synchronously for biosample {request.biosample}.",
                    section_count=total_sections,
                    processing_mode="sync",
                    project_id=request.project_id,
                    estimated_time="Completed",
                    hash_value=hash_value
                )
            else:
                # Update task history to failed status (if description was provided)
                if request.description and request.description.strip():
                    update_task_history_status(task_id, 'failed', {'error': result.get('error', 'Unknown error')})
                
                raise HTTPException(status_code=500, detail=result["error"])
            
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available - Celery components missing"
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in match_objects_async: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/progress/{task_id}")
async def get_task_progress(task_id: str):
    """
    Get the real-time progress of a task with section-level granularity.
    
    - **task_id**: The task identifier returned from match-objects-async
    
    Returns:
        - completed_sections: Number of sections processed so far
        - total_sections: Total number of sections to process  
        - status: Current processing status
        - error: Error message if any
    """
    try:
        # Special case for synchronous tasks
        if task_id == "sync_completed":
            return {
                "completed_sections": 1,
                "total_sections": 1,
                "status": "Completed synchronously",
                "error": None
            }
        
        # Check if this is a generated task ID - if so, get the Celery task ID
        celery_task_id = task_id
        task_history_record = task_history_manager.get_task(task_id)
        if task_history_record and task_history_record.get('celery_task_id'):
            celery_task_id = task_history_record['celery_task_id']
            print(f"PROGRESS DEBUG: Mapped generated task ID {task_id} to Celery task ID {celery_task_id}")
        else:
            # If no mapping found, assume task_id is already a Celery task ID
            print(f"PROGRESS DEBUG: No mapping found, treating {task_id} as Celery task ID")
        
        # Get task result from Celery using the correct Celery task ID
        task = celery_app.AsyncResult(celery_task_id)
        
        # Debug logging to see what we're getting
        print(f"PROGRESS DEBUG: task_id={task_id}")
        print(f"PROGRESS DEBUG: task.state={task.state}")
        print(f"PROGRESS DEBUG: task.info={task.info}")
        print(f"PROGRESS DEBUG: task.result={task.result}")
        
        if task.state == 'PENDING':
            print("PROGRESS DEBUG: Returning PENDING state")
            return {
                "completed_sections": 0,
                "total_sections": 0,
                "remaining_sections": 0,
                "status": "Task is waiting to be processed",
                "error": None
            }
        elif task.state == 'PROGRESS':
            # Extract section progress from task info
            current = task.info.get('current_section', 0)
            total = task.info.get('total_sections', 1)
            remaining = max(0, total - current)
            status = task.info.get('status', 'Processing...')
            
            print(f"PROGRESS DEBUG: Returning PROGRESS - current={current}, total={total}, remaining={remaining}")
            
            return {
                "completed_sections": current,
                "total_sections": total,
                "remaining_sections": remaining,
                "status": status,
                "error": None
            }
        elif task.state == 'SUCCESS':
            # Task completed successfully
            total = task.result.get('total_sections', 1)
            return {
                "completed_sections": total,
                "total_sections": total,
                "remaining_sections": 0,
                "status": "Completed successfully",
                "error": None
            }
        else:  # FAILURE
            return {
                "completed_sections": 0,
                "total_sections": 0,
                "remaining_sections": 0,
                "status": "Task failed",
                "error": task.info.get('error', str(task.result) if task.result else 'Unknown error')
            }
        
    except Exception as e:
        return {
            "completed_sections": 0,
            "total_sections": 0,
            "remaining_sections": 0,
            "status": "Error checking progress",
            "error": str(e)
        }

@app.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of an asynchronous object matching task.
    
    - **task_id**: The task identifier returned from match-objects-async
    """
    try:
        # Check if this is a generated task ID - if so, get the Celery task ID
        celery_task_id = task_id
        task_history_record = task_history_manager.get_task(task_id)
        if task_history_record and task_history_record.get('celery_task_id'):
            celery_task_id = task_history_record['celery_task_id']
            print(f"TASK STATUS DEBUG: Mapped generated task ID {task_id} to Celery task ID {celery_task_id}")
        else:
            # If no mapping found, assume task_id is already a Celery task ID
            print(f"TASK STATUS DEBUG: No mapping found, treating {task_id} as Celery task ID")
        
        # Get task result from Celery using the correct Celery task ID
        task = celery_app.AsyncResult(celery_task_id)
        
        if task.state == 'PENDING':
            response = TaskStatusResponse(
                task_id=task_id,
                state=task.state,
                status='Task is waiting to be processed'
            )
        elif task.state == 'PROGRESS':
            # Extract section progress from task info - handle case where task.info might be None
            if task.info:
                current_section = task.info.get('current_section', 0)
                total_sections = task.info.get('total_sections', 1)
                current_biosample = task.info.get('current_biosample', 0)
                total_biosamples = task.info.get('total_biosamples', 1)
                current_biosample_id = task.info.get('current_biosample_id')
                status = task.info.get('status', f'Processing {current_section}/{total_sections} sections')
            else:
                current_section = 0
                total_sections = 1
                current_biosample = 0
                total_biosamples = 1
                current_biosample_id = None
                status = 'Processing...'
            
            response = TaskStatusResponse(
                task_id=task_id,
                state=task.state,
                current=current_section,
                total=total_sections,
                status=status,
                current_biosample=current_biosample,
                total_biosamples=total_biosamples,
                current_biosample_id=current_biosample_id
            )
        elif task.state == 'SUCCESS':
            # Get final section counts - handle case where task.result might be None
            if task.result:
                total_sections = task.result.get('total_sections', task.result.get('current_section', 1))
                status = task.result.get('status', 'Completed')
                result = task.result.get('result')
            else:
                total_sections = 1
                status = 'Completed'
                result = None
            
            response = TaskStatusResponse(
                task_id=task_id,
                state=task.state,
                current=total_sections,
                total=total_sections,
                status=status,
                result=result
            )
        else:  # FAILURE
            # Handle case where task.info might be None
            if task.info:
                status = task.info.get('status', 'Task failed')
                error = task.info.get('error', str(task.result) if task.result else 'Unknown error')
            else:
                status = 'Task failed'
                error = str(task.result) if task.result else 'Unknown error'
                
            response = TaskStatusResponse(
                task_id=task_id,
                state=task.state,
                status=status,
                error=error
            )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving task status: {str(e)}"
        )

@app.post("/match-objects", response_model=ObjectMatchingResponse)
async def match_objects(request: ObjectMatchingRequest):
    print(f"DEBUG REQUEST: Received match-objects request with description: '{request.description}', type: {type(request.description)}")
    print(f"DEBUG REQUEST: Full match-objects request data: bbox={request.bbox}, project_id={request.project_id}, biosample={request.biosample}, section={request.section}, stain={request.stain}, description={request.description}")
    """
    Run object matching analysis on brain histological sections.
    
    - **bbox**: Bounding box coordinates as [x1, y1, x2, y2]
    - **stain**: Tissue stain type (default: "NISL")
    - **biosample**: Brain specimen identifier
    - **project_id**: Research project identifier  
    - **section**: Target histological section number
    """
    try:
        # Generate hash for the bounding box and unique task ID
        hash_box = str(request.bbox)
        hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
        task_id = generate_task_id(request.bbox, request.project_id, request.biosample, request.section, request.stain)
        
        # Save task to history before processing (if description provided)
        print(f"DEBUG MATCH-OBJECTS: About to check description. Description: '{request.description}', stripped: '{request.description.strip() if request.description else None}'")
        has_description = bool(request.description and request.description.strip())
        if has_description:
            print(f"DEBUG MATCH-OBJECTS: Description check passed, saving task to history")
            save_task_to_history(request, task_id, hash_value, 'processing')
        else:
            print(f"DEBUG MATCH-OBJECTS: Description check failed, NOT saving to history")
        
        # Call the object matching function
        result = run_object_matching(
            bbox=request.bbox,
            stain=request.stain,
            biosample=request.biosample,
            project_id=request.project_id,
            section=request.section
        )
        
        if result["success"]:
            # Update task history to completed status (if description was provided)
            print(f"DEBUG MATCH-OBJECTS COMPLETE: About to update task status. Description: '{request.description}', stripped: '{request.description.strip() if request.description else None}'")
            print(f"DEBUG MATCH-OBJECTS COMPLETE: has_description stored value: {has_description}")
            if has_description:
                print(f"DEBUG MATCH-OBJECTS COMPLETE: Updating task status to completed")
                update_task_history_status(task_id, 'completed', {
                    'processed_sections': result.get('processed_sections', 0)
                })
            else:
                print(f"DEBUG MATCH-OBJECTS COMPLETE: Description check failed, NOT updating task status")
            
            return ObjectMatchingResponse(
                success=True,
                message="Object matching completed successfully",
                output_directory=result["output_directory"],
                hash_value=hash_value,
                processed_sections=result["processed_sections"],
                bbox=request.bbox,
                biosample=request.biosample,
                project_id=request.project_id,
                section=request.section,
                stain=request.stain
            )
        else:
            # Update task history to failed status (if description was provided)
            if request.description and request.description.strip():
                update_task_history_status(task_id, 'failed', {'error': result.get('error', 'Unknown error')})
            
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in match_objects: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)