import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr')
from vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/N1教学楼建筑_t3.dwg")
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]


param=QueryFeaturesParams(
    beginpos=0,
    condition="name='1' or name='2' or name='3' or name='4'",
    fields="objectid,points,envelop",
    geom=True,
    limit=50000,
    maxReturnCount=50000,
    querytype="condition",
    zoom= 1
)


# 获取地图原数据
queryFeaturesService=QueryFeaturesService()
res=queryFeaturesService.query(mapid=mapid,params=param,version="v1")
print(res)

# import requests
# data = dict(
#             beginpos=0,
#             condition="name='1' or name='2' or name='3' or name='4'",
#             fields="objectid,points,envelop",
#             geom=True,
#             limit=50000,
#             maxReturnCount=50000,
#             querytype="condition",
#             zoom= 1,
#             layername="s5d0e6aeae"
#         )

# res=requests.post(
#     url="https://vjmap.com/server/api/v1/map/cmd/queryFeatures/ccc372282a88/v1",
#     json=data,
#     headers={
#         "token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6MiwiVXNlcm5hbWUiOiJhZG1pbjEiLCJOaWNrTmFtZSI6ImFkbWluMSIsIkF1dGhvcml0eUlkIjoiYWRtaW4iLCJCdWZmZXJUaW1lIjo4NjQwMCwiZXhwIjo0ODEzMjY3NjM3LCJpc3MiOiJ2am1hcCIsIm5iZiI6MTY1OTY2NjYzN30.cDXCH2ElTzU2sQU36SNHWoTYTAc4wEkVIXmBAIzWh6M"
#     }
# )
# print(res.request.body)
# print(res.json())