__version__ = "2024.08.05"
__title__ = "Intersection"
__author__ = "<TheMarkster> 2021"
__license__ = "LGPL 2.1"
__doc__ = "Find the intersection of 2 or 3 faces/edges"
__usage__ = '''Select 2 faces or edges in the 3d view and run the macro'''
from PySide import QtGui,QtCore
import FreeCAD, FreeCADGui, Part
import os

Gui = FreeCADGui
App = FreeCAD
#intersection macro, (c) 2022, by <TheMarkster>
#Full documentation on github at https://github.com/mwganson/intersection
class Intersection:
    def __init__(self,obj):
        obj.Proxy = self
        obj.addProperty("App::PropertyVector","Center","Intersection","Center of Mass of intersection result")
        obj.addProperty("App::PropertyBool","EnableLogging","Intersection","Enable log messages").EnableLogging = False
        obj.addProperty("App::PropertyEnumeration","ObjectOrder","Intersection","Order of evaluation").ObjectOrder =\
                ["1,2,3","1,3,2","2,1,3","2,3,1","3,1,2","3,2,1","1,2","2,1","1,3","3,1","3,2","2,3"]
        obj.addProperty("App::PropertyLinkSub","Object1","Intersection","First intersection object")
        obj.addProperty("App::PropertyLinkSub","Object2","Intersection","Second intersection object")
        obj.addProperty("App::PropertyLinkSub","Object3","Intersection","Optional 3rd object")
        obj.addProperty("App::PropertyBool","HasIntersection","Intersection","If intersection is found this will be True")
        obj.addProperty("App::PropertyBool","CheckVertexIntersection","Intersection",\
    "When there are 3 objects and the intersection of the first 2 is a vertex, set this True \
    to require that the vertex lies on the 3rd face or edge\n").CheckVertexIntersection = False
        obj.addProperty("App::PropertyBool","ResetOnRecompute","Intersection","Reset shape to null at the start of each recompute").ResetOnRecompute = True
        obj.addProperty("App::PropertyFloatConstraint","Tolerance","Intersection","Tolerance, default: 0.01 mm").Tolerance = (0.01,0,float("inf"),.01)
        obj.addProperty("App::PropertyString","Type","Intersection","Type of the intersection object or None").Type="None"
        obj.addProperty("App::PropertyString","Version","Intersection").Version = __version__
        obj.addProperty("App::PropertyEnumeration","Trimming","Intersection","If Trimmed, then the intersection edge is attempted to be trimmed to surfaces\n\
    If the intersection does not lie on the surface/edge, then it will not be considered an intersection in Trimmed mode.").Trimming = \
    ["Untrimmed","Trimmed"]
        obj.setEditorMode("HasIntersection",1) #readonly
        obj.setEditorMode("Version",1)
        obj.setEditorMode("Type",1)
        self.fpName = obj.Name
        self.editingMode = False

    def log(self,fp,msg):
        if fp.EnableLogging:
            FreeCAD.Console.PrintLog(msg)

    def validate(self, fp, propName):
        prop = getattr(fp,propName)
        if not prop:
            return
        prop1 = prop[1]
        if not prop1:
            obj = prop[0]
            if len(obj.Shape.Faces) == 1:
                prop1 = "Face1" if not obj.isDerivedFrom("PartDesign::Plane") else "Plane"
            elif len(obj.Shape.Edges) == 1:
                prop1 = "Edge1" if not obj.isDerivedFrom("PartDesign::Line") else "Line"
            elif len(obj.Shape.Vertexes) == 1:
                prop1 = "Vertex1" if not obj.isDerivedFrom("PartDesign::Point") else "Point"
                FreeCAD.Console.PrintWarning("Intersection: Vertex objects not supported\n")
            else:
                return
            setattr(fp,propName,(obj,prop1))

    def execute(self,fp):
        if fp.ResetOnRecompute:
            fp.Shape = Part.Shape()
        self.validate(fp,"Object1")
        self.validate(fp,"Object2")
        self.validate(fp,"Object3")
        shape = self.findIntersection(fp)
        if not shape.isNull():
            fp.Shape = self.makeShapeType(fp,shape)
        fp.Type = self.getIntersectionType(fp,fp.Shape)
        try:
            fp.Shape.check()
            fp.HasIntersection = not fp.Shape.isNull()
        except:
            fp.HasIntersection = False
            fp.Shape = Part.Shape()

    def makeShapeType(self,fp,shp):
        if fp.Trimming == "Untrimmed":
            return shp
        if fp.Trimming == "Trimmed":
            obj1,obj2,obj3 = self.getOrderedObjectShapes(fp)

            common = shp.common(obj1) if obj1 and not obj1.isNull() else shp
            common = common.common(obj2) if obj2 and not obj2.isNull() else common
            common = common.common(obj3) if obj3 and  not obj3.isNull() else common
            return common

    def getIntersectionType(self,fp,shp):
        if hasattr(shp,"Compound1") and hasattr(shp.Compound1,"Edge1"):
            fp.Center = shp.Compound1.Edge1.CenterOfGravity
            return shp.Compound1.Edge1.Curve.TypeId
        if hasattr(shp,"Surface"):
            fp.Center = shp.Surface.Position
            return shp.Surface.TypeId
        if hasattr(shp,"Vertex1"):
            fp.Center = shp.Vertex1.Point
            return shp.Vertex1.ShapeType
        if not shp:
            fp.Center = FreeCAD.Vector()
            return "None"
        if hasattr(shp,"isNull") and shp.isNull():
            fp.Center = FreeCAD.Vector()
            return "Null shape"
        return shp.ShapeType

    def getIntersectionShape(self,fp,intersection):
        """return geometry / list as shape"""
        shape = Part.Shape()
        #self.log(fp,f"Intersection macro: intersection = {intersection}\n")
        if intersection:
            self.log(fp,f"getintshp(): intersection = {intersection}\n")
            intObj = intersection #can be [point,point...] or line or [bspline,bspline...]
            if isinstance(intObj,list):
                self.log(fp,f"getintshp(): intObj is list\n")
                shapes = [sh.toShape() for sh in intObj]
                self.log(fp,f"getintshp(): shapes = {shapes}\n")
                shape = Part.makeCompound(shapes) if len(shapes)>1 else shapes[0]
            elif isinstance(intObj,tuple):
                self.log(fp,f"getintshp(): intersection is a tuple\n")
                shapes = [sh.toShape() for sh in intObj[0]]
                self.log(fp,f"getintshp(): shapes = {shapes}\n")
                shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0] if shapes else Part.Shape()
            else:
                shape = intersection.toShape() if hasattr(intersection,"toShape") else Part.Shape()
        self.log(fp,f"getintshp():(after) shape = {shape}\n")
        return shape

    def getOrderedObjectShapes(self,fp):
        """gets the shapes user has set for the Object links according to the order in fp.ObjectOrder"""
        s1 = fp.Object1[0].getSubObject(fp.Object1[1])[0] if fp.Object1 else None
        s2 = fp.Object2[0].getSubObject(fp.Object2[1])[0] if fp.Object2 else None
        s3 = fp.Object3[0].getSubObject(fp.Object3[1])[0] if fp.Object3 else None
        orders = [(s1,s2,s3),(s1,s3,s2),(s2,s1,s3),(s2,s3,s1),(s3,s1,s2),(s3,s2,s1),\
        (s1,s2,None),(s2,s1,None),(s1,s3,None),(s3,s1,None),(s3,s2,None),(s2,s3,None)]
        s1,s2,s3 = orders[fp.getEnumerationsOfProperty("ObjectOrder").index(fp.ObjectOrder)]
        return (s1,s2,s3)


    def findIntersection(self,fp):
        if not fp.Object1 or not fp.Object2:
            return Part.Shape()
        try:
            s1,s2,s3 = self.getOrderedObjectShapes(fp)
        except Exception as ex:
            FreeCAD.Console.PrintError(f"{ex}")
            return Part.Shape()
        c1 = s1.Curve if hasattr(s1,"Curve") else s1.Surface if hasattr(s1,"Surface") else None
        c2 = s2.Curve if hasattr(s2,"Curve") else s2.Surface if hasattr(s2,"Surface") else None
        c3 = s3.Curve if hasattr(s3,"Curve") else s3.Surface if hasattr(s3,"Surface") else None
        if not bool(c1 != None and c2 != None):
            FreeCAD.Console.PrintError("First 2 shapes in the shape order have to be valid shapes, neither can null or empty\n")
            return Part.Shape()
        intersection = c1.intersect(c2, fp.Tolerance)
        if not intersection:
            self.log(fp,"No intersection, trying c2 -> c1 instead of c1 -> c2\n")
            intersection = c2.intersect(c1, fp.Tolerance)
            intersection = self.getIntersectionShape(fp,intersection)
        if not intersection:
            self.log(fp,"No intersection between c1 and c2\n")
            return Part.Shape()
        intersection = self.trimEdgeToSurfaces(fp,intersection,s1,s2)
        shape = self.getIntersectionShape(fp, intersection)
        if shape.isNull():
            self.log(fp,"No intersection shape\n")
            return Part.Shape()
        if not c3: #success with first 2 objects, no third object
            self.log(fp,f"checking shape = {shape} and s2 = {s2} \n")
            shape = self.checkVertexIntersection(fp, shape, s2)
            if shape.isNull():
                self.log(fp,"check vertex intersection returned null shape\n")
                return shape #shape was not inside c2
            else:
                shape = self.checkVertexIntersection(fp, shape, s1)
                self.log(fp,f"shape.isNull() = {shape.isNull()} after checking vertex with s1 {s1}\n")
                return shape
        c4 = shape.Curve if hasattr(shape,"Curve") else shape.Surface if hasattr(shape,"Surface") else None
        if not c4: #intersection at vertex found, now check against c3, c2, and c1
            return self.checkAllVertexIntersections(fp, shape, s1, s2, s3)
        #intersection was not a vertex, so must be an edge
        #c4 is the curve result, c3 is the surface/curve of Object3
        self.log(fp,f"checking c3.intersect(c4,fp.Tolerance) {c3}.intersect({c4},fp.Tolerance)\n")
        intersection = c3.intersect(c4,fp.Tolerance) if c4 else None
        self.log(fp,f"intersection = {intersection}\n")
        if not intersection:
            return Part.Shape()
        return self.getIntersectionShape(fp,intersection)

    def checkVertexIntersection(self, fp, shp, s3):
        """shp is a vertex shape inside a compound, s3 is an object, either a Curve or a Surface to test shp
            for intersection with.  Returns the vertex if it intersects with s3, or a null shape if not."""
        if not fp.CheckVertexIntersection:
            return shp
        if shp.isNull():
                self.log(fp,"ckvtx: shp is null\n")
                return shp
        self.log(fp,f"checkVertexIntersection(): shp = {shp}, s3 = {s3}\n")
        if not hasattr(shp,"Face1") and not hasattr(shp,"Edge1") and not hasattr(shp,"Plane") and not hasattr(shp,"Line") and hasattr(shp,"Vertex1"):
            msgs = [f"shp {shp} is a vertex, pt = {v.Point}\n" for v in s3.Vertexes]
            for msg in msgs:
                self.log(fp,msg)
            verts = [v for v in shp.Vertexes if v.distToShape(s3)[0] <= fp.Tolerance]
            if not verts:
                self.log(fp,f"ckvtxint: no points out of {len(s3.Vertexes)} found on {s3}\n")
            for v in verts:
                self.log(fp,f"ckvtxint: {v.Point} is on {s3}\n")
            comp = Part.makeCompound(verts) if verts else Part.Shape()
            self.log(fp,f"comp.check(True) = {comp.check(True)}\n")
            return comp
        else: #was not a vertex
            self.log(fp,f"{shp} was Not a vertex\n")
            return shp

    def trimEdgeToSurfaces(self,fp,curve,surface1,surface2):
        """return from intersect() is sometimes a line, but the line extends beyond the face.
        this seeks to trim the line/curve to the confines of thos surfaces"""
        self.log(fp,f"trim(): curve = {curve}, surface1 = {surface1}, surface2 = {surface2}\n")
        return curve

    def checkAllVertexIntersections(self, fp, shp, s1, s2, s3):
        shape = self.checkVertexIntersection(fp, shp, s3)
        if shape.isNull():
            return shape
        else:
            shape = self.checkVertexIntersection(fp, shape,s2)
            if shape.isNull():
                return shape
            else:
                return self.checkVertexIntersection(fp, shape,s1)

    def editFaces(self):
        from PySide import QtGui
        fp = FreeCAD.ActiveDocument.getObject(self.fpName)
        if not FreeCADGui.Control.activeDialog():
            panel = TaskEditLinkSubPanel(fp,["Object1","Object2","Object3"],"Faces/Edges")
            FreeCADGui.Control.showDialog(panel)
            self.editingMode = True #tells execute() not to hide the linked object
        else:
            self.editingMode=False
            FreeCAD.Console.PrintError("Another task dialog is active.  Close that one and try again.\n")



