import sys
import os
sys.path.append(os.getcwd())
from vjmap.services import UploadMAPService

service=UploadMAPService()
res=service.upload_file("/opt/data/private/liuteng/code/dev/gc-cad-cr-server/src/data/file_system/test/A-2-101.dwg")
print(res)

