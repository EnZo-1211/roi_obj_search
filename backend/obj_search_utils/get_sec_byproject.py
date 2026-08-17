from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base
import pandas as pd
import json

class OpenAtlasDB:
    def __init__(self):
        self.db_config = {
            'NAME': 'OPEN_ATLAS',
            'USER': 'root',
            'PASSWORD': 'Health#123',
            'HOST': '172.20.23.98',
            'PORT': '3307'
        }
        self.engine = None
        self.Session = None
        self.Base = None
        
        # HBA_V2 database config (from metadata.py)
        self.hba_config = {
            'NAME': 'HBA_V2',
            'USER': 'root',
            'PASSWORD': 'Health#123',
            'HOST': 'apollo2.humanbrain.in',
            'PORT': '3306'
        }
        self.hba_engine = None
        
    def connect(self):
        """Establish database connection"""
        connection_string = f"mysql+pymysql://{self.db_config['USER']}:{self.db_config['PASSWORD']}@{self.db_config['HOST']}:{self.db_config['PORT']}/{self.db_config['NAME']}"
        
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        
        # Auto-map existing tables
        self.Base = automap_base()
        self.Base.prepare(autoload_with=self.engine)
        
        # Also connect to HBA_V2 database
        hba_connection_string = f"mysql+pymysql://{self.hba_config['USER']}:{self.hba_config['PASSWORD']}@{self.hba_config['HOST']}:{self.hba_config['PORT']}/{self.hba_config['NAME']}"
        self.hba_engine = create_engine(hba_connection_string)
        
