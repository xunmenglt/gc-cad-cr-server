import os
import sys
import uvicorn
sys.path.append(os.getcwd())
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from server.router.file_router import router as file_router
from server.router.task_router import router as task_router
from database.base import create_tables

# 导入所有数据库模型，确保表定义被注册
from database.models import sys_file_model, task_model


# FastAPI应用配置
app = FastAPI(
    title="广诚CAD内容识别服务",
    description="""
    ## 广诚CAD内容识别系统API文档
    
    这是一个专门用于CAD图纸内容识别和处理的服务系统，提供以下功能：
    
    ### 主要功能模块
    
    * **文件管理** - 文件上传、下载、文件夹管理
    * **任务管理** - CAD识别任务的创建、执行、监控
    
    ### 支持的文件格式
    
    * CAD文件：DWG、DXF
    * 图片文件：PNG、JPG、JPEG
    * 其他格式：PDF
    
    ### 使用说明
    
    1. 首先通过文件管理接口上传需要处理的CAD文件
    2. 创建识别任务，配置相关参数
    3. 启动任务进行识别处理
    4. 监控任务进度并获取结果
    
    ### 技术支持
    
    如有问题请联系技术支持团队。
    """,
    version="1.0.0",
    contact={
        "name": "广诚科技",
        "email": "support@guangcheng.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "文件管理",
            "description": "文件和文件夹的上传、创建、删除、查看等操作",
        },
        {
            "name": "任务管理", 
            "description": "CAD识别任务的创建、启动、停止、监控等操作",
        },
        {
            "name": "系统信息",
            "description": "系统状态检查和基本信息查询",
        },
    ],
    docs_url="/docs",  # 原生Swagger UI地址
    redoc_url="/redoc",  # ReDoc地址
    openapi_url="/openapi.json"  # OpenAPI schema地址
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """服务启动时初始化数据库"""
    try:
        create_tables()
        print("数据库表初始化完成")
    except Exception as e:
        print(f"数据库表初始化失败: {str(e)}")
        raise

@app.get("/", tags=["系统信息"])
async def root():
    """
    系统首页
    
    返回系统基本信息和服务状态
    """
    return {
        "message": "广诚CAD内容识别服务",
        "version": "1.0.0",
        "status": "running",
        "docs": {
            "scalar_dark": "/scalar",          # 深色主题文档
            "scalar_light": "/scalar-light",   # 浅色主题文档  
            "swagger": "/docs",                # 原生Swagger
            "redoc": "/redoc"                  # ReDoc
        }
    }

@app.get("/health", tags=["系统信息"])
async def health_check():
    """
    健康检查接口
    
    用于监控系统运行状态
    """
    return {"status": "healthy", "timestamp": "2023-12-01T10:00:00Z"}

# 添加 Scalar 文档路由 (最美观的文档界面)
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    from fastapi.responses import HTMLResponse
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title}</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}
        </style>
    </head>
    <body>
        <script
            id="api-reference"
            type="application/json"
            data-url="{app.openapi_url}"
            data-configuration='{{"theme": "purple", "darkMode": true, "layout": "modern", "hideModels": false}}'
        ></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 添加浅色主题 Scalar 文档路由
@app.get("/scalar-light", include_in_schema=False)
async def scalar_light_html():
    from fastapi.responses import HTMLResponse
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title} - 浅色主题</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #ffffff;
            }}
        </style>
    </head>
    <body>
        <script
            id="api-reference"
            type="application/json"
            data-url="{app.openapi_url}"
            data-configuration='{{"theme": "default", "darkMode": false, "layout": "modern", "hideModels": false}}'
        ></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 注册路由
app.include_router(file_router, prefix="/files", tags=["文件管理"])
app.include_router(task_router, prefix="/task", tags=["任务管理"])

if __name__ == "__main__":
    print("启动广诚CAD内容识别服务...")
    print("文档地址:")
    print("   • Scalar 深色主题: http://localhost:8000/scalar")
    print("   • Scalar 浅色主题: http://localhost:8000/scalar-light") 
    print("   • Swagger UI:      http://localhost:8000/docs") 
    print("   • ReDoc:           http://localhost:8000/redoc")
    print("服务地址:         http://localhost:8000")
    
    uvicorn.run(
        "server.start:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # 禁用热重载以避免文件监视限制问题
    )

if __name__=="__main__":
    uvicorn.run(
        "server.start:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # 禁用热重载以避免文件监视限制问题
    )