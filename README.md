# Intersection
FreeCAD Macro creates intersection object between 2 selected faces / edges

# Installation
Not yet available in the addon manager.  Place the .FCMacro file into your macro folder.  On first run it will offer to create a new file, intersection.py.  This file is needed in order for the Intersection object to be functional after restarting FreeCAD and loading a document containing one of the objects.  If the Intersection macro is uninstalled you will need to manually remove the intersection.py file, too.<br/>

# Toolbar Icon
Download the toolbar <a href="Intersection_Icon.svg">icon</a> <img src="Intersection_Icon.svg" alt="toolbar icon"><br/>

# Usage
Select both faces or edges in the 3d view (not in the tree / combo view), then run the macro.<br/>
<br/>
Selection can be:<br/>
2 faces <br/>
1 face, 1 edge <br/>
2 edges <br/>
<br/>
A new Intersection object is created in the tree.  If there is an intersection between the 2 selected subobjects the Intersection object's Shape will be that intersection.  It can be a point, multiple points, a line, or a bspline, depending on the intersection.  If there is an active Body, the Intersection object will be placed in that Body.  If there is no active Body, but there is an active Part, then the Intersection will go into that Part.<br/>
<br/>
The edge will be blue, the points will be a lighter shade of blue.  The Intersection object is parametric.  If the faces/edges change and there is no longer an intersection, the shape will remain, but the colors will change to red (edges) and orange (points) to indicate the intersection has been lost.  This rather than nullifying the shape is so if there are links to the intersection, such as links to external geometry within a sketch, those links will not be lost if the loss of the intersection is only temporary.  The tree icon also changes to indicate there is no intersection.  There will be a prominent red exclamation point in the icon when there is no intersection.<br/>
<br/>