class TaskEditLinkSubPanel: #simple editor for App::PropertyLinkSub
    def __init__(self, obj, linkSubNames, subNames,):
        self.obj = obj
        self.subNames = subNames
        self.linkSubNames = linkSubNames #list of property names
        self.linkObjs = []
        self.subObjects = []
        for ii,lsn in enumerate(self.linkSubNames):
            if lsn:
                atr = getattr(self.obj,self.linkSubNames[ii])
                if atr and len(atr) == 2:
                    self.linkObjs.append(atr[0])
                    self.subObjects.append(atr[1])
        self.obj.Proxy.log(self.obj, f"linkObjs = {self.linkObjs}, subObjects = {self.subObjects}\n")
        self.form = QtGui.QWidget()
        self.label1 = QtGui.QLabel("Select the "+self.subNames+" subobjects to use and click OK.\nThe ones already being utilized have been selected for you.")
        layout=QtGui.QHBoxLayout()
        layout.addWidget(self.label1)
        self.form.setLayout(layout)
        self.form.setWindowTitle('Edit '+self.subNames)
        FreeCADGui.Selection.clearSelection()
        for ii,linkObj in enumerate(self.linkObjs):
            for f in self.subObjects[ii]:
                FreeCADGui.Selection.addSelection(FreeCAD.ActiveDocument.Name,linkObj.Name,f)
        self.obj.Proxy.editingMode = True

    def reject(self):
        FreeCADGui.Control.closeDialog()
        fp = self.obj
        self.obj.Proxy.editingMode = False
        FreeCADGui.activeDocument().resetEdit()
        FreeCAD.ActiveDocument.recompute()

    def accept(self):
        FreeCADGui.ActiveDocument.resetEdit()
        FreeCADGui.Control.closeDialog()
        fp = self.obj
        if not fp: #user deleted or closed document perhaps
            return
        selx = FreeCADGui.Selection.getSelectionEx()
        if not selx:
            FreeCAD.Console.PrintWarning("Nothing selected, leaving "+self.linkObj.Name+" unmodified.")
            return
        subobjects = []
        for s in selx:
            if s.HasSubObjects:
                for en in s.SubElementNames:
                    subobjects.append((s.Object,en))
            else:
                if s.Object.isDerivedFrom("PartDesign::Plane"):
                    subobjects.append((s.Object,"Plane"))
                elif s.Object.isDerivedFrom("PartDesign::Line"):
                    subobjects.append((s.Object,"Line"))
                elif not hasattr(s.Object,"Shape"):
                    FreeCAD.Console.PrintWarning(f"Skipping {s.Object.Label}\n")
                    continue
                elif len(s.Object.Shape.Faces) == 1:
                    subobjects.append((s.Object,"Face1"))
                elif len(s.Object.Shape.Edges) == 1:
                    subobjects.append((s.Object,"Edge1"))
        if len(subobjects) > 3 or len(subobjects) == 0:
            FreeCAD.Console.PrintError("Selection Error, select 1, 2, or 3 objects\n")
            raise Exception("Invalid selection\n")
        else:
            for linkSubName in self.linkSubNames:
                setattr(self.obj, linkSubName, None)
            for ii,subobject in enumerate(subobjects):
                setattr(self.obj,self.linkSubNames[ii], subobject)
        if hasattr(fp,"_Body") and fp._Body and self.linkObj not in fp._Body.Group:
            fp._Body.Group += [self.linkObj]
        if hasattr(fp.Proxy,"editingMode"):
            fp.Proxy.editingMode = False
        FreeCAD.ActiveDocument.recompute()


