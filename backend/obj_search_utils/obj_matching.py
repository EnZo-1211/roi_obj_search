import numpy as np
import imageio as imio
import os
import torch
from tqdm import tqdm
import cv2
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from pathlib import Path
from obj_search_utils.get_sec_byproject import OpenAtlasDB
from sqlalchemy import create_engine, text
from obj_search_utils.input_bounding import input_bound
import hashlib
from obj_search_utils.get_metadata import get_metadata_for_all



def get_thumbnail_path(biosample, section, stain):
    sec_path =  f"/apps/analytics/{biosample}/{stain}/"
    for p in Path(sec_path).rglob("*thumbnail_original.jpg"):
        # print(p.parts)
       f_name = p.parts[-1]
       sec = f_name.split("SE_")[1].split("_")[0]
       #print(sec)
       if sec == str(section):
           return "/".join(p.parts)[1:]


def map_stain_name(db_stain_name):
    """
    Maps database stain names to selection metadata stain names
    """
    stain_mapping = {
        'NISL': 'NISSL',
        'NISSL': 'NISSL', 
        'MYEL': 'MYELIN',
        'HEOS': 'Haematoxylin and Eosin',
        'Haematoxylin and Eosin': 'Haematoxylin and Eosin',
        'IHCS': 'Immuno Histo Chemistry',
        'Immuno Histo Chemistry': 'Immuno Histo Chemistry'
    }
    return stain_mapping.get(db_stain_name, db_stain_name)

def get_sections(project_id,stain):
    db = OpenAtlasDB()
    project_data = db.get_project_data_json(project_id)
    
    # Debug: Print the actual structure to understand what's available
    print("DEBUG - Project data structure:")
    print(f"Keys: {project_data.keys()}")
    if 'brains' in project_data and len(project_data['brains']) > 0:
        print(f"First brain keys: {project_data['brains'][0].keys()}")
        selection_meta = project_data['brains'][0]["selection_metadata"]
        print(f"Selection metadata structure: {selection_meta}")
        
        # Try different possible paths for sections
        try:
            if isinstance(selection_meta, dict):
                if "series" in selection_meta:
                    #added here 
                    mapped_stain=map_stain_name(stain)
                    stain_data = selection_meta["series"][mapped_stain]
                    
                    # CLAUDE CHANGE: Handle all_sections=True case by getting sections from filesystem
                    # Check if all_sections is True
                    if stain_data.get("all_sections", False):
                        print(f"DEBUG: all_sections=True for stain {mapped_stain}, getting sections from filesystem")
                        # Get the biosample from the first brain (assuming single biosample per call)
                        biosample = project_data['brains'][0]['biosample']
                        sections = get_sections_from_path(biosample, stain)
                        print(f"DEBUG: Found {len(sections)} sections from filesystem: {sections}")
                    else:
                        sections = stain_data["sections"]
                    # END CLAUDE CHANGE
                elif "sections" in selection_meta:
                    sections = selection_meta["sections"]
                elif "NISSL" in selection_meta:
                    sections = selection_meta[stain]["sections"]
                else:
                    # Fallback: return empty list and log the structure
                    print(f"ERROR: Could not find sections in structure: {selection_meta}")
                    return []
            else:
                print(f"ERROR: selection_metadata is not a dict: {type(selection_meta)}")
                return []
        except KeyError as e:
            print(f"ERROR: Missing key in selection_metadata: {e}")
            print(f"Available keys: {list(selection_meta.keys()) if isinstance(selection_meta, dict) else 'Not a dict'}")
            return []
    else:
        print("ERROR: No brains data found")
        return []
        
    return sections


def get_thumbnail_org_paths(biosample, sections, stain="NISL"):
    """
    Returns thumbnail paths only for the section numbers specified in the 'sections' list.
    """
    base_path = f"/apps/analytics/{biosample}/{stain}"
    thumbnail_paths_dict = {}

    # Convert sections to a set for O(1) lookup speed (faster than list lookup)
    target_sections = set(sections)

    for p in Path(base_path).rglob("*thumbnail_original.jpg"):
        try:
            # Extract section number from filename
            sec_num = int(p.parts[-1].split("SE_")[-1].split("_")[0])
            
            # Only add to dictionary if it matches your requested list
            if sec_num in target_sections:
                path = "/".join(p.parts)
                thumbnail_paths_dict[sec_num] = path[1:]
        except (ValueError, IndexError):
            # Skips files that don't follow the naming convention
            continue

    # Sort the dictionary by section number
    sorted_paths_dict = {sec: path for sec, path in sorted(thumbnail_paths_dict.items())}
    #print('The dictionary is',sorted_paths_dict)
    return sorted_paths_dict
 

def local_consensus_confidence(points, radius=30):

    tree = cKDTree(points)
    counts = np.array([
        len(tree.query_ball_point(p, radius))
        for p in points
    ])

    # normalize to [0, 1]
    conf = counts / counts.max()
    return conf   


