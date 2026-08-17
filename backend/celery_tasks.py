import sys
import os
from typing import List
import hashlib
# Import task history manager with explicit path from Celery's perspective
import sys
import os
sys.path.append('/apps/src')
from task_history import TaskHistoryManager

# Create task history manager instance with absolute path
task_history_manager = TaskHistoryManager('/apps/volumes/task_history.json')

#celery -A src.celery_config worker --loglevel=debug --concurrency=2 -n worker1@%h to run celery

# Add the src directory and obj_search_utils to Python path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'obj_search_utils'))

from src.celery_config import celery_app
from src.obj_search_utils.obj_matching import run_object_matching
from src.obj_search_utils.section_counter import get_project_biosamples

@celery_app.task(bind=True)
def process_object_matching(self, bbox: List[float], stain: str, biosample: int, 
                          project_id: int, section: int,history_task_id: str = None):#adding this now
    """
    Celery task for processing object matching analysis.
    
    Args:
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        stain: Tissue stain type
        biosample: Brain specimen identifier
        project_id: Research project identifier
        section: Target histological section number
    
    Returns:
        dict: Processing result with success status and details
    """
    
    try:
        print(f"CELERY DEBUG START: Task started with history_task_id = '{history_task_id}'")
        print(f"CELERY DEBUG START: history_task_id type: {type(history_task_id)}")
        print(f"CELERY DEBUG START: history_task_id is None: {history_task_id is None}")
        print(f"CELERY DEBUG START: bool(history_task_id): {bool(history_task_id)}")
        # Generate hash for the bounding box (same as synchronous endpoint)
        hash_box = str(bbox)
        hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
        
        # Define enhanced progress callback that accepts biosample information
        def progress_callback(current_section, total_sections, status_msg, current_biosample=None, total_biosamples=None, current_biosample_id=None):
            print(f"CELERY PROGRESS CALLBACK CALLED: current={current_section}, total={total_sections}, status={status_msg}")
            print(f"CELERY BIOSAMPLE INFO: current_biosample={current_biosample}, total_biosamples={total_biosamples}, current_biosample_id={current_biosample_id}")
            print(f"CELERY CALLBACK: About to call self.update_state with PROGRESS state")
            
            # If biosample info is not passed as parameters, try to extract from status message
            if current_biosample_id is None and "Biosample " in status_msg:
                try:
                    # Extract biosample ID from status message like "Biosample 123: Processing section 5"
                    biosample_part = status_msg.split("Biosample ")[1]
                    if ":" in biosample_part:
                        current_biosample_id = biosample_part.split(":")[0].strip()
                except Exception as e:
                    print(f"DEBUG: Error parsing biosample info from status: {e}")
            
            # For multiple biosamples, show progress per biosample (resets for each biosample)
            # The progress bar will show 0-100% for each biosample individually
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_section': current_section,
                    'total_sections': total_sections,
                    'status': status_msg,
                    'hash_value': hash_value,
                    'current_biosample_id': current_biosample_id,
                    'current_biosample': current_biosample,
                    'total_biosamples': total_biosamples,
                    # Add percentage for frontend display
                    'progress_percent': int((current_section / total_sections * 100)) if total_sections > 0 else 0
                }
            )
            print(f"CELERY PROGRESS: State updated to PROGRESS - {current_section}/{total_sections} sections for biosample {current_biosample_id}")
        
        # Initial progress update (we'll get the real total_sections from run_object_matching)
        progress_callback(0, 1, f'Starting object matching for biosample {biosample}, section {section}')
        
        # Call the object matching function with progress callback
        print(f"CELERY DEBUG: About to call run_object_matching with params: bbox={bbox}, stain={stain}, biosample={biosample}, project_id={project_id}, section={section}")
        print(f"CELERY DEBUG: progress_callback being passed: {progress_callback}")
        print(f"CELERY DEBUG: progress_callback type: {type(progress_callback)}")
        result = run_object_matching(
            bbox=bbox,
            stain=stain,
            biosample=biosample,
            project_id=project_id,
            section=section,
            progress_callback=progress_callback
        )
        print(f"CELERY DEBUG: run_object_matching returned: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        print(f"CELERY DEBUG: result['success'] = {result.get('success', 'KEY_NOT_FOUND')}")
        
        if result["success"]:
            print(f"CELERY DEBUG: Task SUCCESS - processed_sections: {result.get('processed_sections', 'N/A')}")
            print(f"CELERY DEBUG: Task SUCCESS - total_combinations: {result.get('total_combinations', 'N/A')}")
            print(f"CELERY DEBUG: Preparing return object...")
            # Use processed_sections for consistency
            total_processed = result.get("processed_sections", result.get("total_combinations", 1))

            
            # Update task history if it exists (tasks with descriptions)
            if history_task_id:
                print(f"CELERY DEBUG: history_task_id provided: {history_task_id}")
                
                # Add retry logic for file-based storage timing issues
                import time
                import os
                print(f"CELERY DEBUG: Current working directory: {os.getcwd()}")
                print(f"CELERY DEBUG: Task history storage path: {task_history_manager.storage_path}")
                print(f"CELERY DEBUG: Task history file exists: {os.path.exists(task_history_manager.storage_path)}")
                existing_task = None
                for attempt in range(3):  # Try up to 3 times
                    existing_task = task_history_manager.get_task(history_task_id)
                    if existing_task:
                        break
                    print(f"CELERY DEBUG: Attempt {attempt + 1}/3 - Task not found, waiting 0.5 seconds...")
                    time.sleep(0.5)
                
                print(f"CELERY DEBUG: Found existing task: {existing_task is not None}")
                if existing_task:
                    print(f"CELERY DEBUG: Task has description: {existing_task.get('description') is not None}")
                    print(f"CELERY DEBUG: Description value: '{existing_task.get('description')}'")
                
                if existing_task and existing_task.get('description'):
                    task_history_manager.update_task_status(
                        history_task_id,
                        'completed',
                        {
                            'processed_sections': total_processed
                        }
                    )
                    print(f"CELERY DEBUG: Updated task history {history_task_id} to completed")
                else:
                    print(f"CELERY DEBUG: Task {history_task_id} not found in history or has no description after 3 attempts - skipping update")
            else:
                print(f"CELERY DEBUG: No history_task_id provided - skipping history update")







            return_obj = {
                'current_section': total_processed,
                'total_sections': total_processed,
                'status': 'Object matching completed successfully',
                'result': {
                    'success': True,
                    'message': "Object matching completed successfully",
                    'output_directory': result["output_directory"],
                    'hash_value': hash_value,
                    'processed_sections': total_processed,
                    'total_combinations': result.get("total_combinations", 1),
                    'bbox': bbox,
                    'biosample': biosample,
                    'project_id': project_id,
                    'section': section,
                    'stain': stain
                }
            }
            print(f"CELERY DEBUG: Returning success object, size: {len(str(return_obj))} chars")
            return return_obj
        else:
            print(f"CELERY DEBUG: Task FAILED - result: {result}")
            print(f"CELERY DEBUG: Error from result: {result.get('error', 'NO_ERROR_KEY')}")
            # Task failed
            error_msg = result.get("error", "Unknown error")
            print(f"CELERY DEBUG: About to update_state to FAILURE with error: {error_msg}")
            self.update_state(
                state='FAILURE',
                meta={
                    'status': 'Object matching failed',
                    'error': error_msg
                }
            )
            print(f"CELERY DEBUG: About to raise Exception with: {error_msg}")
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"CELERY DEBUG: Exception caught: {type(e).__name__}: {str(e)}")
        print(f"CELERY DEBUG: Exception args: {e.args}")
        # Update task state to FAILURE
        error_str = str(e)
        print(f"CELERY DEBUG: About to update_state to FAILURE with exception: {error_str}")
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Object matching failed with exception',
                'error': error_str
            }
        )
        print(f"CELERY DEBUG: About to re-raise exception: {error_str}")
        raise