class IntersectionVP:

    def __init__(self, obj):
        '''Set this object to the proxy object of the actual view provider'''
        obj.Proxy = self

    def setEdit(self,vobj,modNum):
        #FreeCAD.Console.PrintMessage("modNum = "+str(modNum)+"\n")
        if modNum == 0:
            vobj.Object.Proxy.editFaces()
            return True
        elif modNum == 3: #color per face
            FreeCADGui.runCommand('Part_ColorPerFace',0)
            return True

    def attach(self, obj):
        '''Setup the scene sub-graph of the view provider, this method is mandatory'''
        self.Object = obj.Object

    def updateData(self, fp, prop):
        '''If a property of the handled feature has changed we have the chance to handle this here'''
        # fp is the handled feature, prop is the name of the property that has changed
        #FreeCAD.Console.PrintMessage(prop+" is now "+str(getattr(fp,prop))+chr(10))
        if prop == "HasIntersection":
            fp.ViewObject.signalChangeIcon()
    def getDisplayModes(self,obj):
        '''Return a list of display modes.'''
        modes=[]
        modes.append("Flat Lines")
        return modes

    def getDefaultDisplayMode(self):
        '''Return the name of the default display mode. It must be defined in getDisplayModes.'''
        return "Flat Lines"

    def setDisplayMode(self,mode):
        '''Map the display mode defined in attach with those defined in getDisplayModes.\
                Since they have the same names nothing needs to be done. This method is optional'''
        return mode

    def onChanged(self, vp, prop):
        '''Here we can do something when a single property got changed'''
        pass

    def onDelete(self, vobj, subelements):
        return True

    def getIcon(self):
        '''Return the icon in XPM format which will appear in the tree view. This method is\
                optional and if not defined a default icon is shown.'''
        xpm =__xpm__
        fp = self.Object
        color = "None" if fp.HasIntersection else "red"
        fp.ViewObject.LineColor = (1.,0.,0.) if not fp.HasIntersection else (0.,0.,1.)
        fp.ViewObject.PointColor = (1.,.5,0.) if not fp.HasIntersection else (0.,1.,1.)
        return xpm.replace("None",color)

    def __getstate__(self):
        '''When saving the document this object gets stored using Python's json module.\
                Since we have some un-serializable parts here -- the Coin stuff -- we must define this method\
                to return a tuple of all serializable objects or None.'''
        return None

    def __setstate__(self,state):
        '''When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here.'''
        return None