#THRES=0.55,INLI=6
def wrap_corners_and_draw_matches(ref_points, dst_points, img1, img2, conf_threshold=0.55):
    
    M_affine, affine_inliers_mask = cv2.estimateAffine2D(
        ref_points, dst_points, method=cv2.RANSAC, 
        ransacReprojThreshold=3.0, maxIters=1000, confidence=0.999
    )

    if M_affine is None or affine_inliers_mask is None:
        return None, None


    mask = affine_inliers_mask.flatten()
    inlier_indices = np.where(mask > 0)[0]
    inlier_src = ref_points[inlier_indices]
    inlier_dst = dst_points[inlier_indices]
    
    scores = local_consensus_confidence(inlier_dst)

    passed_idx = np.where(scores >= conf_threshold)[0]
    
    # Check if number of high-confidence inlier points is less than 5
    if len(passed_idx) < 6:
        return None, None

    final_src = inlier_src[passed_idx]
    final_dst = inlier_dst[passed_idx]
    final_scores = scores[passed_idx]

    # Update final_mask to only reflect the survivors
    final_mask = np.zeros(len(ref_points), dtype=np.uint8)
    final_mask[inlier_indices[passed_idx]] = 1


    M_clean, _ = cv2.estimateAffine2D(final_src, final_dst)
    img2_with_box = img2.copy()

    if M_clean is not None:
        M_clean = np.nan_to_num(M_clean) # Safety against NaN
        h1, w1 = img1.shape[:2]
        corners_img1 = np.array([[0, 0], [w1-1, 0], [w1-1, h1-1], [0, h1-1]], dtype=np.float32).reshape(-1, 1, 2)
        warped_corners = cv2.transform(corners_img1, M_clean)
        

        cv2.polylines(img2_with_box, [np.nan_to_num(warped_corners).astype(np.int32)], True, (0, 255, 0), 4)

    # 5. Create Final Canvas and Draw Filtered Matches
    h1, w1 = img1.shape[:2]
    h2, w2 = img2_with_box.shape[:2]
    img_matches = np.zeros((max(h1, h2), w1 + w2, 3), dtype=np.uint8)
    img_matches[:h1, :w1] = img1
    img_matches[:h2, w1:] = img2_with_box

    for p1, p2, c in zip(final_src, final_dst, final_scores):
        color = (0, int(255 * c), int(255 * (1 - c)))
        thickness = int(1 + 3 * c)
        
        # Explicit integer conversion to avoid OpenCV 'Bad argument' errors
        pt1 = (int(round(float(p1[0]))), int(round(float(p1[1]))))
        pt2 = (int(round(float(p2[0] + w1))), int(round(float(p2[1]))))
        
        cv2.line(img_matches, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)

    return img_matches, final_mask