@celery_app.task(bind=True)
def process_bulk_object_matching(self, bbox: List[float], stain: str, 
                               project_id: int, section: int):
    """
    Celery task for processing object matching across all biosamples in a project.
    
    Args:
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        stain: Tissue stain type
        project_id: Research project identifier
        section: Target histological section number
    
    Returns:
        dict: Processing result with success status and details
    """
    
    try:
        # Get all biosamples for the project
        biosamples = get_project_biosamples(project_id)
        total_biosamples = len(biosamples)
        
        if total_biosamples == 0:
            raise Exception(f"No biosamples found for project {project_id}")
        
        # Update task state to PROGRESS
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': total_biosamples,
                'status': f'Starting bulk object matching for project {project_id} with {total_biosamples} biosamples'
            }
        )
        
        # Generate hash for the bounding box
        hash_box = str(bbox)
        hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
        
        processed_results = []
        total_processed_sections = 0
        
        # Process each biosample
        for i, biosample in enumerate(biosamples):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total': total_biosamples,
                    'status': f'Processing biosample {biosample} ({i+1}/{total_biosamples})',
                    'hash_value': hash_value
                }
            )
            
            try:
                # Call the object matching function for this biosample
                result = run_object_matching(
                    bbox=bbox,
                    stain=stain,
                    biosample=biosample,
                    project_id=project_id,
                    section=section
                )
                
                if result["success"]:
                    processed_results.append({
                        'biosample': biosample,
                        'success': True,
                        'processed_sections': result["processed_sections"],
                        'output_directory': result["output_directory"]
                    })
                    total_processed_sections += result["processed_sections"]
                else:
                    processed_results.append({
                        'biosample': biosample,
                        'success': False,
                        'error': result["error"]
                    })
                    
            except Exception as e:
                processed_results.append({
                    'biosample': biosample,
                    'success': False,
                    'error': str(e)
                })
        
        # Calculate success rate
        successful_biosamples = sum(1 for r in processed_results if r['success'])
        
        # Return final result
        return {
            'current': total_biosamples,
            'total': total_biosamples,
            'status': 'Bulk object matching completed',
            'result': {
                'success': True,
                'message': f"Bulk object matching completed for project {project_id}",
                'hash_value': hash_value,
                'total_biosamples': total_biosamples,
                'successful_biosamples': successful_biosamples,
                'total_processed_sections': total_processed_sections,
                'bbox': bbox,
                'project_id': project_id,
                'section': section,
                'stain': stain,
                'biosample_results': processed_results
            }
        }
            
    except Exception as e:
        # Update task state to FAILURE
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Bulk object matching failed with exception',
                'error': str(e)
            }
        )
        raise