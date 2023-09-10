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
## Center (Vector)
Readonly.  The center of the intersection.
## Check Vertex Intersection (Bool)
Default: True.  When there are 3 objects if the intersection of the first 2 is a vertex, then when this is True, the vertex is checked to see if it lies on the 3rd object.  Can resolve some cases where there are false positives.
## Enable Logging (Bool)
Default: False.  If True some rather quite cryptic logging message can be seen in the report view (also requires logging be enabled in FreeCAD).
## Has Intersection (Bool)
True if there is an intersection, False if not.  This property is readonly, for information only.
## Incomplete (Bool)
Readonly.  If this is True, then it means the first 2 objects were successfully intersected, but the 3rd object could not be used because the intersection was a vertex.
## Object1, Object2, Object3 (LinkSub)
The objects to test for intersection.  An example could be Sketch.Edge1, or Cylinder.Face2.  These should be faces or edges only, selected in the 3d view, but if the object only has one face or one edge it can be selected in the combo view / tree view.
## Object Order (Enumeration)
Allow to rearrange the order of evaluation of Object1, Object2, and Object3.  The way the order of evaluation works is first an intersection is sought between Object1 and Object2.  If an intersection is found, let's say for example an intersection between 2 faces results in a line, then the result (the line) is checked for an intersection with Object3, if any.  In some cases the intersection between Object1 and Object2 is a point.  Points cannot be used in the intersect() function, so the Incomplete property is set to True and a warning is shown in the Report view.  You can sometimes rearrange the order of evaluation in order to allow all 3 objects to be used.
## Reset On Recompute (Bool)
Default: True.  If True, reset the Intersection object's shape to null at the beginning of the recompute.  Set to False to retain the existing intersection shape when due to subsequent changes to the model the objects no longer intersect.  This is to help not to lose Link properties and have to configure them again.
## Tolerance (Float)
Default 0.01 mm.  When checking that the intersection shape (when it's a vertex) of the first 2 objects (when there are 3 objects) this tolerance value is used to determine whether a point lies on a surface / curve.
## Trimming (Enumeration)
Default: Untrimmed.  In Untrimmed mode faces and edges are treated as untrimmed (infinite) geometries.  In Trimmed mode a common is taken with the intersection shape and with the 2 or 3 objects in an attempt to trim the resulting intersection to match the surface.  Take the intersection of 2 perpendicular faces to see the difference here.
## Type (String)
The type of the intersection object.  This is also readonly.  Shows the TypeId of the intersection shape.  For example, if 2 datum planes are intersecting, then the Type would be Part::GeomLine.
## Version (String)
Readonly.  The version of the macro used to create this Intersection object.

# Limitations / Known Issues
* Surfaces and edges are often treated as infinite in size.<br/>
* A datum line tangent to a face might not be seen as intersecting.<br/>
To illustrate both of the above issues, consider a datum line positioned on the top face of a cube, running front to back.  If the datum line and the top face are selected to make the Intersection object, no intersection will be found even though the line is on the plane of the face.  But if the front face is selected along with the datum line, then an intersection will be found.  If you move the datum line in the z direction so that it is above the top face, the intersection with the front face is still found because the front face is treated as an infinite plane.<br/>
2 properties are there to help with these issues: Trimming and Check Vertex Intersection.

* seamlines may interfere with the intersection shape.  For example, if a datum plane intersects a sphere the seamline of the sphere might trim the intersection shape to produce an arc instead of a full circle.<br/>
* bspline edges are troublesome, sometimes not all intersections with s-type curves are found.

# Changelog
* 2023.09.09 -- add code for addon manager to be able to (hopefully) put an icon on the toolbar during installation
* 2022.02.26.rev2 -- minor tooltip changes
* 2022.02.26 -- Add face/edge editor, fix issue with CheckVertexIntersection()
* 2022.02.25 -- Add Trimming, Enable Logging, Object Order, ResetOnRecompute, CheckVertexIntersection properties.
* 2022.02.24.rev4 -- add Object Order property
* 2022.02.24.rev3 -- add support for 3rd object
* 2022.02.24.rev2 --make some properties readonly
* 2022.02.24 -- initial version
