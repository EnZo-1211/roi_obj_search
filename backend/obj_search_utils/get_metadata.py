
from sqlalchemy import create_engine, text


MySQL_db_user = "root"
MySQL_db_password = "Health#123"
# MySQL_db_host = "dev2test3.humanbrain.in"
MySQL_db_host = "apollo2.humanbrain.in"
MySQL_db_port = "3306"
MySQL_db_name = "HBA_V2"
MySQL_DATABASE_URL = f"mysql+pymysql://{MySQL_db_user}:{MySQL_db_password}@{MySQL_db_host}:{MySQL_db_port}/{MySQL_db_name}"
MySQL_engine = create_engine(
    MySQL_DATABASE_URL,
    pool_size=10,          # Number of connections to keep in pool
    max_overflow=20,       # Additional connections when pool is full
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo=False             # Set to True for SQL debug logging
)

def MySQL_db_retriever(sql_query):
    with MySQL_engine.connect() as connection:  
        result = connection.execute(text(sql_query))  
    data = result.fetchall()
    return data

# def get_zoomlevel(jp2_path):


def get_metadata(biosample, section, stain_type='NISL'):
    #sereies type = 1 is NISL
    # print(f"MySQL query: biosample={biosample}, section={section}, stain_type={stain_type}")
    
    query = f"""
    SELECT 
        sct.rigidrotation, 
        sct.width, 
        sct.height, 
        sct.jp2Path, 
        ss.ontology, 
        sct.trsdata, 
        sct.export_status, 
        st.mnemonic 
    FROM HBA_V2.seriesset ss 
    JOIN HBA_V2.series s ON ss.id = s.seriesset 
    JOIN HBA_V2.section sct ON s.id = sct.series 
    JOIN HBA_V2.seriestype st ON s.seriestype = st.id
    WHERE ss.biosample = {biosample}
    AND st.mnemonic = '{stain_type}'
    AND sct.positionindex = {section}
    """
    
    # print(f"Executing query: {query}")
    
    try:
        result = MySQL_db_retriever(query)
        print(f"Query result: {result}")
        
        if not result or len(result) == 0:
            print(f"No data found for biosample={biosample}, section={section}, stain={stain_type}")
            return None
            
        jp2_file_name = result[0][3].split("/")[-1]
        jp2_path = result[0][3]
        
        #if the export status from section table is 4 then the image can be loaded in tif
        if result[0][6] == 4:
            jp2_file_name = jp2_file_name.replace(".jp2", ".tif")
            jp2_path = result[0][3].replace(".jp2", ".tif")

        result_dict = {"rotation":result[0][0], "width":result[0][1], "height":result[0][2],
         "jp2_file_name":jp2_file_name, "ontology":result[0][4], "trs_data":result[0][5], "jp2_path": jp2_path}

        print(f"Returning metadata: {result_dict}")
        return result_dict
        
    except Exception as e:
        print(f"Error in get_metadata: {str(e)}")
        return None


def get_metadata_for_all(biosample, stain_type='NISL'):
    #sereies type = 1 is NISL
    # print(f"MySQL query: biosample={biosample}, section={section}, stain_type={stain_type}")
    
    query = f"""
    SELECT 
        sct.positionindex,
        sct.rigidrotation, 
        sct.width, 
        sct.height, 
        sct.jp2Path, 
        ss.ontology, 
        sct.trsdata, 
        sct.export_status, 
        st.mnemonic 
    FROM HBA_V2.seriesset ss 
    JOIN HBA_V2.series s ON ss.id = s.seriesset 
    JOIN HBA_V2.section sct ON s.id = sct.series 
    JOIN HBA_V2.seriestype st ON s.seriestype = st.id
    WHERE ss.biosample = {biosample}
    AND st.mnemonic = '{stain_type}'
    """
    
    # print(f"Executing query: {query}")

    result_dict = {}
    
    try:
        result = MySQL_db_retriever(query)
        # print(f"Query result: {result}")
        
        # if not result or len(result) == 0:
        #     print(f"No data found for biosample={biosample}, section={section}, stain={stain_type}")
        #     return None
        for r in result:
            jp2_file_name = r[4].split("/")[-1]
            jp2_path = r[4].replace(".jp2", ".tif") #added this line 
            # print(jp2_file_name)
            if r[7] == 4:
                jp2_file_name = jp2_file_name.replace(".jp2", ".tif")
                jp2_path = r[4].replace(".jp2", ".tif")
                # print(jp2_file_name)
            sec = r[0]
            result_dict[sec] =  {"rotation":r[1], 
                                 "width":r[2], 
                                 "height":r[3],
                                 "jp2_file_name":jp2_file_name,
                                 "ontology":r[5], 
                                 "trs_data":r[6], 
                                 "jp2_path": jp2_path}
            # print(result_dict[sec])
        # jp2_file_name = result[0][3].split("/")[-1]
        # jp2_path = result[0][3]
        
        # #if the export status from section table is 4 then the image can be loaded in tif
        # if result[0][6] == 4:
        #     jp2_file_name = jp2_file_name.replace(".jp2", ".tif")
        #     jp2_path = result[0][3].replace(".jp2", ".tif")

        # result_dict = {"rotation":result[0][0], "width":result[0][1], "height":result[0][2],
        #  "jp2_file_name":jp2_file_name, "ontology":result[0][4], "trs_data":result[0][5], "jp2_path": jp2_path}

        # print(f"Returning metadata: {result_dict}")
        return result_dict
        
    except Exception as e:
        print(f"Error in get_metadata: {str(e)}")
        return None