def run_object_matching_old(bbox, stain, biosample, project_id, section, progress_callback=None, target_biosample=None, target_stain=None, reference_image=None, xfeat_model=None):
    """
    Main function to run object matching with the provided parameters.
    
    Args:
        bbox: List of bounding box coordinates [x1, y1, x2, y2]
        stain: Tissue stain type (e.g., 'NISL')
        biosample: Brain specimen identifier
        project_id: Research project identifier
        section: Target histological section number
        progress_callback: Optional callback function to report progress
        
    Returns:
        dict: Result with success status, output directory, and processed sections count
    """
    try:
        # print(f"DEBUG: Starting run_object_matching")
        # print(f"DEBUG: Current working directory: {os.getcwd()}")
        # print(f"DEBUG: Parameters - bbox: {bbox}, project_id: {project_id}, biosample: {biosample}, section: {section}, stain: {stain}")
        
        # Initialize XFeat model - use provided model if available
        if xfeat_model is not None:
            xfeat = xfeat_model
            print(f"🔵 USING PROVIDED XFEAT MODEL (no reload)")
        else:
            # print(f"DEBUG: Loading XFeat model...")
            xfeat = torch.hub.load('verlab/accelerated_features', 'XFeat', pretrained=True, top_k=4096).cuda()
            # print(f"DEBUG: XFeat model loaded successfully")
        
        # Generate hash for the bounding box
        hash_box = str(bbox)
        hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
        
        # Get sections from project - use target parameters for searching if provided
        search_stain = target_stain if target_stain is not None else stain
        search_biosample = target_biosample if target_biosample is not None else biosample
        
        sections = get_sections(project_id, search_stain)#added here
        sec_path_dict = get_thumbnail_org_paths(search_biosample, sections, search_stain)#added here
        #print('HEllo ',sec_path_dict.items())

        #added here - use target parameters for search metadata
        sec_metadata = get_metadata_for_all(search_biosample, search_stain)
        
        # ALWAYS use the provided FIXED reference image - NO fallback creation
        if reference_image is None:
            return {
                "success": False,
                "error": "No reference image provided - this should not happen in multi-biosample mode"
            }
        
        # Use the pre-created FIXED reference image (same pixels for ALL biosamples)
        im1 = reference_image.copy()  # Make a copy to avoid any modifications
        print(f"🔵 USING EXACT REFERENCE PIXELS: hash={hashlib.md5(im1.tobytes()).hexdigest()[:8]}, target={search_biosample}/{search_stain}")
        
        
        

        # Create output directory
        # Use a path that's accessible in the container
        # base_results_dir = os.environ.get('RESULTS_DIR', '/home/projects/discovery/roi_object_search/volumes/results')
        base_results_dir = os.environ.get('RESULTS_DIR', '/apps/volumes/results')

        output_dir = f"{base_results_dir}/{project_id}/{hash_value}/{search_biosample}/{search_stain}"
        # print(f"DEBUG: Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        # print(f"DEBUG: Output directory created successfully")
        
        processed_sections = 0
        total_sections = len(sec_path_dict)
        # print(f"DEBUG: Starting to process {total_sections} sections")

        # Report initial progress
        if progress_callback:
            progress_callback(0, total_sections, f"Starting to process {total_sections} sections")

        # Process each section
        for sec_id, img_path in tqdm(sec_path_dict.items()):
            # print(f"DEBUG: Processing section {sec_id} from path: {img_path}")
            
            # Report progress at start of each section
            if progress_callback:
                progress_callback(processed_sections, total_sections, f"Processing section {sec_id} ({processed_sections}/{total_sections})")
            
            try:
                im2_orig = np.copy(imio.v2.imread(img_path)[..., ::-1])
                im2 = im2_orig.copy()
                # print(f"DEBUG: Loaded image for section {sec_id}, shape: {im2.shape}")
                
                rot_deg = sec_metadata[sec_id]['rotation']
                if rot_deg is not None:
                    if rot_deg != 0:
                        k = -int(rot_deg / 90)
                        im2 = np.rot90(im2, k).copy()
                        # print(f"DEBUG: Rotated image for section {sec_id} by {rot_deg} degrees")
                
                # Match with reference image
                # print(f"DEBUG: Running XFeat matching for section {sec_id}")
                mkpts_0, mkpts_1 = xfeat.match_xfeat(im1, im2, top_k=4096)
                # print(f"DEBUG: XFeat found {len(mkpts_0)} matches for section {sec_id}")
                
                #added here
                if len(mkpts_0) == 0:
                    print(f"DEBUG: No XFeat matches found for section {sec_id}")
                    processed_sections += 1
                    if progress_callback:
                        progress_callback(processed_sections, total_sections, f"No matches found for section {sec_id} ({processed_sections}/{total_sections})")
                    continue
                
                canvas, mask = wrap_corners_and_draw_matches(mkpts_0, mkpts_1, im1, im2)
                
                # Skip this section if insufficient inlier points (less than 5)
                if canvas is None:
                    print(f"DEBUG: Skipping section {sec_id} - insufficient inlier points")
                    # Still count this as processed for progress tracking
                    processed_sections += 1
                    if progress_callback:
                        progress_callback(processed_sections, total_sections, f"Skipped section {sec_id} ({processed_sections}/{total_sections})")
                    continue
                
                print(f"DEBUG: Creating matplotlib figure for section {sec_id}")
                # Plot and Save
                plt.figure(figsize=(10, 5))
                
                # Check if canvas is a list/tuple
                img_to_show = canvas[0] if isinstance(canvas, (list, tuple)) else canvas
                
                plt.imshow(img_to_show[..., ::-1])  
                plt.title(f"Section ID: {sec_id}")
                plt.axis("off")
                
                # Save with section ID as filename
                save_path = os.path.join(output_dir, f"{sec_id}.png")
                print(f"DEBUG: Saving image to: {save_path}")
                plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
                
                # Force filesystem sync
                import time
                time.sleep(0.1)  # Small delay
                os.sync() if hasattr(os, 'sync') else None
                
                # Check if file was actually created
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    print(f"DEBUG: Successfully saved {save_path}, size: {file_size} bytes")
                else:
                    print(f"DEBUG: ERROR - File was not created: {save_path}")
                
                plt.close()
                processed_sections += 1
                print(f"DEBUG: Completed section {sec_id}. Total processed: {processed_sections}")
                
                # Report progress after each section
                if progress_callback:
                    progress_callback(processed_sections, total_sections, f"Processed section {sec_id} ({processed_sections}/{total_sections})")
                
            except Exception as e:
                print(f"DEBUG: ERROR processing section {sec_id}: {str(e)}")
                import traceback
                print(f"DEBUG: Traceback: {traceback.format_exc()}")
                # Still count this as processed for progress tracking
                processed_sections += 1
                if progress_callback:
                    progress_callback(processed_sections, total_sections, f"Error processing section {sec_id} ({processed_sections}/{total_sections})")
                continue
        
        print(f"DEBUG: Finished processing. Total sections processed: {processed_sections}")
        print(f"DEBUG: Output directory: {output_dir}")
        print(f"DEBUG: Hash value: {hash_value}")
        
        # Final check - list files in output directory
        if os.path.exists(output_dir):
            files = os.listdir(output_dir)
            print(f"DEBUG: Files created in output directory: {files}")
        else:
            print(f"DEBUG: ERROR - Output directory does not exist: {output_dir}")
        
        return {
            "success": True,
            "output_directory": output_dir,
            "processed_sections": processed_sections,
            "hash_value": hash_value
        }
        
    except Exception as e:
        print(f"DEBUG: MAJOR ERROR in run_object_matching: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }






# ======= MULTI-BIOSAMPLE SUPPORT (TEST FEATURE) =======

def get_all_biosamples_and_stains(project_id):
    """
    Get all biosamples and their available stains for a project
    Returns: {biosample_id: [list_of_stains], ...}
    """
    db = OpenAtlasDB()
    project_data = db.get_project_data_json(project_id)
    
    biosample_stains = {}
    
    if 'brains' in project_data:
        for brain in project_data['brains']:
            biosample = brain['biosample']
            available_stains = []
            
            if 'selection_metadata' in brain and 'series' in brain['selection_metadata']:
                # Get all available stains for this biosample
                for stain_name in brain['selection_metadata']['series'].keys():
                    stain_data = brain['selection_metadata']['series'][stain_name]
                    sections = stain_data['sections']
                    # CLAUDE CHANGE: Include stains that have sections OR all_sections=True
                    if len(sections) > 0 or stain_data.get('all_sections', False):
                        available_stains.append(stain_name)
                    # END CLAUDE CHANGE
            
            biosample_stains[biosample] = available_stains
    
    print(f"DEBUG: Found biosamples and stains: {biosample_stains}")
    return biosample_stains

def get_sections_from_path(biosample, stain):
    
    """Return all section numbers for a given biosample and stain."""
    # CLAUDE CHANGE: Fix path and section extraction to match get_thumbnail_org_paths logic
    b_path = f"/apps/analytics/{biosample}/{stain}/"
    sections = []
    
    try:
        for p in Path(b_path).rglob("*thumbnail_original.jpg"):
            try:
                # Extract section number from filename using same logic as get_thumbnail_org_paths
                sec_num = int(p.parts[-1].split("SE_")[-1].split("_")[0])
                sections.append(sec_num)
            except (ValueError, IndexError):
                # Skip files that don't follow the naming convention
                continue
        
        # Return sorted list of unique section numbers
        return sorted(list(set(sections)))
        
    except Exception as e:
        print(f"ERROR: Could not read sections from path {b_path}: {e}")
        return []
    # END CLAUDE CHANGE

def get_sections_for_biosample(project_id, stain, biosample):
    """
    Get sections for a specific biosample and stain
    """
    db = OpenAtlasDB()
    project_data = db.get_project_data_json(project_id)
    
    if 'brains' in project_data:
        for brain in project_data['brains']:
            if brain['biosample'] == biosample:
                selection_meta = brain["selection_metadata"]
                
                try:
                    if isinstance(selection_meta, dict) and "series" in selection_meta:
                        mapped_stain = map_stain_name(stain)
                        stain_data = selection_meta["series"][mapped_stain]
                        
                        # CLAUDE CHANGE: Handle all_sections=True case by getting sections from filesystem
                        # Check if all_sections is True
                        if stain_data.get("all_sections", False):
                            print(f"DEBUG: all_sections=True for biosample {biosample}, stain {stain}, getting sections from filesystem")
                            sections = get_sections_from_path(biosample, stain)
                            print(f"DEBUG: Found {len(sections)} sections from filesystem for biosample {biosample}, stain {stain}")
                        else:
                            sections = stain_data["sections"]
                            print(f"DEBUG: Found {len(sections)} sections for biosample {biosample}, stain {stain}")
                        # END CLAUDE CHANGE
                        
                        return sections
                except KeyError as e:
                    print(f"ERROR: Missing key for biosample {biosample}, stain {stain}: {e}")
                    return []
    
    print(f"ERROR: No data found for biosample {biosample}")
    return []

def get_reverse_stain_mapping():
    """
    Create reverse mapping from metadata stain names to database stain names
    """
    # Direct mapping from metadata stain names to database stain names
    reverse_mapping = {
        'NISSL': 'NISL',
        'MYELIN': 'MYEL', 
        'Haematoxylin and Eosin': 'HEOS',
        'Immuno Histo Chemistry': 'IHCS'
    }
    
    return reverse_mapping

def run_object_matching(bbox, stain, biosample, project_id, section, progress_callback=None):
    """
    Multi-biosample + Multi-stain ROI object matching - processes each biosample-stain combination individually
    Uses the exact same logic as run_object_matching_old for each biosample-stain combination
    
    Args:
        bbox: List of bounding box coordinates [x1, y1, x2, y2]
        stain: Database stain name (e.g., 'NISL', 'HEOS') - used as reference but each biosample uses its own reference
        biosample: Reference biosample ID (original biosample where bbox was drawn)
        project_id: Research project identifier
        section: Target histological section number (original section where bbox was drawn)
        progress_callback: Optional callback function to report progress
        
    Returns:
        dict: Result with success status and processed combinations for all biosamples and stains
    """
    try:
        # print(f"DEBUG: Starting multi-biosample ROI matching using run_object_matching_old logic")
        # print(f"DEBUG: Will call run_object_matching_old for each biosample-stain combination individually")
        # print(f"DEBUG: INPUT BOUNDING BOX - Section: {section}, Biosample: {biosample}")
        # print(f"DEBUG: progress_callback parameter received: {progress_callback}")
        # print(f"DEBUG: progress_callback type: {type(progress_callback)}")
        
        # Store the original progress callback for use in wrapper
        original_progress_callback = progress_callback
        
        # Get all available biosamples and their stains
        all_combinations = get_all_biosamples_and_stains(project_id)
        
        if not all_combinations:
            return {
                "success": False,
                "error": f"No biosamples found in project {project_id}"
            }
        
        # Generate hash for the bounding box
        hash_box = str(bbox)
        hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
        
        # CREATE FIXED REFERENCE IMAGE ONCE (before processing all combinations)
        print(f"🔵 CREATING FIXED REFERENCE IMAGE")
        
        # Get original metadata for reference image rotation
        ref_metadata = get_metadata_for_all(biosample, stain)
        if section not in ref_metadata:
            return {
                "success": False,
                "error": f"Reference section {section} not found in biosample {biosample}, stain {stain}"
            }
        
        ref_rotation = ref_metadata[section]['rotation']
        
        # Create the FIXED reference image that will be reused for all combinations
        cropped_image = input_bound(bbox, biosample, stain, section)
        ref_array = np.array(cropped_image)
        if ref_rotation is not None:
            fixed_reference_image = np.rot90(np.copy(ref_array[..., ::-1]), -int(ref_rotation / 90)).copy()
        else:
            fixed_reference_image = ref_array
            
        fixed_ref_hash = hashlib.md5(fixed_reference_image.tobytes()).hexdigest()[:8]
        print(f"🔵 FIXED REFERENCE CREATED: hash={fixed_ref_hash}, from={biosample}/{stain}/{section}")
        print(f"🔵 This EXACT pixel data will be used for ALL biosample combinations")
        
        # Initialize XFeat model ONCE for all combinations
        print(f"🔵 LOADING XFEAT MODEL ONCE")
        xfeat = torch.hub.load('verlab/accelerated_features', 'XFeat', pretrained=True, top_k=4096).cuda()
        
        # Create base output directory
        base_results_dir = os.environ.get('RESULTS_DIR', '/apps/volumes/results')
        base_output_dir = f"{base_results_dir}/{project_id}/{hash_value}"
        
        processed_results = []
        
        # CLAUDE CHANGE: Calculate biosamples for per-biosample progress tracking
        processed_count = 0  # Track biosample-stain combinations processed
        reverse_mapping = get_reverse_stain_mapping()
        
        # Calculate total combinations for progress reporting
        total_combinations = sum(len(stains) for stains in all_combinations.values())
        
        print(f"DEBUG: Will process {total_combinations} biosample-stain combinations")
        
        # Calculate total biosamples for progress tracking
        total_biosamples = len(all_combinations)
        current_biosample_index = 0
        
        # Process each biosample and all its available stains individually
        for target_biosample, available_meta_stains in all_combinations.items():
            current_biosample_index += 1
            print(f"DEBUG: Starting biosample {target_biosample} ({current_biosample_index}/{total_biosamples}) - resetting progress for this biosample")
            
            # Calculate total sections for current biosample only
            current_biosample_total_sections = 0
            
            # First pass: count sections for this biosample
            for meta_stain in available_meta_stains:
                try:
                    target_stain = reverse_mapping.get(meta_stain, meta_stain)
                    available_sections = get_sections_for_biosample(project_id, target_stain, target_biosample)
                    current_biosample_total_sections += len(available_sections) if available_sections else 0
                except Exception as e:
                    print(f"DEBUG: Error counting sections for biosample {target_biosample}: {e}")
                    continue
            
            print(f"DEBUG: Biosample {target_biosample} has {current_biosample_total_sections} total sections")
            
            # Reset progress for this biosample - starts at 0 for each biosample
            current_biosample_processed_sections = 0
            
            # Create wrapper progress callback that tracks progress within current biosample only
            # Use closure to capture current values and the original progress_callback
            def create_biosample_progress_callback(biosample_id, biosample_idx, total_biosample_count, biosample_total_sections, original_progress_callback):
                def biosample_progress_callback(current_in_stain, total_in_stain, status_msg):
                    print(f"DEBUG WRAPPER: Called with current={current_in_stain}, total={total_in_stain}, status={status_msg}")
                    # Report progress for current biosample only (starts from 0 for each biosample)
                    if original_progress_callback:
                        print(f"DEBUG WRAPPER: Calling progress_callback with current={current_in_stain}, total={biosample_total_sections}")
                        print(f"DEBUG WRAPPER: Biosample info: index={biosample_idx}, total_biosamples={total_biosample_count}, id={biosample_id}")
                        try:
                            # Try enhanced callback with biosample info first
                            original_progress_callback(current_in_stain, biosample_total_sections, 
                                            f"Biosample {biosample_id}: {status_msg}",
                                            biosample_idx, total_biosample_count, str(biosample_id))
                            print(f"DEBUG WRAPPER: Enhanced callback succeeded")
                        except Exception as e:
                            print(f"DEBUG WRAPPER: Enhanced callback failed with {type(e).__name__}: {e}")
                            # Fallback to standard callback
                            try:
                                original_progress_callback(current_in_stain, biosample_total_sections, 
                                                f"Biosample {biosample_id}: {status_msg}")
                                print(f"DEBUG WRAPPER: Fallback callback succeeded")
                            except Exception as e2:
                                print(f"DEBUG WRAPPER: Fallback callback also failed with {type(e2).__name__}: {e2}")
                    else:
                        print(f"DEBUG WRAPPER: No progress_callback provided!")
                return biosample_progress_callback
            
            # Create the callback for this specific biosample
            biosample_progress_callback = create_biosample_progress_callback(
                target_biosample, current_biosample_index, total_biosamples, current_biosample_total_sections, original_progress_callback
            )
            print(f"DEBUG: Processing biosample {target_biosample} with {len(available_meta_stains)} stains: {available_meta_stains}")
            
            # Process each stain for this biosample using run_object_matching_old logic
            for meta_stain in available_meta_stains:
                target_stain = reverse_mapping.get(meta_stain, meta_stain)
                print(f"DEBUG: Calling run_object_matching_old for biosample {target_biosample}, stain {target_stain} - combination {processed_count + 1}/{total_combinations}")
                
                try:
                    # Get sections available for this biosample and stain
                    available_sections = get_sections_for_biosample(project_id, target_stain, target_biosample)
                    if not available_sections:
                        print(f"DEBUG: No sections available for biosample {target_biosample}, stain {target_stain}, skipping")
                        processed_count += 1
                        continue
                    
                    # Get metadata to find valid reference sections
                    target_metadata = get_metadata_for_all(target_biosample, target_stain)
                    if not target_metadata:
                        print(f"DEBUG: No metadata available for biosample {target_biosample}, stain {target_stain}, skipping")
                        processed_count += 1
                        continue
                    
                    available_metadata_sections = list(target_metadata.keys())
                    print(f"DEBUG: Sections with metadata for biosample {target_biosample}, stain {target_stain}: {available_metadata_sections}")
                    
                    # Prioritize the original input section if available, otherwise use first available section
                    reference_section = None
                    # First try to use the original input section
                    if section in available_sections and section in available_metadata_sections:
                        reference_section = section
                        print(f"DEBUG: Using original input section {section} as reference for biosample {target_biosample}, stain {target_stain}")
                    else:
                        # Fallback to first available section
                        for section_num in available_sections:
                            if section_num in available_metadata_sections:
                                reference_section = section_num
                                print(f"DEBUG: Original section {section} not available, using section {reference_section} as reference for biosample {target_biosample}, stain {target_stain}")
                                break
                    
                    if reference_section is None:
                        print(f"DEBUG: No valid reference section found for biosample {target_biosample}, stain {target_stain}")
                        processed_count += 1
                        continue
                    
                    print(f"🟢 PROCESSING {target_biosample}/{target_stain} - will use FIXED reference pixels")
                    
                    # Call run_object_matching_old for this specific biosample-stain combination
                    # CLAUDE FIX: Pass the FIXED reference image pixels (not coordinates), target search parameters, and XFeat model
                    result = run_object_matching_old(
                        bbox=bbox,
                        stain=stain,  # Use ORIGINAL stain for backward compatibility
                        biosample=biosample,  # Use ORIGINAL biosample for backward compatibility
                        project_id=project_id,
                        section=section,  # Use ORIGINAL section for backward compatibility
                        progress_callback=biosample_progress_callback,  # Use per-biosample progress tracking
                        target_biosample=target_biosample,  # Target biosample to search in
                        target_stain=target_stain,  # Target stain to search in
                        reference_image=fixed_reference_image,  # Pass the FIXED reference image
                        xfeat_model=xfeat  # Pass the SHARED XFeat model instance
                    )
                    # END CLAUDE FIX
                    
                    if result.get("success", False):
                        processed_results.append({
                            "biosample": target_biosample,
                            "stain": target_stain,
                            "reference_section": reference_section,
                            "sections_processed": result.get("processed_sections", 0),
                            "total_sections": len(available_sections),
                            "output_path": result.get("output_directory"),
                            "hash_value": result.get("hash_value", hash_value)
                        })
                        print(f"DEBUG: Successfully processed biosample {target_biosample}, stain {target_stain} using run_object_matching_old")
                    else:
                        print(f"DEBUG: Failed to process biosample {target_biosample}, stain {target_stain}: {result.get('error', 'Unknown error')}")
                    
                    processed_count += 1
                    
                except Exception as stain_error:
                    print(f"DEBUG: Error processing biosample {target_biosample}, stain {target_stain}: {stain_error}")
                    import traceback
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    processed_count += 1
                    continue
            
            # Report completion of this biosample - set to 100% complete for this biosample
            print(f"DEBUG: Completed biosample {target_biosample} - processed {current_biosample_total_sections}/{current_biosample_total_sections} sections")
            if original_progress_callback:
                try:
                    # Try enhanced callback with biosample info first
                    original_progress_callback(current_biosample_total_sections, current_biosample_total_sections, 
                                    f"Completed biosample {target_biosample}",
                                    current_biosample_index, total_biosamples, str(target_biosample))
                except Exception as e:
                    print(f"DEBUG: Completion callback failed: {e}")
                    # Fallback to standard callback
                    try:
                        original_progress_callback(current_biosample_total_sections, current_biosample_total_sections, 
                                        f"Completed biosample {target_biosample}")
                    except Exception as e2:
                        print(f"DEBUG: Completion callback fallback also failed: {e2}")
        
        print(f"DEBUG: Completed processing {len(processed_results)} biosample-stain combinations using run_object_matching_old logic")
        
        # Calculate total processed sections across all combinations for compatibility with celery_tasks.py
        total_processed_sections = sum(result["sections_processed"] for result in processed_results)
        
        return {
            "success": True,
            "output_directory": base_output_dir,
            "processed_sections": total_processed_sections,  # Use processed_sections for consistency with celery_tasks.py
            "processed_combinations": processed_results,
            "total_combinations": len(processed_results),
            "hash_value": hash_value
        }
        
    except Exception as e:
        print(f"DEBUG: MAJOR ERROR in multi-biosample ROI matching: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }


def run_object_matching_multistain(bbox, biosample, project_id, section, stain, progress_callback=None):
    """
    Multi-stain ROI object matching for single biosample
    Takes input stain for reference image, then searches across ALL stains available for the biosample
    
    Args:
        bbox: List of bounding box coordinates [x1, y1, x2, y2]
        biosample: Single biosample ID to process
        project_id: Research project identifier
        section: Target histological section number (for reference image)
        stain: Database stain name for the input bounding box reference image
        progress_callback: Optional callback function to report progress
        
    Returns:
        dict: Result with success status and processed stain combinations
    """
    try:
        print(f"DEBUG: Starting multi-stain object matching for biosample {biosample}")
        print(f"DEBUG: Parameters - bbox: {bbox}, project_id: {project_id}, section: {section}")
        print(f"DEBUG: Input stain for reference image: {stain}")
        
        # Get project data to find stains and sections available for this specific biosample
        from obj_search_utils.get_sec_byproject import OpenAtlasDB
        
        db = OpenAtlasDB()
        project_data = db.get_project_data_json(project_id)
        
        if not project_data.get("success", True) or "error" in project_data:
            return {
                "success": False,
                "error": f"Failed to get project data: {project_data.get('error', 'Unknown error')}"
            }
        
        # Find the specific biosample in the project data
        target_brain = None
        for brain in project_data["brains"]:
            if str(brain["biosample"]) == str(biosample):
                target_brain = brain
                break
        
        if not target_brain:
            return {
                "success": False,
                "error": f"Biosample {biosample} not found in project {project_id}"
            }
        
        # Get available stains and their sections from the selection metadata
        selection_metadata = target_brain.get("selection_metadata", {})
        series_data = selection_metadata.get("series", {})
        
        if not series_data:
            return {
                "success": False,
                "error": f"No series data found for biosample {biosample} in project {project_id}"
            }
        
        # Build target stains with their sections
        target_stains_with_sections = {}
        reverse_stain_mapping = get_reverse_stain_mapping()
        
        for meta_stain, stain_data in series_data.items():
            db_stain = reverse_stain_mapping.get(meta_stain, meta_stain)
            sections = stain_data.get("sections", [])
            if sections:  # Only include stains that have sections
                target_stains_with_sections[db_stain] = sections
                print(f"DEBUG: Stain {db_stain} (metadata: {meta_stain}) has sections: {sections}")
        
        if not target_stains_with_sections:
            return {
                "success": False,
                "error": f"No stains with sections found for biosample {biosample} in project {project_id}"
            }
        
        total_stains = len(target_stains_with_sections)
        print(f"DEBUG: Will process {total_stains} stains for biosample {biosample}: {list(target_stains_with_sections.keys())}")
        print(f"DEBUG: Each stain will be processed individually using run_object_matching_old")
        
        # Generate hash for the bounding box (for consistent output directory)
        hash_box = str(bbox)
        hash_value = hashlib.md5(hash_box.encode("utf-8")).hexdigest()
        
        # Create base output directory
        base_results_dir = os.environ.get('RESULTS_DIR', '/apps/volumes/results')
        base_output_dir = f"{base_results_dir}/{project_id}/{hash_value}/{biosample}"
        
        processed_results = []
        processed_count = 0
        
        # Process each stain using run_object_matching_old
        for target_stain, available_sections in target_stains_with_sections.items():
            print(f"DEBUG: Processing stain {target_stain} for biosample {biosample} ({processed_count + 1}/{total_stains})")
            print(f"DEBUG: Available sections for biosample {biosample}, stain {target_stain}: {available_sections}")
            
            try:
                # Get actual metadata to find which sections are available in database
                metadata_all = get_metadata_for_all(biosample, target_stain)
                if not metadata_all:
                    print(f"DEBUG: No metadata available for biosample {biosample}, stain {target_stain}, skipping")
                    processed_count += 1
                    continue
                
                available_metadata_sections = list(metadata_all.keys())
                print(f"DEBUG: Sections with metadata for stain {target_stain}: {available_metadata_sections}")
                
                # Find the first section that exists in both project data and database metadata
                reference_section = None
                for section_num in available_sections:
                    if section_num in available_metadata_sections:
                        reference_section = section_num
                        break
                
                if reference_section is None:
                    print(f"DEBUG: No valid reference section found for stain {target_stain}. Project sections: {available_sections}, DB sections: {available_metadata_sections}")
                    print(f"DEBUG: Using first available DB section as fallback: {available_metadata_sections[0] if available_metadata_sections else 'None'}")
                    if available_metadata_sections:
                        reference_section = available_metadata_sections[0]
                    else:
                        processed_count += 1
                        continue
                
                print(f"DEBUG: Using section {reference_section} as reference for stain {target_stain}")
                
                # Call run_object_matching_old for this stain
                stain_result = run_object_matching_old(
                    bbox=bbox,
                    stain=target_stain,
                    biosample=biosample,
                    project_id=project_id,
                    section=reference_section,
                    progress_callback=None
                )
                
                if stain_result.get("success", False):
                    processed_results.append({
                        "biosample": biosample,
                        "stain": target_stain,
                        "reference_section": reference_section,
                        "sections_processed": stain_result.get("processed_sections", 0),
                        "total_sections": len(available_sections),
                        "output_path": stain_result.get("output_directory"),
                        "hash_value": stain_result.get("hash_value", hash_value)
                    })
                    print(f"DEBUG: Successfully processed biosample {biosample}, stain {target_stain}")
                else:
                    print(f"DEBUG: Failed to process biosample {biosample}, stain {target_stain}: {stain_result.get('error', 'Unknown error')}")
                
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total_stains, 
                                    f"Processed stain {target_stain} for biosample {biosample} ({processed_count}/{total_stains})")
                
            except Exception as stain_error:
                print(f"DEBUG: Error processing biosample {biosample}, stain {target_stain}: {stain_error}")
                processed_count += 1
                continue
        
        print(f"DEBUG: Completed processing {len(processed_results)} stains for biosample {biosample}")
        
        return {
            "success": True,
            "output_directory": base_output_dir,
            "processed_combinations": processed_results,
            "total_combinations": len(processed_results),
            "hash_value": hash_value,
            "biosample": biosample
        }
        
    except Exception as e:
        print(f"DEBUG: MAJOR ERROR in multi-stain matching: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

# ======= END MULTI-BIOSAMPLE SUPPORT =======

##Function Calling (Original script execution)
if __name__ == "__main__":
    # Example usage - this runs when the script is executed directly
    project_id = 137
    biosample = 222
    bbox = [
        25606.409140880016,
        -66500.21460810334,
        50830.62380964222,
        -58397.88960987465
    ]
    stain = 'NISL'
    section = 1291
    
    result = run_object_matching(bbox, stain, biosample, project_id, section)
    print(f"Result: {result}")