def findHome(fp, datum1=None):
    """find a home for fp, either in a Part or a Body, if one is active
       or in same container as datum1 if none are active"""
    foundHome = False
    body=FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")
    part=FreeCADGui.ActiveDocument.ActiveView.getActiveObject("part")
    if body:
        body.Group=body.Group+[fp]
        foundHome = True
    if not foundHome and datum1:
        parent = None
        if datum1.Parents:
            parent=datum1.Parents[0][0] #put in same body as Object1
        if parent and parent.TypeId == "App::Part":
            part = parent
            if not foundHome:
                for obj in parent.Group:
                    if obj.TypeId == "PartDesign::Body":
                        if datum1 in obj.Group:
                            obj.Group += [fp]
                            foundHome = True
        elif parent and parent.TypeId == "PartDesign::Body":
            if not body and not foundHome:
                parent.Group += [fp]
                foundHome = True
        if not foundHome:
            if part:
                part.Group += [fp]
    return foundHome

def makeObject(FP):

    doc = FreeCAD.ActiveDocument
    if doc:
        fp = doc.addObject("Part::FeaturePython","Intersection")
        if FP:
            FP.Intersection(fp)
            FP.IntersectionVP(fp.ViewObject)
        else:
            Intersection(fp)
            IntersectionVP(fp.ViewObject)
        fp.ViewObject.PointSize = 7
        fp.ViewObject.LineWidth = 7
        foundHome = findHome(fp) #puts in part/body if one is active
        doc.recompute()
        sel = FreeCADGui.Selection.getSelectionEx()
        subobjects = []
        for s in sel:
            if s.HasSubObjects:
                for en in s.SubElementNames:
                    subobjects.append((s.Object,en))
            else:
                if s.Object.isDerivedFrom("PartDesign::Plane"):
                    subobjects.append((s.Object,"Plane"))
                elif s.Object.isDerivedFrom("PartDesign::Line"):
                    subobjects.append((s.Object,"Line"))
                elif not hasattr(s.Object,"Shape"):
                    FreeCAD.Console.PrintWarning(f"Skipping {s.Object.Label}\n")
                    continue
                elif len(s.Object.Shape.Faces) == 1:
                    subobjects.append((s.Object,"Face1"))
                elif len(s.Object.Shape.Edges) == 1:
                    subobjects.append((s.Object,"Edge1"))
        if len(subobjects) > 3 or len(subobjects) == 0:
            FreeCAD.Console.PrintError("Selection Error, select 1, 2, or 3 objects\n")
            raise Exception("Invalid selection\n")
        else:
            fp.Object1 = subobjects[0] if len(subobjects) >= 1 else None
            fp.Object2 = subobjects[1] if len(subobjects) >= 2 else None
            fp.Object3 = subobjects[2] if len(subobjects) == 3 else None
            if not foundHome:
                findHome(fp,fp.Object1[0]) #put fp in same body as first selected object
        doc.recompute()

