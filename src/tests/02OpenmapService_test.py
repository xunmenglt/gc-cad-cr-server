import sys
import os
sys.path.append(os.getcwd())
from vjmap.services import UploadMAPService,OpenMapRequestParams,OpenmapService

uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/dev/gc-cad-cr-server/src/data/file_system/test/A-2-102.dwg")
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]

openmapService=OpenmapService()
params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
res=openmapService.openmap(mapid=mapid,params=params)
layoutIndex=res.get("layoutIndex",None)
layouts=res.get("layouts",None)
print(res)
print(layoutIndex)
print(layouts)


