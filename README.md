# Intersection
FreeCAD Macro creates intersection object between 2 or 3 selected faces / edges

# Installation
Not yet available in the addon manager.  Place the .FCMacro file into your macro folder.  On first run it will offer to create a new file, intersection.py.  This file is needed in order for the Intersection object to be functional after restarting FreeCAD and loading a document containing one of the objects.  If the Intersection macro is uninstalled you will need to manually remove the intersection.py file, too.<br/>

# Toolbar Icon
Download the toolbar <a href="Intersection_Icon.svg">icon</a> <img src="Intersection_Icon.svg" alt="toolbar icon"><br/>

# Usage
Select 2 or 3 objects, run the macro.  Produces an Intersection object, which will be the shape of the intersection.<br/>
<br/>
Selection can be any combination of 2 or 3 faces or edges.<br/>
<br/>
* 2 edges
* 3 edges
* 2 faces
* 3 faces
* 2 edges, 1 face
* 1 edge, 2 faces

It is generally better to select the subobjects in the 3d view, but if the selected object only has 1 face or 1 edge it can be selected in the combo view, if desired.  Datum Planes and Datum Lines may also be used.  If 3 objects are selected, the order of selection can be important.  The underlying freeCAD function only supports 2 objects at a time, so the first 2 objects must be intersected first, and then the 3rd object is tested for intersections against that first result (between objects 1 and 2).  But only surfaces and edges have this intersect function, so if the intersection of the first 2 objects is a vertex, then the 3rd object cannot be used and the result will be considered "Incomplete".  If you wish to use 2 faces and an edge, then select the faces first, and then the edge last.<br/>
<br/>
A new Intersection object is created in the tree.  If there is an intersection between the selected subobjects the Intersection object's Shape will be that intersection.  It can be a point, multiple points, a line, or a bspline, depending on the intersection.  If there is an active Body, the Intersection object will be placed in that Body.  If there is no active Body, but there is an active Part, then the Intersection will go into that Part.<br/>
<br/>
The edge will be blue, the points will be a lighter shade of blue.  The Intersection object is parametric.  If the faces/edges change and there is no longer an intersection, the shape will remain, but the colors will change to red (edges) and orange (points) to indicate the intersection has been lost.  This rather than nullifying the shape is so if there are links to the intersection, such as links to external geometry within a sketch, those links will not be lost if the loss of the intersection is only temporary.  The tree icon also changes to indicate there is no intersection.  There will be a prominent red exclamation point in the icon when there is no intersection.<br/>
<br/>
# Properties
The Intersection object has a few properties.
## Has Intersection (Bool)
True if there is an intersection, False if not.  This property is readonly, for information only.
## Incomplete (Bool)
Readonly.  If this is True, then it means the first 2 objects were successfully intersected, but the 3rd object could not be used because the intersection was a vertex.
## Object1, Object2 (LinkSub)
The objects to test for intersection.  An example could be Sketch.Edge1, or Cylinder.Face2.
## Type (String)
The type of the intersection object.  This is also readonly.  Shows the TypeId of the intersection shape.  For example, if 2 datum planes are intersecting, then the Type would be Part::GeomLine.
## Version (String)
Readonly.  The version of the macro used to create this Intersection object.

# Limitations / Known Issues
* Surfaces and edges are often treated as infinite in size.<br/>
* A datum line tangent to a face might not be seen as intersecting.<br/>
<br/>
To illustrate both of the above issues, consider a datum line positioned on the top face of a cube, running front to back.  If the datum line and the top face are selected to make the Intersection object, no intersection will be found even though the line is on the plane of the face.  But if the front face is selected along with the datum line, then an intersection will be found.  If you move the datum line in the z direction so that it is above the top face, the intersection with the front face is still found because the front face is treated as an infinite plane.<br/>
* seamlines may interfere with the intersection shape.  For example, if a datum plane intersects a sphere the seamline of the sphere might trim the intersection shape to produce an arc instead of a full circle.<br/>
* 

# Changelog
* 2022.02.24.rev3 -- add support for 3rd object
* 2022.02.24.rev2 --make some properties readonly
* 2022.02.24 -- initial version
