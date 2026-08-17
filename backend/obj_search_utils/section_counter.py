from .get_sec_byproject import OpenAtlasDB
from .get_metadata import MySQL_db_retriever
from sqlalchemy import text

def count_sections_for_project(project_id, stain='NISL'):
    """
    Count the total number of sections across all biosamples in a project.
    
    Args:
        project_id (int): The project identifier
        stain (str): The stain type to count sections for (default: 'NISL')
    
    Returns:
        dict: Contains total section count and breakdown by biosample
    """
    
    # Get project data including biosamples
    db = OpenAtlasDB()
    project_data = db.get_project_data_json(project_id)
    
    if "error" in project_data:
        return {"error": project_data["error"], "total_sections": 0}
    
    total_sections = 0
    biosample_section_counts = {}
    
    # For each biosample in the project, count sections
    for brain in project_data["brains"]:
        biosample = brain["biosample"]
        
        # Query to count sections for this biosample
        query = f"""
        SELECT COUNT(sct.positionindex) as section_count
        FROM HBA_V2.seriesset ss 
        JOIN HBA_V2.series s ON ss.id = s.seriesset 
        JOIN HBA_V2.section sct ON s.id = sct.series 
        JOIN HBA_V2.seriestype st ON s.seriestype = st.id
        WHERE ss.biosample = {biosample}
        AND st.mnemonic = '{stain}'
        """
        
        try:
            result = MySQL_db_retriever(query)
            if result and len(result) > 0:
                section_count = result[0][0]
                biosample_section_counts[biosample] = section_count
                total_sections += section_count
            else:
                biosample_section_counts[biosample] = 0
        except Exception as e:
            print(f"Error counting sections for biosample {biosample}: {e}")
            biosample_section_counts[biosample] = 0
    
    return {
        "project_id": project_id,
        "total_sections": total_sections,
        "biosample_breakdown": biosample_section_counts,
        "project_name": project_data.get("project_name", "Unknown")
    }

def count_sections_for_biosample(biosample, stain='NISL', project_id=None):
    """
    Count the number of sections for a specific biosample within a project context.
    
    Args:
        biosample (int): The biosample identifier
        stain (str): The stain type to count sections for (default: 'NISL')
        project_id (int): The project identifier to get project-specific count
    
    Returns:
        dict: Contains section count and metadata for the biosample
    """
    
    if project_id is None:
        # Fallback to old behavior if no project_id provided
        query = f"""
        SELECT COUNT(sct.positionindex) as section_count
        FROM HBA_V2.seriesset ss 
        JOIN HBA_V2.series s ON ss.id = s.seriesset 
        JOIN HBA_V2.section sct ON s.id = sct.series 
        JOIN HBA_V2.seriestype st ON s.seriestype = st.id
        WHERE ss.biosample = {biosample}
        AND st.mnemonic = '{stain}'
        """
        
        try:
            result = MySQL_db_retriever(query)
            if result and len(result) > 0:
                section_count = result[0][0]
                return {
                    "biosample": biosample,
                    "section_count": section_count,
                    "stain": stain
                }
            else:
                return {
                    "biosample": biosample,
                    "section_count": 0,
                    "stain": stain
                }
        except Exception as e:
            print(f"Error counting sections for biosample {biosample}: {e}")
            return {
                "biosample": biosample,
                "section_count": 0,
                "stain": stain,
                "error": str(e)
            }
    else:
        # Use OpenAtlas to get project data and extract sections for the specific biosample
        db = OpenAtlasDB()
        project_data = db.get_project_data_json(project_id)
        
        if "error" in project_data:
            return {
                "biosample": biosample,
                "section_count": 0,
                "stain": stain,
                "error": project_data["error"]
            }
        
        # Find the specific biosample in the project brains
        target_brain = None
        for brain in project_data["brains"]:
            if brain["biosample"] == biosample:
                target_brain = brain
                break
        
        if target_brain is None:
            return {
                "biosample": biosample,
                "section_count": 0,
                "stain": stain,
                "error": f"Biosample {biosample} not found in project {project_id}"
            }
        
        # Navigate to selection_metadata -> series -> stain -> sections
        try:
            selection_metadata = target_brain.get("selection_metadata", {})
            series = selection_metadata.get("series", {})
            
            # Debug: print available stains
            print(f"DEBUG: Available stains in series: {list(series.keys())}")
            print(f"DEBUG: Looking for stain: '{stain}'")
            
            # Try both NISL and NISSL (common variations)
            stain_data = None
            if stain in series:
                stain_data = series[stain]
            elif stain == "NISL" and "NISSL" in series:
                stain_data = series["NISSL"]
                print(f"DEBUG: Found NISSL instead of NISL")
            elif stain == "NISSL" and "NISL" in series:
                stain_data = series["NISL"]
                print(f"DEBUG: Found NISL instead of NISSL")
            
            if stain_data is None:
                stain_data = {}
                print(f"DEBUG: No stain data found for '{stain}'")
            
            sections_list = stain_data.get("sections", [])
            
            # CLAUDE CHANGE: Handle all_sections=True case by getting sections from filesystem
            if stain_data.get("all_sections", False):
                print(f"DEBUG: all_sections=True for biosample {biosample}, stain {stain}, getting sections from filesystem")
                # Import the function from obj_matching
                from .obj_matching import get_sections_from_path
                sections_list = get_sections_from_path(biosample, stain)
                print(f"DEBUG: Found {len(sections_list)} sections from filesystem for biosample {biosample}, stain {stain}")
            # END CLAUDE CHANGE
            
            section_count = len(sections_list)
            
            print(f"DEBUG: Found {section_count} sections: {sections_list[:5] if len(sections_list) >= 5 else sections_list}...")
            
            return {
                "biosample": biosample,
                "section_count": section_count,
                "stain": stain,
                "project_id": project_id,
                "brain_name": target_brain.get("brain_name", "Unknown"),
                "sections": sections_list if section_count <= 20 else f"{section_count} sections available"
            }
            
        except Exception as e:
            return {
                "biosample": biosample,
                "section_count": 0,
                "stain": stain,
                "project_id": project_id,
                "error": f"Error extracting sections: {str(e)}"
            }

def get_project_biosamples(project_id):
    """
    Get all biosamples for a project.
    
    Args:
        project_id (int): The project identifier
    
    Returns:
        list: List of biosample IDs for the project
    """
    db = OpenAtlasDB()
    project_data = db.get_project_data_json(project_id)
    
    if "error" in project_data:
        return []
    
    return [brain["biosample"] for brain in project_data["brains"]]