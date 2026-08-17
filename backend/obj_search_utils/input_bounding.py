import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
from sqlalchemy import create_engine, text
from obj_search_utils.get_metadata import get_metadata


def apply_correction(pts,rot,jp2_wid,jp2_hei):
    if rot==270:
        theta = -90*np.pi/180
    elif rot==90:
        theta = 90*np.pi/180
    elif rot==180:
        theta = np.pi
    elif rot == 0:
        theta = 0

    c,s = np.cos(theta), np.sin(theta)

    org = np.array([jp2_wid//2,-jp2_hei//2])

    pts_rot = []
    for pt in pts:
        x,y = pt-org
        x_ = x*c-y*s+org[0]
        y_ = x*s+y*c+org[1]
        pts_rot.append([x_,y_])

    pts_rot = np.array(pts_rot)
    
    return pts_rot


def get_thumbnail_path(biosample, section, stain):
    sec_path =  f"/apps/analytics/{biosample}/{stain}/"
    for p in Path(sec_path).rglob("*thumbnail_original.jpg"):
        # print(p.parts)
       f_name = p.parts[-1]
       sec = f_name.split("SE_")[1].split("_")[0]
       #print(sec)
       if sec == str(section):
           return "/".join(p.parts)[1:]


def input_bound(bbox,bio_sample,stain,section):
    
    thumbnail_path=get_thumbnail_path(bio_sample,section,stain)
    #added here 
    sec_metadata = get_metadata(bio_sample, section,stain)
    
    WSI_WIDTH, WSI_HEIGHT = sec_metadata['width'], sec_metadata['height']


    thumbnail_image = Image.open(thumbnail_path)


    x1, y1, x2, y2 = bbox

    bbox_poly = np.array([
        [x1, y1],
        [x2, y1],
        [x2, y2],
        [x1, y2],
        [x1, y1]   
    ])
    
    coords = apply_correction(
        bbox_poly,
        0,
        WSI_WIDTH,
        WSI_HEIGHT
        )
    coords /= 2**6
    coords[:, 1] *= -1
    
    #plt.imshow(thumbnail_image)
    #plt.plot(coords[:, 0], coords[:, 1], 'r-', linewidth=2)
    #plt.axis("off")
    #plt.savefig('input_box2.png')
    #plt.show()

    x_coords = coords[:, 0]
    y_coords = coords[:, 1]
    x_min, x_max = int(x_coords.min()), int(x_coords.max())
    y_min, y_max = int(y_coords.min()), int(y_coords.max())
    
    cropped_image = thumbnail_image.crop((x_min, y_min, x_max, y_max))

    return cropped_image








