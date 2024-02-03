"""Donut-cutter
"""

import numpy as np
import shapely.geometry as sg
import shapely
import fiona
import sys
from pathlib import Path
from shapely.ops import nearest_points


# SETTINGS ########################################################################

GAP = 0.001

TESTDIRECTORY = "./data"
TESTFILE_IN = "donut_meshzone.shp"
TESTFILE_OUT = "donuts_out.shp"
TESTFILE_POINTS = "donuts_points.shp"
TESTFILE_LINES = "donuts_lines.shp"

TEST_IN = Path(TESTDIRECTORY)/TESTFILE_IN
TEST_OUT = Path(TESTDIRECTORY)/TESTFILE_OUT
TEST_POINTS = Path(TESTDIRECTORY)/TESTFILE_POINTS
TEST_LINES = Path(TESTDIRECTORY)/TESTFILE_LINES


# FUNCTIONS #######################################################################

def split_point(outline,point):
	circle = sg.Point(point).buffer(GAP)
	bound = circle.boundary
	inter = shapely.intersection(outline,bound)
	return(inter.geoms[0],inter.geoms[1])

def draw_new(exterior,interior,sign_ext,sign_int):
	exterior = sg.polygon.orient(shapely.Polygon(exterior), sign=sign_ext)
	exterior = exterior.exterior
	interior = sg.polygon.orient(shapely.Polygon(interior), sign=sign_int)
	interior = interior.exterior
	center = interior.centroid
	nearest_ext = nearest_points(sg.MultiPoint(exterior.coords),center)[0]
	nearest_int = nearest_points(sg.MultiPoint(interior.coords),nearest_ext)[0]
	for index_ext in range(0,len(exterior.coords)):
		if exterior.coords[index_ext]==nearest_ext.coords[0]:
			break
	for index_int in range(0,len(interior.coords)):
		if interior.coords[index_int]==nearest_int.coords[0]:
			break
	newline = sg.LineString([nearest_ext,nearest_int])
	ext_a, ext_b = split_point(exterior,nearest_ext)
	int_a, int_b = split_point(interior,nearest_int)
	new_ext = ext_a
	new_int = int_a
	newline2 = newline
	for test_ext in (ext_a,ext_b):
		for test_int in (int_a,int_b):
			test_line = sg.LineString([test_ext,test_int])
			if not shapely.intersection(newline,test_line):
				if newline2 == newline:
					newline2 = test_line
					new_ext = test_ext
					new_int = test_int
				else:
					if test_line.length < newline2.length:
						newline2 = test_line
						new_ext = test_ext
						new_int = test_int
	return(exterior,interior,nearest_ext,nearest_int,index_ext,index_int,new_ext,new_int,center)

def cut(exterior,interior):
	exterior,interior,\
	nearest_ext,nearest_int,\
	index_ext,index_int,\
	new_ext,new_int,\
	center = draw_new(exterior,interior,-1,1)
	
	try:
		new = []
		leg1 = shapely.LineString([nearest_ext,exterior.coords[index_ext+1]])
		pnt1 = sg.Point(new_ext).buffer(GAP/3)
		if shapely.intersection(pnt1,leg1):
			exterior,interior,\
			nearest_ext,nearest_int,\
			index_ext,index_int,\
			new_ext,new_int,\
			center = draw_new(exterior,interior,1,-1)
			if index_ext!=0:
				new.append(exterior.coords[:index_ext])
			new.append(new_ext.coords)
			new.append(new_int.coords)
			if index_int==len(interior.coords):
				new.append(interior.coords[1:-1])
			else:
				new.append(interior.coords[index_int+1:])
				new.append(interior.coords[:index_int+1])
			new.append(nearest_int.coords)
			new.append(nearest_ext.coords)
			if index_ext!=len(exterior.coords):
				new.append(exterior.coords[index_ext:])	
		else:
			leg2 = shapely.LineString([nearest_ext,exterior.coords[index_ext-1]])
			pnt2 = sg.Point(new_ext).buffer(GAP/3)
			if shapely.intersection(pnt2,leg2):
				if index_ext!=0:
					new.append(exterior.coords[:index_ext])
				new.append(new_ext.coords)
				new.append(new_int.coords)
				if index_int==len(interior.coords):
					new.append(interior.coords[1:-1])
				else:
					new.append(interior.coords[index_int+1:])
					new.append(interior.coords[:index_int+1])
				new.append(nearest_int.coords)
				new.append(nearest_ext.coords)
				if index_ext!=len(exterior.coords):
					new.append(exterior.coords[index_ext:])	
			else:
				exterior,interior,\
				nearest_ext,nearest_int,\
				index_ext,index_int,\
				new_ext,new_int,\
				center = draw_new(exterior,interior,1,-1)
				if index_ext!=0:
					new.append(exterior.coords[:index_ext])
				new.append(new_ext.coords)
				new.append(new_int.coords)
				if index_int==len(interior.coords):
					new.append(interior.coords[1:-1])
				else:
					new.append(interior.coords[index_int+1:])
					new.append(interior.coords[:index_int+1])
				new.append(nearest_int.coords)
				new.append(nearest_ext.coords)
				if index_ext!=len(exterior.coords):
					new.append(exterior.coords[index_ext:])	
		new = np.vstack(new)
		new[-1]=new[0]
		exterior = sg.LinearRing(new)
		print("ok")
	except:
		print("fail")

	return(exterior)

	
def fix_part(part_in):
	if len(part_in.interiors):
		exterior = part_in.exterior
		for interior in part_in.interiors:
			exterior = cut(exterior,interior)
		part_in = sg.Polygon(exterior)
	return part_in


# MAIN ########################################################################

def main(input_shp,output_shp,gap):
    """"""
    with fiona.open(input_shp) as source:
    	output_schema = dict(source.schema)
    	output_schema['geometry'] = "Polygon"
    	with fiona.open(output_shp,'w',
        				driver=source.driver,
        				crs=source.crs,
        				schema=output_schema) as output:
	    	for item in source:
	    		shape = sg.shape(item['geometry'])
	    		if shape.geom_type == "MultiPolygon":
	    			for part in shape.geoms:
	    				part = fix_part(part)
	    				output.write({'id':-1,
	    					'properties':item['properties'],
	    					'geometry':sg.mapping(part)})
	    		elif shape.geom_type == "Polygon":
	    			part = fix_part(shape)
	    			output.write({'id':-1,
	    				'properties':item['properties'],
	    				'geometry':sg.mapping(part)})
	    		else:
	    			print(f"This is not a ploygon: {shape.geom_type}")


def test():
    main(TEST_IN,TEST_OUT,GAP)


if __name__ == "__main__":
    test()