# Database connections established
        return self.engine
    
    def get_session(self):
        """Get database session"""
        if not self.Session:
            self.connect()
        return self.Session()
    
    def explore_table_relationships(self):
        """Explore relationships between the three main tables"""
        session = self.get_session()
        
        print("=== EXPLORING TABLE RELATIONSHIPS ===\n")
        
        # Check table structures
        tables_to_explore = ['groups_project', 'groups_projectbrainselection', 'groups_brainidentifier']
        
        for table_name in tables_to_explore:
            print(f"--- {table_name.upper()} TABLE STRUCTURE ---")
            try:
                # Get table columns
                result = session.execute(text(f"DESCRIBE {table_name}"))
                columns = result.fetchall()
                for column in columns:
                    print(f"  {column[0]} - {column[1]} - {column[2]} - {column[3]}")
                print()
            except Exception as e:
                print(f"Error exploring {table_name}: {e}\n")
        
        # Check foreign key relationships
        print("--- FOREIGN KEY RELATIONSHIPS ---")
        try:
            fk_query = """
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                CONSTRAINT_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE
                REFERENCED_TABLE_SCHEMA = 'OPEN_ATLAS' 
                AND TABLE_NAME IN ('groups_project', 'groups_projectbrainselection', 'groups_brainidentifier')
            ORDER BY TABLE_NAME, COLUMN_NAME;
            """
            result = session.execute(text(fk_query))
            relationships = result.fetchall()
            
            if relationships:
                for rel in relationships:
                    print(f"  {rel[0]}.{rel[1]} -> {rel[3]}.{rel[4]} (Constraint: {rel[2]})")
            else:
                print("  No foreign key relationships found in schema information.")
            print()
        except Exception as e:
            print(f"Error getting foreign keys: {e}\n")
        
        # Sample data from each table to understand connections
        print("--- SAMPLE DATA AND POTENTIAL CONNECTIONS ---")
        for table_name in tables_to_explore:
            try:
                print(f"{table_name.upper()}:")
                result = session.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                rows = result.fetchall()
                columns = result.keys()
                
                if rows:
                    print(f"  Columns: {list(columns)}")
                    for i, row in enumerate(rows):
                        print(f"  Row {i+1}: {dict(zip(columns, row))}")
                else:
                    print("  No data found")
                print()
            except Exception as e:
                print(f"  Error sampling {table_name}: {e}\n")
        
        # Look for common column names that might indicate relationships
        print("--- ANALYZING POTENTIAL RELATIONSHIPS BY COLUMN NAMES ---")
        try:
            common_columns_query = """
            SELECT 
                t1.TABLE_NAME as table1,
                t1.COLUMN_NAME as column1,
                t2.TABLE_NAME as table2,
                t2.COLUMN_NAME as column2
            FROM 
                INFORMATION_SCHEMA.COLUMNS t1
            JOIN 
                INFORMATION_SCHEMA.COLUMNS t2 
            ON 
                t1.COLUMN_NAME = t2.COLUMN_NAME 
                AND t1.TABLE_NAME != t2.TABLE_NAME
            WHERE 
                t1.TABLE_SCHEMA = 'OPEN_ATLAS' 
                AND t2.TABLE_SCHEMA = 'OPEN_ATLAS'
                AND t1.TABLE_NAME IN ('groups_project', 'groups_projectbrainselection', 'groups_brainidentifier')
                AND t2.TABLE_NAME IN ('groups_project', 'groups_projectbrainselection', 'groups_brainidentifier')
            ORDER BY t1.COLUMN_NAME;
            """
            result = session.execute(text(common_columns_query))
            common_cols = result.fetchall()
            
            if common_cols:
                print("  Common columns that might indicate relationships:")
                for col in common_cols:
                    print(f"    {col[0]}.{col[1]} <-> {col[2]}.{col[3]}")
            else:
                print("  No common columns found between tables")
            print()
        except Exception as e:
            print(f"Error finding common columns: {e}\n")
        
        session.close()
        
        # Summary
        print("=== RELATIONSHIP SUMMARY ===")
        print("Based on table names, likely relationships:")
        print("  • groups_project: Main project table")
        print("  • groups_projectbrainselection: Links projects to brain selections") 
        print("  • groups_brainidentifier: Contains brain identifier information")
        print("  • Probable flow: project -> brain selection -> brain identifier")
    
    def get_biosample_and_seriesset(self, brain_id):
        """Get biosample and seriesset_id from HBA_V2 database based on brain_id"""
        if not self.hba_engine:
            self.connect()
        
        try:
            with self.hba_engine.connect() as connection:
                # Query to get biosample and seriesset_id (ss.id) from HBA_V2
                # brain_id maps to seriesset.id, and we want the biosample from that seriesset
                query = """
                SELECT 
                    ss.biosample,
                    ss.id as seriesset_id
                FROM HBA_V2.seriesset ss 
                WHERE ss.id = :brain_id
                LIMIT 1
                """
                
                result = connection.execute(text(query), {"brain_id": brain_id})
                row = result.fetchone()
                
                if row:
                    return {
                        "biosample": row[0],
                        "seriesset_id": row[1]
                    }
                else:
                    return {
                        "biosample": brain_id,  # fallback to brain_id
                        "seriesset_id": None
                    }
                    
        except Exception as e:
            return {
                "biosample": brain_id,  # fallback to brain_id
                "seriesset_id": None
            }
        
    def get_project_data_json(self, project_id):
        """Get project data with brain details and selection metadata as JSON"""
        session = self.get_session()
        
        try:
            # Query to get all required data in one go
            query = """
            SELECT 
                p.name as project_name,
                bi.brain_id,
                bi.brain_name,
                pbs.selection_metadata
            FROM 
                groups_project p
            JOIN 
                groups_projectbrainselection pbs ON p.id = pbs.project_id
            JOIN 
                groups_brainidentifier bi ON pbs.brain_identifier_id = bi.id
            WHERE 
                p.id = :project_id
            """
            
            result = session.execute(text(query), {"project_id": project_id})
            rows = result.fetchall()
            
            if not rows:
                return {"error": f"No data found for project ID {project_id}"}
            
            # Build the response JSON
            project_data = {
                "project_id": project_id,
                "project_name": rows[0][0],  # project_name from first row
                "brains": []
            }
            
            for row in rows:
                project_name, brain_id, brain_name, selection_metadata = row
                
                # Get biosample and seriesset_id from HBA_V2 database
                biosample_data = self.get_biosample_and_seriesset(brain_id)
                
                # Parse selection_metadata JSON
                try:
                    selection_meta = json.loads(selection_metadata) if selection_metadata else {}
                except json.JSONDecodeError:
                    selection_meta = {}
                
                brain_data = {
                    "biosample": biosample_data["biosample"],
                    "seriesset_id": biosample_data["seriesset_id"],
                    "brain_name": brain_name,
                    "selection_metadata": selection_meta
                }
                
                project_data["brains"].append(brain_data)
            
            session.close()
            return project_data
            
        except Exception as e:
            session.close()
            return {"error": f"Database error: {str(e)}"}
    
    def get_project_data_json_pretty(self, project_id):
        """Get project data and print it as pretty JSON"""
        import json
        
        data = self.get_project_data_json(project_id)
        pretty_json = json.dumps(data, indent=4, default=str)
        print(pretty_json)
        return data






if __name__ == "__main__":
    # Initialize database connection
    db = OpenAtlasDB()
    
    try:
        # Connect to database
        db.connect()
        
        # Test with project ID 115
        db.get_project_data_json_pretty(137)
       
    except Exception as e:
        print(f"Database connection error: {e}")