def write_file():
    current = __file__
    new_name = current.replace(".FCMacro", ".py")
    with open(new_name, "w") as new_file:
        with open(__file__, "r") as current_file:
            new_file.write(current_file.read())

if __name__ == "__main__":

    if ".FCMacro" in __file__ and not os.path.exists(__file__.replace(".FCMacro",".py")):
        write_file()
        new_name = __file__.replace(".FCMacro", ".py")
        FreeCAD.Console.PrintWarning(f"A new file has been created named {new_name} in order for the feature python objects to work when you reload a document containing one of them.\n")
    import importlib
    import Intersection
    importlib.reload(Intersection)

    if __version__ > Intersection.__version__:
        write_file() #update .py file with new version (only needed for versions < 022 / 1.0)
        importlib.reload(Intersection)
        FreeCAD.Console.PrintMessage(f"Intersection.py has been updated to version {__version__}\n")
    elif __version__ < Intersection.__version__:
        FreeCAD.Console.PrintError(f"version of existing Intersection.py file ({Intersection.__version__}) is greater than current version ({__version__}) update skipped\n")

    makeObject(Intersection)

#icon for addon manager to put on toolbar
__xpm__ ="""/* XPM */
static char * _632119818831[] = {
"64 64 147 2 ",
"   c #74596C",
".  c #787573",
"X  c #E70000",
"o  c #E80000",
"O  c #F10000",
"+  c #EC1112",
"@  c #EC1119",
"#  c #ED221A",
"$  c #EC1226",
"%  c None",
"&  c #EC1229",
"*  c #F21C24",
"=  c #ED2123",
"-  c #ED2229",
";  c #ED1C51",
":  c #ED214E",
">  c #ED2255",
",  c #EC1172",
"<  c #ED2179",
"1  c #8B7E5A",
"2  c #BEA736",
"3  c #BBA438",
"4  c #BBAA3C",
"5  c #C7AD1B",
"6  c #C8AD1A",
"7  c #D5AB1F",
"8  c #C5AD22",
"9  c #C9B22B",
"0  c #C6B030",
"q  c #E4D316",
"w  c #F5E707",
"e  c #FFEF00",
"r  c #F9ED0C",
"t  c #FFF200",
"y  c #FFFA00",
"u  c #F7EB13",
"i  c #F3E71E",
"p  c #F3E91C",
"a  c #CEC62F",
"s  c #D5C42C",
"d  c #E9DD36",
"f  c #E4D43A",
"g  c #E6DB3D",
"h  c #E8DE39",
"j  c #EFE526",
"k  c #ECE32D",
"l  c #F0E525",
"z  c #EAE034",
"x  c #B28B4B",
"c  c #AC8F51",
"v  c #A78F5C",
"b  c #B3A344",
"n  c #BCB541",
"m  c #A7A35C",
"M  c #ADA859",
"N  c #8B8768",
"B  c #928F6C",
"V  c #969366",
"C  c #9B9662",
"Z  c #9C9862",
"A  c #93936B",
"S  c #8C8A70",
"D  c #A39363",
"F  c #97BD60",
"G  c #C7BC68",
"H  c #D7D25F",
"J  c #DBD25D",
"K  c #E3D948",
"L  c #E1D94B",
"P  c #E0D750",
"I  c #FFF544",
"U  c #FFF54D",
"Y  c #FFF653",
"T  c #FFF65C",
"R  c #D6CF6A",
"E  c #D7D162",
"W  c #D9D063",
"Q  c #D3CC73",
"!  c #FFF768",
"~  c #FFF873",
"^  c #FFF87C",
"/  c #12009D",
"(  c #2D008C",
")  c #360886",
"_  c #250D93",
"`  c #241D9F",
"'  c #21249E",
"]  c #2F279B",
"[  c #332E97",
"{  c #0C0DA9",
"}  c #1315A4",
"|  c #1E1CA1",
" . c #4F4E87",
".. c #545285",
"X. c #585682",
"o. c #035ACB",
"O. c #156CC2",
"+. c #61B69C",
"@. c #37C4B6",
"#. c #4EC1B0",
"$. c #0BAAE2",
"%. c None",
"&. c #30CBC0",
"*. c #36CDC8",
"=. c #00EAFF",
"-. c #00F3FF",
";. c cyan",
":. c #BDBB91",
">. c #BFBF9D",
",. c #B7B7A6",
"<. c #BFB7A0",
"1. c #BCBDA3",
"2. c #B5B7AC",
"3. c #BCB6AE",
"4. c #B7B9AE",
"5. c #BCBAAC",
"6. c #B6AFBA",
"7. c #AFB2BE",
"8. c #B4B6B5",
"9. c #BAB6B4",
"0. c #B3B4BB",
"q. c #B9B4B8",
"w. c #C0BC8A",
"e. c #C4BE9D",
"r. c #C1BBA1",
"t. c #C0C095",
"y. c #FFF882",
"u. c #FFF98B",
"i. c #FFF994",
"p. c #FFF99A",
"a. c #C6C2A1",
"s. c #FFFAA5",
"d. c #FFFAAB",
"f. c #FFFBB4",
"g. c #FFFBBD",
"h. c #AAADC6",
"j. c #B3AFC8",
"k. c #AEB1C4",
"l. c #B2B6C2",
"z. c #FFFBC3",
"x. c #FFFCCB",
"c. c #FFFCD4",
"v. c #FFFDDA",
"b. c #FFFDE2",
"n. c #FFFEEC",
"m. c #FFFEF2",
"M. c none",
/* pixels */
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t e I M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t t t I M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t t t t U M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t t t t e Y M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.t t t t t t e T M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t d e.y t t e T M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e y l j.Q y t t t ! M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.3.Q y t t t ! M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e y l q.e.5.R y t t e ~ M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.e.e.3.R t t t t ~ M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e y l q.e.e.e.3.W y t t e ^ M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.e.e.e.e.3.J y t t e y.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e y l q.e.e.e.e.e.3.J y t t t u.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.e.e.e.e.e.e.9.J y t t e u.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t j q.e.e.e.e.r.e.e.3.P y t t t i.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.t y j q.e.t.e.e.e.e.r.t.q.P t t t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.e.e.e.e.e.e.a.e.e.r.L y t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.e.e.e.e.e.e.e.e.e.e.q.L t t t e s.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.t y l q.e.e.e.e.e.e.e.e.e.1.0.P t t t t t d.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t l q.r.r.r.e.r.G 8 0 0 0 2 q y t t t t e f.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.b.t w 3 0 0 0 0 0 0 0 0 0 0 0 0 0 2 q y t t t t t e f.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.e t t t t t t w 3 0 0 0 0 0 0 0 0 0 0 0 0 0 2 q y y E h.z t t e g.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.e t t t t t t t t t t t y w 3 0 0 0 0 0 0 9 b B V V V Z S a y y H 8.0.z t t t z.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.e t t t t t t t t t e t t t u l.w.5 7 F -.=.=.-.*.x C Z Z D Z S a y y H 4.>.8.k t t t x.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"t t t t t t t t t t 7.>.>.>.,.1.5.:.6 7 F -.=.=.-.*.x Z Z Z Z Z S a y y E 4.>.>.h.k y t e x.M.M.M.M.M.M.% % % % % % % % % % % M.",
"t t t t t >.1.>.>.t.,.1.1.>.>.>.1.:.5 7 F ;.$.( ' }  .M Z Z Z Z S a y y H 4.>.>.>.8.j y t e c.M.M.M.M.M.% % % % % % % % % % % M.",
"t t e t y k.>.>.1.>.>.>.>.t.>.>.1.:.5 7 F ;.$.( ` ` } ..M Z Z Z S a y y H 4.>.>.>.>.0.j t t t v.M.M.M.M.% % % % % % % % % % % M.",
"M.e t t t t l.>.>.>.>.>.>.>.>.>.1.:.5 7 F ;.$.) | ] [ { ..M Z Z S a y y H 4.>.>.>.>.>.7.l t t t b.M.M.M.% % % % % % % % % % % M.",
"M.M.e e t t t k.>.>.>.>.>.>.>.>.1.:.5 9 4 Z . { } ' ` | } X.M Z S a y y H 4.>.>.>.>.>.>.0.p t t e b.M.M.% % % % % % % % % % % M.",
"M.M.M.e t t t y k.>.>.>.>.a.>.>.1.t.5 9 4 A M . } _ O.;.=.=.-.#.v a y y H 4.>.>.>.>.>.>.>.0.p t t e n.M.% % % % % % % % % % % M.",
"M.M.M.M.e t t t t h.>.>.>.>.t.1.1.:.5 9 4 A Z m . / O.;.=.=.-.&.1 s y y E 4.>.>.>.>.>.>.>.>.7.u t t t y % & % % % % % % % % % M.",
"M.M.M.M.M.e t t t t k.>.>.1.a.t.1.:.5 9 4 A Z Z m   o.;.=.-.-.&.N s y y H 4.>.>.>.>.>.>.>.>.1.0.u t t y % % % % % % % % % % % M.",
"M.M.M.M.M.M.e t t t t 7.>.>.>.>.1.:.5 9 4 A Z Z Z c +.-.=.=.-.&.N s y y H 4.>.>.>.>.1.1.,.>.>.>.0.r y y % % % % % % % % % % % M.",
"M.M.M.M.M.M.M.e t t t t h.>.>.>.1.:.5 9 4 A Z Z Z c +.-.=.=.-.&.1 s y y E 8.,.>.,.0.j t t t t t t t t y % % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.t t t t t 2.,.t.1.:.6 9 4 A Z Z C Z Z Z C v v D S a y t t t t t t t t t t t t t t t t y % % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.t t t t r 4.1.1.e.5 9 4 A Z C V V V V V B 9 y t t t t t t t t t t e t t t t e b.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.e t t t r 2.1.w.5 9 2 V C B n y t t t t t t t t t t t t t t t e g.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.e t t t u l.:.5 2 s y t t t t t t t t t t e t t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.m.e t t t t t t t t t t t t t t t t y L q.q.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.m.e t t t t t t t t t t t d q.e.e.e.e.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.n.e t t t y i 9.<.e.e.e.e.e.e.e.e.e.e.9.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.t p 3.e.e.e.e.e.e.e.e.e.e.e.9.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.t t j q.e.e.e.e.e.e.e.e.e.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.e t t j q.e.e.e.e.e.e.e.e.e.9.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.c.t t t t k q.e.e.e.e.e.e.e.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.x.t t t k q.e.e.e.e.e.e.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.z.e t t z q.e.e.e.e.e.e.q.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.g.e t y h q.e.e.e.e.e.9.L y e p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.f.e t t g q.e.e.e.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.f.t t y h 2.e.e.e.9.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.d.t t t L 9.e.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.s.e t y d 2.e.9.L y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.p.t t t d <.0.L t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.p.t t y g 6.P y t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.i.t t t f f t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.u.t t t t t t p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.u.e t t t e p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % % % M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.y.e t t e p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % % % M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.^ t t e p.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.% % % % % % % M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.",
"M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M.M."
};"""